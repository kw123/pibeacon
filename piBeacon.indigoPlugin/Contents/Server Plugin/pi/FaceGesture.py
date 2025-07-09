# -*- coding:utf-8 -*-
# /usr/bin/python3
"""
	@file DFRobot_RTU.py
	@brief Modbus RTU libary for Arduino. 
	
	@copyright   Copyright (c) 2025 DFRobot Co.Ltd (http://www.dfrobot.com)
	@licence     The MIT License (MIT)
	@author [Arya](xue.peng@dfrobot.com)
	@version  V1.0
	@date  2021-07-16
	@https://github.com/DFRobot/DFRobot_RTU
	
	adopted by Karl Wachs
"""
version			= 1.2

import sys
import serial
import time
from smbus2 import SMBus, i2c_msg

import logging
from ctypes import *
import os, json, datetime, subprocess, copy

sys.path.append("../")
sys.path.append(os.getcwd())
import	piBeaconUtils	as U
import	piBeaconGlobals as G

try:
	import queue as queue
except:
	import Queue as queue
import threading


G.program = "FaceGesture"

GLOB_USBownerFile					= G.homeDir+"temp/USB.owner"
GLOB_resetFile						= G.homeDir+"temp/FaceGesture.reset"
GLOB_restartFile					= G.homeDir+"temp/FaceGesture.restart"
GLOB_commandFile					= G.homeDir+"temp/FaceGesture.cmd"
GLOB_fileToReceiveCommands 			= G.homeDir+"temp/receiveCommands.input"
GLOB_recoverymessage 				= G.homeDir+"temp/FaceGesture.recovery"
GLOB_recoveryPrevious 				= G.homeDir+"temp/FaceGesture.previousRecovery"
GLOB_faceDetectionThreshold			= 80
GLOB_gestureDetectionThreshold		= 80
GLOB_detectionRange					= 100
GLOB_ignoreSameCommands				= -1
GLOB_cmdCodeForrelay				= 99

# Define device address and baud rate
GLOB_DEVICE_ID 						= 0x72
GLOB_RT_BAUD_RATE 					= 9600
GLOB_SERIAL_PORTNAME				= "serial0"




