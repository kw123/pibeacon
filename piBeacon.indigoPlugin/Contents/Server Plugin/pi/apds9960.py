#!/usr/bin/env python
# -*- coding: utf-8 -*-
# by Karl Wachs
# feb 5 2016
# version 0.9 
##
##
##
#
#  copied from various sources especialy SPARKFUN
#
##

##


import	sys, os, time, json, datetime,subprocess,copy
import math
import io
import fcntl # used to access I2C parameters like addresses

try:
	if subprocess.Popen("/usr/bin/ps -ef | /usr/bin/grep pigpiod  | /usr/bin/grep -v grep",shell=True,stdout=subprocess.PIPE,stderr=subprocess.PIPE).communicate()[0].decode('utf-8').find("pigpiod")< 5:
		subprocess.call("/usr/bin/sudo /usr/bin/pigpiod &", shell=True)
	import gpiozero
	from gpiozero.pins.pigpio import PiGPIOFactory
	from gpiozero import Device
	Device.pin_factory = PiGPIOFactory()
	useGPIO = False
except:
	try:
		import RPi.GPIO as GPIO
		GPIO.setmode(GPIO.BCM)
		GPIO.setwarnings(False)
		useGPIO = True
	except: pass

sys.path.append(os.getcwd())
import	piBeaconUtils	as U
import	piBeaconGlobals as G

G.program = "apds9960"


import smbus


