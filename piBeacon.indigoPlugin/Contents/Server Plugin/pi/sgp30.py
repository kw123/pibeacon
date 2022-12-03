#!/usr/bin/python
# -*- coding: utf-8 -*-
# by Karl Wachs
# 2018-01-28
# version 0.1 
##
##
#! /usr/bin/env python
# -*- coding: utf-8 -*-
####################

import sys, os, time, json, datetime,subprocess,copy, struct
import math
import copy
import logging
import smbus
import threading

##sudo pip install sgp30

sys.path.append(os.getcwd())
import	piBeaconUtils	as U
import	piBeaconGlobals as G

G.program = "sgp30"


class SGP30_class:
	def __init__(self, i2c_dev=None, i2c_msg=None, address=0x58):
		"""Mapping table of SGP30 commands.

		Friendly-name, followed by 16-bit command,
		then the number of parameter and response words.

		Each word is two bytes followed by a third CRC
		checksum byte. So a response length of 2 would
		result in the transmission of 6 bytes total.
		"""
		self.commands = {
			'init_air_quality': (0x2003, 0, 0),
			'measure_air_quality': (0x2008, 0, 2),
			'get_baseline': (0x2015, 0, 2),
			'set_baseline': (0x201e, 2, 0),
			'set_humidity': (0x2061, 1, 0),
			'measure_test': (0x2032, 0, 1),  # Production verification only
			'get_feature_set_version': (0x202f, 0, 1),
			'measure_raw_signals': (0x2050, 0, 2),
			'get_serial_id': (0x3682, 0, 3)
		}

		self._i2c_addr =address
		self._i2c_dev = i2c_dev
		self._i2c_msg = i2c_msg
		if self._i2c_dev is None:
			from smbus2 import SMBus, i2c_msg
			self._i2c_msg = i2c_msg
			self._i2c_dev = SMBus(1)

	def command(self, command_name, parameters=None):
		if parameters is None:
			parameters = []
		parameters = list(parameters)
		cmd, param_len, response_len = self.commands[command_name]
		if len(parameters) != param_len:
			raise ValueError("{} requires {} parameters. {} supplied!".format(command_name,	param_len, len(parameters) ))

		parameters_out = [cmd]

		for i in range(len(parameters)):
			parameters_out.append(parameters[i])
			parameters_out.append(self.calculate_crc(parameters[i]))

		data_out = struct.pack('>H' + ('HB' * param_len), *parameters_out)

		msg_w = self._i2c_msg.write(self._i2c_addr, data_out)
		self._i2c_dev.i2c_rdwr(msg_w)
		time.sleep(0.025)  # Suitable for all commands except 'measure_test'

		if response_len > 0:
			# Each parameter is a word (2 bytes) followed by a CRC (1 byte)
			msg_r = self._i2c_msg.read(self._i2c_addr, response_len * 3)
			self._i2c_dev.i2c_rdwr(msg_r)

			buf = msg_r.buf[0:response_len * 3]

			response = struct.unpack(
				'>' + ('HB' * response_len),
				buf)

			verified = []
			for i in range(response_len):
				offset = i * 2
				value, crc = response[offset:offset + 2]
				if crc != self.calculate_crc(value):
					raise RuntimeError("Invalid CRC in response from SGP30: {:02x} != {:02x}", crc, self.calculate_crc(value), buf)
				verified.append(value)
			return verified

	def calculate_crc(self, data):
		"""Calculate an 8-bit CRC from a 16-bit word

		Defined in section 6.6 of the SGP30 datasheet.

		Polynominal: 0x31 (x8 + x5 + x4 + x1)
		Initialization: 0xFF
		Reflect input/output: False
		Final XOR: 0x00

		"""
		crc = 0xff  # Initialization value
		# calculates 8-Bit checksum with given polynomial
		for byte in [(data & 0xff00) >> 8, data & 0x00ff]:
			crc ^= byte
			for _ in range(8):
				if crc & 0x80:
					crc = (crc << 1) ^ 0x31  # XOR with polynominal
				else:
					crc <<= 1
		return crc & 0xff

	def get_unique_id(self):
		result = self.command('get_serial_id')
		return result[0] << 32 | result[1] << 16 | result[0]

	def get_feature_set_version(self):
		result = self.command('get_feature_set_version')[0]
		return (result & 0xf000) >> 12, result & 0x00ff

	def start_measurement(self):
		"""Start air quality measurement on the SGP30.

		The first 15 readings are discarded so this command will block for 15s.
		"""
		self.command('init_air_quality')
		while True:
			# Discard the initialisation readings as per page 8/15 of the datasheet
			eco2, tvoc = self.command('measure_air_quality')
			# The first 15 readings should return as 400, 0 so abort when they change
			if eco2 != 400 or tvoc != 0:
				break
			sys.stdout.write('.')
			sys.stdout.flush()
			time.sleep(1.0)

	def get_air_quality(self):
		"""Get an air quality measurement.

		Returns an instance of SGP30Reading with the properties equivalent_co2 and total_voc.

		This should be called at 1s intervals to ensure the dynamic baseline compensation on the SGP30 operates correctly.

		"""
		eco2, tvoc = self.command('measure_air_quality')
		return eco2, tvoc

	def get_baseline(self):
		"""Get the current baseline setting.

		Returns an instance of SGP30Reading with the properties equivalent_co2 and total_voc.

		"""
		eco2, tvoc = self.command('get_baseline')
		return eco2, tvoc

	def set_baseline(self, eco2, tvoc):
		self.command('set_baseline', [eco2, tvoc])


	def set_init_air_quality(self):
		self.command('init_air_quality')


	def testSensor(self):
		return self.command('measure_test')

 # ===========================================================================
