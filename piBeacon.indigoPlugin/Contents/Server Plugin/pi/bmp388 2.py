#! /usr/bin/env python
# -*- coding: utf-8 -*-
####################

import sys, os, time, json, datetime,subprocess,copy
import smbus
import math
import time


sys.path.append(os.getcwd())
import	piBeaconUtils	as U
import	piBeaconGlobals as G
G.program = "bmp388"



# define BMP388 Device I2C address
I2C_ADD_BMP388_AD0_LOW = 0x76
I2C_ADD_BMP388_AD0_HIGH = 0x77
I2C_ADD_BMP388 = I2C_ADD_BMP388_AD0_HIGH
BMP388_REG_ADD_WIA = 0x00
BMP388_REG_VAL_WIA = 0x50
BMP388_REG_ADD_ERR = 0x02
BMP388_REG_VAL_FATAL_ERR = 0x01
BMP388_REG_VAL_CMD_ERR = 0x02
BMP388_REG_VAL_CONF_ERR = 0x04
BMP388_REG_ADD_STATUS = 0x03
BMP388_REG_VAL_CMD_RDY = 0x10
BMP388_REG_VAL_DRDY_PRESS = 0x20
BMP388_REG_VAL_DRDY_TEMP = 0x40
BMP388_REG_ADD_CMD = 0x7E
BMP388_REG_VAL_EXTMODE_EN = 0x34
BMP388_REG_VAL_FIFI_FLUSH = 0xB0
BMP388_REG_VAL_SOFT_RESET = 0xB6
BMP388_REG_ADD_PWR_CTRL = 0x1B
BMP388_REG_VAL_PRESS_EN = 0x01
BMP388_REG_VAL_TEMP_EN = 0x02
BMP388_REG_VAL_NORMAL_MODE = 0x30
BMP388_REG_ADD_PRESS_XLSB = 0x04
BMP388_REG_ADD_PRESS_LSB = 0x05
BMP388_REG_ADD_PRESS_MSB = 0x06
BMP388_REG_ADD_TEMP_XLSB = 0x07
BMP388_REG_ADD_TEMP_LSB = 0x08
BMP388_REG_ADD_TEMP_MSB = 0x09
BMP388_REG_ADD_T1_LSB = 0x31
BMP388_REG_ADD_T1_MSB = 0x32
BMP388_REG_ADD_T2_LSB = 0x33
BMP388_REG_ADD_T2_MSB = 0x34
BMP388_REG_ADD_T3 = 0x35
BMP388_REG_ADD_P1_LSB = 0x36
BMP388_REG_ADD_P1_MSB = 0x37
BMP388_REG_ADD_P2_LSB = 0x38
BMP388_REG_ADD_P2_MSB = 0x39
BMP388_REG_ADD_P3 = 0x3A
BMP388_REG_ADD_P4 = 0x3B
BMP388_REG_ADD_P5_LSB = 0x3C
BMP388_REG_ADD_P5_MSB = 0x3D
BMP388_REG_ADD_P6_LSB = 0x3E
BMP388_REG_ADD_P6_MSB = 0x3F
BMP388_REG_ADD_P7 = 0x40
BMP388_REG_ADD_P8 = 0x41
BMP388_REG_ADD_P9_LSB = 0x42
BMP388_REG_ADD_P9_MSB = 0x43
BMP388_REG_ADD_P10 = 0x44
BMP388_REG_ADD_P11 = 0x45

