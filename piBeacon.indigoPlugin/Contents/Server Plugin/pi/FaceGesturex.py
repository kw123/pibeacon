# -*- coding:utf-8 -*-

'''
	@file DFRobot_RTU.py
	@brief Modbus RTU libary for Arduino. 
	
	@copyright   Copyright (c) 2025 DFRobot Co.Ltd (http://www.dfrobot.com)
	@licence     The MIT License (MIT)
	@author [Arya](xue.peng@dfrobot.com)
	@version  V1.0
	@date  2021-07-16
	@https://github.com/DFRobot/DFRobot_RTU
'''
import sys
import serial
import time
from smbus2 import SMBus, i2c_msg

import logging
from ctypes import *
import os, json, datetime, subprocess, copy

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

version			= 1.0

G.program = "FaceGesture"

GLOB_resetFile						= G.homeDir+"temp/DF2301Q.reset"
GLOB_restartFile					= G.homeDir+"temp/DF2301Q.restart"
GLOB_commandFile					= G.homeDir+"temp/DF2301Q.cmd"
GLOB_expectResponseAfter			= 10 # seconds
GLOB_maxRestartConnections			= 5  # count




sys.path.append("../")

class DFRobot_RTU(object):
	
	_packet_header = {"id": 0, "cmd": 1, "cs": 0}
	
	'''Enum constant'''
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

	def __init__(self, baud, bits, parity, stopbit):
		'''
			@brief Serial initialization.
			@param baud:  The UART baudrate of raspberry pi
			@param bits:  The UART data bits of raspberry pi
			@param parity:  The UART parity bits of raspberry pi
			@param stopbit:  The UART stopbit bits of raspberry pi.
		'''
		#self._ser = serial.Serial("/dev/ttyAMA0",baud, bits, parity, stopbit)
		self._ser = serial.Serial("/dev/serial0",baud, bits, parity, stopbit)
		self._timeout = 0.1 #0.1s
	
	def set_timout_time_s(self, timeout = 0.1):
		'''
			@brief Set receive timeout time, unit s.
			@param timeout:  receive timeout time, unit s, default 0.1s.
		'''
		self._timeout = timeout

	def read_coils_register(self, id, reg):
		'''
			@brief Read a coils Register.
			@param id:  modbus device ID. Range: 0x00 ~ 0xF7(0~247), 0x00 is broadcasr address, which all slaves will process broadcast packets, 
			@n          but will not answer.
			@param reg: Coils register address.
			@return Return the value of the coils register value.
			@n      True: The value of the coils register value is 1.
			@n      False: The value of the coils register value is 0.
		'''
		l = [(reg >> 8)&0xFF, (reg & 0xFF), 0x00, 0x01]
		val = False
		if (id < 1) or (id > 0xF7):
			print("device addr error.(1~247) %d"%id)
			return 0
		l = self._packed(id, self.eCMD_READ_COILS, l)
		self._send_package(l)
		l = self.recv_and_parse_package(id, self.eCMD_READ_COILS,1)
		if (l[0] == 0) and len(l) == 7:
			if (l[4] & 0x01) != 0:
					val = True
		return val
			
	def read_discrete_inputs_register(self, id, reg):
		'''
			@brief Read a discrete input register.
			@param id:  modbus device ID. Range: 0x00 ~ 0xF7(0~247), 0x00 is broadcasr address, which all slaves will process broadcast packets, 
			@n          but will not answer.
			@param reg: Discrete input register address.
			@return Return the value of the discrete input register value.
			@n      True: The value of the discrete input register value is 1.
			@n      False: The value of the discrete input register value is 0.
		'''
		l = [(reg >> 8)&0xFF, (reg & 0xFF), 0x00, 0x01]
		val = False
		if (id < 1) or (id > 0xF7):
			print("device addr error.(1~247) %d"%id)
			return 0
		l = self._packed(id, self.eCMD_READ_DISCRETE, l)
		self._send_package(l)
		l = self.recv_and_parse_package(id, self.eCMD_READ_DISCRETE,1)
		if (l[0] == 0) and len(l) == 7:
			if (l[4] & 0x01) != 0:
					val = True
		return val
			
	def read_holding_register(self, id, reg):
		'''
			@brief Read a holding Register.
			@param id:  modbus device ID. Range: 0x00 ~ 0xF7(0~247), 0x00 is broadcasr address, which all slaves will process broadcast packets, 
			@n          but will not answer.
			@param reg: Holding register address.
			@return Return the value of the holding register value.
		'''
		l = [(reg >> 8)&0xFF, (reg & 0xFF), 0x00, 0x01]
		if (id < 1) or (id > 0xF7):
			print("device addr error.(1~247) %d"%id)
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
		'''
			@brief Read a input Register.
			@param id:  modbus device ID. Range: 0x00 ~ 0xF7(0~247), 0x00 is broadcasr address, which all slaves will process broadcast packets, 
			@n          but will not answer.
			@param reg: Input register address.
			@return Return the value of the holding register value.
		'''
		l = [(reg >> 8)&0xFF, (reg & 0xFF), 0x00, 0x01]
		if (id < 1) or (id > 0xF7):
			print("device addr error.(1~247) %d"%id)
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
		'''
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
		'''
		val = 0x0000
		re = True
		if flag:
			val = 0xFF00
			re = False
		l = [(reg >> 8)&0xFF, (reg & 0xFF), (val >> 8)&0xFF, (val & 0xFF)]
		if(id > 0xF7):
			print("device addr error.")
			return 0
		l = self._packed(id, self.eCMD_WRITE_COILS, l)
		self._send_package(l)
		l = self.recv_and_parse_package(id, self.eCMD_WRITE_COILS,reg)
		return l[0]
			

	def write_holding_register(self, id, reg, val):
		'''
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
		'''
		l = [(reg >> 8)&0xFF, (reg & 0xFF), (val >> 8)&0xFF, (val & 0xFF)]
		val = 0
		if(id > 0xF7):
			print("device addr error.")
			return 0
		l = self._packed(id, self.eCMD_WRITE_HOLDING, l)
		self._send_package(l)
		l = self.recv_and_parse_package(id, self.eCMD_WRITE_HOLDING,reg)
		return l[0]
			
	def read_coils_registers(self, id, reg, reg_num):
		'''
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
		'''
		length = reg_num // 8
		mod = reg_num % 8
		if mod:
			length += 1
		l = [(reg >> 8)&0xFF, (reg & 0xFF), (reg_num >> 8) & 0xFF, reg_num & 0xFF]
		if (id < 1) or (id > 0xF7):
			print("device addr error.(1~247) %d"%id)
			return [self.eRTU_ID_ERROR]
		l = self._packed(id, self.eCMD_READ_COILS, l)
		self._send_package(l)
		l = self.recv_and_parse_package(id, self.eCMD_READ_COILS,length)
		if ((l[0] == 0) and (len(l) == (5+length+1))):
			la = [l[0]] + l[4: len(l)-2]
			return la
		return [l[0]]
		
	def read_discrete_inputs_registers(self, id, reg, reg_num):
		'''
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
		'''
		length = reg_num // 8
		mod = reg_num % 8
		if mod:
			length += 1
		l = [(reg >> 8)&0xFF, (reg & 0xFF), (reg_num >> 8) & 0xFF, reg_num & 0xFF]
		if (id < 1) or (id > 0xF7):
			print("device addr error.(1~247) %d"%id)
			return [self.eRTU_ID_ERROR]
		l = self._packed(id, self.eCMD_READ_DISCRETE, l)
		self._send_package(l)
		l = self.recv_and_parse_package(id, self.eCMD_READ_DISCRETE,length)
		if ((l[0] == 0) and (len(l) == (5+length+1))):
			la = [l[0]] + l[4: len(l)-2]
			return la
		return [l[0]]
		
	def read_holding_registers(self, id, reg, size):
		'''
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
		'''
		l = [(reg >> 8)&0xFF, (reg & 0xFF), (size >> 8) & 0xFF, size & 0xFF]
		if (id < 1) or (id > 0xF7):
			print("device addr error.(1~247) %d"%id)
			return [self.eRTU_ID_ERROR]
		l = self._packed(id, self.eCMD_READ_HOLDING, l)
		self._send_package(l)
		l = self.recv_and_parse_package(id, self.eCMD_READ_HOLDING,size*2)
		#lin = ['%02X' % i for i in l]
		#print(" ".join(lin))
		if (l[0] == 0) and (len(l) == (5+size*2+1)):
			la = [l[0]] + l[4: len(l)-2]
			return la
		return [l[0]]

	def read_input_registers(self, id, reg, size):
		'''
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
		'''
		l = [(reg >> 8)&0xFF, (reg & 0xFF), (size >> 8) & 0xFF, size & 0xFF]
		if (id < 1) or (id > 0xF7):
			print("device addr error.(1~247) %d"%id)
			return [self.eRTU_ID_ERROR]
		l = self._packed(id, self.eCMD_READ_INPUT, l)
		self._send_package(l)
		l = self.recv_and_parse_package(id, self.eCMD_READ_INPUT,size*2)
		#lin = ['%02X' % i for i in l]
		#print(" ".join(lin))
		if (l[0] == 0) and (len(l) == (5+size*2+1)):
			la = [l[0]] + l[4: len(l)-2]
			return la
		return [l[0]]
		
	def write_coils_registers(self, id, reg, reg_num, data):
		'''
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
		'''
		length = reg_num // 8
		mod = reg_num % 8
		if mod:
			length += 1
		if len(data) < length:
			return [self.eRTU_EXCEPTION_ILLEGAL_DATA_VALUE]
		l = [(reg >> 8)&0xFF, (reg & 0xFF), ((reg_num >> 8) & 0xFF), (reg_num & 0xFF), length] + data
		if(id > 0xF7):
			print("device addr error.")
			return 0
		l = self._packed(id, self.eCMD_WRITE_MULTI_COILS, l)
		self._send_package(l)
		l = self.recv_and_parse_package(id, self.eCMD_WRITE_MULTI_COILS,reg)
		if (l[0] == 0) and len(l) == 9:
			val = ((l[5] << 8) | l[6]) & 0xFFFF
		return l[0]
			
	def write_holding_registers(self, id, reg, data):
		'''
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
		'''
		size = len(data) >> 1
		l = [(reg >> 8)&0xFF, (reg & 0xFF), ((size >> 8) & 0xFF), (size & 0xFF), size*2] + data
		if(id > 0xF7):
			print("device addr error.")
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
		#print("len=%d"%length)
		pos = 0
		while pos < length:
			crc ^= (data[pos] | 0x0000)
			#print("pos=%d, %02x"%(pos,data[pos]))
			i = 8;
			while i != 0:
				if (crc & 0x0001) != 0:
					crc = (crc >> 1)&0xFFFF
					crc ^= 0xA001
				else:
					crc = (crc >> 1)&0xFFFF
				i -= 1
			pos += 1
		crc = (((crc & 0x00FF) << 8) | ((crc & 0xFF00) >> 8)) & 0xFFFF
		#print("crc=%x"%crc)
		return crc

	def _clear_recv_buffer(self):
		remain = self._ser.inWaiting()
		while remain:
			self._ser.read(remain)
			remain = self._ser.inWaiting()

	def _packed(self, id, cmd, l):
		length = 4+len(l)
		#print(len(l))
		package = [0]*length
		package[0] = id
		package[1] = cmd
		package[2:length-2] = l
		#lin = ['%02X' % i for i in package]
		#print(" ".join(lin))

		crc = self._calculate_crc(package[:len(package)-2])
		package[length-2] = (crc >> 8) & 0xFF
		package[length-1] = crc & 0xFF
		
		#lin = ['%02X' % i for i in package]
		#print(" ".join(lin))
		return package;

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
				#print("%d = %02X"%(index, head[index]))
				index += 1
				if (index == 1) and (head[0] != id):
					index = 0
				elif (index == 2) and ((head[1] & 0x7F) != cmd):
					index = 0
				remain = index
				t = time.time()
			if time.time() - t > self._timeout:
				#print("time out.")
				return [self.eRTU_RECV_ERROR]
			if(index == 4):
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
						  #print("index = 0")
						else:
						  index = 8
						  #print("index = 8")
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
						if(time.time() - t >self._timeout):
						  print("time out1.")
						  return [self.eRTU_RECV_ERROR]
					crc = ((package[len(package) - 2] << 8) | package[len(package) - 1]) & 0xFFFF
					if crc != self._calculate_crc(package[1:len(package) - 2]):
						print("CRC ERROR")
						return [self.eRTU_RECV_ERROR]
					if package[2] & 0x80:
						package[0] = package[3]
					else:
						package[0] = 0
					#lin = ['%02X' % i for i in package]
					#print(" ".join(lin))
					return package

