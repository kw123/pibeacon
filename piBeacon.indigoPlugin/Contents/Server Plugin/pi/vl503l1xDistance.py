#!/usr/bin/env python
# -*- coding: utf-8 -*-
# by Karl Wachs
# feb 5 2016
# version 0.9 
##
##  get sensor values and write the to a file in json format for later pickup, 
##  do it in a timed manner not to load the system, is every 1 seconds then 30 senods break
##

import  sys, os, time, json, datetime,subprocess,copy
import math


sys.path.append(os.getcwd())
import  piBeaconUtils	as U
import  piBeaconGlobals as G

G.program = "vl503l1xDistance"
import  displayDistance as DISP

import RPi.GPIO as GPIO

GPIO.setmode(GPIO.BCM)
GPIO.setwarnings(False)


import board
import busio



# SPDX-FileCopyrightText: 2017 Scott Shawcroft, written for Adafruit Industries
# SPDX-FileCopyrightText: Copyright (c) 2021 Carter Nelson for Adafruit Industries
#
# SPDX-License-Identifier: MIT
"""
`adafruit_vl53l1x`
================================================================================
CircuitPython module for interacting with the VL53L1X distance sensor.
* Author(s): Carter Nelson
Implementation Notes
--------------------
**Hardware:**
* Adafruit `VL53L1X Time of Flight Distance Sensor - ~30 to 4000mm
  <https://www.adafruit.com/product/3967>`_
**Software and Dependencies:**
* Adafruit CircuitPython firmware for the supported boards:
  https://github.com/adafruit/circuitpython/releases
* Adafruit's Bus Device library: https://github.com/adafruit/Adafruit_CircuitPython_BusDevice
"""

import struct
from adafruit_bus_device import i2c_device
from micropython import const

# imports__version__ = "0.0.0+auto.0"
__repo__ = "https://github.com/adafruit/Adafruit_CircuitPython_VL53L1X.git"

_VL53L1X_I2C_SLAVE_DEVICE_ADDRESS = const(0x0001)
_VL53L1X_VHV_CONFIG__TIMEOUT_MACROP_LOOP_BOUND = const(0x0008)
_GPIO_HV_MUX__CTRL = const(0x0030)
_GPIO__TIO_HV_STATUS = const(0x0031)
_PHASECAL_CONFIG__TIMEOUT_MACROP = const(0x004B)
_RANGE_CONFIG__TIMEOUT_MACROP_A_HI = const(0x005E)
_RANGE_CONFIG__VCSEL_PERIOD_A = const(0x0060)
_RANGE_CONFIG__TIMEOUT_MACROP_B_HI = const(0x0061)
_RANGE_CONFIG__VCSEL_PERIOD_B = const(0x0063)
_RANGE_CONFIG__VALID_PHASE_HIGH = const(0x0069)
_SD_CONFIG__WOI_SD0 = const(0x0078)
_SD_CONFIG__INITIAL_PHASE_SD0 = const(0x007A)
_SYSTEM__INTERRUPT_CLEAR = const(0x0086)
_SYSTEM__MODE_START = const(0x0087)
_VL53L1X_RESULT__RANGE_STATUS = const(0x0089)
_VL53L1X_RESULT__FINAL_CROSSTALK_CORRECTED_RANGE_MM_SD0 = const(0x0096)
_VL53L1X_IDENTIFICATION__MODEL_ID = const(0x010F)

TB_SHORT_DIST = {
	 # ms: (MACROP_A_HI, MACROP_B_HI)
	 15: (b"\x00\x1D", b"\x00\x27"),
	 20: (b"\x00\x51", b"\x00\x6E"),
	 33: (b"\x00\xD6", b"\x00\x6E"),
	 50: (b"\x01\xAE", b"\x01\xE8"),
	 100: (b"\x02\xE1", b"\x03\x88"),
	 200: (b"\x03\xE1", b"\x04\x96"),
	 500: (b"\x05\x91", b"\x05\xC1"),
}

TB_LONG_DIST = {
	 # ms: (MACROP_A_HI, MACROP_B_HI)
	 20: (b"\x00\x1E", b"\x00\x22"),
	 33: (b"\x00\x60", b"\x00\x6E"),
	 50: (b"\x00\xAD", b"\x00\xC6"),
	 100: (b"\x01\xCC", b"\x01\xEA"),
	 200: (b"\x02\xD9", b"\x02\xF8"),
	 500: (b"\x04\x8F", b"\x04\xA4"),
}


