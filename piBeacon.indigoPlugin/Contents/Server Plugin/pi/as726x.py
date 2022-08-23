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
G.program = "as726x"




# ===========================================================================
# as726x Class
# ===========================================================================

# The MIT License (MIT)
#
# Copyright (c) 2017 Dean Miller for Adafruit Industries
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
"""
`adafruit_as726x`
====================================================

Driver for the AS726x spectral sensors

* Author(s): Dean Miller

replaced micopython read/write with

	def _read_u8(self, command):
		return = self.bus.read_byte_data(self.address, reg)

	def __write_u8(self, reg, value):
		self.bus.write_byte_data(self.address, reg, value)
Karl Wachs


"""

import time

try:
	import struct
except ImportError:
	import ustruct as struct


_AS726X_ADDRESS			= 0x49

_AS726X_HW_VERSION		= 0x00
_AS726X_FW_VERSION		= 0x02
_AS726X_CONTROL_SETUP	= 0x04
_AS726X_INT_T			= 0x05
_AS726X_DEVICE_TEMP		= 0x06
_AS726X_LED_CONTROL		= 0x07

#for reading sensor data
_AS7262_V_HIGH			= 0x08
_AS7262_V_LOW			= 0x09
_AS7262_B_HIGH			= 0x0A
_AS7262_B_LOW			= 0x0B
_AS7262_G_HIGH			= 0x0C
_AS7262_G_LOW			= 0x0D
_AS7262_Y_HIGH			= 0x0E
_AS7262_Y_LOW			= 0x0F
_AS7262_O_HIGH			= 0x10
_AS7262_O_LOW			= 0x11
_AS7262_R_HIGH			= 0x12
_AS7262_R_LOW			= 0x13

_AS7262_V_CAL			= 0x14
_AS7262_B_CAL			= 0x18
_AS7262_G_CAL			= 0x1C
_AS7262_Y_CAL			= 0x20
_AS7262_O_CAL			= 0x24
_AS7262_R_CAL			= 0x28

#hardware registers
_AS726X_SLAVE_STATUS_REG = 0x00
_AS726X_SLAVE_WRITE_REG	 = 0x01
_AS726X_SLAVE_READ_REG	 = 0x02
_AS726X_SLAVE_TX_VALID	 = 0x02
_AS726X_SLAVE_RX_VALID	 = 0x01

_AS7262_VIOLET			 = 0x08
_AS7262_BLUE			 = 0x0A
_AS7262_GREEN			 = 0x0C
_AS7262_YELLOW			 = 0x0E
_AS7262_ORANGE			 = 0x10
_AS7262_RED				 = 0x12

_AS7262_VIOLET_CALIBRATED = 0x14
_AS7262_BLUE_CALIBRATED	  = 0x18
_AS7262_GREEN_CALIBRATED  = 0x1C
_AS7262_YELLOW_CALIBRATED = 0x20
_AS7262_ORANGE_CALIBRATED = 0x24
_AS7262_RED_CALIBRATED	  = 0x28

_AS726X_NUM_CHANNELS	= 6

_counts_Per_mu_Watt		= 45. # with gain = 16, int time = 166 mSec

