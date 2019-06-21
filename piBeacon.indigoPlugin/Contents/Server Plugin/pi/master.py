#!/usr/bin/env python
# -*- coding: utf-8 -*-
# by Karl Wachs
# feb 5 2016
# version 0.7
##
##	1. start beaconloop.py
##	2. loop and check if beaconloop is still alive , if not reboot
##	3. check if we can ping the server, if not	reboot 
##
##

import sys, os, subprocess, copy
import time,datetime
import json
import RPi.GPIO as GPIO

sys.path.append(os.getcwd())
import	piBeaconGlobals as G
import	piBeaconUtils	as U
G.program = "master"






####################      #########################
def cleanupOldFiles():


	os.system("rm -r {}logs                     >/dev/null 2>&1".format(G.homeDir))
	os.system("rm	 {}iPhoneBLE.py             >/dev/null 2>&1".format(G.homeDir))
	os.system("rm	 {}rejects.*                >/dev/null 2>&1".format(G.homeDir))
	os.system("rm	 {}logfile                  >/dev/null 2>&1".format(G.homeDir))
	os.system("rm	 {}logfile-1                >/dev/null 2>&1".format(G.homeDir))
	os.system("rm	 {}call-log                 >/dev/null 2>&1".format(G.homeDir))
	os.system("rm	 {}alive                    >/dev/null 2>&1".format(G.homeDir))
	os.system("rm	 {}master.log               >/dev/null 2>&1".format(G.homeDir))
	os.system("rm	 {}interface                >/dev/null 2>&1".format(G.homeDir))
	os.system("rm	 {}logfile                  >/dev/null 2>&1".format(G.homeDir))
	os.system("rm	 {}beaconloop               >/dev/null 2>&1".format(G.homeDir))
	os.system("rm	 {}errlog                   >/dev/null 2>&1".format(G.homeDir))
	os.system("rm	 {}getsensorvalues.py       >/dev/null 2>&1".format(G.homeDir))
	os.system("rm	 {}receiveGPIOcommands.py   >/dev/null 2>&1".format(G.homeDir))
	os.system("rm	 {}rennameMeTo_myoutput.py  >/dev/null 2>&1".format(G.homeDir))
	os.system("rm	 {}renameMyTo_mysensors.py  >/dev/null 2>&1".format(G.homeDir))
	os.system("rm	 {}INPUTRotata*             >/dev/null 2>&1".format(G.homeDir))
	os.system("rm	 {}INPUTRotateSwitchGrey.py >/dev/null 2>&1".format(G.homeDir))

	restart=False
	return restart




####################      #########################
def checkIfGpioIsInstalled():
	try:
		ret = subprocess.Popen("gpio -v",shell=True,stdout=subprocess.PIPE,stderr=subprocess.PIPE).communicate()
		if ret[0].find("version:") ==-1:
			os.system("rm -R /tmp/wiringPi")
			installGPIO = "cd /tmp; git clone git://git.drogon.net/wiringPi; cd wiringPi; ./build ;	 rm -R /tmp/wiringPi"
			U.toLog(-1,"installing gpio wiringPi .... {}\n with: {}".format(unicode(ret), installGPIO), doPrint=True)
			ret = subprocess.Popen(installGPIO,shell=True,stdout=subprocess.PIPE,stderr=subprocess.PIPE).communicate()
			U.toLog(-1,"result of installing gpio wiringPi .... {}".format(unicode(ret)), doPrint=True)
	except	Exception, e:
		U.toLog(-1, u"checkIfGpioIsInstalled in Line {} has error={}".format(sys.exc_traceback.tb_lineno, e), doPrint=True)





	