# -*- coding: utf-8 -*-
'''
  @file DFRobot_GestureFaceDetection.py
  @brief Define the basic structure and methods of the DFRobot_GestureFaceDetection class.
  @copyright   Copyright (c) 2025 DFRobot Co.Ltd (http://www.dfrobot.com)
  @license     The MIT license (MIT)
  @author [thdyyl](yuanlong.yu@dfrobot.com)
  @version  V1.0
  @date  2025-03-17
  @https://github.com/DFRobot/DFRobot_GestureFaceDetection
'''


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
		'''
			@brief Init function
			@return True if initialization is successful, otherwise false.
		'''
		if self.readInputReg(self.REG_GFD_PID) == self.GFD_PID:
			return True
		return False


	def read_pid(self):
		'''
			@brief Get the device PID
			@return Return the device PID 
		'''
		return self.readInputReg(self.REG_GFD_PID)


	def read_vid(self):
		'''
			@brief Get the device VID
			@return Return the device VID
		'''
		return self.readInputReg(self.REG_GFD_VID)


	def config_uart(self, baud, parity, stop_bit):
		'''
			@brief Configure UART
			@n !!!However, the current CSK6 chip's serial port only supports changing the baud rate, and the stop and check bits should be set to default.
			@param baud Baud rate  EBAUD_1200 ~ EBAUD_921600
			@param parity Parity bit UART_CFG_PARITY_NONE ~ UART_CFG_PARITY_SPACE 
			@param stop_bit Stop bits UART_CFG_STOP_BITS_0_5 ~ UART_CFG_STOP_BITS_2
			@return Return 0 if configuration is successful, otherwise return error code.
		'''
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
		'''
			@brief Get the number of detected faces
			@return Return the number of detected faces
		'''
		return self.readInputReg(self.REG_GFD_FACE_NUMBER)


	def get_face_location_x(self):
		'''
			@brief Get the X location of the face
			@return Return the X location
		'''
		return self.readInputReg(self.REG_GFD_FACE_LOCATION_X)


	def get_face_location_y(self):
		'''
			@brief Get the Y location of the face
			@return Return the Y location
		'''
		return self.readInputReg(self.REG_GFD_FACE_LOCATION_Y)


	def get_face_score(self):
		'''
			@brief Get the face score
			@return Return the face score
		'''
		return self.readInputReg(self.REG_GFD_FACE_SCORE)


	def get_gesture_type(self):
		'''
			@brief Get the gesture type
					- 1: LIKE (👍) - blue
					- 2: OK (👌) - green
					- 3: STOP (🤚) - red
					- 4: YES (✌) - yellow
					- 5: SIX (🤙) - purple
			@return Return the gesture type
		'''
		return self.readInputReg(self.REG_GFD_GESTURE_TYPE)


	def get_gesture_score(self):
		'''
			@brief Get the gesture score
			@return Return the gesture score
		'''
		return self.readInputReg(self.REG_GFD_GESTURE_SCORE)


	def set_face_detect_thres(self, score):
		'''
			@brief Set the face detection threshold
			@n Sets the threshold for face detection (0-100). Default is 60%
			@param score Threshold score
		'''
		if (0 >= score) or (score > 100):
				return False
		return self.writeHoldingReg(self.REG_GFD_FACE_SCORE_THRESHOLD, score)


	def get_face_detect_thres(self):
		'''
			@brief Get the face detection threshold
			@n Get the threshold for face detection (0-100). Default is 60%
			@return Return the face detection threshold
		'''
		return self.readHoldingReg(self.REG_GFD_FACE_SCORE_THRESHOLD)


	def set_detect_thres(self, x):
		'''
			@brief Set the x-range for face detection
			@n Sets the threshold for detecting the X coordinate (0-100). Default is 60%.
			@param x Threshold value
		'''
		if (0 >= x) or (x > 100):
				return False
		return self.writeHoldingReg(self.REG_GFD_FACE_THRESHOLD, x)


	def get_detect_thres(self):
		'''
			@brief Get the x-range for face detection
			@n Get the threshold for detecting the X coordinate (0-100). Default is 60%.
			@return Return the x-range for face detection
		'''
		return self.readHoldingReg(self.REG_GFD_FACE_THRESHOLD)


	def set_gesture_detect_thres(self, score):
		'''
			@brief Set the gesture detection threshold
			@n Sets the threshold for gesture detection (0-100). Default is 60%.
			@param score Threshold score
		'''
		if (0 >= score) or (score > 100):
				return False
		return self.writeHoldingReg(self.REG_GFD_GESTURE_SCORE_THRESHOLD, score)


	def get_gesture_detect_thres(self):
		'''
			@brief Get the gesture detection threshold
			@n Get the threshold for gesture detection (0-100). Default is 60%.
			@return Return the threshold for gesture detection
		'''
		return self.readHoldingReg(self.REG_GFD_GESTURE_SCORE_THRESHOLD)


	def set_addr(self, addr):
		'''
			@brief Set the device address
			@param addr Address to set
		'''
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
		'''
			@fn write_reg
			@brief Write data to a register
			@param reg 16-bit register address
			@param data 8-bit register value
		'''
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
		'''
			@fn read_reg
			@brief Read data from a register
			@param reg 16-bit register address
			@param length Length of data to read
			@return Data read from the register
		'''
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

