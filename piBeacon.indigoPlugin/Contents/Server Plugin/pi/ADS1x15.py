#!/usr/bin/python
# -*- coding: utf-8 -*-
# by Karl Wachs
# feb 12 2020
# version 1.1 
##
##
from __future__ import division

import math

import	sys, os, time, json, datetime,subprocess,copy

sys.path.append(os.getcwd())
import	piBeaconUtils	as U
import	piBeaconGlobals as G

G.program = "ADS1x15"

try: import smbus
except: pass



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
				U.logger.log(30, u"in Line {} has error={}".format(sys.exc_traceback.tb_lineno, e))



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
				if  val > 0x7FFF:
					val= (val - 0xFFFF)*pga/32768.0
				else:
					val= ( (result[0] << 8) | (result[1]) )*pga/32768.0
				#print self.ic, sps, pga, channel, val, result
				return val
		except	Exception, e:
				U.logger.log(20, u"in Line {} has error={}".format(sys.exc_traceback.tb_lineno, e))



#
#################################
def startSensor(devId,i2cADR):
	global SENSOR, sensors, sensor, resModel

	try:
		if devId not in SENSOR:
			#U.logger.log(30, u"starting devId:{}".format(devId))
			SENSOR[devId]=ADS1x15(address=i2cADR, ic=resModel[devId]) 
			return 
	except	Exception, e:
		U.logger.log(20, u"in Line {} has error={}".format(sys.exc_traceback.tb_lineno, e))
	return 

#===========================================================================
# ADS1x15
# ===========================================================================
 
def getValues():
	global SENSOR, sensors, sensor, input, gain, resModel
	global badSensor, i2cAddress


	values = {}
	if sensor not in sensors:
		U.logger.log(30, "error sensor:{} , sensors:{}".format(sensor, sensors))
		return {}  
	try:
		for i2c in i2cAddress:
			for devId in i2cAddress[i2c]:
				values[devId] = ""
				inp = input[devId].split("-")
				v = 0; v1 = 0
				v =  (SENSOR[devId].readADCSingleEnded(channel=int(inp[0]), pga=gain[devId], sps=250))
				if len(inp) == 2:
					v1 =  (SENSOR[devId].readADCSingleEnded(channel=int(inp[1]), pga=gain[devId], sps=250))
				values[devId] = {"INPUT":round(v-v1,2)}
				

		#U.logger.log(30, u"getValues    devId: {:12s},  gain:{}, i2c:{},  v:{}, dv:{}".format(devId, gain[devId], i2c, v4, v-v1))
		#U.logger.log(30, u"getValues : input:{}, len:{};   v:{}; v1:{}".format(inp, len(inp), v, v1))
		badSensor = 0
		return values
	except	Exception, e:
		badSensor += 1
		U.logger.log(30, u"in Line {} has error={}".format(sys.exc_traceback.tb_lineno, e))
		U.logger.log(30, u"input:{}, len:{};  ".format(inp, len(inp)))
	return values

# ===========================================================================
# read params
# ===========================================================================


def readParams():
	global sensorList, sensors, sensor, SENSOR
	global sensorRefreshSecs, sendToIndigoEvery, minSendDelta
	global rawOld
	global deltaX, input, gain, resModel, i2cAddress
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
			
		try: sensorRefreshSecs	= float(G.sensorRefreshSecs)
		except: pass
		try: minSendDelta		= float(G.minSendDelta)
		except: pass
		try: sendToIndigoEvery	= float(G.sendToIndigoEvery)
		except: pass
				
		for devId in sensors[sensor]:

			i2cADDR = U.getI2cAddress(sensors[sensor][devId], default ="")
			if i2cADDR not in i2cAddress: i2cAddress[i2cADDR] =[]
			i2cAddress[i2cADDR].append(devId)

			try:	sendToIndigoEvery = float(sensors[sensor][devId]["sendToIndigoEvery"])
			except: pass
			try:	minSendDelta = float(sensors[sensor][devId]["minSendDelta"])
			except: pass
			try:	sensorRefreshSecs = float(sensors[sensor][devId]["sensorRefreshSecs"])
			except: pass


			try:	deltaX[devId] = float(sensors[sensor][devId]["deltaX"])/100.
			except:	deltaX[devId] = 0.1

			try:	input[devId] = sensors[sensor][devId]["input"]
			except:	input[devId] = "0"

			try:	gain[devId] = int(sensors[sensor][devId]["gain"])
			except:	gain[devId] = 6144

			try: 	resModel[devId] = 0x01 if int(sensors[sensor][devId]["resModel"]) == 16 else 0x00
			except: resModel[devId] = 0x01


			U.logger.log(30,"==== Start {} ===== @ i2c:{}; inputC:{};  deltaX:{}, gain:{}, resModel:{}".format(G.program, i2cADDR, input[devId], deltaX[devId], gain[devId], resModel[devId] ) )
			startSensor(devId, i2cADDR)
		U.logger.log(30,    "==== Start {}... sendToIndigoEvery:{};minSendDelta:{};  sensorRefreshSecs:{},all i2c->devids:{}".format(G.program, sendToIndigoEvery, minSendDelta, sensorRefreshSecs, i2cAddress))
				
		deldevID={}		   
		for devId in SENSOR:
			if devId not in sensors[sensor]:
				deldevID[devId]=1

		for dd in  deldevID:
			del SENSOR[dd]

		if len(SENSOR) == 0: 
			####exit()
			pass

	except	Exception, e:
		U.logger.log(30, u"in Line {} has error={}".format(sys.exc_traceback.tb_lineno, e))

