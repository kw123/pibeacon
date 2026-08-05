#!/usr/bin/env python
# -*- coding: utf-8 -*-
# by Karl Wachs
# mar 2 2016
# version 0.95
##
##	 read GPIO INPUT and send http to indigo with data if pulses detected
#

##

import	sys, os, subprocess, copy
import	time,datetime
import	json
# TIME CRITICAL - keeps its own GPIO handling on purpose: this counts rain-bucket edges through
# GPIO.add_event_detect, so it must not go through a shared layer.
# The import is guarded: it used to be bare, so on a box without RPi.GPIO - a pi5, where RPi.GPIO
# does not run and rpi-lgpio is needed instead - the whole program died at import with a traceback
# and no explanation. gpioOK says whether pulses can be counted at all.
gpioOK = False
try:
	import	RPi.GPIO as GPIO
	GPIO.setmode(GPIO.BCM)			# inside the guard - this used to run unguarded further down and
	GPIO.setwarnings(False)			# would raise NameError once the import was protected
	gpioOK = True
except Exception:
	pass							# reported after U.setLogging(), the logger has no handlers yet here
import  smbus

sys.path.append(os.getcwd())
import	piBeaconUtils	as U
import	piBeaconGlobals as G

G.program = "rainSensorRG11"


def readParams():
	"""Reads the latest plugin/device configuration parameters for the RG-11 rain sensor, applying global params, sensor mode, GPIO/relay or I2C setup, sensitivity thresholds and rain scale factors, and restarting the process if the input GPIO channel changed.

	Inputs:
	    None.
	Outputs:
	    None: updates global config state, configures GPIO/I2C hardware, may restart the process
	"""
	global sensor, sensors
	global gpioIn , gpioSW1 ,gpioSW2, gpioSW5, gpioSWP, cyclePower, sensorMode
	global ON, off
	global oldRaw, lastRead
	global switchToLowerSensitive, switchToHigherSensitive, bucketSize,bucketSize0, sendMSGEverySecs
	global status, relayType, i2cAddress, bus
	try:
		restart = False


		inp, inpRaw, lastRead2 = U.doRead(lastTimeStamp=lastRead)
		if inp == "": return
		if lastRead2 == lastRead: return
		lastRead  = lastRead2
		if inpRaw == oldRaw: return
		oldRaw	   = inpRaw


		oldSensors		  = sensors

		U.getGlobalParams(inp)
		if "sensors"			in inp : sensors =				(inp["sensors"])


		if sensor not in sensors:
			U.logger.log(20,	"no "+ G.program+" sensor defined, exiting")
			exit()

		sens= sensors[sensor]
		found ={"{}".format(ii):{"RISING":0,"GPIOchanged":0,"BOTH":0 } for ii in range(100)}
		for devId in sens:
			sss= sens[devId]
			if "relayType" in sss:	relayType = sss["relayType"]
			else: 					relayType = "gpio-relay"
			if "gpioIn"					   not in sss: continue
			if relayType == "gpio-relay":
				if "gpioSW5"				   not in sss: continue
				if "gpioSW2"				   not in sss: continue
				if "gpioSW1"				   not in sss: continue
				if "gpioSWP"				   not in sss: continue
			if "sensorMode"				   not in sss: continue
			
			cp	= sss["cyclePower"] != "0"

			if gpioIn != -1 and gpioIn != int(sss["gpioIn"]):
				restart = True
				U.logger.log(20,	"gpios channel changed, need to restart")
				U.restartMyself(param="", reason=" new gpioIn")
				return 

			cyclePower = True 
			if relayType == "gpio-relay":
				if gpioSWP != int(sss["gpioSWP"]):
					gpioSWP = int(sss["gpioSWP"])
					if gpioSWP >0: GPIO.setup(gpioSWP, GPIO.OUT)
					powerOFF(calledFrom="read")
				if gpioSW1 != int(sss["gpioSW1"]):
					gpioSW1 = int(sss["gpioSW1"])
					if gpioSW1 >0: GPIO.setup(gpioSW1, GPIO.OUT)
				if gpioSW2 != int(sss["gpioSW2"]):
					gpioSW2 = int(sss["gpioSW2"])
					if gpioSW2 >0: GPIO.setup(gpioSW2, GPIO.OUT)
				if gpioSW5 != int(sss["gpioSW5"]):
					gpioSW5 = int(sss["gpioSW5"])
					if gpioSW5 >0: GPIO.setup(gpioSW5, GPIO.OUT)
			else: 
				if bus =="":
					DEVICE_BUS = 1
					bus= smbus.SMBus(DEVICE_BUS)
					i2cAddress = int(sss["i2cAddress"])
					gpioSWP = 4
					gpioSW5 = 3
					gpioSW2 = 2
					gpioSW1 = 1

			switchToLowerSensitive["checkIfIsRaining"]	= 10# int(sss["TimeSwitchSensitivityRainToMayBeRaining"])
			switchToLowerSensitive["maybeRain"]			= 10# int(sss["TimeSwitchSensitivityMayBeRainingToHigh"])
			switchToLowerSensitive["highSensitive"]		= 10# int(sss["TimeSwitchSensitivityHighToMed"])
			switchToLowerSensitive["medSensitive"]		= 10# int(sss["TimeSwitchSensitivityMedToLow"])
			
			switchToHigherSensitive["lowSensitive"]		= 100# int(sss["TimeSwitchSensitivityLowToMed"])
			switchToHigherSensitive["medSensitive"]		= 100# int(sss["TimeSwitchSensitivityMedToHigh"])
			switchToHigherSensitive["highSensitive"]	= 100# int(sss["TimeSwitchSensitivityHighToAnyRain"])
			try: 	rainScaleFactor						= float(sss["rainScaleFactor"])
			except: rainScaleFactor						= 1.
				
			if gpioIn != int(sss["gpioIn"]):
				gpioIn	= int(sss["gpioIn"])
				GPIO.setup(gpioIn,	GPIO.IN, pull_up_down=GPIO.PUD_UP)
				GPIO.add_event_detect(gpioIn, GPIO.FALLING,		callback=GPIOchanged, bouncetime=100)  
				if sss["sensorMode"] != "dynamic":	setModeTo("checkIfIsRaining", calledFrom="readParams1")

			if sensorMode != sss["sensorMode"]:
				if sss["sensorMode"] != "dynamic":
					sendShortStatus(rainMsg["checkIfIsRaining"])
					nextModeSwitchNotBefore= time.time()+2
				setModeTo(sss["sensorMode"],force=True, calledFrom="readParams2")

			sensorMode									= sss["sensorMode"]
			sendMSGEverySecs							= float(sss["sendMSGEverySecs"])
			time.sleep(0.4)
			powerON(calledFrom="read")
			cyclePower = cp

			bucketSize={}
			for kk in bucketSize0:
				bucketSize[kk] = bucketSize0[kk]*rainScaleFactor

			
	except Exception as e:
		U.logger.log(20,"", exc_info=True)
				

