# -*- coding: utf-8 -*
"""
	@file	DFRobot_DF2301Q.py
	@note	DFRobot_DF2301Q Class infrastructure, implementation of underlying methods
	@copyright	Copyright (c) 2010 DFRobot Co.Ltd (http://www.dfrobot.com)
	@licence	The MIT License (MIT)
	@author	[qsjhyy](yihuan.huang@dfrobot.com)
	@version	V1.0
	@date	2022-12-30
	@url	https://github.com/DFRobot/DFRobot_DF2301Q
	madified / adapted by KW Nov 2024
	adopted by Karl Wachs
"""
version			= 1.4

import serial

import logging
import sys, os, time, json, datetime, subprocess, copy
import smbus

sys.path.append(os.getcwd())
import	piBeaconUtils	as U
import	piBeaconGlobals as G
try:
	import gpiozero
	k_useGPIO = False
except:
	try:
		import RPi.GPIO as GPIO
		GPIO.setmode(GPIO.BCM)
		GPIO.setwarnings(False)
		k_useGPIO = True
	except: pass


try:
	import queue as queue
except:
	import Queue as queue
import threading


G.program = "DF2301Q"

GLOB_PORTownerFile					= G.homeDir+"temp/PORT.owner"
GLOB_resetFile						= G.homeDir+"temp/DF2301Q.reset"
GLOB_restartFile					= G.homeDir+"temp/DF2301Q.restart"
GLOB_commandFile					= G.homeDir+"temp/DF2301Q.cmd"
GLOB_errorFile						= G.homeDir+"temp/DF2301Q.error"
GLOB_fileToReceiveCommands 			= G.homeDir+"temp/receiveCommands.input"
GLOB_recoverymessage 				= G.homeDir+"temp/DF2301Q.recovery"
GLOB_recoveryPrevious 				= G.homeDir+"temp/DF2301Q.previousRecovery"
GLOB_commonrelayActiveFile			= G.homeDir+"temp/lastRelayReset"
GLOB_commonrelayActiveDeltaTime		= 20.
GLOB_expectResponseAfter			= 10 # seconds
GLOB_maxRestartConnections			= 5  # count
GLOB_cmdCodeForrelay				= 999

DF2301Q_I2C_sleepAfterReadWrite 	= 200 # msec
DF2301Q_UART_sleepAfterReadWrite	= 100 # msec

############ I2C ############################	start

## i2c address
DF2301Q_I2C_ADDR							= 0x64

## Address of the register for requesting command word ID
DF2301Q_I2C_REG_CMDID						= 0x02
## Address of the register for playing audio by command word ID
DF2301Q_I2C_REG_PLAY_CMDID					= 0x03
## Register for setting mute mode
DF2301Q_I2C_REG_SET_MUTE					= 0x04
## Register for setting volume
DF2301Q_I2C_REG_SET_VOLUME					= 0x05
## Address of the register for wake-up time
DF2301Q_I2C_REG_WAKE_TIME					= 0x06

# tail
DF2301Q_I2C_MSG_TAIL						= 0x5A
############ I2C ############################	end



############ UART ##########################	start
## UART baud rate
DF2301Q_UART_BAUDRATE						= 9600
## Maximum data length of serial data frame
DF2301Q_UART_MSG_DATA_MAX_SIZE				= 8

# header
DF2301Q_UART_MSG_HEAD_LOW					= 0xF4
DF2301Q_UART_MSG_HEAD_HIGH					= 0xF5
DF2301Q_UART_MSG_HEAD						= 0xF5F4
# tail
DF2301Q_UART_MSG_TAIL						= 0xFB

# msg_type
DF2301Q_UART_MSG_TYPE_CMD_UP				= 0xA0 ## => normal data 
DF2301Q_UART_MSG_TYPE_CMD_DOWN				= 0xA1
DF2301Q_UART_MSG_TYPE_ACK					= 0xA2
DF2301Q_UART_MSG_TYPE_NOTIFY				= 0xA3 ##other messages

# msg_cmd
## Report voice recognition results
DF2301Q_UART_MSG_CMD_ASR_RESULT				= 0x91 ## => normal data 
## Play local broadcast audio
DF2301Q_UART_MSG_CMD_PLAY_VOICE				= 0x92
## Read the serial number of FLASH
DF2301Q_UART_MSG_CMD_GET_FLASHUID			= 0x93
## Read version number
DF2301Q_UART_MSG_CMD_GET_VERSION			= 0x94
## Reset the voice module
DF2301Q_UART_MSG_CMD_RESET_MODULE			= 0x95
## Settings
DF2301Q_UART_MSG_CMD_SET_CONFIG				= 0x96
## Enter update mode
DF2301Q_UART_MSG_CMD_ENTER_OTA_MODE			= 0x97
## Event notification
DF2301Q_UART_MSG_CMD_NOTIFY_STATUS			= 0x9A ## after DF2301Q_UART_MSG_TYPE_NOTIFY	
DF2301Q_UART_MSG_CMD_ACK_COMMON				= 0xAA
# if user want add please add form DF2301Q_UART_MSG_CMD_USER_START
DF2301Q_UART_MSG_CMD_USER_START				= 0xB0

# msg_data	msg_cmd:DF2301Q_UART_MSG_CMD_PLAY_VOICE
DF2301Q_UART_MSG_DATA_PLAY_START			= 0x80
DF2301Q_UART_MSG_DATA_PLAY_PAUSE			= 0x81
DF2301Q_UART_MSG_DATA_PLAY_RESUME			= 0x82
DF2301Q_UART_MSG_DATA_PLAY_STOP				= 0x83
DF2301Q_UART_MSG_DATA_PLAY_BY_VOICEID		= 0x90
DF2301Q_UART_MSG_DATA_PLAY_BY_SEMANTIC_ID	= 0x91
DF2301Q_UART_MSG_DATA_PLAY_BY_CMD_ID		= 0x92

# msg_data	msg_cmd:DF2301Q_UART_MSG_CMD_GET_VERSION
## Serial protocol version number
DF2301Q_UART_MSG_DATA_VER_PROTOCOL			= 0x80
## SDK version number
DF2301Q_UART_MSG_DATA_VER_SDK				= 0x81
## ASR component version number
DF2301Q_UART_MSG_DATA_VER_ASR				= 0x82
## Audio pre-processing algorithm version number
DF2301Q_UART_MSG_DATA_VER_PREPROCESS		= 0x83
## Player version number
DF2301Q_UART_MSG_DATA_VER_PLAYER			= 0x84
## App version number
DF2301Q_UART_MSG_DATA_VER_APP				= 0x8A

# msg_data	msg_cmd:DF2301Q_UART_MSG_CMD_NOTIFY_STATUS
DF2301Q_UART_MSG_DATA_NOTIFY_POWERON		= 0xB0
DF2301Q_UART_MSG_DATA_NOTIFY_WAKEUPENTER	= 0xB1
DF2301Q_UART_MSG_DATA_NOTIFY_WAKEUPEXIT		= 0xB2
DF2301Q_UART_MSG_DATA_NOTIFY_PLAYSTART		= 0xB3
DF2301Q_UART_MSG_DATA_NOTIFY_PLAYEND		= 0xB4

# msg_data msg_cmd:DF2301Q_UART_MSG_CMD_SET_CONFIG
DF2301Q_UART_MSG_CMD_SET_VOLUME				= 0x80
DF2301Q_UART_MSG_CMD_SET_ENTERWAKEUP		= 0x81
DF2301Q_UART_MSG_CMD_SET_PRT_MID_RST		= 0x82
DF2301Q_UART_MSG_CMD_SET_MUTE				= 0x83
DF2301Q_UART_MSG_CMD_SET_WAKE_TIME			= 0x84
DF2301Q_UART_MSG_CMD_SET_NEEDACK			= 0x90
DF2301Q_UART_MSG_CMD_SET_NEEDSTRING			= 0x91
# ACK error code
DF2301Q_UART_MSG_ACK_ERR_NONE				= 0x00
DF2301Q_UART_MSG_ACK_ERR_CHECKSUM			= 0xFF
DF2301Q_UART_MSG_ACK_ERR_NOSUPPORT			= 0xFE

DF2301Q_UART_PORT_NAME						= "serial0"

############ UART ##########################	end


"""
26-22:14:49 DF2301Q           _recv_packet           L:544  Lv:20 data_rev_count:2, cmd_ID:0,  msg:['', '0200a39a0300b2f201fb']
26-22:14:49 DF2301Q           _recv_packet           L:546  Lv:20    #:0,  length:2, types:00,  ids:a3; cmds:9a, data:00b2  <--- wakeup exit
26-22:39:10 DF2301Q           _recv_packet           L:552  Lv:20 data_rev_count:2, cmd_ID:0,  msg:['0200A39A0000B0ED01FB']
26-22:39:10 DF2301Q           _recv_packet           L:554  Lv:20    #:0,  lenght:2, types:00,  ids:A3; cmds:9A, data:00B0   <-- powwr on

"""



class DFRobot_DF2301Q_I2C():

	def __init__(self, i2c_addr=DF2301Q_I2C_ADDR, bus=1, sleepAfterWrite=DF2301Q_I2C_sleepAfterReadWrite):
		"""Constructor for the DFRobot DF2301Q I2C voice-recognition module driver; stores the I2C address, opens an smbus connection on the given bus, and sets the debug level and post-write sleep delay (converted from ms to seconds).

		Inputs:
		    i2c_addr (int): I2C address of the DF2301Q module
		    bus (int): I2C bus number to open
		    sleepAfterWrite (float): Delay in milliseconds to wait after each write
		Outputs:
		    None: Initializes instance attributes and opens the smbus.SMBus connection
		"""
		self._addr = i2c_addr
		self._i2c = smbus.SMBus(bus)
		self.debug = 0
		self.sleepAfterWrite = sleepAfterWrite/1000.
		#super(DFRobot_DF2301Q_I2C, self).__init__()

	def set_Params(self, sleepAfterWrite=DF2301Q_I2C_sleepAfterReadWrite, logLevel=0, commandList={}):
		"""Updates runtime parameters of the driver: sets the debug/log level and the post-write sleep delay (converted from ms to seconds), optionally logging the values.

		Inputs:
		    sleepAfterWrite (float): Delay in milliseconds to wait after each write
		    logLevel (int): Debug verbosity level
		    commandList (dict): Command list (accepted but unused)
		Outputs:
		    int: Always returns 0
		"""
		self.debug = int(logLevel)
		self.sleepAfterWrite = sleepAfterWrite/1000.
		if self.debug > 1: U.logger.log(20, "sleepAfterWrite:{}, logLevel:{}".format(sleepAfterWrite, logLevel) )
		return 0

	def get_CMDID(self):
		"""Reads the recognized command ID register from the DF2301Q module after a short delay; returns the command ID (0 means nothing new was recognized).

		Inputs:
		    None.
		Outputs:
		    int: Recognized command ID, or 0 if nothing new
		"""
		time.sleep(0.05)	 # Prevent the access rate from interfering with other functions of the voice module
		CMDID =  self._read_reg(DF2301Q_I2C_REG_CMDID)  # 0 = nothig new
		if self.debug > 1 and CMDID > 0: U.logger.log(20,": {}".format(CMDID))
		return CMDID # == 0  nothing new

	def play_CMDID(self, CMDID):
		# note Can enter wake-up state through ID = 1 in I2C mode
		"""Triggers the module to play/announce a given command ID by writing it to the play-command register, then waits one second.

		Inputs:
		    CMDID (int): Command ID to play
		Outputs:
		    int: Always returns 0
		"""
		if self.debug > 1: U.logger.log(20,": {}".format(CMDID))
		self._write_reg(DF2301Q_I2C_REG_PLAY_CMDID, CMDID)
		time.sleep(1)
		return 0

	def set_wakeup(self):
		"""Forces the module into wake-up state by writing command ID 1 to the play-command register.

		Inputs:
		    None.
		Outputs:
		    int: Always returns 0
		"""
		if self.debug > 1: U.logger.log(20,":")
		self._write_reg(DF2301Q_I2C_REG_PLAY_CMDID, 1)
		return 0

	def get_wake_time(self):
		"""Reads and returns the module's current wake-up duration from the wake-time register.

		Inputs:
		    None.
		Outputs:
		    int: Wake time value read from the register
		"""
		wktime =  self._read_reg(DF2301Q_I2C_REG_WAKE_TIME)
		if self.debug > 1: U.logger.log(20,": {}".format(wktime))
		return wktime
		return 0

	def set_wake_time(self, wake_time):
		"""Sets the module's wake-up duration by writing the low byte of the supplied value to the wake-time register.

		Inputs:
		    wake_time (int): Wake time value to set (low byte written)
		Outputs:
		    int: Always returns 0
		"""
		if self.debug > 1: U.logger.log(20,": {}".format(wake_time))
		self._write_reg(DF2301Q_I2C_REG_WAKE_TIME, wake_time & 0xFF)
		return 0

	def set_volume(self, vol):
		"""Sets the module's speaker volume, clamping the integer value to the range 0-20 before writing it to the volume register.

		Inputs:
		    vol (int): Desired volume, clamped to 0-20
		Outputs:
		    int: Always returns 0
		"""
		v = int(vol)
		if self.debug > 1: U.logger.log(20,": {}".format(v))
		self._write_reg(DF2301Q_I2C_REG_SET_VOLUME, max(0,min(v,20)))
		return 0

	def set_mute_mode(self, mode, calledFrom=""):
		"""Sets the module's mute mode, normalizing any nonzero value to 1, and writes it to the mute register.

		Inputs:
		    mode (int): Mute mode; nonzero treated as 1 (muted)
		    calledFrom (str): Caller identifier used only for logging
		Outputs:
		    int: Always returns 0
		"""
		m = int(mode)
		if 0 != m:
			m = 1
		if self.debug > 1: U.logger.log(20,": {} from:{}".format(m, calledFrom))
		self._write_reg(DF2301Q_I2C_REG_SET_MUTE, m)
		return 0

	def _write_reg(self, reg, data):
		"""Low-level helper that writes a register on the DF2301Q over I2C; wraps a single int into a list and writes it as a block, then sleeps for the configured post-write delay.

		Inputs:
		    reg (int): Register address to write
		    data (int or list): Byte value or list of bytes to write
		Outputs:
		    None: Writes block data to the I2C bus and sleeps
		"""
		if isinstance(data, int):
			data = [data]
		if self.debug > 2: U.logger.log(20,": {}->{}".format(reg, data))
		self._i2c.write_i2c_block_data(self._addr, reg, data)
		time.sleep(self.sleepAfterWrite)

	def _read_reg(self, reg):
		"""Low-level helper that reads a single byte from the given register over I2C and returns it.

		Inputs:
		    reg (int): Register address to read
		Outputs:
		    int: First byte read from the register
		"""
		ret =  self._i2c.read_i2c_block_data(self._addr, reg, 1)
		if self.debug > 2: U.logger.log(20,": ret:{}".format(ret))
		return ret[0]
		#time.sleep(self.sleepAfterWrite)

	def reset_module(self):
		"""Stub for the I2C interface variant; resetting the module is unsupported, so it merely logs an informational message that reset is not implemented.

		Inputs:
		    None.
		Outputs:
		    None: logs that reset is not implemented for the I2C interface
		"""
		U.logger.log(20,": reset not implemented for i2c interface")

	def set_need_ack(self):
		"""Stub for the I2C interface variant; setting the need-ack flag is unsupported, so it merely logs an informational message that the feature is not implemented.

		Inputs:
		    None.
		Outputs:
		    None: logs that set_need_ack is not implemented for the I2C interface
		"""
		U.logger.log(20,": set_need_ack not implemented for i2c interface")

	def set_need_string(self):
		"""Stub for the I2C interface variant; setting the need-string flag is unsupported, so it merely logs an informational message that the feature is not implemented.

		Inputs:
		    None.
		Outputs:
		    None: logs that set_need_string is not implemented for the I2C interface
		"""
		U.logger.log(20,": set_need_string not implemented for i2c interface")

	def close_Port(self):
		"""Stub for the I2C interface variant; closing the port is unsupported, so it merely logs an informational message that the feature is not implemented.

		Inputs:
		    None.
		Outputs:
		    None: logs that close_Port is not implemented for the I2C interface
		"""
		U.logger.log(20,": close_Port not implemented for i2c interface")
	

