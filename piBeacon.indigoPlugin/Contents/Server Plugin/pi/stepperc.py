import RPi.GPIO as GPIO
import time
import datetime
import sys
global lastStep, colPWM,  colorMap, LastHourColorSet
global intensityMult, intensityMax, intensityMin
global maxStepsUsed, startSteps

GPIO.setmode(GPIO.BCM)
GPIO.setwarnings(False)

# constants 
homeDir               ="/home/pi/pibeacon/"
stepsIn360            = 64*64
maxStepsUsed          = 4000
startSteps			  = 0
secondsTotalInDay     = 60.*60.*24.
secondsTotalInHalfDay = 60.*60.*12
intensityMult         = 1.
intensityMax          = 100
intensityMin          = 30

lastStep              = 0
LastHourColorSet      = -1




### GPIO pins ########
pin_Coil1       = 21 # blue
pin_Coil2       = 20 # pink
pin_Coil3       = 16 # yellow
pin_Coil4       = 12 # orange

pin_rgbLED		= [13,26,19] # r g b pins

pin_LeftMove    = 18
pin_RightMove   = 23

pin_IntensityUp = 24
pin_IntensityDn = 25

pin_LeftLimit   = 27
pin_RightLimit  = 22


 
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


#  coil current sequences
Seq = [[],[],[],[],[],[],[],[],[]]
#		  B  p  y  o
Seq[0] = [0, 0, 0, 0]  # off
Seq[1] = [1, 0, 0, 1]
Seq[2] = [1, 0, 0, 0]
Seq[3] = [1, 1, 0, 0]
Seq[4] = [0, 1, 0, 0]
Seq[5] = [0, 1, 1, 0]
Seq[6] = [0, 0, 1, 0]
Seq[7] = [0, 0, 1, 1]
Seq[8] = [0, 0, 0, 1]


GPIO.setup(pin_Coil1,     GPIO.OUT)
GPIO.setup(pin_Coil2,     GPIO.OUT)
GPIO.setup(pin_Coil3,     GPIO.OUT)
GPIO.setup(pin_Coil4,     GPIO.OUT)
GPIO.setup(pin_rgbLED[0],     GPIO.OUT)
GPIO.setup(pin_rgbLED[1],     GPIO.OUT)
GPIO.setup(pin_rgbLED[2],     GPIO.OUT)
GPIO.setup(pin_LeftMove,    GPIO.IN, pull_up_down=GPIO.PUD_UP)
GPIO.setup(pin_RightMove,   GPIO.IN, pull_up_down=GPIO.PUD_UP)
GPIO.setup(pin_LeftLimit,   GPIO.IN, pull_up_down=GPIO.PUD_UP)
GPIO.setup(pin_RightLimit,  GPIO.IN, pull_up_down=GPIO.PUD_UP)
GPIO.setup(pin_IntensityUp, GPIO.IN, pull_up_down=GPIO.PUD_UP)
GPIO.setup(pin_IntensityDn, GPIO.IN, pull_up_down=GPIO.PUD_UP)

colPWM ={}
for pin in pin_rgbLED:
	colPWM[pin] = GPIO.PWM(pin, 100)



# ------------------    ------------------ 
def setOFF():
	setStep(Seq[0])

 
# ------------------    ------------------ 
def setStep(values):
	GPIO.output(pin_Coil1, values[0])
	GPIO.output(pin_Coil2, values[1])
	GPIO.output(pin_Coil3, values[2])
	GPIO.output(pin_Coil4, values[3])

 
# ------------------    ------------------ 
def move(delay, steps, direction):
	global lastStep
	ii = lastStep
	#print "steps", steps,  direction, delay, lastStep
	iSteps= 0
	for i in range(steps):
		# check if at left or right limit
		if direction == 1 and  GPIO.input(pin_RightLimit) == 0: return iSteps
		if direction ==-1 and  GPIO.input(pin_LeftLimit)  == 0:  return iSteps
		iSteps += 1
		ii += direction
		if ii > 8: ii=1
		if ii < 1: ii=8
		setStep(Seq[ii])
		lastStep = ii
		time.sleep(delay)
	setOFF()
	return iSteps


# ------------------    ------------------ 
def setColor(hour,blink=0):
	global colPWM, colorMap, LastHourColorSet
	lastC = LastHourColorSet
	for p in range(len(pin_rgbLED)):
		pin = pin_rgbLED[p]
		if blink   ==1: 
			colPWM[pin].start( getIntensity(100) )	
			LastHourColorSet = -1
		elif blink ==-1: 
			colPWM[pin].start( getIntensity(0) )	
			LastHourColorSet = -1
		else:
			if lastC != hour:
				colPWM[pin].start( getIntensity(colorMap[hour][p]) )	
				LastHourColorSet = hour


# ------------------    ------------------ 
def getIntensity(intensity):
	global pin_Coil, intensityMax, intensityMin
	return int( min( intensityMax, max(intensityMin,float(intensity)*intensityMult) ) )


