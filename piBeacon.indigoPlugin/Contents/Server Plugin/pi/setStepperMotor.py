#!/usr/bin/env python
# -*- coding: utf-8 -*-
# by Karl Wachs
# feb 5 2016
# version 0.7 

import subprocess
import time
import sys
import smbus
import json,  os, time, datetime
import copy
import RPi.GPIO as GPIO
import threading
try: import Queue
except: import queue as Queue

sys.path.append(os.getcwd())
import  piBeaconUtils   as U
import  piBeaconGlobals as G
G.program = "setStepperMotor"


###########


GPIO.setmode(GPIO.BCM)
GPIO.setwarnings(False)


# ===========================================================================
# read params
# ===========================================================================

#################################		 
def readParams():
	global sensor, output, inpRaw, inp, DEVID
	global motorType
	global oldRaw, lastRead
	global doReadParameters
	global gpiopinSET
	global lastDict
	global threadDict
	global actionQueue
	global stopThread
	global stopMoveNOW
	global isSleep


	try:

		changed =0
		inpLast= inp
		inp,inpRaw,lastRead2 = U.doRead(lastTimeStamp=lastRead)


		if inp == "": 
			inp = inpLast
			return changed
			
		if lastRead2 == lastRead: return 0
		lastRead  = lastRead2
		if inpRaw == oldRaw: return 0
		oldRaw	   = inpRaw
		U.getGlobalParams(inp)
		 


		if "output"					in inp:	 output=			 			   (inp["output"])
		#### G.debug = 2 
		if G.program not in output:
			U.logger.log(30, G.program+ " is not in parameters = not enabled, stopping "+ G.program+".py" )
			exit()


		theDict0 = output[G.program]
		devIdList= {}
		for dI in  theDict0:
			devId = str(dI)
			devIdList[devId] = True
			theDict= theDict0[devId][0]
			if devId in lastDict and lastDict[devId] == theDict: continue
			lastDict[devId] = theDict

			print theDict
			mt = theDict["motorType"]

			if not ( mt.find("unipolar") > -1 or mt.find("bipolar") > -1 or mt.find("DRV8834") > -1 or mt.find("A4988") > -1 ): continue

 			if "motorType"		 	in theDict: motorType[devId]				 		=	mt
			changed = 1

		
			gpiopinSET[devId] ={}
			if "pin_CoilA1"			in theDict: gpiopinSET[devId]["pin_CoilA1"]			=	int(theDict["pin_CoilA1"])
			if "pin_CoilA2"			in theDict: gpiopinSET[devId]["pin_CoilA2"]			=	int(theDict["pin_CoilA2"])
			if "pin_CoilB1"			in theDict: gpiopinSET[devId]["pin_CoilB1"]			=	int(theDict["pin_CoilB1"])
			if "pin_CoilB2"			in theDict: gpiopinSET[devId]["pin_CoilB2"]			=	int(theDict["pin_CoilB2"])

			if "pin_Step"			in theDict: gpiopinSET[devId]["pin_Step"]			=	int(theDict["pin_Step"])
			if "pin_Dir"			in theDict: gpiopinSET[devId]["pin_Dir"]			=	int(theDict["pin_Dir"])
			if "pin_Sleep"			in theDict: gpiopinSET[devId]["pin_Sleep"]			=	int(theDict["pin_Sleep"])

			if "pin_sensor0"		in theDict: gpiopinSET[devId]["pin_sensor0"]		=	int(theDict["pin_sensor0"])
			if "pin_sensor1"		in theDict: gpiopinSET[devId]["pin_sensor1"]		=	int(theDict["pin_sensor1"])
			if "pin_sensor2"		in theDict: gpiopinSET[devId]["pin_sensor2"]		=	int(theDict["pin_sensor2"])

			if motorType[devId] == "unipolar-4096":
				defineGPIOout(gpiopinSET[devId]["pin_CoilA1"])
				defineGPIOout(gpiopinSET[devId]["pin_CoilA2"])
				defineGPIOout(gpiopinSET[devId]["pin_CoilB1"])
				defineGPIOout(gpiopinSET[devId]["pin_CoilB2"])
				SeqCoils[devId] = []
				SeqCoils[devId].append([0, 0, 0, 0]) # off
				SeqCoils[devId].append([1, 0, 0, 1])
				SeqCoils[devId].append([1, 0, 0, 0])
				SeqCoils[devId].append([1, 1, 0, 0])
				SeqCoils[devId].append([0, 1, 0, 0])
				SeqCoils[devId].append([0, 1, 1, 0])
				SeqCoils[devId].append([0, 0, 1, 0])
				SeqCoils[devId].append([0, 0, 1, 1])
				SeqCoils[devId].append([0, 0, 0, 1])
				minStayON[devId] = 0.0001
				isSleep[devId]   = False
				nStepsInSequence[devId] = len(SeqCoils[devId]) -1

			elif motorType[devId] == "bipolar-2":
				defineGPIOout(gpiopinSET[devId]["pin_CoilA1"])
				defineGPIOout(gpiopinSET[devId]["pin_CoilA2"])
				defineGPIOout(gpiopinSET[devId]["pin_CoilB1"])
				defineGPIOout(gpiopinSET[devId]["pin_CoilB2"])
				SeqCoils[devId] = []
				SeqCoils[devId].append([0, 0, 0, 0])  # off
				SeqCoils[devId].append([0, 1, 1, 0])
				SeqCoils[devId].append([0, 1, 0, 0])
				SeqCoils[devId].append([0, 1, 0, 1])
				SeqCoils[devId].append([0, 0, 0, 1])
				SeqCoils[devId].append([1, 0, 0, 1])
				SeqCoils[devId].append([1, 0, 0, 0])
				SeqCoils[devId].append([1, 0, 1, 0])
				SeqCoils[devId].append([0, 0, 1, 0])
				minStayON[devId] = 0.0002
				isSleep[devId]   = False
				nStepsInSequence[devId] = len(SeqCoils[devId]) -1

			elif motorType[devId] == "bipolar-1":
				defineGPIOout(gpiopinSET[devId]["pin_CoilA1"])
				defineGPIOout(gpiopinSET[devId]["pin_CoilA2"])
				defineGPIOout(gpiopinSET[devId]["pin_CoilB1"])
				defineGPIOout(gpiopinSET[devId]["pin_CoilB2"])
				SeqCoils[devId] = []
				SeqCoils[devId].append([0, 0, 0, 0])  # off
				SeqCoils[devId].append([0, 1, 1, 0])
				SeqCoils[devId].append([0, 1, 0, 1])
				SeqCoils[devId].append([1, 0, 0, 1])
				SeqCoils[devId].append([1, 0, 1, 0])
				minStayON[devId] = 0.0002
				isSleep[devId]   = False
				nStepsInSequence[devId] = len(SeqCoils[devId]) -1

			elif motorType[devId].find("DRV8834") >-1:
				defineGPIOout(gpiopinSET[devId]["pin_Step"])
				defineGPIOout(gpiopinSET[devId]["pin_Dir"])
				defineGPIOout(gpiopinSET[devId]["pin_Sleep"])
				minStayON[devId] = 0.00001
				isSleep[devId]   = False
			elif motorType[devId].find("A4988") >-1:
				defineGPIOout(gpiopinSET[devId]["pin_Step"])
				defineGPIOout(gpiopinSET[devId]["pin_Dir"])
				defineGPIOout(gpiopinSET[devId]["pin_Sleep"])
				minStayON[devId] = 0.00001
				isSleep[devId]   = False

			else:
				print " stopping  motorType not defined",  motorType
				exit()

			defineGPIOin(gpiopinSET[devId]["pin_sensor0"])
			defineGPIOin(gpiopinSET[devId]["pin_sensor1"])
			defineGPIOin(gpiopinSET[devId]["pin_sensor2"])

			## start queues if new
			if devId not in threadDict:
				stopThread[devId]  = False
				stopMoveNOW[devId] = False
				actionQueue[devId] = Queue.Queue()
				threadDict[devId]  = threading.Thread(name=u'move', target=doMove, args=(devId,))
				threadDict[devId].start()
			devIdList[devId] = True


		## stop queues if not deid is gone
		delThreads ={}
		for devId in stopThread:
			if devId not in devIdList:
				stopThread[devId]  = True
				stopMoveNOW[devId] = True
				delThreads[devID]  = True
		if len(delThreads)> 0:
			time.sleep(3)
			for devId in delThreads:
				threadDict[devId].join()
				del stopThread[devId] 	
				del actionQueue[devId] 	
				del stopMoveNOW[devId] 	
				del threadDict[devId]

		return changed

	except	Exception, e:
		print  u"in Line '%s' has error='%s'" % (sys.exc_traceback.tb_lineno, e)
		U.logger.log(30, u"in Line '%s' has error='%s'" % (sys.exc_traceback.tb_lineno, e))
		time.sleep(10)
		return 3




