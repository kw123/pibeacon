#! /usr/bin/env python3
# -*- coding: utf-8 -*-
####################
import time

import sys, os, time, json, datetime,subprocess,copy
import logging
from datetime import timedelta
import board

i2c = board.I2C()  # uses board.SCL and board.SDA

sys.path.append(os.getcwd())
import	piBeaconUtils	as U
import	piBeaconGlobals as G

G.program = "sensirionscd40"


# SPDX-FileCopyrightText: 2017 Scott Shawcroft, written for Adafruit Industries
# SPDX-FileCopyrightText: Copyright (c) 2021 ladyada for Adafruit Industries
#
# SPDX-License-Identifier: MIT
"""
`adafruit_scd4x`
================================================================================

Driver for Sensirion SCD4X CO2 sensor


* Author(s): ladyada

Implementation Notes
--------------------

**Hardware:**

* `Adafruit SCD4X breakout board <https://www.adafruit.com/product/5187>`_

**Software and Dependencies:**

* Adafruit CircuitPython firmware for the supported boards:
  https://github.com/adafruit/circuitpython/releases

* Adafruit's Bus Device library: https://github.com/adafruit/Adafruit_CircuitPython_BusDevice
"""

import struct
from adafruit_bus_device import i2c_device

try:
	from typing import Tuple, Union
	from busio import I2C
except ImportError:
	pass

__version__ = "1.4.0"
__repo__ = "https://github.com/adafruit/Adafruit_CircuitPython_SCD4X.git"

_SCD4X_DEFAULT_ADDR = 0x62
_SCD4X_REINIT = 0x3646
_SCD4X_FACTORYRESET = 0x3632
_SCD4X_FORCEDRECAL = 0x362F
_SCD4X_SELFTEST = 0x3639
_SCD4X_DATAREADY = 0xE4B8
_SCD4X_STOPPERIODICMEASUREMENT = 0x3F86
_SCD4X_STARTPERIODICMEASUREMENT = 0x21B1
_SCD4X_STARTLOWPOWERPERIODICMEASUREMENT = 0x21AC
_SCD4X_READMEASUREMENT = 0xEC05
_SCD4X_SERIALNUMBER = 0x3682
_SCD4X_GETTEMPOFFSET = 0x2318
_SCD4X_SETTEMPOFFSET = 0x241D
_SCD4X_GETALTITUDE = 0x2322
_SCD4X_SETALTITUDE = 0x2427
_SCD4X_SETPRESSURE = 0xE000
_SCD4X_PERSISTSETTINGS = 0x3615
_SCD4X_GETASCE = 0x2313
_SCD4X_SETASCE = 0x2416
_SCD4X_MEASURESINGLESHOT = 0x219D
_SCD4X_MEASURESINGLESHOTRHTONLY = 0x2196


