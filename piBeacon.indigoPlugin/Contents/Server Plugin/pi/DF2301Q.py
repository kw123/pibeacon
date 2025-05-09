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

version			= 1.2

G.program = "DF2301Q"

GLOB_resetFile						= G.homeDir+"temp/DF2301Q.reset"
GLOB_restartFile					= G.homeDir+"temp/DF2301Q.restart"
GLOB_commandFile					= G.homeDir+"temp/DF2301Q.cmd"
GLOB_expectResponseAfter			= 10 # seconds
GLOB_maxRestartConnections			= 5  # count

DF2301Q_I2C_sleepAfterReadWrite = 200 # msec
DF2301Q_UART_sleepAfterReadWrite= 100 # msec

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
		self._addr = i2c_addr
		self._i2c = smbus.SMBus(bus)
		self.debug = 0
		self.sleepAfterWrite = sleepAfterWrite/1000.
		#super(DFRobot_DF2301Q_I2C, self).__init__()

	def set_Params(self, sleepAfterWrite=DF2301Q_I2C_sleepAfterReadWrite,logLevel=0, commandList={}):
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

	def reset_module(self):
		U.logger.log(20,": reset not implemented for i2c interface")

	def set_need_ack(self):
		U.logger.log(20,": set_need_ack not implemented for i2c interface")

	def set_need_string(self):
		U.logger.log(20,": set_need_string not implemented for i2c interface")

	def close_Port(self):
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
		self._ser = serial.Serial("/dev/"+serialPortName, baudrate=DF2301Q_UART_BAUDRATE, bytesize=8, parity='N', stopbits=1, timeout=0.5)
		if self._ser.isOpen:
			self.close_Port()

		self._ser.open()
		self.messagesSend = []
		super(DFRobot_DF2301Q_UART, self).__init__()
		#self.reset_module()

	def close_Port(self):
		if self._ser.isOpen:
			self._ser.close()
		return 

	def set_Params(self, sleepAfterWrite=0, logLevel=-1, commandList={}):
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
		v = int(set_value)
		if self.debug > 1: U.logger.log(20, "value:{}".format(v) )
		self.setting_CMD( DF2301Q_UART_MSG_CMD_SET_VOLUME, max(0,min(v,20)))


	def set_mute_mode(self,  set_value, calledFrom=""):
		m = 0 != int(set_value)
		if self.debug > 1: U.logger.log(20,": {}, from:{}".format(m, calledFrom))
		self.setting_CMD( DF2301Q_UART_MSG_CMD_SET_MUTE, m)


	def set_wake_time(self,  set_value):
		if self.debug > 1: U.logger.log(20, "value:{}".format(set_value) )
		self.setting_CMD( DF2301Q_UART_MSG_CMD_SET_WAKE_TIME, set_value & 0xFF)


	def set_wakeup(self):
		if self.debug > 1: U.logger.log(20, "value:{}".format(1) )
		self.setting_CMD( DF2301Q_UART_MSG_CMD_SET_ENTERWAKEUP, 1)



	def set_need_ack(self): 
		if self.debug > 1: U.logger.log(20, "value:{}".format(1) )
		self.setting_CMD( DF2301Q_UART_MSG_CMD_SET_NEEDACK, 1)


	def set_need_string(self): 
		if self.debug > 1: U.logger.log(20, "value:{}".format(1) )
		self.setting_CMD( DF2301Q_UART_MSG_CMD_SET_NEEDSTRING, 1)



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

		if self.debug > 2: U.logger.log(20, "msg:{}".format(msg) )
		self._send_packet(msg)


	def setting_CMD_UP(self):
		try:
			msg = self.uart_msg()
			msg.msg_type = DF2301Q_UART_MSG_TYPE_CMD_UP
			msg.msg_cmd = DF2301Q_UART_MSG_CMD_ASR_RESULT
			msg.msg_seq = self._send_sequence
			self._send_sequence += 1
			msg.msg_data[0] = 0
			msg.msg_data[1] = 0
			msg.data_length = 2
	
			if self.debug > 2: U.logger.log(20, "msg:{}".format(msg) )
			self._send_packet(msg)
		except Exception as e:
			U.logger.log(20, "in Line {} has error={}".format(sys.exc_info()[-1].tb_lineno, e))

	def set_notify_Status(self): # does not work
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

		if self.debug > 2: U.logger.log(20, "msg:{}".format(str(msg)) )
		self._send_packet(msg)



	def get_wakeTime(self): #dummy not done yet
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

		self._send_packet(msg)


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
			self._send_packet(msg)
		except Exception as e:
			U.logger.log(20, "in Line {} has error={}".format(sys.exc_info()[-1].tb_lineno, e))


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
		except Exception as e:
			U.logger.log(20, "in Line {} has error={}".format(sys.exc_info()[-1].tb_lineno, e))
			U.logger.log(20, "data:{}, msg:{}".format(data, str(msg.msg_data)))



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
		while self._ser.in_waiting:
			xx = self._ser.read(1)
			allChar += xx.hex().upper()
			receive_char = ord(xx)
			if self.debug > 2: U.logger.log(20, "receive_char:{}".format(receive_char))

			if(self.REV_STATE_HEAD0 == rev_state): # begin of receive of data 			== 00
				if(DF2301Q_UART_MSG_HEAD_LOW == receive_char):#							== F4
					rev_state = self.REV_STATE_HEAD1

			elif(self.REV_STATE_HEAD1 == rev_state):#									== 01
				if(DF2301Q_UART_MSG_HEAD_HIGH == receive_char):#						== F5
					rev_state = self.REV_STATE_LENGTH0
				else:
					rev_state = self.REV_STATE_HEAD0

			elif(self.REV_STATE_LENGTH0 == rev_state):#									== 02
				msg.data_length = receive_char
				rev_state = self.REV_STATE_LENGTH1

			elif(self.REV_STATE_LENGTH1 == rev_state):#									== 03
				msg.data_length += receive_char << 8
				rev_state = self.REV_STATE_TYPE

			elif(self.REV_STATE_TYPE == rev_state):#									== 04
				msg.msg_type = receive_char
				rev_state = self.REV_STATE_CMD

			elif(self.REV_STATE_CMD == rev_state):#										== 05
				msg.msg_cmd = receive_char
				rev_state = self.REV_STATE_SEQ

			elif(self.REV_STATE_SEQ == rev_state):#										== 06
				msg.msg_seq = receive_char
				if(msg.data_length > 0):
					rev_state = self.REV_STATE_DATA
					data_rev_count = 0
				else:
					rev_state = self.REV_STATE_CKSUM0

			elif(self.REV_STATE_DATA == rev_state): # this actual data; [0] == cmd id 	== 07
				msg.msg_data[data_rev_count] = receive_char
				data_rev_count += 1
				if(msg.data_length == data_rev_count):
					rev_state = self.REV_STATE_CKSUM0

			elif(self.REV_STATE_CKSUM0 == rev_state):  # chk_sum is  not used			== 08
				chk_sum = receive_char
				rev_state = self.REV_STATE_CKSUM1

			elif(self.REV_STATE_CKSUM1 == rev_state):   # chk_sum is  not used			== 09
				chk_sum += receive_char << 8
				rev_state = self.REV_STATE_TAIL

			elif(self.REV_STATE_TAIL == rev_state):# received the end, set the cmd id=	== 0a
				if(DF2301Q_UART_MSG_TAIL == receive_char):#								== FB
					if(DF2301Q_UART_MSG_TYPE_CMD_UP == msg.msg_type):#					== A0
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
			for xx in allChar:
				xx = xx[:-2] # -2, skip "FB" ==  DF2301Q_UART_MSG_TAIL
				try: 
					ll = int(xx[0:2],16)
				except: continue
				if len(xx) < 12:
					U.logger.log(20, "bad data len:{}; >>{}<<".format(len(xx), xx))
					continue
				if len(xx) > 26:
					U.logger.log(20, "bad data len:{}; >>{}<<".format(len(xx), xx))
					continue

				ii += 1
				length.append(ll)
				typ.append(xx[4:6])
				tt = int(typ[-1],16)
				cmd.append(xx[6:8])
				cc =int(cmd[-1],16)
				seq.append(int(xx[8:10],16))
				data.append(xx[10:10+ll*2])
				chksum.append(xx[10+ll*2:]) #
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


				if tt == DF2301Q_UART_MSG_TYPE_NOTIFY:				 																	# A3 
					if  cc == DF2301Q_UART_MSG_CMD_NOTIFY_STATUS:  																		# 9A
						try:	iData = int(data[-1][2:],16)
						except:	iData = 0
						#U.logger.log(20, "iData >>{},{}<<".format(data[-1], iData))
						if   iData == DF2301Q_UART_MSG_DATA_NOTIFY_POWERON:			responses[ii] = 800 # power on 									# B0
						elif iData == DF2301Q_UART_MSG_DATA_NOTIFY_WAKEUPENTER:		responses[ii] = 801 # wake up   								# 91
						elif iData == DF2301Q_UART_MSG_DATA_NOTIFY_WAKEUPEXIT:		responses[ii] = 802 # wake up exit								# B2
						elif iData == DF2301Q_UART_MSG_DATA_NOTIFY_PLAYSTART:		responses[ii] = 803 # PLAYSTART									# B3
						elif iData == DF2301Q_UART_MSG_DATA_NOTIFY_PLAYEND:			responses[ii] = 804 # PLAYEND									# B4

				elif tt == DF2301Q_UART_MSG_TYPE_ACK:																					# A2
					if cc == DF2301Q_UART_MSG_CMD_SET_CONFIG:						responses[ii] = 820 # config command received sucessully		# 96
					if cc == DF2301Q_UART_MSG_CMD_RESET_MODULE:						responses[ii] = 821 # reset module								# 95

				elif tt== DF2301Q_UART_MSG_TYPE_CMD_UP: 																				# A0
					try:	iData = int(data[-1][0:2],16)
					except:	iData = 0
					if cc == DF2301Q_UART_MSG_CMD_ASR_RESULT:						responses[ii] = iData #  real command received					# 91


			if self.uart_cmd_ID == 0 and len(responses) > 0:
				for res in responses:
					if self.uart_cmd_ID  < res: self.uart_cmd_ID  = res

		except Exception as e:
			pass
			U.logger.log(20, "in Line {} has error={}".format(sys.exc_info()[-1].tb_lineno, e))

		try:
			if self.debug > 1 and data_rev_count > 0: 
				U.logger.log(20, "data_rev_count:{}, cmd_ID:{},  msg:{}".format(data_rev_count, self.uart_cmd_ID, str(allChar)) )
				for ii in range(len(length)):
					U.logger.log(20, "   #:{},  length:{:1}, typ:{:2},  cmd:{:2}; chksum:{:4}, seq:{:3d}=={:<3d} replySeq?,  data:{:<6} {}, resp:{}=={} ".format(ii, length[ii], typ[ii], cmd[ii] , chksum[ii] , seq[ii], replySeq[ii], data[ii], data[ii][0:2], responses[ii],  self.commandList.get(str(responses[ii]),"") ) )
	 
		except Exception as e:
			U.logger.log(20, "in Line {} has error={}".format(sys.exc_info()[-1].tb_lineno, e))

		return data_rev_count, allChar


