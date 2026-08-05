#!/usr/bin/env python3
# -*- coding: utf-8 -*-
import os
import time
import subprocess
import sys

sys.path.append(os.getcwd())
sys.path.append("/home/pi/pibeacon")		# callbeacon is usually started from /home/pi, not from the pibeacon dir
try:
	import	piBeaconGlobals as G
	import	piBeaconUtils	as U
	homeDir  = G.homeDir
	homeDir0 = G.homeDir0
except:
	homeDir		= "/home/pi/pibeacon/"
	homeDir0	= "/home/pi/"

	# BOOTSTRAP FALLBACK: callbeacon runs before/without a working package (that is its job), so it
	# must never depend on piBeaconUtils. These are the few file helpers it uses, in plain stdlib.
	import glob as _glob, shutil as _shutil
	class _Ufallback(object):
		@staticmethod
		def makeDir(d):
			try:
				if not os.path.isdir(d): os.makedirs(d)
			except Exception: pass
		@staticmethod
		def removeFile(f):
			for ff in (_glob.glob(f) or [f]):
				try:
					if os.path.isdir(ff):	_shutil.rmtree(ff)
					elif os.path.exists(ff):os.remove(ff)
				except Exception: pass
		@staticmethod
		def doWriteSimpleFile(f, data):
			try:
				fh = open(f, "w"); fh.write("{}".format(data)); fh.close()
				os.chmod(f, 0o666)
			except Exception: pass
		@staticmethod
		def fixLogPermissions(files, owner="pi"):
			for f in files:
				try:
					if not os.path.exists(f):
						fh = open(f, "a"); fh.close()
					os.chmod(f, 0o666)
					import pwd, grp
					os.chown(f, pwd.getpwnam(owner).pw_uid, grp.getgrnam(owner).gr_gid)
				except Exception: pass
		@staticmethod
		def makeAccessible(path, recursive=True, owner="pi", verbose=False):
			EXEC = (".py", ".sh", ".exp", ".bash", ".so", ".pyc")
			todo = [path]
			if recursive and os.path.isdir(path):
				for base, dirs, names in os.walk(path):
					todo += [os.path.join(base, x) for x in dirs + names]
			for xx in todo:
				try:
					if os.path.isdir(xx) or xx.lower().endswith(EXEC) or os.path.basename(xx) in ("tf","tm","ct","py","py3"):
						os.chmod(xx, 0o777)
					else:
						os.chmod(xx, 0o666)
				except Exception: pass
			try:
				import pwd, grp
				uid, gid = pwd.getpwnam(owner).pw_uid, grp.getgrnam(owner).gr_gid
				for xx in todo:
					try:	os.chown(xx, uid, gid)
					except Exception: pass
			except Exception: pass
	U = _Ufallback()

import logging

try:	U.fixLogPermissions(["/var/log/pibeacon"])		# else this sudo-run script owns the log as root
except Exception:	pass
logging.basicConfig(level=logging.INFO, filename= "/var/log/pibeacon",format='%(asctime)s %(module)-17s %(funcName)-22s L:%(lineno)-4d %(message)s', datefmt='%d-%H:%M:%S')
class _TenthFmt(logging.Formatter):	# timestamps with tenths of a second, same as piBeaconUtils.setLogging
	def formatTime(self, record, datefmt=None):
		return "{}.{}".format(time.strftime(datefmt or '%d-%H:%M:%S', time.localtime(record.created)), int(record.msecs/100.))
for _h in logging.getLogger().handlers: _h.setFormatter(_TenthFmt('%(asctime)s %(module)-17s %(funcName)-22s L:%(lineno)-4d %(message)s', datefmt='%d-%H:%M:%S'))
logger = logging.getLogger(__name__)


################################
def readPopen(cmd):
	"""Runs a shell command via subprocess.Popen, captures stdout and stderr, and returns them decoded as UTF-8 strings; returns empty strings on any exception.

	Inputs:
	    cmd (str): shell command to execute
	Outputs:
	    tuple: (stdout, stderr) as decoded strings, or empty strings on error
	"""
	try:
		ret, err = subprocess.Popen(cmd, shell=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE).communicate()
		return ret.decode('utf_8'), err.decode('utf_8')
	except Exception as e:
		return "","" 

#################################
def simpleCall(cmd):
	"""Fires off a shell command asynchronously via subprocess.Popen without waiting for it or capturing output; silently ignores any failure.

	Inputs:
	    cmd (str): shell command to launch
	Outputs:
	    None: spawns a subprocess for its side effects
	"""
	try:
		subprocess.Popen(cmd, shell=True)
	except:
		pass
	return 

