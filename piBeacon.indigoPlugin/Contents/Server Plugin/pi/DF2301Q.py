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
"""

import serial

import logging
from ctypes import *
import sys, os, time, json, datetime, subprocess, copy
import smbus

sys.path.append(os.getcwd())
import	piBeaconUtils	as U
import	piBeaconGlobals as G
import RPi.GPIO as GPIO

try:
	import queue as queue
except:
	import Queue as queue
import threading


G.program = "DF2301Q"
resetFile						= G.homeDir+"temp/DF2301Q.reset"

DF2301Q_I2C_sleepAfterReadWrite = 200 # msec
DF2301Q_UART_sleepAfterReadWrite= 50 # msec

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
DF2301Q_UART_MSG_TYPE_CMD_UP				= 0xA0
DF2301Q_UART_MSG_TYPE_CMD_DOWN				= 0xA1
DF2301Q_UART_MSG_TYPE_ACK					= 0xA2
DF2301Q_UART_MSG_TYPE_NOTIFY				= 0xA3
# msg_cmd
## Report voice recognition results
DF2301Q_UART_MSG_CMD_ASR_RESULT				= 0x91
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
DF2301Q_UART_MSG_CMD_NOTIFY_STATUS			= 0x9A
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
DF2301Q_UART_MSG_ACK_ERR_CHECKSUM			= 0xff
DF2301Q_UART_MSG_ACK_ERR_NOSUPPORT			= 0xfe

DF2301Q_UART_PORT_NAME						= "serial0"

############ UART ##########################	end




class DFRobot_DF2301Q_I2C():

	def __init__(self, i2c_addr=DF2301Q_I2C_ADDR, bus=1, sleepAfterWrite=DF2301Q_I2C_sleepAfterReadWrite):
		self._addr = i2c_addr
		self._i2c = smbus.SMBus(bus)
		self.debug = 0
		self.sleepAfterWrite = sleepAfterWrite/1000.
		#super(DFRobot_DF2301Q_I2C, self).__init__()

	def set_Params(self, sleepAfterWrite=DF2301Q_I2C_sleepAfterReadWrite,logLevel=0):
		self.debug = int(logLevel)
		self.sleepAfterWrite = sleepAfterWrite/1000.
		if self.debug > 1: U.logger.log(20, "sleepAfterWrite:{}, logLevel:{}".format(sleepAfterWrite, logLevel) )

	def get_CMDID(self):
		time.sleep(0.05)	 # Prevent the access rate from interfering with other functions of the voice module
		CMDID =  self._read_reg(DF2301Q_I2C_REG_CMDID)  # 0 = nothig new
		if self.debug > 1 and CMDID > 0: U.logger.log(20,": {}".format(CMDID))
		return CMDID # == 0  nothing new

	def play_CMDID(self, CMDID):
		# note Can enter wake-up state through ID = 1 in I2C mode
		if self.debug > 1: U.logger.log(20,": {}".format(CMDID))
		self._write_reg(DF2301Q_I2C_REG_PLAY_CMDID, CMDID)
		time.sleep(1)

	def set_wakeup(self):
		if self.debug > 1: U.logger.log(20,":")
		self._write_reg(DF2301Q_I2C_REG_PLAY_CMDID, 1)

	def get_wake_time(self):
		wktime =  self._read_reg(DF2301Q_I2C_REG_WAKE_TIME)
		if self.debug > 1: U.logger.log(20,": {}".format(wktime))
		return wktime

	def set_wake_time(self, wake_time):
		if self.debug > 1: U.logger.log(20,": {}".format(wake_time))
		self._write_reg(DF2301Q_I2C_REG_WAKE_TIME, wake_time & 0xFF)

	def set_volume(self, vol):
		v = int(vol)
		if self.debug > 1: U.logger.log(20,": {}".format(v))
		self._write_reg(DF2301Q_I2C_REG_SET_VOLUME, max(0,min(v,20)))

	def set_mute_mode(self, mode, calledFrom=""):
		m = int(mode)
		if (0 != m):
			m = 1
		if self.debug > 1: U.logger.log(20,": {} from:{}".format(m, calledFrom))
		self._write_reg(DF2301Q_I2C_REG_SET_MUTE, m)

	def _write_reg(self, reg, data):
		if isinstance(data, int):
			data = [data]
		if self.debug > 2: U.logger.log(20,": {}->{}".format(reg, data))
		self._i2c.write_i2c_block_data(self._addr, reg, data)
		time.sleep(self.sleepAfterWrite)

	def _read_reg(self, reg):
		ret =  self._i2c.read_i2c_block_data(self._addr, reg, 1)
		if self.debug > 2: U.logger.log(20,": ret:{}".format(ret))
		return ret[0]
		#time.sleep(self.sleepAfterWrite)


##############  uart (serial) class #########
class DFRobot_DF2301Q_UART():

	REV_STATE_HEAD0	 	= 0x00
	REV_STATE_HEAD1	 	= 0x01
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
		'''!
			@brief Class for serial data frame struct
		'''
		def __init__(self):
			'''!
				@brief sensor_status structure init
			'''
			self.header = 0
			self.data_length = 0
			self.msg_type = 0
			self.msg_cmd = 0
			self.msg_seq = 0
			self.msg_data = [0] * 8

	def __init__(self, serialPortName=DF2301Q_UART_PORT_NAME, sleepAfterWrite=DF2301Q_UART_sleepAfterReadWrite ):
		'''!
			@brief Module UART communication init
		'''
		self.sleepAfterWrite = sleepAfterWrite/1000.
		self.debug = 0
		self.uart_cmd_ID = 0
		self._send_sequence = 0
		self._ser = serial.Serial("/dev/"+serialPortName, baudrate=DF2301Q_UART_BAUDRATE, bytesize=8, parity='N', stopbits=1, timeout=0.5)
		if self._ser.isOpen == False:
			self._ser.open()
		super(DFRobot_DF2301Q_UART, self).__init__()
		#self.reset_module()

	def set_Params(self, sleepAfterWrite=DF2301Q_I2C_sleepAfterReadWrite, logLevel=0):
		self.debug = int(logLevel)
		self.sleepAfterWrite = sleepAfterWrite/1000.
		if self.debug > 1: U.logger.log(20, "sleepAfterWrite:{}, logLevel:{}".format(sleepAfterWrite, logLevel) )


	def get_CMDID(self):
		'''!
			@brief Get the ID corresponding to the command word
			@return Return the obtained command word ID, returning 0 means no valid ID is obtained
		'''
		data_rev_count = self._recv_packet()
		return self.uart_cmd_ID					# set in _recv_packet;  !=0 if new  ok data, 0 otherwise


	def set_volume(self,  set_value):
		v = int(set_value)
		if self.debug > 1: U.logger.log(20, "value:{}".format(v) )
		self.setting_CMD( DF2301Q_UART_MSG_CMD_SET_VOLUME, max(0,min(v,20)))


	def set_mute_mode(self,  set_value, calledFrom=""):
		m = int(set_value)
		if (0 != m):
			m = 1
		if self.debug > 1: U.logger.log(20,": {}, from:{}".format(m, calledFrom))
		self.setting_CMD( DF2301Q_UART_MSG_CMD_SET_MUTE, m)


	def set_wake_time(self,  set_value):
		if self.debug > 1: U.logger.log(20, "value:{}".format(set_value) )
		self.setting_CMD( DF2301Q_UART_MSG_CMD_SET_WAKE_TIME, set_value & 0xFF)


	def set_wakeup(self): # does not work
		if self.debug > 1: U.logger.log(20, "value:{}".format(0) )
		self.setting_CMD( DF2301Q_UART_MSG_CMD_SET_ENTERWAKEUP, 0)


	def set_notify_Status(self): # does not work
		if self.debug > 1: U.logger.log(20, "")
		self.setting_Notify( DF2301Q_UART_MSG_CMD_NOTIFY_STATUS, DF2301Q_UART_MSG_DATA_NOTIFY_POWERON)
		self.setting_Notify( DF2301Q_UART_MSG_CMD_NOTIFY_STATUS, DF2301Q_UART_MSG_DATA_NOTIFY_WAKEUPENTER)
		self.setting_Notify( DF2301Q_UART_MSG_CMD_NOTIFY_STATUS, DF2301Q_UART_MSG_DATA_NOTIFY_WAKEUPEXIT)


	def setting_Notify(self, set_type, set_value):
		'''!
			@brief Set commands of the module
		'''
		msg = self.uart_msg()
		msg.header = DF2301Q_UART_MSG_HEAD
		msg.data_length = 2
		msg.msg_type = DF2301Q_UART_MSG_TYPE_NOTIFY
		msg.msg_cmd = set_type
		msg.msg_seq = self._send_sequence
		self._send_sequence += 1
		msg.msg_data[0] = set_value
		msg.msg_data[1] = 0

		if self.debug > 2: U.logger.log(20, "msg:{}".format(str(msg)) )
		self._send_packet(msg)



	def get_wakeTime(self):
		if self.debug > 1: U.logger.log(20, "value: null")
		msg = self.uart_msg()
		msg.header = DF2301Q_UART_MSG_HEAD
		msg.data_length = 3
		msg.msg_type = DF2301Q_UART_MSG_TYPE_CMD_DOWN
		msg.msg_cmd = DF2301Q_UART_MSG_CMD_PLAY_VOICE
		msg.msg_seq = self._send_sequence
		self._send_sequence += 1
		msg.msg_data[0] = DF2301Q_UART_MSG_DATA_PLAY_START
		msg.msg_data[1] = DF2301Q_UART_MSG_DATA_PLAY_BY_CMD_ID
		msg.msg_data[2] = CMDID

		self._send_packet(msg)



	def play_CMDID(self, CMDID):
		'''!
			@brief Play the corresponding reply audio according to the command word ID
			@param CMDID - Command word ID
		'''
		if self.debug > 1: U.logger.log(20, "value:{}".format(CMDID) )
		msg = self.uart_msg()
		msg.header = DF2301Q_UART_MSG_HEAD
		msg.data_length = 3
		msg.msg_type = DF2301Q_UART_MSG_TYPE_CMD_DOWN
		msg.msg_cmd = DF2301Q_UART_MSG_CMD_PLAY_VOICE
		msg.msg_seq = self._send_sequence
		self._send_sequence += 1
		msg.msg_data[0] = DF2301Q_UART_MSG_DATA_PLAY_START
		msg.msg_data[1] = DF2301Q_UART_MSG_DATA_PLAY_BY_CMD_ID
		msg.msg_data[2] = CMDID

		self._send_packet(msg)

	def reset_module(self):
		'''!
			@brief Reset the module
		'''
		try:
			if self.debug > 1: U.logger.log(20, "value:{}".format("") )
			msg = self.uart_msg()
			msg.header = DF2301Q_UART_MSG_HEAD
			msg.data_length = 5
			msg.msg_type = DF2301Q_UART_MSG_TYPE_CMD_DOWN
			msg.msg_cmd = DF2301Q_UART_MSG_CMD_RESET_MODULE
			msg.msg_seq = self._send_sequence
			self._send_sequence += 1
			msg.msg_data[0] = ord('r')
			msg.msg_data[1] = ord('e')
			msg.msg_data[2] = ord('s')
			msg.msg_data[3] = ord('e')
			msg.msg_data[4] = ord('t')

			self._send_packet(msg)
		except Exception as e:
			U.logger.log(20, "in Line {} has error={}".format(sys.exc_info()[-1].tb_lineno, e))


	def setting_CMD(self, set_type, set_value):
		'''!
			@brief Set commands of the module
			@param set_type - Set type
			@n			 DF2301Q_UART_MSG_CMD_SET_VOLUME : Set volume, the set value range 1-7  # uart is from 0-20 ???
			@n			 DF2301Q_UART_MSG_CMD_SET_ENTERWAKEUP : Enter wake-up state; set value 0
			@n			 DF2301Q_UART_MSG_CMD_SET_MUTE : Mute mode; set value 1: mute, 0: unmute
			@n			 DF2301Q_UART_MSG_CMD_SET_WAKE_TIME : Wake-up duration; the set value range 0-255s
			@param set_value - Set value, refer to the set type above for the range
		'''
		msg = self.uart_msg()
		msg.header = DF2301Q_UART_MSG_HEAD
		msg.data_length = 2
		msg.msg_type = DF2301Q_UART_MSG_TYPE_CMD_DOWN
		msg.msg_cmd = DF2301Q_UART_MSG_CMD_SET_CONFIG
		msg.msg_seq = self._send_sequence
		self._send_sequence += 1
		msg.msg_data[0] = set_type
		msg.msg_data[1] = set_value

		if self.debug > 2: U.logger.log(20, "msg:{}".format(str(msg)) )
		self._send_packet(msg)


	def _send_packet(self, msg):
		'''
			@brief Write data through UART
			@param msg - Data packet to be sent
		'''
		try:
			chk_sum = 0x0000
			data = []
			data.append(msg.header & 0xFF)
			data.append((msg.header >> 8) & 0xFF)
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
			if self.debug > 2: U.logger.log(20,"_send_packet: {}".format(data))
			self._ser.write(data)
			time.sleep(self.sleepAfterWrite)
		except Exception as e:
			U.logger.log(20, "in Line {} has error={}".format(sys.exc_info()[-1].tb_lineno, e))
			U.logger.log(20, "data:{}, msg:{}".format(data, str(msg.msg_data)))

	def _recv_packet(self):
		'''
			@brief Read data through UART
			@param msg - Buffer for receiving data packet
		'''

		self.uart_cmd_ID = 0  # for next iteration
		msg = self.uart_msg()
		rev_state = self.REV_STATE_HEAD0
		receive_char = 0
		chk_sum = 0
		data_rev_count = 0
		while self._ser.in_waiting:
			receive_char = ord(self._ser.read(1))
			if self.debug > 3: U.logger.log(20, "receive_char:{}".format(receive_char))

			if(self.REV_STATE_HEAD0 == rev_state): # begin of receive of data
				if(DF2301Q_UART_MSG_HEAD_LOW == receive_char):
					rev_state = self.REV_STATE_HEAD1

			elif(self.REV_STATE_HEAD1 == rev_state):
				if(DF2301Q_UART_MSG_HEAD_HIGH == receive_char):
					rev_state = self.REV_STATE_LENGTH0
					msg.header = DF2301Q_UART_MSG_HEAD
				else:
					rev_state = self.REV_STATE_HEAD0

			elif(self.REV_STATE_LENGTH0 == rev_state):
				msg.data_length = receive_char
				rev_state = self.REV_STATE_LENGTH1

			elif(self.REV_STATE_LENGTH1 == rev_state):
				msg.data_length += receive_char << 8
				rev_state = self.REV_STATE_TYPE

			elif(self.REV_STATE_TYPE == rev_state):
				msg.msg_type = receive_char
				rev_state = self.REV_STATE_CMD

			elif(self.REV_STATE_CMD == rev_state):
				msg.msg_cmd = receive_char
				rev_state = self.REV_STATE_SEQ

			elif(self.REV_STATE_SEQ == rev_state):
				msg.msg_seq = receive_char
				if(msg.data_length > 0):
					rev_state = self.REV_STATE_DATA
					data_rev_count = 0
				else:
					rev_state = self.REV_STATE_CKSUM0

			elif(self.REV_STATE_DATA == rev_state): # this actual data; [0] == cmd id
				msg.msg_data[data_rev_count] = receive_char
				data_rev_count += 1
				if(msg.data_length == data_rev_count):
					rev_state = self.REV_STATE_CKSUM0

			elif(self.REV_STATE_CKSUM0 == rev_state):  # chk_sum is  not used
				chk_sum = receive_char
				rev_state = self.REV_STATE_CKSUM1

			elif(self.REV_STATE_CKSUM1 == rev_state):   # chk_sum is  not used
				chk_sum += receive_char << 8
				rev_state = self.REV_STATE_TAIL

			elif(self.REV_STATE_TAIL == rev_state):  # received the end, set the cmd id
				if(DF2301Q_UART_MSG_TAIL == receive_char):
					if(DF2301Q_UART_MSG_TYPE_CMD_UP == msg.msg_type):
						self.uart_cmd_ID = msg.msg_data[0]
					elif(DF2301Q_UART_MSG_TYPE_NOTIFY == msg.msg_type):
						self.uart_cmd_ID = msg.msg_data[0]
				else:  # reset
					data_rev_count = 0
				rev_state = self.REV_STATE_HEAD0

			else: # set to begin sequence of data
				rev_state = self.REV_STATE_HEAD0

		return data_rev_count


# ===========================================================================
# read params
# ===========================================================================

###############################
def readParams():
	global sensors, logDir, sensor,	 displayEnable
	global SENSOR, sensorsOld
	global oldRaw, lastRead
	global startTime, lastMeasurement, oldi2cOrUart, oldserialPortName, keepAwake, lastkeepAwake
	global gpioCmdIndicator, gpioCmdIndicatorInverse, gpioCmdIndicatorOnTime, gpioAlreadyLoaded, restartRepeat, refreshRepeat
	global sleepAfterWrite, oldSleepAfterWrite, commandList, resetPowerGPIO
	global i2cOrUart, serialPortName
	global gpioCmdForAction, gpioNumberForCmdAction, anyCmdDefined, logLevel
	try:


		inp,inpRaw,lastRead2 = U.doRead(lastTimeStamp=lastRead)
		if inp == "": return
		if lastRead2 == lastRead: return
		lastRead	 = lastRead2
		if inpRaw == oldRaw: return
		oldRaw		 = inpRaw


		U.getGlobalParams(inp)

		if "sensors"	in inp:	 sensors =		(inp["sensors"])


		if sensor not in sensors:
			U.logger.log(20, "{} is not in parameters = not enabled, stopping {}.py".format(G.program,G.program) )
			exit()


		if logLevel > 0: U.logger.log(10,"{} reading new parameters".format(G.program) )

		for devId in sensors[sensor]:

			if "commandList" in sensors[sensor][devId]:
				commandList = json.loads(sensors[sensor][devId].get("commandList","{}"))


			if "logLevel" in sensors[sensor][devId]:
				if str(logLevel) != sensors[sensor][devId].get("logLevel","0"):
					upd = True
				logLevel = int(sensors[sensor][devId].get("logLevel","1"))

			restart = False
			i2cOrUart =  sensors[sensor][devId].get("i2cOrUart","")	
			if i2cOrUart != "" and oldi2cOrUart != i2cOrUart:					restart = True

			if "restartRepeat" in sensors[sensor][devId]:
				restartRepeat = float(sensors[sensor][devId].get("restartRepeat",100.))

			if "refreshRepeat" in sensors[sensor][devId]:
				refreshRepeat = float(sensors[sensor][devId].get("refreshRepeat",50.))

			if i2cOrUart == "uart":
				if "uartSleepAfterWrite" in sensors[sensor][devId]:
					if oldSleepAfterWrite != "" and sleepAfterWrite != oldSleepAfterWrite:
						upd = True
					sleepAfterWrite = float(sensors[sensor][devId].get("uartSleepAfterWrite",str(DF2301Q_UART_sleepAfterReadWrite)))
				oldSleepAfterWrite = sleepAfterWrite

				serialPortName =  sensors[sensor][devId].get("serialPortName", DF2301Q_UART_PORT_NAME)	
				if serialPortName != "" and oldserialPortName != serialPortName:
					restart = True
				oldiserialPortName = serialPortName

			else:
				if "i2cSleepAfterWrite" in sensors[sensor][devId]:
					if oldSleepAfterWrite != "" and  sleepAfterWrite != oldSleepAfterWrite:
						upd = True
					sleepAfterWrite = float(sensors[sensor][devId].get("i2cSleepAfterWrite",str(DF2301Q_I2C_sleepAfterReadWrite)))
				oldSleepAfterWrite = sleepAfterWrite

			upd = False
			if devId not in SENSOR or restart:
				if devId in SENSOR: del SENSOR[devId]
				upd = True
				startSensor(devId)
				if devId not in SENSOR or SENSOR[devId] == "":
					return

			if devId not in sensorsOld: upd = True

			keepAwake = sensors[sensor][devId].get("keepAwake") == "1"
			if keepAwake: sensors[sensor][devId]["setWakeTime"] = 255

			if "mute" in sensors[sensor][devId] and (upd or sensors[sensor][devId].get("mute") != sensorsOld[sensor][devId].get("mute")):
				upd = True

			elif "volume" in sensors[sensor][devId] and ( sensors[sensor][devId].get("volume") != sensorsOld[sensor][devId].get("volume")):
				upd = True

			elif "setWakeTime" in sensors[sensor][devId] and (sensors[sensor][devId].get("setWakeTime") != sensorsOld[sensor][devId].get("setWakeTime")):
				upd = True

			if "gpioCmdIndicator" in sensors[sensor][devId]:
				if (
						gpioCmdIndicator == "" or str(gpioCmdIndicator) != sensors[sensor][devId].get("gpioCmdIndicator","") or
						str(gpioCmdIndicatorInverse) != sensors[sensor][devId].get("gpioCmdIndicatorInverse","0") or
						str(gpioCmdIndicatorOnTime)	 != sensors[sensor][devId].get("gpioCmdIndicatorOnTime",1)
					):
					try:	gpioCmdIndicator	= int(sensors[sensor][devId].get("gpioCmdIndicator",""))
					except:	gpioCmdIndicator	= ""
					if gpioCmdIndicator not in ["",-1,0]:
						gpioCmdIndicatorInverse 		= sensors[sensor][devId].get("gpioCmdIndicatorInverse","0")
						try:	gpioCmdIndicatorOnTime	= int(sensors[sensor][devId].get("gpioCmdIndicatorOnTime",1000))
						except:	gpioCmdIndicatorOnTime	= 1000
						if not gpioAlreadyLoaded:
							GPIO.setmode(GPIO.BCM)
							GPIO.setwarnings(False)
							gpioAlreadyLoaded = True

						GPIO.setup(gpioCmdIndicator, GPIO.OUT)
						GPIO.output(gpioCmdIndicator, gpioCmdIndicatorInverse == "0")


			if "resetPowerGPIO" in sensors[sensor][devId]:
				if ( resetPowerGPIO == "" or str(resetPowerGPIO) != sensors[sensor][devId].get("resetPowerGPIO","")	):
					try:	resetPowerGPIO	= int(sensors[sensor][devId].get("resetPowerGPIO",""))
					except:	resetPowerGPIO	= ""
					if resetPowerGPIO not in ["",0,-1]:
						if logLevel > 0: U.logger.log(20, "checking parameters file for  resetPowerGPIO:{} enabled?".format(resetPowerGPIO) )
						resetPowerGPIO = int(resetPowerGPIO)
						if not gpioAlreadyLoaded:
							GPIO.setmode(GPIO.BCM)
							GPIO.setwarnings(False)
							gpioAlreadyLoaded = True

						GPIO.setup(resetPowerGPIO, GPIO.OUT)
						GPIO.output(resetPowerGPIO, 1)


			for ii in range(1,5):
				iis = str(ii)
				if "gpioNumberForCmdAction"+iis in sensors[sensor][devId]:
						if ( gpioNumberForCmdAction[ii] == "" or str(gpioNumberForCmdAction[ii]) != sensors[sensor][devId].get("gpioNumberForCmdAction"+iis,"") ):
							try:	gpioNumberForCmdAction[ii] 	= int(sensors[sensor][devId].get("gpioNumberForCmdAction"+iis,""))
							except: gpioNumberForCmdAction[ii] 	= ""
						if ( gpioCmdForAction[ii] == "" or str(gpioCmdForAction[ii] ) != sensors[sensor][devId].get("gpioCmdForAction"+iis,"") ):
							try:	gpioCmdForAction[ii]  			= int(sensors[sensor][devId].get("gpioCmdForAction"+iis,""))
							except:	gpioCmdForAction[ii] = ""

							if gpioNumberForCmdAction[ii] not in ["",0,-1]:
								if logLevel > 0: U.logger.log(20, "checking parameters file for  gpioNumberForCmdAction:{} enabled? for gpioCmdForAction:{} ".format(gpioNumberForCmdAction[ii], gpioCmdForAction[ii]  ) )
								gpioNumberForCmdAction[ii]  = int(gpioNumberForCmdAction[ii] )
								anyCmdDefined = True
								if not gpioAlreadyLoaded:
									GPIO.setmode(GPIO.BCM)
									GPIO.setwarnings(False)
									gpioAlreadyLoaded = True
	
								GPIO.setup(gpioNumberForCmdAction[ii] , GPIO.OUT)
								GPIO.output(gpioNumberForCmdAction[ii] , 1)


			if upd: U.logger.log(20,"setting volume:{}, mute:{}, setWakeTime:{}, keep_awake:{}, gpioCmdIndicator:>{}<, gpioCmdIndicatorInverse:{}, gpioCmdIndicatorOnTime:{:.0f}, refreshRepeat:{:.1f}, restartRepeat:{:.1f}, logLevel:{}".format( sensors[sensor][devId].get("volume"), sensors[sensor][devId].get("mute"), sensors[sensor][devId].get("setWakeTime"), keepAwake, gpioCmdIndicator, gpioCmdIndicatorInverse, gpioCmdIndicatorOnTime, refreshRepeat, restartRepeat,logLevel) )

			if upd:
				checkifRefreshSetup(restart=restart, upd=upd)

			sensorsOld = copy.copy(sensors)

		deldevID = {}			
		for devId in SENSOR:
			if devId not in sensors[sensor]:
				deldevID[devId] = 1
		for dd in	deldevID:
			del SENSOR[dd]
		if len(SENSOR) == 0:
			pass



	except Exception as e:
		U.logger.log(20, "in Line {} has error={}".format(sys.exc_info()[-1].tb_lineno, e))
		U.logger.log(20, "{}".format(sensors[sensor]))



#################################
def startSensor(devId ):
	global sensors,sensor
	global lastRestart
	global SENSOR
	global tempMuteOff, learningOn
	global i2cOrUart, sleepAfterWrite, serialPortName
	global logLevel

	startTime =time.time()

	tempMuteOff = 0
	learningOn	= False

	if devId not in SENSOR or SENSOR[devId] == "":
		SENSOR[devId] = ""
		try:
			if i2cOrUart == "uart":
				if logLevel > 0: U.logger.log(20, "started sensor,  serial port:{}, sleep:{}".format(serialPortName, sleepAfterWrite))
				SENSOR[devId] = DFRobot_DF2301Q_UART(serialPortName=serialPortName, sleepAfterWrite=sleepAfterWrite)
			else:
				if logLevel > 0: U.logger.log(20, "started sensor,  i2cAddr:{}, sleep:{}".format(DF2301Q_I2C_ADDR, sleepAfterWrite))
				SENSOR[devId] = DFRobot_DF2301Q_I2C(i2c_addr=DF2301Q_I2C_ADDR, sleepAfterWrite=sleepAfterWrite)
			SENSOR[devId].set_Params(sleepAfterWrite=sleepAfterWrite, logLevel=logLevel)
			lastRestart	= time.time()
		except	Exception as e:
			U.logger.log(20, "in Line {} has error={}".format(sys.exc_info()[-1].tb_lineno, e))
			if str(e).find("could not open port /dev/") > -1:
				data = {"sensors":{sensor:{devId:"badsenor_error:bad_port_setting_/dev/"+serialPortName}}}
				U.sendURL(data)
			del SENSOR[devId]
		return

#################################
def setMute(ON, CMDID=0):
	global lastkeepAwake, SENSOR, tempMuteOff, learningOn, currentMute
	global logLevel
	try:

		if not ON:
			if not learningOn:
				learningOn = True
				tempMuteOff = time.time() + 100
				if logLevel > 0: U.logger.log(20, "set mute OFF  expires in {:.1f} secs".format(tempMuteOff-time.time()))
				for devId in SENSOR:
						if int(sensors[sensor][devId]["volume"]) < 5:
							SENSOR[devId].set_volume(10) 			# set  volume to 10 during learning
							lastkeepAwake = time.time()
						if int(sensors[sensor][devId]["mute"]) != 0 and currentMute == "1":
							SENSOR[devId].set_mute_mode(0, calledFrom="setMute1")
							currentMute = "0"
							lastkeepAwake = time.time()
							if CMDID > 0: SENSOR[devId].play_CMDID(CMDID)
		else:
			if learningOn:
				if logLevel > 0: U.logger.log(20, "set mute back to config ")
				tempMuteOff = 0
				learningOn = False
				lastkeepAwake = 0
				checkifRefreshSetup(upd=True)
			else:
				for devId in SENSOR:
					if currentMute  != sensors[sensor][devId]["mute"] :
						SENSOR[devId].set_mute_mode(sensors[sensor][devId]["mute"], calledFrom="setMute2")
						currentMute = "1"



	except Exception as e:
		U.logger.log(20, "in Line {} has error={}".format(sys.exc_info()[-1].tb_lineno, e))
		U.logger.log(20, "{}".format(sensors[sensor]))
	return


#################################
def checkifRefreshSetup( restart=False, upd=False):
	global lastkeepAwake, keepAwake, sensors, sensor, SENSOR, tempMuteOff, learningOn
	global refreshRepeat, currentMute, badSensor, sleepAfterWrite, logLevel
	global logLevel
	try:

		if learningOn and time.time() - tempMuteOff > 0: learningOn = False

		if learningOn: return

		#if not keepAwake and not restart and not upd: return
		#U.logger.log(20, "check if re awake : {:.1f}".format(time.time() -lastkeepAwake))
		if  time.time() - lastkeepAwake > refreshRepeat or restart or upd:
			startTime = time.time()
			for devId in SENSOR:
				if True:
					SENSOR[devId].set_mute_mode(1, calledFrom="checkifRefreshSetup1")
					currentMute = "1"

				if keepAwake:
					SENSOR[devId].set_wakeup()
					SENSOR[devId].set_wake_time(int(sensors[sensor][devId]["setWakeTime"]))

				if restart and not keepAwake:
					SENSOR[devId].set_wake_time(int(sensors[sensor][devId]["setWakeTime"]))

				if True:
					SENSOR[devId].set_volume(int(sensors[sensor][devId]["volume"]))
					SENSOR[devId].set_mute_mode(sensors[sensor][devId]["mute"], calledFrom="checkifRefreshSetup2")
					SENSOR[devId].set_Params(sleepAfterWrite=sleepAfterWrite,logLevel=logLevel)
					currentMute = sensors[sensor][devId]["mute"]

				SENSOR[devId].set_notify_Status()

				if logLevel > 0: U.logger.log(20, "(re)-init sensor, timeUsed:{:.1f}, upd:{}, restart:{}, keepAwake:{}, setWakeTime:{}, mute:{}, volume:{}, learning <0?:{:.1f}, learningOn:{} ".format(time.time()-startTime,upd, restart, keepAwake, sensors[sensor][devId]["setWakeTime"], sensors[sensor][devId]["mute"],  sensors[sensor][devId]["volume"], min(999., time.time() - tempMuteOff) ,learningOn))
			lastkeepAwake = time.time()

	except Exception as e:
		badSensor +=1
		U.logger.log(20, "in Line {} has error={}".format(sys.exc_info()[-1].tb_lineno, e))


#################################
def checkifRestartConnection():
	global sensorsOld, oldRaw, lastRead, oldi2cOrUart, oldserialPortName
	global lastRestart, restartRepeat, restartON, SENSOR
	global logLevel

	try: # reset all check variables and then a read of parametes leads to a restart of the connection
		if not restartON: return
		if time.time() - lastRestart < restartRepeat: return
		oldi2cOrUart				= ""
		oldserialPortName			= ""
		sensorsOld					= {}
		oldRaw						= ""
		lastRead					= {}
		lastRestart					= time.time()
		SENSOR						= {}
	except	Exception as e:
		U.logger.log(20, "in Line {} has error={}".format(sys.exc_info()[-1].tb_lineno, e))
	return


#################################
def checkIfRestart():
	global logLevel
	try:
		if not os.path.isfile(resetFile): return
		os.remove(resetFile)

		if logLevel > 0: U.logger.log(20, "==== doing reset ====, requested by plugin")

		U.restartMyself(param="", reason="reset_requested", doPrint=True)

	except	Exception as e:
		U.logger.log(20, "in Line {} has error={}".format(sys.exc_info()[-1].tb_lineno, e))
	return


#################################
def getValues(devId):
	global sensor, sensors,	 SENSOR, badSensor, tempMuteOff, learningOn
	global keepAwake, gpioCmdIndicator
	global commandList, lastValidCmd, lastkeepAwake
	global i2cOrUart
	global cmdQueue, anyCmdDefined, gpioCmdIndicator
	global logLevel, firstCmdReceived

	try:
		CMDID = 0

		if devId not in SENSOR or SENSOR[devId] == "":
			badSensor += 1
			return "badSensor"

		for ii in range(1):
			try:
				CMDID = SENSOR[devId].get_CMDID()
			except	Exception as e:
				if logLevel > 0: U.logger.log(20, "error in received CMDID: {:3d}, badSensorCount:{}, error:{}".format(CMDID, badSensor, e)  )
				badSensor += 1
				if badSensor > 2:
					checkifRefreshSetup(restart=badSensor > 0, upd=True)
				if badSensor >= 5: return "badSensor"
				return {"cmd":0}

			if CMDID > 0: break

		if CMDID != 0:
			if logLevel > 0: U.logger.log(20, "received CMDID: {:3d}= {:20}, secs sinceLast:{:.1f}".format(CMDID, commandList.get(str(CMDID),""), time.time() - lastValidCmd) )
			if CMDID > 199 and CMDID < 209: # in learning mode? if yes make shure mute is off
				setMute(False, CMDID=CMDID)
			else:
				setMute(True)

		if CMDID == 255:
			lastkeepAwake = 0
			checkifRefreshSetup(restart=badSensor > 0, upd=True)


		if CMDID in [1,2]:
			if i2cOrUart == "uart":
				if logLevel > 0: U.logger.log(20, "firstCmdReceived:{}, lvc: {:.1f}  dtlka= {:.1f}".format(firstCmdReceived, time.time() - lastValidCmd, time.time() - lastkeepAwake) )
				if not firstCmdReceived or (time.time() - lastValidCmd > 5 and time.time() - lastkeepAwake > 5):
					lastkeepAwake = 0
					checkifRefreshSetup(restart=True, upd=True)
			else:
				if not firstCmdReceived or (time.time() - lastValidCmd > 20 and time.time() - lastkeepAwake > 20):
					lastkeepAwake = 0
					checkifRefreshSetup(restart=True, upd=True)

		if badSensor > 0:
			 U.logger.log(20, "reset bad sensor count after {:} bad sensor readings".format(badSensor)  )

		if CMDID != 0:
			lastValidCmd = time.time()
			if anyCmdDefined or gpioCmdIndicator != "": cmdQueue.put(CMDID)
		firstCmdReceived = True

		badSensor = 0
		return {"cmd":CMDID}

	except	Exception as e:
		U.logger.log(20, "in Line {} has error={}".format(sys.exc_info()[-1].tb_lineno, e))

	badSensor += 1
	if badSensor >= 5: return "badSensor"
	return ""



############################################
def checkResetPower():
	global resetPowerGPIO
	global logLevel
	if logLevel > 0: U.logger.log(20, "power off/on resetPowerGPIO:{} enabled?".format(resetPowerGPIO not in ["","-1"]) )
	if resetPowerGPIO not in ["","-1"]:  # switch power off/on twice to reset i2c / serial on sensor
		if logLevel > 0: U.logger.log(20, "power off/on twice with relay with gpio:{}".format(resetPowerGPIO))
		GPIO.output(resetPowerGPIO, 0) # relay on (power off)
		time.sleep(1)
		GPIO.output(resetPowerGPIO, 1) # relay off (power on)
		time.sleep(1)
		GPIO.output(resetPowerGPIO, 0) # relay on
		time.sleep(1)
		GPIO.output(resetPowerGPIO, 1) # relay off(power on)
		return

############################################
def startThreads():
	global threadCMD
	global logLevel

	if logLevel > 0: U.logger.log(20, "start cmd thread ")
	try:
		threadCMD = {}
		threadCMD["state"]   = "start"
		threadCMD["thread"]  = threading.Thread(name='cmdCheckIfGPIOon', target=cmdCheckIfGPIOon)
		threadCMD["state"]   = "running"
		threadCMD["thread"].start()

	except  Exception as e:
		if logLevel > 0: U.logger.log(20,"", exc_info=True)
	return

############################################
def cmdCheckIfGPIOon():
	global gpioCmdForAction, gpioNumberForCmdAction, anyCmdDefined
	global gpioCmdIndicator, gpioCmdIndicatorInverse, gpioCmdIndicatorOnTime
	global cmdQueue, threadCMD
	global logLevel
	try:
		if logLevel > 0: U.logger.log(20, "start  loop")
		while threadCMD["state"] == "running":
			try:
				ledOn = 0
				while not cmdQueue.empty():
					cmd = cmdQueue.get()
					if gpioCmdIndicator != "":
						ledOn = time.time()
						GPIO.output(gpioCmdIndicator, gpioCmdIndicatorInverse != "0")
						#U.logger.log(20, "setting GPIO{} off/on ".format(gpioCmdIndicator) )
					if anyCmdDefined:
						for ii in range(1,5):
							if gpioNumberForCmdAction[ii] == "": continue
							if gpioCmdForAction[ii] == "": continue
							if gpioCmdForAction[ii] == cmd:
								if logLevel > 0: U.logger.log(20, "setting  item({}) GPIO{} off/on due to receiving cmd:{} ".format(ii, gpioNumberForCmdAction[ii], gpioCmdForAction[ii]) )
								GPIO.output(gpioNumberForCmdAction[ii], 0)
								time.sleep(0.5)
								GPIO.output(gpioNumberForCmdAction[ii], 1)
				if ledOn > 0:
					time.sleep(max(0,gpioCmdIndicatorOnTime/1000. - (time.time() - ledOn)))
					GPIO.output(gpioCmdIndicator, gpioCmdIndicatorInverse == "0")

			except	Exception as e:
				U.logger.log(20, "in Line {} has error={}".format(sys.exc_info()[-1].tb_lineno, e))
				time.sleep(10)

			if not (anyCmdDefined or gpioCmdIndicator): time.sleep(10)
			time.sleep(0.2)

	except	Exception as e:
		U.logger.log(20, "in Line {} has error={}".format(sys.exc_info()[-1].tb_lineno, e))
	if logLevel > 0: U.logger.log(20, "ended  loop, state:{}".format(threadCMD["state"] ))


############################################
def execSensorLoop():
	global sensor, sensors, badSensor
	global SENSOR, sensorMode
	global oldRaw, lastRead
	global startTime, lastMeasurement, lastRestart, restartRepeat, restartON
	global oldi2cOrUart, oldserialPortName, sensorsOld, keepAwake, lastkeepAwake, tempMuteOff, serialPortName
	global gpioCmdIndicator, gpioCmdIndicatorInverse, gpioCmdIndicatorOnTime
	global refreshRepeat, gpioAlreadyLoaded
	global currentMute
	global sleepAfterWrite, oldSleepAfterWrite, commandList, lastValidCmd
	global resetPowerGPIO
	global gpioCmdForAction, gpioNumberForCmdAction, anyCmdDefined
	global cmdQueue, logLevel
	global threadCMD
	global firstCmdReceived



	firstCmdReceived				= False
	logLevel						= 1
	cmdQueue						= queue.Queue()
	gpioCmdForAction				= ["","","","",""]
	gpioNumberForCmdAction			= ["","","","",""]
	anyCmdDefined					= False

	serialPortName					= ""
	resetPowerGPIO					= ""
	commandList						= {}
	lastValidCmd					= 0
	sleepAfterWrite 				= 0.1
	oldSleepAfterWrite 				= ""

	currentMute						= "0"
	gpioAlreadyLoaded				= False
	refreshRepeat					= 50
	gpioCmdIndicatorOnTime			= 1000
	gpioCmdIndicatorInverse			= "0"
	gpioCmdIndicator				= ""
	restartON						= True
	restartRepeat					= 400
	lastRestart						= time.time()
	tempMuteOff						= 0
	lastkeepAwake					= 0
	keepAwake						= False
	oldi2cOrUart					= ""
	oldserialPortName				= ""
	sensorsOld						= {}
	sendToIndigoSecs				= 85
	startTime						= time.time()
	lastMeasurement					= time.time()
	oldRaw							= ""
	lastRead						= 0
	sensorRefreshSecs				= 0.3
	sensors							= {}
	sensor							= G.program
	badSensor						= 0
	SENSOR							= {}
	myPID							= str(os.getpid())
	U.setLogging()
	U.killOldPgm(myPID,G.program+".py")# kill old instances of myself if they are still running

	#U.resetI2cBus()

	if U.getIPNumber() > 0:
		time.sleep(10)
		exit()

	readParams()

	time.sleep(1)

	lastRead = time.time()

	U.echoLastAlive(G.program)

	startThreads()

	lastAliveSend		= time.time()
	theValues 			= {}
	sensorWasBad 		= False
	while True:
		try:
			extraSleep = 0
			tt = time.time()
			sendData = False
			data = {}
			theValues = {}
			theValues["cmd"] = ""
			if sensor in sensors:
				data = {"sensors": {sensor:{}}}
				for devId in sensors[sensor]:
					theValues = getValues(devId)

					if theValues == "":
						continue

					data["sensors"][sensor][devId] = "alive"

					if theValues == "badSensor" or type(theValues) == type(" "):
						sensorWasBad = True
						if badSensor in [5,6]:
							extraSleep = 2
							sendData = True
							data["sensors"][sensor][devId] = "badSensor"
							break

						elif badSensor > 10:
							checkResetPower()
							U.restartMyself(param="", reason="badsensor", doPrint=True)

						extraSleep = 2
						break

					elif theValues["cmd"] != 0:
						data["sensors"][sensor][devId] = theValues
						sendData = True

					if tt - sendToIndigoSecs > lastAliveSend:
						sendData = True

			if sendData:
				U.sendURL(data, wait=False)
				#U.makeDATfile(G.program, data)
				extraSleep  += 0.01
				lastRead = time.time() + 4.
				lastAliveSend = time.time()



			U.echoLastAlive(G.program)

			if  tt - lastRead > 2.:
				checkIfRestart()
				checkifRestartConnection()
				readParams()
				lastRead = time.time()
				checkifRefreshSetup()

			#U.logger.log(20, "dt time last{:.1f},  start:{:.1f}".format(time.time()  - lastMeasurement, time.time()  - startTime))


			dtLast = time.time()  - lastMeasurement
			slTime = max(0, sensorRefreshSecs + extraSleep  - (time.time()  - lastMeasurement) )
			time.sleep(slTime )
			lastMeasurement = time.time()


		except	Exception as e:
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