# read params
# ===========================================================================

#################################		 
def readParams():
	global sensorList, sensors, sensor
	global rawOld
	global deltaX, sgp30, minSendDelta
	global oldRaw, lastRead
	global startTime, lastBaseLine
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
			U.logger.log(30, G.program+" is not in parameters = not enabled, stopping "+G.program+".py" )
			exit()
			

		U.logger.log(10, G.program+" reading new parameter file" )

		new = False
		for devId  in sensors[sensor]:
			if devId not in deltaX:  deltaX[devId] = 0
			old = deltaX[devId]
			try:
				if "deltaX" in sensors[sensor][devId]: 
					deltaX[devId] = float(sensors[sensor][devId]["deltaX"])/100.
				else:
					deltaX[devId] = 0.1
			except:
				deltaX[devId] = 0.1
			if old != deltaX[devId]: new = True

			old = minSendDelta 
			try:
				if "minSendDelta" in sensors[sensor][devId]: 
					minSendDelta = float(sensors[sensor][devId]["minSendDelta"])
				else:
					minSendDelta = 10
			except:
				minSendDelta = 5.
			if old != minSendDelta: new = True

				
			if devId not in sensorClass:
				lastBaseLine[devId] = time.time() - 21 
				lastInit    = U.readFloat("{}{}.lastInit".format(G.homeDir,G.program), default = 0)
				lastPowerUp =U.readFloat("{}masterStartAfterboot".format(G.homeDir), default = 0) 
				init		=U.readFloat("{}{}.lastInit".format(G.homeDir,G.program), default = 0)
				startSensor(devId, lastPowerUp=lastPowerUp, init=init)
				if sensorClass[devId] == "":
					return

			if new: 
				U.logger.log(30," new parameters read:  minSendDelta:{};  deltaX:{}".format(minSendDelta, deltaX[devId]) )
				
		deldevID={}		   
		for devId in sensorClass:
			if devId not in sensors[sensor]:
				deldevID[devId]=1
		for dd in  deldevID:
			del sensorClass[dd]
		if len(sensorClass) ==0: 
			####exit()
			pass


	except	Exception as e:
		U.logger.log(30,"", exc_info=True)
		print(sensors[sensor])
		


