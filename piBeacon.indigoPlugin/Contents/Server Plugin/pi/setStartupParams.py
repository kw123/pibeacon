#!/usr/bin/env python
# -*- coding: utf-8 -*-
#
# set autologin to auto login comamndline
#
#
import subprocess
import sys
import os
import time

sys.path.append(os.getcwd())
try:
	import	piBeaconGlobals as G
	import	piBeaconUtils	as U
	homeDir  = G.homeDir
	homeDir0 = G.homeDir0
except:
	homeDir		= "/home/pi/pibeacon/"
	homeDir0	= "/home/pi/"

program = "setStartupParams"


#################################
def readPopen(cmd):
	"""Runs a shell command via subprocess.Popen, capturing stdout and stderr, and returns them decoded as UTF-8 strings; returns two empty strings on any exception.

	Inputs:
	    cmd (str): shell command line to execute
	Outputs:
	    tuple: (stdout, stderr) decoded UTF-8 strings, or ('','') on error
	"""
	try:
		ret, err = subprocess.Popen(cmd, shell=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE).communicate()
		return ret.decode('utf_8'), err.decode('utf_8')
	except Exception as e:
		return "","" 

#################################
def getOsVersion():
	"""Determines the Raspberry Pi OS version by reading /etc/os-release and parsing the VERSION_ID line, returning it as an integer.

	Inputs:
	    None.
	Outputs:
	    int: OS VERSION_ID as integer, or 0 if not found
	"""
	osInfo	 = readPopen("cat /etc/os-release")[0].strip("\n").split("\n")
	for line in osInfo:
		if line .find("VERSION_ID=") == 0:
			return int( line.strip('"').split('="')[1] )
	return 0 

def execUpdate():
	"""Performs one-time Raspberry Pi startup configuration via raspi-config (boot behaviour, I2C, LEDs, splash, rootfs expansion) when the setStartupParams.done marker file is absent, writes the marker, waits for other installs to finish, and reboots the Pi.

	Inputs:
	    None.
	Outputs:
	    None: runs raspi-config commands, writes a marker file, logs progress and may reboot the system
	"""
	osV = getOsVersion()
	U.logger.log(20, "starting w osV:{}".format(osV))
	if not os.path.isfile("{}setStartupParams.done".format(homeDir)):
		
		actions = ["/usr/bin/sudo /usr/bin/raspi-config nonint do_boot_behaviour B2",
#				  "/usr/bin/sudo /usr/bin/raspi-config nonint do_boot_wait 1",
				  "/usr/bin/sudo /usr/bin/raspi-config nonint do_i2c 0",
				  "/usr/bin/sudo /usr/bin/raspi-config nonint do_leds 0",
				  "/usr/bin/sudo /usr/bin/raspi-config nonint do_boot_splash 1",
				  "/usr/bin/sudo /usr/bin/raspi-config nonint do_expand_rootfs"]
	
		for action in actions:
			U.logger.log(20, "doing:{}:".format(action))
			ret = readPopen(action)
			U.logger.log(20, "response:{}".format(ret))
		readPopen("echo finished > {}setStartupParams.done".format(homeDir))
		U.logger.log(20, "finished w setting startup params, need to wait for other installs to finish")
		time.sleep(30)
		for ii in range(200):
			if not U.pgmStillRunning("checkForIncl"): break
			U.logger.log(20, "checkForIncl still running")
			time.sleep(10)
		U.logger.log(20, "finished w setting startup params, need to reboot, will do in 10 secs")
		U.doReboot(tt=10., text="one time restart after raspi-config params set")

	U.logger.log(20, "finished, all set ")


U.setLogging()
execUpdate()
exit()