def defineGPIOin(pin):
		try:    GPIO.setup(int(pin),	GPIO.IN, pull_up_down=GPIO.PUD_UP)
		except: pass

def defineGPIOout(pin):
		try:    GPIO.setup( int(pin),	GPIO.OUT)
		except: pass
	
def setGPIOValue(pin,val):
	#print "setting GPIO# %d,to %d"%( pin,val)
	try: GPIO.output(int(pin),int(val))
	except: pass


def getPinValue(devId,pinName):
	global gpiopinSET
	if devId not in gpiopinSET: return -1
	if pinName not in gpiopinSET[devId]: return -1
	if gpiopinSET[devId][pinName] < 1:   return -1
	ret =  GPIO.input(gpiopinSET[devId][pinName])
	return (ret-1)*-1


# ########################################
# #########  moving functions ############
# ########################################
 
# ------------------	------------------ 
def makeStep(devId,seq):
	global gpiopinSET
	global SeqCoils
	#print "makeStep", seq, SeqCoils[seq]
	setGPIOValue(gpiopinSET[devId]["pin_CoilA1"], SeqCoils[devId][seq][0])
	setGPIOValue(gpiopinSET[devId]["pin_CoilA2"], SeqCoils[devId][seq][1])
	setGPIOValue(gpiopinSET[devId]["pin_CoilB1"], SeqCoils[devId][seq][2])
	setGPIOValue(gpiopinSET[devId]["pin_CoilB2"], SeqCoils[devId][seq][3])


