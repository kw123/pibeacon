#!/usr/bin/env python
# -*- coding: utf-8 -*-
# by Karl Wachs
# mar 2 2016
# version 0.95
##
##	 read GPIO INPUT and send http to indigo with data if pulses detected
#
## py3 prept, needs testing 
##

import	sys, os, subprocess, copy
import	time,datetime
import	json
# TIME CRITICAL - keeps its own GPIO handling on purpose: this COUNTS edges, and a missed one is a
# permanently wrong reading. No shared layer, no per-pin indirection.
# RPi.GPIO FIRST, deliberately - the opposite of the order this used to have. Its add_event_detect
# runs the edge callback from the library's own thread on a memory-mapped register, while every
# gpiozero edge goes through the pin factory, which on the pigpio factory means a socket round trip
# per event; under a fast pulse train that is where counts get lost. gpiozero stays as the last
# resort for a board where RPi.GPIO does not exist (on a pi5 the rpi-lgpio shim provides it).
# useGPIO and gpioOK are ALWAYS defined: useGPIO used to be left unset when both imports failed and
# the program then died much later with "NameError: useGPIO" instead of naming what was missing.
useGPIO = False			# True = talk to RPi.GPIO directly
gpioOK  = False
try:
	import RPi.GPIO as GPIO
	GPIO.setmode(GPIO.BCM)
	GPIO.setwarnings(False)
	useGPIO = True
	gpioOK  = True
except Exception:
	try:
		import gpiozero
		from gpiozero import Device
		try:
			from gpiozero.pins.pigpio import PiGPIOFactory
			Device.pin_factory = PiGPIOFactory()
		except Exception:
			pass			# no pigpiod: gpiozero picks its own factory
		gpioOK = True
	except Exception:
		pass				# reported after U.setLogging(), no handlers yet here

sys.path.append(os.getcwd())
import	piBeaconUtils	as U
import	piBeaconGlobals as G

G.program = "INPUTpulse"
if useGPIO: GPIO.setmode(GPIO.BCM)


def checkReset():
	"""Checks whether the pulse input counters have been reset externally by comparing against U.checkresetCount, updating the global counter copy when a reset occurred.

	Inputs:
	    None.
	Outputs:
	    bool: True if INPUTcount changed (a reset was applied), otherwise False
	"""
	global	INPUTcount
	INPUTcount2 = U.checkresetCount(INPUTcount)
	if INPUTcount2 != INPUTcount:
		INPUTcount = copy.copy(INPUTcount2)
		return True
	return False

