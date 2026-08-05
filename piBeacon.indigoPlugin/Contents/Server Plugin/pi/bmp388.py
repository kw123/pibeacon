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


import time
import sys

from math import pow


## copied from https://github.com/DFRobot/DFRobot_BMP388/blob/master/raspbarry/example/I2CReadTemperature/I2CReadTemperature.py
## with some simplification ie i2c setup
class bmp388():
	def __init__(self,i2cAdd = 119):
		"""Initializes the BMP388 driver: opens SMBus 1 at the given I2C address, zeroes temperature/pressure calibration coefficients, verifies the chip ID (0x50, exiting on mismatch), then loads calibration data and writes the sensor configuration.

		Inputs:
		    i2cAdd (int): I2C address of the BMP388 sensor (default 119)
		Outputs:
		    None: opens the I2C bus and configures the sensor, or logs on failure
		"""
		try:
			self._addr = i2cAdd
			self.i2c = smbus.SMBus(1)
 
			self.op_mode = 0
			self.par_t1 = 0
			self.par_t2 = 0
			self.par_t3 = 0
			self.par_p1 = 0
			self.par_p2 = 0
			self.par_p3 = 0
			self.par_p4 = 0
			self.par_p5 = 0
			self.par_p6 = 0
			self.par_p7 = 0
			self.par_p8 = 0
			self.par_p9 = 0
			self.par_p10 = 0
			self.par_p11 = 0
			chip_id = self.bmp3_get_regs(0x00, 1)[0]
			if (chip_id != 0x50):
				U.logger.log(20, "chip errror")
				sys.exit()
				return

			self.get_calib_data()
			self.set_config()
		except Exception as e:
			U.logger.log(20,"", exc_info=True)
  
  
	def get_calib_data(self):
		"""Reads the 21 raw calibration registers from the BMP388 starting at register 0x31 and parses them into the driver's calibration coefficient attributes.

		Inputs:
		    None.
		Outputs:
		    None: reads calibration registers and populates calibration attributes
		"""
		calib = self.bmp3_get_regs(0x31,21) 
		self.parse_calib_data(calib)

	def uint8_int(self,num):
		"""Converts an unsigned 8-bit value into a signed integer by subtracting 256 when the value exceeds 127.

		Inputs:
		    num (int): unsigned 8-bit value to convert
		Outputs:
		    int: signed interpretation of the byte
		"""
		if(num>127):
			num = num - 256
		return num

	def parse_calib_data(self,calib):
		"""Decodes the BMP388's raw calibration byte array into floating-point compensation coefficients (par_t1-t3 and par_p1-p11) by combining bytes, applying sign conversion, and scaling by fixed divisors, storing each on the instance.

		Inputs:
		    calib (list): Raw calibration register bytes (at least 21 ints) read from the sensor
		Outputs:
		    None: Stores computed par_t* and par_p* calibration coefficients on the instance
		"""
		temp_var = 0.00390625
		self.par_t1 = ((calib[1]<<8)|calib[0])/temp_var
	
		temp_var = 1073741824.0
		self.par_t2 = ((calib[3]<<8)|calib[2])/temp_var
	
		temp_var = 281474976710656.0
		calibTemp = self.uint8_int(calib[4])
		self.par_t3 = (calibTemp)/temp_var
	
		temp_var = 1048576.0
		calibTempA = self.uint8_int(calib[6])
		calibTempB = self.uint8_int(calib[5])
		self.par_p1 = ((calibTempA|calibTempB)-16384)/temp_var
	
		temp_var = 536870912.0
		calibTempA = self.uint8_int(calib[8])
		calibTempB = self.uint8_int(calib[7])
		self.par_p2 = (((calibTempA<<8)|calibTempB)-16384)/temp_var
	
		temp_var = 4294967296.0
		calibTemp = self.uint8_int(calib[9])
		self.par_p3 = calibTemp/temp_var
	
		temp_var = 137438953472.0
		calibTemp = self.uint8_int(calib[10])
		self.par_p4 = calibTemp/temp_var
	
		temp_var = 0.125
		self.par_p5 = ((calib[12]<<8)|calib[11])/temp_var
	
		temp_var = 64.0
		self.par_p6 = ((calib[14]<<8)|calib[13])/temp_var
	
		temp_var = 256.0
		calibTemp = self.uint8_int(calib[15])
		self.par_p7 = calibTemp/temp_var
	
		temp_var = 32768.0
		calibTemp = self.uint8_int(calib[16])
		self.par_p8 = calibTemp/temp_var
	
		temp_var = 281474976710656.0
		self.par_p9 = ((calib[18]<<8)|calib[17])/temp_var
	
		temp_var = 281474976710656.0
		calibTemp = self.uint8_int(calib[19])
		self.par_p10 = (calibTemp)/temp_var
	
		temp_var = 36893488147419103232.0
		calibTemp = self.uint8_int(calib[20])
		self.par_p11 = (calibTemp)/temp_var 

	def set_config(self):
		"""Configures the sensor by enabling the selected pressure/temperature settings, then sets the operating mode to normal (0x03) and writes it to the power-control register.

		Inputs:
		    None.
		Outputs:
		    None: Applies sensor settings and power mode to the device over I2C
		"""
		settings_sel = 2|4|16|32|128
		self.bmp3_set_sensor_settings(settings_sel) 
		self.op_mode = 0x03
		self.write_power_mode()
	
	def bmp3_set_sensor_settings(self,settings_sel):
		#set_pwr_ctrl_settings
		"""Reads the power-control register (0x1b), conditionally enables the pressure and temperature measurement bits according to the settings selection bitmask, and writes the updated value back.

		Inputs:
		    settings_sel (int): Bitmask selecting which sensor settings (e.g. pressure/temp enable) to apply
		Outputs:
		    None: Writes updated power-control register to the device
		"""
		reg_data = self.bmp3_get_regs(0x1b,1)[0]
		if(settings_sel & 2):
			reg_data = (reg_data&~(0x01))|(0x01&0x01)
		if(settings_sel & 4):
			reg_data = (reg_data&~(0x02))|((0x01<<0x01)&0x02)
		data = [reg_data]
		self.bmp3_set_regs(0x1b,data)
	
	def write_power_mode(self):
		"""Reads the power-control register (0x1b), inserts the configured operating mode into bits 4-5, and writes the modified byte back to the sensor.

		Inputs:
		    None.
		Outputs:
		    None: Writes the operating mode into the device's power-control register
		"""
		op_mode_reg_val = self.bmp3_get_regs(0x1b,1)[0]
		op_mode_reg_val = (op_mode_reg_val&~(0x30))|((self.op_mode<<0x04)&0x30)
		data = [op_mode_reg_val]
		self.bmp3_set_regs(0x1b,data)
	

	def readData(self):
		"""Reads six raw data registers starting at 0x04, assembles 24-bit uncompensated pressure and temperature values, compensates them using the calibration coefficients, and returns the rounded temperature and pressure.

		Inputs:
		    None.
		Outputs:
		    tuple: Rounded (temperature, pressure) compensated readings
		"""
		rslt 	= self.bmp3_get_regs(0x04,6)
		#parse_sensor_data
		xlsb 	= rslt[0]
		lsb 	= rslt[1] << 8
		msb 	= rslt[2] << 16
		uncomp_pressure = msb|lsb|xlsb
		xlsb 	= rslt[3]
		lsb 	= rslt[4] << 8
		msb 	= rslt[5] << 16
		uncomp_temperature = msb|lsb|xlsb
		t = self.compensate_temperature(uncomp_temperature)
		p = self.compensate_pressure(uncomp_pressure,t)
		return  round(t,2), round(p,2)

	
	def readTemperature(self):
		"""Returns the compensated temperature reading by requesting sensor data with the temperature compensation flag (2), rounded to two decimals.

		Inputs:
		    None.
		Outputs:
		    float: Compensated temperature rounded to two decimals
		"""
		return round(self.bmp3_get_sensor_data(2),2)
	
	def readPressure(self):
		"""Returns the compensated pressure reading by requesting sensor data with the pressure compensation flag (1), rounded to two decimals.

		Inputs:
		    None.
		Outputs:
		    float: Compensated pressure rounded to two decimals
		"""
		return round(self.bmp3_get_sensor_data(1),2)

	def bmp3_get_sensor_data(self,sensor_comp):
		"""Reads six raw data registers from 0x04, builds the 24-bit uncompensated pressure and temperature values, and returns the compensated value(s) selected by the compensation bitmask.

		Inputs:
		    sensor_comp (int): Bitmask selecting which compensated value (pressure and/or temperature) to compute
		Outputs:
		    float: Compensated pressure or temperature value depending on sensor_comp
		"""
		rslt 	= self.bmp3_get_regs(0x04,6)
		#parse_sensor_data
		xlsb 	= rslt[0]
		lsb 	= rslt[1] << 8
		msb 	= rslt[2] << 16
		uncomp_pressure = msb|lsb|xlsb
		xlsb 	= rslt[3]
		lsb 	= rslt[4] << 8
		msb 	= rslt[5] << 16
		uncomp_temperature = msb|lsb|xlsb
		value = self.compensate_data(sensor_comp,uncomp_pressure,uncomp_temperature)
		return value
  
	def compensate_data(self,sensor_comp,uncomp_pressure,uncomp_temperature):
		"""Applies temperature compensation when the corresponding bit is set, then pressure compensation (using the compensated temperature) when its bit is set, and returns the last computed value.

		Inputs:
		    sensor_comp (int): Bitmask selecting temperature (0x03) and/or pressure (0x01) compensation
		    uncomp_pressure (int): Raw uncompensated pressure value
		    uncomp_temperature (int): Raw uncompensated temperature value
		Outputs:
		    float: Compensated pressure or temperature depending on the selected flags
		"""
		if(sensor_comp & 0x03):
			value = self.compensate_temperature(uncomp_temperature)
		if(sensor_comp & 0x01):
			value = self.compensate_pressure(uncomp_pressure,value)
		return value
	
	def compensate_temperature(self,uncomp_temperature):
		"""Converts a raw uncompensated temperature reading into a compensated temperature using the par_t1, par_t2 and par_t3 calibration coefficients.

		Inputs:
		    uncomp_temperature (int): Raw uncompensated temperature value from the sensor
		Outputs:
		    float: Compensated (linearized) temperature value
		"""
		uncomp_temp = uncomp_temperature
		partial_data1 = (uncomp_temp - self.par_t1)
		partial_data2 = (partial_data1 * self.par_t2)
		comp_temp = partial_data2 + (partial_data1 * partial_data1)*self.par_t3
		return comp_temp
	
	def compensate_pressure(self,uncomp_pressure,t_lin):
		"""Converts a raw uncompensated pressure reading into a compensated pressure using the par_p1-p11 calibration coefficients and the linearized temperature.

		Inputs:
		    uncomp_pressure (int): Raw uncompensated pressure value from the sensor
		    t_lin (float): Linearized (compensated) temperature used in pressure compensation
		Outputs:
		    float: Compensated pressure value
		"""
		partial_data1 = self.par_p6 * t_lin
		partial_data2 = self.par_p7 * pow(t_lin, 2)
		partial_data3 = self.par_p8 * pow(t_lin, 3)
		partial_out1 = self.par_p5 + partial_data1 + partial_data2 + partial_data3

		partial_data1 = self.par_p2 * t_lin
		partial_data2 = self.par_p3 * pow(t_lin, 2)
		partial_data3 = self.par_p4 * pow(t_lin, 3)
		partial_out2 = uncomp_pressure *(self.par_p1-0.000145 + partial_data1 + partial_data2 + partial_data3)

		partial_data1 = pow(uncomp_pressure, 2)
		partial_data2 = self.par_p9 + self.par_p10 * t_lin
		partial_data3 = partial_data1 * partial_data2
		partial_data4 = partial_data3 + pow(uncomp_pressure, 3) * self.par_p11

		comp_press = partial_out1 + partial_out2 + partial_data4

		return comp_press
	
	def readCalibratedAltitude(self,seaLevel):
		"""Reads the current compensated pressure and computes the altitude above the given sea-level reference pressure using the barometric formula, rounded to two decimals.

		Inputs:
		    seaLevel (float): Reference sea-level pressure used for altitude calculation
		Outputs:
		    float: Calibrated altitude in meters rounded to two decimals
		"""
		pressure = self.readPressure()
		return round((1.0 - pow(pressure / seaLevel, 0.190284)) * 287.15 / 0.0065,2)

	def readSeaLevel(self, altitude):
		"""Computes the equivalent sea-level pressure from the current sensor pressure reading and a known altitude using the barometric formula, rounded to two decimals.

		Inputs:
		    altitude (float): Known altitude in meters at the sensor location
		Outputs:
		    float: Sea-level-adjusted pressure rounded to 2 decimals
		"""
		pressure = self.readPressure()
		return round(pressure / pow(1.0 - (altitude / 44330.0), 5.255),2)

	def readAltitude(self):
		"""Reads the current pressure from the sensor and converts it to an altitude estimate (in meters) via the barometric formula, rounded to two decimals.

		Inputs:
		    None.
		Outputs:
		    float: Estimated altitude in meters rounded to 2 decimals
		"""
		pressure = self.readPressure()
		return round((1.0 - pow(pressure / 101325, 0.190284)) * 287.15 / 0.0065,2)
	
	def INTEnable(self):
		"""Enables the sensor's interrupt by writing 0x40 to the interrupt control register 0x19 over I2C.

		Inputs:
		    None.
		Outputs:
		    None: Writes interrupt-enable byte to I2C register 0x19
		"""
		reg_data = [0x40]
		reg_addr = 0x19
		self.bmp3_set_regs(reg_addr, reg_data)
	
	def INTDisable(self):
		"""Disables the sensor's interrupt by writing 0x00 to the interrupt control register 0x19 over I2C.

		Inputs:
		    None.
		Outputs:
		    None: Writes interrupt-disable byte to I2C register 0x19
		"""
		reg_data = [0x00]
		reg_addr = 0x19
		self.bmp3_set_regs(reg_addr, reg_data)


	def bmp3_get_regs(self,reg,len):
		"""Reads a block of bytes from the sensor over I2C starting at the given register address and returns them.

		Inputs:
		    reg (int): Starting I2C register address to read from
		    len (int): Number of bytes to read
		Outputs:
		    list: List of bytes read from the I2C block
		"""
		rslt = self.i2c.read_i2c_block_data(self._addr,reg,len)
		return rslt

	def bmp3_set_regs(self,reg,data):
		"""Writes a block of data bytes to the sensor over I2C at the given register address.

		Inputs:
		    reg (int): I2C register address to write to
		    data (list): List of byte values to write
		Outputs:
		    None: Writes data bytes to the I2C bus
		"""
		self.i2c.write_i2c_block_data(self._addr,reg,data)

