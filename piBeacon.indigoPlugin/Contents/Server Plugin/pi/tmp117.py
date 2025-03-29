#!/usr/bin/python
# -*- coding: utf-8 -*-
## adopted from adafruit 
#
#

import time
import board
import adafruit_tmp117
import sys, os, json, datetime,subprocess,copy


sys.path.append(os.getcwd())
import	piBeaconUtils	as U
import	piBeaconGlobals as G

G.program = "tmp117"
#  copied fro adafruit examples  https://github.com/adafruit/Adafruit_CircuitPython_TMP117/blob/main/examples
#===========================================================================
# TMP117 Class
# ===========================================================================
class SENSOR:

	# Constructor
	def __init__(self, i2cAddress=72):

		i2c = board.I2C()  # uses board.SCL and board.SDA
		self.tmp117 = adafruit_tmp117.TMP117(i2c,address=i2cAddress)
		self.tmp117.averaged_measurements 	= adafruit_tmp117.AverageCount.AVERAGE_8X
		self.tmp117.measurement_delay 		= adafruit_tmp117.MeasurementDelay.DELAY_0_125_S
		return 

	def getTemp(self):
		try:
			return self.tmp117.temperature
		except: 
			return ""

# ===========================================================================
# read params
# ===========================================================================

#################################		 
def readParams():
	global sensorList, sensors, sensor,	 sensorRefreshSecs
	global rawOld
	global deltaX, theSensor, minSendDelta
	global oldRaw, lastRead
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
			U.logger.log(20,"{} is not in parameters = not enabled, stopping {}.py".format(G.program, G.program) )
			exit()
			
				
		deltaX={}
		for devId in sensors[sensor]:
			deltaX[devId]  = 0.05
			try:
				xx = sensors[sensor][devId]["sensorRefreshSecs"].split("#")
				sensorRefreshSecs = float(xx[0]) 
			except:
				sensorRefreshSecs = 90	  


			i2cAddress = U.getI2cAddress(sensors[sensor][devId], default ="")

			try:
				if "deltaX" in sensors[sensor][devId]: 
					deltaX[devId]= float(sensors[sensor][devId]["deltaX"])/100.
			except:
				deltaX[devId] = 0.05

			try:
				if "minSendDelta" in sensors[sensor][devId]: 
					minSendDelta= float(sensors[sensor][devId]["minSendDelta"])/100.
			except:
				minSendDelta = 5.

				
			if devId not in theSensor:
				U.logger.log(20,"==== Start {} ===== @ i2c= {}".format(G.program, i2cAddress))
				i2cAdd = U.muxTCA9548A(sensors[sensor][devId])
				theSensor[devId] = SENSOR(i2cAddress=i2cAdd)
				U.muxTCA9548Areset()
				U.logger.log(20," started ")
				
		deldevID={}		   
		for devId in theSensor:
			if devId not in sensors[sensor]:
				deldevID[devId]=1
		for dd in  deldevID:
			del theSensor[dd]
		if len(theSensor) ==0: 
			####exit()
			pass

	except Exception as e:
		U.logger.log(20,"", exc_info=True)



#################################
def getValues(devId):
	global sensor, sensors, theSensor, badSensor

	i2cAdd = U.muxTCA9548A(sensors[sensor][devId])
	temp = "" 
	ambTemp = "" 
	try:
		temp	 = theSensor[devId].getTemp()
		#print(" temp:{}".format(temp)) # for testing
		if temp == "" :
			badSensor += 1
			U.muxTCA9548Areset()
			return "badSensor"
		data = {"temp":round(temp,1)}
		badSensor = 0
		U.muxTCA9548Areset()
		return data
	except Exception as e:
		if badSensor >2 and badSensor < 5: 
			U.logger.log(20,"", exc_info=True)
			U.logger.log(20,u"temp>>{}".format(temp)+"<<")
		badSensor +=1
	if badSensor > 3: 
		U.muxTCA9548Areset()
		return "badSensor"
	U.muxTCA9548Areset()
	return ""		 






############################################
global rawOld
global sensor, sensors, badSensor
global deltaX, theSensor, minSendDelta
global oldRaw, lastRead

oldRaw						=""
lastRead					= 0

theSensor					= {}
minSendDelta				= 5.
loopCount					= 0
sensorList					= []
sensors						= {}
sensor						= G.program
quick						= False
badSensor					= 0
loopSleep					= 5
rawOld						= ""
deltaX						= {}
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




lastValue		  	= {}
lastData			= {}
lastSend			= 0
lastRead			= time.time()
G.lastAliveSend		= time.time() -1000

sensorWasBad = False
while True:
	try:
		tt	 = time.time()
		data = {"sensors": {}}
		if sensor in sensors:
			for devId in sensors[sensor]:
				if devId not in lastValue: lastValue[devId] =-500.
				values = getValues(devId)
				if values == "": continue
				data["sensors"] = {sensor:{}}
				data["sensors"][sensor] = {devId:{}}
				if values =="badSensor":
					sensorWasBad = True
					data["sensors"][sensor][devId]["Current"]="badSensor"
					if badSensor < 5: 
						U.logger.log(20," bad sensor")
						U.sendURL(data)
					lastValue[devId] =-100.
					continue
				elif values["temp"] !="" :
					if sensorWasBad: # sensor was bad, back up again, need to do a restart to set config 
						U.restartMyself(reason=" back from bad sensor, need to restart to get sensors reset",doPrint=False)
					
					data["sensors"][sensor][devId] = values
					current = float(values["temp"])
					delta	= current-lastValue[devId]
					deltaN	= abs(delta) / max (0.5,(current+lastValue[devId])/2.)
				else:
					continue
				#print values, deltaN, deltaX[devId]
				if ( ( deltaN > deltaX[devId]						   ) or 
					 (	tt - abs(G.sendToIndigoSecs) > G.lastAliveSend	) or  
					 ( quick										   )   ) and  \
				   ( ( tt - G.lastAliveSend > minSendDelta			   )   ):
						#print data
						U.sendURL(data)
						lastValue[devId]  = current

		loopCount += 1

		U.makeDATfile(G.program, data)
		quick = U.checkNowFile(G.program)				 
		U.echoLastAlive(G.program)

		if loopCount %5 == 0 and not quick:
			tt= time.time()
			if tt - lastRead > 5.:	
				readParams()
				lastRead = tt
		if not quick:
			time.sleep(loopSleep)
		
	except Exception as e:
		U.logger.log(20,"", exc_info=True)
		time.sleep(5.)
try: 	G.sendThread["run"] = False; time.sleep(1)
except: pass
sys.exit(0)