def makeStepDRV8834(devId,dir):
	global gpiopinSET
	global lastDirection
	global isSleep


	if  devId in isSleep and isSleep[devId]: 
		setGPIOValue(gpiopinSET[devId]["pin_Sleep"], 1)
		time.sleep(0.01)
	isSleep[devId]= False

	if devId not in lastDirection or  dir != lastDirection[devId]: 
		setGPIOValue(gpiopinSET[devId]["pin_Dir"], dir==1)
		time.sleep(0.1)
	lastDirection[devId] = dir

	setGPIOValue(gpiopinSET[devId]["pin_Step"], 1)
	time.sleep(0.00001)
	setGPIOValue(gpiopinSET[devId]["pin_Step"], 0)
	time.sleep(0.00001)

def makeStepA4988(devId,dir):
	global gpiopinSET
	global lastDirection
	global isSleep

	if  devId in isSleep and isSleep[devId]: 
		setGPIOValue(gpiopinSET[devId]["pin_Sleep"], 1)
		time.sleep(0.01)
	isSleep[devId]= False

	if devId not in lastDirection or  dir != lastDirection[devId]: 
		setGPIOValue(gpiopinSET[devId]["pin_Dir"], dir==1)
		time.sleep(0.1)
	lastDirection[devId] = dir

	setGPIOValue(gpiopinSET[devId]["pin_Step"], 1)
	time.sleep(0.00001)
	setGPIOValue(gpiopinSET[devId]["pin_Step"], 0)
	time.sleep(0.00001)

