#!/usr/bin/python
# -*- coding: utf-8 -*-
# by Karl Wachs
# feb 5 2016

masterVersion			= 15.10
## changelog: 
# 2020-04-05 added check for NTP
# 2020-xx-xx 
#
#
#


import sys, os, subprocess, copy
import time,datetime
import json
import RPi.GPIO as GPIO
try:
	import serial
except:
	pass

import smbus

sys.path.append(os.getcwd())
import	piBeaconGlobals as G
import traceback
import	piBeaconUtils	as U
G.program = "master"

####################      #########################
def checkIfUARThciChannelIsOnRPI4():
	try:
		rpi = U.getRPiType().split(",")[0]
		# returns Pi 4 Model B Rev 1.2
		if rpi.find("Pi 4") == -1: return # check only for RPI 4
	
		HCIs = U.whichHCI()
		U.logger.log(20, "checking if BLE startup ok on RPI4, HCIs:{}".format(HCIs))
		# returns :  hci["hci"][hciNo] = {"bus":bus, "numb":int(hciNo[3:]),"upDown":"DOWN","BLEmac":"0"}
		if HCIs["hci"] != {}:
			for xx in HCIs["hci"]:
				if "bus" in HCIs["hci"][xx]:
					if HCIs["hci"][xx]["bus"] == "UART":
						U.logger.log(20, "BLE startup check ok, UART channel found")
						return # all ok

		text = "BLE ON RPI4 :  UART BLE NOT ENABLED will restart BLE stack (hciattach /dev/ttyAMA0 bcm43xx 921600 noflow -) and try again,, HCI inf:\n{}".format(HCIs)
		U.logger.log(20, text)
		cmd = "timeout 5 sudo hciattach /dev/ttyAMA0 bcm43xx 921600 noflow -"
		ret = subprocess.Popen(cmd, shell=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE).communicate()
		U.logger.log(20, "cmd: {} and ret:".format(cmd, ret))

		cmd = "timeout 20 sudo hciattach /dev/ttyAMA0 bcm43xx 921600 noflow -"
		ret = subprocess.Popen(cmd, shell=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE).communicate()
		U.logger.log(20, "cmd: {} and ret:".format(cmd, ret))
		time.sleep(2)

		HCIs = U.whichHCI()
		# returns :  hci["hci"][hciNo] = {"bus":bus, "numb":int(hciNo[3:]),"upDown":"DOWN","BLEmac":"0"}
		if HCIs["hci"] != {}:
			for xx in HCIs["hci"]:
				if "bus" in HCIs["hci"][xx]:
					if HCIs["hci"][xx]["bus"] == "UART":
						U.logger.log(20, "BLE startup check ok, UART channel found")
						return # all ok

		U.sendURL( data={"data":{"error":text}}, squeeze=False, wait=True )

	except	Exception as e:
		U.logger.log(40, u"Line {} has error={}".format(traceback.extract_tb(sys.exc_info()[2])[-1][1], e))
	return

####################      #########################
def checkIfGpioIsInstalled():
	try:
		ret = subprocess.Popen("gpio -v",shell=True,stdout=subprocess.PIPE,stderr=subprocess.PIPE).communicate()
		if ret[0].find("version:") ==-1:
			subprocess.call("rm -R /tmp/wiringPi", shell=True)
			installGPIO = "cd /tmp; git clone git://git.drogon.net/wiringPi; cd wiringPi; ./build ;	 rm -R /tmp/wiringPi"
			U.logger.log(30,"installing gpio wiringPi .... {}\n with: {}".format(unicode(ret), installGPIO))
			ret = subprocess.Popen(installGPIO,shell=True,stdout=subprocess.PIPE,stderr=subprocess.PIPE).communicate()
			U.logger.log(30,"result of installing gpio wiringPi .... {}".format(unicode(ret)))
	except	Exception as e:
		U.logger.log(40, u"Line {} has error={}".format(traceback.extract_tb(sys.exc_info()[2])[-1][1], e))




####################      #########################
def checkWiFiSetupBootDir():

	if U.copySupplicantFileFromBoot():
		U.doReboot(tt=10., text="restart w new wifi setup supplicant file in /boot dir")
		time.sleep(30)
		return 

	if U.checkifWifiJsonFileInBootDir():
		U.doReboot(tt=10., text="restart w new wifi setup json data in /boot dir ")
		time.sleep(30)
	return 

