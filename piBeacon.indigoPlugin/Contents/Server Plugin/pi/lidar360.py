#!/usr/bin/python
# -*- coding: utf-8 -*-
# by Karl Wachs
# 2018-01-10
# version 0.9 
##
##
#! /usr/bin/env python
# -*- coding: utf-8 -*-
####################

import sys, os, time, json, datetime,subprocess,copy
import math
import copy
import logging
import threading


sys.path.append(os.getcwd())
import	piBeaconUtils	as U
import	piBeaconGlobals as G
G.program = "lidar360"

'''Simple and lightweight module for working with Lidar rangefinder scanners.

Usage example:

>>> from Lidar import Lidar
>>> lidar = Lidar('/dev/ttyUSB0')
>>> 
>>> info = lidar.get_info()
>>> print(info)
>>> 
>>> health = lidar.get_health()
>>> print(health)
>>> 
>>> for i, scan in enumerate(lidar.iter_scans()):
...  print('%d: Got %d measurments' % (i, len(scan)))
...  if i > 10:
...   break
...
>>> 0
>>> lidar.stop_motor()
>>> lidar.disconnect()

For additional information please refer to the Lidar class documentation.
'''
import codecs
import serial
import struct

SYNC_BYTE = b'\xA5'
SYNC_BYTE2 = b'\x5A'

GET_INFO_BYTE = b'\x50'
GET_HEALTH_BYTE = b'\x52'

STOP_BYTE = b'\x25'
RESET_BYTE = b'\x40'

SCAN_BYTE = b'\x20'
FORCE_SCAN_BYTE = b'\x21'

DESCRIPTOR_LEN = 7
INFO_LEN = 20
HEALTH_LEN = 3

INFO_TYPE = 4
HEALTH_TYPE = 6
SCAN_TYPE = 129

#Constants & Command to start A2 motor
MAX_MOTOR_PWM = 1023
DEFAULT_MOTOR_PWM = 0.3
SET_PWM_BYTE = b'\xF0'

_HEALTH_STATUSES = {
	0: 'Good',
	1: 'Warning',
	2: 'Error',
}



def _b2i(byte):
	'''Converts byte to integer (for Python 2 compatability)'''
	return byte if int(sys.version[0]) == 3 else ord(byte)

class LidarException(Exception):
	'''Basic exception class for Lidar'''



