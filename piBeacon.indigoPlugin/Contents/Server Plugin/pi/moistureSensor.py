#! /usr/bin/env python3
# -*- coding: utf-8 -*-
####################
# fixed  2020-04-06:	 except Exception >>> as e<<< : was missing in several lines, only happens when error occures

import sys, os, time, json, datetime,subprocess,copy
import smbus
import math
import time



sys.path.append(os.getcwd())
import	piBeaconUtils	as U
import	piBeaconGlobals as G

G.program = "moistureSensor"



###############################
###############################
class MoistureChirp:
	def __init__(self,  address=0x20):

		"""Initializes a Chirp moisture sensor wrapper: opens SMBus 1, sends a wake-up read to the device, and reads the firmware version register into self.version. Logs and ignores errors.

		Inputs:
		    address (int): I2C address of the sensor (default 0x20, though overridden to 0x20 internally)
		Outputs:
		    None: sets self.version, self.address, self.bus; reads from I2C
		"""
		try:
			self.version = 0
			import smbus
			self.address = 0x20
			self.bus = smbus.SMBus(1)
			time.sleep(0.1)
			#send wake up , need to wait after
			self.bus.read_byte_data(self.address, 0x07) 
			time.sleep(1)
			self.version = self.bus.read_byte_data(self.address, 0x07) 

			# don't do a reset 
			#time.sleep(0.1)
			#self.bus.write_byte(self.address, 0x06) # reset

			time.sleep(1)
		except Exception as e:
			U.logger.log(20, "in Line {} has error={}".format(sys.exc_info()[-1].tb_lineno, e))
		return 

	def getVersion(self): 
		"""Returns the firmware version of the Chirp moisture sensor that was read during initialization.

		Inputs:
		    None.
		Outputs:
		    int: the sensor's firmware version value
		"""
		return self.version

	def getdata(self, moisture=True, temp=True, Illuminance=True): 
		"""Reads moisture, temperature, and/or illuminance from the Chirp sensor over I2C, polling a busy register and byte-swapping each 16-bit word, returning a dict with the requested values (defaulting to -99 for unread/failed readings).

		Inputs:
		    moisture (bool): whether to read the moisture value
		    temp (bool): whether to read the temperature value
		    Illuminance (bool): whether to read the illuminance value
		Outputs:
		    dict: {'temp':..., 'Illuminance':..., 'moisture':...} with sensor readings or -99 defaults
		"""
		retData={"temp":-99, "Illuminance":-99, "moisture":-99}
		try:
			if temp:
				for ii in range(20):
					if not self.bus.read_byte_data(self.address, 0x09): 
						time.sleep(0.05)
						ret = self.bus.read_word_data(self.address, 0x05)
						retData["temp"] =  ((ret & 0xFF) << 8) + (ret >> 8)
						break 
		except Exception as e:
			U.logger.log(20, "in Line {} has error={} temp ".format(sys.exc_info()[-1].tb_lineno, e))

		try:
			if moisture:
				for ii in range(20):
					if not self.bus.read_byte_data(self.address, 0x09): 
						time.sleep(0.05)
						ret = self.bus.read_word_data(self.address, 0x00)
						retData["moisture"] = ((ret & 0xFF) << 8) + (ret >> 8) 
						break 
		except Exception as e:
			U.logger.log(20, "in Line {} has error={} moisture ".format(sys.exc_info()[-1].tb_lineno, e))

		try:
			if Illuminance:
				il = 0
				for kk in range(3):
					for ii in range(20):
						self.bus.write_byte(self.address, 0x03)
						if not self.bus.read_byte_data(self.address, 0x09): 
							time.sleep(0.05)
							ret = self.bus.read_word_data(self.address, 0x04)
							il = ((ret & 0xFF) << 8) + (ret >> 8) 
							break 
					if il != 0: break
					time.sleep(1)
				retData["Illuminance"] = il 
		except Exception as e:
			U.logger.log(20, "in Line {} has error={} Illuminance ".format(sys.exc_info()[-1].tb_lineno, e))

		return retData
# ===========================================================================
# read params
# ===========================================================================