class APDS9960():

		def __init__(self,i2cAdd=0x39):
			"""Constructs the APDS9960 driver instance, storing the I2C address and initializing all register addresses, bit-field masks, gain/LED/gesture parameter constants, and default configuration values used by the sensor.

			Inputs:
			    i2cAdd (int): I2C address of the APDS9960 (default 0x39)
			Outputs:
			    None: sets instance attributes for registers, constants, and defaults
			"""
			self.DEBUG					= 0

			##/* APDS-9960 I2C address */
			self.address				 = i2cAdd

			##/* Gesture parameters */
			self.GESTURE_THRESHOLD_OUT	 = 4
			self.GESTURE_THRESHOLD_OUT_2 =256
			self.GESTURE_SENSITIVITY_1	 = 1
			self.GESTURE_SENSITIVITY_2	 = 2

			##/* Error code for returned values */
			self.ERROR					= 0xFF

			##/* Acceptable device IDs */
			self.APDS9960_ID_1			= 0xAB
			self.APDS9960_ID_2			= 0x9C 

			##/* Misc parameters */
			self.FIFO_PAUSE_TIME		 = 0.003	  # Wait period (ms) between FIFO reads

			##/* APDS-9960 register addresses */
			self.APDS9960_ENABLE		= 0x80
			self.APDS9960_ATIME			= 0x81
			self.APDS9960_WTIME			= 0x83
			self.APDS9960_AILTL			= 0x84
			self.APDS9960_AILTH			= 0x85
			self.APDS9960_AIHTL			= 0x86
			self.APDS9960_AIHTH			= 0x87
			self.APDS9960_PILT			= 0x89
			self.APDS9960_PIHT			= 0x8B
			self.APDS9960_PERS			= 0x8C
			self.APDS9960_CONFIG1		= 0x8D
			self.APDS9960_PPULSE		= 0x8E
			self.APDS9960_CONTROL		= 0x8F
			self.APDS9960_CONFIG2		= 0x90
			self.APDS9960_ID			= 0x92
			self.APDS9960_STATUS		= 0x93
			self.APDS9960_CDATAL		= 0x94
			self.APDS9960_CDATAH		= 0x95
			self.APDS9960_RDATAL		= 0x96
			self.APDS9960_RDATAH		= 0x97
			self.APDS9960_GDATAL		= 0x98
			self.APDS9960_GDATAH		= 0x99
			self.APDS9960_BDATAL		= 0x9A
			self.APDS9960_BDATAH		= 0x9B
			self.APDS9960_PDATA			= 0x9C
			self.APDS9960_POFFSET_UR	= 0x9D
			self.APDS9960_POFFSET_DL	= 0x9E
			self.APDS9960_CONFIG3		= 0x9F
			self.APDS9960_GPENTH		= 0xA0
			self.APDS9960_GEXTH			= 0xA1
			self.APDS9960_GCONF1		= 0xA2
			self.APDS9960_GCONF2		= 0xA3
			self.APDS9960_GOFFSET_U		= 0xA4
			self.APDS9960_GOFFSET_D		= 0xA5
			self.APDS9960_GOFFSET_L		= 0xA7
			self.APDS9960_GOFFSET_R		= 0xA9
			self.APDS9960_GPULSE		= 0xA6
			self.APDS9960_GCONF3		= 0xAA
			self.APDS9960_GCONF4		= 0xAB
			self.APDS9960_GFLVL			= 0xAE
			self.APDS9960_GSTATUS		= 0xAF
			self.APDS9960_IFORCE		= 0xE4
			self.APDS9960_PICLEAR		= 0xE5
			self.APDS9960_CICLEAR		= 0xE6
			self.APDS9960_AICLEAR		= 0xE7
			self.APDS9960_GFIFO_U		= 0xFC
			self.APDS9960_GFIFO_D		= 0xFD
			self.APDS9960_GFIFO_L		= 0xFE
			self.APDS9960_GFIFO_R		= 0xFF

			##/* Bit fields */
			self.APDS9960_PON			= 0b00000001  # power on
			self.APDS9960_AEN			= 0b00000010  # color enable
			self.APDS9960_PEN			= 0b00000100  # prox enable
			self.APDS9960_WEN			= 0b00001000  # color int enable
			self.APSD9960_AIEN			= 0b00010000  # color wait enable
			self.APDS9960_PIEN			= 0b00100000  # prox int enable
			self.APDS9960_GEN			= 0b01000000  # Gesture enable
			self.APDS9960_GVALID		= 0b00000001  # Gesture valid

			##/* On/Off definitions */
			self.OFF					= 0
			self.ON						= 1

			##/* Acceptable parameters for self.setMode */
			self.POWER					= 0
			self.AMBIENT_LIGHT			= 1
			self.PROXIMITY				= 2
			self.WAIT					= 3
			self.AMBIENT_LIGHT_INT		= 4
			self.PROXIMITY_INT			= 5
			self.GESTURE				= 6
			self.ALL					= 7

			##/* LED Drive values */
			self.LED_DRIVE_100MA		= 0
			self.LED_DRIVE_50MA			= 1
			self.LED_DRIVE_25MA			= 2
			self.LED_DRIVE_12_5MA		= 3

			##/* Proximity Gain (PGAIN) values */
			self.PGAIN_1X				= 0
			self.PGAIN_2X				= 1
			self.PGAIN_4X				= 2
			self.PGAIN_8X				= 3

			##/* ALS Gain (AGAIN) values */
			self.AGAIN_1X				= 0
			self.AGAIN_4X				= 1
			self.AGAIN_16X				= 2
			self.AGAIN_64X				= 3

			##/* Gesture Gain (GGAIN) values */
			self.GGAIN_1X				= 0
			self.GGAIN_2X				= 1
			self.GGAIN_4X				= 2
			self.GGAIN_8X				= 3

			##/* LED Boost values */
			self.LED_BOOST_100			= 0
			self.LED_BOOST_150			= 1
			self.LED_BOOST_200			= 2
			self.LED_BOOST_300			= 3	   

			##/* Gesture wait time values */
			self.GWTIME_0MS				= 0
			self.GWTIME_2_8MS			= 1
			self.GWTIME_5_6MS			= 2
			self.GWTIME_8_4MS			= 3
			self.GWTIME_14_0MS			= 4
			self.GWTIME_22_4MS			= 5
			self.GWTIME_30_8MS			= 6
			self.GWTIME_39_2MS			= 7

			##/* Default values */
			self.DEFAULT_ATIME			= 219	  # 103ms
			self.DEFAULT_WTIME			= 246	  # 27ms
			self.DEFAULT_PROX_PPULSE	= 0x87	  # 16us, 8 pulses
			self.DEFAULT_GESTURE_PPULSE = 0x89	  # 16us, 10 pulses
			self.DEFAULT_POFFSET_UR		= 0		  # 0 offset
			self.DEFAULT_POFFSET_DL		= 0		  # 0 offset	  
			self.DEFAULT_CONFIG1		= 0x60	  # No 12x wait (WTIME) factor
			self.DEFAULT_LDRIVE			= 0
			self.DEFAULT_PGAIN			= 2
			self.DEFAULT_AGAIN			= 1
			self.DEFAULT_PILT			= 0		  # Low proximity threshold
			self.DEFAULT_PIHT			= 50	  # High proximity threshold
			self.DEFAULT_AILT			= 0xFFFF  # Force interrupt for calibration
			self.DEFAULT_AIHT			= 0
			self.DEFAULT_PERS			= 0x11	  # 2 consecutive prox or ALS for int.
			self.DEFAULT_CONFIG2		= 0x01	  # No saturation interrupts or LED boost  
			self.DEFAULT_CONFIG3		= 0		  # Enable all photodiodes, no SAI
			self.DEFAULT_GPENTH			= 40	  # Threshold for entering gesture mode
			self.DEFAULT_GEXTH			= 30	  # Threshold for exiting gesture mode	  
			self.DEFAULT_GCONF1			= 0b01000000 #0x40	  # 4 gesture events for int., 1 for exit
			self.DEFAULT_GGAIN			= 0
			self.DEFAULT_GLDRIVE		= 0
			self.DEFAULT_GWTIME			= self.GWTIME_0MS	  
			self.DEFAULT_GOFFSET		= 0		  # No offset scaling for gesture mode
			self.DEFAULT_GPULSE			= 0xC0	  # 32us
			self.DEFAULT_GPULSE		   |= 10	  # 10 pulses
			self.DEFAULT_GCONF3			= 0		  # All photodiodes active during gesture
			self.DEFAULT_GIEN			= 1		  # Disable gesture interrupts
			self.GESTURE_CLEAR			= 0b00000100	# 



			##/* Container for gesture data */
			self.NDataPoints=32



			#* @brief Configures I2C communications and initializes registers to defaults
			#*
			#* @return True if initialized successfully. False otherwise.
		def init(self):



			#/* Initialize I2C */
			"""Opens the I2C bus, verifies the chip ID matches a known APDS9960 ID, then writes all default ambient-light, proximity, and gesture configuration values to the device registers; returns False if any step fails.

			Inputs:
			    None.
			Outputs:
			    bool: True on successful initialization, False on any I2C/ID failure
			"""
			self.BUS = smbus.SMBus(1)

			#/* Read ID register and check against known values for APDS-9960 */
			retCode, idd = self.ReadDataByte(self.APDS9960_ID)
			if not retCode:																	 return False

			if( not( idd == self.APDS9960_ID_1 or idd == self.APDS9960_ID_2) ):				 return False

			#/* Set ENABLE register to 0 (disable all features) */
			if( not self.setMode(self.ALL, self.OFF) ):										 return False

			#/* Set default values for ambient light and proximity registers */
			if( not self.WriteDataByte(self.APDS9960_ATIME, self.DEFAULT_ATIME) ):			 return False
			if( not self.WriteDataByte(self.APDS9960_WTIME, self.DEFAULT_WTIME) ):			 return False
			if( not self.WriteDataByte(self.APDS9960_PPULSE, self.DEFAULT_PROX_PPULSE) ):	 return False
			if( not self.WriteDataByte(self.APDS9960_POFFSET_UR, self.DEFAULT_POFFSET_UR) ): return False
			if( not self.WriteDataByte(self.APDS9960_POFFSET_DL, self.DEFAULT_POFFSET_DL) ): return False
			if( not self.WriteDataByte(self.APDS9960_CONFIG1, self.DEFAULT_CONFIG1) ):		 return False
			if( not self.setLEDDrive(self.DEFAULT_LDRIVE) ):								 return False
			if( not self.setProximityGain(self.DEFAULT_PGAIN) ):							 return False
			if( not self.setAmbientLightGain(self.DEFAULT_AGAIN) ):							 return False
			if( not self.setProxIntLowThresh(self.DEFAULT_PILT) ):							 return False
			if( not self.setProxIntHighThresh(self.DEFAULT_PIHT) ):							 return False
			if( not self.setLightIntLowThreshold(self.DEFAULT_AILT) ):						 return False
			if( not self.setLightIntHighThreshold(self.DEFAULT_AIHT) ):						 return False
			if( not self.WriteDataByte(self.APDS9960_PERS, self.DEFAULT_PERS) ):			 return False
			if( not self.WriteDataByte(self.APDS9960_CONFIG2, self.DEFAULT_CONFIG2) ):		 return False
			if( not self.WriteDataByte(self.APDS9960_CONFIG3, self.DEFAULT_CONFIG3) ):		 return False

			#/* Set default values for gesture sense registers */
			if( not self.setGestureEnterThresh(self.DEFAULT_GPENTH) ):						 return False
			if( not self.setGestureExitThresh(self.DEFAULT_GEXTH) ):						 return False
			if( not self.WriteDataByte(self.APDS9960_GCONF1, self.DEFAULT_GCONF1) ):		 return False
			if( not self.setGestureGain(self.DEFAULT_GGAIN) ):								 return False
			if( not self.setGestureLEDDrive(self.DEFAULT_GLDRIVE) ):						 return False
			if( not self.setGestureWaitTime(self.DEFAULT_GWTIME) ):							 return False
			if( not self.WriteDataByte(self.APDS9960_GOFFSET_U, self.DEFAULT_GOFFSET) ):	 return False
			if( not self.WriteDataByte(self.APDS9960_GOFFSET_D, self.DEFAULT_GOFFSET) ):	 return False
			if( not self.WriteDataByte(self.APDS9960_GOFFSET_L, self.DEFAULT_GOFFSET) ):	 return False
			if( not self.WriteDataByte(self.APDS9960_GOFFSET_R, self.DEFAULT_GOFFSET) ):	 return False
			if( not self.WriteDataByte(self.APDS9960_GPULSE, self.DEFAULT_GPULSE) ):		 return False
			if( not self.WriteDataByte(self.APDS9960_GCONF3, self.DEFAULT_GCONF3) ):		 return False
			if( not self.setGestureIntEnable(self.DEFAULT_GIEN) ):							 return False

			return True
	

		#/*******************************************************************************
		#* Public methods for controlling the APDS-9960
		#******************************************************************************/

		""" 
		* @brief Reads and returns the contents of the ENABLE register
		*
		* @return Contents of the ENABLE register. 0xFF if error.
		""" 
		def getMode(self): 
			#/* Read current ENABLE register */
			"""Reads the APDS9960 ENABLE register and returns its value, returning the ERROR code (0xFF) if the read fails.

			Inputs:
			    None.
			Outputs:
			    int: ENABLE register value, or self.ERROR (0xFF) on read failure
			"""
			retCode,val = self.ReadDataByte(self.APDS9960_ENABLE) 
			if not retCode :return self.ERROR
			return val

		""" 
		* @brief Enables or disables a feature in the APDS-9960
		*
		* @param[in] mode which feature to enable
		* @param[in] enable ON (1) or OFF (0)
		* @return True if operation success. False otherwise.
		""" 
		def setMode(self, mode,	 enable):
			"""Modifies the APDS9960 ENABLE register to turn a given feature mode on or off; for individual modes 0-6 it sets/clears the corresponding bit, while ALL sets the register to 0x7F or 0x00, then writes the result back.

			Inputs:
			    mode (int): feature mode index (0-6) or ALL constant
			    enable (int): 1 to enable, 0 to disable the mode
			Outputs:
			    bool: True on success, False on read/write failure
			"""
			reg_val = self.getMode()
			if( reg_val == self.ERROR ): return False
	
			#/* Change bit(s) in ENABLE register */
			enable = enable & 0x01
			if( mode >= 0  and	mode <= 6 ): 
				if (enable):
					reg_val |= (1 << mode)
				else:
					reg_val &= ~(1 << mode)
				
			elif( mode == self.ALL ):
				if (enable):
					reg_val = 0x7F
				else:
					reg_val = 0x00
	
			#/* Write value back to ENABLE register */
			if( not self.WriteDataByte(self.APDS9960_ENABLE, reg_val) ): return False
	
			return True
		

		""" 
		* @brief Starts the light (R/G/B/Ambient) sensor on the APDS-9960
		*
		* @param[in] interrupts true to enable hardware interrupt on high or low light
		* @return True if sensor enabled correctly. False on error.
		""" 
		def enableLightSensor(self, interrupts):
			#/* Set default gain, interrupts, enable power, and enable sensor */
			"""Starts the ambient light sensor on the APDS-9960 by setting the default ALS gain, optionally enabling the light interrupt, powering on the chip, and enabling the ambient light mode.

			Inputs:
			    interrupts (bool): True to enable the hardware ambient-light interrupt, False to disable it
			Outputs:
			    bool: True if the sensor was enabled correctly, False on any configuration failure
			"""
			if( not self.setAmbientLightGain(self.DEFAULT_AGAIN) ): 
				return False
			if( interrupts ):
				if( not self.setAmbientLightIntEnable(1) ):
					return False
			else:
				if( not self.setAmbientLightIntEnable(0) ):
					return False
			if( not self.enablePower() ): return False
			if( not self.setMode(self.AMBIENT_LIGHT, 1) ): return False
	
			return True


		""" 
		* @brief Ends the light sensor on the APDS-9960
		*
		* @return True if sensor disabled correctly. False on error.
		""" 
		def disableLightSensor(self):
			"""Stops the ambient light sensor on the APDS-9960 by disabling its interrupt and turning off the ambient light mode.

			Inputs:
			    None.
			Outputs:
			    bool: True if the sensor was disabled correctly, False on any failure
			"""
			if( not self.setAmbientLightIntEnable(0) ):		return False
			if( not self.setMode(self.AMBIENT_LIGHT, 0) ):	return False
	
			return True
		

		""" 
		* @brief Starts the proximity sensor on the APDS-9960
		*
		* @param[in] interrupts true to enable hardware external interrupt on proximity
		* @return True if sensor enabled correctly. False on error.
		""" 
		def enableProximitySensor(self, interrupts):
			#/* Set default gain, LED, interrupts, enable power, and enable sensor */
			"""Starts the proximity sensor on the APDS-9960 by setting the default proximity gain and LED drive, optionally enabling the proximity interrupt, powering on the chip, and enabling proximity mode.

			Inputs:
			    interrupts (bool): True to enable the hardware proximity interrupt, False to disable it
			Outputs:
			    bool: True if the sensor was enabled correctly, False on any configuration failure
			"""
			if( not self.setProximityGain(self.DEFAULT_PGAIN) ): return False
			if( not self.setLEDDrive(self.DEFAULT_LDRIVE) ):	 return False
			if( interrupts ):
				if( not self.setProximityIntEnable(1) ):
					return False
				
			else:
				if( not self.setProximityIntEnable(0) ):
					return False
				
			
			if( not self.enablePower() ): return False
			if( not self.setMode(self.PROXIMITY, 1) ): return False
	
			return True
		
		def disableProximitySensor(self):
			"""Placeholder/stub for disabling the proximity sensor; currently performs no action and returns immediately.

			Inputs:
			    None.
			Outputs:
			    None: Returns None; no operation performed
			"""
			return

		""" 
		* @brief Starts the gesture recognition engine on the APDS-9960
		*
		* @param[in] interrupts true to enable hardware external interrupt on gesture
		* @return True if engine enabled correctly. False on error.
		""" 
		def enableGestureSensor(self, interrupts):
			#/* Enable gesture mode
			#Set ENABLE to 0 (power off)
			#Set WTIME to 0xFF
			#Set AUX to LED_BOOST_300
			#Enable PON, WEN, PEN, GEN in ENABLE 
			"""Starts the gesture recognition engine on the APDS-9960 by resetting gesture parameters, configuring wait time, proximity pulses and LED boost, optionally enabling the gesture interrupt, then enabling gesture mode, power, wait, proximity and gesture modes.

			Inputs:
			    interrupts (bool): True to enable the hardware gesture interrupt, False to disable it
			Outputs:
			    bool: True if the gesture engine was enabled correctly, False on any configuration failure
			"""
			self.resetGestureParameters()
			if( not self.WriteDataByte(self.APDS9960_WTIME, 0xFF) ):						 return False
			if( not self.WriteDataByte(self.APDS9960_PPULSE, self.DEFAULT_GESTURE_PPULSE) ): return False
			if( not self.setLEDBoost(self.LED_BOOST_300) ):									 return False
			if( interrupts ):
				if( not self.setGestureIntEnable(1) ):
					return False
				
			else:
				if( not self.setGestureIntEnable(0) ):
					return False
				
			
			if( not self.setGestureMode(1) ): return False
			if( not self.enablePower() ): return False
			if( not self.setMode(self.WAIT, 1) ): return False
			if( not self.setMode(self.PROXIMITY, 1) ): return False
			if( not self.setMode(self.GESTURE, 1) ): return False
	
			return True
		

		""" 
		* @brief Ends the gesture recognition engine on the APDS-9960
		*
		* @return True if engine disabled correctly. False on error.
		""" 
		def disableGestureSensor(self):
			"""Stops the gesture recognition engine on the APDS-9960 by resetting gesture parameters, disabling the gesture interrupt, and turning off gesture mode.

			Inputs:
			    None.
			Outputs:
			    bool: True if the gesture engine was disabled correctly, False on any failure
			"""
			self.resetGestureParameters()
			if( not self.setGestureIntEnable(0) ): return False
			if( not self.setGestureMode(0) ):	   return False
			if( not self.setMode(self.GESTURE, 0) ):	return False
	
			return True
		""" 
		* @brief reset the gesture fifi data on the APDS
		*
		* @return True if ok
		""" 
		def clearGestureFIFO(self):
			"""Clears the gesture FIFO data on the APDS-9960 by writing the FIFO-clear bits to the GCONF4 register.

			Inputs:
			    None.
			Outputs:
			    bool: True if the FIFO was cleared successfully, False on read/write error or exception
			"""
			try:
				retCode,val = self.ReadDataByte(self.APDS9960_GCONF4)
				if( not retCode): return False
			
				out = 0b00000111
				#print	"gesture bits:", val, out 
				if( not self.WriteDataByte( self.APDS9960_GCONF4,out) ): return False
				return True
			except Exception as e:
				U.logger.log(30,"", exc_info=True)
				return False

		""" 
		* @brief Determines if there is a gesture available for reading
		*
		* @return True if gesture available. False otherwise.
		""" 
		def isGestureAvailable(self):
			#/* Read value from GSTATUS register */
			"""Determines whether a gesture is available to read by reading the GSTATUS register and checking the GVALID bit.

			Inputs:
			    None.
			Outputs:
			    bool or int: True if a valid gesture is available, False otherwise, or self.ERROR if the register read fails
			"""
			retCode,val = self.ReadDataByte(self.APDS9960_GSTATUS)
			if not retCode: return self.ERROR
			
	
			#/* Shift and mask out GVALID bit */
			val &= self.APDS9960_GVALID
	
			#/* Return true/False based on GVALID bit */
			if( val == 1): return True
			else: return False
		

		""" 
		* @brief Processes a gesture event and returns best guessed gesture
		*
		* @return Number corresponding to gesture. -1 on error.
		""" 
		def readGesture(self):
			"""Reads and processes a gesture event from the APDS-9960 by checking validity, reading the gesture FIFO into up/down/left/right data arrays, and decoding them into a best-guess gesture via processGestureData.

			Inputs:
			    None.
			Outputs:
			    tuple: A 4-tuple (motion str, nearFar str, UPdown int, LEFTright int) describing the detected gesture; motion may be 'NONE'/'' or self.ERROR on failure
			"""
			motion	  = ""
			nearFar	  = ""
			UPdown	  = 0
			LEFTright = 0 
			try:
	
				#/* Make sure that power and gesture is on and data is valid */
				if( not self.isGestureAvailable() or not( self.getMode() & 0b01000001) ):
					return	"NONE", nearFar,UPdown,LEFTright

				fifoBytes = 0
				bytesRead = 0
				fifoData  =[0 for ii in range(128)]
	
				#/* Keep looping as long as gesture data is valid */
				maxLoop = 3
				motion	= ""
				#print "in read gesture " 
				#/* Wait some time to collect next batch of FIFO data */
		
				#/* Get the contents of the STATUS register. Is data still valid? */
				retCode, gstatus  =self.ReadDataByte(self.APDS9960_GSTATUS) 
				if not retCode: return self.ERROR, nearFar,UPdown,LEFTright
				
		
				#/* If we have valid data, read in FIFO */
				if( (gstatus & self.APDS9960_GVALID) == self.APDS9960_GVALID ):		   
					#print "in read gesture	 valid " , gstatus

					#/* Read the current FIFO level */
					retCode, fifoBytes	=self.ReadDataByte(self.APDS9960_GFLVL) 
					if not retCode: return self.ERROR, nearFar,UPdown,LEFTright

					#/* If there's stuff in the FIFO, read it into our data block */
					if( fifoBytes > 0):
						bytesRead, fifoData = self.ReadDataBlock(self.APDS9960_GFIFO_U, fifoBytes * 4 )
						if( bytesRead == -1 ): return self.ERROR, nearFar,UPdown,LEFTright
						
						bytesRead = min(bytesRead, fifoBytes, self.NDataPoints*4)
						#/* If at least 1 set of data, sort the data into U/D/L/R */
						#print "fifio", fifoBytes /4
						upD	   = []
						downD  = []
						leftD  = []
						rightD = []
						nrec = 0
						if( bytesRead >= 4 ):
							for	 jj	 in range(bytesRead/4) :
								i=jj*4
								upD.append(fifoData[i + 0])
								downD.append(fifoData[i + 1])
								leftD.append(fifoData[i + 2])
								rightD.append(fifoData[i + 3])
								nrec +=1

							motion, nearFar,UPdown,LEFTright= self.processGestureData(upD,downD,leftD,rightD,nrec)
							U.logger.log(10,"======== MOTION :"+ motion+ "; nearFar :"+ nearFar," ======")
					return motion, nearFar,UPdown,LEFTright
				else:
					#/* Determine best guessed gesture and clean up */
					time.sleep(self.FIFO_PAUSE_TIME)
					return motion, nearFar,UPdown,LEFTright
			except Exception as e:
				U.logger.log(30,"", exc_info=True)
			return motion, nearFar,UPdown,LEFTright
			

		""" 
		* Turn the APDS-9960 on
		*
		* @return True if operation successful. False otherwise.
		""" 
		def enablePower(self):
			"""Turns the APDS-9960 on by setting the POWER mode bit.

			Inputs:
			    None.
			Outputs:
			    bool: True if power was enabled successfully, False on failure
			"""
			if( not self.setMode(self.POWER, 1) ): return False
	
			return True
		

		""" 
		* Turn the APDS-9960 off
		*
		* @return True if operation successful. False otherwise.
		""" 
		def disablePower(self):
			"""Turns the APDS-9960 off by clearing the POWER mode bit.

			Inputs:
			    None.
			Outputs:
			    bool: True if power was disabled successfully, False on failure
			"""
			if( not self.setMode(self.POWER, 0) ): return False
	
			return True
		

		#/*******************************************************************************
		#* Ambient light and color sensor controls
		#******************************************************************************/

		""" 
		* @brief Reads the ambient (clear) light level as a 16-bit value
		*
		* @param[out] val value of the light sensor.
		* @return True if operation successful. False otherwise.
		""" 
		def readAmbientLight(self):
			"""Reads the ambient (clear) light level from the APDS-9960 as a 16-bit value by reading the clear-channel low and high byte registers and combining them.

			Inputs:
			    None.
			Outputs:
			    int: The combined 16-bit ambient light value, or -1 if either register read fails
			"""
			val = 0
	
			#/* Read value from clear channel, low byte register */
			retCode,val = self.ReadDataByte(self.APDS9960_CDATAL)
			if not retCode: return -1
	
			#/* Read value from clear channel, high byte register */
			retCode,val2 = self.ReadDataByte(self.APDS9960_CDATAH)
			if not retCode:return -1
			val = val + (val2 << 8)
			#print "readAmbientLight",val,hex(val),val2,hex(val2)
			return val
		

		""" 
		* @brief Reads the red light level as a 16-bit value
		*
		* @param[out] val value of the light sensor.
		* @return True if operation successful. False otherwise.
		""" 
		def readRedLight(self):
			"""Reads the red light/clear-channel level from the APDS9960 by reading the low and high byte data registers over I2C and combining them into a 16-bit value.

			Inputs:
			    None.
			Outputs:
			    int: 16-bit red light value, or -1 if an I2C read fails
			"""
			val = 0
	
			#/* Read value from clear channel, low byte register */
			retCode,val = self.ReadDataByte(self.APDS9960_RDATAL)
			if not retCode	: return -1
			val1 = val
	
			#/* Read value from clear channel, high byte register */
			retCode,val2 = self.ReadDataByte(self.APDS9960_RDATAH) 
			if not retCode: return -1
			val = val + (val2 << 8)
	
			return val
		

		""" 
		* @brief Reads the green light level as a 16-bit value
		*
		* @param[out] val value of the light sensor.
		* @return True if operation successful. False otherwise.
		""" 
		def readGreenLight(self):
			"""Reads the green light level from the APDS9960 by reading the low and high green data byte registers over I2C and combining them into a 16-bit value.

			Inputs:
			    None.
			Outputs:
			    int: 16-bit green light value, or -1 if an I2C read fails
			"""
			val = 0
	
			#/* Read value from clear channel, low byte register */
			retCode,val1 = self.ReadDataByte(self.APDS9960_GDATAL) 
			if not retCode: return -1
	
			#/* Read value from clear channel, high byte register */
			retCode, val = self.ReadDataByte(self.APDS9960_GDATAH)
			if not retCode: return -1
			val = val1 + (val << 8)
	
			return val
		

		""" 
		* @brief Reads the red light level as a 16-bit value
		*
		* @param[out] val value of the light sensor.
		* @return True if operation successful. False otherwise.
		""" 
		def readBlueLight(self):
			"""Reads the blue light level from the APDS9960 by reading the low and high blue data byte registers over I2C and combining them into a 16-bit value.

			Inputs:
			    None.
			Outputs:
			    int: 16-bit blue light value, or -1 if an I2C read fails
			"""
			val = 0
	
			#/* Read value from clear channel, low byte register */
			retCode,val1 = self.ReadDataByte(self.APDS9960_BDATAL)
			if not retCode: return -1
	
			#/* Read value from clear channel, high byte register */
			retCode,val = self.ReadDataByte(self.APDS9960_BDATAH)
			if not retCode: return -1
			val = val1 + (val << 8)
	
			return	val
		

		#/*******************************************************************************
		#* Proximity sensor controls
		#******************************************************************************/

		""" 
		* @brief Reads the proximity level as an 8-bit value
		*
		* @param[out] val value of the proximity sensor.
		* @return True if operation successful. False otherwise.
		""" 
		def readProximity(self):
			"""Reads the 8-bit proximity value from the APDS9960 proximity data register and returns it inverted (255 minus the raw reading) so larger values mean closer.

			Inputs:
			    None.
			Outputs:
			    int: Inverted proximity value (255-raw), or -1 if the read fails
			"""
			val = -1
			#/* Read value from proximity data register */
			retCode,val = self.ReadDataByte(self.APDS9960_PDATA)
			if not retCode: return -1
			return 255-val
		

		#/*******************************************************************************
		#* High-level gesture controls
		#******************************************************************************/

		""" 
		* @brief Resets all the parameters in the gesture data member
		""" 
		def resetGestureParameters(self):
			"""Placeholder/no-op intended to reset the gesture data members; the body simply returns without doing anything.

			Inputs:
			    None.
			Outputs:
			    None: No effect; returns immediately
			"""
			return		  

		""" 
		* @brief Processes the raw gesture data to determine swipe direction
		*
		* @return True if near or far state seen. False otherwise.
		""" 
		def processGestureData(self,upD,downD,leftD,rightD,nrec):
			
			"""Analyzes accumulated raw up/down/left/right gesture sample arrays to determine swipe direction and near/far state, computing left-right and up-down deltas and sums, logging diagnostics, and classifying the motion.

			Inputs:
			    upD (list): Sequence of up-detector samples
			    downD (list): Sequence of down-detector samples
			    leftD (list): Sequence of left-detector samples
			    rightD (list): Sequence of right-detector samples
			    nrec (int): Number of gesture records/samples collected
			Outputs:
			    tuple: (motion, nearFAR, udDel, lrDel): direction string, near/far string, and up-down and left-right delta totals
			"""
			motion	= "NONE"
			nearFAR = "NONE"
			try:
				lrDelta = [0 for ii in range(32)]
				lrSum	= [0 for ii in range(32)]
				udDelta = [0 for ii in range(32)]
				udSum	= [0 for ii in range(32)]
				lrTot = 0
				udTot = 0
				lrDel = 0 
				udDel = 0
				iStart	= 0
				#print "number of gestures:", nrec
				#/* If we have less than 4 total gestures, that's not enough */
				if( nrec <= 3  or nrec > 32 or len(leftD)< 3): return motion ,nearFAR, udDel, lrDel 
	
				d1 = 0
				d1 += leftD[0]	- leftD[1] 
				d1 += rightD[0] - rightD[1] 
				d1 += upD[0]	- upD[1] 
				d1 += downD[0]	- downD[1] 
				if d1 > 200 : iStart= 1
				else:		  iStart= 0

				for i in range(iStart,nrec):
					lrDelta[i] = leftD[i] - rightD[i]
					lrSum[i]   = leftD[i] + rightD[i]
					udDelta[i] = upD[i]	  - downD[i]
					udSum[i]   = upD[i]	  + downD[i]
					lrTot += lrSum[i]
					udTot += udSum[i]
					lrDel += lrDelta[i]
					udDel += udDelta[i]
				
				try:
					self.count+=1
				except:
					self.count =0
				U.logger.log(10,	"count:" +str(self.count))
				U.logger.log(10,	"d1" +str(d1)+ ";  iStart:" +str(iStart)+";	 lrTot:"+str(lrTot)+";	lrDel:"+str(lrDel)+";  udDel:"+str(udDel)+";  udTot:"+str(udTot))
				self.doPRINT("lrDelta:", lrDelta, nrec)
				self.doPRINT("lrSum	 :", lrSum,	  nrec)
				self.doPRINT("udDelta:", udDelta, nrec)
				self.doPRINT("udSum	 :", udSum,	  nrec)

				direction  = abs(udDel) - abs(lrDel)
			
				if	 direction > +10:  # vertical
					if	 udDel	 >	30: motion = "DOWN" 
					elif udDel	 < -30: motion = "UP" 
					else:				motion = "VERTICAL"
				elif direction < -10: # horizontal
					if	 lrDel	 >	30: motion = "LEFT" 
					elif lrDel	 < -30: motion = "RIGHT" 
					else:				motion = "HORIZONTAL"
				else:					motion = "MOVEMENT" # dont know direction
			
			
				if	  lrTot + udTot > 400* (nrec-iStart) : nearFAR = "NEAR"
				elif  lrTot + udTot < 120*	(nrec-iStart): nearFAR = "FAR"
				else									 : nearFAR = "MIDDLE"

				U.logger.log(10,	"motion:"+ motion +";  nearFAR:"+nearFAR)  
			except Exception as e:
					U.logger.log(30,"", exc_info=True)
					U.logger.log(30, "leftD:{}".format(leftD))
			return motion ,nearFAR, udDel, lrDel	   

		def doPRINT(self,label,theList,nrec):
			"""Formats a labeled, right-justified row of the first nrec values from a list and writes it to the logger at debug level for gesture-data diagnostics.

			Inputs:
			    label (str): Prefix label for the logged line
			    theList (list): List of numeric values to print
			    nrec (int): Number of leading elements to include
			Outputs:
			    None: Writes a formatted line to the logger
			"""
			out = label
			for ii in range(nrec):
				out += str(theList[ii]).rjust(4)
			U.logger.log(10,	out)


		#/*******************************************************************************
		#* Getters and setters for register values
		#******************************************************************************/

		""" 
		* @brief Returns the lower threshold for proximity detection
		*
		* @return lower threshold
		""" 
		def getProxIntLowThresh(self):
	
			#/* Read value from PILT register */
			"""Reads the lower proximity-interrupt threshold from the APDS9960 PILT register over I2C.

			Inputs:
			    None.
			Outputs:
			    tuple: (True, value) on success or (False, 0) if the read fails
			"""
			retCode,val = self.ReadDataByte(self.APDS9960_PILT)
			if not retCode: return False,0
	
			return True, val
		

		""" 
		* @brief Sets the lower threshold for proximity detection
		*
		* @param[in] threshold the lower proximity threshold
		* @return True if operation successful. False otherwise.
		""" 
		def setProxIntLowThresh(self,threshold):
			"""Writes the given value to the APDS9960 PILT register to set the lower proximity-interrupt threshold.

			Inputs:
			    threshold (int): Lower proximity threshold byte to write
			Outputs:
			    bool: True if the write succeeded, False otherwise
			"""
			if( not self.WriteDataByte(self.APDS9960_PILT, threshold) ): return False
			return True
		

		""" 
		* @brief Returns the high threshold for proximity detection
		*
		* @return high threshold
		""" 
		def getProxIntHighThresh(self):
			#/* Read value from PIHT register */
			"""Reads the high proximity-interrupt threshold from the APDS9960 PIHT register over I2C.

			Inputs:
			    None.
			Outputs:
			    int or tuple: Threshold value on success, or (False, 0) if the read fails
			"""
			retCode,val = self.ReadDataByte(self.APDS9960_PIHT)
			if not retCode: return False,0
			return val
		

		""" 
		* @brief Sets the high threshold for proximity detection
		*
		* @param[in] threshold the high proximity threshold
		* @return True if operation successful. False otherwise.
		""" 
		def setProxIntHighThresh(self, threshold):
			"""Writes the given value to the APDS9960 PIHT register to set the high proximity-interrupt threshold.

			Inputs:
			    threshold (int): High proximity threshold byte to write
			Outputs:
			    bool: True if the write succeeded, False otherwise
			"""
			if( not self.WriteDataByte(self.APDS9960_PIHT, threshold) ): return False
			return True
		

		""" 
		* @brief Returns LED drive strength for proximity and ALS
		*
		* Value	   LED Current
		*	0		 100 mA
		*	1		  50 mA
		*	2		  25 mA
		*	3		  12.5 mA
		*
		* @return the value of the LED drive strength. 0xFF on failure.
		""" 
		def getLEDDrive(self):
			#/* Read value from CONTROL register */
			"""Reads the APDS9960 CONTROL register and extracts the 2-bit LED drive strength setting (bits 6-7) for proximity and ALS.

			Inputs:
			    None.
			Outputs:
			    int: LED drive strength code 0-3, or self.ERROR if the read fails
			"""
			retCode,val = self.ReadDataByte(self.APDS9960_CONTROL)
			if not retCode: return self.ERROR
	
			#/* Shift and mask out LED drive bits */
			val = (val >> 6) & 0b00000011
	
			return val
		

		""" 
		* @brief Sets the LED drive strength for proximity and ALS
		*
		* Value	   LED Current
		*	0		 100 mA
		*	1		  50 mA
		*	2		  25 mA
		*	3		  12.5 mA
		*
		* @param[in] drive the value (0-3) for the LED drive strength
		* @return True if operation successful. False otherwise.
		""" 
		def setLEDDrive(self, drive):
			#/* Read value from CONTROL register */
			"""Sets the LED drive strength in the APDS9960 CONTROL register by reading the current value, masking the 2-bit drive field into bits 6-7, and writing it back.

			Inputs:
			    drive (int): 2-bit LED drive value (0-3)
			Outputs:
			    bool: True on successful I2C write, False on read/write failure
			"""
			retCode,val = self.ReadDataByte(self.APDS9960_CONTROL)
			if not retCode: return False

			#/* Set bits in register to given value */
			drive &= 0b00000011
			drive = drive << 6
			val &= 0b00111111
			val |= drive
	
			#/* Write register value back into CONTROL register */
			if( not self.WriteDataByte(self.APDS9960_CONTROL, val) ): return False
	
			return True
		

		""" 
		* @brief Returns receiver gain for proximity detection
		*
		* Value	   Gain
		*	0		1x
		*	1		2x
		*	2		4x
		*	3		8x
		*
		* @return the value of the proximity gain. 0xFF on failure.
		""" 
		def getProximityGain(self):
			#/* Read value from CONTROL register */
			"""Reads the CONTROL register and extracts the 2-bit proximity receiver gain field (bits 2-3) of the APDS9960.

			Inputs:
			    None.
			Outputs:
			    int: Proximity gain value (0-3), or self.ERROR on read failure
			"""
			retCode,val = self.ReadDataByte(self.APDS9960_CONTROL)
			if not retCode: return self.ERROR
	
			#/* Shift and mask out PDRIVE bits */
			val = (val >> 2) & 0b00000011
	
			return	val
		

		""" 
		* @brief Sets the receiver gain for proximity detection
		*
		* Value	   Gain
		*	0		1x
		*	1		2x
		*	2		4x
		*	3		8x
		*
		* @param[in] drive the value (0-3) for the gain
		* @return True if operation successful. False otherwise.
		""" 
		def setProximityGain(self, drive):
			#/* Read value from CONTROL register */
			"""Sets the proximity receiver gain by reading the CONTROL register, masking the 2-bit gain value into bits 2-3, and writing it back.

			Inputs:
			    drive (int): 2-bit proximity gain value (0-3)
			Outputs:
			    bool: True on successful I2C write, False on read/write failure
			"""
			retCode,val = self.ReadDataByte(self.APDS9960_CONTROL)
			if not retCode: return False
	
			#/* Set bits in register to given value */
			drive &= 0b00000011
			drive = drive << 2
			val &= 0b11110011
			val |= drive
	
			#/* Write register value back into CONTROL register */
			if( not self.WriteDataByte(self.APDS9960_CONTROL, val) ): return False
	
			return True
		

		""" 
		* @brief Returns receiver gain for the ambient light sensor (ALS)
		*
		* Value	   Gain
		*	0		 1x
		*	1		 4x
		*	2		16x
		*	3		64x
		*
		* @return the value of the ALS gain. 0xFF on failure.
		""" 
		def getAmbientLightGain(self):
			#/* Read value from CONTROL register */
			"""Reads the CONTROL register and extracts the 2-bit ambient light sensor (ALS) gain field (bits 0-1) of the APDS9960.

			Inputs:
			    None.
			Outputs:
			    int: ALS gain value (0-3), or self.ERROR on read failure
			"""
			retCode,val = self.ReadDataByte(self.APDS9960_CONTROL)
			if not retCode: return self.ERROR
			#/* Shift and mask out ADRIVE bits */
			val &= 0b00000011
	
			return val
		

		""" 
		* @brief Sets the receiver gain for the ambient light sensor (ALS)
		*
		* Value	   Gain
		*	0		 1x
		*	1		 4x
		*	2		16x
		*	3		64x
		*
		* @param[in] drive the value (0-3) for the gain
		* @return True if operation successful. False otherwise.
		""" 
		def setAmbientLightGain(self, drive):
			#/* Read value from CONTROL register */
			"""Sets the ambient light sensor (ALS) receiver gain by reading the CONTROL register, masking the 2-bit value into bits 0-1, and writing it back.

			Inputs:
			    drive (int): 2-bit ALS gain value (0-3)
			Outputs:
			    bool: True on successful I2C write, False on read/write failure
			"""
			retCode,val = self.ReadDataByte(self.APDS9960_CONTROL)
			if not retCode: return False
	
			#/* Set bits in register to given value */
			drive &= 0b00000011
			val &= 0b11111100
			val |= drive
	
			#/* Write register value back into CONTROL register */
			if( not self.WriteDataByte(self.APDS9960_CONTROL, val) ): return False
	
			return True
		

		""" 
		* @brief Get the current LED boost value
		* 
		* Value	 Boost Current
		*	0		 100%
		*	1		 150%
		*	2		 200%
		*	3		 300%
		*
		* @return The LED boost value. 0xFF on failure.
		""" 
		def getLEDBoost(self):
			#/* Read value from CONFIG2 register */
			"""Reads the CONFIG2 register and extracts the 2-bit LED boost current field (bits 4-5) of the APDS9960.

			Inputs:
			    None.
			Outputs:
			    int: LED boost value (0-3 mapping to 100-300%), or self.ERROR on read failure
			"""
			retCode,val = self.ReadDataByte(self.APDS9960_CONFIG2)
			if not retCode: return self.ERROR
			#/* Shift and mask out LED_BOOST bits */
			val = (val >> 4) & 0b00000011
	
			return val
		

		""" 
		* @brief Sets the LED current boost value
		*
		* Value	 Boost Current
		*	0		 100%
		*	1		 150%
		*	2		 200%
		*	3		 300%
		*
		* @param[in] drive the value (0-3) for current boost (100-300%)
		* @return True if operation successful. False otherwise.
		""" 
		def setLEDBoost(self, boost):
			#/* Read value from CONFIG2 register */
			"""Sets the LED current boost level by reading the CONFIG2 register, masking the 2-bit boost value into bits 4-5, and writing it back.

			Inputs:
			    boost (int): 2-bit LED boost value (0-3 for 100-300%)
			Outputs:
			    bool: True on successful I2C write, False on read/write failure
			"""
			retCode,val = self.ReadDataByte(self.APDS9960_CONFIG2)
			if not retCode: return False
	
			#/* Set bits in register to given value */
			boost &= 0b00000011
			boost = boost << 4
			val &= 0b11001111
			val |= boost
	
			#/* Write register value back into CONFIG2 register */
			if( not self.WriteDataByte(self.APDS9960_CONFIG2,val)): return False
	
			return True
		   

		""" 
		* @brief Gets proximity gain compensation enable
		*
		* @return 1 if compensation is enabled. 0 if not. 0xFF on error.
		""" 
		def getProxGainCompEnable(self):
			#/* Read value from CONFIG3 register */
			"""Reads the CONFIG3 register and extracts the proximity gain compensation enable bit (bit 5) of the APDS9960.

			Inputs:
			    None.
			Outputs:
			    int: 1 if compensation enabled, 0 if disabled, or self.ERROR on read failure
			"""
			retCode,val = self.ReadDataByte(self.APDS9960_CONFIG3)
			if not retCode: return self.ERROR
	
			#/* Shift and mask out PCMP bits */
			val = (val >> 5) & 0b00000001
	
			return val
		

		""" 
		* @brief Sets the proximity gain compensation enable
		*
		* @param[in] enable 1 to enable compensation. 0 to disable compensation.
		* @return True if operation successful. False otherwise.
		""" 
		def setProxGainCompEnable(self, enable):
			#/* Read value from CONFIG3 register */
			"""Sets the proximity gain compensation enable bit by reading the CONFIG3 register, masking the single-bit value into bit 5, and writing it back.

			Inputs:
			    enable (int): 1 to enable, 0 to disable compensation
			Outputs:
			    bool: True on successful I2C write, False on read/write failure
			"""
			retCode,val = self.ReadDataByte(self.APDS9960_CONFIG3)
			if not retCode: return False
	
			#/* Set bits in register to given value */
			enable &= 0b00000001
			enable = enable << 5
			val &= 0b11011111
			val |= enable
	
			#/* Write register value back into CONFIG3 register */
			if( not self.WriteDataByte(self.APDS9960_CONFIG3, val) ): return False
	
			return True
		

		""" 
		* @brief Gets the current mask for enabled/disabled proximity photodiodes
		*
		* 1 = disabled, 0 = enabled
		* Bit	 Photodiode
		*  3	   UP
		*  2	   DOWN
		*  1	   LEFT
		*  0	   RIGHT
		*
		* @return Current proximity mask for photodiodes. 0xFF on error.
		""" 
		def getProxPhotoMask(self):
			#/* Read value from CONFIG3 register */
			"""Reads the CONFIG3 register and extracts the 4-bit proximity photodiode enable/disable mask (bits 0-3) of the APDS9960.

			Inputs:
			    None.
			Outputs:
			    int: 4-bit photodiode mask, or self.ERROR on read failure
			"""
			retCode,val = self.ReadDataByte(self.APDS9960_CONFIG3)
			if not retCode:
				return	self.ERROR
	
			#/* Mask out photodiode enable mask bits */
			val &= 0b00001111
	
			return val
		

		""" 
		* @brief Sets the mask for enabling/disabling proximity photodiodes
		*
		* 1 = disabled, 0 = enabled
		* Bit	 Photodiode
		*  3	   UP
		*  2	   DOWN
		*  1	   LEFT
		*  0	   RIGHT
		*
		* @param[in] mask 4-bit mask value
		* @return True if operation successful. False otherwise.
		""" 
		def setProxPhotoMask(self, mask):
			#/* Read value from CONFIG3 register */
			"""Sets the proximity photodiode enable/disable mask by reading the CONFIG3 register, masking the 4-bit value into bits 0-3, and writing it back.

			Inputs:
			    mask (int): 4-bit photodiode mask (1=disabled, 0=enabled per diode)
			Outputs:
			    bool: True on successful I2C write, False on read/write failure
			"""
			retCode,val = self.ReadDataByte(self.APDS9960_CONFIG3)
			if not retCode: return False
	
			#/* Set bits in register to given value */
			mask &= 0b00001111
			val &= 0b11110000
			val |= mask
	
			#/* Write register value back into CONFIG3 register */
			if( not self.WriteDataByte(self.APDS9960_CONFIG3, val) ): return False
	
			return True
		

		""" 
		* @brief Gets the entry proximity threshold for gesture sensing
		*
		* @return Current entry proximity threshold.
		""" 
		def getGestureEnterThresh(self):
			#/* Read value from GPENTH register */
			"""Reads the GPENTH register to return the entry proximity threshold used to start gesture sensing mode on the APDS9960.

			Inputs:
			    None.
			Outputs:
			    int: Entry proximity threshold value, or 0 on read failure
			"""
			retCode,val = self.ReadDataByte(self.APDS9960_GPENTH)
			if not retCode: return 0
			return val
		

		""" 
		* @brief Sets the entry proximity threshold for gesture sensing
		*
		* @param[in] threshold proximity value needed to start gesture mode
		* @return True if operation successful. False otherwise.
		""" 
		def setGestureEnterThresh(self, threshold):
			"""Writes the gesture-enter proximity threshold to the APDS-9960 GPENTH register, which is the proximity level needed to begin gesture mode.

			Inputs:
			    threshold (int): Proximity threshold byte to start gesture sensing
			Outputs:
			    bool: True if the register write succeeded, False otherwise
			"""
			if( not self.WriteDataByte(self.APDS9960_GPENTH, threshold) ): return False
			return True
		

		""" 
		* @brief Gets the exit proximity threshold for gesture sensing
		*
		* @return Current exit proximity threshold.
		""" 
		def getGestureExitThresh(self):
			#/* Read value from GEXTH register */
			"""Reads the gesture-exit proximity threshold from the APDS-9960 GEXTH register, the proximity level at which gesture mode ends.

			Inputs:
			    None.
			Outputs:
			    int: Current exit threshold value, or 0 on read failure
			"""
			retCode,val = self.ReadDataByte(self.APDS9960_GEXTH)
			if not retCode: return 0
			return val
		

		""" 
		* @brief Sets the exit proximity threshold for gesture sensing
		*
		* @param[in] threshold proximity value needed to end gesture mode
		* @return True if operation successful. False otherwise.
		""" 
		def setGestureExitThresh(self, threshold):
			"""Writes the gesture-exit proximity threshold to the APDS-9960 GEXTH register, the proximity level needed to end gesture mode.

			Inputs:
			    threshold (int): Proximity threshold byte to end gesture sensing
			Outputs:
			    bool: True if the register write succeeded, False otherwise
			"""
			if( not self.WriteDataByte(self.APDS9960_GEXTH, threshold) ): return False
			return True
		

		""" 
		* @brief Gets the gain of the photodiode during gesture mode
		*
		* Value	   Gain
		*	0		1x
		*	1		2x
		*	2		4x
		*	3		8x
		*
		* @return the current photodiode gain. 0xFF on error.
		""" 
		def getGestureGain(self):
			#/* Read value from GCONF2 register */
			"""Reads the GCONF2 register and extracts the gesture-mode photodiode gain by shifting and masking the GGAIN bits (values 0-3 for 1x-8x).

			Inputs:
			    None.
			Outputs:
			    int: Current photodiode gain (0-3), or empty string on read failure
			"""
			retCode,val = self.ReadDataByte(self.APDS9960_GCONF2)
			if not retCode: return ""
	
			#/* Shift and mask out GGAIN bits */
			val = (val >> 5) & 0b00000011
	
			return val
		

		""" 
		* @brief Sets the gain of the photodiode during gesture mode
		*
		* Value	   Gain
		*	0		1x
		*	1		2x
		*	2		4x
		*	3		8x
		*
		* @param[in] gain the value for the photodiode gain
		* @return True if operation successful. False otherwise.
		""" 
		def setGestureGain(self, gain):
			#/* Read value from GCONF2 register */
			"""Reads the GCONF2 register, replaces its GGAIN bits with the supplied gain value, and writes the modified byte back to set the gesture-mode photodiode gain.

			Inputs:
			    gain (int): Photodiode gain code (0-3) for gesture mode
			Outputs:
			    bool: True if read and write succeeded, False otherwise
			"""
			retCode,val = self.ReadDataByte(self.APDS9960_GCONF2)
			if not retCode: return False
	
			#/* Set bits in register to given value */
			gain &= 0b00000011
			gain = gain << 5
			val &= 0b10011111
			val |= gain
	
			#/* Write register value back into GCONF2 register */
			if( not self.WriteDataByte(self.APDS9960_GCONF2, val) ): return False
	
			return True
		

		""" 
		* @brief Gets the drive current of the LED during gesture mode
		*
		* Value	   LED Current
		*	0		 100 mA
		*	1		  50 mA
		*	2		  25 mA
		*	3		  12.5 mA
		*
		* @return the LED drive current value. 0xFF on error.
		""" 
		def getGestureLEDDrive(self):
			#/* Read value from GCONF2 register */
			"""Reads the GCONF2 register and extracts the gesture-mode LED drive current by shifting and masking the GLDRIVE bits (values 0-3 for 100mA-12.5mA).

			Inputs:
			    None.
			Outputs:
			    int: Current LED drive code (0-3), or self.ERROR on read failure
			"""
			retCode,val = self.ReadDataByte(self.APDS9960_GCONF2)
			if not retCode: return self.ERROR
	
			#/* Shift and mask out GLDRIVE bits */
			val = (val >> 3) & 0b00000011
	
			return val
		

		""" 
		* @brief Sets the LED drive current during gesture mode
		*
		* Value	   LED Current
		*	0		 100 mA
		*	1		  50 mA
		*	2		  25 mA
		*	3		  12.5 mA
		*
		* @param[in] drive the value for the LED drive current
		* @return True if operation successful. False otherwise.
		""" 
		def setGestureLEDDrive(self, drive):
			#/* Read value from GCONF2 register */
			"""Reads the GCONF2 register, replaces its GLDRIVE bits with the supplied drive value, and writes the byte back to set the gesture-mode LED drive current.

			Inputs:
			    drive (int): LED drive current code (0-3) for gesture mode
			Outputs:
			    bool: True if read and write succeeded, False otherwise
			"""
			retCode,val = self.ReadDataByte(self.APDS9960_GCONF2)
			if not retCode: return False
	
			#/* Set bits in register to given value */
			drive &= 0b00000011
			drive = drive << 3
			val &= 0b11100111
			val |= drive
	
			#/* Write register value back into GCONF2 register */
			if( not self.WriteDataByte(self.APDS9960_GCONF2, val) ): return False
	
			return True
		

		""" 
		* @brief Gets the time in low power mode between gesture detections
		*
		* Value	   Wait time
		*	0		   0 ms
		*	1		   2.8 ms
		*	2		   5.6 ms
		*	3		   8.4 ms
		*	4		  14.0 ms
		*	5		  22.4 ms
		*	6		  30.8 ms
		*	7		  39.2 ms
		*
		* @return the current wait time between gestures. 0xFF on error.
		""" 
		def getGestureWaitTime(self):
			#/* Read value from GCONF2 register */
			"""Reads the GCONF2 register and masks out the GWTIME bits to return the low-power wait time between gesture detections (values 0-7).

			Inputs:
			    None.
			Outputs:
			    int: Current gesture wait-time code (0-7), or self.ERROR on read failure
			"""
			retCode,val = self.ReadDataByte(self.APDS9960_GCONF2)
			if not retCode: return self.ERROR
   
			#/* Mask out GWTIME bits */
			val &= 0b00000111
	
			return val
		

		""" 
		* @brief Sets the time in low power mode between gesture detections
		*
		* Value	   Wait time
		*	0		   0 ms
		*	1		   2.8 ms
		*	2		   5.6 ms
		*	3		   8.4 ms
		*	4		  14.0 ms
		*	5		  22.4 ms
		*	6		  30.8 ms
		*	7		  39.2 ms
		*
		* @param[in] the value for the wait time
		* @return True if operation successful. False otherwise.
		""" 
		def setGestureWaitTime(self, time):
			#/* Read value from GCONF2 register */
			"""Reads the GCONF2 register, replaces its GWTIME bits with the supplied time value, and writes the byte back to set the wait time between gesture detections.

			Inputs:
			    time (int): Gesture wait-time code (0-7)
			Outputs:
			    bool or int: True if write succeeded, False on write failure, self.ERROR on read failure
			"""
			retCode,val = self.ReadDataByte(self.APDS9960_GCONF2)
			if not retCode: return self.ERROR

	
			#/* Set bits in register to given value */
			time &= 0b00000111
			val	 &= 0b11111000
			val	 |= time
	
			#/* Write register value back into GCONF2 register */
			if( not self.WriteDataByte(self.APDS9960_GCONF2, val) ): return False
	
			return True
		

		""" 
		* @brief Gets the low threshold for ambient light interrupts
		*
		* @param[out] threshold current low threshold stored on the APDS-9960
		* @return True if operation successful. False otherwise.
		""" 
		def getLightIntLowThreshold(self):
			"""Reads the low and high byte registers (AILTL/AILTH) of the ambient-light interrupt low threshold and combines them into a single 16-bit value.

			Inputs:
			    None.
			Outputs:
			    tuple: (True, threshold) on success or (False, 0) on read failure
			"""
			threshold = 0
	
			#/* Read value from ambient light low threshold, low byte register */
			retCode,val = self.ReadDataByte(self.APDS9960_AILTL)
			if not retCode: return False, 0

	
			#/* Read value from ambient light low threshold, high byte register */
			retCode,val1 = self.ReadDataByte(self.APDS9960_AILTH)
			threshold = val1 + (val << 8)
	
			return True, threshold
		

		""" 
		* @brief Sets the low threshold for ambient light interrupts
		*
		* @param[in] threshold low threshold value for interrupt to trigger
		* @return True if operation successful. False otherwise.
		""" 
		def setLightIntLowThreshold(self, threshold):
			#/* Break 16-bit threshold into 2 8-bit values */
			"""Splits the 16-bit threshold into low and high bytes and writes them to the ambient-light interrupt low threshold registers via I2C.

			Inputs:
			    threshold (int): 16-bit low threshold value for the ambient-light interrupt
			Outputs:
			    bool: True if both byte writes succeeded, False otherwise
			"""
			val_low = threshold & 0x00FF
			val_high = (threshold & 0xFF00) >> 8
	
			#/* Write low byte */
			retCode = self.WriteDataByte(self.APDS9960_AIHTL, val_low ) 
			if( not retCode ): return False
	
			#/* Write high byte */
			retCode = self.WriteDataByte(self.APDS9960_AILTH, val_high ) 
			if( not retCode ): return False
	
			return True
		

		""" 
		* @brief Gets the high threshold for ambient light interrupts
		*
		* @param[out] threshold current low threshold stored on the APDS-9960
		* @return True if operation successful. False otherwise.
		""" 
		def getLightIntHighThreshold(self):
			"""Reads the ambient-light interrupt high threshold registers and combines the two bytes into a single 16-bit value.

			Inputs:
			    None.
			Outputs:
			    tuple: (True, threshold) on success or (False, threshold) on read failure
			"""
			threshold = 0
			#/* Read value from ambient light high threshold, low byte register */
			retCode, threshold = self.ReadDataByte(self.APDS9960_AIHTL) 
			if( not retCode ): return False, threshold
	
			#/* Read value from ambient light high threshold, high byte register */
			retCode, val = self.ReadDataByte(self.APDS9960_AIHTL)
			if( not retCode ): return False, threshold
			threshold = threshold + (val << 8)
	
			return True, threshold
		

		""" 
		* @brief Sets the high threshold for ambient light interrupts
		*
		* @param[in] threshold high threshold value for interrupt to trigger
		* @return True if operation successful. False otherwise.
		""" 
		def setLightIntHighThreshold(self, threshold):
			#/* Break 16-bit threshold into 2 8-bit values */
			"""Sets the 16-bit high threshold for ambient-light (clear-channel) interrupts on the APDS-9960 by splitting it into low and high bytes and writing them to the AIHTL and AIHTH registers.

			Inputs:
			    threshold (int): 16-bit high threshold value to write
			Outputs:
			    bool: True if both register writes succeed, False otherwise
			"""
			val_low = threshold & 0x00FF
			val_high = (threshold & 0xFF00) >> 8
	
			#/* Write low byte */
			if( not self.WriteDataByte(self.APDS9960_AIHTL, val_low) ): return False
	
			#/* Write high byte */
			if( not self.WriteDataByte(self.APDS9960_AIHTH, val_high) ): return False
	
			return True
		

		""" 
		* @brief Gets the low threshold for proximity interrupts
		*
		* @param[out] threshold current low threshold stored on the APDS-9960
		* @return True if operation successful. False otherwise.
		""" 
		def getProximityIntLowThreshold(self):
			"""Reads the current proximity-interrupt low threshold from the APDS-9960 PIHT register.

			Inputs:
			    None.
			Outputs:
			    tuple: (success bool, threshold int) where success is True if the read succeeded
			"""
			val = 0
			#/* Read value from proximity low threshold register */
			retCode, val = self.ReadDataByte(self.APDS9960_PIHT )
			if( not retCode ): return False, val
	
			return True, val
		

		""" 
		* @brief Sets the low threshold for proximity interrupts
		*
		* @param[in] threshold low threshold value for interrupt to trigger
		* @return True if operation successful. False otherwise.
		""" 
		def setProximityIntLowThreshold(self, threshold):
			#/* Write threshold value to register */
			"""Writes the proximity-interrupt low threshold value to the APDS-9960 PIHT register.

			Inputs:
			    threshold (int): low threshold value for the interrupt to trigger
			Outputs:
			    bool: True if the register write succeeds, False otherwise
			"""
			retCode = self.WriteDataByte(self.APDS9960_PIHT, threshold)
			if( not retCode ): return False
	
			return True
		

		""" 
		* @brief Gets the high threshold for proximity interrupts
		*
		* @param[out] threshold current low threshold stored on the APDS-9960
		* @return True if operation successful. False otherwise.
		""" 
		def getProximityIntHighThreshold(self):
			"""Reads the current proximity-interrupt high threshold from the APDS-9960 PIHT register.

			Inputs:
			    None.
			Outputs:
			    tuple: (success bool, threshold int) where success is True if the read succeeded
			"""
			val = 0
	
			#/* Read value from proximity low threshold register */
			retCode, val = self.ReadDataByte(self.APDS9960_PIHT)
			if( not retCode ): return False, val
	
			return True, val
		

		""" 
		* @brief Sets the high threshold for proximity interrupts
		*
		* @param[in] threshold high threshold value for interrupt to trigger
		* @return True if operation successful. False otherwise.
		""" 
		def setProximityIntHighThreshold(self, threshold):
			#/* Write threshold value to register */
			"""Writes the proximity-interrupt high threshold value to the APDS-9960 PIHT register.

			Inputs:
			    threshold (int): high threshold value for the interrupt to trigger
			Outputs:
			    bool: True if the register write succeeds, False otherwise
			"""
			retCode = self.WriteDataByte(self.APDS9960_PIHT, threshold)
			if( not retCode ): return False
	
			return True
		

		""" 
		* @brief Gets if ambient light interrupts are enabled or not
		*
		* @return 1 if interrupts are enabled, 0 if not. 0xFF on error.
		""" 
		def getAmbientLightIntEnable(self):
			#/* Read value from ENABLE register */
			"""Reads the ENABLE register and extracts the AIEN bit to report whether ambient-light interrupts are currently enabled.

			Inputs:
			    None.
			Outputs:
			    int: 1 if enabled, 0 if disabled, or self.ERROR on read failure
			"""
			retCode, val = self.ReadDataByte(self.APDS9960_ENABLE) 
			if( not retCode ): return self.ERROR
	
			#/* Shift and mask out AIEN bit */
			val = (val >> 4) & 0b00000001
			return val
		

		""" 
		* @brief Turns ambient light interrupts on or off
		*
		* @param[in] enable 1 to enable interrupts, 0 to turn them off
		* @return True if operation successful. False otherwise.
		""" 
		def setAmbientLightIntEnable(self, enable):
			#/* Read value from ENABLE register */
			"""Enables or disables ambient-light interrupts by read-modify-writing the AIEN bit of the APDS-9960 ENABLE register.

			Inputs:
			    enable (int): 1 to enable interrupts, 0 to disable
			Outputs:
			    bool: True if the register read and write succeed, False otherwise
			"""
			retCode, val = self.ReadDataByte(self.APDS9960_ENABLE)
			if( not retCode ): return False

			#/* Set bits in register to given value */
			enable &= 0b00000001
			enable = enable << 4
			val &= 0b11101111
			val |= enable
	
			#/* Write register value back into ENABLE register */
			retCode = self.WriteDataByte(self.APDS9960_ENABLE, val) 
			if( not retCode ): return False
	
			return True
		

		""" 
		* @brief Gets if proximity interrupts are enabled or not
		*
		* @return 1 if interrupts are enabled, 0 if not. 0xFF on error.
		""" 
		def getProximityIntEnable(self):
	
			#/* Read value from ENABLE register */
			"""Reads the ENABLE register and extracts the PIEN bit to report whether proximity interrupts are currently enabled.

			Inputs:
			    None.
			Outputs:
			    tuple: (success bool, value int) where value is 1 if enabled, 0 if disabled
			"""
			retCode, val = self.ReadDataByte(self.APDS9960_ENABLE) 
			if( not retCode ): return False, 0
	
			#/* Shift and mask out PIEN bit */
			val = (val >> 5) & 0b00000001
	
			return True,val
		

		""" 
		* @brief Turns proximity interrupts on or off
		*
		* @param[in] enable 1 to enable interrupts, 0 to turn them off
		* @return True if operation successful. False otherwise.
		""" 
		def setProximityIntEnable(self, enable):
			#/* Read value from ENABLE register */
			"""Enables or disables proximity interrupts by read-modify-writing the PIEN bit of the APDS-9960 ENABLE register.

			Inputs:
			    enable (int): 1 to enable interrupts, 0 to disable
			Outputs:
			    bool: True if the register read and write succeed, False otherwise
			"""
			retCode, val = self.ReadDataByte(self.APDS9960_ENABLE)
			if( not retCode ): return False
	
			#/* Set bits in register to given value */
			enable &= 0b00000001
			enable = enable << 5
			val &= 0b11011111
			val |= enable
	
			#/* Write register value back into ENABLE register */
			retCode= self.WriteDataByte(self.APDS9960_ENABLE,val)
			if( not retCode ): return False
	
			return True
		

		""" 
		* @brief Gets if gesture interrupts are enabled or not
		*
		* @return 1 if interrupts are enabled, 0 if not. 0xFF on error.
		""" 
		def getGestureIntEnable(self):
			#/* Read value from GCONF4 register */
			"""Reads the GCONF4 register and extracts the GIEN bit to report whether gesture interrupts are currently enabled.

			Inputs:
			    None.
			Outputs:
			    int: 1 if enabled, 0 if disabled; returns False on read failure
			"""
			retCode, val = self.ReadDataByte(self.APDS9960_GCONF4)
			if( not retCode ): return False
	
			#/* Shift and mask out GIEN bit */
			val = (val >> 1) & 0b00000001
	
			return val
		

		""" 
		* @brief Turns gesture-related interrupts on or off
		*
		* @param[in] enable 1 to enable interrupts, 0 to turn them off
		* @return True if operation successful. False otherwise.
		""" 
		def setGestureIntEnable(self, enable):
			#print datetime.datetime.now().strftime("%Y%m%d-%H:%M:%S")+" enable /disable gesture interrupt :", enable
			#/* Read value from GCONF4 register */
			"""Enables or disables gesture interrupts by read-modify-writing the GIEN bit of the APDS-9960 GCONF4 register.

			Inputs:
			    enable (int): 1 to enable interrupts, 0 to disable
			Outputs:
			    bool: True if the register read and write succeed, False otherwise
			"""
			retCode, val = self.ReadDataByte(self.APDS9960_GCONF4)
			if( not retCode ): return False
	
			#/* Set bits in register to given value */
			enable &= 0b00000001
			enable = enable << 1
			val &= 0b11111101
			val |= enable
	
			#/* Write register value back into GCONF4 register */
			retCode	 = self.WriteDataByte(self.APDS9960_GCONF4,val)
			if( not retCode ): return False
	
			return True
		

		""" 
		* @brief Clears the ambient light interrupt
		*
		* @return True if operation completed successfully. False otherwise.
		""" 
		def clearAmbientLightInt(self):
			"""Clears the ambient-light interrupt by reading the APDS-9960 ambient-light clear (PICLEAR) register.

			Inputs:
			    None.
			Outputs:
			    bool: True if the clear read succeeds, False otherwise
			"""
			retCode, val = self.ReadDataByte(self.APDS9960_PICLEAR)
			if( not retCode ): return False
	
			return True
		

		""" 
		* @brief Clears the proximity interrupt
		*
		* @return True if operation completed successfully. False otherwise.
		""" 
		def clearProximityInt(self):
			"""Clears the APDS9960 proximity interrupt by reading the proximity-clear register, returning whether the I2C read succeeded.

			Inputs:
			    None.
			Outputs:
			    bool: True if the clear-register read succeeded, False otherwise
			"""
			retCode, val = self.ReadDataByte(self.APDS9960_PICLEAR)
			if( not retCode ): return False
	
			return True
		

		""" 
		* @brief Tells if the gesture state machine is currently running
		*
		* @return 1 if gesture state machine is running, 0 if not. 0xFF on error.
		""" 
		def getGestureMode(self):
			#/* Read value from GCONF4 register */
			"""Reads the GCONF4 register and masks out the GMODE bit to report whether the gesture state machine is currently active.

			Inputs:
			    None.
			Outputs:
			    int: The GMODE bit (0 or 1), or self.ERROR if the register read failed
			"""
			retCode, val = self.ReadDataByte(self.APDS9960_GCONF4)
			if( not retCode ): return self.ERROR
	
			#/* Mask out GMODE bit */
			val &= 0b00000001
	
			return val
		

		""" 
		* @brief Tells the state machine to either enter or exit gesture state machine
		*
		* @param[in] mode 1 to enter gesture state machine, 0 to exit.
		* @return True if operation successful. False otherwise.
		""" 
		def setGestureMode(self, mode):
			#/* Read value from GCONF4 register */
			"""Enables or disables the gesture state machine by reading GCONF4, setting its GMODE bit to the requested value, and writing it back.

			Inputs:
			    mode (int): 1 to enter gesture mode, 0 to exit (only low bit used)
			Outputs:
			    bool or tuple: True on success; False (or False, val) if a read/write to GCONF4 failed
			"""
			retCode, val = self.ReadDataByte(self.APDS9960_GCONF4)
			if( not retCode ): return False, val
	
			#/* Set bits in register to given value */
			mode &= 0b00000001
			val &= 0b11111110
			val |= mode
	
			#/* Write register value back into GCONF4 register */
			retCode =self.WriteDataByte(self.APDS9960_GCONF4, val )
			if( not retCode ): return False
	
			return True
		

		#/*******************************************************************************
		#* Raw I2C Reads and Writes
		#******************************************************************************/

		""" 
		* @brief Writes a single byte to the I2C device (no register)
		*
		* @param[in] val the 1-byte value to write to the I2C device
		* @return True if successful write operation. False otherwise.
		""" 
		def WriteByte(self):	# not used
			"""Issues an I2C write_quick (zero-data) command to the device address; unused helper that logs and returns False on error.

			Inputs:
			    None.
			Outputs:
			    bool: True if the quick write succeeded, False on exception
			"""
			try:
				#print	u"WriteByte"
				self.BUS.write_quick(self.address) 
			except Exception as e:
				U.logger.log(30,"", exc_info=True)
				return False
			return True
		

		""" 
		* @brief Writes a single byte to the I2C device and specified register
		*
		* @param[in] reg the register in the I2C device to write to
		* @param[in] val the 1-byte value to write to the I2C device
		* @return True if successful write operation. False otherwise.
		""" 
		def WriteDataByte(self, reg,  val):
			"""Writes a single byte value to the given register of the I2C device via write_byte_data, logging and returning False on failure.

			Inputs:
			    reg (int): register address to write to
			    val (int): one-byte value to write
			Outputs:
			    bool: True if the byte write succeeded, False on exception
			"""
			try:
				#print	u"WriteDataByte",hex(val), hex(reg)
				self.BUS.write_byte_data(self.address,reg, val)
				return True
			except Exception as e:
				U.logger.log(30,"", exc_info=True)
				return False	   
		

		"""			
		* @brief Writes a block (array) of bytes to the I2C device and register
		*
		* @param[in] reg the register in the I2C device to write to
		* @param[in] val pointer to the beginning of the data byte array
		* @param[in] len the length (in bytes) of the data to write
		* @return True if successful write operation. False otherwise.
		""" 
		def WriteDataBlock(self, reg, val,ll):	## not used
			"""Writes a block of bytes to the I2C device by issuing a write_quick then looping write_block_data for ll entries; unused helper that returns False on error.

			Inputs:
			    reg (int): register address to write to
			    val (list): sequence of byte values to write
			    ll (int): number of bytes to write
			Outputs:
			    bool: True if all block writes succeeded, False on exception
			"""
			try:
				#print	u"WriteDataBlock",val, reg, ll
				self.BUS.write_quick(self.address,reg) 
				for i in range(ll):
					self.BUS.write_block_data(self.address,val[i])
				return True
			except Exception as e:
				U.logger.log(30,"", exc_info=True)
				return False	   

		""""
		* @brief Reads a single byte from the I2C device and specified register
		*
		* @param[in] reg the register to read from
		* @param[out] the value returned from the register
		* @return True if successful read operation. False otherwise.
		"""
		def ReadDataByte(self, reg):
			"""Reads a single byte from the given register of the I2C device via read_byte_data, returning a success flag and the value.

			Inputs:
			    reg (int): register address to read from
			Outputs:
			    tuple: (True, value) on success; (False, 0) on exception
			"""
			try:
				val = self.BUS.read_byte_data(self.address,reg)
			except Exception as e:
				U.logger.log(30,"", exc_info=True)
				return False, 0
			#print	u"ReadDataByte return",hex(reg), hex(val)
			return True, val
		

		""" 
		* @brief Reads a block (array) of bytes from the I2C device and register
		*
		* @param[in] reg the register to read from
		* @param[out] val pointer to the beginning of the data
		* @param[in] len number of bytes to read
		* @return Number of bytes read. -1 on read error.
		""" 
		def ReadDataBlock1(self, reg, lenIN):
			"""Reads lenIN bytes from the I2C device one byte at a time after a write_quick, accumulating them into a list and counting how many were read.

			Inputs:
			    reg (int): register address (issued via write_quick)
			    lenIN (int): number of bytes to read
			Outputs:
			    tuple: (count, list of byte values) on success; (-1, []) on exception
			"""
			try:
				val=[]
				self.BUS.write_quick(self.address) 
				lenOUT=0
				for i in range(lenIN):
					val.append(self.BUS.read_byte(self.address))
					lenOUT+=1
				#print "ReadDataBlock", i+1, val 
				return lenOUT, val
			except Exception as e:
				U.logger.log(30,"", exc_info=True)
				return -1, []



		########## special read direct #############
		def ReadDataBlock(self, reg, lenIN):
			"""Special direct block read that calls read_i2c_block_data from register 0xFC four times, concatenating the results into one byte list.

			Inputs:
			    reg (int): register parameter (ignored; fixed 0xFC is used)
			    lenIN (int): requested length (ignored; four blocks are read)
			Outputs:
			    tuple: (byte count, list of byte values) on success; (-1, []) on exception
			"""
			try:
				ret =[]
				for nn in range(4):
					ret+=(self.BUS.read_i2c_block_data(self.address,0xFC) )
				lenOUT= len(ret)
				#print "ReadDataBlock",ret
				return lenOUT, ret
			except Exception as e:
				U.logger.log(30,"", exc_info=True)
				return -1, []




		########## special read direct #############
		def ReadDataBlock3(self, reg, lenIN):
			"""Special direct block read that opens /dev/i2c-1, sets the I2C slave address via ioctl, reads 128 raw bytes, and converts them to a list of integer values.

			Inputs:
			    reg (int): register parameter (unused in the read)
			    lenIN (int): requested length (unused; fixed 128 bytes read)
			Outputs:
			    tuple: (count, list of int byte values) on success; (-1, []) on exception
			"""
			try:
				val=[]
				#print	u"ReadDataBlock",reg,len
				self.BUS.write_quick(self.address) 

				self.file_read	= io.open("/dev/i2c-1", "rb", buffering = 0)
				fcntl.ioctl(self.file_read,	 0x703, self.address) #	 0x703 = I2C_SLAVE 
				ret		= self.file_read.read(128)
				self.file_read.close()

				#print	type(ret), ret
				val2=[]
				lenOut =0
				for c in ret:
					val2.append(ord(c))
					lenOut +=1
					
				#print "ReadDataBlock", lenOut, val2
				return lenOut, val2
			except Exception as e:
				U.logger.log(30,"", exc_info=True)
				return -1, []


				
