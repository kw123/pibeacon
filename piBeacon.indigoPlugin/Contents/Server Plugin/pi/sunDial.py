#!/usr/bin/env python
# -*- coding: utf-8 -*-
# by Karl Wachs
# feb 5 2016
# version 0.9 
##
###
import RPi.GPIO as GPIO
import	sys, os, time, json, datetime,subprocess,copy
import math


sys.path.append(os.getcwd())
import	piBeaconUtils	as U
import	piBeaconGlobals as G
G.program = "sunDial"
import	RPi.GPIO as GPIO


GPIO.setmode(GPIO.BCM)
GPIO.setwarnings(False)


# ===========================================================================
# read params
# ===========================================================================

#################################		 
def readParams():
	global sensor, output, inpRaw, inp, DEVID,useRTC
	global speed
	global lastCl, timeZone, currTZ
	global oldRaw, lastRead
	global doReadParameters
	global gpiopinSET

	try:

		if not doReadParameters: return
		changed =0
		inpLast= inp
		inp,inpRaw,lastRead2 = U.doRead(lastTimeStamp=lastRead)

		if inp == "": 
			inp = inpLast
			return changed
			
		if lastRead2 == lastRead: return changed
		lastRead  = lastRead2
		if inpRaw == "error":
			U.checkParametersFile("parameters-DEFAULT-clock", force = True)
		if inpRaw == oldRaw: return changed
		oldRaw	   = inpRaw
		U.getGlobalParams(inp)
		 
		if "debugRPI"				in inp:	 G.debug=		  int(inp["debugRPI"]["debugRPIOUTPUT"])
		if "useRTC"					in inp:	 useRTC=			 (inp["useRTC"])
		if "output"					in inp:	 output=			 (inp["output"])
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
			DEVID = devId
			clockDict= clock[devId][0]
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
				
			if "intensityMult"		in clockDict:  intensity["Mult"]				=  float(clockDict["intensityMult"])
			if "intensityMax"		in clockDict:  intensity["Max"]					=  float(clockDict["intensityMax"])
			if "intensityMin"		in clockDict:  intensity["Min"]					=  float(clockDict["intensityMin"])
			if "speed"			 	in clockDict:  speed		   					=  float(clockDict["speed"])
 
			if "pin_Coil1"			 in clockDict: gpiopinSET["pin_Coil1"]			 =	int(clockDict["pin_Coil1"])
			if "pin_Coil2"			 in clockDict: gpiopinSET["pin_Coil2"]			 =	int(clockDict["pin_Coil2"])
			if "pin_Coil3"			 in clockDict: gpiopinSET["pin_Coil3"]			 =	int(clockDict["pin_Coil3"])
			if "pin_Coil4"			 in clockDict: gpiopinSET["pin_Coil4"]			 =	int(clockDict["pin_Coil4"])
			if "pin_LeftMove"		 in clockDict: gpiopinSET["pin_LeftMove"]		 =	int(clockDict["pin_LeftMove"])
			if "pin_RightMove"		 in clockDict: gpiopinSET["pin_RightMove"]		 =	int(clockDict["pin_RightMove"])
			if "pin_IntensityUp"	 in clockDict: gpiopinSET["pin_IntensityUp"]	 =	int(clockDict["pin_IntensityUp"])
			if "pin_IntensityDn"	 in clockDict: gpiopinSET["pin_IntensityDn"]	 =	int(clockDict["pin_IntensityDn"])
			if "pin_LeftLimit"		 in clockDict: gpiopinSET["pin_LeftLimit"]		 =	int(clockDict["pin_LeftLimit"])
			if "pin_RightLimit"		 in clockDict: gpiopinSET["pin_RightLimit"]		 =	int(clockDict["pin_RightLimit"])
			if "pin_rgbLED_R"		 in clockDict: gpiopinSET["pin_rgbLED"][0]		 =	int(clockDict["pin_rgbLED_R"])
			if "pin_rgbLED_G"		 in clockDict: gpiopinSET["pin_rgbLED"][1]		 =	int(clockDict["pin_rgbLED_G"])
			if "pin_rgbLED_B"		 in clockDict: gpiopinSET["pin_rgbLED"][2]		 =	int(clockDict["pin_rgbLED_B"])


			## print clockDict
			break
		return changed

	except	Exception, e:
		print  u"in Line '%s' has error='%s'" % (sys.exc_traceback.tb_lineno, e)
		U.toLog(-1, u"in Line '%s' has error='%s'" % (sys.exc_traceback.tb_lineno, e))
		time.sleep(10)
		return 3