class DFRobot_RTU(object):
	
	_packet_header = {"id": 0, "cmd": 1, "cs": 0}
	
	"""Enum constant"""
	eRTU_EXCEPTION_ILLEGAL_FUNCTION     = 0x01
	eRTU_EXCEPTION_ILLEGAL_DATA_ADDRESS = 0x02
	eRTU_EXCEPTION_ILLEGAL_DATA_VALUE   = 0x03
	eRTU_EXCEPTION_SLAVE_FAILURE        = 0x04
	eRTU_EXCEPTION_CRC_ERROR            = 0x08
	eRTU_RECV_ERROR                     = 0x09
	eRTU_MEMORY_ERROR                   = 0x0A
	eRTU_ID_ERROR                       = 0x0B
	
	eCMD_READ_COILS           = 0x01
	eCMD_READ_DISCRETE        = 0x02
	eCMD_READ_HOLDING         = 0x03
	eCMD_READ_INPUT           = 0x04
	eCMD_WRITE_COILS          = 0x05
	eCMD_WRITE_HOLDING        = 0x06
	eCMD_WRITE_MULTI_COILS    = 0x0F
	eCMD_WRITE_MULTI_HOLDING  = 0x10

	def __init__(self, baud, bits, parity, stopbit, portName="serial0"):
		"""
			@brief Serial initialization.
			@param baud:  The UART baudrate of raspberry pi
			@param bits:  The UART data bits of raspberry pi
			@param parity:  The UART parity bits of raspberry pi
			@param stopbit:  The UART stopbit bits of raspberry pi.
			@param portName:  The UART dev port name
		"""
		self.portName = "/dev/"+portName
		#self._ser = serial.Serial("/dev/ttyAMA0",baud, bits, parity, stopbit)
		self._ser = serial.Serial(self.portName,baud, bits, parity, stopbit)
		self._timeout = 0.1 #0.1s
	
	def set_timout_time_s(self, timeout = 0.1):
		"""
			@brief Set receive timeout time, unit s.
			@param timeout:  receive timeout time, unit s, default 0.1s.
		"""
		self._timeout = timeout

	def read_coils_register(self, id, reg):
		"""
			@brief Read a coils Register.
			@param id:  modbus device ID. Range: 0x00 ~ 0xF7(0~247), 0x00 is broadcasr address, which all slaves will process broadcast packets, 
			@n          but will not answer.
			@param reg: Coils register address.
			@return Return the value of the coils register value.
			@n      True: The value of the coils register value is 1.
			@n      False: The value of the coils register value is 0.
		"""
		l = [(reg >> 8)&0xFF, (reg & 0xFF), 0x00, 0x01]
		val = False
		if (id < 1) or (id > 0xF7):
			U.logger.log(20,"device addr error.(1~247) %d"%id)
			return 0
		l = self._packed(id, self.eCMD_READ_COILS, l)
		self._send_package(l)
		l = self.recv_and_parse_package(id, self.eCMD_READ_COILS,1)
		if (l[0] == 0) and len(l) == 7:
			if (l[4] & 0x01) != 0:
					val = True
		return val
			
	def read_discrete_inputs_register(self, id, reg):
		"""
			@brief Read a discrete input register.
			@param id:  modbus device ID. Range: 0x00 ~ 0xF7(0~247), 0x00 is broadcasr address, which all slaves will process broadcast packets, 
			@n          but will not answer.
			@param reg: Discrete input register address.
			@return Return the value of the discrete input register value.
			@n      True: The value of the discrete input register value is 1.
			@n      False: The value of the discrete input register value is 0.
		"""
		l = [(reg >> 8)&0xFF, (reg & 0xFF), 0x00, 0x01]
		val = False
		if (id < 1) or (id > 0xF7):
			U.logger.log(20,"device addr error.(1~247) %d"%id)
			return 0
		l = self._packed(id, self.eCMD_READ_DISCRETE, l)
		self._send_package(l)
		l = self.recv_and_parse_package(id, self.eCMD_READ_DISCRETE,1)
		if (l[0] == 0) and len(l) == 7:
			if (l[4] & 0x01) != 0:
					val = True
		return val
			
	def read_holding_register(self, id, reg):
		"""
			@brief Read a holding Register.
			@param id:  modbus device ID. Range: 0x00 ~ 0xF7(0~247), 0x00 is broadcasr address, which all slaves will process broadcast packets, 
			@n          but will not answer.
			@param reg: Holding register address.
			@return Return the value of the holding register value.
		"""
		l = [(reg >> 8)&0xFF, (reg & 0xFF), 0x00, 0x01]
		if (id < 1) or (id > 0xF7):
			U.logger.log(20,"device addr error.(1~247) %d"%id)
			return 0
		l = self._packed(id, self.eCMD_READ_HOLDING, l)
		self._send_package(l)
		l = self.recv_and_parse_package(id, self.eCMD_READ_HOLDING,2)
		if (l[0] == 0) and len(l) == 8:
			l[0] = ((l[4] << 8) | l[5]) & 0xFFFF
		else:
			l[0] = 0
		return l[0]

	def read_input_register(self, id, reg):
		"""
			@brief Read a input Register.
			@param id:  modbus device ID. Range: 0x00 ~ 0xF7(0~247), 0x00 is broadcasr address, which all slaves will process broadcast packets, 
			@n          but will not answer.
			@param reg: Input register address.
			@return Return the value of the holding register value.
		"""
		l = [(reg >> 8)&0xFF, (reg & 0xFF), 0x00, 0x01]
		if (id < 1) or (id > 0xF7):
			U.logger.log(20,"device addr error.(1~247) %d"%id)
			return 0
		l = self._packed(id, self.eCMD_READ_INPUT, l)
		self._send_package(l)
		l = self.recv_and_parse_package(id, self.eCMD_READ_INPUT,2)
		if (l[0] == 0) and len(l) == 8:
			l[0] = ((l[4] << 8) | l[5]) & 0xFFFF
		else:
			l[0] = 0
		return l[0]
			
	def write_coils_register(self, id, reg, flag):
		"""
			@brief Write a coils Register.
			@param id:  modbus device ID. Range: 0x00 ~ 0xF7(0~247), 0x00 is broadcasr address, which all slaves will process broadcast packets, 
			@n          but will not answer.
			@param reg: Coils register address.
			@param flag: The value of the register value which will be write, 0 ro 1.
			@return Exception code:
			@n      0 : sucess.
			@n      1 or eRTU_EXCEPTION_ILLEGAL_FUNCTION : Illegal function.
			@n      2 or eRTU_EXCEPTION_ILLEGAL_DATA_ADDRESS: Illegal data address.
			@n      3 or eRTU_EXCEPTION_ILLEGAL_DATA_VALUE:  Illegal data value.
			@n      4 or eRTU_EXCEPTION_SLAVE_FAILURE:  Slave failure.
			@n      8 or eRTU_EXCEPTION_CRC_ERROR:  CRC check error.
			@n      9 or eRTU_RECV_ERROR:  Receive packet error.
			@n      10 or eRTU_MEMORY_ERROR: Memory error.
			@n      11 or eRTU_ID_ERROR: Broadcasr address or error ID
		"""
		val = 0x0000
		if flag:
			val = 0xFF00
		l = [(reg >> 8)&0xFF, (reg & 0xFF), (val >> 8)&0xFF, (val & 0xFF)]
		if id > 0xF7 :
			U.logger.log(20,"device addr error.")
			return 0
		l = self._packed(id, self.eCMD_WRITE_COILS, l)
		self._send_package(l)
		l = self.recv_and_parse_package(id, self.eCMD_WRITE_COILS,reg)
		return l[0]
			

	def write_holding_register(self, id, reg, val):
		"""
			@brief Write a holding register.
			@param id:  modbus device ID. Range: 0x00 ~ 0xF7(0~247), 0x00 is broadcasr address, which all slaves will process broadcast packets, 
			@n          but will not answer.
			@param reg: Holding register address.
			@param val: The value of the register value which will be write.
			@return Exception code:
			@n      0 : sucess.
			@n      1 or eRTU_EXCEPTION_ILLEGAL_FUNCTION : Illegal function.
			@n      2 or eRTU_EXCEPTION_ILLEGAL_DATA_ADDRESS: Illegal data address.
			@n      3 or eRTU_EXCEPTION_ILLEGAL_DATA_VALUE:  Illegal data value.
			@n      4 or eRTU_EXCEPTION_SLAVE_FAILURE:  Slave failure.
			@n      8 or eRTU_EXCEPTION_CRC_ERROR:  CRC check error.
			@n      9 or eRTU_RECV_ERROR:  Receive packet error.
			@n      10 or eRTU_MEMORY_ERROR: Memory error.
			@n      11 or eRTU_ID_ERROR: Broadcasr address or error ID
		"""
		l = [(reg >> 8)&0xFF, (reg & 0xFF), (val >> 8)&0xFF, (val & 0xFF)]
		if id > 0xF7 :
			U.logger.log(20,"device addr error.")
			return 0
		l = self._packed(id, self.eCMD_WRITE_HOLDING, l)
		self._send_package(l)
		l = self.recv_and_parse_package(id, self.eCMD_WRITE_HOLDING,reg)
		return l[0]
			
	def read_coils_registers(self, id, reg, reg_num):
		"""
			@brief Read multiple coils Register.
			@param id:  modbus device ID. Range: 0x00 ~ 0xF7(0~247), 0x00 is broadcasr address, which all slaves will process broadcast packets, 
			@n          but will not answer.
			@param reg: Read the start address of the coil register.
			@param reg_num: Number of coils Register.
			@return list: format as follow:
			@n      list[0]: Exception code:
			@n               0 : sucess.
			@n               1 or eRTU_EXCEPTION_ILLEGAL_FUNCTION : Illegal function.
			@n               2 or eRTU_EXCEPTION_ILLEGAL_DATA_ADDRESS: Illegal data address.
			@n               3 or eRTU_EXCEPTION_ILLEGAL_DATA_VALUE:  Illegal data value.
			@n               4 or eRTU_EXCEPTION_SLAVE_FAILURE:  Slave failure.
			@n               8 or eRTU_EXCEPTION_CRC_ERROR:  CRC check error.
			@n               9 or eRTU_RECV_ERROR:  Receive packet error.
			@n               10 or eRTU_MEMORY_ERROR: Memory error.
			@n               11 or eRTU_ID_ERROR: Broadcasr address or error ID
			@n      list[1:]: The value of the coil register list.
		"""
		length = reg_num // 8
		mod = reg_num % 8
		if mod:
			length += 1
		l = [(reg >> 8)&0xFF, (reg & 0xFF), (reg_num >> 8) & 0xFF, reg_num & 0xFF]
		if (id < 1) or (id > 0xF7):
			U.logger.log(20,"device addr error.(1~247) %d"%id)
			return [self.eRTU_ID_ERROR]
		l = self._packed(id, self.eCMD_READ_COILS, l)
		self._send_package(l)
		l = self.recv_and_parse_package(id, self.eCMD_READ_COILS,length)
		if l[0] == 0 and len(l) == (5+length+1):
			la = [l[0]] + l[4: len(l)-2]
			return la
		return [l[0]]
		
	def read_discrete_inputs_registers(self, id, reg, reg_num):
		"""
			@brief Read multiple discrete inputs register.
			@param id:  modbus device ID. Range: 0x00 ~ 0xF7(0~247), 0x00 is broadcasr address, which all slaves will process broadcast packets, 
			@n          but will not answer.
			@param reg: Read the start address of the discrete inputs register.
			@param reg_num: Number of coils Register.
			@return list: format as follow:
			@n      list[0]: Exception code:
			@n               0 : sucess.
			@n               1 or eRTU_EXCEPTION_ILLEGAL_FUNCTION : Illegal function.
			@n               2 or eRTU_EXCEPTION_ILLEGAL_DATA_ADDRESS: Illegal data address.
			@n               3 or eRTU_EXCEPTION_ILLEGAL_DATA_VALUE:  Illegal data value.
			@n               4 or eRTU_EXCEPTION_SLAVE_FAILURE:  Slave failure.
			@n               8 or eRTU_EXCEPTION_CRC_ERROR:  CRC check error.
			@n               9 or eRTU_RECV_ERROR:  Receive packet error.
			@n               10 or eRTU_MEMORY_ERROR: Memory error.
			@n               11 or eRTU_ID_ERROR: Broadcasr address or error ID
			@n      list[1:]: The value list of the discrete inputs register.
		"""
		length = reg_num // 8
		mod = reg_num % 8
		if mod:
			length += 1
		l = [(reg >> 8)&0xFF, (reg & 0xFF), (reg_num >> 8) & 0xFF, reg_num & 0xFF]
		if (id < 1) or (id > 0xF7):
			U.logger.log(20,"device addr error.(1~247) %d"%id)
			return [self.eRTU_ID_ERROR]
		l = self._packed(id, self.eCMD_READ_DISCRETE, l)
		self._send_package(l)
		l = self.recv_and_parse_package(id, self.eCMD_READ_DISCRETE,length)
		if l[0] == 0 and len(l) == (5+length+1):
			la = [l[0]] + l[4: len(l)-2]
			return la
		return [l[0]]
		
	def read_holding_registers(self, id, reg, size):
		"""
			@brief Read multiple holding register.
			@param id:  modbus device ID. Range: 0x00 ~ 0xF7(0~247), 0x00 is broadcasr address, which all slaves will process broadcast packets, 
			@n          but will not answer.
			@param reg: Read the start address of the holding register.
			@param size: Number of read holding register.
			@return list: format as follow:
			@n      list[0]: Exception code:
			@n               0 : sucess.
			@n               1 or eRTU_EXCEPTION_ILLEGAL_FUNCTION : Illegal function.
			@n               2 or eRTU_EXCEPTION_ILLEGAL_DATA_ADDRESS: Illegal data address.
			@n               3 or eRTU_EXCEPTION_ILLEGAL_DATA_VALUE:  Illegal data value.
			@n               4 or eRTU_EXCEPTION_SLAVE_FAILURE:  Slave failure.
			@n               8 or eRTU_EXCEPTION_CRC_ERROR:  CRC check error.
			@n               9 or eRTU_RECV_ERROR:  Receive packet error.
			@n               10 or eRTU_MEMORY_ERROR: Memory error.
			@n               11 or eRTU_ID_ERROR: Broadcasr address or error ID
			@n      list[1:]: The value list of the holding register.
		"""
		l = [(reg >> 8)&0xFF, (reg & 0xFF), (size >> 8) & 0xFF, size & 0xFF]
		if (id < 1) or (id > 0xF7):
			U.logger.log(20,"device addr error.(1~247) %d"%id)
			return [self.eRTU_ID_ERROR]
		l = self._packed(id, self.eCMD_READ_HOLDING, l)
		self._send_package(l)
		l = self.recv_and_parse_package(id, self.eCMD_READ_HOLDING,size*2)
		#lin = ['%02X' % i for i in l]
		#U.logger.log(20," ".join(lin))
		if (l[0] == 0) and (len(l) == (5+size*2+1)):
			la = [l[0]] + l[4: len(l)-2]
			return la
		return [l[0]]

	def read_input_registers(self, id, reg, size):
		"""
			@brief Read multiple input register.
			@param id:  modbus device ID. Range: 0x00 ~ 0xF7(0~247), 0x00 is broadcasr address, which all slaves will process broadcast packets, 
			@n          but will not answer.
			@param reg: Read the start address of the input register.
			@param size: Number of read input register.
			@return list: format as follow:
			@n      list[0]: Exception code:
			@n               0 : sucess.
			@n               1 or eRTU_EXCEPTION_ILLEGAL_FUNCTION : Illegal function.
			@n               2 or eRTU_EXCEPTION_ILLEGAL_DATA_ADDRESS: Illegal data address.
			@n               3 or eRTU_EXCEPTION_ILLEGAL_DATA_VALUE:  Illegal data value.
			@n               4 or eRTU_EXCEPTION_SLAVE_FAILURE:  Slave failure.
			@n               8 or eRTU_EXCEPTION_CRC_ERROR:  CRC check error.
			@n               9 or eRTU_RECV_ERROR:  Receive packet error.
			@n               10 or eRTU_MEMORY_ERROR: Memory error.
			@n               11 or eRTU_ID_ERROR: Broadcasr address or error ID
			@n      list[1:]: The value list of the input register.
		"""
		l = [(reg >> 8)&0xFF, (reg & 0xFF), (size >> 8) & 0xFF, size & 0xFF]
		if (id < 1) or (id > 0xF7):
			U.logger.log(20,"device addr error.(1~247) %d"%id)
			return [self.eRTU_ID_ERROR]
		l = self._packed(id, self.eCMD_READ_INPUT, l)
		self._send_package(l)
		l = self.recv_and_parse_package(id, self.eCMD_READ_INPUT,size*2)
		#lin = ['%02X' % i for i in l]
		#U.logger.log(20," ".join(lin))
		if (l[0] == 0) and (len(l) == (5+size*2+1)):
			la = [l[0]] + l[4: len(l)-2]
			return la
		return [l[0]]
		
	def write_coils_registers(self, id, reg, reg_num, data):
		"""
			@brief Write multiple coils Register.
			@param id:  modbus device ID. Range: 0x00 ~ 0xF7(0~247), 0x00 is broadcasr address, which all slaves will process broadcast packets, 
			@n          but will not answer.
			@param reg: Write the start address of the coils register.
			@param reg_num: Number of coils Register.
			@param data: The list of storage coils Registers' value which will be write.
			@return Exception code:
			@n      0 : sucess.
			@n      1 or eRTU_EXCEPTION_ILLEGAL_FUNCTION : Illegal function.
			@n      2 or eRTU_EXCEPTION_ILLEGAL_DATA_ADDRESS: Illegal data address.
			@n      3 or eRTU_EXCEPTION_ILLEGAL_DATA_VALUE:  Illegal data value.
			@n      4 or eRTU_EXCEPTION_SLAVE_FAILURE:  Slave failure.
			@n      8 or eRTU_EXCEPTION_CRC_ERROR:  CRC check error.
			@n      9 or eRTU_RECV_ERROR:  Receive packet error.
			@n      10 or eRTU_MEMORY_ERROR: Memory error.
			@n      11 or eRTU_ID_ERROR: Broadcasr address or error ID
		"""
		length = reg_num // 8
		mod = reg_num % 8
		if mod:
			length += 1
		if len(data) < length:
			return [self.eRTU_EXCEPTION_ILLEGAL_DATA_VALUE]
		l = [(reg >> 8)&0xFF, (reg & 0xFF), ((reg_num >> 8) & 0xFF), (reg_num & 0xFF), length] + data
		if id > 0xF7:
			U.logger.log(20,"device addr error.")
			return 0
		l = self._packed(id, self.eCMD_WRITE_MULTI_COILS, l)
		self._send_package(l)
		l = self.recv_and_parse_package(id, self.eCMD_WRITE_MULTI_COILS,reg)
		if (l[0] == 0) and len(l) == 9:
			val = ((l[5] << 8) | l[6]) & 0xFFFF
		return l[0]
			
	def write_holding_registers(self, id, reg, data):
		"""
			@brief Write multiple holding Register.
			@param id:  modbus device ID. Range: 0x00 ~ 0xF7(0~247), 0x00 is broadcasr address, which all slaves will process broadcast packets, 
			@n          but will not answer.
			@param reg: Write the start address of the holding register.
			@param data: The list of storage holding Registers' value which will be write.
			@return Exception code:
			@n      0 : sucess.
			@n      1 or eRTU_EXCEPTION_ILLEGAL_FUNCTION : Illegal function.
			@n      2 or eRTU_EXCEPTION_ILLEGAL_DATA_ADDRESS: Illegal data address.
			@n      3 or eRTU_EXCEPTION_ILLEGAL_DATA_VALUE:  Illegal data value.
			@n      4 or eRTU_EXCEPTION_SLAVE_FAILURE:  Slave failure.
			@n      8 or eRTU_EXCEPTION_CRC_ERROR:  CRC check error.
			@n      9 or eRTU_RECV_ERROR:  Receive packet error.
			@n      10 or eRTU_MEMORY_ERROR: Memory error.
			@n      11 or eRTU_ID_ERROR: Broadcasr address or error ID
		"""
		size = len(data) >> 1
		l = [(reg >> 8)&0xFF, (reg & 0xFF), ((size >> 8) & 0xFF), (size & 0xFF), size*2] + data
		if id > 0xF7:
			U.logger.log(20,"device addr error.")
			return 0
		l = self._packed(id, self.eCMD_WRITE_MULTI_HOLDING, l)
		self._send_package(l)
		l = self.recv_and_parse_package(id, self.eCMD_WRITE_MULTI_HOLDING,reg)
		if (l[0] == 0) and len(l) == 9:
			val = ((l[5] << 8) | l[6]) & 0xFFFF
		return l[0]
			
	def _calculate_crc(self, data):
		crc = 0xFFFF
		length = len(data)
		#U.logger.log(20,"len=%d"%length)
		pos = 0
		while pos < length:
			crc ^= (data[pos] | 0x0000)
			#U.logger.log(20,"pos=%d, %02x"%(pos,data[pos]))
			i = 8
			while i != 0:
				if (crc & 0x0001) != 0:
					crc = (crc >> 1)&0xFFFF
					crc ^= 0xA001
				else:
					crc = (crc >> 1)&0xFFFF
				i -= 1
			pos += 1
		crc = (((crc & 0x00FF) << 8) | ((crc & 0xFF00) >> 8)) & 0xFFFF
		#U.logger.log(20,"crc=%x"%crc)
		return crc

	def _clear_recv_buffer(self):
		remain = self._ser.inWaiting()
		while remain:
			self._ser.read(remain)
			remain = self._ser.inWaiting()

	def _packed(self, id, cmd, l):
		length = 4+len(l)
		#U.logger.log(20,len(l))
		package = [0]*length
		package[0] = id
		package[1] = cmd
		package[2:length-2] = l
		#lin = ['%02X' % i for i in package]
		#U.logger.log(20," ".join(lin))

		crc = self._calculate_crc(package[:len(package)-2])
		package[length-2] = (crc >> 8) & 0xFF
		package[length-1] = crc & 0xFF
		
		#lin = ['%02X' % i for i in package]
		#U.logger.log(20," ".join(lin))
		return package

	def _send_package(self, l):
		self._clear_recv_buffer()
		if len(l):
			self._ser.write(l)
			time.sleep(self._timeout)

	def recv_and_parse_package(self, id, cmd, val):
		package = [self.eRTU_ID_ERROR]
		if id == 0:
			return [0]
		if (id < 1) or (id > 0xF7):
			return package
		head = [0]*4
		index = 0
		t = time.time()
		remain = 0
		while remain < 5:
			if self._ser.inWaiting():
				data = self._ser.read(1)
				try: 
					head[index] = ord(data)
				except:
					head[index] = data
				#U.logger.log(20,"%d = %02X"%(index, head[index]))
				index += 1
				if (index == 1) and (head[0] != id):
					index = 0
				elif (index == 2) and ((head[1] & 0x7F) != cmd):
					index = 0
				remain = index
				t = time.time()
			if time.time() - t > self._timeout:
				#U.logger.log(20,"time out.")
				return [self.eRTU_RECV_ERROR]
			if index == 4:
				if head[1] & 0x80:
					index = 5
				else:
					if head[1] < 5:
						if head[2] != (val & 0xFF):
							index = 0
							remain = 0
						else:
							index = 5 + head[2]
					else:
						if (((head[2] << 8) | head[3]) & 0xFFFF) != val:
							index = 0
							remain = 0
							#U.logger.log(20,"index = 0")
						else:
							index = 8
							#U.logger.log(20,"index = 8")
				if index > 0:
					package = [0]*(index + 1)
					package[1:5] = head
					remain = index - 4
					index = 5
					t = time.time()
					while remain > 0:
						if self._ser.inWaiting():
							data = self._ser.read(1)
							try: 
								package[index] = ord(data)
							except:
								package[index] = data
							index += 1
							remain -= 1
							t = time.time()
						if time.time() - t >self._timeout:
							U.logger.log(20,"time out1.")
							return [self.eRTU_RECV_ERROR]
					crc = ((package[len(package) - 2] << 8) | package[len(package) - 1]) & 0xFFFF
					if crc != self._calculate_crc(package[1:len(package) - 2]):
						U.logger.log(20,"CRC ERROR")
						return [self.eRTU_RECV_ERROR]
					if package[2] & 0x80:
						package[0] = package[3]
					else:
						package[0] = 0
					#lin = ['%02X' % i for i in package]
					#U.logger.log(20," ".join(lin))
					return package
		return [0]