class VL53L1X:
	"""Driver for the VL53L1X distance sensor."""

	def __init__(self, i2c, address=41):
		self.i2c_device = i2c_device.I2CDevice(i2c, address)
		self._i2c = i2c
		model_id, module_type, mask_rev = self.model_info
		if False and  (model_id != 0xEA or module_type != 0xCC or mask_rev != 0x10):
				raise RuntimeError("Wrong sensor ID or type!")
		self.sensor_init()
		self._timing_budget = None
		self.timing_budget = 50

	def sensor_init(self):
		# pylint: disable=line-too-long
		init_seq = bytes(
				[  # value	 addr : description
					 0x00,  # 0x2d : set bit 2 and 5 to 1 for fast plus mode (1MHz I2C), else don't touch
					 0x00,  # 0x2e : bit 0 if I2C pulled up at 1.8V, else set bit 0 to 1 (pull up at AVDD)
					 0x00,  # 0x2f : bit 0 if GPIO pulled up at 1.8V, else set bit 0 to 1 (pull up at AVDD)
					 0x01,  # 0x30 : set bit 4 to 0 for active high interrupt and 1 for active low (bits 3:0 must be 0x1), use SetInterruptPolarity()
					 0x02,  # 0x31 : bit 1 = interrupt depending on the polarity
					 0x00,  # 0x32 : not user-modifiable
					 0x02,  # 0x33 : not user-modifiable
					 0x08,  # 0x34 : not user-modifiable
					 0x00,  # 0x35 : not user-modifiable
					 0x08,  # 0x36 : not user-modifiable
					 0x10,  # 0x37 : not user-modifiable
					 0x01,  # 0x38 : not user-modifiable
					 0x01,  # 0x39 : not user-modifiable
					 0x00,  # 0x3a : not user-modifiable
					 0x00,  # 0x3b : not user-modifiable
					 0x00,  # 0x3c : not user-modifiable
					 0x00,  # 0x3d : not user-modifiable
					 0xFF,  # 0x3e : not user-modifiable
					 0x00,  # 0x3f : not user-modifiable
					 0x0F,  # 0x40 : not user-modifiable
					 0x00,  # 0x41 : not user-modifiable
					 0x00,  # 0x42 : not user-modifiable
					 0x00,  # 0x43 : not user-modifiable
					 0x00,  # 0x44 : not user-modifiable
					 0x00,  # 0x45 : not user-modifiable
					 0x20,  # 0x46 : interrupt configuration 0->level low detection, 1-> level high, 2-> Out of window, 3->In window, 0x20-> New sample ready , TBC
					 0x0B,  # 0x47 : not user-modifiable
					 0x00,  # 0x48 : not user-modifiable
					 0x00,  # 0x49 : not user-modifiable
					 0x02,  # 0x4a : not user-modifiable
					 0x0A,  # 0x4b : not user-modifiable
					 0x21,  # 0x4c : not user-modifiable
					 0x00,  # 0x4d : not user-modifiable
					 0x00,  # 0x4e : not user-modifiable
					 0x05,  # 0x4f : not user-modifiable
					 0x00,  # 0x50 : not user-modifiable
					 0x00,  # 0x51 : not user-modifiable
					 0x00,  # 0x52 : not user-modifiable
					 0x00,  # 0x53 : not user-modifiable
					 0xC8,  # 0x54 : not user-modifiable
					 0x00,  # 0x55 : not user-modifiable
					 0x00,  # 0x56 : not user-modifiable
					 0x38,  # 0x57 : not user-modifiable
					 0xFF,  # 0x58 : not user-modifiable
					 0x01,  # 0x59 : not user-modifiable
					 0x00,  # 0x5a : not user-modifiable
					 0x08,  # 0x5b : not user-modifiable
					 0x00,  # 0x5c : not user-modifiable
					 0x00,  # 0x5d : not user-modifiable
					 0x01,  # 0x5e : not user-modifiable
					 0xCC,  # 0x5f : not user-modifiable
					 0x0F,  # 0x60 : not user-modifiable
					 0x01,  # 0x61 : not user-modifiable
					 0xF1,  # 0x62 : not user-modifiable
					 0x0D,  # 0x63 : not user-modifiable
					 0x01,  # 0x64 : Sigma threshold MSB (mm in 14.2 format for MSB+LSB), default value 90 mm
					 0x68,  # 0x65 : Sigma threshold LSB
					 0x00,  # 0x66 : Min count Rate MSB (MCPS in 9.7 format for MSB+LSB)
					 0x80,  # 0x67 : Min count Rate LSB
					 0x08,  # 0x68 : not user-modifiable
					 0xB8,  # 0x69 : not user-modifiable
					 0x00,  # 0x6a : not user-modifiable
					 0x00,  # 0x6b : not user-modifiable
					 0x00,  # 0x6c : Intermeasurement period MSB, 32 bits register
					 0x00,  # 0x6d : Intermeasurement period
					 0x0F,  # 0x6e : Intermeasurement period
					 0x89,  # 0x6f : Intermeasurement period LSB
					 0x00,  # 0x70 : not user-modifiable
					 0x00,  # 0x71 : not user-modifiable
					 0x00,  # 0x72 : distance threshold high MSB (in mm, MSB+LSB)
					 0x00,  # 0x73 : distance threshold high LSB
					 0x00,  # 0x74 : distance threshold low MSB ( in mm, MSB+LSB)
					 0x00,  # 0x75 : distance threshold low LSB
					 0x00,  # 0x76 : not user-modifiable
					 0x01,  # 0x77 : not user-modifiable
					 0x0F,  # 0x78 : not user-modifiable
					 0x0D,  # 0x79 : not user-modifiable
					 0x0E,  # 0x7a : not user-modifiable
					 0x0E,  # 0x7b : not user-modifiable
					 0x00,  # 0x7c : not user-modifiable
					 0x00,  # 0x7d : not user-modifiable
					 0x02,  # 0x7e : not user-modifiable
					 0xC7,  # 0x7f : ROI center
					 0xFF,  # 0x80 : XY ROI (X=Width, Y=Height)
					 0x9B,  # 0x81 : not user-modifiable
					 0x00,  # 0x82 : not user-modifiable
					 0x00,  # 0x83 : not user-modifiable
					 0x00,  # 0x84 : not user-modifiable
					 0x01,  # 0x85 : not user-modifiable
					 0x00,  # 0x86 : clear interrupt, 0x01=clear
					 0x00,  # 0x87 : ranging, 0x00=stop, 0x40=start
				]
		)
		self._write_register(0x002D, init_seq)
		self.start_ranging()
		while not self.data_ready:
				time.sleep(0.01)
		self.clear_interrupt()
		self.stop_ranging()
		self._write_register(_VL53L1X_VHV_CONFIG__TIMEOUT_MACROP_LOOP_BOUND, b"\x09")
		self._write_register(0x0B, b"\x00")

	@property
	def model_info(self):
		"""A 3 tuple of Model ID, Module Type, and Mask Revision."""
		info = self._read_register(_VL53L1X_IDENTIFICATION__MODEL_ID, 3)
		return (info[0], info[1], info[2])  # Model ID, Module Type, Mask Rev

	@property
	def distance(self):
		"""The distance in units of centimeters."""
		if self._read_register(_VL53L1X_RESULT__RANGE_STATUS)[0] != 0x09:
				return None
		dist = self._read_register(
				_VL53L1X_RESULT__FINAL_CROSSTALK_CORRECTED_RANGE_MM_SD0, 2
		)
		dist = struct.unpack(">H", dist)[0]
		return dist / 10.

	def start_ranging(self):
		"""Starts ranging operation."""
		self._write_register(_SYSTEM__MODE_START, b"\x40")

	def stop_ranging(self):
		"""Stops ranging operation."""
		self._write_register(_SYSTEM__MODE_START, b"\x00")

	def clear_interrupt(self):
		"""Clears new data interrupt."""
		self._write_register(_SYSTEM__INTERRUPT_CLEAR, b"\x01")

	@property
	def data_ready(self):
		"""Returns true if new data is ready, otherwise false."""
		if (
				self._read_register(_GPIO__TIO_HV_STATUS)[0] & 0x01
				== self._interrupt_polarity
		):
				return True
		return False

	@property
	def timing_budget(self):
		"""Ranging duration in milliseconds. Increasing the timing budget
		increases the maximum distance the device can range and improves
		the repeatability error. However, average power consumption augments
		accordingly. ms = 15 (short mode only), 20, 33, 50, 100, 200, 500."""
		return self._timing_budget

	@timing_budget.setter
	def timing_budget(self, val):
		reg_vals = None
		mode = self.distance_mode
		if mode == 1:
				reg_vals = TB_SHORT_DIST
		if mode == 2:
				reg_vals = TB_LONG_DIST
		if reg_vals is None:
				raise RuntimeError("Unknown distance mode.")
		if val not in reg_vals:
				raise ValueError("Invalid timing budget.")
		self._write_register(_RANGE_CONFIG__TIMEOUT_MACROP_A_HI, reg_vals[val][0])
		self._write_register(_RANGE_CONFIG__TIMEOUT_MACROP_B_HI, reg_vals[val][1])
		self._timing_budget = val

	@property
	def _interrupt_polarity(self):
		int_pol = self._read_register(_GPIO_HV_MUX__CTRL)[0] & 0x10
		int_pol = (int_pol >> 4) & 0x01
		return 0 if int_pol else 1

	@property
	def distance_mode(self):
		"""The distance mode. 1=short, 2=long."""
		mode = self._read_register(_PHASECAL_CONFIG__TIMEOUT_MACROP)[0]
		if mode == 0x14:
				return 1  # short distance
		if mode == 0x0A:
				return 2  # long distance
		return None  # unknown

	@distance_mode.setter
	def distance_mode(self, mode):
		if mode == 1:
				# short distance
				self._write_register(_PHASECAL_CONFIG__TIMEOUT_MACROP, b"\x14")
				self._write_register(_RANGE_CONFIG__VCSEL_PERIOD_A, b"\x07")
				self._write_register(_RANGE_CONFIG__VCSEL_PERIOD_B, b"\x05")
				self._write_register(_RANGE_CONFIG__VALID_PHASE_HIGH, b"\x38")
				self._write_register(_SD_CONFIG__WOI_SD0, b"\x07\x05")
				self._write_register(_SD_CONFIG__INITIAL_PHASE_SD0, b"\x06\x06")
		elif mode == 2:
				# long distance
				self._write_register(_PHASECAL_CONFIG__TIMEOUT_MACROP, b"\x0A")
				self._write_register(_RANGE_CONFIG__VCSEL_PERIOD_A, b"\x0F")
				self._write_register(_RANGE_CONFIG__VCSEL_PERIOD_B, b"\x0D")
				self._write_register(_RANGE_CONFIG__VALID_PHASE_HIGH, b"\xB8")
				self._write_register(_SD_CONFIG__WOI_SD0, b"\x0F\x0D")
				self._write_register(_SD_CONFIG__INITIAL_PHASE_SD0, b"\x0E\x0E")
		else:
				raise ValueError("Unsupported mode.{}".format(mode))
		self.timing_budget = self._timing_budget

	def _write_register(self, address, data, length=None):
		if length is None:
				length = len(data)
		with self.i2c_device as i2c:
				i2c.write(struct.pack(">H", address) + data[:length])

	def _read_register(self, address, length=1):
		data = bytearray(length)
		with self.i2c_device as i2c:
				i2c.write(struct.pack(">H", address))
				i2c.readinto(data)
		return data

	def set_address(self, new_address):
		"""
		Set a new I2C address to the instantaited object. This is only called when using
		multiple VL53L0X sensors on the same I2C bus (SDA & SCL pins). See also the
		`example <examples.html#multiple-vl53l1x-on-same-i2c-bus>`_ for proper usage.
		"""
		self._write_register(
				_VL53L1X_I2C_SLAVE_DEVICE_ADDRESS, struct.pack(">B", new_address)
		)
		self.i2c_device = i2c_device.I2CDevice(self._i2c, new_address)