class SCD4X:
	"""
	CircuitPython helper class for using the SCD4X CO2 sensor

	:param ~busio.I2C i2c_bus: The I2C bus the SCD4X is connected to.
	:param int address: The I2C device address for the sensor. Default is :`0x62`

	**Quickstart: Importing and using the SCD4X**

		Here is an example of using the :class:`SCD4X` class.
		First you will need to import the libraries to use the sensor

		.. code-block:: python

			import board
			import adafruit_scd4x

		Once this is done you can define your `board.I2C` object and define your sensor object

		.. code-block:: python

			i2c = board.I2C()   # uses board.SCL and board.SDA
			scd = adafruit_scd4x.SCD4X(i2c)
			scd.start_periodic_measurement()

		Now you have access to the CO2, temperature and humidity using
		the :attr:`CO2`, :attr:`temperature` and :attr:`relative_humidity` attributes

		.. code-block:: python

			if scd.data_ready:
				temperature = scd.temperature
				relative_humidity = scd.relative_humidity
				co2_ppm_level = scd.CO2

	"""

	def __init__(self, i2c_bus: I2C, address: int = _SCD4X_DEFAULT_ADDR) -> None:
		self.i2c_device = i2c_device.I2CDevice(i2c_bus, address)
		self._buffer = bytearray(18)
		self._cmd = bytearray(2)
		self._crc_buffer = bytearray(2)

		# cached readings
		self._temperature = None
		self._relative_humidity = None
		self._co2 = None

		self.stop_periodic_measurement()

	@property
	def CO2(self) -> int:  # pylint:disable=invalid-name
		"""Returns the CO2 concentration in PPM (parts per million)

		.. note::
			Between measurements, the most recent reading will be cached and returned.

		"""
		if self.data_ready:
			self.read_data()
		return self._co2

	@property
	def temperature(self) -> float:
		"""Returns the current temperature in degrees Celsius

		.. note::
			Between measurements, the most recent reading will be cached and returned.

		"""
		if self.data_ready:
			self.read_data()
		return self._temperature

	@property
	def relative_humidity(self) -> float:
		"""Returns the current relative humidity in %rH.

		.. note::
			Between measurements, the most recent reading will be cached and returned.

		"""
		if self.data_ready:
			self.read_data()
		return self._relative_humidity

	def measure_single_shot(self) -> None:
		"""On-demand measurement of CO2 concentration, relative humidity, and
		temperature for SCD41 only"""
		self.send_readCommand(_SCD4X_MEASURESINGLESHOT, cmd_delay=5)

	def measure_single_shot_rht_only(self) -> None:
		"""On-demand measurement of relative humidity and temperature for
		SCD41 only"""
		self.send_readCommand(_SCD4X_MEASURESINGLESHOTRHTONLY, cmd_delay=0.05)

	def reinit(self) -> None:
		"""Reinitializes the sensor by reloading user settings from EEPROM."""
		self.stop_periodic_measurement()
		self.send_readCommand(_SCD4X_REINIT, cmd_delay=0.02)

	def factory_reset(self) -> None:
		"""Resets all configuration settings stored in the EEPROM and erases the
		FRC and ASC algorithm history."""
		self.stop_periodic_measurement()
		self.send_readCommand(_SCD4X_FACTORYRESET, cmd_delay=1.2)

	def set_force_calibration(self, target_co2: int) -> None:
		"""Forces the sensor to recalibrate with a given current CO2"""
		self.stop_periodic_measurement()
		self._send_writecommand_value(_SCD4X_FORCEDRECAL, target_co2)
		time.sleep(0.5)
		self._read_reply(self._buffer, 3)
		correction = struct.unpack_from(">h", self._buffer[0:2])[0]
		if correction == 0xFFFF:
			raise RuntimeError(
				"Forced recalibration failed.\
			Make sure sensor is active for 3 minutes first"
			)

	def get_self_calibration_enabled(self) -> bool:
		"""Enables or disables automatic self calibration (ASC). To work correctly, the sensor must
		be on and active for 7 days after enabling ASC, and exposed to fresh air for at least 1 hour
		per day. Consult the manufacturer's documentation for more information.

		.. note::
			This value will NOT be saved and will be reset on boot unless
			saved with persist_settings().

		"""
		self.send_readCommand(_SCD4X_GETASCE, cmd_delay=0.001)
		self._read_reply(self._buffer, 3)
		return self._buffer[1] == 1

	def set_self_calibration_enabled(self, enabled: bool) -> None:
		self._send_writecommand_value(_SCD4X_SETASCE, enabled)

	def self_test(self) -> None:
		"""Performs a self test, takes up to 10 seconds"""
		self.stop_periodic_measurement()
		self.send_readCommand(_SCD4X_SELFTEST, cmd_delay=10)
		self._read_reply(self._buffer, 3)
		if (self._buffer[0] != 0) or (self._buffer[1] != 0):
			raise RuntimeError("Self test failed")

	def read_data(self) -> Tuple[int, float, int]:
		"""Reads the temp/hum/co2 from the sensor and caches it"""
		self.send_readCommand(_SCD4X_READMEASUREMENT, cmd_delay=0.001)
		self._read_reply(self._buffer, 9)
		self._co2 = (self._buffer[0] << 8) | self._buffer[1]

		temp = (self._buffer[3] << 8) | self._buffer[4]
		self._temperature = -45 + 175 * (temp / 2**16)

		humi = (self._buffer[6] << 8) | self._buffer[7]
		self._relative_humidity = int(100 * (humi / 2**16))

		return self._co2, self._temperature, self._relative_humidity 

	@property
	def data_ready(self) -> bool:
		"""Check the sensor to see if new data is available"""
		self.send_readCommand(_SCD4X_DATAREADY, cmd_delay=0.001)
		self._read_reply(self._buffer, 3)
		return not ((self._buffer[0] & 0x07 == 0) and (self._buffer[1] == 0))


	def get_serial_number(self) -> Tuple[int, int, int, int, int, int]:
		"""Request a 6-tuple containing the unique serial number for this sensor"""
		self.send_readCommand(_SCD4X_SERIALNUMBER, cmd_delay=0.001)
		self._read_reply(self._buffer, 9)
		return (
			self._buffer[0],
			self._buffer[1],
			self._buffer[3],
			self._buffer[4],
			self._buffer[6],
			self._buffer[7],
		)

	def stop_periodic_measurement(self) -> None:
		"""Stop measurement mode"""
		self.send_readCommand(_SCD4X_STOPPERIODICMEASUREMENT, cmd_delay=0.5)

	def start_periodic_measurement(self) -> None:
		"""Put sensor into working mode, about 5s per measurement

		.. note::
			Only the following commands will work once in working mode:

			* :attr:`CO2 <adafruit_scd4x.SCD4X.CO2>`
			* :attr:`temperature <adafruit_scd4x.SCD4X.temperature>`
			* :attr:`relative_humidity <adafruit_scd4x.SCD4X.relative_humidity>`
			* :meth:`data_ready() <adafruit_scd4x.SCD4x.data_ready>`
			* :meth:`reinit() <adafruit_scd4x.SCD4X.reinit>`
			* :meth:`factory_reset() <adafruit_scd4x.SCD4X.factory_reset>`
			* :meth:`force_calibration() <adafruit_scd4x.SCD4X.force_calibration>`
			* :meth:`self_test() <adafruit_scd4x.SCD4X.self_test>`
			* :meth:`set_ambient_pressure() <adafruit_scd4x.SCD4X.set_ambient_pressure>`

		"""
		self.send_readCommand(_SCD4X_STARTPERIODICMEASUREMENT)

	def start_low_periodic_measurement(self) -> None:
		"""Put sensor into low power working mode, about 30s per measurement. See
		:meth:`start_periodic_measurement() <adafruit_scd4x.SCD4X.start_perodic_measurement>`
		for more details.
		"""
		self.send_readCommand(_SCD4X_STARTLOWPOWERPERIODICMEASUREMENT)

	def persist_settings(self) -> None:
		"""Save temperature offset, altitude offset, and selfcal enable settings to EEPROM"""
		self.send_readCommand(_SCD4X_PERSISTSETTINGS, cmd_delay=0.8)

	def set_ambient_pressure(self, ambient_pressure: int) -> None:
		"""Set the ambient pressure in hPa at any time to adjust CO2 calculations"""
		if ambient_pressure < 0 or ambient_pressure > 65535:
			raise AttributeError("`ambient_pressure` must be from 0~65535 hPascals")
		self._send_writecommand_value(_SCD4X_SETPRESSURE, ambient_pressure)

	def get_temperature_offset(self) -> float:
		"""Specifies the offset to be added to the reported measurements to account for a bias in
		the measured signal. Value is in degrees Celsius with a resolution of 0.01 degrees and a
		maximum value of 374 C

		.. note::
			This value will NOT be saved and will be reset on boot unless saved with
			persist_settings().

		"""
		self.send_readCommand(_SCD4X_GETTEMPOFFSET, cmd_delay=0.001)
		self._read_reply(self._buffer, 3)
		temp = (self._buffer[0] << 8) | self._buffer[1]
		return 175.0 * temp / 2**16

	def set_temperature_offset(self, offset: Union[int, float]) -> None:
		if offset > 374:
			raise AttributeError(
				"Offset value must be less than or equal to 374 degrees Celsius"
			)
		temp = int(offset * 2**16 / 175)
		self._send_writecommand_value(_SCD4X_SETTEMPOFFSET, temp)

	def get_altitude(self) -> int:
		"""Specifies the altitude at the measurement location in meters above sea level. Setting
		this value adjusts the CO2 measurement calculations to account for the air pressure's effect
		on readings.

		.. note::
			This value will NOT be saved and will be reset on boot unless saved with
			persist_settings().
		"""
		self.send_readCommand(_SCD4X_GETALTITUDE, cmd_delay=0.001)
		self._read_reply(self._buffer, 3)
		return (self._buffer[0] << 8) | self._buffer[1]

	def set_altitude(self, height: int) -> None:
		if height > 65535:
			raise AttributeError("Height must be less than or equal to 65535 meters")
		self._send_writecommand_value(_SCD4X_SETALTITUDE, height)

	def _check_buffer_crc(self, buf: bytearray) -> bool:
		for i in range(0, len(buf), 3):
			self._crc_buffer[0] = buf[i]
			self._crc_buffer[1] = buf[i + 1]
			if self._crc8(self._crc_buffer) != buf[i + 2]:
				raise RuntimeError("CRC check failed while reading data")
		return True

	def send_readCommand(self, cmd: int, cmd_delay: float = 0) -> None:
		self._cmd[0] = (cmd >> 8) & 0xFF
		self._cmd[1] = cmd & 0xFF

		try:
			with self.i2c_device as i2c:
				i2c.write(self._cmd, end=2)
		except OSError as err:
			raise RuntimeError(
				"Could not communicate via I2C, some commands/settings "
				"unavailable while in working mode"
			) from err
		time.sleep(cmd_delay)

	def _send_writecommand_value(self, cmd, value, cmd_delay=0):
		self._buffer[0] = (cmd >> 8) & 0xFF
		self._buffer[1] = cmd & 0xFF
		self._crc_buffer[0] = self._buffer[2] = (value >> 8) & 0xFF
		self._crc_buffer[1] = self._buffer[3] = value & 0xFF
		self._buffer[4] = self._crc8(self._crc_buffer)
		with self.i2c_device as i2c:
			i2c.write(self._buffer, end=5)
		time.sleep(cmd_delay)

	def _read_reply(self, buff, num):
		with self.i2c_device as i2c:
			i2c.readinto(buff, end=num)
		self._check_buffer_crc(self._buffer[0:num])

	@staticmethod
	def _crc8(buffer: bytearray) -> int:
		crc = 0xFF
		for byte in buffer:
			crc ^= byte
			for _ in range(8):
				if crc & 0x80:
					crc = (crc << 1) ^ 0x31
				else:
					crc = crc << 1
		return crc & 0xFF  # return the bottom 8 bits