#################################
#################################
#################################
#################################
#################################
#################################
#################################
def execADS1x15():			 
	global sensorList, sensors, sensor, SENSOR, gain, input, resModel
	global sensorRefreshSecs, sendToIndigoEvery, minSendDelta
	global sValues, displayInfo
	global oldRaw, lastRead
	global input, deltaX, i2cAddress
	global badSensor

	badSensor			= 0
	i2cAddress			= {}
	resModel			= {}
	gain				= {}
	input				= {}
	sensorRefreshSecs	= 5
	minSendDelta		= 4
	sendToIndigoEvery	= 90
	oldRaw				= ""
	lastRead			= 0
	loopCount			= 0
	deltaX				= {}
	sensorList			= []
	sensors				= {}
	SENSOR 				= {}
	quick				= False
	myPID				= str(os.getpid())

	sensor = G.program

	U.setLogging()

	U.killOldPgm(myPID,G.program+".py")# kill old instances of myself if they are still running

	readParams()



	myPID		= str(os.getpid())
	U.killOldPgm(myPID,G.program+".py")# kill old instances of myself if they are still running

	NSleep= int(sensorRefreshSecs)
	if G.networkType  in G.useNetwork and U.getNetwork() == "off": 
		if U.getIPNumber() > 0:
			U.logger.log(30,"no ip number working, giving up")
			time.sleep(10)

	eth0IP, wifi0IP, G.eth0Enabled,G.wifiEnabled = U.getIPCONFIG()


	tt					= time.time()
	badSensors			= {}
	lastData			= {}
	lastMsg				= 0
	G.tStart			= tt
	lastMeasurement		= tt
	lastRead			= tt

	while True:
		try:
			sendToIndigo = False
			tt	 = time.time()
			lastMeasurement		= tt
			data = {"sensors": {}}
			if sensor in sensors:
				values = getValues()
				data["sensors"] = {sensor:{}}
				for devId in sensors[sensor]:
					data["sensors"][sensor][devId] ={}
					if devId not in lastData: lastData[devId] = -500.
					if devId not in values: value = ""
					else:					value = values[devId]
					if value == "":
						sensorWasBad = True
						data["sensors"][sensor][devId]["INPUT"] = "badSensor"
						if badSensor > 5: 
							U.logger.log(30," bad sensor")
							U.sendURL(data)
						lastData[devId] =-100.
						continue
					else:
						data["sensors"][sensor][devId] = value
						current = value["INPUT"]
						delta	= current-lastData[devId]
						deltaN	= abs(delta) / max (0.5,(current+lastData[devId])/2.)
				
					if ( ( deltaN > deltaX[devId]							) or 
						 (	tt - abs(sendToIndigoEvery) > G.lastAliveSend	) or  
						 ( quick											)   ) and  \
					   ( ( tt - G.lastAliveSend > minSendDelta				)   ):
							sendToIndigo = True
							lastData[devId]	= current
			#U.logger.log(20, u"data{}".format(data))
			
			if sendToIndigo:
				U.sendURL(data)
			loopCount += 1

			U.makeDATfile(G.program, data)
			quick = U.checkNowFile(G.program)				 
			U.echoLastAlive(G.program)

			if not quick:
				tt= time.time()
				if tt - lastRead > 5.:	
					readParams()
					lastRead = tt
			if not quick:
				time.sleep(max (0,time.time() - lastMeasurement + sensorRefreshSecs) )
		except Exception, e:
			U.logger.log(50, u"in Line {} has error={}".format(sys.exc_traceback.tb_lineno, e))
			time.sleep(5.)
execADS1x15()
try: 	G.sendThread["run"] = False; time.sleep(1)
except: pass
sys.exit(0)
