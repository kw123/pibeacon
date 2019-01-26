#!/usr/bin/env python
# -*- coding: utf-8 -*-
# by Karl Wachs
# feb 5 2016
# version 0.9 
##
###
import RPi.GPIO as GPIO
import sys, os, time, json, datetime,subprocess,copy
import threading
import Queue


sys.path.append(os.getcwd())
import	piBeaconUtils	as U
import	piBeaconGlobals as G
G.program = "sunDial"


GPIO.setmode(GPIO.BCM)
GPIO.setwarnings(False)



# ########################################
# #########    read params           #####
# ########################################

# ------------------    ------------------ 
def readParams():
	global sensor, output, inpRaw, inp, useRTC
	global speed, amPM1224, motorType
	global lastCl, timeZone, currTZ
	global oldRaw, lastRead
	global doReadParameters
	global gpiopinSET
	global clockDictLast
	global colPWM, beepPWM

	try:

		changed =0
		inpLast= inp
		inp,inpRaw,lastRead2 = U.doRead(lastTimeStamp=lastRead)


		if inp == "": 
			inp = inpLast
			return changed
			
		if lastRead2 == lastRead: return changed
		lastRead  = lastRead2
		if inpRaw == oldRaw: return changed
		oldRaw	   = inpRaw
		U.getGlobalParams(inp)
		 


		if "debugRPI"				in inp:	 G.debug=		  				int(inp["debugRPI"]["debugRPIOUTPUT"])
		if "useRTC"					in inp:	 useRTC=					       (inp["useRTC"])
		if "pin_webAdhoc"		    in inp:  gpiopinSET["pin_webAdhoc"]	= 	int(inp["pin_webAdhoc"])
		if "output"					in inp:	 output=			 			   (inp["output"])
		#### G.debug = 2 
		if G.program not in output:
			U.toLog(-1, G.program+ " is not in parameters = not enabled, stopping "+ G.program+".py" )
			exit()
		clockLightSensor =0
		if "clockLightSensor"			in inp: 
			try:	xx = float(inp["clockLightSensor"])
			except: xx = 0
			clockLightSensor =xx


		clock = output[G.program]
		for devId in  clock:
			clockDict		= clock[devId][0]
			if clockDictLast == clockDict: continue
			clockDictLast 	= clockDict
			print clockDict
			if "timeZone"			 in clockDict:	
				if timeZone !=			   (clockDict["timeZone"]):
					changed = max(2, changed)  
					timeZone =				   (clockDict["timeZone"])
					tznew  = int(timeZone.split(" ")[0])
					if tznew != currTZ:
						U.toLog(-1, u"changing timezone from "+str(currTZ)+"  "+timeZones[currTZ+12]+" to "+str(tznew)+"  "+timeZones[tznew+12])
						os.system("sudo cp /usr/share/zoneinfo/"+timeZones[tznew+12]+" /etc/localtime")
						currTZ = tznew

			clockDict["timeZone"] = str(currTZ)+" "+ timeZones[currTZ+12]
				
			if "intensityMult"		in clockDict:  intensity["Mult"]				=	float(clockDict["intensityMult"])
			if "intensityMax"		in clockDict:  intensity["Max"]					=	float(clockDict["intensityMax"])
			if "intensityMin"		in clockDict:  intensity["Min"]					=	float(clockDict["intensityMin"])
			if "speed"			 	in clockDict:  speed		   					=	float(clockDict["speed"])
 			if "amPM1224"		 	in clockDict:  gpiopinSET["amPM1224"]	 		=	int(clockDict["amPM1224"])
 			if "motorType"		 	in clockDict:  motorType				 		=	    (clockDict["motorType"])

			if "pin_CoilA1"			in clockDict: gpiopinSET["pin_CoilA1"]			=	int(clockDict["pin_CoilA1"])
			if "pin_CoilA2"			in clockDict: gpiopinSET["pin_CoilA2"]			=	int(clockDict["pin_CoilA2"])
			if "pin_CoilB1"			in clockDict: gpiopinSET["pin_CoilB1"]			=	int(clockDict["pin_CoilB1"])
			if "pin_CoilB2"			in clockDict: gpiopinSET["pin_CoilB2"]			=	int(clockDict["pin_CoilB2"])

			if "pin_Step"			in clockDict: gpiopinSET["pin_Step"]			=	int(clockDict["pin_Step"])
			if "pin_Dir"			in clockDict: gpiopinSET["pin_Dir"]				=	int(clockDict["pin_Dir"])
			if "pin_Sleep"			in clockDict: gpiopinSET["pin_Sleep"]			=	int(clockDict["pin_Sleep"])
			if "pin_Enable"			in clockDict: gpiopinSET["pin_Enable"]			=	int(clockDict["pin_Enable"])
			if "pin_Fault"			in clockDict: gpiopinSET["pin_Fault"]			=	int(clockDict["pin_Fault"])
			if "pin_Reset"			in clockDict: gpiopinSET["pin_Reset"]			=	int(clockDict["pin_Reset"])


			if "pin_Up"				in clockDict: gpiopinSET["pin_Up"]				=	int(clockDict["pin_Up"])
			if "pin_Dn"				in clockDict: gpiopinSET["pin_Dn"]				=	int(clockDict["pin_Dn"])
			if "pin_intensity"		in clockDict: gpiopinSET["pin_intensity"]		=	int(clockDict["pin_intensity"])
			if "pin_restart"		in clockDict: gpiopinSET["pin_restart"]			=	int(clockDict["pin_restart"])
			if "pin_sensor0"		in clockDict: gpiopinSET["pin_sensor0"]			=	int(clockDict["pin_sensor0"])
			if "pin_sensor12"		in clockDict: gpiopinSET["pin_sensor12"]		=	int(clockDict["pin_sensor12"])
			if "pin_rgbLED_R"		in clockDict: gpiopinSET["pin_rgbLED"][0]		=	int(clockDict["pin_rgbLED_R"])
			if "pin_rgbLED_G"		in clockDict: gpiopinSET["pin_rgbLED"][1]		=	int(clockDict["pin_rgbLED_G"])
			if "pin_rgbLED_B"		in clockDict: gpiopinSET["pin_rgbLED"][2]		=	int(clockDict["pin_rgbLED_B"])
			if "pin_amPM1224"		in clockDict: gpiopinSET["pin_amPM1224"]		=	int(clockDict["pin_amPM1224"])
			if "pin_beep"			in clockDict: gpiopinSET["pin_beep"]			=	int(clockDict["pin_beep"])




			if motorType.find("unipolar") >-1 or motorType.find("bipolar") >-1:
				defineGPIOout(gpiopinSET["pin_CoilA1"])
				defineGPIOout(gpiopinSET["pin_CoilA2"])
				defineGPIOout(gpiopinSET["pin_CoilB1"])
				defineGPIOout(gpiopinSET["pin_CoilB2"])
			elif motorType.find("DRV8834") >-1 :
				defineGPIOout(gpiopinSET["pin_Step"])
				defineGPIOout(gpiopinSET["pin_Dir"])
				defineGPIOout(gpiopinSET["pin_Sleep"])
				defineGPIOout(gpiopinSET["pin_Enable"])
				defineGPIOin("pin_Fault")
			elif motorType.find("A4988") >-1:
				defineGPIOout(gpiopinSET["pin_Step"])
				defineGPIOout(gpiopinSET["pin_Dir"])
				defineGPIOout(gpiopinSET["pin_Sleep"])
				defineGPIOout(gpiopinSET["pin_Enable"])
				defineGPIOout(gpiopinSET["pin_Reset"])
							

			defineGPIOout(gpiopinSET["pin_rgbLED"][0])
			defineGPIOout(gpiopinSET["pin_rgbLED"][1])
			defineGPIOout(gpiopinSET["pin_rgbLED"][2])

			defineGPIOout(gpiopinSET["pin_beep"])


			defineGPIOin("pin_Up")
			defineGPIOin("pin_Dn")
			defineGPIOin("pin_intensity")
			defineGPIOin("pin_restart")
			defineGPIOin("pin_sensor0")
			defineGPIOin("pin_sensor12")
			defineGPIOin("pin_amPM1224")
			defineGPIOin("pin_webAdhoc")


			colPWM = {}
			for pin in gpiopinSET["pin_rgbLED"]:
				colPWM[pin] = GPIO.PWM(pin, 100)

			try: beepPWM = GPIO.PWM(gpiopinSET["pin_beep"], 100)
			except: beepPWM=""

			defineMotorType()


			## print clockDict
			break
		return changed

	except	Exception, e:
		print  u"in Line '%s' has error='%s'" % (sys.exc_traceback.tb_lineno, e)
		U.toLog(-1, u"in Line '%s' has error='%s'" % (sys.exc_traceback.tb_lineno, e))
		time.sleep(10)
		return 3