####################      #########################
def readNewParams(force=False):
		global enableRebootCheck,  restart,sensorList,rPiCommandPORT, firstRead
		global sensorEnabled, enableiBeacons, beforeLoop, cAddress,rebootHour,rebooted,BLEserial,BLEserialOLD,sensors,enableShutDownSwitch, rebootWatchDogTime
		global shutdownInputPin, shutdownPinVoltSensor,shutDownPinVetoOutput , sensorAlive,useRamDiskForLogfiles, displayActive
		global actions, output
		global lastAlive
		global activePGMdict, bluetoothONoff
		global oldRaw,	lastRead
		global batteryMinPinActiveTimeForShutdown, inputPinVoltRawLastONTime
		global batteryChargeTimeForMaxCapacity, batteryCapacitySeconds
		global GPIOTypeAfterBoot1, GPIOTypeAfterBoot2, GPIONumberAfterBoot1, GPIONumberAfterBoot2
		global activePGM
		global configured
		global startWebServerSTATUS, startWebServerINPUT
		global fanGPIOPin, fanTempOnAtTempValue, fanTempName, fanTempDevId, fanEnable
		global wifiEthCheck, BeaconUseHCINoOld,BLEconnectUseHCINoOld

		BLEserialOLD= BLEserial

		inp,inpRaw,lastRead2 = U.doRead(lastTimeStamp=lastRead)
		if inp == "": 
			os.system("cp "+G.homeDir+"parameters  "+G.homeDir+"temp/parameters")
			time.sleep(1)
			inp,inpRaw,lastRead2 = U.doRead(lastTimeStamp=lastRead)


		if not force:
			if inp == "": return
			if lastRead2 == lastRead: return
			lastRead  = lastRead2
			if inpRaw == oldRaw: return

		lastRead   = lastRead2
		oldRaw	   = inpRaw

		sensorsOld	  = copy.copy(sensors)
		oldSensorList = copy.copy(sensorList)
		rPiRestartCommand =""
			
		U.getGlobalParams(inp)

		if wifiEthCheck != {} and wifiEthCheck != G.wifiEthOld:
			U.restartMyself(reason="new wifi, eth defs, need to restart master", doPrint=True)
		wifiEthCheck = copy.copy(G.wifiEthOld)

		if BeaconUseHCINoOld != "" and BeaconUseHCINoOld != G.BeaconUseHCINo:
			U.restartMyself(reason="new hci-Beacon defs, need to restart master", doPrint=True)
		BeaconUseHCINoOld = copy.copy(G.BeaconUseHCINo)

		if BLEconnectUseHCINoOld != "" and BLEconnectUseHCINoOld != G.BLEconnectUseHCINo:
			U.restartMyself(reason="new hci-BLEconnect defs, need to restart master", doPrint=True)
		BLEconnectUseHCINoOld = copy.copy(G.BLEconnectUseHCINo)

		if "debugRPI"						in inp:	 G.debug=						int(inp["debugRPI"]["debugRPICALL"])
		if u"BLEserial"						in inp:	 BLEserial =					   (inp["BLEserial"])
		if u"enableRebootCheck"				in inp:	 enableRebootCheck=				   (inp["enableRebootCheck"])
		if u"batteryMinPinActiveTimeForShutdown" in inp: batteryMinPinActiveTimeForShutdown= float(inp["batteryMinPinActiveTimeForShutdown"])
		if u"enableiBeacons"				in inp:	 enableiBeacons=		 		   (inp["enableiBeacons"])
		if u"cAddress"						in inp:	 cAddress=				  		    inp["cAddress"]
		if u"rebootHour"					in inp:	 rebootHour=					    int(inp["rebootHour"])
		if u"sensors"						in inp:	 sensors =				 		   (inp["sensors"])
		if u"useRamDiskForLogfiles" 		in inp:	 useRamDiskForLogfiles =  		    inp["useRamDiskForLogfiles"]
		if u"actions"						in inp:	 actions			   =  		    inp["actions"]
		if u"useRTC"						in inp:	 U.setUpRTC(inp["useRTC"])
		if u"batteryChargeTimeForMaxCapacity" in inp: batteryChargeTimeForMaxCapacity= 	float(inp["batteryChargeTimeForMaxCapacity"])
		if u"batteryCapacitySeconds" 		in inp:	 batteryCapacitySeconds= 			float(inp["batteryCapacitySeconds"])

		if u"GPIONumberAfterBoot1" 			in inp:	 GPIONumberAfterBoot1= 			 	 (inp["GPIONumberAfterBoot1"])
		if u"GPIONumberAfterBoot2" 			in inp:	 GPIONumberAfterBoot2= 			 	 (inp["GPIONumberAfterBoot2"])
		if u"GPIOTypeAfterBoot1" 			in inp:	 GPIOTypeAfterBoot1= 			 	 (inp["GPIOTypeAfterBoot1"])
		if u"GPIOTypeAfterBoot2" 			in inp:	 GPIOTypeAfterBoot2= 			 	 (inp["GPIOTypeAfterBoot2"])
		if u"configured" 					in inp:	 configured= 					 	 (inp["configured"])
		if u"startWebServerSTATUS" 			in inp:	 startWebServerSTATUS= 			  int(inp["startWebServerSTATUS"])
		if u"startWebServerINPUT" 			in inp:	 startWebServerINPUT= 			  int(inp["startWebServerINPUT"])
		if u"fanEnable" 					in inp:	 fanEnable= 					     (inp["fanEnable"])
		if fanEnable == "0" or fanEnable == "1":
			
			if u"fanTempDevId" 					in inp:	
				if  inp["fanTempDevId"] =="0":
					fanTempName ="internal"
				else:
					if "sensors" not in inp: 
						fanTempDevId = ""
						fanTempName  = ""
					else:
						fanTempName  = "" 
						fanTempDevId = (inp["fanTempDevId"])
						for pgmName in inp["sensors"]:
							for devId in inp["sensors"][pgmName]:
								if fanTempDevId == devId:
									fanTempName = pgmName
									break
							if fanTempName !="":
								break
			if fanTempName !="":
				if u"fanGPIOPin" in inp and (inp["fanGPIOPin"]) != "-1": 
					xx= int(inp["fanGPIOPin"])
					if xx > 0 and xx != fanGPIOPin: 
						fanGPIOPin = xx
						GPIO.setup(fanGPIOPin, GPIO.OUT)	
				if u"fanTempOnAtTempValue" in inp:
					fanTempOnAtTempValue= int(inp["fanTempOnAtTempValue"])

		
		doGPIOAfterBoot()


		if u"sleepAfterBoot" 				in inp:	 
			fixRcLocal(inp["sleepAfterBoot"])
		
		if u"bluetoothONoff"			 in inp:
			if bluetoothONoff != inp["bluetoothONoff"]:
				if inp["bluetoothONoff"].lower() =="on":
					os.system("rfkill unblock bluetooth")
					os.system("systemctl enable hciuart")
					time.sleep(20)
					U.sendRebootHTML("switch bluetooth back on ",reboot=True)
				else:
					if U.pgmStillRunning("/usr/lib/bluetooth/bluetoothd"):
						U.toLog(-1,"switching blue tooth stack off ")
						os.system("rfkill block bluetooth")
						os.system("systemctl disable hciuart")
						U.killOldPgm(myPID,"/usr/lib/bluetooth/bluetoothd")
				bluetoothONoff = inp["bluetoothONoff"]

		sensorList =""
		for sensor in sensors:
			sensorList+=sensor+","
		
		displayActive  = False
		neopixelActive = False
		neopixelClockActive = False
		if "output"				in inp:	 
			output=				  (inp["output"])

			for pp in ["setTEA5767","OUTPUTgpio","neopixelClock","display","neopixel","neopixelClock","sunDial","setStepperMotor"]:
				if pp in output:
						U.toLog(1, "setting "+pp+" ON") 
						if pp not in activePGM:
							if pp =="display":
								checkIfDisplayIsRunning()
							elif pp =="neopixel":
								checkIfNeopixelIsRunning(pgm= "neopixel")
							elif pp =="neopixelClock":
								checkIfNeopixelIsRunning(pgm= "neopixelClock")
							else:
								startProgam(pp+".py", params="", reason="restarting "+pp+"..not running")
						activePGM[pp] =True
				else:
					try: del activePGM[pp] 
					except: pass
					U.killOldPgm(-1, pp+".py")


		xx= {"spiMCP3008":"spiMCP3008","i2c":"simplei2csensors"}
		for pp in xx:
			pgm = xx[pp]
			if sensorList.find(pp) >-1:
					U.toLog(1, "setting {} ON".format(pgm)) 
					if pgm not in activePGM:
						startProgam(pgm+".py", params="", reason="restarting {}..not running".format(pgm))
					activePGM[pgm] =True
			else:
				try: del activePGM[pp] 
				except: pass
				U.killOldPgm(-1, pgm+".py")




		## check if socket port has changed, if yes do a reboot 
		pppp = 0
		if u"rPiCommandPORT"		in inp:	 pppp=		 (inp["rPiCommandPORT"])
		if str(rPiCommandPORT) !="0":
			if str(pppp) != str(rPiCommandPORT):
				time.sleep(10)
				U.sendRebootHTML("change_in_port")
		rPiCommandPORT = int(pppp)
				

		### for shutdown pins changes  we need to restart this program

		if u"shutDownPinVetoOutput"	  in inp:  
			xxx=				   int(inp["shutDownPinVetoOutput"])
			if shutDownPinVetoOutput !=-1 and xxx != shutDownPinVetoOutput: # is a change, not just switch on 
				U.toLog(-1, "restart master for new shutdown input pin", doPrint=True)
				os.system("/usr/bin/python "+G.homeDir+"master.py &" )
			if shutDownPinVetoOutput != xxx:
				shutDownPinVetoOutput=	   xxx
				if shutdownInputPin ==15 or shutdownInputPin==14:
					os.system("systemctl disable hciuart")
					time.sleep(1)
				if shutDownPinVetoOutput !=-1:
					GPIO.setup(shutDownPinVetoOutput, GPIO.OUT) # disable shutdown 
					GPIO.output(shutDownPinVetoOutput, True)    # set to high while running 


		if u"shutdownInputPin"	 in inp:  
			xxx=				   int(inp["shutdownInputPin"])
			if shutdownInputPin !=-1 and xxx != shutdownInputPin:  # is a change, not just switch on 
				U.toLog(-1, "restart master for new shutdown input pin", doPrint=True)
				os.system("/usr/bin/python "+G.homeDir+"master.py &" )
			if shutdownInputPin != xxx:
				shutdownInputPin=	  xxx
				if shutdownInputPin ==15 or shutdownInputPin==14:
					os.system("systemctl disable hciuart")
					time.sleep(1)
				if shutdownInputPin !=-1:
					GPIO.setup(int(shutdownInputPin), GPIO.IN, pull_up_down = GPIO.PUD_UP)	# use pin shutDownPin  to input reset


		if u"shutdownPinVoltSensor"	 in inp:  
			xxx=				   int(inp["shutdownPinVoltSensor"])
			if shutdownPinVoltSensor !=-1 and xxx != shutdownPinVoltSensor:  # is a change, not just switch on 
				U.toLog(-1, "restart master for new shutdown input pin", doPrint=True)
				os.system("/usr/bin/python "+G.homeDir+"master.py &" )
			if shutdownPinVoltSensor != xxx:
				shutdownPinVoltSensor=	  xxx
				if shutdownPinVoltSensor ==15 or shutdownPinVoltSensor==14:
					os.system("systemctl disable hciuart")
					time.sleep(1)
				GPIO.setup(int(shutdownPinVoltSensor), GPIO.IN, pull_up_down = GPIO.PUD_UP)	# use pin shutDownPin  to input reset


		if u"rebootWatchDogTime" in inp :
			xxx	  =int(inp["rebootWatchDogTime"])
			if U.pgmStillRunning("shutdownd"):
				if xxx <=0: os.system("shutdown -c >/dev/null 2>&1") 
			elif xxx != rebootWatchDogTime:
				rebootWatchDog()
			rebootWatchDogTime= xxx


		if "rPiRestartCommand"	in inp:	 rPiRestartCommand=	   (inp["rPiRestartCommand"])
		if inp["rPiRestartCommand"] !="":
			inp["rPiRestartCommand"] =""
			U.writeJson(G.homeDir+"parameters",inp, sort_keys=True, indent=2)
			#os.system("/usr/bin/python "+G.homeDir+ "copyToTemp.py")



		if	rPiRestartCommand.find("restartRPI") >-1:
			os.system("rm "+G.homeDir+"installLibs.done")
			U.sendURL(sendAlive="reboot")
			U.doReboot(10.,"re-loading everything due to request from parameter file")


		if	rPiRestartCommand.find("reboot") > -1:
			U.sendURL(sendAlive="reboot")
			U.doReboot(10.,"rebooting due to request from parameter file")


		if	rPiRestartCommand.find("master") > -1:
			U.toLog(-1,"restart due to new input {}".format(rPiRestartCommand), doPrint=True)
			os.system("/usr/bin/python "+G.homeDir+"master.py &" )
			sys.exit()

		time.sleep(1)

		setACTIVEorKILL("INPUTgpio","INPUTgpio.py","")
		setACTIVEorKILL("INPUTtouch","INPUTtouch.py","INPUTtouch")
		setACTIVEorKILL("INPUTtouch16","INPUTtouch16.py","INPUTtouch16")
		setACTIVEorKILL("INPUTRotarySwitchAbsolute","INPUTRotarySwitchAbsolute.py","INPUTRotarySwitchAbsolute")
		setACTIVEorKILL("INPUTRotarySwitchIncremental","INPUTRotarySwitchIncremental.py","INPUTRotarySwitchIncremental")
	

		setACTIVEorKILL("myprogram","myprogram.py","")
		setACTIVEorKILL("mysensors","mysensors.py","")

				
		#print " sensors:", sensors
		U.toLog(0, "sensors		  : " +	 sensorList)

		for ss in G.specialSensorList:
			if	ss in sensors: 
				checkifActive(ss, ss+".py", True)
		
		if	(rPiRestartCommand.find("rPiCommandPORT") >-1) and G.wifiType =="normal" and G.networkType !="clockMANUAL" and rPiCommandPORT >0:
				startProgam("receiveCommands.py", params=str(rPiCommandPORT), reason=" restart requested from plugin")

		if	not beforeLoop:
			if rPiRestartCommand.find("beacons") >-1 :
					U.killOldPgm(-1,"beaconloop.py")
					checkIfAliveFileOK("beaconloop",force="set")
					startProgam("beaconloop.py", params="", reason=" at startup ")

		sensorEnabled =copy.copy(sensorList)
		firstRead = False
		return 

####################      #########################
def setACTIVEorKILL(tag,pgm,check,force=0):
	global sensors, activePGMdict
	#print tag, sensorList
	try:
		theList=""
		for sensor in sensors:
			theList+=sensor.split("-")[0]+","
		#print theList
		if	(tag in theList and tag not in activePGMdict) or force==1:
			activePGMdict[tag]=[pgm,check]
			startProgam(pgm, params="", reason=" at startup ")
			checkifActive(tag, pgm, True)
			U.toLog(-1,"started:%s"%pgm, doPrint= True)
		elif ( tag not in theList and tag in  activePGMdict) or force==-1:
			U.killOldPgm(-1,pgm)
			U.toLog(-1,"stopping sensor as no {} enabled".format(tag), doPrint=True)
			if tag	in activePGMdict: del activePGMdict[tag] 
		elif tag  in activePGMdict and force ==0:
			del activePGMdict[tag] 
	except	Exception, e:
		U.toLog(-1, u"in Line {} has error={}".format(sys.exc_traceback.tb_lineno, e))