# ===========================================================================
# read params
# ===========================================================================

#################################		
def readParams():
	global sensorList, sensors, logDir, sensor,  sensorRefreshSecs, dynamic, deltaDist, deltaDistAbs,displayEnable
	global output, sensorActive, distanceUnits
	global actionDistanceOld, actionShortDistance, actionShortDistanceLimit, actionMediumDistance, actionMediumDistanceLimit, actionLongDistance, actionLongDistanceLimit
	global oldRaw, lastRead
	global acuracyDistanceMode, acuracyDistanceModeOld, xShutPin, i2cNumber, i2CseqNumber
	global mode, modeOld
	try:

		inp,inpRaw,lastRead2 = U.doRead(lastTimeStamp=lastRead)
		if inp == "": return True
		if lastRead2 == lastRead: return True
		lastRead	= lastRead2
		if inpRaw == oldRaw: return True
		oldRaw	 = inpRaw


		externalSensor = False
		sensorList=[]
		sensorsOld= copy.copy(sensors)
		
		U.getGlobalParams(inp)
		
		if "sensorList"		in inp:  sensorList =		inp["sensorList"]
		if "sensors"		in inp:  sensors =			inp["sensors"]
		if "distanceUnits"	in inp:  distanceUnits =	inp["distanceUnits"]
		
		if "output"			in inp:  output	=			inp["output"]
	
 
		if sensor not in sensors:
			U.logger.log(20, "{} is not in parameters = not enabled, stopping".format(G.program) )
			time.sleep(0.1)
			U.killOldPgm(-1, G.program+".py") # exit() does not seem to work 
			sys.exit(0)
			return False
			
 
		sensorUp = doWeNeedToStartSensor(sensors,sensorsOld,sensor)


		if sensorUp != 0: # something has changed
			if os.path.isfile(G.homeDir+"temp/"+sensor+".dat"):
				os.remove(G.homeDir+"temp/"+sensor+".dat")
				
		deltaDist = {}
		deltaDistAbs = {}
		acuracyDistanceMode = {}
		mode = {}
		xShutPin = {}
		i2cNumber = {}
		i2CseqNumber = 0
		for devId in sensors[sensor]:

			try:
				if "displayEnable" in sensors[sensor][devId]: 
					displayEnable = sensors[sensor][devId]["displayEnable"]
			except:
				display = False	


			try:	deltaDist[devId] = float(sensors[sensor][devId].get("deltaDist",10))/100.
			except: deltaDist[devId] = 0.1

			try:	deltaDistAbs[devId] = float(sensors[sensor][devId].get("deltaDistAbs",10))
			except: deltaDistAbs[devId] = 10.

			try:	distanceUnits = sensors[sensor][devId].get("dUnits","cm")
			except:	distanceUnits = "cm"

			try:	acuracyDistanceMode[devId] = int(sensors[sensor][devId].get("acuracyDistanceMode",50000)) # timing budget
			except:	acuracyDistanceMode[devId] = 50000

			try:	mode[devId] = int(sensors[sensor][devId].get("mode",2))
			except:	mode[devId] = 2

			if "xShutPin" in sensors[sensor][devId] and sensors[sensor][devId]["xShutPin"] not in ["-1",""]:
				xx = int(sensors[sensor][devId].get("xShutPin",26))
				if xx > 0 and xx < 27:
					xShutPin[devId] = xx
					i2CseqNumber += 1


			try:	sensorRefreshSecs = float(sensors[sensor][devId].get("sensorRefreshSecs",1))
			except:	sensorRefreshSecs = 1.

			try:
				if "actionShortDistance" in sensors[sensor][devId]:		actionShortDistance = (sensors[sensor][devId]["actionShortDistance"])
			except:														actionShortDistance = ""

			try:
				if "actionMediumDistance" in sensors[sensor][devId]:	actionMediumDistance = (sensors[sensor][devId]["actionMediumDistance"])
			except:														actionMediumDistance = ""

			try:
				if "actionLongDistance" in sensors[sensor][devId]:		actionLongDistance = (sensors[sensor][devId]["actionLongDistance"])
			except:														actionLongDistance = ""

			try:
				if "actionShortDistanceLimit" in sensors[sensor][devId]:actionShortDistanceLimit = float(sensors[sensor][devId]["actionShortDistanceLimit"])
			except:														actionShortDistanceLimit = -1

			try:
				if "actionLongDistanceLimit" in sensors[sensor][devId]:	actionLongDistanceLimit = float(sensors[sensor][devId]["actionLongDistanceLimit"])
			except:														actionLongDistanceLimit = -1


		if sensorUp == 1:
			startSensor()
				
		if sensorUp == -1:
				U.logger.log(30, "==== stop  ranging =====")
				sys.exit()
				return False

	except  Exception as e:
		U.logger.log(30,"", exc_info=True)
		return True