class DFRobot_GestureFaceDetection_UART(DFRobot_GestureFaceDetection, DFRobot_RTU): 
	def __init__(self, baud, addr):
		# Initialize UART baud rate and address
		self.__baud = baud
		self.__addr = addr
		DFRobot_GestureFaceDetection.__init__(self)
		DFRobot_RTU.__init__(self, baud, 8, 'N', 1)

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



'''
  @file config_gesture.py
  @brief Config gestures
  @details  This code configure the location, score of faces, and gestures along with their scores.
  @copyright   Copyright (c) 2025 DFRobot Co.Ltd (http://www.dfrobot.com)
  @license     The MIT license (MIT)
  @author [thdyyl](yuanlong.yu@dfrobot.com)
  @version  V1.0
  @date  2025-03-31
  @https://github.com/DFRobot/DFRobot_GestureFaceDetection
'''




def setup():
	"""
	@brief Setup function for initializing sensor thresholds.
	
	This function sets the thresholds for face detection and gesture detection.
	"""
	# Wait for the sensor to start.
	time.sleep(5)

	while gfd.begin() == False:
		print("Communication with device failed, please check connection")
		time.sleep(1)

	# Set face detection score threshold (0~100)
	if gfd.set_face_detect_thres(60):
		print("Face detection threshold set to 60.")
	else:
		print("Set the face detection threshold fail.")
	# Set gesture detection score threshold (0~100)
	if gfd.set_gesture_detect_thres(60):
		print("Gesture detection threshold set to 60.")
	else:
		print("Set the gesture detection threshold fail.")
	# Set detection range, 0~100
	if gfd.set_detect_thres(100):
		print("Detection range set to maximum.")
	else:
		print("Set the gesture detection range fail.")


