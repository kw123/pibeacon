#!/usr/bin/env python
# -*- coding: utf-8 -*-
# by Karl Wachs
# feb 5 2016
# version 0.7
import math
import struct
import logging


import sys, os, time, json, datetime,subprocess,copy
import smbus

sys.path.append(os.getcwd())
import	piBeaconUtils	as U
import	piBeaconGlobals as G

G.program	= "lsm303"

# Copyright 2020 jackw01. Released under the MIT license.
__version__	= '1.0.0'


LSM303_ADDRESS_ACCEL					= 0x19 # 0011001x
LSM303_REGISTER_ACCEL_CTRL_REG1_A		= 0x20
LSM303_REGISTER_ACCEL_CTRL_REG2_A		= 0x21
LSM303_REGISTER_ACCEL_CTRL_REG3_A		= 0x22
LSM303_REGISTER_ACCEL_CTRL_REG4_A		= 0x23
LSM303_REGISTER_ACCEL_CTRL_REG5_A		= 0x24
LSM303_REGISTER_ACCEL_CTRL_REG6_A		= 0x25
LSM303_REGISTER_ACCEL_REFERENCE_A		= 0x26
LSM303_REGISTER_ACCEL_STATUS_REG_A		= 0x27
LSM303_REGISTER_ACCEL_OUT_X_L_A			= 0x28
LSM303_REGISTER_ACCEL_OUT_X_H_A			= 0x29
LSM303_REGISTER_ACCEL_OUT_Y_L_A			= 0x2A
LSM303_REGISTER_ACCEL_OUT_Y_H_A			= 0x2B
LSM303_REGISTER_ACCEL_OUT_Z_L_A			= 0x2C
LSM303_REGISTER_ACCEL_OUT_Z_H_A			= 0x2D
LSM303_REGISTER_ACCEL_FIFO_CTRL_REG_A	= 0x2E
LSM303_REGISTER_ACCEL_FIFO_SRC_REG_A	= 0x2F
LSM303_REGISTER_ACCEL_INT1_CFG_A		= 0x30
LSM303_REGISTER_ACCEL_INT1_SOURCE_A		= 0x31
LSM303_REGISTER_ACCEL_INT1_THS_A		= 0x32
LSM303_REGISTER_ACCEL_INT1_DURATION_A	= 0x33
LSM303_REGISTER_ACCEL_INT2_CFG_A		= 0x34
LSM303_REGISTER_ACCEL_INT2_SOURCE_A		= 0x35
LSM303_REGISTER_ACCEL_INT2_THS_A		= 0x36
LSM303_REGISTER_ACCEL_INT2_DURATION_A	= 0x37
LSM303_REGISTER_ACCEL_CLICK_CFG_A		= 0x38
LSM303_REGISTER_ACCEL_CLICK_SRC_A		= 0x39
LSM303_REGISTER_ACCEL_CLICK_THS_A		= 0x3A
LSM303_REGISTER_ACCEL_TIME_LIMIT_A		= 0x3B
LSM303_REGISTER_ACCEL_TIME_LATENCY_A	= 0x3C
LSM303_REGISTER_ACCEL_TIME_WINDOW_A		= 0x3D

LSM303_ADDRESS_MAG							= 0x1E # 0011110x
LSM303_REGISTER_MAG_CRA_REG_M				= 0x00
LSM303_REGISTER_MAG_CRB_REG_M				= 0x01
LSM303_REGISTER_MAG_MR_REG_M				= 0x02
LSM303_REGISTER_MAG_OUT_X_H_M				= 0x03
LSM303_REGISTER_MAG_OUT_X_L_M				= 0x04
LSM303_REGISTER_MAG_OUT_Z_H_M				= 0x05
LSM303_REGISTER_MAG_OUT_Z_L_M				= 0x06
LSM303_REGISTER_MAG_OUT_Y_H_M				= 0x07
LSM303_REGISTER_MAG_OUT_Y_L_M				= 0x08
LSM303_REGISTER_MAG_SR_REG_Mg				= 0x09
LSM303_REGISTER_MAG_IRA_REG_M				= 0x0A
LSM303_REGISTER_MAG_IRB_REG_M				= 0x0B
LSM303_REGISTER_MAG_IRC_REG_M				= 0x0C
LSM303_REGISTER_MAG_TEMP_OUT_H_M			= 0x31
LSM303_REGISTER_MAG_TEMP_OUT_L_M			= 0x32

MAG_GAIN ={}
MAG_GAIN["130"]								= 0x20 # +/- 1.3
MAG_GAIN["190"]								= 0x40 # +/- 1.9
MAG_GAIN["250"]								= 0x60 # +/- 2.5
MAG_GAIN["400"]								= 0x80 # +/- 4.0
MAG_GAIN["470"]								= 0xA0 # +/- 4.7
MAG_GAIN["560"]								= 0xC0 # +/- 5.6
MAG_GAIN["810"]								= 0xE0 # +/- 8.1

