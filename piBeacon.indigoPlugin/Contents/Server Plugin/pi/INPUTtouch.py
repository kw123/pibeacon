#!/usr/bin/env python
# -*- coding: utf-8 -*-
# by Karl Wachs
#


import RPi.GPIO as GPIO
import time
import	sys, os, time, json, datetime,subprocess,copy
import struct

sys.path.append(os.getcwd())
import	piBeaconUtils	as U
import	piBeaconGlobals as G
G.program = "INPUTtouch"
import smbus 


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

# Copyright (c) 2014 Adafruit Industries
# Author: Tony DiCola
# Based on Adafruit_I2C.py created by Kevin Townsend.
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

# Register addresses.
MPR121_I2CADDR_DEFAULT = 0x5A
MPR121_TOUCHSTATUS_L   = 0x00
MPR121_TOUCHSTATUS_H   = 0x01
MPR121_FILTDATA_0L	   = 0x04
MPR121_FILTDATA_0H	   = 0x05
MPR121_BASELINE_0	   = 0x1E
MPR121_MHDR			   = 0x2B
MPR121_NHDR			   = 0x2C
MPR121_NCLR			   = 0x2D
MPR121_FDLR			   = 0x2E
MPR121_MHDF			   = 0x2F
MPR121_NHDF			   = 0x30
MPR121_NCLF			   = 0x31
MPR121_FDLF			   = 0x32
MPR121_NHDT			   = 0x33
MPR121_NCLT			   = 0x34
MPR121_FDLT			   = 0x35
MPR121_TOUCHTH_0	   = 0x41
MPR121_RELEASETH_0	   = 0x42
MPR121_DEBOUNCE		   = 0x5B
MPR121_CONFIG1		   = 0x5C
MPR121_CONFIG2		   = 0x5D
MPR121_CHARGECURR_0	   = 0x5F
MPR121_CHARGETIME_1	   = 0x6C
MPR121_ECR			   = 0x5E
MPR121_AUTOCONFIG0	   = 0x7B
MPR121_AUTOCONFIG1	   = 0x7C
MPR121_UPLIMIT		   = 0x7D
MPR121_LOWLIMIT		   = 0x7E
MPR121_TARGETLIMIT	   = 0x7F
MPR121_GPIODIR		   = 0x76
MPR121_GPIOEN		   = 0x77
MPR121_GPIOSET		   = 0x78
MPR121_GPIOCLR		   = 0x79
MPR121_GPIOTOGGLE	   = 0x7A
MPR121_SOFTRESET	   = 0x80

MAX_I2C_RETRIES		   = 5

def reverseByteOrder(data):
	"""Reverses the byte order of an int (16-bit) or long (32-bit) value."""
	# Courtesy Vishal Sapre
	byteCount = len(hex(data)[2:].replace('L','')[::2])
	val		  = 0
	for i in range(byteCount):
		val	   = (val << 8) | (data & 0xff)
		data >>= 8
	return val

