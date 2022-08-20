#!/usr/bin/python
# -*- coding: utf-8 -*-
import os, subprocess


if os.path.isfile("/home/pi/pibeacon/includep2.done"):
	exit()
try:
	import serial
except:
	subprocess.call("sudo apt-get install python-serial", shell=True)

try:
	import smbus2
except:
	subprocess.call("sudo pip install smbus2", shell=True)
try:
	import pexpect
except:
	subprocess.call("sudo pip install pexpect", shell=True)

ret = subprocess.Popen("which expect",shell=True,stdout=subprocess.PIPE,stderr=subprocess.PIPE).communicate()
if ret[0].find("/usr/bin/expect") == -1:
	ret = subprocess.Popen("sudo apt-get install -y expect &",shell=True,stdout=subprocess.PIPE,stderr=subprocess.PIPE).communicate()

ret = subprocess.Popen("which hcidump",shell=True,stdout=subprocess.PIPE,stderr=subprocess.PIPE).communicate()
if ret[0].find("/usr/bin/hcidump") == -1:
	ret = subprocess.Popen("sudo apt-get install -y bluez-hcidump &",shell=True,stdout=subprocess.PIPE,stderr=subprocess.PIPE).communicate()

subprocess.Popen('echo "done" > "/home/pi/pibeacon/includep2.done"',shell=True,stdout=subprocess.PIPE,stderr=subprocess.PIPE)

exit()