#!/usr/bin/python
# -*- coding: utf-8 -*-
## adopted from adafruit 
#
import	sys, os, subprocess, copy
import	time, datetime
import	json

import select


sys.path.append(os.getcwd())
import	piBeaconUtils	as U
import	piBeaconGlobals as G
G.program = "checkVoltage"



###############################################
def readParams():
	global sensor, sensors, oldSensor
	global INPgpioType,INPUTcount,INPUTlastvalue
	global GPIOdict, restart
	global oldRaw, lastRead
	global coincidence

	inp,inpRaw,lastRead2 = U.doRead(lastTimeStamp=lastRead)
	U.getGlobalParams(inp)

	return

###############################################
def countBadVoltagePIG(gpio, level, tick):
	writeStatus()
	return 

###############################################
def countBadVoltage():
	writeStatus()
	return 


###############################################
def writeStatus():
	global badVoltageCount,method
	badVoltageCount.append({"count":badVoltageCount[-1]["count"]+1,"timestamp": datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S"),"method":method})
	if len(badVoltageCount) > 100:
		badVoltageCount = badVoltageCount[0].extend(badVoltageCount[-90:])
	U.logger.log(20,"bad voltage reported, count ={}".format(badVoltageCount[-1]))
	writeStatusOut(badVoltageCount)

###############################################
def writeStatusOut(badVoltageCount):
	global method
	if "method" not in badVoltageCount[-1]:
		badVoltageCount=[{"count":0,"timestamp": datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S"),"method":method}]
	U.writeJson(G.homeDir+G.program+".badVoltage", badVoltageCount)


###############################################
def readLastFile():
	global badVoltageCount, method
	badVoltageCount, raw = U.readJson(G.homeDir+G.program+".badVoltage")
	if badVoltageCount =={}:
		badVoltageCount =[]
	if badVoltageCount ==[]:
		badVoltageCount.append({"count":0,"timestamp": datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S"),"method":method})
	writeStatusOut(badVoltageCount)
	U.logger.log(20,"bad voltage file read {}".format(badVoltageCount))
	return 

###############################################
def execVoltageChecker():
	global badVoltageCount, lastRead, startTime, method

	try:
		startTime = time.time()

		lastRead =0
		badVoltageCount = []
		readParams()
		if G.enableVoltageCheck.find("0") >-1: 
			U.logger.log(20,"voltage check not enabled: {}".format(G.enableVoltageCheck))
			exit()

		method = G.enableVoltageCheck.split("-")[0]
		U.setLogging()
		myPID= str(os.getpid())
		U.killOldPgm(myPID, G.program+".py")# old old instances of myself if they are still running
		redLED = 35
		readLastFile()

		if method == "gpio":
			if U.getOSinfo().lower().find("pi zero") ==-1:
				import	RPi.GPIO as GPIO  
				GPIO.setmode(GPIO.BCM)
				try:
					GPIO.setup(redLED, GPIO.IN)
					U.logger.log(20,"GPIO  trying to read  gpio{}: {}".format(redLED, GPIO.input(redLED)))
					GPIO.add_event_detect(int(redLED), GPIO.FALLING,	callback=countBadVoltage) 
				except	Exception as e :
					U.logger.log(30, u"cBY:{:<20} Line {} has error={}".format(G.program, sys.exc_info()[-1].tb_lineno, e))
					U.logger.log(20,"checking  GPIO/setup to read {} failed, trying pigpio".format(redLED) )
					GPIOmethod = "pigio"
			while True:
				time.sleep(20)
				readParams()
			exit()

		if method == "pigio":
			if U.getOSinfo().lower().find("pi zero") ==-1:
				import	pigpio 
				try:
					if not U.pgmStillRunning("pigpiod"):
						os.system("sudo pigpiod &")
					PIGPIO = pigpio.pi()
					PIGPIO.set_mode( redLED,pigpio.INPUT )
					U.logger.log(20,"pigpio trying to read  gpio{}: {}".format(redLED, PIGPIO.read(redLED)))
					PIGPIO.callback(22, pigpio.FALLING_EDGE, countBadVoltagePIG)
				except	Exception as e :
					U.logger.log(30, u"cBY:{:<20} Line {} has error={}".format(G.program, sys.exc_info()[-1].tb_lineno, e))
					U.logger.log(30,"bad voltage checker not started GPIO and pigpio failed both, ERROR")
					time.sleep(500)

				time.sleep(1)
				U.logger.log(20,"started  bad voltage checker using method:{}".format(method))

			else:
					U.logger.log(20,"{}.. not active for pi zero, would stop OS".format(G.program) )
			while True:
				time.sleep(20)
				readParams()
			exit()

		if method == "file":
			U.logger.log(20,"started  bad voltage checker using method:{}".format(method))
			epoll = select.epoll()

			file = open("/sys/devices/platform/soc/soc:firmware/get_throttled")
			epoll.register(file.fileno(), select.EPOLLPRI | select.EPOLLERR)
			status = file.read()

			while(True):
				epoll.poll()
				file.seek(0)
				status = file.read()
				get_throttled = int(status, 16)
				writeStatus()
				U.logger.log(30,"low voltage event happened; get_throttled = {}".format(get_throttled))
				time.sleep(0.5)

			epoll.unregister(file.fileno())
			file.close()
			exit()

	except	Exception as e :
		U.logger.log(30, u"cBY:{:<20} Line {} has error={}".format(G.program, sys.exc_info()[-1].tb_lineno, e))

###############################################
execVoltageChecker()
