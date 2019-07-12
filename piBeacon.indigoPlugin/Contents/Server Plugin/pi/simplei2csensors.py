#!/usr/bin/python
# -*- coding: utf-8 -*-
# by Karl Wachs
# feb 5 2016
# version 0.9 
##
##	get sensor values and write the to a file in json format for later pickup, 
##	do it in a timed manner not to load the system, is every 1 seconds then 30 senods break
##
from __future__ import division

import math

import	sys, os, time, json, datetime,subprocess,copy


import struct

try: import smbus
except: pass




import re

import logging
sys.path.append(os.getcwd())
import	piBeaconUtils	as U
import	piBeaconGlobals as G
G.program = "simplei2csensors"





# Copyright (c) 2014 Adafruit Industries
# Author: Tony DiCola
#
# Based on the BMP280 driver with BME280 changes provided by
# David J Taylor, Edinburgh (www.satsignal.eu)
#
# Permission is hereby granted, free of charge, to any person obtaining a copy
# of this software and associated documentation files (the "Software"), to deal
# in the Software without restriction, including without limitation the rights
# to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
# copies of the Software, and to permit persons to whom the Software is
# furnished to do so, subject to the following conditions:
#
# The above copyright notice and this permission notice shall be included in
# all copies or substantial portions of the Software.
#
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
# IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
# FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
# AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
# LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
# OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN
# THE SOFTWARE.




# ===========================================================================
# Adafruit_I2C Class
# ===========================================================================

class Adafruit_I2C(object):
	@staticmethod
	def getPiRevision():
		"Gets the version number of the Raspberry Pi board"
		# Revision list available at: http://elinux.org/RPi_HardwareHistory#Board_Revision_History
		try:
			with open('/proc/cpuinfo', 'r') as infile:
				for line in infile:
					# Match a line of the form "Revision : 0002" while ignoring extra
					# info in front of the revsion (like 1000 when the Pi was over-volted).
					match = re.match('Revision\s+:\s+.*(\w{4})$', line)
					if match and match.group(1) in ['0000', '0002', '0003']:
						# Return revision 1 if revision ends with 0000, 0002 or 0003.
						return 1
					elif match:
						# Assume revision 2 if revision ends with any other 4 chars.
						return 2
				# Couldn't find the revision, assume revision 0 like older code for compatibility.
				return 0
		except:
			return 0

	@staticmethod
	def getPiI2CBusNumber():
		# Gets the I2C bus number /dev/i2c#
		return 1 

	def __init__(self, address, busnum=-1, debug=False):
		self.address = address
		# By default, the correct I2C bus is auto-detected using /proc/cpuinfo
		# Alternatively, you can hard-code the bus version below:
		# self.bus = smbus.SMBus(0); # Force I2C0 (early 256MB Pi's)
		# self.bus = smbus.SMBus(1); # Force I2C1 (512MB Pi's)
		self.bus = smbus.SMBus(busnum if busnum >-1 else Adafruit_I2C.getPiI2CBusNumber())
		self.debug = debug

	def reverseByteOrder(self, data):
		"Reverses the byte order of an int (16-bit) or long (32-bit) value"
		# Courtesy Vishal Sapre
		byteCount = len(hex(data)[2:].replace('L','')[::2])
		val				= 0
		for i in range(byteCount):
			val		   = (val << 8) | (data & 0xff)
			data >>= 8
		return val

	def errMsg(self):
		print "Error accessing 0x%02X: Check your I2C address" % self.address
		return -1

	def write8(self, reg, value):
		"Writes an 8-bit value to the specified register/address"
		try:
			self.bus.write_byte_data(self.address, reg, value)
			if self.debug:
				print "I2C: Wrote 0x%02X to register 0x%02X" % (value, reg)
		except IOError, err:
			return self.errMsg()

	def write16(self, reg, value):
		"Writes a 16-bit value to the specified register/address pair"
		try:
			self.bus.write_word_data(self.address, reg, value)
			if self.debug:
				print ("I2C: Wrote 0x%02X to register pair 0x%02X,0x%02X" %
				 (value, reg, reg+1))
		except IOError, err:
			return self.errMsg()

	def writeRaw8(self, value):
		"Writes an 8-bit value on the bus"
		try:
			self.bus.write_byte(self.address, value)
			if self.debug:
				print "I2C: Wrote 0x%02X" % value
		except IOError, err:
			return self.errMsg()

	def writeList(self, reg, list):
		"Writes an array of bytes using I2C format"
		try:
			if self.debug:
				print "I2C: Writing list to register 0x%02X:" % reg
				print list
			self.bus.write_i2c_block_data(self.address, reg, list)
		except IOError, err:
			return self.errMsg()

	def readList(self, reg, length):
		"Read a list of bytes from the I2C device"
		try:
			results = self.bus.read_i2c_block_data(self.address, reg, length)
			if self.debug:
				print ("I2C: Device 0x%02X returned the following from reg 0x%02X" %
				 (self.address, reg))
				print results
			return results
		except IOError, err:
			return self.errMsg()

	def readU8(self, reg):
		"Read an unsigned byte from the I2C device"
		try:
			result = self.bus.read_byte_data(self.address, reg)
			if self.debug:
				print ("I2C: Device 0x%02X returned 0x%02X from reg 0x%02X" %
				 (self.address, result & 0xFF, reg))
			return result
		except IOError, err:
			return self.errMsg()

	def readS8(self, reg):
		"Reads a signed byte from the I2C device"
		try:
			result = self.bus.read_byte_data(self.address, reg)
			if result > 127: result -= 256
			if self.debug:
				print ("I2C: Device 0x%02X returned 0x%02X from reg 0x%02X" %
				 (self.address, result & 0xFF, reg))
			return result
		except IOError, err:
			return self.errMsg()

	def readU16(self, reg, little_endian=True):
		"Reads an unsigned 16-bit value from the I2C device"
		try:
			result = self.bus.read_word_data(self.address,reg)
			# Swap bytes if using big endian because read_word_data assumes little
			# endian on ARM (little endian) systems.
			if not little_endian:
				result = ((result << 8) & 0xFF00) + (result >> 8)
			if (self.debug):
				print "I2C: Device 0x%02X returned 0x%04X from reg 0x%02X" % (self.address, result & 0xFFFF, reg)
			return result
		except IOError, err:
			return self.errMsg()

	def readU16BE(self, register):
		"""Read an unsigned 16-bit value from the specified register, in big
		endian byte order."""
		return self.readU16(register, little_endian=False)


	def readU16Rev(self, reg):
		"Reads an unsigned 16-bit value from the I2C device with rev byte order"
		try:
			lobyte = self.readU8(reg)
			hibyte = self.readU8(reg+1)
			result = (hibyte << 8) + lobyte
			if (self.debug):
				print "I2C: Device 0x%02X returned 0x%04X from reg 0x%02X" % (self.address, result & 0xFFFF, reg)
			return result
		except IOError, err:
			return self.errMsg()

	def readU16LE(self, register):
		"""Read an unsigned 16-bit value from the specified register, in little
		endian byte order."""
		return self.readU16(register, little_endian=True)



	def readS16(self, reg, little_endian=True):
		"Reads a signed 16-bit value from the I2C device"
		try:
			result = self.readU16(reg,little_endian)
			if result > 32767: result -= 65536
			return result
		except IOError, err:
			return self.errMsg()

	def readS16BE(self, register):
		"""Read a signed 16-bit value from the specified register, in big
		endian byte order."""
		return self.readS16(register, little_endian=False)

	def readS16Rev(self, reg):
		"Reads a signed 16-bit value from the I2C device with rev byte order"
		try:
			lobyte = self.readS8(reg)
			hibyte = self.readU8(reg+1)
			result = (hibyte << 8) + lobyte
			if (self.debug):
				print "I2C: Device 0x%02X returned 0x%04X from reg 0x%02X" % (self.address, result & 0xFFFF, reg)
			return result
		except IOError, err:
			return self.errMsg()
 
	def readS16LE(self, register):
		"""Read a signed 16-bit value from the specified register, in little
		endian byte order."""
		return self.readS16(register, little_endian=True)

	def readS16BE(self, register):
		"""Read a signed 16-bit value from the specified register, in big
		endian byte order."""
		return self.readS16(register, little_endian=False)

# ===========================================================================
# veml6070 Class
# ===========================================================================




class VEML6070:
	ADDR_L				=0x38 # 7bit address of the VEML6070 (write, read)
	ADDR_H				=0x39 # 7bit address of the VEML6070 (read)

	RSET_240K			=240000
	RSET_270K			=270000
	RSET_300K			=300000
	RSET_600K			=600000

	SHUTDOWN_DISABLE	=0x00
	SHUTDOWN_ENABLE		=0x01

	INTEGRATIONTIME_1_2T=0x00
	INTEGRATIONTIME_1T	=0x01
	INTEGRATIONTIME_2T	=0x02
	INTEGRATIONTIME_4T	=0x03

	def __init__(self, i2c_bus=1, rSet=270000, integrationTime=0x02):
		try:
			self.bus = smbus.SMBus(i2c_bus)
			self.sensor_address = 0x38
			self.rset = rSet
			self.shutdown = self.SHUTDOWN_DISABLE # before set_integration_time()
			self.set_integration_time(integrationTime&0x03)
			self.disable()
		except	Exception, e:
			U.toLog(-1, u"in Line {} has error={}".format(sys.exc_traceback.tb_lineno, e))

	def set_integration_time(self, integrationTime):
		try:
			self.integration_time = integrationTime&0x03
			self.bus.write_byte(self.sensor_address, self.get_command_byte())
			# constant offset determined experimentally to allow sensor to readjust
			time.sleep(0.2)
		except	Exception, e:
			U.toLog(-1, u"in Line {} has error={}".format(sys.exc_traceback.tb_lineno, e))

	def get_integration_time(self):
		return self.integration_time

	def enable(self):
		self.shutdown = self.SHUTDOWN_DISABLE
		self.bus.write_byte(self.sensor_address, self.get_command_byte())

	def disable(self):
		self.shutdown = self.SHUTDOWN_ENABLE
		self.bus.write_byte(self.sensor_address, self.get_command_byte())

	def get_uva_light_intensity_raw(self):
		self.enable()
		# wait two times the refresh time to allow completion of a previous cycle with old settings (worst case)
		time.sleep(self.get_refresh_time()*2)
		msb = self.bus.read_byte(self.sensor_address+(self.ADDR_H-self.ADDR_L))
		lsb = self.bus.read_byte(self.sensor_address)
		self.disable()
		return (msb << 8) | lsb

	def get_uva_light_intensity(self):
		uv	 = self.get_uva_light_intensity_raw()
		sensi= self.get_uva_light_sensitivity()
		return uv * sensi

	def get_command_byte(self):
		"""
		assembles the command byte for the current state
		"""
		cmd = (self.shutdown & 0x01) << 0 # SD
		cmd = (self.integration_time & 0x03) << 2 # IT
		cmd = ((cmd | 0x02) & 0x3F) # reserved bits
		return cmd

	def get_refresh_time(self):
		"""
		returns time needed to perform a complete measurement using current settings (in s)
		"""
		case_refresh_rset = {
			self.RSET_240K: 0.1,
			self.RSET_270K: 0.1125,
			self.RSET_300K: 0.125,
			self.RSET_600K: 0.25
		}
		case_refresh_it = {
			self.INTEGRATIONTIME_1_2T: 0.5,
			self.INTEGRATIONTIME_1T: 1,
			self.INTEGRATIONTIME_2T: 2,
			self.INTEGRATIONTIME_4T: 4
		}
		return case_refresh_rset[self.rset] * case_refresh_it[self.integration_time]

	def get_uva_light_sensitivity(self):
		"""
		returns UVA light sensitivity in W/(m*m)/step
		"""
		case_sens_rset = {
			self.RSET_240K: 0.05,
			self.RSET_270K: 0.05625,
			self.RSET_300K: 0.0625,
			self.RSET_600K: 0.125
		}
		case_sens_it = {
			self.INTEGRATIONTIME_1_2T: 0.5,
			self.INTEGRATIONTIME_1T: 1,
			self.INTEGRATIONTIME_2T: 2,
			self.INTEGRATIONTIME_4T: 4
		}
		return case_sens_rset[self.rset] / case_sens_it[self.integration_time]


# ===========================================================================
# BME280 Class
# ===========================================================================


class BME280:

	# BME280 default address.
	BME280_I2CADDR = 0x77

	# Operating Modes
	BME280_OSAMPLE_1 = 1
	BME280_OSAMPLE_2 = 2
	BME280_OSAMPLE_4 = 3
	BME280_OSAMPLE_8 = 4
	BME280_OSAMPLE_16 = 5

	# BME280 Registers

	BME280_REGISTER_DIG_T1 = 0x88  # Trimming parameter registers
	BME280_REGISTER_DIG_T2 = 0x8A
	BME280_REGISTER_DIG_T3 = 0x8C

	BME280_REGISTER_DIG_P1 = 0x8E
	BME280_REGISTER_DIG_P2 = 0x90
	BME280_REGISTER_DIG_P3 = 0x92
	BME280_REGISTER_DIG_P4 = 0x94
	BME280_REGISTER_DIG_P5 = 0x96
	BME280_REGISTER_DIG_P6 = 0x98
	BME280_REGISTER_DIG_P7 = 0x9A
	BME280_REGISTER_DIG_P8 = 0x9C
	BME280_REGISTER_DIG_P9 = 0x9E

	BME280_REGISTER_DIG_H1 = 0xA1
	BME280_REGISTER_DIG_H2 = 0xE1
	BME280_REGISTER_DIG_H3 = 0xE3
	BME280_REGISTER_DIG_H4 = 0xE4
	BME280_REGISTER_DIG_H5 = 0xE5
	BME280_REGISTER_DIG_H6 = 0xE6
	BME280_REGISTER_DIG_H7 = 0xE7

	BME280_REGISTER_CHIPID = 0xD0
	BME280_REGISTER_VERSION = 0xD1
	BME280_REGISTER_SOFTRESET = 0xE0

	BME280_REGISTER_CONTROL_HUM = 0xF2
	BME280_REGISTER_CONTROL = 0xF4
	BME280_REGISTER_CONFIG = 0xF5
	BME280_REGISTER_PRESSURE_DATA = 0xF7
	BME280_REGISTER_TEMP_DATA = 0xFA
	BME280_REGISTER_HUMIDITY_DATA = 0xFD


	def __init__(self, mode=4, address=0x77, i2c=None,**kwargs):
		try:
			# Check that mode is valid.
			if mode not in [self.BME280_OSAMPLE_1, self.BME280_OSAMPLE_2, self.BME280_OSAMPLE_4,
							self.BME280_OSAMPLE_8, self.BME280_OSAMPLE_16]:
				raise ValueError(
					'Unexpected mode value {0}.	 Set mode to one of self.BME280_ULTRALOWPOWER, self.BME280_STANDARD, self.BME280_HIGHRES, or self.BME280_ULTRAHIGHRES'.format(mode))
			self._mode = mode
			# Create I2C device.
			self._device = Adafruit_I2C(address)
			# Load calibration values.
			self._load_calibration()
			self._device.write8(self.BME280_REGISTER_CONTROL, 0x3F)
			self.t_fine = 0.0
		except	Exception, e:
				U.toLog(-1, u"in Line {} has error={}".format(sys.exc_traceback.tb_lineno, e))
		

	def _load_calibration(self):

		self.dig_T1 = self._device.readU16(self.BME280_REGISTER_DIG_T1)
		self.dig_T2 = self._device.readS16(self.BME280_REGISTER_DIG_T2)
		self.dig_T3 = self._device.readS16(self.BME280_REGISTER_DIG_T3)

		self.dig_P1 = self._device.readU16(self.BME280_REGISTER_DIG_P1)
		self.dig_P2 = self._device.readS16(self.BME280_REGISTER_DIG_P2)
		self.dig_P3 = self._device.readS16(self.BME280_REGISTER_DIG_P3)
		self.dig_P4 = self._device.readS16(self.BME280_REGISTER_DIG_P4)
		self.dig_P5 = self._device.readS16(self.BME280_REGISTER_DIG_P5)
		self.dig_P6 = self._device.readS16(self.BME280_REGISTER_DIG_P6)
		self.dig_P7 = self._device.readS16(self.BME280_REGISTER_DIG_P7)
		self.dig_P8 = self._device.readS16(self.BME280_REGISTER_DIG_P8)
		self.dig_P9 = self._device.readS16(self.BME280_REGISTER_DIG_P9)

		self.dig_H1 = self._device.readU8(self.BME280_REGISTER_DIG_H1)
		self.dig_H2 = self._device.readS16(self.BME280_REGISTER_DIG_H2)
		self.dig_H3 = self._device.readU8(self.BME280_REGISTER_DIG_H3)
		self.dig_H6 = self._device.readS8(self.BME280_REGISTER_DIG_H7)

		h4 = self._device.readS8(self.BME280_REGISTER_DIG_H4)
		h4 = (h4 << 24) >> 20
		self.dig_H4 = h4 | (self._device.readU8(self.BME280_REGISTER_DIG_H5) & 0x0F)

		h5 = self._device.readS8(self.BME280_REGISTER_DIG_H6)
		h5 = (h5 << 24) >> 20
		self.dig_H5 = h5 | (self._device.readU8(self.BME280_REGISTER_DIG_H5) >> 4 & 0x0F)

		'''
		print '0xE4 = {0:2x}'.format (self._device.readU8 (self.BME280_REGISTER_DIG_H4))
		print '0xE5 = {0:2x}'.format (self._device.readU8 (self.BME280_REGISTER_DIG_H5))
		print '0xE6 = {0:2x}'.format (self._device.readU8 (self.BME280_REGISTER_DIG_H6))
		print 'dig_H1 = {0:d}'.format (self.dig_H1)
		print 'dig_H2 = {0:d}'.format (self.dig_H2)
		print 'dig_H3 = {0:d}'.format (self.dig_H3)
		print 'dig_H4 = {0:d}'.format (self.dig_H4)
		print 'dig_H5 = {0:d}'.format (self.dig_H5)
		print 'dig_H6 = {0:d}'.format (self.dig_H6)
		'''

	def read_raw_temp(self):
		"""Reads the raw (uncompensated) temperature from the sensor."""
		meas = self._mode
		self._device.write8(self.BME280_REGISTER_CONTROL_HUM, meas)
		meas = self._mode << 5 | self._mode << 2 | 1
		self._device.write8(self.BME280_REGISTER_CONTROL, meas)
		sleep_time = 0.00125 + 0.0023 * (1 << self._mode)
		sleep_time = sleep_time + 0.0023 * (1 << self._mode) + 0.000575
		sleep_time = sleep_time + 0.0023 * (1 << self._mode) + 0.000575
		time.sleep(sleep_time)	# Wait the required time
		msb = self._device.readU8(self.BME280_REGISTER_TEMP_DATA)
		lsb = self._device.readU8(self.BME280_REGISTER_TEMP_DATA + 1)
		xlsb = self._device.readU8(self.BME280_REGISTER_TEMP_DATA + 2)
		raw = ((msb << 16) | (lsb << 8) | xlsb) >> 4
		return raw

	def read_raw_pressure(self):
		"""Reads the raw (uncompensated) pressure level from the sensor."""
		"""Assumes that the temperature has already been read """
		"""i.e. that enough delay has been provided"""
		msb = self._device.readU8(self.BME280_REGISTER_PRESSURE_DATA)
		lsb = self._device.readU8(self.BME280_REGISTER_PRESSURE_DATA + 1)
		xlsb = self._device.readU8(self.BME280_REGISTER_PRESSURE_DATA + 2)
		raw = ((msb << 16) | (lsb << 8) | xlsb) >> 4
		return raw

	def read_raw_humidity(self):
		"""Assumes that the temperature has already been read """
		"""i.e. that enough delay has been provided"""
		msb = self._device.readU8(self.BME280_REGISTER_HUMIDITY_DATA)
		lsb = self._device.readU8(self.BME280_REGISTER_HUMIDITY_DATA + 1)
		raw = (msb << 8) | lsb
		return raw

	def read_temperature(self):
		"""Gets the compensated temperature in degrees celsius."""
		# float in Python is double precision
		UT = float(self.read_raw_temp())
		var1 = (UT / 16384.0 - self.dig_T1 / 1024.0) * float(self.dig_T2)
		var2 = ((UT / 131072.0 - self.dig_T1 / 8192.0) * (UT / 131072.0 - self.dig_T1 / 8192.0)) * float(self.dig_T3)
		self.t_fine = int(var1 + var2)
		temp = (var1 + var2) / 5120.0
		return temp

	def read_pressure(self):
		"""Gets the compensated pressure in Pascals."""
		adc = self.read_raw_pressure()
		var1 = self.t_fine / 2.0 - 64000.0
		var2 = var1 * var1 * self.dig_P6 / 32768.0
		var2 = var2 + var1 * self.dig_P5 * 2.0
		var2 = var2 / 4.0 + self.dig_P4 * 65536.0
		var1 = (
			   self.dig_P3 * var1 * var1 / 524288.0 + self.dig_P2 * var1) / 524288.0
		var1 = (1.0 + var1 / 32768.0) * self.dig_P1
		if var1 == 0:
			return 0
		p = 1048576.0 - adc
		p = ((p - var2 / 4096.0) * 6250.0) / var1
		var1 = self.dig_P9 * p * p / 2147483648.0
		var2 = p * self.dig_P8 / 32768.0
		p = p + (var1 + var2 + self.dig_P7) / 16.0
		return p

	def read_humidity(self):
		adc = self.read_raw_humidity()
		# print 'Raw humidity = {0:d}'.format (adc)
		h = self.t_fine - 76800.0
		h = (adc - (self.dig_H4 * 64.0 + self.dig_H5 / 16384.8 * h)) * (
		self.dig_H2 / 65536.0 * (1.0 + self.dig_H6 / 67108864.0 * h * (
		1.0 + self.dig_H3 / 67108864.0 * h)))
		h = h * (1.0 - self.dig_H1 * h / 524288.0)
		if h > 100:
			h = 100
		elif h < 0:
			h = 0
		return h





# ===========================================================================
# BMP
# ===========================================================================


# Copyright (c) 2014 Adafruit Industries
# Author: Tony DiCola
#
# Permission is hereby granted, free of charge, to any person obtaining a copy
# of this software and associated documentation files (the "Software"), to deal
# in the Software without restriction, including without limitation the rights
# to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
# copies of the Software, and to permit persons to whom the Software is
# furnished to do so, subject to the following conditions:
#
# The above copyright notice and this permission notice shall be included in
# all copies or substantial portions of the Software.
#
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
# IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
# FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
# AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
# LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
# OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN
# THE SOFTWARE.