# ===========================================================================
# read params
# ===========================================================================

###############################
def readParams():
	global sensors, logDir, sensor,	 displayEnable
	global SENSOR, sensorOld
	global oldRaw, lastRead
	global startTime, lastMeasurement, oldi2cOrUart, oldserialPortName, keepAwake, lastkeepAwake
	global restartRepeat, refreshRepeat
	global sleepAfterWrite, oldSleepAfterWrite, commandList
	global i2cOrUart, serialPortName
	global gpioCmdForAction, gpioNumberForCmdAction, gpioInverseAction, gpioOnTimeAction, anyCmdDefined, unixCmdAction, unixCmdVoiceNo
	global lastReset, restartConnectionCounter, badSensor
	global logLevel, tmpMuteOff, learningOn, expectResponse, currentMute, setWakeTime
	global GPIOZERO
	global reactOnlyToCommands, maxCommandId, minErrorCmdID, offCommand
	global gpioUsed
	global resetGPIOClass
	try:


		inp, inpRaw, lastRead2 = U.doRead(lastTimeStamp=lastRead)
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



		for devId in sensors[sensor]:

			# anything new?
			newParams = False
			if devId not in sensorOld:
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

			if logLevel > 0: U.logger.log(10,"{} reading new parameters for devId:{}".format(G.program, devId) )

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
			if devId not in serialPortName: 			serialPortName[devId] 				= "serial0"
			if devId not in reactOnlyToCommands: 		reactOnlyToCommands[devId] 			= [x for x in range(maxCommandId)]
			if devId not in resetGPIOClass: 			resetGPIOClass[devId] 				= 999999999
			resetGPIOClass[devId] = float(sensors[sensor][devId].get("resetGPIOClass",999999999))
			if devId not in ignoreUntilEndOfLearning:	ignoreUntilEndOfLearning[devId]		= -1
			
			for ii in range(1,6):
				unixCmdAction[ii] =  sensors[sensor][devId].get("unixCmdAction"+str(ii),"")
				try: 	unixCmdVoiceNo[ii] = int(sensors[sensor][devId].get("unixCmdVoiceNo"+str(ii),"-1"))
				except: unixCmdVoiceNo[ii] = -1
				if unixCmdAction[ii] != "": anyCmdDefined = True

			U.logger.log(20, "unixCmdVoiceNo:{}; unixCmdAction:{} ".format(unixCmdVoiceNo, unixCmdAction) )
			
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
			U.logger.log(20, "devId:{}; reactOnlyToCommands:{} ".format(devId, reactOnlyToCommands) )

			if "logLevel" in sensors[sensor][devId]:
				if str(logLevel) != sensors[sensor][devId].get("logLevel","0"): upd = True
				logLevel = int(sensors[sensor][devId].get("logLevel","1"))
			else:
				logLevel = 0

			restart = ""
			i2cOrUart[devId] =  sensors[sensor][devId].get("i2cOrUart","")	
			if devId not in oldi2cOrUart or (i2cOrUart[devId] != "" and oldi2cOrUart[devId] != i2cOrUart[devId]):	restart = True
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
					restart = "portname changed"
				oldserialPortName[devId]  = copy.copy(serialPortName[devId])
				time.sleep(4)
			else:
				if "i2cSleepAfterWrite" in sensors[sensor][devId]:
					if  devId not in oldSleepAfterWrite or (oldSleepAfterWrite[devId] != "" and  sleepAfterWrite[devId] != oldSleepAfterWrite[devId]):
						upd = True
					sleepAfterWrite[devId] = float(sensors[sensor][devId].get("i2cSleepAfterWrite",str(DF2301Q_I2C_sleepAfterReadWrite)))
				else:
					sleepAfterWrite[devId] = 50.
				oldSleepAfterWrite[devId] = copy.copy(sleepAfterWrite[devId])

			upd = ""
			if devId not in SENSOR or restart:
				upd = "devId not present"
				startSensor(devId)
				if devId not in SENSOR:
					return

			if devId not in sensorOld: 
				upd = "devId not in old present"

			elif "mute" in sensors[sensor][devId] and (upd or sensors[sensor][devId].get("mute") != sensorOld[devId].get("mute")):
				upd = "change in mute"

			elif "volume" in sensors[sensor][devId] and ( sensors[sensor][devId].get("volume") != sensorOld[devId].get("volume")):
				upd = "change in volme"

			elif "setWakeTime" in sensors[sensor][devId] and (sensors[sensor][devId].get("setWakeTime") != sensorOld[devId].get("setWakeTime")):
				upd = "change in wake time"

			setGPIOconfig(devIdSelect=devId)


			if upd and logLevel > 0: U.logger.log(20,"devId:{}; reason:{}, serialPortName:{},  setting volume:{}, mute:{}, setWakeTime:{}, keep_awake:{}, refreshRepeat:{:.1f}, restartRepeat:{:.1f}, logLevel:{}".format(devId, upd, serialPortName[devId], sensors[sensor][devId].get("volume"), sensors[sensor][devId].get("mute"), setWakeTime[devId], keepAwake[devId], refreshRepeat[devId], restartRepeat[devId],logLevel) )

			if upd:
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
		U.logger.log(20, "{}".format(sensors[sensor]))




