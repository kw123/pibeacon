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
import	RPi.GPIO as GPIO  

sys.path.append(os.getcwd())
import	piBeaconUtils	as U
import	piBeaconGlobals as G
G.program = "rainSensorRG11"
GPIO.setmode(GPIO.BCM)


def readParams():
	global sensor, sensors
	global gpioIn , gpioSW1 ,gpioSW2, gpioSW5, gpioSWP, cyclePower, sensorMode
	global ON, off
	global oldRaw, lastRead
	global switchToLowerSensitive, switchToHigherSensitive, bucketSize, sendMSGEverySecs
	global status
	try:
		restart = False


		inp,inpRaw,lastRead2 = U.doRead(lastTimeStamp=lastRead)
		if inp == "": return
		if lastRead2 == lastRead: return
		lastRead  = lastRead2
		if inpRaw == oldRaw: return
		oldRaw	   = inpRaw


		oldSensors		  = sensors

		U.getGlobalParams(inp)
		if "sensors"			in inp : sensors =				(inp["sensors"])
		if "debugRPI"			in inp:	 G.debug=			  int(inp["debugRPI"]["debugRPISENSOR"])

		if sensor not in sensors:
			U.toLog(0,	"no "+ G.program+" sensor defined, exiting",doPrint=True)
			exit()

		sens= sensors[sensor]
		found ={str(ii):{"RISING":0,"GPIOchanged":0,"BOTH":0 } for ii in range(100)}
		for devId in sens:
			sss= sens[devId]
			if "gpioIn"					   not in sss: continue
			if "gpioSW5"				   not in sss: continue
			if "gpioSW2"				   not in sss: continue
			if "gpioSW1"				   not in sss: continue
			if "gpioSWP"				   not in sss: continue
			if "sensorMode"				   not in sss: continue
			
			cp	= sss["cyclePower"] != "0"

			if gpioIn != -1 and gpioIn != int(sss["gpioIn"]):
				restart = True
				U.toLog(0,	"gpios channel changed, need to restart",doPrint=True)
				U.restartMyself(param="", reason=" new gpioIn",doPrint=True)
				return 

			cyclePower = True 
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
			switchToLowerSensitive["checkIfIsRaining"]	= int(sss["TimeSwitchSensitivityRainToMayBeRaining"])
			switchToLowerSensitive["maybeRain"]			= int(sss["TimeSwitchSensitivityMayBeRainingToHigh"])
			switchToLowerSensitive["highSensitive"]		= int(sss["TimeSwitchSensitivityHighToMed"])
			switchToLowerSensitive["medSensitive"]		= int(sss["TimeSwitchSensitivityMedToLow"])
			
			switchToHigherSensitive["lowSensitive"]		= int(sss["TimeSwitchSensitivityLowToMed"])
			switchToHigherSensitive["medSensitive"]		= int(sss["TimeSwitchSensitivityMedToHigh"])
			switchToHigherSensitive["highSensitive"]	= int(sss["TimeSwitchSensitivityHighToAnyRain"])
				
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

			
	except	Exception, e:
		U.toLog(-1, u"in Line '%s' has error='%s'" % (sys.exc_traceback.tb_lineno, e),doPrint=True)
				

def setupSensors():

		U.toLog(0, "starting setup GPIOs ",doPrint=True)

		ret=subprocess.Popen("modprobe w1-gpio" ,shell=True,stdout=subprocess.PIPE,stderr=subprocess.PIPE).communicate()
		if len(ret[1]) > 0:
			U.toLog(-1, "starting GPIO: return error "+ ret[0]+"\n"+ret[1],doPrint=True)
			return False

		ret=subprocess.Popen("modprobe w1_therm",shell=True,stdout=subprocess.PIPE,stderr=subprocess.PIPE).communicate()
		if len(ret[1]) > 0:
			U.toLog(-1, "starting GPIO: return error "+ ret[0]+"\n"+ret[1],doPrint=True)
			return False

		return True
 
