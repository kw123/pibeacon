#!/usr/bin/python
# -*- coding: utf-8 -*-
# by Karl Wachs
# 2018-01-28
# version 0.1 
##
##
#! /usr/bin/env python
# -*- coding: utf-8 -*-
####################


## ok for py3

import sys, os, time, json, datetime,subprocess,copy
import math
import copy
import smbus
try:	import serial
except:	pass


sys.path.append(os.getcwd())
import	piBeaconUtils	as U
import	piBeaconGlobals as G

G.program = "mhzCO2"
#simple bitfield object


#H.yasuhiro,2017/1/17

class mhz16_class_i2c:
	ppm			= 0
	IOCONTROL	= 0X0E << 3
	FCR			= 0X02 << 3
	LCR			= 0X03 << 3
	DLL			= 0x00 << 3
	DLH			= 0X01 << 3
	THR			= 0X00 << 3
	RHR			= 0x00 << 3
	TXLVL		= 0X08 << 3
	RXLVL		= 0X09 << 3


	def __init__(self, address = 0x4d, sensorType=1):
		"""Initializes an MH-Z CO2 sensor driver, opening the SMBus I2C connection at the given address and selecting the measure/calibrate command byte sequences and data offsets based on the sensor type.

		Inputs:
		    address (int): I2C bus address of the sensor (default 0x4d)
		    sensorType (int): Sensor variant selecting which command set and data offset to use
		Outputs:
		    None: Sets up I2C handle and command/data attributes
		"""
		self.i2c_addr = address
		self.i2c	  = smbus.SMBus(1)
		if sensorType ==1:
			self.cmd_measure	   = [0xFF,0x01,0x9C,0x00,0x00,0x00,0x00,0x00,0x63]
			self.cmd_calibrateZero = [0xFF,0x01,0x87,0x00,0x00,0x00,0x00,0x00,0x78]
			self.beginData		   = 4 
			self.commandByteReturn = self.cmd_measure[2]
		else:
			self.cmd_measure	   = [0xFF,0x01,0x86,0x00,0x00,0x00,0x00,0x00,0x79] # does not work 
			self.cmd_calibrateZero = [0xFF,0x87,0x87,0x00,0x00,0x00,0x00,0x00,0xF2]	 # does not work 
