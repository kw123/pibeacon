#!/usr/bin/env python
# -*- coding: utf-8 -*-
# by Karl Wachs
# mar 2 2016
# version 0.95
##
##   read sensors and GPIO INPUT and send http to indigo with data
#
#	GPIO pins as inputs: GPIO:but#  ={"27":"0","22":"1","25":"2","24":"3","23":"4","18":"5"}

##
homeDir = "/home/pi/pibeacon/"
logDir  = "/var/log/"
import  sys, os, subprocess, copy
import  time,datetime
import  json
import	piBeaconUtils	as U
import	piBeaconGlobals as G


def killOldPgm(myPID,pgmToKill):
		"""Finds and kills any running processes matching the given program name (via ps/grep), skipping the caller's own PID, to terminate stale instances.

		Inputs:
		    myPID (int): the caller's process ID to exclude from killing
		    pgmToKill (str): program name substring to match against running processes
		Outputs:
		    None: sends kill -9 to matching processes and logs
		"""
		global debug
		try:
			# /proc instead of "ps -ef | grep X | grep -v grep" - this also fixes a py3 bug on the
			# way: communicate() returns BYTES, and the old ret.split("\n") on bytes raises there
			for pid, cmdline in U.procList(pgmToKill):
				if (" " + cmdline + " ").find(" grep ") > -1: continue
				if pid == int(myPID): continue
				U.logger.log(20, "killing "+pgmToKill)
				subprocess.call("kill -9 "+str(pid), shell=True)
		except Exception as e:
			U.logger.log(20,"", exc_info=True)

def readParams():
		"""Reads and JSON-parses the plugin's parameters file from the home directory and applies the parsed values via U.getGlobalParams; returns early if parsing fails.

		Inputs:
		    None.
		Outputs:
		    None: loads parameters file and updates global params
		"""
		global debug
		f=open(homeDir+"parameters","r")
		try:	inp =json.loads(f.read())
		except: return
		f.close()
		U.getGlobalParams(inp)

######### main  ########
U.setLogging()

readParams()

try:
	myPID = str(os.getpid())
	cmd= json.loads(sys.argv[1])
	if "delayStart" in cmd:
		delayStart =  float(cmd["delayStart"])
		time.sleep(delayStart)

	killOldPgm(myPID, "playsound.py")  # old old instances of myself if they are still running
	cmdOut= cmd["player"]+ " "+homeDir+"soundfiles/"++ cmd["file"] +" &"
	U.logger.log(10, cmdOut)
	subprocess.call(cmdOut, shell=True)
except  Exception as e:
	U.logger.log(20,"", exc_info=True)

		
sys.exit(0)		
