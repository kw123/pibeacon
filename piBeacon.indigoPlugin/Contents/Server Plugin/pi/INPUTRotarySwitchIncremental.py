#!/usr/bin/env python
# -*- coding: utf-8 -*-
# by Karl Wachs
# Feb 3 2019
# version 0.95
##
## py prept 
## read  encoded continuous incremantal rotaty switch, send integer value to indogo every 90 secs or if changed
##   2 gpios are read. they go 1 0 1 0 .. most have 0=ON and 1 = off
## one full step is 
#  B: 011001100110
#  A: 001100110011
# and oposit direction:
#  B: 001100110011
#  A: 011001100110 
# one full step is 4 bits
# for fast changing events: try: 
#   PIgGPIO  events put into queue(gpioEVENTthread), get by a thread (workQueue) and anaylzed with workEvent
#
# workEVENT and executePinChange have options to
# supports bounces and to cover for missing signals in the steps.
#  ignorePinValue =
#   0= no management
#   1 = if event pin not changed: set event pin true if TRUE would be next expected signal (not if threads & queue are used)
#   2 = if event pin not changed: flip PIN value is same as last value (not if threads & queue are used, as working on queue and receiving are out of sync)
#   3 = if event pin not changed: add flipped pin event to sequence
##

import	sys, os, subprocess, copy
import	time,datetime
import	json

sys.path.append(os.getcwd())
import	piBeaconUtils	as U
import	piBeaconGlobals as G

G.program = "INPUTRotarySwitchIncremental"


#################################
def readParams():
		"""Reads the latest plugin parameter file, and if sensor definitions changed, updates each device's INPUTS configuration (pins A/B, inverse, transition, ignore-pin, reset-time, increment options), initializes count tracking, sets the GPIO backend to pigpio with threads, and starts GPIO or restarts the program when pins change.

		Inputs:
		    None.
		Outputs:
		    None: Updates global sensors/INPUTS/counts config, starts GPIO, may restart the program
		"""
		global sensors
		global sensor
		global oldRaw, lastRead, INPUTS
		global counts, countSignals
		global useWhichGPIO, useThreads


		inp, inpRaw, lastRead2 = U.doRead(lastTimeStamp=lastRead)
		if inp == "": return
		if lastRead2 == lastRead: return
		lastRead   = lastRead2
		if inpRaw == oldRaw: return
		oldRaw	   = inpRaw

		oldSensors  = sensors

		U.getGlobalParams(inp)
		if "sensors"			in inp : sensors =				(inp["sensors"])
		if oldSensors == sensors: return 

		restart = False
			
		if G.program  not in sensors:
			U.logger.log(20, "no {} sensor defined, exiting".format(G.program))
			stopProgram()

		oldINPUTS  = copy.deepcopy(INPUTS)
		restart    = False
		if sensor in sensors:
			for devId in sensors[sensor]:
				new = False
				sens = sensors[sensor][devId]
				if devId not in INPUTS: 
					INPUTS[devId]  = {"pinALastValue":9999999, "incrementIfGT4Signals": "0", "lastChangeTime":0, "pinBLastValue":9999999, "pinA":21, "pinB":20, "inverse": True,"direction": 0, "newCycle":False, "distinctTransition":False, "ignorePinValue": "0","lastEvent": 0, "resetTimeCheck":0.001}
					#INPUTS[devId]["LockRotary"] = threading.Lock()		# create lock for rotary switch

				if devId not in counts:
					counts[devId] = 0
				if devId not in countSignals:
					countSignals[devId] = 0

				if "INPUT_0" in sens:
					if  INPUTS[devId]["pinA"] != int(sens["INPUT_0"]):
						INPUTS[devId]["pinA"]  = int(sens["INPUT_0"])
						new = True

				if "INPUT_1" in sens:
					if  INPUTS[devId]["pinB"] != int(sens["INPUT_1"]):
						INPUTS[devId]["pinB"]  = int(sens["INPUT_1"])
						new = True

				if "resetTimeCheck" in sens:
						INPUTS[devId]["resetTimeCheck"]  		= float(sens["resetTimeCheck"])

				if "inverse" in sens:
						INPUTS[devId]["inverse"]   				= (sens["inverse"] == "1")

				if "distinctTransition" in sens:
						INPUTS[devId]["distinctTransition"]		= (sens["distinctTransition"] == "1")

				if "ignorePinValue" in sens:
						INPUTS[devId]["ignorePinValue"] 		= int(sens["ignorePinValue"])

				if "incrementIfGT4Signals" in sens:
						INPUTS[devId]["incrementIfGT4Signals"]  = (sens["incrementIfGT4Signals"]=="1")

				useWhichGPIO = "pig"
				useThreads	 = True
						
					
				if oldINPUTS != {} and new:
					restart = True
					break
				elif oldINPUTS == {} or new:
					startGPIO(devId)
		if restart:
			stopProgram(action ="onlyThread")
			U.restartMyself(reason="new parameters")
		return 