#			self.cmd_calibrateZero = [0xFF,0x01,0x87,0x00,0x00,0x00,0x00,0x00,0x78]
			self.beginData		   = 2 
			self.commandByteReturn = self.cmd_measure[2]

	def start(self):
		"""Initializes the sensor's UART-over-I2C bridge registers by writing IOCONTROL, FIFO control, line control, and baud-rate divisor registers to configure communication.

		Inputs:
		    None.
		Outputs:
		    None: Writes configuration values to the device registers over I2C
		"""
		try:
			self.write_register(self.IOCONTROL, 0x08)
		except IOError:
			pass

		self.write_register(self.FCR, 0x07)
		self.write_register(self.LCR, 0x83)
		self.write_register(self.DLL, 0x60)
		self.write_register(self.DLH, 0x00)
		self.write_register(self.LCR, 0x03)
 
	def calibrate(self):
		"""Performs a zero-point calibration of the CO2 sensor by resetting the FIFO and sending the calibrate-zero command sequence; on error logs the exception and sets co2 to -1.

		Inputs:
		    None.
		Outputs:
		    None: Sends the calibration command; sets self.co2 to -1 on failure
		"""
		try:
			self.write_register(self.FCR, 0x07)
			self.send(self.cmd_calibrateZero)
			time.sleep(0.1)
			return
		except Exception as e:
			U.logger.log(20,"", exc_info=True)
		self.co2 = -1
 
	def measure(self):
		"""Triggers a CO2 measurement by resetting the FIFO, sending the measure command, and parsing the received response; on error logs the exception and sets co2 to -1.

		Inputs:
		    None.
		Outputs:
		    None: Updates self.co2 via parse(); sets it to -1 on failure
		"""
		try:
			self.write_register(self.FCR, 0x07)
			self.send(self.cmd_measure)
			self.parse(self.receive())
			return
		except Exception as e:
			U.logger.log(20,"", exc_info=True)
		self.co2 = -1
 
	def parse(self, response):
		"""Parses a 9-byte sensor response frame, validating the start byte, command byte echo, and checksum, then extracts the CO2 value from the two data bytes into self.co2 (or -1 if invalid).

		Inputs:
		    response (list): List of byte values returned by the sensor
		Outputs:
		    None: Sets self.co2 to the parsed CO2 ppm value or -1 if the frame is invalid
		"""
		checksum = 0
		#print response
 
		if len(response) < 9:
			if len(response) == 8 and response[0] !=255:
				response = [255] + response
				#print "fixed"
			else:
				self.co2 = -1
				return
 
		for i in range (0, 9):
			checksum += response[i]
			
		self.co2 = -1
		if response[0] == 0xFF:
			if response[1] == self.commandByteReturn:
				if checksum % 256 == 0xFF:
					self.co2  = (response[self.beginData]<<8) + response[self.beginData+1]
		#print self.co2
 
	def read_register(self, reg_addr):
		"""Reads a single byte from the given register address over I2C after a short delay.

		Inputs:
		    reg_addr (int): Register address to read from
		Outputs:
		    int: The byte value read from the register
		"""
		time.sleep(0.001)
		return self.i2c.read_byte_data(self.i2c_addr, reg_addr)

	def write_register(self, reg_addr, val):
		"""Writes a single byte value to the given register address over I2C after a short delay.

		Inputs:
		    reg_addr (int): Register address to write to
		    val (int): Byte value to write
		Outputs:
		    None: Writes the value to the register over I2C
		"""
		time.sleep(0.001)
		self.i2c.write_byte_data(self.i2c_addr, reg_addr, val)

	def send(self, command):
		"""Sends a command byte sequence to the sensor by recording the command byte and, if the transmit FIFO has enough room, writing the command bytes as an I2C block to the THR register.

		Inputs:
		    command (list): List of command bytes to transmit to the sensor
		Outputs:
		    None: Writes the command block to the device over I2C if TX buffer space permits
		"""
		self.commandByte= command[2]
		if self.read_register(self.TXLVL) >= len(command):	# can we send enough bytes , should be 9
			self.i2c.write_i2c_block_data(self.i2c_addr, self.THR, command)

	def receive(self):
		"""Reads up to 9 response bytes from the I2C UART bridge by polling the RX FIFO level register and reading available bytes from the RHR register, retrying briefly on errors and timing out after 0.2 seconds.

		Inputs:
		    None.
		Outputs:
		    list: List of received byte values (empty list on failure or timeout)
		"""
		try:
			n	  = 9
			buf	  = []
			start = time.time()
			errcountMAX = 2
			while n > 0:
				try: 
					rx_level = self.read_register(self.RXLVL) # are there enough bytes available to read , should be 9.
				except Exception as e:
					time.sleep(0.004)
					errcountMAX -= 1
					if errcountMAX == 0: 
						U.logger.log(10, "receive read_register too may tries stopping read,  has error='%s'" % ( e))
						return buf
					continue
					
				if rx_level > n:
					rx_level = n
 
				buf.extend(self.i2c.read_i2c_block_data(self.i2c_addr, self.RHR, rx_level))
				n = n - rx_level
 
				if time.time() - start > 0.2:
					break
				
			return buf
		except Exception as e:
			U.logger.log(20,"", exc_info=True)
		return []

class mhz_class_serial:
	pass
	
