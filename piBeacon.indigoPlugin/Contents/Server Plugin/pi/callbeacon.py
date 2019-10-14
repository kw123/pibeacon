#!/usr/bin/env python
# -*- coding: utf-8 -*-
import os
import time
import subprocess


#set GPIOs if requested BEFOR master.py runs just onece after boot 
os.system("/usr/bin/python /home/pi/pibeacon/doGPIOatStartup.py & ")


# make new directories if they do not exist 
os.system("mkdir /home/pi/pibeacon/ > /dev/null 2>&1 ")
os.system("mkdir /home/pi/pibeacon/soundfiles > /dev/null 2>&1 ")
os.system("mkdir /home/pi/pibeacon/fonts > /dev/null 2>&1 ")
os.system("mkdir /home/pi/pibeacon/displayfiles > /dev/null 2>&1 ")
os.system("mkdir /home/pi/pibeacon/temp > /dev/null 2>&1 ")
## set permissions
os.system("chmod +666 -R /home/pi/pibeacon > /dev/null 2>&1 ")
os.system("chmod +111 -R /home/pi/pibeacon/*.py > /dev/null 2>&1 ")

os.system("chmod +777 -R /home/pi/pibeacon/soundfiles > /dev/null 2>&1 ")
os.system("chmod +777 -R /home/pi/pibeacon/fonts > /dev/null 2>&1 ")
os.system("chmod +777 -R /home/pi/pibeacon/displayfiles > /dev/null 2>&1 ")
os.system("chmod +777 -R /home/pi/pibeacon/fonts > /dev/null 2>&1 ")
os.system("chown -R  pi  /home/pi/pibeacon/ ")
os.system("rm  /home/pi/pibeacon/restartCount > /dev/null 2>&1 ")

os.system("rm  /home/pi/pibeacon/*.pyc > /dev/null 2>&1 ")

os.system("rm  /home/pi/pibeacon/pygame.active")

## call main program
os.system("cd /home/pi/pibeacon; /usr/bin/python /home/pi/pibeacon/master.py & ")