# ########################################
# #########    basic setup funtions  #####
# ########################################
# ------------------    ------------------ 
def setupTimeZones():
	global timeZone, timeZones, currTZ
	timeZone = ""
	timeZones =[]
	for ii in range(-12,13):
		if ii<0:
			timeZones.append("/Etc/GMT+" +str(abs(ii)))
		else:
			timeZones.append("/Etc/GMT-"+str(ii))
		
	timeZones[12+12] = "Pacific/Auckland"
	timeZones[11+12] = "Pacific/Pohnpei"
	timeZones[10+12] = "Australia/Melbourne"
	timeZones[9+12]	 = "Asia/Tokyo"
	timeZones[8+12]	 = "Asia/Shanghai"
	timeZones[7+12]	 = "Asia/Saigon"
	timeZones[6+12]	 = "Asia/Dacca"
	timeZones[5+12]	 = "Asia/Karachi"
	timeZones[4+12]	 = "Asia/Dubai"
	timeZones[3+12]	 = "/Europe/Moscow"
	timeZones[2+12]	 = "/Europe/Helsinki"
	timeZones[1+12]	 = "/Europe/Berlin"
	timeZones[0+12]	 = "/Europe/London"
	timeZones[-1+12] = "Atlantic/Cape_Verde"
	timeZones[-2+12] = "Atlantic/South_Georgia"
	timeZones[-3+12] = "America/Buenos_Aires"
	timeZones[-4+12] = "America/Puerto_Rico"
	timeZones[-5+12] = "/US/Eastern"
	timeZones[-6+12] = "/US/Central"
	timeZones[-7+12] = "/US/Mountain"
	timeZones[-8+12] = "/US/Pacific"
	timeZones[-9+12] = "/US/Alaska"
	timeZones[-10+12] = "Pacific/Honolulu"
	timeZones[-11+12] = "US/Samoa"
	#print "timeZones:", timeZones

	#delta to UTC:
	JulDelta = int(subprocess.Popen("date -d '1 Jul' +%z " ,shell=True,stdout=subprocess.PIPE,stderr=subprocess.PIPE).communicate()[0].strip("\n").strip())/100
	JanDelta = int(subprocess.Popen("date -d '1 Jan' +%z " ,shell=True,stdout=subprocess.PIPE,stderr=subprocess.PIPE).communicate()[0].strip("\n").strip())/100
	NowDelta = int(subprocess.Popen("date  +%z "		   ,shell=True,stdout=subprocess.PIPE,stderr=subprocess.PIPE).communicate()[0].strip("\n").strip())/100

	currTZ = JanDelta
	return 


