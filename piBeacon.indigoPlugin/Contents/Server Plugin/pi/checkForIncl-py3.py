#!/usr/bin/python3
# -*- coding: utf-8 -*-
import sys, os, time, subprocess, logging
import shutil

def _fixLogPerm(_fn):		# a sudo-started helper CREATES this file as root; a later program running
	try:					# as pi then cannot append and python logging swallows the error silently
		if not os.path.exists(_fn):
			_f = open(_fn, "a")
			_f.close()
		os.chmod(_fn, 0o666)
		import pwd, grp
		os.chown(_fn, pwd.getpwnam("pi").pw_uid, grp.getgrnam("pi").gr_gid)
	except Exception:	pass

_fixLogPerm("/var/log/pibeacon")
logging.basicConfig(level=logging.INFO, filename= "/var/log/pibeacon",format='%(asctime)s %(module)-17s %(funcName)-22s L:%(lineno)-4d %(message)s', datefmt='%d-%H:%M:%S')
class _TenthFmt(logging.Formatter):	# timestamps with tenths of a second, same as piBeaconUtils.setLogging
	def formatTime(self, record, datefmt=None):
		return "{}.{}".format(time.strftime(datefmt or '%d-%H:%M:%S', time.localtime(record.created)), int(record.msecs/100.))
for _h in logging.getLogger().handlers: _h.setFormatter(_TenthFmt('%(asctime)s %(module)-17s %(funcName)-22s L:%(lineno)-4d %(message)s', datefmt='%d-%H:%M:%S'))
logger = logging.getLogger(__name__)

####-------------------------------------------------------------------------####
def readPopen(cmd,doPrint= True):
	"""Runs a shell command via subprocess.Popen, optionally logging the result, and returns the decoded stdout and stderr strings.

	Inputs:
	    cmd (str): shell command to execute
	    doPrint (bool): whether to log the command result
	Outputs:
	    tuple: (stdout, stderr) decoded utf-8 strings, or None on exception
	"""
	try:
		logger.log(20,"doing:  {}".format(cmd) )
		ret, err = subprocess.Popen(cmd, shell=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE).communicate()
		ret = ret.decode('utf_8')
		err = err.decode('utf_8')
		if doPrint: logger.log(20,"result: {} {}".format(ret, err ) )
		return ret, err
	except Exception as e:
		logger.log(20,"", exc_info=True)

def readFile(fName):
	"""Opens the named file, reads its entire contents, and returns them as a string; returns an empty string on error.

	Inputs:
	    fName (str): path of the file to read
	Outputs:
	    str: file contents, or '' on error
	"""
	try:
		f=open(fName,"r")
		ret = f.read()
		f.close()
		return ret
	except Exception as e:
		logger.log(20,"", exc_info=True)
	return ""

def writeFile(fName,NewFile):
	"""Opens the named file for writing and writes the supplied content to it, logging any exception.

	Inputs:
	    fName (str): path of the file to write
	    NewFile (str): content to write to the file
	Outputs:
	    None: writes the file to disk; logs on error
	"""
	try:
		f=open(fName,"w")
		f.write(NewFile)
		f.close()
		return 
	except Exception as e:
		logger.log(20,"", exc_info=True)
	return 

def checkIfOSlt9():
	"""Reads /etc/os-release and returns the numeric OS VERSION_ID, or 0 if not found.

	Inputs:
	    None.
	Outputs:
	    int: the OS VERSION_ID number, or 0 if not present
	"""
	osInfo	 = readPopen("cat /etc/os-release",doPrint=False)[0].strip("\n").split("\n")
	for line in osInfo:
		if line .find("VERSION_ID=") == 0:
			return int( line.strip('"').split('="')[1] )
	return 0

def checkOsVersionis3():
	"""Returns True if the running Python interpreter is version 3 or higher, based on the major version digit of sys.version.

	Inputs:
	    None.
	Outputs:
	    bool: True if Python major version >= 3, else False
	"""
	return int(sys.version[0]) >= 3



#################################
NOT_AVAILABLE_FILE = "/home/pi/pibeacon/aptNotAvailable.txt"

