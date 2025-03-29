#!/usr/bin/python
# -*- coding: utf-8 -*-
import os, time, subprocess, logging, sys

logging.basicConfig(level=logging.INFO, filename= "/var/log/pibeacon",format='%(asctime)s %(module)-17s %(funcName)-22s L:%(lineno)-4d Lv:%(levelno)s %(message)s', datefmt='%d-%H:%M:%S')
logger = logging.getLogger(__name__)


def readPopen(cmd):
		try:
			logger.log(30,"doing:  {}".format(cmd) )
			ret, err = subprocess.Popen(cmd, shell=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE).communicate()
			logger.log(30,"ret: {} {}".format(ret, err ) )
			return ret.decode('utf_8'), err.decode('utf_8')
		except Exception as e:
			logger.log(20,"", exc_info=True)

def checkIfPy3():
	osInfo	 = readPopen("cat /etc/os-release")[0].strip("\n").split("\n")
	for line in osInfo:
		if line .find("VERSION_ID=") == 0:
			if int( line.strip('"').split('="')[1] ) >=11: return True
	return False

def checkOsVersionis3():
	return sys.version[0] == "3"


def execInstall():

	if checkOsVersionis3: 
		logger.log(30,"python2 not installed stopping checking for include py2 "  )
		readPopen('echo "done" > "/home/pi/pibeacon/includepy2.done"')
		exit()

	if checkIfPy3():
		logger.log(30,"must use py3 due to opsys version < 10 "  )
		readPopen('echo "done" > "/home/pi/pibeacon/includepy2.done"')
		exit()


	for ii in range(20):
		logger.log(20,"check if apt-get ist still running"  )
		ret = readPopen("ps -ef | grep apt-get")
		if ret[0].find("apt-get install") == -1:
			break
		time.sleep(10)		


	if True:
		logger.log(20,"check if apt install  is ok"  )
		ret = readPopen("sudo apt --fix-broken install  -y &")


	if False:
		logger.log(20,"check python-serial"  )
		try:
			import serial
		except Exception as e:
			logger.log(20,"", exc_info=True)
			readPopen("sudo apt-get install python-serial")

	if True:
		logger.log(20,"check smbus2"  )
		try:
			import smbus2
		except Exception as e:
			logger.log(20,"", exc_info=True)
			readPopen("sudo pip install smbus2")

	if True:
		logger.log(20,"check hcidump"  )
		ret = readPopen("which hcidump")
		if ret[0].find("/usr/bin/hcidump") == -1:
			readPopen("sudo apt-get install -y bluez-hcidump")

	if True:
		logger.log(20,"check pigpio"  )
		try:
			import RPi.GPIO as GPIO
		except:
			ret = readPopen("sudo apt-get install -y pigpio python-pigpio ")

	if True:
		logger.log(20,"check RPi.GPIO "  )
		try:		
			import RPi.GPIO as GPIO
		except Exception as e:
			logger.log(20,"", exc_info=True)
			ret = readPopen("sudo apt-get install python3-dev python3-rpi.gpio")

	if True:
		logger.log(20,"check pexpect"  )
		try:
			import pexpect
		except Exception as e:
			logger.log(20,"", exc_info=True)
			readPopen("sudo pip install pexpect")

	if False:
		logger.log(20,"check import Adafruit_DHT"  )
		try:
			import Adafruit_DHT
		except Exception as e:
			logger.log(20,"", exc_info=True)
			readPopen("sudo pip install Adafruit_DHT ")

	if True:
		logger.log(20,"check expect"  )
		ret = readPopen("which expect")
		if ret[0].find("/usr/bin/expect") == -1:
			readPopen("sudo apt-get install -y expect")


	logger.log(20,"check if apt install  is ok"  )
	ret = readPopen("sudo apt --fix-broken install  -y")
	logger.log(20,"check if apt autoremove  is ok"  )
	ret = readPopen("sudo apt autoremove -y &")

	readPopen('echo "done" > "/home/pi/pibeacon/includepy2.done"')

	logger.log(20,"finished" )

execInstall()
