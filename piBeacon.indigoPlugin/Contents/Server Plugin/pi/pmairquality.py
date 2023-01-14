#! /usr/bin/env python
# -*- coding: utf-8 -*-
####################

# karl wachs 2018-04-21
#  copied pieces of code from various sources (adafruit, githubs ... )
#  most posted codes had issues and did not run completely #
#
#  this will read a PMS5003
#	connect +5V (not 3.3) ground and RX on the RPI	 to	  +5V GND TX on the sensor
#
#


import sys, os, time, json, subprocess,copy


sys.path.append(os.getcwd())
import	piBeaconUtils	as U
import	piBeaconGlobals as G

G.program = "pmairquality"


import serial 
import struct

import RPi.GPIO as GPIO
GPIO.setwarnings(False)
GPIO.setmode(GPIO.BCM)

startBytes	= bytearray(b'\x42\x4d')
checksum0	= sum(startBytes)

class thisSensorClass:
	def __init__(self,	serialPort="/dev/ttyAMA0"):

		self.ser			= serial.Serial()
		self.ser.port		= serialPort 
		self.ser.stopbits	= serial.STOPBITS_ONE
		self.ser.bytesize	= serial.EIGHTBITS
		self.ser.baudrate	= 9600
		self.ser.timeout	= 1
		self.ser.open()
		U.logger.log(20,"thisSensorClass started,  params:{}".format( self.ser))

	def getData(self): 
		debugPrint 				= G.debug
		data					= ""
		rawData					= ""
		startBytesIndex 		= 0
		maxWaitTimeForStartByte	= 5
		acumValues 				= [0 for kk in range(15)]
		nMeasurements 			= 0
		delayBetweenReads 		= 1
		nTries 					= 3
		totStartTime 			= time.time()
		try:
			for ii in range(nTries):
				if ii > 0: 
					time.sleep(delayBetweenReads)
				self.ser.flushInput()
				findStartCounter = 0
				startTimeFindStartByte = time.time()
				startByteFound = False

				while True:
					if time.time() - startTimeFindStartByte > maxWaitTimeForStartByte:
						if ii > 0:
							U.logger.log(20,"Timeout: start of package not found after {} secs".format(maxWaitTimeForStartByte))
						break

					findStartCounter +=1
					#U.logger.log(20,"ntry:{}, findStartCounter:{}".format(ii, findStartCounter))
					isStartByte = self.ser.read(1)
					try:	
						if type(isStartByte) is bytes: isStartByte = ord(isStartByte)
					except:	
						U.logger.log(20, "empty read")
						continue
					if isStartByte == bytearray(b'\x42\x4d')[startBytesIndex]:
						if startBytesIndex == 0:
							startBytesIndex = 1
						elif startBytesIndex == 1:
							startByteFound = True
							break # found 
					else:
						startBytesIndex = 0

				if not startByteFound: continue

				data = bytearray(self.ser.read(2))  # Get frame length packet
				if len(data) != 2:
					U.logger.log(20, "Could not find length packet")
					continue

				checksum1 	= sum(bytearray(b'\x42\x4d')) + sum(data)
				frameLength = struct.unpack(">H", data)[0]

				rawData = bytearray(self.ser.read(frameLength))
				if len(rawData) != frameLength:
					U.logger.log(20, "Invalid frame length. Got {} bytes, expected {}.".format(len(rawData), frameLength))
					continue

				allDecodedData = struct.unpack(">HHHHHHHHHHHHHH", rawData)
				checksum1 += sum(rawData[:-2])
				checksum2 = allDecodedData[13] 
				# Don't include the checksum bytes in the checksum calculation
				if checksum1 != checksum2:
					U.logger.log(20,  "bad checksum: 1:{}, 2:{}".format(checksum1, checksum2) )
					continue
				for kk in range(len(allDecodedData)):
					acumValues[kk] += allDecodedData[kk]
				nMeasurements += 1
				if debugPrint > 2: U.logger.log(20,  "nread:{:}, findStartCounter:{:2d}, dt:{:.2f}, valuesread:{:}".format(nMeasurements, findStartCounter, time.time() - startTimeFindStartByte, allDecodedData) )

			if nMeasurements == 0: 
				return "badSensor"

			for kk in range(len(acumValues)):
				acumValues[kk] = int(round(acumValues[kk]/ max(1.,nMeasurements),0))

			totStartTime = round( (time.time() - totStartTime), 3)

			if debugPrint	> 2: # debug  
				U.logger.log(20,  "---------------------------------------" )
				U.logger.log(20,  "data nMeasurements:{}, totReadtime:{}".format(nMeasurements, totStartTime) )
				U.logger.log(20,  "Concentration Units (standard)" )
				U.logger.log(20,  "PM 1.0: {}\tPM2.5: {}\tPM10: {}".format(acumValues[0], acumValues[1], acumValues[2]) )
				U.logger.log(20,  "---------------------------------------" )
				U.logger.log(20,  "Concentration Units (environmental)" )
				U.logger.log(20,  "PM 1.0: {}\tPM2.5: {}\tPM10: {}".format(acumValues[3], acumValues[4], acumValues[5]) )
				U.logger.log(20,  "---------------------------------------" )
				U.logger.log(20,  "Particle size  Count" )
				U.logger.log(20,  " > 0.3um / 0.1L air:{}".format( acumValues[6] ))
				U.logger.log(20,  " > 0.5um / 0.1L air:{}".format( acumValues[7] ))
				U.logger.log(20,  " > 1.0um / 0.1L air:{}".format( acumValues[8] ))
				U.logger.log(20,  " > 2.5um / 0.1L air:{}".format( acumValues[9] ))
				U.logger.log(20,  " > 5.0um / 0.1L air:{}".format( acumValues[10] ))
				U.logger.log(20,  " > 10 um / 0.1L air:{}".format( acumValues[11] ))
				U.logger.log(20,  "---------------------------------------" )
			return acumValues

		except	Exception as e:
			U.logger.log(30,"", exc_info=True)
		U.logger.log(30, " bad read, .. len{}   receivedCharacters:{}".format(len(rawData), rawData))
		return "badSensor"



 # ===========================================================================
