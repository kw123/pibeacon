#!/usr/bin/env python
# -*- coding: utf-8 -*-
# by Karl Wachs
# feb 5 2016
# version 0.9 
##
##	get sensor values and write the to a file in json format for later pickup, 
##	do it in a timed manner not to load the system, is every 1 seconds then 30 senods break
##

import	sys, os, time, json, datetime,subprocess,copy
import math

sys.path.append(os.getcwd())
import	piBeaconUtils	as U
import	piBeaconGlobals as G
G.program = "neopixelClock"
import	RPi.GPIO as GPIO





# ===========================================================================
# read params
# ===========================================================================

#################################		 
def readParams():
	global sensor, output, inpRaw, inp, DEVID,useRTC
	global clockDict, devTypeLEDs, speed, speedOfChange, clockLightSet,setClock, clockMode, gpiopinSET, clockLightSensor, minLightNotOff
	global lastCl, timeZone, currTZ
	global oldRaw, lastRead
	global doReadParameters
	try:

		if not doReadParameters: return
		changed =0
		inpLast= inp
		inp,inpRaw,lastRead2 = U.doRead(lastTimeStamp=lastRead)

		if inp == "": 
			inp = inpLast
			return changed
			
		if lastRead2 == lastRead: return changed
		lastRead  = lastRead2
		if inpRaw == "error":
			U.checkParametersFile("parameters-DEFAULT-clock", force = True)
		if inpRaw == oldRaw: return changed
		oldRaw	   = inpRaw
		U.getGlobalParams(inp)
		 
		if "debugRPI"				in inp:	 G.debug=		  int(inp["debugRPI"]["debugRPIOUTPUT"])
		if "useRTC"					in inp:	 useRTC=			 (inp["useRTC"])
		if "output"					in inp:	 output=			 (inp["output"])
		if "minLightNotOff"			in inp:	 minLightNotOff=  int(inp["minLightNotOff"])
		#### G.debug = 2 
		if "neopixelClock" not in output:
			U.logger.log(30, "neopixel-clock	 is not in parameters = not enabled, stopping "+ G.program+".py" )
			exit()
		clockLightSensor =1.

		clock = output["neopixelClock"]
		for devId in  clock:
			DEVID = devId
			clockDict= clock[devId][0]
			clu= unicode(clockDict)
			if lastCl == clu: 
				return changed

			lastCl = clu
			if "devTypeLEDs"	 not in clockDict: continue
			#if clockDict		!= "start" and json.dumps(clockDict)  != json.dumps(cl["neoPixelClock"]):	return 1
			changed = 1
			if "devTypeLEDs"	 in clockDict: 
				if devTypeLEDs !="start" and devTypeLEDs != clockDict["devTypeLEDs"]:
					changed = 2	  
				devTypeLEDs		=  clockDict["devTypeLEDs"]
			else:
					changed = 3	  
			if "timeZone"			 in clockDict:	
				if timeZone !=			   (clockDict["timeZone"]):
					changed = max(2, changed)  
					timeZone =				   (clockDict["timeZone"])
					tznew  = int(timeZone.split(" ")[0])
					if tznew != currTZ:
						U.logger.log(30, u"changing timezone from "+str(currTZ)+"  "+G.timeZones[currTZ+12]+" to "+str(tznew)+"  "+G.timeZones[tznew+12])
						os.system("sudo cp /usr/share/zoneinfo/"+G.timeZones[tznew+12]+" /etc/localtime")
						currTZ = tznew

			clockDict["timeZone"] = str(currTZ)+" "+ G.timeZones[currTZ+12]
				
			if "speedOfChange"	 in clockDict: speedOfChange   =  clockDict["speedOfChange"]
			if "speed"			 in clockDict: speed		   =  clockDict["speed"]

			if "clockLightSet"	 in clockDict: 
				xx											   =  clockDict["clockLightSet"]
				if	xx != clockLightSet:
					changed	  = max(changed,1)
				clockLightSet = xx
			try:
				if "GPIOsetA"			 in clockDict: gpiopinSET["setA"]			 =	int(clockDict["GPIOsetA"])
				if "GPIOsetB"			 in clockDict: gpiopinSET["setB"]			 =	int(clockDict["GPIOsetB"])
				if "GPIOsetC"			 in clockDict: gpiopinSET["setC"]			 =	int(clockDict["GPIOsetC"])
				if "GPIOup"				 in clockDict: gpiopinSET["up"]				 =	int(clockDict["GPIOup"])
				if "GPIOdown"			 in clockDict: gpiopinSET["down"]			 =	int(clockDict["GPIOdown"])
			except:
				pass

			## print clockDict
			break
		if devTypeLEDs == "start":	   changed = 3	# = no data inout restart myself in some seconds
		if changed ==2 : saveParameters()
		return changed

	except	Exception, e:
		print  u"in Line {} has error={}".format(sys.exc_traceback.tb_lineno, e)
		U.logger.log(30, u"in Line {} has error={}".format(sys.exc_traceback.tb_lineno, e))
		time.sleep(10)
		return 3

def startNEOPIXEL(setClock = ""):
	global devTypeLEDs, speed, speedOfChange, clockLightSet,clockMode, clockLightSetOverWrite, LEDintensityFactor
	global DEVID, clockDict, inp 


	try:
		# define short cuts
		clockDict["LEDsum"]		=[]
		clockDict["LEDstart"]	=[]
	
		HHMMSSDDnofTicks={"HH":12,"MM":60,"SS":60,"DD":31}

		lightset = clockLightSet
		if lightset =="auto":
			lightset = clockLightSetOverWrite  ## put here input from light sensor 

		if	 True										: multHMS = 1.	; multMark=1.
		if	 LEDintensityFactor.lower() =="offoff"		: multHMS = 0.12; multMark=0.0
		elif LEDintensityFactor.lower() =="nightoff"	: multHMS = 0.15; multMark=0.0
		elif LEDintensityFactor.lower() =="nightdim"	: multHMS = 0.20; multMark=0.0
		elif LEDintensityFactor.lower() =="daylow"		: multHMS = 0.40; multMark=0.90
		elif LEDintensityFactor.lower() =="daymedium"	: multHMS = 0.60; multMark=0.95
		elif LEDintensityFactor.lower() =="dayhigh"		: multHMS = 1.0 ; multMark=1.0


		if lightset.lower() == "offoff":
			setNightOffPatterns()
		elif lightset.lower() == "nightoff":
			setNightPatterns()
		else:
			restorefromNightPatterns()

		lll = 0
		for r in clockDict["rings"]:
			clockDict["LEDstart"].append(lll)
			lll+=r
			clockDict["LEDsum"].append(lll)
		maxLED = lll
		
		for tt in ["HH","MM","SS","DD"]:
			lll = 0
			for r in clockDict["ticks"][tt]["ringNo"]:
				lll +=clockDict["rings"][r]
			clockDict["ticks"][tt]["LEDsum"]   = lll
			clockDict["ticks"][tt]["LEDstart"] = 0
			if len(clockDict["ticks"][tt]["ringNo"]) >0:
				clockDict["ticks"][tt]["LEDstart"]= clockDict["LEDstart"][clockDict["ticks"][tt]["ringNo"][0]]
			lll = 0
			for r in clockDict["marks"][tt]["ringNo"]:
				lll +=clockDict["rings"][r]
			clockDict["marks"][tt]["LEDsum"]   = lll
			clockDict["marks"][tt]["LEDstart"] = 0
			if len(clockDict["marks"][tt]["ringNo"]) >0:
				clockDict["marks"][tt]["LEDstart"]= clockDict["LEDstart"][clockDict["marks"][tt]["ringNo"][0]]


		string = ""
		for tt in ["HH","MM","SS"]:
			string+=  " "+tt+":" +unicode(clockDict["marks"][tt])
		U.logger.log(10, u"startNEOPIXEL..lightset: "+unicode(lightset)+string)
