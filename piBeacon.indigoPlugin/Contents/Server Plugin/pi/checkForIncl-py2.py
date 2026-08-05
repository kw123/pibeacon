#!/usr/bin/python
# -*- coding: utf-8 -*-
import os, time, subprocess, logging, sys

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


def readPopen(cmd):
		"""Runs a shell command via subprocess.Popen, logging the command and result, and returns the decoded stdout and stderr strings.

		Inputs:
		    cmd (str): shell command to execute
		Outputs:
		    tuple: (stdout, stderr) decoded utf-8 strings, or None on exception
		"""
		try:
			logger.log(20,"doing:  {}".format(cmd) )
			ret, err = subprocess.Popen(cmd, shell=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE).communicate()
			logger.log(20,"ret: {} {}".format(ret, err ) )
			return ret.decode('utf_8'), err.decode('utf_8')
		except Exception as e:
			logger.log(20,"", exc_info=True)

def checkIfPy3():
	"""Reads /etc/os-release and returns True if the OS VERSION_ID is 11 or greater, indicating a Python-3-only platform.

	Inputs:
	    None.
	Outputs:
	    bool: True if OS VERSION_ID >= 11, else False
	"""
	osInfo	 = readPopen("cat /etc/os-release")[0].strip("\n").split("\n")
	for line in osInfo:
		if line .find("VERSION_ID=") == 0:
			if int( line.strip('"').split('="')[1] ) >=11: return True
	return False

def checkOsVersionis3():
	"""Returns whether the running Python interpreter is version 3 by checking the first character of sys.version.

	Inputs:
	    None.
	Outputs:
	    bool: True if Python major version is 3
	"""
	return sys.version[0] == "3"


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

	"""Performs the Python 2 dependency-install workflow: exits early if running Python 3 or a newer OS, waits for any running apt-get, then checks for and installs required packages (smbus2, hcidump, pigpio, RPi.GPIO, pexpect, expect), fixes broken apt packages, and writes a completion marker file.

	Inputs:
	    None.
	Outputs:
	    None: installs system/python packages via apt/pip, logs progress, and writes the includepy2.done marker
	"""
	if checkOsVersionis3: 
		logger.log(20,"python2 not installed stopping checking for include py2 "  )
		open("/home/pi/pibeacon/includepy2.done", "w").write("done")
		exit()

	if checkIfPy3():
		logger.log(20,"must use py3 due to opsys version < 10 "  )
		open("/home/pi/pibeacon/includepy2.done", "w").write("done")
		exit()


	for ii in range(20):
		logger.log(20,"check if apt-get ist still running"  )
		ret = readPopen("ps -ef | grep apt-get")
		if ret[0].find("apt-get install") == -1:
			break
		time.sleep(10)		


	if True:
		logger.log(20,"check if apt install  is ok"  )
		ret = readPopen("sudo apt-get --fix-broken install  -y &")


	if False:
		logger.log(20,"check python-serial"  )
		try:
			import serial
		except Exception as e:
			logger.log(20,"", exc_info=True)
			aptInstall("python-serial")

	if True:
		logger.log(20,"check smbus2"  )
		try:
			import smbus2
		except Exception as e:
			logger.log(20,"", exc_info=True)
			readPopen("sudo pip install smbus2")

	if True:
		logger.log(20,"check hcidump"  )
		ret = readPopen("which hcidump")
		if ret[0].find("/usr/bin/hcidump") == -1:
			aptInstall("bluez-hcidump")

	if True:
		logger.log(20,"check pigpio"  )
		try:
			import RPi.GPIO as GPIO
		except:
			ret = aptInstall("pigpio python-pigpio")

	if True:
		logger.log(20,"check RPi.GPIO "  )
		try:		
			import RPi.GPIO as GPIO
		except Exception as e:
			logger.log(20,"", exc_info=True)
			ret = aptInstall("python3-dev python3-rpi.gpio")

	if True:
		logger.log(20,"check pexpect"  )
		try:
			import pexpect
		except Exception as e:
			logger.log(20,"", exc_info=True)
			readPopen("sudo pip install pexpect")

	if False:
		logger.log(20,"check import Adafruit_DHT"  )
		try:
			import Adafruit_DHT
		except Exception as e:
			logger.log(20,"", exc_info=True)
			readPopen("sudo pip install Adafruit_DHT ")

	if True:
		logger.log(20,"check expect"  )
		ret = readPopen("which expect")
		if ret[0].find("/usr/bin/expect") == -1:
			aptInstall("expect")


	logger.log(20,"check if apt install  is ok"  )
	ret = readPopen("sudo apt-get --fix-broken install  -y")
	logger.log(20,"check if apt autoremove  is ok"  )
	ret = readPopen("sudo apt-get autoremove -y &")

	open("/home/pi/pibeacon/includepy2.done", "w").write("done")

	logger.log(20,"finished" )

execInstall()