####################      #########################
def doWeNeedToStartTouch(sensors,sensorsOld):
	try:
		for sensor in sensors:
			for n in range(30):
				sensor="INPUTtouch12-"+str(n)
				if sensor not in sensors: continue
				if sensor not in sensorsOld: return 1
				for devId  in sensors[sensor]:
					if "gpio" not in sensors[sensor][devId]: continue
					if devId not in sensorsOld[sensor]: return 1
					ss = sensors[sensor][devId]["gpio"]
					if ss not in sensorsOld[sensor][devId]: return 1
					for nn in range(len(ss)):
						if "gpio" not in ss[nn]: return 1
				U.toLog(1, "enabled sensor " +sensor)
		return 0
	except	Exception, e:
		U.toLog(-1, u"in Line {} has error={}".format(sys.exc_traceback.tb_lineno, e))
		U.toLog(-1,"start INPUTtouch12: "+ unicode(sensors))
	return 0



####################      #########################
def checkifActive(sensorName, pyName, active):
	if active:
		checkIfPGMisRunning(pyName,force=True, checkAliveFile=sensorName )
		checkIfAliveFileOK(sensorName)
	else:
		U.killOldPgm(1,pyName)
	return 



#########  start pgms  
def installLibs():
	if U.pgmStillRunning("installLibs.py"): return
	os.system("/usr/bin/python "+G.homeDir+"installLibs.py ") # wait until finished

	
####################      #########################
def startProgam(pgm, params="", reason=""):
	U.toLog(1, ">>>> starting "+pgm+" "+reason	  )
	os.system("/usr/bin/python "+G.homeDir+pgm+" "+params+" &")


####################      #########################
def startBLEconnect():
	global sensors, BLEserial, BLEserialOLD
	try:
		##print BLEserial, BLEserialOLD
		if "BLEconnect" not in sensors:
			U.killOldPgm(-1, "BLEconnect.py")
			return

		if BLEserial !=	 BLEserialOLD:
			BLEserialOLD = BLEserial
			U.killOldPgm(-1, "BLEconnect.py")

		if BLEserial == "sequential":
			if not U.pgmStillRunning("BLEconnect.py") :
				startProgam("BLEconnect.py", params="", reason="..starting in serial mode ")
			return

		if BLEserial == "parallel":
			for	 dev in sensors["BLEconnect"]:
				mac=sensors["BLEconnect"][dev]["macAddress"]
				##print "mac", mac
				if len(mac) < 5: continue
				if not U.pgmStillRunning("BLEconnect.py "+mac):
					startProgam("BLEconnect.py", params=mac, reason="..starting in parallel mode ")
	except	Exception, e :
		U.toLog(-1, u"in Line {} has error={}".format(sys.exc_traceback.tb_lineno, e), doPrint=True)
	return


####################      #########################
def startBLEsensor():
	global sensors
	try:
		if "BLEsensor" not in sensors:
			U.killOldPgm(-1, "BLEsensor.py")
			return
		if not U.pgmStillRunning("BLEsensor.py"):
			startProgam("BLEsensor.py", params="", reason="")
	except	Exception, e :
		U.toLog(-1, u"in Line {} has error={}".format(sys.exc_traceback.tb_lineno, e), doPrint=True)
	return

	
########## check if programs are running	 
	


####################      #########################
def checkIfDisplayIsRunning():
	tt = time.time()
	if tt-G.tStart< 15: return
	
	try:
		if not U.pgmStillRunning("display.py"):
			startProgam("display.py", params="", reason="..not running ")
			checkIfAliveFileOK("display",force="set")
			return
		if not checkIfAliveFileOK("display"):
			startProgam("display.py", params="", reason="..not sending alive signal")
			checkIfAliveFileOK("display",force="set")
			return
		if os.path.isfile(G.homeDir+"temp/display.inp") and os.path.getsize(G.homeDir+"temp/display.inp") > 50000:
			startProgam("display.py", params="", reason=" ..display.inp file too big")
			checkIfAliveFileOK("display",force="set")
			return
	except	Exception, e :
		U.toLog (-1, u"in Line {} has error={}".format(sys.exc_traceback.tb_lineno, e))
		return
	return




####################      #########################
def checkIfNeopixelIsRunning(pgm= "neopixel"):
	global lastcheckIfNeopixelIsRunning
	tt = time.time()
	if tt-G.tStart< 5: return
	try: ii = lastcheckIfNeopixelIsRunning
	except: lastcheckIfNeopixelIsRunning = 0
	if tt - lastcheckIfNeopixelIsRunning < 30: return 
	lastcheckIfNeopixelIsRunning = tt
	try:
		U.toLog (1, u"checking if  {} running".format(pgm))
		if not U.pgmStillRunning(pgm+".py"):
			U.toLog (1, u"restarting  {}".format(pgm))
			startProgam(pgm+".py", params="", reason="..not running ")
			checkIfAliveFileOK(pgm,force="set")
			return
		if not checkIfAliveFileOK("neopixel"):
			startProgam(pgm+".py", params="", reason="..not sending alive signal")
			checkIfAliveFileOK("neopixel",force="set")
			return
		if os.path.isfile(G.homeDir+"temp/neopixel.inp") and os.path.getsize(G.homeDir+"temp/neopixel.inp") > 50000:
			startProgam("neopixel.py", params="", reason=" ..neopixel.inp file too big")
			checkIfAliveFileOK("neopixel",force="set")
			return
	except	Exception, e :
		U.toLog (-1, u"in Line {} has error={}".format(sys.exc_traceback.tb_lineno, e))
		return
	return



####################      #########################
def checkIfPGMisRunning(pgmToStart,force=False,checkAliveFile="", parameters=""):
	tt = time.time()
	if tt-G.tStart< 15 and not force: return
	try:
		if not U.pgmStillRunning(pgmToStart):
			startProgam(pgmToStart, params=parameters, reason="restarting "+pgmToStart+"..not running")
			return
		if checkAliveFile !="":
			alive = checkIfAliveFileOK(checkAliveFile)
			#print "pgm to start", pgmToStart, checkAliveFile, alive
			if not alive:
				startProgam(pgmToStart, params="", reason="restarting "+pgmToStart+"..not running .. no alive file")
				return

	except	Exception, e :
		U.toLog (-1, u"in Line {} has error={}".format(sys.exc_traceback.tb_lineno, e))
	return


####################      #########################
def checkIfbeaconLoopIsRunning():
	global	sensorList, enableRebootCheck, enableiBeacons, sensorAlive, sensors, lastAlive
	try:
		#print "checking beaconloop running start of pgm"
		tt = time.time()
		if tt-G.tStart< 10: return
		
		if U.pgmStillRunning("installLibs.py"): return


		#print "checking beaconloop running 0"
		if enableRebootCheck.find("restartLoop")>-1  or enableRebootCheck.find("rebootLoop") >-1:
			#print "checking beaconloop running 1"
			if	not checkIfAliveFileOK("beaconloop"):
				#print "checking beaconloop running 2"
			
				if	enableRebootCheck.find("rebootLoop") >-1:
					U.sendURL(sendAlive="reboot")
					time.sleep(20)
					U.doReboot(10.," Seconds since change in alive file :"+ str(tt- lastAlive["beaconloop"]) +" -- rebooting ")

				#print "checking beaconloop running 3"
				U.killOldPgm(-1,"beaconloop.py")
				checkIfAliveFileOK("beaconloop",force="set")
				startProgam("beaconloop.py", params="", reason=" restart requested by plugin ")
			return

		#print "checking beaconloop running 4"
		if not checkIfAliveFileOK("beaconloop"):
					#print "checking beaconloop running	 alive file not ok"
					U.killOldPgm(-1,"beaconloop.py")
					checkIfAliveFileOK("beaconloop",force="set")
					#print "checking if beaconloop running: are starting beaconlooop"
					startProgam("beaconloop.py", params="", reason=" alive file is old ")

	except	Exception, e:
		U.toLog(-1, u"in Line {} has error={}".format(sys.exc_traceback.tb_lineno, e), doPrint=True)
	return



####################      #########################
def checkIfAliveFileOK(sensor,force=""):
	global sensorAlive
	alive = True 
	tt = time.time()	
	if	tt - G.tStart < 20 and force =="": return alive
	if force =="set":
		sensorAlive[sensor]=time.time()
		return alive
		
	data =0
	try:
		if sensor not in sensorAlive: sensorAlive[sensor]=0
		
		try:
			data =""
			try:
				f = open(G.homeDir+"temp/alive."+sensor,"r")
				data =f.read()
				data =data.strip("\n")
				lastUpdate=float(data)
				f.close()
				#print "alive test 1 for " , sensor,  lastUpdate
			except	Exception, e:
				#print " exception ",sys.exc_traceback.tb_lineno, e
				time.sleep(0.2)
				if os.path.isfile(G.homeDir+"temp/alive."+sensor):
						f = open(G.homeDir+"temp/alive."+sensor,"r")
						data =f.read()
						data =data.strip("\n")
						lastUpdate=float(data)
						f.close()
				else:
					#print " alive file for ", sensor, " not found"
					##os.system("ls -l "+G.homeDir+"temp/")
					lastUpdate=0
					try:f.close()
					except: pass

		except	Exception, e:
			U.toLog(-1, u"(2) in Line {} has error={}".format(sys.exc_traceback.tb_lineno, e), doPrint=True)
			lastUpdate=0
		#print "alive test 2 for " , sensor, data
			
	   # dont do anything directly after midnight
		dd = datetime.datetime.now()
		if dd.hour == 0 and dd.minute < 10: return alive
 

		#print " alive test 2  delta T",tt - lastUpdate 
		if tt - lastUpdate > 240:  ## nothing for 4 min signal: no alive
			alive = False
		sensorAlive[sensor] = lastUpdate
	except	Exception, e:
		U.toLog(-1, u"(3) in Line {} has error={}".format(sys.exc_traceback.tb_lineno, e), doPrint=True)
	return alive






