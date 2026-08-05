#!/usr/bin/env python
# -*- coding: utf-8 -*-
# by Karl Wachs
# Feb 3 2019
# version 0.95
##
## py3 prept 

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
#### AE18 Absolute Rotary Encoder 12 bit  that is read like SPI, but just very simple code
####    CLK, CS, DO= read data. it is 12 bits + some status bits
####    pins: Vcc(Red),  GND(black), CS(yellow), CLK(Blue), DO(green), GRD shield black
####    http://www.china-encoder.com/product_detail/productId=101.html
####    this also comes in V=5V;  needs a level shifter to work w raspberry pi 
####

import	sys, os, subprocess, copy
import	time,datetime
import	json

sys.path.append(os.getcwd())
import	piBeaconUtils	as U
import	piBeaconGlobals as G

# TIME CRITICAL - keeps its own GPIO handling on purpose (bit-banged serial read from the encoder, one toggle per bit), so no shared layer
# and no per-pin indirection.
# RPi.GPIO FIRST: a register write is ~1-2 us, a gpiozero toggle goes through the pin factory.
# The pigpio factory is OPTIONAL: without pigpiod, gpiozero keeps its OWN default factory (lgpio on
# a pi5, rpigpio/native elsewhere) instead of this whole branch failing over. Forcing
# PiGPIOFactory() was what made this unusable on newer hardware.
# Nothing starts pigpiod here any more - master does that in startPigpiod(), before it launches any
# program, so the backend no longer depends on where a program sits in the start order.
# useGPIO and gpioOK are ALWAYS defined: useGPIO used to be left unset when both imports failed and
# the program then died much later with "NameError: useGPIO" instead of naming what was missing.
useGPIO = False			# True = talk to RPi.GPIO directly
gpioOK  = False
try:
	import RPi.GPIO as GPIO
	GPIO.setmode(GPIO.BCM)
	GPIO.setwarnings(False)
	useGPIO = True
	gpioOK  = True
except Exception:
	try:
		import gpiozero
		from gpiozero import Device
		try:
			from gpiozero.pins.pigpio import PiGPIOFactory
			Device.pin_factory = PiGPIOFactory()
		except Exception:
			pass
		gpioOK = True
	except Exception:
		pass				# reported after U.setLogging(), no handlers yet here


G.program = "INPUTRotarySwitchAbsolute"


#################################
def readParams():
		"""Reads the latest plugin parameters/config, and if the sensor configuration changed, updates per-device input/output GPIO pin mappings, code types and bit counts in the INPUTS structure, starting GPIO for new devices and restarting the process if existing pin assignments changed.

		Inputs:
		    None.
		Outputs:
		    None: updates global sensors/INPUTS state, may start GPIO or restart the process
		"""
		global sensors
		global oldRaw, lastRead, nInputs, INPUTS, nBits


		inp, inpRaw, lastRead2 = U.doRead(lastTimeStamp=lastRead)
		if inp == "": return
		if lastRead2 == lastRead: return
		lastRead   = lastRead2
		if inpRaw == oldRaw: return
		oldRaw	   = inpRaw

		oldSensors  = sensors

		U.getGlobalParams(inp)
		if "sensors"			in inp : sensors =				(inp["sensors"])
		if oldSensors == sensors: return 

		restart = False
			
		if G.program  not in sensors:
			U.logger.log(20,"{} not in sensors, exit ".format(G.program))
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

					## outp GPIOs
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
						if useGPIO: startGPIO(devId)
						else:		startGPIOzero(devId)
				
		if restart:
			U.restartMyself(reason="new parameters")
		return 



 
	   
