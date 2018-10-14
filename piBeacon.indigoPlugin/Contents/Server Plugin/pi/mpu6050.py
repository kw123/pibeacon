#!/usr/bin/env python
# -*- coding: utf-8 -*-

import sys, os, time, json, datetime,subprocess,copy
import math
import struct
import smbus

sys.path.append(os.getcwd())
import	piBeaconUtils	as U
import	piBeaconGlobals as G
G.program = "mpu6050"
G.debug = 0

"""This program handles the communication over I2C
between a Raspberry Pi and a MPU-6050 Gyroscope / Accelerometer combo.
Made by: MrTijn/Tijndagamer
Released under the MIT License
Copyright (c) 2015, 2016, 2017 MrTijn/Tijndagamer
"""

import smbus



class THESENSORCLASS:

	# Global Variables
	GRAVITIY_MS2 = 9.80665
	address = 0x68
	bus = smbus.SMBus(1)

	# Scale Modifiers
	ACCEL_SCALE_MODIFIER_2G = 16384.0
	ACCEL_SCALE_MODIFIER_4G = 8192.0
	ACCEL_SCALE_MODIFIER_8G = 4096.0
	ACCEL_SCALE_MODIFIER_16G = 2048.0

	GYRO_SCALE_MODIFIER_250DEG = 131.0
	GYRO_SCALE_MODIFIER_500DEG = 65.5
	GYRO_SCALE_MODIFIER_1000DEG = 32.8
	GYRO_SCALE_MODIFIER_2000DEG = 16.4

	# Pre-defined ranges
	ACCEL_RANGE_2G = 0x00
	ACCEL_RANGE_4G = 0x08
	ACCEL_RANGE_8G = 0x10
	ACCEL_RANGE_16G = 0x18

	GYRO_RANGE_250DEG = 0x00
	GYRO_RANGE_500DEG = 0x08
	GYRO_RANGE_1000DEG = 0x10
	GYRO_RANGE_2000DEG = 0x18

	# MPU-6050 Registers
	PWR_MGMT_1 = 0x6B
	PWR_MGMT_2 = 0x6C

	ACCEL_XOUT0 = 0x3B
	ACCEL_YOUT0 = 0x3D
	ACCEL_ZOUT0 = 0x3F

	TEMP_OUT0 = 0x41

	GYRO_XOUT0 = 0x43
	GYRO_YOUT0 = 0x45
	GYRO_ZOUT0 = 0x47

	ACCEL_CONFIG = 0x1C
	GYRO_CONFIG = 0x1B

	def __init__(self, i2cAddress=""):
		if i2cAddress!="":
			self.address = i2cAddress

		# Wake up the MPU-6050 since it starts in sleep mode
		self.bus.write_byte_data(self.address, self.PWR_MGMT_1, 0x00)
		self.set_gyro_range( self.GYRO_RANGE_500DEG)
		self.set_accel_range(self.ACCEL_RANGE_4G)

	# I2C communication methods

	def read_i2c_word(self, register):
		"""Read two i2c registers and combine them.

		register -- the first register to read from.
		Returns the combined read results.
		"""
		# Read the data from the registers
		high = self.bus.read_byte_data(self.address, register)
		low	 = self.bus.read_byte_data(self.address, register + 1)

		value = (high << 8) + low

		if (value >= 0x8000):
			return -((65535 - value) + 1)
		else:
			return value

	# MPU-6050 Methods

	def get_temp(self):
		"""Reads the temperature from the onboard temperature sensor of the MPU-6050.

		Returns the temperature in degrees Celcius.
		"""
		raw_temp = self.read_i2c_word(self.TEMP_OUT0)

		# Get the actual temperature using the formule given in the
		# MPU-6050 Register Map and Descriptions revision 4.2, page 30
		actual_temp = (raw_temp / 340.0) + 36.53

		return actual_temp

	def set_accel_range(self, accel_range):
		"""Sets the range of the accelerometer to range.

		accel_range -- the range to set the accelerometer to. Using a
		pre-defined range is advised.
		"""
		# First change it to 0x00 to make sure we write the correct value later
		self.bus.write_byte_data(self.address, self.ACCEL_CONFIG, 0x00)

		# Write the new range to the ACCEL_CONFIG register
		self.bus.write_byte_data(self.address, self.ACCEL_CONFIG, accel_range)

	def read_accel_range(self, raw = False):
		"""Reads the range the accelerometer is set to.

		If raw is True, it will return the raw value from the ACCEL_CONFIG
		register
		If raw is False, it will return an integer: -1, 2, 4, 8 or 16. When it
		returns -1 something went wrong.
		"""
		raw_data = self.bus.read_byte_data(self.address, self.ACCEL_CONFIG)

		if raw is True:
			return raw_data
		elif raw is False:
			if raw_data == self.ACCEL_RANGE_2G:
				return 2
			elif raw_data == self.ACCEL_RANGE_4G:
				return 4
			elif raw_data == self.ACCEL_RANGE_8G:
				return 8
			elif raw_data == self.ACCEL_RANGE_16G:
				return 16
			else:
				return -1

	def get_accel_data(self, g = False):
		"""Gets and returns the X, Y and Z values from the accelerometer.

		If g is True, it will return the data in g
		If g is False, it will return the data in m/s^2
		Returns a dictionary with the measurement results.
		"""
		x = self.read_i2c_word(self.ACCEL_XOUT0)
		y = self.read_i2c_word(self.ACCEL_YOUT0)
		z = self.read_i2c_word(self.ACCEL_ZOUT0)

		accel_scale_modifier = None
		accel_range = self.read_accel_range(True)

		if accel_range == self.ACCEL_RANGE_2G:
			accel_scale_modifier = self.ACCEL_SCALE_MODIFIER_2G
		elif accel_range == self.ACCEL_RANGE_4G:
			accel_scale_modifier = self.ACCEL_SCALE_MODIFIER_4G
		elif accel_range == self.ACCEL_RANGE_8G:
			accel_scale_modifier = self.ACCEL_SCALE_MODIFIER_8G
		elif accel_range == self.ACCEL_RANGE_16G:
			accel_scale_modifier = self.ACCEL_SCALE_MODIFIER_16G
		else:
			U.toLog(-1,"Unkown range - accel_scale_modifier set to self.ACCEL_SCALE_MODIFIER_2G")
			accel_scale_modifier = self.ACCEL_SCALE_MODIFIER_2G

		x = x / accel_scale_modifier
		y = y / accel_scale_modifier
		z = z / accel_scale_modifier

		if not g:
			x = x * self.GRAVITIY_MS2
			y = y * self.GRAVITIY_MS2
			z = z * self.GRAVITIY_MS2
		return {'x': round(x,2), 'y':  round(y,2), 'z':	 round(z,2)}

	def set_gyro_range(self, gyro_range):
		"""Sets the range of the gyroscope to range.

		gyro_range -- the range to set the gyroscope to. Using a pre-defined
		range is advised.
		"""
		# First change it to 0x00 to make sure we write the correct value later
		self.bus.write_byte_data(self.address, self.GYRO_CONFIG, 0x00)

		# Write the new range to the ACCEL_CONFIG register
		self.bus.write_byte_data(self.address, self.GYRO_CONFIG, gyro_range)

	def read_gyro_range(self, raw = False):
		"""Reads the range the gyroscope is set to.

		If raw is True, it will return the raw value from the GYRO_CONFIG
		register.
		If raw is False, it will return 250, 500, 1000, 2000 or -1. If the
		returned value is equal to -1 something went wrong.
		"""
		raw_data = self.bus.read_byte_data(self.address, self.GYRO_CONFIG)

		if raw is True:
			return raw_data
		elif raw is False:
			if raw_data == self.GYRO_RANGE_250DEG:
				return 250
			elif raw_data == self.GYRO_RANGE_500DEG:
				return 500
			elif raw_data == self.GYRO_RANGE_1000DEG:
				return 1000
			elif raw_data == self.GYRO_RANGE_2000DEG:
				return 2000
			else:
				return -1

	def get_gyro_data(self):
		"""Gets and returns the X, Y and Z values from the gyroscope.

		Returns the read values in a dictionary.
		"""
		x = self.read_i2c_word(self.GYRO_XOUT0)
		y = self.read_i2c_word(self.GYRO_YOUT0)
		z = self.read_i2c_word(self.GYRO_ZOUT0)

		gyro_scale_modifier = None
		gyro_range = self.read_gyro_range(True)

		if gyro_range == self.GYRO_RANGE_250DEG:
			gyro_scale_modifier = self.GYRO_SCALE_MODIFIER_250DEG
		elif gyro_range == self.GYRO_RANGE_500DEG:
			gyro_scale_modifier = self.GYRO_SCALE_MODIFIER_500DEG
		elif gyro_range == self.GYRO_RANGE_1000DEG:
			gyro_scale_modifier = self.GYRO_SCALE_MODIFIER_1000DEG
		elif gyro_range == self.GYRO_RANGE_2000DEG:
			gyro_scale_modifier = self.GYRO_SCALE_MODIFIER_2000DEG
		else:
			U.toLog(-1,"Unkown range - gyro_scale_modifier set to self.GYRO_SCALE_MODIFIER_250DEG")
			gyro_scale_modifier = self.GYRO_SCALE_MODIFIER_250DEG

		x = (x / gyro_scale_modifier)
		y = (y / gyro_scale_modifier)
		z = (z / gyro_scale_modifier)

		return {'x': round(x,2), 'y':  round(y,2), 'z':	 round(z,2)}