##20181122-02:21:04 startNEOPIXEL..lightset: offoff;  clockDict[marks] {u'MM': {'LEDstart': 0, u'RGB': [0, 0, 0], u'ringNo': [], 'LEDsum': 0, u'marks': []}, u'SS': {'LEDstart': 0, u'RGB': [0, 0, 0], u'ringNo': [], 'LEDsum': 0, u'marks': []}, u'DD': {'LEDstart': 0, u'RGB': [0, 0, 0], u'ringNo': [], 'LEDsum': 0, u'marks': []}, u'HH': {'LEDstart': 0, u'RGB': [0, 0, 0], u'ringNo': [], 'LEDsum': 0, u'marks': []}}

		pos={}
		for tt in ["HH","MM","SS","DD"]:
			ticks = HHMMSSDDnofTicks[tt]
			ind =[]
			nRings		= len(clockDict["ticks"][tt]["ringNo"])
			if nRings ==0: continue
			ringNo		= clockDict["ticks"][tt]["ringNo"]
			if ringNo ==[]: continue
			LEDstart	= clockDict["ticks"][tt]["LEDstart"]
			LEDsInRing0 = clockDict["rings"][ringNo[0]]
			LEDsum		= clockDict["ticks"][tt]["LEDsum"]
		
			if clockDict["ticks"][tt]["npix"] ==3:	# only for single ring
				for ii in range(clockDict["rings"][ringNo[0]]):
					left		= ii+LEDstart - 1
					mid			= ii+LEDstart
					right		= ii+LEDstart + 1
					if left	 <	LEDstart:			left   = LEDstart + LEDsum -1
					if right >= LEDstart + LEDsum:	right  = LEDstart
					ind.append([left,mid,right])
				RGB= calcRGBdimm(clockDict["ticks"][tt]["RGB"],multHMS,minLight=True)
				pos[tt]= {"RGB":RGB,"index":ind,"blink":clockDict["ticks"][tt]["blink"]}

			elif clockDict["ticks"][tt]["npix"] ==-1: #fill ring up to number
				for tick in range(ticks): 
					tIndex =[]
					##for jj in range(LEDsInRing0):
					for nR in range(nRings):  ### add if # of tick < # of led in ring 
						LEDsinRING		= clockDict["rings"][ringNo[nR]]
						LEDStartinRING	= clockDict["LEDstart"][ringNo[nR]]
						if	 ticks > LEDsinRING:  maxT = int(tick / (float(ticks)/LEDsinRING))
						elif ticks < LEDsinRING:  maxT = int(tick * (float(LEDsinRING)/ticks)) 
						else:					  maxT = tick 
						fromT =0
						if maxT == LEDsinRING-1: # starts at 0 oterhwise no -1 
							fromT=1
						for ii in range(fromT,maxT+1):
							tIndex.append(ii+ LEDStartinRING)
					ind.append(tIndex)
				RGB= calcRGBdimm(clockDict["ticks"][tt]["RGB"],multHMS,minLight=True)
				pos[tt]= {"RGB":RGB,"index":ind,"blink":clockDict["ticks"][tt]["blink"]}

			elif clockDict["ticks"][tt]["npix"] ==1: # single led 
				for tick in range(ticks): 
					tIndex =[]
					##for jj in range(LEDsInRing0):
					for nR in range(nRings):  ### add if # of tick < # of led in ring 
						LEDsinRING		= clockDict["rings"][ringNo[nR]]
						LEDStartinRING	= clockDict["LEDstart"][ringNo[nR]]
						if ticks > LEDsinRING:
							tIndex.append(int(tick / (float(ticks)/LEDsinRING)) + LEDStartinRING)
						elif ticks < LEDsinRING:
							tIndex.append(int(tick * (float(LEDsinRING)/ticks)) + LEDStartinRING)
						else:
							tIndex.append(tick + LEDStartinRING)
					ind.append(tIndex)
				RGB= calcRGBdimm(clockDict["ticks"][tt]["RGB"],multHMS,minLight=True)
				pos[tt]= {"RGB":RGB,"index":ind,"blink":clockDict["ticks"][tt]["blink"]}

			elif clockDict["ticks"][tt]["npix"] ==0: # do not show
				pass

		marks={}
		if (lightset.lower()).find("off") ==-1: 
			for tt in ["HH","MM","SS","DD"]:
				index=[[]]
				if tt not in clockDict["marks"]			 : continue
				if clockDict["marks"][tt] =={}			 : continue
				if clockDict["marks"][tt]["marks"] == [] : continue
				ticks = HHMMSSDDnofTicks[tt]
				for	 nR in range(len(clockDict["marks"][tt]["ringNo"])):
					ringNo		= clockDict["marks"][tt]["ringNo"][nR]
					LEDstart	= clockDict["LEDstart"][ringNo]
					LEDsinRING	= clockDict["rings"][ringNo]
					mult = float(LEDsinRING) / ticks
					for ll in clockDict["marks"][tt]["marks"]:
						ii = int(ll*mult + LEDstart)
						if ii < maxLED:
							index[0].append(ii)
				marks[tt] = {"RGB":[min(int(multMark*x),255) for x in clockDict["marks"][tt]["RGB"]],"index":index}

		if marks == {}: 
			marks = ""
		pos["marks"] = marks

		pos["speed"] = speed

		pos["extraLED"] =""
		if "extraLED" in clockDict and clockDict["extraLED"] !="":
			pos["extraLED"] ={}
			if "RGB" in clockDict["extraLED"]:
				pos["extraLED"]["RGB"]	 = clockDict["extraLED"]["RGB"]
			else:
				pos["extraLED"]["RGB"]	 = [100,100,100]
			if "blink" in clockDict["extraLED"]:
				pos["extraLED"]["blink"] = clockDict["extraLED"]["blink"]
			else:
				pos["extraLED"]["blink"] = [1,1]
			ind =[]
			for tick in clockDict["extraLED"]["ticks"]:
				ind.append(tick)
			pos["extraLED"]["index"] = [ind]
			


		U.logger.log(10, " starting neopixel with:"+ unicode(pos) )	 
		#print	" starting neopixel with MM :", unicode(pos["MM"]["RGB"])
		#print	" starting neopixel with:", unicode(pos["marks"])

		out={"resetInitial": "", "repeat": -1,"command":[{"type": "clock","position":pos, "display": "immediate","speedOfChange":speedOfChange,"marks":marks,"speed":speed}]}
		if setClock !="":
			out["setClock"] = setClock
			clockMode ="setClockStarted"
		else:
			clockMode ="run"
		
		if not U.pgmStillRunning("neopixel.py neopixelClock"):
			U.killOldPgm(myPID,"neopixel.py")
			os.system("/usr/bin/python "+G.homeDir+"neopixel.py neopixelClock &" )
		setNEOinput(out)

	except	Exception, e:
		print  u"in Line {} has error={}".format(sys.exc_traceback.tb_lineno, e)
		U.logger.log(30, u"in Line {} has error={}".format(sys.exc_traceback.tb_lineno, e))
		print "clockDict=", clockDict,"<<"
		print "inp=", inp,"<<"
	return 