#################################		 
	def __init__(self,serialPort="/dev/serial0",sensorType = 2):
	
	
		"""Initializes the serial-based MH-Z CO2 sensor driver, setting up measure/calibration command byte sequences and amplification-range command tables for the given sensor type, then opens a 9600-baud pyserial connection on the specified serial port.

		Inputs:
		    serialPort (str): Serial device path to open (defaults to /dev/serial0)
		    sensorType (int): Sensor variant selector choosing the command byte set (defaults to 2)
		Outputs:
		    None: Configures instance attributes and opens the serial port
		"""
		if sensorType ==1:
			self.cmd_measure		= [0xFF,0x01,0x9C,0x00,0x00,0x00,0x00,0x00,0x63]
			self.cmd_calibrateZero	= [0xFF,0x01,0x87,0x00,0x00,0x00,0x00,0x00,0x78]
			self.beginData			= 4 
			self.commandByteReturn = self.cmd_measure[2]
		else:
			self.cmd_measure		= [0xFF,0x01,0x86,0x00,0x00,0x00,0x00,0x00,0x79] # does not work 
			self.cmd_calibrateZero	= [0xFF,0x01,0x87,0x00,0x00,0x00,0x00,0x00,0x78]
#			self.beginData		   = 2 
			self.commandByteReturn = self.cmd_measure[2]

		self.amplification={ "1000":[0xFF, 0x01, 0x99, 0x00, 0x00, 0x00, 0x03, 0xE8, 0x7B],
							 "2000":[0xFF, 0x01, 0x99, 0x00, 0x00, 0x00, 0x07, 0xD0, 0x8F],
							 "3000":[0xFF, 0x01, 0x99, 0x00, 0x00, 0x00, 0x0B, 0xB8, 0xA3],
							 "5000":[0xFF, 0x01, 0x99, 0x00, 0x00, 0x00, 0x13, 0x88, 0xCB]}
	
		U.logger.log(20, "mhz_class port:{} ".format(serialPort))
		self.port = serialPort
		#print 'Trying port %s ' % self.port
		self.co2 = -1
		self.ser			= serial.Serial()
		self.ser.port		= self.port 
		self.ser.stopbits	= serial.STOPBITS_ONE
		self.ser.bytesize	= serial.EIGHTBITS
		self.ser.baudrate	= 9600
		self.ser.timeout	= 2
		self.ser.open()

#################################		 
	def start(self):
		"""Ensures the serial connection is open; reopens it if it was closed. Serial counterpart to mhz16_class_i2c.start() so shared restart paths work for both sensor types.

		Inputs:
		    None.
		Outputs:
		    None: Opens the serial port if not already open
		"""
		if not self.ser.is_open: self.ser.open()

#################################		 
	def measure(self):
		"""Triggers a CO2 measurement by sending the measure command over serial, then parsing the received response into the co2 attribute; sets co2 to -1 on error.

		Inputs:
		    None.
		Outputs:
		    None: Updates self.co2 with the measured value or -1
		"""
		try:
			self.send(self.cmd_measure)
			self.parse(self.receive())
			return
		except Exception as e:
			U.logger.log(20,"", exc_info=True)
		self.co2 = -1

#################################		 
	def setRange(self,range=3000):
		"""Sets the sensor's measurement amplification/range by looking up the matching command sequence in the amplification table for the given range value and sending it over serial.

		Inputs:
		    range (int or str): Desired CO2 range key (e.g. 1000/2000/3000/5000)
		Outputs:
		    None: Sends a range command over serial; no-op if range not recognized
		"""
		r = str(range)
		try:
			if r in self.amplification:
				self.send(self.amplification[str(r)])
				return
		except Exception as e:
			U.logger.log(20,"", exc_info=True)

#################################		 
	def calibrate(self):
		"""Performs zero-point calibration by sending the calibrate-zero command over serial and parsing the response into the co2 attribute; sets co2 to -1 on error.

		Inputs:
		    None.
		Outputs:
		    None: Sends calibration command and updates self.co2
		"""
		try:
			self.send(self.cmd_calibrateZero)
			self.parse(self.receive())
			return
		except Exception as e:
			U.logger.log(20,"", exc_info=True)
		self.co2 = -1