##################################	gesture handling ############
def gestureInterrupt(gpio=0):
	"""GPIO interrupt callback that resets the global lastGestureTime to 0 and flags newInterrupt True so the main loop knows a gesture interrupt fired.

	Inputs:
	    gpio (int): GPIO pin number that triggered the interrupt
	Outputs:
	    None: sets module-level lastGestureTime and newInterrupt globals
	"""
	global lastGestureTime,	 newInterrupt
	lastGestureTime = 0
	newInterrupt	= True
	#print datetime.datetime.now().strftime("%Y%m%d-%H:%M:%S")+ "  interrupt happended ", gpio
	return 
	
def getinput(devid):
	"""Polls the APDS9960 sensor for a given device: reads gesture, proximity, and RGB/ambient color values when their refresh intervals elapse, runs configured shell actions for detected gestures/proximity changes, updates global tracking state, and returns the changed readings.

	Inputs:
	    devid (str): key identifying the sensor device within the sensors dict
	Outputs:
	    dict: data dict of newly changed readings (gesture, nearFar, proximity, speed, red/blue/green, AmbientLight)
	"""
	global sensors, sensor, sensorList, sensorDev
	global lastRedValue, lastBlueValue, lastGreenValue, lastAmbValue, lastGesture
	global lastColorTime,lastGestureTime, lastProximityTime,  lastProximityValue, newInterrupt	  
	global refreshColor, deltaColor, refreshProximity, deltaProximity, enableGesture,enableNearFar, interruptGPIO, i2cAddress

	try:
			newGesture	 = False
			data ={}
			tt = time.time()
			newInterrupt		= False
			sen = sensors[sensor][devid] #	shortcut 
			if enableGesture and (tt - lastGestureTime) > 0.1: 
				gesture,nearFar,UPdown, LEFTright = sensorDev.readGesture()
				## values UPdown, LEFTright not used yet 
				if gesture != lastGesture and gesture not in ["","NONE",sensorDev.ERROR]:#	 valid: ["UP","DOWN","VERTICAL","LEFT","RIGHT","HORIZONTAL","MOVEMENT"]
					#print " new gesture" ,lastGesture, gesture
					if enableNearFar and nearFar != "":
						data["nearFar"]	 = nearFar
					data["gesture"]		 = gesture
					newGesture	= True
					if "action"+str(gesture) in sensors[sensor][devid] and sen["action"+(gesture)] !="": 
						U.logger.log(10, "action: "+str(gesture)+" " +sen["action"+str(gesture)])
						subprocess.call(sensors[sensor][devid]["action"+str(gesture)], shell=True)
					if "action"+str(nearFar) in sensors[sensor][devid] and sen["action"+(nearFar)] !="": 
						U.logger.log(10, "action: "+str(nearFar)+" " +sen["action"+str(nearFar)])
						subprocess.call(sensors[sensor][devid]["action"+str(nearFar)], shell=True)
					sensorDev.clearGestureFIFO()
					time.sleep(0.02)
					sensorDev.readGesture()	 # clean out fifo
				lastGesture				= gesture
				tt = time.time()
				lastGestureTime			= tt
	
			tt = time.time()
			if (tt - lastProximityTime) > refreshProximity or ( newGesture and (tt - lastProximityTime) > 0.2): 
				if newGesture: time.sleep(0.1)
				prox = sensorDev.readProximity() 
				if abs(prox-lastProximityValue) > deltaProximity:
					#print		"readProximity			 ", prox
					data["proximity"]	= prox
					data["speed"]		= (prox- lastProximityValue)/max((tt-lastProximityTime),0.01)
					lastColorTime		= 0
					lastGestureTime		= 0
					if prox > lastProximityValue and "actionPROXup"	  in sen and sen["actionPROXup"] !="": 
						U.logger.log(10, "action:  "+sensors[sensor][devid]["actionPROXup"])
						subprocess.call(sensors[sensor][devid]["actionPROXup"], shell=True)
					if prox < lastProximityValue and "actionPROXdown" in sen and sen["actionPROXdown"] !="" : 
						subprocess.call(sensors[sensor][devid]["actionPROXdown"], shell=True)
						U.logger.log(10, "action: "+sensors[sensor][devid]["actionPROXdown"])
					lastProximityValue	= prox
					lastProximityTime	= tt

			tt = time.time()
			if (tt - lastColorTime) > refreshColor	or ( newGesture and (tt - lastColorTime) > 0.2):
				amb	  = sensorDev.readAmbientLight() 
				time.sleep(0.05)
				red	  = sensorDev.readRedLight() 
				time.sleep(0.05)
				green = sensorDev.readGreenLight() 
				time.sleep(0.05)
				blue  = sensorDev.readBlueLight() 
				time.sleep(0.05)
				#print red,blue,green, amb
				if( abs(red	  - lastRedValue)	> deltaColor or 
					abs(blue  - lastBlueValue)	> deltaColor or 
					abs(green - lastGreenValue) > deltaColor or 
					abs(amb	  - lastAmbValue)	> deltaColor  ):
						lastRedValue		= red 
						lastBlueValue		= blue 
						lastGreenValue		= green 
						lastAmbValue		= amb
						data["red"]			= red
						data["blue"]		= blue
						data["green"]		= green
						data["AmbientLight"] = amb
				lastColorTime				= tt
		

	except Exception as e:
		U.logger.log(30,"", exc_info=True)
	sensorDev.clearGestureFIFO()
	return data

				   





