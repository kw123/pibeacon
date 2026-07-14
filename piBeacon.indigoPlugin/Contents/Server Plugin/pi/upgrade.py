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

program = "upgrade"


#################################
def readPopen(cmd):
	"""Runs a shell command via subprocess.Popen and returns its decoded stdout and stderr, returning empty strings on error.

	Inputs:
	    cmd (str): shell command line to execute
	Outputs:
	    tuple: (stdout, stderr) as decoded UTF-8 strings, or ('','') on error
	"""
	try:
		ret, err = subprocess.Popen(cmd, shell=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE).communicate()
		return ret.decode('utf_8'), err.decode('utf_8')
	except Exception as e:
		return "","" 

#################################
def getOsVersion():
	"""Reads /etc/os-release and returns the integer VERSION_ID of the operating system, or 0 if not found.

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
	"""Runs the system update sequence (apt-get update, upgrade, and autoremove with --yes), logging the OS version and each command's response.

	Inputs:
	    None.
	Outputs:
	    None: executes apt-get update/upgrade/autoremove and logs results
	"""
	osV = getOsVersion()
	U.logger.log(20, "starting w osV:{}".format(osV))
	U.logger.log(20, "sudo apt-get --yes --assume-yes update ")
	ret = readPopen( "sudo apt-get --yes --assume-yes update ")
	U.logger.log(20, "update response:{}".format(ret))
	U.logger.log(20, "sudo apt-get --yes --assume-yes upgrade ")
	ret = readPopen( "sudo apt-get --yes --assume-yes upgrade ")
	U.logger.log(20, "upgrade response:{}".format(ret))
	U.logger.log(20, "sudo apt-get --yes --assume-yes autoremove ")
	ret = readPopen( "sudo apt-get --yes --assume-yes autoremove ")
	U.logger.log(20, "upgrade response:{}".format(ret))
	U.logger.log(20, "finished, all set ")

U.setLogging()
execUpdate()
exit()