class Adafruit_AS726x(object):
	"""AS726x spectral sensor.
	  """

	MODE_0 = 0b00
	"""Continuously gather samples of violet, blue, green and yellow. Orange and red are skipped and read zero."""

	MODE_1 = 0b01
	"""Continuously gather samples of green, yellow, orange and red. Violet and blue are skipped and read zero."""

	MODE_2 = 0b10 #default
	"""Continuously gather samples of all colors"""

	ONE_SHOT = 0b11
	"""Gather a single sample of all colors and then stop"""

	GAIN = (1, 3.7, 16, 64)

	INDICATOR_CURRENT_LIMITS = (1, 2, 4, 8)

	DRIVER_CURRENT_LIMITS = (12.5, 25, 50, 100)

	def __init__(self,i2cAddress=_AS726X_ADDRESS):
		try:
			self._driver_led			= False
			self._indicator_led			= False
			self._driver_led_current	= Adafruit_AS726x.DRIVER_CURRENT_LIMITS.index(12.5)
			self._indicator_led_current = Adafruit_AS726x.INDICATOR_CURRENT_LIMITS.index(1)
			self._conversion_mode		= Adafruit_AS726x.MODE_2
			self._integration_time		= 0
			self._gain					= Adafruit_AS726x.GAIN.index(1)

			self.address				=_AS726X_ADDRESS
			self.bus					= smbus.SMBus(1)

			#reset device
			self._virtual_write(_AS726X_CONTROL_SETUP, 0x80)

			#wait for it to boot up
			time.sleep(1)

			#try to read the version reg to make sure we can connect
			version = self._virtual_read(_AS726X_HW_VERSION)

			#TODO: add support for other devices
			if version != 0x40:
				raise ValueError("device could not be reached or this device is not supported!")

			self._integration_time = 140
			self._conversion_mode  = Adafruit_AS726x.MODE_2
			self._gain			  = 16
			self._norm = 16.*140. / (self._gain*self._integration_time*_counts_Per_mu_Watt)


		except	Exception as e:
			print (u"init in Line {} has error={}".format (traceback.extract_tb(sys.exc_info()[2])[-1][1], e))
			U.logger.log(30, u"init in Line {} has error={}".format (traceback.extract_tb(sys.exc_info()[2])[-1][1], e))
		return


	def enable_driver_led(self, val):
		val = bool(val)
		if self._driver_led == val:
			return
		self._driver_led = val
		enable = self._virtual_read(_AS726X_LED_CONTROL)
		enable &= ~(0x1 << 3)
		self._virtual_write(_AS726X_LED_CONTROL, enable | (val << 3))
		return

	def set_driver_led_current(self, val):
		if val not in Adafruit_AS726x.DRIVER_CURRENT_LIMITS:
			raise ValueError("Must be 12.5, 25, 50 or 100")
		if self._driver_led_current == val:
			return
		self._driver_led_current = val
		state = self._virtual_read(_AS726X_LED_CONTROL)
		state &= ~(0x3 << 4)
		state = state | (Adafruit_AS726x.DRIVER_CURRENT_LIMITS.index(val) << 4)
		self._virtual_write(_AS726X_LED_CONTROL, state)
		return

	def indicator_led(self, val):
		val = bool(val)
		if self._indicator_led == val:
			return
		self._indicator_led = val
		enable = self._virtual_read(_AS726X_LED_CONTROL)
		enable &= ~(0x1)
		self._virtual_write(_AS726X_LED_CONTROL, enable | val)
		return

	def indicator_led_current(self, val):
		if val not in Adafruit_AS726x.INDICATOR_CURRENT_LIMITS:
			raise ValueError("Must be 1, 2, 4 or 8")
		if self._indicator_led_current == val:
			return
		self._indicator_led_current = val
		state = self._virtual_read(_AS726X_LED_CONTROL)
		state &= ~(0x3 << 1)
		state = state | (Adafruit_AS726x.INDICATOR_CURRENT_LIMITS.index(val) << 4)
		self._virtual_write(_AS726X_LED_CONTROL, state)
		return

	def set_Conversion_mode(self, val):
		"""The conversion mode. One of:
		   - `MODE_0`
		   - `MODE_1`
		   - `MODE_2`
		   - `ONE_SHOT`"""
		val = int(val)
		assert self.MODE_0 <= val <= self.ONE_SHOT
		if self._conversion_mode == val:
			return
		self._conversion_mode = val
		print "as726x...setting new conversion_mode", val
		state = self._virtual_read(_AS726X_CONTROL_SETUP)
		state &= ~(val << 2)
		self._virtual_write(_AS726X_CONTROL_SETUP, state | (val << 2))
		return

	def set_Gain(self, val):
		try:
			if val not in Adafruit_AS726x.GAIN:
				raise ValueError("Must be 1, 3.7, 16 or 64")
			self._norm = 16.*140. / (val*self._integration_time*_counts_Per_mu_Watt)
			if self._gain == val:
				return
			self._gain = val
			print "as726x...setting new gain:", val, "	 intTime:", self._integration_time,"  norm:", self._norm
			state = self._virtual_read(_AS726X_CONTROL_SETUP)
			state &= ~(0x3 << 4)
			state |= (Adafruit_AS726x.GAIN.index(val) << 4)
			self._virtual_write(_AS726X_CONTROL_SETUP, state)
			return
		except	Exception as e:
			print (u"in Line {} has error={}".format (traceback.extract_tb(sys.exc_info()[2])[-1][1], e))
			U.logger.log(30, u"in Line {} has error={}".format (traceback.extract_tb(sys.exc_info()[2])[-1][1], e))

	def set_Integration_time(self, val):
		if not 2.8 <= val <= 714:
			raise ValueError("Out of supported range 2.8 - 714 ms")
		val = int(val/2.8)
		xval= val*2.8
		self._norm = 16.*140. / (self._gain*xval*_counts_Per_mu_Watt)
		if self._integration_time == xval:
			return
		print "as726x... setting new integrationTime", xval, "	 gain:", self._gain ,"	norm:", self._norm
		self._integration_time = xval
		self._virtual_write(_AS726X_INT_T, val)
		return

	def start_measurement(self):
		"""Begin a measurement.
		   This will set the device to One Shot mode and values will not change after `data_ready`
		   until `start_measurement` is called again or the `conversion_mode` is changed."""
		state = self._virtual_read(_AS726X_CONTROL_SETUP)
		state &= ~(0x02)
		self._virtual_write(_AS726X_CONTROL_SETUP, state)
		self._conversion_mode = self.ONE_SHOT
		return

	def read_channel(self, channel):
		"""Read an individual sensor channel"""
		return (self._virtual_read(channel) << 8) | self._virtual_read(channel + 1)

	def read_calibrated_value(self, channel):
		"""Read a calibrated sensor channel"""
		val = bytearray(4)
		val[0] = self._virtual_read(channel)
		val[1] = self._virtual_read(channel + 1)
		val[2] = self._virtual_read(channel + 2)
		val[3] = self._virtual_read(channel + 3)
		return struct.unpack('!f', val)[0]

	
	def data_ready(self):
		"""True if the sensor has data ready to be read, False otherwise"""
		return (self._virtual_read(_AS726X_CONTROL_SETUP) >> 1) & 0x01

