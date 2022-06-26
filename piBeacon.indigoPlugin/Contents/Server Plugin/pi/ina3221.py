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
G.program = "ina3221"


# constants

#/*=========================================================================
#	 I2C ADDRESS/BITS
#	 -----------------------------------------------------------------------*/
INA3221_ADDRESS =						  (0x40)	# 1000000 (A0+A1=GND)
INA3221_READ	=						  (0x01)
#/*=========================================================================*/

#/*=========================================================================
#	 CONFIG REGISTER (R/W)
#	 -----------------------------------------------------------------------*/
INA3221_REG_CONFIG			  =			 (0x00)
#	 /*---------------------------------------------------------------------*/
INA3221_CONFIG_RESET		  =			 (0x8000)  # Reset Bit
	
INA3221_CONFIG_ENABLE_CHAN1	  =			 (0x4000)  # Enable Channel 1
INA3221_CONFIG_ENABLE_CHAN2	  =			 (0x2000)  # Enable Channel 2
INA3221_CONFIG_ENABLE_CHAN3	  =			 (0x1000)  # Enable Channel 3

INA3221_CONFIG_AVG2		=				 (0x0800)  # AVG Samples Bit 2 - See table 3 spec
INA3221_CONFIG_AVG1		=				 (0x0400)  # AVG Samples Bit 1 - See table 3 spec
INA3221_CONFIG_AVG0		=				 (0x0200)  # AVG Samples Bit 0 - See table 3 spec

INA3221_CONFIG_VBUS_CT2 =				 (0x0100)  # VBUS bit 2 Conversion time - See table 4 spec
INA3221_CONFIG_VBUS_CT1 =				 (0x0080)  # VBUS bit 1 Conversion time - See table 4 spec
INA3221_CONFIG_VBUS_CT0 =				 (0x0040)  # VBUS bit 0 Conversion time - See table 4 spec

INA3221_CONFIG_VSH_CT2	=				 (0x0020)  # Vshunt bit 2 Conversion time - See table 5 spec
INA3221_CONFIG_VSH_CT1	=				 (0x0010)  # Vshunt bit 1 Conversion time - See table 5 spec
INA3221_CONFIG_VSH_CT0	=				 (0x0008)  # Vshunt bit 0 Conversion time - See table 5 spec

INA3221_CONFIG_MODE_2	=				 (0x0004)  # Operating Mode bit 2 - See table 6 spec
INA3221_CONFIG_MODE_1	=				 (0x0002)  # Operating Mode bit 1 - See table 6 spec
INA3221_CONFIG_MODE_0	=				 (0x0001)  # Operating Mode bit 0 - See table 6 spec

#/*=========================================================================*/

#/*=========================================================================
#	 SHUNT VOLTAGE REGISTER (R)
#	 -----------------------------------------------------------------------*/
INA3221_REG_SHUNTVOLTAGE_1	 =			   (0x01)
#/*=========================================================================*/

#/*=========================================================================
#	 BUS VOLTAGE REGISTER (R)
#	 -----------------------------------------------------------------------*/
INA3221_REG_BUSVOLTAGE_1	 =			   (0x02)
#/*=========================================================================*/

SHUNT_RESISTOR_VALUE		 = (0.1,0.1,0.1)   # default shunt resistor value of 0.1 Ohm




# ===========================================================================
# INA3221 Class
# ===========================================================================

