#!/usr/bin/env python3
# vim: set encoding=utf-8 tabstop=4 softtabstop=4 shiftwidth=4 expandtab
#########################################################################
#  Copyright 2017- Serge Wagener					 serge@wagener.family
#########################################################################
#  This software is free software: you can redistribute it and/or modify
#  it under the terms of the GNU General Public License as published by
#  the Free Software Foundation, either version 3 of the License, or
#  (at your option) any later version.
#
#  Thi software is distributed in the hope that it will be useful,
#  but WITHOUT ANY WARRANTY; without even the implied warranty of
#  MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#  GNU General Public License for more details.
#
#  You should have received a copy of the GNU General Public License
#  along with this software  If not, see <http://www.gnu.org/licenses/>.
#########################################################################

# pip3 install pyserial

import binascii
import logging
import serial
import threading
import sys


class RD200M:

	cmd_RESULT_QUERY 	= 0x01	# Request all data
	cmd_RESET 			= 0xA0	# RD200M reset
	cmd_SET_PERIOD 		= 0xA1	# Set data transfer period
	cmd_RESULT_RETURN 	= 0x10	# Read all data (receive only)
	cmd_test		 	= 0x02	# Read all data (receive only)

	status = {0x00: 'Measurement between power on and 200s',
			  0x01: 'Measurement between 200s and 1h',
			  0x10: 'WARNING: Measurement within 30m and count > 10',
			  0x02: 'Measurement after 1h',
			  0xE0: 'Detected vibrations, measurement maybe unreliable'}

	def __init__(self, port='/dev/ttyAMA0', baudrate=19200, period=10):
		"""
		Creates an instance of the RD200M class.

		:param port: Serial port to use. Defaults to the Raspberry Pi onboard UART
		:type port: string
		:param baudrate: Baudrate (bit/s) for serial port communication. Defaults to 19200 for RD200M
		:type baudrate: int
		:param period: Time interval in minutes for the RD200M to send measurements automatically
		:type period: int
		"""
		self.logger 		= logging.getLogger(__name__)
		self.port 			= port
		self.baudrate 		= baudrate
		self.period 		= period
		self.__timeout 		= None
		self.__serial 		= serial.Serial()
		self.__receive_thread = None

	def open(self):
		"""
		Opens the serial port specified in the constructor.

		:return: Returns true on succes or false if unable to open serial port
		:rtype: bool
		"""
		self.__serial.baudrate 	= self.baudrate
		self.__serial.port 		= self.port
		self.__serial.open()
		if self.__serial.isOpen:
			self.logger.info("Serial port '{}' opened with {} bit/s".format(self.port, self.baudrate))
		else:
			self.logger.critical("Unable to open port '{}'".format(self.port))
			return False
		#self.__serial.flushInput()
		return True

	def reset(self, period=None):
		"""
		Reset the RD200M by setting the desired measurement send period and a reset command

		:param period: Time interval in minutes for the RD200M to send measurements automatically
		:type period: int
		"""
		self.__serial.baudrate = self.baudrate
		if period:
			self.period = period
		self.logger.info("Resetting RD200M and setting measurement period to {} minutes".format(self.period))
		self._send_cmd(self.cmd_SET_PERIOD, self.period)
		time.sleep(1)
		self._send_cmd(self.cmd_RESET)
		time.sleep(1)

	def test(self, period=None):
		"""
		"""
		self._send_cmd(self.cmd_test)

	def force_read(self):
		""" Force the RD200M to send the actual values """
		self._send_cmd(self.cmd_RESULT_QUERY)

	def close(self):
		"""
		Closes the serial port and cancels reading in progress.

		:return: Returns always true for now
		:rtype: bool
		"""
		if self.__serial.isOpen:
			self.__serial.close()
			self.logger.debug("Serial port '{}' closed".format(self.port))
		else:
			self.logger.debug("Cannot close serial port '{}' because it is not open".format(self.port))
		return True

	def _send_cmd(self, cmd, data=None):
		"""
		Sends a command to the RD200M with optional parameters

		:param cmd: Command to send. See cmd_* constants in this class.
		:type cmd: int
		:param data: Optional data to send with the command (such as period time)
		:type data: int

		:return: Returns true if command has been sucessfully bufered for sending or false on any error
		:rtype: bool
		"""
		cmdarray = bytearray([0x02, cmd])
		if data:
			if isinstance(data, int):
				size = (data.bit_length() + 7) // 8
				checksum = 0xFF - (cmd + size + data)
				cmdarray.extend([size, data, checksum])
			else:
				self.logger.warning("Data must be of type integer, ignoring '{}'".format(data))
				return False
		else:
			size = 0
			checksum = 0xFF - (cmd + size)
			cmdarray.extend([size, checksum])
		self.logger.debug("Sending command '{}'".format(binascii.hexlify(cmdarray).decode()))
		self.__serial.write(cmdarray)
		return True

	def _process_measurement_data(self, data):
		"""
		Processes an incoming (already checksum tested) data packet and prints

		:param data: 4 bytes data received from RD200M.
		:type data: bytes

		:return: Returns always true for now
		:rtype: bool
		"""
		if len(data) != 4:
			self.logger.warning("Received data '{}' has not exactly 4 bytes, cannot decode measurement".format(binascii.hexlify(data).decode()))
			return False
		status = data[0]
		minutes = data[1]
		integer = data[2]
		decimal = data[3]
		radon = float(str(integer) + "." + str(decimal)) * 37  # * 37 converts pCi/L to bq/m3
		self.logger.info("Radon is {} bq/m3, {}".format(radon, self.status[status]))
		return True

	def getData(self):
		try:
				nData = self.__serial.inWaiting()
				self.logger.debug("ndata: {}".format(nData))
				if nData >0:
					response = self.__serial.read(size=nData)
					#print " response ", response, nData
					if len(response) == 8:
						self.logger.debug("Received '{}'".format(binascii.hexlify(response).decode()))
						cmd = response[1]
						size = int(response[2])
						data = response[3:3 + size]
						checksum = int.from_bytes(response[-1:], byteorder='big')
						data_sum = 0
						for ch in data:
							data_sum += ch
						calculated_checksum = 0xFF - (cmd + size + data_sum)
						if checksum == calculated_checksum:
							if cmd == self.cmd_RESULT_RETURN:
								self._process_measurement_data(data)
							else:
								self.logger.warning("Received unknown command '{'}".format(cmd))
						else:
							self.logger.warning("Checksum error, ignoring received data '{}'".format(binascii.hexlify(response).decode()))
					else:
						self.logger.debug("Received '{}'".format(binascii.hexlify(response).decode()))
		except	Exception, e :
				self.logger.debug("", exc_info=True)