#################################
def setGPIOconfig(devIdSelect=0, force=False):
	global sensors, sensor
	global SENSOR
	global gpioCmdForAction, gpioNumberForCmdAction, gpioInverseAction, gpioOnTimeAction, anyCmdDefined
	global logLevel
	global GPIOZERO, gpioUsed
	try:
		if devIdSelect != 0: devIdList = [devIdSelect]
		else:
			devIdList = []
			for xx in sensors[sensor]:
				devIdList.append(xx)

		if logLevel > 1: U.logger.log(20, "starting  devIdSelect:{}, force:{}, devIds:{}".format(devIdSelect, force, devIdList) )
		for devId in devIdList:
			for ii in range(1,6):
				if gpioUsed[ii] == 0 or force: 
					iis = str(ii)
					if force:
						gpioNumberForCmdAction[ii] = ""
						gpioCmdForAction[ii] = ""
						gpioOnTimeAction[ii] = ""
						gpioInverseAction[ii] = ""
					try:
						if "gpioNumberForCmdAction"+iis in sensors[sensor][devId]:
							if logLevel > 1: U.logger.log(20, "setting #{}, devId:{}".format(iis, devId) )
							changed = False
							if ( gpioNumberForCmdAction[ii] == "" or str(gpioNumberForCmdAction[ii])	!= sensors[sensor][devId].get("gpioNumberForCmdAction"+iis,"") ):
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

							if ( gpioCmdForAction[ii] == "" 		or str(gpioCmdForAction[ii] ) 		!= sensors[sensor][devId].get("gpioCmdForAction"+iis,"") ):
								try:	
										gpioCmdForAction[ii]  			= int(sensors[sensor][devId].get("gpioCmdForAction"+iis,""))
										changed = True
										gpioUsed[ii] = 1
								except:	gpioCmdForAction[ii] = ""

							if ( gpioOnTimeAction[ii] == "" 		or str(gpioOnTimeAction[ii] ) 		!= sensors[sensor][devId].get("gpioOnTimeAction"+iis,"") ):
								try:	
										gpioOnTimeAction[ii]  			= float(sensors[sensor][devId].get("gpioOnTimeAction"+iis,""))
										changed = True
										gpioUsed[ii] = 1
								except:	gpioOnTimeAction[ii] = ""

							if ( gpioInverseAction[ii] == "" 		or str(gpioInverseAction[ii] ) 		!= sensors[sensor][devId].get("gpioInverseAction"+iis,"") ):
								try:	
										gpioInverseAction[ii]  			= sensors[sensor][devId].get("gpioInverseAction"+iis,"")
										changed = True
										gpioUsed[ii] = 1
								except:	gpioInverseAction[ii] = ""

							if logLevel > 2: U.logger.log(20, "devId:{}; checking parameters file for #{}  changed:{}; gpioNumberForCmdAction:>{}< enabled? for gpioCmdForAction:>{}<, ontime:>{}<, inverse:{} conditions: gpioInverse==0/1:{}  gpioOnTime==float:{}  gpioCmd==int:{}  gpioNumber==int:{} ".format(devId, ii,changed, gpioNumberForCmdAction[ii], gpioCmdForAction[ii], gpioOnTimeAction[ii], gpioInverseAction[ii] , gpioInverseAction[ii] in ["0","1"] , isinstance(gpioOnTimeAction[ii],float) , isinstance(gpioCmdForAction[ii], int) , isinstance(gpioNumberForCmdAction[ii], int) ) )
							if changed:
								if gpioInverseAction[ii] in ["0","1"] and isinstance(gpioOnTimeAction[ii],float) and isinstance(gpioCmdForAction[ii], int) and isinstance(gpioNumberForCmdAction[ii], int):
									if logLevel > 1: U.logger.log(20, "devId:{}; checking parameters file for #{}  gpioNumberForCmdAction:>{}< enabled? for gpioCmdForAction:>{}<, ontime:>{}<, inverse:{} ".format(devId, ii, gpioNumberForCmdAction[ii], gpioCmdForAction[ii], gpioOnTimeAction[ii], gpioInverseAction[ii]  ) )
									anyCmdDefined = True
									if k_useGPIO:
										GPIO.setup(gpioNumberForCmdAction[ii], GPIO.OUT)
										GPIO.output(gpioNumberForCmdAction[ii], gpioInverseAction[ii] == "0")  
									else:
										try: GPIOZERO[gpioNumberForCmdAction[ii]].close()
										except: pass
										GPIOZERO[gpioNumberForCmdAction[ii]] = gpiozero.LED(gpioNumberForCmdAction[ii])
										getattr(GPIOZERO[gpioNumberForCmdAction[ii]], "on" if gpioInverseAction[ii] == "0" else "off")()
					except Exception as e:
						U.logger.log(20, "in Line {} has error={}".format(sys.exc_info()[-1].tb_lineno, e))


	except Exception as e:
		U.logger.log(20, "in Line {} has error={}".format(sys.exc_info()[-1].tb_lineno, e))