###############################
###############################
class SENSORclass():
	def __init__(self,  fastSlow="fast"):
		i2c_addr=0x62
		self._i2c_addr = i2c_addr

		try:
			self.forceCalibration = 0
			self.thisSensor = SCD4X(i2c)
			time.sleep(0.1)

		except Exception as e:
			U.logger.log(30,"", exc_info=True)
			try: del self.thisSensor 
			except: pass
		U.logger.log(20,"return  ")
		return 

	def getData(self): 
		try:
			for ii in range(3):
				if self.thisSensor.data_ready:
					return  self.thisSensor.read_data()
				else:
					time.sleep(2)
			return "notready", 0, ""
		except Exception as e:
			U.logger.log(20,"getData ", exc_info=True)
			time.sleep(5)
		return "","",""



	def get_auto_self_calibration_active(self):
		return self.thisSensor.get_self_calibration_enabled()

	def get_AltitudeCompensation(self):
		return self.thisSensor.get_altitude()

	def get_Force_self_calibration(self):
		return self.forceCalibration

	def get_TemperatureOffset(self):
		return self.thisSensor.get_temperature_offset()

	def get_serialNumber(self):
		return self.thisSensor.get_serial_number()


	def stop_measurements(self):
		self.thisSensor.stop_periodic_measurement()
		return 

	def start_measurements(self):
		self.thisSensor.start_periodic_measurement()
		return 

	def start_30sec_measurements(self,meter):
		self.start_low_periodic_measurement()
		return 

	def set_AltitudeCompensation(self, meter):
		self.thisSensor.set_altitude(meter)
		return

	def start_periodic_measurement(self):
		self.thisSensor.start_periodic_measurement()
		return


	def start_low_periodic_measurement(self):
		self.thisSensor.start_low_periodic_measurement()
		return



	def set_auto_self_calibration_active(self, onOff):
		if onOff : value = 1
		else: value = 0
		self.thisSensor.set_self_calibration_enabled = onOff
		return 

	def set_Force_self_calibration(self, pOffset):
		self.forceCalibration = pOffset
		self.thisSensor.set_force_calibration(pOffset)
		return 

	def setTemperatureOffset(self, toffset):
		self.thisSensor.set_temperature_offset(toffset)
		return 

	def soft_reset(self):
		self.thisSensor.reinit()

	def set_Reset(self):
		self.thisSensor.factory_reset()
		return 


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
			U.logger.log(30, "{} is not in parameters = not enabled, stopping {}.py".format(G.program,G.program) )
			exit()
			

		U.logger.log(10,"{} reading new parameters".format(G.program) )

		if sensor not in sensorsOld:
			sensorsOld[sensor] = {}

		deltaX={}
		restart = False
		sendToIndigoSecs = G.sendToIndigoSecs	
		for devId in sensors[sensor]:
			if devId not in sensorsOld[sensor]:
				sensorsOld[sensor][devId] = {}

			try:
				if devId not in deltaX: deltaX[devId]  = 2
				if "deltaX" in sensors[sensor][devId]: 
					deltaX[devId]= float(sensors[sensor][devId]["deltaX"])/100.
			except:
				deltaX[devId] = 2

			delSens = False


			if sensors[sensor][devId].get("altitudeCompensation","")  		!= sensorsOld[sensor][devId].get("altitudeCompensation",""):
				delSens = True

			if sensors[sensor][devId].get("autoCalibration","1")  			!= sensorsOld[sensor][devId].get("autoCalibration","1"):
				delSens = True

			if sensors[sensor][devId].get("sensorTemperatureOffset","")		!= sensorsOld[sensor][devId].get("sensorTemperatureOffset",""):
				delSens = True

			if sensors[sensor][devId].get("fastSlowRead","fast")			!= sensorsOld[sensor][devId].get("fastSlowRead","fast"):
				delSens = True

			if "altitudeCompensation"		not in sensors[sensor][devId]:	sensors[sensor][devId]["altitudeCompensation"] 		= ""
			if "autoCalibration" 			not in sensors[sensor][devId]:	sensors[sensor][devId]["autoCalibration"] 			= "1"
			if "sensorTemperatureOffset" 	not in sensors[sensor][devId]:	sensors[sensor][devId]["sensorTemperatureOffset"] 	= ""
			if "fastSlowRead" 				not in sensors[sensor][devId]:	sensors[sensor][devId]["fastSlowRead"] 				= "fast"

			if delSens:
				if devId in SENSOR: del SENSOR[devId]

			try:
				if "minSendDelta" in sensors[sensor][devId]: 
					minSendDelta = float(sensors[sensor][devId]["minSendDelta"])
			except:
				minSendDelta = 5.

				
			if devId not in SENSOR or  restart:
				U.logger.log(20," new parameters read:  minSendDelta:{};  deltaX:{}; sensorRefreshSecs:{}".format( minSendDelta, deltaX[devId], sensorRefreshSecs) )
				startSensor(devId)
				if SENSOR[devId] == "":
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
		U.logger.log(30,"", exc_info=True)
		U.logger.log(30, "{}".format(sensors[sensor]))
		


