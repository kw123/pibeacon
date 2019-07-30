#!/usr/bin/env python
# -*- coding: utf-8 -*-
# by Karl Wachs
# feb 5 2016
# version 0.7 
##
import RPi.GPIO as GPIO
import time
import pigpio 


global lastStep
global pwmRange
global PIG

PIG = True

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
"""
Seq.append([0, 1, 1, 0])
Seq.append([0, 1, 0, 0])
Seq.append([0, 1, 0, 1])
Seq.append([0, 0, 0, 1])
Seq.append([1, 0, 0, 1])
Seq.append([1, 0, 0, 0])
Seq.append([1, 0, 1, 0])
Seq.append([0, 0, 1, 0])
"""

nsteps = len(Seq) -1


if False:
	for ii in range(1,nsteps+1):
		for nn in range(4):
			Seq[ii][nn] = not Seq[ii][nn]

print Seq

print coil 

pwmRange = 40000

lastStep = 0


if PIG: 
	PIGPIO = pigpio.pi()
	for ii in range(len(coil)):
		PIGPIO.set_mode( coil[ii],pigpio.OUTPUT )
		PIGPIO.set_PWM_range( coil[ii], pwmRange )
		PIGPIO.set_PWM_frequency( coil[ii], pwmRange )
		PIGPIO.set_PWM_dutycycle( coil[ii], 0 )
		print "N:", ii," freq:",  PIGPIO.get_PWM_frequency( coil[ii] )

else:
	for ii in range(len(coil)):
		GPIO.setup(coil[ii], GPIO.OUT)
		colPWM[ii] = GPIO.PWM(coil[ii], pwmRange)
		colPWM[ii].start(0)

def setOFF():
	setStep(Seq[0])


def exeStep(ii,ampl):
	global PIGPIO, colPWM, coil
	if PIG:
		print "exeStep", ii, ampl
		PIGPIO.set_PWM_dutycycle(coil[ii],int(ampl))
	else:
		colPWM[ii].ChangeDutyCycle(int(ampl))	


def setStep(values,tune=1.0):
	global PIG, PIGPIO, pwmRange

	count = sum(values)
	print count, tune
	if count ==2:
		for ii in range(4):
			if values[ii] == 0:
				exeStep(ii, 0)
			else:
				exeStep(ii, int(pwmRange*tune))
	else:
		for ii in range(4):
			if values[ii]  ==0:
				exeStep(ii, 0)
			else:
				exeStep(ii, int(pwmRange))#  *tune))
 
def move(reduce, reduceS, delay, delayS, steps, direction):
	global lastStep
	ii = lastStep
	print reduce, reduceS, delay, delayS, steps
	for i in range(steps):
		ii += direction
		if ii > nsteps: ii = 1
		if ii < 1:      ii = nsteps
		print ii, Seq[ii]
		if sum(Seq[ii]) ==1:
			time.sleep(0.0002)
			#setStep(Seq[0])# Seq[ii],tune =0.9)
			setStep(Seq[ii],tune=reduce)
			time.sleep(delay)
			if delayS> 0.: 
				setStep(Seq[ii],tune=reduce)
				time.sleep(delayS)

		else:
			time.sleep(0.0002)
			#setStep(Seq[0])
			setStep(Seq[ii],tune=reduce)
			time.sleep(delay)
			if delayS> 0.: 
				setStep(Seq[ii],tune=reduceS)
				time.sleep(delayS)

	 	lastStep = ii


setStep(Seq[0])
while True:
	
	delay   =  float(raw_input("Time Delay (ms)? "))/1000.
	delayS  =  float(raw_input("Time sleep (ms)? "))/1000.
	reduce  =  float(raw_input("reduce(0-99)? "))/100.
	reduceS =  float(raw_input("reduce while S(0-99)? "))/100.




	stepsF  =  int(raw_input("How many steps forward? "))
	stepsB  =  int(raw_input("How many steps backwards? "))
	move(reduce, reduceS  , delay, delayS, stepsF,+1)
	setStep(Seq[0])
	time.sleep(1)
	move(reduce, reduceS , delay, delayS, stepsB,-1)
	setStep(Seq[0])
 