# ------------------    ------------------ 
def defineMotorType():
	global SeqCoils, minStayOn, motorType, stepsIn360, maxStepsUsed, nStepsInSequence
	SeqCoils = []
	print "motorType", motorType

	try:
		mtSplit    		= motorType.split("-")
		mult       		= int(mtSplit[2])
		stepsIn360 		= int(mtSplit[1])*mult
		maxStepsUsed	= stepsIn360 -1
	except:
		print " stopping  motorType wrong", motorType, mtSplit
		exit()

	if mtSplit[0] == "bipolar":
		minStayOn = 0.001
		if motorType.find("-1") >-1:
			SeqCoils.append([0, 0, 0, 0])  # off
			SeqCoils.append([0, 1, 1, 0])
			SeqCoils.append([0, 1, 0, 1])
			SeqCoils.append([1, 0, 0, 1])
			SeqCoils.append([1, 0, 1, 0])
		elif motorType.find("-2") >-1:
			SeqCoils.append([0, 0, 0, 0])  # off
			SeqCoils.append([0, 1, 1, 0])
			SeqCoils.append([0, 1, 0, 0])
			SeqCoils.append([0, 1, 0, 1])
			SeqCoils.append([0, 0, 0, 1])
			SeqCoils.append([1, 0, 0, 1])
			SeqCoils.append([1, 0, 0, 0])
			SeqCoils.append([1, 0, 1, 0])
			SeqCoils.append([0, 0, 1, 0])

	elif mtSplit[0] == "unipolar":
		SeqCoils.append([0, 0, 0, 0]) # off
		SeqCoils.append([1, 0, 0, 1])
		SeqCoils.append([1, 0, 0, 0])
		SeqCoils.append([1, 1, 0, 0])
		SeqCoils.append([0, 1, 0, 0])
		SeqCoils.append([0, 1, 1, 0])
		SeqCoils.append([0, 0, 1, 0])
		SeqCoils.append([0, 0, 1, 1])
		SeqCoils.append([0, 0, 0, 1])
		minStayOn = 0.001
		maxStepsUsed	= stepsIn360 -10

	elif mtSplit[0] =="DRV8834" or mtSplit[0] == "A4988":
		minStayOn = 0.001

	else:
		print " stopping  motorType not defined"
		exit()

	nStepsInSequence= len(SeqCoils) -1
	print nStepsInSequence, SeqCoils
	return 

# ------------------    ------------------ 
def setgpiopinSET():
	global gpiopinSET
	### GPIO pins ########
	gpiopinSET						= {}
	gpiopinSET["pin_CoilA1"]      	= -1 # blue
	gpiopinSET["pin_CoilA2"]      	= -1 # pink
	gpiopinSET["pin_CoilB1"]      	= -1 # yellow
	gpiopinSET["pin_CoilB2"]      	= -1 # orange

	gpiopinSET["pin_Fault"]      	= -1 # orange
	gpiopinSET["pin_Dir"]      		= -1 # orange
	gpiopinSET["pin_Step"]      	= -1 # orange
	gpiopinSET["pin_Sleep"]      	= -1 # orange
	gpiopinSET["pin_Enable"]    	= -1 # orange
	gpiopinSET["pin_Reset"] 		= -1


	gpiopinSET["pin_rgbLED"]	 	= [-1,-1,-1] # r g b pins

	gpiopinSET["pin_Up"]   			= -1
	gpiopinSET["pin_Dn"]  			= -1

	gpiopinSET["pin_intensity"]		= -1
	gpiopinSET["pin_restart"]		= -1

	gpiopinSET["pin_sensor0"]  		= -1
	gpiopinSET["pin_sensor12"] 		= -1

	gpiopinSET["pin_amPM1224"]   	= -1
	gpiopinSET["pin_webAdhoc"]  	= -1
	gpiopinSET["pin_beep"]  		= -1

	return 


# ########################################
# #########    masic GPIO funtions  ######
# ########################################

# ------------------    ------------------ 
def defineGPIOin(pin):
	try:    GPIO.setup(int(gpiopinSET[pin]),	GPIO.IN, pull_up_down=GPIO.PUD_UP)
	except: pass
	return

