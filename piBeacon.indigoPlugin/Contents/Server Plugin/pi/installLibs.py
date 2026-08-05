#!/usr/bin/env python
# -*- coding: utf-8 -*-
# by Karl Wachs
# feb 5 2016
# version 0.9
##
##
##
import sys, os, subprocess, copy
import time,datetime
import json
sys.path.append(os.getcwd())
import	piBeaconUtils	as U
import	piBeaconGlobals as G

G.program  = "installLibs"



def setupLibs(upgradeOpSys):
		"""Installs and configures the sensor software libraries on a Raspberry Pi: checks network/nameserver, enables I2C/SPI/1-wire in boot and module config files, optionally runs apt-get upgrades, and installs Python dev tools, bluez, smbus, i2c-tools, and Adafruit GPIO/SPI libraries. Writes a completion marker file and reports whether a reboot is required.

		Inputs:
		    upgradeOpSys (str): Flag string (e.g. 'force', 'dist-upgrade', 'pygame') controlling which upgrade/install steps run
		Outputs:
		    bool: True if a reboot is needed because of config changes
		"""
		reBootNeeded = False
		U.logger.log(20,	 "==== starting setup sensor libraries")
		bootFile = U.getBootFileName()
		U.logger.log(20,"==== check if nameserver works")
		cmd= "/bin/ping -c 3 -i 1 -W 3 -q www.google.com " # not /sbin/ like on a mac!!
		ret = subprocess.Popen(cmd,shell=True,stdout=subprocess.PIPE,stderr=subprocess.PIPE).communicate()
		if "{}".format(ret).find("unknown host www.google.com") >-1:
			U.logger.log(20, " nameserver wrong , need to fix, add it to /etc/network/interfaces file ")
			if subprocess.Popen("cat /etc/network/interfaces ",shell=True,stdout=subprocess.PIPE,stderr=subprocess.PIPE).communicate()[0].find("nameserver")==-1:
				U.copyFile("/home/pi/interfaces", "/etc/network/")
				subprocess.Popen("/sbin/ifdown wlan0 && sleep 1 && /sbin/ifup --force wlan0",shell=True)
				U.logger.log(20, " copied new interface file	 ")
				time.sleep(2)
			else:
				time.sleep(10)
				U.logger.log(20, "network setup wrong, need manual intervention ")
				return reBootNeeded

		U.logger.log(20, "==== testing config files and updating if needed")


		if U.uncommentOrAdd("(python /home/pi/callbeacon.py &)","/etc/rc.local",before="exit 0") >0:
			U.logger.log(20, "need to reboot, added 'python /home/pi/callbeacon.py &'	to /home/pi/callbeacon.py")
			reBootNeeded=True

		if U.uncommentOrAdd("dtoverlay=w1-gpio",bootFile) >0:
			U.logger.log(20, "need to reboot, added 'dtoverlay=w1-gpio' to " + bootFile)
			reBootNeeded=True

		if U.removefromFile("dtparam=spi=off",bootFile)>0:
			U.logger.log(20, "removed dtparam=spi=off")

		if U.removefromFile("dtparam=i2c_arm=off",bootFile)>0:
			U.logger.log(20, "removed blacklist i2c-bcm2708")

		if U.uncommentOrAdd("dtparam=i2c_arm=on",bootFile) >0:
			U.logger.log(20, "need to reboot, added 'dtparam=i2c_arm=on' to " + bootFile)
			reBootNeeded=True

		if U.uncommentOrAdd("dtparam=i2c1=on",bootFile) >0:
			U.logger.log(20, "need to reboot, added 'dtparam=i2c1=on' to " + bootFile)
			reBootNeeded=True


		if U.uncommentOrAdd("i2c-dev",bootFile) >0:
			U.logger.log(20, "need to reboot, added 'i2c-dev'  to /etc/modules")
			reBootNeeded=True

		if U.uncommentOrAdd("i2c-bcm2708","/etc/modules") >0:
			U.logger.log(20, "need to reboot, added '2c-bcm2708'  to /etc/modules")
			reBootNeeded=True

		if U.removefromFile("blacklist i2c-bcm2708","/etc/modprobe.d/raspi-blacklist.conf")>0:
			U.logger.log(20, "removed blacklist i2c-bcm2708")

		if U.removefromFile("blacklist spi-bcm2708","/etc/modprobe.d/raspi-blacklist.conf")>0:
			U.logger.log(20, "removed blacklist i2c-bcm2708")

		#if U.uncommentOrAdd("display_rotate=2",bootFile) >0:
		#	 U.logger.log(20, "need to reboot, added 'dtparam=i2c1=on'  to /etc/modules")
		#	 reBootNeeded=True

		if False:
			if upgradeOpSys.find("force")>-1 or upgradeOpSys.find("dist-upgrade"):
				cmd="apt-get -y update"
				U.logger.log(20, "==== getting "+cmd+"  updates")
				ret=subprocess.Popen(cmd +" &",shell=True)
				time.sleep(10)
				for ii in range(300):  # max 3 hours
					if U.pgmStillRunning(cmd):
						U.logger.log(20, "==== "+cmd+"  still running")
						time.sleep(10)
					else:
						break
				U.logger.log(20,"==== "+cmd+" finished ")

				cmd="apt-get -y upgrade"
				ret=subprocess.Popen(cmd +" &",shell=True)
				time.sleep(10)
				for ii in range(300) :	# max 3 hours
					if U.pgmStillRunning(cmd) :
						U.logger.log(20, "==== "+cmd+"  still running")
						time.sleep(10)
					else :
						break
				U.logger.log(20,"==== "+cmd+" finished")

				if upgradeOpSys.find("dist-upgrade")>-1: # not automatically if force, only if explicitly requested
					cmd="apt-get dist-upgrade"
					U.logger.log(20, "==== installing "+cmd+"  -- this might take an hour+ ")
					ret=subprocess.Popen(cmd +" &",shell=True)
					time.sleep(10)
					for ii in range(400) :	# max 3 hours
						if U.pgmStillRunning(cmd) :
							U.logger.log(20, "==== "+cmd+"  still running")
							time.sleep(10)
						else :
							break
					U.logger.log(20,"==== "+cmd+" finished")

			cmd="apt-get -y autoremove"
			U.logger.log(20, "==== cleaning up  "+cmd)
			ret=subprocess.Popen(cmd +" &",shell=True)
			time.sleep(10)
			for ii in range(300) :	# max 3 hours
				if U.pgmStillRunning(cmd) :
					U.logger.log(20, "==== "+cmd+"  still running")
					time.sleep(10)
				else :
					break
			U.logger.log(20,"==== "+cmd+" finished")

			cmd="apt-get clean"
			U.logger.log(20, "==== cleaning up  "+cmd)
			ret=subprocess.Popen(cmd+" &" ,shell=True)
			time.sleep(10)
			for ii in range(300) :	# max 3 hours
				if U.pgmStillRunning(cmd) :
					U.logger.log(20, "==== "+cmd+"  still running")
					time.sleep(10)
				else :
					break
			U.logger.log(20,"==== "+cmd+" finished")



		if	upgradeOpSys.lower().find("force")>-1:
			cmd="apt-get install build-essential python-dev"
			U.logger.log(20, "==== installing "+cmd+" this might take an hour ")
			ret=subprocess.Popen(cmd+" &" ,shell=True)
			time.sleep(10)
			for ii in range(300) :	# max 3 hours
				if U.pgmStillRunning(cmd) :
					U.logger.log(20, "==== "+cmd+"  still running")
					time.sleep(10)
				else :
					break
			U.logger.log(20,"==== "+cmd+" finished")


		if	upgradeOpSys.lower().find("pygame") >-1 or upgradeOpSys.lower().find("force")>-1:
			cmd="apt-get install python-pygame "
			U.logger.log(20, "==== installing "+cmd+" this might take an hour ")
			ret=subprocess.Popen(cmd+" &" ,shell=True)
			time.sleep(10)
			for ii in range(300) :	# max 3 hours
				if U.pgmStillRunning(cmd) :
					U.logger.log(20, "==== "+cmd+"  still running")
					time.sleep(10)
				else :
					break
			U.logger.log(20,"==== "+cmd+" finished")

		time.sleep(1)
		cmd="apt-get install -y python-dev"
		U.logger.log(20, "==== installing "+cmd)
		ret=subprocess.Popen(cmd ,shell=True,stdout=subprocess.PIPE,stderr=subprocess.PIPE).communicate()
		U.logger.log(20,"python-dev return {}, {}".format(ret[0], ret[1]))

		time.sleep(1)
		cmd="apt-get install python-bluez"
		U.logger.log(20, "==== installing "+cmd)
		ret=subprocess.Popen(cmd ,shell=True,stdout=subprocess.PIPE,stderr=subprocess.PIPE).communicate()
		U.logger.log(20,"{}, {}".format(ret[0], ret[1]))

		time.sleep(1)
		cmd="apt-get -y install python-smbus"
		U.logger.log(20, "==== installing "+cmd)
		ret=subprocess.Popen(cmd ,shell=True,stdout=subprocess.PIPE,stderr=subprocess.PIPE).communicate()
		U.logger.log(20,"{}, {}".format(ret[0], ret[1]))

		time.sleep(1)
		cmd="apt-get -y install i2c-tools"
		U.logger.log(20, "==== installing "+cmd)
		ret=subprocess.Popen(cmd ,shell=True,stdout=subprocess.PIPE,stderr=subprocess.PIPE).communicate()
		U.logger.log(20,"{}, {}".format(ret[0], ret[1]))

		time.sleep(1)
		cmd="cd "+G.homeDir0+" ;git clone https://github.com/adafruit/Adafruit-Raspberry-Pi-Python-Code.git"
		U.logger.log(20, "==== installing "+cmd)
		ret=subprocess.Popen(cmd ,shell=True,stdout=subprocess.PIPE,stderr=subprocess.PIPE).communicate()
		U.logger.log(20,"{}, {}".format(ret[0], ret[1]))


		time.sleep(1)
		U.logger.log(20,	 "==== checking  spi")
		if not os.path.isfile(G.homeDir0+"py-spidev-master/setup.py"):
			cmd="cd "+G.homeDir0+" ;wget https://github.com/Gadgetoid/py-spidev/archive/master.zip; mkdir py-spidev-master"
			ret=subprocess.Popen(cmd ,shell=True,stdout=subprocess.PIPE,stderr=subprocess.PIPE).communicate()
			U.logger.log(20,"{}, {}".format(ret[0], ret[1]))

			cmd="echo 'A'| unzip master.zip; rm master.zip; cd "+G.homeDir0+"py-spidev-master; sudo /usr/bin/python setup.py install;cd "+G.homeDir
			U.logger.log(20, "==== installing "+cmd)
			ret=subprocess.Popen(cmd ,shell=True,stdout=subprocess.PIPE,stderr=subprocess.PIPE).communicate()
			U.logger.log(20,"{}, {}".format(ret[0], ret[1]))
			U.logger.log(20, "==== installing "+cmd+" done")


		time.sleep(1)
		if not os.path.isfile(G.homeDir0+"Adafruit_Python_GPIO/setup.py") or  upgradeOpSys.lower().find("force")>-1:
			cmd="cd "+G.homeDir0+" ; git clone https://github.com/adafruit/Adafruit_Python_GPIO.git"
			U.logger.log(20, "==== getting  "+cmd)
			try:  # test if there
				ret=subprocess.Popen(cmd ,shell=True,stdout=subprocess.PIPE,stderr=subprocess.PIPE).communicate()
				U.logger.log(20, "Adafruit_Python_GPIO return \n"+ ret[0]+"\n"+ret[1])
				cmd="cd "+G.homeDir0+"Adafruit_Python_GPIO; /usr/bin/python setup.py install"
				ret=subprocess.Popen(cmd ,shell=True,stdout=subprocess.PIPE,stderr=subprocess.PIPE).communicate()
				U.logger.log(20, "Adafruit_Python_GPIO return \n"+ ret[0]+"\n"+ret[1])
			except Exception as e:
				U.logger.log(20, "Adafruit_Python_GPIO failed")


		U.logger.log(20,	 "=======  finished setup sensor libraries ==========")

		f=open(G.homeDir+"installLibs.done","w")
		f.write("4.0")
		f.close()
		return reBootNeeded
		
		
