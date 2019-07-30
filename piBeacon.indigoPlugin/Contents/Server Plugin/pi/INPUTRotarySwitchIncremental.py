#!/usr/bin/env python
# -*- coding: utf-8 -*-
# by Karl Wachs
# Feb 3 2019
# version 0.95
##
## read  encoded continuous incremantal rotaty switch, send integer value to indogo every 90 secs or if changed
##   2 gpios are read. they go 1 0 1 0 .. most have 0=ON and 1 = off
## one full step is 
#  B: 011001100110
#  A: 001100110011
# and oposit direction:
#  B: 001100110011
#  A: 011001100110 
# one full step is 4 bits
# this py program can read the gpio pins through regular GPIO edge.BOTH events(workEvent), and analyzed with workEvent
# for fast changing events: try: 
#   RPI.GPIO events put into queue(pigEVENTthread),  get by a thread (workQueue) and analyzed with workEvent
#   PIgGPIO  events put into queue(gpioEVENTthread), get by a thread (workQueue) and anaylzed with workEvent
#
# workEVENT and executePinChange have options to
# supporess bounces and to cover for missing signals in the steps.
#  ignorePinValue =
#   0= no management
#   1 = if event pin not changed: set event pin true if TRUE would be next expected signal (not if threads & queue are used)
#   2 = if event pin not changed: flip PIN value is same as last value (not if threads & queue are used, as working on queue and receiving are out of sync)
#   3 = if event pin not changed: add flipped pin event to sequence
##

import	sys, os, subprocess, copy
import	time,datetime
import	json
import	RPi.GPIO as GPIO  

sys.path.append(os.getcwd())
import	piBeaconUtils	as U
import	piBeaconGlobals as G
G.program = "INPUTRotarySwitchIncremental"


#################################
def readParams():
		global sensors
		global oldRaw, lastRead, INPUTS
		global counts, countSignals
		global useWhichGPIO, useThreads


		inp,inpRaw,lastRead2 = U.doRead(lastTimeStamp=lastRead)
		if inp == "": return
		if lastRead2 == lastRead: return
		lastRead   = lastRead2
		if inpRaw == oldRaw: return
		oldRaw	   = inpRaw

		oldSensors  = sensors

		U.getGlobalParams(inp)
		if "sensors"			in inp : sensors =				(inp["sensors"])
		if "debugRPI"			in inp:	 G.debug=			  int(inp["debugRPI"]["debugRPISENSOR"])
		if oldSensors == sensors: return 

		restart = False
			
		if G.program  not in sensors:
			print G.program + "  not in sensors" 
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

				if "useWhichGPIO" in sens:
						xxx 							 = sens["useWhichGPIO"].split("-")
						if  useWhichGPIO != xxx[0]:
							new = True
						if  useThreads != (xxx[1] == "threads"):
							new = True
						useWhichGPIO = xxx[0]
						useThreads	 = xxx[1] == "threads"
						
					
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
def setupGPIOsystem():

	U.logger.log(30, "starting setup GPIOsystem")

	ret=subprocess.Popen("modprobe w1-gpio" ,shell=True,stdout=subprocess.PIPE,stderr=subprocess.PIPE).communicate()
	if len(ret[1]) > 0:
		U.logger.log(30, "starting GPIO: return error "+ ret[0]+"\n"+ret[1])
		return False

	ret=subprocess.Popen("modprobe w1_therm",shell=True,stdout=subprocess.PIPE,stderr=subprocess.PIPE).communicate()
	if len(ret[1]) > 0:
		U.logger.log(30, "starting GPIO: return error "+ ret[0]+"\n"+ret[1])
		return False

	return True




#################################
def saveCounts():
	global counts
	f= open(G.homeDir+G.program+".counts", "w")
	f.write(json.dumps(counts))	
	f.close()

#################################
def readCounts():
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

	if debug > 2: print "pigEVENT:", pin, level, " A:",str(stateA)[0], " B:",str(stateB)[0],  " since last %.3f"%(tick - lastTick)/1000., "msecs"
	lastTick = tick
	threadDict["queue"].put(( pin, stateA, stateB, tick/1000. ))
	return 

#################################
def gpioEVENTthread(pin):
	global lastTick
	global INPUTS, pinsToDevid
	global threadDict
	global debug
	devIDUsed = pinsToDevid[pin]
	IP = INPUTS[devIDUsed]
	pinA= IP["pinA"]
	pinB= IP["pinB"]
	stateA = (GPIO.input(pinA) == 0)
	stateB = (GPIO.input(pinB) == 0)
	if IP["inverse"]:
		stateA = not stateA
		stateB = not stateB
	tick = time.time()*1000

	level = "D"
	if pin == pinB and stateB: level = "U" 
	if pin == pinA and stateA: level = "U"

	if debug > 2: print "rpiEVENT:", pin, level, " A:",str(stateA)[0], " B:",str(stateB)[0],  " since last %.3f"%(tick - lastTick), "msecs"
	lastTick = tick
	threadDict["queue"].put(( pin, stateA, stateB, tick ))
	return 

