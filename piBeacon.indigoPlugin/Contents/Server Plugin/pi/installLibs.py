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
import RPi.GPIO as GPIO
sys.path.append(os.getcwd())
import	piBeaconUtils	as U
import	piBeaconGlobals as G

G.program  = "installLibs"



def setupLibs(upgradeOpSys):
		reBootNeeded = False
		U.toLog(-1,	 "==== starting setup sensor libraries")

		U.toLog(-1,"==== check if nameserver works")
		cmd= "/bin/ping -c 3 -i 1 -W 3 -q www.google.com " # not /sbin/ like on a mac!!
		ret = subprocess.Popen(cmd,shell=True,stdout=subprocess.PIPE,stderr=subprocess.PIPE).communicate()
		if unicode(ret).find("unknown host www.google.com") >-1:
			U.toLog(-1, " nameserver wrong , need to fix, add it to /etc/network/interfaces file ")
			if subprocess.Popen("cat /etc/network/interfaces ",shell=True,stdout=subprocess.PIPE,stderr=subprocess.PIPE).communicate()[0].find("nameserver")==-1:
				subprocess.Popen("cp /home/pi/interfaces /etc/network/ ",shell=True)
				subprocess.Popen("/sbin/ifdown wlan0 && sleep 1 && /sbin/ifup --force wlan0",shell=True)
				U.toLog(-1, " copied new interface file	 ")
				time.sleep(2)
			else:
				time.sleep(10)
				U.toLog(-1, "network setup wrong, need manual intervention ")
				return	  

		U.toLog(-1, "==== testing config files and updating if needed")


		if U.uncommentOrAdd("(sleep 10; python /home/pi/callbeacon.py &)","/etc/rc.local",before="exit 0") >0:
			U.toLog(-1, "need to reboot, added 'sleep 10; python /home/pi/callbeacon.py &'	to /home/pi/callbeacon.py")
			reBootNeeded=True

		if U.uncommentOrAdd("dtoverlay=w1-gpio","/boot/config.txt") >0:
			U.toLog(-1, "need to reboot, added 'dtoverlay=w1-gpio'	to /boot/config.txt")
			reBootNeeded=True

		if U.removefromFile("dtparam=spi=off","/boot/config.txt")>0:
			U.toLog(-1, "removed dtparam=spi=off")

		if U.removefromFile("dtparam=i2c_arm=off","/boot/config.txt")>0:
			U.toLog(-1, "removed blacklist i2c-bcm2708")

		if U.uncommentOrAdd("dtparam=i2c_arm=on","/boot/config.txt") >0:
			U.toLog(-1, "need to reboot, added 'dtparam=i2c_arm=on'	 to /boot/config.txt")
			reBootNeeded=True

		if U.uncommentOrAdd("dtparam=i2c1=on","/boot/config.txt") >0:
			U.toLog(-1, "need to reboot, added 'dtparam=i2c1=on'  to /boot/config.txt")
			reBootNeeded=True


		if U.uncommentOrAdd("i2c-dev","/boot/config.txt") >0:
			U.toLog(-1, "need to reboot, added 'i2c-dev'  to /etc/modules")
			reBootNeeded=True

		if U.uncommentOrAdd("i2c-bcm2708","/etc/modules") >0:
			U.toLog(-1, "need to reboot, added '2c-bcm2708'	 to /etc/modules")
			reBootNeeded=True

		if U.removefromFile("blacklist i2c-bcm2708","/etc/modprobe.d/raspi-blacklist.conf")>0:
			U.toLog(-1, "removed blacklist i2c-bcm2708")

		if U.removefromFile("blacklist spi-bcm2708","/etc/modprobe.d/raspi-blacklist.conf")>0:
			U.toLog(-1, "removed blacklist i2c-bcm2708")

		#if U.uncommentOrAdd("display_rotate=2","/boot/config.txt") >0:
		#	 U.toLog(-1, "need to reboot, added 'dtparam=i2c1=on'  to /boot/config.txt")
		#	 reBootNeeded=True

		if False:
			if upgradeOpSys.find("force")>-1 or upgradeOpSys.find("dist-upgrade"):
				cmd="apt-get -y update"
				print datetime.datetime.now().strftime("%Y%m%d-%H:%M:%S")+" installLibs ==== getting "+cmd+"  this might take an hour"
				U.toLog(-1, "==== getting "+cmd+"  updates")
				ret=subprocess.Popen(cmd +" &",shell=True)
				time.sleep(10)
				for ii in range(300):  # max 3 hours
					if U.pgmStillRunning(cmd):
						U.toLog(-1, "==== "+cmd+"  still running")
						time.sleep(10)
					else:
						break
				U.toLog(-1,"==== "+cmd+" finished ")

				cmd="apt-get -y upgrade"
				print datetime.datetime.now().strftime("%Y%m%d-%H:%M:%S")+" installLibs ==== getting "+cmd+"  this might take an hour"
				ret=subprocess.Popen(cmd +" &",shell=True)
				time.sleep(10)
				for ii in range(300) :	# max 3 hours
					if U.pgmStillRunning(cmd) :
						U.toLog(-1, "==== "+cmd+"  still running")
						time.sleep(10)
					else :
						break
				U.toLog(-1,"==== "+cmd+" finished")

				if upgradeOpSys.find("dist-upgrade")>-1: # not automatically if force, only if explicitly requested
					cmd="apt-get dist-upgrade"
					U.toLog(-1, "==== installing "+cmd+"  -- this might take an hour+ ")
					ret=subprocess.Popen(cmd +" &",shell=True)
					time.sleep(10)
					for ii in range(400) :	# max 3 hours
						if U.pgmStillRunning(cmd) :
							U.toLog(-1, "==== "+cmd+"  still running")
							time.sleep(10)
						else :
							break
					U.toLog(-1,"==== "+cmd+" finished")

			cmd="apt-get -y autoremove"
			U.toLog(-1, "==== cleaning up  "+cmd)
			ret=subprocess.Popen(cmd +" &",shell=True)
			time.sleep(10)
			for ii in range(300) :	# max 3 hours
				if U.pgmStillRunning(cmd) :
					U.toLog(-1, "==== "+cmd+"  still running")
					time.sleep(10)
				else :
					break
			U.toLog(-1,"==== "+cmd+" finished")

			cmd="apt-get clean"
			U.toLog(-1, "==== cleaning up  "+cmd)
			ret=subprocess.Popen(cmd+" &" ,shell=True)
			time.sleep(10)
			for ii in range(300) :	# max 3 hours
				if U.pgmStillRunning(cmd) :
					U.toLog(-1, "==== "+cmd+"  still running")
					time.sleep(10)
				else :
					break
			U.toLog(-1,"==== "+cmd+" finished")



		if	upgradeOpSys.lower().find("force")>-1:
			cmd="apt-get install build-essential python-dev"
			U.toLog(-1, "==== installing "+cmd+" this might take an hour ")
			ret=subprocess.Popen(cmd+" &" ,shell=True)
			time.sleep(10)
			for ii in range(300) :	# max 3 hours
				if U.pgmStillRunning(cmd) :
					U.toLog(-1, "==== "+cmd+"  still running")
					time.sleep(10)
				else :
					break
			U.toLog(-1,"==== "+cmd+" finished")


		if	upgradeOpSys.lower().find("pygame") >-1 or upgradeOpSys.lower().find("force")>-1:
			cmd="apt-get install python-pygame "
			U.toLog(-1, "==== installing "+cmd+" this might take an hour ")
			ret=subprocess.Popen(cmd+" &" ,shell=True)
			time.sleep(10)
			for ii in range(300) :	# max 3 hours
				if U.pgmStillRunning(cmd) :
					U.toLog(-1, "==== "+cmd+"  still running")
					time.sleep(10)
				else :
					break
			U.toLog(-1,"==== "+cmd+" finished")

		time.sleep(1)
		cmd="apt-get install -y python-dev"
		U.toLog(-1, "==== installing "+cmd)
		ret=subprocess.Popen(cmd ,shell=True,stdout=subprocess.PIPE,stderr=subprocess.PIPE).communicate()
		U.toLog(-1,"python-dev return "+ret[0]+"\n"+ret[1])

		time.sleep(1)
		cmd="apt-get install python-bluez"
		U.toLog(-1, "==== installing "+cmd)
		ret=subprocess.Popen(cmd ,shell=True,stdout=subprocess.PIPE,stderr=subprocess.PIPE).communicate()
		U.toLog(-1,	  ret[0]+"\n"+ret[1])

		time.sleep(1)
		cmd="apt-get -y install python-smbus"
		U.toLog(-1, "==== installing "+cmd)
		ret=subprocess.Popen(cmd ,shell=True,stdout=subprocess.PIPE,stderr=subprocess.PIPE).communicate()
		U.toLog(-1,	  ret[0]+"\n"+ret[1])

		time.sleep(1)
		cmd="apt-get -y install i2c-tools"
		U.toLog(-1, "==== installing "+cmd)
		ret=subprocess.Popen(cmd ,shell=True,stdout=subprocess.PIPE,stderr=subprocess.PIPE).communicate()
		U.toLog(-1,	  ret[0]+"\n"+ret[1])

		time.sleep(1)
		cmd="cd "+G.homeDir0+" ;git clone https://github.com/adafruit/Adafruit-Raspberry-Pi-Python-Code.git"
		U.toLog(-1, "==== installing "+cmd)
		ret=subprocess.Popen(cmd ,shell=True,stdout=subprocess.PIPE,stderr=subprocess.PIPE).communicate()
		U.toLog(-1,	  ret[0]+"\n"+ret[1])

		time.sleep(1)
		cmd="apt-get install python-bluez"
		U.toLog(-1, "==== installing "+cmd)
		ret=subprocess.Popen(cmd ,shell=True,stdout=subprocess.PIPE,stderr=subprocess.PIPE).communicate()
		U.toLog(-1,	  ret[0]+"\n"+ret[1])

		time.sleep(1)
		U.toLog(-1,	 "==== checking	 spi")
		if not os.path.isfile(G.homeDir0+"py-spidev-master/setup.py"):
			cmd="cd "+G.homeDir0+" ;wget https://github.com/Gadgetoid/py-spidev/archive/master.zip; mkdir py-spidev-master"
			ret=subprocess.Popen(cmd ,shell=True,stdout=subprocess.PIPE,stderr=subprocess.PIPE).communicate()
			U.toLog(-1,	  ret[0]+"\n"+ret[1])

			cmd="echo 'A'| unzip master.zip; rm master.zip; cd "+G.homeDir0+"py-spidev-master; sudo /usr/bin/python setup.py install;cd "+G.homeDir
			U.toLog(-1, "==== installing "+cmd)
			ret=subprocess.Popen(cmd ,shell=True,stdout=subprocess.PIPE,stderr=subprocess.PIPE).communicate()
			U.toLog(-1,	  ret[0]+"\n"+ret[1])
			U.toLog(-1, "==== installing "+cmd+" done")


		try:
			import Adafruit_DHT
			DHTinstalled=True
		except:
			DHTinstalled=False
		
		print "DHTinstalled",DHTinstalled
		time.sleep(1)
		if (not os.path.isfile(G.homeDir0+"Adafruit_Python_DHT/setup.py"))	or upgradeOpSys.lower().find("dht") >-1 or upgradeOpSys.lower().find("force")>-1 or (not DHTinstalled):
			cmd="cd "+G.homeDir0+"; git clone https://github.com/adafruit/Adafruit_Python_DHT.git"
			U.toLog(-1, "==== getting  "+cmd)
			try:
				ret=subprocess.Popen(cmd ,shell=True,stdout=subprocess.PIPE,stderr=subprocess.PIPE).communicate()
				U.toLog(-1,"Adafruit_Python_DHT return "+ret[0]+"\n"+ret[1])
				cmd="cd "+G.homeDir0+"Adafruit_Python_DHT; sudo /usr/bin/python setup.py install"
				ret=subprocess.Popen(cmd ,shell=True,stdout=subprocess.PIPE,stderr=subprocess.PIPE).communicate()
				U.toLog(-1, "Adafruit_Python_DHT return "+ ret[0]+"\n"+ret[1])
			except:	   # installed
				U.toLog(-1, "install failed for Adafruit_Python_DHT")

		time.sleep(1)
		if not os.path.isfile(G.homeDir0+"Adafruit_Python_GPIO/setup.py") or  upgradeOpSys.lower().find("force")>-1:
			cmd="cd "+G.homeDir0+" ; git clone https://github.com/adafruit/Adafruit_Python_GPIO.git"
			U.toLog(-1, "==== getting  "+cmd)
			try:  # test if there
				ret=subprocess.Popen(cmd ,shell=True,stdout=subprocess.PIPE,stderr=subprocess.PIPE).communicate()
				U.toLog(-1, "Adafruit_Python_GPIO return \n"+ ret[0]+"\n"+ret[1])
				cmd="cd "+G.homeDir0+"Adafruit_Python_GPIO; /usr/bin/python setup.py install"
				ret=subprocess.Popen(cmd ,shell=True,stdout=subprocess.PIPE,stderr=subprocess.PIPE).communicate()
				U.toLog(-1, "Adafruit_Python_GPIO return \n"+ ret[0]+"\n"+ret[1])
			except	Exception, e:
				U.toLog(-1, "Adafruit_Python_GPIO failed")


		U.toLog(-1,	 "=======  finished setup sensor libraries ==========")

		f=open(G.homeDir+"installLibs.done","w")
		f.write("4.0")
		f.close()
		return reBootNeeded
		
		
