#!/usr/bin/python
# -*- coding: utf-8 -*-
## adopted from adafruit 
#
#
import math
import struct
import logging


import sys, os, time, json, datetime,subprocess,copy
import smbus

sys.path.append(os.getcwd())
import	piBeaconUtils	as U
import	piBeaconGlobals as G

G.program = "mag3110"


# result in micro Tesla per bit

class THESENSORCLASS():
	myaddress = 0x0E
	def __init__(self, busNumber=1, address=0x0E,	 magDivider=1, enableCalibration=False, declination=0,magOffset="", offsetTemp=0, magResolution =1):
		try:

			self.busNumber			 = busNumber
			try:
				self.bus			= smbus.SMBus(self.busNumber)
			except Exception as e:
				U.logger.log(30,'couldn\'t open bus: {0}'.format(e))
				return 
			
			self.enableCalibration	 = enableCalibration
			self.heading			 = 0
			self.calibrationFile	 = G.homeDir+G.program+'.calib'
			if address =="": address = self.myaddress
			self.address			 = address
			self.offsetTemp			 = 0
			self.magDivider			 = 1.
			self.declination		 = 0.
			self.calibrations		= {'maxX':0,'minX':0,'maxY':0, 'minY':0, 'maxZ':0, 'minZ':0}
			self.magOffset			 = [0,0,0]
			if magOffset!="":
				self.enableCalibration = False

			U.setMAGParams(self,magOffset=magOffset, magDivider=magDivider, declination=declination, offsetTemp=offsetTemp)

			if not self.initSensor(): return

			if self.enableCalibration:	
				self.calibrations= U.loadCalibration(self.calibrationFile)
				U.magCalibrate(self, force = False,calibTime=5)
		except Exception as e:
			U.logger.log(30,"", exc_info=True)
			return


	def initSensor(self):
		try:
			# read a byte to see if the i2c connection is working
			# disregared
			#pylint: disable=unused-variable
			byte = self.bus.read_byte_data(self.address, 1)
			U.logger.log(10,'Found compass at {0}'.format(self.address))
		except Exception as e:
			U.logger.log(30,"", exc_info=True)
			return False

		#warm up the compass
		register = 0x11				# CTRL_REG2
		data  = (1 << 7)			# Reset before each acquisition
		data |= (1 << 5)			# Raw mode, do not apply user offsets
		data |= (0 << 5)			# Disable reset cycle
		try:
			self.bus.write_byte_data(self.address, register, data)
		except Exception as e:
			U.logger.log(30,"", exc_info=True)
			return False

		# System operation
		register = 0x10				# CTRL_REG1
		data  = (0 << 5)			# Output data rate (10 Hz when paired with 128 oversample)
		data |= (3 << 3)			# Oversample of 128
		data |= (0 << 2)			# Disable fast read
		data |= (0 << 1)			# Continuous measurement
		data |= (1 << 0)			# Active mode
		try:
			self.bus.write_byte_data(self.address, register, data)
		except Exception as e:
			U.logger.log(30,"", exc_info=True)
			return False
		return True


	def rawMagAllData(self):
		try:
			self.bus.write_byte(self.address, 0x00)
			# disable=unused-variable
			[status, xh, xl, yh, yl, zh, zl, who, sm, oxh, oxl, oyh, oyl, ozh, ozl, temp, c1, c2] = self.bus.read_i2c_block_data(self.address, 0, 18)
			#print "bits >>>",status, xh, xl, yh, yl, zh, zl, who, sm, oxh, oxl, oyh, oyl, ozh, ozl, temp, c1, c2,"<<<< \n"

			xyz = struct.pack('BBBBBB', xl, xh, yl, yh, zl, zh)
			x, y, z = struct.unpack('hhh', xyz)


			if temp > 127:	temp -= 256
			if temp < -30:	temp = -99
			else:			temp += self.offsetTemp

		except Exception as e:
			U.logger.log(30,"", exc_info=True)
			return [0,0,0,0],-1000

		return [x,y,z],temp

	def getRawMagData(self):
		raw,temp = self.rawMagAllData()
		return raw



# read params
# ===========================================================================





#################################		 
def readParams():
	global sensors, sensor
	global rawOld
	global theSENSORdict
	global oldRaw, lastRead
	try:

		inp, inpRaw, lastRead2 = U.doRead(lastTimeStamp=lastRead)
		if inp == "": return
		if lastRead2 == lastRead: return
		lastRead   = lastRead2
		if inpRaw == oldRaw: return
		oldRaw	   = inpRaw

		U.getGlobalParams(inp)
		if "sensors"			in inp:	 sensors =				 (inp["sensors"])

 
		if sensor not in sensors:
			U.logger.log(30, G.program+" is not in parameters = not enabled, stopping "+G.program+".py" )
			exit()
				
		for devId in sensors[sensor]:
			U.getMAGReadParameters(sensors[sensor][devId],devId)
			if devId not in theSENSORdict:
				startTheSensor(devId, G.i2cAddress, G.offsetTemp[devId], G.magOffset[devId], G.magDivider[devId], G.declination[devId], G.magResolution[devId],G.enableCalibration[devId])
			U.setMAGParams(theSENSORdict[devId],magOffset=G.magOffset[devId], magDivider=G.magDivider[devId],enableCalibration=G.enableCalibration[devId], declination=G.declination[devId], offsetTemp=G.offsetTemp[devId])
			 
		theSENSORdict = U.cleanUpSensorlist( sensors[sensor], theSENSORdict)	   

	except Exception as e:
		U.logger.log(30,"", exc_info=True)

