#!/usr/bin/python
# -*- coding: utf-8 -*-
## adopted from adafruit   
#
#

import sys, os, time, json, copy
import smbus

sys.path.append(os.getcwd())
import	piBeaconUtils	as U
import	piBeaconGlobals as G

G.program = "bno055"

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




# I2C addresses
BNO055_ADDRESS_A					 = 0x28
BNO055_ADDRESS_B					 = 0x29
BNO055_ID							 = 0xA0

# Page id register definition
BNO055_PAGE_ID_ADDR					 = 0X07

# PAGE0 REGISTER DEFINITION START
BNO055_CHIP_ID_ADDR					 = 0x00
BNO055_ACCEL_REV_ID_ADDR			 = 0x01
BNO055_MAG_REV_ID_ADDR				 = 0x02
BNO055_GYRO_REV_ID_ADDR				 = 0x03
BNO055_SW_REV_ID_LSB_ADDR			 = 0x04
BNO055_SW_REV_ID_MSB_ADDR			 = 0x05
BNO055_BL_REV_ID_ADDR				 = 0X06

# Accel data register
BNO055_ACCEL_DATA_X_LSB_ADDR		 = 0X08
BNO055_ACCEL_DATA_X_MSB_ADDR		 = 0X09
BNO055_ACCEL_DATA_Y_LSB_ADDR		 = 0X0A
BNO055_ACCEL_DATA_Y_MSB_ADDR		 = 0X0B
BNO055_ACCEL_DATA_Z_LSB_ADDR		 = 0X0C
BNO055_ACCEL_DATA_Z_MSB_ADDR		 = 0X0D

# Mag data register
BNO055_MAG_DATA_X_LSB_ADDR			 = 0X0E
BNO055_MAG_DATA_X_MSB_ADDR			 = 0X0F
BNO055_MAG_DATA_Y_LSB_ADDR			 = 0X10
BNO055_MAG_DATA_Y_MSB_ADDR			 = 0X11
BNO055_MAG_DATA_Z_LSB_ADDR			 = 0X12
BNO055_MAG_DATA_Z_MSB_ADDR			 = 0X13

# Gyro data registers
BNO055_GYRO_DATA_X_LSB_ADDR			 = 0X14
BNO055_GYRO_DATA_X_MSB_ADDR			 = 0X15
BNO055_GYRO_DATA_Y_LSB_ADDR			 = 0X16
BNO055_GYRO_DATA_Y_MSB_ADDR			 = 0X17
BNO055_GYRO_DATA_Z_LSB_ADDR			 = 0X18
BNO055_GYRO_DATA_Z_MSB_ADDR			 = 0X19

# Euler data registers
BNO055_EULER_H_LSB_ADDR				 = 0X1A
BNO055_EULER_H_MSB_ADDR				 = 0X1B
BNO055_EULER_R_LSB_ADDR				 = 0X1C
BNO055_EULER_R_MSB_ADDR				 = 0X1D
BNO055_EULER_P_LSB_ADDR				 = 0X1E
BNO055_EULER_P_MSB_ADDR				 = 0X1F

# Quaternion data registers
BNO055_QUATERNION_DATA_W_LSB_ADDR	 = 0X20
BNO055_QUATERNION_DATA_W_MSB_ADDR	 = 0X21
BNO055_QUATERNION_DATA_X_LSB_ADDR	 = 0X22
BNO055_QUATERNION_DATA_X_MSB_ADDR	 = 0X23
BNO055_QUATERNION_DATA_Y_LSB_ADDR	 = 0X24
BNO055_QUATERNION_DATA_Y_MSB_ADDR	 = 0X25
BNO055_QUATERNION_DATA_Z_LSB_ADDR	 = 0X26
BNO055_QUATERNION_DATA_Z_MSB_ADDR	 = 0X27

# Linear acceleration data registers
BNO055_LINEAR_ACCEL_DATA_X_LSB_ADDR	 = 0X28
BNO055_LINEAR_ACCEL_DATA_X_MSB_ADDR	 = 0X29
BNO055_LINEAR_ACCEL_DATA_Y_LSB_ADDR	 = 0X2A
BNO055_LINEAR_ACCEL_DATA_Y_MSB_ADDR	 = 0X2B
BNO055_LINEAR_ACCEL_DATA_Z_LSB_ADDR	 = 0X2C
BNO055_LINEAR_ACCEL_DATA_Z_MSB_ADDR	 = 0X2D

# Gravity data registers
BNO055_GRAVITY_DATA_X_LSB_ADDR		 = 0X2E
BNO055_GRAVITY_DATA_X_MSB_ADDR		 = 0X2F
BNO055_GRAVITY_DATA_Y_LSB_ADDR		 = 0X30
BNO055_GRAVITY_DATA_Y_MSB_ADDR		 = 0X31
BNO055_GRAVITY_DATA_Z_LSB_ADDR		 = 0X32
BNO055_GRAVITY_DATA_Z_MSB_ADDR		 = 0X33