def setupSensors():

		"""Loads the Linux 1-Wire kernel modules (w1-gpio and w1_therm) via modprobe to initialize GPIO-based sensor support, returning False if either modprobe call errors.

		Inputs:
		    None.
		Outputs:
		    bool: True if both modules loaded, False on modprobe error
		"""
		U.logger.log(20, "starting setup GPIOs ")

		ret=subprocess.Popen("modprobe w1-gpio" ,shell=True,stdout=subprocess.PIPE,stderr=subprocess.PIPE).communicate()
		if len(ret[1]) > 0:
			U.logger.log(20, "starting GPIO: return error "+ ret[0]+"\n"+ret[1])
			return False

		ret=subprocess.Popen("modprobe w1_therm",shell=True,stdout=subprocess.PIPE,stderr=subprocess.PIPE).communicate()
		if len(ret[1]) > 0:
			U.logger.log(20, "starting GPIO: return error "+ ret[0]+"\n"+ret[1])
			return False

		return True
 
def GPIOchanged(gpio):	
	"""GPIO falling-edge callback fired when the RG-11 relay clicks; debounces the event, records click timing, and in static or dynamic mode escalates/sends rain messages, accumulates rain buckets, and switches sensitivity modes based on click intervals.

	Inputs:
	    gpio (int): GPIO pin number that triggered the event; ignored unless it equals the configured input pin
	Outputs:
	    None: updates rain status, sends messages, power-cycles and switches sensor modes
	"""
	global sensor, sensors
	global gpioIn , gpioSW1 ,gpioSW2, gpioSW5, cyclePower
	global lastClick,lastClick2, eventStartedList, lastCheckIfisRaining
	global nextModeSwitchNotBefore
	global switchToLowerSensitive, switchToHigherSensitive, bucketSize
	global status
	global simpleCount 
	global rainMsg
	global ON, off
	global sensorMode
	global ProgramStart
	global inGPIOchanged
	global lastGPIOStatus, newGPIOStatus
	global doPrint
	
	if gpio != gpioIn: return 
	gpioStatus1 = getGPIO(gpioIn,calledFrom="event1") 
	simpleCount +=1
	U.logger.log(10,	"into GPIOchanged, GPIO in: {}".format(gpioStatus1)+" {}".format(lastGPIOStatus)+"; count: {}".format(simpleCount)+ " since last %.4f"%(time.time() - lastClick)+";	 inGPIOchanged: {}".format(inGPIOchanged))
	if time.time() - ProgramStart < 0: return 
	if time.time() - lastClick < 0.06: return  # click come at > 50 msec so they must be > that apart 

	gpioStatus2 = getGPIO(gpioIn,calledFrom="event2") 
	U.logger.log(10,	"gpio{}".format(gpio)+ " {}".format(gpioStatus1)+"  {}".format(gpioStatus2)+ " since last %.4f"%(time.time() - lastClick) )
	lastClick2 = lastClick
	lastClick  = time.time()
	U.logger.log(10, "accepted  currentMode "+ status["currentMode"])

	inGPIOchanged = True

	eventStartedList.pop(0)
	eventStartedList.append(time.time())
	newRainTime =[]
	for x in eventStartedList:
		newRainTime.append( max(0.001, time.time()	- x) )


	# static, shortcut to check if its rainging, will just send a msg, no rain amount 
	if sensorMode != "dynamic":
		if sensorMode == "checkIfIsRaining" : 
			if cyclePower:
				if time.time() - lastCheckIfisRaining > switchToLowerSensitive["checkIfIsRaining"] and switchToLowerSensitive["checkIfIsRaining"] >0:
					lastCheckIfisRaining = time.time()
					sendShortStatus(rainMsg["maybeRain"])
					lastCheckIfisRaining = time.time()+3
					powerOFF(calledFrom="GPIOchanged0-0")
					time.sleep(3)
					powerON(calledFrom="GPIOchanged0-1")
					return 
			lastCheckIfisRaining = time.time()
			sendShortStatus(rainMsg["highSensitive"])
			U.writeRainStatus(status)
			inGPIOchanged = False
			return 
		# calc amount of rain etc	  
		bucket = bucketSize[status["currentMode"] ]
		accumBuckets(bucket)
		U.logger.log(10,status["currentMode"] +"	{}".format(bucket)+"   {}".format(newRainTime))
		U.writeRainStatus(status)



	# we are here because a the relay clicked.
	# start at checkIfIsRaining. if std: switch to maybe raining 
	#	if not start go to highSensitive immediately 
	# 
	# if maybe rain: next click must happen withing x secs, if not reset to checkIfRaining.	 (ie 2.click in xx secs)
	#  if not go back to check if is raining 
	if sensorMode == "dynamic":
		if	status["currentMode"]  == "checkIfIsRaining":
			if time.time() - lastCheckIfisRaining > switchToLowerSensitive["checkIfIsRaining"] and switchToLowerSensitive["checkIfIsRaining"] >0:
				sendShortStatus(rainMsg["maybeRain"])
				lastClick = time.time()+5.1
				powerOFF(calledFrom="GPIOchanged1-1")
				setModeTo("maybeRain", force=True, calledFrom="GPIOchanged1-1", powerCycle=False)
				lastCheckIfisRaining = time.time()+5.1
				time.sleep(5)
				lastClick = time.time()
				lastCheckIfisRaining = time.time()
				powerON(calledFrom="GPIOchanged1-1")
				U.writeRainStatus(status)
				inGPIOchanged = False
				return 
			### this should only happen when switchToLowerSensitive["checkIfIsRaining"] ==0 
			lastCheckIfisRaining = time.time()
			setModeTo("highSensitive", force=True, calledFrom="GPIOchanged1-2")
			sendShortStatus(rainMsg["highSensitive"])
			U.writeRainStatus(status)
			inGPIOchanged = False
			eventStartedList= [time.time()-(100) for ii in range(nEvenstStarted-1)]+[eventStartedList[nEvenstStarted-1]]
			return 

		if status["currentMode"]  == "maybeRain": 
			if time.time() - lastCheckIfisRaining > switchToLowerSensitive["maybeRain"] and switchToLowerSensitive["maybeRain"] >0:
				sendShortStatus(rainMsg["checkIfIsRaining"])
				lastCheckIfisRaining = time.time()+4.1
				lastClick = time.time() +4.1
				powerOFF(calledFrom="GPIOchanged1-3")
				setModeTo("checkIfIsRaining", force=True, calledFrom="GPIOchanged1-3", powerCycle=False)
				time.sleep(4)
				lastCheckIfisRaining = time.time()
				lastClick = time.time() 
				powerON(calledFrom="GPIOchanged1-3")
				U.writeRainStatus(status)
				inGPIOchanged = False
				return 
			lastCheckIfisRaining = time.time()
			setModeTo("highSensitive", force=True, calledFrom="GPIOchanged2")
			sendShortStatus(rainMsg["highSensitive"])
			eventStartedList= [time.time()-(100) for ii in range(nEvenstStarted-1)]+[eventStartedList[nEvenstStarted-1]]
			U.writeRainStatus(status)
			inGPIOchanged = False
			return 


		# calc amount of rain etc	  
		bucketsize = bucketSize[status["currentMode"] ]
		accumBuckets(bucketsize)
		U.logger.log(10,status["currentMode"] +";   bucketsize:{}".format(bucketsize)+";	 buckets:{}".format(status["values"]["nMesSinceLastReset"])+";  newRainTime: {}".format(newRainTime)  )


		if status["currentMode"]  == "highSensitive":
			if	 newRainTime[0] < switchToLowerSensitive["highSensitive"]: # require len(newRainTime) clicks
				if status["values"]["buckets"] > 0: checkIfMSGtoBeSend(force =True)
				if setModeTo("medSensitive", calledFrom="GPIOchanged3", force = True):
					sendShortStatus(rainMsg["medSensitive"])
					eventStartedList = [time.time()-(100) for ii in range(nEvenstStarted-1)]+[eventStartedList[nEvenstStarted-1]]



		elif status["currentMode"]	== "medSensitive":
			if	 newRainTime[0] <  switchToLowerSensitive["medSensitive"]: # require len(newRainTime) clicks
				if status["values"]["buckets"] > 0: checkIfMSGtoBeSend(force =True)
				if setModeTo("lowSensitive", calledFrom="GPIOchanged5", force = True):
					sendShortStatus(rainMsg["lowSensitive"])
					eventStartedList= [time.time()-(100) for ii in range(nEvenstStarted-1)]+[eventStartedList[nEvenstStarted-1]]

		elif status["currentMode"]	== "lowSensitive":
			pass
			
						
	U.writeRainStatus(status)
	inGPIOchanged = False
	return 


