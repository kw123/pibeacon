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


try:
	#1/0 # use GPIO
	if subprocess.Popen("/usr/bin/ps -ef | /usr/bin/grep pigpiod  | /usr/bin/grep -v grep",shell=True,stdout=subprocess.PIPE,stderr=subprocess.PIPE).communicate()[0].decode('utf-8').find("pigpiod")< 5:
		subprocess.call("/usr/bin/sudo /usr/bin/pigpiod &", shell=True)
	import pigpio
	useGPIO = False
except  Exception as e:
	try:
		import RPi.GPIO as GPIO
		GPIO.setmode(GPIO.BCM)
		GPIO.setwarnings(False)
		useGPIO = True
	except: pass


sys.path.append(os.getcwd())
import  piBeaconUtils   as U
import  piBeaconGlobals as G

import  displayDistance as DISP
G.program = "ultrasoundDistance"

version = 2.3



# ===========================================================================
# read params
# ===========================================================================

#################################		
def readParams():
	global sensors, sensor,  sensorRefreshSecs, dynamic, mode, deltaDist, deltaDistAbs,displayEnable
	global output
	global distanceUnits
	global oldRaw, lastRead
	global PIGPIO
	try:

		inp, inpRaw, lastRead2 = U.doRead(lastTimeStamp=lastRead)
		if inp == "": return
		if lastRead2 == lastRead: return
		lastRead   = lastRead2
		if inpRaw == oldRaw: return
		oldRaw	 = inpRaw

		sensorsOld = copy.copy(sensors)
	   
		U.getGlobalParams(inp)
		 
		if "sensors"				in inp:  sensors =		   (inp["sensors"])
		if "distanceUnits"		  in inp:  distanceUnits=	  (inp["distanceUnits"])
		
		if "output"				 in inp:  output=			 (inp["output"])
   
 
		if sensor not in sensors:
			U.logger.log(30, "ultrasound is not in parameters = not enabled, stopping ultrasoundDistance.py" )
			exit()
			time.sleep(3000000)
			
 
		sensorUp = U.doWeNeedToStartSensor(sensors,sensorsOld,sensor)


		if sensorUp != 0: # something has changed
			if os.path.isfile(G.homeDir+"temp/"+sensor+".dat"):
				os.remove(G.homeDir+"temp/"+sensor+".dat")


		if sensorUp == 1:
			for devId in sensors[sensor]:
				echoPin = int(sensors[sensor][devId]["gpioEcho"])
				trigPin = int(sensors[sensor][devId]["gpioTrigger"])
				if useGPIO:
					GPIO.setup(trigPin,  GPIO.OUT)
					GPIO.setup(echoPin,  GPIO.IN,  pull_up_down = GPIO.PUD_UP)
					U.logger.log(20, "adding devId:{} to GPIO, echo:{}, trigger:{} ".format(devId, echoPin, trigPin) )
				else:
					U.logger.log(20, "adding devId:{} to PIGPIO, echo:{}, trigger:{} ".format(devId, echoPin, trigPin) )
					if PIGPIO == "": PIGPIO = pigpio.pi()
					PIGPIO.set_mode( echoPin, pigpio.INPUT)
					PIGPIO.set_pull_up_down( echoPin, pigpio.PUD_UP )
					PIGPIO.set_mode( trigPin, pigpio.OUTPUT)

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
				sensorRefreshSecs = 0.3	

			try:
				if "displayEnable" in sensors[sensor][devId]: 
					displayEnable = sensors[sensor][devId]["displayEnable"]
			except: pass


			try:	deltaDist[devId] = float(sensors[sensor][devId].get("deltaDist",10))/100. # its in %
			except: deltaDist[devId] = 0.1

			try:	deltaDistAbs[devId] = float(sensors[sensor][devId].get("deltaDistAbs",10)) # its in cm 
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


def getzeroValue():
	global newValue
	newValue = True
	return 


#################################
def getDistancePIGPIO(devId):
	global sensor,sensors , first, maxRange, badSensor, PIGPIO
	try:
		echoPin	= int(sensors[sensor][devId]["gpioEcho"])  
		triggPin = int(sensors[sensor][devId]["gpioTrigger"]) 
		#U.logger.log(20,"devId:{} start, echo:{}, trigger:{}".format(devId, echoPin, triggPin))
		if first: 
			PIGPIO[devId]["trigger"].off()
			time.sleep(1)
			first = False

		maxDistOff = 9999999.
		elapsed = [maxDistOff, maxDistOff, maxDistOff]
		good = 0
		echoStartOK = False
		#read up to 6 times until 3 good measurements, then take average  
		MAX = -1
		MIN = 9999
		if sensors[sensor][devId].get("smoothMeasurements",True):
			maxGood = 1
		else:
			maxGood = 3
		for kk in range(8):
			time.sleep(0.03)
			# send a short on pulse, first clear 
			PIGPIO.write(triggPin,0)
			time.sleep(0.000001)
			PIGPIO.write(triggPin,1)
			time.sleep(0.000001)
			PIGPIO.write(triggPin,0)

			#wait for echo to start
			bad = False
			waitForEchoStart = time.time()
			while PIGPIO.read(echoPin) == 0:
				if time.time() - waitForEchoStart > 0.01: 
					bad = True
					time.sleep(0.2)
					break
			if bad:
				badSensor += 1
				#U.logger.log(20, u"echo  not 1")
				time.sleep(0.5)
				continue

			echoStartOK = True
			#wait for echo to stop
			timeOut = False
			startTime = time.time()
			#while PIGPIO[devId]["echo"].value == 1:
			while PIGPIO.read(echoPin) == 1:
				if time.time() - startTime > 0.035: # max range is 4m : 4*2/340 = 8/334 = 0.0239 , use some safety and set to 0.035
					timeOut = True
					break  # skip this measurement
			if timeOut: continue
			stopTime = time.time()

			# delta is the round trip time
			xx = round((stopTime - startTime)* 17000.,1)  #17000 = 34000/2 ...  /2 due to round trip; 1 msec = 17 cm distance
			if xx >= maxDistOff: continue 
			if xx > maxRange: continue 
			elapsed[good] = xx  #17000 = 34000/2 ...  /2 due to round trip; 1 msec = 17 cm distance
			if   MAX < elapsed[good]: MAX = elapsed[good]
			elif MIN > elapsed[good]: MIN = elapsed[good]
			good += 1
			if good == 3: break
			if good >= maxGood: break

		#U.logger.log(20,f"distances:  {elapsed}")


		if badSensor > 30:	
			badSensor = 0
			return "badSensor"
		if not echoStartOK: return ""
		if good != 3: return ""

		badSensor = 0
		elapsed = sorted(elapsed)

		if maxGood == 1: 
			return elapsed[0]

		# check if smooth values
		dx = elapsed[2] - elapsed[0]
		# ignore if dx > 15% or 20 cm
		if dx < 20. or dx < 0.3 * elapsed[0]/max(1,elapsed[2] + elapsed[0]):
			return elapsed[1]

		dx = elapsed[2] - elapsed[1]
		if dx < 20. or dx < 0.3 * elapsed[1]/max(1,elapsed[2] + elapsed[1]):
			return elapsed[1]

		dx = elapsed[1] - elapsed[0]
		if dx < 20. or dx < 0.3 * elapsed[1]/max(1,elapsed[1] + elapsed[0]):
			return elapsed[1]

		return ""

	except  Exception as e:
			U.logger.log(30,"", exc_info=True)
	return ""
 

