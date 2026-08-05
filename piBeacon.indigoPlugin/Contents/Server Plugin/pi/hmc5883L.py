import math
import struct
import logging


import sys, os, time, json, datetime,subprocess,copy
import smbus

sys.path.append(os.getcwd())
import	piBeaconUtils	as U
import	piBeaconGlobals as G

G.program = "hmc5883L"



# result in micro Tesla per bit
class THESENSORCLASS:
	myaddress=0x1E
	def __init__(self, busNumber=1, address=0x1E, magResolution =1,enableCalibration=False, magDivider = 1.,declination=0, magOffset=""):

		"""Initializes an HMC5883L magnetometer driver: opens the I2C bus, stores address, calibration, divider, declination and offset settings, applies magnetometer parameters, initializes the sensor registers, and optionally loads/runs calibration.

		Inputs:
		    busNumber (int): I2C bus number to open
		    address (int or str): I2C device address; defaults to 0x1E, empty string falls back to default address
		    magResolution (int): magnetometer gain/resolution index (0-7)
		    enableCalibration (bool): whether to load and run calibration
		    magDivider (float): scaling divider applied to magnetometer readings
		    declination (float): magnetic declination correction
		    magOffset (str): magnetometer offset spec; non-empty disables calibration
		Outputs:
		    None: configures instance attributes and hardware; returns early if the I2C bus cannot be opened
		"""
		self.busNumber			 = busNumber
		try:
			self.bus			= smbus.SMBus(self.busNumber)
		except Exception as e:
			U.logger.log(20,'couldn\'t open bus: {0}'.format(e))
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
		U.setMAGParams(self,magOffset=magOffset, magDivider=magDivider, declination=declination)

		self.initSensor(magResolution)

		if self.enableCalibration:	
			U.loadCalibration(self)
			U.magCalibrate(self, force = False,calibTime=5)

	def initSensor(self,magResolution):
		"""Initializes the HMC5883L sensor registers by selecting the microtesla-per-LSB scale from the resolution index and writing the averaging/output-rate, gain, and continuous-measurement mode configuration over I2C.

		Inputs:
		    magResolution (int): gain/resolution index, clamped to 0-7
		Outputs:
		    None: writes configuration bytes to the I2C device; logs on error
		"""
		try:
			uTPerLSBList		= [0.073, 0.092, 0.122, 0.152, 0.227 , 0.256, 0.303 , 0.435]
			magResolution = min(max(magResolution,0),7)
			self.uTPerLSB		= uTPerLSBList[magResolution]
			self.bus.write_byte_data(self.address, 0x00, 0x70) # 8 Average, 15 Hz, normal measurement
			self.bus.write_byte_data(self.address, 0x01, magResolution<< 5) # Scale = bits 5,6,7
			self.bus.write_byte_data(self.address, 0x02, 0x00) # Continuous measurement
		except Exception as e:
			U.logger.log(20,"", exc_info=True)
	def twos_complement(self,val, len):
		# Convert twos compliment to integer
		"""Converts a two's-complement value of the given bit length into a signed integer.

		Inputs:
		    val (int): raw unsigned value to interpret
		    len (int): number of bits in the value
		Outputs:
		    int: signed integer interpretation of the input
		"""
		if (val & (1 << len - 1)):
			val = val - (1<<len)
		return val

	def convert(self, data, offset):
		"""Combines two consecutive bytes of I2C data at the given offset into a 16-bit signed value via two's complement; returns a sentinel -99999 when the reading is the saturation value -4096.

		Inputs:
		    data (list): block of raw bytes read from the sensor
		    offset (int): starting index of the high byte within data
		Outputs:
		    int: signed axis reading, or -99999 if saturated
		"""
		val = self.twos_complement(data[offset] << 8 | data[offset+1], 16)
		if val == -4096: return -99999
		return val

	def getRawMagData(self):
		"""Reads a raw I2C data block from the HMC5883L and converts it into the X, Y and Z magnetometer axis values.

		Inputs:
		    None.
		Outputs:
		    list: list of three signed integers [x, y, z]
		"""
		data = self.bus.read_i2c_block_data(self.address, 0x00)
		x = self.convert(data, 3)
		y = self.convert(data, 7)
		z = self.convert(data, 5)
		return [x,y,z]
	def getMagData(self):
		"""Returns the magnetometer X/Y/Z data by delegating to getRawMagData.

		Inputs:
		    None.
		Outputs:
		    list: list of three signed integers [x, y, z]
		"""
		return self.getRawMagData()




# read params
# ===========================================================================

#################################		 
def readParams():
	"""Reads fresh plugin parameters, skips processing if input is empty/unchanged, verifies this sensor is enabled (exiting if not), then for each configured device loads magnetometer read parameters, starts the sensor if new, applies mag params, and prunes the active sensor list.

	Inputs:
	    None.
	Outputs:
	    None: updates module globals and per-device sensor objects; returns early on no/unchanged input, exits if sensor not enabled, logs on error
	"""
	global sensors, sensor 
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
			U.logger.log(20, G.program+" is not in parameters = not enabled, stopping "+G.program+".py" )
			exit()
				
		for devId in sensors[sensor]:
			U.getMAGReadParameters(sensors[sensor][devId],devId)
			if devId not in theSENSORdict:
				startTheSensor(devId, G.i2cAddress,	 G.magResolution[devId],  G.declination[devId],	 G.magOffset[devId],  G.magDivider[devId],	G.enableCalibration[devId])
			U.setMAGParams(theSENSORdict[devId],magOffset= G.magOffset[devId], magDivider= G.magDivider[devId], declination= G.declination[devId])
		 
		theSENSORdict = U.cleanUpSensorlist( sensors[sensor], theSENSORdict)	   

	except Exception as e:
		U.logger.log(20,"", exc_info=True)