class MPR121():

	
	"""Class for communicating with an I2C device using the adafruit-pureio pure
	python smbus library, or other smbus compatible I2C interface. Allows reading
	and writing 8-bit, 16-bit, and byte array values to registers
	on the device."""
	def __init__(self, address=0x5a,busNum=1):
		"""Create an instance of the I2C device at the specified address on the
		specified I2C bus number."""
		self._address = address
		self._bus = smbus.SMBus(busNum)

	def writeRaw8(self, value):
		"""Write an 8-bit value on the bus (without register)."""
		value = value & 0xFF
		self._bus.write_byte(self._address, value)

	def write8(self, register, value):
		"""Write an 8-bit value to the specified register."""
		value = value & 0xFF
		self._bus.write_byte_data(self._address, register, value)

	def write16(self, register, value):
		"""Write a 16-bit value to the specified register."""
		value = value & 0xFFFF
		self._bus.write_word_data(self._address, register, value)

	def writeList(self, register, data):
		"""Write bytes to the specified register."""
		self._bus.write_i2c_block_data(self._address, register, data)

	def readList(self, register, length):
		"""Read a length number of bytes from the specified register.  Results
		will be returned as a bytearray."""
		results = self._bus.read_i2c_block_data(self._address, register, length)
		return results

	def readRaw8(self):
		"""Read an 8-bit value on the bus (without register)."""
		result = self._bus.read_byte(self._address) & 0xFF
		return result

	def readU8(self, register):
		"""Read an unsigned byte from the specified register."""
		result = self._bus.read_byte_data(self._address, register) & 0xFF
		return result

	def readS8(self, register):
		"""Read a signed byte from the specified register."""
		result = self.readU8(register)
		if result > 127:
			result -= 256
		return result

	def readU16(self, register, little_endian=True):
		"""Read an unsigned 16-bit value from the specified register, with the
		specified endianness (default little endian, or least significant byte
		first)."""
		result = self._bus.read_word_data(self._address,register) & 0xFFFF
		# Swap bytes if using big endian because read_word_data assumes little
		# endian on ARM (little endian) systems.
		if not little_endian:
			result = ((result << 8) & 0xFF00) + (result >> 8)
		return result

	def readS16(self, register, little_endian=True):
		"""Read a signed 16-bit value from the specified register, with the
		specified endianness (default little endian, or least significant byte
		first)."""
		result = self.readU16(register, little_endian)
		if result > 32767:
			result -= 65536
		return result

	def readU16LE(self, register):
		"""Read an unsigned 16-bit value from the specified register, in little
		endian byte order."""
		return self.readU16(register, little_endian=True)

	def readU16BE(self, register):
		"""Read an unsigned 16-bit value from the specified register, in big
		endian byte order."""
		return self.readU16(register, little_endian=False)

	def readS16LE(self, register):
		"""Read a signed 16-bit value from the specified register, in little
		endian byte order."""
		return self.readS16(register, little_endian=True)

	def readS16BE(self, register):
		"""Read a signed 16-bit value from the specified register, in big
		endian byte order."""
		return self.readS16(register, little_endian=False)




	def begin(self, i2c=None, **kwargs):
		"""Initialize communication with the MPR121. 

		Can specify a custom I2C address for the device using the address 
		parameter (defaults to 0x5A). Optional i2c parameter allows specifying a 
		custom I2C bus source (defaults to platform's I2C bus).

		Returns True if communication with the MPR121 was established, otherwise
		returns False.
		"""		   
		U.setStopCondition(on=True)
		# Save a reference to the I2C device instance for later communication.
		return self._reset()

	def _reset(self):
		global TOU_THRESH, REL_THRESH
		# Soft reset of device.
		self._i2c_retry(self.write8, MPR121_SOFTRESET, 0x63)
		time.sleep(0.001) # This 1ms delay here probably isn't necessary but can't hurt.
		# Set electrode configuration to default values.
		self._i2c_retry(self.write8, MPR121_ECR, 0x00)
		# Check CDT, SFI, ESI configuration is at default values.
		c = self._i2c_retry(self.readU8, MPR121_CONFIG2)
		if c != 0x24:
		   return False
		# Set threshold for touch and release to default values.
		self.set_thresholds(TOU_THRESH, REL_THRESH)
		# Configure baseline filtering control registers.
		self._i2c_retry(self.write8, MPR121_MHDR, 0x01)
		self._i2c_retry(self.write8, MPR121_NHDR, 0x01)
		self._i2c_retry(self.write8, MPR121_NCLR, 0x0E)
		self._i2c_retry(self.write8, MPR121_FDLR, 0x00)
		self._i2c_retry(self.write8, MPR121_MHDF, 0x01)
		self._i2c_retry(self.write8, MPR121_NHDF, 0x05)
		self._i2c_retry(self.write8, MPR121_NCLF, 0x01)
		self._i2c_retry(self.write8, MPR121_FDLF, 0x00)
		self._i2c_retry(self.write8, MPR121_NHDT, 0x00)
		self._i2c_retry(self.write8, MPR121_NCLT, 0x00)
		self._i2c_retry(self.write8, MPR121_FDLT, 0x00)
		# Set other configuration registers.
		self._i2c_retry(self.write8, MPR121_DEBOUNCE, 0)
		self._i2c_retry(self.write8, MPR121_CONFIG1, 0x10) # default, 16uA charge current
		self._i2c_retry(self.write8, MPR121_CONFIG2, 0x20) # 0.5uS encoding, 1ms period
		# Enable all electrodes.
		self._i2c_retry(self.write8, MPR121_ECR, 0x8F) # start with first 5 bits of baseline tracking
		# All done, everything succeeded!
		return True

	def _i2c_retry(self, func, *params):
		# Run specified I2C request and ignore IOError 110 (timeout) up to
		# retries times.  For some reason the Pi 2 hardware I2C appears to be
		# flakey and randomly return timeout errors on I2C reads.  This will
		# catch those errors, reset the MPR121, and retry.
		count = 0
		while True:
			try:
				return func(*params)
			except IOError as ex:
				# Re-throw anything that isn't a timeout (110) error.
				if ex.errno != 110:
					raise ex
			# Else there was a timeout, so reset the device and retry.
			self._reset()
			# Increase count and fail after maximum number of retries.
			count += 1
			if count >= MAX_I2C_RETRIES:
				raise RuntimeError('Exceeded maximum number or retries attempting I2C communication!')

	def set_thresholds(self, touch, release):
		"""Set the touch and release threshold for all inputs to the provided
		values.	 Both touch and release should be a value between 0 to 255
		(inclusive).
		"""
		assert touch >= 0 and touch <= 255, 'touch must be between 0-255 (inclusive)'
		assert release >= 0 and release <= 255, 'release must be between 0-255 (inclusive)'
		# Set the touch and release register value for all the inputs.
		for i in range(12):
			self._i2c_retry(self.write8, MPR121_TOUCHTH_0 + 2*i, touch)
			self._i2c_retry(self.write8, MPR121_RELEASETH_0 + 2*i, release)

	def filtered_data(self, pin):
		"""Return filtered data register value for the provided pin (0-11).
		Useful for debugging.
		"""
		assert pin >= 0 and pin < 12, 'pin must be between 0-11 (inclusive)'
		return self._i2c_retry(self.readU16LE, MPR121_FILTDATA_0L + pin*2)

	def baseline_data(self, pin):
		"""Return baseline data register value for the provided pin (0-11).
		Useful for debugging.
		"""
		assert pin >= 0 and pin < 12, 'pin must be between 0-11 (inclusive)'
		bl = self._i2c_retry(self.readU8, MPR121_BASELINE_0 + pin)
		return bl << 2

	def touched(self):
		"""Return touch state of all pins as a 12-bit value where each bit 
		represents a pin, with a value of 1 being touched and 0 not being touched.
		"""
		
		t = self._i2c_retry(self.readU16LE, MPR121_TOUCHSTATUS_L)
		return t & 0xFFFF



