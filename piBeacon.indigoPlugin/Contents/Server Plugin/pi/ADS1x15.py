#!/usr/bin/python
# -*- coding: utf-8 -*-
# by Karl Wachs
# feb 12 2020
# version 1.1 
##
##

## ok for py3


from __future__ import division

import math

import	sys, os, time, json, datetime,subprocess,copy

sys.path.append(os.getcwd())
import	piBeaconUtils	as U
import	piBeaconGlobals as G

G.program = "ADS1x15"

try: import smbus
except: pass



# Copyright (c) 2014 Adafruit Industries
# Author: Tony DiCola
#
# Based on the BMP280 driver with BME280 changes provided by
# David J Taylor, Edinburgh (www.satsignal.eu)
#
# Permission is hereby granted, free of charge, to any person obtaining a copy
# of this software and associated documentation files (the "Software"), to deal
# in the Software without restriction, including without limitation the rights
# to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
# copies of the Software, and to permit persons to whom the Software is
# furnished to do so, subject to the following conditions:
#
# The above copyright notice and this permission notice shall be included in
# all copies or substantial portions of the Software.
#
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
# IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
# FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
# AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
# LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
# OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN
# THE SOFTWARE.



# ===========================================================================
# ADS1x15 Class
#
# Originally written by K. Townsend, Adafruit (https://github.com/adafruit/Adafruit-Raspberry-Pi-Python-Code/tree/master/Adafruit_ADS1x15)
# Updates and new functions implementation by Pedro Villanueva, 03/2013.
# The only error in the original code was in line 57:
#			   __ADS1015_REG_CONFIG_DR_920SPS	 = 0x0050
# should be
#			   __ADS1015_REG_CONFIG_DR_920SPS	 = 0x0060
#
# NOT IMPLEMENTED: Conversion ready pin, page 15 datasheet.
# ===========================================================================