#################################
def startSensor():
	global mode, modeOld
	global acuracyDistanceMode, acuracyDistanceModeOld, sensCl, xShutPin, i2cNumber, i2c, i2CseqNumber, deltaDist
	try:
		if i2c == "":
			i2c = busio.I2C(board.SCL, board.SDA)

		U.logger.log(20,"starting  i2CseqNumber:{}, xShutPin:{}".format(i2CseqNumber, xShutPin))
		runningI2C = i2CseqNumber
		for devId in deltaDist:
			if devId in xShutPin:
				GPIO.setup(xShutPin[devId], GPIO.OUT)
				U.logger.log(20,"switching off devId:{}, xShutPin:{}".format(devId, xShutPin[devId]))
				GPIO.output(xShutPin[devId], False)
				time.sleep(0.1)
		
		for devId in deltaDist:
			if i2CseqNumber > 0:
				if devId in xShutPin:
					runningI2C -= 1  # STARTING FROM HIGH NUMBER DOWN TO 0X29
					i2cNumber[devId] = runningI2C+0x29
					U.logger.log(20, "==== setting up xshut for devid:{}, xShutPin:{} i2c:0x{:x}".format( devId, xShutPin.get(devId,"off"), runningI2C+0x29))
					GPIO.output(xShutPin[devId], True)
					time.sleep(0.2)
				else:
					runningI2C -= 1
					i2cNumber[devId] = 0x29
			else:
					i2cNumber[devId] = 0x29



			sensCl[devId] = VL53L1X(i2c)

			sensCl[devId].distance_mode = mode[devId] 
			sensCl[devId].timing_budget = acuracyDistanceMode[devId]

			modeOld[devId] = mode[devId]
			acuracyDistanceModeOld[devId] = acuracyDistanceMode[devId]

			if runningI2C >0:
				U.logger.log(20, "==== setting up xshut for devid:{}, xShutPin:{} --> i2c:0x{:x}".format( devId, xShutPin[devId], runningI2C+0x29))
				sensCl[devId].set_address(runningI2C + 0x29) 

			model_id, module_type, mask_rev = sensCl[devId].model_info
			U.logger.log(20, "==== ranging started ==== devId:{}, i2c#:{}.. model:{}, type:{}, mask:{}, distance_mode:{}, timing_budget:{}".format( devId, runningI2C, model_id, module_type, mask_rev, sensCl[devId].distance_mode, sensCl[devId].timing_budget))
			sensCl[devId].start_ranging()

		return 

	except  Exception as e:
		U.logger.log(30,"", exc_info=True)
	U.restartMyself(reason="connection to sensor is hanging at startSensor 3 ", delay = 10,doPrint=True, doRestartCount=False)


