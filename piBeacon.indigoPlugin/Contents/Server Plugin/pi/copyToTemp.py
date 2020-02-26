#!/usr/bin/env python
# -*- coding: utf-8 -*-
# by Karl Wachs
# mar 2 2016
# version 0.95
##
##	  --- utils 
#
#	 
import sys 
import os 
import time
import subprocess
sys.path.append(os.getcwd())
import piBeaconGlobals as G
import piBeaconUtils as U
U.setLogging()
G.program 		= "copyToTemp"


if __name__ == "__main__":
	timeLastFile	= 0
	myPID			= str(os.getpid())
	U.killOldPgm(myPID, G.program+".py")

	subprocess.call("chmod a+w -R "+G.homeDir+"*", shell=True)
	subprocess.call("chown -R pi:pi "+G.homeDir+"*", shell=True)
	try:	
		subprocess.call("touch "+G.homeDir+"temp/touchFile", shell=True)
		timeLastFile = os.path.getmtime(G.homeDir+"temp/touchFile") -1
	except: 
		timeLastFile = 0

	while True:	   
		doCopy = 0

		if os.path.isfile(G.homeDir+"temp/touchFile"):
			if timeLastFile != os.path.getmtime(G.homeDir+"temp/touchFile"):
				doCopy = 1
				
		elif os.path.isdir(G.homeDir+"temp"):
				doCopy = 2
				subprocess.call("touch "+G.homeDir+"temp/touchFile", shell=True)

		if not os.path.isfile(G.homeDir+"temp/parameters"):
				doCopy = 3
				
		###print G.program, doCopy 
		if doCopy >0:
				##print G.program, doCopy
				for fileName in G.parameterFileList:
					if os.path.isfile(G.homeDir+fileName):
							subprocess.call("sudo cp "+G.homeDir+fileName +" " +G.homeDir+"temp/"+fileName, shell=True)
				try:  
					timeLastFile = os.path.getmtime(G.homeDir+"temp/touchFile")
				except:	 timeLastFile = -10
				subprocess.call("chmod a+w -R "  +G.homeDir+"temp/*", shell=True)
				subprocess.call("chown -R pi:pi "+G.homeDir+"temp/*", shell=True)
				time.sleep(10)

		time.sleep(0.5)