# ------------------    ------------------ 
def defineGPIOout(pin):
	try:    GPIO.setup( int(pin),	GPIO.OUT)
	except: pass
	return
	
# ------------------    ------------------ 
def setGPIOValue(pin,val):
	#print "setting GPIO# %d,to %d"%( pin,val)
	GPIO.output(int(pin),int(val))
	return


# ------------------    ------------------ 
def getPinValue(pinName):
	global gpiopinSET
	if pinName not in gpiopinSET: return -1
	if gpiopinSET[pinName] < 1:   return -1
	ret =  GPIO.input(gpiopinSET[pinName])
	return (ret-1)*-1



# ########################################
# #########  moving functions ############
# ########################################
 
# ------------------    ------------------ 
def makeStep(seq):
	global gpiopinSET
	global SeqCoils
	#print "makeStep", seq, SeqCoils[seq]
	setGPIOValue(gpiopinSET["pin_CoilA1"], SeqCoils[seq][0])
	setGPIOValue(gpiopinSET["pin_CoilA2"], SeqCoils[seq][1])
	setGPIOValue(gpiopinSET["pin_CoilB1"], SeqCoils[seq][2])
	setGPIOValue(gpiopinSET["pin_CoilB2"], SeqCoils[seq][3])


def makeStepDRV8834(dir):
	global gpiopinSET
	global lastDirection
	global isDisabled
	global isSleep


	if isDisabled or isSleep: 
		setMotorON()
		time.sleep(0.01)

	if dir != lastDirection: 
		setGPIOValue(gpiopinSET["pin_Dir"], dir==1)
		lastDirection = dir
		time.sleep(0.1)

	setGPIOValue(gpiopinSET["pin_Step"], 1)
	time.sleep(0.0001)
	setGPIOValue(gpiopinSET["pin_Step"], 0)
	time.sleep(0.0001)


# ------------------    ------------------ 
def setMotorON():
	global motorType, isDisabled, isSleep
	if motorType.find("DRV8834") >-1 or motorType.find("A4988") >-1 :
		setGPIOValue(gpiopinSET["pin_Sleep"], 1)
		setGPIOValue(gpiopinSET["pin_Enable"], 0)
	else:
		pass
	isSleep 	= False
	isDisabled  = False

def setMotorOFF():
	global motorType, isDisabled, isSleep
	if motorType.find("DRV8834") >-1 or motorType.find("A4988") >-1 :
		setGPIOValue(gpiopinSET["pin_Sleep"], 0)
		setGPIOValue(gpiopinSET["pin_Enable"], 1)
	else:
		makeStep(0)
	isSleep 	= True
	isDisabled  = True

def setMotorSleep():
	global motorType, isDisabled, isSleep
	if motorType.find("DRV8834") >-1 or motorType.find("A4988") >-1 :
		setGPIOValue(gpiopinSET["pin_Sleep"], 0)
	else:
		makeStep(0)
	isSleep = True

 
# ------------------    ------------------ 
def move(stayOn, steps, direction, force = 0):
	global lastStep
	global gpiopinSET
	global SeqCoils
	global nStepsInSequence
	global whereIs12
	global minStayOn
	global motorType


	stayOn = max(minStayOn,stayOn)
	lStep = lastStep
	#print "steps", steps,  direction, stayOn, lastStep
	steps = int(steps)
	iSteps= 0
	if iSteps > 0 and speed == 1: makeStep(ii)
	for i in range(steps):

		if getPinValue("pin_sensor12") ==1: 
			whereIs12[direction] = iSteps
			whereIs12["active"]  = True
		else:
			whereIs12["average"] = int( ( whereIs12[1] + whereIs12[-1] ) *0.5)
			whereIs12["active"]  = True


		# check if at left or right limit
		stop 	 = getPinValue("pin_sensor0")
		if stop == 1 and i > force: 
			print "stop", stop, whereIs12
			return iSteps

		iSteps += 1
		lStep += direction
		if lStep > nStepsInSequence: lStep = 1
		if lStep < 1: 				 lStep = nStepsInSequence

		if motorType.find("DRV8834") >-1:
			makeStepDRV8834(direction)
		else:
			makeStep(lStep)

	 	lastStep = lStep
		time.sleep(stayOn)
	#if speed < 100 or stayOn > 0.5: setOFF()
	return iSteps

# ------------------    ------------------ 
def testIfMove( waitBetweenSteps, nextStep ):
	global maxStepsUsed, startSteps
	global speed
	global t0
	global printON
	global totalSteps
	global hour, minute, second
	global secSinMidnit, hour12, secSinMidnit2	
	global rewindDone


	lasttotalSteps = totalSteps
	nextTotalSteps 	= min( int( secSinMidnit2 / waitBetweenSteps), maxStepsUsed )
	if nextTotalSteps != totalSteps:
		nextStep    = nextTotalSteps - totalSteps 
		totalSteps += nextStep

		if nextStep <0:	dir = -1
		else:			dir =  1

		if printON: print "secSinMidnit 2 ", "%.2f"%secSinMidnit, "H",hour, "M",minute, "S",second, "dt %.5f"%(time.time()-t0), "nstep",nextStep, "totSteps",totalSteps

		if nextStep != 0: 
			if speed > 10 or nextStep >5: stayOn =0.001
			else:		                  stayOn =0.01
			if lasttotalSteps < 10: force = 10 
			else:					force = 0
			#print "dir, nextStep", dir, nextStep
			move(stayOn, int( abs(nextStep) ), dir, force = force)
			if speed == 1 and nextStep ==1:
				setMotorSleep()
			setColor()

		#saveTime(secSinMidnit)
		rewindDone = True
		t0=time.time()
	return   nextStep