####################      #########################
def readNewParams(force=0):
	global restart,sensorList,rPiCommandPORT, firstRead
	global sensorEnabled, enableiBeacons, beforeLoop, cAddress,rebootHour,rebooted,sensors,enableShutDownSwitch, rebootWatchDogTime
	global shutdownInputPin, shutdownPinVoltSensor,shutDownPinVetoOutput , sensorAlive,useRamDiskForLogfiles
	global actions, output
	global lastAlive
	global activePGMdict, bluetoothONoff
	global oldRaw,	lastRead
	global batteryMinPinActiveTimeForShutdown, inputPinVoltRawLastONTime
	global batteryUPSshutdownALCHEMYupcI2C, batteryUPSshutdownEnable
	global SMBUS
	global batteryChargeTimeForMaxCapacity, batteryCapacitySeconds
	global GPIOTypeAfterBoot1, GPIOTypeAfterBoot2, GPIONumberAfterBoot1, GPIONumberAfterBoot2
	global activePGM
	global configured
	global startWebServerSTATUS, startWebServerINPUT
	global fanGPIOPin, fanTempOnAtTempValue, fanTempOffAtTempValue, fanTempName, fanTempDevId, fanEnable
	global wifiEthCheck, BeaconUseHCINoOld,BLEconnectUseHCINoOld
	global batteryUPSshutdownAtxPercent, shutdownSignalFromUPSPin, shutdownSignalFromUPS_SerialInput, shutdownSignalFromUPS_InitTime
	global ifNetworkChanges
	global typeForPWM, maxSizeOfLogfileOnRPI
	global xWindows, startXonPi
	global clearHostsFile
	global myPID
	global python3
	global BLEdirectSensorDeviceActive
	global BLEdirectSwitchbotActive
	global startOtherProgram, startOtherProgramOld, startOtherProgramKeepRunning
	global macIfWOLsendToIndigoServer, IpnumberIfWOLsendToIndigoServer
	global typeOfUPS, RTCpresent

	try:	
		inp,inpRaw,lastRead2 = U.doRead(lastTimeStamp=lastRead)
		if inp == "": 
			subprocess.call("cp "+G.homeDir+"parameters  "+G.homeDir+"temp/parameters", shell=True)
			time.sleep(1)
			inp,inpRaw,lastRead2 = U.doRead(lastTimeStamp=lastRead)


		if force == 0:
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

		if wifiEthCheck != {} and wifiEthCheck != G.wifiEthOld and G.networkType.find("indigo") > -1:
			U.restartMyself(reason="new wifi, eth defs, need to restart master:{}  :{}".format(wifiEthCheck, G.wifiEthOld), doPrint =True)
		wifiEthCheck = copy.copy(G.wifiEthOld)

		if BeaconUseHCINoOld != "" and BeaconUseHCINoOld != G.BeaconUseHCINo:
			U.restartMyself(reason="new hci-Beacon defs, need to restart master", doPrint =True)
		BeaconUseHCINoOld = copy.copy(G.BeaconUseHCINo)

		if BLEconnectUseHCINoOld != "" and BLEconnectUseHCINoOld != G.BLEconnectUseHCINo:
			U.restartMyself(reason="new hci-BLEconnect defs, need to restart master", doPrint =True)
		BLEconnectUseHCINoOld = copy.copy(G.BLEconnectUseHCINo)

		if u"batteryMinPinActiveTimeForShutdown" 	in inp: batteryMinPinActiveTimeForShutdown = float(inp["batteryMinPinActiveTimeForShutdown"])
		if u"enableiBeacons"						in inp:	 enableiBeacons=					inp["enableiBeacons"]
		if u"cAddress"								in inp:	 cAddress=							inp["cAddress"]
		if u"rebootHour"							in inp:	 rebootHour=						int(inp["rebootHour"])
		if u"sensors"								in inp:	 sensors =							inp["sensors"]
		if u"useRamDiskForLogfiles" 				in inp:	 useRamDiskForLogfiles =			inp["useRamDiskForLogfiles"]
		if u"actions"								in inp:	 actions			   =			inp["actions"]
		if u"useRTC"								in inp:	 U.setUpRTC(inp["useRTC"])
		if u"batteryChargeTimeForMaxCapacity" 		in inp: batteryChargeTimeForMaxCapacity=	float(inp["batteryChargeTimeForMaxCapacity"])
		if u"batteryCapacitySeconds" 				in inp:	 batteryCapacitySeconds= 			float(inp["batteryCapacitySeconds"])

		if u"GPIONumberAfterBoot1" 					in inp:	 GPIONumberAfterBoot1= 				inp["GPIONumberAfterBoot1"]
		if u"GPIONumberAfterBoot2" 					in inp:	 GPIONumberAfterBoot2= 				inp["GPIONumberAfterBoot2"]
		if u"GPIOTypeAfterBoot1" 					in inp:	 GPIOTypeAfterBoot1= 				inp["GPIOTypeAfterBoot1"]
		if u"GPIOTypeAfterBoot2" 					in inp:	 GPIOTypeAfterBoot2= 				inp["GPIOTypeAfterBoot2"]
		if u"configured" 							in inp:	 configured= 						inp["configured"]
		if u"startWebServerSTATUS" 					in inp:	 startWebServerSTATUS= 				int(inp["startWebServerSTATUS"])
		if u"startWebServerINPUT" 					in inp:	 startWebServerINPUT= 				int(inp["startWebServerINPUT"])
		if u"fanEnable" 							in inp:	 fanEnable= 						inp["fanEnable"]
		if u"ifNetworkChanges" 						in inp:	 ifNetworkChanges= 					inp["ifNetworkChanges"] 
		if u"maxSizeOfLogfileOnRPI" 				in inp:	 maxSizeOfLogfileOnRPI= 		  	int(inp["maxSizeOfLogfileOnRPI"]) 
		if u"startXonPi" 							in inp:	 startXonPi= 						inp["startXonPi"]
		if u"clearHostsFile" 						in inp:	 clearHostsFile= 					inp["clearHostsFile"] == "1"
		if u"macIfWOLsendToIndigoServer" 			in inp:	 macIfWOLsendToIndigoServer= 		inp["macIfWOLsendToIndigoServer"] 
		if u"IpnumberIfWOLsendToIndigoServer" 		in inp:	 IpnumberIfWOLsendToIndigoServer= 	inp["IpnumberIfWOLsendToIndigoServer"] 

		if u"startOtherProgram" 					in inp:	 
			if startOtherProgram != inp["startOtherProgram"]:
				startOtherProgramOld = startOtherProgram
			startOtherProgram 				= inp["startOtherProgram"].strip()
			startOtherProgramKeepRunning 	= inp["startOtherProgramKeepRunning"]

		setupX(action=startXonPi)


		if u"typeForPWM" 				in inp:	 
			if typeForPWM != inp["typeForPWM"] and inp["typeForPWM"] == "PIGPIO":
				typeForPWM = 	inp["typeForPWM"]
				if not U.pgmStillRunning("pigpiod"): 	
					U.logger.log(10, "starting pigpiod")
					subprocess.call("sudo pigpiod -s 2 &", shell=True)
					time.sleep(0.5)
					if not U.pgmStillRunning("pigpiod"): 	
						U.logger.log(30, "restarting myself as pigpiod not running, need to wait for timeout to release port 8888")
						time.sleep(20)
						U.restartMyself(reason="pigpiod not running")
						exit(0)



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
				if u"fanTempOffAtTempValue" in inp:
					fanTempOffAtTempValue= int(inp["fanTempOffAtTempValue"])

		
		doGPIOAfterBoot()

		if force == 2: return 

		if u"sleepAfterBoot" 				in inp:	 
			fixRcLocal(inp["sleepAfterBoot"])
		
		if u"bluetoothONoff"			 in inp:
			if bluetoothONoff != inp["bluetoothONoff"]:
				U.logger.log(30, " updating BLE stack from {}  to {}".format(bluetoothONoff,inp["bluetoothONoff"] ))
				if inp["bluetoothONoff"].lower() =="on":
					subprocess.call("rfkill unblock bluetooth", shell=True)
					subprocess.call("systemctl enable hciuart", shell=True)
					time.sleep(20)
					U.sendRebootHTML("switch bluetooth back on ",reboot=True)
				else:
					if U.pgmStillRunning("/usr/lib/bluetooth/bluetoothd"):
						U.logger.log(30,"switching blue tooth stack off ")
						subprocess.call("rfkill block bluetooth", shell=True)
						subprocess.call("systemctl disable hciuart", shell=True)
						U.killOldPgm(myPID,"/usr/lib/bluetooth/bluetoothd")
				bluetoothONoff = inp["bluetoothONoff"]

		sensorList =""
		for sensor in sensors:
			sensorList+=sensor+","
			python3[sensor] = False
		
		if "output"				in inp:	 
			output=				  (inp["output"])
			U.logger.log(20, "output devices: {}".format(output))

			for pp in ["setTEA5767","OUTPUTgpio","neopixelClock","display","neopixel","neopixelClock","sundial","setStepperMotor"]:
				if pp in output:
						U.logger.log(10, "setting Active {}".format(pp) ) 
						if pp not in activePGM:
							if pp =="display":
								checkIfDisplayIsRunning()
								activePGM[pp] =True
							elif pp =="neopixel":
								checkIfNeopixelIsRunning(pgm= "neopixel")
								activePGM[pp] =True
							elif pp =="neopixelClock":
								G.sundialActive = "/home/pi/pibeacon/temp/neopixelClock.cmd"
								checkIfNeopixelIsRunning(pgm= "neopixelClock")
								activePGM[pp] =True
								RTCpresent = True
							else:
								startProgam(pp+".py", params="", reason="restarting "+pp+"..not running")
								activePGM[pp] =True
						if pp=="sundial": 
							G.sundialActive = "/home/pi/pibeacon/temp/sundial.cmd"
							activePGM[pp] =True
							RTCpresent = True
						if pp == u"display":
							for devId in output[pp]:
								ddd = output[pp][devId][0]
								if "screenXwindows" == ddd["devType"]:
									setupX(action="start")
								activePGM[pp] =True


				else:
					try: del activePGM[pp] 
					except: pass
					U.killOldPgm(-1, pp+".py")


		xx= {"spiMCP3008":"spiMCP3008","i2c":"simplei2csensors"}
		for pp in xx:
			pgm = xx[pp]
			if sensorList.find(pp) >-1:
					U.logger.log(10, "checking if Active: {}".format(pgm)) 
					if pgm not in activePGM:
						startProgam(pgm+".py", params="", reason="restarting {}..not running".format(pgm))
					activePGM[pgm] =True
			else:
				try: del activePGM[pp] 
				except: pass
				U.killOldPgm(-1, pgm+".py")


		for pgm in G.python3Apps:
			if sensorList.find(pgm) >-1:
					U.logger.log(10, "checking if Active: {}".format(pgm)) 
					activePGM[pgm] = True
					python3[pgm]   = True
					if pgm not in activePGM:
						startProgam(pgm+".py", params="", reason="restarting {}..not running".format(pgm))
			else:
				try: del activePGM[pgm] 
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

		if u"typeOfUPS"	  in inp:	typeOfUPS =	inp["typeOfUPS"]
		else:						typeOfUPS =	""


		if u"shutDownPinVetoOutput"	  in inp:  
			try:
				xxx=				   int(inp["shutDownPinVetoOutput"])
				if shutDownPinVetoOutput != -1 and xxx != shutDownPinVetoOutput: # is a change, not just switch on 
					U.logger.log(20, "restart master for new shutdown input pin")
					subprocess.call("/usr/bin/python "+G.homeDir+"master.py &" , shell=True)
				if shutDownPinVetoOutput != xxx:
					shutDownPinVetoOutput=	   xxx
					if shutdownInputPin ==15 or shutdownInputPin==14:
						subprocess.call("systemctl disable hciuart", shell=True)
						time.sleep(1)
					if shutDownPinVetoOutput !=-1:
						GPIO.setup(shutDownPinVetoOutput, GPIO.OUT) # disable shutdown 
						GPIO.output(shutDownPinVetoOutput, True)    # set to high while running 
			except: pass


		if u"shutdownInputPin"	 in inp:  
			try:
				xxx=				   int(inp["shutdownInputPin"])
				if shutdownInputPin != -1 and xxx != shutdownInputPin:  # is a change, not just switch on 
					U.logger.log(20, "restart master for new shutdown input pin")
					subprocess.call("/usr/bin/python "+G.homeDir+"master.py &" , shell=True)
				if shutdownInputPin != xxx:
					shutdownInputPin=	  xxx
					if shutdownInputPin ==15 or shutdownInputPin==14:
						subprocess.call("systemctl disable hciuart", shell=True)
						time.sleep(1)
					if shutdownInputPin !=-1:
						GPIO.setup(int(shutdownInputPin), GPIO.IN, pull_up_down = GPIO.PUD_UP)	# use pin shutDownPin  to input reset
			except: pass


		if u"shutdownPinVoltSensor"	 in inp:  
			try:
				xxx=				   int(inp["shutdownPinVoltSensor"])
				if shutdownPinVoltSensor != -1 and xxx != shutdownPinVoltSensor:  # is a change, not just switch on 
					U.logger.log(20, "restart master for new shutdown input pin")
					subprocess.call("/usr/bin/python "+G.homeDir+"master.py &" , shell=True)
				if shutdownPinVoltSensor != xxx:
					shutdownPinVoltSensor=	  xxx
					if shutdownPinVoltSensor == 15 or shutdownPinVoltSensor == 14:
						subprocess.call("systemctl disable hciuart", shell=True)
						time.sleep(1)
					GPIO.setup(int(shutdownPinVoltSensor), GPIO.IN, pull_up_down = GPIO.PUD_UP)	# use pin shutDownPin  to input reset
					batteryUPSshutdownEnable = "upsv2"
			except: pass

		if u"shutdownSignalFromUPSPin"	 in inp: 
			try: 
				xxx = int(inp["shutdownSignalFromUPSPin"])
				if shutdownSignalFromUPSPin != -1 and xxx != shutdownSignalFromUPSPin:  # is a change, not just switch on 
					U.logger.log(30, "UPS-V2 restart master for new shutdownSignalFromUPSPin GPIO input pin")
					subprocess.call("/usr/bin/python "+G.homeDir+"master.py &" , shell=True)
					time.sleep(2)
				if shutdownSignalFromUPSPin == -1 and xxx != shutdownSignalFromUPSPin and xxx > 1:  # is a change, not just switch on 
					shutdownSignalFromUPSPin =	  xxx
					shutdownSignalFromUPS_InitTime = time.time()
					U.logger.log(20,"UPS-V2 setting shutdown signal event tracking to init in in 2 minutes, using GPIO-pin#{}".format(shutdownSignalFromUPSPin))
					batteryUPSshutdownEnable = "upsv2"
			except: pass

		if typeOfUPS in ["OnlyC","AC"]:
			U.logger.log(30,"UPS-V2 starting serial port for UPS support")
			port = U.getSerialDEV()
			if port =="":
				U.logger.log(20, "UPS-V2 serial port not setup properly, setting  interface to off ")
				shutdownSignalFromUPS_SerialInput =""
				batteryUPSshutdownAtxPercent = -1
			else:		
				U.logger.log(20, "UPS-V2 serial port startiung w port= {}".format(port))
				shutdownSignalFromUPS_SerialInput  = serial.Serial(port, 9600)




		if u"batteryUPSshutdownALCHEMYupcI2C" in inp and inp["batteryUPSshutdownALCHEMYupcI2C"] !="":  
			if batteryUPSshutdownALCHEMYupcI2C != int(inp["batteryUPSshutdownALCHEMYupcI2C"]):
				U.logger.log(20,"UPS-i2c starting i2c UPS support @ i2c: {}".format(inp["batteryUPSshutdownALCHEMYupcI2C"]))
				SMBUS = smbus.SMBus(1)
			batteryUPSshutdownALCHEMYupcI2C = int(inp["batteryUPSshutdownALCHEMYupcI2C"])
			batteryUPSshutdownEnable = "ALCHEMY"



		if batteryUPSshutdownEnable != "" and (u"batteryUPSshutdownAtxPercent" in inp and inp["batteryUPSshutdownAtxPercent"] !=""):  
			xxx= int(inp["batteryUPSshutdownAtxPercent"])
			if batteryUPSshutdownAtxPercent !=-1 and xxx != batteryUPSshutdownAtxPercent:  # is a change, not just switch on 
				U.logger.log(20, "UPS-V2 restart master for new batteryUPSshutdownAtxPercent ")
				subprocess.call("/usr/bin/python "+G.homeDir+"master.py &" , shell=True)
				time.sleep(2)
			if batteryUPSshutdownAtxPercent ==-1 and xxx != batteryUPSshutdownAtxPercent:  # is a change, not just switch on 
				batteryUPSshutdownAtxPercent =	  xxx

		else:
			U.logger.log(20, "UPS interface NOT enabled")



		if u"rebootWatchDogTime" in inp :
			xxx  =int(inp["rebootWatchDogTime"])
			if U.pgmStillRunning("shutdownd"):
				if xxx <=0: subprocess.call("shutdown -c >/dev/null 2>&1", shell=True)
			elif xxx != rebootWatchDogTime:
				rebootWatchDog()
			rebootWatchDogTime= xxx


		if "rPiRestartCommand"	in inp:	 rPiRestartCommand=	   (inp["rPiRestartCommand"])
		if inp["rPiRestartCommand"] !="":
			inp["rPiRestartCommand"] =""
			U.writeJson(G.homeDir+"parameters",inp, sort_keys=True, indent=2)
			#subprocess.call("/usr/bin/python "+G.homeDir+ "copyToTemp.py", shell=True)



		if	rPiRestartCommand.find("restartRPI") >-1:
			subprocess.call("rm "+G.homeDir+"installLibs.done", shell=True)
			U.sendURL(sendAlive="reboot")
			U.doReboot(tt=10., text="re-loading everything due to request from parameter file")


		if	rPiRestartCommand.find("reboot") > -1:
			U.sendURL(sendAlive="reboot")
			U.doReboot(tt=10., text="rebooting due to request from parameter file")


		if	rPiRestartCommand.find("master") > -1:
			U.logger.log(20,"restart due to new input:  {}".format(rPiRestartCommand))
			subprocess.call("/usr/bin/python "+G.homeDir+"master.py &" , shell=True)
			sys.exit()

		time.sleep(1)

	
		if	(rPiRestartCommand.find("rPiCommandPORT") >-1) and G.wifiType =="normal" and G.networkType !="clockMANUAL" and rPiCommandPORT >0:
				startProgam("receiveCommands.py", params=str(rPiCommandPORT), reason=" restart requested from plugin")


		setACTIVEorKILL("INPUTgpio","INPUTgpio.py","")
		time.sleep(1)
		setACTIVEorKILL("INPUTpulse","INPUTpulse.py","INPUTpulse")
		time.sleep(1)
		setACTIVEorKILL("INPUTtouch","INPUTtouch.py","INPUTtouch")
		time.sleep(1)
		setACTIVEorKILL("INPUTtouch16","INPUTtouch16.py","INPUTtouch16")
		time.sleep(1)
		setACTIVEorKILL("INPUTRotarySwitchAbsolute","INPUTRotarySwitchAbsolute.py","INPUTRotarySwitchAbsolute")
		time.sleep(1)
		setACTIVEorKILL("INPUTRotarySwitchIncremental","INPUTRotarySwitchIncremental.py","INPUTRotarySwitchIncremental")
	

		setACTIVEorKILL("myprogram","myprogram.py","")
		setACTIVEorKILL("mysensors","mysensors.py","")

				
		#print " sensors:", sensors
		U.logger.log(20, "sensors		  : " +	 sensorList)

		for ss in G.specialSensorList:
			#U.logger.log(20, "checking sensor if {} ".format(ss))
			if ss in sensors: 
				checkifActive(ss, ss+".py", True)
				time.sleep(1)

		BLEdirectSensorDeviceActive = False
		for sensor in sensors:
			for devId in sensors[sensor]:
				if "isBLElongConnectDevice" in sensors[sensor][devId] and sensors[sensor][devId]["isBLElongConnectDevice"]:
					BLEdirectSensorDeviceActive = True
					U.logger.log(30, u"BLEdirectSensorDeviceActive:{}, sensor:{}, devID:{} sensor[]:{}".format(BLEdirectSensorDeviceActive, sensor, devId,sensors[sensor][devId] ))
					break

		BLEdirectSwitchbotActive = False
		if "output" in inp and "OUTPUTswitchbotRelay" in inp["output"]:
			U.logger.log(30, u"BLEdirectSwitchbotActive:{}".format(inp["output"]["OUTPUTswitchbotRelay"] ))
			BLEdirectSwitchbotActive = True
		else:
			U.logger.log(30, u"BLEdirectSwitchbotActive: not active: {}".format(inp["output"]))

		

		if	not beforeLoop:
			if rPiRestartCommand.find("beacons") >-1 :
					U.killOldPgm(-1,"beaconloop.py")
					checkIfAliveFileOK("beaconloop",force="set")
					startProgam("beaconloop.py", params="", reason=" at startup ")

		sensorEnabled =copy.copy(sensorList)
		firstRead = False
		return 
	except	Exception as e:
		U.logger.log(40, u"Line {} has error={}".format(traceback.extract_tb(sys.exc_info()[2])[-1][1], e))



####################      #########################
def setupX(action="leaveAlone"):
	try:
		if action == "leaveAlone" or  action == "": return 
		U.logger.log(30, "startX called action: >>>{}<<<".format(action))
		if action == "start": 	
			if os.path.isfile(G.homeDir+"pygame.active"):
				# need to reboot 
				U.doReboot(tt=20., text="rebooting due to switch to xterminal from fulls screen pygame")
				exit()
			if not U.pgmStillRunning("startx"):
				U.stopDisplay()
				U.logger.log(30, "start GUI w sudo /usr/bin/startx, exiting master")
				if U.checkIfInFile(["@lxterminal","/home/pi/pibeacon/startmaster.sh"],"/etc/xdg/lxsession/LXDE-pi/autostart") == "not found":
					## add line 
					##     @lxterminal -e "/home/pi/pibeacon/startmaster.sh"
					## to  /etc/xdg/lxsession/LXDE-pi/autostart 

					subprocess.call("mkdir  /etc/xdg/lxsession", shell=True)
					subprocess.call("mkdir  /etc/xdg/lxsession/LXDE-pi/", shell=True)
					subprocess.call("cp "+G.homeDir+"autostart.forxwindows   /etc/xdg/lxsession/LXDE-pi/autostart", shell=True)
					subprocess.call("sudo chmod +x /etc/xdg/lxsession/LXDE-pi/autostart", shell=True)
					subprocess.call("sudo chown -R pi:pi /etc/xdg/lxsession/LXDE-pi/", shell=True)

				subprocess.call("sudo /usr/bin/startx &", shell=True)
				# this will relaunch master.py through autstart --> startmaster.sh
				time.sleep(2)
				if not U.pgmStillRunning("startx"):
					subprocess.call("sudo /usr/bin/startx &", shell=True)
					# sometimes need to start twice
				U.killOldPgm(-1,"callbeacon.py")
				exit()
			else:
				if not U.pgmStillRunning("startmaster.sh"):
					U.doReboot(tt=5., text="rebooting due to xterminal, startmaster.sh is not running")
				U.logger.log(30, "startX already up, no action ")
				
		if action == "stop": 
			U.stopDisplay()
			U.killOldPgm(-1,"startx")

	except	Exception as e:
		U.logger.log(40, u"Line {} has error={}".format(traceback.extract_tb(sys.exc_info()[2])[-1][1], e))


####################      #########################
def startUPSShutdownPinAfterStart():
	global shutdownSignalFromUPSPin, shutdownSignalFromUPS_InitTime
	U.logger.log(30,"UPS-V2 starting shutdown signal event listening pgm using pin#{}".format(shutdownSignalFromUPSPin))
	shutdownSignalFromUPS_InitTime = -1
	GPIO.setup(int(shutdownSignalFromUPSPin), GPIO.IN, pull_up_down = GPIO.PUD_DOWN)
	GPIO.add_event_detect(shutdownSignalFromUPSPin, GPIO.FALLING, callback= shutdownSignalFromUPS, bouncetime=1000)