#################################
def getINPUTgpio(devId):
	"""Reads the current input value for a device from its GPIO pins, decoding either a serial-encoded stream (with a parity/status retry) or a set of binary input pins, applying inverse, grey-code, or Bourns 8-bit table conversion based on the device's code type.

	Inputs:
	    devId (str): device identifier whose input pins are read
	Outputs:
	    dict: dict {'INPUT': value} with the decoded input value, or -1 on serial read failure
	"""
	global nInputs, INPUTS, GPIOZERO
	value = 0
	try:

		if INPUTS[devId]["codeType"].find("serialEncoded") > -1:
			if useGPIO:		data, parityOK, status = getSerialInfo(devId)
			else:			data, parityOK, status = getSerialInfoZero(devId)
			if status[1] == 0 and status[2] ==0 and parityOK: 
				value = data
			else: # try again
				time.sleep(0.001)
				if useGPIO:		data, parityOK, status = getSerialInfo(devId)
				else:			data, parityOK, status = getSerialInfoZero(devId)
				if status[1] == 0 and status[2] ==0 and parityOK: 
					value = data
				else:
					value = -1

		else:
			for n in range(nInputs[devId]):
				if useGPIO:		dd =  GPIO.input(INPUTS[devId]["pinI"][n]) 
				else:			dd =  GPIOZERO[devId]["pinI"][n].value
				if   INPUTS[devId]["codeType"].find("Inverse")  > -1 and     dd: value += 1 << n
				elif INPUTS[devId]["codeType"].find("Inverse") == -1 and not dd: value += 1 << n

			if   INPUTS[devId]["codeType"].find("grey")>-1:			value = geyToInt(value)

			elif INPUTS[devId]["codeType"].find("bourns8Bit")>-1:	value = burnsTableToInt(value)

	except Exception as e:
			U.logger.log(20,"", exc_info=True)
	return {"INPUT":value}




#################################
def getSerialInfo(devId):
	"""Reads an absolute rotary encoder over a serial GPIO interface by toggling a chip-select and clock line, sampling the data pin for nBits plus 6 status bits, then assembles the position value, computes a parity check, and extracts the status bits.

	Inputs:
	    devId (str): Device identifier keying into the INPUTS pin-configuration dict
	Outputs:
	    tuple: (data int, parity-valid bool, status bits list)
	"""
	global INPUTS
	data = 0
	status = [0,0,0,0,0,0]

	wait = 0.000001 # 1 uSec
	on = 1
	#print INPUTS[devId]
	GPIO.output(INPUTS[devId]["pinO"][0], GPIO.LOW) # select device
	time.sleep(wait*2)# wait 2x Micro sec

	
	# get data bits
	nBits  = INPUTS[devId]["nBits"]
	bits   = [0 for ii in range(nBits+6)]
	parity = 0

	GPIO.output(INPUTS[devId]["pinO"][1], GPIO.LOW) # clock bits start

	time.sleep(wait)# wait x Micro sec
	for bit in range(nBits+6):
		GPIO.output(INPUTS[devId]["pinO"][1], GPIO.HIGH) # clock bit HIGH
		value = GPIO.input(INPUTS[devId]["pinI"][0])# read data bit
		bits[bit] = value
		parity   += value  
		time.sleep(wait)
		GPIO.output(INPUTS[devId]["pinO"][1], GPIO.LOW)# clock bit off
		time.sleep(wait)
	GPIO.output(INPUTS[devId]["pinO"][0], GPIO.HIGH) # un- select device

	status = bits[nBits:]	
	parity2 = (parity %2) == 0
	for bit in range(nBits):
		if bits[bit] == on:
			data += 1 << ( nBits -1 -bit) 

	time.sleep(wait)
	#print "data", data,"parity", parity,"parity2", parity2," status bits", status, "bits", bits 
	return data	, parity2==0 ,status


