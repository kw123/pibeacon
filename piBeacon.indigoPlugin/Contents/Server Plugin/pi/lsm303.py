#!/usr/bin/env python
# -*- coding: utf-8 -*-
# by Karl Wachs
# feb 5 2016
# version 0.7
import math
import struct
import logging


import sys, os, time, json, datetime,subprocess,copy
import smbus, struct

sys.path.append(os.getcwd())
import	piBeaconUtils	as U
import	piBeaconGlobals as G
G.program = "lsm303"

# The MIT License (MIT)
#
# Copyright (c) 2016 Adafruit Industries
#
# Permission is hereby granted, free of charge, to any person obtaining a copy
# of this software and associated documentation files (the "Software"), to deal
# in the Software without restriction, including without limitation the rights
# to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
# copies of the Software, and to permit persons to whom the Software is
# furnished to do so, subject to the following conditions:
#
# The above copyright notice and this permission notice shall be included in all
# copies or substantial portions of the Software.
#
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
# IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
# FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
# AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
# LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
# OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
# SOFTWARE.


# Minimal constants carried over from Arduino library:

## for chinese board, but does not work right and mag
#LSM303_ADDRESS_ACCEL = 0x1d   # 0011001x

LSM303_ADDRESS_ACCEL = 0x19	  # 0011001x

LSM303_ADDRESS_MAG	 = 0x1e	  # 0011110x

										 # Default	  Type
LSM303_REGISTER_ACCEL_CTRL_REG1_A = 0x20 # 00000111	  rw
LSM303_REGISTER_ACCEL_CTRL_REG4_A = 0x23 # 00000000	  rw
LSM303_REGISTER_ACCEL_OUT_X_L_A	  = 0x28
LSM303_REGISTER_MAG_CRA_REG_M	  = 0x00
LSM303_REGISTER_MAG_CRB_REG_M	  = 0x01
LSM303_REGISTER_MAG_MR_REG_M	  = 0x02
LSM303_REGISTER_MAG_OUT_X_H_M	  = 0x03

# Gain settings for set_mag_gain()
g_1_3 = 0b00100000 #0x20 # +/- 1.3 Gauss = 130uT
g_1_9 = 0b01000000 #0x40 # +/- 1.9
g_2_5 = 0b01100000 #0x60 # +/- 2.5
g_4_0 = 0b10000000 #0x80 # +/- 4.0
g_4_7 = 0b10100000 #0xA0 # +/- 4.7
g_5_6 = 0b11000000 #0xC0 # +/- 5.6
g_8_1 = 0b11100000 #0xE0 # +/- 8.1
LSM303_magGain = [g_1_3,g_1_9,g_2_5,g_4_0,g_4_7,g_5_6,g_8_1]