# -*- coding: utf-8 -*-
"""
  @file DFRobot_GestureFaceDetection.py
  @brief Define the basic structure and methods of the DFRobot_GestureFaceDetection class.
  @copyright   Copyright (c) 2025 DFRobot Co.Ltd (http://www.dfrobot.com)
  @license     The MIT license (MIT)
  @author [thdyyl](yuanlong.yu@dfrobot.com)
  @version  V1.0
  @date  2025-03-17
  @https://github.com/DFRobot/DFRobot_GestureFaceDetection
"""


class DFRobot_GestureFaceDetection(object):
	# Define register address constants
	REG_GFD_ADDR = 0x0000                       #< Device address register
	REG_GFD_BAUDRATE = 0x0001                   #< Baud rate configuration register
	REG_GFD_VERIFY_AND_STOP = 0x0002            #< Parity and stop bits configuration register
	REG_GFD_FACE_THRESHOLD = 0x0003             #< Face detection threshold, X coordinate
	REG_GFD_FACE_SCORE_THRESHOLD = 0x0004       #< Face score threshold
	REG_GFD_GESTURE_SCORE_THRESHOLD = 0x0005    #< Gesture score threshold

	GFD_PID = 0x0272                            #< Product ID
	# Error codes for UART configuration
	ERR_INVALID_BAUD = 0x0001           #< Invalid baud rate
	ERR_INVALID_PARITY = 0x0002         #< Invalid parity setting
	ERR_INVALID_STOPBIT = 0x0004        #< Invalid stop bit
	ERR_CONFIG_BUAD = 0x0010            #< Baud rate configuration failed.
	ERR_CONFIG_PARITY_STOPBIT = 0x0020  #< Failed to configure checksum and stop bit.
	SUCCESS = 0x0000                    #< Operation succeeded

	REG_GFD_PID = 0x0000                        #< Product ID register
	REG_GFD_VID = 0x0001                        #< Vendor ID register
	REG_GFD_HW_VERSION = 0x0002                 #< Hardware version register
	REG_GFD_SW_VERSION = 0x0003                 #< Software version register
	REG_GFD_FACE_NUMBER = 0x0004                #< Number of detected faces
	REG_GFD_FACE_LOCATION_X = 0x0005            #< Face X coordinate
	REG_GFD_FACE_LOCATION_Y = 0x0006            #< Face Y coordinate
	REG_GFD_FACE_SCORE = 0x0007                 #< Face score
	REG_GFD_GESTURE_TYPE = 0x0008               #< Gesture type
	REG_GFD_GESTURE_SCORE = 0x0009              #< Gesture score

	INPUT_REG_OFFSET = 0x06                     #< Input register offset


	EBAUD_1200 = 1         #< Baud rate 1200
	EBAUD_2400 = 2         #< Baud rate 2400
	EBAUD_4800 = 3         #< Baud rate 4800
	EBAUD_9600 = 4         #< Baud rate 9600
	EBAUD_14400 = 5        #< Baud rate 14400
	EBAUD_19200 = 6        #< Baud rate 19200
	EBAUD_38400 = 7        #< Baud rate 38400
	EBAUD_57600 = 8        #< Baud rate 57600
	EBAUD_115200 = 9       #< Baud rate 115200
	EBAUD_230400 = 10      #< Baud rate 230400
	EBAUD_460800 = 11      #< Baud rate 460800
	EBAUD_921600 = 12      #< Baud rate 921600

	UART_CFG_PARITY_NONE = 0      #< No parity
	UART_CFG_PARITY_ODD = 1       #< Odd parity
	UART_CFG_PARITY_EVEN = 2      #< Even parity
	UART_CFG_PARITY_MARK = 3      #< Mark parity
	UART_CFG_PARITY_SPACE = 4     #< Space parity

	UART_CFG_STOP_BITS_0_5 = 0    #< 0.5 stop bits
	UART_CFG_STOP_BITS_1 = 1      #< 1 stop bit
	UART_CFG_STOP_BITS_1_5 = 2    #< 1.5 stop bits
	UART_CFG_STOP_BITS_2 = 3      #< 2 stop bits

	I2C_RETRY_MAX = 3
	def __init__(self):
			# Initialize the class
			pass


	def begin(self):
		"""
			@brief Init function
			@return True if initialization is successful, otherwise false.
		"""
		if self.readInputReg(self.REG_GFD_PID) == self.GFD_PID:
			return True
		return False


	def read_pid(self):
		"""
			@brief Get the device PID
			@return Return the device PID 
		"""
		return self.readInputReg(self.REG_GFD_PID)


	def read_vid(self):
		"""
			@brief Get the device VID
			@return Return the device VID
		"""
		return self.readInputReg(self.REG_GFD_VID)


	def config_uart(self, baud, parity, stop_bit):
		"""
			@brief Configure UART
			@n !!!However, the current CSK6 chip's serial port only supports changing the baud rate, and the stop and check bits should be set to default.
			@param baud Baud rate  EBAUD_1200 ~ EBAUD_921600
			@param parity Parity bit UART_CFG_PARITY_NONE ~ UART_CFG_PARITY_SPACE 
			@param stop_bit Stop bits UART_CFG_STOP_BITS_0_5 ~ UART_CFG_STOP_BITS_2
			@return Return 0 if configuration is successful, otherwise return error code.
		"""
		if (baud < self.EBAUD_1200) or (baud > self.EBAUD_921600):
				return self.ERR_INVALID_BAUD
		if (parity < self.UART_CFG_PARITY_NONE) or (parity > self.UART_CFG_PARITY_SPACE):
				return self.ERR_INVALID_PARITY
		if (stop_bit < self.UART_CFG_STOP_BITS_0_5) or (stop_bit > self.UART_CFG_STOP_BITS_2):
				return self.ERR_INVALID_STOPBIT
		# Set baud rate
		if not self.writeHoldingReg(self.REG_GFD_BAUDRATE, baud):
				return self.ERR_CONFIG_BUAD
		# Set parity and stop bits
		verify_and_stop = (parity << 8) | (stop_bit & 0xff)
		if not self.writeHoldingReg(self.REG_GFD_VERIFY_AND_STOP, verify_and_stop):
				return self.ERR_CONFIG_PARITY_STOPBIT
		return self.SUCCESS
	

	def get_face_number(self):
		"""
			@brief Get the number of detected faces
			@return Return the number of detected faces
		"""
		return self.readInputReg(self.REG_GFD_FACE_NUMBER)


	def get_face_location_x(self):
		"""
			@brief Get the X location of the face
			@return Return the X location
		"""
		return self.readInputReg(self.REG_GFD_FACE_LOCATION_X)


	def get_face_location_y(self):
		"""
			@brief Get the Y location of the face
			@return Return the Y location
		"""
		return self.readInputReg(self.REG_GFD_FACE_LOCATION_Y)


	def get_face_score(self):
		"""
			@brief Get the face score
			@return Return the face score
		"""
		return self.readInputReg(self.REG_GFD_FACE_SCORE)


	def get_gesture_type(self):
		"""
			@brief Get the gesture type
					- 1: LIKE (👍) - blue
					- 2: OK (👌) - green
					- 3: STOP (🤚) - red
					- 4: YES (✌) - yellow
					- 5: SIX (🤙) - purple
			@return Return the gesture type
		"""
		return self.readInputReg(self.REG_GFD_GESTURE_TYPE)


	def get_gesture_score(self):
		"""
			@brief Get the gesture score
			@return Return the gesture score
		"""
		return self.readInputReg(self.REG_GFD_GESTURE_SCORE)


	def set_face_detect_thres(self, score):
		"""
			@brief Set the face detection threshold
			@n Sets the threshold for face detection (0-100). Default is 60%
			@param score Threshold score
		"""
		if (0 >= score) or (score > 100):
				return False
		return self.writeHoldingReg(self.REG_GFD_FACE_SCORE_THRESHOLD, score)


	def get_face_detect_thres(self):
		"""
			@brief Get the face detection threshold
			@n Get the threshold for face detection (0-100). Default is 60%
			@return Return the face detection threshold
		"""
		return self.readHoldingReg(self.REG_GFD_FACE_SCORE_THRESHOLD)


	def set_detect_thres(self, x):
		"""
			@brief Set the x-range for face detection
			@n Sets the threshold for detecting the X coordinate (0-100). Default is 60%.
			@param x Threshold value
		"""
		if (0 >= x) or (x > 100):
				return False
		return self.writeHoldingReg(self.REG_GFD_FACE_THRESHOLD, x)


	def get_detect_thres(self):
		"""
			@brief Get the x-range for face detection
			@n Get the threshold for detecting the X coordinate (0-100). Default is 60%.
			@return Return the x-range for face detection
		"""
		return self.readHoldingReg(self.REG_GFD_FACE_THRESHOLD)


	def set_gesture_detect_thres(self, score):
		"""
			@brief Set the gesture detection threshold
			@n Sets the threshold for gesture detection (0-100). Default is 60%.
			@param score Threshold score
		"""
		if (0 >= score) or (score > 100):
				return False
		return self.writeHoldingReg(self.REG_GFD_GESTURE_SCORE_THRESHOLD, score)


	def get_gesture_detect_thres(self):
		"""
			@brief Get the gesture detection threshold
			@n Get the threshold for gesture detection (0-100). Default is 60%.
			@return Return the threshold for gesture detection
		"""
		return self.readHoldingReg(self.REG_GFD_GESTURE_SCORE_THRESHOLD)


	def set_addr(self, addr):
		"""
			@brief Set the device address
			@param addr Address to set
		"""
		if (addr < 1) or (addr > 0xF7):
				return False
		return self.writeHoldingReg(self.REG_GFD_ADDR, addr)