# read params
# ===========================================================================

#################################		 
def readParams():
	global sensors, sensor
	global rawOld
	global theSENSORdict
	global oldRaw, lastRead
	try:

		inp,inpRaw,lastRead2 = U.doRead(lastTimeStamp=lastRead)
		if inp == "": return
		if lastRead2 == lastRead: return
		lastRead   = lastRead2
		if inpRaw == oldRaw: return
		oldRaw	   = inpRaw


		externalSensor=False
		sensorsOld= copy.copy(sensors)

		U.getGlobalParams(inp)
		  
		if "sensors"			in inp:	 sensors =				 (inp["sensors"])
		if "debugRPI"			in inp:	 G.debug=			  int(inp["debugRPI"]["debugRPISENSOR"])
 
		if sensor not in sensors:
			U.toLog(-1, G.program+" is not in parameters = not enabled, stopping "+G.program )
			exit()
			
		for devId in sensors[sensor]:
			U.getMAGReadParameters(sensors[sensor][devId],devId)
				
			if devId not in theSENSORdict:
				startSENSOR(devId, G.i2cAddress)
				
		deldevID={}		   
		for devId in theSENSORdict:
			if devId not in sensors[sensor]:
				deldevID[devId]=1
		for dd in  deldevID:
			del theSENSORdict[dd]
		if len(theSENSORdict) ==0: 
			####exit()
			pass

	except	Exception, e:
		U.toLog(-1, u"in Line '%s' has error='%s'" % (sys.exc_traceback.tb_lineno, e))

