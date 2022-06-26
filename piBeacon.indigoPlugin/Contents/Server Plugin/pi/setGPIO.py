#!/usr/bin/env python
# -*- coding: utf-8 -*-
# by Karl Wachs
# nov 27 2015
# version 0.5 
##

import json
import sys
import subprocess
import time
import datetime
import os


allowedCommands = ["up", "down", "pulseUp", "pulseDown", "continuousUpDown", "analogWrite"]

sys.path.append(os.getcwd())
import	piBeaconUtils	as U
import	piBeaconGlobals as G
import traceback
G.program = "setGPIO"

devType = "OUTPUTgpio"




####################### main start ###############
PWM = 100

U.setLogging()

myPID = str(os.getpid())

try:	command = json.loads(sys.argv[1])
except: 
	U.logger.log(30, "setGPIO  bad json:" + unicode(sys.argv))
	exit()


inp,inpRaw,lastRead2 = U.doRead(lastTimeStamp=0)
U.getGlobalParams(inp)
U.getIPNumber() 

U.setLogLevel()

U.logger.log(10, "setGPIO  command :" + unicode(sys.argv))

if "cmd" in command:
	cmd= command["cmd"]
	if cmd not in allowedCommands:
		U.logger.log(30," bad command " + command + "  allowed:" + unicode(allowedCommands))
		exit(1)

if "pin" in command:
	pin= int(command["pin"])
else:
		U.logger.log(30, " bad command " + command + "  pin not included")
		exit(1)


U.killOldPgm(myPID, G.program+".py", param1='"pin":',param2= '"'+str(pin)+'",')	 # old old instances of myself if they are still running


delayStart = max(0,U.calcStartTime(command,"startAtDateTime")-time.time())
if delayStart > 0: 
	time.sleep(delayStart)

if "values" in command:
	values =  command["values"]
	
	
#	 "values:{analogValue:"analogValue+",pulseUp:"+ pulseUp + ",pulseDown:" + pulseDown + ",nPulses:" + nPulses+"}

try:
	if "pulseUp" in values:		pulseUp = float(values["pulseUp"])
	else:						pulseUp = 0
	if "pulseDown" in values:	pulseDown = float(values["pulseDown"])
	else:						pulseDown = 0
	if "nPulses" in values:		nPulses = int(values["nPulses"])
	else:						nPulses = 0
	if "analogValue" in values: bits = max(0.,min(100.,float(values["analogValue"])))
	else:						bits = 0
except	Exception as e:
	U.logger.log(30, u"in Line {} has error={}".format(traceback.extract_tb(sys.exc_info()[2])[-1][1], e))
	exit(0)

inverseGPIO = False
if "inverseGPIO" in command:
	inverseGPIO = command["inverseGPIO"]

if "devId" in command:
	devId = str(command["devId"])
else: devId = "0"

import RPi.GPIO as GPIO
GPIO.setmode(GPIO.BCM)
GPIO.setwarnings(False)


try:	PWM = int(command["PWM"]) *100
except: pass

typeForPWM = "GPIO"
if u"typeForPWM" in inp and inp["typeForPWM"] == "PIGPIO" and U.pgmStillRunning("pigpiod"):
	import pigpio
	PIGPIO = pigpio.pi()
	pwmRange  = PWM
	pwmFreq   = PWM
	typeForPWM = "PIGPIO"

try:
	if cmd == "up":
		GPIO.setup(pin, GPIO.OUT)
		if inverseGPIO: 
			GPIO.output(pin, False)
			U.sendURL({"outputs":{"OUTPUTgpio-1-ONoff":{devId:{"actualGpioValue":"low"}}}})
		else:
			GPIO.output(pin, True)
			U.sendURL({"outputs":{"OUTPUTgpio-1-ONoff":{devId:{"actualGpioValue":"high"}}}})
		

	elif cmd == "down":
		GPIO.setup(pin, GPIO.OUT)
		if inverseGPIO: 
			GPIO.output(pin, True)
			U.sendURL({"outputs":{"OUTPUTgpio-1-ONoff":{devId:{"actualGpioValue":"high"}}}})
		else: 
			GPIO.output(pin, False )
			U.sendURL({"outputs":{"OUTPUTgpio-1-ONoff":{devId:{"actualGpioValue":"low"}}}})

	elif cmd == "analogWrite":
		if inverseGPIO:
			value = (100-bits)	# duty cycle on xx hz
		else:
			value =   bits	 # duty cycle on xxx hz 
		U.logger.log(20, "analogwrite pin = {};    duty cyle: {};  PWM={}; using {}".format(pin, value, PWM, typeForPWM)

		if value >0:
			U.sendURL({"outputs":{"OUTPUTgpio-1":{devId:{"actualGpioValue":"high"}}}})
		else:
			U.sendURL({"outputs":{"OUTPUTgpio-1":{devId:{"actualGpioValue":"low"}}}})

		if typeForPWM == "PIGPIO": 	
			PIGPIO.set_mode(pin, pigpio.OUTPUT)
			PIGPIO.set_PWM_frequency(pin, pwmFreq)
			PIGPIO.set_PWM_range(pin, pwmRange)
			PIGPIO.set_PWM_dutycycle(pin, value )

		else:
			GPIO.setup(pin, GPIO.OUT)
			p = GPIO.PWM(pin, PWM)	# 
			p.start(int(value))	 # start the PWM with  the proper duty cycle

		time.sleep(1000000000)	# we need to keep it alive otherwise it will stop  this is > 1000 days ~ 3 years


	elif cmd == "pulseUp":
		GPIO.setup(pin, GPIO.OUT)
		if inverseGPIO: GPIO.output(pin, False)
		else:			GPIO.output(pin, True)
		time.sleep(pulseUp)
		if inverseGPIO: GPIO.output(pin, True)
		else:			GPIO.output(pin, False)


	elif cmd == "pulseDown":
		GPIO.setup(pin, GPIO.OUT)
		if inverseGPIO: GPIO.output(pin, True)
		else:			GPIO.output(pin, False)
		time.sleep(pulseDown)
		if inverseGPIO: GPIO.output(pin, False)
		else:			GPIO.output(pin, True)

	elif cmd == "continuousUpDown":
		GPIO.setup(pin, GPIO.OUT)
		for ii in range(nPulses):
			if inverseGPIO:	  GPIO.output(pin, False)
			else:			  GPIO.output(pin, True)
			time.sleep(pulseUp)
			if inverseGPIO:	  GPIO.output(pin, True)
			else:			  GPIO.output(pin, False)
			time.sleep(pulseDown)

	U.removeOutPutFromFutureCommands(pin, devType)
			


except	Exception as e:
	U.logger.log(30, u"in Line {} has error={}".format(traceback.extract_tb(sys.exc_info()[2])[-1][1], e))

exit(0)