# Temperature data register
BNO055_TEMP_ADDR					 = 0X34

# Status registers
BNO055_CALIB_STAT_ADDR				 = 0X35
BNO055_SELFTEST_RESULT_ADDR			 = 0X36
BNO055_INTR_STAT_ADDR				 = 0X37

BNO055_SYS_CLK_STAT_ADDR			 = 0X38
BNO055_SYS_STAT_ADDR				 = 0X39
BNO055_SYS_ERR_ADDR					 = 0X3A

# Unit selection register
BNO055_UNIT_SEL_ADDR				 = 0X3B
BNO055_DATA_SELECT_ADDR				 = 0X3C

# Mode registers
BNO055_OPR_MODE_ADDR				 = 0X3D
BNO055_PWR_MODE_ADDR				 = 0X3E

BNO055_SYS_TRIGGER_ADDR				 = 0X3F
BNO055_TEMP_SOURCE_ADDR				 = 0X40

# Axis remap registers
BNO055_AXIS_MAP_CONFIG_ADDR			 = 0X41
BNO055_AXIS_MAP_SIGN_ADDR			 = 0X42

# Axis remap values
AXIS_REMAP_X						 = 0x00
AXIS_REMAP_Y						 = 0x01
AXIS_REMAP_Z						 = 0x02
AXIS_REMAP_POSITIVE					 = 0x00
AXIS_REMAP_NEGATIVE					 = 0x01

# SIC registers
BNO055_SIC_MATRIX_0_LSB_ADDR		 = 0X43
BNO055_SIC_MATRIX_0_MSB_ADDR		 = 0X44
BNO055_SIC_MATRIX_1_LSB_ADDR		 = 0X45
BNO055_SIC_MATRIX_1_MSB_ADDR		 = 0X46
BNO055_SIC_MATRIX_2_LSB_ADDR		 = 0X47
BNO055_SIC_MATRIX_2_MSB_ADDR		 = 0X48
BNO055_SIC_MATRIX_3_LSB_ADDR		 = 0X49
BNO055_SIC_MATRIX_3_MSB_ADDR		 = 0X4A
BNO055_SIC_MATRIX_4_LSB_ADDR		 = 0X4B
BNO055_SIC_MATRIX_4_MSB_ADDR		 = 0X4C
BNO055_SIC_MATRIX_5_LSB_ADDR		 = 0X4D
BNO055_SIC_MATRIX_5_MSB_ADDR		 = 0X4E
BNO055_SIC_MATRIX_6_LSB_ADDR		 = 0X4F
BNO055_SIC_MATRIX_6_MSB_ADDR		 = 0X50
BNO055_SIC_MATRIX_7_LSB_ADDR		 = 0X51
BNO055_SIC_MATRIX_7_MSB_ADDR		 = 0X52
BNO055_SIC_MATRIX_8_LSB_ADDR		 = 0X53
BNO055_SIC_MATRIX_8_MSB_ADDR		 = 0X54

# Accelerometer Offset registers
ACCEL_OFFSET_X_LSB_ADDR				 = 0X55
ACCEL_OFFSET_X_MSB_ADDR				 = 0X56
ACCEL_OFFSET_Y_LSB_ADDR				 = 0X57
ACCEL_OFFSET_Y_MSB_ADDR				 = 0X58
ACCEL_OFFSET_Z_LSB_ADDR				 = 0X59
ACCEL_OFFSET_Z_MSB_ADDR				 = 0X5A

# Magnetometer Offset registers
MAG_OFFSET_X_LSB_ADDR				 = 0X5B
MAG_OFFSET_X_MSB_ADDR				 = 0X5C
MAG_OFFSET_Y_LSB_ADDR				 = 0X5D
MAG_OFFSET_Y_MSB_ADDR				 = 0X5E
MAG_OFFSET_Z_LSB_ADDR				 = 0X5F
MAG_OFFSET_Z_MSB_ADDR				 = 0X60

# Gyroscope Offset register s
GYRO_OFFSET_X_LSB_ADDR				 = 0X61
GYRO_OFFSET_X_MSB_ADDR				 = 0X62
GYRO_OFFSET_Y_LSB_ADDR				 = 0X63
GYRO_OFFSET_Y_MSB_ADDR				 = 0X64
GYRO_OFFSET_Z_LSB_ADDR				 = 0X65
GYRO_OFFSET_Z_MSB_ADDR				 = 0X66

# Radius registers
ACCEL_RADIUS_LSB_ADDR				 = 0X67
ACCEL_RADIUS_MSB_ADDR				 = 0X68
MAG_RADIUS_LSB_ADDR					 = 0X69
MAG_RADIUS_MSB_ADDR					 = 0X6A

# Power modes
POWER_MODE_NORMAL					 = 0X00
POWER_MODE_LOWPOWER					 = 0X01
POWER_MODE_SUSPEND					 = 0X02

