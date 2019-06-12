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
G.program = "INPUTpulse"
GPIO.setmode(GPIO.BCM)


def checkReset():
	global	INPUTcount
	INPUTcount2 = U.checkresetCount(INPUTcount)
	if INPUTcount2 != INPUTcount:
		INPUTcount = copy.copy(INPUTcount2)
		return True
	return False

def readParams():
	global sensor, sensors
	global INPgpioType,INPUTcount,INPUTlastvalue
	global GPIOdict, restart
	global oldRaw, lastRead
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
		#print "sens:", sens
		found ={str(ii):{"RISING":0,"FALLING":0,"BOTH":0 } for ii in range(100)}
		for devId in sens:
			sss= sens[devId]
			if "gpio"							not in sss: continue
			if "deadTime"						not in sss: continue
			if "risingOrFalling"				not in sss: continue
			if "minSendDelta"					not in sss: continue
			if "bounceTime"						not in sss: continue
			if "deadTime"						not in sss: continue
			if "deadTimeBurst"					not in sss: continue
			if "inpType"						not in sss: continue
			if "timeWindowForBursts"			not in sss: continue
			if "timeWindowForLongEvents"		not in sss: continue
			if "timeWindowForContinuousEvents"	not in sss: continue
			if "minBurstsinTimeWindowToTrigger" not in sss: continue

			gpio						= sss["gpio"]
			risingOrFalling				= sss["risingOrFalling"]
			inpType						= sss["inpType"]

			try:	bounceTime			= int(sss["bounceTime"])
			except: bounceTime			= 10

			try:	timeWindowForLongEvents = float(sss["timeWindowForLongEvents"])
			except: timeWindowForLongEvents = -1

			try:	minSendDelta		= int(sss["minSendDelta"])
			except: minSendDelta		= 1

			try:	deadTime			= float(sss["deadTime"])
			except: deadTime			= 1

			try:	deadTimeBurst		= float(sss["deadTimeBurst"])
			except: deadTimeBurst		= 1

			try:	timeWindowForBursts = int(sss["timeWindowForBursts"])
			except: timeWindowForBursts = -1

			try:	minBurstsinTimeWindowToTrigger = int(sss["minBurstsinTimeWindowToTrigger"])
			except: minBurstsinTimeWindowToTrigger = -1

			try:	timeWindowForLongEvents = float(sss["timeWindowForLongEvents"])
			except: timeWindowForLongEvents = -1

			try:	pulseEveryXXsecsLongEvents = float(sss["pulseEveryXXsecsLongEvents"])
			except: pulseEveryXXsecsLongEvents = -1

			try:	timeWindowForContinuousEvents = float(sss["timeWindowForContinuousEvents"])
			except: timeWindowForContinuousEvents = -1


			found[gpio][risingOrFalling]		 = 1
			if gpio in GPIOdict and "risingOrFalling" in GPIOdict[gpio]: 
					if GPIOdict[gpio]["bounceTime"] !=	bounceTime: 
						restart=True
						return
					if GPIOdict[gpio]["risingOrFalling"] !=	 risingOrFalling: 
						restart=True
						return
					GPIOdict[gpio]["deadTime"]								= deadTime
					GPIOdict[gpio]["deadTimeBurst"]							= deadTimeBurst
					GPIOdict[gpio]["devId"]									= devId
					GPIOdict[gpio]["minSendDelta"]							= minSendDelta
					GPIOdict[gpio]["minBurstsinTimeWindowToTrigger"]		= minBurstsinTimeWindowToTrigger
					GPIOdict[gpio]["timeWindowForBursts"]					= timeWindowForBursts
					GPIOdict[gpio]["timeWindowForLongEvents"]				= timeWindowForLongEvents
					GPIOdict[gpio]["timeWindowForContinuousEvents"]			= timeWindowForContinuousEvents
					GPIOdict[gpio]["pulseEveryXXsecsLongEvents"]			= pulseEveryXXsecsLongEvents
					GPIOdict[gpio]["lastsendBurst"]							= 0
					GPIOdict[gpio]["lastsendCount"]							= 0
					GPIOdict[gpio]["lastsendlongEvent"]						= 0
					GPIOdict[gpio]["lastsendContinuousEvent"]				= 0
					if inpType != GPIOdict[gpio]["inpType"]:
						if	 inpType == "open":
							GPIO.setup(int(gpio), GPIO.IN)
						elif inpType == "high":
							GPIO.setup(int(gpio), GPIO.IN, pull_up_down=GPIO.PUD_UP)
						elif inpType == "low":
							GPIO.setup(int(gpio), GPIO.IN, pull_up_down=GPIO.PUD_DOWN)
					GPIOdict[gpio]["inpType"]	 = inpType
					continue 
			elif gpio in GPIOdict and "risingOrFalling" not in GPIOdict[gpio]: 
				print "setting up ",risingOrFalling
				GPIOdict[gpio]={
								  "devId":							devId,
								  "inpType":						inpType,
								  "minSendDelta":					minSendDelta,
								  "bounceTime":						bounceTime,
								  "deadTime":						deadTime,
								  "deadTimeBurst":					deadTimeBurst,
								  "risingOrFalling":				risingOrFalling,
								  "timeWindowForBursts":			timeWindowForBursts,
								  "timeWindowForLongEvents":		timeWindowForLongEvents,
								  "pulseEveryXXsecsLongEvents":		pulseEveryXXsecsLongEvents,
								  "timeWindowForContinuousEvents":	timeWindowForContinuousEvents,
								  "minBurstsinTimeWindowToTrigger": minBurstsinTimeWindowToTrigger,
								  "lastSignal":						0,
								  "lastsendCount":					0,
								  "lastsendBurst":					0,
								  "lastsendlongEvent":				0,
								  "lastsendContinuousEvent":		0,
								  "count":							0 }
				print  GPIOdict				  
				if	 inpType == "open":
					GPIO.setup(int(gpio), GPIO.IN)
				elif inpType == "high":
					GPIO.setup(int(gpio), GPIO.IN, pull_up_down=GPIO.PUD_UP)
				elif inpType == "low":
					GPIO.setup(int(gpio), GPIO.IN, pull_up_down=GPIO.PUD_DOWN)
				if	risingOrFalling == "RISING": 
					GPIO.add_event_detect(int(gpio), GPIO.RISING,	callback=RISING,  bouncetime=bounceTime)  
				elif  risingOrFalling == "FALLING": 
					GPIO.add_event_detect(int(gpio), GPIO.FALLING,	callback=FALLING, bouncetime=bounceTime)  
				else:
					GPIO.add_event_detect(int(gpio), GPIO.BOTH,		callback=BOTH, bouncetime=bounceTime)  
				GPIOdict[gpio]["inpType"]	 = inpType

			elif gpio not in GPIOdict: # change: reboot 
				GPIOdict[gpio]={
								  "devId":							devId,
								  "inpType":						inpType,
								  "minSendDelta":					minSendDelta,
								  "bounceTime":						bounceTime,
								  "deadTime":						deadTime,
								  "deadTimeBurst":					deadTimeBurst,
								  "risingOrFalling":				risingOrFalling,
								  "timeWindowForBursts":			timeWindowForBursts,
								  "timeWindowForLongEvents":		timeWindowForLongEvents,
								  "pulseEveryXXsecsLongEvents":		pulseEveryXXsecsLongEvents,
								  "timeWindowForContinuousEvents":	timeWindowForContinuousEvents,
								  "minBurstsinTimeWindowToTrigger": minBurstsinTimeWindowToTrigger,
								  "lastSignal":						0,
								  "lastsendCount":					0,
								  "lastsendBurst":					0,
								  "lastsendlongEvent":				0,
								  "lastsendContinuousEvent":		0,
								  "count":							0 }
				print  ""				
				if	 inpType == "open":
					GPIO.setup(int(gpio), GPIO.IN)
				elif inpType == "high":
					GPIO.setup(int(gpio), GPIO.IN, pull_up_down=GPIO.PUD_UP)
				elif inpType == "low":
					GPIO.setup(int(gpio), GPIO.IN, pull_up_down=GPIO.PUD_DOWN)
				if	risingOrFalling == "RISING": 
					GPIO.add_event_detect(int(gpio), GPIO.RISING,	callback=RISING,  bouncetime=bounceTime)  
				elif  risingOrFalling == "FALLING": 
					GPIO.add_event_detect(int(gpio), GPIO.FALLING,	callback=FALLING, bouncetime=bounceTime)  
				else:
					GPIO.add_event_detect(int(gpio), GPIO.BOTH,		callback=BOTH, bouncetime=bounceTime)  
				GPIOdict[gpio]["inpType"]	 = inpType
				
		oneFound = False
		restart=False
		delGPIO={}
		for gpio in GPIOdict:
			for risingOrFalling in["FALLING","RISING","BOTH"]:
				if found[gpio][risingOrFalling]==1: 
					oneFound = True
					continue
				if risingOrFalling in GPIOdict:
					restart=True
					continue
			if GPIOdict[gpio] == {}: delGPIO[gpio]=1
		for gpio in delGPIO:
			if gpio in GPIOdict: del GPIOdict[gpio]
		
		if not oneFound:
			U.toLog(0,	"no	 gpios setup, exiting",doPrint=True)
			exit()
		if	restart:
			U.toLog(0,	"gpios edge channel deleted, need to restart",doPrint=True)
			U.restartMyself(param="", reason=" new definitions",doPrint=True)
			
		U.toLog(0,	"GPIOdict: " +unicode(GPIOdict),doPrint=True)
	except	Exception, e:
		U.toLog(-1, u"in Line {} has error={}".format(sys.exc_traceback.tb_lineno, e),doPrint=True)
				

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
 
 
def FALLING(gpio):	
	fillGPIOdict(gpio,"FALLING")
	 
