#!/usr/bin/python
# -*- coding: utf-8 -*-
# by Karl Wachs
# 2018-01-28
# version 0.1 
##
##
#! /usr/bin/env python
# -*- coding: utf-8 -*-
####################

import sys, os, time, json, datetime,subprocess,copy
import math
import copy
import logging
from collections import OrderedDict
import smbus


sys.path.append(os.getcwd())
import	piBeaconUtils	as U
import	piBeaconGlobals as G
G.program = "sgp30"

#! /usr/bin/env python
# -*- coding: utf-8 -*-
####################

# The MIT License (MIT)
#
# Copyright (c) 2017 ladyada for Adafruit Industries
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
"""
`adafruit_sgp30`
====================================================

I2C driver for SGP30 Sensirion VoC sensor

* Author(s): ladyada
"""


# pylint: disable=bad-whitespace
_SGP30_DEFAULT_I2C_ADDR	 = 0x58
_SGP30_FEATURESET		 = 0x0020

_SGP30_CRC8_POLYNOMIAL	 = 0x31
_SGP30_CRC8_INIT		 = 0xFF
# pylint: enable=bad-whitespace

class SGP30_class:
	"""
	A driver for the SGP30 gas sensor.
	"""

	def __init__(self, address=_SGP30_DEFAULT_I2C_ADDR):
		"""Initialize the sensor, get the serial # and verify that we found a proper SGP30"""
		self.bus		 = smbus.SMBus(1)
		self.i2c_address = address

		# get unique serial, its 48 bits so we store in an array
		self.serial		= self._i2c_read([0x36, 0x82], 3,  0.01)
		# get featuerset
		self.featureset = self._i2c_read([0x20, 0x2f], 1,  0.01)
		if self.featureset[0] != _SGP30_FEATURESET:
			raise RuntimeError('SGP30 Not detected')
		self.iaq_init()

	def iaq_init(self):
		"""Initialize the IAQ algorithm"""
		return self._i2c_write([0x20, 0x03], 0.01)

	def iaq_measure(self):
		"""Measure the CO2eq and TVOC"""
		return self._i2c_read( [0x20, 0x08], 2, 0.05)

	def get_iaq_baseline(self):
		"""Retreive the IAQ algorithm baseline for CO2eq and TVOC"""
		return self._i2c_read( [0x20, 0x15], 2, 0.01)


	def set_iaq_baseline(self, co2eq, tvoc):
		"""Set the previously recorded IAQ algorithm baseline for CO2eq and TVOC"""
		if co2eq == 0 and tvoc == 0:
			raise RuntimeError('Invalid baseline')
		buf = []
		for value in [tvoc, co2eq]:
			arr = [value >> 8, value & 0xFF]
			arr.append(self._generate_crc(arr))
			buf += arr
		return self._i2c_write( [0x20, 0x1e] + buf, 0.01)

	def _i2c_write(self, command, delay):
		self.bus.write_i2c_block_data(self.i2c_address, command[0], command[1:])
		time.sleep(delay)



	def _i2c_read(self, command,  reply_size, delay):
		"""Run an SGP command query, get a reply and CRC results if necessary"""
		self.bus.write_i2c_block_data(self.i2c_address, command[0], command[1:])
		time.sleep(delay)
		crc_result = self.bus.read_i2c_block_data(self.i2c_address, 0,reply_size * (2+1))
		result = []
		for i in range(reply_size):
			word = [crc_result[3*i], crc_result[3*i+1]]
			crc = crc_result[3*i+2]
			if self._generate_crc(word) != crc:
				raise RuntimeError('CRC Error')
			result.append(word[0] << 8 | word[1])
		return result

	def _generate_crc(self, data):
		"""8-bit CRC algorithm for checking data"""
		crc = _SGP30_CRC8_INIT
		# calculates 8-Bit checksum with given polynomial
		for byte in data:
			crc ^= byte
			for _ in range(8):
				if crc & 0x80:
					crc = (crc << 1) ^ _SGP30_CRC8_POLYNOMIAL
				else:
					crc <<= 1
		return crc & 0xFF


 # ===========================================================================
# read params
# ===========================================================================