def setModeTo(newMode, calledFrom="", powerCycle=True, force = False):
	"""Switches the rain sensor to a new sensitivity mode if allowed, respecting the minimum time between switches unless forced, applying the physical switch settings and updating current/last mode state.

	Inputs:
	    newMode (str): target sensitivity mode name
	    calledFrom (str): caller label for logging
	    powerCycle (bool): whether to power-cycle the relay during the switch
	    force (bool): bypass the minimum-time-between-switches guard
	Outputs:
	    bool: True if the mode was changed, False if blocked or unchanged
	"""
	global nextModeSwitchNotBefore, minTimeBetweenModeSwitch
	global status, ProgramStart

	#if time.time() - ProgramStart < 20: return 

	U.logger.log(10, "try to set new mode	 "+newMode+ " from "+status["currentMode"]+"  tt - nextModeSwitchNotBefore: {}".format(time.time() - nextModeSwitchNotBefore) +" called from: "+calledFrom )
	if (time.time() - nextModeSwitchNotBefore < 0) and not force: 
		return False
		
	U.logger.log(10, "setting mode to: "+newMode+ ";	 from currrentMode: "+status["currentMode"] )
	
	if status["currentMode"] != newMode or force:
		setSwitch(newMode, powerCycle=powerCycle)
		status["lastMode"]	   = status["currentMode"]
		status["currentMode"]  = newMode
		nextModeSwitchNotBefore= time.time() +3
		return True

	return False