def updatewebserverStatus():
	global eth0IP, wifi0IP, LEDintensityFactor, clockLightSetOverWrite, clockLightSet, timeZone, lightSensorValue
	statusData		= []
	statusData.append( "Neopixel CLOCK current Status, updated every 3 secs ")
	statusData.append( "time........... = "+ datetime.datetime.now().strftime(u"%H:%M:%S") )
	statusData.append( "time zone...... = "+ str(timeZone))
	statusData.append( "IP-Number..eth. = "+ eth0IP )
	statusData.append( "IP-Number..wifi = "+ wifi0IP )
	statusData.append( "WiFi enabled... = "+ str(G.wifiEnabled) )
	statusData.append( "ClockLightSet.. = "+ str(clockLightSet) )
	statusData.append( "LightSensorRaw. = "+ str(lightSensorValue) )
	statusData.append( "LightSensor.... = "+ str(LEDintensityFactor) )
	statusData.append( "LightOveride... = "+ str(clockLightSetOverWrite) )
	statusData.append( "Marks-HH....... = "+ str(clockDict["marks"]["HH"]) )
	statusData.append( "Marks-MM....... = "+ str(clockDict["marks"]["MM"]) )
	statusData.append( "Marks-SS....... = "+ str(clockDict["marks"]["SS"]) )
	statusData.append( "Ticks-HH....... = "+ str(clockDict["ticks"]["HH"]) )
	statusData.append( "Ticks-MM....... = "+ str(clockDict["ticks"]["MM"]) )
	statusData.append( "Ticks-SS....... = "+ str(clockDict["ticks"]["SS"]) )
	U.updateWebStatus(json.dumps(statusData) )



#################################
def calcRGBdimm(input,multHMS,minLight=False):
	global minLightNotOff
	RGB= []
	for x in input:
		
		if x==0 :
			rgb = 0
		elif x <37 and not minLight: 
			rgb = 0
		else:	  
			if minLight:
				rgb = max(min(int(multHMS*(x-36) + 33),255),minLightNotOff)
			else:
				rgb = min(int(multHMS*(x-36) + 33),255)
		RGB.append(rgb)
	return RGB

#################################
def setNEOinput(out):
		global lastNeoParamsSet
		f=open(G.homeDir+"temp/neopixel.inp","a")
		f.write(json.dumps(out)+"\n") 
		f.close()
		lastNeoParamsSet = time.time()
		#print " new neo paramers written", datetime.datetime.now()

#################################
def setupGPIOforTimeset():
	global gpiopinSET 
	try: 
		GPIO.setwarnings(False)
		GPIO.cleanup() 
		GPIO.setmode(GPIO.BCM)

		GPIO.setup(gpiopinSET["setA"], GPIO.IN, pull_up_down=GPIO.PUD_UP)
		GPIO.add_event_detect(gpiopinSET["setA"], GPIO.BOTH,	 callback=setA, bouncetime=500)	 

		GPIO.setup(gpiopinSET["setB"], GPIO.IN, pull_up_down=GPIO.PUD_UP)
		GPIO.add_event_detect(gpiopinSET["setB"], GPIO.BOTH,	 callback=setB, bouncetime=500)	 

		GPIO.setup(gpiopinSET["setC"], GPIO.IN, pull_up_down=GPIO.PUD_UP)
		GPIO.add_event_detect(gpiopinSET["setC"], GPIO.BOTH,	 callback=setC, bouncetime=500)	 


		GPIO.setup(gpiopinSET["up"], GPIO.IN, pull_up_down=GPIO.PUD_UP)
		GPIO.add_event_detect(gpiopinSET["up"], GPIO.FALLING,	  callback=upPressed, bouncetime=500)  

		GPIO.setup(gpiopinSET["down"], GPIO.IN, pull_up_down=GPIO.PUD_UP)
		GPIO.add_event_detect(gpiopinSET["down"], GPIO.FALLING,		callback=downPressed, bouncetime=500)  
	except	Exception, e:
		U.logger.log(30, u"in Line {} has error={}".format(sys.exc_traceback.tb_lineno, e))

	return

#################################
def setA(gpio):
	global clockLightSet, enableupDown,enableHH,enableMM,enableDD,enableDDonOFF, enableTZset,enablePattern,enableLight,currHH, currMM, currDD, currTZ,	useRTC, newDate, resetGPIO, lastButtonTime,switchON
	global doReadParameters
	button = "setA"
	U.logger.log(10, " into "+ button)
	if checkLastButtonPressTiming(button) !=0: return
	time.sleep(0.1)
	currHH, currMM, newDate = setAllSwitchesOff()
	if GPIO.input(gpio) ==0:
		enableupDown	= True
		U.logger.log(10, button+" on")
		switchON[1]		= True
		enableupDown	= True
		if		 switchON[1] and not switchON[2] and not switchON[3]:
			enableHH		= True			  
			if G.ntpStatus == "started, working":
				U.stopNTP(mode="temp")
			enableTZset		= False
		elif	 switchON[1] and	 switchON[2] and not switchON[3]:
			enableDD		= True
			if G.ntpStatus == "started, working":
				U.stopNTP(mode="temp")
		elif	 switchON[1] and not switchON[2] and	 switchON[3]:
			enableDDonOFF	= True
		elif	 switchON[1] and	switchON[2] and		switchON[3]:
			enableTZset		= True
			pass
					
	else:
		U.logger.log(10, button+" off ")
		switchON[1]		= False
		if	 not switchON[1] and not switchON[2] and not switchON[3]:
			setExtraLEDoff()
			startWithNewDate(newDate,"setA")
		elif not switchON[1] and	 switchON[2] and not switchON[3]:
			enableupDown	= True
			enableMM		= True
			if G.ntpStatus == "started, working":
				U.stopNTP(mode="temp")
		elif not switchON[1] and not switchON[2] and	 switchON[3]:
			enableupDown	= True
			enableLight		= True
			setLIGHT("stay")
		elif not switchON[1] and	 switchON[2] and	 switchON[3]:
			enableupDown	= True
			enablePattern	= True
			if G.ntpStatus == "started, working":
				U.stopNTP(mode="temp")
		saveParameters()

	U.logger.log(10,	"switchON:"+str(switchON)+"; enableupDown: "+str(enableupDown)+";  enableHH: "+str(enableHH)+";	 enableMM: "+str(enableMM)+";  enableDD: "+str(enableDD)+";	 enableDDonOFF: "+str(enableDDonOFF)+";	 enableLight: "+str(enableLight)+";	 enableTZset: "+str(enableLight)+";	 enableTZset: "+str(enablePattern))
	if not switchON[1] and not switchON[2] and not switchON[3]: doReadParameters = True
	else:														doReadParameters = False
	return


#################################
def setB(gpio):
	global clockLightSet, enableupDown,enableHH,enableMM,enableDD,enableDDonOFF, enableTZset,enablePattern,enableLight,currHH, currMM, currDD, currTZ,	useRTC, newDate, resetGPIO, lastButtonTime,switchON
	global doReadParameters

	button = "setB"
	U.logger.log(10, " into "+ button)
	if checkLastButtonPressTiming(button) !=0: return
	time.sleep(0.1)
	currHH, currMM, newDate = setAllSwitchesOff()
	
	if GPIO.input(gpio) ==0:
		U.logger.log(10, button+" on")
		switchON[2]		= True
		enableupDown	= True
		if	 not switchON[1] and	switchON[2] and not switchON[3]:
			enableMM		= True
			if G.ntpStatus == "started, working":
				U.stopNTP(mode="temp")
		elif	 switchON[1] and	 switchON[2] and not switchON[3]:
			enableDD		= True
			U.stopNTP(mode="temp")
		elif not switchON[1] and	 switchON[2] and	 switchON[3]:
			enablePattern	= True
		elif	 switchON[1] and not switchON[2] and	 switchON[3]:
			enableTZset		= True
		elif	 switchON[1] and	 switchON[2] and	 switchON[3]:
			enableTZset		= True

	else:
		U.logger.log(10, button+" off ")
		switchON[2]		= False
		if	not switchON[1] and not switchON[2] and not switchON[3]:
			setExtraLEDoff()
			startWithNewDate(newDate,"setA")
		if	  switchON[1] and not switchON[2] and not switchON[3]:
			enableupDown	= True
			enableHH		= True
			U.stopNTP(mode="temp")
		elif not switchON[1] and not switchON[2] and	 switchON[3]:
			enableupDown	= True
			enableLight		= True
			setLIGHT("stay")
		elif	 switchON[1] and not switchON[2] and	 switchON[3]:
			enableupDown	= True
			enableDDonOFF	= True
		saveParameters()

	U.logger.log(10,	"switchON:"+str(switchON)+"; enableupDown: "+str(enableupDown)+";  enableHH: "+str(enableHH)+";	 enableMM: "+str(enableMM)+";  enableDD: "+str(enableDD)+";	 enableDDonOFF: "+str(enableDDonOFF)+";	 enableLight: "+str(enableLight)+";	 enableTZset: "+str(enableLight)+";	 enableTZset: "+str(enablePattern))

	if not switchON[1] and not switchON[2] and not switchON[3]: doReadParameters = True
	else:														doReadParameters = False
	return