#################################		 
	def send(self,cmd):
		"""Writes a raw command byte sequence to the sensor over the serial port.

		Inputs:
		    cmd (list): Byte values forming the command to transmit
		Outputs:
		    None: Writes the command bytes to the serial port
		"""
		self.ser.write(cmd)

#################################		 
	def receive(self):			  
		"""Reads 9 bytes from the serial port and converts them into a list of integer byte values.

		Inputs:
		    None.
		Outputs:
		    list: List of up to 9 received byte values
		"""
		s = self.ser.read(9)
		z=bytearray(s)
		retV =[]
		for x in z:
			retV.append(x)
		#print retV
		return retV

#################################		 
	def parse(self, response):
		"""Validates a 9-byte sensor response by checking the start byte, command echo byte and checksum, and on success extracts the CO2 concentration into self.co2 (otherwise leaves it at -1).

		Inputs:
		    response (list): 9-element list of response byte values from the sensor
		Outputs:
		    None: Sets self.co2 and self.raw from the parsed response
		"""
		checksum = 0
		#print response

		self.co2 = -1
		self.raw = response
		try: 
			ll = len(response)
		except Exception as e:
			U.logger.log(20,"", exc_info=True)
			return 
		if ll != 9: return
		for i in range (0, 9):
			checksum += response[i]
			
		if response[0] == 0xFF:
			if response[1] == self.commandByteReturn:
				if checksum % 256 == 0xFF:
					self.co2  = (response[self.beginData]<<8) + response[self.beginData+1]
		#print self.co2, response, [hex(no) for no in response]
		return 



# ===========================================================================
# read params
# ===========================================================================