def GPIOchanged(gpio):	
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
	U.toLog(1,	"into GPIOchanged, GPIO in: " +str(gpioStatus1)+" "+str(lastGPIOStatus)+";	 count: "+str(simpleCount)+ " since last %.4f"%(time.time() - lastClick)+";	 inGPIOchanged: "+str(inGPIOchanged), doPrint=doPrint)
	if time.time() - ProgramStart < 0: return 
	if time.time() - lastClick < 0.06: return  # click come at > 50 msec so they must be > that apart 

	gpioStatus2 = getGPIO(gpioIn,calledFrom="event2") 
	U.toLog(1,	"gpio"+str(gpio)+ " "+ str(gpioStatus1)+"  "+str(gpioStatus2)+ " since last %.4f"%(time.time() - lastClick),doPrint=doPrint )
	lastClick2 = lastClick
	lastClick  = time.time()
	U.toLog(1, "accepted  currentMode "+ status["currentMode"], doPrint=False)

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
		U.toLog(1,status["currentMode"] +"	"+str(bucket)+"	 "+ str(newRainTime) , doPrint=False )
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
		U.toLog(1,status["currentMode"] +";	  bucketsize:"+str(bucketsize)+";	 buckets:"+str(status["values"]["nMesSinceLastReset"])+";	 newRainTime: "+ str(newRainTime) , doPrint=doPrint )


		if status["currentMode"]  == "highSensitive":
			if	 newRainTime[0] < switchToLowerSensitive["highSensitive"]: # require len(newRainTime) clicks
				 if status["values"]["buckets"] > 0: checkIfMSGtoBeSend(force =True)
				 if setModeTo("medSensitive", calledFrom="GPIOchanged3", force = True):
					sendShortStatus(rainMsg["medSensitive"])
					eventStartedList= [time.time()-(100) for ii in range(nEvenstStarted-1)]+[eventStartedList[nEvenstStarted-1]]



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
	global nextModeSwitchNotBefore, minTimeBetweenModeSwitch
	global status, ProgramStart

	#if time.time() - ProgramStart < 20: return 

	U.toLog(0, "try to set new mode	 "+newMode+ " from "+status["currentMode"]+"  tt - nextModeSwitchNotBefore: "+str(time.time() - nextModeSwitchNotBefore) +" called from: "+calledFrom,doPrint=doPrint )
	if (time.time() - nextModeSwitchNotBefore < minTimeBetweenModeSwitch) and not force: 
		return False
		
	U.toLog(0, "setting mode to: "+newMode+ ";	 from currrentMode: "+status["currentMode"] ,doPrint=False)
	
	if status["currentMode"] != newMode or force:
		setSwitch(newMode, powerCycle=powerCycle)
		status["lastMode"]	   = status["currentMode"]
		status["currentMode"]  = newMode
		nextModeSwitchNotBefore= time.time() +3
		return True

	return False

def setSwitch(newMode, powerCycle=True):
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
	global status
	status["values"]["nMesSinceLastReset"] +=1
	status["values"]["buckets"]	  += bucket
	status["values"]["nMes"]	  += 1
	status["values"]["lastBucket"] = bucket
	status["values"]["lastMes"]	   = time.time()
	return
	
def calcRates():
	status["values"]["bucketsTotal"] += status["values"]["buckets"]
	deltaTime						  = time.time() -  status["values"]["startMes"]
	rainRate						  = (status["values"]["buckets"] / max(0.01,deltaTime)) *3600  # per hour
	deltaTime						  = deltaTime
	U.writeRainStatus(status)
	return rainRate, status["values"]["bucketsTotal"], deltaTime, status["values"]["nMes"], status["values"]["nMesSinceLastReset"]

def resetMes(all=False):
	status["values"]["nMesSinceLastReset"]	  = 0
	status["values"]["buckets"]	   = 0
	status["values"]["startMes"]   = time.time()
	status["values"]["lastBucket"] = 0
	status["values"]["lastMes"]	   = 0
	if all: 
		status["values"]["bucketsTotal"] = 0
		status["values"]["nMes"]		 = 0