#################################
def setC(gpio):
	global clockLightSet, enableupDown,enableHH,enableMM,enableDD,enableDDonOFF, enableTZset,enablePattern,enableLight,currHH, currMM, currDD, currTZ,	useRTC, newDate, resetGPIO, lastButtonTime,switchON
	global doReadParameters
	button = "setC"
	U.logger.log(10, " into "+ button)
	if checkLastButtonPressTiming(button) !=0: return
	time.sleep(0.1)
	currHH, currMM, newDate = setAllSwitchesOff()
	if GPIO.input(gpio) ==0:
		U.logger.log(10, button+" on")
		switchON[3]		= True
		enableupDown	= True
		if	 not switchON[1] and not switchON[2] and	 switchON[3]:
			enableLight		= True
			setLIGHT("stay")
		elif	 switchON[1] and not switchON[2] and	 switchON[3]:
			enableDDonOFF	= True
		elif	 switchON[1] and	 switchON[2] and	 switchON[3]:
			enableTZset		= True
		elif not switchON[1] and	 switchON[2] and	 switchON[3]:
			enablePattern	= True
	else:
		U.logger.log(10, button+" off ")
		switchON[3]		= False
		if	not switchON[1] and not switchON[2] and not switchON[3]:
			setExtraLEDoff()
			startNEOPIXEL()
		elif	switchON[1] and not switchON[2] and not switchON[3]:
			enableupDown	= True
			enableHH		= True
			if G.ntpStatus == "started, working":
				U.stopNTP(mode="temp")
		elif not switchON[1] and	 switchON[2] and not switchON[3]:
			enableupDown	= True
			enableMM		= True
			if G.ntpStatus == "started, working":
				U.stopNTP(mode="temp")
		elif	 switchON[1] and	 switchON[2] and not switchON[3]:
			enableupDown	= True
			enableDD		= True
			if G.ntpStatus == "started, working":
				U.stopNTP(mode="temp")
		saveParameters()

	U.logger.log(10,	"switchON:"+str(switchON)+"; enableupDown: "+str(enableupDown)+";  enableHH: "+str(enableHH)+";	 enableMM: "+str(enableMM)+";  enableDD: "+str(enableDD)+";	 enableDDonOFF: "+str(enableDDonOFF)+";	 enableLight: "+str(enableLight)+";	 enableTZset: "+str(enableLight)+";	 enableTZset: "+str(enablePattern))
	if not switchON[1] and not switchON[2] and not switchON[3]: doReadParameters = True
	else:														doReadParameters = False
	return



#################################
def upPressed(gpio):
	global clockDict, clockLightSet, enableupDown,enableHH,enableMM,enableDD,enableDDonOFF, enableTZset,enablePattern,enableLight,currHH, currMM, currDD, currTZ,  useRTC, newDate, resetGPIO, lastButtonTime, switchON
	if not enableupDown: return
	button = "UP"
	if checkLastButtonPressTiming(button) !=0: return
	time.sleep(0.1)
	U.logger.log(10, button+" button")
	if	enableHH: 
		currHH +=1
		if currHH <	 0:	 currHH = 23
		if currHH > 23:	 currHH =  0
		clockDict["extraLED"]										= {"ticks":[currHH*2 + 60 + 48 + 40 + 32  ], "RGB":[200,200,200],"blink":[1,0]} # start on 8 ring 
		startNEOPIXELNewTime(currHH, currMM, currDD)
	elif enableMM: 
		currMM +=1
		if currMM <	 0:	 currMM = 59
		if currMM > 59:	 currMM =  0
		clockDict["extraLED"]										= {"ticks":[currMM ], "RGB":[200,200,200],"blink":[1,0]} # start on 8 ring 
		startNEOPIXELNewTime(currHH, currMM, currDD)
	elif enableDD: 
		currDD +=1
		startNEOPIXELNewTime(currHH, currMM, currDD)
	elif enableTZset: 
		setTimeZone("UP")
	elif enableLight: 
		setLIGHT("UP")
	elif enablePattern: 
		setPatternUPdown("UP")
	elif enableDDonOFF: 
		if clockDict["ticks"]["DD"]["npix"] == 0:
			setDDonOff("UP")
		else:
			setDDonOff("DOWN")
		
	return

#################################
def downPressed(gpio):
	global clockDict, clockLightSet, enableupDown,enableHH,enableMM,enableDD,enableDDonOFF, enableTZset,enablePattern,enableLight,currHH, currMM, currDD, currTZ,  useRTC, newDate, resetGPIO, lastButtonTime, switchON
	if not enableupDown: return
	button = "DOWN"
	if checkLastButtonPressTiming(button) !=0: return
	time.sleep(0.1)
	U.logger.log(10, button+" button")
	if	 enableHH: 
		currHH -=1
		if currHH <	 0:	 currHH = 23
		if currHH > 23:	 currHH =  0
		clockDict["extraLED"]										= {"ticks":[currHH*2 + 60 + 48 + 40 + 32  ], "RGB":[200,200,200],"blink":[1,0]} # start on 8 ring 
		startNEOPIXELNewTime(currHH, currMM, currDD)
	elif enableMM: 
		currMM -=1
		if currMM <	 0:	 currMM = 59
		if currMM > 59:	 currMM =  0
		clockDict["extraLED"]										= {"ticks":[currMM ], "RGB":[200,200,200],"blink":[1,0]} # start on 8 ring 
		startNEOPIXELNewTime(currHH, currMM, currDD)
	elif enableDD: 
		currDD -=1
		startNEOPIXELNewTime(currHH, currMM, currDD)
	elif enableTZset: 
		setTimeZone("DOWN")
	elif enableLight: 
		setLIGHT("DOWN")
	elif enablePattern: 
		setPatternUPdown("DOWN")
	elif enableDDonOFF: 
		showNWstatus()	  
	
	return


#################################
def setAllSwitchesOff():
	global	enableupDown,enableHH,enableMM,enableDD,enableDDonOFF, enableTZset,enablePattern,enableLight
	enableHH		= False
	enableMM		= False
	enableLight		= False
	enableDD		= False
	enableDDonOFF	= False
	enablePattern	= False
	enableTZset		= False
	enableupDown	= False
	dd				= datetime.datetime.now()
	currHH			= dd.hour
	currMM			= dd.minute
	newDate			= dd.strftime("%Y-%m-%d %H:%M:%S")
	return	 currHH, currMM, newDate


#################################
def startWithNewDate(newDate,set):
	U.logger.log(10, set+':	;;; date -s "'+newDate+'" ' +set)
	if newDate !="":
		os.system("date -s '"+newDate+"'")
		if "useRTC" in inp and (inp["useRTC"] !="" and inp["useRTC"] !="0"):
				U.logger.log(10, " sync hwclock" )
				os.system("sudo hwclock -w") # set hw clock to system time stamp, only works if HW is enabled
	U.logger.log(10, 'set1:	;;; date -s finished ')
	startNEOPIXEL()
	### no!	  resetGPIO = True
	U.logger.log(10, " endof "+set)
	if G.ntpStatus == "temp disabled":
			U.startNTP()

