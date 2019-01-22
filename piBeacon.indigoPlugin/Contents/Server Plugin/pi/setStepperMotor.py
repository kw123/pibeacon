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
import	RPi.GPIO as GPIO
import threading
import Queue

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
	global isDisabled
	global isReset


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
		 


		if "debugRPI"				in inp:	 G.debug=		  				int(inp["debugRPI"]["debugRPIOUTPUT"])
		if "output"					in inp:	 output=			 			   (inp["output"])
		#### G.debug = 2 
		if G.program not in output:
			U.toLog(-1, G.program+ " is not in parameters = not enabled, stopping "+ G.program+".py" )
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
			if "pin_Coil1"			in theDict: gpiopinSET[devId]["pin_Coil1"]			=	int(theDict["pin_Coil1"])
			if "pin_Coil2"			in theDict: gpiopinSET[devId]["pin_Coil2"]			=	int(theDict["pin_Coil2"])
			if "pin_Coil3"			in theDict: gpiopinSET[devId]["pin_Coil3"]			=	int(theDict["pin_Coil3"])
			if "pin_Coil4"			in theDict: gpiopinSET[devId]["pin_Coil4"]			=	int(theDict["pin_Coil4"])

			if "pin_Step"			in theDict: gpiopinSET[devId]["pin_Step"]			=	int(theDict["pin_Step"])
			if "pin_Dir"			in theDict: gpiopinSET[devId]["pin_Dir"]			=	int(theDict["pin_Dir"])
			if "pin_Sleep"			in theDict: gpiopinSET[devId]["pin_Sleep"]			=	int(theDict["pin_Sleep"])
			if "pin_Enable"			in theDict: gpiopinSET[devId]["pin_Enable"]			=	int(theDict["pin_Enable"])
			if "pin_Fault"			in theDict: gpiopinSET[devId]["pin_Fault"]			=	int(theDict["pin_Fault"])
			if "pin_Reset"			in theDict: gpiopinSET[devId]["pin_Reset"]			=	int(theDict["pin_Reset"])

			if "pin_sensor0"		in theDict: gpiopinSET[devId]["pin_sensor0"]		=	int(theDict["pin_sensor0"])
			if "pin_sensor1"		in theDict: gpiopinSET[devId]["pin_sensor1"]		=	int(theDict["pin_sensor1"])
			if "pin_sensor2"		in theDict: gpiopinSET[devId]["pin_sensor2"]		=	int(theDict["pin_sensor2"])

			if motorType[devId] == "unipolar-4096":
				defineGPIOout(gpiopinSET[devId]["pin_Coil1"])
				defineGPIOout(gpiopinSET[devId]["pin_Coil2"])
				defineGPIOout(gpiopinSET[devId]["pin_Coil3"])
				defineGPIOout(gpiopinSET[devId]["pin_Coil4"])
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
				minDelay[devId] = 0.0001
				nStepsInSequence[devId] = len(SeqCoils[devId]) -1

			elif motorType[devId] == "bipolar-200-2":
				defineGPIOout(gpiopinSET[devId]["pin_Coil1"])
				defineGPIOout(gpiopinSET[devId]["pin_Coil2"])
				defineGPIOout(gpiopinSET[devId]["pin_Coil3"])
				defineGPIOout(gpiopinSET[devId]["pin_Coil4"])
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
				minDelay[devId] = 0.0002
				nStepsInSequence[devId] = len(SeqCoils[devId]) -1

			elif motorType[devId] == "bipolar-200-1":
				defineGPIOout(gpiopinSET[devId]["pin_Coil1"])
				defineGPIOout(gpiopinSET[devId]["pin_Coil2"])
				defineGPIOout(gpiopinSET[devId]["pin_Coil3"])
				defineGPIOout(gpiopinSET[devId]["pin_Coil4"])
				SeqCoils[devId] = []
				SeqCoils[devId].append([0, 0, 0, 0])  # off
				SeqCoils[devId].append([0, 1, 1, 0])
				SeqCoils[devId].append([0, 1, 0, 1])
				SeqCoils[devId].append([1, 0, 0, 1])
				SeqCoils[devId].append([1, 0, 1, 0])
				minDelay[devId] = 0.0002
				nStepsInSequence[devId] = len(SeqCoils[devId]) -1

			elif motorType[devId].find("DRV8834") >-1:
				defineGPIOout(gpiopinSET[devId]["pin_Step"])
				defineGPIOout(gpiopinSET[devId]["pin_Dir"])
				defineGPIOout(gpiopinSET[devId]["pin_Sleep"])
				defineGPIOout(gpiopinSET[devId]["pin_Enable"])
				defineGPIOin(gpiopinSET[devId]["pin_Fault"])
				minDelay[devId] = 0.00001
				isSleep[devId]   = False
				isDisabled[devId] = False
				isReset[devId]   = False
			elif motorType[devId].find("A4988") >-1:
				defineGPIOout(gpiopinSET[devId]["pin_Step"])
				defineGPIOout(gpiopinSET[devId]["pin_Dir"])
				defineGPIOout(gpiopinSET[devId]["pin_Sleep"])
				defineGPIOout(gpiopinSET[devId]["pin_Enable"])
				defineGPIOout(gpiopinSET[devId]["pin_Reset"])
				minDelay[devId] = 0.00001
				isSleep[devId]   = False
				isDisabled[devId] = False
				isReset[devId]   = False

			else:
				print " stopping  motorType not defined"+ motorType
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
		U.toLog(-1, u"in Line '%s' has error='%s'" % (sys.exc_traceback.tb_lineno, e))
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
	setGPIOValue(gpiopinSET[devId]["pin_Coil1"], SeqCoils[devId][seq][0])
	setGPIOValue(gpiopinSET[devId]["pin_Coil2"], SeqCoils[devId][seq][1])
	setGPIOValue(gpiopinSET[devId]["pin_Coil3"], SeqCoils[devId][seq][2])
	setGPIOValue(gpiopinSET[devId]["pin_Coil4"], SeqCoils[devId][seq][3])


