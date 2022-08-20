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
import traceback
import  displayDistance as DISP
G.program = "ultrasoundDistance"





# ===========================================================================
# read params
# ===========================================================================

#################################        
def readParams():
	global sensors, sensor,  sensorRefreshSecs, dynamic, mode, deltaDist,displayEnable
	global output
	global distanceUnits
	global oldRaw, lastRead
	global actionDistanceOld, actionShortDistance, actionShortDistanceLimit, actionMediumDistance, actionMediumDistanceLimit, actionLongDistance, actionLongDistanceLimit, distanceMax
	try:

		inp,inpRaw,lastRead2 = U.doRead(lastTimeStamp=lastRead)
		if inp == "": return
		if lastRead2 == lastRead: return
		lastRead   = lastRead2
		if inpRaw == oldRaw: return
		oldRaw     = inpRaw

		sensorsOld= copy.copy(sensors)
	   
		U.getGlobalParams(inp)
		 
		if "sensors"                in inp:  sensors =           (inp["sensors"])
		if "distanceUnits"          in inp:  distanceUnits=      (inp["distanceUnits"])
		
		if "output"                 in inp:  output=             (inp["output"])
   
 
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
		deltaDist={}
		for devId in sensors[sensor]:
			try:
				xx = sensors[sensor][devId]["sensorRefreshSecs"].split("#")
				sensorRefreshSecs = float(xx[0])
			except Exception as e:
				U.logger.log(20, u"in Line {} has error={};  setting sensorRefreshSecs to 100".format(traceback.extract_tb(sys.exc_info()[2])[-1][1], e) )
				sensorRefreshSecs = 100    

			try:
				if "displayEnable" in sensors[sensor][devId]: 
					displayEnable = sensors[sensor][devId]["displayEnable"]
			except:
				display = False    


			deltaDist[devId]  = 0.1
			try:
				if "deltaDist" in sensors[sensor][devId]: 
					deltaDist[devId]= float(sensors[sensor][devId]["deltaDist"])/100.
			except:
				pass

			try:
				if "units" in sensors[sensor][devId]:
					units= sensors[sensor][devId]["units"]
					distanceUnits = units
			except  Exception as e:
				pass


			try:
				if "actionShortDistance" in sensors[sensor][devId]:         actionShortDistance = (sensors[sensor][devId]["actionShortDistance"])
			except:                                                         actionShortDistance = ""

			try:
				if "actionMediumDistance" in sensors[sensor][devId]:        actionMediumDistance = (sensors[sensor][devId]["actionMediumDistance"])
			except:                                                         actionMediumDistance = ""

			try:
				if "actionLongDistance" in sensors[sensor][devId]:          actionLongDistance = (sensors[sensor][devId]["actionLongDistance"])
			except:                                                         actionLongDistance = ""

			try:
				if "actionShortDistanceLimit" in sensors[sensor][devId]:    actionShortDistanceLimit = float(sensors[sensor][devId]["actionShortDistanceLimit"])
			except:                                                         actionShortDistanceLimit = -1

			try:
				if "actionLongDistanceLimit" in sensors[sensor][devId]:     actionLongDistanceLimit = float(sensors[sensor][devId]["actionLongDistanceLimit"])
			except:                                                         actionLongDistanceLimit = -1

  
	except  Exception as e:
		U.logger.log(30, u"in Line {} has error={}".format(traceback.extract_tb(sys.exc_info()[2])[-1][1], e))


