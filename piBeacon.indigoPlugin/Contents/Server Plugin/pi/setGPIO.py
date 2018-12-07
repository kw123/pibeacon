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
G.program = "setGPIO"

devType = "OUTPUTgpio"




####################### main start ###############
PWM = 100


myPID = str(os.getpid())

try:	command = json.loads(sys.argv[1])
except: 
	U.toLog(-1, "setGPIO  bad json:" + unicode(sys.argv))
	exit()


inp,inpRaw,lastRead2 = U.doRead(lastTimeStamp=0)
U.getGlobalParams(inp)
U.getIPNumber() 

try:	G.debug= command["debug"]
except: G.debug = 1
G.debug = 3
U.toLog(0, "setGPIO  command :" + unicode(sys.argv))
try:	PWM= command["PWM"]
except: pass


if "cmd" in command:
	cmd= command["cmd"]
	if cmd not in allowedCommands:
		U.toLog(-1, G.program +" bad command " + command + "  allowed:" + unicode(allowedCommands))
		exit(1)

if "pin" in command:
	pin= int(command["pin"])
else:
		U.toLog(-1, G.program +" bad command " + command + "  pin not included")
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
except	Exception, e:
	U.toLog(-1, u"in Line '%s' has error='%s'" % (sys.exc_traceback.tb_lineno, e))
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
			value = PWM*(100-bits)	# duty cycle on xx hz
		else:	 
			value =	   PWM*bits	 # duty cycle on xxx hz 
		U.toLog(1, G.program +" analogwrite pin = " + str(pin) + " to duty cyle:  :" + unicode(value)+";  PWM="+ str(PWM))
		GPIO.setup(pin, GPIO.OUT)
		p = GPIO.PWM(pin, PWM*100)	# 
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
			


except	Exception, e:
	U.toLog(-1, u"in Line '%s' has error='%s'" % (sys.exc_traceback.tb_lineno, e))

exit(0)