##############  uart (serial) class #########
class DFRobot_DF2301Q_UART():

	#  this is just the squence number of the data bytes received has no further meaning
	REV_STATE_HEAD0		= 0x00
	REV_STATE_HEAD1		= 0x01
	REV_STATE_LENGTH0 	= 0x02
	REV_STATE_LENGTH1 	= 0x03
	REV_STATE_TYPE		= 0x04
	REV_STATE_CMD		= 0x05
	REV_STATE_SEQ		= 0x06
	REV_STATE_DATA		= 0x07
	REV_STATE_CKSUM0	= 0x08
	REV_STATE_CKSUM1	= 0x09
	REV_STATE_TAIL		= 0x0a

	class uart_msg():
		"""!
			@brief Class for serial data frame struct
		"""
		def __init__(self):
			"""!
				@brief sensor_status structure init
			"""
			self.header = 0
			self.data_length = 0
			self.msg_type = 0
			self.msg_cmd = 0
			self.msg_seq = 0
			self.msg_data = [0] * 8

	def __init__(self, serialPortName=DF2301Q_UART_PORT_NAME, sleepAfterWrite=DF2301Q_UART_sleepAfterReadWrite ):
		"""!
			@brief Module UART communication init
		"""
		self.sleepAfterWrite = sleepAfterWrite/1000.
		self.debug = 0
		self.uart_cmd_ID = 0
		self._send_sequence = 0
		self.commandList = {}
		self._ser = serial.Serial("/dev/"+serialPortName, baudrate=DF2301Q_UART_BAUDRATE, bytesize=8, parity='N', stopbits=1, timeout=0.1)
		if self._ser.isOpen:
			self.close_Port()

		self._ser.open()
		self.messagesSend = []
		super(DFRobot_DF2301Q_UART, self).__init__()
		#self.reset_module()
		self.startTime = time.time()

	def close_Port(self):
		"""Closes the underlying serial port for the UART interface variant, closing the connection if it is currently open.

		Inputs:
		    None.
		Outputs:
		    None: closes the open serial port
		"""
		if self._ser.isOpen:
			self._ser.close()
		return 

	def set_Params(self, sleepAfterWrite=0, logLevel=-1, commandList={}):
		"""Updates the driver's configuration: optionally sets the debug log level, the post-write sleep delay (converting from milliseconds to seconds), and the command list. Errors are caught and logged.

		Inputs:
		    sleepAfterWrite (int): delay in milliseconds applied after a write, stored as seconds
		    logLevel (int): debug log level; -1 leaves it unchanged
		    commandList (dict): command mapping copied into the driver; empty dict leaves it unchanged
		Outputs:
		    None: updates self.debug, self.sleepAfterWrite, and self.commandList
		"""
		try:
			if logLevel != -1:
				self.debug = int(logLevel)

			if sleepAfterWrite != 0:
				self.sleepAfterWrite = sleepAfterWrite/1000. # set in msecs by calling program

			if commandList != {}:
				self.commandList = copy.copy(commandList)

			if self.debug > 1: U.logger.log(20, "sleepAfterWrite:{}, logLevel:{} ".format(sleepAfterWrite, logLevel) )

		except Exception as e:
			U.logger.log(20, "in Line {} has error={}".format(sys.exc_info()[-1].tb_lineno, e))


	def get_CMDID(self):
		"""!
			@brief Get the ID corresponding to the command word
			@return Return the obtained command word ID, returning 0 means no valid ID is obtained
		"""
		data_rev_count, allChar = self._recv_packet() # is always 1 for cmd_id 
		return self.uart_cmd_ID			# set in _recv_packet;  !=0 if new  ok data, 0 otherwise


	def set_volume(self,  set_value):
		"""Sets the device output volume by sending the SET_VOLUME UART command, clamping the integer value to the range 0-20.

		Inputs:
		    set_value (int): desired volume, clamped to 0-20
		Outputs:
		    object: result of setting_CMD sending the SET_VOLUME command
		"""
		v = int(set_value)
		if self.debug > 1: U.logger.log(20, "value:{}".format(v) )
		return self.setting_CMD( DF2301Q_UART_MSG_CMD_SET_VOLUME, max(0,min(v,20)))


	def set_mute_mode(self,  set_value, calledFrom=""):
		"""Enables or disables mute mode by sending the SET_MUTE UART command with a boolean derived from set_value (nonzero means mute).

		Inputs:
		    set_value (int): mute flag; nonzero enables mute
		    calledFrom (str): optional caller identifier used only for debug logging
		Outputs:
		    object: result of setting_CMD sending the SET_MUTE command
		"""
		m = 0 != int(set_value)
		if self.debug > 1: U.logger.log(20,": {}, from:{}".format(m, calledFrom))
		return self.setting_CMD( DF2301Q_UART_MSG_CMD_SET_MUTE, m)


	def set_wake_time(self,  set_value):
		"""Sets the wake-up duration by sending the SET_WAKE_TIME UART command with the value masked to a single byte (0xFF).

		Inputs:
		    set_value (int): wake time, masked to the low byte
		Outputs:
		    object: result of setting_CMD sending the SET_WAKE_TIME command
		"""
		if self.debug > 1: U.logger.log(20, "value:{}".format(set_value) )
		return self.setting_CMD( DF2301Q_UART_MSG_CMD_SET_WAKE_TIME, set_value & 0xFF)


	def set_wakeup(self):
		"""Forces the device into wake-up mode by sending the SET_ENTERWAKEUP UART command with value 1.

		Inputs:
		    None.
		Outputs:
		    object: result of setting_CMD sending the SET_ENTERWAKEUP command
		"""
		if self.debug > 1: U.logger.log(20, "value:{}".format(1) )
		return self.setting_CMD( DF2301Q_UART_MSG_CMD_SET_ENTERWAKEUP, 1)



	def set_need_ack(self): 
		"""Enables acknowledgement responses on the UART interface by sending the SET_NEEDACK command with value 1.

		Inputs:
		    None.
		Outputs:
		    object: result of setting_CMD sending the SET_NEEDACK command
		"""
		if self.debug > 1: U.logger.log(20, "value:{}".format(1) )
		return self.setting_CMD( DF2301Q_UART_MSG_CMD_SET_NEEDACK, 1)


	def set_need_string(self): 
		"""Enables string responses on the UART interface by sending the SET_NEEDSTRING command with value 1.

		Inputs:
		    None.
		Outputs:
		    object: result of setting_CMD sending the SET_NEEDSTRING command
		"""
		if self.debug > 1: U.logger.log(20, "value:{}".format(1) )
		return self.setting_CMD( DF2301Q_UART_MSG_CMD_SET_NEEDSTRING, 1)



	def setting_CMD(self, set_type, set_value):
		"""!
			@brief Set commands of the module
			@param set_type - Set type
			@n			 DF2301Q_UART_MSG_CMD_SET_VOLUME : Set volume, the set value range 1-7  # uart is from 0-20 ???
			@n			 DF2301Q_UART_MSG_CMD_SET_ENTERWAKEUP : Enter wake-up state; set value 0  #### does not work
			@n			 DF2301Q_UART_MSG_CMD_SET_MUTE : Mute mode; set value 1: mute, 0: unmute
			@n			 DF2301Q_UART_MSG_CMD_SET_WAKE_TIME : Wake-up duration; the set value range 0-255  ### does not work 
			@param set_value - Set value, refer to the set type above for the range
		"""
		msg = self.uart_msg()
		msg.msg_type = DF2301Q_UART_MSG_TYPE_CMD_DOWN
		msg.msg_cmd = DF2301Q_UART_MSG_CMD_SET_CONFIG
		msg.msg_seq = self._send_sequence
		self._send_sequence += 1
		msg.msg_data[0] = set_type
		msg.msg_data[1] = set_value
		msg.data_length = 2

		if self.debug > 2: U.logger.log(20, "msg:{}".format(vars(msg)) )
		return self._send_packet(msg)


	def setting_CMD_UP(self):
		"""Builds an ASR-result CMD_UP UART message with an incrementing send sequence and two zero data bytes, then transmits it to the DF2301Q voice module via _send_packet.

		Inputs:
		    None.
		Outputs:
		    int: Result of _send_packet (0/1 status), or 1 on exception
		"""
		try:
			msg = self.uart_msg()
			msg.msg_type = DF2301Q_UART_MSG_TYPE_CMD_UP
			msg.msg_cmd = DF2301Q_UART_MSG_CMD_ASR_RESULT
			msg.msg_seq = self._send_sequence
			self._send_sequence += 1
			msg.msg_data[0] = 0
			msg.msg_data[1] = 0
			msg.data_length = 2
	
			if self.debug > 2: U.logger.log(20, "msg:{}".format(vars(msg)) )
			return self._send_packet(msg)
		except Exception as e:
			U.logger.log(20, "in Line {} has error={}".format(sys.exc_info()[-1].tb_lineno, e))
		return 1

	def set_notify_Status(self): # does not work
		"""Sends a NOTIFY-status setting command to the module requesting wakeup-enter notifications by calling setting_Notify with the appropriate type/cmd/value constants (noted as not working).

		Inputs:
		    None.
		Outputs:
		    None: Sends a notify-setting packet to the UART module
		"""
		if self.debug > 1: U.logger.log(20, "")
		#self.setting_Notify( DF2301Q_UART_MSG_TYPE_CMD_DOWN, DF2301Q_UART_MSG_CMD_GET_VERSION, DF2301Q_UART_MSG_DATA_VER_PROTOCOL)
		#self.setting_Notify( DF2301Q_UART_MSG_CMD_PLAY_VOICE, 0)
		self.setting_Notify( DF2301Q_UART_MSG_TYPE_NOTIFY, DF2301Q_UART_MSG_CMD_NOTIFY_STATUS, DF2301Q_UART_MSG_DATA_NOTIFY_WAKEUPENTER)


	def setting_Notify(self, set_type, set_cmd, set_value):
		"""!
			@brief Set commands of the module
		"""
		msg = self.uart_msg()
		msg.msg_type = set_type
		msg.msg_cmd = set_cmd
		msg.msg_seq = self._send_sequence
		self._send_sequence += 1
		msg.msg_data[0] = set_value
		msg.msg_data[1] = 0
		msg.data_length = 2

		if self.debug > 2: U.logger.log(20, "msg:{}".format(vars(msg)) )
		return self._send_packet(msg)



	def get_wakeTime(self): #dummy not done yet
		"""Placeholder/stub for retrieving the module wake time; currently unimplemented and does nothing.

		Inputs:
		    None.
		Outputs:
		    None: No operation; returns nothing
		"""
		return 




	def play_CMDID(self, CMDID):
		"""!
			@brief Play the corresponding reply audio according to the command word ID
			@param CMDID - Command word ID
		"""
		if self.debug > 1: U.logger.log(20, "value:{}".format(CMDID) )
		msg = self.uart_msg()
		msg.msg_type = DF2301Q_UART_MSG_TYPE_CMD_DOWN
		msg.msg_cmd = DF2301Q_UART_MSG_CMD_PLAY_VOICE
		msg.msg_seq = self._send_sequence
		self._send_sequence += 1
		msg.msg_data[0] = DF2301Q_UART_MSG_DATA_PLAY_START
		msg.msg_data[1] = DF2301Q_UART_MSG_DATA_PLAY_BY_CMD_ID
		msg.msg_data[2] = CMDID
		msg.data_length = 3

		return self._send_packet(msg)


	def reset_module(self):
		"""!
			@brief Reset the module
		"""
		try:
			if self.debug > 1: U.logger.log(20, "value:{}".format("") )
			msg = self.uart_msg()
			msg.msg_type = DF2301Q_UART_MSG_TYPE_CMD_DOWN
			msg.msg_cmd = DF2301Q_UART_MSG_CMD_RESET_MODULE
			msg.msg_seq = self._send_sequence
			self._send_sequence += 1
			msg.msg_data[0] = ord('r')
			msg.msg_data[1] = ord('e')
			msg.msg_data[2] = ord('s')
			msg.msg_data[3] = ord('e')
			msg.msg_data[4] = ord('t')
			msg.data_length = 8

			U.logger.log(20, "reset_module msg:{}".format(msg.msg_data))
			return self._send_packet(msg)
		except Exception as e:
			U.logger.log(20, "in Line {} has error={}".format(sys.exc_info()[-1].tb_lineno, e))
		return  1

	def _send_packet(self, msg):
		"""
			@brief Write data through UART
			@param msg - Data packet to be sent
		"""
		try:
			chk_sum = 0x0000
			data = []
			data.append(DF2301Q_UART_MSG_HEAD_LOW & 0xFF)
			data.append(DF2301Q_UART_MSG_HEAD_HIGH & 0xFF)
			data.append(msg.data_length & 0xFF)
			data.append((msg.data_length >> 8) & 0xFF)
			data.append(msg.msg_type & 0xFF)
			chk_sum += msg.msg_type
			data.append(msg.msg_cmd & 0xFF)
			chk_sum += msg.msg_cmd
			data.append(msg.msg_seq & 0xFF)
			chk_sum += msg.msg_seq
			for i in range(0, msg.data_length):
				try: 	data.append(msg.msg_data[i] & 0xFF)
				except:	data.append(msg.msg_data[i] ) #for a string)
				chk_sum += msg.msg_data[i]

			data.append(chk_sum & 0xFF)
			data.append((chk_sum >> 8) & 0xFF)
			data.append(DF2301Q_UART_MSG_TAIL & 0xFF)
			if self.debug > 1: U.logger.log(20,"_send_packet:#:{},  {} = {}".format(msg.msg_seq, data, str([hex(data[i]) for i in range(len(data))]).replace("'","").replace("0x","")))
			self._ser.write(data)

			self.messagesSend.append(data)
			if len(self.messagesSend) > 10:
				del self.messagesSend[0]

			time.sleep(self.sleepAfterWrite)
			return 0
		except Exception as e:
			U.logger.log(20, "in Line {} has error={}".format(sys.exc_info()[-1].tb_lineno, e))
			U.logger.log(20, "data:{}, msg:{}".format(data, str(msg.msg_data)))
		return 1



	def _recv_packet(self):
		"""
			@brief Read data through UART
			@param msg - Buffer for receiving data packet
		"""

		self.uart_cmd_ID = 0  # for next iteration
		msg = self.uart_msg()
		rev_state = self.REV_STATE_HEAD0
		receive_char = 0
		chk_sum = 0
		data_rev_count = 0
		allChar = ""
		#U.logger.log(20, "enter at:{:.2f}".format(time.time() - self.startTime ))
		if not 	self._ser.in_waiting:
			#U.logger.log(20, "leave at:{:.2f}  empty".format(time.time() - self.startTime ))
			return data_rev_count, allChar

		while self._ser.in_waiting:
			xx = self._ser.read(1)
			xxHex = xx.hex().upper()
			allChar += xxHex
			receive_char = ord(xx)
			if self.debug > 1: U.logger.log(20, "receive_char:{:3}={}, rev_state:{}".format(receive_char, xxHex, rev_state))

			if self.REV_STATE_HEAD0 == rev_state: # begin of receive of data 			== 00
				if DF2301Q_UART_MSG_HEAD_LOW == receive_char:#					== F4
					rev_state = self.REV_STATE_HEAD1

			elif self.REV_STATE_HEAD1 == rev_state :#									== 01
				if DF2301Q_UART_MSG_HEAD_HIGH == receive_char:#					== F5
					rev_state = self.REV_STATE_LENGTH0
				else:
					rev_state = self.REV_STATE_HEAD0

			elif self.REV_STATE_LENGTH0 == rev_state:#									== 02
				msg.data_length = receive_char
				rev_state = self.REV_STATE_LENGTH1

			elif self.REV_STATE_LENGTH1 == rev_state:#									== 03
				msg.data_length += receive_char << 8
				rev_state = self.REV_STATE_TYPE

			elif self.REV_STATE_TYPE == rev_state:#										== 04
				msg.msg_type = receive_char
				rev_state = self.REV_STATE_CMD

			elif self.REV_STATE_CMD == rev_state:#										== 05
				msg.msg_cmd = receive_char
				rev_state = self.REV_STATE_SEQ

			elif self.REV_STATE_SEQ == rev_state :#										== 06
				msg.msg_seq = receive_char
				if msg.data_length > 0:
					rev_state = self.REV_STATE_DATA
					data_rev_count = 0
				else:
					rev_state = self.REV_STATE_CKSUM0

			elif self.REV_STATE_DATA == rev_state : # this actual data; [0] == cmd id 	== 07
				msg.msg_data[data_rev_count] = receive_char
				data_rev_count += 1
				if msg.data_length == data_rev_count:
					rev_state = self.REV_STATE_CKSUM0

			elif self.REV_STATE_CKSUM0 == rev_state:  # chk_sum is  not used			== 08
				chk_sum = receive_char
				rev_state = self.REV_STATE_CKSUM1

			elif self.REV_STATE_CKSUM1 == rev_state:   # chk_sum is  not used			== 09
				chk_sum += receive_char << 8
				rev_state = self.REV_STATE_TAIL

			elif self.REV_STATE_TAIL == rev_state:# received the end, set the cmd id=	== 0a
				if DF2301Q_UART_MSG_TAIL == receive_char:#								== FB
					if DF2301Q_UART_MSG_TYPE_CMD_UP == msg.msg_type:#					== A0
						self.uart_cmd_ID = msg.msg_data[0]
				else:  # reset
					data_rev_count = 0
				rev_state = self.REV_STATE_HEAD0

			else: # set to begin sequence of data
				rev_state = self.REV_STATE_HEAD0

		try:

			length = []
			typ = []
			cmd = []
			chksum = []
			seq = []
			data = []
			allChar = allChar.upper().split("F4F5") #DF2301Q_UART_MSG_HEAD.hex())
			if len(allChar[0]) == 0: del allChar[0]
			responses = [0]* len(allChar)
			replySeq = [-1]* len(allChar)

			ii = -1
			if self.debug > 1: U.logger.log(20, "allChar >>{}<<".format(allChar))
			for xx in allChar:
				xx = xx[:-2] # -2, skip "FB" ==  DF2301Q_UART_MSG_TAIL
				try: 
					ll = int(xx[0:2],16)
				except: 
					if self.debug > 1: U.logger.log(20, "no int  >>{}<<".format( xx[0:2]))
					continue
				if len(xx) < 12:
					if self.debug > 1: U.logger.log(20, "bad data len:{}; >>{}<<".format(len(xx), xx))
					continue
				if len(xx) > 26:
					if self.debug > 1: U.logger.log(20, "bad data len:{}; >>{}<<".format(len(xx), xx))
					continue

				ii += 1
				#01 23 45 67 89 01 23 45 67 89 01
				#03 00 A0 91 05 67 00 25 C2 01 FB for cmdid = 103
				length.append(ll)
				typ.append(xx[4:6])					# == A0
				tt = int(typ[-1],16)				# == 
				cmd.append(xx[6:8])					# == 91
				cc =int(cmd[-1],16)
				seq.append(int(xx[8:10],16))		# == 05
				data.append(xx[10:10+ll*2])			# == 670025    ll = 3  67 --> 103 as int 
				chksum.append(xx[10+ll*2:]) 		# -- C201
				for msgSend in self.messagesSend:
					# msgSend format:  0,1=header; 2,3 = len; 4 = type; 5 = cmd; 6 = seq 8,9,.. = data; -3,-2 = chksum, -1 = tail  
					#U.logger.log(20, "seq:{}, msgSend {}  ".format(seq[-1], msgSend))
					if msgSend[6] == seq[-1]:
						#U.logger.log(20, "sequence {}  found".format(seq[-1]))
						replySeq[ii] =  seq[-1]
						break
				if replySeq[ii] == -1:
					#U.logger.log(20, "sequence {}  not found".format(seq[-1]))
					pass


				try:	iData = int(data[-1][0:2],16)
				except:	iData = 0
				try:	iData2 = int(data[-1][2:4],16)
				except:	iData2 = 0
				if tt == DF2301Q_UART_MSG_TYPE_NOTIFY:				 																				# A3 
					if  cc == DF2301Q_UART_MSG_CMD_NOTIFY_STATUS:  																					# 9A
						if   iData2 == DF2301Q_UART_MSG_DATA_NOTIFY_POWERON:		responses[ii] = 800 # power on 									# B0
						elif iData2 == DF2301Q_UART_MSG_DATA_NOTIFY_WAKEUPENTER:	responses[ii] = 801 # wake up   								# 91
						elif iData2 == DF2301Q_UART_MSG_DATA_NOTIFY_WAKEUPEXIT:		responses[ii] = 802 # wake up exit								# B2
						elif iData2 == DF2301Q_UART_MSG_DATA_NOTIFY_PLAYSTART:		responses[ii] = 803 # PLAYSTART									# B3
						elif iData2 == DF2301Q_UART_MSG_DATA_NOTIFY_PLAYEND:		responses[ii] = 804 # PLAYEND									# B4
						else:														responses[ii] = 830
					else:															responses[ii] = 840
					
				elif tt == DF2301Q_UART_MSG_TYPE_ACK:																								# A2
					if cc == DF2301Q_UART_MSG_CMD_SET_CONFIG:						responses[ii] = 820 # config command received successfully		# 96
					if cc == DF2301Q_UART_MSG_CMD_RESET_MODULE:						responses[ii] = 821 # reset module								# 95

				elif tt == DF2301Q_UART_MSG_TYPE_CMD_UP: 																							# A0
					if cc == DF2301Q_UART_MSG_CMD_ASR_RESULT:						responses[ii] = iData #  real command received					# 91

				if self.debug > 1: U.logger.log(20, "  disected: length:{:1}, typ:{:2}, tt:{}, cc:{},  cmd:{:2}; chksum:{:4}, seq:{:3d}=={:<3d}, data:{:<6} {} cmdID={} _cmd_id:{}  , resp:{}".format(length[-1], typ[-1], tt, cc, cmd[-1] , chksum[-1] , seq[-1], replySeq[-1], data[-1], data[-1][0:2], iData, self.uart_cmd_ID, responses) )


			if self.uart_cmd_ID == 0 and len(responses) > 0:
				for res in responses:
					if self.uart_cmd_ID  < res: self.uart_cmd_ID  = res

		except Exception as e:
			pass
			U.logger.log(20, "in Line {} has error={}".format(sys.exc_info()[-1].tb_lineno, e))

		try:
			if self.debug > 1 and data_rev_count > 0: 
				U.logger.log(20, "data_rev_count:{}, cmd_ID:{}, leave at:{:.2f}".format(data_rev_count, self.uart_cmd_ID, time.time() - self.startTime) )
				for ii in range(len(length)):
					U.logger.log(20, "   #:{},  length:{:1}, typ:{:2},  cmd:{:2}; chksum:{:4}, seq:{:3d}=={:<3d} replySeq?,  data:{:<6} {}, resp:{}=={} ".format(ii, length[ii], typ[ii], cmd[ii] , chksum[ii] , seq[ii], replySeq[ii], data[ii], data[ii][0:2], responses[ii],  self.commandList.get(str(responses[ii]),"") ) )
	 
		except Exception as e:
			U.logger.log(20, "in Line {} has error={}".format(sys.exc_info()[-1].tb_lineno, e))

		return data_rev_count, allChar