# Retrieve and print PID
	pid = gfd.read_pid()
	print("PID: {}".format(pid))
	vid = gfd.read_vid()
	print("VID: {}".format(vid))

def loop():
	"""
	@brief Main loop function for continuous detection.
	
	This function continuously checks for faces and gestures, and prints their details.
	"""
	nTotext= {0:"none", 1:"LIKE-blue",2:"OK-green",3:"STOP-red",4:"YES-yellow",5:"SIX-purple"}
	while True:
		# Check if any faces are detected
		if gfd.get_face_number() > 0:
			# Get face score and position coordinates
			face_score = gfd.get_face_score()
			face_x = gfd.get_face_location_x()
			face_y = gfd.get_face_location_y()

			gesture_type = gfd.get_gesture_type()
			gesture_score = gfd.get_gesture_score()

			print("Detect face at (x = {}, y = {}, score = {} ; gesture {}={}, score = {}".format(face_x, face_y, face_score, gesture_type, nTotext.get(gesture_type,"-"), gesture_score))
	
		# Delay for 500 milliseconds
		time.sleep(0.5)


# Macro definition: Set to True to use I2C, False to use UART
USE_I2C = False  # Set to True to use I2C, False to use UART

# Define device address and baud rate
DEVICE_ID = 0x72
UART_BAUD_RATE = 9600

# Choose between I2C or UART based on the macro definition
if USE_I2C:
	# Using I2C interface
	gfd = DFRobot_GestureFaceDetection_I2C(bus=1, addr=DEVICE_ID)  # Assuming I2C bus 1 is used
else:
	# Using UART interface
	gfd = DFRobot_GestureFaceDetection_UART(baud=UART_BAUD_RATE, addr=DEVICE_ID)



# Execute setup function
setup()


loop()
