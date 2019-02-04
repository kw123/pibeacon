#!/usr/bin/env python
# -*- coding: utf-8 -*-
# by Karl Wachs
# Feb 3 2019
# version 0.95
##
##	 read  grey encoded n pin rotaty switch, send integer value to indogo every 90 secs or if chnaged
#

##

import	sys, os, subprocess, copy
import	time,datetime
import	json
import	RPi.GPIO as GPIO  
import threading


sys.path.append(os.getcwd())
import	piBeaconUtils	as U
import	piBeaconGlobals as G
G.program = "INPUTRotataryPulseSwitch"


def readParams():
		global sensors
		global oldRaw, lastRead, INPUTS


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
			exit()

		oldINPUTS  = copy.deepcopy(INPUTS)
		restart    = False
		if sensor in sensors:
			for devId in sensors[sensor]:
				new = False
				sens = sensors[sensor][devId]
				if devId not in INPUTS: 
					INPUTS[devId]  = {"pinALastValue":9999999, "lastChangeTime":0, "count":0, "pinBLastValue":9999999, "bounceTime":0.002, "pinA":21, "pinB":20}
					INPUTS[devId]["LockRotary"] = threading.Lock()		# create lock for rotary switch

				if INPUTS[devId]["bounceTime"] !=  int(sens["bounceTime"]):
					new = True
					INPUTS[devId]["bounceTime"]		= int(sens["bounceTime"])

				if INPUTS[devId]["pinA"] !=  int(sens["INPUT_0"]):
					INPUTS[devId]["pinA"] = int(sens["INPUT_0"])
					new = True
				if INPUTS[devId]["pinB"] !=  int(sens["INPUT_1"]):
					INPUTS[devId]["pinB"] = int(sens["INPUT_1"])
					new = True
		
				if oldINPUTS != {} and new:
					restart = True
					break
				elif oldINPUTS == {} or new:
					startGPIO(devId)
		if restart:
			U.restartMyself(reason="new parameters")
		return 


def setupSensors():

	U.toLog(-1, "starting setup sensors",doPrint=True)

	ret=subprocess.Popen("modprobe w1-gpio" ,shell=True,stdout=subprocess.PIPE,stderr=subprocess.PIPE).communicate()
	if len(ret[1]) > 0:
		U.toLog(-1, "starting GPIO: return error "+ ret[0]+"\n"+ret[1],doPrint=True)
		return False

	ret=subprocess.Popen("modprobe w1_therm",shell=True,stdout=subprocess.PIPE,stderr=subprocess.PIPE).communicate()
	if len(ret[1]) > 0:
		U.toLog(-1, "starting GPIO: return error "+ ret[0]+"\n"+ret[1],doPrint=True)
		return False

	return True


	   
def gpioEvent(pin):
 	global INPUTS, pinsToDevid, newData
	value = 0
	#print "into event", pin
	try:
			devIDUsed = pinsToDevid[pin]
			IP = INPUTS[devIDUsed]
			pinA= IP["pinA"]
			pinB= IP["pinB"]
			bounceTime = IP["bounceTime"]
			stateA = GPIO.input(pinA) 
			stateB = GPIO.input(pinB) 
				
			if stateA ==  IP["pinALastValue"] and stateB ==  IP["pinBLastValue"]:
				#print " no change", stateA, stateB
				return 

			if IP["pinALastValue"] and IP["pinBLastValue"]:
				try: INPUTS[devId]["LockRotary"].acquire()	
				except:
					time.sleep(0.01)
					try: INPUTS[devId]["LockRotary"].acquire()	
					except: return 
				if pin == pinB:
					IP["count"] +=1
				else:
					IP["count"] -=1
				INPUTS[devId]["LockRotary"].release()	
				newData = True

			if stateA !=  IP["pinALastValue"] or stateB !=  IP["pinBLastValue"]:
				#print "event:  %.3f"%(time.time()- IP["lastChangeTime"]), stateA, stateB, IP["pinALastValue"], IP["pinBLastValue"], IP["count"]
				IP["lastChangeTime"] = time.time()#

			IP["pinALastValue"] = stateA
			IP["pinBLastValue"] = stateB
	except	Exception, e:
			U.toLog(-1, u"in Line '%s' has error='%s'" % (sys.exc_traceback.tb_lineno, e), doPrint=True)
	return 



def startGPIO(devId):
	global INPUTS, pinsToDevid
	print "setting up gpio", INPUTS[devId]
	try:

		GPIO.setup( INPUTS[devId]["pinA"], GPIO.IN, pull_up_down=GPIO.PUD_UP)
		GPIO.setup( INPUTS[devId]["pinB"], GPIO.IN, pull_up_down=GPIO.PUD_UP)
		if INPUTS[devId]["bounceTime"] > 0:
			GPIO.add_event_detect( INPUTS[devId]["pinA"], GPIO.RISING, callback=gpioEvent , bouncetime=INPUTS[devId]["bounceTime"]) 		
			GPIO.add_event_detect( INPUTS[devId]["pinB"], GPIO.RISING, callback=gpioEvent , bouncetime=INPUTS[devId]["bounceTime"]) 
		else:
			GPIO.add_event_detect( INPUTS[devId]["pinA"], GPIO.RISING, callback=gpioEvent ) 		
			GPIO.add_event_detect( INPUTS[devId]["pinB"], GPIO.RISING, callback=gpioEvent ) 
		
		pinsToDevid[INPUTS[devId]["pinA"]] = devId
		pinsToDevid[INPUTS[devId]["pinB"]] = devId

		return
	except	Exception, e:
		U.toLog(-1, u"in Line '%s' has error='%s'" % (sys.exc_traceback.tb_lineno, e), doPrint=True)
		U.toLog(-1,"start "+ G.program+ "  "+ unicode(sensors), doPrint=True)
	return




global sensors
global sensors
global oldRaw, lastRead
global INPUTS
global newData
oldRaw				= ""
lastRead			= 0
INPUTS				= {}
sensors				= {}
pinsToDevid			= {}
newData				= False

###################### constants #################

GPIO.setmode(GPIO.BCM)

myPID		= str(os.getpid())
U.killOldPgm(myPID,G.program+".py")# old old instances of myself if they are still running

#  Possible answers are 0 = Compute Module, 1 = Rev 1, 2 = Rev 2, 3 = Model B+/A+
piVersion = GPIO.RPI_REVISION

sensor			  = G.program

U.toLog(-1, "starting "+G.program+" program",doPrint=True)


LockRotary = threading.Lock()		# create lock for rotary switch


readParams()

# check if everything is installed
for i in range(100):
	if not setupSensors(): 
		time.sleep(10)
		if i%50==0: U.toLog(-1,"sensor libs not installed, need to wait until done",doPrint=True)
	else:
		break	 
		

shortWait			= 0.3	 
lastEverything		= time.time()-10000. # -1000 do the whole thing initially
G.lastAliveSend		= time.time()

#print "shortWait",shortWait	 

if U.getIPNumber() > 0:
	U.toLog(-1," sensors no ip number  exiting ", doPrint =True)
	time.sleep(10)
	exit()


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
			data0[devId] = {"INPUT":INPUTS[devId]["count"]}

		if	data0 != lastData or tt - lastMsg > 100:
			lastMsg=tt
			lastData=copy.copy(data0)
			data["sensors"][sensor] = data0
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
		newData = False
	except	Exception, e:
		U.toLog(-1, u"in Line '%s' has error='%s'" % (sys.exc_traceback.tb_lineno, e),doPrint=True)
		time.sleep(5.)


sys.exit(0)
