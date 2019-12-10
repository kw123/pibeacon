#!/usr/bin/env python
# -*- coding: utf-8 -*-
import os
import time
import subprocess

homeDir  = "/home/pi/pibeacon/"
homeDir0 = "/home/pi/"

#set GPIOs if requested BEFOR master.py runs just onece after boot 
os.system("/usr/bin/python {}doGPIOatStartup.py & ".format(homeDir))


# make new directories if they do not exist 
os.system("mkdir {} > /dev/null 2>&1 ".format(homeDir))
os.system("mkdir {}soundfiles > /dev/null 2>&1 ".format(homeDir))
os.system("mkdir {}fonts > /dev/null 2>&1 ".format(homeDir))
os.system("mkdir {}displayfiles > /dev/null 2>&1 ".format(homeDir))
os.system("mkdir {}temp > /dev/null 2>&1 ".format(homeDir))
## set permissions
os.system("chmod +666 -R {} > /dev/null 2>&1 ".format(homeDir))
os.system("chmod +111 -R {}*.py > /dev/null 2>&1 ".format(homeDir))

os.system("chmod +777 -R {}soundfiles > /dev/null 2>&1 ".format(homeDir))
os.system("chmod +777 -R {}fonts > /dev/null 2>&1 ".format(homeDir))
os.system("chmod +777 -R {}displayfiles > /dev/null 2>&1 ".format(homeDir))
os.system("chmod +777 -R {}fonts > /dev/null 2>&1 ".format(homeDir))
os.system("chown -R  pi  {} ".format(homeDir))
os.system("rm  {}restartCount > /dev/null 2>&1 ".format(homeDir))


os.system("rm  {}*.pyc > /dev/null 2>&1 ".format(homeDir))

os.system("rm  {}pygame.active".format(homeDir))

# rememebr boot time / or better when did master.py start first
os.system("echo {:.0f} >{}masterStartAfterboot".format(time.time(), homeDir))


## call main program
os.system("cd {}; /usr/bin/python {}master.py & ".format(homeDir,homeDir))

## clean up old files
os.system("rm  /var/log/piBeacon.log > /dev/null 2>&1 ")
os.system("rm {}beaconloop.py > /dev/null 2>&1 ".format(homeDir0))
os.system("rm {}BLEconnect.py > /dev/null 2>&1 ".format(homeDir0))
os.system("rm {}batteryLevelPosition > /dev/null 2>&1 ".format(homeDir0))
os.system("rm {}alive.ultrasoundDistance > /dev/null 2>&1 ".format(homeDir0))
os.system("rm {}alive.sensors > /dev/null 2>&1 ".format(homeDir0))
os.system("rm {}alive.sensors > /dev/null 2>&1 ".format(homeDir0))
os.system("rm {}sundial.py > /dev/null 2>&1 ".format(homeDir0))
os.system("rm {}offsetUUID > /dev/null 2>&1 ".format(homeDir0))
os.system("rm {}interfaces > /dev/null 2>&1 ".format(homeDir0))
os.system("rm {}interface.py > /dev/null 2>&1 ".format(homeDir0))
os.system("rm {}installLibs.py > /dev/null 2>&1 ".format(homeDir0))
os.system("rm {}installLibs.done > /dev/null 2>&1 ".format(homeDir0))
os.system("rm {}INPUTcount > /dev/null 2>&1 ".format(homeDir0))
os.system("rm {}ignoreUUID > /dev/null 2>&1 ".format(homeDir0))
os.system("rm {}ignoreMAC > /dev/null 2>&1 ".format(homeDir0))
os.system("rm {}getUltraSoundDistance.py>  /dev/null 2>&1 ".format(homeDir0))
os.system("rm {}getsensorvalues.py > /dev/null 2>&1 ".format(homeDir0))
os.system("rm {}fastDown > /dev/null 2>&1 ".format(homeDir0))
os.system("rm {}execcommands.current > /dev/null 2>&1 ".format(homeDir0))
os.system("rm {}doNotIgnore > /dev/null 2>&1 ".format(homeDir0))
os.system("rm {}checkLogfile.py > /dev/null 2>&1 ".format(homeDir0))
os.system("rm {}beaconsExistingHistory > /dev/null 2>&1 ".format(homeDir0))
os.system("rm {}onlyTheseMAC > /dev/null 2>&1 ".format(homeDir0))
os.system("rm {}parameters > /dev/null 2>&1 ".format(homeDir0))
os.system("rm {}playsound.py > /dev/null 2>&1 ".format(homeDir0))
os.system("rm {}receiveGPIOcommands.py > /dev/null 2>&1 ".format(homeDir0))
os.system("rm {}rejects > /dev/null 2>&1 ".format(homeDir0))
os.system("rm {}renameMeTo_mysensors.py > /dev/null 2>&1 ".format(homeDir0))
os.system("rm {}rennameMeTo_myoutput.py> /dev/null 2>&1 ".format(homeDir0))
os.system("rm {}sensors.py > /dev/null 2>&1 ".format(homeDir0))
os.system("rm {}setGPIO.py > /dev/null 2>&1 ".format(homeDir0))
os.system("rm {}setmcp4725.py > /dev/null 2>&1 ".format(homeDir0))
os.system("rm {}signalDelta > /dev/null 2>&1 ".format(homeDir0))
os.system("rm {}ultrasoundDistance.py > /dev/null 2>&1 ".format(homeDir0))
os.system("rm {}UUIDtoIphone > /dev/null 2>&1 ".format(homeDir0))
os.system("rm {}wpa_supplicant.conf > /dev/null 2>&1 ".format(homeDir0))
os.system("rm {}getsensorvalues.dat > /dev/null 2>&1 ".format(homeDir0))
os.system("rm {}execcommands.py > /dev/null 2>&1 ".format(homeDir0))
os.system("rm -r {}soundfiles > /dev/null 2>&1 ".format(homeDir0))