#################################
def startTheSensor(devId, i2cAddress, magResolution, declination, magOffset, magDivider, enableCalibration=False):
	"""Instantiates and registers an HMC5883L magnetometer sensor object in the global theSENSORdict keyed by device id, passing address, resolution, divider, declination and offset; runs a 5-second calibration when enabled and no offset is provided.

	Inputs:
	    devId (str): Indigo device id used as the key in the sensor dictionary
	    i2cAddress (int): I2C bus address of the magnetometer
	    magResolution (int): magnetometer resolution/gain setting
	    declination (float): magnetic declination correction
	    magOffset (list): hard-iron offset triple [x,y,z]; empty/zero triggers calibration
	    magDivider (float): scaling divider applied to magnetometer readings
	    enableCalibration (bool): whether to run sensor calibration
	Outputs:
	    None: creates the sensor object, may calibrate, and logs; no return value
	"""
	global theSENSORdict
	try:
		U.logger.log(20,"==== Start "+G.program+" ===== @ i2c= {}".format(i2cAddress)+"	devId={}".format(devId))
		if magOffset == [0,0,0]:
			theSENSORdict[devId] = THESENSORCLASS(address=i2cAddress, magResolution = magResolution, enableCalibration=enableCalibration, magDivider=magDivider, declination = declination, magOffset= magOffset)
			if enableCalibration:
				theSENSORdict[devId].calibrate(calibTime=5)
		else:
			theSENSORdict[devId] = THESENSORCLASS(address=i2cAddress, magResolution = magResolution, enableCalibration=enableCalibration, magDivider=magDivider, declination = declination)

	except Exception as e:
		U.logger.log(20,"", exc_info=True)



#################################
def getValues(devId):
	"""Reads magnetometer data for the given device, applies offset/divider correction and computes Euler angles (heading, roll, pitch), returning a dict with MAG and EULER sub-dicts; returns {'MAG':'bad'} on error.

	Inputs:
	    devId (str): device id whose sensor object is read from theSENSORdict
	Outputs:
	    dict: {'MAG':{x,y,z}, 'EULER':{heading,roll,pitch}} or {'MAG':'bad'} on failure
	"""
	global theSENSORdict
	data={}
	try:
		raw		  = theSENSORdict[devId].getMagData()
		magCorr	  = U.magDataCorrected(theSENSORdict[devId], raw )
		EULER	  = U.getEULER(magCorr,theClass = theSENSORdict[devId])
		data["MAG"]	  = fillWithItems(magCorr,	 ["x","y","z"],2,mult=1.)
		data["EULER"] = fillWithItems(EULER,	 ["heading","roll","pitch"],2)
		#print data
		U.logger.log(10, "raw".ljust(11)+" {}".format(raw))
		for xx in data:
			U.logger.log(10, (xx).ljust(11)+" {}".format(data[xx]))
		return data
	except Exception as e:
		U.logger.log(20,"", exc_info=True)
	return {"MAG":"bad"}

def fillWithItems(theList,theItems,digits,mult=1):
	"""Builds a dict mapping each name in theItems to the corresponding value in theList, multiplied by mult and rounded to digits decimals.

	Inputs:
	    theList (list): numeric values to assign, aligned by index with theItems
	    theItems (list): key names for the output dict
	    digits (int): number of decimal places to round to
	    mult (float): multiplier applied to each value before rounding
	Outputs:
	    dict: mapping of each item name to its rounded, scaled value
	"""
	out={}
	for ii in range(len(theItems)):
		out[theItems[ii]] = round(mult*theList[ii],digits)
	return out


############################################
global sensor, sensors
global theSENSORdict
global oldRaw, lastRead
oldRaw						= ""
lastRead					= 0

loopCount					= 0
NSleep						= 100
sensors						= {}
sensor						= G.program
quick						= False
rawOld						= ""
theSENSORdict				={}
myPID		= str(os.getpid())
U.killOldPgm(myPID,G.program+".py")# kill old instances of myself if they are still running


if U.getIPNumber() > 0:
	time.sleep(10)
	exit()
U.setLogging()

readParams()

lastRead = time.time()

U.echoLastAlive(G.program)

lastValue			= {}
lastRead			= time.time()
G.lastAliveSend		= time.time() -1000
lastValueDefault	= {"EULER":{"heading":0,"roll":0,"pitch":0},"MAG":{"x":-100000,"y":11110,"z":11110},"temp":0}
testDims			= ["MAG"]
testCoords			= ["x","y","z"]
testForBadSensor	= "MAG"
lastValue			= {}
thresholdDefault	= 2.

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

		tt= time.time()
		if tt - lastRead > 5.:	
			readParams()
			lastRead = tt
		if not quick:
			time.sleep(G.sensorLoopWait)
		
	except Exception as e:
		U.logger.log(20,"", exc_info=True)
		time.sleep(5.)
try: 	G.sendThread["run"] = False; time.sleep(1)
except: pass
sys.exit(0)