def RISING(gpio):
	fillGPIOdict(gpio,"RISING")
	
def BOTH(gpio):
	fillGPIOdict(gpio,"BOTH")

def fillGPIOdict(gpio,risingOrFalling):
	global INPUTcount, GPIOdict, sensor, BURSTS, lastGPIO, longEVENT, contEVENT, sensors
	
	ggg = GPIOdict[str(gpio)]
	tt= time.time()
	countChanged = False
	if tt- ggg["lastSignal"] > ggg["deadTime"]:	 
		ggg["count"]+=1
		INPUTcount[int(gpio)]+=1
		ggg["lastSignal"] = tt
		U.toLog(2, risingOrFalling+" edge on %d2"%gpio+" gpio,	count: %d"% ggg["count"]+", timest: %6.1f"%tt+", lastSendC: %6.1f"%ggg["lastsendCount"]+", minSendDelta: %d"%ggg["minSendDelta"])
		countChanged = True

	###############	 this EVENTtype requires a minBurstsinTimeWindowToTrigger  in timeWindowForBursts to trigger ###
	burst=0
	bbb =  BURSTS[gpio]
	if ggg["minBurstsinTimeWindowToTrigger"] > 0:
		ll	=len(bbb)
		for kk in range(ll):
			ii = ll - kk -1
			if tt-bbb[ii][0] > ggg["timeWindowForBursts"]: 
				del bbb[ii]
		U.toLog(2, "BURST: "+str(ll)+"	"+str(tt)+"	 "+ str(bbb)+"	"+str(ggg["timeWindowForBursts"] ))
		ll	=len(bbb)
		if ll == 0	or	tt - bbb[-1][0]	 < ggg["deadTimeBurst"]: 
			bbb.append([tt,1])
			U.toLog(2, "BURST:	in window "+str(ggg["timeWindowForBursts"]))
			ll	+=1
			delupto = -1
			for kk in range(ll):
					ii = ll - kk -1
					bbb[ii][1]+=1
					if bbb[ii][1] >= ggg["minBurstsinTimeWindowToTrigger"]:
						U.toLog(2, "BURST triggered "+ risingOrFalling+" edge .. on %d2"%gpio+" gpio,  burst# "+unicode(ii)+";	#signals="+ unicode(bbb[ii][1])+ "--  in "+ unicode(ggg["timeWindowForBursts"]) +"secs time window")
						burst	= tt
						delupto = ii-1
						break
			if delupto >0:
				for kk in range(delupto):
					del bbb[delupto - kk -1]


	###############	 this EVENTtype requires a pulse every second for timeWindowForLongEvents seconds  ###
	lEVENTtt=0
	bbb =  longEVENT[gpio]
	if ggg["timeWindowForLongEvents"] > 0:
		U.toLog(2, "longEVENT(1): "+str(ll)+"  "+str(tt)+";	  timeWindowForLongEvents: "+str(ggg["timeWindowForLongEvents"])+"	secs" )
		ll	=len(bbb)
		if True: 
			bbb.append([tt,tt+ggg["pulseEveryXXsecsLongEvents"]])
			U.toLog(2, "contEVENT(2):  in window ;	 N events="+ unicode(ll) )
			ll	   += 1
			delupto = -1
			for kk in range(ll):
					ii = ll - kk -1
					delta1 = tt - bbb[ii][1]
					delta0 = tt - bbb[ii][0]
					if delta1 > 0. and delupto == -1: 
						delupto = ii-1
						U.toLog(2, "longEVENT(3) rejected  ")
						continue
					if delta0 >= ggg["timeWindowForLongEvents"]:
						U.toLog(2, "longEVENT(4) triggered ")
						lEVENTtt   = tt
						delupto	   = ii-1
					bbb[ii][1]	= tt+ggg["pulseEveryXXsecsLongEvents"]
			if delupto >0:
				for kk in range(delupto):
					del bbb[delupto - kk -1]

	###############	 this EVENTtype requires a pulse to start the CONT event, will extend event if new pulse arrives before timeWindowForContinuousEvents is over  ###
	cEVENTtt=0
	if ggg["timeWindowForContinuousEvents"] > 0:
		if contEVENT[gpio] == -1 or contEVENT[gpio] == 0:  # new event 
			cEVENTtt = tt
		elif  tt - contEVENT[gpio]	> ggg["timeWindowForContinuousEvents"]:
			# was expired send off then send ON 
			data = {"sensors":{sensor:{ggg["devId"]:{}}}}
			data["sensors"][sensor][ggg["devId"]]["continuous"]		 = -1
			U.sendURL(data,wait=False)

			time.sleep(0.01)
			cEVENTtt = tt
		#  or just conti nue old c event = just update contEVENT not need to send data 
		contEVENT[gpio] =  tt
		U.toLog(2, "cEVENT(1): "+str(tt)+"; cEVENTtt="+ unicode(cEVENTtt)  )

	
	data = {"sensors":{sensor:{ggg["devId"]:{}}}}

	if (tt - ggg["lastsendBurst"] > ggg["minSendDelta"]) and  burst > 0 :  
			data["sensors"][sensor][ggg["devId"]]["burst"]		= int(burst)
			data["sensors"][sensor][ggg["devId"]]["count"]		= ggg["count"]
			ggg["lastsendBurst"] = tt
			ggg["lastsendCount"] = tt
			if burst >0:
				lastGPIO= U.doActions(data["sensors"],lastGPIO, sensors, sensor,theAction="1")

	if (tt - ggg["lastsendContinuousEvent"] > ggg["minSendDelta"]) and	cEVENTtt > 0 :	
			data["sensors"][sensor][ggg["devId"]]["continuous"]		 = int(cEVENTtt)
			data["sensors"][sensor][ggg["devId"]]["count"]			 = ggg["count"]
			ggg["lastsendContinuousEvent"] = tt
			ggg["lastsendCount"] = tt
			if cEVENTtt >0:
				lastGPIO= U.doActions(data["sensors"],lastGPIO, sensors, sensor,theAction="3")

	if (tt - ggg["lastsendlongEvent"] > ggg["minSendDelta"]) and  lEVENTtt > 0 :  
			data["sensors"][sensor][ggg["devId"]]["longEvent"]	= int(lEVENTtt)
			data["sensors"][sensor][ggg["devId"]]["count"]		= ggg["count"]
			ggg["lastsendlongEvent"] = tt
			ggg["lastsendCount"] = tt
			if lEVENTtt >0:
				lastGPIO= U.doActions(data["sensors"],lastGPIO, sensors, sensor,theAction="2")

	if (tt - ggg["lastsendCount"] > ggg["minSendDelta"]) and countChanged:	
			data ["sensors"][sensor][ggg["devId"]]["count"]		= ggg["count"]
			ggg["lastsendCount"] = tt

	if data["sensors"][sensor][ggg["devId"]] !={}:
			U.sendURL(data,wait=False)
			U.writeINPUTcount(INPUTcount)

