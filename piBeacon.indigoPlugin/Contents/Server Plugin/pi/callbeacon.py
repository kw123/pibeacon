#!/usr/bin/env python
# -*- coding: utf-8 -*-
import os
import time
import subprocess

homeDir  = "/home/pi/pibeacon/"
homeDir0 = "/home/pi/"

#set GPIOs if requested BEFOR master.py runs just once after boot 
os.system("/usr/bin/python {}doGPIOatStartup.py > /dev/null 2>&1  & ".format(homeDir))


# make new directories if they do not exist 
os.system("mkdir {} > 					/dev/null 2>&1 ".format(homeDir))
os.system("mkdir {}soundfiles > 		/dev/null 2>&1 ".format(homeDir))
os.system("mkdir {}fonts > 				/dev/null 2>&1 ".format(homeDir))
os.system("mkdir {}displayfiles > 		/dev/null 2>&1 ".format(homeDir))
os.system("mkdir {}temp > 				/dev/null 2>&1 ".format(homeDir))
## set permissions
os.system("chmod +666 -R {} > 			/dev/null 2>&1 ".format(homeDir))
os.system("chmod +111 -R {}*.py > 		/dev/null 2>&1 ".format(homeDir))

os.system("chmod +777 -R {}soundfiles > /dev/null 2>&1 ".format(homeDir))
os.system("chmod +777 -R {}fonts > 		/dev/null 2>&1 ".format(homeDir))
os.system("chmod +777 -R {}displayfiles > /dev/null 2>&1 ".format(homeDir))
os.system("chmod +777 -R {}fonts > 		/dev/null 2>&1 ".format(homeDir))
os.system("chown -R  pi  {} ".format(homeDir))


os.system("rm {}*.pyc > /dev/null 2>&1 ".format(homeDir))

os.system("rm {}pygame.active".format(homeDir))

# remember boot time / or better when did master.py start first
os.system("echo {:.0f} >{}masterStartAfterboot".format(time.time(), homeDir))

os.system("rm {}restartCount > 			/dev/null 2>&1 ".format(homeDir))
#os.system("rm  /var/log/piBeacon.log >	/dev/null 2>&1 ")

## call main program
os.system("cd {}; /usr/bin/python {}master.py & ".format(homeDir,homeDir))


# remove old files 
delList =[
		"beacon_batteryLevelPosition", "beacon_ignoreMAC", "beacon_offsetUUID", "beacon_UUIDtoIphone, beacon_doNotIgnore", "beacon_fastDown", "beacon_ignoreUUID", 
		"beacon_minSignalCutoff", "beacon_onlyTheseMAC", "beacon_signalDelta",  "rejects.*", 
		"logfile", "logfile-1", "call-log",  "errlog", "logfile", "master.log", 
		"alive", "interface", "beaconloop",
		"rdlidar.py","sensors.py", "iPhoneBLE.py", "getsensorvalues.py", "receiveGPIOcommands.py", "INPUTRotata*", "INPUTRotateSwitchGrey.py" ]
for dd in delList:
	os.system("rm {}{} > /dev/null 2>&1 ".format(homeDir, dd))

os.system("rm -r {}logs                   >/dev/null 2>&1".format(homeDir))

# check if master running, if not restart after 50-100 secs  
time.sleep(50)
for ii in range(10):
	ret = subprocess.Popen("ps -ef | grep master.py | grep -v grep", shell=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE).communicate()[0]
	if ret.find("master.py") >-1: exit()
	time.sleep(5)
print ("callbeacon       restarting master.py, seems to not be active")
os.system("cd {}; /usr/bin/python   {}master.py & ".format(homeDir,homeDir))		

exit()