# ------------------    ------------------ 
def testIfRewind( nextStep ):
	global maxStepsUsed, startSteps
	global t0
	global printON
	global totalSteps
	global hour, minute, second
	global secSinMidnit, hour12, secSinMidnit2	
	global rewindDone


	if hour12 > 6: rewindDone = False
	if (hour12 < 3 and  not rewindDone) or nextStep ==0:
		if printON: print "rewind ", "%.2f"%secSinMidnit, "H",hour, "M",minute, "S",second, "dt %.5f"%(time.time()-t0), "nstep",nextStep, "totSteps",totalSteps
		move (0.001,maxStepsUsed,-1, force = 30 )
		rewindDone = True
		totalSteps = 0
		t0=time.time()
	totalSteps = max(0, min(totalSteps, maxStepsUsed) )

	return 



# ------------------    ------------------ 
def findLeftRight():
	global maxStepsUsed,stepsIn360
	global printON
	global waitBetweenSteps, secondsTotalInDay, maxStepsUsed 
	global amPM1224
	global whereIs12

	time.sleep(0.3)

	stayOn = 0.001
	if stepsIn360 < 1000:
		stayOn =0.001

	maxSteps = int(max(stepsIn360*1.001,stepsIn360+2))



	# check if we start at 0 left or right
	if getPinValue("pin_sensor0") ==1:
		trySteps = int(stepsIn360 / 50)
		steps = move(stayOn, trySteps , -1, force=trySteps)
		time.sleep(0.1)
		if steps != trySteps:
			print "NOT ok tried %d  -1 steps, we were right of 0 "%trySteps
			time.sleep(0.1)
			steps = move(stayOn, trySteps*2 , 1, force=trySteps*2)
			if steps == trySteps*2:
				print "ok tried %dsteps right"%(trySteps*2)
			else:
				print "??"
			time.sleep(0.1)
		else:
			print "ok tried %d  1 , we were left of 0 , move a little further away"%(trySteps*3)
			steps = move(stayOn, trySteps*3, -1, force=0)
			

	# must pass 12 , if not rewind
	rightLimit = move(stayOn, maxSteps , 1, force=20)
	if whereIs12[1] ==-1:
		print "not passed 12 at right turn"
		time.sleep(0.1)
		xx = move(stayOn, maxSteps , -1, force=50)
		if whereIs12[-1] == -1:
			print "not passed 12 at left,  turn do 10% left"
			xx = move(stayOn, int(maxSteps*0.1), -1, force=10)
		#now do full circle twice
		time.sleep(0.1)
		rightLimit  = move(stayOn, maxSteps ,  1, force=10)
	else:
		print "LR passed 12 at right turn "
		

	time.sleep(0.1)
	leftLimit  = move(stayOn, maxSteps , -1, force=20)
	time.sleep(0.1)
	rightLimit2 = move(stayOn, maxSteps ,  1, force=10)
	time.sleep(0.1)
	leftLimit2 = move(stayOn, maxSteps  , -1, force=20)
	time.sleep(0.2)
	
	print "whereIs12", whereIs12

	
	if printON: print "rightLimit",rightLimit,rightLimit2, "leftLimit",leftLimit,leftLimit2, " out of ",stepsIn360
	leftLimit = int((leftLimit+leftLimit2) *0.5)
	if abs(rightLimit - leftLimit) > stepsIn360:
		blinkLetters(["S","O","S"])

	time.sleep(0.1)
	#leftLimit = move(0.001, rightLimit/2 , -1)

	maxStepsUsed  = max(1,int((leftLimit+leftLimit2)*0.5))

	if amPM1224 =="24":	waitBetweenSteps 	= secondsTotalInDay     / maxStepsUsed 
	else: 				waitBetweenSteps 	= secondsTotalInHalfDay / maxStepsUsed 


	return 




# ########################################
# #########     beeps & blinks  ##########
# ########################################

def addToBeepBlinkQueue(text =[], color=[1,1,1], sound=1, stop = False, end=False, restore = True):
	global beepBlinkThread, stopBlinkBeep


	if stop: 
		stopBlinkBeep =True
		time.sleep(1)
		print" clear queue bf " ,beepBlinkThread["queue"].qsize() 
		beepBlinkThread["queue"].queue.clear()
		print" clear queue af",beepBlinkThread["queue"].qsize() 
		stopBlinkBeep =True
		return 

	if end: 
		stopBlinkBeep =True
		time.sleep(1)
		print" clear queue bf " ,beepBlinkThread["queue"].qsize() 
		beepBlinkThread["queue"].queue.clear()
		print" clear queue af",beepBlinkThread["queue"].qsize() 
		beepBlinkThread["thread"].join()
		return 

	add ={}
	if beepBlinkThread["beep"]    : add["beep"]  = sound
	if beepBlinkThread["color"]   : add["color"] = color
	add["text"]    = text
	add["restore"] = restore
	stopBlinkBeep  = False
	beepBlinkThread["queue"].put(add) 