#################################
def startSENSOR(devId, i2cAddress):
	global theSENSORdict
	try:
		U.toLog(-1,"==== Start "+G.program+" ===== @ i2c= " +unicode(i2cAddress)+"	devId=" +unicode(devId))
		theSENSORdict[devId] = THESENSORCLASS(i2cAddress=i2cAddress)
	except	Exception, e:
		U.toLog(-1, u"in Line '%s' has error='%s'" % (sys.exc_traceback.tb_lineno, e))



#################################
def getValues(devId):
	global theSENSORdict
	data={}
	try:
		data["temp"]	 = theSENSORdict[devId].get_temp()
		data["ACC"]		 = theSENSORdict[devId].get_accel_data(g=True)
		data["GYR"]		 = theSENSORdict[devId].get_gyro_data()
		#print data
		for xx in data:
			U.toLog(2, (xx).ljust(7)+" "+unicode(data[xx]))
		return data
	except	Exception, e:
		U.toLog(-1, u"in Line '%s' has error='%s'" % (sys.exc_traceback.tb_lineno, e))
	return {"ACC":"bad"}

def fillWithItems(theList,theItems,digits):
	out={}
	for ii in range(len(theItems)):
		out[theItems[ii]] = round(theList[ii],digits)
	return out


############################################
global rawOld
global sensor, sensors
global theSENSORdict
global oldRaw,	lastRead
oldRaw					= ""
lastRead				= 0

G.debug						= 5
loopCount					= 0
NSleep						= 100
sensors						= {}
sensor						= G.program
quick						= False
output						= {}
sensorActive				= False
rawOld						= ""
theSENSORdict					={}
myPID		= str(os.getpid())
U.killOldPgm(myPID,G.program+".py")# kill old instances of myself if they are still running


if U.getIPNumber() > 0:
	time.sleep(10)
	exit()

readParams()


lastRead = time.time()

U.echoLastAlive(G.program)

lastValue			= {}
lastRead			= time.time()
G.lastAliveSend		= time.time() -1000
lastValueDefault	= {"ACC":{"x":11110,"y":11110,"z":11110},"GYR":{"x":11110,"y":111110,"z":111110},"temp":0}
testDims			= ["ACC","GYR"]
testCoords			= ["x","y","z"]
testForBadSensor	= "ACC"
lastValue			= {}
thresholdDefault	= 0.01
while True:
	try:
		if sensor in sensors:
			for devId in sensors[sensor]:
				if devId not in lastValue: lastValue[devId] = copy.copy(lastValueDefault)
				if devId not in G.threshold: G.threshold[devId] = thresholdDefault
				values = getValues(devId)
				lastValue =U.checkMGACCGYRdata(
					values,lastValue,testDims,testCoords,testForBadSensor,devId,sensor,quick)
 
		loopCount +=1
		quick = U.checkNowFile(G.program)				 
		if U.checkNewCalibration(G.program):
			U.toLog(-1, u"starting new calibration in 5 sec for 1 minute.. move sensor around")
			time.sleep(5)
			theSENSORdict[devId].calibrate(force=True,calibTime=60)
			U.toLog(-1, u"finished	new calibration")
			
		U.echoLastAlive(G.program)

		tt= time.time()
		if tt - lastRead > 5.:	
			readParams()
			lastRead = tt
		if not quick:
			time.sleep(G.sensorLoopWait)
		
	except	Exception, e:
		U.toLog(-1, u"in Line '%s' has error='%s'" % (sys.exc_traceback.tb_lineno, e))
		time.sleep(5.)
sys.exit(0)