###############################
def	makeUsbItemList():
	"""Scans /dev via 'ls -l | grep ttyUSB' to discover connected USB serial devices and populates the global USBitems list with their device names.

	Inputs:
	    None.
	Outputs:
	    None: Populates the global USBitems list with discovered ttyUSB device names
	"""
	global USBitems
	USBitems = []
	cmd = "/bin/ls -l /dev | /usr/bin/grep ttyUSB"
	ret = subprocess.Popen(cmd,shell=True,stdout=subprocess.PIPE,stderr=subprocess.PIPE).communicate()[0].decode('utf-8')
	for line in (ret).split("\n"):
		pp = line.find("ttyUSB")
		if pp > 10:
			USBitems.append(line[pp-1:].strip().split(" ")[0])

# ===========================================================================
# read params
# ===========================================================================

###############################
def readParams():
	"""Reads the plugin parameter file and, for each changed DF2301Q device, initializes/updates all per-device globals (log level, command lists, react/error commands, learning, mute, i2c-vs-uart interface, serial port, sleep/refresh/restart timings, keep-awake, etc.), refreshes the USB and PORT-owner files, and (re)starts the sensor when needed.

	Inputs:
	    None.
	Outputs:
	    None: Returns early on no/unchanged input; otherwise updates many module globals and starts sensors
	"""
	global sensors, logDir, sensor,	 displayEnable
	global SENSOR, sensorOld
	global oldRaw, lastRead, lastRead2
	global startTime, lastMeasurement, oldi2cOrUart, oldserialPortName, keepAwake, lastkeepAwake
	global restartRepeat, refreshRepeat
	global sleepAfterWrite, oldSleepAfterWrite, commandList
	global i2cOrUart, serialPortName
	global gpioCmdForAction, gpioNumberForCmdAction, gpioInverseAction, gpioOnTimeAction, anyCmdDefined, unixCmdAction, unixCmdVoiceNo
	global lastReset, restartConnectionCounter, badSensor
	global tmpMuteOff, learningOn, expectResponse, currentMute, setWakeTime
	global GPIOZERO
	global reactOnlyToCommands, maxCommandId, minErrorCmdID, offCommand
	global gpioUsed, failedCount
	global resetGPIOClass
	global lastCommandReceived, lastValidCmdAt, ignoreSameCommands
	global restartSensor
	global allowLearning
	global commonRelayActive
	global logLevel
	
	
	try:

		inp, inpRaw, lastRead2 = U.doRead(lastTimeStamp=lastRead)
		if inp == "": return

		firstRead = False
		if len(restartSensor) == 0:
			if lastRead2 == lastRead: return
			if lastRead == 0: firstRead = True
		lastRead	 = lastRead2
		if len(restartSensor) == 0:
			if inpRaw == oldRaw: return
		oldRaw		 = inpRaw

		if type(logLevel) != type({}): logLevel = {"-1":0}

		U.getGlobalParams(inp)

		if "sensors"	in inp:	 sensors =		(inp["sensors"])

		if sensor not in sensors:
			U.logger.log(20, "{} is not in parameters = not enabled, stopping {}.py".format(G.program,G.program) )
			exit()

		initPORTownerFile(firstRead)

		makeUsbItemList()

		for devId in sensors[sensor]:
			restart = ""
			clearPORTownerFile(devId, firstRead)
			# anything new?
			newParams = False
			if devId not in sensorOld or devId in restartSensor:
				newParams = True
			else:
				for ii in sensors[sensor][devId]:
					if ii not in sensorOld[devId]:
						newParams = True
						break
					if sensors[sensor][devId][ii] != sensorOld[devId][ii]:
						newParams = True
						break
			if not newParams: continue


			if devId not in lastReset: 					lastReset[devId] 					= time.time()
			if devId not in restartConnectionCounter: 	restartConnectionCounter[devId] 	= 0
			if devId not in badSensor: 					badSensor[devId] 					= 0
			if devId not in expectResponse: 			expectResponse[devId] 				= time.time() + 999
			if devId not in learningOn: 				learningOn[devId] 					= False
			if devId not in currentMute: 				currentMute[devId] 					= "0"
			if devId not in tmpMuteOff: 				tmpMuteOff[devId] 					= 0
			if devId not in lastkeepAwake: 				lastkeepAwake[devId] 				= time.time() -999
			if devId not in restartRepeat: 				restartRepeat[devId] 				= 100
			if devId not in refreshRepeat: 				refreshRepeat[devId] 				= 200
			if devId not in sleepAfterWrite: 			sleepAfterWrite[devId] 				= 200
			if devId not in setWakeTime: 				setWakeTime[devId] 					= 200
			if devId not in serialPortName: 			serialPortName[devId] 				= ""
			if devId not in reactOnlyToCommands: 		reactOnlyToCommands[devId] 			= [x for x in range(maxCommandId)]
			if devId not in resetGPIOClass: 			resetGPIOClass[devId] 				= 999999999
			if devId not in ignoreUntilEndOfLearning:	ignoreUntilEndOfLearning[devId]		= -1
			if devId not in lastCommandReceived:		lastCommandReceived[devId]			= ""
			if devId not in lastValidCmdAt:				lastValidCmdAt[devId]				= 0
			if devId not in ignoreSameCommands:			ignoreSameCommands[devId]			= -1
			if devId not in resetGPIOClass:				resetGPIOClass[devId]				= 999999999
			if devId not in failedCount:				failedCount[devId]					= 0
			if devId not in allowLearning:				allowLearning[devId]				=  True
			if devId not in commonRelayActive:			commonRelayActive[devId]			=  False
			if devId not in logLevel:					logLevel[devId]						=  0

			if "logLevel" in sensors[sensor][devId]:
				if str(logLevel[devId]) != sensors[sensor][devId].get("logLevel","0"): upd = True
				logLevel[devId] = int(sensors[sensor][devId].get("logLevel","1"))
			else:
				logLevel[devId] = 0

			if logLevel[devId]  > 0: U.logger.log(10,"{} reading new parameters for devId:{}".format(G.program, devId) )
						
			resetGPIOClass[devId] 				= float(sensors[sensor][devId].get("resetGPIOClass",999999999))
			
			for ii in range(1,9):
				if sensors[sensor][devId].get("unixCmdAction"+str(ii),"") != "":
					unixCmdAction[ii] =  sensors[sensor][devId].get("unixCmdAction"+str(ii),"")
					try: 	unixCmdVoiceNo[ii] = int(sensors[sensor][devId].get("unixCmdVoiceNo"+str(ii),"-1"))
					except: unixCmdVoiceNo[ii] = -1
					if unixCmdAction[ii] != "": anyCmdDefined = True
			
			commandList[devId] = {}
			reactCmds = []
			errCmds = []
			if "commandList" in sensors[sensor][devId]:
				commandList[devId] = json.loads(sensors[sensor][devId].get("commandList","{}"))
				offCommandID = 255
				for ii in commandList[devId]:
					try:
						xx = int(ii)
						if xx > maxCommandId: maxCommandId = xx
						reactCmds.append(xx)
						if commandList[devId].find("off"): offCommandID = xx
					except: pass
				maxCommandId +=1

				for ii in commandList[devId]:
					try:
						xx = int(ii)
						if xx >= offCommandID: errCmds.append(xx)
					except: pass
				reactOnlyToCommands[devId] = copy.copy(reactCmds)

			if "reactOnlyToCommands" in sensors[sensor][devId]:
				xx = sensors[sensor][devId].get("reactOnlyToCommands","all")
				reactOnlyToCommands[devId] = copy.copy(reactCmds)

				if xx not in ["all",""]:
					yy = xx.split(",")
					if len(yy) > 0:
						try:
							rr = copy.copy(errCmds)
							for x in yy:
								try: 	rr.append(int(x))
								except: pass
							if len(rr) > len(errCmds): reactOnlyToCommands[devId] = rr
						except Exception as e: 
							U.logger.log(20, "devId:{}; error reactOnlyToCommands:{}   rr:{}, e:{}".format(devId, xx, rr, e) )
							pass

			allowLearning[devId] = sensors[sensor][devId].get("allowLearning", "1") == "1"

			if "ignoreSameCommands" in sensors[sensor][devId]: 
				try: ignoreSameCommands[devId] = float(sensors[sensor][devId].get("ignoreSameCommands", -1))
				except: ignoreSameCommands[devId] = -1



			restart = ""
			i2cOrUart[devId] =  sensors[sensor][devId].get("i2cOrUart","")	
			if devId not in oldi2cOrUart or (i2cOrUart[devId] != "" and oldi2cOrUart[devId] != i2cOrUart[devId]):	restart = "change in intface"
			i2cOrUart[devId]  = copy.copy(i2cOrUart[devId])

			if "restartRepeat" in sensors[sensor][devId]:
				restartRepeat[devId] = float(sensors[sensor][devId].get("restartRepeat",100.))
			else:
				restartRepeat[devId] = 100.

			if "refreshRepeat" in sensors[sensor][devId]:
				refreshRepeat[devId] = float(sensors[sensor][devId].get("refreshRepeat",50.))
			else:
				refreshRepeat[devId] = 50.


			setWakeTime[devId] = int(sensors[sensor][devId].get("setWakeTime","200") )
			commonRelayActive[devId] = sensors[sensor][devId].get("commonRelayActive","0")  == "1"

			keepAwake[devId] = sensors[sensor][devId].get("keepAwake") == "1"
			if keepAwake[devId]: 
				setWakeTime[devId] = 255
				refreshRepeat[devId] = 220.


			if i2cOrUart[devId] == "uart":
				if "uartSleepAfterWrite" in sensors[sensor][devId]:
					if devId not in oldSleepAfterWrite or (oldSleepAfterWrite[devId] != "" and sleepAfterWrite[devId] != oldSleepAfterWrite[devId]):
						upd = True
					sleepAfterWrite[devId] = float(sensors[sensor][devId].get("uartSleepAfterWrite",str(DF2301Q_UART_sleepAfterReadWrite)))
				oldSleepAfterWrite[devId] = copy.copy(sleepAfterWrite[devId])

				serialPortName[devId] =  sensors[sensor][devId].get("serialPortName", DF2301Q_UART_PORT_NAME)	
				if devId not in oldserialPortName or (serialPortName[devId] != "" and oldserialPortName[devId]  != serialPortName[devId]) :
					restart = "portname changed "
				oldserialPortName[devId]  = copy.copy(serialPortName[devId])
			else:
				if "i2cSleepAfterWrite" in sensors[sensor][devId]:
					if  devId not in oldSleepAfterWrite or (oldSleepAfterWrite[devId] != "" and  sleepAfterWrite[devId] != oldSleepAfterWrite[devId]):
						upd = True
					sleepAfterWrite[devId] = float(sensors[sensor][devId].get("i2cSleepAfterWrite",str(DF2301Q_I2C_sleepAfterReadWrite)))
				else:
					sleepAfterWrite[devId] = 50.
				oldSleepAfterWrite[devId] = copy.copy(sleepAfterWrite[devId])

			upd = ""
			if devId not in SENSOR or restart != "" or devId in restartSensor:
				failedCount[devId] = 0
				if not startSensor(devId) or devId not in SENSOR:
					U.logger.log(20,"devId:{}; start failed".format(devId) )
					if devId in SENSOR: SENSOR[devId] = ""
					continue
				restart += "devId not in SENSOR,"

			if devId not in sensorOld: 
				upd = "devId not in old present"

			elif "mute" in sensors[sensor][devId] and (upd or sensors[sensor][devId].get("mute") != sensorOld[devId].get("mute")):
				upd = "change in mute"

			elif "volume" in sensors[sensor][devId] and ( sensors[sensor][devId].get("volume") != sensorOld[devId].get("volume")):
				upd = "change in volme"

			elif "setWakeTime" in sensors[sensor][devId] and (sensors[sensor][devId].get("setWakeTime") != sensorOld[devId].get("setWakeTime")):
				upd = "change in wake time"

			prepGPIOInfoForCommands(devId, inp.get("output",{}))


			if upd != "" and logLevel[devId] > 0: U.logger.log(20,"devId:{}; upd reason:{}, serialPortName:{}, setting volume:{}, mute:{}, setWakeTime:{}, keep_awake:{}, refreshRepeat:{:.1f}, restartRepeat:{:.1f}, logLevel:{}".format(devId, upd, serialPortName[devId],  sensors[sensor][devId].get("volume"), sensors[sensor][devId].get("mute"), setWakeTime[devId], keepAwake[devId], refreshRepeat[devId], restartRepeat[devId],logLevel[devId]) )

			if upd != "":
				checkifRefreshSetup(devId, restart=restart, upd=upd)

		sensorOld = copy.copy(sensors[sensor])

		deldevID = {}			
		for devId in SENSOR:
			if devId not in sensors[sensor]:
				deldevID[devId] = 1
		for dd in	deldevID:
			SENSOR[devId].close_Port()
			del SENSOR[dd]
		if len(SENSOR) == 0:
			pass



	except Exception as e:
		U.logger.log(20, "in Line {} has error={}".format(sys.exc_info()[-1].tb_lineno, e))