# ------------------	------------------ 
def setMotorOFFall():
	global motorType

	for devId in motorType:
		setMotorOFF(devId)
	return

# ------------------	------------------ 
def setMotorOFF(devId):
	global motorType, isSleep

	if devId in motorType:		
		if motorType[devId].find("DRV8834") >-1:
			setGPIOValue(gpiopinSET[devId]["pin_Sleep"], 0)
		elif motorType[devId].find("A4988") >-1:
			setGPIOValue(gpiopinSET[devId]["pin_Sleep"], 0)
		else:
			makeStep(devId,0)
		isSleep[devId]    = True
	return

# ------------------	------------------ 
def setMotorON(devId):
	global motorType, isSleep

	if devId in motorType:		
		if motorType[devId].find("DRV8834") >-1:
			setGPIOValue(gpiopinSET[devId]["pin_Sleep"], 1)
		elif motorType[devId].find("A4988") >-1:
			setGPIOValue(gpiopinSET[devId]["pin_Sleep"], 1)
		else:
			pass
		isSleep[devId]    = False
	return

# ------------------	------------------ 
def setMotorSleep(devId):
	global motorType, isSleep
	if devId in motorType:		
		if motorType[devId].find("DRV8834") >-1:
			setGPIOValue(gpiopinSET[devId]["pin_Sleep"], 0)
		elif motorType[devId].find("A4988") >-1:
			setGPIOValue(gpiopinSET[devId]["pin_Sleep"], 0)
		else:
			makeStep(devId,0)
		isSleep[devId]= True
	return

 
# ------------------	------------------ 
def setMotorWake(devId):
	global motorType, isSleep
	if devId in motorType:		
		if motorType[devId].find("DRV8834") >-1:
			setGPIOValue(gpiopinSET[devId]["pin_Sleep"], 1)
		elif motorType[devId].find("A4988") >-1:
			setGPIOValue(gpiopinSET[devId]["pin_Sleep"], 1)
		else:
			pass
		isSleep[devId]= False
	return

# ------------------	------------------ 
def doMove(devId): #steps, delay, direction, stopForGPIO):
 	global actionQueue
	global stopThread

	while True:
		while not actionQueue[devId].empty():
			#print" checking queue size", actionQueue[devId].qsize() 
			repeat, actions = actionQueue[devId].get()
			ii = max(repeat, 1) # repeat can by a VERY large number, then range does not work)
			while ii > 0:
				ii -= 1
				if move(devId, actions) <0: break
			if stopThread[devId]:
				sys.exit()
		if stopThread[devId]:
			sys.exit()



