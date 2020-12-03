import RPi.GPIO as GPIO
import time
global lastStep

GPIO.setmode(GPIO.BCM)
GPIO.setwarnings(False)
coil_1 = 21 # blue
coil_2 = 20 # pink
coil_3 = 16 # yellow
coil_4 = 12 # orange
 
#
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


lastStep = 0

GPIO.setup(coil_1, GPIO.OUT)
GPIO.setup(coil_2, GPIO.OUT)
GPIO.setup(coil_3, GPIO.OUT)
GPIO.setup(coil_4, GPIO.OUT)
 
def setOFF():
	setStep(Seq[0])

 
def setStep(values):
	GPIO.output(coil_1, values[0])
	GPIO.output(coil_2, values[1])
	GPIO.output(coil_3, values[2])
	GPIO.output(coil_4, values[3])
 
def move(delay, steps, direction):
	global lastStep
	ii = lastStep
	for i in range(steps):
		ii += direction
		if ii > 8: ii=1
		if ii < 1: ii=8
		setStep(Seq[ii])
		time.sleep(delay)
	 	lastStep = ii


setStep(Seq[0])
while True:
	
	delay  = raw_input("Time Delay (ms)?")
	stepsF = raw_input("How many steps forward? ")
	stepsB = raw_input("How many steps backwards? ")
	move(float(delay) / 1000.0, int(stepsF),+1)
	setStep(Seq[0])
	move(float(delay) / 1000.0, int(stepsB),-1)
	setStep(Seq[0])
 