class DFRobot_GestureFaceDetection_I2C(DFRobot_GestureFaceDetection): 
	def __init__(self, bus, addr):
		# Initialize I2C address and bus
		self.__addr = addr
		self.__i2cbus = bus
		super(DFRobot_GestureFaceDetection_I2C, self).__init__()

	def calculate_crc(self, data):
		crc = 0xFF
		for byte in data:
			crc ^= byte
			for _ in range(8):
				if crc & 0x80:
					crc = (crc << 1) ^ 0x07
				else:
					crc <<= 1
			crc &= 0xFF
		return crc


	def write_reg(self, reg, data):
		"""
			@fn write_reg
			@brief Write data to a register
			@param reg 16-bit register address
			@param data 8-bit register value
		"""
		# Split data into high and low 8 bits and write to I2C register
		val_high_byte = (data >> 8) & 0xFF 
		val_low_byte = data & 0xFF    
		reg_high_byte = (reg >> 8) & 0xFF
		reg_low_byte = reg & 0xFF
		crc = self.calculate_crc([reg_high_byte, reg_low_byte, val_high_byte, val_low_byte])
		for i in range(self.I2C_RETRY_MAX):
			with SMBus(self.__i2cbus) as bus:
				msg = i2c_msg.write(self.__addr, [reg_high_byte, reg_low_byte, val_high_byte, val_low_byte, crc])
				bus.i2c_rdwr(msg)
				time.sleep(0.05) # Because the slave has a clock extension, it needs to wait.
				msg = i2c_msg.read(self.__addr, 3)
				bus.i2c_rdwr(msg)
				data = list(msg)
				ret_data = (data[0] << 8) | data[1]
				if self.calculate_crc(data[:2]) == data[2] and ret_data == crc:
						return True
		return False

	def read_reg(self, reg, length):
		"""
			@fn read_reg
			@brief Read data from a register
			@param reg 16-bit register address
			@param length Length of data to read
			@return Data read from the register
		"""
		reg_high_byte = (reg >> 8) & 0xFF 
		reg_low_byte = reg & 0xFF         
		crc = self.calculate_crc([reg_high_byte, reg_low_byte])
		for i in range(self.I2C_RETRY_MAX):
				with SMBus(self.__i2cbus) as bus:
					msg = i2c_msg.write(self.__addr, [reg_high_byte, reg_low_byte, crc])
					bus.i2c_rdwr(msg)
					time.sleep(0.02)
					msg = i2c_msg.read(self.__addr, 3)
					bus.i2c_rdwr(msg)
					data = list(msg)
					ret_data = (data[0] << 8) | data[1]
					if self.calculate_crc(data[:length]) == data[length] and ret_data != 0xFFFF:
						return ret_data
		return 0

	def writeHoldingReg(self, reg, data):
		return self.write_reg(reg, data)

	def readInputReg(self, reg):
		return self.read_reg(self.INPUT_REG_OFFSET + reg, 2)

	def readHoldingReg(self, reg):
		return self.read_reg(reg, 2)