def aptNotAvailable():
	"""Packages this OS release simply does not have - one name per line, remembered across runs."""
	try:
		f = open(NOT_AVAILABLE_FILE)
		out = [x.strip() for x in f.read().split("\n") if x.strip() != ""]
		f.close()
		return out
	except Exception:
		return []


def markAptNotAvailable(pkg):
	"""Remembers that apt does not know this package on this OS, so it is never retried."""
	try:
		known = aptNotAvailable()
		if pkg in known:	return
		f = open(NOT_AVAILABLE_FILE, "a")
		f.write("{}\n".format(pkg))
		f.close()
	except Exception:
		pass


def aptInstall(pkgs, extra="-y "):
	"""apt-get install that does not fight a package the OS does not have.

	"E: Unable to locate package X" is NOT a transient failure - the package is gone or renamed in
	this release (libgpiod2 became libgpiod3 in trixie), so retrying it on every single start just
	burns an apt run and fills the log with the same error forever. The name is written to
	aptNotAvailable.txt and skipped from then on; delete that file to make it try again after an
	OS upgrade.

	Inputs:
	    pkgs (str): one or more package names, space separated
	    extra (str): extra apt options, default "-y "
	Outputs:
	    bool: True when apt ran and did not report a missing package
	"""
	wanted = [p for p in pkgs.split(" ") if p.strip() != ""]
	known  = aptNotAvailable()
	todo   = [p for p in wanted if p not in known]
	if not todo:
		logger.log(20, "skipping apt install of {} - not available on this OS (see {})".format(" ".join(wanted), NOT_AVAILABLE_FILE))
		return False
	ret = readPopen("sudo apt-get install {}{}".format(extra, " ".join(todo)))
	out = "{} {}".format(ret[0], ret[1]) if ret else ""
	if out.find("Unable to locate package") > -1:
		for p in todo:
			if out.find("Unable to locate package {}".format(p)) > -1:
				markAptNotAvailable(p)
				logger.log(20, "apt does not know '{}' on this OS - marked, will not be retried".format(p))
		return False
	return True