# ------------------    ------------------ 
def setOFF():
	global SeqCoils
	setStep(SeqCoils[0])

 
# ------------------    ------------------ 
def setStep(values):
	global gpiopinSET
	## print "setStep", values
	GPIO.output(gpiopinSET["pin_Coil1"], values[0])
	GPIO.output(gpiopinSET["pin_Coil2"], values[1])
	GPIO.output(gpiopinSET["pin_Coil3"], values[2])
	GPIO.output(gpiopinSET["pin_Coil4"], values[3])

 
# ------------------    ------------------ 
def move(delay, steps, direction):
	global lastStep
	global gpiopinSET
	global SeqCoils


	ii = lastStep
	#print "steps", steps,  direction, delay, lastStep
	iSteps= 0
	for i in range(steps):
		# check if at left or right limit
		if direction == 1 and  GPIO.input(gpiopinSET["pin_RightLimit"]) == 0: return iSteps
		if direction ==-1 and  GPIO.input(gpiopinSET["pin_LeftLimit"])  == 0:  return iSteps
		iSteps += 1
		ii += direction
		if ii > 8: ii=1
		if ii < 1: ii=8
		setStep(SeqCoils[ii])
	 	lastStep = ii
		time.sleep(delay)
	if speed < 50: setOFF()
	return iSteps


# ------------------    ------------------ 
def setColor(hour,blink=0, force = False):
	global colPWM, colorMap, LastHourColorSet
	global gpiopinSET

	lastC = LastHourColorSet
	for p in range(len(gpiopinSET["pin_rgbLED"])):
		pin = gpiopinSET["pin_rgbLED"][p]
		if blink   ==1: 
			colPWM[pin].start( getIntensity(100) )	
			LastHourColorSet = -1
		elif blink ==-1: 
			colPWM[pin].start( getIntensity(0) )	
			LastHourColorSet = -1
		else:
			if lastC != hour or force:
				colPWM[pin].start( getIntensity(colorMap[hour][p]) )	
				LastHourColorSet = hour


# ------------------    ------------------ 
def getIntensity(intens):
	global pin_Coil, intensity
	retV= int( min( intensity["Max"], max(intensity["Min"],float(intens)*(intensity["Mult"]/100.) ) ) )
	#print  "intens", retV
	return retV


# ------------------    ------------------ 
def getTime( HHAmPM):
	global speed
	global hour, minute, second

	today = datetime.date.today()
	secSinMidnit = (time.time() - time.mktime(today.timetuple()))*speed
	secSinMidnit = secSinMidnit %(secondsTotalInDay)
	hour   = int( secSinMidnit/(60*60) )
	minute = int( (secSinMidnit - hour*60*60) /60 )
	second = int( secSinMidnit - hour*60*60 - minute*60)
	if HHAmPM: 
		hour12 = hour%12
		secSinMidnit2 = secSinMidnit%secondsTotalInHalfDay
	else: 
		hour12 = hour
		secSinMidnit2  =secSinMidnit

	return secSinMidnit, hour12, secSinMidnit2


# ------------------    ------------------ 
def getManualParams( sleep ):
	global intensity
	global hour, minute, second
	global gpiopinSET


	nSteps = 1
	nPress = time.time()
	delay = 0.02
	while GPIO.input(gpiopinSET["pin_LeftMove"]) == 0:
		move (delay,int(nSteps),-1)
		if time.time() - nPress >2:
			nSteps = min(500, nSteps*1.5)
			delay = 0.001
		sleep = min(0.0001, sleep)

	while GPIO.input(gpiopinSET["pin_RightMove"]) == 0:
		move (delay,int(nSteps),1)
		if time.time() - nPress >2:
			nSteps = min(500, nSteps*1.5)
			delay = 0.001
		sleep = min(0.0001, sleep)

	while GPIO.input(gpiopinSET["pin_IntensityUp"]) == 0:
		nSteps = min(500, nSteps*1.5)
		intensity["Mult"] = min(1000,intensity["Mult"]+nSteps)
		setColor(hour, force = True)
		time.sleep(0.5)
		sleep = min(0.0001, sleep)

	while GPIO.input(gpiopinSET["pin_IntensityDn"]) == 0:
		nSteps = min(500, nSteps*1.5)
		intensity["Mult"] = max(5,intensity["Mult"]-nSteps)
		setColor(hour, force = True)
		time.sleep(0.5)
		sleep = min(0.0001, sleep)

	return sleep