#################################		 
def readParams():
	global sensorList, sensors, logDir, sensor,	 sensorRefreshSecs, displayEnable
	global rawOld
	global deltaX, sgp30, minSendDelta
	global oldRaw, lastRead
	global startTime, lastBaseLine
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
			

		U.logger.log(30, G.program+" reading new parameter file" )

		if sensorRefreshSecs == 91:
			try:
				xx	   = str(inp["sensorRefreshSecs"]).split("#")
				sensorRefreshSecs = float(xx[0]) 
			except:
				sensorRefreshSecs = 91	  
		deltaX={}
		restart = False
		for devId in sensors[sensor]:
			deltaX[devId]  = 0.1
			old = sensorRefreshSecs
			try:
				if "sensorRefreshSecs" in sensors[sensor][devId]:
					xx = sensors[sensor][devId]["sensorRefreshSecs"].split("#")
					sensorRefreshSecs = float(xx[0]) 
			except:
				sensorRefreshSecs = 91	  
			if old != sensorRefreshSecs: restart = True

			
			i2cAddress = U.getI2cAddress(sensors[sensor][devId], default ="")

			old = deltaX[devId]
			try:
				if "deltaX" in sensors[sensor][devId]: 
					deltaX[devId]= float(sensors[sensor][devId]["deltaX"])/100.
			except:
				deltaX[devId] = 0.1
			if old != deltaX[devId]: restart = True

			old = minSendDelta
			try:
				if "minSendDelta" in sensors[sensor][devId]: 
					minSendDelta= float(sensors[sensor][devId]["minSendDelta"])
			except:
				minSendDelta = 5.
			if old != minSendDelta: restart = True

				
			if devId not in sgp30sensor or	restart:
				lastBaseLine[devId] = time.time() - 21 
				startSensor(devId, i2cAddress)
				if sgp30sensor[devId] =="":
					return
			U.logger.log(30," new parameters read: i2cAddress:" +unicode(i2cAddress) +";	 minSendDelta:"+unicode(minSendDelta)+
					   ";  deltaX:"+unicode(deltaX[devId])+";  sensorRefreshSecs:"+unicode(sensorRefreshSecs) )
				
		deldevID={}		   
		for devId in sgp30sensor:
			if devId not in sensors[sensor]:
				deldevID[devId]=1
		for dd in  deldevID:
			del sgp30sensor[dd]
		if len(sgp30sensor) ==0: 
			####exit()
			pass


	except	Exception, e:
		U.logger.log(30, u"in Line {} has error={}".format(sys.exc_traceback.tb_lineno, e))
		print sensors[sensor]
		



#################################
def startSensor(devId,i2cAddress):
	global sensors,sensor
	global startTime
	global sgp30sensor
	U.logger.log(30,"==== Start "+G.program+" ===== @ i2c= " +unicode(i2cAddress))
	startTime =time.time()


	i2cAdd = U.muxTCA9548A(sensors[sensor][devId]) # switch mux on if requested and use the i2c address of the mix if enabled
	
	try:
		sgp30sensor[devId]	=  SGP30_class(address=i2cAdd)
		U.logger.log(30, "SGP30 serial #{}".format(unicode([hex(i) for i in sgp30sensor[devId].serial])) )
		U.logger.log(30, "featureset   {}".format(unicode([hex(i) for i in sgp30sensor[devId].featureset]))  )

		sgp30sensor[devId].iaq_init()
		#sgp30.set_iaq_baseline(0x8973, 0x8aae)
		setBaseLine(devId)
				
	except	Exception, e:
		U.logger.log(30, u"in Line {} has error={}".format(sys.exc_traceback.tb_lineno, e))
		sgp30sensor[devId]	 =""
	time.sleep(.1)

	U.muxTCA9548Areset()


#################################
def setBaseLine(devId):
	global sensors,sensor
	global startTime
	global sgp30sensor, lastBaseLine
	if time.time() - lastBaseLine[devId] < 20: return 
	
	for ii in range(100):
			co2eq_base, tvoc_base = sgp30sensor[devId].get_iaq_baseline()
			U.logger.log(10, "%d **** Baseline values: CO2eq = %d, TVOC = %d" % (ii,co2eq_base, tvoc_base) )
			if co2eq_base !=0: break 
			co2eq, tvoc = sgp30sensor[devId].iaq_measure()
			time.sleep(1)
	lastBaseLine[devId] = time.time()



#################################
def getValues(devId):
	global sensor, sensors,	 sgp30sensor, badSensor
	global startTime
	global lastMeasurement
	global lastBaseLine
	global lastCO2, lastVOC

	ret = ""
	try:
		if sgp30sensor[devId] =="":
			badSensor +=1
			return "badSensor"
		if time.time() - lastBaseLine[devId] > 1000:
			setBaseLine(devId)
			time.sleep(10)
		CO2	 = 0.
		VOC	 = 0.
		n	 = 0
		fail = 0
		i2cAdd = U.muxTCA9548A(sensors[sensor][devId]) # switch mux on if requested and use the i2c address of the mix if enabled
		for ii in range(20):
			try:	co2eq, tvoc = sgp30sensor[devId].iaq_measure()
			except: continue
			if co2eq >0 and tvoc > 0:
				if lastVOC != 0 and fail < 3:
					if abs(co2eq - lastCO2) > 10: 
						fail+=1
						continue  
					if abs(tvoc	 - lastVOC) > 3:  
						fail +=1
						continue  
				CO2 += co2eq
				VOC += tvoc
				n	+= 1.
				#print lastCO2, lastVOC, n, ii, co2eq, tvoc, CO2/n, VOC/n
				if n > 6: break
				time.sleep(1)
		if CO2 == 0: 
			 badSensor+=1
		else:	 
			lastCO2 =  CO2/n
			lastVOC =  VOC/n
			ret	 = {"CO2":	 ( "%d"%( CO2/n	 ) ).strip(), 
					"VOC":	 ( "%d"%( VOC/n	 ) ).strip()}
			#print ret
			U.logger.log(10, unicode(ret)) 
			badSensor = 0
	except	Exception, e:
		U.logger.log(30, u"in Line {} has error={}".format(sys.exc_traceback.tb_lineno, e))
		badSensor+=1
		if badSensor >3: ret = "badSensor"
	U.muxTCA9548Areset()
	return ret





