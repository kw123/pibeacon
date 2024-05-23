#!/usr/bin/python3
# -*- coding: utf-8 -*-
import os, time, subprocess, logging

logging.basicConfig(level=logging.INFO, filename= "/var/log/pibeacon",format='%(asctime)s %(module)-17s %(funcName)-22s L:%(lineno)-4d Lv:%(levelno)s %(message)s', datefmt='%d-%H:%M:%S')
logger = logging.getLogger(__name__)

####-------------------------------------------------------------------------####
def readPopen(cmd,doPrint= True):
	try:
		logger.log(30,"doing:  {}".format(cmd) )
		ret, err = subprocess.Popen(cmd, shell=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE).communicate()
		if doPrint: logger.log(30,"ret: {} {}".format(ret, err ) )
		return ret.decode('utf_8'), err.decode('utf_8')
	except Exception as e:
		logger.log(20,"", exc_info=True)

def checkIfOSlt9():
	osInfo	 = readPopen("cat /etc/os-release",doPrint=False)[0].strip("\n").split("\n")
	for line in osInfo:
		if line .find("VERSION_ID=") == 0:
			return int( line.strip('"').split('="')[1] )
	return 0

def checkOsVersionis3():
	return int(sys.version[0]) >= 3



def execInstall():

	v = checkIfOSlt9() 

	logger.log(20,"------ starting on os v :{}".format(v) )

	if v < 9:
		logger.log(20,"finished, due to OS < 9, py 3 not completely installed" )
		readPopen('echo "done" > "/home/pi/pibeacon/includep3.done"')
		exit()

		usebreakOption = ""

	if v >11: 	usebreakOption = "--break-system-packages "
	else:		usebreakOption = ""
	logger.log(20,"------ starting on os v :{} withoption: --{}".format(v, usebreakOption) )


	for ii in range(10):
		logger.log(20,"check if apt-get ist still running"  )
		ret = readPopen("ps -ef | grep apt-get")
		if ret[0].find("apt-get install") == -1:
			break
		time.sleep(20)		

	if True:
		ret = readPopen("gpio -v",doPrint=False)
		if ret[0].find("version:") == -1:
			readPopen("rm -R /tmp/wiringPi")
			installGPIO = "cd /tmp; wget https://project-downloads.drogon.net/wiringpi-latest.deb; sudo dpkg -i wiringpi-latest.deb ; rm -R /tmp/wiringPi"
			ret = readPopen(installGPIO)

	if True:
		logger.log(20,"check RPi.GPIO "  )
		try:
			import RPi.GPIO as GPIO
		except:
			ret = readPopen("sudo apt-get install python3-dev python3-rpi.gpio")


	if True:
		logger.log(20,"check hcidump"  )
		ret = readPopen("which hcidump")
		if ret[0].find("hcidump") == -1:
			readPopen("sudo apt-get install -y bluez-hcidump")

	if True:
		logger.log(20,"check adafruit-circuitpython-seesaw"  )
		try:
			from adafruit_seesaw.seesaw import Seesaw
		except:
			readPopen("sudo pip3 install {}  adafruit-circuitpython-seesaw".format(usebreakOption))

	if True:
		logger.log(20,"check board neopixel"  )
		try:
			import board
			import neopixel
		except Exception as e:
			readPopen("sudo pip3 install "+usebreakOption+ " rpi_ws281x adafruit-circuitpython-neopixel;sudo pip3 install  "+usebreakOption+ "  adafruit-blinka") # it is now ...../pibeacon no .log



	if True:
		logger.log(20,"check adafruit-circuitpython-lidarlite"  )
		try:
			import adafruit_lidarlite
		except:
			readPopen("sudo pip3 install  "+usebreakOption+ "  adafruit-circuitpython-lidarlite")

	if True:
		logger.log(20,"check adafruit_tmp117"  )
		try:
			import adafruit_tmp117
		except:
			readPopen("sudo pip3 install  "+usebreakOption+ " adafruit-circuitpython-tmp117")


	if True:
		logger.log(20,"check adafruit-circuitpython-dht"  )
		try:
			import adafruit_dht
		except:
			readPopen("sudo pip3 install  "+usebreakOption+ "   adafruit-circuitpython-dht")



	if True:
		logger.log(20,"check Adafruit_DHT"  )
		try:
			import Adafruit_DHT
		except Exception as e:
			readPopen("sudo pip3 install  "+usebreakOption+ " Adafruit_DHT") # it is now ...../pibeacon no .log

	if True:
		logger.log(20,"check pexpect"  )
		try:
			import pexpect
		except:
			readPopen("sudo pip3 install  "+usebreakOption+ "  pexpect")

	if True:
		logger.log(20,"check expect"  )
		ret = readPopen("which expect")
		if ret[0].find("/usr/bin/expect") == -1:
			readPopen("sudo apt-get install -y expect")



	if True:
		logger.log(20,"check libgpiod2"  )
		aptList	 = readPopen("dpkg -s libgpiod2 | grep 'install ok installed'")[0]

		if aptList.find("install ok installed") == -1:
			readPopen("sudo apt-get install libgpiod2 &")


	readPopen('echo "done" > "/home/pi/pibeacon/includep3.done"')
	logger.log(20,"finished")

execInstall()