#### read calibrated values		
	def temperature(self):
		"""The temperature of the device in Celsius"""
		return self._virtual_read(_AS726X_DEVICE_TEMP)
	
	def violet(self):
		"""Calibrated violet (450nm) value"""
		return self.read_calibrated_value(_AS7262_VIOLET_CALIBRATED)*self._norm 
	
	def blue(self):
		"""Calibrated blue (500nm) value"""
		return self.read_calibrated_value(_AS7262_BLUE_CALIBRATED)*self._norm 
	
	def green(self):
		"""Calibrated green (550nm) value"""
		return self.read_calibrated_value(_AS7262_GREEN_CALIBRATED)*self._norm 
	
	def yellow(self):
		"""Calibrated yellow (570nm) value"""
		return self.read_calibrated_value(_AS7262_YELLOW_CALIBRATED)*self._norm 
	
	def orange(self):
		"""Calibrated orange (600nm) value"""
		return self.read_calibrated_value(_AS7262_ORANGE_CALIBRATED)*self._norm 
	
	def red(self):
		"""Calibrated red (650nm) value"""
		return self.read_calibrated_value(_AS7262_RED_CALIBRATED)*self._norm 



#### raw reads ...	not used	
	def raw_violet(self):
		"""Raw violet (450nm) 16-bit value"""
		return self.read_channel(_AS7262_VIOLET)
	
	def raw_blue(self):
		"""Raw blue (500nm) 16-bit value"""
		return self.read_channel(_AS7262_BLUE)
	
	def raw_green(self):
		"""Raw green (550nm) 16-bit value"""
		return self.read_channel(_AS7262_GREEN)
	
	def raw_yellow(self):
		"""Raw yellow (570nm) 16-bit value"""
		return self.read_channel(_AS7262_YELLOW)
	
	def raw_orange(self):
		"""Raw orange (600nm) 16-bit value"""
		return self.read_channel(_AS7262_ORANGE)
	
	def raw_red(self):
		"""Raw red (650nm) 16-bit value"""
		return self.read_channel(_AS7262_RED)