def startTouch16Serial():
	global SCLPin,SDOPin, HALF_BIT_TIME, CHARACTER_DELAY, sensBase
	global INPUTlastvalue, INPUTcount, INPUTtouchCountFilename
	HALF_BIT_TIME		= .001#	 1 msec
	CHARACTER_DELAY		= 5*HALF_BIT_TIME

	GPIO.setmode(GPIO.BCM)
	GPIO.setup(SCLPin,GPIO.OUT)
	GPIO.setup(SDOPin,GPIO.IN)

def getTouched16Serial(np):
	global SCLPin,SDOPin

	try:
		GPIO.output(SCLPin,GPIO.HIGH)
		time.sleep(HALF_BIT_TIME)
		time.sleep(CHARACTER_DELAY)
		keys =[0 for ii in range(np)]
		for button in range(np):
			GPIO.output(SCLPin,GPIO.LOW)
			time.sleep(HALF_BIT_TIME)
			keyval=GPIO.input(SDOPin)
			if not keyval:
				keys[button]=1
			GPIO.output(SCLPin,GPIO.HIGH)
			time.sleep(HALF_BIT_TIME)

		return keys

	except	Exception, e:
		U.toLog(-1, u"in Line {} has error={}".format(sys.exc_traceback.tb_lineno, e), doPrint =True)


def getTouched16i2c(np):
	global NumberOfPads , devClass16i2c
	try:
		keys = [0 for ii in range(np)]
		
		data = struct.unpack('2B', devClass16i2c.read(2))
		if data != (0,0):
			for ii in range(8):
				jj = (1 <<(7-ii))
				if data[0] & jj !=0: keys[ii]=1
			for ii in range(8):
				jj = (1 <<(7-ii))
				if data[1] & jj !=0: keys[ii +8]=1
			# pins[i] = 0/1 for i ..0..16 if pressed 
		return keys
	except	Exception, e:
		U.toLog(-1, u"in Line '%s' has error='%s'" % (sys.exc_traceback.tb_lineno, e), doPrint =True)


def startTouch12i2c():
	global sensBase
	global TOU_THRESH, REL_THRESH
	global devClass12i2c
	TOU_THRESH		= 12
	REL_THRESH		= 6
	devClass12i2c = MPR121()
	if not devClass12i2c.begin():
		U.toLog(-1, "Error initializing MPR121.	 Check your wiring!", doPrint =True)
		sys.exit(1)