#################################
def saveCounts():
	"""Persists the current per-device counts dictionary to a JSON file in the plugin home directory named after the program with a .counts extension.

	Inputs:
	    None.
	Outputs:
	    None: Writes the counts dict as JSON to disk
	"""
	global counts
	f= open(G.homeDir+G.program+".counts", "w")
	f.write(json.dumps(counts))	
	f.close()

#################################
def readCounts():
	"""Loads the persisted per-device counts from the program's .counts JSON file into the global counts dict, defaulting to an empty dict if the file is missing or unparseable.

	Inputs:
	    None.
	Outputs:
	    None: Populates the global counts dict from the .counts file
	"""
	global counts
	if os.path.isfile(G.homeDir+G.program+".counts"):
		f= open(G.homeDir+G.program+".counts", "r")
		try:    counts = json.loads(f.read())	
		except: counts ={}
		f.close()
	else:
		counts= {}
	return 


#################################
def pigEVENTthread(pin, level, tick):
	"""pigpio edge-event callback for an incremental rotary encoder: looks up the device by pin, reads the current states of both A and B pins based on which pin fired and its level, then enqueues a (pin, stateA, stateB, timestamp) tuple to the worker thread queue.

	Inputs:
	    pin (int): GPIO pin number that triggered the event
	    level (int): Edge level (1=up/0=down/other=watchdog) of the triggered pin
	    tick (int): pigpio microsecond timestamp of the event
	Outputs:
	    None: Records lastTick and puts an event tuple on the thread queue
	"""
	global lastTick
	global INPUTS, pinsToDevid
	global threadDict
	global debug
	global PIGPIO
	devIDUsed = pinsToDevid[pin]
	IP = INPUTS[devIDUsed]
	pinA= IP["pinA"]
	pinB= IP["pinB"]
	if pin == pinB:
		stateB = level == 0
		stateA =  (PIGPIO.read(pinA) == 0)
	if pin == pinA:
		stateA = level == 0
		stateB =  (PIGPIO.read(pinB) == 0)
	if   level == 1: level = "U"
	elif level == 0: level = "D"
	else:			 level = "N"

	lastTick = tick
	threadDict["queue"].put(( pin, stateA, stateB, tick/1000. ))
	return 


#################################
def workQueue():
	"""Worker thread loop that drains the encoder event queue, dispatching each queued (pin, stateA, stateB, tt) item to workEvent until the stop flag is set; sleeps briefly when the queue is empty and logs any exception.

	Inputs:
	    None.
	Outputs:
	    None: Processes queued encoder events via workEvent until stopped
	"""
	global lastTick
	global INPUTS, pinsToDevid
	global threadDict
	try:
		while True:
			if threadDict["stopThread"]: return 
			while not threadDict["queue"].empty():
				items = threadDict["queue"].get() 
				workEvent(items[0], stateA=items[1], stateB=items[2], tt=items[3])
				if threadDict["stopThread"]: return 
			time.sleep(0.2)
	except Exception as e:
		U.logger.log(30,"", exc_info=True)
	return