########## i/o methods 
	def _read_u8(self, reg):
		"""read a single byte from a specified register"""
		return	self.bus.read_byte_data(self.address, reg)

	def __write_u8(self, reg, value):
		"""Write a command and 1 byte of data to the I2C device"""
		self.bus.write_byte_data(self.address, reg, value)


	def _virtual_read(self, addr):
		"""read a virtual register"""
		while True:
			# Read slave I2C status to see if the read buffer is ready.
			status = self._read_u8(_AS726X_SLAVE_STATUS_REG)
			if (status & _AS726X_SLAVE_TX_VALID) == 0:
				# No inbound TX pending at slave. Okay to write now.
				break
		# Send the virtual register address (setting bit 7 to indicate a pending write).
		self.__write_u8(_AS726X_SLAVE_WRITE_REG, addr)
		while True:
			# Read the slave I2C status to see if our read data is available.
			status = self._read_u8(_AS726X_SLAVE_STATUS_REG)
			if (status & _AS726X_SLAVE_RX_VALID) != 0:
				# Read data is ready.
				break
		# Read the data to complete the operation.
		data = self._read_u8(_AS726X_SLAVE_READ_REG)
		return data

	def _virtual_write(self, addr, value):
		"""write a virtual register"""
		while True:
			# Read slave I2C status to see if the write buffer is ready.
			status = self._read_u8(_AS726X_SLAVE_STATUS_REG)
			if (status & _AS726X_SLAVE_TX_VALID) == 0:
				break # No inbound TX pending at slave. Okay to write now.
		# Send the virtual register address (setting bit 7 to indicate a pending write).
		self.__write_u8(_AS726X_SLAVE_WRITE_REG, (addr | 0x80))
		while True:
			# Read the slave I2C status to see if the write buffer is ready.
			status = self._read_u8(_AS726X_SLAVE_STATUS_REG)
			if (status & _AS726X_SLAVE_TX_VALID) == 0:
				break # No inbound TX pending at slave. Okay to write data now.

		# Send the data to complete the operation.
		self.__write_u8(_AS726X_SLAVE_WRITE_REG, value)


 # ===========================================================================
# read params
# ===========================================================================

#################################		 
def readParams():
	global sensorList, sensors, logDir, sensor,	 sensorRefreshSecs
	global rawOld
	global deltaX, as726xsensor, minSendDelta
	global oldRaw, lastRead
	global LEDmA, doAverage, LEDBlink, gain, integrationTime
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
				if "gain" in sensors[sensor][devId]: 
					gain= float(sensors[sensor][devId]["gain"])
			except:
				gain = 16

			try:
				if "integrationTime" in sensors[sensor][devId]: 
					integrationTime= float(sensors[sensor][devId]["integrationTime"])
			except:
				integrationTime = 140

			try:
				if "doAverage" in sensors[sensor][devId]: 
					doAverage= int(sensors[sensor][devId]["doAverage"])
			except:
				doAverage = 1

			try:
				if "LEDmA" in sensors[sensor][devId]: 
					LEDmA= float(sensors[sensor][devId]["LEDmA"])
			except:
				LEDmA = 5.

			try:
				if "LEDBlink" in sensors[sensor][devId]: 
					LEDBlink= int(sensors[sensor][devId]["LEDBlink"])
			except:
				LEDBlink = 0



			if devId not in as726xsensor:
				U.logger.log(30,"==== Start "+G.program+" ====== @ i2c= " +unicode(i2cAddress) )
				i2cAdd = U.muxTCA9548A(sensors[sensor][devId])
				as726xsensor[devId] = Adafruit_AS726x(i2cAddress=i2cAdd)
				as726xsensor[devId].set_Conversion_mode(as726xsensor[devId].MODE_2)
				U.muxTCA9548Areset()
			i2cAdd = U.muxTCA9548A(sensors[sensor][devId])
			as726xsensor[devId].set_Integration_time(integrationTime)
			as726xsensor[devId].set_Gain(gain)
			U.muxTCA9548Areset()
			
		deldevID={}		   
		for devId in as726xsensor:
			if devId not in sensors[sensor]:
				deldevID[devId]=1
		for dd in  deldevID:
			del as726xsensor[dd]
		if len(as726xsensor) ==0: 
			####exit()
			pass

	except	Exception as e:
		U.logger.log(30, u"readParams in Line {} has error={}".format (traceback.extract_tb(sys.exc_info()[2])[-1][1], e))