#################################
def maxLogLevel():
	"""Iterates the per-device logLevel dictionary and returns the highest log level configured across all devices.

	Inputs:
	    None.
	Outputs:
	    int: Maximum log level among all devices (0 if none/error)
	"""
	global logLevel
	x = 0
	try:
		for devId in logLevel:
			if x < logLevel[devId]: x = logLevel[devId]
	except Exception as e:
		U.logger.log(20, "in Line {} has error={}".format(sys.exc_info()[-1].tb_lineno, e))

	return x
	
	
#################################
def prepGPIOInfoForCommands(devIdSelect, output):
	"""For the selected device(s), reads GPIO-for-command parameters (gpio number, command id, on-time, inverse) from the sensor config, validates and caches them in the GPIO action globals, marks GPIOs used, and builds the gpioInfoIndigoIDForMsgToReceivecommand map linking GPIO numbers to Indigo output device IDs from the output structure.

	Inputs:
	    devIdSelect (int): Specific device id to process, or 0 for all devices
	    output (dict): Output-device structure mapping devType to Indigo output device IDs and gpio info
	Outputs:
	    None: Updates GPIO action globals and the gpioInfoIndigoIDForMsgToReceivecommand mapping
	"""
	global sensors, sensor
	global SENSOR
	global gpioCmdForAction, gpioNumberForCmdAction, gpioInverseAction, gpioOnTimeAction, anyCmdDefined
	global logLevel
	global GPIOZERO, gpioUsed
	global gpioInfoIndigoIDForMsgToReceivecommand

	try:
		if devIdSelect != 0: devIdList = [devIdSelect]
		else:
			devIdList = []
			for xx in sensors[sensor]:
				devIdList.append(xx)
				
		doGpioInfoIndigoIDForMsgToReceivecommand = False
		if maxLogLevel() > 2: U.logger.log(20, "starting  devIdSelect:{}, devIds:{}".format(devIdSelect, devIdList) )
		for devId in devIdList:
			for ii in range(1,9):
				if gpioUsed[ii] == 0: 
					iis = str(ii)
					try:
						if "gpioNumberForCmdAction"+iis in sensors[sensor][devId]:
							if logLevel[devId] > 1: U.logger.log(20, "setting #{}, devId:{}".format(iis, devId) )
							changed = False
							if gpioNumberForCmdAction[ii] == "" or str(gpioNumberForCmdAction[ii])	!= sensors[sensor][devId].get("gpioNumberForCmdAction"+iis,""):
								try:	
										gpioNumberForCmdAction[ii] 		= int(sensors[sensor][devId].get("gpioNumberForCmdAction"+iis,""))
										if gpioNumberForCmdAction[ii] not in range(2,27):
											gpioNumberForCmdAction[ii]  = ""
										else:
											changed = True
											gpioUsed[ii] = 1
								except Exception as e:
									U.logger.log(20, "in Line {} has error={}".format(sys.exc_info()[-1].tb_lineno, e))
									gpioNumberForCmdAction[ii] 	= ""

							if gpioCmdForAction[ii] == "" 		or str(gpioCmdForAction[ii] ) 		!= sensors[sensor][devId].get("gpioCmdForAction"+iis,""):
								try:	
										gpioCmdForAction[ii]  			= int(sensors[sensor][devId].get("gpioCmdForAction"+iis,""))
										changed = True
										gpioUsed[ii] = 1
								except:	gpioCmdForAction[ii] = ""

							if gpioOnTimeAction[ii] == "" 		or str(gpioOnTimeAction[ii] ) 		!= sensors[sensor][devId].get("gpioOnTimeAction"+iis,""):
								try:	
										gpioOnTimeAction[ii]  			= float(sensors[sensor][devId].get("gpioOnTimeAction"+iis,""))
										changed = True
										gpioUsed[ii] = 1
								except:	gpioOnTimeAction[ii] = ""

							if gpioInverseAction[ii] == "" 		or str(gpioInverseAction[ii] ) 		!= sensors[sensor][devId].get("gpioInverseAction"+iis,""):
								try:	
										gpioInverseAction[ii]  			= sensors[sensor][devId].get("gpioInverseAction"+iis,"")
										changed = True
										gpioUsed[ii] = 1
								except:	gpioInverseAction[ii] = ""

							if logLevel[devId] > 2: U.logger.log(20, "devId:{}; checking parameters file for #{}  changed:{}; gpioNumberForCmdAction:>{}< enabled? for gpioCmdForAction:>{}<, ontime:>{}<, inverse:{} conditions: gpioInverse==0/1:{}  gpioOnTime==float:{}  gpioCmd==int:{}  gpioNumber==int:{} ".format(devId, ii,changed, gpioNumberForCmdAction[ii], gpioCmdForAction[ii], gpioOnTimeAction[ii], gpioInverseAction[ii] , gpioInverseAction[ii] in ["0","1"] , isinstance(gpioOnTimeAction[ii],float) , isinstance(gpioCmdForAction[ii], int) , isinstance(gpioNumberForCmdAction[ii], int) ) )
							if changed:
								if gpioInverseAction[ii] in ["0","1"] and isinstance(gpioOnTimeAction[ii],float) and isinstance(gpioCmdForAction[ii], int) and isinstance(gpioNumberForCmdAction[ii], int):
									gpio = gpioNumberForCmdAction[ii] 
									if logLevel[devId]  > 1: U.logger.log(20, "devId:{}; checking parameters file for #{}  gpioNumberForCmdAction:>{}< enabled? for gpioCmdForAction:>{}<, ontime:>{}<, inverse:{} ".format(devId, ii, gpio, gpioCmdForAction[ii], gpioOnTimeAction[ii], gpioInverseAction[ii]  ) )
									if gpio not in gpioInfoIndigoIDForMsgToReceivecommand: 
										gpioInfoIndigoIDForMsgToReceivecommand[gpio] = {"indigoIdOfOutputDevice":"0", "devType":"OUTPUTgpio-1"}
										doGpioInfoIndigoIDForMsgToReceivecommand = True
									anyCmdDefined = True
									# actual oenable is done when it is needed
								
					except Exception as e:
						U.logger.log(20, "in Line {} has error={}".format(sys.exc_info()[-1].tb_lineno, e))

		# prep gpioInfoIndigoIDForMsgToReceivecommand to be able to send indgoID to receivecommand, that will send send message to indigo about state of gpio 
		if doGpioInfoIndigoIDForMsgToReceivecommand and output != {}:
			for devType in output:
				if devType.find("OUTPUT") == 0:
					for indigoIdOfOutputDevice in output[devType]:
						for dev in output[devType][indigoIdOfOutputDevice]:
							if "gpio" in dev:
								gpio = int(dev["gpio"])
								if gpio in gpioInfoIndigoIDForMsgToReceivecommand:
									gpioInfoIndigoIDForMsgToReceivecommand[gpio] = {"indigoIdOfOutputDevice":indigoIdOfOutputDevice, "devType":devType}
			if maxLogLevel() > 0: U.logger.log(20, "devIdSelect:{}, gpioInfoIndigoIDForMsgToReceivecommand:{} ".format(devIdSelect, gpioInfoIndigoIDForMsgToReceivecommand))

	except Exception as e:
		U.logger.log(20, "in Line {} has error={}".format(sys.exc_info()[-1].tb_lineno, e))


#################################
def startSensor(devId):
	"""Starts (or restarts) the DF2301Q sensor for a device: closes any existing instance, then opens it over UART (checking serial0/ttyS0 or scanning USB ports, retrying and verifying via get_CMDID) or over I2C, sets params/volume, and records the accepted port in the PORT-owner file.

	Inputs:
	    devId (str): Device id whose sensor instance to start
	Outputs:
	    bool: True if started (or no work needed), False if connection failed/errored
	"""
	global sensors,sensor
	global lastRestart
	global SENSOR
	global tmpMuteOff, learningOn
	global i2cOrUart, sleepAfterWrite, serialPortName, lastkeepAwake
	global logLevel, commandList
	global lastReset, expectResponse, restartConnectionCounter
	global USBitems

	tmpMuteOff[devId] = 0

	if devId in SENSOR:
		SENSOR[devId].close_Port()
		del SENSOR[devId]
	if devId in restartSensor:
		del restartSensor[devId]
	

	usePort = ""
	if devId not in SENSOR:
		serialPortNameUse[devId] = ""
		lastkeepAwake[devId] = time.time() 
		currentMute[devId] = "0"
		learningOn[devId] = False
		restartConnectionCounter[devId] += 1
		connected = False
		if logLevel[devId] > 0: U.logger.log(20, "devId:{}; =========== starting sensor  ============= type:\"{}\", \nUSB options:{}, \nPORTownerFile:{}\n==============================\n".format(devId, i2cOrUart[devId], USBitems, readPORTownerFile()))
		try:
			if i2cOrUart[devId] == "uart":
				if sensors[sensor][devId].get("serialPortName","") in ["serial0","ttys0"]:
					usePort = cmdCheckSerialPort(devId, sensors[sensor][devId]["serialPortName"],  doNotUse=usePort)
					if usePort != "":
						for kkk in range(3):
							if connected: break
							if kkk > 0: time.sleep(3)
							try:
								SENSOR[devId] = DFRobot_DF2301Q_UART(serialPortName=usePort, sleepAfterWrite=sleepAfterWrite[devId])
							except Exception as e:
								U.logger.log(20, "devId:{}, port:{}, retry after  in Line {} has error={}".format(devId, usePort, sys.exc_info()[-1].tb_lineno, e))
								continue
								
							if logLevel[devId]> 2: U.logger.log(20, "devId:{}; after set class, setting params sleep:{}, volume:{}".format(devId, sleepAfterWrite[devId], sensors[sensor][devId]["volume"]))
							SENSOR[devId].set_Params( logLevel=logLevel[devId], commandList=commandList[devId] )
							SENSOR[devId].set_volume(int(sensors[sensor][devId]["volume"]))
	
							time.sleep(0.1)
							for kkkk in range(10):
								startTest = time.time()
								CMDID = SENSOR[devId].get_CMDID()
								if CMDID > 0:
									if logLevel[devId] > 0: U.logger.log(20, "devId:{} / port:{}   CMDID:{} received  after {:.1} secs".format(devId, usePort, CMDID, time.time() -  startTest))
									connected = True
									lastRestart	= time.time()
									updatePORTownerFile(devId, port=usePort, calledFrom="accepted port")
									time.sleep(0.1)
									break
	
								if logLevel[devId] > 1: U.logger.log(20, "devId:{} still waiting for response at {} after {:.1} secs (2)".format(devId, usePort, time.time() -  startTest ))
								time.sleep(0.5)
							
				
				
				elif len(USBitems) > 0:
					for kk in range(len(USBitems)):
						if connected: break
						if logLevel[devId]> 0: U.logger.log(20, "devId:{};  try serial port loop    doNotUse>{}<  bf cmdCheckSerialPort ==== ".format(devId, usePort))
						usePort = cmdCheckSerialPort(devId, USBitems[kk],  doNotUse=usePort)
						if logLevel[devId] > 0: U.logger.log(20, "devId:{}; cmdCheckSerialPort returned try serial port:{}, use:{}".format(devId, serialPortName[devId], usePort))
						if usePort != "":
							for kkk in range(3):
								if connected: break
								if kkk > 0: time.sleep(3)
								try:
									SENSOR[devId] = DFRobot_DF2301Q_UART(serialPortName=usePort, sleepAfterWrite=sleepAfterWrite[devId])
								except Exception as e:
									U.logger.log(20, "devId:{}, port:{}, retry after  in Line {} has error={}".format(devId, usePort, sys.exc_info()[-1].tb_lineno, e))
									if str(e).find("could not open port") > -1 and kkk == 1: # only do it after failed second time
										cycleUSBPort()
									continue
									
								if logLevel[devId]> 2: U.logger.log(20, "devId:{}; after set class, setting params sleep:{}, volume:{}".format(devId, sleepAfterWrite[devId], sensors[sensor][devId]["volume"]))
								SENSOR[devId].set_Params( logLevel=logLevel[devId], commandList=commandList[devId] )
								SENSOR[devId].set_volume(int(sensors[sensor][devId]["volume"]))
		
								time.sleep(0.1)
								for kkkk in range(10):
									startTest = time.time()
									CMDID = SENSOR[devId].get_CMDID()
									if CMDID > 0:
										if logLevel[devId]> 0: U.logger.log(20, "devId:{} / port:{}   CMDID:{} received  after {:.1} secs".format(devId, usePort, CMDID, time.time() -  startTest))
										connected = True
										lastRestart	= time.time()
										updatePORTownerFile(devId, port=usePort, calledFrom="accepted port")
										time.sleep(0.1)
										break
		
									if logLevel[devId]> 1: U.logger.log(20, "devId:{} still waiting at {} for response after {:.1} secs (1)".format(devId, usePort, time.time() -  startTest ))
									time.sleep(0.5)
									
				
				else:
						U.logger.log(20, "devId:{} no serial port found, sleep for 20 secs".format(devId ))
						updatePORTownerFile(devId, port=usePort, calledFrom="not connected port")
						time.sleep(10)
						
						
			else: # i2c
				SENSOR[devId] = DFRobot_DF2301Q_I2C(i2c_addr=DF2301Q_I2C_ADDR, sleepAfterWrite=sleepAfterWrite[devId])
				if logLevel[devId]> 0: U.logger.log(20, "devId:{}; started sensor,  i2cAddr:{}, sleep:{}".format(devId, DF2301Q_I2C_ADDR, sleepAfterWrite[devId]))
				connected = True

			if connected:
				if devId in SENSOR:
					#if logLevel[devId]> 0: U.logger.log(20, "devId:{}; commandList:{}".format(devId, str(commandList[devId])[0:100] ))
					SENSOR[devId].set_Params(sleepAfterWrite=sleepAfterWrite[devId], logLevel=logLevel[devId], commandList=commandList[devId] )
					lastRestart	= time.time()
			else:
					if logLevel[devId]> 0: U.logger.log(20, "devId:{}; not connected".format(devId))
					failedCount[devId] +=1
			
				
		except Exception as e:
			U.logger.log(20, "in Line {} has error={}".format(sys.exc_info()[-1].tb_lineno, e))
			if str(e).find("could not open port /dev/") > -1:
				data = {"sensors":{sensor:{devId:"badsenor_error:bad_port_setting_/dev/"+serialPortName[devId]}}}
				U.sendURL(data)
			SENSOR[devId].close_Port()
			del SENSOR[devId]
			failedCount[devId] +=1
			return False
	return True

