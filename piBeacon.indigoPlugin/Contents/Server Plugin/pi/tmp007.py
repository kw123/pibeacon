#!/usr/bin/python
# -*- coding: utf-8 -*-
## adopted from adafruit 
#
#

import sys, os, time, json, datetime,subprocess,copy
import smbus
import math

sys.path.append(os.getcwd())
import	piBeaconUtils	as U
import	piBeaconGlobals as G

G.program = "tmp007"
# Copyright (c) 2014 Adafruit Industries
# Author: Tony DiCola
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


# Coefficient values, found from this whitepaper:
# http://www.ti.com/lit/ug/sbou107/sbou107.pdf
# registers

# Default device I2C address.
_TMP007_I2CADDR = 0x40

# Register addresses.
_TMP007_CONFIG = 0x02
_TMP007_DEVID = 0x1F
_TMP007_VOBJ = 0x0
_TMP007_TAMB = 0x01
_TMP007_TOBJ = 0x03

# Config register values.
_TMP007_CFG_RESET = 0x8000
_TMP007_CFG_MODEON = 0x7000
CFG_1SAMPLE = 0x0000
CFG_2SAMPLE = 0x0200
CFG_4SAMPLE = 0x0400
CFG_8SAMPLE = 0x0600
CFG_16SAMPLE = 0x0800
_TMP007_CFG_DRDYEN = 0x0100
_TMP007_CFG_DRDY = 0x0080


# ===========================================================================
# TMP007 Class
# ===========================================================================
class TMP007:

	 # Constructor
	def __init__(self, i2cAddress=""):

		self.debug = G.debug
		if i2cAddress == "" or i2cAddress == 0:
			self.address = 0x40
		else:
			self.address = i2cAddress
				
		self.bus = smbus.SMBus(1)

		self.BUFFER = bytearray(4)

		self.errMsg = ""

		time.sleep(0.5)
		return 


	def begin(self):
		# load_calibration()
		config = _TMP007_CFG_MODEON | _TMP007_CFG_DRDYEN | CFG_8SAMPLE
		config = ((config & 0xFF) << 8) | (config >> 8)
		self.bus.write_word_data(self.address, _TMP007_CONFIG, config)


	# read Obj Temp in C
	def readObjTempC(self):
		raw = self.readU16BE(_TMP007_TOBJ) >>2
		if raw > 16384: raw = 16384-raw
		return raw *0.03125

	# read voltage
	def readVoltage(self):
		raw = self.readU16BE(_TMP007_VOBJ)
		if raw > 32767:
			raw = (raw & 0x7fff) - 32768
		return raw

	def raw_sensor_temperature(self):
		"""Read raw die temperature from TMP007 sensor.  Meant to be used in the
		calculation of temperature values.
		"""
		raw = self.readU16BE(_TMP007_TAMB)
		return raw >> 2


	def getdata(self):
		dieTempC = (self.readU16BE(_TMP007_TAMB) >>2 )* 0.03125
		objTempC = self.readObjTempC()
		sensorVolts = self.readVoltage()
		###print "dieTempC",dieTempC, "objTempC",objTempC, "sensorVolts",sensorVolts
		return objTempC, dieTempC



	def write8(self, reg, value):
		"Writes an 8-bit value to the specified register/address"
		try:
			self.bus.write_byte_data(self.address, reg, value)
		except IOError, err:
			return self.errMsg()

	def writeu16(self, reg, value):
		out = (value >> 8) & 0xFF
		out+= value & 0xFF
		self.bus.write_word_data(self.address, reg, value)
		return 

	def writeRaw8(self, value):
		"Writes an 8-bit value on the bus"
		try:
			self.bus.write_byte(self.address, value)
		except IOError, err:
			return self.errMsg()

	def writeList(self, reg, list):
		"Writes an array of bytes using I2C format"
		try:
			self.bus.write_i2c_block_data(self.address, reg, list)
		except IOError, err:
			return self.errMsg()

	def readList(self, reg, length):
		"Read a list of bytes from the I2C device"
		try:
			results = self.bus.read_i2c_block_data(self.address, reg, length)
			return results
		except IOError, err:
			return self.errMsg()

	def readU8(self, reg):
		"Read an unsigned byte from the I2C device"
		try:
			result = self.bus.read_byte_data(self.address, reg)
			return result
		except IOError, err:
			return self.errMsg()

	def readS8(self, reg):
		"Reads a signed byte from the I2C device"
		try:
			result = self.bus.read_byte_data(self.address, reg)
			if result > 127: result -= 256
			return result
		except IOError, err:
			return self.errMsg()

	def readU16(self, reg, little_endian=True):
		"Reads an unsigned 16-bit value from the I2C device"
		try:
			result = self.bus.read_word_data(self.address,reg)
			# Swap bytes if using big endian because read_word_data assumes little
			# endian on ARM (little endian) systems.
			if not little_endian:
				result = ((result << 8) & 0xFF00) + (result >> 8)
			return result
		except IOError, err:
			return self.errMsg()

	def readU16BE(self, register):
		"""Read an unsigned 16-bit value from the specified register, in big
		endian byte order."""
		return self.readU16(register, little_endian=False)


	def readU16Rev(self, reg):
		"Reads an unsigned 16-bit value from the I2C device with rev byte order"
		try:
			lobyte = self.readU8(reg)
			hibyte = self.readU8(reg+1)
			result = (hibyte << 8) + lobyte
			return result
		except IOError, err:
			return self.errMsg()

	def readU16LE(self, register):
		"""Read an unsigned 16-bit value from the specified register, in little
		endian byte order."""
		return self.readU16(register, little_endian=True)



	def readS16(self, reg, little_endian=True):
		"Reads a signed 16-bit value from the I2C device"
		try:
			result = self.readU16(reg,little_endian)
			if result > 32767: result -= 65536
			return result
		except IOError, err:
			return self.errMsg()

	def readS16BE(self, register):
		"""Read a signed 16-bit value from the specified register, in big
		endian byte order."""
		return self.readS16(register, little_endian=False)

	def readS16Rev(self, reg):
		"Reads a signed 16-bit value from the I2C device with rev byte order"
		try:
			lobyte = self.readS8(reg)
			hibyte = self.readU8(reg+1)
			result = (hibyte << 8) + lobyte
			return result
		except IOError, err:
			return self.errMsg()
 
	def readS16LE(self, register):
		"""Read a signed 16-bit value from the specified register, in little
		endian byte order."""
		return self.readS16(register, little_endian=True)

	def readS16BE(self, register):
		"""Read a signed 16-bit value from the specified register, in big
		endian byte order."""
		return self.readS16(register, little_endian=False)



 # ===========================================================================
