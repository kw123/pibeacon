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
G.program = "ina219"
G.debug = 0


# ===========================================================================
# INA219 Class
# ===========================================================================
class INA219:

# ===========================================================================
	__INA219_ADDRESS						 = 0x40	   # I2C ADDRESS/BITS 1000000 (A0+A1=GND)
	__INA219_READ							 = 0x01
# ===========================================================================
	__INA219_REG_CONFIG						 = 0x00	   # CONFIG REGISTER (R/W)
# ===========================================================================
	__INA219_CONFIG_RESET					 = 0b1000000000000000	# Reset Bit
	
	__INA219_CONFIG_BVOLTAGERANGE_MASK		 = 0b0010000000000000	# Bus Voltage Range Mask
	__INA219_CONFIG_BVOLTAGERANGE_16V		 = 0b0000000000000000	# 0-16V Range
	__INA219_CONFIG_BVOLTAGERANGE_32V		 = 0b0010000000000000	# 0-32V Range <<<< default

	__INA219_CONFIG_GAIN_MASK				 = 0b0001100000000000  # Gain Mask
	__INA219_CONFIG_GAIN_1_40MV				 = 0b0000000000000000  # Gain 1, 40mV Range
	__INA219_CONFIG_GAIN_2_80MV				 = 0b0000100000000000  # Gain 2, 80mV Range
	__INA219_CONFIG_GAIN_4_160MV			 = 0b0001000000000000  # Gain 4, 160mV Range
	__INA219_CONFIG_GAIN_8_320MV			 = 0b0001100000000000  # Gain 8, 320mV Range <<<< default

	__INA219_CONFIG_BADCRES_MASK			 = 0b0000011110000000  # Bus ADC Resolution Mask
	__INA219_CONFIG_BADCRES_9BIT			 = 0b0000000010000000  # 9-bit bus res = 0..511
	__INA219_CONFIG_BADCRES_10BIT			 = 0b0000000100000000  # 10-bit bus res = 0..1023
	__INA219_CONFIG_BADCRES_11BIT			 = 0b0000001000000000  # 11-bit bus res = 0..2047
	__INA219_CONFIG_BADCRES_12BIT			 = 0b0000010000000000  # 12-bit bus res = 0..4097 <<<< default

	__INA219_CONFIG_SADCRES_MASK			 = 0b0000000001111000  # Shunt ADC Resolution and Averaging Mask
	__INA219_CONFIG_SADCRES_9BIT_1S_84US	 = 0b0000000000000000  # 1 x 9-bit shunt sample
	__INA219_CONFIG_SADCRES_10BIT_1S_148US	 = 0b0000000000001000  # 1 x 10-bit shunt sample
	__INA219_CONFIG_SADCRES_11BIT_1S_276US	 = 0b0000000000010000  # 1 x 11-bit shunt sample
	__INA219_CONFIG_SADCRES_12BIT_1S_532US	 = 0b0000000000011000  # 1 x 12-bit shunt sample  <<<< default
	__INA219_CONFIG_SADCRES_12BIT_2S_1060US	 = 0b0000000001001000  # 2 x 12-bit shunt samples averaged together
	__INA219_CONFIG_SADCRES_12BIT_4S_2130US	 = 0b0000000001010000  # 4 x 12-bit shunt samples averaged together
	__INA219_CONFIG_SADCRES_12BIT_8S_4260US	 = 0b0000000001011000  # 8 x 12-bit shunt samples averaged together
	__INA219_CONFIG_SADCRES_12BIT_16S_8510US = 0b0000000001100000  # 16 x 12-bit shunt samples averaged together
	__INA219_CONFIG_SADCRES_12BIT_32S_17MS	 = 0b0000000001101000  # 32 x 12-bit shunt samples averaged together
	__INA219_CONFIG_SADCRES_12BIT_64S_34MS	 = 0b0000000001110000  # 64 x 12-bit shunt samples averaged together
	__INA219_CONFIG_SADCRES_12BIT_128S_69MS	 = 0b0000000001111000  # 128 x 12-bit shunt samples averaged together

	__INA219_CONFIG_MODE_MASK				 = 0x0007  # Operating Mode Mask
	__INA219_CONFIG_MODE_POWERDOWN			 = 0x0000
	__INA219_CONFIG_MODE_SVOLT_TRIGGERED	 = 0x0001
	__INA219_CONFIG_MODE_BVOLT_TRIGGERED	 = 0x0002
	__INA219_CONFIG_MODE_SANDBVOLT_TRIGGERED = 0x0003
	__INA219_CONFIG_MODE_ADCOFF				 = 0x0004
	__INA219_CONFIG_MODE_SVOLT_CONTINUOUS	 = 0x0005
	__INA219_CONFIG_MODE_BVOLT_CONTINUOUS	 = 0x0006
	__INA219_CONFIG_MODE_SANDBVOLT_CONTINUOUS = 0x0007 #<<<< default