####################      #########################
def shutdownSignalFromUPS(channel):
	global shutdownSignalFromUPS_pin, shutdownSignalFromUPS_InitTime, batteryUPSshutdown_Vin
	U.logger.log(30, "LOW battery capacity event called for pi# {}".format(channel))
	if channel != shutdownSignalFromUPSPin: return 
	if batteryUPSshutdown_Vin == "GOOD": 
		U.logger.log(30, "LOW battery capacity event reset because Vin is GOOD, wait for 1 minute to restart")
		GPIO.remove_event_detect(shutdownSignalFromUPSPin)
		shutdownSignalFromUPS_InitTime = time.time() - 60 # just 1 minute not 2 
		return 
	U.logger.log(30, "detected LOW battery capacity")
	time.sleep(1)
	if GPIO.input(shutdownSignalFromUPSPin) >1:
		U.logger.log(30, "LOW battery capacity event cancelled ... UPS system back up")
		return
	print "shutting down"
	U.doReboot(tt=10, text="shutdown by UPS signal battery capacity", cmd="sudo killall -9 python; sudo sync;wait 4;sudo shutdown now;sudo wait 3;sudo halt")

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
			U.logger.log(30,"started:%s"%pgm)
		elif ( tag not in theList and tag in  activePGMdict) or force==-1:
			U.killOldPgm(-1,pgm)
			U.killOldPgm(-1,pgm+"3")
			U.logger.log(30,"stopping sensor as no {} enabled".format(tag))
			if tag	in activePGMdict: del activePGMdict[tag] 
		elif tag  in activePGMdict and force ==0:
			del activePGMdict[tag] 
	except	Exception as e:
		U.logger.log(40, u"Line {} has error={}".format(traceback.extract_tb(sys.exc_info()[2])[-1][1], e))





####################      #########################
def doWeNeedToStartTouch(sensorsI, sensorsOld):
	try:
			for n in range(30):
				sensor = "INPUTtouch12-"+str(n)
				if sensor not in sensorsI: continue
				if sensor not in sensorsOld: return 1
				for devId  in sensorsI[sensor]:
					if "gpio" not in sensorsI[sensor][devId]: continue
					if devId not in sensorsOld[sensor]: return 1
					ss = sensorsI[sensor][devId]["gpio"]
					if ss not in sensorsOld[sensor][devId]: return 1
					for nn in range(len(ss)):
						if "gpio" not in ss[nn]: return 1
				U.logger.log(10, "enabled sensor " +sensor)
			return 0
	except	Exception as e:
		U.logger.log(40, u"Line {} has error={}".format(traceback.extract_tb(sys.exc_info()[2])[-1][1], e))
		U.logger.log(30,"start INPUTtouch12: "+ unicode(sensorsI))
	return 0



####################      #########################
def checkifActive(sensorName, pyName, active):
	if active:
		U.logger.log(10," check if active: {}  {}".format(sensorName,pyName))
		checkIfPGMisRunning(pyName, force=True, checkAliveFile=sensorName )
		checkIfAliveFileOK(sensorName)
	else:
		U.killOldPgm(1,pyName)
	return 



#########  start pgms  
def installLibs():
	if U.pgmStillRunning("installLibs.py"): return
	subprocess.call("/usr/bin/python "+G.homeDir+"installLibs.py ", shell=True)
	# wait until finished

	
####################      #########################
def startProgam(pgm, params="", reason=""):
	global python3
	pgm1 = pgm.split(".")[0]
	if pgm1 in python3 and python3[pgm1]: 
		cmd = "sudo -E /usr/bin/python3  "+G.homeDir+pgm+" "+ params+" &"
		U.logger.log(30, ">>>> starting "+pgm+" "+reason+";--  with cmd: "+cmd  )
	else:
		cmd = "sudo /usr/bin/python "+G.homeDir+pgm+"  "+ params+" &"
	U.logger.log(20, ">>>> starting "+pgm+" "+reason+";--  with cmd: "+cmd  )
	subprocess.call(cmd, shell=True)


####################      #########################
def startBLEconnect():
	global sensors, BLEdirectSensorDeviceActive, BLEdirectSwitchbotActive
	try:

		if "BLEconnect" not in sensors and not BLEdirectSensorDeviceActive and not BLEdirectSwitchbotActive:
			U.killOldPgm(-1, "BLEconnect.py")
			return

		if not U.pgmStillRunning("BLEconnect.py") :
			U.logger.log(30, u"BLEdirectSensorDeviceActive:{} , BLEconnect:{} or switchbot active".format(BLEdirectSensorDeviceActive, "BLEconnect" in sensors))
			startProgam("BLEconnect.py", params="", reason="..starting in serial mode ")
		return

	except	Exception, e :
		U.logger.log(40, u"Line {} has error={}".format(traceback.extract_tb(sys.exc_info()[2])[-1][1], e))
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
		U.logger.log(40, u"Line {} has error={}".format(traceback.extract_tb(sys.exc_info()[2])[-1][1], e))
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
		U.logger.log(10, u"checking if running: {}".format(pgm))
		if not U.pgmStillRunning(pgm+".py"):
			U.logger.log(10, u"restarting  {}".format(pgm))
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
		U.logger.log(40, u"Line {} has error={}".format(traceback.extract_tb(sys.exc_info()[2])[-1][1], e))
		return
	return



####################      #########################
def checkIfPGMisRunning(pgmToStart, force=False, checkAliveFile="", parameters=""):
	tt = time.time()
	#U.logger.log(30, u"{};  {};  {};  {}; dt:{:.0f}".format(pgmToStart, force,checkAliveFile, parameters , tt-G.tStart))
	if tt-G.tStart< 15. and not force: return
	try:
		if not U.pgmStillRunning(pgmToStart):
			startProgam(pgmToStart, params=parameters, reason=" -- restarting "+pgmToStart+" ..not running")
			return
		if checkAliveFile !="":
			alive = checkIfAliveFileOK(checkAliveFile)
			#print "pgm to start", pgmToStart, checkAliveFile, alive
			if not alive:
				startProgam(pgmToStart, params="", reason=" -- restarting "+pgmToStart+" ..not running .. no alive file")
				return

	except	Exception, e :
		U.logger.log(40, u"Line {} has error={}".format(traceback.extract_tb(sys.exc_info()[2])[-1][1], e))
	return


####################      #########################
def checkIfbeaconLoopIsRunning():
	global	sensorList, enableiBeacons, sensorAlive, sensors, lastAlive
	try:
		#print "checking beaconloop running start of pgm"
		tt = time.time()
		if tt-G.tStart< 10: return
		
		if U.pgmStillRunning("installLibs.py"): return


		#print "checking beaconloop running 0"
		if G.enableRebootCheck.find("restartLoop")>-1  or G.enableRebootCheck.find("rebootLoop") >-1:
			#print "checking beaconloop running 1"
			if	not checkIfAliveFileOK("beaconloop"):
				#print "checking beaconloop running 2"
			
				if	G.enableRebootCheck.find("rebootLoop") >-1:
					U.sendURL(sendAlive="reboot")
					time.sleep(20)
					U.doReboot(tt=10., text=" Seconds since change in alive file :"+ str(tt- lastAlive["beaconloop"]) +" -- rebooting ")

				#print "checking beaconloop running 3"
				U.killOldPgm(-1,"beaconloop.py")
				checkIfAliveFileOK("beaconloop",force="set")
				startProgam("beaconloop.py", params="", reason=" restart du to old  Alive-File")
			return

		#print "checking beaconloop running 4"
		if not checkIfAliveFileOK("beaconloop"):
					#print "checking beaconloop running	 alive file not ok"
					U.killOldPgm(-1,"beaconloop.py")
					checkIfAliveFileOK("beaconloop",force="set")
					#print "checking if beaconloop running: are starting beaconlooop"
					startProgam("beaconloop.py", params="", reason=" alive file is old ")

	except	Exception as e:
		U.logger.log(40, u"Line {} has error={}".format(traceback.extract_tb(sys.exc_info()[2])[-1][1], e))
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
			except	Exception as e:
				#print " exception ",traceback.extract_tb(sys.exc_info()[2])[-1][1], e
				time.sleep(0.2)
				if os.path.isfile(G.homeDir+"temp/alive."+sensor):
						f = open(G.homeDir+"temp/alive."+sensor,"r")
						data = f.read()
						data =data.strip("\n")
						lastUpdate=float(data)
						f.close()
				else:
					#print " alive file for ", sensor, " not found"
					##subprocess.call("ls -l "+G.homeDir+"temp/", shell=True)
					lastUpdate=0
					try: f.close()
					except: pass

		except	Exception as e:
			U.logger.log(40, u"Line {} has error={}".format(traceback.extract_tb(sys.exc_info()[2])[-1][1], e))
			lastUpdate=0
		#print "alive test 2 for " , sensor, data
			
	   # dont do anything directly after midnight
		dd = datetime.datetime.now()
		if dd.hour == 0 and dd.minute < 10: return alive
 

		#print " alive test 2  delta T",tt - lastUpdate 
		if tt - lastUpdate > 240:  ## nothing for 4 min signal: no alive
			alive = False
			sensorAlive[sensor] = tt
		else:
			sensorAlive[sensor] = lastUpdate
	except	Exception as e:
		U.logger.log(40, u"Line {} has error={}".format(traceback.extract_tb(sys.exc_info()[2])[-1][1], e))
	return alive






####################      #########################
def checkDiskSpace(maxUsedPercent=90,kbytesLeft=500000,dir=""): # check if enough disk space  left (min 10% or 500Mbyte)
	try:
		ret=subprocess.Popen("df" ,shell=True,stdout=subprocess.PIPE,stderr=subprocess.PIPE).communicate()[0]
		lines = ret.split("\n")
		retCode = 0
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
					kbytesAvailable = int(items[3])
					usedPercent=int(items[4].strip("%"))
					if	usedPercent > 90 or kbytesAvailable < 4000 : retCode= 2 ## 90% or 4 Mbyte
				except:
					return 0
			if line.find(G.homeDir+"temp") > -1: # for temp disks
				items = line.split()
				try:
					kbytesAvailable = int(items[3])
					usedPercent=int(items[4].strip("%"))
					if	usedPercent > 90 or kbytesAvailable < 100 : retCode= 3 ## 90% or 100kb
					#U.logger.log(40, u"diskspace: kbytesAvailable={} usedPercent={}".format(kbytesAvailable, usedPercent))
				except:
					return 0

		return retCode
	except	Exception, e :
		U.logger.log(40, u"Line {} has error={}".format(traceback.extract_tb(sys.exc_info()[2])[-1][1], e))


####################      #########################
def rebootWatchDog():
	global rebootWatchDogTime
	try:

		if rebootWatchDogTime <=0:
			if U.pgmStillRunning("shutdownd"):
				subprocess.call("shutdown -c >/dev/null 2>&1", shell=True)
			return


		if U.pgmStillRunning("shutdownd"):
			subprocess.call("shutdown -c >/dev/null 2>&1", shell=True)
			time.sleep(0.1)
			subprocess.call("shutdown +"+str(rebootWatchDogTime)+" >/dev/null 2>&1", shell=True)



	except	Exception, e :
		U.logger.log(40, u"Line {} has error={}".format(traceback.extract_tb(sys.exc_info()[2])[-1][1], e))


####################      #########################
def checkIfRebootRequest():
	###print "into checkIfRebootRequest"
	if	os.path.isfile(G.homeDir+"temp/rebootNeeded"):
		f=open(G.homeDir+"temp/rebootNeeded") 
		reason = f.read()
		f.close()
		os.remove(G.homeDir+"temp/rebootNeeded")
		if reason.find("noreboot")>-1:
			U.logger.log(30, " sending message to plugin re:{}".format(reason) )
			U.sendRebootHTML(reason)
		else:
			U.logger.log(30, " rebooting due to request:{}".format(reason))
			if reason.find("FORCE") >-1:
				U.doReboot(tt=15,force=True)
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
						U.doReboot(tt=20, text=" rebooting due to repeated request:{}".format(reason))
				except: pass
				
			f=open(G.homeDir+"temp/restartCount","w") 
			f.write(str(count+1))
			f.close()
			U.logger.log(30, " starting master due to request:" + reason )
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
	U.logger.log(30, "re booting" )

	rebooted = True
	time.sleep(30)
	U.sendRebootHTML("regular_reboot_at_" +str(rebootHour) +"_hours_requested ")
 
	U.doRebootThroughRUNpinReset()




####################      #########################
def getreading(adc_address,adc_channel):
	global SMBUS
	try:
		max_reading	= 2047.0 # bits
		vref		= 6144. # mV
		volts 		= 0
		# Reset the registers (address and data) and then read the data.
		SMBUS.write_i2c_block_data(adc_address, 0x01, [0x85, 0x83]) #Reset config register
		SMBUS.write_i2c_block_data(adc_address, 0x00, [0x00, 0x00]) #Reset data register
		# Wait till the reading stabilize.
		time.sleep(0.1) # Wait for conversion to finish
		# Trigger the ADC for a one-shot reading on the channel.
		SMBUS.write_i2c_block_data(adc_address, 0x01, [adc_channel, 0x43]) # Initialize channel we want to read.
		time.sleep(0.1) # Wait for conversion to finish
		# Read the data register.
		reading  = SMBUS.read_word_data(adc_address, 0) # Read data register
		# Do the proper bit movements. Refer to data sheet for how the bits are read in.
		valor = ((((reading) & 0xFF) <<8) | ((int(reading) & 0xFFF0)>>8))
		valor = valor >> 4 # 4 LSB bits are ignored.
		volts = valor/max_reading*vref
	except	Exception, e :
		U.logger.log(40, u"Line {} has error={}".format(traceback.extract_tb(sys.exc_info()[2])[-1][1], e))

	return volts