def beepBlinkQueue():
	global beepBlinkThread, stopBlinkBeep

	while True:
		while not beepBlinkThread["queue"].empty():
			#print" checking queue size", actionQueue[devId].qsize() 
			action = beepBlinkThread["queue"].get()
			doBlinkBeep(action) 
			if beepBlinkThread["end"]:
				sys.exit()
			if stopBlinkBeep: break
		if LastHourColorSetToRemember !=[]:
			setColor( blink=0, color = LastHourColorSetToRemember, force = True)
		if beepBlinkThread["end"]:
			sys.exit()
		time.sleep(1)
	sys.exit()



# ########################################
# #########     LED  funtions ############
# ########################################

def doBlinkBeep(action):
	global stopBlinkBeep
	stopBlinkBeep = False
	if "text" not in action: return 
	blinkLetters(action["text"], [1,1,1], action["beep"])

# ------------------    ------------------ 
def setColor( blink=0, color = [1.,1.,1.], beep=-1, force = False):
	global colPWM, LastHourColorSet, secSinMidnit, LastHourColorSetToRemember
	global gpiopinSET

	lastC = LastHourColorSet

	if stopBlinkBeep: return 
	if blink !=0 : 
		for p in range(len(gpiopinSET["pin_rgbLED"])):
			pin = gpiopinSET["pin_rgbLED"][p]
			if  blink ==1: 
				if color[p] >= 0:
					colPWM[pin].start( int(getIntensity(100)*color[p]))	
			elif blink == -1: 
				colPWM[pin].start( getIntensity(0) )	
		if beepPWM !="":
			if  blink == 1: 
				if beep >= 0 : beepPWM.start( int(beep *100) )	
			else:			   beepPWM.start( 0 )	

		LastHourColorSet = -1


	else:
		if abs(secSinMidnit-lastC) >10 or force:
			cm = timeToColor(secSinMidnit)
			for p in range(len(gpiopinSET["pin_rgbLED"])):
				pin = gpiopinSET["pin_rgbLED"][p]
				#print "int", p, getIntensity(cm[p]) 
				colPWM[pin].start( getIntensity(cm[p])*color[p] )	
				LastHourColorSet = secSinMidnit
				LastHourColorSetToRemember = color

# ------------------    ------------------ 
def getIntensity(intens):
	global  intensity
	retV= int( min( intensity["Max"], max(intensity["Min"],float(intens)*(intensity["Mult"]/100.) ) ) )
	#print  "intens", retV
	return retV


# ------------------    ------------------ 
def testIfBlink( ):
	global speed, blinkHour, hour
	if speed ==1:
		if  second%60 < 20 and blinkHour != hour:
			blinkHour = hour
			addToBeepBlinkQueue(text =["o","n"], color=[1,1,1], sound=1, stop = False, end=False, restore = True)
	return 



def blinkLetters(letters, color, beep):
	global morseCode
	global longBlink, shortBlink, breakBlink
	global stopBlinkBeep
	for l in letters:
		if l in morseCode:
			for sig in morseCode[l]:
				if sig ==1:	blink(longBlink,  breakBlink, 1, color, beep)
				else:   	blink(shortBlink, breakBlink, 1, color, beep)
			time.sleep(breakBlink)
	return

def blink(on, off, n, color, beep):
	global stopBlinkBeep
	for i in range(n):
		if stopBlinkBeep: return 
		setColor(blink= 1, color=color, beep=beep)
		time.sleep(on)	
		if stopBlinkBeep: return 
		setColor(blink=-1, color=color, beep=beep)
		time.sleep(off)	
	return 


def timeToColor(tt):
	times = [   0, 		   4*60*60,	   8*60*60,		11*60*60,	  13*60*60,		 16*60*60,	20*60*60,	 24*60*60]
	rgb   = [ [20,20,20], [20,20,20], [80,30,30], [100,100,100], [100,100,100], [50,50,50], [80,30,30], [20,20,20] ]
	rgbout= rgb[0]
	for ii in range(1,len(times)):
		if tt > times[ii]: continue
		dt = (tt-times[ii-1])/(times[ii]-times[ii-1]) 
		for rr in range(3):
			rgbout[rr] =  dt * (rgb[ii][rr]-rgb[ii-1][rr])  +  rgb[ii-1][rr]
		break
	return rgbout


# ########################################
# #########   time   funtions ############
# ########################################
# ------------------    ------------------ 
def getTime():
	global speed, amPM1224
	global hour, minute, second
	global secSinMidnit, hour12, secSinMidnit2	

	today = datetime.date.today()
	secSinMidnit = (time.time() - time.mktime(today.timetuple()))*speed
	secSinMidnit = secSinMidnit %(secondsTotalInDay)
	hour   = int( secSinMidnit/(60*60) )
	minute = int( (secSinMidnit - hour*60*60) /60 )
	second = int( secSinMidnit - hour*60*60 - minute*60)
	if amPM1224 == "12": 
		hour12 = hour%12
		secSinMidnit2 = secSinMidnit%secondsTotalInHalfDay
	elif amPM1224 == "24": 
		hour12 = hour
		secSinMidnit2  =secSinMidnit
	else: 
		hour12 = hour
		secSinMidnit2  =secSinMidnit
	return 

