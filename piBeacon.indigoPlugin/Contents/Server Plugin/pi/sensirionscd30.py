#! /usr/bin/env python3
# -*- coding: utf-8 -*-
####################
import time

import sys, os, time, json, datetime,subprocess,copy
import logging
import smbus2
import struct
from datetime import timedelta

sys.path.append(os.getcwd())
import	piBeaconUtils	as U
import	piBeaconGlobals as G
G.program = "sensirionscd30"



def interpret_as_float(integer: int):
	return struct.unpack('!f', struct.pack('!I', integer))[0]


class SCD30:
	"""Python I2C driver for the SCD30 CO2 sensor."""

	def __init__(self):
		self._i2c_addr = 0x61
		self._i2c = smbus2.SMBus(1)

	def _pretty_hex(self, data):
		"""Formats an I2C message in an easily readable format.

		Parameters:
			data: either None, int, or a list of ints.

		Returns:
			a string '<none>' or hex-formatted data (singular or list).
		"""
		if data is None:
			return "<none>"
		if type(data) is int:
			data = [data]
		if len(data) == 0:
			return "<none>"

		if len(data) == 1:
			value = "{:02x}".format(data[0])
			if len(value) % 2:
				value = "0" + value
			return "0x" + value
		return "[" + ", ".join("0x{:02x}".format(byte) for byte in data) + "]"

	def _check_word(self, word: int, name: str = "value"):
		"""Checks that a word is a valid two-byte value and throws otherwise.

		Parameters:
			word: integer value to check.
			name (optional): name of the variable to include in the error.
		"""
		if not 0 <= word <= 0xFFFF:
			raise ValueError("{} outside valid two-byte word range: {}".format(name, word))

	def _word_or_none(self, response: list):
		"""Unpacks an I2C response as either a single 2-byte word or None.

		Parameters:
			response: None or a single-value list.

		Returns:
			None or the single value inside 'response'.
		"""
		return next(iter(response or []), None)

	def _crc8(self, word: int):
		"""Computes the CRC-8 checksum as per the SCD30 interface description.

		Parameters:
			word: two-byte integer word value to compute the checksum over.

		Returns:
			single-byte integer CRC-8 checksum.

		Polynomial: x^8 + x^5 + x^4 + 1 (0x31, MSB)
		Initialization: 0xFF

		Algorithm adapted from:
		https://en.wikipedia.org/wiki/Computation_of_cyclic_redundancy_checks

		"""
		self._check_word(word, "word")
		polynomial = 0x31
		rem = 0xFF
		word_bytes = word.to_bytes(2, "big")
		for byte in word_bytes:
			rem ^= byte
			for _ in range(8):
				if rem & 0x80:
					rem = (rem << 1) ^ polynomial
				else:
					rem = rem << 1
				rem &= 0xFF

		return rem

	def _send_command(self, command: int, num_response_words: int = 1,
					  arguments: list = []):
		"""Sends the provided I2C command and reads out the results.

		Parameters:
			command: the two-byte command code, e.g. 0x0010.
			num_response_words: number of two-byte words in the result.
			arguments (optional): list of two-byte arguments to the command.

		Returns:
			list of num_response_words two-byte int values from the sensor.
		"""
		self._check_word(command, "command")
		U.logger.log(10, "Executing command {} with arguments:{}" .format(self._pretty_hex(command), self._pretty_hex(arguments)))

		raw_message = list(command.to_bytes(2, "big"))
		for argument in arguments:
			self._check_word(argument, "argument")
			raw_message.extend(argument.to_bytes(2, "big"))
			raw_message.append(self._crc8(argument))

		U.logger.log(10, "Sending raw I2C data block:{}".format(self._pretty_hex(raw_message)) )

		# self._i2c.write_i2c_block_data(self._i2c_addr, command, arguments)
		write_txn = smbus2.i2c_msg.write(self._i2c_addr, raw_message)
		self._i2c.i2c_rdwr(write_txn)

		# The interface description suggests a >3ms delay between writes and
		# reads for most commands.
		time.sleep(timedelta(milliseconds=5).total_seconds())

		if num_response_words == 0:
			return []

		read_txn = smbus2.i2c_msg.read(self._i2c_addr, num_response_words * 3)
		self._i2c.i2c_rdwr(read_txn)

		# raw_response = self._i2c.read_i2c_block_data(
		#	self._i2c_addr, command, 3 * num_response_words)
		raw_response = list(read_txn)
		logging.debug("Received raw I2C response: " + self._pretty_hex(raw_response))

		if len(raw_response) != 3 * num_response_words:
			U.logger.log(30, "Wrong response length: {) expected:{}".format(len(raw_response),  3 * num_response_words))

		# Data is returned as a sequence of num_response_words 2-byte words
		# (big-endian), each with a CRC-8 checksum:
		# [MSB0, LSB0, CRC0, MSB1, LSB1, CRC1, ...]
		response = []
		for i in range(num_response_words):
			# word_with_crc contains [MSB, LSB, CRC] for the i-th response word
			word_with_crc = raw_response[3 * i: 3 * i + 3]
			word = int.from_bytes(word_with_crc[:2], "big")
			response_crc = word_with_crc[2]
			computed_crc = self._crc8(word)
			if (response_crc != computed_crc):
				U.logger.log(30, "CRC verification for word {} failed: received {} computed {}".format(self._pretty_hex(word), self._pretty_hex(response_crc), self._pretty_hex(computed_crc)) )
				return None
			response.append(word)

		U.logger.log(10, "CRC-verified response: {}".format(self._pretty_hex(response)) )
		return response

	def get_firmware_version(self):
		"""Reads the firmware version from the sensor.

		Returns:
			two-byte integer version number
		"""
		return self._word_or_none(self._send_command(0xD100))

	def get_data_ready(self):
		return self._word_or_none(self._send_command(0x0202))

	def start_periodic_measurement(self, ambient_pressure: int = 0):
		"""Starts periodic measurement of CO2 concentration, humidity and temp.

		Parameters:
			ambient_pressure (optional): external pressure reading in millibars.

		The enable status of periodic measurement is stored in non-volatile
		memory onboard the sensor module and will persist after shutdown.

		ambient_pressure may be set to either 0 to disable ambient pressure
		compensation, or between [700; 1400] mBar.
		"""
		if ambient_pressure and not 700 <= ambient_pressure <= 1400:
			raise ValueError("Ambient pressure must be set to either 0 or in the range [700; 1400] mBar")

		self._send_command(0x0010, num_response_words=0,
						   arguments=[ambient_pressure])

	def stop_periodic_measurement(self):
		"""Stops periodic measurement of CO2 concentration, humidity and temp.

		The enable status of periodic measurement is stored in non-volatile
		memory onboard the sensor module and will persist after shutdown.
		"""
		self._send_command(0x0104, num_response_words=0)

	def get_measurement_interval(self):
		"""Gets the interval used for periodic measurements.

		Returns:
			measurement interval in seconds or None.
		"""
		interval = self._word_or_none(self._send_command(0x4600, 1))

		if interval is None or not 2 <= interval <= 1800:
			U.logger.log(30, "Failed to read measurement interval, received: {}".format(self._pretty_hex(interval)) )

		return interval

	def set_measurement_interval(self, interval=2):
		"""Sets the interval used for periodic measurements.

		Parameters:
			interval: the interval in seconds within the range [2; 1800].

		The interval setting is stored in non-volatile memory and persists
		after power-off.
		"""
		if not 2 <= interval <= 1800:
			raise ValueError("Interval must be in the range [2; 1800] (sec)")

		self._send_command(0x4600, 1, [interval])

	def read_measurement(self):
		"""Reads out a CO2, temperature and humidity measurement.

		Must only be called if a measurement is available for reading, i.e.
		get_data_ready() returned 1.

		Returns:
			tuple of measurement values (CO2 ppm, Temp 'C, RH %) or None.
		"""
		data = self._send_command(0x0300, num_response_words=6)

		if data is None or len(data) != 6:
			U.logger.log(30, "Failed to read measurement, received: ".format( self._pretty_hex(data)) )
			return None

		co2_ppm = interpret_as_float((data[0] << 16) | data[1])
		temp_celsius = interpret_as_float((data[2] << 16) | data[3])
		rh_percent = interpret_as_float((data[4] << 16) | data[5])

		return (co2_ppm, temp_celsius, rh_percent)

	def set_auto_self_calibration(self, active: bool):
		"""(De-)activates the automatic self-calibration feature.

		Parameters:
			active: True to enable, False to disable.

		The setting is persisted in non-volatile memory.
		"""
		arg = 1 if active else 0
		self._send_command(0x5306, num_response_words=0, arguments=[arg])

	def get_auto_self_calibration_active(self):
		"""Gets the automatic self-calibration feature status.

		Returns:
			1 if ASC is active, 0 if inactive, or None upon error.
		"""
		return self._word_or_none(self._send_command(0x5306))

	def get_temperature_offset(self):
		"""Gets the currently active temperature offset.

		The temperature offset is used to compensate for reading bias caused by
		heat generated by nearby electrical components or the SCD30 itself.

		See the documentation of set_temperature_offset for more details on
		calculating the offset value correctly.

		The temperature offset is stored in non-volatile memory and persists
		across shutdowns.

		Returns:
			Temperature offset floating-point value in degrees Celsius.
		"""
		offset_ticks = self._word_or_none(self._send_command(0x5403))
		if offset_ticks is None:
			return None
		return offset_ticks / 100.0

	def set_temperature_offset(self, offset: float):
		"""Sets a new temperature offset.

		The correct temperature offset will vary depending on the installation
		of the sensor as well as its configuration; different measurement
		intervals will result in different power draw, and thus, different
		amounts of electrical heating.

		To compute the offset value for any fixed configuration:
			1. Install and configure the sensor as needed.
			2. Start continuous measurement and let it run for at least 10
			   minutes or until a stable temperature equilibrium is reached.
			3. Get the previous temperature offset value T_offset_old from
			   the SCD30 using get_temperature_offset.
			4. Get a temperature reading T_measured from the SCD30 using
			   read_measurement.
			5. Measure the ambient temperature T_ambient using a *different*
			   sensor, away from the immediate proximity of the SCD30.
			6. Compute the new offset to set as follows:
			   T_offset_new = (T_measured + T_offset_old) - T_ambient

		After setting a new value, allow the sensor readings to stabilize,
		which will happen slowly and gradually.

		For more details, see the documentation on the project page.

		Arguments:
			offset: temperature offset floating-point value in degrees Celsius.
		"""
		offset_ticks = int(offset * 100)
		return self._send_command(0x5403, 0, [offset_ticks])

	def soft_reset(self):
		"""Resets the sensor without the need to disconnect power.

		This restarts the onboard system controller and forces the sensor
		back to its power-up state.
		"""
		self._send_command(0xD304, num_response_words=0)


