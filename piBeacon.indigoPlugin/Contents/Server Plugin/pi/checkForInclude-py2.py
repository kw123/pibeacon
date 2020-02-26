#!/usr/bin/python
# -*- coding: utf-8 -*-
import	os

try:
	import serial
except:
	subprocess.call("sudo apt-get install python-serial", shell=True)

try:
	import smbus2
except:
	subprocess.call("sudo pip install smbus2", shell=True)

exit()