###############################
def readParams():
	"""Reads the plugin's parameter/config file and updates global moisture-sensor settings (sensors, deltaX, sensorMode, minSendDelta, I2C address) for each configured device, (re)starting the sensor when settings change and removing devices no longer present.

	Inputs:
	    None.
	Outputs:
	    None: updates module globals and starts sensors; logs errors
	"""
	global sensorList, sensors, logDir, sensor,	 sensorRefreshSecs, displayEnable
	global deltaX, SENSOR, minSendDelta, sensorMode
	global oldRaw, lastRead
	global startTime, lastMeasurement, sendToIndigoSecs
	try:



		inp, inpRaw, lastRead2 = U.doRead(lastTimeStamp=lastRead)
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
			U.logger.log(20, "{} is not in parameters = not enabled, stopping {}.py".format(G.program,G.program) )
			exit()
			

		U.logger.log(10,"{} reading new parameters".format(G.program) )

		deltaX={}
		restart = False
		sendToIndigoSecs = G.sendToIndigoSecs	
		for devId in sensors[sensor]:
	

			old = U.getI2cAddress(sensors[sensor][devId], default ="")
			try:
				if "i2cAddress" in sensors[sensor][devId]:
					i2cAddress = int(sensors[sensor][devId]["i2cAddress"])
			except:
				i2cAddress = 119	   
			if old != i2cAddress:  restart = True 

			try:
				if devId not in deltaX: deltaX[devId]  = 0.1
				if "deltaX" in sensors[sensor][devId]: 
					deltaX[devId]= float(sensors[sensor][devId]["deltaX"])/100.
			except:
				deltaX[devId] = 0.1

			try:
				if devId not in sensorMode: sensorMode[devId]  = "" # chirp or adafruit
				if "sensorMode" in sensors[sensor][devId]: 
					sensorMode[devId]= sensors[sensor][devId]["sensorMode"]
			except:
				sensorMode[devId] = "chirp-2.7"

			try:
				if "minSendDelta" in sensors[sensor][devId]: 
					minSendDelta= float(sensors[sensor][devId]["minSendDelta"])
			except:
				minSendDelta = 5.

				
			if devId not in SENSOR or  restart:
				U.logger.log(20," new parameters read: i2cAddress:{}; minSendDelta:{};  deltaX:{}; sensorRefreshSecs:{}, sensorMode:{}".format(i2cAddress, minSendDelta, deltaX[devId], sensorRefreshSecs, sensorMode[devId]) )
				startSensor(devId, i2cAddress)
				if SENSOR[devId] =="":
					return
		deldevID={}		   
		for devId in SENSOR:
			if devId not in sensors[sensor]:
				deldevID[devId]=1
		for dd in  deldevID:
			del SENSOR[dd]
		if len(SENSOR) ==0: 
			####exit()
			pass



	except Exception as e:
		U.logger.log(20, "in Line {} has error={}".format(sys.exc_info()[-1].tb_lineno, e))
		U.logger.log(20, "{}".format(sensors[sensor]))
		


#################################
def startSensor(devId,i2cAddress):
	"""Initializes the moisture sensor for a given device by configuring the I2C mux and, if not already started, creating either an Adafruit Seesaw sensor or a MoistureChirp sensor (per sensorMode) at the given I2C address, storing it in the SENSOR global and resetting the mux afterward.

	Inputs:
	    devId (str): Indigo device identifier
	    i2cAddress (int): I2C address of the moisture sensor
	Outputs:
	    None: creates sensor object in SENSOR global; resets mux; logs errors
	"""
	global sensors,sensor
	global startTime
	global gasBaseLine, gasBurnIn
	global SENSOR, i2c_bus
	startTime =time.time()

	i2cAdd = U.muxTCA9548A(sensors[sensor][devId]) # switch mux on if requested and use the i2c address of the mix if enabled
	
	try:
		ii = SENSOR[devId]
	except:
		try:
			time.sleep(1)
			if sensorMode[devId]== "adafruit":
				from board import SCL, SDA
				import busio
				from adafruit_seesaw.seesaw import Seesaw
				i2c_bus = busio.I2C(SCL, SDA)
				SENSOR[devId]  = Seesaw(i2c_bus, addr=i2cAddress)

			elif sensorMode[devId].find("chirp") >-1:
				SENSOR[devId] = MoistureChirp(address=i2cAddress)
				v = SENSOR[devId].getVersion()
				U.logger.log(20, "started chirp sensor, version={}".format(v) )
	
		except Exception as e:
			U.logger.log(20, "in Line {} has error={}".format(sys.exc_info()[-1].tb_lineno, e))
			SENSOR[devId] = ""
			U.muxTCA9548Areset()
			return
	U.muxTCA9548Areset()