class THESENSORCLASS():
	"""LSM303 accelerometer & magnetometer."""

	def __init__(self, accelerationGain=1,magGain=0) :
		try:
			accel_address=LSM303_ADDRESS_ACCEL
			self.i2cAddA = accel_address
			mag_address=LSM303_ADDRESS_MAG
			i2c=None
			"""Initialize the LSM303 accelerometer & magnetometer.	The hires
			boolean indicates if high resolution (12-bit) mode vs. low resolution
			(10-bit, faster and lower power) mode should be used.
			"""
			# Setup I2C interface for accelerometer and magnetometer.
			import Adafruit_GPIO.I2C as I2C
			i2c = I2C
			self._accel = i2c.get_i2c_device(accel_address)
			self._mag	= i2c.get_i2c_device(mag_address)

			# Enable the accelerometer
			self.set_acc_gain(accelerationGain=int(accelerationGain))

			# Enable the magnetometer
			self.set_mag_gain(magGain=int(magGain))

		except	Exception, e:
			U.logger.log(30, u"in Line {} has error={}".format(sys.exc_traceback.tb_lineno, e))


	def set_acc_gain(self,accelerationGain=1):
		# Select hi-res (12-bit) or low-res (10-bit) output mode.
		# Low-res mode uses less power and sustains a higher update rate,
		# output is padded to compatible 12-bit units.
		self._accel.write8(LSM303_REGISTER_ACCEL_CTRL_REG1_A, 0x27) #= 0b00100111  = normal power enable xyz
		if accelerationGain	 == 0:
			self._accel.write8(LSM303_REGISTER_ACCEL_CTRL_REG4_A, 0b00000000)
			self.accfactor = [2./2048, 2./2048,2./2048]
		elif accelerationGain ==1:
			self._accel.write8(LSM303_REGISTER_ACCEL_CTRL_REG4_A, 0b00001000)
			self.accfactor = [4./2048, 4./2048,4./2048] # g/LSB
		elif accelerationGain ==2:
			self._accel.write8(LSM303_REGISTER_ACCEL_CTRL_REG4_A, 0b00011000)
			self.accfactor = [8./2048, 8./2048,8./2048]

	def set_mag_gain(self,magGain=0):
		# Set the magnetometer gain.  Gain should be one of the following constants: 
		#self._mag.write8(LSM303_REGISTER_MAG_CRA_REG_M, 0b00000000)  # 15Hz data out rate 
		self._mag.write8(0x00, 0b00010000)	# 15Hz data out rate 
		#print " mag gain", bin(LSM303_magGain[magGain])
		self._mag.write8(0x01, LSM303_magGain[magGain] )
		if magGain ==  0 :	self.magfactor = [100./1055, 100./1055,100./950] # uT/ LSB
		if magGain ==  1 :	self.magfactor = [100./795,	 100./795, 100./710]
		if magGain ==  2 :	self.magfactor = [100./635,	 100./635, 100./570]
		if magGain ==  3 :	self.magfactor = [100./430,	 100./430, 100./385]
		if magGain ==  4 :	self.magfactor = [100./375,	 100./375, 100./335]
		if magGain ==  5 :	self.magfactor = [100./320,	 100./320, 100./285]
		if magGain ==  6 :	self.magfactor = [100./230,	 100./230, 100./205]


	def readData(self):
		try:
			"""Read the accelerometer and magnetometer value.  A tuple of tuples will
			be returned with:
			  ((accel X, accel Y, accel Z), (mag X, mag Y, mag Z))
			"""
			# Read the accelerometer as signed 16-bit little endian values.
			accel_raw = self._accel.readList(LSM303_REGISTER_ACCEL_OUT_X_L_A | 0x80, 6)
			accel = struct.unpack('<hhh', accel_raw)
			# Convert to 12-bit values by shifting unused bits.
			accel = [accel[0] >> 4, accel[1] >> 4, accel[2] >> 4]
			for ii in range(3):
				accel[ii] *=  self.accfactor[ii]   

			# Read the magnetometer.
			mag_raw = self._mag.readList(LSM303_REGISTER_MAG_OUT_X_H_M, 6)
			magx = struct.unpack('>hhh', mag_raw)
			mag =[0,0,0]
			for ii in range(3):
				mag[ii] = magx[ii] * self.magfactor[ii] 
			print magx, accel
			  
			return (accel, mag)

		except	Exception, e:
			U.logger.log(30, u"in Line {} has error={}".format(sys.exc_traceback.tb_lineno, e))
		


		
def startSENSOR(devId, i2cAddress):
	global theSENSORdict
	try:
		if G.accelerationGain =="": G.accelerationGain = 1
		if G.magGain =="":			G.magGain		   = 0
		G.accelerationGain = int(G.accelerationGain)
		G.magGain		   = int(G.magGain)
		U.logger.log(30,"==== Start "+G.program+" ===== @ i2c= " +unicode(i2cAddress)+"	devId=" +unicode(devId)+"  accelerationGain="+unicode(G.accelerationGain)+"	 magGain="+unicode(G.magGain))
		theSENSORdict[devId] = THESENSORCLASS(accelerationGain=G.accelerationGain,magGain=G.magGain) 

	except	Exception, e:
		U.logger.log(30, u"in Line {} has error={}".format(sys.exc_traceback.tb_lineno, e))