#################################		 
def readParams():
	"""Reads the plugin's parameter/config file, and when it has changed, updates global sensor settings (refresh interval, I2C address, interface type, deltaX, CO2 normal/offset, sensitivity, calibration thresholds, send delta) for each configured device, (re)starting sensors whose settings changed and removing sensors no longer present.

	Inputs:
	    None.
	Outputs:
	    None: Updates module-level globals and starts/removes sensor instances
	"""
	global sensorList, sensors, logDir, sensor, sensorRefreshSecs, displayEnable
	global rawOld,i2cAddress
	global deltaX, mhz16, minSendDelta
	global oldRaw, lastRead
	global startTime
	global CO2normal, CO2offset,sensitivity,timeaboveCalibrationMAX
	global interfaceType
	try:


		inp, inpRaw, lastRead2 = U.doRead(lastTimeStamp=lastRead)
		if inp == "": return
		if lastRead2 == lastRead: return
		lastRead 	= lastRead2
		if inpRaw == oldRaw: return
		oldRaw		= inpRaw
		
		externalSensor=False
		sensorList=[]
		sensorsOld= copy.copy(sensors)


		
		U.getGlobalParams(inp)


		if "sensorList"			in inp: sensorList=			(inp["sensorList"])
		if "sensors"			in inp: sensors =				(inp["sensors"])

		if sensor not in sensors:
			U.logger.log(20, G.program+" is not in parameters = not enabled, stopping "+G.program+".py" )
			exit()


		U.logger.log(10, G.program+" reading new parameter file" )

		if sensorRefreshSecs == 91:
			try:
				xx = str(inp["sensorRefreshSecs"]).split("#")
				sensorRefreshSecs = float(xx[0]) 
			except:
				sensorRefreshSecs = 91
		deltaX={}
		restart = False
		for devId in sensors[sensor]:
			deltaX[devId]  = 0.1

			try:
				if "sensorRefreshSecs" in sensors[sensor][devId]:
					xx = sensors[sensor][devId]["sensorRefreshSecs"].split("#")
					sensorRefreshSecs = float(xx[0]) 
			except:
				sensorRefreshSecs = 91
			
			old = i2cAddress
			i2cAddress = U.getI2cAddress(sensors[sensor][devId],default="")
			if old != i2cAddress: 
				#U.logger.log(20, "new i2cAddress {} vs {}". format(old, i2cAddress))
				restart = True

			try: old = interfaceType
			except: old = ""; interfaceType ="i2c"
			try:
				if "interfaceType" in sensors[sensor][devId]: 
					interfaceType= sensors[sensor][devId]["interfaceType"]
				else:
					interfaceType ="i2c"
			except:
				interfaceType = "i2c"
			if old != interfaceType: 
				#U.logger.log(20, "new interface")
				restart = True

			try:
				if "deltaX" in sensors[sensor][devId]: 
					deltaX[devId]= float(sensors[sensor][devId]["deltaX"])/100.
			except:
				deltaX[devId] = 0.1

			try:
				if "CO2normal" in sensors[sensor][devId]: 
					CO2normal[devId]= float(sensors[sensor][devId]["CO2normal"])
			except:
				CO2normal[devId] = 410

			try:
				if "CO2offset" in sensors[sensor][devId]: 
					CO2offset[devId]= float(sensors[sensor][devId]["CO2offset"])
			except:
				CO2offset[devId] = 0

			try:
				if "sensitivity" in sensors[sensor][devId]: 
					sensitivity[devId]= sensors[sensor][devId]["sensitivity"]
			except:
				sensitivity[devId] = "medium"

			try:
				if "timeaboveCalibrationMAX" in sensors[sensor][devId]: 
					timeaboveCalibrationMAX[devId]= float(sensors[sensor][devId]["sensitivity"])
			except:
				timeaboveCalibrationMAX[devId] = 1200


			try:
				if "minSendDelta" in sensors[sensor][devId]: 
					minSendDelta= float(sensors[sensor][devId]["minSendDelta"])
			except:
				minSendDelta = 5.

				
			if devId not in mhz16sensor or restart:
				U.logger.log(20," new / changed parameters read: i2cAddress:{};  minSendDelta:{};  deltaX:{};  sensorRefreshSecs:{};  restart:{}".format(i2cAddress, minSendDelta, deltaX[devId], sensorRefreshSecs, restart))
				startSensor(devId, i2cAddress)
				if mhz16sensor[devId] =="":
					return
				
		deldevID={}
		for devId in mhz16sensor:
			if devId not in sensors[sensor]:
				deldevID[devId]=1
		for dd in  deldevID:
			del mhz16sensor[dd]
		if len(mhz16sensor) ==0: 
			####exit()
			pass


	except Exception as e:
		U.logger.log(20,"", exc_info=True)
		U.logger.log(20, "{}".format(sensors[sensor]))
		



#################################
def startSensor(devId,i2cAddress):
	"""Starts a CO2 sensor for the given device by selecting the I2C mux channel and creating either an I2C sensor instance or, for serial interfaces, setting up GPIO calibration, opening a serial MH-Z sensor, setting its range, calibrating it and creating the serial sensor object.

	Inputs:
	    devId (str): Indigo device identifier to start the sensor for
	    i2cAddress (str): I2C address for the sensor (default fallback used if empty)
	Outputs:
	    None: Creates the sensor instance in mhz16sensor and resets the I2C mux
	"""
	global sensors, sensor
	global startTime
	global mhz16sensor , interfaceType
	
	U.logger.log(20,"==== Start {} ===== @ i2c={} , interfaceType:{}" .format(G.program, i2cAddress, interfaceType))
	startTime =time.time()


	i2cAdd = U.muxTCA9548A(sensors[sensor][devId]) # switch mux on if requested and use the i2c address of the mix if enabled
	
	try:
		if interfaceType =="i2c":
			mhz16sensor[devId]	=  mhz16_class_i2c(address=i2cAdd, sensorType=2)
		else:
			try:import serial
			except: pass
			sP = U.getSerialDEV()
			restartSensor()					# the pin is set up by the shared gpio layer on first use
		
			mhz16sensor[devId]	= mhz_class_serial(serialPort = sP)
			mhz16sensor[devId].setRange(range=3000)
			calibrateSensor(devId)
			time.sleep(1)
			mhz16sensor[devId].start()
						
	except Exception as e:
		U.logger.log(20,"", exc_info=True)
		mhz16sensor[devId] =""
	time.sleep(.1)

	U.muxTCA9548Areset()



