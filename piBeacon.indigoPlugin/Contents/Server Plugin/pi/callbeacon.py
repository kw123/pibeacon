#!/usr/bin/env python
# -*- coding: utf-8 -*-
import os
import time
import subprocess

homeDir  = "/home/pi/pibeacon/"
homeDir0 = "/home/pi/"

#set GPIOs if requested BEFOR master.py runs just once after boot 
subprocess.call("/usr/bin/python {}doGPIOatStartup.py > /dev/null 2>&1  & ".format(homeDir), shell=True)


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
subprocess.call("chown -R  pi  {} ".format(homeDir), shell=True)


subprocess.call("rm {}*.pyc > 					/dev/null 2>&1 ".format(homeDir), shell=True)

subprocess.call("rm {}pygame.active".format(homeDir), shell=True)

# remember boot time / or better when did master.py start first
subprocess.call("echo {:.0f} >{}masterStartAfterboot".format(time.time(), homeDir), shell=True)

subprocess.call("rm {}restartCount > 			/dev/null 2>&1 ".format(homeDir), shell=True)
#subprocess.call("rm  /var/log/piBeacon.log >	/dev/null 2>&1 ")

## call main program
subprocess.call("cd {}; nohup /bin/bash master.sh & ".format(homeDir), shell=True)


# remove old files 

delList =[
		"masteripAddress","beacon_batteryLevelPosition", "beacon_ignoreMAC", "beacon_offsetUUID", "beacon_UUIDtoIphone, beacon_doNotIgnore", "beacon_fastDown", "beacon_ignoreUUID", 
		"beacon_minSignalCutoff", "beacon_onlyTheseMAC", "beacon_signalDelta",  "rejects.*", 
		"logfile", "logfile-1", "call-log",  "errlog", "logfile", "master.log", 
		"alive", "interface", "beaconloop",
		"rdlidar.py","sensors.py", "iPhoneBLE.py", "getsensorvalues.py", "receiveGPIOcommands.py", "INPUTRotata*", "INPUTRotateSwitchGrey.py" 
		"moistureSensorAdafruit","checkAdfruitInclude.py","checkForInclude.py"]
for dd in delList:
	subprocess.call("rm {}{} > /dev/null 2>&1 ".format(homeDir, dd), shell=True)

# remove old logfiles
subprocess.call("rm  /var/log/pibeacon*.log  >/dev/null 2>&1", shell=True) # it is now ...../pibeacon no .log
subprocess.call("rm -r {}logs               >/dev/null 2>&1".format(homeDir), shell=True)


exit()