###################################################################################################
# manage USB and serial ports between sensors of this type and other device types ##
###################################################################################################
def updatePORTownerFile(devId, port="x", failed="x", calledFrom=""):
	"""Records the result of a port-acquisition attempt for a device in the in-memory PORT-owner structure (setting the working port or appending a failed entry), writes it to the shared PORT-owner file, and reads it back.

	Inputs:
	    devId (str): Device id whose port-owner entry is updated
	    port (str): Working port name to store, or 'x' to skip
	    failed (str): Failed port/reason to append, or 'x'/'' to skip
	    calledFrom (str): Caller label used for logging
	Outputs:
	    dict: The PORT-owner mapping re-read from file
	"""
	global logLevel, localPORTownerFile
	try:
		if devId in localPORTownerFile:
			if port !="x":
				localPORTownerFile[devId]["ok"] = port
			if failed not in ["x",""] and failed not in localPORTownerFile[devId]["failed"]:
				localPORTownerFile[devId]["failed"].append(failed)
				
		writePORTownerFile(localPORTownerFile)
		if logLevel[devId]> 1: U.logger.log(20, "devId:{}; calledf:{}, writing   PORTownerFile:{} ".format(devId, calledFrom, localPORTownerFile))
		localPORTownerFile = readPORTownerFile()
		if logLevel[devId]> 1: U.logger.log(20, "devId:{}; calledf:{}, read back PORTownerFile:{} ".format(devId, calledFrom, localPORTownerFile))

	except Exception as e:
			U.logger.log(20, "in Line {} has error={}".format(sys.exc_info()[-1].tb_lineno, e))
	return localPORTownerFile
	
#################################
def readPORTownerFile():
	"""Reads and returns the shared PORT-owner JSON file (which tracks port ownership across device types) into the localPORTownerFile global.

	Inputs:
	    None.
	Outputs:
	    dict: Parsed PORT-owner mapping, or empty dict on error
	"""
	global logLevel, localPORTownerFile
	try:
		localPORTownerFile, xxx = U.readJson(GLOB_PORTownerFile)
		return localPORTownerFile
	except Exception as e:
			U.logger.log(20, "in Line {} has error={}".format(sys.exc_info()[-1].tb_lineno, e))
	return {}

#################################
def initPORTownerFile(firstRead):
	"""Initializes the PORT-owner file by loading it (defaulting to an empty dict) and, on the first read, resetting this program's device entries and writing the file back.

	Inputs:
	    firstRead (bool): True on the first parameter read to reset owner entries
	Outputs:
	    dict: The (possibly reset) PORT-owner mapping
	"""
	global logLevel, localPORTownerFile
	try:
		localPORTownerFile = readPORTownerFile()
		if type(localPORTownerFile) != type({}): localPORTownerFile = {}
		if firstRead: 
			for devId in localPORTownerFile:
				if "devType" == G.program:
					localPORTownerFile[devId] = {"failed":[], "ok":"", "devType":G.program}
			writePORTownerFile(localPORTownerFile)
	except Exception as e:
			U.logger.log(20, "in Line {} has error={}".format(sys.exc_info()[-1].tb_lineno, e))
	return localPORTownerFile
	
#################################
def clearPORTownerFile(devId, firstRead):
	"""Clears a device's PORT-owner entry by resetting its 'ok' port to empty (creating a default entry if missing or on first read) and writing the updated PORT-owner file.

	Inputs:
	    devId (str): Device id whose port-owner entry is cleared
	    firstRead (bool): True on first read to fully reset the device entry
	Outputs:
	    dict: The updated PORT-owner mapping
	"""
	global logLevel, localPORTownerFile
	try:
			if firstRead: localPORTownerFile[devId] = {"failed":[], "ok":"", "devType":G.program}
			if devId not in localPORTownerFile: localPORTownerFile[devId] = {"failed":[], "ok":"", "devType":G.program}
			localPORTownerFile[devId]["ok"] = ""
			writePORTownerFile(localPORTownerFile)
	except Exception as e:
			U.logger.log(20, "in Line {} has error={}".format(sys.exc_info()[-1].tb_lineno, e))
	return localPORTownerFile
	
#################################
def checkifdevIdInPORTownerFile(devId):
	"""Ensures the given device id has an entry in the in-memory localPORTownerFile dict, creating a default record (empty failed list, empty ok port, current program as devType) if absent, then persists the dict to disk.

	Inputs:
	    devId (str): Indigo device id key used in the port-owner registry
	Outputs:
	    dict: the (possibly updated) localPORTownerFile mapping
	"""
	global logLevel, localPORTownerFile
	try:
			if devId not in localPORTownerFile: localPORTownerFile[devId] = {"failed":[], "ok":"", "devType":G.program}
			writePORTownerFile(localPORTownerFile)
	except Exception as e:
			U.logger.log(20, "in Line {} has error={}".format(sys.exc_info()[-1].tb_lineno, e))
	return localPORTownerFile

#################################
def checkifIdInOKPORTownerFile(devId, findThis):
	"""Checks whether the given port/value (findThis) is currently recorded as the successfully owned ('ok') port for the device id in localPORTownerFile.

	Inputs:
	    devId (str): device id key to look up
	    findThis (str): port/value to compare against the device's stored 'ok' entry
	Outputs:
	    bool: True if findThis matches the device's ok port, else False
	"""
	global logLevel, localPORTownerFile
	try:
			if devId not in localPORTownerFile: return False
			if findThis == localPORTownerFile[devId]["ok"]: return True
			return False
	except Exception as e:
			U.logger.log(20, "in Line {} has error={}".format(sys.exc_info()[-1].tb_lineno, e))
	return False

#################################
def checkifIdInFAILEDPORTownerFile(devId, findThis):
	"""Checks whether the given port/value (findThis) appears in the device's list of previously failed ports in localPORTownerFile.

	Inputs:
	    devId (str): device id key to look up
	    findThis (str): port/value to search for in the device's 'failed' list
	Outputs:
	    bool: True if findThis is in the device's failed list, else False
	"""
	global logLevel, localPORTownerFile
	try:
			if devId not in localPORTownerFile: return False
			if findThis in localPORTownerFile[devId]["failed"]: return True
			return False
	except Exception as e:
			U.logger.log(20, "in Line {} has error={}".format(sys.exc_info()[-1].tb_lineno, e))
	return False

#################################
def getdevIdsPORTownerFile():
	"""Returns a list of all device ids currently registered as keys in the in-memory localPORTownerFile dict.

	Inputs:
	    None.
	Outputs:
	    list: list of device id keys, or empty list on error
	"""
	global logLevel, localPORTownerFile
	try:
			retList = []
			for devId in localPORTownerFile:
				retList.append(devId )
			return retList
	except Exception as e:
			U.logger.log(20, "in Line {} has error={}".format(sys.exc_info()[-1].tb_lineno, e))
	return []

#################################
def writePORTownerFile(PORTownerFile):
	"""Replaces the in-memory localPORTownerFile with a copy of the supplied dict and writes it as formatted JSON to the GLOB_PORTownerFile path.

	Inputs:
	    PORTownerFile (dict): port-owner registry mapping to store and persist
	Outputs:
	    None: updates global localPORTownerFile and writes the JSON file
	"""
	global logLevel, localPORTownerFile
	try:
		localPORTownerFile = copy.copy(PORTownerFile)
		U.writeJson(GLOB_PORTownerFile, localPORTownerFile, sort_keys=False, indent=4)
	except Exception as e:
			U.logger.log(20, "in Line {} has error={}".format(sys.exc_info()[-1].tb_lineno, e))
	return 



#################################
def cycleUSBPort():
	"""Power-cycles the Raspberry Pi USB bus by listing ttyUSB devices then unbinding and rebinding the usb driver via sudo tee, waits for recovery, clears the port-owner parameter file, and restarts the plugin program.

	Inputs:
	    None.
	Outputs:
	    None: runs shell commands to rebind USB, resets the port file, and restarts the process
	"""
	global logLevel
	try:
		cmdtty = "/bin/ls -l /dev | /usr/bin/grep ttyUSB"
		ret = subprocess.Popen(cmdtty,shell=True,stdout=subprocess.PIPE,stderr=subprocess.PIPE).communicate()[0].decode('utf-8')
		cmd = "echo '1-1' |sudo tee /sys/bus/usb/drivers/usb/unbind"
		U.logger.log(20, "cycling USB ports with : {} .. bind\n  /dev/ttyUSB:\n{} ".format(cmd, ret))
		subprocess.call(cmd, shell=True)
		time.sleep(5)
		cmd = "echo '1-1' |sudo tee /sys/bus/usb/drivers/usb/bind"
		subprocess.call(cmd, shell=True)
		time.sleep(10) # this needs some time to recover 
		initPORTownerFile(True) # clear parameters file 
		U.restartMyself(reason="power cycle USB", python3="1")

	except Exception as e:
			U.logger.log(20, "in Line {} has error={}".format(sys.exc_info()[-1].tb_lineno, e))
	return 

###################################################################################################
# manage USB and serial ports between sensors of this type and other device types   ==== END ##
###################################################################################################


#################################
def setMute(devId, ON, CMDID=0):
	"""Toggles the DF2301Q voice sensor's mute/learning behavior: when turned on during a learning window it temporarily unmutes, raises volume, and plays a command id; otherwise it restores mute to the configured value, and when turned off it ends learning mode and re-applies the configured setup.

	Inputs:
	    devId (str): device id of the sensor to configure
	    ON (bool): True to enter the unmute/learning state, False to restore configured mute
	    CMDID (int): optional command id to play on the sensor when unmuting during learning
	Outputs:
	    None: updates mute/learning globals and sends mute/volume/play commands to the sensor hardware
	"""
	global lastkeepAwake, SENSOR, tmpMuteOff, learningOn, currentMute, ignoreUntilEndOfLearning
	global logLevel
	try:

		if ON:
			if  ignoreUntilEndOfLearning[devId] > 0 and not learningOn[devId]:
				learningOn[devId] = True
				tmpMuteOff[devId] = time.time() + 100
				if logLevel[devId]> 0: U.logger.log(20, "devId:{}; set mute OFF  expires in {:.1f} secs".format(devId, tmpMuteOff[devId]-time.time()))
				if int(sensors[sensor][devId]["volume"]) < 5:
					SENSOR[devId].set_volume(10) 			# set  volume to 10 during learning
					setExpectResponse(devId)
					lastkeepAwake[devId] = time.time()
				if int(sensors[sensor][devId]["mute"]) != 0 and currentMute[devId]  == "1":
					SENSOR[devId].set_mute_mode(0, calledFrom="setMute1")
					setExpectResponse(devId)
					currentMute[devId] = "0"
					lastkeepAwake[devId] = time.time()
					if CMDID > 0: 
						SENSOR[devId].play_CMDID(CMDID)
			else:
				if currentMute[devId] != "1":
					if logLevel[devId]> 0: U.logger.log(20, "devID:{}; set mute back to 1 ".format(devId))
					SENSOR[devId].set_mute_mode(1, calledFrom="setMute2")
					currentMute[devId] = "1"
				tmpMuteOff[devId] = 0
				
		else:
			if learningOn[devId]:
				if logLevel[devId]> 0: U.logger.log(20, "devID:{}; set mute learning params back to config ".format(devId))
				tmpMuteOff[devId] = 0
				learningOn[devId] = False
				lastkeepAwake[devId] = 0
				checkifRefreshSetup(devId, upd=True)
			else:
				for devId in SENSOR:
					if currentMute[devId] != sensors[sensor][devId]["mute"]:
						SENSOR[devId].set_mute_mode(sensors[sensor][devId]["mute"], calledFrom="setMute3")
						setExpectResponse(devId)
						currentMute[devId] = sensors[sensor][devId]["mute"]

	except Exception as e:
		U.logger.log(20, "in Line {} has error={}".format(sys.exc_info()[-1].tb_lineno, e))
		U.logger.log(20, "{}".format(sensors[sensor]))
	return