############################################
global rawOld
global sensor, sensors, badSensor
global deltaX, sgp30sensor, minSendDelta
global	lastRead
global startTime,  lastMeasurement, lastBaseLine
global lastCO2, lastVOC

lastBaseLine				= {}
	
lastCO2						= 0
lastVOC						= 0

startTime					= time.time()
lastMeasurement				= time.time()
oldRaw						= ""
lastRead					= 0
minSendDelta				= 5.
loopCount					= 0
sensorRefreshSecs			= 91
NSleep						= 100
sensorList					= []
sensors						= {}
sensor						= G.program
quick						= False
display						= "0"
output						= {}
badSensor					= 0
sensorActive				= False
loopSleep					= 0.5
rawOld						= ""
sgp30sensor					  ={}
deltaX						  = {}
displayEnable				= 0
U.setLogging()

myPID		= str(os.getpid())
U.killOldPgm(myPID,G.program+".py")# kill old instances of myself if they are still running


if U.getIPNumber() > 0:
	time.sleep(10)
	exit()
readParams()

time.sleep(1)

lastRead = time.time()

U.echoLastAlive(G.program)

#					  used for deltax comparison to trigger update to indigo
lastValues0			= {"CO2":0,	 "VOC":0}
deltaMin			= {"CO2":2,	 "VOC":2}
lastValues			= {}
lastValues2			= {}
lastData			= {}
lastSend			= 0
lastDisplay			= 0
lastRead			= time.time()
G.lastAliveSend		= time.time() -1000

msgCount			= 0
loopSleep			= 1.
sensorWasBad		= False

while True:
	try:
		data = {"sensors": {sensor:{}}}
		sendData = False
		if sensor in sensors:
			for devId in sensors[sensor]:
				if devId not in lastValues: 
					lastValues[devId]  =copy.copy(lastValues0)
					lastValues2[devId] =copy.copy(lastValues0)
				values = getValues(devId)
				if values == "": continue
				data["sensors"][sensor][devId]={}
				if values =="badSensor":
					sensorWasBad = True
					data["sensors"][sensor][devId]="badSensor"
					if badSensor < 5: 
						U.sendURL(data)
						U.logger.log(20," bad sensor, restarting")
						time.sleep(10)
					else:
						U.restartMyself(param="", reason="badsensor",doPrint=True)
					lastValues2[devId] =copy.copy(lastValues0)
					lastValues[devId]  =copy.copy(lastValues0)
					continue
				elif values["CO2"] !="" :
					if sensorWasBad: # sensor was bad, back up again, need to do a restart to set config 
						time.sleep(10)
						U.restartMyself(reason=" back from bad sensor, need to restart to get sensors reset",doPrint=False)
					
					data["sensors"][sensor][devId] = values
					deltaN =0
					for xx in lastValues0:
						try:
							current = float(values[xx])
							delta= abs(current-lastValues2[devId][xx])/ max (0.5,(current+lastValues2[devId][xx])/2.)
							if delta < deltaMin[xx]: continue
							delta  /=  max (0.5,(current+lastValues2[devId][xx])/2.)
							deltaN = max(deltaN,delta) 
							lastValues[devId][xx] = current
						except: pass
				else:
					continue
				if ( msgCount > 5 and (	 ( deltaN > deltaX[devId]  ) or	 (	time.time() - abs(G.sendToIndigoSecs) > G.lastAliveSend	 ) or  quick   ) and  ( time.time() - G.lastAliveSend > minSendDelta ) ):
					sendData = True
					lastValues2[devId] = copy.copy(lastValues[devId])
				msgCount  +=1

		if sendData:
			U.sendURL(data)
		loopCount +=1

		##U.makeDATfile(G.program, data)
		quick = U.checkNowFile(G.program)				 
		U.echoLastAlive(G.program)

		if loopCount %5 ==0 and not quick:
			if time.time() - lastRead > 5.:	 
				readParams()
				lastRead = time.time()
		if not quick:
			time.sleep(loopSleep)
	except	Exception, e:
		U.logger.log(30, u"in Line {} has error={}".format(sys.exc_traceback.tb_lineno, e))
		time.sleep(5.)
try: 	G.sendThread["run"] = False; time.sleep(1)
except: pass
sys.exit(0)
 

		