#################################
def startSensor(devId):
	global sensors,sensor
	global lastRestart
	global SENSOR
	global tmpMuteOff, learningOn
	global i2cOrUart, sleepAfterWrite, serialPortName, lastkeepAwake
	global logLevel, commandList
	global lastReset, expectResponse, restartConnectionCounter

	startTime =time.time()

	tmpMuteOff[devId] = 0

	if devId in SENSOR:
		SENSOR[devId].close_Port()
		del SENSOR[devId]


	if devId not in SENSOR:
		lastkeepAwake[devId] = time.time() 
		currentMute[devId] = "0"
		learningOn[devId] = False
		restartConnectionCounter[devId] += 1
		try:
			if i2cOrUart[devId] == "uart":
				if logLevel > 0: U.logger.log(20, "devId:{}; started sensor,  serial port:{}, sleep:{}".format(devId, serialPortName[devId], sleepAfterWrite[devId]))
				if cmdCheckSerialPort(devId):
					SENSOR[devId] = DFRobot_DF2301Q_UART(serialPortName=serialPortName[devId], sleepAfterWrite=sleepAfterWrite[devId])
				else:
					time.sleep(20)
			else:
				if logLevel > 0: U.logger.log(20, "devId:{}; started sensor,  i2cAddr:{}, sleep:{}".format(devId, DF2301Q_I2C_ADDR, sleepAfterWrite[devId]))
				SENSOR[devId] = DFRobot_DF2301Q_I2C(i2c_addr=DF2301Q_I2C_ADDR, sleepAfterWrite=sleepAfterWrite[devId])

			if devId in SENSOR:
				#if logLevel > 0: U.logger.log(20, "devId:{}; commandList:{}".format(devId, str(commandList[devId])[0:100] ))
				SENSOR[devId].set_Params(sleepAfterWrite=sleepAfterWrite[devId], logLevel=logLevel, commandList=commandList[devId] )
				lastRestart	= time.time()
		except Exception as e:
			U.logger.log(20, "in Line {} has error={}".format(sys.exc_info()[-1].tb_lineno, e))
			if str(e).find("could not open port /dev/") > -1:
				data = {"sensors":{sensor:{devId:"badsenor_error:bad_port_setting_/dev/"+serialPortName[devId]}}}
				U.sendURL(data)
			SENSOR[devId].close_Port()
			del SENSOR[devId]
		return