####################      #########################
def checkDiskSpace(maxUsedPercent=90,kbytesLeft=500000): # check if enough disk space  left (min 10% or 500Mbyte)
	try:
		ret=subprocess.Popen("df" ,shell=True,stdout=subprocess.PIPE,stderr=subprocess.PIPE).communicate()[0]
		lines = ret.split("\n")
		retCode=0
		for line in lines:
			if line.find("/dev/root") > -1:
				items = line.split()
				try:
					kbytesAvailable = int(items[3])
					usedPercent=int(items[4].strip("%"))
					if	usedPercent > maxUsedPercent and kbytesAvailable < kbytesLeft : retCode= 1
				except:
					return 0
			if line.find("/var/log") > -1: # for temp disks
				items = line.split()
				try:
					bytesAvailable = int(items[3])
					usedPercent=int(items[4].strip("%"))
					if	usedPercent > 90 or bytesAvailable < 4000 : retCode= 2 ## 90% or 4 Mbyte
				except:
					return 0
			if line.find("/run/user/") > -1: # for temp disks
				items = line.split()
				try:
					bytesAvailable = int(items[3])
					usedPercent=int(items[4].strip("%"))
					if	usedPercent > 90 or bytesAvailable < 4000 : retCode= 2 ## 90% or 4 Mbyte
				except:
					return 0

		return retCode
	except	Exception, e :
		U.toLog (-1, u"in Line {} has error={}".format(sys.exc_traceback.tb_lineno, e))


####################      #########################
def rebootWatchDog():
	global rebootWatchDogTime
	try:

		if rebootWatchDogTime <=0:
			if U.pgmStillRunning("shutdownd"):
				os.system("shutdown -c >/dev/null 2>&1")
			return


		if U.pgmStillRunning("shutdownd"):
			os.system("shutdown -c >/dev/null 2>&1")
			time.sleep(0.1)
			os.system("shutdown +"+str(rebootWatchDogTime)+" >/dev/null 2>&1")



	except	Exception, e :
		U.toLog (-1, u"in Line {} has error={}".format(sys.exc_traceback.tb_lineno, e))


####################      #########################
def checkIfRebootRequest():
	###print "into checkIfRebootRequest"
	if	os.path.isfile(G.homeDir+"temp/rebootNeeded"):
		f=open(G.homeDir+"temp/rebootNeeded") 
		reason = f.read()
		f.close()
		os.remove(G.homeDir+"temp/rebootNeeded")
		if reason.find("noreboot")>-1:
			U.toLog(-1, " sending message to plugin re:{}".format(reason) , doPrint=True)
			U.sendURL(sendAlive="alive",text=reason)
		else:
			U.toLog(-1, " rebooting due to request:{}".format(reason), doPrint=True)
			time.sleep(50)
			U.sendRebootHTML(reason)
			U.doRebootThroughRUNpinReset()


	#print "into checkIfRebootRequest restartNeeded" , os.path.isfile(G.homeDir+"temp/restartNeeded")
	if	os.path.isfile(G.homeDir+"temp/restartNeeded"):
		#print "into checkIfRebootRequest restartNeeded" , os.path.isfile(G.homeDir+"temp/restartNeeded")
		f=open(G.homeDir+"temp/restartNeeded","r") 
		reason = f.read()
		f.close()
		os.remove(G.homeDir+"temp/restartNeeded")
		if reason.find("bluetooth_startup")>-1:
			count = 0
			if	os.path.isfile(G.homeDir+"temp/restartCount"):
				try:
					f=open(G.homeDir+"temp/restartCount","r") 
					count = int(f.read())
					f.close()
					if count > 5: 
						os.remove(G.homeDir+"temp/restartCount")
						U.toLog(-1, " rebooting due to repeated request:{}".format(reason), doPrint=True)
						U.doReboot(20," rebooting due to repeated request:{}".format(reason))
				except: pass
				
			f=open(G.homeDir+"temp/restartCount","w") 
			f.write(str(count+1))
			f.close()
			U.toLog(-1, " starting master due to request:" + reason , doPrint=True)
			U.restartMyself()
			

####################      #########################
def checkIfNightReboot():
	global rebootHour,rebooted


	#print "rebootHour", rebootHour, "rebooted", rebooted,	" hour=",datetime.datetime.now().hour, "true? ",datetime.datetime.now().hour == rebootHour
	if rebootHour < 0:						 return
	if rebooted:							 return
	nn = datetime.datetime.now()
	if nn.hour	  != rebootHour:			 return
	# time window for reboot 2 minutes with some ramdom # added(pi# =0...19)
	#print "rebootHour", nn.minute,	 int(G.myPiNumber)*2,  int(G.myPiNumber)*2+1
	if nn.minute  <	 int(G.myPiNumber)*2:	 return 
	if nn.minute  >	 int(G.myPiNumber)*2+1 : return 
	U.toLog (-1, "re booting", doPrint=True )

	rebooted = True
	time.sleep(30)
	U.sendRebootHTML("regular_reboot_at_" +str(rebootHour) +"_hours_requested ")
 
	U.doRebootThroughRUNpinReset()



####################      #########################
def checkIfShutDownVoltage():
	global shutdownInputPin, shutdownPinVoltSensor,  batteryMinPinActiveTimeForShutdown, inputPinVoltRawLastONTime
	global batteryChargeTimeForMaxCapacity, batteryCapacitySeconds
	global  batteryStatus,lastWriteBatteryStatus
	#print " checkIfShutDownVoltage into"
	try:
		ii = lastWriteBatteryStatus
	except:
		try:
			lastWriteBatteryStatus =0
			#print "checkIfShutDownVoltage initializing"
			batteryStatus, raw= U.readJson(G.homeDir+"batteryStatus")
			delItem=[]
			for item in batteryStatus:
				if item not in ["timeCharged", "testTime","percentCharged","inputPinVoltRawLastONTime","batteryTimeLeftEndOfCharge","status","batteryCapacitySeconds","batteryChargeTimeForMaxCapacity","batteryMinPinActiveTimeForShutdown", "batteryTimeLeft"]:
					delItem.append(item)
			for item in delItem:
				del batteryStatus[item]
			for item in ["timeCharged", "testTime","percentCharged","inputPinVoltRawLastONTime","batteryTimeLeftEndOfCharge","status","batteryCapacitySeconds","batteryChargeTimeForMaxCapacity","batteryMinPinActiveTimeForShutdown", "batteryTimeLeft"]:
				if item not in batteryStatus:
					batteryStatus[item] =0
	
			if shutdownPinVoltSensor != -1:
				#print	"setting shutdownPinVoltSensor to GPIO: " + str(shutdownPinVoltSensor) 
				U.toLog(-1, "setting shutdownPinVoltSensor to GPIO: {}".format(shutdownPinVoltSensor), doPrint=True)
				try: GPIO.setup(int(shutdownPinVoltSensor), GPIO.IN, pull_up_down = GPIO.PUD_UP)	# use pin shutDownPin  to input reset
				except: pass
				inputPinVoltRawLastONTime = time.time()
		except: pass
		if batteryStatus =={}: 
			batteryStatus ={"timeCharged":0, "testTime":time.time(),"percentCharged":0,"inputPinVoltRawLastONTime":0,"batteryTimeLeftEndOfCharge":0,"status":"","batteryCapacitySeconds":0,"batteryChargeTimeForMaxCapacity":0,"batteryMinPinActiveTimeForShutdown":0,"batteryTimeLeft":0}
	try:
		#print "batteryStatus ", batteryStatus
		batteryStatus["batteryChargeTimeForMaxCapacity"] 			= batteryChargeTimeForMaxCapacity
		batteryStatus["batteryCapacitySeconds"] 			= batteryCapacitySeconds
		batteryStatus["batteryMinPinActiveTimeForShutdown"]		= batteryMinPinActiveTimeForShutdown
		for ii in range(2):
			if GPIO.input(int(shutdownPinVoltSensor)) == 1:
				batteryStatus["timeCharged"] 						+= (time.time() - batteryStatus["testTime"]) 
				batteryStatus["timeCharged"]						= round(min(batteryStatus["timeCharged"],batteryChargeTimeForMaxCapacity),5) # x hour charge time should get to 90+%
				batteryStatus["inputPinVoltRawLastONTime"]			= round(time.time(),5)
				batteryStatus["testTime"]							= round(time.time(),5)
				batteryStatus["percentCharged"] 					= round(max( 0, batteryStatus["timeCharged"] /batteryChargeTimeForMaxCapacity ),5)
				batteryStatus["batteryTimeLeftEndOfCharge"]			= round(min(batteryMinPinActiveTimeForShutdown, batteryCapacitySeconds*batteryStatus["percentCharged"]),5)
				if batteryStatus["percentCharged"] ==1:				  batteryStatus["status"]	= "charged"
				else:  												  batteryStatus["status"]	= "charging"
				batteryStatus["batteryTimeLeft"]					= batteryStatus["batteryTimeLeftEndOfCharge"]
				lastWriteBatteryStatus= writeJson2(batteryStatus,G.homeDir+"batteryStatus", lastWriteBatteryStatus)
				#print "checkIfShutDownVoltage normal return"
				return
			time.sleep(0.1)

		batteryStatus["batteryTimeLeftEndOfCharge"]		= round(min(batteryMinPinActiveTimeForShutdown, batteryCapacitySeconds*batteryStatus["percentCharged"]),5)
		batteryStatus["timeCharged"] 					= round(batteryStatus["timeCharged"] * max( 0, 1. -  (time.time()-batteryStatus["testTime"])/max(1,batteryCapacitySeconds)  ),5)#discharging
		batteryStatus["testTime"] 						= round(time.time(),5)
		batteryStatus["batteryTimeLeft"] 				= round( (batteryStatus["inputPinVoltRawLastONTime"] + batteryStatus["batteryTimeLeftEndOfCharge"]) - time.time(),5)
		if batteryStatus["batteryTimeLeft"] >0: 
			batteryStatus["status"]						= "dis-charging"
			lastWriteBatteryStatus= writeJson2(batteryStatus,G.homeDir+"batteryStatus", lastWriteBatteryStatus)
			U.toLog (-1, "checkIfShutDownVoltage discharging ", doPrint=True)
			return 

		batteryStatus["status"]							= "empty"
		lastWriteBatteryStatus= writeJson2(batteryStatus,G.homeDir+"batteryStatus", 0)

	except	Exception, e :
			U.toLog (-1, u"in Line {} has error={}".format(sys.exc_traceback.tb_lineno, e), doPrint=True)
			return
	U.toLog (-1, "checkIfShutDownVoltage rebooting ", doPrint=True )
	U.sendRebootHTML("battery empty", reboot=False)

	return 

