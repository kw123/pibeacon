#!/usr/bin/ python
import os, sys
try:
	import serial
except:
	os.system("sudo apt-get install python-serial")

try:
	import smbus2
except:
	os.system("sudo pip install smbus2")
	
sys.exit(0)		   