# read params
# ===========================================================================

#################################		 
def readParams():
	global sensorList, sensors,  sensor,	 sensorRefreshSecs
	global deltaX, minSendDelta
	global oldRaw, lastRead
	global startTime
	global resetPin
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
			U.logger.log(30, G.program+" is not in parameters = not enabled, stopping BME680.py" )
			exit()
			

		U.logger.log(20, G.program+" reading new parameter file" )


 

		if sensorRefreshSecs == 91:
			try:
				xx	   = str(inp["sensorRefreshSecs"]).split("#")
				sensorRefreshSecs = float(xx[0]) 
			except:
				sensorRefreshSecs = 91	  
		doReset = False
		for devId in sensors[sensor]:
			if devId not in deltaX:
				deltaX[devId]  = 0.15

			oldresetPin = copy.copy(resetPin)
			if "resetPin" in sensors[sensor][devId]: resetPin[devId] = sensors[sensor][devId]["resetPin"]
			if devId in resetPin and (devId not in oldresetPin or oldresetPin[devId] != resetPin[devId]):
				doReset = True

			old = sensorRefreshSecs
			try:
				if "sensorRefreshSecs" in sensors[sensor][devId]:
					xx = sensors[sensor][devId]["sensorRefreshSecs"].split("#")
					sensorRefreshSecs = float(xx[0]) 
			except:
				sensorRefreshSecs = 12	  
			if old != sensorRefreshSecs: doReset = True
			

			old = deltaX[devId]
			try:
				if "deltaX" in sensors[sensor][devId]: 
					deltaX[devId] = float(sensors[sensor][devId]["deltaX"])/100.
			except:
				deltaX[devId] = 0.15
			if old != deltaX[devId]: doReset = True

			old = minSendDelta
			try:
				if "minSendDelta" in sensors[sensor][devId]: 
					minSendDelta= float(sensors[sensor][devId]["minSendDelta"])
			except:
				minSendDelta = 5.
			if old != minSendDelta: doReset = True


			if devId not in thisSensor:
				startSensor(devId)
				resetSensor(devId=devId)
				if thisSensor[devId] == "":
					return

			if  doReset:
				resetSensor(devId=devId)

			U.logger.log(20," new parameters read: minSendDelta:{},   deltaX:{},  sensorRefreshSecs:{},".format(minSendDelta, deltaX[devId], sensorRefreshSecs) )


				
		deldevID = {}
		for devId in thisSensor:
			if devId not in sensors[sensor]:
				deldevID[devId]=1
		for dd in  deldevID:
			U.logger.log(20,"removing devId from sensorlist:{}".format(dd) )
			del thisSensor[dd]

		if len(thisSensor) == 0: 
			U.logger.log(20,"empty sensorlist, exiting")
			exit()

	except	Exception as e:
		U.logger.log(30,"", exc_info=True)
		U.logger.log(30,"{}".format(sensors[sensor]) )
		



#################################
def startSensor(devId):
	global sensors,sensor
	global startTime
	global thisSensor, firstValue
	U.logger.log(30,"==== Start {} =====  for devId:{}".format(G.program, devId))
	startTime =time.time()
 
	try:
		sP = U.getSerialDEV() 
		thisSensor[devId]  = thisSensorClass(serialPort = sP)
		
	except	Exception as e:
		U.logger.log(30,"", exc_info=True)
		thisSensor[devId] =""
	return


