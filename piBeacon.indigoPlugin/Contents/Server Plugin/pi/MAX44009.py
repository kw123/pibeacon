#!/usr/bin/python
# -*- coding: utf-8 -*-
# by Karl Wachs
# April 16 2020
# version 1.1 
##
##
from __future__ import division

import math

import	sys, os, time, json, datetime,subprocess,copy

sys.path.append(os.getcwd())
import	piBeaconUtils	as U
import	piBeaconGlobals as G


### simple fully automatic lux sensor 0.045 .. 188,000 lux
G.program = "MAX44009"

try: import smbus
except: pass


class SENSORclass():

	_REG_INTERRUPT_STATUS 	= 0x00
	_REG_INTERRUPT_ENABLE 	= 0x01
	_REG_CONFIGURATION		= 0x02
	_REG_LUX_HIGH_BYTE		= 0x03
	_REG_LUX_LOW_BYTE		= 0x04
	_REG_UPPER_THRESHOLD  	= 0x05
	_REG_LOWER_THRESHOLD  	= 0x06
	_REG_TIMER_THRESHOLD  	= 0x07
	def __init__(self, bus=1, address=0x4a):
		self._bus = smbus.SMBus(bus)
		self.address = address

	def setParams(self, cont=0, manual=0, cdr=0, timer=0):
		config = (cont & 0x01) << 7 | (manual & 0x01) << 6 | (cdr & 0x01) << 3 | timer & 0x07
		self._bus.write_byte_data(self.address,self._REG_CONFIGURATION, config)

	def getLuminosity(self):
		data      = self._bus.read_i2c_block_data(self.address, self._REG_LUX_HIGH_BYTE, 2)
		exponent  = (data[0] & 0xF0) >> 4
		mantissa  = ((data[0] & 0x0F) << 4) | (data[1] & 0x0F)
		luminance = ((2 ** exponent) * mantissa) * 0.045
		return luminance
#
#################################
def startSensor(devId,i2cADR):
	global SENSOR, sensors, sensor

	try:
		if devId not in SENSOR:
			SENSOR[devId]=SENSORclass(address=i2cADR) 
			#                       measure every 800mS, 	not Man= autorange, all cur goes into ADC,  not used if manual =0
	 		SENSOR[devId].setParams(cont=0, 		   		manual=0, 			cdr=0, 					timer=0)
			return 
	except	Exception, e:
		U.logger.log(20, u"in Line {} has error={}".format(sys.exc_traceback.tb_lineno, e))
	return 

#===========================================================================
# ADS1x15
# ===========================================================================
 
def getValues():
	global SENSOR, sensors, sensor
	global badSensor, i2cAddress


	values = {}
	if sensor not in sensors:
		U.logger.log(30, "error sensor:{} , sensors:{}".format(sensor, sensors))
		return {}  
	try:
		for i2c in i2cAddress:
			for devId in i2cAddress[i2c]:
				values[devId] = ""
				values[devId] = {"illuminance":round(SENSOR[devId].getLuminosity(),2)}
		badSensor = 0
		return values
	except	Exception, e:
		badSensor += 1
		U.logger.log(30, u"in Line {} has error={}".format(sys.exc_traceback.tb_lineno, e))
	return values

# ===========================================================================
# read params
# ===========================================================================


def readParams():
	global sensorList, sensors, sensor, SENSOR
	global sensorRefreshSecs, sendToIndigoEvery, minSendDelta
	global rawOld
	global deltaX, input, gain, resModel, i2cAddress
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
				
		for devId in sensors[sensor]:

			i2cADDR = U.getI2cAddress(sensors[sensor][devId], default ="")
			if i2cADDR not in i2cAddress: i2cAddress[i2cADDR] =[]
			if devId not in i2cAddress[i2cADDR]:
				i2cAddress[i2cADDR].append(devId)

			try:	sendToIndigoEvery = float(sensors[sensor][devId]["sendToIndigoEvery"])
			except: pass
			try:	minSendDelta = float(sensors[sensor][devId]["minSendDelta"])
			except: pass
			try:	sensorRefreshSecs = float(sensors[sensor][devId]["sensorRefreshSecs"])
			except: pass

			try:	deltaX[devId] = float(sensors[sensor][devId]["deltaX"])/100.
			except:	deltaX[devId] = 0.05 # =5%


			startSensor(devId, i2cADDR)
		U.logger.log(30,	"==== Start {}... sendToIndigoEvery:{};minSendDelta:{};  sensorRefreshSecs:{},all i2c->devids:{}, detltaX:{}".format(G.program, sendToIndigoEvery, minSendDelta, sensorRefreshSecs, i2cAddress, deltaX))
				
		deldevID={}		   
		for devId in SENSOR:
			if devId not in sensors[sensor]:
				deldevID[devId]=1

		for dd in  deldevID:
			del SENSOR[dd]

		if len(SENSOR) == 0: 
			####exit()
			pass

	except	Exception, e:
		U.logger.log(30, u"in Line {} has error={}".format(sys.exc_traceback.tb_lineno, e))

#################################
#################################
#################################
#################################
#################################
#################################
#################################
def execMAX44009():			 
	global sensorList, sensors, sensor, SENSOR
	global sensorRefreshSecs, sendToIndigoEvery, minSendDelta
	global oldRaw, lastRead
	global deltaX, i2cAddress
	global badSensor

	badSensor			= 0
	i2cAddress			= {}
	sensorRefreshSecs	= 3
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
				values = getValues()
				data["sensors"] = {sensor:{}}
				for devId in sensors[sensor]:
					data["sensors"][sensor][devId] ={}
					if devId not in lastData: lastData[devId] = -500.
					if devId not in values: value = ""
					else:					value = values[devId]
					if value == "":
						sensorWasBad = True
						data["sensors"][sensor][devId]["illuminance"] = "badSensor"
						if badSensor > 5: 
							U.logger.log(30," bad sensor")
							U.sendURL(data)
						lastData[devId] =-100.
						continue
					else:
						data["sensors"][sensor][devId] = value
						current = value["illuminance"]
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
		except Exception, e:
			U.logger.log(50, u"in Line {} has error={}".format(sys.exc_traceback.tb_lineno, e))
			time.sleep(5.)
execMAX44009()
try: 	G.sendThread["run"] = False; time.sleep(1)
except: pass
sys.exit(0)