# Operation mode settings
OPERATION_MODE_CONFIG				 = 0X00
OPERATION_MODE_ACCONLY				 = 0X01
OPERATION_MODE_MAGONLY				 = 0X02
OPERATION_MODE_GYRONLY				 = 0X03
OPERATION_MODE_ACCMAG				 = 0X04
OPERATION_MODE_ACCGYRO				 = 0X05
OPERATION_MODE_MAGGYRO				 = 0X06
OPERATION_MODE_AMG					 = 0X07
OPERATION_MODE_IMUPLUS				 = 0X08
OPERATION_MODE_COMPASS				 = 0X09
OPERATION_MODE_M4G					 = 0X0A
OPERATION_MODE_NDOF_FMC_OFF			 = 0X0B
OPERATION_MODE_NDOF					 = 0X0C




##class BNO055(object):
class BNO055():

	def __init__(self, resetPin=None, i2cAddress=BNO055_ADDRESS_A, **kwargs):
		# If reset pin is provided save it and a reference to provided GPIO
		# bus (or the default system GPIO bus if none is provided).
		self.i2cAddress = i2cAddress
		self.resetPin = resetPin
		if self.resetPin is not None:
			if useGPIO:
				GPIO.setup(self.resetPin, GPIO.OUT)
				GPIO.output(self.resetPin, True)
			else:
				self.GPIOZERO.LED(self.resetPin, initial_value=True)
			# Wait a 650 milliseconds in case setting the reset high reset the chip.
			time.sleep(0.65)
		# Use I2C if no serial port is provided.
		# Assume we're using platform's default I2C bus if none is specified.
		self.bus = smbus.SMBus(1)
		#self.Calibration = []
		self.Calibration = self.readCalibrationFromFile()

	def readCalibrationFromFile(self):
		calib = []
		try:
			if os.path.isfile(G.homeDir +G.program+".calib"):
				f = open(G.homeDir +G.program+".calib","r")
				calib = json.loads(f.read())
				f.close()
				U.logger.log(10,"INIT: read calibration from file: {}".format(calib))
				return calib
		except:
			try: f.close()
			except: pass
		return[]

	def writeCalibrationToFile(self,calib):
		try:
			f = open(G.homeDir +G.program+".calib","w")
			f.write( json.dumps(calib))
			f.close()
		except:
			try: f.close()
			except: pass
		return

	def _write_bytes(self, reg, ll):
		# Write a list of 8-bit values starting at the provided register address.
		self.bus.write_i2c_block_data(self.i2cAddress, reg, ll)
		return 
		
	def _write_byte(self, reg, value):
		# Write an 8-bit value to the provided register address.  If ack is True
		return self.bus.write_byte_data(self.i2cAddress, reg, value)

	def _read_bytes(self, reg, length):
		# Read a number of unsigned byte values starting from the provided address.
		return self.bus.read_i2c_block_data(self.i2cAddress, reg, length)
		
	def _read_byte(self, reg):
		# Read an 8-bit unsigned value from the provided register address.
		return self.bus.read_byte_data(self.i2cAddress, reg)
	
	def _read_signed_byte(self, reg):
		# Read an 8-bit signed value from the provided register address.
		data = self._read_byte(reg)
		if data > 127:
			return data - 256
		else:
			return data

	def _config_mode(self):
		# Enter configuration mode.
		self.set_mode(OPERATION_MODE_CONFIG)

	def _operation_mode(self):
		# Enter operation mode to read sensor data.
		self.set_mode(self._mode)

	def begin(self, mode=OPERATION_MODE_NDOF):
		"""Initialize the BNO055 sensor.  Must be called once before any other
		BNO055 library functions.  Will return True if the BNO055 was
		successfully initialized, and False otherwise.
		"""
		# Save the desired normal operation mode.
		self._mode = mode
		# First send a thow-away command and ignore any response or I2C errors
		# just to make sure the BNO is in a good state and ready to accept
		# commands (this seems to be necessary after a hard power down).
		try:
			self._write_byte(BNO055_PAGE_ID_ADDR, 0)
		except IOError:
			# Swallow an IOError that might be raised by an I2C issue.	Only do
			# this for this very first command to help get the BNO and board's
			# I2C into a clear state ready to accept the next commands.
			pass
		# Make sure we're in config mode and on page 0.
		self._config_mode()
		self._write_byte(BNO055_PAGE_ID_ADDR, 0)
		# Check the chip ID
		bno_id = self._read_byte(BNO055_CHIP_ID_ADDR)
		U.logger.log(10,'BEGIN: Read chip ID: 0x{0:02X}'.format(bno_id))
		if bno_id != BNO055_ID:
			return False
		# Reset the device.
		if self.resetPin is not None:
			# Use the hardware reset pin if provided.
			# Go low for a short period, then high to signal a reset.
			U.logger.log(10,'BEGIN: doing a hardware reset')
			if useGPIO:
				GPIO.output(self.resetPin, False)
				time.sleep(0.01)  # 10ms
				GPIO.output(self.resetPin, True)
			else:
				self.GPIOZERO.off()
				time.sleep(0.01)  # 10ms
				self.GPIOZERO.on()
		else:
			# Else use the reset command.
			U.logger.log(10,'BEGIN: doing a software reset')
			self._write_byte(BNO055_SYS_TRIGGER_ADDR, 0x20)

			
		# Wait 650ms after reset for chip to be ready (as suggested
		# in datasheet).
		time.sleep(0.8)
		# Set to normal power mode.
		self._write_byte(BNO055_PWR_MODE_ADDR, POWER_MODE_NORMAL)
		# Default to internal oscillator.
		self._write_byte(BNO055_SYS_TRIGGER_ADDR, 0x0)

		# set temp source to accellerometers(0x00) if gyroscope does not work (0x01)
		self._write_byte(BNO055_TEMP_SOURCE_ADDR, 0x01)

		#print self.Calibration
		if self.Calibration != []:
			self.set_calibration(self.Calibration,setMode=False)


		# Enter normal operation mode.
		self._operation_mode()
		return True

	def set_mode(self, mode):
		"""Set operation mode for BNO055 sensor.  Mode should be a value from
		table 3-3 and 3-5 of the datasheet:
		  http://www.adafruit.com/datasheets/BST_BNO055_DS000_12.pdf
		"""
		self._write_byte(BNO055_OPR_MODE_ADDR, mode & 0xFF)
		# Delay for 30 milliseconds (datsheet recommends 19ms, but a little more
		# can't hurt and the kernel is going to spend some unknown amount of time
		# too).
		time.sleep(0.03)

	def get_revision(self):
		"""Return a tuple with revision information about the BNO055 chip.	Will
		return 5 values:
		  - Software revision
		  - Bootloader version
		  - Accelerometer ID
		  - Magnetometer ID
		  - Gyro ID
		"""
		# Read revision values.
		accel = self._read_byte(BNO055_ACCEL_REV_ID_ADDR)
		mag = self._read_byte(BNO055_MAG_REV_ID_ADDR)
		gyro = self._read_byte(BNO055_GYRO_REV_ID_ADDR)
		bl = self._read_byte(BNO055_BL_REV_ID_ADDR)
		sw_lsb = self._read_byte(BNO055_SW_REV_ID_LSB_ADDR)
		sw_msb = self._read_byte(BNO055_SW_REV_ID_MSB_ADDR)
		sw = ((sw_msb << 8) | sw_lsb) & 0xFFFF
		# Return the results as a tuple of all 5 values.
		return (sw, bl, accel, mag, gyro)

	def set_external_crystal(self, external_crystal):
		"""Set if an external crystal is being used by passing True, otherwise
		use the internal oscillator by passing False (the default behavior).
		"""
		# Switch to configuration mode.
		self._config_mode()
		# Set the clock bit appropriately in the SYS_TRIGGER register.
		if external_crystal:
			self._write_byte(BNO055_SYS_TRIGGER_ADDR, 0x80)
		else:
			self._write_byte(BNO055_SYS_TRIGGER_ADDR, 0x00)
		# Go back to normal operation mode.
		self._operation_mode()

	def get_system_status(self, run_self_test=True):
		try:
			"""Return a tuple with status information.	Three values will be returned:
			  - System status register value with the following meaning:
				  0 = Idle
				  1 = System Error
				  2 = Initializing Peripherals
				  3 = System Initialization
				  4 = Executing Self-Test
				  5 = Sensor fusion algorithm running
				  6 = System running without fusion algorithms
			  - Self test result register bit value with the following meaning:
				  Bit value: 1 = test passed, 0 = test failed
				  Bit 0 = Accelerometer self test
				  Bit 1 = Magnetometer self test
				  Bit 2 = Gyroscope self test
				  Bit 3 = MCU self test
				  Value of 0x0F = all good!
			  - System error register value with the following meaning:
				  0 = No error
				  1 = Peripheral initialization error
				  2 = System initialization error
				  3 = Self test result failed
				  4 = Register map value out of range
				  5 = Register map address out of range
				  6 = Register map write error
				  7 = BNO low power mode not available for selected operation mode
				  8 = Accelerometer power mode not available
				  9 = Fusion algorithm configuration error
				 10 = Sensor configuration error

			If run_self_test is passed in as False then no self test is performed and
			None will be returned for the self test result.	 Note that running a
			self test requires going into config mode which will stop the fusion
			engine from running.
			"""
			self_test = None
			if run_self_test:
				# Switch to configuration mode if running self test.
				self._config_mode()
				# Perform a self test.
				sys_trigger = self._read_byte(BNO055_SYS_TRIGGER_ADDR)
				self._write_byte(BNO055_SYS_TRIGGER_ADDR, sys_trigger | 0x1)
				# Wait for self test to finish.
				time.sleep(1.0)
				# Read test result.
				self_test = self._read_byte(BNO055_SELFTEST_RESULT_ADDR)
				# Go back to operation mode.
				self._operation_mode()
			# Now read status and error registers.
			status = self._read_byte(BNO055_SYS_STAT_ADDR)
			error = self._read_byte(BNO055_SYS_ERR_ADDR)
			# Return the results as a tuple of all 3 values.
			return (status, self_test, error)
		except Exception as e:
			U.logger.log(20,"", exc_info=True)

	def get_calibration_status(self):
		"""Read the calibration status of the sensors and return a 4 tuple with calibration status as follows:
		  - System, 3=fully calibrated, 0=not calibrated
		  - Gyroscope, 3=fully calibrated, 0=not calibrated
		  - Accelerometer, 3=fully calibrated, 0=not calibrated
		  - Magnetometer, 3=fully calibrated, 0=not calibrated
		"""
		# Return the calibration status register value.
		cal_status = self._read_byte(BNO055_CALIB_STAT_ADDR)
		sys = (cal_status >> 6) & 0x03
		gyro = (cal_status >> 4) & 0x03
		accel = (cal_status >> 2) & 0x03
		mag = cal_status & 0x03
		# Return the results as a tuple of all 3 values.
		return (sys, gyro, accel, mag)

	def get_calibration(self,setMode=True):
		"""Return the sensor's calibration data and return it as an array of
		22 bytes. Can be saved and then reloaded with the set_calibration function
		to quickly calibrate from a previously calculated set of calibration data.
		"""
		# Switch to configuration mode, as mentioned in section 3.10.4 of datasheet.
		if setMode:
			self._config_mode()
		# Read the 22 bytes of calibration data and convert it to a list (from
		# a bytearray) so it's more easily serialized should the caller want to
		# store it.
		cal_data = list(self._read_bytes(ACCEL_OFFSET_X_LSB_ADDR, 22))
		# Go back to normal operation mode.
		if setMode :
			self._operation_mode()
		return cal_data

	def set_calibration(self, data,setMode=True):
		"""Set the sensor's calibration data using a list of 22 bytes that
		represent the sensor offsets and calibration data.	This data should be
		a value that was previously retrieved with get_calibration (and then
		perhaps persisted to disk or other location until needed again).
		"""
		U.logger.log(10,"BEGIN: setting calibration ")
		# Check that 22 bytes were passed in with calibration data.
		if data is None or len(data) != 22:
			raise ValueError('Expected a list of 22 bytes for calibration data.')
		# Switch to configuration mode, as mentioned in section 3.10.4 of datasheet.
		if setMode:
			self._config_mode()
		# Set the 22 bytes of calibration data.
		self._write_bytes(ACCEL_OFFSET_X_LSB_ADDR, data)
		# Go back to normal operation mode.
		if setMode :
			self._operation_mode()

	def get_axis_remap(self):
		"""Return a tuple with the axis remap register values.	This will return
		6 values with the following meaning:
		  - X axis remap (a value of AXIS_REMAP_X, AXIS_REMAP_Y, or AXIS_REMAP_Z.
						  which indicates that the physical X axis of the chip
						  is remapped to a different axis)
		  - Y axis remap (see above)
		  - Z axis remap (see above)
		  - X axis sign (a value of AXIS_REMAP_POSITIVE or AXIS_REMAP_NEGATIVE
						 which indicates if the X axis values should be positive/
						 normal or negative/inverted.  The default is positive.)
		  - Y axis sign (see above)
		  - Z axis sign (see above)

		Note that by default the axis orientation of the BNO chip looks like
		the following (taken from section 3.4, page 24 of the datasheet).  Notice
		the dot in the corner that corresponds to the dot on the BNO chip:

						   | Z axis
						   |
						   |   / X axis
					   ____|__/____
		  Y axis	 / *   | /	  /|
		  _________ /______|/	 //
				   /___________ //
				  |____________|/
		"""
		# Get the axis remap register value.
		map_config = self._read_byte(BNO055_AXIS_MAP_CONFIG_ADDR)
		z = (map_config >> 4) & 0x03
		y = (map_config >> 2) & 0x03
		x = map_config & 0x03
		# Get the axis remap sign register value.
		sign_config = self._read_byte(BNO055_AXIS_MAP_SIGN_ADDR)
		x_sign = (sign_config >> 2) & 0x01
		y_sign = (sign_config >> 1) & 0x01
		z_sign = sign_config & 0x01
		# Return the results as a tuple of all 3 values.
		return (x, y, z, x_sign, y_sign, z_sign)

	def set_axis_remap(self, x, y, z,
					   x_sign=AXIS_REMAP_POSITIVE, y_sign=AXIS_REMAP_POSITIVE,
					   z_sign=AXIS_REMAP_POSITIVE):
		"""Set axis remap for each axis.  The x, y, z parameter values should
		be set to one of AXIS_REMAP_X, AXIS_REMAP_Y, or AXIS_REMAP_Z and will
		change the BNO's axis to represent another axis.  Note that two axises
		cannot be mapped to the same axis, so the x, y, z params should be a
		unique combination of AXIS_REMAP_X, AXIS_REMAP_Y, AXIS_REMAP_Z values.

		The x_sign, y_sign, z_sign values represent if the axis should be positive
		or negative (inverted).

		See the get_axis_remap documentation for information on the orientation
		of the axises on the chip, and consult section 3.4 of the datasheet.
		"""
		# Switch to configuration mode.
		self._config_mode()
		# Set the axis remap register value.
		map_config = 0x00
		map_config |= (z & 0x03) << 4
		map_config |= (y & 0x03) << 2
		map_config |= x & 0x03
		self._write_byte(BNO055_AXIS_MAP_CONFIG_ADDR, map_config)
		# Set the axis remap sign register value.
		sign_config = 0x00
		sign_config |= (x_sign & 0x01) << 2
		sign_config |= (y_sign & 0x01) << 1
		sign_config |= z_sign & 0x01
		self._write_byte(BNO055_AXIS_MAP_SIGN_ADDR, sign_config)
		# Go back to normal operation mode.
		self._operation_mode()

	def _read_vector(self, address, count=3):
		# Read count number of 16-bit signed values starting from the provided
		# address. Returns a tuple of the values that were read.
		data = self._read_bytes(address, count*2)
		result = [0]*count
		for i in range(count):
			result[i] = ((data[i*2+1] << 8) | data[i*2]) & 0xFFFF
			if result[i] > 32767:
				result[i] -= 65536
		return result

	def read_euler(self):
		"""Return the current absolute orientation as a tuple of heading, roll,
		and pitch euler angles in degrees.
		"""
		try:
			heading, roll, pitch = self._read_vector(BNO055_EULER_H_LSB_ADDR)
			return (heading/16.0, roll/16.0, pitch/16.0)
		except Exception as e:
			U.logger.log(20,"", exc_info=True)
		return 0,0,0
		
	def read_magnetometer(self):
		"""Return the current magnetometer reading as a tuple of X, Y, Z values
		in micro-Teslas.
		"""
		try:
			x, y, z = self._read_vector(BNO055_MAG_DATA_X_LSB_ADDR)
			return (x/16.0, y/16.0, z/16.0)
		except Exception as e:
			U.logger.log(20,"", exc_info=True)
		return 0,0,0

	def read_gyroscope(self):
		"""Return the current gyroscope (angular velocity) reading as a tuple of
		X, Y, Z values in degrees per second.
		"""
		try:
			x, y, z = self._read_vector(BNO055_GYRO_DATA_X_LSB_ADDR)
			return (x/900.0, y/900.0, z/900.0)
		except Exception as e:
			U.logger.log(20,"", exc_info=True)
		return 0,0,0

	def read_accelerometer(self):
		"""Return the current accelerometer reading as a tuple of X, Y, Z values
		in meters/second^2.
		"""
		try:
			x, y, z = self._read_vector(BNO055_ACCEL_DATA_X_LSB_ADDR)
			return (x/100.0, y/100.0, z/100.0)
		except Exception as e:
			U.logger.log(20,"", exc_info=True)
		return 0,0,0

	def read_linear_acceleration(self):
		"""Return the current linear acceleration (acceleration from movement,
		not from gravity) reading as a tuple of X, Y, Z values in meters/second^2.
		"""
		try:
			x, y, z = self._read_vector(BNO055_LINEAR_ACCEL_DATA_X_LSB_ADDR)
			return (x/100.0, y/100.0, z/100.0)
		except Exception as e:
			U.logger.log(20,"", exc_info=True)
		return 0,0,0

	def read_gravity(self):
		"""Return the current gravity acceleration reading as a tuple of X, Y, Z
		values in meters/second^2.
		"""
		try:
			x, y, z = self._read_vector(BNO055_GRAVITY_DATA_X_LSB_ADDR)
			return (x/100.0, y/100.0, z/100.0)
		except Exception as e:
			U.logger.log(20,"", exc_info=True)
		return 0,0,0

	def read_quaternion(self):
		"""Return the current orientation as a tuple of X, Y, Z, W quaternion
		values.
		"""
		try:
			w, x, y, z = self._read_vector(BNO055_QUATERNION_DATA_W_LSB_ADDR, 4)
			# Scale values, see 3.6.5.5 in the datasheet.
			scale = (1.0 / (1<<14))
			return (x*scale, y*scale, z*scale, w*scale)
		except Exception as e:
			U.logger.log(20,"", exc_info=True)
		return 0,0,0,0

	def read_temp(self):
		"""Return the current temperature in Celsius."""
		try:
			return self._read_signed_byte(BNO055_TEMP_ADDR)
		except Exception as e:
			U.logger.log(20,"", exc_info=True)
		return 0
		
		
		