def makeStepDRV8834(devId,dir):
	global gpiopinSET
	global lastDirection
	global isDisabled
	global isSleep

	#print "makeStep", devId,dir
	if devId in isDisabled and  isDisabled[devId]: 
		setGPIOValue(gpiopinSET[devId]["pin_Enable"], 0)
		time.sleep(0.01)
	isDisabled[devId]= False

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
	global isDisabled
	global isSleep
	global isReset

	#print "makeStep", devId,dir
	if devId in isDisabled and  isDisabled[devId]: 
		setGPIOValue(gpiopinSET[devId]["pin_Enable"], 0)
		time.sleep(0.01)
	isDisabled[devId]= False

	if  devId in isSleep and isSleep[devId]: 
		setGPIOValue(gpiopinSET[devId]["pin_Sleep"], 1)
		time.sleep(0.01)
	isSleep[devId]= False

	if  devId in isReset and isReset[devId]: 
		setGPIOValue(gpiopinSET[devId]["pin_Reset"], 1)
		time.sleep(0.01)
	isReset[devId]= False

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
	global motorType, isDisabled, isSleep, isReset

	if devId in motorType:		
		if motorType[devId].find("DRV8834") >-1:
			setGPIOValue(gpiopinSET[devId]["pin_Sleep"], 0)
			setGPIOValue(gpiopinSET[devId]["pin_Enable"], 1)
		elif motorType[devId].find("A4988") >-1:
			setGPIOValue(gpiopinSET[devId]["pin_Sleep"], 0)
			setGPIOValue(gpiopinSET[devId]["pin_Enable"], 1)
			setGPIOValue(gpiopinSET[devId]["pin_Reset"], 0)
		else:
			makeStep(devId,0)
		isReset[devId]    = True
		isSleep[devId]    = True
		isDisabled[devId] = True
	return

# ------------------	------------------ 
def setMotorSleep(devId):
	global motorType, isDisabled, isSleep
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
	global minDelay
	global motorType
	global imputFileName
	global stopMoveNOW

	#print "move actions: ", actions, minDelay

	stopMoveNOW[devId] = False

	iSteps = 0
	for cc in actions:
		#print "cc", cc

		
		if cc["delayBf"] > 0: time.sleep(cc["delayBf"])

		if "sleep" in cc: 
			setMotorSleep(devId)
			continue
			
		steps 		= cc["steps"]
		delay 		= max(minDelay[devId], cc["delay"])
		nDelay  	= min(delay, 1.)
		dir   		= cc["dir"]
		stopForGPIO = cc["stopForGPIO"]


		if devId not in lastStep: lastStep[devId]= +1
		lStep = lastStep[devId]

		#print "steps", devId, steps,  dir, delay, nDelay, lastStep
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
			startDelay = time.time()
			if delay > nDelay:
				while True:
					if stopMoveNOW[devId]: 
						#print "move stopped: =============="
						return -iSteps
					if time.time() - startDelay > delay: break
					time.sleep(0.05)
			else:
				if stopMoveNOW[devId]: 
					#print "move stopped: =============="
					return -iSteps
				time.sleep(delay)

		#if delay < 100 or delay > 0.5: setOFF()

	return iSteps