#################################
def startGPIO(devId):
	"""Configures the GPIO pins (pinA/pinB) for a rotary encoder device via pigpio, starting the pigpiod daemon and a worker queue thread if needed, and registers EITHER_EDGE callbacks so pin transitions are dispatched to the event handler.

	Inputs:
	    devId (str): Device identifier whose pinA/pinB are looked up in INPUTS and bound to pigpio edge callbacks
	Outputs:
	    None: Registers pigpio callbacks, starts daemon/thread, and updates pinsToDevid and threadDict; logs on error
	"""
	global INPUTS, pinsToDevid
	global threadDict, useThreads
	global useWhichGPIO, PIGPIO, pigpio, lastTick
	global debug

	try:
		pinsToDevid[INPUTS[devId]["pinA"]] = devId
		pinsToDevid[INPUTS[devId]["pinB"]] = devId
		U.logger.log(30, "pinsToDevid {}".format(pinsToDevid))

		if useWhichGPIO == "pig":
			if PIGPIO == "":
				import pigpio
				import threading 
				try: import Queue
				except: import queue as Queue
				if not U.pgmStillRunning("pigpiod"): 	
					U.logger.log(30, "starting pigpiod")
					subprocess.call("sudo pigpiod &", shell=True)
					time.sleep(0.5)
					if not U.pgmStillRunning("pigpiod"): 	
						U.logger.log(30, " restarting myself as pigpiod not running, need to wait for timeout to release port 8888")
						time.sleep(20)
						U.restartMyself(reason="pigpiod not running")
						exit(0)

				PIGPIO = pigpio.pi()
				threadDict["queue"] = Queue.Queue()
				threadDict["thread"] = threading.Thread(target=workQueue, name="workQueue" )
				threadDict["thread"].start()
				
			if devId not in threadDict:
				threadDict[devId] ={ "pinA":"",  "pinB":"" }

			U.logger.log(30, "PIGPIO setup for devId"+str(devId)+"  "+ str(INPUTS[devId]))
			PIGPIO.set_mode( INPUTS[devId]["pinA"], pigpio.INPUT)
			PIGPIO.set_pull_up_down( INPUTS[devId]["pinA"], pigpio.PUD_UP )
			PIGPIO.set_mode( INPUTS[devId]["pinB"], pigpio.INPUT)
			PIGPIO.set_pull_up_down( INPUTS[devId]["pinB"], pigpio.PUD_UP )

			threadDict[devId]["pinA"] = PIGPIO.callback(INPUTS[devId]["pinA"], pigpio.EITHER_EDGE, pigEVENTthread)
			threadDict[devId]["pinB"] = PIGPIO.callback(INPUTS[devId]["pinB"], pigpio.EITHER_EDGE, pigEVENTthread)
			return
		else:
			exit()
		

		return
	except Exception as e:
		U.logger.log(30,"", exc_info=True)
		U.logger.log(30,"start {}  {} ".format(G.program, sensors))
	return


	   
#################################
def workEvent(pin, stateA=-1, stateB =-1, tt=-1):
	"""Handles a rotary-encoder pin edge event: resolves the device from the pin, reads or normalizes the A/B pin states (applying inversion and ignorePinValue compensation), defaults the timestamp, and forwards the resolved states to executePinChange.

	Inputs:
	    pin (int): GPIO pin number that triggered the event, used to look up the device
	    stateA (bool or int): State of pin A; -1 means read it live from pigpio
	    stateB (bool or int): State of pin B; -1 means read it live from pigpio
	    tt (float): Event timestamp; -1 means use current time.time()
	Outputs:
	    None: Delegates to executePinChange; logs on error
	"""
	global INPUTS, pinsToDevid, newData, PIGPIO
	global counts
	global countSignals
	global debug
	try:
			devIDUsed = pinsToDevid[pin]
			IP = INPUTS[devIDUsed]
			pinA= IP["pinA"]
			pinB= IP["pinB"]

			if stateA==-1 and stateB ==-1:
				stateA = PIGPIO.read(pinA) == 0 
				stateB = PIGPIO.read(pinB) == 0
	
			if IP["inverse"]:
				stateA = not stateA
				stateB = not stateB

			if tt == -1:  
				tt = time.time()


			if  IP["ignorePinValue"] == 1 and not useThreads: 
				if pin == pinB :
					if stateB == IP["pinBLastValue"]:
						if  IP["direction"] == "+":
							if not stateB: 
								stateB = True
				else:
					if stateA == IP["pinALastValue"]:
						if  IP["direction"] == "-":
							if not stateA  == 1: 
								stateA = True
							
			elif  IP["ignorePinValue"] == 2 and not useThreads: 
				if pin == pinB :
					if stateB == IP["pinBLastValue"]:
						stateB = not stateB
				else:
					if stateA == IP["pinALastValue"]:
						stateA = not stateA

							
			elif  IP["ignorePinValue"] == 3: 
				if pin == pinB :
					if stateB == IP["pinBLastValue"]:
						executePinChange(devIDUsed, pin, stateA, not stateB, tt)
				else:
					if stateA == IP["pinALastValue"]:
						executePinChange(devIDUsed, pin, not stateA, stateB, tt)

			executePinChange(devIDUsed, pin, stateA, stateB, tt)

	except Exception as e:
			U.logger.log(30,"", exc_info=True)

			return 