class BMP388(object):
	"""docstring for BMP388"""
	def __init__(self, i2c_addr=I2C_ADD_BMP388):
		self._address = i2c_addr
		self._bus = smbus.SMBus(0x01)
		# Load calibration values.
		if self._read_byte(BMP388_REG_ADD_WIA) == BMP388_REG_VAL_WIA:
			U.logger.log(10,"Pressure sersor BMP388 detected")
		u8RegData = self._read_byte(BMP388_REG_ADD_STATUS)
		if u8RegData & BMP388_REG_VAL_CMD_RDY:
			self._write_byte(BMP388_REG_ADD_CMD,
			BMP388_REG_VAL_SOFT_RESET)
			time.sleep(0.01)
		else:
			U.logger.log(20,"Pressure sersor NULL")
			self._write_byte(BMP388_REG_ADD_PWR_CTRL, BMP388_REG_VAL_PRESS_EN | BMP388_REG_VAL_TEMP_EN | BMP388_REG_VAL_NORMAL_MODE)
		self._load_calibration()

	def _read_byte(self, cmd):
		return self._bus.read_byte_data(self._address, cmd)

	def _read_s8(self, cmd):
		result = self._read_byte(cmd)
		if result > 128:
			result -= 256
		return result

	def _read_u16(self, cmd):
		LSB = self._bus.read_byte_data(self._address, cmd)
		MSB = self._bus.read_byte_data(self._address, cmd + 0x01)
		return (MSB << 0x08) + LSB

	def _read_s16(self, cmd):
		result = self._read_u16(cmd)
		if result > 32767:
			result -= 65536
		return result

	def _write_byte(self, cmd, val):
		self._bus.write_byte_data(self._address, cmd, val)

	def _load_calibration(self):
		self.T1 = self._read_u16(BMP388_REG_ADD_T1_LSB)
		self.T2 = self._read_u16(BMP388_REG_ADD_T2_LSB)
		self.T3 = self._read_s8(BMP388_REG_ADD_T3)
		self.P1 = self._read_s16(BMP388_REG_ADD_P1_LSB)
		self.P2 = self._read_s16(BMP388_REG_ADD_P2_LSB)
		self.P3 = self._read_s8(BMP388_REG_ADD_P3)
		self.P4 = self._read_s8(BMP388_REG_ADD_P4)
		self.P5 = self._read_u16(BMP388_REG_ADD_P5_LSB)
		self.P6 = self._read_u16(BMP388_REG_ADD_P6_LSB)
		self.P7 = self._read_s8(BMP388_REG_ADD_P7)
		self.P8 = self._read_s8(BMP388_REG_ADD_P8)
		self.P9 = self._read_s16(BMP388_REG_ADD_P9_LSB)
		self.P10 = self._read_s8(BMP388_REG_ADD_P10)
		self.P11 = self._read_s8(BMP388_REG_ADD_P11)
		self.P11 = self._read_s8(BMP388_REG_ADD_P11)

	def compensate_temperature(self, adc_T):
		partial_data1 = adc_T - 256 * self.T1
		partial_data2 = self.T2 * partial_data1
		partial_data3 = partial_data1 * partial_data1
		partial_data4 = partial_data3 * self.T3
		partial_data5 = partial_data2 * 262144 + partial_data4
		partial_data6 = partial_data5 / 4294967296
		self.T_fine = partial_data6
		comp_temp = partial_data6 * 25 / 16384
		return comp_temp

	def compensate_pressure(self, adc_P):
		partial_data1 = self.T_fine * self.T_fine
		partial_data2 = partial_data1 / 0x40
		partial_data3 = partial_data2 * self.T_fine / 256
		partial_data4 = self.P8 * partial_data3 / 0x20
		partial_data5 = self.P7 * partial_data1 * 0x10
		partial_data6 = self.P6 * self.T_fine * 4194304
		offset = self.P5 * 140737488355328 + partial_data4 \
		+ partial_data5 + partial_data6
		partial_data2 = self.P4 * partial_data3 / 0x20
		partial_data4 = self.P3 * partial_data1 * 0x04
		partial_data5 = (self.P2 - 16384) * self.T_fine * 2097152
		sensitivity = (self.P1 - 16384) * 70368744177664 \
		+ partial_data2 + partial_data4 + partial_data5
		partial_data1 = sensitivity / 16777216 * adc_P
		partial_data2 = self.P10 * self.T_fine
		partial_data3 = partial_data2 + 65536 * self.P9
		partial_data4 = partial_data3 * adc_P / 8192
		partial_data5 = partial_data4 * adc_P / 512
		partial_data6 = adc_P * adc_P
		partial_data2 = self.P11 * partial_data6 / 65536
		partial_data3 = partial_data2 * adc_P / 128
		partial_data4 = offset / 0x04 + partial_data1 + partial_data5 \
		+ partial_data3
		comp_press = partial_data4 * 25 / 1099511627776
		return comp_press

	def get_temperature_and_pressure(self):
		"""Returns pressure in Pa as double. Output value of "6386.2"equals 96386.2 Pa = 963.862 hPa."""
		xlsb 		= self._read_byte(BMP388_REG_ADD_TEMP_XLSB)
		lsb    		= self._read_byte(BMP388_REG_ADD_TEMP_LSB)
		msb   		= self._read_byte(BMP388_REG_ADD_TEMP_MSB)
		adc_T 		= (msb << 0x10) + (lsb << 0x08) + xlsb
		temperature = self.compensate_temperature(adc_T)
		xlsb  		= self._read_byte(BMP388_REG_ADD_PRESS_XLSB)
		lsb   		= self._read_byte(BMP388_REG_ADD_PRESS_LSB)
		msb   		= self._read_byte(BMP388_REG_ADD_PRESS_MSB)
		adc_P 		= (msb << 0x10) + (lsb << 0x08) + xlsb
		pressure 	= self.compensate_pressure(adc_P)
		return (temperature/100., pressure)