def startBNO(devId, i2cAddress):
	global BNO055sensor
	try:
		U.logger.log(30,"==== Start BNO055 ===== @ i2c= {}".format(i2cAddress)+"	 devId={}".format(devId))
		if resetPin !=-1:
			BNO055sensor[devId] = BNO055(i2cAddress=i2cAddress, resetPin=resetPin)
		else:
			BNO055sensor[devId] = BNO055(i2cAddress=i2cAddress)
		configAvailable = False
		if not BNO055sensor[devId].begin():
			time.sleep(0.5)
			if not BNO055sensor[devId].begin():
				raise RuntimeError('BEGIN: Failed to initialize BNO055! Is the sensor connected?')

		status, self_test, error = BNO055sensor[devId].get_system_status()
		U.logger.log(10,'BEGIN: System status:	  {0}'.format(status&0b01111111)+ "	   (5 is normal)")
		U.logger.log(10,'BEGIN: Self test result:	  0x{0:02X}'.format(self_test)+ " (0x0F is normal)")
		# Print out an error if system status is in error mode.
		if status == 0x01:
			U.logger.log(30,'BEGIN: System error: {0}'.format(error))
			U.logger.log(30,'BEGIN: See datasheet section 4.3.59 for the meaning.')

		# Print BNO055 software revision and other diagnostic data.
		sw, bl, accel, mag, gyro = BNO055sensor[devId].get_revision()
		U.logger.log(10,'BEGIN: Software version:	  {0}'.format(sw))
		U.logger.log(10,'BEGIN: Bootloader version: {0}'.format(bl))
		U.logger.log(10,'BEGIN: Accelerometer ID:	  0x{0:02X}'.format(accel))
		U.logger.log(10,'BEGIN: Magnetometer ID:	  0x{0:02X}'.format(mag))
		U.logger.log(10,'BEGIN: Gyroscope ID:		  0x{0:02X}\n'.format(gyro))
		if mag ==0 or accel ==0 or gyro ==0: 
				time.sleep(1)
				U.restartMyself(reason=" init not working, sensor does not report properly (IDs =0 )", doPrint=False)

	except Exception as e:
		U.logger.log(20,"", exc_info=True)