os.system("rm  {}sensors.py > /dev/null 2>&1 ".format(homeDir))
os.system("rm  {}beacon_batteryLevelPosition > /dev/null 2>&1".format(homeDir))	
os.system("rm  {}beacon_ignoreMAC >	/dev/null 2>&1".format(homeDir))  
os.system("rm  {}beacon_offsetUUID  >	  /dev/null 2>&1".format(homeDir))	
os.system("rm  {}beacon_UUIDtoIphone>  /dev/null 2>&1".format(homeDir))
os.system("rm  {}beacon_doNotIgnore >  /dev/null 2>&1".format(homeDir))	
os.system("rm  {}beacon_fastDown > /dev/null 2>&1".format(homeDir))	
os.system("rm  {}beacon_ignoreUUID >	 /dev/null 2>&1".format(homeDir))  
os.system("rm  {}beacon_minSignalCutoff >  /dev/null 2>&1".format(homeDir))	
os.system("rm  {}beacon_onlyTheseMAC >  /dev/null 2>&1".format(homeDir))	 
os.system("rm  {}beacon_signalDelta >  /dev/null 2>&1".format(homeDir))
os.system("rm -r {}logs                   >/dev/null 2>&1".format(homeDir))
os.system("rm  {}iPhoneBLE.py             >/dev/null 2>&1".format(homeDir))
os.system("rm  {}rejects.*                >/dev/null 2>&1".format(homeDir))
os.system("rm  {}logfile                  >/dev/null 2>&1".format(homeDir))
os.system("rm  {}logfile-1                >/dev/null 2>&1".format(homeDir))
os.system("rm  {}call-log                 >/dev/null 2>&1".format(homeDir))
os.system("rm  {}alive                    >/dev/null 2>&1".format(homeDir))
os.system("rm  {}master.log               >/dev/null 2>&1".format(homeDir))
os.system("rm  {}interface                >/dev/null 2>&1".format(homeDir))
os.system("rm  {}logfile                  >/dev/null 2>&1".format(homeDir))
os.system("rm  {}beaconloop               >/dev/null 2>&1".format(homeDir))
os.system("rm  {}errlog                   >/dev/null 2>&1".format(homeDir))
os.system("rm  {}getsensorvalues.py       >/dev/null 2>&1".format(homeDir))
os.system("rm  {}receiveGPIOcommands.py   >/dev/null 2>&1".format(homeDir))
os.system("rm  {}rennameMeTo_myoutput.py  >/dev/null 2>&1".format(homeDir))
os.system("rm  {}renameMyTo_mysensors.py  >/dev/null 2>&1".format(homeDir))
os.system("rm  {}INPUTRotata*             >/dev/null 2>&1".format(homeDir))
os.system("rm  {}INPUTRotateSwitchGrey.py >/dev/null 2>&1".format(homeDir))

time.sleep(50)
ret = subprocess.Popen("ps -ef | grep master.py | grep -v grep", shell=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE).communicate()[0]
lines = ret.split("\n")
for line in lines :
	if len(line) < 10 : continue
	exit()
print ("callbeacon       restarting master.py, seems to not be active")
os.system("cd {}; /usr/bin/python   {}master.py & ".format(homeDir,homeDir))		

exit()