#################################		 
def readParams():
	global sensors, sensor
	global rawOld
	global theSENSORdict, resetPin
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

		if "sensors"			in inp:	 sensors =				 (inp["sensors"])


		U.getGlobalParams(inp)
		
		
 
		if sensor not in sensors:
			U.logger.log(30, G.program+"is not in parameters = not enabled, stopping "+G.program )
			exit()
			
				
		for devId in sensors[sensor]:
			changed=  U.getMAGReadParameters(sensors[sensor][devId],devId) 
			if	changed.find("accelerationGain") >-1  or changed.find("magGain") >-1: 
				U.restartMyself(reason="new gain seetungs require restart ",doPrint=False)

				
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
		U.logger.log(30, u"in Line {} has error={}".format(sys.exc_traceback.tb_lineno, e))



#################################
def getValues(devId):
	global sensor, sensors,	 theSENSORdict
	try:
		data = {}
		ACC,MAG=  theSENSORdict[devId].readData()
		MAG = U.applyOffsetNorm(MAG,sensors[sensor][devId],["magOffsetX","magOffsetY","magOffsetZ",],"magDivider") 

		#print ACC, MAG
		EULER = U.getEULER(MAG)

			
		data["ACC"]	  = fillWithItems(ACC,["x","y","z"],3)
		data["MAG"]	  = fillWithItems(MAG,["x","y","z"],2)
		data["EULER"] = fillWithItems(EULER,["heading","roll","pitch"],2)
		for xx in data:
			U.logger.log(10, (xx).ljust(11)+" "+unicode(data[xx]))
		return data
	except	Exception, e:
		U.logger.log(30, u"in Line {} has error={}".format(sys.exc_traceback.tb_lineno, e))
	return {"MAG":"bad"}

def fillWithItems(theList,theItems,digits):
	out={}
	for ii in range(len(theItems)):
		out[theItems[ii]] = round(theList[ii],digits)
	return out


############################################
global sensor, sensors, badSensor
global deltaX, theSENSORdict, accelerationGain, magGain
global oldRaw,	lastRead
oldRaw					= ""
lastRead				= 0



loopCount					= 0
NSleep						= 100
sensors						= {}
sensor						= G.program
quick						= False
rawOld						= ""
theSENSORdict				= {}
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



lastValueDefault	= {"EULER":{"heading":0,"roll":0,"pitch":0},"MAG":{"x":0,"y":0,"z":0},"GYR":{"x":0,"y":0,"z":0},"ACC":{"x":0,"y":0,"z":0}}
lastRead			= time.time()
G.lastAliveSend		= time.time() -1000
testDims			= ["MAG","ACC"]
testCoords			= ["x","y","z"]
testForBadSensor	= "MAG"
lastValue			= {}
thresholdDefault	= 0.1
sumTest				={"dim":"MAG","limits":[0,250.]}
singleTest			={"dim":"MAG","coord":"heading","limits":[-9999.,400.]}

startTime = time.time()
while True:
	try:
		tt = time.time()
		if sensor in sensors:
			skip =False
			
		if sensor in sensors:
			for devId in sensors[sensor]:
				if devId not in lastValue: lastValue[devId] = copy.copy(lastValueDefault)
				if devId not in G.threshold: G.threshold[devId] = thresholdDefault
				values = getValues(devId)
				lastValue =U.checkMGACCGYRdata(
					values,lastValue,testDims,testCoords,testForBadSensor,devId,sensor,quick)
					#sumTest=sumTest,singleTest=singleTest)

		loopCount +=1

		quick = U.checkNowFile(G.program)				 
		U.echoLastAlive(G.program)

		tt= time.time()
		if tt - lastRead > 5.:	
			readParams()
			lastRead = tt
		if not quick:
			time.sleep(G.sensorLoopWait)
		
	except	Exception, e:
		U.logger.log(30, u"in Line {} has error={}".format(sys.exc_traceback.tb_lineno, e))
		time.sleep(5.)
try: 	G.sendThread["run"] = False; time.sleep(1)
except: pass
ys.exit(0)