def readParams():
	"""Reads the latest sensor configuration and, for each pulse-input GPIO device, sets up or updates its edge-detection configuration (bounce time, dead times, burst/coincidence windows, rising/falling type) in GPIOdict, registering RPi.GPIO event callbacks or gpiozero Button handlers, removing stale entries, and triggering a restart or exit when definitions change.

	Inputs:
	    None.
	Outputs:
	    None: Updates GPIOdict/coincidence config, registers GPIO callbacks, and may restart or exit the process
	"""
	global sensor, sensors, oldSensor
	global INPgpioType,INPUTcount,INPUTlastvalue
	global GPIOdict, restart
	global oldRaw, lastRead
	global coincidence
	global minSendDelta
	global GPIOZERO

	try:
		restart = False
		found = {}

		inp, inpRaw, lastRead2 = U.doRead(lastTimeStamp=lastRead)
		if inp == "": return
		if lastRead2 == lastRead: return
		lastRead  = lastRead2
		if inpRaw == oldRaw: return
		oldRaw	   = inpRaw

		U.getGlobalParams(inp)
		if "sensors"			in inp : sensors =				(inp["sensors"])

		if sensor not in sensors:
			U.logger.log(20, "no {} sensor defined, exiting".format(G.program))
			exit()
			time.sleep(3000000)

		sens = sensors[sensor]

		changed = False
		for devId in sens:
			if devId not in oldSensor: 
				changed = True
			else:
				for item in sens[devId]:
					if item not in oldSensor:
						changed = True
					elif "{}".format(sens[devId][item]) != "{}".format(oldSensor[devId][item]):
						changed = True
					if changed: break
			if changed: break		 
		oldSensor = copy.deepcopy(sensors[sensor])

		if changed:
			found = {str(ii):{"RISING":0,"FALLING":0,"BOTH":0 } for ii in range(100)}
			for devId in sens:
				sss= sens[devId]
				if "gpio"									not in sss: continue
				if "risingOrFalling"						not in sss: continue
				if "minSendDelta"							not in sss: continue # in sec
				if "inpType"								not in sss: continue


				gpio						= sss["gpio"]
				risingOrFalling				= sss["risingOrFalling"]
				inpType						= sss["inpType"]

				try:	bounceTime			= int(sss.get("bounceTime",10))
				except: bounceTime			= 10

				try:	minSendDelta		= int(sss.get("minSendDelta",5))
				except: minSendDelta		= 5

				try:	deadTime			= float(sss.get("deadTime",1))
				except: deadTime			= 1

				try:	deadTimeBurst		= float(sss.get("deadTimeBurst",1.))
				except: deadTimeBurst		= 1

				try:	timeWindowForBursts = int(sss.get("timeWindowForBursts",-1))
				except: timeWindowForBursts = -1

				try:	minEventsinTimeWindowToTriggerBursts = int(sss.get("minEventsinTimeWindowToTriggerBursts",-1))
				except: minEventsinTimeWindowToTriggerBursts = -1

				try:	timeWindowForContinuousEvents = float(sss.get("timeWindowForContinuousEvents",-1))
				except: timeWindowForContinuousEvents = -1


				#U.logger.log(20,"setup 0 on gpio:{},  risingOrFalling:{}, useGPIO:{} new?:{}".format( gpio, risingOrFalling, useGPIO, gpio in GPIOdict) )

				found[gpio][risingOrFalling]		 = 1
				gpioPIN = int(gpio)
				if gpio in GPIOdict: ### this is update
						if GPIOdict[gpio]["bounceTime"] !=	bounceTime or GPIOdict[gpio].get("risingOrFalling","xxx") !=	 risingOrFalling: 
							restart=True
							return

						GPIOdict[gpio]["deadTime"]								= deadTime
						GPIOdict[gpio]["deadTimeBurst"]							= deadTimeBurst
						GPIOdict[gpio]["devId"]									= devId
						GPIOdict[gpio]["minSendDelta"]							= minSendDelta
						GPIOdict[gpio]["minEventsinTimeWindowToTriggerBursts"]	= minEventsinTimeWindowToTriggerBursts
						GPIOdict[gpio]["timeWindowForBursts"]					= timeWindowForBursts
						GPIOdict[gpio]["timeWindowForContinuousEvents"]			= timeWindowForContinuousEvents
						GPIOdict[gpio]["lastsendBurst"]							= 0
						GPIOdict[gpio]["lastsendCount"]							= 0
						GPIOdict[gpio]["lastsendContinuousEvent"]				= 0
						GPIOdict[gpio]["lastsendContinuousEventEND"]			= 0
						GPIOdict[gpio]["inpType"]	 = inpType
						continue 



				else: # new setup
					GPIOdict[gpio]={
									  "devId":							devId,
									  "inpType":						inpType,
									  "minSendDelta":					minSendDelta,
									  "bounceTime":						bounceTime,
									  "deadTime":						deadTime,
									  "deadTimeBurst":					deadTimeBurst,
									  "risingOrFalling":				risingOrFalling,
									  "timeWindowForBursts":			timeWindowForBursts,
									  "timeWindowForContinuousEvents":	timeWindowForContinuousEvents,
									  "minEventsinTimeWindowToTriggerBursts": minEventsinTimeWindowToTriggerBursts,
									  "lastSignal":						0,
									  "lastsendCount":					0,
									  "lastsendBurst":					0,
									  "lastsendContinuousEvent":		0,
									  "lastsendContinuousEventEND":		0,
									  "coincidence":					{},
									  "count":							0 }
					if useGPIO:
						if	 inpType == "open":
							GPIO.setup(int(gpio), GPIO.IN)
						elif inpType == "high":
							GPIO.setup(int(gpio), GPIO.IN, pull_up_down=GPIO.PUD_UP)
						elif inpType == "low":
							GPIO.setup(int(gpio), GPIO.IN, pull_up_down=GPIO.PUD_DOWN)
							if bounceTime > 0:
								GPIO.add_event_detect(int(gpio), GPIO.RISING,	callback=fillGPIOdict,  bouncetime=bounceTime)  
							else:
								GPIO.add_event_detect(int(gpio), GPIO.RISING,	callback=fillGPIOdict)  
						elif  risingOrFalling == "FALLING": 
							if bounceTime > 0:
								GPIO.add_event_detect(int(gpio), GPIO.FALLING,	callback=fillGPIOdict, bouncetime=bounceTime)  
							else:
								GPIO.add_event_detect(int(gpio), GPIO.FALLING,	callback=fillGPIOdict)  
						else:
							if bounceTime > 0:
								GPIO.add_event_detect(int(gpio), GPIO.BOTH,		callback=fillGPIOdict, bouncetime=bounceTime)  
							else:
								GPIO.add_event_detect(int(gpio), GPIO.BOTH,		callback=fillGPIOdict)  
					else:
						pull_up = None
						active_state = True
						if inpType == "high": 
							pull_up = True 
							active_state = None 
						if inpType == "low":  
							pull_up = False
							active_state = None  

						if bounceTime > 0:
							GPIOZERO[gpioPIN] = gpiozero.Button(gpioPIN, pull_up=pull_up, active_state=active_state, bounce_time=bounceTime) 
						else:
							GPIOZERO[gpioPIN] = gpiozero.Button(gpioPIN, pull_up=pull_up, active_state=active_state) 

						if   risingOrFalling == "RISING": 			GPIOZERO[gpioPIN].when_pressed  = fillFALLING 
						elif risingOrFalling == "FALLING": 			GPIOZERO[gpioPIN].when_released = fillRAISING
						else:
																	GPIOZERO[gpioPIN].when_pressed  = fillFALLING
																	GPIOZERO[gpioPIN].when_released = fillRAISING
						#U.logger.log(20,"setup 2 on gpio:{},  risingOrFalling:{}, pull_up:{}, active_state:{}, bounceTime:{}".format( gpioPIN, risingOrFalling, pull_up, active_state, bounceTime) )

					GPIOdict[gpio]["inpType"]	 = inpType
				
				
		oneFound = False
		restart = False
		delGPIO = {}
		U.logger.log(20, "GPIOdict: {}".format(GPIOdict))
		for gpio in GPIOdict:
			if gpio not in INPUTcount: INPUTcount[gpio] = 0
			GPIOdict[gpio]["count"] = INPUTcount[gpio]
			for risingOrFalling in ["FALLING","RISING","BOTH"]:
				if found[gpio][risingOrFalling] == 1: 
					oneFound = True
					continue
				if risingOrFalling in GPIOdict: # was deleted, need restart
					restart=True
					continue
			if GPIOdict[gpio] == {}: delGPIO[gpio]=1
			GPIOdict[gpio]["coincidence"] ={}		

		for gpio in delGPIO:
			if gpio in GPIOdict: del GPIOdict[gpio]
		
		if not oneFound:
			U.logger.log(20, "no gpios setup, exiting")
			exit()
		if	restart:
			U.logger.log(20, "gpios edge channel deleted, need to restart")
			U.restartMyself(param="", reason=" new definitions")
			
		sensorC = "INPUTcoincidence"
		coincidence2 ={}
		if sensorC in sensors:
			sens = sensors[sensorC]
			#print "sens:", sens
			for devIdC in sens:
				sss= sens[devIdC]
				if "INPUTdevId0"				not in sss: continue
				if "coincidenceTimeInterval"	not in sss: continue
				if "minSendDelta"				not in sss: continue
				if devIdC not in INPUTcount: INPUTcount[devIdC] = 0
				coincidence2[devIdC]={}
				coincidence2[devIdC]["gpios"] ={}
				coincidence2[devIdC]["coincidenceTimeInterval"] = float(sens[devIdC]["coincidenceTimeInterval"])/1000.
				coincidence2[devIdC]["lastSend"] = 0
				coincidence2[devIdC]["minSendDelta"] = float(sens[devIdC]["coincidenceTimeInterval"])
				for ii in range(4):
					if "INPUTdevId"+str(ii) not in sens[devIdC]: continue
					devId = sens[devIdC]["INPUTdevId"+str(ii)]
					if int(devId) < 1: continue
					for gpio in GPIOdict:
						if devId != GPIOdict[gpio]["devId"]: continue
						GPIOdict[gpio]["coincidence"][devIdC] = True
						coincidence2[devIdC]["gpios"][gpio]  = 0


		for devIdC in coincidence2:
			if devIdC not in coincidence: 	coincidence[devIdC] = copy.copy(coincidence2[devIdC])
			else: 							coincidence[devIdC]["coincidenceTimeInterval"] = copy.copy(coincidence2[devIdC]["coincidenceTimeInterval"])
		delCoincidence ={}
		for devIdC in coincidence:
			if devIdC not in coincidence2: delCoincidence[devIdC] = True
		for devIdC in delCoincidence:
			del coincidence[devIdC]
		U.logger.log(10,"GPIOdict: {}".format(GPIOdict) )
		#print coincidence

	except Exception as e:
		U.logger.log(20,"", exc_info=True)
				

 