# ===========================================================================

# ===========================================================================
#	SHUNT VOLTAGE REGISTER (R)
	__INA219_REG_SHUNTVOLTAGE				 = 0x01
# ===========================================================================
#	BUS VOLTAGE REGISTER (R)
	__INA219_REG_BUSVOLTAGE					 = 0x02
# ===========================================================================
#	POWER REGISTER (R)
	__INA219_REG_POWER						 = 0x03
# ==========================================================================
#	 CURRENT REGISTER (R)
	__INA219_REG_CURRENT					 = 0x04
# ===========================================================================
#	 CALIBRATION REGISTER (R/W)
	__INA219_REG_CALIBRATION				 = 0x05
# ===========================================================================


	 # Constructor
	def __init__(self, i2cAddress="",shuntResistor=0.1):


		if i2cAddress =="" or i2cAddress ==0:
			self.i2cAddress = self.__INA219_ADDRESS 
		else:
			self.i2cAddress = i2cAddress
				
		self.bus = smbus.SMBus(1)
		 
		self.ina219SetCalibration_32V_2A(shuntResistor)
	
	def twosToInt(self, val, ll):
		# Convert twos compliment to integer
		if(val & (1 << ll - 1)):
			val = val - (1<<ll)
		return val

	def ina219SetCalibration_32V_2A(self, shuntResistor):
		self.ina219_currentMultiplier_mA = shuntResistor	# Current LSB = 100uA per bit (1000/100 = 10)
		self.ina219_powerMutiplier_mW	 = 2	 # Power LSB = 1mW per bit (2/1)
		self.ina219_busMultiplier		 = 4./1000.		# bus voltage LSB = 4mV	 ==> in volt
		self.ina219_ShuntVoltageMultiplier = shuntResistor *0.1		# bus voltage LSB = 4mV

		# Set Calibration register to 'Cal' calculated above	
		bb = [(0x1000 >> 8) & 0xFF, 0x1000 & 0xFF]
		self.bus.write_i2c_block_data(self.i2cAddress, self.__INA219_REG_CALIBRATION, bb)
		
		# Set Config register to take into account the settings above
		config = self.__INA219_CONFIG_BVOLTAGERANGE_32V | \
				 self.__INA219_CONFIG_GAIN_8_320MV | \
				 self.__INA219_CONFIG_BADCRES_12BIT | \
				 self.__INA219_CONFIG_SADCRES_12BIT_1S_532US | \
				 self.__INA219_CONFIG_MODE_SANDBVOLT_CONTINUOUS
		
		bb = [(config >> 8) & 0xFF, config & 0xFF]
		self.bus.write_i2c_block_data(self.i2cAddress, self.__INA219_REG_CONFIG, bb)

	def getBusVoltage_mV(self):
		try:
			result= self.bus.read_i2c_block_data(self.i2cAddress,self.__INA219_REG_BUSVOLTAGE,2)
			#print "getBusVoltage_mV", result 
			if (result[0] >> 7 == 1):
				testint = (result[0]*256 + result[1])
				othernew = self.twosToInt(testint, 16)
				return float(othernew>>3) *self.ina219_busMultiplier 
			else:
				return float(  ((result[0] << 8) | (result[1]) ) >>3) *self.ina219_busMultiplier 
		except	Exception, e:
			U.toLog(-1, u"in Line '%s' has error='%s'" % (sys.exc_traceback.tb_lineno, e))
			return ""
		
	def getShuntVoltage_mV(self):
		try:
			result = self.bus.read_i2c_block_data(self.i2cAddress,self.__INA219_REG_SHUNTVOLTAGE,2)
			#print "getShuntVoltage_mV", result 
			if (result[0] >> 7 == 1):
				testint = (result[0]*256 + result[1])
				othernew = self.twosToInt(testint, 16)
				return float(othernew) * self.ina219_ShuntVoltageMultiplier
			else:
				return (float((result[0] << 8) | (result[1])) * self.ina219_ShuntVoltageMultiplier)
		except	Exception, e:
			U.toLog(-1, u"in Line '%s' has error='%s'" % (sys.exc_traceback.tb_lineno, e))
			return ""

	def getCurrent_mA(self):
		try:
			result = self.bus.read_i2c_block_data(self.i2cAddress,self.__INA219_REG_CURRENT,2)
			#print "getCurrent_mA", result 
			if (result[0] >> 7 == 1):
				testint = (result[0]*256 + result[1])
				othernew = self.twosToInt(testint, 16)
				return float(othernew )* self.ina219_currentMultiplier_mA
			else:
				return float((result[0] << 8) | (result[1])) *self.ina219_currentMultiplier_mA
		except	Exception, e:
			U.toLog(-1, u"in Line '%s' has error='%s'" % (sys.exc_traceback.tb_lineno, e))
			return ""

	def getPower_mW(self):
		try:
			result = self.bus.read_i2c_block_data(self.i2cAddress,self.__INA219_REG_POWER,2)
			#print "getPower_mW", result 
			if (result[0] >> 7 == 1):
				testint = (result[0]*256 + result[1])
				othernew = self.twosToInt(testint, 16)
				return float(othernew )* self.ina219_powerMutiplier_mW
			else:
				return float((result[0] << 8) | (result[1]) )* self.ina219_powerMutiplier_mW
		except	Exception, e:
			U.toLog(-1, u"in Line '%s' has error='%s'" % (sys.exc_traceback.tb_lineno, e))
			return ""
 # ===========================================================================