#################################
def getDistance(devId):
	global sensor,sensors , first, maxRange, badSensor
	try:
		echoPin	= int(sensors[sensor][devId]["gpioEcho"])  
		triggerPin = int(sensors[sensor][devId]["gpioTrigger"]) 
		GPIO.output(triggerPin, False)
		if first: time.sleep(2) ; first = False
		maxDistOff = 9999999.
		elapsed = [maxDistOff,maxDistOff,maxDistOff]
		good = 0
		echoStartOK = False
		#read up to 6 times until 3 good measurements, then take average  
		MAX = -1
		MIN = 9999
		if sensors[sensor][devId].get("smoothMeasurements",True):
			maxGood = 1
		else:
			maxGood = 3
		for kk in range(8):
			time.sleep(0.03)
			GPIO.output(triggerPin, True)
			time.sleep(0.0002)
			GPIO.output(triggerPin, False)
			#U.logger.log(20, u"send pulse stop {}".format(time.time()-t))

			# echo:  1..0
			# echo must be 0 
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
			xx = round((stopTime - startTime)* 17000.,2)  #17000 = 34000/2 ...  /2 due to round trip; 1 msec = 17 cm distance
			if xx >= maxDistOff: continue 
			if xx > maxRange: continue 
			elapsed[good]  = xx
			if   MAX < elapsed[good]: MAX = elapsed[good]
			elif MIN > elapsed[good]: MIN = elapsed[good]
			good += 1
			if good == 3: break
			if good >= maxGood: break

		if badSensor > 30:	
			badSensor = 0
			return "badSensor"
		if not echoStartOK: return ""
		if good != 3: return ""

		badSensor = 0
		elapsed = sorted(elapsed)

		if maxGood == 1: 
			return elapsed[0]

		# check if smooth values
		dx = elapsed[2] - elapsed[0]
		# ignore if dx > 10% or 20 cm
		if dx < 20. or dx < 0.2* elapsed[0]/max(1,elapsed[2] + elapsed[0]):
			return elapsed[1]

		dx = elapsed[2] - elapsed[1]
		if dx < 20. or dx < 0.2* elapsed[1]/max(1,elapsed[2] + elapsed[1]):
			return elapsed[1]

		dx = elapsed[1] - elapsed[0]
		if dx < 20. or dx < 0.2* elapsed[1]/max(1,elapsed[1] + elapsed[0]):
			return elapsed[1]

		return ""

	except  Exception as e:
			U.logger.log(30,"", exc_info=True)
	return ""
 
 
#################################

def execMain():			 
	global sensors,sensorRefreshSecs,sensor, NSleep, ipAddress, dynamic, mode, deltaDist, first, displayEnable
	global output, authentication
	global distanceUnits
	global oldRaw,  lastRead, maxRange,badSensor
	global PIGPIO
	
	PIGPIO						= ""
	maxRange					= 555.
	oldRaw						= ""
	lastRead					= 0
	distanceUnits				= "1.0"
	
	first						= False
	loopCount					= 0
	sensorRefreshSecs			= 0.3
	NSleep						= 100
	sensors						= {}
	sensor						= G.program
	quick						= False
	mode						= 0
	output						= {}
	sendEvery					= 55. # send at least every xx secs msg to indigo even if no trigger
	U.setLogging()
	
	U.logger.log(20,"{} version:{} started with use GPIO:{}".format(G.program, version, useGPIO))
	
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
					if useGPIO:
						dist = getDistance(devId)
					else:
						dist = getDistancePIGPIO(devId)
	
	
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
					#U.logger.log(20,"devId:{}, dist:{}, deltaA:{:.2}, deltaDistAbs:{}, deltaN:{:.2}, deltaDist:{} trDD:{}, DDa:{}".format(devId, dist, deltaA, deltaDistAbs[devId], deltaN, deltaDist[devId], trigDD, trigDDa))
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

execMain()
sys.exit(0)