# ===========================================================================
# read params
# ===========================================================================

#################################		 
def readParams():
	"""Reads the latest plugin parameter file, parses APDS9960 sensor settings (color/proximity refresh and delta thresholds, gesture/near-far enables, interrupt GPIO, I2C address) into module globals, and if the sensor configuration changed it instantiates and initializes the APDS9960 device, enabling its light, proximity, and gesture sensors and wiring up the gesture interrupt GPIO.

	Inputs:
	    None.
	Outputs:
	    None: updates module globals, initializes the APDS9960 hardware, configures GPIO interrupts, and logs
	"""
	global lastRedValue, lastBlueValue, lastGreenValue, lastAmbValue, lastGesture 
	global lastColorTime,lastGestureTime, lastProximityTime,  lastProximityValue
	global sensors, sensor, sensorList, sensorDev, interruptGPIOAlreadySetup, sensorsOld
	global refreshColor, deltaColor, refreshProximity, deltaProximity, enableGesture,enableNearFar, interruptGPIO, i2cAddress
	global oldRaw, lastRead
	global PIZEROGPIO

	try:

		inp, inpRaw, lastRead2 = U.doRead(lastTimeStamp=lastRead)
		if inp == "": return
		if lastRead2 == lastRead: return
		lastRead   = lastRead2
		if inpRaw == oldRaw: return
		oldRaw	   = inpRaw
		sensorList=[]


		if len(sensors) >0:
			sensorsOld= copy.copy(sensors)

		
		U.getGlobalParams(inp)
		  
		if "sensorList"			in inp:	 sensorList=			 (inp["sensorList"])
		if "sensors"			in inp:	 sensors =				 (inp["sensors"])
		
		if sensors =={}: return 
 
		if sensor not in sensors:
			U.logger.log(30, sensor+" is not in parameters = not enabled, stopping "+G.program+".py" )
			U.logger.log(30, "{}".format(sensors) )
			exit()


		for devid in sensors[sensor]:
			
			if "refreshColor" in sensors[sensor][devid]:
				refreshColor	   = float(sensors[sensor][devid]["refreshColor"])
			else:
				refreshColor   = 50.
			if "deltaColor" in sensors[sensor][devid]:
				deltaColor		 = float(sensors[sensor][devid]["deltaColor"])
			else:
				deltaColor	 = 50.

			if "refreshProximity" in sensors[sensor][devid]:
				refreshProximity	  = float(sensors[sensor][devid]["refreshProximity"])
			else:
				refreshProximity   = 2.
			if "deltaProximity" in sensors[sensor][devid]:
				deltaProximity		 = float(sensors[sensor][devid]["deltaProximity"])
			else:
				deltaProximity	 = 50.

			if "enableGesture" in sensors[sensor][devid]:
				enableGesture		= sensors[sensor][devid]["enableGesture"] =="1"
			else:
				enableGesture	= True

			if "enableNearFar" in sensors[sensor][devid]:
				enableNearFar	= sensors[sensor][devid]["enableNearFar"] =="1"
			else:
				enableNearFar   = True

			if "interruptGPIO" in sensors[sensor][devid]:
				interruptGPIO		= int(sensors[sensor][devid]["interruptGPIO"])
			else:
				interruptGPIO  = 23

			i2cAddress = U.getI2cAddress(sensors[sensor][devId], default =57)
 
		sensorUp = doWeNeedToStartSensor(sensors,sensorsOld,sensor)
		
		if sensorUp == 1:
				sensorDev= APDS9960(i2cAdd=i2cAddress)
				sensorDev.init()
				U.logger.log(30, "starting sensorDev")
				U.logger.log(30,	 " starting sensorDev", "{}".format(sensorDev))

				if refreshColor >=0:

					if	sensorDev.enableLightSensor(False) :
						U.logger.log(30,	 "enableLightSensor ok")
					else:
						U.logger.log(30, "enableLightSensor bad exit ")
						exit()
					#Wait for initialization and calibration to finish
					time.sleep(1)

				if refreshProximity >=0:
					if sensorDev.setProximityGain(1):
						U.logger.log(30, "setProximityGain ok")
					else:
						U.logger.log(30, "setProximityGain bad exit")
						exit()

					if sensorDev.enableProximitySensor(False):
						U.logger.log(30, "enableProximitySensor ok")
					else:
						U.logger.log(30, "enableProximitySensor bad exit")
						exit()

				if enableGesture:
					if sensorDev.enableGestureSensor(True):
						U.logger.log(30, "enableGestureSensor ok")
					else:
						U.logger.log(30, "enableGestureSensor bad exit")
						exit()

				
				if enableGesture:
					try:
						if interruptGPIO > 0:
							if interruptGPIOAlreadySetup != interruptGPIO:
								if useGPIO:
									GPIO.setup(interruptGPIO, GPIO.IN)
									GPIO.remove_event_detect(interruptGPIO)
									GPIO.add_event_detect(interruptGPIO,GPIO.FALLING)
									GPIO.add_event_callback(interruptGPIO,gestureInterrupt)
									U.logger.log(20, "GPIO interrupt pin setup")
									interruptGPIOAlreadySetup = interruptGPIO
								else:
									PIZEROGPIO[interruptGPIO] = gpiozero.Button(interruptGPIO, pull_up=True) 
									PIZEROGPIO[interruptGPIO].when_pressed  = gestureInterrupt 

									U.logger.log(20, "PIZEROGPIO interrupt pin setup")
									interruptGPIOAlreadySetup = interruptGPIO

					except Exception as e:
						U.logger.log(30,"", exc_info=True)
					

		if sensorUp == -1:
			pass
			# stop sensor
		if len(sensors) >0:
			sensorsOld= copy.copy(sensors)

		
	except Exception as e:
		U.logger.log(30,"", exc_info=True)

