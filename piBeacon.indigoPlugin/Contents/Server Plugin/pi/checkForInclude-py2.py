#!/usr/bin/python
# -*- coding: utf-8 -*-
import	os, time


sleepTime = 30
try:
	pass #from adafruit_seesaw.seesaw import Seesaw
except:
	time.sleep(sleepTime)
	sleepTime -= 30
	#os.system("sudo pip3 install adafruit-circuitpython-seesawimport busio &")
exit()