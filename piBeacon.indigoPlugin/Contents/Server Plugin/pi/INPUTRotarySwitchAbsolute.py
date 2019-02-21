#!/usr/bin/env python
# -*- coding: utf-8 -*-
# by Karl Wachs
# Feb 3 2019
# version 0.95
##
## read encoded n pin rotaty switch, send integer value to indogo every 90 secs or if changed
#### grey code = only 1 bit changes pre step
####    eg http://www.grayhill.com/assets/1/7/mech_encoder_26.pdf
#### regular binary; normal binary code 
###  like also: https://www.amazon.com/gp/product/B071F4QM6L/ref=ppx_yo_dt_b_asin_title_o06__o00_s00?ie=UTF8&th=1
#### bourns table encoded: 
####    special bourns devices that comes with an 8 bit 0-127 value encoding
####    https://www.bourns.com/pdfs/ace.pdf
####    pins 1,2,G,,3,4   8,7,G,6,5 
#### serial bourns device that is read like SPI, but just very simple code
####    CLK, CS, DO= read data. it is 10 bits + some status bits
####    pins: Di,CLK, GND, DO, V+, CS
####    https://www.bourns.com/pdfs/EMS22A.pdf
#

##

import	sys, os, subprocess, copy
import	time,datetime
import	json
import	RPi.GPIO as GPIO  

sys.path.append(os.getcwd())
import	piBeaconUtils	as U
import	piBeaconGlobals as G
G.program = "INPUTRotarySwitchAbsolute"


#################################
def readParams():
		global sensors
		global oldRaw, lastRead, nInputs, INPUTS, nBits


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
						INPUTS[devId]  = {"lastValue":-1,"codeType":"bin","pinI":[],"nBits":0}

					INPUTS[devId]["codeType"] = sens["codeType"]

					for nn in range(nInputs[devId]):
						if len(INPUTS[devId]["pinI"]) < nn+1:
							INPUTS[devId]["pinI"].append(-1)
							new = True
						if INPUTS[devId]["pinI"][nn] != sens["INPUT_"+str(nn)]:
							new = True
							INPUTS[devId]["lastValue"] = -1
						INPUTS[devId]["pinI"][nn] = int(sens["INPUT_"+str(nn)])

					if "nBits" in sens: 
						try:    INPUTS[devId]["nBits"]= int(sens["nBits"])
						except: pass

					## oupt GPIOs
					for nn in range(27):
						if "OUTPUT_"+str(nn) in sens:
							if "pinO" not in INPUTS[devId]:
								INPUTS[devId]["pinO"]=[]
								new = True
							if len(INPUTS[devId]["pinO"]) < nn+1:
								INPUTS[devId]["pinO"].append(-1)
								new = True
							if INPUTS[devId]["pinO"][nn] != int(sens["OUTPUT_"+str(nn)]):
								new = True
							INPUTS[devId]["pinO"][nn] = int(sens["OUTPUT_"+str(nn)])
					if oldINPUTS != {} and new:
						restart = True
						break
					elif oldINPUTS == {} or new:
						startGPIO(devId)
				
		if restart:
			U.restartMyself(reason="new parameters")
		return 


#################################
def setupGPIOsystem():

	U.toLog(-1, "starting setup GPIOsystem",doPrint=True)

	ret=subprocess.Popen("modprobe w1-gpio" ,shell=True,stdout=subprocess.PIPE,stderr=subprocess.PIPE).communicate()
	if len(ret[1]) > 0:
		U.toLog(-1, "starting GPIO: return error "+ ret[0]+"\n"+ret[1],doPrint=True)
		return False

	ret=subprocess.Popen("modprobe w1_therm",shell=True,stdout=subprocess.PIPE,stderr=subprocess.PIPE).communicate()
	if len(ret[1]) > 0:
		U.toLog(-1, "starting GPIO: return error "+ ret[0]+"\n"+ret[1],doPrint=True)
		return False

	return True
 
	   