# ===========================================================================
# read params
# ===========================================================================

###############################
def readParams():
	global sensorList, sensors, logDir, sensor, sensorRefreshSecs
	global rawOld
	global deltaX, minSendDelta
	global oldRaw, lastRead
	global lastMeasurement, sendToIndigoSecs
	try:



		inp,inpRaw,lastRead2 = U.doRead(lastTimeStamp=lastRead)
		if inp == "": return
		if lastRead2 == lastRead: return
		lastRead   = lastRead2
		if inpRaw == oldRaw: return
		oldRaw	   = inpRaw
		
		externalSensor = False
		sensorList = []
		sensorsOld = copy.copy(sensors)

	
		U.getGlobalParams(inp)
		  
		if "sensorList"			in inp:	 sensorList=			 (inp["sensorList"])
		if "sensors"			in inp:	 sensors =				 (inp["sensors"])
		
 
		if sensor not in sensors:
			U.logger.log(30, "{} is not in parameters = not enabled, stopping {}.py".format(G.program,G.program) )
			exit()
			

		U.logger.log(10, "{} reading new parameter file".format(G.program) )

		deltaX={}
		restart = False
		sendToIndigoSecs = G.sendToIndigoSecs	
		for devId in sensors[sensor]:
			try:
				if "sendToIndigoSecs" in sensors[sensor][devId]:
					sendToIndigoSecs = float(sensors[sensor][devId]["sendToIndigoSecs"])
			except:
				sendToIndigoSecs = G.sendToIndigoSecs	  

			try:
				if "sensorRefreshSecs" in sensors[sensor][devId]:
					sensorRefreshSecs = float(sensors[sensor][devId]["sensorRefreshSecs"])
			except:
				sensorRefreshSecs = 5	  

		
			old = U.getI2cAddress(sensors[sensor][devId], default ="")
			try:
				if "i2cAddress" in sensors[sensor][devId]:
					i2cAddress = float(sensors[sensor][devId]["i2cAddress"])
			except:
				i2cAddress = 119	   
			if old != i2cAddress:  restart = True 

			try:
				if devId not in deltaX: deltaX[devId]  = 0.1
				if "deltaX" in sensors[sensor][devId]: 
					deltaX[devId]= float(sensors[sensor][devId]["deltaX"])/100.
			except:
				deltaX[devId] = 0.1

			try:
				if "minSendDelta" in sensors[sensor][devId]: 
					minSendDelta= float(sensors[sensor][devId]["minSendDelta"])
			except:
				minSendDelta = 5.

				
			if devId not in BMP388SENSOR or  restart:
				U.logger.log(20," new parameters read: i2cAddress:{}; minSendDelta:{};  deltaX:{}; sensorRefreshSecs:{}".format(i2cAddress, minSendDelta, deltaX[devId], sensorRefreshSecs) )
				startSensor(devId)
				if BMP388SENSOR[devId] == "":
					return
				
		deldevID={}		   
		for devId in BMP388SENSOR:
			if devId not in sensors[sensor]:
				deldevID[devId] = 1
		for dd in  deldevID:
			del BMP388SENSOR[dd]
		if len(BMP388SENSOR) == 0: 
			####exit()
			pass

	except	Exception, e:
		U.logger.log(30, u"in Line {} has error={}".format(sys.exc_traceback.tb_lineno, e))
		U.logger.log(30, "{}".format(sensors[sensor]))
		



#################################
def startSensor(devId):
	global sensors, sensor
	global BMP388SENSOR

	i2cAdd = U.muxTCA9548A(sensors[sensor][devId]) # switch mux on if requested and use the i2c address of the mix if enabled
	
	try:
		BMP388SENSOR[devId]  = BMP388(i2c_addr=i2cAdd)
	except:
		try:
			time.sleep(1)
			BMP388SENSOR[devId]  = BMP388(i2c_addr=i2cAdd)
		except	Exception, e:
			U.logger.log(30, u"in Line {} has error={}".format(sys.exc_traceback.tb_lineno, e))
			BMP388SENSOR[devId] = ""
			U.muxTCA9548Areset()
			return
	U.muxTCA9548Areset()