class ADS1x15:
	i2c = None

	# IC Identifiers
	__IC_ADS1015					  = 0x00
	__IC_ADS1115					  = 0x01

	# Pointer Register
	__ADS1015_REG_POINTER_MASK		  = 0x03
	__ADS1015_REG_POINTER_CONVERT	  = 0x00
	__ADS1015_REG_POINTER_CONFIG	  = 0x01
	__ADS1015_REG_POINTER_LOWTHRESH	  = 0x02
	__ADS1015_REG_POINTER_HITHRESH	  = 0x03

	# Config Register
	__ADS1015_REG_CONFIG_OS_MASK	  = 0x8000
	__ADS1015_REG_CONFIG_OS_SINGLE	  = 0x8000	# Write: Set to start a single-conversion
	__ADS1015_REG_CONFIG_OS_BUSY	  = 0x0000	# Read: Bit = 0 when conversion is in progress
	__ADS1015_REG_CONFIG_OS_NOTBUSY	  = 0x8000	# Read: Bit = 1 when device is not performing a conversion

	__ADS1015_REG_CONFIG_MUX_MASK	  = 0x7000
	__ADS1015_REG_CONFIG_MUX_DIFF_0_1 = 0x0000	# Differential P = AIN0, N = AIN1 (default)
	__ADS1015_REG_CONFIG_MUX_DIFF_0_3 = 0x1000	# Differential P = AIN0, N = AIN3
	__ADS1015_REG_CONFIG_MUX_DIFF_1_3 = 0x2000	# Differential P = AIN1, N = AIN3
	__ADS1015_REG_CONFIG_MUX_DIFF_2_3 = 0x3000	# Differential P = AIN2, N = AIN3
	__ADS1015_REG_CONFIG_MUX_SINGLE_0 = 0x4000	# Single-ended AIN0
	__ADS1015_REG_CONFIG_MUX_SINGLE_1 = 0x5000	# Single-ended AIN1
	__ADS1015_REG_CONFIG_MUX_SINGLE_2 = 0x6000	# Single-ended AIN2
	__ADS1015_REG_CONFIG_MUX_SINGLE_3 = 0x7000	# Single-ended AIN3

	__ADS1015_REG_CONFIG_PGA_MASK	  = 0x0E00
	__ADS1015_REG_CONFIG_PGA_6_144V	  = 0x0000	# +/-6.144V range
	__ADS1015_REG_CONFIG_PGA_4_096V	  = 0x0200	# +/-4.096V range
	__ADS1015_REG_CONFIG_PGA_2_048V	  = 0x0400	# +/-2.048V range (default)
	__ADS1015_REG_CONFIG_PGA_1_024V	  = 0x0600	# +/-1.024V range
	__ADS1015_REG_CONFIG_PGA_0_512V	  = 0x0800	# +/-0.512V range
	__ADS1015_REG_CONFIG_PGA_0_256V	  = 0x0A00	# +/-0.256V range

	__ADS1015_REG_CONFIG_MODE_MASK	  = 0x0100
	__ADS1015_REG_CONFIG_MODE_CONTIN  = 0x0000	# Continuous conversion mode
	__ADS1015_REG_CONFIG_MODE_SINGLE  = 0x0100	# Power-down single-shot mode (default)

	__ADS1015_REG_CONFIG_DR_MASK	  = 0x00E0
	__ADS1015_REG_CONFIG_DR_128SPS	  = 0x0000	# 128 samples per second
	__ADS1015_REG_CONFIG_DR_250SPS	  = 0x0020	# 250 samples per second
	__ADS1015_REG_CONFIG_DR_490SPS	  = 0x0040	# 490 samples per second
	__ADS1015_REG_CONFIG_DR_920SPS	  = 0x0060	# 920 samples per second
	__ADS1015_REG_CONFIG_DR_1600SPS	  = 0x0080	# 1600 samples per second (default)
	__ADS1015_REG_CONFIG_DR_2400SPS	  = 0x00A0	# 2400 samples per second
	__ADS1015_REG_CONFIG_DR_3300SPS	  = 0x00C0	# 3300 samples per second (also 0x00E0)

	__ADS1115_REG_CONFIG_DR_8SPS	  = 0x0000	# 8 samples per second
	__ADS1115_REG_CONFIG_DR_16SPS	  = 0x0020	# 16 samples per second
	__ADS1115_REG_CONFIG_DR_32SPS	  = 0x0040	# 32 samples per second
	__ADS1115_REG_CONFIG_DR_64SPS	  = 0x0060	# 64 samples per second
	__ADS1115_REG_CONFIG_DR_128SPS	  = 0x0080	# 128 samples per second
	__ADS1115_REG_CONFIG_DR_250SPS	  = 0x00A0	# 250 samples per second (default)
	__ADS1115_REG_CONFIG_DR_475SPS	  = 0x00C0	# 475 samples per second
	__ADS1115_REG_CONFIG_DR_860SPS	  = 0x00E0	# 860 samples per second

	__ADS1015_REG_CONFIG_CMODE_MASK	  = 0x0010
	__ADS1015_REG_CONFIG_CMODE_TRAD	  = 0x0000	# Traditional comparator with hysteresis (default)
	__ADS1015_REG_CONFIG_CMODE_WINDOW = 0x0010	# Window comparator

	__ADS1015_REG_CONFIG_CPOL_MASK	  = 0x0008
	__ADS1015_REG_CONFIG_CPOL_ACTVLOW = 0x0000	# ALERT/RDY pin is low when active (default)
	__ADS1015_REG_CONFIG_CPOL_ACTVHI  = 0x0008	# ALERT/RDY pin is high when active

	__ADS1015_REG_CONFIG_CLAT_MASK	  = 0x0004	# Determines if ALERT/RDY pin latches once asserted
	__ADS1015_REG_CONFIG_CLAT_NONLAT  = 0x0000	# Non-latching comparator (default)
	__ADS1015_REG_CONFIG_CLAT_LATCH	  = 0x0004	# Latching comparator

	__ADS1015_REG_CONFIG_CQUE_MASK	  = 0x0003
	__ADS1015_REG_CONFIG_CQUE_1CONV	  = 0x0000	# Assert ALERT/RDY after one conversions
	__ADS1015_REG_CONFIG_CQUE_2CONV	  = 0x0001	# Assert ALERT/RDY after two conversions
	__ADS1015_REG_CONFIG_CQUE_4CONV	  = 0x0002	# Assert ALERT/RDY after four conversions
	__ADS1015_REG_CONFIG_CQUE_NONE	  = 0x0003	# Disable the comparator and put ALERT/RDY in high state (default)


	# Dictionaries with the sampling speed values
	# These simplify and clean the code (avoid the abuse of if/elif/else clauses)
	spsADS1115 = {
	8:__ADS1115_REG_CONFIG_DR_8SPS,
	16:__ADS1115_REG_CONFIG_DR_16SPS,
	32:__ADS1115_REG_CONFIG_DR_32SPS,
	64:__ADS1115_REG_CONFIG_DR_64SPS,
	128:__ADS1115_REG_CONFIG_DR_128SPS,
	250:__ADS1115_REG_CONFIG_DR_250SPS,
	475:__ADS1115_REG_CONFIG_DR_475SPS,
	860:__ADS1115_REG_CONFIG_DR_860SPS
	}
	spsADS1015 = {
	128:__ADS1015_REG_CONFIG_DR_128SPS,
	250:__ADS1015_REG_CONFIG_DR_250SPS,
	490:__ADS1015_REG_CONFIG_DR_490SPS,
	920:__ADS1015_REG_CONFIG_DR_920SPS,
	1600:__ADS1015_REG_CONFIG_DR_1600SPS,
	2400:__ADS1015_REG_CONFIG_DR_2400SPS,
	3300:__ADS1015_REG_CONFIG_DR_3300SPS
	}
	# Dictionariy with the programable gains
	pgaADS1x15 = {
	6144:__ADS1015_REG_CONFIG_PGA_6_144V,
	4096:__ADS1015_REG_CONFIG_PGA_4_096V,
	2048:__ADS1015_REG_CONFIG_PGA_2_048V,
	1024:__ADS1015_REG_CONFIG_PGA_1_024V,
	512:__ADS1015_REG_CONFIG_PGA_0_512V,
	256:__ADS1015_REG_CONFIG_PGA_0_256V
	}


	# Constructor
	def __init__(self, address=0x4a, debug=False):
		try:
			self.bus 		= smbus.SMBus(1)
			self.address 	= address
			self.debug 		= debug
		except	Exception as e:
				U.logger.log(30,"", exc_info=True)

	def readADC(self, channel=0, pga=6144, sps=250, singleOrDiff="single"):
		try:
			"Gets a ADC reading  in mV. \
			The sample rate for this mode (single-shot) can be used to lower the noise \
			(low sps) or to lower the power consumption (high sps) by duty cycling, \
			see datasheet page 14 for more info. \
			The pga must be given in mV, see page 13 for the supported values."

			# With invalid channel return -1
			if channel not in [0,1,2,3,"0-1","0-3","1-3","2-3"] :
				if True or (self.debug):
					U.logger.log(30, "ADS1x15: Invalid channel specified: {}".format(channel))
				return -1
			#U.logger.log(20, "ADS1x15: channel:{}, pga:{}, sps:{}, singleOrDiff:{}".format(channel, pga, sps, singleOrDiff))

			# Disable comparator, Non-latching, Alert/Rdy active low
			# traditional comparator, single-shot mode
			config = self.__ADS1015_REG_CONFIG_CQUE_NONE	| \
					 self.__ADS1015_REG_CONFIG_CLAT_NONLAT	| \
					 self.__ADS1015_REG_CONFIG_CPOL_ACTVLOW | \
					 self.__ADS1015_REG_CONFIG_CMODE_TRAD	| \
					 self.__ADS1015_REG_CONFIG_MODE_SINGLE

			# Set sample per seconds, defaults to 250sps
			# If sps is in the dictionary (defined in init) it returns the value of the constant
			# othewise it returns the value for 250sps. This saves a lot of if/elif/else code!
			if ( (sps not in self.spsADS1115) & self.debug):
					U.logger.log(20, "ADS1x15: Invalid pga specified: {}, using 6144mV".format(sps))
			config |= self.spsADS1115.setdefault(sps, self.__ADS1115_REG_CONFIG_DR_250SPS)

			# Set PGA/voltage range, defaults to +-6.144V
			if ( (pga not in self.pgaADS1x15) & self.debug):
				U.logger.log(20, "ADS1x15: Invalid pga specified: {}, using 6144mV".format(sps))
			config |= self.pgaADS1x15.setdefault(pga, self.__ADS1015_REG_CONFIG_PGA_6_144V)

			# Set the channel to be converted
			if singleOrDiff == "single": # single ended pin 
				if   channel == 3: 		config |= self.__ADS1015_REG_CONFIG_MUX_SINGLE_3
				elif channel == 2:		config |= self.__ADS1015_REG_CONFIG_MUX_SINGLE_2
				elif channel == 1:		config |= self.__ADS1015_REG_CONFIG_MUX_SINGLE_1
				else:					config |= self.__ADS1015_REG_CONFIG_MUX_SINGLE_0
			else:
				#  differential 
				if   channel == "2-3":	config |= self.__ADS1015_REG_CONFIG_MUX_DIFF_2_3 
				elif channel == "1-3":	config |= self.__ADS1015_REG_CONFIG_MUX_DIFF_1_3
				elif channel == "0-3":	config |= self.__ADS1015_REG_CONFIG_MUX_DIFF_0_3
				else:					config |= self.__ADS1015_REG_CONFIG_MUX_DIFF_0_1



			# Set 'start single-conversion' bit
			config |= self.__ADS1015_REG_CONFIG_OS_SINGLE

			# Write config register to the ADC
			theBytes = [(config >> 8) & 0xFF, config & 0xFF]
			if self.debug: U.logger.log(20,  "channel  bytes written: {}, {}".format(channel, bytes))
			self.bus.write_i2c_block_data(self.address, self.__ADS1015_REG_POINTER_CONFIG, theBytes)

			# Wait for the ADC conversion to complete
			# The minimum delay depends on the sps: delay >= 1/sps
			# We add 1ms to be sure
			delay = 1.0/sps+0.001
			time.sleep(delay)

			# Read the conversion results
			result = self.bus.read_i2c_block_data(self.address, self.__ADS1015_REG_POINTER_CONVERT, 2)
			# Return a mV value for the ADS1115
			# (Take signed values into account as well)
			val = (result[0] << 8) | (result[1])
			if  val > 0x7FFF:						val = (val - 0xFFFF)*pga/32768.0
			else:									val = ( (result[0] << 8) | (result[1]) )*pga/32768.0
			if self.debug: U.logger.log(20,  "sps:{}, pga:{}, channel:{}, val:{}, result:{}".format( sps, pga, channel, val, result))
			return val

		except	Exception as e:
			U.logger.log(32,"", exc_info=True)
		return ""