# ===========================================================================
# read params
# ===========================================================================

###############################
def readParams():
	"""Reads the latest plugin parameter file, updates global sensor configuration (i2c address, refresh intervals, delta thresholds), starts sensors for new or changed devices, and removes sensors no longer present in the configuration.

	Inputs:
	    None.
	Outputs:
	    None: Updates global sensor config and BMP388SENSOR dict; logs and may exit
	"""
	global sensorList, sensors, logDir, sensor, sensorRefreshSecs
	global rawOld
	global deltaX, minSendDelta
	global oldRaw, lastRead
	global lastMeasurement, sendToIndigoSecs
	try:



		inp, inpRaw, lastRead2 = U.doRead(lastTimeStamp=lastRead)
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
			U.logger.log(20, "{} is not in parameters = not enabled, stopping {}.py".format(G.program,G.program) )
			exit()
			

		U.logger.log(10, "{} reading new parameter file".format(G.program) )

		deltaX={}
		restart = False
		sendToIndigoSecs = G.sendToIndigoSecs	
		for devId in sensors[sensor]:

			sendToIndigoSecs = G.sendToIndigoSecs	  
			try:
				if "sendToIndigoSecs" in sensors[sensor][devId]:
					sendToIndigoSecs = float(sensors[sensor][devId]["sendToIndigoSecs"])
			except: pass

			sensorRefreshSecs = 2	  
			try:
				if "sensorRefreshSecs" in sensors[sensor][devId]:
					sensorRefreshSecs = float(sensors[sensor][devId]["sensorRefreshSecs"])
			except: pass

			old = ""
			i2cAddress = 119	   
			if sensor in sensorsOld and devId in sensorsOld[sensor]:
				old = U.getI2cAddress(sensorsOld[sensor][devId], default="")
			try:
				if "i2cAddress" in sensors[sensor][devId]:
					i2cAddress = int(sensors[sensor][devId]["i2cAddress"])
			except: pass
			if old != i2cAddress:  restart = True 

			deltaX[devId] = 0.1
			try:
				if devId not in deltaX: deltaX[devId]  = 0.1
				if "deltaX" in sensors[sensor][devId]: 
					deltaX[devId]= float(sensors[sensor][devId]["deltaX"])/100.
			except: pass

			minSendDelta = 5.
			try:
				if "minSendDelta" in sensors[sensor][devId]: 
					minSendDelta = float(sensors[sensor][devId]["minSendDelta"])
			except: pass

				
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

	except Exception as e:
		U.logger.log(20,"", exc_info=True)
		U.logger.log(20, "{}".format(sensors[sensor]))
		