####################      #########################
def writeJson2(data,fileName,lastWriteBatteryStatus):
	try:
		if time.time() - lastWriteBatteryStatus < 20: return lastWriteBatteryStatus
		U.writeJson(fileName, data,sort_keys=True, indent=0)
	except: pass
	return time.time()
	


####################      #########################
def checkLogfiles():
	global useRamDiskForLogfiles
	try:
		if os.path.isfile(G.homeDir+"permanentLog.log") and	 os.path.getsize(G.homeDir+"permanentLog.log") > 20000:
			os.system("rm "+G.homeDir+"permanentLog.log")	 
	except: pass

	if not os.path.isfile(G.logDir+"piBeacon.log"): return 
	nBytes = os.path.getsize(G.logDir+"piBeacon.log")
	if nBytes > 30000000: # 30 mbytes
		if  os.path.isfile(G.logDir+"piBeacon-1.log"):  
			os.system("sudo rm "+G.logDir+"piBeacon-1.log ")
		os.system("sudo mv "+G.logDir+"piBeacon.log "+G.logDir+"piBeacon-1.log ")


	if checkDiskSpace(maxUsedPercent=80,kbytesLeft=500000) == 0: return	 # (need 500Mbyte free or 80%
	U.toLog(-1, "delete logfiles  due to  limited disk space ", doPrint=True)
	os.system("sudo rm /var/log/*")
	os.system("sudo rm "+G.logDir+"*")
	if checkDiskSpace(maxUsedPercent=80,kbytesLeft=500000) == 0: return	 # (need 500Mbyte free or 80%
	U.doRebootThroughRUNpinReset()



####################      #########################
def checkRamDisk():
		global useRamDiskForLogfiles
		ret=subprocess.Popen("df" ,shell=True,stdout=subprocess.PIPE,stderr=subprocess.PIPE).communicate()[0]
		lines = ret.split("\n")
	  
		ramDiskActive = False
		for line in lines:
			if line.find("/var/log") == -1:continue
			ramDiskActive = True
			break
			
		if useRamDiskForLogfiles=="1" and not ramDiskActive: 
			if	U.checkIfInFile(["tmpfs","/var/log"],"/etc/fstab") ==1:
				U.uncommentOrAdd("tmpfs	  /var/log	  tmpfs	   defaults,noatime,nosuid,mode=0755,size=60m	 0 0","/etc/fstab")
				U.toLog(-1," master need to reboot, added ram disk for /var/log ", doPrint=True)
				return True
		if useRamDiskForLogfiles=="0" and ramDiskActive: 
			if	U.checkIfInFile(["tmpfs","/var/log"],"/etc/fstab") ==1:
				U.removefromFile("tmpfs /var/log","/etc/fstab")
				U.toLog(-1," master need to reboot, removed ram disk for /var/log ", doPrint=True)
				return True
		return False




####################      #########################
def delayAndWatchDog():
	global shutdownInputPin, lastshutdownInputPinTime, shutdownPinVoltSensor, rebootWatchDogTime,lastrebootWatchDogTime

	try:
		for xx in range(20): # thats 20 seconds
			time.sleep(1)
			tt = time.time()

			if shutdownPinVoltSensor >1 and  tt - G.tStart > 20:
				checkIfShutDownVoltage()

			if shutdownInputPin >1 :
				if GPIO.input(shutdownInputPin) == 1: 
					lastshutdownInputPinTime = tt

				### print "master: shutdown pin #%d;  secs pressed:%.1f"%(shutdownInputPin,tt - lastshutdownInputPinTime )
				if tt - G.tStart > 20  and tt - lastshutdownInputPinTime > 3:
					 U.doReboot(10, "shudown pin pressed", cmd="sudo sync; wait 2; sudo shutdown now")

			if xx%5 ==1 and False:
				if	os.path.isfile("/run/nologin"):
					os.system("rm /run/nologin &")

				if	rebootWatchDogTime > 0 and tt - lastrebootWatchDogTime > (rebootWatchDogTime*60 -20.): # rebootWatchDogTime is in minutes
					lastrebootWatchDogTime = tt
					rebootWatchDog()
					
	except	Exception, e :
		U.toLog (-1, u"in Line {} has error={}".format(sys.exc_traceback.tb_lineno, e))



####################      #########################
def checkSystemLOG():
	global lastcheckSystemLOG, rememberLineSystemLOG
	try: 
		xx = lastcheckSystemLOG
	except: 
		lastcheckSystemLOG=0
		rememberLineSystemLOG =[]
	
	tt = int(time.time())
	if (tt - lastcheckSystemLOG) < 25:
		return
	lastcheckSystemLOG = tt
	try:
		out = subprocess.Popen("tail -300 /var/log/syslog " ,shell=True,stdout=subprocess.PIPE,stderr=subprocess.PIPE).communicate()
		if out[1].find("tail: cannot open ") >-1 :
			out = subprocess.Popen("logread | tail -100 " ,shell=True,stdout=subprocess.PIPE,stderr=subprocess.PIPE).communicate()
			if out[1] !="": return 
		out= out[0]
		if out.find("REGISTER DUMP") > -1:
			lines = out.split("\n")
			for line in lines:
				if len(line) < 53: continue
				if line.find(" DUMP ") > -1:
					if line[0:50] in rememberLineSystemLOG: continue
					rememberLineSystemLOG.append(line[0:50])
					if len(rememberLineSystemLOG) ==1: # do not send  the first occurence
						continue 
					if len(rememberLineSystemLOG) > 5: # only remember the first 5 
						rememberLineSystemLOG.pop(0)
					U.toLog(1, "sending message to plugin re:" + line ,doPrint=False)
					U.sendURL(sendAlive="alive",text="checkSystemLOG_register_dump_occured_noreboot_"+line)
			
	except	Exception, e :
		U.toLog (-1, u"in Line {} has error={}".format(sys.exc_traceback.tb_lineno, e))


####################      #########################
def cycleWifi():
	eth0IP, wifi0IP, G.eth0Enabled, G.wifiEnabled = U.getIPCONFIG()
	#print "master:	 is wifi enabled : "+str(G.wifiEnabled)
	if G.wifiEnabled:
		if U.getIPNumberMaster()> 0:
			#print "master:	 cycle wlan0"
			os.system("sudo /sbin/ifconfig wlan0 down; sudo /sbin/ifconfig wlan0 up")  # cycle wlan
	return

####################      #########################
def doGPIOAfterBoot():
	global GPIOTypeAfterBoot1, GPIOTypeAfterBoot2, GPIONumberAfterBoot1, GPIONumberAfterBoot2, alreadyBooted


	f=open(G.homeDir+"doGPIOatStartup.py","w")

	f.write("#!/usr/bin/env python\n")
	f.write("# -*- coding: utf-8 -*-\n")
	f.write("#  called from callbeacon.py BEFORE master.py  to set GPIO in or output QUICKLY after boot \n")
	f.write("import RPi.GPIO as GPIO\n")
	f.write("GPIO.setwarnings(False)\n")
	f.write("GPIO.setmode(GPIO.BCM)\n")
	if GPIOTypeAfterBoot1 != "off": 
		if GPIONumberAfterBoot1 != "-1" and GPIONumberAfterBoot1 != "":
			if GPIOTypeAfterBoot1 =="Ohigh":
				f.write("GPIO.setup("+str(GPIONumberAfterBoot1)+", GPIO.OUT, initial=GPIO.HIGH)\n")
			if GPIOTypeAfterBoot1 =="Olow":
				f.write("GPIO.setup("+str(GPIONumberAfterBoot1)+", GPIO.OUT, initial=GPIO.LOW)\n")
			if GPIOTypeAfterBoot1.find("Iup") ==0:
				f.write("GPIO.setup("+str(GPIONumberAfterBoot1)+", GPIO.IN, pull_up_down = GPIO.PUD_UP)\n")
			if GPIOTypeAfterBoot1.find("Idown") ==0:
				f.write("GPIO.setup("+str(GPIONumberAfterBoot1)+", GPIO.IN, pull_up_down = GPIO.PUD_DOWN)\n")
			if GPIOTypeAfterBoot1.find("Ifloat") ==0:
				f.write("GPIO.setup("+str(GPIONumberAfterBoot1)+", GPIO.IN)\n")

	if GPIOTypeAfterBoot2 != "off": 
		if GPIONumberAfterBoot2 != "-1" and GPIONumberAfterBoot2 != "":
			if GPIOTypeAfterBoot2 =="Ohigh":
				f.write("GPIO.setup("+str(GPIONumberAfterBoot2)+", GPIO.OUT, initial=GPIO.HIGH)\n")
			if GPIOTypeAfterBoot2 =="Olow":
				f.write("GPIO.setup("+str(GPIONumberAfterBoot2)+", GPIO.OUT, initial=GPIO.LOW)\n")
			if GPIOTypeAfterBoot2.find("Iup") ==0:
				f.write("GPIO.setup("+str(GPIONumberAfterBoot2)+", GPIO.IN, pull_up_down = GPIO.PUD_UP)\n")
			if GPIOTypeAfterBoot2.find("Idown") ==0:
				f.write("GPIO.setup("+str(GPIONumberAfterBoot2)+", GPIO.IN, pull_up_down = GPIO.PUD_DOWN)\n")
			if GPIOTypeAfterBoot2.find("Ifloat") ==0:
				f.write("GPIO.setup("+str(GPIONumberAfterBoot2)+", GPIO.IN)\n")
	f.write("\n")

	f.close()

	return


	
	
