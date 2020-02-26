#!/usr/bin/python
# -*- coding: utf-8 -*-
import	os, time, subprocess



osInfo	 = (subprocess.Popen("cat /etc/os-release" ,shell=True,stdout=subprocess.PIPE,stderr=subprocess.PIPE).communicate()[0].decode('utf-8')).strip("\n").split("\n")
for line in osInfo:
	if line .find("VERSION_ID=") == 0:
		os = int( line.strip('"').split('="')[1] )
if os < 9: 
	print (" os is to old for adafruit p3 stuff, exit")
	exit()


sleepTime = 30
try:
	from adafruit_seesaw.seesaw import Seesaw
except:
	time.sleep(sleepTime)
	sleepTime -= 30
	print (" install adafruit-circuitpython-seesaw")
	subprocess.Popen("sudo pip3 install adafruit-circuitpython-seesaw",shell=True, stdout=subprocess.PIPE).communicate()
	print (" install adafruit-blinka")
	subprocess.Popen("sudo pip3 install adafruit-blinka",shell=True, stdout=subprocess.PIPE).communicate()

try:
	import adafruit_lidarlite
except:
	time.sleep(max(0,sleepTime))
	subprocess.Popen("sudo pip3 install adafruit-circuitpython-lidarlite &",shell=True)
exit()