#################################
def doWeNeedToStartSensor(sensors,sensorsOld,selectedSensor):
	if selectedSensor not in sensors:	return -1
	if selectedSensor not in sensorsOld: return 1

	for devId in sensors[selectedSensor] :
			if devId not in sensorsOld[selectedSensor] :			return 1
			for prop in sensors[sensor][devId] :
				if prop not in sensorsOld[selectedSensor][devId] :  return 1
				if sensors[selectedSensor][devId][prop] != sensorsOld[selectedSensor][devId][prop]:
					return 1
	
	for devId in sensorsOld[selectedSensor]:
			if devId not in sensors[selectedSensor] :				return 1
			for prop in sensorsOld[selectedSensor][devId] :
				if prop not in sensors[selectedSensor][devId] :		return 1

	return 0



#################################
#################################
def getDistance(devId):
	global sensor, sensors, badSensor
	global actionDistanceOld, actionShortDistance, actionShortDistanceLimit, actionMediumDistance, actionMediumDistanceLimit, actionLongDistance, actionLongDistanceLimit
	global acuracyDistanceMode, acuracyDistanceModeOld, sensCl
	global mode, modeOld

	try:

		if modeOld[devId] != mode[devId]:
			sensCl[devId].distance_mode = mode[devId] 
		if acuracyDistanceModeOld[devId] != acuracyDistanceMode[devId]:
			sensCl[devId].timing_budget = acuracyDistanceMode[devId]

		modeOld[devId] = mode[devId]
		acuracyDistanceModeOld[devId] = acuracyDistanceMode[devId]

		dist = None
		try:			
			for ii in range(10):
				if sensCl[devId].data_ready: break
				time.sleep(0.1)

			dist = sensCl[devId].distance
			if dist is None: return 999.

			sensCl[devId].clear_interrupt()

		except  Exception as e:
			U.logger.log(20,"{}, bad sensorcount:{}".format(e, badSensor))
			badSensor += 1
			if badSensor > 4: 
				badSensor = 0
				return "badSensor"
			return ""

		badSensor = 0
		return dist#  return in cm


	except  Exception as e:
			U.logger.log(30,"", exc_info=True)
	return ""		