####################      #########################
def checkTempForFanOnOff(force = False):
	global fanGPIOPin, fanTempOnAtTempValue, lastTempValue, lastTimeTempValueChecked, fanTempName, fanTempDevId, fanEnable
	try:
		#print "into checkTempForFanOnOff",fanTempName, fanTempDevId, fanEnable, fanTempOnAtTempValue, lastTimeTempValueChecked, lastTempValue
		#U.toLog (-1, u"checkTempForFanOnOff fanEnable:{}  fanTempName:{}   fanGPIOPin:{}".format(fanEnable, fanTempName, fanGPIOPin), doPrint=True)
		if not(fanEnable =="0" or fanEnable =="1"):						return
		if fanTempName   =="": 											return
		if int(fanGPIOPin) < -1: 										return

		tt0 = time.time()
		if ( tt0 - lastTimeTempValueChecked  < 5) and not force:		return

		if fanTempName   == "internal":
			tempInfo = subprocess.Popen("/opt/vc/bin/vcgencmd measure_temp" ,shell=True,stdout=subprocess.PIPE,stderr=subprocess.PIPE).communicate()[0]
			try:	temp = float(tempInfo.split("=")[1].split("'")[0])
			except: temp = 0.

		else:		

			if not os.path.isfile(G.homeDir+"temp/"+fanTempName+".dat"):	return

			rr , raw = U.readJson(G.homeDir+"temp/"+fanTempName+".dat")
			if rr == {}:
				time.sleep(0.1)
				rr, raw = U.readJson(G.homeDir+"temp/"+fanTempName+".dat")
			lastTimeTempValueChecked = tt0


			if rr == {} : 													return
			if fanTempDevId not in rr : 									return
			if "temp" not in rr[fanTempDevId]: 								return
			temp = float(rr[fanTempDevId]["temp"])
			if temp == lastTempValue:										return 

		#U.toLog (-1, u"checkTempForFanOnOff temp:{}  fanTempOnAtTempValue:{}".format(temp, fanTempOnAtTempValue), doPrint=True)

		if temp > fanTempOnAtTempValue: 
			#print " fan on"
			if  lastTempValue < fanTempOnAtTempValue: 
				if fanEnable =="1": GPIO.output(fanGPIOPin, True)
				if fanEnable =="0": GPIO.output(fanGPIOPin, False)
		else:
			#print " fan off"
			if  lastTempValue > fanTempOnAtTempValue or lastTempValue ==-1: 
				if fanEnable =="0": GPIO.output(fanGPIOPin, True)
				if fanEnable =="1": GPIO.output(fanGPIOPin, False)

		lastTempValue = temp


	except	Exception, e :
		U.toLog (-1, u"checkTempForFanOnOff in Line {} has error={}".format(sys.exc_traceback.tb_lineno, e), doPrint=True)
	return

	
	
####################      #########################
def fixRcLocal(sleepTime):

	if not os.path.isfile(G.homeDir+"/etc/rc.local"):
		os.system("cp  /etc/rc.local /home/pi/pibeacon/rc.local")

	f=open("/etc/rc.local","r")
	rclocal = f.read().split("\n")
	f.close()

	out      = ""
	writeOut = False
	test     = ""
	for line in rclocal:
		if line.find("/home/pi/callbeacon.py")>-1:
			test ="(python /home/pi/callbeacon.py &)"
			if line == test:
				break
			else:
				out+=test+"\n"
				writeOut= True
		else:
			out+=line+"\n"

	if writeOut:
		U.toLog(-1, "writing new rc.local file with new line:\n {}".format(test), doPrint=True)
		f=open("/etc/rc.local","w")
		f.write(out)
		f.close()


	f=open("/home/pi/pibeacon/callbeacon.py","r")
	callbeacon = f.read().split("\n")
	f.close()

	out      = ""
	writeOut = False
	test     = ""
	for line in callbeacon:
		if line.find("/usr/bin/python /home/pi/pibeacon/master.py")>-1:
			if sleepTime =="0":
				test = 'os.system("cd /home/pi/pibeacon; /usr/bin/python /home/pi/pibeacon/master.py & ")'
			else:
				test = 'os.system("sleep '+sleepTime+'; cd /home/pi/pibeacon; python /home/pi/pibeacon/master.py &")'
			if line == test:
				break
			else:
				out+=test+"\n"
				writeOut= True
		else:
			out+=line+"\n"

	if writeOut:
		f=open("/home/pi/pibeacon/callbeacon.py","w")
		f.write(out)
		f.close()

	## updating callbeacon file 
	U.toLog(-1, "writing new callbeacon.py file", doPrint=True)
	os.system("cp /home/pi/pibeacon/callbeacon.py /home/pi/callbeacon.py")
	return



####################      #########################
def checkFSCHECKfile():
	
	try:
		f=open(G.homeDir+"temp/dosfsck","r")
		data = f.read()
		f.close()
		if data.find("data may be corrupt") >-1: # try again, see if fixed..
			dataSend = u"dosfsck has error (was fixed after boot): "+"/--/".join((data.split("\n"))[0:10])
			os.system("dosfsck -w -r -l -a -v -t /dev/mmcblk0p1 > "+G.homeDir+"temp/dosfsck")
			f=open(G.homeDir+"temp/dosfsck","r")
			data = f.read()
			f.close()
			if data.find("data may be corrupt") >-1: # not fixed, send msg to plugin 
				dataSend = u"dosfsck has error also after re-run: "+ "/--/".join((data.split("\n"))[0:10])

			U.toLog (-1, dataSend, doPrint=True)
			U.sendURL(sendAlive="alive",text=dataSend)
	except	Exception, e :
		U.toLog (-1, u"checkFSCHECKfile in Line {} has error={}".format(sys.exc_traceback.tb_lineno, e), doPrint=True)

	return 


		
####################      #########################
#################### main #########################
####################      #########################