# ------------------	------------------ 
def testForFault(devId):
	global gpiopinSET
	if motorType[devId].find("DRV8834") == -1: return False

	val  = getPinValue(devId,"pin_Fault")
	if   val == 0:
			print "fault indicator ON"
			return True
	elif val == 1:
			return False

#
def checkForNewImput():
	global actionQueue
	global restart
	global imputFileName
	global stopMoveNOW

	actions		= []
	devId		= ""
	stopForGPIO	= [-1,-1,-1]

	inpNew, inpRaw = U.doRead(imputFileName)
	if inpNew == "": return 
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
				if cc != {}: actions.append({"steps":0,"delay":0,"delayBf":0,"dir":0,"stopForGPIO":[-1,-1,-1]})
				if u"steps"		in cc:  
					actions[-1]["steps"] 			= int(cc["steps"])
				if u"delay"		in cc:  
					actions[-1]["delay"]   			= float(cc["delay"])/10000.
				if u"delayBf"		in cc:  
					actions[-1]["delayBf"]   		= float(cc["delayBf"])
				if u"dir"		in cc:  
					actions[-1]["dir"]   			= int(cc["dir"])
				if u"GPIO0"	in cc:  
					actions[-1]["stopForGPIO"][0]	= int(cc["GPIO0"])
				if u"GPIO1"	in cc:  
					actions[-1]["stopForGPIO"][1]	= int(cc["GPIO1"])
				if u"GPIO2"	in cc:  
					actions[-1]["stopForGPIO"][2]	= int(cc["GPIO2"])
				if u"sleep"	in cc:  
					actions[-1]["sleep"] = True

		if u"restart"				in inpNew:  
			restart   = (inpNew["restart"] =="1")
 
		os.remove(imputFileName)

		if restart:
			time.sleep(0.1)
			U.restartmyself()
			os.system("/usr/bin/python "+G.homeDir+G.program+".py &")

		if stopMoveNOW[devId]: 
			#print" clear queue bf " ,actionQueue[devId].qsize() 
			actionQueue[devId].queue.clear()
			#print" clear queue af",actionQueue[devId].qsize() 
		actionQueue[devId].put((repeat,actions)) 
		#print "adding new commands",devId, repeat, actions, stopMoveNOW[devId]

		return 
	
	except  Exception, e:
		U.toLog(-1, u"in Line '%s' has error='%s'" % (sys.exc_traceback.tb_lineno, e),doPrint=True)
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
global minDelay
global lastDirection
global isDisabled, isSleep, isReset
global isFault
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

isFault				= {}
lastDict 			= {}
isDisabled			= {}
isSleep				= {}
isReset				= {}
lastDirection		= {}
motorType			= {}
minDelay			= {} 
lastStep			= {}
gpiopinSET			= {}
SeqCoils			= {}
nStepsInSequence	= {}


imputFileName = G.homeDir+"temp/"+G.program+".inp"


myPID	=   str(os.getpid())
readParams()
U.toLog(0, G.program+"  command :" + unicode(sys.argv))



command =""
try:
	if len(sys.argv) >1:
		command = json.loads(sys.argv[1])
except:
	pass

lastAlive = time.time()
os.system("echo "+str(time.time())+" > "+ G.homeDir+"temp/alive."+sensor)


U.killOldPgm(myPID,G.program+".py")# del old instances of myself if they are still running
   
if "startAtDateTime" in command:
	try:
		delayStart = max(0,U.calcStartTime(command,"startAtDateTime")-time.time())
		if delayStart > 0:
			U.toLog(2, "delayStart delayed by: "+ str(delayStart))
			time.sleep(delayStart)
	except:
		pass

lastAlive = time.time()
U.echoLastAlive(G.program)



if readParams() ==3:
		U.toLog(-1," parameters not defined", doPrint=True)
		time.sleep(20)
		exit()
	



myPID		= str(os.getpid())
U.killOldPgm(myPID,G.program+".py")# kill old instances of myself if they are still running

U.echoLastAlive(G.program)

G.lastAliveSend	 = time.time() -1000


print "motorType", motorType
print "nStepsInSequence, SeqCoils", nStepsInSequence, SeqCoils
print "gpiopinSET",gpiopinSET
print "minDelay", minDelay


printON 	= True
t0			= time.time()

setMotorOFFall()

lastRead = time.time()

wait = 0.5

while True:
			

	checkForNewImput()
	time.sleep(wait)
	if time.time() - lastRead > 10:
		readParams()
		lastRead = time.time()