#################################
def setMute(devId, ON, CMDID=0):
	global lastkeepAwake, SENSOR, tmpMuteOff, learningOn, currentMute, ignoreUntilEndOfLearning
	global logLevel
	try:

		if ON:
			if  ignoreUntilEndOfLearning[devId] > 0 and not learningOn[devId]:
				learningOn[devId] = True
				tmpMuteOff[devId] = time.time() + 100
				if logLevel > 0: U.logger.log(20, "devId:{}; set mute OFF  expires in {:.1f} secs".format(devId, tmpMuteOff[devId]-time.time()))
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
			if learningOn[devId]:
				if logLevel > 0: U.logger.log(20, "devID:{}; set mute back to config ".format(devId))
				tmpMuteOff[devId] = 0
				learningOn[devId] = False
				lastkeepAwake[devId] = 0
				checkifRefreshSetup(devId, upd=True)
			else:
				for devId in SENSOR:
					if currentMute[devId]  != sensors[sensor][devId]["mute"] :
						SENSOR[devId].set_mute_mode(sensors[sensor][devId]["mute"], calledFrom="setMute2")
						setExpectResponse(devId)
						currentMute[devId] = "1"

	except Exception as e:
		U.logger.log(20, "in Line {} has error={}".format(sys.exc_info()[-1].tb_lineno, e))
		U.logger.log(20, "{}".format(sensors[sensor]))
	return


#################################
def checkifRefreshSetup(devId,  restart=False, upd=False):
	global lastkeepAwake, keepAwake, sensors, sensor, SENSOR, tmpMuteOff, learningOn
	global refreshRepeat, currentMute, badSensor, sleepAfterWrite, logLevel
	global logLevel, commandList, expectResponse, setWakeTime
	try:

		if learningOn[devId] and time.time() - tmpMuteOff[devId] > 0: learningOn[devId] = False

		if learningOn[devId]: return

		#if not keepAwake and not restart and not upd: return
		#U.logger.log(20, "check if re awake : {}, {}".format(lastkeepAwake, refreshRepeat))
		if  time.time() - lastkeepAwake[devId] > refreshRepeat[devId] or restart or upd:
			startTime = time.time()
			if True:
				SENSOR[devId].set_mute_mode(1, calledFrom="checkifRefreshSetup1")
				setExpectResponse(devId)
				currentMute[devId] = "1"

			if keepAwake[devId]:
				SENSOR[devId].set_wake_time(setWakeTime[devId])
				setExpectResponse(devId)
				SENSOR[devId].set_wakeup()

			if restart and not keepAwake[devId]:
				expectResponse[devId] = time.time()
				SENSOR[devId].set_wake_time(setWakeTime[devId])

			if True:
				setExpectResponse(devId)
				SENSOR[devId].set_volume(int(sensors[sensor][devId]["volume"]))
				SENSOR[devId].set_mute_mode(sensors[sensor][devId]["mute"], calledFrom="checkifRefreshSetup2")
				SENSOR[devId].set_Params(sleepAfterWrite=sleepAfterWrite[devId], logLevel=logLevel )
				currentMute[devId] = sensors[sensor][devId]["mute"]

			if logLevel > 0: U.logger.log(20, "devId:{}; (re)-init sensor, timeUsed:{:.1f}, upd:{}, restart:{}, keepAwake:{}, setWakeTime:{}, mute:{}, volume:{}, learning <0?:{:.1f}, learningOn:{} ".format(devId, time.time()-startTime,upd, restart, keepAwake[devId], setWakeTime[devId], sensors[sensor][devId]["mute"],  sensors[sensor][devId]["volume"], min(999., time.time() - tmpMuteOff[devId]) ,learningOn[devId]))
			lastkeepAwake[devId] = time.time()

	except Exception as e:
		badSensor[devId] +=1
		U.logger.log(20, "in Line {} has error={}".format(sys.exc_info()[-1].tb_lineno, e))



############ check if we expect a response soon #####################
def setNoExpectResponse(devId, calledfrom=""):
	global expectResponse, restartConnectionCounter
	expectResponse[devId] = time.time() + 9999999999
	restartConnectionCounter[devId] = 0
	lastkeepAwake[devId] = time.time()
	if logLevel > 1: U.logger.log(20, "devId:{}; setting  expectResponse to {:.1f}, called from:{}".format(devId, 9999999999, calledfrom ))
	return 

#################################
def setExpectResponse(devId):
	global expectResponse, logLevel
	expectResponse[devId] = time.time() + GLOB_expectResponseAfter
	if logLevel > 1: U.logger.log(20, "devId:{}; setting  expectResponse to {:.1f}".format(devId, GLOB_expectResponseAfter))

	return 