#################################
def checkifRefreshSetup(devId,  restart=False, upd=False):
	"""Periodically (or on demand) re-initializes the sensor's runtime settings — mute mode, wake time/wakeup, volume, and sleep/log parameters — when the refresh interval has elapsed or a restart/update is requested, skipping while learning is active and flagging an error if the sensor responds badly.

	Inputs:
	    devId (str): device id of the sensor to refresh
	    restart (bool): force a full re-init including wake-time setup
	    upd (bool): force a refresh/update even before the interval elapses
	Outputs:
	    None: sends configuration commands to the sensor, updates mute/keepAwake state, and increments badSensor on error
	"""
	global lastkeepAwake, keepAwake, sensors, sensor, SENSOR, tmpMuteOff, learningOn
	global refreshRepeat, currentMute, badSensor, sleepAfterWrite, logLevel
	global logLevel, commandList, expectResponse, setWakeTime
	try:

		if learningOn[devId] and time.time() - tmpMuteOff[devId] > 0: learningOn[devId] = False

		if learningOn[devId]: return

		#if not keepAwake and not restart and not upd: return
		#U.logger.log(20, "check if re awake : {}, {}".format(lastkeepAwake, refreshRepeat))
		badResponse = False
		if  time.time() - lastkeepAwake[devId] > refreshRepeat[devId] or restart or upd:
			startTime = time.time()
			if True:
				if SENSOR[devId].set_mute_mode(1, calledFrom="checkifRefreshSetup1") == 1: badResponse = True
				setExpectResponse(devId)
				currentMute[devId] = "1"

			if keepAwake[devId]:
				if not badResponse and SENSOR[devId].set_wake_time(setWakeTime[devId]) == 1: badResponse = True
				setExpectResponse(devId)
				if not badResponse and SENSOR[devId].set_wakeup() == 1: badResponse= True

			if restart and not keepAwake[devId]:
				expectResponse[devId] = time.time()
				if not badResponse and SENSOR[devId].set_wake_time(setWakeTime[devId]) == 1: badResponse = True

			if True:
				setExpectResponse(devId)
				if not badResponse and SENSOR[devId].set_volume(int(sensors[sensor][devId]["volume"])) == 1: badResponse = True
				if not badResponse and SENSOR[devId].set_mute_mode(sensors[sensor][devId]["mute"], calledFrom="checkifRefreshSetup2") == 1: badResponse = True
				if not badResponse and SENSOR[devId].set_Params(sleepAfterWrite=sleepAfterWrite[devId], logLevel=logLevel[devId] ) == 1: badResponse = True
				currentMute[devId] = sensors[sensor][devId]["mute"]

			if badResponse: 
				checkErrorSend(devId, "bad send data", 900, "new, restart")		

			if logLevel[devId]> 0: U.logger.log(20, "devId:{}; (re)-init sensor, timeUsed:{:.1f}, upd:{}, restart:{}, keepAwake:{}, setWakeTime:{}, mute:{}, volume:{}, learning <0?:{:.1f}, learningOn:{} ".format(devId, time.time()-startTime,upd, restart, keepAwake[devId], setWakeTime[devId], sensors[sensor][devId]["mute"],  sensors[sensor][devId]["volume"], min(999., time.time() - tmpMuteOff[devId]) ,learningOn[devId]))
			lastkeepAwake[devId] = time.time()

	except Exception as e:
		badSensor[devId] += 1
		U.logger.log(20, "in Line {} has error={}".format(sys.exc_info()[-1].tb_lineno, e))



############ check if we expect a response soon #####################
def setNoExpectResponse(devId, calledfrom=""):
	"""Disables response-expectation timing for a device by pushing its expectResponse timestamp far into the future, resetting the reconnect counter and refreshing the keep-awake timestamp.

	Inputs:
	    devId (str): device id whose response expectation is being cleared
	    calledfrom (str): optional label of the caller, used only in log output
	Outputs:
	    None: updates expectResponse, restartConnectionCounter, and lastkeepAwake globals
	"""
	global expectResponse, restartConnectionCounter
	expectResponse[devId] = time.time() + 9999999999
	restartConnectionCounter[devId] = 0
	lastkeepAwake[devId] = time.time()
	if logLevel[devId]> 1: U.logger.log(20, "devId:{}; setting  expectResponse to {:.1f}, called from:{}".format(devId, 9999999999, calledfrom ))
	return 

#################################
def setExpectResponse(devId):
	"""Arms a response-timeout for the device by setting its expectResponse timestamp to the current time plus the configured GLOB_expectResponseAfter window.

	Inputs:
	    devId (str): device id for which a response is now expected
	Outputs:
	    None: updates the expectResponse global timestamp
	"""
	global expectResponse, logLevel
	expectResponse[devId] = time.time() + GLOB_expectResponseAfter
	if logLevel[devId]> 1: U.logger.log(20, "devId:{}; setting  expectResponse to {:.1f}".format(devId, GLOB_expectResponseAfter))

	return 

#################################
def checkExpectResponse(devId):
	"""For UART devices, checks whether an expected response has timed out and escalates accordingly: restarts the whole program after too many reconnects, otherwise restarts the connection; also triggers a setup refresh when the bad-sensor counter exceeds a threshold.

	Inputs:
	    devId (str): device id to check for an overdue response
	Outputs:
	    int: 3 if program restart triggered, 2 if connection restart, 1 if refresh-setup triggered, else 0
	"""
	global expectResponse, i2cOrUart, checkExpectResponse, restartConnectionCounter, minRestartConnectionTime

	try:
		if i2cOrUart[devId] == "uart":
		
			if expectResponse[devId] - time.time() > 0 and expectResponse[devId] - time.time() < 99: 
				if logLevel[devId]> 1: U.logger.log(20, "devId:{}; testing if response by now, time left:{:.1f} ".format(devId, - (time.time()-expectResponse[devId]) ))
		
			if time.time() - expectResponse[devId] > 0: 
				if logLevel[devId]> 0: U.logger.log(20, "devId:{}; expected a response by now, not received for:{:.1f} secs,  reconnect counter: {}".format(devId, time.time()-expectResponse[devId], restartConnectionCounter[devId] ))
				if restartConnectionCounter[devId] > GLOB_maxRestartConnections: 
					if logLevel[devId]> 0: U.logger.log(20, "devId:{}; expected a response by now,  too many reconnects, do restart of program ".format(devId))
					checkIfRestart(force=True)
					return 3
		
				if logLevel[devId]> 0: U.logger.log(20, "devId:{}; expected a response by now, not received for:{:.1f} secs, do restart connection  ".format(devId, time.time()-expectResponse[devId] ))
				checkIfRestartConnection(devId, force=True)
				return 2
	
		if badSensor[devId] > 7:
			checkifRefreshSetup(devId, restart=True , upd=True)
			return 1
	except Exception as e:
		U.logger.log(20, "in Line {} has error={}".format(sys.exc_info()[-1].tb_lineno, e))

	return 0

#################################


#################################
def checkIfRestartConnection(devId, force=False):
	"""Restarts the sensor connection when restarts are enabled (or forced) and the restart-repeat interval has elapsed, by clearing the cached port/sensor/read tracking variables and calling startSensor for each device.

	Inputs:
	    devId (str): device id (loop also iterates all devices in restartRepeat)
	    force (bool): bypass the enabled flag and interval check to force a reconnect
	Outputs:
	    None: resets connection-tracking globals and re-starts the sensor connection
	"""
	global sensorOld, oldRaw, lastRead, oldi2cOrUart, oldserialPortName
	global lastRestart, restartRepeat, restartON, SENSOR
	global logLevel, restartConnectionCounter

	try: # reset all check variables and then a read of parametes leads to a restart of the connection
		for devId in restartRepeat:
			if not restartON and not force: return
			if time.time() - lastRestart < restartRepeat[devId] and not force: return
			oldi2cOrUart[devId]			= {}
			oldserialPortName[devId]	= {}
			sensorOld[devId]			= {}
			oldRaw						= ""
			lastRead					= 0
			lastRestart					= time.time()
			startSensor(devId)
	except Exception as e:
		U.logger.log(20, "in Line {} has error={}".format(sys.exc_info()[-1].tb_lineno, e))
	return


#################################
def checkIfRestart(force=False):
	"""Checks for the presence of a restart-flag file (or a forced request) and, if found, removes it, logs the restart, and triggers a plugin restart of itself.

	Inputs:
	    force (bool): When True, restart unconditionally even if the flag file is absent
	Outputs:
	    None: removes the restart flag file, logs, and restarts the plugin process
	"""
	global logLevel
	try:
		if os.path.isfile(GLOB_restartFile): 
			os.remove(GLOB_restartFile)
		else: 
			if not force: return

		if maxLogLevel() > 0:
			if not	force:  U.logger.log(20, "==== doing restart ====, requested by plugin")
			else:	        U.logger.log(20, "==== doing restart ====, requested by program")

		U.restartMyself(param="", reason="reset_requested "+GLOB_restartFile+" exists", doPrint=True)

	except Exception as e:
		U.logger.log(20, "in Line {} has error={}".format(sys.exc_info()[-1].tb_lineno, e))
	return

#################################
def checkIfReset():
	"""Checks for a reset-flag file; if present, removes it and performs a reset of every sensor device along with restarting its connection.

	Inputs:
	    None.
	Outputs:
	    None: removes the reset flag file, resets each sensor module, and logs
	"""
	global logLevel, SENSOR
	try:
		if not os.path.isfile(GLOB_resetFile): return
		os.remove(GLOB_resetFile)

		for devId in SENSOR:
			if logLevel[devId]> 0: U.logger.log(20, "devID:{}; ==== doing reset ====, requested by plugin".format(devId ))
			doReset(devId)
			checkIfRestartConnection(devId, force=True)

	except Exception as e:
		U.logger.log(20, "in Line {} has error={}".format(sys.exc_info()[-1].tb_lineno, e))
	return

#################################
def doReset(devId, force=False):
	"""Resets the sensor module for the given device if more than 50 seconds have passed since its last reset (or if forced), recording the new reset time.

	Inputs:
	    devId (str): Device identifier whose sensor module to reset
	    force (bool): When True, reset regardless of the time-since-last-reset throttle
	Outputs:
	    bool: True if a reset was performed, False if skipped due to throttling
	"""
	global lastReset, SENSOR
	if time.time() - lastReset[devId] > 50 or force:
		U.logger.log(20, "==== doing a reset ====")
		SENSOR[devId].reset_module()
		lastReset[devId] = time.time()
		return True
	return False

#################################
def checkIfCommand():
	"""!
		read json file commandFile and execute commands read from that file
	"""
	global logLevel, SENSOR
	try:
		if not os.path.isfile(GLOB_commandFile): return
		data, ddd = U.readJson(GLOB_commandFile)
		os.remove(GLOB_commandFile)
		if len(ddd) < 3: return 
		for devId in SENSOR:
			if maxLogLevel() > 0: U.logger.log(20, "devID:{}; ==== exec commands: {}".format(devId, data))
			if "volume"		in data: 
				SENSOR[devId].set_volume(int(data["volume"]))
				getValues(devId, wait=0.1)
			if "mute"		in data: 
				SENSOR[devId].set_mute_mode(data["mute"], calledFrom="checkIfCommand")
				getValues(devId, wait=0.1)
			if "cmdid"		in data: 
				SENSOR[devId].play_CMDID(data["cmdid"])
				getValues(devId, wait=0.1)
			if "wakeup"		in data: 
				SENSOR[devId].set_wakeup()
				getValues(devId, wait=0.1)
			if "waketime"	in data: 
				SENSOR[devId].set_wake_time(data["waketime"])
				getValues(devId, wait=0.1)
			if "reset" 		in data: 
				doReset(devId,force=True)
				getValues(devId, wait=0.1)
			if "ack" 		in data: 
				SENSOR[devId].set_need_ack()
				getValues(devId, wait=0.1)
			if "string" 		in data: 
				SENSOR[devId].set_need_string()
				getValues(devId, wait=0.1)
			if "loglevel" 		in data: 
				logLevel[devId] = data["loglevel"]
				SENSOR[devId].set_Params(logLevel=logLevel[devId])
				getValues(devId, wait=0.1)
			if "connection" 	in data: 
				checkIfRestartConnection(devId, force=True)
				getValues(devId, wait=0.1)
			if "restart" 		in data: 
				checkIfRestart(force=True)
				getValues(devId, wait=0.1)

	except Exception as e:
		U.logger.log(20, "in Line {} has error={}".format(sys.exc_info()[-1].tb_lineno, e))
	return



#################################
def resetSensorRelay(devId):
	"""
		reset the connection to sensor devId
	"""
	global logLevel, SENSOR, sensors
	global i2cOrUart
	global commonRelayActive


	try:
		if os.path.isfile(GLOB_commonrelayActiveFile): 
			data, ddd = U.readJson(GLOB_commonrelayActiveFile)
			if type(data) == type({}) and data != {}: 
				if time.time() - data.get("lastrelay",0) < GLOB_commonrelayActiveDeltaTime:
					return 
		
		if U.checki2cdetect == "bad":
			U.logger.log(20, "i2c hangs, needs reset")

		if os.path.isfile(GLOB_recoveryPrevious): 
			os.remove(GLOB_recoveryPrevious)

		if os.path.isfile(GLOB_recoverymessage): 
			os.rename(GLOB_recoverymessage,GLOB_recoveryPrevious)


		startTime = time.time()
		for ii in range(8):
			if sensors[sensor][devId].get("gpioCmdForAction"+str(ii),"") == str(GLOB_cmdCodeForrelay):
				if commonRelayActive.get(devId,False):
					U.writeJson(GLOB_commonrelayActiveFile, json.dumps({"lastrelay":time.time()}))
				cmdQueue.put(GLOB_cmdCodeForrelay)
				time.sleep(6)
				break
		msg = {"devId":devId,"time":time.time()}
		U.writeJson(GLOB_recoverymessage, msg)

		if time.time() - startTime < 2: time.sleep(10)
		U.restartMyself(reason="sensor not answering", delay=0, python3=True)

	except Exception as e:
		U.logger.log(20, "in Line {} has error={}".format(sys.exc_info()[-1].tb_lineno, e))
	return
	

############################################
def sendRecoveryMessage():
	"""Sends a recovery notification by invoking sendxxRecoveryMessage with the recovered-success code 1001.

	Inputs:
	    None.
	Outputs:
	    None: delegates to sendxxRecoveryMessage(1001)
	"""
	sendxxRecoveryMessage(1001)
	return

############################################
def sendNotRecoveryMessage():
	"""Sends a not-recovered notification by invoking sendxxRecoveryMessage with the failure code 1002.

	Inputs:
	    None.
	Outputs:
	    None: delegates to sendxxRecoveryMessage(1002)
	"""
	sendxxRecoveryMessage(1002)
	return

############################################
def sendxxRecoveryMessage(code):
	"""Reads the recovery-message JSON file (if present), rotates it to the previous-recovery file, computes elapsed time since the last reset and any prior reset timestamp, then posts a recovery/not-recovered status message to the plugin via sendURL.

	Inputs:
	    code (int): Recovery status code (1001 for recovered, 1002 for not recovered)
	Outputs:
	    None: rotates recovery files, sends a URL status message, and updates lastAliveSend
	"""
	global sensor, lastAliveSend
	try:
		if not os.path.isfile(GLOB_recoverymessage): return 
		data, ddd = U.readJson(GLOB_recoverymessage)
		dataP, dddP= U.readJson(GLOB_recoveryPrevious)
		lastTime = data.get("time", time.time()-30)
		devId = data.get("devId", "")
		try: os.remove(GLOB_recoveryPrevious)
		except: pass
		os.rename(GLOB_recoverymessage, GLOB_recoveryPrevious)
		pr = dataP.get("time","")
		if pr != "":
			try:	previousReset = "_previous_Reset_@_"+datetime.datetime.fromtimestamp(pr).strftime("%Y-%m-%d %H:%M:%S")
			except: previousReset = ""
		if lastTime != "":
			try:	lastTime = "{:.1f}_secs".format(time.time()-lastTime)
			except: lastTime = ""
		if devId != "" and lastTime != "": 
			if code == 1001: 	yesNo = "" 
			else: 				yesNo = "Not_"
			errText = "{}recovered_from_sensor_reset_after_{}{}".format(yesNo, lastTime, previousReset) 
			U.sendURL({"sensors":{sensor:{devId:{"cmd":code,"errText":errText}}}}, wait=False)
			lastAliveSend[devId] = time.time()
	except Exception as e:
		U.logger.log(20, "in Line {} has error={}".format(sys.exc_info()[-1].tb_lineno, e))
	return