#################################
def startTheSensor(devId, i2cAddress,offsetTemp , magOffset, magDivider, declination, magResolution,enableCalibration):
	global theSENSORdict
	try:
		U.logger.log(30,"==== Start "+G.program+" ===== @ i2c= {}".format(i2cAddress)+"	devId={}".format(devId))
		if magOffset == [0,0,0]:
			theSENSORdict[devId] = THESENSORCLASS(address=i2cAddress,  magDivider= magDivider, enableCalibration=enableCalibration, declination=declination,magOffset=magOffset, offsetTemp =offsetTemp)
			if enableCalibration:
				theSENSORdict[devId].calibrate(calibTime=5)
		else:
			theSENSORdict[devId] = THESENSORCLASS(address=i2cAddress,  magDivider= magDivider, enableCalibration=enableCalibration, declination=declination, offsetTemp =offsetTemp)
	except Exception as e:
		U.logger.log(30,"", exc_info=True)



#################################
def getValues(devId):
	global sensor, sensors,	 theSENSORdict
	data={}
	try:
		raw,temp  = theSENSORdict[devId].rawMagAllData()
		magCorr	  = U.magDataCorrected( theSENSORdict[devId], raw)
		EULER	  = U.getEULER( magCorr ,theClass = theSENSORdict[devId])
		if temp ==-1000:
			return {"MAG":"bad"}
		elif temp !=-99:
			data["temp "] = temp

		data["MAG"]	  = fillWithItems(magCorr,			  ["x","y","z"],2,mult=1.)
		data["EULER"] = fillWithItems(EULER,["heading","roll","pitch"],2)
		#print data
		U.logger.log(10, "raw".ljust(11)+" {}".format(raw))
		for xx in data:
			U.logger.log(10, (xx).ljust(11)+" {}".format(data[xx]))
		return data
	except Exception as e:
		U.logger.log(30,"", exc_info=True)
	return {"MAG":"bad"}

def fillWithItems(theList,theItems,digits,mult=1):
	out={}
	for ii in range(len(theItems)):
		out[theItems[ii]] = round(mult*theList[ii],digits)
	return out


############################################
global rawOld
global sensor, sensors, badSensor
global oldRaw,	lastRead
oldRaw					= ""
lastRead				= 0

loopCount					= 0
NSleep						= 100
sensors						= {}
sensor						= G.program
quick						= False
theSENSORdict				 ={}
U.setLogging()

myPID		= str(os.getpid())
U.killOldPgm(myPID,G.program+".py")# kill old instances of myself if they are still running


if U.getIPNumber() > 0:
	time.sleep(10)
	exit()

readParams()

time.sleep(1)

U.echoLastAlive(G.program)

lastRead			= time.time()
G.lastAliveSend		= time.time() -1000
lastValueDefault	= {"EULER":{"heading":0,"roll":0,"pitch":0},"MAG":{"x":-100000,"y":0,"z":0},"temp":0}
lastValue ={}
testDims			= ["MAG"]
testCoords			= ["x","y","z"]
testForBadSensor	= "MAG"
lastValue			= {}
thresholdDefault	= 0.01


while True:
	try:
		tt = time.time()
		if sensor in sensors:
			for devId in sensors[sensor]:
				if devId not in lastValue:	 lastValue[devId]	= copy.copy(lastValueDefault)
				if devId not in G.threshold: G.threshold[devId] = thresholdDefault
				values = getValues(devId)
				lastValue =U.checkMGACCGYRdata(
					values,lastValue, testDims,testCoords,testForBadSensor,devId,sensor,quick)

		loopCount +=1
		quick = U.checkNowFile(G.program)				 
		if U.checkNewCalibration(G.program):
			U.logger.log(30, u"starting new calibration in 5 sec for 1 minute.. move sensor around")
			time.sleep(5)
			for devId in theSENSORdict:
				U.magCalibrate(theSENSORdict[devId], force = False,calibTime=30)
			U.logger.log(30, u"finished	new calibration")
			
		U.echoLastAlive(G.program)

		tt= time.time()
		if tt - lastRead > 5.:	
			readParams()
			lastRead = tt
		if not quick:
			time.sleep(G.sensorLoopWait)
		
	except Exception as e:
		U.logger.log(30,"", exc_info=True)
		time.sleep(5.)
try: 	G.sendThread["run"] = False; time.sleep(1)
except: pass
sys.exit(0)