#
#################################
def startSensor(devId,i2cADR):
	global SENSOR, sensors, sensor

	try:
		if devId not in SENSOR:
			#U.logger.log(30, u"starting devId:{}".format(devId))
			SENSOR[devId]=ADS1x15(address=i2cADR) 
			return 
	except	Exception as e:
		U.logger.log(30,"", exc_info=True)
	return 

#===========================================================================
# ADS1x15
# ===========================================================================
 
def getValues():
	global SENSOR, sensors, sensor, inputChannel, gain, sps
	global badSensor, i2cAddress


	values = {}
	if sensor not in sensors:
		U.logger.log(30, "error sensor:{} , sensors:{}".format(sensor, sensors))
		return {}  
	#U.logger.log(20, u"getValues i2cAddress {}".format(i2cAddress))
	try:
		for i2c in i2cAddress:
			for devId in i2cAddress[i2c]:
				values[devId] = ""
				#U.logger.log(20, u"getValues devId:{}  inputChannel[devId]:{}".format(devId, inputChannel[devId]))
				v = 0
				if inputChannel[devId].find("-") > -1:
					v =  (SENSOR[devId].readADC(channel=inputChannel[devId] , pga=gain[devId], sps=sps[devId], singleOrDiff="diff"))
				else:
					v =  (SENSOR[devId].readADC(channel=int(inputChannel[devId]), pga=gain[devId], sps=sps[devId], singleOrDiff="single"))
				if type(v) == type(""): 
					badSensor += 1
					return ""

				values[devId] = {"INPUT":round(v,2)}
				#U.logger.log(30, u"getValues    devId: {:14s},  v:{}, gain[devId]:{}, conversionFactor:{}".format(devId, values[devId], gain[devId], conversionFactor))
				

		#U.logger.log(20, u"getValues   v:{}".format( values))
		badSensor = 0
		return values
	except	Exception as e:
		badSensor += 1
		U.logger.log(30,"", exc_info=True)
	return values

