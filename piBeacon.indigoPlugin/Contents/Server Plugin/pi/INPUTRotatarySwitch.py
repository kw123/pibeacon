#!/usr/bin/env python
# -*- coding: utf-8 -*-
# by Karl Wachs
# Feb 3 2019
# version 0.95
##
##	 read  grey encoded n pin rotaty switch, send integer value to indogo every 90 secs or if chnaged
#

##

import	sys, os, subprocess, copy
import	time,datetime
import	json
import	RPi.GPIO as GPIO  

sys.path.append(os.getcwd())
import	piBeaconUtils	as U
import	piBeaconGlobals as G
G.program = "INPUTRotatarySwitch"


def readParams():
		global sensors
		global oldRaw, lastRead, nInputs, INPUTS


		inp,inpRaw,lastRead2 = U.doRead(lastTimeStamp=lastRead)
		if inp == "": return
		if lastRead2 == lastRead: return
		lastRead   = lastRead2
		if inpRaw == oldRaw: return
		oldRaw	   = inpRaw

		oldSensors  = sensors

		U.getGlobalParams(inp)
		if "sensors"			in inp : sensors =				(inp["sensors"])
		if "debugRPI"			in inp:	 G.debug=			  int(inp["debugRPI"]["debugRPISENSOR"])
		if oldSensors == sensors: return 

		restart = False
			
		if G.program  not in sensors:
			print G.program + "  not in sensors" 
			exit()
		oldINPUTS  = copy.deepcopy(INPUTS)
		restart    = False
		if sensor in sensors:
				for devId in sensors[sensor]:
					new = False
					sens = sensors[sensor][devId]
					nInputs[devId] = int(sens["nInputs"])
					if devId not in INPUTS: 
						INPUTS[devId]  = {"lastValue":-1,"codeType":"bin","pin":[]}
					INPUTS[devId]["codeType"]= sens["codeType"]
					for nn in range(nInputs[devId]):
						if len(INPUTS[devId]["pin"]) < nn+1:
							INPUTS[devId]["pin"].append(-1)
							new = True
						if INPUTS[devId]["pin"][nn] != sens["INPUT_"+str(nn)]:
							new = True
							INPUTS[devId]["lastValue"] = -1
						INPUTS[devId]["pin"][nn] = int(sens["INPUT_"+str(nn)])
					if oldINPUTS != {} and new:
						restart = True
						break
					elif oldINPUTS == {} or new:
						startGPIO(devId)
		if restart:
			U.restartMyself(reason="new parameters")
		return 


def setupSensors():

	U.toLog(-1, "starting setup sensors",doPrint=True)

	ret=subprocess.Popen("modprobe w1-gpio" ,shell=True,stdout=subprocess.PIPE,stderr=subprocess.PIPE).communicate()
	if len(ret[1]) > 0:
		U.toLog(-1, "starting GPIO: return error "+ ret[0]+"\n"+ret[1],doPrint=True)
		return False

	ret=subprocess.Popen("modprobe w1_therm",shell=True,stdout=subprocess.PIPE,stderr=subprocess.PIPE).communicate()
	if len(ret[1]) > 0:
		U.toLog(-1, "starting GPIO: return error "+ ret[0]+"\n"+ret[1],doPrint=True)
		return False

	return True
 
	   
def getINPUTgpio(devId):
	global nInputs, INPUTS
	value = 0
	try:
		value = 0
		for n in range(nInputs[devId]):
			dd =  GPIO.input(INPUTS[devId]["pin"][n]) 
			if   INPUTS[devId]["codeType"].find("Inverse")  >-1 and     dd:	value += 1 << n
			elif INPUTS[devId]["codeType"].find("Inverse") ==-1 and not dd: value += 1 << n
		if INPUTS[devId]["codeType"].find("grey")>-1:  value = geyToInt(value)

	except	Exception, e:
			U.toLog(-1, u"in Line '%s' has error='%s'" % (sys.exc_traceback.tb_lineno, e), doPrint=True)
	return {"INPUT":value}

def geyToInt(val): 
	grey =0
	while(val):
		grey = grey ^ val
		val  = val >> 1
	return grey


def startGPIO(devId):
	global nInputs, INPUTS
	print "setting up gpio", INPUTS[devId]
	try:
		for n in range(nInputs[devId]):
			GPIO.setup( INPUTS[devId]["pin"][n], GPIO.IN, pull_up_down=GPIO.PUD_UP)
		return
	except	Exception, e:
		U.toLog(-1, u"in Line '%s' has error='%s'" % (sys.exc_traceback.tb_lineno, e), doPrint=True)
		U.toLog(-1,"start "+ G.program+ "  "+ unicode(sensors), doPrint=True)
	return




global sensors
global sensors
global oldRaw, lastRead
global nInputs, INPUTS
oldRaw				= ""
lastRead			= 0
nInputs				= {}
INPUTS				= {}
sensors				= {}

###################### constants #################

GPIO.setmode(GPIO.BCM)

myPID		= str(os.getpid())
U.killOldPgm(myPID,G.program+".py")# old old instances of myself if they are still running

#  Possible answers are 0 = Compute Module, 1 = Rev 1, 2 = Rev 2, 3 = Model B+/A+
piVersion = GPIO.RPI_REVISION

sensor			  = G.program

U.toLog(-1, "starting "+G.program+" program",doPrint=True)

readParams()

# check if everything is installed
for i in range(100):
	if not setupSensors(): 
		time.sleep(10)
		if i%50==0: U.toLog(-1,"sensor libs not installed, need to wait until done",doPrint=True)
	else:
		break	 
		

shortWait			= 0.3	 
lastEverything		= time.time()-10000. # -1000 do the whole thing initially
G.lastAliveSend		= time.time()

#print "shortWait",shortWait	 

if U.getIPNumber() > 0:
	U.toLog(-1," sensors no ip number  exiting ", doPrint =True)
	time.sleep(10)
	exit()


lastMsg  = 0 
quick    = 0

lastData = {}
G.tStart = time.time() 
lastRead = time.time()
shortWait = 1
loopCount  = 0

while True:
	try:
		data0={}
		data ={"sensors":{}}
		tt= time.time()
		if sensor not in sensors: break
		for devId in  sensors[sensor]:
			if devId not in lastData: lastData[devId]={"INPUT":0}
			data0[devId] = getINPUTgpio(devId)

		if	data0 != lastData or tt - lastMsg > 100:
			lastMsg=tt
			lastData=copy.copy(data0)
			data["sensors"][sensor] = data0
			U.sendURL(data)

		quick = U.checkNowFile(G.program)
		if loopCount%50==0:
			U.echoLastAlive(G.program)
			
		if time.time()- lastRead > 10:
			readParams()
			lastRead = time.time()

		loopCount+=1
		time.sleep(shortWait)
	except	Exception, e:
		U.toLog(-1, u"in Line '%s' has error='%s'" % (sys.exc_traceback.tb_lineno, e),doPrint=True)
		time.sleep(5.)


sys.exit(0)