#################################
def setTimeZone(upDown):
	global clockLightSet, enableupDown,enableHH,enableMM,enableDD,enableDDonOFF, enableTZset,enablePattern,enableLight,currHH, currMM, currDD, currTZ,	useRTC, newDate, resetGPIO, lastButtonTime, switchON
	global inp,	 DEVID, clockDict
	global timeZone

	l0=60 + 48 + 40 + 32 +1
	ind = currTZ
	U.logger.log(10,"set timezone "+	 upDown) 
	if	upDown =="UP":
		ind +=1
	else:
		ind -=1
	if ind > 12:  ind = 12
	if ind <-12:  ind = -12
	tz= G.timeZones[ind+12]
	currTZ =  ind
	U.logger.log(10, 'set tz:	  '+upDown+ '  new tz: '+ str(ind)+"  "+tz)
	clockDict["extraLED"]										= {"ticks":[ii+l0 for ii in range(ind+12)], "RGB":[100,100,100],"blink":[1,0]} # start on 8 ring 
	clockDict["clockLightSet"]									= clockLightSet
	inp["output"]["neopixelClock"][DEVID][0]["clockLightSet"]	= clockDict["clockLightSet"] 
	inp["output"]["neopixelClock"][DEVID][0]["extraLED"]		= clockDict["extraLED"]
	makeTZ(tz)
	#print "timeZone", inp["output"]["neopixelClock"][DEVID][0]["timeZone"] 
	startNEOPIXEL()
	return
#################################
def makeTZ(tz):
	global inp, clockDict, DEVID, currTZ
	clockDict["timeZone"] = str(currTZ)+" "+tz
	inp["output"]["neopixelClock"][DEVID][0]["timeZone"] = str(currTZ)+" "+tz
	#print "sudo cp /usr/share/zoneinfo/"+tz+" /etc/localtime"
	U.writeTZ(  cTZ="tz" )

def writeTZ(tz ):
	os.system("sudo cp /usr/share/zoneinfo/"+tz+" /etc/localtime")


#################################
def setExtraLEDoff():
	global DEVID, clockDict, inp
	try:
		if clockDict["extraLED"] !="" or inp["output"]["neopixelClock"][DEVID][0]["extraLED"] !="":
			clockDict["extraLED"]										= ""
			inp["output"]["neopixelClock"][DEVID][0]["extraLED"]		= ""
			saveParameters()
	except	Exception, e:
		print  u"in Line {} has error={}".format(sys.exc_traceback.tb_lineno, e)
		U.logger.log(30, u"in Line {} has error={}".format(sys.exc_traceback.tb_lineno, e))
		print "clockDict=", clockDict,"<<"
		print "inp=", inp,"<<"
		print "DEVID=", DEVID,"<<"

#################################
def startNEOPIXELNewTime(h,m,d,tz=""):
	global clockLightSet, enableupDown,enableHH,enableMM,enableDD,enableDDonOFF, enableTZset,enablePattern,enableLight,currHH, currMM, currDD, currTZ,	useRTC, newDate, resetGPIO, lastButtonTime, switchON
	U.logger.log(10,"startNEOPIXELNewTime "+	 str(d)+"  "+ str(h)+"	"+ str(m)) 
	if h <	0:	h = 23
	if h > 23:	h =	 0
	if m <	0:	m = 59
	if m > 59:	m =	 0
	currHH = h
	currMM = m
	currdd = d
	dd = datetime.datetime.now()
	if dd.day == d:
		newDate = dd.strftime("%Y-%m-%d ")+"%02d"%h+":"+"%02d"%m+":00"
	else:
		dd = datetime.datetime.now() - datetime.timedelta(d-dd.day)
		newDate = dd.strftime("%Y-%m-%d ")+"%02d"%h+":"+"%02d"%m+":00"
	U.logger.log(10, 'bf startNEOPIXEL:	;;; date -s "'+newDate+'"')
	#os.system("date -s '"+newDate+"'")
	startNEOPIXEL(setClock="%02d"%d+":%02d"%h+":%02d"%m+":00")
 
#################################
def setLIGHT(upDown):
	global clockLightSet, enableupDown,enableHH,enableMM,enableDD,enableDDonOFF, enableTZset,enablePattern,enableLight,currHH, currMM, currDD, currTZ,	useRTC, newDate, resetGPIO, lastButtonTime, switchON
	global DEVID, clockDict, inp
	try:
		lightOptions = ["offoff","nightoff", "nightdim","daylow","daymedium", "dayhigh","auto"]
		ind =4
		l0 =60 + 48 + 40 + 32 + 24 + 16 + 12
		U.logger.log(10,"setLIGHT "+  upDown) 
		try: 
			ind =  lightOptions.index(clockLightSet.lower())
			if	upDown =="UP":
				ind +=1
				if ind > 6: ind = 0
			if	upDown =="DOWN":
				ind -=1
				if ind < 0: ind = 0
			else: 
				pass
		except:
			ind = 4
		U.logger.log(10, 'setLIGHT:   '+upDown+ '    '+ str(ind))
		clockLightSet = lightOptions[ind]
		clockDict["extraLED"]										= {"ticks":[ii+l0 for ii in range(ind)] , "RGB":[100,100,100],"blink":[1,1]} # start on 8 ring 
		clockDict["clockLightSet"]									= clockLightSet
		inp["output"]["neopixelClock"][DEVID][0]["clockLightSet"]	= clockDict["clockLightSet"] 
		inp["output"]["neopixelClock"][DEVID][0]["extraLED"]		= clockDict["extraLED"]
	
		startNEOPIXEL()
		return
	except	Exception, e:
		print  u"in Line {} has error={}".format(sys.exc_traceback.tb_lineno, e)
		U.logger.log(30, u"in Line {} has error={}".format(sys.exc_traceback.tb_lineno, e))
		print "clockDict=", clockDict,"<<"
		print "inp=", inp,"<<"



#################################
def setPatternUPdown(upDown):
	global clockLightSet, enableupDown,enableHH,enableMM,enableDD,enableDDonOFF, enableTZset,enablePattern,enableLight,currHH, currMM, currDD, currTZ,	useRTC, newDate, resetGPIO, lastButtonTime, switchON
	global inp,	 DEVID
	global marksONoff, hoursPix, minutesPix,ticksMMHH
	global marksOptions, ticksOptions
	U.logger.log(10,"setPattern "+   upDown) 
	U.logger.log(10, unicode( clockDict["clockLightSet"] )) 
	
	getCurrentPatterns()

	if upDown =="DOWN":
		if marksONoff < 4:	setPatternTo(ticks=ticksMMHH,marks=marksONoff+1, save=True,restart=True, ExtraLED=True)
		else:				setPatternTo(ticks=ticksMMHH,marks=0,			 save=True,restart=True, ExtraLED=True)
	else:
		if ticksMMHH < 3:	setPatternTo(ticks=ticksMMHH+1,marks=marksONoff, save=True,restart=True, ExtraLED=True)
		else:				setPatternTo(ticks=0,		   marks=marksONoff, save=True,restart=True, ExtraLED=True)
	return