#################################
def doWeNeedToStartSensor(sensors,sensorsOld,selectedSensor):
	"""Compares the current and previous sensor parameter dictionaries for the selected sensor to decide whether the sensor needs to be (re)started; returns -1 if the sensor is no longer configured, 1 if any device or property was added/removed/changed, and 0 if unchanged.

	Inputs:
	    sensors (dict): current sensor configuration mapping sensor->devId->props
	    sensorsOld (dict): previous sensor configuration to compare against
	    selectedSensor (str): key of the sensor type being checked
	Outputs:
	    int: -1 if sensor removed, 1 if (re)start needed, 0 if no change
	"""
	if selectedSensor not in sensors:	 return -1
	if selectedSensor not in sensorsOld: 
		return 1
	for devId in sensors[selectedSensor] :
			if devId not in sensorsOld[selectedSensor] : 
				return 1
			for prop in sensors[sensor][devId] :
				if prop not in sensorsOld[selectedSensor][devId] :
					return 1
				if sensors[selectedSensor][devId][prop] != sensorsOld[selectedSensor][devId][prop]:
					return 1
   
	for devId in sensorsOld[selectedSensor]:
			if devId not in sensors[selectedSensor] :				
				return 1
			for prop in sensorsOld[selectedSensor][devId] :
				if prop not in sensors[selectedSensor][devId] :
					return 1

	return 0