#################################
def workQueue():
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
	except	Exception, e:
		U.logger.log(30, u"in Line {} has error={}".format(sys.exc_traceback.tb_lineno, e))
	return


#################################
def startGPIO(devId):
	global INPUTS, pinsToDevid
	global threadDict, useThreads
	global useWhichGPIO, PIGPIO, pigpio, lastTick
	global debug

	try:
		pinsToDevid[INPUTS[devId]["pinA"]] = devId
		pinsToDevid[INPUTS[devId]["pinB"]] = devId
		U.logger.log(30, "pinsToDevid "+unicode(pinsToDevid))

		if useWhichGPIO == "pig":
			if PIGPIO == "":
				import pigpio
				import threading 
				import Queue
				if not U.pgmStillRunning("pigpiod"): 	
					U.logger.log(30, "starting pigpiod")
					os.system("sudo pigpiod &")
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

		elif useWhichGPIO == "rpi":
			U.logger.log(30, "GPIO  setting up gpio "+str(devId)+"  "+ str(INPUTS[devId]))
			GPIO.setup( INPUTS[devId]["pinA"], GPIO.IN, pull_up_down=GPIO.PUD_UP)
			GPIO.setup( INPUTS[devId]["pinB"], GPIO.IN, pull_up_down=GPIO.PUD_UP)
			if useThreads: 
				if 	"queue" not in threadDict:
					import threading 
					import Queue
					threadDict["queue"] = Queue.Queue()
					threadDict["thread"] = threading.Thread(target=workQueue, name="workQueue" )
					threadDict["thread"].start()
				GPIO.add_event_detect( INPUTS[devId]["pinA"], GPIO.BOTH, callback=gpioEVENTthread ) 		
				GPIO.add_event_detect( INPUTS[devId]["pinB"], GPIO.BOTH, callback=gpioEVENTthread ) 
			else:
				GPIO.add_event_detect( INPUTS[devId]["pinA"], GPIO.BOTH, callback=workEvent ) 		
				GPIO.add_event_detect( INPUTS[devId]["pinB"], GPIO.BOTH, callback=workEvent ) 

		else:
			print " error useWhichGPIO not defined"
			exit()
		

		return
	except	Exception, e:
		U.logger.log(30, u"in Line {} has error={}".format(sys.exc_traceback.tb_lineno, e))
		U.logger.log(30,"start "+ G.program+ "  "+ unicode(sensors))
	return


	   
#################################
def workEvent(pin, stateA=-1, stateB =-1, tt=-1):
 	global INPUTS, pinsToDevid, newData
	global counts
	global countSignals
	global debug
	try:
			devIDUsed = pinsToDevid[pin]
			IP = INPUTS[devIDUsed]
			pinA= IP["pinA"]
			pinB= IP["pinB"]

			if stateA==-1 and stateB ==-1:
				stateA = (GPIO.input(pinA) == 0)
				stateB = (GPIO.input(pinB) == 0)
	
			if IP["inverse"]:
				stateA = not stateA
				stateB = not stateB

			if tt == -1:  
				tt = time.time()

			if debug > 1: print str(devIDUsed)[-3:-1],"+into event %7.4f"%(tt - IP["lastChangeTime"])," %7.4f"%(tt - IP["lastEvent"]),"; pin", pin,"; cycle", str(IP["newCycle"])[0], ";  dir", str(IP["direction"])[0], ";  A",str(stateA)[0], ";  B",str(stateB)[0], ";  AL",str(IP["pinALastValue"])[0], ";  BL",str(IP["pinBLastValue"])[0], ";  CS",countSignals[devIDUsed], ";  C",counts[devIDUsed]


			if  IP["ignorePinValue"] == 1 and not useThreads: 
				if pin == pinB :
					if stateB == IP["pinBLastValue"]:
						if  IP["direction"] == "+":
							if not stateB: 
								if debug > 0: print "fix B1;  A:", str(stateA)[0],  "; B:",str(stateB)[0], "; dir", str(IP["direction"])[0]
								stateB = True
				else:
					if stateA == IP["pinALastValue"]:
						if  IP["direction"] == "-":
							if not stateA  == 1: 
								if debug > 0: print "fix A1;  A:", str(stateA)[0],  "; B:",str(stateB)[0], "; dir", str(IP["direction"])[0]
								stateA = True
							
			elif  IP["ignorePinValue"] == 2 and not useThreads: 
				if pin == pinB :
					if stateB == IP["pinBLastValue"]:
						if debug > 0: print "fix B2;  A:", str(stateA)[0],  "; B:",str(stateB)[0], "; dir", str(IP["direction"])[0]
						stateB = not stateB
				else:
					if stateA == IP["pinALastValue"]:
						if debug > 0: print "fix A2;  A:", str(stateA)[0],  "; B:",str(stateB)[0], "; dir", str(IP["direction"])[0]
						stateA = not stateA

							
			elif  IP["ignorePinValue"] == 3: 
				if pin == pinB :
					if stateB == IP["pinBLastValue"]:
						if debug > 0: print "fix 3 B; A:", str(stateA)[0],  "; B:",str(stateB)[0], "; dir",str(IP["direction"])[0]
						executePinChange(devIDUsed, pin, stateA, not stateB, tt)
				else:
					if stateA == IP["pinALastValue"]:
						if debug > 0: print "fix 3 A; A:", str(stateA)[0],  "; B:",str(stateB)[0], "; dir", str(IP["direction"])[0]
						executePinChange(devIDUsed, pin, not stateA, stateB, tt)

			executePinChange(devIDUsed, pin, stateA, stateB, tt)

	except	Exception, e:
			U.logger.log(30, u"in Line {} has error={}".format(sys.exc_traceback.tb_lineno, e))

			return 

