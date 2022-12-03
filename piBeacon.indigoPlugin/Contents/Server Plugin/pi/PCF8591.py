#!/usr/bin/python
# -*- coding: utf-8 -*-
# by Karl Wachs
# feb 12 2020
# version 1.1
##
##	do it in a timed manner not to load the system, is every 1 seconds then 30 senods break
##
from __future__ import division

import math

import	sys, os, time, json, datetime,subprocess,copy

sys.path.append(os.getcwd())
import	piBeaconUtils	as U
import	piBeaconGlobals as G

G.program = "PCF8591"

try: import smbus
except: pass



# ===========================================================================
# PCF8591
# ===========================================================================

#################################
def getValues(devId):
	global sensor, sensors, badSensor, SENSOR
	global input, Vmul

	try:
		data = ""
		if str(devId) not in SENSOR:  return 
		v = 0
		i2cAdd =U.muxTCA9548A(sensors[sensor][devId])
		inp = input[devId].split("-")
		if len(inp) == 2:
			SENSOR[devId].write_byte(i2cAdd,0x40+int(inp[0]))
			SENSOR[devId].read_byte(i2cAdd) # dummy read to start conversion
			v = int(SENSOR[devId].read_byte(i2cAdd))
			SENSOR[devId].write_byte(i2cAdd,0x40+int(inp[1]))
			SENSOR[devId].read_byte(i2cAdd) # dummy read to start conversion
			v -= int(SENSOR[devId].read_byte(i2cAdd))
		else:
			SENSOR[devId].write_byte(i2cAdd,0x40+int(inp[0]))
			SENSOR[devId].read_byte(i2cAdd) # dummy read to start conversion
			v = int(SENSOR[devId].read_byte(i2cAdd))
		U.muxTCA9548Areset()
		data = {"INPUT":v}
		#U.logger.log(20, u"devID {} v={}".format(devId, v))

	except	Exception as e:
		U.logger.log(30,"", exc_info=True)
		data= ""
		U.muxTCA9548Areset()
	return data

#
#################################
def startSensor(devId):
	global SENSOR, sensors, sensor

	try:
		if devId not in SENSOR :
			i2cAdd = U.muxTCA9548A(sensors[sensor][devId])
			SENSOR[devId]=smbus.SMBus(1)
			U.muxTCA9548Areset()
	except	Exception as e:
		U.logger.log(30,"", exc_info=True)
		U.muxTCA9548Areset()
	return 
		
# ===========================================================================
# sensor end
# ===========================================================================

 
# ===========================================================================
# read params
# ===========================================================================


def readParams():
	global sensorList, sensors, sensor, SENSOR
	global sensorRefreshSecs, sendToIndigoEvery, minSendDelta
	global rawOld
	global deltaX, input
	global oldRaw, lastRead
	try:



		inp,inpRaw,lastRead2 = U.doRead(lastTimeStamp=lastRead)
		if inp == "": return
		if lastRead2 == lastRead: return
		lastRead   = lastRead2
		if inpRaw == oldRaw: return
		oldRaw	   = inpRaw
		
		externalSensor=False
		sensorList=[]
		sensorsOld= copy.copy(sensors)


		U.getGlobalParams(inp)
		  
		if "sensorList"			in inp:	 sensorList=			 (inp["sensorList"])
		if "sensors"			in inp:	 sensors =				 (inp["sensors"])
		
 
		if sensor not in sensors:
			U.logger.log(30, G.program+" is not in parameters = not enabled, stopping "+G.program+".py" )
			exit()
			
		try: sensorRefreshSecs	= float(G.sensorRefreshSecs)
		except: pass
		try: minSendDelta		= float(G.minSendDelta)
		except: pass
		try: sendToIndigoEvery	= float(G.sendToIndigoEvery)
		except: pass
				
		for devId in sensors[sensor]:

			i2cAddress = U.getI2cAddress(sensors[sensor][devId], default ="")

			try:	sendToIndigoEvery = float(sensors[sensor][devId]["sendToIndigoEvery"])
			except: pass
			try:	minSendDelta = float(sensors[sensor][devId]["minSendDelta"])
			except: pass
			try:	sensorRefreshSecs = float(sensors[sensor][devId]["sensorRefreshSecs"])
			except: pass

			try:	deltaX[devId] = float(sensors[sensor][devId]["deltaX"])/100.
			except:	deltaX[devId] = 0.1

			try:	input[devId] = (sensors[sensor][devId]["input"])
			except:	input[devId] = "0"

			U.logger.log(30,"==== Start "+G.program+" ===== @ i2c:{};inputC:{};  deltaX:{}".format(i2cAddress, input[devId], deltaX[devId]))
			startSensor(devId)
		U.logger.log(30,"==== Start "+G.program+" ===== @ sendToIndigoEvery:{};minSendDelta:{};  sensorRefreshSecs:{}".format(sendToIndigoEvery, minSendDelta, sensorRefreshSecs))
				
		deldevID={}		   
		for devId in SENSOR:
			if devId not in sensors[sensor]:
				deldevID[devId]=1
		for dd in  deldevID:
			del SENSOR[dd]
		if len(SENSOR) ==0: 
			####exit()
			pass

	except	Exception as e:
		U.logger.log(30,"", exc_info=True)