#################################
def startSensor(devId, lastPowerUp=0, init=0):
	global sensors,sensor
	global startTime
	global sensorClass
	global threadDict
	U.logger.log(30,"==== Start "+G.program+" ===== ")
	startTime =time.time()

	if devId not in threadDict:
		threadDict[devId] = { "state":"init","pause":False, "thread": threading.Thread(name=u'getValues', target=getValues, args=(devId,))}	

	try:
		sensorClass[devId]	=  SGP30_class()
		startSensor2(devId, lastPowerUp=lastPowerUp, init=init)
			
		if threadDict[devId]["state"] == "init":
			threadDict[devId]["thread"].start()
			U.logger.log(20, u"thread started")
		else:
			U.logger.log(20, u"threadDict already on")
		
		threadDict[devId]["state"] = "run"

	# dont do this!!! only at factory 
		#testSensor = sensorClass[devId].testSensor()
		#U.logger.log(30, "SGP30 sensortest   #{}".format(hex(testSensor) ) )
		#time.sleep(10)
	except	Exception as e:
		U.logger.log(30,"", exc_info=True)
		U.logger.log(20, u"****  startup sensor did not work ****")
		sensorClass[devId]  = ""
		threadDict[devId]["state"] = "stop"
	return 

#################################
def startSensor2(devId, lastPowerUp=0, init=0):
	global lastBaseLine
	global threadDict

	try:


		if init == -1:
			U.logger.log(20, "SGP30 : initializing = reset baseline" )
			if devId in threadDict:
				threadDict[devId]["pause"] = True
			delBaseLine()
			sensorClass[devId].set_init_air_quality()
			subprocess.call("echo {}> {}{}.lastInit".format(time.time(), G.homeDir, G.program), shell=True )
			time.sleep(12)
		else:
			try: 	lastReadSensor = U.readFloat("{}temp/{}.lastreadSensor".format(time.time(), G.homeDir,G.program),default=0)
			except: lastReadSensor = 0
			lastBaseLine[devId] = time.time()
			readBaseLine(devId)
			if devId in threadDict:
				threadDict[devId]["pause"] = True

			if time.time() - lastPowerUp > 60*60*2 and time.time() - lastReadSensor > 100: 
				sensorClass[devId].set_init_air_quality()
				if vocBase > 0 and co2Base > 0:
					U.logger.log(20, "SGP30 : setting baseline from file" )
					setBaseLine(devId)

		serialId = sensorClass[devId].get_unique_id()
		features = sensorClass[devId].get_feature_set_version()
		U.logger.log(20, "SGP30 serial    #{}".format(hex(serialId) ) )
		U.logger.log(20, "SGP30 featureset {}".format([hex(i) for i in  features] ) )
		time.sleep(1)
		warmUp(devId)

		if devId in threadDict :
			threadDict[devId]["pause"] = False


	except	Exception as e:
		U.logger.log(30,"", exc_info=True)
	time.sleep(.1)
	return 



#################################
def warmUp(devId):
	global sensors,sensor
	global startTime
	global sensorClass

	try:	
		for ii in range(30):
			co2, voc = sensorClass[devId].get_air_quality()
			if ii > 6 and (co2 > 400 or voc > 0) : break 
			if ii%4 == 0: U.logger.log(20, "try:{:2d} warmup values:   CO2= {}, VOC= {}".format(ii,co2, voc) )
			time.sleep(1)
		if ii < 29: U.logger.log(20,     "try:{:2d} warmup finished: CO2= {}, VOC= {}".format(ii,co2, voc) )
		else: 		U.logger.log(20,     "****    warmup NOT finished: CO2= {}, VOC= {}".format(co2, voc) )

	except	Exception as e:
		U.logger.log(30,"", exc_info=True)
		U.logger.log(20, "****    warmup NOT finished")
		sensorClass[devId]	 = ""


#################################
def getBaseLine(devId):
	global sensors,sensor
	global sensorClass, lastBaseLine
	global co2Base, vocBase
	try:	
		co2Base, vocBase= sensorClass[devId].get_baseline()
		U.logger.log(20, "**** baseline from sensor: CO2eq ={}, TVOC = {}".format(co2Base, vocBase) )
		if vocBase > 0 and co2Base > 0:
			U.writeJson(G.homeDir+G.program+".baseline", {"co2Base":co2Base, "vocBase":vocBase} )
	except	Exception as e:
		U.logger.log(30,"", exc_info=True)
		U.logger.log(20, "****    could not read baseline from device")
	return 