# ------------------    ------------------ 
def testIfBlink( sleep, waitBetweenSteps ):
	global speed, blinkHour
	global hour, minute, second
	if speed ==1:
		if  second%60 < 20 and blinkHour != hour:
			blinkHour = hour
			setColor(hour,blink=-1)
			time.sleep(0.5)	
			setColor(hour,blink=1)
			time.sleep(0.5)	
			setColor(hour,blink=-1)
			time.sleep(0.5)	
			setColor(hour)
			sleep = max (0.001, waitBetweenSteps/5*speed-3 )
	time.sleep(min(0.5, sleep ))
	return 


# ------------------    ------------------ 
def testIfMove( secSinMidnit, secSinMidnit2, waitBetweenSteps, nextStep, rewindDone ):
	global maxStepsUsed, startSteps
	global speed
	global t0
	global printON
	global totalSteps
	global hour, minute, second


	nextTotalSteps 	= min( int( secSinMidnit2 / waitBetweenSteps), maxStepsUsed )
	if nextTotalSteps != totalSteps:
		nextStep    = nextTotalSteps - totalSteps 
		totalSteps += nextStep

		if nextStep <0:	dir = -1
		else:			dir =  1

		if printON: print "secSinMidnit", "%.2f"%secSinMidnit, "H",hour, "M",minute, "S",second, "dt %.5f"%(time.time()-t0), "nstep",nextStep, "totSteps",totalSteps

		if nextStep != 0: 
			move(0.001, int( abs(nextStep) ), dir)
			setColor(hour)

		#saveTime(secSinMidnit)
		rewindDone = True
		t0=time.time()
	return   nextStep, rewindDone


# ------------------    ------------------ 
def testIfRewind( secSinMidnit, hour12, nextStep, rewindDone ):
	global maxStepsUsed, startSteps
	global t0
	global printON
	global totalSteps
	global hour, minute, second


	if hour12 > 6: rewindDone = False
	if (hour12 < 3 and  not rewindDone) or nextStep ==0:
		if printON: print "rewind ", "%.2f"%secSinMidnit, "H",hour, "M",minute, "S",second, "dt %.5f"%(time.time()-t0), "nstep",nextStep, "totSteps",totalSteps
		move (0.001,maxStepsUsed,-1)
		rewindDone = True
		totalSteps = 0
		t0=time.time()
	totalSteps = max(0, min(totalSteps, maxStepsUsed) )

	return rewindDone



# ------------------    ------------------ 
def findLeftRight():
	global maxStepsUsed
	global printON

	rightLimit = move(0.001, 5000 ,  1)
	time.sleep(0.2)
	leftLimit = move(0.001, 5000 , -1)
	
	if printON: print "rightLimit",rightLimit, "leftLimit",leftLimit

	time.sleep(0.1)
	#leftLimit = move(0.001, rightLimit/2 , -1)

	maxStepsUsed 	 = leftLimit

	return 