#################################
def getValues(devId, wait=0.):
	"""Reads the latest command ID (CMDID) from the sensor, handling bad-sensor retries, learning-mode entry/exit, keep-awake/refresh logic, and reset commands; returns a dict describing the accepted command or a bad-sensor marker.

	Inputs:
	    devId (str): Device identifier of the sensor to read
	    wait (float): Seconds to sleep before reading the sensor
	Outputs:
	    dict or str: {'cmd': CMDID} on success/idle, or the string 'badSensor' / '' on repeated read failures
	"""
	global sensor, sensors,	 SENSOR, badSensor, tmpMuteOff, learningOn
	global keepAwake
	global commandList, lastkeepAwake
	global i2cOrUart
	global cmdQueue, anyCmdDefined
	global logLevel, firstCmdReceived
	global reactOnlyToCommands, ignoreUntilEndOfLearning
	global lastCommandReceived, lastValidCmdAt, ignoreSameCommands
	global startTime
	global allowLearning

	try:
		#if logLevel[devId]> 0: U.logger.log(20, "devID:{}; enter getValues time:{:.2f}".format(devId, time.time() - startTime))
		CMDID = 0
		if wait > 0: time.sleep(wait)

		if devId not in SENSOR:
			if devId not in badSensor: badSensor[devId] = 0
			badSensor[devId] += 1
			return "badSensor"

		for ii in range(3):
			if ii > 0: time.sleep(0.1) 
			try:
				CMDID = SENSOR[devId].get_CMDID()
			except Exception as e:
				if ii > 0:
					if logLevel[devId]> 0: U.logger.log(20, "devID:{}; error in received CMDID: {:3d}, badSensorCount:{}, error:{}".format(devId, CMDID, badSensor[devId], e)  )
					badSensor[devId] += 1
					if badSensor[devId] > 2:
						checkifRefreshSetup(devId, restart=badSensor[devId] > 0, upd=True)
					if badSensor[devId] >= 5: return "badSensor"
					return {"cmd":0}
			if CMDID > 0: break

		#if logLevel[devId]> 0: U.logger.log(20, "devId:{}; step2  getValues time:{:.2f}".format(devId, time.time() - startTime))

		if CMDID == 0:
			checkExpectResponse(devId)
			return {"cmd":CMDID}

		# received some response, reset check for response
		setNoExpectResponse(devId, calledfrom="cmdid={}".format(CMDID))
		restartConnectionCounter[devId] = 0
		firstCmdReceived = True

		accept = False
		if CMDID != 0:
			if logLevel[devId]> 0: U.logger.log(20, "devID:{}; received CMDID: {:3d}= {:}. ".format(devId, CMDID, commandList[devId].get(str(CMDID),"")) )

			if acceptCMDID(devId, CMDID) == 1:
				if logLevel[devId]> 1: U.logger.log(20, "devID:{}; received CMDID: {:3d}= {:}, skip ========".format(devId, CMDID,  commandList[devId].get(str(CMDID),"")) )
				accept = False
			else:
				accept = True
				if logLevel[devId]> 0: U.logger.log(20, "devID:{};    ---------------- valid cmd:{}={}; learning mode active? >{}< ============".format(devId, CMDID, commandList[devId].get(str(CMDID),""), ignoreUntilEndOfLearning[devId] !=-1 ))
				# check for learning 
				if ignoreUntilEndOfLearning[devId] != -1: # already in learning mode
					if  CMDID in [203, 207, 208]:#   or not(CMDID > 199 and CMDID < 209)):	 # exit learning?
						U.logger.log(20, "devID:{}; exit learning mode CMDID:{}, last cmdid was :{}, set mute back to device".format(devId, CMDID, ignoreUntilEndOfLearning[devId] )  )
						U.sendURL({"sensors":{sensor:{devId:{"cmd":CMDID}}}}, wait=False)
						ignoreUntilEndOfLearning[devId] = -1
						setMute(devId, False, CMDID=CMDID)
				else:
					if CMDID in [200, 201, 202]:
						if ignoreUntilEndOfLearning[devId] == -1: # learning not started
							if not allowLearning[devId]: # start learning, not allow?
								U.logger.log(20, "devID:{}; request to enter learning mode CMDID:{},  rejected!  ==> reset sensor (allowLearning was set to off in device edit)".format(devId, CMDID )  )
								U.sendURL({"sensors":{sensor:{devId:{"cmd":822}}}}, wait=False)
								time.sleep(0.2)
								doReset(devId, force=True)
								time.sleep(7)
								checkifRefreshSetup(devId, restart=True)
								return {"cmd":0}
							
							else: # enter learning mode 
								setMute(devId, False, CMDID=CMDID)
								ignoreUntilEndOfLearning[devId]  = CMDID
								U.sendURL({"sensors":{sensor:{devId:{"cmd":CMDID}}}}, wait=False)
								return {"cmd":0}

					elif CMDID in [204, 205, 206, 208]: # just ignore
						U.sendURL({"sensors":{sensor:{devId:{"cmd":CMDID}}}}, wait=False)
						return {"cmd":0}

					elif CMDID in [203, 207]: # exit learning / exit deleting 
						U.logger.log(20, "devID:{}; learning mode exit CMDID:{}".format(devId, CMDID )  )
						ignoreUntilEndOfLearning[devId]  = -1
						U.sendURL({"sensors":{sensor:{devId:{"cmd":CMDID}}}}, wait=False)
						if currentMute[devId]  != sensors[sensor][devId]["mute"]:
							setMute(devId, sensors[sensor][devId]["mute"])
						return {"cmd":0}
					else:
						pass # do nothing here 

		

		if CMDID == 255:
			time.sleep(2)
			lastkeepAwake[devId] = 0
			checkifRefreshSetup(devId, restart=badSensor[devId] > 0, upd=True)
			accept = True

		if CMDID in [200, 201, 202] and allowLearning[devId]: # start learning
			time.sleep(2)
			lastkeepAwake[devId] = 0
			checkifRefreshSetup(devId, restart=badSensor[devId] > 0, upd=True)
			accept = True


		if CMDID == 800 :
			time.sleep(3.)
			doReset(devId)
			time.sleep(3.)
			lastkeepAwake[devId] = 0
			checkifRefreshSetup(devId, restart=True, upd=True)
			accept = True

		if CMDID == 802 and keepAwake[devId]: # 802 == exit wakeup
			lastkeepAwake[devId] = 0
			checkifRefreshSetup(devId, restart=True, upd=True)
			accept = True


		if CMDID in [1,2]:
			if i2cOrUart[devId] == "uart":
				if logLevel[devId]> 0: U.logger.log(20, "devID:{}; firstCmdReceived:{}, lastValCmd @: {:.1f}  dtlka= {:.1f}".format(devId, firstCmdReceived, time.time() - lastValidCmdAt[devId], time.time() - lastkeepAwake[devId]) )
				if not firstCmdReceived or (time.time() - lastValidCmdAt[devId] > 5 and time.time() - lastkeepAwake[devId] > 5):
					lastkeepAwake[devId] = 0
					checkifRefreshSetup(devId, restart=True, upd=True)
			else:
				if not firstCmdReceived or (time.time() - lastValidCmdAt[devId] > 20 and time.time() - lastkeepAwake[devId] > 20):
					lastkeepAwake[devId] = 0
					checkifRefreshSetup(devId, restart=True, upd=True)
			accept = True

		if badSensor[devId] > 1:
			U.logger.log(20, "devID:{}; reset bad sensor count after {:} bad sensor readings".format(devId, badSensor[devId])  )

		badSensor[devId] = 0
		if CMDID not in reactOnlyToCommands[devId]: 	return {"cmd":0}  
		if accept:										return {"cmd":CMDID}
		else:											return {"cmd":0}

	except Exception as e:
		U.logger.log(20, "in Line {} has error={}".format(sys.exc_info()[-1].tb_lineno, e))

	badSensor[devId] += 1
	if badSensor[devId] >= 5: return "badSensor"
	return ""

############################################
def acceptCMDID(devId, CMDID):
	"""Determines whether a received command ID should be accepted, suppressing duplicates that arrive within each device's ignore-same-command window; updates last-command bookkeeping and queues accepted commands.

	Inputs:
	    devId (str): Device identifier that received the command
	    CMDID (int): The received command ID to evaluate
	Outputs:
	    int: 0 if CMDID is 0, 1 to suppress a too-soon duplicate, 2 to accept
	"""
	global lastCommandReceived, lastValidCmdAt, ignoreSameCommands
	global anyCmdDefined
	
	if CMDID == 0: return 0
	if logLevel[devId]> 1: U.logger.log(20, "devId:{}, checking cmdID:{} ".format(devId, CMDID))
	retCode = 0
	devId2 = 0
	dt = 0
	for devId2 in lastCommandReceived:
		dt =  time.time() - lastValidCmdAt[devId2]
		if logLevel[devId]> 1: U.logger.log(20, "devId:{}, last:{}   time:{:.1f} < {:.1f}?".format(devId2, lastCommandReceived[devId2], dt,  ignoreSameCommands[devId2]))
		if lastCommandReceived[devId2] == CMDID:
			if ignoreSameCommands[devId2] > 0 and dt  < ignoreSameCommands[devId2]:
				retCode = 1
				break
			else:
				retCode = 2

	lastValidCmdAt[devId] = time.time()
	lastCommandReceived[devId] = CMDID 
	if logLevel[devId]> 1: U.logger.log(20, "devId:{}, oldDevId:{}, CMDID:{}, retCode:{}, dt:{:.1f} secs".format(devId, devId2, CMDID, retCode, dt))
	if retCode != 1:
		if anyCmdDefined: cmdQueue.put(CMDID)
	return retCode	


############################################
def checkResetPower():
	"""Placeholder hook for checking/resetting power that currently performs no action.

	Inputs:
	    None.
	Outputs:
	    None: no-op
	"""
	return

############################################
def startThreads():
	"""Starts the background command-processing thread that runs cmdCheckIfGPIOon, recording its running state.

	Inputs:
	    None.
	Outputs:
	    None: creates and starts the cmdCheckIfGPIOon thread and logs
	"""
	global threadCMD
	global logLevel

	U.logger.log(20, "start cmd thread logLevel:{}".format(logLevel))
	if maxLogLevel() > 0: U.logger.log(20, "start cmd thread ")
	try:
		threadCMD = {}
		threadCMD["state"]   = "start"
		threadCMD["thread"]  = threading.Thread(name='cmdCheckIfGPIOon', target=cmdCheckIfGPIOon)
		threadCMD["state"]   = "running"
		threadCMD["thread"].start()

	except  Exception as e:
		U.logger.log(20,"", exc_info=True)
	return

############################################
def cmdCheckIfGPIOon():
	"""Background thread loop that drains the command queue and, for each configured GPIO action matching a voice command, writes pulse-up output commands to the receive-commands file to actuate the mapped GPIO pins.

	Inputs:
	    None.
	Outputs:
	    None: writes GPIO pulse commands to the command file and logs until the thread state stops
	"""
	global gpioCmdForAction, gpioNumberForCmdAction, gpioInverseAction, gpioOnTimeAction	
	global cmdQueue, threadCMD
	global logLevel, anyCmdDefined
	global GPIOZERO
	global unixCmdAction, unixCmdVoiceNo
	global gpioInfoIndigoIDForMsgToReceivecommand

	try:
		time.sleep(1)
		if maxLogLevel() > 0: U.logger.log(20, "start  GPIO action  thread")
		anyOn = False
		while threadCMD["state"] == "running":
			time.sleep(0.1)
			try:
				outFile = []
				pinsUsed = []
				last = []
				while not cmdQueue.empty():
					cmd = cmdQueue.get()
					if maxLogLevel() > 1: U.logger.log(20, "checking gpio requests command:{} ===== anyCmdDefined:{}".format(cmd, anyCmdDefined) )
					if cmd > 300: continue  # ignore status messages
					if anyCmdDefined:
						for ii in range(1,9):
							if maxLogLevel() > 2: U.logger.log(20, "checking  #:{}, command:{},  gpioCmdForAction:{}, gpioNumberForCmdAction:{}, ontime:{}".format(ii, cmd,  gpioCmdForAction[ii]  , gpioNumberForCmdAction[ii], gpioOnTimeAction[ii]) )
							if gpioNumberForCmdAction[ii] == "": 			continue
							if gpioCmdForAction[ii] == "": 		 			continue
							if gpioNumberForCmdAction[ii] in pinsUsed:		continue

							gpio = gpioNumberForCmdAction[ii]
							if gpio in gpioInfoIndigoIDForMsgToReceivecommand:
								indigoIdOfOutputDevice = gpioInfoIndigoIDForMsgToReceivecommand[gpio]["indigoIdOfOutputDevice"]
								devType = gpioInfoIndigoIDForMsgToReceivecommand[gpio]["devType"]
							else:
								indigoIdOfOutputDevice = "0"
								devType = "OUTPUTgpio-1"

							##    any cmd								cmd >= 1 == wake key any comand			cmd >= 2 == wake + any real cmd					cmd > 2, any real command

							if cmd == GLOB_cmdCodeForrelay:
								if gpioCmdForAction[ii] == cmd:
									outFile.append({"device": devType, "devId":indigoIdOfOutputDevice, 'pin': gpio, 'command': 'pulseUp', 'values': {'pulseUp': gpioOnTimeAction[ii]}, 'inverseGPIO': gpioInverseAction[ii] != "0", "debug":max(10,min(30, maxLogLevel()*10))})
							else:
								if 	gpioCmdForAction[ii] == cmd:
									outFile.append({"device": devType, "devId":indigoIdOfOutputDevice, 'pin': gpio, 'command': 'pulseUp', 'values': {'pulseUp': gpioOnTimeAction[ii]}, 'inverseGPIO': gpioInverseAction[ii] != "0", "debug":max(10,min(30, maxLogLevel()*10))})
									pinsUsed.append(gpio)
								else:
									if ( (gpioCmdForAction[ii] == 1 and cmd > 0) or
										 (gpioCmdForAction[ii] == 2 and cmd > 1) or 
										 (gpioCmdForAction[ii] == 3 and cmd > 4)
									   ):
										last.append({"device": devType, "devId":indigoIdOfOutputDevice, 'pin': gpio, 'command': 'pulseUp', 'values': {'pulseUp': gpioOnTimeAction[ii]}, 'inverseGPIO': gpioInverseAction[ii] != "0", "debug":max(10,min(30, maxLogLevel()*10))})
										pinsUsed.append(gpio)
				if outFile != [] or last != []:
					if last != []: outFile += last
					f = open(GLOB_fileToReceiveCommands,"a")
					f.write(json.dumps(outFile))
					f.close()
					if maxLogLevel() > 0: U.logger.log(20, "sending cmd:{} to receiveCommands file:{}".format(outFile, GLOB_fileToReceiveCommands) )
									
								
			except Exception as e:
				U.logger.log(20, "in Line {} has error={}".format(sys.exc_info()[-1].tb_lineno, e))
				time.sleep(10)
				

	except Exception as e:
		U.logger.log(20, "in Line {} has error={}".format(sys.exc_info()[-1].tb_lineno, e))
	if maxLogLevel() > 0: U.logger.log(20, "ended  loop, state:{}".format(threadCMD["state"] ))