#################################
def getValues(devId):
	global sensor, sensors,	 BMP388SENSOR, badSensor
	global gasBurnIn, gasBaseLine, lastMeasurement, sendToIndigoSecs

	try:
		if BMP388SENSOR[devId] == "": 
			badSensor += 1
			return "badSensor"

		temp   		 = 0
		press  		 = 0
		alt	   		 = 0
		i2cAdd = U.muxTCA9548A(sensors[sensor][devId]) # switch mux on if requested and use the i2c address of the mix if enabled

		temp,press = BMP388SENSOR[devId].get_temperature_and_pressure()
		temp  +=  float(sensors[sensor][devId]["offsetTemp"]) 
		press +=  float(sensors[sensor][devId]["offsetPress"]) 
		#print temp,press
		badSensor = 0
		data = {"temp":	 round(temp,1), 
				"press": round(press,1)
				}
		return data
	except	Exception, e:
		U.logger.log(30, u"in Line {} has error={}".format(sys.exc_traceback.tb_lineno, e))
	badSensor += 1
	if badSensor > 3: return "badSensor"
	return ""





############################################
global rawOld
global sensor, sensors, badSensor
global deltaX, BMP388SENSOR, minSendDelta
global oldRaw, lastRead

sendToIndigoSecs			= 80
lastMeasurement				= time.time()
oldRaw						= ""
lastRead					= 0
minSendDelta				= 5.
loopCount					= 0
sensorRefreshSecs			= -1
NSleep						= 100
sensorList					= []
sensors						= {}
sensor						= G.program
quick						= False
display						= "0"
output						= {}
badSensor					= 0
sensorActive				= False
rawOld						= ""
BMP388SENSOR				= {}
deltaX				  		= {}
myPID		= str(os.getpid())
U.setLogging()
U.killOldPgm(myPID,G.program+".py")# kill old instances of myself if they are still running


if U.getIPNumber() > 0:
	time.sleep(10)
	exit()

readParams()

time.sleep(1)

lastRead = time.time()

U.echoLastAlive(G.program)




lastValues0			= {"temp":0,"hum":0}
lastValues			= {}
lastValues2			= {}
lastData			= {}
lastSend			= 0
lastDisplay			= 0
startTime			= time.time()
G.lastAliveSend		= time.time() -1000

lastMeasurement 	= time.time()

sensorWasBad 		= False
while True:
	try:
		tt = time.time()
		sendData = False
		data ={}
		if sensor in sensors:
			data = {"sensors": {sensor:{}}}
			for devId in sensors[sensor]:
				if devId not in lastValues: 
					lastValues[devId]  =copy.copy(lastValues0)
					lastValues2[devId] =copy.copy(lastValues0)
				values = getValues(devId)
				if values == "": 
					continue

				data["sensors"][sensor][devId]={}
				if values =="badSensor":
					sensorWasBad = True
					data["sensors"][sensor][devId]="badSensor"
					if badSensor < 5: 
						U.logger.log(30," bad sensor")
						U.sendURL(data)
					else:
						U.restartMyself(param="", reason="badsensor",doPrint=True)
					lastValues2[devId] =copy.copy(lastValues0)
					lastValues[devId]  =copy.copy(lastValues0)
					continue
				elif values["temp"] !="" :
					if sensorWasBad: # sensor was bad, back up again, need to do a restart to set config 
						U.restartMyself(reason=" back from bad sensor, need to restart to get sensors reset",doPrint=False)
					
					data["sensors"][sensor][devId] = values
					deltaN =0
					for xx in lastValues0:
						try:
							current = float(values[xx])
							delta	= current-lastValues2[devId][xx]
							delta  /=  max (0.5,(current+lastValues2[devId][xx])/2.)
							deltaN	= max(deltaN,abs(delta) )
							lastValues[devId][xx] = current
						except: pass
				else:
					continue
				if (   ( deltaN > deltaX[devId]	 ) or  (  tt - abs(sendToIndigoSecs) > G.lastAliveSend  ) or	quick	) and  ( tt - G.lastAliveSend > minSendDelta ):
						if time.time() - startTime < 60 and deltaN > 0.5: 
							sendData = False
						else:
							sendData = True
							lastValues2[devId] = copy.copy(lastValues[devId])
		if sendData:
			U.sendURL(data)
		#print " BMP388 to makeDATfile ", data
		U.makeDATfile(G.program, data)

		loopCount +=1

		##U.makeDATfile(G.program, data)
		quick = U.checkNowFile(G.program)				 
		U.echoLastAlive(G.program)

		tt= time.time()
		if tt - lastRead > 5.:	
			readParams()
			lastRead = tt
		time.sleep( max(5, (lastMeasurement+sensorRefreshSecs) - time.time() ) )
		lastMeasurement = time.time()

	except	Exception, e:
		U.logger.log(30, u"in Line {} has error={}".format(sys.exc_traceback.tb_lineno, e))
		time.sleep(5.)
try: 	G.sendThread["run"] = False; time.sleep(1)
except: pass
sys.exit(0)
		