#!/usr/bin/env python3
# vim: set encoding=utf-8 tabstop=4 softtabstop=4 shiftwidth=4 expandtab
#########################################################################
#  Copyright 2017- Serge Wagener					 serge@wagener.family
#########################################################################
#  This software is free software: you can redistribute it and/or modify
#  it under the terms of the GNU General Public License as published by
#  the Free Software Foundation, either version 3 of the License, or
#  (at your option) any later version.
#
#  Thi software is distributed in the hope that it will be useful,
#  but WITHOUT ANY WARRANTY; without even the implied warranty of
#  MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#  GNU General Public License for more details.
#
#  You should have received a copy of the GNU General Public License
#  along with this software  If not, see <http://www.gnu.org/licenses/>.
#########################################################################

# pip3 install paho-mqtt pyserial

"""
This software runs on a Raspberry Pi (old v1 is ok). It connects to the FTLABS RD200M Radon sensor
via serial port and to  print 
"""

import logging
import time




logging.basicConfig(level=logging.DEBUG, format='%(asctime)s %(levelname)-8s %(module)-15s %(threadName)-20s %(message)s -- %(filename)s:%(funcName)s:%(lineno)d', datefmt='%Y-%m-%d %H:%M:%S')
logger = logging.getLogger(__name__)
logger.debug("Starting RADON measurement")


rd200m = RD200M()
rd200m.open()
rd200m.reset()

time.sleep(1)
#rd200m.reset()
#time.sleep(0.5)
rd200m.force_read()
time.sleep(1)
rd200m.getData()

time.sleep(1)

rd200m.force_read()
time.sleep(1)
rd200m.getData()

rd200m.test()
time.sleep(1)
rd200m.getData()



time.sleep(2)
rd200m.getData()
()
exit()