####################      #########################
def getAlechemyUPSdata():
	global batteryUPSshutdownALCHEMYupcI2C
	try:
		#U.logger.log(20, u"into getAlechemyUPSdata")
		channel0	= 0b11000001   # Measure V-in
		channel1	= 0b11010001   # Measure V-out
		channel2	= 0b11100001   # Measure V-battery
		channel3	= 0b11110001   # Measure V across NTC, to measure Temperature.
		V_batt_min	= 3100. # Minimum V of battery capacity too low set to 0.
		capacity	= (3900 - V_batt_min)
		Vin			= 0
		Vbat		= 0
		Vout		= 0
		TempC		= 0
		Vtext		= ""

		Vin 		= getreading(batteryUPSshutdownALCHEMYupcI2C, channel0)
		# Read Channel 1 - Battery V
		Vbat		= getreading(batteryUPSshutdownALCHEMYupcI2C, channel1)
		# Read Channel 2 - Output V
		Vout 		= getreading(batteryUPSshutdownALCHEMYupcI2C, channel2)
		# Read Channel 3 - Temperature.
		TempC 		= (4.0 - getreading(batteryUPSshutdownALCHEMYupcI2C, channel3)/1000.) / 0.0408 # Temperature in C 
		if Vin < 3000:
			Vtext = "VinOff"

	except	Exception, e :
		U.logger.log(40, u"Line {} has error={}".format(traceback.extract_tb(sys.exc_info()[2])[-1][1], e))

	return Vin, Vtext, Vbat, int(100.*min(1, (Vbat - V_batt_min)/capacity)), Vout, TempC




####################      #########################
def getupsv2UPSdata():
	global shutdownSignalFromUPS_SerialInput
	try:
		#U.logger.log(20, u"into getupsv2UPSdata")
		# first flush and wait for new data , sending every 1 sec
		#print "inWaiting() bf flush:",shutdownSignalFromUPS_SerialInput.inWaiting()
		#self.ser.flushInput()		
		#time.sleep(0.1)
		##
		# GOOD,BATCAP 84,Vout 5204 $
		#$ SmartUPS V1.00,Vin GOOD,BATCAP 84,Vout 5204 $
		#$ SmartUPS V1.00,Vin NG 
		####

		uart_string =""
		good  = ""
		batCap = ""
		Vout = ""
		Vin  = 0
		Vtext = ""
		for ii in range(10):
			nn = shutdownSignalFromUPS_SerialInput.inWaiting()
			#print "inWaiting", nn
			if  nn !=0:
				time.sleep(0.01)
				nn = shutdownSignalFromUPS_SerialInput.inWaiting()
				uart_string = shutdownSignalFromUPS_SerialInput.read(nn)
				# check if we got a full line
				#$ SmartUPS V1.00,Vin GOOD,BATCAP 84,Vout 5204 $
				if len(uart_string) > 30 and uart_string[-2] =="$" and uart_string[0] =="$": break
				if len(uart_string) > 50 : break
				if uart_string[0] !="$": continue
				#print "uart_string not complete - len:",len(uart_string)," ::",uart_string.replace("\n","--"),"::end"
				time.sleep(0.2)
				nn = shutdownSignalFromUPS_SerialInput.inWaiting()
				uart_string += shutdownSignalFromUPS_SerialInput.read(nn)
				if len(uart_string) > 30 and uart_string[-2] =="$": 
					#print "uart_string not complete after 2. read - len:",len(uart_string)," ::",uart_string.replace("\n","--"),"::end"
					break
				#print "uart_string  after continue to read not complete - len:",len(uart_string)," ::",uart_string.replace("\n","--"),"::end"
			
			
			else:
				time.sleep(0.2)
		lines = uart_string.strip().split("\n")
		nLines = len(lines)

		for nn in range(nLines):
			if lines[nLines-nn-1].count("$") == 2 and lines[nLines-nn-1][-1] =="$":
				good = lines[nLines-nn-1].strip().strip("$").strip().split(",")	
				break			

		if good == "":
			return "", "no connection", 0, 0, 0

#	print(uart_string)
		#print "tries",ii, "data", good 
		for dd in good:
			if   "SmartUPS" in dd: version 	= dd.split(" ")[1]
			elif "Vin" 		in dd: Vtext	= dd.split(" ")[1]
			elif "BATCAP" 	in dd: batCap 	= int(dd.split(" ")[1])
			elif "Vout" 	in dd: Vout 	= float(dd.split(" ")[1])/1000.
		return version, Vtext, batCap, Vout
	except	Exception, e :
		U.logger.log(40, u"Line {} has error={}".format(traceback.extract_tb(sys.exc_info()[2])[-1][1], e))

	return version, "no connection", batCap, Vout


####################      #########################

def getUPSdata():
	global shutdownSignalFromUPS_SerialInput
	try:
		version 	= ""
		batCap 		= 0
		Vout 		= 0
		Vin			= 0
		TempC		= 0
		Vbat		= ""
		Vtext		= "" 

		if batteryUPSshutdownALCHEMYupcI2C != "":
			Vin, Vtext, Vbat, batCap, Vout, TempC = getAlechemyUPSdata()
			return "ALCHEMY", Vtext, Vin, Vbat, batCap, Vout, TempC

		elif shutdownSignalFromUPS_SerialInput != "": 
			version, Vtext, batCap, Vout = getupsv2UPSdata()
			return version, Vtext, Vin, Vbat, batCap, Vout, TempC

	except	Exception, e :
		U.logger.log(40, u"Line {} has error={}".format(traceback.extract_tb(sys.exc_info()[2])[-1][1], e))

	return version, "no connection", Vin, Vbat, batCap, Vout, 0


####################      #########################
def checkIfShutDownVoltage():
	global shutdownInputPin, shutdownPinVoltSensor,  batteryMinPinActiveTimeForShutdown, inputPinVoltRawLastONTime
	global batteryChargeTimeForMaxCapacity, batteryCapacitySeconds
	global batteryStatus,lastWriteBatteryStatus
	global batteryUPSshutdownAtxPercent, shutdownSignalFromUPS_SerialInput, shutdownSignalFromUPS_LastCall , shutdownSignalFromUPS_LastCount, batteryUPSshutdown_Vin
	global batteryUPSshutdownALCHEMYupcI2C, batteryUPSshutdownEnable
	global checkIfShutDownVoltageLastCheck


	if batteryUPSshutdownEnable == "" : return 

	if time.time() - checkIfShutDownVoltageLastCheck < 20: return 
	checkIfShutDownVoltageLastCheck = time.time()

	version = ""
	Vtext	= ""
	Vin		= ""
	batCap	= ""
	Vbat	= ""
	Vout	= ""
	temp 	= ""
	try:
		if batteryUPSshutdownAtxPercent > 1:
			try: 
				ii = shutdownSignalFromUPS_LastCall
			except: # init if called first time 
				shutdownSignalFromUPS_LastCall = time.time() -100
				shutdownSignalFromUPS_LastCount = 0

			version, Vtext, Vin, Vbat, batCap, Vout, temp = getUPSdata()
			U.logger.log(10, "UPS-V2 data: Vin {:.0f}[mV], Vtext:{}, Vbat:{:.0f}, battery-capacity@ {:.0f}[%], Vout {:.0f}[mV], temp:{:.1f}".format(Vin, Vtext, Vbat, batCap, Vout, temp)) 

			if time.time() - shutdownSignalFromUPS_LastCall > 20:
				shutdownSignalFromUPS_LastCall = time.time()

				U.logger.log(10, "UPS-V2 data: Vin {:.0f}[mV], Vtext:{}, Vbat:{:.0f}, battery-capacity@ {:.0f}[%], Vout {:.0f}[mV], temp:{:.1f}".format(Vin, Vtext, Vbat, batCap, Vout, temp)) 

				if version not in ["ALCHEMY",""]:
					if Vtext == "NG" and batCap != "":
						if int(batCap) < batteryUPSshutdownAtxPercent:
							shutdownSignalFromUPS_LastCount +=1
							U.logger.log(30, "UPS-V2 Vin is off and battery capacity {}%  below limit {}%.. checking countdown to 0: {}".format(batCap, batteryUPSshutdownAtxPercent, 5-shutdownSignalFromUPS_LastCount)) 
							if shutdownSignalFromUPS_LastCount > 3:
								U.logger.log(30, "UPS-V2.. rebooting after 4 wait / test".format(batteryUPSshutdownAtxPercent, batCap)) 
								U.doReboot(tt=10,  text="UPS-V2 shutdown by UPS  battery capacity message", cmd="sudo killall -9 python;sudo sync; wait 4;sudo shutdown now;sudo wait 3;sudo halt")

				if version in ["ALCHEMY"] and batCap != "" and Vtext == "VinOff":
						if int(batCap) < batteryUPSshutdownAtxPercent:
							shutdownSignalFromUPS_LastCount +=1
							U.logger.log(30, "UPS- Alchemy Vin is off and battery capacity {}%  below limit {}%.. checking countdown to 0: {}".format(batCap, batteryUPSshutdownAtxPercent, 4-shutdownSignalFromUPS_LastCount)) 
							if shutdownSignalFromUPS_LastCount > 2:
								U.logger.log(30, "UPS-Alchemy.. rebooting after 4 wait / test".format(batteryUPSshutdownAtxPercent, batCap)) 
								U.doReboot(tt=10,  text="UPS-Alchemy shutdown by UPS  battery capacity message", cmd="sudo killall -9 python;sudo sync; wait 4;sudo shutdown now;sudo wait 3;sudo halt")



		if shutdownPinVoltSensor > 1 or batteryUPSshutdownALCHEMYupcI2C != "": 
			try:
				ii = lastWriteBatteryStatus
			except:
				try:
					lastWriteBatteryStatus = 0
					#print "checkIfShutDownVoltage initializing"
					batteryStatus, raw= U.readJson(G.homeDir+"batteryStatus")
					delItem = []
					for item in batteryStatus:
						if item not in ["timeCharged", "testTime","chargeLevel","inputPinVoltRawLastONTime","batteryTimeLeftEndOfCharge","status","batteryCapacitySeconds","batteryChargeTimeForMaxCapacity","batteryMinPinActiveTimeForShutdown", "batteryTimeLeft"]:
							delItem.append(item)
					for item in delItem:
						del batteryStatus[item]
					for item in ["timeCharged", "testTime","chargeLevel","inputPinVoltRawLastONTime","batteryTimeLeftEndOfCharge","status","batteryCapacitySeconds","batteryChargeTimeForMaxCapacity","batteryMinPinActiveTimeForShutdown", "batteryTimeLeft"]:
						if item not in batteryStatus:
							batteryStatus[item] = 0
	
					if shutdownPinVoltSensor > 1:
						#print	"setting shutdownPinVoltSensor to GPIO: " + str(shutdownPinVoltSensor) 
						U.logger.log(30, "setting shutdownPinVoltSensor to GPIO: {}".format(shutdownPinVoltSensor))
						try: GPIO.setup(int(shutdownPinVoltSensor), GPIO.IN, pull_up_down = GPIO.PUD_UP)	# use pin shutDownPin  to input reset
						except: pass
						inputPinVoltRawLastONTime = time.time()
				except: pass
				if batteryStatus == {}: 
					batteryStatus ={"timeCharged":0, "testTime":time.time(),"chargeLevel":0,"inputPinVoltRawLastONTime":0,"batteryTimeLeftEndOfCharge":0,"status":"","batteryCapacitySeconds":0,"batteryChargeTimeForMaxCapacity":0,"batteryMinPinActiveTimeForShutdown":0,"batteryTimeLeft":0}
			try:
				#print "batteryStatus ", batteryStatus
				batteryStatus["batteryChargeTimeForMaxCapacity"] 			= batteryChargeTimeForMaxCapacity
				batteryStatus["batteryCapacitySeconds"] 					= batteryCapacitySeconds
				batteryStatus["batteryMinPinActiveTimeForShutdown"]			= batteryMinPinActiveTimeForShutdown

				if version == "ALCHEMY":
					U.logger.log(10, "checkIfShutDownVoltage  Vtext:{};  batteryStatus:{}".format(Vtext, json.dumps(batteryStatus, sort_keys=True, indent=2) ))
					if Vtext != "VinOff":
							batteryStatus["timeCharged"] 						+= (time.time() - batteryStatus["testTime"]) 
							batteryStatus["timeCharged"]						= round(min(batteryStatus["timeCharged"], batteryChargeTimeForMaxCapacity),1) # x hour charge time should get to 90+%
							batteryStatus["inputPinVoltRawLastONTime"]			= round(time.time(),1)
							batteryStatus["testTime"]							= round(time.time(),1)
							batteryStatus["chargeLevel"] 						= round(max( 0., batteryStatus["timeCharged"]/batteryChargeTimeForMaxCapacity ),4)
							batteryStatus["batteryTimeLeftEndOfCharge"]			= round(min(batteryMinPinActiveTimeForShutdown, batteryCapacitySeconds*batteryStatus["chargeLevel"]),1)
							if batteryStatus["chargeLevel"] == 1:				  batteryStatus["status"]	= "charged"
							else:  												  batteryStatus["status"]	= "charging"
							batteryStatus["batteryTimeLeft"]					= batteryStatus["batteryTimeLeftEndOfCharge"]
							lastWriteBatteryStatus= writeJson2(batteryStatus,G.homeDir+"batteryStatus", lastWriteBatteryStatus)
							return
				elif version != "ALCHEMY":
					for ii in range(2):
						if shutdownPinVoltSensor > 3-1 and  GPIO.input(int(shutdownPinVoltSensor)) == 1:
							batteryStatus["timeCharged"] 						+= (time.time() - batteryStatus["testTime"]) 
							batteryStatus["timeCharged"]						= round(min(batteryStatus["timeCharged"],batteryChargeTimeForMaxCapacity),1) # x hour charge time should get to 90+%
							batteryStatus["inputPinVoltRawLastONTime"]			= round(time.time(),1)
							batteryStatus["testTime"]							= round(time.time(),1)
							batteryStatus["chargeLevel"] 						= round(max( 0., batteryStatus["timeCharged"] /batteryChargeTimeForMaxCapacity ),4)
							batteryStatus["batteryTimeLeftEndOfCharge"]			= round(min(batteryMinPinActiveTimeForShutdown, batteryCapacitySeconds*batteryStatus["chargeLevel"]),1)
							if batteryStatus["chargeLevel"] == 1:			  	  batteryStatus["status"]	= "charged"
							else:  												  batteryStatus["status"]	= "charging"
							batteryStatus["batteryTimeLeft"]					= batteryStatus["batteryTimeLeftEndOfCharge"]
							lastWriteBatteryStatus= writeJson2(batteryStatus,G.homeDir+"batteryStatus", lastWriteBatteryStatus)
							return
						time.sleep(0.1)
				else:
					pass

				batteryStatus["batteryTimeLeftEndOfCharge"]		= round(min(batteryMinPinActiveTimeForShutdown, batteryCapacitySeconds*batteryStatus["chargeLevel"]),1)
				batteryStatus["timeCharged"] 					= round(batteryStatus["timeCharged"] * max( 0, 1. -  (time.time()-batteryStatus["testTime"])/max(1,batteryCapacitySeconds)  ),5)#discharging
				batteryStatus["testTime"] 						= round(time.time(),1)
				batteryStatus["batteryTimeLeft"] 				= round( (batteryStatus["inputPinVoltRawLastONTime"] + batteryStatus["batteryTimeLeftEndOfCharge"]) - time.time(),1)
				if batteryStatus["batteryTimeLeft"] > 0: 
					batteryStatus["status"]						= "dis-charging"
					lastWriteBatteryStatus = writeJson2(batteryStatus,G.homeDir+"batteryStatus", lastWriteBatteryStatus)
					U.logger.log(20, "checkIfShutDownVoltage  --> ac power off (pin {} low),  discharging battery, batteryStatus:{}".format(shutdownPinVoltSensor if version != "ALCHEMY" else Vtext, json.dumps(batteryStatus, sort_keys=True, indent=2) ))
					return 

				batteryStatus["status"]							= "empty"
				lastWriteBatteryStatus= writeJson2(batteryStatus,G.homeDir+"batteryStatus", 0)

			except	Exception, e :
					U.logger.log(40, u"Line {} has error={}".format(traceback.extract_tb(sys.exc_info()[2])[-1][1], e))
					return
			U.logger.log(30, "checkIfShutDownVoltage: rebooting " )
			#this will send and HTML to indigo and then issue a shutdown command
			U.sendRebootHTML("battery empty", reboot=False, wait=15.)

	except	Exception, e :
			U.logger.log(40, u"Line {} has error={}".format(traceback.extract_tb(sys.exc_info()[2])[-1][1], e))

	return 