### artificial indent to indicate main program 
if True:

	global enableRebootCheck,myPID,restart,sensorList,rPiCommandPORT,firstRead
	global rebootWatchDogTime, lastrebootWatchDogTime
	global sensorEnabled,  restart, enableiBeacons, beforeLoop,iPhoneMACList,rebootHour,rebooted,BLEserial,BLEserialOLD
	global lastAliveultrasoundDistance, sensorAlive,useRamDiskForLogfiles,lastAlive

	global shutdownInputPin, shutdownPinVoltSensor, shutDownPinVetoOutput, lastshutdownInputPinTime
	global actions, output, sensors, sensorList
	global activePGMdict, bluetoothONoff
	global oldRaw,	lastRead
	global batteryMinPinActiveTimeForShutdown, inputPinVoltRawLastONTime
	global batteryChargeTimeForMaxCapacity, batteryCapacitySeconds
	global GPIOTypeAfterBoot1, GPIOTypeAfterBoot2, GPIONumberAfterBoot1, GPIONumberAfterBoot2, alreadyBooted
	global activePGM
	global configured
	global startWebServerSTATUS, startWebServerINPUT
	global fanGPIOPin, fanTempOnAtTempValue, lastTempValue, lastTimeTempValueChecked, fanTempName, fanTempDevId, fanEnable
	global wifiEthCheck, BeaconUseHCINoOld,BLEconnectUseHCINoOld


	checkFSCHECKfileDone	= False
	wifiEthCheck			= {}
	BeaconUseHCINoOld		= ""
	BLEconnectUseHCINoOld	= ""
	fanEnable				= "-"
	fanTempName				= ""
	fanTempDevId			= ""
	lastTempValue			= -1
	lastTimeTempValueChecked= -1
	fanGPIOPin				= -1
	fanTempOnAtTempValue	= -1

	activePGM				= {}
	GPIOTypeAfterBoot1		= "off"
	GPIOTypeAfterBoot2		= "off"
	GPIONumberAfterBoot1	= "-1"
	GPIONumberAfterBoot2	= "-1"
	alreadyBooted			= False


	startWebServerSTATUS	 = 80
	startWebServerINPUT		 = 8010
	batteryChargeTimeForMaxCapacity = 3600. # seconds
	batteryCapacitySeconds   = 5*3600 # 

	batteryMinPinActiveTimeForShutdown = 9999999999999
	inputPinVoltRawLastONTime = time.time()
	oldRaw					= ""
	lastRead				= 0
	bluetoothONoff			= "on"
	getSensorsActive		= 0
	geti2cActive			= 0
	getDHTActive			= 0
	getWire18B20Active		= 0
	getspiMCP3008Active		= 0
	getmyprogramActive		= 0
	getpmairqualityActive	= 0
	G.debug					= 5
	tea5767Active			= False
	OUTPUTgpioActive		= False
	displayActive			= False 
	neopixelActive			= False
	neopixelClockActive		= False
	rebootHour				= -1  # defualt : do  not reboot
	rebooted				= True
	useRamDiskForLogfiles	= "0"
	enableiBeacons			= "1"
	beforeLoop				= True
	myPID					= str(os.getpid())
	enableRebootCheck		= ""
	restart					= ""
	sensorEnabled			= []
	sensorList				= []
	sensors					= {}
	enableSensor			= "0"
	rPiCommandPORT			= 0
	ipConnection			= time.time() +100
	G.lastAliveSend2		= time.time()
	lastAlive				= []
	lastAliveultrasoundDistance =0
	loopCount				= 0
	iPhoneMACListOLD		= ""
	shutdownInputPin		= -1
	shutDownPinVetoOutput	= -1
	shutdownPinVoltSensor		= -1
	lastshutdownInputPinTime= 0
	BLEserial				= "serial"
	rebootWatchDogTime		= -1
	sensorAlive				= {}
	actions					= []
	firstRead				= True
	activePGMdict			= {}
	configured				= ""
	adhocWifiStarted		= -1

	GPIO.setwarnings(False)
	GPIO.setmode(GPIO.BCM)
	G.debug = 0


	# remove precompiled py programs in case .py was updated
	os.system("rm "+G.homeDir+"*.pyc  > /dev/null 2>&1")

	# make dir for our logfiles if they do not exist
	#os.system("mkdir "+G.logDir+"> /dev/null 2>&1" )

	if	os.path.isdir(G.homeDir+"temp"):
		os.system("rm  "+G.homeDir+"temp/* > /dev/null 2>&1")
		alreadyBooted = True
	else:
		os.system("mkdir  "+G.homeDir+"temp")
		alreadyBooted = False
	os.system("mount -t tmpfs -o size=2m tmpfs "+G.homeDir+"temp")


	if cleanupOldFiles():
		startProgam("master.py", params="", reason="..cleaned-up old files")

	G.tStart	  = time.time()

	U.resetRebootingNow()

	G.last_masterStart = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")


	for ff in G.programFiles:
		if ff == G.program:
			U.killOldPgm(myPID,G.program+".py")
		else:
			U.killOldPgm(-1, ff+".py")

	for ff in G.specialOutputList:
			U.killOldPgm(-1, ff+".py")

	for ff in G.specialSensorList:
			U.killOldPgm(-1, ff+".py")

	for ff in ["webserverINPUT","webserverSTATUS"]:
			U.killOldPgm(-1, ff+".py")

	os.system("/usr/bin/python "+G.homeDir+"copyToTemp.py")
	time.sleep(1)

	readNewParams(force=True)
	U.toLog (-1, "START.. indigoServer IP:>>{}<<".format(G.ipOfServer) , doPrint=True)

	checkLogfiles()

	time.sleep(1)


	# sets: G.wifiType = normal/ adhoc
	U.whichWifi() 

	adhocWifiStarted = U.checkWhenAdhocWifistarted()

	U.toLog (-1, "Master adhocWifi is:{} ;  G.wifiType is:{}".format(adhocWifiStarted, G.wifiType) , doPrint=True)

	os.system("cp  "+G.homeDir+"callbeacon.py  "+G.homeDir0+"callbeacon.py")


	U.clearNetwork()

	if G.networkType  in G.useNetwork and G.wifiType =="normal":
		for ii in range(100):
			if ii > 5:
				U.toLog (-1, " master no ip number working, giving up")
				G.networkType="clockMANUAL"
				break
	
			retCode, changed = U.getIPNumberMaster()
			if retCode > 1 or G.ipAddress =="":
				U.setNetwork("off")
				time.sleep(5)
				U.toLog (-1, " master no ip number working, trying again, retcode="+ str(retCode))
			else:
				U.clearNetwork()
				break
			
	
	readNewParams()



	if	G.wifiType =="normal" and G.networkType !="clockMANUAL" and	 rPiCommandPORT >0:
			startProgam("receiveCommands.py", params=str(rPiCommandPORT), reason=" restart requested from plugin")



	if configured == "": 
		if G.networkType  in G.useNetwork and G.wifiType =="normal":
			adhoc    	 = True
			wifiWaiting  = True
			for ii in range(500):
				if G.userIdOfServer	 == "xxstartxx":
					if adhoc and adhocWifiStarted < 0: 
						U.toLog (-1," launching at start startAdhocWifi ", doPrint=True )
						U.startAdhocWifi()
						U.startwebserverINPUT(startWebServerINPUT)
					if wifiWaiting: 
						if U.checkwebserverINPUT():
							wifiWaiting= False
					adhoc = False
					U.toLog (-1, " master not configured yet, lets wait for new config files", doPrint=True)
					if ii >498:
						startProgam("master.py", params="", reason="..not configured yet")
						exit(0)
					time.sleep(1)
					readNewParams()
				else:
					break


	os.system("sudo chown -R  pi:pi "+G.logDir)


	if startWebServerSTATUS > 0:
		if not U.checkIfwebserverSTATUSrunning():
			U.startwebserverSTATUS(startWebServerSTATUS)



	if adhocWifiStarted > 0 and G.wifiType =="adhoc":
		if not U.checkIfwebserverINPUTrunning():
			U.startwebserverINPUT(startWebServerINPUT)
			# restore old interfaces for next reboot 
			os.system('sudo cp '+G.homeDir+'interfaces-DEFAULT /etc/network/interfaces')
			for ii in range(999):
				U.checkwebserverINPUT()
				time.sleep(1)
		
	


	if G.networkType  in G.useNetwork and G.wifiType =="normal":
		for ii in range(100):
			if ii > 98:
				U.toLog(-1, "master no connection to indigo server at ip:>>{}<<  network type:{}".format(G.ipOfServer, G.networkType) , doPrint=True)
				time.sleep(7)
				startProgam("master.py", params="", reason=".. failed to connect to indigo server")
				exit(0)
			if U.testPing() >0:
				readNewParams()
				if time.time() - G.ipConnection > 600.: # after 10 minutes 
					if enableRebootCheck.find("rebootPing") >-1:
						U.sendURL(sendAlive="reboot")
						U.doReboot(30.," reboot due to no  PING reply from MAC for 10 minutes ")				
				if time.time() - G.ipConnection > 100.: 
					if  G.wifiEth["wlan0"]["on"]  in ["onIf","off"] and G.wifiEth["eth0"]["on"] !="off":
						G.wifiEthOld = copy.copy(G.wifiEth)
						G.wifiEth["wlan0"]["on"] 	= "on"
						G.wifiEth["wlan0"]["useIP"] = "use"
						G.wifiEth["eth0"]["on"]     = "onIf"
						G.wifiEth["eth0"]["useIP"]  = "useIf"
						G.switchedToWifi = time.time()
						U.getIPNumberMaster()
			else: 
				U.toLog(-1, "can ping indigo server at ip:>>{}<<".format(G.ipOfServer), doPrint=True)
				break
			time.sleep(10)



	# make directory for sound files
	if not os.path.isdir(G.homeDir+"soundfiles"):
		os.system("mkdir "+G.homeDir+"soundfiles &")


	if checkDiskSpace() == 1:
		U.toLog(-1, "please expand hard disk, not enough disk space left either do sudo raspi-config and expand HD	 or replace ssd with larger ssd ", doPrint=True)
		time.sleep(50)
		exit()


	if os.path.isfile(G.homeDir+"temp/rebootNeeded"):
		os.remove(G.homeDir+"temp/rebootNeeded")
	if os.path.isfile(G.homeDir+"temp/restartNeeded"):
		os.remove(G.homeDir+"temp/restartNeeded")


	# check if all libs for sensors etc are installed
	installLibs()
	time.sleep(0.5)
	for ii in range(200):
		if	os.path.isfile(G.homeDir+"installLibs.done"):
			break
		if ii%10==0:
			U.toLog (-1, " master still waiting for installibs to finish", doPrint=True)
		time.sleep(5)



	GPIO.setwarnings(False)




	#(re)start beaonloop for bluez / iBeacons
	if enableiBeacons =="1": 
		startProgam("beaconloop.py", params="", reason=" at startup ")
		checkIfAliveFileOK("beaconloop",force="set")
 
	if checkRamDisk(): 
		U.toLog (-1, " master  waiting to reboot due to ram disk change", doPrint=True)
		time.sleep(60) # give it some time, it should never happen here 
		U.sendRebootHTML("change_in_ramdisk_for_logfiles")

	lastrebootWatchDogTime = time.time() - rebootWatchDogTime*60. +30.
	os.system("shutdown - c >/dev/null 2>&1") ## stop any pending shutdowns

	beforeLoop			 = False
	# main loop every 30 seconds

	# do a system boot sector check / repair
	os.system("dosfsck -w -r -l -a -v -t /dev/mmcblk0p1 > "+G.homeDir+"temp/dosfsck & ")


	# reset rights and ownership just in case
	os.system("chmod a+r -R "+G.homeDir0+"*")
	os.system("chmod a+x "+G.homeDir0+"callbeacon.py")

	os.system("chmod a+w -R "+G.homeDir+"*")
	os.system("chown -R pi:pi "+G.homeDir0+"*")

	#os.system("sudo chown -R  pi:pi	 /run/user/1000/pibeacon")
	os.system("sudo chmod a+x  /lib/udev/hwclock-set")
	#

	checkIfGpioIsInstalled()


	#startProgam("actions.py", params="", reason=" at startup ")
	#checkIfAliveFileOK("actions",force="set")

	G.tStart	  = time.time()

	U.sendi2cToPlugin()
	tAtLoopSTart =time.time()

	U.testNetwork()
	U.testNTP()
	if G.ntpStatus != "started, working":
		U.startNTP(mode="simple")
		if G.ntpStatus !="started, working":
			#print "master: stopping NTP, not working", G.ntpStatus
			U.stopNTP("final")
			G.ntpStatus ="stopped, after not working"


	if	((G.networkStatus.find("Inet") > -1) and  # network up
		 (G.ntpStatus=="started, working"  ) and  # NTP working
		 (G.useRTC != "" and G.useRTC != "0")  ):					 # RTC installed ...   ==>	set HW clock to NTP time stamp:
			os.system("sudo /sbin/hwclock -w")




	startingnetworkStatus = G.networkStatus
	startingnetworkype	  = G.networkType
	restartCLock		  = time.time() +  999999999.

	retCode, changed = U.getIPNumberMaster(quiet=False)
	if retCode ==0 and G.ipAddress !="":
		U.setNetwork("on")
	
	if changed: 
		U.restartMyself(reason="changed ip number, eg wifi was switched off with eth0 present (1)")

	os.system("rm  "+ G.homeDir+"temp/sending		   > /dev/null 2>&1 ")


	U.toLog(1,"starting loop", doPrint=True)


	checkTempForFanOnOff(force = True)

	while True:

		if abs(tAtLoopSTart	 - time.time()) > 30:
			if G.networkType.find("indigo") >-1 and G.wifiType =="normal":
				U.restartMyself(reason="new time set, delta="+unicode(tAtLoopSTart	- time.time()))
		
		tAtLoopSTart =time.time()
		
		loopCount += 1
		if loopCount == 3: 
			checkFSCHECKfile()

		try:	
			readNewParams()
			if loopCount%5 == 0: 
				if checkRamDisk():
					if loopCount < 10: 
						U.toLog (-1, " master  waiting to reboot due to ram disk change", doPrint=True)
						time.sleep(60) # give it some time directly after reboot
					U.sendRebootHTML("change_in_ramdisk_for_logfiles")
				# check if fs is still ok

				
			if loopCount%60 == 0: # every 10 minutes
				U.sendi2cToPlugin()		   
				if (unicode(subprocess.Popen("echo x > x" ,shell=True,stdout=subprocess.PIPE,stderr=subprocess.PIPE).communicate())).find("Read-only file system") > 0:
					U.doReboot(10.," reboot due to bad SSD, 'file system is read only'")				   
					time.sleep(10)
					os.system("reboot now")
				os.system("rm x")
			
				os.system("sudo chown -R  pi:pi	 "+G.homeDir)

			#check if IP number has changed, or if we should switch off wlan0 if eth0 is present 
			if loopCount%24 == 0: # every 2 minutes
				oldIP = G.ipAddress
				retCode, changed = U.getIPNumberMaster(quiet=True)

				if	G.ipAddress =="" and G.networkType !="clockMANUAL" :
					U.doReboot(10.," reboot due to no IP nummber")				   
					time.sleep(10)
					os.system("reboot now")

				if changed: 
					U.restartMyself(reason="changed ip number, eg wifi was switched off with eth0 present (loop)")

				if retCode == 0 and G.ipAddress !="":
					U.setNetwork("on")

				if oldIP != G.ipAddress:
					eth0IP, wifi0IP, G.eth0Enabled, G.wifiEnabled = U.getIPCONFIG()
					if eth0IP == "" or wifi0IP == "": # avoid restart when both are active
						U.restartMyself(reason="changed ip number,.. eth0IP: {};  wifi0IP: {};  oldIP: {};  G.ipAddress:{}".format(eth0IP, wifi0IP, oldIP, G.ipAddress) )


	##########   check if pgms are running

			if str(rPiCommandPORT) !="0"  and G.wifiType =="normal" and G.networkType !="clockMANUAL" and (G.networkStatus).find("indigo") >-1: 
				checkIfPGMisRunning("receiveCommands.py", checkAliveFile="", parameters=str(rPiCommandPORT))

			if "BLEconnect" in sensors:
				startBLEconnect()
			if enableiBeacons == "0" and "BLEsensor" in sensors:
				startBLEsensor()

			for pp in ["setTEA5767","OUTPUTgpio","neopixelClock","display","neopixel","neopixelClock","spiMCP3008","simplei2csensors","sunDial","setStepperMotor"]:
					U.toLog(1, "setting {} ON".format(pp) ) 
					if pp in activePGM:
						if   pp =="display":
							checkIfDisplayIsRunning()
						elif pp =="neopixel":
							checkIfNeopixelIsRunning(pgm= "neopixel")
						elif pp =="neopixelClock":
							checkIfNeopixelIsRunning(pgm= "neopixelClock")
						elif pp =="sunDial":
							checkIfPGMisRunning(pp+".py", checkAliveFile="sunDial")
						else:
							checkIfPGMisRunning(pp+".py")
			

			for ss in G.specialSensorList:
				if	(ss in sensors or ss in activePGM )and not (ss in activePGMdict): 
					checkIfPGMisRunning(ss+".py",checkAliveFile=ss)
							   
			for ss in activePGMdict:
				checkIfPGMisRunning(activePGMdict[ss][0],checkAliveFile=activePGMdict[ss][1] )

			checkIfPGMisRunning("copyToTemp.py")
		
			if enableiBeacons != "0":
				checkIfbeaconLoopIsRunning()

			checkIfRebootRequest()
		
			if rebootHour >-1:
				checkIfNightReboot()
				if datetime.datetime.now().hour > rebootHour: rebooted = False


			checkSystemLOG()



	######### start / stop  wifi  &  web servers 
			if adhocWifiStarted > 0:
				if time.time() - adhocWifiStarted > 600:
					U.stopAdhocWifi()
			else:
				adhocWifiStarted = U.checkWhenAdhocWifistarted()

			if U.checkIfStartAdhocWiFi():
				#print " seems to be tru start adhoc wifi"
				if U.whichWifi() =="normal":
					U.startAdhocWifi()
					adhocWifiStarted = time.time()

			if U.checkIfStopAdhocWiFi():
				if U.whichWifi() =="adhoc":
					U.stopAdhocWifi()
					adhocWifiStarted = -1

			if startWebServerSTATUS >0 or U.checkIfStartwebserverSTATUS():
				if not U.checkIfwebserverSTATUSrunning():
					U.startwebserverSTATUS(startWebServerSTATUS)

			if startWebServerSTATUS >0 and  U.checkIfStopwebserverSTATUS():
				if U.checkIfwebserverSTATUSrunning():
					U.stopwebserverSTATUS()

			if startWebServerINPUT > 0 and  U.checkIfStopwebserverINPUT() and adhocWifiStarted <0:
				if U.checkIfwebserverINPUTrunning():
					U.stopwebserverINPUT()

			if startWebServerINPUT > 0 or U.checkIfStartwebserverINPUT():
				if not U.checkIfwebserverINPUTrunning():
					U.startwebserverINPUT(startWebServerINPUT)
			U.checkwebserverINPUT()

			if fanGPIOPin > 0:
				checkTempForFanOnOff()

			U.checkIfAliveNeedsToBeSend()
		
			if loopCount%5 == 0: 
				U.checkrclocalFile()
		
			if loopCount %4 ==0: # check network every 40 secs
				U.testNetwork(force = True)
				U.checkNTP()
				#print "startingnetworkStatus", startingnetworkStatus , G.networkStatus , G.networkType
				if	((G.networkStatus.find("Inet") > -1 ) and	# network up
					 (G.ntpStatus=="started, working"	) and	# NTP working
					 (G.useRTC !="" and G.useRTC != "0")  ):			# RTC installed ...	  ==>  set HW clock to NTP time stamp:
					os.system("sudo /sbin/hwclock -w")

				if (G.networkStatus).find("indigo") > -1 and (G.networkType).find("clock") ==-1:
					if U.testPing()==2:				# if no ping gets return we assume we are not connected, this happens after powerfailure. the router comes aback after rpi and wifi has given up, need to restart
						if time.time() - G.ipConnection > 600.: # after 10 minutes 
							if enableRebootCheck.find("rebootPing") >-1:
								U.sendURL(sendAlive="reboot")
								U.doReboot(30.," reboot due to no  PING reply from MAC for 10 minutes ")				

				if	G.networkType.find("clock")> -1:
						if startingnetworkStatus.find("Inet") >-1 and G.networkStatus.find("Inet") == -1 : # was up at start, now down
							if (time.time() - restartCLock) < 0:
								G.networkType ="clockMANUAL"
								#print "set to clock manual"
								restartCLock = time.time()+2  # wait at least one round before declaring a loss of wifi 
								cycleWifi()
						else:
							restartCLock = time.time()+ 999999999
							G.networkType ="clock"

						#print "restartCLock", time.time() - restartCLock
						if G.networkType =="clockMANUAL"  and (time.time() - restartCLock)> 0  :
							xx = G.networkType
							G.networkType="x"
							ipOK, changed = U.getIPNumberMaster(quiet=True)
							G.networkType = xx
							#print " networkStatus, ipOK : ",  G.networkStatus, ipOK

							if	ipOK >0 and G.networkStatus.find("Inet") ==-1:
								U.setNetwork("off")
								G.networkType="clockMANUAL"
								cycleWifi()
								#print " setting to clockmanual "
								U.restartMyself(reason="network went down ")

						if ( startingnetworkStatus.find("Inet") ==-1 and  G.networkStatus.find("Inet") >-1	) :
							U.clearNetwork()
							xx = G.networkType
							G.networkType="x"
							ipOK, changed = U.getIPNumberMaster(quiet=False)
							G.networkType = xx
							#print " networkStatus, ipOK : ",  G.networkStatus, ipOK
							if ipOK ==0 and G.networkStatus.find("Inet") >-1:
								U.restartMyself(reason="network came back ")



			if loopCount %120 ==0: # check logfiles every 150*10=1200 seconds ~ 30 minutes
				checkLogfiles()
				loopCount =0
				## check if we have network back
				
			delayAndWatchDog()

		except	Exception, e :
			U.toLog (-1, u"in Line {} has error={}".format(sys.exc_traceback.tb_lineno, e), doPrint=True)

U.toLog (-1, u"exit at end of master", doPrint=True)	
time.sleep(10)
sys.exit(0)		   