def setSwitch(newMode, powerCycle=True):
	"""Applies the physical relay/GPIO switch configuration for a given sensitivity mode by calling the matching set* helper, optionally power-cycling the sensor off before and on after the change.

	Inputs:
	    newMode (str): sensitivity mode to apply (checkIfIsRaining/lowSensitive/medSensitive/highSensitive)
	    powerCycle (bool): whether to power-cycle the relay around the switch
	Outputs:
	    None: drives relay/GPIO hardware and power-cycles the sensor
	"""
	global cyclePower
	if cyclePower and powerCycle:
		powerOFF(calledFrom="setSwitch")
	if	 newMode =="checkIfIsRaining":	setcheckIfIsRaining()
	elif newMode =="lowSensitive":		setlowSensitive()
	elif newMode =="medSensitive":		setmedSensitive()
	elif newMode =="highSensitive":		sethighSensitive()
	if cyclePower and powerCycle:
		time.sleep(0.5)
		powerON(calledFrom="setSwitch")
		time.sleep(0.2)
	return

			
def checkIfDownGradedNeeded(force = False):
	"""Periodically checks whether the rain sensor should be downgraded to a less sensitive mode after a period without rain clicks; in dynamic mode steps down through the sensitivity levels and in static mode returns to checkIfIsRaining, sending status messages as it goes.

	Inputs:
	    force (bool): skip timing/idle guards and force the downgrade evaluation
	Outputs:
	    None: switches sensor modes, sends status messages, updates timers
	"""
	global nextModeSwitchNotBefore, lastDownGradeCheck, checkForDowngradeEvery, eventStartedList
	global minTimeBetweenModeSwitch
	global sensorMode
	global status, ProgramStart
	global lastGPIOStatus, newGPIOStatus

	if not force:
		if time.time() - ProgramStart < 20: return 
		if time.time() - lastDownGradeCheck < checkForDowngradeEvery:	 return 
		if time.time() - nextModeSwitchNotBefore	 < 0:				 return 
		lastRainTime = time.time()- eventStartedList[nEvenstStarted-1] 
		if lastRainTime < 5:											 return 
	else: 
		lastRainTime = 9999999
		
	if sensorMode == "dynamic": 
		if	 status["currentMode"] == "lowSensitive" and (lastRainTime > switchToHigherSensitive["lowSensitive"] or force):
			if status["values"]["buckets"] > 0: checkIfMSGtoBeSend(force =True)
			if setModeTo("medSensitive", calledFrom="checkIfDownGradedNeeded1"):
				sendShortStatus(rainMsg["medSensitive"])
				nextModeSwitchNotBefore= time.time()+switchToHigherSensitive["medSensitive"]
		elif status["currentMode"] == "medSensitive" and (lastRainTime > switchToHigherSensitive["medSensitive"] or force):
			if status["values"]["buckets"] > 0: checkIfMSGtoBeSend(force =True)
			if setModeTo("highSensitive", calledFrom="checkIfDownGradedNeeded2"):
				sendShortStatus(rainMsg["highSensitive"])
				nextModeSwitchNotBefore= time.time()+switchToHigherSensitive["highSensitive"]
		elif status["currentMode"] == "highSensitive" and (lastRainTime > switchToHigherSensitive["highSensitive"] or force):
			if status["values"]["buckets"] > 0: checkIfMSGtoBeSend(force =True)
			if setModeTo("checkIfIsRaining", calledFrom="checkIfDownGradedNeeded3"):
				sendShortStatus(rainMsg["checkIfIsRaining"])
				nextModeSwitchNotBefore= time.time()+switchToHigherSensitive["highSensitive"]
		elif status["currentMode"] == "maybeRain" and (lastRainTime > switchToHigherSensitive["maybeRain"] or force):
			if status["values"]["buckets"] > 0: checkIfMSGtoBeSend(force =True)
			if setModeTo("checkIfIsRaining", calledFrom="checkIfDownGradedNeeded3"):
				sendShortStatus(rainMsg["checkIfIsRaining"])
				nextModeSwitchNotBefore= time.time()+20
	else:
		st = getGPIO(gpioIn,calledFrom="downgrade")
		#print datetime.datetime.now().strftime("%H:%M:%S: ") + "checking downgrade static ",status["currentMode"], lastRainTime, max(switchToHigherSensitive[status["currentMode"]],60), st, lastGPIOStatus
		if st: return 
		if status["currentMode"] == "checkIfIsRaining": return 
		if	 lastRainTime > max(min(500,switchToHigherSensitive[status["currentMode"]]),60):
				#print "downgrading static to checkIfIsRaining "
				setModeTo("checkIfIsRaining", calledFrom="checkIfRelayON", powerCycle=False, force = False)
				sendShortStatus(rainMsg["checkIfIsRaining"])
				nextModeSwitchNotBefore= time.time()+minTimeBetweenModeSwitch
		
	lastDownGradeCheck = time.time()
	return