#################################
def restartSensor():
	"""Power-cycles or resets the sensor by toggling the calibration GPIO pin low for 7 seconds and then back high.

	Inputs:
	    None.
	Outputs:
	    None: Drives the calibration GPIO pin to restart the sensor
	"""
	global mhz16sensor, calibrationPin
	try: 
		U.gpioOut(calibrationPin, "pulseoff", secs=7)		# low for 7 s, then high again
		time.sleep(0.1)
	except Exception as e:
		U.logger.log(20,"", exc_info=True)
	time.sleep(.1)




#################################
def calibrateSensor(devId):
	"""Calibrates the CO2 sensor for a device by selecting the I2C mux channel, zeroing the CO2 offset, calling the sensor calibrate routine, taking three measurements, and computing a new CO2 offset as the configured normal value minus the measured CO2.

	Inputs:
	    devId (str): Indigo device identifier to calibrate
	Outputs:
	    None: Updates the global CO2offset for the device
	"""
	global sensors, sensor
	global mhz16sensor
	global CO2normal, CO2offset,sensitivity
	
	i2cAdd = U.muxTCA9548A(sensors[sensor][devId]) # switch mux on if requested and use the i2c address of the mix if enabled
	#print "calibrating"
	ret ="" 
	try: 
		CO2offset[devId] = 0  
		mhz16sensor[devId].calibrate()
		time.sleep(5)
		ret = getValues(devId,nMeasurements=3)
		if ret == "badSensor":
			U.logger.log(20, " calibration did not work exit ")
			time.sleep(5)
			return
			
		co2 = ret["CO2"]

		CO2offset[devId] = CO2normal[devId] - co2 
		#print "calib co2, CO2offset, CO2normal: ", co2, CO2offset[devId], CO2normal[devId]
	except Exception as e:
		U.logger.log(20,"", exc_info=True)
	time.sleep(.1)


#################################
def getValues(devId,nMeasurements=5):
	"""Reads CO2 from an MH-Z16 sensor on the given device, averaging multiple measurements while skipping invalid (-1) readings, applies a per-device offset, and returns the computed values. On failure or all-bad reads it increments a bad-sensor counter, restarts the sensor, and may return 'badSensor'.

	Inputs:
	    devId (str): device id keyed into the mhz16sensor/sensors maps
	    nMeasurements (int): number of readings to average (minimum 2)
	Outputs:
	    dict or str: dict with CO2, CO2offset, CO2calibration and raw values, or the string 'badSensor' on failure
	"""
	global sensor, sensors, mhz16sensor, badSensor
	global startTime, CO2offset, CO2normal, sensitivity

	ret = "badSensor"
	try:
		if mhz16sensor[devId] =="":
			badSensor +=1
			return "badSensor"
		i2cAdd = U.muxTCA9548A(sensors[sensor][devId]) # switch mux on if requested and use the i2c address of the mix if enabled
		if mhz16sensor[devId] =="": 
			badSensor +=1
			return "badSensor"
		nnn			= max(2,nMeasurements)
		raw			= 0
		nMeas		= 0.
		addIfBad 	= 2
		ii			= 0
		while ii < nnn:
			ii+=1
			mhz16sensor[devId].measure()
			co2 =  mhz16sensor[devId].co2
			U.logger.log(10, " co2 raw: %d" %co2 )
			if co2 ==-1: 
				ii -= addIfBad	# onetime only 
				addIfBad = 0
				U.logger.log(20, "bad data read ")

				continue
			raw += co2
			nMeas +=1.
			if ii != nnn-1: time.sleep(2)
			if ii%5 ==0: U.echoLastAlive(G.program)

		if raw ==0:
			needRestart =True
			badSensor+=1
			if badSensor >3: ret = "badSensor"
			mhz16sensor[devId].start()
			return ret
			
		raw /= nMeas 
		CO2 = raw + CO2offset[devId]
		#print "raw, CO2, CO2offset, CO2normal", raw, CO2, CO2offset[devId], CO2normal[devId]
		ret = {"CO2":			 ( round(CO2,1)			   )
			   ,"CO2offset":	 ( round(CO2offset[devId],1) )
			   ,"CO2calibration":( round(CO2normal[devId],1) ) 
			   ,"raw":			 ( round(raw,1)			   ) }
		U.logger.log(10, "{}".format(ret)) 
		badSensor = 0
	except Exception as e:
		U.logger.log(20,"", exc_info=True)
		badSensor+=1
		if badSensor >3: ret = "badSensor"
		mhz16sensor[devId].start()
 
	U.muxTCA9548Areset()
	return ret