# ------------------    ------------------ 
def getTime(speed , HHAmPM):
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

	return hour,minute,second, secSinMidnit, hour12, secSinMidnit2


# ------------------    ------------------ 
def getManualParams(speed, hour, sleep ):
	global intensityMult, intensityMax, intensityMin


	nSteps = 1
	nPress = time.time()
	delay = 0.02
	while GPIO.input(pin_LeftMove)==0:
		move (delay,int(speed*nSteps),-1)
		if time.time() - nPress >2:
			nSteps = min(500, nSteps*1.5)
			delay = 0.001
		sleep = min(0.0001, sleep)

	while GPIO.input(pin_RightMove)==0:
		move (delay,int(speed*nSteps),1)
		if time.time() - nPress >2:
			nSteps = min(500, nSteps*1.5)
			delay = 0.001
		sleep = min(0.0001, sleep)

	while GPIO.input(pin_IntensityUp)==0:
		intensityMult +=5
		setColor(hour)
		time.sleep(0.5)
		sleep = min(0.0001, sleep)

	while GPIO.input(pin_IntensityDn)==0:
		intensityMult -=5
		setColor(hour)
		time.sleep(0.5)
		sleep = min(0.0001, sleep)

	return sleep


# ------------------    ------------------ 
def testIfBlink( speed, hour, second, blinkHour, sleep, waitBetweenSteps ):
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
	return blinkHour


# ------------------    ------------------ 
def testIfMove(hour, minute, second, secSinMidnit, secSinMidnit2, waitBetweenSteps, speed, totalSteps, nextStep, t0, rewindDone ):
	global maxStepsUsed, startSteps
	nextTotalSteps 	= min( int( secSinMidnit2 / waitBetweenSteps), maxStepsUsed )
	if nextTotalSteps != totalSteps:
		nextStep    = nextTotalSteps - totalSteps 
		totalSteps += nextStep

		if nextStep <0:	dir = -1
		else:			dir =  1


		if nextStep != 0: 
			move(0.001, int( abs(nextStep) ), dir)
			setColor(hour)

		#saveTime(secSinMidnit)
		rewindDone = True
		t0=time.time()
	return  totalSteps, nextStep, t0, rewindDone


# ------------------    ------------------ 
def testIfRewind(hour, minute, second, secSinMidnit, hour12,  totalSteps, nextStep, t0, rewindDone ):
	global maxStepsUsed, startSteps

	if hour12 > 6: rewindDone = False
	if (hour12 < 3 and  not rewindDone) or nextStep ==0:
		move (0.001,maxStepsUsed,-1)
		rewindDone = True
		totalSteps = 0
		t0=time.time()
	totalSteps = max(0, min(totalSteps, maxStepsUsed) )

	return rewindDone, totalSteps, t0



# ------------------    ------------------ 
def findLeftRight():
	global maxStepsUsed

	rightLimit = move(0.001, 5000 ,  1)
	time.sleep(0.2)
	leftLimit = move(0.001, 5000 , -1)
	
	time.sleep(0.1)
	#leftLimit = move(0.001, rightLimit/2 , -1)

	maxStepsUsed 	 = leftLimit

	return  True


# ------------------    ------------------ 
###################################################################################
###################################################################################
def clock(speed, HHAmPM):

	# reset motor to off
	setOFF()

	hour, minute, second, secSinMidnit, hour12, secSinMidnit2 		= getTime(speed, HHAmPM)

	xx																= findLeftRight()

	if not HHAmPM:	waitBetweenSteps = secondsTotalInDay     / maxStepsUsed 
	else: 			waitBetweenSteps = secondsTotalInHalfDay / maxStepsUsed 

	totalSteps 														= 0
	t0																= time.time()
	blinkHour														= -1
	sleepDefault													= waitBetweenSteps/5*speed
	rewindDone 														= True
	nextStep 														= 1



	while True:
				
		hour, minute, second, secSinMidnit, hour12, secSinMidnit2	= getTime( speed=speed, HHAmPM=HHAmPM )
	
		totalSteps, nextStep, t0, rewindDone						= testIfMove( hour, minute, second, secSinMidnit, secSinMidnit2, waitBetweenSteps, speed, totalSteps, nextStep, t0, rewindDone )

		rewindDone, totalSteps, t0 									= testIfRewind( hour, minute, second, secSinMidnit, hour12, totalSteps, nextStep, t0, rewindDone )

		sleep 														= getManualParams( speed, hour, sleepDefault )

		blinkHour		  											= testIfBlink( speed, hour, second, blinkHour, sleep, waitBetweenSteps )

	return

###################################################################################
###################################################################################



try:    speed = int(sys.argv[1])
except: speed = 1
try:    HHAmPM = (sys.argv[2]) == "12"
except: HHAmPM = False
clock(speed,HHAmPM)