###############################
#################################
#################################
#################################
#################################
#################################
#################################
#################################
def execPCF():			 
	global sensorList, sensors, sensor, SENSOR, input
	global sensorRefreshSecs, sendToIndigoEvery, minSendDelta
	global sValues, displayInfo
	global oldRaw, lastRead
	global input, deltaX
	global badSensor

	badSensor			= 0
	input				= {}
	sensorRefreshSecs	= 5
	minSendDelta		= 4
	sendToIndigoEvery	= 90
	oldRaw				= ""
	lastRead			= 0
	loopCount			= 0
	deltaX				= {}
	sensorList			= []
	sensors				= {}
	SENSOR 				= {}
	quick				= False
	myPID				= str(os.getpid())

	sensor = G.program

	U.setLogging()

	U.killOldPgm(myPID,G.program+".py")# kill old instances of myself if they are still running

	readParams()



	myPID		= str(os.getpid())
	U.killOldPgm(myPID,G.program+".py")# kill old instances of myself if they are still running

	NSleep= int(sensorRefreshSecs)
	if G.networkType  in G.useNetwork and U.getNetwork() == "off": 
		if U.getIPNumber() > 0:
			U.logger.log(30,"no ip number working, giving up")
			time.sleep(10)

	eth0IP, wifi0IP, G.eth0Enabled,G.wifiEnabled = U.getIPCONFIG()


	tt					= time.time()
	badSensors			= {}
	lastData			= {}
	lastMsg				= 0
	G.tStart			= tt
	lastMeasurement		= tt
	lastRead			= tt

	while True:
		try:
			sendToIndigo = False
			tt	 = time.time()
			lastMeasurement		= tt
			data = {"sensors": {}}
			if sensor in sensors:
				data["sensors"] = {sensor:{}}
				for devId in sensors[sensor]:
					data["sensors"][sensor][devId] ={}
					if devId not in lastData: lastData[devId] = -500.
					values = getValues(devId)
					if values == "":
						sensorWasBad = True
						data["sensors"][sensor][devId]["INPUT"] = "badSensor"
						if badSensor > 5: 
							U.logger.log(30," bad sensor")
							U.sendURL(data)
						lastData[devId] =-100.
						continue
					else:
						data["sensors"][sensor][devId] = values
						current = values["INPUT"]
						delta	= current-lastData[devId]
						deltaN	= abs(delta) / max (0.5,(current+lastData[devId])/2.)
				
					if ( ( deltaN > deltaX[devId]							) or 
						 (	tt - abs(sendToIndigoEvery) > G.lastAliveSend	) or  
						 ( quick											)   ) and  \
					   ( ( tt - G.lastAliveSend > minSendDelta				)   ):
							sendToIndigo = True
							lastData[devId]	= current
			#U.logger.log(20, u"data{}".format(data))
			
			if sendToIndigo:
				U.sendURL(data)
			loopCount += 1

			U.makeDATfile(G.program, data)
			quick = U.checkNowFile(G.program)				 
			U.echoLastAlive(G.program)

			if not quick:
				tt= time.time()
				if tt - lastRead > 5.:	
					readParams()
					lastRead = tt
			if not quick:
				time.sleep(max (0,time.time() - lastMeasurement + sensorRefreshSecs) )
		except Exception as e:
			U.logger.log(30,"", exc_info=True)
			time.sleep(5.)
execPCF()
try: 	G.sendThread["run"] = False; time.sleep(1)
except: pass
sys.exit(0)