#################################
def getINPUTgpio(devId):
	global nInputs, INPUTS
	value = 0
	try:

		if INPUTS[devId]["codeType"].find("serialEncoded") >-1:
			data, status = getSerialInfo(devId)
			if status[1] == 0 and status[2] ==0: 
				value = data
			else:
				value = -1

		else:
			for n in range(nInputs[devId]):
				dd =  GPIO.input(INPUTS[devId]["pinI"][n]) 
				if   INPUTS[devId]["codeType"].find("Inverse")  >-1 and     dd:	value += 1 << n
				elif INPUTS[devId]["codeType"].find("Inverse") ==-1 and not dd: value += 1 << n

			if   INPUTS[devId]["codeType"].find("grey")>-1:			value = geyToInt(value)

			elif INPUTS[devId]["codeType"].find("bourns8Bit")>-1:	value = burnsTableToInt(value)

	except	Exception, e:
			U.toLog(-1, u"in Line '%s' has error='%s'" % (sys.exc_traceback.tb_lineno, e), doPrint=True)
	return {"INPUT":value}




#################################
def getSerialInfo(devId):
	global INPUTS
	data = 0
	status = [0,0,0,0,0,0]

	GPIO.output(INPUTS[devId]["pinO"][0], GPIO.LOW) # select device
	time.sleep(0.000001)# wait 1 Micro sec

	# get data bits
	nBits = INPUTS[devId]["nBits"]
	GPIO.output(INPUTS[devId]["pinO"][1], GPIO.LOW) # clock bits start
	for bit in range(nBits):
		GPIO.output(INPUTS[devId]["pinO"][1], GPIO.HIGH) # clock bit HIGH
		if GPIO.input(INPUTS[devId]["pinI"][0]): # read data bit
			data += 1 << ( nBits -1 -bit) 
		GPIO.output(INPUTS[devId]["pinO"][1], GPIO.LOW)# clock bit off

	for bit in range(6):
		GPIO.output(INPUTS[devId]["pinO"][1], GPIO.HIGH)
		if GPIO.input(INPUTS[devId]["pinI"][0]):
			status[bit] = 1
		GPIO.output(INPUTS[devId]["pinO"][1], GPIO.LOW)
	
	GPIO.output(INPUTS[devId]["pinO"][0], GPIO.HIGH) # un- select device
	#print "data", data," status bits", status
	return data	, status



#################################
def geyToInt(val): 
	grey =0
	while(val):
		grey = grey ^ val
		val  = val >> 1
	return grey


#################################
def burnsTableToInt(val): 
	global burns8BitLookUp
	if val >= 0 and val < len(burns8BitLookUp):
		return burns8BitLookUp[val]
	return 0


#################################
def startGPIO(devId):
	global nInputs, INPUTS
	try:
		if "pinI" in INPUTS[devId]:
			for n in range(nInputs[devId]):
				GPIO.setup( INPUTS[devId]["pinI"][n], GPIO.IN, pull_up_down=GPIO.PUD_UP)
		if "pinO" in INPUTS[devId]:
			for n in range(len(INPUTS[devId]["pinO"])):
				GPIO.setup( INPUTS[devId]["pinO"][n], GPIO.OUT)
				GPIO.output(INPUTS[devId]["pinO"][n], 1)
		return
	except	Exception, e:
		U.toLog(-1, u"in Line '%s' has error='%s'" % (sys.exc_traceback.tb_lineno, e), doPrint=True)
		U.toLog(-1,"start "+ G.program+ "  "+ unicode(sensors), doPrint=True)
	return




global sensors
global sensors
global oldRaw, lastRead
global nInputs, INPUTS