def accumBuckets(bucket):
	"""Accumulates one rain measurement into the running status counters, adding the given bucket amount to the totals and recording the last bucket size and measurement timestamp.

	Inputs:
	    bucket (float): rain amount for this click to add to the accumulators
	Outputs:
	    None: updates the global rain status values dict
	"""
	global status
	status["values"]["nMesSinceLastReset"] +=1
	status["values"]["buckets"]	  += bucket
	status["values"]["nMes"]	  += 1
	status["values"]["lastBucket"] = bucket
	status["values"]["lastMes"]	   = time.time()
	return
	
def calcRates():
	"""Computes the current rain rate (per hour) from accumulated buckets over the elapsed measurement time, adds the buckets to the running total, persists rain status, and returns the rate plus aggregate counters.

	Inputs:
	    None.
	Outputs:
	    tuple: (rainRate, bucketsTotal, deltaTime, nMes, nMesSinceLastReset)
	"""
	status["values"]["bucketsTotal"] += status["values"]["buckets"]
	deltaTime						  = time.time() -  status["values"]["startMes"]
	rainRate						  = (status["values"]["buckets"] / max(0.01,deltaTime)) *3600  # per hour
	deltaTime						  = deltaTime
	U.writeRainStatus(status)
	return rainRate, status["values"]["bucketsTotal"], deltaTime, status["values"]["nMes"], status["values"]["nMesSinceLastReset"]

def resetMes(all=False):
	"""Resets the per-interval rain measurement counters (buckets, count since last reset, start time, last bucket/measurement) and, when all is True, also clears the cumulative buckets total and total measurement count.

	Inputs:
	    all (bool): also reset the cumulative totals when True
	Outputs:
	    None: updates the global rain status values dict
	"""
	status["values"]["nMesSinceLastReset"]	  = 0
	status["values"]["buckets"]	   = 0
	status["values"]["startMes"]   = time.time()
	status["values"]["lastBucket"] = 0
	status["values"]["lastMes"]	   = 0
	if all: 
		status["values"]["bucketsTotal"] = 0
		status["values"]["nMes"]		 = 0

def resetValues():
	"""Fully resets all rain measurement values by calling resetMes(all=True) and then persists the cleared status to disk.

	Inputs:
	    None.
	Outputs:
	    None: clears all rain counters and writes rain status to file
	"""
	resetMes(all=True)
	U.writeRainStatus(status)


			
def checkIfRelayON():
	"""Throttled watchdog (runs at most every 3s) that reads the signal relay's GPIO input; if it has been ON too long it either power-cycles/resets the device (in cyclePower mode) or escalates the sensor's sensitivity to highSensitive (drizzle) or medSensitive (rain) and sends a short status update based on how long the event has lasted.

	Inputs:
	    None.
	Outputs:
	    None: Updates mode/sensitivity, power-cycles relay, sends status, and logs; returns early on errors or throttling
	"""
	global lastRelayONCheck
	global gpioIn, gpioSWP, ON, off, cyclePower
	global eventStartedList, lastGPIOStatus, newGPIOStatus
	try:
		if time.time()- lastRelayONCheck < 3: return 
		lastRelayONCheck = time.time()
		gpioStatus = getGPIO(gpioIn,calledFrom="checkRelay")
		maxONTime = 40
		if gpioStatus:
			if cyclePower:
				if sensorMode == "checkIfIsRaining":
					if time.time()- eventStartedList[nEvenstStarted-1] < maxONTime: return 
					U.logger.log(20, "resetting device in \"check if raining mode\", signal relay is ON for > {}".format(maxONTime)+"secs: %d"%( time.time()- eventStartedList[0])+"	to enable to detect new rain" )
				else:
					if time.time()- eventStartedList[nEvenstStarted-1] < 5: return 
					U.logger.log(20, "hanging? resetting device, signal relay is on for > {}".format(maxONTime)+"secs: {}".format( time.time()- eventStartedList[0])+"	 current Status"+status["currentMode"] )
					powerCyleRelay()
				eventStartedList= [time.time()-(7+5*(nEvenstStarted-ii)) for ii in range(nEvenstStarted-1)]+[eventStartedList[nEvenstStarted-1]]
			else:
				if	 time.time()- eventStartedList[nEvenstStarted-1] < 10: 
					return
				elif time.time()- eventStartedList[nEvenstStarted-1] < 145: #set to drizzle
					setModeTo("highSensitive", calledFrom="checkIfRelayON", powerCycle=False, force = False)
					sendShortStatus(rainMsg["highSensitive"])
				else: # set to rain
					setModeTo("medSensitive", calledFrom="checkIfRelayON", powerCycle=False, force = False)
					sendShortStatus(rainMsg["medSensitive"])
					#eventStartedList = time.time()
	except Exception as e:
		U.logger.log(20,"", exc_info=True)


			