####################      #########################
def writeJson2(data, fileName, lastWriteBatteryStatusI):
	try:
		if time.time() - lastWriteBatteryStatusI < 20: return lastWriteBatteryStatusI
		U.writeJson(fileName, data, sort_keys=True, indent=0)
	except: pass
	return time.time()
	


####################      #########################
def checkLogfiles():
	global maxSizeOfLogfileOnRPI
	try:
		retCode =  checkDiskSpace(maxUsedPercent=80, kbytesLeft=500000) 	 # (need 500Mbyte free or 80% max

		if retCode in[1,2]: 	 # (need 500Mbyte free or 80% max
			subprocess.call("sudo  chown -R pi:pi /var/log/*", shell=True)
			subprocess.call("sudo echo "" >  /var/log/pibeacon", shell=True)
			files = subprocess.Popen("find /var/log -type f",shell=True,stdout=subprocess.PIPE,stderr=subprocess.PIPE).communicate()[0].split()
			for f in files:
				subprocess.call("sudo echo "" >  {}".format(f) , shell=True)
			try: U.logger.log(30, "reset  logfiles  due to  limited disk space ")
			except: pass
		elif retCode ==3:
			U.restartMyself(reason="not enough space in temp directory, restart master should clean it up ", delay=20, doPrint =True)
			time.sleep(20)

			
		retCode =  checkDiskSpace(maxUsedPercent=80, kbytesLeft=500000) 	 # (need 500Mbyte free or 80% max

		if retCode in [1,2]:   # (need 500Mbyte free or 80% max
			U.restartMyself(reason=" out of space ")
			subprocess.call("sudo killall -9 python; sleep 2;sudo reboot -f", shell=True)

		try:
			if os.path.isfile("{}permanent.log".format(G.homeDir)) and os.path.getsize("{}permanent.log".format(G.homeDir)) > 20000:
				subprocess.call("tail -300 {}permanent.log > {}tempFileaa ; mv {}tempFileaa  {}permanent.log".format(G.homeDir,G.homeDir,G.homeDir,G.homeDir), shell=True)
		except: pass

		if not os.path.isfile(G.logDir+"pibeacon"): return 
		nBytes = os.path.getsize(G.logDir+"pibeacon")
		U.logger.log(10, "checking logfile size: {}".format(nBytes))
		if nBytes > maxSizeOfLogfileOnRPI: # default 10 mBytes
			if  os.path.isfile(G.logDir+"pibeacon-1.log"):  
				subprocess.call("sudo rm "+G.logDir+"pibeacon-1 ", shell=True)
			subprocess.call("sudo cp "+G.logDir+"pibeacon "+G.logDir+"pibeacon-1 ", shell=True)
			subprocess.call("sudo  chown -R pi:pi /var/log/*", shell=True)
			subprocess.call("sudo echo "" >  /var/log/pibeacon", shell=True)
	except	Exception, e :
		print u"Line {} has error={}".format(traceback.extract_tb(sys.exc_info()[2])[-1][1], e)
		return


	U.doRebootThroughRUNpinReset()



####################      #########################
def checkRamDisk(loopCount=99):
	try:
		if loopCount < 10: return 

		global useRamDiskForLogfiles
		ret=subprocess.Popen("df" ,shell=True,stdout=subprocess.PIPE,stderr=subprocess.PIPE).communicate()[0]
		lines = ret.split("\n")
	  
		changed = False
		ramDiskActive = False
		for line in lines:
			if line.find("/var/log") > -1: 
				ramDiskActive = True
				break
			
		if useRamDiskForLogfiles == "1" and not ramDiskActive: 
			U.logger.log(30," ramdisk requested, but not active .. adding to /etc/fstab")
			U.logger.log(30," ramdisk requested, checkIfInFile: {}, or {}".format(U.checkIfInFile(["tmpfs","/var/log"],"/etc/fstab"), U.checkIfInFile(["#tmpfs","/var/log"],"/etc/fstab") ))
			if	U.checkIfInFile(["tmpfs","/var/log"],"/etc/fstab") == "not found" or U.checkIfInFile(["#tmpfs","/var/log"],"/etc/fstab") =="found":
				U.removefromFile("/var/log","/etc/fstab")
				U.uncommentOrAdd("tmpfs	  /var/log	  tmpfs	   defaults,noatime,nosuid,mode=0755,size=60m	 0 0","/etc/fstab")
				U.logger.log(30," master needs to reboot, added ram disk for /var/log ")
				changed = True

		if useRamDiskForLogfiles == "0" and ramDiskActive: 
			U.logger.log(30," ramdisk off, but  active .. removing from /etc/fstab")
			U.logger.log(30," ramdisk requested, checkIfInFile: {}, or {}".format(U.checkIfInFile(["tmpfs","/var/log"],"/etc/fstab"), U.checkIfInFile(["#tmpfs","/var/log"],"/etc/fstab") ))
			U.removefromFile("/var/log","/etc/fstab")
			U.logger.log(30," master needs to reboot, removed ram disk for /var/log ")
			changed = True

		if changed:
			U.logger.log(30, " master  waiting to reboot due to ram disk change")
			time.sleep(60) # give it some time, it should never happen here 
			U.sendRebootHTML("change_in_ramdisk_for_logfiles")
	except	Exception, e :
		U.logger.log(40, u"Line {} has error={}".format(traceback.extract_tb(sys.exc_info()[2])[-1][1], e))
	return 




####################      #########################
def delayAndWatchDog():
	global shutdownInputPin, lastshutdownInputPinTime, shutdownPinVoltSensor, rebootWatchDogTime,lastrebootWatchDogTime

	try:
		for xx in range(20): # thats 20 seconds
			time.sleep(1)
			tt = time.time()

			if (shutdownPinVoltSensor >1 or batteryUPSshutdownAtxPercent >1) and  tt - G.tStart > 20:
				checkIfShutDownVoltage()

			if shutdownInputPin >1 :
				if GPIO.input(shutdownInputPin) == 1: 
					lastshutdownInputPinTime = tt

				### print "master: shutdown pin #%d;  secs pressed:%.1f"%(shutdownInputPin,tt - lastshutdownInputPinTime )
				if tt - G.tStart > 10  and tt - lastshutdownInputPinTime > 3:
					U.doReboot(tt=10,  text="... shutdown by button/pin", cmd="sudo killall -9 python; sudo sync;wait 9;sudo halt")

			if xx%5 ==1 and False:
				if	os.path.isfile("/run/nologin"):
					subprocess.call("rm /run/nologin &", shell=True)

				if	rebootWatchDogTime > 0 and tt - lastrebootWatchDogTime > (rebootWatchDogTime*60 -20.): # rebootWatchDogTime is in minutes
					lastrebootWatchDogTime = tt
					rebootWatchDog()

			if xx%3 ==1: # check web status every 3 secs while waiting 
				U.checkwebserverINPUT()
					

	except	Exception, e :
		U.logger.log(40, u"Line {} has error={}".format(traceback.extract_tb(sys.exc_info()[2])[-1][1], e))



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
					U.logger.log(10, "sending message to plugin re:" + line )
					U.sendURL(sendAlive="alive",text="checkSystemLOG_register_dump_occured_reboot_"+line)
		
					U.doReboot(tt=15, text="restart due to register dump:", force=True)
			
	except	Exception, e :
		U.logger.log(40, u"Line {} has error={}".format(traceback.extract_tb(sys.exc_info()[2])[-1][1], e))


####################      #########################
def cycleWifi():
	eth0IP, wifi0IP, G.eth0Enabled, G.wifiEnabled = U.getIPCONFIG()
	#print "master:	 is wifi enabled : "+str(G.wifiEnabled)
	if G.wifiEnabled:
		indigoServerOn, changed, connected = U.getIPNumberMaster(quiet=True)
		if not connected:
			#print "master:	 cycle wlan0"
			subprocess.call("sudo /sbin/ifconfig wlan0 down; sudo /sbin/ifconfig wlan0 up", shell=True)
			# cycle wlan
	return

####################      #########################
def doGPIOAfterBoot():
	global GPIOTypeAfterBoot1, GPIOTypeAfterBoot2, GPIONumberAfterBoot1, GPIONumberAfterBoot2

	try:
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
	except	Exception, e :
		U.logger.log(40, u"Line {} has error={}".format(traceback.extract_tb(sys.exc_info()[2])[-1][1], e))
	return 

	
	
####################      #########################
def checkTempForFanOnOff(force = False):
	global fanGPIOPin, fanTempOnAtTempValue, fanTempOffAtTempValue, lastTempValue, fanWasOn,  lastTimeTempValueChecked, fanTempName, fanTempDevId, fanEnable
	global fanOnTimePercent, fanOntimeData, fanOntimePeriod
	try:
		#print "into checkTempForFanOnOff",fanTempName, fanTempDevId, fanEnable, fanTempOnAtTempValue, fanTempOffAtTempValue, lastTimeTempValueChecked, lastTempValue
		#U.logger.log(30, u"checkTempForFanOnOff fanEnable:{}  fanTempName:{}   fanGPIOPin:{}".format(fanEnable, fanTempName, fanGPIOPin))
		if not(fanEnable =="0" or fanEnable =="1"):						return
		if fanTempName   == "": 										return
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

		#U.logger.log(30, u"checkTempForFanOnOff temp:{}  fanTempOnAtTempValue:{}".format(temp, fanTempOnAtTempValue))

		if temp > fanTempOnAtTempValue: 
			fanOntimeData.append([time.time(),1])

			#print " fan on"
			if  fanWasOn <=0: 
				if fanEnable =="1": GPIO.output(fanGPIOPin, True)
				if fanEnable =="0": GPIO.output(fanGPIOPin, False)
				fanWasOn = 1
		else:
			#print " fan off"  .. only if 1 degree lower than target
			if  temp < (fanTempOnAtTempValue - fanTempOffAtTempValue ): 
				fanOntimeData.append([time.time(),0])
			else:
				fanOntimeData.append([time.time(),1])

			if  ( fanWasOn == 1 and temp < (fanTempOnAtTempValue - fanTempOffAtTempValue ) ) or fanWasOn == 0: 
				if fanEnable =="0": GPIO.output(fanGPIOPin, True)
				if fanEnable =="1": GPIO.output(fanGPIOPin, False)
				fanWasOn = -1

		if True: 
			fanOnTimePercent = ""
			tempTime = copy.copy(fanOntimeData)
			for tt in tempTime:
				if time.time() - tt[0] < fanOntimePeriod: break
				del(fanOntimeData[0])
			#print tempTime
			#print fanOntimeData
			if len(fanOntimeData) > 1:
				fanOnTimePercent = 0.
				for nn in range(1,len(fanOntimeData)):
					if fanOntimeData[nn-1][1]: 
						fanOnTimePercent += fanOntimeData[nn][0] - fanOntimeData[nn-1][0]
				fanOnTimePercent = fanOnTimePercent / max(1.,fanOntimeData[-1][0] - fanOntimeData[0][0])
			#print fanOnTimePercent
				
		lastTempValue = temp

	except	Exception, e :
		U.logger.log(40, u"Line {} has error={}".format(traceback.extract_tb(sys.exc_info()[2])[-1][1], e))
	return

	
	
####################      #########################
def fixRcLocal(sleepTime):
	try:
		if not os.path.isfile(G.homeDir+"/etc/rc.local"):
			subprocess.call("cp  /etc/rc.local /home/pi/pibeacon/rc.local", shell=True)

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
			U.logger.log(20, "writing new rc.local file with new line:\n {}".format(test))
			f=open(G.homeDir+"temp/rc.local","w")
			f.write(out)
			f.close()
			subprocess.call("sudo cp "+G.homeDir+"temp/rc.local /etc/rc.local ", shell=True)
			subprocess.call("sudo chmod a+x /etc/rc.local", shell=True)


		f=open("/home/pi/pibeacon/callbeacon.py","r")
		callbeacon = f.read().split("\n")
		f.close()

		out      = ""
		writeOut = ""
		test     = ""
		for line in callbeacon:
			if line.find("master.sh ")>-1 and writeOut =="":
				if sleepTime =="0":
					test = 'subprocess.call("cd {}; nohup /bin/bash master.sh > /dev/null 2>&1 & ".format(homeDir), shell=True)'
				else:
					test = 'subprocess.call("sleep '+sleepTime+ ';cd {}; nohup /bin/bash master.sh > /dev/null 2>&1 & ".format(homeDir), shell=True)'
				if line == test:
					break
				else:
					out+=test+"\n"
					if test.find("sleep") > -1:	writeOut =" new sleep time"
					else: 						writeOut ="set sleep to 0"
			else:
				out+=line+"\n"

		if writeOut != "":
			f=open("/home/pi/pibeacon/callbeacon.py","w")
			f.write(out)
			f.close()

		## updating callbeacon file 
		U.logger.log(20, "writing callbeacon.py file")
		subprocess.call("cp /home/pi/pibeacon/callbeacon.py /home/pi/callbeacon.py", shell=True)
	except	Exception, e :
		U.logger.log(40, u"Line {} has error={}".format(traceback.extract_tb(sys.exc_info()[2])[-1][1], e))
	return
 


