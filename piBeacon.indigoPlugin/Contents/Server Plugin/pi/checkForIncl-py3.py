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
		ret = ret.decode('utf_8')
		err = err.decode('utf_8')
		if doPrint: logger.log(30,"result: {} {}".format(ret, err ) )
		return ret, err
	except Exception as e:
		logger.log(20,"", exc_info=True)

def readFile(fName):
	try:
		f=open(fName,"r")
		ret = f.read()
		f.close()
		return ret
	except Exception as e:
		logger.log(20,"", exc_info=True)
	return ""

def writeFile(fName,NewFile):
	try:
		f=open(fName,"w")
		f.write(NewFile)
		f.close()
		return 
	except Exception as e:
		logger.log(20,"", exc_info=True)
	return 

def checkIfOSlt9():
	osInfo	 = readPopen("cat /etc/os-release",doPrint=False)[0].strip("\n").split("\n")
	for line in osInfo:
		if line .find("VERSION_ID=") == 0:
			return int( line.strip('"').split('="')[1] )
	return 0

def checkOsVersionis3():
	return int(sys.version[0]) >= 3



def execInstall():

	notSupported = ["DHT","GPIO"]
	v = checkIfOSlt9() 

	if v < 9:
		logger.log(20,"finished, due to OS < 9, py 3 not completely installed" )
		readPopen('echo "done" > "/home/pi/pibeacon/includepy3.done"')
		exit()

	if v >11: 	usebreakOption = "--break-system-packages "
	else:		usebreakOption = ""

	logger.log(20,"------ starting on os v :{} not suported:{}, withoption: --{}".format(v, notSupported, usebreakOption) )



	for ii in range(20):
		logger.log(20,"check if apt-get ist still running"  )
		ret = readPopen("ps -ef | grep apt-get")
		if ret[0].find("apt-get install") == -1:
			break
		time.sleep(10)		

	if True:
		logger.log(20,"check if apt install  is ok"  )
		ret = readPopen("sudo apt --fix-broken install  -y")
		ret = readPopen("sudo apt autoremove -y")


	if "GPIO" not in notSupported:
		ret = readPopen("gpio -v",doPrint=False)
		if ret[0].find("version:") == -1:
			readPopen("rm -R /tmp/wiringPi")
			installGPIO = "cd /tmp; wget https://project-downloads.drogon.net/wiringpi-latest.deb; sudo dpkg -i wiringpi-latest.deb ; rm -R /tmp/wiringPi"
			ret = readPopen(installGPIO)

	if "GPIO" not in notSupported:
		logger.log(20,"check RPi.GPIO "  )
		try:
			import RPi.GPIO as GPIO
		except:
			ret = readPopen("sudo apt-get install -y python3-dev python3-rpi.gpio")


	if "libgpiod2" not in notSupported:
		logger.log(20,"check libgpiod2"  )
		aptList	 = readPopen("dpkg -s libgpiod2 | grep 'install ok installed'")[0]

		if aptList.find("install ok installed") == -1:
			logger.log(20,"sudo apt-get install libgpiod2"  )
			readPopen("sudo apt-get install libgpiod2")


	if "hcidump" not in notSupported:
		logger.log(20,"check hcidump"  )
		ret = readPopen("which hcidump")
		if ret[0].find("hcidump") == -1:
			for ii in range(5):
				readPopen("sudo apt-get install -y bluez-hcidump" )
				ret = readPopen("which hcidump")
				if ret[0].find("hcidump") == -1:
					logger.log(30,"hcidump not properly installed, try again"  )
					time.sleep(20)
				else:
					logger.log(30,"hcidump installed"  )
					break



	if "seesaw" not in notSupported:
		logger.log(20,"check adafruit-circuitpython-seesaw"  )
		try:
			from adafruit_seesaw.seesaw import Seesaw
		except:
			logger.log(20,"sudo pip3 install {}  adafruit-circuitpython-seesaw".format(usebreakOption) )
			readPopen("sudo pip3 install {}  adafruit-circuitpython-seesaw".format(usebreakOption))


	if "pigpio" not in notSupported:
		logger.log(20,"check pigpio"  )
		try:
			if subprocess.Popen("/usr/bin/ps -ef | /usr/bin/grep pigpiod  | /usr/bin/grep -v grep",shell=True,stdout=subprocess.PIPE,stderr=subprocess.PIPE).communicate()[0].decode('utf-8').find("pigpiod")< 5:
				subprocess.call("/usr/bin/sudo /usr/bin/pigpiod &", shell=True)
				time.sleep(0.5)
			import pigpio
		except:
			logger.log(20,"sudo apt-get install -y pigpio python3-pigpio ".format(usebreakOption) )
			ret = readPopen("sudo apt-get install -y pigpio python3-pigpio ")


	if "neopixel" not in notSupported:
		logger.log(20,"check board neopixel"  )
		try:
			import board
			import neopixel
		except Exception as e:
			logger.log(20,"sudo pip3 install "+usebreakOption+ " rpi_ws281x adafruit-circuitpython-neopixel;sudo pip3 install  "+usebreakOption+ "  adafruit-blinka" )
			readPopen("sudo pip3 install "+usebreakOption+ " rpi_ws281x adafruit-circuitpython-neopixel;sudo pip3 install  "+usebreakOption+ "  adafruit-blinka") # it is now ...../pibeacon no .log


	if "lidarlite" not in notSupported:
		logger.log(20,"check adafruit-circuitpython-lidarlite"  )
		try:
			import adafruit_lidarlite
		except:
			logger.log(20,"sudo pip3 install  "+usebreakOption+ "  adafruit-circuitpython-lidarlite" )
			readPopen("sudo pip3 install  "+usebreakOption+ "  adafruit-circuitpython-lidarlite")


	if "tmp117" not in notSupported:
		logger.log(20,"check adafruit_tmp117"  )
		try:
			import adafruit_tmp117
		except:
			logger.log(20,"sudo pip3 install  "+usebreakOption+ " adafruit-circuitpython-tmp117" )
			readPopen("sudo pip3 install  "+usebreakOption+ " adafruit-circuitpython-tmp117")


	if "dht" not in notSupported:
		logger.log(20,"check adafruit-circuitpython-dht"  )
		try:
			import adafruit_dht
		except:
			logger.log(20,"sudo pip3 install  "+usebreakOption+ "   adafruit-circuitpython-dht" )
			readPopen("sudo pip3 install  "+usebreakOption+ "   adafruit-circuitpython-dht")


	if "DHT" not in notSupported:
		logger.log(20,"check Adafruit_DHT"  )
		try:
			import Adafruit_DHT
		except Exception as e:
			logger.log(20,"sudo pip3 install  "+usebreakOption+ " Adafruit_DHT" )
			readPopen("sudo pip3 install  "+usebreakOption+ " Adafruit_DHT") 


	if "pexpect" not in notSupported:
		logger.log(20,"check pexpect"  )
		try:
			import pexpect
		except:
			logger.log(20,"sudo pip3 install  "+usebreakOption+ " adafruit-circuitpython-tmp117" )
			readPopen("sudo pip3 install  "+usebreakOption+ "  pexpect")


	if "expect" not in notSupported:
		logger.log(20,"check expect"  )
		ret = readPopen("which expect")
		if ret[0].find("/usr/bin/expect") == -1:
			readPopen("sudo apt-get install -y expect")


	if True:
		logger.log(20,"check if apt install  is ok"  )
		ret = readPopen("sudo apt --fix-broken install  -y") # wait until finsihed
		logger.log(20,"check if apt autoremove  is ok"  )
		ret = readPopen("sudo apt autoremove -y &")

	readPopen('echo "done" > "/home/pi/pibeacon/includepy3.done"')

	logger.log(20,"finished")

execInstall()