def checkIfMSGtoBeSend(force =False):
	"""Periodically (or when forced) computes rain rate/total and other measurements via calcRates, packages them into a per-sensor data dict, sends it to the configured URL, resets measurement accumulators, optionally triggers a downgrade check, and persists rain status.

	Inputs:
	    force (bool): If True, bypass the time-since-last-send throttle and send immediately
	Outputs:
	    None: Sends data via URL, resets measurements, writes rain status file, logs; returns early when throttled
	"""
	global lastCalcCheck, sendMSGEverySecs, ProgramStart, sensorMode, switchToLowerSensitive, bucketSize
	try:
		if time.time()- lastCalcCheck < max( sendMSGEverySecs, switchToLowerSensitive[status["currentMode"]] ) and not force: return 
		if time.time() - ProgramStart < 5 : return 
	
		rate, totalRain, measurementTime, nBuckets,nBucketsSinceReset= calcRates()
		data={"sensors":{sensor:{}}}
		rainLevel = rainMsg[status["currentMode"]]
		for devId in sensors[sensor]: 
			data["sensors"][sensor][devId] = {"rainRate": round(rate,4), "totalRain": round(totalRain,4),"nBucketsTotal": nBuckets,"nBuckets": nBucketsSinceReset, "measurementTime":round(measurementTime,1),"mode":sensorMode,"sensitivity":status["currentMode"],"bucketSize":bucketSize[status["currentMode"]],"rainLevel":rainLevel}
		U.sendURL(data,wait=False)
		resetMes()
		if nBuckets < 4 and time.time()- lastCalcCheck > 40 and rainLevel > 1:
			checkIfDownGradedNeeded( force = True )
		U.writeRainStatus(status)
		lastCalcCheck = time.time()
	except Exception as e:
		U.logger.log(20,"", exc_info=True)


def sendShortStatus(level):
	"""Sends a lightweight status update for each device of the sensor containing the current rain level, mode, sensitivity, and bucket size, but only if it differs from the last sent message and enough time has passed since the last send and program start.

	Inputs:
	    level (int): Rain level value to report in the status message
	Outputs:
	    None: Sends status via URL when changed and updates last-sent trackers
	"""
	global sensorMode, status, ProgramStart, lastShortMsgSend, lastShortMsg, bucketSize
	if time.time() - ProgramStart < 5:		 return 
	if time.time() - lastShortMsgSend < 0.5: return 
	data={"sensors":{sensor:{}}}
	for devId in sensors[sensor]: 
		data["sensors"][sensor][devId] = {"rainLevel":level,"mode":sensorMode,"sensitivity":status["currentMode"],"bucketSize":bucketSize[status["currentMode"]] }
	if lastShortMsg != data["sensors"][sensor]: 
		U.sendURL(data,wait=False)
		lastShortMsgSend = time.time()
	lastShortMsg = data["sensors"][sensor]
	return

def setcheckIfIsRaining():
	"""Configures the relay switches for 'check if raining' mode by driving gpioSW5 on and gpioSW2/gpioSW1 off, using GPIO output for gpio-relay type or i2c writes otherwise, only when cyclePower is enabled.

	Inputs:
	    None.
	Outputs:
	    None: Sets GPIO pins or writes to the i2c relay
	"""
	global cyclePower
	global gpioIn , gpioSW1 ,gpioSW2, gpioSW5, gpioSWP, ON, off, relayType
	if cyclePower:
		if relayType == "gpio-relay":
			setGPIO(gpioSW5, ON)
			setGPIO(gpioSW2, off)
			setGPIO(gpioSW1, off)
		else:
			seti2cRelay( gpioSW5, 0xff)
			seti2cRelay( gpioSW2, 0x00)
			seti2cRelay( gpioSW1, 0x00)
	

def sethighSensitive():
	"""Configures the relay switches for high-sensitivity mode by driving gpioSW2 on and gpioSW5/gpioSW1 off, via GPIO output for gpio-relay type or i2c writes otherwise, only when cyclePower is enabled.

	Inputs:
	    None.
	Outputs:
	    None: Sets GPIO pins or writes to the i2c relay
	"""
	global cyclePower
	global gpioIn , gpioSW1 ,gpioSW2, gpioSW5, gpioSWP, ON, off, relayType
	if cyclePower:
		if relayType == "gpio-relay":
			setGPIO(gpioSW5, off)
			setGPIO(gpioSW2, ON)
			setGPIO(gpioSW1, off)
		else:
			seti2cRelay( gpioSW5, 0x00)
			seti2cRelay( gpioSW2, 0xff)
			seti2cRelay( gpioSW1, 0x00)