def getTouched12i2c(np):
	global restartCount
	global devClass12i2c

	try:
		currentTap	= devClass12i2c.touched()
		channelData =[0 for ii in range(np)]
		for i in range(np):
			pin_bit = 1 << i
			channelData[i] = (pin_bit & currentTap !=0) &0x01
		return channelData

	except	Exception, e:
		restartCount+=1
		U.toLog(-1, u"in Line '%s' has error='%s'" % (sys.exc_traceback.tb_lineno, e), doPrint =True)



def readParams():
		global sensors,	 sensor, sensBase, oldSensParams
		global INPgpioType,INPUTcount,INPUTlastvalue,	oldParams
		global SCLPin, SDOPin
		global devClass16Serial,devClass16i2c,devClass12i2c, INPUTsensors,INPUTsensorTypes
		global oldRaw, lastRead

		INPUTcount = U.checkresetCount(INPUTcount)


		inp,inpRaw,lastRead2 = U.doRead(lastTimeStamp=lastRead)
		if inp == "": return
		if lastRead2 == lastRead: return
		lastRead   = lastRead2
		if inpRaw == oldRaw: return
		oldRaw	   = inpRaw

		oldSensors		  = copy.copy(sensors)

		U.getGlobalParams(inp)
		if "sensors"			in inp : sensors =				(inp["sensors"])
		if "debugRPI"			in inp:	 G.debug=			  int(inp["debugRPI"]["debugRPISENSOR"])
		if oldSensors == sensors: return 

		INPUTsensorTypes=[]
		INPUTsensors={}
		for sensor in sensors:
			if "INPUTtouch" in sensor.split("-")[0]:
				if sensor not in INPUTsensors:
					INPUTsensors[sensor]=[]
				for devId in sensors[sensor]:
					if sensors[sensor][devId]["devType"] not in INPUTsensors[sensor]:
						INPUTsensors[sensor].append(sensors[sensor][devId]["devType"])
					if sensors[sensor][devId]["devType"] not in INPUTsensorTypes: INPUTsensorTypes.append(sensors[sensor][devId]["devType"])
				
		if	INPUTsensors == {}:
			exit()

	   
		for sen in INPUTsensors:
			for devId in sensors[sen]:
				if "devType"	   in sensors[sen][devId] : devType = sensors[sen][devId]["devType"]
				else: continue
				if devType not in INPUTsensorTypes: INPUTsensorTypes.append(devType)
				if devType == "16Serial":
					for nn in range(30):
						sen = sensBase+"-"+str(nn)
						if sen not in sensors: continue
						try:
							if "SCLPin" in sensors[sen][devId]: 
								SCLPin = int(sensors[sen][devId]["SCLPin"])
						except:
							SCLPin = 27	   
						try:
							if "SDOPin" in sensors[sen][devId]: 
								SDOPin = int(sensors[sen][devId]["SDOPin"])
						except:
							SCLPin = 22 
					if devClass16Serial =="":
						startTouch16Serial()
						devClass16i2Serial = "started"

				elif devType == "16i2c":
					if devClass16i2c =="":
						devClass16i2c = U.simpleI2cReadWrite(0x57, 1) 

				elif devType == "12i2c":
					if devClass12i2c =="":
						startTouch12i2c()
			


def getINPUTcapacitor(sensors,data,devType, NPads):
	global INPUTlastvalue, INPUTcount
	new = False
	try:
		### get ALLL xx pad data data for sensor
		if	 devType =="16Serial":	channelData = getTouched16Serial(NPads)
		elif devType =="16i2c":		channelData = getTouched16i2c(NPads)
		elif devType =="12i2c":		channelData = getTouched12i2c(NPads)
		else: channelData  = {}
		#print devType, INPUTsensors, data
		#if sum( channelData ) > 0: print channelData
		new		= False
		for sensName in INPUTsensors:
			if devType not in INPUTsensors[sensName]: continue
			for devId in sensors[sensName]:
				if devType != sensors[sensName][devId]["devType"]: continue
				if "lowHighAs" in  sensors[sensName][devId]:
					lowHighAs =	 sensors[sensName][devId]["lowHighAs"]
				else:
					lowHighAs = "0"
				#print "devId, devType, channelData",devId, devType, channelData
				sens = sensors[sensName][devId]["INPUTS"]
				d={}
				for nn in range(len(sens)):
					if "gpio" not in sens[nn]:		continue
					gpioPIN = int(sens[nn]["gpio"])
					if	gpioPIN >= NPads:			continue
					if	gpioPIN < 0:				continue
					if lowHighAs =="0":
						if channelData[gpioPIN] ==0: dd="1"
						else:						 dd="0"
					else:
						if channelData[gpioPIN] ==0: dd="0"
						else:						 dd="1"

					if sens[nn]["count"] !="off":
						if sens[nn]["count"] == "up":
							if INPUTlastvalue[gpioPIN] != "1" and dd == "1":
								INPUTcount[gpioPIN]+=1
								new = True
						else:
							if INPUTlastvalue[gpioPIN] != "0" and dd == "0":
								INPUTcount[gpioPIN] += 1
								new = True
						d["INPUT_" + str(nn)] = INPUTcount[gpioPIN]

					else:
						d["INPUT_" + str(nn)] = dd
					INPUTlastvalue[gpioPIN] = dd
				if d !={}:
					if sensName not in data: data[sensName]={}
					data[sensName][devId] = copy.copy(d)
		if new: U.writeINPUTcount(INPUTcount)

	except	Exception, e:
		U.toLog(-1, u"in Line '%s' has error='%s'" % (sys.exc_traceback.tb_lineno, e), doPrint =True)

	return data,new