MAG_RATE = {}
MAG_RATE["0.7"]								= 0x00 # 0.75 H
MAG_RATE["1.5"]								= 0x01 # 1.5 Hz
MAG_RATE["3.0"]								= 0x62 # 3.0 Hz
MAG_RATE["7.5"]								= 0x03 # 7.5 Hz
MAG_RATE["15"]								= 0x04 # 15 Hz
MAG_RATE["30"]								= 0x05 # 30 Hz
MAG_RATE["75"]								= 0x06 # 75 Hz
MAG_RATE["210"]								= 0x07 # 210 Hz

ACCEL_MS2_PER_LSB	= 0.00980665 # meters/second^2 per least significant bit

GAUSS_TO_MICROTESLA	= 100.0

class THESENSORCLASS(object):
#	'LSM303 3-axis accelerometer/magnetometer'

	def __init__(self, accelerationGain="1", magGain="4.7", magFregRate ="3.0" ):
		# 'Initialize the sensor'
		self._bus	= smbus.SMBus(1)

		# Enable the accelerometer - all 3 channels
		self._bus.write_i2c_block_data(LSM303_ADDRESS_ACCEL, LSM303_REGISTER_ACCEL_CTRL_REG1_A, [0b01000111])

		# Select hi-res (12-bit) or low-res (10-bit) output mode.
		# Low-res mode uses less power and sustains a higher update rate,
		# output is padded to compatible 12-bit units.
		if accelerationGain=="1":	self._bus.write_i2c_block_data(LSM303_ADDRESS_ACCEL, LSM303_REGISTER_ACCEL_CTRL_REG4_A, [0b00001000])
		else:						self._bus.write_i2c_block_data(LSM303_ADDRESS_ACCEL, LSM303_REGISTER_ACCEL_CTRL_REG4_A, [0b00000000])

		# Enable the magnetometer
		self._bus.write_i2c_block_data(LSM303_ADDRESS_MAG, LSM303_REGISTER_MAG_MR_REG_M, [0b00000000])

		if magGain in MAG_GAIN:
			self.set_mag_gain(MAG_GAIN[magGain])

		if magFregRate in MAG_RATE:
			self.set_mag_rate(MAG_RATE[magFregRate])

	def read_accel(self):
		#'Read raw acceleration in meters/second squared'
		# Read as signed 12-bit little endian values
		accel_bytes	= self._bus.read_i2c_block_data(LSM303_ADDRESS_ACCEL, LSM303_REGISTER_ACCEL_OUT_X_L_A | 0x80, 6)
		accel_raw	= struct.unpack('<hhh', bytearray(accel_bytes))

		return (
			(accel_raw[0] >> 4) * ACCEL_MS2_PER_LSB,
			(accel_raw[1] >> 4) * ACCEL_MS2_PER_LSB,
			(accel_raw[2] >> 4) * ACCEL_MS2_PER_LSB,
		)

	def set_mag_gain(self, gain):
		#'Set magnetometer gain'
		self._gain	= gain
		if gain	== MAG_GAIN["130"]	:
			self._lsb_per_gauss_xy	= 1100
			self._lsb_per_gauss_z	= 980
		elif gain	== MAG_GAIN["190"]	:
			self._lsb_per_gauss_xy	= 855
			self._lsb_per_gauss_z	= 760
		elif gain	== MAG_GAIN["250"]	:
			self._lsb_per_gauss_xy	= 670
			self._lsb_per_gauss_z	= 600
		elif gain	== MAG_GAIN["400"]	:
			self._lsb_per_gauss_xy	= 450
			self._lsb_per_gauss_z	= 400
		elif gain	== MAG_GAIN["470"]	:
			self._lsb_per_gauss_xy	= 400
			self._lsb_per_gauss_z	= 355
		elif gain	== MAG_GAIN["560"]	:
			self._lsb_per_gauss_xy	= 330
			self._lsb_per_gauss_z	= 295
		elif gain	== MAG_GAIN["810"]	:
			self._lsb_per_gauss_xy	= 230
			self._lsb_per_gauss_z	= 205

		self._bus.write_i2c_block_data(LSM303_ADDRESS_MAG, LSM303_REGISTER_MAG_CRB_REG_M, [self._gain])

	def set_mag_rate(self, rate):
		#'Set magnetometer rate'
		self._bus.write_i2c_block_data(LSM303_ADDRESS_MAG, LSM303_REGISTER_MAG_CRA_REG_M, [(rate & 0x07) << 2])

	def read_mag(self):
		#'Read raw magnetic field in microtesla'
		# Read as signed 16-bit big endian values
		mag_bytes	= self._bus.read_i2c_block_data(LSM303_ADDRESS_MAG, LSM303_REGISTER_MAG_OUT_X_H_M, 6)
		mag_raw	= struct.unpack('>hhh', bytearray(mag_bytes))

		return (
			mag_raw[0] / self._lsb_per_gauss_xy * GAUSS_TO_MICROTESLA,
			mag_raw[2] / self._lsb_per_gauss_xy * GAUSS_TO_MICROTESLA,
			mag_raw[1] / self._lsb_per_gauss_z * GAUSS_TO_MICROTESLA,
		)
		


		