# ------------------    ------------------ 
def getamPM():
	val = getPinValue("pin_amPM1224")
	if val == 1:
		return "12"
	elif val == 0:
		return "24"
	return "error"

# ------------------    ------------------ 
def testForAmPM():
	global amPM1224
	val = getamPM()
	if   val == "12":
		#print "pin_amPM1224 on"
		if amPM1224 =="24":
			getTime()
			findLeftRight()
		amPM1224 = "12"
	elif val == "24":
		if amPM1224 =="12":
			getTime()
			findLeftRight()
		amPM1224 = "24"



# ########################################
# #########    IO    funtions ############
# ########################################
# ------------------    ------------------ 
def getManualParams( sleep ):

	#sleep = testleftRightON(sleep)
	#testIfRestart()

	sleep = testIfIntensityOn(sleep)

	testForAmPM()

	testForWebAdhoc()

	isFault = testForFault()

	return sleep

# ------------------    ------------------ 
def testForWebAdhoc():
	global webAdhocLastOff, webAdhoc
	global gpiopinSET
	val  = getPinValue("pin_webAdhoc")
	if val == 1 and time.time() - webAdhocLastOff >10:
		if not webAdhoc:
			print "pin_webAdhoc on"
			startAdhocWeb()
			webAdhoc = True
	
	if val == 0:
		webAdhocLastOff = time.time()
		if webAdhoc:
			print "pin_webAdhoc off"
			stopAdhocWeb()
			webAdhoc = False
# ------------------    ------------------ 
def testForRestart():
	global RestartLastOff
	val  = getPinValue("pin_Reset")
	if val == 1 and time.time() - RestartLastOff >3:
		if not RestartLastOff:
			print "restart requested"
		time.sleep(10)
		U.restartMyself(param=" restart requested", reason="",doPrint=True)
	
	if val == 0:
		RestartLastOff = time.time()

# ------------------    ------------------ 
def testForFault():
	global gpiopinSET
	if motorType.find("DRV8834") == -1: return False

	val  = getPinValue("pin_Fault")
	if   val == 0:
			print "fault indicator ON"
			return True
	elif val == 1:
			return False


# ------------------    ------------------ 
def testleftRightON(sleep):
	global intensity
	global stepsIn360
	leftRightON 	= getPinValue("pin_leftRight")
	up				= getPinValue("pin_Up")
	down			= getPinValue("pin_Dn")
	nPress = time.time()

	stayOn = 0.001
	if  leftRightON:
		while getPinValue("pin_Up") ==1:
				#print "move L"
				move (stayOn,int(nSteps),-1, force=1000)
				if time.time() - nPress >2:
					nSteps = min(stepsIn360/10, nSteps*1.5)
					stayOn = 0.001
				sleep = min(0.0001, sleep)

		while getPinValue("pin_Dn") ==1:
				#print "move R"
				move (stayOn,int(nSteps),1, force=1000)
				if time.time() - nPress >2:
					nSteps = min(stepsIn360/10, nSteps*1.5)
					stayOn = 0.001
				sleep = min(0.0001, sleep)
	return sleep

# ------------------    ------------------ 
def testIfIntensityOn(sleep):
	global intensity
	intensityON 	= getPinValue("pin_intensity")
	up				= getPinValue("pin_Up")
	down			= getPinValue("pin_Dn")
	nPress = time.time()

	if intensityON:
		while getPinValue("pin_Up") ==1:
				#print "pin_IntensityUp"
				nSteps = min(500, nSteps*1.5)
				intensity["Mult"] = min(1000,intensity["Mult"]+nSteps)
				setColor( force = True)
				time.sleep(0.3)
				sleep = min(0.0001, sleep)

		while getPinValue("pin_Dn")==1:
				#print "pin_IntensityDn"
				nSteps = min(500, nSteps*1.5)
				intensity["Mult"] = max(5,intensity["Mult"]-nSteps)
				setColor( force = True)
				time.sleep(0.3)
				sleep = min(0.0001, sleep)
	return sleep



# ########################################
# #########    web   funtions ############
# ########################################

# ------------------    ------------------ 
def startAdhocWeb():
	return

# ------------------    ------------------ 
def stopAdhocWeb():
	return


 #######################################
# #########       main        ##########
# ######################################

global clockDict, clockLightSet, useRTC
global sensor, output, inpRaw
global oldRaw,	lastRead, inp
global timeZones, timeZone
global doReadParameters
global networkIndicatorON
global lastStep, colPWM,  LastHourColorSet, beepPWM
global intensity
global maxStepsUsed, startSteps, stepsIn360, nStepsInSequence
global speed, amPM1224, motorType, adhocWeb
global gpiopinSET, SeqCoils
global blinkHour
global t0
global printON
global totalSteps
global hour, minute, second
global secSinMidnit, hour12, secSinMidnit2	
global webAdhocLastOff, webAdhoc
global rewindDone
global longBlink, shortBlink, breakBlink
global morseCode
global whereIs12
global minStayOn
global lastDirection
global isDisabled, isSleep
global isFault
global RestartLastOff 
global clockDictLast
global beepBlinkThread, stopBlinkBeep