#################################
def startSensor(devId, CO2Target="", reset=False):
	global sensors,sensor
	global startTime
	global SENSOR, i2c_bus
	global serialNumber, sensorTemperatureOffset, autoCalibration, sensorCO2Target, altitudeCompensation
	startTime =time.time()

	
	if devId  in SENSOR:
		if reset:
			U.logger.log(20," soft resetting sensor")
			self.thisSensor.stop_periodic_measurement()
			SENSOR[devId].thisSensor.soft_reset()
			del SENSOR[devId]
		if not reset and CO2Target != "": 
			self.thisSensor.stop_periodic_measurement()
			SENSOR[devId].set_Force_self_calibration(CO2Target)
			sensorCO2Target[devId]			= SENSOR[devId].thisSensor.get_Force_self_calibration()


	if devId not  in SENSOR:
		try:
			autoCalibration[devId]			= True
			SENSOR[devId]					= SENSORclass( )
			if SENSOR[devId]				== "": return 
			if True:

				serialNumber[devId]	 = ""
				try:
					serialNumber[devId]				= "{}".format(SENSOR[devId].get_serialNumber()).replace("(","").replace(")","").replace(" ","")
				except: pass

				if CO2Target != "": 
					U.logger.log(20," setting co2 calib. to:{}".format(CO2Target))
					if CO2Target != 400:
						sensors[sensor][devId]["autoCalibration"] = "0"
					SENSOR[devId].set_Force_self_calibration(CO2Target)

				if sensors[sensor][devId]["altitudeCompensation"] != "": 
					SENSOR[devId].set_AltitudeCompensation(int(sensors[sensor][devId]["altitudeCompensation"]))

				if sensors[sensor][devId]["autoCalibration"] != "": 
					SENSOR[devId].set_auto_self_calibration_active( sensors[sensor][devId]["autoCalibration"] == "1" )

				if sensors[sensor][devId]["sensorTemperatureOffset"] != "": 
					SENSOR[devId].setTemperatureOffset(int(sensors[sensor][devId]["sensorTemperatureOffset"]) )
					time.sleep(1)

				AutocalibWas					= SENSOR[devId].get_auto_self_calibration_active()
				altitudeCompensation[devId]		= SENSOR[devId].get_AltitudeCompensation()
				sensorCO2Target[devId]			= SENSOR[devId].get_Force_self_calibration()
				sensorTemperatureOffset[devId]	= SENSOR[devId].get_TemperatureOffset()
				U.logger.log(20," serialNumber: {}, auto-calibration was set to: {:}, temperature offset was:{}, CO2 target:{}, altitudeCompensation:{}".format(serialNumber[devId], AutocalibWas, sensorTemperatureOffset[devId], sensorCO2Target[devId], altitudeCompensation[devId]) )

				autoCalibration[devId]			= SENSOR[devId].get_auto_self_calibration_active()
				sensorTemperatureOffset[devId]	= SENSOR[devId].get_TemperatureOffset()

			fastSlow = sensors[sensor][devId].get("fastSlowRead","fast") 
			if fastSlow == "slow":
				U.logger.log(20,"set slow ")
				SENSOR[devId].start_low_periodic_measurement()
			else:
				U.logger.log(20,"set fast ")
				SENSOR[devId].start_periodic_measurement()

			time.sleep(2)


		except Exception as e:
			U.logger.log(30,"", exc_info=True)
			SENSOR[devId] = ""
			return
		time.sleep(4)
	U.muxTCA9548Areset()