#################################
def executePinChange(devIDUsed, pin, stateA, stateB, tt):
	"""Applies the quadrature decoding logic for a rotary encoder: tracks new-cycle state and last pin values, and increments or decrements the device count (setting direction) when a valid A/B transition completes a cycle, also handling reset timeouts and the increment-on-many-signals option.

	Inputs:
	    devIDUsed (str): Device identifier indexing INPUTS, counts, and countSignals
	    pin (int): GPIO pin number of the transition (pinA or pinB)
	    stateA (bool): Current state of pin A
	    stateB (bool): Current state of pin B
	    tt (float): Timestamp of the event
	Outputs:
	    None: Mutates counts, direction, newCycle, timing fields, and sets newData; logs on error
	"""
	global INPUTS, pinsToDevid, newData
	global counts
	global countSignals
	global debug

	try:
			IP = INPUTS[devIDUsed]
			pinA= IP["pinA"]
			pinB= IP["pinB"]
			countSignals[devIDUsed] += 1

			if stateA ==  IP["pinALastValue"] and stateB ==  IP["pinBLastValue"]:
				return 

			# save last values..
			if (not stateA) and (not stateB):
				IP["newCycle"] = True

			if (tt - IP["lastChangeTime"]) > IP["resetTimeCheck"] and not IP["newCycle"] and countSignals[devIDUsed]	> 4: 
				IP["newCycle"] = True
			if (tt - IP["lastEvent"])      > IP["resetTimeCheck"] and not IP["newCycle"] and countSignals[devIDUsed]	> 4: 
				IP["newCycle"] = True

			if (not IP["pinALastValue"]) and (not IP["pinBLastValue"]): IP["newCycle"]= True

			# must start new cyle first ie both pins have to be False.. avoid double triggers eg B is true, A true, false, true would trigger 2 counts
			if  IP["newCycle"]:
				if stateA and stateB:
					if pin == pinB:
						#	 A must have been alread TRUE         dont check if not required         both pins switched at the same time 
						if (stateA ==  IP["pinALastValue"] or not  IP["distinctTransition"]  ) or ( not IP["pinALastValue"] and  not IP["pinBLastValue"] ):
							counts[devIDUsed] 		+= 1
							IP["direction"]      	= True
							IP["newCycle"]       	= False
							IP["lastEvent"]      	= tt
							countSignals[devIDUsed]	=0
					else:
						if ( stateB ==  IP["pinBLastValue"] or not  IP["distinctTransition"] ) or ( not IP["pinALastValue"] and  not IP["pinBLastValue"] ):
							counts[devIDUsed] 		-= 1
							IP["direction"]      	= False
							IP["newCycle"]       	= False
							IP["lastEvent"]      	= tt
							countSignals[devIDUsed]	= 0
					newData = True

			if 	countSignals[devIDUsed] > 4 and IP["incrementIfGT4Signals"] and (tt- IP["lastEvent"]) > IP["resetTimeCheck"]:
				if IP["direction"]: counts[devIDUsed]  +=1
				else:				counts[devIDUsed]  -=1
				IP["newCycle"]       = False
				IP["lastEvent"]      = tt
				countSignals[devIDUsed]  =0



			if stateA !=  IP["pinALastValue"] or stateB !=  IP["pinBLastValue"]:
				IP["lastChangeTime"] = tt#


			IP["pinALastValue"] = stateA
			IP["pinBLastValue"] = stateB
	except Exception as e:
			U.logger.log(30,"", exc_info=True)
	return 