############################################
def cmdCheckSerialPort( devId, serialType, doNotUse=""):
	"""Verifies and configures the serial port for a device: for hardware serial it checks/repairs the Raspberry Pi serial console/hardware config (rebooting if changed), then for non-reboot cases locates an available /dev device matching the configured port name, skipping ports already in use, and returns the chosen port.

	Inputs:
	    devId (str): Device identifier whose serial port to validate
	    serialType (str): Serial type/name (e.g. contains 'USB' or a port suffix)
	    doNotUse (str): Optional port to mark as failed/exclude when updating the owner file
	Outputs:
	    str: The selected available port device name, or empty string if none found or on error
	"""
	global gpioCmdForAction, gpioNumberForCmdAction, gpioInverseAction, gpioOnTimeAction, serialPortName
	global sensor, sensors
	global USBitems

	try:
		reboot = False
		if serialType.find("USB") == -1: # check if serial hardware is enabled, if requested and not present, enable and reboot
			for ii in range(30): # if prep step not done, wait
				raspi, ddd = U.readJson(G.homeDir+"raspiConfig.params")
				reboot = False
				if ddd == "":
					time.sleep(2)
					continue
	
				#U.logger.log(20, "raspiConfig.params file found:  \nSERIAL_HARDWARE:{}, \nSERIAL_CONSOLE:{} \nSERIAL_CONSOLE_OLD:{}".format(raspi.get("SERIAL_HARDWARE",""), raspi.get("SERIAL_CONSOLE",""), raspi.get("SERIAL_CONSOLE_OLD","") ))
	
				if "SERIAL_CONSOLE" in raspi  and "SERIAL_HARDWARE" in raspi and "SERIAL_CONSOLE_OLD" in raspi:
					if raspi["SERIAL_CONSOLE"].get("result","") in ["0","1"]: 			old = 0
					else:
						if raspi["SERIAL_CONSOLE_OLD"].get("result","") in ["0","1"]: 	old = 1
						else: 															old = 2
	
					hardWare = raspi["SERIAL_HARDWARE"]["result"]
	
					if old == 2 or hardWare not in ["0","1"]:
						U.logger.log(20, "raspiConfig.params file found, bad config  \nSERIAL_HARDWARE:{}, \nSERIAL_CONSOLE:{} \nSERIAL_CONSOLE_OLD:{}".format(hardWare, raspi.get("SERIAL_CONSOLE",""), raspi.get("SERIAL_CONSOLE_OLD","") ))
						break
	
					if old == 1:
						cons	 = raspi["SERIAL_CONSOLE_OLD"]["result"]
					else:
						cons	 = raspi["SERIAL_CONSOLE"]["result"]
	
					U.logger.log(20, "old version?:{}, hardWare:{} cons:{}".format(old==1, hardWare, cons ))
					if old == 1:
						if hardWare != "0" or cons == "0":
							cmd = "/usr/bin/sudo /usr/bin/raspi-config nonint do_serial 2" # enable hardware, disable software
							ret = subprocess.Popen(cmd,shell=True,stdout=subprocess.PIPE,stderr=subprocess.PIPE).communicate()[0].decode('utf-8')
							U.logger.log(20, "ret: {}".format(ret))
							reboot = True
							msg = "serial hard ware / conole  config wrong,  changed and rebooting to rectify #907"
							U.logger.log(20, " {}".format(msg))
							U.sendURL({"sensors":{sensor:{devId:{"cmd":907}}}}, wait=False)
	
					else: # new version, separate cons and hw
						if hardWare != "0":
							cmd = "/usr/bin/sudo /usr/bin/raspi-config nonint do_serial_hw 0" # enable hardware
							ret = subprocess.Popen(cmd,shell=True,stdout=subprocess.PIPE,stderr=subprocess.PIPE).communicate()[0].decode('utf-8')
							U.logger.log(20, "ret: {}".format(ret))
							reboot = True
							msg = "serial hard ware config wrong,  changed and rebooting to rectify #903"
							U.logger.log(20, " {}".format(msg))
							U.sendURL({"sensors":{sensor:{devId:{"cmd":903}}}}, wait=False)
		
						if cons != "1":
							cmd = "/usr/bin/sudo /usr/bin/raspi-config nonint do_serial_cons 1"  # disable console
							ret = subprocess.Popen(cmd,shell=True,stdout=subprocess.PIPE,stderr=subprocess.PIPE).communicate()[0].decode('utf-8')
							U.logger.log(20, "ret: {}".format(ret))
							reboot = True
							msg = "serial console config wrong, changed and rebooting to rectify #904"
							U.logger.log(20, " {}".format(msg))
							U.sendURL({"sensors":{sensor:{devId:{"cmd":904}}}}, wait=False)
	
					if reboot:
						U.setRebootRequest("configuring serial port")
						time.sleep(10000)
					else:
						if logLevel[devId]> 1: U.logger.log(20, "serial port configured properly")
	
				break
			if logLevel[devId]> 1: U.logger.log(20, "after check serial hw: reboot; {}, doNotUse>{}<".format(reboot, doNotUse))

		if not reboot:
			checkPort = serialPortName[devId].strip("*")
			if logLevel[devId]> 1: U.logger.log(20, "devId:{}, checkPort:{}, \nPORTownerFile:{}".format(devId, checkPort, readPORTownerFile() ))
			
			checkifdevIdInPORTownerFile(devId)

			updatePORTownerFile(devId, port="", failed=doNotUse, calledFrom="clear port")

			cmd = "/bin/ls -l /dev | /usr/bin/grep "+checkPort
			ret = subprocess.Popen(cmd,shell=True,stdout=subprocess.PIPE,stderr=subprocess.PIPE).communicate()[0].decode('utf-8')
			if logLevel[devId]> 1: U.logger.log(20, " ls -l /dev  ret:\n{}".format(ret))
			
			found = ""
			for line in ret.split("\n"):
				pp = line.find(checkPort)
				if pp < 10: continue		
				#U.logger.log(20, " pp:{}, line {}".format(pp, line))
				existingport = line[pp:].strip().split(" ")[0]
				alreadyInUse = 0
				
				if checkifIdInFAILEDPORTownerFile(devId, existingport):
					if logLevel[devId]> 1:U.logger.log(20, "devId:{}, skipping:{} in failed list".format(devId, existingport))
					continue

				if not checkifIdInOKPORTownerFile(devId, existingport):
					for dddd in getdevIdsPORTownerFile():
						if checkifIdInOKPORTownerFile(dddd, existingport): 
							if logLevel[devId]> 1:U.logger.log(20, "devId:{}, already in use by devId:{}  port:{}".format(devId, dddd, existingport))
							alreadyInUse = dddd
							break
						
				if alreadyInUse == 0:
						if logLevel[devId]> 1:U.logger.log(20, "devId:{}  selected port:{}".format(devId, existingport))
						return existingport
	
			msg = "bad_port:_/dev/"+serialType
			msg += ", restarting"
			U.logger.log(20, " {}".format(msg))
			checkErrorSend(devId, "port {} not available, restarting sensor".format(serialType), 901,"delayed, restart")

	except Exception as e:
		U.logger.log(20, "in Line {} has error={}".format(sys.exc_info()[-1].tb_lineno, e))

	return ""
		
############################################
def checkErrorSend(devId, errorText, CMDID, action):
	"""Manages error reporting/deduplication for a sensor command: on action 'reset' it clears the persisted error file, otherwise it logs the error, compares against the last stored error (by text and time), and conditionally sends the error to Indigo via URL, rewrites the error JSON file, and optionally restarts the process.

	Inputs:
	    devId (str): Indigo device id the error pertains to
	    errorText (str): human-readable error message to report
	    CMDID (int): command id sent with the error payload
	    action (str): control flags such as 'reset', 'delayed', or 'restart'
	Outputs:
	    None: logs, writes/removes the error JSON file, sends URL to Indigo, may restart process
	"""
	global logLevel
	global lastErrExists
	try:
		if action == "reset":
			if lastErrExists and os.path.isfile(GLOB_errorFile):
				os.remove(GLOB_errorFile)
			lastErrExists = False
			return
				
		U.logger.log(20, " {}".format(errorText))
		lastError, inRaw = U.readJson(GLOB_errorFile)
		sendMsg = ""
		if lastError == {}: 													sendMsg += "new"
		elif errorText != "" and lastError.get("errorText","") != errorText:	sendMsg += "text"
		elif time.time() -  float(lastError.get("lastErrTime",0)) < 200:		sendMsg += "time"
		
		if sendMsg != "":
		
			if sendMsg.find("time") > -1 or ( action.find("delayed") == -1 and sendMsg.find("text") > -1 ):
				U.sendURL({"sensors":{sensor:{devId:{"cmd":CMDID,"errorText":errorText }}}}, wait=False)

			lastErrExists = True
			U.writeJson(GLOB_errorFile, {"errorText": errorText,"lastErrTime":"{:.1f}".format(time.time()), "timetext":datetime.datetime.now().strftime("%Y-%m-%d-%H:%M:%S") } )

			if action.find("restart") > -1: 
				U.restartMyself(reason=errorText, python3="1")



	except Exception as e:
		U.logger.log(20, "in Line {} has error={}".format(sys.exc_info()[-1].tb_lineno, e))
	return 



############################################
def execSensorLoop():
	"""Main sensor process entry point: initializes all global state dictionaries, sets up logging, kills old instances, reads parameters, starts worker threads, then runs the perpetual measurement loop that polls each device's values, sends data/alive pings to Indigo, handles bad-sensor restarts, and periodically checks for commands, restarts, and config refreshes until the sensor is removed.

	Inputs:
	    None.
	Outputs:
	    None: runs the infinite sensor loop; updates globals, logs, sends URLs, signals command thread to stop on exit
	"""
	global sensor, sensors, badSensor
	global SENSOR, sensorMode
	global oldRaw, lastRead, lastRead2
	global startTime, lastMeasurement, lastRestart, restartRepeat, restartON
	global oldi2cOrUart, i2cOrUart, oldserialPortName, sensorOld, keepAwake, lastkeepAwake, tmpMuteOff, serialPortName, serialPortNameUse
	global gpioCmdForAction, gpioNumberForCmdAction, gpioInverseAction, gpioOnTimeAction
	global refreshRepeat
	global currentMute
	global sleepAfterWrite, oldSleepAfterWrite, commandList
	global anyCmdDefined
	global cmdQueue, logLevel
	global threadCMD
	global firstCmdReceived
	global learningOn
	global lastReset, expectResponse, restartConnectionCounter, setWakeTime
	global GPIOZERO, failedCount
	global reactOnlyToCommands, maxCommandId, minErrorCmdID,offCommand
	global gpioUsed 
	global resetGPIOClass
	global unixCmdVoiceNo, unixCmdAction
	global ignoreUntilEndOfLearning
	global lastCommandReceived, lastValidCmdAt, ignoreSameCommands, restartSensor
	global lastErrExists
	global lastAliveSend
	global gpioInfoIndigoIDForMsgToReceivecommand
	global allowLearning
	global commonRelayActive

	logLevel						= {"-1":1}
	commonRelayActive				= {}
	allowLearning					= {}
	gpioInfoIndigoIDForMsgToReceivecommand							= {}
	lastErrExists					= True
	failedCount						= {}
	lastRead2						= ""
	restartSensor					= {}
	lastCommandReceived				= {}
	lastValidCmdAt					= {}
	ignoreSameCommands				= {}
	ignoreUntilEndOfLearning		= {}
	resetGPIOClass					= {}
	gpioUsed 						= [0,0,0,0,0,0,0,0,0,0]
	reactOnlyToCommands				= {}
	offCommand						= 255
	maxCommandId					= 1000
	minErrorCmdID					= 700
	GPIOZERO						= {}
	restartConnectionCounter		= {}
	expectResponse					= {}
	lastReset						= {}
	serialPortNameUse				= {}
	serialPortName					= {}
	oldserialPortName				= {}
	learningOn						= {}
	currentMute						= {}
	restartRepeat					= {}
	tmpMuteOff						= {}
	lastkeepAwake					= {}
	keepAwake						= {}
	oldi2cOrUart					= {}
	i2cOrUart						= {}
	sensorOld						= {}
	refreshRepeat					= {}
	setWakeTime						= {}
	badSensor						= {}
	lastRestart						= time.time()
	SENSOR							= {}
	firstCmdReceived				= False
	# NO "logLevel = 1" here: logLevel is a dict, devId -> level, and it is initialised as one
	# 40 lines up. This line used to overwrite it with a plain int, so every logLevel[devId] and
	# maxLogLevel() failed with "'int' object is not iterable" until readParams() happened to run
	# and repair the type.
	cmdQueue						= queue.Queue()
	unixCmdVoiceNo					= ["","","","","","","","","",""]
	unixCmdAction					= ["","","","","","","","","",""]
	gpioCmdForAction				= ["","","","","","","","","",""]
	gpioNumberForCmdAction			= ["","","","","","","","","",""]
	gpioInverseAction				= ["","","","","","","","","",""]
	gpioOnTimeAction				= ["","","","","","","","","",""]
	anyCmdDefined					= False

	commandList						= {}
	sleepAfterWrite 				= {}
	oldSleepAfterWrite 				= {}

	restartON						= True
	sendToIndigoSecs				= 200
	startTime						= time.time()
	lastMeasurement					= time.time()
	oldRaw							= ""
	lastRead						= 0
	sensorRefreshSecs				= 0.3
	sensors							= {}
	sensor							= G.program
	myPID							= str(os.getpid())
	U.setLogging()
	U.killOldPgm(myPID,G.program+".py")# kill old instances of myself if they are still running

	#U.resetI2cBus()

	U.logger.log(20, "==== start {}  ===============".format(version))

	if U.getIPNumber() > 0:
		time.sleep(10)
		exit()

	readParams()

	lastRead = time.time()

	U.echoLastAlive(G.program)

	startThreads()

	lastAliveSend		= {}
	theValues 			= {}
	sensorWasBad 		= False
	while True:
		if sensor not in sensors: 
			break 
		try:
			extraSleep = 0
			tt = time.time()
			sendData = {}
			data = {}
			theValues = {}
			theValues["cmd"] = ""
			
			if sensor in sensors:
				data = {"sensors": {sensor:{}}}
				sendData = False
				devIdList = {}
				for devId in sensors[sensor]:
					if devId not in lastAliveSend:
						lastAliveSend[devId] = 0
					theValues = getValues(devId)
					#U.logger.log(20, "devId:{}, value:{}, time:{:.2f}".format(devId, theValues, time.time() - startTime))
					
					devIdList[devId] = 0

					if theValues == "":
						continue

					if badSensor[devId] >= 5 or type(theValues) == type(" ") or failedCount[devId] > 6:
						sensorWasBad = True
						if badSensor[devId] in [5,6,9] or failedCount[devId] > 6:
							checkErrorSend(devId, "bad read, restarting sensor", 900, "delayed, restart")
							resetSensorRelay(devId)
							break
						extraSleep = 2

					if theValues == "badSensor": time.sleep(2)

					elif theValues["cmd"] != 0:
						data["sensors"][sensor][devId] = theValues
						devIdList[devId] = 1
						checkErrorSend(devId, "", 0, "reset")
						U.sendURL(data, wait=False)
						for devId2 in devIdList:
							lastAliveSend[devId2] = time.time()


					elif time.time() - sendToIndigoSecs > lastAliveSend[devId]:
						data["sensors"][sensor][devId] = {"cmd":700}
						sendData = True
						devIdList[devId] = 1

			if sendData:
				U.sendURL(data, wait=False)
				#U.makeDATfile(G.program, data)
				extraSleep  += 0.01
				lastRead = time.time() + 4.
				for devId in devIdList:
					lastAliveSend[devId] = time.time()

			U.echoLastAlive(G.program)

			if  time.time() - lastRead > 3.:
				checkIfCommand()
				checkIfRestart()
				for devId in sensors[sensor]:
					checkIfRestartConnection(devId)
				readParams()
				lastRead = time.time()
				for devId in sensors[sensor]:
					checkifRefreshSetup(devId)
				checkIfReset()

			#U.logger.log(20, "dt time last{:.1f},  start:{:.1f}".format(time.time()  - lastMeasurement, time.time()  - startTime))


			dtLast = time.time()  - lastMeasurement
			slTime = max(0., sensorRefreshSecs + extraSleep  - (time.time()  - lastMeasurement) )
			time.sleep(0.1 )
			lastMeasurement = time.time()


		except Exception as e:
			U.logger.log(20, "in Line {} has error={}".format(sys.exc_info()[-1].tb_lineno, e))
			time.sleep(5.)

	threadCMD["state"] = "stop"

G.pythonVersion = int(sys.version.split()[0].split(".")[0])
# output: , use the first number only
#3.7.3 (default, Apr	3 2019, 05:39:12)
#[GCC 8.2.0]

execSensorLoop()
try: 	G.sendThread["run"] = False; time.sleep(1)
except: pass
sys.exit(0)