def fillRAISING(but):
	#U.logger.log(20,"fillRAISING   pin:{}".format(but.pin.number))
	"""gpiozero when_released callback for a falling/rising edge that forwards the event to fillGPIOdict using the button's pin number.

	Inputs:
	    but (gpiozero.Button): The button object whose pin.number identifies the GPIO pin
	Outputs:
	    None: Calls fillGPIOdict with the pin number to record the pulse event
	"""
	fillGPIOdict(but.pin.number)
 
def fillFALLING(but):
	#U.logger.log(20,"fillFALLING   pin:{}".format(but.pin.number))
	"""Falling-edge GPIO interrupt callback that simply forwards the pin number of the triggering button to fillGPIOdict for event processing.

	Inputs:
	    but (object): Button/event object carrying a .pin.number attribute identifying the GPIO pin
	Outputs:
	    None: delegates to fillGPIOdict; no return value
	"""
	fillGPIOdict(but.pin.number)


def fillGPIOdict(gpioINT):
	"""Core pulse-input event handler invoked on each GPIO edge: applies dead-time filtering, increments the pulse count, evaluates burst and continuous-event windows, checks coincidence groups across multiple GPIOs, and dispatches resulting count/burst/continuous data to Indigo via sendURL while persisting the count.

	Inputs:
	    gpioINT (int): GPIO pin number (coerced to int) that fired the edge event
	Outputs:
	    None: updates global GPIO/burst/coincidence state, sends data via U.sendURL, and writes INPUTcount to file
	"""
	global INPUTcount, GPIOdict, sensor, BURSTS, lastGPIO, contEVENT, sensors
	global GPIOZERO

	gpioINT	= int(gpioINT)
	gpio	= str(gpioINT)
	ggg		= GPIOdict[gpio]
	tt		= time.time()
	countChanged = False
	#U.logger.log(20,"{} edge on gpio: tt-lastSignal:{:.2f};  deadTime:{:.2f}".format( gpio, tt- ggg["lastSignal"], ggg["deadTime"]) )
	if tt- ggg["lastSignal"] > ggg["deadTime"]:	 
		if gpio not in INPUTcount: INPUTcount[gpio] = 0
		INPUTcount[gpio]+=1
		ggg["count"] = INPUTcount[gpio]
		#print gpioINT, INPUTcount[gpioINT]
		ggg["lastSignal"] = tt
		#U.logger.log(10,"{} edge on gpio: {},	count: {}  timest: {:6.1f}, lastSendC: {:6.1f}, minSendDelta:{}, count:{}".format(risingOrFalling, gpio, ggg["count"], tt, ggg["lastsendCount"], ggg["minSendDelta"], INPUTcount[gpio]))
		countChanged = True

	###############	 this EVENTtype requires a minEventsinTimeWindowToTriggerBursts  in timeWindowForBursts to trigger ###
	burst=0
	bbb =  BURSTS[gpioINT]
	if ggg["minEventsinTimeWindowToTriggerBursts"] > 0:
		ll	=len(bbb)
		for kk in range(ll):
			ii = ll - kk -1
			if tt-bbb[ii][0] > ggg["timeWindowForBursts"]: 
				del bbb[ii]
		#U.logger.log(10, "BURST: "+str(ll)+""+str(tt)+"	 "+ str(bbb)+" "+str(ggg["timeWindowForBursts"] ))
		ll	=len(bbb)
		if ll == 0	or (tt - bbb[-1][0]  > ggg["deadTimeBurst"]): 
			bbb.append([tt,1])
			#U.logger.log(10, "BURST: in window "+str(ggg["timeWindowForBursts"]))
			ll	+=1
			delupto = -1
			for kk in range(ll):
					ii = ll - kk -1
					try:
						bbb[ii][1]+=1
					except:
						U.logger.log(20, " burst  gpio:{}; bbb:{}; ll:{};  ii:{} ".format(gpio, bbb, ll, ii )  )
						break
					if bbb[ii][1] >= ggg["minEventsinTimeWindowToTriggerBursts"]:
						burst	= tt
						delupto = ii-1
						bbb[ii][1]	= tt+ggg["timeWindowForBursts"]
						break
			if delupto >0:
				for kk in range(delupto):
					del bbb[delupto - kk -1]
	if burst ==0:  ggg["lastsendBurst"] = 0

	data = {"sensors":{sensor:{ggg["devId"]:{}}}}

	###############	 this EVENTtype requires a pulse to start the CONT event, will extend event if new pulse arrives before timeWindowForContinuousEvents is over  ###
	cEVENTtt=0
	if ggg["timeWindowForContinuousEvents"] > 0:
		if contEVENT[gpioINT] == -1 or contEVENT[gpio] == 0:  # new event 
			cEVENTtt = tt
		elif  contEVENT[gpioINT] > 0 and tt - contEVENT[gpioINT] > ggg["timeWindowForContinuousEvents"]:
			# was expired send off then send ON 
			if tt - ggg["lastsendContinuousEventEND"] > ggg["minSendDelta"]:
				data["sensors"][sensor][ggg["devId"]]["continuous"]		 = -1
				ggg["lastsendContinuousEventEND"] = tt
				ggg["lastsendContinuousEvent"] = 0
		#  or just conti nue old c event = just update contEVENT not need to send data 
		contEVENT[gpioINT] =  tt

	

	if (tt - ggg["lastsendBurst"] > ggg["minSendDelta"]) and burst > 0 :  
			data["sensors"][sensor][ggg["devId"]]["burst"]		= int(burst)
			data["sensors"][sensor][ggg["devId"]]["count"]		= ggg["count"]
			ggg["lastsendBurst"] = tt
			ggg["lastsendCount"] = tt
			if burst >0:
				lastGPIO= U.doActions(data["sensors"],lastGPIO, sensors, sensor,theAction="PulseBurst")

	if (tt - ggg["lastsendContinuousEvent"] > ggg["minSendDelta"]) and cEVENTtt > 0 :	
			data["sensors"][sensor][ggg["devId"]]["continuous"]		 = int(cEVENTtt)
			data["sensors"][sensor][ggg["devId"]]["count"]			 = ggg["count"]
			ggg["lastsendContinuousEvent"] = tt
			ggg["lastsendContinuousEventEND"] = 0
			ggg["lastsendCount"] = tt
			if cEVENTtt >0:
				lastGPIO= U.doActions(data["sensors"],lastGPIO, sensors, sensor,theAction="PulseContinuous")

	if (tt - ggg["lastsendCount"] > ggg["minSendDelta"]) and countChanged:	
			data ["sensors"][sensor][ggg["devId"]]["count"]			= ggg["count"]
			ggg["lastsendCount"] = tt

	if data == {"sensors":{sensor:{ggg["devId"]:{}}}}: data = {"sensors":{}}

	if len(GPIOdict[gpio]["coincidence"]) > 0:
			for devIdC in coincidence:
				if gpio in coincidence[devIdC]["gpios"]:
					coincidence[devIdC]["gpios"][gpio] = tt
			for devIdC in coincidence:
				triggerC = True
				for gp in coincidence[devIdC]["gpios"]:
					if tt - coincidence[devIdC]["gpios"][gp] > coincidence[devIdC]["coincidenceTimeInterval"]: 	
						triggerC = False
						break
				if triggerC:		
						try: 	INPUTcount[devIdC] +=1
						except: INPUTcount[devIdC] = 1
						coincidence[devIdC]["lastSend"] = tt
						if "INPUTcoincidence" not in data["sensors"]: data["sensors"]["INPUTcoincidence"] = {}
						if devIdC not in data["sensors"]["INPUTcoincidence"]: data["sensors"]["INPUTcoincidence"][devIdC] ={}
						data["sensors"]["INPUTcoincidence"][devIdC]["count"] = INPUTcount[devIdC]
						if False:
							out = ""
							for gp in coincidence[devIdC]["gpios"]:
								out+= "{}: {:.5f}; ".format(gp, tt- coincidence[devIdC]["gpios"][gp] )
							U.logger.log(10, "coincidenceTrigger  devIdC:{:<12}; tt:{:.2f}; count:{};  GPIOS-dt:{}   window:{:.5f}, last send:{}, data:{}".format(devIdC, tt, INPUTcount[devIdC], out, coincidence[devIdC]["coincidenceTimeInterval"], coincidence[devIdC]["lastSend"], data)  )
	if sensor in data["sensors"] or "INPUTcoincidence" in data["sensors"]:
			if sensor in data["sensors"]:
				data["sensors"][sensor][ggg["devId"]]["time"] = tt
				data["sensors"][sensor][ggg["devId"]]["eventOrPeriod"] = "event"
			U.sendURL(data, wait=False)
			U.writeINPUTcount(INPUTcount)

	#print 	INPUTcount			