def readNewParams():
		global rebootCommand
		inp,inpRaw = doRead()
		if inp == "": return
		if u"rebootCommand"			in inp: rebootCommand		  = inp["rebootCommand"]

def doRead():
	inp, inRaw ="",""
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

		
def doReboot(tt,text,cmd=""):
	global rebootCommand
	U.toLog(-1,text)
	print " rebooting / shutdown ", text
	time.sleep(tt)
	if cmd =="":
		os.system(rebootCommand)
	else:
		os.system(cmd)


global debug, rebootCommand
rebootCommand ="reboot now"

if not os.path.isdir(G.logDir):
	os.system("mkdir "+G.logDir +" 2>&1 1>/dev/null &")

debug=1

readNewParams()


print datetime.datetime.now().strftime("%Y%m%d-%H:%M:%S")+" installLibs starting "

test=[False for ii in range(10)]
try:
	f=open(G.homeDir+"installLibs.done","r")
	test[0]= float(f.read())
	f.close()
except: test[0] = -1

myPID			= str(os.getpid())

upgradeOpSys =""
try:
	upgradeOpSys = sys.argv[1]
	print datetime.datetime.now().strftime("%Y%m%d-%H:%M:%S")+" installLibs	 will do a complete upgrade of the opsys , this might take a LOOONG time"
	# kill some of the programs that might be in conflict with installing new opsys s..
	U.killOldPgm(myPID,"callbeacon.py")
	U.killOldPgm(myPID,"beaconloop.py")
	U.killOldPgm(myPID,"BLEconnect.py")
	U.killOldPgm(myPID,"getsensorvalues.py")
	U.killOldPgm(myPID,"receiveGPIOcommands.py")
	U.killOldPgm(myPID,"ultrasoundDistance.py")
	U.killOldPgm(myPID,"display.py")
	os.system("rm " + G.homeDir + "installLibs.done	 >/dev/null 2>&1")
	test[0] = -1
	arguments = unicode(sys.argv)
except:
	print datetime.datetime.now().strftime("%Y%m%d-%H:%M:%S")+" installLibs no opsys upgrade requested"
	arguments = ""


test[1] = not os.path.isfile(G.homeDir0+"Adafruit_Python_DHT/setup.py")
test[2] = not os.path.isfile(G.homeDir0+"Adafruit_Python_GPIO/setup.py")
test[3] = not os.path.isdir(G.homeDir0+"py-spidev-master")
test[4] = not os.path.isdir( G.homeDir0+"Adafruit-Raspberry-Pi-Python-Code")
doU= False
for ii in range(1,len(test)):
	if test[ii]:
		doU=True
		print "test:" , test
		break

if test[0] < 4.0 or	 doU:
	U.toLog(-1, "==== tested installed version, doing upgrades")
	if setupLibs(arguments):		
		doReboot(2.,"==== will reboot now to activate sensor settings")
	if upgradeOpSys !="":
		doReboot(2.,"==== will reboot now to activate new op-sys installs")

else:
		U.toLog(-1,	 "==== libraries seem to be setup, no need for action")

U.toLog(-1,	 "==== libraries install finished")

print  datetime.datetime.now().strftime("%Y%m%d-%H:%M:%S")+" installLibs install finished"

sys.exit(0)		   