# read params
# ===========================================================================

#################################		 
def readParams():
	global sensorList, sensors, logDir, sensor,	 sensorRefreshSecs
	global rawOld
	global deltaX, INAsensor, minSendDelta
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
		if "debugRPI"			in inp:	 G.debug=			  int(inp["debugRPI"]["debugRPISENSOR"])
		
 
		if sensor not in sensors:
			U.toLog(-1, G.program+" is not in parameters = not enabled, stopping "+G.program+".py" )
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
				deltaX[devId] = 0.1

			try:
				if "minSendDelta" in sensors[sensor][devId]: 
					minSendDelta= float(sensors[sensor][devId]["minSendDelta"])/100.
			except:
				minSendDelta = 5.


			try:
				if "minSendDelta" in sensors[sensor][devId]: 
					minSendDelta= float(sensors[sensor][devId]["minSendDelta"])/100.
			except:
				minSendDelta = 5.


			try:
				shuntResistor = 0.1
				if "shuntResistor" in sensors[sensor][devId]: 
					shuntResistor= float(sensors[sensor][devId]["shuntResistor"])
			except:
				shuntResistor = 0.1

				
			if devId not in INAsensor:
				U.toLog(-1,"==== Start "+G.program+" ===== @ i2c= " +unicode(i2cAddress)+";	  shuntResistor= "+ unicode(shuntResistor))
				i2cAdd = U.muxTCA9548A(sensors[sensor][devId])
				INAsensor[devId] = INA219(i2cAddress=i2cAdd, shuntResistor=shuntResistor)
				U.muxTCA9548Areset()
				
		deldevID={}		   
		for devId in INAsensor:
			if devId not in sensors[sensor]:
				deldevID[devId]=1
		for dd in  deldevID:
			del INAsensor[dd]
		if len(INAsensor) ==0: 
			####exit()
			pass

	except	Exception, e:
		U.toLog(-1, u"in Line '%s' has error='%s'" % (sys.exc_traceback.tb_lineno, e))



