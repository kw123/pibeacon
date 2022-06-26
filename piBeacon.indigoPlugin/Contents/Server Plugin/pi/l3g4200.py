#!/usr/bin/python
# -*- coding: utf-8 -*-
## adopted from adafruit 
#
#

import sys, os, time, json, datetime,subprocess,copy
import smbus

sys.path.append(os.getcwd())
import	piBeaconUtils	as U
import	piBeaconGlobals as G
import traceback
G.program = "l3g4200"


# ===========================================================================
# L3G4200 Class
# ===========================================================================
class THESENSORCLASS:

	__L3G4200_ADDRESS					  = 0x69


# ===========================================================================
#	 CALIBRATION REGISTER (R/W)
	__L3G4200_REG_CALIBRATION			  = 0x05
# ===========================================================================


	 # Constructor
	def __init__(self, i2cAddress=""):

		try:
			if i2cAddress =="" or i2cAddress ==0:
				self.i2cAddress = self.__L3G4200_ADDRESS 
			else:
				self.i2cAddress = i2cAddress
				
			self.bus = smbus.SMBus(1)

			self.L3G4200SetCalibration()

		except	Exception as e:
			U.logger.log(30, u"in Line {} has error={}".format(traceback.extract_tb(sys.exc_info()[2])[-1][1], e))
		return 

	def L3G4200SetCalibration(self):
		# L3G4200D address, i2cAddress(104)
		# Select Control register1, 0x20(32)
		#		0x0F(15)	Normal mode, X, Y, Z-Axis enabled
		#  BW = 00 = ODR = 100Hz 
		#  DR = 00 = 12.5 Hz cutoff
		#  normal = 1000
		#  z	  = 0100
		#  Y	  = 0010
		#  X	  = 0001  
		self.bus.write_byte_data(self.i2cAddress, 0x20, 0b00001111)

		# L3G4200D address, i2cAddress(104)
		# Select Control register4, 0x23(35)
		#		0x30(48)	Continous update, Data LSB at lower address
		#					FSR 2000dps, Self test disabled, 4-wire interface
		# 4wire					= 0000000x x=0
		# selftest				= 00000xx0 xx = 00
		# fullscale				= 00xx0000 xx = 11 2000dps max
		# Big/Little Endian		= 0x000000 x = 0 data LSB @ lower address
		# blockupdate			= x0000000 x = 0 continuous update
		self.bus.write_byte_data(self.i2cAddress, 0x23, 0b00110000)

	def getXYZ(self):
		try:
			# L3G4200D address, i2cAddress(104)
			# Read data back from 0x28(40), 2 bytes, X-Axis LSB first
			data0 = self.bus.read_byte_data(self.i2cAddress, 0x28)
			data1 = self.bus.read_byte_data(self.i2cAddress, 0x29)
			# Convert the data
			xGyro = data1 * 256 + data0
			if xGyro > 32767 :
				xGyro -= 65536

			# L3G4200D address, i2cAddress(104)
			# Read data back from 0x2A(42), 2 bytes, Y-Axis LSB first
			data0 = self.bus.read_byte_data(self.i2cAddress, 0x2A)
			data1 = self.bus.read_byte_data(self.i2cAddress, 0x2B)
			# Convert the data
			yGyro = data1 * 256 + data0
			if yGyro > 32767 :
				yGyro -= 65536

			# L3G4200D address, i2cAddress(104)
			# Read data back from 0x2C(44), 2 bytes, Z-Axis LSB first
			data0 = self.bus.read_byte_data(self.i2cAddress, 0x2C)
			data1 = self.bus.read_byte_data(self.i2cAddress, 0x2D)
			# Convert the data
			zGyro = data1 * 256 + data0
			if zGyro > 32767 :
				zGyro -= 65536

			return xGyro, yGyro, zGyro
		except	Exception as e:
			pass
		return -9999999999990,0,0

	def getTemp(self):	### very rough in celsius
		try:
			temp = self.bus.read_byte_data(self.i2cAddress, 0x26)
			# Convert the data
			if temp > 127 :
				temp -= 128
			temp = 128 - temp  - 90	 # it goes down with rising temp so 128 - temp	- fudge factor 
			return float(int(temp))
		except	Exception as e:
			pass
		return -99	  
		
