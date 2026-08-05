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
		"""Initializes a MAX44009 ambient light sensor driver instance by opening the given I2C bus and storing the device's I2C address.

		Inputs:
		    bus (int): I2C bus number passed to smbus.SMBus (default 1)
		    address (int): I2C device address (default 0x4a)
		Outputs:
		    None: Opens the smbus.SMBus handle and stores it on the instance
		"""
		self._bus = smbus.SMBus(bus)
		self.address = address

	def setParams(self, cont=0, manual=0, cdr=0, timer=0):
		"""Packs the continuous, manual, current-division-ratio, and integration-timer bits into the MAX44009 configuration byte and writes it to the configuration register over I2C.

		Inputs:
		    cont (int): Continuous-mode bit (0/1), shifted to bit 7
		    manual (int): Manual-mode bit (0/1), shifted to bit 6
		    cdr (int): Current-division-ratio bit (0/1), shifted to bit 3
		    timer (int): Integration timer value (lower 3 bits)
		Outputs:
		    None: Writes the assembled config byte to the MAX44009 configuration register
		"""
		config = (cont & 0x01) << 7 | (manual & 0x01) << 6 | (cdr & 0x01) << 3 | timer & 0x07
		self._bus.write_byte_data(self.address,self._REG_CONFIGURATION, config)

	def getLuminosity(self):
		"""Reads the two lux data bytes from the MAX44009, extracts the exponent and mantissa, and computes the ambient light level in lux.

		Inputs:
		    None.
		Outputs:
		    float: Computed luminance in lux
		"""
		data      = self._bus.read_i2c_block_data(self.address, self._REG_LUX_HIGH_BYTE, 2)
		exponent  = (data[0] & 0xF0) >> 4
		mantissa  = ((data[0] & 0x0F) << 4) | (data[1] & 0x0F)
		luminance = ((2 ** exponent) * mantissa) * 0.045
		return luminance
#
#################################
def startSensor(devId,i2cADR):
	"""Lazily creates a MAX44009 sensor object for a device id at the given I2C address if not already present, and configures it (continuous off, manual off/autorange, cdr 0, timer 0).

	Inputs:
	    devId (str): Device identifier used as key in the SENSOR registry
	    i2cADR (int): I2C address passed to the sensor constructor
	Outputs:
	    None: Registers and configures the sensor object; logs on error
	"""
	global SENSOR, sensors, sensor

	try:
		if devId not in SENSOR:
			SENSOR[devId]=SENSORclass(address=i2cADR) 
			#                       measure every 800mS, 	not Man= autorange, all cur goes into ADC,  not used if manual =0
			SENSOR[devId].setParams(cont=0, 		   		manual=0, 			cdr=0, 					timer=0)
			return 
	except Exception as e:
		U.logger.log(20,"", exc_info=True)
	return 

#===========================================================================
# ADS1x15
# ===========================================================================
 
def getValues():
	"""Iterates over all known I2C addresses and their device ids, reads luminosity from each MAX44009 sensor, and returns a dict of per-device illuminance values rounded to two decimals; resets or increments the bad-sensor counter accordingly.

	Inputs:
	    None.
	Outputs:
	    dict: Maps device id to {'illuminance': value}; empty dict on error or unknown sensor
	"""
	global SENSOR, sensors, sensor
	global badSensor, i2cAddress


	values = {}
	if sensor not in sensors:
		U.logger.log(20, "error sensor:{} , sensors:{}".format(sensor, sensors))
		return {}  
	try:
		for i2c in i2cAddress:
			for devId in i2cAddress[i2c]:
				values[devId] = ""
				values[devId] = {"illuminance":round(SENSOR[devId].getLuminosity(),2)}
		badSensor = 0
		return values
	except Exception as e:
		badSensor += 1
		U.logger.log(20,"", exc_info=True)
	return values

# ===========================================================================
# read params
# ===========================================================================


def readParams():
	"""Reads the latest plugin parameter file, and if changed, parses global params and the sensors config, building the i2c-address-to-device map, per-device timing/delta settings, and starting each MAX44009 sensor; removes sensor objects no longer in the config. Exits if this sensor is not enabled.

	Inputs:
	    None.
	Outputs:
	    None: Updates module globals (sensors, i2cAddress, deltaX, SENSOR, timing) and starts/stops sensors; logs on error
	"""
	global sensorList, sensors, sensor, SENSOR
	global sensorRefreshSecs, sendToIndigoEvery, minSendDelta
	global rawOld
	global deltaX, input, gain, resModel, i2cAddress
	global oldRaw, lastRead

	try:
		inp, inpRaw, lastRead2 = U.doRead(lastTimeStamp=lastRead)
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
			U.logger.log(20, G.program+" is not in parameters = not enabled, stopping "+G.program+".py" )
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
		U.logger.log(20,	"==== Start {}... sendToIndigoEvery:{};minSendDelta:{};  sensorRefreshSecs:{},all i2c->devids:{}, detltaX:{}".format(G.program, sendToIndigoEvery, minSendDelta, sensorRefreshSecs, i2cAddress, deltaX))
				
		deldevID={}		   
		for devId in SENSOR:
			if devId not in sensors[sensor]:
				deldevID[devId]=1

		for dd in  deldevID:
			del SENSOR[dd]

		if len(SENSOR) == 0: 
			####exit()
			pass

	except Exception as e:
		U.logger.log(20,"", exc_info=True)

#################################
#################################
#################################
#################################
#################################
#################################
#################################
def execMAX44009():			 
	"""Main run loop for the MAX44009 light-sensor process: initializes globals, kills old instances, loads params, then continuously reads illuminance from each device, decides when to send to Indigo based on delta/interval thresholds, writes data/DAT files, refreshes params periodically, and sleeps between cycles.

	Inputs:
	    None.
	Outputs:
	    None: Runs an infinite measurement/reporting loop sending data to Indigo and writing files
	"""
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
			U.logger.log(20,"no ip number working, giving up")
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
							U.logger.log(20," bad sensor")
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
		except Exception as e:
			U.logger.log(20,"", exc_info=True)
			time.sleep(5.)
execMAX44009()
try: 	G.sendThread["run"] = False; time.sleep(1)
except: pass
sys.exit(0)