###############################
###############################
class SENSORclass():
	def __init__(self):

		try:
			self.scd30 = SCD30()
			time.sleep(0.1)
			self.scd30.set_measurement_interval(2)
			self.scd30.start_periodic_measurement()
			time.sleep(2)
		except Exception as e:
			U.logger.log(30, u"in Line {} has error={}".format(sys.exc_info()[-1].tb_lineno, e))
		return 

	def getData(self): 
		try:
			for ii in range (20):
				if self.scd30.get_data_ready():
					CO2, temp, hum = self.scd30.read_measurement()
					return CO2, temp, hum 
				else: 
					time.sleep(0.2)
		except Exception as e:
			U.logger.log(30, u"in Line {} has error={} ".format(sys.exc_info()[-1].tb_lineno, e))

		return "","",""
# ===========================================================================
# read params
# ===========================================================================

###############################
def readParams():
	global sensorList, sensors, logDir, sensor,	 sensorRefreshSecs, displayEnable
	global deltaX, SENSOR, minSendDelta, sensorMode
	global oldRaw, lastRead
	global startTime, lastMeasurement, sendToIndigoSecs
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
			U.logger.log(30, "{} is not in parameters = not enabled, stopping {}.py".format(G.program,G.program) )
			exit()
			

		U.logger.log(10,"{} reading new parameters".format(G.program) )

		deltaX={}
		restart = False
		sendToIndigoSecs = G.sendToIndigoSecs	
		for devId in sensors[sensor]:

			try:
				if devId not in deltaX: deltaX[devId]  = 2
				if "deltaX" in sensors[sensor][devId]: 
					deltaX[devId]= float(sensors[sensor][devId]["deltaX"])/100.
			except:
				deltaX[devId] = 2

			try:
				if "minSendDelta" in sensors[sensor][devId]: 
					minSendDelta= float(sensors[sensor][devId]["minSendDelta"])
			except:
				minSendDelta = 5.

				
			if devId not in SENSOR or  restart:
				U.logger.log(30," new parameters read:  minSendDelta:{};  deltaX:{}; sensorRefreshSecs:{}".format( minSendDelta, deltaX[devId], sensorRefreshSecs) )
				startSensor(devId)
				if SENSOR[devId] =="":
					return
		deldevID={}		   
		for devId in SENSOR:
			if devId not in sensors[sensor]:
				deldevID[devId]=1
		for dd in  deldevID:
			del SENSOR[dd]
		if len(SENSOR) ==0: 
			####exit()
			pass



	except Exception as e:
		U.logger.log(30, u"in Line {} has error={}".format(sys.exc_info()[-1].tb_lineno, e))
		U.logger.log(30, "{}".format(sensors[sensor]))
		