# read params
# ===========================================================================

#################################		 
def readParams():
	global sensors, sensor
	global BNO055sensor, resetPin
	global oldRaw, lastRead

	try:

		inp, inpRaw, lastRead2 = U.doRead(lastTimeStamp=lastRead)
		if inp == "": return
		if lastRead2 == lastRead: return
		lastRead   = lastRead2
		if inpRaw == oldRaw: return
		oldRaw	   = inpRaw



		externalSensor=False
		sensorsOld= copy.copy(sensors)

 
		
		U.getGlobalParams(inp)
		if "sensors"			in inp:	 sensors =				 (inp["sensors"])
		
 
		if sensor not in sensors:
			U.logger.log(30, "BNO055 is not in parameters = not enabled, stopping ina219.py" )
			exit()
			
				
		for devId in sensors[sensor]:
			U.getMAGReadParameters(sensors[sensor][devId],devId)


			try:
				if "resetPin" in sensors[sensor][devId]: 
					resetPin= int(sensors[sensor][devId]["resetPin"])
			except:
				resetPin = -1
				
			if devId not in BNO055sensor:
				startBNO(devId, G.i2cAddress)
				
		deldevID={}		   
		for devId in BNO055sensor:
			if devId not in sensors[sensor]:
				deldevID[devId]=1
		for dd in  deldevID:
			del BNO055sensor[dd]
		if len(BNO055sensor) ==0: 
			####exit()
			pass

	except Exception as e:
		U.logger.log(20,"", exc_info=True)



