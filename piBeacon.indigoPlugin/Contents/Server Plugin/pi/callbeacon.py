#!/usr/bin/env python
# -*- coding: utf-8 -*-
import os
import time
import subprocess
import sys

sys.path.append(os.getcwd())
try:
	import	piBeaconGlobals as G
	import	piBeaconUtils	as U
	homeDir  = G.homeDir
	homeDir0 = G.homeDir0
except:
	homeDir		= "/home/pi/pibeacon/"
	homeDir0	= "/home/pi/"

import os, time, subprocess, logging, sys

logging.basicConfig(level=logging.INFO, filename= "/var/log/pibeacon",format='%(asctime)s %(module)-17s %(funcName)-22s L:%(lineno)-4d Lv:%(levelno)s %(message)s', datefmt='%d-%H:%M:%S')
logger = logging.getLogger(__name__)


################################
def readPopen(cmd):
	try:
		ret, err = subprocess.Popen(cmd, shell=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE).communicate()
		return ret.decode('utf_8'), err.decode('utf_8')
	except Exception as e:
		return "","" 

#################################
def simpleCall(cmd):
	try:
		ret, err = subprocess.Popen(cmd, shell=True)
		return ret.decode('utf_8'), err.decode('utf_8')
	except Exception as e:
		return "","" 

#################################
def getOsVersion():
	osInfo	 = readPopen("cat /etc/os-release")[0].strip("\n").split("\n")
	for line in osInfo:
		if line .find("VERSION_ID=") == 0:
			return int( line.strip('"').split('="')[1] )
	return 0 

#################################
def checkIfmustUsePy3():
	if getOsVersion() >= 11:  return True
	if sys.version[0] == "3": return True
	return False

#################################
logger.log(30," -1-  starting callbeacon "  )

simpleCall("/usr/bin/sudo /usr/bin/systemctl daemon-reload")

if checkIfmustUsePy3(): usePython3 = "yes" 
else:					usePython3 = "" 

#set GPIOs if requested BEFOR master.py runs just once after boot 
if usePython3 == "":	simpleCall("/usr/bin/sudo /usr/bin/python {}doGPIOatStartup.py > /dev/null 2>&1  & ".format(homeDir))
else:					simpleCall("/usr/bin/sudo /usr/bin/python3 -E {}doGPIOatStartup.py > /dev/null 2>&1  & ".format(homeDir))

logger.log(30," -2-  callbeacon after doGPIOatStartup "  )


# make new directories if they do not exist 
subprocess.call("mkdir {} > 					/dev/null 2>&1 ".format(homeDir), shell=True)
subprocess.call("mkdir {}soundfiles > 		    /dev/null 2>&1 ".format(homeDir), shell=True)
subprocess.call("mkdir {}fonts > 				/dev/null 2>&1 ".format(homeDir), shell=True)
subprocess.call("mkdir {}displayfiles > 		/dev/null 2>&1 ".format(homeDir), shell=True)
subprocess.call("mkdir {}temp > 				/dev/null 2>&1 ".format(homeDir), shell=True)
## set permissions
subprocess.call("chmod +666 -R {} > 			/dev/null 2>&1 ".format(homeDir), shell=True)
subprocess.call("chmod +111 -R {}*.py > 		/dev/null 2>&1 ".format(homeDir), shell=True)

subprocess.call("chmod +777 -R {}soundfiles >   /dev/null 2>&1 ".format(homeDir), shell=True)
subprocess.call("chmod +777 -R {}fonts > 		/dev/null 2>&1 ".format(homeDir), shell=True)
subprocess.call("chmod +777 -R {}displayfiles > /dev/null 2>&1 ".format(homeDir), shell=True)
subprocess.call("chmod +777 -R {}fonts > 		/dev/null 2>&1 ".format(homeDir), shell=True)
subprocess.call("chmod +777  {}tm > 		/dev/null 2>&1 ".format(homeDir), shell=True)
subprocess.call("chmod +777  {}tf > 		/dev/null 2>&1 ".format(homeDir), shell=True)
subprocess.call("chmod +777  {}py > 		/dev/null 2>&1 ".format(homeDir), shell=True)
subprocess.call("chmod +777  {}ct > 		/dev/null 2>&1 ".format(homeDir), shell=True)
subprocess.call("chown -R  pi  {} ".format(homeDir), shell=True)

logger.log(30," -3-  callbeacon after chmod "  )

subprocess.call("rm {}*.pyc > 					/dev/null 2>&1 ".format(homeDir), shell=True)


subprocess.call("rm {}pygame.active".format(homeDir), shell=True)

# remember boot time / or better when did master.py start first
subprocess.call("echo {:.0f} >{}masterStartAfterboot".format(time.time(), homeDir), shell=True)

subprocess.call("rm {}restartCount > 			/dev/null 2>&1 ".format(homeDir), shell=True)
#subprocess.call("rm  /var/log/piBeacon.log >	/dev/null 2>&1 ")


# call main program
cmd1 = "cd {}; nohup /bin/bash master.sh  {} & ".format(homeDir, usePython3)
logger.log(30," -4-  callbeacon {}".format(cmd1) )

subprocess.call(cmd1, shell=True)


# remove old files 

delList =[
		"masteripAddress","beacon_batteryLevelPosition", "beacon_ignoreMAC", "beacon_offsetUUID", "beacon_UUIDtoIphone, beacon_doNotIgnore", "beacon_fastDown", "beacon_ignoreUUID", 
		"beacon_minSignalCutoff", "beacon_onlyTheseMAC", "beacon_signalDelta",  "rejects.*", 
		"logfile", "logfile-1", "call-log",  "errlog", "logfile", "master.log", 
		"alive", "interface", "beaconloop",
		"rdlidar.py","sensors.py", "iPhoneBLE.py", "getsensorvalues.py", "getBeaconParameters.py", "beepBeacon.py", "receiveGPIOcommands.py", "INPUTRotata*", "INPUTRotateSwitchGrey.py" 
		"moistureSensorAdafruit","checkAdfruitInclude.py","checkForInclude.py","checkForInclude-py3.py","checkForInclude-py2.py","neopixel.py"]
for dd in delList:
	subprocess.call("rm {}{} > /dev/null 2>&1 ".format(homeDir, dd), shell=True)

# remove old logfiles
subprocess.call("rm  /var/log/pibeacon*.log  >/dev/null 2>&1", shell=True) # it is now ...../pibeacon no .log
subprocess.call("rm -r {}logs                >/dev/null 2>&1".format(homeDir), shell=True)

logger.log(30," -5-  callbeacon finished"  )


exit()