def resetValues():
	resetMes(all=True)
	U.writeRainStatus(status)


			
def checkIfRelayON():
	global lastRelayONCheck
	global gpioIn, gpioSWP, ON, off, cyclePower
	global eventStartedList, lastGPIOStatus, newGPIOStatus
	if time.time()- lastRelayONCheck < 3: return 
	lastRelayONCheck = time.time()
	gpioStatus = getGPIO(gpioIn,calledFrom="checkRelay")
	maxONTime = 40
	if gpioStatus:
		if cyclePower:
			if sensorMode == "checkIfIsRaining":
				if time.time()- eventStartedList[nEvenstStarted-1] < maxONTime: return 
				U.toLog(-1, "resetting device in \"check if raining mode\", signal relay is ON for > "+str(maxONTime)+"secs: %d"%( time.time()- eventStartedList[0])+"	to enable to detect new rain" ,doPrint=doPrint)
			else:
				if time.time()- eventStartedList[nEvenstStarted-1] < 5: return 
				U.toLog(-1, "hanging? resetting device, signal relay is on for > "+str(maxONTime)+"secs: "+str( time.time()- eventStartedList[0])+"	 current Status"+status["currentMode"] ,doPrint=doPrint)
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


			
def checkIfMSGtoBeSend(force =False):
	global lastCalcCheck, sendMSGEverySecs, ProgramStart, sensorMode, switchToLowerSensitive
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


def sendShortStatus(level):
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
	global cyclePower
	global gpioIn , gpioSW1 ,gpioSW2, gpioSW5, gpioSWP, ON, off
	if doPrint: print datetime.datetime.now().strftime("%M:%S.%f: ") + "setcheckIfIsRaining.. cyclePower", cyclePower
	if cyclePower:
		setGPIO(gpioSW5, ON)
		setGPIO(gpioSW2, off)
		setGPIO(gpioSW1, off)
def sethighSensitive():
	global cyclePower
	global gpioIn , gpioSW1 ,gpioSW2, gpioSW5, gpioSWP, ON, off
	if doPrint: print datetime.datetime.now().strftime("%M:%S.%f: ") + "sethighSensitive.. cyclePower", cyclePower
	if cyclePower:
		setGPIO(gpioSW5, off)
		setGPIO(gpioSW2, ON)
		setGPIO(gpioSW1, off)
def setmedSensitive():
	global cyclePower
	global gpioIn , gpioSW1 ,gpioSW2, gpioSW5, gpioSWP, ON, off
	if doPrint: print datetime.datetime.now().strftime("%M:%S.%f: ") + "setmedSensitive.. cyclePower", cyclePower
	if cyclePower:
		setGPIO(gpioSW5, off)
		setGPIO(gpioSW2, off)
		setGPIO(gpioSW1, ON)
def setlowSensitive():
	global cyclePower
	global gpioIn , gpioSW1 ,gpioSW2, gpioSW5, gpioSWP, ON, off
	if doPrint: print datetime.datetime.now().strftime("%M:%S.%f: ") + "setlowSensitive.. cyclePower", cyclePower
	if cyclePower:
		setGPIO(gpioSW5, off)
		setGPIO(gpioSW2, off)
		setGPIO(gpioSW1, off)

def powerCyleRelay():
	global gpioSWP, ON, off
	powerOFF(calledFrom="powerCyleRelay")
	powerON(calledFrom="powerCyleRelay")

def powerON(calledFrom=""):
	global gpioSWP, ON, off
	if doPrint: print datetime.datetime.now().strftime("%M:%S.%f: ") + "powerON called from: "+ calledFrom+"  "+str(off)
	setGPIO(gpioSWP, off)

def powerOFF(calledFrom=""):
	global gpioSWP, ON, off
	if doPrint: print datetime.datetime.now().strftime("%M:%S.%f: ") + "powerOFF called from: "+ calledFrom.ljust(10)+"	 "+str(ON)
	setGPIO(gpioSWP, ON)