#################################
def getCurrentPatterns():
	global marksONoff, hoursPix, minutesPix, ticksMMHH
	global clockDict, inp 
	try:
		if clockDict["ticks"]["MM"]["npix"] ==1:						minutesPix = 1
		else:															minutesPix = -1
		if clockDict["ticks"]["HH"]["ringNo"] ==[8,1]:					hoursPix   = 1
		elif clockDict["ticks"]["HH"]["ringNo"] ==[8,6,4]:				hoursPix   = 3
		else:															hoursPix   = 4

		if	 minutesPix ==	1 and hoursPix ==1: ticksMMHH = 0  # this is the fewest pixel mode 
		elif minutesPix ==	1 and hoursPix ==3: ticksMMHH = 1  
		elif minutesPix ==	1 and hoursPix ==4: ticksMMHH = 2
		elif minutesPix == -1 and hoursPix ==3: ticksMMHH = 3
		elif minutesPix == -1 and hoursPix ==4: ticksMMHH = 4
		else:									ticksMMHH = 4

		if		 clockDict["marks"]["MM"]["marks"] == []:				marksONoff = 0 # = no marks
		elif	 clockDict["marks"]["MM"]["marks"] == [0, 15, 30, 45]:	marksONoff = 1
		else: #must be:[0, 5, 10, 15, 20, 25, 30, 35, 40, 45, 50, 55]
			if	 clockDict["marks"]["SS"]["marks"] == []:				marksONoff = 2
			elif clockDict["marks"]["HH"]["marks"] == [0]:				marksONoff = 4
			else:														marksONoff = 3
	except	Exception, e:
		print  u"in Line {} has error={}".format(sys.exc_traceback.tb_lineno, e)
		U.logger.log(30, u"in Line {} has error={}".format(sys.exc_traceback.tb_lineno, e))
		print "clockDict=", clockDict,"<<"

#################################
def setNightPatterns():
	global marksONoff, hoursPix, minutesPix, ticksMMHH
	global marksONoffLAST, hoursPixLAST, minutesPixLAST, ticksMMHHLAST
	global nightMode

	if nightMode !=1:	 
		marksONoffLAST, hoursPixLAST, minutesPixLAST, ticksMMHHLAST = marksONoff, hoursPix, minutesPix, ticksMMHH
		nightMode = 1
		setPatternTo(ticks=1 ,marks=0, save=False, restart=False, ExtraLED=False)
	return
#################################
def setNightOffPatterns():
	global marksONoff, hoursPix, minutesPix, ticksMMHH
	global marksONoffLAST, hoursPixLAST, minutesPixLAST, ticksMMHHLAST
	global nightMode

	if nightMode !=2: 
		marksONoffLAST, hoursPixLAST, minutesPixLAST, ticksMMHHLAST = marksONoff, hoursPix, minutesPix, ticksMMHH
		nightMode = 2
		setPatternTo(ticks=0 ,marks=0, save=False, restart=False, ExtraLED=False)
	return

#################################
def	 restorefromNightPatterns():
	global marksONoff, hoursPix, minutesPix, ticksMMHH
	global marksONoffLAST, hoursPixLAST, minutesPixLAST, ticksMMHHLAST
	global nightMode

	if nightMode >0:
		setPatternTo(ticks=ticksMMHHLAST ,marks=marksONoffLAST, save=False, restart=False, ExtraLED=False)
		nightMode = 0
	return


#################################
def setPatternTo(ticks="" ,marks="", save=True, restart=True, ExtraLED=False):
	global inp, clockDict, DEVID
	global ticksOptions, marksOptions
	try:
		if ticks !="":
			clockDict["ticks"]									= copy.copy(ticksOptions[ticks])
			inp["output"]["neopixelClock"][DEVID][0]["ticks"]	= copy.copy(ticksOptions[ticks])
		if marks !="":
			clockDict["marks"]									= copy.copy(marksOptions[marks])
			inp["output"]["neopixelClock"][DEVID][0]["marks"]	= copy.copy(marksOptions[marks])
		if ExtraLED and ticks !="" and marks !="":
			l0 = 60 + 48 + 40 +32 +1
			clockDict["extraLED"]	= {"ticks":[ii+l0 for ii in range(ticks+4*marks)], "RGB":[100,100,100],"blink":[1,0]} # start on 8 ring 
		
		getCurrentPatterns()
		if save:
			saveParameters()
		if restart:
			startNEOPIXEL()
	except	Exception, e:
		print  u"in Line {} has error={}".format(sys.exc_traceback.tb_lineno, e)
		U.logger.log(30, u"in Line {} has error={}".format(sys.exc_traceback.tb_lineno, e))
		print "clockDict", clockDict
		print "inp", inp
		print "DEVID", DEVID
		print "ticks", ticks
		print "marks", marks
		
	return
	
#################################
def setDDonOff(upDown):
	global clockLightSet, enableupDown,enableHH,enableMM,enableDD,enableDDonOFF, enableTZset,enablePattern,enableLight,currHH, currMM, currDD, currTZ,	useRTC, newDate, resetGPIO, lastButtonTime, switchON
	global DEVID, clockDict, inp 
	U.logger.log(10,"setDDonOff "+   upDown) 
	U.logger.log(10, unicode(clockDict["clockLightSet"]))
	if upDown=="UP":
		if clockDict["ticks"]["DD"]["npix"] == 0:
			inp["output"]["neopixelClock"][DEVID][0]["ticks"]["DD"]["npix"] = 1
			clockDict["ticks"]["DD"]["npix"] = 1
			saveParameters()
			time.sleep(0.1)
			startNEOPIXEL()
	else:
		if clockDict["ticks"]["DD"]["npix"] == 1:
			inp["output"]["neopixelClock"][DEVID][0]["ticks"]["DD"]["npix"] = 0
			clockDict["ticks"]["DD"]["npix"] = 0
			saveParameters()
			time.sleep(0.1)
			startNEOPIXEL()
	return
	
#################################
def showNWstatus():
	global clockLightSet, enableupDown,enableHH,enableMM,enableDD,enableDDonOFF, enableTZset,enablePattern,enableLight,currHH, currMM, currDD, currTZ,	useRTC, newDate, resetGPIO, lastButtonTime, switchON
	global DEVID, clockDict, inp 
	global networkIndicatorON
	U.logger.log(10,"show NW status ") 

	l0 =60 + 48 + 40 + 32 + 24 + 16 + 12
	if G.networkStatus.find("Inet") >-1: # set network indicator = on for 30 secs 
		clockDict["extraLED"]  = {"ticks":[ii+l0 for ii in range(8)], "RGB":[0,100,0],"blink":[1,0]} # start on 8 ring 
	else:
		clockDict["extraLED"]  = {"ticks":[ii+l0 for ii in range(8)], "RGB":[100,0,0],"blink":[1,0]} # start on 8 ring 
	startNEOPIXEL()
	networkIndicatorON	= time.time()+5
	return
	

#################################
def saveParameters():
	global inp
	global lastNeoParamsSet

	f= open(G.homeDir+"parameters","w")
	f.write(json.dumps(inp, sort_keys=True, indent=2))
	f.close()
	lastNeoParamsSet = time.time() 
	os.system("touch "+G.homeDir+"temp/touchFile")
	return

#################################
def checkLastButtonPressTiming(button):
	global lastButtonTime
	tt =  float(time.time())
	dt =  tt - lastButtonTime[button]
	lastButtonTime[button] = tt
	if dt < 0.35: 
		U.logger.log(10,button + " time: "+str(dt)+"	rejected" )
		return 1
	U.logger.log(10,button+ "	 time: "+str(dt) )
	return	0

 