############################################
global rawOld,i2cAddress
global sensor, sensors, badSensor
global deltaX, mhz16sensor, minSendDelta
global	lastRead
global startTime,  lastMeasurement, reStartReq 
global CO2offset, CO2normal, sensitivity,timeaboveCalibrationMAX
global interfaceType


interfaceType				= ""
i2cAddress					=""
timeOKCalibration			={}
timeaboveCalibrationMAX		={}
sensitivity					= {}
CO2normal					= {}
CO2offset					= {}
reStartReq					= False
startTime					= time.time()
lastMeasurement				= time.time()
oldRaw						= ""
lastRead					= 0
minSendDelta				= 5.
loopCount					= 0
sensorRefreshSecs			= 91
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
mhz16sensor					={}
deltaX						= {}
displayEnable				= 0
U.setLogging()

myPID		= str(os.getpid())
U.killOldPgm(myPID,G.program+".py")# kill old instances of myself if they are still running


if U.getIPNumber() > 0:
	time.sleep(10)
	exit()
readParams()

time.sleep(1)

lastRead = time.time()

U.echoLastAlive(G.program)

#					used for deltax comparison to trigger update to indigo
lastValues0			= {"CO2":0}
lastValues			= {}
lastData			= {}
lastSend			= 0
lastDisplay			= 0
lastRead			= time.time()
G.lastAliveSend		= time.time() -1000

msgCount			= 0
loopSleep			= 1
sensorWasBad		= False


calibTime			= time.time()
needCalibration = False
calibrationWaitTime = 60 # secs

calibrating			= 20