# ------------------	------------------ 
def move(devId, actions): #steps, delay, direction, stopForGPIO):
	global lastStep
	global gpiopinSET
	global SeqCoils
	global nStepsInSequence
	global minStayON
	global motorType
	global imputFileName
	global stopMoveNOW

	#print "move actions: ", actions, minStayON

	stopMoveNOW[devId] = False

	iSteps = 0
	for cc in actions:
		#print "cc", cc

		if stopMoveNOW[devId]: 
			#print "move stopped: =============="
			return -iSteps

		
		if cc["waitBefore"] > 0: time.sleep(cc["waitBefore"])

		if "sleepMotor" in cc: 
			setMotorSleep(devId)

		if "wakeMotor" in cc: 
			setMotorWake(devId)

		if "onMotor" in cc: 
			setMotorON(devId)

		if "offMotor" in cc: 
			setMotorOFF(devId)

		if "wait" in cc: 
			time.sleep(cc["wait"])
		
		if "steps" in cc and cc["steps"] >0 :

			steps 		= cc["steps"]
			stayOn 		= max(minStayON[devId], cc["stayOn"])
			nStayOn  	= min(stayOn, 1.)
			dir   		= cc["dir"]
			stopForGPIO = cc["stopForGPIO"]


			if devId not in lastStep: lastStep[devId]= +1
			lStep = lastStep[devId]

			#print "steps", devId, steps,  dir, delay, nStayOn, lastStep
			steps = int(steps)
			iSteps= 0
			for i in range(steps):
				for iGPIO in range(3):
					if iGPIO in stopForGPIO:
						if stopForGPIO[iGPIO] >-1:
							stop 	 = getPinValue(devId,"pin_sensor"+str(iGPIO))
							if stop == stopForGPIO[iGPIO]:
								print "stop for GPIO", stop
								#return -iSteps
					iSteps += 1
				if motorType[devId].find("DRV8834") >-1:
					makeStepDRV8834(devId,dir)
				elif motorType[devId].find("A4988") >-1:
					makeStepA4988(devId,dir)
				else:
					lStep += dir
					if lStep > nStepsInSequence[devId]: lStep = 1
					if lStep < 1: 						lStep = nStepsInSequence[devId]
					makeStep(devId,lStep)
					lastStep[devId] = lStep

				#check if new command (>) and do the delay properly,  
				startON = time.time()
				if stayOn > nStayOn:
					while True:
						if stopMoveNOW[devId]: 
							#print "move stopped: =============="
							return -iSteps
						if time.time() - startON > stayOn: break
						time.sleep(0.05)
				else:
					if stopMoveNOW[devId]: 
						#print "move stopped: =============="
						return -iSteps
					time.sleep(stayOn)

		if stopMoveNOW[devId]: 
			#print "move stopped: =============="
			return -iSteps

		if cc["waitAfter"] > 0: time.sleep(cc["waitAfter"])

	return iSteps


# ------------------	------------------ 
def checkForNewImput():
	global actionQueue
	global restart
	global imputFileName
	global stopMoveNOW


	if not os.path.isfile(imputFileName): return 

	f = open(imputFileName,"r")
	xxx = f.read()  
	f.close()
	os.remove(imputFileName)
	items=xxx.split("\n")

	for item in items:
		actions		= []
		if len(item) < 10: continue
		try:
			inpNew = json.loads(item)
		except:
			print " can not load ", item
			continue

		#print inpNew
		try:
			if "dev.id"		in inpNew:  devId   = str(inpNew["dev.id"])
			else:						return 

			if "repeat"		in inpNew:  repeat  = int(inpNew["repeat"])
			else:						repeat = 0

			if "waitForLast" in inpNew:	stopMoveNOW[devId] = inpNew["waitForLast"] == "0"
			else:						stopMoveNOW[devId] = False

			if "command" in inpNew:
				inp = inpNew["command"]
				newCommand = True
				restart = False
				#print "command", inp
				for cc in inp:
					#print cc
					if cc != {}: actions.append({"steps":0, "stayOn":0, "waitBefore":0, "waitAfter":0, "wait":0, "dir":0, "stopForGPIO":[-1,-1,-1]})
					if u"steps"		in cc:  
						actions[-1]["steps"] 			= int(cc["steps"])
					if u"stayOn"		in cc:  
						actions[-1]["stayOn"]   		= float(cc["stayOn"])/10000.
					if u"waitBefore"		in cc:  
						actions[-1]["waitBefore"]   	= float(cc["waitBefore"])
					if u"waitAfter"		in cc:  
						actions[-1]["waitAfter"]   		= float(cc["waitAfter"])
					if u"dir"		in cc:  
						actions[-1]["dir"]   			= int(cc["dir"])
					if u"GPIO0"	in cc:  
						actions[-1]["stopForGPIO"][0]	= int(cc["GPIO0"])
					if u"GPIO1"	in cc:  
						actions[-1]["stopForGPIO"][1]	= int(cc["GPIO1"])
					if u"GPIO2"	in cc:  
						actions[-1]["stopForGPIO"][2]	= int(cc["GPIO2"])

					if u"sleepMotor"	in cc:  
						actions[-1]["sleepMotor"] = True

					if u"wakeMotor"	in cc:  
						actions[-1]["wakeMotor"] = True

					if u"offMotor"	in cc:  
						actions[-1]["offMotor"] = True

					if u"onMotor"	in cc:  
						actions[-1]["onMotor"] = True

					if u"wait"	in cc:  
						actions[-1]["wait"] = float(cc["wait"])

			if u"restart"				in inpNew:  
				restart   = (inpNew["restart"] =="1")
 
			if restart:
				time.sleep(0.1)
				U.restartmyself()
				subprocess.call("/usr/bin/python "+G.homeDir+G.program+".py &", shell=True)

			if stopMoveNOW[devId]: 
				print" clear queue bf " ,actionQueue[devId].qsize() 
				actionQueue[devId].queue.clear()
				print" clear queue af",actionQueue[devId].qsize() 
			actionQueue[devId].put((repeat,actions)) 
			print "adding new commands",devId, stopMoveNOW[devId], repeat,actionQueue[devId].qsize() , actions

		except Exception, e:
			U.logger.log(30, u"in Line '%s' has error='%s'" % (sys.exc_traceback.tb_lineno, e))
			print  u"in Line '%s' has error='%s'" % (sys.exc_traceback.tb_lineno, e)
	return 
   