def setmedSensitive():
	"""Configures the relay switches for medium-sensitivity mode by driving gpioSW1 on and gpioSW5/gpioSW2 off, via GPIO output for gpio-relay type or i2c writes otherwise, only when cyclePower is enabled.

	Inputs:
	    None.
	Outputs:
	    None: Sets GPIO pins or writes to the i2c relay
	"""
	global cyclePower
	global gpioIn , gpioSW1 ,gpioSW2, gpioSW5, gpioSWP, ON, off, relayType
	if cyclePower:
		if relayType == "gpio-relay":
			setGPIO(gpioSW5, off)
			setGPIO(gpioSW2, off)
			setGPIO(gpioSW1, ON)
		else:
			seti2cRelay( gpioSW5, 0x00)
			seti2cRelay( gpioSW2, 0x00)
			seti2cRelay( gpioSW1, 0xff)

def setlowSensitive():
	"""Configures the relay switches for low-sensitivity mode by driving all three switch lines (gpioSW5, gpioSW2, gpioSW1) off, via GPIO output for gpio-relay type or i2c writes otherwise, only when cyclePower is enabled.

	Inputs:
	    None.
	Outputs:
	    None: Sets GPIO pins or writes to the i2c relay
	"""
	global cyclePower
	global gpioIn , gpioSW1 ,gpioSW2, gpioSW5, gpioSWP, ON, off, relayType
	if cyclePower:
		if relayType == "gpio-relay":
			setGPIO(gpioSW5, off)
			setGPIO(gpioSW2, off)
			setGPIO(gpioSW1, off)
		else:
			seti2cRelay( gpioSW5, 0x00)
			seti2cRelay( gpioSW2, 0x00)
			seti2cRelay( gpioSW1, 0x00)

def powerCyleRelay():
	"""Power-cycles the sensor's relay by calling powerOFF followed by powerON.

	Inputs:
	    None.
	Outputs:
	    None: Toggles the power relay off then on
	"""
	global gpioSWP, ON, off
	powerOFF(calledFrom="powerCyleRelay")
	powerON(calledFrom="powerCyleRelay")

def powerON(calledFrom=""):
	"""Turns the sensor power on by driving the power switch pin gpioSWP to the off (de-energized) level via GPIO output for gpio-relay type or an i2c write otherwise.

	Inputs:
	    calledFrom (str): Caller identifier for logging/tracing context
	Outputs:
	    None: Sets the power GPIO pin or writes to the i2c relay
	"""
	global gpioSWP, ON, off
	if relayType == "gpio-relay":
		setGPIO(gpioSWP, off)
	else:
		seti2cRelay( gpioSWP, 0x00)

def powerOFF(calledFrom=""):
	"""Turns the sensor power off by driving the power switch pin gpioSWP to the ON (energized) level via GPIO output for gpio-relay type or an i2c write otherwise.

	Inputs:
	    calledFrom (str): Caller identifier for logging/tracing context
	Outputs:
	    None: Sets the power GPIO pin or writes to the i2c relay
	"""
	global gpioSWP, ON, off, relayType
	if relayType == "gpio-relay":
		setGPIO(gpioSWP, ON)
	else:
		seti2cRelay( gpioSWP, 0xff)


def seti2cRelay(pin,ONoff):
	"""Writes a byte value to the i2c relay board at the configured address using the given pin/register as the command, but only when pin is greater than zero.

	Inputs:
	    pin (int): Register/command byte (relay channel) to write to; ignored if not positive
	    ONoff (int): Byte value to write (e.g. 0x00 off, 0xff on)
	Outputs:
	    None: Writes a byte to the i2c bus
	"""
	global bus, i2cAddress
	if pin > 0:
		bus.write_byte_data(i2cAddress, pin, ONoff)

def setGPIO(pin,ONoff):
	"""Sets the output level of a GPIO pin via GPIO.output, but only when pin is greater than zero.

	Inputs:
	    pin (int): GPIO pin number to set; ignored if not positive
	    ONoff (int): Output level to drive (ON/off)
	Outputs:
	    None: Drives the GPIO output pin
	"""
	if pin > 0:
		GPIO.output(pin, ONoff)

def getGPIO(pin,calledFrom=""):
	"""Reads the current digital state of a GPIO pin, updating module-level last/new status globals, and returns whether the pin reads as ON. Returns 0 when no valid pin (pin <= 0) is given.

	Inputs:
	    pin (int): BCM GPIO pin number to read; values <= 0 are ignored
	    calledFrom (str): Optional label identifying the caller (unused in body)
	Outputs:
	    bool or int: True/False if the pin equals the ON level, or 0 when pin is not positive
	"""
	global ON, lastGPIOStatus, newGPIOStatus
	if pin > 0:
			lastGPIOStatus = newGPIOStatus
			st =  GPIO.input(pin) == ON
			newGPIOStatus = st
			return st
	return 0

  
  
global sensors
global oldParams
global oldRaw,	lastRead
global gpioIn , gpioSW1 ,gpioSW2, gpioSW5, gpioSWP, cyclePower, sensorMode
global nextModeSwitchNotBefore, minTimeBetweenModeSwitch
global switchToLowerSensitive, switchToHigherSensitive, bucketSize,bucketSize0, rainScaleFactor
global lastClick,lastClick2, eventStartedList
global lastDirection
global values
global status
global simpleCount 
global lastDownGradeCheck, checkForDowngradeEvery, lastCalcCheck, lastCheckIfisRaining
global lastCalcCheck, sendMSGEverySecs
global rainMsg
global ON, off
global lastRelayONCheck
global ProgramStart
global lastShortMsgSend
global lastShortMsg
global inGPIOchanged, lastGPIOStatus, newGPIOStatus
global relayType, i2cAddress, bus