###############################
class DFRobot_GestureFaceDetection_UART(DFRobot_GestureFaceDetection, DFRobot_RTU): 
	def __init__(self, baud, addr, portName="serial0"):
		# Initialize UART baud rate and address
		self.__baud = baud
		self.__addr = addr
		DFRobot_GestureFaceDetection.__init__(self)
		DFRobot_RTU.__init__(self, baud, 8, 'N', 1, portName=portName)

	def writeHoldingReg(self, reg, data):
		ret = self.write_holding_register(self.__addr, reg, data)
		return ret == 0

	def readInputReg(self, reg):
		try:
			data = self.read_input_registers(self.__addr, reg, 1)
			
			# Ensure data list has at least three elements
			if len(data) >= 3:
				regData = (data[1] << 8) | data[2]
			else:
				regData = 0
			
			return regData

		except Exception as e:
			return 0

	def readHoldingReg(self, reg):
		try:
			data = self.read_holding_registers(self.__addr, reg, 1)
			
			# Ensure data list has at least three elements
			if len(data) >= 3:
				regData = (data[1] << 8) | data[2]
			else:
				regData = 0
			
			return regData
		except Exception as e:
			return 0

###############################
def	makeUsbItemList():
	"""
		@brief this method will f read /dev/ for USB and serial ports and fill dict serialItems
	"""

	global serialItems
	serialItems = []
	cmd = "/bin/ls -l /dev | /usr/bin/grep ttyUSB"
	ret = subprocess.Popen(cmd,shell=True,stdout=subprocess.PIPE,stderr=subprocess.PIPE).communicate()[0].decode('utf-8')
	cmd = "/bin/ls -l /dev | /usr/bin/grep serial0"
	ret2 = subprocess.Popen(cmd,shell=True,stdout=subprocess.PIPE,stderr=subprocess.PIPE).communicate()[0].decode('utf-8')
	for line in (ret+ret2).split("\n"):
		pp = line.find("ttyUSB")
		if pp > 10:
			serialItems.append(line[pp-1:].strip().split(" ")[0])

# ===========================================================================
# read params
# ===========================================================================

###############################
def readParams():
	"""
		@brief this method read parameters fiel and fill dicts used in the program
	"""

	global sensors, logDir, sensor,	 displayEnable
	global SENSOR, sensorOld
	global oldRaw, lastRead
	global startTime, lastMeasurement, oldi2cOrUart, oldserialPortName

	global i2cOrUart, serialPortName
	global gpioCmdForAction, gpioNumberForCmdAction, gpioInverseAction, gpioOnTimeAction, anyCmdDefined, unixCmdAction, unixCmdVoiceNo
	global badSensor
	global logLevel
	global reactOnlyToCommands
	global gpioUsed, failedCount
	global lastCommandReceived, lastValidCmdAt, ignoreSameCommands
	global faceDetectionThreshold, gestureDetectionThreshold, detectionRange
	global restartSensor


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


		U.getGlobalParams(inp)

		if "sensors"	in inp:	 sensors =		(inp["sensors"])



		if sensor not in sensors:
			U.logger.log(20, "{} is not in parameters = not enabled, stopping {}.py".format(G.program,G.program) )
			exit()

		initUSBownerFile(firstRead)

		makeUsbItemList()
		
		for devId in sensors[sensor]:
			restart = ""
			U.logger.log(20, "checking: {} old?:{}, restart:{}".format(devId, devId in sensorOld, devId in restartSensor) )
			clearUSBownerFile(devId, firstRead)

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

			if logLevel > 0: U.logger.log(10,"{} reading new parameters for devId:{}".format(G.program, devId) )

			if devId not in badSensor: 					badSensor[devId] 					= 0
			if devId not in serialPortName: 			serialPortName[devId] 				= ""
			if devId not in reactOnlyToCommands: 		reactOnlyToCommands[devId] 			= [x for x in range(6)]
			if devId not in lastCommandReceived:		lastCommandReceived[devId]			= ""
			if devId not in lastValidCmdAt:				lastValidCmdAt[devId]				= 0
			if devId not in ignoreSameCommands:			ignoreSameCommands[devId]			= GLOB_ignoreSameCommands
			if devId not in faceDetectionThreshold:		faceDetectionThreshold[devId]		= GLOB_faceDetectionThreshold
			if devId not in gestureDetectionThreshold:	gestureDetectionThreshold[devId]	= GLOB_gestureDetectionThreshold
			if devId not in detectionRange:				detectionRange[devId]				= GLOB_detectionRange
			if devId not in failedCount:				failedCount[devId]					= 0
			 
			for ii in range(1,9):
				unixCmdAction[ii] =  sensors[sensor][devId].get("unixCmdAction"+str(ii),"")
				try: 	unixCmdVoiceNo[ii] = int(sensors[sensor][devId].get("unixCmdVoiceNo"+str(ii),"-1"))
				except: unixCmdVoiceNo[ii] = -1
				if unixCmdAction[ii] != "": anyCmdDefined = True

			U.logger.log(20, "devId:{}, unixCmdNo:{}; unixCmdAction:{} ".format(devId, unixCmdVoiceNo, unixCmdAction) )
			
			reactCmds = []
			errCmds = []

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
				if str(logLevel) != sensors[sensor][devId].get("logLevel","0"): restart += "loglevel,"
				logLevel = int(sensors[sensor][devId].get("logLevel","1"))
			else:
				logLevel = 0

			restart += getAndCheckParam(devId, "ignoreSameCommands", 		ignoreSameCommands,		 	GLOB_ignoreSameCommands,		"float")
			restart += getAndCheckParam(devId, "faceDetectionThreshold", 	faceDetectionThreshold,		GLOB_faceDetectionThreshold,	"int")
			restart += getAndCheckParam(devId, "gestureDetectionThreshold",	gestureDetectionThreshold,	GLOB_gestureDetectionThreshold,	"int")
			restart += getAndCheckParam(devId, "detectionRange", 			detectionRange, 			GLOB_detectionRange, 			"int")
			
			i2cOrUart[devId] =  sensors[sensor][devId].get("i2cOrUart","")	
			
			if i2cOrUart[devId] == "i2c":
				if devId not in oldi2cOrUart or (i2cOrUart[devId] != "" and oldi2cOrUart[devId] != i2cOrUart[devId]):	restart = "i2c new,"
				oldi2cOrUart[devId]  = copy.copy(i2cOrUart[devId])


			elif i2cOrUart[devId] == "uart":
				serialPortName[devId] =  sensors[sensor][devId].get("serialPortName", GLOB_SERIAL_PORTNAME)	
				if devId not in oldserialPortName or (serialPortName[devId] != "" and oldserialPortName[devId]  != serialPortName[devId]) :
					restart += "portname changed,"
				oldserialPortName[devId]  = copy.copy(serialPortName[devId])
				time.sleep(1)

			prepGPIOInfoForCommands(devId, inp.get("output",{}))
			if devId not in SENSOR or restart or devId in restartSensor:
				failedCount[devId] = 0
				if not startSensor(devId) or devId not in SENSOR:
					U.logger.log(20,"devId:{}; start failed".format(devId) )
					if devId in SENSOR: SENSOR[devId] = ""
					continue
				restart += "devId not in SENSOR,"

			if devId not in sensorOld: 
				restart += "devId not in old config,"

			if restart != "" and logLevel > 0: U.logger.log(20, "devId:{}; reason:{}, serialPortName:{}, logLevel:{}, detectionRange:{}, gestureDetectionThreshold:{}, faceDetectionThreshold:{}, ignoreSameCommands:{}".format(devId, restart, serialPortName[devId], logLevel, detectionRange[devId], gestureDetectionThreshold[devId], faceDetectionThreshold[devId], ignoreSameCommands[devId] ) )

			U.logger.log(20, "devId:{}; end of sensor start, now loop".format(devId) )

		sensorOld = copy.copy(sensors[sensor])

		deldevID = {}			
		for devId in SENSOR:
			if devId not in sensors[sensor]:
				deldevID[devId] = 1
		for dd in	deldevID:
			SENSOR[devId].close_Port()
			del SENSOR[dd]
			
	except Exception as e:
		U.logger.log(20, "in Line {} has error={}".format(sys.exc_info()[-1].tb_lineno, e))
		U.logger.log(20, "{}".format(sensors[sensor]))


#################################
def getAndCheckParam(devId, theItemName, theItem, default, function):
	"""
		@brief this method will fix int, float formats 
	"""
	global sensors, sensor
	
	if theItemName in sensors[sensor][devId]: 
		try: 
			if function == "int":	xx = int(sensors[sensor][devId].get(theItemName, default))
			if function == "float":	xx = float(sensors[sensor][devId].get(theItemName, default))
			if xx != theItem[devId]:
				theItem[devId] = xx
				return theItemName+","
		except Exception as e:
			U.logger.log(20, "in Line {} has error={}".format(sys.exc_info()[-1].tb_lineno, e))
			theItem[devId] = default
	return ""