#################################
def checkExpectResponse(devId):
	global expectResponse, i2cOrUart, checkExpectResponse, restartConnectionCounter, minRestartConnectionTime

	try:
		if i2cOrUart[devId] == "uart":
		
			if expectResponse[devId] - time.time() > 0 and expectResponse[devId] - time.time() < 99: 
				if logLevel > 1: U.logger.log(20, "devId:{}; testing if response by now, time left:{:.1f} ".format(devId, - (time.time()-expectResponse[devId]) ))
		
			if time.time() - expectResponse[devId] > 0: 
				if logLevel > 0: U.logger.log(20, "devId:{}; expected a response by now, not received for:{:.1f} secs,  reconnect counter: {}".format(devId, time.time()-expectResponse[devId], restartConnectionCounter[devId] ))
				if restartConnectionCounter[devId] > GLOB_maxRestartConnections: 
					if logLevel > 0: U.logger.log(20, "devId:{}; expected a response by now,  too many reconnects, do restart of program ".format(devId))
					checkIfRestart(force=True)
					return 3
		
				if logLevel > 0: U.logger.log(20, "devId:{}; expected a response by now, not received for:{:.1f} secs, do restart connection  ".format(devId, time.time()-expectResponse[devId] ))
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
	global logLevel
	try:
		if os.path.isfile(GLOB_restartFile): 
			os.remove(GLOB_restartFile)
		else: 
			if not force: return

		if logLevel > 0:
			if not	force: U.logger.log(20, "==== doing restart ====, requested by plugin")
			else:	force: U.logger.log(20, "==== doing restart ====, requested by program")

		U.restartMyself(param="", reason="reset_requested "+GLOB_restartFile+" exists", doPrint=True)

	except Exception as e:
		U.logger.log(20, "in Line {} has error={}".format(sys.exc_info()[-1].tb_lineno, e))
	return

#################################
def checkIfReset():
	global logLevel, SENSOR
	try:
		if not os.path.isfile(GLOB_resetFile): return
		os.remove(GLOB_resetFile)

		for devId in SENSOR:
			if logLevel > 0: U.logger.log(20, "devID:{}; ==== doing reset ====, requested by plugin".format(devId ))
			doReset(devId)
			checkIfRestartConnection(devId, force=True)

	except Exception as e:
		U.logger.log(20, "in Line {} has error={}".format(sys.exc_info()[-1].tb_lineno, e))
	return

#################################
def doReset(devId, force=False):
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
			if logLevel > 0: U.logger.log(20, "devID:{}; ==== exec commands: {}".format(devId, data))
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
				logLevel = data["loglevel"]
				SENSOR[devId].set_Params(logLevel=logLevel)
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
def getValues(devId, wait=0):
	global sensor, sensors,	 SENSOR, badSensor, tmpMuteOff, learningOn
	global keepAwake
	global commandList, lastValidCmd, lastkeepAwake
	global i2cOrUart
	global cmdQueue, anyCmdDefined
	global logLevel, firstCmdReceived, lastCMDID
	global reactOnlyToCommands, lastCMDID, ignoreUntilEndOfLearning

	try:
		CMDID = 0
		if wait >0: time.sleep(wait)

		if devId not in SENSOR:
			badSensor[devId] += 1
			return "badSensor"

		for ii in range(1):
			try:
				CMDID = SENSOR[devId].get_CMDID()
			except Exception as e:
				if logLevel > 0: U.logger.log(20, "devID:{}; error in received CMDID: {:3d}, badSensorCount:{}, error:{}".format(devId, CMDID, badSensor[devId], e)  )
				badSensor[devId] += 1
				if badSensor[devId] > 2:
					checkifRefreshSetup(devId, restart=badSensor[devId] > 0, upd=True)
				if badSensor[devId] >= 5: return "badSensor"
				return {"cmd":0}

			if CMDID > 0: break

		if CMDID == 0:
			checkExpectResponse(devId)
			return {"cmd":CMDID}

		# received some response, reset check for response
		setNoExpectResponse(devId, calledfrom="cmdid={}".format(CMDID))
		restartConnectionCounter[devId] = 0
		firstCmdReceived = True

		if CMDID != 0:
			if lastCMDID == CMDID and time.time() - lastValidCmd < 0.1:
				if logLevel > 0: U.logger.log(20, "devID:{}; received CMDID: {:3d}= {:20}, Last:{:3d} secs sinceLast:{:.2f}, skipping cmdid < 0.1 secs appart".format(devId, CMDID,  commandList[devId].get(str(CMDID),""), lastCMDID, time.time() - lastValidCmd) )
			else:
				if logLevel > 0: U.logger.log(20, "devID:{}; received CMDID: {:3d}= {:20}, Last:{:3d}, secs sinceLast:{:.2f}".format(devId, CMDID, commandList[devId].get(str(CMDID),""), lastCMDID, time.time() - lastValidCmd) )
				# check for learning 
				if ignoreUntilEndOfLearning[devId] != -1: # already in learning mode
					if  CMDID in [203,207,208]:#   or not(CMDID > 199 and CMDID < 209)):	 # exit learning?
						U.logger.log(20, "devID:{}; exit learning mode CMDID:{}, last cmdid was :{}, set mute back to device".format(devId, CMDID, ignoreUntilEndOfLearning[devId] )  )
						U.sendURL({"sensors":{sensor:{devId:{"cmd":CMDID}}}}, wait=False)
						ignoreUntilEndOfLearning[devId] = -1
						setMute(devId, False, CMDID=CMDID)
				else:
					if CMDID > 199 and CMDID < 209: # in learning mode? if yes make shure mute is off
						U.logger.log(20, "devID:{}; enter learning mode CMDID:{}".format(devId, CMDID )  )
						ignoreUntilEndOfLearning[devId]  = CMDID
						U.sendURL({"sensors":{sensor:{devId:{"cmd":CMDID}}}}, wait=False)
						setMute(devId, True, CMDID=CMDID)
					else:
						setMute(devId, False)

		lastCMDID = CMDID
		
		if CMDID not in reactOnlyToCommands[devId]:
			return {"cmd":0}  

		if CMDID == 255 :
			time.sleep(2)
			lastkeepAwake[devId] = 0
			checkifRefreshSetup(devId, restart=badSensor[devId] > 0, upd=True)

		if CMDID == 800 :
			time.sleep(3.)
			doReset(devId)
			time.sleep(3.)
			lastkeepAwake[devId] = 0
			checkifRefreshSetup(devId, restart=True, upd=True)

		if CMDID == 802 and keepAwake[devId]: # 802 == exit wakeup
			lastkeepAwake[devId] = 0
			checkifRefreshSetup(devId, restart=True, upd=True)


		if CMDID in [1,2]:
			if i2cOrUart[devId] == "uart":
				if logLevel > 0: U.logger.log(20, "devID:{}; firstCmdReceived:{}, lastValCmd @: {:.1f}  dtlka= {:.1f}".format(devId, firstCmdReceived, time.time() - lastValidCmd, time.time() - lastkeepAwake[devId]) )
				if not firstCmdReceived or (time.time() - lastValidCmd > 5 and time.time() - lastkeepAwake[devId] > 5):
					lastkeepAwake[devId] = 0
					checkifRefreshSetup(devId, restart=True, upd=True)
			else:
				if not firstCmdReceived or (time.time() - lastValidCmd > 20 and time.time() - lastkeepAwake[devId] > 20):
					lastkeepAwake[devId] = 0
					checkifRefreshSetup(devId, restart=True, upd=True)

		if badSensor[devId] > 1:
			U.logger.log(20, "devID:{}; reset bad sensor count after {:} bad sensor readings".format(devId, badSensor[devId])  )

		if CMDID != 0:
			lastValidCmd = time.time()
			if anyCmdDefined: cmdQueue.put(CMDID)

		badSensor[devId] = 0
		return {"cmd":CMDID}

	except Exception as e:
		U.logger.log(20, "in Line {} has error={}".format(sys.exc_info()[-1].tb_lineno, e))

	badSensor[devId] += 1
	if badSensor[devId] >= 5: return "badSensor"
	return ""



