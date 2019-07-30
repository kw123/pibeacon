#!/usr/bin/env python
# -*- coding: utf-8 -*-
# by Karl Wachs
# march 1 2016
# exampel program to get data and send it to indigo
import	sys
import os
import time
import json
import datetime
import subprocess
import copy

sys.path.append(os.getcwd())
import	piBeaconUtils	as U
import	piBeaconGlobals as G
G.program = "launchpgm"


# ===========================================================================
# read params do not change
# ===========================================================================
def readParams():
		global debug, sensorList,launchCommand, launchCheck,sensorRefreshSecs, sensors, minSendDelta

		sensorList	= "0"
		oldlaunchCommand = copy.copy(launchCommand)
		inp,inRaw = U.doRead()

		U.getGlobalParams(inp)
		if u"debugRPI"			in inp:	 G.debug=					 int(inp["debugRPI"]["debugRPImystuff"])
		if "sensors"			in inp:	 sensors =					 (inp["sensors"])

		if G.program not in sensors: 
			exit()
		sensor = sensors[G.program]
		for id in sensor:
			if "launchCommand"	in sensor[id]:	launchCommand[id] =				sensor[id]["launchCommand"]
			if "launchCheck"  in sensor[id]:	launchCheck[id]	  =				sensor[id]["launchCheck"]
			try:
				xx = sensors[sensor][devId]["sensorRefreshSecs"].split("#")
				sensorRefreshSecs = float(xx[0]) 
			except:
				sensorRefreshSecs = 100	   

			try:
				if "minSendDelta" in sensors[sensor][devId]: 
					minSendDelta= float(sensors[sensor][devId]["minSendDelta"])/100.
			except:
				minSendDelta = 5.

		# check if anything new
		if id not in oldlaunchCommand or launchCommand[id] != oldlaunchCommand[id]:
			startSensors(launchCommand[id])

		if id in oldlaunchCommand and id not in	 launchCommand:
			stopSensor(launchCommand[id])



# ===========================================================================
# stop	launch cmd
# ===========================================================================

def stopSensors(launchCmd):
		try:
			# do your init here
			U.killOldPgm(myPID, launchCmd)
			## add any init code here for address # addr
			U.logger.log(30, u"stopping	" + unicode(launchCmd) )
		except	Exception, e:
			U.logger.log(30, u"in Line {} has error={}".format(sys.exc_traceback.tb_lineno, e))
			U.logger.log(30, u"launchCmd used: " + unicode(launchCmd) )
# ===========================================================================
# start	 launch cmd
# ===========================================================================

def startSensors(launchCmd):
		try:
			# do your init here
			os.system(launchCmd+" &")
			## add any init code here for address # addr
			U.logger.log(30, u"starting	" + unicode(launchCmd) )
		except	Exception, e:
			U.logger.log(30, u"in Line {} has error={}".format(sys.exc_traceback.tb_lineno, e))
			U.logger.log(30, u"launchCmd used: " + unicode(launchCmd) )
# ===========================================================================
# start	 launch cmd
# ===========================================================================

def checkIfRunning(check):
		try:
			# do your init here
			if check !="": 
				return "running" if U.pgmStillRunning(check) else "not running"
			else: 
				return "not checked"
		except	Exception, e:
			U.logger.log(30, u"in Line {} has error={}".format(sys.exc_traceback.tb_lineno, e))
			U.logger.log(30, u"checking used: " + unicode(check) )


# ===========================================================================
# sensor end
# ===========================================================================


# ===========================================================================
# Main, should ok as is
# ===========================================================================


global debug, sensorList, externalSensor,launchCommand, launchCheck,indigoIds, ipAddress, sensors, minSendDelta, sensorRefreshSecs

debug			  = 5 # will be overwritten in readParams
nInputs			  = 10 # number of input channels 1...10 max

loopCount		  = 0  # for loop,	not used could be deleted, but you might need it
minSendDelta	  = 5.
sensorRefreshSecs = 10 # will be overwritten in readParams, number of seconds to sleep in each loop
sensorList		  = [] # list of sensor, we are looking for "mysensors"
launchCommand	  = {}	# this is teh command we will launch
launchCheck		  = {}	# this is teh ps -ef string that will check if command is running
sensor			  = G.program
U.setLogging()

readParams()		   # get parameters send from indigo

if U.getIPNumber() > 0:
	print G.program+ " no ip number	 exit "
	time.sleep(10)
	exit()

myPID			  = str(os.getpid())
U.killOldPgm(myPID, G.program+".py")# kill old instances of myself if they are still running

quick	 = False
lastData = {}
loopCount = 0
lastMsg =0
while True:	 # loop for ever
		loopCount +=1
		data={}
		try:
			if sensor in sensors:#
				data["sensors"]={sensor:{}}
				for id in sensors[sensor]:
					data["sensors"][sensor][id] ={}
					v  = checkIfRunning(launchCheck[id])
					if v != "not checked":
						if v == "not running":
							startSensors(launchCommand[id])
							v = checkIfRunning(launchCheck[id])
					data["sensors"][sensor][id]["status"]  = v

			### send data to plugin
			if loopCount%1 == 0 or quick or lastData != data: 
				if data !={} and ( time.time() -lastMsg > minSendDelta	 ):
					lastMsg = time.time()
					U.sendURL(data, squeeze=False)
				lastData = copy.copy(data)
			
			# check if we should send data now, requested by plugin
			quick = U.checkNowFile(G.program)				 

			# make alive file for mast to signal we are still running
			if loopCount %20 ==0:
				U.echoLastAlive(G.program)

		except	Exception, e :
			U.logger.log(30, u"in Line {} has error={}".format(sys.exc_traceback.tb_lineno, e))

		time.sleep(sensorRefreshSecs) # sleep the requested amount
		readParams()  # check if we have new parameetrs

sys.exit(0)		   
