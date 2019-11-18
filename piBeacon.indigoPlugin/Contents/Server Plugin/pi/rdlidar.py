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
G.program = "rdlidar"

'''Simple and lightweight module for working with RPLidar rangefinder scanners.

Usage example:

>>> from rplidar import RPLidar
>>> lidar = RPLidar('/dev/ttyUSB0')
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
>>> lidar.stop()
>>> lidar.stop_motor()
>>> lidar.disconnect()

For additional information please refer to the RPLidar class documentation.
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


class RPLidarException(Exception):
	'''Basic exception class for RPLidar'''


def _b2i(byte):
	'''Converts byte to integer (for Python 2 compatability)'''
	return byte if int(sys.version[0]) == 3 else ord(byte)

def _process_scan(raw):
	'''Processes input raw data and returns measurment data'''
	new_scan = bool(_b2i(raw[0]) & 0b1)
	inversed_new_scan = bool((_b2i(raw[0]) >> 1) & 0b1)
	quality = _b2i(raw[0]) >> 2
	if new_scan == inversed_new_scan:
		raise RPLidarException('New scan flags mismatch')
	check_bit = _b2i(raw[1]) & 0b1
	if check_bit != 1:
		raise RPLidarException('Check bit not equal to 1')
	angle = ((_b2i(raw[1]) >> 1) + (_b2i(raw[2]) << 7)) / 64.
	distance = (_b2i(raw[3]) + (_b2i(raw[4]) << 8)) / 4.
	return new_scan, quality, angle, distance


class RPLidar(object):
	'''Class for communicating with RPLidar rangefinder scanners'''

	_serial_port = None  #: serial port connection
	port = ''  #: Serial port name, e.g. /dev/ttyUSB0
	timeout = 1  #: Serial port timeout
	motor = False  #: Is motor running?
	baudrate = 115200  #: Baudrate for serial port

	def __init__(self, port, baudrate=115200, timeout=1, logger=None, mSpeed=DEFAULT_MOTOR_PWM):
		'''Initilize RPLidar object for communicating with the sensor.

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
			logger = logging.getLogger('rplidar')
		self.connect()
		self.start_motor()

	def connect(self):
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
			raise RPLidarException('Failed to connect to the sensor due to: {}'.format(err) )

	def disconnect(self):
		'''Disconnects from the serial port'''
		if self._serial_port is None:
			return
		self._serial_port.close()

	def set_pwm(self, pwm):
		assert(0 <= pwm <=1)
		payload = struct.pack("<H", int(pwm * MAX_MOTOR_PWM))
		self._send_payload_cmd(SET_PWM_BYTE, payload)

	def start_motor(self):
		'''Starts sensor motor'''
		U.logger.log(10,'Starting motor')
		# For A1
		self._serial_port.dtr = False

		# For A2
		self.set_pwm(self._motorSpeed)
		self.motor_running = True
		U.logger.log(20,'Starting motor .. done')

	def stop_motor(self):
		'''Stops sensor motor'''
		U.logger.log(20,'Stoping motor')
		# For A2
		self.set_pwm(0)
		time.sleep(.001)
		# For A1
		self._serial_port.dtr = True
		self.motor_running = False

	def _send_payload_cmd(self, cmd, payload):
		'''Sends `cmd` command with `payload` to the sensor'''
		U.logger.log(10,'sending cmd:{} payload:{}'.format(cmd,payload ) )
		size = struct.pack('B', len(payload))
		req = SYNC_BYTE + cmd + size + payload
		checksum = 0
		for v in struct.unpack('B'*len(req), req):
			checksum ^= v
		req += struct.pack('B', checksum)
		self._serial_port.write(req)
		U.logger.log(10,'Command sent: {}'.format(req))

	def _send_cmd(self, cmd):
		'''Sends `cmd` command to the sensor'''
		req = SYNC_BYTE + cmd
		self._serial_port.write(req)
		U.logger.log(10,'Command sent: {}'.format(req) )

	def _read_descriptor(self):
		'''Reads descriptor packet'''
		descriptor = self._serial_port.read(DESCRIPTOR_LEN)
		U.logger.log(10,'Recieved descriptor: {}'.format(descriptor) )
		if len(descriptor) != DESCRIPTOR_LEN:
			raise RPLidarException('Descriptor length mismatch')
		elif not descriptor.startswith(SYNC_BYTE + SYNC_BYTE2):
			raise RPLidarException('Incorrect descriptor starting bytes .. ok  first 2 calls ')
		is_single = _b2i(descriptor[-2]) == 0
		return _b2i(descriptor[2]), is_single, _b2i(descriptor[-1])

	def _read_response(self, dsize):
		'''Reads response packet with length of `dsize` bytes'''
		U.logger.log(10,'Trying to read response: {} bytes'.format(dsize) )
		data = self._serial_port.read(dsize)
		U.logger.log(10,'Recieved data len{}'.format(len(data)) )
		if len(data) != dsize:
			raise RPLidarException('Wrong body size')
		return data

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
				raise RPLidarException('Wrong get_info reply length')
			if not is_single:
				raise RPLidarException('Not a single response mode')
			if dtype != INFO_TYPE:
				raise RPLidarException('Wrong response data type')
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
			U.logger.log(30, u"in Line {} has error={}".format(sys.exc_traceback.tb_lineno, e))

	def get_health(self):
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
			raise RPLidarException('Wrong get_info reply length')
		if not is_single:
			raise RPLidarException('Not a single response mode')
		if dtype != HEALTH_TYPE:
			raise RPLidarException('Wrong response data type')
		raw = self._read_response(dsize)
		status = _HEALTH_STATUSES[_b2i(raw[0])]
		error_code = (_b2i(raw[1]) << 8) + _b2i(raw[2])
		return status, error_code

	def clear_input(self):
		'''Clears input buffer by reading all available data'''
		self._serial_port.read_all()

	def stop(self):
		'''Stops scanning process, disables laser diode and the measurment
		system, moves sensor to the idle state.'''
		U.logger.log(20,'Stoping scanning')
		self._send_cmd(STOP_BYTE)
		time.sleep(.001)
		self.clear_input()

	def reset(self):
		'''Resets sensor core, reverting it to a similar state as it has
		just been powered up.'''
		U.logger.log(20,'Reseting the sensor')
		self._send_cmd(RESET_BYTE)
		time.sleep(.002)

	def iter_measurments(self, max_buf_meas=500):
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
		U.logger.log(30,'Health status: {} [{}]'.format(status, error_code) )
		if status == _HEALTH_STATUSES[2]:
			U.logger.log(30,'Trying to reset sensor due to the error. Error code: {}'.format(error_code) )
			self.reset()
			status, error_code = self.get_health()
			if status == _HEALTH_STATUSES[2]:
				raise RPLidarException('RPLidar hardware failure. Error code: {}'.format(error_code) )
		elif status == _HEALTH_STATUSES[1]:
			U.logger.log(30,'Warning sensor status detected! Error code:{}'.format(error_code) )
		cmd = SCAN_BYTE
		self._send_cmd(cmd)
		dsize, is_single, dtype = self._read_descriptor()
		if dsize != 5:
			raise RPLidarException('Wrong get_info reply length')
		if is_single:
			raise RPLidarException('Not a multiple response mode')
		if dtype != SCAN_TYPE:
			raise RPLidarException('Wrong response data type')
		while True:
			raw = self._read_response(dsize)
			U.logger.log(10,'Recieved scan response: %s' % raw)
			if max_buf_meas:
				data_in_buf = self._serial_port.in_waiting
				if data_in_buf > max_buf_meas*dsize:
					U.logger.log(30, 'Too many measurments in the input buffer: {}  {} Clearing buffer...'.format(data_in_buf//dsize, max_buf_meas) )
					self._serial_port.read(data_in_buf//dsize*dsize)
			yield _process_scan(raw)

	def iter_scans(self, max_buf_meas=500, min_len=5):
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




# ===========================================================================
# read params
# ===========================================================================

#################################		 
def readParams():
	global sensorList, sensors, logDir, sensor,	 sensorRefreshSecs, displayEnable
	global rawOld
	global oldRaw, lastRead
	global startTime
	global motorFrequency, nContiguousAngles, contiguousDeltaValue, anglesInOneBin,triggerLast, triggerEmpty, sendToIndigoEvery, lastAliveSend, minSendDelta

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
			U.logger.log(30, "{} is not in parameters = not enabled, stopping {}.py".format(sensor, sensor) )
			exit()
			

		U.logger.log(20, "{} reading new parameter file".format(sensor) )

		restart = False
		for devId in sensors[sensor]:

			
			if devId not in motorFrequency: 			motorFrequency[devId] 				= 0.3
			if devId not in nContiguousAngles: 			nContiguousAngles[devId] 			= 5
			if devId not in contiguousDeltaValue:		contiguousDeltaValue[devId]		 	= 5
			if devId not in anglesInOneBin:				anglesInOneBin[devId] 				= 2
			if devId not in triggerLast:				triggerLast[devId] 					= 4
			if devId not in triggerEmpty:				triggerEmpty[devId] 				= 5
			if devId not in sendToIndigoEvery:			sendToIndigoEvery[devId]			= 30
			if devId not in lastAliveSend:				lastAliveSend[devId]				= 0
			if devId not in measurementsNeededForCalib	:measurementsNeededForCalib[devId]	= -1

			try:
				old = measurementsNeededForCalib[devId]
				if "measurementsNeededForCalib" in sensors[sensor][devId]: 
					measurementsNeededForCalib[devId] = int(sensors[sensor][devId]["measurementsNeededForCalib"])
			except:	measurementsNeededForCalib[devId] = 6
			if old !=-1 and old != measurementsNeededForCalib[devId]: 
				os.remove(G.homeDir+"rdlidar.emptyRoom > /dev/null 2>&1 ")
				restart = True

			try:
				old = triggerLast[devId]
				if "triggerLast" in sensors[sensor][devId]: 
					triggerLast[devId] = float(sensors[sensor][devId]["triggerLast"])
			except:	triggerLast[devId] = 5
			if old != triggerLast[devId]: restart = True

			try:
				old = triggerEmpty[devId]
				if "triggerEmpty" in sensors[sensor][devId]: 
					triggerEmpty[devId] = float(sensors[sensor][devId]["triggerEmpty"])
			except:	triggerEmpty[devId] = 5
			if old != triggerEmpty[devId]: restart = True

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
			
			if devId not in sensorCLASS  or restart:
				startSensor(devId, motorFrequency[devId], restart = True)
				if sensorCLASS[devId] == "":
					return
				
		deldevID={}		   
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
		print sensors[sensor]
		


#################################
def startSensor(devId, motorFreq, restart=False):
	global sensors, sensor
	global startTime
	global sensorCLASS
	global countMeasurements, calibrateEmptyRoom
	global quick, getRdlidarThreads
	try:
		startTime =time.time()

		startOK = False
		
		for ii in range(3): # need to init several times in some circumstances 
			try:
				sensorCLASS[devId]  =	 RPLidar('/dev/ttyUSB0', mSpeed = motorFreq)#  U.getSerialDEV())
				time.sleep(0.5)	
				info = sensorCLASS[devId].get_info()
				if info == None: continue 	
				U.logger.log(20, u"lidar info: {}".format(info) )
				time.sleep(0.5)	
				health = sensorCLASS[devId].get_health()		
				U.logger.log(20, u"lidar health: {}".format(health) )
				startOK = True
				break
				#sensorCLASS[devId].stop()
				#sensorCLASS[devId].stop_motor()
				#sensorCLASS[devId].disconnect()
				#exit()
			except	Exception, e:
				U.logger.log(30, u"in Line {} has error={}".format(sys.exc_traceback.tb_lineno, e))
				sensorCLASS[devId] = ""
				time.sleep(1)
		if not startOK:
			U.logger.log(20, u"lidar not started, need to restart pgm" )
			time.sleep(10)
			exit()

		else:
			empty= ""
			jObj, raw = U.readJson(G.homeDir+"rdlidar.emptyRoom")
			if raw !="" and "values" in jObj:
				empty = jObj["values"]
				aa = jObj["anglesInOneBin"] 
				if devId not in aa or aa[devId] != anglesInOneBin[devId]: 
					empty = ""
			if empty !="":
				U.logger.log(20, u"read old calibration file")
				calibrateEmptyRoom[devId] = False
			else:
				U.logger.log(20, u"need new calibration, no old file found")
				calibrateEmptyRoom[devId]= True

			countMeasurements[devId] = 0
				
			if restart:
				getRdlidarThreads["state"] = "stop"
				time.sleep(1)
				getRdlidarThreads={}
			if getRdlidarThreads == {}:
				getRdlidarThreads = { "run":True, "state":"wait", "thread": threading.Thread(name=u'getValues', target=getValues, args=(devId,empty))}	
				getRdlidarThreads["thread"].start()

				U.logger.log(20, u"thread started")
			else:
				U.logger.log(20, u"getRdlidarThreads already on :{}".format(getRdlidarThreads))
			
			getRdlidarThreads["state"] = "run"

			time.sleep(.1)
	except	Exception, e:
		U.logger.log(30, u"in Line {} has error={}".format(sys.exc_traceback.tb_lineno, e))




#################################
def getValues(devId,empty):
	global sensor, sensors,	 sensorCLASS, badSensor
	global startTime
	global countMeasurements, calibrateEmptyRoom
	global motorFrequency, nContiguousAngles, contiguousDeltaValue, anglesInOneBin,triggerLast, triggerEmpty, sendToIndigoEvery, lastAliveSend, minSendDelta
	global quick, getRdlidarThreads
	global waitforMeasurements, measurementsNeededForCalib


	ret = ""
	try:
		useBins = int(360 / anglesInOneBin[devId])

		U.logger.log(20, "starting with params:\n========\nuseBins: {}; motorFrequency: {};  anglesInOneBin: {};  \ncontiguousDeltaValue: {};  nContiguousAngles: {};  \ntriggerLast:{};  triggerEmpty:{};  sendToIndigoEvery:{}\n========".format(
				useBins, motorFrequency[devId], anglesInOneBin[devId], contiguousDeltaValue[devId], nContiguousAngles[devId], triggerLast[devId], triggerEmpty[devId],sendToIndigoEvery[devId] ))
		while getRdlidarThreads["state"] != "run":
			if getRdlidarThreads["state"] == "stop": wait
			time.sleep(1)

		if sensorCLASS[devId] =="": return
			 
		countMeasurements[devId] = 0
		lastS =  0
		emptyS = 0.
		tStart = time.time()
		values ={"current":[0 for i in range(anglesInOneBin[devId])], "last":[0 for i in range(useBins)], "empty":[0 for i in range(useBins)], "phi":[ ii*anglesInOneBin[devId] for ii in range(useBins)]}
		triggerValues2 = {"current":{"GT":0,"LT":0,"maxValue":0,"directions":[]},"empty":{"GT":0,"LT":0,"maxValue":0,"directions":[]}}
		triggerValues  = {"current":{"GT":0,"LT":0,"maxValue":0,"directions":[]},"empty":{"GT":0,"LT":0,"maxValue":0,"directions":[]}}


		if empty !="": 
			values["empty"] = copy.copy(empty)
			triggerValues["empty"]["maxValue"]  = max(values["empty"])
		for measurments in sensorCLASS[devId].iter_scans():
			if getRdlidarThreads["state"] == "wait": 
				time.sleep(0.2)
				continue 
			if getRdlidarThreads["state"] == "stop": break 

			deltaList = {"current":[],"empty":[]}
			values["current"] = [0 for i in range(useBins)]
			values["entries"] = [0 for i in range(useBins)]

			ss = sorted(measurments, key = lambda x: x[1])
			nM = len(measurments)
			countNotEmptyBins = 0
			countValues = 0
			# combine bins, pick only good signal values
			for ok, phi, v in ss:
				try:
					if ok < 14: 	continue # dont use weak signals
					countValues +=1
					bin = int(phi/anglesInOneBin[devId])
					values["current"][bin] += v
					values["entries"][bin] += 1.
				except	Exception, e:
					U.logger.log(30, u"in Line {} has error={}".format(sys.exc_traceback.tb_lineno, e))
			countNotEmptyBins = useBins - values["entries"].count(0)
			upD={"current":0,"empty":0}
			triggerValues["current"]["GT"] = 0
			triggerValues["current"]["LT"] = 0
			triggerValues["empty"]["GT"] = 0
			triggerValues["empty"]["LT"] = 0
			triggerValues["empty"]["directions"] = []
			triggerValues["current"]["directions"] = []
			nTot = 0
			for ii in range(useBins):
						nTot += values["entries"][ii]
						values["current"][ii]  = ( values["current"][ii]/max(1.,values["entries"][ii]))
						if values["entries"][ii] > 0 and values["last"][ii] >0 and values["empty"][ii] >0:	
							for kk in ["current","empty"]:
								delta = 100*(values["last"][ii] - values[kk][ii]) / max(1.,values["last"][ii] + values[kk][ii])

								if abs( delta ) >  contiguousDeltaValue[devId]:
									#U.logger.log(20, " {}; delta: {}; contiguousDeltaValue: {}".format(kk, delta, contiguousDeltaValue) )
									if delta > 0:
										if  upD[kk] != -1:
											deltaList[kk].append( delta )
											if len(deltaList[kk]) >= nContiguousAngles[devId]:
												#if sum(deltaList[kk]) >  (nContiguousAngles*nContiguousAngles): 
													if upD[kk] == +1:	
																		triggerValues[kk]["GT"] 				+= 1 
																		triggerValues[kk]["directions"][-1][1]  = ii
																		triggerValues[kk]["directions"][-1][2] += +1
																		triggerValues[kk]["directions"][-1][3] += int(delta)
													else:				
																		triggerValues[kk]["GT"] += nContiguousAngles[devId]
																		triggerValues[kk]["directions"].append( [max(0,ii-nContiguousAngles[devId]-1), ii ,nContiguousAngles[devId], int(delta*nContiguousAngles[devId])  ] )
													upD[kk] = +1
										else:
											deltaList[kk] = []
											upD[kk] = 0

									if delta < 0:
										if upD[kk] != +1:
											deltaList[kk].append( delta )
											if len(deltaList[kk]) >= nContiguousAngles[devId]:
												#if sum(deltaList[kk]) < -(nContiguousAngles*nContiguousAngles): 
													if upD[kk] == -1:	
																		triggerValues[kk]["LT"] 				+= 1 
																		triggerValues[kk]["directions"][-1][1]  = ii
																		triggerValues[kk]["directions"][-1][2] += +1
																		triggerValues[kk]["directions"][-1][3] += int(delta)
													else:				
																		triggerValues[kk]["LT"] += nContiguousAngles[devId]
																		triggerValues[kk]["directions"].append( [max(0,ii-nContiguousAngles[devId] -1), ii, nContiguousAngles[devId], int(delta*nContiguousAngles[devId])  ] )
													upD[kk] = -1
										else:
											deltaList[kk] = []
											upD[kk] = 0
	
									
								else:
									deltaList[kk] = []
									upD[kk] = 0
						else:
							if False:
								deltaList["empty"] = []
								upD["empty"] = 0
								deltaList["current"] = []
								upD["current"] = 0
						values["current"][ii]  = int( values["current"][ii] )
			triggerValues["current"]["maxValue"] = max(values["current"])


			countMeasurements[devId] +=1
			##### check if calibration mode ##############
			if countMeasurements[devId] >= waitforMeasurements and calibrateEmptyRoom[devId]:
				LL = len(values["current"])
				if countMeasurements[devId] == waitforMeasurements: # start calib
					accumV =  copy.copy(values["current"])
					countC = [0 for ii in range(LL)]
					for ii  in range(LL):
						if values["current"][ii] > 0: countC[ii] = 1
				else: # accumulate 
					for ii in range(LL):
						accumV[ii] += values["current"][ii]
						if values["current"][ii] > 0: countC[ii] +=1
				if countMeasurements[devId] >= waitforMeasurements+ measurementsNeededForCalib[devId]: # finished calib
					calibrateEmptyRoom[devId]= False
					for ii in range(LL):
						accumV[ii] = int(accumV[ii]/max(1,countC[ii]))
					values["empty"] = copy.copy(accumV)
					zeros = accumV.count(0)
					triggerValues["empty"]["maxValue"] = triggerValues["current"]["maxValue"] 
					U.logger.log(20,"created new empty room calibration file bins with no value: {} out of: {}".format(zeros, len(accumV)))
					U.writeJson(G.homeDir+"rdlidar.emptyRoom", {"values":values["empty"],"anglesInOneBin":anglesInOneBin})
					##### calibration ended         ##############
			##### check if calibration mode ##############  END




			if not calibrateEmptyRoom[devId]:
				test =	( 	triggerValues["current"]["GT"] > triggerLast[devId] or 
							triggerValues["current"]["LT"] > triggerLast[devId]  or 
							abs(triggerValues["empty"]["GT"] - triggerValues2["empty"]["GT"]) > triggerEmpty[devId] or 
							abs(triggerValues["empty"]["LT"] - triggerValues2["empty"]["LT"]) > triggerEmpty[devId]  or 
							time.time() - abs(sendToIndigoEvery[devId]) > lastAliveSend[devId]  or  
							quick  
						)  and 	( time.time() - lastAliveSend[devId] > minSendDelta[devId] ) 
					

				if  test:
					data = {"triggerValues": triggerValues}
					data["anglesInOneBin"] = anglesInOneBin
					data["empty"] = values["empty"]
					data["current"] = values["current"]
					data["last"] = values["last"]
					U.sendURL( {"sensors":{sensor:{devId:data}}} )
					lastAliveSend[devId] = time.time()
					# keep last send trigger values
					triggerValues2 = copy.copy(triggerValues)

			values["last"] = copy.copy(values["current"])

			U.logger.log(10, "testifSend:{};  dT:{:6.1f};  nM :{:3d}; nE: {:3d};   DELTA  Cont- L-GT: {:3d};  L-LT: {:3d};  E-GT: {:3d};  E-LT: {:3d}".format(
				test, time.time() - tStart, nM, countNotEmptyBins, triggerValues["current"]["GT"], triggerValues["current"]["LT"], triggerValues["empty"]["GT"], triggerValues["empty"]["LT"])
			 )

	except	Exception, e:
		U.logger.log(30, u"in Line {} has error={}".format(sys.exc_traceback.tb_lineno, e))
	return 





############################################
global rawOld
global sensor, sensors, badSensor
global sensorCLASS
global oldRaw, lastRead
global startTime
global quick, getRdlidarThreads
global motorFrequency, nContiguousAngles, contiguousDeltaValue, anglesInOneBin,triggerLast, triggerEmpty, sendToIndigoEvery, lastAliveSend,minSendDelta
global calibrateEmptyRoom
global countMeasurements, waitforMeasurements,	measurementsNeededForCalib

waitforMeasurements 		= 4
measurementsNeededForCalib 	= {}
motorFrequency 				= {}
nContiguousAngles			= {}
contiguousDeltaValue 		= {}
anglesInOneBin 				= {}
triggerLast 				= {}
triggerEmpty 				= {}
sendToIndigoEvery 			= {}
lastAliveSend				= {}
minSendDelta				= {}	
calibrateEmptyRoom			= {}
countMeasurements			= {}

getRdlidarThreads			={}
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

U.echoLastAlive(G.program)

lastRead			= time.time()
G.lastAliveSend		= time.time() -1000

msgCount			= 0
loopSleep			= 1
sensorWasBad		= False


while True:
	try:
		loopCount +=1
		quick = U.checkNowFile(G.program)				 
		U.echoLastAlive(G.program)

		if loopCount %5 ==0 and not quick:
			if time.time() - lastRead > 5.:	 
				readParams()
				lastRead = time.time()
		if U.checkNewCalibration(G.program):
			U.logger.log(30, u"starting with new empty room data calibration")
			for devId in calibrateEmptyRoom:
				calibrateEmptyRoom[devId] = True
				countMeasurements[devId]  = 0

		time.sleep(loopSleep)
	except	Exception, e:
		U.logger.log(30, u"in Line {} has error={}".format(sys.exc_traceback.tb_lineno, e))
		time.sleep(5.)
try: 	G.sendThread["run"] = False; time.sleep(1)
except: pass
sys.exit(0)
 

		