class INA3221():



	###########################
	# INA3221 Code
	###########################
	def __init__(self, twi=1, i2cAddress=INA3221_ADDRESS, shunt_resistor = SHUNT_RESISTOR_VALUE	 ):
		self._bus = smbus.SMBus(twi)

		if i2cAddress =="" or i2cAddress ==0:
			self.i2cAddress = INA3221_ADDRESS 
		else:
			self.i2cAddress = i2cAddress

		self.SHUNT_RESISTOR= SHUNT_RESISTOR_VALUE


		config =	INA3221_CONFIG_ENABLE_CHAN1 |		 \
					INA3221_CONFIG_ENABLE_CHAN2 |	 \
					INA3221_CONFIG_ENABLE_CHAN3 |	 \
					INA3221_CONFIG_AVG1 |		 \
					INA3221_CONFIG_VBUS_CT2 |		 \
					INA3221_CONFIG_VSH_CT2 |		\
					INA3221_CONFIG_MODE_2 |		   \
					INA3221_CONFIG_MODE_1 |		   \
					INA3221_CONFIG_MODE_0

		


		self._write_register_little_endian(INA3221_REG_CONFIG, config)


	def _write(self, register, data):
		#print "addr =0x%x register = 0x%x data = 0x%x " % (self.i2cAddress, register, data)
		self._bus.write_byte_data(self.i2cAddress, register, data)


	def _read(self, data):

		returndata = self._bus.read_byte_data(self.i2cAddress, data)
		#print "addr = 0x%x data = 0x%x %i returndata = 0x%x " % (self.i2cAddress, data, data, returndata)
		return returndata


	def _read_register_little_endian(self, register): 
	
		result = self._bus.read_word_data(self.i2cAddress,register) & 0xFFFF
		lowbyte = (result & 0xFF00)>>8 
		highbyte = (result & 0x00FF) << 8
		switchresult = lowbyte + highbyte 
		#print "Read 16 bit Word addr =0x%x register = 0x%x switchresult = 0x%x " % (self.i2cAddress, register, switchresult)
		return switchresult
   
   
	def _write_register_little_endian(self, register, data): 

		data = data & 0xFFFF
		# reverse configure byte for little endian
		lowbyte = data>>8
		highbyte = (data & 0x00FF)<<8
		switchdata = lowbyte + highbyte
		self._bus.write_word_data(self.i2cAddress, register, switchdata)
		#print "Write  16 bit Word addr =0x%x register = 0x%x data = 0x%x " % (self.i2cAddress, register, data)
	   


	def _getBusVoltage_raw(self, channel):
	#Gets the raw bus voltage (16-bit signed integer, so +-32767)

		value = self._read_register_little_endian(INA3221_REG_BUSVOLTAGE_1+(channel ) *2) &0xfff8
		if value > 32767:
			value -= 65536
		return value

	def _getShuntVoltage_raw(self, channel):
	#Gets the raw shunt voltage (16-bit signed integer, so +-32767)
	
		value = self._read_register_little_endian(INA3221_REG_SHUNTVOLTAGE_1+(channel ) *2)&0xfff8
		if value > 32767:
			value -= 65536
		return value

	# public functions

	def getBusVoltage_V(self, channel):
		# Gets the Bus voltage in volts

		value = self._getBusVoltage_raw(channel)/1000.
		return value 


	def getShuntVoltage_mV(self, channel):
		# Gets the shunt voltage in mV (so +-168.3mV)

		value = self._getShuntVoltage_raw(channel)
		return value * 0.005

	def getCurrent_mA(self, channel):
		#Gets the current value in mA, taking into account the config settings and current LSB
		
		valueDec = self.getShuntVoltage_mV(channel)/ self.SHUNT_RESISTOR[channel]				
		return valueDec

	def getShuntVoltageCurrent(self, channel):
		v = self.getShuntVoltage_mV(channel)			
		a = v / self.SHUNT_RESISTOR[channel]			   
		return v,a

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
				sensorRefreshSecs = 100	   


			i2cAddress = U.getI2cAddress(sensors[sensor][devId], default ="")

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
				shuntResistor =[0.1,0.1,0.1]
				for ii in range(3):
					if "shuntResistor"+str(ii) in sensors[sensor][devId]:
						shuntResistor[ii]= float(sensors[sensor][devId]["shuntResistor"+str(ii+1)])
			except:
				shuntResistor =[0.1,0.1,0.1]


			if devId not in INAsensor:
				U.logger.log(30,"==== Start "+G.program+" ====== @ i2c= " +unicode(i2cAddress)+";	shuntResistor= "+ str(shuntResistor))
				i2cAdd = U.muxTCA9548A(sensors[sensor][devId])
				INAsensor[devId] = INA3221(i2cAddress=i2cAdd,shunt_resistor=shuntResistor)
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

	except	Exception as e:
		U.logger.log(30, u"in Line {} has error={}".format(traceback.extract_tb(sys.exc_info()[2])[-1][1], e))