# read params
# ===========================================================================

#################################		 
def readParams():
	global sensorList, sensors, sensor,	 sensorRefreshSecs
	global rawOld
	global deltaX, tmp007sensor, minSendDelta
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
			U.logger.log(30,"{} is not in parameters = not enabled, stopping {}.py".format(G.program, G.program) )
			exit()
			
				
		deltaX={}
		for devId in sensors[sensor]:
			deltaX[devId]  = 0.1
			try:
				xx = sensors[sensor][devId]["sensorRefreshSecs"].split("#")
				sensorRefreshSecs = float(xx[0]) 
			except:
				sensorRefreshSecs = 90	  


			i2cAddress = U.getI2cAddress(sensors[sensor][devId], default ="")

			try:
				if "deltaX" in sensors[sensor][devId]: 
					deltaX[devId]= float(sensors[sensor][devId]["deltaX"])/100.
			except:
				deltaX[devId] = 0.05

			try:
				if "minSendDelta" in sensors[sensor][devId]: 
					minSendDelta= float(sensors[sensor][devId]["minSendDelta"])/100.
			except:
				minSendDelta = 5.

				
			if devId not in tmp007sensor:
				U.logger.log(30,"==== Start {} ===== @ i2c= {}".format(G.program, i2cAddress))
				i2cAdd = U.muxTCA9548A(sensors[sensor][devId])
				tmp007sensor[devId] = TMP007(i2cAddress=i2cAdd)
				tmp007sensor[devId].begin()
				U.muxTCA9548Areset()
				U.logger.log(30," started ")
				
		deldevID={}		   
		for devId in tmp007sensor:
			if devId not in sensors[sensor]:
				deldevID[devId]=1
		for dd in  deldevID:
			del tmp007sensor[dd]
		if len(tmp007sensor) ==0: 
			####exit()
			pass

	except	Exception as e:
		U.logger.log(30,"", exc_info=True)



