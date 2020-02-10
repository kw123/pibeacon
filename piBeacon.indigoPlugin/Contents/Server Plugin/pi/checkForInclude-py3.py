#!/usr/bin/python
# -*- coding: utf-8 -*-
import	os, time


sleepTime = 30
try:
	from adafruit_seesaw.seesaw import Seesaw
except:
	time.sleep(sleepTime)
	sleepTime -= 30
	print (" install adafruit-circuitpython-seesaw")
	os.system("sudo pip3 install adafruit-circuitpython-seesaw")
	print (" install adafruit-blinka")
	os.system("sudo pip3 install adafruit-blinka")
try:
	import adafruit_lidarlite
except:
	time.sleep(max(0,sleepTime))
	os.system("sudo pip3 install adafruit-circuitpython-lidarlite &")
exit()