#################################
def getValues(devId):
	global sensor, sensors,	 SENSOR, badsensorCountCO2
	global startTime, sendToIndigoSecs, sensorMode
	global serialNumber, sensorTemperatureOffset, autoCalibration, sensorCO2Target, altitudeCompensation
	global badSensor

	
	try:
		if devId not in SENSOR:
			startSensor(devId) 
		if SENSOR[devId] == "": 
			return "badSensor"

		CO2, temp, hum = 	SENSOR[devId].getData()

		if CO2  == "notReady":
			return 0, 0, 0

		temp = round(temp,1)
		#U.logger.log(20,"CO2:{}, temp:{}, hum:{}".format(CO2,temp, hum ))
		if type(temp) != float: 
			if badsensorCountCO2[devId]  > 5: return "badSensor"
			return ""

		#U.logger.log(20, u"CO2:{}, temp:{}, hum:{}".format(CO2, temp, hum))
		if "offsetTemp" in sensors[sensor][devId]: temp += float(sensors[sensor][devId]["offsetTemp"])
		if "offsetHum"  in sensors[sensor][devId]: hum  += float(sensors[sensor][devId]["offsetHum"])
		if "offsetCO2"  in sensors[sensor][devId]: CO2  += float(sensors[sensor][devId]["offsetCO2"])

		try:
			data = {"temp":	round(temp,1), "CO2": int(CO2), "hum": int(hum), "serialNumber":serialNumber[devId], "autoCalibration": autoCalibration[devId], 
					"sensorTemperatureOffset": sensorTemperatureOffset[devId],"sensorCO2Target":sensorCO2Target[devId], "altitudeCompensation":altitudeCompensation[devId],
					 "fastSlowRead":sensors[sensor][devId].get("fastSlowRead","fast")} 
			badsensorCountCO2[devId]  = 0
			return data
		except:
			if badsensorCountCO2[devId] > 5: return  "badSensor"
	except Exception as e:
		U.logger.log(30,"end of getValues", exc_info=True)
	if badsensorCountCO2[devId]  > 5: return "badSensor"
	return ""