def readNewParams():
		"""Reads the plugin parameters file and, if present, updates the module-global rebootCommand from the parsed parameters.

		Inputs:
		    None.
		Outputs:
		    None: Updates global rebootCommand; returns early if no params read
		"""
		global rebootCommand
		inp, inpRaw = doRead()
		if inp == "": return
		if "rebootCommand"			in inp: rebootCommand		  = inp["rebootCommand"]

def doRead():
	"""Reads the parameters file from the home directory and parses it as JSON, retrying once after a short delay if the first read fails. Returns the parsed object and the raw text, or empty strings on failure.

	Inputs:
	    None.
	Outputs:
	    tuple: (parsed params dict or '', raw file text or '')
	"""
	inp, inRaw = "",""
	try:
		f=open(G.homeDir+"parameters","r")
		inRaw =f.read()
		inp =json.loads(inRaw)
	except: 
			try:
				time.sleep(0.1)
				f=open(G.homeDir+"parameters","r")
				inRaw =f.read()
				inp =json.loads(inRaw)
			except: 
				try:	f.close()
				except: return "",""
				return "",""

	try:	f.close()
	except: return "",""
	return inp, inRaw

		
def doReboot(tt=1,text="",cmd=""):
	"""Logs a message, waits a given number of seconds, then triggers a system reboot by running either the supplied command or the global rebootCommand via the shell.

	Inputs:
	    tt (int): Seconds to sleep before rebooting
	    text (str): Message logged before rebooting
	    cmd (str): Optional shell command to run; falls back to global rebootCommand if empty
	Outputs:
	    None: Logs, sleeps, and invokes a reboot shell command
	"""
	global rebootCommand
	U.logger.log(20,text)
	time.sleep(tt)
	if cmd =="":
		subprocess.call(rebootCommand, shell=True)
	else:
		subprocess.call(cmd, shell=True)