#################################
def startSensor(devId):
	global sensors,sensor
	global startTime
	global SENSOR, i2c_bus
	global deviceVersion
	startTime =time.time()

	
	try:
		ii = SENSOR[devId]
	except:
		try:
			time.sleep(1)
			SENSOR[devId]  = SENSORclass()
			deviceVersion = SENSOR[devId].scd30.get_firmware_version()
			print ( " version: {}".format(deviceVersion) )
		except	Exception as e:
			U.logger.log(30, u"in Line {} has error={}".format(sys.exc_info()[-1].tb_lineno, e))
			SENSOR[devId] = ""
			return
	U.muxTCA9548Areset()



#################################
def getValues(devId):
	global sensor, sensors,	 SENSOR, badSensor
	global startTime, sendToIndigoSecs, sensorMode
	global deviceVersion

	try:
		if SENSOR[devId] == "": 
			badSensor +=1
			return "badSensor"

		CO2, temp, hum = 	SENSOR[devId].getData()
		if "offsetTemp" in sensors[sensor][devId]: temp += float(sensors[sensor][devId]["offsetTemp"])
		if "offsetHum"  in sensors[sensor][devId]: hum  += float(sensors[sensor][devId]["offsetHum"])
		if "offsetCO2"  in sensors[sensor][devId]: CO2  += float(sensors[sensor][devId]["offsetCO2"])
		data = {"temp":	round(temp,1), "CO2": int(CO2), "hum": int(hum), "deviceVersion":deviceVersion} 
		badSensor = 0
		return data
	except	Exception as e:
		U.logger.log(30, u"in Line {} has error={}".format(sys.exc_info()[-1].tb_lineno, e))
	badSensor += 1
	if badSensor > 5: return "badSensor"
	return ""