######  burns 8 bit code table
global burns8BitLookUp
oldRaw				= ""
lastRead			= 0
nInputs				= {}
INPUTS				= {}
sensors				= {}
#           p 0 1 2 3 4 5 6 7 dec
burns8Bit= [[0,0,1,1,1,1,1,1,1,127],[1,0,0,1,1,1,1,1,1,63],[2,0,0,1,1,1,1,1,0,62],[3,0,0,1,1,1,0,1,0,58],[4,0,0,1,1,1,0,0,0,56],[5,1,0,1,1,1,0,0,0,184],[6,1,0,0,1,1,0,0,0,152],[7,0,0,0,1,1,0,0,0,24],[8,0,0,0,0,1,0,0,0,8],[9,0,1,0,0,1,0,0,0,72],[10,0,1,0,0,1,0,0,1,73],[11,0,1,0,0,1,1,0,1,77],[12,0,1,0,0,1,1,1,1,79],[13,0,0,0,0,1,1,1,1,15],[14,0,0,1,0,1,1,1,1,47],[15,1,0,1,0,1,1,1,1,175],[16,1,0,1,1,1,1,1,1,191],[17,1,0,0,1,1,1,1,1,159],[18,0,0,0,1,1,1,1,1,31],[19,0,0,0,1,1,1,0,1,29],[20,0,0,0,1,1,1,0,0,28],[21,0,1,0,1,1,1,0,0,92],[22,0,1,0,0,1,1,0,0,76],[23,0,0,0,0,1,1,0,0,12],[24,0,0,0,0,0,1,0,0,4],[25,0,0,1,0,0,1,0,0,36],[26,1,0,1,0,0,1,0,0,164],[27,1,0,1,0,0,1,1,0,166],[28,1,0,1,0,0,1,1,1,167],[29,1,0,0,0,0,1,1,1,135],[30,1,0,0,1,0,1,1,1,151],[31,1,1,0,1,0,1,1,1,215],[32,1,1,0,1,1,1,1,1,223],[33,1,1,0,0,1,1,1,1,207],[34,1,0,0,0,1,1,1,1,143],[35,1,0,0,0,1,1,1,0,142],[36,0,0,0,0,1,1,1,0,14],[37,0,0,1,0,1,1,1,0,46],[38,0,0,1,0,0,1,1,0,38],[39,0,0,0,0,0,1,1,0,6],[40,0,0,0,0,0,0,1,0,2],[41,0,0,0,1,0,0,1,0,18],[42,0,1,0,1,0,0,1,0,82],[43,0,1,0,1,0,0,1,1,83],[44,1,1,0,1,0,0,1,1,211],[45,1,1,0,0,0,0,1,1,195],[46,1,1,0,0,1,0,1,1,203],[47,1,1,1,0,1,0,1,1,235],[48,1,1,1,0,1,1,1,1,239],[49,1,1,1,0,0,1,1,1,231],[50,1,1,0,0,0,1,1,1,199],[51,0,1,0,0,0,1,1,1,71],[52,0,0,0,0,0,1,1,1,7],[53,0,0,0,1,0,1,1,1,23],[54,0,0,0,1,0,0,1,1,19],[55,0,0,0,0,0,0,1,1,3],[56,0,0,0,0,0,0,0,1,1],[57,0,0,0,0,1,0,0,1,9],[58,0,0,1,0,1,0,0,1,41],[59,1,0,1,0,1,0,0,1,169],[60,1,1,1,0,1,0,0,1,233],[61,1,1,1,0,0,0,0,1,225],[62,1,1,1,0,0,1,0,1,229],[63,1,1,1,1,0,1,0,1,245],[64,1,1,1,1,0,1,1,1,247],[65,1,1,1,1,0,0,1,1,243],[66,1,1,1,0,0,0,1,1,227],[67,1,0,1,0,0,0,1,1,163],[68,1,0,0,0,0,0,1,1,131],[69,1,0,0,0,1,0,1,1,139],[70,1,0,0,0,1,0,0,1,137],[71,1,0,0,0,0,0,0,1,129],[72,1,0,0,0,0,0,0,0,128],[73,1,0,0,0,0,1,0,0,132],[74,1,0,0,1,0,1,0,0,148],[75,1,1,0,1,0,1,0,0,212],[76,1,1,1,1,0,1,0,0,244],[77,1,1,1,1,0,0,0,0,240],[78,1,1,1,1,0,0,1,0,242],[79,1,1,1,1,1,0,1,0,250],[80,1,1,1,1,1,0,1,1,251],[81,1,1,1,1,1,0,0,1,249],[82,1,1,1,1,0,0,0,1,241],[83,1,1,0,1,0,0,0,1,209],[84,1,1,0,0,0,0,0,1,193],[85,1,1,0,0,0,1,0,1,197],[86,1,1,0,0,0,1,0,0,196],[87,1,1,0,0,0,0,0,0,192],[88,0,1,0,0,0,0,0,0,64],[89,0,1,0,0,0,0,1,0,66],[90,0,1,0,0,1,0,1,0,74],[91,0,1,1,0,1,0,1,0,106],[92,0,1,1,1,1,0,1,0,122],[93,0,1,1,1,1,0,0,0,120],[94,0,1,1,1,1,0,0,1,121],[95,0,1,1,1,1,1,0,1,125],[96,1,1,1,1,1,1,0,1,253],[97,1,1,1,1,1,1,0,0,252],[98,1,1,1,1,1,0,0,0,248],[99,1,1,1,0,1,0,0,0,232],[100,1,1,1,0,0,0,0,0,224],[101,1,1,1,0,0,0,1,0,226],[102,0,1,1,0,0,0,1,0,98],[103,0,1,1,0,0,0,0,0,96],[104,0,0,1,0,0,0,0,0,32],[105,0,0,1,0,0,0,0,1,33],[106,0,0,1,0,0,1,0,1,37],[107,0,0,1,1,0,1,0,1,53],[108,0,0,1,1,1,1,0,1,61],[109,0,0,1,1,1,1,0,0,60],[110,1,0,1,1,1,1,0,0,188],[111,1,0,1,1,1,1,1,0,190],[112,1,1,1,1,1,1,1,0,254],[113,0,1,1,1,1,1,1,0,126],[114,0,1,1,1,1,1,0,0,124],[115,0,1,1,1,0,1,0,0,116],[116,0,1,1,1,0,0,0,0,112],[117,0,1,1,1,0,0,0,1,113],[118,0,0,1,1,0,0,0,1,49],[119,0,0,1,1,0,0,0,0,48],[120,0,0,0,1,0,0,0,0,16],[121,1,0,0,1,0,0,0,0,144],[122,1,0,0,1,0,0,1,0,146],[123,1,0,0,1,1,0,1,0,154],[124,1,0,0,1,1,1,1,0,158],[125,0,0,0,1,1,1,1,0,30],[126,0,1,0,1,1,1,1,0,94],[127,0,1,0,1,1,1,1,1,95]]
burns8BitLookUp= [0 for ii in range(256)]
for ii in range(len(burns8Bit)):
	burns8BitLookUp[burns8Bit[ii][9]] = ii 
	## eg 127 --> 0 
	## 63     --> 1
######  burns




###################### constants #################

GPIO.setmode(GPIO.BCM)
GPIO.setwarnings(False)

myPID		= str(os.getpid())
U.killOldPgm(myPID,G.program+".py")# old old instances of myself if they are still running

#  Possible answers are 0 = Compute Module, 1 = Rev 1, 2 = Rev 2, 3 = Model B+/A+
piVersion = GPIO.RPI_REVISION

sensor			  = G.program

U.toLog(-1, "starting "+G.program+" program",doPrint=True)

# check if everything is installed
for i in range(100):
	if not setupGPIOsystem(): 
		time.sleep(10)
		if i%50==0: U.toLog(-1,"sensor libs not installed, need to wait until done",doPrint=True)
	else:
		break	 
		


readParams()


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
shortWait = 0.5
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