def setLED(devId,value):
	global sensor, sensors,	 as726xsensor
	try:
		i2cAdd = U.muxTCA9548A(sensors[sensor][devId])
		if value == 0:
			as726xsensor[devId].enable_driver_led(False)
		else:
			as726xsensor[devId].set_driver_led_current(value)
			as726xsensor[devId].enable_driver_led(True)
		U.muxTCA9548Areset()
	except	Exception as e:
		U.logger.log(30, u"setLED in Line {} has error={}".format (traceback.extract_tb(sys.exc_info()[2])[-1][1], e))
	return 


#################################
def getValues(devId):
	global sensor, sensors,	 as726xsensor, badSensor
	global LEDmA, doAverage, LEDBlink, gain

	i2cAdd = U.muxTCA9548A(sensors[sensor][devId])
	data ={"blue":"","green":"","yellow":"","orange":"","red":"","violet":"","temp":"","LEDcurrent":0}
	try:
		for ii in range(20):
			if as726xsensor[devId].data_ready(): break
			time.sleep(.1)
		##print "blue" , as726xsensor[devId].blue()
		data["blue"]		= as726xsensor[devId].blue()
		data["green"]		= as726xsensor[devId].green()
		data["yellow"]		= as726xsensor[devId].yellow()
		data["orange"]		= as726xsensor[devId].orange()
		data["red"]			= as726xsensor[devId].red()
		data["violet"]		= as726xsensor[devId].violet()
		data["temp"]		= as726xsensor[devId].temperature()
		badSensor = 0
		U.muxTCA9548Areset()
		return data

	except	Exception as e:
		if badSensor >-1 and badSensor < 5000: 
			U.logger.log(30, u"getValues in Line {} has error={}".format (traceback.extract_tb(sys.exc_info()[2])[-1][1], e))
			U.logger.log(30, unicode(data) )
						
		badSensor+=1
	if badSensor >3: 
		U.muxTCA9548Areset()
		return "badSensor"
	U.muxTCA9548Areset()
	return "badSensor"		  






############################################
global rawOld
global sensor, sensors, badSensor
global deltaX, as726xsensor, minSendDelta
global oldRaw, lastRead
global LEDmA, doAverage, LEDBlink, gain, integrationTime
global formatStr

oldRaw						=""
lastRead					= 0



LEDmA						= 0
LEDmALast					= 0
doAverage					= 0 
LEDBlink					= 0
LEDBlinkLast				= 0
gain						= 16
integrationTime				= 140
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
loopSleep					= 0.9
rawOld						= ""
as726xsensor				= {}
deltaX						= {}
myPID						= str(os.getpid())
U.setLogging()
U.killOldPgm(myPID,G.program+".py")# kill old instances of myself if they are still running
formatStr = {"blue":"9.4f","green":"9.4f","yellow":"9.4f","orange":"9.4f","red":"9.4f","violet":"9.4f","temp":"9.1f","LEDcurrent":"9.1f"}

if U.getIPNumber() > 0:
	time.sleep(10)
	exit()

readParams()

time.sleep(1)

lastRead = time.time()

U.echoLastAlive(G.program)