#################################
def executePinChange(devIDUsed, pin, stateA, stateB, tt):
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
				if debug > 0: print " no change", pin, stateA, stateB
				return 

			# save last values..
			if (not stateA) and (not stateB):
				IP["newCycle"] = True

			if (tt - IP["lastChangeTime"]) > IP["resetTimeCheck"] and not IP["newCycle"] and countSignals[devIDUsed]	> 4: 
				if debug >0: print " reset newCycle lastChangeTime"
				IP["newCycle"] = True
			if (tt - IP["lastEvent"])      > IP["resetTimeCheck"] and not IP["newCycle"] and countSignals[devIDUsed]	> 4: 
				if debug >0: print " reset newCycle lastEvent"
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
							print "reject A"
					else:
						if ( stateB ==  IP["pinBLastValue"] or not  IP["distinctTransition"] ) or ( not IP["pinALastValue"] and  not IP["pinBLastValue"] ):
							counts[devIDUsed] 		-= 1
							IP["direction"]      	= False
							IP["newCycle"]       	= False
							IP["lastEvent"]      	= tt
							countSignals[devIDUsed]	= 0
						else:
							print "reject B"
					newData = True

			if 	countSignals[devIDUsed] > 4 and IP["incrementIfGT4Signals"] and (tt- IP["lastEvent"]) > IP["resetTimeCheck"]:
				if IP["direction"]: counts[devIDUsed]  +=1
				else:				counts[devIDUsed]  -=1
				IP["newCycle"]       = False
				IP["lastEvent"]      = tt
				countSignals[devIDUsed]  =0
				if debug > 0: print "fixing count due to countSignal > 4"


			# debug		
			if debug > 1:  print str(devIDUsed)[-3:-1],"=exit event %7.4f"%(tt - IP["lastChangeTime"])," %7.4f"%(tt - IP["lastEvent"]),"; pin", pin,"; cycle", str(IP["newCycle"])[0], ";  dir", str(IP["direction"])[0], ";  A",str(stateA)[0], ";  B",str(stateB)[0], ";  AL",str(IP["pinALastValue"])[0], ";  BL",str(IP["pinBLastValue"])[0],";  CS",countSignals[devIDUsed], ";  C",counts[devIDUsed]

			if stateA !=  IP["pinALastValue"] or stateB !=  IP["pinBLastValue"]:
				IP["lastChangeTime"] = tt#


			IP["pinALastValue"] = stateA
			IP["pinBLastValue"] = stateB
	except	Exception, e:
			U.logger.log(30, u"in Line {} has error={}".format(sys.exc_traceback.tb_lineno, e))
	return 




#################################



#################################
def checkReset():
	if not os.path.isfile(G.homeDir+"temp/"+ G.program+".reset"): return False
	try:    os.remove(G.homeDir+"temp/" + G.program+".reset")
	except: pass
	return True


#################################
def stopProgram(action=""):
	global threadDict, stopThread

	if "tread" in threadDict:
		stopThread = True
		threadDict["thread"].join()
	if action == "onlyThread":
		return 
	sys.exit(0)



#################################
#################################
######      MAIN     ############
#################################
#################################
global sensors
global sensors
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



#### threadding does not work with edge detect, can have only ONE edge detect !!!!
threadDict			= {"stopThread":False}
lastTick 			= 0.
PIGPIO				= ""	
useWhichGPIO		= "rpi"
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

GPIO.setmode(GPIO.BCM)
U.setLogging()

myPID		= str(os.getpid())
U.killOldPgm(myPID,G.program+".py")# old old instances of myself if they are still running

#  Possible answers are 0 = Compute Module, 1 = Rev 1, 2 = Rev 2, 3 = Model B+/A+
piVersion = GPIO.RPI_REVISION

sensor			  = G.program

U.logger.log(30, "starting "+G.program+" program")

# check if everything is installed
for i in range(100):
	if not setupGPIOsystem(): 
		time.sleep(10)
		if i%50==0: U.logger.log(30,G.program+"===>  GPIO sensor libs not installed, need to wait until done")
	else:
		break	 


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
			lastMsg=tt
			lastData=copy.copy(data0)
			data["sensors"][sensor] = data0
			#print data, counts
			U.sendURL(data)
		quick = U.checkNowFile(G.program)
		if loopCount%50==0:
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
				counts[devId]=0
				saveCounts()

		newData = False
	except	Exception, e:
		U.logger.log(30, u"in Line {} has error={}".format(sys.exc_traceback.tb_lineno, e))
		time.sleep(5.)

stopProgram()