############################################
def checkResetPower():
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
	global gpioCmdForAction, gpioNumberForCmdAction, gpioInverseAction, gpioOnTimeAction	
	global cmdQueue, threadCMD
	global logLevel, anyCmdDefined
	global GPIOZERO
	global resetGPIOClass, unixCmdAction, unixCmdVoiceNo

	try:
		time.sleep(1)
		if logLevel > 0: U.logger.log(20, "start  refresh GPIO loop")
		ledOn = [0,0,0,0,0,0,0,0]
		anyOn = False
		lastResetGPIO = {}
		for devId in sensors[sensor]: 
			lastResetGPIO[devId] = time.time()
			
		while threadCMD["state"] == "running":
			try:
				while not cmdQueue.empty():
					cmd = cmdQueue.get()
					if logLevel > 1: U.logger.log(20, "starting  command:{}, unixCmdAction:{}, unixCmdVoiceNo:{}".format(cmd,  unixCmdAction, unixCmdVoiceNo) )
					if cmd > 300: continue  # ignore status messages
					if anyCmdDefined:
						for ii in range(1,6):
							if gpioNumberForCmdAction[ii] == "": continue
							if gpioCmdForAction[ii] == "": continue
							##    any cmd								cmd >= 1 == wake key any comand			cmd >= 2 == wake + any real cmd					cmd > 2, any real command
							if gpioCmdForAction[ii]  == 0 or (gpioCmdForAction[ii]  == 1 and cmd > 0) or  (gpioCmdForAction[ii]  == 2 and cmd > 1) or  (gpioCmdForAction[ii]  == 3 and cmd > 2) or  gpioCmdForAction[ii] == cmd:
								ledOn[ii] = time.time()
								if logLevel > 0: U.logger.log(20, "setting  item({}) GPIO{} on due to receiving cmd:{} ontime:{}, inv:{} ".format(ii, gpioNumberForCmdAction[ii], gpioCmdForAction[ii], gpioOnTimeAction[ii], gpioInverseAction[ii] ) )
								if k_useGPIO:
									GPIO.output(gpioNumberForCmdAction[ii], gpioInverseAction[ii] != "0")
								else:
									getattr(GPIOZERO[gpioNumberForCmdAction[ii]], "on" if gpioInverseAction[ii] != "0" else "off")()
								anyOn = True
						for ii in range(1,6):
							if unixCmdAction[ii] == "": continue
							if unixCmdVoiceNo[ii] != cmd: continue
							##    any cmd								cmd >= 1 == wake key any comand			cmd >= 2 == wake + any real cmd					cmd > 2, any real command
							if logLevel > 1: U.logger.log(20, "starting  item({}) command:{} ".format(ii, unixCmdAction[ii] ) )
							subprocess.call(unixCmdAction[ii] , shell=True)

				if anyOn:
					anyOn = False
					for ii in range(1,6):
						if ledOn[ii] > 0:
							if time.time() - ledOn[ii]  > gpioOnTimeAction[ii]:
								ledOn[ii] = 0
								if logLevel > 1: U.logger.log(20, "setting  item({}) GPIO{} on/off to receiving cmd:{} ontime:{}, inv:{} ".format(ii, gpioNumberForCmdAction[ii], gpioCmdForAction[ii], gpioOnTimeAction[ii], gpioInverseAction[ii] ) )
								if k_useGPIO:
									GPIO.output(gpioNumberForCmdAction[ii], gpioInverseAction[ii] == "0")
								else:
									getattr(GPIOZERO[gpioNumberForCmdAction[ii]], "on" if gpioInverseAction[ii] == "0" else "off")()
							else:
								anyOn = True
				else:
					for devId in sensors[sensor]: 
						if time.time() - lastResetGPIO[devId] > resetGPIOClass[devId]:
							lastResetGPIO[devId] = time.time()
							setGPIOconfig(devIdSelect=devId, force=True)

			except Exception as e:
				U.logger.log(20, "in Line {} has error={}".format(sys.exc_info()[-1].tb_lineno, e))
				time.sleep(10)
				checkIfRestart(force=True)

			if anyOn: 	time.sleep(0.2)
			else: 		time.sleep(0.1)

	except Exception as e:
		U.logger.log(20, "in Line {} has error={}".format(sys.exc_info()[-1].tb_lineno, e))
	if logLevel > 0: U.logger.log(20, "ended  loop, state:{}".format(threadCMD["state"] ))


