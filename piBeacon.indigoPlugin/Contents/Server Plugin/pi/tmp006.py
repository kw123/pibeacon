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
G.program = "tmp006"
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
TMP006_B0	= -0.0000294
TMP006_B1	= -0.00000057
TMP006_B2	= 0.00000000463
TMP006_C2	= 13.4
TMP006_TREF = 298.15
TMP006_A2	= -0.00001678
TMP006_A1	= 0.00175
TMP006_S0	= 6.4  # * 10^-14

# Default device I2C address.
TMP006_I2CADDR		= 0x40

# Register addresses.
TMP006_CONFIG		= 0x02
TMP006_MANID		= 0xFE
TMP006_DEVID		= 0xFF
TMP006_VOBJ			= 0x0
TMP006_TAMB			= 0x01

# Config register values.
TMP006_CFG_RESET	= 0x8000
TMP006_CFG_MODEON	= 0x7000
CFG_1SAMPLE			= 0x0000
CFG_2SAMPLE			= 0x0200
CFG_4SAMPLE			= 0x0400
CFG_8SAMPLE			= 0x0600
CFG_16SAMPLE		= 0x0800
TMP006_CFG_DRDYEN	= 0x0100
TMP006_CFG_DRDY		= 0x0080


# ===========================================================================
# TMP006 Class
# ===========================================================================
class TMP006:

	 # Constructor
	def __init__(self, i2cAddress=""):

		self.debug = G.debug
		if i2cAddress =="" or i2cAddress ==0:
			self.address = 0x40
		else:
			self.address = i2cAddress
				
		self.bus = smbus.SMBus(1)
		self.errMsg =""

	def begin(self, samplerate=CFG_16SAMPLE):
		"""Start taking temperature measurements.  Samplerate can be one of
		TMP006_CFG_1SAMPLE, TMP006_CFG_2SAMPLE, TMP006_CFG_4SAMPLE,
		TMP006_CFG_8SAMPLE, or TMP006_CFG_16SAMPLE.	 The default is 16 samples
		for the highest resolution.	 Returns True if the device is intialized,
		False otherwise.
		"""
		if samplerate not in (CFG_1SAMPLE, CFG_2SAMPLE, CFG_4SAMPLE, CFG_8SAMPLE, CFG_16SAMPLE):
			raise ValueError('Unexpected samplerate value! Must be one of: CFG_1SAMPLE, CFG_2SAMPLE, CFG_4SAMPLE, CFG_8SAMPLE, or CFG_16SAMPLE')
		U.logger.log(30,'Using samplerate value: {0:04X}'.format(samplerate))
		# Set configuration register to turn on chip, enable data ready output,
		# and start sampling at the specified rate.
		config = TMP006_CFG_MODEON | TMP006_CFG_DRDYEN | samplerate
		# Flip byte order of config value because write16 uses little endian but we
		# need big endian here.	 This is an ugly hack for now, better to add support
		# in write16 for explicit endians.
		config = ((config & 0xFF) << 8) | (config >> 8)
		self.write16(TMP006_CONFIG, config)
		# Check manufacturer and device ID match expected values.
		mid = self.readU16BE(TMP006_MANID)
		did = self.readU16BE(TMP006_DEVID)
		U.logger.log(30,'Read manufacturer ID: {0:04X}'.format(mid))
		U.logger.log(30,'Read device ID: {0:04X}'.format(did))
		return mid == 0x5449 and did == 0x0067


	def sleep(self):
		"""Put TMP006 into low power sleep mode.  No measurement data will be
		updated while in sleep mode.
		"""
		control = self.readU16BE(TMP006_CONFIG)
		control &= ~(TMP006_CFG_MODEON)
		self.write16(TMP006_CONFIG, control)
		U.logger.log(10,'TMP006 entered sleep mode.')

	def wake(self):
		"""Wake up TMP006 from low power sleep mode."""
		control = self.readU16BE(TMP006_CONFIG)
		control |= TMP006_CFG_MODEON
		self.write16(TMP006_CONFIG, control)
		U.logger.log(10,'TMP006 woke from sleep mode.')

	def readRawVoltage(self):
		"""Read raw voltage from TMP006 sensor.	 Meant to be used in the
		calculation of temperature values.
		"""
		raw = self.readS16BE(TMP006_VOBJ)
		U.logger.log(10,'Raw voltage: 0x{0:04X} ({1:0.4F} uV)'.format(raw & 0xFFFF,
			raw * 156.25 / 1000.0))
		return raw

	def readRawDieTemperature(self):
		"""Read raw die temperature from TMP006 sensor.	 Meant to be used in the
		calculation of temperature values.
		"""
		return  self.readS16BE(TMP006_TAMB) >>2

	def readDieTempC(self):
		"""Read sensor die temperature and return its value in degrees celsius."""
		try:
			Tdie = self.readRawDieTemperature()
			return Tdie * 0.03125
		except	Exception, e:
				U.logger.log(30, u"in Line {} has error={}".format(sys.exc_traceback.tb_lineno, e))
		return ""
		
	def getdata(self):
		try:
			tA = self.readDieTempC()
			tO = self.readObjTempC()
			return tA, tO
		except:
			return "",""
			
			
	def readObjTempC(self):
		try:
			"""Read sensor object temperature (i.e. temperature of item in front of
			the sensor) and return its value in degrees celsius."""
			# Read raw values and scale them to required units.
			Tdie = self.readRawDieTemperature()
			Vobj = self.readRawVoltage()
			Vobj *= 156.25		   # 156.25 nV per bit
			U.logger.log(10,'Vobj = {0:0.4} nV'.format(Vobj))
			Vobj /= 1000000000.0   # Convert nV to volts
			Tdie *= 0.03125		   # Convert to celsius
			Tdie += 273.14		   # Convert to kelvin
			# Compute object temperature following equations from:
			# http://www.ti.com/lit/ug/sbou107/sbou107.pdf
			Tdie_ref = Tdie - TMP006_TREF
			S = 1.0 + TMP006_A1*Tdie_ref + TMP006_A2*math.pow(Tdie_ref, 2.0)
			S *= TMP006_S0
			S /= 10000000.0
			S /= 10000000.0
			Vos = TMP006_B0 + TMP006_B1*Tdie_ref + TMP006_B2*math.pow(Tdie_ref, 2.0)
			fVobj = (Vobj - Vos) + TMP006_C2*math.pow((Vobj - Vos), 2.0)
			Tobj = math.sqrt(math.sqrt(math.pow(Tdie, 4.0) + (fVobj/S)))
			return Tobj - 273.15
		except	Exception, e:
			U.logger.log(30, u"in Line {} has error={}".format(sys.exc_traceback.tb_lineno, e))
			return ""


	def write8(self, reg, value):
		"Writes an 8-bit value to the specified register/address"
		try:
			self.bus.write_byte_data(self.address, reg, value)
			if self.debug:
				print "I2C: Wrote 0x%02X to register 0x%02X" % (value, reg)
		except IOError, err:
			return self.errMsg()

	def write16(self, reg, value):
		"Writes a 16-bit value to the specified register/address pair"
		try:
			self.bus.write_word_data(self.address, reg, value)
			if self.debug:
				print ("I2C: Wrote 0x%02X to register pair 0x%02X,0x%02X" %
				 (value, reg, reg+1))
		except IOError, err:
			return self.errMsg()

	def writeRaw8(self, value):
		"Writes an 8-bit value on the bus"
		try:
			self.bus.write_byte(self.address, value)
			if self.debug:
				print "I2C: Wrote 0x%02X" % value
		except IOError, err:
			return self.errMsg()

	def writeList(self, reg, list):
		"Writes an array of bytes using I2C format"
		try:
			if self.debug:
				print "I2C: Writing list to register 0x%02X:" % reg
				print list
			self.bus.write_i2c_block_data(self.address, reg, list)
		except IOError, err:
			return self.errMsg()

	def readList(self, reg, length):
		"Read a list of bytes from the I2C device"
		try:
			results = self.bus.read_i2c_block_data(self.address, reg, length)
			if self.debug:
				print ("I2C: Device 0x%02X returned the following from reg 0x%02X" %
				 (self.address, reg))
				print results
			return results
		except IOError, err:
			return self.errMsg()

	def readU8(self, reg):
		"Read an unsigned byte from the I2C device"
		try:
			result = self.bus.read_byte_data(self.address, reg)
			if self.debug:
				print ("I2C: Device 0x%02X returned 0x%02X from reg 0x%02X" %
				 (self.address, result & 0xFF, reg))
			return result
		except IOError, err:
			return self.errMsg()

	def readS8(self, reg):
		"Reads a signed byte from the I2C device"
		try:
			result = self.bus.read_byte_data(self.address, reg)
			if result > 127: result -= 256
			if self.debug:
				print ("I2C: Device 0x%02X returned 0x%02X from reg 0x%02X" %
				 (self.address, result & 0xFF, reg))
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
			if (self.debug):
				print "I2C: Device 0x%02X returned 0x%04X from reg 0x%02X" % (self.address, result & 0xFFFF, reg)
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
			if (self.debug):
				print "I2C: Device 0x%02X returned 0x%04X from reg 0x%02X" % (self.address, result & 0xFFFF, reg)
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
			if (self.debug):
				print "I2C: Device 0x%02X returned 0x%04X from reg 0x%02X" % (self.address, result & 0xFFFF, reg)
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
	global sensorList, sensors, sensor,	sensorRefreshSecs
	global rawOld
	global deltaX, tmp006sensor, minSendDelta
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
			
				
		deltaX={}
		for devId in sensors[sensor]:
			deltaX[devId]  = 0.1
			try:
				xx = sensors[sensor][devId]["sensorRefreshSecs"].split("#")
				sensorRefreshSecs = float(xx[0]) 
			except:
				sensorRefreshSecs = 90	  


			try:
				if "i2cAddress" in sensors[sensor][devId]: 
					i2cAddress = int(sensors[sensor][devId]["i2cAddress"])
			except:
				i2cAddress = ""	   

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

				
			if devId not in tmp006sensor:
				U.logger.log(30,"==== Start "+G.program+" ===== @ i2c= " +unicode(i2cAddress))
				i2cAdd = U.muxTCA9548A(sensors[sensor][devId])
				tmp006sensor[devId] = TMP006(i2cAddress=i2cAdd)
				tmp006sensor[devId].begin()
				U.muxTCA9548Areset()
				U.logger.log(30," started ")
				
		deldevID={}		   
		for devId in tmp006sensor:
			if devId not in sensors[sensor]:
				deldevID[devId]=1
		for dd in  deldevID:
			del tmp006sensor[dd]
		if len(tmp006sensor) ==0: 
			####exit()
			pass

	except	Exception, e:
		U.logger.log(30, u"in Line {} has error={}".format(sys.exc_traceback.tb_lineno, e))