#################################
def startSensor(devId):
	"""Initializes a BMP388 sensor instance for the given device, switching the TCA9548A I2C mux if configured, retrying once after a delay on failure, and storing the instance (or empty string on failure) in the global BMP388SENSOR dict.

	Inputs:
	    devId (str): Device identifier key for the sensor to start
	Outputs:
	    None: Populates BMP388SENSOR[devId] and resets the I2C mux
	"""
	global sensors, sensor
	global BMP388SENSOR

	i2cAdd = U.muxTCA9548A(sensors[sensor][devId]) # switch mux on if requested and use the i2c address of the mix if enabled
	
	try:
		BMP388SENSOR[devId]  = bmp388(i2cAdd=i2cAdd)
	except:
		try:
			time.sleep(1)
			BMP388SENSOR[devId]  = bmp388(i2cAdd=i2cAdd)
		except Exception as e:
			U.logger.log(20,"", exc_info=True)
			BMP388SENSOR[devId] = ""
			U.muxTCA9548Areset()
			return
	U.muxTCA9548Areset()



#################################
def getValues(devId):
	"""Reads temperature and pressure from the BMP388 sensor for the given device, applies configured offsets, tracks bad-sensor counts, and returns the rounded readings as a dict.

	Inputs:
	    devId (str): Device identifier key for the sensor to read
	Outputs:
	    dict or str: Dict with 'temp' and 'press', or 'badSensor'/'' on error
	"""
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

		temp, press   = BMP388SENSOR[devId].readData()
		temp  +=  float(sensors[sensor][devId]["offsetTemp"]) 
		press +=  float(sensors[sensor][devId]["offsetPress"]) 
		#print temp,press
		badSensor = 0
		data = {"temp":	 round(temp,1), 
				"press": int(press)
				}
		return data
	except Exception as e:
		U.logger.log(20,"", exc_info=True)
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




lastValues0			= {"temp":0,"press":0}
lastValues			= {}
lastValues2			= {}
lastData			= {}
lastSend			= 0
lastDisplay			= 0
startTime			= time.time()
G.lastAliveSend		= time.time() -1000

lastMeasurement 	= time.time() -5

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
						U.logger.log(20," bad sensor")
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

	except Exception as e:
		U.logger.log(20,"", exc_info=True)
		time.sleep(5.)
try: 	G.sendThread["run"] = False; time.sleep(1)
except: pass
sys.exit(0)
		