loopCount = 0
while True:
	try:
		data = {"sensors": {sensor:{}}}
		sendData = False
		if sensor in sensors:
			for devId in sensors[sensor]:
				if devId not in lastValues: 
					lastValues[devId]			= copy.copy(lastValues0)
					timeOKCalibration[devId ]	= 0
				
				if loopCount ==0:
					calibTime = time.time()
					calibrateSensor(devId)

				loopCount +=1
				values = getValues(devId, nMeasurements=3 )
				if values == "": continue
				data["sensors"][sensor][devId]={}
				if values =="badSensor":
					sensorWasBad = True
					data["sensors"][sensor][devId]="badSensor"
					if badSensor < 5: 
						U.logger.log(20," bad sensor")
						U.sendURL(data)
					else:
						U.restartMyself(param="", reason="badsensor",doPrint=True)
					lastValues[devId]  =copy.copy(lastValues0)
					if badSensor > 5: reStartReq = True 
					continue
				elif values["CO2"] !="" :
					if sensorWasBad: # sensor was bad, back up again, need to do a restart to set config 
						U.restartMyself(reason=" back from bad sensor, need to restart to get sensors reset",doPrint=False)
					
					data["sensors"][sensor][devId] = values
					needCalibration = False
					x1 = data["sensors"][sensor][devId]["CO2"] - CO2normal[devId] 

					if	 sensitivity[devId] =="small" : recalib = [20,20]
					elif sensitivity[devId] =="medium": recalib = [30,30]
					else							  : recalib = [50,50]

					if (  x1 < -recalib[0] ) or  ( abs(x1) > recalib[1] and time.time() - calibTime < calibrationWaitTime ): 
						#print "delta calib",  data["sensors"][sensor][devId]["CO2"], CO2normal[devId],data["sensors"][sensor][devId]["CO2"] - CO2normal[devId] , time.time() - calibTime 
						needCalibration = True
					else:
						if abs(x1)	> recalib[1]:
							if time.time() - timeOKCalibration[devId] > timeaboveCalibrationMAX[devId]:
								#print "time for recalibration after %d [sec]"%(time.time() - timeOKCalibration)
								needCalibration = True
						else:
							timeOKCalibration[devId] = time.time()
							calibrating -= 1
					deltaN = 0
					delta  = 99999
					for xx in lastValues0:
						try:
							current = float(values[xx])
							delta	= abs(current-lastValues[devId][xx]) / max (0.5,(current+lastValues[devId][xx])/2.)
							deltaN	= max(deltaN, delta)
							lastValues[devId][xx] = current
						except: pass
					#print "delta %.4f" % deltaN, deltaX[devId]
					#print " delta co2 compared to last:", delta
					if time.time() - calibTime > calibrationWaitTime: 
						data["sensors"][sensor][devId]["calibration"] ="set"
					elif (	(time.time() - calibTime) > calibrationWaitTime/3)	and delta < abs(recalib[0]):
						data["sensors"][sensor][devId]["calibration"] ="set Preliminary"
					else:
						data["sensors"][sensor][devId]["calibration"] ="finding"
				else:
					continue
				#print "G.sendToIndigoSecs), G.lastAliveSend , minSendDelta",G.sendToIndigoSecs, G.lastAliveSend , minSendDelta
				#U.logger.log(20,"{}, {}, {}, {}, {}".format(deltaN > deltaX[devId], (  time.time() - G.lastAliveSend  > abs(G.sendToIndigoSecs) ) , quick,  ( time.time() - G.lastAliveSend > minSendDelta ), calibrating ))
				if (( deltaN > deltaX[devId]   or  (  time.time() - G.lastAliveSend  > abs(G.sendToIndigoSecs) ) or  quick  ) and ( time.time() - G.lastAliveSend > minSendDelta ) ):
					sendData = True

		#print "calibrating", calibrating
		if sendData or calibrating >=0:
			U.sendURL(data)
		loopCount +=1

		##U.makeDATfile(G.program, data)
		quick = U.checkNowFile(G.program)
		U.echoLastAlive(G.program)

		if loopCount %5 ==0 and not quick:
			if time.time() - lastRead > 5.:
				readParams()
				lastRead = time.time()

		if U.checkNewCalibration(G.program) or needCalibration :
			U.logger.log(20, "set CO2 calibration")
			if sensor in sensors:
				for devId in sensors[sensor]:
					calibrateSensor(devId)
					timeOKCalibration[devId] = time.time()
					calibTime				 = time.time()
					calibrating				 = 10

		if not quick:
			time.sleep(loopSleep)
		if reStartReq:
			time.sleep(5)
			subprocess.call("/usr/bin/python "+G.homeDir+G.program+".py &", shell=True)

	except Exception as e:
		U.logger.log(20,"", exc_info=True)
		time.sleep(5.)
try: 	G.sendThread["run"] = False; time.sleep(1)
except: pass
sys.exit(0)
 

		