#################################
def getValues(devId):
	"""Reads a moisture/soil sensor for one device, taking 10 samples at 0.2s intervals, discarding outliers, and averaging temperature, moisture, and illuminance; applies a temperature offset and returns rounded values. Supports adafruit, chirp-2.7, and default sensor modes, and returns a bad-sensor marker after repeated failures.

	Inputs:
	    devId (str): device id key into the sensors/SENSOR dictionaries
	Outputs:
	    dict or str: dict with temp/Illuminance/moisture, or 'badSensor', or empty string on error
	"""
	global sensor, sensors,	 SENSOR, badSensor
	global startTime, sendToIndigoSecs, sensorMode

	try:
		if SENSOR[devId] == "": 
			badSensor +=1
			return "badSensor"

		temp		 = 0.
		moisture	 = 0.
		Illuminance	 = 0.
		tempL		 = [-1000*ii for ii in range(5)]
		moistureL	 = [-1000*ii for ii in range(5)]
		IlluminanceL = [-1000*ii for ii in range(5)]
		i2cAdd = U.muxTCA9548A(sensors[sensor][devId]) # switch mux on if requested and use the i2c address of the mix if enabled

		# take the average of  measurments every 0.2 secs
		goodM = 0
		for ii in range(10):
			time.sleep(0.2)
			if sensorMode[devId] == "adafruit":
				tempL[goodM]  		= SENSOR[devId].get_temp()
				moistureL[goodM]	= SENSOR[devId].moisture_read()

			elif sensorMode[devId] == "chirp-2.7":
				dataFromSens  = SENSOR[devId].getdata(moisture=True, temp=True, Illuminance=True)
				if dataFromSens["moisture"] == -99: return "badSensor"
				tempL[goodM]  		=  dataFromSens["temp"]/10.
				IlluminanceL[goodM] =  dataFromSens["Illuminance"]
				moistureL[goodM]	=  dataFromSens["moisture"]
			else:
				dataFromSens  = SENSOR[devId].getdata(moisture=True, temp=False, Illuminance=False)
				if dataFromSens["moisture"] == -99: return "badSensor"
				tempL[goodM]  		=  dataFromSens["temp"]/10.
				IlluminanceL[goodM] =  dataFromSens["Illuminance"]
				moistureL[goodM]	=  dataFromSens["moisture"]
			goodM +=1
			if goodM > 4: break
		tempL 		 = sorted(tempL)[1:4]; 			tc =0
		IlluminanceL = sorted(IlluminanceL)[1:4];	mc= 0
		moistureL	 = sorted(moistureL)[1:4];		ic =0

		for ii in range(3):
			if moistureL[ii] > -99:		moisture 		+= moistureL[ii]; 		mc += 1.
			if tempL[ii] > -99:			temp 			+= tempL[ii]; 			tc += 1.
			if IlluminanceL[ii] > -99:	Illuminance		+= IlluminanceL[ii]; 	ic += 1.
		
		temp 		= temp/max(1.,tc) + float(sensors[sensor][devId]["offsetTemp"]) 
		moisture 	= moisture/max(1.,mc)
		Illuminance = Illuminance/max(1.,ic)

		data = {"temp":	round(temp,1), 
		 "Illuminance":	round(Illuminance,0),
			"moisture":	round(moisture,0)} 
		#print (tempL, IlluminanceL, moistureL, data)
		badSensor = 0
		return data
	except Exception as e:
		U.logger.log(20, "in Line {} has error={}".format(sys.exc_info()[-1].tb_lineno, e))
	badSensor += 1
	if badSensor > 5: return "badSensor"
	return ""





