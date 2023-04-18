#!/usr/bin/env python
# -*- coding: utf-8 -*-
# by Karl Wachs
# feb 5 2016
# version 0.9 
##
##  get sensor values and write the to a file in json format for later pickup, 
##  do it in a timed manner not to load the system, is every 1 seconds then 30 senods break
##

import  sys, os, time, json, datetime,subprocess,copy
import math

import RPi.GPIO as GPIO


GPIO.setmode(GPIO.BCM)
sys.path.append(os.getcwd())
import  piBeaconUtils   as U
import  piBeaconGlobals as G

import  displayDistance as DISP
G.program = "ultrasoundDistance"





# ===========================================================================
# read params
# ===========================================================================

#################################		
def readParams():
	global sensors, sensor,  sensorRefreshSecs, dynamic, mode, deltaDist, deltaDistAbs,displayEnable
	global output
	global distanceUnits
	global oldRaw, lastRead
	try:

		inp,inpRaw,lastRead2 = U.doRead(lastTimeStamp=lastRead)
		if inp == "": return
		if lastRead2 == lastRead: return
		lastRead   = lastRead2
		if inpRaw == oldRaw: return
		oldRaw	 = inpRaw

		sensorsOld= copy.copy(sensors)
	   
		U.getGlobalParams(inp)
		 
		if "sensors"				in inp:  sensors =		   (inp["sensors"])
		if "distanceUnits"		  in inp:  distanceUnits=	  (inp["distanceUnits"])
		
		if "output"				 in inp:  output=			 (inp["output"])
   
 
		if sensor not in sensors:
			U.logger.log(30, "ultrasound is not in parameters = not enabled, stopping ultrasoundDistance.py" )
			exit()
			
 
		sensorUp = U.doWeNeedToStartSensor(sensors,sensorsOld,sensor)


		if sensorUp != 0: # something has changed
			if os.path.isfile(G.homeDir+"temp/"+sensor+".dat"):
				os.remove(G.homeDir+"temp/"+sensor+".dat")


		if sensorUp == 1:
			for devId in sensors[sensor]:
				GPIO.setwarnings(False)
				gpioPin= int(sensors[sensor][devId]["gpioTrigger"])
				GPIO.setup(gpioPin,  GPIO.OUT)
				gpioPin= int(sensors[sensor][devId]["gpioEcho"])
				GPIO.setup(gpioPin,  GPIO.IN,  pull_up_down = GPIO.PUD_UP)
		if sensorUp == -1:
			pass
			# stop sensor
		deltaDist = {}
		deltaDistAbs = {}

		for devId in sensors[sensor]:
			try:
				xx = sensors[sensor][devId]["sensorRefreshSecs"].split("#")
				sensorRefreshSecs = float(xx[0])
			except Exception as e:
				U.logger.log(20,"", exc_info=True)
				sensorRefreshSecs = 5	

			try:
				if "displayEnable" in sensors[sensor][devId]: 
					displayEnable = sensors[sensor][devId]["displayEnable"]
			except:
				display = False	


			try:	deltaDist[devId] = float(sensors[sensor][devId].get("deltaDist",10))/100.
			except: deltaDist[devId] = 0.1

			try:	deltaDistAbs[devId] = float(sensors[sensor][devId].get("deltaDistAbs",10))
			except: deltaDistAbs[devId] = 10.

			try:
				if "units" in sensors[sensor][devId]:
					units= sensors[sensor][devId]["units"]
					distanceUnits = units
			except  Exception as e:
				pass

			U.readDistanceSensor(devId, sensors, sensor)

  
	except  Exception as e:
		U.logger.log(30,"", exc_info=True)