#################################
def getValues(devId):
	global sensor, sensors,	 INAsensor, badSensor
	global actionDistanceOld, actionShortDistance, actionShortDistanceLimit, actionMediumDistance, actionMediumDistanceLimit, actionLongDistance, actionLongDistanceLimit

	i2cAdd = U.muxTCA9548A(sensors[sensor][devId])
	for ll1 in range(2):
		try:
			data ={"Current1":"","Current2":"","Current3":""}
			for ii in range(3):
				ShuntVoltage,Current = INAsensor[devId].getShuntVoltageCurrent(ii)
				BusVoltage			 = INAsensor[devId].getBusVoltage_V(ii)
				#print ii, "SV:",ShuntVoltage, "   BV:",BusVoltage, "  C:",Current
				data["ShuntVoltage"+str(ii+1)] =("%7.1f"%ShuntVoltage).strip()
				data["BusVoltage"+str(ii+1)]   =("%7.3f"%BusVoltage).strip()
				data["Current"+str(ii+1)]	   =("%7.1f"%Current).strip()
			badSensor = 0
			U.muxTCA9548Areset()
			return data
		except	Exception as e:
			if badSensor >2 and badSensor < 5: 
				U.logger.log(30, u"in Line {} has error={}".format(traceback.extract_tb(sys.exc_info()[2])[-1][1], e))
				U.logger.log(30, u"Current>>" + unicode(Current)+"<<")
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
		tt = time.time()
		data = {"sensors":{}}
		if sensor in sensors:
			for devId in sensors[sensor]:
				if devId not in lastCurrent: lastCurrent[devId] =[-500.,-500,-500]
				values = getValues(devId)
				if values == "": continue
				data["sensors"] = {sensor:{}}
				data["sensors"][sensor] = {devId:{}}
				if values =="badSensor":
					sensorWasBad = True
					data["sensors"][sensor][devId]["Current0"]="badSensor"
					if badSensor < 5: 
						U.logger.log(30," bad sensor")
						U.sendURL(data)
					lastCurrent[devId] =-100.
					continue
				else:
					deltaN = 0
					ok = True
					for ii in range(3):
						if values["Current"+str(ii+1)] =="": 
							ok = False
							break
					if not ok: continue

					if sensorWasBad: # sensor was bad, back up again, need to do a restart to set config 
						U.restartMyself(reason=" back from bad sensor, need to restart to get sensors reset",doPrint=False)
					#print values
					data["sensors"][sensor][devId] = values
					current=[0,0,0]
					for ii in range(3):
						current[ii] = float(values["Current"+str(ii+1)])
						delta	= current[ii]-lastCurrent[devId][ii]
						delta  /=  max (0.5,(current[ii]+lastValues2[devId][ii])/2.)
						deltaN	= max(deltaN, abs(delta) )
				
				if ( ( deltaN > deltaX[devId]						   ) or 
					 (	tt - G.lastAliveSend  > abs(G.sendToIndigoSecs) ) or  
					 ( quick										   )   ) and  \
				   ( ( tt - minSendDelta  > G.lastAliveSend			  )	  ): 
						## print " sending",deltaN ,deltaX[devId],	tt - G.lastAliveSend ,tt - minSendDelta	 , sensorRefreshSecs, G.sendToIndigoSecs
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
		
	except	Exception as e:
		U.logger.log(30, u"in Line {} has error={}".format(traceback.extract_tb(sys.exc_info()[2])[-1][1], e))
		time.sleep(5.)
try: 	G.sendThread["run"] = False; time.sleep(1)
except: pass
sys.exit(0)