class Lidar(object):
	'''Class for communicating with Lidar rangefinder scanners'''

	_serial_port = None  #: serial port connection
	port = ''  #: Serial port name, e.g. /dev/ttyUSB0
	timeout = 1  #: Serial port timeout
	motor = False  #: Is motor running?
	baudrate = 115200  #: Baudrate for serial port

	def __init__(self, port, baudrate=115200, timeout=1, logger=None, mSpeed=DEFAULT_MOTOR_PWM):
		try:
			'''Initilize Lidar object for communicating with the sensor.

			Parameters
			----------
			port : str
				Serial port name to which sensor is connected
			baudrate : int, optional
				Baudrate for serial connection (the default is 115200)
			timeout : float, optional
				Serial port connection timeout in seconds (the default is 1)
			logger : logging.Logger instance, optional
				Logger instance, if none is provided new instance is created
			'''
			self._motorSpeed = mSpeed
			self._serial_port = None
			self.port = port
			self.baudrate = baudrate
			self.timeout = timeout
			self.motor_running = None
			if logger is None:
				logger = logging.getLogger('Lidar')
			self.connect()
			self.start_motor()
		except	Exception, e:
			U.logger.log(30, u"in Line {} has error={}  -{}".format(sys.exc_traceback.tb_lineno, e, self.port) )


	def _process_scan(self, raw):
		try:
			'''Processes input raw data and returns measurment data'''
			new_scan = bool(_b2i(raw[0]) & 0b1)
			inversed_new_scan = bool((_b2i(raw[0]) >> 1) & 0b1)
			quality = _b2i(raw[0]) >> 2
			if new_scan == inversed_new_scan:
				raise LidarException('{}-New scan flags mismatch'.format(self.port))
			check_bit = _b2i(raw[1]) & 0b1
			if check_bit != 1:
				raise LidarException('{}-Check bit not equal to 1'.format(self.port))
			angle = ((_b2i(raw[1]) >> 1) + (_b2i(raw[2]) << 7)) / 64.
			distance = (_b2i(raw[3]) + (_b2i(raw[4]) << 8)) / 4.
			return new_scan, quality, angle, distance
		except	Exception, e:
				U.logger.log(30, u"in Line {} has error={}".format(sys.exc_traceback.tb_lineno, e))



	def connect(self):
		try:
			'''Connects to the serial port with the name `self.port`. If it was
			connected to another serial port disconnects from it first.'''
			if self._serial_port is not None:
				self.disconnect()
			try:
				self._serial_port = serial.Serial(
					self.port, self.baudrate,
					parity=serial.PARITY_NONE, stopbits=serial.STOPBITS_ONE,
					timeout=self.timeout, dsrdtr=True)
			except serial.SerialException as err:
				raise LidarException('{}-Failed to connect to the sensor due to: {}'.format(self.port, err) )
		except	Exception, e:
			U.logger.log(30, u"in Line {} has error={}".format(sys.exc_traceback.tb_lineno, e))

	def disconnect(self):
		try:
			'''Disconnects from the serial port'''
			if self._serial_port is None:
				return
			self._serial_port.close()
		except	Exception, e:
			U.logger.log(30, u"in Line {} has error={}".format(sys.exc_traceback.tb_lineno, e))

	def set_pwm(self, pwm):
		try:
			assert(0 <= pwm <=1)
			payload = struct.pack("<H", int(pwm * MAX_MOTOR_PWM))
			self._send_payload_cmd(SET_PWM_BYTE, payload)
		except	Exception, e:
			U.logger.log(30, u"in Line {} has error={}".format(sys.exc_traceback.tb_lineno, e))

	def start_motor(self):
		try:
			'''Starts sensor motor'''
			U.logger.log(10,'{}-Starting motor'.format(self.port))
			# For A1
			self._serial_port.dtr = False

			# For A2
			self.set_pwm(self._motorSpeed)
			self.motor_running = True
			U.logger.log(20,'{}-Starting motor .. done'.format(self.port))
		except	Exception, e:
			U.logger.log(30, u"in Line {} has error={}  -{}".format(sys.exc_traceback.tb_lineno, e, self.port) )

	def stop_motor(self):
		try:
			'''Stops sensor motor'''
			U.logger.log(20,'{}-Stoping motor'.format(self.port))
			# For A2
			self.set_pwm(0)
			time.sleep(.001)
			# For A1
			self._serial_port.dtr = True
			self.motor_running = False
		except	Exception, e:
			U.logger.log(30, u"in Line {} has error={}  -{}".format(sys.exc_traceback.tb_lineno, e, self.port) )

	def _send_payload_cmd(self, cmd, payload):
		try:
			'''Sends `cmd` command with `payload` to the sensor'''
			U.logger.log(10,'{}-sending cmd:{} payload:{}'.format(self.port,cmd,payload ) )
			size = struct.pack('B', len(payload))
			req = SYNC_BYTE + cmd + size + payload
			checksum = 0
			for v in struct.unpack('B'*len(req), req):
				checksum ^= v
			req += struct.pack('B', checksum)
			self._serial_port.write(req)
			U.logger.log(10,'{}Command sent: {}'.format(self.port,req))
		except	Exception, e:
			U.logger.log(30, u"in Line {} has error={}  -{}".format(sys.exc_traceback.tb_lineno, e, self.port) )

	def _send_cmd(self, cmd):
		try:
			'''Sends `cmd` command to the sensor'''
			req = SYNC_BYTE + cmd
			self._serial_port.write(req)
			U.logger.log(10,'{}-Command sent: {}'.format(self.port,req) )
		except	Exception, e:
			U.logger.log(30, u"in Line {} has error={}  -{}".format(sys.exc_traceback.tb_lineno, e, self.port) )

	def _read_descriptor(self):
		try:
			'''Reads descriptor packet'''
			descriptor = self._serial_port.read(DESCRIPTOR_LEN)
			U.logger.log(10,'{}-Recieved descriptor: {}'.format(self.port,descriptor) )
			if len(descriptor) != DESCRIPTOR_LEN:
				raise LidarException(' Descriptor length mismatch')
			elif not descriptor.startswith(SYNC_BYTE + SYNC_BYTE2):
				raise LidarException('{}-Incorrect descriptor starting bytes .. ok  first 2 calls '.format(self.port) )
			is_single = _b2i(descriptor[-2]) == 0
			return _b2i(descriptor[2]), is_single, _b2i(descriptor[-1])
		except	Exception, e:
			U.logger.log(30, u"in Line {} has error={}  -{}".format(sys.exc_traceback.tb_lineno, e, self.port) )
		return "","",""
	def _read_response(self, dsize):
		try:
			'''Reads response packet with length of `dsize` bytes'''
			U.logger.log(10,'{}-Trying to read response: {} bytes'.format(self.port, dsize) )
			data = self._serial_port.read(dsize)
			U.logger.log(10,'{}-Recieved data len{}'.format(self.port,len(data)) )
			if len(data) != dsize:
				raise LidarException('{}-Wrong body size'.format(self.port) )
			return data
		except	Exception, e:
			U.logger.log(30, u"in Line {} has error={}  -{}".format(sys.exc_traceback.tb_lineno, e, self.port) )

	def get_info(self):
		'''Get device information

		Returns
		-------
		dict
			Dictionary with the sensor information
		'''
		try:
			self._send_cmd(GET_INFO_BYTE)
			dsize, is_single, dtype = self._read_descriptor()
			if dsize != INFO_LEN:
				raise LidarException('{}-Wrong get_info reply length'.format(self.port) )
			if not is_single:
				raise LidarException('{}-Not a single response mode'.format(self.port) )
			if dtype != INFO_TYPE:
				raise LidarException('{}-Wrong response data type'.format(self.port) )
			raw = self._read_response(dsize)
			serialnumber = codecs.encode(raw[4:], 'hex').upper()
			serialnumber = codecs.decode(serialnumber, 'ascii')
			data = {
				'model': _b2i(raw[0]),
				'firmware': (_b2i(raw[2]), _b2i(raw[1])),
				'hardware': _b2i(raw[3]),
				'serialnumber': serialnumber,
			}
			return data
		except	Exception, e:
			U.logger.log(30, u"in Line {} has error={}  -{}".format(sys.exc_traceback.tb_lineno, e, self.port) )

	def get_health(self):
		try:
			'''Get device health state. When the core system detects some
			potential risk that may cause hardware failure in the future,
			the returned status value will be 'Warning'. But sensor can still work
			as normal. When sensor is in the Protection Stop state, the returned
			status value will be 'Error'. In case of warning or error statuses
			non-zero error code will be returned.

			Returns
			-------
			status : str
				'Good', 'Warning' or 'Error' statuses
			error_code : int
				The related error code that caused a warning/error.
			'''
			self._send_cmd(GET_HEALTH_BYTE)
			dsize, is_single, dtype = self._read_descriptor()
			if dsize != HEALTH_LEN:
				raise LidarException('{}-Wrong get_info reply length'.format(self.port) )
			if not is_single:
				raise LidarException('{}-Not a single response mode'.format(self.port) )
			if dtype != HEALTH_TYPE:
				raise LidarException('{}-Wrong response data type'.format(self.port) )
			raw = self._read_response(dsize)
			status = _HEALTH_STATUSES[_b2i(raw[0])]
			error_code = (_b2i(raw[1]) << 8) + _b2i(raw[2])
			return status, error_code
		except	Exception, e:
			U.logger.log(30, u"in Line {} has error={}".format(sys.exc_traceback.tb_lineno, e))

	def clear_input(self):
		try:
			'''Clears input buffer by reading all available data'''
			self._serial_port.read_all()
		except	Exception, e:
			U.logger.log(30, u"in Line {} has error={}".format(sys.exc_traceback.tb_lineno, e))

	def stop(self):
		try:
			'''Stops scanning process, disables laser diode and the measurment
			system, moves sensor to the idle state.'''
			U.logger.log(20,'{}-Stoping scanning'.format(self.port))
			self._send_cmd(STOP_BYTE)
			time.sleep(.001)
			self.clear_input()
		except	Exception, e:
			U.logger.log(30, u"in Line {} has error={}".format(sys.exc_traceback.tb_lineno, e))

	def reset(self):
		try:
			'''Resets sensor core, reverting it to a similar state as it has
			just been powered up.'''
			U.logger.log(20,'{}-Reseting the sensor'.format(self.port))
			self._send_cmd(RESET_BYTE)
			time.sleep(.002)
		except	Exception, e:
			U.logger.log(30, u"in Line {} has error={}".format(sys.exc_traceback.tb_lineno, e))

	def iter_measurments(self, max_buf_meas=500):
		try:
			'''Iterate over measurments. Note that consumer must be fast enough,
			otherwise data will be accumulated inside buffer and consumer will get
			data with increaing lag.

			Parameters
			----------
			max_buf_meas : int
				Maximum number of measurments to be stored inside the buffer. Once
				numbe exceeds this limit buffer will be emptied out.

			Yields
			------
			new_scan : bool
				True if measurment belongs to a new scan
			quality : int
				Reflected laser pulse strength
			angle : float
				The measurment heading angle in degree unit [0, 360)
			distance : float
				Measured object distance related to the sensor's rotation center.
				In millimeter unit. Set to 0 when measurment is invalid.
			'''
			self.start_motor()
			status, error_code = self.get_health()
			U.logger.log(20,'{}-Health status: {} [{}]'.format(self.port, status, error_code) )
			if status == _HEALTH_STATUSES[2]:
				U.logger.log(20,'{}-Trying to reset sensor due to the error. Error code: {}'.format(self.port, error_code) )
				self.reset()
				status, error_code = self.get_health()
				if status == _HEALTH_STATUSES[2]:
					raise LidarException('{}-Lidar hardware failure. Error code: {}'.format(self.port, error_code) )
			elif status == _HEALTH_STATUSES[1]:
				U.logger.log(20,'{}-Warning sensor status detected! Error code:{}'.format(self.port, error_code) )
			cmd = SCAN_BYTE
			self._send_cmd(cmd)
			dsize, is_single, dtype = self._read_descriptor()
			if dsize != 5:
				raise LidarException('{}-Wrong get_info reply length'.format(self.port) )
			if is_single:
				raise LidarException('{}-Not a multiple response mode'.format(self.port) )
			if dtype != SCAN_TYPE:
				raise LidarException('{}-Wrong response data type'.format(self.port) )
			while True:
				raw = self._read_response(dsize)
				U.logger.log(10,'{}-Recieved scan response: {}'.format(self.port, raw) )
				if max_buf_meas:
					data_in_buf = self._serial_port.in_waiting
					if data_in_buf > max_buf_meas*dsize:
						U.logger.log(20, 'Too many measurments in the input buffer: {}  {} Clearing buffer... --{}'.format(data_in_buf//dsize, max_buf_meas, self.port) )
						self._serial_port.read(data_in_buf//dsize*dsize)
				yield self._process_scan(raw)
		except	Exception, e:
			U.logger.log(30, u"in Line {} has error={}".format(sys.exc_traceback.tb_lineno, e))
		return 

	def iter_scans(self, max_buf_meas=500, min_len=5):
		try:
			'''Iterate over scans. Note that consumer must be fast enough,
			otherwise data will be accumulated inside buffer and consumer will get
			data with increasing lag.

			Parameters
			----------
			max_buf_meas : int
				Maximum number of measurments to be stored inside the buffer. Once
				numbe exceeds this limit buffer will be emptied out.
			min_len : int
				Minimum number of measurments in the scan for it to be yelded.

			Yields
			------
			scan : list
				List of the measurments. Each measurment is tuple with following
				format: (quality, angle, distance). For values description please
				refer to `iter_measurments` method's documentation.
			'''
			scan = []
			iterator = self.iter_measurments(max_buf_meas)
			for new_scan, quality, angle, distance in iterator:
				if new_scan:
					if len(scan) > min_len:
						yield scan
					scan = []
				if quality > 0 and distance > 0:
					scan.append((quality, angle, distance))
		except	Exception, e:
			U.logger.log(30, u"in Line {} has error={}".format(sys.exc_traceback.tb_lineno, e))
		return 



# ===========================================================================
# read params
# ===========================================================================

#################################		 
def readParams():
	global sensorList, sensors, logDir, sensor,	 sensorRefreshSecs, displayEnable
	global rawOld
	global oldRaw, lastRead
	global startTime
	global motorFrequency, nContiguousAngles, contiguousDeltaValue, anglesInOneBin,triggerLast, triggerCalibrated, sendToIndigoEvery, lastAliveSend, minSendDelta, usbPortUsed, usbPort, sendPixelData, doNotUseDataRanges, doNotUseDataRangesString, minSignalStrength
	global sensorCLASS

	try:
		inp,inpRaw,lastRead2 = U.doRead(lastTimeStamp=lastRead)
		if inp == "": return
		if lastRead2 == lastRead: return
		lastRead   = lastRead2
		if inpRaw == oldRaw: return
		oldRaw	   = inpRaw
		
		externalSensor=False
		sensorList=[]
		sensorsOld= copy.copy(sensors)


		
		U.getGlobalParams(inp)
		  
		if "sensorList"			in inp:	 sensorList=			 (inp["sensorList"])
		if "sensors"			in inp:	 sensors =				 (inp["sensors"])
		
 
		if sensor not in sensors:
			U.logger.log(30, "{}-is not in parameters = not enabled, stopping {}.py".format(sensor, sensor) )
			exit()
			

		U.logger.log(20, "{}-reading new parameter file".format(sensor) )

		restart = False
		deldevID={}		   
		for devId in sensors[sensor]:

			
			if devId not in motorFrequency: 			motorFrequency[devId] 				= 0.3
			if devId not in nContiguousAngles: 			nContiguousAngles[devId] 			= 5
			if devId not in contiguousDeltaValue:		contiguousDeltaValue[devId]		 	= 5
			if devId not in anglesInOneBin:				anglesInOneBin[devId] 				= 2
			if devId not in triggerLast:				triggerLast[devId] 					= 4
			if devId not in triggerCalibrated:			triggerCalibrated[devId] 			= 5
			if devId not in sendToIndigoEvery:			sendToIndigoEvery[devId]			= 30
			if devId not in lastAliveSend:				lastAliveSend[devId]				= time.time()
			if devId not in measurementsNeededForCalib:	measurementsNeededForCalib[devId]	= -1
			if devId not in usbPort:					usbPort[devId]						= -1
			if devId not in sendPixelData:				sendPixelData[devId]				= True
			if devId not in doNotUseDataRanges:			doNotUseDataRanges[devId]			= []
			if devId not in minSignalStrength:			minSignalStrength[devId]			= []

			try:
				old = usbPort[devId]
				if "usbPort" in sensors[sensor][devId]: 
					usbPort[devId] = sensors[sensor][devId]["usbPort"]
			except: usbPort[devId] = "autoUSB"

			if old !=-1 and usbPort[devId] != old : 
				restart = True

			try:
				minSignalStrength[devId] = 14
				if "minSignalStrength" in sensors[sensor][devId]: 
					minSignalStrength[devId] = int(sensors[sensor][devId]["minSignalStrength"])
			except: minSignalStrength[devId] = 14


			try:
				sendPixelData[devId] = True
				if "sendPixelData" in sensors[sensor][devId]: 
					sendPixelData[devId] = sensors[sensor][devId]["sendPixelData"] =="1"
			except:	sendPixelData[devId] = True

			try:
				old = measurementsNeededForCalib[devId]
				if "measurementsNeededForCalib" in sensors[sensor][devId]: 
					measurementsNeededForCalib[devId] = int(sensors[sensor][devId]["measurementsNeededForCalib"])
			except:	measurementsNeededForCalib[devId] = 6
			if old !=-1 and old != measurementsNeededForCalib[devId]: 
				os.remove(G.homeDir+"lidar.calibrated"+usbPortUsed[devId]+"> /dev/null 2>&1 ")
				restart = True

			try:
				old = triggerLast[devId]
				if "triggerLast" in sensors[sensor][devId]: 
					triggerLast[devId] = float(sensors[sensor][devId]["triggerLast"])
			except:	triggerLast[devId] = 5
			if old != triggerLast[devId]: restart = True

			try:
				old = triggerCalibrated[devId]
				if "triggerCalibrated" in sensors[sensor][devId]: 
					triggerCalibrated[devId] = float(sensors[sensor][devId]["triggerCalibrated"])
			except:	triggerCalibrated[devId] = 5
			if old != triggerCalibrated[devId]: restart = True

			try:
				old = sendToIndigoEvery[devId]
				if "sendToIndigoEvery" in sensors[sensor][devId]: 
					sendToIndigoEvery[devId] = float(sensors[sensor][devId]["sendToIndigoEvery"])
			except:	sendToIndigoEvery[devId] = 5.
			if old != sendToIndigoEvery[devId]: restart = True

			try:
				old = minSendDelta[devId]
				if "minSendDelta" in sensors[sensor][devId]: 
					minSendDelta[devId] = float(sensors[sensor][devId]["minSendDelta"])
			except:	minSendDelta[devId] = 5.
			if old != minSendDelta[devId]: restart = True

			try:
				old = motorFrequency[devId]
				if "motorFrequency" in sensors[sensor][devId]: 
					motorFrequency[devId] = float(sensors[sensor][devId]["motorFrequency"])
			except:	motorFrequency[devId] = 0.3
			if old != motorFrequency[devId]: restart = True
				
			try:
				old = nContiguousAngles[devId]
				if "nContiguousAngles" in sensors[sensor][devId]: 
					nContiguousAngles[devId] = int(sensors[sensor][devId]["nContiguousAngles"])
			except:	nContiguousAngles[devId] = 4
			if old != nContiguousAngles[devId]: restart = True

			try:
				old = contiguousDeltaValue[devId]
				if "contiguousDeltaValue" in sensors[sensor][devId]: 
					contiguousDeltaValue[devId] = float(sensors[sensor][devId]["contiguousDeltaValue"])
			except:	contiguousDeltaValue[devId] = 5.
			if old != contiguousDeltaValue[devId]: restart = True

			try:
				old = anglesInOneBin[devId]
				if "anglesInOneBin" in sensors[sensor][devId]: 
					anglesInOneBin[devId] = int(sensors[sensor][devId]["anglesInOneBin"])
			except:	anglesInOneBin[devId] = 2
			if old != anglesInOneBin[devId]: restart = True

			try:
				if "doNotUseDataRanges" in sensors[sensor][devId]: 
					doNotUseDataRangesString[devId] =""
					doNotUseDataRanges[devId] = []
					if len(sensors[sensor][devId]["doNotUseDataRanges"]) > 2:
						doNotUseDataRangesString[devId] =sensors[sensor][devId]["doNotUseDataRanges"]
						ddd = doNotUseDataRangesString[devId].split(";")
						for dd in ddd: 
							if len(dd) > 2 and "-" in dd:
								d = dd.split("-")
								doNotUseDataRanges[devId].append([int(d[0]),int(d[1])])
			except:	doNotUseDataRanges[devId] = []
	
		
			if devId not in sensorCLASS  or restart:
				if  not startSensor(devId, restart = True)  or (devId in sensorCLASS and sensorCLASS[devId] == ""): 
					deldevID[devId] = True
					U.logger.log(30, u"{}-bad sensor start, stopping that sensor".format(usbPortUsed[devId]) )
				
		for devId in sensorCLASS:
			if devId not in sensors[sensor]:
				deldevID[devId]=1
		for dd in  deldevID:
			del sensorCLASS[dd]
		if len(sensorCLASS) ==0: 
			####exit()
			pass



	except	Exception, e:
		U.logger.log(30, u"in Line {} has error={}".format(sys.exc_traceback.tb_lineno, e))
		


#################################
def startSensor(devId, restart=False):
	global sensors, sensor
	global startTime
	global sensorCLASS
	global countMeasurements, calibratecalibrated, usbPortUsed, usbPort, motorFrequency
	global quick, getlidarThreads
	try:

		
		sensorCLASS[devId] = ""
		usbPortUsed[devId] = ""
		startTime = time.time()

		startOK = False
			
		if usbPort[devId] == "autoUSB":
			activUsbList = U.findActiveUSB()
		else:
			activUsbList = [usbPort[devId]]

		for usb in activUsbList: 
			usbPortUsed[devId] = usb
			if not U.checkIfusbSerialActive(usbPortUsed[devId]):
					U.logger.log(20, u"tried {}, is not active ".format(usbPortUsed[devId]))
					usbPortUsed[devId] =""
					continue
			for ii in range(3): # need to init several times in some circumstances 
				try:
					sensorCLASS[devId]  = Lidar('/dev/'+usbPortUsed[devId], mSpeed = motorFrequency[devId])#  U.getSerialDEV())
					time.sleep(0.5)	
					info = sensorCLASS[devId].get_info()
					if info == None: continue 	
					U.logger.log(20, u"{}-lidar info: {}".format(usbPortUsed[devId], info) )
					time.sleep(0.5)	
					health = sensorCLASS[devId].get_health()		
					U.logger.log(20, u"{}-lidar health: {}".format(usbPortUsed[devId],health) )
					startOK = True
					break
					#sensorCLASS[devId].stop()
					#sensorCLASS[devId].stop_motor()
					#sensorCLASS[devId].disconnect()
					#exit()
				except	Exception, e:
					U.logger.log(30, u"in Line {} has error={} -{}".format(sys.exc_traceback.tb_lineno, e, usbPortUsed[devId]))
					time.sleep(1)
					sensorCLASS[devId] = ""
					usbPortUsed[devId] = ""
			if startOK: 
				break

			U.logger.log(20, u"tried {}, is not answering properly ".format(usbPortUsed[devId]))
			sensorCLASS[devId] = ""
			usbPortUsed[devId] = ""


		if not startOK:
			U.logger.log(20, u"{} not started, no usb works, need to restart pgm-{}".format(G.program, usbPortUsed[devId]) )
			time.sleep(10)
			sensorCLASS[devId] = ""
			return False


		countMeasurements[devId] = 0
			
		if devId not in getlidarThreads: getlidarThreads[devId] = {}
		if restart:
			getlidarThreads[devId]["state"] = "stop"
			sensorCLASS[devId].stop()
			time.sleep(3)
			getlidarThreads[devId]={}
		if getlidarThreads[devId] == {}:
			getlidarThreads[devId] = { "run":True, "state":"wait", "thread": threading.Thread(name=u'getValues', target=getValues, args=(devId,))}	
			getlidarThreads[devId]["thread"].start()

			U.logger.log(20, u"thread started -{}".format(usbPortUsed[devId]))
		else:
			U.logger.log(20, u"getlidarThreads already on :{}".format(usbPortUsed[devId]))
		
		getlidarThreads[devId]["state"] = "run"

		time.sleep(.1)

	except	Exception, e:
		U.logger.log(30, u"in Line {} has error={}".format(sys.exc_traceback.tb_lineno, e, usbPortUsed[devId]))
		sensorCLASS[devId] = ""
		return False
	return True



#################################
def getValues(devId):
	global sensor, sensors,	 sensorCLASS, badSensor
	global startTimes
	global countMeasurements, calibratecalibrated
	global motorFrequency, nContiguousAngles, contiguousDeltaValue, anglesInOneBin,triggerLast, triggerCalibrated, sendToIndigoEvery, lastAliveSend, minSendDelta, usbPortUsed, usbPort, sendPixelData, doNotUseDataRanges, minSignalStrength
	global quick, getlidarThreads
	global waitforMeasurements, measurementsNeededForCalib
	
	calibratedSend = False

	# skip errors that repeated > 100 secs, try again, exit if 2 in a row < 100 secs 
	lastError = 0
	lastAliveSend[devId] = time.time()
	while  time.time() - lastError > 100:
		lastError = time.time()
		try:
			ret = ""
			useBins = int(360 / anglesInOneBin[devId])
			calibratedBins = [0 for i in range(useBins)]

			U.logger.log(20, "{}- starting with params:\n========\nuseBins: {}; motorFrequency: {};  anglesInOneBin: {};  \ncontiguousDeltaValue: {};  nContiguousAngles: {};  \ntriggerLast:{};  triggerCalibrated:{};  sendToIndigoEvery:{}\n========".format( usbPortUsed[devId],
					useBins, motorFrequency[devId], anglesInOneBin[devId], contiguousDeltaValue[devId], nContiguousAngles[devId], triggerLast[devId], triggerCalibrated[devId],sendToIndigoEvery[devId] ))
			while getlidarThreads[devId]["state"] != "run":
				if getlidarThreads[devId]["state"] == "stop": return 
				time.sleep(1)

			if sensorCLASS[devId] =="": return
			 
			countMeasurements[devId] = 0

			values 			= []
			entries 		= []
			timeStamps		= []
			nMeasKeep 		= max( 7,measurementsNeededForCalib[devId] +3)
			nTriggerKeep 	= 6



			for nn in range(nMeasKeep):
				values.append(copy.copy(calibratedBins))
				entries.append(copy.copy(calibratedBins))
				timeStamps.append(time.time())

			calibrated= ""
			U.logger.log(20, "trying to read: {}lidar360.calibrated-{}".format(G.homeDir,usbPortUsed[devId]) )
			jObj, raw = U.readJson("{}lidar360.calibrated-{}".format(G.homeDir,usbPortUsed[devId]) )
			if raw !="" and "values" in jObj:
				calibrated = jObj
				aa = jObj["anglesInOneBin"] 
				if devId not in aa or aa[devId] != anglesInOneBin[devId]: 
					calibrated = ""
			if calibrated !="":
				U.logger.log(20, u"read old calibration file")
				calibratecalibrated[devId] = False
			else:
				U.logger.log(20, u"need new calibration, no old file found-{}".format(usbPortUsed[devId]) )
				calibratecalibrated[devId]= True


			trV0 = { "current":{}, "calibrated":{} }
			trV0["current"]["nonZero"]	= 0
			trV0["current"]["GT"] 		= {"totalCount":0, "totalSum":0, "sections":[]}
			trV0["current"]["LT"] 		= {"totalCount":0, "totalSum":0, "sections":[]}
			trV0["calibrated"]["nonZero"]	= 0
			trV0["calibrated"]["GT"]   		= {"totalCount":0, "totalSum":0, "sections":[]}
			trV0["calibrated"]["LT"]  		= {"totalCount":0, "totalSum":0, "sections":[]} 
			trV0["calibrated"]["LT"]  		= {"totalCount":0, "totalSum":0, "sections":[]}
			trV =[]
			for nn in range(nTriggerKeep+1):
				trV.append(copy.copy(trV0)) 



			if calibrated !="": 
				try:
					if useBins != len(calibrated["values"]):
						calibratecalibrated[devId] = True
					else:
						values[0]  = copy.copy(calibrated["values"])
						entries[0] = copy.copy(calibrated["entries"])
				except:
					values[0]  = copy.copy(calibratedBins)
					entries[0]  = copy.copy(calibratedBins)
					calibratecalibrated[devId] = True
				trV[0]["calibrated"]["nonZero"]	= useBins - entries[0].count(0)
			else:
				calibratecalibrated[devId] = True



			tStart		= time.time()
			loopCount 	= 0
			for measurments in sensorCLASS[devId].iter_scans():
				loopCount +=1
				if getlidarThreads[devId]["state"] == "wait": 
					time.sleep(0.2)
					continue 
				if getlidarThreads[devId]["state"] == "stop": break 
			
				
				values.append(copy.copy(calibratedBins))
				entries.append(copy.copy(calibratedBins))
				timeStamps.append(time.time())
				del values[1]
				del entries[1]
				del timeStamps[1]

				ss = sorted(measurments, key = lambda x: x[1])
				nM = len(measurments)
				countNotcalibratedBins = 0
				# combine bins, pick only good signal values
				for ok, phi, v in ss:
					try:
						if ok < minSignalStrength[devId]: 	continue # dont use weak signals
						bin = min(useBins-1,int(phi/anglesInOneBin[devId]))
						values[-1][bin] += float(v)
						entries[-1][bin] += 1
					except	Exception, e:
						U.logger.log(30, u"in Line {} has error={}, bin:{}, entries:{} --{}".format(sys.exc_traceback.tb_lineno, e,bin, entries,  usbPortUsed[devId]))

				for ii in range(useBins):
					values[-1][ii]  = int( values[-1][ii]/max(1.,entries[-1][ii]))

				countNotcalibratedBins = useBins - entries[-1].count(0)
				upD			= {"current":0,"calibrated":0}
				deltaValues	= {"current":copy.copy(calibratedBins),"calibrated": copy.copy(calibratedBins)}
				#U.logger.log(20, u"1---tv:{}".format(tv))
				kk = 0
				kki= 0
				try:
					for mm in range(nTriggerKeep):
						nn = - (1 + mm)
						deltaList = {"current":[],"calibrated":[]}
						upD		  = {"current":0, "calibrated":0}
						trV[nn] = copy.deepcopy(trV0)
						trV[nn]["current"]["nonZero"] = useBins-(entries[nn]).count(0)
						for kk in ["current","calibrated"]:
							if kk =="current":	kki = -1
							else:			 	kki = 0 
							if nn == 1 and kk =="current": continue
							deltaList[kk] 	= []
							upD[kk] 		= 0
							for ii in range(useBins):

								## exclude data form bin ranges for triggers:
								try:
									use = True
									for dd in doNotUseDataRanges[devId]: # [[notFrom#1,notTo#1],[notFrom#2,notTo#2],..]
										if ii > dd[0] and ii < dd[1]: 
											use = False
											break
								except: 
									use = True

								if use and entries[-1][ii] > 0 and entries[nn][ii] >0 and entries[0][ii] >0:	
									deltaValues[kk][ii] = 100*(values[kki][ii] - values[nn][ii]) / max(1.,values[kki][ii] + values[nn][ii])

									if abs( deltaValues[kk][ii] ) >  contiguousDeltaValue[devId]:
										#U.logger.log(20, " {}; delta: {}; contiguousDeltaValue: {}".format(kk, delta, contiguousDeltaValue) )
										if deltaValues[kk][ii] > 0:
											if  upD[kk] != -1:
												deltaList[kk].append( deltaValues[kk][ii] )
												if len(deltaList[kk]) >= nContiguousAngles[devId]:
													if upD[kk] == +1:	
														trV[nn][kk]["GT"]["totalCount"]   		    += 1 
														trV[nn][kk]["GT"]["totalSum"]   		  	+= int(deltaValues[kk][ii]) 
														trV[nn][kk]["GT"]["sections"][-1]["bins"][1] = ii
														trV[nn][kk]["GT"]["sections"][-1]["sum"]    += int(deltaValues[kk][ii])
													else:	
														trV[nn][kk]["GT"]["totalSum"]   += int(sum(deltaList[kk]))
														trV[nn][kk]["GT"]["totalCount"] += nContiguousAngles[devId]
														trV[nn][kk]["GT"]["sections"].append(  {"bins":[max(0,ii-nContiguousAngles[devId]-1),ii], "sum":int(sum(deltaList[kk]))} )
														#U.logger.log(20, u"adding section: loopCount:{};  kk{}, kki{}, nn:{}, ii:{}; len(trv):{};  trV {} ".format(loopCount, kk, kki, nn, ii, len(trV[nn][kk]["GT"]["sections"]), trV[nn][kk]["GT"]))
													upD[kk] = +1
											else:
												deltaList[kk] 	= []
												upD[kk] 		= 0

										if deltaValues[kk][ii] < 0:
											if upD[kk] != +1:
												deltaList[kk].append( deltaValues[kk][ii] )
												if len(deltaList[kk]) >= nContiguousAngles[devId]:
													if upD[kk] == -1:	
														trV[nn][kk]["LT"]["totalCount"]   		    += 1 
														trV[nn][kk]["LT"]["totalSum"]   			+= int(deltaValues[kk][ii]) 
														trV[nn][kk]["LT"]["sections"][-1]["bins"][1] = ii
														trV[nn][kk]["LT"]["sections"][-1]["sum"]    += int(deltaValues[kk][ii])
													else:				
														trV[nn][kk]["LT"]["totalCount"] += nContiguousAngles[devId]
														trV[nn][kk]["LT"]["totalSum"]   += int(sum(deltaList[kk]))
														trV[nn][kk]["LT"]["sections"].append(  {"bins":[max(0,ii-nContiguousAngles[devId]-1),ii], "sum":int(sum(deltaList[kk]))} )
														#U.logger.log(20, u"adding section: loopCount:{};  kk{}, kki{}, nn:{}, ii:{}; len(trv):{};  trV {} ".format(loopCount, kk, kki, nn, ii, len(trV[nn][kk]["LT"]["sections"]), trV[nn][kk]["LT"]))
													upD[kk] = -1
											else:
												deltaList[kk] 	= []
												upD[kk] 		= 0

								
									else:
										deltaList[kk] 	= []
										upD[kk] 		= 0
						trV[nn]["calibrated"]["nonZero"] = trV[0]["calibrated"]["nonZero"]	
				except	Exception, e:
					U.logger.log(20, u"in Line {} has error={} --{}".format(sys.exc_traceback.tb_lineno, e,  usbPortUsed[devId]))
					U.logger.log(20, u"trV {} kk{}, kki{}, nn:{}".format(trV, kk, kki, nn))
				

				countMeasurements[devId] +=1
				##### check if calibration mode ##############
				#U.logger.log(20,"countMeasurements: {};  waitforMeasurements: {};  calibratecalibrated: {}".format(countMeasurements[devId], waitforMeasurements, calibratecalibrated[devId]))
				if countMeasurements[devId] >= waitforMeasurements and calibratecalibrated[devId]:
					if countMeasurements[devId] == waitforMeasurements: # start calib
						accumV = copy.copy(calibratedBins)
						countC = copy.copy(calibratedBins)
						nMeas =0

					for ii in range(useBins):
						accumV[ii] += values[-1][ii]
						if values[-1][ii] > 0: countC[ii] += 1
					nMeas +=1

					if countMeasurements[devId] >= waitforMeasurements + measurementsNeededForCalib[devId]: # finished calib
						calibratecalibrated[devId] = False
						for ii in range(useBins):
							accumV[ii] = int(accumV[ii]/max(1,countC[ii]))
							countC[ii] = int(countC[ii])

						values[0]  	= copy.copy(accumV)
						entries[0] 	= copy.copy(countC)
						trV[0]["calibrated"]["nonZero"] = useBins-(entries[0]).count(0)
						U.logger.log(20,"{}-created new calibrated room calibration file bins with zero bins: {} out of: {}, nMeas:{}; req:{}".format( usbPortUsed[devId], accumV.count(0), len(accumV), nMeas, measurementsNeededForCalib[devId]))
						U.writeJson(G.homeDir+G.program+".calibrated-"+usbPortUsed[devId], {"values":values[0], "entries":entries[0], "anglesInOneBin":anglesInOneBin, "nMeas":nMeas})
						calibratedSend = False
						##### calibration ended         ##############
				##### check if calibration mode ##############  END


				test = 0; test0 = 0
				if not calibratecalibrated[devId] and loopCount > 20:
					test0 =  (time.time() - lastAliveSend[devId]) > minSendDelta[devId] 

					if test0:
						maxAllValue	= {"current":-1, "calibrated":-1}
						maxAllind 	= {"current":-1, "calibrated":-1}
						for ce in ["current", "calibrated"]:
							for lg in ["LT","GT"]:
								for nn in range(nTriggerKeep):
									ii = -(1+nn) 
									if trV[ii][ce][lg]["totalCount"] > maxAllValue[ce]:
										maxAllValue[ce] = trV[ii][ce][lg]["totalCount"]
										maxAllind[ce] = ii

						test =			maxAllValue["current"] > triggerLast[devId]
						test = test or (time.time() - sendToIndigoEvery[devId]) > lastAliveSend[devId]
						test = test or  quick
	

						if  test:
							data = {"triggerValues": 
									{"current": trV[maxAllind["current"]]["current"], 
									"calibrated": trV[maxAllind["calibrated"]]["calibrated"] ,
									"nBins": useBins, 
									"port": usbPortUsed[devId],
									"dTime_Last-Current": round(timeStamps[maxAllind["current"]] - timeStamps[-1],2),
									"dIndex_Last-Current": -maxAllind["current"]},
									"doNotUseDataRanges":doNotUseDataRangesString[devId] }
							if sendPixelData[devId]:
								if not calibratedSend:
									data["calibrated"] 	= values[0]
									calibratedSend = True
								data["current"] = values[-1]
								data["last"] 	= values[maxAllind["current"]]
							U.sendURL( {"sensors":{sensor:{devId:data}}} )
							lastAliveSend[devId] = time.time()
							# keep last send trigger values

							if False: U.logger.log(20,"{}-maxAllValue:{};  maxAllind:{}\ntrV E gt:{}; lt:{}".format( usbPortUsed[devId], maxAllValue, maxAllind, trV[maxAllind["calibrated"]]["calibrated"]["GT"], trV[maxAllind["calibrated"]]["calibrated"]["LT"]) )
						U.echoLastAlive(G.program)

				if False:
					U.logger.log(20, "{}-testifSend:{};{};  dT:{:6.1f};  nM :{:3d}; nE: {:3d};   DELTA  Cont- L-GT: {};  L-LT: {};  E-GT: {};  E-LT: {}, trgcalibrated:{};  trgLast:{}".format(
						 usbPortUsed[devId],test,test0, time.time() - tStart, nM, countNotcalibratedBins, trV[-1]["current"]["GT"], trV[-1]["current"]["LT"], trV[-1]["calibrated"]["GT"], trV[-1]["calibrated"]["LT"],  triggerCalibrated[devId], triggerLast[devId] )
					 )
		except	Exception, e:
			U.logger.log(30, u"in Line {} has error={}".format(sys.exc_traceback.tb_lineno, e))
	U.logger.log(30, u"{}-exit getsensor due error in iter_measurments".format({ usbPortUsed[devId]}))
	lastAliveSend[devId]  = 0
	return 




############################################
global rawOld
global sensor, sensors, badSensor
global sensorCLASS
global oldRaw, lastRead
global startTime
global quick, getlidarThreads
global motorFrequency, nContiguousAngles, contiguousDeltaValue, anglesInOneBin,triggerLast, triggerCalibrated, sendToIndigoEvery, lastAliveSend,minSendDelta, usbPortUsed, sendPixelData, doNotUseDataRanges, doNotUseDataRangesString, minSignalStrength
global calibratecalibrated
global countMeasurements, waitforMeasurements,	measurementsNeededForCalib

minSignalStrength			= {}
doNotUseDataRangesString	= {}
doNotUseDataRanges			= {}
sendPixelData				= {}
usbPort						= {}
usbPortUsed					= {}
waitforMeasurements 		= 10
measurementsNeededForCalib 	= {}
motorFrequency 				= {}
nContiguousAngles			= {}
contiguousDeltaValue 		= {}
anglesInOneBin 				= {}
triggerLast 				= {}
triggerCalibrated 				= {}
sendToIndigoEvery 			= {}
lastAliveSend				= {}
minSendDelta				= {}	
calibratecalibrated			= {}
countMeasurements			= {}

getlidarThreads			={}
quick						= False
oldDistances				={}
	

startTime					= time.time()
lastMeasurement				= time.time()
oldRaw						= ""
lastRead					= 0
loopCount					= 0
sensorRefreshSecs			= 91
NSleep						= 100
sensorList					= []
sensors						= {}
sensor						= G.program
display						= "0"
badSensor					= 0
sensorActive				= False
loopSleep					= 0.5
rawOld						= ""
sensorCLASS					={}
displayEnable				= 0
myPID		= str(os.getpid())
U.setLogging()

U.killOldPgm(myPID,G.program+".py")# kill old instances of myself if they are still running

U.logger.log(20,"==== Start {} ===== ".format(G.program))

if U.getIPNumber() > 0:
	time.sleep(10)
	U.logger.log(30, u"exit  {} , no ip number found".format(G.program))
	exit()

readParams()



time.sleep(1)

lastRead = time.time()
lastUpdate = time.time()
U.echoLastAlive(G.program)

lastRead			= time.time()

msgCount			= 0
loopSleep			= 1
sensorWasBad		= False


while True:
	try:
		loopCount +=1
		quick = U.checkNowFile(G.program)				 

		if loopCount %5 ==0 and not quick:
			if time.time() - lastRead > 5.:	 
				readParams()
				lastRead = time.time()

			for devId in lastAliveSend:
				if time.time() - lastAliveSend[devId] > 120: 
					U.restartMyself(reason=G.program+" data acquisition seems to hang", delay= 20)

		if U.checkNewCalibration(G.program):
			U.logger.log(30, u"starting with new calibrated room data calibration")
			for devId in calibratecalibrated:
				calibratecalibrated[devId] = True
				countMeasurements[devId]  = 0

		time.sleep(loopSleep)
	except	Exception, e:
		U.logger.log(30, u"in Line {} has error={}".format(sys.exc_traceback.tb_lineno, e))
		time.sleep(5.)
try: 	G.sendThread["run"] = False; time.sleep(1)
except: pass
sys.exit(0)
 

		