#################################
def readBaseLine(devId):
	global sensors,sensor
	global sensorClass, lastBaseLine
	global co2Base, vocBase
	try:
		try: 	
				if os.path.isfile(G.homeDir+G.program+".baseline"):
					lastUpdateTime = os.stat(G.homeDir+G.program+".baseline").st_mtime
				else:
					lastUpdateTime  = time.time() -(24*60*60)*99
		except	Exception as e:
				lastUpdateTime = time.time() -(24*60*60)*99
		if time.time() - lastUpdateTime > (24*60*60)*2: 
			U.logger.log(20, "**** baseline file too old to be used: {:.1f} days or older".format( (time.time() - lastUpdateTime)/(24*60*60) ) )
			return 
		data, raw = U.readJson(G.homeDir+G.program+".baseline")
		if raw != "" and "co2Base" in data and "vocBase" in data:
			if data["co2Base"] > 10 and  data["vocBase"] > 10:
				U.logger.log(20, "**** baseline read from file: {}".format(data) )
				co2Base = data["co2Base"]
				vocBase = data["vocBase"]
			else:
				U.logger.log(20, "**** baseline read from file:  NOT mature yet (co2Base  < 10)" )

	except	Exception as e:
		U.logger.log(30,"", exc_info=True)
	return 

#################################
def delBaseLine():
	subprocess.call("rm "+G.homeDir+G.program+".baseline > /dev/null 2>&1", shell=True)
	return 

#################################
def setBaseLine(devId):
	global sensors,sensor
	global sensorClass, lastBaseLine
	global co2Base, vocBase
	try:	
		U.logger.log(20, "setting baseline to : CO2eq ={}, TVOC = {}".format(co2Base, vocBase) )
		sensorClass[devId].set_baseline(co2Base, vocBase)
	except	Exception as e:
		U.logger.log(30,"", exc_info=True)



#################################
def getValues(devId):
	global sensor, sensors,	 sensorClass, badSensor
	global startTime
	global threadDict
	global lastBaseLine
	global lastCO2, lastVOC
	global deltaX
	global quick
	global minSendDelta

	lastValues0			= {"CO2":0,	 "VOC":0}
	deltaMin			= {"CO2":5,	 "VOC":5}
	lastValues			= {}
	lastValues2			= {}
	lastData			= {}
	lastSend			= 0
	loopCount 			= 0
	badSensor 			= 0
	sensorWasBad		= False
	G.lastAliveSend		= time.time() - 1000
	lastRead			= time.time() - 0.9
	values 				= ""
	data 				= {}
	sendData			= False

	while True:
		try:
			if sensorClass[devId] == "": return

			for jj in range(200):
				if threadDict[devId]["state"] == "run": break
				if threadDict[devId]["state"] == "stop": 
					sensorClass[devId] = ""
					return
				time.sleep(1)

			for jj in range(200):
				if not threadDict[devId]["pause"] : break
				time.sleep(1)

			data = {"sensors": {sensor:{}}}
			sendData = False
			if sensor in sensors:
				for devId in sensors[sensor]:
					if devId not in lastValues: 
						lastValues[devId]  =copy.copy(lastValues0)
						lastValues2[devId] =copy.copy(lastValues0)
					try:
						if time.time() - lastBaseLine[devId] > 2000:
							lastBaseLine[devId] = time.time()
							getBaseLine(devId)
						CO2	 = 0.
						VOC	 = 0.
						n	 = 0
						#U.logger.log(20, u"into getValues")
						for ii in range(20):
						
							time.sleep(max (0, 0.975 - (time.time()-lastRead) ) )
							if threadDict[devId]["state"] != "run":  break
							if threadDict[devId]["pause"] :  break
							try:
								co2eq, tvoc = sensorClass[devId].get_air_quality()
								#U.logger.log(20,"co2eq:{}, tvoc:{},  delta time: {:.2f}".format(co2eq, tvoc,time.time()-lastRead ))
								lastRead = time.time()
							except Exception as e:
								U.logger.log(20,"", exc_info=True)
								time.sleep(1)
								continue
							if co2eq > 0:
								CO2 += co2eq
								VOC += tvoc
								n	+= 1.
								U.logger.log(20,"lastCO2:{}, lastVOC:{}, n:{}, ii:{}, co2eq:{}, tvoc:{}, CO2/n:{}, VOC/n:{}".format(lastCO2, lastVOC, n, ii, co2eq, tvoc, CO2/n, VOC/n))
								if n > 6: break
						if CO2 == 0 or n ==0: 
							 badSensor+=1
						elif CO2/n > 59999 or VOC/n > 59999: 
							startSensor2(devId, init=-1)
							continue
						else:	 
							lastCO2 =  CO2/n
							lastVOC =  VOC/n
							values	 = {"CO2": int(CO2/n), "VOC":int(VOC/n)}
							badSensor = 0
					except	Exception as e:
						U.logger.log(30,"", exc_info=True)
						badSensor+=1
					if badSensor >3: values = "badSensor"

					if values == "": continue
					data["sensors"][sensor][devId]={}
					if values =="badSensor":
						sensorWasBad = True
						data["sensors"][sensor][devId]="badSensor"
						if badSensor < 5: 
							U.sendURL(data)
							U.logger.log(20," bad sensor ... try again ")
							time.sleep(1)
						else:
							U.restartMyself(param="", reason="badsensor",doPrint=True)
						lastValues2[devId] =copy.copy(lastValues0)
						lastValues[devId]  =copy.copy(lastValues0)
						continue
					elif values["CO2"] != "":
						if sensorWasBad: # sensor was bad, back up again, need to do a restart to set config 
							time.sleep(10)
							U.restartMyself(reason=" back from bad sensor, need to restart to get sensors reset",doPrint=False)
					
						data["sensors"][sensor][devId] = values
						deltaN =0
						for xx in lastValues0:
							try:
								current = float(values[xx])
								delta= abs(current-lastValues2[devId][xx])
								if delta < deltaMin[xx]: continue
								delta  /=  max (0.5,(current+lastValues2[devId][xx])/2.)
								deltaN = max(deltaN,delta) 
								lastValues[devId][xx] = current
							except: pass
						subprocess.call("echo {:.0f} > {}temp/{}.lastreadSensor".format(time.time(), G.homeDir,G.program), shell=True)
					else:
						continue
					if (  ( ( deltaN > deltaX[devId]  ) or  ( time.time() - abs(G.sendToIndigoSecs) > G.lastAliveSend ) or  quick   ) and  ( time.time() - G.lastAliveSend > minSendDelta ) ):
						sendData = True
						lastValues2[devId] = copy.copy(lastValues[devId])
						

			if sendData:
				U.logger.log(20,"spg30:{}".format(data))
				U.sendURL(data)
				quick = False
			loopCount +=1

		except Exception as e:
			U.logger.log(30,"", exc_info=True)
			badSensor +=1
	sensorClass[devId] = ""
	return 





