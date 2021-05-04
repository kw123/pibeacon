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

pipList	 = (subprocess.Popen("/usr/bin/pip3 list" ,shell=True,stdout=subprocess.PIPE,stderr=subprocess.PIPE).communicate()[0].decode('utf-8'))


foundOne = False
for xx in ["adafruit-circuitpython-seesaw","adafruit-circuitpython-lidarlite","adafruit-circuitpython-dht"]:
	if xx not in pipList:
		foundOne = True
		break
print (foundOne)

libgpiod2 = False
aptList	 = (subprocess.Popen("dpkg -s libgpiod2 | grep 'install ok installed'" ,shell=True,stdout=subprocess.PIPE,stderr=subprocess.PIPE).communicate()[0].decode('utf-8'))

if  aptList.find("install ok installed") == -1:
	libgpiod2 = True


if not foundOne and not aptList: 
	print ("check for pip3 includees, nothing found to install")
	exit()


sleepTime = 20


try:
	from adafruit_seesaw.seesaw import Seesaw
except:
	time.sleep(sleepTime)
	sleepTime -= 20
	if "adafruit-circuitpython-seesaw" not in pipList:
		print (" install adafruit-circuitpython-seesaw")
		subprocess.Popen("sudo pip3 install adafruit-circuitpython-seesaw",shell=True, stdout=subprocess.PIPE).communicate()
	if "adafruit-blinka" not in pipList:
		print (" install adafruit-blinka")
		subprocess.Popen("sudo pip3 install adafruit-blinka",shell=True, stdout=subprocess.PIPE).communicate()

try:
	import adafruit_lidarlite
except:
	time.sleep(max(0,sleepTime))
	sleepTime -= 20
	if "adafruit-circuitpython-lidarlite" not in pipList:
		print(" installing adafruit-circuitpython-lidarlite\n")
		subprocess.Popen("sudo pip3 install adafruit-circuitpython-lidarlite &",shell=True)

try:
	import adafruit_dht
except:
	time.sleep(max(0,sleepTime))
	sleepTime -= 20
	if "adafruit-circuitpython-dht" not in pipList:
		print(" installing adafruit-circuitpython-dht\n")
		subprocess.Popen("sudo pip3 install adafruit-circuitpython-dht &",shell=True)

if libgpiod2:
		print(" installing libgpiod2\n")
		subprocess.Popen("sudo apt-get install libgpiod2 &",shell=True)

exit()


