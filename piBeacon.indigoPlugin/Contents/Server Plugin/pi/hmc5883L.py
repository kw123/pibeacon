import math
import struct
import logging


import sys, os, time, json, datetime,subprocess,copy
import smbus

sys.path.append(os.getcwd())
import	piBeaconUtils	as U
import	piBeaconGlobals as G
G.program = "hmc5883L"
G.debug = 0



# result in micro Tesla per bit
class THESENSORCLASS:
	myaddress=0x1E
	def __init__(self, busNumber=1, address=0x1E, magResolution =1,enableCalibration=False, magDivider = 1.,declination=0, magOffset=""):

		self.busNumber			 = busNumber
		try:
			self.bus			= smbus.SMBus(self.busNumber)
		except Exception, e:
			U.toLog(-1,'couldn\'t open bus: {0}'.format(e))
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
		try:
			uTPerLSBList		= [0.073, 0.092, 0.122, 0.152, 0.227 , 0.256, 0.303 , 0.435]
			magResolution = min(max(magResolution,0),7)
			self.uTPerLSB		= uTPerLSBList[magResolution]
			self.bus.write_byte_data(self.address, 0x00, 0x70) # 8 Average, 15 Hz, normal measurement
			self.bus.write_byte_data(self.address, 0x01, magResolution<< 5) # Scale = bits 5,6,7
			self.bus.write_byte_data(self.address, 0x02, 0x00) # Continuous measurement
		except	Exception, e:
			U.toLog(-1, u"in Line {} has error={}".format(sys.exc_traceback.tb_lineno, e))
	def twos_complement(self,val, len):
		# Convert twos compliment to integer
		if (val & (1 << len - 1)):
			val = val - (1<<len)
		return val

	def convert(self, data, offset):
		val = self.twos_complement(data[offset] << 8 | data[offset+1], 16)
		if val == -4096: return -99999
		return val

	def getRawMagData(self):
		data = self.bus.read_i2c_block_data(self.address, 0x00)
		x = self.convert(data, 3)
		y = self.convert(data, 7)
		z = self.convert(data, 5)
		return [x,y,z]
	def getMagData(self):
		return self.getRawMagData()




# read params
# ===========================================================================

#################################		 
def readParams():
	global sensors, sensor 
	global theSENSORdict 
	global oldRaw, lastRead
	try:

		inp,inpRaw,lastRead2 = U.doRead(lastTimeStamp=lastRead)
		if inp == "": return
		if lastRead2 == lastRead: return
		lastRead   = lastRead2
		if inpRaw == oldRaw: return
		oldRaw	   = inpRaw

		U.getGlobalParams(inp)
		if "sensors"			in inp:	 sensors =				 (inp["sensors"])
		if "debugRPI"			in inp:	 G.debug=			  int(inp["debugRPI"]["debugRPISENSOR"])
 
		if sensor not in sensors:
			U.toLog(-1, G.program+" is not in parameters = not enabled, stopping "+G.program+".py" )
			exit()
				
		for devId in sensors[sensor]:
			U.getMAGReadParameters(sensors[sensor][devId],devId)
			if devId not in theSENSORdict:
				startTheSensor(devId, G.i2cAddress,	 G.magResolution[devId],  G.declination[devId],	 G.magOffset[devId],  G.magDivider[devId],	G.enableCalibration[devId])
			U.setMAGParams(theSENSORdict[devId],magOffset= G.magOffset[devId], magDivider= G.magDivider[devId], declination= G.declination[devId])
		 
		theSENSORdict = U.cleanUpSensorlist( sensors[sensor], theSENSORdict)	   

	except	Exception, e:
		U.toLog(-1, u"in Line {} has error={}".format(sys.exc_traceback.tb_lineno, e))

#################################
def startTheSensor(devId, i2cAddress, magResolution, declination, magOffset, magDivider, enableCalibration=False):
	global theSENSORdict
	try:
		U.toLog(-1,"==== Start "+G.program+" ===== @ i2c= " +unicode(i2cAddress)+"	devId=" +unicode(devId))
		if magOffset == [0,0,0]:
			theSENSORdict[devId] = THESENSORCLASS(address=i2cAddress, magResolution = magResolution, enableCalibration=enableCalibration, magDivider=magDivider, declination = declination, magOffset= magOffset)
			if enableCalibration:
				theSENSORdict[devId].calibrate(calibTime=5)
		else:
			theSENSORdict[devId] = THESENSORCLASS(address=i2cAddress, magResolution = magResolution, enableCalibration=enableCalibration, magDivider=magDivider, declination = declination)

	except	Exception, e:
		U.toLog(-1, u"in Line {} has error={}".format(sys.exc_traceback.tb_lineno, e))



#################################
def getValues(devId):
	global theSENSORdict
	data={}
	try:
		raw		  = theSENSORdict[devId].getMagData()
		magCorr	  = U.magDataCorrected(theSENSORdict[devId], raw )
		EULER	  = U.getEULER(magCorr,theClass = theSENSORdict[devId])
		data["MAG"]	  = fillWithItems(magCorr,	 ["x","y","z"],2,mult=1.)
		data["EULER"] = fillWithItems(EULER,	 ["heading","roll","pitch"],2)
		#print data
		U.toLog(2, "raw".ljust(11)+" "+unicode(raw))
		for xx in data:
			U.toLog(2, (xx).ljust(11)+" "+unicode(data[xx]))
		return data
	except	Exception, e:
		U.toLog(-1, u"in Line {} has error={}".format(sys.exc_traceback.tb_lineno, e))
	return {"MAG":"bad"}

def fillWithItems(theList,theItems,digits,mult=1):
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

G.debug						= 5
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
		
	except	Exception, e:
		U.toLog(-1, u"in Line {} has error={}".format(sys.exc_traceback.tb_lineno, e))
		time.sleep(5.)
sys.exit(0)