#################################
def prepGPIOInfoForCommands(devIdSelect, output):
	"""
		@brief this method will prepare dicts to be used when an event occurs to set gpios or unix commands
	"""

	global sensors, sensor
	global SENSOR
	global gpioCmdForAction, gpioNumberForCmdAction, gpioInverseAction, gpioOnTimeAction, anyCmdDefined
	global logLevel
	global gpioUsed
	global gpioInfoIndigoIDForMsgToReceivecommand
	try:
		if devIdSelect != 0: devIdList = [devIdSelect]
		else:
			devIdList = []
			for xx in sensors[sensor]:
				devIdList.append(xx)

		doGpioInfoIndigoIDForMsgToReceivecommand = False
		if logLevel > 1: U.logger.log(20, "starting  devIdSelect:{}, force:{}, devIds:{}".format(devIdSelect, force, devIdList) )
		for devId in devIdList:
			for ii in range(1,9):
				if gpioUsed[ii] == 0: 
					iis = str(ii)
					try:
						if "gpioNumberForCmdAction"+iis in sensors[sensor][devId]:
							if logLevel > 1: U.logger.log(20, "setting #{}, devId:{}".format(iis, devId) )
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

							if logLevel > 0: U.logger.log(20, "devId:{}; checking parameters file for #{}  changed:{}; gpioNumberForCmdAction:>{}< enabled? for gpioCmdForAction:>{}<, ontime:>{}<, inverse:{} conditions: gpioInverse==0/1:{}  gpioOnTime==float:{}  gpioCmd==int:{}  gpioNumber==int:{} ".format(devId, ii,changed, gpioNumberForCmdAction[ii], gpioCmdForAction[ii], gpioOnTimeAction[ii], gpioInverseAction[ii] , gpioInverseAction[ii] in ["0","1"] , isinstance(gpioOnTimeAction[ii],float) , isinstance(gpioCmdForAction[ii], int) , isinstance(gpioNumberForCmdAction[ii], int) ) )
							if changed:
								if gpioInverseAction[ii] in ["0","1"] and isinstance(gpioOnTimeAction[ii],float) and isinstance(gpioCmdForAction[ii], int) and isinstance(gpioNumberForCmdAction[ii], int):
									gpio = gpioNumberForCmdAction[ii] 
									if logLevel > 1: U.logger.log(20, "devId:{}; checking parameters file for #{}  gpioNumberForCmdAction:>{}< enabled? for gpioCmdForAction:>{}<, ontime:>{}<, inverse:{} ".format(devId, ii, gpio, gpioCmdForAction[ii], gpioOnTimeAction[ii], gpioInverseAction[ii]  ) )
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
			if logLevel > 0: U.logger.log(20, "devIdSelect:{}, gpioInfoIndigoIDForMsgToReceivecommand:{} ".format(devIdSelect, gpioInfoIndigoIDForMsgToReceivecommand))

	except Exception as e:
		U.logger.log(20, "in Line {} has error={}".format(sys.exc_info()[-1].tb_lineno, e))
	return 

#################################
def startSensor(devId):
	"""
		@brief this method will start to connect to the sensor
	"""
	global sensors, sensor
	global lastRestart
	global SENSOR
	global i2cOrUart, serialPortName
	global logLevel
	global counter
	global serialItems, failedCount
	global faceDetectionThreshold, gestureDetectionThreshold, detectionRange

	if devId in SENSOR:
		del SENSOR[devId]
	if devId in restartSensor:
		del restartSensor[devId]
		
	ntries = 0

	usePort = ""
	if devId not in SENSOR:
		connected = False
		try:
			if logLevel > 0: U.logger.log(20, "devId:{}; =========== starting sensor  ============= type:\"{}\", \nUSB options:{}, \nUSBownerFile:{}\n==============================\n".format(devId, i2cOrUart[devId], serialItems, readUSBownerFile()))
			if i2cOrUart[devId] == "uart":
				testPort = serialItems
				if sensors[sensor][devId].get("serialPortName","") .find("serial") > -1:
					testPort = ["serial0"]
				for kk in range(len(testPort)):
					usePort = cmdCheckSerialPort(devId, doNotUse=usePort)
					if logLevel > 0: U.logger.log(20, "devId:{}; starting sensor,  serial port:{}, usePort:{}".format(devId, serialPortName[devId], usePort))
					if usePort != "":
						SENSOR[devId] = DFRobot_GestureFaceDetection_UART(baud=GLOB_RT_BAUD_RATE, addr=GLOB_DEVICE_ID, portName=usePort)
						U.logger.log(20, "started with selected port")
						for ntries in range(3): 
							if SENSOR[devId].begin():
								connected = True
								updateUSBownerFile(devId, port=usePort, calledFrom="accepted port")
								break
							if logLevel > 0: U.logger.log(20, "Communication with device failed, trying next port")
							time.sleep(1)
						if not connected: continue # try next port
						break # all ok
					else:
						time.sleep(2)
						
			else: # i2c
				if logLevel > 0: U.logger.log(20, "devId:{}; starting sensor,  i2cAddr:{}".format(devId, GLOB_DEVICE_ID))
				SENSOR[devId] =  DFRobot_GestureFaceDetection_I2C(bus=1, addr=GLOB_DEVICE_ID) 
				for ntries in range(3): 
					try:
						if SENSOR[devId].begin():
							connected = True
							break
						if logLevel > 0: U.logger.log(20, "Communication with device failed, please check connection")
						time.sleep(3)

					except Exception as e:
						U.logger.log(20, "in Line {} has error={}".format(sys.exc_info()[-1].tb_lineno, e))
						if logLevel > 0: U.logger.log(20, "Communication with device failed, please check connection")
						if str(e).find("Connection timed out") > -1:
							break
						time.sleep(3)
					
					
				if not connected: 
						for jj in range(1,8):
							if sensors[sensor][devId].get("gpioCmdForAction"+str(jj),"") == str(GLOB_cmdCodeForrelay):
								if logLevel > 0: U.logger.log(20, "send {} command to gpio #:{}={}".format(GLOB_cmdCodeForrelay, jj, sensors[sensor][devId].get("gpioCmdForAction"+str(jj),"")))
								cmdQueue.put(GLOB_cmdCodeForrelay)
								resetSensorRelay(devId)
								break

			if not connected: 
				failedCount[devId] +=1
				updateUSBownerFile(devId, port=usePort, calledFrom="not connected port")
				return False

			U.logger.log(20, "Communication with device connected after {} tries".format(ntries+1))

			if devId in SENSOR:
				lastRestart	= time.time()
				counter[devId] = 0
				# Wait for the sensor to start.
				time.sleep(5)
			
				# Set face detection score threshold (0~100)
				for ntries in range(5):
					if SENSOR[devId].set_face_detect_thres(faceDetectionThreshold[devId]):
						if logLevel > 0: U.logger.log(20, "Face detection threshold set to:{}".format(faceDetectionThreshold[devId]))
						break
					else:
						if logLevel > 0: U.logger.log(20, "Set the face detection threshold fail. was:{}".format(faceDetectionThreshold[devId]))
					time.sleep(0.2)

				# Set gesture detection score threshold (0~100)
				for ntries in range(5):
					if SENSOR[devId].set_gesture_detect_thres(gestureDetectionThreshold[devId]):
						if logLevel > 0: U.logger.log(20, "Gesture detection threshold set to:{}".format(gestureDetectionThreshold[devId]))
						break
					else:
						if logLevel > 0: U.logger.log(20, "Set the gesture detection threshold fail. was:{}".format(gestureDetectionThreshold[devId]))
					time.sleep(0.2)

				# Set detection range, 0~100
				for ntries in range(5):
					if SENSOR[devId].set_detect_thres(detectionRange[devId]):
						if logLevel > 0: U.logger.log(20, "Detection range set to:{}".format(detectionRange[devId]))
						break
					else:
						if logLevel > 0: U.logger.log(20, "Set the gesture detection range fail. was:{}".format(detectionRange[devId]))
					time.sleep(0.2)
			
			# Retrieve and print PID
				if logLevel > 0: U.logger.log(20, "PID: {}, VID:{}".format(SENSOR[devId].read_pid(), SENSOR[devId].read_vid()) )

		except Exception as e:
			U.logger.log(20, "in Line {} has error={}".format(sys.exc_info()[-1].tb_lineno, e))
			if str(e).find("could not open port /dev/") > -1:
				data = {"sensors":{sensor:{devId:"badsenor_error:bad_port_setting_/dev/"+serialPortName[devId]}}}
				U.sendURL(data)
			del SENSOR[devId]
			
	return True

###################################################################################################
# manage USB and serial ports between sensors of this type and other device types ##
###################################################################################################
def updateUSBownerFile(devId, port="x", failed="x", calledFrom=""):
	"""
		@brief this method will update the USB owner file 
	"""
	global logLevel, localUSBownerFile
	try:
		if devId in localUSBownerFile:
			if port !="x":
				localUSBownerFile[devId]["ok"] = port
			if failed not in ["x",""] and failed not in localUSBownerFile[devId]["failed"]:
				localUSBownerFile[devId]["failed"].append(failed)
				
		writeUSBownerFile(localUSBownerFile)
		if logLevel > 1: U.logger.log(20, "devId:{}; calledf:{}, writing   USBownerFile:{} ".format(devId, calledFrom, localUSBownerFile))
		localUSBownerFile = readUSBownerFile()
		if logLevel > 1: U.logger.log(20, "devId:{}; calledf:{}, read back USBownerFile:{} ".format(devId, calledFrom, localUSBownerFile))

	except Exception as e:
			U.logger.log(20, "in Line {} has error={}".format(sys.exc_info()[-1].tb_lineno, e))
	return localUSBownerFile
	
#################################
def readUSBownerFile():
	"""
		@brief this method will read the USB owner file 
	"""
	global logLevel, localUSBownerFile
	try:
		localUSBownerFile, xxx = U.readJson(GLOB_USBownerFile)
		return localUSBownerFile
	except Exception as e:
			U.logger.log(20, "in Line {} has error={}".format(sys.exc_info()[-1].tb_lineno, e))
	return {}

#################################
def initUSBownerFile(firstRead):
	global logLevel, localUSBownerFile
	"""
		@brief this method will init the USB owner file 
	"""
	try:
		localUSBownerFile = readUSBownerFile()
		if type(localUSBownerFile) != type({}): localUSBownerFile = {}
		if firstRead: 
			for devId in localUSBownerFile:
				if "devType" == G.program:
					localUSBownerFile[devId] = {"failed":[], "ok":"", "devType":G.program}
			writeUSBownerFile(localUSBownerFile)
	except Exception as e:
			U.logger.log(20, "in Line {} has error={}".format(sys.exc_info()[-1].tb_lineno, e))
	return localUSBownerFile
	