#################################
def getultrasoundDistance(devId):
	global sensor,sensors , first, maxRange, badSensor
	try:
		echoPin	= int(sensors[sensor][devId]["gpioEcho"])  
		triggerPin = int(sensors[sensor][devId]["gpioTrigger"]) 
		GPIO.output(triggerPin, False)
		if first: time.sleep(2) ; first = False
		maxDistOff = 9999999.
		elapsed=[maxDistOff,maxDistOff,maxDistOff]
		good = 0
		echoStartOK = False
		#read up to 6 times until 3 good measurements, then take average  
		timeAtStart = time.time()
		MAX = -1
		MIN = 9999
		for kk in range(8):
			time.sleep(0.03)
			GPIO.output(triggerPin, True)
			time.sleep(0.0002)
			GPIO.output(triggerPin, False)
			#U.logger.log(20, u"send pulse stop {}".format(time.time()-t))

			# echo:  1..0
			# echo must be 1 
			if GPIO.input(echoPin) == 1:
				#U.logger.log(20, u"echo  not started")
				time.sleep(0.5)
				badSensor += 1
				continue

			#wait for echo to start
			bad = False
			waitForEchoStart = time.time()
			while GPIO.input(echoPin) == 0:
				if time.time() - waitForEchoStart > 0.01: 
					bad = True
					time.sleep(0.2)
					break
			if bad:
				badSensor += 1
				#U.logger.log(20, u"echo  not 0")
				time.sleep(0.5)
				continue

			echoStartOK = True
			#wait for echo to stop
			timeOut = False
			startTime = time.time()
			while GPIO.input(echoPin) == 1:
				if time.time() - startTime > 0.035: # max range is 4m : 4*2/340 = 8/334 = 0.0239 , use some safety and set to 0.035
					timeOut= True
					break  # skip this measurement
			stopTime = time.time()

			if timeOut: 
				time.sleep(0.2)
				continue

			# delta is the round trip time
			elapsed[good] = round((stopTime - startTime)* 17000.,2)  #17000 = 34000/2 ...  /2 due to round trip; 1 msec = 17 cm distance
			if   MAX < elapsed[good]: MAX = elapsed[good]
			elif MIN > elapsed[good]: MIN = elapsed[good]
			good += 1
			if good == 3: break

		if badSensor > 30:	
			badSensor = 0
			return "badSensor"
		if not echoStartOK: return ""

		badSensor = 0
		result = maxDistOff	
		# take average 
		elapsed = sorted(elapsed)
		ll = len(elapsed)
		#first remove non valid measurements
		for ii in range(ll): 
			if elapsed[-1] == maxDistOff:
				elapsed.pop()
		# how many meaurements left, if 3 
		if good == 3:
			for ii in range(good):
				if   MAX == elapsed[ii]:
					MAX = -1
					continue
				elif MIN == elapsed[ii]:
					MIN = -1
					continue
				result = round(elapsed[ii],2)
				break

		elif len(elapsed) == 2:
			result = round((elapsed[0]+elapsed[1])/2.,2)

		elif len(elapsed) == 1:
			result = elapsed[0] 

		else: # not good out of range
			result = maxRange

		#.logger.log(20, u"result		 {}, dist:{}[cm]".format( result, elapsed))
		if result >  maxRange: 
			#print "overflow"
			return maxRange 
		#print "res= ",result 
		return  round(result , 2)

	except  Exception as e:
			U.logger.log(30,"", exc_info=True)
	return ""
 
 

#################################

			 
global senors,sensorRefreshSecs,sensor, NSleep, ipAddress, dynamic, mode, deltaDist, first, displayEnable
global output, authentication
global distanceUnits
global oldRaw,  lastRead, maxRange,badSensor

distanceOffset				= {}
distanceMax					= {}
maxRange					= 555.
oldRaw						= ""
lastRead					= 0
distanceUnits				= "1.0"

debug						= 5
first						= False
loopCount					= 0
sensorRefreshSecs			= 5
NSleep						= 100
sensors						= {}
sensor						= G.program
quick						= False
lastMsg						= 0
mode						= 0
display						= "0"
output						= {}
delta						= 0
sendEvery					= 55. # send at least every xx secs msg to indigo even if no trigger
U.setLogging()

readParams()