# ===========================================================================
# read params
# ===========================================================================

#################################		 
def readParams():
	global sensors, sensor
	global threshold, theSENSORdict
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

		
 
		if sensor not in sensors:
			U.logger.log(30, G.program+" is not in parameters = not enabled, stopping "+G.program )
			exit()

		for devId in sensors[sensor]:
			U.getMAGReadParameters(sensors[sensor][devId],devId)

			if devId not in theSENSORdict:
				U.logger.log(30,"==== Start "+G.program+" ===== @ i2c= " +unicode(G.i2cAddress))
				theSENSORdict[devId] = THESENSORCLASS(i2cAddress=G.i2cAddress)
				
		deldevID={}		   
		for devId in theSENSORdict:
			if devId not in sensors[sensor]:
				deldevID[devId]=1
		for dd in  deldevID:
			del theSENSORdict[dd]
		if len(theSENSORdict) ==0: 
			####exit()
			pass

	except	Exception as e:
		U.logger.log(30, u"in Line {} has error={}".format (traceback.extract_tb(sys.exc_info()[2])[-1][1], e))



#################################
def getValues(devId):
	global sensor, sensors,	 theSENSORdict, badSensor

	for ii in range(2):
		try:
			x,y,z  = theSENSORdict[devId].getXYZ()
			if x =="": 
				badSensor+=1
				continue
			temp = theSENSORdict[devId].getTemp() - G.offsetTemp[devId]
			data = {"GYR":{"x":x, "y":y, "z":z},"temp":temp}
			U.logger.log(10, unicode(data))
			badSensor = 0
			return data
		except	Exception as e:
			if badSensor > 2 and badSensor < 5: 
				U.logger.log(30, u"in Line {} has error={}".format (traceback.extract_tb(sys.exc_info()[2])[-1][1], e) +"  "+ unicode(badSensor))
			badSensor+=1
	if badSensor >3: return "badSensor"
	return{"GYR":{"x":"", "y":"", "z":""},"temp":"" }	






############################################
global rawOld
global sensor, sensors, badSensor
global theSENSORdict, badSensor
global oldRaw,	lastRead
oldRaw					= ""
lastRead				= 0

badSensor					= 0
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

U.echoLastAlive(G.program)


lastValue			= {}
lastRead			= time.time()
G.lastAliveSend		= time.time() -1000
lastValueDefault	= {"GYR":{"x":0,"y":0,"z":0}}
testDims			= ["GYR"]
testCoords			= ["x","y","z"]
testForBadSensor	= "GYR"
thresholdDefault	= 20.

sensorWasBad = False
while True:
	try:
		if sensor in sensors:
			for devId in sensors[sensor]:
				if devId not in lastValue:	 lastValue[devId]	= copy.copy(lastValueDefault)
				if devId not in G.threshold: G.threshold[devId] = thresholdDefault
				values = getValues(devId)
				lastValue =U.checkMGACCGYRdata(
					values,lastValue,testDims,testCoords,testForBadSensor,devId,sensor,quick)

		loopCount +=1

		quick = U.checkNowFile(G.program)				 
		U.echoLastAlive(G.program)
		tt = time.time()
		if tt - lastRead > 5.:	
			readParams()
			lastRead = tt
		if not quick:
			time.sleep(G.sensorLoopWait)
		
	except	Exception as e:
		U.logger.log(30, u"in Line {} has error={}".format (traceback.extract_tb(sys.exc_info()[2])[-1][1], e))
		time.sleep(5.)
try: 	G.sendThread["run"] = False; time.sleep(1)
except: pass
sys.exit(0)