def setGPIO(pin,ONoff):
	if pin > 0:
		GPIO.output(pin, ONoff)

def getGPIO(pin,calledFrom=""):
	global ON, lastGPIOStatus, newGPIOStatus
	if pin > 0:
		lastGPIOStatus = newGPIOStatus
		st =  GPIO.input(pin) == ON
		newGPIOStatus = st
		if doPrint and (calledFrom !="loop" or (calledFrom =="loop" and newGPIOStatus !=lastGPIOStatus) ): print datetime.datetime.now().strftime("%M:%S.%f: ") +" getGPIO === calledFrom:"+calledFrom.ljust(15)+ ";  new / previous",newGPIOStatus,lastGPIOStatus
		return st
	return 0

  
  
global sensors
global oldParams
global oldRaw,	lastRead
global gpioIn , gpioSW1 ,gpioSW2, gpioSW5, gpioSWP, cyclePower, sensorMode
global nextModeSwitchNotBefore, minTimeBetweenModeSwitch
global switchToLowerSensitive, switchToHigherSensitive, bucketSize
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
global doPrint 

###################### init #################
	
uPmm					 = 25.4
minTimeBetweenModeSwitch = 5
nextModeSwitchNotBefore	 = 0
lastDirection			 = 99
lastClick				 = 0
lastClick2				 = 0
nEvenstStarted			 = 6
eventStartedList		 = [time.time()-(150) for ii in range(nEvenstStarted)]
simpleCount				 = 0
switchToLowerSensitive	 = {"checkIfIsRaining":0,		 "maybeRain":0,	  "highSensitive":3,			"medSensitive":3,			"lowSensitive":99999999 }  # time between signals;	switch from xx to next higher bucket capacity = lower sinsititvity 
switchToHigherSensitive	 = {"checkIfIsRaining":99999999, "maybeRain":100, "highSensitive":100,			"medSensitive":100,			"lowSensitive":100		 }	# time between signals;	 switch from xx to next lower bucket capacity  if time between signals is > secs eg medSensitive to highSensitive
rainMsg					 = {"checkIfIsRaining":0,		 "maybeRain":1,	  "highSensitive":2,			"medSensitive":3,			"lowSensitive":4		}
bucketSize				 = {"checkIfIsRaining":0,		 "maybeRain":0,	  "highSensitive":0.0001*uPmm,	"medSensitive":0.001*uPmm,	"lowSensitive":0.01*uPmm}  # in inches --> mm
gpioIn					 = -1 
gpioSW1					 = -1
gpioSW2					 = -1
gpioSW5					 = -1
gpioSWP					 = -1
sensorMode				 = "dynamic"
cyclePower				 = True
ON						 = False # for relay outoput 
off						 = True	 # for relay outoput 

doPrint					 = False

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

myPID		= str(os.getpid())
U.killOldPgm(myPID,G.program+".py")# old old instances of myself if they are still running

GPIO.setwarnings(False)

# check if everything is installed
for i in range(100):
	if not setupSensors(): 
		time.sleep(10)
		if i%50==0: U.toLog(-1,"sensor libs not installed, need to wait until done",doPrint=True)
	else:
		break	 
if U.getIPNumber() > 0:
	U.toLog(-1," sensors no ip number  exiting ", doPrint =True)
	time.sleep(10)
	exit()

sensor			  = G.program
sensors			  ={}
loopCount		  = 0

U.toLog(-1, "starting "+G.program+" program",doPrint=True)

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
			U.restartMyself(param="", reason=" new definitions",doPrint=True)


		loopCount+=1
		time.sleep(shortWait)
	except	Exception, e:
		U.toLog(-1, u"in Line '%s' has error='%s'" % (sys.exc_traceback.tb_lineno, e),doPrint=True)
		time.sleep(5.)


sys.exit(0)