myPID	   = str(os.getpid())
U.killOldPgm(myPID,G.program+".py")# kill old instances of myself if they are still running

if U.getIPNumber() > 0:
	#print " no ip number "
	time.sleep(10)
	exit()

#print "ultrasound ip:"+ G.ipAddress


U.echoLastAlive(G.program)

lastDist			= {}
lastTime			= {}
lastData			= {}
lastSend			= 0
lastDisplay			= 0
G.lastAliveSend		= time.time() -1000
lastRead 			= time.time()
badSensor 			= 0

while True:
	try:
		tt = time.time()
		data = {}
		data["sensors"] = {}
		oneSend = False
		if sensor in sensors:
			data["sensors"][sensor] = {}
			for devId in sensors[sensor]:
				data["sensors"][sensor][devId] = {}
				if devId not in lastDist: 
					lastDist[devId] = -500.
					lastTime[devId] = 0.
				dist = getultrasoundDistance(devId)
				#U.logger.log(20,"dist:{}".format(dist))

				if dist == "badSensor":
					badSensor = 0
					first = True
					#U.logger.log(30," bad sensor, sleeping for 2 secs")
					data["sensors"][sensor][devId]["distance"]= "badSensor"
					U.sendURL(data)
					lastDist[devId] = -100.
					time.sleep(2)
					continue

				if dist == "": continue

				dist = round(float(dist),1)
				delta  = (dist - lastDist[devId])
				deltaA = abs(delta)
				deltaT = max((tt  - lastTime[devId]),0.01)
				speed  = round(delta / deltaT,3)
				deltaN = (deltaA*2) / max (0.5,(dist+lastDist[devId]))
				regionEvents = U.doActionDistance(dist, speed, devId)

				trigDD 	= deltaN > deltaDist[devId]
				trigDDa	= deltaA > deltaDistAbs[devId]
				trigDT	= tt - sendEvery > lastTime[devId] 
				trigQi	= quick
				if ( trigDD and trigDDa ) or trigDT or trigQi or regionEvents[2]: 
							trig = ""
							if trigDD or trigDDa:		trig +="Dist;"
							if trigDT: 					trig +="Time;"
							if regionEvents[0] != "": 		
								trig += "distanceEvent"
								data["sensors"][sensor][devId]["distanceEvent"]	= regionEvents[0]
							data["sensors"][sensor][devId]["stopped"]	= regionEvents[1]
							trig = trig.strip(";")
							data["sensors"][sensor][devId]["trigger"]	= trig
							data["sensors"][sensor][devId]["distance"] = dist
							data["sensors"][sensor][devId]["speed"]	= speed
							oneSend = True
							G.lastAliveSend = tt
							lastDist[devId] = dist
							lastTime[devId] = tt
							#U.logger.log(20, "dist:{:} ;deltaN:{:.3f};  trig:{}, regionEvents:{:}, data:{}".format(dist, deltaN, trig, regionEvents, data) )	

				if displayEnable not in ["","0"]:
					DISP.displayDistance(dist, sensor, sensors, output, distanceUnits)
	
		if oneSend:	
			U.sendURL(data)
		loopCount +=1
		
		U.makeDATfile(G.program, data)

		quick = U.checkNowFile(G.program)				

		readParams()

		U.echoLastAlive(G.program)

		nLoops= int(max(sensorRefreshSecs/0.1, 1))
		#U.logger.log(20, "loopCount:{}, nLoops:{}, mode:{}, sensorRefreshSecs:{}".format(loopCount, nLoops, mode, sensorRefreshSecs) )
		for n in range(nLoops):
			if quick:			   break
			time.sleep(0.1)
			if time.time() - lastRead > 10:
				readParams()
				lastRead = time.time()
			if n > 800: break
		#print "end of loop", loopCount
	except  Exception as e:
		U.logger.log(30,"", exc_info=True)
		time.sleep(5.)
try: 	G.sendThread["run"] = False; time.sleep(1)
except: pass
sys.exit(0)
