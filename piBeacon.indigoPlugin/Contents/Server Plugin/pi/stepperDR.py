#!/usr/bin/env python
# -*- coding: utf-8 -*-
# by Karl Wachs
# feb 5 2016
# version 0.9 
##
###
import RPi.GPIO as GPIO
import	sys, os, time

import	RPi.GPIO as GPIO


GPIO.setmode(GPIO.BCM)
GPIO.setwarnings(False)


# ########################################
# #########  moving functions ############
# ########################################
 
# ------------------    ------------------ 

def makeStepDRV8834(dir):
	global gpiopinSET, lastDirection
	global isDisabled, isSleep


	if isDisabled: 
		setGPIOValue(gpiopinSET["pin_Enable"], 0)
		time.sleep(0.01)
		isDisabled= False

	if  isSleep: 
		setGPIOValue(gpiopinSET["pin_Sleep"], 1)
		time.sleep(0.01)
		isSleep= False

	if dir != lastDirection: 
		setGPIOValue(gpiopinSET["pin_Dir"], dir==1)
		lastDirection = dir
		time.sleep(0.1)

	setGPIOValue(gpiopinSET["pin_Step"], 1)
	time.sleep(0.000001)
	setGPIOValue(gpiopinSET["pin_Step"], 0)


# ------------------    ------------------ 
def setMotorOFF():
	global gpiopinSET
	setGPIOValue(gpiopinSET["pin_Sleep"], 0)
	setGPIOValue(gpiopinSET["pin_Enable"], 1)


def setMotorSleep():
	global gpiopinSET
	setGPIOValue(gpiopinSET["pin_Sleep"], 0)

 
# ------------------    ------------------ 
def move(delay, steps, direction):
	global minDelay
	delay = max(minDelay,delay)
	steps = int(steps)
	for i in range(steps):
		makeStepDRV8834(direction)
		time.sleep(delay)
	return 



def defineGPIOin(pin):
		try:    GPIO.setup(int(gpiopinSET[pin]),	GPIO.IN, pull_up_down=GPIO.PUD_UP)
		except: pass

def defineGPIOout(pin):
		try:    GPIO.setup( int(pin),	GPIO.OUT)
		except: pass
	
def setGPIOValue(pin,val):
	GPIO.output(int(pin),int(val))



def getPinValue(pinNumber):
	if pinNumber not in gpiopinSET: return -1
	if gpiopinSET[pinNumber] < 1:   return -1
	ret =  GPIO.input(gpiopinSET[pinNumber])
	return (ret-1)*-1



#################################
#################################
#################################

global gpiopinSET
global minDelay
global lastDirection
global isDisabled
global isSleep
global isFault


isFault				  = False
isDisabled			  = True
isSleep				  = True
lastDirection		  = 0
minDelay = 0.00001


## GPIO pins ########
gpiopinSET						= {}
gpiopinSET["pin_Dir"]      		= 19 # orange
gpiopinSET["pin_Step"]      	= 13 # orange
gpiopinSET["pin_Sleep"]      	= 6 # orange
gpiopinSET["pin_Enable"]      	= 5 # orange
defineGPIOout(gpiopinSET["pin_Step"])
defineGPIOout(gpiopinSET["pin_Dir"])
defineGPIOout(gpiopinSET["pin_Sleep"])
defineGPIOout(gpiopinSET["pin_Enable"])



motorMode = 16
stepsIn360        = 200 * motorMode


setMotorOFF()


while True:
			
	delay  = int(raw_input("Time Delay (10uS)?"))
	stepsF = int(raw_input("How many steps forward? "))
	stepsB = int(raw_input("How many steps backwards? "))
	nn = int(raw_input("How often loop? "))
	for ii in range(nn):
		move(delay/100000, stepsF, 1)
		time.sleep(0.1)
		move(delay/100000, stepsB, -1)
		time.sleep(0.1)


		

