#!/usr/bin/env python
# -*- coding: utf-8 -*-
# by Karl Wachs
# mar 2 2016
# version 0.95
##
##	  --- utils 
#
#	
## ok for py3
 
import sys 
import os 
import time
import subprocess
sys.path.append(os.getcwd())
import piBeaconGlobals as G
import piBeaconUtils as U
U.setLogging()
G.program 		= "copyToTemp"


####-------------------------------------------------------------------------####
def readPopen(cmd):
		"""Runs a shell command via subprocess.Popen and returns its decoded stdout and stderr as a tuple of strings; logs an exception on failure.

		Inputs:
		    cmd (str): Shell command line to execute
		Outputs:
		    tuple: (stdout, stderr) decoded as UTF-8 strings, or None on exception
		"""
		try:
			ret, err = subprocess.Popen(cmd, shell=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE).communicate()
			return ret.decode('utf_8'), err.decode('utf_8')
		except Exception as e:
			U.logger.log(20,"", exc_info=True)


def setupTempDir():
	"""Creates the plugin's temp directory if missing, mounts it as a 2MB tmpfs RAM filesystem if not already mounted, and clears any existing files in it.

	Inputs:
	    None.
	Outputs:
	    None: Creates/mounts the temp directory and removes its contents via shell commands; logs on error
	"""
	try:
		if	not os.path.isdir(G.homeDir+"temp"):
			U.makeDir(G.homeDir + "temp")
		# check if already tempfs type, if not create 
		if readPopen("df | grep tempfs ")[0].find(G.homeDir+"temp") == -1:
			subprocess.call("mount -t tmpfs -o size=2m tmpfs "+G.homeDir+"temp", shell=True)
		U.removeFile(G.homeDir + "temp/*")
	except Exception as e:
		U.logger.log(20,"", exc_info=True)
	return 


if __name__ == "__main__":
	timeLastFile	= 0
	myPID			= str(os.getpid())
	U.killOldPgm(myPID, G.program+".py")

	setupTempDir()

	subprocess.call("chmod a+w -R "+G.homeDir+"*", shell=True)
	subprocess.call("chown -R pi:pi "+G.homeDir+"*", shell=True)
	try:	
		U.touchFile(G.homeDir + "temp/touchFile")
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
				U.touchFile(G.homeDir + "temp/touchFile")

		if not os.path.isfile(G.homeDir+"temp/parameters"):
				doCopy = 3
				
		###print G.program, doCopy 
		if doCopy >0:
				U.logger.log(10,"copying to files to temp dir files={}".format(G.parameterFileList))
				for fileName in G.parameterFileList:
					if os.path.isfile(G.homeDir+fileName):
							cmd = "sudo cp "+G.homeDir+fileName +" " +G.homeDir+"temp/"+fileName
							subprocess.call(cmd, shell=True)
				try:  
					timeLastFile = os.path.getmtime(G.homeDir+"temp/touchFile")
				except:	 timeLastFile = -10
				subprocess.call("chmod a+w -R "  +G.homeDir+"temp/*", shell=True)
				subprocess.call("chown -R pi:pi "+G.homeDir+"temp/*", shell=True)
				time.sleep(10)

		time.sleep(0.5)