global SCLPin,SDOPin, HALF_BIT_TIME, CHARACTER_DELAY
global INPUTlastvalue, INPUTcount, INPUTtouchCountFilename
global NumberOfPads
global sensBase, sensor, sensors, oldSensParams
global devClass16Serial,devClass16i2c,devClass12i2c,INPUTsensors,INPUTsensorTypes
global restartCount
global devTypes
global oldRaw,	lastRead
oldRaw					= ""
lastRead				= 0

NumberOfPads		= {"16Serial":16, "16i2c":16,"12i2c":12}
restartCount		= 0
oldSensParams		= ""
devClass16Serial	=""
devClass16i2c		=""
devClass12i2c		=""

INPUTlastvalue	  = ["-1" for i in range(100)]
INPUTActive		  = {}
INPUTcount		  = [0 for i in range(100)]
oldParams		  = ""
sensBase		  = G.program
INPUTtouchCountFilename =sensBase+"Count"

#################### same for all 

myPID		= str(os.getpid())
U.killOldPgm(myPID,G.program+".py")# old old instances of myself if they are still running

sensor			  = G.program
sensors			  ={}
loopCount		  = 0

U.toLog(-1, "starting "+G.program+" program", doPrint =True)
readParams()
if U.getIPNumber() > 0:
	U.toLog(-1, " sensors no ip number	exiting ", doPrint =True)
	time.sleep(10)
	exit()

INPUTcount= U.readINPUTcount()

shortWait			= 2	   # seconds to send new INPUT info if available, tried interrupt, but that is NOT STABLE .. this works does ~ 0.2 sec to indigo round trip.
lastEverything		= time.time()-10000. # -1000 do the whole thing initially
G.lastAliveSend		= time.time()
lastData		= {}
lastMsg			= time.time()
quick			= False
G.tStart		= time.time() 
lastRead		= time.time()
lastGPIO		= ["" for ii in range(30)]
shortWait		= 0.1
lastData		= {}


######### specific for sensor ##########


#################### same for all 
while True:
	try:
		data0 ={}
		data={}
		tt= time.time()
		#print INPUTsensorTypes
		for devType in INPUTsensorTypes:
				data0, new = getINPUTcapacitor( sensors, data0, devType,NumberOfPads[devType])
				#print devType, data0
		if	data0 != {}:
			if data0 != lastData or (tt-lastMsg > G.sendToIndigoSecs) or quick: #
				lastGPIO= U.doActions(data0,lastGPIO, sensors, sensBase+"-1")
							
				lastMsg=tt
				lastData=copy.copy(data0)
				data["sensors"]		= data0
				U.sendURL(data)

		U.makeDATfile(G.program, data)
		quick = U.checkNowFile(G.program)
		U.manageActions("-loop-")
		if loopCount%50==0:
			U.echoLastAlive(G.program)
			if time.time()- lastRead > 10:
				readParams()
				lastRead = time.time()

		if restartCount >0:
			U.restartMyself(param="", reason=" io error",doPrint=True)

		loopCount+=1
		time.sleep(shortWait)
	except	Exception, e:
		U.toLog(-1, u"in Line '%s' has error='%s'" % (sys.exc_traceback.tb_lineno, e), doPrint =True)
		time.sleep(5.)


sys.exit(0)

	   