####################      #########################
def checkFSCHECKfile():
	
	try:
		f=open(G.homeDir+"temp/dosfsck","r")
		data = f.read()
		f.close()
		if data.find("data may be corrupt") >-1: # try again, see if fixed..
			dataSend = u"dosfsck has error (was fixed after boot): "+"/--/".join((data.split("\n"))[0:10])
			subprocess.call("dosfsck -w -r -l -a -v -t /dev/mmcblk0p1 > "+G.homeDir+"temp/dosfsck", shell=True)
			f=open(G.homeDir+"temp/dosfsck","r")
			data = f.read()
			f.close()
			if data.find("data may be corrupt") >-1: # not fixed, send msg to plugin 
				dataSend = u"dosfsck has error also after re-run: "+ "/--/".join((data.split("\n"))[0:10])

			U.logger.log(20, dataSend)
			U.sendURL(sendAlive="alive",text=dataSend)
	except	Exception, e :
		U.logger.log(40, u"Line {} has error={}".format(traceback.extract_tb(sys.exc_info()[2])[-1][1], e))

	return 


####################      #########################
def tryRestartNetwork():
	global startNetworkTimer

	try:
		startNetworkTimer
	except:
		startNetworkTimer = 0
	try:
		if time.time() - startNetworkTimer < 120: return 
		startNetworkTimer = time.time()
		if len(G.ipAddress) < 8:
			ret = subprocess.Popen("sudo /etc/init.d/networking restart&" 	,shell=True,stdout=subprocess.PIPE,stderr=subprocess.PIPE).communicate()[0].strip("\n").strip()
			U.logger.log(30, u"(re)starting network, response: {}".format(ret))
			time.sleep(10)
			indigoServerOn, changed, connected = U.getIPNumberMaster(quiet=True)
			if G.ipAddress != "" and G.networkType.find("indigo") > -1:
				U.restartMyself(reason=u" ip number is back on")
	except	Exception, e :
		U.logger.log(40, u"Line {} has error={}".format(traceback.extract_tb(sys.exc_info()[2])[-1][1], e))
	return

####################      #########################
def checkIfclearHostsFile():

	try:
		if clearHostsFile: 
			U.logger.log(20, u"resetting file /home/pi/.ssh/known_hosts")
			subprocess.call(u"sudo rm /home/pi/.ssh/known_hosts", shell=True)
	except	Exception, e :
		U.logger.log(40, u"Line {} has error={}".format(traceback.extract_tb(sys.exc_info()[2])[-1][1], e))
	return 

####################      #########################
def checkPythonLibs():
	try:
		subprocess.call(u"sudo /usr/bin/python3 {}checkForInclude-py3.py & ".format(G.homeDir), shell=True)
		subprocess.call(u"sudo /usr/bin/python {}checkForInclude-py2.py & ".format(G.homeDir), shell=True)
	except	Exception, e :
		U.logger.log(40, u"Line {} has error={}".format(traceback.extract_tb(sys.exc_info()[2])[-1][1], e))
	return 

####################      #########################
def checknetwork0():
	try:
		indigoServerOn, changed, connected = u"", u"", u""

		if G.networkType in G.useNetwork and G.wifiType == u"normal":
			for ii in range(2):
				if ii > 0 :
					if G.networkType.find("clock") >-1: 
						U.logger.log(30, u"no ip number working, giving up, running w/o ip number or indigo server, setting mode to clockMANUAL = stand alone")
						G.networkType = u"clockMANUAL"
						U.setNetwork(u"off")
						break
	
				indigoServerOn, changed, connected = U.getIPNumberMaster(quiet=ii<2)
				if not indigoServerOn  or G.ipAddress == "":
					U.setNetwork(u"off")
					time.sleep(5)
					U.logger.log(30, u"no ip number working, trying again, indigoServerOn:{}, myip:{}".format(indigoServerOn, G.ipAddress))
				else:
					U.clearNetwork()
					U.logger.log(20, u"ip number found  ip:{}".format(G.ipAddress))
					break

		else:
			if G.networkType.find(u"clock") > -1 and G.wifiType == u"normal":
				for ii in range(2):
					if ii > 0:
						U.logger.log(30,u"no ip number working, giving up, setting mode to clockMANUAL = stand alone, netwtype was:{}".format(G.networkType))
						G.networkType = u"clockMANUAL"
						break
	
					indigoServerOn, changed,connected = U.getIPNumberMaster(quiet=ii<2, noRestart=True)
					if not indigoServerOn or G.ipAddress == u"":
						U.setNetwork(u"off")
						time.sleep(5)
						U.logger.log(30, u"no  indigo ip number working, trying again, indigoServerOn:{}, myip:{}".format(indigoServerOn, G.ipAddress))
					else:
						U.clearNetwork()
						U.logger.log(20, u"ip number found and connected to indigo  ip:{}".format( G.ipAddress))
						break
	except	Exception, e :
		U.logger.log(40, u"Line {} has error={}".format(traceback.extract_tb(sys.exc_info()[2])[-1][1], e))

	return indigoServerOn, changed, connected 

####################      #########################
def checkIfFirstStart():
	global configured, adhocWifiStarted
	try:
		U.logger.log(20,u"RPistrt configured at>{}<, userIdOfServer:{}".format(configured, G.userIdOfServer) )
		if configured == "" and G.userIdOfServer == u"xxstartxx": 
			U.logger.log(20,u"RPi not configured yet, waiting for config or wifi; networkType:{}; useNetwork:{}, wifiType:{}".format(G.networkType,G.useNetwork,G.wifiType) )
			if G.networkType  in G.useNetwork and G.wifiType == u"normal":
				wifiWaiting  = True
				GPIO.setup(26, GPIO.IN, pull_up_down = GPIO.PUD_UP)
				if GPIO.input(26) == 0 and G.userIdOfServer	 == u"xxstartxx":
						## start adhoc wifi
						for ii in range(500):
							if G.userIdOfServer	 == u"xxstartxx":
								if  adhocWifiStarted < 0: 
									U.logger.log(30,u" launching at start startAdhocWifi " )
									U.startAdhocWifi()
									U.startwebserverINPUT(startWebServerINPUT)
							if wifiWaiting: 
								if U.checkwebserverINPUT():
									wifiWaiting= False
									time.sleep(10)
									break

				if G.userIdOfServer	 == "xxstartxx":
						for ii in range(300):
							if G.userIdOfServer	 == u"xxstartxx":
								U.logger.log(30, u" master not configured yet, lets wait for new config files")
								if ii >298:
									startProgam("master.py", params="", reason="..not configured yet")
									exit(0)
								time.sleep(5)
								readNewParams()
							else:
								break
						U.stopAdhocWifi()
	except	Exception, e :
		U.logger.log(40, u"Line {} has error={}".format(traceback.extract_tb(sys.exc_info()[2])[-1][1], e))
	return 

####################      #########################
def	checkForAdhocWeb():
	global adhocWifiStarted, ipNumberForAdhoc
	try:
		if adhocWifiStarted > 10:
			if not U.checkIfwebserverINPUTrunning():
				U.startwebserverINPUT(80, useIP=ipNumberForAdhoc, force=True)
				# restore old interfaces for next reboot 
				for ii in range(150):
					if U.checkwebserverINPUT(): break
					if U.checkIfStopAdhocWiFi():break
					U.logger.log(20,u" in loop waiting for webserver input  ")
					time.sleep(5)
				U.logger.log(20,u"switching back to normal wifi setup")
				U.stopAdhocWifi()
				U.restartMyself(reason=u"starting back to normal from adhoc wifi")
	except	Exception, e :
		U.logger.log(40, u"Line {} has error={}".format(traceback.extract_tb(sys.exc_info()[2])[-1][1], e))
	return 

####################      #########################
def checkIfNetworkStarted2(indigoServerOn, changed, connected ):
	try:
		if G.networkType  in G.useNetwork and G.wifiType =="normal":
			for ii in range(100):
				if ii > 98:
					U.logger.log(30, "master no connection to indigo server at ip:>>{}<<  network type:{}".format(G.ipOfServer, G.networkType) )
					time.sleep(7)
					startProgam("master.py", params="", reason=".. failed to connect to indigo server")
					exit(0)
				if U.testPing(G.ipOfServer) >0:
					readNewParams()
					if time.time() - G.ipConnection > 600.: # after 10 minutes 
						if G.enableRebootCheck.find("rebootPing") >-1:
							U.sendURL(sendAlive="reboot")
							U.doReboot(tt=30., text=" reboot due to no  PING reply from MAC for 10 minutes ")				
					if time.time() - G.ipConnection > 100.: 
						if  G.wifiEth["wlan0"]["on"]  in ["onIf","off"] and G.wifiEth["eth0"]["on"] !="off":
							G.wifiEthOld = copy.copy(G.wifiEth)
							G.wifiEth["wlan0"]["on"] 	= "on"
							G.wifiEth["wlan0"]["useIP"] = "use"
							G.wifiEth["eth0"]["on"]     = "onIf"
							G.wifiEth["eth0"]["useIP"]  = "useIf"
							G.switchedToWifi = time.time()
							indigoServerOn, changed, connected = U.getIPNumberMaster()
				else: 
					U.logger.log(20, "can ping indigo server at ip:>>{}<<".format(G.ipOfServer))
					break
				time.sleep(10)
	except	Exception, e :
		U.logger.log(40, u"Line {} has error={}".format(traceback.extract_tb(sys.exc_info()[2])[-1][1], e))
	return indigoServerOn, changed, connected

####################      #########################
def checkNetworkLoop(restartCLock, indigoServerOn, changed, connected ):
	global ifNetworkChanges, startingnetworkStatus
	try:
		U.testNetwork(force = True)
		U.checkNTP()
		#print "startingnetworkStatus", startingnetworkStatus , G.networkStatus , G.networkType
		if	((G.networkStatus.find("Inet") > -1 ) and	# network up
			 (G.ntpStatus=="started, working"	) and	# NTP working
			 (G.useRTC !="" and G.useRTC != "0")  ):			# RTC installed ...	  ==>  set HW clock to NTP time stamp:
			subprocess.call("sudo /sbin/hwclock -w", shell=True)

		if (G.networkStatus).find("indigo") > -1 and (G.networkType).find("clock") ==-1:
			if U.testPing(G.ipOfServer)==2:				# if no ping gets return we assume we are not connected, this happens after powerfailure. the router comes aback after rpi and wifi has given up, need to restart
				if time.time() - G.ipConnection > 600.: # after 10 minutes 
					if G.enableRebootCheck.find("rebootPing") >-1:
						U.sendURL(sendAlive="reboot")
						U.doReboot(tt=30., text=" reboot due to no  PING reply from MAC for 10 minutes ")				

		if	G.networkType.find("clock") > -1:
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
				if G.networkType == "clockMANUAL"  and (time.time() - restartCLock)> 0  :
					xx = G.networkType
					G.networkType = "x"
					indigoServerOn, changed, connected = U.getIPNumberMaster()
					G.networkType = xx
					#print " networkStatus, ipOK : ",  G.networkStatus, ipOK

					if	ipOK >0 and G.networkStatus.find("Inet") ==-1 :
						U.logger.log(20, "setting to clockmanual, wifi off networkStatus:{}, ipOK:{}".format( G.networkStatus, ipOK) )
						U.setNetwork("off")
						G.networkType="clockMANUAL"
						cycleWifi()
						#print " setting to clockmanual "
						if    ifNetworkChanges == "restartMaster":
							U.restartMyself(reason="network went down ")
						elif  ifNetworkChanges == "reboot":
							U.doReboot(tt=5, text="network off")

				if ( startingnetworkStatus.find("Inet") == -1 and  G.networkStatus.find("Inet") >-1 ) :
					U.clearNetwork()
					xx = G.networkType
					G.networkType="x"
					ipOK, changed = U.getIPNumberMaster(quiet=False)
					G.networkType = xx
					U.logger.log(20, "network back on networkStatus:{}, ipOK:{}".format( G.networkStatus, ipOK) )
					if indigoServerOn == 0 and G.networkStatus.find("Inet") >-1:
						if    ifNetworkChanges == "restartMaster":
							U.restartMyself(reason="network back up")
						elif  ifNetworkChanges == "reboot":
							U.doReboot(tt=5, text="network came back")

	except	Exception, e :
		U.logger.log(40, u"Line {} has error={}".format(traceback.extract_tb(sys.exc_info()[2])[-1][1], e))
	return restartCLock, indigoServerOn, changed, connected 

####################      #########################
def killOldPrograms():
	global myPID
	try:
		U.stopDisplay()
		U.killOldPgm(myPID,"python", delList=G.programFiles+G.specialSensorList+["getBeaconParameters"]+["webserverINPUT","webserverSTATUS"]+[G.program], verbose=False)
		#U.killOldPgm(myPID,"python3 ", delList=G.programFiles+G.specialSensorList+["getBeaconParameters"]+["webserverINPUT","webserverSTATUS"]+[G.program]+["DHT3"], verbose=False)

		time.sleep(1)
		for ff in G.specialOutputList:
				U.killOldPgm(-1, ff+".py")
	except	Exception, e :
		U.logger.log(40, u"Line {} has error={}".format(traceback.extract_tb(sys.exc_info()[2])[-1][1], e))
	return 

####################      #########################
def checkInstallLibs():
	try:
		installLibs()
		time.sleep(0.5)
		for ii in range(200):
			if	os.path.isfile(G.homeDir+"installLibs.done"):
				break
			if ii%10==0:
				U.logger.log(30, " master still waiting for installibs to finish")
			time.sleep(5)
	except	Exception, e :
		U.logger.log(40, u"Line {} has error={}".format(traceback.extract_tb(sys.exc_info()[2])[-1][1], e))
	return 