############################################
def execMoistureSensor():
	"""Main daemon loop for the moisture sensor process: initializes globals, kills old instances, reads parameters, then repeatedly polls each configured device via getValues, sends data to Indigo when values change beyond a delta or on a heartbeat interval, writes DAT files, and refreshes parameters periodically.

	Inputs:
	    None.
	Outputs:
	    None: runs an infinite loop sending sensor data to Indigo and writing files/logs
	"""
	global sensor, sensors, badSensor, sensorList
	global deltaX, SENSOR, minSendDelta, sensorMode
	global oldRaw, lastRead
	global startTime, sendToIndigoSecs, sensorRefreshSecs, lastMeasurement

	sensorMode					= {}
	sendToIndigoSecs			= 80
	startTime					= time.time()
	lastMeasurement				= time.time()
	oldRaw						= ""
	lastRead					= 0
	minSendDelta				= 5.
	loopCount					= 0
	sensorRefreshSecs			= 9
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

	firstValue			= True


	lastValues0			= {"moisture":0,"temp":0, "Illuminance":0}
	lastValues			= {}
	lastValues2			= {}
	lastData			= {}
	lastSend			= 0
	G.lastAliveSend		= time.time()

	sensorWasBad 		= False
	while True:
		try:
			tt = time.time()
			sendData = False
			data ={}
			if sensor in sensors:
				data = {"sensors": {sensor:{}}}
				for devId in sensors[sensor]:
					if devId not in lastValues: 
						lastValues[devId]  =copy.copy(lastValues0)
						lastValues2[devId] =copy.copy(lastValues0)
					values = getValues(devId)
					if values == "": 
						continue

					data["sensors"][sensor][devId]={}
					if values == "badSensor":
						sensorWasBad = True
						data["sensors"][sensor][devId]="badSensor"
						if badSensor < 5: 
							U.logger.log(20," bad sensor")
							U.sendURL(data)
						else:
							U.restartMyself(param="", reason="badsensor",doPrint=True,python3=True)
						lastValues2[devId] =copy.copy(lastValues0)
						lastValues[devId]  =copy.copy(lastValues0)
						continue
					elif values["moisture"] !="" :
					
						data["sensors"][sensor][devId] = values
						deltaN =0
						for xx in lastValues0:
							try:
								current = float(values[xx])
								delta	= current-lastValues2[devId][xx]
								delta  /=  max (0.5,(current+lastValues2[devId][xx])/2.)
								deltaN	= max(deltaN,abs(delta) )
								lastValues[devId][xx] = current
							except: pass
					else:
						continue
					if (   ( deltaN > deltaX[devId]	 ) or  (  tt - abs(sendToIndigoSecs) > G.lastAliveSend  ) or quick ) and  ( tt - G.lastAliveSend > minSendDelta ):
						sendData = True
						lastValues2[devId] = copy.copy(lastValues[devId])
						firstValue = False
			if sendData:
				U.sendURL(data)
			U.makeDATfile(G.program, data)

			loopCount +=1

			##U.makeDATfile(G.program, data)
			quick = U.checkNowFile(G.program)				 
			U.echoLastAlive(G.program)

			tt= time.time()
			if tt - lastRead > 5.:	
				readParams()
				lastRead = tt
			time.sleep( max(0, (lastMeasurement+sensorRefreshSecs) - time.time() ) )
			lastMeasurement = time.time()

		except Exception as e:
			U.logger.log(20, "in Line {} has error={}".format(sys.exc_info()[-1].tb_lineno, e))
			time.sleep(5.)


G.pythonVersion = int(sys.version.split()[0].split(".")[0])
# output: , use the first number only
#3.7.3 (default, Apr  3 2019, 05:39:12) 
#[GCC 8.2.0]

execMoistureSensor()
try: 	G.sendThread["run"] = False; time.sleep(1)
except: pass
sys.exit(0)