############################################
global rawOld
global sensor, sensors, badSensor
global deltaX, sensorClass, minSendDelta
global lastRead
global startTime,  lastBaseLine
global lastCO2, lastVOC
global co2Base, vocBase
global threadDict
global quick

threadDict					= {}
lastBaseLine				= {}
co2Base						= -1
vocBase						= -1

lastCO2						= 0
lastVOC						= 0

startTime					= time.time()
oldRaw						= ""
lastRead					= 0
minSendDelta				= 5.
loopCount					= 0
sensorList					= []
sensors						= {}
sensor						= G.program
quick						= False
badSensor					= 0
sensorActive				= False
loopSleep					= 0.5
rawOld						= ""
sensorClass					= {}
deltaX						= {}
loopSleep 					= 1.

U.setLogging()

myPID		= str(os.getpid())
U.killOldPgm(myPID,G.program+".py")# kill old instances of myself if they are still running


if U.getIPNumber() > 0:
	time.sleep(10)
	exit()

readParams()

time.sleep(1)

lastRead = time.time()

U.echoLastAlive(G.program)


while True:
	try:
		time.sleep(loopSleep)
		loopCount +=1

		##U.makeDATfile(G.program, data)
		quick = U.checkNowFile(G.program)	
		if quick: sleep(5)			 
		U.echoLastAlive(G.program)

		if U.checkNewCalibration(G.program):
			U.logger.log(20, u"starting with new init")
			for devId in lastBaseLine:
				startSensor2(devId, init=-1)

			for devId in threadDict:
				if threadDict[devId]["state"] == "stop": break

		if loopCount %5 ==0 and not quick:
			if time.time() - lastRead > 5.:	 
				readParams()
				lastRead = time.time()

	except	Exception as e:
		U.logger.log(30,"", exc_info=True)
		time.sleep(5.)

try: 	G.sendThread["run"] = False; time.sleep(2)
except: pass
sys.exit(0)
 

		