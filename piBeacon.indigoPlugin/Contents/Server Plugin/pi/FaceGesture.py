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

sys.path.append("../")
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

GLOB_resetFile						= G.homeDir+"temp/FaceGesture.reset"
GLOB_restartFile					= G.homeDir+"temp/FaceGesture.restart"
GLOB_commandFile					= G.homeDir+"temp/FaceGesture.cmd"
GLOB_expectResponseAfter			= 10 # seconds
GLOB_maxRestartConnections			= 5  # count


# Define device address and baud rate
GLOB_DEVICE_ID = 0x72
GLOB_RT_BAUD_RATE = 9600
GLOB_SERIAL_PORTNAME= "serial0"




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



# ===========================================================================
# read params
# ===========================================================================

###############################
def readParams():
	global sensors, logDir, sensor,	 displayEnable
	global SENSOR, sensorOld
	global oldRaw, lastRead
	global startTime, lastMeasurement, oldi2cOrUart, oldserialPortName

	global commandList
	global i2cOrUart, serialPortName
	global gpioCmdForAction, gpioNumberForCmdAction, gpioInverseAction, gpioOnTimeAction, anyCmdDefined, unixCmdAction, unixCmdVoiceNo
	global badSensor
	global logLevel
	global GPIOZERO
	global reactOnlyToCommands
	global gpioUsed

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

			if devId not in badSensor: 					badSensor[devId] 					= 0
			if devId not in serialPortName: 			serialPortName[devId] 				= "serial0"
			if devId not in reactOnlyToCommands: 		reactOnlyToCommands[devId] 			= [x for x in range(6)]
			
			for ii in range(1,6):
				unixCmdAction[ii] =  sensors[sensor][devId].get("unixCmdAction"+str(ii),"")
				try: 	unixCmdVoiceNo[ii] = int(sensors[sensor][devId].get("unixCmdVoiceNo"+str(ii),"-1"))
				except: unixCmdVoiceNo[ii] = -1
				if unixCmdAction[ii] != "": anyCmdDefined = True

			U.logger.log(20, "unixCmdVoiceNo:{}; unixCmdAction:{} ".format(unixCmdVoiceNo, unixCmdAction) )
			
			commandList[devId] = {}
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
				if str(logLevel) != sensors[sensor][devId].get("logLevel","0"): upd = True
				logLevel = int(sensors[sensor][devId].get("logLevel","1"))
			else:
				logLevel = 0

			restart = ""
			i2cOrUart[devId] =  sensors[sensor][devId].get("i2cOrUart","")	
			if devId not in oldi2cOrUart or (i2cOrUart[devId] != "" and oldi2cOrUart[devId] != i2cOrUart[devId]):	restart = True
			i2cOrUart[devId]  = copy.copy(i2cOrUart[devId])


			if i2cOrUart[devId] == "uart":

				serialPortName[devId] =  sensors[sensor][devId].get("serialPortName", GLOB_SERIAL_PORTNAME)	
				if devId not in oldserialPortName or (serialPortName[devId] != "" and oldserialPortName[devId]  != serialPortName[devId]) :
					restart = "portname changed"
				oldserialPortName[devId]  = copy.copy(serialPortName[devId])
				time.sleep(4)

			upd = ""
			if devId not in SENSOR or restart:
				upd = "devId not present"
				startSensor(devId)
				if devId not in SENSOR:
					return

			if devId not in sensorOld: 
				upd = "devId not in old present"


			setGPIOconfig(devIdSelect=devId)


			if upd and logLevel > 0: U.logger.log(20,"devId:{}; reason:{}, serialPortName:{},  logLevel:{}".format(devId, upd, serialPortName[devId], logLevel) )


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
	global sensors, sensor
	global lastRestart
	global SENSOR
	global i2cOrUart, sleepAfterWrite, serialPortName
	global logLevel, commandList
	global counter

	startTime =time.time()

	if devId in SENSOR:
		del SENSOR[devId]


	if devId not in SENSOR:
		try:
			if i2cOrUart[devId] == "uart":
				if logLevel > 0: U.logger.log(20, "devId:{}; started sensor,  serial port:{}".format(devId, serialPortName[devId]))
				if cmdCheckSerialPort(devId):
					SENSOR[devId] = DFRobot_GestureFaceDetection_UART(baud=GLOB_RT_BAUD_RATE, addr=GLOB_DEVICE_ID)
				else:
					time.sleep(20)
			else:
				if logLevel > 0: U.logger.log(20, "devId:{}; started sensor,  i2cAddr:{}".format(devId, GLOB_DEVICE_ID))
				SENSOR[devId] =  DFRobot_GestureFaceDetection_I2C(bus=1, addr=GLOB_DEVICE_ID) 

			if devId in SENSOR:
				lastRestart	= time.time()
				counter[devId] = 0
				# Wait for the sensor to start.
				time.sleep(5)
			
				while SENSOR[devId].begin() == False:
					if logLevel > 0: U.logger.log(20, "Communication with device failed, please check connection")
					time.sleep(1)
			
				# Set face detection score threshold (0~100)
				if SENSOR[devId].set_face_detect_thres(80):
					if logLevel > 0: U.logger.log(20, "Face detection threshold set to 60.")
				else:
					if logLevel > 0: U.logger.log(20, "Set the face detection threshold fail.")
				# Set gesture detection score threshold (0~100)
				if SENSOR[devId].set_gesture_detect_thres(20):
					if logLevel > 0: U.logger.log(20, "Gesture detection threshold set to 60.")
				else:
					if logLevel > 0: U.logger.log(20, "Set the gesture detection threshold fail.")
				# Set detection range, 0~100
				if SENSOR[devId].set_detect_thres(100):
					if logLevel > 0: U.logger.log(20, "Detection range set to maximum.")
				else:
					if logLevel > 0: U.logger.log(20, "Set the gesture detection range fail.")
			
			
			# Retrieve and print PID
				pid = SENSOR[devId].read_pid()
				if logLevel > 0: U.logger.log(20, "PID: {}".format(pid))
				vid = SENSOR[devId].read_vid()
				if logLevel > 0: U.logger.log(20, "VID: {}".format(vid))

		except Exception as e:
			U.logger.log(20, "in Line {} has error={}".format(sys.exc_info()[-1].tb_lineno, e))
			if str(e).find("could not open port /dev/") > -1:
				data = {"sensors":{sensor:{devId:"badsenor_error:bad_port_setting_/dev/"+serialPortName[devId]}}}
				U.sendURL(data)
			del SENSOR[devId]
			
		return




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
def getValues(devId, wait=0):
	global sensor, sensors,	 SENSOR, badSensor, tmpMuteOff, learningOn
	global keepAwake
	global commandList, lastValidCmd, lastkeepAwake
	global i2cOrUart
	global cmdQueue, anyCmdDefined
	global logLevel, firstCmdReceived, lastCMDID
	global reactOnlyToCommands, lastCMDID, ignoreUntilEndOfLearning
	global cmdToText

	try:
		CMDID = 0
		CMDIDText = ""
		cmdScore = 0
		facesScore = 0
		facesX = 0
		facesY = 0
		if wait >0: time.sleep(wait)

		if devId not in SENSOR:
			badSensor[devId] += 1
			return "badSensor"

		for ii in range(20):
			time.sleep(0.5)
			try:
				faces = SENSOR[devId].get_face_number()
				if faces == 0: continue
			except Exception as e:
				if logLevel > 0: U.logger.log(20, "devID:{}; error in received CMDID: {:3d}, badSensorCount:{}, error:{}".format(devId, CMDID, badSensor[devId], e)  )
				badSensor[devId] += 1
				if badSensor[devId] >= 5: return "badSensor"
				return {"cmd":0}

			facesScore = SENSOR[devId].get_face_score()
			facesX	= SENSOR[devId].get_face_location_x()
			facesY = SENSOR[devId].get_face_location_y()


			if logLevel > 1: U.logger.log(20, f' faces:{faces:}, faceScore:{facesScore:}, facesX:{facesX:}, facesY:{facesY:}' )
			for ii in range(3):
				CMDID = int(SENSOR[devId].get_gesture_type())
				cmdScore = SENSOR[devId].get_gesture_score()
				if logLevel > 1: U.logger.log(20, f'        counter:{counter[devId]:}, cmd:{CMDID:}, cmdScore:{cmdScore:}, cmdText:{cmdToText.get(CMDID,""):}' )
				if CMDID > 0: break
				time.sleep(0.1)
			if CMDID > 0: break 
		
		if badSensor[devId] > 1:
			U.logger.log(20, "devID:{}; reset bad sensor count after {:} bad sensor readings".format(devId, badSensor[devId])  )

		if CMDID != 0:
			lastValidCmd = time.time()
			if anyCmdDefined: cmdQueue.put(CMDID)
			counter[devId] +=1

		badSensor[devId] = 0
		if logLevel > 0: U.logger.log(20, f'== counter:{counter[devId]:}, cmd:{CMDID:}, cmdScore:{cmdScore:}, cmdText:{cmdToText.get(CMDID,""):}, faces:{faces:}, faceScore:{facesScore:}, facesX:{facesX:}, facesY:{facesY:}' )
		return {"counter":counter[devId], "cmd":CMDID, "cmdScore":cmdScore, "cmdText":cmdToText.get(CMDID,""), "faces":faces, "faceScore ":facesScore, "facesX":facesX, "facesY":facesY }


	except Exception as e:
		U.logger.log(20, "in Line {} has error={}".format(sys.exc_info()[-1].tb_lineno, e))

	badSensor[devId] += 1
	if badSensor[devId] >= 5: return "badSensor"
	return ""




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
	global unixCmdAction, unixCmdVoiceNo

	try:
		time.sleep(1)
		if logLevel > 0: U.logger.log(20, "start  refresh GPIO loop")
		ledOn = [0,0,0,0,0,0,0,0]
		anyOn = False
			
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
					pass
					
			except Exception as e:
				U.logger.log(20, "in Line {} has error={}".format(sys.exc_info()[-1].tb_lineno, e))
				time.sleep(10)

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
	global startTime, lastMeasurement, lastRestart
	global oldi2cOrUart, i2cOrUart, oldserialPortName, sensorOld, serialPortName
	global gpioCmdForAction, gpioNumberForCmdAction, gpioInverseAction, gpioOnTimeAction
	global commandList, lastValidCmd
	global anyCmdDefined
	global cmdQueue, logLevel
	global threadCMD
	global firstCmdReceived
	global GPIOZERO
	global reactOnlyToCommands
	global gpioUsed 
	global unixCmdVoiceNo, unixCmdAction
	global lastCMDID
	global cmdToText
	global counter
	
	cmdToText						= {0:"none", 1:"LIKE-blue",2:"OK-green",3:"STOP-red",4:"YES-yellow",5:"SIX-purple"}

	
	counter							= {}
	lastCMDID						= -1
	gpioUsed 						= [0,0,0,0,0,0,0,0,0,0]
	reactOnlyToCommands				= {}
	GPIOZERO						= {}
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
							data["sensors"][sensor][devId] = {"cmd":900}
							break

						extraSleep = 2

					elif theValues.get("faces",0) != 0:
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
				readParams()
				lastRead = time.time()

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


