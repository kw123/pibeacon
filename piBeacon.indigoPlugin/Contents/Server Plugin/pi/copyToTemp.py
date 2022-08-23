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


def setupTempDir():
	try:
		if	not os.path.isdir(G.homeDir+"temp"):
			subprocess.call("mkdir  "+G.homeDir+"temp", shell=True)
		# check if already tempfs type, if not create 
		if subprocess.Popen("df | grep tempfs ", shell=True,stdout=subprocess.PIPE,stderr=subprocess.PIPE).communicate()[0].find(G.homeDir+"temp") == -1:
			subprocess.call("mount -t tmpfs -o size=2m tmpfs "+G.homeDir+"temp", shell=True)
		subprocess.call("sudo rm "+G.homeDir+"temp/*", shell=True)
	except	Exception, e :
		U.logger.log(40, u"Line {} has error={}".format(traceback.extract_tb(sys.exc_info()[2])[-1][1], e))
	return 


if __name__ == "__main__":
	timeLastFile	= 0
	myPID			= str(os.getpid())
	U.killOldPgm(myPID, G.program+".py")

	setupTempDir()

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
				U.logger.log(30,u"copying to files to temp dir files={}".format(G.parameterFileList))
				for fileName in G.parameterFileList:
					if os.path.isfile(G.homeDir+fileName):
							cmd = "sudo cp "+G.homeDir+fileName +" " +G.homeDir+"temp/"+fileName
							subprocess.call(cmd, shell=True)
							#U.logger.log(30,cmd)
				try:  
					timeLastFile = os.path.getmtime(G.homeDir+"temp/touchFile")
				except:	 timeLastFile = -10
				subprocess.call("chmod a+w -R "  +G.homeDir+"temp/*", shell=True)
				subprocess.call("chown -R pi:pi "+G.homeDir+"temp/*", shell=True)
				time.sleep(10)

		time.sleep(0.5)