class BMP085:
	# BMP085 default address.
	BMP085_I2CADDR			 = 0x77

	# Operating Modes
	BMP085_ULTRALOWPOWER	 = 0
	BMP085_STANDARD			 = 1
	BMP085_HIGHRES			 = 2
	BMP085_ULTRAHIGHRES		 = 3

	# BMP085 Registers
	BMP085_CAL_AC1			 = 0xAA	 # R   Calibration data (16 bits)
	BMP085_CAL_AC2			 = 0xAC	 # R   Calibration data (16 bits)
	BMP085_CAL_AC3			 = 0xAE	 # R   Calibration data (16 bits)
	BMP085_CAL_AC4			 = 0xB0	 # R   Calibration data (16 bits)
	BMP085_CAL_AC5			 = 0xB2	 # R   Calibration data (16 bits)
	BMP085_CAL_AC6			 = 0xB4	 # R   Calibration data (16 bits)
	BMP085_CAL_B1			 = 0xB6	 # R   Calibration data (16 bits)
	BMP085_CAL_B2			 = 0xB8	 # R   Calibration data (16 bits)
	BMP085_CAL_MB			 = 0xBA	 # R   Calibration data (16 bits)
	BMP085_CAL_MC			 = 0xBC	 # R   Calibration data (16 bits)
	BMP085_CAL_MD			 = 0xBE	 # R   Calibration data (16 bits)
	BMP085_CONTROL			 = 0xF4
	BMP085_TEMPDATA			 = 0xF6
	BMP085_PRESSUREDATA		 = 0xF6

	# Commands
	BMP085_READTEMPCMD		 = 0x2E
	BMP085_READPRESSURECMD	 = 0x34



	def __init__(self, mode=1, address=0x77, i2c=None, **kwargs):
		# Check that mode is valid.
		if mode not in [self.BMP085_ULTRALOWPOWER, self.BMP085_STANDARD, self.BMP085_HIGHRES, self.BMP085_ULTRAHIGHRES]:
			raise ValueError('Unexpected mode value {0}.  Set mode to one of self.BMP085_ULTRALOWPOWER, self.BMP085_STANDARD, self.BMP085_HIGHRES, or self.BMP085_ULTRAHIGHRES'.format(mode))
		self._mode = mode
		# Create I2C device.
		self._device =	Adafruit_I2C(address)
		# Load calibration values.
		self._load_calibration()

	def _load_calibration(self):
		self.cal_AC1 = self._device.readS16BE(self.BMP085_CAL_AC1)	 # INT16
		self.cal_AC2 = self._device.readS16BE(self.BMP085_CAL_AC2)	 # INT16
		self.cal_AC3 = self._device.readS16BE(self.BMP085_CAL_AC3)	 # INT16
		self.cal_AC4 = self._device.readU16BE(self.BMP085_CAL_AC4)	 # UINT16
		self.cal_AC5 = self._device.readU16BE(self.BMP085_CAL_AC5)	 # UINT16
		self.cal_AC6 = self._device.readU16BE(self.BMP085_CAL_AC6)	 # UINT16
		self.cal_B1 = self._device.readS16BE(self.BMP085_CAL_B1)	 # INT16
		self.cal_B2 = self._device.readS16BE(self.BMP085_CAL_B2)	 # INT16
		self.cal_MB = self._device.readS16BE(self.BMP085_CAL_MB)	 # INT16
		self.cal_MC = self._device.readS16BE(self.BMP085_CAL_MC)	 # INT16
		self.cal_MD = self._device.readS16BE(self.BMP085_CAL_MD)	 # INT16
		U.toLog(3,'AC1 = {0:6d}'.format(self.cal_AC1))
		U.toLog(3,'AC2 = {0:6d}'.format(self.cal_AC2))
		U.toLog(3,'AC3 = {0:6d}'.format(self.cal_AC3))
		U.toLog(3,'AC4 = {0:6d}'.format(self.cal_AC4))
		U.toLog(3,'AC5 = {0:6d}'.format(self.cal_AC5))
		U.toLog(3,'AC6 = {0:6d}'.format(self.cal_AC6))
		U.toLog(3,'B1 = {0:6d}'.format(self.cal_B1))
		U.toLog(3,'B2 = {0:6d}'.format(self.cal_B2))
		U.toLog(3,'MB = {0:6d}'.format(self.cal_MB))
		U.toLog(3,'MC = {0:6d}'.format(self.cal_MC))
		U.toLog(3,'MD = {0:6d}'.format(self.cal_MD))

	def _load_datasheet_calibration(self):
		# Set calibration from values in the datasheet example.	 Useful for debugging the
		# temp and pressure calculation accuracy.
		self.cal_AC1 = 408
		self.cal_AC2 = -72
		self.cal_AC3 = -14383
		self.cal_AC4 = 32741
		self.cal_AC5 = 32757
		self.cal_AC6 = 23153
		self.cal_B1 = 6190
		self.cal_B2 = 4
		self.cal_MB = -32767
		self.cal_MC = -8711
		self.cal_MD = 2868

	def read_raw_temp(self):
		"""Reads the raw (uncompensated) temperature from the sensor."""
		self._device.write8(self.BMP085_CONTROL, self.BMP085_READTEMPCMD)
		time.sleep(0.005)  # Wait 5ms
		raw = self._device.readU16BE(self.BMP085_TEMPDATA)
		U.toLog(3,'Raw temp 0x{0:X} ({1})'.format(raw & 0xFFFF, raw))
		return raw

	def read_raw_pressure(self):
		"""Reads the raw (uncompensated) pressure level from the sensor."""
		self._device.write8(self.BMP085_CONTROL, self.BMP085_READPRESSURECMD + (self._mode << 6))
		if self._mode == self.BMP085_ULTRALOWPOWER:
			time.sleep(0.005)
		elif self._mode == self.BMP085_HIGHRES:
			time.sleep(0.014)
		elif self._mode == self.BMP085_ULTRAHIGHRES:
			time.sleep(0.026)
		else:
			time.sleep(0.008)
		msb = self._device.readU8(self.BMP085_PRESSUREDATA)
		lsb = self._device.readU8(self.BMP085_PRESSUREDATA+1)
		xlsb = self._device.readU8(self.BMP085_PRESSUREDATA+2)
		raw = ((msb << 16) + (lsb << 8) + xlsb) >> (8 - self._mode)
		U.toLog(3,'Raw pressure 0x{0:04X} ({1})'.format(raw & 0xFFFF, raw))
		return raw

	def read_temperature(self):
		"""Gets the compensated temperature in degrees celsius."""
		UT = self.read_raw_temp()
		# Datasheet value for debugging:
		#UT = 27898
		# Calculations below are taken straight from section 3.5 of the datasheet.
		X1 = ((UT - self.cal_AC6) * self.cal_AC5) >> 15
		X2 = (self.cal_MC << 11) // (X1 + self.cal_MD)
		B5 = X1 + X2
		temp = ((B5 + 8) >> 4) / 10.0
		U.toLog(3,'Calibrated temperature {0} C'.format(temp))
		return temp

	def read_pressure(self):
		"""Gets the compensated pressure in Pascals."""
		UT = self.read_raw_temp()
		UP = self.read_raw_pressure()
		# Datasheet values for debugging:
		#UT = 27898
		#UP = 23843
		# Calculations below are taken straight from section 3.5 of the datasheet.
		# Calculate true temperature coefficient B5.
		X1 = ((UT - self.cal_AC6) * self.cal_AC5) >> 15
		X2 = (self.cal_MC << 11) // (X1 + self.cal_MD)
		B5 = X1 + X2
		U.toLog(3,'B5 = {0}'.format(B5))
		# Pressure Calculations
		B6 = B5 - 4000
		U.toLog(3,'B6 = {0}'.format(B6))
		X1 = (self.cal_B2 * (B6 * B6) >> 12) >> 11
		X2 = (self.cal_AC2 * B6) >> 11
		X3 = X1 + X2
		B3 = (((self.cal_AC1 * 4 + X3) << self._mode) + 2) // 4
		U.toLog(3,'B3 = {0}'.format(B3))
		X1 = (self.cal_AC3 * B6) >> 13
		X2 = (self.cal_B1 * ((B6 * B6) >> 12)) >> 16
		X3 = ((X1 + X2) + 2) >> 2
		B4 = (self.cal_AC4 * (X3 + 32768)) >> 15
		U.toLog(3,'B4 = {0}'.format(B4))
		B7 = (UP - B3) * (50000 >> self._mode)
		U.toLog(3,'B7 = {0}'.format(B7))
		if B7 < 0x80000000:
			p = (B7 * 2) // B4
		else:
			p = (B7 // B4) * 2
		X1 = (p >> 8) * (p >> 8)
		X1 = (X1 * 3038) >> 16
		X2 = (-7357 * p) >> 16
		p = p + ((X1 + X2 + 3791) >> 4)
		U.toLog(3,'Pressure {0} Pa'.format(p))
		return p

	def read_altitude(self, sealevel_pa=101325.0):
		"""Calculates the altitude in meters."""
		# Calculation taken straight from section 3.6 of the datasheet.
		pressure = float(self.read_pressure())
		altitude = 44330.0 * (1.0 - pow(pressure / sealevel_pa, (1.0/5.255)))
		U.toLog(3,'Altitude {0} m'.format(altitude))
		return altitude

	def read_sealevel_pressure(self, altitude_m=0.0):
		"""Calculates the pressure at sealevel when given a known altitude in
		meters. Returns a value in Pascals."""
		pressure = float(self.read_pressure())
		p0 = pressure / pow(1.0 - altitude_m/44330.0, 5.255)
		U.toLog(3,'Sealevel pressure {0} Pa'.format(p0))
		return p0






# ===========================================================================
# ADS1x15 Class
#
# Originally written by K. Townsend, Adafruit (https://github.com/adafruit/Adafruit-Raspberry-Pi-Python-Code/tree/master/Adafruit_ADS1x15)
# Updates and new functions implementation by Pedro Villanueva, 03/2013.
# The only error in the original code was in line 57:
#			   __ADS1015_REG_CONFIG_DR_920SPS	 = 0x0050
# should be
#			   __ADS1015_REG_CONFIG_DR_920SPS	 = 0x0060
#
# NOT IMPLEMENTED: Conversion ready pin, page 15 datasheet.
# ===========================================================================

class ADS1x15:
	i2c = None

	# IC Identifiers
	__IC_ADS1015					  = 0x00
	__IC_ADS1115					  = 0x01

	# Pointer Register
	__ADS1015_REG_POINTER_MASK		  = 0x03
	__ADS1015_REG_POINTER_CONVERT	  = 0x00
	__ADS1015_REG_POINTER_CONFIG	  = 0x01
	__ADS1015_REG_POINTER_LOWTHRESH	  = 0x02
	__ADS1015_REG_POINTER_HITHRESH	  = 0x03

	# Config Register
	__ADS1015_REG_CONFIG_OS_MASK	  = 0x8000
	__ADS1015_REG_CONFIG_OS_SINGLE	  = 0x8000	# Write: Set to start a single-conversion
	__ADS1015_REG_CONFIG_OS_BUSY	  = 0x0000	# Read: Bit = 0 when conversion is in progress
	__ADS1015_REG_CONFIG_OS_NOTBUSY	  = 0x8000	# Read: Bit = 1 when device is not performing a conversion

	__ADS1015_REG_CONFIG_MUX_MASK	  = 0x7000
	__ADS1015_REG_CONFIG_MUX_DIFF_0_1 = 0x0000	# Differential P = AIN0, N = AIN1 (default)
	__ADS1015_REG_CONFIG_MUX_DIFF_0_3 = 0x1000	# Differential P = AIN0, N = AIN3
	__ADS1015_REG_CONFIG_MUX_DIFF_1_3 = 0x2000	# Differential P = AIN1, N = AIN3
	__ADS1015_REG_CONFIG_MUX_DIFF_2_3 = 0x3000	# Differential P = AIN2, N = AIN3
	__ADS1015_REG_CONFIG_MUX_SINGLE_0 = 0x4000	# Single-ended AIN0
	__ADS1015_REG_CONFIG_MUX_SINGLE_1 = 0x5000	# Single-ended AIN1
	__ADS1015_REG_CONFIG_MUX_SINGLE_2 = 0x6000	# Single-ended AIN2
	__ADS1015_REG_CONFIG_MUX_SINGLE_3 = 0x7000	# Single-ended AIN3

	__ADS1015_REG_CONFIG_PGA_MASK	  = 0x0E00
	__ADS1015_REG_CONFIG_PGA_6_144V	  = 0x0000	# +/-6.144V range
	__ADS1015_REG_CONFIG_PGA_4_096V	  = 0x0200	# +/-4.096V range
	__ADS1015_REG_CONFIG_PGA_2_048V	  = 0x0400	# +/-2.048V range (default)
	__ADS1015_REG_CONFIG_PGA_1_024V	  = 0x0600	# +/-1.024V range
	__ADS1015_REG_CONFIG_PGA_0_512V	  = 0x0800	# +/-0.512V range
	__ADS1015_REG_CONFIG_PGA_0_256V	  = 0x0A00	# +/-0.256V range

	__ADS1015_REG_CONFIG_MODE_MASK	  = 0x0100
	__ADS1015_REG_CONFIG_MODE_CONTIN  = 0x0000	# Continuous conversion mode
	__ADS1015_REG_CONFIG_MODE_SINGLE  = 0x0100	# Power-down single-shot mode (default)

	__ADS1015_REG_CONFIG_DR_MASK	  = 0x00E0
	__ADS1015_REG_CONFIG_DR_128SPS	  = 0x0000	# 128 samples per second
	__ADS1015_REG_CONFIG_DR_250SPS	  = 0x0020	# 250 samples per second
	__ADS1015_REG_CONFIG_DR_490SPS	  = 0x0040	# 490 samples per second
	__ADS1015_REG_CONFIG_DR_920SPS	  = 0x0060	# 920 samples per second
	__ADS1015_REG_CONFIG_DR_1600SPS	  = 0x0080	# 1600 samples per second (default)
	__ADS1015_REG_CONFIG_DR_2400SPS	  = 0x00A0	# 2400 samples per second
	__ADS1015_REG_CONFIG_DR_3300SPS	  = 0x00C0	# 3300 samples per second (also 0x00E0)

	__ADS1115_REG_CONFIG_DR_8SPS	  = 0x0000	# 8 samples per second
	__ADS1115_REG_CONFIG_DR_16SPS	  = 0x0020	# 16 samples per second
	__ADS1115_REG_CONFIG_DR_32SPS	  = 0x0040	# 32 samples per second
	__ADS1115_REG_CONFIG_DR_64SPS	  = 0x0060	# 64 samples per second
	__ADS1115_REG_CONFIG_DR_128SPS	  = 0x0080	# 128 samples per second
	__ADS1115_REG_CONFIG_DR_250SPS	  = 0x00A0	# 250 samples per second (default)
	__ADS1115_REG_CONFIG_DR_475SPS	  = 0x00C0	# 475 samples per second
	__ADS1115_REG_CONFIG_DR_860SPS	  = 0x00E0	# 860 samples per second

	__ADS1015_REG_CONFIG_CMODE_MASK	  = 0x0010
	__ADS1015_REG_CONFIG_CMODE_TRAD	  = 0x0000	# Traditional comparator with hysteresis (default)
	__ADS1015_REG_CONFIG_CMODE_WINDOW = 0x0010	# Window comparator

	__ADS1015_REG_CONFIG_CPOL_MASK	  = 0x0008
	__ADS1015_REG_CONFIG_CPOL_ACTVLOW = 0x0000	# ALERT/RDY pin is low when active (default)
	__ADS1015_REG_CONFIG_CPOL_ACTVHI  = 0x0008	# ALERT/RDY pin is high when active

	__ADS1015_REG_CONFIG_CLAT_MASK	  = 0x0004	# Determines if ALERT/RDY pin latches once asserted
	__ADS1015_REG_CONFIG_CLAT_NONLAT  = 0x0000	# Non-latching comparator (default)
	__ADS1015_REG_CONFIG_CLAT_LATCH	  = 0x0004	# Latching comparator

	__ADS1015_REG_CONFIG_CQUE_MASK	  = 0x0003
	__ADS1015_REG_CONFIG_CQUE_1CONV	  = 0x0000	# Assert ALERT/RDY after one conversions
	__ADS1015_REG_CONFIG_CQUE_2CONV	  = 0x0001	# Assert ALERT/RDY after two conversions
	__ADS1015_REG_CONFIG_CQUE_4CONV	  = 0x0002	# Assert ALERT/RDY after four conversions
	__ADS1015_REG_CONFIG_CQUE_NONE	  = 0x0003	# Disable the comparator and put ALERT/RDY in high state (default)


	# Dictionaries with the sampling speed values
	# These simplify and clean the code (avoid the abuse of if/elif/else clauses)
	spsADS1115 = {
	8:__ADS1115_REG_CONFIG_DR_8SPS,
	16:__ADS1115_REG_CONFIG_DR_16SPS,
	32:__ADS1115_REG_CONFIG_DR_32SPS,
	64:__ADS1115_REG_CONFIG_DR_64SPS,
	128:__ADS1115_REG_CONFIG_DR_128SPS,
	250:__ADS1115_REG_CONFIG_DR_250SPS,
	475:__ADS1115_REG_CONFIG_DR_475SPS,
	860:__ADS1115_REG_CONFIG_DR_860SPS
	}
	spsADS1015 = {
	128:__ADS1015_REG_CONFIG_DR_128SPS,
	250:__ADS1015_REG_CONFIG_DR_250SPS,
	490:__ADS1015_REG_CONFIG_DR_490SPS,
	920:__ADS1015_REG_CONFIG_DR_920SPS,
	1600:__ADS1015_REG_CONFIG_DR_1600SPS,
	2400:__ADS1015_REG_CONFIG_DR_2400SPS,
	3300:__ADS1015_REG_CONFIG_DR_3300SPS
	}
	# Dictionariy with the programable gains
	pgaADS1x15 = {
	6144:__ADS1015_REG_CONFIG_PGA_6_144V,
	4096:__ADS1015_REG_CONFIG_PGA_4_096V,
	2048:__ADS1015_REG_CONFIG_PGA_2_048V,
	1024:__ADS1015_REG_CONFIG_PGA_1_024V,
	512:__ADS1015_REG_CONFIG_PGA_0_512V,
	256:__ADS1015_REG_CONFIG_PGA_0_256V
	}


	# Constructor
	def __init__(self, address=0x4a, ic=__IC_ADS1115, debug=False):
		try:
			# Depending on if you have an old or a new Raspberry Pi, you
			# may need to change the I2C bus.  Older Pis use SMBus 0,
			# whereas new Pis use SMBus 1.	If you see an error like:
			# 'Error accessing 0x48: Check your I2C address '
			# change the SMBus number in the initializer below!
			self._Device = Adafruit_I2C(address)
			self.address = address
			self.debug = debug

			# Make sure the IC specified is valid
			if ((ic < self.__IC_ADS1015) | (ic > self.__IC_ADS1115)):
				if (self.debug):
					print "ADS1x15: Invalid IC specfied: ", ic
				return
			else:
				self.ic = ic

			# Set pga value, so that getLastConversionResult() can use it,
			# any function that accepts a pga value must update this.
			self.pga = 6144
		except	Exception, e:
				U.toLog(-1, u"in Line {} has error={}".format(sys.exc_traceback.tb_lineno, e))



	def readADCSingleEnded(self, channel=0, pga=6144, sps=250):
		try:
			"Gets a single-ended ADC reading from the specified channel in mV. \
			The sample rate for this mode (single-shot) can be used to lower the noise \
			(low sps) or to lower the power consumption (high sps) by duty cycling, \
			see datasheet page 14 for more info. \
			The pga must be given in mV, see page 13 for the supported values."

			# With invalid channel return -1
			if (channel > 3):
				if (self.debug):
					print "ADS1x15: Invalid channel specified: %d" % channel
				return -1

			# Disable comparator, Non-latching, Alert/Rdy active low
			# traditional comparator, single-shot mode
			config = self.__ADS1015_REG_CONFIG_CQUE_NONE	| \
					 self.__ADS1015_REG_CONFIG_CLAT_NONLAT	| \
					 self.__ADS1015_REG_CONFIG_CPOL_ACTVLOW | \
					 self.__ADS1015_REG_CONFIG_CMODE_TRAD	| \
					 self.__ADS1015_REG_CONFIG_MODE_SINGLE

			# Set sample per seconds, defaults to 250sps
			# If sps is in the dictionary (defined in init) it returns the value of the constant
			# othewise it returns the value for 250sps. This saves a lot of if/elif/else code!
			if (self.ic == self.__IC_ADS1015):
			  config |= self.spsADS1015.setdefault(sps, self.__ADS1015_REG_CONFIG_DR_1600SPS)
			else:
				if ( (sps not in self.spsADS1115) & self.debug):
					print "ADS1x15: Invalid pga specified: %d, using 6144mV" % sps
				config |= self.spsADS1115.setdefault(sps, self.__ADS1115_REG_CONFIG_DR_250SPS)

			# Set PGA/voltage range, defaults to +-6.144V
			if ( (pga not in self.pgaADS1x15) & self.debug):
				print "ADS1x15: Invalid pga specified: %d, using 6144mV" % sps
			config |= self.pgaADS1x15.setdefault(pga, self.__ADS1015_REG_CONFIG_PGA_6_144V)
			self.pga = pga

			# Set the channel to be converted
			if channel == 3:
				config |= self.__ADS1015_REG_CONFIG_MUX_SINGLE_3
			elif channel == 2:
				config |= self.__ADS1015_REG_CONFIG_MUX_SINGLE_2
			elif channel == 1:
				config |= self.__ADS1015_REG_CONFIG_MUX_SINGLE_1
			else:
				config |= self.__ADS1015_REG_CONFIG_MUX_SINGLE_0

			# Set 'start single-conversion' bit
			config |= self.__ADS1015_REG_CONFIG_OS_SINGLE

			# Write config register to the ADC
			bytes = [(config >> 8) & 0xFF, config & 0xFF]
			#print "channel	 bytes written: " , channel, bytes
			self._Device.writeList(self.__ADS1015_REG_POINTER_CONFIG, bytes)

			# Wait for the ADC conversion to complete
			# The minimum delay depends on the sps: delay >= 1/sps
			# We add 0.1ms to be sure
			delay = 1.0/sps+0.02
			time.sleep(delay)

			# Read the conversion results
			result = self._Device.readList(self.__ADS1015_REG_POINTER_CONVERT, 2)
			if (self.ic == self.__IC_ADS1015):
				# Shift right 4 bits for the 12-bit ADS1015 and convert to mV
				val= ( ((result[0] << 8) | (result[1] & 0xFF)) >> 4 )*pga/2048.0
				#print val, result
				return val
			else:
				# Return a mV value for the ADS1115
				# (Take signed values into account as well)
				val = (result[0] << 8) | (result[1])
				if val > 0x7FFF:
					val= (val - 0xFFFF)*pga/32768.0
				else:
					val= ( (result[0] << 8) | (result[1]) )*pga/32768.0
				#print val, result
				return val
		except	Exception, e:
				U.toLog(-1, u"in Line {} has error={}".format(sys.exc_traceback.tb_lineno, e))






# ===========================================================================
# TSL2561 Class
# ===========================================================================


class TSL2561:

	def __init__(self, address=0x39, debug=0):
		self.bus = smbus.SMBus(1)
		self.address = address
		self.debug = debug
		self.bus.write_byte_data(self.address, 0x80, 0x03)
		self.bus.write_byte_data(self.address, 0x86, 0x00)
		self.defGain	= -1
		self.defintTime = -1
		self.setGain(gain=1,intTime=102.)


	def setGain(self,gain=1,intTime=102.):
		""" Set the gain """
		if	 (gain==1  and intTime ==13.7 ) :	self.bus.write_byte_data(self.address,0x81, 0b00000100)		# set gain = 1X and timing = 14 mSec.. only up to 37k
		elif (gain==1  and intTime ==102.):		 self.bus.write_byte_data(self.address,0x81, 0b00000101)	 # set gain = 1X and timing = 101 mSec.. only up to 37k
		elif (gain==1  and intTime ==402.):		 self.bus.write_byte_data(self.address,0x81, 0b00000110)	 # set gain = 1X and timing = 402 mSec.. up to 65k, missing factor 2
		elif (gain==16 and intTime ==13.7  ):	self.bus.write_byte_data(self.address,0x81, 0b00010100)		# set gain = 16X and timing = 14 mSec.. up to 65k, missing factor 2
		elif (gain==16 and intTime ==102.):		 self.bus.write_byte_data(self.address,0x81, 0b00010101)	 # set gain = 16X and timing = 402 mSec
		elif (gain==16 and intTime ==402.):		 self.bus.write_byte_data(self.address,0x81, 0b00010110)	 # set gain = 16X and timing = 402 mSec
			

		self.defGain		= gain						   # safe gain for calculation
		self.defintTime		= intTime					   
		if intTime ==13.7: time.sleep(0.1)				# pause for integration (self.pause must be bigger than integration time)
		if intTime ==102:  time.sleep(0.6)				# pause for integration (self.pause must be bigger than integration time)
		else:			   time.sleep(0.9)

	def readFull(self, reg=0x8C):
		"""Reads visible+IR diode from the I2C device"""
		return self.bus.read_word_data(self.address,reg)

	def readIR(self, reg=0x8E):
		"""Reads IR only diode from the I2C device"""
		return self.bus.read_word_data(self.address,reg)


	def readLux(self, gain = 1):
		"""Grabs a lux reading either with autoranging (gain=0) or with a specified gain (1, 16)"""


		self.setGain(gain=16, intTime=402.)
		full = self.readFull()
		ir	 = self.readIR()
		g,i =16, 402 ## 13.7
		#print g,i, full,ir 
		if	full > 30000:
			self.setGain(gain=16, intTime=102.)
			full = self.readFull()
			ir	 = self.readIR()
			g,i =16,102
			#print g,i, full,ir 
			if	full > 20000:
				self.setGain(gain=1, intTime=102. )
				full = self.readFull()
				ir	 = self.readIR()
				g,i =1,102
				#print g,i, full,ir 
				if full > 20000:
					self.setGain(gain=1, intTime=13.7 )
					full = self.readFull()
					ir	 = self.readIR()
					g,i =1,13.7 
					#print g,i, full,ir 

		IR		= ir	   *(16*402.)/(g*i)
		ambient = max(full *(16*402.)/(g*i),0.5)
		
		
		ratio = (IR / float(ambient)) # changed to make it run under python 2
		#print IR, ambient, ratio

		if ((ratio >= 0) & (ratio <= 0.52)):
			lux = (0.0315 * ambient) - (0.0593 * ambient * (ratio**1.4))
		elif (ratio <= 0.65):
			lux = (0.0229 * ambient) - (0.0291 * IR)
		elif (ratio <= 0.80):
			lux = (0.0157 * ambient) - (0.018 * IR)
		elif (ratio <= 1.3):
			lux = (0.00338 * ambient) - (0.0026 * IR)
		elif (ratio > 1.3):
			lux = 0
		#print "===", g,i,ir,IR,full,ambient, lux

		return {"lux":lux,"IR":IR,"ambient":ambient}


# ===========================================================================
# OPT3001 Class
# ===========================================================================


class OPT3001:

	def __init__(self, address = 0x44):
		try:
			self._DeviceAddress = address
			self.bus = smbus.SMBus(1)
					 #5432109876543210
			bits  = 0b1100000000000000	# enable auto  mode
			bits |= 0b0000100000000000	# 800 msec convtime 
			bits |= 0b0000011000000000	# continuous conversion
			self.readReset		 = struct.pack("BBB",0x01,0b11001010,0b00000000)
			self.readStartSingle = struct.pack("BBB",0x01,0b11000010,0b00000000)  # 100 msec conv time
			self.setLowLimit	 = struct.pack("BBB",0x02,0b00000000,0b00000000)
			self.setHihLimit	 = struct.pack("BBB",0x03,0b10111111,0b11111111)

			self.simpleRW = U.simpleI2cReadWrite( self._DeviceAddress,1)
			self.simpleRW.write(self.readStartSingle)
			self.simpleRW.write(self.setLowLimit)
			self.simpleRW.write(self.setHihLimit)
			time.sleep(0.8)
		except	Exception, e:
			U.toLog(-1, u"in Line {} has error={}".format(sys.exc_traceback.tb_lineno, e))

	def readLux(self):
		try:
			nn = 0
			while True:
				nn+=1
				self.simpleRW.write(self.readStartSingle)  # normal write_word seems not to work ,always 0 
				self.simpleRW.write(self.setLowLimit)
				self.simpleRW.write(self.setHihLimit)
				time.sleep(0.15)
				result = self.bus.read_word_data(self._DeviceAddress,0x00)
				r1 = (result&0xff00) >> 8
				r0 = (result&0x00ff) 
				#### bytes are flipped top byte is 0 and bottom byte is 1!!!!
				exp	   = (r0&0xF0 )>>4	 # first 4 bits of botton byte
				b1	   = (r1	  )>>8	 # botton 12 bits
				b2	   = (r0&0x0F )<<8	 # botton 12 bits
				base   = b1 + b2	  
				lux	   = ((base << exp)*0.01) # base * 2**exp  * 0.01 lux 
				if (exp > 11 or lux > 83865.60) and nn < 10: continue  #out of bounce?
				return lux
		except	Exception, e:
			U.toLog(-1, u"in Line {} has error={}".format(sys.exc_traceback.tb_lineno, e))
			self.simpleRW.write(self.readStartSingle)
			self.simpleRW.write(self.setLowLimit)
			self.simpleRW.write(self.setHihLimit)
		return ""



# ===========================================================================
# TCS34725 Class
# ===========================================================================



class TCS34725:
	i2c = None

	__TCS34725_ADDRESS			= 0x29
	__TCS34725_ID				= 0x12 # 0x44 = TCS34721/TCS34725, 0x4D = TCS34723/TCS34727

	__TCS34725_COMMAND_BIT		= 0x80

	__TCS34725_ENABLE			= 0x00
	__TCS34725_ENABLE_AIEN		= 0x10 # RGBC Interrupt Enable
	__TCS34725_ENABLE_WEN		= 0x08 # Wait enable - Writing 1 activates the wait timer
	__TCS34725_ENABLE_AEN		= 0x02 # RGBC Enable - Writing 1 actives the ADC, 0 disables it
	__TCS34725_ENABLE_PON		= 0x01 # Power on - Writing 1 activates the internal oscillator, 0 disables it
	__TCS34725_ATIME			= 0x01 # Integration time
	__TCS34725_WTIME			= 0x03 # Wait time (if TCS34725_ENABLE_WEN is asserted)
	__TCS34725_WTIME_2_4MS		= 0xFF # WLONG0 = 2.4ms	  WLONG1 = 0.029s
	__TCS34725_WTIME_204MS		= 0xAB # WLONG0 = 204ms	  WLONG1 = 2.45s
	__TCS34725_WTIME_614MS		= 0x00 # WLONG0 = 614ms	  WLONG1 = 7.4s
	__TCS34725_AILTL			= 0x04 # Clear channel lower interrupt threshold
	__TCS34725_AILTH			= 0x05
	__TCS34725_AIHTL			= 0x06 # Clear channel upper interrupt threshold
	__TCS34725_AIHTH			= 0x07
	__TCS34725_PERS				= 0x0C # Persistence register - basic SW filtering mechanism for interrupts
	__TCS34725_PERS_NONE		= 0b0000 # Every RGBC cycle generates an interrupt
	__TCS34725_PERS_1_CYCLE		= 0b0001 # 1 clean channel value outside threshold range generates an interrupt
	__TCS34725_PERS_2_CYCLE		= 0b0010 # 2 clean channel values outside threshold range generates an interrupt
	__TCS34725_PERS_3_CYCLE		= 0b0011 # 3 clean channel values outside threshold range generates an interrupt
	__TCS34725_PERS_5_CYCLE		= 0b0100 # 5 clean channel values outside threshold range generates an interrupt
	__TCS34725_PERS_10_CYCLE	= 0b0101 # 10 clean channel values outside threshold range generates an interrupt
	__TCS34725_PERS_15_CYCLE	= 0b0110 # 15 clean channel values outside threshold range generates an interrupt
	__TCS34725_PERS_20_CYCLE	= 0b0111 # 20 clean channel values outside threshold range generates an interrupt
	__TCS34725_PERS_25_CYCLE	= 0b1000 # 25 clean channel values outside threshold range generates an interrupt
	__TCS34725_PERS_30_CYCLE	= 0b1001 # 30 clean channel values outside threshold range generates an interrupt
	__TCS34725_PERS_35_CYCLE	= 0b1010 # 35 clean channel values outside threshold range generates an interrupt
	__TCS34725_PERS_40_CYCLE	= 0b1011 # 40 clean channel values outside threshold range generates an interrupt
	__TCS34725_PERS_45_CYCLE	= 0b1100 # 45 clean channel values outside threshold range generates an interrupt
	__TCS34725_PERS_50_CYCLE	= 0b1101 # 50 clean channel values outside threshold range generates an interrupt
	__TCS34725_PERS_55_CYCLE	= 0b1110 # 55 clean channel values outside threshold range generates an interrupt
	__TCS34725_PERS_60_CYCLE	= 0b1111 # 60 clean channel values outside threshold range generates an interrupt
	__TCS34725_CONFIG			= 0x0D
	__TCS34725_CONFIG_WLONG		= 0x02 # Choose between short and long (12x) wait times via TCS34725_WTIME
	__TCS34725_CONTROL			= 0x0F # Set the gain level for the sensor
	__TCS34725_ID				= 0x12 # 0x44 = TCS34721/TCS34725, 0x4D = TCS34723/TCS34727
	__TCS34725_STATUS			= 0x13
	__TCS34725_STATUS_AINT		= 0x10 # RGBC Clean channel interrupt
	__TCS34725_STATUS_AVALID	= 0x01 # Indicates that the RGBC channels have completed an integration cycle

	__TCS34725_CDATAL			= 0x14 # Clear channel data
	__TCS34725_CDATAH			= 0x15
	__TCS34725_RDATAL			= 0x16 # Red channel data
	__TCS34725_RDATAH			= 0x17
	__TCS34725_GDATAL			= 0x18 # Green channel data
	__TCS34725_GDATAH			= 0x19
	__TCS34725_BDATAL			= 0x1A # Blue channel data
	__TCS34725_BDATAH			= 0x1B

	__TCS34725_INTEGRATIONTIME_2_4MS  = 0xFF   #  2.4ms - 1 cycle	 - Max Count: 1024
	__TCS34725_INTEGRATIONTIME_24MS	  = 0xF6   # 24ms  - 10 cycles	- Max Count: 10240
	__TCS34725_INTEGRATIONTIME_50MS	  = 0xEB   #  50ms	- 20 cycles	 - Max Count: 20480
	__TCS34725_INTEGRATIONTIME_101MS  = 0xD5   #  101ms - 42 cycles	 - Max Count: 43008
	__TCS34725_INTEGRATIONTIME_154MS  = 0xC0   #  154ms - 64 cycles	 - Max Count: 65535
	__TCS34725_INTEGRATIONTIME_700MS  = 0x00   #  700ms - 256 cycles - Max Count: 65535

	__TCS34725_GAIN_1X					= 0x00	 #	No gain
	__TCS34725_GAIN_4X					= 0x01	 #	2x gain
	__TCS34725_GAIN_16X					= 0x02	 #	16x gain
	__TCS34725_GAIN_60X					= 0x03	 #	60x gain

	__integrationTimeDelay = {
		0xFF: 0.0024,  # 2.4ms - 1 cycle	- Max Count: 1024
		0xF6: 0.024,   # 24ms  - 10 cycles	- Max Count: 10240
		0xEB: 0.050,   # 50ms  - 20 cycles	- Max Count: 20480
		0xD5: 0.101,   # 101ms - 42 cycles	- Max Count: 43008
		0xC0: 0.154,   # 154ms - 64 cycles	- Max Count: 65535
		0x00: 0.700	   # 700ms - 256 cycles - Max Count: 65535
	}

	# Private Methods
	def __readU8(self, reg):
		return self._Device.readU8(self.__TCS34725_COMMAND_BIT | reg)

	def __readU16Rev(self, reg):
		return self._Device.readU16Rev(self.__TCS34725_COMMAND_BIT | reg)

	def __write8(self, reg, value):
		self._Device.write8(self.__TCS34725_COMMAND_BIT | reg, value & 0xff)

	# Constructor
	def __init__(self, address=0x29, debug=False, integrationTime=0xFF, gain=0x01):
		self._Device = Adafruit_I2C(address)

		self.address = address
		self.debug = debug
		self.integrationTime = integrationTime
		self.initialize(integrationTime, gain)

	def initialize(self, integrationTime, gain):
		"Initializes I2C and configures the sensor (call this function before \
		doing anything else)"
		# Make sure we're actually connected
		result = self.__readU8(self.__TCS34725_ID)
		if (result != 0x44):
			return -1

		# Set default integration time and gain
		self.setIntegrationTime(integrationTime)
		self.setGain(gain)

		# Note: by default, the device is in power down mode on bootup
		self.enable()

	def enable(self):
		self.__write8(self.__TCS34725_ENABLE, self.__TCS34725_ENABLE_PON)
		time.sleep(0.01)
		self.__write8(self.__TCS34725_ENABLE, (self.__TCS34725_ENABLE_PON | self.__TCS34725_ENABLE_AEN))

	def disable(self):
		reg = 0
		reg = self.__readU8(self.__TCS34725_ENABLE)
		self.__write8(self.__TCS34725_ENABLE, (reg & ~(self.__TCS34725_ENABLE_PON | self.__TCS34725_ENABLE_AEN)))

	def setIntegrationTime(self, integrationTime):
		"Sets the integration time for the TC34725"
		self.integrationTime = integrationTime

		self.__write8(self.__TCS34725_ATIME, integrationTime)

	def getIntegrationTime(self):
		return self.__readU8(self.__TCS34725_ATIME)

	def setGain(self, gain):
		"Adjusts the gain on the TCS34725 (adjusts the sensitivity to light)"
		self.__write8(self.__TCS34725_CONTROL, gain)

	def getGain(self):
		return self.__readU8(self.__TCS34725_CONTROL)

	def getRawData(self):
		"Reads the raw red, green, blue and clear channel values"

		color = {}

		color["r"] = self.__readU16Rev(self.__TCS34725_RDATAL)
		color["b"] = self.__readU16Rev(self.__TCS34725_BDATAL)
		color["g"] = self.__readU16Rev(self.__TCS34725_GDATAL)
		color["c"] = self.__readU16Rev(self.__TCS34725_CDATAL)

		# Set a delay for the integration time
		delay = self.__integrationTimeDelay.get(self.integrationTime)
		time.sleep(delay)

		return color

	def setInterrupt(self, int):
		r = self.__readU8(self.__TCS34725_ENABLE)

		if (int):
			r |= self.__TCS34725_ENABLE_AIEN
		else:
			r &= ~self.__TCS34725_ENABLE_AIEN

		self.__write8(self.__TCS34725_ENABLE, r)

	def clearInterrupt(self):
		self._Device.write8(self.__TCS34725_ENABLE, 0x66 & 0xff)

	def setIntLimits(self, low, high):
		self._Device.write8(0x04, low & 0xFF)
		self._Device.write8(0x05, low >> 8)
		self._Device.write8(0x06, high & 0xFF)
		self._Device.write8(0x07, high >> 8)

	#Static Utility Methods
	@staticmethod
	def calculateColorTemperature(rgb):
		"Converts the raw R/G/B values to color temperature in degrees Kelvin"

		if not isinstance(rgb, dict):
			raise ValueError('calculateColorTemperature expects dict as parameter')

		# 1. Map RGB values to their XYZ counterparts.
		# Based on 6500K fluorescent, 3000K fluorescent
		# and 60W incandescent values for a wide range.
		# Check for divide by 0 (total darkness) and return None.
			# Note: Y = Illuminance or lux
		X = (-0.14282 * rgb['r']) + (1.54924 * rgb['g']) + (-0.95641 * rgb['b'])
		Y = (-0.32466 * rgb['r']) + (1.57837 * rgb['g']) + (-0.73191 * rgb['b'])
		Z = (-0.68202 * rgb['r']) + (0.77073 * rgb['g']) + (0.56332 * rgb['b'])

		if (X + Y + Z) == 0:
			return None

		# 2. Calculate the chromaticity co-ordinates
		xc = (X) / (X + Y + Z)
		yc = (Y) / (X + Y + Z)

		# Check for divide by 0 again and return None.
		if (0.1858 - yc) == 0:
			return None

		# 3. Use McCamy's formula to determine the CCT
		n = (xc - 0.3320) / (0.1858 - yc)

		# Calculate the final CCT
		cct = (449.0 * (n ** 3.0)) + (3525.0 *(n ** 2.0)) + (6823.3 * n) + 5520.33

		return int(cct)

	@staticmethod
	def calculateLux(rgb):
		"Converts the raw R/G/B values to color temperature in degrees Kelvin"

		if not isinstance(rgb, dict):
			raise ValueError('calculateLux expects dict as parameter')

		illuminance = (-0.32466 * rgb['r']) + (1.57837 * rgb['g']) + (-0.73191 * rgb['b'])

		return int(illuminance)


		
# ===========================================================================
# SHT21
# ===========================================================================
class SHT21:

	def __init__(self,i2cAdd= 0x40):
		self._SOFTRESET					  = 0xFE
		self._TRIGGER_TEMPERATURE_NO_HOLD = 0xF3
		self._TRIGGER_HUMIDITY_NO_HOLD	  = 0xF5
		# load simple i2c write, regular i2c read does not work.. only send address then read xbytes, no register, no 2* 1 byte read 
		self.sens = U.simpleI2cReadWrite(i2cAdd,1)

		"""According to the datasheet the soft reset takes less than 15 ms."""
		self.sens.write(struct.pack("B",self._SOFTRESET))
		time.sleep(0.02)

	def read_temperature(self):	   
		try:
			self.sens.write(struct.pack("B",self._TRIGGER_TEMPERATURE_NO_HOLD))
			time.sleep(0.25)
			data = struct.unpack('2B',self.sens.read(2))
			"""read 2 bytes of data (ignore byte 3 = check sum) 
			T = 46.82 + (172.72 * (data/2^16))
			"""
			temp  = (data[0] << 8) + data[1]
			temp *= 175.72
			temp /= 1 << 16 
			temp -= 46.85
			return temp
		except	Exception, e:
			U.toLog(-1, u"in Line {} has error={}".format(sys.exc_traceback.tb_lineno, e))
		return ""
		

	def read_humidity(self):   
		try: 
			self.sens.write(struct.pack("B",self._TRIGGER_HUMIDITY_NO_HOLD))
			time.sleep(0.25)
			data = struct.unpack('2B',self.sens.read(2))
			"""read 2 bytes of data (ignore byte 3 = check sum) 
			RH in percent:
			RH = -6 + (125 * (data / 2 ^16))
			"""
			hum	 = (data[0] << 8) + data[1]
			hum *= 125
			hum /= 1 << 16 
			hum -= 6
			return min(hum,100.)
		except	Exception, e:
			U.toLog(-1, u"in Line {} has error={}".format(sys.exc_traceback.tb_lineno, e))
		return ""
		




# ===========================================================================
# LM75A
# ===========================================================================
class LM75A:
	# By default the address of LM75A is set to 0x48
	# aka A0, A1, and A2 are set to GND (0v).
	address = 0x48


	def __init__(self, i2cAdd):
		self._DeviceAddress = i2cAdd
		self.bus = smbus.SMBus(1)
		time.sleep(0.015)

	def read_temperature(self):	   
		"""Reads the temperature from the sensor.  Not that this call blocks
		for 250ms to allow the sensor to return the data"""
		data = []
		raw = self.bus.read_word_data(self._DeviceAddress,0x0) & 0xFFFF
		raw = ((raw << 8) & 0xFF00) + (raw >> 8)
		return (raw / 32.0) / 8.0
		 
				

# ===========================================================================
# AM2320
# ===========================================================================

# from IoTPy.errors import IoTPy_ThingError




class CommunicationError(Exception):
	pass


class AM2320:
	"""
	AM2320 temperature and humidity sensor class.
	:param interface:  I2C interface id.
	:type interface: :int
	:param sensor_address: AM2320 sensor I2C address. Optional, default 0x5C (92).
	:type sensor_address: int
	"""

	def __init__(self, i2cAdd=0x5c):
		self._Device_address = i2cAdd
		self.bus = smbus.SMBus(1)
		self.PARAM_AM2320_READ = 0x03
		self.REG_AM2320_HUMIDITY_MSB = 0x00 # not used
		self.REG_AM2320_HUMIDITY_LSB = 0x01 # not used
		self.REG_AM2320_TEMPERATURE_MSB = 0x02
		self.REG_AM2320_TEMPERATURE_LSB = 0x03 # not used
		self.REG_AM2320_DEVICE_ID_BIT_24_31 = 0x0B

	def _read_raw(self, command, regaddr, regcount):
		try:
			# need to read twice then it works	 , no clue why
			try:	 self.bus.write_i2c_block_data(self._Device_address, 0x00, [])
				#self.bus.write_i2c_block_data(self._Device_address, command, [regaddr, regcount])
			except:	  pass
			time.sleep(0.01)
			self.bus.write_i2c_block_data(self._Device_address, 0x00, [])
			self.bus.write_i2c_block_data(self._Device_address, command, [regaddr, regcount])
			time.sleep(0.002)

			buf = self.bus.read_i2c_block_data(self._Device_address, 0, 8)
 
			buf_str = "".join(chr(x) for x in buf)

			crc = struct.unpack('<H', buf_str[-2:])[0]
			if crc != self._am_crc16(buf[:-2]):
				raise CommunicationError("AM2320 CRC error.")
			return buf_str[2:-2]
		except	Exception, e:
				U.toLog(-1, u"in Line {} has error={}".format(sys.exc_traceback.tb_lineno, e))
		return "	"

	def _am_crc16(self, buf):
		crc = 0xFFFF
		for c in buf:
			crc ^= c
			for i in range(8):
				if crc & 0x01:
					crc >>= 1
					crc ^= 0xA001
				else:
					crc >>= 1
		return crc

	def read_uid(self):	 # not used
		"""
		Read and return unique 32bit sensor ID.
		:return: A unique 32bit sensor ID.
		:rtype: int
		"""
		resp = self._read_raw(self.PARAM_AM2320_READ, self.REG_AM2320_DEVICE_ID_BIT_24_31, 4)
		uid = struct.unpack('>I', resp)[0]
		return uid

	def read(self):
		"""
		Read and store temperature and humidity value.
		Read temperature and humidity registers from the sensor, then convert and store them.
		Use :func:`temperature` and :func:`humidity` to retrieve these values.
		"""
		t,h="",""
		try:
			raw_data = self._read_raw(self.PARAM_AM2320_READ, self.REG_AM2320_HUMIDITY_MSB, 4)
			t = struct.unpack('>H', raw_data[-2:])[0] / 10.0
			h = struct.unpack('>H', raw_data[-4:2])[0] / 10.0
		except	Exception, e:
				U.toLog(-1, u"in Line {} has error={}".format(sys.exc_traceback.tb_lineno, e))
				U.toLog(-1, u"return  value: t="+ unicode(t)+"; h="+ unicode(h)	 )
		return t,h


# ===========================================================================
# MCP9808
# ===========================================================================
# Copyright (c) 2014 Adafruit Industries
# Author: Tony DiCola
#
# Permission is hereby granted, free of charge, to any person obtaining a copy
# of this software and associated documentation files (the "Software"), to deal
# in the Software without restriction, including without limitation the rights
# to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
# copies of the Software, and to permit persons to whom the Software is
# furnished to do so, subject to the following conditions:
#
# The above copyright notice and this permission notice shall be included in
# all copies or substantial portions of the Software.
#
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
# IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
# FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
# AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
# LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
# OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN
# THE SOFTWARE.




class MCP9808:
	"""Class to represent an Adafruit MCP9808 precision temperature measurement
	board.
	"""
	# Default I2C address for device.
	MCP9808_I2CADDR_DEFAULT		   = 0x18

	# Register addresses.
	MCP9808_REG_CONFIG			   = 0x01
	MCP9808_REG_UPPER_TEMP		   = 0x02
	MCP9808_REG_LOWER_TEMP		   = 0x03
	MCP9808_REG_CRIT_TEMP		   = 0x04
	MCP9808_REG_AMBIENT_TEMP	   = 0x05
	MCP9808_REG_MANUF_ID		   = 0x06
	MCP9808_REG_DEVICE_ID		   = 0x07

	# Configuration register values.
	MCP9808_REG_CONFIG_SHUTDOWN	   = 0x0100
	MCP9808_REG_CONFIG_CRITLOCKED  = 0x0080
	MCP9808_REG_CONFIG_WINLOCKED   = 0x0040
	MCP9808_REG_CONFIG_INTCLR	   = 0x0020
	MCP9808_REG_CONFIG_ALERTSTAT   = 0x0010
	MCP9808_REG_CONFIG_ALERTCTRL   = 0x0008
	MCP9808_REG_CONFIG_ALERTSEL	   = 0x0002
	MCP9808_REG_CONFIG_ALERTPOL	   = 0x0002
	MCP9808_REG_CONFIG_ALERTMODE   = 0x0001

	def __init__(self, address=0x18):
		"""Initialize MCP9808 device on the specified I2C address and bus number.
		Address defaults to 0x18 and bus number defaults to the appropriate bus
		for the hardware.
		"""
		self._device = Adafruit_I2C(address)


	def begin(self):
		"""Start taking temperature measurements. Returns True if the device is 
		intialized, False otherwise.
		"""
		# Check manufacturer and device ID match expected values.
		mid = self._device.readU16BE(self.MCP9808_REG_MANUF_ID)
		did = self._device.readU16BE(self.MCP9808_REG_DEVICE_ID)
		U.toLog(3,'Read manufacturer ID: {0:04X}'.format(mid))
		U.toLog(3,'Read device ID: {0:04X}'.format(did))
		return mid == 0x0054 and did == 0x0400

	def readTempC(self):
		"""Read sensor and return its value in degrees celsius."""
		# Read temperature register value.
		t = self._device.readU16BE(self.MCP9808_REG_AMBIENT_TEMP)
		U.toLog(3,'Raw ambient temp register value: 0x{0:04X}'.format(t & 0xFFFF))
		# Scale and convert to signed value.
		temp = (t & 0x0FFF) / 16.0
		if t & 0x1000:
			temp -= 256.0
		return temp




# ===========================================================================
# VEML6030
# ===========================================================================


class VEML6030:
	# With ADDR pin plugged to power supply = high = VDD : address = 0x48
	# With ADDR pin plugged to ground = low :			   address = 0x10
	VEML6030_I2C_ADDRESS   = 0x10

	# REGISTER 00H SETTINGS
	#Sensitivity mode selection (BIT 12:11)
	VEML6030_SM0		   = 0b0000000000000000
	VEML6030_SM1		   = 0b0000100000000000
	VEML6030_SM2		   = 0b0001000000000000
	VEML6030_SM3		   = 0b0001100000000000

	#ALS integration time setting (BIT 9:6)
	VEML6030_IT_25MS	   = 0b0000001100000000
	VEML6030_IT_50MS	   = 0b0000001000000000
	VEML6030_IT_100MS	   = 0b0000000000000000
	VEML6030_IT_200MS	   = 0b0000000001000000
	VEML6030_IT_400MS	   = 0b0000000010000000
	VEML6030_IT_800MS	   = 0b0000000011000000
	integrationTimeBits	   = [[	 "25",VEML6030_IT_25MS,0.25],
							  [	 "50",VEML6030_IT_50MS,0.5],
							  [ "100",VEML6030_IT_100MS,1.],
							  [ "200",VEML6030_IT_200MS,2.],
							  [ "400",VEML6030_IT_400MS,4.],
							  [ "800",VEML6030_IT_800MS,8.]]
	integrationTimeGainFactor  = 0.0576 # for integration time = 100, gain =1, rest is multiply
	#ALS integration time setting (BIT 12:11)
	VEML6030_Gain_1		   = 0b0000000000000000
	VEML6030_Gain_2		   = 0b0000100000000000
	VEML6030_Gain_1_8	   = 0b0001000000000000
	VEML6030_Gain_1_4	   = 0b0001100000000000
	gainBits			   = [["1/8", VEML6030_Gain_1_8,0.125],
							  ["1/4", VEML6030_Gain_1_4,0.25],
							  [	 "1", VEML6030_Gain_1,1.0],
							  [	 "2", VEML6030_Gain_2,2.0]]



	#ALS persistence protect number setting (BIT 5:4)
	VEML6030_PERS0		   = 0b0000000000000000
	VEML6030_PERS1		   = 0b0000000000010000
	VEML6030_PERS2		   = 0b0000000000100000
	VEML6030_PERS3		   = 0b0000000000110000

	#ALS interrupt enable setting (BIT 1)
	VEML6030_INT_DISABLE   = 0b0000000000000000
	VEML6030_INT_ENABLE	   = 0b0000000000000010

	#ALS shut down setting (BIT 0)
	VEML6030_SD_ENABLE	   = 0b0000000000000000
	VEML6030_SD_DISABLE	   = 0b0000000000000001

	# REGISTER 03H SETTINGS
	#Power saving mode
	VEML6030_Mode0		  = 0x0000
	VEML6030_Mode1		  = 0x0020
	VEML6030_Mode2		  = 0x0040
	VEML6030_Mode3		  = 0x0060
	VEML6030_PSM_DISABLE  = 0x0001
	VEML6030_PSM_ENABLE	  = 0x0000

	# COMMAND CODES
	COMMAND_CODE_CONF	  = 0x00
	COMMAND_CODE_WH		  = 0x01 #ALS high threshold window setting
	COMMAND_CODE_WL		  = 0x02 #ALS low threshold window setting
	COMMAND_CODE_PSM	  = 0x03 #Power saving mode (BIT :0)
	COMMAND_CODE_ALS	  = 0x04 #whole ALS 16 bits
	COMMAND_CODE_WHITE	  = 0x05 #whole WHITE 16 bits
	COMMAND_CODE_IF		  = 0x06 #ALS crossing low/high threshold INT trigger event(BIT 15:14)



	def __init__(self,address=""):
		U.setStopCondition(on=True)

		if address =="":
			self._DeviceAddress = self.VEML6030_I2C_ADDRESS 
		else:
			self._DeviceAddress	 =	 address  
		self.bus = smbus.SMBus(1)
		# disable power save mode
		self.bus.write_word_data(self._DeviceAddress,self.COMMAND_CODE_PSM,self.VEML6030_PSM_DISABLE)


		self.minWaitTime=0.75
		self.minResult = 400
		self.maxResult = 20000
		self.gainLast  = 2
		self.itLast	   = 1
		
	def getLight(self):
		try:
			alsData	  = [0,0,0]
			whiteData = [0,0,0]
			alsDataL   = [0,0,0]
			whiteDataL = [0,0,0]
			for ii in range(3):
				# Loop for polling
				gain = self.gainLast
				IT	 = self.itLast
				configuration	= self.VEML6030_SM0 | self.integrationTimeBits[IT][1] | self.gainBits[gain][1] | self.VEML6030_PERS0 | self.VEML6030_INT_DISABLE | self.VEML6030_SD_ENABLE
				waitTime = self.minWaitTime + self.integrationTimeBits[IT][2]/10.
				factor= self.integrationTimeGainFactor /( self.gainBits[gain][2] * self.integrationTimeBits[IT][2])
				#print "trying: gain=",gain, "IT=",IT,"factor", factor, "waitTime",waitTime
				self.bus.write_word_data(self._DeviceAddress,self.COMMAND_CODE_CONF, configuration)
				time.sleep(waitTime)


				#count should be between 400 and 20,000, if not adjust gain and int time after first measurement 

				while True:
					alsData[ii]			= self.bus.read_word_data(self._DeviceAddress,self.COMMAND_CODE_ALS)
					whiteData[ii]		= self.bus.read_word_data(self._DeviceAddress,self.COMMAND_CODE_WHITE)
					alsDataL[ii]		= alsData[ii]*factor
					whiteDataL[ii]		= whiteData[ii]*factor
					#print	"result:",alsData[ii],alsDataL[ii], whiteData[ii], whiteDataL[ii]
					if alsData[ii] < self.minResult: 
						multF = int(self.minResult/max(alsData[ii],0.01))+1
						if gain == 3:
							if IT ==5: break
							IT =min(multF,5)
						else: 
							left = multF - (3-gain)
							if gain == min(multF,3): gain +=1
							else:
								gain = min(multF,3)
							if left >1:
								if IT == min(IT+left,5):
									IT = min(IT+left+1,5)
								else:
									IT =min(IT+left,5)
					elif alsData[ii] > self.maxResult: 
						if IT ==0: 
							if gain == 0:break
							gain = max(gain-3,0)
						else: 
							IT =max(IT-3,0)
					else:
						break
					configuration	= self.VEML6030_SM0 | self.integrationTimeBits[IT][1] | self.gainBits[gain][1] | self.VEML6030_PERS0 | self.VEML6030_INT_DISABLE | self.VEML6030_SD_ENABLE
					waitTime = self.minWaitTime + self.integrationTimeBits[IT][2]/10.
					factor= self.integrationTimeGainFactor /( self.gainBits[gain][2] * self.integrationTimeBits[IT][2])
					#print "trying: gain=",gain, "IT=",IT,"factor", factor, "waitTime",waitTime
					self.bus.write_word_data(self._DeviceAddress,self.COMMAND_CODE_CONF, configuration)
					time.sleep(waitTime)
				if ii==1: # skip 3. round?
					if abs(alsDataL[0]-alsDataL[1])/max(0.1,alsDataL[0]+alsDataL[1]) < 0.05: break
				self.gainLast = gain
				self.itLast	  = IT 
			
			## pick the middle value of the three values
			##print	 "end result:",alsData,alsDataL, whiteData, whiteDataL
			A = sorted(alsDataL)[1]
			W = sorted(whiteDataL)[1]
			#print A,W
			return	A,W
		except	Exception, e:
			U.toLog(-1, u"in Line {} has error={}".format(sys.exc_traceback.tb_lineno, e))
		return "",""


# ===========================================================================
# VEML7700
# ===========================================================================


class VEML7700:
	# With ADDR pin plugged to power supply = high = VDD : address = 0x48
	# With ADDR pin plugged to ground = low :			   address = 0x10
	VEML7700_I2C_ADDRESS   = 0x10


	#ALS integration time setting (BIT 9:6)
	VEML7700_IT_25MS	   = 0b0000001100000000
	VEML7700_IT_50MS	   = 0b0000001000000000
	VEML7700_IT_100MS	   = 0b0000000000000000
	VEML7700_IT_200MS	   = 0b0000000001000000
	VEML7700_IT_400MS	   = 0b0000000010000000
	VEML7700_IT_800MS	   = 0b0000000011000000
	integrationTimeBits	   = [[	 "25",VEML7700_IT_25MS,0.25],
							  [	 "50",VEML7700_IT_50MS,0.5],
							  [ "100",VEML7700_IT_100MS,1.],
							  [ "200",VEML7700_IT_200MS,2.],
							  [ "400",VEML7700_IT_400MS,4.],
							  [ "800",VEML7700_IT_800MS,8.]]
							  
	integrationTimeGainFactor  = 0.0576 # for integration time = 100, gain =1, rest is multiply

	#ALS integration time setting (BIT 12:11)
	VEML7700_Gain_1		   = 0b0000000000000000
	VEML7700_Gain_2		   = 0b0000100000000000
	VEML7700_Gain_1_8	   = 0b0001000000000000
	VEML7700_Gain_1_4	   = 0b0001100000000000
	gainBits			   = [["1/8", VEML7700_Gain_1_8,0.125],
							  ["1/4", VEML7700_Gain_1_4,0.25],
							  [	 "1", VEML7700_Gain_1,1.0],
							  [	 "2", VEML7700_Gain_2,2.0]]



	#ALS interrupt enable setting (BIT 1)
	VEML7700_INT_DISABLE   = 0b0000000000000000
	VEML7700_INT_ENABLE	   = 0b0000000000000010


	# REGISTER 03H SETTINGS
	#Power saving mode
	VEML7700_Mode0		  = 0x0000 #  use this , is fastest 
	VEML7700_Mode1		  = 0x0020
	VEML7700_Mode2		  = 0x0040
	VEML7700_Mode3		  = 0x0060
	VEML7700_PSM_DISABLE  = 0x0001
	VEML7700_PSM_ENABLE	  = 0x0000

	# COMMAND CODES
	COMMAND_CODE_CONF	  = 0x00
	COMMAND_CODE_WH		  = 0x01 #ALS high threshold window setting
	COMMAND_CODE_WL		  = 0x02 #ALS low threshold window setting
	COMMAND_CODE_PSM	  = 0x03 #Power saving mode (BIT :0)
	COMMAND_CODE_ALS	  = 0x04 #whole ALS 16 bits
	COMMAND_CODE_WHITE	  = 0x05 #whole WHITE 16 bits
	COMMAND_CODE_IF		  = 0x06 #ALS crossing low/high threshold INT trigger event(BIT 15:14)



	def __init__(self,address=""):
		U.setStopCondition(on=True)

		if address =="":
			self._DeviceAddress = self.VEML7700_I2C_ADDRESS 
		else:
			self._DeviceAddress	 =	 address  
		self.bus = smbus.SMBus(1)
		# disable power save mode ... 


		self.minWaitTime=0.65
		self.minResult = 200
		self.maxResult = 20000
		self.gainLast  = 0
		self.itLast	   = 0
		configuration	= self. VEML7700_Mode0 | self.integrationTimeBits[self.itLast][1] | self.gainBits[self.gainLast][1] | self.VEML7700_INT_DISABLE 
		self.bus.write_word_data(self._DeviceAddress,self.COMMAND_CODE_CONF, configuration)
		
	def getLight(self):
		try:
			alsData	  = [0,0,0]
			whiteData = [0,0,0]
			alsDataL   = [0,0,0]
			whiteDataL = [0,0,0]
			for ii in range(3):
				# Loop for polling
				gain = self.gainLast
				IT	 = self.itLast
				configuration	= self.integrationTimeBits[IT][1] | self.gainBits[gain][1] | self.VEML7700_INT_DISABLE 
				waitTime = self.minWaitTime + self.integrationTimeBits[IT][2]*0.1
				factor= self.integrationTimeGainFactor /( self.gainBits[gain][2] * self.integrationTimeBits[IT][2])
				self.bus.write_word_data(self._DeviceAddress,self.COMMAND_CODE_CONF, configuration)
				time.sleep(waitTime)


				#count should be between 400 and 20,000, if not adjust gain and int time after first measurement 

				gainLast = -10
				ITLast	 = -10
				for kkk in range(5):
					if gainLast == gain and ITLast == IT: break
					gainLast = gain
					ITLast	 = IT
					##print kkk," trying: gain=",gain, "IT=",IT,"factor", factor, "waitTime",waitTime
					alsData[ii]			= self.bus.read_word_data(self._DeviceAddress,self.COMMAND_CODE_ALS)
					whiteData[ii]		= self.bus.read_word_data(self._DeviceAddress,self.COMMAND_CODE_WHITE)
					alsDataL[ii]		= alsData[ii]*factor
					whiteDataL[ii]		= whiteData[ii]*factor
					##print	 "result:",alsData[ii],alsDataL[ii], whiteData[ii], whiteDataL[ii]
					if alsData[ii] < self.minResult: 
						multF = int(self.minResult/max(alsData[ii],0.01))+1
						if gain == 3:
							if IT ==5: break
							IT =min(multF,5)
						else: 
							left = multF - (3-gain)
							if gain == min(multF,3): gain +=1
							else:
								gain = min(multF,3)
							if left >1:
								if IT == min(IT+left,5):
									IT = min(IT+left+1,5)
								else:
									IT =min(IT+left,5)
					elif alsData[ii] > self.maxResult: 
						if IT ==0: 
							if gain == 0:break
							gain = max(gain-3,0)
						else: 
							IT =max(IT-3,0)
					else:
						break
					configuration	=  self.integrationTimeBits[IT][1] | self.gainBits[gain][1] |  self.VEML7700_INT_DISABLE 
					waitTime = self.minWaitTime + self.integrationTimeBits[IT][2]/10.
					factor= self.integrationTimeGainFactor /( self.gainBits[gain][2] * self.integrationTimeBits[IT][2])
					#print "2 trying: gain=",gain, "IT=",IT,"factor", factor, "waitTime",waitTime
					self.bus.write_word_data(self._DeviceAddress,self.COMMAND_CODE_CONF, configuration)
					time.sleep(waitTime)
				if ii==1: # skip 3. round?
					if abs(alsDataL[0]-alsDataL[1])/max(0.1,alsDataL[0]+alsDataL[1]) < 0.1: break
				self.gainLast = gain
				self.itLast	  = IT 
			
			## pick the middle value of the three values
			##print	 "end result:",alsData,alsDataL, whiteData, whiteDataL
			A = sorted(alsDataL)[1]
			W = sorted(whiteDataL)[1]
			##print A,W
			return	A,W
		except	Exception, e:
			U.toLog(-1, u"in Line {} has error={}".format(sys.exc_traceback.tb_lineno, e))
		return "",""



# ===========================================================================
# VEML6075
# ===========================================================================


class VEML6075:
	# VEML6075 slave address 
	ADDR			   =0x10 

	# Registers define 
	REG				   =0x00
	UVA_DATA_REG	   =0x07
	UVB_DATA_REG	   =0x09
	UVCOMP1_DATA_REG   =0x0A
	UVCOMP2_DATA_REG   =0x0B
	ID_REG			   =0x0C

	# Register value define : CONF 
	
	SD			  =0b00000001
	UV_AF_AUTO	  =0b00000000
	UV_AF_FORCE	  =0b00000010
	UV_TRIG_NO	  =0b00000000
	UV_TRIG_ONCE  =0b00000100
	HD			  =0b00001000
	UV_IT_MASK	  =0b01110000
	UV_IT_50MS	  =0b00000000
	UV_IT_100MS	  =0b00010000
	UV_IT_200MS	  =0b00100000
	UV_IT_400MS	  =0b00110000
	UV_IT_800MS	  =0b01000000

	def __init__(self,i2cAddress=""):
		U.setStopCondition(on=True)
		if i2cAddress =="":
			self._DeviceAddress = self.ADDR 
		else:
			self._DeviceAddress	 =	 i2cAddress	 
		self.bus = smbus.SMBus(1)

		self.intList	=[0.05,0.1,0.2,0.4,0.8]
		self.intBits	=[self.UV_IT_50MS, self.UV_IT_100MS, self.UV_IT_200MS, self.UV_IT_400MS, self.UV_IT_800MS]
		self.intNumbers = len(self.intList)
		self.intIndex	= 2


		self.defaultIntegrationTime = self.intList[self.intIndex]
		self.actualIntegrationTime	= self.intList[self.intIndex]

		# shutdown sensor
		configBits		 =(self.UV_AF_AUTO |  self.UV_TRIG_NO )
		self.bus.write_word_data(self._DeviceAddress, self.REG, configBits | self.SD)

		# Enable VEML6075 
		self.setDefBits(self.intIndex )


		self.uva_a_coef			= 2.22 # uva_a_coef = , which is the default value for the UVA VIS coefficient
		self.uva_b_coef			= 1.33 # uva_b_coef = , which is the default value for the UVA IR coefficient
		self.uva_c_coef			= 2.95 # uvb_c_coef = , which is the default value for the UVB VIS coefficient
		self.uva_d_coef			= 1.74 # uvb_d_coef = , which is the default value for the UVB IR coefficient
		self.UVAresponsivity	= 0.001461
		self.UVBresponsivity	= 0.002591

		self.uva_a_coef			= 1.92 # uva_a_coef = , which is the default value for the UVA VIS coefficient
		self.uva_b_coef			= 0.63 # uva_b_coef = , which is the default value for the UVA IR coefficient
		self.uva_c_coef			= 2.46# uvb_c_coef = , which is the default value for the UVB VIS coefficient
		self.uva_d_coef			= 0.63 # uvb_d_coef = , which is the default value for the UVB IR coefficient
		self.UVAresponsivity	= 0.001461
		self.UVBresponsivity	= 0.002591



	def setDefBits(self,index):
		self.intIndex				= index
		configBits					= (self.UV_AF_AUTO |  self.UV_TRIG_NO |	 self.intBits[self.intIndex])
		self.actualIntegrationTime	= self.intList[self.intIndex]
		self.bus.write_word_data(self._DeviceAddress, self.REG, configBits)
		time.sleep(self.actualIntegrationTime+0.05)
		
	def getLight(self):
		try:
			for ii in range(3):
			
				uva_data		= self.bus.read_word_data(self._DeviceAddress, self.UVA_DATA_REG)
				if ( uva_data >1000 and uva_data < 30000):
					break
				elif uva_data <= 2000:
					if self.intIndex == self.intNumbers-1: 
						break
					self.setDefBits(min(self.intIndex +2, self.intNumbers-1))
				elif uva_data >= 30000:
					if self.intIndex ==0: 
						break
					self.setDefBits(max(0, self.intIndex-3))


			uvb_data		= self.bus.read_word_data(self._DeviceAddress, self.UVB_DATA_REG) 
			uvcomp1_data	= self.bus.read_word_data(self._DeviceAddress, self.UVCOMP1_DATA_REG)
			uvcomp2_data	= self.bus.read_word_data(self._DeviceAddress, self.UVCOMP2_DATA_REG)
			
			self.correctionFactor	= self.actualIntegrationTime/self.defaultIntegrationTime 
					
			#print self.actualIntegrationTime, uva_data, uvb_data, uvcomp1_data, uvcomp2_data

			UVAcalc = uva_data - self.uva_a_coef * uvcomp1_data - self.uva_b_coef * uvcomp2_data
			UVBcalc = uvb_data - self.uva_c_coef * uvcomp1_data - self.uva_d_coef * uvcomp2_data
			UVIA = round(UVAcalc *	self.UVAresponsivity * self.correctionFactor ,1)
			UVIB = round(UVBcalc *	self.UVBresponsivity * self.correctionFactor ,1)

			return max(UVIA,0.), max(UVIB,0)

		except	Exception, e:
			U.toLog(-1, u"in Line {} has error={}".format(sys.exc_traceback.tb_lineno, e))
		return "",""


# ===========================================================================
# ADC121
# ===========================================================================


class ADC121:


	def __init__(self,address="",type="MQ9"):

	# Distributed with a free-will license.
	# Use it any way you want, profit or free, provided it fits in the licenses of its associated works.
	# 
	# https://github.com/ControlEverythingCommunity


		self.i2cAddress = address
		self.bus		= smbus.SMBus(1)



	def getData(self):
		try:
			ADC		= -99

			data	= self.bus.read_i2c_block_data(self.i2cAddress, 0x00, 2)
			# Convert the data to 12-bits
			ADC1	 = (data[0] & 0x0F) * 256 + data[1]

			time.sleep(0.1)

			data	= self.bus.read_i2c_block_data(self.i2cAddress, 0x00, 2)
			ADC2	= (data[0] & 0x0F) * 256 + data[1]

			ADC		= (ADC1+ADC2)/2
		except:
			pass	  
		return ADC
		


# ===========================================================================
# MS5803
# ===========================================================================


class MS5803:


	def __init__(self,address="",type="30BA"):

	# Distributed with a free-will license.
	# Use it any way you want, profit or free, provided it fits in the licenses of its associated works.
	# MS5803_30BA
	# This code is designed to work with the MS5803_30BA_I2CS I2C Mini Module available from ControlEverything.com.
	# https://www.controleverything.com/content/Analog-Digital-Converters?sku=MS5803-30BA_I2CS#tabs-0-product_tabset-2


		self.sensType = type

		self.i2cAddress= address
		self.bus = smbus.SMBus(1)
		# MS5803_30BA address, 0x76(118)
		#		0x1E(30)	Reset command
		self.bus.write_byte(self.i2cAddress, 0x1E)
		time.sleep(0.5)

		# Read 12 bytes of calibration data
		# Read pressure sensitivity
		data = self.bus.read_i2c_block_data(self.i2cAddress, 0xA2, 2)
		self.C1 = data[0] * 256 + data[1]

		# Read pressure offset
		data = self.bus.read_i2c_block_data(self.i2cAddress, 0xA4, 2)
		self.C2 = data[0] * 256 + data[1]

		# Read temperature coefficient of pressure sensitivity
		data = self.bus.read_i2c_block_data(self.i2cAddress, 0xA6, 2)
		self.C3 = data[0] * 256 + data[1]

		# Read temperature coefficient of pressure offset
		data = self.bus.read_i2c_block_data(self.i2cAddress, 0xA8, 2)
		self.C4 = data[0] * 256 + data[1]

		# Read reference temperature
		data = self.bus.read_i2c_block_data(self.i2cAddress, 0xAA, 2)
		self.C5 = data[0] * 256 + data[1]

		# Read temperature coefficient of the temperature
		data = self.bus.read_i2c_block_data(self.i2cAddress, 0xAC, 2)
		self.C6 = data[0] * 256 + data[1]




	def getData(self):
		try:
			cTemp		= -99
			pressure	= -99


############# new data every time
			# MS5803 address, 0x76(118)
			#		0x40(64)	Pressure conversion(OSR = 256) command
			self.bus.write_byte(self.i2cAddress, 0x40)

			time.sleep(0.5)

			# Read digital pressure value
			# Read data back from 0x00(0), 3 bytes
			# D1 MSB2, D1 MSB1, D1 LSB
			value = self.bus.read_i2c_block_data(self.i2cAddress, 0x00, 3)
			D1 = value[0] * 65536 + value[1] * 256 + value[2]

			# MS5803_30BA address, 0x76(118)
			#		0x50(64)	Temperature conversion(OSR = 256) command
			self.bus.write_byte(self.i2cAddress, 0x50)

			time.sleep(0.5)

			# Read digital temperature value
			# Read data back from 0x00(0), 3 bytes
			# D2 MSB2, D2 MSB1, D2 LSB
			value = self.bus.read_i2c_block_data(self.i2cAddress, 0x00, 3)
			D2 = value[0] * 65536 + value[1] * 256 + value[2]




			if self.sensType == "30BA":
				try:
					dT		= D2 - self.C5 * 256.
					TEMP	= 2000. + dT * self.C6 / 8388608.
					OFF		= self.C2 * 65536. + (self.C4 * dT) / 128.
					SENS	= self.C1 * 32768. + (self.C3 * dT ) / 256.
					T2		= 0
					OFF2	= 0
					SENS2	= 0

					if TEMP >= 2000 :
						T2		= 7. * (dT * dT) / 137438953472.
						OFF2	= ((TEMP - 2000.) * (TEMP - 200.0)) / 16.
						SENS2	= 0
					elif TEMP < 2000 :
						T2		= 3. * (dT * dT) / 8589934592
						OFF2	= 3. * ((TEMP - 2000.) * (TEMP - 2000.)) / 2
						SENS2	= 5	 * ((TEMP - 2000.) * (TEMP - 2000.)) / 8
						if TEMP < -1500:
							OFF2  = OFF2  + 7. * ((TEMP + 1500.) * (TEMP + 1500.))
							SENS2 = SENS2 + 4. * ((TEMP + 1500.) * (TEMP + 1500.))

					TEMP		= TEMP - T2
					OFF			= OFF  - OFF2
					SENS		= SENS - SENS2
					pressure	= ((((D1 * SENS) / 2097152.) - OFF) / 8192. )  *10	#  in pascal
					cTemp		= TEMP / 100.
				except:
					pass
			  
			if self.sensType == "05BA":
				try:
					dT = D2 - self.C5 * 256
					TEMP	= 2000 + dT * self.C6 / 8388608
					OFF		= self.C2 * 262144 + (self.C4 * dT) / 32
					SENS	= self.C1 * 131072 + (self.C3 * dT ) / 128
					T2		= 0
					OFF2	= 0
					SENS2	= 0

					if TEMP > 2000 :
						T2		= 0
						OFF2	= 0
						SENS2	= 0
					elif TEMP < 2000 :
						T2		= 3 * (dT * dT) / 8589934592
						OFF2	= 3 * ((TEMP - 2000) * (TEMP - 2000)) / 8
						SENS2	= 7 * ((TEMP - 2000) * (TEMP - 2000)) / 8
						if TEMP < -1500 :
							SENS2 = SENS2 + 3 * ((TEMP + 1500) * (TEMP +1500))

					TEMP = TEMP - T2
					OFF = OFF - OFF2
					SENS = SENS - SENS2
					pressure = ((((D1 * SENS) / 2097152) - OFF) / 32768.0)	# in pascal
					cTemp = TEMP / 100.0
				except:
					pass

			elif self.sensType == "01BA":
				try:
					dT		= D2 - self.C5 * 256
					TEMP	= 2000 + dT * self.C6 / 8388608
					OFF		= self.C2 * 65536 + (self.C4 * dT) / 128
					SENS	= self.C1 * 32768 + (self.C3 * dT ) / 256
					T2		= 0
					OFF2	= 0
					SENS2	= 0

					if TEMP >= 2000 :
						T2		= 0
						OFF2	= 0
						SENS2	= 0
						if TEMP > 4500 :
							SENS2 = SENS2 - ((TEMP - 4500) * (TEMP - 4500)) / 8
					elif TEMP < 2000 :
						T2		= (dT * dT) / 2147483648
						OFF2	= 3 * ((TEMP - 2000) * (TEMP - 2000))
						SENS2	= 7 * ((TEMP - 2000) * (TEMP - 2000)) / 8
						if TEMP < -1500 :
							SENS2 = SENS2 + 2 * ((TEMP + 1500) * (TEMP + 1500))

					TEMP	 = TEMP - T2
					OFF		 = OFF - OFF2
					SENS	 = SENS - SENS2
					pressure = ((((D1 * SENS) / 2097152) - OFF) / 32768.0)	# pascal
					cTemp	 = TEMP / 100.0
				except:
					pass


			elif self.sensType == "07BA":
				try:
					dT		= D2 - self.C5 * 256
					TEMP	= 2000 + dT * self.C6 / 8388608
					OFF		= self.C2 * 262144 + (self.C4 * dT) / 32
					SENS	= self.C1 * 131072 + (self.C3 * dT ) / 64
					T2 = 0
					OFF2 = 0
					SENS2 = 0

					if TEMP > 2000 :
						T2		= 0
						OFF2	= 0
						SENS2	= 0
					elif TEMP < 2000 :
						T2		= 3 * (dT * dT) / 8589934592
						OFF2	= 3 * ((TEMP - 2000) * (TEMP - 2000)) / 8
						SENS2	= 7 * ((TEMP - 2000) * (TEMP - 2000)) / 8
						if TEMP < -1500 :
							SENS2 = SENS2 + 3 * ((TEMP + 1500) * (TEMP +1500))

					TEMP		= TEMP - T2
					OFF			= OFF - OFF2
					SENS		= SENS - SENS2
					pressure	= ((((D1 * SENS) / 2097152) - OFF) / 32768.0)  # pascal
					cTemp		= TEMP / 100.0
				except:
					pass


			elif self.sensType == "02BA":
				try:
					dT		= D2 - self.C5 * 256
					TEMP	= 2000 + dT * self.C6 / 8388608
					OFF		= self.C2 * 131072 + (self.C4 * dT) / 64
					SENS	= self.C1 * 65536 + (self.C3 * dT ) / 128
					T2		= 0
					OFF2	= 0
					SENS2	= 0

					if TEMP >= 2000 :
						T2		= 0
						OFF2	= 0
						SENS2	= 0
					elif TEMP < 2000 :
						T2			= (dT * dT) / 2147483648
						OFF2		= 61 * ((TEMP - 2000) * (TEMP - 2000)) / 16
						SENS2		= 2 * ((TEMP - 2000) * (TEMP - 2000))
						if TEMP < -1500 :
							OFF2	= OFF2 + 20 * ((TEMP + 1500) * (TEMP + 1500))
							SENS2	= SENS2 + 12 * ((TEMP + 1500) * (TEMP +1500))

					TEMP		= TEMP - T2
					OFF			= OFF - OFF2
					SENS		= SENS - SENS2
					pressure	= ((((D1 * SENS) / 2097152) - OFF) / 32768.0) # pascal
					cTemp	= TEMP / 100.0
				except:
					pass


			  
			elif self.sensType == "14BA":
				try:
					dT			= D2 - self.C5 * 256
					TEMP		= 2000 + dT * self.C6 / 8388608
					OFF			= self.C2 * 65536 + (self.C4 * dT) / 128
					SENS		= self.C1 * 32768 + (self.C3 * dT ) / 256
					T2			= 0
					OFF2		= 0
					SENS2	= 0

					if TEMP > 2000 :
						T2		= 7 * (dT * dT)/ 137438953472
						OFF2	= ((TEMP - 2000) * (TEMP - 2000)) / 16
						SENS2	= 0
					elif TEMP < 2000 :
						T2		= 3 * (dT * dT) / 8589934592
						OFF2	= 3 * ((TEMP - 2000) * (TEMP - 2000)) / 8
						SENS2	= 5 * ((TEMP - 2000) * (TEMP - 2000)) / 8
						if TEMP < -1500:
							OFF2	= OFF2 + 7 * ((TEMP + 1500) * (TEMP + 1500))
							SENS2	= SENS2 + 4 * ((TEMP + 1500) * (TEMP + 1500))

					TEMP	 = TEMP - T2
					OFF		 = OFF - OFF2
					SENS	 = SENS - SENS2
					pressure = ((((D1 * SENS) / 2097152) - OFF) / 32768.0)	# pascal
					cTemp	 = TEMP / 100.0				   
				except:
					pass




		except:
			pass
		return cTemp, pressure



# ===========================================================================
# IS1145
# ===========================================================================


class IS1145():
# Author: Joe Gutting
# With use of Adafruit IS1145 library for Arduino, Adafruit_GPIO.I2C & BMP Library by Tony DiCola
#
# Permission is hereby granted, free of charge, to any person obtaining a copy
# of this software and associated documentation files (the "Software"), to deal
# in the Software without restriction, including without limitation the rights
# to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
# copies of the Software, and to permit persons to whom the Software is
# furnished to do so, subject to the following conditions:
#
# The above copyright notice and this permission notice shall be included in
# all copies or substantial portions of the Software.
#
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
# IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
# FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
# AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
# LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
# OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN
# THE SOFTWARE.


	# COMMANDS
	IS1145_PARAM_QUERY						= 0x80
	IS1145_PARAM_SET						= 0xA0
	IS1145_NOP								= 0x0
	IS1145_RESET							= 0x01
	IS1145_BUSADDR							= 0x02
	IS1145_PS_FORCE							= 0x05
	IS1145_ALS_FORCE						= 0x06
	IS1145_PSALS_FORCE						= 0x07
	IS1145_PS_PAUSE							= 0x09
	IS1145_ALS_PAUSE						= 0x0A
	IS1145_PSALS_PAUSE						= 0xB
	IS1145_PS_AUTO							= 0x0D
	IS1145_ALS_AUTO							= 0x0E
	IS1145_PSALS_AUTO						= 0x0F
	IS1145_GET_CAL							= 0x12

	# Parameters
	IS1145_PARAM_I2CADDR					= 0x00
	IS1145_PARAM_CHLIST						= 0x01
	IS1145_PARAM_CHLIST_ENUV				= 0x80
	IS1145_PARAM_CHLIST_ENAUX				= 0x40
	IS1145_PARAM_CHLIST_ENALSIR				= 0x20
	IS1145_PARAM_CHLIST_ENALSVIS			= 0x10
	IS1145_PARAM_CHLIST_ENPS1				= 0x01
	IS1145_PARAM_CHLIST_ENPS2				= 0x02
	IS1145_PARAM_CHLIST_ENPS3				= 0x04

	IS1145_PARAM_PSLED12SEL					= 0x02
	IS1145_PARAM_PSLED12SEL_PS2NONE			= 0x00
	IS1145_PARAM_PSLED12SEL_PS2LED1			= 0x10
	IS1145_PARAM_PSLED12SEL_PS2LED2			= 0x20
	IS1145_PARAM_PSLED12SEL_PS2LED3			= 0x40
	IS1145_PARAM_PSLED12SEL_PS1NONE			= 0x00
	IS1145_PARAM_PSLED12SEL_PS1LED1			= 0x01
	IS1145_PARAM_PSLED12SEL_PS1LED2			= 0x02
	IS1145_PARAM_PSLED12SEL_PS1LED3			= 0x04

	IS1145_PARAM_PSLED3SEL					= 0x03
	IS1145_PARAM_PSENCODE					= 0x05
	IS1145_PARAM_ALSENCODE					= 0x06

	IS1145_PARAM_PS1ADCMUX					= 0x07
	IS1145_PARAM_PS2ADCMUX					= 0x08
	IS1145_PARAM_PS3ADCMUX					= 0x09
	IS1145_PARAM_PSADCOUNTER				= 0x0A
	IS1145_PARAM_PSADCGAIN					= 0x0B
	IS1145_PARAM_PSADCMISC					= 0x0C
	IS1145_PARAM_PSADCMISC_RANGE			= 0x20
	IS1145_PARAM_PSADCMISC_PSMODE			= 0x04

	IS1145_PARAM_ALSIRADCMUX				= 0x0E
	IS1145_PARAM_AUXADCMUX					= 0x0F

	IS1145_PARAM_ALSVISADCOUNTER			= 0x10
	IS1145_PARAM_ALSVISADCGAIN				= 0x11
	IS1145_PARAM_ALSVISADCMISC				= 0x12
	IS1145_PARAM_ALSVISADCMISC_VISRANGE		= 0x20

	IS1145_PARAM_ALSIRADCOUNTER				= 0x1D
	IS1145_PARAM_ALSIRADCGAIN				= 0x1E
	IS1145_PARAM_ALSIRADCMISC				= 0x1F
	IS1145_PARAM_ALSIRADCMISC_RANGE			= 0x20

	IS1145_PARAM_ADCCOUNTER_511CLK			= 0x70

	IS1145_PARAM_ADCMUX_SMALLIR				= 0x00
	IS1145_PARAM_ADCMUX_LARGEIR				= 0x03



	# REGISTERS
	IS1145_REG_PARTID						= 0x00
	IS1145_REG_REVID						= 0x01
	IS1145_REG_SEQID						= 0x02

	IS1145_REG_INTCFG						= 0x03
	IS1145_REG_INTCFG_INTOE					= 0x01
	IS1145_REG_INTCFG_INTMODE				= 0x02

	IS1145_REG_IRQEN						= 0x04
	IS1145_REG_IRQEN_ALSEVERYSAMPLE			= 0x01
	IS1145_REG_IRQEN_PS1EVERYSAMPLE			= 0x04
	IS1145_REG_IRQEN_PS2EVERYSAMPLE			= 0x08
	IS1145_REG_IRQEN_PS3EVERYSAMPLE			= 0x10


	IS1145_REG_IRQMODE1						= 0x05
	IS1145_REG_IRQMODE2						= 0x06

	IS1145_REG_HWKEY						= 0x07
	IS1145_REG_MEASRATE0					= 0x08
	IS1145_REG_MEASRATE1					= 0x09
	IS1145_REG_PSRATE						= 0x0A
	IS1145_REG_PSLED21						= 0x0F
	IS1145_REG_PSLED3						= 0x10
	IS1145_REG_UCOEFF0						= 0x13
	IS1145_REG_UCOEFF1						= 0x14
	IS1145_REG_UCOEFF2						= 0x15
	IS1145_REG_UCOEFF3						= 0x16
	IS1145_REG_PARAMWR						= 0x17
	IS1145_REG_COMMAND						= 0x18
	IS1145_REG_RESPONSE						= 0x20
	IS1145_REG_IRQSTAT						= 0x21
	IS1145_REG_IRQSTAT_ALS					= 0x01

	IS1145_REG_ALSVISDATA0					= 0x22
	IS1145_REG_ALSVISDATA1					= 0x23
	IS1145_REG_ALSIRDATA0					= 0x24
	IS1145_REG_ALSIRDATA1					= 0x25
	IS1145_REG_PS1DATA0						= 0x26
	IS1145_REG_PS1DATA1						= 0x27
	IS1145_REG_PS2DATA0						= 0x28
	IS1145_REG_PS2DATA1						= 0x29
	IS1145_REG_PS3DATA0						= 0x2A
	IS1145_REG_PS3DATA1						= 0x2B
	IS1145_REG_UVINDEX0						= 0x2C
	IS1145_REG_UVINDEX1						= 0x2D
	IS1145_REG_PARAMRD						= 0x2E
	IS1145_REG_CHIPSTAT						= 0x30

	# I2C Address
	IS1145_ADDR								= 0x60


	def __init__(self, i2cAddress=IS1145_ADDR):

			self.bus = smbus.SMBus(1)
			if i2cAddress =="" or i2cAddress ==0:
				self._DeviceAddress = self.IS1145_ADDR 
			else:
				self._DeviceAddress = i2cAddress

			#reset device
			self._reset()

			# Load calibration values.
			self._load_calibration()

	# device reset
	def _reset(self):
			self.bus.write_byte_data(self._DeviceAddress, self.IS1145_REG_MEASRATE0, 0)
			self.bus.write_byte_data(self._DeviceAddress, self.IS1145_REG_MEASRATE1, 0)
			self.bus.write_byte_data(self._DeviceAddress, self.IS1145_REG_IRQEN, 0)
			self.bus.write_byte_data(self._DeviceAddress, self.IS1145_REG_IRQMODE1, 0)
			self.bus.write_byte_data(self._DeviceAddress, self.IS1145_REG_IRQMODE2, 0)
			self.bus.write_byte_data(self._DeviceAddress, self.IS1145_REG_INTCFG, 0)
			self.bus.write_byte_data(self._DeviceAddress, self.IS1145_REG_IRQSTAT, 0xFF)

			self.bus.write_byte_data(self._DeviceAddress, self.IS1145_REG_COMMAND, self.IS1145_RESET)
			time.sleep(.01)
			self.bus.write_byte_data(self._DeviceAddress, self.IS1145_REG_HWKEY, 0x17)
			time.sleep(.01)

	# write Param
	def writeParam(self, p, v):
			self.bus.write_byte_data(self._DeviceAddress, self.IS1145_REG_PARAMWR, v)
			self.bus.write_byte_data(self._DeviceAddress, self.IS1145_REG_COMMAND, p | self.IS1145_PARAM_SET)
			paramVal = self.bus.read_byte_data(self._DeviceAddress,self.IS1145_REG_PARAMRD)
			return paramVal

	# load calibration to sensor
	def _load_calibration(self):
			# /***********************************/
			# Enable UVindex measurement coefficients!
			self.bus.write_byte_data(self._DeviceAddress, self.IS1145_REG_UCOEFF0, 0x29)
			self.bus.write_byte_data(self._DeviceAddress, self.IS1145_REG_UCOEFF1, 0x89)
			self.bus.write_byte_data(self._DeviceAddress, self.IS1145_REG_UCOEFF2, 0x02)
			self.bus.write_byte_data(self._DeviceAddress, self.IS1145_REG_UCOEFF3, 0x00)

			# Enable UV sensor
			self.writeParam(self.IS1145_PARAM_CHLIST, self.IS1145_PARAM_CHLIST_ENUV | self.IS1145_PARAM_CHLIST_ENALSIR | self.IS1145_PARAM_CHLIST_ENALSVIS | self.IS1145_PARAM_CHLIST_ENPS1)

			# Enable interrupt on every sample
			self.bus.write_byte_data(self._DeviceAddress, self.IS1145_REG_INTCFG, self.IS1145_REG_INTCFG_INTOE)
			self.bus.write_byte_data(self._DeviceAddress, self.IS1145_REG_IRQEN,  self.IS1145_REG_IRQEN_ALSEVERYSAMPLE)

			# /****************************** Prox Sense 1 */

			# Program LED current
			self.bus.write_byte_data(self._DeviceAddress, self.IS1145_REG_PSLED21, 0x03) # 20mA for LED 1 only
			self.writeParam(self.IS1145_PARAM_PS1ADCMUX, self.IS1145_PARAM_ADCMUX_LARGEIR)

			# Prox sensor #1 uses LED #1
			self.writeParam(self.IS1145_PARAM_PSLED12SEL, self.IS1145_PARAM_PSLED12SEL_PS1LED1)

			# Fastest clocks, clock div 1
			self.writeParam(self.IS1145_PARAM_PSADCGAIN, 0)

			# Take 511 clocks to measure
			self.writeParam(self.IS1145_PARAM_PSADCOUNTER, self.IS1145_PARAM_ADCCOUNTER_511CLK)

			# in prox mode, high range
			self.writeParam(self.IS1145_PARAM_PSADCMISC, self.IS1145_PARAM_PSADCMISC_RANGE | self.IS1145_PARAM_PSADCMISC_PSMODE)
			self.writeParam(self.IS1145_PARAM_ALSIRADCMUX, self.IS1145_PARAM_ADCMUX_SMALLIR)

			# Fastest clocks, clock div 1
			self.writeParam(self.IS1145_PARAM_ALSIRADCGAIN, 0)

			# Take 511 clocks to measure
			self.writeParam(self.IS1145_PARAM_ALSIRADCOUNTER, self.IS1145_PARAM_ADCCOUNTER_511CLK)

			# in high range mode
			self.writeParam(self.IS1145_PARAM_ALSIRADCMISC, self.IS1145_PARAM_ALSIRADCMISC_RANGE)

			# fastest clocks, clock div 1
			self.writeParam(self.IS1145_PARAM_ALSVISADCGAIN, 0)

			# Take 511 clocks to measure
			self.writeParam(self.IS1145_PARAM_ALSVISADCOUNTER, self.IS1145_PARAM_ADCCOUNTER_511CLK)

			# in high range mode (not normal signal)
			self.writeParam(self.IS1145_PARAM_ALSVISADCMISC, self.IS1145_PARAM_ALSVISADCMISC_VISRANGE)

			# measurement rate for auto
			self.bus.write_byte_data(self._DeviceAddress, self.IS1145_REG_MEASRATE0, 0xFF) # 255 * 31.25uS = 8ms

			# auto run
			self.bus.write_byte_data(self._DeviceAddress, self.IS1145_REG_COMMAND, self.IS1145_PSALS_AUTO)


	def getLight(self):
		v = self.bus.read_word_data(self._DeviceAddress,0x22)  ## ( overlaps somewhat with IR  )
		i = self.bus.read_word_data(self._DeviceAddress,0x24)
		u = self.bus.read_word_data(self._DeviceAddress,0x2C)/100.
		#p = self._bus.read_word_data(self._DeviceAddress,0x26)	 ## proximity 
		return v,u, i



# ===========================================================================
# VEML6040
# ===========================================================================


class VEML6040:
	VEML6040_SLAVE_ADD	   = 0x10

	COMMAND_CODE_CONF	   = 0x00
	COMMAND_CODE_R_DATA	   = 0x08
	COMMAND_CODE_G_DATA	   = 0x09
	COMMAND_CODE_B_DATA	   = 0x0A
	COMMAND_CODE_W_DATA	   = 0x0B

	VEML6040_Mode_ON	   = 0b0000000000000000
	VEML6040_Mode_OFF	   = 0b0000000000000001
							#  7654321076543210
	VEML6040_IT_40MS	   = 0b0000000000000000
	VEML6040_IT_80MS	   = 0b0000000000010000
	VEML6040_IT_160MS	   = 0b0000000000100000
	VEML6040_IT_320MS	   = 0b0000000000110000
	VEML6040_IT_640MS	   = 0b0000000001000000
	VEML6040_IT_1280MS	   = 0b0000000001010000
	integrationTimeBits		   = [[	 "40",	VEML6040_IT_40MS,  1.0],
								  [	 "80",	VEML6040_IT_80MS,  2.0],
								  [ "160", VEML6040_IT_160MS,  4.0],
								  [ "320", VEML6040_IT_320MS,  8.0],
								  [ "640", VEML6040_IT_640MS,  16.0],
								  ["1280",VEML6040_IT_1280MS,  32.0]]
	integrationMinMsec		   = 0.04
	integrationTimeGainFactor  = 0.25168

	VEML6040_TRIG_OFF	  = 0b0000000000000000
	VEML6040_TRIG_ON	  = 0b0000000000000100
	VEML6040_AUTO_OFF	  = 0b0000000000000000 # = force
	VEML6040_AUTO_ON	  = 0b0000000000000010



	def __init__(self,address=""):
		U.setStopCondition(on=True)

		try:
			if address =="":
				self._DeviceAddress = self.VEML6040_SLAVE_ADD 
			else:
				self._DeviceAddress	 =	 address  
			self.bus = smbus.SMBus(1)

			# Shut Down Color Sensor
			configuration	= self.VEML6040_Mode_OFF 
			self.bus.write_word_data(self._DeviceAddress, self.COMMAND_CODE_CONF, configuration)
			# Enable Color Sensor
			configuration	= self.VEML6040_Mode_ON |  self.VEML6040_IT_40MS 
			self.bus.write_word_data(self._DeviceAddress, self.COMMAND_CODE_CONF, configuration)
		
			self.minWaitTime=0.5
			self.minResult = 400
			self.maxResult = 20000
			self.itLast	   = 1
		except	Exception, e:
			U.toLog(-1, u"in Line {} has error={}".format(sys.exc_traceback.tb_lineno, e))


		

	def getLight(self):
		# RGB W data
		R_DATA	 = [0,0,0]
		G_DATA	 = [0,0,0]
		B_DATA	 = [0,0,0]
		W_DATA	 = [0,0,0]
		# RGB W data normalized with integr. time
		R_DATA_LUX	= [0,0,0]
		G_DATA_LUX	= [0,0,0]
		B_DATA_LUX	= [0,0,0]
		W_DATA_LUX	= [0,0,0]
		try:
			for ii in range(3):
				IT				= self.itLast
				waitTime		= self.minWaitTime + self.integrationTimeBits[IT][2]*self.integrationMinMsec
				factor			= self.integrationTimeGainFactor  * self.integrationTimeBits[IT][2]
				configuration	= self.VEML6040_Mode_ON |  self.integrationTimeBits[IT][1]
				self.bus.write_word_data(self._DeviceAddress, self.COMMAND_CODE_CONF, configuration)
				time.sleep(waitTime)

				while True:
					# get RGB W data 
					R_DATA[ii]	= self.bus.read_word_data(self._DeviceAddress,self.COMMAND_CODE_R_DATA)
					G_DATA[ii]	= self.bus.read_word_data(self._DeviceAddress,self.COMMAND_CODE_G_DATA)
					B_DATA[ii]	= self.bus.read_word_data(self._DeviceAddress,self.COMMAND_CODE_B_DATA)
					W_DATA[ii]	= self.bus.read_word_data(self._DeviceAddress,self.COMMAND_CODE_W_DATA)
					R_DATA_LUX[ii] = R_DATA[ii]*factor
					G_DATA_LUX[ii] = G_DATA[ii]*factor
					B_DATA_LUX[ii] = B_DATA[ii]*factor
					W_DATA_LUX[ii] = W_DATA[ii]*factor
					maxV = max(R_DATA[ii],G_DATA[ii],B_DATA[ii],W_DATA[ii])
					#print maxV
					if maxV < self.minResult: 
						if IT == 5: 
							break
						
						multF = int(self.minResult/max(maxV,0.01))+1
						#print multF
						left = multF - (5-IT)
						if left >1:
							if IT == min(IT+left,5):
							   IT = min(IT+left+1,5)
							else:
								IT =min(IT+left,5)
						else:
							break
						
					elif maxV > self.maxResult: 
						if IT ==0: break
						if IT > 0: 
							IT =max(IT-3,0)
					else:
							break
						
					# calc for next round
					waitTime		= self.minWaitTime + self.integrationTimeBits[IT][2]*self.integrationMinMsec
					factor			= self.integrationTimeGainFactor  * self.integrationTimeBits[IT][2]
					configuration	= self.VEML6040_Mode_ON |  self.integrationTimeBits[IT][1]
					self.bus.write_word_data(self._DeviceAddress, self.COMMAND_CODE_CONF, configuration)
					#print "trying: IT=",IT,"factor", factor, "waitTime",waitTime
					time.sleep(waitTime)
				if ii==1: # skip 3. round?
					if abs(W_DATA_LUX[0]-W_DATA_LUX[1])/max(0.1,W_DATA_LUX[0]+W_DATA_LUX[1]) < 0.05: break
				self.itLast	  = IT 

			#print	"end result:",R_DATA,R_DATA_LUX, W_DATA, W_DATA_LUX
			R= sorted(R_DATA_LUX)[1]
			G= sorted(G_DATA_LUX)[1]
			B= sorted(B_DATA_LUX)[1]
			W= sorted(W_DATA_LUX)[1]
			return	[R, G, B, W]
		except	Exception, e:
			U.toLog(-1, u"in Line {} has error={}".format(sys.exc_traceback.tb_lineno, e))
		return "",""


# ===========================================================================
# T5403
# ===========================================================================


T5403_slaveAddress = 0x77
#registers
T5403_COMMAND_REG = 0xf1
T5403_DATA_REG_LSB = 0xf5
T5403_DATA_REG_MSB = 0xf6
#commands
T5403_COMMAND_GET_TEMP = 0x03
#definitions for pressure reading commands with accuracy modes
T5403_MODE_LOW = 0x00
T5403_MODE_STANDARD = 0x01
T5403_MODE_HIGH = 0x10
T5403_MODE_ULTRA = 0x11

def startT5403(i2c=0):
	global c1,c2,c3,c4,c5,c6,c7,c8,sensorT5403
	sensorT5403 = smbus.SMBus(1)

	if i2c != 0 :
		i2cAdd = int(i2c)
	else :
		i2cAdd = T5403_slaveAddress

	c1 = (sensorT5403.read_byte_data(i2cAdd,0x8f)<<8) + sensorT5403.read_byte_data(i2cAdd,0x8e)
	c2 = (sensorT5403.read_byte_data(i2cAdd,0x91)<<8) + sensorT5403.read_byte_data(i2cAdd,0x90)
	c3 = (sensorT5403.read_byte_data(i2cAdd,0x93)<<8) + sensorT5403.read_byte_data(i2cAdd,0x92)
	c4 = (sensorT5403.read_byte_data(i2cAdd,0x95)<<8) + sensorT5403.read_byte_data(i2cAdd,0x94)
	c5 = (sensorT5403.read_byte_data(i2cAdd,0x97)<<8) + sensorT5403.read_byte_data(i2cAdd,0x96)
	c6 = (sensorT5403.read_byte_data(i2cAdd,0x99)<<8) + sensorT5403.read_byte_data(i2cAdd,0x98)
	c7 = (sensorT5403.read_byte_data(i2cAdd,0x9b)<<8) + sensorT5403.read_byte_data(i2cAdd,0x9a)
	c8 = (sensorT5403.read_byte_data(i2cAdd,0x9d)<<8) + sensorT5403.read_byte_data(i2cAdd,0x9c)
	c5 = uint16Toint16(c5)
	c6 = uint16Toint16(c6)
	c7 = uint16Toint16(c7)
	c8 = uint16Toint16(c8)
	U.toLog(1, u"enabled T5403")

def uint16Toint16(data):
		if data > 32767:
				return data - 0x10000
		else:
				return data
def sendCommandT5403(cmd,address=T5403_slaveAddress):
		sensorT5403.write_byte_data(address,T5403_COMMAND_REG,cmd)
def getT5403RawData(address=T5403_slaveAddress):
		return (sensorT5403.read_byte_data(address,T5403_DATA_REG_MSB)<<8) + sensorT5403.read_byte_data(address,T5403_DATA_REG_LSB)
		
def getT5403(sensor, data):
	global sensorT5403i, T5403started
	global c1,c2,c3,c4,c5,c6,c7,c8, sensorT5403
	global sensors, sValues, displayInfo
	if sensor not in sensors: return data

	try:
		ii= T5403started
	except:	   
		T5403started=1
		sensorT5403i ={}


	precision = T5403_MODE_STANDARD
	try:
		data[sensor] ={}
		for devId in sensors[sensor] :
			i2cAdd = U.muxTCA9548A(sensors[sensor][devId], i2c= T5403_slaveAddress)
			if devId not in sensorT5403i:
					sensorT5403i[devId]= i2cAdd
					startT5403(i2c=i2cAdd)
					time.sleep(0.1)
			sendCommandT5403(T5403_COMMAND_GET_TEMP,address=i2cAdd )
			time.sleep(0.006)
			temp_raw = uint16Toint16(  getT5403RawData() )
			temp_actual	 =	(  (  (	 ((c1 * temp_raw)/ 0x100) +	  (c2 * 0x40)  ) * 100) / 0x10000  ) /100.
			time.sleep(0.1)
			#Load measurement noise level into command along with start command bit.
			precision = (precision << 3)|(0x01)
			# Start pressure measurement
			sendCommandT5403(precision)
			if precision == T5403_MODE_LOW:
					time.sleep(0.005)
			elif precision == T5403_MODE_STANDARD:
					time.sleep(0.011)
			elif precision == T5403_MODE_HIGH:
					time.sleep(0.019)
			elif precision == T5403_MODE_ULTRA:
					time.sleep(0.067)
			else:
					time.sleep(0.1)
			pressure_raw = getT5403RawData()
			# calculate pressure
			s = (((( c5 * temp_raw) >> 15) * temp_raw) >> 19) + c3 + (( c4 * temp_raw) >> 17)
			o = (((( c8 * temp_raw) >> 15) * temp_raw) >> 4) + (( c7 * temp_raw) >> 3) + (c6 * 0x4000)
			press= (s * pressure_raw + o) >> 14
			#U.toLog(5, u" temp press "+ str(temp_raw)+ " "+ str(pressure_raw))
			t = temp_actual
			p = press

			if t!="":
				try:	t = float(t) + float(sensors[sensor][devId]["offsetTemp"])
				except: pass
				data[sensor][devId] = {"temp":round(t,1)}
				if p!="":
					try:	p = (float(p) + float(sensors[sensor][devId]["offsetPress"]))
					except: pass
				data[sensor][devId]["press"]=round(p,1)
				putValText(sensors[sensor][devId],[t],["temp"])
				if devId in badSensors: del badSensors[devId]
				time.sleep(0.1)
			else:
				data= incrementBadSensor(devId,sensor,data)

	except	Exception, e:
			U.toLog(-1, u"in Line {} has error={}".format(sys.exc_traceback.tb_lineno, e))
			U.toLog(-1, u" sensor bad T5403 @ "+ unicode(sensorT5403i))
			
	if sensor in data and data[sensor]=={}: del data[sensor]
	U.muxTCA9548Areset()
	return data	   



# ===========================================================================
# BMP
# ===========================================================================
def getBMP(sensor, data):
	global sensorBMP, BMPstarted
	global sensors, sValues, displayInfo
	
	if sensor not in sensors: return data

	try:
		ii= BMPstarted
	except:	   
		BMPstarted=1
		sensorBMP ={}

	try:
		data[sensor] ={}
		for devId in sensors[sensor]:
			i2cAdd = U.muxTCA9548A(sensors[sensor][devId])

			if devId not in sensorBMP:
				sensorBMP[devId]= BMP085(address=i2cAdd)
			try:
				t =float(sensorBMP[devId].read_temperature())
				p =sensorBMP[devId].read_pressure()
				if p < 0: 
					raise ValueError("bad return value, pressure < 0") 
			except	Exception, e:
					U.toLog(-1, u"in Line {} has error={}".format(sys.exc_traceback.tb_lineno, e))
					U.toLog(-1, u"return  value: t={} ; p={};   i2c address used:{}".format(t, p, i2cAdd) )
					data = incrementBadSensor(devId,sensor,data)
					return data
			if t!="":
				try:	t = float(t) + float(sensors[sensor][devId]["offsetTemp"])
				except:	 pass
				data[sensor][devId] = {"temp":round(t,1)}

				if p!="":
					try:	p = float(p) + float(sensors[sensor][devId]["offsetPress"])
					except: pass
					data[sensor][devId]["press"]=round(p,1)
				
				if devId in badSensors: del badSensors[devId]
				putValText(sensors[sensor][devId],[t,p],["temp","press"])
				time.sleep(0.1)
			else:
				data= incrementBadSensor(devId,sensor,data)
	except	Exception, e:
		U.toLog(-1, u"in Line {} has error={}".format(sys.exc_traceback.tb_lineno, e))

	if sensor in data and data[sensor]=={}: del data[sensor]
	U.muxTCA9548Areset()
	return data	   



# ===========================================================================
# BME
# ===========================================================================
def getBME(sensor, data,BMP=False):
	global sensorBME280, BME280started
	global sensors, sValues, displayInfo
	
	if sensor not in sensors: return data

	try:
		ii= BME280started
	except:	   
		BME280started=1
		sensorBME280 ={}

	try:
		t,p,h="","",""
		data[sensor] ={}
		for devId in sensors[sensor]:
			i2cAdd = U.muxTCA9548A(sensors[sensor][devId])
			
			if devId not in sensorBME280:
				sensorBME280[devId]= BME280(mode=4,address=i2cAdd)
			try:
				t =float(sensorBME280[devId].read_temperature())
				p =sensorBME280[devId].read_pressure()
				if p < 0: 
					raise ValueError("bad return value, pressure < 0") 
				if not BMP:
					h = sensorBME280[devId].read_humidity()
			except	Exception, e:
					U.toLog(-1, u"in Line {} has error={}".format(sys.exc_traceback.tb_lineno, e))
					U.toLog(-1, u"return  value: t={} ; p={}; h={} ;   i2c address used:{}".format(t, p, h, i2cAdd)	  )
					data = incrementBadSensor(devId,sensor,data)
					return data
			if t!="":
				try:	t = float(t) + float(sensors[sensor][devId]["offsetTemp"])
				except:	 
					data = incrementBadSensor(devId,sensor,data)
					return data
				data[sensor][devId] = {"temp":round(t,1)}

				if p!="":
					try:	p = float(p) + float(sensors[sensor][devId]["offsetPress"])
					except:	 
						data = incrementBadSensor(devId,sensor,data)
						return data
					data[sensor][devId]["press"]=round(p,1)

				if h!= "":
					try:	h = (float(h)  + float(sensors[sensor][devId]["offsetHum"]))
					except:	 
						data = incrementBadSensor(devId,sensor,data)
						return data
					data[sensor][devId]["hum"]=round(h,1)
				
				if devId in badSensors: del badSensors[devId]
				if not BMP:
					putValText(sensors[sensor][devId],[t,h,p],["temp","hum","press"])
				else:
					putValText(sensors[sensor][devId],[t,p],["temp","press"])
				time.sleep(0.1)
			else:
				data= incrementBadSensor(devId,sensor,data)
	except	Exception, e:
		U.toLog(-1, u"in Line {} has error={}".format(sys.exc_traceback.tb_lineno, e))

	if sensor in data and data[sensor]=={}: del data[sensor]
	U.muxTCA9548Areset()

	return data	   

				
# ===========================================================================
# getSHT21
# ===========================================================================
def getSHT21(sensor, data):
	global sensorSHT21, SHT21started
	global sensors, sValues, displayInfo
	
	if sensor not in sensors: return data
	try:
		try:
			ii= SHT21started
		except:	   
			SHT21started=1
			sensorSHT21 ={}
			
		try:
			data[sensor] ={}
			for devId in sensors[sensor]:
				i2cAdd = U.muxTCA9548A(sensors[sensor][devId])
				if devId not in sensorSHT21:
					sensorSHT21[devId]= SHT21(i2cAdd=i2cAdd)

				t =("%.2f"%float(sensorSHT21[devId].read_temperature())).strip()
				h =("%3d"%sensorSHT21[devId].read_humidity()).strip()
				if t!="":
					try:	t = str(float(t) + float(sensors[sensor][devId]["offsetTemp"]))
					except:	 pass
					data[sensor][devId] = {"temp":round(t,1)}

					if h!= "":
						try:	h = (float(h)  + float(sensors[sensor][devId]["offsetHum"]))
						except: pass
						data[sensor][devId]["hum"]=round(h,1)
				
					if devId in badSensors: del badSensors[devId]
					putValText(sensors[sensor][devId],[t,h],["temp","hum"])
					time.sleep(0.1)
				else:
					data= incrementBadSensor(devId,sensor,data)
		except	Exception, e:
			U.toLog(-1, u"in Line {} has error={}".format(sys.exc_traceback.tb_lineno, e))
	except	Exception, e:
		U.toLog(-1, u"in Line {} has error={}".format(sys.exc_traceback.tb_lineno, e))
	if sensor in data and data[sensor]=={}: del data[sensor]
	U.muxTCA9548Areset()
	return data	   


# ===========================================================================
# getLM75A
# ===========================================================================
def getLM75A(sensor, data):
	global sensorLM75A, LM75Astarted
	global sensors, sValues, displayInfo
	
	if sensor not in sensors: return data

	try:
		try:
			ii= M75Astarted
		except:	   
			M75Astarted=1
			sensorLM75A ={}

		try:
			data[sensor] ={}
			for devId in sensors[sensor]:
				i2cAdd = U.muxTCA9548A(sensors[sensor][devId])
				if devId not in sensorLM75A:
					sensorLM75A[devId]= LM75A(i2cAdd=i2cAdd)
				t =float(sensorLM75A[devId].read_temperature())
				if t!="":
					try:	t = float(t) + float(sensors[sensor][devId]["offsetTemp"])
					except:	 pass
					data[sensor][devId] = {"temp":round(t,1)}
					
					if devId in badSensors: del badSensors[devId]
					putValText(sensors[sensor][devId],[t],["temp"])
					time.sleep(0.1)
				else:
					data= incrementBadSensor(devId,sensor,data)
		except	Exception, e:
			U.toLog(-1, u"in Line {} has error={}".format(sys.exc_traceback.tb_lineno, e))
	except	Exception, e:
		U.toLog(-1, u"in Line {} has error={}".format(sys.exc_traceback.tb_lineno, e))
	if sensor in data and data[sensor]=={}: del data[sensor]
	U.muxTCA9548Areset()
	return data	   

# ===========================================================================
# getAM2320
# ===========================================================================
def getAM2320(sensor, data):
	global sensorAM2320, AM2320started
	global sensors, sValues, displayInfo
	
	if sensor not in sensors: return data

	try:
		try:
			ii= AM2320started
		except:	   
			AM2320started=1
			sensorAM2320 ={}

		try:
			sensor = "i2cAM2320"
			if sensor in sensorList :
				data[sensor] ={}
				for devId in sensors[sensor]:
					i2cAdd = U.muxTCA9548A(sensors[sensor][devId])
					i2c=sensors[sensor][devId]["i2cAddress"]
					if devId not in sensorAM2320:
						sensorAM2320[devId]= AM2320(i2cAdd=i2cAdd)
					t,h =sensorAM2320[devId].read()
					if t!="":
						try:	t = float(t) + float(sensors[sensor][devId]["offsetTemp"])
						except:	 pass
						data[sensor][devId] = {"temp":round(t,1)}

						if h!= "":
							try:	h = (float(h)  + float(sensors[sensor][devId]["offsetHum"]))
							except: pass
							data[sensor][devId]["hum"]=round(h,1)
						
						if devId in badSensors: del badSensors[devId]
						putValText(sensors[sensor][devId],[t,h],["temp","hum"])
						time.sleep(0.1)
					else:
						data= incrementBadSensor(devId,sensor,data)
		except	Exception, e:
			U.toLog(-1, u"in Line {} has error={}".format(sys.exc_traceback.tb_lineno, e))
	except	Exception, e:
		U.toLog(-1, u"in Line {} has error={}".format(sys.exc_traceback.tb_lineno, e))
	if sensor in data and data[sensor]=={}: del data[sensor]
	U.muxTCA9548Areset()
	return data	   

# ===========================================================================
# getMCP9808
# ===========================================================================
def getMCP9808(sensor, data):
	global sensorMCP9808, MCP9808Started
	global sensors, sValues, displayInfo
	
	if sensor not in sensors: return data
	try :
		ii = MCP9808Started
	except :
		MCP9808Started = 1
		sensorMCP9808 = {}
	try:
		data[sensor] ={}
		for devId in sensors[sensor] :
			i2cAdd = U.muxTCA9548A(sensors[sensor][devId])
			if devId not in sensorMCP9808:
				sensorMCP9808[devId] = MCP9808(int(i2cAdd))
				sensorMCP9808[devId].begin()
			t=sensorMCP9808[devId].readTempC()
			if t!="" :
				try:   t = (float(t) + float(sensors[sensor][devId]["offsetTemp"]))
				except: pass
				data[sensor][devId] = {"temp":round(t,1)}
				putValText(sensors[sensor][devId],[t],["temp"])
				if devId in badSensors: del badSensors[devId]
				time.sleep(0.1)
			else:
				data= incrementBadSensor(devId,sensor,data)
		if sensor in data and data[sensor]=={}: del data[sensor]
	except	Exception, e:
		U.toLog(-1, u"in Line {} has error={}".format(sys.exc_traceback.tb_lineno, e))
	if sensor in data and data[sensor]=={}: del data[sensor]
	U.muxTCA9548Areset()
	return data	   

		


# ===========================================================================
# TCS34725
# ===========================================================================

def getTCS34725(sensor, data):
	global sensorTCS, TCSStarted
	global sensors, sValues, displayInfo
	if sensor not in sensors: return data

	try:
		data[sensor] ={}
		for devId in sensors[sensor] :
			i2cAdd = U.muxTCA9548A(sensors[sensor][devId])
			try:
					ii= TCSStarted
			except:
					TCSStarted=1
					sensorTCS ={}

			try :
				if devId   not in  sensorTCS:
						sensorTCS[devId] = TCS34725(address=i2cAdd,integrationTime=0xEB, gain=0x01)
						sensorTCS[devId].setInterrupt(False)
						time.sleep(1)

				rgb = sensorTCS[devId].getRawData()
				colorTemp = sensorTCS[devId].calculateColorTemperature(rgb)
				lux = sensorTCS[devId].calculateLux(rgb)
				sensorTCS[devId].setInterrupt(True)
				lux= float(lux)
				if lux>=0:
					data[sensor][devId]={}
					data[sensor][devId]["clear"]=rgb["c"]
					data[sensor][devId]["red"]	=rgb["r"]
					data[sensor][devId]["green"]=rgb["g"]
					data[sensor][devId]["blue"] =rgb["b"]
					data[sensor][devId]["colorTemp"] =colorTemp
					data[sensor][devId]["lux"] =lux
					putValText(sensors[sensor][devId],[lux],["lux"])
					time.sleep(0.1)	   
				if devId in badSensors: del badSensors[devId]
			except: 
				data= incrementBadSensor(devId,sensor,data)
	except	Exception, e:
		U.toLog(-1, u"in Line {} has error={}".format(sys.exc_traceback.tb_lineno, e))
	if sensor in data and data[sensor]=={}: del data[sensor]
	return data






# ===========================================================================
# MS5803
# ===========================================================================

def getMS5803(sensor, data):
	global sensorMS5803, MS5803Started
	global sensors, sValues, displayInfo
	if sensor not in sensors: return data

	try:
		data[sensor] ={}
		for devId in sensors[sensor] :
			i2cAdd = U.muxTCA9548A(sensors[sensor][devId])
			type   = sensors[sensor][devId]["type"]
			try:
					ii= MS5803Started
					##U.setStopCondition(on=True)  # not needed
			except:
					MS5803Started=1
					sensorMS5803 ={}

			try :
				if devId   not in  sensorMS5803:
						sensorMS5803[devId] = MS5803(address=i2cAdd,type=type)
						time.sleep(1)

				temp, press = sensorMS5803[devId].getData()

				if temp >-90:
					try:	temp +=	 float(sensors[sensor][devId]["offsetTemp"])
					except: pass
					data[sensor][devId]={}
					data[sensor][devId]["temp"]= round(temp,1)
					if press >-90:
						try:	press +=  float(sensors[sensor][devId]["offsetPress"])
						except: pass
						data[sensor][devId]["press"]=press
					if devId in badSensors: del badSensors[devId]

				else:
					data= incrementBadSensor(devId,sensor,data)
			except: 
				data= incrementBadSensor(devId,sensor,data)
	except	Exception, e:
		U.toLog(-1, u"in Line {} has error={}".format(sys.exc_traceback.tb_lineno, e))
	if sensor in data and data[sensor]=={}: del data[sensor]
	U.muxTCA9548Areset()
	return data



# ===========================================================================
# ADC121
# ===========================================================================

def getADC121(sensor, data):
	global sensorADC121, ADC121Started
	global sensors, sValues, displayInfo
	if sensor not in sensors: return data

	try:
		data[sensor] ={}
		for devId in sensors[sensor] :
			i2cAdd = U.muxTCA9548A(sensors[sensor][devId])
			type   = sensors[sensor][devId]["type"]
			try:
					ii= ADC121Started
					##U.setStopCondition(on=True)  # not needed
			except:
					ADC121Started=1
					sensorADC121 ={}

			try :
				if devId   not in  sensorADC121:
						sensorADC121[devId] = ADC121(address=i2cAdd,type=type)
						time.sleep(1)

				adc = sensorADC121[devId].getData()
				if adc >-90:
					data[sensor][devId]={}
					data[sensor][devId]["adc"]=adc
				else:
					data= incrementBadSensor(devId,sensor,data)
			except	Exception, e:
				print  u"in Line {} has error={}".format(sys.exc_traceback.tb_lineno, e)
				data= incrementBadSensor(devId,sensor,data)
	except	Exception, e:
		U.toLog(-1, u"in Line {} has error={}".format(sys.exc_traceback.tb_lineno, e))
	if sensor in data and data[sensor]=={}: del data[sensor]
	return data


# ===========================================================================
# OPT3001
# ===========================================================================

def getOPT3001(sensor, data):
	global sensorOPT3001, OPT3001Started
	global sensors, sValues, displayInfo
	if sensor not in sensors: return data

	try:
		data[sensor] ={}
		for devId in sensors[sensor] :
			i2cAdd = U.muxTCA9548A(sensors[sensor][devId])
			try:
					ii= OPT3001Started
					##U.setStopCondition(on=True)  # not needed
			except:
					OPT3001Started=1
					sensorOPT3001 ={}

			try :
				if devId   not in  sensorOPT3001:
						sensorOPT3001[devId] = OPT3001(address=i2cAdd)
						time.sleep(1)

				lux = round(sensorOPT3001[devId].readLux(),2)
				if lux>=0:
					data[sensor][devId]={}
					data[sensor][devId]["illuminance"]=lux
					putValText(sensors[sensor][devId],[lux],["lux"])
					time.sleep(0.1)	   
				if devId in badSensors: del badSensors[devId]
			except: 
				data= incrementBadSensor(devId,sensor,data)
	except	Exception, e:
		U.toLog(-1, u"in Line {} has error={}".format(sys.exc_traceback.tb_lineno, e))
	if sensor in data and data[sensor]=={}: del data[sensor]
	U.muxTCA9548Areset()
	return data



# ===========================================================================
# getVEM7700
# ===========================================================================
def getVEML7700(sensor, data):
	global sensorVEML7700, VEML7700Started
	global sensors, sValues, displayInfo

	if sensor not in sensors: return data

	try:
		data[sensor] ={}
		for devId in sensors[sensor] :
			i2cAdd = U.muxTCA9548A(sensors[sensor][devId])
			try:
					ii= VEML7700Started
			except:
					VEML7700Started=1
					sensorVEML7700 ={}
			try :
				if devId   not in  sensorVEML7700:
					sensorVEML7700[devId] = VEML7700(address=i2cAdd)
				ambient,white= sensorVEML7700[devId].getLight()
				## print ambient,white
				if ambient>=0:
					data[sensor][devId]					= {}
					data[sensor][devId]["ambient"]		= round(ambient,2)
					data[sensor][devId]["white"]		= round(white,2)
					putValText(sensors[sensor][devId],[ambient],["lux"])
					U.toLog(2, u"VEML7700: "+ unicode(data[sensor][devId]))
					time.sleep(0.1)	   
				if devId in badSensors: del badSensors[devId]
			except	Exception, e:
				U.toLog(-1, u"in Line {} has error={}".format(sys.exc_traceback.tb_lineno, e))
				data= incrementBadSensor(devId,sensor,data)
	except	Exception, e:
		U.toLog(-1, u"in Line {} has error={}".format(sys.exc_traceback.tb_lineno, e))
	if sensor in data and data[sensor]=={}: del data[sensor]
	U.muxTCA9548Areset()
	return data


# ===========================================================================
# getVEML6030
# ===========================================================================
def getVEML6030(sensor, data):
	global sensorVEML6030, VEML6030Started
	global sensors, sValues, displayInfo

	if sensor not in sensors: return data

	try:
		data[sensor] ={}
		for devId in sensors[sensor] :
			i2cAdd = U.muxTCA9548A(sensors[sensor][devId])
			try:
					ii= VEML6030Started
			except:
					VEML6030Started=1
					sensorVEML6030 ={}
			try :
				if devId   not in  sensorVEML6030:
					sensorVEML6030[devId] = VEML6030(address=i2cAdd)
				ambient,white= sensorVEML6030[devId].getLight()
				if ambient>=0:
					data[sensor][devId]					= {}
					data[sensor][devId]["ambient"]		= round(ambient,2)
					data[sensor][devId]["white"]		= round(white,2)
					putValText(sensors[sensor][devId],[ambient],["lux"])
					U.toLog(2, u"VEML6030: "+ unicode(data[sensor][devId]))
					time.sleep(0.1)	   
				if devId in badSensors: del badSensors[devId]
			except: 
				data= incrementBadSensor(devId,sensor,data)
	except	Exception, e:
		U.toLog(-1, u"in Line {} has error={}".format(sys.exc_traceback.tb_lineno, e))
	if sensor in data and data[sensor]=={}: del data[sensor]
	U.muxTCA9548Areset()
	return data


# ===========================================================================
# getVEML6040
# ===========================================================================

def getVEML6040(sensor, data):
	global sensorVEML6040, VEML6040Started
	global sensors, sValues, displayInfo

	if sensor not in sensors: return data

	try:
		data[sensor] ={}
		for devId in sensors[sensor] :
			i2cAdd = U.muxTCA9548A(sensors[sensor][devId])
			try:
					ii= VEML6040Started
			except:
					VEML6040Started=1
					sensorVEML6040 ={}
			try :
				if devId   not in  sensorVEML6040:
					sensorVEML6040[devId] = VEML6040(address=i2cAdd)
				r,g,b,w = sensorVEML6040[devId].getLight()
				w= float(w)
				if w>=0:
					data[sensor][devId]={}
					data[sensor][devId]["red"]	  =round(r,1)
					data[sensor][devId]["green"]  =round(g,1)
					data[sensor][devId]["blue"]	  =round(b,1)
					data[sensor][devId]["white"]  =round(w,1)
					putValText(sensors[sensor][devId],[w],["lux"])
					time.sleep(0.1)	   
				if devId in badSensors: del badSensors[devId]
			except	Exception, e:
				U.toLog(-1, u"in Line {} has error={}".format(sys.exc_traceback.tb_lineno, e))
				data= incrementBadSensor(devId,sensor,data)
	except	Exception, e:
		U.toLog(-1, u"in Line {} has error={}".format(sys.exc_traceback.tb_lineno, e))
	if sensor in data and data[sensor]=={}: del data[sensor]
	U.muxTCA9548Areset()
	return data

#
# ===========================================================================
# TMP102
# ===========================================================================
def getTMP102(sensor, data):
	global sensorTMP102, TMP102Started
	global sensors, sValues, displayInfo
   
	if sensor not in sensors: return data

	try:
		ii= TMP102Started
	except:	   
		TMP102Started=1
		sensorTMP102 ={}

	try:
		data[sensor] ={}
		for devId in sensors[sensor] :
			i2cAdd = U.muxTCA9548A(sensors[sensor][devId])
			if devId not in sensorTMP102:
				sensorTMP102[devId] = smbus.SMBus(1)
			tRaw =	sensorTMP102[devId].read_word_data(i2cAdd,0)
			t = (((tRaw << 8) & 0xFF00) + (tRaw >> 8)>>4)
			if t > 2047: t = t-4096
			t= float(t)*0.0625
			if t!="":
				try:	t = (float(t) + float(sensors[sensor][devId]["offsetTemp"]))
				except: pass
				data[sensor][devId]={"temp":round(t,1)}
				putValText(sensors[sensor][devId],[t],["temp"])
				if devId in badSensors: del badSensors[devId]
				time.sleep(0.1) 
			else:	 
				data= incrementBadSensor(devId,sensor,data)
	except	Exception, e:
		U.toLog(-1, u"in Line {} has error={}".format(sys.exc_traceback.tb_lineno, e))
	if sensor in data and data[sensor]=={}: del data[sensor]
	U.muxTCA9548Areset()
	return data	   


# ===========================================================================
# getIS1145
# ===========================================================================

def getIS1145(sensor, data):
	global sensorIS1145, IS1145Started
	global sensors, sValues, displayInfo

	if sensor not in sensorList : return data	 
	try:
			ii= IS1145Started
	except:
			IS1145Started=1
			sensorIS1145 ={}
	try:
		data[sensor] ={}
		for devId in sensors[sensor] :
			i2cAdd = U.muxTCA9548A(sensors[sensor][devId])
			if devId   not in  sensorIS1145:
				sensorIS1145[devId] = IS1145(i2cAddress=i2cAdd)
				
				
			v,u,i = sensorIS1145[devId].getLight()
			try: 
				v= float(v)
				if v>=0:
					data[sensor][devId]={}
					data[sensor][devId]["visible"]	  =round(v,1)
					data[sensor][devId]["UV"]		  =round(u,1)
					data[sensor][devId]["IR"]		  =round(i,1)
					putValText(sensors[sensor][devId],[v],["lux"])
					time.sleep(0.1)	   
				if devId in badSensors: del badSensors[devId]
			except:
				data= incrementBadSensor(devId,sensor,data)
	except	Exception, e:
		U.toLog(-1, u"in Line {} has error={}".format(sys.exc_traceback.tb_lineno, e))
		data= incrementBadSensor(devId,sensor,data)
	if sensor in data and data[sensor]=={}: del data[sensor]
	U.muxTCA9548Areset()
	return data	   


# ===========================================================================
# getVEML6075
# ===========================================================================

def getVEML6075(sensor, data):
	global sensorVEML6075, VEML6075Started
	global sensors, sValues, displayInfo

	if sensor not in sensorList : return data	 

	try:
		data[sensor] ={}
		for devId in sensors[sensor] :
			i2cAdd = U.muxTCA9548A(sensors[sensor][devId])
			try:
				ii= VEML6075Started
			except:
				VEML6075Started=1
				sensorVEML6075 ={}
			try :
				if devId   not in  sensorVEML6075:
					sensorVEML6075[devId] = VEML6075(i2cAddress=i2cAdd)
				UVA,UVB= sensorVEML6075[devId].getLight()
				#print UVA,UVB
				if UVA !="":
					UVA= float(UVA)
					if UVA >= 0:
						data[sensor][devId]={}
						data[sensor][devId]["UVA"]=UVA
						data[sensor][devId]["UVB"]=UVB
						time.sleep(0.1)	   
					if devId in badSensors: del badSensors[devId]
				else:
					data= incrementBadSensor(devId,sensor,data)
			except	Exception, e:
				U.toLog(-1, u"in Line {} has error={}".format(sys.exc_traceback.tb_lineno, e))
				data= incrementBadSensor(devId,sensor,data)
	except	Exception, e:
		U.toLog(-1, u"in Line {} has error={}".format(sys.exc_traceback.tb_lineno, e))
	if sensor in data and data[sensor]=={}: del data[sensor]
	U.muxTCA9548Areset()
	return data	   

# ===========================================================================
# TSL2561
# ===========================================================================
def getTSL2561(sensor, data):
	global sensorTSL2561, TSL2561Started
	global sensors, sValues, displayInfo

	if sensor not in sensorList : return data	 

	try:
		ii= TSL2561Started
	except:
		TSL2561Started=1
		sensorTSL2561 ={}

	try:
		data[sensor] ={}
		for devId in sensors[sensor] :
			i2cAdd = U.muxTCA9548A(sensors[sensor][devId])
			if devId not in sensorTSL2561 :
					sensorTSL2561[devId]=TSL2561(address=i2cAdd)
			ret =  sensorTSL2561[devId].readLux(gain = 1)
			if ret!="":
				ret["lux"] = round(ret["lux"],2)
				data[sensor][devId]=ret	 # this is ~ {'lux': 0, 'IR': 51755, 'ambient': 2424}
				putValText(sensors[sensor][devId],[ret["ambient"]],["lux"])
				if devId in badSensors: del badSensors[devId]
				time.sleep(0.1)
			else:
				data= incrementBadSensor(devId,sensor,data)
		if sensor in data and data[sensor]=={}: del data[sensor]
	except	Exception, e:
		U.toLog(-1, u"in Line {} has error={}".format(sys.exc_traceback.tb_lineno, e))
	if sensor in data and data[sensor]=={}: del data[sensor]
	U.muxTCA9548Areset()
	return data	   

 
 
# ===========================================================================
# ADS1x15
# ===========================================================================
 
def getADS1x15(sensor, data):
	global sensorADS1x15, ADS1x15Started
	global sensors, sValues, displayInfo


	if sensor not in sensors : return data	  
	data[sensor] ={}

	try:
		ii= ADS1x15Started
	except:	   
		ADS1x15Started=1
		sensorADS1x15 ={}
	try:
		for devId in sensors[sensor] :
			i2cAdd = U.muxTCA9548A(sensors[sensor][devId])
			if devId not in sensorADS1x15 :
				rm=0x01
				if sensors[sensor][devId]["resModel"] != "":
					rm=sensors[sensor][devId]["resModel"]
					if rm!=0:	rm=0x01
					else:		rm=0x00
				sensorADS1x15[devId]=ADS1x15(address=i2cAdd,ic=rm)
			g=6144
			if sensors[sensor][devId]["gain"] != "" :
				g=sensors[sensor][devId]["gain"]
			if g>6144: g=6144
			if g<256:  g=256
			if g%2!=0: g=6144

			if "input" in sensors[sensor][devId]:
				input= int(sensors[sensor][devId]["input"])
			else:
				input=0
			v=[0,0,0,0]
			data[sensor][devId]={}
			for inp in range(4):
				v[inp] = ("%4d"%sensorADS1x15[devId].readADCSingleEnded(channel=inp, pga=g, sps=250)).strip()
				if devId in badSensors: del badSensors[devId]
			if sensor.find("-1") ==-1:
				for inp in range(4):
					data[sensor][devId]["INPUT_"+str(inp)]	= v[inp]
			else:
					data[sensor][devId]["INPUT_0"]	= v[int(sensors[sensor][devId]["input"])]

	except	Exception, e:
		data= incrementBadSensor(devId,sensor,data)
		U.toLog(-1, u"in Line {} has error={}".format(sys.exc_traceback.tb_lineno, e))
	if sensor in data and data[sensor]=={}: del data[sensor]
	U.muxTCA9548Areset()
	return data	   








# ===========================================================================
# VEML6070
# ===========================================================================


def getVEML6070(sensor, data):
	global sensorVEML6070, VEML6070Started
	global sensors, sValues, displayInfo

	if sensor not in sensors : return data	  
	try:
		data[sensor] ={}
		for devId in sensors[sensor] :
			try:
				try:
					ii= VEML6070Started
				except:	   
					VEML6070Started=1
					sensorVEML6070 ={}
				i2cAdd =U.muxTCA9548A(sensors[sensor][devId])
				props = sensors[sensor][devId]
				if devId not in sensorVEML6070 :
					if "integrationTime" in props and "rSet" in props: 
						sensorVEML6070[devId]=VEML6070(integrationTime=int(props["integrationTime"]),rSet=int(props["rSet"])  )
						sensorVEML6070[devId].set_integration_time(int(props["integrationTime"]))
					elif "integrationTime" not in props and "rSet" in props: 
						sensorVEML6070[devId]=VEML6070(rSet=int(props["rSet"]))
					elif "integrationTime" in props	 and "rSet" not in props: 
						sensorVEML6070[devId]=VEML6070(integrationTime=int(props["integrationTime"]))
						sensorVEML6070[devId].set_integration_time(int(props["integrationTime"]))
					else: 
						sensorVEML6070[devId]=VEML6070()
						sensorVEML6070[devId].set_integration_time(2)
				uv = ("%.1f"%sensorVEML6070[devId].get_uva_light_intensity()).strip()
				if uv !="":
					uv= float(uv)
					if uv >= 0:
						data[sensor][devId]={}
						data[sensor][devId]["UV"]=uv
						time.sleep(0.1)	   
					if devId in badSensors: del badSensors[devId]
				else:
					data= incrementBadSensor(devId,sensor,data)
			except:
				data= incrementBadSensor(devId,sensor,data)
	except	Exception, e:
			U.toLog(-1, u"in Line {} has error={}".format(sys.exc_traceback.tb_lineno, e))
	if sensor in data and data[sensor]=={}: del data[sensor]
	U.muxTCA9548Areset()
	return data


# ===========================================================================
# PCF8591
# ===========================================================================

def getPCF8591(sensor, data):
	global PCF8591Started, sensorPCF8591
	global sensors, sValues, displayInfo

	if sensor not in sensors : return data	  
	   
	try:
		ii= PCF8591Started
	except:	   
		PCF8591Started=1
		sensorPCF8591={}
	try:
		data[sensor] ={}
		for devId in sensors[sensor]:
			i2cAdd =U.muxTCA9548A(sensors[sensor][devId])
			if str(devId) not in sensorPCF8591:
				sensorPCF8591[devId]=smbus.SMBus(1)
				
			if "input" in sensors[sensor][devId]:
				input= int(sensors[sensor][devId]["input"])
			else:
				input=0
			data[sensor][devId] ={}
			v=[0,0,0,0]
			for inp in range(4):
					sensorPCF8591[devId].write_byte(i2cAdd,0x40+inp)
					sensorPCF8591[devId].read_byte(i2cAdd) # dummy read to start conversion
					v[inp]= int(sensorPCF8591[devId].read_byte(i2cAdd) *3300./255.)
					if devId in badSensors: del badSensors[devId]
			if sensor.find("-1") ==-1:
				for inp in range(4):
					data[sensor][devId]["INPUT_"+str(inp)]	= v[inp]
			else:
					data[sensor][devId]["INPUT_0"]	= v[input]
	except	Exception, e:
		U.toLog(-1, u"in Line {} has error={}".format(sys.exc_traceback.tb_lineno, e))
		data= incrementBadSensor(devId,sensor,data)
	if sensor in data and data[sensor]=={}: del data[sensor]
	U.muxTCA9548Areset()
	return data


# ===========================================================================
# utils II
# ===========================================================================

def putValText(sensorInfo,values,params):
	global sValues,displayInfo
	if "displayEnable" not in sensorInfo: return 
	if sensorInfo["displayEnable"] !="1": return 
	
	llength= len(values)
	for ii in range(llength):
		sValues[params[ii]][0].append(values[ii])
		if "logScale" in sensorInfo:	
			sValues[params[ii]][2].append(sensorInfo["logScale"])
		else:
			sValues[params[ii]][2].append("0")

	if "displayText" in sensorInfo:
		splits = sensorInfo["displayText"].split(";")
		if len(splits)== llength:
			for ii in range(llength):
				sValues[params[ii]][1].append(splits[ii])
		else:	 
			for ii in range(llength):
				sValues[params[ii]][1].append("")
	else:	 
		for ii in range(llength):
			sValues[params[ii]][1].append("")

		
	displayInfo["display"]= True
			
	return 

def incrementBadSensor(devId,sensor,data,text="badSensor"):
	global badSensors
	try:
		if devId not in badSensors:badSensors[devId] ={"count":0,"text":text}
		badSensors[devId]["count"] +=1
		badSensors[devId]["text"]  +=text
		#print badSensors
		if	badSensors[devId]["count"]	> 2:
			if sensor not in data: data={sensor:{devId:{}}}
			if devId not in data[sensor]: data[sensor][devId]={}
			data[sensor][devId]["badSensor"] = badSensors[devId]["text"]
			del badSensors[devId]
	except	Exception, e:
		U.toLog(-1, u"in Line {} has error={}".format(sys.exc_traceback.tb_lineno, e))
	return data 


		
# ===========================================================================
# sensor end
# ===========================================================================

 
# ===========================================================================
# read params
# ===========================================================================


def readParams():
		global sensorList, sensors, sendToIndigoSecs, sensorRefreshSecs
		global output
		global tempUnits, pressureUnits, distanceUnits
		global oldRaw, lastRead
		global addNewOneWireSensors

		rCode= False

		inp,inpRaw,lastRead2 = U.doRead(lastTimeStamp=lastRead)
		if inp == "": return rCode
		if lastRead2 == lastRead: return rCode
		lastRead  = lastRead2
		if inpRaw == oldRaw: return 
		oldRaw	   = inpRaw

		oldSensor		  = sensorList
		sensorList=[]
		sensorsOld= copy.copy(sensors)
		outputOld= unicode(output)


		U.getGlobalParams(inp)
		if "debugRPI"			  in inp:  G.debug=				int(inp["debugRPI"]["debugRPISENSOR"])
		if "output"				  in inp: output=				   (inp["output"])
		if "tempUnits"			  in inp: tempUnits=			   (inp["tempUnits"])
		if "pressureUnits"		  in inp: pressureUnits=		   (inp["pressureUnits"])
		if "distanceUnits"		  in inp: distanceUnits=		   (inp["distanceUnits"])
		if "sensors"			  in inp: sensors =				   (inp["sensors"])
		if "sensorRefreshSecs"	  in inp: sensorRefreshSecs = float(inp["sensorRefreshSecs"])
		if "addNewOneWireSensors" in inp: addNewOneWireSensors =   (inp["addNewOneWireSensors"])


		sensorList=""
		for sensor in sensors:
			sensorList+=sensor.split("-")[0]+","


		### any changes?
		sensorUp = U.doWeNeedToStartSensor(sensors, sensorsOld, sensorType="i2c")
		if outputOld != unicode(output): rCode=True
		
		
				 
		if sensorUp =={}:
			if os.path.isfile(G.homeDir+"temp/simplei2csensors.dat"):
				os.remove(G.homeDir+"temp/simplei2csensors.dat")
			exit(0)

		return rCode





#################################
def doDisplay():
	global displayInfo,sValues
	global output
	global initDisplay
	global tempUnits, pressureUnits, distanceUnits

	if "display" not in displayInfo: return

	if not displayInfo["display"]: return
	
	try:
		##print " to display:", dist, output
		if len(output) ==0: return
		if "display" not in output: return

		try:
			a=initDisplay  # this fails if fist time
		except:
			initDisplay=time.time() # start display.py if we come here after startup first time
			print " starting display from simplei2csensors 1"
			os.system("/usr/bin/python "+G.homeDir+"display.py	&" )
			time.sleep(0.2)

		if time.time() - initDisplay > 3600*3: # once every 3 hour restart display
			print " starting display from simplei2csensors 2"
			os.system("/usr/bin/python "+G.homeDir+"display.py	&" )
			initDisplay =time.time()
			time.sleep(0.2)

		
		if not U.pgmStillRunning("display.py"):
			print " starting display from simplei2csensors 3"
			os.system("/usr/bin/python "+G.homeDir+"display.py	&" )
			time.sleep(0.2)
			initDisplay =time.time()


		x0T = 0
		x1V = 0
		reduceFont =0.88
			
		for devid in output["display"]:
			ddd = output["display"][devid][0]
			if "devType" not in ddd:  continue
			devType		= ddd["devType"]
			displayResolution	  = ""
			try:
				if "displayResolution" in ddd:
					displayResolution	= ddd["displayResolution"].split("x")
					displayResolution	= [int(displayResolution[0]),int(displayResolution[1])]				   
			except:pass
			if "intensity"	in ddd: 
				intensity  = int(ddd["intensity"])

			displayWAIT				= "wait"
			scrollDelay				= 1
			scrollDelayBetweenPages = 1.
			scrollDelaySet			= 1.


			if "scrollSpeed"  in ddd:
				if	 ddd["scrollSpeed"] =="slow":
					scrollDelaySet =2.0
					scrollDelayBetweenPages =2.
				elif ddd["scrollSpeed"] =="fast":
					scrollDelayBetweenPages =0.5
					scrollDelaySet = 0.5

			scrollxy =""
			if "scrollxy"  in ddd: 
				scrollxy  = ddd["scrollxy"]
			if scrollxy not in ["up","down","left","right"]:
				scrollxy=""	   

			delayStart				=1
			if scrollxy =="": 
				delayStart			=1.2

			
			showDateTime ="1"
			if "showDateTime"  in ddd: 
				showDateTime  = ddd["showDateTime"]
				
				
			extraPageForDisplay=[]
			if "extraPageForDisplay"  in ddd: 
				extraPageForDisplay	 = ddd["extraPageForDisplay"]

			if os.path.isfile(G.homeDir+"temp/extraPageForDisplay.inp"):
				f = open(G.homeDir+"temp/extraPageForDisplay.inp","r")
				extraPageForDisplay=json.loads( f.read())
				f.close()
			
			font =""
			fwidth0 ="22"
			fwidth1 ="30"
			pos1= "[0,0]"	 
			intensity=100
			fillT =[]
			fill = [int(255*intensity/100),int(255*intensity/100),int(255*intensity/100)]
			fillCL =[200,200,200]
			if devType.find("RGBmatrix")>-1:
				scrollDelay =0.05
				fill0 = [0,0,0]
				fwidth0 ="0"
				fwidth1 ="0"

			if devType == "RGBmatrix16x16":
				ymax = 16
				xmax = 16
				fontUP	  ="5x8.pil"	
				fontDOWN  ="5x8.pil"	
				posy0= 0	
				posy1= 8	
				
			elif devType == "RGBmatrix32x16":
				ymax = 16
				xmax = 32
				fontUP	  ="5x8.pil"	
				fontDOWN  ="5x8.pil"	
				posy0= 0	
				posy1= 8	
				
			elif devType == "RGBmatrix32x32":
				ymax = 32
				xmax = 32
				fontUP	  ="5x8.pil"	
				fontDOWN  ="8x13.pil"	 
				posy0= 1	
				posy1= 16	 
				reduceFont =1
				
			elif devType == "RGBmatrix64x32":
				ymax = 32
				xmax = 64
				fontUP	  ="6x9.pil"	
				fontDOWN  ="9x18.pil"	 
				posy0= 1	
				posy1= 16	 
				
			elif devType == "RGBmatrix96x32":
				ymax = 32
				xmax = 96
				fontUP	  ="6x9.pil"	
				fontDOWN  ="9x18.pil"	 
				posy0= 1	
				posy1= 16	 
				clock ="[10,0,25,16]"
				fontCL ="9x18.pil"	  
				
			elif devType=="ssd1351":
				scrollDelay =0.05
				fill0 = [0,0,0]
				scrollDelay =0.015
				ymax = 128
				xmax = 128
				fontUP	  ="Arial.ttf"	  
				fontDOWN  ="Arial.ttf"	  
				fwidth0 ="26"
				fwidth1 ="48"
				posy0= 5	
				posy1= 60	 
				reduceFont = 0.91
				
			elif devType=="st7735":
				scrollDelay =0.015
				fill0 = [0,0,0]
				reset = fill0
				ymax = 128
				xmax = 160
				fontUP	  ="Arial.ttf"	  
				fontDOWN  ="Arial.ttf"	  
				fwidth0 ="36"
				fwidth1 ="60"
				posy0= 5	
				posy1= 60	 
				
			elif devType in ["ssd1306"]:
				scrollDelay =0.015
				ymax = 64
				xmax = 128
				fill = 255
				fillT=[255,255,255,255,255,255]
				fill0=0
				fontUP	  ="Arial.ttf"	  
				fontDOWN  ="Arial.ttf"	  
				fwidth0 ="14"
				fwidth1 ="30"
				posy0= 0	
				posy1= 30	 
				
			elif devType in ["sh1106"]:
				scrollDelay =0.015
				ymax = 64
				xmax = 128
				fill = 255
				fillT=[255,255,255,255]
				fill0=0
				fontUP	  ="Arial.ttf"	  
				fontDOWN  ="Arial.ttf"	  
				fwidth0 ="14"
				fwidth1 ="30"
				posy0= 0	
				posy1= 30	 
				
			elif devType.lower().find("screen") >-1:
				reduceFont	= 0.930
				scrollDelay = 0.015
				fill0		= [0,0,0]
				reset		= fill0
				fontUP		="Arial.ttf"	
				fontDOWN	="Arial.ttf"	
				ymax	= 480
				xmax	= 800
				fwidth0 = 150
				fwidth1 = 250
				x0T		= 10
				x1V		= 0
				posy0	= 0	   
				posy1	= 210	 
				if len( displayResolution ) ==2:
					try:
						ymax = displayResolution[1]
						xmax = displayResolution[0]
					except:
						pass
				try:	
					fwidth0 = int(fwidth0 *ymax / 500) 
					fwidth1 = int(fwidth1 *ymax / 500) 
					posy1	= int(ymax/2.) 
				except: pass	
##		  print xmax,ymax,posy1,fwidth1
		
		nPages=0
		posText0=[]
		posText1=[]
		outText0=[]
		outText1=[]




		if scrollxy !="":
			reset		= ""
		else:
			reset		= fill0
			displayWAIT ="immediate"
		if True:
			dx=0;dy=0
			if scrollxy in ["left","right"]:
				dx = xmax
				dy = 0
			elif scrollxy in ["up","down"]:
				dx = 0
				dy = ymax 

			if showDateTime =="1":
				nPages = 2	
			else:
				nPages = 0 
				
			# sValues = {"temp":[v1,v2,v3],"hum":[v1,v2,v3,v4],....}
			#print sValues
			if "temp" in sValues:
				theValues	= sValues["temp"][0]
				theText		= sValues["temp"][1]
				if len(theValues) >0:
					for	 ii in range(len(theValues)):
						t =	 float(theValues[ii])
						if tempUnits == u"Fahrenheit":
							t = t * 9. / 5. + 32.
							tu = " Temp[F]"
						elif tempUnits == u"Kelvin":
							t+= 273.15
							tu= " Temp[K]"
						else:
							tu= " Temp[C]"
						if theText[ii] !="":
							tu= theText[ii]
						t = "%.1f" % t
						if devType not in ["sh1106","ssd1306"]:
							fillT+= [0,255,0]
						posText0.append([nPages*dx+x0T,nPages*dy+ posy0])
						posText1.append([nPages*dx+x1V,nPages*dy+ posy1])
						outText0.append(tu)
						outText1.append(t)
						nPages+=1

			if "hum" in sValues:
				theValues	= sValues["hum"][0]
				theText		= sValues["hum"][1]
				if len(theValues) >0:
					for	 ii in range(len(theValues)):
						h =	 float(theValues[ii])
						if devType not in ["sh1106","ssd1306"]:
							fillT+= [0,0,255]
						posText0.append([nPages*dx+x0T,nPages*dy+ posy0])
						posText1.append([nPages*dx+x1V,nPages*dy+ posy1])
						if theText[ii] !="":
							outText0.append(theText[ii])
						else:	 
							outText0.append("  Hum[%]")
						outText1.append("	%2d"%float(h))
						nPages+=1

			if "press" in sValues:
				theValues	= sValues["press"][0]
				theText		= sValues["press"][1]
				if len(theValues) >0:
					for	 ii in range(len(theValues)):
						p =	 float(theValues[ii])
						if pressureUnits == "atm":							   p *= 0.000009869233; p = "%6.3f"%p; pu= "P[atm]"
						elif pressureUnits == "bar":						   p *= 0.00001; p = "%7.4f" % p;	   pu= "P[Bar]"
						elif pressureUnits == "mbar":						   p *= 0.01; p = "%6.1f" % p	;	   pu= "P[mBar]"
						elif pressureUnits == "mm":							   p *= 0.00750063; p = "%6.1f"%p;	   pu= 'P[mmHg]'
						elif pressureUnits == "Torr":						   p *= 0.00750063; p = "%6.1f"%p;	   pu= "P[Torr]"
						elif pressureUnits == "inches":						   p *= 0.000295299802; p = "%6.2f"%p; pu= 'P["Hg]'
						elif pressureUnits == "PSI":						   p *= 0.000145038; p = "%6.2f"%p;	   pu= "P[PSI]"
						elif pressureUnits == "hPascal":					   p *= 0.01; p = "%6.1f"% p;		   pu= "P[hPa]"
						else:												   p = "%9d" % p;					   pu= "P[Pa]"
						p=p.strip(); pu=pu.strip()	  
						
						if devType not in ["sh1106","ssd1306"]:
							fillT+= [255,0,0]
							
						posText0.append([nPages*dx+x0T,nPages*dy+ posy0])
						posText1.append([nPages*dx+x1V,nPages*dy+ posy1])
						if theText[ii] !="":
							outText0.append(theText[ii])
						else:	 
							outText0.append(pu)
						outText1.append(p)		  
						nPages+=1

			if "lux" in sValues:
				theValues	= sValues["lux"][0]
				theText		= sValues["lux"][1]
				logScale	= sValues["lux"][2]
				if len(theValues) >0:
					for	 ii in range(len(theValues)):
						lux =  theValues[ii]
						lux =  float(lux)
						if logScale[ii] =="1":
							l = ("%7.2f"%math.log10(max(1.,lux))).replace(" ","")
							lu	=  "[lux]-log"
						else:
							l = "%6d"%lux; lu = '[lux]'
						l=l.strip(); lu=lu.strip()	  
						if devType not in ["sh1106","ssd1306"]:
							fillT+= [255,0,0]
						posText0.append([nPages*dx+x0T,nPages*dy+ posy0])
						posText1.append([nPages*dx+x1V,nPages*dy+ posy1])
						if theText[ii] !="":
							outText0.append(theText[ii])
						else:	 
							outText0.append(lu)
						outText1.append(l)		  
						nPages+=1

			##print extraPageForDisplay
			if extraPageForDisplay !=[] and extraPageForDisplay !="":
				for newPage in extraPageForDisplay:
					if newPage[0] =="" and newPage[1] =="": continue
					posText0.append([nPages*dx+x0T,nPages*dy+ posy0])
					posText1.append([nPages*dx+x1V,nPages*dy+ posy1])
					if newPage[0] !="":
						outText0.append(newPage[0])
					else:	 
						outText0.append("")
					if newPage[1] !="":
						outText1.append(newPage[1])
					else:	 
						outText1.append("")
					color =[255,255,255]   
					if newPage[2] !="":
						try: color = json.loads("["+newPage[2].strip("(").strip(")").strip("[").strip("]")+"]")
						except:pass
					fillT.append(color)
					nPages+=1
				

			if showDateTime =="1":
				 sensorPages = nPages -2
			else:
				sensorPages	 = nPages
				
			if scrollxy == "": nPages=1
			#if devType=="st7735": nPages = 1
			out = {"resetInitial": "", "repeat": 999, "scrollxy":scrollxy, "scrollPages":str(nPages), "scrollDelayBetweenPages":str(scrollDelayBetweenPages), "scrollDelay":str(scrollDelay*scrollDelaySet), "command":[] }
			
			if showDateTime =="1":
				out["command"].append({"type": "date", "fill":str(fillCL), "delayStart":str(delayStart*scrollDelaySet), "display":displayWAIT, "reset":str(fill0)})
				out["command"].append({"type": "clock", "fill":str(fillCL), "delayStart":str(delayStart*scrollDelaySet), "display":displayWAIT, "reset":str(reset)})
			else:
				out["command"].append({"type": "NOP", "reset":str(fill0)})

			for ii in range(0,sensorPages):
				##if ii==0 :reset = fill0
				if scrollxy =="":reset = fill0
				else:	 reset = ""
				if ii==(sensorPages-1) or scrollxy =="":disp = "immediate"
				else:				   disp = "wait"
				next = outText0[ii]
				pos	 = posText0[ii]
				fwidthV = int(fwidth0)
				nred = len(next.strip()) - 8
				while nred > 0:
						fwidthV *=reduceFont
						nred -=1
				out["command"].append({"type": "text", "fill":str(fillT[ii]), "reset":str(reset), "delayStart":str(delayStart*scrollDelaySet), "position":pos, "display":"wait", "text":next, "font":fontUP, "width":str(int(fwidthV))})
				comma = ","
				next = outText1[ii]
				pos	 = posText1[ii]
				fwidthV = int(fwidth1)
				nred = len(next.strip()) - 4
				while nred > 0:
						fwidthV *=reduceFont
						nred -=1
				#print	"fwidthV,2",fwidthV ,fwidth1 ,nred ,next
				#print len(next.strip()), next , fwidth1, fwidthV
					
				out["command"].append({"type": "text", "fill":str(fillT[ii]), "delayStart":str(delayStart*scrollDelaySet), "position":pos, "display":disp, "text":next, "font":fontDOWN, "width":str(int(fwidthV))})
		#print out
		try:
			if os.path.isfile(G.homeDir+"temp/display.inp") and os.path.getsize(G.homeDir+"temp/display.inp") > 20000:
				wmode ="w"
			else:
				wmode ="a"
			f=open(G.homeDir+"temp/display.inp",wmode); f.write(json.dumps(out)+"\n"); f.close()
		except:
			try:
				U.toLog(-1,"retry to write to display.inp", doPrint=True )
				time.sleep(0.1)
				f=open(G.homeDir+"temp/display.inp","w"); f.write(json.dumps(out)+"\n"); f.close()
			except	Exception, e:
				U.toLog(-1,u"in Line {} has error={}".format(sys.exc_traceback.tb_lineno, e), doPrint=True )
				if unicode(e).find("No space left on device") >-1:
					os.system("rm "+G.homeDir+"temp/* ")
		return 
	except	Exception, e:
		U.toLog(-1,"in Line {} has error={}".format(sys.exc_traceback.tb_lineno, e), doPrint=True )
		U.toLog(-1,unicode(sValues), doPrint=True )





#################################
def makeLightsensorFile(data):
	global makeLightsensorFileTime
	try:
		ii=makeLightsensorFileTime
	except:
		makeLightsensorFileTime = 0
	if time.time() - makeLightsensorFileTime < 5: return 
	makeLightsensorFileTime = int(time.time())
	out=""
	for sensor in data:
		for devId in data[sensor]:
			if "ambient" in data[sensor][devId]:
				out = json.dumps({"light":float(data[sensor][devId]["ambient"]),"sensor":sensor,"time":time.time()})
				break
			if "white" in data[sensor][devId]:
				out = json.dumps({"light":float(data[sensor][devId]["white"]),"sensor":sensor,"time":time.time()})
				break
			if "visible" in data[sensor][devId]:
				out = json.dumps({"light":float(data[sensor][devId]["visible"]),"sensor":sensor,"time":time.time()})
				break
			if "lux" in data[sensor][devId]:
				out = json.dumps({"light":float(data[sensor][devId]["lux"]),"sensor":sensor,"time":time.time()})
				break
	if len(out) > 0:  
		f=open(G.homeDir+"temp/lightSensor.dat","w")
		f.write(out)
		f.close()

   
#################################
#################################
#################################
#################################
#################################
#################################
#################################
#################################
			 
global sensorList, sensors,badSensors
global c1,c2,c3,c4,c5,c6,c7,c8
global tempUnits, pressureUnits, distanceUnits
global regularCycle
global sValues, displayInfo
global oldRaw, lastRead
global sensorRefreshSecs
global addNewOneWireSensors

addNewOneWireSensors="0"

sensorRefreshSecs	= 90
oldRaw				= ""
lastRead			= 0
tempUnits			="Celsius"
pressureUnits		= "mBar"
distanceUnits		= "1"
loopCount			= 0
sensorList			= []
sensors				= {}
DHTpin				= 17
spi0				= 0
spi1				= 0
authentication		= "digest"
quick				= False
output				= {}

readParams()

if U.getIPNumber() > 0:
	U.toLog(-1," getsensors no ip number  exiting ", doPrint =True)
	time.sleep(10)
	exit()


myPID		= str(os.getpid())
U.killOldPgm(myPID,G.program+".py")# kill old instances of myself if they are still running

NSleep= int(sensorRefreshSecs)
if G.networkType  in G.useNetwork and U.getNetwork() == 1: 
	if U.getIPNumber() > 0:
		U.toLog(-1,"no ip number working, giving up", doPrint = True )
		time.sleep(10)
		exit()
eth0IP, wifi0IP, G.eth0Enabled,G.wifiEnabled = U.getIPCONFIG()


tt					= time.time()
badSensors			= {}
lastData			= {}
lastMsg				= 0
G.tStart			= tt
lastregularCycle	= tt
lastRead			= tt
regularCycle		= True
lastData			= {}
xxx 				= ""
while True:
	try:
		tt = time.time()
		data={}
		sValues={"temp":[[],[],[]],"press":[[],[],[]],"hum":[[],[],[]],"lux":[[],[],[]]}	  
		displayInfo={}
		if regularCycle:
# temp+ press .. 
			if "i2cBMExx"		in sensors: data = getBME("i2cBMExx",		 data)
			if "i2cBMP280"		in sensors: data = getBME("i2cBMP280",		 data,BMP=True)
			if "i2cBMPxx"		in sensors: data = getBMP("i2cBMPxx",		 data)
			if "i2cT5403"		in sensors: data = getT5403("i2cT5403",		 data)
			if "i2cMS5803"		in sensors: data = getMS5803("i2cMS5803",data)
## only temp 
			if "i2cMCP9808"		in sensors: data = getMCP9808("i2cMCP9808",	 data)
			if "i2cTMP102"		in sensors: data = getTMP102("i2cTMP102",	 data)
			if "i2cLM35A"		in sensors: data = getLM75A("i2cLM35A",		 data)
			if "i2cSHT21"		in sensors: data = getSHT21("i2cSHT21",		 data)
			if "i2cAM2320"		in sensors: data = getAM2320("i2cAM2320",	 data)
## light sensors 
			if "i2cTCS34725"	in sensors: data = getTCS34725("i2cTCS34725",data)
			if "i2cOPT3001"		in sensors: data = getOPT3001("i2cOPT3001",	 data)
			if "i2cVEML7700"	in sensors: data = getVEML7700("i2cVEML7700",  data)
			if "i2cVEML6030"	in sensors: data = getVEML6030("i2cVEML6030",data)
			if "i2cVEML6040"	in sensors: data = getVEML6040("i2cVEML6040",data)
			if "i2cVEML6070"	in sensors: data = getVEML6070("i2cVEML6070",data)
			if "i2cVEML6075"	in sensors: data = getVEML6075("i2cVEML6075",data)

			if "i2cIS1145"		in sensors: data = getIS1145("i2cIS1145",	 data)
			if "i2cTSL2561"		in sensors: data = getTSL2561("i2cTSL2561",	 data)
## adc sensors
			if "i2cPCF8591-1"	in sensors: data = getPCF8591("i2cPCF8591-1",data)
			if "i2cPCF8591"		in sensors: data = getPCF8591("i2cPCF8591",	 data)
			if "i2cADS1x15"		in sensors: data = getADS1x15("i2cADS1x15",	 data)
			if "i2cADS1x15-1"	in sensors: data = getADS1x15("i2cADS1x15-1",data)
			if "i2cADC121"		in sensors: data = getADC121("i2cADC121",data)


		doDisplay()

		loopCount +=1
		
		delta =-1
		changed = 0
		if lastData=={}: 
			changed = 1
		else:
			for sens in data:
				if changed>0: break
				if sens not in lastData:
					changed= 2
					break
				for devid in data[sens]:
					if changed>0: break
					if devid not in lastData[sens]:
						changed= 3
						break
					for devType in data[sens][devid]:
						if changed>0: changed = 4
						if devType not in lastData[sens][devid]:
							changed= 5
							break
						try:
							#print dd, lastData[sens][dd], data[sens][dd]
							xxx = U.testBad( data[sens][devid][devType],lastData[sens][devid][devType], xxx)

							if xxx > (G.deltaChangedSensor/100.): 
								changed = xxx
								break
						except	Exception, e:
							#print e
							#print lastData[sens][dd]
							#print data[sens][dd]
							changed = 7
							break
		#print "changed? ", changed,	   tt-lastMsg, G.sendToIndigoSecs ,	 tt-lastMsg, G.deltaChangedSensor, data
		if data !={} and (		changed >0 or	( (tt-lastMsg) >  G.sendToIndigoSecs  or (tt-lastMsg) > 200	 )		 ):
			lastMsg = tt
			lastData=copy.copy(data)
			try:
				U.sendURL({"sensors":data})
			except	Exception, e:
				U.toLog(-1, u"in Line {} has error={}".format(sys.exc_traceback.tb_lineno, e),permanentLog=True)
			time.sleep(0.05)

		quick = U.checkNowFile(G.program)				 

		U.makeDATfile(G.program, {"sensors":data})
		makeLightsensorFile(data)
		U.echoLastAlive(G.program)


		tt= time.time()
		NSleep = int(sensorRefreshSecs)*2
		if tt- lastregularCycle > sensorRefreshSecs:
			regularCycle = True
			lastregularCycle  = tt

		for n in range(NSleep):
			if quick: break
			readParams()
			time.sleep(0.5)
			quick = U.checkNowFile(G.program)				 
			if tt - lastRead > 5:
				lastRead = tt
				U.checkIfAliveNeedsToBeSend()
	except	Exception, e:
		U.toLog(-1, u"in Line {} has error={}".format(sys.exc_traceback.tb_lineno, e),permanentLog=True)
		time.sleep(5.)
sys.exit(0)