def resetContinuousEvents():
	"""Periodically scans all configured GPIOs with continuous-event windows and, for any whose continuous event has expired beyond its time window, sends an OFF (continuous = -1) update to Indigo and resets the related send timers.

	Inputs:
	    None.
	Outputs:
	    None: sends continuous-event end data via U.sendURL and mutates global GPIOdict/contEVENT state
	"""
	global GPIOdict, contEVENT, sensor
	tt = time.time()
	for gpio in GPIOdict:
		ggg = GPIOdict[gpio]
		if ggg["timeWindowForContinuousEvents"] > 0:
			igpio= int(gpio)
			if	contEVENT[igpio] > 0:
				if	tt - contEVENT[igpio]  > ggg["timeWindowForContinuousEvents"]:
					if tt - ggg["lastsendContinuousEventEND"] > ggg["minSendDelta"]:
						contEVENT[igpio] =	-1
						# was expired send off then send ON 
						data = {"sensors":{sensor:{ggg["devId"]:{}}}}
						data["sensors"][sensor][ggg["devId"]]["continuous"] = -1
						U.sendURL(data,wait=False)
						ggg["lastsendContinuousEventEND"] = tt
						ggg["lastsendContinuousEvent"] = 0

  
def execMain():
	"""Main entry point for the pulse-input sensor program: initializes all global state, sets up logging, kills stale instances, loads persisted counts and parameters, then runs an endless loop that resets continuous events, periodically reloads params, checks for resets/restarts, sends alive echoes, and pushes accumulated count data to Indigo.

	Inputs:
	    None.
	Outputs:
	    None: runs an infinite service loop; initializes globals, logs, sends data via U.sendURL, may exit() or restart
	"""
	global sensors, sensor, oldSensor, INPUTcount
	global oldParams
	global GPIOdict, restart, BURSTS, lastGPIO, contEVENT
	global oldRaw,	lastRead, lastSend
	global minSendDelta
	global coincidence
	global GPIOZERO

	GPIOZERO		= {}
	oldSensor		= {}
	coincidence		= {}
	oldRaw			= ""
	lastRead		= 0
	minSendDelta	= 50
	sensor			= G.program
	INPUTcount		= {}
	BURSTS			= [[]	  for i in range(50)]
	contEVENT		= [0	  for i in range(50)]
	lastGPIO		= [""	  for ii in range(50)]
	oldParams		= ""
	GPIOdict		= {}
	restart			= False
	countReset		= False


	U.setLogging()

	if not gpioOK:	U.logger.log(20, "no GPIO backend on this rpi (neither RPi.GPIO nor gpiozero) - pulses cannot be counted; install rpi-lgpio on a pi5")
	elif not useGPIO:	U.logger.log(20, "counting pulses through gpiozero - RPi.GPIO was not available. Edge events go through the pin factory, fast pulse trains may lose counts")


	myPID		= str(os.getpid())
	U.killOldPgm(myPID,G.program+".py")# old old instances of myself if they are still running


	sensors			  ={}
	loopCount		  = 0

	U.logger.log(20, "starting "+G.program+" program")

	INPUTcount = U.readINPUTcount()
	U.logger.log(20, " INPUTcount:{}".format(INPUTcount) )

	readParams()



	G.lastAliveSend		= time.time()
	# set alive file at startup


	if U.getIPNumber() > 0:
		U.logger.log(20," sensors no ip number  exiting ")
		time.sleep(10)
		exit()

	G.tStart = time.time()
	lastRead = time.time()
	shortWait = 0.5
	lastSend  = 0
	lastEcho  = 0
	
	while True:
		try:
			newData = False
		
			resetContinuousEvents()

			if loopCount %10 == 0:
				U.manageActions("-loop-")
				if loopCount%5 == 0:
					countReset = checkReset()
					if countReset:
						for gpio in GPIOdict:
							if str(gpio) not in INPUTcount: 
								INPUTcount[str(gpio)] = 0
							if INPUTcount[str(gpio)] == 0: 
								GPIOdict[gpio]["count"] = 0
		
					##U.checkIfAliveNeedsToBeSend(lastMsg)
					if time.time()- lastRead > 10:
							readParams()
							lastRead = time.time()

					if restart:
						U.restartMyself(param="", reason=" new definitions")

				if time.time() - lastEcho  > 180:
						lastEcho = time.time()
						U.echoLastAlive(G.program)

				data = {"sensors":{}}
				if ((time.time() - lastSend >  2) and loopCount > 3 ) or countReset:
					data["sensors"][sensor] = {}
					for gpio in GPIOdict:
							#U.logger.log(10, u" gpio:{} passed; data:{} ".format(gpio, data) )
							if "devId" not in GPIOdict[gpio]: continue
							#U.logger.log(20, u" DT:{}, minsend:{} ".format(time.time() - GPIOdict[gpio]["lastsendCount"], minSendDelta) )
							if (time.time() - GPIOdict[gpio]["lastsendCount"]) >  G.sendToIndigoSecs:
								devId = GPIOdict[gpio]["devId"] 
								data["sensors"][sensor][devId] = {"count": GPIOdict[gpio]["count"],"time":time.time(), "eventOrPeriod":"period"}
								#U.logger.log(10, u" gpio:{} passed; data:{} ".format(gpio, data) )
								newData = True
								GPIOdict[gpio]["lastsendCount"] = time.time()
				for devIdC in coincidence:
					if ((time.time() - coincidence[devIdC]["lastSend"] >  G.sendToIndigoSecs) and loopCount > 3 ) or countReset:
						if "INPUTcoincidence" not in data: data["sensors"]["INPUTcoincidence"] = {}
						data["sensors"]["INPUTcoincidence"][devIdC] = {"count": INPUTcount[devIdC],"time":time.time()}
						coincidence[devIdC]["lastSend"] = time.time()
						newData = True
				if newData:
					#U.logger.log(20, u"send data:{} ".format(data) )
					U.sendURL(data,wait=False)
					lastSend = time.time()
					loopCount = 0
					countReset = False
					U.writeINPUTcount(INPUTcount)


			loopCount+=1
			time.sleep(shortWait)
		except Exception as e:
			U.logger.log(20,"", exc_info=True)
			time.sleep(5.)

execMain()
try: 	G.sendThread["run"] = False; time.sleep(1)
except: pass

sys.exit(0)