#################################
def setLightfromSensor():
	global clockLightSet,clockLightSetOverWrite, clockLightSensor, lightSensorValueLast, lightSensorValue
	global lastTimeStampSensorFile, clockLightSetOverWriteOld,  LEDintensityFactor, LEDintensityFactorOld
	try:
		if clockLightSensor			  == 0: return

		try:	ii = lastTimeStampSensorFile
		except: 
			lastTimeStampSensorFile	  = 0
			clockLightSetOverWriteOld = ""
			LEDintensityFactorOld 	  = ""
			lightSensorValue          = 0


		if not os.path.isfile(G.homeDir+"temp/lightSensor.dat"): return
		t = os.path.getmtime(G.homeDir+"temp/lightSensor.dat")
	
		lightSensorValueREAD = ""
		maxRange = 10000.
		sensor =""
		rr, raw = U.readJson(G.homeDir+"temp/lightSensor.dat")
		if rr =={}: 			return
		if "light" not in rr: 	return
		try:
				lightSensorValueREAD = rr["light"]
				sensor				 = rr["sensor"]
				tt					 = rr["time"]
				if sensor == "i2cTSL2561":
					maxRange = 12000.
				elif sensor == "i2cOPT3001":
					maxRange =	2000.
				elif sensor == "i2cVEML6030":
					maxRange =	700.
				elif sensor == "i2cIS1145":
					maxRange =	2000.
			
				#print "lastTimeStampSensorFile, tt", lastTimeStampSensorFile, tt
				if lastTimeStampSensorFile == tt: return 

				lastTimeStampSensorFile = tt
		
			
		except:
			U.logger.log(30, "error reading light sensor")
			return
		if lightSensorValueREAD =="" : return 

		#print "lightSensorValueREAD, lightSensorValueLast", lightSensorValueREAD, lightSensorValueLast
		##	check if 0 , must be 2 in a row.
		if lightSensorValueREAD == 0 and lightSensorValueLast !=0: 
				lightSensorValueLast = lightSensorValueREAD
				return
		lightSensorValueLast = lightSensorValueREAD


		lightSensorValue = lightSensorValueREAD * clockLightSensor *100000./ maxRange
		if	 lightSensorValue < 80:		   CLS ="offoff"  
		elif lightSensorValue < 120:	   CLS ="nightoff"  
		elif lightSensorValue < 400:	   CLS ="nightdim"  
		elif lightSensorValue < 2700:	   CLS ="daylow"	   
		elif lightSensorValue < 16000:	   CLS ="daymedium" 
		else						:	   CLS ="dayhigh"   
		
		restartstartNEOPIXEL = True 
		if LEDintensityFactorOld  != CLS:
			LEDintensityFactorOld 	= LEDintensityFactor
			LEDintensityFactor 		= CLS
			restartstartNEOPIXEL = True 
		if clockLightSet.lower() == "auto": 
			if clockLightSetOverWriteOld !=	  CLS:
				clockLightSetOverWriteOld 	= clockLightSetOverWrite
				clockLightSetOverWrite 		= CLS
				restartstartNEOPIXEL = True 
				
		if restartstartNEOPIXEL:
			startNEOPIXEL()
		#print  "setting lightSenVREAD lightSenV, clockLSetOW, maxRange, clockLightSet, LEDintF:"+str(int(lightSensorValueREAD))+"  "+str(int(lightSensorValue))+" "+str(clockLightSetOverWrite)+"  "+str(int(maxRange))+" "+clockLightSet+"  "+str(LEDintensityFactor) 
		U.logger.log(10, "setting lightSenVREAD lightSenV, clockLSetOW, maxRange, clockLightSet, LEDintF:"+str(int(lightSensorValueREAD))+"  "+str(int(lightSensorValue))+" "+str(clockLightSetOverWrite)+"  "+str(int(maxRange))+" "+clockLightSet+"  "+str(LEDintensityFactor))
##20181122-02:17:22 setting  lightSensorValueREAD lightSensorValue, clockLightSetOverWrite, maxRange, clockLightSet, LEDintensityFactor:6.0  50.0 daymedium  12000.0 offoff  offoff
	except	Exception, e:
		U.logger.log(30, u"in Line {} has error={}".format(sys.exc_traceback.tb_lineno, e))
	return


#################################
def afterAdhocWifistarted(maxTime):
	global DEVID, clockDict, inp 
	l0=60 + 48 + 40 
	clockDict["extraLED"]	  = {"ticks":[ii+l0 for ii in range(maxTime)], "RGB":[0,0,200],"blink":[1,1]} # blink led 7 on 8 ring 
	return



#################################
def resetEverything():
	print "resetting everything back to default, then reboot "
	U.killOldPgm(myPID,"neopixel.py")
	os.system('sudo cp '+G.homeDir+'interfaces-DEFAULT-clock /etc/network/interfaces')
	os.system('cp '+G.homeDir+'parameters-DEFAULT-clock '+G.homeDir+'parameters')
	os.system('sudo cp '+G.homeDir+'wpa_supplicant.conf-DEFAULT-clock /etc/wpa_supplicant/wpa_supplicant.conf')
	time.sleep(2)
	os.system("sudo killall -9 python; sudo sync;sleep 2; sudo reboot -f")
	return ## dummy

#################################
def shutdown():
	print" we are shutting down now"
	time.sleep(1.5)
	os.system("sudo killall -9 python;sleep 2; shutdown now")
	return ## dummy


#################################
def readMarksFile():
	global marksOptions,ticksOptions
	rr, raw = U.readJson(G.homeDir+"temp/patterns")
	if rr == {} or "marks" not in rr:
		restorePattern()
		rr, raw = U.readJson(G.homeDir+"temp/patterns")
	if rr == {} or "marks" not in rr:
		print " fatal error patern file destroyed" 
		marksOptions = copy.copy(inp["output"]["neopixelClock"][DEVID][0]["marks"])
		ticksOptions = copy.copy(inp["output"]["neopixelClock"][DEVID][0]["ticks"])
		return 
		
	marksOptions   = copy.copy(rr["marks"])
	ticksOptions   = copy.copy(rr["ticks"])
	
#################################
def restorePattern():
	os.system(" cp "+G.homeDir+"patterns-DEFAULT-clock " +G.homeDir+"patterns") 
	os.system(" cp "+G.homeDir+"patterns-DEFAULT-clock " +G.homeDir+"temp/patterns") 
	return 
	
#################################
#################################
#################################
#################################
global clockDict, clockLightSet, enableupDown,enableHH,enableMM,enableDD,enableDDonOFF, enableTZset,enablePattern,enableLight,currHH, currMM, currDD, currTZ,  useRTC, newDate, resetGPIO, lastButtonTime
global switchON, minLightNotOff
global sensor, output, inpRaw, lastCl,clockMarks,maRGB
global oldRaw,	lastRead, inp
global gpiopinSET
global clockLightSetOverWrite,useRTC, newDate, resetGPIO, lastButtonTime, DEVID
global timeZone
global lightSensorValueLast, lightSensorValue
global doReadParameters
global nightMode
global networkIndicatorON
global lastNeoParamsSet
global clockLightSensor, clockLightSetOverWrite, clockLightSetOverWriteOld, LEDintensityFactorOld, LEDintensityFactor
global eth0IP, wifi0IP

lastNeoParamsSet	= time.time()
nightMode			= 0

doReadParameters	= True
timeZone			= ""

#delta to UTC:
JulDelta = int(subprocess.Popen("date -d '1 Jul' +%z " ,shell=True,stdout=subprocess.PIPE,stderr=subprocess.PIPE).communicate()[0].strip("\n").strip())/100
JanDelta = int(subprocess.Popen("date -d '1 Jan' +%z " ,shell=True,stdout=subprocess.PIPE,stderr=subprocess.PIPE).communicate()[0].strip("\n").strip())/100
NowDelta = int(subprocess.Popen("date  +%z "		   ,shell=True,stdout=subprocess.PIPE,stderr=subprocess.PIPE).communicate()[0].strip("\n").strip())/100

currTZ = JanDelta

#print "current tz:", currTZ,JulDelta,JanDelta,NowDelta, G.timeZones[currTZ+12], G.timeZones