morseCode= {"A":[0,1], 		"B":[1,0,0,0],	 "C":[1,0,1,0], "D":[1,0,0], 	"E":[0], 		"F":[0,0,1,0], 	"G":[1,1,0],	"H":[0,0,0,0], 	"I":[0,0],
			"J":[0,1,1,1], 	"K":[1,0,1], 	"L":[0,1,0,0], 	"M":[1,1], 		"N":[1,0], 		"O":[1,1,1], 	"P":[0,1,1,0],	"Q":[1,1,0,1], 	"R":[0,1,0],
			"S":[0,0,0], 	"T":[1], 		"U":[0,0,1], 	"V":[0,0,0,1], 	"W":[0,1,1], "X":[1,0,0,1], 	"Y":[1,0,1,1], 	"Z":[1,1,0,0],
			"0":[1,1,1,1,1], "1":[0,1,1,1,1], "2":[0,0,1,1,1], "3":[0,0,0,1,1], "4":[0,0,0,0,1], "5":[0,0,0,0,0], "6":[1,0,0,0,0], "7":[1,1,0,0,0], "8":[1,1,1,0,0], "9":[1,1,1,1,0],
			"s":[0], # one short
			"l":[1], # one long
			"b":[0,0,0,1]}  # beethoven ddd DAAA

longBlink			  	= 0.6
shortBlink			  	= 0.2
breakBlink			  	= 0.5

isFault				  	= False

isDisabled			  	= True
isSleep				  	= True
lastDirection		  	= 0
webAdhocLastOff		  	= time.time() + 100
webAdhoc			  	= False
# constants 
adhocWebLast		  	= 0
motorType			  	= "xx"
startSteps			  	= 0
secondsTotalInDay     	= 60.*60.*24.
secondsTotalInHalfDay 	= 60.*60.*12
intensity             	= {}
intensity["Mult"]     	= 100.
intensity["Max"]      	= 100.
intensity["Min"]      	= 10.
amPM1224			  	= "24"
speed				  	= 1
RestartLastOff 		  	= time.time()+100

lastStep              	= 0
LastHourColorSet      	= -1
nightMode				= 0
doReadParameters		= True
dd						= datetime.datetime.now()
oldRaw					= ""
lastRead				= 0
inpRaw					= ""
inp						= ""
debug					= 5
loopCount				= 0
sensor					= G.program
lastGPIOreset	 		= 0
G.lastAliveSend	 		= time.time() -1000
loopC			 		= 0
lastShutDownTest 		= -1
lastRESETTest	 		= -1
printON 				= True
totalSteps 				= 0
t0						= time.time()
blinkHour				= -1
rewindDone 				= True
nextStep 				= 1
whereIs12 				= {-1:-1, 1:-1, "average":-1, "active":False}
clockDictLast			= {}
LastHourColorSetToRemember =[]

myPID		= str(os.getpid())
U.killOldPgm(myPID,G.program+".py")# kill old instances of myself if they are still running

setgpiopinSET()

setupTimeZones()
#print "current tz:", currTZ,JulDelta,JanDelta,NowDelta, timeZones[currTZ+12], timeZones

if readParams() ==3:
		U.toLog(-1," parameters not defined", doPrint=True)
		U.checkParametersFile("parameters-DEFAULT-sunDial", force = True)
		time.sleep(20)
		U.restartMyself(param=" bad parameters read", reason="",doPrint=True)

setMotorOFF()

U.echoLastAlive(G.program)


print "gpiopinSET",gpiopinSET

try:    speed = int(sys.argv[1])
except: pass

stopBlinkBeep	= False
beepBlinkThread = {"color":True, "beep":True,"stop":False, "end":False, "queue": Queue.Queue(), "thread": threading.Thread(name=u'beepBlinkQueue', target=beepBlinkQueue, args=())}	
beepBlinkThread["thread"].start()



amPM1224 = getamPM()

### here it starts 
getTime()

setColor(force=True)

addToBeepBlinkQueue(text=["b","b","b","b","b","b"])
#blinkLetters(["S","T","A","R","T"])
#beepLetters(["S","T","A","R","T"])
#time.sleep(3)
#blinkLetters(["S","O","S"])

findLeftRight()

sleepDefault = waitBetweenSteps/5*speed


print "clock starting;   waitBetweenSteps", waitBetweenSteps, "speed", speed, "totalSteps",totalSteps,"sleepDefault", sleepDefault,"amPM1224",amPM1224,"secSinMidnit2",secSinMidnit2
print "intensity", intensity

nextStep = 1

while True:
			
	getTime()
	nextStep = testIfMove( waitBetweenSteps, nextStep )
	testIfRewind( nextStep )
	sleep = getManualParams( sleepDefault )
	testIfBlink()
	time.sleep(sleep)

	
stopBlinkBeep	= True
time.sleep(1)
beepBlinkThread["thread"].join


		