#################################
def doAction(distance):
	global actionDistanceOld, actionShortDistance, actionShortDistanceLimit, actionMediumDistance, actionMediumDistanceLimit, actionLongDistance, actionLongDistanceLimit

	try:
		if actionShortDistance == "" and actionMediumDistance == "" and actionMediumDistance == "": return 

		if distance != "" and distance !=0:

			if	 distance > actionLongDistanceLimit:	region = "long"
			elif distance < actionShortDistanceLimit:	region = "short"
			else:										region = "medium"

			# check reset of last action, if last was short distamce must have been not short at least once ...  
			if actionDistanceOld != "":
				if	actionDistanceOld == "short"		and region == "short":	actionDistanceOld = ""
				elif actionDistanceOld == "long"	 	and region == "long":	actionDistanceOld = ""
				elif actionDistanceOld == "medium"  	and region == "medium":	actionDistanceOld = ""

			if actionShortDistance != ""	and actionDistanceOld != "short"	and  region == "short":
				subprocess.call(actionShortDistance, shell=True)
				actionDistanceOld = "short"
					
			if actionMediumDistance != ""	and  actionDistanceOld != "medium"	and region == "medium":
				subprocess.call(actionMediumDistance, shell=True)
				actionDistanceOld = "medium"
					
			if actionLongDistance != ""		and actionDistanceOld != "long"		and region == "long":
				subprocess.call(actionLongDistance, shell=True)
				actionDistanceOld = " long"

	except  Exception as e:
			U.logger.log(30,"", exc_info=True)