minLightNotOff				= 45
switchON					= [False,False,False,False]
DEVID						= "0"
gpiopinSET					= {"setA": 13,"setB":21,"setC":12,"up":19,"down":26} # default 
enableupDown				= False
enableHH					= False
enableMM					= False
enableDD					= False
enablePattern				= False
enableDDonOFF				= False
enableTZset					= False
enableLight					= False
dd							= datetime.datetime.now()
currHH						= dd.hour
currMM						= dd.minute
currDD						= dd.day
useRTC						= ""
newDate						= ""
resetGPIO					= False
lightSensorValueLast		= -1
lightSensorValue			= -1
clockLightSensor			= 0
clockLightSetOverWrite		= "daymedium"
clockLightSetOverWriteOld	= ""
LEDintensityFactorOld		= ""
LEDintensityFactor			= "dayhigh"
lastButtonTime				= {"setA": 0,"setB":0,"setC":0,"UP":0,"DOWN":0}
oldRaw						= ""
lastRead					= 0
clockLightSet				= ""
clockMode					= "run"
clockDict					="start"
speed						= 1
speedOfChange				= 0
lastCl						= ""
devTypeLEDs					= "start"
inpRaw						= ""
inp							= ""
debug						= 5
first						= False
loopCount					= 0
sensor						= G.program
eth0IP						=""
wifi0IP						=""
U.setLogging()

# check for corrupt parameters file 
U.checkParametersFile("parameters-DEFAULT-clock", force = False)

if readParams() ==3:
		U.logger.log(30," parameters not defined")
		U.checkParametersFile("parameters-DEFAULT-clock", force = True)
		time.sleep(20)
		U.restartMyself(param=" bad parameters read", reason="")
	

myPID		= str(os.getpid())
U.killOldPgm(myPID,G.program+".py")# kill old instances of myself if they are still running


U.killOldPgm(myPID,"neopixel.py")

readMarksFile()
getCurrentPatterns()

U.echoLastAlive(G.program)

setAllSwitchesOff()
setupGPIOforTimeset()
slTime = 1

#save old wifi setting
os.system('cp /etc/network/interfaces '+G.homeDir+'interfaces-old')

# stop x11 vnc listener
#os.system('sudo systemctl stop vncserver-x11-serviced.service')

	
sleepTime = slTime
maxWifiAdHocTime	= 12
if U.whichWifi() == "normal":
	wifiStarted = -1
	wifiStartedLastTest = 99999999999999999999.
else:
	wifiStarted			= time.time()
	wifiStartedLastTest = int(time.time())
	afterAdhocWifistarted(maxWifiAdHocTime)

lastWIFITest	 = -1
		

lastGPIOreset	 = 0
G.lastAliveSend	 = time.time() -1000
loopC			 = 0
lastShutDownTest = -1
lastRESETTest	 = -1


U.testNetwork()
U.getIPNumber() 
eth0IP, wifi0IP, G.eth0Enabled, G.wifiEnabled = U.getIPCONFIG()


networkIndicatorON = -1
if wifiStarted < 0:
	l0 =60 + 48 + 40 + 32 + 24 + 16 + 12
	if G.networkStatus.find("Inet") >-1: # set network indicator = on for 30 secs 
		clockDict["extraLED"]  = {"ticks":[ii+l0 for ii in range(8)], "RGB":[0,100,0],"blink":[1,0]} # start on 8 ring 
	else:
		clockDict["extraLED"]  = {"ticks":[ii+l0 for ii in range(8)], "RGB":[100,0,0],"blink":[1,0]} # start on 8 ring 
	startNEOPIXEL()
	networkIndicatorON	= time.time()+25
U.checkParametersFile("parameters-DEFAULT-clock")

	
while True:
	loopC+=1
	try:
	
	
		if networkIndicatorON > 0 and (time.time() > networkIndicatorON) :
			setExtraLEDoff() 
			networkIndicatorON = -1
			startNEOPIXEL()

		if loopC % 600 ==0:	 ### every 10 minutes check if parametersfile is ok, if not, restore default 
			U.checkParametersFile("parameters-DEFAULT-clock")

				
		if loopC % 30 ==0: # every 30 secs read parameters file 
			updatewebserverStatus()
			# set neopixel params file if not set for 1 minutes 

			if time.time() - lastNeoParamsSet > 290: 
				setExtraLEDoff() 
				startNEOPIXEL()

			ret = readParams() 
			if ret == 1: 
				startNEOPIXEL()
			elif ret == 2: 
				U.restartMyself(reason="restarting due to new device specs")
			elif ret == 3: 
				U.checkParametersFile("parameters-DEFAULT-clock")
				time.sleep(20) # wait for some time for good parameters
				U.restartMyself(param=" bad parameters read", reason="")
		
		if loopC % 3 ==0: # every 3 secs read parameters file 
			setLightfromSensor()
			U.echoLastAlive(G.program)
			updatewebserverStatus()
		time.sleep(sleepTime)

		if resetGPIO:  # ready to be removed 
			if time.time() - lastGPIOreset >3: setupGPIOforTimeset()
			resetGPIO = False
			lastGPIOreset = time.time()


		if GPIO.input(gpiopinSET["setB"]) == 1 and GPIO.input(gpiopinSET["setB"]) == 1 and GPIO.input(gpiopinSET["setC"]) == 1:
			doReadParameters = True

			if clockMode.find("setClock") >-1:
				U.logger.log(30," resetting clock mode to RUN") 
				startNEOPIXEL()

		### test for shutdown
		if GPIO.input(gpiopinSET["up"]) == 0 and GPIO.input(gpiopinSET["down"]) == 0 :
			lastShutDownTest+=1
			if lastShutDownTest > 2:
				ticks =[]
				for ind in range(8):
					ticks.append(ind + 60 + 48 + 40 + 32 + 24 + 16 + 12)
				clockDict["extraLED"]	 = {"ticks":ticks, "RGB":[100,100,100],"blink":[1,1]} # show all 8 led on ring w 8 led = dim white blinking
				startNEOPIXEL()
				shutdown()
		else:
			lastShutDownTest =-1

		### test for wifi adhoc setup requested ... and reset to regular wifi 
		if GPIO.input(gpiopinSET["up"]) == 0  and GPIO.input(gpiopinSET["down"]) == 1 :
			lastWIFITest+=1
			if lastWIFITest > 4: 
				if wifiStarted ==-1: 
					afterAdhocWifistarted(maxWifiAdHocTime)
					startNEOPIXEL()
					time.sleep(2)
					U.setStartAdhocWiFi()
					wifiStarted = time.time()
		else:
		   lastWIFITest =-1

		if wifiStarted > -1:
			if (time.time() - wifiStarted >maxWifiAdHocTime*60 ): # reset wifi after maxWifiAdHocTime minutes
				U.setStopAdhocWiFi() 
			iTT= int(time.time())
			if	iTT	 - wifiStartedLastTest > 60: # count down LEDs
				l1 = maxWifiAdHocTime - (iTT - int(wifiStarted))/60
				afterAdhocWifistarted(l1)
				startNEOPIXEL()
				wifiStartedLastTest = iTT

			
		### test for reset requested
		if GPIO.input(gpiopinSET["down"]) == 0 and	GPIO.input(gpiopinSET["up"]) == 1:
			lastRESETTest+=1
			if lastRESETTest > 4:
				resetEverything()
		else:
			lastRESETTest =-1



		#print "setC",GPIO.input(gpiopinSET["setC"])
			
	except	Exception, e:
		U.logger.log(30, u"in Line {} has error={}".format(sys.exc_traceback.tb_lineno, e))
		time.sleep(10.)
		if unicode(e).find("string indices must be integers") >-1:
			U.logger.log(30,"clockDict: "+unicode(clockDict)+"<<" )
			U.logger.log(30,"inp: "+ unicode(inp) +"<<")
			U.restartMyself(reason=" string error")
sys.exit(0)