#################################
def getValues(devId):
	global sensor, sensors,	 tmp006sensor, badSensor

	i2cAdd = U.muxTCA9548A(sensors[sensor][devId])
	temp = ""
	try:
		temp,ambTemp	 = tmp006sensor[devId].getdata()
		if temp =="" or ambTemp =="" :
			badSensor+=1
			U.muxTCA9548Areset()
			return "badSensor"
		data = {"temp":round(temp,2),"AmbientTemperature":round(ambTemp,2)}
		badSensor = 0
		U.muxTCA9548Areset()
		return data
	except	Exception, e:
		if badSensor >2 and badSensor < 5: 
			U.logger.log(30, u"in Line {} has error={}".format(sys.exc_traceback.tb_lineno, e))
			U.logger.log(30, u"temp>>" + unicode(temp)+"<<")
		badSensor+=1
	if badSensor >3: 
		U.muxTCA9548Areset()
		return "badSensor"
	U.muxTCA9548Areset()
	return ""		 






############################################
global rawOld
global sensor, sensors, badSensor
global deltaX, tmp006sensor, minSendDelta
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
tmp006sensor				={}
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
		
	except	Exception, e:
		U.logger.log(30, u"in Line {} has error={}".format(sys.exc_traceback.tb_lineno, e))
		time.sleep(5.)
try: 	G.sendThread["run"] = False; time.sleep(1)
except: pass
sys.exit(0)