############################################
def cmdCheckSerialPort( devId, reboot=True):
	global gpioCmdForAction, gpioNumberForCmdAction, gpioInverseAction, gpioOnTimeAction, serialPortName
	global sensor, sensors
	try:
		for ii in range(30):
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
					U.logger.log(20, "serial port configured properly")

			break

		if not reboot:
			cmd = "/bin/ls -l /dev | /usr/bin/grep serial"
			ret = subprocess.Popen(cmd,shell=True,stdout=subprocess.PIPE,stderr=subprocess.PIPE).communicate()[0].decode('utf-8')
			found = ""
			for line in ret.split("\n"):
				pp = line.find("serial")
				if pp < 10: continue
				found += line[pp-1:]+"; "
				if line.find(serialPortName[devId]) > 10: 
					U.logger.log(20, "{}  ok: {}".format(serialPortName[devId], line ))
					return True
	
			msg = "bad_port:_/dev/"+serialPortName[devId]+";_existing:"+found.strip().strip(";")
			msg += ", rebooting now"
			U.logger.log(20, " {}".format(msg))
			U.sendURL({"sensors":{sensor:{devId:{"cmd":900}}}}, wait=False)
			time.sleep(10000)
			U.setRebootRequest("adding serial port")

	except Exception as e:
		U.logger.log(20, "in Line {} has error={}".format(sys.exc_info()[-1].tb_lineno, e))

	return False
		


############################################
def execSensorLoop():
	global sensor, sensors, badSensor
	global SENSOR, sensorMode
	global oldRaw, lastRead
	global startTime, lastMeasurement, lastRestart, restartRepeat, restartON
	global oldi2cOrUart, i2cOrUart, oldserialPortName, sensorOld, keepAwake, lastkeepAwake, tmpMuteOff, serialPortName
	global gpioCmdForAction, gpioNumberForCmdAction, gpioInverseAction, gpioOnTimeAction
	global refreshRepeat
	global currentMute
	global sleepAfterWrite, oldSleepAfterWrite, commandList, lastValidCmd
	global anyCmdDefined
	global cmdQueue, logLevel
	global threadCMD
	global firstCmdReceived
	global learningOn
	global lastReset, expectResponse, restartConnectionCounter, setWakeTime
	global GPIOZERO
	global reactOnlyToCommands, maxCommandId, minErrorCmdID,offCommand
	global gpioUsed 
	global resetGPIOClass
	global unixCmdVoiceNo, unixCmdAction
	global lastCMDID
	global ignoreUntilEndOfLearning
	
	
	ignoreUntilEndOfLearning		= {}
	lastCMDID						= -1
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
	logLevel						= 1
	cmdQueue						= queue.Queue()
	unixCmdVoiceNo					= ["","","","","","","","",""]
	unixCmdAction					= ["","","","","","","","",""]
	gpioCmdForAction				= ["","","","","","","","",""]
	gpioNumberForCmdAction			= ["","","","","","","","",""]
	gpioInverseAction				= ["","","","","","","","",""]
	gpioOnTimeAction				= ["","","","","","","","",""]
	anyCmdDefined					= False

	commandList						= {}
	lastValidCmd					= 0
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

	U.logger.log(20, "==== start {}".format(version))

	if U.getIPNumber() > 0:
		time.sleep(10)
		exit()

	readParams()

	time.sleep(1)

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
			sendData = False
			data = {}
			theValues = {}
			theValues["cmd"] = ""
			if sensor in sensors:
				data = {"sensors": {sensor:{}}}
				for devId in sensors[sensor]:
					if devId not in lastAliveSend:
						lastAliveSend[devId] = 0
					theValues = getValues(devId)

					if theValues == "":
						continue

					if theValues == "badSensor" or type(theValues) == type(" "):
						sensorWasBad = True
						if badSensor[devId] in [5,6]:
							extraSleep = 2
							sendData = True
							data["sensors"][sensor][devId] = {"cmd":910}
							break

						extraSleep = 2

					elif theValues["cmd"] != 0:
						data["sensors"][sensor][devId] = theValues
						sendData = True

					elif tt - sendToIndigoSecs > lastAliveSend[devId]:
						data["sensors"][sensor][devId] = {"cmd":700}
						sendData = True

			if sendData:
				U.sendURL(data, wait=False)
				#U.makeDATfile(G.program, data)
				extraSleep  += 0.01
				lastRead = time.time() + 4.
				lastAliveSend[devId] = time.time()

			U.echoLastAlive(G.program)

			if  tt - lastRead > 3.:
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
			slTime = max(0, sensorRefreshSecs + extraSleep  - (time.time()  - lastMeasurement) )
			time.sleep(slTime )
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