#################################


			 
global sensorList, externalSensor,senors,sensorRefreshSecs,sensor, NSleep, ipAddress, dynamic, mode, deltaDist, deltaDistAbs, displayEnable
global output, authentication, badSensor
global distanceUnits, sensorActive
global actionShortDistance, actionShortDistanceLimit, actionMediumDistance, actionMediumDistanceLimit, actionLongDistance, actionLongDistanceLimit, actionDistanceOld
global oldRaw, lastRead
global badSensor, lastDist
global aliveTimeStamp, loopSleep
global acuracyDistanceMode, acuracyDistanceModeOld, sensCl, lastCycle, i2c, xShutPin
global mode, modeOld


i2c							= ""
sensCl						= {}
maxRange					= {1:230.,2:400.}
aliveTimeStamp				= time.time() + 20
badSensor					= 0
oldRaw						= ""
lastRead					= 0

distanceUnits				= "1.0"
actionShortDistance			= ""
actionShortDistanceLimit	= 5.
actionMediumDistance		= ""
actionMediumDistanceLimit	= 10
actionLongDistance			= ""
actionLongDistanceLimit	 	= 20.
actionDistanceOld			= 0

acuracyDistanceMode			= {}
acuracyDistanceModeOld		= {}
mode						= {}
modeOld						= {}
loopCount					= 0
sensorRefreshSecs			= 1
NSleep						= 100
sensorList					= []
sensors						= {}
sensor						= G.program
quick						= False
display						= "0"
output						= {}
badSensor					= 0
sensorActive				= False

sendEvery					= 30.

U.setLogging()

myPID		= str(os.getpid())
U.killOldPgm(myPID,G.program+".py")# kill old instances of myself if they are still running

if U.getIPNumber(doPrint=False) > 0:
	time.sleep(10)
	exit()


readParams()


U.echoLastAlive(G.program)