#################################


 
##################################	main ############
global sensors, sensor,sensorDev, lastColorTime,  lastRedValue, lastBlueValue, lastGreenValue, lastAmbValue, lastGestureTime,  lastProximityTime,  lastProximityValue
global sensorList, ipAddress, interruptGPIOAlreadySetup
global authentication, newInterrupt, sensorsOld
global refreshColor, deltaColor, refreshProximity, deltaProximity, enableGesture,enableNearFar, interruptGPIO, i2cAddress
global oldRaw,	lastRead
global PIZEROGPIO

PIZEROGPIO					= {}

oldRaw					= ""
lastRead				= 0

tt = time.time()

interruptGPIO		= -1
interruptGPIOAlreadySetup =-99
lastColorTime		= 0
lastProximityTime	= 0
lastGestureTime		= 0
lastProximityValue	= -1
lastRedValue		= -1
lastGreenValue		= -1
lastBlueValue		= -1
lastAmbValue		= -1
lastGesture			= ""
sensorDev			= ""
debug				= 5
first				= False
loopCount			= 0
NSleep				= 100
sensorList			= []
sensors				= {"x":0}
sensor				= G.program
lastAlive			= 0
lastMsg				= 0
output				= {}
newInterrupt		= False
refreshColor		=-1
deltaColor			= 10
refreshProximity	= 10
deltaProximity		= 10
enableGesture		= True
enableNearFar		= True
interruptGPIO		= 17
i2cAddress			= 0x39
sensorsOld			= {"x":0}
myPID		= str(os.getpid())
U.setLogging()
U.killOldPgm(myPID,G.program+".py")# kill old instances of myself if they are still running