############################################
def execSensor():
	global sensor, sensors, badSensor, sensorList
	global deltaX, SENSOR, minSendDelta, sensorMode
	global oldRaw, lastRead
	global startTime, sendToIndigoSecs, sensorRefreshSecs, lastMeasurement
	global deviceVersion

	deviceVersion				= ""
	sensorMode					= {}
	sendToIndigoSecs			= 80
	startTime					= time.time()
	lastMeasurement				= time.time()
	oldRaw						= ""
	lastRead					= 0
	minSendDelta				= 5.
	loopCount					= 0
	sensorRefreshSecs			= 9
	sensorList					= []
	sensors						= {}
	sensor						= G.program
	quick						= False
	output						= {}
	badSensor					= 0
	SENSOR						= {}
	deltaX						= {}
	myPID						= str(os.getpid())
	U.setLogging()
	U.killOldPgm(myPID,G.program+".py")# kill old instances of myself if they are still running


	if U.getIPNumber() > 0:
		time.sleep(10)
		exit()

	readParams()

	time.sleep(1)

	lastRead = time.time()

	U.echoLastAlive(G.program)


	lastValues0			= {"moisture":0,"temp":0, "hum":0}
	lastValues			= {}
	lastValues2			= {}
	lastData			= {}
	lastSend			= 0
	G.lastAliveSend		= time.time()

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
					if values == "badSensor":
						sensorWasBad = True
						data["sensors"][sensor][devId]="badSensor"
						if badSensor < 5: 
							U.logger.log(30," bad sensor")
							U.sendURL(data)
						else:
							U.restartMyself(param="", reason="badsensor",doPrint=True,python3=True)
						lastValues2[devId] =copy.copy(lastValues0)
						lastValues[devId]  =copy.copy(lastValues0)
						continue
					elif values["CO2"] !="":
					
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
					if (   ( deltaN > deltaX[devId]	 ) or  (  tt - abs(sendToIndigoSecs) > G.lastAliveSend  ) or quick ) and  ( tt - G.lastAliveSend > minSendDelta ):
						sendData = True
						lastValues2[devId] = copy.copy(lastValues[devId])
			##print (data)
			if sendData:
				U.sendURL(data)
			U.makeDATfile(G.program, data)

			loopCount +=1

			##U.makeDATfile(G.program, data)
			quick = U.checkNowFile(G.program)				 
			U.echoLastAlive(G.program)

			tt= time.time()
			if tt - lastRead > 5.:	
				readParams()
				lastRead = tt
			time.sleep( max(0, (lastMeasurement+sensorRefreshSecs) - time.time() ) )
			lastMeasurement = time.time()

		except	Exception as e:
			U.logger.log(30, u"in Line {} has error={}".format(sys.exc_info()[-1].tb_lineno, e))
			time.sleep(5.)


G.pythonVersion = int(sys.version.split()[0].split(".")[0])
# output: , use the first number only
#3.7.3 (default, Apr  3 2019, 05:39:12) 
#[GCC 8.2.0]

execSensor()
try: 	G.sendThread["run"] = False; time.sleep(1)
except: pass
sys.exit(0)