# ------------------    ------------------ 
###################################################################################
###################################################################################
def clock(HHAmPM):
	global speed
	global blinkHour
	global t0
	global printON
	global totalSteps
	global hour, minute, second

	printON 	= True
	totalSteps 	= 0
	t0			= time.time()
	blinkHour	= -1
	rewindDone 	= True
	nextStep 	= 1

	# reset motor to off
	setOFF()

	secSinMidnit, hour12, secSinMidnit2	= getTime(HHAmPM)

	findLeftRight()

	if not HHAmPM:	waitBetweenSteps 	= secondsTotalInDay     / maxStepsUsed 
	else: 			waitBetweenSteps 	= secondsTotalInHalfDay / maxStepsUsed 

	sleepDefault = waitBetweenSteps/5*speed


	print "clock starting;   waitBetweenSteps", waitBetweenSteps, "speed", speed, "totalSteps",totalSteps,"sleepDefault", sleepDefault,"HHAmPM",HHAmPM,"secSinMidnit2",secSinMidnit2

	while True:
				
		secSinMidnit, hour12, secSinMidnit2	= getTime( HHAmPM )

		nextStep, rewindDone = testIfMove( secSinMidnit, secSinMidnit2, waitBetweenSteps,  nextStep, rewindDone )
		rewindDone = testIfRewind( secSinMidnit, hour12, nextStep, rewindDone )
		sleep = getManualParams( sleepDefault )
		testIfBlink( sleep, waitBetweenSteps )

	return

###################################################################################
###################################################################################

	
#################################
#################################
#################################
#################################
global clockDict, clockLightSet, enableupDown,enableHH,enableMM,enableDD,enableDDonOFF, enableTZset,enablePattern,enableLight,currHH, currMM, currDD, currTZ,  useRTC, newDate, resetGPIO, lastButtonTime
global sensor, output, inpRaw
global oldRaw,	lastRead, inp
global timeZones, timeZone
global doReadParameters
global networkIndicatorON
global lastStep, colPWM,  colorMap, LastHourColorSet
global intensity
global maxStepsUsed, startSteps
global speed
global gpiopinSET, SeqCoils


# constants 
stepsIn360            = 64*64
maxStepsUsed          = 4000
startSteps			  = 0
secondsTotalInDay     = 60.*60.*24.
secondsTotalInHalfDay = 60.*60.*12
intensity             = {}
intensity["Mult"]     = 1.
intensity["Max "]     = 100
intensity["Min"]      = 30

lastStep              = 0
LastHourColorSet      = -1

### GPIO pins ########
gpiopinSET					  = {}
gpiopinSET["pin_Coil1"]       = 21 # blue
gpiopinSET["pin_Coil2"]       = 20 # pink
gpiopinSET["pin_Coil3"]       = 16 # yellow
gpiopinSET["pin_Coil4"]       = 12 # orange

gpiopinSET["pin_rgbLED"]	  = [13,26,19] # r g b pins

gpiopinSET["pin_LeftMove"]    = 18
gpiopinSET["pin_RightMove"]   = 23

gpiopinSET["pin_IntensityUp"] = 24
gpiopinSET["pin_IntensityDn"] = 25

gpiopinSET["pin_LeftLimit"]   = 27
gpiopinSET["pin_RightLimit"]  = 22




 
colorMap=[]
#				Red	   Blue	green
colorMap.append([ 15,  15  ,  15] )# 0
colorMap.append([ 15,  15  ,  15] )# 1
colorMap.append([ 15,  15  ,  15] )# 2
colorMap.append([ 15,  15  ,  15] )# 3
colorMap.append([ 15,  15  ,  15] )# 4
colorMap.append([ 20,  20  ,  20] )# 5
colorMap.append([ 60,  20  ,  20] )# 6 
colorMap.append([100,  20  ,  20] )# 7
colorMap.append([100,  20  ,  20] )# 8
colorMap.append([100,  50  ,  50] )# 9
colorMap.append([ 80,  80  ,  80] )# 10
colorMap.append([ 80, 100  ,  90] )# 11
colorMap.append([ 80, 100  , 100] )# 12
colorMap.append([ 80, 100  ,  90] )# 13
colorMap.append([ 80,  90  ,  80] )# 14
colorMap.append([100,  50  ,  50] )# 15
colorMap.append([100,  20  ,  20] )# 16
colorMap.append([100,  15  ,  15] )# 17
colorMap.append([100,  10  ,  10] )# 18
colorMap.append([ 60,  10  ,  10] )# 19
colorMap.append([ 30,  10  ,  10] )# 20
colorMap.append([ 15,  15  ,  15] )# 21
colorMap.append([ 15,  15  ,  15] )# 22
colorMap.append([ 15,  15  ,  15] )# 23


