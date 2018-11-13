#! /usr/bin/env python
# -*- coding: utf-8 -*-
####################
# pibeacon Plugin
# Developed by Karl Wachs
# karlwachs@me.com

import os
import sys
import re
import subprocess
import pwd
import datetime
import time
import json
import copy
import math
import socket
import threading
import SocketServer
import traceback
import Queue
import resource
import versionCheck.versionCheck as VS
import myLogPgms.myLogPgms 
import cProfile
import pstats

dataVersion = 32.50




## Static parameters, not changed in pgm
_GlobalConst_numberOfiBeaconRPI	 = 10
_GlobalConst_numberOfRPI		 = 20
_GlobalConst_emptyBeacon = {u"indigoId": 0, u"ignore": 0, u"status": u"up", u"lastUp": 0, u"note": u"beacon", u"expirationTime": 90,
			   u"created": 0, u"updateFING": 0, u"updateWindow": 0, u"updateSignalValuesSeconds": 0, u"signalDelta": 999, u"minSignalCutoff": -999,
			   u"PosX": 0., u"PosY": 0., u"PosZ": 0., u"typeOfBeacon": u"other", u"beaconTxPower": +999, u"fastDown": u"0",
			   u"batteryLevel": u"",
			   u"fastDownMinSignal":-999,
			   u"showBeaconOnMap": u"0","showBeaconNickName": u"",u"showBeaconSymbolAlpha": u"0.5",u"showBeaconSymboluseErrorSize": u"1",u"showBeaconSymbolColor": u"b",
			   u"receivedSignals":[[-999,0],[-999,0],[-999,0],[-999,0],[-999,0],[-999,0],[-999,0],[-999,0],[-999,0],[-999,0]]}
_GlobalConst_typeOfBeacons = {u"xy":		u"07775dd0111b11e491910800200c9a66",
				 u"tile":	   u"01",
				 u"sanwo":	   u"fda50693a4e24fb1afcfc6eb07647825",
				 u"radius":	   u"2f234454cf6d4a0fadf2f4911ba9ffa6",
				 u"rPI":	   u"2f234454cf6d4a0fadf2f4911ba9ffa6-9",
				 u"pebbleBee": u"1804180f1803190002020a0808ff0e0a",
				 u"JINOU":	   u"e2c56db5dffb48d2b060d0f5a71096e0",
				 u"Jaalee":	   u"ebefd08370a247c89837e7b5634df524",
				 u"other":	u"",
				 u"Other1": u"",
				 u"Other2": u"",
				 u"highTx": u"",
				 }
_GlobalConst_emptyBeaconProps = {u"note": u"beacon",
					u"expirationTime": 90,
					u"created": 0,
					u"updateSignalValuesSeconds": 0,
					u"signalDelta": 999,
					u"minSignalCutoff": -999,
					u"typeOfBeacon": u"other",
					u"beaconTxPower": 999,
					u"memberOfFamily": 0,
					u"memberOfGuests": 0,
					u"memberOfOther1": 0,
					u"memberOfOther2": 0,
					u"ignore": 0,
					u"enableBroadCastEvents": "0",
					u"fastDownMinSignal": -999,
					u"showBeaconOnMap": u"0",u"showBeaconNickName": u"",u"showBeaconSymbolType": u",",u"showBeaconSymbolAlpha": u"0.5",u"showBeaconSymboluseErrorSize": u"1",u"showBeaconSymbolColor": u"b",
					u"fastDown": u"0"}

_GlobalConst_emptyrPiProps	  ={	 u"typeOfBeacon":			  u"rPI",
						u"updateSignalValuesSeconds": 300,
						u"beaconTxPower":			  999,
						u"SupportsBatteryLevel":	  False,
						u"sendToIndigoSecs":		  90,
						u"sensorRefreshSecs":		  90,
						u"deltaChangedSensor":		  5,
						u"PosXYZ":					 u"0.,0.,0.",
						u"BLEserial":				 u"sequential",
						u"shutDownPinInput" :		 u"-1",
						u"signalDelta" :			 u"999",
						u"minSignalCutoff" :		 u"-999",
						u"expirationTime" :			 u"90",
						u"fastDown" :				 u"0",
						u"enableBroadCastEvents":	 "0",
						u"rssiOffset" :				 0,
						u"shutDownPinOutput" :		 u"-1" }

_GlobalConst_fillMinMaxStates = ["Temperature","AmbientTemperature","Pressure","Humidity","AirQuality","visible","ambient","white","illuminance","IR","CO2","VOC","INPUT_0","rainRate"]

_GlobalConst_emptyRPI =	  {
	u"rpiType": u"rPi",
	u"enableRebootCheck": u"restartLoop",
	u"enableiBeacons": u"1",
	u"input": {},
	u"ipNumberPi": u"",
	u"ipNumberPiSendTo": u"",
	u"output": {},
	u"passwordPi": u"raspberry",
	u"piDevId": 0,
	u"piMAC": u"",
	u"piNumberReceived": u"",
	u"piOnOff": u"0",
	u"authKeyOrPassword": u"assword",
	u"piUpToDate": [],
	u"sensorList": u"0,",
	u"lastMessage":0,
	u"sendToIndigoSecs":		 90,
	u"sensorRefreshSecs":		  20,
	u"deltaChangedSensor":		  5,
	u"rssiOffset" :		   0,
	u"emptyMessages":			 0,
	u"deltaTime1": 100,
	u"deltaTime2": 100,
	u"userIdPi": u"pi"}


_GlobalConst_emptyRPISENSOR =	{
	u"rpiType": u"rPiSensor",
	u"enableRebootCheck": u"restartLoop",
	u"enableiBeacons": u"0",
	u"input": {},
	u"ipNumberPi": u"",
	u"ipNumberPiSendTo": u"",
	u"lastUpPi": 0,
	u"output": {},
	u"passwordPi": u"raspberry",
	u"authKeyOrPassword": u"assword",
	u"piDevId": 0,
	u"piMAC": u"",
	u"piNumberReceived": u"",
	u"piOnOff": u"0",
	u"piUpToDate": [],
	u"sensorList": u"0,",
	u"lastMessage":0,
	u"sendToIndigoSecs":		 90,
	u"sensorRefreshSecs":		  20,
	u"deltaChangedSensor":		  5,
	u"userIdPi": u"pi"}

_GlobalConst_allGPIOlist = [
	  [u"-1", u"do not use"]
	, [u"2",  u"GPIO02 = pin  # 3 -- I2C"]
	, [u"3",  u"GPIO03 = pin  # 5 -- I2C"]
	, [u"4",  u"GPIO04 = pin  # 7 -- ONE WIRE"]
	, [u"17", u"GPIO17 = pin  # 11 -- DHT"]
	, [u"27", u"GPIO27 = pin  # 13"]
	, [u"22", u"GPIO22 = pin  # 15"]
	, [u"10", u"GPIO10 = pin  # 19 -- SPS"]
	, [u"9",  u"GPIO09 = pin  # 21 -- SPS"]
	, [u"11", u"GPIO11 = pin  # 23 -- SPS"]
	, [u"5",  u"GPIO05 = pin  # 29"]
	, [u"6",  u"GPIO06 = pin  # 31"]
	, [u"13", u"GPIO13 = pin  # 33"]
	, [u"19", u"GPIO19 = pin  # 35"]
	, [u"26", u"GPIO26 = pin  # 37"]
	, [u"14", u"GPIO14 = pin  # 8  -- TX - REBOOT PIN OUT"]
	, [u"15", u"GPIO15 = pin  # 10 -- RX - REBOOT PIN IN"]
	, [u"18", u"GPIO18 = pin  # 12"]
	, [u"23", u"GPIO23 = pin  # 16"]
	, [u"24", u"GPIO24 = pin  # 18"]
	, [u"25", u"GPIO25 = pin  # 22"]
	, [u"8",  u"GPIO08 = pin  # 24 -- SPS"]
	, [u"7",  u"GPIO07 = pin  # 26 -- SPS"]
	, [u"12", u"GPIO12 = pin  # 32"]
	, [u"16", u"GPIO16 = pin  # 36"]
	, [u"20", u"GPIO20 = pin  # 38"]
	, [u"21", u"GPIO21 = pin  # 40"]]

_GlobalConst_ICONLIST	= [	  [u"None", u"None"],
				 [u"None", u"Error"],
				 [u"PowerOff", u"PowerOn"],
				 [u"DimmerOff", u"DimmerOn"],
				 [u"FanOff", u"FanOn"],
				 [u"SprinklerOff", u"SprinklerOn"],
				 [u"SensorOff", u"SensorOn"],
				 [u"SensorOn", u"SensorTripped"],
				 [u"SensorOff", u"SensorTripped"],
				 [u"EnergyMeterOff", u"EnergyMeterOn"],
				 [u"LightSensor", u"LightSensorOn"],
				 [u"MotionSensor", u"MotionSensorTripped"],
				 [u"DoorSensorClosed", u"DoorSensorOpened"],
				 [u"WindowSensorClosed", u"WindowSensorOpened"],
				 [u"TemperatureSensor", u"TemperatureSensorOn"],
				 [u"HumiditySensor", u"HumiditySensorOn"],
				 [u"HumidifierOff", u"HumidifierOn"],
				 [u"DehumidifierOff", u"DehumidifierOn"],
				 [u"TimerOff", u"TimerOn"]]


_GlobalConst_beaconPlotSymbols		= [u"text", u"dot", u"smallCircle", u"largeCircle", u"square"] # label/text only, dot, small circle, circle prop to dist to rpi, square (for RPI)



_GlobalConst_allowedCommands	   = [u"up", u"down", u"pulseUp", u"pulseDown", u"continuousUpDown", u"analogWrite", u"disable", u"newMessage", u"resetDevice", u"startCalibration", u"rampUp", u"rampDown", u"rampUpDown"]	 # commands support for GPIO pins
_GlobalConst_allowedSensors		   = [u"ultrasoundDistance", u"vl503l0xDistance", u"vl6180xDistance", u"vcnl4010Distance", # dist / light
						 u"apds9960",															  # dist gesture
						 u"i2cTCS34725", u"i2cTSL2561", u"i2cVEML6070", u"i2cVEML6030", u"i2cVEML6040", u"i2cVEML7700",		# light 
						 u"i2cVEML6075", u"i2cIS1145", u"i2cOPT3001",									# light	  
						 u"BLEsensor",
						 u"Wire18B20", u"i2cTMP102", u"i2cMCP9808", u"i2cLM35A",						 # temp 
						 u"DHTxx", u"DHT11", u"i2cAM2320", u"i2cSHT21","si7021",						 # temp / hum
						 u"i2cBMPxx", u"i2cT5403", u"i2cBMP280","i2cMS5803",						 # temp / press
						 u"i2cBMExx",															 # temp / press/ hum /
						 u"bme680",																   # temp / press/ hum / gas
						 u"tmp006",																   # temp rmote infrared
						 u"pmairquality",
						 u"amg88xx",																# infrared camera
						 u"ccs811",																   # co2 voc 
						 u"mhz-I2C",																# co2 temp 
						 u"mhz-SERIAL",
						 u"rainSensorRG11",
						 u"launchpgm",
						 u"sgp30",																  # co2 voc 
						 u"as3935",																	# lightning sensor 
						 u"i2cMLX90614", u"mlx90614",												   # remote	 temp &ambient temp 
						 u"ina219",																	 # current and V 
						 u"ina3221",																  # current and V 3 channels
						 u"as726x",																	 # rgb yellow orange violot
						 u"l3g4200", u"bno055", u"mag3110", u"mpu6050", u"hmc5883L", u"mpu9255", u"lsm303",	   # gyroscope
						 u"INPgpio", u"INPUTgpio-1", u"INPUTgpio-4", u"INPUTgpio-8", u"INPUTgpio-26",		# gpio inputs
						 u"INPUTtouch-1", u"INPUTtouch-4", u"INPUTtouch-8", u"INPUTtouch-12", u"INPUTtouch-16",		 # capacitor inputs
						 u"INPUTtouch12-1", u"INPUTtouch12-4", u"INPUTtouch12-8", u"INPUTtouch12-12",	   # capacitor inputs
						 u"INPUTtouch16-1", u"INPUTtouch16-4", u"INPUTtouch16-8", u"INPUTtouch16-16",	   # capacitor inputs
						 u"i2cADS1x15", u"i2cADS1x15-1", u"spiMCP3008", u"spiMCP3008-1","i2cADC121",
						 u"i2cPCF8591", u"i2cPCF8591-1",											   # adc
						 u"INPUTpulse",
						 u"mysensors", u"myprogram",
						 u"BLEconnect"]
i2cSensors				 = ["si7021","bme680","amg88xx","ccs811",u"sgp30", u"mlx90614",	 "ina219","ina3221","as726x","as3935",u"l3g4200", u"bno055", u"mag3110", u"mpu6050", u"hmc5883L", u"mpu9255", u"lsm303", u"vl6180xDistance", u"vcnl4010Distance",u"apds9960"]

_GlobalConst_allowedOUTPUT		   = [u"neopixel", u"neopixel-dimmer", u"neopixelClock", u"OUTPUTgpio-1-ONoff", u"OUTPUTgpio-1", u"OUTPUTgpio-4", u"OUTPUTgpio-10", u"OUTPUTgpio-26", u"setMCP4725", u"display", u"setPCF8591dac", u"setTEA5767"]
_GlobalConst_allowedpiSends		   = [u"updateParamsFTP", u"updateAllFilesFTP", u"rebootSSH", u"resetOutputSSH", u"shutdownSSH", u"getStatsSSH", u"initSSH", u"upgradeOpSysSSH"]


_GlobalConst_groupList			   = [u"Family", u"Guests", u"Other1", u"Other2"]

_defaultDateStampFormat			   = u"%Y-%m-%d %H:%M:%S"

################################################################################
# 
class Plugin(indigo.PluginBase):
####-------------------------------------------------------------------------####
	def __init__(self, pluginId, pluginDisplayName, pluginVersion, pluginPrefs):
		indigo.PluginBase.__init__(self, pluginId, pluginDisplayName, pluginVersion, pluginPrefs)

		self.pathToPlugin = os.getcwd() + "/"
		## = /Library/Application Support/Perceptive Automation/Indigo 6/Plugins/piBeacon.indigoPlugin/Contents/Server Plugin
		p = max(0, self.pathToPlugin.lower().find(u"/plugins/")) + 1
		self.indigoPath			= self.pathToPlugin[:p]
		major, minor, release = map(int, indigo.server.version.split("."))
		self.indigoVersion		= major
		self.pluginVersion		= pluginVersion
		self.pluginId			= pluginId
		self.pluginName			= pluginId.split(".")[-1]
		self.myPID				= os.getpid()
		indigo.server.log(u"setting parameters for indigo version: >>"+unicode(self.indigoVersion)+u"<<; my PID="+str(self.myPID))	 
		indigo.server.log(u"pluginId: "+unicode(self.pluginId))	  
		self.pluginState				= "init"
		self.pluginShortName 	= "piBeacon"

####-------------------------------------------------------------------------####
	def __del__(self):
		indigo.PluginBase.__del__(self)

	###########################		INIT	## START ########################

####-------------------------------------------------------------------------####
	def startup(self):
		try:
			
			#indigo.server.log(u"Install Path: {0}".format(indigo.server.getInstallFolderPath()))
			#indigo.server.log(u"Database: {0}/{1}".format(indigo.server.getDbFilePath(), indigo.server.getDbName()))		 selfself.ML.myLog( text =	= myLogPgms.myLogPgmsself.ML.myLog( text = X()


			self.ML = myLogPgms.myLogPgms.MLX()
	   
			self.startTime		= time.time()
			self.checkPluginPath()

			self.getDebugLevels()

			self.setVariables()

			#### basic check if we can do get path for files			 
			self.initFileDir()

			self.checkcProfile()

 
			indigo.server.log( u" --V " + self.pluginVersion + u"	initializing ")
			if self.logFileActive !="standard" : self.ML.myLog( text = u" --V " + self.pluginVersion + u"     initializing  -- ")


			self.setupBasicFiles()



			self.startupFIXES0()


			self.getFolderIdOfBeacons()


			self.initCARS()

			self.readConfig()

			## create the folder and variables we use to receive the messages from the pis through the indigo webserver
			self.deleteAndCeateVariables(False)

			self.startupFIXES1()
			
			self.resetMinMaxSensors(init=True)


			self.statusChanged = 0
			self.setGroupStatus(init=True)		  

			self.checkPiEnabled()
			
			self.ML.myLog( text =  u" ..  startup() finished ")
	   
		except	Exception, e:
			self.errorLog(u"--------------------------------------------------------------------------------------------------------------")
			self.errorLog(u"Error in startup of plugin, waiting for 2000 secs then restarting plugin")
			self.errorLog(u"in Line '%s' has error='%s'" % (sys.exc_traceback.tb_lineno, e))
			self.errorLog(u"--------------------------------------------------------------------------------------------------------------")
			self.sleep(2000)
			exit(1)
		return
		




####-------------------------------------------------------------------------####
	def checkPluginPath(self):
		try:
			indigo.server.log(u"starting " + self.pluginName)
			if self.pathToPlugin.find(u"/" + self.pluginName + ".indigoPlugin/") == -1:
				self.errorLog(u"--------------------------------------------------------------------------------------------------------------")
				self.errorLog(u"The pluginname is not correct, please reinstall or rename")
				self.errorLog(u"It should be   /Libray/....../Plugins/" + self.pluginName + ".indigPlugin")
				p = max(0, self.pathToPlugin.find(u"/Contents/Server"))
				self.errorLog(u"It is: " + self.pathToPlugin[:p])
				self.errorLog(u"please check your download folder, delete old *.indigoPlugin files or this will happen again during next update")
				self.errorLog(u"---------------------------------------------------------------------------------------------------------------")
				self.sleep(2000)
				exit(1)
				
		except	Exception, e:
			self.errorLog(u"--------------------------------------------------------------------------------------------------------------")
			self.errorLog(u"Error in startup of plugin, waiting for 2000 secs then restarting plugin")
			self.errorLog(u"in Line '%s' has error='%s'" % (sys.exc_traceback.tb_lineno, e))
			self.errorLog(u"--------------------------------------------------------------------------------------------------------------")
			self.sleep(2000)
			exit(1)
		return

####-------------------------------------------------------------------------####
	def initFileDir(self):

			if not os.path.exists(self.userIndigoDir):
				os.mkdir(self.userIndigoDir)

	
			if not os.path.exists(self.userIndigoPluginDir):
				os.mkdir(self.userIndigoPluginDir)
			if not os.path.exists(self.userIndigoPluginDir):
				self.errorLog(u"error creating the plugin data dir did not work, can not create: "+ self.userIndigoPluginDir)
				self.sleep(1000)
				exit()
				
			if os.path.exists(self.oldIndigoDir + "all") and not os.path.exists(self.userIndigoPluginDir + "all"):
				indigo.server.log(u" moving "+ "cp -R" + self.oldIndigoDir+"* " + self.userIndigoPluginDir )
				os.system(u"cp -R " + self.oldIndigoDir+"* " + self.userIndigoPluginDir )

			if not os.path.exists(self.userIndigoPluginDir+"plotPositions"):
				os.mkdir(self.userIndigoPluginDir+"plotPositions")
			if not os.path.exists(self.cameraImagesDir):
				os.mkdir(self.cameraImagesDir)


####-------------------------------------------------------------------------####
	def startupFIXES1(self):
		try:
			dateString = datetime.datetime.now().strftime(_defaultDateStampFormat)
			##map uuid to beacon type
			self.UUIDtoType = {}
			for xx in _GlobalConst_typeOfBeacons:
				if _GlobalConst_typeOfBeacons[xx] != "":
					self.UUIDtoType[_GlobalConst_typeOfBeacons[xx]] = xx

		
			self.sprinklerDeviceActive = False

			######## fix  battery prop	and signal if not used 
			try:
				for dev in indigo.devices.iter(self.pluginId):
					if dev.deviceTypeId == u"beacon" or (dev.deviceTypeId.lower()) ==u"rpi":
						for pi in range(_GlobalConst_numberOfiBeaconRPI):
							if len(dev.states[u"Pi_"+unicode(pi)+"_Time"]) < 5 or dev.states[u"Pi_"+unicode(pi)+u"_Time"] is None :
								if unicode(dev.states[u"Pi_"+unicode(pi)+u"_Signal"]) == "0":
									self.addToStatesUpdateDict(unicode(dev.id),u"Pi_"+unicode(pi)+u"_Signal",-999,dev=dev)
						self.executeUpdateStatesDict(calledFrom="startupFIXES1")


					upd = False
					props = dev.pluginProps
					if u"SupportsBatteryLevel" in props:
						props[u"SupportsBatteryLevel"] = False
						upd = True

					if u"addNewOneWireSensors" in props:   # reset accept new one wire devcies 
						props[u"addNewOneWireSensors"] = "0"
						upd = True

						
					if "lastSensorChange" in dev.states:
						if len(dev.states["lastSensorChange"]) < 5:
							dev.updateStateOnServer(u"lastSensorChange",dateString)

					if dev.deviceTypeId == u"BLEconnect":
						props["isBLEconnectDevice"] = True

					if dev.deviceTypeId in _GlobalConst_allowedSensors:
						props["isSensorDevice"] = True
						upd = True

					if dev.deviceTypeId in _GlobalConst_allowedOUTPUT:
						props["isOutputDevice"] = True
						upd = True
						
					if (dev.deviceTypeId.lower()) =="rpi":
						props["isRPIDevice"] = True
						props["typeOfBeacon"] =u"rPI"
						upd = True
						if props[u"address"] in self.beacons:
							self.beacons[props[u"address"]][u"typeOfBeacon"] = u"rPI"

					if dev.deviceTypeId =="rPI-Sensor":
						props["isRPISensorDevice"] = True
						upd = True

					if dev.deviceTypeId =="beacon":
						props["isBeaconDevice"] = True
						upd = True

					if dev.deviceTypeId =="car":
						props["isCARDevice"] = True
						upd = True

					if upd:
						dev.replacePluginPropsOnServer(props)
							
			except	Exception, e:
				self.ML.myLog( text =  u"startupFIXES in Line '%s' has error='%s'" % (sys.exc_traceback.tb_lineno, e))
			try:
				os.remove(self.userIndigoPluginDir + "config")
			except:
				pass


		except	Exception, e:
			self.errorLog(u"--------------------------------------------------------------------------------------------------------------")
			self.errorLog(u"Error in startup of plugin, waiting for 2000 secs then restarting plugin")
			self.errorLog(u"in Line '%s' has error='%s'" % (sys.exc_traceback.tb_lineno, e))
			self.errorLog(u"--------------------------------------------------------------------------------------------------------------")
			self.sleep(2000)
			exit(1)
		return


####-------------------------------------------------------------------------####
	def initCARS(self):
			try:
				self.CARS = {u"carId":{},u"beacon":{}}
				self.checkCarsNeed = {}
				return 
				for beacon in self.beacons:
					if beacon in self.CARS[u"beacon"]: 
						try: 
							indogoId = self.beacons[beacon][u"indigoId"]
							if indogoId >0:
								dev= indigo.devices[self.beacons[beacon][u"indigoId"]]
								self.updateCARS(beacon,dev,dev.states,force=True)
						except: pass

			except:
				pass


####-------------------------------------------------------------------------####
	def setupBasicFiles(self):
		try:

			if not os.path.exists(self.userIndigoPluginDir + u"all"):
				os.mkdir(self.userIndigoPluginDir + u"all")
			if not os.path.exists(self.userIndigoPluginDir + u"rejected"):
				os.mkdir(self.userIndigoPluginDir + u"rejected")
				os.system(u" mv " + self.userIndigoPluginDir + u"rejct* " + self.userIndigoPluginDir + u"rejected")
			if not os.path.exists(self.userIndigoPluginDir + u"interfaceFiles"):
				os.mkdir(self.userIndigoPluginDir + u"interfaceFiles")
				os.system(u"rm " + self.userIndigoPluginDir + u"param*")
				os.system(u"rm " + self.userIndigoPluginDir + u"interfa*")
				os.system(u"rm " + self.userIndigoPluginDir + u"wpa_supplicant*")
			if not os.path.exists(self.userIndigoPluginDir + u"soundFiles"):
				os.mkdir(self.userIndigoPluginDir + u"soundFiles")
			if not os.path.exists(self.userIndigoPluginDir + u"displayFiles"):
				os.mkdir(self.userIndigoPluginDir + u"displayFiles")
			if not os.path.exists(self.cameraImagesDir):
				os.mkdir(self.cameraImagesDir)
		
		except	Exception, e:
			self.errorLog(u"--------------------------------------------------------------------------------------------------------------")
			self.errorLog(u"Error in startup of plugin, waiting for 2000 secs then restarting plugin")
			self.errorLog(u"in Line '%s' has error='%s'" % (sys.exc_traceback.tb_lineno, e))
			self.errorLog(u"--------------------------------------------------------------------------------------------------------------")
			self.sleep(2000)
			exit(1)
		return

####-------------------------------------------------------------------------####
	def startupFIXES0(self): # change old names used


		try:
			for dev in indigo.devices.iter("props.isBeaonDevice,props.isRPIDevice,props.isRPISensorDevice,props.isBLEconnectDevice"):
				if not dev.enabled: continue
				try:
					if u"lastStatusChange" in dev.states:
						dateString	= datetime.datetime.now().strftime(_defaultDateStampFormat)
						dateString2 = dev.states[u"lastStatusChange"]
						if len(dateString2) < 10:
								dev.updateStateOnServer("lastStatusChange",dateString)
						else:
							dateString = dateString2
				
						if u"displayStatus" in dev.states:
							new =  self.padDisplay(dev.states[u"status"]) + dateString[5:]
							if new != dev.states[u"displayStatus"]:
								dev.updateStateOnServer("displayStatus",new)
							if	 u"up" in new:
								dev.updateStateImageOnServer(indigo.kStateImageSel.SensorOn)
							elif  u"down" in new:
								dev.updateStateImageOnServer(indigo.kStateImageSel.SensorOff)
							else:
								dev.updateStateImageOnServer(indigo.kStateImageSel.SensorTripped)

				except	Exception, e:
						indigo.server.log(dev.name+"  "+u"startupFIXES0 in Line '%s' has error='%s'" % (sys.exc_traceback.tb_lineno, e))
		except	Exception, e:
				indigo.server.log(dev.name+"  "+u"startupFIXES0 in Line '%s' has error='%s'" % (sys.exc_traceback.tb_lineno, e))
		return


####-------------------------------------------------------------------------####
	def getDebugLevels(self):
		try:
			self.debugLevel			= []
			for d in ["Logic","DevMgmt","BeaconData","SensorData","OutputDevice","UpdateRPI","OfflineRPI","Fing","BLE","CAR","BC","all","Socket","Special","PlotPositions"]:
				if self.pluginPrefs.get(u"debug"+d, False): self.debugLevel.append(d)
			

			self.debugRPILevel={}
			self.debugRPILevel[u"debugRPICALL"]				 = int(self.pluginPrefs.get(u"debugRPICALL", 0))
			self.debugRPILevel[u"debugRPIBEACON"]			 = int(self.pluginPrefs.get(u"debugRPIBEACON", 0))
			self.debugRPILevel[u"debugRPISENSOR"]			 = int(self.pluginPrefs.get(u"debugRPISENSOR", 0))
			self.debugRPILevel[u"debugRPIOUTPUT"]			 = int(self.pluginPrefs.get(u"debugRPIOUTPUT", 0))
			self.debugRPILevel[u"debugRPIBLE"]				 = int(self.pluginPrefs.get(u"debugRPIBLE", 0))
			self.debugRPILevel[u"debugRPImystuff"]			 = int(self.pluginPrefs.get(u"debugRPImystuff", 0))
		except	Exception, e:
			self.errorLog(u"--------------------------------------------------------------------------------------------------------------")
			self.errorLog(u"Error in startup of plugin, waiting for 2000 secs then restarting plugin")
			self.errorLog(u"in Line '%s' has error='%s'" % (sys.exc_traceback.tb_lineno, e))
			self.errorLog(u"--------------------------------------------------------------------------------------------------------------")
			self.sleep(2000)
			exit(1)
		return




####-------------------------------------------------------------------------####
	def setVariables(self):
		try:
			self.MAChome					= os.path.expanduser(u"~")
			self.userIndigoDir				= self.MAChome + "/indigo/"
			self.userIndigoPluginDir		= self.userIndigoDir + u"piBeacon/"
			self.oldIndigoDir				= self.MAChome + u"/documents/piBeacon/"
			self.cameraImagesDir			= self.userIndigoPluginDir+"cameraImages/"

			self.setLogfile(self.pluginPrefs.get("logFileActive2", "standard"))
			
			self.beaconsFileSort			= True
			self.parametersFileSort			= True
			self.RPIFileSort				= True
			
			self.bootWaitTime				= 100
			self.currentlyBooting			= time.time() + self.bootWaitTime + 25
			self.lastUPtoDown				= time.time() + 35
			self.checkIPSendSocketOk		= {}
			self.actionList					= []
			self.updateStatesDict			= {}
			self.executeUpdateStatesDictActive = ""

			self.newBeaconsLogTimer			= 0
			self.selectBeaconsLogTimer		= {}
			
			self.rPi						= {}
			self.beacons					= {}

			self.PasswordsAreSet			= 0
			self.indigoCommand				= ""
			self.countLoop					= 0
			self.selectedPiServer			= 0
			self.quitNow					= ""
			self.statusChanged				= 0

			self.maxParseSec				= "1.0"
			self.newIgnoreMAC				= 0
			self.upDateNotSuccessful		=  [0 for ii in range(_GlobalConst_numberOfRPI)]
			self.lastUpdateSend				= time.time()
			self.rejectedByPi				= {}
			self.sendInitialValue			= "" # will be dev.id if output should be send 

			self.beaconsIgnoreUUID			= {}
			self.updatePiBeaconNote			= {}
			self.updateNeeded				= ""
			self.updateNeededTimeOut		= 9999999999999999999999999999		  
			self.devUpdateList				= {}
		
			self.enableFING					= "0"
			self.timeErrorCount				= [0 for ii in range(_GlobalConst_numberOfRPI)]
			self.deleteHistoryAfterSeconds	= 84600
			self.configAndReboot			= ""
			self.initStatesOnServer			= True
			try:
				self.rPiCommandPORT			= self.pluginPrefs.get(u"rPiCommandPORT", u"9999")
			except:
				self.rPiCommandPORT			= "0" # port on rPis to receive commands ==0 disable
			try:
				self.iBeaconFolderName		= self.pluginPrefs.get(u"iBeaconFolderName", u"Pi_Beacons_new")
			except:
				self.iBeaconFolderName		= u"Pi_Beacons_new" 
			try:
				self.iBeaconFolderNameVariables	 = self.pluginPrefs.get(u"iBeaconFolderNameVariables", u"piBeacons")
			except:
				self.iBeaconFolderNameVariables	 = u"piBeacons" 
			try:
				self.automaticRPIReplacement= unicode(self.pluginPrefs.get(u"automaticRPIReplacement", u"False")).lower() == u"true" 
			except:
				self.automaticRPIReplacement= False 
			try:
				self.expTimeMultiplier= float(self.pluginPrefs.get(u"expTimeMultiplier", 2))
			except:
				self.expTimeMultiplier= 2. 



			try:
				self.enableRebootRPIifNoMessages  = int(self.pluginPrefs.get(u"enableRebootRPIifNoMessages", 999999999))
			except:
				self.enableRebootRPIifNoMessages  = 999999999

			try:
				self.tempUnits				= self.pluginPrefs.get(u"tempUnits", u"Celsius")
			except:
				self.tempUnits				= u"Celsius"

			try:
				self.tempDigits				 = int(self.pluginPrefs.get(u"tempDigits", 1))
			except:
				self.tempDigits				 = 1

			try:
				self.rainUnits				= self.pluginPrefs.get(u"rainUnits", u"mm")
			except:
				self.rainUnits				= u"mm"

			try:
				self.rainDigits				 = int(self.pluginPrefs.get(u"rainDigits", 0))
			except:
				self.rainDigits				 = 0

			try:
				self.pressureUnits			= self.pluginPrefs.get(u"pressureUnits", u"hPascal")
			except:
				self.pressureUnits			= u"hPascal"

			try:
				self.saveValuesDictChanged	= False
				self.saveValuesDict			= self.pluginPrefs.get(u"saveValuesDict", indigo.Dict())
			except:
				self.saveValuesDict			= indigo.Dict()

			try:
				self.distanceUnits			= float(self.pluginPrefs.get(u"distanceUnits", 1.))
			except:
				self.distanceUnits			= 1.0
			try:
				self.speedUnits				= float(self.pluginPrefs.get(u"speedUnits", 1.))
			except:
				self.speedUnits				= 1.0

			try:
				self.lightningTimeWindow			 = float(self.pluginPrefs.get(u"lightningTimeWindow", 10.))
			except:
				self.lightningTimeWindow			 = 10.0


			try:
				self.lightningNumerOfSensors			 = int(self.pluginPrefs.get(u"lightningNumerOfSensors", 1))
			except:
				self.lightningNumerOfSensors			 = 1



			try:
				self.maxParseSec			= self.pluginPrefs.get(u"maxParseSec", u"1.0")
			except:
				self.maxParseSec			= 1.0
			try:
				self.txPowerCutoffDefault	= int(self.pluginPrefs.get(u"txPowerCutoffDefault", 999.))
			except:
				self.txPowerCutoffDefault	= 999.
			try:
			 self.deleteHistoryAfterSeconds = int(self.pluginPrefs.get(u"deleteHistoryAfterSeconds", u"84600"))
			except:
			 self.deleteHistoryAfterSeconds = 84600
			try:
				self.secToDown				= float(self.pluginPrefs.get(u"secToDown", u"80"))
			except:
				self.secToDown				= 80.

			try:
				self.acceptNewiBeacons		= int(self.pluginPrefs.get(u"acceptNewiBeacons", 999))
				if self.acceptNewiBeacons  ==u"1": 
											  self.pluginPrefs[u"acceptNewiBeacons"] = -999
											  self.acceptNewiBeacons  = -999
				if self.acceptNewiBeacons  ==u"0": 
											  self.pluginPrefs[u"acceptNewiBeacons"] = 999
											  self.acceptNewiBeacons  = 999
			except:
				self.acceptNewiBeacons		= -999

			self.acceptJunkBeacons			= self.pluginPrefs.get(u"acceptJunkBeacons", u"0")


			try:
				self.sendFullUUID			= self.pluginPrefs.get(u"sendFullUUID", u"1")
			except:
				self.sendFullUUID			= u"0"

			try:
				self.removeJunkBeacons		= self.pluginPrefs.get(u"removeJunkBeacons", u"1")==u"1"
			except:
				self.removeJunkBeacons		= True

			try:
				self.restartBLEifNoConnect = self.pluginPrefs.get(u"restartBLEifNoConnect", u"1") == "1"
			except :
				self.restartBLEifNoConnect = True

			try:
				self.rebootWatchDogTime		= self.pluginPrefs.get(u"rebootWatchDogTime", u"-1")
			except:
				self.rebootWatchDogTime		= u"-1"

			self.constantUUIDmajMIN			= u"uuid-maj-min"
			self.lenOfUUID					= 32

			try:
				self.expectTimeout			= self.pluginPrefs.get(u"expectTimeout", u"15")
			except:
				self.expectTimeout			= "15"


			self.indigoInputPORT			= int(self.pluginPrefs.get(u"indigoInputPORT", 0))
			self.IndigoOrSocket				= (self.pluginPrefs.get(u"IndigoOrSocket", u"indigo"))
			self.dataStats					= {u"startTime": time.time()}
			try:	self.maxSocksErrorTime	= float(self.pluginPrefs.get(u"maxSocksErrorTime", u"600.")) 
			except: self.maxSocksErrorTime	= 600.
			self.portOfServer				= self.pluginPrefs.get(u"portOfServer", u"8176")
			self.userIdOfServer				= self.pluginPrefs.get(u"userIdOfServer", u"")
			self.passwordOfServer			= self.pluginPrefs.get(u"passwordOfServer", u"")
			self.authentication				= self.pluginPrefs.get(u"authentication", u"digest")
			self.myIpNumber					= self.pluginPrefs.get(u"myIpNumber", u"192.168.1.130")
			self.GPIOpwm					= self.pluginPrefs.get(u"GPIOpwm", 1)

			try:	self.rebootHour			= int(self.pluginPrefs.get(u"rebootHour", -1))
			except: self.rebootHour			= -1

			self.updateRejectListsCount		= 0
		
			try:
				self.sendAfterSeconds		= int(self.pluginPrefs.get(u"sendAfterSeconds", u"60"))
			except:
				self.sendAfterSeconds		= 60
			try:
				self.piUpdateWindow			= float(self.pluginPrefs.get(u"piUpdateWindow", 0))
			except:
				self.piUpdateWindow			= 0.

			self.rPiRestartCommand			= [u"" for ii in range(_GlobalConst_numberOfRPI)]  ## which part need to restart on rpi

			self.anyProperTydeviceNameOrId = 0

			self.lastexecuteUpdateStatesDictCalledFrom = "init"

			self.wifiSSID					= self.pluginPrefs.get(u"wifiSSID", u"")
			self.wifiPassword				= self.pluginPrefs.get(u"wifiPassword", u"")
			self.key_mgmt					= self.pluginPrefs.get(u"key_mgmt", u"")
			self.routerIP					= self.pluginPrefs.get(u"routerIP", u"192.168.1.1")
			self.wifiOFF					= self.pluginPrefs.get(u"wifiOFF", u"on")

			self.fingscanTryAgain			= False
			try:
				self.enableFING				= self.pluginPrefs.get(u"enableFING", u"0")
			except:
				self.enableFING				= u"0"
			self.sendBroadCastEventsList	= []
			self.enableBroadCastEvents		= self.pluginPrefs.get(u"enableBroadCastEvents", u"0" )

			self.freezeAddRemove			= False
			self.outdeviceForOUTPUTgpio		= ""
			self.queueList					= ""
			self.queueListBLE				= ""
			self.groupStatusList={}
			for group in _GlobalConst_groupList:
				self.groupStatusList[group] = {u"members":{},"allHome":"0", u"allAway":"0", u"oneHome":u"0", u"oneAway":u"0", u"nHome":0,u"nAway":0}
			self.groupStatusListALL			= {u"nHome":0,"nAway":0,u"anyChange":False}
			self.groupCountNameDefault		= self.pluginPrefs.get(u"groupCountNameDefault",u"iBeacon_Count_")
			self.ibeaconNameDefault			= self.pluginPrefs.get(u"ibeaconNameDefault",u"iBeacon_")
			self.triggerList				= []
			self.newADDRESS					= {}

			self.pythonPath					= u"/usr/bin/python2.6"
			if os.path.isfile(u"/usr/bin/python2.7"):
				self.pythonPath				= u"/usr/bin/python2.7"
			elif os.path.isfile(u"/usr/bin/python2.6"):
				self.pythonPath				= u"/usr/bin/python2.6"


			self.trackSignalStrengthIfGeaterThan = [99999.,"i"]
			self.trackSignalChangeOfRPI			 = False

			self.beaconPositionsUpdated			= 0

			self.lastFixConfig = 0
			
			self.wifiOFF										   = self.pluginPrefs.get(u"wifiOFF", u"on")



			############ plot beacon positions 
			try:	self.beaconPositionsUpdateTime				   = float(self.pluginPrefs.get(u"beaconPositionsUpdateTime", -1))
			except: self.beaconPositionsUpdateTime				   = -1.
			try:	self.beaconPositionsdeltaDistanceMinForImage   = float(self.pluginPrefs.get(u"beaconPositionsdeltaDistanceMinForImage",	 1.))
			except: self.beaconPositionsdeltaDistanceMinForImage   = 1.

			self.beaconPositionsData							   = {u"mac":{}}
			self.beaconPositionsData[u"Xscale"]						= self.pluginPrefs.get(u"beaconPositionsimageXscale", u"20" )
			self.beaconPositionsData[u"Yscale"]						= self.pluginPrefs.get(u"beaconPositionsimageYscale", u"30" )
			self.beaconPositionsData[u"Zlevels"]					= self.pluginPrefs.get(u"beaconPositionsimageZlevels", u"0,5" )
			self.beaconPositionsData[u"dotsY"]						= self.pluginPrefs.get(u"beaconPositionsimageDotsY", u"600" )
			self.beaconPositionsData[u"Outfile"]					= self.pluginPrefs.get(u"beaconPositionsimageOutfile", u"" )
			self.beaconPositionsData[u"Text"]						= self.pluginPrefs.get(u"beaconPositionsimageText", u"text on top" )
			self.beaconPositionsData[u"ShowCaption"]				= self.pluginPrefs.get(u"beaconPositionsimageShowCaption", u"0" )
			self.beaconPositionsData[u"TextPos"]					= self.pluginPrefs.get(u"beaconPositionsimageTextPos", u"0,0" )
			self.beaconPositionsData[u"TextSize"]					= self.pluginPrefs.get(u"beaconPositionsimageTextSize", u"12" )
			self.beaconPositionsData[u"TextColor"]					= self.pluginPrefs.get(u"beaconPositionsimageTextColor", u"#000000" )
			self.beaconPositionsData[u"TextRotation"]				= self.pluginPrefs.get(u"beaconPositionsimageTextRotation", u"0" )
			self.beaconPositionsData[u"compress"]					= self.pluginPrefs.get(u"beaconPositionsimageCompress",True )
			self.beaconPositionsData[u"ShowRPIs"]					= self.pluginPrefs.get(u"beaconPositionsimageShowRPIs", u"0" )
			self.beaconPositionsData[u"ShowExpiredBeacons"]			= self.pluginPrefs.get(u"beaconShowExpiredBeacons", u"0" )
			self.beaconPositionsLastCheck							= time.time() - 20
			
		except	Exception, e:
			self.errorLog(u"--------------------------------------------------------------------------------------------------------------")
			self.errorLog(u"Error in startup of plugin, waiting for 2000 secs then restarting plugin")
			self.errorLog(u"in Line '%s' has error='%s'" % (sys.exc_traceback.tb_lineno, e))
			self.errorLog(u"--------------------------------------------------------------------------------------------------------------")
			self.sleep(2000)
			exit(1)

		self.lastSaveConfig = 0

		return



####-------------------------------------------------------------------------####
	def setGroupStatus(self, init=False, devIdSelected=""):
		self.statusChanged = 0
		try:

			triggerGroup= {}
			for group in _GlobalConst_groupList:
				triggerGroup[group]={u"allHome":False,"allWay":False,"oneHome":False,"oneAway":False}

			for group in  _GlobalConst_groupList:
				self.groupStatusList[group][u"nAway"] = 0
				self.groupStatusList[group][u"nHome"] = 0
			self.groupStatusListALL[u"nHome"] = 0
			self.groupStatusListALL[u"nAway"] = 0
   
			okList =[]
						  
			for beacon	in self.beacons:
				if self.beacons[beacon][u"note"].find(u"beacon") !=0: continue
				if self.beacons[beacon][u"indigoId"] ==0 or self.beacons[beacon][u"indigoId"] ==u"": continue
				try:
					dev= indigo.devices[self.beacons[beacon][u"indigoId"]]
				except:
					continue
					
				if dev.deviceTypeId !="beacon":	  continue
				if dev.states[u"status"]==u"up":
					self.groupStatusListALL[u"nHome"]	  +=1
				else:							 
					self.groupStatusListALL[u"nAway"]	  +=1

				if dev.states[u"groupMember"] == "": continue
				if devIdSelected !="" and dev.id  !=devIdSelected:	continue
				if not dev.enabled:	 continue
				okList.append(unicode(dev.id))
				for group in _GlobalConst_groupList:
					if group in dev.states[u"groupMember"]:
						self.groupStatusList[group][u"members"][unicode(dev.id)] = True
						if dev.states[u"status"]==u"up":
							if self.groupStatusList[group][u"oneHome"] ==u"0":
								triggerGroup[group][u"oneHome"] = True
								self.groupStatusList[group][u"oneHome"]	  = u"1"
							self.groupStatusList[group][u"nHome"]	  +=1
						else:
							if self.groupStatusList[group][u"oneAway"] ==u"0":
								triggerGroup[group][u"oneAway"] = True
							self.groupStatusList[group][u"oneAway"]	  = u"1"
							self.groupStatusList[group][u"nAway"]	  +=1
 
 


			if init:
				for group in  _GlobalConst_groupList:
					removeList=[]
					for member in self.groupStatusList[group][u"members"]:
						if member not in okList:
							removeList.append(member)
					for member in  removeList:
						del self.groupStatusList[group][u"members"][member]


			for group in _GlobalConst_groupList:
				if self.groupStatusList[group][u"nAway"] == len(self.groupStatusList[group][u"members"]):
					if self.groupStatusList[group][u"allAway"] ==u"0":
						triggerGroup[group][u"allAway"] = True
					self.groupStatusList[group][u"allAway"]	  = u"1"
					self.groupStatusList[group][u"oneHome"]	  = u"0"
				else:		 
					self.groupStatusList[group][u"allAway"]	  = u"0"
					
				if self.groupStatusList[group][u"nHome"] == len(self.groupStatusList[group][u"members"]):
					if self.groupStatusList[group][u"allHome"] ==u"0":
						triggerGroup[group][u"allHome"] = True
					self.groupStatusList[group][u"allHome"]	  = u"1"
					self.groupStatusList[group][u"oneAway"]	  = u"0"
				else:		 
					self.groupStatusList[group][u"allHome"]	  = u"0"


			# now extra variables
			for group in _GlobalConst_groupList:
				for tType in [u"Home", u"Away"]:
					varName = self.groupCountNameDefault+group+"_"+tType
					gName="n"+tType
					try:
						var = indigo.variables[varName]
					except:
						indigo.variable.create(varName, u"",self.iBeaconFolderNameVariables)
						var = indigo.variables[varName]
					
					if var.value !=	 unicode(self.groupStatusList[group][gName]):	
						indigo.variable.updateValue(varName,unicode(self.groupStatusList[group][gName]))


			
			for tType in [u"Home", u"Away"]:
				varName = self.groupCountNameDefault+"ALL_"+tType
				gName="n"+tType
				try:
					var = indigo.variables[varName]
				except:
					indigo.variable.create(varName, u"", self.iBeaconFolderNameVariables)
					var = indigo.variables[varName]
				
				if var.value !=	 unicode(self.groupStatusListALL[gName]):	
					indigo.variable.updateValue(varName,unicode(self.groupStatusListALL[gName]))


			#for group in  self.groupStatusList:
			#self.ML.myLog( text = group+"	"+ unicode( self.groupStatusList[group]))
			#indigo.server.log(u"trigger list "+ unicode( self.triggerList))


			if	init != u"init" and len(self.triggerList) > 0:
				for group in triggerGroup:
					for tType in triggerGroup[group]:
						if triggerGroup[group][tType]:
							self.triggerEvent(group+"-"+tType)
				
		except	Exception, e:
			if len(unicode(e)) > 5 :
				self.ML.myLog( text =  u"setGroupStatus in Line '%s' has error='%s'" % (sys.exc_traceback.tb_lineno, e))


######################################################################################
	# Indigo Trigger Start/Stop
######################################################################################

####-------------------------------------------------------------------------####
	def triggerStartProcessing(self, trigger):
		self.triggerList.append(trigger.id)

####-------------------------------------------------------------------------####
	def triggerStopProcessing(self, trigger):
		if trigger.id in self.triggerList:
			self.triggerList.remove(trigger.id)

	#def triggerUpdated(self, origDev, newDev):
	#	self.triggerStopProcessing(origDev)
	#	self.triggerStartProcessing(newDev)


######################################################################################
	# Indigo Trigger Firing
######################################################################################

####-------------------------------------------------------------------------####
	def triggerEvent(self, eventId):
		if	time.time() < self.currentlyBooting: # no triggering in the first 100+ secs after boot 
			self.ML.myLog( text = u"triggerEvent: %s suppressed due to reboot" % eventId)
			return
		for trigId in self.triggerList:
			trigger = indigo.triggers[trigId]
			if trigger.pluginTypeId == eventId:
				indigo.trigger.execute(trigger)
		return




####-------------------------------------------------------------------------####
	def deleteAndCeateVariables(self, delete):
		try:
			piFolder = indigo.variables.folder.create(self.iBeaconFolderNameVariables)
		except :
			piFolder = indigo.variables.folders[self.iBeaconFolderNameVariables]

		### delete at midnight and (re) create	to save sql logger space , we dont need the history
		if delete:
			try:		indigo.variable.delete(u"pi_IN_Alive")
			except:		pass
			try:		indigo.variable.delete(u"pi_IN_format")
			except:		pass
			try:		indigo.variable.delete(self.ibeaconNameDefault+u"With_Status_Change")
			except:		pass
			try:		indigo.variable.delete(self.ibeaconNameDefault+u"With_ClosestRPI_Change")
			except:		pass
			try:		indigo.variable.delete(self.ibeaconNameDefault+u"Rebooting")
			except:		pass
			
		try:			indigo.variable.create(u"pi_IN_Alive", u"", piFolder)
		except:			pass
		try:			indigo.variable.create(self.ibeaconNameDefault+u"With_Status_Change", u"", piFolder)
		except:			pass
		try:			indigo.variable.create(self.ibeaconNameDefault+u"With_ClosestRPI_Change", u"", piFolder)
		except:			pass
		try:			indigo.variable.create(self.ibeaconNameDefault+u"Rebooting", u"", piFolder)
		except:			pass

		for pi in range(_GlobalConst_numberOfRPI):
			if delete:
				try:
					indigo.variable.delete(u"pi_IN_" + unicode(pi))
				except:
					pass
			try:
				indigo.variable.create(u"pi_IN_" + unicode(pi), u"", piFolder)
			except:
				pass
				
		try:			indigo.variable.create(u"lightningEventDate", u"", piFolder)
		except:			pass
		try:			indigo.variable.create(u"lightningEventDevices", u"0", piFolder)
		except:			pass

####-------------------------------------------------------------------------####
	def getFolderIdOfBeacons(self):
		self.piFolderId = 0
		try:
			self.piFolderId = indigo.devices.folders.getId(self.iBeaconFolderName)
			if self.piFolderId > 0:
				return
		except:
			pass
		try:
			ff = indigo.devices.folder.create(self.iBeaconFolderName)
			self.piFolderId = ff.id
		except:
			self.piFolderId = 0
			self.iBeaconFolderName = "Pi_Beacons_new"

		try:
			self.piFolderIdVariables = indigo.devices.folders.getId(self.iBeaconFolderNameVariables)
			if self.piFolderIdVariables > 0:
				return
		except:
			pass
		try:
			ff = indigo.variables.folder.create(self.iBeaconFolderNameVariables)
			self.piFolderIdVariables = ff.id
		except:
			self.piFolderIdVariables = 0
			self.iBeaconFolderNameVariables = "piBeacons"

		return


####-------------------------------------------------------------------------####
	def readTcpipSocketStats(self):
		self.dataStats ={}
		try:
			f = open(self.userIndigoPluginDir + "dataStats", u"r")
			self.dataStats = json.loads(f.read())
			f.close()
			if u"updates" not in self.dataStats:
				self.resetDataStats()
				return
			if u"nstates" not in self.dataStats[u"updates"]:
				self.resetDataStats()
				return
		except	Exception, e:
			self.resetDataStats() 
			self.ML.myLog( text = u"readTcpipSocketStats in Line '%s:'%s'" % (sys.exc_traceback.tb_lineno, e))
		if u"data" not in self.dataStats:
			self.resetDataStats() 

####-------------------------------------------------------------------------####
	def resetDataStats(self):
			self.dataStats={u"startTime": time.time(),"data":{},"updates":{u"devs":0,"states":0,"startTime": time.time(),"nstates":[0 for ii in range(11)]}}

		
####-------------------------------------------------------------------------####
	def saveTcpipSocketStats(self):
		 self.writeJson(self.dataStats, fName=self.userIndigoPluginDir + u"dataStats", format=True )


####------================----------- CARS ------================-----------
####-------------------------------------------------------------------------####
	def saveCARS(self,force=False):
		if force: self.cleanupDeepCARS()
		self.writeJson(self.CARS,fName=self.userIndigoPluginDir + u"CARS" )

####-------------------------------------------------------------------------####
	def readCARS(self):
		try:
			f = open(self.userIndigoPluginDir + "CARS", u"r")
			self.CARS = json.loads(f.read())
			f.close()
		except:
			self.sleep(1)
			try:
				f = open(self.userIndigoPluginDir + "CARS", u"r")
				self.CARS = json.loads(f.read())
				f.close()
			except	Exception, e:
				self.CARS={u"carId":{},"beacon":{}}

		for carIds in self.CARS[u"carId"]:
			self.updateAllCARbeacons(carIds)

		self.cleanupDeepCARS()


####-------------------------------------------------------------------------####
	def cleanupDeepCARS(self):
		try:
			delDD=[]
			for carIds in self.CARS[u"carId"]:
				try: indigo.devices[int(carIds)]
				except Exception, e:
					self.ML.myLog( text =  u"cleanupDeepCARS in Line '%s' has error='%s'" % (sys.exc_traceback.tb_lineno, e))
					if unicode(e).find(u"timeout waiting") > -1:
						self.ML.myLog( text =  u"communication to indigo is interrupted")
						return
					self.ML.myLog( text =  u"devId "+carIds+" not defined in devices  removing from	 CARS:"+unicode(self.CARS))
					delDD.append(carIds)
				if u"homeSince" not in self.CARS[u"carId"][carIds]:	 self.CARS[u"carId"][carIds][u"homeSince"] = 0
				if u"awaySince" not in self.CARS[u"carId"][carIds]:	 self.CARS[u"carId"][carIds][u"awaySince"] = 0
				if u"beacons"	not in self.CARS[u"carId"][carIds]:	 self.CARS[u"carId"][carIds][u"beacons"]   = {}
			for carIds in delDD:
				del self.CARS[u"carId"][carIds]
				
		except	Exception, e:
			self.ML.myLog( text = u"cleanupDeepCARS in Line '%s:'%s'" % (sys.exc_traceback.tb_lineno, e))


####-------------------------------------------------------------------------####
	def updateAllCARbeacons(self,indigoCarIds,force=False):
		try:
				beacon = ""
				if self.ML.decideMyLog(u"CAR"): self.ML.myLog( text = u"updateAllCARbeacons	 CARS:" + unicode(self.CARS))
				for beacon in self.CARS[u"beacon"]:
					if indigoCarIds	 !=	 unicode(self.CARS[u"beacon"][beacon][u"carId"]) and not force: continue
					beaconDevId = self.beacons[beacon][u"indigoId"]
					beaconDev	= indigo.devices[beaconDevId]
					if self.ML.decideMyLog(u"CAR"): self.ML.myLog( text =  u"updating all cars")
					self.updateCARS(beacon,beaconDev,beaconDev.states, force=True)
					break
					
		except	Exception, e:
			self.ML.myLog( text = u"updateAllCARbeacons in Line '%s:'%s'" % (sys.exc_traceback.tb_lineno, e))
			self.ML.myLog( text = u"updateAllCARbeacons beacon		 " +beacon)
			self.ML.myLog( text = u"updateAllCARbeacons indigoCarIds " +indigoCarIds)

####-------------------------------------------------------------------------####
	def updateCARS(self,beacon,beaconDev,beaconNewStates,force=False):
		try:
			if beacon not in self.CARS[u"beacon"]: return
			if len(beacon) < 10: return
			indigoCarIds = unicode(self.CARS[u"beacon"][beacon][u"carId"])
			if indigoCarIds not in	self.CARS[u"carId"]: # pointer to indigo ID
				self.ML.myLog( text = beacon+u" beacon: not found in CARS[carId], removing from dict;  CARSdict: " + unicode(self.CARS))
				del self.CARS[u"beacon"][beacon]
				return
			indigoIDofBeacon = beaconDev.id
			carDev			 = indigo.devices[int(indigoCarIds)]
			props			 = carDev.pluginProps
			carName			 = carDev.name
			if beaconDev.states[u"status"] == beaconNewStates[u"status"] and not force:
				if self.ML.decideMyLog(u"CAR"): self.ML.myLog( text = "updateCARS:	"+carName+u"  "+beacon+u" no change")
				return
				 
			try:	whatForStatus = carDev.pluginProps[u"displayS"]	 
			except: whatForStatus = ""
			if whatForStatus ==u"": whatForStatus="location" 

			oldCarStatus	 = carDev.states[u"location"]
			oldCarEngine	 = carDev.states[u"engine"]
			oldCarMotion	 = carDev.states[u"motion"]
			oldBeaconStatus	 = beaconDev.states[u"status"]
			newBeaconStatus	 = beaconNewStates[u"status"]
			beaconType		 = self.CARS[u"beacon"][beacon][u"beaconType"]
			beaconBattery	 = 0
			beaconUSB		 = 0
			beaconKey		 = 2
			nKeysFound		 = 0
			oldAwaySince = self.CARS[u"carId"][indigoCarIds][u"awaySince"] 
			oldHomeSince = self.CARS[u"carId"][indigoCarIds][u"homeSince"] 
			if self.ML.decideMyLog(u"CAR"): self.ML.myLog( text = carName+"-"+indigoCarIds+u"  "+beacon+u" updating "+beaconType+", oldBeaconStatus="+	oldBeaconStatus+", newBeaconStatus="+  newBeaconStatus+"  oldAwaySince:"+str(time.time()-oldAwaySince)+"  oldHomeSince:"+str(time.time()-oldHomeSince)+", oldCarStatus="+oldCarStatus+", oldCarEngine="+oldCarEngine+", oldCarMotion="+oldCarMotion)

			if beaconType == "beaconBattery":	 
				if newBeaconStatus	==u"up": beaconBattery = 2	## battery beacon is home
				else:						beaconBattery = 1 
			if beaconType == "beaconUSB":		 
				if newBeaconStatus	==u"up": beaconUSB	   = 2	## usb beacon is home
				else:						beaconUSB	  = 1
			if beaconType.find(u"beaconKey")>-1: 
				if newBeaconStatus	!="up": beaconKey	  = 1  # at least one is missing
				nKeysFound	+= 1

			for b in self.CARS[u"carId"][indigoCarIds][u"beacons"]:
				beaconTypeTest = self.CARS[u"beacon"][b][u"beaconType"]
				if beaconTypeTest == beaconType: continue
				if indigoCarIds != unicode(self.CARS[u"beacon"][b][u"carId"]): continue
				indigoDEV  = indigo.devices[self.beacons[b][u"indigoId"]]
				st = indigoDEV.states[u"status"]
				if self.ML.decideMyLog(u"CAR"): self.ML.myLog( text = carName+"-"+indigoCarIds+" testing dev="+ indigoDEV.name+"  st="+st+"	 type="+beaconTypeTest) 

				if beaconTypeTest == "beaconBattery":	 
					if st  ==u"up": beaconBattery = 2  ## battery beacon is home
					else:			beaconBattery = 1 
				if beaconTypeTest == "beaconUSB":		 
					if st  ==u"up": beaconUSB		 = 2  ## usb beacon is home
					else:			beaconUSB		 = 1
				if beaconTypeTest.find(u"beaconKey")>-1: 
					if st  != "up": beaconKey	= 1
					nKeysFound += 1
					
			if nKeysFound ==0:		beaconKey	= 0

			self.checkCarsNeed[indigoCarIds]= 0



			updateProps = False
			if u"address" not in props: 
				props[u"address"] ="away"
				updateProps=True
			if (beaconBattery==2 or beaconUSB==2 or beaconKey==2) and props[u"address"] ==u"away":
				props[u"address"] = "home"
				updateProps=True
			elif not (beaconBattery==2 or beaconUSB==2 or beaconKey==2) and props[u"address"] ==u"home":
				props[u"address"] = "away" 
				updateProps=True

			self.addToStatesUpdateDict(indigoCarIds,"motion",carDev.states[u"motion"],dev=carDev)
			
			if	 beaconUSB==2: 
				self.addToStatesUpdateDict(indigoCarIds,"engine", u"on")
			elif beaconUSB==1:
				self.addToStatesUpdateDict(indigoCarIds,"engine", u"off")

			if not (beaconBattery==2 or beaconUSB==2 or beaconKey==2):	# nothing on = gone , away ..
				self.addToStatesUpdateDict(indigoCarIds,"location", u"away")
				if oldCarStatus !="away": 
					self.setIcon(carDev,props,"SensorOff-SensorOn",0)
					self.CARS[u"carId"][indigoCarIds][u"awaySince"] = time.time()
					self.addToStatesUpdateDict(indigoCarIds,"LastLeaveFromHome",datetime.datetime.now().strftime(_defaultDateStampFormat))
				self.addToStatesUpdateDict(indigoCarIds,"motion", u"left")
				self.addToStatesUpdateDict(indigoCarIds,"engine", u"unknown")
				self.checkCarsNeed[indigoCarIds]= 0

			else:	  # something on, we are home.
				if self.ML.decideMyLog(u"CAR"): self.ML.myLog( text = carName+"- setting to be home,   oldCarStatus:"+oldCarStatus)
				self.addToStatesUpdateDict(indigoCarIds,"location", u"home")
				if oldCarStatus !="home": 
					self.CARS[u"carId"][indigoCarIds][u"homeSince"] = time.time()
					self.addToStatesUpdateDict(indigoCarIds,"LastArrivalAtHome",datetime.datetime.now().strftime(_defaultDateStampFormat))



			if self.ML.decideMyLog(u"CAR"): self.ML.myLog( text = carName+"-"+indigoCarIds+" update states (1)	: type: "+beaconType+"	bat="+str(beaconBattery)+"	USB="+str(beaconUSB)+"	Key="+str(beaconKey)+ "	 car newawaySince="+unicode(int(time.time()-self.CARS[u"carId"][indigoCarIds][u"awaySince"]))+" newhomeSince="+unicode(int(time.time()-self.CARS[u"carId"][indigoCarIds][u"homeSince"])) )

			if	oldCarStatus == "away":
			
				if beaconBattery==2 or beaconUSB==2 or beaconKey==2: 
					self.setIcon(carDev,props,"SensorOff-SensorOn",1)
					if time.time() - self.CARS[u"carId"][indigoCarIds][u"awaySince"]  > 120: # just arriving home, was away for some time
						self.addToStatesUpdateDict(indigoCarIds,"motion", u"arriving")
						self.checkCarsNeed[indigoCarIds]= 0
							
					else : # is this a fluke?
						self.addToStatesUpdateDict(indigoCarIds,"motion", u"unknown")
						self.checkCarsNeed[indigoCarIds]= time.time() + 20

				elif indigoCarIds in self.updateStatesDict and "location" in self.updateStatesDict[indigoCarIds] and self.updateStatesDict[indigoCarIds]["location"]["value"] == "home":
						self.ML.myLog( text = carName+"-"+indigoCarIds+u" beacon: "+beacon+" bad state , coming home, but no beacon is on")
						self.checkCarsNeed[indigoCarIds]= time.time() + 20

				if carDev.states[u"LastLeaveFromHome"] ==u"": self.addToStatesUpdateDict(indigoCarIds,"LastLeaveFromHome",datetime.datetime.now().strftime(_defaultDateStampFormat))



			else:  ## home
				if (beaconBattery==2 or beaconUSB==2 or beaconKey==2): 
					if	beaconUSB==1 : # engine is off
						if	 oldCarMotion == "arriving" and time.time() - self.CARS[u"carId"][indigoCarIds][u"homeSince"] > 10:	 
								self.addToStatesUpdateDict(indigoCarIds,"motion", u"stop")
						elif oldCarMotion == "leaving"	and time.time() - self.CARS[u"carId"][indigoCarIds][u"homeSince"] >200: 
								self.addToStatesUpdateDict(indigoCarIds,"motion", u"stop")
						elif oldCarMotion == "left"		and time.time() - self.CARS[u"carId"][indigoCarIds][u"homeSince"] < 60: 
								self.addToStatesUpdateDict(indigoCarIds,"motion", u"arriving")
						elif oldCarMotion == "": 
								self.addToStatesUpdateDict(indigoCarIds,"motion", u"stop")
						elif oldCarMotion == "unknown": 
								self.addToStatesUpdateDict(indigoCarIds,"motion", u"stop")
						elif oldCarMotion == "stop": 
								pass
						else:
								self.checkCarsNeed[indigoCarIds]= time.time() + 20
							
					if	beaconUSB==2 : # engine is on
						if time.time() - self.CARS[u"carId"][indigoCarIds][u"homeSince"] >600: 
							self.addToStatesUpdateDict(indigoCarIds,"motion", u"leaving")
						elif time.time() - self.CARS[u"carId"][indigoCarIds][u"homeSince"] >60 and oldCarMotion == "stop": 
							self.addToStatesUpdateDict(indigoCarIds,"motion", u"leaving")
						elif time.time() - self.CARS[u"carId"][indigoCarIds][u"homeSince"] <30 and oldCarMotion in[u"unknown", u"leaving"]: 
							self.addToStatesUpdateDict(indigoCarIds,"motion", u"arriving")
						else:
							self.checkCarsNeed[indigoCarIds]= time.time() + 20

				else:
					self.checkCarsNeed[indigoCarIds]= time.time() + 20

				if carDev.states[u"LastArrivalAtHome"] ==u"": self.addToStatesUpdateDict(indigoCarIds,"LastArrivalAtHome",datetime.datetime.now().strftime(_defaultDateStampFormat))

			if updateProps:
					carDev.replacePluginPropsOnServer(props)
					carDev			 = indigo.devices[int(indigoCarIds)]

			st= ""
			whatForStatus = whatForStatus.split(u"/")
			if u"location" in whatForStatus: st =	   self.updateStatesDict[indigoCarIds][u"location"]["value"]
			if u"engine"   in whatForStatus: st +="/"+ self.updateStatesDict[indigoCarIds][u"engine"]["value"]
			if u"motion"   in whatForStatus: st +="/"+ self.updateStatesDict[indigoCarIds][u"motion"]["value"]
			st = st.strip(u"/").strip(u"/")
			self.addToStatesUpdateDict(indigoCarIds,"status",st)
			if self.updateStatesDict[indigoCarIds][u"location"]["value"] ==u"home":
				carDev.updateStateImageOnServer(indigo.kStateImageSel.SensorOn)
			else:
				carDev.updateStateImageOnServer(indigo.kStateImageSel.SensorTripped)
			
			if self.ML.decideMyLog(u"CAR"): self.ML.myLog( text = carName+"-"+indigoCarIds+" update states (2)	: type: "+beaconType+ "	 car newawaySince="+unicode(int(time.time() - self.CARS[u"carId"][indigoCarIds][u"awaySince"]))+" newhomeSince="+unicode(int(time.time() - self.CARS[u"carId"][indigoCarIds][u"homeSince"])) )
			if indigoCarIds in self.checkCarsNeed: 
				if self.ML.decideMyLog(u"CAR"):self.ML.myLog( text = carName+"-"+indigoCarIds+" update states (2)  checkCarsNeed time since last= "+str(int(time.time() - self.checkCarsNeed[indigoCarIds])))
			if self.ML.decideMyLog(u"CAR"): self.ML.myLog( text = carName+"-"+indigoCarIds+" updateStatesList(2):"+unicode(self.updateStatesDict))
		except	Exception, e:
			self.ML.myLog( text = u"updateCARS in Line '%s: has error'%s'" % (sys.exc_traceback.tb_lineno, e))


		return 


####-------------------------------------------------------------------------####
	def setupCARS(self,carIdi,props,mode=""):
		try:
			carIds= unicode(carIdi)
			if carIds not in self.CARS[u"carId"]:
				self.CARS[u"carId"][carIds]= {}
			if u"homeSince" not in self.CARS[u"carId"][carIds]:	 self.CARS[u"carId"][carIds][u"homeSince"] = 0
			if u"awaySince" not in self.CARS[u"carId"][carIds]:	 self.CARS[u"carId"][carIds][u"awaySince"] = 0
			if u"beacons"	not in self.CARS[u"carId"][carIds]:	 self.CARS[u"carId"][carIds][u"beacons"]   = {}

			dev = indigo.devices[carIdi]
			update,text = self.setupBeaconsForCARS(props,carIds)
	 
		except	Exception, e:
			self.ML.myLog( text = u"setupCARS in Line '%s:'%s'" % (sys.exc_traceback.tb_lineno, e))
			if unicode(e).find(u"timeout waiting") > -1:
				self.ML.myLog( text =  u"communication to indigo is interrupted")
			self.ML.myLog( text =  u"devId "+carIds+" indigo lookup/save problem")
			return 

		try:
			if mode in [u"init", u"validate"]:
				if self.ML.decideMyLog(u"CAR"): self.ML.myLog( text =  u"setupCARS updating states mode:"+ mode+";	updateStatesList:"+unicode(self.updateStatesDict))
				if u"description" not in props: props[u"description"]=""
				if props[u"description"] != text:
					props[u"description"]= text
					dev.replacePluginPropsOnServer(props)
				self.executeUpdateStatesDict(onlyDevID=carIds,calledFrom="setupCARS ")
			if update: 
				self.setALLrPiV(u"piUpToDate", [u"updateParamsFTP"])
		except	Exception, e:
			self.ML.myLog( text = u"setupCARS in Line '%s:'%s'" % (sys.exc_traceback.tb_lineno, e))
			return props
		return	props
		
####-------------------------------------------------------------------------####
	def setupBeaconsForCARS(self,propsCar,carIds):
		try:
			##self.ML.myLog( text = carIds+" props"+unicode(propsCar))
			beaconList=[]
			text="Beacons:"
			update = False
			for beaconType in propsCar:
				if beaconType.find(u"beacon") ==-1: continue
				try: beaconID= int(propsCar[beaconType])
				except: continue
				if int(beaconID) ==0: continue
				try:  beaconDev = indigo.devices[beaconID]
				except: continue
				beacon = beaconDev.address
				beaconList.append(beacon)
				self.CARS[u"beacon"][beacon]= {u"carId":carIds,"beaconType":beaconType}
				if beacon not in self.CARS[u"carId"][carIds][u"beacons"]:  self.CARS[u"carId"][carIds][u"beacons"][beacon]=beaconID
				text+=beaconType.split(u"beacon")[1]+"="+beaconDev.name+";"
				props = beaconDev.pluginProps
				if props[u"fastDown"] ==  "0":
					props[u"fastDown"] =  "15"
					if self.ML.decideMyLog(u"CAR"): self.ML.myLog( text = u"updating fastdown for "+beaconDev.name +" to 0")
					update=True
					beaconDev.replacePluginPropsOnServer(props)
				delB={}
				for b in self.CARS[u"carId"][carIds][u"beacons"]:
					if b not in self.CARS[u"beacon"] or b not in beaconList:
						delB[b]=1
				for b in delB:
					del self.CARS[u"carId"][carIds][u"beacons"][b]
					del self.CARS[u"beacon"][b]
		except Exception, e:
			self.ML.myLog( text =  u"setupBeaconsForCARS in Line '%s' has error='%s'" % (sys.exc_traceback.tb_lineno, e))
			if unicode(e).find(u"timeout waiting") > -1:
				self.ML.myLog( text =  u"communication to indigo is interrupted")
				return 1/0
			self.ML.myLog( text =  u"devId "+carIds+" indigo lookup/save problem,  in props:"+unicode(props)+"	CARS:"+unicode(self.CARS))
		return update,text.strip(u";")

####------================----------- CARS ------================-----------END


####------================------- sprinkler ------================-----------
	########################################
	# Sprinkler Control Action callback
	######################
	def actionControlSprinkler(self, action, dev):
		props		= dev.pluginProps
		#indigo.server.log("actionControlSprinkler: "+ unicode(props)+"\n\n"+ unicode(action))
		pi			= str(props["piServerNumber"])
		ipNumberPi	= self.RPI[pi]["ipNumberPi"]
		devId		= int(self.RPI[pi]["piDevId"])
		deviceDefs	= [{"gpio":-1,u"outType":1}]
		dictForRPI	= {"cmd":"",u"OUTPUT":0,u"deviceDefs":json.dumps(deviceDefs),u"typeId":"OUTPUTgpio-1",u"outputDev":"Sprinkler","piServerNumber": pi,"ipNumberPi":ipNumberPi,"nPulses":0,u"devId":devId}

		### !!!	 zoneindex goes from 1 ... n !!!

		########################################
		# Required plugin sprinkler actions: These actions must be handled by the plugin.
		########################################
		###### ZONE ON ######
		if action.sprinklerAction == indigo.kSprinklerAction.ZoneOn:
			# first reset all relays -- besides the new and controll 
			if dev.pluginProps["PumpControlOn"]: nValves = dev.zoneCount-1
			else: nValves = dev.zoneCount
			try:	activeZone = int(int(action.zoneIndex))
			except: activeZone = 0
			if activeZone == 0: return 
			
			GPIOpin			   = []
			cmd				   = []
			inverseGPIO		   = []
			for nn in range(nValves):
				if nn+1 == int(action.zoneIndex):							 continue
				##if nn-1 ==  nValves and dev.pluginProps["PumpControlOn"]: continue 
				GPIOpin.append(props["GPIOzone"+str(nn+1)])
				dictForRPI["deviceDefs"] = json.dumps(deviceDefs)
				cmd.append("down")
				inverseGPIO.append(True)
			self.sendGPIOCommands( ipNumberPi, pi, cmd, GPIOpin, inverseGPIO)
			if dev.pluginProps["PumpControlOn"]: # last valve is the control valve 
				deviceDefs[0]["gpio"]	 = props["GPIOzone"+str(dev.zoneCount)]
				dictForRPI["deviceDefs"] = json.dumps(deviceDefs)
				dictForRPI["cmd"]		 = "pulseUp"
				dictForRPI["pulseUp"]	 = dev.zoneMaxDurations[action.zoneIndex-1]*60
				self.setPin(dictForRPI)

			self.sleep(0.1)	   ## we need to wait until all gpios are of, other wise then next might be before one of the last off
			deviceDefs[0]["gpio"]	 = props["GPIOzone"+str(action.zoneIndex)]
			dictForRPI["deviceDefs"] = json.dumps(deviceDefs)
			dictForRPI["cmd"]		 = "pulseUp"
			dictForRPI["pulseUp"]	 = dev.zoneMaxDurations[action.zoneIndex-1]*60
			self.setPin(dictForRPI)

			durations		 = dev.zoneScheduledDurations
			zoneMaxDurations = dev.zoneMaxDurations
			activeZone		 = int(int(action.zoneIndex))
			zoneStarted		 = datetime.datetime.now().strftime(_defaultDateStampFormat)
			timeLeft = 0
			dur = 0
			if activeZone > 0:
				secDone = (datetime.datetime.now() - datetime.datetime.strptime(zoneStarted, "%Y-%m-%d %H:%M:%S")).total_seconds()
				minutes	 = int(secDone/60)


				if len(durations) == nValves:
					dur		= min(durations[activeZone-1], zoneMaxDurations[activeZone-1]) + 0.2
					allDur = 0.1
					for mm in durations:
						allDur += mm
					allMinutes = 0.1
					if activeZone <= len(durations) and activeZone > 1:
						for mm in durations[0:activeZone-1]:
							allMinutes += mm
				else : # single zone manual, check if overwrite max duration
					if "sprinklerActiveZoneSetManualDuration" in indigo.variables:
						try:	dur = max(0,float(indigo.variables["sprinklerActiveZoneSetManualDuration"].value ) )
						except	Exception, e:
							indigo.server.log( u"actionControlSprinkler for variable sprinklerActiveZoneSetManualDuration in Line '%s' has error='%s'" % (sys.exc_traceback.tb_lineno, e)+" using max value instead")
							dur = 0
					if dur == 0:  # no overwrite, use max duration
								dur = zoneMaxDurations[activeZone-1]
					allMinutes = 0
					allDur = dur

				timeLeft	= int(max(0,(dur )))
				timeLeftAll = int(max(0,allDur-allMinutes +0.1) )
				dur			= int(dur)
				allDur		= int(allDur)

				self.addToStatesUpdateDict(str(dev.id), "activeZone",				 action.zoneIndex)
				self.addToStatesUpdateDict(str(dev.id), "activeZoneStarted",		 datetime.datetime.now().strftime(_defaultDateStampFormat))
				self.addToStatesUpdateDict(str(dev.id), "activeZoneMinutesLeft",	 timeLeft)
				self.addToStatesUpdateDict(str(dev.id), "activeZoneMinutesDuration", dur)
				self.addToStatesUpdateDict(str(dev.id), "allZonesMinutesDuration",	 allDur)
				self.addToStatesUpdateDict(str(dev.id), "allZonesMinutesLeft",		 timeLeftAll)





		###### ALL ZONES OFF ######
		elif action.sprinklerAction == indigo.kSprinklerAction.AllZonesOff:
			nValves = dev.zoneCount
			GPIOpin =[]
			cmd=[]
			inverseGPIO =[]
			for nn in range(nValves):
				GPIOpin.append(props["GPIOzone"+str(nn+1)])
				dictForRPI["deviceDefs"] = json.dumps(deviceDefs)
				cmd.append("down")
				inverseGPIO.append(True)
			self.sendGPIOCommands( ipNumberPi, pi, cmd, GPIOpin, inverseGPIO)
			self.addToStatesUpdateDict(str(dev.id), "activeZoneStarted",		"")
			self.addToStatesUpdateDict(str(dev.id), "activeZone",				 0)
			self.addToStatesUpdateDict(str(dev.id), "activeZoneMinutesLeft",	 0)
			self.addToStatesUpdateDict(str(dev.id), "activeZoneMinutesDuration", 0)
			self.addToStatesUpdateDict(str(dev.id), "allZonesMinutesLeft",		 0)
			self.addToStatesUpdateDict(str(dev.id), "allZonesMinutesDuration",	 0)

		self.executeUpdateStatesDict(onlyDevID=str(dev.id),calledFrom="")
		return 



####-------------------------------------------------------------------------####
	def initSprinkler(self, force = False):
		#self.lastSprinklerStats = "2018-05-31 23:23:00"
		self.lastSprinklerStats = datetime.datetime.now().strftime(_defaultDateStampFormat)

		for dev in indigo.devices.iter("props.isSprinklerDevice"):
			self.sprinklerDeviceActive = True
			for xx in ["minutesRunToday", "minutesRunThisWeek","minutesRunYesterday","minutesRunLastWeek","minutesRunThisMonth","minutesRunLastMonth"]:
				lastList = dev.states[xx].split(",")
				if len(lastList) != dev.zoneCount or force:
					lastList = ["0" for ii in range(dev.zoneCount)]
					lastList = ",".join(lastList)
					self.addToStatesUpdateDict(str(dev.id),xx,lastList)

			self.executeUpdateStatesDict(onlyDevID=str(dev.id))


####-------------------------------------------------------------------------####
	def resetSprinklerStats(self):	 ### called from the plugin menu
		self.initSprinkler(force=True)


####-------------------------------------------------------------------------####
	def sprinklerStats(self): 
		try: 
			if not self.sprinklerDeviceActive: return  
			now = datetime.datetime.now()
			dateString = now.strftime(_defaultDateStampFormat)
			# 2019-11-12 09:33:11
			# 1234567890123456789

			# same minute?
			if dateString[0:17] == self.lastSprinklerStats[0:17]: return




			newDay = False
			newWeek = False
			newMonth = False
			if dateString[0:10] != self.lastSprinklerStats[0:10]:
				newDay = True
				if now.weekday() == 0:
					newWeek = True
				if now.day == 1:
					newMonth = True
			
			self.lastSprinklerStats = dateString

			if newDay:
				for dev in indigo.devices.iter("props.isSprinklerDevice"):
					self.addToStatesUpdateDict(str(dev.id),"minutesRunYesterday",dev.states["minutesRunToday"])
					lastList = dev.states["minutesRunToday"].split(",")
					lastList = ["0" for ii in range(dev.zoneCount)]
					lastList = ",".join(lastList)
					self.addToStatesUpdateDict(str(dev.id),"minutesRunToday",lastList)

					if newWeek:
						self.addToStatesUpdateDict(str(dev.id),"minutesRunLastWeek",dev.states["minutesRunThisWeek"])
						lastList = dev.states["minutesRunThisWeek"].split(",")
						lastList = ["0" for ii in range(dev.zoneCount)]
						lastList = ",".join(lastList)
						self.addToStatesUpdateDict(str(dev.id),"minutesRunThisWeek",lastList)

					if newMonth:
						self.addToStatesUpdateDict(str(dev.id),"minutesRunLastMonth",dev.states["minutesRunThisMonth"])
						lastList = dev.states["minutesRunThisMonth"].split(",")
						lastList = ["0" for ii in range(dev.zoneCount)]
						lastList = ",".join(lastList)
						self.addToStatesUpdateDict(str(dev.id),"minutesRunThisMonth",lastList)

					self.executeUpdateStatesDict(onlyDevID=dev.id)



			for dev in indigo.devices.iter("props.isSprinklerDevice"):
				props			   = dev.pluginProps
				try:	activeZone = int(dev.states["activeZone"])
				except: activeZone = 0
				if activeZone == 0: 
					self.addToStatesUpdateDict(str(dev.id), "activeZoneMinutesLeft",	 0)
					self.addToStatesUpdateDict(str(dev.id), "activeZoneMinutesDuration", 0)
					self.addToStatesUpdateDict(str(dev.id), "allZonesMinutesLeft",		 0)
					self.addToStatesUpdateDict(str(dev.id), "allZonesMinutesDuration",	 0)

				else:
					if props["PumpControlOn"]: nValves = dev.zoneCount-1
					else: nValves	 = dev.zoneCount
					durations		 = dev.zoneScheduledDurations
					zoneMaxDurations = dev.zoneMaxDurations
					zoneStarted		 = dev.states["activeZoneStarted"] # show date time when started . long string 

					if len(zoneStarted) > 10:  # show date time when started . long string 
						secDone = (datetime.datetime.now() - datetime.datetime.strptime(zoneStarted, "%Y-%m-%d %H:%M:%S")).total_seconds()
						minutes	 = int(secDone/60)

						try:	allDur = int(dev.states["allZonesMinutesDuration"])
						except: allDur = 0
						if len(durations) == nValves:
							dur		= min(durations[activeZone-1], zoneMaxDurations[activeZone-1])
							allMinutes = minutes
							if activeZone <= len(durations) and activeZone > 1:
								for mm in durations[0:activeZone-1]:
									allMinutes += mm
						else :
							dur		   = int(dev.states["activeZoneMinutesDuration"])
							allMinutes = minutes

						timeLeft	=  int(max(0,(dur	 - minutes)+0.1) )
						timeLeftAll =  int(max(0,(allDur - allMinutes)+0.1) )


						self.addToStatesUpdateDict(str(dev.id), "activeZoneMinutesLeft",   timeLeft)
						self.addToStatesUpdateDict(str(dev.id), "allZonesMinutesLeft",	   timeLeftAll)

					else: # show date time when started .if short , not started
						self.addToStatesUpdateDict(str(dev.id), "activeZoneMinutesLeft",   0)
						self.addToStatesUpdateDict(str(dev.id), "allZonesMinutesLeft",	   0)


					for xx in ["minutesRunToday", "minutesRunThisWeek", "minutesRunThisMonth"]:
						lastList = dev.states[xx].split(",")
						if len(lastList) != dev.zoneCount:
							lastList = ["0" for ii in range(dev.zoneCount)]
						lastList[activeZone-1] = str( int(lastList[activeZone-1])+1 )
						if props["PumpControlOn"] :
							lastList[dev.zoneCount-1] = str( int(lastList[dev.zoneCount-1])+1 )
						lastList = ",".join(lastList)
						self.addToStatesUpdateDict(str(dev.id),xx,lastList)
						

				self.executeUpdateStatesDict(onlyDevID=str(dev.id))
		except	Exception, e:
			indigo.server.log( u"readConfig in Line '%s' has error='%s'" % (sys.exc_traceback.tb_lineno, e))

####------================------- sprinkler ------================-----------END


####-------------------------------------------------------------------------####
	def readConfig(self):  ## only once at startup
		try:

			self.readTcpipSocketStats()
			
			self.RPI = self.getParamsFromFile(self.userIndigoPluginDir+"RPIconf")
			if self.RPI =={}: 
				self.ML.myLog( text = self.userIndigoPluginDir + "RPIconf file does not exist or has bad data, will do a new setup ")


			self.sensorMessages = self.getParamsFromFile(self.userIndigoPluginDir+ "sensorMessages")

			for pi in range(_GlobalConst_numberOfiBeaconRPI):
				if unicode(pi) not in self.RPI:
					self.RPI[unicode(pi)] = copy.deepcopy(_GlobalConst_emptyRPI)
				for piProp in _GlobalConst_emptyRPI:
					if piProp not in self.RPI[unicode(pi)]:
						self.RPI[unicode(pi)][piProp] = copy.deepcopy(_GlobalConst_emptyRPI[piProp])


				delProp=[]
				for piProp in self.RPI[unicode(pi)]:
					if piProp not in _GlobalConst_emptyRPI:
						delProp.append(piProp)
				for piProp in delProp:
					del self.RPI[unicode(pi)][piProp]
				delSen={}
				for sensor in self.RPI[unicode(pi)][u"input"]:
					if sensor not in _GlobalConst_allowedSensors: delSen[sensor]=1
				for sensor in delSen :
					del self.RPI[unicode(pi)][u"input"][sensor]
					

			for pi in range(_GlobalConst_numberOfiBeaconRPI, _GlobalConst_numberOfRPI):
				if unicode(pi) not in self.RPI:
					self.RPI[unicode(pi)] = copy.deepcopy(_GlobalConst_emptyRPISENSOR)
				for piProp in _GlobalConst_emptyRPISENSOR:
					if piProp not in self.RPI[unicode(pi)]:
						self.RPI[unicode(pi)][piProp] = copy.deepcopy(_GlobalConst_emptyRPISENSOR[piProp])
				
				
				### cleanup empty devids in RPI [sensor]
				delProp=[]
				for piProp in self.RPI[unicode(pi)]:
					if piProp not in _GlobalConst_emptyRPISENSOR:
						delProp.append(piProp)
				for piProp in delProp:
					del self.RPI[unicode(pi)][piProp]
				
				for iii in ["input","output"]:
					delSens={}
					for sensor in self.RPI[unicode(pi)][iii]:

						delDev ={}
						for devId in self.RPI[unicode(pi)][iii][sensor]:
							try:	 indigo.devices[int(devId)]
							except:	 delDev[devId] = True
						for devId in delDev:
							del self.RPI[unicode(pi)][iii][sensor][devId]
							indigo.server.log("RPI cleanup "+ unicode(pi)+" del "+iii+" devId:"+ devId)

						if self.RPI[unicode(pi)][iii][sensor] =={}:
							delSens[sensor]=True
					
					for sensor in delSens:
						indigo.server.log("RPI cleanup "+ unicode(pi)+" deleting "+iii+"  "+ sensor)
						del self.RPI[unicode(pi)][iii][sensor]


			for pi in range(_GlobalConst_numberOfRPI):
				if self.RPI[unicode(pi)][u"piOnOff"] == "0": 
					self.upDateNotSuccessful[pi] == 0
					self.removeONErPiV(pi, u"piUpToDate", [u"updateAllFilesFTP"])


			self.beacons		   = self.getParamsFromFile(self.userIndigoPluginDir+ "beacons")

			for beacon in self.beacons:
				for nn in _GlobalConst_emptyBeacon:
					if nn not in self.beacons[beacon]:
						self.beacons[beacon][nn]=copy.deepcopy(_GlobalConst_emptyBeacon[nn])
						
				for pi in range(_GlobalConst_numberOfiBeaconRPI):
					if self.beacons[beacon][u"indigoId"] ==0: continue
					try:
						chList=[]
						dev = indigo.devices[self.beacons[beacon][u"indigoId"]]
						if dev.states[u"closestRPI"]	 == "": 
							chlist.append({u"key":"closestRPI", u"value":-1})
						if dev.states[u"closestRPIText"] != "Pi_"+str(dev.states[u"closestRPI"]): 
							chlist.append({u"key":"closestRPIText", u"value":"Pi_"+str(dev.states[u"closestRPI"])})
						lastUp= float(time.mktime(time.strptime(dev.states[u"Pi_"+unicode(pi)+"_Time"],_defaultDateStampFormat)))
						if self.beacons[beacon][u"receivedSignals"][pi][1] > lastUp: continue # time entry
						self.beacons[beacon][u"receivedSignals"][pi][0]= float(dev.states[u"Pi_"+str(pi)+"_Signal"])
						self.beacons[beacon][u"receivedSignals"][pi][1]= lastUp
						self.execUpdateStatesList(dev,chList)
					except:
						pass


			self.beaconsUUIDtoName	 = self.getParamsFromFile(self.userIndigoPluginDir+"beaconsUUIDtoName",	  oldName= self.userIndigoPluginDir+"UUIDtoName")
			self.beaconsUUIDtoIphone = self.getParamsFromFile(self.userIndigoPluginDir+"beaconsUUIDtoIphone",	  oldName= self.userIndigoPluginDir+"UUIDtoIphone")
			self.beaconsIgnoreUUID	 = self.getParamsFromFile(self.userIndigoPluginDir+"beaconsIgnoreUUID",	  oldName= self.userIndigoPluginDir+"beaconsIgnoreFamily")
			self.rejectedByPi		 = self.getParamsFromFile(self.userIndigoPluginDir+"rejected/rejectedByPi.json")
			self.version			 = self.getParamsFromFile(self.userIndigoPluginDir+"dataVersion", default=0)


			self.readCARS()
			
			
			self.ML.myLog( text = u" ..	 config read from files")
			self.fixConfig(checkOnly = ["all","rpi","beacon","CARS","sensors","output","force"],fromPGM="readconfig") 
			
		except	Exception, e:
			indigo.server.log( u"readConfig in Line '%s' has error='%s'" % (sys.exc_traceback.tb_lineno, e))
			exit(1)


####-------------------------------------------------------------------------####
	def getParamsFromFile(self,newName, oldName="", default ={}): # called from read config for various input files 
			out = default
			if os.path.isfile(newName):
				try:
					f = open(newName, u"r")
					out	 = json.loads(f.read())
					f.close()
					if oldName !="" and os.path.isfile(oldName):
						os.system("rm "+oldName)
				except	Exception, e:
					self.ML.myLog( text =  u"getParamsFromFile in Line '%s' has error='%s'" % (sys.exc_traceback.tb_lineno, e))
					out ={}
			else:
				out = default
			if oldName !="" and os.path.isfile(oldName):
				try:
					f = open(oldName, u"r")
					out	 = json.loads(f.read())
					f.close()
					os.system("rm "+oldName)
				except	Exception, e:
					self.ML.myLog( text =  u"getParamsFromFile in Line '%s' has error='%s'" % (sys.exc_traceback.tb_lineno, e))
					out = default
			return out

####-------------------------------------------------------------------------####
	def savebeaconPositionsFile(self):
		self.setImageParameters()
		try:
				f = open(self.userIndigoPluginDir + "plotPositions/positions.json", u"w")
				f.write(json.dumps(self.beaconPositionsData))
				f.close()
				if self.ML.decideMyLog(u"PlotPositions"): self.ML.myLog( text =	 u"savebeaconPositionsFile "+ unicode(self.beaconPositionsData[u"mac"])[0:100] )
		except	Exception, e:
			self.ML.myLog( text =  u"savebeaconPositionsFile in Line '%s' has error='%s'" % (sys.exc_traceback.tb_lineno, e))
		return

####-------------------------------------------------------------------------####
	def setImageParameters(self):
		self.beaconPositionsData[u"piDir"]			= self.userIndigoPluginDir+"plotPositions"
		self.beaconPositionsData[u"logLevel"]		= "debugPlotPositions" in self.debugLevel
		self.beaconPositionsData[u"logFile"]		= self.userIndigoPluginDir+"plotPositions/plotPositions.log"
		self.beaconPositionsData[u"distanceUnits"]	= self.distanceUnits

####-------------------------------------------------------------------------####
	def makeNewBeaconPositionPlots(self):
		try: 
			changed = False

			self.beaconPositionsData[u"mac"]={}
			for beacon in self.beacons:
					try:
						if self.beacons[beacon][u"showBeaconOnMap"] ==0: continue
						indigoId = self.beacons[beacon][u"indigoId"]
						if indigoId ==0 or indigoId ==u"":				 continue
						try:	dev = indigo.devices[indigoId]
						except: continue
						if self.beaconPositionsData[u"ShowExpiredBeacons"] == "0" and dev.states["status"] == u"expired": continue
						props = dev.pluginProps
						
						if u"showBeaconOnMap" not in props or props[u"showBeaconOnMap"] ==u"0":
							if beacon in self.beaconPositionsData[u"mac"]:
								del self.beaconPositionsData[u"mac"][beacon]
							changed = True
							
						elif "showBeaconOnMap"	in props and props[u"showBeaconOnMap"] in _GlobalConst_beaconPlotSymbols:
							if beacon not in self.beaconPositionsData[u"mac"]:
								changed = True
							try:	distanceToRPI = float(dev.states[unicode(dev.states[u"closestRPIText"])+"_Distance"])
							except: distanceToRPI = 0.5
							# State "Pi_8_Signal" of "b-radius-3"
							if dev.states["status"] == u"expired": useSymbol = "square45"
							else:								   useSymbol = props[u"showBeaconOnMap"]
							self.beaconPositionsData[u"mac"][beacon]={u"name":dev.name,
								u"position":			 [float(dev.states[u"PosX"]),float(dev.states[u"PosY"]),float(dev.states[u"PosZ"])],
								u"nickName":			 props[u"showBeaconNickName"],
								u"symbolType":			 useSymbol,
								u"symbolColor":			 props[u"showBeaconSymbolColor"],
								u"symbolAlpha":			 props[u"showBeaconSymbolAlpha"] ,
								u"distanceToRPI":		 distanceToRPI ,
								u"textColor":			 props[u"showBeaconTextColor"] ,
								u"status":				 dev.states[u"status"]					}
					except	Exception, e:
							self.ML.myLog( text =  u"makeNewBeaconPositionPlots in Line '%s' has error='%s'" % (sys.exc_traceback.tb_lineno, e))

			if self.beaconPositionsData[u"ShowRPIs"] in	 _GlobalConst_beaconPlotSymbols:
				for pi in range(_GlobalConst_numberOfiBeaconRPI):
					if self.RPI[unicode(pi)][u"piOnOff"]  == "0": continue
					if self.RPI[unicode(pi)][u"piDevId"]  == "0": continue
					if self.RPI[unicode(pi)][u"piDevId"]  == "":  continue
					try:
							dev = indigo.devices[self.RPI[unicode(pi)][u"piDevId"]]
							props = dev.pluginProps

							p = props[u"PosXYZ"].split(u",")
							pos =[0,0,0] 
							try:
								if len(pos)==3:	   pos = [float(p[0]),float(p[1]),float(p[2])]
							except:	 
												   pos = [0,0,0] 

							beacon = dev.address
							if self.beaconPositionsData[u"ShowRPIs"] ==u"square": nickN =  " R-"+unicode(pi)
							else:												  nickN =  "R-"+unicode(pi)
							self.beaconPositionsData[u"mac"][beacon]={u"name":"RPI-"+unicode(pi),
								u"position":			 pos,
								u"nickName":			 nickN,
								u"symbolType":			 self.beaconPositionsData[u"ShowRPIs"],
								u"symbolColor":			 u"#00F000",
								u"symbolAlpha":			 u"0.5" ,
								u"distanceToRPI":		 1.0 ,
								u"textColor":			 u"#008000" ,
								u"status":				 dev.states[u"status"]					}
					except:
							continue
	#						 self.ML.myLog( text =	u"makeNewBeaconPositionPlots in Line '%s' has error='%s'" % (sys.exc_traceback.tb_lineno, e))
	 
			if changed or self.beaconPositionsUpdated>0: 
					self.savebeaconPositionsFile()
					cmd = self.pythonPath + " '" + self.pathToPlugin + "makeBeaconPositionPlots.py' '"+self.userIndigoPluginDir+"plotPositions/' & "
					if self.ML.decideMyLog(u"PlotPositions"): 
						self.ML.myLog( text =  u"makeNewBeaconPositionPlots ..	beaconPositionsUpdated: "+ unicode(self.beaconPositionsUpdated))
						self.ML.myLog( text =  u"makeNewBeaconPositionPlots cmd:  "+ cmd)
					os.system(cmd)

		except	Exception, e:
			if unicode(e).find(u"timeout waiting") > -1:
				self.ML.myLog( text =  u"makeNewBeaconPositionPlots in Line '%s' has error='%s'" % (sys.exc_traceback.tb_lineno, e))
				self.ML.myLog( text =  u"communication to indigo is interrupted")
				return 
			if len(unicode(e)) > 5	and unicode(e).find(u"not found in database") ==-1:
				self.ML.myLog( text =  u"makeNewBeaconPositionPlots in Line '%s' has error='%s'" % (sys.exc_traceback.tb_lineno, e))

		self.beaconPositionsUpdated		= 0
		self.beaconPositionsLastCheck	= time.time()
		
		return 





####-------------------------------------------------------------------------####
	def calcPitoPidist(self):
		self.piToPiDistance =[[[-1,-1,-1,-1] for ii in range(_GlobalConst_numberOfiBeaconRPI)] for jj in range(_GlobalConst_numberOfiBeaconRPI)]
		self.piPosition = [[-1,-1,-1] for ii in range(_GlobalConst_numberOfiBeaconRPI)]
		for ii in range(_GlobalConst_numberOfiBeaconRPI):
			try:
				if self.RPI[unicode(ii)][u"piDevId"] ==0: continue
				if self.RPI[unicode(ii)][u"piDevId"] ==u"": continue
				devii = indigo.devices[self.RPI[unicode(ii)][u"piDevId"]]
				propsii= devii.pluginProps
				Pii = self.getPosXYZ(devii,propsii,ii)
				self.piPosition[ii]=Pii
				for jj in range(ii+1, _GlobalConst_numberOfiBeaconRPI):
					try:
						if self.RPI[unicode(jj)][u"piDevId"] == 0: continue
						if self.RPI[unicode(jj)][u"piDevId"] ==u"": continue
						devjj = indigo.devices[self.RPI[unicode(jj)][u"piDevId"]]
						propsjj= devjj.pluginProps
						Pjj = self.getPosXYZ(devjj,propsjj,jj)
						deltaDist =0
						for kk in range(2):
							delD = Pii[kk]-Pjj[kk] 
							deltaDist+= (delD)**2 
							self.piToPiDistance[ii][jj][kk] =  delD
							self.piToPiDistance[jj][ii][kk] = -delD
						deltaDist = math.sqrt(deltaDist)
						self.piToPiDistance[ii][jj][3] = deltaDist
						self.piToPiDistance[jj][ii][3] = deltaDist
					except	Exception, e:
						self.ML.myLog( text =  u"calcPitoPidist in Line '%s' has error='%s'" % (sys.exc_traceback.tb_lineno, e))
			except	Exception, e:
				self.ML.myLog( text =  u"calcPitoPidist in Line '%s' has error='%s'" % (sys.exc_traceback.tb_lineno, e))
		return True

####-------------------------------------------------------------------------####
	def getPosXYZ(self,dev,props,jj):
		try: 
			if u"PosXYZ" not in props:
				props[u"PosXYZ"] ="0,0,0"
				dev.replacePluginPropsOnServer(props)
				self.ML.myLog( text =  u"calcPitoPidist in Line '%s' has error='%s'" % (sys.exc_traceback.tb_lineno, e)+" fixing props, you might need to edit RPI#"+unicode(jj))
			Pjj = props[u"PosXYZ"].split(u",")

			if len(Pjj) != 3:
				props[u"PosXYZ"] ="0,0,0"
				dev.replacePluginPropsOnServer(props)

			Pjj = props[u"PosXYZ"].split(u",")
			return [float(Pjj[0]),float(Pjj[1]),float(Pjj[2])]

		except	Exception, e:
			self.ML.myLog( text =  u"calcPitoPidist in Line '%s' has error='%s'" % (sys.exc_traceback.tb_lineno, e)+" fixing props, you might need to edit RPI#"+unicode(jj))
			props[u"PosXYZ"] ="0,0,0"
			dev.replacePluginPropsOnServer(props)
		return [0,0,0]

####-------------------------------------------------------------------------####
	def fixConfig(self,checkOnly = ["all"],fromPGM=""):
		if  self.ML.decideMyLog(u"Logic"):  self.ML.myLog( text = u"fixConfig called from "+fromPGM +u"; with:"+unicode(checkOnly) )
		# dont do it too often
		if time.time() - self.lastFixConfig < 25: return
		self.lastFixConfig	= time.time()

		nowDD = datetime.datetime.now()
		dateString = nowDD.strftime(_defaultDateStampFormat)
		#self.ML.myLog( text =	"entering fixConfig checkOnly:"+unicode(checkOnly) +"  fromPGM:"+fromPGM)
		anyChange= False
		
		try:
			if "rpi" in checkOnly :
				for pi in range(_GlobalConst_numberOfRPI):
					if self.RPI[unicode(pi)][u"ipNumberPi"] != "":
						if self.RPI[unicode(pi)][u"ipNumberPiSendTo"] != self.RPI[unicode(pi)][u"ipNumberPi"]:
							self.RPI[unicode(pi)][u"ipNumberPiSendTo"] = copy.copy(self.RPI[unicode(pi)][u"ipNumberPi"])
							anyChange = True

					try:
						piDevId = int(self.RPI[unicode(pi)][u"piDevId"])
						if piDevId >0:
							dev= indigo.devices[piDevId]
							props = dev.pluginProps
							upd=False
							if nowDD.hour < 5 and u"addNewOneWireSensors" in props: # reset after midnight
								props[u"addNewOneWireSensors"] = "0"
								upd = True

							if u"ipNumberPi" not in props or ( len(self.RPI[unicode(pi)][u"ipNumberPi"])> 6 and self.RPI[unicode(pi)][u"ipNumberPi"] != props[u"ipNumberPi"]):
								upd=True
								props[u"ipNumberPi"] = self.RPI[unicode(pi)][u"ipNumberPi"]
							
							if u"userIdPi" not in props or self.RPI[unicode(pi)][u"userIdPi"] != props[u"userIdPi"]:
								upd=True
								props[u"userIdPi"]	 = self.RPI[unicode(pi)][u"userIdPi"]
							
							if u"passwordPi" not in props or self.RPI[unicode(pi)][u"passwordPi"] != props[u"passwordPi"]:
								upd=True
								props[u"passwordPi"] = self.RPI[unicode(pi)][u"passwordPi"]
							
							if u"sendToIndigoSecs" not in props and "sensorRefreshSecs" in props:
								upd=True
								props[u"sendToIndigoSecs"] = copy.deepcopy(props[u"sensorRefreshSecs"])

							if u"sendToIndigoSecs" not in props :
								upd=True
								props[u"sendToIndigoSecs"] = copy.deepcopy(_GlobalConst_emptyRPI[u"sensorRefreshSecs"])

							if u"sensorRefreshSecs" not in props :
								upd=True
								props[u"sensorRefreshSecs"] = copy.deepcopy(_GlobalConst_emptyRPI[u"sensorRefreshSecs"])

							if u"rssiOffset" not in props :
								upd=True
								props[u"rssiOffset"] = copy.deepcopy(_GlobalConst_emptyRPI[u"rssiOffset"])

							if dev.enabled:
								if self.RPI[unicode(pi)][u"piOnOff"] != "1":
									try:	del self.checkIPSendSocketOk[self.RPI[unicode(pi)][u"ipNumber"]]
									except: pass
								self.RPI[unicode(pi)][u"piOnOff"] = "1"
							else:
								self.RPI[unicode(pi)][u"piOnOff"] = "0"
							
							if upd:
								dev.replacePluginPropsOnServer(props)
								dev= indigo.devices[piDevId]
								anyChange = True
							
					except	Exception, e:
						if unicode(e).find(u"timeout waiting") > -1:
							self.ML.myLog( text =  u"fixConfig in Line '%s' has error='%s'" % (sys.exc_traceback.tb_lineno, e))
							self.ML.myLog( text =  u"communication to indigo is interrupted")
							return
						self.ML.myLog( text =  u"fixConfig in Line '%s' has error='%s'" % (sys.exc_traceback.tb_lineno, e))
						self.ML.myLog( text =  u"error normal if rpi has been deleted, removing from list: setting piDevId=0")
						self.RPI[unicode(pi)][u"piDevId"] =0
						anyChange = True

					if self.RPI[unicode(pi)][u"piOnOff"] != "0":
						if len(self.RPI[unicode(pi)][u"ipNumberPi"]) < 8:
							self.RPI[unicode(pi)][u"piOnOff"] = "0"
							anyChange = True
							continue
		except	Exception, e:
			self.ML.myLog( text =  u"fixConfig in Line '%s' has error='%s'" % (sys.exc_traceback.tb_lineno, e))
		#self.ML.myLog( text =	u"fixConfig time elapsed point A  "+str(time.time()- self.lastFixConfig) +"     anyChange: "+ str(anyChange))

		try:
			if "all" in checkOnly:
				delDEV = []
				for dev in indigo.devices.iter("props.isCARDevice,props.isBeaconDevice,props.isRPIDevice"):
					if dev.deviceTypeId==u"car": 
						props=dev.pluginProps
						newP = self.setupCARS(dev.id,props,mode="init")
						if newP[u"description"] != dev.description:
							if self.ML.decideMyLog(u"CAR"): self.ML.myLog( text =  u"replacing car props"+ dev.name+"  "+ newP[u"description"]+"  "+ dev.description)
							dev.description =  newP[u"description"] 
							dev.replaceOnServer()
							anyChange = True
						continue
					
					if dev.deviceTypeId.find(u"rPI") >-1: 
						props= dev.pluginProps
						try:	pi = int(dev.states[u"note"].split(u"-")[1])
						except: continue
						try:	beacon = props[u"address"]
						except: beacon =""
				
						if u"ipNumberPi" in props and len(props[u"ipNumberPi"])> 6 and self.RPI[unicode(pi)][u"ipNumberPi"] != props[u"ipNumberPi"]:
							self.ML.myLog( text =  u"dev :" + dev.name + " fixing ipNumber in RPI")
							self.RPI[unicode(pi)][u"ipNumberPi"] = props[u"ipNumberPi"]
							anyChange = True

						if dev.id != self.RPI[unicode(pi)][u"piDevId"]:
							self.ML.myLog( text =  u"dev :" + dev.name + " fixing piDevId in RPI")
							self.RPI[unicode(pi)][u"piDevId"]	 = dev.id
							anyChange = True

						if len(beacon)> 6 and self.RPI[unicode(pi)][u"piMAC"] != beacon:
							self.ML.myLog( text =  u"dev :" + dev.name + " fixing piMAC in RPI")
							self.RPI[unicode(pi)][u"piMAC"]	   = beacon
							anyChange = True

						if u"userIdPi" in props and	 self.RPI[unicode(pi)][u"userIdPi"] != props[u"userIdPi"]:
							self.ML.myLog( text =  u"dev :" + dev.name + " fixing userIdPi in RPI")
							self.RPI[unicode(pi)][u"userIdPi"]	  = self.RPI[unicode(pi)][u"userIdPi"]
							anyChange = True

						if u"passwordPi" in props and  self.RPI[unicode(pi)][u"passwordPi"] != props[u"passwordPi"]:
							self.ML.myLog( text =  u"dev :" + dev.name + " fixing passwordPi in RPI")
							self.RPI[unicode(pi)][u"passwordPi"]	= self.RPI[unicode(pi)][u"passwordPi"]
							anyChange = True

					if dev.deviceTypeId.find(u"beacon") >-1: 
						props		= dev.pluginProps
						updateProps = False
						for propEmpty in _GlobalConst_emptyBeaconProps:
							if propEmpty not in props:
								props[propEmpty] = _GlobalConst_emptyBeaconProps[propEmpty]
								updateProps=True
						if updateProps:
							dev.replacePluginPropsOnServer(props)
							anyChange = True
							
					if "force" in checkOnly:	
						if self.fixDevProps(dev) == -1:
							delDEV.append(dev)
							anyChange = True
					###self.ML.myLog( text =  u"dev :" +unicode(dev))

				for dev in delDEV:
					self.ML.myLog( text =  u"fixConfig dev :" + dev.name + " has no addressfield")
					# indigo.device.delete(dev)
		except	Exception, e:
			self.ML.myLog( text =  u"fixConfig in Line '%s' has error='%s'" % (sys.exc_traceback.tb_lineno, e))
		#self.ML.myLog( text =	u"fixConfig time elapsed point B  "+str(time.time()- self.lastFixConfig)+"     anyChange: "+ str(anyChange) )
		
		try:
			if "all" in checkOnly or "beacon" in checkOnly:
				# remove junk:
				remove = []
				for beacon in self.beacons:
					if len(beacon) != len(u"0C:F3:EE:00:83:40"):  # !=17 length, remove junk
						remove.append(beacon)
						anyChange = True
						#self.ML.myLog( text =	u"fixConfig anyChange: A") 
					elif beacon == "":
						remove.append(beacon)
						anyChange = True
						#self.ML.myLog( text =	u"fixConfig anyChange: B") 
					else:
						
						for nn in _GlobalConst_emptyBeacon:
							if nn not in self.beacons[beacon]:
								self.beacons[beacon][nn] = copy.deepcopy(_GlobalConst_emptyBeacon[nn])
								anyChange = True
								self.ML.myLog( text =	u"fixConfig anyChange: C") 
						delnn=[]
						for nn in self.beacons[beacon]:
							if nn not in _GlobalConst_emptyBeacon:
								delnn.append(nn)
						for nn in delnn:
							del self.beacons[beacon][nn]
							anyChange = True
						try:
							float(self.beacons[beacon][u"created"])
							self.beacons[beacon][u"created"] = dateString
						except:
							pass


						if self.beacons[beacon][u"typeOfBeacon"] == u"rPi":
							  self.beacons[beacon][u"typeOfBeacon"] = u"rPI"

						if self.beacons[beacon][u"indigoId"] != 0:	# sync with indigo
							try:
								dev = indigo.devices[self.beacons[beacon][u"indigoId"]]
								props = dev.pluginProps
								if	 dev.deviceTypeId != u"beacon" and	(dev.deviceTypeId.lower()) != u"rpi":
									try:
										dev = indigo.devices[self.beacons[beacon][u"indigoId"]]
										self.ML.myLog( text =  u"fixConfig fixing: beacon should not in beacon list: " +beacon+"  "+ dev.name+"	 "+dev.deviceTypeId )
									except:
										self.ML.myLog( text =  u"fixConfig fixing: beacon should not in beacon list: " +beacon+"  no name / device"+"  "+dev.deviceTypeId )
									remove.append(beacon)
									anyChange = True
									self.ML.myLog( text =	u"fixConfig anyChange: F") 
									continue



								beaconDEV = props[u"address"]
								if beaconDEV != beacon:
									self.beacons[beacon][u"indigoId"] = 0
									self.ML.myLog( text =  u"fixing: "+dev.name+u" beaconDEV:"+beaconDEV+u"  beacon:"+beacon+u" beacon wrong, using current beacon-mac")
									anyChange = True

								self.beacons[beacon][u"status"]					 = dev.states[u"status"]
								self.beacons[beacon][u"note"]					 = dev.states[u"note"]
								self.beacons[beacon][u"signalDelta"]			 = props[u"signalDelta"]
								self.beacons[beacon][u"minSignalCutoff"]		 = props[u"minSignalCutoff"]
								self.beacons[beacon][u"typeOfBeacon"]			 = props[u"typeOfBeacon"]
								self.beacons[beacon][u"beaconTxPower"]			 = props[u"beaconTxPower"]
								self.beacons[beacon][u"created"]				 = dev.states[u"created"]
								try:	
									self.beacons[beacon][u"showBeaconOnMap"]	 = props[u"showBeaconOnMap"] 
								except: pass
								dev.updateStateOnServer(u"TxPowerSet",int(props[u"beaconTxPower"]))
								if u"fastDown" in props: # not for RPI
									self.beacons[beacon][u"fastDown"]			 = props[u"fastDown"]
								else:
									self.ML.myLog( text =  dev.name+" has no fastDown")
									self.beacons[beacon][u"fastDown"]			 = "0"
								if u"fastDownMinSignal" in props: # not for RPI
									self.beacons[beacon][u"fastDownMinSignal"]			  = props[u"fastDownMinSignal"]
								else:
									self.beacons[beacon][u"fastDownMinSignal"]			  = -999
								
								if u"updateSignalValuesSeconds" in props: # not for RPIindigoIdindigoIdindigoIdindigoIdindigoId
									self.beacons[beacon][u"updateSignalValuesSeconds"] = float(props[u"updateSignalValuesSeconds"])
								else:
									self.beacons[beacon][u"updateSignalValuesSeconds"] = 300
								#if "batteryLevel" in props: # not for RPI
								#	 self.beacons[beacon][u"batteryLevel"] = props[u"batteryLevel"]
								#else:
								#	 self.beacons[beacon][u"batteryLevel"] = "100"
							except	Exception, e:
								anyChange = True
								self.ML.myLog( text = u"fixConfig anyChange: G") 
								if unicode(e).find(u"timeout waiting") > -1:
									self.ML.myLog( text =  u"fixConfig in Line '%s' has error='%s'" % (sys.exc_traceback.tb_lineno, e))
									self.ML.myLog( text =  u"communication to indigo is interrupted")
									return 
								elif unicode(e).find(u"not found in database") >-1:
									self.beacons[beacon][u"indigoId"] =0
									continue
								else:
									self.ML.myLog( text =  u"fixConfig in Line '%s' has error='%s'" % (sys.exc_traceback.tb_lineno, e))
									try:
										self.ML.myLog( text =  u"device:" +dev.name+"  "+unicode(dev.states)+"\n  beacon:" +unicode(self.beacons[beacon]) )
									except	Exception, e:
										self.ML.myLog( text =  u"fixConfig in Line '%s' has error='%s'" % (sys.exc_traceback.tb_lineno, e))
									return 
							
								
						else:
							self.beacons[beacon][u"updateSignalValuesSeconds"] = _GlobalConst_emptyBeacon[u"updateSignalValuesSeconds"]
				for beacon in remove:
					self.ML.myLog( text =  u"fixConfig:  deleting beacon:"+beacon+" " +unicode(self.beacons[beacon]))
					del self.beacons[beacon]

		except	Exception, e:
			self.ML.myLog( text =  u"fixConfig in Line '%s' has error='%s'" % (sys.exc_traceback.tb_lineno, e))
		#self.ML.myLog( text = u"fixConfig time elapsed point C  "+str(time.time()- self.lastFixConfig) +"     anyChange: "+ str(anyChange))

		try:
			if "rpi" in checkOnly:
				for beacon in self.beacons:
					if self.beacons[beacon][u"typeOfBeacon"].lower() == "rpi":
						if self.beacons[beacon][u"note"].find(u"Pi-") == 0:
							try:
								pi = int(self.beacons[beacon][u"note"][3:])
							except:
								continue
							if self.beacons[beacon][u"indigoId"] != 0 :# and self.beacons[beacon][u"ignore"] ==0:
								try:
									devId = indigo.devices[self.beacons[beacon][u"indigoId"]].id
									if self.RPI[unicode(pi)][u"piDevId"] != devId:
										self.RPI[unicode(pi)][u"piDevId"] = devId
										anyChange = True
										#self.ML.myLog( text =	u"fixConfig anychange: D-1")
								except	Exception, e:
									if unicode(e).find(u"timeout waiting") > -1:
										self.ML.myLog( text =  u"fixConfig in Line '%s' has error='%s'" % (sys.exc_traceback.tb_lineno, e))
										self.ML.myLog( text =  u"communication to indigo is interrupted")
										return
									elif unicode(e).find(u"not found in database") >-1:
										self.beacons[beacon][u"indigoId"] = 0
										anyChange = True
										#self.ML.myLog( text =	u"fixConfig anychange: D-2  beacon, pi, devid "+ str(beacon) +"  "+ str(pi) +"  "+ str(devId) )
										continue
									else:
										self.ML.myLog( text =  u"fixConfig in Line '%s' has error='%s'" % (sys.exc_traceback.tb_lineno, e))
										self.ML.myLog( text =  u"unknown error")
										return

			if "all" in checkOnly or "beacon" in checkOnly :
				for beacon in self.beacons:
					if self.beacons[beacon][u"indigoId"] == 0:	# remove iphones if the devices was deleted
						if beacon in self.beaconsUUIDtoIphone:
							del self.beaconsUUIDtoIphone[beacon]
							anyChange = True
							#self.ML.myLog( text =	u"fixConfig anychange: D-3  beacon,  "+ str(beacon) )
		except	Exception, e:
			self.ML.myLog( text =  u"fixConfig in Line '%s' has error='%s'" % (sys.exc_traceback.tb_lineno, e))
		#self.ML.myLog( text =	u"fixConfig time elapsed point D  "+str(time.time()- self.lastFixConfig) +"     anyChange: "+ str(anyChange))


		if "rpi" in checkOnly:
			self.calcPitoPidist()

		
		#self.ML.myLog( text =	u"fixConfig leaving after 4	 %4.2f secs"%(time.time()-self.lastFixConfig) )
		#self.ML.myLog( text =	u"fixConfig time elapsed point E  "+str(time.time()- self.lastFixConfig) +"     anyChange: "+ str(anyChange))

		
		if "all" in checkOnly:
			if self.syncSensors(): anyChange = True

		#self.ML.myLog( text =	u"fixConfig time elapsed point F  "+str(time.time()- self.lastFixConfig) +"     anyChange: "+ str(anyChange) )

		if anyChange or (time.time() - self.lastSaveConfig) > 100:
			self.lastSaveConfig = time.time() 
			self.saveConfig()
		#self.ML.myLog( text =	u"fixConfig time elapsed  END:    "+str(time.time()- self.lastFixConfig)+"     anyChange: "+ str(anyChange) )
		#indigo.server.log("beacon: 5C:F3:70:77:FB:6C "+ unicode(self.beacons["5C:F3:70:77:FB:6C"]))
		#indigo.server.log("beacon: B8:27:EB:9F:FE:6D "+ unicode(self.beacons["B8:27:EB:9F:FE:6D"]))
		return


####-------------------------------------------------------------------------####
	def checkSensorMessages(self, devId,item="lastMessage", default=0):
		try:
			devIds = unicode(devId)
			if devIds == "": return 0
			if devIds not in self.sensorMessages:
				self.sensorMessages[devIds] = {}
				self.sensorMessages[devIds][item] = default
				return 0
			else:
				if item in self.sensorMessages[devIds]:
					ret = self.sensorMessages[devIds][item]
					self.sensorMessages[devIds][item] = default
					return ret
				else:
					self.sensorMessages[devIds][item] = default
				return 0
		except	Exception, e:
			self.ML.myLog( text =  u"checkSensorMessages in Line '%s' has error='%s'" % (sys.exc_traceback.tb_lineno, e))
		return 1


####-------------------------------------------------------------------------####
	def saveSensorMessages(self,devId="",item="", value=0):
		try:
			if devId != "":
				self.checkSensorMessages(devId, item="lastMessage", default=value)
			else:
				self.writeJson(self.sensorMessages,fName=self.userIndigoPluginDir + u"sensorMessages")
			return
		except	Exception, e:
			self.ML.myLog( text =  u"saveSensorMessages in Line '%s' has error='%s'" % (sys.exc_traceback.tb_lineno, e))


####-------------------------------------------------------------------------####
	def writeJson(self,data, fName="", format=False ):
		try:
			
			if format:
				out = json.dumps(data, sort_keys=True, indent=2)
			else:
				out = json.dumps(data)

			if fName !="":
				f=open(fName,u"w")
				f.write(out)
				f.close()
			return out
			
		except	Exception, e:
			self.ML.myLog( text =  u"writeJson "+fname+" in Line '%s' has error='%s'" % (sys.exc_traceback.tb_lineno, e))
		return ""	 

####-------------------------------------------------------------------------####
	def saveConfig(self):
		self.writeJson(self.RPI, fName=self.userIndigoPluginDir + u"RPIconf", format=self.RPIFileSort)

		self.saveCARS()

		self.writeJson(self.beacons, fName=self.userIndigoPluginDir + "beacons", format=self.beaconsFileSort)

		self.makeBeacons_parameterFile()

		self.writeJson( self.beaconsUUIDtoName, fName=self.userIndigoPluginDir + u"beaconsUUIDtoName")

		self.writeJson( self.beaconsIgnoreUUID, fName=self.userIndigoPluginDir + u"beaconsIgnoreUUID")

		self.writeJson(self.beaconsUUIDtoIphone,fName=self.userIndigoPluginDir + u"beaconsUUIDtoIphone")


####-------------------------------------------------------------------------####
	def fixDevProps(self, dev):
		dateString = datetime.datetime.now().strftime(_defaultDateStampFormat)
		updateProps = False
		props = dev.pluginProps

		if u"description" in props:
			if dev.description != props[u"description"] and props[u"description"] !="":
				dev.description = props[u"description"]
				props[u"description"] =""
				dev.replaceOnServer()
				updateProps = True

		if dev.deviceTypeId == u"rPI-Sensor":
			if len(unicode(dev.address)) < 2 or unicode(dev.address) == "-None-" or dev.address is None:
				notes =	 dev.description.split(u"-")
				if notes[0].lower() == u"rpi" and len(notes)>2:
					updateProps	 = True
					props[u"address"] = u"Pi-"+notes[1]
			if len(dev.states[u"created"]) < 5: 
				dev.updateStateOnServer(u"created", dateString )



		if dev.deviceTypeId not in [u"rPI", u"beacon"]: 
			if updateProps:
				dev.replacePluginPropsOnServer(props)
			return 0

		if dev.deviceTypeId == "beacon":
			for prop in _GlobalConst_emptyBeaconProps:
				if prop not in props:
					updateProps = True
					props[prop] = _GlobalConst_emptyBeaconProps[prop]
				if prop.find(u"memberOf") > -1:
					if isinstance(props[prop],int):
						updateProps = True
						if props[prop] == 1:
							props[prop] = True
						else:
							props[prop] = False
						
 


		if dev.deviceTypeId == "rPI":
			for prop in _GlobalConst_emptyrPiProps:
				if prop not in props:
					updateProps = True
					props[prop] = _GlobalConst_emptyrPiProps[prop]
				if prop.find(u"memberOf") > -1:
					if isinstance(props[prop],int):
						if props[prop] == 1:
							props[prop] = True
						else:
							props[prop] = False
							
			if dev.description.find(u"rPI-") > -1:
				if dev.states[u"note"].find(u"Pi-") > -1:
					pi= dev.states[u"note"].split(u"-")[1]
					if dev.description != "rPI-"+pi+"-"+self.RPI[unicode(pi)][u"ipNumberPi"]:
						updateProps = True
						dev.description = "rPI-"+pi+"-"+self.RPI[unicode(pi)][u"ipNumberPi"]
					self.RPI[unicode(pi)][u"piDevId"] =dev.id
		if updateProps:
			updateProps= False
			#dev.replaceOnServer()
			dev.replacePluginPropsOnServer(props)
			props=dev.pluginProps

		if u"lastStatusChange" in dev.states and len(dev.states[u"lastStatusChange"]) < 5:
			#self.ML.myLog( text =	u"filling empty state lastStatusChange	of dev:"+ dev.name+"   with current date: "+dd)
			dev.updateStateOnServer(u"lastStatusChange",dateString)


		# only rPi and iBeacon from here on
		if u"address" not in props:
			self.ML.myLog( errorType = u"smallErr", text =u"dev :" + dev.name + " has no address field, please do NOT manually create beacon devices")
			self.ML.myLog( errorType = u"smallErr", text =u"fixDevProps " + dev.name + " props" + unicode(props))
			indigo.device.delete(dev)
			return -1

	   
		try:
			beacon = props[u"address"]
			if u"beaconTxPower" not in props:
				props[u"beaconTxPower"] = _GlobalConst_emptyBeacon[u"beaconTxPower"]
				updateProps = True
			if u"typeOfBeacon" not in props:
				props[u"typeOfBeacon"] = _GlobalConst_emptyBeacon[u"typeOfBeacon"]
				updateProps = True
			if u"typeOfBeacon" not in props:
				if dev.deviceTypeId ==u"beacon":
					props[u"typeOfBeacon"] = "other"
				if dev.deviceTypeId == "rPI" :
				  props[u"typeOfBeacon"] = "rPI"

			if u"updateSignalValuesSeconds" not in props:
				updateProps = True
				if (dev.deviceTypeId.lower()) == "rpi" :
					props[u"updateSignalValuesSeconds"] = 300
				else:
					props[u"updateSignalValuesSeconds"] = 0
			if u"signalDelta" not in props:
				updateProps = True
				props[u"signalDelta"] = 999
			if u"minSignalCutoff" not in props:
				updateProps = True
				props[u"minSignalCutoff"] = 999
			if u"fastDown" not in props:
				updateProps = True
				props[u"fastDown"] = "0"

			try:
				created = dev.states[u"created"]
			except:
				created = ""
			if created == "":
				updateProps = True
				self.addToStatesUpdateDict(unicode(dev.id),"created", dateString,dev=dev)
			if u"expirationTime" not in props:
				updateProps = True
				props[u"expirationTime"] = 90.

			if updateProps:
				dev.replacePluginPropsOnServer(props)
				if self.ML.decideMyLog(u"Logic"): self.ML.myLog( text =	 u"updating props for " + dev.name + " in fix props")

			if dev.deviceTypeId == "beacon" :
				noteState = "beacon-" + props[u"typeOfBeacon"] 
				if dev.states[u"note"] != noteState:
					self.addToStatesUpdateDict(unicode(dev.id),"note",noteState,dev=dev)
			else:  
				noteState = dev.states[u"note"]		 


			if beacon not in self.beacons:
				self.ML.myLog( text =  u"fixDevProps: adding beacon from devices to self.beacons: "+beacon+"  dev:"+dev.name)
				self.beacons[beacon] = copy.deepcopy(_GlobalConst_emptyBeacon)
			self.beacons[beacon][u"created"]		  = dev.states[u"created"]
			self.beacons[beacon][u"indigoId"]		  = dev.id
			self.beacons[beacon][u"status"]			  = dev.states[u"status"]
			if dev.deviceTypeId == "beacon" :
				self.beacons[beacon][u"typeOfBeacon"] = "other"
			else:
				self.beacons[beacon][u"typeOfBeacon"] = "rPI"
			self.beacons[beacon][u"note"]			  = noteState
			self.beacons[beacon][u"typeOfBeacon"]	  = props[u"typeOfBeacon"]
			self.beacons[beacon][u"beaconTxPower"]	  = int(props[u"beaconTxPower"])
			self.beacons[beacon][u"signalDelta"]	  = int(props[u"signalDelta"])
			self.beacons[beacon][u"minSignalCutoff"]  = int(props[u"minSignalCutoff"])
			self.beacons[beacon][u"expirationTime"]	  = float(props[u"expirationTime"])
			self.beacons[beacon][u"fastDown"]		  = float(props[u"fastDown"])
			try:
				self.beacons[beacon][u"batteryLevel"] = dev.states[u"batteryLevel"]
			except:
				self.beacons[beacon][u"batteryLevel"] = ""
			self.beacons[beacon][u"updateSignalValuesSeconds"] = float(props[u"updateSignalValuesSeconds"])

		except	Exception, e:
			self.ML.myLog( text =  u"fixDevProps in Line '%s' has error='%s'" % (sys.exc_traceback.tb_lineno, e))

		return 0



	

####-------------------------------------------------------------------------####
	def deviceStartComm(self, dev):
		try:
			if self.pluginState == "init":
			
				doSensorValueAnalog =["Wire18B20","DHTxx","DHT11","i2cTMP102","i2cMCP9808","i2cLM35A","i2cT5403",
				"i2cMS5803","i2cBMPxx","tmp006","i2cSHT21""i2cAM2320","i2cBMExx","bme680","si7021",
				"pmairquality",
				"BLEsensor","sgp30",
				"mhz-I2C","mhz-SERIAL",
				"ccs811","rainSensorRG11","as3935",
				"ina3221", "ina219",
				"i2cADC121",
				"i2cPCF8591-1", "i2cPCF8591"
				"i2cADS1x15-1", "i2cADS1x15"
				"spiMCP3008-1", "spiMCP3008",
				"i2cTCS34725", "as726x", "i2cOPT3001", "i2cVEML7700", "i2cVEML6030", "i2cVEML6040", "i2cVEML6070", "i2cVEML6075", "i2cTSL2561", 
				"mlx90614", "amg88xx", 
				"vl503l0xDistance", "vcnl4010Distance", "vl6180xDistance", "apds9960", "ultrasoundDistance",
				"INPUTpulse"]
				
				doSensorValueOnOff =["INPUTgpio-1","INPUTgpio-4","INPUTgpio-8","INPUTgpio-26",
				"INPUTtouch-1","INPUTtouch-4","INPUTtouch-12","INPUTtouch-16",
				"rPI","rPI-Sensor","beacon","BLEconnect"]
				
				dev.stateListOrDisplayStateIdChanged()	# update  from device.xml info if changed
				if self.version < 32.50:
					indigo.server.log(" checking for deviceType upgrades: "+ dev.name)
					if dev.deviceTypeId in doSensorValueAnalog:
						props = dev.pluginProps
						if "SupportsSensorValue" not in props:
							indigo.server.log(" processing: "+ dev.name )
							dev = indigo.device.changeDeviceTypeId(dev, dev.deviceTypeId)
							dev.replaceOnServer()
							dev = indigo.devices[dev.id]
							props = dev.pluginProps
							props["SupportsSensorValue"] 		= True
							props["SupportsOnState"] 			= False
							props["AllowSensorValueChange"] 	= False
							props["AllowOnStateChange"] 		= False
							props["SupportsStatusRequest"] 		= False
							dev.replacePluginPropsOnServer(props)
							indigo.server.log("SupportsSensorValue  after replacePluginPropsOnServer")

					if dev.deviceTypeId in doSensorValueOnOff:
						props = dev.pluginProps
						if "SupportsOnState" not in props:
							indigo.server.log(" processing: "+ dev.name )
							dev = indigo.device.changeDeviceTypeId(dev, dev.deviceTypeId)
							dev.replaceOnServer()
							dev = indigo.devices[dev.id]
							props = dev.pluginProps
							props["SupportsSensorValue"] 		= False
							props["SupportsOnState"] 			= True
							props["AllowSensorValueChange"] 	= False
							props["AllowOnStateChange"] 		= False
							props["SupportsStatusRequest"] 		= False
							dev.replacePluginPropsOnServer(props)
							if dev.deviceTypeId in ["rPI","rPI-Sensor","beacon","BLEconnect"]:
								dev= indigo.devices[dev.id]
								dev.updateStateOnServer("onOffState",(dev.states["status"].lower()).find("up")==0, uiValue=dev.states["displayStatus"] )
								if (dev.states["status"].lower()) in ["up","on"]:
									dev.updateStateImageOnServer(indigo.kStateImageSel.SensorOn)
								elif (dev.states["status"].lower()) in ["down","off"]:
									dev.updateStateImageOnServer(indigo.kStateImageSel.SensorOff)
								else:
									dev.updateStateImageOnServer(indigo.kStateImageSel.SensorTripped)
								dev.replaceOnServer()

							indigo.server.log("SupportsOnState after replacePluginPropsOnServer")



				props= dev.pluginProps
				if u"piServerNumber" in props:
					piN = props[u"piServerNumber"]	  
					self.updateNeeded = "enable-"+unicode(piN)
				self.statusChanged=2

			if dev.deviceTypeId == "sprinkler":
				self.sprinklerDeviceActive = True



				
		except	Exception, e:
			self.ML.myLog( text =  u"deviceStartComm in Line '%s' has error='%s'" % (sys.exc_traceback.tb_lineno, e))

####-------------------------------------------------------------------------####
	def deviceDeleted(self, dev):
		props= dev.pluginProps

		if u"address" in props: 
				beacon = props[u"address"]
				if beacon in self.beacons:
					if u"indigoId" in self.beacons[beacon] and	self.beacons[beacon][u"indigoId"] == dev.id:
						self.ML.myLog( text =  u"-setting beacon device in internal tables to 0:  " + dev.name+"  "+unicode(dev.id)+" enabled:"+ unicode(dev.enabled)+ "  pluginState:"+ self.pluginState)
						self.beacons[beacon][u"indigoId"] = 0
						self.beacons[beacon][u"ignore"]	  = 1
						#self.ML.myLog( text =	u"re-starting device:  " + dev.name+"  "+unicode(dev.id)+" enabled:"+ unicode(dev.enabled)+ "  pluginState:"+ self.pluginState)
						#self.ML.myLog( text =	unicode(dev))
		self.deviceStopComm(dev)
		return
		
####-------------------------------------------------------------------------####
	def deviceStopComm(self, dev):
		try:
			props= dev.pluginProps
			if self.pluginState != "stop":

				if self.freezeAddRemove : self.sleep(0.2)

				if u"piServerNumber" in props:
					piN = props[u"piServerNumber"]	  
					self.updateNeeded = "disable-"+unicode(piN)

				self.statusChanged=2
 
		except	Exception, e:
			self.ML.myLog( text =  u"deviceStopComm in Line '%s' has error='%s'" % (sys.exc_traceback.tb_lineno, e))


####-------------------------------------------------------------------------####
	#def didDeviceCommPropertyChange(self, origDev, newDev):
	#	 #if origDev.pluginProps['xxx'] != newDev.pluginProps['address']:
	#	 #	  return True
	#	 return False
	###########################		INIT	## END	 ########################




	###########################		DEVICE	#################################
####-------------------------------------------------------------------------####
	def getDeviceConfigUiValues(self, pluginProps, typeId="", devId=0):
		if typeId in [u"beacon", u"rPI"]:
			try:
				theDictList =  super(Plugin, self).getDeviceConfigUiValues(pluginProps, typeId, devId)
				for nn in range(len(theDictList)):
					item = theDictList[nn]
					if u"address" in item:
							theDictList[nn][u"newMACNumber"] = copy.deepcopy(theDictList[nn][u"address"])
							return theDictList[nn]
			except	Exception, e:
				self.ML.myLog( text = u"getDeviceConfigUiValues in Line '%s' has error='%s'" % (sys.exc_traceback.tb_lineno, e))

		return super(Plugin, self).getDeviceConfigUiValues(pluginProps, typeId, devId)



####-------------------------------------------------------------------------####
	def validateDeviceConfigUi(self, valuesDict, typeId, devId):

		error =""
		errorDict = valuesDict
		valuesDict[u"MSG"] = "OK"
		update = 0
		beacon = "xx"
		try:
			dev = indigo.devices[devId]
			props = dev.pluginProps
			##self.ML.myLog( text = " sensor type: "+typeId )

			if typeId in [u"beacon", u"rPI"]:
				try:
					beacon = props[u"address"]
				except: pass
				

			if typeId == "car":
				valuesDict = self.setupCARS(devId,valuesDict,mode="validate")
				return (True, valuesDict)

				
			if typeId == "BLEconnect":
					if len(valuesDict[u"macAddress"]) == len(u"01:02:03:04:05:06"):
						dev.updateStateOnServer(u"TxPowerSet",int(valuesDict[u"beaconTxPower"]))
						valuesDict[u"macAddress"] = valuesDict[u"macAddress"].upper()
					else:
						valuesDict[u"MSG"] = "bad Mac Number"
						return (False,valuesDict)
				
			if typeId == "sprinkler":
				#valuesDict[u"description"] = "Pi-"+valuesDict[u"piServerNumber"]
				valuesDict[u"address"] = "Pi-"+valuesDict[u"piServerNumber"]
				#self.updateNeeded += " fixConfig "
				return (True, valuesDict)


			if typeId == "beacon":
				newMAC = valuesDict[u"newMACNumber"].upper()
				valuesDict[u"newMACNumber"] = newMAC
				if len(newMAC) == len(u"01:02:03:04:05:06"):
						if beacon != newMAC:
							self.ML.myLog( text = u"replacing beacon mac "+beacon+u" with "+newMAC)
							if beacon !="xx" and beacon in self.beacons:
								self.ML.myLog( text = u"replacing existing beacon")
								self.beacons[newMAC]	= copy.deepcopy(self.beacons[beacon])
								self.beacons[beacon][u"indigoId"] = 0
								self.newADDRESS[devId]	= newMAC
								props[u"address"]= self.newADDRESS[devId]
								dev.replacePluginPropsOnServer(props)
								dev = indigo.devices[devId]
								props = dev.pluginProps
							else:
								self.ML.myLog( text = u"creating a new beacon")
								self.beacons[newMAC]	= copy.deepcopy(_GlobalConst_emptyBeacon)
								self.newADDRESS[devId]	= newMAC
								props[u"address"]		= newMAC
								dev.replacePluginPropsOnServer(props)
								dev = indigo.devices[devId]
								props = dev.pluginProps
							beacon = newMAC
				else:
					valuesDict[u"MSG"] = "bad Mac Number"
					valuesDict[u"newMACNumber"] = beacon
					return (False, valuesDict)
				
				if len(beacon) !=len(u"01:02:03:04:05:06"):
					valuesDict[u"MSG"] = "bad Mac Number"
					return (False, valuesDict)
				self.beaconPositionsUpdated = 1
				
				
			if typeId == "rPI":
				newMAC = valuesDict[u"newMACNumber"].upper()
				valuesDict[u"newMACNumber"] = newMAC
				if len(newMAC) == len(u"01:02:03:04:05:06"):
						if beacon != newMAC:
							self.ML.myLog( text = u"replacing RPI BLE mac "+beacon+u" with "+newMAC)
							piFound =-1
							for pi in range(_GlobalConst_numberOfiBeaconRPI): 
								if self.RPI[unicode(pi)][u"piMAC"] == newMAC:
									self.ML.myLog( text = u"replacing RPI BLE mac failed. rpi already exists with this MAC number")
									valuesDict[u"MSG"] = "bad beacon#, already exist as RPI"
									return (False, valuesDict)
							pi0 = "-1"
							for pi in range(_GlobalConst_numberOfiBeaconRPI): 
								if self.RPI[unicode(pi)][u"piMAC"] == beacon:
									pi0 = unicode(pi)
									break
							if pi0 ==u"-1":
									self.ML.myLog( text = u"replacing RPI BLE mac failed. beacon mac not found ")
									valuesDict[u"MSG"] = "non existing beacon#"
									return (False, valuesDict)
								
							self.ML.myLog( text = u"replacing existing beacon")
							if beacon not in self.beacons:
								self.beacons[newMAC] = copy.deepcopy(_GlobalConst_emptyBeacon)
								self.beacons[newMAC][u"note"] = "PI-"+pi0
							else:
								self.beacons[newMAC] = copy.deepcopy(self.beacons[beacon])
							self.beacons[beacon][u"indigoId"] = 0
							self.newADDRESS[devId]			 = newMAC
							props[u"address"]				  = self.newADDRESS[devId]
							self.RPI[pi0][u"piMAC"]			  = newMAC
							dev.replacePluginPropsOnServer(props)
							dev = indigo.devices[devId]
							props = dev.pluginProps
							if beacon in self.beacons:
								self.beacons[beacon][u"indigoId"]= 0
							beacon = newMAC

				else:
					valuesDict[u"MSG"] = "bad Mac Number"
					valuesDict[u"newMACNumber"] = beacon
					return (False, valuesDict)
				
				if len(beacon) !=len(u"01:02:03:04:05:06"):
					valuesDict[u"MSG"] = "bad Mac Number"
					return (False, valuesDict)



			if typeId == "rPI" or typeId == "beacon":
				if beacon in self.beacons:
					self.beacons[beacon][u"expirationTime"] = float(valuesDict[u"expirationTime"])
					self.beacons[beacon][u"updateSignalValuesSeconds"] = float(valuesDict[u"updateSignalValuesSeconds"])
					self.beacons[beacon][u"beaconTxPower"] = int(valuesDict[u"beaconTxPower"])
					dev.updateStateOnServer(u"TxPowerSet",int(valuesDict[u"beaconTxPower"]))
					self.beacons[beacon][u"ignore"] = int(valuesDict[u"ignore"])

					if typeId == "beacon":
						self.beacons[beacon][u"note"] = "beacon-" + valuesDict[u"typeOfBeacon"]
						self.addToStatesUpdateDict(unicode(dev.id),"note", self.beacons[beacon][u"note"],dev=dev)
						if valuesDict[u"typeOfBeacon"] != self.beacons[beacon][u"typeOfBeacon"]:
							self.setALLrPiV(u"piUpToDate", [u"updateParamsFTP"])
							if self.ML.decideMyLog(u"UpdateRPI"): self.ML.myLog( text =	 u"update RPI due to typeOfBeacon")
						if int(valuesDict[u"signalDelta"]) != self.beacons[beacon][u"signalDelta"]:
							self.setALLrPiV(u"piUpToDate", [u"updateParamsFTP"])
							if self.ML.decideMyLog(u"UpdateRPI"): self.ML.myLog( text =	 u"update RPI due to signalDelta")
						if int(valuesDict[u"minSignalCutoff"]) != self.beacons[beacon][u"minSignalCutoff"]:
							self.setALLrPiV(u"piUpToDate", [u"updateParamsFTP"])
							if self.ML.decideMyLog(u"UpdateRPI"): self.ML.myLog( text =	 u"update RPI due to minSignalCutoff")
						if int(valuesDict[u"fastDown"]) != self.beacons[beacon][u"fastDown"]:
							self.setALLrPiV(u"piUpToDate", [u"updateParamsFTP"])
							if self.ML.decideMyLog(u"UpdateRPI"): self.ML.myLog( text =	 u"update RPI due to fastDown")
						if int(valuesDict[u"fastDownMinSignal"]) != self.beacons[beacon][u"fastDownMinSignal"]:
							self.setALLrPiV(u"piUpToDate", [u"updateParamsFTP"])
							if self.ML.decideMyLog(u"UpdateRPI"): self.ML.myLog( text =	 u"update RPI due to fastDownMinSignal")

						self.beacons[beacon][u"showBeaconOnMap"]		 = valuesDict[u"showBeaconOnMap"]
						self.beacons[beacon][u"typeOfBeacon"]			 = valuesDict[u"typeOfBeacon"]
						self.beacons[beacon][u"signalDelta"]			 = int(valuesDict[u"signalDelta"])
						self.beacons[beacon][u"minSignalCutoff"]		 = int(valuesDict[u"minSignalCutoff"])
						self.beacons[beacon][u"fastDown"]				 = int(valuesDict[u"fastDown"])
						self.beacons[beacon][u"fastDownMinSignal"]		 = int(valuesDict[u"fastDownMinSignal"])
						memberList =""
						for group in _GlobalConst_groupList:
							if unicode(valuesDict[u"memberOf"+group]).lower() == "true":
								memberList += group+"/"
						memberList = memberList.strip(u"/")
						if dev.states[u"groupMember"] != memberList:
								dev.updateStateOnServer(u"groupMember",memberList)


								
			if typeId.find(u"rPI") > -1:
				pi = -1
				for pi0 in range(_GlobalConst_numberOfRPI):
					if devId == self.RPI[unicode(pi0)][u"piDevId"]:
						pi = pi0
						break
				if pi >= 0:
					if u"shutDownPinInput"	not in props  or (u"shutDownPinInput"  in props and valuesDict[u"shutDownPinInput"]	 != props[u"shutDownPinInput"]):
						self.setONErPiV(pi,"piUpToDate", [u"updateParamsFTP"])
						self.rPiRestartCommand[pi] = "master"
					if u"shutDownPinOutput" not in props  or (u"shutDownPinOutput" in props and valuesDict[u"shutDownPinOutput"] != props[u"shutDownPinOutput"]):
						self.setONErPiV(pi,"piUpToDate", [u"updateParamsFTP"])
						self.rPiRestartCommand[pi] = "master"
					if u"useRamDiskForLogfiles" not in props  or (u"useRamDiskForLogfiles" in props and valuesDict[u"useRamDiskForLogfiles"] != props[u"useRamDiskForLogfiles"]):
						self.setONErPiV(pi,"piUpToDate", [u"updateParamsFTP"])
						self.rPiRestartCommand[pi] = "master"
					if u"useRTC" not in props  or (u"useRTC" in props and valuesDict[u"useRTC"] != props[u"useRTC"]):
						self.setONErPiV(pi,"piUpToDate", [u"updateParamsFTP"])
						self.rPiRestartCommand[pi] = "master"

					srf = valuesDict[u"sendToIndigoSecs"]
					if srf != self.RPI[unicode(pi)][u"sendToIndigoSecs"] :
						self.setONErPiV(pi,"piUpToDate", [u"updateParamsFTP"])
						self.updateNeeded += " fixConfig sendToIndigoSecs "
						self.rPiRestartCommand[pi] = "master"
					self.RPI[unicode(pi)][u"sendToIndigoSecs"] = srf

					srf = valuesDict[u"sensorRefreshSecs"]
					if srf != self.RPI[unicode(pi)][u"sensorRefreshSecs"] :
						self.setONErPiV(pi,"piUpToDate", [u"updateParamsFTP"])
						self.updateNeeded += " fixConfig sensorRefreshSecs "
						self.rPiRestartCommand[pi] = "master"
					self.RPI[unicode(pi)][u"sensorRefreshSecs"] = srf

					srf = valuesDict[u"deltaChangedSensor"]
					if srf != self.RPI[unicode(pi)][u"deltaChangedSensor"] :
						self.setONErPiV(pi,"piUpToDate", [u"updateParamsFTP"])
						self.updateNeeded += " fixConfig deltaChangedSensor "
						self.rPiRestartCommand[pi] = "master"
					self.RPI[unicode(pi)][u"deltaChangedSensor"] = srf

			if typeId == "rPI":
				pi = -1
				for pi0 in range(_GlobalConst_numberOfiBeaconRPI):
					if devId == self.RPI[unicode(pi0)][u"piDevId"]:
						pi = pi0
						break
				if pi >= 0:
					try:	 self.RPI[unicode(pi)][u"rssiOffset"]	= float(valuesDict["rssiOffset"])
					except:	 self.RPI[unicode(pi)][u"rssiOffset"]	= 0.

					srf = valuesDict[u"BLEserial"]
					if not (u"BLEserial" in props and srf == props[u"BLEserial"]) :
						self.setONErPiV(pi,"piUpToDate", [u"updateParamsFTP"])
						self.updateNeeded += " fixConfig BLEserial "
						self.rPiRestartCommand[pi] = "BLEconnect"
					self.RPI[unicode(pi)][u"BLEserial"] = srf

					xyz = valuesDict[u"PosXYZ"]
					try:
						xyz = xyz.split(u",")
						if len(xyz) == 3:
							self.beacons[beacon][u"PosX"] = int(float(xyz[0]) * self.distanceUnits)
							self.beacons[beacon][u"PosY"] = int(float(xyz[1]) * self.distanceUnits)
							self.beacons[beacon][u"PosZ"] = int(float(xyz[2]) * self.distanceUnits)
							dev = indigo.devices[devId]
							self.addToStatesUpdateDict(unicode(dev.id),"PosX", float(xyz[0]),decimalPlaces=1,dev=dev)
							self.addToStatesUpdateDict(unicode(dev.id),"PosY", float(xyz[1]),decimalPlaces=1)
							self.addToStatesUpdateDict(unicode(dev.id),"PosZ", float(xyz[2]),decimalPlaces=1)
					except	Exception, e:
						self.ML.myLog( text =  u"validateDeviceConfigUi in Line '%s' has error='%s'" % (sys.exc_traceback.tb_lineno, e))
						self.ML.myLog( text =  u"bad input for xyz-coordinates: " + valuesDict[u"PosXYZ"])
						self.beacons[beacon][u"PosX"] = 0.
						self.beacons[beacon][u"PosY"] = 0.
						self.beacons[beacon][u"PosZ"] = 0.
				self.executeUpdateStatesDict(calledFrom="validateDeviceConfigUi RPI")		 
				return (True, valuesDict)


			elif typeId	 ==u"rPI-Sensor":
						update = 0
						pi = -1
						for pi0 in range(_GlobalConst_numberOfRPI):
							if devId == self.RPI[unicode(pi0)][u"piDevId"]:
								pi = pi0
								break
						if pi >= 0:
							self.setONErPiV(pi,"piUpToDate", [u"updateParamsFTP"])
						return (True, valuesDict)



			elif typeId	 ==u"BLEconnect":
				BLEMAC = valuesDict[u"macAddress"].upper()
				if len(BLEMAC) != 17: return
				active=""
				for pi in range(_GlobalConst_numberOfiBeaconRPI):
					update=0
					if valuesDict[u"rPiEnable"+unicode(pi)]:
						if typeId not in self.RPI[unicode(pi)][u"input"]:
							self.RPI[unicode(pi)][u"input"][typeId]={}
							update=1
						if unicode(devId) not in self.RPI[unicode(pi)][u"input"][typeId]:
							self.RPI[unicode(pi)][u"input"][typeId][unicode(devId)]=""
						if BLEMAC !=  self.RPI[unicode(pi)][u"input"][typeId][unicode(devId)]:
							update=1
						self.RPI[unicode(pi)][u"input"][typeId][unicode(devId)] = BLEMAC
						active+=" "+unicode(pi)+","
					else:
						if typeId in self.RPI[unicode(pi)][u"input"]:
							if unicode(devId) in self.RPI[unicode(pi)][u"input"][typeId]:
								del	 self.RPI[unicode(pi)][u"input"][typeId][unicode(devId)]
								update=1
					valuesDict[u"description"] = "on rPi "+ active
					valuesDict[u"address"] = BLEMAC
					if typeId in self.RPI[unicode(pi)][u"input"]:
						if self.RPI[unicode(pi)][u"input"][typeId] == {}:
							del self.RPI[unicode(pi)][u"input"][typeId]

					if typeId not in self.RPI[unicode(pi)][u"input"]:
						if typeId in self.RPI[unicode(pi)][u"sensorList"]:
							self.RPI[unicode(pi)][u"sensorList"]= self.RPI[unicode(pi)][u"sensorList"].replace(typeId+",","")

					if u"iPhoneRefreshDownSecs" in props :
						if props[u"iPhoneRefreshDownSecs"] != valuesDict[u"iPhoneRefreshDownSecs"]:
							update = 1
					else:
							update = 1

					if u"iPhoneRefreshUpSecs" in props :
						if props[u"iPhoneRefreshUpSecs"] != valuesDict[u"iPhoneRefreshUpSecs"] :
							update = 1
					else:
							update = 1

					if u"BLEtimeout" in props :
						if props[u"BLEtimeout"] != valuesDict[u"BLEtimeout"] :
							update = 1
					else :
						update = 1

					if u"retryIfUP" in props :
						 if props[u"retryIfUP"] != valuesDict[u"retryIfUP"] :
							update = 1
					else:
							update = 1

					if update==1:
						self.rPiRestartCommand[pi] +="BLEconnect,"
						self.updateNeeded += " fixConfig "
						self.setONErPiV(pi,"piUpToDate", [u"updateParamsFTP"])
				return (True, valuesDict)



			if typeId.find(u"INPUTgpio")>-1 or typeId.find(u"INPUTtouch")>-1:
				if typeId.find(u"INPUTgpio")>-1:	typeINPUT = "INPUTgpio"
				if typeId.find(u"INPUTtouch")>-1:	typeINPUT = "INPUTtouch"
				
				active = ""
				update = 0

				pi = int(valuesDict[u"piServerNumber"])
				for pi0 in range(_GlobalConst_numberOfRPI):
					if pi == pi0:													  continue
					if u"input" not in self.RPI[unicode(pi0)]:						  continue
					if typeId not in self.RPI[unicode(pi0)][u"input"]:				  continue
					if unicode(devId) not in self.RPI[unicode(pi0)][u"input"][typeId]:continue
					del self.RPI[unicode(pi0)][u"input"][typeId][unicode(devId)]
					self.setONErPiV(pi0,"piUpToDate",[u"updateParamsFTP"])
					self.rPiRestartCommand[pi0] += typeINPUT+","
					update = 1

				if pi >= 0:
					if u"piServerNumber" in props:
						if pi != int(props[u"piServerNumber"]):
							self.setONErPiV(pi0,"piUpToDate",[u"updateParamsFTP"])
							self.rPiRestartCommand[int(props[u"piServerNumber"])] += typeINPUT+","
							update = 1
					self.setONErPiV(pi,"piUpToDate", [u"updateParamsFTP"])
					self.rPiRestartCommand[pi] += typeINPUT+","

				if typeId not in self.RPI[unicode(pi)][u"input"]:
						self.RPI[unicode(pi)][u"input"][typeId] = {}
						update = 1
				if unicode(devId) not in self.RPI[unicode(pi)][u"input"][typeId]:
					self.RPI[unicode(pi)][u"input"][typeId][unicode(devId)] = []
					update = 1
				newDeviceDefs = json.loads(valuesDict[u"deviceDefs"])

				try:
					if len(newDeviceDefs) != len(self.RPI[unicode(pi)][u"input"][typeId][unicode(devId)]):
						update = 1
					for n in range(len(newDeviceDefs)):
						if update == 1: break
						for item in newDeviceDefs[n]:
							if newDeviceDefs[n][item] != self.RPI[unicode(pi)][u"input"][typeId][unicode(devId)][n][item]:
								update = 1
								break
				except:
					update = 1

				self.RPI[unicode(pi)][u"input"][typeId][unicode(devId)] = newDeviceDefs

				if typeINPUT == "INPUTgpio":
					pinMappings = "(#,gpio,inpType,Count)"
				if typeINPUT == "INPUTtouch":
					pinMappings = "(#,Chan.,Count)"
					
					
				for n in range(len(newDeviceDefs)):
					if u"gpio" in newDeviceDefs[n]:
						if newDeviceDefs[n][u"gpio"]==u"": continue
						if typeINPUT == "INPUTgpio":
							pinMappings += "(u" + unicode(n) + ":" + newDeviceDefs[n][u"gpio"]+ "," + newDeviceDefs[n][u"inpType"] + "," + newDeviceDefs[n][u"count"] + ");"
						if typeINPUT == "INPUTtouch":
							pinMappings += "(u" + unicode(n) + ":" + newDeviceDefs[n][u"gpio"]+ ","	 + newDeviceDefs[n][u"count"] + ");"
				valuesDict[u"description"] = pinMappings

				if update == 1:
					self.rPiRestartCommand[pi] += typeINPUT+","
					self.updateNeeded += " fixConfig "
					self.setONErPiV(pi,"piUpToDate", [u"updateParamsFTP"])

				if valuesDict["count"]  == "off":
					valuesDict["SupportsOnState"]		= True
					valuesDict["SupportsSensorValue"]	= False
				else:
					valuesDict["SupportsOnState"]		= False
					valuesDict["SupportsSensorValue"]	= True
					

				valuesDict[u"piDone"]		= False
				valuesDict[u"stateDone"]	= False
				dev.replaceOnServer()
				self.ML.myLog( text =  u" piUpToDate pi: " +unicode(pi)+ "	value:"+ unicode(self.RPI[unicode(pi)][u"piUpToDate"]))
				self.ML.myLog( text =  unicode(valuesDict) )
				return (True, valuesDict)


	 

			if typeId.find(u"OUTPUTgpio-") > -1:
				update = 0
				active = ""
				pi = int(valuesDict[u"piServerNumber"])
				for pi0 in range(_GlobalConst_numberOfRPI):
					if pi == pi0:														continue
					if u"output" not in self.RPI[unicode(pi0)]:							continue
					if typeId not in self.RPI[unicode(pi0)][u"output"]:					continue
					if unicode(devId) not in self.RPI[unicode(pi0)][u"output"][typeId]: continue
					del self.RPI[unicode(pi0)][u"output"][typeId][unicode(devId)]
					self.setONErPiV(pi0,"piUpToDate",[u"updateParamsFTP"])

				if pi >= 0:
					if u"piServerNumber" in props:
						if pi != int(props[u"piServerNumber"]):
							self.setONErPiV(pi,"piUpToDate", [u"updateParamsFTP"])
							update=1

				

				if typeId not in self.RPI[unicode(pi)][u"output"]:
					self.RPI[unicode(pi)][u"output"][typeId] = {}
					update = 1
				if unicode(devId) not in self.RPI[unicode(pi)][u"output"][typeId]:
					self.RPI[unicode(pi)][u"output"][typeId][unicode(devId)] = []
					update = 1
				new = json.loads(valuesDict[u"deviceDefs"])

				try:
					if len(new) != len(self.RPI[unicode(pi)][u"output"][typeId][unicode(devId)]):
						update = 1
					for n in range(len(new)):
						if update == 1: break
						for item in new[n]:
							if new[n] != self.RPI[unicode(pi)][u"output"][typeId][unicode(devId)][n][item]:
								update = 1
								break
				except:
					update = 1

				self.RPI[unicode(pi)][u"output"][typeId][unicode(devId)] = new

				pinMappings ="(#,gpio,type,init)"
				for n in range(len(new)):
					if u"gpio" in new[n]:
						pinMappings += "(u" + unicode(n) + ":" + new[n][u"gpio"]+"," + new[n][u"outType"] +"," +  new[n][u"initialValue"]  +");"
					else:
						pinMappings += "(u" + unicode(n) + ":-);"
				valuesDict[u"description"] = pinMappings

				if update == 1:
					self.rPiRestartCommand[pi] += typeId+","
					self.updateNeeded += " fixConfig "
					self.setONErPiV(pi,"piUpToDate", [u"updateParamsFTP"])

				valuesDict[u"piDone"] = False
				valuesDict[u"stateDone"] = False
				dev.replaceOnServer()
				#self.ML.myLog( text = " at save " + unicode(update)+"	"+unicode(valuesDict)+"\n"+unicode(self.RPI[unicode(pi0)][u"input"]))
				return (True, valuesDict)



			elif typeId in _GlobalConst_allowedSensors:
				update = 0
				pi = int(valuesDict[u"piServerNumber"])
				if pi >= 0:
					if u"piServerNumber" in props:
						 if pi != int(props[u"piServerNumber"]):
							 self.updateNeeded += " fixConfig "
							 self.rPiRestartCommand[pi] += "master,"
							 self.rPiRestartCommand[int(props[u"piServerNumber"])] += "master,"
							 self.setONErPiV(props[u"piServerNumber"],"piUpToDate",[u"updateParamsFTP"])

					valuesDict[u"address"] = "PI-" + unicode(pi)
					if typeId not in self.RPI[unicode(pi)][u"input"]:
						self.RPI[unicode(pi)][u"input"][typeId] = {}
						self.rPiRestartCommand[pi] += "master,"
						self.updateNeeded += " fixConfig "

					if unicode(dev.id) not in self.RPI[unicode(pi)][u"input"][typeId]:
						self.RPI[unicode(pi)][u"input"][typeId][unicode(dev.id)]={}
						self.updateNeeded += " fixConfig "
					self.setONErPiV(pi,"piUpToDate", [u"updateParamsFTP"])


				if u"BLEsensor" == typeId :
					valuesDict[u"description"] = valuesDict[u"type"] +"-"+ valuesDict[u"mac"]


				if u"launchpgm" == typeId :
					valuesDict[u"description"] =  "pgm: "+valuesDict[u"launchCommand"]


				if	typeId	in ["mhz-I2C","mhz-SERIAL"]:
					dev.updateStateOnServer("CO2calibration",valuesDict["CO2normal"])


				if	typeId	=="rainSensorRG11":
						valuesDict[u"description"] = "INP:"+valuesDict[u"gpioIn"]+"-SW5:"+valuesDict[u"gpioSW5"]+"-SW2:"+valuesDict[u"gpioSW2"]+"-SW1:"+valuesDict[u"gpioSW1"]+"-SW12V:"+valuesDict[u"gpioSWP"]

						
				if	typeId =="pmairquality" :
					if valuesDict[u"resetPin"] !="-1" and valuesDict[u"resetPin"] !="":
						valuesDict[u"description"] = "reset-GPIO: " +valuesDict[u"resetPin"]
					else:
						valuesDict[u"description"] = "reset-GPIO not used"


				if	typeId =="Wire18B20" : # update serial number in states in case we jumped around with dev types. 
					if len(dev.states["serialNumber"]) < 5  and dev.description.find("sN= 28")>-1:
						dev.updateStateOnServer("serialNumber", dev.description.split("sN= ")[1])



						
				if	typeId.find(u"DHT") >-1:
					if u"gpioPin" in valuesDict:
						valuesDict[u"description"] = "GPIO-PIN: " +valuesDict[u"gpioPin"]
						
				if ("i2c" in typeId.lower() or typeId in i2cSensors):  
					if "i2cAddress" in valuesDict:
						try:
							addrhex = "	 = #"+hex(int(valuesDict[u"i2cAddress"]))
						except:
							addrhex =""
						if u"useMuxChannel" in valuesDict and valuesDict[u"useMuxChannel"] !="-1":
							valuesDict[u"description"] = "i2c: " +valuesDict[u"i2cAddress"]+addrhex +u"; mux-channel: "+valuesDict[u"useMuxChannel"]
						else:
							valuesDict[u"description"] = "i2c: " +valuesDict[u"i2cAddress"]+addrhex
				if	"calibrationPin" in valuesDict:
							valuesDict[u"description"] = "CalibGPIO: " +valuesDict[u"calibrationPin"]
					
				if "ultrasoundDistance" == typeId :
					self.rPiRestartCommand[pi] += "ultrasoundDistance,"
					if u"gpioTrigger" not in props or (props[u"gpioTrigger"] != valuesDict[u"gpioTrigger"]): 
						self.rPiRestartCommand[pi] += "ultrasoundDistance,"
					if u"gpioEcho" not in props or(props[u"gpioEcho"] != valuesDict[u"gpioEcho"]): 
						self.rPiRestartCommand[pi] += "ultrasoundDistance,"
					if u"sensorRefreshSecs" not in props or (props[u"sensorRefreshSecs"] != valuesDict[u"sensorRefreshSecs"]): 
						self.rPiRestartCommand[pi] += "ultrasoundDistance,"
					if u"deltaDist" not in props or (props[u"deltaDist"] != valuesDict[u"deltaDist"]): 
						self.rPiRestartCommand[pi] += "ultrasoundDistance,"
					valuesDict[u"description"] = "trigger-pin: " +valuesDict[u"gpioTrigger"] +"; echo-pin: " +valuesDict[u"gpioEcho"]+"; refresh:"+valuesDict[u"sensorRefreshSecs"]+"; unit:"+valuesDict[u"dUnits"]
					valuesDict,error = self.addBracketsPOS(valuesDict,"pos1")
					if error ==u"":
						valuesDict,error = self.addBracketsPOS(valuesDict,"pos2")
						if error ==u"":
							valuesDict,error = self.addBracketsPOS(valuesDict,"pos3")

				if "vl503l0xDistance" == typeId :
					self.rPiRestartCommand[pi] += "vl503l0xDistance,"
					if u"sensorRefreshSecs" not in props or (props[u"sensorRefreshSecs"] != valuesDict[u"sensorRefreshSecs"]): 
						self.rPiRestartCommand[pi] += "vl503l0xDistance,"
					if u"sensorRefreshSecs" not in props or (props[u"sensorRefreshSecs"] != valuesDict[u"sensorRefreshSecs"]): 
						self.rPiRestartCommand[pi] += "ultrasoundDistance,"
					if u"deltaDist" not in props or (props[u"deltaDist"] != valuesDict[u"deltaDist"]): 
						self.rPiRestartCommand[pi] += "vl503l0xDistance,"

				if "vl6180xDistance" == typeId :
					if typeId not in self.RPI[unicode(pi)][u"input"]:
						self.RPI[unicode(pi)][u"input"][typeId] = {}
						self.rPiRestartCommand[pi] += "vl6180xDistance,"
					if u"sensorRefreshSecs" not in props or (props[u"sensorRefreshSecs"] != valuesDict[u"sensorRefreshSecs"]): 
						self.rPiRestartCommand[pi] += "vl6180xDistance,"
					if u"deltaDist" not in props or (props[u"deltaDist"] != valuesDict[u"deltaDist"]): 
						self.rPiRestartCommand[pi] += "vl6180xDistance,"

				elif "vcnl4010Distance" == typeId :
					self.rPiRestartCommand[pi] += "vcnl4010Distance,"
					if u"sensorRefreshSecs" not in props or (props[u"sensorRefreshSecs"] != valuesDict[u"sensorRefreshSecs"]): 
						self.rPiRestartCommand[pi] += "vcnl4010Distance,"
					if u"deltaDist" not in props or (props[u"deltaDist"] != valuesDict[u"deltaDist"]): 
						self.rPiRestartCommand[pi] += "vcnl4010Distance,"

				if "INPUTpulse" == typeId :
					pinMappings = "gpio="+valuesDict[u"gpio"]+ "," +valuesDict[u"risingOrFalling"]+ " Edge, u" +valuesDict[u"deadTime"]+ "secs deadTime"
					valuesDict[u"description"] = pinMappings

				self.setONErPiV(pi,"piUpToDate", [u"updateParamsFTP"])
				self.updateNeeded += " fixConfig "
				valuesDict[u"msg"] =error
				if error ==u"":
					self.updateNeeded += " fixConfig "
					self.setONErPiV(pi,"piUpToDate", [u"updateParamsFTP"])
					return (True, valuesDict)
				else:
					errorDict[u"msg"]= error
					self.ML.myLog( text =  u"validating device error:" +error+"	 fields:"+unicode(valuesDict))
					return (False,valuesDict,errorDict)


			elif typeId in _GlobalConst_allowedOUTPUT:
				if typeId==u"neopixel-dimmer":
					self.ML.myLog( text =  u"entering neopixel dimmer ")
					try:
						neopixelDevice = indigo.devices[int(valuesDict[u"neopixelDevice"])]
						propsX = neopixelDevice.pluginProps
						pi = int(propsX[u"piServerNumber"])
						self.rPiRestartCommand[pi] += "neopixel,"
						self.setONErPiV(pi,"piUpToDate", [u"updateParamsFTP"]) 
						valuesDict[u"address"] = neopixelDevice.name
						try: 
							xxx= propsX[u"devType"].split(u"x")
							ymax = int(xxx[0])
							xmax = int(xxx[1])
						except:
							error ="devtype not defined for neopixel"
							valuesDict[u"msg"] =error
							errorDict[u"msg"]= error
							return (False,valuesDict,errorDict)
							
						self.ML.myLog( text =  u"entering neopixel dimmer 2")
						
						pixels="; pix="
						if valuesDict[u"pixelMenulist"] !="": pixels +=valuesDict[u"pixelMenulist"]
						else:
							for ii in range(20):
								if u"pixelMenu"+unicode(ii) in valuesDict and valuesDict[u"pixelMenu"+unicode(ii)] !="":
									pixel =valuesDict[u"pixelMenu"+unicode(ii)]
									if u"," not in pixel: 
										# try just one dim.
										valuesDict[u"pixelMenu"+unicode(ii)]= "0,"+pixel

									pixel =valuesDict[u"pixelMenu"+unicode(ii)]
									xxx = pixel.split(u",")
									x = xxx[1]
									y = xxx[0]
									if	int(x) >= xmax : x = unicode(max(0,xmax-1))
									if	int(y) >= ymax : y = unicode(max(0,ymax-1))
									pixels +=y+","+x+" "
									valuesDict[u"pixelMenu"+unicode(ii)] = y+","+x
							pixels =pixels.strip(u" ")
						valuesDict[u"description"]	= "rampSp="+ valuesDict[u"speedOfChange"]+"[sec]"+ pixels
						self.ML.myLog( text =  u"entering neopixel dimmer 3")
						
						
					except	Exception, e:
						if unicode(e).find(u"timeout waiting") > -1:
							self.ML.myLog( text =  u"validateDeviceConfigUi in Line '%s' has error='%s'" % (sys.exc_traceback.tb_lineno, e))
							self.ML.myLog( text =  u"communication to indigo is interrupted")
							return (False, valuesDict, errorDict)
						self.ML.myLog( text =  u"validateDeviceConfigUi in Line '%s' has error='%s'" % (sys.exc_traceback.tb_lineno, e))
						
				elif typeId==u"neopixel":
					try:
						pi = int(valuesDict[u"piServerNumber"])
						self.rPiRestartCommand[pi] += "neopixel,"
						valuesDict[u"address"]		 = "Pi-"+valuesDict[u"piServerNumber"]
						valuesDict[u"devType"]		 = valuesDict[u"devTypeROWs"] +"x"+valuesDict[u"devTypeLEDs"]
						valuesDict[u"description"]	 = "type="+valuesDict[u"devType"]
						self.setONErPiV(pi,"piUpToDate", [u"updateParamsFTP"]) 
					except:
						pass
				else:
					pi = int(valuesDict[u"piServerNumber"])
					valuesDict[u"address"] = "PI-" + unicode(pi)
					if pi >= 0:
						if u"piServerNumber" in props:
							if pi != int(props[u"piServerNumber"]):
								self.updateNeeded += " fixConfig "
						cAddress = ""
						devType=""

						if u"devType" in valuesDict:
							devType = valuesDict[u"devType"]
						
						if u"output" not in	  self.RPI[unicode(pi)]:  
							self.RPI[unicode(pi)][u"output"]={}
						if typeId not in   self.RPI[unicode(pi)][u"output"]:  
							self.RPI[unicode(pi)][u"output"][typeId]={}
						if unicode(devId) not in   self.RPI[unicode(pi)][u"output"][typeId]:  
							self.RPI[unicode(pi)][u"output"][typeId][unicode(devId)]={}

						if u"i2cAddress" in valuesDict:
							cAddress = valuesDict[u"i2cAddress"]
							self.RPI[unicode(pi)][u"output"][typeId][unicode(devId)] = [{u"i2cAddress":cAddress},{u"devType":devType}]

						elif "spiAddress" in valuesDict:
							cAddress = unicode(int(valuesDict[u"spiAddress"]))
							self.RPI[unicode(pi)][u"output"][typeId][unicode(devId)] = [{u"spi":cAddress},{u"devType":devType}]

						self.RPI[unicode(pi)][pi] = 1
						self.updateNeeded += " fixConfig "
						self.rPiRestartCommand[pi] += "receiveGPIOcommands,"
						self.setONErPiV(pi,"piUpToDate", [u"updateParamsFTP"])


						if typeId==u"display":
							valuesDict = self.fixDisplayProps(valuesDict,typeId,devType)
					
							self.rPiRestartCommand[pi] += "display,"
							self.setONErPiV(pi,"piUpToDate", [u"updateAllFilesFTP"]) # this will send images and fonts too
							valuesDict,error = self.addBracketsPOS(valuesDict,"pos1")
							if error ==u"":
								valuesDict,error = self.addBracketsPOS(valuesDict,"pos2")
								if error ==u"":
									valuesDict,error = self.addBracketsPOS(valuesDict,"pos3")


						if typeId==u"setTEA5767":
							dev = indigo.devices[devId]
							self.setONErPiV(pi,"piUpToDate", [u"updateParamsFTP"]) # this will send config only
							self.addToStatesUpdateDict(devId,"status"	,"f= "+valuesDict[u"defFreq"] + "; mute= " +valuesDict[u"mute"],dev=dev)
							self.addToStatesUpdateDict(devId,"frequency",valuesDict[u"defFreq"] )
							self.addToStatesUpdateDict(devId,"mute"		,valuesDict[u"mute"])
							self.executeUpdateStatesDict(onlyDevID=str(devId),calledFrom="validateDeviceConfigUi set TEA")
							self.devUpdateList[str(devId)] = True

			else:
				pass
			valuesDict[u"msg"] =error
			if error ==u"":
				self.updateNeeded += " fixConfig "
				return (True, valuesDict)
			else:
				errorDict[u"msg"]= error
				return (False,valuesDict,errorDict)


		except	Exception, e:
			if unicode(e).find(u"timeout waiting") > -1:
				self.ML.myLog( text =  u"validateDeviceConfigUi in Line '%s' has error='%s'" % (sys.exc_traceback.tb_lineno, e))
				self.ML.myLog( text =  u"communication to indigo is interrupted")
				return (False, valuesDict, errorDict)
			self.ML.myLog( text =  u"validateDeviceConfigUi in Line '%s' has error='%s'" % (sys.exc_traceback.tb_lineno, e))
		self.updateNeeded += " fixConfig "
		return (False, valuesDict, errorDict)

####-------------------------------------------------------------------------####
	def execdevUpdateList(self):
		if self.devUpdateList == {}: return
		for devId in self.devUpdateList:
			try:
				dev = indigo.devices[int(devId)]
				if dev.states[u"mute"] ==u"1":
					dev.updateStateImageOnServer(indigo.kStateImageSel.SensorOff)
				else:
					dev.updateStateImageOnServer(indigo.kStateImageSel.SensorOn)
			except Exception, e:
					self.ML.myLog( text =  u"execdevUpdateList in Line '%s' has error='%s'" % (sys.exc_traceback.tb_lineno, e))
		self.devUpdateList ={}

####-------------------------------------------------------------------------####
	def fixDisplayProps(self, valuesDict,typeId,devType):
		try:
			if typeId==u"display":
				if devType ==u"LCD1602":
					if u"displayResolution" in valuesDict: del valuesDict[u"displayResolution"]
					if u"textForssd1351-1"	in valuesDict: del valuesDict[u"textForssd1351-1"]
					if u"textForssd1351-2"	in valuesDict: del valuesDict[u"textForssd1351-2"]
					if u"PIN_RST"			in valuesDict: del valuesDict[u"PIN_RST"]
					if u"PIN_CS"			in valuesDict: del valuesDict[u"PIN_CS"]
					if u"PIN_DC"			in valuesDict: del valuesDict[u"PIN_DC"]
					if u"PIN_CE"			in valuesDict: del valuesDict[u"PIN_CE"]
					if u"intensity"			in valuesDict: del valuesDict[u"intensity"]
					if u"flipDisplay"		in valuesDict: del valuesDict[u"flipDisplay"]
					if u"scrollSpeed"		in valuesDict: del valuesDict[u"scrollSpeed"] 
					if u"extraPage0Line0"	in valuesDict: del valuesDict[u"extraPage0Line0"]
					if u"extraPage0Line1"	in valuesDict: del valuesDict[u"extraPage0Line1"]
					if u"extraPage0Color"	in valuesDict: del valuesDict[u"extraPage0Color"]
					if u"extraPage1Line0"	in valuesDict: del valuesDict[u"extraPage1Line0"]
					if u"extraPage1Line1"	in valuesDict: del valuesDict[u"extraPage1Line1"]
					if u"extraPage1Color"	in valuesDict: del valuesDict[u"extraPage1Color"]
					valuesDict[u"scrollxy"]		= "0"
					valuesDict[u"showDateTime"] = "0"
		except	Exception, e:
			if unicode(e).find(u"timeout waiting") > -1:
				self.ML.myLog( text =  u"fixDisplayProps in Line '%s' has error='%s'" % (sys.exc_traceback.tb_lineno, e))
		return valuesDict

####-------------------------------------------------------------------------####
	def addBracketsPOS(self, valuesDict,pos):
		error = ""
		if pos in valuesDict:
			if valuesDict[pos].find(u"[") !=0:
				valuesDict[pos] =u"["+valuesDict[pos]
			if valuesDict[pos].find(u"]") != len(valuesDict[pos])-1:
				valuesDict[pos] =valuesDict[pos]+"]"
			if len(valuesDict[pos]) > 2:
				if valuesDict[pos].find(u",") ==-1:
					valuesDict[pos]="error"
					error ="comma missing"
		return valuesDict,error



		###########################		MENU  #################################
####-------------------------------------------------------------------------####
	def printConfigMenu(self, valuesDict=None, typeId="", devId=0):
		self.printConfig()
		return valuesDict
####-------------------------------------------------------------------------####
	def buttonPrintGroupsCALLBACK(self, valuesDict=None, typeId="", devId=0):
		self.printGroups()
		return valuesDict
####-------------------------------------------------------------------------####
	def buttonPrintStatsCALLBACK(self, valuesDict=None, typeId="", devId=0):
		self.printTCPIPstats(all="yes")
		self.printUpdateStats()
		return valuesDict
####-------------------------------------------------------------------------####
	def resetStatsMenu(self, valuesDict=None, typeId=""):
		self.resetDataStats()

####-------------------------------------------------------------------------####
	def printDeviceDictCALLBACK(self, valuesDict=None, typeId=""):
		devId= int(valuesDict[u"printDeviceDict"])
		dev=indigo.devices[devId]
		self.ML.myLog( text = dev.name+"/"+unicode(devId)+" -------------------------------",mType="printing dev info for"	 )
		props=dev.pluginProps
		states=dev.states
		self.ML.myLog( text =  u"\n"+unicode(props),mType="props:")
		self.ML.myLog( text =  u"\n"+unicode(states),mType="states:")
		try:  self.ML.myLog( text = dev.description,mType="description:")
		except: pass
		try:  self.ML.myLog( text = dev.address,mType="address:")
		except: pass
		try:  self.ML.myLog( text = dev.deviceTypeId,mType="deviceTypeId:")
		except: pass
		try:  self.ML.myLog( text = unicode(dev.enabled),mType="enabled:")
		except: pass
		try:  self.ML.myLog( text = dev.model,mType="model:")
		except: pass
		if u"piServerNumber" in props:
			if props[u"piServerNumber"]!="":
				pi= int(props[u"piServerNumber"])
				self.ML.myLog( text =  u"\n"+self.writeJson(self.RPI[unicode(pi)], format=True ),mType="RPI info:")
		else:
			for pi in range(_GlobalConst_numberOfiBeaconRPI):
				if u"rPiEnable"+unicode(pi) in props:
					 self.ML.myLog( text =	u"\n"+self.writeJson(self.RPI[unicode(pi)], format=True ),mType="RPI info:")


		return valuesDict

####-------------------------------------------------------------------------####
	def printBLEreportCALLBACK(self, valuesDict=None, typeId=""):

		self.currentlyBooting			= time.time()+80
		pi = valuesDict[u"configurePi"]
		if pi ==u"": return
		out= json.dumps([{u"command":"BLEreport"}])
		self.presendtoRPI(pi,out)

		return valuesDict


####-------------------------------------------------------------------------####
	def buttonConfirmchangeLogfile(self, valuesDict=None, typeId="", devId=0):
		if not os.path.isfile(self.indigoPath + 'IndigoWebServer/indigopy/indigoconn.py'): return valuesDict
		f = open(self.indigoPath + 'IndigoWebServer/indigopy/indigoconn.py', u"r")
		g = open(self.indigoPath + 'IndigoWebServer/indigopy/indigoconn.py-1', u"w")
		lev = 0
		tab = "	"
		for line in f.readlines():
			if lev == 0:
				if line.find('def ServerWriteLog(self, logMessage):') > -1:
					lev = 1
					g.write(line)
					if line[0] == tab:
						tab = "	"
					else:
						tab = "    "
				else:
					g.write(line)
				continue
			elif lev == 1:
				stringToFind= '\'request to set variable "pi_IN_\''
				if line.find('if logMessage.find('+stringToFind+') ==0:	 return') == -1 and line.find('###KW mod to suppress a lot of messages') == -1:
					g.write(tab + '###KW mod to suppress a lot of messages\n')
					g.write(tab + tab + 'if logMessage.find('+stringToFind+') ==0:	return\n')

				else:
					lev = 10  # already modified, dont do anything
					break
				g.write(line)
				lev = 2
				continue
			else:
				g.write(line)
		f.close()
		g.close()
		if lev == 10:
			os.remove(self.indigoPath + 'IndigoWebServer/indigopy/indigoconn.py-1')
			self.ML.myLog( text =  u"....modified version already inplace, do nothing")
			return valuesDict

		if os.path.isfile(self.indigoPath + 'IndigoWebServer/indigopy/indigoconn.py.original'):
			os.remove(self.indigoPath + 'IndigoWebServer/indigopy/indigoconn.py.original')
		os.rename(self.indigoPath + 'IndigoWebServer/indigopy/indigoconn.py',
				  self.indigoPath + 'IndigoWebServer/indigopy/indigoconn.py.original')
		os.rename(self.indigoPath + 'IndigoWebServer/indigopy/indigoconn.py-1',
				  self.indigoPath + 'IndigoWebServer/indigopy/indigoconn.py')
		self.ML.myLog( text = u"/Library/Application Support/Perceptive Automation/Indigo x/IndigoWebServer/indigopy/indigoconn.py has been replace with modified version(logging suppressed)")
		self.ML.myLog( text = u"  the original has been renamed to indigoconn.py.original, you will need to restart indigo server to activate new version")
		self.ML.myLog( text = u"  to go back to the original version replace/rename the new version with the saved .../IndigoWebServer/indigopy/indigoconn.py.original file")

		return valuesDict

####-------------------------------------------------------------------------####
	def buttonConfirmReversechangeLogfile(self, valuesDict=None, typeId="", devId=0):

		if os.path.isfile(self.indigoPath + 'IndigoWebServer/indigopy/indigoconn.py.original'):
			os.remove(self.indigoPath + 'IndigoWebServer/indigopy/indigoconn.py')
			os.rename(self.indigoPath + 'IndigoWebServer/indigopy/indigoconn.py.original',
				  self.indigoPath + 'IndigoWebServer/indigopy/indigoconn.py')
			self.ML.myLog( text = u"/Library/Application Support/Perceptive Automation/Indigo x/IndigoWebServer/indigopy/indigoconn.py.original has been restored")
			self.ML.myLog( text = u" you will need to restart indigo server to activate new version")
		else:
			self.ML.myLog( text = u"no file ... indigopy.py.original found to restore")

		return valuesDict


####-------------------------------------------------------------------------####
	def setALLrPiV(self, item, value):
		for pi in range(_GlobalConst_numberOfRPI):
			self.setONErPiV(pi, item, value)
		return	  

####-------------------------------------------------------------------------####
	def setONErPiV(self,pi, item, value):
		try:
			pi=unicode(pi)
			if pi in self.RPI:
				if self.RPI[pi][u"ipNumberPi"] != "":
					if self.RPI[pi][u"piOnOff"] == "1":
						if value ==u"" or value ==[] or value ==[u""] or isinstance(self.RPI[pi][item], ( int, long ) ) or isinstance(self.RPI[pi][item],(str, unicode)):
							self.RPI[pi][item]=[]
						else:
							for v in value:
								if v not in self.RPI[pi][item]:
									self.RPI[pi][item].append(v)
			return
		except	Exception, e:
			self.ML.myLog( text =  u"setONErPiV in Line '%s' has error='%s'" % (sys.exc_traceback.tb_lineno, e))


####-------------------------------------------------------------------------####
	def removeAllPiV(self, item, value):
		for pi in range(_GlobalConst_numberOfRPI):
			self.removeONErPiV(pi, item, value)
		return	  

####-------------------------------------------------------------------------####
	def removeONErPiV(self,pi, item, value):
		pi=unicode(pi)
		###self.ML.myLog( text =  u"before "+ pi+"	"+item+"  "+ unicode(value)+"  "+ unicode(self.RPI[pi][item]))
		if pi in self.RPI:
			for v in value:
				vv = v.split(".exp")[0]
				if vv in self.RPI[pi][item]:
					self.RPI[pi][item].remove(vv)
		return



####-------------------------------------------------------------------------####
	def filterAllpiSimple(self, filter="", valuesDict=None, typeId="", devId=""):
		list=[]
		for pi in range(_GlobalConst_numberOfRPI):
			piS= unicode(pi)
			try:
				devId= int(self.RPI[piS][u"piDevId"])
				if devId >0:
					name= "-"+indigo.devices[devId].name
			except: name=""
			list.append((piS,"#"+piS+"-"+self.RPI[piS][u"ipNumberPi"]+name))
		return list

####-------------------------------------------------------------------------####
	def filterNeopixelDevice(self, filter="", valuesDict=None, typeId="", devId=""):
		list=[(u"0", u"not active")]
		return list

####-------------------------------------------------------------------------####
	def filterNeopixelType(self, filter="", valuesDict=None, typeId="", devId=""):
		list=[(u"0", u"not active")
			 ,(u"line"		 , u"LINE  enter left and right end")
			 ,(u"sPoint"	 , u"ONE	  POINT	 ")
			 ,(u"points"	 , u"MULTIPLE POINTS ")
			 ,(u"rectangle"	 , u"RECTANGLE ")
			 ,(u"image"		 , u"IMAGE	not implemnted yet")
			 ,(u"matrix"	 , u"MATRIX enter only RGB values for EACH point ")
			 ,(u"thermometer", u"THERMOMETER enter start, end pixels and color delta")
			 ,(u"NOP"		 , u"No operation, use to wait before next action")
			 ,(u"exec"		 , u"execute , not implemened yet")]
		return list


####-------------------------------------------------------------------------####
	def filterDisplayType(self, filter="", valuesDict=None, typeId="", devId=""):
		list=[(u"0", u"not active")
			 ,(u"text"			, u"text: eg %%d:sensorVolt:input%%[mV]")
			 ,(u"textWformat"	, u"text: with format string eg %%v:123%%FORMAT%3.1f[mV]; only for numbers")
			 ,(u"date"			, u"date:  %Y-%m-%d full screen")
			 ,(u"clock"			, u"clock: %H:%M full screen")
			 ,(u"dateString"	, u"date time: string format eg %HH:%M:%S")
			 ,(u"line"			, u"line [Xstart,Ystart,Xend,Yend], width")
			 ,(u"point"			, u"point-s: ([[x,y],[x,y],..] ")
			 ,(u"dot"			, u"dot: [x,y]	 size radius or x,y size")
			 ,(u"rectangle"		, u"rectangle [Xtl,Ytl,Xrb,Yrb]")
			 ,(u"triangle"		, u"triangle [X1,Y1,X2,Y2,Y3,Y3]")
			 ,(u"ellipse"		, u"ellipse, [Xtl,Ytl,Xrb,Yrb]")
			 ,(u"image"			, u"image: file name ")
			 ,(u"vBar"			, u"vertical bar ")
			 ,(u"hBar"			, u"horizontal bar ")
			 ,(u"vBarwBox"		, u"vertical bar with box ")
			 ,(u"hBarwBox"		, u"horizontal bar	with box")
			 ,(u"hist"			, u"histogram ")
			 ,(u"NOP"			, u"No operation, use to wait before next action")
			 ,(u"exec"			, u"execute")]
		return list


####-------------------------------------------------------------------------####
	def filterNeoPixelRings(self, filter="", valuesDict=None, typeId="", devId=""):
		list=[(u"1", u"1")
			 ,(u"6", u"6")
			 ,(u"8", u"8")
			 ,(u"10", u"10")
			 ,(u"12", u"12")
			 ,(u"14", u"14")
			 ,(u"16", u"16")
			 ,(u"20", u"20")
			 ,(u"24", u"24")
			 ,(u"28", u"28")
			 ,(u"30", u"30")
			 ,(u"32", u"32")
			 ,(u"36", u"36")
			 ,(u"40", u"40")
			 ,(u"48", u"48")
			 ,(u"60", u"60")
			 ,(u"72", u"72")]
		return list


####-------------------------------------------------------------------------####
	def filter10To100(self, filter="", valuesDict=None, typeId="", devId=""):
		list=[(u"10", u"10")
			 ,(u"20", u"20")
			 ,(u"30", u"30")
			 ,(u"40", u"40")
			 ,(u"50", u"50")
			 ,(u"60", u"60")
			 ,(u"70", u"70")
			 ,(u"80", u"80")
			 ,(u"90", u"90")
			 ,(u"100", u"100")]
		return list

####-------------------------------------------------------------------------####
	def filterDisplayPages(self, filter="", valuesDict=None, typeId="", devId=""):
		list=[(u"1", u"1")
			 ,(u"2", u"2")
			 ,(u"3", u"3")
			 ,(u"4", u"4")
			 ,(u"5", u"5")
			 ,(u"6", u"6")
			 ,(u"7", u"7")
			 ,(u"8", u"8")]
		return list
	   
####-------------------------------------------------------------------------####
	def filterDisplayScrollDelay(self, filter="", valuesDict=None, typeId="", devId=""):
		list=[(u"0.015", u"0.015 secs")
			 ,(u"0.025", u"0.025 secs")
			 ,(u"0.05" , u"0.05 secs")
			 ,(u"0.1"  , u"0.1 secs")
			 ,(u"0.2"  , u"0.2 secs")
			 ,(u"0.3"  , u"0.3 secs")
			 ,(u"0.4"  , u"0.4 secs")
			 ,(u"0.6"  , u"0.6 secs")]
		return list
  
####-------------------------------------------------------------------------####
	def filterDisplayNumberOfRepeats(self, filter="", valuesDict=None, typeId="", devId=""):
		list=[(u"1" , u"1")
			 ,(u"2" , u"2 ")
			 ,(u"3" , u"3")
			 ,(u"4" , u"4")
			 ,(u"5" , u"5")
			 ,(u"6" , u"8")
			 ,(u"7" , u"7")
			 ,(u"8" , u"8")
			 ,(u"9" , u"9")
			 ,(u"10" ,	"10")
			 ,(u"12" , u"12")
			 ,(u"15" , u"15")
			 ,(u"20" , u"20")
			 ,(u"25" , u"25")
			 ,(u"30" , u"30")
			 ,(u"50" , u"50")
			 ,(u"60" , u"60")
			 ,(u"100" , u"100")
			 ,(u"500" , u"500")
			 ,(u"9999999" , u"infinit")]
		return list

####-------------------------------------------------------------------------####
	def filterscrollDelayBetweenPages(self, filter="", valuesDict=None, typeId="", devId=""):
		list=[(u"0", u"no delay")
			 ,(u"0.5", u"0.5 sec delay")
			 ,(u"1"	 , u"1 sec delay")
			 ,(u"2"	 , u"2 sec delay")
			 ,(u"3"	 , u"3 sec delay")
			 ,(u"4"	 , u"4 sec delay")
			 ,(u"5"	 , u"5 sec delay")
			 ,(u"8"	 , u"8 sec delay")
			 ,(u"10" , u"10 sec delay")
			 ,(u"15" , u"15 sec delay")
			 ,(u"20" , u"20 sec delay")]
		return list
	   
####-------------------------------------------------------------------------####
	def filterDisplayScroll(self, filter="", valuesDict=None, typeId="", devId=""):
		list=[(u"0"			   , u"no scrolling")
			 ,(u"left"		   , u"scroll to left ")
			 ,(u"right"		   , u"scroll to right")
			 ,(u"up"		   , u"scroll up ")
			 ,(u"down"		   , u"scroll down")]
		return list
		
####-------------------------------------------------------------------------####
	def filterDisplayFonts(self, filter="", valuesDict=None, typeId="", devId=""):

		fonts=	   [[u"4x6.pil","4x6 for LED display"],
					[u"5x7.pil","5x7 for LED display"],
					[u"5x8.pil","5x8 for LED display"],
					[u"6x10.pil","6x10 for LED display"],
					[u"6x12.pil","6x12 for LED display"],
					[u"6x13.pil","6x13 for LED display"],
					[u"6x13B.pil","6x138 for LED display"],
					[u"6x13O.pil","6x130 for LED display"],
					[u"6x9.pil","6x9 for LED display"],
					[u"7x13.pil","7x13 for LED display"],
					[u"7x13B.pil","7x138 for LED display"],
					[u"7x13O.pil","7x130 for LED display"],
					[u"7x14.pil","7x14 for LED display"],
					[u"7x14B.pil","7x148 for LED display"],
					[u"8x13.pil","8x13 for LED display"],
					[u"8x13B.pil","8x138 for LED display"],
					[u"8x13O.pil","8x130 for LED display"],
					[u"9x15.pil","9x15 for LED display"],
					[u"9x15B.pil","9x158 for LED display"],
					[u"9x18.pil","9x18 for LED display"],
					[u"9x18B.pil","9x188 for LED display"],
					[u"10x20.pil","10x20 for LED display"],
					[u"clR6x12.pil","clR6x12 for LED display"],
					[u"RedAlert.ttf","RedAlert small displays"],
					[u"Courier New.ttf","Courier New, Mono spaced"],
					[u"Andale Mono.ttf","Andale, Mono spaced"],
					[u"Volter__28Goldfish_29.ttf","Volter__28Goldfish_29 for small displays"],
					[u"Arial.ttf","arial for regular monitors and small displays"]]
		return fonts

 
####-------------------------------------------------------------------------####
	def filterPiI(self, valuesDict=None, filter="self", typeId="", devId="x"):

		list = []
		for pi in range(_GlobalConst_numberOfiBeaconRPI):
			if self.RPI[unicode(pi)][u"piOnOff"] != "0":
				list.append([unicode(pi), unicode(pi)])
		for pi in range(_GlobalConst_numberOfiBeaconRPI, _GlobalConst_numberOfRPI):
			if self.RPI[unicode(pi)][u"piOnOff"] != "0":
				list.append([unicode(pi), unicode(pi) ])

		return list

####-------------------------------------------------------------------------####
	def confirmPiNumberBUTTONI(self, valuesDict=None, typeId="", devId="x"):
		try:
			piN = valuesDict[u"piServerNumber"]
			nn = self.getTypeIDLength(typeId)
			valuesDict[u"piDone"]	 = True
			valuesDict[u"stateDone"] = True

			self.stateNumberForInputGPIOX = ""
			if valuesDict[u"deviceDefs"] == "":
				valuesDict[u"deviceDefs"]=json.dumps([{} for i in range(nn)])

			xxx= json.loads(valuesDict[u"deviceDefs"])
			pinMappings = ""
			nn = min(nn,len(xxx))
			for n in range(nn):
				if u"gpio" in xxx[n]:
					pinMappings += unicode(n) + ":" + xxx[n][u"gpio"] + "|"
			valuesDict[u"pinMappings"] = pinMappings
		except	Exception, e:
			self.ML.myLog( text =  u"confirmPiNumberBUTTONI in Line '%s' has error='%s'" % (sys.exc_traceback.tb_lineno, e))


		return valuesDict
		
####-------------------------------------------------------------------------####
	def getTypeIDLength(self,typeId):
		if typeId.find(u"INPUT") == -1 and	typeId.find(u"OUTPUT") == -1:
			return 0
		nn = 1
		tt = typeId.split(u"-")
		if len(tt)==1:
			tt= typeId
		else: 
			tt= tt[1]
			
		if	 tt.find(u"10") > -1: nn=10
		elif tt.find(u"12") > -1: nn=12
		elif tt.find(u"16") > -1: nn=16
		elif tt.find(u"20") > -1: nn=20
		elif tt.find(u"26") > -1: nn=26
		elif tt.find(u"1")	> -1: nn=1
		elif tt.find(u"4")	> -1: nn=4
		elif tt.find(u"8")	> -1: nn=8
		return nn

####-------------------------------------------------------------------------####
	def filterINPUTchannels(self, valuesDict=None, filter="", typeId="", devId="x"):
		list = []
		nn = self.getTypeIDLength(typeId)
		for i in range(nn):
			list.append((unicode(i), unicode(i)))
		return list


####-------------------------------------------------------------------------####
	def confirmStateBUTTONI(self, valuesDict=None, typeId="", devId="x"):
		piN	 = valuesDict[u"piServerNumber"]
		inS	 = valuesDict[u"INPUTstate"]
		inSi = int(inS)
		nn = self.getTypeIDLength(typeId)
		if valuesDict[u"deviceDefs"]!="":
			xxx=json.loads(valuesDict[u"deviceDefs"])
			if len(xxx) < nn:
				for ll in range(nn-len(xxx)):
					xxx.append({u"gpio":"", u"inpType":"", u"count": u"off"})
			if	u"gpio" in xxx[inSi] and xxx[inSi][u"gpio"] !="":
				valuesDict[u"gpio"]		 = xxx[inSi][u"gpio"]
				if	u"inpType" in xxx[inSi]:
					valuesDict[u"inpType"]	 = xxx[inSi][u"inpType"]
				valuesDict[u"count"]	 = xxx[inSi][u"count"]

		valuesDict[u"stateDone"] = True
		return valuesDict


####-------------------------------------------------------------------------####
	def confirmSelectionBUTTONI(self, valuesDict=None, typeId="", devId="x"):
			nChannels = self.getTypeIDLength(typeId)

			try:
				idevId = int(devId)
				if idevId != 0:
					dev = indigo.devices[idevId]
					props = dev.pluginProps
			except:
				dev = ""
				props = ""
				piNumberExisting = ""
				return
			piN	 = valuesDict[u"piServerNumber"]
			try:	 inSi = int(valuesDict[u"INPUTstate"])
			except:	 inSi = -1
			inS	 = str(inSi)
			gpio = "-1"
			try:	 gpio = str(int(valuesDict[u"gpio"]))
			except:	 gpio = "-1"
				
			if valuesDict[u"deviceDefs"]!="":
				xxx=json.loads(valuesDict[u"deviceDefs"])
				if len(xxx) < nChannels:
					for ll in range(nChannels-len(xxx)):
						xxx.append({u"gpio":"", u"inpType":"", u"count": u"off"})
			else:
				xxx=[]
				for ll in range(nChannels):
						xxx.append({u"gpio":"", u"inpType":"", u"count": u"off"})

			valuesDict[u"stateDone"] = True

				
			if valuesDict[u"gpio"] ==u"-1":
				xxx[inSi]={}
			else:
				if	   u"inpType" in valuesDict:
					xxx[inSi]	= {u"gpio": gpio, u"inpType": valuesDict[u"inpType"], u"count": valuesDict[u"count"]}
				else:
					xxx[inSi]	= {u"gpio": gpio,  u"inpType": u"", u"count": valuesDict[u"count"]}
				
				
			pinMappings =""
			# clean up
			for n in range(nChannels):
				if u"gpio" in xxx[n]:
					if xxx[n][u"gpio"] == u"-1" or xxx[n][u"gpio"] ==u"":
						 xxx[n]={}
						 
					pinMappings+=unicode(n)+":"+xxx[n][u"gpio"]+"|"
					for l in range(n,nChannels):
						if l==n: continue
						if u"gpio" not in xxx[l]:	continue
						if xxx[l][u"gpio"] == u"-1":  continue
						if xxx[n][u"gpio"] == xxx[l][u"gpio"]:
							pinMappings="error # "+unicode(n)+u" same pin as #"+unicode(l)
							xxx[l][u"gpio"]=u"-1"
							valuesDict[u"gpio"] == u"-1"
							break
					if u"error" in pinMappings: break


				
			valuesDict[u"pinMappings"] = pinMappings
			valuesDict[u"deviceDefs"] = json.dumps(xxx)
			return valuesDict

####-------------------------------------------------------------------------####
	def filterPiO(self, valuesDict=None, filter="self", typeId="", devId="x"):

			list = []
			for pi in range(_GlobalConst_numberOfiBeaconRPI):
				piS= unicode(pi)
				if self.RPI[piS][u"piOnOff"] != u"0":
					try:
						devId= int(self.RPI[piS][u"piDevId"])
						if devId >0:
							name= u"-"+indigo.devices[devId].name
					except: name=""
					list.append([piS,u"#"+piS+"-"+self.RPI[piS][u"ipNumberPi"]+name])

			return list

####-------------------------------------------------------------------------####
	def confirmPiNumberBUTTONO(self, valuesDict=None, typeId="", devId="x"):
			piN = valuesDict[u"piServerNumber"]
			nn = self.getTypeIDLength(typeId)
			try:
				idevId = int(devId)
				if idevId != 0:
					dev = indigo.devices[idevId]
					props = dev.pluginProps
			except:
				props = []

			valuesDict[u"piDone"] = True
			valuesDict[u"stateDone"] = False
			self.stateNumberForInputGPIOX = ""


			if valuesDict[u"deviceDefs"] == "" or len(json.loads(valuesDict[u"deviceDefs"])) != nn:
				valuesDict[u"deviceDefs"] = json.dumps([{} for i in range(nn)])

			xxx = json.loads(valuesDict[u"deviceDefs"])
			pinMappings = ""
			update= False
			for n in range(nn):
				if u"gpio" in xxx[n]:
					if u"initialValue" not in xxx[n]: 
						xxx[n][u"initialValue"] ="-"
						update= True
					pinMappings += unicode(n) + ":" + xxx[n][u"gpio"]+"," + xxx[n][u"outType"]+"," + xxx[n][u"initialValue"] + u"|"
			valuesDict[u"pinMappings"] = pinMappings
			if update:
				valuesDict[u"deviceDefs"] = json.dumps(xxx)

			return valuesDict

####-------------------------------------------------------------------------####
	def filterOUTPUTchannels(self, valuesDict=None, filter="", typeId="", devId="x"):
			list = []
			nn = self.getTypeIDLength(typeId)
			for i in range(nn):
				list.append((unicode(i), unicode(i)))
			return list

####-------------------------------------------------------------------------####
	def confirmStateBUTTONO(self, valuesDict=None, typeId="", devId="x"):
			piN = valuesDict[u"piServerNumber"]
			inS = valuesDict[u"OUTPUTstate"]
			inSi = int(inS)
			nn = self.getTypeIDLength(typeId)
			if valuesDict[u"deviceDefs"] != "":
				xxx = json.loads(valuesDict[u"deviceDefs"])
				if u"gpio" in xxx[inSi] and xxx[inSi][u"gpio"] != "":
					valuesDict[u"gpio"]	   = xxx[inSi][u"gpio"]
					valuesDict[u"outType"] = xxx[inSi][u"outType"]
					valuesDict[u"initialValue"] = xxx[inSi][u"initialValue"]

			valuesDict[u"stateDone"] = True
			return valuesDict

####-------------------------------------------------------------------------####
	def filtergpioList(self, valuesDict=None, filter="", typeId="", devId="x"):
			list = copy.deepcopy(_GlobalConst_allGPIOlist)
			return list

####-------------------------------------------------------------------------####
	def filterList16(self, valuesDict=None, filter="", typeId="", devId="x"):
			list = []
			for ii in range(16):
				list.append((ii,ii))
			return list

####-------------------------------------------------------------------------####
	def filterList12(self, valuesDict=None, filter="", typeId="", devId="x"):
			list = []
			for ii in range(12):
				list.append((ii,ii))
			return list

####-------------------------------------------------------------------------####
	def filterList10(self, valuesDict=None, filter="", typeId="", devId="x"):
			list = []
			for ii in range(10):
				list.append((ii,ii))
			return list

####-------------------------------------------------------------------------####
	def filterList8(self, valuesDict=None, filter="", typeId="", devId="x"):
			list = []
			for ii in range(8):
				list.append((ii,ii))
			return list

####-------------------------------------------------------------------------####
	def filterList4(self, valuesDict=None, filter="", typeId="", devId="x"):
			list = []
			for ii in range(4):
				list.append((ii,ii))
			return list

####-------------------------------------------------------------------------####
	def filterList1(self, valuesDict=None, filter="", typeId="", devId="x"):
			list = []
			for ii in range(1):
				list.append((ii,ii))
			return list



####-------------------------------------------------------------------------####
	def filteri2cChannelS(self, valuesDict=None, filter="", typeId="", devId="x"):
			piN = valuesDict[u"piServerNumber"]
			valuesDict[u"i2cActive"] ="test"
			return valuesDict


####-------------------------------------------------------------------------####
	def confirmSelectionBUTTONO(self, valuesDict=None, typeId="", devId="x"):
			nChannels = self.getTypeIDLength(typeId)

			try:
				idevId = int(devId)
				if idevId != 0:
					dev = indigo.devices[idevId]
					props = dev.pluginProps
			except:
				dev = ""
				props = ""
				piNumberExisting = ""
				return

			try:
				xxx = json.loads(valuesDict[u"deviceDefs"])
			except:
				xxx=[]	  
			try:
				oldxxx = json.loads(props[u"deviceDefs"])
			except:
				oldxxx = copy.deepcopy(xxx)
				for n in range(len(oldxxx)):
					oldxxx[n][u"initialValue"] ="x"
					   
			inS = valuesDict[u"OUTPUTstate"]
			inSi = int(inS)
			if valuesDict[u"gpio"] == "0":
				xxx[inSi] = {}
			else:
				xxx[inSi] = {u"gpio": valuesDict[u"gpio"],"outType": valuesDict[u"outType"],"initialValue": valuesDict[u"initialValue"]}
			#self.ML.myLog( text = "confirmSelectionBUTTONO nChannels, xx: "+unicode(nChannels)+ "	"+unicode(xxx))	   
			pinMappings = ""
			# clean up
			for n in range(nChannels):
				#self.ML.myLog( text = "n "+unicode(n) + "	"+unicode(xxx[n]))
				if u"gpio" in xxx[n]:
					if xxx[n][u"gpio"] == "0":
						del xxx[n]
					if	len(oldxxx) < (n+1) or "initialValue" not in oldxxx[n] or (xxx[n][u"initialValue"] !=	 oldxxx[n][u"initialValue"]):
						self.sendInitialValue = dev.id
					pinMappings += unicode(n) + ":" + xxx[n][u"gpio"]+ "," + xxx[n][u"outType"]+ "," +	xxx[n][u"initialValue"]+"|"
					#self.ML.myLog( text = "pinMappings: "+unicode(n)+ "  "+unicode(pinMappings))	 
					for l in range(n, nChannels):
						if l == n: continue
						if u"gpio" not in xxx[l]:	continue
						if xxx[l][u"gpio"] == "0":	continue
						if xxx[n][u"gpio"] == xxx[l][u"gpio"]:
							pinMappings = "error # " + unicode(n) + " same pin as #" + unicode(l)
							xxx[l][u"gpio"] = "0"
							valuesDict[u"gpio"] == "0"
							break
					if u"error" in pinMappings: break

			valuesDict[u"pinMappings"] = pinMappings
			valuesDict[u"deviceDefs"] = json.dumps(xxx)
			#self.ML.myLog( text = "valuesDict: "+unicode(valuesDict))	  
			return valuesDict

####-------------------------------------------------------------------------####
	def sendConfigCALLBACKaction(self, action1=None, typeId="", devId=0):
		try:
			valuesDict = action1.props
			if valuesDict[u"configurePi"] ==u"": return
			return self.execButtonConfig(valuesDict, level="0,", action=[u"updateParamsFTP"], Text="send Config Files to pi# ")
		except:
			self.ML.myLog( text =  u"sendConfigCALLBACKaction  bad rPi number:"+ unicode(valuesDict))


####-------------------------------------------------------------------------####
	def buttonConfirmSendOnlyCALLBACKaction(self, action1=None, typeId="", devId=0):
		return self.buttonConfirmSendOnlyCALLBACK(action1.props)

####-------------------------------------------------------------------------####
	def buttonConfirmSendOnlyParamsCALLBACK(self, valuesDict=None, typeId="", devId=0):
		return self.execButtonConfig(valuesDict, level="0,", action=[u"updateParamsFTP"], Text="send Config Files to pi# ")

####-------------------------------------------------------------------------####
	def buttonConfirmSendRestartPyCALLBACK(self, valuesDict=None, typeId="", devId=0):
		return self.execButtonConfig(valuesDict, level="master,", action=[u"updateParamsFTP"], Text="send Config Files and restart master.py  ")

####-------------------------------------------------------------------------####
	def buttonConfirmConfigureCALLBACK(self, valuesDict=None, typeId="", devId=0):
		return self.execButtonConfig(valuesDict, level="reboot,", action=[u"updateParamsFTP"], Text="send Config Files and restart rPI")

	def buttonUpgradeCALLBACK(self, valuesDict=None, typeId="", devId=0):
		return self.execButtonConfig(valuesDict, level="0,", action=[u"upgradeOpSysSSH"], Text="upgrade rPi")

####-------------------------------------------------------------------------####
	def buttonResetOutputCALLBACK(self, valuesDict=None, typeId="", devId=0):
		return self.execButtonConfig(valuesDict, level="0,", action=[u"resetOutputSSH"], Text="reset output file  and reboot pi# ")

####-------------------------------------------------------------------------####
	def buttonSendBigFilesCALLBACK(self, valuesDict=None, typeId="", devId=0):
		return self.execButtonConfig(valuesDict, level="master,", action=[u"updateAllFilesFTP"], Text="send ALL Files to pi# ")

####-------------------------------------------------------------------------####
	def buttonSendINITCALLBACK(self, valuesDict=None, typeId="", devId=0):
		return self.execButtonConfig(valuesDict, level="0,", action=[u"initSSH",u"updateAllFilesFTP","rebootSSH"], Text="make dirs etc on RPI, send pgms,... only once")

####-------------------------------------------------------------------------####
	def buttonShutdownCALLBACK(self, valuesDict=None, typeId="", devId=0):
		self.currentlyBooting = time.time()+self.bootWaitTime
		return self.execButtonConfig(valuesDict, level="0,", action=[u"shutdownSSH"], Text="shut down rPi#	")

####-------------------------------------------------------------------------####
	def buttonSendAllandRebootCALLBACK(self, valuesDict=None, typeId="", devId=0):
		self.currentlyBooting = time.time()+self.bootWaitTime
		return self.execButtonConfig(valuesDict, level="0,", action=[u"updateAllFilesFTP","rebootSSH"], Text="rPi configure and reboot pi# ")

####-------------------------------------------------------------------------####
	def buttonRebootCALLBACK(self, valuesDict=None, typeId="", devId=0):
		self.currentlyBooting = time.time()+self.bootWaitTime
		return self.execButtonConfig(valuesDict, level="0,", action=[u"rebootSSH"], Text="rPi reboot")

####-------------------------------------------------------------------------####
	def buttonStopConfigCALLBACK(self, valuesDict=None, typeId="", devId=0):
		return self.execButtonConfig(valuesDict, level="0,", action=[u""], Text="rPi stop Configure ")

####-------------------------------------------------------------------------####
	def buttonGetSystemParametersCALLBACK(self, valuesDict=None, typeId="", devId=0):
		return self.execButtonConfig(valuesDict, level="0,", action=[u"getStatsSSH"], Text="get stats from rpi")


####-------------------------------------------------------------------------####
	def execButtonConfig(self, valuesDict, level="0,", action=[], Text=""):
		try:
			try:
				pi = int(valuesDict[u"configurePi"])
			except:
				return valuesDict
			
			if pi == 999:
				self.setALLrPiV(u"piUpToDate", action)
				self.rPiRestartCommand = [level for ii in range(_GlobalConst_numberOfRPI)]	## which part need to restart on rpi
				self.upDateNotSuccessful = [0 for ii in range(_GlobalConst_numberOfRPI)]
				return valuesDict
			if pi < 99:
				if self.ML.decideMyLog(u"UpdateRPI"): self.ML.myLog( text =	 Text + unicode(pi)+"  action string:"+ unicode(action)	 )
				self.rPiRestartCommand[pi] = level	## which part need to restart on rpi
				self.upDateNotSuccessful[pi] = 0 
				self.setONErPiV(pi,"piUpToDate", action)
		except	Exception, e:
			self.ML.myLog( text =  u"execButtonConfig in Line '%s' has error='%s'" % (sys.exc_traceback.tb_lineno, e))
		return valuesDict


####-------------------------------------------------------------------------####
	def buttonConfirmWiFiCALLBACK(self, valuesDict=None, typeId="", devId=0):
		try:
			pi = int(valuesDict[u"configurePi"])
		except:
			return valuesDict
		for pi in range(_GlobalConst_numberOfRPI):
				if self.wifiSSID != "" and self.wifiPassword != "":
					if self.ML.decideMyLog(u"UpdateRPI"): self.ML.myLog( text =	 u"configuring WiFi on pi#" + unicode(pi))
					self.rPiRestartCommand = [u"restart" for ii in range(_GlobalConst_numberOfRPI)]	 ## which part need to restart on rpi
					self.configureWifi(pi)
				else:
					self.ML.myLog( text =  u"buttonConfirmWiFiCALLBACK configuring WiFi: SSID and password not set")

		if pi < 99:
			if self.wifiSSID != "" and self.wifiPassword != "":
				if self.ML.decideMyLog(u"UpdateRPI"): self.ML.myLog( text =	 u"configuring WiFi on pi#" + unicode(pi))
				self.rPiRestartCommand[pi] = "reboot"  ## which part need to restart on rpi
				self.configureWifi(pi)
			else:
				self.ML.myLog( text =  u"buttonConfirmWiFiCALLBACK configuring WiFi: SSID and password not set")

		return valuesDict


####-------------------------------------------------------------------------####
	def buttonShutdownHardSocketCALLBACKaction(self,  action1=None, typeId="", devId=0):
		self.buttonShutdownHardSocketCALLBACK(valuesDict=action1.props)

####-------------------------------------------------------------------------####
	def buttonShutdownHardSocketCALLBACK(self, valuesDict=None ,typeId="", devId=0):
		try:
			pi = int(valuesDict[u"configurePi"])
		except:
			return valuesDict
		if pi == 999:
			for pi in range(_GlobalConst_numberOfRPI):
				out= json.dumps([{u"command":"general","cmdLine":"sync;sleep 2;sudo killall python ;sudo halt &"}])
				self.ML.myLog( text =  u"hard shutdown of rpi  "+self.RPI[unicode(pi)][u"ipNumberPi"] +";  "+ json.dumps(out) )
				self.presendtoRPI(pi,out)
		else:
				out= json.dumps([{u"command":"general","cmdLine":"sync;sleep 2 ;sudo killall python; sudo halt &"}])
				self.ML.myLog( text =  u"hard shutdown of rpi  "+self.RPI[unicode(pi)][u"ipNumberPi"] +";  "+ json.dumps(out) )
				self.presendtoRPI(pi,out)
		return


####-------------------------------------------------------------------------####
	def buttonRebootHardSocketCALLBACKaction(self,	action1=None, typeId="", devId=0):
		self.buttonRebootHardSocketCALLBACK(valuesDict=action1.props)

####-------------------------------------------------------------------------####
	def buttonRebootHardSocketCALLBACK(self, valuesDict=None, typeId="", devId=0):
		pi = valuesDict[u"configurePi"]
		try:
			pi = int(valuesDict[u"configurePi"])
		except:
			return valuesDict
		if pi == 999:
			for pi in range(_GlobalConst_numberOfRPI):
				out= json.dumps([{u"command":"general","cmdLine":"sync;sleep 2;sudo killall python ;sudo reboot -f &"}])
				self.ML.myLog( text =  u"hard reboot of rpi	 "+self.RPI[unicode(pi)][u"ipNumberPi"] +";	 "+ json.dumps(out) )
				self.presendtoRPI(pi,out)
		else:
				out= json.dumps([{u"command":"general","cmdLine":"sync;sleep 2;sudo killall python ;sudo reboot -f &"}])
				self.ML.myLog( text =  u"hard reboot of rpi	 "+self.RPI[unicode(pi)][u"ipNumberPi"] +";	 "+ json.dumps(out) )
				self.presendtoRPI(pi,out)
		return


####-------------------------------------------------------------------------####
	def buttonRebootSocketCALLBACKaction(self,	action1=None, typeId="", devId=0):
		self.buttonRebootSocketCALLBACK(valuesDict=action1.props)

####-------------------------------------------------------------------------####
	def buttonRebootSocketCALLBACK(self, valuesDict=None, typeId="", devId=0):
		try:
			pi = int(valuesDict[u"configurePi"])
		except:
			return valuesDict
		if pi == 999:
			for pi in range(_GlobalConst_numberOfRPI):
				out= json.dumps([{u"command":"general","cmdLine":";sudo killall python; sudo reboot &"}])
				self.ML.myLog( text =  u"regular reboot of rpi	"+self.RPI[unicode(pi)][u"ipNumberPi"] +";	"+ json.dumps(out) )
				self.presendtoRPI(pi,out)
		else:
				out= json.dumps([{u"command":"general","cmdLine":";sudo killall python; sudo reboot &"}])
				self.ML.myLog( text =  u"regular reboot of rpi	"+self.RPI[unicode(pi)][u"ipNumberPi"] +";	"+ json.dumps(out) )
				self.presendtoRPI(pi,out)
		
		return


####-------------------------------------------------------------------------####
	def setTimeCALLBACKaction(self,	 action1=None, typeId="", devId=0):
		self.doActionSetTime(action1.props[u"configurePi"])# do it now
		return

####-------------------------------------------------------------------------####
	def buttonsetTimeCALLBACK(self, valuesDict=None, typeId="", devId=0):
		self.actionList.append({u"action":"setTime","value":valuesDict[u"configurePi"]}) # put it into queue and return to menu
		return

####-------------------------------------------------------------------------####
	def refreshNTPCALLBACKaction(self,	action1=None, typeId="", devId=0):
		valuesDict = action1.props
		self.buttonrefreshNTPCALLBACK(valuesDict)
		return

####-------------------------------------------------------------------------####
	def buttonrefreshNTPCALLBACK(self, valuesDict=None, typeId="", devId=0):
		valuesDict[u"anyCmdText"] = "refreshNTP"
		self.buttonAnycommandCALLBACK(valuesDict)
		return

####-------------------------------------------------------------------------####
	def stopNTPCALLBACKaction(self,	 action1=None, typeId="", devId=0):
		valuesDict = action1.props
		self.buttonstopNTPCALLBACK(valuesDict)
		return

####-------------------------------------------------------------------------####
	def buttonstopNTPCALLBACK(self, valuesDict=None, typeId="", devId=0):
		valuesDict[u"anyCmdText"] = "stopNTP"
		self.buttonAnycommandCALLBACK(valuesDict)
		return
	
	
####-------------------------------------------------------------------------####
	def doActionSetTime(self, pi):
		try: 
			piI=int(pi)
			if piI >= _GlobalConst_numberOfRPI: return 
			if piI <0:			   return 

		except: 
			self.ML.myLog( text =  u"ERROR	set time of rpi	 bad PI# given:"+unicode(pi) )
			return
			
		try: 
			
			ipNumberPi = self.RPI[pi][u"ipNumberPi"]
			goodEnoughDT  = 1.
			dt =0
			xx, retC = self.testDeltaTime( pi, ipNumberPi,dt)
			for ii in range(5):
				dt , retC  = self.testDeltaTime( pi, ipNumberPi, dt*0.9)
				if retC !=0:
					self.ML.myLog( text =  u"sync time	MAC --> RPI, did not work, no connection to RPI# "+ pi )
					return 
				if abs(dt) < 0.5: break 
				
			self.ML.myLog( text =  u"set time of RPI# "+pi+"  finished, new delta time =%6.1f"%dt+"[secs]")

		except	Exception, e:
			self.ML.myLog( text =  u"doActionSetTime in Line '%s' has error='%s'" % (sys.exc_traceback.tb_lineno, e))
		
		return

####-------------------------------------------------------------------------####
	def testDeltaTime(self, pi, ipNumberPi, tOffset):
		try: 

			dateTimeString = datetime.datetime.fromtimestamp(time.time()+ tOffset).strftime(_defaultDateStampFormat+".%f")
			out= json.dumps([{u"command":"general","cmdLine":"setTime="+dateTimeString}])
			retC = self.presendtoRPI(pi,out)
			if retC !=0: return 0, retC
			if self.ML.decideMyLog(u"UpdateRPI"):self.ML.myLog( text =	u"set time # of rpi "+pi+"	ip="+ipNumberPi+";	offset-used:%5.2f"%tOffset+";  cmd:"+ json.dumps(out) )

			self.RPI[pi][u"deltaTime1"] =-99999
			for ii in range(20):
				if self.RPI[pi][u"deltaTime1"] != -99999: break
				time.sleep(0.1)

			delta1 = self.RPI[pi][u"deltaTime1"]
			delta2 = self.RPI[pi][u"deltaTime2"]
			if abs(delta1) < 1.5 and abs(delta2) < 1.5:
				dt = abs(delta1*3.+delta2) /4.
			else:
				if abs(delta1) < abs(delta2): dt = delta1
				else:						  dt = delta2
			
			return dt, retC

		except	Exception, e:
			self.ML.myLog( text =  u"testDeltaTime in Line '%s' has error='%s'" % (sys.exc_traceback.tb_lineno, e))
		

		return 0

		
####-------------------------------------------------------------------------####
	def sendAnycommandCALLBACKaction(self, action1=None, typeId="", devId=0):
		self.buttonAnycommandCALLBACK(valuesDict=action1.props)
		return
		
####-------------------------------------------------------------------------####
	def buttonAnycommandCALLBACK(self, valuesDict=None, typeId="", devId=0):
		pi = valuesDict[u"configurePi"]
		if pi ==u"": return
		out= json.dumps([{u"command":"general","cmdLine":valuesDict[u"anyCmdText"]}])
		self.ML.myLog( text =  u"send YOUR command to rpi  "+self.RPI[unicode(pi)][u"ipNumberPi"] +";  "+ json.dumps(out) )
		self.presendtoRPI(pi,out)
		return

		
####-------------------------------------------------------------------------####
	def filterBeacons(self, valuesDict=None, filter="", typeId="", devId=0):
		list = []
		for dev in indigo.devices.iter("props.isBeaconDevice"):
				list.append((dev.id,dev.name))
		list.append((0,"delete"))
		return list

####-------------------------------------------------------------------------####
	def filterSoundFiles(self, valuesDict=None, filter="", typeId="", devId=0):
		list = []
		for fileName in os.listdir(self.userIndigoPluginDir+"/soundFiles/"):
			list.append((fileName,fileName))
		return list

####-------------------------------------------------------------------------####
	def filterSensorONoffIcons(self, valuesDict=None, filter="", typeId="", devId=0):
		list = []
		for ll in _GlobalConst_ICONLIST:
			list.append((ll[0]+"-"+ll[1],ll[0]+", u"+ll[1]))
		list.append((u"-","	 "))
		return list


####-------------------------------------------------------------------------####
	def filterPiD(self, valuesDict=None, filter="", typeId="", devId=0):
		list = []
		for pi in range(_GlobalConst_numberOfiBeaconRPI):
			if self.RPI[unicode(pi)][u"piOnOff"] == "0" or self.RPI[unicode(pi)][u"ipNumberPi"] == "":
				list.append([unicode(pi), unicode(pi) + "-"])
			else:
				list.append([unicode(pi), unicode(pi) + "-" + self.RPI[unicode(pi)][u"ipNumberPi"] + "-" + self.RPI[unicode(pi)][u"piMAC"]])
		for pi in range(_GlobalConst_numberOfiBeaconRPI,_GlobalConst_numberOfRPI):
			if self.RPI[unicode(pi)][u"piOnOff"] == "0" or self.RPI[unicode(pi)][u"ipNumberPi"] == "":
				list.append([unicode(pi), unicode(pi) + "-	  - Sensor Only"])
			else:
				list.append([unicode(pi), unicode(pi) + "-" + self.RPI[unicode(pi)][u"ipNumberPi"] + "- Sensor Only"])
		return list

####-------------------------------------------------------------------------####
	def filterPiOnlyBlue(self, valuesDict=None, filter="", typeId="", devId=0):
		list = []
		for pi in range(_GlobalConst_numberOfiBeaconRPI):
			if self.RPI[unicode(pi)][u"piOnOff"] == "0" or self.RPI[unicode(pi)][u"ipNumberPi"] == "":
				pass
			else:
				list.append([unicode(pi), unicode(pi) + "-" + self.RPI[unicode(pi)][u"ipNumberPi"] + "-" + self.RPI[unicode(pi)][u"piMAC"]])
		return list

####-------------------------------------------------------------------------####
	def filterPi(self, valuesDict=None, typeId="", devId=0):
		list = []
		for pi in range(_GlobalConst_numberOfiBeaconRPI):
			if self.RPI[unicode(pi)][u"piOnOff"] == "0" or	self.RPI[unicode(pi)][u"ipNumberPi"] == "": continue
			list.append([unicode(pi), unicode(pi) + "-" + self.RPI[unicode(pi)][u"ipNumberPi"] + "-" + self.RPI[unicode(pi)][u"piMAC"]])
		for pi in range(_GlobalConst_numberOfiBeaconRPI,_GlobalConst_numberOfRPI):
			if self.RPI[unicode(pi)][u"piOnOff"] == "0" or	self.RPI[unicode(pi)][u"ipNumberPi"] == "": continue
			list.append([unicode(pi), unicode(pi) + "-" + self.RPI[unicode(pi)][u"ipNumberPi"] + "- Sensor Only"])
		list.append([999, u"all"])
		return list

####-------------------------------------------------------------------------####
	def filterPiNoAll(self, valuesDict=None, typeId="", devId=0):
		list = []
		for pi in range(_GlobalConst_numberOfiBeaconRPI):
			if self.RPI[unicode(pi)][u"piOnOff"] == "0": continue
			if self.RPI[unicode(pi)][u"ipNumberPi"] == "": continue
			list.append([unicode(pi), unicode(pi) + "-" + self.RPI[unicode(pi)][u"ipNumberPi"] + "-" + self.RPI[unicode(pi)][u"piMAC"]])
		for pi in range(_GlobalConst_numberOfiBeaconRPI, _GlobalConst_numberOfRPI):
			if self.RPI[unicode(pi)][u"piOnOff"] == "0": continue
			if self.RPI[unicode(pi)][u"ipNumberPi"] == "": continue
			list.append([unicode(pi), unicode(pi) + "-" + self.RPI[unicode(pi)][u"ipNumberPi"] + "- Sensor Only"])
		return list

####-------------------------------------------------------------------------####
	def filterPiOUT(self, filter="", valuesDict=None, typeId="", devId=0):
		list = []
		default = ""
		for pi in range(_GlobalConst_numberOfRPI):
			if self.RPI[unicode(pi)][u"piOnOff"] == "0": continue
			if self.RPI[unicode(pi)][u"ipNumberPi"] == "": continue
			if self.RPI[unicode(pi)][u"piDevId"] == 0: continue
			devIDpi = self.RPI[unicode(pi)][u"piDevId"]
			if typeId in self.RPI[unicode(pi)][u"output"] and unicode(devId) in self.RPI[unicode(pi)][u"output"][typeId]:
				try:
					default = (unicode(pi), u"Pi-" + unicode(pi) + "-" + self.RPI[unicode(pi)][u"ipNumberPi"] + ";	Name =" + indigo.devices[devIDpi].name)
				except	Exception, e:
					self.ML.myLog( text =  u"filterPiOUT in Line '%s' has error='%s'" % (sys.exc_traceback.tb_lineno, e))
					self.ML.myLog( text =  u" devid " + unicode(devIDpi))
				continue
			else:
				try:
					list.append((unicode(pi), u"Pi-" + unicode(pi) + "-" + self.RPI[unicode(pi)][u"ipNumberPi"] + ";  Name =" + indigo.devices[devIDpi].name))
				except	Exception, e:
					self.ML.myLog( text =  u"filterPiOUT in Line '%s' has error='%s'" % (sys.exc_traceback.tb_lineno, e))
					self.ML.myLog( text =  u" devid " + unicode(devIDpi))

		if default != "":
			list.append(default)

		return list



####-------------------------------------------------------------------------####
	def filterActiveBEACONs(self, valuesDict=None, typeId="", devId=0):

		try:
			listActive = []
			for mac in self.beacons:
				if len(mac) < 5: continue
				try:
					name = indigo.devices[self.beacons[mac][u"indigoId"]].name
				except:
					continue
				if self.beacons[mac][u"ignore"] <= 0 and self.beacons[mac][u"indigoId"] != 0:
					listActive.append([mac, name + "- active, used"])
			listActive = sorted(listActive, key=lambda tup: tup[1])
		except	Exception, e:
			self.ML.myLog( text =  u"filterActiveBEACONs in Line '%s' has error='%s'" % (sys.exc_traceback.tb_lineno, e))
			listActive = []
		return listActive

####-------------------------------------------------------------------------####
	def filterMACs(self, valuesDict=None, typeId="", devId=0):

		listrejectedByPi = []
		listActive		 = []
		listDeleted		 = []
		listIgnored		 = []
		listOldIgnored	 = []

		if False:
			try:
				f = open(self.userIndigoPluginDir + "rejected/rejectedByPi.json", u"r")
				self.rejectedByPi = json.loads(f.read())
				f.close()
			except:
				self.rejectedByPi = {}


			for mac in self.rejectedByPi:
				if len(mac) < 5: continue
				try:
					uuid = self.rejectedByPi[mac][u"uuid"]
				except:
					continue
				listrejectedByPi.append([mac, mac + "- ignored on pi -" + uuid])
			listrejectedByPi = sorted(listrejectedByPi, key=lambda tup: tup[1])

		for mac in self.beacons:
			if len(mac) < 5: continue
			try:
				name = indigo.devices[self.beacons[mac][u"indigoId"]].name
			except:
				name = mac
			if self.beacons[mac][u"ignore"] <= 0 and self.beacons[mac][u"indigoId"] != 0:
				listActive.append([mac, name + "- active, used"])
		listActive = sorted(listActive, key=lambda tup: tup[1])

		for mac in self.beacons:
			if len(mac) < 5: continue
			try:
				name = indigo.devices[self.beacons[mac][u"indigoId"]].name
			except:
				name = mac
			if self.beacons[mac][u"ignore"] == 0 and self.beacons[mac][u"indigoId"] == 0:
				listDeleted.append([mac, name + "- deleted previously"])
		listDeleted = sorted(listDeleted, key=lambda tup: tup[1])

		for mac in self.beacons:
			if len(mac) < 5: continue
			try:
				name = indigo.devices[self.beacons[mac][u"indigoId"]].name
			except	Exception, e:
				if unicode(e).find(u"timeout waiting") > -1:
					self.ML.myLog( text =  u"filterMACs in Line '%s' has error='%s'" % (sys.exc_traceback.tb_lineno, e))
					self.ML.myLog( text =  u"communication to indigo is interrupted")
					return
				name = mac

			if self.beacons[mac][u"ignore"] == 1:
				listIgnored.append([mac, name + "- on ignoredList"])
		listIgnored = sorted(listIgnored, key=lambda tup: tup[1])

		for mac in self.beacons:
			if len(mac) < 5: continue
			if self.beacons[mac][u"ignore"] == 2:
				listOldIgnored.append([mac, mac + "- on ignoredList- old"])
		listOldIgnored = sorted(listOldIgnored, key=lambda tup: tup[1])

		return listrejectedByPi + listOldIgnored + listDeleted + listIgnored + listActive


####-------------------------------------------------------------------------####
	def filterRPIs(self, valuesDict=None, typeId="", devId=0):

		listActive = []
		for dev in indigo.devices.iter("props.isRPIDevice"):
			if dev.deviceTypeId !="rPI": continue
			try:
				indigoId = dev.id
				props = dev.pluginProps
				if u"note" not in dev.states: continue
				if dev.states[u"note"].find(u"Pi-") == -1: continue
				try: 
					if int(dev.states[u"note"].split(u"-")[1]) > 9: continue
				except: pass
				
				dev	 = indigo.devices[indigoId]
				name = dev.name
				mac	 = dev.description
				listActive.append([str(indigoId), name+"-"+mac ])
				
			except:
				pass
		listActive = sorted(listActive, key=lambda tup: tup[1])


		return listActive


####-------------------------------------------------------------------------####
	def filterUUIDiphone(self, valuesDict=None, typeId="", devId=0):
		list0 = []
		for dev in indigo.devices.iter("props.isBeaconDevice"):
			try:
				beacon = dev.pluginProps[u"address"]
				uuid   = dev.states[u"UUID"]
				name   = dev.name
			except:
				continue

			ff =  self.findUUIDcompare(uuid,self.beaconsUUIDtoIphone, self.constantUUIDmajMIN,self.lenOfUUID)
			if ff ==-1: continue
			
			if ff ==0:
					list0.append((dev.id, u"already defined: " +name + "  UUID: " + uuid))
			else:
					list0.append((dev.id, u"	  available: " +name + "  UUID: " + uuid))

		list0 = sorted(list0, key=lambda tup: tup[1])

		return list0
		

####-------------------------------------------------------------------------####
	def findUUIDcompare(self,uuid,UUIDtoIphone, constantUUIDmajMIN,lenOfUUID):

			ok, UUid = self.setUUIDcompare(uuid,constantUUIDmajMIN,lenOfUUID)
			if not ok: return -1 
			for mac in self.beaconsUUIDtoIphone:
				ok, UUID = self.setUUIDcompare(self.beaconsUUIDtoIphone[mac][0],constantUUIDmajMIN,lenOfUUID)
				if UUid == UUID: 
					return 0
			return 1
		
####-------------------------------------------------------------------------####
	def setUUIDcompare(self,uuid, constantUUIDmajMIN,lenOfUUID):
		UUIDx = uuid.split(u"-")
		UUid  = uuid
		if len(UUIDx)	 !=3:			return False, UUid
		if len(UUIDx[0]) != lenOfUUID:	return False, UUid
		if	 constantUUIDmajMIN	 == "uuid--min":	UUid = UUIDx[0] + "--"+ UUIDx[2]
		elif constantUUIDmajMIN	 == "uuid-maj-":	UUid = UUIDx[0] + "-" + UUIDx[1] + "-"
		elif constantUUIDmajMIN	 == "uuid--":		UUid = UUIDx[0]
		return True, UUid



####-------------------------------------------------------------------------####
	def filterUUIDName(self, valuesDict=None, typeId="", devId=0):
		list0 = []
		list1 = {}
		for dev in indigo.devices.iter("props.isRPIDevice,props.isBeaconDevice"):
			props = dev.pluginProps
			try:
				uuid = dev.states[u"UUID"]
				if dev.deviceTypeId != "beacon" and dev.deviceTypeId != "rPI": continue
				try:
					uuid = uuid.split(u"-")[0]
				except:
					pass
				if uuid == "": uuid = "."
				if uuid in self.beaconsUUIDtoName:
					name = self.beaconsUUIDtoName[uuid]
				else:
					name = "--"
				if uuid not in list1:
					list1[uuid] = 1
					list0.append((uuid, name+ "-"+ uuid ))
			except:
				continue

		list0 = sorted(list0, key=lambda tup: tup[1])
		#self.ML.myLog( text =	unicode(list0))
		return list0

####-------------------------------------------------------------------------####
	def filterUUIDNameExisting(self, valuesDict=None, typeId="", devId=0):
		list0 = []
		for uuid in self.beaconsUUIDtoName:
			if uuid != "" and self.beaconsUUIDtoName != "":
				list0.append([uuid, self.beaconsUUIDtoName[uuid]+"-"+ uuid])
		list0 = sorted(list0, key=lambda tup: tup[1])
		return list0




####-------------------------------------------------------------------------####
	def buttonconfirmPreselectCALLBACK(self, valuesDict=None, typeId="", devId=0):
		try:
			self.constantUUIDmajMIN = valuesDict[u"constantUUIDmajMIN"]
			try: self.lenOfUUID		= int(valuesDict[u"lenOfUUID"])
			except: self.lenOfUUID	=  32
		except	Exception, e:
			self.ML.myLog( text =  u"buttonconfirmPreselectCALLBACK in Line '%s' has error='%s'" % (sys.exc_traceback.tb_lineno, e))
			return valuesDict

		#self.ML.myLog( text = json.dumps(self.beaconsUUIDtoIphone))
		return valuesDict
####-------------------------------------------------------------------------####
	def buttonconfirmUUIDiphoneNameCALLBACK(self, valuesDict=None, typeId="", devId=0):
		try:
			id = int(valuesDict[u"selectUUIDiphone"])
			if id > 0:
				dev		= indigo.devices[id]
				uuid	= dev.states[u"UUID"]
				beacon	= dev.pluginProps[u"address"]
				if beacon in self.beaconsUUIDtoIphone:
					valuesDict[u"nameForIphone"] = self.beaconsUUIDtoIphone[beacon][3]
				
		except	Exception, e:
			self.ML.myLog( text =  u"buttonconfirmUUIDiphoneNameCALLBACK in Line '%s' has error='%s'" % (sys.exc_traceback.tb_lineno, e))

		return valuesDict

####-------------------------------------------------------------------------####
	def buttonConfirmSelectIphoneUUIDtoMACCALLBACK(self, valuesDict=None, typeId="", devId=0):
		try:
			id = int(valuesDict[u"selectUUIDiphone"])
			self.constantUUIDmajMIN = valuesDict[u"constantUUIDmajMIN"]
			self.lenOfUUID			= int(valuesDict[u"lenOfUUID"])
			if id > 0:
				dev		= indigo.devices[id]
				uuid	= dev.states[u"UUID"]
				beacon	= dev.pluginProps[u"address"]
				self.beaconsUUIDtoIphone[beacon]=[uuid,self.constantUUIDmajMIN,self.lenOfUUID, valuesDict[u"nameForIphone"]]
				ff =  self.findUUIDcompare(uuid,self.beaconsUUIDtoIphone, self.constantUUIDmajMIN,self.lenOfUUID)
				if ff == 1 or ff ==0: 
					for pi in range(_GlobalConst_numberOfiBeaconRPI):
						self.setONErPiV(pi,"piUpToDate", [u"updateParamsFTP"])
						self.upDateNotSuccessful[pi]= 0
				valuesDict[u"nameForIphone"] = self.beaconsUUIDtoIphone[beacon][3]
				
		except	Exception, e:
			self.ML.myLog( text =  u"buttonConfirmSelectIphoneUUIDtoMACCALLBACK in Line '%s' has error='%s'" % (sys.exc_traceback.tb_lineno, e))
			return valuesDict

		self.ML.myLog( text =  u"buttonConfirmSelectIphoneUUIDtoMACCALLBACK: UUIDtoIphone=" + unicode(self.beaconsUUIDtoIphone))
		#self.ML.myLog( text = json.dumps(self.beaconsUUIDtoIphone))
		return valuesDict

####-------------------------------------------------------------------------####
	def buttonConfirmDeleteUUIDtoMACCALLBACK(self, valuesDict=None, typeId="", devId=0):
		try:
			id = int(valuesDict[u"selectUUIDiphone"])
			if id > 0:
				dev = indigo.devices[id]
				uuid = dev.states[u"UUID"]
				beacon = dev.pluginProps[u"address"]
				ff =  self.findUUIDcompare(uuid,self.beaconsUUIDtoIphone, self.constantUUIDmajMIN,self.lenOfUUID)
				if ff==0:
					del self.beaconsUUIDtoIphone[beacon]
					for pi in range(_GlobalConst_numberOfiBeaconRPI):
						self.setONErPiV(pi,"piUpToDate", [u"updateParamsFTP"])
						self.upDateNotSuccessful[pi] = 0

		except	Exception, e:
			self.ML.myLog( text =  u"buttonConfirmDeleteUUIDtoMACCALLBACK in Line '%s' has error='%s'" % (sys.exc_traceback.tb_lineno, e))
			return valuesDict

		#self.ML.myLog( text = json.dumps(self.beaconsUUIDtoIphone))
		return valuesDict

 
 
 
 ###-------------------------------------------------------------------------####
	def buttonConfirmSelectUUIDtoNameCALLBACK(self, valuesDict=None, typeId="", devId=0):
		uuid = valuesDict[u"selectUUID"]
		uname = valuesDict[u"uuidtoName"]
		if uuid != "" and uname != "":
			self.beaconsUUIDtoName[uuid] = uname

		#self.ML.myLog( text = json.dumps(self.beaconsUUIDtoName))
		return valuesDict

####-------------------------------------------------------------------------####
	def buttonConfirmDeleteUUIDtoNameCALLBACK(self, valuesDict=None, typeId="", devId=0):
		uuid = valuesDict[u"selectUUIDexistingMap"]
		if uuid != "":
			if uuid in self.beaconsUUIDtoName:
				del self.beaconsUUIDtoName[uuid]

		#self.ML.myLog( text = json.dumps(self.beaconsUUIDtoName))
		return valuesDict



####-------------------------------------------------------------------------####
	def mapNametoUUID(self, name):
		try:
			for uuid in self.beaconsUUIDtoName:
				if name == self.beaconsUUIDtoName[uuid]:
					return uuid
			return ""
		except	Exception, e:
			self.ML.myLog( text =  u"mapNametoUUID in Line '%s' has error='%s'" % (sys.exc_traceback.tb_lineno, e))
		return uuid



####-------------------------------------------------------------------------####
	def mapUUIDtoName(self, uuid, typeId="beacon"):
		try:
			if uuid == "x-x-x":		return -1,uuid
			if typeId != "beacon":	return	1,uuid
			u = uuid.split(u"-")
			if len(u) != 3:			return -1,uuid
			if u[0] in self.beaconsUUIDtoName:
					return 0, self.beaconsUUIDtoName[u[0]] + "-" + u[1] + "-" + u[2]
			return 1, uuid
		except	Exception, e:
			self.ML.myLog( text =  u"mapUUIDtoName in Line '%s' has error='%s'" % (sys.exc_traceback.tb_lineno, e))
		return 1, uuid

####-------------------------------------------------------------------------####
	def mapMACtoiPhoneUUID(self, mac, uuid, typeId="beacon"):
		try:
			if uuid == "x-x-x":					return -1, u""
			if typeId != "beacon":				return	1, uuid
			u = uuid.split(u"-")
			if len(u) != 3:						return -1, u""
			if mac not in self.beaconsUUIDtoIphone:	   return  1, uuid
			if self.beaconsUUIDtoIphone[mac][3] == "":		return	1, uuid
			return 0, self.beaconsUUIDtoIphone[mac][3]+ "-" + u[1] + "-" + u[2]
		except	Exception, e:
			self.ML.myLog( text =  u"mapMACtoiPhoneUUID in Line '%s' has error='%s'" % (sys.exc_traceback.tb_lineno, e))
		return 1,uuid



####-------------------------------------------------------------------------####
	def buttonConfirmnewBeaconsLogTimerCALLBACK(self, valuesDict=None, typeId="", devId=0):
		try:
			xx = float(valuesDict[u"newBeaconsLogTimer"])
			if xx > 0: 
				self.newBeaconsLogTimer = time.time() + xx*60
				self.ML.myLog( text =  u"newBeaconsLogTimer set to: " +valuesDict[u"newBeaconsLogTimer"] +" minutes")
			else:
				self.newBeaconsLogTimer = 0
		except	Exception, e:
			self.ML.myLog( text =  u"buttonConfirmnewBeaconsLogTimerCALLBACK in Line '%s' has error='%s'" % (sys.exc_traceback.tb_lineno, e))
			self.newBeaconsLogTimer = 0
		return valuesDict
					
			
####-------------------------------------------------------------------------####
	def buttonConfirmSelectBeaconCALLBACK(self, valuesDict=None, typeId="", devId=0):
		try:
			id	= self.beacons[valuesDict[u"selectBEACON"]][u"indigoId"]
			len = int(valuesDict[u"selectBEACONlen"])
			dev = indigo.devices[int(id)]
		except	Exception, e:
			self.ML.myLog( text =  u"buttonConfirmSelectBeaconCALLBACK in Line '%s' has error='%s'" % (sys.exc_traceback.tb_lineno, e))
			return valuesDict
		self.ML.myLog( text = "log messages for	 beacon:"+dev.name +" mac:"+valuesDict[u"selectBEACON"][:len])
		self.selectBeaconsLogTimer[valuesDict[u"selectBEACON"]]	 = len
		return valuesDict
					
			
####-------------------------------------------------------------------------####
	def buttonConfirmStopSelectBeaconCALLBACK(self, valuesDict=None, typeId="", devId=0):
		self.selectBeaconsLogTimer ={}
		return valuesDict
					
			
			
####-------------------------------------------------------------------------####
	def buttonConfirmselectLargeChangeInSignalCALLBACK(self, valuesDict=None, typeId="", devId=0):
		xx =  valuesDict[u"trackSignalStrengthIfGeaterThan"].split(u",")
		self.trackSignalStrengthIfGeaterThan = [float(xx[0]),xx[1]]
		if xx[1] ==u"i":
			self.ML.myLog( text = "log messages for beacons with signal strength change GT "+ unicode(self.trackSignalStrengthIfGeaterThan[0])+";  including ON->off and off-ON")
		else:
			self.ML.myLog( text = "log messages for beacons with signal strength change GT "+ unicode(self.trackSignalStrengthIfGeaterThan[0])+";  excluding ON->off and off-ON")
		return valuesDict
			
####-------------------------------------------------------------------------####
	def buttonConfirmselectChangeOfRPICALLBACK(self, valuesDict=None, typeId="", devId=0):
		self.trackSignalChangeOfRPI = valuesDict[u"trackSignalChangeOfRPI"] ==u"1"
		self.ML.myLog( text = "log messages for beacons that change closest RPI: "+ unicode(self.trackSignalChangeOfRPI))
		return valuesDict


####-------------------------------------------------------------------------####
	def buttonExecuteReplaceBeaconCALLBACK(self, valuesDict=None, typeId="", devId=0):
	
		try:

			oldMAC = valuesDict[u"oldMAC"]
			newMAC = valuesDict[u"newMAC"]
			oldINDIGOid = self.beacons[oldMAC][u"indigoId"]
			newINDIGOid = self.beacons[newMAC][u"indigoId"]
			oldDEV = indigo.devices[oldINDIGOid]
			newDEV = indigo.devices[newINDIGOid]
			oldName = oldDEV.name
			newName = newDEV.name
			oldPROPS = oldDEV.pluginProps
			 
			if oldDEV.states[u"status"].lower() != "expired":
				self.ML.myLog( text = "ERROR can not replace existing active beacon; " + oldName+"	still active")
				valuesDict[u"msg"] = "ERROR can not replace existing ACTIVE beacon"
				return valuesDict
			if oldMAC == newMAC:
				self.ML.myLog( text = "ERROR, can't replace itself")
				valuesDict[u"msg"] = "ERROR,choose 2 different beacons"
				return valuesDict

			oldPROPS[u"address"] = newMAC
			oldDEV.replacePluginPropsOnServer(oldPROPS)
		
			self.beacons[newMAC] = copy.deepcopy(self.beacons[oldMAC])
			self.beacons[newMAC][u"indigoId"] = oldINDIGOid
			del self.beacons[oldMAC]
			indigo.device.delete(newDEV)

			self.ML.myLog( text = "=== replaced MAC number "+oldMAC+"  of device "+oldName +" with "+ newMAC+" --	and deleted device "+newName+"	===" )
			valuesDict[u"msg"] = "replaced, moved MAC number"

		except	Exception, e:
			self.ML.myLog( text =  u"buttonExecuteReplaceBeaconCALLBACK in Line '%s' has error='%s'" % (sys.exc_traceback.tb_lineno, e))
		return valuesDict

####-------------------------------------------------------------------------####
	def buttonExecuteReplaceRPICALLBACK(self, valuesDict=None, typeId="", devId=0):
	
		try:

			oldID = valuesDict[u"oldID"]
			newID = valuesDict[u"newID"]
			if oldID == newID: 
				valuesDict[u"msg"] = "must use 2 different RPI"
				return

			oldDEV	 = indigo.devices[int(oldID)]
			newDEV	 = indigo.devices[int(newID)]
			oldName	 = oldDEV.name
			newName	 = newDEV.name
			oldPROPS = oldDEV.pluginProps
			newPROPS = newDEV.pluginProps
			oldMAC	 =	copy.deepcopy(oldPROPS[u"address"])
			newMAC	 =	copy.deepcopy(newPROPS[u"address"])

			oldPROPS[u"address"] = newMAC
			oldDEV.replacePluginPropsOnServer(oldPROPS)
			newPROPS[u"address"] = newMAC[:-1]+"x"
			newDEV.replacePluginPropsOnServer(newPROPS)


			self.beacons[newMAC] = self.beacons[oldMAC]
			self.beacons[newMAC][u"indigoId"]= oldDEV.id

			if oldMAC not in self.beacons:
				self.beacons[oldMAC] = copy.deepcopy(_GlobalConst_emptyRPI)
			self.beacons[oldMAC][u"indigoId"]= newDEV.id

			
			try:
				piN = oldDEV.states[u"note"].split(u"-")[1]
				self.RPI[piN][u"piMAC"] = newMAC
			except:
				pass
				
			self.fixConfig(checkOnly = ["all","rpi"],fromPGM="buttonExecuteReplaceRPICALLBACK")
			self.ML.myLog( text = "=== replaced MAC number "+oldMAC+"  of device "+oldName +" with "+ newMAC+" --	and deleted device "+newName+"	===" )
			valuesDict[u"msg"] = "replaced, moved MAC number"

		except	Exception, e:
			self.ML.myLog( text =  u"buttonExecuteReplaceRPICALLBACK in Line '%s' has error='%s'" % (sys.exc_traceback.tb_lineno, e))
		return valuesDict

####-------------------------------------------------------------------------####
	def inpDummy(self, valuesDict=None, typeId="", devId=0):
		return

####-------------------------------------------------------------------------####
	def buttonConfirmMACIgnoreCALLBACK(self, valuesDict=None, typeId="", devId=0):
		mac = valuesDict[u"ignoreMAC"]
		if mac in self.beacons:
			if self.beacons[mac][u"ignore"] == 0:
				self.beacons[mac][u"ignore"] = 1
				self.newIgnoreMAC += 1

				for pi in range(_GlobalConst_numberOfiBeaconRPI):
					self.setONErPiV(pi,"piUpToDate", [u"updateParamsFTP"])
					self.upDateNotSuccessful[pi] = 0
		else:
			self.beacons[mac] = copy.deepcopy(_GlobalConst_emptyBeacon)
			self.beacons[mac][u"ignore"] = 1
			self.newIgnoreMAC += 1
			self.beacons[mac][u"created"] = datetime.datetime.now().strftime(_defaultDateStampFormat)
		self.ML.myLog( text =  u"setting "+mac+" indigoId: "+ unicode(self.beacons[mac][u"indigoId"])+" to ignore -mode: "+ unicode(self.beacons[mac][u"ignore"]) )
		self.beacons[mac][u"status"] = "ignored"	
		if self.beacons[mac][u"indigoId"] >0: 
			try:
				indigo.device.delete(indigo.devices[self.beacons[mac][u"indigoId"]])
			except:
				pass
		self.makeBeacons_parameterFile()
		for pi in range(_GlobalConst_numberOfiBeaconRPI):
			self.setONErPiV(pi,"piUpToDate", [u"updateParamsFTP"])
			self.upDateNotSuccessful[pi] = 0
		
			
		return valuesDict

####-------------------------------------------------------------------------####
	def buttonConfirmMACunIgnoreCALLBACK(self, valuesDict=None, typeId="", devId=0):
		mac = valuesDict[u"ignoreMAC"]
		if mac in self.beacons:
			if self.beacons[mac][u"ignore"] != 0:
				self.beacons[mac][u"ignore"] = 0
				if self.beacons[mac][u"indigoId"] ==0:
					self.beacons[mac][u"ignore"] = -1
				self.newIgnoreMAC += 1
		else:
			self.newIgnoreMAC += 1
			self.beacons[mac] = copy.deepcopy(_GlobalConst_emptyBeacon)
			self.beacons[mac][u"ignore"] = 0
			self.beacons[mac][u"created"] = datetime.datetime.now().strftime(_defaultDateStampFormat)
			
			if mac in self.rejectedByPi:
				self.beacons[mac][u"ignore"] = -1  # must not be ignored
				del self.rejectedByPi[mac]
				try:
					f = open(self.userIndigoPluginDir + "rejected/rejectedByPi.json", u"w")
					f.write(json.dumps(self.rejectedByPi))
					f.close()
				except:
					pass
		self.ML.myLog( text =  u"setting "+mac+" indigoId: "+ unicode(self.beacons[mac][u"indigoId"])+" to un-ignore -mode: "+ unicode(self.beacons[mac][u"ignore"]) )
		if self.beacons[mac][u"indigoId"] ==0:
			self.createNewiBeaconDeviceFromBeacons(mac)

		self.makeBeacons_parameterFile()
		for pi in range(_GlobalConst_numberOfiBeaconRPI):
			self.setONErPiV(pi,"piUpToDate", [u"updateParamsFTP"])
			self.upDateNotSuccessful[pi] = 0

		return valuesDict

####-------------------------------------------------------------------------####
	def createNewiBeaconDeviceFromBeacons(self, mac):
		try:
			name = "beacon_" + mac
			dev= indigo.device.create(
				protocol		= indigo.kProtocol.Plugin,
				address			= mac,
				name			= name,
				description		= "a-a-a",
				pluginId		= self.pluginId,
				deviceTypeId	= "beacon",
				folder			= self.piFolderId,
				props		   = {
					   u"typeOfBeacon":				 _GlobalConst_emptyBeaconProps[u"typeOfBeacon"],
					   u"updateSignalValuesSeconds": _GlobalConst_emptyBeaconProps[u"updateSignalValuesSeconds"],
					   u"expirationTime":			 _GlobalConst_emptyBeaconProps[u"expirationTime"],
					   u"fastDown":					 _GlobalConst_emptyBeaconProps[u"fastDown"],
					   u"signalDelta":				 _GlobalConst_emptyBeaconProps[u"signalDelta"],
					   u"minSignalCutoff":			 _GlobalConst_emptyBeaconProps[u"minSignalCutoff"],
					   u"beaconTxPower":			 _GlobalConst_emptyBeaconProps[u"beaconTxPower"],
					   u"isBeaconDevice" :			 True,
					   u"SupportsBatteryLevel":		 False,
					   u"UUID":						 u""}
				)
			self.beacons[mac][u"indigoId"] = dev.id

		except	Exception, e:
				if unicode(e).find(u"timeout waiting") > -1:
					self.ML.myLog( text =  u"createNewiBeaconDeviceFromBeacons in Line '%s' has error='%s'" % (sys.exc_traceback.tb_lineno, e))



####-------------------------------------------------------------------------####
	def buttonConfirmMACDeleteCALLBACK(self, valuesDict=None, typeId="", devId=0):
		mac = valuesDict[u"ignoreMAC"]
		if mac in self.beacons:
			for pi in range(_GlobalConst_numberOfiBeaconRPI):
				self.setONErPiV(pi,"piUpToDate", [u"updateParamsFTP"])
				self.upDateNotSuccessful[pi] = 0
			del self.beacons[mac]
		self.fixConfig(checkOnly = ["all","rpi"],fromPGM="buttonConfirmMACDeleteCALLBACK")
		return valuesDict

####-------------------------------------------------------------------------####
	def buttonConfirmMACDeleteALLCALLBACK(self, valuesDict=None, typeId="", devId=0):
		self.beacons = {}
		self.fixConfig(checkOnly = ["all","rpi"],fromPGM="buttonConfirmMACDeleteALLCALLBACK")
		for pi in range(_GlobalConst_numberOfiBeaconRPI):
			self.setONErPiV(pi,"piUpToDate", [u"updateParamsFTP"])
			self.upDateNotSuccessful[pi] = 0
		try:
			os.system(u"rm "+ self.userIndigoPluginDir + "rejected/reject-1" )
			os.system(u"cp "+ self.userIndigoPluginDir + "rejected/rejects "+ self.userIndigoPluginDir + "rejected/reject-1" )
			os.system(u"rm "+ self.userIndigoPluginDir + "rejected/rejects*" )
		except: pass
		return valuesDict

####-------------------------------------------------------------------------####

### not used 
	def buttonConfirmMACnonactiveCALLBACK(self, valuesDict=None, typeId="", devId=0):
		delB = []
		ll0 = len(self.beacons)
		for beacon in self.beacons:
			if self.beacons[beacon][u"indigoId"] != 0:		  continue
			if int(self.beacons[beacon][u"ignore"]) == 0:		   continue
			delB.append(beacon)

		for beacon in delB:
			del self.beacons[beacon]

		try:
			f = open(self.userIndigoPluginDir + "rejected/rejectedByPi.json", u"r")
			self.rejectedByPi = json.loads(f.read())
			f.close()
		except:
			self.rejectedByPi = {}

		delB=[]
		for mac in self.rejectedByPi:
			if mac not in self.beacons:
				delB.append(mac)
		for mac in delB:
			self.ML.myLog( text =  u"removing "+mac+" from rejected history ")
			del self.rejectedByPi[mac]
			
		try:
			f = open(self.userIndigoPluginDir + "rejected/rejectedByPi.json", u"w")
			f.write(json.dumps(self.rejectedByPi))
			f.close()
			os.system(u"rm "+ self.userIndigoPluginDir + "rejected/reject-1" )
			os.system(u"cp "+ self.userIndigoPluginDir + "rejected/rejects "+ self.userIndigoPluginDir + "rejected/reject-1" )
			os.system(u"rm "+ self.userIndigoPluginDir + "rejected/rejects*" )
			self.ML.myLog( text =  u"old rejected/rejects file renamed to"+self.userIndigoPluginDir+" rejected/reject-1")
		except: pass


		self.fixConfig(checkOnly = ["all","rpi"],fromPGM="buttonConfirmMACnonactiveCALLBACK")
		ll2 = len(self.beacons)
		self.ML.myLog( text =  u"from initially good "+unicode(ll0)+" beacons # of beacons removed from BEACONlist: "+ unicode(ll0-ll2) )
		

####-------------------------------------------------------------------------####
	def buttonConfirmMACDeleteOLDHISTORYCALLBACK(self, valuesDict=None, typeId="", devId=0):
		delB = []
		ll0 = len(self.beacons)
		for beacon in self.beacons:
			if self.beacons[beacon][u"indigoId"] != 0:
				try:
					dd= indigo.devices[self.beacons[beacon][u"indigoId"]]
					continue
				except	Exception, e:
					if unicode(e).find(u"timeout waiting") >-1: continue
					self.ML.myLog( text =  u"buttonConfirmMACDeleteOLDHISTORYCALLBACK in Line '%s' has error='%s'" % (sys.exc_traceback.tb_lineno, e))

			#if int(self.beacons[beacon][u"ignore"]) != 2:			continue
			delB.append(beacon)

		for beacon in delB:
			self.ML.myLog( text =  u"deleting beacon="+beacon+" from (deleted/ignored) history .. can be used again" )
			del self.beacons[beacon]
			
		delB=[]
		for mac in self.rejectedByPi:
			if mac not in self.beacons:
				delB.append(mac)
		for mac in delB:
			#self.ML.myLog( text =	u"removing "+mac+" from rejected file ")
			del self.rejectedByPi[mac]
			
		try:
			f = open(self.userIndigoPluginDir + "rejected/rejectedByPi.json", u"r")
			self.rejectedByPi = json.loads(f.read())
			f.close()
		except:
			self.rejectedByPi = {}
	 
		try:
			f = open(self.userIndigoPluginDir + "rejected/rejectedByPi.json", u"w")
			f.write(json.dumps(self.rejectedByPi))
			f.close()
			os.system(u"rm "+ self.userIndigoPluginDir + "rejected/reject-1" )
			os.system(u"cp "+ self.userIndigoPluginDir + "rejected/rejects "+ self.userIndigoPluginDir + "rejected/reject-1" )
			os.system(u"rm "+ self.userIndigoPluginDir + "rejected/rejects*" )
			self.ML.myLog( text =  u"old rejected/rejects file renamed to"+self.userIndigoPluginDir+" rejected/reject-1")
		except: pass


		self.fixConfig(checkOnly = ["all","rpi"],fromPGM="buttonConfirmMACDeleteOLDHISTORYCALLBACK")
		ll2 = len(self.beacons)
		self.ML.myLog( text =  u"from initially good "+unicode(ll0)+" beacons # of beacons removed from BEACONlist: "+ unicode(ll0-ll2) )

		return valuesDict
		
####-------------------------------------------------------------------------####
	def buttonSetAllExistingDevicesToActiveCALLBACK(self, valuesDict=None, typeId="", devId=0):
		for beacon in self.beacons:
			if self.beacons[beacon][u"indigoId"] != 0: 
				self.beacons[beacon][u"ignore"] = 0
				try:
					dev = indigo.devices[int(self.beacons[beacon][u"indigoId"])]
					props = dev.pluginProps
					props[u"ignore"] = "0"
					dev.replacePluginPropsOnServer(props)
				except:
					pass
		self.ML.myLog( text =  u"set all existing iBeacon devices to active")

		return valuesDict


####-------------------------------------------------------------------------####
	def filterMACfamilies(self, valuesDict=None, typeId="", devId=0):
		list0 = []
		for uuid in self.beaconsIgnoreUUID:
			if uuid == "": continue
			list0.append((uuid, u"UUID family already ignored: " + uuid))  # 1a13ff4c00 up to here0c0e00931210948d9701e5
		list0 = sorted(list0, key=lambda tup: tup[0])

		list1 = []
		for mac in self.beacons:
			if len(mac) < 5: continue
			try:
				dev = indigo.devices[self.beacons[mac][u"indigoId"]]
				name = dev.name
				note12 = dev.description[:12]
				if note12 == "": continue
				list1.append([note12, name + "	UUID: " + note12])
			except	Exception, e:
				if unicode(e).find(u"timeout waiting") > -1:
					self.ML.myLog( text =  u"filterMACfamilies in Line '%s' has error='%s'" % (sys.exc_traceback.tb_lineno, e))
					self.ML.myLog( text =  u"communication to indigo is interrupted")
					return

		list1 = sorted(list1, key=lambda tup: tup[1])
		if self.ML.decideMyLog(u"Logic"): self.ML.myLog( text =	 u" family list:" + unicode(list0 + list1))

		return list0 + list1

####-------------------------------------------------------------------------####
	def buttonConfirmMACIgnoreFamilyCALLBACK(self, valuesDict=None, typeId="", devId=0):
		uuid = valuesDict[u"ignoreMACfamily"]
		if uuid not in self.beaconsIgnoreUUID:
			self.beaconsIgnoreUUID[uuid]=True # 1a13ff4c00 up to here0c0e00931210948d9701e5
			self.setALLrPiV(u"piUpToDate", [u"updateParamsFTP"])
			self.upDateNotSuccessful =[0 for ii in range(_GlobalConst_numberOfRPI)]
		return valuesDict

####-------------------------------------------------------------------------####
	def buttonConfirmMACunIgnoreFamilyCALLBACK(self, valuesDict=None, typeId="", devId=0):
		uuid = valuesDict[u"ignoreMACfamily"]
		if uuid in self.beaconsIgnoreUUID:
			del self.beaconsIgnoreUUID[uuid]
			self.upDateNotSuccessful = [0 for ii in range(_GlobalConst_numberOfRPI)]
			self.setALLrPiV(u"piUpToDate", [u"updateParamsFTP"])

####-------------------------------------------------------------------------####
	def buttonConfirmMACemptyFamilyCALLBACK(self, valuesDict=None, typeId="", devId=0):
		self.beaconsIgnoreUUID = {}
		for pi in range(_GlobalConst_numberOfiBeaconRPI):
			self.setONErPiV(pi,"piUpToDate", [u"updateParamsFTP"])
			self.upDateNotSuccessful[pi] = 0
		return valuesDict



####-------------------------------------------------------------------------####
	def confirmdeviceIDINPUTBUTTONmenu(self, valuesDict=None, typeId="", devId=""):
		try:
			devId = int(valuesDict[u"inputDev"])
			dev = indigo.devices[devId]
			props = dev.pluginProps
			for ii in range(30):
				valuesDict[u"i" + unicode(ii)] = False
			if u"deviceDefs" in props:
				gpioList = json.loads(props[u"deviceDefs"])
				for ii in range(30):
					if ii <= len(gpioList) and "gpio" in gpioList[ii]:
						valuesDict[u"i" + unicode(ii)] = True
			elif "gpio" in props:
				valuesDict[u"i" + props[u"gpio"]] = True
		except:
			pass
		return valuesDict

####-------------------------------------------------------------------------####
	def resetGPIOCountCALLBACKmenu(self, valuesDict=None, typeId="", devId=0):

		try:
			dev = indigo.devices[int(valuesDict[u"inputDev"])]
		except:
			try:
				dev = indigo.devices[valuesDict[u"inputDev"]]
			except:
				self.ML.myLog( errorType = u"bigErr", text =u"ERROR:  Reset counter of GPIO pin on rPi;	 dev: " + valuesDict[u"inputDev"] + " not defined")
				return

		devId=dev.id
		props = dev.pluginProps
		pi = props[u"piServerNumber"]
		resetGPIOCount = []
		if u"deviceDefs" in props:
			listGPIO= json.loads(props[u"deviceDefs"])
			if u"GPIOpins" in valuesDict:
				for pin in valuesDict[u"GPIOpins"]:
					for items in listGPIO:
						if u"gpio" not in items: continue
						if pin == items[u"gpio"]:
							resetGPIOCount.append(pin)
			else:
				for ii in range(len(listGPIO)):
					if u"INPUT_" + unicode(ii) in valuesDict and valuesDict[u"INPUT_" + unicode(ii)]:
						if u"gpio"	in listGPIO[ii]:
							resetGPIOCount.append(int(listGPIO[ii][u"gpio"]))
			#self.ML.myLog( text =	u"valuesDict"+ unicode(valuesDict)+"  resetGPIOCount"+ unicode(resetGPIOCount)+"  listGPIO "+ unicode(listGPIO))

		elif "gpio" in props:
			gpio = props[u"gpio"]
			if valuesDict[u"INPUT_" +gpio]:
				resetGPIOCount.append(gpio)
				 
		if resetGPIOCount == []: return valuesDict

		theType= dev.deviceTypeId.split(u"-")[0]
		textToSend = json.dumps([{u"device": typeId, u"command":"file","fileName":"/home/pi/pibeacon/"+theType+".reset","fileContents":resetGPIOCount}])
		self.sendtoRPI(self.RPI[unicode(pi)][u"ipNumberPi"], pi, textToSend)

		if self.ML.decideMyLog(u"UpdateRPI"): self.ML.myLog( text =	 u"resetGPIOCount requested: for " + dev.name + " on pi:"+ unicode(pi)+"; pins:" + unicode(resetGPIOCount))
		return valuesDict

####-------------------------------------------------------------------------####
	def resetGPIOCountCALLBACKaction(self, action1=None, typeId="", devId=0):
		self.resetGPIOCountCALLBACKmenu(action1.props)
		return



####-------------------------------------------------------------------------####
	def filterChannels(self, filter="", valuesDict=None, typeId="", devId=""):
		#indigo.server.log(u"filterChannels "+unicode(valuesDict))
		list=[]
		for ii in range(41):
			list.append((str(41-ii),"Channel-"+str(41-ii)))
		list.append((u"0","no pick"))
		return list


####-------------------------------------------------------------------------####
	def confirmdeviceRPIanyPropBUTTON(self, valuesDict, typeId="", devId=""):
		try:
			self.anyProperTydeviceNameOrId = valuesDict[u"deviceNameOrId"]
		except:
			self.ML.myLog( text = "ERROR:"+ self.anyProperTydeviceNameOrId +" not in defined")
		return valuesDict

####-------------------------------------------------------------------------####
	def filterAnyPropertyNameACTION(self, filter="", valuesDict=None, typeId="", devId=""):
		list=[]
		if self.anyProperTydeviceNameOrId ==0:
			return list
		try: id = int(self.anyProperTydeviceNameOrId)
		except: id =self.anyProperTydeviceNameOrId
		try: dev = indigo.devices[id]
		except:
			self.ML.myLog( text = "ERROR:"+ unicode(self.anyProperTydeviceNameOrId) +" not in defined")
			return list
		self.ML.myLog( text = "dev: "+ unicode(dev)+"XX" )
		self.ML.myLog( text = "id selected: "+ unicode(self.anyProperTydeviceNameOrId)+"XX" )
		props = dev.pluginProps
		for nn in props:
			list.append([nn,nn])
		return list

####-------------------------------------------------------------------------####
	def setAnyPropertyCALLBACKaction(self, action1=None, typeId="", devId=0):
		valuesDict = action1.props
		
		try: id = int(valuesDict[u"deviceNameOrId"])
		except: id = valuesDict[u"deviceNameOrId"]
		try: dev = indigo.devices[id]
		except:
			self.ML.myLog( text = "ERROR:"+ valuesDict[u"deviceNameOrId"] +" not in indigodevices")
			return
			
		if u"propertyName" not in valuesDict:
			self.ML.myLog( text =  u"ERROR:	 propertyName not in valuesDict")
			return
		props = dev.pluginProps
		propertyName =valuesDict[u"propertyName"] 
		if propertyName not in props:
			self.ML.myLog( text =  u"ERROR:	 "+propertyName+" not in pluginProps")
			return
		if u"propertyContents" not in valuesDict:
			self.ML.myLog( text =  u"ERROR:	 propertyContents not in valuesDict")
			return
		self.ML.myLog( text =  u"updating " +dev.name+"	 "+propertyName+"  "+props[propertyName])
		
		props[propertyName] = self.convertVariableOrDeviceStateToText(valuesDict[u"propertyContents"])

		dev.replacePluginPropsOnServer(props)
		return

####-------------------------------------------------------------------------####
	def getAnyPropertyCALLBACKaction(self, action1=None, typeId="", devId=0):
		valuesDict = action1.props
		##self.ML.myLog( text = " property request:"+ unicode(valuesDict) )
		try: id = int(valuesDict[u"deviceNameOrId"])
		except: id = valuesDict[u"deviceNameOrId"]
		try: dev = indigo.devices[id]
		except: 
			self.ML.myLog( text = "ERROR: "+ valuesDict[u"deviceNameOrId"] +" not in indigodevices")
			return {u"propertyName":"ERROR: " +valuesDict[u"deviceNameOrId"] +" not in indigodevices"}
			
		if u"propertyName" not in valuesDict:
			self.ML.myLog( text =  u"ERROR:	 propertyName not in valuesDict")
			return {u"propertyName":"ERROR:	 propertyName  not in valuesDict"}
		props = dev.pluginProps
		propertyName =valuesDict[u"propertyName"] 
		if propertyName not in props:
			self.ML.myLog( text =  u"ERROR:	 "+propertyName+" not in pluginProps")
			return {u"propertyName":"ERROR: "+propertyName+" not in pluginProps"}
		propertyContents = props[propertyName]
 
		try:
			var = indigo.variables[u"piBeacon_property"]
		except:
			indigo.variable.create(u"piBeacon_property", u"", self.iBeaconFolderNameVariables)

		indigo.variable.updateValue(u"piBeacon_property",propertyContents)
		
		return json.dumps({propertyName:unicode(propertyContents)}) # return value only works in api v 2


####-------------------------------------------------------------------------####
	def setTEA5767CALLBACKaction(self, action1=None, typeId="", devId=0):
		valuesDict = action1.props
		self.setTEA5767CALLBACKmenu(valuesDict)


####-------------------------------------------------------------------------####
	def setTEA5767CALLBACKmenu(self, valuesDict=None, typeId="", devId=0):
		try:
			vd=valuesDict
			try:
				devId = int(vd[u"outputDev"])
				dev = indigo.devices[devId]
			except:
				try:
					dev = indigo.devices[vd[u"outputDev"]]
					devId = dev.id
				except:
					self.ML.myLog( text =  u"error outputDev not set")
					vd[u"msg"] = "error outputDev not set"
					return
###			   #self.ML.myLog( text =  unicode(vd))
						
			typeId			  = "setTEA5767"
			props			  = dev.pluginProps
			piServerNumber	  = props[u"address"].split(u"-")[1]
			ip				  = self.RPI[piServerNumber][u"ipNumberPi"]
			if self.ML.decideMyLog(u"OutputDevice"): self.ML.myLog( text = "pi: "+str(ip)+"	 "+unicode(vd))

			cmds={}	  
			if u"command" in vd:	
				command = vd[u"command"]
			else:
				command = vd
			
			updateProps = False
			if u"frequency" in command and command[u"frequency"] !="":
				cmds[u"frequency"] = self.convertVariableOrDeviceStateToText(command[u"frequency"])
				props[u"defFreq"]  = cmds[u"frequency"]
				updateProps = True
			if u"mute" in command and command[u"mute"] !="":
				cmds[u"mute"] = self.convertVariableOrDeviceStateToText(command[u"mute"])
				props[u"mute"]	= cmds[u"mute"]
				updateProps = True
			if u"mono" in command and command[u"mono"] !="":
				cmds[u"mono"] = self.convertVariableOrDeviceStateToText(command[u"mono"])
				props[u"mono"]	= cmds[u"mono"]
				updateProps = True
			if u"restart" in command and command[u"restart"] ==u"1":
				cmds[u"restart"] = "1"
			if u"scan" in command and command[u"scan"] !="":
				cmds[u"scan"] = self.convertVariableOrDeviceStateToText(command[u"scan"])
				if u"minSignal" in command and command[u"minSignal"] !="":
					cmds[u"minSignal"] = self.convertVariableOrDeviceStateToText(command[u"minSignal"])
			if updateProps: 
				dev.replacePluginPropsOnServer(props)
				dev = indigo.devices[devId]
				self.addToStatesUpdateDict(devId,"status"	,"f= "+unicode(props[u"defFreq"]) + "; mute= " +unicode(props[u"mute"]),dev=dev)
				self.addToStatesUpdateDict(devId,"frequency",props[u"defFreq"],decimalPlaces=1)
				self.addToStatesUpdateDict(devId,"mute"		,props[u"mute"])
				self.executeUpdateStatesDict(onlyDevID=str(devId), calledFrom="setTEA5767CALLBACKmenu")
				if props[u"mute"] ==u"1":
						dev.updateStateImageOnServer(indigo.kStateImageSel.SensorOff)
				else:
						dev.updateStateImageOnServer(indigo.kStateImageSel.SensorOn)

			startAtDateTime = 0
			if u"startAtDateTime" in valuesDict:
				  startAtDateTime = self.setDelay(startAtDateTimeIN=self.convertVariableOrDeviceStateToText(vd[u"startAtDateTime"]))

			textToSend = json.dumps([{u"device": typeId, u"startAtDateTime":startAtDateTime,"command":"file","fileName":"/home/pi/pibeacon/setTEA5767.set","fileContents":cmds}])
			
			
			try:
				line = "\n##=======use this as a python script in an action group action :=====\n"
				line +="plug = indigo.server.getPlugin(\"com.karlwachs.piBeacon\")"
				line +="\nplug.executeAction(\"setTEA5767\" , props ={u"
				line +="\n	 \"outputDev\":\""+unicode(vd[u"outputDev"])+"\""
				line +="\n	,\"device\":\"" +unicode(typeId)+"\""
				line +="\n	,\"startAtDateTime\":\""+unicode(startAtDateTime)+"\""
				for cc in cmds:
					line +="\n	,\""+cc+"\":\""+unicode(cmds[cc])+"\""
				line +="})\n"
				line+= "##=======	end	   =====\n"
				if self.ML.decideMyLog(u"OutputDevice"): self.ML.myLog( text = "\n"+line+"\n")
			except:
				if self.ML.decideMyLog(u"OutputDevice"): self.ML.myLog( text = "use this as a python script command:\n"+"plug = indigo.server.getPlugin(\"com.karlwachs.piBeacon\")\nplug.executeAction(\"setTEA5767\" ,	props =(u"+
				  json.dumps({u"outputDev":vd[u"outputDev"],"device": typeId})+" error")
			self.sendtoRPI(ip, piServerNumber, textToSend)
			vd[u"msg"] = " ok"
		except	Exception, e:
				self.ML.myLog( text =  u"setTEA5767CALLBACKmenu in Line '%s' has error='%s'" % (sys.exc_traceback.tb_lineno, e))


####-------------------------------------------------------------------------####
	def confirmduplicateBUTTONmenu(self, valuesDict=None, typeId="", devId="x"):
		try:
			vd = valuesDict

			## first save
			cd = self.savedisplayPropsWindowCALLBACKbutton(valuesDict=vd)

			## copy from to 
			dublicateFrom = vd[u"dublicateFrom"]
			dublicateTo	  = vd[u"dublicateTo"]
			if dublicateFrom == dublicateTo: return vd
			# copy the props shown in the action 
			for xxx in ["type","text","delayStart","offONTime","reset","font","width","fill","position","display"]:
				vd[xxx+dublicateTo] = vd[xxx+dublicateFrom]

			## show new ones on screen 
			vd = self.setdisplayPropsWindowCALLBACKbutton(valuesDict=vd)

		except	Exception, e:
			self.ML.myLog( text =  u"confirmduplicateBUTTONmenu in Line '%s' has error='%s'" % (sys.exc_traceback.tb_lineno, e))
		return vd

####-------------------------------------------------------------------------####
	def setdisplayPropsWindowCALLBACKbutton(self, valuesDict=None, typeId="", devId=0):
		vd = valuesDict
		try:	fromWindow = int(vd["fromWindow"])
		except: return vd 
		for xx in vd:
			if "xYAYx" in xx:
				yy = xx.split("xYAYx")
				if yy[1] == "99": continue
				fromProp =	yy[0]+unicode(int(yy[1])+fromWindow)
				if fromProp in vd:
					vd[xx] = vd[fromProp]
		vd["windowStart"] = vd["fromWindow"]+" .. to "+ str(int(vd["fromWindow"])+10)
		return vd
		
####-------------------------------------------------------------------------####
	def savedisplayPropsWindowCALLBACKbutton(self, valuesDict=None, typeId="", devId=0):
		vd = valuesDict
		try:	fromWindow = int(vd["fromWindow"])
		except: return vd 
		for xx in vd:
			if "xYAYx" in xx:
				yy = xx.split("xYAYx")
				vd[ yy[0] + unicode(int(yy[1])+fromWindow) ] = vd[xx]
		return vd

####-------------------------------------------------------------------------####
	def setdisplayCALLBACKaction(self, action1=None, typeId="", devId=0):
		valuesDict = action1.props
		return self.setdisplayCALLBACKmenu(valuesDict)

####-------------------------------------------------------------------------####
	def setdisplayCALLBACKmenu(self, valuesDict=None, typeId="", devId=0):
		cmds =[]
		try:
			vd=valuesDict
			###if self.ML.decideMyLog(u"OutputDevice"): self.ML.myLog( text = "setdisplayCALLBACKmenu: "+ unicode(vd))
			try:
				dev = indigo.devices[int(vd[u"outputDev"])]
			except:
				try:
					dev = indigo.devices[vd[u"outputDev"]]
				except:
					self.ML.myLog( text =  u"error outputDev not set")
					vd[u"msg"] = "error outputDev not set"
					return
###			   #self.ML.myLog( text =  unicode(vd))
						
			props = dev.pluginProps
			piServerNumber	  = props[u"address"].split(u"-")[1]
			typeId			  = "OUTPUT-Display"
			if u"command" in vd:	
				cmds = vd[u"command"]
				for iii in range(200):
					if u"%%v:" not in cmds and "%%d:" not in cmds: break
					cmds= self.convertVariableOrDeviceStateToText(self.convertVariableOrDeviceStateToText(cmds))
				if self.ML.decideMyLog(u"OutputDevice"): self.ML.myLog( text = "input:"+ unicode(vd[u"command"])+" result:"+unicode(cmds)+"\n")
					
				if cmds .find(u"[{'") ==0: #  this will not work for json  replace ' with " as text delimiters and save any " 
					cmds = cmds.replace(u"'","aa123xxx123xxxaa").replace('"',"'").replace(u"aa123xxx123xxxaa",'"')
					
				try:
					cmds = json.loads(cmds)
				except	Exception, e:
					if len(unicode(e)) > 5 :
						self.ML.myLog( text =  u"setdisplayCALLBACKmenu in Line '%s' has error='%s'" % (sys.exc_traceback.tb_lineno, e))
					self.ML.myLog( text =  u"error in json conversion for "+unicode(cmds))
					vd[u"msg"] = "error in json conversion"
					return
				if self.ML.decideMyLog(u"OutputDevice"): self.ML.myLog( text = " after json conversion:"+unicode(cmds)+"\n")

				delCMDS =[]					   
				for ii in range(len(cmds)):
					cType = cmds[ii][u"type"]
					if cType == "0" or cType == "" or \
						cType not in [u"text",u"textWformat",u"clock",u"dateString",u"analogClock",u"digitalClock",u"date",u"NOP",u"line",u"point",u"ellipse",u"vBar",u"hBar",u"vBarwBox",u"hBarwBox",u"rectangle",u"triangle",u"hist",u"exec",u"image",u"dot"]:
						delCMDS.append(ii)
						continue
					if u"position" in cmds[ii]:
						try:	
							xx					   = json.loads(cmds[ii][u"position"])
							cmds[ii][u"position"]  = xx
						except: 
							try: 
								xx = json.loads(json.dumps (cmds[ii][u"position"]))
								# is ok was already	 loaded
							except: 
								self.ML.myLog( text = " error in input: position= "+  unicode(cmds[ii][u"position"]) )	 
								valuesDict[u"msg"] = "error in position"
					if cType =="textWformat" and u"text" in cmds[ii] and "FORMAT" in cmds[ii][u"text"]: 
						try:
							xx = cmds[ii][u"text"].split("FORMAT")
							cmds[ii][u"text"] = xx[1]%(float(xx[0]))
						except:
							self.ML.myLog( text = "setdisplayCALLBACK error in formatting: "+ unicode(cmds[ii][u"text"]))
					if cType not in[u"text",u"textWformat",u"dateString",u"image"]:
						if u"text" in cmds[ii]: del cmds[ii][u"text"]
				if len(delCMDS) >0:
					for ii in delCMDS[::-1]:
						del cmds[ii]

			else:
				###if self.ML.decideMyLog(u"OutputDevice"): self.ML.myLog( text = "input:"+ unicode(vd))
				cmds =[]
				nn =-1
				for ii in range(100):
					iiS = unicode(ii)
					if u"type"+iiS not in vd: continue	
					cType = vd[u"type"+iiS]
					if cType == "0":				  continue	
					if cType == "":					  continue	
					if cType in [u"text",u"textWformat",u"clock",u"dateString",u"digitalClock",u"analogClock",u"date",u"NOP",u"line",u"point",u"ellipse",u"vBar",u"hBar",u"vBarwBox",u"hBarwBox",u"rectangle",u"triangle",u"hist",u"exec",u"image",u"dot"]:
						cmds.append({})
						nn+=1
						cmds[nn][u"type"]				  = cType
						if cType ==u"analogClock":
							cmds[nn]["hh"]	  = {}
							cmds[nn]["mm"]	  = {}
							cmds[nn]["ss"]	  = {}
							cmds[nn]["ticks"] = {}
							cmds[nn]["box"]	  = {}
						
						if u"text"+iiS in vd:
							cmds[nn][u"text"]			  = self.convertVariableOrDeviceStateToText(vd[u"text"+iiS])
							if cType =="textWformat" and "FORMAT" in cmds[nn][u"text"]: 
								try:
									xx = cmds[nn][u"text"].split("FORMAT")
									cmds[nn][u"text"] = xx[1]%(float(xx[0]))
								except:
									self.ML.myLog( text = "setdisplayCALLBACK error in formatting: "+ unicode(cmds[nn][u"text"]))
							   
						if u"font"+iiS in vd:
							cmds[nn][u"font"]			  = self.convertVariableOrDeviceStateToText(vd[u"font"+iiS])

						if u"delayStart"+iiS in vd:
							cmds[nn][u"delayStart"]		  = self.convertVariableOrDeviceStateToText(vd[u"delayStart"+iiS])

 

						cmds[nn][u"fill"]	 = self.setupListDisplay(vd,u"fill"+iiS,  lenItem=3,default="") 
						cmds[nn][u"reset"]	 = self.setupListDisplay(vd,u"reset"+iiS, lenItem=3,default="") 

						if u"width"+iiS in vd:
							cmds[nn][u"width"]			  = self.setupListDisplay(vd,u"width"+iiS, lenItem=2,default="") 

						if u"format"+iiS in vd:
							cmds[nn][u"format"]			   = self.convertVariableOrDeviceStateToText(vd[u"format"+iiS])

						if u"radius"+iiS in vd:
							cmds[nn][u"radius"]			  = self.setupListDisplay(vd,u"radius"+iiS,lenItem=2,default="") 

						if u"fillhh"+iiS in vd:
							cmds[nn][u"hh"][u"fill"]	  = self.setupListDisplay(vd,u"fillhh"+iiS, lenItem=3,default="") 

						if u"fillmm"+iiS in vd:
							cmds[nn][u"mm"][u"fill"]	  = self.setupListDisplay(vd,u"fillmm"+iiS, lenItem=3,default="") 

						if u"fillss"+iiS in vd:
							cmds[nn][u"ss"][u"fill"]	  = self.setupListDisplay(vd,u"fillss"+iiS, lenItem=3,default="") 

						if u"fillticks"+iiS in vd:
							cmds[nn][u"ticks"][u"fill"]	  = self.setupListDisplay(vd,u"fillticks"+iiS, lenItem=3,default="") 

						if u"mode"+iiS in vd:
							cmds[nn][u"mode"]			  = self.convertVariableOrDeviceStateToText(vd[u"mode"+iiS])

						if u"box"+iiS in vd:
							cmds[nn][u"box"]["on"]		  = self.convertVariableOrDeviceStateToText(vd[u"box"+iiS])

						if u"fillBox"+iiS in vd:
							cmds[nn][u"box"][u"fill"]	  = self.addBrackets(self.convertVariableOrDeviceStateToText(vd[u"fillBox"+iiS]),cType=3)

						if u"widthBox"+iiS in vd:
							cmds[nn][u"box"][u"width"]	  = self.convertVariableOrDeviceStateToText(vd[u"widthBox"+iiS])
						if u"heightBox"+iiS in vd:
							cmds[nn][u"box"][u"height"]	   = self.convertVariableOrDeviceStateToText(vd[u"heightBox"+iiS])


						if u"display"+iiS in vd:
							cmds[nn][u"display"]		  = self.convertVariableOrDeviceStateToText(vd[u"display"+iiS])

						if u"position"+iiS in vd:
							cmds[nn][u"position"]		  = self.addBrackets(self.convertVariableOrDeviceStateToText(vd[u"position"+iiS]),cType=cType)

						if u"offONTime"+iiS in vd:
							cmds[nn][u"offONTime"]		  = self.addBrackets( self.convertVariableOrDeviceStateToText(vd[u"offONTime"+iiS]), cType=3, default=[0,999999999,0] )

						if cType not in[u"text",u"textWformat",u"dateString",u"image"]:
							if u"text" in cmds[nn]:	 del cmds[nn][u"text"]
						if cType == "point":
							if u"width" in cmds[nn]: del cmds[nn][u"width"]


				#self.ML.myLog( text =	unicode(vd))
			ip = self.RPI[piServerNumber][u"ipNumberPi"]
			
			startAtDateTime = 0
			if u"startAtDateTime" in valuesDict:
				  startAtDateTime = self.setDelay(startAtDateTimeIN=self.convertVariableOrDeviceStateToText(vd[u"startAtDateTime"]))

			repeat				= 1
			resetInitial		= ""
			scrollxy			= ""
			scrollPages			= 1
			scrollDelay			= 0
			scrollDelayBetweenPages = 0
			intensity			= "100" 
			showDateTime		= "0"
			restoreAfterBoot	= False
			if u"repeat" in vd:
				repeat = self.convertVariableOrDeviceStateToText(vd[u"repeat"])

			if u"intensity" in vd:
				  intensity = self.convertVariableOrDeviceStateToText(vd[u"intensity"])

			if u"resetInitial" in vd:
				resetInitial = self.convertVariableOrDeviceStateToText(vd[u"resetInitial"])

			if u"scrollxy" in vd:		  
				scrollxy		   = self.convertVariableOrDeviceStateToText(vd[u"scrollxy"])

			if u"showDateTime" in vd:		  
				showDateTime		   = self.convertVariableOrDeviceStateToText(vd[u"showDateTime"])

			if u"scrollPages" in vd:		 
				scrollPages		 = self.convertVariableOrDeviceStateToText(vd[u"scrollPages"])

			if u"scrollDelay" in vd:		 
				scrollDelay		 = self.convertVariableOrDeviceStateToText(vd[u"scrollDelay"])

			if u"scrollDelayBetweenPages" in vd:		 
				scrollDelayBetweenPages = self.convertVariableOrDeviceStateToText(vd[u"scrollDelayBetweenPages"])

			if u"restoreAfterBoot" in vd:		  
				restoreAfterBoot = self.convertVariableOrDeviceStateToText(vd[u"restoreAfterBoot"])

			try:
				line = "\n##=======use this as a python script in an action group action :=====\n"
				line +="plug = indigo.server.getPlugin(\"com.karlwachs.piBeacon\")"
				line +="\nplug.executeAction(\"Display\" ,	props ={"
				line +="\n	 \"outputDev\":\""+unicode(vd[u"outputDev"])+"\""
				line +="\n	,\"device\":\"" +unicode(typeId)+"\""
				line +="\n	,\"restoreAfterBoot\":\""+unicode(restoreAfterBoot)+"\""
				line +="\n	,\"intensity\":\""+unicode(intensity)+"\""
				line +="\n	,\"repeat\":\""+unicode(repeat)+"\""
				line +="\n	,\"resetInitial\":\""+unicode(resetInitial)+"\""
				line +="\n	,\"scrollxy\":\""+unicode(scrollxy)+"\""
				line +="\n	,\"showDateTime\":\""+unicode(showDateTime)+"\""
				line +="\n	,\"startAtDateTime\":\""+unicode(startAtDateTime)+"\""
				line +="\n	,\"scrollPages\":\""+unicode(scrollPages)+"\""
				line +="\n	,\"scrollDelay\":\""+unicode(scrollDelay)+"\""
				line +="\n	,\"scrollDelayBetweenPages\":\""+unicode(scrollDelayBetweenPages)+"\""
				line +="\n	,\"command\":'['+\n		 '"

				### this will create list of dicts, one per command, remove blank items, sort  ,.. 
				doList =[u"type",u"position",u"width",u"fill",u"font",u"text",u"offONTime",u"display",u"reset"] # sorted by this
				noFont =[u"NOP",u"line",u"point",u"ellipse",u"vBar",u"hBar",u"vBarwBox",u"hBarwBox",u"rectangle",u"triangle",u"hist",u"exec",u"image",u"dot"]
				for cc in range(len(cmds)):
					delItem=[]
					if len(cmds[cc]) > 0:
						line +="{"
						for item in doList:
							if item in cmds[cc]:
								if cmds[cc][item] !="" and not ( item ==u"font" and cmds[cc][u"type"] in noFont) :
									line +='"'+item+'":'+json.dumps(cmds[cc][item]).strip(" ")+", "
								else:# this is blank
									delItem.append(item)
		  
						for item in cmds[cc]: # this is for the others not listed in the sort List
							if item in doList: continue
							if cmds[cc][item] !="":
								line +='"'+item+'":'+json.dumps(cmds[cc][item]).strip(" ")+", "
							else: # this is blank
								delItem.append(item)
		  
						## remove blanks 
						for item in delItem: 
							del cmds[cc][item]
						# close line 
						line  = line.strip(u", ") + "}'+\n	   ',"

				## finish cmd lines
				line  = line.strip(u"'+\n	  ',")	+ "]'\n	 })\n"
				## end of output
				line += "##=======	 end	=====\n"

				if self.ML.decideMyLog(u"OutputDevice"): self.ML.myLog( text = "\n"+line+"\n")
				vd[u"msg"] = " ok"

			except	Exception, e:
				if len(unicode(e)) > 5 :
					self.ML.myLog( text =  u"setdisplayCALLBACKmenu in Line '%s' has error='%s'" % (sys.exc_traceback.tb_lineno, e))
					vd[u"msg"] = "error"
			textToSend = json.dumps([{u"device": typeId,  "restoreAfterBoot": False, u"intensity":intensity,"repeat":repeat,"resetInitial":resetInitial,"startAtDateTime":startAtDateTime,
				u"scrollxy":scrollxy, u"showDateTime":showDateTime,"scrollPages":scrollPages,"scrollDelay":scrollDelay,"scrollDelayBetweenPages":scrollDelayBetweenPages,
				u"command": cmds}])
			self.sendtoRPI(ip, piServerNumber, textToSend)
			
		except	Exception, e:
			if len(unicode(e)) > 5 :
				self.ML.myLog( text =  u"setdisplayCALLBACKmenu in Line '%s' has error='%s'" % (sys.exc_traceback.tb_lineno, e))
				self.ML.myLog( text =  u"error display check "+unicode(vd))
				valuesDict[u"msg"] = "error in parameters"
		return vd
		

	def setupListDisplay(self,theDict,tType,lenItem=0,default=""):
		try:
			ret = default
			if tType in theDict:
				ret = self.convertVariableOrDeviceStateToText(theDict[tType])
				if len(ret) > 0: 
					if "," in ret:
						ret	 =	self.addBrackets(ret,cType=lenItem)
					else:
						ret = int(ret)
		except	Exception, e:
			if len(unicode(e)) > 5 :
				self.ML.myLog( text =  u"setdisplayCALLBACKmenu in Line '%s' has error='%s'" % (sys.exc_traceback.tb_lineno, e))
		return ret
####-------------------------------------------------------------------------####
	def addBrackets(self,pos,cType="",default=[]):
		try:
			test = unicode(pos).strip(",")
			
			if len(test) ==0: return default
			if cType == "point":
				return json.loads(test)
				
			
			if		type(cType) == type(2):	 nItems = cType
			elif	cType ==u"text":		 nItems = 2
			elif	cType ==u"line":		 nItems = 4
			elif	cType ==u"ellipse" :	 nItems = 4
			elif	cType ==u"dot" :		 nItems = 2
			elif	cType ==u"radius"  :	 nItems = 2
			elif	cType ==u"center"  :	 nItems = 2
			elif	cType ==u"vBar"	   :	 nItems = 3
			elif	cType ==u"hBar"	   :	 nItems = 3
			elif	cType ==u"vBarwBox":	 nItems = 3
			elif	cType ==u"hBarwBox":	 nItems = 3
			elif	cType ==u"rectangle":	 nItems = 4
			elif	cType ==u"triangle":	 nItems = 6
			elif	cType ==u"dateString":	 nItems = 2
			elif	cType ==u"analogClock":	 nItems = 2
			elif	cType ==u"digitalClock": nItems = 2
			else:							 nItems = -1
			
			if len(test) >0 and test[0]	 =="[": test = test[1:]	   
			if len(test) >0 and test[-1] =="[": test = test[:-1] 
			test = test.split(",")	 
			pp = []
			for t in test:
					try:	x = int(float(t))
					except: x = t
					pp.append(x)
			if nItems !=-1 and nItems != len(pp):
				self.ML.myLog( text = "addBrackets error in input: pos= "+unicode(pos) +  "; wrong number of coordinates, should be: %d" %(nItems) )
				
			return pp
		except	Exception, e:
			self.ML.myLog( text =  u"addBrackets in Line '%s' has error='%s'" % (sys.exc_traceback.tb_lineno, e))
			self.ML.myLog( text = "addBrackets error in input: cType:"+unicode(cType)+";  default= "+unicode(default)+";  pos= "+  unicode(pos) )	 
		return default
							


####-------------------------------------------------------------------------####
	def setneopixelCALLBACKaction(self, action1=None, typeId="", devId=0):
		valuesDict = action1.props
		return self.setneopixelCALLBACKmenu(valuesDict)[u"msg"]

####-------------------------------------------------------------------------####
	def setneopixelCALLBACKmenu(self, valuesDict=None, typeId="", devId=0):
		try:
			vd=valuesDict
			vd[u"msg"] = ""
			try:
				devId = int(vd[u"outputDev"])
				dev = indigo.devices[devId]
			except:
				try:
					dev = indigo.devices[vd[u"outputDev"]]
					devId = dev.id
				except:
					self.ML.myLog( text =  u"error outputDev not set")
					vd[u"msg"] = "error outputDev not set"
					return vd
###			   #self.ML.myLog( text =  unicode(vd))
						
			props = dev.pluginProps
			piServerNumber	  = props[u"address"].split(u"-")[1]
			typeId			  = "OUTPUT-neopixel"
			lightON = False
			maxRGB	= 0
			if u"command" in vd:	
				cmds = vd[u"command"]
				for iii in range(200):
					if u"%%v:" not in cmds and "%%d:" not in cmds: break
					cmds= self.convertVariableOrDeviceStateToText(cmds)
				if self.ML.decideMyLog(u"OutputDevice"): self.ML.myLog( text = "input:\n"+ unicode(vd[u"command"])+"\n result:\n"+unicode(cmds)+"\n")
					
				if cmds .find(u"[{'") ==0: #  this will not work for json  replace ' with " as text delimiters and save any " 
					cmds = cmds.replace(u"'","aa123xxx123xxxaa").replace('"',"'").replace(u"aa123xxx123xxxaa",'"')
					
				try:
					cmds = json.loads(cmds)
				except	Exception, e:
					if len(unicode(e)) > 5 :
						self.ML.myLog( text =  u"setneopixelCALLBACKmenu in Line '%s' has error='%s'" % (sys.exc_traceback.tb_lineno, e))
					self.ML.myLog( text =  u"error in json conversion for "+unicode(cmds))
					vd[u"msg"] = "error in json conversion"
					return
				if self.ML.decideMyLog(u"OutputDevice"): self.ML.myLog( text = " after json conversion:\n"+unicode(cmds)+"\n")
					
				for ii in range(len(cmds)):
					cType = cmds[ii][u"type"]
					if u"position" in cmds[ii]:
							cmds, xx, ok = self.makeACompleteList(u"position", cmds[ii],cmds,ii,ii)
							if not ok: return vd 
					if not (cType == "image"):
						if u"text" in cmds[ii]: del cmds[ii][u"text"]

			else:
				cmds =[]
				nn =-1
				for ii in range(100):
					iiC= str(ii)
					if u"type"+unicode(ii) not in vd: continue	
					cType = vd[u"type"+iiC]
					if cType == "0":				  continue	
					if cType == "":					  continue	
					if (cType ==u"text"		  or
						cType ==u"NOP"		  or
						cType ==u"line"		  or
						cType ==u"points"	  or
						cType ==u"sPoint"	  or
						cType ==u"rectangle"  or
						cType ==u"matrix"	  or
						cType ==u"exec"		  or
						cType ==u"image"):
						cmds.append({})
						nn+=1
						cmds[nn][u"type"]				  = cType
						if u"text"+iiC in vd:
							cmds[nn][u"text"]			   = self.convertVariableOrDeviceStateToText(vd[u"text"+iiC])
						if u"delayStart"+iiC in vd:
							cmds[nn][u"delayStart"]		   = self.convertVariableOrDeviceStateToText(vd[u"delayStart"+iiC])
						if u"reset"+iiC in vd:
							cmds, vd, ok = self.makeACompleteList(u"reset", vd,cmds,nn,ii)
						if u"rotate"+iiC in vd:
							cmds[nn][u"rotate"]			   = self.convertVariableOrDeviceStateToText(vd[u"rotate"+iiC])
						if u"rotateSeconds"+iiC in vd:
							cmds[nn][u"rotateSeconds"]	   = self.convertVariableOrDeviceStateToText(vd[u"rotateSeconds"+iiC])
						if u"display"+iiC in vd:
							cmds[nn][u"display"]		  = self.convertVariableOrDeviceStateToText(vd[u"display"+iiC])
						if u"position"+iiC in vd:
							cmds, vd, ok = self.makeACompleteList(u"position", vd,cmds,nn,ii)
							if not ok: return vd 
						if u"speedOfChange"+iiC in vd:
							cmds[nn][u"speedOfChange"] = self.convertVariableOrDeviceStateToText(vd[u"speedOfChange"+iiC])

						if	cType != "image" :
							if u"text" in cmds[nn]:	 del cmds[nn][u"text"]
							
					elif cType ==u"thermometer":
						if u"startPixelx"+iiC in vd and "endPixelx"+iiC in vd and "startPixelRGB"+iiC in vd and "endPixelRGB"+iiC in vd and "deltaColorSteps"+iiC in vd:
							cmds.append({})
							nn+=1
							cmds[nn][u"type"]				  = "points"
							if u"position"+iiC in vd:
								cmds, vd, ok = self.makeACompleteList(u"position", vd,cmds,nn,ii)
								if not ok: return vd 
							if u"speedOfChange"+iiC in vd:
								cmds[nn][u"speedOfChange"] = self.convertVariableOrDeviceStateToText(vd[u"speedOfChange"+iiC])
							if u"delayStart"+iiC in vd:
								cmds[nn][u"delayStart"]		   = self.convertVariableOrDeviceStateToText(vd[u"delayStart"+iiC])
							if u"reset"+iiC in vd:
								cmds, vd, ok = self.makeACompleteList(u"reset", vd,cmds,nn,ii)
							
							startPixelx		= int(self.convertVariableOrDeviceStateToText(vd[u"startPixelx"+iiC]))
							endPixelx		= int(self.convertVariableOrDeviceStateToText(vd[u"endPixelx"+iiC]))
							startPixelRGB	= map(int, self.convertVariableOrDeviceStateToText(vd[u"startPixelRGB"+iiC]).split(u",")  )
							endPixelRGB		= map(int, self.convertVariableOrDeviceStateToText(vd[u"endPixelRGB"+iiC]).split(u",")	  )
							deltaColorSteps = map(int, self.convertVariableOrDeviceStateToText(vd[u"deltaColorSteps"+iiC]).split(u","))
							if self.ML.decideMyLog(u"OutputDevice"):self.ML.myLog( text = ";  startPixelx:"+unicode(startPixelx) +";  endPixelx:"+unicode(endPixelx) +";  startPixelRGB:"+unicode(startPixelRGB)+";	 endPixelRGB:"+unicode(endPixelRGB) +";	 deltaColorSteps:"+unicode(deltaColorSteps)	 ) 
							nsteps	   =  max(0,abs(endPixelx - startPixelx))
							deltaC	   =  [endPixelRGB[ll] - startPixelRGB[ll] for ll in range(3)]
							deltaCabs  =  map(abs, deltaC)
							deltaCN	   =  sum(deltaCabs)
							stepSize   =  float(deltaCN)/ max(1,nsteps)	 
							stepSizeSign   =  [cmp(deltaC[0],0),cmp(deltaC[1],0),cmp(deltaC[2],0)] 
							if self.ML.decideMyLog(u"OutputDevice"):self.ML.myLog( text = ";  nsteps:"+unicode(nsteps) +";	deltaC:"+unicode(deltaC) +";  deltaCabs:"+unicode(deltaCabs) +";  deltaCN:"+unicode(deltaCN) +";  stepSize:"+unicode(stepSize)+";  stepSizeSign:"+unicode(stepSizeSign) ) 
							pos=[]
							if sum(deltaColorSteps) ==0:  # same delta steps for RGB 
								iii = startPixelx
								fsteps= float(nsteps)
								for kkk in range(nsteps):
									pos.append([0,iii, min(255,int(startPixelRGB[0]+ float(kkk)*deltaC[0]/fsteps+0.5)),min(255,int(startPixelRGB[1]+ float(kkk)*deltaC[1]/fsteps+0.5)),min(255,int(startPixelRGB[2]+ float(kkk)*deltaC[2]/fsteps+0.5))])
									iii+=1
							else: #different R,G,B steps 
								iii	   = startPixelx
								nnn	   = 0
								jjj	   = 0
								color =	 copy.deepcopy(startPixelRGB)
								rest  = 0
								if	 stepSizeSign[jjj] >0: color[jjj] -= stepSize
								else:					   color[jjj] += stepSize
								while  nnn < nsteps and iii < endPixelRGB:
									if	 stepSizeSign[jjj] >0:
										color[jjj] += stepSize +max(0,rest)+0.5
										colorF =  map(int,color)
										rest = color[jjj]  -  endPixelRGB[jjj] 
										if rest > 0:
											color[jjj] = endPixelRGB[jjj]
											colorF	   = map(int,color)
											jjj+=1
									else:
										color[jjj] -= stepSize	- min(0,rest)+0.5
										colorF = map(int,color)
										rest = color[jjj]  -  endPixelRGB[jjj]
										if rest < 0:
											color[jjj] = endPixelRGB[jjj]
											colorF	   = map(int,color)
											jjj+=1
									pos.append([0,iii, min(255,colorF[0]),min(255,colorF[1]),min(255,colorF[2])] )
									jjj = min(jjj,2)
									iii+=1
									nnn+=1
							if self.ML.decideMyLog(u"OutputDevice"):self.ML.myLog( text = unicode(pos)) 
							cmds[nn][u"position"] = pos
						else:
							vd[u"msg"] = "error in type"
							return vd
						

				#self.ML.myLog( text =	unicode(vd))
			ip = self.RPI[piServerNumber][u"ipNumberPi"]
			
			startAtDateTime = 0
			if u"startAtDateTime" in valuesDict:
				  startAtDateTime = self.setDelay(startAtDateTimeIN=self.convertVariableOrDeviceStateToText(vd[u"startAtDateTime"]))

			repeat =1
			resetInitial = ""
			scrollxy = ""
			scrollPages =1
			scrollDelay =0
			scrollDelayBetweenPages =0
			intensity = "100" 
			showDateTime = "0"
			if u"repeat" in vd:
				repeat = self.convertVariableOrDeviceStateToText(vd[u"repeat"])
			else:
				repeat = 1

			if u"intensity" in vd:
				  intensity = self.convertVariableOrDeviceStateToText(vd[u"intensity"])

			if u"resetInitial" in vd:
				resetInitial, vd, ok = self.makeACompleteList(u"resetInitial", vd)
				if not ok: return vd 

			restoreAfterBoot =False
			if u"restoreAfterBoot" in vd:		  
				restoreAfterBoot = self.convertVariableOrDeviceStateToText(vd[u"restoreAfterBoot"])

			textToSend = json.dumps([{u"device": typeId,  "restoreAfterBoot": restoreAfterBoot, u"intensity":intensity,"repeat":repeat,"resetInitial":resetInitial,"startAtDateTime":startAtDateTime,"command": cmds}])
			try:
				line = "\n##=======use this as a python script in an action group action :=====\n"
				line +="plug = indigo.server.getPlugin(\"com.karlwachs.piBeacon\")"
				line +="\nplug.executeAction(\"Neopixel\" , props ={u"
				line +="\n	 \"outputDev\":\""+unicode(vd[u"outputDev"])+"\""
				line +="\n	,\"device\":\"" +unicode(typeId)+"\""
				line +="\n	,\"restoreAfterBoot\":"+unicode(restoreAfterBoot)
				line +="\n	,\"intensity\":"+unicode(intensity)
				line +="\n	,\"repeat\":"+unicode(repeat)
				line +="\n	,\"resetInitial\":\""+unicode(resetInitial)+"\""
				line +="\n	,\"command\":'['+\n		 '"
				for cc in cmds:
					line+=json.dumps(cc)+"'+\n	   ',"
					pts = unicode(cc).split(u"]")
					for pts2 in pts: 
						items = pts2.split(u",")
						if len(items) < 3: continue
						for xx	in range(3):
							try: 
								rgbV=  int(items[-xx])
								if rgbV > maxRGB:
									maxRGB	= rgbV
									if	rgbV > 55:	#0..255, ~ 50+ light comes on 
										lightON = True
							except: pass
							
							
				line = line.strip(u"'+\n	 ',")	 
				line+="]'\n	 })\n"
				line+= "##=======	end	   =====\n"
				if self.ML.decideMyLog(u"OutputDevice"): self.ML.myLog( text = "\n"+line+"\n")
			except	Exception, e:
				if len(unicode(e)) > 5 :
					self.ML.myLog( text =  u"setneopixelCALLBACKmenu in Line '%s' has error='%s'" % (sys.exc_traceback.tb_lineno, e))
				if self.ML.decideMyLog(u"OutputDevice"): self.ML.myLog( text = "use this as a ppython script command:\n"+"plug = indigo.server.getPlugin(\"com.karlwachs.piBeacon\")\nplug.executeAction(\"Neopixel\" , props ="+
				  (json.dumps({u"outputDev":vd[u"outputDev"],"device": typeId,	"restoreAfterBoot": False, u"intensity":intensity,"repeat":repeat,"resetInitial":resetInitial})).strip(u"}").replace(u"false","False").replace(u"true","True")+"\n,\"command\":'"+json.dumps(cmds) +"'})"+"\n")
				self.ML.myLog( text =  u"vd: "+unicode(vd))

			chList =[{u"key":"OUTPUT","value": unicode(cmds).replace(u" ","")}]
			chList.append({u"key":"status","value": round(maxRGB/2.55)})
			self.execUpdateStatesList(dev,chList)
			if lightON:
				dev.updateStateImageOnServer(indigo.kStateImageSel.PowerOn)
			else:
				dev.updateStateImageOnServer(indigo.kStateImageSel.PowerOff)

			self.sendtoRPI(ip, piServerNumber, textToSend)
			vd[u"msg"] = " ok"
			
		except	Exception, e:
			if len(unicode(e)) > 5 :
				self.ML.myLog( text =  u"setneopixelCALLBACKmenu in Line '%s' has error='%s'" % (sys.exc_traceback.tb_lineno, e))
				self.ML.myLog( text =  u"error display check "+unicode(vd))
				valuesDict[u"msg"] = "error in parameters"
		return vd



####-------------------------------------------------------------------------####
	def makeACompleteList(self,item, vd,cmds=[],nn="",ii=""):
		try:
			if item+unicode(ii) in vd:
				xxx				 = unicode(self.convertVariableOrDeviceStateToText(unicode(vd[item+unicode(ii)])))
				if xxx ==u"": return cmds, vd, True
				if xxx[0]  !=u"[": xxx = u"["+xxx
				if xxx[-1] !=u"]": xxx =xxx+ u"]"
				try:	
					if cmds ==[]:
						cmds			 = json.loads(xxx)
					else:
						cmds[nn][item]	 = json.loads(xxx)
					return cmds, vd, True
				except Exception, e:
					self.ML.myLog( text =  u"makeACompleteList in Line '%s' has error='%s'" % (sys.exc_traceback.tb_lineno, e))
					self.ML.myLog( text = " error in input: "+item+" ii="+unicode(ii)+" nn="+unicode(nn)+ " cmds="+	 unicode(cmds) + " xxx="+  unicode(xxx))	
					vd[u"msg"] = "error in parameter"
				return cmds,vd, False
		except	Exception, e:
			if len(unicode(e)) > 5 :
				self.ML.myLog( text =  u"makeACompleteList in Line '%s' has error='%s'" % (sys.exc_traceback.tb_lineno, e))
				self.ML.myLog( text =  u"item " +unicode(item)+unicode(ii)+"  , vd "+unicode(vd))
			return cmds,vd, False
		return cmds,vd, True



####-------------------------------------------------------------------------####
	def sendFileToRPIviaSocket(self,ip, pi, fileName,fileContents,fileMode="w",touchFile=True):
		try: 
			out= (json.dumps([{u"command":"file","fileName":fileName,"fileContents":fileContents,"fileMode":fileMode,"touchFile":touchFile}]))
			if self.ML.decideMyLog(u"OutputDevice"): self.ML.myLog( text =	u"sending file to  "+ip+";	"+ out )
			self.sendtoRPI(ip, pi,	out)
		except	Exception, e:
				self.ML.myLog( text =  u"sendFileToRPIviaSocket in Line '%s' has error='%s'" % (sys.exc_traceback.tb_lineno, e))
		return




####-------------------------------------------------------------------------####
	def presendtoRPI(self,piIN, out):
		retC = 0
		if unicode(piIN) ==u"999":
			for pi in range(_GlobalConst_numberOfRPI):
				piU= unicode(pi)
				if self.RPI[piU][u"ipNumberPi"] == "":	 continue
				if self.RPI[piU][u"piOnOff"]	== u"":	 continue
				if self.RPI[piU][u"piOnOff"]	== u"0": continue
				retC = max(retC, self.sendtoRPI(self.RPI[piU][u"ipNumberPi"], pi, out ) )
		else:
			piU = unicode(piIN)
			if self.RPI[piU][u"piOnOff"]	== u"":	 return	 2
			if self.RPI[piU][u"piOnOff"]	== u"0": return	 2
			if self.RPI[piU][u"ipNumberPi"] == u"":	 return	 2
			retC = self.sendtoRPI(self.RPI[piU][u"ipNumberPi"], piIN, out)
		
		return retC

####-------------------------------------------------------------------------####
	def sendtoRPI(self, ip, pi,	 theString, force = False):
		"""

		:rtype: object
		"""
		try:
			if ip not in self.checkIPSendSocketOk:
				self.checkIPSendSocketOk[ip] = {u"count":0,u"time":0, u"pi": unicode(pi)}
			
			if self.checkIPSendSocketOk[ip][u"count"] > 5 and not force:
				if time.time() + self.checkIPSendSocketOk[ip][u"time"] > 120:
					  self.checkIPSendSocketOk[ip][u"count"] = 0
				else: 
					self.ML.myLog( text =  u"sending to	 pi#"+unicode(pi)+u" "+ip+u" skipped due to recent failure count, reset by dis-enable & enable rPi ;  command-string=" + theString)
					return -1

			if self.ML.decideMyLog(u"OutputDevice"): self.ML.myLog( text =	u"sending to  "+ip+u";	command-string=" + theString)
			   # Create a socket (SOCK_STREAM means a TCP socket)
			sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
			sock.settimeout(3.)
			try:
					# Connect to server and send data
					sock.connect((ip, int(self.rPiCommandPORT)))
					sock.sendall(theString + "\n")
			except	Exception, e:
					if len(unicode(e)) > 5 :
						if	time.time() > self.currentlyBooting:  # NO MSG IF RPIS ARE BOOTING
							self.ML.myLog( text =  u"error in socket-send to rPi:"+str(ip)+"  "+ theString)
							try:	self.ML.myLog( text =  u"line:%s;  err:%s" % (sys.exc_traceback.tb_lineno, e))
							except: pass
							self.checkIPSendSocketOk[ip][u"count"] += 1 
							self.checkIPSendSocketOk[ip][u"time"]	= time.time()
						try:	sock.close()
						except: pass
						return -1
			finally:
					sock.close()
		except	Exception, e:
			if len(unicode(e)) > 5 :
				if	time.time() > self.currentlyBooting: # NO MSG IF RPIS ARE BOOTING
					self.ML.myLog( text =  u"error in socket-send to rPi:"+str(ip)+"  "+ theString)
					self.ML.myLog( text =  u"sendtoRPI in Line '%s' has error='%s'" % (sys.exc_traceback.tb_lineno, e))
					self.ML.myLog( text =  unicode(self.checkIPSendSocketOk))
					self.checkIPSendSocketOk[ip]["count"] += 1 
					self.checkIPSendSocketOk[ip]["time"]   = -time.time()
				try:	sock.close()
				except: pass
				return -1
		self.checkIPSendSocketOk[ip]["count"] = 0 
		self.checkIPSendSocketOk[ip]["time"]  = time.time()
		return 0


####-------------------------------------------------------------------------####
	def playSoundFileCALLBACKmenu(self, valuesDict=None, typeId="", devId=0):
		try:
			valuesDict[u"typeId"]		 = "playSound"
			valuesDict[u"cmd"]			 = "playSound"
			self.setPin(valuesDict)
		except	Exception, e:
			self.ML.myLog( text =  u"playSoundFileCALLBACKmenu in Line '%s' has error='%s'" % (sys.exc_traceback.tb_lineno, e))
			return valuesDict
		return valuesDict

####-------------------------------------------------------------------------####
	def restartPluginCALLBACKaction(self, action1=None, typeId="", devId=0):
		self.quitNow		= "Internal restart requested, ignore indigo warning message >>piBeacon Error ..."
		return


####-------------------------------------------------------------------------####
	def restartPluginCALLBACKmenu(self, valuesDict=None, typeId="", devId=0):
		self.quitNow		 = "Internal restart requested, ignore indigo warning message >>piBeacon Error ..."
		valuesDict[u"MSG"]	 = "internal restart underway, exit menu"
		return valuesDict


####-------------------------------------------------------------------------####
	def resetSprinklerStats(self, valuesDict=None, typeId="", devId=0):
		valuesDict[u"cmd"]		 = "startCalibration"
		self.setPin(valuesDict)


####-------------------------------------------------------------------------####
	def startCalibrationCALLBACKmenu(self, valuesDict=None, typeId="", devId=0):
		valuesDict[u"cmd"]		 = "startCalibration"
		self.setPin(valuesDict)

####-------------------------------------------------------------------------####
	def setnewMessageCALLBACKmenu(self, valuesDict=None, typeId="", devId=0):
		valuesDict[u"cmd"]		 = "newMessage"
		self.setPin(valuesDict)

####-------------------------------------------------------------------------####
	def setresetDeviceCALLBACKmenu(self, valuesDict=None, typeId="", devId=0):
		valuesDict[u"cmd"]		 = "resetDevice"
		self.setPin(valuesDict)
		if valuesDict["typeId"] != "rainSensorRG11": return 
		
		# reseting plugin data for rain sensor:
		piServerNumber = int(valuesDict["piServerNumber"] )
		for dev in indigo.devices.iter("props.isSensorDevice"):
			if dev.deviceTypeId !="rainSensorRG11": continue
			
			for key in ["rainRate","rainRateMinToday","rainRateMaxToday","rainRateMinYesterday","rainRateMaxYesterday","hourRain","lasthourRain","dayRain","lastdayRain","weekRain","lastweekRain","monthRain","lastmonthRain","yearRain","lastyearRain"]:
				self.addToStatesUpdateDict(unicode(dev.id), key, 0)
			self.addToStatesUpdateDict(unicode(dev.id), "resetDate", datetime.datetime.now().strftime(_defaultDateStampFormat))
			self.executeUpdateStatesDict(onlyDevID=str(dev.id),calledFrom="setresetDeviceCALLBACKmenu")

			dev2 = indigo.devices[dev.id]
			props= dev2.pluginProps
			for key in ["hourRainTotal","dayRainTotal" ,"weekRainTotal","monthRainTotal","yearRainTotal"]:
				props[key] = 0
			dev2.replacePluginPropsOnServer(props)
		return 



####-------------------------------------------------------------------------####
	def setMyoutputCALLBACKmenu(self, valuesDict=None, typeId="", devId=0):
		valuesDict[u"typeId"]			 = "myoutput"
		valuesDict[u"cmd"]				 = "myoutput"
		self.setPin(valuesDict)

####-------------------------------------------------------------------------####
	def setMCP4725CALLBACKmenu(self, valuesDict=None, typeId="", devId=0):
		devId = int(valuesDict[u"outputDev"])
		dev = indigo.devices[devId]
		props = dev.pluginProps
		valuesDict[u"typeId"]			 = "setMCP4725"
		valuesDict[u"devId"]			 = dev.id
		valuesDict[u"i2cAddress"]		 = props[u"i2cAddress"]
		valuesDict[u"piServerNumber"]	 = props[u"address"].split(u"-")[1]
		#valuesDict[u"cmd"]				  = "analogWrite"
		self.setPin(valuesDict)

####-------------------------------------------------------------------------####
	def setPCF8591dacCALLBACKmenu(self, valuesDict=None, typeId="", devId=0):
		devId = int(valuesDict[u"outputDev"])
		dev = indigo.devices[devId]
		props = dev.pluginProps
		valuesDict[u"typeId"]			 = "setPCF8591dac"
		valuesDict[u"devId"]			 = dev.id
		valuesDict[u"i2cAddress"]		 = props[u"i2cAddress"]
		valuesDict[u"piServerNumber"]	 = props[u"address"].split(u"-")[1]
		#valuesDict[u"cmd"]				  = "analogWrite"
		self.setPin(valuesDict)


####-------------------------------------------------------------------------####
	def actionControlDimmerRelay(self, action, dev0):
		try:
			props0 = dev0.pluginProps
			if dev0.deviceTypeId == "neopixel-dimmer":
				valuesDict={}
			 
				try:
						devNEO		= indigo.devices[int(props0[u"neopixelDevice"])]
						typeId		= devNEO.deviceTypeId
						devId		= devNEO.id
						propsNEO	= devNEO.pluginProps
						devTypeNEO	= propsNEO[u"devType"]
						try: 
							xxx= propsNEO[u"devType"].split(u"x")
							ymax = int(xxx[0])
							xmax = int(xxx[1])
						except	Exception, e:
							self.ML.myLog( text =  u"actionControlDimmerRelay in Line '%s' has error='%s'" % (sys.exc_traceback.tb_lineno, e))
							return
				except	Exception, e:
					self.ML.myLog( text =  u"actionControlDimmerRelay in Line '%s' has error='%s'" % (sys.exc_traceback.tb_lineno, e))
					return

				if self.ML.decideMyLog(u"OutputDevice"): self.ML.myLog( text = unicode(action) )
	 
				if not action.configured:
					self.ML.myLog( text = "actionControlDimmerRelay neopixel-dimmer not enabled:" +unicode(dev0.name) )
					return
				###action = dev.deviceAction
				if u"pixelMenulist" in props0 and props0[u"pixelMenulist"] !="":
					 position = props0[u"pixelMenulist"]
					 if position.find(u"*") >-1:
						position='[u"*","*"]'
				else:
					position = u"["
					for ii in range(100):
						mmm = "pixelMenu"+unicode(ii)
						if	mmm not in props0 or props0[mmm] ==u"":		 continue
						if len(props0[mmm].split(u",")) !=2:			continue
						position += u"["+props0[mmm]+"],"
					position  = position.strip(u",") +"]"
				position = json.loads(position)

				chList =[]


				RGB = [0,0,0,-1]

				channelKeys={u"redLevel":0,"greenLevel":1,"blueLevel":2,"whiteLevel":3}
				if action.deviceAction == indigo.kDeviceAction.TurnOn:
					chList.append({'key':"onOffState", 'value':True})
					RGB=[255,255,255,-1]
				elif action.deviceAction == indigo.kDeviceAction.TurnOff:
					chList.append({'key':"onOffState", 'value':False})
					RGB=[0,0,0,-1]
				elif action.deviceAction == indigo.kDeviceAction.SetBrightness:
					brightness	   = float(action.actionValue)
					brightnessByte = int(round(2.55 * brightness ))	 ### 0..255
					RGB[3]	= brightnessByte
				elif action.deviceAction == indigo.kDeviceAction.SetColorLevels:
					actionColorVals = action.actionValue
					for channel in actionColorVals:
						if channel in channelKeys:
							brightness	   = float(actionColorVals[channel])  ## 0...100
							brightnessByte = int(round(2.55 * brightness ))	 ### 0..255
							if channel in channelKeys:
								RGB[channelKeys[channel]] = brightnessByte
							
				
				if RGB[3] !=-1:
					white = int((RGB[3])/(2.55))
					for col in	channelKeys:
						ii = channelKeys[col]
						RGB[ii]=RGB[3]
						chList.append({'key':col, 'value':white})
				else:
					RGB[3] = int(  round( (RGB[0]+RGB[1]+RGB[2])/3. )  )  ## 0..3*2.55=7.65

				for channel in channelKeys:
					if channel in dev0.states:
						chList.append(	{  'key':channel, 'value':int(round(RGB[channelKeys[channel]]/2.55))  }	 )
					
				if max(RGB) > 55: chList.append({'key':"onOffState", 'value':True})	   ## scale is 0-255
				else:			  chList.append({'key':"onOffState", 'value':False})

				#if "whiteLevel" in chList: del chList[u"whiteLevel"]
				self.execUpdateStatesList(dev0,chList)

				ppp =[]
				if unicode(position).find(u"*") > -1:
					ppp=[u"*","*",RGB[0],RGB[1],RGB[2]]
				else:
					for p in position:
						p[0] = min(	 max((ymax-1),0),int(p[0])	)
						p[1] = min(	 max((xmax-1),0),int(p[1])	)
						ppp.append([p[0],p[1],RGB[0],RGB[1],RGB[2]])
				if u"speedOfChange" in props0 and props0[u"speedOfChange"] !="":
					try:
						valuesDict[u"speedOfChange0"]		  = int(props0[u"speedOfChange"])
					except	Exception, e:
						self.ML.myLog( text =  u"actionControlDimmerRelay in Line '%s' has error='%s'" % (sys.exc_traceback.tb_lineno, e))
				if self.ML.decideMyLog(u"OutputDevice"): self.ML.myLog( text = "props0 "+unicode(props0) )

				valuesDict[u"outputDev"]		 = devId
				valuesDict[u"type0"]			 = "points"
				valuesDict[u"position0"]		 = json.dumps(ppp)
				valuesDict[u"display0"]			 = "immediate"
				valuesDict[u"reset0"]			 = ""
				valuesDict[u"restoreAfterBoot"]	 = True
			
				if self.ML.decideMyLog(u"OutputDevice"): self.ML.myLog( text = "valuesDict "+unicode(valuesDict) )
			
				self.setneopixelCALLBACKmenu(valuesDict)


				return
			
			
			#####  GPIO		 
			else:
				dev= dev0
			props = dev.pluginProps

			#self.ML.myLog( text = "deviceAction \n"+ unicode(action)+"\n props "+unicode(props))
			valuesDict={}
			valuesDict[u"outputDev"]=dev.id
			valuesDict[u"piServerNumber"] = props[u"piServerNumber"]
			valuesDict[u"deviceDefs"]	  = props[u"deviceDefs"]
			if dev.deviceTypeId ==u"OUTPUTgpio-1-ONoff":
				valuesDict[u"typeId"]	  = "OUTPUTgpio-1-ONoff"
				typeId					 = "OUTPUTgpio-1-ONoff"
			else: 
				valuesDict[u"typeId"]	  = "OUTPUTgpio-1"
				typeId					 = "OUTPUTgpio-1"
			if u"deviceDefs" in props:
				dd = json.loads(props[u"deviceDefs"])
				if len(dd) >0 and "gpio" in dd[0]:
					valuesDict[u"GPIOpin"]	  = dd[0][u"gpio"]
				elif "gpio" in props:
					valuesDict[u"GPIOpin"] = props[u"gpio"]
				else:
					self.ML.myLog( text = "deviceAction error,	gpio not defined action=" +	 (unicode(action)).replace(u"\n","")+"\n props "+unicode(props))
			elif "gpio" in props:
				valuesDict[u"GPIOpin"] = props[u"gpio"]
			else:
				self.ML.myLog( text = "deviceAction error,	gpio not defined action=" +	 (unicode(action)).replace(u"\n","")+"\n props "+unicode(props))
			   
				

			###### TURN ON ######
			if action.deviceAction == indigo.kDimmerRelayAction.TurnOn:
				valuesDict[u"cmd"] = "up"

			###### TURN OFF ######
			elif action.deviceAction == indigo.kDimmerRelayAction.TurnOff:
				valuesDict[u"cmd"] = "down"

			###### TOGGLE ######
			elif action.deviceAction == indigo.kDimmerRelayAction.Toggle:
				newOnState = not dev.onState
				if newOnState: valuesDict[u"cmd"] = "up"
				else:		   valuesDict[u"cmd"] = "down"

			###### SET BRIGHTNESS ######
			elif action.deviceAction == indigo.kDimmerRelayAction.SetBrightness:
				newBrightness = action.actionValue
				valuesDict[u"cmd"] = "analogWrite"
				valuesDict[u"analogValue"] = unicode(float(newBrightness))


			###### BRIGHTEN BY ######
			elif action.deviceAction == indigo.kDimmerRelayAction.BrightenBy:
				newBrightness = dev.brightness + action.actionValue
				if newBrightness > 100:
					newBrightness = 100
				valuesDict[u"cmd"] = "analogWrite"
				valuesDict[u"analogValue"] = unicode(float(newBrightness))

			###### DIM BY ######
			elif action.deviceAction == indigo.kDimmerRelayAction.DimBy:
				newBrightness = dev.brightness - action.actionValue
				if newBrightness < 0:
					newBrightness = 0
				valuesDict[u"cmd"] = "analogWrite"
				valuesDict[u"analogValue"] = unicode(float(newBrightness))

			else:
				return

			self.setPinCALLBACKmenu(valuesDict, typeId)
			return
		except	Exception, e:
			self.ML.myLog( text =  u"actionControlDimmerRelay in Line '%s' has error='%s'" % (sys.exc_traceback.tb_lineno, e))


####-------------------------------------------------------------------------####
	def actionControlGeneral(self, action, dev):
		###### STATUS REQUEST ######
		if action.deviceAction == indigo.kDeviceGeneralAction.RequestStatus:
			indigo.server.log(u"sent \"%s\" %s" % (dev.name, u"status request"))

####-------------------------------------------------------------------------####
	def setBacklightBrightness(self, pluginAction, dev):
		return

####-------------------------------------------------------------------------####
	def confirmdeviceIDOUTPUTBUTTONmenu(self, valuesDict=None, typeId="", devId=""):
		try:
			devId = int(valuesDict[u"outputDev"])
			dev = indigo.devices[devId]
			self.outdeviceForOUTPUTgpio = devId
		except:
			self.outdeviceForOUTPUTgpio = ""
		return valuesDict

####-------------------------------------------------------------------------####
	def filterINPUTdevices(self, valuesDict=None, filter="", typeId="", devId=""):
			list = []
			for dev in indigo.devices.iter("props.isSensorDevice"):
				if dev.deviceTypeId.find(u"INPUTgpio") == -1 and dev.deviceTypeId.find(u"INPUTtouch") == -1 and dev.deviceTypeId.find(u"INPUTpulse") == -1: continue
				list.append((dev.id, dev.name))
			return list

####-------------------------------------------------------------------------####
	def filterOUTPUTdevicesACTION(self, valuesDict=None, filter="", typeId="",devId=""):
		list = []
		for dev in indigo.devices.iter("props.isOutputDevice"):
			if dev.deviceTypeId.find(u"OUTPUTgpio") ==-1: continue
			list.append((dev.id,dev.name))
		return list

####-------------------------------------------------------------------------####
	def filterOUTPUTchannelsACTION(self, valuesDict=None, filter="", typeId="", devId=""):
		okList = []
		#self.ML.myLog( text =	u"self.outdeviceForOUTPUTgpio " + unicode(self.outdeviceForOUTPUTgpio))
		if self.outdeviceForOUTPUTgpio ==u"": return []
		try:	dev	  = indigo.devices[int(self.outdeviceForOUTPUTgpio)]
		except: return []
		try:
			props= dev.pluginProps
			gpioList= json.loads(props[u"deviceDefs"])
			list = copy.deepcopy(_GlobalConst_allGPIOlist)
			#self.ML.myLog( text =	u"gpioList " + unicode(props))
			for ll in list:
				if ll[0] ==u"0": continue
				#self.ML.myLog( text =	u"ll "+ unicode(ll))
				for ii in range(len(gpioList)):
					if u"gpio" not in  gpioList[ii]: continue
					if gpioList[ii][u"gpio"] != ll[0]: continue
					okList.append((ll[0],"OUTPUT_"+unicode(ii)+" "+ll[1]))
					break
			#self.ML.myLog( text = unicode(okList))
		except	Exception, e:
			self.ML.myLog( text =  u"filterOUTPUTchannelsACTION in Line '%s' has error='%s'" % (sys.exc_traceback.tb_lineno, e))
		return okList


####-------------------------------------------------------------------------####
	def filterTimezones(self, valuesDict=None, filter="", typeId="", devId=""):

		timeZones =[]
		xxx=[]
		for ii in range(-12,13):
			if ii<0:
				timeZones.append(u"/Etc/GMT+" +str(abs(ii)))
			else:
				timeZones.append(u"/Etc/GMT-"+str(ii))
		timeZones[12+12] = "Pacific/Auckland"
		timeZones[11+12] = "Pacific/Pohnpei"
		timeZones[10+12] = "Australia/Melbourne"
		timeZones[9+12]	 = "Asia/Tokyo"
		timeZones[8+12]	 = "Asia/Shanghai"
		timeZones[7+12]	 = "Asia/Saigon"
		timeZones[6+12]	 = "Asia/Dacca"
		timeZones[5+12]	 = "Asia/Karachi"
		timeZones[4+12]	 = "Asia/Dubai"
		timeZones[3+12]	 = "/Europe/Moscow"
		timeZones[2+12]	 = "/Europe/Helsinki"
		timeZones[1+12]	 = "/Europe/Berlin"
		timeZones[0+12]	 = "/Europe/London"
		timeZones[-1+12] = "Atlantic/Cape_Verde"
		timeZones[-2+12] = "Atlantic/South_Georgia"
		timeZones[-3+12] = "America/Buenos_Aires"
		timeZones[-4+12] = "America/Puerto_Rico"
		timeZones[-5+12] = "/US/Eastern"
		timeZones[-6+12] = "/US/Central"
		timeZones[-7+12] = "/US/Mountain"
		timeZones[-8+12] = "/US/Pacific"
		timeZones[-9+12] = "/US/Alaska"
		timeZones[-10+12] = "Pacific/Honolulu"
		timeZones[-11+12] = "US/Samoa"
		for ii in range(len(timeZones)):
			if ii > 12:
				xxx.append((str(ii-12)+" "+timeZones[ii], u"+"+str(abs(ii-12))+" "+timeZones[ii]))
			else:
				xxx.append((str(ii-12)+" "+timeZones[ii], (str(ii-12))+" "+timeZones[ii]))
		return xxx
		
####-------------------------------------------------------------------------####
	def setPinCALLBACKmenu(self, valuesDict=None, typeId=""):
		#self.ML.myLog( text =	unicode(valuesDict))

		try:
			devId = int(valuesDict[u"outputDev"])
			dev = indigo.devices[devId]
			props = dev.pluginProps
			valuesDict[u"piServerNumber"] = props[u"piServerNumber"]
			if u"deviceDefs" not in props:
				self.ML.myLog( text =  u"deviceDefs not in valuesDict, need to define OUTPUT device properly " )
				return valuesDict
			valuesDict[u"deviceDefs"] = props[u"deviceDefs"]
		except:
			self.ML.myLog( text =  u"device not properly defined, please define OUTPUT ")
			return valuesDict

		#self.outdeviceForOUTPUTgpio = ""
		dev = indigo.devices[devId]
		props = dev.pluginProps
		valuesDict[u"typeId"]	  = dev.deviceTypeId
		valuesDict[u"devId"]	  = devId
		self.setPin(valuesDict)


####-------------------------------------------------------------------------####
	def setDelay(self, startAtDateTimeIN=""):
		startAtDateTimeIN = unicode(startAtDateTimeIN)
		if self.ML.decideMyLog(u"OutputDevice"): self.ML.myLog( text = "startAtDateTimeIN: "+ startAtDateTimeIN)
		try:
			if len(startAtDateTimeIN) ==0 :	 return 0
			lsTime = len(startAtDateTimeIN)
			if (lsTime < 11 and startAtDateTimeIN.find(u":") == -1 and startAtDateTimeIN.find(u"-") == -1) or (
					startAtDateTimeIN.find(u".") and 9 < lsTime < 14):	## max 9,999,999 = 120 days, vs 2014 12 12 0 0 00 date string
					try:
						sd =   float(startAtDateTimeIN)
						if sd < 1: 
							return	0
						return	float(startAtDateTimeIN)
					except: 
						 return 0
			else:
				try:
					if self.ML.decideMyLog(u"OutputDevice"): self.ML.myLog( text = "startAtDateTimeIN: doing datetime")
					startAtDateTime	   = startAtDateTimeIN.replace(u"-","").replace(u":","").replace(u" ","").replace(u"/","").replace(u".","").replace(u",","")
					startAtDateTime	   = startAtDateTime.ljust(14,"0")
					return	 max(0, time.mktime( datetime.datetime.strptime(startAtDateTime,_defaultDateStampFormat+".%f").timetuple() ) -time.time() )
				except	Exception, e:
					self.ML.myLog( text =  u"setDelay in Line '%s' has error='%s'" % (sys.exc_traceback.tb_lineno, e))
					return 0
		except	Exception, e:
			self.ML.myLog( text =  u"isetDelay n Line '%s' has error='%s'" % (sys.exc_traceback.tb_lineno, e))
		return 0



####-------------------------------------------------------------------------####
	def setPin(self, valuesDict=None):
		#self.ML.myLog( text =	unicode(valuesDict))

		#self.outdeviceForOUTPUTgpio =""
		try:
			if u"piServerNumber" not in valuesDict:
				self.ML.myLog( text =  u"setPIN missing parameter: piServerNumber not defined")
				return
			pi = int(valuesDict[u"piServerNumber"])
			if pi < 0 or pi >= _GlobalConst_numberOfRPI:
				self.ML.myLog( text =  u"setPIN bad parameter: piServerNumber out of range: " + unicode(pi))
				return

			if self.RPI[unicode(pi)][u"piOnOff"] != "1":
				self.ML.myLog( text =  u"setPIN bad parameter: piServer is not enabled: " + unicode(pi))
				return

			try:
				if not indigo.devices[int(self.RPI[unicode(pi)][u"piDevId"])].enabled:
					return 
			except:
				return

			ip = self.RPI[unicode(pi)][u"ipNumberPi"]
			typeId = valuesDict[u"typeId"]

			startAtDateTime = 0
			if u"startAtDateTime" in valuesDict:
				  startAtDateTime = self.setDelay(startAtDateTimeIN=valuesDict[u"startAtDateTime"])

			if u"restoreAfterBoot"	 in valuesDict:
				restoreAfterBoot   = valuesDict[u"restoreAfterBoot"]
				if restoreAfterBoot !="1": restoreAfterBoot = "0"
			else:
				restoreAfterBoot ="0"

			if u"pulseUp"		 in valuesDict:
				try:
					pulseUp = float(valuesDict[u"pulseUp"])
				except:
					pulseUp = 0.
			else:
				pulseUp = 0.

			if u"pulseDown"		   in valuesDict:
				try:
					pulseDown = float(valuesDict[u"pulseDown"])
				except:
					pulseDown = 0.
			else:
				pulseDown = 0.

			if u"nPulses"		 in valuesDict:
				try:
					nPulses = int(valuesDict[u"nPulses"])
				except:
					nPulses = 0
			else:
				nPulses = 0


			if u"analogValue" in valuesDict:
				try:
					analogValue = float(valuesDict[u"analogValue"])
				except:
					analogValue = 0.
			else:
				analogValue = 0.
				
			if u"rampTime" in valuesDict:
				try:
					rampTime = float(valuesDict[u"rampTime"])
				except:
					rampTime = 0.
			else:
				rampTime = 0.




			inverseGPIO=False

			if typeId == "myoutput":
				if u"text" not in valuesDict:
					self.ML.myLog( text =  u"setPIN bad parameter: text not supplied: for pi#" + unicode(pi))
					return

				if self.ML.decideMyLog(u"OutputDevice"): self.ML.myLog( text =	u"sending command to rPi at " + ip + "; port: " + unicode(self.rPiCommandPORT) + "; cmd: myoutput;	"+ valuesDict[u"text"]		)
				self.sendGPIOCommand(ip, pi, typeId, u"myoutput",  text=valuesDict[u"text"])
				return


			if typeId == "playSound":
					if u"soundFile" not in valuesDict:
						self.ML.myLog( text =  u"setPIN bad parameter: soundFile not supplied: for pi#" + unicode(pi))
						return
					try:
						line = "\n##=======use this as a python script in an action group action :=====\n"
						line +="plug = indigo.server.getPlugin(\"com.karlwachs.piBeacon\")"
						line +="\nplug.executeAction(\"playSoundFile\" , props ={u"
						line +="\n	 \"outputDev\":\""+unicode(valuesDict[u"outputDev"])+"\""
						line +="\n	,\"device\":\"" +unicode(typeId)+"\""
						line +="\n	,\"restoreAfterBoot\":"+unicode(restoreAfterBoot)
						line +="\n	,\"startAtDateTime\":\""+unicode(startAtDateTime)+"\""
						line +="\n	,\"cmd\":\""+valuesDict[u"cmd"]+"\""
						line +="\n	,\"soundFile\":\""+valuesDict["soundFile"]+"\"})\n"
						line+= "##=======	end	   =====\n"
						if self.ML.decideMyLog(u"OutputDevice"): self.ML.myLog( text = "\n"+line+"\n")
					except:
						if self.ML.decideMyLog(u"OutputDevice"): self.ML.myLog( text =	u"sending command to rPi at " + ip + "; port: " + unicode(self.rPiCommandPORT) + "; cmd: " + valuesDict[u"cmd"] + ";  " + valuesDict[u"soundFile"])
					self.sendGPIOCommand(ip, pi,typeId, valuesDict[u"cmd"], soundFile=valuesDict[u"soundFile"])
					return

			if u"cmd" not in valuesDict:
				self.ML.myLog( text =  u" setPIN bad parameter: cmd not set:")
				return
			cmd = valuesDict[u"cmd"]

			if cmd not in _GlobalConst_allowedCommands:
				self.ML.myLog( text =  u" setPIN bad parameter: cmd bad:" + cmd+ u" allowed commands= " + unicode(_GlobalConst_allowedCommands))
				return

			if cmd == "newMessage":
				if u"typeId" not in valuesDict:
					self.ML.myLog( text =  u"setPIN bad parameter: typeId not supplied: for pi#" + unicode(pi))
					return

				if self.ML.decideMyLog(u"OutputDevice"): self.ML.myLog( text =	u"sending command to rPi at " + ip + "; port: " + unicode(self.rPiCommandPORT) + "; cmd: " + valuesDict[u"cmd"] + ";  " + valuesDict[u"typeId"])
				self.sendGPIOCommand(ip, pi, typeId, valuesDict[u"cmd"])
				return

			if cmd == "resetDevice":
				if u"typeId" not in valuesDict:
					self.ML.myLog( text =  u"setPIN bad parameter: typeId not supplied: for pi#" + unicode(pi))
					return

				if self.ML.decideMyLog(u"OutputDevice"): self.ML.myLog( text =	u"sending command to rPi at " + ip + "; port: " + unicode(self.rPiCommandPORT) + "; cmd: " + valuesDict[u"cmd"] + ";  " + valuesDict[u"typeId"])
				self.sendGPIOCommand(ip, pi, typeId, valuesDict[u"cmd"])
				return

			if cmd == "startCalibration":
				if u"typeId" not in valuesDict:
					self.ML.myLog( text =  u"setPIN bad parameter: typeId not supplied: for pi#" + unicode(pi))
					return

				if self.ML.decideMyLog(u"OutputDevice"): self.ML.myLog( text =	u"sending command to rPi at " + ip + "; port: " + unicode(self.rPiCommandPORT) + "; cmd: " + valuesDict[u"cmd"] + ";  " + valuesDict[u"typeId"])
				self.sendGPIOCommand(ip, pi, typeId, valuesDict[u"cmd"])
				return


			try:
				devIds = unicode(valuesDict[u"devId"])
				devId = int(devIds)
				dev = indigo.devices[devId]
				props=dev.pluginProps
			except:
				self.ML.myLog( text =  u" setPIN bad parameter: OUTPUT device not created: for pi: " + unicode(pi) )
				return

			if typeId in [u"setMCP4725","setPCF8591dac"]:
				try:
					i2cAddress = props[u"i2cAddress"]
					out = ""
					# _GlobalConst_allowedCommands		=[u"up","down","pulseUp","pulseDown","continuousUpDown","disable"]	# commands support for GPIO pins
					if cmd == "analogWrite":
						out = cmd
					elif cmd == "pulseUp":
						out = cmd + "," + unicode(pulseUp)
					elif cmd == "pulseDown":
						out = cmd + "," + unicode(pulseDown)
					elif cmd == "continuousUpDown":
						out = cmd + "," + unicode(pulseUp) + "" + unicode(pulseUp) + "," + unicode(nPulses)
					out = cmd + "," + unicode(analogValue)
					out = cmd + "," + unicode(rampTime)
					self.addToStatesUpdateDict(unicode(dev.id),"OUTPUT", out,dev=dev)
				except	Exception, e:
					self.ML.myLog( text =  u"setPIN in Line '%s' has error='%s'" % (sys.exc_traceback.tb_lineno, e))
					outN = 0
				try:
					line = "\n##=======use this as a python script in an action group action :=====\n"
					line +="plug = indigo.server.getPlugin(\"com.karlwachs.piBeacon\")"
					line +="\nplug.executeAction(\"set"+typeId+"\" , props ={u"
					line +="\n	 \"outputDev\":\""+unicode(valuesDict[u"outputDev"])+"\""
					line +="\n	,\"device\":\"" +unicode(typeId)+"\""
					line +="\n	,\"restoreAfterBoot\":"+unicode(restoreAfterBoot)
					line +="\n	,\"startAtDateTime\":\""+unicode(startAtDateTime)+"\""
					line +="\n	,\"cmd\":\""+valuesDict[u"cmd"]+"\""
					line +="\n	,\"pulseUp\":\""+unicode(pulseUp)+"\""
					line +="\n	,\"pulseDown\":\""+unicode(pulseDown)+"\""
					line +="\n	,\"rampTime\":\""+unicode(rampTime)+"\""
					line +="\n	,\"analogValue\":\""+unicode(analogValue)+"\"})\n"
					line+= "##=======	end	   =====\n"
					if self.ML.decideMyLog(u"OutputDevice"): self.ML.myLog( text = "\n"+line+"\n")
				except:
					if self.ML.decideMyLog(u"OutputDevice"): self.ML.myLog( text = u"sending command to rPi at " + ip + "; port: " + unicode(self.rPiCommandPORT) +
							   u"; cmd: " + unicode(cmd) + ";  pulseUp: " + unicode(pulseUp) + ";  pulseDown: " +
							   unicode(pulseDown) + ";	nPulses: " + unicode(nPulses) + ";	analogValue: " + unicode(analogValue)+ ";  rampTime: " + unicode(rampTime)+ 
							   u";	restoreAfterBoot: " + unicode(restoreAfterBoot)+ ";	 startAtDateTime: " + startAtDateTime)

				self.sendGPIOCommand(ip, pi, typeId, cmd, i2cAddress=i2cAddress,pulseUp=pulseUp, pulseDown=pulseDown, nPulses=nPulses, analogValue=analogValue,rampTime=rampTime, restoreAfterBoot=restoreAfterBoot , startAtDateTime=startAtDateTime, inverseGPIO =inverseGPIO )
				self.executeUpdateStatesDict(onlyDevID = str(dev.id), calledFrom="setPin")
				return

			if typeId.find(u"OUTPUTgpio") > -1 :
				if u"GPIOpin" in valuesDict:
					GPIOpin = valuesDict[u"GPIOpin"]
					deviceDefs = json.loads(valuesDict[u"deviceDefs"])
					output="0"
					for nn in range(len(deviceDefs)):
						if u"gpio" in deviceDefs[nn]:
							if GPIOpin == deviceDefs[nn][u"gpio"] :
								output= unicode(nn)
								break
				elif  "OUTPUT" in valuesDict:
					output = int(valuesDict[u"OUTPUT"])
					deviceDefs = json.loads(valuesDict[u"deviceDefs"])
					if output <= len(deviceDefs):
						if u"gpio" in deviceDefs[output]:
							GPIOpin = deviceDefs[output][u"gpio"]
						else:
							self.ML.myLog( text =  u" setPIN bad parameter: no GPIOpin defined:" + unicode(valuesDict))
							return
					else:
						self.ML.myLog( text =  u" setPIN bad parameter: no GPIOpin defined:" + unicode(valuesDict))
						return
				else:
					self.ML.myLog( text =  u" setPIN bad parameter: no GPIOpin defined:" + unicode(valuesDict))
					return
				if deviceDefs[int(output)][u"outType"] == "0": inverseGPIO = False
				else:										   inverseGPIO = True

				if typeId == "OUTPUTgpio-1":
					analogValue = float(analogValue)
					b = ""
					if cmd == "up":
						b = 100
					elif cmd == "down":
						b = 0
					elif cmd == "analogWrite":
						b = int(float(analogValue))
					if b != "" and	"onOffState" in dev.states:
						self.addToStatesUpdateDict(unicode(dev.id),"brightnessLevel", b,dev=dev)
						if b == 100: 
							self.addToStatesUpdateDict(unicode(dev.id),"onOffState", True)
						if b == 0:	 
							self.addToStatesUpdateDict(unicode(dev.id),"onOffState", False)
				if typeId == "OUTPUTgpio-1-ONoff":
					if cmd == "analogWrite": cmd ="up"
					analogValue =100
					b = ""
					if cmd == "up":
						analogValue =100
						b = 100
					elif cmd == "down":
						analogValue =0
						b = 0
					if b != "" and	"onOffState" in dev.states:
						if b == 100: 
							self.addToStatesUpdateDict(unicode(dev.id),"onOffState", True,dev=dev)
						if b == 0:	 
							self.addToStatesUpdateDict(unicode(dev.id),"onOffState", False)


				try:
					out = ""
					# _GlobalConst_allowedCommands		=[u"up","down","pulseUp","pulseDown","continuousUpDown","disable"]	# commands support for GPIO pins
					if cmd == "up" or cmd == "down":
						out = cmd
					elif cmd == "pulseUp":
						out = cmd + "," + unicode(pulseUp)
					elif cmd == "pulseDown":
						out = cmd + "," + unicode(pulseDown)
					elif cmd == "continuousUpDown":
						out = cmd + "," + unicode(pulseUp) + "" + unicode(pulseUp) + "," + unicode(nPulses)
					elif cmd == "rampUp" or cmd == "rampDown" or cmd == "rampUpDown":
						out = cmd + "," + unicode(pulseUp) + "" + unicode(pulseUp) + "," + unicode(nPulses)+ "," + unicode(rampTime)
					elif cmd == "analogWrite":
						out = cmd + "," + unicode(analogValue)
					outN = int(output)
					if "OUTPUT_%0.2d"%outN in dev.states: self.addToStatesUpdateDict(unicode(dev.id),"OUTPUT_%0.2d"%outN, out,dev=dev)
				except	Exception, e:
					self.ML.myLog( text =  u"setPIN in Line '%s' has error='%s'" % (sys.exc_traceback.tb_lineno, e))
					outN = 0
				try:
					line = "\n##=======use this as a python script in an action group action :=====\n"
					line +="plug = indigo.server.getPlugin(\"com.karlwachs.piBeacon\")"
					line +="\nplug.executeAction(\"setPins\" , props ={u"
					line +="\n	 \"outputDev\":\""+unicode(valuesDict[u"outputDev"])+"\""
					line +="\n	,\"device\":\"" +unicode(typeId)+"\""
					line +="\n	,\"restoreAfterBoot\":"+unicode(restoreAfterBoot)
					line +="\n	,\"startAtDateTime\":\""+unicode(startAtDateTime)+"\""
					line +="\n	,\"cmd\":\""+valuesDict[u"cmd"]+"\""
					line +="\n	,\"pulseUp\":\""+unicode(pulseUp)+"\""
					line +="\n	,\"pulseDown\":\""+unicode(pulseDown)+"\""
					line +="\n	,\"rampTime\":\""+unicode(rampTime)+"\""
					line +="\n	,\"analogValue\":\""+unicode(analogValue)+"\""
					line +="\n	,\"GPIOpin\":\""+unicode(GPIOpin)+"\"})\n"
					line+= "##=======	end	   =====\n"
					if self.ML.decideMyLog(u"OutputDevice"): self.ML.myLog( text = "\n"+line+"\n")
				except:
					if self.ML.decideMyLog(u"OutputDevice"): self.ML.myLog( text = u"sending command to rPi at " + ip + "; port: " + unicode(self.rPiCommandPORT) + " pin: " +
							   unicode(GPIOpin) + "; GPIOpin: " + unicode(GPIOpin) + "/OUTPUT#" + unicode(outN) + "; cmd: " +
							   unicode(cmd) + ";  pulseUp: " + unicode(pulseUp) + ";  pulseDown: " +
							   unicode(pulseDown) + ";	nPulses: " + unicode(nPulses) + ";	analogValue: " + unicode(analogValue)+ "; rampTime: " + unicode(rampTime)+ ";  restoreAfterBoot: " + unicode(restoreAfterBoot)+ ";	startAtDateTime: " + startAtDateTime)

				self.sendGPIOCommand(ip, pi, typeId, cmd, GPIOpin=GPIOpin, pulseUp=pulseUp, pulseDown=pulseDown, nPulses=nPulses, analogValue=analogValue, rampTime=rampTime, restoreAfterBoot=restoreAfterBoot , startAtDateTime=startAtDateTime, inverseGPIO =inverseGPIO )
				self.executeUpdateStatesDict(onlyDevID= devIds, calledFrom="setPin END")
				return
			
			self.ML.myLog( text =  u"setPIN:   no condition met, returning")

		except	Exception, e:
			self.ML.myLog( text =  u"setPin in Line '%s' has error='%s'" % (sys.exc_traceback.tb_lineno, e))

####-------------------------------------------------------------------------####
	def buttonConfirmoldIPCALLBACK(self, valuesDict=None, typeId="", devId=0):
		pi = int(valuesDict[u"PINumberForIPChange"])
		valuesDict[u"oldipNumberPi"] = self.RPI[unicode(pi)][u"ipNumberPi"]
		valuesDict[u"newipNumberPi"] = self.RPI[unicode(pi)][u"ipNumberPi"]
		return valuesDict


####-------------------------------------------------------------------------####
	def buttonConfirmIPnumberCALLBACK(self, valuesDict=None, typeId="", devId=0):
		pi = int(valuesDict[u"PINumberForIPChange"])
		if valuesDict[u"oldipNumberPi"] != valuesDict[u"newipNumberPi"]:
			self.RPI[unicode(pi)][u"ipNumberPiSendTo"] = valuesDict[u"oldipNumberPi"]
			self.RPI[unicode(pi)][u"ipNumberPi"] = valuesDict[u"newipNumberPi"]
			self.setONErPiV(pi,"piUpToDate",[u"updateParamsFTP","rebootSSH"])
			self.rPiRestartCommand[pi]		= "rebootSSH"  ## which part need to restart on rpi
			self.configureWifi(pi)
			self.RPI[unicode(pi)][u"ipNumberPiSendTo"] = self.RPI[unicode(pi)][u"ipNumberPi"]
		return valuesDict


	###########################		MENU   END #################################




	###########################		ACTION	#################################

####-------------------------------------------------------------------------####
	def sendConfigviaSocketCALLBACKaction(self, action1=None, typeId="", devId=0):
		try:
			v = action1.props
			if v[u"configurePi"] ==u"": return
			piS= unicode(v[u"configurePi"])
			ip= self.RPI[piS][u"ipNumberPi"]
			if len(ip.split(u".")) != 4:
				self.ML.myLog( text =  u"sendingFile to rPI,  bad parameters:"+piS+"  "+ip+"  "+ unicode(v))
				return
			try:
				if not	indigo.devices[int(self.RPI[piS][u"piDevId"])].enabled: return
			except:
				return

			fileContents = self.makeParametersFile(piS,retFile=True)
			if len(fileContents) >0:
				if self.ML.decideMyLog(u"OutputDevice"): self.ML.myLog( text =	u"sending parameters file via socket: "+unicode(v)+" \n"+fileContents)
				self.sendFileToRPIviaSocket(ip,piS,"/home/pi/pibeacon/parameters",fileContents,fileMode="w")

		except	Exception, e:
			self.ML.myLog( text =  u"sendConfigviaSocketCALLBACKaction in Line '%s' has error='%s'" % (sys.exc_traceback.tb_lineno, e))
		return


####-------------------------------------------------------------------------####
	def sendExtraPagesToRpiViaSocketCALLBACKaction(self, action1=None, typeId="", devId=0):
		try:
			v = action1.props
			if v[u"configurePi"] ==u"": return
			piS= unicode(v[u"configurePi"])
			ip= self.RPI[piS][u"ipNumberPi"]
			if len(ip.split(u".")) != 4:
				self.ML.myLog( text =  u"sendingFile to rPI,  bad parameters:"+piS+"  "+ip+"  "+ unicode(v))
				return
			try:
				if not	indigo.devices[int(self.RPI[piS][u"piDevId"])].enabled: return
			except:
				return
				
			#if self.ML.decideMyLog(u"OutputDevice"): self.ML.myLog( text =	 u"sending extrapage file via socket: "+unicode(v))
			fileContents =[]
			#self.ML.myLog( text = unicode(propsOut))
			for ii in range(10):																			
				if u"extraPage"+unicode(ii)+"Line0" in v and "extraPage"+unicode(ii)+"Line1" in v and "extraPage"+unicode(ii)+"Color" in v:
					line0 = self.convertVariableOrDeviceStateToText(v[u"extraPage"+unicode(ii)+"Line0"])
					line1 = self.convertVariableOrDeviceStateToText(v[u"extraPage"+unicode(ii)+"Line1"])
					color = self.convertVariableOrDeviceStateToText(v[u"extraPage"+unicode(ii)+"Color"])
					fileContents.append([line0,line1,color])
			if len(fileContents) >0:
				self.sendFileToRPIviaSocket(ip, piS, "/home/pi/pibeacon/temp/extraPageForDisplay.inp",json.dumps(fileContents),fileMode="w",touchFile=False)

		except	Exception, e:
			self.ML.myLog( text =  u"sendExtraPagesToRpiViaSocketCALLBACKaction in Line '%s' has error='%s'" % (sys.exc_traceback.tb_lineno, e))
		return

####-------------------------------------------------------------------------####
	def setPinCALLBACKaction(self, action1):
		valuesDict = action1.props
		try:
			try:
				devId = int(valuesDict[u"outputDev"])
				dev = indigo.devices[devId]
			except:
				try:
					dev = indigo.devices[valuesDict[u"outputDev"]]
					devId=dev.id
				except:
					self.ML.myLog( text =  u"device not in valuesDict, need to define parameters properly ")
					return

			props = dev.pluginProps
			if u"deviceDefs" not in props:
				self.ML.myLog( text =  u"deviceDefs not in valuesDict, need to define OUTPUT device properly ")
				return
			valuesDict[u"deviceDefs"] = props[u"deviceDefs"]
			valuesDict[u"piServerNumber"] = props[u"piServerNumber"]


		except:
			self.ML.myLog( text =  u"setPinCALLBACKaction device not properly defined, please define OUTPUT ")
			return valuesDict
		dtypeId = dev.deviceTypeId
		if dtypeId.find(u"OUTPUTgpio") > -1:
			valuesDict[u"typeId"] = "OUTPUTgpio"

		valuesDict[u"devId"] = devId
		#self.ML.myLog( text =	u"valuesDict "+unicode(valuesDict))
		self.setPin(valuesDict)

		return

####-------------------------------------------------------------------------####
	def setMCP4725CALLBACKaction(self, action1):
		valuesDict = action1.props
		try:
			devId = int(valuesDict[u"outputDev"])
			dev = indigo.devices[devId]
		except:
			try:
				dev = indigo.devices[valuesDict[u"outputDev"]]
			except:
				self.ML.myLog( text =  u"setMCP4725CALLBACKaction action put wrong, device name/id	not installed/ configured:" + unicode(valuesDict))
				return

		props = dev.pluginProps
		typeId							= "setMCP4725"
		valuesDict[u"typeId"]			 = typeId
		valuesDict[u"devId"]			 = dev.id
		valuesDict[u"i2cAddress"]		 = props[u"i2cAddress"]
		valuesDict[u"piServerNumber"]	 = props[u"address"].split(u"-")[1]
		valuesDict[u"cmd"]				 = "analogWrite"
		self.setPin(valuesDict)
		return

####-------------------------------------------------------------------------####
	def setPCF8591dacCALLBACKaction(self, action1):
		valuesDict = action1.props
		try:
			devId = int(valuesDict[u"outputDev"])
			dev = indigo.devices[devId]
		except:
			try:
				dev = indigo.devices[valuesDict[u"outputDev"]]
			except:
				self.ML.myLog( text =  u"setPCF8591dacCALLBACKaction action put wrong, device name/id  not installed/ configured:" + unicode(valuesDict))
				return

		props = dev.pluginProps
		typeId							= "setPCF8591dac"
		valuesDict[u"typeId"]			 = typeId
		valuesDict[u"devId"]			 = dev.id
		valuesDict[u"i2cAddress"]		 = props[u"i2cAddress"]
		valuesDict[u"piServerNumber"]	 = props[u"address"].split(u"-")[1]
		valuesDict[u"cmd"]				 = "analogWrite"
		self.setPin(valuesDict)
		return


####-------------------------------------------------------------------------####
	def startCalibrationCALLBACKAction(self, action1):
		valuesDict = action1.props
		valuesDict[u"cmd"] = "startCalibration"
		self.setPin(valuesDict)

####-------------------------------------------------------------------------####
	def setnewMessageCALLBACKAction(self, action1):
		valuesDict = action1.props
		valuesDict[u"cmd"] = "newMessage"
		self.setPin(valuesDict)
		valuesDict[u"cmd"]		 = "resetDevice"

####-------------------------------------------------------------------------####
	def setresetDeviceCALLBACKAction(self, action1):
		valuesDict = action1.props
		valuesDict[u"cmd"]		 = "resetDevice"
		self.setPin(valuesDict)

####-------------------------------------------------------------------------####
	def setMyoutputCALLBACKaction(self, action1):
		valuesDict = action1.props
		valuesDict[u"typeId"]			 = "myoutput"
		valuesDict[u"cmd"]				 = "myoutput"
		self.setPin(valuesDict)
		return

####-------------------------------------------------------------------------####
	def playSoundFileCALLBACKaction(self, action1):
		valuesDict = action1.props
		valuesDict[u"typeId"]			 = "playSound"
		valuesDict[u"cmd"]				 = "playSound"
		self.setPin(valuesDict)
		return
	###########################		ACTION	 END #################################


	###########################	   Config  #################################
####-------------------------------------------------------------------------####
	def XXgetPrefsConfigUiValues(self):
		valuesDict = self.pluginPrefs.get(u"saveValuesDict", indigo.Dict())
		valuesDict[u"piServerNumber"]  = 99
		valuesDict[u"ipNumberPi"]	   = "192.168.1.999"
		valuesDict[u"enablePiEntries"] = False
		return valuesDict

####-------------------------------------------------------------------------####
	def buttonConfirmPiServerCALLBACK(self, valuesDict=None, typeId=""):

		try:
			pi = int(valuesDict[u"piServerNumber"])
		except:
			return valuesDict
		self.selectedPiServer		  = pi
		if pi >= _GlobalConst_numberOfiBeaconRPI:
			valuesDict[u"beaconOrSensor"] = "Sensor only rPi"
		else:
			valuesDict[u"beaconOrSensor"] = "iBeacon and Sensor rPi"

		usePassword = self.RPI[unicode(pi)][u"passwordPi"]
		if	self.RPI[unicode(pi)][u"passwordPi"] == "raspberry":
			for pi0 in self.RPI:
				if self.RPI[pi0][u"passwordPi"] !="raspberry":
					usePassword = self.RPI[pi0][u"passwordPi"]
					break
		valuesDict[u"passwordPi"]		 = usePassword
					
		useID = self.RPI[unicode(pi)][u"userIdPi"]
		if	self.RPI[unicode(pi)][u"userIdPi"] == "pi":
			for pi0 in self.RPI:
				if self.RPI[pi0][u"userIdPi"] !="pi" and len(self.RPI[pi0][u"userIdPi"]) > 1:
					useID = self.RPI[pi0][u"userIdPi"]
					break
		valuesDict[u"userIdPi"]			 = useID
		
		useIP = self.RPI[unicode(pi)][u"ipNumberPi"]
		if	self.RPI[unicode(pi)][u"ipNumberPi"] == "":
			for pi0 in self.RPI:
				if self.RPI[pi0][u"ipNumberPi"] !="":
					useIP = self.RPI[pi0][u"ipNumberPi"]+"x"
					break
		valuesDict[u"ipNumberPi"]		 = useIP
			
		valuesDict[u"enablePiEntries"]	 = True
		valuesDict[u"piOnOff"]			 = self.RPI[unicode(pi)][u"piOnOff"]
		valuesDict[u"enableRebootCheck"] = self.RPI[unicode(pi)][u"enableRebootCheck"]
		valuesDict[u"MSG"]				 = "enter configuration"
		return valuesDict

####-------------------------------------------------------------------------####
	def buttonConfirmPiServerConfigCALLBACK(self, valuesDict=None, typeId="", devId=0):
		try:
			pi = int(valuesDict[u"piServerNumber"])
		#### check pi on/off
			p01 = valuesDict[u"piOnOff"]
			if p01 != self.RPI[unicode(pi)][u"piOnOff"] and self.RPI[unicode(pi)][u"piOnOff"] == "0":
				self.setONErPiV(pi,"piUpToDate", [u"updateParamsFTP"])
				self.upDateNotSuccessful[pi] = 0
			self.RPI[unicode(pi)][u"piOnOff"] = p01
			
			
			if p01 == u"0":
				self.upDateNotSuccessful[pi] == 0
				self.removeONErPiV(pi, u"piUpToDate", [u"updateParamsFTP"])

		####### check ipnumber
			ipn = valuesDict[u"ipNumberPi"]
			checkIPN = ipn.split(u".")
			if len(checkIPN) != 4:
				valuesDict[u"MSG"] = "ip number not correct"
				return valuesDict
			try:
				for iii in range(4):
					int(checkIPN[iii])
			except:
				valuesDict[u"MSG"] = "ip number not correct"
				return valuesDict

			# first test if already used somewhere else
			if self.RPI[unicode(pi)][u"piOnOff"] != u"0":
				for jj in range(_GlobalConst_numberOfRPI):
					if pi == jj: continue
					if self.RPI[unicode(jj)][u"piOnOff"] == "0": continue
					if self.RPI[unicode(jj)][u"ipNumberPi"] == ipn:
							valuesDict[u"MSG"] = "ip number already in use"
							return valuesDict

				if self.RPI[unicode(pi)][u"ipNumberPi"]	  != ipn:
					self.RPI[unicode(pi)][u"ipNumberPi"]   = ipn
					self.setONErPiV(pi,"piUpToDate", [u"updateParamsFTP"])
				self.RPI[unicode(pi)][u"ipNumberPiSendTo"] = ipn

			#### check authkey vs std password ..
				self.RPI[unicode(pi)][u"authKeyOrPassword"]		= valuesDict[u"authKeyOrPassword"]


			#### check userid password ..
				if self.RPI[unicode(pi)][u"userIdPi"]	  != valuesDict[u"userIdPi"]:
					self.RPI[unicode(pi)][u"userIdPi"]	   = valuesDict[u"userIdPi"]
					self.setONErPiV(pi,"piUpToDate", [u"updateParamsFTP"])

				if self.RPI[unicode(pi)][u"passwordPi"]	  != valuesDict[u"passwordPi"]:
					self.RPI[unicode(pi)][u"passwordPi"]   = valuesDict[u"passwordPi"]
					self.setONErPiV(pi,"piUpToDate", [u"updateParamsFTP"])

				if self.RPI[unicode(pi)][u"enableRebootCheck"] != valuesDict[u"enableRebootCheck"]:
					self.RPI[unicode(pi)][u"enableRebootCheck"] = valuesDict[u"enableRebootCheck"]
					self.setONErPiV(pi,"piUpToDate", [u"updateParamsFTP"])

			
			valuesDict[u"MSG"] = "Pi server configuration set"

			if self.RPI[unicode(pi)][u"piOnOff"] == "0":
				valuesDict[u"MSG"] = "Pi server disabled"
				try:
					dev= indigo.devices[self.RPI[unicode(pi)][u"piDevId"]]
					dev.enabled = False
					dev.replaceOnServer()
				except:
					pass
				return valuesDict


			valuesDict[u"enablePiEntries"] = False
			if self.ML.decideMyLog(u"UpdateRPI"): self.ML.myLog( text =	 u"pi=		   "+unicode(pi))
			if self.ML.decideMyLog(u"UpdateRPI"): self.ML.myLog( text =	 u"valuesDict= "+unicode(valuesDict))
			if self.ML.decideMyLog(u"UpdateRPI"): self.ML.myLog( text =	 u"RPI=		   "+unicode(self.RPI[unicode(pi)]))

			if pi >= _GlobalConst_numberOfiBeaconRPI:
						if self.RPI[unicode(pi)][u"piDevId"] == 0: # check if  existing device
							found =False
							for dev in indigo.devices.iter("props.isRPISensorDevice"):
								if dev.address.split(u"-")[1] == unicode(pi):
									props=dev.pluginProps
									if props[u"ipNumber"] != ipn:
										props[u"ipNumber"] = ipn
										dev.replacePluginPropsOnServer(props)
										self.updateNeeded += "fixConfig"
										self.setONErPiV(pi,"piUpToDate", [u"updateParamsFTP"])
										
									self.RPI[unicode(pi)][u"piDevId"] = dev.id
									found = True
									break
							if not found:
								dev= indigo.device.create(
									protocol		= indigo.kProtocol.Plugin,
									address			= "Pi-"+unicode(pi),
									name			= "Pi_Sensor_" + unicode(pi),
									description		= "rPI-" + unicode(pi)+"-"+ipn,
									pluginId		= self.pluginId,
									deviceTypeId	= "rPI-Sensor",
									folder			= self.piFolderId,
									props		= {
										   u"typeOfBeacon": u"rPi-Sensor",
										   u"sendToIndigoSecs": 90,
										   u"shutDownPinInput" : "-1",
										   u"shutDownPinOutput" : "-1",
										   u"signalDelta" : "999",
										   u"minSignalCutoff" : "-999",
										   u"expirationTime" : "90",
										   u"isRPISensorDevice" : True,
										   u"fastDown" : "0",
										   u"ipNumber":ipn}
									)
								self.addToStatesUpdateDict(unicode(dev.id),u"created",datetime.datetime.now().strftime(_defaultDateStampFormat),dev=dev)
								self.addToStatesUpdateDict(unicode(dev.id),u"note", u"Pi-" + unicode(pi)+"-"+ipn)
								self.RPI[unicode(pi)][u"piDevId"] = dev.id
								self.updateNeeded += "fixConfig"
								self.setONErPiV(pi,"piUpToDate", [u"updateParamsFTP"])
						else:
							try:
								dev= indigo.devices[self.RPI[unicode(pi)][u"piDevId"]]
							except Exception, e: 
								if unicode(e).find(u"not found in database") >-1:
									dev= indigo.device.create(
										protocol		= indigo.kProtocol.Plugin,
										address			= "Pi-"+unicode(pi),
										name			= "Pi_Sensor_" + unicode(pi),
										description		= "rPI-" + unicode(pi)+"-"+ipn,
										pluginId		= self.pluginId,
										deviceTypeId	= "rPI-Sensor",
										folder			= self.piFolderId,
										props		= {
											   u"typeOfBeacon": u"rPi-Sensor",
											   u"sendToIndigoSecs": 90,
											   u"shutDownPinInput" : "-1",
											   u"signalDelta" : "999",
											   u"expirationTime" : "90",
											   u"fastDown" : "0",
											   u"isRPISensorDevice" : True,
											   u"ipNumber":ipn}
										)
									self.addToStatesUpdateDict(unicode(dev.id),"created",datetime.datetime.now().strftime(_defaultDateStampFormat),dev=dev)
									self.addToStatesUpdateDict(unicode(dev.id),u"note", u"Pi-" + unicode(pi)+"-"+ipn)
									self.RPI[unicode(pi)][u"piDevId"] = dev.id
									self.updateNeeded += "fixConfig"
									self.setONErPiV(pi,"piUpToDate", [u"updateParamsFTP"])
								else: return valuesDict	   
						dev= indigo.devices[self.RPI[unicode(pi)][u"piDevId"]]
						props= dev.pluginProps
						self.addToStatesUpdateDict(unicode(dev.id),u"note", u"Pi-" + unicode(pi)+"-"+ipn,dev=dev)
						props[u"description"] = "rPI-"+unicode(pi)+"-"+ipn
						self.RPI[unicode(pi)][u"piMAC"] = unicode(pi)
						dev.replacePluginPropsOnServer(props)
			try:
				dev= indigo.devices[self.RPI[unicode(pi)][u"piDevId"]]
				dev.enabled = (self.RPI[unicode(pi)][u"piOnOff"] == "1")
				dev.replaceOnServer()
				try:	del self.checkIPSendSocketOk[self.RPI[unicode(pi)][u"ipNumber"]]
				except: pass
				self.executeUpdateStatesDict(onlyDevID= str(dev.id), calledFrom="buttonConfirmPiServerConfigCALLBACK end")
			except:
				pass

			self.fixConfig(checkOnly = ["all","rpi"],fromPGM="buttonConfirmPiServerConfigCALLBACK")

		except	Exception, e:
			self.ML.myLog( text =  u"buttonConfirmPiServerConfigCALLBACK in Line '%s' has error='%s'" % (sys.exc_traceback.tb_lineno, e))

		return valuesDict

####-------------------------------------------------------------------------####
	def validatePrefsConfigUi(self, valuesDict):

		try: self.enableFING				= valuesDict[u"enableFING"]
		except: self.enableFING				= "0"
			####-----------------	 ---------
			
		self.debugLevel			= []
		for d in ["Logic","DevMgmt","BeaconData","SensorData","OutputDevice","UpdateRPI","OfflineRPI","Fing","BLE","CAR","BC","all","Socket","Special","PlotPositions"]:
			if valuesDict[u"debug"+d]: self.debugLevel.append(d)

		self.setLogfile(valuesDict[u"logFileActive2"])
	 
		self.enableBroadCastEvents					= valuesDict[u"enableBroadCastEvents"]

  
		try:			   
			if self.debugRPILevel[u"debugRPICALL"]	   != int(valuesDict[u"debugRPICALL"]):	   self.setALLrPiV(u"piUpToDate", [u"updateParamsFTP"])
			self.debugRPILevel[u"debugRPICALL"]			= int(valuesDict[u"debugRPICALL"])
		except:			   pass
		try:			   
			if self.debugRPILevel[u"debugRPIBEACON"]   != int(valuesDict[u"debugRPIBEACON"]):  self.setALLrPiV(u"piUpToDate", [u"updateParamsFTP"])
			self.debugRPILevel[u"debugRPIBEACON"]		= int(valuesDict[u"debugRPIBEACON"])
		except:			   pass
		try:			   
			if self.debugRPILevel[u"debugRPISENSOR"]   != int(valuesDict[u"debugRPISENSOR"]):  self.setALLrPiV(u"piUpToDate", [u"updateParamsFTP"])
			self.debugRPILevel[u"debugRPISENSOR"]		= int(valuesDict[u"debugRPISENSOR"])
		except:			   pass
		try:			   
			if self.debugRPILevel[u"debugRPIOUTPUT"]   != int(valuesDict[u"debugRPIOUTPUT"]):  self.setALLrPiV(u"piUpToDate", [u"updateParamsFTP"])
			self.debugRPILevel[u"debugRPIOUTPUT"]		= int(valuesDict[u"debugRPIOUTPUT"])
		except:			   pass
		try:			   
			if self.debugRPILevel[u"debugRPIBLE"]	   != int(valuesDict[u"debugRPIBLE"]):	   self.setALLrPiV(u"piUpToDate", [u"updateParamsFTP"])
			self.debugRPILevel[u"debugRPIBLE"]			= int(valuesDict[u"debugRPIBLE"])
		except:			   pass
		try:			   
			if self.debugRPILevel[u"debugRPImystuff"]  != int(valuesDict[u"debugRPImystuff"]): self.setALLrPiV(u"piUpToDate", [u"updateParamsFTP"])
			self.debugRPILevel[u"debugRPImystuff"]		= int(valuesDict[u"debugRPImystuff"])
		except:			   pass
		try:		
			if unicode(self.acceptNewiBeacons) != unicode(valuesDict[u"acceptNewiBeacons"]): self.setALLrPiV(u"piUpToDate", [u"updateParamsFTP"])
			self.acceptNewiBeacons				= int(valuesDict[u"acceptNewiBeacons"])
		except:			   pass

		if unicode(self.acceptJunkBeacons) != unicode(valuesDict[u"acceptJunkBeacons"]): self.setALLrPiV(u"piUpToDate", [u"updateParamsFTP"])
		self.acceptJunkBeacons				= valuesDict[u"acceptJunkBeacons"]

		if self.sendFullUUID			   != valuesDict[u"sendFullUUID"]: self.setALLrPiV(u"piUpToDate", [u"updateParamsFTP"])
		self.sendFullUUID					= valuesDict[u"sendFullUUID"]

		try: self.txPowerCutoffDefault		= int(valuesDict[u"txPowerCutoffDefault"])
		except: self.txPowerCutoffDefault	= 1.

		try: self.speedUnits				= int(valuesDict[u"speedUnits"])
		except: self.speedUnits				= 1.
		try: self.distanceUnits				= int(valuesDict[u"distanceUnits"])
		except: self.distanceUnits			= 1.
		try: self.lightningTimeWindow		= float(valuesDict[u"lightningTimeWindow"])
		except: self.lightningTimeWindow	= 10.
		try: self.lightningNumerOfSensors		= int(valuesDict[u"lightningNumerOfSensors"])
		except: self.lightningNumerOfSensors	= 1



		self.pressureUnits					= valuesDict[u"pressureUnits"]	# 1 for Pascal
		self.tempUnits						= valuesDict[u"tempUnits"]	# Celsius, Fahrenheit, Kelvin
		self.tempDigits						= int(valuesDict[u"tempDigits"])  # 0/1/2
		
		newRain								= valuesDict[u"rainUnits"]	# mm inches
		self.rainDigits						= int(valuesDict[u"rainDigits"])  # 0/1/2
		if newRain != self.rainUnits:
			mult = 1.
			if	 newRain =="inch" and self.rainUnits == "mm":	mult = 1./25.4
			elif newRain =="inch" and self.rainUnits == "cm":	mult = 1./2.54
			elif newRain =="mm"	  and self.rainUnits == "cm":	mult = 10.
			elif newRain =="mm"	  and self.rainUnits == "inch": mult = 25.4
			elif newRain =="cm"	  and self.rainUnits == "inch": mult = 2.54
			elif newRain =="cm"	  and self.rainUnits == "mm":	mult = 0.1
			for dev in indigo.devices.iter("props.isSensorDevice"):
				if dev.deviceTypeId.find(u"rainSensorRG11") != -1: 
					props = dev.pluginProps
					for state in dev.states:
						if state.find("Rain") >-1 or state.find("rainRate") >-1:
							try: x = float(dev.states[state])
							except: continue
							self.addToStatesUpdateDict(unicode(dev.id),state, x*mult, decimalPlaces=self.rainDigits ,dev=dev)
					self.executeUpdateStatesDict(onlyDevID=str(dev.id),calledFrom="validatePrefsConfigUi")
					   
					for prop in ["hourRainTotal","lasthourRainTotal","dayRainTotal" ,"lastdayRainTotal","weekRainTotal","lastWeekRainTotal","monthRainTotal" ,"lastmonthRainTotal","yearRainTotal"]:
							try:	props[prop] = float(props[prop]) * mult
							except: pass
					dev.replacePluginPropsOnServer(props)

		self.rainUnits =   newRain					
		self.rebootHour						= int(valuesDict[u"rebootHour"])
		self.removeJunkBeacons				= valuesDict[u"removeJunkBeacons"]==u"1"
		xxx									= valuesDict[u"restartBLEifNoConnect"] == "1"
		if xxx != self.restartBLEifNoConnect:
			self.setALLrPiV(u"piUpToDate", [u"updateParamsFTP"])
		self.restartBLEifNoConnect			= xxx
		
		try: self.enableRebootRPIifNoMessages	 = int(valuesDict[u"enableRebootRPIifNoMessages"])
		except: self.enableRebootRPIifNoMessages = 999999999
		try:
			self.automaticRPIReplacement	= str(valuesDict[u"automaticRPIReplacement"]).lower() == u"true" 
		except:
			self.automaticRPIReplacement	= False 
		try:
			self.expTimeMultiplier	= float(valuesDict[u"expTimeMultiplier"])
		except:
			self.expTimeMultiplier	= 2. 

		try:	self.maxSocksErrorTime		= float(valuesDict[u"maxSocksErrorTime"])
		except: self.maxSocksErrorTime		= 600.



		try:
			self.piUpdateWindow = float(valuesDict[u"piUpdateWindow"])
		except:
			valuesDict[u"piUpdateWindow"] = 0
			self.piUpdateWindow = 0.


		try:	self.beaconPositionsUpdateTime = float(valuesDict[u"beaconPositionsUpdateTime"])
		except: pass
		try:	self.beaconPositionsdeltaDistanceMinForImage = float(valuesDict[u"beaconPositionsdeltaDistanceMinForImage"])
		except: pass
		self.beaconPositionsData[u"Xscale"]				= (valuesDict[u"beaconPositionsimageXscale"])
		self.beaconPositionsData[u"Yscale"]				= (valuesDict[u"beaconPositionsimageYscale"])
		self.beaconPositionsData[u"Zlevels"]			= (valuesDict[u"beaconPositionsimageZlevels"])
		self.beaconPositionsData[u"dotsY"]				= (valuesDict[u"beaconPositionsimageDotsY"])
		self.beaconPositionsData[u"Outfile"]			= (valuesDict[u"beaconPositionsimageOutfile"])
		self.beaconPositionsData[u"ShowRPIs"]			= (valuesDict[u"beaconPositionsimageShowRPIs"])
		self.beaconPositionsData[u"ShowExpiredBeacons"] = (valuesDict[u"beaconShowExpiredBeacons"])
		self.beaconPositionsData[u"ShowCaption"]		= (valuesDict[u"beaconPositionsimageShowCaption"])
		self.beaconPositionsData[u"Text"]				= (valuesDict[u"beaconPositionsimageText"])
		self.beaconPositionsData[u"TextColor"]			= (valuesDict[u"beaconPositionsimageTextColor"])
		self.beaconPositionsData[u"TextPos"]			= (valuesDict[u"beaconPositionsimageTextPos"])
		self.beaconPositionsData[u"TextSize"]			= (valuesDict[u"beaconPositionsimageTextSize"])
		self.beaconPositionsData[u"TextRotation"]		= (valuesDict[u"beaconPositionsimageTextRotation"])
		self.beaconPositionsData[u"compress"]			= (valuesDict[u"beaconPositionsimageCompress"])
		self.beaconPositionsUpdated						= 2



		xxx = valuesDict[u"rebootWatchDogTime"]
		if xxx != self.rebootWatchDogTime:
			self.setALLrPiV(u"piUpToDate", [u"updateParamsFTP"])
		self.rebootWatchDogTime = xxx

		self.expectTimeout = valuesDict[u"expectTimeout"]

		try:
			delH = int(valuesDict[u"deleteHistoryAfterSeconds"])
		except:
			delH = 86400
		if delH != self.deleteHistoryAfterSeconds:
			self.setALLrPiV(u"piUpToDate", [u"updateParamsFTP"])
		self.deleteHistoryAfterSeconds = delH

		try:
			xx = int(valuesDict[u"rPiCommandPORT"])
		except:
			xx = 9999
		if xx != self.rPiCommandPORT:
			self.setALLrPiV(u"piUpToDate", [u"updateParamsFTP"])
		self.rPiCommandPORT = xx


		try:
			xx = int(valuesDict[u"indigoInputPORT"])
		except:
			xx = 9999
		if xx != self.indigoInputPORT:
			self.quitNow = u"restart needed, commnunication was switched "
			self.ML.myLog( text =  u"switching communication, will send new config to all RPI and restart plugin")
			self.setALLrPiV(u"piUpToDate", [u"updateParamsFTP"])
		self.indigoInputPORT = xx

		try:
			xx = (valuesDict[u"IndigoOrSocket"])
		except:
			xx = 9999
		if xx != self.IndigoOrSocket:
			self.quitNow = u"restart, commnunication was switched "
			self.ML.myLog( text =  u"switching communication, will send new config to all RPI and restart plugin")
			self.setALLrPiV(u"piUpToDate", [u"updateParamsFTP"])
		self.IndigoOrSocket = xx

		try:
			xx = valuesDict[u"iBeaconFolderName"]
		except:
			xx = u"PI_Beacons_new"
		if xx != self.iBeaconFolderName:
			self.iBeaconFolderName = xx
			self.getFolderIdOfBeacons()
		try:
			xx = valuesDict[u"iBeaconFolderNameVariables"]
		except:
			xx = u"piBeacons"
		if xx != self.iBeaconFolderNameVariables:
			self.iBeaconFolderNameVariables = xx
			self.getFolderIdOfBeacons()

		upNames = False
		if self.groupCountNameDefault != valuesDict[u"groupCountNameDefault"]:	   upNames = True
		if self.ibeaconNameDefault	  != valuesDict[u"ibeaconNameDefault"]:		   upNames = True
		self.groupCountNameDefault = valuesDict[u"groupCountNameDefault"]
		self.ibeaconNameDefault	   = valuesDict[u"ibeaconNameDefault"]
		if upNames:
			self.deleteAndCeateVariables(False)




		self.myIpNumber = valuesDict[u"myIpNumber"]
		try:
			self.secToDown = float(valuesDict[u"secToDown"])
		except:
			self.secToDown = 90.

		pp = valuesDict[u"myIpNumber"]
		if pp != self.myIpNumber:
			self.setALLrPiV(u"piUpToDate", [u"updateParamsFTP"])
		self.myIpNumber = pp

		pp = valuesDict[u"portOfServer"]
		if pp != self.portOfServer:
			self.setALLrPiV(u"piUpToDate", [u"updateParamsFTP"])
		self.portOfServer = pp

		pp = valuesDict[u"userIdOfServer"]
		if pp != self.userIdOfServer:
			self.setALLrPiV(u"piUpToDate", [u"updateParamsFTP"])
		self.userIdOfServer = pp

		pp = valuesDict[u"passwordOfServer"]
		if pp != self.passwordOfServer:
			self.setALLrPiV(u"piUpToDate", [u"updateParamsFTP"])
		self.passwordOfServer = pp

		pp = valuesDict[u"authentication"]
		if pp != self.authentication:
			self.setALLrPiV(u"piUpToDate", [u"updateParamsFTP"])
		self.authentication = pp

		pp = valuesDict[u"GPIOpwm"]
		if pp != self.GPIOpwm:
			self.setALLrPiV(u"piUpToDate", [u"updateParamsFTP"])
		self.GPIOpwm = pp


		ss = valuesDict[u"wifiSSID"]
		pp = valuesDict[u"wifiPassword"]
		kk = valuesDict[u"key_mgmt"]
		ll = valuesDict[u"routerIP"]
		mm = valuesDict[u"wifiOFF"]
		if ss != self.wifiSSID or pp != self.wifiPassword or kk != self.key_mgmt or ll != self.routerIP or mm != self.wifiOFF:
			self.wifiSSID		= ss
			self.wifiPassword	= pp
			self.key_mgmt		= kk
			self.routerIP		= ll
			self.wifiOFF		= mm
			self.setALLrPiV(u"piUpToDate", [u"updateParamsFTP"])

		pp = int(valuesDict[u"sendAfterSeconds"])
		if pp != self.sendAfterSeconds:
			self.setALLrPiV(u"piUpToDate", [u"updateParamsFTP"])
			self.sendAfterSeconds = pp


		if u"all" in self.debugLevel:
			self.printConfig()

		self.fixConfig(checkOnly = ["all","rpi","force"],fromPGM="validatePrefsConfigUi")
		self.saveValuesDict = valuesDict
		self.saveValuesDictChanged = True
		return True, valuesDict

####-------------------------------------------------------------------------####
	def confirmDevicex(self, valuesDict=None, typeId="", devId=0):

		pi = int(valuesDict[u"piServerNumber"])
		if devId == 0:
			self.selectedPiServer = pi
			valuesDict[u"enablePiEntries"]	 = True
			valuesDict[u"ipNumberPi"]		 = self.RPI[unicode(pi)][u"ipNumberPi"]
			valuesDict[u"userIdPi"]			 = self.RPI[unicode(pi)][u"userIdPi"]
			valuesDict[u"piOnOff"]			 = self.RPI[unicode(pi)][u"piOnOff"]
			valuesDict[u"MSG"]				 = u"enter configuration"
			return valuesDict
		return valuesDict

	####-----------------	 ---------
	def setLogfile(self,lgFile):
		self.logFileActive =lgFile
		if   self.logFileActive =="standard":	self.logFile = ""
		elif self.logFileActive =="indigo":		self.logFile = self.indigoPath.split("Plugins/")[0]+"Logs/"+self.pluginId+"/plugin.log"
		else:									self.logFile = self.indigoConfigDir +"plugin.log"
		self.ML.myLogSet(debugLevel = self.debugLevel ,logFileActive=self.logFileActive, logFile = self.logFile)


	###########################	   MAIN LOOP  ############################
####-------------------------------------------------------------------------####
	def initConcurrentThread(self):
		self.countP				 = 0
		self.countPTotal		 = 0
		self.updateNeeded		 = ""

		now = datetime.datetime.now()
		self.messagesQueue	  = Queue.Queue()
		self.messagesQueueBLE = Queue.Queue()
		self.queueActive	  = False
		self.queueActiveBLE	  = False
		self.quitNow		  = u""

		self.startTime		  = time.time()
		self.stackReady		  = False
		self.socketServer	  = None

		self.writeJson(dataVersion, fName=self.userIndigoPluginDir + "dataVersion")

		self.initSprinkler()
		
		if self.indigoInputPORT > 0 and self.IndigoOrSocket == u"socket":
			self.currentlyBooting				= time.time() + 40
			self.socketServer, self.stackReady	= self.startTcpipListening(self.myIpNumber, self.indigoInputPORT)
			self.currentlyBooting				= time.time() + 20
		else:
			indigo.server.log(u" ..	 subscribing to indigo variable changes" )
			indigo.variables.subscribeToChanges()
			self.currentlyBooting	= time.time() + 20
			self.stackReady			= True

		self.lastMinute			= now.minute
		self.lastHour			= now.hour
		self.lastSecCheck		= 0
		self.countLoop			= 0
		self.ML.myLog( text = u" ..	 checking sensors" )
		self.syncSensors()
		self.ML.myLog( text = u" ..	 checking devices tables" )
		for dev in indigo.devices.iter(self.pluginId):
			props = dev.pluginProps
			if (dev.deviceTypeId.lower()) == u"rpi" or dev.deviceTypeId == u"beacon":
				self.freezeAddRemove = False

				try:
					beacon = props[u"address"]
				except:
					self.ML.myLog( text =  u"device has no address:" + dev.name + u" " + unicode(dev.id) +
						unicode(props) + u" " + unicode(dev.globalProps) + u" please delete and let the plugin create the devices")
					continue

				if beacon not in self.beacons:
					self.beacons[beacon]			 = copy.deepcopy(_GlobalConst_emptyBeacon)
					self.beacons[beacon][u"indigoId"] = dev.id
					self.beacons[beacon][u"created"]  = dev.states[u"created"]

			else:
				if u"description" in props:
					if dev.description != props[u"description"] and props[u"description"] != "":
						dev.description = props[u"description"]
						props[u"description"] = u""
						dev.replaceOnServer()
						updateProps = True
	

			if dev.deviceTypeId.find(u"OUTPUTgpio") > -1:
				xxx = json.loads(props[u"deviceDefs"])
				nn = len(xxx)
				update=False
				for n in range(nn):
					if u"gpio" in xxx[n]:
						if xxx[n][u"gpio"] == "-1":
							del xxx[n]
							continue
						if	u"initialValue" not in xxx[n]:
							xxx[n][u"initialValue"] ="-"
							update=True
				if update: 
					props[u"deviceDefs"] = json.dumps(xxx)
					dev.replacePluginPropsOnServer(props)
				###indigo.server.log(dev.name+" "+unicode(props))

		self.ML.myLog( text = u" ..	 checking BLEconnect" )
		self.BLEconnectCheckPeriod(now, force=True)
		self.ML.myLog( text = u" ..	 checking beacons" )
		self.BeaconsCheckPeriod(now, force=True)

		self.rPiRestartCommand = [u"master" for ii in range(_GlobalConst_numberOfRPI)]	## which part need to restart on rpi
		self.setupFilesForPi()
		if self.version != dataVersion :
			self.currentlyBooting = time.time() + 40
			self.ML.myLog( text =  u" ..  new py programs  etc will be send	 to rPis")
			for pi in range(_GlobalConst_numberOfRPI) :
				if self.RPI[unicode(pi)][u"ipNumberPi"] != "" :
					self.setONErPiV(pi,"piUpToDate", [u"updateAllFilesFTP","restartmasterSSH"])
					self.upDateNotSuccessful[pi] = 0
					self.sendFilesToPiServerFTP(pi, fileToSend="updateAllFilesFTP.exp")
					self.sshToRPI(pi, fileToSend=u"restartmasterSSH.exp")
					self.RPI[unicode(pi)][u"piUpToDate"] =[]
					self.upDateNotSuccessful[pi] = 0
			self.ML.myLog( text =  u" ..  new versions send to rPis")


		if len(self.checkCarsNeed) > 0:
			for carId in self.checkCarsNeed:
				self.updateAllCARbeacons(carId,force=True)
		self.currentlyBooting = time.time() + 10


		self.lastUpdateSend = time.time()  # used to send updates to all rPis if not done anyway every day
		self.pluginState	= "run"

		return 





	###########################	   cProfile stuff   ############################ START
	####-----------------  ---------
	def getcProfileVariable(self):

		try:
			if self.timeTrVarName in indigo.variables:
				xx = (indigo.variables[self.timeTrVarName].value).strip().lower().split("-")
				if len(xx) ==1: 
					cmd = xx[0]
					pri = ""
				elif len(xx) == 2:
					cmd = xx[0]
					pri = xx[1]
				else:
					cmd = "off"
					pri  = ""
				self.timeTrackWaitTime = 20
				return cmd, pri
		except	Exception, e:
			pass

		self.timeTrackWaitTime = 60
		return "off",""

	####-----------------            ---------
	def printcProfileStats(self,pri=""):
		try:
			if pri !="": pick = pri
			else:		 pick = 'cumtime'
			outFile		= self.userIndigoPluginDir+"timeStats"
			indigo.server.log(" print time track stats to: "+outFile+".dump / txt  with option: "+pick)
			self.pr.dump_stats(outFile+".dump")
			sys.stdout 	= open(outFile+".txt", "w")
			stats 		= pstats.Stats(outFile+".dump")
			stats.strip_dirs()
			stats.sort_stats(pick)
			stats.print_stats()
			sys.stdout = sys.__stdout__
		except: pass
		"""
		'calls'			call count
		'cumtime'		cumulative time
		'file'			file name
		'filename'		file name
		'module'		file name
		'pcalls'		primitive call count
		'line'			line number
		'name'			function name
		'nfl'			name/file/line
		'stdname'		standard name
		'time'			internal time
		"""

	####-----------------            ---------
	def checkcProfile(self):
		try: 
			if time.time() - self.lastTimegetcProfileVariable < self.timeTrackWaitTime: 
				return 
		except: 
			self.cProfileVariableLoaded = 0
			self.do_cProfile  			= "x"
			self.timeTrVarName 			= "enableTimeTracking_"+self.pluginName
			indigo.server.log("testing if variable "+self.timeTrVarName+" is == on/off/print-option to enable/end/print time tracking of all functions and methods (option:'',calls,cumtime,pcalls,time)")

		self.lastTimegetcProfileVariable = time.time()

		cmd, pri = self.getcProfileVariable()
		if self.do_cProfile != cmd:
			if cmd == "on": 
				if  self.cProfileVariableLoaded ==0:
					indigo.server.log("======>>>>   loading cProfile & pstats libs for time tracking;  starting w cProfile ")
					self.pr = cProfile.Profile()
					self.pr.enable()
					self.cProfileVariableLoaded = 2
				elif  self.cProfileVariableLoaded >1:
					self.quitNow = " restart due to change  ON  requested for print cProfile timers"
			elif cmd == "off" and self.cProfileVariableLoaded >0:
					self.pr.disable()
					self.quitNow = " restart due to  OFF  request for print cProfile timers "
		if cmd == "print"  and self.cProfileVariableLoaded >0:
				self.pr.disable()
				self.printcProfileStats(pri=pri)
				self.pr.enable()
				indigo.variable.updateValue(self.timeTrVarName,"done")

		self.do_cProfile = cmd
		return 

	####-----------------            ---------
	def checkcProfileEND(self):
		if self.do_cProfile in["on","print"] and self.cProfileVariableLoaded >0:
			self.printcProfileStats(pri="")
		return
	###########################	   cProfile stuff   ############################ END



####-----------------   main loop          ---------
	def runConcurrentThread(self):

		self.dorunConcurrentThread()
		self.checkcProfileEND()

		self.sleep(1)
		if self.quitNow !="":
			indigo.server.log( u"runConcurrentThread stopping plugin due to:  ::::: " + self.quitNow + " :::::")
			serverPlugin = indigo.server.getPlugin(self.pluginId)
			serverPlugin.restart(waitUntilDone=False)


		indigo.server.log( u"killing 2")
		os.system("/bin/kill -9 "+str(self.myPID) )

		return



####-----------------   main loop          ---------
	def dorunConcurrentThread(self): 

		self.initConcurrentThread()

		if self.logFileActive !="standard":
			indigo.server.log(u" ..	 initalized")
			self.ML.myLog( text = u" ..	 initalized, starting loop" )
		else:	 
			indigo.server.log(u" ..	 initalized, starting loop ")
		theHourToCheckversion = 12
			
		########   ------- here the loop starts	   --------------
		try:
			while self.quitNow == "":
				self.countLoop += 1
				self.sleep(9.)
				VS.versionCheck(self.pluginId,self.pluginVersion,indigo,13,25,printToLog="log")

				if self.countLoop > 2: 
					anyChange= self.periodCheck()
					self.checkGroups()
					if self.enableFING == "1":
						self.updateFING(u"loop ")
					if len(self.sendBroadCastEventsList) >0: self.sendBroadCastNOW()
					
		except self.StopThread:
			indigo.server.log( u"stop requested from indigo ")
		## stop and processing of messages received 
		indigo.server.log( "quitNow: "+self.quitNow)
		
		self.stackReady	 = False 
		self.pluginState = "stop"


		# save all parameters to file 
		self.fixConfig(checkOnly = ["all","rpi","beacon","CARS","sensors","output","force"],fromPGM="finish") # runConcurrentThread end

		if self.socketServer is not None:  
			lsofCMD	 =u"/usr/sbin/lsof -i tcp:"+unicode(self.indigoInputPORT)
			ret = subprocess.Popen(lsofCMD, shell=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE).communicate()
			if len(ret[0]) > 10: indigo.server.log(u".. stopping tcpip stack")
			self.socketServer.shutdown()
			self.socketServer.server_close()

		
		
		return


####-------------------------------------------------------------------------####
	def checkGroups(self):
		if self.statusChanged ==1:	self.setGroupStatus()
		if self.statusChanged ==2:	self.setGroupStatus(init=True)

####-------------------------------------------------------------------------####
	def updateFING(self, source):
		if self.enableFING == "0": return
		devIDs = []
		states = []
		names = []
		try:
			for beacon in self.beacons:
				if self.beacons[beacon][u"ignore"]		 != 0: continue
				if self.beacons[beacon][u"indigoId"]	 == 0: continue
				if self.beacons[beacon][u"updateFING"]	 == 0: continue
				devIDs.append(self.beacons[beacon][u"indigoId"])
				states.append(self.beacons[beacon][u"status"])
				try:
					name = indigo.devices[self.beacons[beacon][u"indigoId"]].name
				except	Exception, e:
					if unicode(e).find(u"timeout waiting") > -1:
						self.ML.myLog( text =  u"updateFING in Line '%s' has error='%s'" % (sys.exc_traceback.tb_lineno, e))
						self.ML.myLog( text =  u"communication to indigo is interrupted")
						return
					if unicode(e).find(u"not found in database") >-1:	 
						name = ""
					else:
						return
						
				names.append(name)
				self.beacons[beacon][u"updateFING"] = 0

			if devIDs != []:
				for i in range(3):
					if self.ML.decideMyLog(u"Fing"): self.ML.myLog( text =	u"updating fingscan ; source:" + source + "	 try# " + unicode(i + 1) + u";	 with " + unicode(names) + " " + unicode(devIDs) + " " + unicode(states))
					plug = indigo.server.getPlugin(u"com.karlwachs.fingscan")
					if plug.isEnabled():
						plug.executeAction(u"piBeaconUpdate", props={u"deviceId": devIDs})
						self.fingscanTryAgain = False
						break
					else:
						if i == 2:
							self.ML.myLog( text =  u"fingscan plugin not reachable")
							self.fingscanTryAgain = True
						self.sleep(1)
		except	Exception, e:
			if len(unicode(e)) > 5 :
				self.ML.myLog( text =  u"updateFING in Line '%s' has error='%s'" % (sys.exc_traceback.tb_lineno, e))

		return
	####----------------- if FINGSCAN is enabled send update signal	 ---------
	def sendBroadCastNOW(self):
		try:
			x = ""
			if	self.enableBroadCastEvents =="0":
				self.sendBroadCastEventsList = []
				return x
			if self.sendBroadCastEventsList == []:	
				return x
			if self.countLoop < 10:
				self.sendBroadCastEventsList = [] 
				return x  ## only after stable ops for 10 loops ~ 20 secs
				
			msg = copy.copy(self.sendBroadCastEventsList)
			self.sendBroadCastEventsList = []
			if len(msg) >0:
				msg ={"pluginId":self.pluginId,"data":msg}
				try:
					if self.ML.decideMyLog(u"BC"): self.ML.myLog( text=u"updating BC with " + unicode(msg),mType=u"BroadCast" )
					indigo.server.broadcastToSubscribers(u"deviceStatusChanged", json.dumps(msg))
				except	Exception, e:
					if len(unicode(e)) > 5:
						indigo.server.log( u"updating sendBroadCastNOW has error in Line '%s' has error='%s'" % (sys.exc_traceback.tb_lineno, e)+u" finscan update failed")

		except	Exception, e:
			if len(unicode(e)) > 5:
				indigo.server.log( u"updating sendBroadCastNOW has error in Line '%s' has error='%s'" % (sys.exc_traceback.tb_lineno, e))
			else:
				x = "break"
		return x


####-------------------------------------------------------------------------####
	def printpiUpToDate(self):
		try:
			list= ""
			for pi in range(_GlobalConst_numberOfRPI):
				ok = True
				for action	in self.RPI[unicode(pi)][u"piUpToDate"]:
					if action not in _GlobalConst_allowedpiSends:
						ok = False
						break
				list+=unicode(pi)+":"+unicode(self.RPI[unicode(pi)][u"piUpToDate"])+"; "
				if not ok: self.RPI[unicode(pi)][u"piUpToDate"]=[]
			if self.ML.decideMyLog(u"OfflineRPI"): self.ML.myLog( text = u"printpiUpToDate list .. pi#:[actionLeft];.. ([]=ok): "+ list	 ) 
		except	Exception, e:
			if len(unicode(e)) > 5 :
				self.ML.myLog( text =  u"printpiUpToDate in Line '%s' has error='%s'" % (sys.exc_traceback.tb_lineno, e))
		return
			
####-------------------------------------------------------------------------####
	def findAnyTaskPi(self, item):
		for pi in range(_GlobalConst_numberOfRPI):
		   if self.RPI[unicode(pi)][item] !=[]: return True
		return False

####-------------------------------------------------------------------------####
	def findTaskPi(self, item,findTask):
		for pi in range(_GlobalConst_numberOfRPI):
		   if findTask in self.RPI[unicode(pi)][item]:	return True
		return False

####-------------------------------------------------------------------------####
	def periodCheck(self):
		anyChange= False
		try:
			tt = time.time()
			if time.time()- self.lastSecCheck < 9. or time.time()- self.startTime < 30: return anyChange
		

			self.checkcProfile()

			now = datetime.datetime.now()
			self.freezeAddRemove =False
			
			self.replaceAddress()

			self.checkForUpdates(now )
			if self.sendInitialValue !="": self.sendInitialValuesToOutput()
			self.checkMinute(now )

			self.sprinklerStats()


			if self.queueList !="":
				for ii in range(40):
					if ii > 0 and self.ML.decideMyLog(u"BeaconData"): self.ML.myLog( text =	 u"wait for queue to become available in main loop,	 ii="+unicode(ii)+u"  "+self.queueList)
					if self.queueList ==u"": break
					self.sleep(0.05)

			
			self.queueList = u"periodCheck"		 # block incoming messages from processing
			self.BLEconnectCheckPeriod(now)
			anyChange = self.BeaconsCheckPeriod(now)
		
			if len(self.checkCarsNeed) > 0:
				delID ={}
				for carId in self.checkCarsNeed:
					if self.checkCarsNeed[carId] >0 and time.time()> self.checkCarsNeed[carId]:
						self.updateAllCARbeacons(carId)
						if self.checkCarsNeed[carId] ==0:
							delID[carId]=1
				for carId in delID:
					del self.checkCarsNeed[carId]
			self.queueList = ""					# unblock incoming meaasages from processing

			self.performActionList()
		
			if self.lastMinute != now.minute: 
				anyChange=True


			self.checkHour(now)

			self.execdevUpdateList()

			if	(  self.beaconPositionsUpdated !=0 or 
				  (self.beaconPositionsUpdateTime > 0 and (time.time()- self.beaconPositionsLastCheck)	> self.beaconPositionsUpdateTime )	 ):
					self.makeNewBeaconPositionPlots()

			self.lastSecCheck		= time.time()
			self.lastMinute			= now.minute
			self.lastHour			= now.hour

			self.freezeAddRemove	= False
			self.initStatesOnServer = False
		except	Exception, e:
			if len(unicode(e)) > 5 :
				self.ML.myLog( text =  u"periodCheck in Line '%s' has error='%s'" % (sys.exc_traceback.tb_lineno, e))

		return anyChange


####-------------------------------------------------------------------------####
	def performActionList(self):
		try:
			if self.actionList == []: return

			for action in self.actionList:
				if action[u"action"] == "setTime":
					self.doActionSetTime(action[u"value"])
		
		except	Exception, e:
			if len(unicode(e)) > 5 :
				self.ML.myLog( text =  u"performActionList in Line '%s' has error='%s'" % (sys.exc_traceback.tb_lineno, e))
		self.actionList =[]
		return


####-------------------------------------------------------------------------####
	def replaceAddress(self):
		try:
			if self.newADDRESS !={}:
				for devId in self.newADDRESS:
					try:
						dev = indigo.devices[devId]
						if len(self.newADDRESS[devId]) == len(u"01:02:03:04:05:06"):
							self.ML.myLog( text =  u"updating "+dev.name+"	address with: "+self.newADDRESS[devId])
							props = dev.pluginProps
							props[u"address"]= self.newADDRESS[devId]
							dev.replacePluginPropsOnServer(props)
							dev = indigo.devices[devId]
							props = dev.pluginProps
					except Exception, e:
						if len(unicode(e)) > 5 :
							self.ML.myLog( text =  u"replaceAddress in Line '%s' has error='%s'" % (sys.exc_traceback.tb_lineno, e))
							self.ML.myLog( text =  u"ok if replacing RPI")
				self.newADDRESS={}

		except	Exception, e:
			if len(unicode(e)) > 5 :
				self.ML.myLog( text =  u"replaceAddress in Line '%s' has error='%s'" % (sys.exc_traceback.tb_lineno, e))



####-------------------------------------------------------------------------####
	def sendInitialValuesToOutput(self):
		try:
			dev= indigo.devices[self.sendInitialValue]
			props= dev.pluginProps
			xxx = json.loads(props[u"deviceDefs"])
			nn = len(xxx)
			piServerNumber = props[u"piServerNumber"]
			ip = self.RPI[unicode(props[u"piServerNumber"])][u"ipNumberPi"]
			for n in range(nn):
				cmd = ""
				cmd = xxx[n][u"initialValue"]
				if cmd ==u"up" or  cmd ==u"down": 
					if self.ML.decideMyLog(u"OutputDevice"): self.ML.myLog( text = "init pin: sending to pi# "+piServerNumber+ "pin3 "+props[u"gpio"]+"	 "+cmd)
					self.sendGPIOCommand(ip, int(piServerNumber), dev.deviceTypeId, cmd, GPIOpin= xxx[n][u"gpio"], restoreAfterBoot="1", inverseGPIO=False)

		except	Exception, e:
			if len(unicode(e)) > 5 :
				self.ML.myLog( text =  u"sendInitialValuesToOutput in Line '%s' has error='%s'" % (sys.exc_traceback.tb_lineno, e))
		self.sendInitialValue ==u""


####-------------------------------------------------------------------------####
	def checkForUpdates(self,now):
		anyChange= False
		try:
			if self.saveValuesDictChanged:
				self.saveValuesDictChanged = False
				self.pluginPrefs[u"saveValuesDict"] = self.saveValuesDict

			if time.time()- self.lastUpdateSend > 3600:	 ## send config every hour, no other action
				self.rPiRestartCommand = [u"" for ii in range(_GlobalConst_numberOfRPI)]  # soft update, no restart required
				self.setALLrPiV(u"piUpToDate", [u"updateParamsFTP"])

			if self.updateNeeded.find(u"enable") > -1 or self.updateNeeded.find(u"disable") > -1: 
				self.syncSensors()
				self.setupFilesForPi()
				try:
					pi = self.updateNeeded.split(u"-")[1]
					self.setONErPiV(pi,"piUpToDate", [u"updateParamsFTP"])
					if self.ML.decideMyLog(u"BeaconData"): self.ML.myLog( text =  u"sending update to pi#"+ unicode(pi))
				except: pass	

				self.updateNeeded ="" 
	 
			if self.updateNeeded.find(u"fixConfig") > -1 or self.findAnyTaskPi(u"piUpToDate"):
				self.fixConfig(checkOnly = ["all","rpi","force"],fromPGM="checkForUpdates") # checkForUpdates  # ok only if changes requested
				self.setupFilesForPi()
				self.updateNeeded = ""


			if not self.findAnyTaskPi(u"piUpToDate"):
			   self.updateRejectListsCount =0
			else:
					self.newIgnoreMAC = 0
					for pi in range(_GlobalConst_numberOfRPI):
						if self.upDateNotSuccessful[pi] > 9:  # count down to 0 then try it again
							if self.ML.decideMyLog(u"OfflineRPI"): self.ML.myLog( text =  u"rPi update delayed due to failed updates rPI# "+ unicode(pi))
							self.upDateNotSuccessful[pi] -= 10
							continue

						if self.RPI[unicode(pi)][u"piOnOff"] == "0" or self.RPI[unicode(pi)][u"ipNumberPi"] == "":
							self.RPI[unicode(pi)][u"piUpToDate"] = []
							continue

						if self.RPI[unicode(pi)][u"piUpToDate"] == []:
							continue
	 
						self.checkSSHsend()


						if u"initSSH" in self.RPI[unicode(pi)][u"piUpToDate"]:
							self.sshToRPI(pi, fileToSend="initSSH.exp")

						if u"upgradeOpSysSSH" in self.RPI[unicode(pi)][u"piUpToDate"]:
							self.sshToRPI(pi, fileToSend="upgradeOpSysSSH.exp")
							self.RPI[unicode(pi)][u"piUpToDate"] = []

						if u"updateAllFilesFTP" in self.RPI[unicode(pi)][u"piUpToDate"]:
							self.sendFilesToPiServerFTP(pi, fileToSend="updateAllFilesFTP.exp")

						if u"updateParamsFTP" in self.RPI[unicode(pi)][u"piUpToDate"]:
							self.sendFilesToPiServerFTP(pi, fileToSend="updateParamsFTP.exp")

						if self.updateRejectListsCount < _GlobalConst_numberOfRPI:
							self.updateRejectListsCount +=1
							self.updateRejectLists()
						else:
							self.printpiUpToDate()

					if self.findTaskPi(u"piUpToDate","getStatsSSH"):
						for pi in range(_GlobalConst_numberOfRPI) :
							if u"getStatsSSH" in self.RPI[unicode(pi)][u"piUpToDate"]:
								self.sshToRPI(pi,fileToSend="getStatsSSH.exp")



					if self.findTaskPi(u"piUpToDate","shutdown"):
						for pi in range(_GlobalConst_numberOfRPI) :
							if u"shutdownSSH" in self.RPI[unicode(pi)][u"piUpToDate"]:
								self.sshToRPI(pi,fileToSend="shutdownSSH.exp")

					if self.findTaskPi(u"piUpToDate","rebootSSH"):
						for pi in range(_GlobalConst_numberOfRPI) :
							if u"rebootSSH" in self.RPI[unicode(pi)][u"piUpToDate"]	 and not  "updateParamsFTP" in self.RPI[unicode(pi)][u"piUpToDate"]:
								reboot=""
								try: 
									props0 = indigo.devices[self.RPI[unicode(pi)][u"piDevId"]].pluginProps
									if u"rebootCommand" in props0 and  props0[u"rebootCommand"].find(u"sudo reboot -f") >-1:
										reboot = props0[u"rebootCommand"]
								except: pass
								if reboot !="":
									self.sshToRPI(pi,fileToSend="rebootFSSH.exp")
								else:
									self.sshToRPI(pi,fileToSend="rebootSSH.exp")

					if self.findTaskPi(u"piUpToDate","resetOutputSSH"):
						for pi in range(_GlobalConst_numberOfRPI) :
							if u"resetOutputSSH" in self.RPI[unicode(pi)][u"piUpToDate"]  and not  "updateParamsFTP" in self.RPI[unicode(pi)][u"piUpToDate"]:
								self.sshToRPI(pi,fileToSend="resetOutputSSH.exp")

		except	Exception, e:
			if len(unicode(e)) > 5 :
				self.ML.myLog( text =  u"checkForUpdates in Line '%s' has error='%s'" % (sys.exc_traceback.tb_lineno, e))
		return anyChange

####-------------------------------------------------------------------------####
	def checkSSHsend(self):
		return 


####-------------------------------------------------------------------------####
	def checkMinute(self, now):
		if now.minute == self.lastMinute: return

		try:
			self.fixConfig(checkOnly = ["all"], fromPGM="checkMinute") # checkMinute
			self.checkRPIStatus()
			self.checkSensorStatus()
			self.saveTcpipSocketStats()

			self.freezeAddRemove = False

			if now.minute % 5 == 0:
				if self.newIgnoreMAC > 0:
					for pi in range(_GlobalConst_numberOfRPI) :
						self.setONErPiV(pi,"piUpToDate", [u"updateParamsFTP"])
					self.newIgnoreMAC = 0

				for pi in range(_GlobalConst_numberOfRPI):
					if self.RPI[unicode(pi)][u"piOnOff"] == "0":			 continue
					if self.RPI[unicode(pi)][u"piDevId"] ==	 0:				 continue
					if time.time() - self.RPI[unicode(pi)][u"lastMessage"] < 330.:	continue
					if self.ML.decideMyLog(u"Logic"): self.ML.myLog( text =	 u"pi server # " + unicode(pi) + "	ip# " + self.RPI[unicode(pi)][u"ipNumberPi"] + "  has not send a message in the last " + unicode(int(time.time() - self.RPI[unicode(pi)][u"lastMessage"] )) + " seconds")

		except Exception, e:
			if len(unicode(e)) > 5 :
				self.ML.myLog( text =  u"checkMinute in Line '%s' has error='%s'" % (sys.exc_traceback.tb_lineno, e))
		return

####-------------------------------------------------------------------------####
	def BLEconnectCheckPeriod(self, now, force = False):
		try:
			if time.time()< self.currentlyBooting:
				return
			for dev in indigo.devices.iter("props.isBLEconnectDevice"):
				if self.queueListBLE == "update": self.sleep(0.1)

				props = dev.pluginProps
				try:
					expirationTime = float(props[u"expirationTime"]) + 0.2
				except:
					continue
				status = "expired"
				lastUp = dev.states[u"lastUp"]
				if len(lastUp) < 10: continue
				lastUp1 = datetime.datetime.strptime(lastUp, _defaultDateStampFormat)
				dt = time.time()- time.mktime(lastUp1.timetuple())
				#self.ML.myLog( text =	dev.name +" dt "+ unicode(dt))
				#self.ML.myLog( text =	dev.name+" pi " + unicode(pi1) +"	expirationTime "+unicode(expirationTime)+"	dt "+unicode(dt))
				if dt <= 1 * expirationTime:
					status = "up"
				elif dt <= self.expTimeMultiplier * expirationTime:
					status = "down"

				if dev.states[u"status"] != status or self.initStatesOnServer or force:
					if self.ML.decideMyLog(u"BLE"): self.ML.myLog( text =  u"BLEconnectCheckPeriod :"+dev.name+"   status in checkBLEdev new status:"+ status+"	 dt="+ unicode(dt) +"; lastUp="+unicode(lastUp)+"; expirationTime="+unicode(expirationTime))
					if status == "up":
						dev.updateStateImageOnServer(indigo.kStateImageSel.SensorOn)
					elif status == "down":
						dev.updateStateImageOnServer(indigo.kStateImageSel.SensorOff)
					else:
						dev.updateStateImageOnServer(indigo.kStateImageSel.SensorTripped)
					
					self.addToStatesUpdateDict(unicode(dev.id),u"status", status,dev=dev)
					self.executeUpdateStatesDict(onlyDevID=str(dev.id),calledFrom="BLEconnectCheckPeriod end")	  


		except Exception, e:
			if len(unicode(e)) > 5 :
				self.ML.myLog( text =  u"BLEconnectCheckPeriod in Line '%s' has error='%s'" % (sys.exc_traceback.tb_lineno, e))
		return

####-------------------------------------------------------------------------####
	def checkSensorStatus(self):

		try:
			for dev in indigo.devices.iter("props.isSensorDevice"):
				if dev.deviceTypeId not in _GlobalConst_allowedSensors: continue
				dt = time.time()- self.checkSensorMessages(dev.id,"lastMessage", default=time.time())

				#self.ML.myLog( text = " checking "+ dev.name+"	 "+ unicode(dt)+" delta secs")
				if time.time()< self.currentlyBooting: continue 
				if dt > 600:
					try:
						if	dev.pluginProps[u"displayS"].lower().find(u"temp")==-1:
							dev.updateStateImageOnServer(indigo.kStateImageSel.PowerOff)
						else:
							dev.updateStateImageOnServer(indigo.kStateImageSel.PowerOff)
					except:
						self.ML.myLog( text = "checkSensorStatus :" + dev.name + " property displayS missing, please edit and save ")
						dev.updateStateImageOnServer(indigo.kStateImageSel.Error)
			self.saveSensorMessages(devId="")

		except Exception, e:
			if len(unicode(e)) > 5 :
				self.ML.myLog( text =  u"checkSensorStatus in Line '%s' has error='%s'" % (sys.exc_traceback.tb_lineno, e))
				try:
					self.ML.myLog( text =  unicode(dev.pluginProps))
				except:
					pass
		return


####-------------------------------------------------------------------------####
	def checkRPIStatus(self):
		try:
			if	time.time()< self.currentlyBooting: return 
			
			for pi in range(_GlobalConst_numberOfRPI):
				if self.RPI[unicode(pi)][u"piDevId"] == 0:	 continue
				try:
					dev = indigo.devices[self.RPI[unicode(pi)][u"piDevId"]]
				except:
					continue
				if self.RPI[unicode(pi)][u"piOnOff"] == "0": 
					if time.time()- self.RPI[unicode(pi)][u"lastMessage"] > 500:
						self.addToStatesUpdateDict(unicode(dev.id),u"online", u"expired",dev=dev)
						dev.updateStateImageOnServer(indigo.kStateImageSel.PowerOff)
						if pi >= _GlobalConst_numberOfiBeaconRPI: 
							self.addToStatesUpdateDict(unicode(dev.id),u"status", u"expired",dev=dev)
					continue

				if time.time()- self.RPI[unicode(pi)][u"lastMessage"] > 240:
					self.addToStatesUpdateDict(unicode(dev.id),u"online", u"expired",dev=dev)
					if pi >= _GlobalConst_numberOfiBeaconRPI: 
						self.addToStatesUpdateDict(unicode(dev.id),u"status", u"expired",dev=dev)
						dev.updateStateImageOnServer(indigo.kStateImageSel.PowerOff)
					else:
						if dev.states[u"status"] in [u"down","expired"]:
							dev.setErrorStateOnServer('IPconnection and BLE down')
							dev.updateStateImageOnServer(indigo.kStateImageSel.SensorTripped)
						else:
							dev.setErrorStateOnServer(u"")
							dev.updateStateImageOnServer(indigo.kStateImageSel.PowerOff)

				elif time.time()- self.RPI[unicode(pi)][u"lastMessage"] >120:
					self.addToStatesUpdateDict(unicode(dev.id),u"online", u"down",dev=dev)
					if pi >= _GlobalConst_numberOfiBeaconRPI: 
						self.addToStatesUpdateDict(unicode(dev.id),u"status", u"down")
						dev.updateStateImageOnServer(indigo.kStateImageSel.PowerOff)
					else:
						if dev.states[u"status"] in [u"down","expired"]:
							dev.setErrorStateOnServer('IPconnection and BLE down')
							dev.updateStateImageOnServer(indigo.kStateImageSel.SensorTripped)
						else:
							dev.setErrorStateOnServer(u"")
							dev.updateStateImageOnServer(indigo.kStateImageSel.PowerOff)

				else:
					self.addToStatesUpdateDict(unicode(dev.id),u"online", u"up",dev=dev)
					self.addToStatesUpdateDict(unicode(dev.id),u"status", u"up")
					dev.setErrorStateOnServer(u"")
					if pi >= _GlobalConst_numberOfiBeaconRPI: 
							dev.updateStateImageOnServer(indigo.kStateImageSel.SensorOn)
					else:
						if dev.states[u"status"] in [u"down","expired"]:
							dev.updateStateImageOnServer(indigo.kStateImageSel.SensorOff)
						else:
							dev.updateStateImageOnServer(indigo.kStateImageSel.SensorOn)

		except Exception, e:
			if len(unicode(e)) > 5 :
				self.ML.myLog( text =  u"checkRPIStatus in Line '%s' has error='%s'" % (sys.exc_traceback.tb_lineno, e))


		return



####-------------------------------------------------------------------------####
	def BeaconsCheckPeriod(self,now, force = False):
		if	time.time()< self.currentlyBooting:
			if time.time()> self.lastUPtoDown:
				self.ML.myLog( text = u"BeaconsCheckPeriod waiting for reboot, no changes in up--> down status for another %4d"%( self.currentlyBooting - time.time())+"[secs]") 
				self.lastUPtoDown  = time.time()+90
			return False # noting for the next x minutes due to reboot 
		anyChange = False
		try:
			for beacon in self.beacons :
				dev =""
				if self.selectBeaconsLogTimer !={}: 
					for sMAC in self.selectBeaconsLogTimer:
						if beacon.find(sMAC[:self.selectBeaconsLogTimer[sMAC]]) ==0:
							self.ML.myLog( text = u"sel.beacon logging: BeaconsCheckPeriod :"+beacon+"; "+(" ").ljust(30)  )
				changed = False
				if u"status" not in self.beacons[beacon] : continue
				## pause is set at device stop, check if still paused skip
							
							
				if self.selectBeaconsLogTimer !={}: 
					for sMAC in self.selectBeaconsLogTimer:
						if beacon.find(sMAC[:self.selectBeaconsLogTimer[sMAC]]) ==0:
							self.ML.myLog( text = u"sel.beacon logging: BeaconsCheckPeriod :"+beacon+"; "+(" ").ljust(30) +"	   passed pause" )

				if self.beacons[beacon][u"lastUp"] > 0:
					if self.beacons[beacon][u"ignore"] == 1 :
						if time.time()- self.beacons[beacon][u"lastUp"] > 3 * 86000 :  ## 3 days
							self.beacons[beacon][u"ignore"] = 2
					# if self.beacons[beacon][u"status"] ==u"expired": continue
					if self.beacons[beacon][u"ignore"] > 0 : continue
				if self.selectBeaconsLogTimer !={}: 
					for sMAC in self.selectBeaconsLogTimer:
						if beacon.find(sMAC[:self.selectBeaconsLogTimer[sMAC]]) ==0:
							self.ML.myLog( text = u"sel.beacon logging: BeaconsCheckPeriod :"+beacon+"; "+(" ").ljust(30) +"	   passed ignore" )

				expT = float(self.beacons[beacon][u"expirationTime"])
				if self.beacons[beacon][u"lastUp"] < 0:	 # fast down was last event, block for 5 secs after that
					if time.time() + self.beacons[beacon][u"lastUp"] > 5:
						self.beacons[beacon][u"lastUp"] = time.time()- expT-0.1
					else:
						if self.selectBeaconsLogTimer !={}: 
							for sMAC in self.selectBeaconsLogTimer:
								if beacon.find(sMAC[:self.selectBeaconsLogTimer[sMAC]]) ==0:
									self.ML.myLog( text = u"sel.beacon logging: BeaconsCheckPeriod :"+beacon+"; "+(" ").ljust(30) +"	   no change in up status, dt:"+unicode(time.time() + self.beacons[beacon][u"lastUp"]) )
						continue

				delta = time.time()- self.beacons[beacon][u"lastUp"]  ##  no !! - self.beacons[beacon][u"updateSignalValuesSeconds"]
				if self.beacons[beacon][u"status"] == u"up" :
					if delta > expT :
						self.beacons[beacon][u"status"] = u"down"
						self.beacons[beacon][u"updateFING"] = 1
						#self.ML.myLog( text =	u" up to down secs: delta= " + unicode(delta) + " expT: " + unicode(expT) + "  " + beacon)
						changed = True
					if delta > self.expTimeMultiplier * expT:
						self.beacons[beacon][u"status"] = u"expired"
						changed = True 
				elif self.beacons[beacon][u"status"] == u"down" :
					if delta > self.expTimeMultiplier * expT:
						self.beacons[beacon][u"status"] = u"expired"
						changed = True
					if delta < expT and self.beacons[beacon][u"fastDown"] != "0":
						self.beacons[beacon][u"status"] = "up"
						#self.ML.myLog( text =	u" down to up secs: delta= " + unicode(delta) + " expT: " + unicode(expT) + "  " + beacon)
						self.beacons[beacon][u"updateFING"] = 1
						changed = True
				elif self.beacons[beacon][u"status"] == u"expired" and delta < self.expTimeMultiplier * expT and self.beacons[beacon][u"fastDown"] != u"0":
					self.beacons[beacon][u"status"] = u"up"
					changed = True
				elif self.beacons[beacon][u"status"] == u"":
					self.beacons[beacon][u"status"] = u"expired"
					changed = True
				if	self.initStatesOnServer: changed = True
				if self.selectBeaconsLogTimer !={}: 
					for sMAC in self.selectBeaconsLogTimer:
						if beacon.find(sMAC[:self.selectBeaconsLogTimer[sMAC]]) ==0:
							self.ML.myLog( text = u"sel.beacon logging: BeaconsCheckPeriod :"+beacon+"; "+(" ").ljust(30) +"	   status: "+ self.beacons[beacon][u"status"]+ ";  deltaT: "+ unicode(delta))

				#if beacon ==u"5C:F3:70:6D:DA:7A": 
				#	 self.ML.myLog( text =	u"rpi0 beacon data (2):"  +unicode(time.time()) +"	"  +unicode(self.beacons[beacon][u"lastUp"])+"	"  +unicode(delta) +"  "+unicode(changed)+"	 "+unicode(force)+"	 "+unicode(self.beacons[beacon]) )

				if changed or force:
					if self.ML.decideMyLog(u"BeaconData"): self.ML.myLog( text =  u"BeaconsCheckPeriod changed=true or force " + beacon + "	 " + self.beacons[beacon][u"status"])
						
					try :
						dev = indigo.devices[self.beacons[beacon][u"indigoId"]]
						if dev.states[u"groupMember"] !="": anyChange = True
						#if dev.name ==u"Pi-20-Karl": self.ML.myLog( text =	 u"status change in BeaconsCheckPeriod for "+ dev.name+"; beacon"+ beacon+"	 from "+dev.states[u"status"]+" to "+ self.beacons[beacon][u"status"]+";  expirationTime="+unicode(expT)+"	time.time()-lastUp="+unicode(delta) )
						self.addToStatesUpdateDict(unicode(dev.id),u"status", self.beacons[beacon][u"status"],dev=dev)

						if self.beacons[beacon][u"status"] == u"up":
							if u"closestRPI"	 in dev.states: 
								closest =  self.findClosestRPI(beacon,dev)
								if closest != dev.states[u"closestRPI"]:
									self.addToStatesUpdateDict(unicode(dev.id),u"closestRPI", closest)
									self.addToStatesUpdateDict(unicode(dev.id),u"closestRPIText", u"Pi_"+str(closest))
							if self.beacons[beacon][u"note"].find(u"beacon")>-1: 
								dev.updateStateImageOnServer(indigo.kStateImageSel.SensorOn) # not for RPI's

						elif self.beacons[beacon][u"status"] == u"down":
							if self.beacons[beacon][u"note"].find(u"beacon")>-1:
								if u"closestRPI" in dev.states:
									self.addToStatesUpdateDict(unicode(dev.id),u"closestRPI", -1)
									self.addToStatesUpdateDict(unicode(dev.id),u"closestRPIText", u"Pi_-1")
								dev.updateStateImageOnServer(indigo.kStateImageSel.SensorOff)
							#else: this is handled in RPI update
							#	 dev.updateStateImageOnServer(indigo.kStateImageSel.Error)

						else:
							if self.beacons[beacon][u"note"].find(u"beacon") > -1:
								dev.updateStateImageOnServer(indigo.kStateImageSel.SensorTripped)
								if u"closestRPI" in dev.states:
									self.addToStatesUpdateDict(unicode(dev.id),u"closestRPI", -1)
									self.addToStatesUpdateDict(unicode(dev.id),u"closestRPIText", u"Pi_-1")
							#else: this is handled in RPI update
							#	 dev.updateStateImageOnServer(indigo.kStateImageSel.Error)

						if beacon in self.CARS[u"beacon"]: 
							self.updateCARS(beacon,dev,self.beacons[beacon])

						if u"showBeaconOnMap" in props and props[u"showBeaconOnMap"] in _GlobalConst_beaconPlotSymbols:self.beaconPositionsUpdated =3

					except	Exception, e:
						if unicode(e).find(u"timeout waiting") > -1:
							self.ML.myLog( text =  u"BeaconsCheckPeriod in Line '%s' has error='%s'" % (sys.exc_traceback.tb_lineno, e))
							self.ML.myLog( text =  u"BeaconsCheckPeriod communication to indigo is interrupted")
							return

				if now.minute != self.lastMinute:
					try :
						devId = int(self.beacons[beacon][u"indigoId"])
						if devId > 0 :
							try:
								dev = indigo.devices[self.beacons[beacon][u"indigoId"]]
								if self.beacons[beacon][u"ignore"]	 ==-1: # was specail, devcie exists now, set back to normal 
									self.beacons[beacon][u"ignore"]	  = 0
							except	Exception, e:
								if unicode(e).find(u"timeout waiting") > -1:
									self.ML.myLog( text =  u"BeaconsCheckPeriod in Line '%s' has error='%s'" % (sys.exc_traceback.tb_lineno, e))
									self.ML.myLog( text =  u"BeaconsCheckPeriod communication to indigo is interrupted")
									return
								if unicode(e).find(u"not found in database") ==-1:
									self.ML.myLog( text =  u"BeaconsCheckPeriod in Line '%s' has error='%s'" % (sys.exc_traceback.tb_lineno, e))
									return

								self.ML.myLog( text =  u"deleting device beaconDict: " + unicode(self.beacons[beacon]))
								self.beacons[beacon][u"indigoId"] = 0
								self.beacons[beacon][u"ignore"]	  = 1
								dev =""
								continue

							if dev != "" and dev.states[u"status"] == "up":

								for pi in range(_GlobalConst_numberOfiBeaconRPI):
									if	dev.states[u"Pi_" + unicode(pi) + u"_Distance"] == 99999.: continue
									if dev.states[u"Pi_" + unicode(pi) + u"_Time"] != "":
										piTime = dev.states[u"Pi_" + unicode(pi) + u"_Time"]
										piTime = datetime.datetime.strptime(piTime, _defaultDateStampFormat)
										if time.time()- time.mktime(piTime.timetuple()) > max(330., self.beacons[beacon][u"updateSignalValuesSeconds"]):
											if	dev.states[u"Pi_" + unicode(pi) + u"_Distance"] != 99999.:
												self.addToStatesUpdateDict(unicode(dev.id),u"Pi_" + unicode(pi) + u"_Distance", 99999.,decimalPlaces=1,dev=dev)
									else :
										self.addToStatesUpdateDict(unicode(dev.id),u"Pi_" + unicode(pi) + u"_Distance", 99999.,decimalPlaces=1,dev=dev)
							self.executeUpdateStatesDict(onlyDevID =str(dev.id), calledFrom="BeaconsCheckPeriod 2")

							if beacon in self.CARS[u"beacon"]: 
								self.updateCARS(beacon,dev,self.beacons[beacon])


					except	Exception, e:
						if len(unicode(e)) > 5 :
							self.ML.myLog( text =  u"BeaconsCheckPeriod in Line '%s' has error='%s'" % (sys.exc_traceback.tb_lineno, e))

				if dev !="":
					self.executeUpdateStatesDict(onlyDevID =str(dev.id),calledFrom="BeaconsCheckPeriod end")

		except	Exception, e:
			if len(unicode(e)) > 5 :
				self.ML.myLog( text =  u"BeaconsCheckPeriod in Line '%s' has error='%s'" % (sys.exc_traceback.tb_lineno, e))
		return anyChange

####-------------------------------------------------------------------------####
	def checkHour(self,now):
		if now.hour == self.lastHour: return
		if now.hour ==0:
			self.resetMinMaxSensors()
		self.rollOverRainSensors()
			
		try:
			self.fixConfig(checkOnly = ["all","rpi","force"],fromPGM="checkHour")
			if now.hour ==0 :
				self.checkPiEnabled()
				
			self.saveCARS(force=True)
			try:
				for beacon in self.beacons:	 # sync with indigo
					if self.beacons[beacon][u"indigoId"] != 0:	# sync with indigo
						try :
							dev = indigo.devices[self.beacons[beacon][u"indigoId"]]
							if self.beacons[beacon][u"ignore"] == 1:
								self.ML.myLog( errorType = u"smallErr", text =u"deleting device: " + dev.name + " beacon to be ignored, clean up ")
								indigo.device.delete(dev)
								continue
							self.beacons[beacon][u"status"] = dev.states[u"status"]
							self.beacons[beacon][u"note"] = dev.states[u"note"]
							
	 
							if self.removeJunkBeacons:
								if dev.name == u"beacon_" + beacon and self.beacons[beacon][u"status"] == u"expired" and time.time()- self.beacons[beacon][u"lastUp"] > 3600 and self.countLoop > 10 :
									self.ML.myLog( errorType = u"smallErr", text =u"deleting beacon: " + dev.name + u"	expired, no messages for > 1 hour and still old name, if you want to keep beacons, you must rename them after they are created")
									self.beacons[beacon][u"ignore"] = 1
									self.newIgnoreMAC += 1
									indigo.device.delete(dev)
						except	Exception, e:
							if len(unicode(e)) > 5 :
								self.ML.myLog( text =  u"checkHour in Line '%s' has error='%s'" % (sys.exc_traceback.tb_lineno, e))
							if unicode(e).find(u"timeout waiting") >-1:
								self.ML.myLog( text =  u"communication to indigo is interrupted")
								return
							if unicode(e).find(u"not found in database") >-1:
								self.ML.myLog( text = "indigoId lookup error, setting to ignore beaconDict: "+ unicode(self.beacons[beacon])  )
								self.beacons[beacon][u"indigoId"] = 0
								self.beacons[beacon][u"ignore"] = 1
								self.beacons[beacon][u"status"] = u"ignored"
							else:
								return
					else :
						self.beacons[beacon][u"status"] = u"ignored"
						if self.beacons[beacon][u"ignore"] == 0:
							self.ML.myLog( text =  u"setting beacon: " +beacon + u" to ignore was set to indigo-id=0 before")
							self.beacons[beacon][u"ignore"] = 1
							self.newIgnoreMAC += 1
			except	Exception, e:
				if len(unicode(e)) > 5 :
					self.ML.myLog( text =  u"checkHour in Line '%s' has error='%s'" % (sys.exc_traceback.tb_lineno, e))

			try:
				if now.hour == 0:
					self.deleteAndCeateVariables(True)	# delete and recreate the variables at midnight to remove their sql database entries
					self.setALLrPiV(u"piUpToDate", [u"updateParamsFTP"])
					##self.rPiRestartCommand = [u"" for ii in range(_GlobalConst_numberOfRPI)] # dont do this use the default for each pibeacon
					self.setupFilesForPi()
					for pi in range(0, _GlobalConst_numberOfRPI) :
						self.sendFilesToPiServerFTP(pi, fileToSend=u"updateParamsFTP.exp")
					self.updateRejectLists()
			except	Exception, e:
				if len(unicode(e)) > 5 :
					self.ML.myLog( text =  u"checkHour in Line '%s' has error='%s'" % (sys.exc_traceback.tb_lineno, e))
		except	Exception, e:
			if len(unicode(e)) > 5 :
				self.ML.myLog( text =  u"checkHour in Line '%s' has error='%s'" % (sys.exc_traceback.tb_lineno, e))


####-------------------------------------------------------------------------####
	def checkPiEnabled(self): # check if pi is defined, but not enabled, give warning at startup
		try:
			for pi in range(_GlobalConst_numberOfRPI):
				if self.RPI[unicode(pi)][u"piOnOff"] != u"0": continue
				if self.RPI[unicode(pi)][u"piDevId"] ==	   0: continue

				if (self.RPI[unicode(pi)][u"passwordPi"]		 !=""  and
					self.RPI[unicode(pi)][u"userIdPi"]			 !=""  and
					self.RPI[unicode(pi)][u"ipNumberPi"]		 != "" and
					self.RPI[unicode(pi)][u"piMAC"]				 != "" and
					self.RPI[unicode(pi)][u"ipNumberPiSendTo"]	 != "" ):
						self.ML.myLog( text =  u"pi# " + unicode(pi) + " is configured but not enabled, mistake? This is checked once a day;  to turn it off set userId or password of unused rPi to empty ")
		except	Exception, e:
			self.ML.myLog( text =  u"checkPiEnabled in Line '%s' has error='%s'" % (sys.exc_traceback.tb_lineno, e))

####-------------------------------------------------------------------------####
	def syncSensors(self):
		try:
			anyChange = False
			#ss = time.time()
			for dev in indigo.devices.iter("props.isSensorDevice ,props.isOutputDevice"):
				sensor = dev.deviceTypeId
				devId  = dev.id
				props  = dev.pluginProps
				if u"piServerNumber" in props:
					try:
						pi = int(props[u"piServerNumber"])
					except:
						self.ML.myLog( text =  u"device not fully defined, please edit "+ dev.name+" pi# not defined "+unicode(props))
						continue

					if self.checkDevToPi(pi, devId, dev.name, u"input",  u"in",  sensor, _GlobalConst_allowedSensors): anyChange= True
					#indigo.server.log("syncSensors A01: "+ str(anyChange)+"  "+ str(time.time() - ss))
					if self.checkDevToPi(pi, devId, dev.name, u"output", u"out", sensor, _GlobalConst_allowedOUTPUT):  anyChange= True
					#indigo.server.log("syncSensors A02: "+ str(anyChange)+"  "+ str(time.time() - ss))

				if u"description" in props and	props[u"description"] !="" and props[u"description"] != dev.description:
					dev.description =  props[u"description"] 
					dev.replaceOnServer()
					anyChange = True
			#indigo.server.log("syncSensors AT: "+ str(anyChange)+"  "+ str(time.time() - ss))

			for pi in range(_GlobalConst_numberOfRPI):
				self.checkSensortoPi(pi, u"input")
				self.checkSensortoPi(pi, u"output")
				if self.mkSensorList(pi): anyChange =True
			#indigo.server.log("syncSensors BT: "+ str(anyChange)+"  "+ str(time.time() - ss))

		except	Exception, e:
			self.ML.myLog( text =  u"syncSensors in Line '%s' has error='%s'" % (sys.exc_traceback.tb_lineno, e))
		return anyChange



####-------------------------------------------------------------------------####
	def checkDevToPi(self, pi, devId, name, io, io2, sensor, allowedS):
		try:
			anyChange = False
			if sensor not in allowedS: return False

			if sensor not in self.RPI[unicode(pi)][io]:
				try:
					dev=indigo.devices[int(devId)]
					name=dev.name
				except Exception, e:
		
					self.ML.myLog( text =  u"checkDevToPi in Line '%s' has error='%s'" % (sys.exc_traceback.tb_lineno, e))
					if unicode(e).find(u"timeout waiting") > -1:
						self.ML.myLog( text =  u"communication to indigo is interrupted")
						return False
					if unicode(e).find(u"not found in database") ==-1:
						return False
					name=""
				self.ML.myLog( text =  u"fixing 1  " + name + "	 " + unicode(devId) + " pi " + unicode(pi) + "; sensor: " + sensor+" devName: "+name)
				self.ML.myLog( text =  u"fixing 1  rpi " + unicode(self.RPI[unicode(pi)][io]))
				self.RPI[unicode(pi)][io][sensor] = {unicode(devId): ""}
				self.setONErPiV(pi,"piUpToDate", [u"updateParamsFTP"])
				anyChange = True
			if len(self.RPI[unicode(pi)][io][sensor]) == 0:
				self.RPI[unicode(pi)][io][sensor] = {unicode(devId): ""}
				anyChange = True

			elif unicode(devId) not in self.RPI[unicode(pi)][io][sensor]:
				self.ML.myLog( text =  u"fixing 2  " + name + "	 " + unicode(devId) + u" pi " + unicode(pi) + u" sensor" + sensor)
				self.RPI[unicode(pi)][io][sensor][unicode(devId)] = ""
				anyChange = True
		except	Exception, e:
			self.ML.myLog( text =  u"checkDevToPi in Line '%s' has error='%s'" % (sys.exc_traceback.tb_lineno, e))
		return anyChange



####-------------------------------------------------------------------------####
	def checkSensortoPi(self, pi, io):
		try:
			anyChange = False
			for sensor in self.RPI[unicode(pi)][io]:
				if len(self.RPI[unicode(pi)][io][sensor]) > 0:
					deldevID = {}
					for devIDrpi in self.RPI[unicode(pi)][io][sensor]:
						try:
							try:
								devID = int(devIDrpi)
								dev = indigo.devices[devID]
							except	Exception, e:
								if unicode(e).find(u"timeout waiting") > -1:
									self.ML.myLog( text =  u"checkSensortoPi in Line '%s' has error='%s'" % (sys.exc_traceback.tb_lineno, e))
									self.ML.myLog( text =  u"communication to indigo is interrupted")
									return True
								if unicode(e).find(u" not found in database") ==-1:
									self.ML.myLog( text =  u"checkSensortoPi in Line '%s' has error='%s'" % (sys.exc_traceback.tb_lineno, e))
									return True

								deldevID[devIDrpi] = 1
								self.ML.myLog( text = "device not found in indigo DB, ok if device was just deleted")
								self.ML.myLog( text = "removing input device from parameters for pi#:" + unicode(pi) + u"  devID=" + unicode(devIDrpi))
								anyChange = True
								continue


							props = dev.pluginProps
							if u"rPiEnable"+unicode(pi) not in props and  u"piServerNumber" not in props:
								self.ML.myLog( text = "piServerNumber not in props for pi#:" + unicode(pi) + u"	 devID=" + unicode(self.RPI[unicode(pi)][io][sensor])+u" removing sensor")
								self.RPI[unicode(pi)][io][sensor] = {}
								anyChange = True
								continue

							if u"piServerNumber" in props:
								if sensor != dev.deviceTypeId or devID != dev.id or pi != int(props[u"piServerNumber"]):
									self.ML.myLog( text = u"sensor/devid/pi/wrong for  pi#:" + unicode(pi)	+ u"  devID=" + unicode(self.RPI[unicode(pi)][io][sensor])+u" props"+unicode(props)+u"\n >>>>>	removing sensor	 <<<<")
									self.RPI[unicode(pi)][io][sensor] = {}
									anyChange = True
								if u"address" in props:
									if props[u"address"] != u"Pi-" + unicode(pi):
										props[u"address"] = u"Pi-" + unicode(pi)
										if self.ML.decideMyLog(u"Logic"): self.ML.myLog( text = "updating address for "+unicode(pi))
										dev.replacePluginPropsOnServer(props)
										anyChange = True
								else:
									props[u"address"] = u"Pi-" + unicode(pi)
									dev.replacePluginPropsOnServer(props)
									if self.ML.decideMyLog(u"Logic"): self.ML.myLog( text = "updating address for "+unicode(pi))
									anyChange = True
							else:
								pass

						except	Exception, e:
							self.ML.myLog( text =  u"checkSensortoPi in Line '%s' :'%s'" % (sys.exc_traceback.tb_lineno, e))
							if unicode(e).find(u"not found in database") ==-1:
								return TRue
							self.ML.myLog( text = u"removing input device from parameters for pi#:" + unicode(pi) + u"	devID=" + unicode(self.RPI[unicode(pi)][io][sensor]))
							deldevID[devIDrpi] = 1
					for devIDrpi in deldevID:
						del self.RPI[unicode(pi)][io][sensor][devIDrpi]
						anyChange = True

			delsen = {}
			for sensor in self.RPI[unicode(pi)][io]:
				if len(self.RPI[unicode(pi)][io][sensor]) == 0:
					delsen[sensor] = 1
			for sensor in delsen:
				anyChange = True
				del self.RPI[unicode(pi)][io][sensor]

		except	Exception, e:
			self.ML.myLog( text =  u"checkSensortoPi in Line '%s' has error='%s'" % (sys.exc_traceback.tb_lineno, e))
		return anyChange

####----------------------reset sensor min max at midnight -----------------------------------####
	def resetMinMaxSensors(self, init=False):
		try:
			nHour = (datetime.datetime.now()).hour 
			for dev in indigo.devices.iter(self.pluginId):
				if	dev.enabled: 
					for ttx in _GlobalConst_fillMinMaxStates:
						if ttx in dev.states and ttx+u"MaxToday" in dev.states:
							try:	val = float(dev.states[ttx])
							except: val = 0
							try:
								xxx = unicode(dev.states[ttx]).split(".")
								if len(xxx) ==1:
									decimalPlaces = 1
								else:
									decimalPlaces = len(xx[1])
							except:
								decimalPlaces = 2

							if init: # at start of pgm	
								reset = False
								try: 
									int(dev.states[ttx+u"MinYesterday"])
								except:
									reset = True
								if not reset: 
									if	(float(dev.states[ttx+u"MaxToday"]) == float(dev.states[ttx+u"MinToday"]) and float(dev.states[ttx+u"MaxToday"]) == 0.) :	 reset = True
								if reset:
									self.addToStatesUpdateDict(unicode(dev.id),ttx+u"MaxYesterday", val,decimalPlaces=decimalPlaces,dev=dev)
									self.addToStatesUpdateDict(unicode(dev.id),ttx+u"MinYesterday", val,decimalPlaces=decimalPlaces)
									self.addToStatesUpdateDict(unicode(dev.id),ttx+u"MaxToday",		val,decimalPlaces=decimalPlaces)
									self.addToStatesUpdateDict(unicode(dev.id),ttx+u"MinToday",		val,decimalPlaces=decimalPlaces)

							elif nHour ==0:	 # update at midnight 
									self.addToStatesUpdateDict(unicode(dev.id),ttx+u"MaxYesterday", dev.states[ttx+u"MaxToday"], decimalPlaces = decimalPlaces,dev=dev)
									self.addToStatesUpdateDict(unicode(dev.id),ttx+u"MinYesterday", dev.states[ttx+u"MinToday"], decimalPlaces = decimalPlaces)
									self.addToStatesUpdateDict(unicode(dev.id),ttx+u"MaxToday",		dev.states[ttx], decimalPlaces = decimalPlaces)
									self.addToStatesUpdateDict(unicode(dev.id),ttx+u"MinToday",		dev.states[ttx], decimalPlaces = decimalPlaces)
							self.executeUpdateStatesDict(onlyDevID =str(dev.id),calledFrom="resetMinMaxSensors")
		except	Exception, e:
			self.ML.myLog( text =  u"resetMinMaxSensors in Line '%s' has error='%s'" % (sys.exc_traceback.tb_lineno, e))

####----------------------reset sensor min max at midnight -----------------------------------####
	def fillMinMaxSensors(self,dev,stateName,value,decimalPlaces):
		try:
			if stateName not in _GlobalConst_fillMinMaxStates: return 
			if stateName in dev.states and stateName+u"MaxToday" in dev.states:
				if self.ML.decideMyLog(u"SensorData"): self.ML.myLog( text =  u"fillMinMaxSensors "+dev.name+"	"+stateName+";	newV= "+unicode(value)+";  in dev.states= "+unicode(dev.states[stateName])+"  dec_pl="+ unicode(decimalPlaces) )
				val = float(value)
				if val > float(dev.states[stateName+u"MaxToday"]):
					self.addToStatesUpdateDict(unicode(dev.id),stateName+u"MaxToday",	 val, decimalPlaces=decimalPlaces,dev=dev)
				if val < float(dev.states[stateName+u"MinToday"]):
					self.addToStatesUpdateDict(unicode(dev.id),stateName+u"MinToday",	 val, decimalPlaces=decimalPlaces,dev=dev)
		except	Exception, e:
			self.ML.myLog( text =  u"fillMinMaxSensors in Line '%s' has error='%s'" % (sys.exc_traceback.tb_lineno, e))

####----------------------reset rain sensor every hour/day/week/month/year -----------------------------------####
	def rollOverRainSensors(self):
		try:
			dd = datetime.datetime.now()
			currDate = (dd.strftime("%Y-%m-%d-%H")).split("-")
			weekNumber = dd.isocalendar()[1]
			
			#self.ML.myLog( text =	u"currDate: " +unicode(currDate), mType="rollOverRainSensors")
			for dev in indigo.devices.iter("props.isSensorDevice"):
				if dev.deviceTypeId.find(u"rainSensorRG11") == -1: continue
				if	not dev.enabled: continue
				props = dev.pluginProps
				lastTest = props["lastDateCheck"].split("-")
				try:
					ff = datetime.datetime.strptime(props["lastDateCheck"], "%Y-%m-%d-%H")
					lastweek = ff.isocalendar()[1]
				except:
					lastweek = -1
					
				#self.ML.myLog( text =	u"lasttest: " +unicode(lastTest), mType="rollOverRainSensors")
				for test in ["hour","day","week","month","year"]:
					if test == "hour"	and int(lastTest[3]) == int(currDate[3]): continue
					if test == "day"	and int(lastTest[2]) == int(currDate[2]): continue
					if test == "month"	and int(lastTest[1]) == int(currDate[1]): continue
					if test == "year"	and int(lastTest[0]) == int(currDate[0]): continue
					if test == "week"	and lastweek		 == weekNumber:		  continue
					ttx = test+"Rain"
					val = dev.states[ttx]
					#self.ML.myLog( text =	u"rolling over: " +unicode(ttx)+";	using current val: "+ str(val), mType="rollOverRainSensors")
					self.addToStatesUpdateDict(unicode(dev.id),"last"+ttx, val,decimalPlaces=self.rainDigits,dev=dev)
					self.addToStatesUpdateDict(unicode(dev.id),ttx, 0,decimalPlaces=self.rainDigits,dev=dev)
					try:	 props[test+"RainTotal"]  = float(dev.states["totalRain"])
					except:	 props[test+"RainTotal"]  = 0
				props["lastDateCheck"] = dd.strftime("%Y-%m-%d-%H")
				dev.replacePluginPropsOnServer(props)
				self.executeUpdateStatesDict(onlyDevID =str(dev.id),calledFrom="rollOverRainSensors")
		except	Exception, e:
			self.ML.myLog( text =  u"resetMinMaxSensors in Line '%s' has error='%s'" % (sys.exc_traceback.tb_lineno, e))


####-------------------------------------------------------------------------####
	def mkSensorList(self, pi):
		try:
			anyChange = False
			sensorList = ""
			INPgpioTypes = []
			for sensor in self.RPI[unicode(pi)][u"input"]:
				if sensor not in _GlobalConst_allowedSensors and sensor not in _GlobalConst_allowedOUTPUT : continue
				if sensor ==u"ultrasoundDistance": continue
				try:
					#					 devId= int(self.RPI[unicode(pi)][u"input"][sensor].keys()[0])# we only need the first one
					for devIds in self.RPI[unicode(pi)][u"input"][sensor]:
						devId = int(devIds)
						if devId < 1: 1 / 0
						dev = indigo.devices[devId]
						props = dev.pluginProps
						if dev.enabled:
							sensorList += sensor+"*"+unicode(devId)	 # added; below only works if just one BLE if several and only one gets disabled it is still present, hence we need to add extra
							if u"i2cAddress" in props:
								sensorList+= "*"+props[u"i2cAddress"]
							if u"spiAddress" in props:
								sensorList+= "*"+props[u"spiAddress"]
							if u"gpioPin" in props:
								sensorList+= "*"+props[u"gpioPin"]
							if u"resModel" in props:
								sensorList+= "*"+props[u"resModel"]
							if u"gain" in props:
								sensorList+= "*"+props[u"gain"]
							sensorList+=","
							
				except	Exception, e:
					self.ML.myLog( text =  u"mkSensorList in Line '%s' has error='%s'" % (sys.exc_traceback.tb_lineno, e))
					if unicode(e).find(u"timeout waiting") > -1:
						self.ML.myLog( text =  u"communication to indigo is interrupted")
						return
					if unicode(e).find(u"not found in database") ==-1:
						return
					self.RPI[unicode(pi)][u"input"][sensor] = {}
			if sensorList != self.RPI[unicode(pi)][u"sensorList"]:
				self.setONErPiV(pi,"piUpToDate", [u"updateParamsFTP"])
				anyChange = True
			self.RPI[unicode(pi)][u"sensorList"] = sensorList

		except	Exception, e:
			self.ML.myLog( text =  u"mkSensorList in Line '%s' has error='%s'" % (sys.exc_traceback.tb_lineno, e))
		return anyChange

#####################################################################################################################################
#####################################################################################################################################
#####################################################################################################################################
##########################################			 receive messages from RPI				#########################################
#####################################################################################################################################
#####################################################################################################################################
#####################################################################################################################################
 


####-------------------------------------------------------------------------####
	def variableUpdated(self, origVar, newVar):
		try:
			if len(newVar.value) < 3:			   return
			if newVar.name.find(u"pi_IN_") != 0:   return
			self.addToDataQueue(newVar.name,json.loads(newVar.value),newVar.value )
			return
		except	Exception, e:
			self.ML.myLog( text =  u"variableUpdated in Line '%s' has error='%s'" % (sys.exc_traceback.tb_lineno, e))
			self.ML.myLog( text =  newVar.value)


####-------------------------------------------------------------------------####
	def addToDataQueue(self,  varNameIN, varJson, varUnicode):	#
		try:
			if not	self.stackReady : return 

			## alive message?
			if varNameIN == u"pi_IN_Alive":
				self.updateAlive(varJson,varUnicode, time.time())
				if self.statusChanged > 0:	  
					self.setGroupStatus()
				return
				
			## check pi#s  etc 
			try:
				pi = int(varNameIN.split(u"_IN_")[1])  ## it is pi_IN_0 .. pi_IN_99
			except:
				self.ML.myLog( text =  u"bad data  Pi not integer: " + varNameIN)
				return
				
			if pi < 0  or pi >= _GlobalConst_numberOfRPI:
				self.ML.myLog( text = u"pi# rejected outside range:	 "+varNameIN)
				return


			## add to message queue
			self.messagesQueue.put((time.time(), pi,varJson,varUnicode))
			if not self.queueActive: 
				self.workOnQueue()


			##
			# update non competing stuff, does not have be done sequential

			##
			# update RPI expirations
			self.RPI[unicode(pi)][u"lastMessage"] = time.time()
			self.setRPIonline(pi)

			##
			# update sensors
			if u"sensors" in varJson:
				if "BLEconnect" in varJson[u"sensors"]:
					self.BLEconnectupdateAll(pi, varJson[u"sensors"])

				self.updateSensors(pi, varJson[u"sensors"])

			##
			if u"BLEreport" in varJson: 
				self.printBLEreport(varJson["BLEreport"])
				return 

			##
			if u"i2c" in varJson:
				self.checkI2c(pi, varJson[u"i2c"])

			##
			if u"bluetooth" in varJson:
				self.checkBlueTooth(pi, varJson[u"bluetooth"])


			
		except	Exception, e:
			self.ML.myLog( text =  u"addToDataQueue in Line '%s' has error='%s'" % (sys.exc_traceback.tb_lineno, e))
			self.ML.myLog( text =  varNameIN+"	" + varUnicode[0:30])


####-------------------------------------------------------------------------####
	def workOnQueue(self):

		self.queueActive  = True
		while not self.messagesQueue.empty():
			item = self.messagesQueue.get() 
			for ii in range(40):
				if self.queueList ==u"update" : break
				if self.queueList ==u""		  : break
				if ii > 0:	pass#if self.ML.decideMyLog(u"Special"): self.ML.myLog( text =	u"wait for queue to become available in workOnqueue,  ii="+unicode(ii)+u"  "+self.queueList)
				time.sleep(0.05)
			self.queueList = "update"  
			self.execUpdate(item[0],item[1],item[2],item[3])
		self.messagesQueue.task_done()
		self.queueActive  = False
		self.queueList = ""	 
		if len(self.sendBroadCastEventsList) >0: self.sendBroadCastNOW()
		return
 
####-------------------------------------------------------------------------####
	def execUpdate(self,  timeStampOfReceive, pi,data,varUnicode):

		try:

			retCode, piMAC, piN = self.checkincomingMACNo(data, pi, timeStampOfReceive)
			if not retCode: return

			if pi >= _GlobalConst_numberOfiBeaconRPI: return 


			### here goes the beacon data updates  -->

			if self.selectBeaconsLogTimer !={}: 
				for sMAC in self.selectBeaconsLogTimer:
					if piMAC.find(sMAC[:self.selectBeaconsLogTimer[sMAC]]) ==0:
						self.ML.myLog( text =	   u"sel.beacon logging: RPI msg	:"+piMAC+"; "+(" ").ljust(36)	 + " pi#="+str(pi)		)

			if u"msgs" in data:
				if self.ML.decideMyLog(u"BeaconData"): self.ML.myLog( text = u"new iBeacon message----------------------------------- \n "+varUnicode)
				secondsCollected = 0
				if u"secsCol" in data:
					secondsCollected = data[u"secsCol"]
				if u"reason" in data:
					reason = data[u"reason"]
				msgs = data[u"msgs"]
				if len(msgs) > 0 and piMAC != "":
					if u"ipAddress" in data:
						ipAddress = data[u"ipAddress"]
						if self.RPI[unicode(pi)][u"ipNumberPi"] != "" and self.RPI[unicode(pi)][u"ipNumberPi"] != ipAddress:
							if ipAddress == "":
								self.setONErPiV(pi,"piUpToDate", [u"updateParamsFTP","rebootSSH"])
								self.ML.myLog( text =  u"rPi#: " + unicode(pi) + u"	 >>" + ipAddress + u"<<	  ip#  send from rPi is empty, will restart rPi, ip# should be" + self.RPI[unicode(pi)][u"ipNumberPi"])
								return
							else:
								self.ML.myLog( text =  u"rPi#: " + unicode(pi) + u"	 >>" + ipAddress +
										   u"<<	  ip number has changed, please fix in menue/pibeacon/setup pi or changed Ip number or send restart to rPi; old >>" +
										   self.RPI[unicode(pi)][u"ipNumberPi"] + u"<<	received from pi: >>" + ipAddress+u"<<")
								return
					else:
						ipAddress = u""
					self.updateBeaconStates(pi, unicode(piN), ipAddress, piMAC, secondsCollected, msgs)
					self.RPI[unicode(pi)][u"emptyMessages"] = 0
				elif len(msgs) == 0 and piMAC != "":
					self.RPI[unicode(pi)][u"emptyMessages"] +=1
					if	self.RPI[unicode(pi)][u"emptyMessages"] >  min(self.enableRebootRPIifNoMessages,10) :
						if	self.RPI[unicode(pi)][u"emptyMessages"] %5 ==0:
							self.ML.myLog( text =  "RPI# "+unicode(pi)+" check , too many empty messages in a row: " + str(self.RPI[unicode(pi)][u"emptyMessages"]) )
							self.ML.myLog( text =  " please check RPI" )
						if	self.RPI[unicode(pi)][u"emptyMessages"] > self.enableRebootRPIifNoMessages:
							self.ML.myLog( text =  "RPI# "+unicode(pi)+" check , too many empty messages in a row: " + str(self.RPI[unicode(pi)][u"emptyMessages"]) )
							self.ML.myLog( text =  "sending reboot command to RPI")
							self.setONErPiV(pi,"piUpToDate",[u"updateParamsFTP","rebootSSH"])
							self.RPI[unicode(pi)][u"emptyMessages"] = 0
				

		except	Exception, e:
			self.ML.myLog( text =  u"execUpdate in Line '%s' has error='%s'" % (sys.exc_traceback.tb_lineno, e))
			self.ML.myLog( text =  varUnicode)

		if self.statusChanged > 0:	  
			self.setGroupStatus()
		return


####-------------------------------------------------------------------------####
	def checkincomingMACNo(self, data, pi,timeStampOfReceive):

		try:

			if u"mac" in data:
				piMAC = data[u"mac"]
			else:
				piMAC =""


			piN = int(data[u"pi"])
			if piN < 0 or piN >= _GlobalConst_numberOfRPI :
				if self.ML.decideMyLog(u"all"): self.ML.myLog( text =  u"bad data  Pi# not in range: "+unicode(piN))
				return	False, "", ""

			try:	
				devPI = indigo.devices[self.RPI[unicode(piN)][u"piDevId"]]
				if u"ts" in data and devPI !="":
					self.compareRpiTime(data,unicode(pi),devPI, timeStampOfReceive)
			except: 
				pass

			if pi >= _GlobalConst_numberOfiBeaconRPI:
				self.checkSensorPiSetup(pi,data,piN )
				return True, piMAC, piN 
		
			if piMAC !="":
				beacon=	 self.RPI[unicode(pi)][u"piMAC"]
				if piMAC != beacon:
					if self.ML.decideMyLog(u"Logic"): self.ML.myLog( text =	 u"MAC# from RPI message is new "+piMAC+u" trying with new BLE-MAC number, old MAC#="+beacon+"--  pi#"+unicode(pi))
					beacon = piMAC
				if len(beacon) == 17: ## len(u"11:22:33:44:55:66")
						indigoId = int(self.RPI[unicode(pi)][u"piDevId"])
						if len(self.RPI[unicode(pi)][u"piMAC"]) != 17 or indigoId == 0:
							if self.ML.decideMyLog(u"Logic"): self.ML.myLog( text =	 u"MAC# from RPI message is new "+beacon+u" not in internal list .. new RPI?"+unicode(pi))
					
						else: # existing RPI with valid MAC # and indigo ID 
							if self.RPI[unicode(pi)][u"piMAC"] != beacon and indigoId > 0:
								try:
									devPI = indigo.devices[indigoId]
									props= devPI.pluginProps
									props[u"address"] = beacon
									devPI.replacePluginPropsOnServer(props)
									if self.RPI[unicode(pi)][u"piMAC"] in self.beacons:
										self.beacons[beacon]			 = copy.deepcopy(self.beacons[self.RPI[unicode(pi)][u"piMAC"]] )
									else:
										self.beacons[beacon]			 = copy.deepcopy(_GlobalConst_emptyBeacon)
									
									self.beacons[piMAC][u"indigoId"] = indigoId
									self.RPI[unicode(pi)][u"piMAC"] = beacon
									if self.ML.decideMyLog(u"Logic"): self.ML.myLog( text =	 u"MAC# from RPI  was updated")
								except	Exception, e:
									self.ML.myLog( text =  u"execUpdate in Line '%s' has error='%s'" % (sys.exc_traceback.tb_lineno, e))
									if self.ML.decideMyLog(u"Logic"): self.ML.myLog( text =	 u"MAC# from RPI...	 indigoId:"+str(indigoId)+u" does not exist, ignoring")

						# added to cover situation when RPI was set to expire by mistake ==>  reset it to ok		
						if beacon in self.beacons: 
							if self.beacons[beacon][u"ignore"] > 0: self.beacons[beacon][u"ignore"] = 0
							self.beacons[beacon][u"lastUp"] = time.time()

		except	Exception, e:
			self.ML.myLog( text =  u"execUpdate in Line '%s' has error='%s'" % (sys.exc_traceback.tb_lineno, e))
			return False, "", ""

		return True, piMAC, piN 



####-------------------------------------------------------------------------####
	def compareRpiTime(self, data, pi, devPI, timeStampOfReceive):
		dt = time.time() - timeStampOfReceive
		if dt > 4.: self.ML.myLog( text =  u"significant internal delay occured digesting data from	 rPi: "+str(pi)+u"	%f5.1 [secs]"%dt) 
		try:
			if u"ts" not in data: return 
			#if pi ==u"0": self.ML.myLog( text =  u"rPi "+unicode(pi)+"	 into compareRpiTime " +unicode(data))
			tzMAC = time.tzname[1]
			if len(tzMAC) <3: tzMAC=time.tzname[0]
			if u"deltaTime" in data:
				self.RPI[pi][u"deltaTime1"] = data[u"deltaTime"]
			else:
				deltaTime = 0
			

			if u"ts" not in data:
				return 
			if u"time" not in data[u"ts"]:
				return	   
			ts = data[u"ts"][u"time"]
			tz = data[u"ts"][u"tz"]
			try:	  deltaT = time.time()- ts
			except:	  deltaT = 101
			self.RPI[pi][u"deltaTime2"] = deltaT
			
			props = devPI.pluginProps
			if u"syncTimeWithMAC" in props and props[u"syncTimeWithMAC"] !="" and props[u"syncTimeWithMAC"] =="0": return 

			if tz!= tzMAC:
				if self.timeErrorCount[int(pi)]	 < 2:
					self.ML.myLog( text =  u"rPi "+unicode(pi)+u" wrong time zone: " + tz + u"	vs "+ tzMAC+u"	on MAC ")
					self.timeErrorCount[int(pi)] +=1
					return

			if devPI !="":
					try:
						sT= float(props[u"syncTimeWithMAC"])
						if abs(time.time()-float(ts)) > sT and tz == tzMAC and self.timeErrorCount[int(pi)] < 5:
							self.timeErrorCount[int(pi)]  +=5
							alreadyUnderway = False
							for action in self.actionList:
								if u"action" in action and action[u"action"] == u"setTime" and action[u"value"] == unicode(pi):
									alreadyUnderway = True
									break
							if not alreadyUnderway:
								self.actionList.append({u"action":"setTime","value":unicode(pi)})
								self.ML.myLog( text =  u"rPi "+unicode(pi)+u" do a time sync MAC --> RPI, time off by: %5.1f"%(time.time()-ts)+u"[secs]"  )
					except: pass


			if tz != tzMAC or (abs(deltaT) > 100):
				# do not check time / time zone if disabled 
					self.timeErrorCount[int(pi)] +=1
					if self.timeErrorCount[int(pi)]	 < 3:
						try:	  deltaT = unicode(int(deltaT))
						except:	  deltaT = unicode(int(time.time())) +" - "+ str(ts)
						self.ML.myLog( text =  u"please do \"sudo raspi-config\" on rPi: "+unicode(pi)+u", set time, reboot ...	 send: TIME-Tsend= "+ deltaT+u"	 /epoch seconds UTC/  timestamp send="+str(ts)	+u"; TZ send is="+tz )

			if (abs(time.time()-float(ts)) < 2. and tz == tzMAC)  or self.timeErrorCount[int(pi)] > 1000:
				self.timeErrorCount[int(pi)] = 0

		except	Exception, e:
			if unicode(e).find(u"timeout waiting") > -1:
				self.ML.myLog( text =  u"communication to indigo is interrupted")
			self.ML.myLog( text =  u"compareRpiTime in Line '%s' has error='%s'" % (sys.exc_traceback.tb_lineno, e))
		return


####-------------------------------------------------------------------------####
	def printBLEreport(self, BLEreport):
		try:
			self.ML.myLog( text =  u"BLEreport received:")
			for rep in BLEreport:
					self.ML.myLog( text =	   u"=======================================\n"+BLEreport[rep][0].strip(u"\n"),mType = rep)
					if len(BLEreport[rep][1]) < 5:
						self.ML.myLog( text =  u"no errors")
					else:
						self.ML.myLog( text =  u"errors:\n"+BLEreport[rep][1].strip(u"\n"),mType = rep)
		except	Exception, e:
			self.ML.myLog( text =  u"printBLEreport in Line '%s' has error='%s'" % (sys.exc_traceback.tb_lineno, e))


####-------------------------------------------------------------------------####
	def checkI2c(self, pi, i2c):
		try:
			for i2cChannel in i2c:
				if i2cChannel is not None:
					if i2cChannel.find(u"i2c.ERROR:.no.such.file....redo..SSD?") > -1 :
						self.ML.myLog( text =  u" pi#"+unicode(pi)+u"  has bad i2c config. you might need to replace SSD")
		except:
			pass


####-------------------------------------------------------------------------####
	def checkBlueTooth(self, pi, blueTooth):
		try:
			if blueTooth is not None:
				if blueTooth.find(u"startup.ERROR:...SSD.damaged?") > -1 :
					self.ML.myLog( text =  u" pi#"+unicode(pi)+u" bluetooth did not startup. you might need to replace SSD")
		except:
			pass


####-------------------------------------------------------------------------####
	def updateAlive(self, varJson,varUnicode,  timeStampOfReceive):
		if u"pi" not in varJson : return 
		try:
			if self.ML.decideMyLog(u"DevMgmt"):	 self.ML.myLog( text =	u"rPi alive message :  " + varUnicode)
			if (varUnicode).find(u"_dump_") >-1: 
				self.ML.myLog( text =  u"rPi error message: Please check that RPI  you might need to replace SD")
				self.ML.myLog( text =  varUnicode)
				return 
			pi = int(varJson[u"pi"])
			if pi >= _GlobalConst_numberOfRPI:
				self.ML.myLog( text =  u"pi# out of range: " + varUnicode)
				return

			self.RPI[unicode(pi)][u"lastMessage"] = time.time()

			if u"reboot" in varJson:
				self.setRPIonline(pi,new="reboot")
				indigo.variable.updateValue(self.ibeaconNameDefault+u"Rebooting","reset from :"+unicode(pi)+" at "+datetime.datetime.now().strftime(_defaultDateStampFormat))
				if u"text" in varJson and varJson[u"text"].find(u"bluetooth_startup.ERROR:") >-1:
					self.ML.myLog( text =  u"RPI# "+unicode(pi)+ " "+varJson[u"text"]+u" Please check that RPI ")
				return
				
			try:
				dev = indigo.devices[self.RPI[unicode(pi)][u"piDevId"]]
			except	Exception, e:
	
				if unicode(e).find(u"timeout waiting") > -1:
					self.ML.myLog( text =  u"updateAlive in Line '%s' has error='%s'" % (sys.exc_traceback.tb_lineno, e))
					self.ML.myLog( text =  u"communication to indigo is interrupted")
					return
				if unicode(e).find(u"not found in database") ==-1:
					self.ML.myLog( text =  u"updateAlive in Line '%s' has error='%s'" % (sys.exc_traceback.tb_lineno, e))
					return
				self.RPI[unicode(pi)][u"piDevId"]=0
				return
			self.compareRpiTime(varJson,unicode(pi),dev, timeStampOfReceive)
			self.setRPIonline(pi)

			if u"i2c" in varJson:
				i2c =unicode(varJson[u"i2c"]).strip(u"[").strip(u"]")
				if dev.states[u"i2cActive"] != i2c:
					self.addToStatesUpdateDict(unicode(dev.id),u"i2cActive", i2c,dev=dev)
			if u"temp" in varJson:
					x, UI, decimalPlaces  = self.convTemp(varJson[u"temp"])
					self.setStatusCol( dev, u"Temperature", x,"", "", "","", decimalPlaces = decimalPlaces)
 


			dev.updateStateImageOnServer(indigo.kStateImageSel.SensorOn)
			if dev.states[u"status"] != "up" :
				self.addToStatesUpdateDict(unicode(dev.id),u"status", u"up",dev=dev)
			if dev.states[u"online"] != "up":
				self.addToStatesUpdateDict(unicode(dev.id),u"online", u"up",dev=dev)
			if pi < _GlobalConst_numberOfiBeaconRPI:
				self.beacons[self.RPI[unicode(pi)][u"piMAC"]][u"lastUp"] = time.time()
				
			self.executeUpdateStatesDict(onlyDevID =str(dev.id), calledFrom="addToDataQueue pi_IN_Alive")

		except	Exception, e:
			if unicode(e).find(u"timeout waiting") > -1:
				self.ML.myLog( text =  u"updateAlive in Line '%s' has error='%s'" % (sys.exc_traceback.tb_lineno, e))
				self.ML.myLog( text =  u"communication to indigo is interrupted")
				return
			if len(unicode(e)) > 5 :
				self.ML.myLog( text =  u"updateAlive in Line '%s' has error='%s'" % (sys.exc_traceback.tb_lineno, e))
				self.ML.myLog( text =  u"variable pi_IN_Alive wrong format: " + varUnicode+" you need to push new upgrade to rPi")

		return
		
		
####-------------------------------------------------------------------------####
	def setRPIonline(self,pi,new="up"):
		try:
			try:	devID = int(self.RPI[unicode(pi)][u"piDevId"])
			except: devID = 0
			if devID ==0: return  # not setup yet 
			#self.ML.myLog( text =	u" setting online status of pi:"+unicode(pi)+" to "+ new)

			now = datetime.datetime.now().strftime(_defaultDateStampFormat)
			dev = indigo.devices[self.RPI[unicode(pi)][u"piDevId"]]
			if new==u"up":
				#self.addToStatesUpdateDict(unicode(dev.id),u"lastMessage", now,dev=dev)
				dev.updateStateImageOnServer(indigo.kStateImageSel.SensorOn)
				if u"status" in dev.states and dev.states[u"status"] != "up":
					self.addToStatesUpdateDict(unicode(devID),u"status", u"up",dev=dev)
				if u"online" in dev.states and dev.states[u"online"] != "up":
					self.addToStatesUpdateDict(unicode(dev.id),u"online", u"up",dev=dev)
				return
			if new==u"reboot":
				#self.addToStatesUpdateDict(unicode(dev.id),u"lastMessage", now,dev=dev)
				if dev.states[u"online"] != "reboot":
					self.ML.myLog( text =  u" setting status of pi# "+unicode(pi)+"	 to reboot for "+str(int(self.bootWaitTime))+" seconds or until new message arrives")
					dev.updateStateImageOnServer(indigo.kStateImageSel.SensorOff)
					self.addToStatesUpdateDict(unicode(dev.id),u"online", u"reboot",dev=dev)
					self.currentlyBooting=time.time()+self.bootWaitTime
					if pi >= _GlobalConst_numberOfiBeaconRPI: 
						self.addToStatesUpdateDict(unicode(dev.id),u"status", u"reboot",dev=dev)
					return
			if new==u"offline":
				if dev.states[u"online"] != "down":
					#dev.updateStateImageOnServer(indigo.kStateImageSel.SensorOff)
					self.addToStatesUpdateDict(unicode(dev.id),u"online", u"down",dev=dev)
					if pi >= _GlobalConst_numberOfiBeaconRPI: 
						self.addToStatesUpdateDict(unicode(dev.id),u"status", u"down",dev=dev)
					return
					
		except	Exception, e:
			if unicode(e).find(u"timeout waiting") > -1:
				self.ML.myLog( text =  u"setRPIonline in Line '%s' has error='%s'" % (sys.exc_traceback.tb_lineno, e))
				self.ML.myLog( text =  u"communication to indigo is interrupted")
				return
			if len(unicode(e)) > 5 :
				self.ML.myLog( text =  u"setRPIonline in Line '%s' has error='%s'" % (sys.exc_traceback.tb_lineno, e))
				self.ML.myLog( text =  u" pi" + unicode(pi)+"  RPI"+ unicode(self.RPI[unicode(pi)]) )
		return
####-------------------------------------------------------------------------####
	def checkSensorPiSetup(self, pi,data,piN):

		try:
			piSend	 = unicode(pi)
			piNReceived = unicode(piN)
			#self.ML.myLog( text =	u"called checkSensorPiSetup")
			if piSend != piNReceived:
				self.ML.myLog( text =  u"sensor pi " + unicode(pi) + " wrong pi# "+piNReceived+" number please fix in setup rPi")
				return -1
			if u"ipAddress" in data:	
				if self.RPI[unicode(pi)][u"ipNumberPi"] != data[u"ipAddress"]:
					self.ML.myLog( text =  u"sensor pi " + unicode(pi) + " wrong IP number please fix in setup rPi, received: -->" +data[u"ipAddress"]+"<-- if it is empty a rPi reboot might solve it")
					return -1
			devId = self.RPI[unicode(pi)][u"piDevId"]
			Found= False
			try:
				dev= indigo.devices[devId]
				Found =True
			except	Exception, e:
			   
				self.ML.myLog( text =  u"checkSensorPiSetup in Line '%s' has error='%s'" % (sys.exc_traceback.tb_lineno, e))
				if unicode(e).find(u"timeout waiting") > -1:
					self.ML.myLog( text =  u"communication to indigo is interrupted")
					return -1

			if not Found:
				self.ML.myLog( text =  u"sensor pi " + unicode(pi) + "- devId: " + unicode(devId) +" not found, please configure the rPi:  "+ unicode(self.RPI[unicode(pi)]))
			if Found:
				if dev.states[u"status"] != "up":
						self.addToStatesUpdateDict(unicode(dev.id),u"status",u"up",dev=dev)
						dev.updateStateImageOnServer(indigo.kStateImageSel.SensorOn)
				if dev.states[u"online"] != "up":
						self.addToStatesUpdateDict(unicode(dev.id),u"online",u"up",dev=dev)
						dev.updateStateImageOnServer(indigo.kStateImageSel.SensorOn)

		except	Exception, e:
			if len(unicode(e)) > 5 :			
				self.ML.myLog( text =  u"checkSensorPiSetup in Line '%s' has error='%s'" % (sys.exc_traceback.tb_lineno, e))
				self.ML.myLog( text =  unicode(data))
		return 0



####-------------------------------------------------------------------------####
	## as we accumulate changes , dev.states does not contain the latest. check update list and if not there then check dev.states
	def getCurrentState(self,dev,devIds,state,fromMETHOD=""):
		try:
			## if devIds == "169381397": self.ML.myLog( text = " getCurrentState:  updateStatesList=" + unicode(self.updateStatesDict) )
			if devIds in self.updateStatesDict and state in self.updateStatesDict[devIds]:
				#if dev.name == "b-node-js":indigo.server.log(dev.name+" using new info "+ unicode(self.updateStatesDict[devIds] ) +";;; ----	   old info= "+ unicode(dev.states ))
				#if devIds == "169381397": self.ML.myLog( text = " getCurrentState:	  state="+ state+"	returning=" + unicode(self.updateStatesDict[devIds]["keys"][state][0]) )
				return self.updateStatesDict[devIds][state]["value"] 
			else:  
				#if dev.name == "b-node-js": indigo.server.log(dev.name+" using old info "+ unicode(dev.states))
				return dev.states[state] 
				
		except	Exception, e:
			self.ML.myLog( text =  u"getCurrentState in Line '%s' has error='%s'" % (sys.exc_traceback.tb_lineno, e))
			self.ML.myLog( text =  u"  .. called from= "+ fromMETHOD+"	state= "+ state)
			self.ML.myLog( text =  u"  .. updateStatesList= " + unicode(self.updateStatesDict)	)
			try:	self.ML.myLog( text =  u"  .. dev= " + unicode(dev.name))
			except: self.ML.myLog( text =  u"  .. device does not exist, just deleted? .. IndigoId="+ devIds)
			return ""

####-------------------------------------------------------------------------####
	def calcPostion(self, dev, expirationTime): ## add Signal time dist status
		try:
			expirationTime	= max(90.,expirationTime)
			devID			= dev.id
			name			= dev.name
			devIds			= unicode(dev.id)
			deltaDistance	= 0.
			status			= "expired"
			distanceToRpi	 = []
			pitimeNearest	= "1900-00-00 00:00:00"
			lastUp			= 99999999999999
			lastUpS			= ""
			update			= False
			#if devID ==78067927: self.ML.myLog( text = "dist  "+ dev.name)
			try:
				lastUp	= 99999999999999
				if u"lastUp" in dev.states: 
					lastUpS = self.getCurrentState(dev,devIds,"lastUp", fromMETHOD="calcPostion1")
					if len(unicode(lastUpS)) > 5:
						lastUp	=  datetime.datetime.strptime(lastUpS, _defaultDateStampFormat)
						lastUp	=  time.mktime(lastUp.timetuple())
			except	Exception, e:
				self.ML.myLog( text =  u"calcPostion in Line '%s' has error='%s'" % (sys.exc_traceback.tb_lineno, e))
				lastUp	= 99999999999999
			
			#if dev.id == 169381397: self.ML.myLog( text = dev.name +"	calcPostion:  " + unicode(self.updateStatesDict) )

			for pi1 in range(_GlobalConst_numberOfiBeaconRPI):
				signal = self.getCurrentState(dev,devIds,"Pi_" + unicode(pi1) + "_Signal", fromMETHOD="calcPostion2")
				#if dev.id == 169381397: self.ML.myLog( text = "...pi1#"+ str(pi1) + "	 signal:"  + unicode(signal) )
				if signal == "": continue
				txPower = self.getCurrentState(dev,devIds,"TxPowerReceived")
				if txPower == "": txPower =-30
				#if dev.id == 169381397: self.ML.myLog( text = "...	  txPower:"	 + unicode(txPower) )

				piTimeS = self.getCurrentState(dev,devIds,"Pi_" + unicode(pi1) + "_Time", fromMETHOD="calcPostion3")
				#if dev.id == 169381397: self.ML.myLog( text = "...	  piTimeS:"	 + unicode(piTimeS) )
				if piTimeS is not None and len(piTimeS) < 5: continue

				if piTimeS > pitimeNearest:
					pitimeNearest = piTimeS
					
				try:
					piTime = datetime.datetime.strptime(piTimeS, _defaultDateStampFormat)
				except:
					piTime = datetime.datetime.now()
				piT2 = time.mktime(piTime.timetuple())
				try:
					dist = self.getCurrentState(dev,devIds,"Pi_" + unicode(pi1) + "_Distance", fromMETHOD="calcPostion4")
					dist = float(dist)
				except	Exception, e:
					self.ML.myLog( text =  u"calcPostion in Line '%s' has error='%s'" % (sys.exc_traceback.tb_lineno, e) +" "+ unicode(sys.exc_traceback))
					dist = 99999.

				if dist == 9999. and  lastUp != 99999999999999: 
					piT2 = lastUp

				#if name == "b-node-js": self.ML.myLog( text = dev.name +"	pi#:"  + unicode(pi1)+"	 dist:"	 + unicode(dist)+"	signal:"  + unicode(signal)+"  time.time()- piT2:"	+ unicode(time.time()- piT2) )
				if signal ==-999:
					if	 time.time()- piT2 <   						expirationTime:							 status = "up"
					elif time.time()- piT2 < self.expTimeMultiplier*expirationTime	and status == "expired": status = "down"
				   #elif time.time()- piT2 >   expirationTime	and status != "up":		 status = "down"
				else:
					if dist >= 99990. and txPower < -20:							 continue
					if dist == "" or (dist >= 99990. and signal > -50):				 continue # fake signals with bad TXpower 
					if dist > 50./max(self.distanceUnits,0.3) and signal > -50:		 continue # fake signals with bad TXpower 
					if time.time()- piT2  < expirationTime:											  # last signal not in expiration range anymore 
						status = "up"
					if time.time()- piT2  < max(90.,expirationTime):								   # last signal not in expiration range anymore , use at least 90 secs.. for cars exp is 15 secs and it forgets the last signals too quickly
						distanceToRpi.append([dist , pi1])
				#if dev.id == 169381397: self.ML.myLog( text = "...	  distanceToRpi: status"  + status)


			#if dev.id == 169381397: self.ML.myLog( text = "...	  distanceToRpi:"  + unicode(distanceToRpi) +"	status:"  + status +"  distanceToRpi"+str(distanceToRpi)+ status +"	 expirationTime"+str(expirationTime))
			if self.getCurrentState(dev,devIds,"status", fromMETHOD="calcPostion5") != status:
				#if dev.id == 354285958: self.ML.myLog( text =	u"status change in calcPostion for "+ dev.name+"  from "+self.getCurrentState(dev,devIds,"status")+" to "+ status+"	 for  piTime=" +pitimeNearest  +";	expirationTime="+unicode(expirationTime)+"	time.time()-lastUp="+unicode(time.time()-lastUp) )
				update=True
				self.addToStatesUpdateDict(unicode(dev.id),u"status", status,dev=dev)
				if	(u"note" in dev.states and dev.states[u"note"].find(u"beacon") >-1) or dev.deviceTypeId ==u"BLEconnect":
					if status ==u"up":
						dev.updateStateImageOnServer(indigo.kStateImageSel.SensorOn)
					elif status ==u"down":
						dev.updateStateImageOnServer(indigo.kStateImageSel.SensorOff)
					elif status ==u"expired":
						dev.updateStateImageOnServer(indigo.kStateImageSel.SensorOff)

			distanceToRpi = sorted(distanceToRpi)
			PijjPosition	= []

			if len(distanceToRpi) > 0:
				clostetPi				= distanceToRpi[0][1]
				distanceToClosestRpi	= distanceToRpi[0][0]
				closestRpiPos			= self.piPosition[clostetPi] # set to closest RPI position 
				newPos					= [closestRpiPos[0],closestRpiPos[1],closestRpiPos[2]]					   # set to closest RPI position 
				#if dev.id ==1434599495: self.ML.myLog( text = "	pi0:"+ unicode(clostetPi)+"	 closestRpiPos:"+ unicode(closestRpiPos)+ "	 "+ unicode(distanceToRpi) )
				
				# calculate the direction vector 
				Npoints=0
				if len(distanceToRpi) > 1:
					for jj in range(1, 2): 
						piJJ = distanceToRpi[jj][1]
						if piJJ == clostetPi:							continue # no distance to itself 
						if self.piPosition[piJJ][0]	 <=0:				continue # not set should not be 0 
						if self.piToPiDistance[piJJ][clostetPi][3] ==0: continue # position of RPi are not set or all the same 
						#if dev.id ==1434599495: self.ML.myLog( text = " jj:"+ unicode(jj)+"   pi#:"+unicode(piJJ)+ "  pi-pi0Dist:"+ unicode(self.piToPiDistance[clostetPi][piJJ])+"  dist to thisPI::"+ unicode(distanceToRpi[jj][0])+ ";	newPos:" + unicode(newPos) )
						
						dist =	distanceToClosestRpi 
						if distanceToRpi[jj][0] <  self.piToPiDistance[piJJ][clostetPi][3]:	 # take radius and use direction to next RPI only
							dist   +=  (distanceToClosestRpi /( 1 + 1.2*distanceToRpi[jj][0])) **2	*self.piToPiDistance[piJJ][clostetPi][3]

						xDir  = (self.piToPiDistance[piJJ][clostetPi][0])/self.piToPiDistance[piJJ][clostetPi][3]
						yDir  = (self.piToPiDistance[piJJ][clostetPi][1])/self.piToPiDistance[piJJ][clostetPi][3]
						newPos[0] += xDir * dist 
						newPos[1] += yDir * dist
						#if dev.id ==1434599495: self.ML.myLog( text = "   dist: "+ unicode(dist) +"  xDir:"+ unicode(xDir)+"  yDir:"+ unicode(yDir)+ ";  newPos:" + unicode(newPos))

				#if devID ==78067927: self.ML.myLog( text = "	closestRpiPos:"+ unicode(closestRpiPos)+"	newPosDelta:"+ unicode(newPosDelta)+"	dist2:"+ unicode(dist2)+"	finalPos:"+ unicode(finalPos))
				pos =[u"PosX","PosY","PosZ"]
				for ii in range(3):
					dd = abs(float(dev.states[pos[ii]]) - newPos[ii])
					if dd > 1./self.distanceUnits:	 # min delta = 1 meter
						self.addToStatesUpdateDict(devIds,pos[ii], newPos[ii],decimalPlaces=1,dev=dev)
						deltaDistance +=dd
						#if devID ==354285958: self.ML.myLog( text = " pos changed in state "+pos[ii]+"	 "+str(dd)+"  "+str(deltaDistance)	)
				#if devID ==78067927: self.ML.myLog( text = "	 finalPos:"+ unicode(finalPos))

		except	Exception, e:
			self.ML.myLog( text =  u"calcPostion in Line '%s' has error='%s'" % (sys.exc_traceback.tb_lineno, e))
		return update, deltaDistance



####-------------------------------------------------------------------------####
	def BLEconnectupdateAll(self, pi, sensors):

		for sensor in sensors:
			if sensor == "BLEconnect":
				self.messagesQueueBLE.put(( pi,sensors[sensor]))

		if not self.queueActiveBLE: 
				self.workOnQueueBLE()

####-------------------------------------------------------------------------####
	def workOnQueueBLE(self):

		self.queueActiveBLE	 = True
		while not self.messagesQueueBLE.empty():
			item = self.messagesQueueBLE.get() 
			for ii in range(40):
				if self.queueListBLE ==u"update" : break
				if self.queueListBLE ==u""		 : break
				if ii > 0:	pass#if self.ML.decideMyLog(u"Special"): self.ML.myLog( text =	u"wait for queue to become available in workOnqueue,  ii="+unicode(ii)+u"  "+self.queueList)
				time.sleep(0.05)
			self.queueListBLE = "update"  
			updateFing = self.BLEconnectupdate(item[0],item[1])
			if updateFing: self.updateFING(u"event")

		if len(self.sendBroadCastEventsList) >0: self.sendBroadCastNOW()
		self.messagesQueueBLE.task_done()
		self.queueActiveBLE	 = False
		self.queueListBLE = ""	
		return


####-------------------------------------------------------------------------####
	def BLEconnectupdate(self, pi, info):
		updateBLE = False
		try:
			for devId in info:
				if self.ML.decideMyLog(u"BLE"): self.ML.myLog( text =  u"BLEconnect data: " + unicode(info))
				try:
					dev = indigo.devices[int(devId)]
				except Exception, e:
		
					if unicode(e).find(u"timeout waiting") > -1:
						self.ML.myLog( text =  u"BLEconnectupdate in Line '%s' has error='%s'" % (sys.exc_traceback.tb_lineno, e))
						self.ML.myLog( text =  u"BLEconnectupdate communication to indigo is interrupted")
						return
					self.ML.myLog( text =  u"BLEconnectupdate devId not defined in devices "+unicode(info)+"  sensor="+unicode(sensor))
					continue
				props = dev.pluginProps
				data={}
				for mac in info[devId]:
					if mac.upper() != props[u"macAddress"].upper() : continue
					data= info[devId][mac]
					break
				if data == {}:
					self.ML.myLog( text =  u"mac not found in devices " + unicode(info[devId]))
					continue

				rssi	  = float(data[u"signal"])
				txPowerR  = float(data[u"txPower"])
				if self.ML.decideMyLog(u"BLE"): self.ML.myLog( text = "BLEconnectupdate PI= "+ unicode(pi) +";	mac:"+mac+ "  rssi:"+unicode(rssi)+ "  txPowerR:"+unicode(txPowerR)+ " TxPowerSet:"+unicode(props[u"beaconTxPower"]))
				update2=False

				txPower= min( int(props[u"beaconTxPower"]),txPowerR )
				expirationTime = int(props[u"expirationTime"])

				if dev.states[u"created"] ==u"":
					self.addToStatesUpdateDict(unicode(dev.id),"created", datetime.datetime.now().strftime(_defaultDateStampFormat),dev=dev)

				if str(dev.states[u"Pi_"+unicode(pi)+"_Signal"]) != str(rssi):
					self.addToStatesUpdateDict(unicode(dev.id), u"Pi_"+unicode(pi)+"_Signal",int(rssi),dev=dev )
				if txPowerR !=-999 and	str(dev.states[u"TxPowerReceived"]) != str(txPowerR):
					self.addToStatesUpdateDict(unicode(dev.id), u"TxPowerReceived",txPowerR ,dev=dev )

				if rssi < -160: upD = "down"
				else:			upD = "up"

				if upD==u"up":
					dist=	 round( self.calcDist(	txPower,  min(txPower,rssi)	 ) / self.distanceUnits	 ,1)
					if self.ML.decideMyLog(u"BLE"): self.ML.myLog( text =  u"rssi txP dist distCorrected.. rssi:" + unicode( rssi)+	 " txPower:" + unicode(txPower)+"  dist:"+ unicode(dist) + "  rssiCaped:" + unicode(min(txPower,rssi)))
					self.addToStatesUpdateDict(unicode(dev.id),u"Pi_"+unicode(pi)+"_Time",	datetime.datetime.now().strftime(_defaultDateStampFormat)  ,dev=dev)
					self.addToStatesUpdateDict(unicode(dev.id),"lastUp",datetime.datetime.now().strftime(_defaultDateStampFormat))
				else:
					dist=99999.
					if dev.states[u"status"] == "up":
						self.addToStatesUpdateDict(unicode(dev.id),u"Pi_"+unicode(pi)+"_Time",	datetime.datetime.now().strftime(_defaultDateStampFormat),dev=dev)
				if abs(dev.states[u"Pi_"+unicode(pi)+"_Distance"] - dist) > 0.5 and abs(dev.states[u"Pi_"+unicode(pi)+"_Distance"] - dist)/max(0.5,dist) > 0.05:
					self.addToStatesUpdateDict(unicode(dev.id),u"Pi_" + unicode(pi) + "_Distance", dist,decimalPlaces=1,dev=dev)
				#self.executeUpdateStatesDict()
				update, deltaDistance = self.calcPostion(dev,expirationTime)
				updateBLE = update or updateBLE
				self.executeUpdateStatesDict(onlyDevID=str(dev.id),calledFrom="BLEconnectupdate end")	 
		except	Exception, e:
			if len(unicode(e)) > 5 :
				self.ML.myLog( text =  u"BLEconnectupdate in Line '%s' has error='%s'" % (sys.exc_traceback.tb_lineno, e))
				if unicode(e).find(u"timeout waiting") > -1:
					self.ML.myLog( text =  u"BLEconnectupdate communication to indigo is interrupted")

		return updateBLE



####-------------------------------------------------------------------------####
	def updateSensors(self, pi, sensors):
		data=""
		dateString = datetime.datetime.now().strftime(_defaultDateStampFormat)
		try:
			if self.ML.decideMyLog(u"SensorData"): self.ML.myLog( text =  u"sensor input  pi" + unicode(pi) + "; data " + unicode(sensors))
			# data[u"sensors"][sensor][u"temp,hum,press,INPUT"]

			for sensor in sensors:
				if sensor == "i2cChannels":
					continue  # need to implement test for i2c channel active

				if sensor == "BLEconnect":
					continue
					
				if sensor == "setTEA5767":
					self.updateTEA5767(pi,sensors[sensor],sensor)
					continue
					
				devUpdate = {}
				for devIds in sensors[sensor]:
					devUpdate[devIds] = True
					try:
						try:	devId = int(devIds)
						except: devId = 0
						if devId == 0: continue
						dev= indigo.devices[devId]
						props= dev.pluginProps
					except	Exception, e:
			
						if unicode(e).find(u"timeout waiting") > -1:
							self.ML.myLog( text =  u"updateSensors in Line '%s' has error='%s'" % (sys.exc_traceback.tb_lineno, e))
							self.ML.myLog( text =  u"communication to indigo is interrupted")
							return
						if unicode(e).find(u"not found in database") ==-1:
							self.ML.myLog( text =  u"updateSensors in Line '%s' has error='%s'" % (sys.exc_traceback.tb_lineno, e))
							return

						self.ML.myLog( text =  u"bad devId send from pi:"+ unicode(pi)+ u"	devId: "+devIds+u" deleted?")
						continue

					if not dev.enabled:
						if self.ML.decideMyLog(u"UpdateRPI"): self.ML.myLog( text =	 u"dev not enabled send from pi:"+ unicode(pi)+ u"	dev: "+dev.name)
						continue

					self.saveSensorMessages(devId=devIds, item=u"lastMessage", value=time.time())


					data = sensors[sensor][devIds]
					uData = unicode(data)
					if sensor=="mysensors":
						self.ML.myLog( text =  sensor+" received "+ uData)
						
					if u"calibrating" in uData:
						self.addToStatesUpdateDict(unicode(dev.id),u"status",u"Sensor calibrating",dev=dev)
						try: dev.updateStateImageOnServer(indigo.kStateImageSel.SensorOff)
						except: pass
						continue
						
					if u"badSensor" in uData:
						self.addToStatesUpdateDict(unicode(dev.id),u"status",u"bad Sensor data, disconnected?",dev=dev)
						try: dev.updateStateImageOnServer(indigo.kStateImageSel.PowerOff)
						except: pass
						continue

					if u"displayS" in props:
						whichKeysToDisplay = props[u"displayS"]
					else:
						whichKeysToDisplay = ""

					if sensor == u"i2cTCS34725" :
						self.updateRGB(dev, data, whichKeysToDisplay)
						continue
						
					elif dev.deviceTypeId == "as726x":
						if "green" in data:
							data["illuminance"] = float(data["green"])*6.83
						self.updateRGB(dev, data, whichKeysToDisplay, dispType=4)
						if u"temp" in data:
							x, UI, decimalPlaces  = self.convTemp(data["temp"])
							self.addToStatesUpdateDict(unicode(dev.id),u"temperature", x, decimalPlaces=decimalPlaces,dev=dev)
						if u"LEDcurrent" in data:
							self.addToStatesUpdateDict(unicode(dev.id),u"LEDcurrent", data["LEDcurrent"], decimalPlaces=1,dev=dev)
						continue
						
					elif sensor == u"i2cVEML6070" :
						self.updateLight(dev, data, whichKeysToDisplay)
						continue

					elif sensor == u"i2cVEML6075" :
						self.updateLight(dev, data, whichKeysToDisplay)
						continue

					elif sensor == u"i2cVEML6040" :
						self.updateLight(dev, data, whichKeysToDisplay,theType=sensor)
						continue

					elif sensor == u"i2cVEML7700" :
						self.updateLight(dev, data, whichKeysToDisplay,theType=sensor)
						continue

					elif sensor == u"i2cVEML6030" :
						self.updateLight(dev, data, whichKeysToDisplay)
						continue

					elif sensor == u"i2cTSL2561" :
						self.updateLight(dev, data, whichKeysToDisplay)
						continue
						
					elif sensor == u"i2cIS1145" :
						self.updateLight(dev, data, whichKeysToDisplay)
						continue
						
					elif sensor == u"i2cOPT3001" :
						self.updateLight(dev, data, whichKeysToDisplay, theType=sensor)
						continue
						
					elif sensor == u"ultrasoundDistance" :
						self.updateDistance(dev, data, whichKeysToDisplay)
						continue
						
					elif sensor == u"vl503l0xDistance" :
						self.updateDistance(dev, data, whichKeysToDisplay)
						continue
						
					elif sensor == u"vl6180xDistance" :
						self.updateDistance(dev, data, whichKeysToDisplay)
						self.updateLight(dev, data, whichKeysToDisplay)
						continue
						
					elif sensor == u"vcnl4010Distance" :
						self.updateDistance(dev, data, whichKeysToDisplay)
						self.updateLight(dev, data, whichKeysToDisplay)
						continue

					elif sensor == u"apds9960" :
						self.updateapds9960(dev, data)
						continue

					elif sensor.find(u"INPUTgpio-") >-1:
						self.updateINPUT(dev, data, whichKeysToDisplay, int(sensor.split("INPUTgpio-")[1]), sensor)
						continue

					elif sensor.find(u"INPUTtouch-") >-1:
						self.updateINPUT(dev, data, whichKeysToDisplay, int(sensor.split("INPUTtouch-")[1]), sensor)
						continue

					elif sensor.find(u"INPUTtouch12-") >-1:
						self.updateINPUT(dev, data, whichKeysToDisplay, int(sensor.split("INPUTtouch12-")[1]), sensor)
						continue

					elif sensor.find(u"INPUTtouch16-") >-1:
						self.updateINPUT(dev, data, whichKeysToDisplay, int(sensor.split("INPUTtouch16-")[1]), sensor)
						continue

					elif sensor == u"spiMCP3008" :
						self.updateINPUT(dev, data, whichKeysToDisplay,	 8, sensor)
						continue
						
					elif sensor == u"spiMCP3008-1" :
						self.updateINPUT(dev, data, u"INPUT_0",	 1, sensor)
						continue

					elif sensor == u"i2cADS1x15-1" :
						self.updateINPUT(dev, data, whichKeysToDisplay, 1, sensor)
						continue
					elif sensor == u"i2cADS1x15" :
						self.updateINPUT(dev, data, whichKeysToDisplay, 4, sensor)
						continue

					elif sensor == u"i2cPCF8591" :
						self.updateINPUT(dev, data, whichKeysToDisplay,	 4, sensor)
						continue
						
					elif sensor == u"i2cPCF8591-1" :
						self.updateINPUT(dev, data, u"INPUT_0",	 1, sensor)
						continue
						
					elif sensor == u"mysensors" :
						self.ML.myLog( text = sensor+"	into input")
						self.updateINPUT(dev, data, whichKeysToDisplay, 10, sensor)
						continue
						
					elif sensor == u"myprogram" :
						self.updateINPUT(dev, data, whichKeysToDisplay, 10, sensor)
						continue
						
					elif dev.deviceTypeId == "Wire18B20":
						self.updateOneWire(dev,data,whichKeysToDisplay,pi)
						continue
						
					elif dev.deviceTypeId == "BLEsensor":
						self.updateBLEsensor(dev,data,whichKeysToDisplay,pi)
						continue
						
					elif dev.deviceTypeId == "ina219":
						self.updateina219(dev,data,whichKeysToDisplay)
						continue
						
					elif dev.deviceTypeId == "ina3221":
						self.updateina3221(dev,data,whichKeysToDisplay)
						continue
						
					elif dev.deviceTypeId == "i2cADC121":
						self.updateADC121(dev,data,whichKeysToDisplay)
						continue
						
					elif dev.deviceTypeId == "l3g4200":
						self.updateGYROS(dev,data,whichKeysToDisplay)
						continue

					elif dev.deviceTypeId == "bno055":
						self.updateGYROS(dev,data,whichKeysToDisplay)
						continue
						
					elif dev.deviceTypeId == "mag3110":
						self.updateGYROS(dev,data,whichKeysToDisplay)
						continue
						
					elif dev.deviceTypeId == "hmc5883L":
						self.updateGYROS(dev,data,whichKeysToDisplay)
						continue

					elif dev.deviceTypeId == "mpu6050":
						self.updateGYROS(dev,data,whichKeysToDisplay)
						continue

					elif dev.deviceTypeId == "mpu9255":
						self.updateGYROS(dev,data,whichKeysToDisplay)
						continue

					elif dev.deviceTypeId == "lsm303":
						self.updateGYROS(dev,data,whichKeysToDisplay)
						continue

					elif dev.deviceTypeId == "INPUTpulse":
						self.updatePULSE(dev,data,whichKeysToDisplay)
						continue


					if sensor =="rainSensorRG11":
						self.updaterainSensorRG11(dev,data,whichKeysToDisplay)
						continue


					if sensor =="pmairquality":
						self.updatePMAIRQUALITY(dev,data,whichKeysToDisplay)
						continue
					if sensor =="launchpgm":
						st = data[u"status"]
						self.addToStatesUpdateDict(unicode(dev.id), "status", st,dev=dev)
						if st == "running": 
							dev.updateStateImageOnServer(indigo.kStateImageSel.SensorOn)
						elif st =="not running": 
							dev.updateStateImageOnServer(indigo.kStateImageSel.SensorOff)
						elif st =="not checked": 
							dev.updateStateImageOnServer(indigo.kStateImageSel.SensorTripped)
						continue
						
					newStatus = dev.states[u"status"]

					if sensor in [u"sgp30",u"ccs811"]:
						try:
							x, UI  = int(float(data[u"CO2"])),	 "CO2 %d[ppm] "%(float(data[u"CO2"]))
							newStatus = self.setStatusCol( dev, u"CO2", x, UI, whichKeysToDisplay, indigo.kStateImageSel.TemperatureSensorOn,newStatus, decimalPlaces = 1)
							x, UI  = int(float(data[u"VOC"])),	 " VOC %d[ppb]"%(float(data[u"VOC"]))
							newStatus = self.setStatusCol( dev, u"VOC", x, UI, whichKeysToDisplay, indigo.kStateImageSel.TemperatureSensorOn,newStatus, decimalPlaces = 1)
						except	Exception, e:
							self.ML.myLog( text =  u"updateSensors in Line '%s' has error='%s'" % (sys.exc_traceback.tb_lineno, e))
							self.ML.myLog( text =  unicode(props))
						

					if sensor == "as3935":
						try:
							if data[u"eventType"]  == "no Action yet":
								 self.addToStatesUpdateDict(unicode(dev.id),"eventType", "no Data", dev=dev) 
							elif data[u"eventType"]	 == "no lightning today":
								 self.addToStatesUpdateDict(unicode(dev.id),"eventType", "no lightning today", dev=dev) 
							elif data[u"eventType"]	 == "measurement":
								self.addToStatesUpdateDict(unicode(dev.id),"eventType", "measurement", dev=dev) 
								if data[u"lightning"]  == "lightning detected":
									x, UI  = int(float(data[u"distance"])),	  "Distance %d[km] "%(float(data[u"distance"]))
									newStatus = self.setStatusCol( dev, u"distance", x, UI, whichKeysToDisplay, indigo.kStateImageSel.TemperatureSensorOn,newStatus, decimalPlaces = 0)
									self.addToStatesUpdateDict(unicode(dev.id),"energy", float(data[u"energy"]), dev=dev) 
									newStatus = self.setStatusCol( dev, u"lightning", data[u"lightning"], "lightning "+datetime.datetime.now().strftime("%m-%d %H:%M:%S"), whichKeysToDisplay, indigo.kStateImageSel.TemperatureSensorOn,newStatus)
									self.addToStatesUpdateDict(unicode(dev.id),"lastLightning", datetime.datetime.now().strftime(_defaultDateStampFormat), dev=dev) 
									rightNow = time.time()
									nDevs = 1
									#indigo.server.log("  checking devL for "+ dev.name )
									for devL in indigo.devices.iter("props.isLightningDevice"):
										if devL.id == dev.id: continue
										lastLightning = devL.states["lastLightning"]
										try:	deltaTime = (datetime.datetime.now() - datetime.datetime.strptime(lastLightning, "%Y-%m-%d %H:%M:%S")).total_seconds()
										except: continue
										if deltaTime < self.lightningTimeWindow : 
											nDevs += 1
										#indigo.server.log(" deltaTime: "+ str(deltaTime))
									if nDevs >= self.lightningNumerOfSensors:
										indigo.variable.updateValue("lightningEventDevices",str(nDevs))
										time.sleep(0.01) # make shure the # of devs gets updated first
										indigo.variable.updateValue("lightningEventDate",datetime.datetime.now().strftime(_defaultDateStampFormat))
										
								elif data[u"lightning"].find("Noise") == 0: 
									 self.addToStatesUpdateDict(unicode(dev.id),"lightning", "calibrating,- sensitivity ", dev=dev) 
								elif data[u"lightning"].find("Disturber") == 0: 
									 self.addToStatesUpdateDict(unicode(dev.id),"lightning", "calibrating,- Disturber event ", dev=dev) 
						except	Exception, e:
							self.ML.myLog( text =  u"updateSensors in Line '%s' has error='%s'" % (sys.exc_traceback.tb_lineno, e))
							self.ML.myLog( text =  unicode(props) +"\n"+ unicode(data))
						continue


					if sensor in["mhz-I2C","mhz-SERIAL"]:
						try:
							x, UI  = int(float(data[u"CO2"])),	 "CO2 %d[ppm] "%(float(data[u"CO2"]))
							newStatus = self.setStatusCol( dev, u"CO2", x, UI, whichKeysToDisplay, indigo.kStateImageSel.TemperatureSensorOn,newStatus, decimalPlaces = 1)
							if abs( float(dev.states["CO2offset"]) - float(data[u"CO2offset"])	) > 1: 
								self.setONErPiV(pi,"piUpToDate", [u"updateParamsFTP"])
							self.addToStatesUpdateDict(unicode(dev.id),"calibration", data[u"calibration"],	  dev=dev) 
							self.addToStatesUpdateDict(unicode(dev.id),"raw", float(data[u"raw"]),	decimalPlaces = 1, dev=dev) 
							self.addToStatesUpdateDict(unicode(dev.id),"CO2offset", float(data[u"CO2offset"]),	decimalPlaces = 1, dev=dev) 
						except	Exception, e:
							self.ML.myLog( text =  u"updateSensors in Line '%s' has error='%s'" % (sys.exc_traceback.tb_lineno, e))
							self.ML.myLog( text =  unicode(props))
						continue


					if u"hum" in data:
						hum= data[u"hum"]
						x, UI, decimalPlaces  = self.convHum(hum)
						newStatus = self.setStatusCol( dev, u"Humidity", x, UI, whichKeysToDisplay, indigo.kStateImageSel.HumiditySensor,newStatus, decimalPlaces = decimalPlaces )

						
					if u"temp" in data:
						temp = data[u"temp"]
						x, UI, decimalPlaces = self.convTemp(temp)
						newStatus = self.setStatusCol( dev, u"Temperature", x, UI, whichKeysToDisplay, indigo.kStateImageSel.TemperatureSensorOn,newStatus, decimalPlaces = decimalPlaces )

					if u"AmbientTemperature" in data:
						temp = data[u"AmbientTemperature"]
						x, UI, decimalPlaces  = self.convTemp(temp)
						newStatus = self.setStatusCol( dev, u"AmbientTemperature", x, UI, whichKeysToDisplay, indigo.kStateImageSel.TemperatureSensorOn,newStatus, decimalPlaces = decimalPlaces)

					if u"MovementAbs" in data:
						try:
							x, UI  = float(data[u"MovementAbs"]),	"%5.2f"%(float(data[u"MovementAbs"]))
							newStatus = self.setStatusCol( dev, u"MovementAbs", x, UI, whichKeysToDisplay, indigo.kStateImageSel.TemperatureSensorOn,newStatus, decimalPlaces = 2)
						except: pass

					if u"Movement" in data:
						try:
							x, UI  = float(data[u"Movement"]),	 "%5.2f"%(float(data[u"Movement"]))
							newStatus = self.setStatusCol( dev, u"Movement", x, UI, whichKeysToDisplay, indigo.kStateImageSel.TemperatureSensorOn,newStatus, decimalPlaces = 2)
						except: pass
					if u"Uniformity" in data:
						try:
							x, UI  = float(data[u"Uniformity"]),   "%5.1f"%(float(data[u"Uniformity"]))
							newStatus = self.setStatusCol( dev, u"Uniformity", x, UI, whichKeysToDisplay, indigo.kStateImageSel.TemperatureSensorOn,newStatus, decimalPlaces = 1)
						except: pass

					if sensor == u"amg88xx" and u"rawData" in data :
						try:
							if ("imageFilesaveRawData" in props and props["imageFilesaveRawData"] =="1") or ("imageFileNumberOfDots" in props and props["imageFileNumberOfDots"] !="-"):
								# exapnd to 8x8 matrix, data is in 4 byte packages *100
								pixPerRow = 8
								dataRaw = json.loads(data[u"rawData"])
								dataRaw = json.dumps([[dataRaw[kkkx] for kkkx in range(pixPerRow*(iiix), pixPerRow*(iiix+1))] for iiix in range(pixPerRow)])

								if "imageFilesaveRawData" in props and props["imageFilesaveRawData"] =="1":
										newStatus = self.setStatusCol( dev, u"rawData", dataRaw,"", whichKeysToDisplay, indigo.kStateImageSel.TemperatureSensorOn,newStatus, decimalPlaces = "")
								if "imageFileNumberOfDots" in props and props["imageFileNumberOfDots"] !="-":
									if "imageFileName" in props and len(props["imageFileName"])>1:
										imageParams	  = json.dumps( {"logLevel":props["imageFilelogLevel"],"compress":props["imageFileCompress"],"fileName":self.cameraImagesDir+props["imageFileName"],"numberOfDots":props["imageFileNumberOfDots"],"dynamic":props["imageFileDynamic"],"colorBar":props["imageFileColorBar"]} )
										cmd = self.pythonPath + u" '" + self.pathToPlugin + u"makeCameraPlot.py' '" +imageParams+"' '"+dataRaw+"' & "  
										os.system(cmd)
						except	Exception, e:
							self.ML.myLog( text =  u"updateSensors in Line '%s' has error='%s'" % (sys.exc_traceback.tb_lineno, e))
							self.ML.myLog( text =  unicode(props))
							self.ML.myLog( text =  unicode(len(data[u"rawData"]))+"	 "+data[u"rawData"])

					if u"Vertical" in data:
						try:
							x, UI  = float(data[u"Vertical"]),	 "%7.3f"%(float(data[u"Vertical"]))
							newStatus = self.setStatusCol( dev, u"VerticalMovement", x, UI, whichKeysToDisplay, indigo.kStateImageSel.TemperatureSensorOn,newStatus, decimalPlaces = 3)
						except: pass

					if u"Horizontal" in data:
						try:
							x, UI  = float(data[u"Horizontal"]),   "%7.3f"%(float(data[u"Horizontal"]))
							newStatus = self.setStatusCol( dev, u"HorizontalMovement", x, UI, whichKeysToDisplay, indigo.kStateImageSel.TemperatureSensorOn,newStatus, decimalPlaces = 3)
						except: pass

					if u"MinimumPixel" in data:
						x, UI, decimalPlaces  = self.convTemp(data[u"MinimumPixel"])
						newStatus = self.setStatusCol( dev, u"MinimumPixel", x, UI, whichKeysToDisplay, indigo.kStateImageSel.TemperatureSensorOn,newStatus, decimalPlaces = decimalPlaces)

					if u"MaximumPixel" in data:
						x, UI, decimalPlaces  = self.convTemp(data[u"MaximumPixel"])
						newStatus = self.setStatusCol( dev, u"MaximumPixel", x, UI, whichKeysToDisplay, indigo.kStateImageSel.TemperatureSensorOn,newStatus, decimalPlaces = decimalPlaces)

					if u"GasResistance" in data:
						gr,grUI, aq, aqUI, gb, gbUI = self.convGas(	 [ data[u"GasResistance"], data[u"AirQuality"], data[u"GasBaseline"] ]	)
						newStatus = self.setStatusCol( dev, u"GasResistance", gr, grUI, whichKeysToDisplay, indigo.kStateImageSel.TemperatureSensorOn,newStatus, decimalPlaces = 0)
						newStatus = self.setStatusCol( dev, u"AirQuality",	  aq, aqUI, whichKeysToDisplay, indigo.kStateImageSel.TemperatureSensorOn,newStatus, decimalPlaces = 0)
						newStatus = self.setStatusCol( dev, u"GasBaseline",	  gb, gbUI, whichKeysToDisplay, indigo.kStateImageSel.TemperatureSensorOn,newStatus, decimalPlaces = 0)


					newStatus = self.setPressureDisplay(dev,data,whichKeysToDisplay,newStatus)
				

				for devIds in devUpdate:
					if devIds in self.updateStatesDict:
						if self.ML.decideMyLog(u"SensorData"): self.ML.myLog( text =  u"pi# "+unicode(pi) + "  " + unicode(devIds)+"  "+unicode(self.updateStatesDict))
						self.executeUpdateStatesDict(onlyDevID=devIds,calledFrom="updateSensors end")
			self.saveSensorMessages(devId="")

		except	Exception, e:
			if len(unicode(e)) > 5 :
				if self.ML.decideMyLog(u"SensorData"): self.ML.myLog( text =  u"updateSensors in Line '%s' has error='%s'" % (sys.exc_traceback.tb_lineno, e))
				if self.ML.decideMyLog(u"SensorData"): self.ML.myLog( text =  u"pi# "+unicode(pi) + "  " + unicode(sensors))

		return

####-------------------------------------------------------------------------####
	def updaterainSensorRG11(self, dev, data, whichKeysToDisplay):
		try:
			props = dev.pluginProps
			if "lastUpdate" not in props or props["lastUpdate"]=="0":
				props["lastUpdate"] = time.time()
			dd = datetime.datetime.now().strftime(_defaultDateStampFormat)
			updateDev = False
			##indigo.server.log(unicode(data))
			rainChanges = []
			if len(dev.states["resetDate"]) < 5:
				rainChanges.append(["resetDate", dd, dd,""])
				#self.addToStatesUpdateDict(unicode(dev.id), "resetDate", datetime.datetime.now().strftime(_defaultDateStampFormat),dev=dev)

			if	 self.rainUnits == "inch":	   mult = 1/25.4	; unit = "in"
			elif self.rainUnits == "cm":	   mult = 0.1 		; unit = "cm"
			else:                              mult = 1 		; unit = "mm"
			
			if "format" in props and len(props["format"])<2: form = "%."+str(self.rainDigits+1)+"f["+self.rainUnits+"]"
			else:											 form = props["format"]
			
			for cc in ["totalRain", "rainRate", "measurementTime", "mode", "rainLevel", "sensitivity","nBuckets","nBucketsTotal","bucketSize"]:
				if cc in data:
					
					if cc =="totalRain":
						x = float(data[cc])*mult	 # is in mm 
						rainChanges.append([cc, x, form%x, self.rainDigits])
						#self.addToStatesUpdateDict(unicode(dev.id),cc, x,	decimalPlaces = self.rainDigits, dev=dev) 
						for zz in ["hourRain","dayRain","weekRain","monthRain","yearRain"]:
							#indigo.server.log(" testing: "+zz)
							zzP= zz+"Total"
							if zzP in props:
								oldV = float(props[zzP])
								#indigo.server.log(" ok: "+zzP+"  old: "+ str(oldV)+"  new: "+ str(x) )
								if oldV > x:
									props[zzP] = x
									updateDev = True
									oldV = x
								rainChanges.append([zz, x-oldV, unicode(x-oldV), self.rainDigits])


					elif cc == "rainRate":
						x = float(data[cc])*mult	 # is in mm 
						rainChanges.append([cc, x, form%x, self.rainDigits+1])
						self.fillMinMaxSensors(dev,"rainRate",x,self.rainDigits)
						if "rainTextMap" in props:
							rtm	 = props["rainTextMap"].split(";")
							lowerLimit =[]
							rainText =[]
							for nn in range(len(rtm)):
								item = rtm[nn].split(":")
								if len(item) !=2: continue
								try: 
									limit = float(item[0])
									if x <= limit or nn+1 == len(rtm) :
										rainChanges.append([u"rainText", item[1],unicode(item[1]),""])
										break
								except: pass
								
					elif cc == "measurementTime":
						x = data[cc]
						rainChanges.append([cc, int(x), unicode(int(x)),""])
						#self.addToStatesUpdateDict(unicode(dev.id),cc, x,	decimalPlaces = 1, dev=dev) 

					elif cc == "rainLevel":
						try: x = int(data[cc])
						except: x = 0
						labels = (props["rainMsgMap"]).split(";")
						if x in [0,1,2,3,4]:
							if x >1: 
								rainChanges.append(["lastRain",dd,dd,""])
							if len(labels) > x:
								rainChanges.append([cc, labels[x],labels[x],""])
								if whichKeysToDisplay == cc: 
									rainChanges.append([u"status", labels[x], labels[x],""])
									#self.addToStatesUpdateDict(unicode(dev.id),u"status", labels[x],dev=dev) 
					elif cc == "nBuckets":
						try: x = int(data[cc])
						except: x = 0
						rainChanges.append([cc, int(x),unicode(int(x)),""])
					elif cc == "nBucketsTotal":
						try: x = int(data[cc])
						except: x = 0
						rainChanges.append([cc, int(x),unicode(int(x)),""])
					elif cc == "bucketSize":
						try: 
							xx = "0["+unit+"]"
							x = float(data[cc])*mult
							if x > 0:  xx = "%.2f"%x+"["+unit+"]"
						except: pass 
						rainChanges.append([cc, x,xx, 4])
					else:
						x = data[cc]
						rainChanges.append([cc, x,unicode(x),""])
						##indigo.server.log(cc+"  "+unicode(x))
			if len(rainChanges)>0:
				if time.time() - props["lastUpdate"] > 900:	  # force update every 15 minutes
					ff = True
					props["lastUpdate"] = time.time()
					updateDev = True
				else:
					ff = False
				for xx in rainChanges:
					self.setStatusCol( dev, xx[0], xx[1], xx[2], whichKeysToDisplay, indigo.kStateImageSel.TemperatureSensorOn,"", decimalPlaces =xx[3], force = ff)
			if updateDev: 
				dev.replacePluginPropsOnServer(props)

		except	Exception, e:
			self.ML.myLog( text =  u"updateSensors in Line '%s' has error='%s'" % (sys.exc_traceback.tb_lineno, e))
			self.ML.myLog( text =  unicode(data))
		return



####-------------------------------------------------------------------------####
	def updatePMAIRQUALITY(self, dev, data, whichKeysToDisplay):
		try:
			for cc in ["pm10_standard","pm25_standard","pm100_standard", "pm10_env","pm25_env","pm100_env","particles_03um","particles_05um","particles_10um","particles_25um","particles_50um","particles_100um"]:
				if cc in data:
					if cc.find("pm") >-1: units = "ug/m3"
					else:				  units = "C/0.1L"
					x, UI  = int(float(data[cc])),	 cc+"=%d["%(int(float(data[cc])))+units+"]"
					
					self.setStatusCol(dev,cc,x,UI,whichKeysToDisplay,"","",decimalPlaces=0)

					if cc == "pm25_standard":
						if	  x < 12:		airQuality = "Good"
						elif  x < 35.4:		airQuality = "Moderate" 
						elif  x < 55.4:		airQuality = "Unhealthy Sensitve" 
						elif  x < 150.4:	airQuality = "Unhealthy" 
						elif  x < 250.4:	airQuality = "Very Unhealthy" 
						else:				airQuality = "Hazardous"
						

						self.setStatusCol(dev,u"airQuality",airQuality,"Air Quality is "+airQuality,whichKeysToDisplay,"","",decimalPlaces=1)

						if	 airQuality == "Good":		 dev.updateStateImageOnServer(indigo.kStateImageSel.SensorOn)
						elif airQuality == "Moderate":	 dev.updateStateImageOnServer(indigo.kStateImageSel.SensorOff)
						else:							 dev.updateStateImageOnServer(indigo.kStateImageSel.SensorTripped)

		except	Exception, e:
			self.ML.myLog( text =  u"updateSensors in Line '%s' has error='%s'" % (sys.exc_traceback.tb_lineno, e))
			self.ML.myLog( text =  unicode(data))
		return



####-------------------------------------------------------------------------####
	def setPressureDisplay(self,dev,data,whichKeysToDisplay,newStatus):
		try:
			if u"press" in data:
				p = float(data[u"press"])
				decimalPlaces = 1

				if self.pressureUnits == "atm":
					p *= 0.000009869233; pu = (u"%6.3f" % p + u" atm");			  decimalPlaces =4
				elif self.pressureUnits == "bar":
					p *= 0.00001; pu = (u"%6.3f" % p + u" Bar");				  decimalPlaces =4
				elif self.pressureUnits == "mbar":
					p *= 0.01; pu = (u"%6.1f" % p + u" mBar");					  decimalPlaces =1
				elif self.pressureUnits == "mm":
					p *= 0.00750063; pu = (u"%6d" % p + u' mmHg');				  decimalPlaces =0
				elif self.pressureUnits == "Torr":
					p *= 0.00750063; pu = (u"%6d" % p + u" Torr") ;				  decimalPlaces =0
				elif self.pressureUnits == "inches":
					 p *= 0.000295299802; pu = (u"%6.2f" % p + u' "Hg') ;		  decimalPlaces =2
				elif self.pressureUnits == "PSI":
					p *= 0.000145038; pu = (u"%6.2f" % p + u" PSI");			  decimalPlaces =2
				elif self.pressureUnits == "hPascal":
					p *=0.01; pu = (u"%6d" % p + u" hPa");						  decimalPlaces =0 
				else:
					pu = (u"%9d" % p + u' Pa').strip()
				pu = pu.strip()
				newStatus = self.setStatusCol(dev, u"Pressure", p, pu, whichKeysToDisplay, u"",newStatus, decimalPlaces = decimalPlaces)
		except	Exception, e:
			if len(unicode(e)) > 5 :
				self.ML.myLog( text =  u"setPressureDisplay in Line '%s' has error='%s'" % (sys.exc_traceback.tb_lineno, e))
		return newStatus


####-------------------------------------------------------------------------####
	def setStatusCol(self,dev,key,value,valueUI,whichKeysToDisplay,image,oldStatus,decimalPlaces=1,force=False):
		try:
			newStatus = oldStatus
			if whichKeysToDisplay !="":
				whichKeysToDisplayList = whichKeysToDisplay.split(u"/")
				whichKeysToDisplaylength = len(whichKeysToDisplayList)
				currentDisplay = oldStatus.split(u"/")
				if len(currentDisplay) != whichKeysToDisplaylength: # reset? display selection changed?
					currentDisplay = whichKeysToDisplay.split(u"/")

			if unicode(dev.states[key]) != unicode(value):
				self.addToStatesUpdateDict(unicode(dev.id), key, value,decimalPlaces=decimalPlaces,dev=dev,force=force)
				self.fillMinMaxSensors(dev,key,value,decimalPlaces=decimalPlaces)

			#if dev.name =="s-3-rainSensorRG11": indigo.server.log(dev.name+"  in setStatusCol "+key+"  "+str(value)+"   "+str(valueUI))

			if whichKeysToDisplay !="":
				for i in range(whichKeysToDisplaylength):
					if whichKeysToDisplayList[i] == key:
						#if dev.name =="s-3-rainSensorRG11": indigo.server.log(dev.name+"  in after  whichKeysToDisplayList")
						if currentDisplay[i] != valueUI:
							if i==0:
								if image != "":
									dev.updateStateImageOnServer(image)
							currentDisplay[i] = valueUI		   
							newStatus= "/".join(currentDisplay)
							#if dev.name =="s-3-rainSensorRG11": indigo.server.log(dev.name+"  in bf   sensorValue  states:"+unicode(dev.states))
							if "sensorValue" in dev.states:
								#if dev.name =="s-3-rainSensorRG11": indigo.server.log(dev.name+" af sensorValue")
								
								# make a very small random number must not be same, otehr no update if it is not a number 
								try: 	x = float(value)
								except:
									tt = time.time()
									x = (tt - int(tt))/10000000000000.
									decimalPlaces =""
									##indigo.server.log(dev.name+"  setStatusCol key:"+key+"  value:"+str(value) +"  x:"+str(x)+"  decimalPlaces:"+str(decimalPlaces))
								#if dev.name =="s-3-rainSensorRG11": indigo.server.log(dev.name+"  "+key+"  "+str(value)+"   "+str(x)+"  "+valueUI)
								if decimalPlaces !="":
									self.addToStatesUpdateDict(unicode(dev.id),u"sensorValue", round(x,decimalPlaces), decimalPlaces=decimalPlaces, dev=dev, uiValue=newStatus,force=force)
								else:
									self.addToStatesUpdateDict(unicode(dev.id),u"sensorValue", x, dev=dev, uiValue=newStatus,force=force)
							self.addToStatesUpdateDict(unicode(dev.id),u"status", newStatus,dev=dev,force=force)
							break


		except	Exception, e:
			if len(unicode(e)) > 5 :##
				self.ML.myLog( text =  u"setStatusCol in Line '%s' has error='%s'" % (sys.exc_traceback.tb_lineno, e))
		return newStatus
		
 
####-------------------------------------------------------------------------####
	def updateOneWire(self,dev,data,whichKeysToDisplay,pi):
	
		## add check for addNewOneWireSensors only add new one if TRUE 
		## format:
		#"sensors":{"Wire18B20":{
		#"1565508294":{"temp":[{"28-0316b5fa44ff":"24.3"}]},
		#"1447141059":{"temp":[{"28-0516b332fbff":"24.8"}]},
		#"416059968": {"temp":[{"28-800000035de5":"21.8"},	{"28-0416b39944ff":"24.6"}]},  ## can be multiple 
		#"1874530568":{"temp":[{"28-0516b33621ff":"24.6"}]}}}
		## 
		try:
			#indigo.server.log("====== DATA	 "+ dev.name+"	"+unicode(data[u"temp"]) )
			for NNN in data[u"temp"]:
				#indigo.server.log(" NNN  "+ unicode(NNN) )
				if not isinstance(NNN, type({})): 
					#indigo.server.log(" NNN not dict  ")
					continue ## old format , skip ; must be list
				#indigo.server.log(" NNN passed as dict	 "+ unicode(NNN) )
				for serialNumber in NNN:
					temp = NNN[serialNumber]
					if temp == "85.0":	temp = "999.9"
					x, UI, decimalPlaces  = self.convTemp(temp)
					#indigo.server.log(" temp  "+ unicode(temp)+"  "+ unicode(serialNumber) )
					if dev.states[u"serialNumber"] == "" or	 dev.states[u"serialNumber"] == serialNumber: # ==u"" new, ==Serial# already setup
						if dev.states[u"serialNumber"] == "": 
							self.addToStatesUpdateDict(unicode(dev.id),"serialNumber",serialNumber,dev=dev)
							self.setONErPiV(pi,"piUpToDate", [u"updateParamsFTP"])
						if serialNumber != u"sN= " + dev.description:
							if dev.description.find("sN= ") == 0:
								snOld =	 dev.description.split(" ")
								addtext =""
								if len(snOld) >2: addtext= " "+ " ".join(snOld[2:])
								if snOld[1] != serialNumber:
									dev.description = u"sN= " + serialNumber +addtext
									dev.replaceOnServer()
							else:
								dev.description = u"sN= " + serialNumber 
								dev.replaceOnServer()

						self.setStatusCol( dev, u"Temperature", x, UI, whichKeysToDisplay, indigo.kStateImageSel.TemperatureSensorOn,dev.states[u"status"], decimalPlaces = decimalPlaces )
						
					else: # try to somewhere else
						#indigo.server.log("  not present, checking other " )
						foundSelf	= False
						for dev0 in indigo.devices.iter("props.isSensorDevice"):
							if dev0.deviceTypeId != "Wire18B20": continue
							if dev0.name == dev.name: continue
							if dev0.states[u"serialNumber"] == serialNumber: 
								#indigo.server.log("  found serial number " +dev0.name +"  "+ serialNumber	)
								foundSelf =True
								self.setStatusCol( dev0, u"Temperature", x, UI, whichKeysToDisplay, indigo.kStateImageSel.TemperatureSensorOn,dev0.states[u"status"],decimalPlaces = decimalPlaces )
								if serialNumber != u"sN= " + dev0.description:
									dev0.description = u"sN= " + serialNumber
									dev0.replaceOnServer()
								break
						if not foundSelf : # really not setup
							try:
								props = indigo.devices[int(self.RPI[unicode(pi)]["piDevId"])].pluginProps
								if "addNewOneWireSensors" in props and props["addNewOneWireSensors"] == "1":
									#indigo.server.log(" not found	")
									dev1 = indigo.device.create(
											protocol		= indigo.kProtocol.Plugin,
											address			= "Pi-"+unicode(pi),
											name			= dev.name+"_"+serialNumber,
											pluginId		= self.pluginId,
											deviceTypeId	= "Wire18B20",
											folder			= self.piFolderId,
											description		= u"sN= " + serialNumber,
											props			= {u"piServerNumber":unicode(pi), "displayState":"status", "displayS":"Temperature", "offsetTemp":"0",  u"displayEnable": u"0", "isSensorDevice":True,
																"SupportsSensorValue":True, "SupportsOnState":False, "AllowSensorValueChange":False, "AllowOnStateChange":False, "SupportsStatusRequest":False}
											)
									
									if "input"	   not in self.RPI[unicode(pi)]			 : self.RPI[unicode(pi)]["input"] ={}
									if "Wire18B20" not in self.RPI[unicode(pi)]["input"] : self.RPI[unicode(pi)]["input"]["Wire18B20"] ={}
									self.RPI[unicode(pi)]["input"]["Wire18B20"][str(dev1.id)] = ""
									self.addToStatesUpdateDict(unicode(dev1.id),"serialNumber",serialNumber,dev=dev1)
									self.setStatusCol( dev1, u"Temperature", x, UI, whichKeysToDisplay, indigo.kStateImageSel.TemperatureSensorOn,dev1.states[u"status"], decimalPlaces = decimalPlaces )
									self.executeUpdateStatesDict(onlyDevID=str(dev1.id),calledFrom="updateOneWire")
									self.setONErPiV(pi,"piUpToDate", [u"updateParamsFTP"])
									self.saveConfig()
							except	Exception, e:
								self.ML.myLog( text =  u"updateOneWire in Line '%s' has error='%s'" % (sys.exc_traceback.tb_lineno, e))
								continue

		except	Exception, e:
				self.ML.myLog( text =  u"updateOneWire in Line '%s' has error='%s'" % (sys.exc_traceback.tb_lineno, e))
 #28-0316b5db4bff


 
####-------------------------------------------------------------------------####
	def updateBLEsensor(self,dev,data,whichKeysToDisplay,pi):
		try:
			x, UI, decimalPlaces  = self.convTemp(data[u"temp"])
			self.addToStatesUpdateDict(unicode(dev.id),"TxPower",data[u"txPower"],dev=dev)
			self.addToStatesUpdateDict(unicode(dev.id),"rssi"	,data[u"rssi"])
			self.addToStatesUpdateDict(unicode(dev.id),"UUID"	,data[u"UUID"])
			self.setStatusCol( dev, u"Temperature", x, UI, whichKeysToDisplay, indigo.kStateImageSel.TemperatureSensorOn,dev.states[u"status"], decimalPlaces = decimalPlaces )
		except	Exception, e:
			if len(unicode(e)) > 5 :
				self.ML.myLog( text =  u"updateBLEsensor in Line '%s' has error='%s'" % (sys.exc_traceback.tb_lineno, e))



 
####-------------------------------------------------------------------------####
	def updatePULSE(self,dev,data,whichKeysToDisplay):
		if self.ML.decideMyLog(u"SensorData"): self.ML.myLog( text = "updatePULSE "+unicode(data) )
		try:
			dd = datetime.datetime.now().strftime(_defaultDateStampFormat)
			if u"count" in data and str(dev.states[u"count"]) != str(data[u"count"]) :
				try:	cOld = float(dev.states[u"count"])
				except: cOld =0
				try:	tOld = float(dev.states[u"lastCountSecs"])
				except: tOld = time.time()-1
				dT =  max(time.time()- tOld,1.)
				freq = max(0,(float(data[u"count"])	 - cOld) / dT)
				self.setStatusCol( dev, u"count", data[u"count"], str(data[u"count"]), whichKeysToDisplay, "","", decimalPlaces = "" )
				self.setStatusCol( dev, u"frequency", freq, (u"%.3f"%freq), whichKeysToDisplay, "","", decimalPlaces = 3 )
				self.addToStatesUpdateDict(str(dev.id),"lastCountSecs",(u"%.1f"%time.time()),dev=dev)
				
			if u"burst" in data and data[u"burst"] !=0 and data[u"burst"] !="":
					self.addToStatesUpdateDict(str(dev.id),"lastBurstSecs",(u"%.1f"%time.time()),dev=dev)
				
			if u"longEvent" in data and data[u"longEvent"] !=0 and data[u"longEvent"] !="":
					self.addToStatesUpdateDict(str(dev.id),"lastLongEventSecs",(u"%.1f"%time.time()),dev=dev)
				
			if u"continuous" in data and data[u"continuous"] !="":
					if data[u"continuous"] > 0: 
						self.addToStatesUpdateDict(str(dev.id),"lastContinuousEventSecs",(u"%.1f"%time.time()),dev=dev)
					else: 
						self.addToStatesUpdateDict(str(dev.id),"lastContinuousEventSecsStop",(u"%.1f"%time.time()),dev=dev)

		except	Exception, e:
			if len(unicode(e)) > 5 :
				self.ML.myLog( text =  u"updatePULSE in Line '%s' has error='%s'" % (sys.exc_traceback.tb_lineno, e))
		return 
 
 
####-------------------------------------------------------------------------####
	def updateTEA5767(self,pi,sensors,sensor):
		if self.ML.decideMyLog(u"OutputDevice"): self.ML.myLog( text = sensor+"	 "+unicode(sensors))
		for devId in sensors:
			try:
				dev = indigo.devices[int(devId)]
				iii = 0
				for channels in sensors[devId][u"channels"]:
					self.ML.myLog( text = "updateTEA5767 sensor: "+sensor+"	 "+unicode(channels))
					freq   = channels[u"freq"]
					Signal = channels[u"Signal"]
					ch = "Channel-"+"%02d"%iii
					self.addToStatesUpdateDict(devId,ch,"f="+str(freq)+"; Sig="+str(Signal),dev=dev)
					iii+=1
				for ii in range(iii,41):
					ch = "Channel-"+"%02d"%ii
					self.addToStatesUpdateDict(devId,ch,"",dev=dev)
			except	Exception, e:
				if len(unicode(e)) > 5 :
					self.ML.myLog( text =  u"updateTEA5767 in Line '%s' has error='%s'" % (sys.exc_traceback.tb_lineno, e))
		return 
	   

####-------------------------------------------------------------------------####
####-------------------------------------------------------------------------####
	def updateINPUT(self, dev, data, upState, nInputs,sensor):
		# {u"pi_IN_":"0","sensors":{u"spiMCP3008":{u"INPUT_6":3,"INPUT_7":9,"INPUT_4":0,"INPUT_5":0,"INPUT_2":19,"INPUT_3":534,"INPUT_0":3296,"INPUT_1":3296}}}
		#									 {u'INPUT_6': 0, u'INPUT_7': 0, u'INPUT_4': 0, u'INPUT_5': 0, u'INPUT_2': 0, u'INPUT_3': 518, u'INPUT_0': 3296, u'INPUT_1': 3296}
		try:
			props = dev.pluginProps
			if u"addToInputName" in props:
				try:   addToInputName = int(props[u"addToInputName"])
				except:addToInputName = 0
			else:	   addToInputName = 0
			
			try: 
				upS = int(upState)
				upState = "INPUT_"+str(upS)
			except:pass
			for ii in range(nInputs):
				if nInputs >10:
						inputState = "INPUT_%0.2d" % (ii+addToInputName)
				elif nInputs ==1 and  u"INPUT" in dev.states:
						inputState = u"INPUT"
						upState	   = u"INPUT"
				else:	inputState = u"INPUT_" + unicode(ii+addToInputName)
				input= u"INPUT_" + unicode(ii)
				if self.ML.decideMyLog(u"SensorData"): self.ML.myLog( text =  dev.name+"  "+ upState+"	"+inputState+" "+ input+ "	"+unicode(data)+"  "+ unicode(dev.states))
				if input in data:
					ss, ssUI, unit = self.addmultOffsetUnit(data[input], props)
					#self.ML.myLog( text =	dev.name+"	input in data "+unicode(ss) + " "+ ssUI )
					if dev.states[inputState] != ss:
						self.addToStatesUpdateDict(unicode(dev.id),inputState, ss,dev=dev)
						### minmax if deice.xml has that field
						if inputState+"MaxYesterday" in dev.states:
							decimalPlaces = 1
							v = ss
							if upState == inputState:
								try: 
									v = float(self.getNumber(ssUI))
									dp = str(v).split(".")
									if len(dp) == 0:
										decimalPlaces = 0
									elif len(dp) == 2:
										decimalPlaces = len(dp[1])
									else:
										pass
								except:
									pass
							self.fillMinMaxSensors(dev,inputState,v,decimalPlaces=decimalPlaces)

							#self.ML.myLog( text =	dev.name+" adding to update")
						if upState == inputState:
							fs = self.getNumber(ss)
							if ss == u"1" or ss == u"up" or (fs != 0. and fs != "x"):
								on = True
								self.setIcon(dev,props,"SensorOff-SensorOn",1)
							else:
								on = False
								self.setIcon(dev,props,"SensorOff-SensorOn",0)

							if u"onOffState" in dev.states: 
								self.addToStatesUpdateDict(unicode(dev.id),u"onOffState",on, dev=dev, uiValue=ssUI)
								if dev.states[u"status"] != ssUI + unit:
									self.addToStatesUpdateDict(unicode(dev.id),u"status", ssUI,dev=dev)
							elif u"sensorValue" in dev.states: 
								self.setStatusCol(dev, upState, ss, ssUI + unit, upState, "","", decimalPlaces = decimalPlaces)
							else:
								if dev.states[u"status"] != ssUI + unit:
									self.addToStatesUpdateDict(unicode(dev.id),u"status", ssUI+unit,dev=dev)

		except	Exception, e:
			if self.ML.decideMyLog(u"SensorData"): self.ML.myLog( text =  u"updateINPUT in Line '%s' has error='%s'" % (sys.exc_traceback.tb_lineno, e))



####-------------------------------------------------------------------------####
	def setIcon(self, dev,iconProps,default,UPdown):
		try:
			if u"iconPair" in iconProps and	 iconProps [u"iconPair"] !="":
				icon = iconProps [u"iconPair"].split(u"-")[UPdown]
			else: 
				icon = default.split(u"-")[UPdown]
			try:
				dev.updateStateImageOnServer(getattr(indigo.kStateImageSel, icon, None)) 
			except	Exception, e: 
				if UPdown ==0:					 dev.updateStateImageOnServer(indigo.kStateImageSel.SensorOff)
				else:							 dev.updateStateImageOnServer(indigo.kStateImageSel.SensorOn)
		except	Exception, e:
			if self.ML.decideMyLog(u"SensorData"): self.ML.myLog( text =  u"setIcon in Line '%s' has error='%s'" % (sys.exc_traceback.tb_lineno, e))
			return	



####-------------------------------------------------------------------------####
	def updateapds9960(self, dev, data):
		try:
			props = dev.pluginProps
			input = u"gesture"
			if input in data:
				if unicode(data[input]).find(u"bad") >-1:
					self.addToStatesUpdateDict(unicode(dev.id),u"status", u"no sensor data - disconnected?",dev=dev)
					self.setIcon(dev,props,"SensorOff-SensorOn",0)
					return
				else:
					if data[input] !="NONE":
						if props[u"displayS"] == input:
							self.addToStatesUpdateDict(unicode(dev.id),u"status", data[input],dev=dev)
						self.addToStatesUpdateDict(unicode(dev.id),input,data[input],dev=dev)
						self.addToStatesUpdateDict(unicode(dev.id),input+"Date",datetime.datetime.now().strftime(_defaultDateStampFormat))
						self.setIcon(dev,props,"SensorOff-SensorOn",1)


			input = u"gestureData"
			if input in data:
					if data[input] !="":
						if props[u"displayS"] == input:
							self.addToStatesUpdateDict(unicode(dev.id),u"status", data[input],dev=dev)
						self.addToStatesUpdateDict(unicode(dev.id),input,data[input],dev=dev)
						self.setIcon(dev,props,"SensorOff-SensorOn",1)

			input = u"distance"
			if input in data:
				if unicode(data[input]).find(u"bad") >-1:
					self.addToStatesUpdateDict(unicode(dev.id),u"status", u"no sensor data - disconnected?",dev=dev)
					self.setIcon(dev,props,"SensorOff-SensorOn",0)
				else:
					if data[input] !="NONE":
						if props[u"displayS"] == input:
							self.addToStatesUpdateDict(unicode(dev.id),u"status", data[input],dev=dev)
						self.addToStatesUpdateDict(unicode(dev.id),input,data[input],dev=dev)
						self.addToStatesUpdateDict(unicode(dev.id),input+"Date",datetime.datetime.now().strftime(_defaultDateStampFormat))
						self.setIcon(dev,props,"SensorOff-SensorOn",1)

			input = u"proximity"
			if input in data:
				if unicode(data[input]).find(u"bad") >-1:
					self.addToStatesUpdateDict(unicode(dev.id),u"status", u"no sensor data - disconnected?",dev=dev)
					self.setIcon(dev,props,"SensorOff-SensorOn",0)
				else:
						if props[u"displayS"] == input:
							self.addToStatesUpdateDict(unicode(dev.id),u"status", data[input],dev=dev)
						self.addToStatesUpdateDict(unicode(dev.id),input,data[input],dev=dev)
						self.addToStatesUpdateDict(unicode(dev.id),input+"Date",datetime.datetime.now().strftime(_defaultDateStampFormat))
						self.setIcon(dev,props,"SensorOff-SensorOn",1)

			self.updateRGB(dev, data, props[u"displayS"])

		except	Exception, e:
			if self.ML.decideMyLog(u"SensorData"): self.ML.myLog( text =  u"updateapds9960 in Line '%s' has error='%s'" % (sys.exc_traceback.tb_lineno, e))



####-------------------------------------------------------------------------####
	def updateina219(self,dev,data,whichKeysToDisplay):
		self.updateIna(dev,data,whichKeysToDisplay, [""])


####-------------------------------------------------------------------------####
	def updateina3221(self,dev,data,whichKeysToDisplay):
		self.updateIna(dev,data,whichKeysToDisplay, [1,2,3,4])
####-------------------------------------------------------------------------####
	def updateIna(self,dev,data,whichKeysToDisplay, nChannels):
		try:
			props = dev.pluginProps
			for jj in nChannels:
				for input in [u"Current"+str(jj),"ShuntVoltage"+str(jj),"BusVoltage"+str(jj)]:
					if input in data:
						if unicode(data[input]).find(u"bad") >-1:
							self.setStatusCol( dev, input, 0,  u"no sensor data - disconnected?", u"Current"+str(jj), "","" )
							self.setIcon(dev,props,"SensorOff-SensorOn",0)
							return
						if data[input] !="":
							ss, ssUI, unit = self.addmultOffsetUnit(data[input], dev.pluginProps)
							self.setStatusCol( dev, input, ss, ssUI+unit, whichKeysToDisplay, "","" )
				self.setIcon(dev,props,"SensorOff-SensorOn",1)
		except	Exception, e:
			if self.ML.decideMyLog(u"SensorData"): self.ML.myLog( text =  u"updateina3221 in Line '%s' has error='%s'" % (sys.exc_traceback.tb_lineno, e))

####-------------------------------------------------------------------------####
	def updateADC121(self,dev,data,whichKeysToDisplay):
		try:
			input = u"adc"
			props = dev.pluginProps
			type  = props[u"type"]
			pp = {"offset": props["offset"],"mult":props["mult"], "unit": "ppm","format":"%2d"}

			if unicode(data[input]).find(u"bad") >-1:
					self.addToStatesUpdateDict(unicode(dev.id),u"status", u"no sensor data - disconnected?",dev=dev)
					self.setIcon(dev,props,"SensorOff-SensorOn",0)
					return
					
			self.setIcon(dev,props,"SensorOff-SensorOn",1)
			#self.ML.myLog( text =	type+"	"+unicode(pp)+ "  " +unicode(data[input]) )
			if input in data:
					if data[input] !="":
						ADC = data[input]
						MaxBits = 4095.	  # 12 bits
						Vcc		= 5000.	  # mVolt max

						if	 type.find(u"MQ") > -1:
							try:	Vca		= float(dev.props[u"Vca"] )	  # mVolt  at clean Air / calibration
							except: Vca		= 3710.

						if	type =="MQ7": #CO
							pp["unit"]		="ppm CO"
							pp["format"]	="%.2f"
							RR1 = 0.22
							RR2 = 0.02
							C1	= 10.
							C2	= 1000.
							k = math.log(RR1/RR2) / math.log(C1/C2)
							a = math.exp(  math.log(RR1) -	k * math.log(C1)  )
							RR = (MaxBits/ADC -1.) / (Vcc/Vca -1.)
							val = math.pow(RR/a,1./k)

						elif   type =="MQ9": # CO
							pp["unit"]		="ppm CO"
							pp["format"]	="%.2f"
							RR1 = 1.5
							RR2 = 0.78
							C1	= 200
							C2	= 1000.
							k = math.log(RR1/RR2) / math.log(C1/C2)
							a = math.exp(  math.log(RR1) -	k * math.log(C1)  )
							RR = (MaxBits/ADC -1.) / (Vcc/Vca -1.)
							val = math.pow(RR/a,1./k)

						elif   type =="MQ9-5LPG": # LPG
							pp["unit"]		="ppm LPG"
							pp["format"]	="%.2f"
							RR1 = 2.0
							RR2 = 0.31
							C1	= 200
							C2	= 10000.
							k = math.log(RR1/RR2) / math.log(C1/C2)
							a = math.exp(  math.log(RR1) -	k * math.log(C1)  )
							RR = (MaxBits/ADC -1.) / (Vcc/Vca -1.)
							val = math.pow(RR/a,1./k)

						elif   type =="MQ9-5CH4": # CH4
							pp["unit"]		="ppm CH4"
							pp["format"]	="%.2f"
							RR1 = 3.0
							RR2 = 0.69
							C1	= 200
							C2	= 10000.
							k = math.log(RR1/RR2) / math.log(C1/C2)
							a = math.exp(  math.log(RR1) -	k * math.log(C1)  )
							RR = (MaxBits/ADC -1.) / (Vcc/Vca -1.)
							val = math.pow(RR/a,1./k)

						elif  type =="MQ4": # LNG
							pp["unit"]		="ppm CNG"
							pp["format"]	="%.2f"
							RR1 = 2.5  
							RR2 = 0.42
							C1	= 20.	
							C2	= 10000.
							k = math.log(RR1/RR2) / math.log(C1/C2)
							a = math.exp(  math.log(RR1) -	k * math.log(C1)  )
							RR = (MaxBits/ADC -1.) / (Vcc/Vca -1.)
							val = math.pow(RR/a,1./k)


						elif type =="MQ3-Alcohol": #alcohol
							pp["unit"]		="Alcohol mg/l"
							pp["format"]	="%.2f"
							RR1 = 2.2  
							RR2 = 0.11
							C1	= 0.1	
							C2	= 10.
							k = math.log(RR1/RR2) / math.log(C1/C2)
							a = math.exp(  math.log(RR1) -	k * math.log(C1)  )
							RR = (MaxBits/ADC -1.) / (Vcc/Vca -1.)
							val = math.pow(RR/a,1./k)

						elif type =="MQ3-Benzene": #alcohol
							pp["unit"]		="Benzene mg/l"
							pp["format"]	="%.2f"
							RR1 = 3. 
							RR2 = 0.75
							C1	= 0.1	
							C2	= 10.
							k = math.log(RR1/RR2) / math.log(C1/C2)
							a = math.exp(  math.log(RR1) -	k * math.log(C1)  )
							RR = (MaxBits/ADC -1.) / (Vcc/Vca -1.)
							val = math.pow(RR/a,1./k)

						elif type =="MQ131": #Ozone 
							pp["unit"]		="ppm Ozon"
							pp["format"]	="%.2f"
							RR1 = 3	 
							RR2 = 0.3
							C1	= 5.  
							C2	= 100.
							k = math.log(RR1/RR2) / math.log(C1/C2)
							a = math.exp(  math.log(RR1) -	k * math.log(C1)  )
							RR = (MaxBits/ADC -1.) / (Vcc/Vca -1.)
							val = math.pow(RR/a,1./k)

						elif type =="A13XX": # hall effect sensor
							pp["unit"]		="º"
							pp["format"]	="%.2f"
							val		= (ADC / MaxBits) * 360.0

						elif type =="TA12_200": # linear current sensor
							pp["unit"]		="mA"
							pp["format"]	="%.1f"
							val		= ADC 

						elif type =="adc": # simple ADC
							pp["unit"]	="mV"
							pp["format"]="%0d"
							val			= ADC *(Vcc/MaxBits)


						ss, ssUI, unit = self.addmultOffsetUnit(val, pp)

						self.setStatusCol( dev0, u"value", ss, ssUI+unit, whichKeysToDisplay, "","" )
						self.setStatusCol( dev0, u"adc", ADC, unicode(ADC), whichKeysToDisplay,"","" )
		except	Exception, e:
			if self.ML.decideMyLog(u"SensorData"): self.ML.myLog( text =  u"updateADC121 in Line '%s' has error='%s'" % (sys.exc_traceback.tb_lineno, e))


####-------------------------------------------------------------------------####
	def updateGYROS(self,dev,data,upState):
		try:
			props = dev.pluginProps
			if unicode(data).find(u"bad") >-1:
					self.addToStatesUpdateDict(unicode(dev.id),u"status", u"no sensor data - disconnected?",dev=dev)
					self.setIcon(dev,props,"SensorOff-SensorOn",0)
					return
			self.setIcon(dev,props,"SensorOff-SensorOn",1)
			theList = [u"EULER","QUAT", u"MAG","GYR","ACC","LIN","GRAV","ROT"]
			XYZSumSQ = 0
			#self.ML.myLog( text =	dev.name +"	 "+ unicode(data))
			for input in theList:
				if input not in data: continue
				out=""
				if input ==u"EULER":
					for dim in [u"heading","pitch","roll"]:
						if dim not in data[input]: continue
						if data[input][dim] ==u"":	continue
						ss, ssUI, unit = self.addmultOffsetUnit(data[input][dim], dev.pluginProps)
						out+=ss+","
						self.addToStatesUpdateDict(unicode(dev.id),dim,ss,dev=dev)
				else:
					for dim in [u"x","y","z","w","q","r","s"]:
						if dim not in data[input]: continue
						if data[input][dim] ==u"":	continue
						ss, ssUI, unit = self.addmultOffsetUnit(data[input][dim], dev.pluginProps)
						out+=ss+","
						self.addToStatesUpdateDict(unicode(dev.id),input+dim,ss,dev=dev)
						if u"XYZSumSQ" in dev.states and (input ==u"GYR" or input ==u"MAG"): 
							XYZSumSQ +=data[input][dim]*data[input][dim]
				if upState == input:
					self.addToStatesUpdateDict(unicode(dev.id),u"status", out.strip(u","),dev=dev)

				if u"XYZSumSQ" in dev.states and (input ==u"GYR" or input ==u"MAG"):  
					xys= (u"%7.2f"%math.sqrt(XYZSumSQ)).strip()
					self.addToStatesUpdateDict(unicode(dev.id),"XYZSumSQ",xys,dev=dev)
					if upState == "XYZSumSQ":
						self.addToStatesUpdateDict(unicode(dev.id),u"status", xys)
					

			input = "calibration"
			stateName  ="calibration"
			if stateName in dev.states and input in data:
				if data[input] !="": 
					out=""
					for dim in data[input]:
						out += dim+":"+unicode(data[input][dim])+","
					out= out.strip(u",").strip(u" ")	
					if	upState == input:
						self.addToStatesUpdateDict(unicode(dev.id),u"status",out,dev=dev)
					self.addToStatesUpdateDict(unicode(dev.id),stateName,out,dev=dev)

			input	   = "temp"
			stateName  ="Temperature"
			if stateName in dev.states and input in data:
				if data[input] !="": 
					x, UI, decimalPlaces = self.mintoday(data[input])
					if	upState == stateName :
						self.addToStatesUpdateDict(unicode(dev.id),u"status",UI,dev=dev)
					self.addToStatesUpdateDict(unicode(dev.id),stateName ,x, decimalPlaces= decimalPlaces,dev=dev)

		except	Exception, e:
			if self.ML.decideMyLog(u"SensorData"): self.ML.myLog( text =  u"updateGYROS in Line '%s' has error='%s'" % (sys.exc_traceback.tb_lineno, e))
			

####-------------------------------------------------------------------------####
	def updateDistance(self, dev, data, whichKeysToDisplay):
			#{u"ultrasoundDistance":{u"477759402":{u"distance":1700.3591060638428}}
		try:

			input = u"distance"
			if input in data:
				if unicode(data[input]).find(u"bad") >-1:
					self.addToStatesUpdateDict(unicode(dev.id),u"status", u"no sensor data - disconnected?",dev=dev)
					self.setIcon(dev,props,"SensorOff-SensorOn",0)
					return

				props = dev.pluginProps
				units = "cm"
				dist0 = 1.
				offset= 0.
				multiply=1.
				if	   u"dUnits"	in props: units	   = props[u"dUnits"]
				try:	
					if u"offset"   in props: offset	  = float(props[u"offset"])
				except: pass

				try:	
					if u"multiply" in props: 
						mm = float(props[u"multiply"])
						if mm != 0: multiply=mm
				except: pass

				raw= float(data[input])	 
				distR= (raw+offset)*multiply
				dist = distR
				ud   = "[]"
				if units == "cm":
				   ud = " [cm]"
				   dist = distR
				   dist0 = (u"%8.1f"%(distR)).replace(u" ","")
				elif units == "m":
				   ud = " [m]"
				   dist = distR*0.01
				   dist0 = (u"%8.2f"%(dist)).replace(u" ","")
				elif units == "inches":
				   ud = ' "'
				   dist = distR*0.3937
				   dist0 = (u"%7.1f"%(dist)).replace(u" ","")
				elif units == "feet":
				   ud = " '"
				   dist = distR*0.03280839895
				   dist0 = (u"%8.2f"%(dist)).replace(u" ","")
				self.setStatusCol(dev, u"distance", dist, dist0, whichKeysToDisplay, u"","", decimalPlaces = decimalPlaces)

				self.addToStatesUpdateDict(unicode(dev.id),"measuredNumber", raw)

				if u"speed" in data:
					try: 
						speed = float(data[u"speed"]) / max(self.speedUnits*100., 0.01)	 # comes in cm/sec
						units = self.speedUnits
						sp = unicode(speed) 
						ud = "[]"
						if units == 0.01:
						   ud = " [cm/s]"
						   sp = (u"%8.1f"%(speed)).replace(u" ","")
						   decimalPlaces = 1
						elif units == 1.0:
						   ud = " [m/s]"
						   sp = (u"%8.2f"%(speed)).replace(u" ","")
						   decimalPlaces = 2
						elif units == 0.0254:
						   ud = ' [i/s]'
						   sp = (u"%7.1f"%(speed)).replace(u" ","")
						   decimalPlaces = 1
						elif units == 0.348:
						   ud = " [f/s]"
						   sp = (u"%8.2f"%(speed)).replace(u" ","")
						   decimalPlaces = 2
						elif units == 0.9144:
						   ud = " [y/s]"
						   sp = (u"%8.2f"%(speed)).replace(u" ","")
						   decimalPlaces = 2
						elif units == 3.6:
						   ud = " [kmh]"
						   sp = (u"%8.2f"%(speed)).replace(u" ","")
						   decimalPlaces = 2
						elif units == 2.2369356:
						   ud = " [mph]"
						   sp = (u"%8.2f"%(speed)).replace(u" ","")
						   decimalPlaces = 2
						self.setStatusCol(dev, u"speed", speed, sp+ud, whichKeysToDisplay, u"","", decimalPlaces = decimalPlaces)
					except:
						pass
				
				
				if u"actionShortDistanceLimit" in props:
					try: cutoff= float(props[u"actionShortDistanceLimit"])
					except: cutoff= 50
				else:		cutoff= 50
				if dist < cutoff:
						self.setIcon(dev,props,"SensorOff-SensorOn",1)
				else:
						self.setIcon(dev,props,"SensorOff-SensorOn",0)

		except	Exception, e:
			if self.ML.decideMyLog(u"SensorData"): self.ML.myLog( text =  u"updateDistance in Line '%s' has error='%s'" % (sys.exc_traceback.tb_lineno, e))





####-------------------------------------------------------------------------####
	def getNumber(self,val):
		# test if a val contains a valid number, if not return ""
		# return the number if any meaningful number (with letters before and after return that number)
		# u"a-123.5e" returns -123.5
		# -1.3e5 returns -130000.0
		# -1.3e-5 returns -0.000013
		# u"1.3e-5" returns -0.000013
		# u"1.3e-5x" returns "" ( - sign not first position	 ..need to include)
		# True, u"truE" u"on" "ON".. returns 1.0;  False u"faLse" u"off" returns 0.0
		# u"1 2 3" returns ""
		# u"1.2.3" returns ""
		# u"12-5" returns ""
		try:
			return float(val)
		except:
			if val == ""														: return "x"
			try:
				ttt = unicode(val).upper()															# if unicode return ""	 (-->except:)
				if ttt== "TRUE" or ttt ==u"ON"	or ttt == "T" or ttt==u"UP"						: return 1.0	 # true/on	 --> 1
				if ttt== "FALSE" or ttt == "OFF"	or ttt== "F" or ttt==u"DOWN" or ttt==  "EXPIRED"	: return 0.0		# false/off --> 0
			except:
				pass
			try:
				xx = ''.join([c for c in val if c in  '-1234567890.'])							 # remove non numbers
				lenXX= len(xx)
				if	lenXX > 0:																	# found numbers..if len( ''.join([c for cin xx if c in	'.']) )			  >1	: return "x"		# remove strings that have 2 or more dots " 5.5 6.6"
					if len(''.join([c for c in	xx if c in '-']) )			 >1 : return "x"		# remove strings that have 2 or more -	  u" 5-5 6-6"
					if len( ''.join([c for c  in xx if c in '1234567890']) ) ==0	: return "x"		# remove strings that just no numbers, just . amd - eg "abc.xyz- hij"
					if lenXX ==1												: return float(xx)	# just one number
					if xx.find(u"-") > 0											: return "x"		  # reject if "-" is not in first position
					valList =  list(val)																# make it a list
					count =	 0																		# count number of numbers
					for i in range(len(val)-1):												  # reject -0 1 2.3 4  not consecutive numbers:..
						if (len(''.join([c for c in valList[i ] if c in	 '-1234567890.'])) ==1 ):  # check if this character is a number, if yes:
							count +=1																#
							if count >= lenXX									: break		 # end of # of numbers, end of test: break, its a number
							if (len(''.join([c for c in valList[i+1] if c in '-1234567890.'])) )== 0:  return "x"  # next is not a number and not all numbers accounted for, so it is numberXnumber
					return														 float(xx)	# must be a real number, everything else is excluded
			except:
				return "x"																			# something failed eg unicode only ==> return ""
		return "x"																					# should not happen just for safety

####-------------------------------------------------------------------------####
	def addmultOffsetUnit(self, data, props):

		try:
			ui = float(data)

			if u"onOff" in props:
				if props[u"onOff"] == "ON-off":
					if ui ==1.:
						return "1", u"off", u""
					else:
						return "0", u"ON",	u""

				if props[u"onOff"] == "on-off":
					if ui ==1.:
						return "1", u"off", u""
					else:
						return "0", u"on",	u""

				if props[u"onOff"] == "off-ON":
					if ui ==1.:
						return "1", u"ON",	u""
					else:
						return "0", u"off", u""

				if props[u"onOff"] == "off-on":
					if ui ==1.:
						return "1", u"on",	u""
					else:
						return "0", u"off", u""

				if props[u"onOff"] == "open-closed":
					if ui ==1.:
						return "1", u"open", u""
					else:
						return "0", u"closed",	u""

				if props[u"onOff"] == "closed-open":
					if ui ==1.:
						return "1", u"closed", u""
					else:
						return "0", u"open",  u""

				if props[u"onOff"] == "up-down":
					if ui ==1.:
						return "1", u"up", u""
					else:
						return "0", u"down",  u""

				if props[u"onOff"] == "closed-open":
					if ui ==1.:
						return "1", u"closed", u""
					else:
						return "0", u"open",  u""
						
				if props[u"onOff"] == "down-up":
					if ui ==1.:
						return "1", u"down", u""
					else:
						return "0", u"up",	u""

			offset =0.
			mult=1.
			if u"offset" in props and props[u"offset"] != "":
				offset = float(props[u"offset"])
			if u"mult" in props and props[u"mult"] != "":
				mult = float(props[u"mult"])


			if u"resistorSensor" in props and props[u"resistorSensor"] == "1":
				feedVolt = float(props[u"feedVolt"])
				feedResistor = float(props[u"feedResistor"])
				ui = feedResistor / max(((feedVolt / max(ui, 0.1)) - 1.), 0.001)

				if u"logScale" in props and props[u"logScale"] == "1":
					ui = math.log10(max(0.00001,(ui))+ offset)*mult
				else:
					ui = (ui + offset)*mult
					
			else:
				if u"logScale" in props and props[u"logScale"] == "1":
					ui = math.log10(max(0.00001,(ui))+ offset)*mult
				else:
					ui = (ui + offset)*mult


			if u"unit" in props and props[u"unit"] != "":
				unit = props[u"unit"]
			else:
				unit = ""

			if u"format" in props and props[u"format"] != "":
				ui = props[u"format"] % ui
			else:
				ui = unicode(ui)
		except	Exception, e:
			if len(unicode(e)) > 5 :
				if self.ML.decideMyLog(u"SensorData"): self.ML.myLog( text =  u"addmultOffsetUnit in Line '%s' has error='%s'" % (sys.exc_traceback.tb_lineno, e))
			ui=data
			unit=""	   
		return unicode(data), ui, unit


####-------------------------------------------------------------------------####
	def updateLight(self, dev, data, upState,theType=""):
		try:
			if u"illuminance" in data or u"	 lux" in data or "UV" in data or "UVA" in data or "UVB" in data or "IR" in data or "ambient" in data or "white"	 or "visible" in data:
				props =	 dev.pluginProps
				if u"unit" in props: unit = props[u"unit"]
				else:				unit = ""
				if u"format" in props: formatN = props[u"format"]
				else:				  formatN = "%7.2f"
				logScale="0"
				if u"logScale" in props: 
					logScale = props[u"logScale"]
					if logScale ==u"1":
						if u"format" in props: formatN = props[u"format"]
						else:				  formatN = "%7.2f"
						

				if u"UVA" in data and "UVB" in data and not "UV" in data and "UV" in dev.states:
					data[u"UV"] = (float(data[u"UVA"]) + float(data[u"UVB"]) )/2.

				for  state, key in [["illuminance","lux"],["illuminance","illuminance"],["IR","IR"],["UVA","UVA"],["UVB","UVB"],["UV","UV"],["ambient","ambient"],["white","white"],["visible","visible"]]:
					if state in dev.states and key in data :
						if logScale !=u"1": self.setStatusCol(dev, state, round(float(data[key]),2),  formatN % (float(data[key]))+unit,                                         upState, "","",decimalPlaces=2 )
						else:				self.setStatusCol(dev, state, round(float(data[key]),2), (formatN % math.log10(max(0.1,float(data[key]))) ).replace(u" ", u"")+unit, upState, "","",decimalPlaces=2 )
						self.fillMinMaxSensors(dev,state,data[key],decimalPlaces=2)

				if u"red" in data:
					self.updateRGB( dev, data, upState, theType=theType)
			else:
				dev.updateStateImageOnServer(indigo.kStateImageSel.LightSensorOff)
				
				   
		except	Exception, e:
			if len(unicode(e)) > 5 :
				if self.ML.decideMyLog(u"SensorData"): self.ML.myLog( text =  u"updateLight in Line '%s' has error='%s'" % (sys.exc_traceback.tb_lineno, e))

####-------------------------------------------------------------------------####
	def updateRGB(self, dev, data, upState, theType="",dispType =""):
		try:
			props = dev.pluginProps
			if u"unit" in props: unit = props[u"unit"]
			else:				 unit = ""

			changed = 0
			if u"ambient"	  in data: changed += self.updateRGB2(dev, u"ambient",	  data, upState,unit, dispType=dispType)
			if u"clear"		  in data: changed += self.updateRGB2(dev, u"clear",	  data, upState,unit, dispType=dispType)
			if u"red"		  in data: changed += self.updateRGB2(dev, u"red",		  data, upState,unit, dispType=dispType)
			if u"green"		  in data: changed += self.updateRGB2(dev, u"green",	  data, upState,unit, dispType=dispType)
			if u"blue"		  in data: changed += self.updateRGB2(dev, u"blue",		  data, upState,unit, dispType=dispType)
			if u"violet"	  in data: changed += self.updateRGB2(dev, u"violet",	  data, upState,unit, dispType=dispType)
			if u"orange"	  in data: changed += self.updateRGB2(dev, u"orange",	  data, upState,unit, dispType=dispType)
			if u"yellow"	  in data: changed += self.updateRGB2(dev, u"yellow",	  data, upState,unit, dispType=dispType)
			if u"lux"		  in data: changed += self.updateRGB2(dev, u"lux",		  data, upState,unit, dispType=dispType)
			if u"illuminance" in data: changed += self.updateRGB2(dev, u"illuminance",data, upState,unit, dispType=dispType)
			if changed > 0:
					dev.updateStateImageOnServer(indigo.kStateImageSel.LightSensorOn)
					if u"illuminance" in dev.states and u"illuminance" not in data:
						il = (-0.32466 * data['red']) + (1.57837 * data['green']) + (-0.73191 * data['blue'])  # fron adafruit
						ilUI = (u"%.1f" % il + "[Lux]").replace(u" ", u"")
						self.setStatusCol(dev, u"illuminance", round(il,1), ilUI, upState, u"",u"",decimalPlaces=1 )
					if u"kelvin" in dev.states:
						k = int(self.calcKelvin(data))
						self.setStatusCol(dev, u"kelvin", k, unicode(k) + u"[ºK]", upState, u"",u"",decimalPlaces=0 )
			if upState == "red/green/blue":
						self.addToStatesUpdateDict(unicode(dev.id),"status", u"r/g/b: "+unicode(data['red'])+"/"+unicode(data['green'])+"/"+unicode(data['blue'])+unit,dev=dev )



		except	Exception, e:
			if len(unicode(e)) > 5 :
				self.ML.myLog( text =  u"updateRGB in Line '%s' has error='%s'" % (sys.exc_traceback.tb_lineno, e))

####-------------------------------------------------------------------------####
	def updateRGB2(self, dev, color, data, upState,unit, dispType=""):

		try:
			if color not in dev.states: 
				###self.ML.myLog( text =  u"updateRGB2 in  trying to update " +color+" in dev "+dev.name+"	state is not in dev" )
				return 0
			if dispType !="":
				try: 
					delta = abs(dev.states[color] - float(data[color]))
				except:
					delta = 10000
				#self.ML.myLog( text =	u"delta: "+ str(delta)+" "+color+"	state: "+str(dev.states[color])+"  data: "+str(data[color])	 )
				if delta < 10 ** (-int(dispType)): return 0
			
				if color =="lux"  or color =="illuminance":	 dispType=2
				self.setStatusCol(dev, color, float(data[color]), color+" "+unicode(data[color])+unit, upState, u"",u"",decimalPlaces=dispType )
				return 1

			if dev.states[color] != unicode(data[color]):
				self.setStatusCol(dev, color, float(data[color]), "color "+unicode(data[color])+unit, upState, u"",u"",decimalPlaces=dispType )
				return 1
			return 0
		except	Exception, e:
			if len(unicode(e)) > 5 :
				self.ML.myLog( text =  u"updateRGB2 in Line '%s' has error='%s'" % (sys.exc_traceback.tb_lineno, e))
		return 0
####-------------------------------------------------------------------------####
	def calcKelvin(self, data):	 # from adafruit
		X = (-0.14282 * data['red']) + (1.54924 * data['green']) + (-0.95641 * data['blue'])
		Y = (-0.32466 * data['red']) + (1.57837 * data['green']) + (-0.73191 * data['blue'])
		Z = (-0.68202 * data['red']) + (0.77073 * data['green']) + (0.56332	 * data['blue'])

		# Check for divide by 0 (total darkness) and return None.
		if (X + Y + Z) == 0:
			return 0

		# 2. Calculate the chromaticity co-ordinates
		xc = (X) / (X + Y + Z)
		yc = (Y) / (X + Y + Z)

		# Check for divide by 0 again and return None.
		if (0.1858 - yc) == 0:
			return 0

		# 3. Use McCamy's formula to determine the CCT
		n = (xc - 0.3320) / (0.1858 - yc)

		# Calculate the final CCT
		return (449.0 * (n ** 3.0)) + (3525.0 * (n ** 2.0)) + (6823.3 * n) + 5520.33


####-------------------------------------------------------------------------####
	def convTemp(self, temp):
		try:
			
			temp = float(temp)
			if temp == 999.9:
				return 999.9,"badSensor", 1
			if self.tempUnits == u"Fahrenheit":
				temp = temp * 9. / 5. + 32.
				suff = u"ºF"
			elif self.tempUnits == u"Kelvin":
				temp += 273.15
				suff = u"ºK"
			else:
				suff = u"ºC"
			if self.tempDigits == 0:
				cString = "%d"
			else:
				cString = "%."+str(self.tempDigits)+"f"
			tempU = (cString % temp).strip()
			return round(temp,self.tempDigits) , tempU + suff,self.tempDigits
		except:pass
		return -99, u"",self.tempDigits



####-------------------------------------------------------------------------####
	def convHum(self, hum):
		try:
			humU = (u"%3d" %float(hum)).strip()
			return int(float(hum)), humU + u"%",0
		except:
			return -99, u"",0

####-------------------------------------------------------------------------####
	def convGas(self, GasIN):
		try:
			bad = False
			try:	
					GasResistance	 = (u"%7d" % (float(GasIN[0])/1000.)).strip()+ u"KOhm"
					GasResistanceInt = int(float(GasIN[0]))
			except: 
					bad = True
			try:	
					AirQuality	  = (u"%3d" % (float(GasIN[1]))).strip()+u"%"
					AirQualityInt = int(float(GasIN[1]) )
			except: 
					bad = True
			try:	
					baseline	  = (u"%7d" % (float(GasIN[2]))).strip()+u"%"
					baselineInt	  = int(float(GasIN[2]))
			except: 
					bad = True
			if not bad:
				return GasResistanceInt, GasResistance , AirQualityInt, AirQuality,baselineInt, baseline
			else:
				return "", u"","", u"","", u""
		except:
			return "", u"","", u"","", u""


####-------------------------------------------------------------------------####
	def getDeviceDisplayStateId(self, dev):
		props = dev.pluginProps
		if u"displayState" in props:
			return props[u"displayState"]
		elif u"displayStatus" in dev.states:
			return	u"displayStatus"
		else:
			return "status"


####-------------------------------------------------------------------------####
	def updateBeaconStates(self, fromPi, piNReceived, ipAddress, piMACSend, nOfSecs, msgs):

		try:
			updateFINGnow = False
			ln = len(msgs)
			if ln < 1: return 
			dateString = datetime.datetime.now().strftime(_defaultDateStampFormat)
			
			#######---- update pi-beacon device info
			updatepiIP		= False
			updatepiMAC		= False
			
			if self.selectBeaconsLogTimer !={}: 
				for sMAC in self.selectBeaconsLogTimer:
					if piMACSend.find(sMAC[:self.selectBeaconsLogTimer[sMAC]]) ==0:
						self.ML.myLog( text =	   u"sel.beacon logging: RPI msg	:"+piMACSend+"; "+(" ").ljust(36)	 + " pi#="+str(fromPi)		)
			if self.RPI[unicode(fromPi)][u"piMAC"] != piMACSend:
				if self.RPI[unicode(fromPi)][u"piMAC"] ==u"":
					self.RPI[unicode(fromPi)][u"piMAC"] = piMACSend
				else:
			   
					try:
						existingIndigoId = int(self.RPI[unicode(fromPi)][u"piDevId"])
						existingPiDev	 = indigo.devices[existingIndigoId]
						props			 = existingPiDev.pluginProps
						try:
							oldMAC		 = props[u"address"]
						except:
							oldMAC		 = existingPiDev.description
						
						if oldMAC != piMACSend:	 # should always be !=
							self.ML.myLog( text =  u"trying: to replace , create new RPI for   "+piMACSend+"  "+unicode(props))
							if piMACSend not in self.beacons:
								replaceRPIBeacon =""
								for btest in self.beacons:
									if self.beacons[btest][u"indigoId"] == existingIndigoId:
										replaceRPIBeacon = btest
										break
								if replaceRPIBeacon !="":
									self.beacons[piMACSend] = copy.deepcopy(self.beacons[replaceRPIBeacon])
									del self.beacons[replaceRPIBeacon]
									self.ML.myLog( text =  u" replacing old beacon")
								else:
									self.ML.myLog( text =  u" adding new ")
									self.beacons[piMACSend]					 = copy.deepcopy(_GlobalConst_emptyBeacon) 
									self.beacons[piMACSend][u"ignore"]		  = 0
									self.beacons[piMACSend][u"indigoId"]	  = existingIndigoId
									self.beacons[piMACSend][u"note"]		  = "Pi-"+str(fromPi)
									self.beacons[piMACSend][u"typeOfBeacon"]  = "rPI"
									self.beacons[piMACSend][u"status"]		  = "up" 
								self.ML.myLog( text =  u" replacing fields	")
								props[u"address"]	  = piMACSend
								props[u"ipNumberPi"]  = ipAddress
								existingPiDev.replacePluginPropsOnServer(props)
								existingPiDev = indigo.devcice[existingIndigoId]
								try:
									existingPiDev.address = piMACSend
									existingPiDev.replaceOnServer()
								except: pass
								self.RPI[unicode(fromPi)][u"piMAC"]	 = piMACSend
								self.RPI[unicode(fromPi)][u"ipNumberPi"] = ipAddress
								if oldMAC in self.beacons: del self.beacons[oldMAC]
								self.setALLrPiV(u"piUpToDate", [u"updateParamsFTP"])
								self.fixConfig(checkOnly = ["all","rpi"],fromPGM="updateBeaconStates pichanged") # updateBeaconStates # ok only if new MAC for rpi ...
							else:
								if self.beacons[piMACSend][u"typeOfBeacon"].lower() !="rpi": 
									pass # let the normal process replace the beacon with the RPI
								else:
									self.RPI[unicode(fromPi)][u"piMAC"]	 = piMACSend
									self.ML.myLog( text =  u"might have failed to replace RPI pi#="+str(fromPi)+";	piMACSend="+piMACSend+", you have to do it manually; beacon with type = rpi already exist ")

					except	Exception, e:
							self.ML.myLog( text =  u"updateBeaconStates in Line '%s' has error='%s'" % (sys.exc_traceback.tb_lineno, e))
							self.ML.myLog( text =  u"failed to replace RPI pi#="+str(fromPi)+";	 piMACSend="+piMACSend+", you have to do it manually")

				updatepiMAC = True
			if self.RPI[unicode(fromPi)][u"piNumberReceived"] != piNReceived:
				self.RPI[unicode(fromPi)][u"piNumberReceived"] = piNReceived
				updatepiIP = True
			foundPI = False
			if piMACSend in self.beacons:
				indigoId = self.beacons[piMACSend][u"indigoId"]
				# if self.ML.decideMyLog(u"Logic"): self.ML.myLog( text =  u"testing new pi 1-- "+unicode(fromPi)+	"  "+unicode(piNReceived)+	"  "+piMACSend +"; indigoId: "+unicode(indigoId) )
				try:
					dev = indigo.devices[indigoId]
				except	Exception, e:
		
					if unicode(e).find(u"timeout waiting") > -1:
						self.ML.myLog( text =  u"updateBeaconStates in Line '%s' has error='%s'" % (sys.exc_traceback.tb_lineno, e))
						self.ML.myLog( text =  u"communication to indigo is interrupted")
						return 
					if unicode(e).find(u"not found in database") ==-1:
						self.ML.myLog( text =  u"updateBeaconStates in Line '%s' has error='%s'" % (sys.exc_traceback.tb_lineno, e))
						self.ML.myLog( text =  u"updateBeaconStates beacons dict: "+ unicode(self.beacons[piMACSend]))
					return 

				try:
					if dev.deviceTypeId == "rPI":
						foundPI = True
						if dev.states[u"note"] != "Pi-" + unicode(piNReceived):
							dev.updateStateOnServer(u"note", u"Pi-" + piNReceived)
							#self.addToStatesUpdateDict(unicode(dev.id),u"note", u"Pi-" + piNReceived,dev=dev)
						self.beacons[piMACSend][u"lastUp"] = time.time()
						self.RPI[unicode(piNReceived)][u"piDevId"] = dev.id
						if dev.description != "rPI-"+ unicode(piNReceived)+"-"+ipAddress:
							dev.description = "rPI-"+ unicode(piNReceived)+"-"+ipAddress
							dev.replaceOnServer()
							
					else:
						indigo.device.delete(dev)
						self.ML.myLog( errorType = u"smallErr", text =u"deleting beacon: " + dev.name + " replacing simple beacon with rPi model(1)")
						del self.beacons[piMACSend]

				except	Exception, e:
					if len(unicode(e)) > 5 :
						self.ML.myLog( errorType = u"smallErr", text =u"updateBeaconStates in Line '%s' has error='%s'" % (sys.exc_traceback.tb_lineno, e))
						self.ML.myLog( errorType = u"smallErr", text =u"beacons[piMACSend] " + unicode(fromPi) + "	" + piMACSend + "  " + unicode(indigoId) + "  " + unicode(self.beacons[piMACSend]))
						if unicode(e).find(u"timeout waiting") > -1:
							self.ML.myLog( text =  u"updateBeaconStates in Line '%s' has error='%s'" % (sys.exc_traceback.tb_lineno, e))
							self.ML.myLog( text =  u"communication to indigo is interrupted")
							return 
						self.ML.myLog( errorType = u"smallErr", text =u" error ok if new / replaced RPI")

					del self.beacons[piMACSend]

			if not foundPI:
				if piMACSend in self.beacons: del self.beacons[piMACSend]
				delDEV = []
				# if self.ML.decideMyLog(u"BeaconData"): self.ML.myLog( text =	u"testing new pi 2-- "+unicode(fromPi)+	 "	"+unicode(piNReceived)+	 "	"+piMACSend )
				for dev in indigo.devices.iter("props.isRPIDevice"):
					props = dev.pluginProps
					try:
						if props[u"address"] == piMACSend:
							delDEV.append(dev)
							self.RPI[unicode(piNReceived)][u"piDevId"] = 0
					except:
			
						self.ML.myLog( text =  u"device has no address, setting piDevId=0:	" + dev.name + " " + unicode(dev.id) +
								   unicode(props) + " " + unicode(dev.globalProps))
						delDEV.append(dev)
						self.RPI[unicode(fromPi)][u"piDevId"] = 0

				for dev in delDEV:
					self.ML.myLog( errorType = u"smallErr", text =u"deleting beacon: " + dev.name + " replacing simple beacon with rPi model(2)")
					try:
						indigo.device.delete(dev)
					except:
						pass

				self.ML.myLog( text =  u"creating new pi 3-- " + unicode(fromPi) + "  " + unicode(piNReceived) + "	" + piMACSend)
				indigo.device.create(
					protocol		= indigo.kProtocol.Plugin,
					address			= piMACSend,
					name			= "Pi_" + piMACSend,
					description		= "rPI-" + piNReceived+"-"+ipAddress,
					pluginId		= self.pluginId,
					deviceTypeId	= "rPI",
					folder			= self.piFolderId,
					props		= {
						u"typeOfBeacon":			  _GlobalConst_emptyrPiProps[u"typeOfBeacon"],
						u"updateSignalValuesSeconds": _GlobalConst_emptyrPiProps[u"updateSignalValuesSeconds"],
						u"beaconTxPower":			  _GlobalConst_emptyrPiProps[u"beaconTxPower"],
						u"SupportsBatteryLevel":	  _GlobalConst_emptyrPiProps[u"SupportsBatteryLevel"],
						u"sendToIndigoSecs":		  _GlobalConst_emptyrPiProps[u"sendToIndigoSecs"],
						u"shutDownPinInput":		  _GlobalConst_emptyrPiProps[u"shutDownPinInput"],
						u"shutDownPinOutput" :		  _GlobalConst_emptyrPiProps[u"shutDownPinOutput"],
						u"PosXYZ":					  _GlobalConst_emptyrPiProps[u"PosXYZ"],
						u"signalDelta" :			  _GlobalConst_emptyrPiProps[u"signalDelta"],
						u"minSignalCutoff" :		  _GlobalConst_emptyrPiProps[u"minSignalCutoff"],
						u"expirationTime" :			  _GlobalConst_emptyrPiProps[u"expirationTime"],
						u"fastDown" :				  _GlobalConst_emptyrPiProps[u"fastDown"],
						u"BLEserial":				  _GlobalConst_emptyrPiProps[u"BLEserial"],
						u"isRPIDevice":				  True,
						u"rssiOffset":				  _GlobalConst_emptyrPiProps[u"rssiOffset"]
						}
					)
					
				try:
					dev = indigo.devices[u"Pi_" + piMACSend]
				except	Exception, e:
					if unicode(e).find(u"timeout waiting") > -1:
						self.ML.myLog( text =  u"updateBeaconStates in Line '%s' has error='%s'" % (sys.exc_traceback.tb_lineno, e))
						self.ML.myLog( text =  u"communication to indigo is interrupted")
						return 
					if unicode(e).find(u"not found in database") ==-1:
						self.ML.myLog( text =  u"updateBeaconStates in Line '%s' has error='%s'" % (sys.exc_traceback.tb_lineno, e))
						return 
					self.ML.myLog( text =  u"updateBeaconStates in Line '%s' has error='%s'" % (sys.exc_traceback.tb_lineno, e))
					return 
					
				dev.updateStateImageOnServer(indigo.kStateImageSel.SensorOn)
				self.addToStatesUpdateDict(unicode(dev.id),u"status", u"up",dev=dev)
				self.addToStatesUpdateDict(unicode(dev.id),u"note", u"Pi-" + piNReceived)
				self.addToStatesUpdateDict(unicode(dev.id),u"TxPowerSet", float(_GlobalConst_emptyrPiProps[u"beaconTxPower"]))
				self.addToStatesUpdateDict(unicode(dev.id),u"created", dateString)
				self.addToStatesUpdateDict(unicode(dev.id),u"Pi_" + unicode(fromPi) + "_Signal", 0)
				self.addToStatesUpdateDict(unicode(dev.id),u"TxPowerReceived",0)
				self.addToStatesUpdateDict(unicode(dev.id),u"pkLen",0)
				self.executeUpdateStatesDict(onlyDevID=str(dev.id),calledFrom="updateBeaconStates new rpi")

				self.updatePiBeaconNote[piMACSend] = 1
				self.beacons[piMACSend]						 = copy.deepcopy(_GlobalConst_emptyBeacon)
				self.beacons[piMACSend][u"expirationTime"]	 = self.secToDown
				self.beacons[piMACSend][u"indigoId"]		 = dev.id
				self.beacons[piMACSend][u"updateFING"]		 = 0
				self.beacons[piMACSend][u"status"]			 = "up"
				self.beacons[piMACSend][u"lastUp"]			 = time.time()
				self.beacons[piMACSend][u"note"]			 = "Pi-" + piNReceived
				self.beacons[piMACSend][u"typeOfBeacon"]	 = "rPI"
				self.beacons[piMACSend][u"created"]			 = dateString
				self.RPI[unicode(fromPi)][u"piDevId"]			 = dev.id  # used to quickly look up the rPI devices in indigo
				self.RPI[unicode(fromPi)][u"piNumberReceived"]	 = piNReceived
				self.RPI[unicode(fromPi)][u"piMAC"]				 = piMACSend
				self.setONErPiV(fromPi,"piUpToDate", [u"updateParamsFTP","rebootSSH"])
				self.fixConfig(checkOnly = ["all","rpi","force"],fromPGM="updateBeaconStates1") # updateBeaconStates # ok only if new MAC for rpi ...


			###########################	 ibeacons ############################
			#### ---- update ibeacon info
			for msg in msgs:
				mac		= msg[0].upper()
				reason	= msg[1]
				uuid	= msg[2]
				try:	rssi = float(msg[3])
				except: rssi = -999.
				txPower = msg[4]
				lCount	= msg[5]
				if rssi ==-999 : 
					txPower=0
				else: 
					try:	rssiOffset = float(self.RPI[unicode(fromPi)][u"rssiOffset"] )
					except: rssiOffset = 0
				try:	batteryLevel = msg[6]
				except: batteryLevel = ""
				try:	pkLen	= msg[7]
				except: pkLen = 0


				if self.selectBeaconsLogTimer !={}: 
					for sMAC in self.selectBeaconsLogTimer:
						if mac.find(sMAC[:self.selectBeaconsLogTimer[sMAC]]) ==0:
							self.ML.myLog( text =	   u"sel.beacon logging: newMSG	  -1- :"+mac+"; "+(" ").ljust(36)	 + " pi#="+str(fromPi) +";	#Msgs="+str(lCount).ljust(2)   +";	pkLen="+str(pkLen).ljust(3)						   +"	 rssi="+str(rssi).rjust(6)	 + "					  txPow="+str(txPower).rjust(6)+" uuid="+ uuid.ljust(44))




				if (len(uuid) > 11 and uuid[:12] in self.beaconsIgnoreUUID) or (mac in self.beacons and self.beacons[mac][u"ignore"] >0 ):
					rj = open(self.userIndigoPluginDir + "rejected/rejects", u"a")
					rj.write(dateString + " pi: " + unicode(fromPi) + "; beacon: " + unicode(msg) + "\n")
					rj.close()
					if self.ML.decideMyLog(u"BeaconData"): self.ML.myLog( text =  u" rejected beacon because its in reject family: pi: " + unicode(fromPi) + "; beacon: " + unicode(msg))
					continue  # ignore certain type of beacons, but only for new ones, old ones must be excluded individually
					####self.ML.myLog( text =  u"pi: "+unicode(fromPi)+"  beacon uuid : "+ unicode(msg) )

				if mac not in self.beacons:
					self.beacons[mac] = copy.deepcopy(_GlobalConst_emptyBeacon)
					self.beacons[mac][u"created"] = dateString
					self.beacons[mac][u"lastUp"]  = time.time()
				if self.beacons[mac][u"ignore"] > 0: continue



				## found valid msg and beacon, update indigo etc
				name = ""
				indigoId = self.beacons[mac][u"indigoId"]
				if indigoId != 0:

					try:
						dev = indigo.devices[indigoId]
						name = dev.name
					except	Exception, e:
						if unicode(e).find(u"timeout waiting") > -1:
							self.ML.myLog( text =  u"updateBeaconStates in Line '%s' has error='%s'" % (sys.exc_traceback.tb_lineno, e) )
							self.ML.myLog( text =  u"communication to indigo is interrupted")
							return 
						if unicode(e).find(u"not found in database") ==-1:
							self.ML.myLog( text =  u"updateBeaconStates in Line '%s' has error='%s'" % (sys.exc_traceback.tb_lineno, e))
							return 
						self.ML.myLog( text =  u"updateBeaconStates in Line '%s' has error='%s'" % (sys.exc_traceback.tb_lineno, e) + " indigoId:" + unicode(self.beacons[mac][u"indigoId"])+" ignore if beacon.. was just deleted")
						self.beacons[mac][u"indigoId"] = 0
				else: # no indigoId found, double check 
					for dev in indigo.devices.iter("props.isBeaconDevice,props.isRPIDevice"):
							props = dev.pluginProps
							if u"address" in props:
								if props[u"address"] == mac:
									if dev.deviceTypeId != "beacon": 
										if self.ML.decideMyLog(u"BeaconData"): self.ML.myLog( text =  u" rejecting new beacon, same mac number already exist for different device type: "+dev.deviceTypeId+"  dev: "+dev.name)
										continue
									else:
										self.beacons[mac][u"indigoId"] = dev.id
										name = dev.name
										break


				if rssi < self.acceptNewiBeacons and name ==u"" and self.beacons[mac][u"ignore"] >= 0: 
					if self.selectBeaconsLogTimer !={}: 
						for sMAC in self.selectBeaconsLogTimer:
							if mac.find(sMAC[:self.selectBeaconsLogTimer[sMAC]]) ==0:
								self.ML.myLog( text = u"sel.beacon logging: newMSG rej rssi :"+mac+"; "+("name= empty").ljust(30)	 + " pi#="+str(fromPi) +";	#Msgs="+str(lCount).ljust(2)   +";	pkLen="+str(pkLen).ljust(3)						   +"	 rssi="+str(rssi).rjust(6)	 + "					  txPow="+str(txPower).rjust(6)+" uuid="+ uuid.ljust(44))
				
					continue # to accept new beacon(name=""), signal must be > threshold
				# if self.ML.decideMyLog(u"BeaconData"): self.ML.myLog( text = "1 updating indigo  w: "+mac+" id "+unicode(self.beacons[mac][u"indigoId"]) )





				try:
					if name == "":
						self.ML.myLog( text =  u"creating new beacon,  received from pi # " + unicode(fromPi) + "/" + piMACSend + ":	  beacon-" + mac + "  UUID: " + uuid)

						name = "beacon_" + mac
						indigo.device.create(
							protocol		= indigo.kProtocol.Plugin,
							address			= mac,
							name			= name,
							description		= uuid,
							pluginId		= self.pluginId,
							deviceTypeId	= "beacon",
							folder			= self.piFolderId,
							props			= {
								   u"typeOfBeacon":				 _GlobalConst_emptyBeaconProps[u"typeOfBeacon"],
								   u"updateSignalValuesSeconds": _GlobalConst_emptyBeaconProps[u"updateSignalValuesSeconds"],
								   u"expirationTime":			 _GlobalConst_emptyBeaconProps[u"expirationTime"],
								   u"fastDown":					 _GlobalConst_emptyBeaconProps[u"fastDown"],
								   u"signalDelta":				 _GlobalConst_emptyBeaconProps[u"signalDelta"],
								   u"minSignalCutoff":			 _GlobalConst_emptyBeaconProps[u"minSignalCutoff"],
								   u"beaconTxPower":			 _GlobalConst_emptyBeaconProps[u"beaconTxPower"],
								   u"isBeaconDevice":			 True,
								   u"SupportsBatteryLevel":		 False,
								   u"UUID":						 uuid}
							)
						try:
							dev = indigo.devices[u"beacon_" + mac]
						except	Exception, e:
				
							if unicode(e).find(u"timeout waiting") > -1:
								self.ML.myLog( text =  u"updateBeaconStates in Line '%s' has error='%s'" % (sys.exc_traceback.tb_lineno, e))
								self.ML.myLog( text =  u"communication to indigo is interrupted")
								return 
						dev.updateStateImageOnServer(indigo.kStateImageSel.SensorOn)
						self.addToStatesUpdateDict(unicode(dev.id),u"status", u"up",dev=dev)
						self.addToStatesUpdateDict(unicode(dev.id),u"UUID", uuid)
						self.addToStatesUpdateDict(unicode(dev.id),u"note", u"beacon-other")
						self.addToStatesUpdateDict(unicode(dev.id),u"created", dateString)
						self.addToStatesUpdateDict(unicode(dev.id),u"TxPowerSet", float(_GlobalConst_emptyBeaconProps[u"beaconTxPower"]))
						for ii in range(_GlobalConst_numberOfiBeaconRPI):
							if ii == fromPi: continue
							try: self.addToStatesUpdateDict(unicode(dev.id),"Pi_"+unicode(ii)+"_Signal",-999)
							except: pass
						self.addToStatesUpdateDict(unicode(dev.id),u"Pi_" + unicode(fromPi) + "_Signal", int(rssi+rssiOffset))
						self.addToStatesUpdateDict(unicode(dev.id),u"TxPowerReceived",float(txPower))
						self.addToStatesUpdateDict(unicode(dev.id),u"closestRPI",fromPi)
						self.addToStatesUpdateDict(unicode(dev.id),u"closestRPIText","Pi_"+str(fromPi))
						if pkLen !=0: self.addToStatesUpdateDict(unicode(dev.id),u"pkLen",pkLen)
						if batteryLevel !="":
							pass
							#self.addToStatesUpdateDict(unicode(dev.id),u"batteryLevel", batteryLevel)
						self.beacons[mac][u"typeOfBeacon"] = "other"
						self.beacons[mac][u"created"] = dateString
						self.beacons[mac][u"expirationTime"] = self.secToDown
						self.beacons[mac][u"lastUp"] = time.time()
						dev = indigo.devices[u"beacon_" + mac]
						props = dev.pluginProps
						self.executeUpdateStatesDict(onlyDevID=str(dev.id), calledFrom="updateBeaconStates new beacon")
						self.fixConfig(checkOnly = ["beacon"],fromPGM="updateBeaconStates new beacon") # updateBeaconStates
						if self.newBeaconsLogTimer >0:
							if time.time()> self.newBeaconsLogTimer:
								self.newBeaconsLogTimer =0
							else:
								self.ML.myLog( text = u"new beacon logging: created:"+unicode(dateString.split(u" ")[1])+" "+mac+"	"+ name.ljust(20)+" "+ uuid.ljust(44)+ "  pi#="+str(fromPi)+ "	rssi="+str(rssi)+ "	 txPower="+str(txPower))

				except	Exception, e:
					if len(unicode(e)) > 5 :
						self.ML.myLog( text =  u"updateBeaconStates in Line '%s' has error='%s'" % (sys.exc_traceback.tb_lineno, e))
						if unicode(e).find(u"timeout waiting") > -1:
							self.ML.myLog( text =  u"communication to indigo is interrupted")
							return 
				dev = indigo.devices[name]
				newStates = copy.copy(dev.states)
				props = dev.pluginProps



				
				updateSignal = False
				if newStates[u"status"] == "up" and rssi == -999.:	## check for fast down signal ==-999
					piStillUp=-1
					ssss =-9999; tttt=-1
					for pix in range(_GlobalConst_numberOfiBeaconRPI):
						if pix == fromPi: continue
						#if mac ==u"0C:F3:EE:00:66:15" and pix ==0:
						#	 if self.ML.decideMyLog(u"CAR"): self.ML.myLog( text = "pi0 test 0C:F3:EE:00:66:15 "+str(time.time() - time.mktime(time.strptime(newStates[u"Pi_"+unicode(pix)+"_Time"],_defaultDateStampFormat)))+"  sig="+str(newStates[u"Pi_"+unicode(pix)+"_Signal"]))
						if len(dev.states[u"Pi_"+unicode(pix)+"_Time"]) < 18: continue 
						if self.beacons[mac][u"receivedSignals"][pix][1] < 10 or (time.time()- self.beacons[mac][u"receivedSignals"][pix][1]) > 25.: continue # states only get updated > updateSignalValuesSeconds, cant expect better numbers
						if dev.states[u"Pi_"+unicode(pix)+"_Signal"] > -500: 
							piStillUp = pix
							ssss = dev.states[u"Pi_"+unicode(pix)+"_Signal"]
							tttt = time.time()- self.beacons[mac][u"receivedSignals"][pix][1]
							break
					if self.ML.decideMyLog(u"CAR"): self.ML.myLog( text = "testing fastdown from pi:"+str(fromPi)+ "  for:"+mac+";	piStillUp? "+str(piStillUp)+", new sig=-999; oldsig"+ str(dev.states[u"Pi_"+unicode(fromPi)+"_Signal"])+"  status:"+ dev.states[u"status"]+ "  lastSig="+str(ssss)+"  lastT="+str(int(tttt)))
					if piStillUp ==-1:
						updateSignal = True
						if mac != piMACSend: dev.updateStateImageOnServer(indigo.kStateImageSel.SensorOff)	# only for regluar ibeacons..
						newStates = self.addToStatesUpdateDict(unicode(dev.id),u"status", u"down",newStates=newStates,dev=dev)
						self.beacons[mac][u"status"] = "down"
						#newStates= self.addToStatesUpdateDict(unicode(dev.id),u"pkLen",pkLen,newStates=newStates)
						self.beacons[mac][u"updateFING"] = 1
						updateFINGnow = True
						self.beacons[mac][u"lastUp"] = -time.time()
						newStates = self.addToStatesUpdateDict(unicode(dev.id),"closestRPI", -1,newStates=newStates)
						newStates = self.addToStatesUpdateDict(unicode(dev.id),"closestRPIText", u"Pi_-1",newStates=newStates)
						if u"showBeaconOnMap" in props and props[u"showBeaconOnMap"] in _GlobalConst_beaconPlotSymbols: self.beaconPositionsUpdated =4
					newStates= self.addToStatesUpdateDict(unicode(dev.id),u"Pi_" + unicode(fromPi) + "_Signal", -999,newStates=newStates,dev=dev)

				# thsi enables better / faster location bounding to only specific room/ rpi
				if u"IgnoreBeaconIfSignalLessThan" in props:
					try:
						IgnoreBeaconIfSignalLessThan = float(props[u"IgnoreBeaconIfSignalLessThan"])
						if IgnoreBeaconIfSignalLessThan > -999.:
							if rssi < IgnoreBeaconIfSignalLessThan:
								rssi=-999
					except: ##IgnoreBeaconIfSignalLessThan value not set 
						pass
	 
				logTRUEfromSignal = False	   
				if self.trackSignalStrengthIfGeaterThan[0] <99.:
					try:	
						deltaSignalLOG = (rssi + rssiOffset - float(self.beacons[mac][u"receivedSignals"][fromPi][0]))
						if self.trackSignalStrengthIfGeaterThan[1] == "i":
							logTRUEfromSignal =	 ( abs(deltaSignalLOG) > self.trackSignalStrengthIfGeaterThan[0]  ) or	(rssi ==-999. and float(self.beacons[mac][u"receivedSignals"][fromPi][0]) !=-999)
						else:
							logTRUEfromSignal =	 ( abs(deltaSignalLOG) > self.trackSignalStrengthIfGeaterThan[0]  ) and ( rssi !=-999 and self.beacons[mac][u"receivedSignals"][fromPi][0] !=-999)
						
						#self.ML.myLog( text = str(rssi)+"	"+ str(self.beacons[mac][u"receivedSignals"][fromPi][0])+"	"+str(self.trackSignalStrengthIfGeaterThan)	 )
					except	Exception, e:
			
						self.ML.myLog( text =  u"updateBeaconStates in Line '%s' has error='%s'" % (sys.exc_traceback.tb_lineno, e))
						logTRUEfromSignal = False
					
				logTRUEfromChangeOFRPI = False
				if dev.deviceTypeId == "beacon": 
					try:	oldRPI = int(dev.states[u"closestRPI"])
					except: oldRPI =-1

				if rssi != -999. :
					if ( self.beacons[mac][u"lastUp"]> -1) :
						self.beacons[mac][u"receivedSignals"][fromPi] =[rssi,time.time()]
						self.beacons[mac][u"lastUp"] = time.time()
						if dev.deviceTypeId == "beacon" : 
							closestRPI = self.findClosestRPI(mac,dev)
						if	( time.time()- self.beacons[mac][u"updateWindow"] > self.beacons[mac][ "updateSignalValuesSeconds"] or
							  time.time()- self.beacons[mac][u"receivedSignals"][fromPi][1] > 100. ):  # ==0 or xx seconds updates for 75 seconds, this RPI msg older than 100 secs then xx secs no update for next time
							self.beacons[mac][u"updateWindow"] = time.time()
							
						if (dev.deviceTypeId == "beacon" and closestRPI != oldRPI) and self.trackSignalChangeOfRPI:
							logTRUEfromChangeOFRPI = True
							
						if (self.beacons[mac][u"status"] != "up" or					 # was down now up
							time.time()- self.beacons[mac][u"updateWindow"] < 70 or			 # update for 70 seconds then break 
							newStates[u"Pi_" + unicode(fromPi) + "_Signal"] == -999 or	# was down now up
							abs(newStates[u"Pi_" + unicode(fromPi) + "_Signal"] - self.beacons[mac][u"receivedSignals"][fromPi][0]) >20 or # signal change large
							(dev.deviceTypeId == "beacon" and closestRPI != newStates[u"closestRPI"])):				   # clostest RPi has changed
								try:
									minTxPower = float(self.beacons[mac][u"beaconTxPower"])
								except:
									minTxPower = 99999.
								updateSignal = True
								newStates = self.addToStatesUpdateDict(unicode(dev.id),u"Pi_" + unicode(fromPi) + "_Signal", int(rssi-rssiOffset),newStates=newStates,dev=dev)
								newStates = self.addToStatesUpdateDict(unicode(dev.id),u"TxPowerReceived",float(txPower),newStates=newStates)
								txx = float(txPower)
								if minTxPower <	 991.: txx = minTxPower
								distCalc = self.calcDist(  txx, (rssi+rssiOffset) )/ self.distanceUnits
								newStates = self.addToStatesUpdateDict(unicode(dev.id),u"Pi_" + unicode(fromPi) + "_Distance", distCalc,newStates=newStates ,decimalPlaces=1  )
								newStates = self.addToStatesUpdateDict(unicode(dev.id),u"Pi_" + unicode(fromPi) + "_Time", dateString,newStates=newStates)
								if newStates[u"status"] != "up":  
									if mac != piMACSend: dev.updateStateImageOnServer(indigo.kStateImageSel.SensorOn)
									newStates=self.addToStatesUpdateDict(unicode(dev.id),u"status", u"up",newStates=newStates)
									self.beacons[mac][u"updateFING"] = 1
									updateFINGnow = True
									self.beacons[mac][u"status"] = "up"
									if u"showBeaconOnMap" in props and props[u"showBeaconOnMap"] in _GlobalConst_beaconPlotSymbols: self.beaconPositionsUpdated =5

						if dev.deviceTypeId == "beacon" : 
							newStates = self.addToStatesUpdateDict(unicode(dev.id),"closestRPI", closestRPI,newStates=newStates,dev=dev)
							newStates = self.addToStatesUpdateDict(unicode(dev.id),"closestRPIText", u"Pi_"+str(closestRPI),newStates=newStates)
							
					self.beacons[mac][u"indigoId"] = dev.id
					if pkLen !=0: newStates= self.addToStatesUpdateDict(unicode(dev.id),u"pkLen",pkLen,newStates=newStates,dev=dev)

				if rssi != -999. or self.beacons[mac][u"receivedSignals"][fromPi][0] != rssi+rssiOffset:
					self.beacons[mac][u"receivedSignals"][fromPi] =[rssi+rssiOffset,time.time()]

				if mac in self.CARS[u"beacon"]:
					if dev.states[u"status"] != newStates[u"status"] and time.time()- self.startTime > 30:
						self.updateCARS(mac,dev,newStates)

				if uuid != "x-x-x" and uuid !="":
					if u"UUID" in dev.states and uuid != dev.states[u"UUID"]:
						newStates = self.addToStatesUpdateDict(unicode(dev.id),u"UUID", uuid,newStates=newStates,dev=dev)
					#if mac ==u"45:A1:10:DB:F7:BD": self.ML.myLog( text = " UUID map1 "+name+"	"+mac+" "+uuid)
					if dev.deviceTypeId != "rPI":
						dev = indigo.devices[name]
						exName = dev.description
						ok1, un1 = self.mapUUIDtoName(uuid, typeId=dev.deviceTypeId)
						ok2, un2 = self.mapMACtoiPhoneUUID(mac, uuid, typeId=dev.deviceTypeId)
						#if mac ==u"45:A1:10:DB:F7:BD": self.ML.myLog( text = " UUID map2 "+unicode(ok)+"  "+un1+"	"+unicode(ok2)+"  "+un2)
						if	ok1 ==0 or ok2==0:
							if ok1 ==0:
								uname = un1
							else:
								uname = un2
							if exName != uname: # not already in place
									if dev.description != uname:
										dev.description = uname	 # update notes (= desciption)
										dev.replaceOnServer()
										dev = indigo.devices[name]
									props = dev.pluginProps
									if u"uuid" not in props:
										props[u"uuid"] = uuid
										dev.replacePluginPropsOnServer(props)
										if self.ML.decideMyLog(u"BeaconData"): self.ML.myLog( text = " creating UUID for " + name + " " + uuid )
									elif props[u"uuid"] != uuid:
										if self.ML.decideMyLog(u"BeaconData"): self.ML.myLog( text = "updating UUID for " + name + "from  " + props[u"uuid"] + "  to  "+ uuid)
										props[u"uuid"] = uuid
										dev.replacePluginPropsOnServer(props)
						elif  ok1 ==1 or ok2==1:
							if ok1 ==1:
								uname = un1
							else:
								uname = un2
								if dev.description != uname:
									dev.description = uname	 # update notes (= desciption)
									dev.replaceOnServer()
									dev = indigo.devices[name]
								props = dev.pluginProps
								if u"uuid" not in props:
									props[u"uuid"] = uuid
									dev.replacePluginPropsOnServer(props)
									if self.ML.decideMyLog(u"BeaconData"): self.ML.myLog( text =  u" creating UUID for " + name + " " + uuid)
								elif props[u"uuid"] != uuid:
									if self.ML.decideMyLog(u"BeaconData"): self.ML.myLog( text =  u"updating UUID for " + name + "from	" + props[u"uuid"] + "	to	" + uuid)
									props[u"uuid"] = uuid
									dev.replacePluginPropsOnServer(props)

				if updateSignal and "note" in dev.states and dev.states[u"note"].find(u"beacon") >-1:  
					try:
						props=dev.pluginProps
						expirationTime=props[u"expirationTime"]
						update, deltaDistance =self.calcPostion(dev, expirationTime)
						if ( update or (deltaDistance > self.beaconPositionsdeltaDistanceMinForImage) ) and "showBeaconOnMap" in props and props[u"showBeaconOnMap"] in _GlobalConst_beaconPlotSymbols:
							#self.ML.myLog( text = u"beaconPositionsUpdated; calcPostion:"+name+" pi#="+str(fromPi)	  +"   deltaDistance:"+ unicode(deltaDistance)	  +"   update:"+ unicode(update)  )
							self.beaconPositionsUpdated =6

					except	Exception, e:
						if len(unicode(e)) > 5 :
							self.ML.myLog( text =  u"updateBeaconStates in Line '%s' has error='%s'" % (sys.exc_traceback.tb_lineno, e))

				if self.newBeaconsLogTimer >0:
						try:
							created = datetime.datetime.strptime(dev.states[u"created"], _defaultDateStampFormat)
							created = time.mktime(created.timetuple()) 
							if created + self.newBeaconsLogTimer > 2*time.time():
								self.ML.myLog( text = u"new.beacon logging: newMSG	 -2- :"+mac+";	"+name.ljust(36)+ " pi#="+str(fromPi) +";  #Msgs="+str(lCount).ljust(2)	  +";  pkLen="+str(pkLen).ljust(3)				  + "	 rssi="+str(rssi).rjust(6)	  +"					  txPow="+str(txPower).rjust(6)+" cr="+dev.states[u"created"]+" uuid="+ uuid.ljust(44))
							if self.newBeaconsLogTimer < time.time():
								self.ML.myLog( text = u"new.beacon logging: resetting  newBeaconsLogTimer to OFF")
								self.newBeaconsLogTimer =0
						except	Exception, e:
							self.ML.myLog( text =  u"updateBeaconStates in Line '%s' has error='%s'" % (sys.exc_traceback.tb_lineno, e))
							
				if self.selectBeaconsLogTimer !={}: 
					for sMAC in self.selectBeaconsLogTimer:
						if mac.find(sMAC[:self.selectBeaconsLogTimer[sMAC]]) ==0:
							self.ML.myLog( text =	  u"sel.beacon logging: newMSG	 -3- :"+mac+"; "+name.ljust(36)	   + " pi#="+str(fromPi) +";  #Msgs="+str(lCount).ljust(2)	 +";  pkLen="+str(pkLen).ljust(3)						 +"	   rssi="+str(rssi).rjust(6)   + "						txPow="+str(txPower).rjust(6)+" uuid="+ uuid.ljust(44))

				if logTRUEfromChangeOFRPI:
					self.ML.myLog( text = u"ChangeOfRPI.beacon logging	 :"+mac+"  "+name.ljust(36)	   + " pi#="+str(closestRPI)+" oldpi=" + str(oldRPI)+";	 #Msgs="+str(lCount).ljust(2)	+";	 pkLen="+str(pkLen) + "		rssi="+str(rssi).rjust(6)		+ "						 txPow="+str(txPower).rjust(6))
		  
				if logTRUEfromSignal:
					if abs(deltaSignalLOG)	 > 500 and rssi > -200:
						self.ML.myLog( text = u"ChangeOfSignal.beacon logging:		"+mac+";  "+name.ljust(36)+ " pi#="+str(fromPi)	 +";  #Msgs="+str(lCount).ljust(2)	 +";  pkLen="+str(pkLen).ljust(3)						 +"	   rssi="+str(rssi).rjust(6)	+" off --> ON			txPow="+str(txPower).rjust(6))
					elif abs(deltaSignalLOG) > 500 and rssi < -200:
						self.ML.myLog( text = u"ChangeOfSignal.beacon logging:		"+mac+";  "+name.ljust(36)+ " pi#="+str(fromPi)	 +";  #Msgs="+str(lCount).ljust(2)	 +";  pkLen="+str(pkLen).ljust(3)						 +"	   rssi="+str(rssi).rjust(6)	+" ON  --> off			txPow="+str(txPower).rjust(6))
					else:
						self.ML.myLog( text = u"ChangeOfSignal.beacon logging:		"+mac+";  "+name.ljust(36)+ " pi#="+str(fromPi)	 +";  #Msgs="+str(lCount).ljust(2)	 +";  pkLen="+str(pkLen).ljust(3)						 +"	   rssi="+str(rssi).rjust(6)	+" new-old_Sig.= "+ unicode(deltaSignalLOG).rjust(5)+ "	 txPow="+str(txPower).rjust(6))

				try:
					if False:  # disabled 
						if dev.deviceTypeId != "rPI":
							try:
								if props[u"typeOfBeacon"].upper().find(u"JAALEE") > -1 and False:
									if batteryLevel !="":
										batteryLevel = int(float(batteryLevel) / 2.55)	# max =255 =11111111 in bits
										if dev.states[u"batteryLevel"] != batteryLevel: 
											newStates = self.addToStatesUpdateDict(unicode(dev.id),u"batteryLevel", batteryLevel,newStates=newStates,dev=dev)
										self.beacons[mac][u"batteryLevel"] = batteryLevel
							except:
								pass
				except:
					pass
				self.executeUpdateStatesDict(onlyDevID=str(dev.id),calledFrom="updateBeaconStates 1")	 

			if updatepiIP:
				if self.ML.decideMyLog(u"Logic"): self.ML.myLog( text =	 u"trying to update device note	 for pi# " + unicode(fromPi))
				if piMACSend in self.beacons:
					if self.beacons[piMACSend][u"indigoId"] != 0:
						try:
							dev = indigo.devices[self.beacons[piMACSend][u"indigoId"]]
							dev.updateStateOnServer(unicode(dev.id),u"note",	 "PI-" + unicode(fromPi))

						except	Exception, e:
							if unicode(e).find(u"timeout waiting") > -1:
								self.ML.myLog( text =  u"updateBeaconStates in Line '%s' has error='%s'" % (sys.exc_traceback.tb_lineno, e))
								self.ML.myLog( text =  u"communication to indigo is interrupted")
								return 

							self.ML.myLog( text =  u"Could not update device for pi# " + unicode(fromPi))


						############DIST CALCULATION for beacon

			
			



			if updateFINGnow: 
				self.updateFING(u"event")
			
		except	Exception, e:

			if unicode(e).find(u"timeout waiting") > -1:
				self.ML.myLog( text =  u"updateBeaconStates in Line '%s' has error='%s'" % (sys.exc_traceback.tb_lineno, e))
				self.ML.myLog( text =  u"communication to indigo is interrupted")
				return 
			if len(unicode(e)) > 5	and unicode(e).find(u"not found in database") ==-1:
				self.ML.myLog( text =  u"updateBeaconStates in Line '%s' has error='%s'" % (sys.exc_traceback.tb_lineno, e))
		return	



####-------------------------------------------------------------------------####
	####calc distance from received signal and transmitted power assuming Signal ~ Power/r**2---------
	def findClosestRPI(self,mac,deviBeacon):
		try:
			if mac				  not in self.beacons:		return -2
			if u"receivedSignals" not in self.beacons[mac]: return -3
			if u"closestRPI"	  not in deviBeacon.states: return -4
		except:
															return -5
		newMAXSignal   = -9999.
		currMAXSignal  = -9999.
		newClosestRPI  = -1
		currClosestRPI = -1

		try:
			currClosestRPI	= int(deviBeacon.states[u"closestRPI"])
			if currClosestRPI !=-1	and (time.time()- self.beacons[mac][u"receivedSignals"][currClosestRPI][1])	 <70.:
				currMAXSignal	= self.beacons[mac][u"receivedSignals"][currClosestRPI][0]
		except: 
			currClosestRPI =-1; currMAXSignal = -9999.

		try:
			for pix in range(_GlobalConst_numberOfiBeaconRPI):
				if self.RPI[unicode(pix)][u"piOnOff"] != "0": 
					try: # if empty field skip
						if time.time()- self.beacons[mac][u"receivedSignals"][pix][1]  <70.:  # signal recent enough
							if self.beacons[mac][u"receivedSignals"][pix][0] > -300: 
								if self.beacons[mac][u"receivedSignals"][pix][0] >	newMAXSignal:	
									newMAXSignal   = self.beacons[mac][u"receivedSignals"][pix][0]
									newClosestRPI  = pix
					except:
						pass
			# dont switch if: <	 4 dBm diff and	 not defined then keep current 
			if (newMAXSignal - currMAXSignal) < 4 and  currClosestRPI !=-1: # 
				newClosestRPI = currClosestRPI
		except	Exception, e: 
			if len(unicode(e)) > 5 :
				self.ML.myLog( text =  u"findClosestRPI in Line '%s' has error='%s'" % (sys.exc_traceback.tb_lineno, e))
		#if mac ==u"48:BD:EE:7C:3D:65": self.ML.myLog( text =  u"mac# :"+mac+u"	  pi-cl:"+ unicode(closest)+u"	in	pi:"+ unicode(pi0)+"  Signal:"+ unicode(maxSignal))
		return newClosestRPI

####-------------------------------------------------------------------------####
	def calcDist(self, power, rssi):
		 try:
			power = float(power)
			if power > 100: return 99999.
			rssi = float(rssi)
			if rssi > 100:	return 99999.
			if rssi < -160: return 99999.

			# sqrt( 10**(  (p-s)/10 )  )  (sqrt replace with **1/2	;  **1/10 ==> **1/20)
			dist = round(min(99999., math.pow(10.0, max((power - rssi), -20.) / 20.)),1)
			###self.ML.myLog( text = unicode(power)+"  "+ unicode(rssi) +" " +unicode(dist)) 
			return dist

		 except	 Exception, e:
			if len(unicode(e)) > 5 :
				self.ML.myLog( text =  u"calcDist in Line '%s' has error='%s'" % (sys.exc_traceback.tb_lineno, e))
		 return 99999.


####-------------------------------------------------------------------------####
	def sendGPIOCommand(self, ip, pi, typeId, cmd, GPIOpin=0, pulseUp=0, pulseDown=0, nPulses=0, analogValue=0,rampTime=0, i2cAddress=0,text="",soundFile="",restoreAfterBoot="0",startAtDateTime=0, inverseGPIO=False):
		cmd1 =""
		try:
			if	 cmd == "newMessage":
				 cmd1 = {u"device": typeId, u"command":cmd, u"startAtDateTime": startAtDateTime}
			elif cmd == "startCalibration":
				 cmd1 = {u"device": typeId, u"command":cmd, u"startAtDateTime": startAtDateTime}
			elif cmd == "resetDevice":
				 cmd1 = {u"device": typeId, u"command":cmd, u"startAtDateTime": startAtDateTime}
			else:
				if typeId == "setMCP4725":
					cmd1 = {u"device": typeId, u"command": cmd, u"i2cAddress": i2cAddress, u"values":{u"analogValue":analogValue,"rampTime":rampTime,"pulseUp":pulseUp,"pulseDown": pulseDown,"nPulses":nPulses},"restoreAfterBoot": restoreAfterBoot, u"startAtDateTime": startAtDateTime}

				elif typeId == "setPCF8591dac":
					cmd1 = {u"device": typeId, u"command": cmd, u"i2cAddress": i2cAddress, u"values":{u"analogValue":analogValue,"rampTime":rampTime,"pulseUp":pulseUp,"pulseDown": pulseDown,"nPulses":nPulses},"restoreAfterBoot": restoreAfterBoot, u"startAtDateTime": startAtDateTime}

				elif typeId == "myoutput":
					cmd1 = {u"device": typeId, u"command": u"myoutput", u"text": text, u"restoreAfterBoot": restoreAfterBoot, u"startAtDateTime": startAtDateTime}

				elif typeId == "playSound":
					cmd1 = {u"device": typeId, u"command": cmd, u"soundFile": soundFile, u"startAtDateTime": startAtDateTime}

				elif typeId.find(u"OUTPUTgpio") >- 1:
					if cmd == "up" or cmd == "down":
						cmd1 = {u"device": typeId, u"command": cmd, u"pin": GPIOpin, u"restoreAfterBoot": restoreAfterBoot, u"startAtDateTime": startAtDateTime, u"inverseGPIO": inverseGPIO}
					elif cmd in[u"pulseUp","pulseDown","continuousUpDown","analogWrite"]:
						cmd1 = {u"device": typeId, u"command": cmd, u"pin": GPIOpin, u"values": {u"analogValue":analogValue,"pulseUp":pulseUp,"pulseDown": pulseDown,"nPulses":nPulses}, u"restoreAfterBoot": restoreAfterBoot, u"startAtDateTime": startAtDateTime, u"inverseGPIO": inverseGPIO}
					elif cmd == "disable":
						cmd1 = {u"device": typeId, u"command": cmd, u"pin": GPIOpin}
						
				elif typeId.find(u"display") >- 1:
					if cmd == "up" or cmd == "down":
						cmd1 = {u"device": typeId, u"command": cmd,	 "restoreAfterBoot": restoreAfterBoot}
						
			cmds = json.dumps([cmd1])
			
			self.sendtoRPI(ip, pi ,cmds)
			
			if self.ML.decideMyLog(u"OutputDevice"): self.ML.myLog( text =	u"sending: " + cmds)

		except	Exception, e:
			if len(unicode(e)) > 5 :
				self.ML.myLog( text =  u"sendGPIOCommand in Line '%s' has error='%s'" % (sys.exc_traceback.tb_lineno, e))



####-------------------------------------------------------------------------####
	def sendGPIOCommands(self, ip, pi, cmd, GPIOpin, inverseGPIO):
		nCmds = len(cmd)
		cmd1 =[]
		try:
			for kk in range(nCmds):
				if cmd[kk] == "up" or cmd[kk] == "down":
					cmd1.append({u"device": "OUTPUTgpio-1", u"command": cmd[kk], u"pin": GPIOpin[kk], u"inverseGPIO": inverseGPIO[kk]})
						
			cmds = json.dumps(cmd1)
			
			self.sendtoRPI(ip, pi ,cmds)
			
			if self.ML.decideMyLog(u"OutputDevice"): self.ML.myLog( text =	u"sendGPIOCommand-s-: " + cmds)

		except	Exception, e:
			if len(unicode(e)) > 5 :
				self.ML.myLog( text =  u"sendGPIOCommands in Line '%s' has error='%s'" % (sys.exc_traceback.tb_lineno, e))




			###########################	   UTILITIES  #### START #################


####-------------------------------------------------------------------------####
	def setupFilesForPi(self):
		try:
			if self.ML.decideMyLog(u"UpdateRPI"): self.ML.myLog( text =	 u"updating pi server files")

			self.makeBeacons_parameterFile()

			for pi in range(_GlobalConst_numberOfRPI):
				piS = unicode(pi)
				if self.RPI[piS][u"piOnOff"] == "0": continue
				self.makeParametersFile(piS)
				self.makeInterfacesFile(piS)
				self.makeSupplicantFile(piS)

			   
		except	Exception, e:
				self.ML.myLog( text =  u"setupFilesForPi in Line '%s' has error='%s'" % (sys.exc_traceback.tb_lineno, e))
		return




####-------------------------------------------------------------------------####
	def makeBeacons_parameterFile(self):
		out={}
		xx1 = []
		xx2 = []
		xx3 = []
		xx4 = {}
		xx5 = {}
		xx6 = {}
		xx7 = {}
		xx8 = {}
		for beacon in self.beacons:
			if self.beacons[beacon][u"ignore"] >= 1:  xx1.append(beacon)
			if self.beacons[beacon][u"ignore"] == 0:  xx2.append(beacon)
			if self.beacons[beacon][u"ignore"] == -1: xx3.append(beacon)
			try:
				if float(self.beacons[beacon][u"signalDelta"]) < 200:
					xx4[beacon] = self.beacons[beacon][u"signalDelta"]
			except:
				pass
			try:
				if float(self.beacons[beacon][u"minSignalCutoff"]) >-120:
					xx5[beacon] = self.beacons[beacon][u"minSignalCutoff"]
			except:
				pass
			if self.beacons[beacon][u"typeOfBeacon"].upper().find(u"JAALEE") > -1:
				xx6[beacon]			  = 1  # offset of uuid-maj-min
				xx7[beacon] = -3  # position of battery info byte in data (-x count from end )
			if u"fastDownMinSignal"	 in self.beacons[beacon]: 
				try:
					fDSecs	= self.beacons[beacon][u"fastDown"]
					fDSig	= self.beacons[beacon][u"fastDownMinSignal"]
					if float(fDSecs) != 0.0:
						xx8[beacon] = {u"seconds":float(fDSecs), u"fastDownMinSignal": float(fDSig)}
				except:
					pass
		out["ignoreMAC"]			= xx1
		out["onlyTheseMAC"]			= xx2
		out["doNotIgnore"]			= xx3
		out["signalDelta"]			= xx4
		out["minSignalCutoff"]		= xx5
		out["offsetUUID"]			= xx6
		out["batteryLevelPosition"] = xx7
		out["fastDownMinSignal"]	= xx8
		out["UUIDtoIphone"]			= self.beaconsUUIDtoIphone
		out["ignoreUUID"]			= []
		for UUID in self.beaconsIgnoreUUID:
			out["ignoreUUID"].append(UUID)


		f = open(self.userIndigoPluginDir + "all/beacon_parameters", u"w")
		f.write(json.dumps(out))
		f.close()

		try:
			f = open(self.userIndigoPluginDir + "all/touchFile", u"w")
			f.write(unicode(time.time()))
			f.close()
		except	Exception, e:
				self.ML.myLog( text =  u"makeBeacons_parameterFile in Line '%s' has error='%s'" % (sys.exc_traceback.tb_lineno, e))
		return



####-------------------------------------------------------------------------####
	def makeInterfacesFile(self,piS):
		try:
			if self.RPI[piS][u"piOnOff"] == "0": return
			f = open(self.userIndigoPluginDir + "interfaceFiles/interfaces." + piS, u"w")
			f.write(u"auto lo\n")
			f.write(u"iface lo inet loopback\n")
			f.write(u"auto eth0\n")
			f.write(u"allow-hotplug eth0\n")
			f.write(u"iface eth0 inet dhcp\n\n")
			f.write(u"allow-hotplug wlan0\n")
			f.write(u"auto wlan0\n")
			f.write(u"iface wlan0 inet static\n")
			f.write(u"	 address " + self.RPI[piS][u"ipNumberPi"] + "\n")
			f.write(u"	 netmask 255.255.255.0 \n")
			f.write(u"	 gateway " + self.routerIP + "\n")
			f.write('	wpa-ssid ' + self.wifiSSID + '\n')
			f.write('	wpa-passphrase	' + self.wifiPassword + '\n')
			f.write('	dns-nameservers 8.8.8.8	  8.8.8.4\n')
			f.write('#iface default inet dhcp\n')
			f.close()
		except	Exception, e:
				self.ML.myLog( text =  u"makeInterfacesFile in Line '%s' has error='%s'" % (sys.exc_traceback.tb_lineno, e))
		return

####-------------------------------------------------------------------------####
	def makeSupplicantFile(self,piS):
		try:
			if self.RPI[piS][u"piOnOff"] == "0": return
			f = open(self.userIndigoPluginDir + "interfaceFiles/wpa_supplicant.conf." + piS, u"w")
			f.write(u"ctrl_interface=DIR=/var/run/wpa_supplicant GROUP=netdev\n")
			f.write(u"update_config=1\n")
			f.write(u"network={\n")
			f.write('ssid="' + self.wifiSSID + '"\n')
			f.write('passphrase="' + self.wifiPassword + '"\n')
			if self.key_mgmt != "" and self.key_mgmt != "NONE":
				f.write('key_mgmt="' + self.key_mgmt + '"\n')
			f.write(u"}\n")
			f.close()
		except	Exception, e:
				self.ML.myLog( text =  u"makeSupplicantFile in Line '%s' has error='%s'" % (sys.exc_traceback.tb_lineno, e))
		return

####-------------------------------------------------------------------------####
	def makeParametersFile(self, piS,retFile=False):
		try:
				if self.RPI[piS][u"piOnOff"] == "0": return
				out = {}
				pi = int(piS)

				out[u"rebootWatchDogTime"]		  = self.rebootWatchDogTime
				out[u"GPIOpwm"]					  = self.GPIOpwm
				out[u"debugRPI"]				  = self.debugRPILevel
				out[u"restartBLEifNoConnect"]	  = self.restartBLEifNoConnect
				out[u"acceptNewiBeacons"]		  = self.acceptNewiBeacons
				out[u"acceptJunkBeacons"]		  = self.acceptJunkBeacons
				out[u"rebootHour"]				  = -1
				out[u"sendAfterSeconds"]		  = unicode(self.sendAfterSeconds)
				out[u"ipOfServer"]				  = self.myIpNumber
				out[u"portOfServer"]			  = self.portOfServer
				out[u"userIdOfServer"]			  = self.userIdOfServer
				out[u"indigoInputPORT"]			  = self.indigoInputPORT
				out[u"IndigoOrSocket"]			  = self.IndigoOrSocket
				out[u"passwordOfServer"]		  = self.passwordOfServer
				out[u"authentication"]			  = self.authentication
				out[u"wifiOFF"]					  = self.wifiOFF
				out[u"myPiNumber"]				  = piS
				out[u"enableRebootCheck"]		  = self.RPI[piS][u"enableRebootCheck"]
				out[u"rPiCommandPORT"]			  = self.rPiCommandPORT
				out[u"sendToIndigoSecs"]		  = self.RPI[piS][u"sendToIndigoSecs"]
				out[u"deleteHistoryAfterSeconds"] = self.deleteHistoryAfterSeconds
				out[u"enableiBeacons"]			  = self.RPI[piS][u"enableiBeacons"]
				out[u"pressureUnits"]			  = self.pluginPrefs.get(u"pressureUnits", u"hPascal")
				out[u"distanceUnits"]			  = self.pluginPrefs.get(u"distanceUnits", u"1.0")
				out[u"tempUnits"]				  = self.pluginPrefs.get(u"tempUnits", u"C")
				out[u"IPnumberOfRPI"]			  = self.RPI[piS][u"ipNumberPi"]
				out[u"deltaChangedSensor"]		  = self.RPI[piS][u"deltaChangedSensor"]
				out[u"sensorRefreshSecs"]		  = float(self.RPI[piS][u"sensorRefreshSecs"])
				out[u"sendFullUUID"]			  = self.sendFullUUID

				try :
					piDeviceExist=False
					try:
						try:	  piID= int(self.RPI[piS][u"piDevId"])
						except:	  piID=0
						if piID !=0: 
							piDev = indigo.devices[piID]
							props = piDev.pluginProps
							piDeviceExist=True
					except	Exception, e:
						if unicode(e).find(u"timeout waiting") > -1:
							self.ML.myLog( text =  u"makeParametersFile in Line '%s' has error='%s'" % (sys.exc_traceback.tb_lineno, e))
							self.ML.myLog( text =  u"communication to indigo is interrupted")
							return
						if unicode(e).find(u"not found in database") >-1:
							self.ML.myLog( text =  u"makeParametersFile in Line '%s' has error='%s'" % (sys.exc_traceback.tb_lineno, e))
							self.ML.myLog( text =  u"RPI:"+piS+" devid:"+unicode(piID)+" not in indigo, please restart plugin ")
							self.updateNeeded += ",fixConfig"
							self.fixConfig(checkOnly = ["all","rpi"],fromPGM="makeParametersFile bad rpi") 
						else:	 
							self.ML.myLog( text =  u"makeParametersFile in Line '%s' has error='%s'" % (sys.exc_traceback.tb_lineno, e))
							self.ML.myLog( text =  u"RPI:"+piS+" error ..  piDevId not set:"+ unicode(self.RPI[piS]))
							self.updateNeeded += ",fixConfig"
							self.fixConfig(checkOnly = ["all","rpi"],fromPGM="makeParametersFile2")

					if piDeviceExist: 
						out[u"shutDownPinInput"]  = -1
						if u"shutDownPinInput" in props:
							try:  out[u"shutDownPinInput"]	=  int(props[u"shutDownPinInput"])
							except: pass
						out[u"minPinActiveTimeForShutdown"]  = 99999999999
						if u"minPinActiveTimeForShutdown" in props:
							try:  out[u"minPinActiveTimeForShutdown"]	=  int(props[u"minPinActiveTimeForShutdown"])
							except: pass
						out[u"shutDownPinOutput"]  = -1
						if u"shutDownPinOutput" in props:
						   try:	 out[u"shutDownPinOutput"]	=  int(props[u"shutDownPinOutput"])
						   except: pass

						if u"display" in props:
							try: out[u"display"]  =	 int(props[u"display"])
							except: pass

						if u"addNewOneWireSensors" in props:
							out[u"addNewOneWireSensors"]  =	 (props[u"addNewOneWireSensors"])

						if u"enableMuxI2C" in props:
							out[u"enableMuxI2C"]  =	 (props[u"enableMuxI2C"])
							
							
						if u"useRTC" in props:
							out[u"useRTC"]	=  props[u"useRTC"]
						else:
							out[u"useRTC"]	=  ""

						if u"networkType" in props:
							out[u"networkType"]	 =	props[u"networkType"]
						else:
							out[u"networkType"]	 =	"fullIndigo"
							
						if u"bluetoothONoff" in props:
							out[u"bluetoothONoff"]	=  props[u"bluetoothONoff"]

							
						if u"rebootAtMidnight" in props and props[u"rebootAtMidnight"] ==u"0":
							out[u"rebootHour"]			 = -1
						else:	 
							out[u"rebootHour"]			 = self.rebootHour

						out = self.updateSensProps(out, props, u"useRamDiskForLogfiles", elseSet="0")
						out = self.updateSensProps(out, props, u"rebootCommand")
						out = self.updateSensProps(out, props, u"BLEserial", elseSet="sequential")

				except	Exception, e:
						self.ML.myLog( text =  u"makeParametersFile in Line '%s' has error='%s'" % (sys.exc_traceback.tb_lineno, e))
						return ""

					

				out[u"rPiRestartCommand"]	 = self.rPiRestartCommand[pi]
				if self.rPiRestartCommand[pi].find(u"reboot") >- 1:
					out[u"reboot"] = datetime.datetime.now().strftime(u"%Y-%m-%d-%H:%M:%S")

				out[u"timeStamp"]  = datetime.datetime.now().strftime(u"%Y-%m-%d-%H:%M:%S")

				self.rPiRestartCommand[pi]= ""


				out[u"sensors"]				 = {}
				for sensor in self.RPI[piS][u"input"]:
					try:
						if sensor not in _GlobalConst_allowedSensors: continue
						if sensor not in self.RPI[piS][u"input"]: continue
						if len(self.RPI[piS][u"input"][sensor]) == 0: continue
						sens={}
						for devIdS in self.RPI[piS][u"input"][sensor]:
							if devIdS == "0" or	 devIdS == "": continue
							try:
								devId = int(devIdS)
								dev = indigo.devices[devId]
							except	Exception, e:
								if unicode(e).find(u"timeout waiting") > -1:
									self.ML.myLog( text =  u"makeParametersFile in Line '%s' has error='%s'" % (sys.exc_traceback.tb_lineno, e))
									self.ML.myLog( text =  u"communication to indigo is interrupted")
									return
								self.ML.myLog( text =  u"makeParametersFile in Line '%s' has error='%s'" % (sys.exc_traceback.tb_lineno, e))
								continue
								
							if not dev.enabled: continue
							props = dev.pluginProps
							sens[devIdS] = {}

							if u"deviceDefs" in props:
								sens[devIdS] = {u"INPUTS":json.loads(props[u"deviceDefs"])}
							sens[devIdS] = self.updateSensProps(sens[devIdS], props, u"gpio")

							if "serialNumber" in dev.states:
								sens[devIdS] = self.updateSensProps(sens[devIdS], dev.states, u"serialNumber",elseSet="--force--")
							else: 
								sens[devIdS] = self.updateSensProps(sens[devIdS], dev.states, u"serialNumber",elseSet=None)

							if u"iPhoneRefreshDownSecs" in props:
								sens[devIdS] = self.updateSensProps(sens[devIdS], props, u"iPhoneRefreshUpSecs",elseSet=300)
								sens[devIdS] = self.updateSensProps(sens[devIdS], props, u"iPhoneRefreshDownSecs",elseSet=10)
								sens[devIdS] = self.updateSensProps(sens[devIdS], props, u"BLEtimeout",elseSet=10)
								sens[devIdS] = self.updateSensProps(sens[devIdS], props, u"macAddress")
								
							#sens[devIdS] = self.updateSensProps(sens[devIdS], props, u"TimeSwitchSensitivityRainToMayBeRaining")
							#sens[devIdS] = self.updateSensProps(sens[devIdS], props, u"TimeSwitchSensitivityMayBeRainingToHigh")
							#sens[devIdS] = self.updateSensProps(sens[devIdS], props, u"TimeSwitchSensitivityHighToMed")
							#sens[devIdS] = self.updateSensProps(sens[devIdS], props, u"TimeSwitchSensitivityMedToLow")
							#sens[devIdS] = self.updateSensProps(sens[devIdS], props, u"TimeSwitchSensitivityLowToMed")
							#sens[devIdS] = self.updateSensProps(sens[devIdS], props, u"TimeSwitchSensitivityMedToHigh")
							#sens[devIdS] = self.updateSensProps(sens[devIdS], props, u"TimeSwitchSensitivityHighToAnyRain")
							sens[devIdS] = self.updateSensProps(sens[devIdS], props, u"rainScaleFactor")
							sens[devIdS] = self.updateSensProps(sens[devIdS], props, u"gpioIn")
							sens[devIdS] = self.updateSensProps(sens[devIdS], props, u"gpioSW1")
							sens[devIdS] = self.updateSensProps(sens[devIdS], props, u"gpioSW2")
							sens[devIdS] = self.updateSensProps(sens[devIdS], props, u"gpioSW5")
							sens[devIdS] = self.updateSensProps(sens[devIdS], props, u"gpioSWP")
							sens[devIdS] = self.updateSensProps(sens[devIdS], props, u"cyclePower")
							sens[devIdS] = self.updateSensProps(sens[devIdS], props, u"sensorMode")
							sens[devIdS] = self.updateSensProps(sens[devIdS], props, u"sendMSGEverySecs")

							sens[devIdS] = self.updateSensProps(sens[devIdS], props, u"timeaboveCalibrationMAX")
							sens[devIdS] = self.updateSensProps(sens[devIdS], dev.states, u"CO2offset")
							sens[devIdS] = self.updateSensProps(sens[devIdS], props, u"launchCommand")
							sens[devIdS] = self.updateSensProps(sens[devIdS], props, u"launchCheck")
							sens[devIdS] = self.updateSensProps(sens[devIdS], props, u"amplification")
							sens[devIdS] = self.updateSensProps(sens[devIdS], props, u"sensitivity")
							sens[devIdS] = self.updateSensProps(sens[devIdS], props, u"CO2normal")
							sens[devIdS] = self.updateSensProps(sens[devIdS], props, u"resetPin")
							sens[devIdS] = self.updateSensProps(sens[devIdS], props, u"shuntResistor")
							sens[devIdS] = self.updateSensProps(sens[devIdS], props, u"shuntResistor1")
							sens[devIdS] = self.updateSensProps(sens[devIdS], props, u"shuntResistor2")
							sens[devIdS] = self.updateSensProps(sens[devIdS], props, u"shuntResistor3")
							sens[devIdS] = self.updateSensProps(sens[devIdS], props, u"useMuxChannel")
							sens[devIdS] = self.updateSensProps(sens[devIdS], props, u"inside")
							sens[devIdS] = self.updateSensProps(sens[devIdS], props, u"minStrikes")
							sens[devIdS] = self.updateSensProps(sens[devIdS], props, u"tuneCapacitor")
							sens[devIdS] = self.updateSensProps(sens[devIdS], props, u"calibrationDynamic")
							sens[devIdS] = self.updateSensProps(sens[devIdS], props, u"minNoiseFloor")
							sens[devIdS] = self.updateSensProps(sens[devIdS], props, u"noiseFloor")
							sens[devIdS] = self.updateSensProps(sens[devIdS], props, u"i2cAddress")
							sens[devIdS] = self.updateSensProps(sens[devIdS], props, u"displayEnable")
							sens[devIdS] = self.updateSensProps(sens[devIdS], props, u"freeParameter")
							sens[devIdS] = self.updateSensProps(sens[devIdS], props, u"gpioEcho")
							sens[devIdS] = self.updateSensProps(sens[devIdS], props, u"gpioTrigger")
							sens[devIdS] = self.updateSensProps(sens[devIdS], props, u"calibrateIfgt")
							sens[devIdS] = self.updateSensProps(sens[devIdS], props, u"setCalibration")
							sens[devIdS] = self.updateSensProps(sens[devIdS], props, u"sensorRefreshSecs")
							sens[devIdS] = self.updateSensProps(sens[devIdS], props, u"deltaDist")
							sens[devIdS] = self.updateSensProps(sens[devIdS], props, u"display")
							sens[devIdS] = self.updateSensProps(sens[devIdS], props, u"units")
							sens[devIdS] = self.updateSensProps(sens[devIdS], props, u"dUnits")
							sens[devIdS] = self.updateSensProps(sens[devIdS], props, u"multiply")
							sens[devIdS] = self.updateSensProps(sens[devIdS], props, u"offset")
							sens[devIdS] = self.updateSensProps(sens[devIdS], props, u"format")
							sens[devIdS] = self.updateSensProps(sens[devIdS], props, u"multiplyTemp")
							sens[devIdS] = self.updateSensProps(sens[devIdS], props, u"multTemp")
							sens[devIdS] = self.updateSensProps(sens[devIdS], props, u"offsetTemp")
							sens[devIdS] = self.updateSensProps(sens[devIdS], props, u"enableCalibration")
							sens[devIdS] = self.updateSensProps(sens[devIdS], props, u"multiplyPress")
							sens[devIdS] = self.updateSensProps(sens[devIdS], props, u"offsetPress")
							sens[devIdS] = self.updateSensProps(sens[devIdS], props, u"offsetGas")
							sens[devIdS] = self.updateSensProps(sens[devIdS], props, u"multiplyHum")
							sens[devIdS] = self.updateSensProps(sens[devIdS], props, u"offsetHum")
							sens[devIdS] = self.updateSensProps(sens[devIdS], props, u"input")
							sens[devIdS] = self.updateSensProps(sens[devIdS], props, u"spiAddress")
							sens[devIdS] = self.updateSensProps(sens[devIdS], props, u"gpioPin")
							sens[devIdS] = self.updateSensProps(sens[devIdS], props, u"resModel")
							sens[devIdS] = self.updateSensProps(sens[devIdS], props, u"gain")
							sens[devIdS] = self.updateSensProps(sens[devIdS], props, u"integrationTime")
							sens[devIdS] = self.updateSensProps(sens[devIdS], props, u"doAverage")
							sens[devIdS] = self.updateSensProps(sens[devIdS], props, u"LEDBlink")
							sens[devIdS] = self.updateSensProps(sens[devIdS], props, u"LEDmA")
							sens[devIdS] = self.updateSensProps(sens[devIdS], props, u"font")
							sens[devIdS] = self.updateSensProps(sens[devIdS], props, u"width")
							sens[devIdS] = self.updateSensProps(sens[devIdS], props, u"width1")
							sens[devIdS] = self.updateSensProps(sens[devIdS], props, u"width2")
							sens[devIdS] = self.updateSensProps(sens[devIdS], props, u"width3")
							sens[devIdS] = self.updateSensProps(sens[devIdS], props, u"pos1")
							sens[devIdS] = self.updateSensProps(sens[devIdS], props, u"pos2")
							sens[devIdS] = self.updateSensProps(sens[devIdS], props, u"pos3")
							sens[devIdS] = self.updateSensProps(sens[devIdS], props, u"pos3LinLog")
							sens[devIdS] = self.updateSensProps(sens[devIdS], props, u"displayEnable")
							sens[devIdS] = self.updateSensProps(sens[devIdS], props, u"logScale")
							sens[devIdS] = self.updateSensProps(sens[devIdS], props, u"displayText")
							sens[devIdS] = self.updateSensProps(sens[devIdS], props, u"intensity")
							sens[devIdS] = self.updateSensProps(sens[devIdS], props, u"freeParameter")
							sens[devIdS] = self.updateSensProps(sens[devIdS], props, u"refreshColor")
							sens[devIdS] = self.updateSensProps(sens[devIdS], props, u"deltaColor")
							sens[devIdS] = self.updateSensProps(sens[devIdS], props, u"refreshProximity")
							sens[devIdS] = self.updateSensProps(sens[devIdS], props, u"deltaProximity")
							sens[devIdS] = self.updateSensProps(sens[devIdS], props, u"enableGesture")
							sens[devIdS] = self.updateSensProps(sens[devIdS], props, u"interruptGPIO")
							sens[devIdS] = self.updateSensProps(sens[devIdS], props, u"actionLEFT")
							sens[devIdS] = self.updateSensProps(sens[devIdS], props, u"actionRIGHT")
							sens[devIdS] = self.updateSensProps(sens[devIdS], props, u"actionUP")
							sens[devIdS] = self.updateSensProps(sens[devIdS], props, u"actionDOWN")
							sens[devIdS] = self.updateSensProps(sens[devIdS], props, u"actionDoubleClick")
							sens[devIdS] = self.updateSensProps(sens[devIdS], props, u"actionLongClick")
							sens[devIdS] = self.updateSensProps(sens[devIdS], props, u"actionNEAR")
							sens[devIdS] = self.updateSensProps(sens[devIdS], props, u"actionFAR")
							sens[devIdS] = self.updateSensProps(sens[devIdS], props, u"actionPROXup")
							sens[devIdS] = self.updateSensProps(sens[devIdS], props, u"actionPROXdown")
							sens[devIdS] = self.updateSensProps(sens[devIdS], props, u"acuracyDistanceMode")
							sens[devIdS] = self.updateSensProps(sens[devIdS], props, u"actionShortDistance")
							sens[devIdS] = self.updateSensProps(sens[devIdS], props, u"actionShortDistanceLimit")
							sens[devIdS] = self.updateSensProps(sens[devIdS], props, u"actionMediumDistance")
							sens[devIdS] = self.updateSensProps(sens[devIdS], props, u"actionLongDistance")
							sens[devIdS] = self.updateSensProps(sens[devIdS], props, u"actionLongDistanceLimit")
							sens[devIdS] = self.updateSensProps(sens[devIdS], props, u"maxCurrent")
							sens[devIdS] = self.updateSensProps(sens[devIdS], props, u"integrationTime")
							sens[devIdS] = self.updateSensProps(sens[devIdS], props, u"rSet")
							sens[devIdS] = self.updateSensProps(sens[devIdS], props, u"SCLPin")
							sens[devIdS] = self.updateSensProps(sens[devIdS], props, u"SDOPin")
							sens[devIdS] = self.updateSensProps(sens[devIdS], props, u"deltaCurrent")
							sens[devIdS] = self.updateSensProps(sens[devIdS], props, u"deltaX")
							sens[devIdS] = self.updateSensProps(sens[devIdS], props, u"threshold")
							sens[devIdS] = self.updateSensProps(sens[devIdS], props, u"sensorLoopWait")
							sens[devIdS] = self.updateSensProps(sens[devIdS], props, u"resetPin")
							sens[devIdS] = self.updateSensProps(sens[devIdS], props, u"minSendDelta")
							sens[devIdS] = self.updateSensProps(sens[devIdS], props, u"magResolution")
							sens[devIdS] = self.updateSensProps(sens[devIdS], props, u"declinationOffset")
							sens[devIdS] = self.updateSensProps(sens[devIdS], props, u"magOffsetX")
							sens[devIdS] = self.updateSensProps(sens[devIdS], props, u"magOffsetY")
							sens[devIdS] = self.updateSensProps(sens[devIdS], props, u"magOffsetZ")
							sens[devIdS] = self.updateSensProps(sens[devIdS], props, u"magDivider")
							sens[devIdS] = self.updateSensProps(sens[devIdS], props, u"accelerationGain")
							sens[devIdS] = self.updateSensProps(sens[devIdS], props, u"magGain")
							sens[devIdS] = self.updateSensProps(sens[devIdS], props, u"devType")
							sens[devIdS] = self.updateSensProps(sens[devIdS], props, u"lowHighAs")
							sens[devIdS] = self.updateSensProps(sens[devIdS], props, u"risingOrFalling")
							sens[devIdS] = self.updateSensProps(sens[devIdS], props, u"deadTime")
							sens[devIdS] = self.updateSensProps(sens[devIdS], props, u"deadTimeBurst")
							sens[devIdS] = self.updateSensProps(sens[devIdS], props, u"timeWindowForBursts")
							sens[devIdS] = self.updateSensProps(sens[devIdS], props, u"minBurstsinTimeWindowToTrigger")
							sens[devIdS] = self.updateSensProps(sens[devIdS], props, u"inpType")
							sens[devIdS] = self.updateSensProps(sens[devIdS], props, u"bounceTime")
							sens[devIdS] = self.updateSensProps(sens[devIdS], props, u"timeWindowForLongEvents")
							sens[devIdS] = self.updateSensProps(sens[devIdS], props, u"timeWindowForContinuousEvents")
							sens[devIdS] = self.updateSensProps(sens[devIdS], props, u"pulseEveryXXsecsLongEvents")
							sens[devIdS] = self.updateSensProps(sens[devIdS], props, u"mac")
							sens[devIdS] = self.updateSensProps(sens[devIdS], props, u"type")
							sens[devIdS] = self.updateSensProps(sens[devIdS], props, u"updateIndigoTiming")

							dev.replacePluginPropsOnServer(props)

						if sens != {}:
							out[u"sensors"][sensor] = sens
							###if self.ML.decideMyLog(u"OfflineRPI"): self.ML.myLog( text =	 piS + "  sensor " + unicode(out[u"sensors"][sensor]) )
					except	Exception, e:
						self.ML.myLog( text =  u"makeParametersFile in Line '%s' has error='%s'" % (sys.exc_traceback.tb_lineno, e))
						self.ML.myLog( text =  unicode(sens))

				out[u"sensorList"] = self.RPI[piS][u"sensorList"]

				out[u"output"]={}			 
				for devOut in indigo.devices.iter("props.isOutputDevice"):
					typeId = devOut.deviceTypeId
					if typeId not in _GlobalConst_allowedOUTPUT: continue
					if not devOut.enabled: continue
					propsOut= devOut.pluginProps
					if u"piServerNumber" in propsOut and propsOut[u"piServerNumber"] != unicode(pi): continue
					if typeId.find(u"OUTPUTgpio") >-1:
						if typeId in self.RPI[piS][u"output"]:
							out[u"output"][typeId] = copy.deepcopy(self.RPI[piS][u"output"][typeId])
					else:
						devIdoutS = unicode(devOut.id)
						i2cAddress =""
						spiAddress =""
						devType	   =""
						if typeId not in out[u"output"]: out[u"output"][typeId]={}
						out[u"output"][typeId][devIdoutS] = [{}]
						
						if typeId.find(u"neopixelClock") >-1:
								if self.ML.decideMyLog(u"OutputDevice"): self.ML.myLog( text =	u" neoPixelClock: "+unicode(propsOut) )
								theDict={}
								theDict[u"ticks"] = {u"HH":{},"MM":{},"SS":{}}
								theDict[u"marks"] = {u"HH":{},"MM":{},"SS":{}}
								theDict[u"rings"] = []
								theDict[u"ticks"][u"HH"] = {u"ringNo":json.loads(u"["+propsOut[u"clockHHRings"]+u"]"),
														  u"RGB":json.loads(u"["+propsOut[u"clockHHRGB"]+u"]"),
														  u"npix":int(propsOut[u"clockHHnPIX"]),
														  u"blink":json.loads(propsOut[u"clockHHBlink"])}
								theDict[u"ticks"][u"MM"] = {u"ringNo":json.loads(u"["+propsOut[u"clockMMRings"]+u"]"),
														  u"RGB":json.loads(u"["+propsOut[u"clockMMRGB"]+u"]"),
														  u"npix":int(propsOut[u"clockMMnPIX"]),
														  u"blink":json.loads(propsOut[u"clockMMBlink"])}
								theDict[u"ticks"][u"SS"] = {u"ringNo":json.loads(u"["+propsOut[u"clockSSRings"]+u"]"),
														  u"RGB":json.loads(u"["+propsOut[u"clockSSRGB"]+u"]"),
														  u"npix":int(propsOut[u"clockSSnPIX"]),
														  u"blink":json.loads(propsOut[u"clockSSBlink"])}
								theDict[u"ticks"][u"DD"] = {u"ringNo":json.loads(u"["+propsOut[u"clockDDRings"]+u"]"),
														  u"RGB":json.loads(u"["+propsOut[u"clockDDRGB"]+u"]"),
														  u"npix":int(propsOut[u"clockDDnPIX"]),
														  u"blink":json.loads(propsOut[u"clockDDBlink"])}
														  
								theDict[u"marks"][u"HH"] = {u"ringNo":json.loads(u"["+propsOut[u"clockHHmarksRings"]+u"]"),
														  u"RGB":json.loads(u"["+propsOut[u"clockHHmarksRGB"]+u"]"),
														  u"marks":json.loads(propsOut[u"clockHHmarks"])}
								theDict[u"marks"][u"MM"] = {u"ringNo":json.loads(u"["+propsOut[u"clockMMmarksRings"]+u"]"),
														  u"RGB":json.loads(u"["+propsOut[u"clockMMmarksRGB"]+"]"),
														  u"marks":json.loads(propsOut[u"clockMMmarks"])}
								theDict[u"marks"][u"SS"] = {u"ringNo":json.loads(u"["+propsOut[u"clockSSmarksRings"]+u"]"),
														  u"RGB":json.loads(u"["+propsOut[u"clockSSmarksRGB"]+u"]"),
														  u"marks":json.loads(propsOut[u"clockSSmarks"])}
								theDict[u"marks"][u"DD"] = {u"ringNo":json.loads(u"["+propsOut[u"clockDDmarksRings"]+u"]"),
														  u"RGB":json.loads(u"["+propsOut[u"clockDDmarksRGB"]+"]"),
														  u"marks":json.loads(propsOut[u"clockDDmarks"])}
								try:
									theDict[u"extraLED"]= {u"ticks":json.loads(u"["+propsOut[u"clockEXTRAticks"]+u"]"),
														  u"RGB":json.loads(u"["+propsOut[u"clockEXTRARGB"]+u"]"),
														  u"blink":json.loads(propsOut[u"clockEXTRAblink"])}
								except:
									theDict[u"extraLED"]   = ""	  
								for jj in range(20):
									if u"ring"+str(jj) in propsOut:
										try: theDict[u"rings"].append(int(propsOut[u"ring"+str(jj)]))
										except:pass 
								nLEDs = sum(theDict[u"rings"])

								propsOut[u"devTypeLEDs"]		  = str(nLEDs)
								propsOut[u"devTypeROWs"]		  = u"1"
								propsOut[u"devType"]			  = u"1x"+str(nLEDs)
								theDict[u"speed"]				  = propsOut[u"speed"]
								theDict[u"speedOfChange"]		  = propsOut[u"speedOfChange"]
								theDict[u"GPIOsetA"]			  = propsOut[u"GPIOsetA"]
								theDict[u"GPIOsetB"]			  = propsOut[u"GPIOsetB"]
								theDict[u"GPIOsetC"]			  = propsOut[u"GPIOsetC"]
								theDict[u"GPIOup"]				  = propsOut[u"GPIOup"]
								theDict[u"GPIOdown"]			  = propsOut[u"GPIOdown"]
								theDict[u"timeZone"]			  = propsOut[u"timeZone"]

								out[u"output"][typeId][devIdoutS][0]=  copy.deepcopy(theDict)
								if self.ML.decideMyLog(u"OutputDevice"): self.ML.myLog( text =	u" neoPixelClock: "+json.dumps(theDict))
								
						if u"clockLightSensor" in propsOut:							out[u"clockLightSensor"] =propsOut[u"clockLightSensor"]
						out[u"output"][typeId][devIdoutS][0] = self.updateSensProps(out[u"output"][typeId][devIdoutS][0], propsOut, u"clockLightSet")
						out[u"output"][typeId][devIdoutS][0] = self.updateSensProps(out[u"output"][typeId][devIdoutS][0], propsOut, u"minLightNotOff")
						out[u"output"][typeId][devIdoutS][0] = self.updateSensProps(out[u"output"][typeId][devIdoutS][0], propsOut, u"devType")
						out[u"output"][typeId][devIdoutS][0] = self.updateSensProps(out[u"output"][typeId][devIdoutS][0], propsOut, u"devTypeROWs")
						out[u"output"][typeId][devIdoutS][0] = self.updateSensProps(out[u"output"][typeId][devIdoutS][0], propsOut, u"devTypeLEDs")
						out[u"output"][typeId][devIdoutS][0] = self.updateSensProps(out[u"output"][typeId][devIdoutS][0], propsOut, u"i2cAddress")
						out[u"output"][typeId][devIdoutS][0] = self.updateSensProps(out[u"output"][typeId][devIdoutS][0], propsOut, u"spiAddress")
						out[u"output"][typeId][devIdoutS][0] = self.updateSensProps(out[u"output"][typeId][devIdoutS][0], propsOut, u"font")
						out[u"output"][typeId][devIdoutS][0] = self.updateSensProps(out[u"output"][typeId][devIdoutS][0], propsOut, u"PIN_RST")
						out[u"output"][typeId][devIdoutS][0] = self.updateSensProps(out[u"output"][typeId][devIdoutS][0], propsOut, u"PIN_DC")
						out[u"output"][typeId][devIdoutS][0] = self.updateSensProps(out[u"output"][typeId][devIdoutS][0], propsOut, u"PIN_CE")
						out[u"output"][typeId][devIdoutS][0] = self.updateSensProps(out[u"output"][typeId][devIdoutS][0], propsOut, u"PIN_CS")
						out[u"output"][typeId][devIdoutS][0] = self.updateSensProps(out[u"output"][typeId][devIdoutS][0], propsOut, u"width")
						out[u"output"][typeId][devIdoutS][0] = self.updateSensProps(out[u"output"][typeId][devIdoutS][0], propsOut, u"mono")
						out[u"output"][typeId][devIdoutS][0] = self.updateSensProps(out[u"output"][typeId][devIdoutS][0], propsOut, u"mute")
						out[u"output"][typeId][devIdoutS][0] = self.updateSensProps(out[u"output"][typeId][devIdoutS][0], propsOut, u"highCut")
						out[u"output"][typeId][devIdoutS][0] = self.updateSensProps(out[u"output"][typeId][devIdoutS][0], propsOut, u"noiseCancel")
						out[u"output"][typeId][devIdoutS][0] = self.updateSensProps(out[u"output"][typeId][devIdoutS][0], propsOut, u"bandLimit")
						out[u"output"][typeId][devIdoutS][0] = self.updateSensProps(out[u"output"][typeId][devIdoutS][0], propsOut, u"DTCon")
						out[u"output"][typeId][devIdoutS][0] = self.updateSensProps(out[u"output"][typeId][devIdoutS][0], propsOut, u"PLLREF")
						out[u"output"][typeId][devIdoutS][0] = self.updateSensProps(out[u"output"][typeId][devIdoutS][0], propsOut, u"XTAL")
						out[u"output"][typeId][devIdoutS][0] = self.updateSensProps(out[u"output"][typeId][devIdoutS][0], propsOut, u"defFreq")
						out[u"output"][typeId][devIdoutS][0] = self.updateSensProps(out[u"output"][typeId][devIdoutS][0], propsOut, u"HLSI")
						out[u"output"][typeId][devIdoutS][0] = self.updateSensProps(out[u"output"][typeId][devIdoutS][0], propsOut, u"signalPin")
						out[u"output"][typeId][devIdoutS][0] = self.updateSensProps(out[u"output"][typeId][devIdoutS][0], propsOut, u"PWMchannel")
						out[u"output"][typeId][devIdoutS][0] = self.updateSensProps(out[u"output"][typeId][devIdoutS][0], propsOut, u"frequency")
						out[u"output"][typeId][devIdoutS][0] = self.updateSensProps(out[u"output"][typeId][devIdoutS][0], propsOut, u"DMAchannel")
						out[u"output"][typeId][devIdoutS][0] = self.updateSensProps(out[u"output"][typeId][devIdoutS][0], propsOut, u"OrderOfMatrix")
						out[u"output"][typeId][devIdoutS][0] = self.updateSensProps(out[u"output"][typeId][devIdoutS][0], propsOut, u"intensity")
						out[u"output"][typeId][devIdoutS][0] = self.updateSensProps(out[u"output"][typeId][devIdoutS][0], propsOut, u"flipDisplay")
 
						if typeId ==u"display":
							##self.ML.myLog( text = unicode(propsOut))
							extraPageForDisplay =[]
							#self.ML.myLog( text = unicode(propsOut))
							for ii in range(10):																			
								if u"extraPage"+unicode(ii)+u"Line0" in propsOut and "extraPage"+unicode(ii)+"Line1" in propsOut and u"extraPage"+unicode(ii)+u"Color" in propsOut:
									line0 = self.convertVariableOrDeviceStateToText(propsOut[u"extraPage"+unicode(ii)+u"Line0"])
									line1 = self.convertVariableOrDeviceStateToText(propsOut[u"extraPage"+unicode(ii)+u"Line1"])
									color = self.convertVariableOrDeviceStateToText(propsOut[u"extraPage"+unicode(ii)+u"Color"])
									extraPageForDisplay.append([line0,line1,color])
							out[u"output"][typeId][devIdoutS][0][u"extraPageForDisplay"]  =	 extraPageForDisplay
							out[u"output"][typeId][devIdoutS][0] = self.updateSensProps(out[u"output"][typeId][devIdoutS][0], propsOut, u"scrollxy")
							out[u"output"][typeId][devIdoutS][0] = self.updateSensProps(out[u"output"][typeId][devIdoutS][0], propsOut, u"scrollSpeed")
							out[u"output"][typeId][devIdoutS][0] = self.updateSensProps(out[u"output"][typeId][devIdoutS][0], propsOut, u"showDateTime")
							out[u"output"][typeId][devIdoutS][0] = self.updateSensProps(out[u"output"][typeId][devIdoutS][0], propsOut, u"intensity")
							out[u"output"][typeId][devIdoutS][0] = self.updateSensProps(out[u"output"][typeId][devIdoutS][0], propsOut, u"scrollxy")
							out[u"output"][typeId][devIdoutS][0] = self.updateSensProps(out[u"output"][typeId][devIdoutS][0], propsOut, u"flipDisplay")
							out[u"output"][typeId][devIdoutS][0] = self.updateSensProps(out[u"output"][typeId][devIdoutS][0], propsOut, u"displayResolution", elseSet="")

								
						if out[u"output"][typeId][devIdoutS] == [{}]:
							del out[u"output"][typeId][devIdoutS]
					if out[u"output"][typeId] == {}:
						del out[u"output"][typeId]


				out = self.writeJson(out, fName = self.userIndigoPluginDir + u"interfaceFiles/parameters." + piS , format=self.parametersFileSort )
 
		except	Exception, e:
				self.ML.myLog( text =  u"makeParametersFile in Line '%s' has error='%s'" % (sys.exc_traceback.tb_lineno, e))
		if retFile: return out
		return

####-------------------------------------------------------------------------####
	def updateSensProps(self, sens, props, param,elseSet=None):
		if param in props and props[param] !="":
			sens[param] = props[param]
		elif  param in props and props[param] == "" and elseSet	 == "--force--":
			sens[param] = ""
		elif elseSet  is not None:
			sens[param] = elseSet
			
		return sens

		
####-------------------------------------------------------------------------####
	def sendFilesToPiServerFTP(self, pi, fileToSend=u"updateParamsFTP.exp"):
		try:
			if self.ML.decideMyLog(u"UpdateRPI"): self.ML.myLog( text =	 u"enter  sendFilesToPiServerFTP #" + unicode(pi) +"  fileToSend:"+ fileToSend)
			if fileToSend==u"updateParamsFTP.exp": self.newIgnoreMAC = 0
			self.lastUpdateSend = time.time()
			if 5 < self.upDateNotSuccessful[pi] and self.upDateNotSuccessful[pi] < 10:
				if self.ML.decideMyLog(u"UpdateRPI"): self.ML.myLog( text =	 u"last updates were not successful wait, then try again")
				self.upDateNotSuccessful[pi] = 240	# = wait 3 minutes
				self.setRPIonline(pi,new=u"offline")
				return

			if self.RPI[unicode(pi)][u"piOnOff"] == "0": return
			if self.RPI[unicode(pi)][u"piUpToDate"] == []: return
			if self.RPI[unicode(pi)][u"ipNumberPi"] == "": return
			try:
				id = int(self.RPI[unicode(pi)][u"piDevId"])
				if id !=0 and not indigo.devices[id].enabled: 
					if self.ML.decideMyLog(u"OfflineRPI"): self.ML.myLog( text =  u"device "+indigo.devices[id].name+"not enabled, no sending to RPI")
					return
			except:
				pass
				
			if self.ML.decideMyLog(u"UpdateRPI"): self.ML.myLog( text =	 u"updating pi server config for # " + unicode(pi))
			pingR = self.testPing(self.RPI[unicode(pi)][u"ipNumberPiSendTo"])
			if pingR != 0:
				if self.ML.decideMyLog(u"OfflineRPI"): self.ML.myLog( text =  u" pi server # " + unicode(pi) + u"  PI# " + self.RPI[unicode(pi)][u"ipNumberPiSendTo"] + u"	not online - does not answer ping - , skipping update")
				self.upDateNotSuccessful[pi] += 1
				self.setRPIonline(pi,new="offline")
				return 1

			prompt = self.getPrompt(pi,fileToSend)

			cmd0 = "/usr/bin/expect '" + self.pathToPlugin + fileToSend + u"'" + u" "
			cmd0+=	self.RPI[unicode(pi)][u"userIdPi"] + " " + self.RPI[unicode(pi)][u"passwordPi"]+" " + prompt+" "
			cmd0+=	self.RPI[unicode(pi)][u"ipNumberPiSendTo"] + " "
			cmd0+=	unicode(pi) + " " + self.userIndigoPluginDir + " '" + self.pathToPlugin + "pi'" + " "+self.expectTimeout

			if self.ML.decideMyLog(u"UpdateRPI"): self.ML.myLog( text =	 u"updating pi server config for # " + unicode(pi) + u"	 executing\n" + cmd0)
			p = subprocess.Popen(cmd0, shell=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
			ret = p.communicate()

			if fileToSend == u"upgradeOpSysSSH.exp" :
				self.updatepiUpToDate(pi,ret,remove=fileToSend)
				self.upDateNotSuccessful[pi] = 0
				return
				
			if len(ret[1]) > 0:
				ret, ok = self.fixHostsFile(ret, pi)
				if not ok: return
				self.ML.myLog( text =  u"return code from fix " + unicode(ret) + u" trying again to configure PI")
				p = subprocess.Popen(cmd0, shell=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
				ret = p.communicate()
				
			if ret[0][-600:].find(u"sftp> ") > -1:
				self.updatepiUpToDate(pi,ret,remove=fileToSend)
			else:
				self.sleep(2)  # try it again after 2 seconds
				p = subprocess.Popen(cmd0, shell=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
				ret = p.communicate()
				if ret[0][-600:].find(u"sftp> ") > -1:
					self.updatepiUpToDate(pi,ret,remove=fileToSend)
				else:
					self.ML.myLog( text =  u"setup pi response (2) message \n" + ret[0])
					self.ML.myLog( text =  u"setup pi response (2) error   \n" + ret[1])
					self.upDateNotSuccessful[pi] += 1
					self.setRPIonline(pi,new="offline")
						
		except	Exception, e:
			self.ML.myLog( text =  u"sendFilesToPiServerFTP in Line '%s' has error='%s'" % (sys.exc_traceback.tb_lineno, e))
		return 1

	
####-------------------------------------------------------------------------####
	def fixHostsFile(self, ret, pi):
		try:	
			if self.ML.decideMyLog(u"UpdateRPI"): self.ML.myLog( text =	 u"setup pi response (1)\n" + unicode(ret))
			if ret[0].find(u".ssh/known_hosts:") > -1:
				if (subprocess.Popen(u"/usr/bin/csrutil status" , shell=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE).communicate()[0].find(u"enabled")) >-1:
					if self.ML.decideMyLog(u"bigErr"): 
						self.ML.myLog( errorType = u"bigErr", text =u'ERROR can not update hosts known_hosts file,	"/usr/bin/csrutil status" shows system enabled SIP; please edit manually with \n"nano '+self.MAChome+u'/.ssh/known_hosts"\n and delete line starting with '+self.RPI[unicode(pi)][u"ipNumberPiSendTo"])
						self.ML.myLog( errorType = u"bigErr", text =u"trying to from within plugin, if it happens again you need to do it manually")
					try:
						f=open(self.MAChome+u'/.ssh/known_hosts',u"r")
						lines= f.readlines()
						f.close()
						f=open(self.MAChome+u'/.ssh/known_hosts',u"w")
						for line in lines:
							if line.find(self.RPI[unicode(pi)][u"ipNumberPiSendTo"]) >-1:continue
							f.write(line+u"\n")
						f.close()
					except	Exception, e:
						self.ML.myLog( text =  u" fix did not work: error  in Line '%s' has error='%s'" % (sys.exc_traceback.tb_lineno, e))
						
					return ["",""], False
					
				fix1 = ret[0].split(u"Offending RSA key in ")
				if len(fix1) > 1:
					fix2 = fix1[1].split(u"\n")[0].strip(u"\n").strip(u"\n")
					fix3 = fix2.split(u":")
					if len(fix3) > 1:
						fixcode = u"/usr/bin/perl -pi -e 's/\Q$_// if ($. == " + fix3[1] + ");' " + fix3[0]
						self.ML.myLog( text =  u"wrong RSA key, trying to fix with: " + fixcode)
						p = subprocess.Popen(fixcode, shell=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
						ret = p.communicate()
 
		except	Exception, e:
			self.ML.myLog( text =  u"fixHostsFile in Line '%s' has error='%s'" % (sys.exc_traceback.tb_lineno, e))
		return ret, True




####-------------------------------------------------------------------------####
	def updatepiUpToDate(self, pi,ret,remove=""):

		if self.ML.decideMyLog(u"UpdateRPI"): 
			try:	self.ML.myLog( text =  u"updatepiUpToDate setup Pi: \n" + unicode(ret[0]).replace(u"\n\n", u"\n")+u"\n....\n"+ unicode(ret[0])[-300:].replace(u"\n\n", u"\n"))
			except: 
				indigo.server.log( u"updatepiUpToDate setup Pi: \n")
				indigo.server.log(ret[0])
		if remove !="":
			self.removeONErPiV(pi, u"piUpToDate", [remove])
		else:
			self.RPI[unicode(pi)][u"piUpToDate"] = []

		self.upDateNotSuccessful[pi] = 0
		self.RPI[unicode(pi)][u"lastMessage"] = time.time()
		self.setRPIonline(pi)



####-------------------------------------------------------------------------####
	def getPrompt(self, pi,fileToSend):
		prompt ="assword"

		if self.RPI[unicode(pi)][u"authKeyOrPassword"] == "login:":
			if fileToSend.find("FTP") >-1:
				prompt ="connect"
			else: 
				prompt ="login:"

		return prompt
####-------------------------------------------------------------------------####
	def sshToRPI(self, pi,fileToSend=""):
		try:

			if self.ML.decideMyLog(u"UpdateRPI"): self.ML.myLog( text =	 u"enter  sshToRPI #" + unicode(pi) +"	fileToSend:"+ fileToSend)
			if self.RPI[unicode(pi)][u"ipNumberPi"] == "": return
			if self.RPI[unicode(pi)][u"piOnOff"] == "0": return
			if 5 < self.upDateNotSuccessful[pi] and self.upDateNotSuccessful[pi] < 10:
				if self.ML.decideMyLog(u"OfflineRPI"): self.ML.myLog( text =  u"last updates were not successful wait, then try again")
				self.upDateNotSuccessful[pi] = 120	# = wait 1 minute
				return

			if self.testPing(self.RPI[unicode(pi)][u"ipNumberPi"]) != 0:
				if self.ML.decideMyLog(u"OfflineRPI"): self.ML.myLog( text =  u" pi server # " + unicode(pi) + u"  PI# " + self.RPI[unicode(pi)][
					u"ipNumberPiSendTo"] + "  not online - does not answer ping - , skipping update")
				self.upDateNotSuccessful[pi] += 1
				return 1
			try: 
				id = int(self.RPI[unicode(pi)][u"piDevId"])
				if id !=0 and not  indigo.devices[id].enabled: return
			except:
				pass


			if fileToSend in [u"shutdownSSH.exp",u"rebootSSH.exp",u"rebootFSSH.exp",u"resetOutputSSH.exp",u"shutdownSSH.exp"]:
				batch =" &"
			else: 
				batch =" "
				
			prompt = self.getPrompt(pi,fileToSend)
			
			cmd = "/usr/bin/expect '" + self.pathToPlugin + fileToSend+"' " + " " + self.RPI[unicode(pi)][u"userIdPi"] + " " + self.RPI[unicode(pi)][u"passwordPi"] + " " + prompt+" "+ self.RPI[unicode(pi)][u"ipNumberPiSendTo"]+ " "+self.expectTimeout+ " "+batch
			if self.ML.decideMyLog(u"UpdateRPI"): self.ML.myLog( text =	 fileToSend+u"	rPi# " + unicode(pi) + "\n" + cmd)
			if batch ==u" ":
				ret = subprocess.Popen(cmd, shell=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE).communicate()
				if self.ML.decideMyLog(u"UpdateRPI"): self.ML.myLog( text =	 u"response: " + unicode(ret) )
				if len(ret[1]) > 0:
					ret, ok = self.fixHostsFile(ret,pi)
					if not ok: return
					ret = subprocess.Popen(cmd, shell=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE).communicate()

			else:
				ret = subprocess.Popen(cmd, shell=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
				ret=[u"",""]
				
			self.updatepiUpToDate(pi,ret,remove=fileToSend)
			
			if fileToSend.find(u"shutdown") >-1: 
				self.upDateNotSuccessful[pi] = 0
				return
			if len(ret[1]) > 0:
				self.ML.myLog( text =  fileToSend+" Pi# "+unicode(pi) + unicode(ret).replace(u"\n\n", u"\n"))

			if fileToSend.find(u"getStats") >-1: 
				try:
					self.upDateNotSuccessful[pi] = 0
					ret1= ((ret[0].split(u"===fix==="))[-1])
					self.ML.myLog( text =  u"stats from rpi# "+unicode(pi)+" \n===fix===" + (ret1).replace(u"\n\n", u"\n"))
				except:
					self.ML.myLog( text =  u"stats from rpi# raw \n\n "+unicode(pi)+" \n" + ret[0].replace(u"\n\n", u"\n")+"\n errors:\n"+ret[1].replace(u"\n\n", u"\n"))
					
				return

		except	Exception, e:
			self.ML.myLog( text =  u"sshToRPI in Line '%s' has error='%s'" % (sys.exc_traceback.tb_lineno, e))
		return 1

####-------------------------------------------------------------------------####
	def configureWifi(self, pi):
		return
		try:
			self.setupFilesForPi()
			if self.RPI[unicode(pi)][u"ipNumberPi"] == "": return
			if self.testPing(self.RPI[unicode(pi)][u"ipNumberPiSendTo"]) != 0:
				if self.ML.decideMyLog(u"OfflineRPI"): self.ML.myLog( text =  u" pi server # " + unicode(pi) + u"  PI# " + self.RPI[unicode(pi)][
					u"ipNumberPiSendTo"] + u"  not online - does not answer ping - , skipping update")
				return 1

			prompt = self.getPrompt(pi,"wifi")

			cmd = "/usr/bin/expect '" + self.pathToPlugin + u"wifi.exp' " + u" " + self.RPI[unicode(pi)][u"userIdPi"] + u" " + self.RPI[unicode(pi)][u"passwordPi"]+ u" "+ prompt+" "+self.expectTimeout
			p = subprocess.Popen(cmd, shell=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
			ret = p.communicate()

			if len(ret[1]) > 0:
				self.ML.myLog( text =  u"setup wifi on pi error (1)\n" + unicode(ret[1]).replace(u"\n\n", u"\n"))
			else:
				if self.ML.decideMyLog(u"UpdateRPI"): self.ML.myLog( text =	 u"setup Pi ok: \n" + unicode(ret[0]).replace(u"\n\n", u"\n"))
		except	Exception, e:
			self.ML.myLog( text =  u"configureWifi in Line '%s' has error='%s'" % (sys.exc_traceback.tb_lineno, e))
		return

####-------------------------------------------------------------------------####
	def testPing(self, ipN):
		try:
			ss = time.time()
			ret = os.system(u"/sbin/ping  -c 1 -W 40 -o " + ipN) # send max 2 packets, wait 40 msec   if one gets back stop
			if self.ML.decideMyLog(u"UpdateRPI"): self.ML.myLog( text =  u" sbin/ping  -c 1 -W 40 -o " + ipN+" return-code: " + unicode(ret))
			
			#indigo.server.log(  ipN+"-1  "+ str(ret) +"  "+ str(time.time() - ss)  )
			
			if int(ret) ==0:  return 0
			self.sleep(0.1)
			ret = os.system(u"/sbin/ping  -c 1 -W 400 -o " + ipN)
			if self.ML.decideMyLog(u"UpdateRPI"): self.ML.myLog( text ="/sbin/ping  -c 1 -W 400 -o " + ipN+" ret-code: " + unicode(ret))
			
			#indigo.server.log(  ipN+"-2  "+ str(ret) +"  "+ str(time.time() - ss)  )
			
			if int(ret) ==0:  return 0
			return 1
		except	Exception, e:
		   self.ML.myLog( text =  u"testPing in Line '%s' has error='%s'" % (sys.exc_traceback.tb_lineno, e))
		
		#indigo.server.log(  ipN+"-3  "+ str(ret) +"  "+ str(time.time() - ss)  )
		return 1


####-------------------------------------------------------------------------####
	def printBeaconsIgnoredButton(self, valuesDict=None, typeId=""):

		############## list of beacons in history
		#				  1234567890123456	1234567890123456789012 1234567890 123456 123456789
		#				  75:66:B5:0A:9F:DB beacon-75:66:B5:0A:9   expired		   0	  1346
		self.ML.myLog( text =  u"#	defined beacons-------------", mType="pi configuration")
		self.ML.myLog( text =  u"#	Beacon MAC		  indigoName			   Status			  type	  txMin ignore sigDlt b-lvl	  LastUp[s] ExpTime updDelay   created",  mType=u"pi configuration")
		for status in [u"ignored", u""]:
			for type in _GlobalConst_typeOfBeacons:
				self.printBeaconInfoLine(status, type)


####-------------------------------------------------------------------------####
	def printConfig(self):

		self.ML.myLog( text =  u" ========== Parameters START ================",			  mType= u"pi configuration")
		self.ML.myLog( text =  u"data path used				   " + unicode(self.userIndigoPluginDir),						   mType= u"pi configuration")
		self.ML.myLog( text =  u"debugLevel Indigo			  -" + unicode(self.debugLevel)+"-",			   mType= u"pi configuration")
		self.ML.myLog( text =  u"debugLevel Pi				  -" + unicode(self.debugRPILevel)+"-",			   mType= u"pi configuration")
		self.ML.myLog( text =  u"automaticRPIReplacement	  " + unicode(self.automaticRPIReplacement),	   mType= u"pi configuration")
		self.ML.myLog( text =  u"myIp Number				  " + unicode(self.myIpNumber),					   mType= u"pi configuration")
		self.ML.myLog( text =  u"port# of indigoWebServer	  " + unicode(self.portOfServer),				   mType= u"pi configuration")
		self.ML.myLog( text =  u"indigo UserID				  " + "...." + unicode(self.userIdOfServer)[4:],   mType= u"pi configuration")
		self.ML.myLog( text =  u"indigo Password			  " + "...." + unicode(self.passwordOfServer)[4:], mType= u"pi configuration")
		self.ML.myLog( text =  u"WiFi key_mgmt				  " + unicode(self.key_mgmt),					   mType= u"pi configuration")
		self.ML.myLog( text =  u"WiFi Password				  " + "...." + unicode(self.wifiPassword)[4:],	   mType= u"pi configuration")
		self.ML.myLog( text =  u"WiFi SSID					  " + unicode(self.wifiSSID),					   mType= u"pi configuration")
		self.ML.myLog( text =  u"wifi OFF if ETH0			  " + unicode(self.wifiOFF),					   mType= u"pi configuration")
		self.ML.myLog( text =  u"Router IP					  " + unicode(self.routerIP),					   mType= u"pi configuration")
		self.ML.myLog( text =  u"Seconds UP to DOWN			  " + unicode(self.secToDown),					   mType= u"pi configuration")
		self.ML.myLog( text =  u"enable FINGSCAN interface	  " + unicode(self.enableFING),					   mType= u"pi configuration")
		self.ML.myLog( text =  u"rejct Beacons with txPower > " + unicode(self.txPowerCutoffDefault) + " dBm", mType= u"pi configuration")
		self.ML.myLog( text =  u"beacon indigo folder Name	  " + unicode(self.iBeaconFolderName),			   mType= u"pi configuration")
		self.ML.myLog( text =  u"accept newiBeacons			  " + unicode(self.acceptNewiBeacons),			   mType= u"pi configuration")
		self.ML.myLog( text =  u"accept junk beacons		  " + unicode(self.acceptJunkBeacons),			   mType= u"pi configuration")
		self.ML.myLog( text =  u"send Full UUID everytime	  " + unicode(self.sendFullUUID),				   mType= u"pi configuration")
		self.ML.myLog( text =  u"distance Units				  " + unicode(self.distanceUnits) + "; 1=m, 0.01=cm , 0.0254=in, 0.3=f, 0.9=y", mType= u"pi configuration")
		self.ML.myLog( text =  u"", mType="pi configuration")
		self.ML.myLog( text =  u"Parameters for each rPi	   ", mType="pi configuration")
		self.ML.myLog( text =  u"", mType="pi configuration")
		self.ML.myLog( text =  u" ========== EXPERT parameters for each PI:----------", mType= u"pi configuration")
		self.ML.myLog( text =  u"delete History after xSecs	  " + unicode(self.deleteHistoryAfterSeconds),			  mType="pi configuration")
		self.ML.myLog( text =  u"colct x secs bf snd		  " + unicode(self.sendAfterSeconds),  mType= u"pi configuration")
		self.ML.myLog( text =  u"port# on rPi 4 GPIO commands " + unicode(self.rPiCommandPORT),	   mType= u"pi configuration")
		self.ML.myLog( text =  u" "															  ,	   mType= u"pi configuration")
		
		self.ML.myLog( text =  u"  # R# 0/1 IP#				beacon-MAC		  indigoName				 Pos X,Y,Z	  indigoID UserID	  Password		 If-rPI-Hangs  SensorAttached",mType= u"pi configuration")
		for pi in range(_GlobalConst_numberOfRPI):
			if self.RPI[unicode(pi)][u"piDevId"] == 0:	 continue
			try:
				dev = indigo.devices[self.RPI[unicode(pi)][u"piDevId"]]
			except	Exception, e:
				if unicode(e).find(u"timeout waiting") > -1:
					self.ML.myLog( text =  u"printConfig in Line '%s' has error='%s'" % (sys.exc_traceback.tb_lineno, e))
					self.ML.myLog( text =  u"communication to indigo is interrupted")
					return

				self.ML.myLog( text =  u"printConfig in Line '%s' has error='%s'" % (sys.exc_traceback.tb_lineno, e))
				self.ML.myLog( text =  u"self.RPI[unicode(pi)][piDevId] not defined for pi: " + unicode(pi))
				continue
			line = unicode(pi).rjust(3) + " "
			line += self.RPI[unicode(pi)][u"piNumberReceived"].rjust(2) + u" "
			line += self.RPI[unicode(pi)][u"piOnOff"].ljust(3) + u" "
			line += self.RPI[unicode(pi)][u"ipNumberPi"].ljust(15) + u" "
			line += self.RPI[unicode(pi)][u"piMAC"].rjust(17) + " "
			line += (dev.name).ljust(25) + " "
			if pi < _GlobalConst_numberOfiBeaconRPI :
				line += (unicode(dev.states[u"PosX"]).split(u".")[0] + u"," + unicode(dev.states[u"PosY"]).split(u".")[0] + u"," + unicode(dev.states[u"PosZ"]).split(u".")[0]).rjust(10)
			else:
				line+=" ".rjust(10)
			line += unicode(self.RPI[unicode(pi)][u"piDevId"]).rjust(12) + u" "
			line += self.RPI[unicode(pi)][u"userIdPi"].ljust(10) + " "
			line += self.RPI[unicode(pi)][u"passwordPi"].ljust(15)
			line += self.RPI[unicode(pi)][u"enableRebootCheck"].ljust(14)
			line += unicode(self.RPI[unicode(pi)][u"sensorList"]).strip(u"[]").ljust(15)
			self.ML.myLog( text =  line, mType="pi configuration")



		self.ML.myLog( text =  u"", mType="pi configuration")
		if len(self.CARS[u"carId"]) > 0:
			self.ML.myLog( text =  u" ==========  CARS =========================", mType="pi configuration")
			self.ML.myLog( text =  u" CAR device-------------".ljust(31)+ u"HomeS	- AwayS".ljust(18)+ u"BAT-beacon".ljust(31)+ u"USB-beacon".ljust(31)+ u"KEY0-beacon".ljust(31)+ u"KEY1-beacon".ljust(31)+ u"KEY2-beacon".ljust(31), mType= u"pi configuration")
			bNames = [u"beaconBattery",u"beaconUSB",u"beaconKey0",u"beaconKey1",u"beaconKey2"]
			bN = [u" ",u" ",u" ",u" ",u" "]
			bF = [u" ",u" ",u" ",u" ",u" "]
			for dd in self.CARS[u"carId"]:
				carDevId = int(dd)
				carDev	= indigo.devices[carDevId]
				props	= carDev.pluginProps
				carName =(carDev.name).strip().ljust(30)
				for nn in range(len(bNames)):
					beaconType= bNames[nn]
					try: 
						beaconId = int(props[beaconType])
						if beaconId==0: continue
					except: continue
					beaconDev= indigo.devices[beaconId]
					propsB = beaconDev.pluginProps
					bN[nn] = (beaconDev.name)
					bF[nn]	  = propsB[u"fastDown"]
				homeSince = int(time.time() - self.CARS[u"carId"][dd][u"homeSince"])
				if homeSince > 9999999: homeSince= " "
				awaySince = int(time.time() - self.CARS[u"carId"][dd][u"awaySince"])
				if awaySince > 9999999: awaySince= " "
				homeSince = str(homeSince).ljust(7)
				awaySince = str(awaySince).ljust(7)
				out =  carName +" "+homeSince+" - "+awaySince
				for n in range(len(bNames)):
					out += " " + bN[n].strip().ljust(30) 
				self.ML.myLog( text =  out, mType= u"pi configuration")
				out =  "		 ....FastDown".ljust(30)+ " ".ljust(18)
				for n in range(len(bNames)):
					if bF[n] !=" ":
						out += " " + (bF[n]+"[sec]").strip().ljust(30)
					else:
						out += " " + (u" ").ljust(30)
					
				self.ML.myLog( text =  out, mType= u"pi configuration")
			self.ML.myLog( text =  u"", mType= u"pi configuration")

		############## list of beacons in history
		#				  1234567890123456	1234567890123456789012 1234567890 123456 123456789
		#				  75:66:B5:0A:9F:DB beacon-75:66:B5:0A:9   expired		   0	  1346
		if True:
			self.ML.myLog( text =  u" ==========  defined beacons ==============", mType= "pi configuration")
			self.ML.myLog( text =  u"#	Beacon MAC		  indigoName				 indigoId Status		   type	   txMin ignore sigDlt minSig	 LastUp[s] ExpTime updDelay	  created",
					   mType= "pi configuration")
			for status in [u"up", u"down", u"expired"]:
				for cType in _GlobalConst_typeOfBeacons:
					self.printBeaconInfoLine(status, cType)

			self.ML.myLog( text =  u"", mType= u"pi configuration")

	def printGroups(self):
		############## list groups with members
		if True:
			self.ML.myLog( text =  u"", mType= "pi configuration")
			self.ML.myLog( text =  u" ========== beacon groups	================", mType= u"pi configuration")
			self.ML.myLog( text =  u" GroupName	 members / counts ",mType= u"pi configuration")

			groupMemberNames={}
			for group in _GlobalConst_groupList:
				groupMemberNames[group]=""
			for beacon	in self.beacons:
				if self.beacons[beacon][u"note"].find(u"beacon") !=0: continue
				if self.beacons[beacon][u"indigoId"] ==0 or self.beacons[beacon][u"indigoId"] ==u"": continue
				try:
					dev= indigo.devices[self.beacons[beacon][u"indigoId"]]
				except:
					continue
					
				if dev.deviceTypeId !="beacon":	  continue
				if dev.states[u"groupMember"] == "": continue
				props= dev.pluginProps
				
				for group in _GlobalConst_groupList:
					if group in dev.states[u"groupMember"]:
						groupMemberNames[group]+= dev.name +"; "
			for group in _GlobalConst_groupList:
				self.ML.myLog( text = " "+ group+u"		"+ unicode(groupMemberNames[group]),mType= u"pi configuration")
				out=u"			  "
				out+=u"nHome: "	 + unicode(self.groupStatusList[group][u"nHome"])+u"; "
				out+=u"oneHome: "+ unicode(self.groupStatusList[group][u"oneHome"])+u"; "
				out+=u"allHome: "+ unicode(self.groupStatusList[group][u"allHome"])+u";	  "
				out+=u"nAway: "	 + unicode(self.groupStatusList[group][u"nAway"])+u"; "
				out+=u"oneAway: "+ unicode(self.groupStatusList[group][u"oneAway"])+u"; "
				out+=u"allAway: "+ unicode(self.groupStatusList[group][u"allAway"])+u"; "
				out+=u"members: "
				for member in self.groupStatusList[group][u"members"]:
					out+= member+u"; "
				self.ML.myLog( text = out,mType=u"pi configuration")
			self.ML.myLog( text =  u"", mType= u"pi configuration")
			

		############## families of beacons ignore list
		if len(self.beaconsIgnoreUUID) > 0:
			self.ML.myLog( text =  u"", mType= u"pi configuration")
			self.ML.myLog( text =  u" =========== Ignore this family of beacons with the following first 12 characters in their UUID:", mType=	u"pi configuration")

			for uuid in self.beaconsIgnoreUUID:
				self.ML.myLog( text = " "+ uuid, mType=	 u"pi configuration")

		############## iphone UUID list
		if len(self.beaconsUUIDtoIphone) > 0:
			self.ML.myLog( text =  u"", mType= u"pi configuration")
			self.ML.myLog( text =  u" ======  UUID to device LINKS ==============", mType= u"pi configuration")
			self.ML.myLog( text =  u"MAC--------------	IndigoName---------------		UUID-Major-Minor--------------------		  nickname--------------------	 ConstType",   mType=  u"pi configuration")
			for beacon in self.beaconsUUIDtoIphone:
				if beacon not in self.beacons:			  continue
				if self.beacons[beacon][u"indigoId"] == 0: continue
				try:
					name = indigo.devices[self.beacons[beacon][u"indigoId"]].name
				except	Exception, e:
					if unicode(e).find(u"timeout waiting") > -1:
						self.ML.myLog( text =  u"printGroups in Line '%s' has error='%s'" % (sys.exc_traceback.tb_lineno, e))
						self.ML.myLog( text =  u"communication to indigo is interrupted")
						return
					continue
				self.ML.myLog( text =  beacon + "  "+ name.ljust(30)+"	" + self.beaconsUUIDtoIphone[beacon][0].ljust(45) + " " + self.beaconsUUIDtoIphone[beacon][3].ljust(30)+ " " + self.beaconsUUIDtoIphone[beacon][1].ljust(15), mType=  u"pi configuration")

		self.ML.myLog( text = u" ==========	 Parameters END ================", mType=  u"pi configuration")
		return 

####-------------------------------------------------------------------------####
	def resetTcpipSocketStatsCALLBACK(self, valuesDict=None, typeId=""):
		self.dataStats={u"startTime":time.time(),"data":{}}

		
####-------------------------------------------------------------------------####
	def printTCPIPstats(self,all="yes"):

		############## tcpip stats 
		if self.socketServer is not None or True:
			if all == "yes":
					startDate= time.strftime(_defaultDateStampFormat,time.localtime(self.dataStats[u"startTime"]))
					self.ML.myLog( text =  u"", mType= "pi TCPIP socket")
					self.ML.myLog( text =  u"Stats for RPI-->INDIGO data transfers. Tracking started "+startDate+u". Report TX errors if time between errors is <"+ str(int(self.maxSocksErrorTime)/60)+u" Min", mType=	 u"pi TCPIP socket")
			self.ML.myLog( text =  u"IP				 name		  type		 first				 last					 #MSGs		 #bytes bytes/MSG  maxBytes bytes/min  MSGs/min", mType= "pi TCPIP socket")

			### self.dataStats[u"data"][IPN][name][type] = {u"firstTime":time.time(),"lastTime":0,"count":0,"bytes":0}

			secMeasured	  = max(1., (time.time() - self.dataStats[u"startTime"]))
			minMeasured	  = secMeasured/60.
			totBytes = 0.0
			totMsg	 = 0.0		
			maxBytes = 0	  
			for IPN in sorted(self.dataStats[u"data"].keys()):
				if all == "yes" or all==IPN:
					for name  in sorted(self.dataStats[u"data"][IPN].keys()):
						for type in sorted(self.dataStats[u"data"][IPN][name].keys()):
							if u"maxBytes"	not in self.dataStats[u"data"][IPN][name][type]: 
								self.resetDataStats()
								return 
							FT		= self.dataStats[u"data"][IPN][name][type][u"firstTime"]
							LT		= self.dataStats[u"data"][IPN][name][type][u"lastTime"] 
							
							dtFT	= datetime.datetime.fromtimestamp(FT).strftime(_defaultDateStampFormat)
							dtLT	= datetime.datetime.fromtimestamp(LT).strftime(_defaultDateStampFormat)
							bytesN	= self.dataStats[u"data"][IPN][name][type][u"bytes"]
							bytes	= unicode(bytesN).rjust(12)
							countN	= self.dataStats[u"data"][IPN][name][type][u"count"]
							count	= unicode(countN).rjust(9)
							maxBytN = self.dataStats[u"data"][IPN][name][type][u"maxBytes"]
							maxByt	= unicode(maxBytN).rjust(9)
							totMsg	  += countN
							totBytes  += bytesN
							try:	bytesPerMsg = unicode(int(self.dataStats[u"data"][IPN][name][type][u"bytes"]/float(self.dataStats[u"data"][IPN][name][type][u"count"]))).rjust(9)
							except: bytesPerMsg = u" ".rjust(9)

							try:	
									bytesPerMin = self.dataStats[u"data"][IPN][name][type][u"bytes"]/minMeasured
									bytesPerMin	  = (u"%9.1f"% (bytesPerMin)  ).rjust(9)
							except: bytesPerMin = u" ".rjust(9)
							try:	
									msgsPerMin	 = self.dataStats[u"data"][IPN][name][type][u"count"]/minMeasured
									msgsPerMin	 = (u"%9.2f"% (msgsPerMin)	).rjust(9)
							except: msgsPerMin	 = u" ".rjust(9)

							maxBytes   = max(maxBytN,maxBytes)

							self.ML.myLog( text = IPN.ljust(15)+u" "+name.ljust(12) +u" "+type.ljust(10)+u" " + dtFT+u" "+dtLT +u" "+ count+u" "+ bytes+ u" "+ bytesPerMsg+ u" "+ maxByt+ u" "+ bytesPerMin+ u" "+ msgsPerMin,mType=" ")
			if all == "yes" and totMsg >0: 
				bytesPerMsg	  = unicode(int(totBytes/totMsg)).rjust(9)
				bytesPerMin	  = (u"%9.1f"% (totBytes/minMeasured)  ).rjust(9)
				msgsPerMin	  = (u"%9.2f"% (totMsg/minMeasured)	   ).rjust(9)
				maxBytes	  =	 unicode(maxBytes).rjust(9)
				self.ML.myLog( text = "total																		  "+ str(int(totMsg)).rjust(10)+ str(int(totBytes)).rjust(13)+ u" "+ bytesPerMsg+ u" "+ maxBytes+ u" "+ bytesPerMin+ u" "+ msgsPerMin,mType=" ")
				self.ML.myLog( text =  u" ===  Stats for RPI --> INDIGO data transfers ==  END total time measured: "+str(int(time.strftime(u"%d", time.gmtime(secMeasured)))-1)+" "+time.strftime(u"%H:%M:%S", time.gmtime(secMeasured))+"; min measured: %2d"%minMeasured, mType=	 u"pi TCPIP socket")
		return 

####-------------------------------------------------------------------------####
	def printUpdateStats(self,):
		if len(self.dataStats[u"updates"]) ==0: return 
		nSecs = max(1,(time.time()-	 self.dataStats[u"updates"][u"startTime"]))
		nMin  = nSecs/60.
		startDate= time.strftime(_defaultDateStampFormat,time.localtime(self.dataStats[u"updates"][u"startTime"]))
		self.ML.myLog( text = "",mType=" " )
		self.ML.myLog( text = "===	measuring started at: " +startDate,mType="indigo update stats " )
		self.ML.myLog( text = "updates: %10d"%self.dataStats[u"updates"][u"devs"]  +u";	 updates/sec: %10.2f"%(self.dataStats[u"updates"][u"devs"]	/nSecs)+u";	 updates/minute: %10.2f"%(self.dataStats[u"updates"][u"devs"]  /nMin), mType=  u"	device ")
		self.ML.myLog( text = "updates: %10d"%self.dataStats[u"updates"][u"states"]+u";	 updates/sec: %10.2f"%(self.dataStats[u"updates"][u"states"]/nSecs)+u";	 updates/minute: %10.2f"%(self.dataStats[u"updates"][u"states"]/nMin), mType=  u"	states ")
		out = "(#states #updates #updates/min) "
		for ii in range(1,10):
			out+= "(%1d %1d %3.1f) "%(ii, self.dataStats[u"updates"][u"nstates"][ii], self.dataStats[u"updates"][u"nstates"][ii]/nMin) 
		out+= "(%1d+ %1d %3.1f)"%(10, self.dataStats[u"updates"][u"nstates"][10], self.dataStats[u"updates"][u"nstates"][10]/nMin) 
		self.ML.myLog( text = "updates: "+out, mType=  u"	#states")
		self.ML.myLog( text = "===	total time measured: " +time.strftime(u"%H:%M:%S", time.gmtime(nSecs)), mType= "indigo update stats" )
		return 


####-------------------------------------------------------------------------####
	def printBeaconInfoLine(self, status, type):

		cc = 0
		for beacon in self.beacons:
			if self.beacons[beacon][u"typeOfBeacon"] != type: continue
			if self.beacons[beacon][u"status"] != status: continue
			try:
				name = indigo.devices[self.beacons[beacon][u"indigoId"]].name
			except	Exception, e:
				if unicode(e).find(u"timeout waiting") > -1:
					self.ML.myLog( text =  u"printBeaconInfoLine in Line '%s' has error='%s'" % (sys.exc_traceback.tb_lineno, e))
					self.ML.myLog( text =  u"communication to indigo is interrupted")
					return
				continue

			cc += 1
			if len(name) > 22: name = name[:21] + ".."
			line = unicode(cc).ljust(2) + " " + beacon + " " + name.ljust(24) + " " +  unicode(self.beacons[beacon][u"indigoId"]).rjust(10) + " "+\
				   self.beacons[beacon][u"status"].ljust(10) + " " + \
				   self.beacons[beacon][u"typeOfBeacon"].rjust(10) + " " + \
				   unicode(self.beacons[beacon][u"beaconTxPower"]).rjust(8) + " " + \
				   unicode(self.beacons[beacon][u"ignore"]).rjust(6) + " " + \
				   unicode(self.beacons[beacon][u"signalDelta"]).rjust(6) + " " + \
				   unicode(self.beacons[beacon][u"minSignalCutoff"]).rjust(6) + " " + \
				   unicode(int(time.time() - self.beacons[beacon][u"lastUp"])).rjust(12) + " " + \
				   unicode(int(self.beacons[beacon][u"expirationTime"])).rjust(7) + " " + \
				   unicode(int(self.beacons[beacon][u"updateSignalValuesSeconds"])).rjust(8) + " " + \
				   unicode(self.beacons[beacon][u"created"]).ljust(19)
			self.ML.myLog( text =  line, mType= "pi configuration")

		if status != u"ignored":
			for beacon in self.beacons:
				if self.beacons[beacon][u"typeOfBeacon"] != type: continue
				if self.beacons[beacon][u"status"] != status: continue
				if self.beacons[beacon][u"ignore"] > 0: continue
				try:
					name = indigo.devices[self.beacons[beacon][u"indigoId"]].name
					continue
				except	Exception, e:
					if unicode(e).find(u"timeout waiting") > -1:
						self.ML.myLog( text =  u"printBeaconInfoLine in Line '%s' has error='%s'" % (sys.exc_traceback.tb_lineno, e))
						self.ML.myLog( text =  u"communication to indigo is interrupted")
						return

					name = ""
				cc += 1
				if len(name) > 22: name = name[:21] + ".."
				line = unicode(cc).ljust(2) + " " + beacon + " " + name.ljust(24) + " "	 + unicode(self.beacons[beacon][u"indigoId"]).rjust(10) + " "+\
					   self.beacons[beacon][u"status"].ljust(10) + " " +\
					   self.beacons[beacon][u"typeOfBeacon"].rjust(10) + " " +\
					   unicode(self.beacons[beacon][u"beaconTxPower"]).rjust(8) + " " +\
					   unicode(self.beacons[beacon][u"ignore"]).rjust(6) + " " +\
					   unicode(self.beacons[beacon][u"signalDelta"]).rjust(6) + " " +\
					   unicode(self.beacons[beacon][u"minSignalCutoff"]).rjust(6) + " " +\
					   unicode(self.beacons[beacon][u"batteryLevel"]).rjust(5) +\
					   unicode(int(time.time() - self.beacons[beacon][u"lastUp"])).rjust(12) + " " +\
					   unicode(int(self.beacons[beacon][u"expirationTime"])).rjust(7) + " " + \
					   unicode(int(self.beacons[beacon][u"updateSignalValuesSeconds"])).rjust(8) + " " + \
					   unicode(self.beacons[beacon][u"created"]).ljust(19)
				self.ML.myLog( text =  line, mType= "pi configuration")

		if status == u"ignored":
			for beacon in self.beacons:
				if self.beacons[beacon][u"typeOfBeacon"] != type: continue
				if self.beacons[beacon][u"status"] != status: continue
				if self.beacons[beacon][u"ignore"] == 1:
					name = " "
					cc += 1
					line = unicode(cc).ljust(2) + " " + beacon + " " + name.ljust(24) + " " +" ".ljust(10) + " "+ \
						   self.beacons[beacon][u"status"].ljust(10) + " " + \
						   self.beacons[beacon][u"typeOfBeacon"].rjust(10) + " " + \
						   unicode(self.beacons[beacon][u"beaconTxPower"]).rjust(8) + " " + \
						   unicode(self.beacons[beacon][u"ignore"]).rjust(6) + " " + \
						   unicode(self.beacons[beacon][u"signalDelta"]).rjust(6) + " " + \
						   unicode(self.beacons[beacon][u"minSignalCutoff"]).rjust(6) + " " + \
						   unicode(self.beacons[beacon][u"batteryLevel"]).rjust(5) + \
						   unicode(int(time.time() - self.beacons[beacon][u"lastUp"])).rjust(12) + " " + \
						   unicode(int(self.beacons[beacon][u"expirationTime"])).rjust(7) + " " + \
						   unicode(int(self.beacons[beacon][u"updateSignalValuesSeconds"])).rjust(8) + " " + \
						   unicode(self.beacons[beacon][u"created"]).ljust(19)
					self.ML.myLog( text =  line, mType=	 u"pi configuration")
			for beacon in self.beacons:
				if self.beacons[beacon][u"typeOfBeacon"] != type: continue
				if self.beacons[beacon][u"status"] != status:	  continue
				if self.beacons[beacon][u"ignore"] == 2:
					name = " "
					cc += 1
					line = unicode(cc).ljust(2) + " " + beacon + " " + name.ljust(24) + " " +" ".ljust(10) + " "+ \
						   self.beacons[beacon][u"status"].ljust(10) + " " + \
						   self.beacons[beacon][u"typeOfBeacon"].rjust(10) + " " + \
						   unicode(self.beacons[beacon][u"beaconTxPower"]).rjust(8) + " " + \
						   unicode(self.beacons[beacon][u"ignore"]).rjust(6) + " " + \
						   unicode(self.beacons[beacon][u"signalDelta"]).rjust(6) + " " + \
						   unicode(self.beacons[beacon][u"minSignalCutoff"]).rjust(6) + " " + \
						   unicode(self.beacons[beacon][u"batteryLevel"]).rjust(5) + \
						   unicode(int(time.time() - self.beacons[beacon][u"lastUp"])).rjust(12) + " " + \
						   unicode(int(self.beacons[beacon][u"expirationTime"])).rjust(7) + " " + \
						   unicode(int(self.beacons[beacon][u"updateSignalValuesSeconds"])).rjust(8) + " " + \
						   unicode(self.beacons[beacon][u"created"]).ljust(19)
					self.ML.myLog( text =  line, mType= "pi configuration")





####-------------------------------------------------------------------------####
	def updateRejectLists(self):
		cmd = self.pythonPath + u" '" + self.pathToPlugin + u"updateRejects.py' '" + self.userIndigoPluginDir + u"' & "
		if self.ML.decideMyLog(u"UpdateRPI"): self.ML.myLog( text =	 cmd)
		os.system(cmd)



##############################################################################################

####-------------------------------------------------------------------------####
	def addToStatesUpdateDict(self,devId,key,value,dev ="",newStates="",decimalPlaces="",uiValue="", force=False):
		devId=str(devId)
		try:
			try:

				for ii in range(5):
					if	self.executeUpdateStatesDictActive =="":
						break
					if self.ML.decideMyLog(u"Special"): 
						self.ML.myLog( text =  u"addToStatesUpdateDict	 #"+str(ii)+"# busy:"+ self.executeUpdateStatesDictActive.ljust(15)+" waiting:"+devId.ljust(12)+" key:"+str(key))
					self.sleep(0.05)
				self.executeUpdateStatesDictActive = devId+"-add"

					
				if devId not in self.updateStatesDict: 
					self.updateStatesDict[devId]={}
				if key in self.updateStatesDict[devId]:
					if value != self.updateStatesDict[devId][key]["value"]:
						self.updateStatesDict[devId][key] = {}
						if newStates !="": newStates[key] = {}
				self.updateStatesDict[devId][key] = {"value":value,"decimalPlaces":decimalPlaces,"force":force,"uiValue":uiValue}
				if newStates !="": newStates[key] = value

			except	Exception, e:
				if	unicode(e).find(u"UnexpectedNullErrorxxxx") >-1: return newStates
				self.ML.myLog( text =  u"addToStatesUpdateDict in Line '%s' has error='%s'" % (sys.exc_traceback.tb_lineno, e) )
				
			#self.updateStatesDict = local	  
		except	Exception, e:
			if	unicode(e).find(u"UnexpectedNullErrorxxxx") >-1: return newStates
			self.ML.myLog( text =  u"addToStatesUpdateDict in Line '%s' has error='%s'" % (sys.exc_traceback.tb_lineno, e) )
		self.executeUpdateStatesDictActive = ""
		return newStates

####-------------------------------------------------------------------------####
	def executeUpdateStatesDict(self,onlyDevID="0",calledFrom=""):
		try:
			if len(self.updateStatesDict) ==0: return
			#if "1929700622" in self.updateStatesDict: self.ML.myLog( text =  u"executeUpdateStatesList calledfrom: "+calledFrom +"; onlyDevID: " +onlyDevID +"; updateStatesList: " +unicode(self.updateStatesDict))
			onlyDevID = str(onlyDevID)

			for ii in range(5):
				if	self.executeUpdateStatesDictActive =="":
					break
				if self.ML.decideMyLog(u"Special"): 
					self.ML.myLog( text =  u"executeUpdateStatesDict #"+str(ii)+"# busy:"+ self.executeUpdateStatesDictActive.ljust(15)+" waiting:"+str(onlyDevID) )
				self.sleep(0.05)
					
			self.executeUpdateStatesDictActive = onlyDevID+"-exe"


			local ={}
			#		 
			if onlyDevID == "0":
				for ii in range(5):
					try: 
						local = copy.deepcopy(self.updateStatesDict)
						break
					except Exception, e:
						if self.ML.decideMyLog(u"Special"):
							self.ML.myLog( text =  u"executeUpdateStatesDict in Line '%s' has error='%s'" % (sys.exc_traceback.tb_lineno, e) )
							self.ML.myLog( text =  u"executeUpdateStatesDict del all calledFrom= "+ calledFrom )
						self.sleep(0.05)
				self.updateStatesDict={} 
				
			elif onlyDevID in self.updateStatesDict:
				for ii in range(5):
					try: 
						local = {onlyDevID: copy.deepcopy(self.updateStatesDict[onlyDevID])}
						break
					except Exception, e:
						if self.ML.decideMyLog(u"Special"):
							self.ML.myLog( text =  u"executeUpdateStatesDict in Line '%s' has error='%s'" % (sys.exc_traceback.tb_lineno, e) )
							self.ML.myLog( text =  u"calledFrom       = "+ calledFrom + ";	 onlyDevID= "+onlyDevID )
							self.ML.myLog( text =  u"lastCalledFrom   = "+ unicode(self.lastexecuteUpdateStatesDictCalledFrom) )
							self.ML.myLog( text =  u"local            = "+ unicode(local) )
							self.ML.myLog( text =  u"updateStatesDict = "+ unicode(self.updateStatesDict) )
							self.ML.myLog( text =  u"dev              = "+ indigo.devices[int(onlyDevID)].name )
						self.sleep(0.05)

				try: 
					del self.updateStatesDict[onlyDevID]
				except Exception, e:
					if self.ML.decideMyLog(u"Special"):
						self.ML.myLog( text =  u"executeUpdateStatesDict in Line '%s' has error='%s'" % (sys.exc_traceback.tb_lineno, e) )
						self.ML.myLog( text =  u"calledFrom       = "+ calledFrom + ";	 onlyDevID= "+onlyDevID )
						self.ML.myLog( text =  u"lastCalledFrom   = "+ unicode(self.lastexecuteUpdateStatesDictCalledFrom) )
						self.ML.myLog( text =  u"local            = "+ unicode(local) )
						self.ML.myLog( text =  u"updateStatesDict = "+ unicode(self.updateStatesDict) )
						self.ML.myLog( text =  u"dev              = "+ indigo.devices[int(onlyDevID)].name )
				
			else:
				self.executeUpdateStatesDictActive = ""
				return 
			self.executeUpdateStatesDictActive = ""

			self.lastexecuteUpdateStatesDictCalledFrom = (calledFrom,onlyDevID)
			
			changedOnly = {}
			trigStatus	   = ""
			trigRPIchanged = ""
			devnamechangedStat=""
			#devnamechangedRPI =""
			dateString = datetime.datetime.now().strftime(_defaultDateStampFormat)
			#self.ML.myLog( text =	u"local1 " +unicode(local))
			for devId in local:
				if onlyDevID !="0" and onlyDevID != devId: continue
				#self.ML.myLog( text =	u"executeUpdateStatesList in after if devId: " +devId )
				if len(local) > 0:
					dev =indigo.devices[int(devId)]
					nKeys =0
					for key in local[devId]:
						value = local[devId][key]["value"]
						if key =="sensorValue" and dev.name =="s-3-rainSensorRG11 ":
							indigo.server.log(" execute   sensorValue: "+unicode(local[devId][key]) )
						if key not in dev.states and key != "lastSensorChange":
							self.ML.myLog( text =  u"executeUpdateStatesDict: key: "+key+ u"  not in states for dev:"+dev.name)
						elif key in dev.states:
							upd = False
							if local[devId][key]["decimalPlaces"] != "": # decimal places present?
								try: 
									if round(value,local[devId][key]["decimalPlaces"]) !=	 round(dev.states[key],local[devId][key]["decimalPlaces"]):
										upd=True
								except: 
										upd=True
							else: 
								if unicode(value) != unicode(dev.states[key]):
										upd=True
							if local[devId][key]["force"]: 
										##indigo.server.log(dev.name+"	"+key+"	 "+unicode(local[devId]["keys"][key])  )
										upd=True
							if upd:
								nKeys +=1
								if devId not in changedOnly: changedOnly[devId]={}
								changedOnly[devId][key] = {"value":local[devId][key]["value"], "decimalPlaces":local[devId][key]["decimalPlaces"], "uiValue":local[devId][key]["uiValue"]}
								if "lastSensorChange" in dev.states and "lastSensorChange" not in changedOnly[devId]:
									nKeys +=1
									changedOnly[devId]["lastSensorChange"] = {"value":dateString,"decimalPlaces":"","uiValue":""}

					##if dev.name =="b-radius_3": self.ML.myLog( text =	u"changedOnly "+unicode(changedOnly))
					if devId in changedOnly and len(changedOnly[devId]) >0:
						chList=[]
						for key in changedOnly[devId]:
							if key ==u"status":	 
								self.statusChanged = max(1,self.statusChanged)
								value =changedOnly[devId][key]["value"]
								if u"lastStatusChange" in dev.states and u"lastStatusChange" not in changedOnly[devId]:
									try:	
										st	= unicode(value).lower() 
										if st in ["up","down","expired","on",u"off",u"1","0"]:
											props =dev.pluginProps
											if	self.enableBroadCastEvents == "all" or	("enableBroadCastEvents" in props and props["enableBroadCastEvents"] == "1" ):
												msg = {"action":"event", "id":str(dev.id), "name":dev.name, "state":"status", "valueForON":"up", "newValue":st}
												if self.ML.decideMyLog(u"BC"): self.ML.myLog( text = u"executeUpdateStatesDict	msg added :" + unicode(msg))
												self.sendBroadCastEventsList.append(msg)
											if dateString != dev.states[u"lastStatusChange"]:
												chList.append({u"key": u"lastStatusChange", u"value":dateString})
									except: pass

								if dev.deviceTypeId ==u"beacon" or dev.deviceTypeId.find(u"rPI") > -1 or dev.deviceTypeId == u"BLEconnect": 
									chList.append({u"key":"displayStatus","value":self.padDisplay(value)+dateString[5:] })
									if	 value == u"up":
										chList.append({u"key":"onOffState","value":True, "uiValue":self.padDisplay(value)+dateString[5:] })
										dev.updateStateImageOnServer(indigo.kStateImageSel.SensorOn)
									elif value == u"down":
										chList.append({u"key":"onOffState","value":False, "uiValue":self.padDisplay(value)+dateString[5:] })
										dev.updateStateImageOnServer(indigo.kStateImageSel.SensorOff)
									else:
										chList.append({u"key":"onOffState","value":False, "uiValue":self.padDisplay(value)+dateString[5:] })
										dev.updateStateImageOnServer(indigo.kStateImageSel.SensorTripped)

								if "lastSensorChange"  in dev.states and (key != "lastSensorChange" or ( key == "lastSensorChange" and nKeys >0)): 
									chList.append({u"key":"lastSensorChange","value":dateString})

							if changedOnly[devId][key]["uiValue"] != "":
								if changedOnly[devId][key][u"decimalPlaces"] != "" and key in dev.states:
									chList.append({u"key":key,"value":changedOnly[devId][key]["value"], u"decimalPlaces":changedOnly[devId][key]["decimalPlaces"],"uiValue":changedOnly[devId][key]["uiValue"]})
									#indigo.server.log(dev.name+"  into changed1 "+unicode(chList))
								else:
									chList.append({u"key":key,"value":changedOnly[devId][key]["value"],"uiValue":changedOnly[devId][key]["uiValue"]})
									#indigo.server.log(dev.name+"  into changed "+unicode(chList))
							else:
								if changedOnly[devId][key][u"decimalPlaces"] != "" and key in dev.states:
									chList.append({u"key":key,"value":changedOnly[devId][key]["value"], u"decimalPlaces":changedOnly[devId][key]["decimalPlaces"]})
								else:
									chList.append({u"key":key,"value":changedOnly[devId][key]["value"]})
							if dev.deviceTypeId ==u"beacon": 
								if key ==u"status": 
									trigStatus			 = dev.name
									devnamechangedStat	 = dev.name+ u"	 "+key+ u"	old="+str(dev.states[key])+ u"	 new="+str(changedOnly[devId][key]["value"])
								if key ==u"closestRPI": 
									trigRPIchanged		 = dev.name
									devnamechangedRPI	 = dev.name+ u"	 "+key+ u"	old="+str(dev.states[key])+ u"	 new="+str(changedOnly[devId][key]["value"]) 
								
						##if dev.name =="b-radius_3": self.ML.myLog( text =	u"chList "+unicode(chList))

						self.execUpdateStatesList(dev,chList)

				if trigStatus !="":
					try:
						indigo.variable.updateValue(self.ibeaconNameDefault+u"With_Status_Change",trigStatus)
					except	Exception, e:
							self.ML.myLog( text =  u"status changed: "+ unicode(devnamechangedStat))
							self.ML.myLog( text =  u"warning, ignoring state update(0): executeUpdateStatesList in Line '%s' has error='%s'" % (sys.exc_traceback.tb_lineno, e) + u" trying again")
							time.sleep(0.5)
							indigo.variable.updateValue(self.ibeaconNameDefault+u"With_Status_Change",trigStatus)
							self.ML.myLog( text =  u"worked 2. time")
					self.triggerEvent(u"someStatusHasChanged")

				if trigRPIchanged !="":
					try:
						indigo.variable.updateValue(self.ibeaconNameDefault+u"With_ClosestRPI_Change",trigRPIchanged)
					except	Exception, e:
							self.ML.myLog( text =  u"RPI   changed: "+ unicode(devnamechangedRPI))
							self.ML.myLog( text =  u"warning, ignoring state update(0): executeUpdateStatesList in Line '%s' has error='%s'" % (sys.exc_traceback.tb_lineno, e) + u" trying again")
							time.sleep(0.5)
							indigo.variable.updateValue(self.ibeaconNameDefault+u"With_ClosestRPI_Change",trigRPIchanged)
							self.ML.myLog( text =  u"worked 2. time")
					self.triggerEvent(u"someClosestrPiHasChanged")

						  
			#for devId in changedOnly:
			#	 dev =indigo.devices[int(devId)]
			#	 self.ML.myLog( text = "%14.3f"%time.time()+"  : "+ unicode(changedOnly[devId]),mType=dev.name.ljust(25)) 
		except	Exception, e:
				if	unicode(e).find(u"UnexpectedNullErrorxxxx") >-1: return 
				self.ML.myLog( text =  u"executeUpdateStatesDict warning, ignoring state update: in Line '%s' has error='%s'" % (sys.exc_traceback.tb_lineno, e) )
		self.executeUpdateStatesDictActive = ""
		return
		
####-------------------------------------------------------------------------####
	def execUpdateStatesList(self,dev,chList):
		try:
			if len(chList) ==0: return
			self.dataStats[u"updates"][u"devs"]	  +=1
			self.dataStats[u"updates"][u"states"] +=len(chList)
			self.dataStats[u"updates"][u"nstates"][min(len(chList),10)]+=1

			if self.indigoVersion >6:
				dev.updateStatesOnServer(chList)
				#self.ML.myLog( text = "execUpdateStatesList "+	 dev.name+"/"+str(dev.id)+":  "+unicode(chList)) 

			else:
				for uu in chList:
					dev.updateStateOnServer(uu[u"key"],uu[u"value"])
				

		except	Exception, e:
			self.ML.myLog( text =  u"execUpdateStatesList in Line '%s' has error='%s'" % (sys.exc_traceback.tb_lineno, e))
			self.ML.myLog( text =  u"chList: "+ unicode(chList))

###############################################################################################



####-------------------------------------------------------------------------####
	def convertVariableOrDeviceStateToText(self,textIn,enableEval=False):
		try:
			if not isinstance(textIn, (str, unicode)): return textIn
			oneFound=False
			for ii in range(5):	 # safety, no forever loop
				if textIn.find(u"%%v:") ==-1: break
				oneFound=True
				textIn,rCode = self.convertVariableToText0(textIn)
				if not rCode: break
			for ii in range(5):	 # safety, no forever loop
				if textIn.find(u"%%d:") ==-1: break
				oneFound=True
				textIn,rCode = self.convertDeviceStateToText0(textIn)
				if not rCode: break
			try:
				if enableEval and oneFound and (textIn.find(u"+")>-1 or	 textIn.find(u"-")>-1 or textIn.find(u"/")>-1 or textIn.find(u"*")>-1):
					textIn = unicode(eval(textIn))
			except: pass		
		except	Exception, e:
			if len(unicode(e)) > 5 :
				indigo.server.log(u"convertVariableOrDeviceStateToText in Line '%s' has error='%s'" % (sys.exc_traceback.tb_lineno, e))
		return textIn
		
####-------------------------------------------------------------------------####
	def convertVariableToText0(self,textIn):
		#  converts eg: 
		#"abc%%v:VariName%%xyz"	  to abcCONTENTSOFVARIABLExyz
		#"abc%%V:VariNumber%%xyz to abcCONTENTSOFVARIABLExyz
		try:
			try:
				start= textIn.find(u"%%v:")
			except:
				return textIn, False
		
			if start==-1:
				return textIn, False
			textOut= textIn[start+4:]
			end = textOut.find(u"%%")
			if end ==-1:
				return textIn, False
			var = textOut[:end]
			try:
				vText= indigo.variables[int(var)].value
			except:
				try:
					vText= indigo.variables[var].value
				except:
					return textIn, False

			try:
				if end+2 >= len(textOut)-1:
					textOut= textIn[:start]+vText
					return textOut, True
				textOut= textIn[:start]+vText+textOut[end+2:]
				return textOut, True
			except:
				return textIn, False
		except	Exception, e:
			if len(unicode(e)) > 5 :
				indigo.server.log(u"convertVariableToText0 in Line '%s' has error='%s'" % (sys.exc_traceback.tb_lineno, e))
		return textIn, False

		

####-------------------------------------------------------------------------####
	def convertDeviceStateToText0(self,textIn):
		#  converts eg: 
		#"abc%%d:devName:stateName%%xyz"   to abcdevicestatexyz
		#"abc%%V:devId:stateName%%xyz to abcdevicestatexyz
		try:
			try:
				start= textIn.find(u"%%d:")
			except:
				return textIn, False
			if start==-1:
				return textIn, False
			textOut= textIn[start+4:]

			secondCol = textOut.find(u":")
			if secondCol ==-1:
				return textIn, False
			dev		= textOut[:secondCol]
			textOut = textOut[secondCol+1:]
			percent = textOut.find(u"%%")
	
			if percent ==-1: return textIn, False
			state	= textOut[:percent]
			textOut = textOut[percent+2:]
			try:
				vText= unicode(indigo.devices[int(dev)].states[state])
			except:
				try:
					vText= unicode(indigo.devices[dev].states[state])
				except:
					return textIn, False
			try:
				if len(textOut)==0:
					textOut= textIn[:start]+vText
					return textOut, True
				textOut= textIn[:start]+vText+textOut
				return textOut, True
			except:
				return textIn, False
		except	Exception, e:
			if len(unicode(e)) > 5 :
				indigo.server.log(u"convertDeviceStateToText0 in Line '%s' has error='%s'" % (sys.exc_traceback.tb_lineno, e))
		return textIn, False



####-----------------  calc # of blnaks to be added to state column to make things look better aligned. ---------
	def padDisplay(self,status):
		if	 status == "up":		return status.ljust(11)
		elif status == "expired":	return status.ljust(8)
		elif status == "down":		return status.ljust(9)
		elif status == "changed":	return status.ljust(8)
		elif status == "double":	return status.ljust(8)
		elif status == "ignored":	return status.ljust(8)
		else:						return status.ljust(10)






##################################################################################################################
##################################################################################################################
##################################################################################################################
###################	 TCPIP listen section  receive data from RPI via socket comm  #####################

####-------------------------------------------------------------------------####
	def ipNumberOK(self,ipcheck):
		for pi in self.RPI:
			if self.RPI[pi][u"piOnOff"] == "0": continue
			if ipcheck == self.RPI[unicode(pi)][u"ipNumberPi"]:
				return True
		return False

####-------------------------------------------------------------------------####
	def handlesockReporting(self,IPN,nBytes,name,type,msg=""):

		try:
			if IPN not in self.dataStats[u"data"]:
				self.dataStats[u"data"][IPN]={}

			if name not in self.dataStats[u"data"][IPN]:
				self.dataStats[u"data"][IPN][name]={}
				
			if type not in self.dataStats[u"data"][IPN][name]:
				self.dataStats[u"data"][IPN][name][type] = {u"firstTime":time.time(),u"lastTime":time.time()-1000,u"count":0,u"bytes":0,"maxBytes":0}
			if u"maxBytes" not in self.dataStats[u"data"][IPN][name][type]:
				self.dataStats[u"data"][IPN][name][type][u"maxBytes"]=0
			self.dataStats[u"data"][IPN][name][type][u"count"] += 1
			self.dataStats[u"data"][IPN][name][type][u"bytes"] += nBytes
			self.dataStats[u"data"][IPN][name][type][u"lastTime"] = time.time()
			self.dataStats[u"data"][IPN][name][type][u"maxBytes"] = max(self.dataStats[u"data"][IPN][name][type][u"maxBytes"], nBytes)

			if type != u"ok" : # log if " errxxx" and previous event was less than xxx min ago	ago
				if time.time() - self.dataStats[u"data"][IPN][name][type][u"lastTime"]	< self.maxSocksErrorTime : # log if previous event was less than 10 minutes ago
					dtLT = datetime.datetime.fromtimestamp(self.dataStats[u"data"][IPN][name][type][u"lastTime"] ).strftime(_defaultDateStampFormat)
					self.ML.myLog( text = u"TCPIP socket error rate high for "+IPN+"/"+name +u" ; previous:"+dtLT )
					self.printTCPIPstats(all=IPN)
				self.saveTcpipSocketStats()
			elif "Socket" in self.debugLevel:
					pass
					#self.ML.myLog( text = "msg:" +	 msg )

				
		except	Exception, e:
			if len(unicode(e)) > 5 :
				indigo.server.log(u"handlesockReporting in Line '%s' has error='%s'" % (sys.exc_traceback.tb_lineno, e))
		return 
		

####-------------------------------------------------------------------------####
	def startTcpipListening(self, myIpNumber, indigoInputPORT):
			self.ML.myLog( text = u" ..	 starting tcpip stack" )
			socketServer = None
			stackReady	 = False
			if self.ML.decideMyLog(u"Socket"): self.ML.myLog( text = u"starting tcpip socket listener, for RPI data, might take some time, using: ip#= " + myIpNumber + ";	port#= " + str(indigoInputPORT) )
			tcpStart = time.time()	
			lsofCMD	 =u"/usr/sbin/lsof -i tcp:"+unicode(indigoInputPORT)
			ret = subprocess.Popen(lsofCMD, shell=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE).communicate()
			if self.ML.decideMyLog(u"Socket"): self.ML.myLog( text = u"lsof output:"+ unicode(ret))
			self.killHangingProcess(ret)
			for ii in range(50):  #	 gives port busy for ~ 60 secs if restart, new start it is fine, error message continues even if it works -- indicator =ok: if lsof gives port number  
				try:	
					socketServer = ThreadedTCPServer((myIpNumber,int(indigoInputPORT)), ThreadedTCPRequestHandler)
					if self.ML.decideMyLog(u"Socket"): self.ML.myLog( text = u"TCPIPsocket:: setting reuse	= 1 " )
					socketServer.socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
					if self.ML.decideMyLog(u"Socket"): self.ML.myLog( text = u"TCPIPsocket:: setting timout = 5 " )
					socketServer.socket.setsockopt(socket.SOL_SOCKET, socket.timeout, 5 )

				except	Exception, e:
					if self.ML.decideMyLog(u"Socket"): self.ML.myLog( text = u"TCPIPsocket:: %s	  try#: %i	time elapsed: %4.1f secs" % (e, ii,	 (time.time()-tcpStart) ) )
				try:
					ret = subprocess.Popen(lsofCMD, shell=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE).communicate()
					if len(ret[0]) >0: #  if lsof gives port number it works.. 
						if self.ML.decideMyLog(u"Socket"): self.ML.myLog( text = lsofCMD+"\n"+ ret[0].strip(u"\n"))
						TCPserverHandle = threading.Thread(target=socketServer.serve_forever)
						TCPserverHandle.daemon =True # don't hang on exit
						TCPserverHandle.start()
						break
				except	Exception, e:
					if unicode(e).find("serve_forever") ==-1:
						indigo.server.log(u"startTcpipListening in Line '%s' has error='%s'" % (sys.exc_traceback.tb_lineno, e))
					self.killHangingProcess(ret)
 
				if	 ii <=2:	tcpWaitTime = 7
				else:			tcpWaitTime = 1
				self.sleep(tcpWaitTime)
			try:	
				tcpName = TCPserverHandle.getName() 
				if self.ML.decideMyLog(u"Socket"): self.ML.myLog( text = u'startTcpipListening tcpip socket listener running; thread:#'+ tcpName)#	+ " try:"+ str(ii)+"  time elapsed:"+ str(time.time()-tcpStart) )
				stackReady = True
				self.ML.myLog( text = u" ..	 tcpip stack started" )
				#### does not work socketServer.settimeout(5)
				

			except	Exception, e:
				indigo.server.log(u"handlesockReporting in Line '%s' has error='%s'" % (sys.exc_traceback.tb_lineno, e))
				self.quitNow=u" tcpip stack did not load, restart"
			return	socketServer, stackReady

	def killHangingProcess(self, ret):

			test = (ret[0].strip("\n")).split("\n")

			if len(test) ==2:
				try: 
					pidTokill = int((test[1].split())[1])
					killcmd = "/bin/kill -9 "+str(pidTokill)
					if self.ML.decideMyLog(u"Socket"): self.ML.myLog( text = u"trying to kill hanging process with: "+killcmd)
					os.system(killcmd)
				except	Exception, e:
					indigo.server.log(u"handlesockReporting in Line '%s' has error='%s'" % (sys.exc_traceback.tb_lineno, e))


####-------------------------------------------------------------------------####
####-------------------------------------------------------------------------####
####-------------------------------------------------------------------------####
class ThreadedTCPRequestHandler(SocketServer.BaseRequestHandler):

####-------------------------------------------------------------------------####
	def handle(self):
		try:
			data0 =""
			dataS =[]
			tStart=time.time()
			len0 = 0
			name = "none"
			
			if	not indigo.activePlugin.ipNumberOK(self.client_address[0]) : 
				if indigo.activePlugin.ML.decideMyLog(u"Socket"): indigo.activePlugin.ML.myLog(text = u"TCPIP socket data receiving from "+ unicode(self.client_address) +u" not in accepted ip number list"  )
				indigo.activePlugin.handlesockReporting(self.client_address[0],0,u"unknown",u"errIP" )
				self.request.close()
				return
			
			# 3 secs should be enough even for slow network mostly one package, should all be send in one package
			self.request.settimeout(5) 

			try: # to catch timeout 
				while True: # until end of message
					buffer = self.request.recv(4096)#  max observed is ~ 3000 bytes
					if not buffer or len(buffer) == 0:#	 or len(buffer) < 4096: 
						break
					data0 += buffer
					len0  = len(data0)

					### check if package is complete:
					dataS = data0.split(u"x-6-a")
					if len(dataS) == 3 and int(dataS[0]) == len(dataS[2]): 
						break
						
					#safety valves
					if time.time() - tStart > 15: break 
					if	len0 > 13000: # check for overflow = 12 packages
						indigo.activePlugin.handlesockReporting(self.client_address[0],len0,u"unknown",u"errBuffOvfl" )
						self.request.close()
						return 
			except	Exception, e:
				e= unicode(e)
				self.request.settimeout(1) 
				self.request.send(u"error")
				self.request.close()
				if e.find("timed out") ==-1: 
					indigo.activePlugin.ML.myLog( text = u"ThreadedTCPRequestHandler in Line '%s' has error='%s'" % (sys.exc_traceback.tb_lineno, e) )
					indigo.activePlugin.handlesockReporting( self.client_address[0],len0,name,e[0:min(10,len(e))] )
				else:
					indigo.activePlugin.handlesockReporting( self.client_address[0],len0,name,u"timeout" )
				return
			self.request.settimeout(1) 
		   
			try: 
				## dataS =split message should look like:  len-TAG-name-TAG-data; -TAG- = x-6-a
				if len(dataS) !=3: # tag not found 
					if indigo.activePlugin.ML.decideMyLog(u"Socket"): indigo.activePlugin.ML.myLog( text = u"TCPIP socket  x-6-a  tag not found: "+data0[0:50] +"  ..  "+data0[-10:]) 
					try: self.request.send(u"error-tag missing")
					except: pass
					self.request.send(u"error")
					self.request.close()
					indigo.activePlugin.handlesockReporting(self.client_address[0],len0,name,u"errTag" )
					return

				expLength = int(dataS[0])
				name	  = dataS[1]
				lenData	  = len(dataS[2])


				if expLength != lenData: # expected # of bytes not received
					if lenData < expLength:
						if indigo.activePlugin.ML.decideMyLog(u"Socket"): indigo.activePlugin.ML.myLog( text = u"TCPIP socket length of {..} data too short, exp:"+dataS[0]+u";	 actual:"+ str(lenData)+u";	 name:"+name+"; "+dataS[2][0:50] +u"	..	  "+data0[-10:]) 
						try: self.request.send(u"error-lenDatawrong-"+str(lenData) )
						except: pass
						self.request.send(u"error")
						self.request.close()
						indigo.activePlugin.handlesockReporting(self.client_address[0],len0,name,u"tooShort" )
						return
					else:
						# check if we received a complete package + extra
						package1 = dataS[2][:expLength]
						try:
							json.loads(package1)
							dataS[2] = package1
							if indigo.activePlugin.ML.decideMyLog(u"Socket"): indigo.activePlugin.ML.myLog( text = u"TCPIP socket length of {..} data wrong -fixed- exp:"+dataS[0]+u";	actual:"+ str(lenData)+u";	name:"+name+"; "+dataS[2][0:50] +u"	   ..	 "+data0[-10:]) 
						except:
							if indigo.activePlugin.ML.decideMyLog(u"Socket"): indigo.activePlugin.ML.myLog( text = u"TCPIP socket length of {..} data wrong, exp:"+dataS[0]+u";	 actual:"+ str(lenData)+u";	 name:"+name+"; "+dataS[2][0:50] +u"	..	  "+data0[-10:]) 
							try: self.request.send(u"error-lenDatawrong-"+str(lenData) )
							except: pass
							self.request.send(u"error")
							self.request.close()
							indigo.activePlugin.handlesockReporting(self.client_address[0],len0,name,u"tooLong" )
							return

			except	Exception, e:
				if indigo.activePlugin.ML.decideMyLog(u"Socket"): indigo.activePlugin.ML.myLog( text = u"ThreadedTCPRequestHandler in Line '%s' has error='%s'" % (sys.exc_traceback.tb_lineno, e))
				if indigo.activePlugin.ML.decideMyLog(u"Socket"): indigo.activePlugin.ML.myLog( text = u"TCPIP socket, len:"+ unicode(len0)+u" data: "+ data0[0:50] +u"	   ..	 "+data0[-10:]) 
				if indigo.activePlugin.ML.decideMyLog(u"Socket"): indigo.activePlugin.handlesockReporting(self.client_address[0],len0,name,u"unknown" )
				self.request.send(u"error")
				self.request.close()
				return

			try: 
				dataJ = json.loads(dataS[2])  # dataJ = json object for data
			except	Exception, e:
				if indigo.activePlugin.ML.decideMyLog(u"Socket"): indigo.activePlugin.ML.myLog( text = u"TCPIP socket  json error;	len of data:"+str(len0)+"  "+ unicode(threading.currentThread())+u"	   time used:"+str(time.time()-tStart) ) 
				if indigo.activePlugin.ML.decideMyLog(u"Socket"): indigo.activePlugin.ML.myLog( text = data0[0:50]+u"	..	 "+data0[-10:] ) 
				try: self.request.send(u"error-Json-"+str(lenData) )
				except: pass
				indigo.activePlugin.handlesockReporting(self.client_address[0],len0,name,u"errJson" )
				self.request.send(u"error")
				self.request.close()
				return
			
			if name.find(u"pi_IN_") != 0 : 
				if indigo.activePlugin.ML.decideMyLog(u"Socket"): indigo.activePlugin.ML.myLog( text = u"TCPIP socket  listener bad name "+name )
				indigo.activePlugin.handlesockReporting(self.client_address[0],len0,name,u"badName" )
			else:

				#### now update Indigo dev/ states 
				indigo.activePlugin.addToDataQueue( name, dataJ,dataS[2] )
				indigo.activePlugin.handlesockReporting(self.client_address[0],len0,name,u"ok",msg=data0 )
			
			if indigo.activePlugin.ML.decideMyLog(u"Socket"): indigo.activePlugin.ML.myLog( text = u" sending ok to "+name.ljust(13) +"data: "+dataS[2][0:20] +".."+dataS[2][-20:])
			try:	self.request.send(u"ok-"+str(lenData) )
			except: pass
			self.request.close()



		except	Exception, e:
			if indigo.activePlugin.ML.decideMyLog(u"Socket"): indigo.activePlugin.ML.myLog( text = u"ThreadedTCPRequestHandler in Line '%s' has error='%s'" % (sys.exc_traceback.tb_lineno, e))
			if indigo.activePlugin.ML.decideMyLog(u"Socket"): indigo.activePlugin.ML.myLog( text = u"TCPIP socket "+ data0[0:50] ) 
			indigo.activePlugin.handlesockReporting(self.client_address[0],len0,name,u"unknown" )
			self.request.close()
		return
####-------------------------------------------------------------------------####
####-------------------------------------------------------------------------####
class ThreadedTCPServer(SocketServer.ThreadingMixIn, SocketServer.TCPServer):
	pass
	
###################	 TCPIP listen section  receive data from RPI via socket comm  end			 #################
##################################################################################################################
##################################################################################################################
##################################################################################################################