#################################
def getultrasoundDistance(devId):
	global sensor,sensors , first, maxUse, badSensor
	try:
		echoPin    = int(sensors[sensor][devId]["gpioEcho"])  
		triggerPin = int(sensors[sensor][devId]["gpioTrigger"]) 
		GPIO.output(triggerPin, False)
		time.sleep(0.06)
		if first: time.sleep(2) ; first = False
		maxDistOff = 9999999.
		elapsed=[maxDistOff,maxDistOff,maxDistOff]
		good = 0
		echoStartOK = False
		for kk in range(6):
			time.sleep(0.05)
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
				time.sleep(0.3)
				continue

			# delta is the round trip time
			elapsed[good] = round((stopTime - startTime)* 17000.,2)  #17000 = 34000/2 ...  /2 due to round trip; 1 msec = 17 cm distance
			good += 1
			if good == 3: break

		if badSensor > 30:	return "badSensor"
		if not echoStartOK: return ""
		badSensor = 0
	
		elapsed = sorted(elapsed)
		ll = len(elapsed)
		for ii in range(ll): 
			if elapsed[-1] == maxDistOff:
				elapsed.pop()
		if len(elapsed) ==3:	
			result = elapsed[1] 
		elif len(elapsed) == 2:
			result = round((elapsed[0]+elapsed[0])/2.,2)
		elif len(elapsed) == 1:
			result = elapsed[0] 
		else:
			result = maxUse

		#.logger.log(20, u"result         {}, dist:{}[cm]".format( result, elapsed))
		if result >  maxUse: 
			#print "overflow"
			return maxUse # set to max = 5 m
		#print "res= ",result 
		return  round(result , 2)# 
	except  Exception as e:
			U.logger.log(30, u"in Line {} has error={}".format(traceback.extract_tb(sys.exc_info()[2])[-1][1], e))
	return ""        
 
 

#################################
def doAction(devId, distanceIN):
	global sensor,sensors , maxUse, badSensor
	global actionDistanceOld, actionShortDistance, actionShortDistanceLimit, actionMediumDistance, actionMediumDistanceLimit, actionLongDistance, actionLongDistanceLimit, distanceMax

	try:
		if actionShortDistance == "" and actionMediumDistance == "" and actionMediumDistance == "": return 

		if distanceIN != "" and distanceIN !=0:
			distance = distanceIN
			badSensor = 0
			#U.logger.log(20, " bf action test  {}  {}  {}  {} ".format(distance, actionShortDistance, actionMediumDistance, actionLongDistance )) 

			# check reset
			
			if	 distance > actionLongDistanceLimit:	region = "long"
			elif distance < actionShortDistanceLimit:	region = "short"
			else:										region = "medium"

			# check reset of last action, if last was short distamce must have been not short at least once ...  
			if actionDistanceOld != "":
				if   actionDistanceOld == "short"   	and region == "short":	actionDistanceOld = ""
				elif actionDistanceOld == "long"    	and region == "long":	actionDistanceOld = ""
				elif actionDistanceOld == "medium"  	and region == "medium":	actionDistanceOld = ""

			if actionShortDistance != ""	and actionDistanceOld != "short"	and  region == "short":
				subprocess.call(actionShortDistance, shell=True)
				actionDistanceOld = "short"
					
			if actionMediumDistance != ""	and  actionDistanceOld != "medium"	and region == "medium":
				subprocess.call(actionMediumDistance, shell=True)
				actionDistanceOld = "medium"
					
			if actionLongDistance != ""		and actionDistanceOld != "long"		and region == "long":
				subprocess.call(actionLongDistance, shell=True)
				actionDistanceOld =" long"

	except  Exception as e:
			U.logger.log(30, u"in Line {} has error={}".format(traceback.extract_tb(sys.exc_info()[2])[-1][1], e))


#################################

			 
global senors,sensorRefreshSecs,sensor, NSleep, ipAddress, dynamic, mode, deltaDist, first, displayEnable
global output, authentication
global distanceUnits
global oldRaw,  lastRead, maxUse,badSensor
global actionDistanceOld, actionShortDistance, actionShortDistanceLimit, actionMediumDistance, actionMediumDistanceLimit, actionLongDistance, actionLongDistanceLimit, distanceMax



actionShortDistance         = ""
actionShortDistanceLimit    = 5.
actionMediumDistance        = ""
actionMediumDistanceLimit   = 10
actionLongDistance          = ""
actionLongDistanceLimit     = 20.
actionDistanceOld           = 0
distanceOffset              = {}
distanceMax					= {}

maxUse 						= 555.

oldRaw                  	= ""
lastRead                	= 0

distanceUnits               = "1.0"