def resetContinuousEvents():
	global GPIOdict, contEVENT, sensor
	for gpio in GPIOdict:
		ggg = GPIOdict[gpio]
		if ggg["timeWindowForContinuousEvents"] > 0:
			igpio= int(gpio)
			if	contEVENT[igpio] > 0:
				if	tt - contEVENT[igpio]  > ggg["timeWindowForContinuousEvents"]:
					contEVENT[igpio] =	-1
					# was expired send off then send ON 
					data = {"sensors":{sensor:{ggg["devId"]:{}}}}
					data["sensors"][sensor][ggg["devId"]]["continuous"] = -1
					U.sendURL(data,wait=False)

  
global sensors, INPUTcount
global oldParams
global GPIOdict, restart, BURSTS, lastGPIO, longEVENT, contEVENT
global oldRaw,	lastRead
oldRaw					= ""
lastRead				= 0

###################### constants #################

INPUTlastvalue	  = ["-1" for i in range(100)]
INPUTcount		  = [0	  for i in range(100)]
BURSTS			  = [[]	  for i in range(50)]
longEVENT		  = [[]	  for i in range(50)]
contEVENT		  = [0	  for i in range(50)]
lastGPIO		  = [""	  for ii in range(50)]
#i2c pins:		  = gpio14 &15
# 1 wire		  = gpio4
oldParams		  = ""
GPIOdict		  = {}
restart			  = False
countReset		  = False
if not setupSensors():
	print " gpio are not setup"
	exit()