#################################
def getSerialInfoZero(devId):
	"""GPIO Zero variant of getSerialInfo that reads an absolute rotary encoder using gpiozero objects (Button/LED) instead of RPi.GPIO, sampling nBits plus 6 status bits and computing the position value, parity check, and status bits.

	Inputs:
	    devId (str): Device identifier keying into the INPUTS and GPIOZERO dicts
	Outputs:
	    tuple: (data int, parity-valid bool, status bits list)
	"""
	global INPUTS, GPIOZERO
	data = 0
	status = [0,0,0,0,0,0]

	wait = 0.000001 # 1 uSec
	on = 1
	#print INPUTS[devId]
	GPIOZERO[devId]["pinO"][0].off()

	time.sleep(wait*2)# wait 2x Micro sec

	
	# get data bits
	nBits  = INPUTS[devId]["nBits"]
	bits   = [0 for ii in range(nBits+6)]
	parity = 0

	GPIOZERO[devId]["pinO"][1].off()

	time.sleep(wait)# wait x Micro sec
	for bit in range(nBits+6):
		value = GPIOZERO[devId]["pinI"][1].value
		bits[bit] = value
		parity   += value  
		time.sleep(wait)
		GPIOZERO[devId]["pinO"][1].off()
		time.sleep(wait)
	GPIOZERO[devId]["pinO"][0].off()

	status = bits[nBits:]	
	parity2 = (parity %2) == 0
	for bit in range(nBits):
		if bits[bit] == on:
			data += 1 << ( nBits -1 -bit) 

	time.sleep(wait)
	#print "data", data,"parity", parity,"parity2", parity2," status bits", status, "bits", bits 
	return data	, parity2==0 ,status


#################################
def geyToInt(val): 
	"""Converts a Gray-code value to its plain binary integer by XOR-folding the value with successive right-shifted copies of itself.

	Inputs:
	    val (int): Gray-code encoded integer to decode
	Outputs:
	    int: Decoded binary integer
	"""
	grey =0
	while(val):
		grey = grey ^ val
		val  = val >> 1
	return grey


#################################
def burnsTableToInt(val): 
	"""Looks up a raw Burns-code byte value in the precomputed burns8BitLookUp table and returns the corresponding decoded position index, or 0 if the value is out of range.

	Inputs:
	    val (int): Raw Burns 8-bit code value to translate
	Outputs:
	    int: Decoded position index, or 0 if out of range
	"""
	global burns8BitLookUp
	if val >= 0 and val < len(burns8BitLookUp):
		return burns8BitLookUp[val]
	return 0


#################################
def startGPIOzero(devId):
	"""Initializes gpiozero objects for a device, creating Button inputs (pull-up) for each input pin and LED outputs (initial high) for each output pin in the GPIOZERO dict; logs and swallows any exception.

	Inputs:
	    devId (str): Device identifier keying into INPUTS and GPIOZERO dicts
	Outputs:
	    None: Populates GPIOZERO with gpiozero pin objects; logs on error
	"""
	global nInputs, GPIOZERO
	try:
		if devId not in GPIOZERO: GPIOZERO[devId] = {"pinI":[0,0,0,0,0],"pinO":[0,0,0,0,0]}
		if "pinI" in INPUTS[devId]:
			for n in range(nInputs[devId]):
				GPIOZERO[devId]["pinI"][n] = gpiozero.Button(INPUTS[devId]["pinI"][n], pull_up=True) 
		if "pinO" in INPUTS[devId]:
			for n in range(len(INPUTS[devId]["pinO"])):
				GPIOZERO[devId]["pinO"][n] = gpiozero.LED(INPUTS[devId]["pinO"][n], initial_value=True) 
		return
	except Exception as e:
		U.logger.log(20,"", exc_info=True)
		U.logger.log(20,"start {}  {}".format(G.program, sensors))
	return

def startGPIO(devId):
	"""Configures RPi.GPIO pins for a device, setting input pins as inputs with pull-up resistors and output pins as outputs driven high; logs and swallows any exception.

	Inputs:
	    devId (str): Device identifier keying into the INPUTS pin-configuration dict
	Outputs:
	    None: Configures GPIO pin modes/levels; logs on error
	"""
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
	except Exception as e:
		U.logger.log(20,"", exc_info=True)
		U.logger.log(20,"start {}  {}".format(G.program, sensors))
	return