#################################
def clearUSBownerFile(devId, firstRead):
	"""
		@brief this method will clear the USB owner file 
	"""
	global logLevel, localUSBownerFile
	try:
			if firstRead: localUSBownerFile[devId] = {"failed":[], "ok":"", "devType":G.program}
			if devId not in localUSBownerFile: localUSBownerFile[devId] = {"failed":[], "ok":"", "devType":G.program}
			localUSBownerFile[devId]["ok"] = ""
			writeUSBownerFile(localUSBownerFile)
	except Exception as e:
			U.logger.log(20, "in Line {} has error={}".format(sys.exc_info()[-1].tb_lineno, e))
	return localUSBownerFile
	
#################################
def checkifdevIdInUSBownerFile(devId):
	"""
		@brief this method will check if devId is already in USB owner file 
	"""
	global logLevel, localUSBownerFile
	try:
			if devId not in localUSBownerFile: localUSBownerFile[devId] = {"failed":[], "ok":"", "devType":G.program}
			writeUSBownerFile(localUSBownerFile)
	except Exception as e:
			U.logger.log(20, "in Line {} has error={}".format(sys.exc_info()[-1].tb_lineno, e))
	return localUSBownerFile

#################################
def checkifIdInOKUSBownerFile(devId, findThis):
	"""
		@brief this method will devid and findthis is ok
	"""
	global logLevel, localUSBownerFile
	try:
			if devId not in localUSBownerFile: return False
			if findThis == localUSBownerFile[devId]["ok"]: return True
			return False
	except Exception as e:
			U.logger.log(20, "in Line {} has error={}".format(sys.exc_info()[-1].tb_lineno, e))
	return False

#################################
def checkifIdInFAILEDUSBownerFile(devId, findThis):
	"""
		@brief this method will devid and findthis is failed
	"""
	global logLevel, localUSBownerFile
	try:
			if devId not in localUSBownerFile: return False
			if findThis in localUSBownerFile[devId]["failed"]: return True
			return False
	except Exception as e:
			U.logger.log(20, "in Line {} has error={}".format(sys.exc_info()[-1].tb_lineno, e))
	return False

#################################
def getdevIdsUSBownerFile():
	"""
		@brief this method will get info for devid 
	"""
	global logLevel, localUSBownerFile
	try:
			retList = []
			for devId in localUSBownerFile:
				retList.append(devId )
			return retList
	except Exception as e:
			U.logger.log(20, "in Line {} has error={}".format(sys.exc_info()[-1].tb_lineno, e))
	return []

#################################
def writeUSBownerFile(USBownerFile):
	"""
		@brief this method will write to usb owner file
	"""
	global logLevel, localUSBownerFile
	try:
		localUSBownerFile = copy.copy(USBownerFile)
		U.writeJson(GLOB_USBownerFile, localUSBownerFile, sort_keys=False, indent=4)
	except Exception as e:
			U.logger.log(20, "in Line {} has error={}".format(sys.exc_info()[-1].tb_lineno, e))
	return 

###################################################################################################
# manage USB and serial ports between sensors of this type and other device types   ==== END ##
###################################################################################################



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
			if "loglevel" 		in data: 
				logLevel = data["loglevel"]
				SENSOR[devId].set_Params(logLevel=logLevel)
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

	try:
		if i2cOrUart[devId] == "uart": return 
		
		if U.checki2cdetect == "bad":
			U.logger.log(20, "i2c hangs, needs reset")

		if os.path.isfile(GLOB_recoveryPrevious): 
			os.remove(GLOB_recoveryPrevious)

		if os.path.isfile(GLOB_recoverymessage): 
			os.rename(GLOB_recoverymessage,GLOB_recoveryPrevious)

		tt = time.time()
		for ii in range(8):
			if sensors[sensor][devId].get("gpioCmdForAction"+str(ii),"") == str(GLOB_cmdCodeForrelay):
				cmdQueue.put(GLOB_cmdCodeForrelay)
				time.sleep(6)
				break
		msg = {"devId":devId,"time":time.time()}
		U.writeJson(GLOB_recoverymessage, msg)

		if time.time() - tt < 2: time.sleep(10)
		U.restartMyself(reason="sensor not answering", delay=0, python3=True)

	except Exception as e:
		U.logger.log(20, "in Line {} has error={}".format(sys.exc_info()[-1].tb_lineno, e))
	return
	

############################################
def sendRecoveryMessage():
	sendxxRecoveryMessage(1001)
	return

############################################
def sendNotRecoveryMessage():
	sendxxRecoveryMessage(1002)
	return

############################################
def sendxxRecoveryMessage(code):
	"""
		@brief this method will  send a "recovery" message to indigoIdOfOutputDevice
	"""
	global sensor, lastAliveSend
	try:
		if not os.path.isfile(GLOB_recoverymessage): return
		previousReset = ""
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
	"""
		@brief this method will get the values for sensor with devid
	"""
	global sensor, sensors,	 SENSOR, badSensor, tmpMuteOff, learningOn
	global keepAwake
	global i2cOrUart
	global cmdQueue, anyCmdDefined
	global logLevel, firstCmdReceived
	global reactOnlyToCommands, ignoreUntilEndOfLearning
	global cmdToText
	global lastCommandReceived, lastValidCmdAt, ignoreSameCommands

	try:
		CMDID = -1
		cmdScore = -1
		facesScore = -1
		facesX = -1
		facesY = -1
		faces = -1
		if wait >0: time.sleep(wait)

		if devId not in SENSOR:
			badSensor[devId] += 1
			return "badSensor"

		for ii in range(2):
			try:
				faces = SENSOR[devId].get_face_number()
				if badSensor[devId] > 1:
					if logLevel > 0: U.logger.log(20, "devID:{}; faces: {:3d}, badSensorCount:{}".format(devId, faces, badSensor[devId])  )
				if faces == 0: continue
			except Exception as e:
				if logLevel > 0: U.logger.log(20, "devID:{}; error in received CMDID: {:3d}, badSensorCount:{}, error:{}".format(devId, CMDID, badSensor[devId], e)  )
				if str(e).find("Input/output error") >0: badSensor[devId] += 2
				badSensor[devId] += 1
				return "badSensor"

			facesScore = SENSOR[devId].get_face_score()
			facesX	= SENSOR[devId].get_face_location_x()
			facesY = SENSOR[devId].get_face_location_y()


			if logLevel > 2: U.logger.log(20, f'devId:{devId:}, faces:{faces:}, faceScore:{facesScore:}, facesX:{facesX:}, facesY:{facesY:}' )
			for jj in range(3):
				CMDID = int(SENSOR[devId].get_gesture_type())
				cmdScore = SENSOR[devId].get_gesture_score()
				if CMDID > 0: 
					if logLevel > 1: U.logger.log(20, f'devId:{devId:}, faces:{faces:}, faceScore:{facesScore:}, facesX:{facesX:}, facesY:{facesY:}' )
					if logLevel > 1: U.logger.log(20, f'              counter:{counter[devId]:}, cmd:{CMDID:}, cmdScore:{cmdScore:}, cmdText:{cmdToText.get(CMDID,""):}' )
					break
				time.sleep(0.1)
				
			if CMDID > 0: break 
			time.sleep(0.5)
		
		if badSensor[devId] > 1:
			U.logger.log(20, "devID:{}; reset bad sensor count CMDID:{}, after {:} bad sensor readings".format(devId, CMDID, badSensor[devId])  )
			badSensor[devId] = 0

		if CMDID == 0 or not acceptCMDID(devId, CMDID):
			return {"cmd":0}
				
		if logLevel > 0: U.logger.log(20, f'== devId:{devId:}, counter:{counter[devId]:}, cmd:{CMDID:}, cmdScore:{cmdScore:}, cmdText:{cmdToText.get(CMDID,""):}, faces:{faces:}, faceScore:{facesScore:}, facesX:{facesX:}, facesY:{facesY:}' )
		return {"counter":counter[devId], "cmd":CMDID, "cmdScore":cmdScore, "cmdText":cmdToText.get(CMDID,""), "faces":faces, "faceScore ":facesScore, "facesX":facesX, "facesY":facesY }


	except Exception as e:
		U.logger.log(20, "in Line {} has error={}".format(sys.exc_info()[-1].tb_lineno, e))

	badSensor[devId] += 1
	if badSensor[devId] >= 5: return "badSensor"
	return ""


############################################
def acceptCMDID(devId, CMDID):
	"""
		@brief this method will check if we should accept this command id, depending on timing of last same command
	"""
	global lastCommandReceived, lastValidCmdAt, ignoreSameCommands
	global anyCmdDefined

	if CMDID <= 0: return False
	for dd in lastCommandReceived:
		if lastCommandReceived[dd] == CMDID and ignoreSameCommands[dd] > 0 and time.time() - lastValidCmdAt[dd] < ignoreSameCommands[dd]:
			return False

	lastValidCmdAt[devId] = time.time()
	lastCommandReceived[devId] = CMDID 
	if anyCmdDefined: cmdQueue.put(CMDID)

	return True