global debug, rebootCommand
rebootCommand ="reboot now"

if not os.path.isdir(G.logDir):
	subprocess.call("mkdir "+G.logDir +" 2>&1 1>/dev/null &", shell=True)

U.setLogging()

debug = 1

readNewParams()


U.logger.log(20," installLibs starting ")

test = [False for ii in range(10)]
try:
	f = open(G.homeDir+"installLibs.done","r")
	test[0] = float(f.read())
	f.close()
except: test[0] = -1

myPID			= str(os.getpid())

upgradeOpSys = ""
try:
	upgradeOpSys = sys.argv[1]
	U.logger.log(20," installLibs     will do a complete upgrade of the opsys , this might take a LOOONG time")
	# kill some of the programs that might be in conflict with installing new opsys s..
	U.killOldPgm(myPID,"callbeacon.py")
	U.killOldPgm(myPID,"beaconloop.py")
	U.killOldPgm(myPID,"BLEconnect.py")
	U.killOldPgm(myPID,"getsensorvalues.py")
	U.killOldPgm(myPID,"receiveGPIOcommands.py")
	U.killOldPgm(myPID,"ultrasoundDistance.py")
	U.killOldPgm(myPID,"display.py")
	U.removeFile(G.homeDir + "installLibs.done")
	test[0] = -1
	arguments = "{}".format(sys.argv)
except:
	U.logger.log(20," installLibs no opsys upgrade requested")
	arguments = ""


test[1] = not os.path.isfile(G.homeDir0+"Adafruit_Python_DHT/setup.py")
test[2] = not os.path.isfile(G.homeDir0+"Adafruit_Python_GPIO/setup.py")
test[3] = not os.path.isdir(G.homeDir0+"py-spidev-master")
test[4] = not os.path.isdir( G.homeDir0+"Adafruit-Raspberry-Pi-Python-Code")
doU= False
for ii in range(1,len(test)):
	if test[ii]:
		doU=True
		break

if test[0] < 4.0 or	 doU:
	U.logger.log(20, "==== tested installed version, doing upgrades")
	if setupLibs(arguments):		
		doReboot(tt=2., text="==== will reboot now to activate sensor settings")
	if upgradeOpSys !="":
		doReboot(tt=2., text="==== will reboot now to activate new op-sys installs")

else:
		U.logger.log(20,	 "==== libraries seem to be setup, no need for action")

U.logger.log(20,	 "==== libraries install finished")



sys.exit(0)		   