lastValue			= {}
averages			= {}
lastData			= {}
lastSend			= 0
lastRead			= time.time()
G.lastAliveSend		= time.time() -1000
rebootCount			= 0

sensorWasBad = False
while True:
	try:
		tt = time.time()
		data = {"sensors":{}}
		sendURLnow = False
		if sensor in sensors:
			data["sensors"][sensor] ={}
			for devId in sensors[sensor]:
				data["sensors"][sensor][devId] ={}
				if devId not in lastValue: lastValue[devId]	 ={"blue":-100,"green":-100,"yellow":-100,"orange":-100,"red":-100,"violet":-100,"temp":-1,"LEDcurrent":0}
				if devId not in averages:	averages[devId]	 ={"blue":0,"green":0,"yellow":0,"orange":0,"red":0,"violet":0,"temp":0,"LEDcurrent":0,"n":0}

				if LEDBlink > 0:
					if time.time() - LEDBlinkLast > LEDBlink:
						for color in averages[devId]:
							averages[devId][color] =0
						if LEDmALast == 0: 
							setLED(devId,LEDmA) 
							LEDmALast = LEDmA
						else:
							setLED(devId,0)
							LEDmALast = 0
						LEDBlinkLast = time.time()
						time.sleep(0.5)
							
				values = getValues(devId)
				##print "values",values
				if values == "": 
					continue
				if values =="badSensor":
					sensorWasBad = True
					data["sensors"][sensor][devId]["violet"] = "badSensor"
					lastValue[devId]["violet"] =-100.
					sendURLnow = True
					rebootCount +=1
					continue

				else:
					deltaN = 0
					ok = True
					for color in values:
						if values[color] =="": 
							ok = False
							data["sensors"][sensor][devId]["violet"] = "badSensor"
							sendURLnow = True
							break
					if not ok: 
						rebootCount +=1
						continue

					if sensorWasBad: # sensor was bad, back up again, need to do a restart to set config 
						U.restartMyself(reason=" back from bad sensor, need to restart to get sensors reset",doPrint=False)

					values["LEDcurrent"]  =LEDmALast

					avsend = False
					if doAverage > 0:
						averages[devId]["n"] += 1
						for color in values:
							averages[devId][color] += values[color]
							values[color] = averages[devId][color]/averages[devId]["n"]
							if averages[devId]["n"] >= doAverage: 
								averages[devId][color] = 0
						if averages[devId]["n"] >= doAverage: 
							averages[devId]["n"] = 0
							avsend = True

					bad = False
					for color in values:
						try:  data["sensors"][sensor][devId][color]=  (	 ("%"+formatStr[color] )%( values[color])  ).strip()
						except:
							data["sensors"][sensor][devId][color] = "badSensor"
							rebootCount +=1
							bad= True
					if bad: continue
					rebootCount = 0

					for color in values:
						value  = values[color]
						#print value, lastValue[devId][color]
						delta	= value-lastValue[devId][color]
						delta  /=  max (0.5,(value+lastValue[devId][color])/2.)
						deltaN	= max(deltaN, abs(delta) )

				if ( ( deltaN > deltaX[devId]							) or 
					 (	tt - G.lastAliveSend  > abs(G.sendToIndigoSecs) ) or  
					 ( quick											)	
					)  and	(		   \
					 ( doAverage == 0  and	 tt - minSendDelta	> G.lastAliveSend  )  or avsend		)	: 
						sendURLnow = True
						lastValue[devId]  = values
						#print " sending",avsend, deltaN ,deltaX[devId],  tt - G.lastAliveSend ,tt - minSendDelta  , G.sendToIndigoSecs
			if sendURLnow:
					##print data
					U.sendURL(data)

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
		if rebootCount >20:
			U.restartMyself(reason="badsensor")
		
	except	Exception as e:
		U.logger.log(30, u"in Line {} has error={}".format (traceback.extract_tb(sys.exc_info()[2])[-1][1], e))
		time.sleep(5.)
try: 	G.sendThread["run"] = False; time.sleep(1)
except: pass
sys.exit(0)