###################### init #################
bus						 = "" 
i2cAddress				 = 16
relayType				 = "gpio-relay"
uPmm					 = 25.
minTimeBetweenModeSwitch = 5
nextModeSwitchNotBefore	 = 0
lastDirection			 = 99
lastClick				 = 0
lastClick2				 = 0
nEvenstStarted			 = 6
eventStartedList		 = [time.time()-(150) for ii in range(nEvenstStarted)]
simpleCount				 = 0
switchToLowerSensitive	 = {"checkIfIsRaining":0,		 "maybeRain":0,	  "highSensitive":10,			"medSensitive":10,			"lowSensitive":99999999 }  # time between signals;	switch from xx to next higher bucket capacity = lower sinsititvity 
switchToHigherSensitive	 = {"checkIfIsRaining":99999999, "maybeRain":100, "highSensitive":100,			"medSensitive":100,			"lowSensitive":100		 }	# time between signals;	 switch from xx to next lower bucket capacity  if time between signals is > secs eg medSensitive to highSensitive
rainMsg					 = {"checkIfIsRaining":0,		 "maybeRain":1,	  "highSensitive":2,			"medSensitive":3,			"lowSensitive":4		}
bucketSize0				 = {"checkIfIsRaining":0,		 "maybeRain":0,	  "highSensitive":0.0001*uPmm,	"medSensitive":0.001*uPmm,	"lowSensitive":0.01*uPmm}  # in inches --> mm
gpioIn					 = -1 
gpioSW1					 = -1
gpioSW2					 = -1
gpioSW5					 = -1
gpioSWP					 = -1
sensorMode				 = "dynamic"
cyclePower				 = True
ON						 = False # for relay output 
off						 = True	 # for relay output 


restart					 = False
lastRead				 = 0
oldRaw					 = ""
status					 = {"values":{"startMes":0, "buckets":0, "bucketsTotal":0, "nMes":0, "lastBucket":0},"currentMode":"checkIfIsRaining","lastMode":""}
checkForDowngradeEvery	 = 10
sendMSGEverySecs		 = 101
lastRelayONCheck		 = 0
lastCheckIfisRaining	 = 0 
lastDownGradeCheck		 = 0
lastCalcCheck			 = 0 
lastRead				 = time.time() +20
ProgramStart			 = time.time() 
lastShortMsgSend		 = 0
lastShortMsg			 = {}
inGPIOchanged			 = False
lastGPIOStatus			 = 0
newGPIOStatus			 = 0

U.setLogging()

if not gpioOK:	U.logger.log(20, "no RPi.GPIO on this rpi - rain pulses cannot be counted (install rpi-lgpio on a pi5)")

myPID		= str(os.getpid())
U.killOldPgm(myPID,G.program+".py")# old old instances of myself if they are still running

GPIO.setwarnings(False)

# check if everything is installed
if False:
	for i in range(100):
		if not setupSensors(): 
			time.sleep(10)
			if i%50==0: U.logger.log(20,"sensor libs not installed, need to wait until done")
		else:
			break	 
if U.getIPNumber() > 0:
	U.logger.log(20," sensors no ip number  exiting ")
	time.sleep(10)
	exit()

sensor			  = G.program
sensors			  ={}
loopCount		  = 0

U.logger.log(20, "starting "+G.program+" program")

ret = U.readRainStatus()
if ret != {}: status = ret
if "nMesSinceLastReset" not in status["values"]:
	status["values"]["nMesSinceLastReset"]	  = 0
	
readParams()
if status["currentMode"] not in rainMsg:status["currentMode"] =	 "checkIfIsRaining"
setModeTo(status["currentMode"], force = True, calledFrom="main")
U.writeRainStatus(status)
if status["currentMode"] == "checkIfIsRaining": sendShortStatus(rainMsg["checkIfIsRaining"])

G.lastAliveSend		= time.time()


quick  = 0

G.tStart			= time.time() 
lastRead			= time.time()
shortWait			= 1


while True:
	try:
		tt= time.time()
		

		if status["currentMode"]  == "maybeRain": 
			if time.time() - lastCheckIfisRaining > switchToLowerSensitive["maybeRain"] and switchToLowerSensitive["maybeRain"] >0:
				lastCheckIfisRaining = time.time()
				setModeTo("checkIfIsRaining", force=True, calledFrom="loop check maybeRain")
				sendShortStatus(rainMsg["checkIfIsRaining"])
				U.writeRainStatus(status)

		if loopCount %10 ==0:
			if time.time()- lastRead > 5:
				readParams()
				lastRead = time.time()
				if U.checkResetFile(G.program):
					resetValues()
					checkIfMSGtoBeSend(force=True)
					

			checkIfRelayON()

			checkIfDownGradedNeeded()
			checkIfMSGtoBeSend()

			if loopCount%60==0:
					U.echoLastAlive(G.program)
			
		getGPIO(gpioIn,calledFrom="loop")

		if restart:
			U.restartMyself(param="", reason=" new definitions")


		loopCount+=1
		time.sleep(shortWait)
	except Exception as e:
		U.logger.log(20,"", exc_info=True)
		time.sleep(5.)

try: 	G.sendThread["run"] = False; time.sleep(1)
except: pass

sys.exit(0)