## clean up old files
os.system("rm  /var/log/piBeacon.log > /dev/null 2>&1 ")
os.system("rm  /home/pi/beaconloop.py > /dev/null 2>&1 ")
os.system("rm  /home/pi/BLEconnect.py > /dev/null 2>&1 ")
os.system("rm  /home/pi/batteryLevelPosition > /dev/null 2>&1 ")
os.system("rm  /home/pi/alive.ultrasoundDistance > /dev/null 2>&1 ")
os.system("rm  /home/pi/alive.sensors > /dev/null 2>&1 ")
os.system("rm  /home/pi/alive.sensors > /dev/null 2>&1 ")
os.system("rm  /home/pi/sundial.py > /dev/null 2>&1 ")
os.system("rm  /home/pi/offsetUUID > /dev/null 2>&1 ")
os.system("rm  /home/pi/interfaces > /dev/null 2>&1 ")
os.system("rm  /home/pi/interface.py > /dev/null 2>&1 ")
os.system("rm  /home/pi/installLibs.py > /dev/null 2>&1 ")
os.system("rm  /home/pi/installLibs.done > /dev/null 2>&1 ")
os.system("rm  /home/pi/INPUTcount > /dev/null 2>&1 ")
os.system("rm  /home/pi/ignoreUUID > /dev/null 2>&1 ")
os.system("rm  /home/pi/ignoreMAC > /dev/null 2>&1 ")
os.system("rm  /home/pi/getUltraSoundDistance.py>  /dev/null 2>&1 ")
os.system("rm  /home/pi/getsensorvalues.py > /dev/null 2>&1 ")
os.system("rm  /home/pi/fastDown > /dev/null 2>&1 ")
os.system("rm  /home/pi/execcommands.current > /dev/null 2>&1 ")
os.system("rm  /home/pi/doNotIgnore > /dev/null 2>&1 ")
os.system("rm  /home/pi/checkLogfile.py > /dev/null 2>&1 ")
os.system("rm  /home/pi/beaconsExistingHistory > /dev/null 2>&1 ")
os.system("rm  /home/pi/onlyTheseMAC > /dev/null 2>&1 ")
os.system("rm  /home/pi/parameters > /dev/null 2>&1 ")
os.system("rm  /home/pi/playsound.py > /dev/null 2>&1 ")
os.system("rm  /home/pi/receiveGPIOcommands.py > /dev/null 2>&1 ")
os.system("rm  /home/pi/rejects > /dev/null 2>&1 ")
os.system("rm  /home/pi/renameMeTo_mysensors.py > /dev/null 2>&1 ")
os.system("rm  /home/pi/rennameMeTo_myoutput.py> /dev/null 2>&1 ")
os.system("rm  /home/pi/sensors.py > /dev/null 2>&1 ")
os.system("rm  /home/pi/setGPIO.py > /dev/null 2>&1 ")
os.system("rm  /home/pi/setmcp4725.py > /dev/null 2>&1 ")
os.system("rm  /home/pi/signalDelta > /dev/null 2>&1 ")
os.system("rm  /home/pi/ultrasoundDistance.py > /dev/null 2>&1 ")
os.system("rm  /home/pi/UUIDtoIphone > /dev/null 2>&1 ")
os.system("rm  /home/pi/wpa_supplicant.conf > /dev/null 2>&1 ")
os.system("rm  /home/pi/getsensorvalues.dat > /dev/null 2>&1 ")
os.system("rm  /home/pi/execcommands.py > /dev/null 2>&1 ")
os.system("rm  /home/pi/pibeacon/sensors.py > /dev/null 2>&1 ")
os.system("rm -r /home/pi/soundfiles > /dev/null 2>&1 ")
os.system("rm  /home/pi/pibeacon/beacon_batteryLevelPosition > /dev/null 2>&1")	
os.system("rm  /home/pi/pibeacon/beacon_ignoreMAC >	/dev/null 2>&1")  
os.system("rm  /home/pi/pibeacon/beacon_offsetUUID  >	  /dev/null 2>&1")	
os.system("rm  /home/pi/pibeacon/beacon_UUIDtoIphone>  /dev/null 2>&1")
os.system("rm  /home/pi/pibeacon/beacon_doNotIgnore >  /dev/null 2>&1")	
os.system("rm  /home/pi/pibeacon/beacon_fastDown > /dev/null 2>&1")	
os.system("rm  /home/pi/pibeacon/beacon_ignoreUUID >	 /dev/null 2>&1")  
os.system("rm  /home/pi/pibeacon/beacon_minSignalCutoff >  /dev/null 2>&1")	
os.system("rm  /home/pi/pibeacon/beacon_onlyTheseMAC >  /dev/null 2>&1")	 
os.system("rm  /home/pi/pibeacon/beacon_signalDelta >  /dev/null 2>&1")
os.system("rm -r /home/pi/pibeacon/logs                   >/dev/null 2>&1")
os.system("rm  /home/pi/pibeacon/iPhoneBLE.py             >/dev/null 2>&1")
os.system("rm  /home/pi/pibeacon/rejects.*                >/dev/null 2>&1")
os.system("rm  /home/pi/pibeacon/logfile                  >/dev/null 2>&1")
os.system("rm  /home/pi/pibeacon/logfile-1                >/dev/null 2>&1")
os.system("rm  /home/pi/pibeacon/call-log                 >/dev/null 2>&1")
os.system("rm  /home/pi/pibeacon/alive                    >/dev/null 2>&1")
os.system("rm  /home/pi/pibeacon/master.log               >/dev/null 2>&1")
os.system("rm  /home/pi/pibeacon/interface                >/dev/null 2>&1")
os.system("rm  /home/pi/pibeacon/logfile                  >/dev/null 2>&1")
os.system("rm  /home/pi/pibeacon/beaconloop               >/dev/null 2>&1")
os.system("rm  /home/pi/pibeacon/errlog                   >/dev/null 2>&1")
os.system("rm  /home/pi/pibeacon/getsensorvalues.py       >/dev/null 2>&1")
os.system("rm  /home/pi/pibeacon/receiveGPIOcommands.py   >/dev/null 2>&1")
os.system("rm  /home/pi/pibeacon/rennameMeTo_myoutput.py  >/dev/null 2>&1")
os.system("rm  /home/pi/pibeacon/renameMyTo_mysensors.py  >/dev/null 2>&1")
os.system("rm  /home/pi/pibeacon/INPUTRotata*             >/dev/null 2>&1")
os.system("rm  /home/pi/pibeacon/INPUTRotateSwitchGrey.py >/dev/null 2>&1")

time.sleep(50)
ret = subprocess.Popen("ps -ef | grep master.py | grep -v grep", shell=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE).communicate()[0]
lines = ret.split("\n")
for line in lines :
	if len(line) < 10 : continue
	exit()
print ("callbeacon       restarting master.py, seems to not be active")
os.system("cd /home/pi/pibeacon; /usr/bin/python   /home/pi/pibeacon/master.py & ")		

exit()