############################################
def startThreads():
	"""
		@brief this method willstart the thread for setting gpios
	"""
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
	"""
		@brief this method will read cmdQueue and send commands to receiveCommands.py via file
	"""
	global gpioCmdForAction, gpioNumberForCmdAction, gpioInverseAction, gpioOnTimeAction	
	global cmdQueue, threadCMD
	global logLevel, anyCmdDefined
	global unixCmdAction, unixCmdVoiceNo
	global gpioInfoIndigoIDForMsgToReceivecommand

	try:
		time.sleep(1)
		if logLevel > 0: U.logger.log(20, "start  GPIO action  thread")
		while threadCMD["state"] == "running":
			time.sleep(0.1)
			try:
				outFile = []
				pinsUsed = []
				last = []
				while not cmdQueue.empty():
					cmd = cmdQueue.get()
					if logLevel > 1: U.logger.log(20, "checking gpio requests command:{} ===== anyCmdDefined:{}".format(cmd, anyCmdDefined) )
					if cmd > 300: continue  # ignore status messages
					if anyCmdDefined:
						for ii in range(1,9):
							if gpioNumberForCmdAction[ii] == "": 			continue
							if gpioCmdForAction[ii] == "": 					continue
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
									outFile.append({"device": devType, "devId":indigoIdOfOutputDevice, "pin": gpio, "command": "pulseUp", "values": {"pulseUp": gpioOnTimeAction[ii]}, "inverseGPIO": gpioInverseAction[ii] != "0", "debug":max(10,min(30,logLevel*10))})
									pinsUsed.append(gpio)
							else:
								if 	gpioCmdForAction[ii] == cmd:
									outFile.append({"device": devType, "devId":indigoIdOfOutputDevice, "pin": gpio, "command": "pulseUp", "values": {"pulseUp": gpioOnTimeAction[ii]}, "inverseGPIO": gpioInverseAction[ii] != "0", "debug":max(10,min(30,logLevel*10))})
									pinsUsed.append(gpio)
								if gpioCmdForAction[ii] == 0:
									last.append({"device": devType, "devId":indigoIdOfOutputDevice, "pin": gpio, "command": "pulseUp", "values": {"pulseUp": gpioOnTimeAction[ii]}, "inverseGPIO": gpioInverseAction[ii] != "0", "debug":max(10,min(30,logLevel*10))})
									pinsUsed.append(gpio)
								
				if outFile != [] or last != []:
					if last != []: outFile += last
					f = open(GLOB_fileToReceiveCommands,"a")
					f.write(json.dumps(outFile))
					f.close()
					if logLevel > 0: U.logger.log(20, "sending cmd:{} to receiveCommands file:{}".format(outFile, GLOB_fileToReceiveCommands) )
									
								
			except Exception as e:
				U.logger.log(20, "in Line {} has error={}".format(sys.exc_info()[-1].tb_lineno, e))
				time.sleep(10)
				

	except Exception as e:
		U.logger.log(20, "in Line {} has error={}".format(sys.exc_info()[-1].tb_lineno, e))
	if logLevel > 0: U.logger.log(20, "ended  loop, state:{}".format(threadCMD["state"] ))


############################################
def cmdCheckSerialPort( devId, doNotUse=""):
	"""
		@brief this method will  the serial ports if present and properly defined, if not reboot might be issued
	"""
	global gpioCmdForAction, gpioNumberForCmdAction, gpioInverseAction, gpioOnTimeAction, serialPortName
	global sensor, sensors
	try:
		for ii in range(30):
			raspi, ddd = U.readJson(G.homeDir+"raspiConfig.params")
			reboot = False
			if ddd == "":
				time.sleep(2)
				continue

			U.logger.log(20, "raspiConfig.params file found:  \nSERIAL_HARDWARE:{}, \nSERIAL_CONSOLE:{} \nSERIAL_CONSOLE_OLD:{}".format(raspi.get("SERIAL_HARDWARE",""), raspi.get("SERIAL_CONSOLE",""), raspi.get("SERIAL_CONSOLE_OLD","") ))

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
					if logLevel > 1: U.logger.log(20, "serial port configured properly")

			break

		if logLevel > 1: U.logger.log(20, "after check serial hw: reboot; {}, doNotUse>{}<".format(reboot, doNotUse))

		if not reboot:
			checkPort = serialPortName[devId].strip("*")
			if logLevel > 1: U.logger.log(20, "devId:{}, checkPort:{}, \nUSBownerFile:{}".format(devId, checkPort, readUSBownerFile() ))
			
			checkifdevIdInUSBownerFile(devId)

			updateUSBownerFile(devId, port="", failed=doNotUse, calledFrom="clear port")

			cmd = "/bin/ls -l /dev | /usr/bin/grep "+checkPort
			ret = subprocess.Popen(cmd,shell=True,stdout=subprocess.PIPE,stderr=subprocess.PIPE).communicate()[0].decode('utf-8')
			if logLevel > 1: U.logger.log(20, " ls -l /dev  ret:\n{}".format(ret))
			
			for line in ret.split("\n"):
				pp = line.find(checkPort)
				if pp < 10: continue		
				U.logger.log(20, " pp:{}, line {}".format(pp, line))
				findThis = line[pp-1:].strip()
				findThis = findThis.split(" ")[0]
				alreadyInUse = 0
				
				if checkifIdInFAILEDUSBownerFile(devId, findThis):
					if logLevel > 1:U.logger.log(20, "devId:{}, skipping:{} in failed list".format(devId, findThis))
					continue

				if not checkifIdInOKUSBownerFile(devId, findThis):
					for dddd in getdevIdsUSBownerFile():
						if checkifIdInOKUSBownerFile(dddd, findThis): 
							if logLevel > 1:U.logger.log(20, "devId:{}, already in use by devId:{}  port:{}".format(devId, dddd, findThis))
							alreadyInUse = dddd
							break
						
				if alreadyInUse == 0:
						if logLevel > 1:U.logger.log(20, "devId:{}  selected port:{}".format(devId, findThis))
						return findThis
	
			msg = "bad_port:_/dev/"+serialPortName[devId]
			msg += ", rebooting now"
			U.logger.log(20, " {}".format(msg))
			U.sendURL({"sensors":{sensor:{devId:{"cmd":900}}}}, wait=False)
			time.sleep(10000)
			U.setRebootRequest("adding serial port")


	except Exception as e:
		U.logger.log(20, "in Line {} has error={}".format(sys.exc_info()[-1].tb_lineno, e))

	return ""
	

		
############################################
def execSensorLoop():
	global sensor, sensors, badSensor
	global SENSOR, sensorMode
	global oldRaw, lastRead
	global startTime, lastMeasurement, lastRestart
	global oldi2cOrUart, i2cOrUart, oldserialPortName, sensorOld, serialPortName
	global gpioCmdForAction, gpioNumberForCmdAction, gpioInverseAction, gpioOnTimeAction
	global anyCmdDefined
	global cmdQueue, logLevel
	global threadCMD
	global firstCmdReceived
	global reactOnlyToCommands
	global gpioUsed 
	global unixCmdVoiceNo, unixCmdAction
	global cmdToText
	global counter
	global USBowner,failedCount
	global lastCommandReceived, lastValidCmdAt, ignoreSameCommands
	global faceDetectionThreshold, gestureDetectionThreshold, detectionRange, restartSensor
	global lastAliveSend
	global gpioInfoIndigoIDForMsgToReceivecommand

	gpioInfoIndigoIDForMsgToReceivecommand							= {}
	restartSensor					= {}
	failedCount						= {}
	cmdToText						= {0:"none", 1:"LIKE-blue",2:"OK-green",3:"STOP-red",4:"YES-yellow",5:"SIX-purple"}
	faceDetectionThreshold			= {}
	gestureDetectionThreshold		= {}
	detectionRange					= {}
	lastCommandReceived				= {}
	lastValidCmdAt					= {}
	ignoreSameCommands				= {}
	USBowner						= {}
	counter							= {}
	gpioUsed 						= [0,0,0,0,0,0,0,0,0,0]
	reactOnlyToCommands				= {}
	serialPortName					= {}
	oldserialPortName				= {}
	oldi2cOrUart					= {}
	i2cOrUart						= {}
	sensorOld						= {}
	badSensor						= {}
	lastRestart						= time.time()
	SENSOR							= {}
	firstCmdReceived				= False
	logLevel						= 0
	cmdQueue						= queue.Queue()
	unixCmdVoiceNo					= ["","","","","","","","","",""]
	unixCmdAction					= ["","","","","","","","","",""]
	gpioCmdForAction				= ["","","","","","","","","",""]
	gpioNumberForCmdAction			= ["","","","","","","","","",""]
	gpioInverseAction				= ["","","","","","","","","",""]
	gpioOnTimeAction				= ["","","","","","","","","",""]
	anyCmdDefined					= False

	sendToIndigoSecs				= 500
	startTime						= time.time()
	lastMeasurement					= time.time()
	oldRaw							= ""
	lastRead						= 0
	sensorRefreshSecs				= 0.5
	sensors							= {}
	sensor							= G.program
	myPID							= str(os.getpid())
	U.setLogging()
	U.killOldPgm(myPID,G.program+".py")# kill old instances of myself if they are still running

	U.logger.log(20, "==== start {}".format(version))

	if U.getIPNumber() > 0:
		time.sleep(10)
		exit()

	startThreads()

	readParams()

	time.sleep(1)

	lastRead = time.time()

	U.echoLastAlive(G.program)

	devId				= ""
	lastAliveSend		= {}
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

					if badSensor[devId] >= 5 or type(theValues) == type(" ") or failedCount[devId] > 6:
						if badSensor[devId] in [5,6,9]  or badSensor[devId]  > 20 or failedCount[devId] > 6:
							extraSleep = 2
							sendData = True
							sendNotRecoveryMessage()
							resetSensorRelay(devId)
							break
						extraSleep = 2

					if theValues == "badSensor": 
						time.sleep(2)

					else:
						if time.time() - startTime < 10: sendRecoveryMessage()

						if theValues.get("faces",0) != 0:
							data["sensors"][sensor][devId] = theValues
							U.sendURL(data, wait=False)
							lastAliveSend[devId] = time.time()
	
						elif tt - sendToIndigoSecs > lastAliveSend[devId]:
							data["sensors"][sensor][devId] = {"cmd":700,"text":"alive message"}
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
				readParams()
				lastRead = time.time()

			#U.logger.log(20, "dt time last{:.1f},  start:{:.1f}".format(time.time()  - lastMeasurement, time.time()  - startTime))


			dtLast = time.time()  - lastMeasurement
			slTime = max(0., sensorRefreshSecs + extraSleep  - dtLast )
			#U.logger.log(20, "slTime:{:.1f}".format(slTime))
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