#################################
def getValues(devId):
	global sensor, sensors,	 INAsensor, badSensor
	global actionDistanceOld, actionShortDistance, actionShortDistanceLimit, actionMediumDistance, actionMediumDistanceLimit, actionLongDistance, actionLongDistanceLimit

	i2cAdd = U.muxTCA9548A(sensors[sensor][devId])
	for ii in range(2):
		try:
			ShuntVoltage = INAsensor[devId].getShuntVoltage_V()
			BusVoltage	 = INAsensor[devId].getBusVoltage_mV()
			Current		 = INAsensor[devId].getCurrent_mA()
			Power		 = INAsensor[devId].getPower_mW()
			#print "SV:",ShuntVoltage, "   BV:",BusVoltage, "  C:",Current, "  P:",Power
			data = {"ShuntVoltage":("%7.1f"%ShuntVoltage).strip(), "BusVoltage":("%7d"%BusVoltage).strip(), "Power":("%7d"%Power).strip(), "Current":("%7.1f"%Current).strip()}
			badSensor = 0
			U.muxTCA9548Areset()
			return data
		except	Exception, e:
			if badSensor >2 and badSensor < 5: 
				U.toLog(-1, u"in Line '%s' has error='%s'" % (sys.exc_traceback.tb_lineno, e))
				U.toLog(-1, u"Current>>" + unicode(Current)+"<<")
			badSensor+=1
	if badSensor >3: 
		U.muxTCA9548Areset()
		return "badSensor"
	U.muxTCA9548Areset()
	return ""		 






############################################
global rawOld
global sensor, sensors, badSensor
global deltaX, INAsensor, minSendDelta
global oldRaw, lastRead

oldRaw						=""
lastRead					= 0

minSendDelta				= 5.
G.debug						= 5
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
loopSleep					= 0.5
rawOld						= ""
INAsensor					={}
deltaX				  = {}
myPID		= str(os.getpid())
U.killOldPgm(myPID,G.program+".py")# kill old instances of myself if they are still running


if U.getIPNumber() > 0:
	time.sleep(10)
	exit()

readParams()

time.sleep(1)

lastRead = time.time()

U.echoLastAlive(G.program)




lastCurrent			= {}
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
				if devId not in lastCurrent: lastCurrent[devId] =-500.
				values = getValues(devId)
				if values == "": continue
				data["sensors"] = {sensor:{}}
				data["sensors"][sensor] = {devId:{}}
				if values =="badSensor":
					sensorWasBad = True
					data["sensors"][sensor][devId]["Current"]="badSensor"
					if badSensor < 5: 
						U.toLog(-1," bad sensor")
						U.sendURL(data)
					lastCurrent[devId] =-100.
					continue
				elif values["Current"] !="" :
					if sensorWasBad: # sensor was bad, back up again, need to do a restart to set config 
						U.restartMyself(reason=" back from bad sensor, need to restart to get sensors reset",doPrint="False")
					
					data["sensors"][sensor][devId] = values
					current = float(values["Current"])
					delta	= current-lastCurrent[devId]
					deltaN	= abs(delta) / max (0.5,(current+lastCurrent[devId])/2.)
				else:
					continue
				
				if ( ( deltaN > deltaX[devId]						   ) or 
					 (	tt - abs(G.sendToIndigoSecs) > G.lastAliveSend	) or  
					 ( quick										   )   ) and  \
				   ( ( tt - G.lastAliveSend > minSendDelta			   )   ):
						U.sendURL(data)
						lastCurrent[devId]	= current

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
		U.toLog(-1, u"in Line '%s' has error='%s'" % (sys.exc_traceback.tb_lineno, e))
		time.sleep(5.)
sys.exit(0)