def startSENSOR(devId, i2cAddress,magGain,accelerationGain,magFregRate):
	global theSENSORdict
	try:
		U.logger.log(30,"==== Start "+G.program+"	===== @ i2c= {}".format(i2cAddress)+"  devId={}".format(devId))
		theSENSORdict[devId] = THESENSORCLASS(magGain=magGain, accelerationGain=accelerationGain, magFregRate=magFregRate) 

	except Exception as e:
		U.logger.log(30,"", exc_info=True)



#################################		 
def readParams():
	global sensors, sensor
	global rawOld
	global theSENSORdict, resetPin
	global oldRaw, lastRead
	try:

		inp, inpRaw, lastRead2	= U.doRead(lastTimeStamp=lastRead)
		if inp	== "": return
		if lastRead2	== lastRead: return
		lastRead	= lastRead2
		if inpRaw	== oldRaw: return
		oldRaw		= inpRaw
		externalSensor=False
		sensorsOld= copy.copy(sensors)

		if "sensors"			in inp:	 sensors	=				 (inp["sensors"])

		U.getGlobalParams(inp)
		
		if sensor not in sensors:
			U.logger.log(30, G.program+"is not in parameters	= not enabled, stopping "+G.program )
			exit()
			
		for devId in sensors[sensor]:
			changed =  U.getMAGReadParameters(sensors[sensor][devId],devId) 
			if changed.find("magGain") >-1  or changed.find("accelerationGain") >-1 or changed.find("magFregRate") >-1: 
				U.restartMyself(reason="new gain seetungs require restart ",doPrint=False)

			if devId not in theSENSORdict:
				startSENSOR(devId, G.i2cAddress, sensors[sensor][devId]["magGain"], sensors[sensor][devId]["accelerationGain"], sensors[sensor][devId]["magFregRate"])
				
		deldevID={}		   
		for devId in theSENSORdict:
			if devId not in sensors[sensor]:
				deldevID[devId]=1
		for dd in  deldevID:
			del theSENSORdict[dd]
		if len(theSENSORdict)	==0: 
			####exit()
			pass

	except Exception as e:
		U.logger.log(30,"", exc_info=True)



#################################
def getValues(devId):
	global sensor, sensors,	 theSENSORdict
	try:
		data	= {}
		MAG=  theSENSORdict[devId].read_mag()
		ACC	= theSENSORdict[devId].read_accel()
		MAG	= U.applyOffsetNorm(MAG,sensors[sensor][devId],["magOffsetX","magOffsetY","magOffsetZ",],"magDivider") 

		#print ACC, MAG
		EULER	= U.getEULER(MAG)
			
		data["ACC"]		= fillWithItems(ACC,["x","y","z"],3)
		data["MAG"]		= fillWithItems(MAG,["x","y","z"],2)
		data["EULER"]	= fillWithItems(EULER,["heading","roll","pitch"],2)
		#for xx in data:
		#	U.logger.log(20, (xx).ljust(11)+" {}".format(data[xx]))
		return data
	except Exception as e:
		U.logger.log(30,"", exc_info=True)
	return {"MAG":"bad"}

#################################
def fillWithItems(theList, theItems, digits):
	out={}
	for ii in range(len(theItems)):
		out[theItems[ii]]	= round(theList[ii],digits)
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

lastRead	= time.time()

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

startTime	= time.time()
while True:
	try:
		tt	= time.time()
		if sensor in sensors:
			skip	=False
			
		if sensor in sensors:
			for devId in sensors[sensor]:
				if devId not in lastValue: lastValue[devId]	= copy.copy(lastValueDefault)
				if devId not in G.threshold: G.threshold[devId]	= thresholdDefault
				values	= getValues(devId)
				lastValue	= U.checkMGACCGYRdata(values,lastValue,testDims,testCoords,testForBadSensor,devId,sensor,quick)
					#sumTest=sumTest,singleTest=singleTest)

		loopCount +=1

		quick	= U.checkNowFile(G.program)				 
		U.echoLastAlive(G.program)

		tt= time.time()
		if tt - lastRead > 5.:	
			readParams()
			lastRead	= tt
		if not quick:
			time.sleep(G.sensorLoopWait)
		
	except Exception as e:
		U.logger.log(30,"", exc_info=True)
		time.sleep(5.)
try: 	G.sendThread["run"]	= False; time.sleep(1)
except: pass
ys.exit(0)