readParams()

if U.getIPNumber() > 0:
	time.sleep(10)
	exit()

subprocess.call("echo "+str(time.time())+" > "+ G.homeDir+"temp/alive."+sensor+" &", shell=True )

lastData			= {}
lastValues			= {}
lastSend			= 0
values				= {}
G.lastAliveSend		= time.time() -1000
quick				= False

sensorDev.clearGestureFIFO()
while True:
	try:
		tt = time.time()
		data = {"sensors":{}}
		if sensor in sensors:
			for devId in sensors[sensor]:
				if devId not in lastData: lastData[devId] =-500.
				values = getinput(devId)
				data["sensors"]		= {sensor:{devId:values}}
				if devId not in lastValues: lastValues[devId]={}
				#print " values", values, lastValues[devId]
				if (  (tt - 300.) > G.lastAliveSend ) or  ( values !={} and ( (lastValues[devId]  != values) or ( (tt - 1.) > G.lastAliveSend) ) or quick):
					U.sendURL(data)
					lastValues[devId]  = values

		loopCount +=1
		
		U.makeDATfile(sensor, data)

		quick = U.checkNowFile(sensor)				  
		if quick:
				lastGestureTime		= 0
				lastProximityTime	= 0
				lastColorTime		= 0


					
		if	tt-lastAlive > 30:	 # one every xx seconds
			U.echoLastAlive(sensor)
			readParams()

		#print "end of loop", loopCount
		if not quick:
			for ii in range(40):
				time.sleep(0.05)
				if newInterrupt:
					time.sleep(0.1) 
					break


	except Exception as e:
		U.logger.log(30,"", exc_info=True)
		time.sleep(5.)
try: 	G.sendThread["run"] = False; time.sleep(1)
except: pass
sys.exit(0)
