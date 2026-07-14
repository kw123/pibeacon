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
		"""Constructs the MAG3110 magnetometer driver: opens the requested SMBus, sets up calibration/offset/declination state, applies magnetometer parameters, initializes the sensor, and optionally loads calibration data and calibrates.

		Inputs:
		    busNumber (int): I2C bus number to open
		    address (int): I2C device address (defaults if empty string)
		    magDivider (float): magnetometer scaling divider
		    enableCalibration (bool): whether to run calibration
		    declination (float): magnetic declination correction
		    magOffset (str): magnetometer offset; non-empty disables calibration
		    offsetTemp (int): temperature offset correction
		    magResolution (int): magnetometer resolution setting
		Outputs:
		    None: initializes object, opens bus, and configures sensor
		"""
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
		"""Initializes the MAG3110 sensor by probing the I2C connection and configuring CTRL_REG2 (reset/raw mode) and CTRL_REG1 (oversampling, continuous active measurement); returns success or failure.

		Inputs:
		    None.
		Outputs:
		    bool: True if sensor configured successfully, False on I2C error
		"""
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
		"""Triggers a read and reads 18 bytes from the MAG3110, unpacks the raw X/Y/Z magnetometer values and temperature (with sign and offset correction), returning the field vector and temperature; returns a fallback on error.

		Inputs:
		    None.
		Outputs:
		    tuple: ([x, y, z], temp); ([0,0,0,0], -1000) on error
		"""
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
		"""Reads all magnetometer data via rawMagAllData and returns only the raw X/Y/Z magnetic field values, discarding the temperature reading.

		Inputs:
		    None.
		Outputs:
		    list: Raw magnetometer axis values
		"""
		raw,temp = self.rawMagAllData()
		return raw



# read params
# ===========================================================================





#################################		 
def readParams():
	"""Reads the latest parameter file, updates global sensor configuration, and for each MAG device applies calibration/offset parameters, starting any newly seen sensor and cleaning up the active sensor dictionary.

	Inputs:
	    None.
	Outputs:
	    None: Updates global sensor state and configures hardware sensors; returns early if no new data
	"""
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
	"""Instantiates a MAG3110 sensor object for the given device at the I2C address with the supplied calibration parameters, storing it in the global sensor dictionary and optionally running a 5-second calibration when no magnetic offset is preset.

	Inputs:
	    devId (str): Device identifier key into the sensor dictionary
	    i2cAddress (int): I2C bus address of the sensor
	    offsetTemp (float): Temperature offset correction
	    magOffset (list): Per-axis magnetic offset; [0,0,0] triggers calibration
	    magDivider (float): Scaling divider for magnetic readings
	    declination (float): Magnetic declination correction in degrees
	    magResolution (float): Magnetometer resolution setting
	    enableCalibration (bool): Whether to run/apply calibration
	Outputs:
	    None: Creates and stores a sensor object in the global theSENSORdict
	"""
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
	"""Reads corrected magnetometer and temperature data for a device, computes Euler angles (heading, roll, pitch), logs the values, and returns a dict with MAG, EULER, and optional temp entries; returns {'MAG':'bad'} on bad reads or errors.

	Inputs:
	    devId (str): Device identifier key into the sensor dictionary
	Outputs:
	    dict: Mapping with MAG/EULER/temp values, or {'MAG':'bad'} on failure
	"""
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
	"""Builds a dict mapping each label in theItems to the corresponding value in theList, scaled by mult and rounded to the given number of digits.

	Inputs:
	    theList (list): Numeric values to map
	    theItems (list): Key labels for each value
	    digits (int): Decimal places to round to
	    mult (float): Multiplier applied before rounding
	Outputs:
	    dict: Labels mapped to rounded, scaled values
	"""
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
			U.logger.log(30, "starting new calibration in 5 sec for 1 minute.. move sensor around")
			time.sleep(5)
			for devId in theSENSORdict:
				U.magCalibrate(theSENSORdict[devId], force = False,calibTime=30)
			U.logger.log(30, "finished	new calibration")
			
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