def execMain():
	"""Main entry point for the absolute rotary-switch sensor program: builds the Burns 8-bit lookup table, sets up logging, kills stale instances, reads parameters, then loops reading each device's GPIO input, sending updates via URL when data changes or periodically, refreshing parameters every 10s and emitting alive heartbeats.

	Inputs:
	    None.
	Outputs:
	    None: Runs the sensor polling loop, sends data, refreshes params, and updates state until stopped
	"""
	global sensors, sensor
	global oldRaw, lastRead
	global nInputs, INPUTS
	global GPIOZERO
	
	######  burns 8 bit code table
	global burns8BitLookUp
	oldRaw				= ""
	lastRead			= 0
	nInputs				= {}
	INPUTS				= {}
	sensors				= {}
	GPIOZERO			= {}
	#           p 0 1 2 3 4 5 6 7 dec
	burns8Bit= [[0,0,1,1,1,1,1,1,1,127],[1,0,0,1,1,1,1,1,1,63],[2,0,0,1,1,1,1,1,0,62],[3,0,0,1,1,1,0,1,0,58],[4,0,0,1,1,1,0,0,0,56],[5,1,0,1,1,1,0,0,0,184],[6,1,0,0,1,1,0,0,0,152],[7,0,0,0,1,1,0,0,0,24],[8,0,0,0,0,1,0,0,0,8],[9,0,1,0,0,1,0,0,0,72],[10,0,1,0,0,1,0,0,1,73],[11,0,1,0,0,1,1,0,1,77],[12,0,1,0,0,1,1,1,1,79],[13,0,0,0,0,1,1,1,1,15],[14,0,0,1,0,1,1,1,1,47],[15,1,0,1,0,1,1,1,1,175],[16,1,0,1,1,1,1,1,1,191],[17,1,0,0,1,1,1,1,1,159],[18,0,0,0,1,1,1,1,1,31],[19,0,0,0,1,1,1,0,1,29],[20,0,0,0,1,1,1,0,0,28],[21,0,1,0,1,1,1,0,0,92],[22,0,1,0,0,1,1,0,0,76],[23,0,0,0,0,1,1,0,0,12],[24,0,0,0,0,0,1,0,0,4],[25,0,0,1,0,0,1,0,0,36],[26,1,0,1,0,0,1,0,0,164],[27,1,0,1,0,0,1,1,0,166],[28,1,0,1,0,0,1,1,1,167],[29,1,0,0,0,0,1,1,1,135],[30,1,0,0,1,0,1,1,1,151],[31,1,1,0,1,0,1,1,1,215],[32,1,1,0,1,1,1,1,1,223],[33,1,1,0,0,1,1,1,1,207],[34,1,0,0,0,1,1,1,1,143],[35,1,0,0,0,1,1,1,0,142],[36,0,0,0,0,1,1,1,0,14],[37,0,0,1,0,1,1,1,0,46],[38,0,0,1,0,0,1,1,0,38],[39,0,0,0,0,0,1,1,0,6],[40,0,0,0,0,0,0,1,0,2],[41,0,0,0,1,0,0,1,0,18],[42,0,1,0,1,0,0,1,0,82],[43,0,1,0,1,0,0,1,1,83],[44,1,1,0,1,0,0,1,1,211],[45,1,1,0,0,0,0,1,1,195],[46,1,1,0,0,1,0,1,1,203],[47,1,1,1,0,1,0,1,1,235],[48,1,1,1,0,1,1,1,1,239],[49,1,1,1,0,0,1,1,1,231],[50,1,1,0,0,0,1,1,1,199],[51,0,1,0,0,0,1,1,1,71],[52,0,0,0,0,0,1,1,1,7],[53,0,0,0,1,0,1,1,1,23],[54,0,0,0,1,0,0,1,1,19],[55,0,0,0,0,0,0,1,1,3],[56,0,0,0,0,0,0,0,1,1],[57,0,0,0,0,1,0,0,1,9],[58,0,0,1,0,1,0,0,1,41],[59,1,0,1,0,1,0,0,1,169],[60,1,1,1,0,1,0,0,1,233],[61,1,1,1,0,0,0,0,1,225],[62,1,1,1,0,0,1,0,1,229],[63,1,1,1,1,0,1,0,1,245],[64,1,1,1,1,0,1,1,1,247],[65,1,1,1,1,0,0,1,1,243],[66,1,1,1,0,0,0,1,1,227],[67,1,0,1,0,0,0,1,1,163],[68,1,0,0,0,0,0,1,1,131],[69,1,0,0,0,1,0,1,1,139],[70,1,0,0,0,1,0,0,1,137],[71,1,0,0,0,0,0,0,1,129],[72,1,0,0,0,0,0,0,0,128],[73,1,0,0,0,0,1,0,0,132],[74,1,0,0,1,0,1,0,0,148],[75,1,1,0,1,0,1,0,0,212],[76,1,1,1,1,0,1,0,0,244],[77,1,1,1,1,0,0,0,0,240],[78,1,1,1,1,0,0,1,0,242],[79,1,1,1,1,1,0,1,0,250],[80,1,1,1,1,1,0,1,1,251],[81,1,1,1,1,1,0,0,1,249],[82,1,1,1,1,0,0,0,1,241],[83,1,1,0,1,0,0,0,1,209],[84,1,1,0,0,0,0,0,1,193],[85,1,1,0,0,0,1,0,1,197],[86,1,1,0,0,0,1,0,0,196],[87,1,1,0,0,0,0,0,0,192],[88,0,1,0,0,0,0,0,0,64],[89,0,1,0,0,0,0,1,0,66],[90,0,1,0,0,1,0,1,0,74],[91,0,1,1,0,1,0,1,0,106],[92,0,1,1,1,1,0,1,0,122],[93,0,1,1,1,1,0,0,0,120],[94,0,1,1,1,1,0,0,1,121],[95,0,1,1,1,1,1,0,1,125],[96,1,1,1,1,1,1,0,1,253],[97,1,1,1,1,1,1,0,0,252],[98,1,1,1,1,1,0,0,0,248],[99,1,1,1,0,1,0,0,0,232],[100,1,1,1,0,0,0,0,0,224],[101,1,1,1,0,0,0,1,0,226],[102,0,1,1,0,0,0,1,0,98],[103,0,1,1,0,0,0,0,0,96],[104,0,0,1,0,0,0,0,0,32],[105,0,0,1,0,0,0,0,1,33],[106,0,0,1,0,0,1,0,1,37],[107,0,0,1,1,0,1,0,1,53],[108,0,0,1,1,1,1,0,1,61],[109,0,0,1,1,1,1,0,0,60],[110,1,0,1,1,1,1,0,0,188],[111,1,0,1,1,1,1,1,0,190],[112,1,1,1,1,1,1,1,0,254],[113,0,1,1,1,1,1,1,0,126],[114,0,1,1,1,1,1,0,0,124],[115,0,1,1,1,0,1,0,0,116],[116,0,1,1,1,0,0,0,0,112],[117,0,1,1,1,0,0,0,1,113],[118,0,0,1,1,0,0,0,1,49],[119,0,0,1,1,0,0,0,0,48],[120,0,0,0,1,0,0,0,0,16],[121,1,0,0,1,0,0,0,0,144],[122,1,0,0,1,0,0,1,0,146],[123,1,0,0,1,1,0,1,0,154],[124,1,0,0,1,1,1,1,0,158],[125,0,0,0,1,1,1,1,0,30],[126,0,1,0,1,1,1,1,0,94],[127,0,1,0,1,1,1,1,1,95]]
	burns8BitLookUp= [0 for ii in range(256)]
	for ii in range(len(burns8Bit)):
		burns8BitLookUp[burns8Bit[ii][9]] = ii 
		## eg 127 --> 0 
		## 63     --> 1
	######  burns
	
	
	
	
	###################### constants #################
	
	U.setLogging()

	if not gpioOK:	U.logger.log(20, "no GPIO backend on this rpi - the encoder cannot be read; install rpi-lgpio on a pi5")
	
	myPID		= str(os.getpid())
	U.killOldPgm(myPID,G.program+".py")# old old instances of myself if they are still running
	
	sensor			  = G.program
	
	U.logger.log(20, "starting "+G.program+" program")
	
	
	readParams()
	
	
	lastEverything		= time.time()-10000. # -1000 do the whole thing initially
	G.lastAliveSend		= time.time()
	

	if U.getIPNumber() > 0:
		U.logger.log(20," sensors no ip number  exiting ")
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
				if devId not in lastData: lastData[devId] = {"INPUT":0}
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
		except Exception as e:
			U.logger.log(20,"", exc_info=True)
			time.sleep(5.)
	
	try: 	G.sendThread["run"] = False; time.sleep(1)
	except: pass

execMain()
sys.exit(0)