myPID		= str(os.getpid())
U.killOldPgm(myPID,G.program+".py")# old old instances of myself if they are still running


sensor			  = G.program
sensors			  ={}
loopCount		  = 0

U.toLog(-1, "starting "+G.program+" program",doPrint=True)

readParams()
INPUTcount = U.readINPUTcount()



# check if everything is installed
for i in range(100):
	if not setupSensors(): 
		time.sleep(10)
		if i%50==0: U.toLog(-1,"sensor libs not installed, need to wait until done",doPrint=True)
	else:
		break	 
		

G.lastAliveSend		= time.time()
# set alive file at startup


if U.getIPNumber() > 0:
	U.toLog(-1," sensors no ip number  exiting ", doPrint =True)
	time.sleep(10)
	exit()

quick  = 0

G.tStart = time.time() 
lastRead = time.time()
shortWait =0.1
while True:
	try:
		tt= time.time()
		
		resetContinuousEvents()

		if loopCount %10 ==0:
			data0={}
			quick = U.checkNowFile(G.program)
			U.manageActions("-loop-")
			if loopCount%5==0:
				countReset = checkReset()
				if countReset:
					for gpio in GPIOdict:
						if INPUTcount[int(gpio)] ==0: 
							GPIOdict[gpio]["count"]=0
				
		
				##U.checkIfAliveNeedsToBeSend(lastMsg)
				if time.time()- lastRead > 10:
						readParams()
						lastRead = time.time()

				if restart:
					U.restartMyself(param="", reason=" new definitions",doPrint=True)

			if loopCount%100==0:
					U.echoLastAlive(G.program)
			
			if loopCount%100==0 or countReset:
				data={"sensors":{sensor:{}}}
				for gpio in GPIOdict:
						if "devId" not in GPIOdict[gpio]: continue
						data["sensors"][sensor][GPIOdict[gpio]["devId"]]={"count": GPIOdict[gpio]["count"],"burst":0}
				U.sendURL(data,wait=False)
				countReset = False


		loopCount+=1
		time.sleep(shortWait)
	except	Exception, e:
		U.toLog(-1, u"in Line {} has error={}".format(sys.exc_traceback.tb_lineno, e),doPrint=True)
		time.sleep(5.)


sys.exit(0)