# ===========================================================================
# read params
# ===========================================================================


def readParams():
	global sensorList, sensors, sensor, SENSOR
	global sensorRefreshSecs, sendToIndigoEvery, minSendDelta
	global rawOld
	global deltaX, inputChannel, gain, resModel, i2cAddress, sps
	global oldRaw, lastRead

	try:
		inp,inpRaw,lastRead2 = U.doRead(lastTimeStamp=lastRead)

		#U.logger.log(20, " comparisons: {}, {},  {}, ".format(inp == "",lastRead2 == lastRead, inpRaw == oldRaw ) )


		if inp == "": return
		if lastRead2 == lastRead: return
		lastRead   = lastRead2
		if inpRaw == oldRaw: return
		oldRaw	   = inpRaw
		
		externalSensor = False
		sensorList=[]
		sensorsOld= copy.copy(sensors)


		U.getGlobalParams(inp)
		  
		if "sensorList"			in inp:	 sensorList=			 (inp["sensorList"])
		if "sensors"			in inp:	 sensors =				 (inp["sensors"])
		
 
		if sensor not in sensors:
			U.logger.log(30, "{} is not in parameters = not enabled, stopping {}.py".format(G.program, G.program) )
			exit()
			
		try: sensorRefreshSecs	= float(G.sensorRefreshSecs)
		except: pass
		try: minSendDelta		= float(G.minSendDelta)
		except: pass
		try: sendToIndigoEvery	= float(G.sendToIndigoEvery)
		except: pass
				
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
			except:	deltaX[devId] = 0.1

			try:	inputChannel[devId] = sensors[sensor][devId]["input"]
			except:	inputChannel[devId] = "0"

			gain[devId] = 6144
			try:	gain[devId] = int(sensors[sensor][devId]["gain"])
			except:	gain[devId] = 6144
			if str(gain[devId]) not in ["6144","4096","2048","1024","512","256"]: gain[devId] = 6144


			sps[devId] = 250
			try:	sps[devId] = int(sensors[sensor][devId]["sps"])
			except:	sps[devId] = 250


			U.logger.log(30,"==== Start {} ===== @ i2c:{}; inputChannel:{};  deltaX:{}, gain:{}, sps:{}".format(G.program, i2cADDR, inputChannel[devId], deltaX[devId], gain[devId], sps[devId]) )
			startSensor(devId, i2cADDR)
		U.logger.log(30,    "==== Start {}... sendToIndigoEvery:{};minSendDelta:{};  sensorRefreshSecs:{},all i2c->devids:{}".format(G.program, sendToIndigoEvery, minSendDelta, sensorRefreshSecs, i2cAddress))
				
		deldevID={}		   
		for devId in SENSOR:
			if devId not in sensors[sensor]:
				deldevID[devId]=1

		for dd in  deldevID:
			del SENSOR[dd]

		if len(SENSOR) == 0: 
			####exit()
			pass

	except	Exception as e:
		U.logger.log(30,"", exc_info=True)

#################################
#################################
#################################
#################################
#################################
#################################
#################################
def execADS1x15():			 
	global sensorList, sensors, sensor, SENSOR, gain, sps, inputChannel
	global sensorRefreshSecs, sendToIndigoEvery, minSendDelta
	global sValues, displayInfo
	global oldRaw, lastRead
	global deltaX, i2cAddress
	global badSensor

	badSensor			= 0
	i2cAddress			= {}
	gain				= {}
	sps					= {}
	inputChannel		= {}
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
				values = getValues()
				data["sensors"] = {sensor:{}}
				for devId in sensors[sensor]:
					data["sensors"][sensor][devId] ={}
					if devId not in lastData: lastData[devId] = -500.
					if devId not in values: value = ""
					else:					value = values[devId]
					if value == "":
						sensorWasBad = True
						data["sensors"][sensor][devId]["INPUT"] = "badSensor"
						if badSensor > 5: 
							U.logger.log(30," bad sensor")
							U.sendURL(data)
						lastData[devId] =-100.
						continue
					else:
						data["sensors"][sensor][devId] = value
						current = value["INPUT"]
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
execADS1x15()
try: 	G.sendThread["run"] = False; time.sleep(1)
except: pass
sys.exit(0)