####################      #########################
def checkFileSystem():
	try:
		if (unicode(subprocess.Popen("echo x > x" ,shell=True,stdout=subprocess.PIPE,stderr=subprocess.PIPE).communicate())).find("Read-only file system") > 0:
			U.doReboot(tt=10., text=" reboot due to bad SSD, 'file system is read only'")				   
			time.sleep(10)
			subprocess.call("sudo killall -9 python; reboot now", shell=True)
		subprocess.call("rm x", shell=True)

		subprocess.call("sudo chown -R  pi:pi	 "+G.homeDir, shell=True)
	except	Exception, e :
		U.logger.log(40, u"Line {} has error={}".format(traceback.extract_tb(sys.exc_info()[2])[-1][1], e))
	return 




####################      #########################
def checkIfipNumberchanged(indigoServerOn, changed, connected):
	try:
		oldIP = G.ipAddress
		indigoServerOn, changed, connected = U.getIPNumberMaster(quiet=True)

		if	G.ipAddress =="" and G.networkType.find("clock") == -1:
			U.doReboot(tt=10., text=" reboot due to no IP nummber")				   
			time.sleep(10)
			subprocess.call("reboot now", shell=True)

		if changed: 
			U.restartMyself(reason="changed ip number, eg wifi was switched off with eth0 present (loop) changed:{}".format(changed))

		if indigoServerOn == 0 and G.ipAddress !="":
			U.setNetwork("on")

		if oldIP != G.ipAddress:
			eth0IP, wifi0IP, G.eth0Enabled, G.wifiEnabled = U.getIPCONFIG()
			if eth0IP == "" or wifi0IP == "": # avoid restart none is active
				U.restartMyself(reason="changed ip number,.. eth0IP: {};  wifi0IP: {};  oldIP: {};  G.ipAddress:{};  G.eth0Active:{};  G.wifiActive:{}".format(eth0IP, wifi0IP, oldIP, G.ipAddress,G.eth0Active,G.wlanActive) )
	except	Exception, e :
		U.logger.log(40, u"Line {} has error={}".format(traceback.extract_tb(sys.exc_info()[2])[-1][1], e))
	return indigoServerOn, changed, connected


####################      #########################
def checkIpSTDprogramsAreRunning(lastCheckAlive):
	global sensors, enableiBeacons, activePGM, activePGMdict, BLEdirectSensorDeviceActive
	try:
		if "BLEconnect" in sensors or BLEdirectSensorDeviceActive or BLEdirectSwitchbotActive:
			startBLEconnect() 

		if time.time() - lastCheckAlive > 100:
			lastCheckAlive = time.time()
			for pp in ["setTEA5767","OUTPUTgpio","neopixelClock","display","neopixel","neopixelClock","spiMCP3008","simplei2csensors","sundial","setStepperMotor"]:
					U.logger.log(10, "checking if Active: {}".format(pp) ) 
					if pp in activePGM:
						if   pp =="display":
							checkIfDisplayIsRunning()
						elif pp =="neopixel":
							checkIfNeopixelIsRunning(pgm="neopixel")
						elif pp =="neopixelClock":
							checkIfNeopixelIsRunning(pgm="neopixelClock")
						elif pp =="sundial":
							checkIfPGMisRunning(pp+".py", checkAliveFile="sundial")
						else:
							checkIfPGMisRunning(pp+".py")
	

			for ss in G.specialSensorList:
				if	(ss in sensors or ss in activePGM ) and not (ss in activePGMdict): 
					checkIfPGMisRunning(ss+".py",checkAliveFile=ss)
					   
			for ss in activePGMdict:
				checkIfPGMisRunning(activePGMdict[ss][0],checkAliveFile=activePGMdict[ss][1])

		checkIfPGMisRunning("copyToTemp.py")

		if enableiBeacons != "0":
			checkIfbeaconLoopIsRunning()
	except	Exception, e :
		U.logger.log(40, u"Line {} has error={}".format(traceback.extract_tb(sys.exc_info()[2])[-1][1], e))

	return lastCheckAlive

####################      #########################
def checkNTP():
	try:
		U.installNTP()
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
				subprocess.call("sudo /sbin/hwclock -w", shell=True)
	except	Exception, e :
		U.logger.log(40, u"Line {} has error={}".format(traceback.extract_tb(sys.exc_info()[2])[-1][1], e))
	return 

####################      #########################
def setupTempDir():
	try:
		if	not os.path.isdir(G.homeDir+"temp"):
			subprocess.call("mkdir  "+G.homeDir+"temp", shell=True)
		if subprocess.Popen("df | grep tempfs ", shell=True,stdout=subprocess.PIPE,stderr=subprocess.PIPE).communicate()[0].find(G.homeDir+"temp") == -1:
			subprocess.call("mount -t tmpfs -o size=2m tmpfs "+G.homeDir+"temp", shell=True)
		subprocess.call("sudo rm "+G.homeDir+"temp/*", shell=True)
	except	Exception, e :
		U.logger.log(40, u"Line {} has error={}".format(traceback.extract_tb(sys.exc_info()[2])[-1][1], e))
	return 

####################      #########################
def checkFilesystem():
	try:
		# do a system boot sector check / repair
		subprocess.call("dosfsck -w -r -l -a -v -t /dev/mmcblk0p1 > "+G.homeDir+"temp/dosfsck & ", shell=True)


		# reset rights and ownership just in case
		subprocess.call("chmod a+r -R "+G.homeDir0+"*", shell=True)
		subprocess.call("chmod a+x "+G.homeDir0+"callbeacon.py", shell=True)
		subprocess.call("chown -R pi:pi "+G.homeDir0+"*", shell=True)

		subprocess.call("sudo  chown -R pi:pi /var/log/*", shell=True)

		#subprocess.call("sudo chown -R  pi:pi	 /run/user/1000/pibeacon", shell=True)
		subprocess.call("sudo chmod a+x  /lib/udev/hwclock-set", shell=True)
	except	Exception, e :
		U.logger.log(40, u"Line {} has error={}".format(traceback.extract_tb(sys.exc_info()[2])[-1][1], e))
	return 



####################      #########################
def checkIfWOLsendToIndigoServer():
	global macIfWOLsendToIndigoServer, IpnumberIfWOLsendToIndigoServer, lastCheckWOL

	try:
		if macIfWOLsendToIndigoServer == "": 			 return 
		if not U.isValidMAC(macIfWOLsendToIndigoServer): return 
		if time.time() - lastCheckWOL < 100: 			 return 

		
		if U.isValidIP(IpnumberIfWOLsendToIndigoServer): 
			ipPing = IpnumberIfWOLsendToIndigoServer
		else: 
			ipPing = G.ipOfServer

		if U.testPing(ipPing) == 0: 
			#U.logger.log(20, u"checking ping to {} ok, no wol action", format(ipPing))
			
			lastCheckWOL = time.time()
			return 
	
		U.logger.log(20, u"SENDING wakeonlan to MAC#:{}".format(macIfWOLsendToIndigoServer))
		subprocess.call("wakeonlan  "+macIfWOLsendToIndigoServer+" &", shell=True)
		lastCheckWOL = time.time()

	except	Exception, e :
		U.logger.log(40, u"Line {} has error={}".format(traceback.extract_tb(sys.exc_info()[2])[-1][1], e))
	return 

def getadhocIpNumber():
	adhocIP = "192.168.1.10"
	try:
		if	os.path.isfile(G.homeDir+"interfaces-adhoc"):
			f=open(G.homeDir+"interfaces-adhoc") 
			lines = f.read()
			f.close()
			ip = lines.split(" address ")[1]
			adhocIP = ip.split("\n")[0].strip()
	except	Exception, e :
		U.logger.log(40, u"Line {} has error={}".format(traceback.extract_tb(sys.exc_info()[2])[-1][1], e))
	return adhocIP

####################      #########################
def checkstartOtherProgram():
	try:
		global startOtherProgram, startOtherProgramOld, startOtherProgramKeepRunning, startOtherProgramStarted
		#U.logger.log(20, u"startOtherProgram:{}<, startOtherProgramOld:{}<, startOtherProgramKeepRunning:{}, startOtherProgramStarted:{},".format(startOtherProgram, startOtherProgramOld, startOtherProgramKeepRunning, startOtherProgramStarted))
		if startOtherProgramOld != startOtherProgram:
			if startOtherProgramOld != "":
				killPGM = startOtherProgramOld.strip()
				if ">" in killPGM: killPGM = killPGM.split(">")[0]
				U.logger.log(20, u"killing :{}, new pgm:{}".format(killPGM, startOtherProgram))
				U.killOldPgm(-1, killPGM)
			U.logger.log(20, u"startOtherProgram:{}< setting start time to -1, old != new".format(startOtherProgram))
			startOtherProgramStarted = -1
		else:
			if startOtherProgramStarted > 0 and not startOtherProgramKeepRunning: 
				return 
		
		startOtherProgramOld = startOtherProgram

		if len(startOtherProgram) < 2: 		
			startOtherProgramStarted = -1
			return 

		if startOtherProgramStarted > 0 and not startOtherProgramKeepRunning: 
			return

		checkPGM = startOtherProgram.strip()
		if ">" in checkPGM: checkPGM = checkPGM.split(">")[0]

		if U.pgmStillRunning(checkPGM): 		
			if startOtherProgramStarted < 0:  startOtherProgramStarted = time.time()
		else:
			U.logger.log(20, u"starting: '{}'".format(startOtherProgram))
			subprocess.call(startOtherProgram, shell=True)
			startOtherProgramStarted = time.time()

		return 

	except	Exception, e :
		U.logger.log(40, u"Line {} has error={}".format(traceback.extract_tb(sys.exc_info()[2])[-1][1], e))
	return 


####################      #########################
#################### main #########################
####################      #########################

