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
"""

import array
import serial

import logging
from ctypes import *
import sys, os, time, json, datetime,subprocess,copy
import smbus

sys.path.append(os.getcwd())
import	piBeaconUtils	as U
import	piBeaconGlobals as G

G.program = "DF2301Q"


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
############ UART ##########################	end


class DFRobot_DF2301Q(object):

	def __init__(self):
		pass


class DFRobot_DF2301Q_I2C(DFRobot_DF2301Q):

	def __init__(self, i2c_addr=DF2301Q_I2C_ADDR, bus=1):
		self._addr = i2c_addr
		self._i2c = smbus.SMBus(bus)
		super(DFRobot_DF2301Q_I2C, self).__init__()

	def get_CMDID(self):
		time.sleep(0.05)	 # Prevent the access rate from interfering with other functions of the voice module
		return self._read_reg(DF2301Q_I2C_REG_CMDID)  # 0= nothig new 

	def play_by_CMDID(self, CMDID):
		# note Can enter wake-up state through ID = 1 in I2C mode
		self._write_reg(DF2301Q_I2C_REG_PLAY_CMDID, CMDID)
		time.sleep(1)

	def get_wake_time(self):
		return self._read_reg(DF2301Q_I2C_REG_WAKE_TIME)

	def set_wake_time(self, wake_time):
		wake_time = wake_time & 0xFF
		self._write_reg(DF2301Q_I2C_REG_WAKE_TIME, wake_time)

	def set_volume(self, vol):
		if (vol < 0):		vol = 0
		elif (vol > 20):  	vol = 20
		self._write_reg(DF2301Q_I2C_REG_SET_VOLUME, vol)

	def set_mute_mode(self, mode):
		if (0 != mode):
			mode = 1
		self._write_reg(DF2301Q_I2C_REG_SET_MUTE, mode)

	def _write_reg(self, reg, data):
		if isinstance(data, int):
			data = [data]
		self._i2c.write_i2c_block_data(self._addr, reg, data)

	def _read_reg(self, reg):
		data = self._i2c.read_i2c_block_data(self._addr, reg, 1)
		return data[0]


##############  uart class, not used yet ##########
class DFRobot_DF2301Q_UART(DFRobot_DF2301Q):

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

	def __init__(self):
		'''!
			@brief Module UART communication init
		'''
		self.uart_cmd_ID = 0
		self._send_sequence = 0
		self._ser = serial.Serial("/dev/ttyAMA0", baudrate=DF2301Q_UART_BAUDRATE, bytesize=8, parity='N', stopbits=1, timeout=0.5)
		if self._ser.isOpen == False:
			self._ser.open()
		super(DFRobot_DF2301Q_UART, self).__init__()

	def get_CMDID(self):
		'''!
			@brief Get the ID corresponding to the command word 
			@return Return the obtained command word ID, returning 0 means no valid ID is obtained
		'''
		self._recv_packet()
		temp = self.uart_cmd_ID
		self.uart_cmd_ID = 0
		return temp

	def play_by_CMDID(self, play_id):
		'''!
			@brief Play the corresponding reply audio according to the command word ID
			@param CMDID - Command word ID
		'''
		msg = self.uart_msg()
		msg.header = DF2301Q_UART_MSG_HEAD
		msg.data_length = 6
		msg.msg_type = DF2301Q_UART_MSG_TYPE_CMD_DOWN
		msg.msg_cmd = DF2301Q_UART_MSG_CMD_PLAY_VOICE
		msg.msg_seq = self._send_sequence
		self._send_sequence += 1
		msg.msg_data[0] = DF2301Q_UART_MSG_DATA_PLAY_START
		msg.msg_data[1] = DF2301Q_UART_MSG_DATA_PLAY_BY_CMD_ID
		msg.msg_data[2] = play_id

		self._send_packet(msg)
		time.sleep(1)

	def reset_module(self):
		'''!
			@brief Reset the module
		'''
		msg = self.uart_msg()
		msg.header = DF2301Q_UART_MSG_HEAD
		msg.data_length = 5
		msg.msg_type = DF2301Q_UART_MSG_TYPE_CMD_DOWN
		msg.msg_cmd = DF2301Q_UART_MSG_CMD_RESET_MODULE
		msg.msg_seq = self._send_sequence
		self._send_sequence += 1
		msg.msg_data[0] = 'r'
		msg.msg_data[1] = 'e'
		msg.msg_data[2] = 's'
		msg.msg_data[3] = 'e'
		msg.msg_data[4] = 't'

		self._send_packet(msg)
		time.sleep(3)


	def set_volume(self,  set_value):
		setting_CMD(self, DF2301Q_UART_MSG_CMD_SET_VOLUME, set_value)


	def set_mute_mode(self,  set_value):
		setting_CMD(self, DF2301Q_UART_MSG_CMD_SET_MUTE, set_value)


	def set_wake_time(self,  set_value):
		setting_CMD(self, DF2301Q_UART_MSG_CMD_SET_WAKE_TIME, set_value)


	def setting_CMD(self, set_type, set_value):
		'''!
			@brief Set commands of the module
			@param set_type - Set type
			@n			 DF2301Q_UART_MSG_CMD_SET_VOLUME : Set volume, the set value range 1-7
			@n			 DF2301Q_UART_MSG_CMD_SET_ENTERWAKEUP : Enter wake-up state; set value 0
			@n			 DF2301Q_UART_MSG_CMD_SET_MUTE : Mute mode; set value 1: mute, 0: unmute
			@n			 DF2301Q_UART_MSG_CMD_SET_WAKE_TIME : Wake-up duration; the set value range 0-255s
			@param set_value - Set value, refer to the set type above for the range
		'''
		msg = self.uart_msg()
		msg.header = DF2301Q_UART_MSG_HEAD
		msg.data_length = 5
		msg.msg_type = DF2301Q_UART_MSG_TYPE_CMD_DOWN
		msg.msg_cmd = DF2301Q_UART_MSG_CMD_SET_CONFIG
		msg.msg_seq = self._send_sequence
		self._send_sequence += 1
		msg.msg_data[0] = set_type
		msg.msg_data[1] = set_value

		self._send_packet(msg)

	def _send_packet(self, msg):
		'''
			@brief Write data through UART
			@param msg - Data packet to be sent
		'''
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
			data.append(msg.msg_data[i] & 0xFF)
			chk_sum += msg.msg_data[i]
		data.append(chk_sum & 0xFF)
		data.append((chk_sum >> 8) & 0xFF)
		data.append(DF2301Q_UART_MSG_TAIL & 0xFF)
		logger.info(data)
		self._ser.write(data)
		time.sleep(0.1)

	def _recv_packet(self):
		'''
			@brief Read data through UART
			@param msg - Buffer for receiving data packet
		'''
		msg = self.uart_msg()
		rev_state = self.REV_STATE_HEAD0
		receive_char = 0
		chk_sum = 0
		data_rev_count = 0
		while self._ser.in_waiting:
			receive_char = ord(self._ser.read(1))
			if(self.REV_STATE_HEAD0 == rev_state):
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
				rev_state = rev_state
				if(msg.data_length > 0):
					rev_state = self.REV_STATE_DATA
					data_rev_count = 0
				else:
					rev_state = self.REV_STATE_CKSUM0
			elif(self.REV_STATE_DATA == rev_state):
				msg.msg_data[data_rev_count] = receive_char
				data_rev_count += 1
				if(msg.data_length == data_rev_count):
					rev_state = self.REV_STATE_CKSUM0
			elif(self.REV_STATE_CKSUM0 == rev_state):
				chk_sum = receive_char
				rev_state = self.REV_STATE_CKSUM1
			elif(self.REV_STATE_CKSUM1 == rev_state):
				chk_sum += receive_char << 8

				rev_state = self.REV_STATE_TAIL
			elif(self.REV_STATE_TAIL == rev_state):
				if(DF2301Q_UART_MSG_TAIL == receive_char):
					if(DF2301Q_UART_MSG_TYPE_CMD_UP == msg.msg_type):
						self.uart_cmd_ID = msg.msg_data[0]
				else:
					data_rev_count = 0
				rev_state = self.REV_STATE_HEAD0
			else:
				rev_state = self.REV_STATE_HEAD0

		return data_rev_count


# ===========================================================================
# read params
# ===========================================================================

###############################
def readParams():
	global sensorList, sensors, logDir, sensor,	 displayEnable
	global deltaX, SENSOR, sensorsOld
	global oldRaw, lastRead
	global startTime, lastMeasurement, oldi2cOrUart, keepAwake, lastkeepAwake
	try:


		inp,inpRaw,lastRead2 = U.doRead(lastTimeStamp=lastRead)
		if inp == "": return
		if lastRead2 == lastRead: return
		lastRead	 = lastRead2
		if inpRaw == oldRaw: return
		oldRaw		 = inpRaw
		
		externalSensor=False
		sensorList=[]
		
		U.getGlobalParams(inp)
			
		if "sensorList"			in inp:	 sensorList=			 (inp["sensorList"])
		if "sensors"			in inp:	 sensors =				 (inp["sensors"])
		
 
		if sensor not in sensors:
			U.logger.log(30, "{} is not in parameters = not enabled, stopping {}.py".format(G.program,G.program) )
			exit()
			

		U.logger.log(10,"{} reading new parameters".format(G.program) )

		for devId in sensors[sensor]:

			restart = False
			i2cOrUart =  sensors[sensor][devId].get("i2cOrUart","i2c")	 
			if oldi2cOrUart != i2cOrUart:	restart = True 
			oldi2cOrUart = i2cOrUart

			upd = False
			if devId not in SENSOR or restart:
				upd = True
				startSensor(devId, i2cOrUart)
				if SENSOR[devId] == "":
					return

			if devId not in sensorsOld: upd= True

			keepAwake = sensors[sensor][devId].get("keepAwake") == "1"
			if keepAwake: sensors[sensor][devId]["setWakeTime"] = 255

			if "mute" in sensors[sensor][devId] and (upd or sensors[sensor][devId].get("mute") != sensorsOld[sensor][devId].get("mute")): 
				upd = True

			elif "volume" in sensors[sensor][devId] and (upd or sensors[sensor][devId].get("volume") != sensorsOld[sensor][devId].get("volume")) : 
				upd = True

			elif "setWakeTime" in sensors[sensor][devId] and (upd or sensors[sensor][devId].get("setWakeTime") != sensorsOld[sensor][devId].get("setWakeTime")) : 
				upd = True
				restart = True

			if upd: 
				refreshSetup(devIdx=devId, init=restart)
			if upd: U.logger.log(20,"setting mode:{} volume:{}, mute:{}, setWakeTime:{}, keep_awake:{}".format(i2cOrUart, sensors[sensor][devId].get("volume"), sensors[sensor][devId].get("mute"), sensors[sensor][devId].get("setWakeTime"), keepAwake) )

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
		U.logger.log(30, u"in Line {} has error={}".format(sys.exc_info()[-1].tb_lineno, e))
		U.logger.log(30, "{}".format(sensors[sensor]))
		


#################################
def refreshSetup(devIdx="", init=False):
	global lastkeepAwake, keepAwake, sensors, sensor, SENSOR
	try:
		if not keepAwake: return 
		#U.logger.log(20, "check if re awake : {:.1f}".format(time.time() -lastkeepAwake))
		if  time.time() - lastkeepAwake < 200: return 
		lastkeepAwake = time.time()
		for devId in SENSOR:
			if devIdx !="" and devIdx != devId: continue
			SENSOR[devId].set_mute_mode(1) 												# mute for startup
			if init or keepAwake:
				SENSOR[devId].set_wake_time(int(sensors[sensor][devId]["setWakeTime"])) # set  setWakeTime as desired
			SENSOR[devId].play_by_CMDID(1) 												# switch on listening
			SENSOR[devId].set_mute_mode(int(sensors[sensor][devId]["mute"])) 			# set  mute as desired
			SENSOR[devId].set_volume(int(sensors[sensor][devId]["volume"])) 			# set  volume as desired
			lastkeepAwake = time.time()
		U.logger.log(20, "awake reset")

	except Exception as e:
		U.logger.log(30, u"in Line {} has error={}".format(sys.exc_info()[-1].tb_lineno, e))

#################################
def startSensor(devId,i2cOrUart):
	global sensors,sensor
	global startTime
	global gasBaseLine, gasBurnIn
	global SENSOR
	startTime =time.time()
	
	try:
		ii = SENSOR[devId]
	except:
		try:
			time.sleep(0.5)
			if i2cOrUart == "uart":
				SENSOR[devId] = DFRobot_DF2301Q_UART()
			else:
				SENSOR[devId] = DFRobot_DF2301Q_I2C()

			U.logger.log(20, u"started sensor, version")
	
		except	Exception as e:
			U.logger.log(30, u"in Line {} has error={}".format(sys.exc_info()[-1].tb_lineno, e))
			SENSOR[devId] = ""
			return



#################################
def getValues(devId):
	global sensor, sensors,	 SENSOR, badSensor
	global keepAwake

	try:
		if SENSOR[devId] == "": 
			badSensor +=1
			return "badSensor"
		goodM = 0
		for ii in range(5):
			try:
				CMDID = SENSOR[devId].get_CMDID()
			except: return {"cmd":0}
			if keepAwake and CMDID == 1: continue
			if CMDID > 0: break
			time.sleep(0.1)

		if CMDID != 0: U.logger.log(20, "CMDID = {}".format(CMDID))
		
		data = {"cmd":CMDID}
		badSensor = 0
		return data
	except	Exception as e:
		U.logger.log(30, u"in Line {} has error={}".format(sys.exc_info()[-1].tb_lineno, e))
	badSensor += 1
	if badSensor > 5: return "badSensor"
	return ""





############################################
def execSensorLoop():
	global sensor, sensors, badSensor, sensorList
	global deltaX, SENSOR, sensorMode
	global oldRaw, lastRead
	global startTime, lastMeasurement
	global oldi2cOrUart, sensorsOld, keepAwake, lastkeepAwake

	lastkeepAwake				= 0
	keepAwake					= False
	oldi2cOrUart				= ""
	sensorsOld					= {}
	sendToIndigoSecs			= 80
	startTime					= time.time()
	lastMeasurement				= time.time()
	oldRaw						= ""
	lastRead					= 0
	loopCount					= 0
	sensorRefreshSecs			= 0.1
	sensorList					= []
	sensors						= {}
	sensor						= G.program
	quick						= False
	output						= {}
	badSensor					= 0
	SENSOR						= {}
	deltaX						= {}
	myPID						= str(os.getpid())
	U.setLogging()
	U.killOldPgm(myPID,G.program+".py")# kill old instances of myself if they are still running


	if U.getIPNumber() > 0:
		time.sleep(10)
		exit()

	readParams()

	time.sleep(1)

	lastRead = time.time()

	U.echoLastAlive(G.program)

	G.lastAliveSend		= time.time()

	sensorWasBad 		= False
	while True:
		try:
			extraSleep = 0
			tt = time.time()
			sendData = False
			data ={}
			if sensor in sensors:
				data = {"sensors": {sensor:{}}}
				for devId in sensors[sensor]:
					theValues = getValues(devId)
					if theValues == "": 
						continue

					data["sensors"][sensor][devId] = {}

					if theValues == "badSensor" or type(theValues) == type(" "):
						sensorWasBad = True
						data["sensors"][sensor][devId] = "badSensor"
						if badSensor < 5: 
							U.logger.log(30," bad sensor")
							U.sendURL(data)
						else:
							U.restartMyself(param="", reason="badsensor",doPrint=True,python3=True)
						continue
					elif theValues["cmd"] != 0:
						data["sensors"][sensor][devId] = theValues
						sendData = True
					if ( tt - abs(sendToIndigoSecs) > G.lastAliveSend	) or quick:
						sendData = True
			if sendData:
				U.sendURL(data)
				extraSleep = 0.5
			U.makeDATfile(G.program, data)

			loopCount += 1

			##U.makeDATfile(G.program, data)
			quick = U.checkNowFile(G.program)				 
			U.echoLastAlive(G.program)

			tt = time.time()
			if tt - lastRead > 2.:	
				readParams()
				lastRead = tt
				refreshSetup()
			time.sleep( max(0, (lastMeasurement + sensorRefreshSecs + extraSleep) - time.time() ) )
			lastMeasurement = time.time()

		except	Exception as e:
			U.logger.log(30, u"in Line {} has error={}".format(sys.exc_info()[-1].tb_lineno, e))
			time.sleep(5.)


G.pythonVersion = int(sys.version.split()[0].split(".")[0])
# output: , use the first number only
#3.7.3 (default, Apr	3 2019, 05:39:12) 
#[GCC 8.2.0]

execSensorLoop()
try: 	G.sendThread["run"] = False; time.sleep(1)
except: pass
sys.exit(0)


