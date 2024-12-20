#!/usr/bin/env python
# -*- coding: utf-8 -*-
# by Karl Wachs
# mar 2 2016
# version 0.95
##
##	 read sensors and GPIO INPUT and send http to indigo with data
#
#	 GPIO pins as inputs: GPIO:but#	 ={"27":"0","22":"1","25":"2","24":"3","23":"4","18":"5"}

##

import	sys, os, subprocess, copy
import	time,datetime
import	json
import	RPi.GPIO as GPIO  

sys.path.append(os.getcwd())
import	piBeaconUtils	as U
import	piBeaconGlobals as G

G.program = "INPUTgpio"


devId = ""
def readParams():
		global sList,sensors
		global INPgpioType,INPUTcount,INPUTlastvalue
		global oldRaw, lastRead

		INPUTcount = U.checkresetCount(INPUTcount)


		inp,inpRaw,lastRead2 = U.doRead(lastTimeStamp=lastRead)
		if inp == "": return
		if lastRead2 == lastRead: return
		lastRead   = lastRead2
		if inpRaw == oldRaw: return
		oldRaw	   = inpRaw

		oldSensors		  = sensors

		U.getGlobalParams(inp)
		if "sensors"			in inp : sensors =				(inp["sensors"])

		restart = False
		sList = ""
		for sensor in sensors:
			sList+=sensor
			
		if "INPUTgpio" not in sList:
			U.logger.log(30,"INPUTgpio not in sensorlist") 
			exit()
		else:
			if oldSensors != {}: # this is {}  at startup.. dont do anything 
				for sensor in sensors:
					if "INPUTgpio" in sensor.split("-")[0]:
						if sensor not in oldSensors:
							restart=True
							break
						for devId in sensors[sensor]:
							if devId  not in oldSensors[sensor]:
								restart=True
								U.logger.log(30, "new sensor def:{}".format( sensors[sensor][devId]["INPUTS"])	)
								break
							if sensors[sensor][devId]["INPUTS"] != oldSensors[sensor][devId]["INPUTS"]:
								restart=True
								U.logger.log(30, "new sensor def:{}".format( sensors[sensor][devId]["INPUTS"])	 )
								U.logger.log(30, "old sensor def:{}".format(oldSensors[sensor][devId]["INPUTS"]) )
								break
					if restart: break
				
		if restart:
			U.restartMyself(reason="new parameters")


 
	   
def getINPUTgpio(all, sens):
		global INPUTlastvalue, INPUTcount
		d = {}
		new = False
		try:
				#U.logger.log(20, u" all{}, sens:{}".format(all, sens))
				for n in range(len(sens["INPUTS"])):
					if "gpio" not in sens["INPUTS"][n]: continue
					if "lowHighAs" in  sens:
						lowHighAs =	 sens["lowHighAs"]
					else:
						lowHighAs = "0"
					gpioPIN = int(sens["INPUTS"][n]["gpio"])
					count = sens["INPUTS"][n]["count"]
					if lowHighAs =="0":
						if GPIO.input(gpioPIN) ==0: dd="1"
						else:						dd="0"
					else:
						if GPIO.input(gpioPIN) ==0: dd="0"
						else:						dd="1"
					if all:
						if count != "off":
							if count == "up":
								if INPUTlastvalue[str(gpioPIN)] != "1" and dd == "1":
									INPUTcount[str(gpioPIN)]+=1
									new = True
							else:
								if INPUTlastvalue[str(gpioPIN)] != "0" and dd == "0":
									INPUTcount[str(gpioPIN)] += 1
									new = True
							d["INPUT_" + str(n)] = INPUTcount[str(gpioPIN)]

						else:
							d["INPUT_" + str(n)] = dd

					else:
						if count != "off":
							if count == "up":
								if INPUTlastvalue[str(gpioPIN)] != "1" and dd == "1":
									INPUTcount[str(gpioPIN)] += 1
									d["INPUT_" + str(n)] = INPUTcount[str(gpioPIN)]
									new = True
							else:
								if INPUTlastvalue[str(gpioPIN)] != "0" and dd == "0":
									INPUTcount[str(gpioPIN)] += 1
									d["INPUT_" + str(n)] = INPUTcount[str(gpioPIN)]
									new = True
						else:
							 if INPUTlastvalue[str(gpioPIN)] != dd:
								 d["INPUT_"+str(n)] = dd
					INPUTlastvalue[str(gpioPIN)] = dd
					#U.logger.log(20, u" d{}, new:{}".format(d, new))
		except	Exception as e:
				U.logger.log(30,"", exc_info=True)
		return d,new