### artificial indent to indicate main program 
def execMaster():
	try:
		global myPID,restart,sensorList,rPiCommandPORT,firstRead
		global rebootWatchDogTime, lastrebootWatchDogTime
		global sensorEnabled,  restart, enableiBeacons, beforeLoop,iPhoneMACList,rebootHour,rebooted
		global lastAliveultrasoundDistance, sensorAlive,useRamDiskForLogfiles,lastAlive

		global shutdownInputPin, shutdownPinVoltSensor, shutDownPinVetoOutput, lastshutdownInputPinTime
		global actions, output, sensors, sensorList
		global activePGMdict, bluetoothONoff
		global oldRaw,	lastRead
		global batteryMinPinActiveTimeForShutdown, inputPinVoltRawLastONTime
		global batteryChargeTimeForMaxCapacity, batteryCapacitySeconds
		global GPIOTypeAfterBoot1, GPIOTypeAfterBoot2, GPIONumberAfterBoot1, GPIONumberAfterBoot2
		global activePGM
		global configured
		global startWebServerSTATUS, startWebServerINPUT
		global fanGPIOPin, fanTempOnAtTempValue, fanTempOffAtTempValue, lastTempValue, fanWasOn,  lastTimeTempValueChecked, fanTempName, fanTempDevId, fanEnable
		global wifiEthCheck, BeaconUseHCINoOld,BLEconnectUseHCINoOld
		global batteryUPSshutdownAtxPercent, shutdownSignalFromUPSPin, shutdownSignalFromUPS_SerialInput, shutdownSignalFromUPS_InitTime, batteryUPSshutdown_Vin
		global sundial
		global masterVersion
		global ifNetworkChanges
		global typeForPWM, maxSizeOfLogfileOnRPI
		global xWindows, startXonPi
		global clearHostsFile
		global python3
		global startingnetworkStatus
		global fanOnTimePercent, fanOntimeData, fanOntimePeriod
		global BLEdirectSensorDeviceActive
		global BLEdirectSwitchbotActive
		global startOtherProgram, startOtherProgramOld, startOtherProgramKeepRunning, startOtherProgramStarted
		global macIfWOLsendToIndigoServer, lastCheckWOL, IpnumberIfWOLsendToIndigoServer
		global batteryUPSshutdownALCHEMYupcI2C, batteryUPSshutdownEnable
		global checkIfShutDownVoltageLastCheck
		global typeOfUPS
		global adhocWifiStarted
		global ipNumberForAdhoc
		global RTCpresent

		RTCpresent						= False
		ipNumberForAdhoc				= "192.168.1.10"
		adhocWifiStarted				= -1
		typeOfUPS						= ""
		checkIfShutDownVoltageLastCheck	= 0
		batteryUPSshutdownALCHEMYupcI2C = ""
		batteryUPSshutdownEnable		= ""

		IpnumberIfWOLsendToIndigoServer = ""
		lastCheckWOL					= 0
		macIfWOLsendToIndigoServer 		= ""
		startOtherProgram				= ""
		startOtherProgramOld			= ""
		startOtherProgramKeepRunning 	= False
		startOtherProgramStarted 		= -1
		BLEdirectSensorDeviceActive 	= False
		BLEdirectSwitchbotActive				= False
		fanOntimePeriod					= 180 #  ==3 minutes for building average fan on 
		fanOntimeData					= []
		fanOnTimePercent				= ""
		python3							= {}
		clearHostsFile					= False
		xWindows						= ""
		startXonPi						= "leaveAlone"
		maxSizeOfLogfileOnRPI			= 10000000
		typeForPWM						= "GPIO"
		ifNetworkChanges  				= "doNothing"
		sundial							= ""
		checkFSCHECKfileDone			= False
		wifiEthCheck					= {}
		BeaconUseHCINoOld				= ""
		BLEconnectUseHCINoOld			= ""
		fanEnable						= "-"
		fanTempName						= ""
		fanTempDevId					= ""
		lastTempValue					= -1
		fanWasOn						= 0
		lastTimeTempValueChecked		= -1
		fanGPIOPin						= -1
		fanTempOnAtTempValue			= -1
		fanTempOffAtTempValue			= 99

		activePGM						= {}
		GPIOTypeAfterBoot1				= "off"
		GPIOTypeAfterBoot2				= "off"
		GPIONumberAfterBoot1			= "-1"
		GPIONumberAfterBoot2			= "-1"
		alreadyBooted					= False


		startWebServerSTATUS			= 80
		startWebServerINPUT				= 8010
		batteryChargeTimeForMaxCapacity = 3600. # seconds
		batteryCapacitySeconds			= 5*3600 # 

		batteryMinPinActiveTimeForShutdown = 9999999999999
		inputPinVoltRawLastONTime 		= time.time()
		oldRaw							= ""
		lastRead						= 0
		bluetoothONoff					= "on"
		rebootHour						= -1  # defualt : do  not reboot
		rebooted						= True
		useRamDiskForLogfiles			= "0"
		enableiBeacons					= "1"
		beforeLoop						= True
		myPID							= str(os.getpid())
		restart							= ""
		sensorEnabled					= []
		sensorList						= []
		sensors							= {}
		enableSensor					= "0"
		rPiCommandPORT					= 0
		ipConnection					= time.time() +100
		G.lastAliveSend2				= time.time()
		lastAlive						= []
		lastAliveultrasoundDistance 	= 0
		loopCount						= 0
		iPhoneMACListOLD				= ""
		shutdownInputPin				= -1
		shutDownPinVetoOutput			= -1
		shutdownPinVoltSensor			= -1
		lastshutdownInputPinTime		= 0
		shutdownSignalFromUPSPin		= -1
		batteryUPSshutdownAtxPercent	= -1
		shutdownSignalFromUPS_SerialInput =""
		shutdownSignalFromUPS_InitTime	= -1
		batteryUPSshutdown_Vin			= "notSet"

		rebootWatchDogTime				= -1
		sensorAlive						= {}
		actions							= []
		firstRead						= True
		activePGMdict					= {}
		configured						= ""
		adhocWifiStarted				= -1

		GPIO.setwarnings(False)
		GPIO.setmode(GPIO.BCM)
		

		subprocess.Popen("/usr/bin/python "+G.homeDir+"doOnce.py" ,shell=True)
		time.sleep(0.5)
		U.setLogging()


		ret = subprocess.Popen("/bin/cat /etc/os-release " ,shell=True,stdout=subprocess.PIPE,stderr=subprocess.PIPE).communicate()[0].strip("\n").strip().split("\n")

		# make dir for short temp files
		setupTempDir()

		G.tStart = time.time()

		U.resetRebootingNow()

		G.last_masterStart = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")


		# just in case the file is present, is created by calling master w nohup. it is terminal output, can be Gbytes
		subprocess.Popen("sudo rm {}nohup.out > /dev/null 2>&1".format(G.homeDir),shell=True)

		killOldPrograms()

		subprocess.call("/usr/bin/python "+G.homeDir+"copyToTemp.py", shell=True)
		subprocess.call("nohup sudo /bin/bash "+G.homeDir+"master.sh > /dev/null 2>&1 ", shell=True)
		time.sleep(1)

		checkIfclearHostsFile()

		readNewParams(force=2)
		U.logger.log(20, "" )
		U.logger.log(20, "=========START.. MASTER  v:{}".format(masterVersion) )

		checkWiFiSetupBootDir()

		checkLogfiles()

		checkPythonLibs()

		U.logger.log(20, "=========START2.. indigoServer @ IP:{}<< G.wifiType:>>{}<<".format(G.ipOfServer, G.wifiType) )

		checkIfUARThciChannelIsOnRPI4()

		time.sleep(1)
		
		subprocess.Popen("sudo hwclock -r",shell=True,stdout=subprocess.PIPE,stderr=subprocess.PIPE)


		ipNumberForAdhoc = getadhocIpNumber()
		# sets: G.wifiType = normal/ adhoc
		U.whichWifi() 

		adhocWifiStarted = U.checkWhenAdhocWifistarted()
		U.prepNextNormalRestartFromAdhocWifi()
		U.clearAdhocWifi()


		if adhocWifiStarted > 10: U.logger.log(20, "adhocWifi active, {} sec left bf restart".format(600 - (time.time() - adhocWifiStarted)) )
		U.logger.log(20, "=========START3.. indigoServer @ IP:{}<< G.wifiType:{}<<, adhocWifiStarted:{}<<, G.networkType:{}<<".format(G.ipOfServer, G.wifiType, adhocWifiStarted, G.networkType) )
		

		subprocess.call("cp  "+G.homeDir+"callbeacon.py  "+G.homeDir0+"callbeacon.py", shell=True)

		U.clearNetwork()

		indigoServerOn, changed, connected = checknetwork0()
	
		readNewParams(force = 1)

		if G.wifiType =="normal" and G.networkType.find("clock") == -1 and rPiCommandPORT >0:
			startProgam("receiveCommands.py", params=str(rPiCommandPORT), reason=" normal start of receiveCommands")


		checkIfFirstStart()
		U.logger.log(20, "=========START4.. indigoServer @ IP:{}<< G.wifiType:{}<<, adhocWifiStarted:{}<<, G.networkType:{}<<".format(G.ipOfServer, G.wifiType, adhocWifiStarted, G.networkType) )

		if startWebServerSTATUS > 0 and  adhocWifiStarted < 10:
			U.startwebserverSTATUS(startWebServerSTATUS)

		U.logger.log(20, "=========START5.. indigoServer @ IP:{}<< G.wifiType:{}<<, adhocWifiStarted:{}<<, G.networkType:{}<<".format(G.ipOfServer, G.wifiType, adhocWifiStarted, G.networkType) )

		checkForAdhocWeb()
		if os.path.isfile(G.homeDir+"temp/rebootNeeded"): 	os.remove(G.homeDir+"temp/rebootNeeded")
		if os.path.isfile(G.homeDir+"temp/restartNeeded"):	os.remove(G.homeDir+"temp/restartNeeded")
		GPIO.setwarnings(False)

		checkRamDisk()

		lastrebootWatchDogTime = time.time() - rebootWatchDogTime*60. +30.
		subprocess.call("shutdown - c >/dev/null 2>&1", shell=True)
		## stop any pending shutdowns


		# check if all libs for sensors etc are installed
		checkInstallLibs()

		U.logger.log(20, "=========START6.. indigoServer @ IP:{}<< G.wifiType:{}<<, adhocWifiStarted:{}<<, G.networkType:{}<<".format(G.ipOfServer, G.wifiType, adhocWifiStarted, G.networkType) )

		#(re)start beaonloop for bluez / iBeacons
		if enableiBeacons == "1": 
			startProgam("beaconloop.py", params="", reason=" at startup ")
			checkIfAliveFileOK("beaconloop",force="set")

		time.sleep(2)
		startBLEconnect()

		indigoServerOn, changed, connected  = checkIfNetworkStarted2(indigoServerOn, changed, connected )

		U.logger.log(20, "=========START7.. indigoServer @ IP:{}<< G.wifiType:{}<<, adhocWifiStarted:{}<<, G.networkType:{}<<, indigoServerOn:{}<<, changed:{}<<, connected:{}<< ".format(G.ipOfServer, G.wifiType, adhocWifiStarted, G.networkType, indigoServerOn, changed, connected ) )
		# make directory for sound files
		if not os.path.isdir(G.homeDir+"soundfiles"):
			subprocess.call("mkdir "+G.homeDir+"soundfiles &", shell=True)


		if checkDiskSpace() == 1:
			U.logger.log(30, "please expand hard disk, not enough disk space left either do sudo raspi-config and expand HD	 or replace ssd with larger ssd ")
			time.sleep(50)
			exit()

		if os.path.isfile(G.homeDir+"temp/rebootNeeded"): 	os.remove(G.homeDir+"temp/rebootNeeded")
		if os.path.isfile(G.homeDir+"temp/restartNeeded"):	os.remove(G.homeDir+"temp/restartNeeded")


		beforeLoop			 = False
		# main loop every 30 seconds

		checkFilesystem()

		checkIfGpioIsInstalled()

		checkstartOtherProgram()
		U.logger.log(20, "=========START8.. adhocWifiStarted:{}<< G.ipAddress:{}<<, RTCpresent:{}<<, networkType:{}<<".format(adhocWifiStarted, G.ipAddress, RTCpresent, G.networkType) )

		#startProgam("actions.py", params="", reason=" at startup ")
		#checkIfAliveFileOK("actions",force="set")

		G.tStart	  = time.time()

		U.sendSensorAndRPiInfoToPlugin(sensors)	
		tAtLoopSTart =time.time()

		U.testNetwork()
		if G.networkType.find("clock") == -1:
			checkNTP()

		startingnetworkStatus = G.networkStatus
		restartCLock		  = time.time() +  999999999.

		if G.networkType.find("clock") == -1:
			indigoServerOn, changed, connected = U.getIPNumberMaster(noRestart=True)
			if indigoServerOn  and G.ipAddress !="":
				U.setNetwork("on")
			if changed: 
				U.restartMyself(reason="changed ip number, eg wifi was switched off with eth0 present (1) changed:{}".format(changed))
		else:
			if G.ipAddress == "":
				time.sleep(10)
			changed = False
	

		U.logger.log(20, "=========START9.. adhocWifiStarted:{}<< G.ipAddress:{}<<, RTCpresent:{}<<, networkType:{}<<".format(adhocWifiStarted, G.ipAddress, RTCpresent, G.networkType) )
		if adhocWifiStarted < 10 and G.ipAddress == "" and RTCpresent:
			U.manualStartOfRTC()


		subprocess.call("rm  {}temp/sending > /dev/null 2>&1 ".format(G.homeDir), shell=True)


		U.logger.log(20,"=========START10 loop")

		checkTempForFanOnOff(force = True)
		lastCheckAlive = time.time() -90

		# start voltage checker 

		while True:
			if loopCount > 1000000000: loopCount = 0
			loopCount += 1

			if abs(tAtLoopSTart	 - time.time()) > 30:
				if G.networkType.find("indigo") >-1 and G.wifiType == "normal":
					U.restartMyself(reason="new time set, delta="+unicode(tAtLoopSTart	- time.time()))
		
			if shutdownSignalFromUPS_InitTime > 0 and time.time() - shutdownSignalFromUPS_InitTime >100: #   2 minutes after start
				startUPSShutdownPinAfterStart()
			

			tAtLoopSTart =time.time()
		
			if loopCount == 3: 
				checkFSCHECKfile()

			try:	
				readNewParams()
				if loopCount%2 == 0: 
					checkstartOtherProgram()
					checkIfWOLsendToIndigoServer()
			
				if loopCount%5 == 0: 
					checkRamDisk(loopCount=loopCount)
				
				if loopCount%60 == 0: # every 10 minutes
					checkFileSystem()

				#check if IP number has changed, or if we should switch off wlan0 if eth0 is present 
				if loopCount%24 == 0: # every 2 minutes
					if G.networkType.find("clock") == -1:
						checkIfipNumberchanged(indigoServerOn, changed, connected)

		##########   check if pgms are running

				if str(rPiCommandPORT) !="0"  and G.wifiType =="normal" and G.networkType.find("clock") == -1 and (G.networkStatus).find("indigo") >-1: 
					checkIfPGMisRunning("receiveCommands.py", checkAliveFile="", parameters=str(rPiCommandPORT))


				lastCheckAlive = checkIpSTDprogramsAreRunning(lastCheckAlive)

				checkIfRebootRequest()
		
				if rebootHour >-1:
					checkIfNightReboot()
					if datetime.datetime.now().hour > rebootHour: rebooted = False

				checkSystemLOG()


		######### start / stop  wifi  &  web servers 
				if adhocWifiStarted > 10 and (time.time() - adhocWifiStarted) > 20 :
					if time.time() - adhocWifiStarted > 600:
						U.stopAdhocWifi()
				else:
					adhocWifiStarted = U.checkWhenAdhocWifistarted()

				if U.checkIfStartAdhocWiFi():
					if adhocWifiStarted  < 20 :
						U.startAdhocWifi()
						time.sleep(20)
					

				if U.checkIfStopAdhocWiFi():
					if adhocWifiStarted > 10 and (time.time() - adhocWifiStarted) > 20 :
						U.stopAdhocWifi()
						time.sleep(20) # symbolic, will reboot before

				if (startWebServerSTATUS >0 or U.checkIfStartwebserverSTATUS()) and adhocWifiStarted < 10:
					if not U.checkIfwebserverSTATUSrunning():
							U.startwebserverSTATUS(startWebServerSTATUS)

				if (startWebServerINPUT > 0 or U.checkIfStartwebserverINPUT()) and adhocWifiStarted < 10:
					if not U.checkIfwebserverINPUTrunning():
						U.startwebserverINPUT(startWebServerINPUT)

				if startWebServerSTATUS > 0 and  U.checkIfStopwebserverSTATUS():
					if U.checkIfwebserverSTATUSrunning():
						U.stopwebserverSTATUS()

				if startWebServerINPUT > 0 and  U.checkIfStopwebserverINPUT():
					if U.checkIfwebserverINPUTrunning():
						U.stopwebserverINPUT()


				if fanGPIOPin > 0:
					checkTempForFanOnOff()

				U.checkIfAliveNeedsToBeSend()
		
				if loopCount%5 == 0: 
					U.checkrclocalFile()

				if loopCount%8 == 0: 
					U.sendSensorAndRPiInfoToPlugin(sensors, fanOnTimePercent=fanOnTimePercent)		   
					if adhocWifiStarted < 10: 
						if G.networkType.find("clock") == -1:
							tryRestartNetwork()
		
				if loopCount %4 == 0: # check network every 40 secs
					checkNetworkLoop(restartCLock, indigoServerOn, changed, connected )

				if loopCount %5 == 0: # check logfiles every 5*20=100 seconds 
					checkLogfiles()

					#check if fallback "master.sh"  is running, if not restart 
					if not U.pgmStillRunning("master.sh"):
						subprocess.call("nohup sudo /bin/bash "+G.homeDir+"master.sh > /dev/null 2>&1 ", shell=True)
					## check if we have network back
				
				delayAndWatchDog()

			except	Exception, e :
				U.logger.log(40, u"Line {} has error={}".format(traceback.extract_tb(sys.exc_info()[2])[-1][1], e))
	except	Exception, e :
		U.logger.log(40, u"Line {} has error={}".format(traceback.extract_tb(sys.exc_info()[2])[-1][1], e))


execMaster()
try: 	G.sendThread["run"] = False; time.sleep(1)
except: pass
U.logger.log(30, u"exit at end of master")	
time.sleep(10)
sys.exit(0)		   