#################################
def getValues(devId):
	global sensor, sensors,	 thisSensor, badSensor
	global startTime
	try:
		if thisSensor[devId] == "": 
			badSensor +=1
			return "badSensor"

		resetSensor(devId=devId)
		retData = thisSensor[devId].getData()
		if retData != "badSensor": 
			data = {"pm10_standard":	retData[0], 
					"pm25_standard":	retData[1], 
					"pm100_standard":	retData[2], 
					"pm10_env":			retData[3], 
					"pm25_env":			retData[4], 
					"pm100_env":		retData[5], 
					"particles_03um":	retData[6], 
					"particles_05um":	retData[7], 
					"particles_10um":	retData[8], 
					"particles_25um":	retData[9], 
					"particles_50um":	retData[10], 
					"particles_100um":	retData[11]	 }
			if G.debug >1: U.logger.log(20, "{}".format(data)) 
			badSensor = 0
			return data
	except	Exception as e:
		U.logger.log(30,"", exc_info=True)

	badSensor+=1
	if badSensor >3: return "badSensor"
	return ""

#################################
def resetSensor(devId =""):
	global resetPin
	for id in resetPin:
		if devId == "" or id == devId:
			pin = resetPin[id]
			if pin == "": continue
			pin = int(pin)
			if pin > 26:  continue 
			if pin < 2:	  continue	
			if G.debug >1: U.logger.log(20, u"resetting pmAirquality device")
			GPIO.setup(pin, GPIO.OUT)
			GPIO.output(pin, True)
			time.sleep(0.1)
			GPIO.output(pin,False)
			time.sleep(0.2)
			GPIO.output(pin,True)
			time.sleep(0.5)
	return 



############################################
global sensor, sensors, badSensor
global deltaX, thisSensor, minSendDelta
global oldRaw, lastRead
global startTime
global resetPin

resetPin					= {}
firstValue					= True
startTime					= time.time()
oldRaw						= ""
lastRead					= 0
minSendDelta				= 5.
loopCount					= 0
sensorRefreshSecs			= 91
NSleep						= 100
sensorList					= []
sensors						= {}
sensor						= G.program
quick						= False
display						= "0"
output						= {}
badSensor					= 0
loopSleep					= 0.5
thisSensor					= {}
deltaX						= {}
U.setLogging()

myPID						= str(os.getpid())
U.killOldPgm(myPID,G.program+".py")# kill old instances of myself if they are still running


if U.getIPNumber() > 0:
	time.sleep(10)
	exit()

readParams()

time.sleep(1)

lastRead = time.time()

U.echoLastAlive(G.program)

resetSensor()

lastValues0			= {"particles_03um":0,"particles_05um":0,"particles_10um":0,"particles_25um":0,"particles_50um":0, "particles_10um":0}
lastValues			= {}
lastValues2			= {}
lastData			= {}
lastSend			= 0
lastDisplay			= 0
startTime			= time.time()
G.lastAliveSend		= time.time() -1000
data				= ""

sensorWasBad = False
while True:
	try:
		tt = time.time()
		sendData = False
		if sensor in sensors:
			data = {"sensors": {sensor:{}}}
			for devId in sensors[sensor]:
				if devId not in lastValues: 
					lastValues[devId]  = copy.copy(lastValues0)
					lastValues2[devId] = copy.copy(lastValues0)
				values = getValues(devId)
				if values == "": continue
				data["sensors"][sensor][devId]={}
				if values == "badSensor":
					sensorWasBad = True
					data["sensors"][sensor][devId] = "badSensor"
					if badSensor < 5: 
						U.logger.log(30," bad sensor")
						U.sendURL(data)
						resetSensor(devId=devId)
					else:
						U.restartMyself(param="", reason="badsensor", doPrint=True)
					lastValues2[devId] = copy.copy(lastValues0)
					lastValues[devId]  = copy.copy(lastValues0)
					continue
				elif values["particles_03um"] != "":
					data["sensors"][sensor][devId] = values
					deltaN =0
					for xx in lastValues0:
						try:
							current = float(values[xx])
							delta= current-lastValues2[devId][xx]
							deltaN= max(deltaN,abs(delta) / max (0.5,(current+lastValues2[devId][xx])/2.))
							lastValues[devId][xx] = current
						except	Exception as e:
							U.logger.log(30,"", exc_info=True)
				else:
					continue
				if sensorWasBad or (   ( deltaN > deltaX[devId] ) or  (  tt - abs(G.sendToIndigoSecs) > G.lastAliveSend  ) or quick	) and  ( tt - G.lastAliveSend > minSendDelta ):
						sensorWasBad = False
						sendData = True
						if not firstValue:
							lastValues2[devId] = copy.copy(lastValues[devId])
						firstValue = False
		if sendData and time.time() - startTime > 10: 
			U.sendURL(data)

		loopCount += 1

					 
		U.echoLastAlive(G.program)

		if loopCount %2 ==0:
			xx= time.time()
			if xx - lastRead > 5.:	
				readParams()
				lastRead = xx

		nsleep = int(max(5,sensorRefreshSecs-5)/5.)
		for ii in range(nsleep):
				quick = U.checkNowFile(G.program)				 
				if U.checkResetFile(G.program): 
					quick = True
					for devId in sensors[sensor]:
						resetSensor(devId=devId) 
				if quick: break
				time.sleep(5.)

	except	Exception as e:
		U.logger.log(30,"", exc_info=True)
		time.sleep(5.)
try: 	G.sendThread["run"] = False; time.sleep(1)
except: pass
sys.exit(0)
		