#################################
def getValues(devId):
	global sensor, sensors,	 BNO055sensor
	global CALlast, lastWriteCalibration, badSelfTest 
	try:
		data = {}
		for ii in range(5):
			# Read the calibration status, 0=uncalibrated and 3=fully calibrated.
			CALsys, CALgyro, CALaccel, CALmag = BNO055sensor[devId].get_calibration_status()
			status = BNO055sensor[devId]._read_byte(BNO055_SYS_STAT_ADDR)&0b01111111
			if CALsys < 2  or (CALgyro + CALaccel +CALmag) <4  or status !=0b00000101 :
				if badSelfTest > 0:
					U.logger.log(10,"CHECK STATUS: badSelfTest count= {}".format(badSelfTest)+"  not calibrated, wait and try again: {}".format({"SYS":str(CALsys),"GYR":str(CALgyro),"ACC":str(CALaccel),"MAG":str(CALmag)}))
					status, self_test, error = BNO055sensor[devId].get_system_status()
					U.logger.log(10,'CHECK STATUS: Self test result : 0x{0:02X}'.format(self_test)+ "(0x0F is normal)")
					U.logger.log(10,'CHECK STATUS: status result	  : 0x{0:b}'.format(status&0b01111111)+" (101 is normal)")
				badSelfTest +=1
				if badSelfTest > 11:
					U.restartMyself(reason="CHECK STATUS:  self test result failed 11 times", doPrint=False)
				time.sleep(0.3)
				continue
			if badSelfTest > 3:
					U.logger.log(10,"CHECK STATUS: SelfTest ok  again , badSelfTest was: {}".format(badSelfTest)+ ";  {}".format({"SYS":str(CALsys),"GYR":str(CALgyro),"ACC":str(CALaccel),"MAG":str(CALmag)}))
			badSelfTest =0
			break
			
		tt= time.time()
		if tt - lastWriteCalibration > 5: 
			BNO055sensor[devId].writeCalibrationToFile(BNO055sensor[devId].get_calibration())
			lastWriteCalibration = tt
			
		
		# Sensor temperature in degrees Celsius:
		t = BNO055sensor[devId].read_temp()

		if t < -30 or t > 80:
			data["calibration"] = {"SYS":str(CALsys),"GYR":str(CALgyro),"ACC":str(CALaccel),"MAG":str(CALmag)  }
		else:
			data["calibration"] = {"SYS":str(CALsys),"GYR":str(CALgyro),"ACC":str(CALaccel),"MAG":str(CALmag)  ,"temp":t}

		# Read the Euler angles for heading, roll, pitch (all in degrees).
		data["EULER"] = fillWithItems(BNO055sensor[devId].read_euler(),["heading","roll","pitch"],2)

		time.sleep(0.01)
		# Gravity acceleration data (i.e. acceleration just from gravity--returned
		# in meters per second squared):
		data["GRAV"] = fillWithItems(BNO055sensor[devId].read_gravity(),["x","y","z"],2)


		time.sleep(0.01)
		# Magnetometer data (in micro-Teslas):
		MAG =  fillWithItems(BNO055sensor[devId].read_magnetometer(),["x","y","z"],1)
		data["MAG"] = MAG


		time.sleep(0.01)
		# Gyroscope data (in degrees per second):
		data["GYR"] = fillWithItems(BNO055sensor[devId].read_gyroscope(),["x","y","z"],2)

		time.sleep(0.01)
		# Accelerometer data (in meters per second squared):
		data["ACC"] = fillWithItems(BNO055sensor[devId].read_accelerometer(),["x","y","z"],1)


		time.sleep(0.01)
		# Linear acceleration data (i.e. acceleration from movement, not gravity--
		# returned in meters per second squared):
		data["LIN"] = fillWithItems(BNO055sensor[devId].read_linear_acceleration(),["x","y","z"],1)

		#print data
		for xx in data:
			U.logger.log(10, (xx).ljust(11)+" {}".format(data[xx]))
		return data
	except Exception as e:
		U.logger.log(20,"", exc_info=True)
	return {"MAG":"bad"}