#################################
def checkReset():
	"""Checks for the existence of a reset trigger file in the temp directory; if found, deletes it and reports that a reset was requested.

	Inputs:
	    None.
	Outputs:
	    bool: True if the reset file existed (and was removed), otherwise False
	"""
	if not os.path.isfile(G.homeDir+"temp/"+ G.program+".reset"): return False
	try:    os.remove(G.homeDir+"temp/" + G.program+".reset")
	except: pass
	return True


#################################
def stopProgram(action=""):
	"""Stops the background worker thread by signaling stopThread and joining it; unless action is 'onlyThread', then exits the whole program via sys.exit.

	Inputs:
	    action (str): If 'onlyThread', only stops the thread without exiting the process
	Outputs:
	    None: Joins the worker thread and may call sys.exit(0)
	"""
	global threadDict, stopThread

	if "tread" in threadDict:
		stopThread = True
		threadDict["thread"].join()
	if action == "onlyThread":
		return 
	sys.exit(0)


def execMain():
	#################################
	#################################
	######      MAIN     ############
	#################################
	#################################
	"""Main entry point of the rotary-switch driver: initializes global state, sets up logging, kills old instances, loads saved counts and parameters, then runs the main loop that reads counts, sends changed data via URL, periodically re-reads params, handles reset requests, and finally stops the program.

	Inputs:
	    None.
	Outputs:
	    None: Runs the indefinite main loop and terminates the program via stopProgram
	"""
	global sensors
	global sensor
	global oldRaw, lastRead
	global INPUTS
	global newData
	global counts
	global debug
	global countSignals
	global useThreads
	global useWhichGPIO
	global threadDict
	global PIGPIO
	global lastTick
	global pinsToDevid
	
	
	
	#### threadding does not work with edge detect, can have only ONE edge detect !!!!
	threadDict			= {"stopThread":False}
	lastTick 			= 0.
	PIGPIO				= ""	
	useWhichGPIO		= "pig"
	useThreads			= True
	countSignals		= {}
	debug 				= 0
	oldRaw				= ""
	lastRead			= 0
	INPUTS				= {}
	sensors				= {}
	pinsToDevid			= {}
	newData				= False
	
	###################### constants #################
	
	U.setLogging()
	
	myPID		= str(os.getpid())
	U.killOldPgm(myPID,G.program+".py")# old old instances of myself if they are still running
	
	
	sensor			  = G.program
	
	U.logger.log(20, "starting "+G.program+" program")
	
	
	readCounts()
	
	readParams()
	
			
	
	shortWait			= 0.3	 
	lastEverything		= time.time()-10000. # -1000 do the whole thing initially
	G.lastAliveSend		= time.time()
	
	#print "shortWait",shortWait	 
	
	if U.getIPNumber() > 0:
		U.logger.log(30," sensors no ip number  exiting ")
		time.sleep(10)
		stopProgram()
	
	
	lastMsg  = 0
	quick    = 0
	
	lastData = {}
	G.tStart = time.time() 
	lastRead = time.time()
	shortWait = 40
	loopCount  = 0
	
	while True:
		try:
			data0={}
			data ={"sensors":{}}
			tt= time.time()
			if sensor not in sensors: break
			for devId in  sensors[sensor]:
				if devId not in lastData: lastData[devId]={"INPUT":0}
				data0[devId] = {"INPUT":counts[devId]}
	
			if	data0 != lastData or tt - lastMsg > 100:
				saveCounts()
				lastMsg = tt
				lastData = copy.copy(data0)
				data["sensors"][sensor] = data0
				#print data, counts
				U.sendURL(data)
			quick = U.checkNowFile(G.program)
			if loopCount%50 == 0:
				U.echoLastAlive(G.program)
				
			if time.time()- lastRead > 10:
				readParams()
				lastRead = time.time()
	
			loopCount+=1
			for iii in range(100):
				time.sleep(shortWait/100.)
				if newData: break
	
			if checkReset():
				for devId in counts:
					counts[devId] = 0
					saveCounts()
	
			newData = False
		except Exception as e:
			U.logger.log(30,"", exc_info=True)
			time.sleep(5.)
	
	stopProgram()
	try: 	G.sendThread["run"] = False; time.sleep(1)
	except: pass

execMain()