lastDist			= {}
lastData			= {}
lastTime			= {}
lastDisplay			= 0
lastRead			= time.time()
G.lastAliveSend		= time.time() -1
startPGM 			= time.time()

restartBadData 			= False

while True:
	try:
		if sensCl == {}:
			time.sleep(20)
			break
		tt = time.time()
		data = {}
		data["sensors"] = {}
		restartM = False
		sendToIndigo = False
		if sensor in sensors:
			data["sensors"][sensor] = {}
			for devId in sensors[sensor]:
				data["sensors"][sensor][devId] = {}
				if devId not in lastDist: 
					lastDist[devId] =-1
					lastTime[devId] = -1
				aliveTimeStamp = time.time() 
				dist = getDistance(devId)
				#U.logger.log(20, "devId:{}, dist:{}".format(devId, dist))

				if dist == "":
					restartBadData = True
					break

				if dist == "badSensor":
					U.logger.log(30," bad sensor, redoing")
					data["sensors"][sensor][devId]["distance"] = "badSensor"
					U.sendURL(data)
					lastDist[devId] = -100.
					U.restartMyself(reason="bad sensor ", delay =15,doPrint=True, doRestartCount=False)
					continue

				dist = round(float(dist),1)
				doAction(dist)
				if dist > maxRange[mode[devId]]: dist = 999
				delta  = dist - lastDist[devId]
				deltaA = abs(dist - lastDist[devId])
				deltaT = max(tt - lastTime[devId],0.01)
				speed  = round(delta / deltaT, 2) 
				deltaN = abs(delta) / max (0.5,(dist+lastDist[devId])/2.)

				#U.logger.log(20, "{}  dtTrue?:{}; dt{:.1f} lastDataSend:{:.1f}".format(dist, tt - abs(sensorRefreshSecs) > lastCycle["lastTime"] , tt - abs(sensorRefreshSecs), lastCycle["lastTime"]) )	
				trigDD 	= deltaN > deltaDist[devId]
				trigDDa	= deltaA > deltaDistAbs[devId]
				trigDT	= tt - sendEvery > lastTime[devId]	
				trigQi	= quick
				if devId in i2cNumber: 	i2cText= "0x{:x}".format(i2cNumber[devId])
				else:					i2cText = "off"
				if trigDD or trigDDa or trigDT or trigQi: 
							data["sensors"][sensor][devId]["i2c"]	= "{}-pin:{}".format(i2cText, xShutPin.get(devId,"off"))
							#data["sensors"][sensor][devId]["triggers"]	= "d%:{:1},dA:{:1},dT:{:1},Q:{:1},LC:{},i2c:{}".format(trigDD, trigDDa, trigDT, trigQi, loopCount, xShutPin)
							data["sensors"][sensor][devId]["distance"]	= dist
							data["sensors"][sensor][devId]["speed"]		= round(speed,2)
							sendToIndigo 			= True
							lastDist[devId]			= dist
							lastTime[devId]			= tt
							G.lastAliveSend 		= tt
				else:
					del data["sensors"][sensor][devId]

				if displayEnable == "1" and  ((deltaN > 0.05  and  tt - lastDisplay >1.)	or  tt - lastDisplay >10. or quick):
					lastDisplay = tt
					DISP.displayDistance(dist, sensor, sensors, output, distanceUnits)
					#U.logger.log(10, "{}  {}".format(dist, deltaDist) )	
					#print datetime.datetime.now().strftime("%Y%m%d-%H:%M:%S"),sensor, dist , deltaDist	

		if sendToIndigo:
			#U.logger.log(20, " data {}".format( data))
			U.sendURL(data)

		loopCount +=1

		U.makeDATfile(G.program, data)

		quick = U.checkNowFile(G.program)				
		U.echoLastAlive(G.program)
					
		aliveTimeStamp = time.time() 

		if loopCount %11 ==0:
			tt= time.time()
			if tt - lastRead > 5.:  
				readParams()
				lastRead = tt
		if not quick: 
			time.sleep(sensorRefreshSecs)
		#print "end of loop", loopCount
	except  Exception as e:
		U.logger.log(30,"", exc_info=True)
		aliveTimeStamp = time.time() +10
		time.sleep(5.)

try: 	G.sendThread["run"] = False; time.sleep(1)
except: pass
U.logger.log(30," exiting at end")
sys.exit(0)