def fillWithItems(theList,theItems,digits):
	out={}
	for ii in range(len(theItems)):
		out[theItems[ii]] = round(theList[ii],digits)
	return out


############################################
global sensor, sensors, badSensor
global deltaX, BNO055sensor
global CALlast, lastWriteCalibration, badSelfTest, resetPin
global oldRaw,	lastRead
oldRaw					= ""
lastRead				= 0


resetPin					= -1
badSelfTest					= 0
lastWriteCalibration		= 0
CALlast						= 0
loopCount					= 0
NSleep						= 100
sensors						= {}
sensor						= G.program
quick						= False
BNO055sensor				={}
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



lastValueDefault	= {"EULER":{"heading":0,"roll":0,"pitch":0},"MAG":{"x":0,"y":0,"z":0},"GRAV":{"x":0,"y":0,"z":0},"ACC":{"x":0,"y":0,"z":0},"LIN":{"x":0,"y":0,"z":0}}
lastRead			= time.time()
G.lastAliveSend		= time.time() -1000
testDims			= ["GRAV","LIN"]
testCoords			= ["x","y","z"]
testForBadSensor	= "MAG"
lastValue			= {}
thresholdDefault	= 0.1
sumTest				={"dim":"GRAV","limits":[0,250.]}
singleTest			={"dim":"EULER","coord":"heading","limits":[-9999.,400.]}

startTime = time.time()
while True:
	try:
		tt = time.time()
		if sensor in sensors:
			skip =False
			
		if sensor in sensors:
			for devId in sensors[sensor]:
				if devId not in lastValue: lastValue[devId] = copy.copy(lastValueDefault)
				if devId not in G.threshold: G.threshold[devId] = thresholdDefault
				values = getValues(devId)
				lastValue =U.checkMGACCGYRdata(
					values,lastValue,testDims,testCoords,testForBadSensor,devId,sensor,quick,
					sumTest=sumTest,singleTest=singleTest)

		loopCount +=1

		quick = U.checkNowFile(G.program)				 
		U.echoLastAlive(G.program)

		tt= time.time()
		if tt - lastRead > 5.:	
			readParams()
			lastRead = tt
		if not quick:
			time.sleep(G.sensorLoopWait)
		
	except Exception as e:
		U.logger.log(20,"", exc_info=True)
		time.sleep(5.)

try: 	G.sendThread["run"] = False; time.sleep(1)
except: pass
sys.exit(0)
