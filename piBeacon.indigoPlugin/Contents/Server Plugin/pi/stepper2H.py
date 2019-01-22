import RPi.GPIO as GPIO
import time
global lastStep

GPIO.setmode(GPIO.BCM)
GPIO.setwarnings(False)

coil=[]
coil.append(21) # red
coil.append(20) # yellow
coil.append(16) # grey
coil.append(12) # green

colPWM ={}

#
Seq = []
#		  
Seq.append([0, 0, 0, 0])  # off
Seq.append([0, 0, 1, 0])
Seq.append([1, 0, 1, 0])
Seq.append([1, 0, 0, 0])
Seq.append([1, 0, 0, 1])
Seq.append([0, 0, 0, 1])
Seq.append([0, 1, 0, 1])
Seq.append([0, 1, 0, 0])
Seq.append([0, 1, 1, 0])

nsteps = len(Seq) -1


if False:
	for ii in range(1,nsteps+1):
		for nn in range(4):
			Seq[ii][nn] = not Seq[ii][nn]

print Seq

print coil 

lastStep = 0

for ii in range(len(coil)):
	GPIO.setup(coil[ii], GPIO.OUT)
	colPWM[ii] = GPIO.PWM(coil[ii], 100)
	colPWM[ii].start(0)

def setOFF():
	setStep(Seq[0])

 
def setStep(values,tune=1):

	count = sum(values)
	print count, tune
	if count ==0: 
		for ii in range(4):
			colPWM[ii].ChangeDutyCycle(0)	
	elif count ==2:
		for ii in range(4):
			if values[ii]  ==0:
				colPWM[ii].ChangeDutyCycle(0)	
			else:
				colPWM[ii].ChangeDutyCycle(100)	
	else:
		for ii in range(4):
			if values[ii]  ==0:
				colPWM[ii].ChangeDutyCycle(0)	
			else:
				colPWM[ii].ChangeDutyCycle(int(100*tune))	
 
def move(delay, steps, direction):
	global lastStep
	ii = lastStep
	for i in range(steps):
		ii += direction
		if ii > nsteps: ii=1
		if ii < 1:      ii= nsteps
		print ii, Seq[ii]
		setStep(Seq[ii])
		if sum(Seq[ii]) ==1:
			time.sleep(0.02)
			#setStep(Seq[0])# Seq[ii],tune =0.9)
			time.sleep(delay)
			#setStep(Seq[ii])
		else:
			time.sleep(0.02)
			#setStep(Seq[0])
			time.sleep(delay)
			setStep(Seq[ii])

	 	lastStep = ii


setStep(Seq[0])
while True:
	
	delay  = raw_input("Time Delay (ms)?")
	stepsF = raw_input("How many steps forward? ")
	stepsB = raw_input("How many steps backwards? ")
	move(float(delay) / 1000.0, int(stepsF),+1)
	setStep(Seq[0])
	time.sleep(1)
	move(float(delay) / 1000.0, int(stepsB),-1)
	setStep(Seq[0])
 