def startGPIO():
	global sensors, INPUTcount, lastGPIO
	try:
		lastGPIO={}
		for nn in range(30):
			lastGPIO[nn] =""
		GPIO.setmode(GPIO.BCM)
		for n in range(30):
			sensor="INPUTgpio-"+str(n)
			if sensor not in sensors: continue
			for devId  in sensors[sensor]:
				if "INPUTS" not in sensors[sensor][devId]: continue
				ss = sensors[sensor][devId]["INPUTS"]
				for nn in range(len(ss)):
					if "gpio" not in ss[nn]: continue
					U.logger.log(20,"ss: {},".format(ss))
					gpioPIN = int(ss[nn]["gpio"])
					theType	= ss[nn]["inpType"]
					count	= ss[nn]["count"]
					if	 count == "off":
						INPUTcount[str(gpioPIN)] = 0
					if	 theType == "open":
						GPIO.setup(gpioPIN, GPIO.IN)
					elif theType == "high":
						GPIO.setup(gpioPIN, GPIO.IN, pull_up_down=GPIO.PUD_UP)
					elif theType == "low":
						GPIO.setup(gpioPIN, GPIO.IN, pull_up_down=GPIO.PUD_DOWN)
					elif theType == "inOpen":
						GPIO.setup(gpioPIN, GPIO.IN)
		return
	except	Exception as e:
		U.logger.log(30,"", exc_info=True)
		U.logger.log(30,"startGPIO: {}".format(sensors))
	return




global sList,sensors
global INPUTMapR
global sensors,lastGPIO
global oldRaw, lastRead
oldRaw				= ""
lastRead			= 0


###################### constants #################

####################  input gios   ...allrpi	  only rpi2 and rpi0--
INPUTlastvalue ={}
for ii in range(30):
	INPUTlastvalue[str(ii)] = "-1"
INPUTcount		  = {}
#i2c pins:		  = gpio14 &15
# 1 wire		  = gpio4
#####################  init parameters that are read from file 

myPID		= str(os.getpid())
U.setLogging()

U.killOldPgm(myPID,G.program+".py")# old old instances of myself if they are still running

#  Possible answers are 0 = Compute Module, 1 = Rev 1, 2 = Rev 2, 3 = Model B+/A+
piVersion = GPIO.RPI_REVISION

sensor			  = G.program
sensors			  = {}
sList			  = ""
loopCount		  = 0

U.logger.log(30, "starting "+G.program+" program")

readParams()
startGPIO()
INPUTcount = U.readINPUTcount()

		



shortWait			= 0.1	 # seconds to send new INPUT info if available, tried interrupt, but that is NOT STABLE .. this works does ~ 0.2 sec to indigo round trip.
lastEverything		= time.time()-10000. # -1000 do the whole thing initially
G.lastAliveSend		= time.time()
# set alive file at startup


lastData		= {}

#print "shortWait",shortWait	 

if U.getIPNumber() > 0:
	U.logger.log(30," sensors no ip number  exiting ")
	time.sleep(10)
	exit()


lastMsg = time.time()
quick  = 0
qCount = 0

G.tStart = time.time() 
lastRead = time.time()
shortWait = 0.15
sensBase = G.program+"-"

while True:
	try:
		data={}
		data0={}
		tt= time.time()
		if sensBase in sList:
			for n in range(30):
				sensor = sensBase + str(n)
				if sensor not in sensors: continue
				newAll = False
				ddd = {}
				for devId in sensors[sensor]:
					dd, new = getINPUTgpio(True, sensors[sensor][devId])
					newAll = new or newAll
					if len(dd) > 0:
						ddd[devId] = dd
				if newAll: U.writeINPUTcount(INPUTcount)
				if ddd != {}:
					data0[sensor] = ddd
		#U.logger.log(20, "data:{}".format(data0))

		if	data0 != {}:
			#print " sensors", data0, lastData
			if data0 != lastData or (tt-lastMsg > G.sendToIndigoSecs) or quick: 
				lastGPIO= U.doActions(data0,lastGPIO, sensors, sensBase+"1")
									
				lastMsg=tt
				lastData=copy.copy(data0)
				data={}
				data["sensors"]		= data0
				U.sendURL(data)

		U.makeDATfile(G.program, data)
		quick = U.checkNowFile(G.program)
		U.manageActions("-loop-")
		if loopCount%50==0:
			##U.checkIfAliveNeedsToBeSend(lastMsg)
			U.echoLastAlive(G.program)
			
		if time.time()- lastRead > 10:
					readParams()
					lastRead = time.time()

		loopCount+=1
		time.sleep(shortWait)
	except	Exception as e:
		U.logger.log(30,"", exc_info=True)
		time.sleep(5.)

try: 	G.sendThread["run"] = False; time.sleep(1)
except: pass

sys.exit(0)