############################################
def execSensor():
	global sensor, sensors, sensorList, badsensorCountCO2
	global deltaX, SENSOR, minSendDelta, sensorMode
	global oldRaw, lastRead
	global startTime, sendToIndigoSecs, sensorRefreshSecs, lastMeasurement
	global serialNumber
	global serialNumber, sensorTemperatureOffset, autoCalibration, sensorCO2Target, altitudeCompensation
	global badSensor

	badSensor					= 0
	serialNumber				= {}
	sensorTemperatureOffset		= {}
	autoCalibration				= {}
	sensorCO2Target				= {}
	altitudeCompensation		= {}
	sensorMode					= {}
	sendToIndigoSecs			= 20
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
	badsensorCountCO2	= {}
	notReadyCountCO2	= {}

	sensorWasBad 		= False

	while True:
		try:
			tt = time.time()
			sendData = False
			data ={}
			if sensor in sensors:
				data = {"sensors": {sensor:{}}}
				for devId in sensors[sensor]:
					if devId not in badsensorCountCO2: badsensorCountCO2[devId] = 0
					if devId not in notReadyCountCO2: notReadyCountCO2[devId] = 0
					CO2Target = U.checkNewCalibration(G.program)
					if CO2Target:
						try:	del SENSOR[devId]
						except:	pass
						U.logger.log(20," CO2Target:{}".format(CO2Target))

						if type(CO2Target) == type({}):
							CO2Target["value"] = max(400, int(CO2Target["value"]))
							startSensor(devId, CO2Target=CO2Target["value"]) # set co2 to lowest value
						else:	
							startSensor(devId, CO2Target=440) # set co2 to lowest value

					if U.checkResetFile(G.program):
						U.logger.log(20," resetting sensor")
						startSensor(devId, CO2Target=430, reset=True) # 


					if devId not in lastValues: 
						lastValues[devId]  = copy.copy(lastValues0)
						lastValues2[devId] = copy.copy(lastValues0)

					values = getValues(devId)
					#U.logger.log(20," values returned:{}".format(values))


					if values in ["badSensor",""]:
						badsensorCountCO2[devId]  +=1
						data["sensors"][sensor][devId] = "badSensor"
						if badsensorCountCO2[devId] == 4: 
							U.logger.log(20,"bad sensor count  limit reached")
							U.sendURL(data)
						else:
							if badsensorCountCO2[devId] == 10:
								U.restartMyself(param="", reason="badsensor",doPrint=True,python3=True)
						lastValues2[devId] = copy.copy(lastValues0)
						lastValues[devId]  = copy.copy(lastValues0)
						continue

					if values in ["notReady"]:
						notReadyCountCO2[devId]  +=1
						if notReadyCountCO2[devId]  == 10:
							data["sensors"][sensor][devId] = "badSensor"
							U.logger.log(20,"notReadyCountCO2 bad sensor count  limit reached")
							U.sendURL(data)
						self.sleep(5)
						if notReadyCountCO2[devId] == 10:
							U.restartMyself(param="", reason="notReadyCountCO2",doPrint=True,python3=True)
						continue

					if values["CO2"] < 380: 
						badsensorCountCO2[devId] +=1
						U.logger.log(20," badsensorCountCO2:{}, co2:{}".format(badsensorCountCO2[devId] , values["CO2"] ))
						if badsensorCountCO2[devId]  > 12:
							U.restartMyself(param="", reason="co2 value to low",doPrint=True,python3=True)

						elif badsensorCountCO2[devId]  > 6:
							sensorCO2Target[devId] += 30	
							startSensor(devId, CO2Target=sensorCO2Target[devId], reset=True) # 
							continue

						elif badsensorCountCO2[devId]  == 7:
							pass
						else:
							continue

					data["sensors"][sensor][devId] = {}
					badsensorCountCO2[devId] = 0
					data["sensors"][sensor][devId] = values
					deltaN = 0
					for xx in lastValues0:
						try:
							current = float(values[xx])
							delta	= current-lastValues2[devId][xx]
							delta  /=  max (0.5,(current+lastValues2[devId][xx])/2.)
							deltaN	= max(deltaN,abs(delta) )
							lastValues[devId][xx] = current
						except: pass

					#U.logger.log(20," checks: :{}, {}, {}, {}".format(deltaN > deltaX[devId]	,  tt - abs(sendToIndigoSecs) > G.lastAliveSend , quick, tt - G.lastAliveSend > minSendDelta ))

					if (   ( deltaN > deltaX[devId]	 ) or  (  tt - abs(sendToIndigoSecs) > G.lastAliveSend  ) or quick ) and  ( tt - G.lastAliveSend > minSendDelta ):
						sendData = True
						lastValues2[devId] = copy.copy(lastValues[devId])
			##print (data)
			if sendData:
				#U.logger.log(20," sending:{}".format(data))
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

		except Exception as e:
			U.logger.log(30,"", exc_info=True)
			time.sleep(5.)


G.pythonVersion = int(sys.version.split()[0].split(".")[0])
# output: , use the first number only
#3.7.3 (default, Apr  3 2019, 05:39:12) 
#[GCC 8.2.0]

execSensor()
try: 	G.sendThread["run"] = False; time.sleep(1)
except: pass
sys.exit(0)