######### main ######

#################################
#################################
#################################

global sensor, output, inpRaw
global oldRaw,	lastRead, inp
global doReadParameters
global lastStep, colPWM
global gpiopinSET, SeqCoils
global printON
global minStayON
global lastDirection
global isSleep
global lastDict
global imputFileName
global restart
global threadDict
global stopThread
global actionQueue
global stopMoveNOW

threadDict			= {}
stopThread			= {}
actionQueue			= {}
stopMoveNOW			= {}

oldRaw				= ""
lastRead			= 0
inpRaw				= ""
inp					= ""
debug				= 5
loopCount			= 0
sensor				= G.program

restart				=  False

iastDict 			= {}
isSleep				= {}
iastDirection		= {}
motorType			= {}
minStayON			= {} 
lastStep			= {}
gpiopinSET			= {}
SeqCoils			= {}
nStepsInSequence	= {}


imputFileName = G.homeDir+"temp/"+G.program+".inp"

U.setLogging()

myPID	=   str(os.getpid())
readParams()
U.logger.log(10, G.program+"  command :" + unicode(sys.argv))



command =""
try:
	if len(sys.argv) >1:
		command = json.loads(sys.argv[1])
except:
	pass

lastAlive = time.time()
subprocess.call("echo "+str(time.time())+" > "+ G.homeDir+"temp/alive."+sensor, shell=True)


U.killOldPgm(myPID,G.program+".py")# del old instances of myself if they are still running
   
if "startAtDateTime" in command:
	try:
		delayStart = max(0,U.calcStartTime(command,"startAtDateTime")-time.time())
		if delayStart > 0:
			U.logger.log(10, "delayStart delayed by: "+ str(delayStart))
			time.sleep(delayStart)
	except:
		pass

lastAlive = time.time()
U.echoLastAlive(G.program)



if readParams() ==3:
		U.logger.log(30," parameters not defined")
		time.sleep(20)
		exit()
	



myPID		= str(os.getpid())
U.killOldPgm(myPID,G.program+".py")# kill old instances of myself if they are still running

U.echoLastAlive(G.program)

G.lastAliveSend	 = time.time() -1000


print "motorType", motorType
print "nStepsInSequence, SeqCoils", nStepsInSequence, SeqCoils
print "gpiopinSET",gpiopinSET
print "minStayON", minStayON


printON 	= True
t0			= time.time()

setMotorOFFall()

lastRead = time.time()

wait = 0.5

U.startAdhocWebserver()


while True:
			
	U.checkAdhocWebserverOutput()

	checkForNewImput()
	time.sleep(wait)
	if time.time() - lastRead > 10:
		readParams()
		lastRead = time.time()