#################################
def getOsVersion():
	"""Reads /etc/os-release and parses the VERSION_ID line to return the OS version as an integer, or 0 if not found.

	Inputs:
	    None.
	Outputs:
	    int: OS VERSION_ID, or 0 if not found
	"""
	osInfo	 = readPopen("cat /etc/os-release")[0].strip("\n").split("\n")
	for line in osInfo:
		if line .find("VERSION_ID=") == 0:
			return int( line.strip('"').split('="')[1] )
	return 0 

#################################
def checkIfmustUsePy3():
	"""Determines whether Python 3 must be used, returning True if the OS version is 11 or higher or the running interpreter is Python 3, otherwise False.

	Inputs:
	    None.
	Outputs:
	    bool: True if Python 3 should be used
	"""
	if getOsVersion() >= 11:  return True
	if sys.version[0] == "3": return True
	return False

#################################
logger.log(20," -1-  starting callbeacon "  )

simpleCall("/usr/bin/sudo /usr/bin/systemctl daemon-reload")

if checkIfmustUsePy3(): usePython3 = "yes" 
else:					usePython3 = "" 

#set GPIOs if requested BEFOR master.py runs just once after boot 
if usePython3 == "":	simpleCall("/usr/bin/sudo /usr/bin/python {}doGPIOatStartup.py > /dev/null 2>&1  & ".format(homeDir))
else:					simpleCall("/usr/bin/sudo /usr/bin/python3 -E {}doGPIOatStartup.py > /dev/null 2>&1  & ".format(homeDir))

logger.log(20," -2-  callbeacon after doGPIOatStartup "  )


# make new directories if they do not exist 
U.makeDir("{}".format(homeDir))
U.makeDir("{}soundfiles".format(homeDir))
U.makeDir("{}fonts".format(homeDir))
U.makeDir("{}displayfiles".format(homeDir))
U.makeDir("{}temp".format(homeDir))
## set permissions: scripts executable, everything else read/write, directories traversable,
## owner pi (never root). Replaces four "chmod +666/+111/+777" lines plus the chown - those
## chmods were INVALID modes (digits are not allowed after "+") and silently did nothing.
# recursive, but ONLY over the pibeacon directory - never /home/pi and never system paths.
# The earlier minutes-long run was not the walk itself: isScript() opened every single file to
# look for a shebang, and setOwner walked the whole tree a second time. Both fixed; the maxSecs
# budget in makeAccessible stays as a net so a big tree can never hold up the boot again.
U.makeAccessible(homeDir, recursive=True, owner="pi")

logger.log(20," -3-  callbeacon after chmod "  )

U.removeFile("{}*.pyc".format(homeDir))


U.removeFile("{}pygame.active".format(homeDir))

# remember boot time / or better when did master.py start first
U.doWriteSimpleFile("{}masterStartAfterboot".format(homeDir), "{:.0f}".format(time.time()))

U.removeFile("{}restartCount".format(homeDir))
#subprocess.call("rm  /var/log/piBeacon.log >	/dev/null 2>&1 ")


# call main program
cmd1 = "cd {}; nohup /bin/bash master.sh  {} & ".format(homeDir, usePython3)

logger.log(20," -4-  callbeacon {}".format(cmd1) )
subprocess.call(cmd1, shell=True)


# remove old files 

delList =[
		"masteripAddress","beacon_batteryLevelPosition", "beacon_ignoreMAC", "beacon_offsetUUID", "beacon_UUIDtoIphone, beacon_doNotIgnore", "beacon_fastDown", "beacon_ignoreUUID", 
		"beacon_minSignalCutoff", "beacon_onlyTheseMAC", "beacon_signalDelta",  "rejects.*", 
		"logfile", "logfile-1", "call-log",  "errlog", "logfile", "master.log", 
		"alive", "interface", "beaconloop",
		"rdlidar.py","sensors.py", "iPhoneBLE.py", "getsensorvalues.py", "getBeaconParameters.py", "beepBeacon.py", "receiveGPIOcommands.py", "INPUTRotata*", "INPUTRotateSwitchGrey.py",
		"setGPIO.py*",		# standalone predecessor of receiveCommands.setGPIO(), nothing launches it any more
		"OUTPUTgpio.py*",	# read-back poller via the (long gone) wiringpi "gpio" tool; setGPIO() reports the state itself
		"DHT copy.py*",		# finder duplicate of DHT.py, byte identical, never imported by anything
		"moistureSensorAdafruit","checkAdfruitInclude.py","checkForInclude.py","checkForInclude-py3.py","checkForInclude-py2.py","neopixel.py"]
for dd in delList:
	U.removeFile("{}{}".format(homeDir, dd))

# remove old logfiles
U.removeFile("/var/log/pibeacon*.log") # it is now ...../pibeacon no .log
U.removeFile("{}logs".format(homeDir))

logger.log(20," -5-  callbeacon finished"  )


exit()
