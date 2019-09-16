#!/usr/bin/ python
homeDir = "/home/pi/pibeacon/"
logDir	= "/var/log/"
import	sys, os, subprocess, copy
import	time,datetime
import json
sys.path.append(os.getcwd())
import	piBeaconUtils	as U
import	piBeaconGlobals as G
G.program = "batteryLevelBLE"

import pexpect
import time
 
def die(child, reason):
		U.logger.log(30,reason)
		child.sendline("disconnect")
		time.sleep(0.5)
		child.sendline("disconnect")
		child.sendline("exit\r")
		child.terminate()


try:
	myPID			= str(os.getpid())
	#kill old G.programs
	U.setLogging()
	U.killOldPgm(myPID,G.program+".py")
	#DEVICE = "24:DA:11:26:3B:4D"
	DEVICE = "24:DA:11:26:3B:4D"
 
 

	child = pexpect.spawn("gatttool -I")
 
	U.logger.log(30,"Connecting to {}".format(DEVICE))
	child.sendline("connect {0}".format(DEVICE))
	ret = child.expect(["Connection successful","Error:",pexpect.TIMEOUT], timeout=5)
	if ret == 0:
		U.logger.log(30,"Connected.., reading battery level")
	if ret == 1:
		die(child," not connected")
		exit()
	if ret == 3:
		die(child,"timeout")
		exit

	# get battery level
	child.sendline("char-read-uuid 2A19")
	child.expect("handle: ", timeout=10)
	child.expect("\r\n", timeout=10)

	batpercent = -2
	data = child.before
	battery = data.split("value: ")
	if len(battery) ==2:  
		try: batpercent =battery[1].strip()
		except: batpercent=-1
	U.logger.log(30,"return: {} {} {} ".format(data, battery, int(batpercent,16)) )
	die(child, "ok")
	exit()
except	Exception, e:
		U.logger.log(50, u"in Line {} has error={}".format(sys.exc_traceback.tb_lineno, e))
U.logger.log(30, u"disconnecting")

die(child, "exception")
exit()