def execInstall():

	"""Installs and verifies all the apt packages and pip3 libraries required for the plugin's Python 3 sensor drivers (wiringPi/GPIO, hcidump, pigpio, pexpect, seesaw, neopixel, lidarlite, tmp117, dht, etc.), skipping those listed in notSupported, and writes a 'done' marker file when finished. Bails out early if the OS version is below 9.

	Inputs:
	    None.
	Outputs:
	    None: Runs shell/apt/pip install commands, imports test modules, logs progress, and writes the includepy3.done marker file
	"""
	notSupported = ["GPIO"]			# "DHT" dropped: the legacy Adafruit_DHT install it disabled is gone
	v = checkIfOSlt9() 

	if v < 9:
		logger.log(20,"finished, due to OS < 9, py 3 not completely installed" )
		open("/home/pi/pibeacon/includepy3.done", "w").write("done")
		exit()

	if v >11: 	usebreakOption = "--break-system-packages "
	else:		usebreakOption = ""

	logger.log(20,"------ starting on os v :{} not suported:{}, withoption: --{}".format(v, notSupported, usebreakOption) )



	for ii in range(20):
		logger.log(20,"check if apt-get ist still running"  )
		ret = readPopen("ps -ef | grep apt-get")
		if ret[0].find("apt-get install") == -1:
			break
		time.sleep(10)		

	if True:
		logger.log(20,"check if apt install  is ok"  )
		ret = readPopen("sudo apt-get --fix-broken install  -y")
		ret = readPopen("sudo apt-get autoremove -y")


	if "GPIO" not in notSupported:
		ret = readPopen("gpio -v",doPrint=False)
		if ret[0].find("version:") == -1:
			shutil.rmtree("/tmp/wiringPi", ignore_errors=True)		# no piBeaconUtils in this installer script
			installGPIO = "cd /tmp; wget https://project-downloads.drogon.net/wiringpi-latest.deb; sudo dpkg -i wiringpi-latest.deb ; rm -R /tmp/wiringPi"
			ret = readPopen(installGPIO)

	if "GPIO" not in notSupported:
		logger.log(20,"check RPi.GPIO "  )
		# it has to WORK, not merely import. On a pi5 the classic RPi.GPIO installs happily and then
		# raises - at import or at the first setmode ("Cannot determine SOC peripheral base
		# address") - because the RP1 does not have the old peripheral layout. So the import is
		# followed by an actual setmode, and the two failures are told apart:
		#   ImportError    = not installed at all  -> install the classic one, as before
		#   anything else  = installed but unusable -> this is the pi5/RP1 case, switch to rpi-lgpio,
		#                    the drop-in replacement that provides the very same "RPi.GPIO" module
		#                    name on top of lgpio.
		# rpi-lgpio and RPi.GPIO CONFLICT - same module name - so the old one has to be removed
		# first, and that is done ONLY after it has proven here that it does not run on this board.
		gpioWorks	= False
		gpioMissing	= False
		try:
			import RPi.GPIO as GPIO
			GPIO.setmode(GPIO.BCM)
			GPIO.setwarnings(False)
			gpioWorks = True
		except ImportError:
			gpioMissing = True
		except Exception as e:
			logger.log(20,"RPi.GPIO is installed but does not run on this board: {}".format(e))

		if gpioWorks:
			logger.log(20,"RPi.GPIO ok")
		elif gpioMissing:
			logger.log(20,"RPi.GPIO missing, installing")
			ret = aptInstall("python3-dev python3-rpi.gpio")
		elif v < 12:
			# a board that needs rpi-lgpio (pi5 / RP1) does not run an OS this old, so an unusable
			# RPi.GPIO here means something else is broken. Do NOT start removing packages over it.
			logger.log(20,"RPi.GPIO does not run and the OS (v{}) is older than a board that would need rpi-lgpio - not touching the installation, check the RPi.GPIO install by hand".format(v))
		else:
			# apt first: raspberry pi os ships python3-rpi-lgpio, and the package itself declares the
			# conflict with python3-rpi.gpio, so apt does the swap properly. pip only as a fallback,
			# and only then is the old package removed by hand - pip cannot resolve that conflict.
			logger.log(20,"RPi.GPIO does not run on this board (pi5/RP1) - switching to rpi-lgpio, the drop-in replacement")
			aptInstall("python3-lgpio")				# the backend rpi-lgpio sits on, and what gpiozero picks on a pi5
			if aptInstall("python3-rpi-lgpio"):
				logger.log(20,"python3-rpi-lgpio installed - verified on the next start of this check")
			else:
				logger.log(20,"python3-rpi-lgpio not available from apt, falling back to pip")
				readPopen("sudo apt-get remove -y python3-rpi.gpio")
				readPopen("sudo pip3 uninstall -y " + usebreakOption + " RPi.GPIO")
				readPopen("sudo pip3 install "   + usebreakOption + " rpi-lgpio")
				logger.log(20,"rpi-lgpio installed via pip - verified on the next start of this check")


	if "libgpiod" not in notSupported:
		# the library was RENAMED: bookworm and older ship libgpiod2, trixie ships libgpiod3. Ask for
		# the new name first and fall back to the old one, instead of hard-coding either - on trixie
		# the old name is simply "Unable to locate package" and used to be retried on every start.
		logger.log(20,"check libgpiod"  )
		installed = ""
		for pkg in ("libgpiod3", "libgpiod2"):
			if readPopen("dpkg -s {} | grep 'install ok installed'".format(pkg), doPrint=False)[0].find("install ok installed") > -1:
				installed = pkg
				break
		if installed != "":
			logger.log(20,"{} already installed".format(installed))
		else:
			for pkg in ("libgpiod3", "libgpiod2"):
				if aptInstall(pkg):
					installed = pkg
					logger.log(20,"{} installed".format(pkg))
					break
			if installed == "":
				logger.log(20,"neither libgpiod3 nor libgpiod2 is available on this OS - gpio sensors that need it will not work")


	if "hcidump" not in notSupported:
		logger.log(20,"check hcidump"  )
		ret = readPopen("which hcidump")
		if ret[0].find("hcidump") == -1:
			for ii in range(5):
				aptInstall("bluez-hcidump")
				ret = readPopen("which hcidump")
				if ret[0].find("hcidump") == -1:
					logger.log(20,"hcidump not properly installed, try again"  )
					time.sleep(20)
				else:
					logger.log(20,"hcidump installed"  )
					break


	if "pigpio" not in notSupported:
		logger.log(20,"check pigpio"  )
		try:
			if subprocess.Popen("/usr/bin/ps -ef | /usr/bin/grep pigpiod  | /usr/bin/grep -v grep",shell=True,stdout=subprocess.PIPE,stderr=subprocess.PIPE).communicate()[0].decode('utf-8').find("pigpiod")< 5:
				subprocess.call("/usr/bin/sudo /usr/bin/pigpiod &", shell=True)
				time.sleep(0.5)
			import pigpio
		except:
			ret = aptInstall("pigpio python3-pigpio")


	if "pexpect" not in notSupported:
		logger.log(20,"check pexpect"  )
		try:
			import pexpect
		except:
			logger.log(20,"sudo pip3 install  "+usebreakOption+ " adafruit-circuitpython-tmp117" )
			readPopen("sudo pip3 install  "+usebreakOption+ "  pexpect")


	if "expect" not in notSupported:
		logger.log(20,"check expect"  )
		ret = readPopen("which expect")
		if ret[0].find("/usr/bin/expect") == -1:
			aptInstall("expect")



	if "seesaw" not in notSupported:
		logger.log(20,"check adafruit-circuitpython-seesaw"  )
		try:
			from adafruit_seesaw.seesaw import Seesaw
		except:
			logger.log(20,"sudo pip3 install {}  adafruit-circuitpython-seesaw".format(usebreakOption) )
			readPopen("sudo pip3 install {}  adafruit-circuitpython-seesaw".format(usebreakOption))


	if "neopixel" not in notSupported:
		logger.log(20,"check board neopixel"  )
		try:
			import board
			import neopixel
		except Exception as e:
			logger.log(20,"sudo pip3 install "+usebreakOption+ " rpi_ws281x adafruit-circuitpython-neopixel;sudo pip3 install  "+usebreakOption+ "  adafruit-blinka" )
			readPopen("sudo pip3 install "+usebreakOption+ " rpi_ws281x adafruit-circuitpython-neopixel;sudo pip3 install  "+usebreakOption+ "  adafruit-blinka") # it is now ...../pibeacon no .log


	if "lidarlite" not in notSupported:
		logger.log(20,"check adafruit-circuitpython-lidarlite"  )
		try:
			import adafruit_lidarlite
		except:
			logger.log(20,"sudo pip3 install  "+usebreakOption+ "  adafruit-circuitpython-lidarlite" )
			readPopen("sudo pip3 install  "+usebreakOption+ "  adafruit-circuitpython-lidarlite")


	if "tmp117" not in notSupported:
		logger.log(20,"check adafruit_tmp117"  )
		try:
			import adafruit_tmp117
		except:
			logger.log(20,"sudo pip3 install  "+usebreakOption+ " adafruit-circuitpython-tmp117" )
			readPopen("sudo pip3 install  "+usebreakOption+ " adafruit-circuitpython-tmp117")


	if "dht" not in notSupported:
		logger.log(20,"check adafruit-circuitpython-dht"  )
		try:
			import adafruit_dht
		except:
			logger.log(20,"sudo pip3 install  "+usebreakOption+ "   adafruit-circuitpython-dht" )
			readPopen("sudo pip3 install  "+usebreakOption+ "   adafruit-circuitpython-dht")


	# (the legacy Adafruit_DHT install is gone: DHT.py uses adafruit_dht - the circuitpython one
	#  installed just above - and nothing imports Adafruit_DHT any more)

	if True:
		logger.log(20,"check if apt install  is ok"  )
		ret = readPopen("sudo apt-get --fix-broken install  -y") # wait until finsihed
		logger.log(20,"check if apt autoremove  is ok"  )
		ret = readPopen("sudo apt-get autoremove -y &")

	open("/home/pi/pibeacon/includepy3.done", "w").write("done")

	logger.log(20,"finished")

execInstall()