actionShortDistance         = ""
actionShortDistanceLimit    = 5.
actionMediumDistance        = ""
actionMediumDistanceLimit   = 10
actionLongDistance          = ""
actionLongDistanceLimit     = 20.
actionDistanceOld           = 0

debug                       = 5
first                       = False
loopCount                   = 0
sensorRefreshSecs           = 60
NSleep                      = 100
sensors                     = {}
sensor                      = G.program
quick                       = False
lastMsg                     = 0
mode                        = 0
display                     = "0"
output                      = {}
delta                       = 0
U.setLogging()

readParams()

myPID       = str(os.getpid())
U.killOldPgm(myPID,G.program+".py")# kill old instances of myself if they are still running

if U.getIPNumber() > 0:
	print " no ip number "
	time.sleep(10)
	exit()

print "ultrasound ip:"+ G.ipAddress


U.echoLastAlive(G.program)

lastDist            = {}
lastTime            = {}
lastData            = {}
lastSend            = 0
lastDisplay         = 0
maxDeltaSpeed       = 40. # = mm/sec
G.lastAliveSend     = time.time() -1000
lastRead 			= time.time()
badSensor 			= 0
while True:
	try:
		tt = time.time()
		data={}
		data["sensors"]     = {}
		if sensor in sensors:
			for devId in sensors[sensor]:
				skip = False
				if devId not in lastDist: 
					lastDist[devId] =-500.
					lastTime[devId] =0.
				dist = getultrasoundDistance(devId)
				if dist == "badSensor":
					badSensor = 0
					first = True
					#U.logger.log(30," bad sensor, sleeping for 2 secs")
					data0={}
					data0[sensor]={}
					data0[sensor][devId]={}
					data0[sensor][devId]["distance"]="badSensor"
					data["sensors"] = data0
					U.sendURL(data)
					lastDist[devId] = -100.
					time.sleep(2)
					continue

				if dist == "": continue
				if not skip:
					doAction(devId, dist)
					data["sensors"]     = {sensor:{devId:{}}}
					delta  =  (dist - lastDist[devId])
					deltaA =  abs(delta)
					deltaT =  max((tt  - lastTime[devId]),0.01)
					speed  =  round(delta / deltaT,3)
					deltaN =  (deltaA*2) / max (0.5,(dist+lastDist[devId]))
					if ( ( deltaN > deltaDist[devId] ) or 
						( (tt - G.sendToIndigoSecs) > G.lastAliveSend )   or 
						( quick )  or 
						( abs(speed) > maxDeltaSpeed)  ):
						data["sensors"][sensor][devId]["distance"] = dist
						data["sensors"][sensor][devId]["speed"]    = speed
						G.lastAliveSend = tt
						U.sendURL(data)
				lastDist[devId]  = dist
				lastTime[devId]  = tt

				if displayEnable == "1" and ( ( deltaN > 0.02 ) or (tt - lastDisplay > 2.   or quick)) :
					lastDisplay = tt
					DISP.displayDistance(dist, sensor, sensors, output, distanceUnits)
					
		if delta > 400: quick = True
		else:           quick = False
		
		loopCount +=1
		
		U.makeDATfile(G.program, data)

		quick = U.checkNowFile(G.program)                

		readParams()

		U.echoLastAlive(G.program)

		nLoops= int(max(sensorRefreshSecs/0.1, 1))
		#U.logger.log(20, "loopCount:{}, nLoops:{}, mode:{}, sensorRefreshSecs:{}".format(loopCount, nLoops, mode, sensorRefreshSecs) )
		for n in range(nLoops):
			if quick:               break
			time.sleep(0.1)
			if time.time() - lastRead > 10:
				readParams()
				lastRead = time.time()
			if n > 800: break
		#print "end of loop", loopCount
	except  Exception as e:
		U.logger.log(30, u"in Line {} has error={}".format(traceback.extract_tb(sys.exc_info()[2])[-1][1], e))
		time.sleep(5.)
try: 	G.sendThread["run"] = False; time.sleep(1)
except: pass
sys.exit(0)