#  coil current SeqCoilsuences
SeqCoils = [[],[],[],[],[],[],[],[],[]]
#		  B  p  y  o
SeqCoils[0] = [0, 0, 0, 0]  # off
SeqCoils[1] = [1, 0, 0, 1]
SeqCoils[2] = [1, 0, 0, 0]
SeqCoils[3] = [1, 1, 0, 0]
SeqCoils[4] = [0, 1, 0, 0]
SeqCoils[5] = [0, 1, 1, 0]
SeqCoils[6] = [0, 0, 1, 0]
SeqCoils[7] = [0, 0, 1, 1]
SeqCoils[8] = [0, 0, 0, 1]





lastNeoParamsSet	= time.time()
nightMode			= 0

doReadParameters	= True
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

#print "current tz:", currTZ,JulDelta,JanDelta,NowDelta, timeZones[currTZ+12], timeZones


dd							= datetime.datetime.now()
oldRaw						= ""
lastRead					= 0
inpRaw						= ""
inp							= ""
debug						= 5
loopCount					= 0
sensor						= G.program

# check for corrupt parameters file 
U.checkParametersFile("parameters-DEFAULT-sunDial", force = False)

if readParams() ==3:
		U.toLog(-1," parameters not defined", doPrint=True)
		U.checkParametersFile("parameters-DEFAULT-sunDial", force = True)
		time.sleep(20)
		U.restartMyself(param=" bad parameters read", reason="",doPrint=True)
	

myPID		= str(os.getpid())
U.killOldPgm(myPID,G.program+".py")# kill old instances of myself if they are still running

U.echoLastAlive(G.program)

#save old wifi setting
os.system('cp /etc/network/interfaces '+G.homeDir+'interfaces-old')

	
maxWifiAdHocTime	= 25
if U.whichWifi() == "normal":
	wifiStarted = -1
	wifiStartedLastTest = 99999999999999999999.
else:
	U.resetWifi() # make sure next reboot it starts normally
	wifiStarted			= time.time()
	wifiStartedLastTest = int(time.time())
	afterAdhocWifistarted(maxWifiAdHocTime)

lastWIFITest	 = -1
		

lastGPIOreset	 = 0
G.lastAliveSend	 = time.time() -1000
loopC			 = 0
lastShutDownTest = -1
lastRESETTest	 = -1


U.testNetwork()
networkIndicatorON = -1
U.checkParametersFile("parameters-DEFAULT-sunDial")


GPIO.setup(gpiopinSET["pin_Coil1"],			GPIO.OUT)
GPIO.setup(gpiopinSET["pin_Coil2"],			GPIO.OUT)
GPIO.setup(gpiopinSET["pin_Coil3"],			GPIO.OUT)
GPIO.setup(gpiopinSET["pin_Coil4"],			GPIO.OUT)
GPIO.setup(gpiopinSET["pin_rgbLED"][0],		GPIO.OUT)
GPIO.setup(gpiopinSET["pin_rgbLED"][1],		GPIO.OUT)
GPIO.setup(gpiopinSET["pin_rgbLED"][2],		GPIO.OUT)
GPIO.setup(gpiopinSET["pin_LeftMove"],		GPIO.IN, pull_up_down=GPIO.PUD_UP)
GPIO.setup(gpiopinSET["pin_RightMove"],		GPIO.IN, pull_up_down=GPIO.PUD_UP)
GPIO.setup(gpiopinSET["pin_LeftLimit"],		GPIO.IN, pull_up_down=GPIO.PUD_UP)
GPIO.setup(gpiopinSET["pin_RightLimit"],	GPIO.IN, pull_up_down=GPIO.PUD_UP)
GPIO.setup(gpiopinSET["pin_IntensityUp"],	GPIO.IN, pull_up_down=GPIO.PUD_UP)
GPIO.setup(gpiopinSET["pin_IntensityDn"],	GPIO.IN, pull_up_down=GPIO.PUD_UP)

colPWM ={}
for pin in gpiopinSET["pin_rgbLED"]:
	colPWM[pin] = GPIO.PWM(pin, 100)

print gpiopinSET

try:    speed = int(sys.argv[1])
except: speed = 1
try:    HHAmPM = (sys.argv[2]) == "12"
except: HHAmPM = False
clock(HHAmPM)