#################################
def getValues(devId):
	global sensor, sensors,	 tmp007sensor, badSensor

	i2cAdd = U.muxTCA9548A(sensors[sensor][devId])
	temp = "" 
	ambTemp = "" 
	try:
		temp,ambTemp	 = tmp007sensor[devId].getdata()
		if temp =="" or ambTemp =="" :
			badSensor+=1
			U.muxTCA9548Areset()
			return "badSensor"
		data = {"temp":round(temp,1),"AmbientTemperature":round(ambTemp,1)}
		badSensor = 0
		U.muxTCA9548Areset()
		return data
	except	Exception as e:
		if badSensor >2 and badSensor < 5: 
			U.logger.log(30,"", exc_info=True)
			U.logger.log(30,u"temp>>{}".format(temp)+"<<")
		badSensor+=1
	if badSensor >3: 
		U.muxTCA9548Areset()
		return "badSensor"
	U.muxTCA9548Areset()
	return ""		 






############################################
global rawOld
global sensor, sensors, badSensor
global deltaX, tmp007sensor, minSendDelta
global oldRaw, lastRead

oldRaw						=""
lastRead					= 0

minSendDelta				= 5.
loopCount					= 0
sensorRefreshSecs			= 60
NSleep						= 100
sensorList					= []
sensors						= {}
sensor						= G.program
quick						= False
output						= {}
badSensor					= 0
sensorActive				= False
loopSleep					= 1
rawOld						= ""
tmp007sensor				={}
deltaX						= {}
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




lastValue		  = {}
lastData			= {}
lastSend			= 0
lastRead			= time.time()
G.lastAliveSend		= time.time() -1000

sensorWasBad = False
while True:
	try:
		tt	 = time.time()
		data = {"sensors": {}}
		if sensor in sensors:
			for devId in sensors[sensor]:
				if devId not in lastValue: lastValue[devId] =-500.
				values = getValues(devId)
				if values == "": continue
				data["sensors"] = {sensor:{}}
				data["sensors"][sensor] = {devId:{}}
				if values =="badSensor":
					sensorWasBad = True
					data["sensors"][sensor][devId]["Current"]="badSensor"
					if badSensor < 5: 
						U.logger.log(30," bad sensor")
						U.sendURL(data)
					lastValue[devId] =-100.
					continue
				elif values["temp"] !="" :
					if sensorWasBad: # sensor was bad, back up again, need to do a restart to set config 
						U.restartMyself(reason=" back from bad sensor, need to restart to get sensors reset",doPrint=False)
					
					data["sensors"][sensor][devId] = values
					current = float(values["temp"])
					delta	= current-lastValue[devId]
					deltaN	= abs(delta) / max (0.5,(current+lastValue[devId])/2.)
				else:
					continue
				#print values, deltaN, deltaX[devId]
				if ( ( deltaN > deltaX[devId]						   ) or 
					 (	tt - abs(G.sendToIndigoSecs) > G.lastAliveSend	) or  
					 ( quick										   )   ) and  \
				   ( ( tt - G.lastAliveSend > minSendDelta			   )   ):
						#print data
						U.sendURL(data)
						lastValue[devId]  = current

		loopCount +=1

		U.makeDATfile(G.program, data)
		quick = U.checkNowFile(G.program)				 
		U.echoLastAlive(G.program)

		if loopCount %40 ==0 and not quick:
			tt= time.time()
			if tt - lastRead > 5.:	
				readParams()
				lastRead = tt
		if not quick:
			time.sleep(loopSleep)
		
	except	Exception as e:
		U.logger.log(30,"", exc_info=True)
		time.sleep(5.)
try: 	G.sendThread["run"] = False; time.sleep(1)
except: pass
sys.exit(0)
