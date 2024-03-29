#! /usr/bin/env python
# -*- coding: utf-8 -*-
####################
# pibeacon Plugin
# Developed by Karl Wachs
# karlwachs@me.com

#
#  compressed data
#  other IO
#
#  
#



#################
try:	import future
except:	pass

try:	import	six
except:	pass

try:	import builtins
except:	pass

try:	import past 
except:	pass

import os
import sys
import subprocess
import pwd
import datetime
import time
import json
import copy
import math
import socket
import threading
import traceback
import platform

try:
	import socketserver as SocketServer
except:
	import SocketServer

try: import Queue
except: import queue as Queue
import cProfile
import pstats
import logging
import zlib

import MAC2Vendor
from checkIndigoPluginName import checkIndigoPluginName 
#import pydevd_pycharm
#pydevd_pycharm.settrace('localhost', port=5678, stdoutToServer=True, stderrToServer=True)

try:
	# noinsp18480ection PyUnresolvedReferences
	import indigo
except ImportError:
	pass

try: 	long
except:	long = int

######### set new  pluginconfig defaults
# this needs to be updated for each new property added to pluginprops. 
# indigo ignores the defaults of new properties after first load of the plugin 
kDefaultPluginPrefs = {
				"iBeaconFolderName":							"Pi_Beacons_new",
				"iBeaconFolderVariablesName":					"piBeacons",
				"awayWhenNochangeInSeconds":					"600",
				"groupCountNameDefault":						"iBeacon_Count_",
				"groupName0":									"Family",
				"groupName1":									"Guests",
				"groupName2":									"Other1",
				"groupName3":									"Other2",
				"groupName4":									"Other3",
				"groupName5":									"Other4",
				"groupName6":									"Other5",
				"ibeaconNameDefault":							"iBeacon_",
				"SQLLoggingEnable":								"on-on",
				"secToDown":									"80",
				"setClostestRPItextToBlank":						"1",
				"sendFullUUID":									"1",
				"removeJunkBeacons":							"1",
				"checkBeaconParametersDisabled":				False,
				"myIpNumber":									"192.168.1.x",
				"IndigoOrSocket":								"socket",
				"portOfServer":									"8176",
				"indigoInputPORT":								"12087",
				"blockNonLocalIp":								False,
				"checkRPIipForReject":							True,
				"maxSocksErrorTime":							"10",
				"compressRPItoPlugin":							"20000",
				"userIdOfServer":								"",
				"passwordOfServer":								"",
				"apiKey":										"",
				"authentication":								"digest",
				"wifiSSID":										"",
				"wifiPassword":									"",
				"key_mgmt":										"NONE",
				"rebootIfNoMessagesSeconds":					"99999999999999",
				"enableRebootRPIifNoMessages":					"999999999",
				"eth0":											'{"on":"on", "useIP":"use"}',
				"wlan0":										'{"on":"dontChange", "useIP":"use"}',
				"piUpdateWindow":								"0",
				"rPiCommandPORT":								"9999",
				"rebootHour":									"1",
				"expectTimeout":								"15",
				"restartBLEifNoConnect":						"1",
				"rebootWatchDogTime":							"-1",
				"GPIOpwm":										"1",
				"rpiDataAcquistionMethod":						"hcidump",
				"tempUnits":									"Celsius",
				"tempDigits":									"1",
				"distanceUnits":								"1.0",
				"speedUnits":									"1.0",
				"pressureUnits":								"Pascal",
				"rainUnits":									"mm",
				"rainDigits":									"1",
				"lightningTimeWindow":							"10",
				"lightningNumerOfSensors":						"10",
				"beaconPositionsUpdateTime":					"-1",
				"beaconPositionsdeltaDistanceMinForImage":		"10",
				"beaconPositionsimageXscale":					"20",
				"beaconPositionsimageYscale":					"30",
				"beaconPositionsimageZlevels":					"0,5",
				"beaconPositionsimageDotsY":					"600",
				"beaconPositionsimageOutfile":					"",
				"beaconPositionsimageShowRPIs":					"0",
				"beaconShowExpiredBeacons":						"0",
				"beaconRandomBeacons":							"0",
				"beaconSymbolSize":								"1.0",
				"beaconLargeCircleSize":						"1.0",
				"beaconPositionsimageShowCaption":				"-1",
				"beaconPositionsShowTimeStamp":					"0",
				"beaconPositionsTitleText":						"text on Top",
				"beaconPositionsTitleTextPos":					"0,0",
				"beaconPositionsTitleTextRotation":				"0",
				"beaconPositionsTitleTextColor":				"#000000",
				"beaconPositionsTitleTextSize":					"12",
				"beaconPositionsCaptionTextSize":				"12",
				"beaconPositionsLabelTextSize":					"18",
				"beaconPositionstextPosLargeCircle":			"0",
				"beaconPositionsimageCompress":					"true",
				"mapUUIDtoNAME":								"0",
				"maxSizeOfLogfileOnRPI":						"10000000",
				"cycleVariables"								: True,
				"debugRPI":										"-1",
				"debugLogic":									False,
				"debugDevMgmt":									False,
				"debugBeaconData":								False,
				"debugSensorData":								False,
				"debugOutputDevice":							False,
				"debugUpdateRPI":								False,
				"debugSocketRPI":								False,
				"debugStartSocket":								False,
				"debugSocket":									False,
				"debugOfflineRPI":								False,
				"debugBC":										False,
				"debugBLE":										False,
				"debugCAR":										False,
				"debugPlotPositions":							False,
				"debugBatteryLevel":							False,
				"debugSQLlogger":								False,
				"debugSQLSuppresslog":							False,
				"debugBeep":									False,
				"debugGarageDoor":								False,
				"debugCars":									False,
				"debugUpdateTimeAndZone":						False,
				"debugSpecial":									False,
				"debugDelayedActions":							False,
				"debugall":										False,
				"showLoginTest":								False,
				"execcommandsListAction":						"delete",
				"getBatteryMethod":								"interactive",
				"do_cProfile":									"on/off/print"
		}



################################################################################
##########  Static parameters, not changed in pgm
################################################################################
_GlobalConst_numberOfiBeaconRPI	 = 20
_GlobalConst_numberOfRPI		 = 41
_rpiList 						 = [str(ii) for ii in range(_GlobalConst_numberOfRPI)]
_rpiBeaconList 					 = [str(ii) for ii in range(_GlobalConst_numberOfiBeaconRPI)]
_rpiSensorList					 = [str(ii) for ii in range(_GlobalConst_numberOfiBeaconRPI, _GlobalConst_numberOfRPI)]
_sqlLoggerDevTypes				 = ["isBeaconDevice", "isRPIDevice", "isRPISensorDevice", "isBLEconnectDevice", "isSensorDevice", "isBLESensorDevice","isBLElongConnectDevice"]
_sqlLoggerDevTypesNotSensor		 = _sqlLoggerDevTypes[:-1]

## this is to reduce writing to sql database 
_sqlLoggerIgnoreStates = {"isBeaconDevice":			"Pi_00_Time,Pi_01_Time,Pi_02_Time,Pi_03_Time,Pi_04_Time,Pi_05_Time,Pi_06_Time,Pi_07_Time,Pi_08_Time,Pi_09_Time,Pi_10_Time,Pi_11_Time,Pi_12_Time,Pi_13_Time,Pi_14_Time,Pi_15_Time,Pi_16_Time,Pi_17_Time,Pi_18_Time,Pi_19_Time,TxPowerReceived,typeOfBeacon,closestRPIText,closestRPITextLast,displayStatus,status,status_ui,lastUpdateBatteryLevel,sensorvalue_ui,updateReason,lastStatusChange,iBeacon,mfg_info"
						, "isRPIDevice":			"Pi_00_Time,Pi_01_Time,Pi_02_Time,Pi_03_Time,Pi_04_Time,Pi_05_Time,Pi_06_Time,Pi_07_Time,Pi_08_Time,Pi_09_Time,Pi_10_Time,Pi_11_Time,Pi_12_Time,Pi_13_Time,Pi_14_Time,Pi_15_Time,Pi_16_Time,Pi_17_Time,Pi_18_Time,Pi_19_Time,TxPowerReceived,typeOfBeacon,closestRPIText,closestRPITextLast,displayStatus,status,status_ui,online,i2cactive,sensorvalue_ui,updateReason,lastStatusChange,lastMessageFromRpi"
						, "isBLEconnectDevice":		"Pi_00_Time,Pi_01_Time,Pi_02_Time,Pi_03_Time,Pi_04_Time,Pi_05_Time,Pi_06_Time,Pi_07_Time,Pi_08_Time,Pi_09_Time,Pi_10_Time,Pi_11_Time,Pi_12_Time,Pi_13_Time,Pi_14_Time,Pi_15_Time,Pi_16_Time,Pi_17_Time,Pi_18_Time,Pi_19_Time,TxPowerReceived,closestRPIText,closestRPITextLast,displayStatus,status,status_ui,sensorvalue_ui,lastStatusChange"
						, "isRPISensorDevice":		"displayStatus,status,status_ui,sensorvalue_ui,lastStatusChange,lastMessageFromRpi"
						, "isBLESensorDevice":		"displayStatus,status,status_ui,sensorvalue_ui,lastStatusChange"
						, "isBLElongConnectDevice":	"displayStatus,status,status_ui,sensorvalue_ui,lastStatusChange"
						, "isSensorDevice":			"displayStatus,status,status_ui,sensorvalue_ui,lastStatusChange"}

_debugAreas = ["Logic", "DevMgmt", "BeaconData", "SensorData", "OutputDevice", "UpdateRPI", "OfflineRPI", "BLE", "CAR", "all", "Socket", "StartSocket", "Special", "PlotPositions", "SocketRPI", "BatteryLevel", "SQLlogger", "SQLSuppresslog", "Beep","UpdateTimeAndZone","GarageDoor","DelayedActions"]



_GlobalConst_emptyBeacon = {
	"indigoId": 0, "ignore": 0, "status": "up", "lastUp": 0, "note": "beacon", "expirationTime": 90,
	"created": 0, "updateWindow": 0, "updateSignalValuesSeconds": 0,
	"PosX": 0., "PosY": 0., "PosZ": 0., "typeOfBeacon": "other", "useOnlyPrioTagMessageTypes":"0", "beaconTxPower": +999,
	"lastBusy":20000,
	"enabled": True,
	"RPINumber": "-1",
	"showBeaconOnMap": 		"0", "showBeaconNickName": "", "showBeaconSymbolAlpha": "0.5", "showBeaconSymboluseErrorSize": "1", "showBeaconSymbolColor": "b",
	"receivedSignals":		[{"rssi":-999, "lastSignal": 0, "distance":99999} for kk in range(_GlobalConst_numberOfiBeaconRPI)]} #  for 10 RPI

_GlobalConst_emptyBeaconProps = {
	"note":							"beacon",
	"expirationTime":				90,
	"created":						0,
	"updateSignalValuesSeconds":	0,
	"signalDelta":					"999",
	"fastDown":				    	"-1",
	"minSignalOn":				    "-999",
	"minSignalOff":					"-999",
	"typeOfBeacon":					"other",
	"beaconTxPower":				999,
	"memberOfFamily":				False,
	"memberOfGuests":				False,
	"memberOfOther1":				False,
	"memberOfOther2":				False,
	"memberOfOther3":				False,
	"useOnlyPrioTagMessageTypes":	"0",
	"isBeaconDevice":				True,
	"SupportsStatusRequest":		False,
	"AllowOnStateChange":			False,
	"AllowSensorValueChange":		False,
	"ignore":						0,
	"batteryLevelCheckhours":		"4/12/20",
	"beaconBeepUUID":				"off",
	"SupportsBatteryLevel":			False,
	"version":					 	"",
	"batteryLevelUUID":				"off",
	"showBeaconOnMap": 				"0", "showBeaconNickName": "", "showBeaconSymbolType": ", ", "showBeaconSymbolAlpha": "0.5", "showBeaconSymboluseErrorSize": "1", "showBeaconSymbolColor": "b"
	}

_GlobalConst_emptyrPiProps	  ={
	"typeOfBeacon":					"rPI",
	"RPINumber":						"-1",
	"updateSignalValuesSeconds":	300,
	"beaconTxPower":				999,
	"SupportsBatteryLevel":			False,
	"sendToIndigoSecs":				90,
	"sensorRefreshSecs":			90,
	"deltaChangedSensor":			5,
	"SupportsStatusRequest":		False,
	"AllowOnStateChange":			False,
	"AllowSensorValueChange":		False,
	"memberOfFamily":				False,
	"memberOfGuests":				False,
	"memberOfOther1":				False,
	"memberOfOther2":				False,
	"memberOfOther3":				False,
	"PosXYZ":						"0.,0.,0.",
	"BLEserial":					"sequential",
	"shutDownPinInput" :			"-1",
	"expirationTime" :				"90",
	"rssiOffset" :					0,
	"isRPIDevice" :					True,
	"useOnlyPrioTagMessageTypes":  "0",
	"rpiDataAcquistionMethod":  	"hcidump",
	"shutDownPinOutput" :			"-1" }

_GlobalConst_fillMinMaxStates = ["countPerMinute", "Temperature", "AmbientTemperature", "Pressure", "Altitude", "Humidity", "visible", "ambient", "white", "illuminance", "IR", "CO2", "VOC", "INPUT_0", "rainRate", "Moisture", "INPUT","Conductivity","Formaldehyde","ambient","lux"]

_GlobalConst_emptyRPI =	  {
	"rpiType":					"rPi",
	"enableRebootCheck":		"restartLoop",
	"enableiBeacons":			"1",
	"input":					{},
	"ipNumberPi":				"",
	"output":					{},
	"passwordPi":				"raspberry",
	"piDevId":					0,
	"piMAC":					"",
	"piOnOff":					"0",
	"authKeyOrPassword":		"assword",
	"hostFileCheck":			"use",
	"piUpToDate": 				[],
	"sensorList": 				"0, ",
	"memberOfFamily":			False,
	"memberOfGuests":			False,
	"memberOfOther1":			False,
	"memberOfOther2":			False,
	"memberOfOther3":			False,
	"lastMessage":				0,
	"sendToIndigoSecs":			90,
	"sensorRefreshSecs":		20,
	"deltaChangedSensor":		5,
	"rssiOffset" :				0,
	"emptyMessages":			0,
	"deltaTime1":				100,
	"deltaTime2": 				100,
	"PosX": 					0,
	"PosY": 					0,
	"PosZ": 					0,
	"userIdPi": 				"pi"}


_GlobalConst_emptyRPISENSOR =	{
	"rpiType":					"rPiSensor",
	"enableRebootCheck":		"restartLoop",
	"enableiBeacons":			"0",
	"input":					{},
	"ipNumberPi":				"",
	"lastUpPi":					0,
	"output":					{},
	"passwordPi":				"raspberry",
	"authKeyOrPassword": 		"assword",
	"hostFileCheck": 			"use",
	"piDevId":					0,
	"piMAC":					"",
	"memberOfFamily":			False,
	"memberOfGuests":			False,
	"memberOfOther1":			False,
	"memberOfOther2":			False,
	"memberOfOther3":			False,
	"piOnOff":					"0",
	"piUpToDate":				[],
	"sensorList":				"0,",
	"lastMessage":				0,
	"sendToIndigoSecs":			90,
	"sensorRefreshSecs":		20,
	"deltaChangedSensor":		5,
	"emptyMessages":			0,
	"userIdPi": 				"pi"}

_GlobalConst_allGPIOlist = [
	  ("-1", "do not use")
	, ("1",  "GPIO01 ")
	, ("2",  "GPIO02 = pin # 3 -- I2C")
	, ("3",  "GPIO03 = pin # 5 -- I2C")
	, ("4",  "GPIO04 = pin # 7 -- ONE WIRE")
	, ("17", "GPIO17 = pin # 11 -- DHT")
	, ("27", "GPIO27 = pin # 13")
	, ("22", "GPIO22 = pin # 15")
	, ("10", "GPIO10 = pin # 19 -- SPS MOSI")
	, ("9",  "GPIO09 = pin # 21 -- SPS MISO")
	, ("11", "GPIO11 = pin # 23 -- SPS SCLK")
	, ("5",  "GPIO05 = pin # 29")
	, ("6",  "GPIO06 = pin # 31")
	, ("13", "GPIO13 = pin # 33")
	, ("19", "GPIO19 = pin # 35")
	, ("26", "GPIO26 = pin # 37")
	, ("14", "GPIO14 = pin # 8  -- TX - REBOOT PIN OUT")
	, ("15", "GPIO15 = pin # 10 -- RX - REBOOT PIN IN")
	, ("18", "GPIO18 = pin # 12")
	, ("23", "GPIO23 = pin # 16")
	, ("24", "GPIO24 = pin # 18")
	, ("25", "GPIO25 = pin # 22")
	, ("8",  "GPIO08 = pin # 24 -- SPS CE0")
	, ("7",  "GPIO07 = pin # 26 -- SPS CE1")
	, ("12", "GPIO12 = pin # 32")
	, ("16", "GPIO16 = pin # 36")
	, ("20", "GPIO20 = pin # 38")
	, ("21", "GPIO21 = pin # 40")]

_GlobalConst_ICONLIST	= [
	["None", "None"],
	["None", "Error"],
	["PowerOff", "PowerOn"],
	["DimmerOff", "DimmerOn"],
	["FanOff", "FanOn"],
	["SprinklerOff", "SprinklerOn"],
	["SensorOff", "SensorOn"],
	["SensorOn", "SensorTripped"],
	["SensorOff", "SensorTripped"],
	["EnergyMeterOff", "EnergyMeterOn"],
	["LightSensor", "LightSensorOn"],
	["MotionSensor", "MotionSensorTripped"],
	["DoorSensorClosed", "DoorSensorOpened"],
	["WindowSensorClosed", "WindowSensorOpened"],
	["TemperatureSensor", "TemperatureSensorOn"],
	["HumiditySensor", "HumiditySensorOn"],
	["HumidifierOff", "HumidifierOn"],
	["DehumidifierOff", "DehumidifierOn"],
	["TimerOff", "TimerOn"]]


_GlobalConst_beaconPlotSymbols = [
	"text", "dot", "smallCircle", "largeCircle", "square"] # label/text only, dot, small circle, circle prop to dist to rpi, square (for RPI)



_GlobalConst_allowedCommands = [
	"up", "down", "pulseUp", "pulseDown", "continuousUpDown", "analogWrite", "disable", "newMessage", "resetDevice",
	"getBeaconParameters", "startCalibration", "BLEAnalysis", "trackMac", "rampUp", "rampDown", "rampUpDown", "beepBeacon", "updateTimeAndZone"]	 # commands support for GPIO pins

_BLEsensorTypes =["BLERuuviTag",
				"BLEiBS01", "BLEiBS01T", "BLEiBS01RG", "BLEiBS03G", "BLEiBS03T", "BLEiBS03TP", "BLEiBS03RG", "BLEiTrackButton", "BLEShellyButton","BLEShellyMotion","BLEShellyDoor",
				"BLEaprilAccel", "BLEaprilTHL", "BLEThermopro", "BLETempspike",
				"BLEminewE8", "BLEminewS1TH", "BLEminewS1TT", "BLEminewS1Plus", "BLEminewAcc",
				"BLEiSensor-on", "BLEiSensor-onOff", "BLEiSensor-RemoteKeyFob", "BLEiSensor-TempHum",
				"BLEblueradio",
				"BLEMKKsensor",
				"BLESatech",
				"BLEswitchbotTempHum","BLEthermoBeacon", "BLEswitchbotMotion", "BLEswitchbotContact",
				"BLEXiaomiMiTempHumRound", "BLEXiaomiMiTempHumClock", "BLEXiaomiMiformaldehyde", "BLEgoveeTempHum"]

_BLEconnectSensorTypes = ["BLEinkBirdPool01B","BLEXiaomiMiVegTrug","BLEXiaomiMiTempHumSquare"]

_GlobalConst_allowedSensors = [
	 "ultrasoundDistance", "vl503l0xDistance", "vl503l1xDistance", "vl6180xDistance", "vcnl4010Distance", # dist / light
	 "apds9960",															  # dist gesture
	 "i2cTCS34725", "i2cTSL2561", "i2cVEML6070", "i2cVEML6030", "i2cVEML6040", "i2cVEML7700",		# light
	 "i2cVEML6075", "i2cIS1145", "i2cOPT3001",									# light
	 "BLEmyBLUEt",
	 "Wire18B20", "i2cTMP102", "i2cMCP9808", "i2cLM35A",						 # temp
	 "DHT", "i2cAM2320", "i2cSHT21", "si7021",						 # temp / hum
	 "BLEXiaomiMiTempHumSquare",
	 "BLEXiaomiMiVegTrug",
	 "BLEinkBirdPool01B",															# temp pool sensor
	 "i2cBMPxx", "i2cT5403", "i2cBMP280", "i2cMS5803",						 # temp / press
	 "i2cBMExx",															 # temp / press/ hum /
	 "bme680",																   # temp / press/ hum / gas
	 "bmp388",																   # temp / press/ alt
	 "tmp006",																   # temp rmote infrared
	 "tmp007",																   # temp rmote infrared
	 "tmp117",																   # temp rmote infrared
	 "max31865",															# prec temp i2c sensor
	 "pmairquality",
	 "amg88xx", "mlx90640",													# infrared camera
	 "lidar360",															# rd lidar
	 "ccs811",																   # co2 voc
	 "mhzCO2",																# co2 temp
	 "sensirionscd30",																# co2 temp
	 "sensirionscd40",																# co2 temp
	 "rainSensorRG11",
	 "moistureSensor",
	 "launchpgm",
	 "sgp30",																  # co2 voc
	 "sgp40",																  # voc
	 "as3935",																	# lightning sensor
	 "i2cMLX90614", "mlx90614",												   # remote	 temp &ambient temp
	 "ina219",																	 # current and V
	 "ina3221",																  # current and V 3 channels
	 "PCF8591",																  #  V 4 channels
	 "ADS1x15",																  #  V 4 channels
	 "as726x",																	 # rgb yellow orange violot
	 "MAX44009",																# illuminance sensor
	 "l3g4200", "bno055", "mag3110", "mpu6050", "hmc5883L", "mpu9255", "lsm303",	   # gyroscope
	 "INPgpio", "INPUTgpio-1", "INPUTgpio-4", "INPUTgpio-8", "INPUTgpio-26",		# gpio inputs
	 "INPUTtouch-1", "INPUTtouch-4", "INPUTtouch-8", "INPUTtouch-12", "INPUTtouch-16",		 # capacitor inputs
	 "INPUTtouch12-1", "INPUTtouch12-4", "INPUTtouch12-8", "INPUTtouch12-12",	   # capacitor inputs
	 "INPUTtouch16-1", "INPUTtouch16-4", "INPUTtouch16-8", "INPUTtouch16-16",	   # capacitor inputs
	 "INPUTRotarySwitchAbsolute", "INPUTRotarySwitchIncremental",
	 "spiMCP3008", "spiMCP3008-1", "i2cADC121",
	 "INPUTpulse", "INPUTcoincidence",
	 "mysensors", "myprogram",
	 "BLEconnect"]

_GlobalConst_lightSensors = [
	"i2cVEML6075", "i2cIS1145", "i2cOPT3001", "i2cTCS34725", "i2cTSL2561", "i2cVEML6070", "i2cVEML6040", "i2cVEML7700"]

_GlobalConst_i2cSensors	  = [
	"si7021", "bme680", "bmp388", "amg88xx", "mlx90640", "ccs811", "sgp30", "sgp40", "mlx90614", "ina219", "ina3221", "as726x", "as3935", "moistureSensor", "PCF8591", "ADS1x15",
	"l3g4200", "bno055", "mag3110", "mpu6050", "hmc5883L", "mpu9255", "lsm303", "vl6180xDistance", "vcnl4010Distance", "apds9960", "MAX44009"]

_GlobalConst_allowedOUTPUT = [
	"neopixel", "neopixel-dimmer", "neopixelClock", "OUTPUTswitchbotRelay", "OUTPUTswitchbotCurtain", "OUTPUTswitchbotCurtain3", "OUTPUTgpio-1-ONoff", "OUTPUTgpio-1", "OUTPUTi2cRelay", "OUTPUTgpio-4", "OUTPUTgpio-10", "OUTPUTgpio-26", "setMCP4725", "OUTPUTxWindows", "display", "setPCF8591dac", "setTEA5767", "sundial", "setStepperMotor", "FBHtempshow"]

_GlobalConst_groupList = ["Family", "Guests", "Other1", "Other2", "Other3", "Other4", "Other5"]
_GlobalConst_groupListDef = ["BEACON","PI","BLEconnect","SENSOR"]


_defaultDateStampFormat = "%Y-%m-%d %H:%M:%S"


################################################################################
# for dev states:

_devtypesToStates = {}
_devtypesToStates["rpiAndBeacon"] = {}
_devtypesToStates["rpiAndBeacon"]["iBeacon"] = "String"	
_devtypesToStates["rpiAndBeacon"]["updateReason"] = "String"	
_devtypesToStates["rpiAndBeacon"]["typeOfBeacon"] = "String"	
_devtypesToStates["rpiAndBeacon"]["vendorName"] = "String"	
_devtypesToStates["rpiAndBeacon"]["mfg_info"] = "String"	

_devtypesToStates["rpiAndBeaconAndBLEconnect"] = {}
for ii in range(_GlobalConst_numberOfiBeaconRPI):
	kk = "{:02d}".format(ii)
	_devtypesToStates["rpiAndBeaconAndBLEconnect"]["Pi_"+kk+"_Signal"] = "Integer"	
	_devtypesToStates["rpiAndBeaconAndBLEconnect"]["Pi_"+kk+"_Distance"] = "Real"	
	_devtypesToStates["rpiAndBeaconAndBLEconnect"]["Pi_"+kk+"_Time"] = "String"	

_devtypesToStates["rpiAndBeaconAndBLEconnect"]["PosX"] = "Real"	
_devtypesToStates["rpiAndBeaconAndBLEconnect"]["PosY"] = "Real"	
_devtypesToStates["rpiAndBeaconAndBLEconnect"]["PosZ"] = "Real"	
_devtypesToStates["rpiAndBeaconAndBLEconnect"]["lastUpdateFromRPI"] = "Integer"	
_devtypesToStates["rpiAndBeaconAndBLEconnect"]["closestRPI"] = "Integer"	
_devtypesToStates["rpiAndBeaconAndBLEconnect"]["closestRPIText"] = "String"	
_devtypesToStates["rpiAndBeaconAndBLEconnect"]["closestRPILast"] = "Integer"	
_devtypesToStates["rpiAndBeaconAndBLEconnect"]["closestRPITextLast"] = "String"	
_devtypesToStates["rpiAndBeaconAndBLEconnect"]["TxPowerReceived"] = "Integer"	
_devtypesToStates["rpiAndBeaconAndBLEconnect"]["TxPowerSet"] = "Integer"	
_devtypesToStates["rpiAndBeaconAndBLEconnect"]["groupMember"] = "String"	
_devtypesToStates["rpiAndBeaconAndBLEconnect"]["displayStatus"] = "String"	


_devtypesToStates["rpiAndSensorAndBeacon"] = {}
_devtypesToStates["rpiAndSensorAndBeacon"]["note"] = "String"	
_devtypesToStates["rpiAndSensorAndBeacon"]["displayStatus"] = "String"	
_devtypesToStates["rpiAndSensorAndBeacon"]["groupMember"] = "String"	



_devtypesToStates["rpiAndSensor"] = {}
_devtypesToStates["rpiAndSensor"]["RPI_throttled"] = "String"	
_devtypesToStates["rpiAndSensor"]["sensors_active"] = "String"	
_devtypesToStates["rpiAndSensor"]["op_sys"] = "String"	
_devtypesToStates["rpiAndSensor"]["last_boot"] = "String"	
_devtypesToStates["rpiAndSensor"]["last_masterStart"] = "String"	
_devtypesToStates["rpiAndSensor"]["rpi_type"] = "String"	
_devtypesToStates["rpiAndSensor"]["fan_OnTime_Percent"] = "String"	
_devtypesToStates["rpiAndSensor"]["i2c_active"] = "String"	
_devtypesToStates["rpiAndSensor"]["lastMessageFromRpi"] = "String"	
_devtypesToStates["rpiAndSensor"]["online"] = "String"	
_devtypesToStates["rpiAndSensor"]["lastStatusChange"] = "String"	


_devtypesToStates["rpi"] = {}
_devtypesToStates["rpi"]["RPI_throttled"] = "String"	
_devtypesToStates["rpi"]["sensors_active"] = "String"	
_devtypesToStates["rpi"]["closestiBeacon"] = "String"	
_devtypesToStates["rpi"]["closestiBeaconLast"] = "String"	
_devtypesToStates["rpi"]["iBeacon"] = "String"	
_devtypesToStates["rpi"]["hciInfo_beacons"] = "String"	
_devtypesToStates["rpi"]["hciInfo"] = "String"	
_devtypesToStates["rpi"]["hciInfo_beep"] = "String"	
_devtypesToStates["rpi"]["hciInfo_BLEconnect"] = "String"	


_devtypesToStates["beacon"] = {}
_devtypesToStates["beacon"]["lastStatusChange"] = "String"	
_devtypesToStates["beacon"]["isBeepable"] = "String"	
_devtypesToStates["beacon"]["vendorName"] = "String"	
_devtypesToStates["beacon"]["lastUpdateBatteryLevel"] = "String"	
_devtypesToStates["beacon"]["lastBatteryReplaced"] = "String"	
_devtypesToStates["beacon"]["iBeacon"] = "String"	


_devtypesToStates["BLEconnect"] = {}
_devtypesToStates["BLEconnect"]["note"] = "String"	
_devtypesToStates["BLEconnect"]["lastUp"] = "String"	
_devtypesToStates["BLEconnect"]["lastStatusChange"] = "String"	
_devtypesToStates["BLEconnect"]["lastStatusChange"] = "String"	

_devtypesToStates["beaconOn"] = {}
_devtypesToStates["beaconOn"]["txPower"] = "Integer"	
_devtypesToStates["beaconOn"]["rssi"] = "Integer"	
_devtypesToStates["beaconOn"]["trigger"] = "String"	
_devtypesToStates["beaconOn"]["lastSensorChange"] = "String"	
_devtypesToStates["beaconOn"]["groupMember"] = "String"
_devtypesToStates["beaconOn"]["lastUpdateFromRPI"] = "String"	


_devtypesToStates["beaconSensor"] = {}
_devtypesToStates["beaconSensor"]["txPower"] = "Integer"	
_devtypesToStates["beaconSensor"]["rssi"] = "Integer"	
_devtypesToStates["beaconSensor"]["trigger"] = "String"	


_devtypesToStates["sensor"] = {}
_devtypesToStates["sensor"]["lastSensorChange"] = "String"	
_devtypesToStates["sensor"]["groupMember"] = "String"
_devtypesToStates["sensor"]["lastUpdateFromRPI"] = "String"	

_devtypesToStates["allDevHaveThese"] = {}
_devtypesToStates["allDevHaveThese"]["status"] = "String"	
_devtypesToStates["allDevHaveThese"]["created"] = "String"	

_devtypesToStates["output"] = {} 


_devtypesToStates["realSensor"] 	= {"":"Real",		"MinToday":"Real",		"MaxYesterday":"Real",		"MinYesterday":"Real",		"MaxToday":"Real",		"AveToday":"Real",		"AveYesterday":"Real",		"MeasurementsToday":"Number",	"MeasurementsYesterday":"Integer",	"ChangeMinutes05":"Real",		"ChangeMinutes10":"Real",		"ChangeMinutes20":"Real",		"ChangeHours01":"Real",		"ChangeHours02":"Real",		"ChangeHours06":"Real",		"ChangeHours12":"Real"  ,	"ChangeHours24":"Real",		"ChangeHours48":"Real"}
_devtypesToStates["integerSensor"]	= {"":"Integer",	"MinToday":"Integer",	"MaxYesterday":"Integer",	"MinYesterday":"Integer",	"MaxToday":"Integer",	"AveToday":"Integer",	"AveYesterday":"Integer",	"MeasurementsToday":"Integer",	"MeasurementsYesterday":"Integer",	"ChangeMinutes05":"Integer",	"ChangeMinutes10":"Integer",	"ChangeMinutes20":"Integer",	"ChangeHours01":"Integer",	"ChangeHours02":"Integer",	"ChangeHours06":"Integer",	"ChangeHours12":"Integer",	"ChangeHours24":"Integer",	"ChangeHours48":"Integer"}
_devtypesToStates["String"]		= {"":"String"}
_devtypesToStates["boolean"]	= {"":"boolean"}

_addingstates = {}
_addingstates["Conductivity"]					= {"addTag":True, "States":_devtypesToStates["realSensor"]}
_addingstates["Moisture"]						= {"addTag":True, "States":_devtypesToStates["realSensor"]}
_addingstates["AirQuality"]						= {"addTag":False, "States":{"AirQuality":"Real"}}
_addingstates["distance"]						= {"addTag":False, "States":{"distance":"Real"}}
_addingstates["distanceEvent"]					= {"addTag":False, "States":{"distanceEvent":"String"}}
_addingstates["distanceRaw"]					= {"addTag":False, "States":{"distanceRaw":"Real"}}
_addingstates["trigger"]						= {"addTag":False, "States":{"trigger":"String"}}
_addingstates["stopped"]						= {"addTag":False, "States":{"stopped":"boolean"}}
_addingstates["speed"]							= {"addTag":False, "States":{"speed":"Real"}}
_addingstates["rotation"]						= {"addTag":False, "States":{"rotation":"Integer"}}
_addingstates["illuminance"]					= {"addTag":True, "States":_devtypesToStates["realSensor"]}
_addingstates["AmbientTemperature"]				= {"addTag":True, "States":_devtypesToStates["realSensor"]}
_addingstates["Temperature"]					= {"addTag":True, "States":_devtypesToStates["realSensor"]}
_addingstates["CO2"] 							= {"addTag":True, "States":_devtypesToStates["integerSensor"]}
_addingstates["Humidity"]						= {"addTag":True, "States":_devtypesToStates["integerSensor"]}
_addingstates["Pressure"]						= {"addTag":True, "States":_devtypesToStates["realSensor"]}
_addingstates["VOC"]							= {"addTag":True, "States":_devtypesToStates["realSensor"]}
_addingstates["Formaldehyde"]					= {"addTag":True, "States":_devtypesToStates["realSensor"]}
_addingstates["switchbotOutput"]				= {"addTag":True, "States":_devtypesToStates["realSensor"]}

_addingstates["rpiAndSensorAndBeacon"]			= {"addTag":False, "States":_devtypesToStates["rpiAndSensorAndBeacon"]}
_addingstates["rpiAndBeaconAndBLEconnect"]		= {"addTag":False, "States":_devtypesToStates["rpiAndBeaconAndBLEconnect"]}
_addingstates["rpiAndBeacon"]					= {"addTag":False, "States":_devtypesToStates["rpiAndBeacon"]}
_addingstates["rpiAndSensor"]					= {"addTag":False, "States":_devtypesToStates["rpiAndSensor"]}
_addingstates["beacon"]							= {"addTag":False, "States":_devtypesToStates["beacon"]}
_addingstates["BLEconnect"]						= {"addTag":False, "States":_devtypesToStates["BLEconnect"]}
_addingstates["rPI"]							= {"addTag":False, "States":_devtypesToStates["rpi"]}
_addingstates["allDevHaveTheseStates"]			= {"addTag":False, "States":_devtypesToStates["allDevHaveThese"]}
_addingstates["beaconSensorStates"]				= {"addTag":False, "States":_devtypesToStates["beaconSensor"]}
_addingstates["sensorStates"]					= {"addTag":False, "States":_devtypesToStates["sensor"]}
_addingstates["beaonOn"]						= {"addTag":False, "States":_devtypesToStates["beaconOn"]}
_addingstates["output"]							= {"addTag":False, "States":_devtypesToStates["output"]}
_addingstates["lastBatteryReplaced"]			= {"addTag":False, "States":{"lastBatteryReplaced":"String"}}

_addingstates["accelerationX"]					= {"addTag":False, "States":{"accelerationX":"Integer"}}
_addingstates["accelerationY"]					= {"addTag":False, "States":{"accelerationY":"Integer"}}
_addingstates["accelerationZ"]					= {"addTag":False, "States":{"accelerationZ":"Integer"}}
_addingstates["accelerationVectorDelta"]		= {"addTag":False, "States":{"accelerationVectorDelta":"Integer"}}
_addingstates["accelerationTotal"]				= {"addTag":False, "States":{"accelerationTotal":"Integer"}}
_addingstates["accelerationXYZMaxDelta"]		= {"addTag":False, "States":{"accelerationXYZMaxDelta":"Integer"}}


_addingstates["trigger"]						= {"addTag":False, "States":{"trigger":"String"}}
_addingstates["packetId"]						= {"addTag":False, "States":{"packetId":"Integer"}}
_addingstates["currentEvent"]					= {"addTag":False, "States":{"currentEvent":"String"}}
_addingstates["previousEvent"]					= {"addTag":False, "States":{"previousEvent":"String"}}
_addingstates["currentEventType"]				= {"addTag":False, "States":{"currentEventType":"String"}}
_addingstates["previousEventType"]				= {"addTag":False, "States":{"previousEventType":"String"}}

_stateListToDevTypes = {}
_stateListToDevTypes["trigger"]					= {"BLEShellyDoor":1,"BLEShellyMotion":1,"BLEShellyButton":1}
_stateListToDevTypes["packetId"]				= {"BLEShellyDoor":1,"BLEShellyMotion":1,"BLEShellyButton":1}
_stateListToDevTypes["currentEvent"]			= {"BLEShellyDoor":1,"BLEShellyMotion":1,"BLEShellyButton":1}
_stateListToDevTypes["previousEvent"]			= {"BLEShellyDoor":1,"BLEShellyMotion":1,"BLEShellyButton":1}
_stateListToDevTypes["currentEventType"]		= {"BLEShellyButton":1}
_stateListToDevTypes["previousEventType"]		= {"BLEShellyButton":1}


_stateListToDevTypes["Conductivity"]			= {"BLEXiaomiMiVegTrug":1 }
_stateListToDevTypes["Moisture"]				= {"BLEXiaomiMiVegTrug":1, "moistureSensor":1 }
_stateListToDevTypes["speed"]					= {"vcnl4010Distance":1, "vl6180xDistance":1, "ultrasoundDistance":1, "vl503l1xDistance":1, "vl503l0xDistance":1}
_stateListToDevTypes["distanceEvent"]			= {"vcnl4010Distance":1, "vl6180xDistance":1, "ultrasoundDistance":1, "vl503l1xDistance":1, "vl503l0xDistance":1}
_stateListToDevTypes["trigger"]					= {"vcnl4010Distance":1, "vl6180xDistance":1, "ultrasoundDistance":1, "vl503l1xDistance":1, "vl503l0xDistance":1}
_stateListToDevTypes["distance"]				= {"vcnl4010Distance":1, "vl6180xDistance":1, "ultrasoundDistance":1, "vl503l1xDistance":1, "vl503l0xDistance":1}
_stateListToDevTypes["distanceRaw"]				= {"vcnl4010Distance":1, "vl6180xDistance":1, "ultrasoundDistance":1, "vl503l1xDistance":1, "vl503l0xDistance":1}
_stateListToDevTypes["rotation"]				= {"BLEShellyDoor":1}
_stateListToDevTypes["illuminance"]				= {"apds9960":1, "BLEXiaomiMiVegTrug":1, "BLEaprilTHL":1, "i2cTCS34725":1, "MAX44009":1, "as726x":1, "i2cOPT3001":1, "i2cTSL2561":1, "moistureSensor":1, "vcnl4010Distance":1, "vl6180xDistance":1,"BLEShellyDoor":1,"BLEShellyMotion":1}
_stateListToDevTypes["Temperature"]				= {"BLEMKKsensor":1,"DHT":1, "mlx90614":1, "BLERuuviTag":1, "BLEiBS01T":1, "BLEiBS03T":1, "BLEiBS03TP":1, "BLEminewS1TH":1, "BLEthermoBeacon":1, "BLEXiaomiMiVegTrug":1, "BLEXiaomiMiformaldehyde":1, "BLEXiaomiMiTempHumClock":1, "BLEXiaomiMiTempHumRound":1, "BLEXiaomiMiTempHumSquare":1, "BLEgoveeTempHum":1, "BLEminewS1Plus":1, "BLEinkBirdPool01B":1, "BLEaprilTHL":1, "BLEThermopro":1, "BLETempspike":1, "BLESatech":1, "BLEiSensor-TempHum":1, "BLEswitchbotTempHum":1, "Wire18B20":1, "i2cTMP102":1, "i2cMCP9808":1, "i2cLM35A":1, "ccs811":1, "i2cT5403":1, "i2cMS5803":1, "i2cBMPxx":1, "i2cBMP280":1, "bmp388":1, "i2cSHT21":1, "i2cAM2320":1, "i2cBMExx":1, "bme680":1, "si7021":1, "tmp006":1, "tmp007":1, "tmp117":1, "max31865":1, "sensirionscd30":1, "sensirionscd40":1, "rPI":1, "rPI-Sensor":1}
_stateListToDevTypes["AmbientTemperature"]		= {"mlx90614":1, "tmp006":1, "tmp007":1, "BLEiBS03TP":1, "amg88xx":1}
_stateListToDevTypes["Humidity"]				= {"BLEMKKsensor":1,"BLEiBS01T":1, "DHT":1, "BLERuuviTag":1, "BLEminewS1TH":1, "BLEXiaomiMiformaldehyde":1, "BLEthermoBeacon":1, "BLEXiaomiMiTempHumClock":1, "BLEXiaomiMiTempHumRound":1, "BLEXiaomiMiTempHumSquare":1, "BLEgoveeTempHum":1, "BLEminewS1Plus":1, "BLEaprilTHL":1, "BLEThermopro":1, "BLESatech":1, "BLEiSensor-TempHum":1, "BLEswitchbotTempHum":1, "i2cSHT21":1, "i2cAM2320":1, "i2cBMExx":1, "bme680":1, "si7021":1,  "sensirionscd30":1, "sensirionscd40":1}
_stateListToDevTypes["CO2"]						= {"sensirionscd30":1, "sensirionscd40":1, "sgp30":1, "mhzCO2":1, "ccs811":1 }
_stateListToDevTypes["Pressure"]				= {"BLERuuviTag":1, "i2cT5403":1, "i2cMS5803":1, "i2cBMPxx":1, "i2cBMP280":1, "bmp388":1, "i2cBMExx":1, "bme680":1 }
_stateListToDevTypes["VOC"]						= {"sgp30":1, "sgp40":1, "ccs811":1, "bmp388":1}
_stateListToDevTypes["AirQuality"]				= {"bme680":1}
_stateListToDevTypes["Formaldehyde"]			= {"BLEXiaomiMiformaldehyde":1 }
_stateListToDevTypes["rpiAndBeacon"]			= {"beacon":1, "rPI":1}
_stateListToDevTypes["rpiAndSensorAndBeacon"]	= {"beacon":1, "rPI":1, "rPI-Sensor":1}
_stateListToDevTypes["rpiAndSensor"]			= {"rPI":1, "rPI-Sensor":1}
_stateListToDevTypes["rPI"]						= {"rPI":1}
_stateListToDevTypes["beacon"]					= {"beacon":1}
_stateListToDevTypes["BLEconnect"]				= {"BLEconnect":1}
_stateListToDevTypes["beaconOn"]				= {"BLEiSensor-onOff":1, "BLEiSensor-on":1, "BLEiSensor-RemoteKeyFob":1, "BLEswitchbotMotion":1, "BLEswitchbotContact":1}
_stateListToDevTypes["beaconSensorStates"]		= {"BLERuuviTag":1, "BLEiBS03T":1, "BLEmyBLUEt":1, "BLEiBS03TP":1, "BLEiBS01T":1, "BLEblueradio":1, "BLEminewS1TH":1, "BLEXiaomiMiTempHumClock":1, "BLEXiaomiMiformaldehyde":1, "BLEXiaomiMiTempHumRound":1, "BLEXiaomiMiTempHumSquare":1, "BLEgoveeTempHum":1, "BLEminewAcc":1, "BLEminewS1Plus":1, "BLEinkBirdPool01B":1, "BLEaprilAccel":1, "BLEaprilTHL":1, "BLEThermopro":1, "BLETempspike":1, "BLEiBS03RG":1, "BLEiBS01RG":1, "BLEiBS01":1, "BLESatech":1, "BLEiSensor-onOff":1, "BLEiSensor-on":1, "BLEiSensor-RemoteKeyFob":1, "BLEiSensor-TempHum":1, "BLEswitchbotTempHum":1, "BLEswitchbotMotion":1, "BLEswitchbotContact":1}
_stateListToDevTypes["rpiAndBeaconAndBLEconnect"] = {"beacon":1, "rPI":1, "BLEconnect":1}
_stateListToDevTypes["accelerationVectorDelta"]	 = {"BLERuuviTag":1,"BLEminewAcc":1,"BLEminewS1Plus":1,"BLEMKKsensor":1,"BLEaprilAccel":1,"BLEiBS03RG":1,"BLEiBS01RG":1,"BLESatech":1}
_stateListToDevTypes["accelerationX"]	 		= {"BLERuuviTag":1,"BLEminewAcc":1,"BLEminewS1Plus":1,"BLEMKKsensor":1,"BLEaprilAccel":1,"BLEiBS03RG":1,"BLEiBS01RG":1,"BLESatech":1}
_stateListToDevTypes["accelerationY"]	 		= {"BLERuuviTag":1,"BLEminewAcc":1,"BLEminewS1Plus":1,"BLEMKKsensor":1,"BLEaprilAccel":1,"BLEiBS03RG":1,"BLEiBS01RG":1,"BLESatech":1}
_stateListToDevTypes["accelerationZ"]	 		= {"BLERuuviTag":1,"BLEminewAcc":1,"BLEminewS1Plus":1,"BLEMKKsensor":1,"BLEaprilAccel":1,"BLEiBS03RG":1,"BLEiBS01RG":1,"BLESatech":1}
_stateListToDevTypes["accelerationTotal"]	 	= {"BLERuuviTag":1,"BLEminewAcc":1,"BLEminewS1Plus":1,"BLEMKKsensor":1,"BLEaprilAccel":1,"BLEiBS03RG":1,"BLEiBS01RG":1,"BLESatech":1}
_stateListToDevTypes["accelerationXYZMaxDelta"]	 = {"BLERuuviTag":1,"BLEminewAcc":1,"BLEminewS1Plus":1,"BLEMKKsensor":1,"BLEaprilAccel":1,"BLEiBS03RG":1,"BLEiBS01RG":1,"BLESatech":1}



_stateListToDevTypes["output"]					= {}
for dd in _GlobalConst_allowedOUTPUT:
	_stateListToDevTypes["output"][dd] = 1


## all sensors 
_stateListToDevTypes["sensorStates"]			= {}
for xx in _GlobalConst_allowedSensors:
	_stateListToDevTypes["sensorStates"][xx]			= 1
for xx in _BLEsensorTypes:
	_stateListToDevTypes["sensorStates"][xx]			= 1
for xx in ["AmbientTemperature","Temperature","CO2","Pressure","VOC","Formaldehyde", "beaconSensorStates"]:
	for dd in _stateListToDevTypes[xx]:
		_stateListToDevTypes["sensorStates"][dd] = 1

for xx in ["beaconOn"]:
	for dd in _stateListToDevTypes[xx]:
		_stateListToDevTypes["beaconOn"][dd] = 1

_stateListToDevTypes["allDevHaveTheseStates"]	= {"*":1}


################################################################################
################################################################################
################################################################################

#
class Plugin(indigo.PluginBase):
####-------------------------------------------------------------------------####
	def __init__(self, pluginId, pluginDisplayName, pluginVersion, pluginPrefs):
		indigo.PluginBase.__init__(self, pluginId, pluginDisplayName, pluginVersion, pluginPrefs)

		self.pluginShortName 			= "piBeacon"

		self.quitNow					= ""
###############  common for all plugins ############
		self.getInstallFolderPath		= indigo.server.getInstallFolderPath()+"/"
		self.indigoPath					= indigo.server.getInstallFolderPath()+"/"
		self.indigoRootPath 			= indigo.server.getInstallFolderPath().split("Indigo")[0]
		self.pathToPlugin 				= self.completePath(os.getcwd())

		major, minor, release 			= map(int, indigo.server.version.split("."))
		self.indigoVersion 				= float(major)+float(minor)/10.
		self.indigoRelease 				= release

		self.pluginVersion				= pluginVersion
		self.pluginId					= pluginId
		self.pluginName					= pluginId.split(".")[-1]
		self.myPID						= os.getpid()
		self.pluginState				= "init"

		self.myPID 						= os.getpid()
		self.MACuserName				= pwd.getpwuid(os.getuid())[0]

		self.MAChome					= os.path.expanduser("~")
		self.userIndigoDir				= self.MAChome + "/indigo/"
		self.indigoPreferencesPluginDir = self.getInstallFolderPath+"Preferences/Plugins/"+self.pluginId+"/"
		self.indigoPluginDirOld			= self.userIndigoDir + self.pluginShortName+"/"
		self.PluginLogFile				= indigo.server.getLogsFolderPath(pluginId=self.pluginId) +"/plugin.log"
		self.showLoginTest 				= pluginPrefs.get('showLoginTest',True)

		formats=	{   logging.THREADDEBUG: "%(asctime)s %(msg)s",
						logging.DEBUG:       "%(asctime)s %(msg)s",
						logging.INFO:        "%(asctime)s %(msg)s",
						logging.WARNING:     "%(asctime)s %(msg)s",
						logging.ERROR:       "%(asctime)s.%(msecs)03d\t%(levelname)-12s\t%(name)s.%(funcName)-25s %(msg)s",
						logging.CRITICAL:    "%(asctime)s.%(msecs)03d\t%(levelname)-12s\t%(name)s.%(funcName)-25s %(msg)s" }

		date_Format = { logging.THREADDEBUG: _defaultDateStampFormat,		# 5
						logging.DEBUG:       _defaultDateStampFormat,		# 10
						logging.INFO:        _defaultDateStampFormat,		# 20
						logging.WARNING:     _defaultDateStampFormat,		# 30
						logging.ERROR:       _defaultDateStampFormat,		# 40
						logging.CRITICAL:    _defaultDateStampFormat }		# 50
		formatter = LevelFormatter(fmt="%(msg)s", datefmt=_defaultDateStampFormat, level_fmts=formats, level_date=date_Format)

		self.plugin_file_handler.setFormatter(formatter)
		self.indiLOG = logging.getLogger("Plugin")  
		self.indiLOG.setLevel(logging.THREADDEBUG)

		self.indigo_log_handler.setLevel(logging.INFO)

		self.indiLOG.log(20,"initializing  ... ")
		self.indiLOG.log(20,"path To files:          =================")
		self.indiLOG.log(10,"indigo                  {}".format(self.indigoRootPath))
		self.indiLOG.log(10,"installFolder           {}".format(self.indigoPath))
		self.indiLOG.log(10,"plugin.py               {}".format(self.pathToPlugin))
		self.indiLOG.log(10,"indigo                  {}".format(self.indigoRootPath))
		self.indiLOG.log(20,"detailed logging        {}".format(self.PluginLogFile))
		if self.showLoginTest:
			self.indiLOG.log(20,"testing logging levels, for info only: ")
			self.indiLOG.log( 0,"logger  enabled for     0 ==> TEST ONLY ")
			self.indiLOG.log( 5,"logger  enabled for     THREADDEBUG    ==> TEST ONLY ")
			self.indiLOG.log(10,"logger  enabled for     DEBUG          ==> TEST ONLY ")
			self.indiLOG.log(20,"logger  enabled for     INFO           ==> TEST ONLY ")
			self.indiLOG.log(30,"logger  enabled for     WARNING        ==> TEST ONLY ")
			self.indiLOG.log(40,"logger  enabled for     ERROR          ==> TEST ONLY ")
			self.indiLOG.log(50,"logger  enabled for     CRITICAL       ==> TEST ONLY ")
		self.indiLOG.log(10,"Plugin short Name       {}".format(self.pluginShortName))
		self.indiLOG.log(10,"my PID                  {}".format(self.myPID))	 
		self.indiLOG.log(10,"Achitecture             {}".format(platform.platform()))	 
		self.indiLOG.log(10,"OS                      {}".format(platform.mac_ver()[0]))	 
		self.indiLOG.log(10,"indigo V                {}".format(indigo.server.version))	 
		self.indiLOG.log(10,"python V                {}.{}.{}".format(sys.version_info[0], sys.version_info[1] , sys.version_info[2]))	 

		self.pythonPath = ""
		if sys.version_info[0] >2:
			if os.path.isfile("/Library/Frameworks/Python.framework/Versions/Current/bin/python3"):
				self.pythonPath				= "/Library/Frameworks/Python.framework/Versions/Current/bin/python3"
		else:
			if os.path.isfile("/usr/local/bin/python"):
				self.pythonPath				= "/usr/local/bin/python"
			elif os.path.isfile("/usr/bin/python2.7"):
				self.pythonPath				= "/usr/bin/python2.7"
		if self.pythonPath == "":
				self.indiLOG.log(40,"FATAL error:  none of python versions 2.7 3.x is installed  ==>  stopping {}".format(self.pluginId))
				self.quitNOW = "none of python versions 2.7 3.x is installed "
				exit()
		self.indiLOG.log(20,"using '{}' for utily programs".format(self.pythonPath))

###############  END common for all plugins ############
		self.waitForMAC2vendor 			= "notInitialized"
		self.getDeviceStateListCalls 	= 0

####-------------------------------------------------------------------------####
	def __del__(self):
		indigo.PluginBase.__del__(self)

	###########################		INIT	## START ########################

####-------------------------------------------------------------------------####
	def startup(self):
		try:
			if not checkIndigoPluginName(self, indigo): 
				exit() 


			if not self.moveToIndigoPrefsDir(self.indigoPluginDirOld, self.indigoPreferencesPluginDir):
				exit()

			if os.path.isfile(self.indigoPreferencesPluginDir+"dataVersion"):
				subprocess.call("rm '"+self.indigoPreferencesPluginDir+"dataVersion' &", shell=True)

			self.startTime = time.time()

			self.getDebugLevels()

			self.setVariables()

			#### basic check if we can do get path for files
			self.initFileDir()

			self.checkcProfile()

			self.setupBasicFiles()

			self.startupFIXES0()

			self.readConfig()

			self.initGarageDoors()

			self.deleteAndCeateVariablesAndDeviceFolder(False)

			self.startupFIXES1()

			self.resetMinMaxSensors(init=True)

			self.statusChanged = 99
			self.setGroupStatus(force=True)

			self.checkPiEnabled()

			if self.userIdOfServer != "":
				cmd = "echo '"+self.passwordOfServer+"' | sudo -S /usr/bin/xattr -rd com.apple.quarantine '"+self.pathToPlugin+"pngquant'"
				ret, err = self.readPopen(cmd)
				if self.decideMyLog("Logic"): self.indiLOG.log(10,"setting attribute for catalina  with:  {}".format(cmd))
				if self.decideMyLog("Logic"): self.indiLOG.log(10," ......... result:{}".format(ret))

			self.setSqlLoggerIgnoreStatesAndVariables()

			self.indiLOG.log(5," ..   startup(self): setting variables, debug ..   finished ")

			#self.indiLOG.log(20,"_stateListToDevTypes:{}".format(json.dumps(_stateListToDevTypes, sort_keys=True, indent=2)))
			#self.indiLOG.log(20,"_devtypesToStates:{}".format(json.dumps(_devtypesToStates, sort_keys=True, indent=2)))


		except Exception as e:
			self.indiLOG.log(50,"--------------------------------------------------------------------------------------------------------------")
			self.indiLOG.log(50,"Line {} has error={}".format(sys.exc_info()[2].tb_lineno, e))
			self.indiLOG.log(50,"Error in startup of plugin, waiting for 2000 secs then restarting plugin")
			self.indiLOG.log(50,"--------------------------------------------------------------------------------------------------------------")
			self.sleep(2000)
			exit(1)
		return


####-----------------	 ---------
	def setSqlLoggerIgnoreStatesAndVariables(self):
		try:
			if self.indigoVersion <  7.4:                             return
			if self.indigoVersion == 7.4 and self.indigoRelease == 0: return
			#tt = ["beacon",              "rPI", "rPI-Sensor", "BLEconnect", "sensor"]

			outOND  = ""
			outOffD = ""
			outONV  = ""
			outOffV = ""
			if self.decideMyLog("SQLSuppresslog"): self.indiLOG.log(10,"setSqlLoggerIgnoreStatesAndVariables settings:{}".format( self.SQLLoggingEnable) )
			if not self.SQLLoggingEnable["devices"]: # switch sql logging off
				for ff in _sqlLoggerDevTypes:

					statesToInclude = _sqlLoggerIgnoreStates[ff].split(",")[0]
					for dev in indigo.devices.iter("props."+ff):
						props = dev.pluginProps
						skip = False
						if ff == "isSensorDevice":
							for kk in _sqlLoggerDevTypesNotSensor:
								if kk in props:
									skip=True
									break
						if skip: continue
						sp = dev.sharedProps
						#if self.decideMyLog("SQLSuppresslog"): self.indiLOG.log(10,"\n1 dev: {} current sharedProps: testing for off \n{}".format(dev.name, "{}".format(sp).replace("\n","")) )
						if "sqlLoggerIgnoreStates" not in sp or statesToInclude not in sp["sqlLoggerIgnoreStates"]:
							sp["sqlLoggerIgnoreStates"] = copy.copy(_sqlLoggerIgnoreStates[ff])
							dev.replaceSharedPropsOnServer(sp)
							outOffD += dev.name+"; "
							dev2 = indigo.devices[dev.id]
							sp2 = dev2.sharedProps

			else:  # switch sql logging (back) on
				for ff in _sqlLoggerDevTypes:
					for dev in indigo.devices.iter("props."+ff):
						props = dev.pluginProps
						skip = False
						### alsways set completely
						if ff == "isSensorDevice":
							for kk in _sqlLoggerDevTypesNotSensor:
								if kk in props:
									skip=True
									break
						if skip: continue
						sp = dev.sharedProps
						if "sqlLoggerIgnoreStates" in sp and len(sp["sqlLoggerIgnoreStates"]) > 0:
							outOffD += dev.name+"; "
							sp["sqlLoggerIgnoreStates"] = ""
							dev.replaceSharedPropsOnServer(sp)



			if not self.SQLLoggingEnable["variables"]:

				for v in self.varExcludeSQLList:
					if v not in indigo.variables: continue
					var = indigo.variables[v]
					sp = var.sharedProps
					if "sqlLoggerIgnoreChanges" in sp and sp["sqlLoggerIgnoreChanges"] == "true":
						continue
					outOffV += var.name+"; "
					sp["sqlLoggerIgnoreChanges"] = "true"
					var.replaceSharedPropsOnServer(sp)

			else:
				for v in self.varExcludeSQLList:
					try:
						if v not in indigo.variables: continue
						var = indigo.variables[v]
						sp = var.sharedProps
						if "sqlLoggerIgnoreChanges" not in sp  or sp["sqlLoggerIgnoreChanges"] != "true":
							continue
						outONV += var.name+"; "
						sp["sqlLoggerIgnoreChanges"] = ""
						var.replaceSharedPropsOnServer(sp)
					except: pass

			if self.decideMyLog("SQLSuppresslog"):
				self.indiLOG.log(10," \n\n")
				if outOffD !="":
					self.indiLOG.log(10," switching off SQL logging for special devtypes/states:\n{}\n for devices:\n>>>{}<<<".format(json.dumps(_sqlLoggerIgnoreStates, sort_keys=True, indent=2), outOffD) )

				if outOND !="":
					self.indiLOG.log(10," switching ON SQL logging for special states for devices: {}".format(outOND) )

				if outOffV !="":
					self.indiLOG.log(10," switching off SQL logging for variables :{}".format(outOffV) )

				if outONV !="":
					self.indiLOG.log(10," switching ON SQL logging for variables :{}".format(outONV) )
				self.indiLOG.log(10,"setSqlLoggerIgnoreStatesAndVariables settings end\n")



		except Exception as e:
			self.exceptionHandler(40, e)
		return



####-----------------	 ---------
	def xxgetEventConfigUiXml(self, typeId, eventId):
		indigo.server.log('Called getEventConfigUiXml(self, typeId:{}, eventId:{},  eventsTypeDict:{}:'.format(typeId, eventId, self.eventsTypeDict) )
		if typeId in self.eventsTypeDict:
			return self.eventsTypeDict[typeId]["ConfigUIRawXml"]
		return None

####-----------------	 ---------
	def xxgetEventConfigUiValues(self, pluginProps, typeId, eventId):
		indigo.server.log('Called getEventConfigUiValues(self, pluginProps:{}, typeId:{}, eventId {}:'.format(pluginProps, typeId, eventId) )
		valuesDict = pluginProps
		errorMsgDict = indigo.Dict()
		return (valuesDict, errorMsgDict)


####-----------------	 ---------
	def initMac2Vendor(self):
		self.waitForMAC2vendor = "initializing"
		try:	self.enableMACtoVENDORlookup	= int(self.pluginPrefs.get("enableMACtoVENDORlookup", "21"))
		except:	self.enableMACtoVENDORlookup	= 21
		if self.enableMACtoVENDORlookup != "0":
			self.M2V =  MAC2Vendor.MAP2Vendor( pathToMACFiles=self.indigoPreferencesPluginDir+"mac2Vendor/", refreshFromIeeAfterDays = self.enableMACtoVENDORlookup, myLogger = self.indiLOG.log )
			self.waitForMAC2vendor = self.M2V.makeFinalTable()

####-----------------	 ---------
	def getVendortName(self,MAC):
		if self.waitForMAC2vendor == "notInitialized": return ""

		if self.enableMACtoVENDORlookup != "0" and self.waitForMAC2vendor == "initializing":
			self.waitForMAC2vendor = self.M2V.makeFinalTable()

		return self.M2V.getVendorOfMAC(MAC)


####-------------------------------------------------------------------------####
	def setCurrentlyBooting(self, addTime, setBy=""):
		try:	self.currentlyBooting = time.time() + addTime
		except: self.errorLog("setCurrentlyBooting:  setting BeaconsCheck,  bad number requested {}, called from: {}".format(addTime, setBy))
		try:
			self.indiLOG.log(10,"setting BeaconsCheck to off (no up-->down) for {:3d} secs requested by: {}".format(addTime, setBy))
		except:
			indigo.server.log("setting BeaconsCheck to off (no up-->down) for {:3d} secs requested by: {}".format(addTime, setBy))
		return


####-------------------------------------------------------------------------####
	def initFileDir(self):

			if not os.path.exists(self.indigoPreferencesPluginDir):
				os.mkdir(self.indigoPreferencesPluginDir)
			if not os.path.exists(self.indigoPreferencesPluginDir):
				self.indiLOG.log(50,"error creating the plugin data dir did not work, can not create: {}".format(self.indigoPreferencesPluginDir)  )
				self.sleep(1000)
				exit()

			if not os.path.exists(self.indigoPreferencesPluginDir+"plotPositions"):
				os.mkdir(self.indigoPreferencesPluginDir+"plotPositions")
			if not os.path.exists(self.cameraImagesDir):
				os.mkdir(self.cameraImagesDir)



####-------------------------------------------------------------------------####
	def startupFIXES0(self): # change old names used


		try:
			for dev in indigo.devices.iter("props.isBeaconDevice,props.isRPIDevice,props.isRPISensorDevice,props.isBLEconnectDevice"):
				if not dev.enabled: continue
				try:
					if "lastStatusChange" in dev.states:
						dateString	= datetime.datetime.now().strftime(_defaultDateStampFormat)
						dateString2 = dev.states["lastStatusChange"]
						if len(dateString2) < 10:
								dev.updateStateOnServer("lastStatusChange", dateString)
						else:
							dateString = dateString2

						if "displayStatus" in dev.states:
							new =  self.padDisplay(dev.states["status"]) + dateString[5:]
							if new != dev.states["displayStatus"]:
								dev.updateStateOnServer("displayStatus",new)
							if	 "up" in new:
								dev.updateStateImageOnServer(indigo.kStateImageSel.SensorOn)
							elif  "down" in new:
								dev.updateStateImageOnServer(indigo.kStateImageSel.SensorOff)
							else:
								dev.updateStateImageOnServer(indigo.kStateImageSel.SensorTripped)



				except Exception as e:
						self.exceptionHandler(40, e)
		except Exception as e:
			self.exceptionHandler(40, e)
		return


####-------------------------------------------------------------------------####
	def startupFIXES1(self):
		try:
			dateString = datetime.datetime.now().strftime(_defaultDateStampFormat)

			self.sprinklerDeviceActive = False

			######## fix  old settings and upper / lower case mac ...
			try:
				for dev in indigo.devices.iter(self.pluginId):
					upd = False
					props = dev.pluginProps
					if dev.deviceTypeId == "beacon" or (dev.deviceTypeId.lower()) == "rpi":
						for piU in _rpiBeaconList:
							piI = int(piU)
							stateT = "Pi_{:02d}_Time".format(piI)
							if stateT not in dev.states: continue
							stateS = "Pi_{:02d}_Signal".format(piI)
							try:
								if dev.states[stateT] is None or len(dev.states[stateT]) < 5:
									if "{}".format(dev.states[stateS]) == "0":
										self.addToStatesUpdateDict(dev.id,stateS,-999)
							except:
								if not self.RPIVersion20:
									self.indiLOG.log(30,"{}  error pi#: {}, state missing ignored/disabled device? stateS:{}, stateT:{}\n states:{}".format(dev.name, piU,stateS, stateT, dev.states) )
								continue

						self.executeUpdateStatesDict(calledFrom="startupFIXES1")

					if dev.deviceTypeId.lower() == "rpi":
						piU = props.get("RPINumber","")
						if piU == "":
							try:
								piU = dev.states["note"].split("-")[1]
								props["RPINumber"] = piU
								upd = True
								self.indiLOG.log(20,"{}  fixed props RPINumber to:{}".format(dev.name, piU) )
							except:
								self.indiLOG.log(30,"{} fix in initial setup or device edit".format(dev.name) )
							
						try:
							for xyz in ["PosX", "PosY", "PosZ"]:
								self.RPI[piU][xyz] = dev.states[xyz]
						except:
								self.indiLOG.log(20,"{}  error piU {}, states:{}, props:{}".format(dev.name, piU,dev.states, props) )

					#if "SupportsBatteryLevel" in props:
					#	props["SupportsBatteryLevel"] = False
					#s	upd = True

					if "oneWireAddNewSensors" in props:   # reset accept new one wire devices
						if props.get("oneWireAddNewSensors","0") != "0":
							props["oneWireAddNewSensors"] = "0"
							upd = True

					if "newMACNumber" in props:   
						for z in props["newMACNumber"]:
							if z.islower():
								props["newMACNumber"] = props["newMACNumber"].upper()
								upd = True
								break

					if "mac" in props:   
						for z in props["mac"]:
							if z.islower():
								props["mac"] = props["mac"].upper()
								upd = True
								break

					if "macIfWOLsendToIndigoServerLabel" in props:   
						for z in props["macIfWOLsendToIndigoServerLabel"]:
							if z.islower():
								props["macIfWOLsendToIndigoServerLabel"] = props["mac"].upper()
								upd = True
								break

					if "address" in props and self.isValidMAC(props["address"]):   
						for z in props["address"]:
							if z.islower():
								props["address"] = props["address"].upper()
								upd = True
								break

					if "lastSensorChange" in dev.states:
						if len(dev.states["lastSensorChange"]) < 5:
							dev.updateStateOnServer("lastSensorChange",dateString)

					if dev.deviceTypeId == "BLEconnect":
						if not props.get("isBLEconnectDevice",False):
							props["isBLEconnectDevice"] = True
						if dev.enabled:
							dev.updateStateOnServer("note", "BLEconnect")

					if dev.deviceTypeId in _GlobalConst_allowedSensors or dev.deviceTypeId in _BLEsensorTypes:
						if not props.get("isSensorDevice",False):
							props["isSensorDevice"] = True
							upd = True

					if dev.deviceTypeId in _GlobalConst_allowedOUTPUT:
						if not props.get("isOutputDevice",False):
							props["isOutputDevice"] = True
							upd = True


					if (dev.deviceTypeId.lower()) == "rpi":
						if "isBeaconDevice" in props:
							del props["isBeaconDevice"]
						props["isRPIDevice"] = True
						props["typeOfBeacon"] = "rPI"
						props["useOnlyPrioTagMessageTypes"] = "0"
						upd = True
						if props["address"] in self.beacons:
							self.beacons[props["address"]]["typeOfBeacon"] = "rPI"

					if dev.deviceTypeId == "rPI-Sensor":
						if not props.get("isRPISensorDevice",False):
							props["isRPISensorDevice"] = True
							upd = True


					if dev.deviceTypeId =="car":
						if not props.get("isCARDevice",False):
							props["isCARDevice"] = True
							upd = True

					if dev.deviceTypeId in _BLEsensorTypes:
						if not props.get("isBLESensorDevice",False):
							props["isBLESensorDevice"] = True
							upd = True
						self.isBLESensorDevice[props["mac"]] = dev.id

					if dev.deviceTypeId in _BLEconnectSensorTypes :
						if not props.get("isBLElongConnectDevice",False):
							props["isBLElongConnectDevice"] = True
							upd = True
						self.isBLElongConnectDevice[props["mac"]] = dev.id


					if dev.deviceTypeId == "OUTPUTswitchbotRelay":
						if not props.get("SupportsStatusRequest",False):
							props["SupportsStatusRequest"] = True
							upd = True


					if "piServerNumber" in props and "rPiEnable0" in props:
						del props["piServerNumber"]
						upd = True

					if "piServerNumber" in props:
						newAdress = "Pi-" + props["piServerNumber"]
						if "mac" in dev.states: newAdress +=" "+dev.states["mac"]
						if props["address"] != newAdress:
							props["address"] = newAdress
							upd = True


					if props.get("isBLESensorDevice",False):
						mac = props.get("address","")
						if self.isValidMAC(mac):
							if  props.get("beaconDevId","") == "":
								for devBeacon in indigo.devices.iter("props.isBeaconDevice"):
									if devBeacon.pluginProps.get("address","") == mac:
										props["beaconDevId"] = devBeacon.id
										#self.indiLOG.log(20,"updating beacon mac {}, devId:{}".format(mac, devBeacon.id ))
										upd = True
										break


					if "rPiEnable0" in props:
						testpiU  =[]
						if "mac" in props:
							newAddress = props["mac"]
							if dev.address != newAddress:
								props["address"] = newAddress
								anyChange = True
								upd = True

							if "description" in props:
								if props["description"] != dev.description:
										dev.description = props["description"]
										if self.decideMyLog("Init"): self.indiLOG.log(5,"updating notes for {}  to :{}".format(dev.name, props["description"]) )
										anyChange = True
										upd = True

					if upd:
						dev.replacePluginPropsOnServer(props)


				self.writeJson(self.RPI, fName=self.indigoPreferencesPluginDir + "RPIconf", fmtOn=self.RPIFileSort)

			except Exception as e:
				self.exceptionHandler(40, e)
			try:
				os.remove(self.indigoPreferencesPluginDir + "config")
			except:
				pass


			self.indiLOG.log(5," ..   checking devices tables" )

	######## fix rPi- --> Pi-
			for dev in indigo.devices.iter("props.isRPIDevice,props.isRPISensorDevice"):
				dd = dev.description
				if dev.description.find("rPI") >-1:
					dd = dd.split("-")
					if len(dd) == 3:
						dev.description = "Pi-"+dd[1]+"-"+dd[2]
						dev.replaceOnServer()

				props = dev.pluginProps

				if dev.deviceTypeId.find("rPI") >-1:
					if dev.deviceTypeId.find("rPI-Sensor") >-1:
						if dev.address.find("Pi-") == 0:
							dev.updateStateOnServer("note",dev.address)
						else:
							dev.updateStateOnServer("note", "Pi-"+dev.address)
					else:
						dev.updateStateOnServer("note", "Pi-"+dev.pluginProps.get("RPINumber","") )


	######## fix  address vendors ..
			for dev in indigo.devices.iter(self.pluginId):
				props = dev.pluginProps

				if dev.deviceTypeId == "rPi" or dev.deviceTypeId == "beacon":
					self.freezeAddRemove = False

					try:
						beacon = props["address"]
					except:
						self.indiLOG.log(40,"device has no address: {} {}\n  {}  {}; please delete and let the plugin create the devices".format(dev.name, dev.id, props, dev.globalProps) )
						continue

					if beacon not in self.beacons:
						self.beacons[beacon]			 = copy.deepcopy(_GlobalConst_emptyBeacon)
						self.beacons[beacon]["indigoId"] = dev.id
						self.beacons[beacon]["created"]  = dev.states["created"]

					if "vendorName" in dev.states and  len(dev.states["vendorName"]) == 0:
						vname = self.getVendortName(beacon)
						if vname !="" and  vname != dev.states["vendorName"]:
							dev.updateStateOnServer("vendorName", vname)


				# typeofBeacon == ruuvi beacon
				if "typeOfBeacon" in props:
					if props["typeOfBeacon"] == "ruuviTag":
						self.indiLOG.log(20,"device: {} updating type of beacon to BLERuuviTag".format(dev.name))
						props["typeOfBeacon"] = "BLERuuviTag"
						dev.replacePluginPropsOnServer(props)


				if dev.deviceTypeId.find("OUTPUTgpio") > -1:
					xxx = json.loads(props["deviceDefs"])
					nn = len(xxx)
					update=False
					for n in range(nn):
						if "gpio" in xxx[n]:
							if xxx[n]["gpio"] == "-1":
								del xxx[n]
								continue
							if	"initialValue" not in xxx[n]:
								xxx[n]["initialValue"] = "float"
								update=True
					if update:
						props["deviceDefs"] = json.dumps(xxx)

						dev.replacePluginPropsOnServer(props)
					###indigo.server.log(dev.name+" {}".format(props))

				if dev.deviceTypeId.find("OUTPUTi2cRelay") > -1:
					xxx = json.loads(props["deviceDefs"])
					nn = len(xxx)
					update=False
					for n in range(nn):
						if "gpio" in xxx[n]:
							if xxx[n]["gpio"] == "-1":
								del xxx[n]
								continue
							if	"initialValue" not in xxx[n]:
								xxx[n]["initialValue"] = "float"
								update=True
					if update:
						props["deviceDefs"] = json.dumps(xxx)

						dev.replacePluginPropsOnServer(props)
					###indigo.server.log(dev.name+" {}".format(props))


				if "description" in props:
					props["description"] =""

					dev.replacePluginPropsOnServer(props)



		except Exception as e:
			self.indiLOG.log(50,"--------------------------------------------------------------------------------------------------------------")
			self.indiLOG.log(50,"Error in startup of plugin, waiting for 2000 secs then restarting plugin")
			self.indiLOG.log(50,"Line {} has error={}".format(sys.exc_info()[2].tb_lineno, e))
			self.indiLOG.log(50,"--------------------------------------------------------------------------------------------------------------")
			self.sleep(2000)
			exit(1)
		return

###-------------------------------------------------------------------------####
	def fixBeaconPILength(self,mac, area):
		try:
			if mac not in self.beacons: return
			lx = len(self.beacons[mac][area])
			if lx < _rpiBeaconList:
				for ll in range(lx,len(_rpiBeaconList)):
					self.beacons[mac][area].append({"distance": 99999, "lastSignal": 0, "rssi": -999})

		except Exception as e:
			self.exceptionHandler(40, e)



####-------------------------------------------------------------------------####
	def setupBasicFiles(self):
		try:

			if not os.path.exists(self.indigoPreferencesPluginDir + "all"):
				os.mkdir(self.indigoPreferencesPluginDir + "all")
			if not os.path.exists(self.indigoPreferencesPluginDir + "rejected"):
				os.mkdir(self.indigoPreferencesPluginDir + "rejected")
				subprocess.call("mv '" + self.indigoPreferencesPluginDir + "reject*' '" + self.indigoPreferencesPluginDir + "rejected'", shell=True)
			if not os.path.exists(self.indigoPreferencesPluginDir + "interfaceFiles"):
				os.mkdir(self.indigoPreferencesPluginDir + "interfaceFiles")
				subprocess.call("rm '" + self.indigoPreferencesPluginDir + "param*'", shell=True)
				subprocess.call("rm '" + self.indigoPreferencesPluginDir + "interfa*'", shell=True)
				subprocess.call("rm '" + self.indigoPreferencesPluginDir + "wpa_supplicant'*", shell=True)
			if not os.path.exists(self.indigoPreferencesPluginDir + "soundFiles"):
				os.mkdir(self.indigoPreferencesPluginDir + "soundFiles")
			if not os.path.exists(self.indigoPreferencesPluginDir + "displayFiles"):
				os.mkdir(self.indigoPreferencesPluginDir + "displayFiles")
			if not os.path.exists(self.cameraImagesDir):
				os.mkdir(self.cameraImagesDir)

		except Exception as e:
			self.indiLOG.log(50,"--------------------------------------------------------------------------------------------------------------")
			self.indiLOG.log(50,"Line {} has error={}".format(sys.exc_info()[2].tb_lineno, e) )
			self.indiLOG.log(50,"Error in startup of plugin, waiting for 2000 secs then restarting plugin")
			self.indiLOG.log(50,"--------------------------------------------------------------------------------------------------------------")
			self.sleep(2000)
			exit(1)
		return



####-------------------------------------------------------------------------####
####-------------------------------------------------------------------------####
	def getDebugLevels(self, useMe=dict()):
		try:
			self.debugLevel	= []
			if useMe == {}:
				for d in _debugAreas:
					if self.pluginPrefs.get("debug"+d, False): self.debugLevel.append(d)
				self.showLoginTest = self.pluginPrefs.get("showLoginTest", True)
				try: 	self.debugRPI		= int(self.pluginPrefs.get("debugRPI","-1"))
				except:	self.debugRPI		= -1

			else:
				for d in _debugAreas:
					if useMe.get("debug"+d, False): self.debugLevel.append(d)
				self.showLoginTest = useMe.get("showLoginTest", True)

			self.indiLOG.log(20,"debug areas:{}".format(self.debugLevel))
		except Exception:
			self.indiLOG.log(50,"Error in startup of plugin, plugin prefs are wrong", exc_info=True)
		return




####-------------------------------------------------------------------------####
	def setVariables(self):
		try:
			self.debugNewDevStates 			= False
			self.cameraImagesDir			= self.indigoPreferencesPluginDir+"cameraImages/"
			self.knownBeaconTags 			= {"input":{}, "output":{},"mfgNames":{}}
			self.isBLESensorDevice			= {}
			self.isBLElongConnectDevice		= {}
			self.isSwitchbotDevice			= {}
			try: 	self.enableMACtoVENDORlookup	= int(self.pluginPrefs.get("enableMACtoVENDORlookup", "21"))
			except: self.enableMACtoVENDORlookup	= 21


			self.oneWireResetNewDevices		= 0
			self.loopSleepTime				= 9.0
			self.setGroupStatusrepeat		= self.loopSleepTime *1.9
			self.setGroupStatusNextCheck 	= time.time() + self.setGroupStatusrepeat +10
			self.beaconsFileSort			= True
			self.parametersFileSort			= True
			self.RPIFileSort				= True
			try:
				xx = (self.pluginPrefs.get("SQLLoggingEnable", "on-on")).split("-")
				self.SQLLoggingEnable ={"devices":xx[0]=="on", "variables":xx[1]=="on"}
			except:
				self.SQLLoggingEnable ={"devices":False, "variables":False}

			self.bootWaitTime				= 100
			self.setCurrentlyBooting(self.bootWaitTime + 25, setBy="setVariables")

			self.checkBatteryLevelHours = [int(x) for x in _GlobalConst_emptyBeaconProps["batteryLevelCheckhours"].split("/")]

			self.lastUPtoDown				= time.time() + 35
			self.lastsetupFilesForPi 		= time.time()
			self.checkIPSendSocketOk		= {}
			self.actionList					= {"setTime":[], "setSqlLoggerIgnoreStatesAndVariables":False}
			self.updateStatesDict			= {}
			self.executeUpdateStatesDictActive = ""

			self.trackSensorId				= []
			self.rpiQueues					= {}
			self.delayedActions				= {}
			self.beaconMessages				= {}

			self.rePopulateStates			= ""
			self.newBeaconsLogTimer			= 0
			self.selectBeaconsLogTimer		= {}

			self.RPI						= {}
			self.beacons					= {}

			self.PasswordsAreSet			= 0
			self.indigoCommand				= ""
			self.countLoop					= 0
			self.selectedPiServer			= 0
			self.statusChanged				= 0


			self.newIgnoreMAC				= 0
			self.lastUpdateSend				= time.time()

			self.sendInitialValue			= "" # will be dev.id if output should be send

			self.updatePiBeaconNote			= {}
			self.updateNeeded				= ""
			self.updateNeededTimeOut		= 9999999999999999999999999999
			self.devUpdateList				= {}

			self.resetMinMaxDayDone 		= -1

			self.doRejects					= False

			self.timeErrorCount				= [0 for ii in _rpiList]
			self.configAndReboot			= ""
			self.initStatesOnServer			= True
			try:
				self.rPiCommandPORT			= self.pluginPrefs.get("rPiCommandPORT", "9999")
			except:
				self.rPiCommandPORT			= "0" # port on rPis to receive commands ==0 disable

			try: 	self.awayWhenNochangeInSeconds	= int(self.pluginPrefs.get("awayWhenNochangeInSeconds", 600))
			except: self.awayWhenNochangeInSeconds	= 600


			#### check for last up and send to rpi to avoid extra pings to phone if last up was recent ------
			self.lastBLEconnectSeen = {} # updated when iphone is up with time stamp
			self.BLEconnectSendStopToRpi = {} # used to collect info up, timestamp, mac devid 
			self.BLEconnectLastUp = {} # used to send info to rpis
			#### check for last up and send to rpi to avoid extra pings to phone if last up was recent end


			self.groupListUsedNames = {}
			for nn in range(len(_GlobalConst_groupList)):
				group = _GlobalConst_groupList[nn]
				self.groupListUsedNames[group] = ""
				try:
					xx = self.pluginPrefs["groupName{}".format(nn)]
					if len(xx) >0: self.groupListUsedNames[group] = xx
				except: pass
			for group in _GlobalConst_groupListDef:
				self.groupListUsedNames[group] = group

			try:				self.iBeaconDevicesFolderName		= self.pluginPrefs.get("iBeaconFolderName", "Pi_Beacons_new")
			except:				self.iBeaconDevicesFolderName		= "Pi_Beacons_new"
			self.pluginPrefs["iBeaconFolderName"] = self.iBeaconDevicesFolderName

			try:				self.iBeaconFolderVariablesName	 = self.pluginPrefs.get("iBeaconFolderVariablesName", "piBeacons")
			except:				self.iBeaconFolderVariablesName	 = "piBeacons"
			self.pluginPrefs["iBeaconFolderVariablesName"] = self.iBeaconFolderVariablesName


			self.iBeaconFolderVariableDataTransferVarsName	 =  "piBeacons_dataTransferVars"


			try:				self.automaticRPIReplacement= "{}".format(self.pluginPrefs.get("automaticRPIReplacement", "False")).lower() == "true"
			except:				self.automaticRPIReplacement= False

			try:				self.setClostestRPItextToBlank= self.pluginPrefs.get("setClostestRPItextToBlank", "1") != "1"
			except:				self.setClostestRPItextToBlank= False

			try:				self.enableRebootRPIifNoMessages  = int(self.pluginPrefs.get("enableRebootRPIifNoMessages", 999999999))
			except:				self.enableRebootRPIifNoMessages  = 999999999
			self.pluginPrefs["enableRebootRPIifNoMessages"] = self.enableRebootRPIifNoMessages

			try:				self.rpiDataAcquistionMethod  =  self.pluginPrefs.get("rpiDataAcquistionMethod", _GlobalConst_emptyrPiProps["rpiDataAcquistionMethod"])
			except:				self.rpiDataAcquistionMethod  = _GlobalConst_emptyrPiProps["rpiDataAcquistionMethod"]
			self.pluginPrefs["rpiDataAcquistionMethod"] = self.rpiDataAcquistionMethod


			try:				self.tempUnits				= self.pluginPrefs.get("tempUnits", "Celsius")
			except:				self.tempUnits				= "Celsius"

			try:				self.tempDigits				 = int(self.pluginPrefs.get("tempDigits", 1))
			except:				self.tempDigits				 = 1

			try:				self.rainUnits				= self.pluginPrefs.get("rainUnits", "mm")
			except:				self.rainUnits				= "mm"

			try:				self.rainDigits				 = int(self.pluginPrefs.get("rainDigits", 0))
			except:				self.rainDigits				 = 0

			try:				self.pressureUnits			= self.pluginPrefs.get("pressureUnits", "mBar")
			except:				self.pressureUnits			= "hPascal"
			if 	self.pressureUnits==  "mbar": 				self.pressureUnits = "mBar"
			self.pluginPrefs["pressureUnits"] 				= self.pressureUnits


			try:				self.distanceUnits			= max(0.0254, float(self.pluginPrefs.get("distanceUnits", 1.)))
			except:				self.distanceUnits			= 1.0
			try:				self.speedUnits				= max(0.01, float(self.pluginPrefs.get("speedUnits", 1.)))
			except:				self.speedUnits				= 1.0

			try:				self.lightningTimeWindow	 = float(self.pluginPrefs.get("lightningTimeWindow", 10.))
			except:				self.lightningTimeWindow	 = 10.0


			try:				self.lightningNumerOfSensors = int(self.pluginPrefs.get("lightningNumerOfSensors", 1))
			except:				self.lightningNumerOfSensors = 1


			try:				self.secToDown				= float(self.pluginPrefs.get("secToDown", "80"))
			except:				self.secToDown				= 80.

			try:				self.acceptNewiBeacons		= int(self.pluginPrefs.get("acceptNewiBeacons", -999))
			except:				self.acceptNewiBeacons		= -999

			if self.acceptNewiBeacons in ["0", "1"]: 		self.acceptNewiBeacons  = -999
			self.pluginPrefs["acceptNewiBeacons"] 			= self.acceptNewiBeacons

			self.acceptNewBeaconMAC							= ""
			self.pluginPrefs["acceptNewBeaconMAC"] 			= self.acceptNewBeaconMAC



			self.acceptNewTagiBeacons						= self.pluginPrefs.get("acceptNewTagiBeacons", "off")
			self.pluginPrefs["acceptNewTagiBeacons"] 		= self.acceptNewTagiBeacons

			self.acceptNewMFGNameBeacons					= self.pluginPrefs.get("acceptNewMFGNameBeacons", "off")

			try:				self.removeJunkBeacons		= self.pluginPrefs.get("removeJunkBeacons", "1") == "1"
			except:				self.removeJunkBeacons		= False

			try:				self.restartBLEifNoConnect = self.pluginPrefs.get("restartBLEifNoConnect", "1") == "1"
			except :				self.restartBLEifNoConnect = True

			try:				self.rebootWatchDogTime		= self.pluginPrefs.get("rebootWatchDogTime", "-1")
			except:				self.rebootWatchDogTime		= "-1"

			try:				self.expectTimeout			= self.pluginPrefs.get("expectTimeout", "20")
			except:				self.expectTimeout			= "20"

			self.cycleVariables								= self.pluginPrefs.get("cycleVariables", True)



			try: 	self.indigoInputPORT	= int(self.pluginPrefs.get("indigoInputPORT", 12087))
			except: self.indigoInputPORT	= 12087
			self.IndigoOrSocket				= self.pluginPrefs.get("IndigoOrSocket", "indigo")
			self.dataStats					= {"startTime": time.time()}
			try:	self.maxSocksErrorTime	= float(self.pluginPrefs.get("maxSocksErrorTime", "600."))
			except: self.maxSocksErrorTime	= 600.
			self.compressRPItoPlugin		= self.pluginPrefs.get("compressRPItoPlugin", "20000")
			try:	self.compressRPItoPlugin	= min(40000, int(self.compressRPItoPlugin))
			except:	self.compressRPItoPlugin	= 20000
			self.portOfServer				= self.pluginPrefs.get("portOfServer", "8176")
			self.userIdOfServer				= self.pluginPrefs.get("userIdOfServer", "")
			self.passwordOfServer			= self.pluginPrefs.get("passwordOfServer", "")
			self.authentication				= self.pluginPrefs.get("authentication", "digest")
			self.apiKey						= self.pluginPrefs.get("apiKey", "")
			self.myIpNumber					= self.pluginPrefs.get("myIpNumber", "192.168.1.130")
			self.blockNonLocalIp			= self.pluginPrefs.get("blockNonLocalIp", False)
			self.checkRPIipForReject		= self.pluginPrefs.get("checkRPIipForReject", True)
			self.GPIOpwm					= self.pluginPrefs.get("GPIOpwm", "1")


			self.delayFastDownBy 			= 3.5  # delay of fast down, give an Up signbal a change to cancel down.

			self.updateRejectListsCount		= 0

			try:				self.piUpdateWindow			= float(self.pluginPrefs.get("piUpdateWindow", 0))
			except:				self.piUpdateWindow			= 0.

			self.rPiRestartCommand			= ["" for ii in range(_GlobalConst_numberOfRPI)]  ## which part need to restart on rpi

			self.anyProperTydeviceNameOrId = 0

			self.wifiSSID					= self.pluginPrefs.get("wifiSSID", "")
			self.wifiPassword				= self.pluginPrefs.get("wifiPassword", "")
			self.key_mgmt					= self.pluginPrefs.get("key_mgmt", "")
			eth0							= '{"on":"dontChange",	"useIP":"use"}'
			wlan0							= '{"on":"dontChange",	"useIP":"useIf"}'
			try: 			self.wifiEth	= {"eth0":json.loads(self.pluginPrefs.get("eth0", eth0)), "wlan0":json.loads(self.pluginPrefs.get("wlan0", wlan0))}
			except: 		self.wifiEth	= {"eth0":json.loads(eth0), "wlan0":json.loads(wlan0)}

			self.freezeAddRemove			= False
			self.outdeviceForOUTPUTgpio		= ""
			self.queueList					= ""
			self.queueListBLE				= ""
			self.groupStatusList={}
			for group in _GlobalConst_groupList+_GlobalConst_groupListDef:
				self.groupStatusList[group] = {"members":{},"allHome":"0", "allAway":"0", "oneHome":"0", "oneAway":"0", "nHome":0, "nAway":0,"nDisabled":0}
			self.groupCountNameDefault		= self.pluginPrefs.get("groupCountNameDefault", "iBeacon_Count_")
			self.ibeaconNameDefault			= self.pluginPrefs.get("ibeaconNameDefault", "iBeacon_")
			self.triggerList				= []
			self.newADDRESS					= {}
			self.trackRPImessages			= -1

			self.trackSignalStrengthIfGeaterThan = [99999.,"i"]
			self.trackSignalChangeOfRPI			 = False

			self.beaconPositionsUpdated			= 0

			self.lastFixConfig = 0

			self.pluginPrefs["wifiOFF"] = ""


			############ plot beacon positions
			try:	self.beaconPositionsUpdateTime					= float(self.pluginPrefs.get("beaconPositionsUpdateTime", -1))
			except: self.beaconPositionsUpdateTime					= -1.
			try:	self.beaconPositionsdeltaDistanceMinForImage	= float(self.pluginPrefs.get("beaconPositionsdeltaDistanceMinForImage",	 1.))
			except: self.beaconPositionsdeltaDistanceMinForImage	= 1.

			self.beaconPositionsData								= {"mac":{}}
			self.beaconPositionsData["Xscale"]						= self.pluginPrefs.get("beaconPositionsimageXscale", "20" )
			self.beaconPositionsData["Yscale"]						= self.pluginPrefs.get("beaconPositionsimageYscale", "30" )
			self.beaconPositionsData["Zlevels"]						= self.pluginPrefs.get("beaconPositionsimageZlevels", "0,5" )
			self.beaconPositionsData["dotsY"]						= self.pluginPrefs.get("beaconPositionsimageDotsY", "600" )

			self.beaconPositionsData["textPosLargeCircle"]			= self.pluginPrefs.get("beaconPositionstextPosLargeCircle", "0" )
			self.beaconPositionsData["labelTextSize"]				= self.pluginPrefs.get("beaconPositionsLabelTextSize", "12" )
			self.beaconPositionsData["captionTextSize"]				= self.pluginPrefs.get("beaconPositionsCaptionTextSize", "12" )
			self.beaconPositionsData["titleTextSize"]				= self.pluginPrefs.get("beaconPositionsTitleTextSize", "12" )
			self.beaconPositionsData["titleText"]					= self.pluginPrefs.get("beaconPositionsTitleText", "text on top" )
			self.beaconPositionsData["titleTextPos"]				= self.pluginPrefs.get("beaconPositionsTitleTextPos", "0,0" )
			self.beaconPositionsData["titleTextColor"]				= self.pluginPrefs.get("beaconPositionsTitleTextColor", "#000000" )
			self.beaconPositionsData["titleTextRotation"]			= self.pluginPrefs.get("beaconPositionsTitleTextRotation", "0" )
			self.beaconPositionsData["Outfile"]						= self.pluginPrefs.get("beaconPositionsimageOutfile", "" )
			self.beaconPositionsData["ShowCaption"]					= self.pluginPrefs.get("beaconPositionsimageShowCaption", "0" )
			self.beaconPositionsData["showTimeStamp"]				= self.pluginPrefs.get("beaconPositionsShowTimeStamp", "1" ) == "1"
			self.beaconPositionsData["compress"]					= self.pluginPrefs.get("beaconPositionsimageCompress",False)
			self.beaconPositionsData["ShowRPIs"]					= self.pluginPrefs.get("beaconPositionsimageShowRPIs", "0" )
			self.beaconPositionsData["randomBeacons"]				= self.pluginPrefs.get("beaconRandomBeacons", "0" )
			self.beaconPositionsData["SymbolSize"]					= self.pluginPrefs.get("beaconSymbolSize", "1.0" )
			self.beaconPositionsData["LargeCircleSize"]				= self.pluginPrefs.get("beaconLargeCircleSize", "1.0" )
			self.beaconPositionsData["ShowExpiredBeacons"]			= self.pluginPrefs.get("beaconShowExpiredBeacons", "0" )
			self.beaconPositionsLastCheck							= time.time() - 20


			self.varExcludeSQLList = [ "pi_IN_"+str(ii) for ii in _rpiList]
			self.varExcludeSQLList.append(self.ibeaconNameDefault+"With_ClosestRPI_Change")
			self.varExcludeSQLList.append(self.ibeaconNameDefault+"Rebooting")
			self.varExcludeSQLList.append(self.ibeaconNameDefault+"With_Status_Change")
			for group in self.groupListUsedNames:
				if len(group) > 0:
					for tType in ["Home", "Away"]:
						self.varExcludeSQLList.append(self.groupCountNameDefault+self.groupListUsedNames[group]+"_"+tType)

			self.checkBeaconParametersDisabled						= self.pluginPrefs.get("checkBeaconParametersDisabled", False )


			self.readChangedValues()

			self.initrpiQueues()

		except Exception as e:
			self.indiLOG.log(50,"--------------------------------------------------------------------------------------------------------------")
			self.indiLOG.log(50,"Line {} has error={}".format(sys.exc_info()[2].tb_lineno, e))
			self.indiLOG.log(50,"Error in startup of plugin, waiting for 2000 secs then restarting plugin")
			self.indiLOG.log(50,"--------------------------------------------------------------------------------------------------------------")
			for ii in range(2000):
				self.sleep(1)
			exit(1)

		self.lastSaveConfig = 0

		return



####-------------------------------------------------------------------------####
	def setGroupStatus(self, force=False):
		try:
			## check if we should do the group variable check now 
			if time.time() - self.setGroupStatusNextCheck < 0 and self.statusChanged == 0: return 
			if self.setGroupStatusNextCheck < 1: force = True
			#self.indiLOG.log(20,"setGroupStatus at:{};   dt:{}, statusChanged:{}".format(datetime.datetime.now(), time.time() - self.setGroupStatusNextCheck, self.statusChanged ))


			for group in  _GlobalConst_groupList+_GlobalConst_groupListDef:
				if group not in self.groupStatusList: 
					self.groupStatusList[group] = {}

				self.groupStatusList[group]["nAway"] = 0
				self.groupStatusList[group]["nHome"] = 0

			triggerGroup = {}
			for group in self.groupStatusList:
				triggerGroup[group]={"allHome":False, "allWay":False, "oneHome":False, "oneAway":False}


			okList =[]
			groupNamesUsed = []
			for group in _GlobalConst_groupList+_GlobalConst_groupListDef:
				groupNamesUsed.append(self.groupListUsedNames[group])
			#self.indiLOG.log(20,"setGroupStatus  groupNamesUsed:{}".format(groupNamesUsed))

			for dev in indigo.devices.iter(self.pluginId):
				#if dev.id == 1434599495: self.indiLOG.log(20,"setGroupStatus0  checking {}".format(dev.name))
				if "groupMember" not in dev.states: 	continue
				if not dev.enabled:						continue


				if dev.deviceTypeId  in ["rPI","rPI-Sensor","beacon","BLEconnect"]:
					for xx in _GlobalConst_groupListDef:
						if xx == "SENSOR": continue
						
						if dev.states["note"].lower().find(xx.lower()) >-1:
							if dev.states["status"] == "up":
								self.groupStatusList[xx]["nHome"]	+=1
								triggerGroup[xx]["oneHome"]			= True
							else:
								self.groupStatusList[xx]["nAway"]	+=1
								triggerGroup[xx]["oneHome"]			= False
						#if dev.deviceTypeId in "beacon": self.indiLOG.log(20,"setGroupStatus2  checking {}, status:{}".format(dev.name, dev.states["status"] ))
						okList.append("{}".format(dev.id))


				elif dev.pluginProps.get("isSensorDevice",False):
					if "groupMember" in dev.states and len(dev.states["groupMember"]) < 3: 
						dev.updateStateOnServer("groupMember","SENSOR")

					dt = (datetime.datetime.now() - dev.lastChanged).seconds
					up = dt < self.awayWhenNochangeInSeconds
					#self.indiLOG.log(10,"setGroupStatus1 {}, dt:{} , up:{}, self.awayWhenNochangeInSeconds:{}".format(dev.name, dt, up, self.awayWhenNochangeInSeconds))
					if up:
						self.groupStatusList["SENSOR"]["nHome"]	+=1
						triggerGroup["SENSOR"]["oneHome"]		= True
					else:
						triggerGroup["SENSOR"]["oneHome"]		= False
						self.groupStatusList["SENSOR"]["nAway"]	+=1
					#if dev.id == 1434599495: self.indiLOG.log(20,"setGroupStatus3  checking {}".format(dev.name))
					okList.append("{}".format(dev.id))

				memberOfGroupsInState = dev.states["groupMember"].split("/")
				usedMemberStates = ""
				for member in memberOfGroupsInState:
					if member in groupNamesUsed:
						usedMemberStates += member+"/"

				## update list if a) forced;  b) a group deleted; c) state is empty  
				usedMemberStates = usedMemberStates.strip("/")
				if force or usedMemberStates != dev.states["groupMember"]:
					valuesDict = self.fillMemberListState( dev, dev.pluginProps, updateNow=True)
					memberOfGroupsInState = valuesDict["memberList"].split("/")

				#self.indiLOG.log(20,"setGroupStatus  dev.name:{}, memberOfGroupsInState:{}".format(dev.name, memberOfGroupsInState))
				if memberOfGroupsInState == []: continue # this dev is not a member of any group
	
				for group in _GlobalConst_groupList:
					groupNameUsedForVar = self.groupListUsedNames[group]
					if groupNameUsedForVar == "": continue

					if groupNameUsedForVar not in memberOfGroupsInState: continue

					self.groupStatusList[group]["members"]["{}".format(dev.id)] = dev.name

					if  "onOffState" in dev.states:
						up = dev.states["onOffState"]
					else: # this is for sensor, if no update in the last xx secs -> not up (xx def is 600 secs)
						up = (datetime.datetime.now() - dev.lastChanged).seconds < self.awayWhenNochangeInSeconds or "onOffState" 

					if up:
						if self.groupStatusList[group]["oneHome"] == "0":
							triggerGroup[group]["oneHome"]			= True
							self.groupStatusList[group]["oneHome"]	= "1"
						self.groupStatusList[group]["nHome"]		+=1
					else:
						if self.groupStatusList[group]["oneAway"] == "0":
							triggerGroup[group]["oneAway"]			= True
						self.groupStatusList[group]["oneAway"]		= "1"
						self.groupStatusList[group]["nAway"]		+=1
							#if group =="Guests": self.indiLOG.log(20,"setGroupStatus2 {},  up:{}, nAway:{}, nHome:{}".format(dev.name, up, self.groupStatusList[group]["nAway"], self.groupStatusList[group]["nHome"]))


			# remove old ones
			for group in  _GlobalConst_groupList+_GlobalConst_groupListDef:
				removeList=[]
				for member in self.groupStatusList[group]["members"]:
					if member not in okList:
						removeList.append(member)
				for member in  removeList:
					del self.groupStatusList[group]["members"][member]
				if len(self.groupStatusList[group]["members"]) ==0:
					for tType in ["Home", "Away"]:
						varName = self.groupCountNameDefault+self.groupListUsedNames[group]+"_"+tType
						if varName in indigo.variables:
							indigo.variable.delete(varName)

			# now all home/ away 
			for group in _GlobalConst_groupList+_GlobalConst_groupListDef:
				#if group =="Guests":self.indiLOG.log(20,"setGroupStatus  group:{}, len(self.groupStatusList[group][members]:{}".format(group, len(self.groupStatusList[group]["members"])))
				if len(self.groupStatusList[group]["members"]) > 0 and self.groupStatusList[group]["nAway"] == len(self.groupStatusList[group]["members"]):
					if self.groupStatusList[group]["allAway"] == "0":
						triggerGroup[group]["allAway"] = True
					self.groupStatusList[group]["allAway"]	  = "1"
					self.groupStatusList[group]["oneHome"]	  = "0"
				else:
					self.groupStatusList[group]["allAway"]	  = "0"

				if len(self.groupStatusList[group]["members"]) > 0 and self.groupStatusList[group]["nHome"] == len(self.groupStatusList[group]["members"]):
					if self.groupStatusList[group]["allHome"] == "0":
						triggerGroup[group]["allHome"] = True
					self.groupStatusList[group]["allHome"]	  = "1"
					self.groupStatusList[group]["oneAway"]	  = "0"
				else:
					self.groupStatusList[group]["allHome"]	  = "0"


			# now fill variables
			#indigo.server.log("self.groupStatusList:{} ".format(self.groupStatusList))
			for group in _GlobalConst_groupList+_GlobalConst_groupListDef:
				groupNameUsedForVar = self.groupListUsedNames[group]
				#if group =="Guests":self.indiLOG.log(20,"setGroupStatus  group:{}, groupNameUsedForVar:{}, len(self.groupStatusList[group][members]):{}, ".format(group, groupNameUsedForVar, len(self.groupStatusList[group]["members"])))
				if len(groupNameUsedForVar)  == 0: 						continue
				if len(self.groupStatusList[group]["members"])  == 0: 	continue

				for tType in ["Home", "Away"]:
					varName = self.groupCountNameDefault+groupNameUsedForVar+"_"+tType
					gName="n"+tType
					try:
						var = indigo.variables[varName]
					except:
						indigo.variable.create(varName, "",self.iBeaconFolderVariablesName)
						var = indigo.variables[varName]

					#if group =="Guests":self.indiLOG.log(20,"var:{} group:{}, gName:{}, value:{}".format(var.name, group, gName, self.groupStatusList[group][gName] ))
					if var.value !=	 self.groupStatusList[group][gName]:
						indigo.variable.updateValue(varName, "{}".format(self.groupStatusList[group][gName]))


			if	self.statusChanged != 99 and len(self.triggerList) > 0:
				for group in triggerGroup:
					for tType in triggerGroup[group]:
						if triggerGroup[group][tType]:
							self.triggerEvent(group+"-"+tType)

		except Exception as e:
			self.exceptionHandler(40, e)
		self.setGroupStatusNextCheck = time.time() +  self.setGroupStatusrepeat
		self.statusChanged = 0
		return 

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
			return
		for trigId in self.triggerList:
			trigger = indigo.triggers[trigId]
			if trigger.pluginTypeId == eventId:
				indigo.trigger.execute(trigger)
		return




####-------------------------------------------------------------------------####
	def deleteAndCeateVariablesAndDeviceFolder(self, recreate):

		try:		indigo.devices.folder.create(self.iBeaconDevicesFolderName)
		except:		pass
		self.piFolderId = indigo.devices.folders[self.iBeaconDevicesFolderName].id


		try:		indigo.variables.folder.create(self.iBeaconFolderVariablesName)
		except:		pass


		if self.IndigoOrSocket	!= "socket":
				try:	indigo.variables.folder.create(self.iBeaconFolderVariableDataTransferVarsName)
				except:	pass

		### if configured:  delete at midnight and (re) create	to save sql logger space , we dont need the history
		if recreate:
			try:	indigo.variable.delete("pi_IN_Alive")
			except:	pass
			try:	indigo.variable.delete(self.ibeaconNameDefault+"With_Status_Change")
			except:	pass
			try:	indigo.variable.delete(self.ibeaconNameDefault+"With_ClosestRPI_Change")
			except:	pass
			try:	indigo.variable.delete(self.ibeaconNameDefault+"Rebooting")
			except:	pass
			try:	indigo.variable.delete(self.ibeaconNameDefault+"Rebooting")
			except:	pass

			for dev in indigo.devices.iter("props.isSensorDevice"):
				if dev.deviceTypeId ==  "lidar360":
					try:	indigo.variable.delete((dev.name+"_data").replace(" ", "_"))
					except:	pass


		try:	indigo.variable.create(self.ibeaconNameDefault+"With_Status_Change", "", self.iBeaconFolderVariablesName)
		except:	pass
		try:	indigo.variable.create(self.ibeaconNameDefault+"With_ClosestRPI_Change", "", self.iBeaconFolderVariablesName)
		except:	pass
		try:	indigo.variable.create(self.ibeaconNameDefault+"Rebooting", "", self.iBeaconFolderVariablesName)
		except:	pass

		for dev in indigo.devices.iter("props.isSensorDevice"):
			if dev.deviceTypeId ==  "lidar360":
				try:	indigo.variable.create((dev.name+"_data").replace(" ", "_"), "", self.iBeaconFolderVariablesName)
				except: pass
				try:	indigo.variable.create((dev.name+"_calibrated").replace(" ", "_"), "", self.iBeaconFolderVariablesName)
				except: pass


		if "lastButtonOnBeaconDevId" not in indigo.variables:
			indigo.variable.create("lastButtonOnBeaconDevId","", self.iBeaconFolderVariablesName)
		if "lastButtonOnDevId" not in indigo.variables:
			indigo.variable.create("lastButtonOnDevId","", self.iBeaconFolderVariablesName)



		if self.IndigoOrSocket	!= "socket":
			try:	indigo.variable.create("pi_IN_Alive", "", self.iBeaconFolderVariableDataTransferVarsName)
			except:	pass

			for piU in self.RPI:
				if recreate:
					try:	indigo.variable.delete("pi_IN_{}".format(piU) )
					except:	pass

				try:	indigo.variable.create("pi_IN_{}".format(piU), "", self.iBeaconFolderVariableDataTransferVarsName)
				except: pass

		try:	indigo.variable.create("lightningEventDate", "", self.iBeaconFolderVariablesName)
		except:	pass
		try:	indigo.variable.create("lightningEventDevices", "0", self.iBeaconFolderVariablesName)
		except:	pass


####-------------------------------------------------------------------------####
	def readTcpipSocketStats(self):
		self.dataStats = {}
		try:
			if os.path.isfile(self.indigoPreferencesPluginDir + "dataStats"):
				f = open(self.indigoPreferencesPluginDir + "dataStats", "r")
			else:
				self.resetDataStats()
				return
		except:
			self.resetDataStats()
			return
		try:
			self.dataStats = json.loads(f.read())
			try: f.close()
			except: pass
			if "updates" not in self.dataStats:
				self.resetDataStats()
				return
			if "nstates" not in self.dataStats["updates"]:
				self.resetDataStats()
				return
		except Exception as e:
			self.resetDataStats()
			self.exceptionHandler(40, e)
		if "data" not in self.dataStats:
			self.resetDataStats()

####-------------------------------------------------------------------------####
	def resetDataStats(self):
		self.dataStats={"startTime": time.time(), "data":{},"updates":{"devs":0, "states":0, "startTime": time.time(), "nstates":[0 for ii in range(11)]}}
		self.saveTcpipSocketStats()

####-------------------------------------------------------------------------####
	def saveTcpipSocketStats(self):
		self.writeJson(self.dataStats, fName=self.indigoPreferencesPluginDir + "dataStats", fmtOn=True )





####-------------------------------------------------------------------------####
####------================----------- garage door  ------================--------
####-------------------------------------------------------------------------####
	def initGarageDoors(self):
		self.garageData = {}
		self.garageData["garageIds"] = {}
		self.garageData["sensorIds"] = {}
		for dev in indigo.devices.iter("props.isgarageDoorDevice"):
			props = self.setupGarageDoor(dev, dev.pluginProps)
			dev.replacePluginPropsOnServer(props)
		return 


####-------------------------------------------------------------------------####
	def setupGarageDoor(self, dev, props):
		try:
			if dev.id not in self.garageData["garageIds"]:
				self.garageData["garageIds"][dev.id] = {}
			garage = self.garageData["garageIds"][dev.id]
			garage["newData"]				= False
			garage["closeSensorID"]			= int(props.get("closeSensor",0))
			garage["openSensorID"]			= int(props.get("openSensor",0))
			garage["movingSensorID"]		= int(props.get("movingSensor",0))
			garage["movingSensorStateName"]	= props["movingSensorState"]
			garage["numberOfMagnets"]		= float(props.get("numberOfMagnets", 0))
			garage["counter"]				= dev.states.get("position",0.)/ max(1.,garage["numberOfMagnets"])
			if dev.states["open"]:			garage["direction"] = -1
			else:							garage["direction"] = 1
			garage["textForClosing"]		= props.get("textForClosing","Closing")
			garage["textForOpening"]		= props.get("textForOpening","Opening")
			garage["textForClosed"]			= props.get("textForClosed", "Closed")
			garage["textForOpen"]			= props.get("textForOpen",   "Open")
			garage["textForStopped"]		= props.get("textForStopped","Stopped")
			garage["textForMoving"]			= props.get("textForMoving", "Moving")
			garage["directionSwitched"] 	= False
			garage["acceptableTimeBetweenMagnets"] 	= float(props.get("acceptableTimeBetweenMagnets", "4"))
			garage["dirInt"] = {-1:garage["textForClosing"], 1:garage["textForOpening"], 0:garage["textForMoving"]	}

			self.garageData["sensorIds"][int(props["closeSensor"])] 	= True
			self.garageData["sensorIds"][int(props["openSensor"])] 		= True
			self.garageData["sensorIds"][int(props["movingSensor"])] 	= True

			try:
				devOpen   = indigo.devices[garage["openSensorID"]]
				devClose  = indigo.devices[garage["closeSensorID"]]
				devMotion = indigo.devices[garage["movingSensorID"]]
				if devClose.states["onOffState"]: 	garage["direction"] = 1
				elif devOpen.states["onOffState"]:  garage["direction"] = -1
				else:								garage["direction"] = 0
				garage["counter"]					= dev.states["position"]/ garage["numberOfMagnets"]

				garage["openSensorStateValue"]		= devOpen.states["onOffState"]
				garage["closeSensorStateValue"]		= devClose.states["onOffState"]
				garage["movingSensorStateValue"]	= devMotion.states[garage["movingSensorStateName"]]
			except Exception as e:
				self.exceptionHandler(40, e)
				garage["openSensorStateValue"]		= ""
				garage["closeSensorStateValue"]		= ""
				garage["movingSensorStateValue"]	= ""
				garage["direction"] = 0
			if self.decideMyLog("GarageDoor"): self.indiLOG.log(10,"setupGarageDoor params:{}".format(dev.name, props))

			props["address"] = ""
			if garage["numberOfMagnets"] >0:
				props["address"] = "{} rail magnets installed".format(int(garage["numberOfMagnets"]))
		except Exception as e:
			self.exceptionHandler(40, e)
		return props

####-------------------------------------------------------------------------####
	def alertGarageDoor(self, sensId):
		try:
			if sensId not in self.garageData["sensorIds"]: return 

			for devId in self.garageData["garageIds"]:
				garage = self.garageData["garageIds"][devId]
				if sensId == garage["closeSensorID"]: 
					garage["newData"] = True

				elif sensId == garage["openSensorID"]: 
					garage["newData"] = True

				elif sensId == garage["movingSensorID"]: 
					garage["newData"] = True

		except Exception as e:
			self.exceptionHandler(40, e)
		return


####-------------------------------------------------------------------------####
	def checkGarageDoor(self):
		try:
			for devId in self.garageData["garageIds"]:
				garage = self.garageData["garageIds"][devId]
				if not garage["newData"]: continue

				dev = indigo.devices[devId]
				garage["newData"] = False

				devOpen			= indigo.devices[garage["openSensorID"]]
				devClose		= indigo.devices[garage["closeSensorID"]]
				devMove			= indigo.devices[garage["movingSensorID"]]

				moveState		= garage["movingSensorStateName"]
				moveOnOffState	= "onOffState"
				closeOnOffState	= "onOffState"
				openOnOffState	= "onOffState"

				lastMotion = dev.states["lastMotion"]
				closedSt = dev.states["closed"] 
				openedSt = dev.states["open"] 
				stoppedSt = dev.states["stopped"] 
				if   garage["direction"] == 1:	directionText	= garage["textForOpening"]
				elif garage["direction"] == -1:	directionText	= garage["textForClosing"]
				else: 							directionText	= garage["textForMoving"]
				if devMove.states[moveState] != garage["movingSensorStateValue"]:
					if devMove.states[moveOnOffState]:
						garage["counter"] += garage["direction"]	
						garage["counter"] = max( min(garage["numberOfMagnets"], garage["counter"]), 0.)
						self.addToStatesUpdateDict(devId, "status", directionText )
						dev.updateStateImageOnServer(indigo.kStateImageSel.SensorOff)
						lastMotion = datetime.datetime.now().strftime(_defaultDateStampFormat)
						self.addToStatesUpdateDict(devId, "lastMotion", lastMotion)
						self.addToStatesUpdateDict(devId, "stopped", False)
						self.addToStatesUpdateDict(devId, "open", False)
						self.addToStatesUpdateDict(devId, "closed", False)
						self.addToStatesUpdateDict(devId, "lastMagnetTriggered", garage["counter"])
						if self.decideMyLog("GarageDoor"): self.indiLOG.log(10,"garage door {} 1. setting Nclosed, Nopen, Nstopped, {}, lastMotion:{}".format(dev.name, directionText, lastMotion))
						garage["directionSwitched"] = False
						openedSt = False 
					else:
						self.addToStatesUpdateDict(devId, "status", garage["textForStopped"])
						self.addToStatesUpdateDict(devId, "lastStop", datetime.datetime.now().strftime(_defaultDateStampFormat))
						dev.updateStateImageOnServer(indigo.kStateImageSel.SensorTripped)
						self.addToStatesUpdateDict(devId, "stopped", True)
						garage["directionSwitched"] = False
						stoppedSt = True
						if self.decideMyLog("GarageDoor"): self.indiLOG.log(10,"garage door {} 2. setting stopped  {}".format(dev.name, garage["textForStopped"]))
					garage["movingSensorStateValue"] = devMove.states[moveState] 

				if devOpen.states[openOnOffState] != garage["openSensorStateValue"]:
					if devOpen.states[openOnOffState]:
						openedSt = True
						self.addToStatesUpdateDict(devId, "open", True)
						self.addToStatesUpdateDict(devId, "stopped", True)
						garage["counter"] = garage["numberOfMagnets"] +1 
						self.addToStatesUpdateDict(devId, "lastOpen", datetime.datetime.now().strftime(_defaultDateStampFormat))
						self.addToStatesUpdateDict(devId, "status", garage["textForOpen"])
						dev.updateStateImageOnServer(indigo.kStateImageSel.SensorOn)
						garage["directionSwitched"] = False
						if self.decideMyLog("GarageDoor"): self.indiLOG.log(10,"garage door {} 3. setting open, stopped  {}".format(dev.name, garage["textForOpen"]))
					garage["openSensorStateValue"] = devOpen.states[openOnOffState]

				if devClose.states[closeOnOffState] != garage["closeSensorStateValue"]:
					if devClose.states[closeOnOffState]:
						self.addToStatesUpdateDict(devId, "closed", True)
						self.addToStatesUpdateDict(devId, "stopped", True)
						garage["counter"] = 0
						self.addToStatesUpdateDict(devId, "lastClose", datetime.datetime.now().strftime(_defaultDateStampFormat))
						self.addToStatesUpdateDict(devId, "status", garage["textForClosed"])
						dev.updateStateImageOnServer(indigo.kStateImageSel.SensorOn)
						garage["directionSwitched"] = False
						if self.decideMyLog("GarageDoor"): self.indiLOG.log(10,"garage door {} 4. setting closed, stopped  {}".format(dev.name, garage["textForClosed"]))
						closedSt = True
						stoppedSt = True
					garage["closeSensorStateValue"] = devClose.states[closeOnOffState]

				if garage["numberOfMagnets"] > 0:
					posi = max(0, min(100, int( 100.*garage["counter"] / max(garage["numberOfMagnets"],1.) ) ))
				else:
					posi = 0
				self.addToStatesUpdateDict(devId, "position", posi, uiValue="{}%".format(posi) )

				if devClose.states["onOffState"]: 
					garage["direction"] = 1
					garage["directionSwitched"] = False
					garage["counter"] = 0
				if devOpen.states["onOffState"]:  
					garage["direction"] = -1
					garage["directionSwitched"] = False
					garage["counter"] = garage["numberOfMagnets"]

				if not devMove.states[moveOnOffState] and not stoppedSt:
					self.addToStatesUpdateDict(devId, "lastStop", datetime.datetime.now().strftime(_defaultDateStampFormat))
					self.addToStatesUpdateDict(devId, "status", garage["textForStopped"])
					self.addToStatesUpdateDict(devId, "stopped", True)
					if self.decideMyLog("GarageDoor"): self.indiLOG.log(10,"garage door {} 5. setting stopped {}, lastMovement:{}".format(dev.name, garage["textForStopped"], lastMotion))
					stoppedSt = True

				### this is for stuck in between 
				if  ( stoppedSt 
					and not closedSt 
					and not openedSt
					and not garage["directionSwitched"]):
						secsWoMovement = (datetime.datetime.now() - datetime.datetime.strptime(lastMotion, _defaultDateStampFormat)).total_seconds()
						if secsWoMovement > garage["acceptableTimeBetweenMagnets"]:
							garage["direction"] *= -1
							garage["directionSwitched"] = True
							if self.decideMyLog("GarageDoor"): self.indiLOG.log(10,"garage door {} 6.  reversing direction due to long stop inbetween signals ({} > {} ), new direction = {}".format(dev.name, secsWoMovement, garage["acceptableTimeBetweenMagnets"], garage["dirInt"][garage["direction"]]))


				self.executeUpdateStatesDict(onlyDevID=devId)
		except Exception as e:
			self.exceptionHandler(40, e, extraText="self.garageData:{}".format(self.garageData))
		return
####-------------------------------------------------------------------------####
####------================----------- garage door   END ==============-----------
####-------------------------------------------------------------------------####







####------================----------- CARS ------================-----------
####-------------------------------------------------------------------------####
	def saveCARS(self, force=False):
		try:
			if force: 
				for carId in copy.deepcopy(self.CARS["carId"]):
					try: indigo.devices[int(carId)]
					except Exception as e:
						self.exceptionHandler(40, e)
						if "{}".format(e).find("timeout waiting") > -1:
							self.indiLOG.log(40,"communication to indigo is interrupted")
							return
						self.indiLOG.log(40,"devId {} not defined in devices removing from	 CARS:{}".format(carId, self.CARS) )
						del self.CARS["carId"][carId]
						continue

					if "homeSince"	not in self.CARS["carId"][carId]:	 self.CARS["carId"][carId]["homeSince"] = 0
					if "awaySince"	not in self.CARS["carId"][carId]:	 self.CARS["carId"][carId]["awaySince"] = 0
					if "beacons"	not in self.CARS["carId"][carId]:	 self.CARS["carId"][carId]["beacons"]   = {}
					for beacon in self.CARS["carId"][carId]["beacons"] :
						if beacon not in self.beacons:
							del self.CARS["carId"][carId]["beacons"][beacon]

				for beacon in copy.deepcopy(self.CARS["beacon"]):
					if self.CARS["beacon"][beacon]["carId"] not in self.CARS["carId"]:
						del self.CARS["beacon"][beacon]

			self.writeJson(self.CARS, fName=self.indigoPreferencesPluginDir + "CARS" )
		except Exception as e:
			self.exceptionHandler(40, e)

####-------------------------------------------------------------------------####
	def readCARS(self):
		self.checkCarsNeed = {}
		self.CARS = {}
		self.lastCARupdate  = time.time()

		xxx={"carId":{}, "beacon":{}}
		try:
			try:
				f = open(self.indigoPreferencesPluginDir + "CARS", "r")
				xxx = json.loads(f.read())
				f.close()
			except:
				self.sleep(1)
				try:
					f = open(self.indigoPreferencesPluginDir + "CARS", "r")
					xxx = json.loads(f.read())
					f.close()
				except Exception as e:
					xxx={"carId":{}, "beacon":{}}

			self.CARS = {"carId":{}, "beacon":{}}

			for dev in indigo.devices.iter("props.isCARDevice"):
				self.CARS["carId"][str(dev.id)] = {}
				props = dev.pluginProps
				self.CARS["carId"][str(dev.id)] = {"homeSince":0, "awaySince":0, "beacons":{}}

				if str(dev.id) in xxx["carId"]:
					self.CARS["carId"][str(dev.id)]["homeSince"] = xxx["carId"][str(dev.id)]["homeSince"]
					self.CARS["carId"][str(dev.id)]["awaySince"] = xxx["carId"][str(dev.id)]["awaySince"]

				for bType in ["beaconBattery","beaconUSB","beaconKey0","beaconKey1","beaconKey2"]:
					bTId = props.get(bType,"")
					if bTId != "":
						try:
							beacon = indigo.devices[int(bTId)].address
						except:
							self.indiLOG.log(30,"readCARS in {} beacon does not exist, please remove beacon ID:{}".format(dev.name, bTId))
							continue
						self.CARS["beacon"][beacon] = {"beaconType": bType,"carId":str(dev.id)}
						self.CARS["carId"][str(dev.id)]["beacons"][beacon] = str(dev.id)

			if self.decideMyLog("CAR"): self.indiLOG.log(10,"readCARS cars:{}".format(self.CARS))

			for carIds in self.CARS["carId"]:
				self.updateAllCARbeacons(carIds)

			self.saveCARS()

		except Exception as e:
			self.exceptionHandler(40, e)



####-------------------------------------------------------------------------####
	def checkIfupdateCARStimeHasCome(self):
		try:
			if time.time() - self.lastCARupdate > 300:
				for carId in self.CARS["carId"]:
					self.checkCarsNeed[carId] = time.time() - 5
				self.lastCARupdate  = time.time()
			self.checkIfCarsNeedUpdate()
		except Exception as e:
			self.exceptionHandler(40, e)
		return 



####-------------------------------------------------------------------------####
	def checkIfCarsNeedUpdate(self):
		try:
			if len(self.checkCarsNeed) == 0: return 
			for carId in copy.copy(self.checkCarsNeed):
				if time.time() > self.checkCarsNeed[carId]:
					if self.decideMyLog("CAR"): self.indiLOG.log(30,"checkIfCarsNeedUpdate:  updating id:{} ".format(carId) )
					self.updateAllCARbeacons(carId)

		except Exception as e:
			self.exceptionHandler(40, e)

		return

####-------------------------------------------------------------------------####
	def updateAllCARbeacons(self, indigoCarIds, force=False):
		beacon = ""
		try:
			if self.decideMyLog("CAR"): self.indiLOG.log(10,"updateAllCARbeacons  CARS:{}".format(self.CARS))
			savetoFile = False

			copCars = copy.deepcopy(self.CARS)
			for carId in copCars["carId"]:
				for beacon in copCars["carId"][carId]["beacons"]:
					if beacon not in self.beacons:
						self.indiLOG.log(30,"CARS: beacon used :{}  not found in beacons dict, removing from CARS:{} ".format(beacon, self.CARS["carId"][carId]["beacons"]) )
						del self.CARS["carId"][carId]["beacons"][beacon]
						savetoFile = True

			for beacon in copy.deepcopy(self.CARS["beacon"]):
				if indigoCarIds != self.CARS["beacon"][beacon]["carId"] and not force: continue
				if beacon not in self.beacons:
					if self.decideMyLog("CAR"): self.indiLOG.log(30,"CARS:  {} beacon: not found in beacons dict, removing from CARS:{} ".format(beacon, self.CARS) )
					del self.CARS["beacon"][beacon]
					savetoFile = True
					continue
				beaconDevId = self.beacons[beacon]["indigoId"]
				beaconDev	= indigo.devices[beaconDevId]
				if self.decideMyLog("CAR"): self.indiLOG.log(5,"updating all cars")
				self.updateCARS(beacon, beaconDev, beaconDev.states["status"], force=True)
				break

			if savetoFile: self.saveCARS(force=True)

		except Exception as e:
			self.exceptionHandler(40, e, extraText="deleted beacon? .. car beacons beacon#  {}\nfor   indigoCarId {}".format(beacon, indigoCarIds) )

####-------------------------------------------------------------------------####
	def updateCARS(self, beacon, beaconDev, newBeaconStatus, force=False):
		try:
			if beacon not in self.CARS["beacon"]: return
			if not self.isValidMAC(beacon): return

			indigoCarIds = "{}".format(self.CARS["beacon"][beacon]["carId"])
			if indigoCarIds not in self.CARS["carId"]: # pointer to indigo ID
				self.indiLOG.log(30,"{} beacon: not found in CARS[carId], removing from dict;  CARSdict: {}".format(beacon, "{}".format(self.CARS)) )
				del self.CARS["beacon"][beacon]
				return

			####  car status:
			#		Home/away , engine= on/off/unknown, motion: arriving/leaving/ stop

			indigoIDofBeacon = beaconDev.id
			carDev			 = indigo.devices[int(indigoCarIds)]
			if not carDev.enabled: return
			props			 = carDev.pluginProps
			carName			 = carDev.name



			try:	whatForStatus = carDev.pluginProps["displayS"]
			except: whatForStatus = ""
			if whatForStatus == "": whatForStatus = "location"

			oldCarStatus	= carDev.states["location"]
			oldCarEngine	= carDev.states["engine"]
			oldCarMotion	= carDev.states["motion"]
			oldBeaconStatus	= beaconDev.states["status"]
			beaconType		= self.CARS["beacon"][beacon]["beaconType"]
			beaconBattery	= "noChange"
			beaconUSB		= "noChange"
			beaconKey		= "present"
			nKeysFound		= 0
			oldAwaySince = self.CARS["carId"][indigoCarIds]["awaySince"]
			oldHomeSince = self.CARS["carId"][indigoCarIds]["homeSince"]
			if self.decideMyLog("CAR"): self.indiLOG.log(10,"{}-{} -1- {} updating {}, oldBeaconStatus={}, newBeaconStatus={}  oldAwaySince:{}  oldHomeSince:{}, oldCarStatus={}, oldCarEngine={}, oldCarMotion={}".format(carName, indigoCarIds, beacon, beaconType, oldBeaconStatus, newBeaconStatus, time.time()-oldAwaySince, time.time()-oldHomeSince, oldCarStatus, oldCarEngine, oldCarMotion) )

			if beaconType == "beaconBattery":
				if newBeaconStatus	== "up": beaconBattery = "present"	## battery beacon is home
				else:						  beaconBattery = "away"

			if beaconType == "beaconUSB":
				if newBeaconStatus	== "up": beaconUSB	    = "on"	## usb beacon is home
				else:						  beaconUSB	    = "off"

			if beaconType.find("beaconKey")>-1:
				if newBeaconStatus	!= "up":  beaconKey	    = "away"   # at least one is missing
				nKeysFound	+= 1

			for b in self.CARS["carId"][indigoCarIds]["beacons"]:
				beaconTypeTest = self.CARS["beacon"][b]["beaconType"]
				if beaconTypeTest == beaconType: continue
				if indigoCarIds != "{}".format(self.CARS["beacon"][b]["carId"]): continue
				indigoDEV  = indigo.devices[self.beacons[b]["indigoId"]]
				st = indigoDEV.states["status"]
				if self.decideMyLog("CAR"): self.indiLOG.log(10,"{}-{} -2- testing dev={}  st={}".format(carName, indigoCarIds, indigoDEV.name, st) )

				if beaconTypeTest == "beaconBattery":
					if st  =="up": beaconBattery 	= "present" ## battery beacon is home
					else:			beaconBattery 	= "away"

				if beaconTypeTest == "beaconUSB":
					if st  =="up": beaconUSB		 = "on"  ## usb beacon is home
					else:			beaconUSB		 = "off"

				if beaconTypeTest.find("beaconKey")>-1:
					if st  != "up": beaconKey		= "away"
					nKeysFound += 1

			if nKeysFound == 0:		beaconKey		= "away"

			if indigoCarIds in self.checkCarsNeed: del self.checkCarsNeed[indigoCarIds]

			updateProps = False
			if "address" not in props:
				props["address"] = "away"
				updateProps = True

			if (beaconBattery == "present" or beaconUSB == "on" or beaconKey == "present") and props["address"] == "away":
				props["address"] = "home"
				updateProps = True

			elif not (beaconBattery == "present" or beaconUSB == "on" or beaconKey == "present") and props["address"] == "home":
				props["address"] = "away"
				updateProps = True

			self.addToStatesUpdateDict(indigoCarIds, "motion",carDev.states["motion"])

			if  beaconUSB == "on":
				self.addToStatesUpdateDict(indigoCarIds, "engine", "on")
			else:
				self.addToStatesUpdateDict(indigoCarIds, "engine", "off")

			if beaconBattery == "present" or beaconUSB == "on" or beaconKey == "present":	#some thing is on== home
				if self.decideMyLog("CAR"): self.indiLOG.log(10,"{} -3-  setting to be home,   oldCarStatus: {}".format(carName ,oldCarStatus) )
				self.addToStatesUpdateDict(indigoCarIds, "location", "home")
				if oldCarStatus != "home":
					self.CARS["carId"][indigoCarIds]["homeSince"] = time.time()
					self.addToStatesUpdateDict(indigoCarIds, "LastArrivalAtHome",datetime.datetime.now().strftime(_defaultDateStampFormat))

			else:	  # nothing on, we are away
				self.addToStatesUpdateDict(indigoCarIds, "location", "away")
				if oldCarStatus != "away":
					self.setIcon(carDev,props, "SensorOff-SensorOn",0)
					self.CARS["carId"][indigoCarIds]["awaySince"] = time.time()
					self.addToStatesUpdateDict(indigoCarIds, "LastLeaveFromHome",datetime.datetime.now().strftime(_defaultDateStampFormat))
				self.addToStatesUpdateDict(indigoCarIds, "motion", "left")
				self.addToStatesUpdateDict(indigoCarIds, "engine", "unknown")
				if indigoCarIds in self.checkCarsNeed: del self.checkCarsNeed[indigoCarIds]



			if self.decideMyLog("CAR"): self.indiLOG.log(10,"{}-{} -4- update states: type:{}    bat={}    USB={}    Key={}    car newawayFor={:.0f}[secs] newhomeFor={:.0f}[secs]".format(carName, indigoCarIds, beaconType, beaconBattery, beaconUSB, beaconKey, time.time()-self.CARS["carId"][indigoCarIds]["awaySince"], time.time()-self.CARS["carId"][indigoCarIds]["homeSince"] ) )

			if oldCarStatus == "away":

				if beaconBattery == "present" or beaconUSB == "on" or beaconKey == "present":
					self.setIcon(carDev,props, "SensorOff-SensorOn",1)
					if time.time() - self.CARS["carId"][indigoCarIds]["awaySince"]  > 120: # just arriving home, was away for some time
						self.addToStatesUpdateDict(indigoCarIds, "motion", "arriving")
						if indigoCarIds in self.checkCarsNeed: del self.checkCarsNeed[indigoCarIds]

					else : # is this a fluke?
						self.addToStatesUpdateDict(indigoCarIds, "motion", "unknown")
						self.checkCarsNeed[indigoCarIds]= time.time() + 20

				elif indigoCarIds in self.updateStatesDict and "location" in self.updateStatesDict[indigoCarIds] and self.updateStatesDict[indigoCarIds]["location"]["value"] == "home":
						self.indiLOG.log(30,"{}-{}; -5- beacon: {} bad state , coming home, but no beacon is on".format(carName, indigoCarIds, beacon) )
						self.checkCarsNeed[indigoCarIds]= time.time() + 20

				if carDev.states["LastLeaveFromHome"] == "": self.addToStatesUpdateDict(indigoCarIds, "LastLeaveFromHome",datetime.datetime.now().strftime(_defaultDateStampFormat))



			else:  ## home
				if (beaconBattery == "present" or beaconUSB == "on" or beaconKey == "present"):

					if	beaconUSB == "off" : # engine is off
						if	 oldCarMotion == "arriving" and time.time() - self.CARS["carId"][indigoCarIds]["homeSince"] > 10:
								self.addToStatesUpdateDict(indigoCarIds, "motion", "stop")

						elif oldCarMotion == "leaving"	and time.time() - self.CARS["carId"][indigoCarIds]["homeSince"] > 200:
								self.addToStatesUpdateDict(indigoCarIds, "motion", "stop")

						elif oldCarMotion == "left"	and time.time() - self.CARS["carId"][indigoCarIds]["homeSince"] < 60:
								self.addToStatesUpdateDict(indigoCarIds, "motion", "arriving")

						elif oldCarMotion == "":
								self.addToStatesUpdateDict(indigoCarIds, "motion", "stop")

						elif oldCarMotion == "unknown":
								self.addToStatesUpdateDict(indigoCarIds, "motion", "stop")

						elif oldCarMotion == "stop":
								pass
						else:
								self.checkCarsNeed[indigoCarIds]= time.time() + 20

					if	beaconUSB == "on" : # engine is on
						if time.time() - self.CARS["carId"][indigoCarIds]["homeSince"] > 600:
							self.addToStatesUpdateDict(indigoCarIds, "motion", "leaving")

						elif time.time() - self.CARS["carId"][indigoCarIds]["homeSince"] > 60 and oldCarMotion == "stop":
							self.addToStatesUpdateDict(indigoCarIds, "motion", "leaving")

						elif time.time() - self.CARS["carId"][indigoCarIds]["homeSince"] < 30 and oldCarMotion in ["unknown", "leaving"]:
							self.addToStatesUpdateDict(indigoCarIds, "motion", "arriving")

						else:
							self.checkCarsNeed[indigoCarIds]= time.time() + 20

				else:
					self.checkCarsNeed[indigoCarIds]= time.time() + 20

				if carDev.states["LastArrivalAtHome"] == "": self.addToStatesUpdateDict(indigoCarIds, "LastArrivalAtHome",datetime.datetime.now().strftime(_defaultDateStampFormat))

			if updateProps:

					carDev.replacePluginPropsOnServer(props)
					carDev	= indigo.devices[int(indigoCarIds)]

			if indigoCarIds in self.updateStatesDict and "location" in self.updateStatesDict[indigoCarIds]:
				st= ""
				whatForStatus = whatForStatus.split("/")
				if "location" in whatForStatus: st =	   self.updateStatesDict[indigoCarIds]["location"]["value"]
				if "engine"   in whatForStatus: st +="/"+ self.updateStatesDict[indigoCarIds]["engine"]["value"]
				if "motion"   in whatForStatus: st +="/"+ self.updateStatesDict[indigoCarIds]["motion"]["value"]
				st = st.strip("/").strip("/")
				self.addToStatesUpdateDict(indigoCarIds, "status",st)
				# double check if not already processed somewhere else
				if self.updateStatesDict[indigoCarIds]["location"]["value"] == "home":
					carDev.updateStateImageOnServer(indigo.kStateImageSel.SensorOn)
				else:
					carDev.updateStateImageOnServer(indigo.kStateImageSel.SensorTripped)

			if self.decideMyLog("CAR"): self.indiLOG.log(10,"{}-{} -6- update states: type:{}     car newawayFor={:.0f}[secs]; newhomeFor={:.0f}[secs]".format(carName, indigoCarIds, beaconType, time.time() - self.CARS["carId"][indigoCarIds]["awaySince"], time.time() - self.CARS["carId"][indigoCarIds]["homeSince"] ) )
			if indigoCarIds in self.checkCarsNeed:
				if self.decideMyLog("CAR"): self.indiLOG.log(10,"{}-{} -7- update states:  checkCarsNeed last={:.0f}[secs]".format(carName, indigoCarIds, (time.time() - self.checkCarsNeed[indigoCarIds])))
			if self.decideMyLog("CAR"): self.indiLOG.log(10,"{}-{} -8- updateStatesList: {}".format(carName, indigoCarIds, self.updateStatesDict) )
		except Exception as e:
			self.exceptionHandler(40, e)


		return


####-------------------------------------------------------------------------####
	def setupCARS(self, carIdi, props, mode=""):
		try:
			carIds= "{}".format(carIdi)
			if carIds not in self.CARS["carId"]:
				self.CARS["carId"][carIds]= {}
			if "homeSince" not in self.CARS["carId"][carIds]:	 self.CARS["carId"][carIds]["homeSince"] = 0
			if "awaySince" not in self.CARS["carId"][carIds]:	 self.CARS["carId"][carIds]["awaySince"] = 0
			if "beacons"	not in self.CARS["carId"][carIds]:	 self.CARS["carId"][carIds]["beacons"]   = {}
			update, text = self.setupBeaconsForCARS(props, carIds)

		except Exception as e:
			self.exceptionHandler(40, e)
			if "{}".format(e).find("timeout waiting") > -1:
				self.indiLOG.log(40,"communication to indigo is interrupted")
			self.indiLOG.log(40,"devId {} indigo lookup/save problem".format(carIds))
			return

		try:
			if mode in ["init", "validate"]:
				if self.decideMyLog("CAR"): self.indiLOG.log(10,"setupCARS updating states mode:{};  updateStatesList: {}".format(mode, self.updateStatesDict))
				if "description" not in props: props["description"] = ""
				if props["description"] != text:
					props["description"]= text

					dev = indigo.devices[carIdi]
					dev.replacePluginPropsOnServer(props)
				self.executeUpdateStatesDict(onlyDevID=carIds,calledFrom = "setupCARS")
			if update:
				self.setALLrPiV("piUpToDate", ["updateParamsFTP"])
		except Exception as e:
			self.exceptionHandler(40, e)
			return props
		return	props

####-------------------------------------------------------------------------####
	def setupBeaconsForCARS(self, propsCar, carIds):
		try:
			beaconList=[]
			text = "Beacons:"
			update = False
			if "setFastDown" in propsCar and propsCar["setFastDown"] != "0":
				setFastDown = int(propsCar["setFastDown"])
			else:
				setFastDown = -1

			for beaconType in propsCar:
				if beaconType.find("beacon") == -1: continue
				try: beaconID= int(propsCar[beaconType])
				except: continue
				if int(beaconID) == 0: continue
				try:  beaconDev = indigo.devices[beaconID]
				except: continue
				beacon = beaconDev.address
				beaconList.append(beacon)
				self.CARS["beacon"][beacon]= {"carId":carIds, "beaconType":beaconType}
				if beacon not in self.CARS["carId"][carIds]["beacons"]:  self.CARS["carId"][carIds]["beacons"][beacon] = beaconID
				text += beaconType.split("beacon")[1] + "=" + beaconDev.name + ";"
				props = beaconDev.pluginProps
				if setFastDown >= 0 and props["fastDown"] != str(setFastDown):
					props["fastDown"] =  str(setFastDown)
					if self.decideMyLog("CAR"): self.indiLOG.log(10,"updating fastdown for {} to {}".format(beaconDev.name, setFastDown) )
					update=True

					beaconDev.replacePluginPropsOnServer(props)
				delB={}
				for b in self.CARS["carId"][carIds]["beacons"]:
					if b not in self.CARS["beacon"] or b not in beaconList:
						delB[b]=1
				for b in delB:
					del self.CARS["carId"][carIds]["beacons"][b]
					del self.CARS["beacon"][b]
		except Exception as e:
			self.exceptionHandler(40, e)
			if "{}".format(e).find("timeout waiting") > -1:
				self.indiLOG.log(40,"communication to indigo is interrupted")
				return False,""
			self.indiLOG.log(40,"devId: {}; indigo lookup/save problem,  in props:{}   CARS:{}".format(carIds, "{}".format(props), self.CARS))
		return update,text.strip(";")



####------================----------- CARS ------================-----------END


####------================------- sprinkler ------================-----------
	########################################
	# Sprinkler Control Action callback
	######################
	def actionControlSprinkler(self, action, dev):
		props		= dev.pluginProps
		#indigo.server.log("actionControlSprinkler: {}".format(props)+"\n\n{}".format(action))
		piU			= props["piServerNumber"]
		ipNumberPi	= self.RPI[piU]["ipNumberPi"]
		devId		= int(self.RPI[piU]["piDevId"])
		deviceDefs	= [{"gpio":-1, "outType":1}]
		dictForRPI	= {"cmd":"", "OUTPUT":0, "deviceDefs":json.dumps(deviceDefs), "typeId": "OUTPUTgpio-1", "outputDev": "Sprinkler", "piServerNumber": piU, "ipNumberPi":ipNumberPi, "nPulses":0, "devId":devId}

		### !!!	 zoneindex goes from 1 ... n !!!

		########################################
		# Required plugin sprinkler actions: These actions must be handled by the plugin.
		########################################
		###### ZONE ON ######
		if action.sprinklerAction == indigo.kSprinklerAction.ZoneOn:
			# first reset all relays -- besides the new and controll
			if props["PumpControlOn"]: nValves = dev.zoneCount-1
			else: nValves = dev.zoneCount
			try:	activeZone = int(int(action.zoneIndex))
			except: activeZone = 0
			if activeZone == 0: return

			GPIOpin			   = []
			cmd				   = []
			inverseGPIO		   = []
			for nn in range(nValves):
				if nn+1 == int(action.zoneIndex):							 continue
				##if nn-1 ==  nValves and dev.pluginprops["PumpControlOn"]: continue
				GPIOpin.append(props["GPIOzone{}".format(nn+1)])
				dictForRPI["deviceDefs"] = json.dumps(deviceDefs)
				cmd.append("down")
				if "relayOnIfLow" in props and not props["relayOnIfLow"]:
					inverseGPIO.append(False)
				else:
					inverseGPIO.append(True)
			self.sendGPIOCommands( ipNumberPi, piU, cmd, GPIOpin, inverseGPIO)
			if props["PumpControlOn"]: # last valve is the control valve
				deviceDefs[0]["gpio"]	   = props["GPIOzone{}".format(dev.zoneCount)]
				dictForRPI["deviceDefs"] = json.dumps(deviceDefs)
				dictForRPI["cmd"]		   =  "pulseUp"
				dictForRPI["pulseUp"]	   = dev.zoneMaxDurations[action.zoneIndex-1]*60
				if "relayOnIfLow" in props and not props["relayOnIfLow"]:
					dictForRPI["inverseGPIO"] = False
				else:
					dictForRPI["inverseGPIO"] = True
				self.setPin(dictForRPI)

			self.sleep(0.1)	   ## we need to wait until all gpios are of, other wise then next might be before one of the last off
			deviceDefs[0]["gpio"]		= props["GPIOzone{}".format(action.zoneIndex)]
			dictForRPI["deviceDefs"]	= json.dumps(deviceDefs)
			dictForRPI["cmd"]			=  "pulseUp"
			dictForRPI["pulseUp"]		= dev.zoneMaxDurations[action.zoneIndex-1]*60
			if "relayOnIfLow" in props and not props["relayOnIfLow"]:
				dictForRPI["inverseGPIO"] = False
			else:
				dictForRPI["inverseGPIO"] = True
			self.setPin(dictForRPI)

			durations		 = dev.zoneScheduledDurations
			zoneMaxDurations = dev.zoneMaxDurations
			activeZone		 = int(int(action.zoneIndex))
			zoneStarted		 = datetime.datetime.now().strftime(_defaultDateStampFormat)
			timeLeft = 0
			dur = 0
			if activeZone > 0:
				secDone = (datetime.datetime.now() - datetime.datetime.strptime(zoneStarted, _defaultDateStampFormat)).total_seconds()
				minutes	 = int(secDone/60)


				if len(durations) == nValves:
					dur		= min(durations[activeZone-1], zoneMaxDurations[activeZone-1]) + 0.2
					allDur = 0.1
					for mm in durations:
						allDur += mm
					allMinutes = 0.1
					if len(durations) >= activeZone > 1:
						for mm in durations[0:activeZone-1]:
							allMinutes += mm
				else : # single zone manual, check if overwrite max duration
					if "sprinklerActiveZoneSetManualDuration" in indigo.variables:
						try:	dur = max(0,float(indigo.variables["sprinklerActiveZoneSetManualDuration"].value ) )
						except Exception as e:
							self.exceptionHandler(40, e)
							dur = 0
					if dur == 0:  # no overwrite, use max duration
								dur = zoneMaxDurations[activeZone-1]
					allMinutes = 0
					allDur = dur

				timeLeft	= int(max(0,(dur )))
				timeLeftAll = int(max(0,allDur-allMinutes +0.1) )
				dur			= int(dur)
				allDur		= int(allDur)

				self.addToStatesUpdateDict(dev.id, "activeZone",				 action.zoneIndex)
				self.addToStatesUpdateDict(dev.id, "activeZoneStarted",		 datetime.datetime.now().strftime(_defaultDateStampFormat))
				self.addToStatesUpdateDict(dev.id, "activeZoneMinutesLeft",	 timeLeft)
				self.addToStatesUpdateDict(dev.id, "activeZoneMinutesDuration", dur)
				self.addToStatesUpdateDict(dev.id, "allZonesMinutesDuration",	 allDur)
				self.addToStatesUpdateDict(dev.id, "allZonesMinutesLeft",		 timeLeftAll)

		###### ALL ZONES OFF ######
		elif action.sprinklerAction == indigo.kSprinklerAction.AllZonesOff:
			nValves = dev.zoneCount
			GPIOpin =[]
			cmd=[]
			inverseGPIO =[]
			for nn in range(nValves):
				GPIOpin.append(props["GPIOzone{}".format(nn+1)])
				dictForRPI["deviceDefs"] = json.dumps(deviceDefs)
				cmd.append("down")
				if "relayOnIfLow" in props and not props["relayOnIfLow"]:
					inverseGPIO.append(False)
				else:
					inverseGPIO.append(True)
			self.sendGPIOCommands( ipNumberPi, piU, cmd, GPIOpin, inverseGPIO)
			self.addToStatesUpdateDict(dev.id, "activeZoneStarted",		"")
			self.addToStatesUpdateDict(dev.id, "activeZone",				 0)
			self.addToStatesUpdateDict(dev.id, "activeZoneMinutesLeft",	 0)
			self.addToStatesUpdateDict(dev.id, "activeZoneMinutesDuration", 0)
			self.addToStatesUpdateDict(dev.id, "allZonesMinutesLeft",		 0)
			self.addToStatesUpdateDict(dev.id, "allZonesMinutesDuration",	 0)

		self.executeUpdateStatesDict(onlyDevID=dev.id, calledFrom="")
		return



####-------------------------------------------------------------------------####
	def initSprinkler(self, force = False):
		#self.lastSprinklerStats = "2018-05-31 23:23:00"
		self.lastSprinklerStats = datetime.datetime.now().strftime(_defaultDateStampFormat)

		for dev in indigo.devices.iter("props.isSprinklerDevice"):
			self.sprinklerDeviceActive = True
			for xx in ["minutesRunToday", "minutesRunThisWeek", "minutesRunYesterday", "minutesRunLastWeek", "minutesRunThisMonth", "minutesRunLastMonth"]:
				lastList = dev.states[xx].split(",")
				if len(lastList) != dev.zoneCount or force:
					lastList = ["0" for ii in range(dev.zoneCount)]
					lastList = ",".join(lastList)
					self.addToStatesUpdateDict(dev.id,xx,lastList)

			self.executeUpdateStatesDict(onlyDevID=dev.id)


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
					self.addToStatesUpdateDict(dev.id, "minutesRunYesterday",dev.states["minutesRunToday"])
					lastList = ["0" for ii in range(dev.zoneCount)]
					lastList = ",".join(lastList)
					self.addToStatesUpdateDict(dev.id, "minutesRunToday",lastList)

					if newWeek:
						self.addToStatesUpdateDict(dev.id, "minutesRunLastWeek",dev.states["minutesRunThisWeek"])
						lastList = ["0" for ii in range(dev.zoneCount)]
						lastList = ",".join(lastList)
						self.addToStatesUpdateDict(dev.id, "minutesRunThisWeek",lastList)

					if newMonth:
						self.addToStatesUpdateDict(dev.id, "minutesRunLastMonth",dev.states["minutesRunThisMonth"])
						lastList = ["0" for ii in range(dev.zoneCount)]
						lastList = ",".join(lastList)
						self.addToStatesUpdateDict(dev.id, "minutesRunThisMonth",lastList)

					self.executeUpdateStatesDict(onlyDevID=dev.id)



			for dev in indigo.devices.iter("props.isSprinklerDevice"):
				props			   = dev.pluginProps
				try:	activeZone = int(dev.states["activeZone"])
				except: activeZone = 0
				if activeZone == 0:
					self.addToStatesUpdateDict(dev.id, "activeZoneMinutesLeft",	 0)
					self.addToStatesUpdateDict(dev.id, "activeZoneMinutesDuration", 0)
					self.addToStatesUpdateDict(dev.id, "allZonesMinutesLeft",		 0)
					self.addToStatesUpdateDict(dev.id, "allZonesMinutesDuration",	 0)

				else:
					if props["PumpControlOn"]: nValves = dev.zoneCount-1
					else: nValves	 = dev.zoneCount
					durations		 = dev.zoneScheduledDurations
					zoneMaxDurations = dev.zoneMaxDurations
					zoneStarted		 = dev.states["activeZoneStarted"] # show date time when started . long string

					if len(zoneStarted) > 10:  # show date time when started . long string
						secDone = (datetime.datetime.now() - datetime.datetime.strptime(zoneStarted, _defaultDateStampFormat)).total_seconds()
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


						self.addToStatesUpdateDict(dev.id, "activeZoneMinutesLeft",   timeLeft)
						self.addToStatesUpdateDict(dev.id, "allZonesMinutesLeft",	   timeLeftAll)

					else: # show date time when started .if short , not started
						self.addToStatesUpdateDict(dev.id, "activeZoneMinutesLeft",   0)
						self.addToStatesUpdateDict(dev.id, "allZonesMinutesLeft",	   0)


					for xx in ["minutesRunToday", "minutesRunThisWeek", "minutesRunThisMonth"]:
						lastList = dev.states[xx].split(",")
						if len(lastList) != dev.zoneCount:
							lastList = ["0" for ii in range(dev.zoneCount)]
						lastList[activeZone-1] = "{}".format( int(lastList[activeZone-1])+1 )
						if props["PumpControlOn"] :
							lastList[dev.zoneCount-1] = "{}".format( int(lastList[dev.zoneCount-1])+1 )
						lastList = ",".join(lastList)
						self.addToStatesUpdateDict(dev.id,xx,lastList)


				self.executeUpdateStatesDict(onlyDevID=dev.id)
		except Exception as e:
			self.exceptionHandler(40, e)

####------================------- sprinkler ------================-----------END


####-------------------------------------------------------------------------####
	def readConfig(self):  ## only once at startup
		try:

			self.readTcpipSocketStats()


			self.RPI = self.getParamsFromFile(self.indigoPreferencesPluginDir+"RPIconf")
			if self.RPI == {}:
				self.indiLOG.log(10,self.indigoPreferencesPluginDir + "RPIconf file does not exist or has bad data, will do a new setup ")


			self.RPIVersion20 = (len(self.RPI) == 20) and len(self.RPI) > 0
			if self.RPIVersion20:
				self.indiLOG.log(20,"RPIconf adding # of rpi  from 20 ..40 ")

			for piU in copy.deepcopy(self.RPI):
				if piU not in _rpiList:
					del self.RPI[piU]



			self.sensorMessages = self.getParamsFromFile(self.indigoPreferencesPluginDir+ "sensorMessages")

			for piU in _rpiBeaconList:
				if piU not in self.RPI:
					self.RPI[piU] = copy.deepcopy(_GlobalConst_emptyRPI)
				for piProp in _GlobalConst_emptyRPI:
					if piProp not in self.RPI[piU]:
						self.RPI[piU][piProp] = copy.deepcopy(_GlobalConst_emptyRPI[piProp])
					if piProp == "enableiBeacons":
						self.RPI[piU][piProp] = "1"

				for piProp in copy.deepcopy(self.RPI[piU]):
					if piProp not in _GlobalConst_emptyRPI:
						del self.RPI[piU][piProp]
				for sensor in copy.deepcopy(self.RPI[piU]["input"]):
					if sensor not in _GlobalConst_allowedSensors and sensor not in _BLEsensorTypes:
						self.indiLOG.log(30,"removing sensor:{}, from PI:{}, not in allowed sensors ".format(sensor, piU))
						del self.RPI[piU]["input"][sensor]



			for piU in _rpiSensorList:
				if piU not in self.RPI:
					self.RPI[piU] = copy.deepcopy(_GlobalConst_emptyRPISENSOR)
				for piProp in _GlobalConst_emptyRPISENSOR:
					if piProp not in self.RPI[piU]:
						self.RPI[piU][piProp] = copy.deepcopy(_GlobalConst_emptyRPISENSOR[piProp])


				### cleanup empty devids in RPI [sensor]
				delProp=[]
				for piProp in self.RPI[piU]:
					if piProp not in _GlobalConst_emptyRPISENSOR:
						delProp.append(piProp)
					if piProp == "enableiBeacons":
						self.RPI[piU][piProp] = "0"

				for piProp in delProp:
					del self.RPI[piU][piProp]

			for piU in _rpiList:
				for IO in ["output"]:
					if IO not in self.RPI[piU]: continue
					for typeID in self.RPI[piU][IO]:
						delDev = {}
						for devId in self.RPI[piU][IO][typeID]:
							try:
								xx=indigo.devices[int(devId)]
								if self.RPI[piU][IO][typeID][devId] in [""]:
									delDev[devId] = 2
							except:	 
								delDev[devId] = 1

						for devId in delDev:
							self.indiLOG.log(20,"RPI cleanup {} del {} devId:{} deldevreason:{}, self.RPI[piU][IO][devId]:{}".format(piU, IO, devId, delDev[devId], self.RPI[piU][IO][typeID])  )
							del self.RPI[piU][IO][typeID][devId]



			for piU in self.RPI:
				if self.RPI[piU]["piOnOff"] == "0":
					self.resetUpdateQueue(piU)


			self.beacons = self.getParamsFromFile(self.indigoPreferencesPluginDir+ "beacons")

			delList={}

			for beacon in copy.deepcopy(self.beacons):
				if type(self.beacons[beacon]) !=type({}):
					self.indiLOG.log(10,"beacon: {}, type:{}".format(beacon, type(self.beacons[beacon])))
					self.indiLOG.log(10,"beacons: {}".format(self.beacons[beacon]))
					delList[beacon] = True
					continue
				for nn in _GlobalConst_emptyBeacon:
					if nn not in self.beacons[beacon]:
						self.beacons[beacon][nn]=copy.deepcopy(_GlobalConst_emptyBeacon[nn])

				if self.beacons[beacon]["indigoId"] == 0: continue

				try:
					dev = indigo.devices[self.beacons[beacon]["indigoId"]]
				except Exception as e:
					self.exceptionHandler(40, e, extraText="beacon: {} not an indigo device, removing from beacon list".format(beacon))
					delList[beacon]= True
					continue

				chList=[]
				if "closestRPI" in dev.states: # must be RPI ..
					if dev.states["closestRPI"] == "":
						chList.append({"key":"closestRPI", "value":-1})
						if self.setClostestRPItextToBlank: chList.append({"key":"closestRPIText", "value":""})
					self.execUpdateStatesList(dev,chList)

				for piU in _rpiBeaconList:
					pi = int(piU)
					piXX = piU
					try:
						if piXX+"_Distance" in dev.states:
							piXX = "Pi_{:02d}".format(pi)
							try:    d =  float(dev.states[piXX+"_Distance"])
							except: d = 99999.
							try:    s =  float(dev.states[piXX+"_Signal"])
							except: s = -999
							try:    t =  float(dev.states[piXX+"_Time"])
							except: t = 0.
							try: 	self.beacons[beacon]["receivedSignals"][pi]
							except: self.beacons[beacon]["receivedSignals"].append({})
							if len(self.beacons[beacon]["receivedSignals"][pi]) == 2:
								self.beacons[beacon]["receivedSignals"][pi] = {"rssi":s, "lastSignal":t, "distance":d}
							elif len(self.beacons[beacon]["receivedSignals"][pi]) !=3:
								self.beacons[beacon]["receivedSignals"][pi] = {"rssi":s, "lastSignal":t, "distance":d}
							elif type(self.beacons[beacon]["receivedSignals"][pi]) != type({}):
								self.beacons[beacon]["receivedSignals"][pi] = {"rssi":s, "lastSignal":t, "distance":d}

							lastUp= self.getTimetimeFromDateString(dev.states[piXX+"_Time"])
							if self.beacons[beacon]["receivedSignals"][pi]["lastSignal"] > lastUp: continue # time entry
							self.beacons[beacon]["receivedSignals"][pi]["rssi"] = float(dev.states[piXX+"_Signal"])
							self.beacons[beacon]["receivedSignals"][pi]["lastSignal"] = lastUp
					except:
						pass
			for beacon in delList:
				del self.beacons[beacon]

			self.currentVersion		 	= self.getParamsFromFile(self.indigoPreferencesPluginDir+"currentVersion", default="0")


			self.readknownBeacontags()

			self.readfastBLEReaction()


			self.startUpdateRPIqueues("start")

			self.startDelayedActionQueue()

			self.startbeaconMessageQueue()

			self.checkDevToRPIlinks()

			self.readCARS()

			self.indiLOG.log(5," ..   config read from files")
			self.fixConfig(checkOnly = ["all", "rpi", "beacon", "CARS", "sensors", "output", "force"], fromPGM="readconfig")
			self.saveConfig(calledFrom="readConfig")
		except Exception as e:
			self.exceptionHandler(40, e)
			exit(1)
		return 



####-------------------------------------------------------------------------####
	def readChangedValues(self):
		try:
			self.changedValues = {}
			version = "-2"
			## cleanup from older version
			if  os.path.isfile(self.indigoPreferencesPluginDir+"changedValues.json"):
				f = open(self.indigoPreferencesPluginDir + "changedValues.json", "r")
				self.changedValues = json.loads(f.read())
				f.close()
				# check for -Version#, if not correct:  rest storage 
				if version  not in self.changedValues: 
					self.changedValues = {version:"version .. format is: indigoId:{stateList:[[timestamp:value],[timestamp:value],...]}"}

				for devId in copy.copy(self.changedValues):
					if devId.find("-") > -1: continue
					if  int(devId) not in indigo.devices:
						del self.changedValues[devId]
		except Exception as e:
			self.exceptionHandler(40, e)
		self.saveChangedValues()

####-------------------------------------------------------------------------####
	def saveChangedValues(self):
		try:
			f = open(self.indigoPreferencesPluginDir + "changedValues.json", "w")
			f.write(json.dumps(self.changedValues))
			f.close()
		except Exception as e:
			self.exceptionHandler(40, e)


####-------------------------------------------------------------------------####
	def savefastBLEReaction(self):
		try:
			f = open(self.indigoPreferencesPluginDir + "fastBLEReaction.json", "w")
			f.write(json.dumps(self.fastBLEReaction, sort_keys=True, indent=2))
			f.close()
		except Exception:
			pass
		return 

####-------------------------------------------------------------------------####
	def readfastBLEReaction(self):
		self.fastBLEReaction = {}
		try:
			f = open(self.indigoPreferencesPluginDir + "fastBLEReaction.json", "r")
			self.fastBLEReaction = json.loads(f.read())
			f.close()
		except Exception:
			pass
		self.savefastBLEReaction()

####-------------------------------------------------------------------------####
	def readknownBeacontags(self):
		try:
			## cleanup from older version
			if os.path.isfile(self.indigoPreferencesPluginDir+"knownBeaconTags"):
				os.remove(self.indigoPreferencesPluginDir+"knownBeaconTags")

			self.knownBeaconTags = {"input":{}, "output":{},"mfgNames":{}}
			try:
				f = open(self.pathToPlugin + "knownBeaconTags.json", "r")
				self.knownBeaconTags = json.loads(f.read())
				f.close()
			except Exception as e:
				self.exceptionHandler(40, e)
				try: f.close()
				except: pass
				return False
			
			saveToFile = ""
			for tag in self.knownBeaconTags["input"]:
				for tt in ["text","Maj","Min","commands","comment","correspondingSwitchbotDevice","dBm","pos","posDelta","useOnlyThisTagToAcceptBeaconMsgDefault","sequence","sensorFunctions","comment","subType","hexCode2","hexCode"]:
					if tt not in self.knownBeaconTags["input"][tag]:
						self.knownBeaconTags["input"][tag][tt] = ""
						saveToFile = "missing: {}  {} ".format(tag, tt) 

			for xx in self.knownBeaconTags:
				for tag in self.knownBeaconTags[xx]:
					if "hexCode" in self.knownBeaconTags[xx][tag]:
						self.knownBeaconTags[xx][tag]["hexCode"] = self.knownBeaconTags[xx][tag].get("hexCode","").upper()

			if saveToFile !="" :
				self.writeJson( self.knownBeaconTags, fName=self.pathToPlugin + "knownBeaconTags.json", fmtOn=True,  toLog=20, printText=saveToFile )

			## write empty supplicant file
			if not os.path.isfile(self.indigoPreferencesPluginDir+"knownBeaconTags.supplicant"):
				self.writeJson( {}, fName=self.indigoPreferencesPluginDir + "knownBeaconTags.supplicant")

			## add to default from supplicant if any data, only new tags will be added
			knownBeaconTagsSupplicant 	= self.getParamsFromFile(self.indigoPreferencesPluginDir+"knownBeaconTags.supplicant")
			if len(knownBeaconTagsSupplicant)> 0:
				self.indiLOG.log(10,"adding  tags from  knownBeaconTags.supplicant: {} ".format(knownBeaconTagsSupplicant))

				for tag in knownBeaconTagsSupplicant:
					if tag not in self.knownBeaconTags["input"]:
						self.knownBeaconTags["input"][tag] = copy.copy(self.knownBeaconTags["input"]["other"])
						for item in self.knownBeaconTags["input"]["other"]:
							if type(self.knownBeaconTags["input"]["other"][item]) == type(1):
								try:	self.knownBeaconTags["input"][tag][item] = int(knownBeaconTagsSupplicant[tag][item])
								except:
										self.indiLOG.log(30,"bad item in knownBeaconTags.supplicant: {} {}".format(item,knownBeaconTagsSupplicant["input"][tag][item] ))
										continue
							self.knownBeaconTags["input"][tag][item] = copy.copy(knownBeaconTagsSupplicant[tag][item])
							self.indiLOG.log(10,"added  item from knownBeaconTags.supplicant: {} {}".format(item,knownBeaconTagsSupplicant[tag][item] ))

			self.writeJson( self.knownBeaconTags, fName=self.indigoPreferencesPluginDir + "knownBeaconTags.full_copy_to_use_as_example", fmtOn=True)
			self.writeJson( self.knownBeaconTags, fName=self.indigoPreferencesPluginDir + "all/knownBeaconTags", fmtOn=False )

			### knwon beacon tags section END ###

		except Exception as e:
			self.exceptionHandler(40, e)
			return False
		return True



####-------------------------------------------------------------------------####
	def checkDevToRPIlinksOneDevInput(self, dev): #
		try:

			if not dev.enabled: return
			props = dev.pluginProps
			if "isSensorDevice" not in props or not props["isSensorDevice"]: return

			#self.indiLOG.log(10,"checking :{}".format(dev.name))

			piServerNumber = -1
			if "piServerNumber" in props:
				try:
					piServerNumber = int(props["piServerNumber"])
				except:
					pass


			for piU in self.RPI:
				pix =  -1
				pi = int(piU)

				if piServerNumber < 0:
					if "rPiEnable"+piU in props and props["rPiEnable"+piU]:
						pix = pi
				else:
					if piServerNumber == pi:
						pix = piServerNumber

				if pix < 0: continue

				if pi == pix:
					if "input" not in self.RPI[piU]: self.RPI[piU]["input"] = {}
					#if pi ==11: self.indiLOG.log(10,"checking ... rpi:{} input:{}".format(piU,  self.RPI[piU]["input"]))
					if "piDevId" not in self.RPI[piU] or self.RPI[piU]["piDevId"] <= 0 or self.RPI[piU]["piOnOff"] != "1": continue
					typeId = dev.deviceTypeId
					if typeId not in self.RPI[piU]["input"]:
						self.RPI[piU]["input"][typeId] = {}
					if "{}".format(dev.id) not in self.RPI[piU]["input"][typeId]:
						self.indiLOG.log(30,"adding back input sensor {:20s}  type:{:30s} to RPI:{:1s}".format(dev.name, dev.deviceTypeId, piU))
						self.RPI[piU]["input"][typeId]["{}".format(dev.id)] = {}

		except Exception as e:
			self.exceptionHandler(40, e)
		return

####-------------------------------------------------------------------------####
	def checkDevToRPIlinksOneDevOutput(self,dev): #
		try:
			props = dev.pluginProps
			if "piServerNumber" in props:
				try: piU = "{}".format(int(props["piServerNumber"]))
				except: return
			else: return
			if "output" not in self.RPI[piU]: return
			typeId = dev.deviceTypeId
			if typeId not in self.RPI[piU]["output"]:
				self.RPI[piU]["output"][typeId] = {}
			if "{}".format(dev.id) not in self.RPI[piU]["output"][typeId]:
				self.indiLOG.log(30,"adding back out device {} to RPI:{}".format(dev.name, piU))
				self.RPI[piU]["output"][typeId]["{}".format(dev.id)] = {}

		except Exception as e:
			self.exceptionHandler(40, e)
		return

####-------------------------------------------------------------------------####
	def checkDevToRPIlinks(self): # called from read config for various input files
		try:

			for dev in indigo.devices.iter("props.isSensorDevice"):
				self.checkDevToRPIlinksOneDevInput(dev)

			for dev in indigo.devices.iter("props.isOutputDevice"):
				self.checkDevToRPIlinksOneDevOutput(dev)


		except Exception as e:
			self.exceptionHandler(40, e)
		return

####-------------------------------------------------------------------------####
	def getParamsFromFile(self, newName, oldName="", default={}): # called from read config for various input files
		try:
			out = copy.deepcopy(default)
			#self.indiLOG.log(10,"getParamsFromFile newName:{} oldName: {}; default:{}".format(newName, oldName, "{}".format(default)[0:100]))
			if os.path.isfile(newName):
				try:
					f = open(newName, "r")
					out	 = json.loads(f.read())
					f.close()
					if oldName !="" and os.path.isfile(oldName):
						subprocess.call("rm "+oldName, shell=True)
				except Exception as e:
					self.exceptionHandler(40, e)
					out =copy.deepcopy(default)
			else:
				out = copy.deepcopy(default)
			if oldName !="" and os.path.isfile(oldName):
				try:
					f = open(oldName, "r")
					out	 = json.loads(f.read())
					f.close()
					subprocess.call("rm "+oldName, shell=True)
				except Exception as e:
					self.exceptionHandler(40, e)
					out = copy.deepcopy(default)
			#self.indiLOG.log(10,"getParamsFromFile out:{} ".format("{}".format(out)[0:100]) )
		except Exception as e:
			self.exceptionHandler(40, e)
		return out

####-------------------------------------------------------------------------####
	def savebeaconPositionsFile(self):
		try:
			self.setImageParameters()
			f = open(self.indigoPreferencesPluginDir + "plotPositions/positions.json", "w")
			f.write(json.dumps(self.beaconPositionsData))
			f.close()
			if self.decideMyLog("PlotPositions"): self.indiLOG.log(5,"savebeaconPositionsFile {}".format("{}".format(self.beaconPositionsData["mac"])[0:100])  )
		except Exception as e:
			self.exceptionHandler(40, e)
		return

####-------------------------------------------------------------------------####
	def setImageParameters(self):
		try:
			self.beaconPositionsData["piDir"]			= self.indigoPreferencesPluginDir+"plotPositions"
			self.beaconPositionsData["logLevel"]		= "PlotPositions" in self.debugLevel
			self.beaconPositionsData["logFile"]		= self.PluginLogFile
			self.beaconPositionsData["distanceUnits"]	= self.distanceUnits
		except Exception as e:
			self.exceptionHandler(40, e)
		return

####-------------------------------------------------------------------------####
	def makeNewBeaconPositionPlots(self):
		try:
			changed = False

			self.beaconPositionsData["mac"]={}
			for beacon in copy.deepcopy(self.beacons):
					try:
						if self.beacons[beacon]["showBeaconOnMap"] ==0: continue
						indigoId = self.beacons[beacon]["indigoId"]
						if indigoId == 0 or indigoId == "":			 continue
						try:	dev = indigo.devices[indigoId]
						except: continue
						if self.beaconPositionsData["ShowExpiredBeacons"] == "0" and dev.states["status"] == "expired": continue
						props = dev.pluginProps

						if "showBeaconOnMap" not in props or props["showBeaconOnMap"] == "0":
							if beacon in self.beaconPositionsData["mac"]:
								del self.beaconPositionsData["mac"][beacon]
							changed = True

						elif "showBeaconOnMap"	in props and props["showBeaconOnMap"] in _GlobalConst_beaconPlotSymbols:
							if beacon not in self.beaconPositionsData["mac"]:
								changed = True
							try:	distanceToRPI = float(dev.states["Pi_{:02d}_Distance".format(int(dev.states["closestRPI"]))])
							except: distanceToRPI = 0.5
							# State "Pi_8_Signal" of "b-radius-3"
							if dev.states["status"] == "expired": useSymbol = "square45"
							else:								   useSymbol = props["showBeaconOnMap"]
							if len(props["showBeaconSymbolColor"])!= 7: showBeaconSymbolColor = "#0F0F0F"
							else:								   		 showBeaconSymbolColor = props["showBeaconSymbolColor"].upper()
							if len(props["showBeaconTextColor"])!= 7:   showBeaconTextColor = "#0FFF0F"
							else:								   		 showBeaconTextColor = props["showBeaconTextColor"].upper()
							self.beaconPositionsData["mac"][beacon]={"name":dev.name,
								"position":			[float(dev.states["PosX"]),float(dev.states["PosY"]),float(dev.states["PosZ"])],
								"nickName":			props["showBeaconNickName"],
								"symbolType":			useSymbol,
								"symbolColor":			showBeaconSymbolColor,
								"symbolAlpha":			props["showBeaconSymbolAlpha"] ,
								"distanceToRPI":		distanceToRPI ,
								"textColor":			showBeaconTextColor ,
								"bType":				"beacon" ,
								"status":				dev.states["status"]					}
					except Exception as e:
							self.exceptionHandler(40, e)

			for dev in indigo.devices.iter("props.isBLEconnectDevice"):
					try:
						props = dev.pluginProps
						beacon = props["macAddress"]
						if "showBeaconOnMap" not in props: continue
						if props["showBeaconOnMap"] == "0": continue
						if self.beaconPositionsData["ShowExpiredBeacons"] == "0" and dev.states["status"] == "expired": continue
						props = dev.pluginProps

						if "showBeaconOnMap" not in props or props["showBeaconOnMap"] =="0":
							if beacon in self.beaconPositionsData["mac"]:
								del self.beaconPositionsData["mac"][beacon]
							changed = True

						elif "showBeaconOnMap"	in props and props["showBeaconOnMap"] in _GlobalConst_beaconPlotSymbols:
							if beacon not in self.beaconPositionsData["mac"]:
								changed = True
							try:	distanceToRPI = float(dev.states["Pi_{:02d}_Distance".format(int(dev.states["closestRPI"]))])
							except: distanceToRPI = 0.5
							if dev.states["status"] == "expired": useSymbol = "square45"
							else:								   useSymbol = props["showBeaconOnMap"]
							if len(props["showBeaconSymbolColor"])!= 7: showBeaconSymbolColor = "#0F0F0F"
							else:								   		 showBeaconSymbolColor = props["showBeaconSymbolColor"].upper()
							if len(props["showBeaconTextColor"])!= 7:   showBeaconTextColor = "#0FFF0F"
							else:								   		 showBeaconTextColor = props["showBeaconTextColor"].upper()
							self.beaconPositionsData["mac"][beacon]={"name":dev.name,
								"position":			[float(dev.states["PosX"]),float(dev.states["PosY"]),float(dev.states["PosZ"])],
								"nickName":			props["showBeaconNickName"],
								"symbolType":			useSymbol,
								"symbolColor":			showBeaconSymbolColor,
								"symbolAlpha":			props["showBeaconSymbolAlpha"] ,
								"distanceToRPI":		distanceToRPI ,
								"textColor":			showBeaconTextColor ,
								"bType":				"BLEconnect" ,
								"status":				dev.states["status"]					}
					except Exception as e:
							self.exceptionHandler(40, e)



			if self.beaconPositionsData["ShowRPIs"] in	 _GlobalConst_beaconPlotSymbols:
				for piU in _rpiBeaconList:
					if self.RPI[piU]["piOnOff"]  == "0": continue
					if self.RPI[piU]["piDevId"]  == "0": continue
					if self.RPI[piU]["piDevId"]  == "":  continue
					try:
							dev = indigo.devices[self.RPI[piU]["piDevId"]]
							props = dev.pluginProps

							p = props["PosXYZ"].split(",")
							pos =[0,0,0]
							try:
								if len(pos)==3:	pos = [float(p[0]),float(p[1]),float(p[2])]
							except:
												pos = [0,0,0]

							beacon = dev.address
							if self.beaconPositionsData["ShowRPIs"] =="square": nickN =  " R-"+piU
							else:												  nickN =  "R-"+piU
							self.beaconPositionsData["mac"][beacon]={"name":"RPI-"+piU,
								"position":			 pos,
								"nickName":			 nickN,
								"symbolType":			 self.beaconPositionsData["ShowRPIs"],
								"symbolColor":			 "#00F000",
								"symbolAlpha":			 "0.5" ,
								"distanceToRPI":		 1.0 ,
								"textColor":			 "#008000" ,
								"bType":				 "RPI" ,
								"status":				 dev.states["status"]					}
					except:
						continue

			if changed or self.beaconPositionsUpdated>0:
					self.savebeaconPositionsFile()
					cmd = self.pythonPath + " '" + self.pathToPlugin + "makeBeaconPositionPlots.py' '"+self.indigoPreferencesPluginDir+"plotPositions/' & "
					#self.indiLOG.log(30," cmd:{}".format(cmd))

					if self.decideMyLog("PlotPositions"):
						self.indiLOG.log(10,"makeNewBeaconPositionPlots .. beaconPositionsUpdated: {}".format(self.beaconPositionsUpdated))
						self.indiLOG.log(10,"makeNewBeaconPositionPlots cmd: {} ".format(cmd) )
					subprocess.call(cmd, shell=True)

		except Exception as e:
			if "{}".format(e).find("timeout waiting") > -1:
				self.exceptionHandler(40, e, extraText="communication to indigo is interrupted")
				return
			if "{}".format(e).find("not found in database") ==-1:
				self.exceptionHandler(40, e)

		self.beaconPositionsUpdated		= 0
		self.beaconPositionsLastCheck	= time.time()

		return





####-------------------------------------------------------------------------####
	def calcPitoPidist(self):

		## creates:
		##	self.piToPiDistance[pi1#][pi2#][kk] matrix w k=0: x vector, k=1: y vector, k=3 dist absolute; k=2 = z is not used
		##	self.piPosition[pi#][x,y,z]
		try:
			self.piToPiDistance =[[[-1,-1,-1,-1] for ii in _rpiBeaconList] for jj in _rpiBeaconList]
			self.piPosition = [[-1,-1,-1] for ii in _rpiBeaconList]
			#self.indiLOG.log(20,"rpi:{}".format(self.RPI) )
			for piU1 in _rpiBeaconList:
				pi1 = int(piU1)
				if self.RPI[piU1]["piDevId"] == 0:   continue
				if self.RPI[piU1]["piDevId"] == "": continue
				devii = indigo.devices[self.RPI[piU1]["piDevId"]]
				propsii= devii.pluginProps
				Pii = self.getPosXYZ(devii,propsii,piU1)
				self.piPosition[pi1]=Pii
				for pi2 in range(pi1+1, _GlobalConst_numberOfiBeaconRPI):
					piU2 = "{}".format(pi2)
					try:
						if self.RPI[piU2]["piDevId"] == 0:   continue
						if self.RPI[piU2]["piDevId"] == "": continue
						devjj = indigo.devices[self.RPI[piU2]["piDevId"]]
						propsjj= devjj.pluginProps
						Pjj = self.getPosXYZ(devjj,propsjj,piU2)
						deltaDist =0
						for kk in range(2):
							delD = Pii[kk]-Pjj[kk]
							deltaDist+= (delD)**2
							self.piToPiDistance[pi1][pi2][kk] =  delD
							self.piToPiDistance[pi2][pi1][kk] = -delD
						deltaDist = math.sqrt(deltaDist)
						self.piToPiDistance[pi1][pi2][3] = deltaDist
						self.piToPiDistance[pi2][pi1][3] = deltaDist
					except Exception as e:
						self.exceptionHandler(40, e)
		except Exception as e:
			self.exceptionHandler(40, e)
		return True

####-------------------------------------------------------------------------####
	def getPosXYZ(self,dev,props,piU):
		try:
			if "PosXYZ" not in props:
				props["PosXYZ"] = "0,0,0"
				dev.replacePluginPropsOnServer(props)
				self.indiLOG.log(40,"Error= fixing props for  RPI#"+piU)
			Pjj = props["PosXYZ"].split(",")

			if len(Pjj) != 3:
				props["PosXYZ"] = "0,0,0"
				dev.replacePluginPropsOnServer(props)

			Pjj = props["PosXYZ"].split(",")
			return [float(Pjj[0]),float(Pjj[1]),float(Pjj[2])]

		except Exception as e:
			self.indiLOG.log(40,"Line {} has error={}".format(sys.exc_info()[2].tb_lineno, e)  +" fixing props, you might need to edit RPI#"+piU)
			props["PosXYZ"] ="0,0,0"
			dev.replacePluginPropsOnServer(props)
		return [0,0,0]

####-------------------------------------------------------------------------####
	def fixConfig(self, checkOnly = ["all"], fromPGM=""):
		try:
			dateString = datetime.datetime.now().strftime(_defaultDateStampFormat)

			if time.time() - self.oneWireResetNewDevices  > 0 and self.oneWireResetNewDevices > 0:
				self.oneWireResetNewDevices =0 
				self.indiLOG.log(20,"resetting one wire accept new devices due to expiration of timewindow.".format()) 
			try:
				# dont do it too often
				if time.time() - self.lastFixConfig < 25: return
				self.lastFixConfig	= time.time()
				if  self.decideMyLog("Logic"): self.indiLOG.log(5,"fixConfig called from "+fromPGM +"; with:{}".format(checkOnly) )

				nowDD = datetime.datetime.now()
				dateString = nowDD.strftime(_defaultDateStampFormat)
				anyChange= False

				if "rpi" in checkOnly or "all" in checkOnly:
					myIPrange = ["300","1","1","1"]
					myIPrangeValid = "empty"
					self.myIpNumberRange = ["-1","-1","-1","-1"]
					for piU in self.RPI:
						if self.RPI[piU]["ipNumberPi"] != "":
							if self.RPI[piU]["piOnOff"] == "1" and self.isValidIP(self.RPI[piU]["ipNumberPi"]):
								newIPList = self.RPI[piU]["ipNumberPi"].split(".")
								if myIPrangeValid == "empty":
									myIPrange =  newIPList
									myIPrangeValid = "ok"
								if myIPrange[0] != newIPList[0] or myIPrange[1] != newIPList[1]:
									myIPrangeValid = "not consistent"

						try:
							piDevId = int(self.RPI[piU]["piDevId"])
							if piDevId > 0:
								dev = indigo.devices[piDevId]
								props = dev.pluginProps
								upd = False
								if time.time() - self.oneWireResetNewDevices  > 0 and  props.get("oneWireAddNewSensors","0") == "1": # reset  if it was enabled too long ago
									props["oneWireAddNewSensors"] = "0"
									upd = True

								if "ipNumberPi" not in props or (self.isValidIP(self.RPI[piU]["ipNumberPi"]) and self.RPI[piU]["ipNumberPi"] != props["ipNumberPi"]):
									if self.decideMyLog("UpdateRPI"): self.indiLOG.log(20,"Updating pi:{}, ipNumberPi props:{} to:{} from self.RPI".format(piU, props["ipNumberPi"] , self.RPI[piU]["ipNumberPi"], ))
									upd=True
									props["ipNumberPi"] = self.RPI[piU]["ipNumberPi"]

								if "userIdPi" not in props or self.RPI[piU]["userIdPi"] != props["userIdPi"]:
									upd=True
									props["userIdPi"]	 = self.RPI[piU]["userIdPi"]

								if "passwordPi" not in props or self.RPI[piU]["passwordPi"] != props["passwordPi"]:
									upd=True
									props["passwordPi"] = self.RPI[piU]["passwordPi"]

								if "sendToIndigoSecs" not in props and "sensorRefreshSecs" in props:
									upd=True
									props["sendToIndigoSecs"] = copy.deepcopy(props["sensorRefreshSecs"])

								if "sendToIndigoSecs" not in props :
									upd=True
									props["sendToIndigoSecs"] = copy.copy(_GlobalConst_emptyRPI["sensorRefreshSecs"])

								if "sensorRefreshSecs" not in props :
									upd=True
									props["sensorRefreshSecs"] = copy.copy(_GlobalConst_emptyRPI["sensorRefreshSecs"])

								if "rssiOffset" not in props :
									upd=True
									props["rssiOffset"] = copy.copy(_GlobalConst_emptyRPI["rssiOffset"])

								if dev.enabled:
									if self.RPI[piU]["piOnOff"] != "1":
										try:	del self.checkIPSendSocketOk[self.RPI[piU]["ipNumberPi"]]
										except: pass
									self.RPI[piU]["piOnOff"] = "1"
								else:
									self.RPI[piU]["piOnOff"] = "0"

								if upd:
			
									dev.replacePluginPropsOnServer(props)
									dev= indigo.devices[piDevId]
									anyChange = True

						except Exception as e:
							if "{}".format(e).find("timeout waiting") > -1:
								self.exceptionHandler(40, e, extraText="communication to indigo is interrupted")
								return
							self.sleep(0.2)
							if self.RPI[piU]["piDevId"] !=0:
								try:
									self.exceptionHandler(40, e)
									self.indiLOG.log(40,"error normal if rpi has been deleted, removing from list: setting piDevId=0")
								except: pass
								self.delRPI(pi=piU, calledFrom="fixConfig")
							anyChange = True

						if self.RPI[piU]["piOnOff"] != "0":
							if not self.isValidIP(self.RPI[piU]["ipNumberPi"]):
								self.RPI[piU]["piOnOff"] = "0"
								anyChange = True
								continue
					if myIPrangeValid == "ok":
						self.myIpNumberRange = myIPrange
			except Exception as e:
				self.exceptionHandler(40, e)

			try:
				if "all" in checkOnly:
					delDEV = []
					for dev in indigo.devices.iter("props.isCARDevice,props.isBeaconDevice,props.isRPIDevice,props.isRPISensorDevice,props.isSensorDevice,props.isOutputDevice"):
						props = dev.pluginProps
						if "created" in dev.states:
							if len(dev.states["created"]) < 10:
								dev.updateStateOnServer("created", dateString)

						if dev.deviceTypeId == "car":
							newP = self.setupCARS(dev.id,props,mode="init")
							if newP["description"] != dev.description:
								if self.decideMyLog("CAR"): self.indiLOG.log(10,"replacing car props {}  {}  {}".format(dev.name,  newP["description"], dev.description) )
								dev.description =  newP["description"]
								dev.replaceOnServer()
								anyChange = True
							continue

						if dev.deviceTypeId != "beacon" and "description" in props:
							if props["description"] != "":
								#if self.decideMyLog("Special"): self.indiLOG.log(10," {}  props:{}, dev.desc:{},".format(dev.name,  props["description"], dev.description) )
								if dev.description != props["description"]:
									dev.description = props["description"]
									#self.indiLOG.log(10,"{} updating descriptions {}".format(dev.name, props["description"]))
									props["description"] = ""
									dev.replaceOnServer()
									updateProps = True

						if dev.deviceTypeId.find("rPI") >-1:
							props= dev.pluginProps
							try:	pi = int(props.get("RPINumber",""),"-1")
							except: continue
							try:	beacon = props["address"]
							except: beacon =""
							piU = "{}".format(pi)

							if "ipNumberPi" in props and self.isValidIP(self.RPI[piU]["ipNumberPi"]) and self.RPI[piU]["ipNumberPi"] != props["ipNumberPi"]:
								self.indiLOG.log(10,"{} fixing ipNumber in RPI device props to {}".format(dev.name, self.RPI[piU]["ipNumberPi"]))
								dev.description = "Pi-{}-{}".format(pi,self.RPI[piU]["ipNumberPi"])
								dev.replaceOnServer()
								props["ipNumberPi"] = self.RPI[piU]["ipNumberPi"]
		
								dev.replacePluginPropsOnServer(props)
								anyChange = True

							if "ipNumberPi" in props and self.isValidIP(props["ipNumberPi"]) and self.RPI[piU]["ipNumberPi"] != props["ipNumberPi"]:
								self.indiLOG.log(10,"{} fixing ipNumber in RPI device props to {}".format(dev.name, props["ipNumberPi"]))
								self.RPI[piU]["ipNumberPi"]  = props["ipNumberPi"]
								anyChange = True

							if dev.id != self.RPI[piU]["piDevId"]:
								self.indiLOG.log(10,"dev :{} fixing piDevId in RPI".format(dev.name) )
								self.RPI[piU]["piDevId"]	 = dev.id
								anyChange = True

							if len(beacon)> 6 and self.RPI[piU]["piMAC"] != beacon:
								self.indiLOG.log(10,"dev: {}  fixing piMAC in RPI".format(dev.name))
								self.RPI[piU]["piMAC"]	   = beacon
								anyChange = True

							if "userIdPi" in props and	 self.RPI[piU]["userIdPi"] != props["userIdPi"]:
								self.indiLOG.log(10,"dev: {} fixing userIdPi in RPI".format(dev.name))
								self.RPI[piU]["userIdPi"]	  = props["userIdPi"]
								anyChange = True

							if "passwordPi" in props and  self.RPI[piU]["passwordPi"] != props["passwordPi"]:
								self.indiLOG.log(10,"dev: {} fixing passwordPi in RPI".format(dev.name))
								self.RPI[piU]["passwordPi"]	= props["passwordPi"]
								anyChange = True

							if dev.deviceTypeId == "rPI":
								beacon = dev.address
								if self.isValidMAC(beacon):
									if beacon not in self.beacons:
										self.beacons[beacon] = copy.deepcopy(_GlobalConst_emptyBeacon)
										self.beacons[beacon]["typeOfBeacon"] = "rPI"
										self.beacons[beacon]["indigoId"] = dev.id
										checkOnly.append("beacon")
										checkOnly.append("force")

							if "address" in props:
								macRPI = props.get("address","-")
								if self.isValidMAC(macRPI):
									if macRPI in self.beacons:
										self.beacons[macRPI]["RPINumber"] = piU

						if dev.deviceTypeId.find("beacon") >-1:
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

					for dev in delDEV:
						self.indiLOG.log(30,"fixConfig dev: {}  has no addressfield".format(dev.name))
						# indigo.device.delete(dev)
			except Exception as e:
				self.exceptionHandler(40, e)

			try:
				if "all" in checkOnly or "beacon" in checkOnly:
					# remove junk:
					remove = []
					for beacon in copy.deepcopy(self.beacons):
						if not self.isValidMAC(beacon):  # !=17 length, remove junk
							remove.append(beacon)
							anyChange = True
						elif beacon =="00:00:00:00:00:00":
							remove.append(beacon)
							anyChange = True
						elif beacon == "":
							remove.append(beacon)
							anyChange = True
						else:

							for nn in _GlobalConst_emptyBeacon:
								if nn not in self.beacons[beacon]:
									self.beacons[beacon][nn] = copy.deepcopy(_GlobalConst_emptyBeacon[nn])
									anyChange = True
							delnn=[]
							for nn in self.beacons[beacon]:
								if nn not in _GlobalConst_emptyBeacon:
									delnn.append(nn)
							for nn in delnn:
								del self.beacons[beacon][nn]
								anyChange = True
							try:
								float(self.beacons[beacon]["created"])
								self.beacons[beacon]["created"] = dateString
							except:
								pass


							if self.beacons[beacon]["typeOfBeacon"] == "rPi":
								self.beacons[beacon]["typeOfBeacon"] = "rPI"

							if self.beacons[beacon]["indigoId"] != 0:	# sync with indigo
								try:
									dev = indigo.devices[self.beacons[beacon]["indigoId"]]
									props = dev.pluginProps
									if	 dev.deviceTypeId != "beacon" and (dev.deviceTypeId.lower()) != "rpi":
										try:
											dev = indigo.devices[self.beacons[beacon]["indigoId"]]
											self.indiLOG.log(30,"fixConfig fixing: beacon should not in beacon list: {}  {}  {}".format(beacon, dev.name, dev.deviceTypeId ) )
										except:
											self.indiLOG.log(30,"fixConfig fixing: beacon should not in beacon list: {} no name / device {}".format(beacon, dev.deviceTypeId ) )
										remove.append(beacon)
										anyChange = True
										continue



									beaconDEV = props["address"]
									if beaconDEV != beacon:
										self.beacons[beacon]["indigoId"] = 0
										self.indiLOG.log(10,"fixing: {}  beaconDEV:{}  beacon:{} beacon wrong, using current beacon-mac".format(dev.name, beaconDEV, beacon))
										anyChange = True

									self.beacons[beacon]["enabled"]				 	= dev.enabled
									try:
										self.beacons[beacon]["status"]					= dev.states["status"]
										self.beacons[beacon]["note"]					= dev.states["note"]
										self.beacons[beacon]["typeOfBeacon"]			= props["typeOfBeacon"]
										self.beacons[beacon]["beaconTxPower"]			= props["beaconTxPower"]
										self.beacons[beacon]["created"]				 	= dev.states["created"]
										self.beacons[beacon]["iBeacon"]				 	= dev.states["iBeacon"]
										self.beacons[beacon]["showBeaconOnMap"]	 		= props["showBeaconOnMap"]
									except: pass

									dev.updateStateOnServer("TxPowerSet", int(props["beaconTxPower"]))

									if "updateSignalValuesSeconds" in props: # not for RPIindigoIdindigoIdindigoIdindigoIdindigoId
										self.beacons[beacon]["updateSignalValuesSeconds"] = float(props["updateSignalValuesSeconds"])
									else:
										self.beacons[beacon]["updateSignalValuesSeconds"] = 300
								except Exception as e:
									anyChange = True
									if "{}".format(e).find("timeout waiting") > -1:
										self.exceptionHandler(40, e)
										self.indiLOG.log(40,"communication to indigo is interrupted")
										return
									elif "{}".format(e).find("not found in database") >-1:
										self.beacons[beacon]["indigoId"] =0
										continue
									else:
										self.exceptionHandler(40, e)
										self.indiLOG.log(40,"dev={}".format(dev.name))
										return


							else:
								self.beacons[beacon]["updateSignalValuesSeconds"] = copy.copy(_GlobalConst_emptyBeacon["updateSignalValuesSeconds"])
					for beacon in remove:
						self.indiLOG.log(10, "fixConfig:  deleting beacon:{}  {}".format(beacon, self.beacons[beacon]))
						del self.beacons[beacon]

			except Exception as e:
				self.exceptionHandler(40, e)
			#self.indiLOG.log(10,"fixConfig time elapsed point C  {}".format(time.time()- self.lastFixConfig) +"     anyChange: {}".format(anyChange))

			try:
				if "rpi" in checkOnly or "all" in checkOnly:
					for beacon in copy.deepcopy(self.beacons):
						try:
							pi = int(self.beacons[beacon]["RPINumber"])
						except:
							continue
						if pi != -1:
							if self.beacons[beacon]["indigoId"] != 0 :# and self.beacons[beacon]["ignore"] ==0:
								piU = "{}".format(pi)
								try:
									devId   = indigo.devices[self.beacons[beacon]["indigoId"]].id
									if self.RPI[piU]["piDevId"] != devId:
										self.RPI[piU]["piDevId"] = devId
										anyChange = True
									if self.RPI[piU]["PosX"] !=0 or self.RPI[piU]["PosY"] !=0 or self.RPI[piU]["PosZ"] !=0 :
										dev   = indigo.devices[devId]
										for xyz in ["PosX", "PosY", "PosZ"]:
											if dev.states[xyz] != self.RPI[piU][xyz]: dev.updateStateOnServer(xyz, self.RPI[piU][xyz] )

								except Exception as e:
									if "{}".format(e).find("timeout waiting") > -1:
										self.exceptionHandler(40, e)
										self.indiLOG.log(40,"communication to indigo is interrupted")
										return
									elif "{}".format(e).find("not found in database") >-1:
										self.beacons[beacon]["indigoId"] = 0
										anyChange = True
										self.indiLOG.log(10,	"fixConfig anychange: (fix) set indigoID=0,  beacon, pi, devid {}".format(beacon) +"  "+ piU +"  {}".format(devId) )
										continue
									else:
										self.exceptionHandler(40, e)
										self.indiLOG.log(40,"unknown error")
										return

			except Exception as e:
				self.exceptionHandler(40, e)


			if "rpi" in checkOnly:
				self.calcPitoPidist()

			if "all" in checkOnly:
				if self.syncSensors(): anyChange = True

			if anyChange or (time.time() - self.lastSaveConfig) > 100:
				self.lastSaveConfig = time.time()
				self.saveConfig(calledFrom="fixconfig")

			self.executeUpdateStatesDict()

		except Exception as e:
			self.exceptionHandler(40, e)
		return


####-------------------------------------------------------------------------####
	def checkSensorMessages(self, devId,item="lastMessage", default=0):
		try:
			devIds = "{}".format(devId)
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
		except Exception as e:
			self.exceptionHandler(40, e)
		return 1


####-------------------------------------------------------------------------####
	def saveSensorMessages(self,devId="",item="", value=0):
		try:
			if devId != "":
				self.checkSensorMessages(devId, item="lastMessage", default=value)
			else:
				self.writeJson(self.sensorMessages,fName=self.indigoPreferencesPluginDir + "sensorMessages")
			return
		except Exception as e:
			self.exceptionHandler(40, e)


####-------------------------------------------------------------------------####
	def writeJson(self,data, fName="", fmtOn=False, printText="", toLog=0):
		try:

			if format:
				out = json.dumps(data, sort_keys=True, indent=2)
			else:
				out = json.dumps(data)

			if fName !="":
				if toLog >0: self.indiLOG.log(toLog,"{}  json writing to fname:{} data:\n{} ".format(printText, fName, data ))
				f=open(fName, "w")
				f.write(out)
				f.close()
			return out

		except Exception as e:
			self.exceptionHandler(40, e)
		return ""

####-------------------------------------------------------------------------####
	def saveConfig(self, only="all", calledFrom=""):

		try:
			if only in ["all", "RPIconf"]:
				self.writeJson(self.RPI, fName=self.indigoPreferencesPluginDir + "RPIconf", fmtOn=self.RPIFileSort)
				#self.indiLOG.log(20," saving RPIconf: {}, RPI:{}".format(calledFrom, self.RPI))

			if only in ["all"]:
				self.saveCARS()

			if only in ["all","beacons"]:
				self.writeJson(self.beacons, fName=self.indigoPreferencesPluginDir + "beacons", fmtOn=self.beaconsFileSort)

			if only in ["all"]:
				self.makeBeacons_parameterFile()

			if only in ["all"]:
				self.writeJson( self.knownBeaconTags,   fName=self.indigoPreferencesPluginDir + "all/knownBeaconTags", fmtOn=True)

		except Exception as e:
			self.exceptionHandler(40, e)
		return

####-------------------------------------------------------------------------####
	def fixDevProps(self, dev):
		dateString = datetime.datetime.now().strftime(_defaultDateStampFormat)
		updateProps = False
		props = dev.pluginProps
		if dev.deviceTypeId == "rPI-Sensor":
			if len("{}".format(dev.address)) < 2 or "{}".format(dev.address) == "-None-" or dev.address is None:
				notes =	 dev.description.split("-")
				if notes[0].lower() == "rpi" and len(notes)>2:
					updateProps	 = True
					props["address"] = "Pi-"+notes[1]
			if len(dev.states["created"]) < 5:
				dev.updateStateOnServer("created", dateString )



		if dev.deviceTypeId not in ["rPI", "beacon"]:
			if updateProps:
				dev.replacePluginPropsOnServer(props)
			return 0

		if dev.deviceTypeId == "beacon":
			for prop in _GlobalConst_emptyBeaconProps:
				if prop not in props:
					updateProps = True
					props[prop] = _GlobalConst_emptyBeaconProps[prop]
				if prop.find("memberOf") > -1:
					if isinstance(props[prop],int):
						updateProps = True
						if props[prop] == 1:
							props[prop] = True
						else:
							props[prop] = False
		updatedev = False
		if dev.deviceTypeId.find("rPI") > -1:
			for prop in _GlobalConst_emptyrPiProps:
				if prop not in props:
					updateProps = True
					props[prop] = _GlobalConst_emptyrPiProps[prop]
				if prop.find("memberOf") > -1:
					if isinstance(props[prop],int):
						if props[prop] == 1:
							props[prop] = True
						else:
							props[prop] = False

			piU = props.get("RPINumber","")
			if piU in  self.RPI and self.RPI[piU]["piDevId"] != dev.id:
				self.RPI[piU]["piDevId"] = dev.id


		if updatedev:
			dev.replaceOnServer()

		if updateProps:
			updateProps= False
			dev.replacePluginPropsOnServer(props)
			props = dev.pluginProps

		self.checkDevToRPIlinksOneDevInput(dev)


		if "lastStatusChange" in dev.states and len(dev.states["lastStatusChange"]) < 5:
			dev.updateStateOnServer("lastStatusChange",dateString)


		# only rPi and iBeacon from here on
		if "address" not in props:
			self.indiLOG.log(30,"=== deleting dev :" + dev.name + " has no address field, please do NOT manually create beacon devices")
			self.indiLOG.log(30,"fixDevProps  props{}".format(props))
			indigo.device.delete(dev)
			return -1


		try:
			beacon = props["address"]
			if "beaconTxPower" not in props:
				props["beaconTxPower"] = _GlobalConst_emptyBeacon["beaconTxPower"]
				updateProps = True

			if "typeOfBeacon" not in props:
				if dev.deviceTypeId =="beacon":
					props["typeOfBeacon"] = _GlobalConst_emptyBeacon["typeOfBeacon"]
					updateProps = True
				if dev.deviceTypeId == "rPI" :
					props["typeOfBeacon"] = "rPI"
					updateProps = True

			if props["typeOfBeacon"] in self.knownBeaconTags["input"] and int(props["beaconTxPower"]) == 999:
				props["beaconTxPower"] = self.knownBeaconTags["input"][props["typeOfBeacon"]]["dBm"]
				updateProps = True

			if "updateSignalValuesSeconds" not in props:
				updateProps = True
				if (dev.deviceTypeId.lower()) == "rpi" :
					props["updateSignalValuesSeconds"] = 300
				else:
					props["updateSignalValuesSeconds"] = _GlobalConst_emptyBeaconProps["updateSignalValuesSeconds"]
			if "signalDelta" not in props:
				updateProps = True
				props["signalDelta"] = _GlobalConst_emptyBeaconProps["signalDelta"]
			if "minSignalOff" not in props:
				updateProps = True
				props["minSignalOff"] = _GlobalConst_emptyBeaconProps["minSignalOff"]
			if "minSignalOn" not in props:
				updateProps = True
				props["minSignalOn"] = _GlobalConst_emptyBeaconProps["minSignalOn"]
			if "fastDown" not in props:
				updateProps = True
				props["fastDown"] = _GlobalConst_emptyBeaconProps["fastDown"]

			if dev.deviceTypeId == "beacon":
				if "useOnlyPrioTagMessageTypes" not in props:
					props["useOnlyPrioTagMessageTypes"] = "0"
					updateProps = True
				if "typeOfBeacon" not in props:
					props["typeOfBeacon"] = "other"
					updateProps = True

				if props["typeOfBeacon"] not in self.knownBeaconTags["input"]:
					for tag in self.knownBeaconTags["input"]:
						if tag.upper() == props["typeOfBeacon"].upper():
							props["typeOfBeacon"] = tag
							updateProps = True
							break
				if "version" not in props:
					props["version"] = dev.states["typeOfBeacon"]
					updateProps = True

			try:
				created = dev.states["created"]
			except:
				created = ""
			if created == "":
				updateProps = True
				self.addToStatesUpdateDict(dev.id, "created", dateString)

			if "expirationTime" not in props:
				updateProps = True
				props["expirationTime"] = 90.

			if updateProps:
				
				dev.replacePluginPropsOnServer(props)
				if self.decideMyLog("Logic"): self.indiLOG.log(5,"updating props for " + dev.name + " in fix props")

			if dev.deviceTypeId == "beacon" :
				noteState = "beacon-" + props["typeOfBeacon"]
				if dev.states["note"] != noteState:
					self.addToStatesUpdateDict(dev.id, "note",noteState)
			else:
				noteState = dev.states["note"]

			if beacon not in self.beacons:
				self.indiLOG.log(10,"fixDevProps: adding beacon from devices to self.beacons: {} dev:{}".format(beacon, dev.name))
				self.beacons[beacon] = copy.deepcopy(_GlobalConst_emptyBeacon)
			self.beacons[beacon]["created"]				= dev.states["created"]
			self.beacons[beacon]["indigoId"]			= dev.id
			self.beacons[beacon]["status"]				= dev.states["status"]
			if dev.deviceTypeId == "beacon" :
				self.beacons[beacon]["typeOfBeacon"]	= "other"
			else:
				self.beacons[beacon]["typeOfBeacon"]	= "rPI"
			self.beacons[beacon]["note"]				= noteState
			self.beacons[beacon]["typeOfBeacon"]		= props["typeOfBeacon"]
			if "useOnlyPrioTagMessageTypes" in props:
				self.beacons[beacon]["useOnlyPrioTagMessageTypes"]	= props["useOnlyPrioTagMessageTypes"]
			else:
				self.beacons[beacon]["useOnlyPrioTagMessageTypes"]	= "1"
			self.beacons[beacon]["beaconTxPower"]	  = int(props["beaconTxPower"])
			self.beacons[beacon]["expirationTime"]	  = float(props["expirationTime"])
			self.beacons[beacon]["updateSignalValuesSeconds"] = float(props["updateSignalValuesSeconds"])

		except Exception as e:
			self.exceptionHandler(40, e)

		return 0


####-------------------------------------------------------------------------####
	def deviceStartComm(self, dev):
		try:
			#self.indiLOG.log(10,"deviceStartComm called for dev={}, stopcom ignore:{}".format(dev.name, self.deviceStopCommIgnore) )

			if self.pluginState == "init":
				dev.stateListOrDisplayStateIdChanged()	# update  from device.xml info if changed

			props = dev.pluginProps

			if dev.deviceTypeId == "beacon":
				typeOfBeacon = props["typeOfBeacon"]
				beepable = False 
				if typeOfBeacon in self.knownBeaconTags["input"]:
					if "commands" in self.knownBeaconTags["input"][typeOfBeacon]:
						if "beep" in self.knownBeaconTags["input"][typeOfBeacon]["commands"]:
							beepable = True
				if beepable:
					if dev.states["isBeepable"] != "YES":
						dev.updateStateOnServer("isBeepable", "YES")
				else:
					if dev.states["isBeepable"] != "not capable":
						dev.updateStateOnServer("isBeepable", "not capable")

				beacon = dev.address
				if beacon not in self.beacons:
					self.beacons[beacon] = copy.copy(_GlobalConst_emptyBeacon)
				self.beacons[beacon]["typeOfBeacon"] = typeOfBeacon
				self.beacons[beacon]["useOnlyPrioTagMessageTypes"] = props["useOnlyPrioTagMessageTypes"]
				self.beacons[beacon]["enabled"] = dev.enabled


			if dev.deviceTypeId.find("rPI") > -1:
				piU = props.get("RPINumber","")
				try: 	self.RPI[piU]["piOnOff"] = "1"
				except: pass

			if dev.pluginProps.get('isBLESensorDevice', False):
				self.isBLESensorDevice[dev.address] = dev.id

			if dev.pluginProps.get('isBLElongConnectDevice', False):
				self.isBLElongConnectDevice[dev.address] = dev.id

			if dev.pluginProps.get('isSwitchbotDevice', False):
				mac = dev.pluginProps.get('mac').upper()
				self.isSwitchbotDevice[mac] = dev.id
				if self.decideMyLog("SensorData"): self.indiLOG.log(10,"dev:{}-{}, is now in SwitchbotDeviceList".format(dev.name, dev.id))

			if dev.deviceTypeId == "sprinkler":
					self.sprinklerDeviceActive = True

			# set prop to true/ false if ... Change5minutes ... states are present 
			if  True:  # props.get("isMememberOfChangedValues","xx") == "xx":
				addToProp = ""
				for state in dev.states:
					if state.find(".ui") > 2: continue
					stateSplit = state.split("Change")
					if 	len( stateSplit ) != 2: continue

					if stateSplit[0] in addToProp: continue
						 
					if len( stateSplit[1] ) < 5: continue

					if ( 
						stateSplit[1].find("Minutes") > -1  or 
						stateSplit[1].find("Hours") > -1
						): 
						addToProp += stateSplit[0]+","

				addToProp = addToProp.strip(",")
				if props.get("isMememberOfChangedValues","xx") != addToProp:
					props["isMememberOfChangedValues"] = addToProp
					dev.replacePluginPropsOnServer(props)
					self.indiLOG.log(20,"deviceStartComm dev:{:30s}: adding isMememberOfChangedValues = {:}".format(dev.name, addToProp))


		except Exception as e:
			self.exceptionHandler(40, e)

####-------------------------------------------------------------------------####
	def deviceDeleted(self, dev):  ### indigo calls this
		props = dev.pluginProps

		if "mac" in dev.states: mac = dev.states["mac"]
		elif "mac" in props: 	mac = props["mac"]
		else:					mac = props.get("address","xx")
		#self.indiLOG.log(30,"deviceDeleted  ?? dev:{}-{},mac:{};  isSwitchbotDevice:{},  in..{}, isSwitchbotDevice :{}".format(dev.name, dev.id, mac, props.get("isSwitchbotDevice", False),  mac in self.isSwitchbotDevice, self.isSwitchbotDevice ))

		if self.isValidMAC(mac):

			if mac in self.beacons and mac.find("00:00:00:00") ==-1:
				if "indigoId" in self.beacons[mac] and	self.beacons[mac]["indigoId"] == dev.id:
					self.indiLOG.log(20,"setting beacon device in internal tables to 0:  {}-{}; enabled:{}  pluginState:{}".format(dev.name, dev.id, dev.enabled, self.pluginState))
					self.beacons[mac]["indigoId"] = 0
					self.beacons[mac]["ignore"]	  = 1
					self.writeJson(self.beacons, fName=self.indigoPreferencesPluginDir + "beacons", fmtOn=self.beaconsFileSort)

			if 	mac in self.isBLESensorDevice and props.get("isBLESensorDevice",False):
				self.indiLOG.log(20,"removing {}- {} from internal tables".format(dev.name, dev.id, mac) )
				del self.isBLESensorDevice[mac]

			if 	mac in self.isBLElongConnectDevice and props.get("isBLElongConnectDevice",False):
				self.indiLOG.log(20,"removing {}- {} from internal tables".format(dev.name, dev.id, mac) )
				del self.isBLElongConnectDevice[mac]

			if props.get("isSwitchbotDevice", False) and  mac in self.isSwitchbotDevice:
				self.indiLOG.log(20,"removing {}- {} from switchbot internal tables".format(dev.name, dev.id, mac) )
				if self.isSwitchbotDevice[mac] == dev.id:
					del self.isSwitchbotDevice[mac]

		if dev.deviceTypeId.find("rPI") > -1:
			try:
				piU = props.get("RPINumber","")
				if piU in self.RPI:
					self.delRPI(pi=piU, calledFrom="deviceDeleted")
			except:
				pass



		self.deviceStopComm(dev)
		return

####-------------------------------------------------------------------------####
	def deviceStopComm(self, dev):
		#self.indiLOG.log(10,"deviceStopComm called for dev={}, stopcom ignore:{}".format(dev.name, self.deviceStopCommIgnore) )
		try:
			if self.pluginState != "stop":

				if self.freezeAddRemove : self.sleep(0.2)


			if dev.deviceTypeId.find("rPI") > -1:
				piU = dev.pluginProps.get("RPINumber","")
				if piU in self.RPI:
					try: 	self.RPI[piU]["piOnOff"] = "0"
					except: pass

			if dev.deviceTypeId.find("beacon") > -1:
				if dev.address in self.beacons:
					self.beacons[dev.address]["enabled"] = False

		except Exception as e:
			self.exceptionHandler(40, e)


####-------------------------------------------------------------------------####
	#def didDeviceCommPropertyChange(self, origDev, newDev):
	#	 #if origDev.pluginProps['xxx'] != newDev.pluginProps['address']:
	#	 #	  return True
	#	 return False
	###########################		INIT	## END	 ########################




	###########################		DEVICE	#################################
####-------------------------------------------------------------------------####
	def getDeviceConfigUiValues(self, pluginProps, typeId="", devId=0):
		try:
			theDictList =  super(Plugin, self).getDeviceConfigUiValues(pluginProps, typeId, devId)
			dev = indigo.devices[devId]
			props = dev.pluginProps

			if typeId in ["beacon", "rPI", "rPI-Sensor"]:
				if typeId != "rPI-Sensor":
					if "address" in theDictList[0]: # 0= valuesDict,1 = errors dict
						if theDictList[0]["address"] != "00:00:00:00:00:00":
							theDictList[0]["newMACNumber"] = copy.copy(theDictList[0]["address"]).upper()
						else:
							theDictList[0]["newMACNumber"] = ""

	

				if typeId.find("rPI") > -1:
					try:
						if "MSG" in theDictList[0]:
							theDictList[0]["enablePiNumberMenu"]  = True
						else:
							theDictList[0]["newauthKeyOrPassword"]  = "assword"
							theDictList[0]["newenableRebootCheck"]  = "restartLoop"
							theDictList[0]["enablePiNumberMenu"]  = True
							theDictList[0]["hostFileCheck"]  = ""

						piU = props.get("RPINumber","")

						if piU in ["","-1"]:
							try:
								piU = dev.states["note"].split("-")[1]
							except:
								piU = ""

						try:
							piU = str(int(piU))
							theDictList[0]["RPINumber"] = piU
							
						except:
							if typeId == "rPI-Sensor":
								for piU in _rpiSensorList:
									if self.RPI[piU1]["piDevId"] == 0:
										theDictList[0]["RPINumber"] = piU
										break
							else:
								for piU in _rpiBeaconList:
									if self.RPI[piU2]["piDevId"] == 0:
										theDictList[0]["RPINumber"] = piU
										break

						theDictList[0]["newIPNumber"]    		= self.RPI[piU]["ipNumberPi"]
						theDictList[0]["newpasswordPi"]  		= self.RPI[piU]["passwordPi"]
						theDictList[0]["newuserIdPi"]    		= self.RPI[piU]["userIdPi"]
						theDictList[0]["newauthKeyOrPassword"]	= self.RPI[piU]["authKeyOrPassword"]
						theDictList[0]["hostFileCheck"]			= self.RPI[piU]["hostFileCheck"]

						if typeId =="rPI" and piU == "-1":
								theDictList[0]["newMACNumber"]	= "00:00:00:00:pi:00"
					except Exception as e:
						self.exceptionHandler(40, e)

				if typeId.find("beacon") > -1:
						beacon = dev.address
						if beacon in self.beacons:
							typeOfBeacon = self.beacons[beacon]["typeOfBeacon"]
							if "batteryLevelUUID" not in theDictList[0]: # only for new devices
								if typeOfBeacon in self.knownBeaconTags["input"]:
									if "commands" in self.knownBeaconTags["input"][typeOfBeacon] and "batteryLevel" in self.knownBeaconTags["input"][typeOfBeacon]["commands"]:
										if  self.knownBeaconTags["input"][typeOfBeacon]["commands"]["batteryLevel"].get("type","") == "BLEconnect" and "gattcmd" in self.knownBeaconTags["input"][typeOfBeacon]["commands"]["batteryLevel"]:
											theDictList[0]["SupportsBatteryLevel"]	= True
											theDictList[0]["batteryLevelUUID"]  	= "gatttool"
										if  self.knownBeaconTags["input"][typeOfBeacon]["commands"]["batteryLevel"].get("type","") == "msgGet" and "params" in self.knownBeaconTags["input"][typeOfBeacon]["commands"]["batteryLevel"]:
											theDictList[0]["SupportsBatteryLevel"]	= True
											theDictList[0]["batteryLevelUUID"]  	= "msg"

			if "isRPION08" in theDictList[0] or typeId in _BLEsensorTypes + _BLEsensorTypes:
				for piU in _rpiBeaconList:
					piUstr = "{:02d}".format(int(piU))
					if self.RPI[piU]["piOnOff"] == "1" and self.isValidIP(self.RPI[piU]["ipNumberPi"]) :
						theDictList[0]["isRPION"+piUstr] = True
					else:
						theDictList[0]["isRPION"+piUstr] = False

	
			if typeId.find("Wire18B20") > -1:		
				theDictList[0]["newSerialNumber"] = dev.states["serialNumber"]

			if True or "memberOfFamily" in theDictList[0] or typeId in ["beacon", "rPI", "rPI-Sensor", "BLEconnect"] or  typeId in _BLEsensorTypes + _BLEsensorTypes:
				for nn in range(len(_GlobalConst_groupList)):
					group = _GlobalConst_groupList[nn]
					groupNameUsedForVar = self.groupListUsedNames[group]
					if len(groupNameUsedForVar) < 1:
						theDictList[0]["groupName{}".format(nn)] = "this group is not used, set name in config"
						theDictList[0]["groupEnable{}".format(nn)] = False
						theDictList[0]["memberOf"+group] = False
					else:
						theDictList[0]["groupName{}".format(nn)] = groupNameUsedForVar
						theDictList[0]["groupEnable{}".format(nn)] = True


			#self.indiLOG.log(20,"theDictList {}".format("{}".format(theDictList[0])))


			return theDictList
		except Exception as e:
			self.exceptionHandler(40, e)

		return super(Plugin, self).getDeviceConfigUiValues(pluginProps, typeId, devId)



####-------------------------------------------------------------------------####
####-------------------------------------------------------------------------####
####----------- device edit validation section -      -----------------------####
####-------------------------------------------------------------------------####
	def validateDeviceConfigUi(self, valuesDict, typeId, devId):

		errorCode = False
		errorDict = indigo.Dict()
		valuesDict["MSG"] = "OK"
		update 	= 0
		beacon 	= "xx"
		thisPi 	= "-1"
		piU 	= "-1"
		retCode = False
		if "mac" in valuesDict:
			valuesDict["mac"] = valuesDict["mac"].upper()
		if "newMACNumber" in valuesDict:
			valuesDict["newMACNumber"] = valuesDict["newMACNumber"].upper()



		try:
			dev = indigo.devices[devId]
			props = dev.pluginProps
			if "newSerialNumber" in valuesDict:
				if valuesDict["newSerialNumber"].find("28-") ==0:
					dev.updateStateOnServer("serialNumber",valuesDict["newSerialNumber"])

			beacon = ""
			if typeId in ["beacon", "rPI"]:
				try:
					beacon = props["address"]
				except: pass
			if  len(beacon) < 8:
				beacon = "00:00:00:00:pi:00"

			if typeId.find("rPI") > -1:
				for piU in self.RPI:
					if devId == self.RPI[piU]["piDevId"]:
						thisPi = piU
						break
				try: thisPiV = "{}".format(int(valuesDict.get("RPINumber","")))
				except: thisPiV = "-1"
				if thisPi =="-1" or (thisPiV != "-1" and thisPi != thisPiV):
					if  thisPi != "-1":
						self.RPI[thisPiV] = copy.deepcopy(self.RPI[thisPi])
					self.RPI[thisPi] = copy.deepcopy(_GlobalConst_emptyRPI)
					thisPi = thisPiV
				valuesDict["RPINumber"] = thisPi

			if typeId in ["rPI-Sensor", "rPI"]:
				if thisPi == "-1":
					valuesDict["enablePiNumberMenu"] = True
					valuesDict, errorDict  = self.setErrorCode(valuesDict,errorDict,  "bad RPI Number")
					return ( False, valuesDict, errorDict )

				if not self.isValidIP(valuesDict["newIPNumber"]):
					valuesDict, errorDict  = self.setErrorCode(valuesDict,errorDict,  "bad IP Number")
					return ( False, valuesDict, errorDict )

				if len(valuesDict["newpasswordPi"]) < 2:
					valuesDict, errorDict  = self.setErrorCode(valuesDict,errorDict,  "bad password")
					return ( False, valuesDict, errorDict )

				if len(valuesDict["newuserIdPi"]) < 2:
					valuesDict, errorDict  = self.setErrorCode(valuesDict,errorDict,  "bad userId for Pi")
					return ( False, valuesDict, errorDict )
		except Exception as e:
			self.indiLOG.log(40,"setting up RPI--beacon Line {} has error={}".format(sys.exc_info()[2].tb_lineno, e))
			valuesDict, errorDict  = self.setErrorCode(valuesDict,errorDict,  "pgm error, check log")
			return ( False, valuesDict, errorDict )


		try:

			#.indiLOG.log(20,"validateDeviceConfigUi    typeId={}".format(typeId))
			# fix STATUS state, INPUT_x was split into several devices, each has "INPUT" not INPUT_0/1/2/3/4..
			if "displayS" in valuesDict and valuesDict["displayS"].find("INPUT_") >-1:
				fix = True
				for state in dev.states:
					if state.find("INPUT_") > -1:
						fix = False
						break
				if fix: valuesDict["displayS"] = "INPUT"

			if   typeId == "car":					retCode, valuesDict, errorDict = self.validateDeviceConfigUi_Cars(		 	valuesDict, errorDict, typeId, thisPi, piU, props, beacon, dev)

			elif typeId == "garageDoor":			retCode, valuesDict, errorDict = self.validateDeviceConfigUi_GarageDoor(	valuesDict, errorDict, typeId, thisPi, piU, props, beacon, dev)

			elif typeId == "sprinkler":				retCode, valuesDict, errorDict = self.validateDeviceConfigUi_Sprinkler(	 	valuesDict, errorDict, typeId, thisPi, piU, props, beacon, dev)

			elif typeId == "BLEconnect":			retCode, valuesDict, errorDict = self.validateDeviceConfigUi_BLEconnect(	valuesDict, errorDict, typeId, thisPi, piU, props, beacon, dev)

			elif typeId == "rPI-Sensor":			retCode, valuesDict, errorDict = self.validateDeviceConfigUi_rPISensor(	 	valuesDict, errorDict, typeId, thisPi, piU, props, beacon, dev)

			elif typeId == "rPI":					retCode, valuesDict, errorDict = self.validateDeviceConfigUi_rPI(			valuesDict, errorDict, typeId, thisPi, piU, props, beacon, dev)

			elif typeId == "beacon":				retCode, valuesDict, errorDict = self.validateDeviceConfigUi_beacon(		valuesDict, errorDict, typeId, thisPi, piU, props, beacon, dev)

			elif typeId.find("INPUTgpio")>-1 or typeId.find("INPUTtouch")>-1:
													retCode, valuesDict, errorDict = self.validateDeviceConfigUi_INPUTG(		valuesDict, errorDict, typeId, thisPi, piU, props, beacon, dev)

			elif typeId.find("INPUTRotatary")>-1 :	retCode, valuesDict, errorDict = self.validateDeviceConfigUi_INPUTRotatary(	valuesDict, errorDict, typeId, thisPi, piU, props, beacon, dev)

			elif typeId.find("OUTPUTgpio-") > -1 or typeId.find("OUTPUTi2cRelay") > -1:
													retCode, valuesDict, errorDict = self.validateDeviceConfigUi_OUTPUTG(		valuesDict, errorDict, typeId, thisPi, piU, props, beacon, dev)

			elif typeId in ["FBHtempshow"]:
													retCode, valuesDict, errorDict = self.validateDeviceConfigUi_FBHtempshow(		valuesDict, errorDict, typeId, thisPi, piU, props, beacon, dev)


			elif typeId in _GlobalConst_allowedSensors or typeId in _BLEsensorTypes or valuesDict.get("isBLElongConnectDevice",False):
													retCode, valuesDict, errorDict = self.validateDeviceConfigUi_sensors(		valuesDict, errorDict, typeId, thisPi, piU, props, beacon, dev)

			elif typeId in _GlobalConst_allowedOUTPUT:
													retCode, valuesDict, errorDict = self.validateDeviceConfigUi_output(		valuesDict, errorDict, typeId, thisPi, piU, props, beacon, dev)

			else:
				valuesDict["MSG"] = " bad dev type: {}".format(typeId)
				self.indiLOG.log(40," bad device type:   {}   not in registed types:\n,_GlobalConst_allowedSensors:{}\n _BLEsensorTypes:{}\n _GlobalConst_allowedOUTPUT:{}\n... ".format(typeId, _GlobalConst_allowedSensors, _BLEsensorTypes, _GlobalConst_allowedOUTPUT))

			self.saveConfig(only = "RPIconf", calledFrom="validateDeviceConfigUi")

			if retCode:
				self.setGroupStatusNextCheck = -1
				self.updateNeeded += " fixConfig "
				return True, valuesDict

			else:
				return (False, valuesDict, errorDict )


		except Exception as e:
			self.exceptionHandler(40, e)
			if "{}".format(e).find("timeout waiting") > -1:
				valuesDict, errorDict  = self.setErrorCode(valuesDict,errorDict,  "communication to indigo is interrupted")
			else:
				valuesDict, errorDict  = self.setErrorCode(valuesDict,errorDict, "please fill out all fields")

		self.updateNeeded += " fixConfig "
		valuesDict, errorDict = self.setErrorCode(valuesDict,errorDict,  "  ??   error .. ?? " )
		return ( False, valuesDict, errorDict )





####-------------------------------------------------------------------------####
	def validateDeviceConfigUi_Cars(self, valuesDict, errorDict, typeId, thisPi, piU, props, beacon, dev):
		try:
			self.delayedActions["data"].put( {"actionTime":time.time()+1.1, "devId":dev.id, "updateItems":["setupCARS"]})
			return True, errorDict, valuesDict
		except Exception as e:
			self.exceptionHandler(40, e)
			return False, errorDict, valuesDict


####-------------------------------------------------------------------------####
	def validateDeviceConfigUi_GarageDoor(self, valuesDict, errorDict, typeId, thisPi, piU, props, beacon, dev):
		try:
			valuesDict = self.setupGarageDoor(dev, valuesDict)
			return True, errorDict, valuesDict
		except Exception as e:
			self.exceptionHandler(40, e)
			return False, errorDict, valuesDict

####-------------------------------------------------------------------------####
	def validateDeviceConfigUi_Sprinkler(self, valuesDict, errorDict, typeId, thisPi, piU, props, beacon, dev):
		try:
			valuesDict["address"] = "Pi-"+valuesDict["piServerNumber"]
			return True, errorDict, valuesDict
		except Exception as e:
			self.exceptionHandler(40, e)
			return False, errorDict, valuesDict


############ RPI- BLEconnect  -------
	def validateDeviceConfigUi_BLEconnect(self, valuesDict, errorDict, typeId, thisPi, piU, props, beacon, dev):
		try:
			if self.isValidMAC(valuesDict["macAddress"]):
				self.addToStatesUpdateDict(dev.id, "TxPowerSet", int(valuesDict["beaconTxPower"]))
				valuesDict["macAddress"] = valuesDict["macAddress"].upper()
			else:
				valuesDict, errorDict  = self.setErrorCode(valuesDict,errorDict, "bad Mac Number:"+valuesDict["macAddress"])
				return ( False, valuesDict, errorDict )
			BLEMAC = valuesDict["macAddress"].upper()

			active = ""
			for piU in _rpiBeaconList:
				pi = int(piU)
				if valuesDict["rPiEnable"+piU] and self.RPI[piU]["piDevId"] >0 and self.RPI[piU]["piOnOff"] == "1":
					if typeId not in self.RPI[piU]["input"]:
						self.RPI[piU]["input"][typeId]={}
					if "{}".format(dev.id) not in self.RPI[piU]["input"][typeId]:
						self.RPI[piU]["input"][typeId]["{}".format(dev.id)] = ""
					self.RPI[piU]["input"][typeId]["{}".format(dev.id)] = BLEMAC
					active+=" "+piU+","
				else:
					if typeId in self.RPI[piU]["input"] and  "{}".format(dev.id) in self.RPI[piU]["input"][typeId]:
						del	 self.RPI[piU]["input"][typeId]["{}".format(dev.id)]
				valuesDict["description"] = "on Pi "+ active.strip(",")
				valuesDict["address"] = BLEMAC
				#self.indiLOG.log(20,"validateDeviceConfigUi_BLEconnect  description={}".format(valuesDict["description"]))

				### remove if not on this pi:
				if typeId in self.RPI[piU]["input"] and self.RPI[piU]["input"][typeId] == {}:
					del self.RPI[piU]["input"][typeId]
				if typeId not in self.RPI[piU]["input"] and typeId in self.RPI[piU]["sensorList"]:
						self.RPI[piU]["sensorList"] = self.RPI[piU]["sensorList"].replace(typeId+",","")

				if True:
					self.rPiRestartCommand[pi] +="BLEconnect,"
					self.updateNeeded += " fixConfig "
					self.setONErPiV(piU, "piUpToDate", ["updateParamsFTP"])


			#indigo.server.log("validateDeviceConfigUi_BLEconnect  groupListUsedNames:{}   \ngroupStatusList{}:".format(self.groupListUsedNames, self.groupStatusList))

			return (True, valuesDict, errorDict)
		except Exception as e:
			self.indiLOG.log(40,"setting up BLEconnect Line {} has error={}".format(sys.exc_info()[2].tb_lineno, e))
			valuesDict, errorDict  = self.setErrorCode(valuesDict,errorDict, "pgm error, check log")
			return ( False, valuesDict, errorDict )

############
	def fillMemberListState(self, dev, valuesDict, updateNow=False):
		try:
			if "groupMember" not in dev.states: return valuesDict
			if  not dev.enabled: return valuesDict

			devId = "{}".format(dev.id)
			memberList = ""
			nn = -1
			for group in _GlobalConst_groupList+_GlobalConst_groupListDef:
				nn +=1
				groupNameUsedForVar = self.groupListUsedNames[group]

				if group in _GlobalConst_groupList:
					GN = "memberOf"+group
					if GN in valuesDict:
						if len(groupNameUsedForVar) == 0:
							valuesDict[GN] = False

						if valuesDict[GN]:
							memberList += groupNameUsedForVar+"/"
							if devId not in self.groupStatusList[group]["members"]:
								self.groupStatusList[group]["members"][devId] = dev.name
						else:
							if devId in self.groupStatusList[group]["members"]:
								del self.groupStatusList[group]["members"][devId]

					else:
							if devId in self.groupStatusList[group]["members"]:
								del self.groupStatusList[group]["members"][devId]

				elif group in _GlobalConst_groupListDef:
					if ((group == "SENSOR" 		and dev.pluginProps.get("isSensorDevice",False) and dev.deviceTypeId != "BLEconnect") or 
					    (group == "BEACON" 		and dev.deviceTypeId  == "beacon") or 
					    (group == "PI" 			and dev.deviceTypeId  == "rPI") or 
					    (group == "PI" 			and dev.deviceTypeId  == "rPI-Sensor") or 
					    (group == "BLEconnect" 	and dev.deviceTypeId  == "BLEconnect")
					   ):
						#self.indiLOG.log(20,"fillMemberListState test1")
						if devId not in self.groupStatusList[group]["members"]:
							self.groupStatusList[group]["members"][devId] = dev.name
						memberList += groupNameUsedForVar+"/"
				#if dev.name =="pi_12-Kleines Display": self.indiLOG.log(20,"fillMemberListState group:{}, members:{}".format(group, self.groupStatusList[group]["members"]))

			memberList = memberList.strip("/")
			if dev.states["groupMember"] != memberList:
				if  updateNow:
					dev.updateStateOnServer("groupMember", memberList)
					valuesDict["memberList"] = memberList
				else:
					self.addToStatesUpdateDict(dev.id, "groupMember", memberList)
					self.updateNeeded += " fixConfig "
				#self.indiLOG.log(20,"fillMemberListState\ngroupListUsedNames:{}\ngroupStatusList:{}\nmemberList:{}\nstate:{}\n updateStatesDict:{}".format(self.groupListUsedNames, self.groupStatusList, memberList, dev.states["groupMember"], self.updateStatesDict))
		except Exception as e:
			self.indiLOG.log(40,"fillMemberListState Line {} has error={}".format(sys.exc_info()[2].tb_lineno, e))
			self.indiLOG.log(40,"fillMemberListState valuesDict:{}".format(valuesDict))
		valuesDict["memberList"] = memberList
		return  valuesDict



############ RPI- sensors  -------
	def validateDeviceConfigUi_rPISensor(self, valuesDict, errorDict, typeId, thisPi, piU, props, beacon, dev):
		try:
			self.RPI[piU]["piOnOff"] 				= "1"
			self.RPI[thisPi]["piDevId"] 			= dev.id
			self.RPI[thisPi]["userIdPi"] 			= valuesDict["newuserIdPi"]
			self.RPI[thisPi]["passwordPi"] 			= valuesDict["newpasswordPi"]
			self.RPI[thisPi]["authKeyOrPassword"]	= valuesDict["newauthKeyOrPassword"]
			self.RPI[thisPi]["hostFileCheck"]		= valuesDict["hostFileCheck"]
			self.RPI[thisPi]["enableRebootCheck"]	= valuesDict["newenableRebootCheck"]
			valuesDict["passwordPi"]				= valuesDict["newpasswordPi"]
			valuesDict["userIdPi"] 					= valuesDict["newuserIdPi"]
			self.RPI[thisPi]["ipNumberPi"]			= valuesDict["newIPNumber"]
			valuesDict["ipNumberPi"]				= valuesDict["newIPNumber"]
			valuesDict["address"] 					= "Pi-{}".format(thisPi)
			valuesDict["description"] 				= "Pi-{}-{}".format(thisPi, valuesDict["newIPNumber"])
			self.RPI[thisPi]["sendToIndigoSecs"]	= valuesDict["sendToIndigoSecs"]
			self.RPI[thisPi]["sensorRefreshSecs"]	= valuesDict["sensorRefreshSecs"]
			self.RPI[thisPi]["deltaChangedSensor"]	= valuesDict["deltaChangedSensor"]
			self.setONErPiV(thisPi,"piUpToDate", ["updateParamsFTP"])
			if valuesDict.get("oneWireAddNewSensors","0") == "1":
				self.oneWireResetNewDevices	= time.time() + 60*60*2 # enable for 2 hours
			self.rPiRestartCommand[int(thisPi)] 	= "master"
			self.updateNeeded 					   += " fixConfig "
			return (True, valuesDict, errorDict)
		except Exception as e:
			self.indiLOG.log(40,"setting up RPI-Sensor Line {} has error={}".format(sys.exc_info()[2].tb_lineno, e))
			valuesDict, errorDict  = self.setErrorCode(valuesDict,errorDict, "pgm error, check log")
			return ( False, valuesDict, errorDict )




############ RPI  -------
	def validateDeviceConfigUi_rPI(self, valuesDict, errorDict, typeId, thisPi, piU, props, beacon, dev):
		try:
			if "address" not in props: new = True
			else:						new = False
			newMAC = valuesDict["newMACNumber"].upper()
			valuesDict["newMACNumber"] = newMAC
			if not self.isValidMAC(newMAC):
				valuesDict["newMACNumber"] = beacon
				valuesDict, errorDict  = self.setErrorCode(valuesDict,errorDict, "bad Mac Number:"+newMAC)
				return ( False, valuesDict, errorDict )

			if valuesDict.get("oneWireAddNewSensors","0") == "1":
				self.oneWireResetNewDevices	= time.time() + 60*60*2 # enable for 2 hours

			if not new:
				if beacon != newMAC:
					self.indiLOG.log(10,"replacing RPI BLE mac {} with {}".format(beacon, newMAC) )
					piFound =-1
					for piU2 in _rpiBeaconList:
						if piU == piU2: continue
						if self.RPI[piU2]["piMAC"] == newMAC:
							self.indiLOG.log(10,"replacing RPI BLE mac failed. rpi already exists with this MAC number")
							valuesDict, errorDict  = self.setErrorCode(valuesDict,errorDict,  "bad beacon#, already exist as RPI")
							return ( False, valuesDict, errorDict )

					self.indiLOG.log(10,"replacing existing beacon")
					if newMAC not in self.beacons:
						self.beacons[newMAC] = copy.deepcopy(_GlobalConst_emptyBeacon)
						self.beacons[newMAC]["note"] = "PI-"+thisPi
						self.beacons[newMAC]["RPINumber"] = thisPi
					else:
						if beacon in self.beacons:
							self.beacons[newMAC] = copy.deepcopy(self.beacons[beacon])
						else:
							self.beacons[newMAC] = copy.deepcopy(_GlobalConst_emptyBeacon)
					self.newADDRESS[dev.id]			= newMAC
					valuesDict["address"]			= newMAC
					self.RPI[thisPi]["piMAC"]		= newMAC
					if beacon in self.beacons:
						self.beacons[beacon]["indigoId"]= 0
					beacon = newMAC
			if new:
				for piU2 in self.RPI:
					if piU2 == piU: continue
					if self.RPI[piU2]["piMAC"] == newMAC:
						self.indiLOG.log(10,"adding new RPI another RPI(#{}) has already that this MAC number:{}".format(piU2, newMAC ))
						valuesDict, errorDict  = self.setErrorCode(valuesDict,errorDict, "bad beacon#, already exist as RPI")
						return ( False, valuesDict, errorDict )
				self.indiLOG.log(10,"setting up new RPI device for pi#{} mac#  {}".format(thisPi, newMAC) )
				for ll in _GlobalConst_emptyrPiProps:
					if ll not in valuesDict: valuesDict[ll]= _GlobalConst_emptyrPiProps[ll]

			self.RPI[thisPi]["piDevId"] 			= dev.id
			valuesDict["address"]					= newMAC
			self.RPI[thisPi]["piMAC"]				= newMAC
			beacon 									= newMAC


			self.RPI[thisPi]["ipNumberPi"] 			= valuesDict["newIPNumber"]
			valuesDict["ipNumberPi"]				= valuesDict["newIPNumber"]
			self.RPI[thisPi]["userIdPi"] 			= valuesDict["newuserIdPi"]
			self.RPI[thisPi]["passwordPi"]			= valuesDict["newpasswordPi"]
			valuesDict["passwordPi"] 				= valuesDict["newpasswordPi"]
			valuesDict["userIdPi"] 					= valuesDict["newuserIdPi"]
			valuesDict["description"] 				= "Pi-{}-{}".format(thisPi, valuesDict["newIPNumber"])


			if beacon in self.beacons and beacon.find("00:00:00:00") ==-1:
				self.beacons[beacon]["expirationTime"] 			= float(valuesDict["expirationTime"])
				self.beacons[beacon]["updateSignalValuesSeconds"]	= float(valuesDict["updateSignalValuesSeconds"])
				self.beacons[beacon]["beaconTxPower"] 				= int(valuesDict["beaconTxPower"])
				self.beacons[beacon]["ignore"] 					= int(valuesDict["ignore"])
				self.addToStatesUpdateDict(dev.id, "TxPowerSet", int(valuesDict["beaconTxPower"]))

			self.RPI[thisPi]["sendToIndigoSecs"] 					= valuesDict["sendToIndigoSecs"]
			self.RPI[thisPi]["sensorRefreshSecs"] 					= valuesDict["sensorRefreshSecs"]
			self.RPI[thisPi]["deltaChangedSensor"] 				= valuesDict["deltaChangedSensor"]
			try:	 self.RPI[thisPi]["rssiOffset"]				= float(valuesDict["rssiOffset"])
			except:	 self.RPI[thisPi]["rssiOffset"]				= 0.
			self.RPI[thisPi]["BLEserial"] 							= valuesDict["BLEserial"]
			self.setONErPiV(thisPi,"piUpToDate", ["updateParamsFTP"])
			self.rPiRestartCommand[int(thisPi)] 					= "master"
			self.RPI[thisPi]["authKeyOrPassword"]					= valuesDict["newauthKeyOrPassword"]
			self.RPI[thisPi]["hostFileCheck"]						= valuesDict["hostFileCheck"]
			self.RPI[thisPi]["enableRebootCheck"]					= valuesDict["newenableRebootCheck"]

			self.RPI[piU]["piOnOff"] 								= "1"

			xyz = valuesDict["PosXYZ"]
			try:
				xyz = xyz.split(",")
				if len(xyz) == 3:
					self.RPI[thisPi]["PosX"] = float(xyz[0]) * self.distanceUnits
					self.RPI[thisPi]["PosY"] = float(xyz[1]) * self.distanceUnits
					self.RPI[thisPi]["PosZ"] = float(xyz[2]) * self.distanceUnits
			except Exception as e:
				self.exceptionHandler(40, e)
				self.indiLOG.log(40,"bad input for xyz-coordinates:{}".format(valuesDict["PosXYZ"]) )

			self.updateNeeded += " fixConfig "
			#if self.decideMyLog("UpdateRPI"): self.indiLOG.log(20,"validateDeviceConfigUi_rPI pi:{}, ipNumberPi props :{} self.RPI: {}".format(piU, props["ipNumberPi"] , self.RPI[piU]["ipNumberPi"], ))

			return (True, valuesDict, errorDict)
		except Exception as e:
			self.indiLOG.log(40,"setting up RPI Line {} has error={}".format(sys.exc_info()[2].tb_lineno, e))
			valuesDict, errorDict  = self.setErrorCode(valuesDict,errorDict, "pgm error, check log")
			return ( False, valuesDict, errorDict )




############ beacons  -------
	def validateDeviceConfigUi_beacon(self, valuesDict, errorDict, typeId, thisPi, piU, props, beacon, dev):
		try:
			#if self.decideMyLog("Special"): self.indiLOG.log(20,"into {}, typeId:{} valuesDict:{}".format(dev.name, typeId, valuesDict))
			newMAC = valuesDict["newMACNumber"].upper()
			if "address" not in props:
				new = True
				beacon = newMAC
			else:						new = False
			newMAC = valuesDict["newMACNumber"].upper()
			valuesDict["newMACNumber"] = newMAC
			if self.isValidMAC(newMAC):
				if beacon != newMAC:
					self.indiLOG.log(10,"replacing beacon mac "+beacon+" with "+newMAC)
					if beacon !="xx" and beacon in self.beacons:
						self.indiLOG.log(10,"replacing existing beacon")
						self.beacons[newMAC]	= copy.deepcopy(self.beacons[beacon])
						self.beacons[beacon]["indigoId"] = 0
						self.newADDRESS[dev.id]	= newMAC
						valuesDict["address"] = self.newADDRESS[dev.id]

					else:
						self.indiLOG.log(10,"creating a new beacon")
						self.beacons[newMAC]	= copy.deepcopy(_GlobalConst_emptyBeacon)
						self.newADDRESS[dev.id]	= newMAC
						valuesDict["address"]		= newMAC

					beacon = newMAC
				elif new:
					self.indiLOG.log(10,"creating a new beacon")
					self.beacons[newMAC]	= copy.deepcopy(_GlobalConst_emptyBeacon)
					self.newADDRESS[dev.id]	= newMAC
					valuesDict["address"]		= newMAC

					beacon = newMAC
			else:
				valuesDict["newMACNumber"] = beacon
				valuesDict, errorDict  = self.setErrorCode(valuesDict,errorDict, "bad Mac Number:"+beacon)
				return ( False, valuesDict, errorDict )
			self.beaconPositionsUpdated = 1

			if not self.isValidMAC(beacon):
				error = "bad Mac Number:"+beacon
				valuesDict, errorDict  = self.setErrorCode(valuesDict,errorDict, "bad Mac Number:"+beacon)
				return ( False, valuesDict, errorDict )
			self.beaconPositionsUpdated = 1

			if beacon in self.beacons and beacon.find("00:00:00:00") == -1:
				self.beacons[beacon]["expirationTime"] = float(valuesDict["expirationTime"])
				self.beacons[beacon]["updateSignalValuesSeconds"] = float(valuesDict["updateSignalValuesSeconds"])
				try: 	self.beacons[beacon]["beaconTxPower"] = int(valuesDict["beaconTxPower"])
				except:	self.beacons[beacon]["beaconTxPower"] = 999
				self.addToStatesUpdateDict(dev.id, "TxPowerSet", int(valuesDict["beaconTxPower"]))
				try:	self.beacons[beacon]["ignore"] = int(valuesDict["ignore"])
				except:	self.beacons[beacon]["ignore"] = 0

				self.beacons[beacon]["note"] = "beacon-" + valuesDict["typeOfBeacon"]
				self.addToStatesUpdateDict(dev.id, "note", self.beacons[beacon]["note"])

				self.beacons[beacon]["showBeaconOnMap"]		 = valuesDict["showBeaconOnMap"]
				self.beacons[beacon]["typeOfBeacon"]		 = valuesDict["typeOfBeacon"]
				valuesDict["version"]		 				 = valuesDict["typeOfBeacon"]
				self.addToStatesUpdateDict(dev.id, "typeOfBeacon", valuesDict["typeOfBeacon"])

				self.setALLrPiV("piUpToDate", ["updateParamsFTP"])

			if "batteryLevelUUID" in valuesDict and (valuesDict["batteryLevelUUID"] in ["msg", "gatttool"] or valuesDict["batteryLevelUUID"].find("TLM") ==0):
				valuesDict["SupportsBatteryLevel"]  = True
			else:
				valuesDict["SupportsBatteryLevel"]  = False

			#if self.decideMyLog("Special"): self.indiLOG.log(20,"at end: {}, typeId:{} valuesDict:{}".format(dev.name, typeId, valuesDict))

			return ( True, valuesDict, errorDict )
		except Exception as e:
			self.indiLOG.log(40,"setting up iBeacon Line {} has error={}".format(sys.exc_info()[2].tb_lineno, e))
			valuesDict, errorDict  = self.setErrorCode(valuesDict,errorDict, "pgm error, check log")
			return ( False, valuesDict, errorDict )




############ sensors  -------
	def validateDeviceConfigUi_sensors(self, valuesDict, errorDict, typeId, thisPi, piUin, props, beacon, dev):
		try:
			errorText = ""
			update = 0
			piUx = -1
			try: 	piUx = valuesDict["piServerNumber"]
			except: pass
			pix = int(piUx)
			newAddress = ""
			newDescription = ""

			if "piServerNumber" in valuesDict and "mac" in valuesDict:
				newAddress = valuesDict.get("mac","")
				newDescription = ""

			elif "piServerNumber" in valuesDict:
				newAddress = "Pi-"
				newDescription = ""

			if "rPiEnable0" in valuesDict:
				newAddress = valuesDict.get("mac","").upper()
				newDescription = "on Pi:"

			if "address" not in valuesDict: valuesDict["address"] = ""

			#self.indiLOG.log(20," into validate sens {}  valuesDict:{}".format(dev.name, valuesDict))

			atLeastOnePiSelected = False
			for piU in self.RPI:
				if ("rPiEnable"+piU in valuesDict and valuesDict["rPiEnable"+piU]) and self.RPI[piU]["piDevId"] >0:
					atLeastOnePiSelected = True
					break

			#if dev.id in [1697729290,1707940373]: self.indiLOG.log(20,"====== dev:{}, piUin:{}, typeId:{}, input:{}".format(dev.name, piUin, typeId, self.RPI[piU]["input"]))
			piU = ""
			pi = 0
			for piU2 in self.RPI:
				pi = int(piU2)

				delpiu = True
				if self.RPI[piU2]["piDevId"] >0 and self.RPI[piU2]["piOnOff"] == "1": 
					# for sensor on a singlerpi
					if "piServerNumber" in valuesDict:
						if pi == pix:
							if typeId not in self.RPI[piU2]["input"]:
								self.RPI[piU2]["input"][typeId] = {}
							if "{}".format(dev.id) not in self.RPI[piU2]["input"][typeId]:
								self.RPI[piU2]["input"][typeId]["{}".format(dev.id)] = ""
							newAddress += piU2+ ","
							delpiu = False
							piU = piU2
						
					# this is for BLE etc with possible multiple rpi
					if "rPiEnable"+piU2 in valuesDict and valuesDict["rPiEnable"+piU2]:
						if typeId not in self.RPI[piU2]["input"]:
							self.RPI[piU2]["input"][typeId]={}
						if "{}".format(dev.id) not in self.RPI[piU2]["input"][typeId]:
							self.RPI[piU2]["input"][typeId]["{}".format(dev.id)] = ""
						newDescription += piU2+ ","
						delpiu = False
						piU = piU2

				if delpiu:
					### remove if not on this pi:
					if piU2 in self.RPI and "input" in self.RPI[piU2]:
						if typeId in self.RPI[piU2]["input"] and "{}".format(dev.id) in self.RPI[piU2]["input"][typeId]:
							del self.RPI[piU2]["input"][typeId]["{}".format(dev.id)]
						if typeId in self.RPI[piU2]["input"] and self.RPI[piU2]["input"][typeId] == {}:
							del self.RPI[piU2]["input"][typeId]
						if typeId not in self.RPI[piU2]["input"] and typeId in self.RPI[piU2]["sensorList"]:
							self.RPI[piU2]["sensorList"] = self.RPI[piU2]["sensorList"].replace(typeId+",","")
						#self.indiLOG.log(20,"+++ removing from  piU:{}  ".format(piU))
					continue
				else:
						self.updateNeeded += " fixConfig "
						self.rPiRestartCommand[pi] += ", sensor"
						self.setONErPiV(piU, "piUpToDate", ["updateParamsFTP"])
			#if dev.id in [1697729290,1707940373]: self.indiLOG.log(20,"====== dev:{},   piU:{}, typeId:{}, input:{}".format(dev.name, piU, typeId, self.RPI[piU]["input"]))

			newDescription  = newDescription.strip(",")
			newAddress  = newAddress.strip(",")
			if piU != "":
				pi = int(piU)
				if valuesDict["address"] != newAddress and newAddress !="":
					valuesDict["address"] = newAddress

				mac = valuesDict["address"] 
				if self.isValidMAC(mac):
					for devBeacon in indigo.devices.iter("props.isBeaconDevice"):
						if devBeacon.pluginProps.get("address","") == mac:
							if valuesDict.get("beaconDevId","") != devBeacon.id:
								valuesDict["beaconDevId"] = devBeacon.id
								self.indiLOG.log(20,"updating corresponding for {} beacon mac{}, devId:{}".format(dev.name,  mac, devBeacon.id))
							break


				if newDescription != "" and ("description" not in valuesDict or valuesDict["description"] != newDescription):
					valuesDict["description"] = newDescription

				if  typeId in _BLEsensorTypes or ("isBLElongConnectDevice" in valuesDict and valuesDict["isBLElongConnectDevice"]):
					if not self.isValidMAC(valuesDict["mac"]):
						valuesDict["MSG"] = "enter valid MAC number"
						return ( False, valuesDict, errorDict )
					valuesDict["address"] =  valuesDict["mac"].upper()
					mac = valuesDict["address"] 
					if valuesDict.get("SupportsBatteryLevel",False):
						for dev1 in indigo.devices.iter("props.isBeaconDevice"):
							if dev1.address == mac:
								valuesDict["beaconDevId"] = dev1.id

				if  typeId == "launchpgm":
					valuesDict["description"] =  "pgm: "+valuesDict["launchCommand"]


				if	typeId	in ["mhzCO2"]:
					#self.addToStatesUpdateDict(dev.id, "CO2calibration", valuesDict["CO2normal"] )
					self.delayedActions["data"].put( {"actionTime":time.time()+1.1, "devId":dev.id, "updateItems":[{"stateName":"CO2calibration", "value":valuesDict["CO2normal"] }]})

				if	typeId	=="rainSensorRG11":
						valuesDict["description"] = "INP:"+valuesDict["gpioIn"]+"-SW5:"+valuesDict["gpioSW5"]+"-SW2:"+valuesDict["gpioSW2"]+"-SW1:"+valuesDict["gpioSW1"]+"-SW12V:"+valuesDict["gpioSWP"]


				if	typeId == "pmairquality":
					if valuesDict["resetPin"] != "-1" and valuesDict["resetPin"] != "":
						valuesDict["description"] = "reset-GPIO: " +valuesDict["resetPin"]
					else:
						valuesDict["description"] = "reset-GPIO not used"

				if	typeId == "lidar360":
						valuesDict["description"] = "MotorFrq: {}Hz; {} in 1 bin; {}; MinSignal: {}".format( int(10*float(valuesDict["motorFrequency"])), valuesDict["anglesInOneBin"], valuesDict["usbPort"],  valuesDict["minSignalStrength"])


				if	typeId == "Wire18B20" : # update serial number in states in case we jumped around with dev types.
					if len(dev.states["serialNumber"]) < 5  and dev.description.find("sN= 28")>-1:
						#self.addToStatesUpdateDict(dev.id, "serialNumber", dev.description.split("sN= ")[1] )
						self.delayedActions["data"].put( {"actionTime":time.time()+1.1  , "devId":dev.id, "updateItems":[{"stateName":"serialNumber", "value":dev.description.split("sN= ")[1] }]})

				if	typeId.find("DHT") >-1:
					if "gpioPin" in valuesDict:
						valuesDict["description"] = "GPIO-PIN: " +valuesDict["gpioPin"]+"; type: "+valuesDict["dhtType"]

				if ("i2c" in typeId.lower() or typeId in _GlobalConst_i2cSensors) or "interfaceType" in valuesDict:
					if "interfaceType" in valuesDict and valuesDict["interfaceType"] == "i2c":
						if "i2cAddress" in valuesDict:
							try:
								addrhex = "=#"+hex(int(valuesDict["i2cAddress"]))
							except:
								addrhex =""
							if "useMuxChannel" in valuesDict and valuesDict["useMuxChannel"] != "-1":
									valuesDict["description"] = "i2c: " +valuesDict["i2cAddress"]+addrhex +"; mux-channel: "+valuesDict["useMuxChannel"]
							else:
									valuesDict["description"] = "i2c: " +valuesDict["i2cAddress"]+addrhex

					elif "interfaceType" in valuesDict and valuesDict["interfaceType"] == "serial":
						valuesDict["description"] = "serial port vers."

					else:
						if "i2cAddress" in valuesDict:
							try:
								addrhex = "=#"+hex(int(valuesDict["i2cAddress"]))
							except:
								addrhex =""
							if "useMuxChannel" in valuesDict and valuesDict["useMuxChannel"] !="-1":
									valuesDict["description"] = "i2c: " +valuesDict["i2cAddress"]+addrhex +"; mux-channel: "+valuesDict["useMuxChannel"]
							else:
									valuesDict["description"] = "i2c: " +valuesDict["i2cAddress"]+addrhex

				if typeId.find("bme680") >-1:
					if   valuesDict["calibrateSetting"] == "setFixedValue": valuesDict["description"] += ", set calib to "+ valuesDict["setCalibrationFixedValue"]
					elif valuesDict["calibrateSetting"] == "readFromFile":	valuesDict["description"] += ", set calib to read from file"
					else:											        valuesDict["description"] += ", recalib if > "+valuesDict["recalibrateIfGT"]+"%"
				if typeId.find("moistureSensor") >-1:
					valuesDict["description"] +=  ";"+valuesDict["minMoisture"]+"<V<"+ valuesDict["maxMoisture"]


				if typeId in ["PCF8591", "ADS1x15"]:
					if "displayS" 	in valuesDict:  					valuesDict["displayS"] 	= "INPUT"
					if "input" 		in valuesDict:  					valuesDict["description"]	+= " C#="+valuesDict["input"]+";"
					if "gain" 		in valuesDict:  			 		valuesDict["description"] 	+= "Gain="+valuesDict["gain"]+";"
					if "sps" 		in valuesDict:  			 		valuesDict["description"] 	+= "SPS="+valuesDict["sps"]+";"
					try:
						o = float(valuesDict["offset"])
						if o != 0.:
							if o > 0: 	 								valuesDict["description"] 	+= "+"+valuesDict["offset"]+";"
							else:									 	valuesDict["description"] 	+=     valuesDict["offset"]+";"
					except: pass
					try:
						m = float(valuesDict["mult"])
						if m != 1.: 	 								valuesDict["description"] 	+= "*"+valuesDict["mult"]+";"
					except: pass
					if valuesDict["resistorSensor"]		== "ground":	valuesDict["description"] 	+= "RG="+valuesDict["feedResistor"]+";V="+valuesDict["feedVolt"]+";"
					if valuesDict["resistorSensor"]		== "V+": 		valuesDict["description"] 	+= "R+="+valuesDict["feedResistor"]+";V="+valuesDict["feedVolt"]+";"
					if valuesDict["maxMin"] 			== "1":			valuesDict["description"] 	+= ""+valuesDict["MINRange"]+";<V<"+valuesDict["MAXRange"]+";"
					if valuesDict["valueOrdivValue"]	== "1/value":	valuesDict["description"] 	+= "1/v;"
					if valuesDict["logScale"] 			== "1":  	 	valuesDict["description"] 	+= "LOG"+";"
					try:
						o = float(valuesDict["offset2"])
						if o != 0.:
							if o > 0: 	 								valuesDict["description"] 	+= "+"+valuesDict["offset2"]+";"
							else:										valuesDict["description"] 	+=     valuesDict["offset2"]+";"
					except: pass
					try:
						m = float(valuesDict["mult"])
						if m != 1.:										valuesDict["description"] 	+= "*"+valuesDict["mult"]+";"
					except: pass
					if valuesDict["format"] 			!= "":  		valuesDict["description"] 	+= "F="+valuesDict["format"]+";"
					if valuesDict["unit"] 				!= "":   		valuesDict["description"] 	+= "U="+valuesDict["unit"]+";"
					valuesDict["description"] = valuesDict["description"].strip(";")

				if "ultrasoundDistance" == typeId :
					self.rPiRestartCommand[pi] += "ultrasoundDistance,"
					if "gpioTrigger" not in props or (props["gpioTrigger"] != valuesDict["gpioTrigger"]):
						self.rPiRestartCommand[pi] += "ultrasoundDistance,"
					if "gpioEcho" not in props or(props["gpioEcho"] != valuesDict["gpioEcho"]):
						self.rPiRestartCommand[pi] += "ultrasoundDistance,"
					if "sensorRefreshSecs" not in props or (props["sensorRefreshSecs"] != valuesDict["sensorRefreshSecs"]):
						self.rPiRestartCommand[pi] += "ultrasoundDistance,"
					if "deltaDist" not in props or (props["deltaDist"] != valuesDict["deltaDist"]):
						self.rPiRestartCommand[pi] += "ultrasoundDistance,"
					valuesDict["description"] = "trigger-pin: " +valuesDict["gpioTrigger"] +"; echo-pin: " +valuesDict["gpioEcho"]+"; refresh:"+valuesDict["sensorRefreshSecs"]+"; unit:"+valuesDict["dUnits"]
					valuesDict, errorText = self.addBracketsPOS(valuesDict, "pos1")
					if errorText == "":
						valuesDict, errorText = self.addBracketsPOS(valuesDict, "pos2")
						if errorText == "":
							valuesDict, errorText = self.addBracketsPOS(valuesDict, "pos3")

				if typeId in ["vl503l0xDistance","vl503l1xDistance","ultrasoundDistance","vl6180xDistance,vcnl4010Distance"]:
						self.rPiRestartCommand[pi] += typeId

				if "INPUTpulse" == typeId :
					pinMappings = "gpio="+valuesDict["gpio"]+ "," +valuesDict["risingOrFalling"]+ " Edge, " +valuesDict["deadTime"]+ "secs deadTime"
					valuesDict["description"] = pinMappings


				if "INPUTcoincidence" == typeId :
					theText = "coincidenceWindow = {} msecs".format(valuesDict["coincidenceTimeInterval"])
					valuesDict["description"] = theText

				valuesDict["MSG"] = errorText

			if errorText == "":
				self.setONErPiV(piU, "piUpToDate", ["updateParamsFTP"])
				return (True, valuesDict, errorDict )
			else:
				self.indiLOG.log(40,"validating device error:{}     fields:{}".format(errorText, valuesDict))
				valuesDict, errorDict  = self.setErrorCode(valuesDict, errorDict,  errorText)
				return ( False, valuesDict, errorDict )

		except Exception as e:
			self.indiLOG.log(40,"setting up iBeacon Line {} has error={}".format(sys.exc_info()[2].tb_lineno, e))
			valuesDict, errorDict  = self.setErrorCode(valuesDict,errorDict, "pgm error, check log")
			return ( False, valuesDict, errorDict )



############ INPUTG  -------
	def validateDeviceConfigUi_INPUTG(self, valuesDict, errorDict, typeId, thisPi, piU, props, beacon, dev):
		try:
			if typeId.find("INPUTgpio")>-1:	typeINPUT = "INPUTgpio"
			if typeId.find("INPUTtouch")>-1:	typeINPUT = "INPUTtouch"

			active = ""
			update = 0

			piU = valuesDict["piServerNumber"]
			pi  = int(piU)
			for piU0 in self.RPI:
				if piU == piU0:											  continue
				if "input" not in self.RPI[piU0]:						  continue
				if typeId not in self.RPI[piU0]["input"]:				  continue
				if "{}".format(dev.id) not in self.RPI[piU0]["input"][typeId]:continue
				del self.RPI[piU0]["input"][typeId]["{}".format(dev.id)]
				self.setONErPiV(piU0,"piUpToDate",["updateParamsFTP"])
				self.rPiRestartCommand[int(piU0)] += typeINPUT+","
				update = 1

			if pi >= 0:
				if "piServerNumber" in props:
					if pi != int(props["piServerNumber"]):
						self.setONErPiV(piU, "piUpToDate",["updateParamsFTP"])
						self.rPiRestartCommand[int(props["piServerNumber"])] += typeINPUT+","
						update = 1
				self.setONErPiV(piU, "piUpToDate", ["updateParamsFTP"])
				self.rPiRestartCommand[pi] += typeINPUT+","

			if typeId not in self.RPI[piU]["input"]:
					self.RPI[piU]["input"][typeId] = {}
					update = 1
			if "{}".format(dev.id) not in self.RPI[piU]["input"][typeId]:
				self.RPI[piU]["input"][typeId]["{}".format(dev.id)] = []
				update = 1
			newDeviceDefs = json.loads(valuesDict["deviceDefs"])

			try:
				if len(newDeviceDefs) != len(self.RPI[piU]["input"][typeId]["{}".format(dev.id)]):
					update = 1
				for n in range(len(newDeviceDefs)):
					if update == 1: break
					for item in newDeviceDefs[n]:
						if newDeviceDefs[n][item] != self.RPI[piU]["input"][typeId]["{}".format(dev.id)][n][item]:
							update = 1
							break
			except:
				update = 1

			self.RPI[piU]["input"][typeId]["{}".format(dev.id)] = newDeviceDefs

			if typeINPUT == "INPUTgpio":
				pinMappings = "(#,gpio,inpType,Count)"
			if typeINPUT == "INPUTtouch":
				pinMappings = "(#,Chan.,Count)"


			for n in range(len(newDeviceDefs)):
				if "gpio" in newDeviceDefs[n]:
					if newDeviceDefs[n]["gpio"]=="": continue
					if typeINPUT == "INPUTgpio":
						pinMappings += "({}".format(n) + ":" + newDeviceDefs[n]["gpio"]+ "," + newDeviceDefs[n]["inpType"] + "," + newDeviceDefs[n]["count"] + ");"
					if typeINPUT == "INPUTtouch":
						pinMappings += "({}".format(n) + ":" + newDeviceDefs[n]["gpio"]+ "," + newDeviceDefs[n]["count"] + ");"
			valuesDict["description"] = pinMappings

			if update == 1:
				self.rPiRestartCommand[pi] += typeINPUT+","
				self.updateNeeded += " fixConfig "
				self.setONErPiV(piU, "piUpToDate", ["updateParamsFTP"])

			if valuesDict["count"]  == "off":
				valuesDict["SupportsOnState"]		= True
				valuesDict["SupportsSensorValue"]	= False
			else:
				valuesDict["SupportsOnState"]		= False
				valuesDict["SupportsSensorValue"]	= True


			valuesDict["piDone"]		= False
			valuesDict["stateDone"]	= False
			self.indiLOG.log(10," piUpToDate pi: {}    value:{}".format(piU, self.RPI[piU]["piUpToDate"]))
			self.indiLOG.log(10, "{}".format(valuesDict) )
			self.updateNeeded += " fixConfig "
			return (True, valuesDict, errorDict )
		except Exception as e:
			self.indiLOG.log(40,"setting up INPUTRotatary Line {} has error={}".format(sys.exc_info()[2].tb_lineno, e))
			valuesDict, errorDict  = self.setErrorCode(valuesDict,errorDict, "pgm error, check log")
			return ( False, valuesDict, errorDict )




############ INPUTRotatary  -------
	def validateDeviceConfigUi_INPUTRotatary(self, valuesDict, errorDict, typeId, thisPi, piU, props, beacon, dev):
		try:
			active = ""
			update = 0

			piU = valuesDict["piServerNumber"]
			pi  = int(piU)
			for piU0 in self.RPI:
				if piU == piU0:											  continue
				if "input" not in self.RPI[piU0]:						  continue
				if typeId not in self.RPI[piU0]["input"]:				  continue
				if "{}".format(dev.id) not in self.RPI[piU0]["input"][typeId]:continue
				del self.RPI[piU0]["input"][typeId]["{}".format(dev.id)]
				self.setONErPiV(piU0,"piUpToDate",["updateParamsFTP"])
				self.rPiRestartCommand[int(piU0)] += typeId+","
				update = 1

			if pi >= 0:
				if "piServerNumber" in props:
					if pi != int(props["piServerNumber"]):
						self.setONErPiV(piU, "piUpToDate",["updateParamsFTP"])
						self.rPiRestartCommand[int(props["piServerNumber"])] += typeId+","
						update = 1
				self.setONErPiV(piU, "piUpToDate", ["updateParamsFTP"])
				self.rPiRestartCommand[pi] += typeId+","

			pinMappings = "GPIOs:"
			for jj in range(10):
				if "INPUT_{}".format(jj) in valuesDict:
					pinMappings+= valuesDict["INPUT_{}".format(jj)]+", "
			valuesDict["description"] = pinMappings.strip(", ")
			self.updateNeeded += " fixConfig "
			return ( True, valuesDict, errorDict )

		except Exception as e:
			self.indiLOG.log(40,"setting up INPUTRotatary Line {} has error={}".format(sys.exc_info()[2].tb_lineno, e))
			valuesDict, errorDict  = self.setErrorCode(valuesDict,errorDict,  "pgm error, check log")
			return ( False, valuesDict, errorDict )


############ OUTPUTG  -------
	def validateDeviceConfigUi_FBHtempshow(self, valuesDict, errorDict, typeId, thisPi, piU, props, beacon, dev):
		try:
			update = 0
			active = ""
			piU = (valuesDict["piServerNumber"])
			for piU0 in self.RPI:
				if piU == piU0:												continue
				if "output" not in self.RPI[piU0]:							continue
				if typeId not in self.RPI[piU0]["output"]:					continue
				if "{}".format(dev.id) not in self.RPI[piU0]["output"][typeId]: continue
				del self.RPI[piU0]["output"][typeId]["{}".format(dev.id)]
				self.setONErPiV(piU0,"piUpToDate",["updateParamsFTP"])

			if int(piU) >= 0:
				if "piServerNumber" in props:
					if piU != props["piServerNumber"]:
						self.setONErPiV(piU, "piUpToDate", ["updateParamsFTP"])
						update = 1

			if "output" not in self.RPI[piU]: self.RPI[piU]["output"] = {}
			if typeId not in self.RPI[piU]["output"]: self.RPI[piU]["output"][typeId] = {}

			devidS = "{}".format(dev.id)
			self.RPI[piU]["output"][typeId][devidS] = {}
			#self.indiLOG.log(20,"onewireTempSensor  out:{}".format(self.RPI[piU]["output"] ))
			for xx in valuesDict:
				if xx.find("onewireTempSensor-") == 0:
					#self.indiLOG.log(20,"onewireTempSensor ={} :{}".format(xx, valuesDict[xx]))
					if valuesDict[xx] in ["-1","0"]: continue
					nn = xx.split("-")[1]
					if valuesDict["HMIP-WTH-"+nn] in ["-1","0"]: continue
					if valuesDict["HMIP-FALMOT-"+nn] in ["-1","0"]: continue
					self.RPI[piU]["output"][typeId][devidS][valuesDict[xx]] =  {"setpointHeat":valuesDict["HMIP-WTH-"+nn],"LEVEL":valuesDict["HMIP-FALMOT-"+nn]}
			#self.indiLOG.log(20,"onewireTempSensor end:{} ".format(self.RPI[piU]["output"][typeId][devidS] ))

			if update == 1:
				self.rPiRestartCommand[int(piU)] += typeId+","
				self.updateNeeded += " fixConfig "
				self.setONErPiV(piU, "piUpToDate", ["updateParamsFTP"])

			valuesDict["piDone"] = False
			valuesDict["stateDone"] = False
			return (True, valuesDict, errorDict)

		except Exception as e:
			self.indiLOG.log(40,"setting up OUTPUT-FBHLine {} has error={}".format(sys.exc_info()[2].tb_lineno, e))
			try:
				valuesDict, errorDict  = self.setErrorCode(valuesDict, errorDict, "pgm error, check log")
			except Exception as e:
				self.indiLOG.log(40,"setting up OUTPUT-FBH Line {} has error={}".format(sys.exc_info()[2].tb_lineno, e))
			return ( False, valuesDict, errorDict )




############ OUTPUTG  -------
	def validateDeviceConfigUi_OUTPUTG(self, valuesDict, errorDict, typeId, thisPi, piU, props, beacon, dev):
		try:
			#self.indiLOG.log(10,"into validate relay")
			update = 0
			active = ""
			piU = (valuesDict["piServerNumber"])
			for piU0 in self.RPI:
				if piU == piU0:												continue
				if "output" not in self.RPI[piU0]:							continue
				if typeId not in self.RPI[piU0]["output"]:					continue
				if "{}".format(dev.id) not in self.RPI[piU0]["output"][typeId]: continue
				del self.RPI[piU0]["output"][typeId]["{}".format(dev.id)]
				self.setONErPiV(piU0,"piUpToDate",["updateParamsFTP"])

			if int(piU) >= 0:
				if "piServerNumber" in props:
					if piU != props["piServerNumber"]:
						self.setONErPiV(piU, "piUpToDate", ["updateParamsFTP"])
						update = 1



			if typeId not in self.RPI[piU]["output"]:
				self.RPI[piU]["output"][typeId] = {}
				update = 1

			if "{}".format(dev.id) not in self.RPI[piU]["output"][typeId]:
				self.RPI[piU]["output"][typeId]["{}".format(dev.id)] = []
				update = 1

			newDefs = json.loads(valuesDict["deviceDefs"])
			#self.indiLOG.log(20,"validateDeviceConfigUi_OUTPUTG.. deviceDefs:{}".format(valuesDict["deviceDefs"]))

			try:
				if len(newDefs) != len(self.RPI[piU]["output"][typeId]["{}".format(dev.id)]):
					update = 1
				for n in range(len(newDefs)):
					if update == 1: break
					for item in newDefs[n]:
						if newDefs[n] != self.RPI[piU]["output"][typeId]["{}".format(dev.id)][n][item]:
							update = 1
							break
			except:
				update = 1

			self.RPI[piU]["output"][typeId]["{}".format(dev.id)] = newDefs

			if typeId.find("OUTPUTi2cRelay") ==-1:  pinMappings = "(#,gpio,type,init)"
			else:									pinMappings = "(ch#,type,init)"
			for n in range(len(newDefs)):
				if "gpio" in newDefs[n]:
					pinMappings += "({}".format(n) + ":" + newDefs[n]["gpio"]+"," + newDefs[n]["outType"] +"," +  newDefs[n]["initialValue"]  +");"
				else:
					pinMappings += "({}".format(n) + ":-);"

				if "inverse" in dev.states:
					#self.addToStatesUpdateDict(dev.id, "inverse", new[n]["outType"]=="1" )
					self.delayedActions["data"].put( {"actionTime":time.time()+1.1  , "devId":dev.id, "updateItems":[{"stateName":"inverse", "value":newDefs[n]["outType"] == "1" }]})
				elif "inverse_{:2d}".format(n) in dev.states:
					#self.addToStatesUpdateDict(dev.id, "inverse_{:2d}".format(n), new[n]["outType"]=="1")
					self.delayedActions["data"].put( {"actionTime":time.time()+1.1  , "devId":dev.id, "updateItems":[{"stateName":"inverse_{:2d}".format(n), "value":newDefs[n]["outType"]}]})

				if "initial" in dev.states:
					self.delayedActions["data"].put( {"actionTime":time.time()+1.1  , "devId":dev.id, "updateItems":[{"stateName":"initial", "value":newDefs[n]["initialValue"]}]})
					#self.addToStatesUpdateDict(dev.id, "initial", new[n]["initialValue"] )
				elif "initial{:2d}".format(n) in dev.states:
					#self.addToStatesUpdateDict(dev.id, "initial{:2d}".format(n), new[n]["initialValue"] )
					self.delayedActions["data"].put( {"actionTime":time.time()+1.1  , "devId":dev.id, "updateItems":[{"stateName":"initial{:2d}".format(n), "value":newDefs[n]["initialValue"]}]})

			valuesDict["description"] = pinMappings
			self.indiLOG.log(10,"setting OUTPUT-G  description:{}".format(pinMappings))

			if update == 1:
				self.rPiRestartCommand[int(piU)] += typeId+","
				self.updateNeeded += " fixConfig "
				self.setONErPiV(piU, "piUpToDate", ["updateParamsFTP"])

			valuesDict["piDone"] = False
			valuesDict["stateDone"] = False
			return (True, valuesDict, errorDict)

		except Exception as e:
			self.indiLOG.log(40,"setting up OUTPUT-G Line {} has error={}".format(sys.exc_info()[2].tb_lineno, e))
			try:
				valuesDict, errorDict  = self.setErrorCode(valuesDict, errorDict, "pgm error, check log")
			except Exception as e:
				self.indiLOG.log(40,"setting up OUTPUT-G Line {} has error={}".format(sys.exc_info()[2].tb_lineno, e))
			return ( False, valuesDict, errorDict )




	def validateDeviceConfigUi_output(self, valuesDict, errorDict, typeId, thisPi, piU, props, beacon, dev):
		try:
			error = ""
			if typeId== "neopixel-dimmer":
				neopixelDevice = indigo.devices[int(valuesDict["neopixelDevice"])]
				propsX = neopixelDevice.pluginProps
				piU = propsX["piServerNumber"]
				pi = int(piU)
				self.rPiRestartCommand[pi] += "neopixel3,"
				self.setONErPiV(piU, "piUpToDate", ["updateParamsFTP"])
				valuesDict["address"] = neopixelDevice.name
				try:
					xxx= propsX["devType"].split("x")
					ymax = int(xxx[0])
					xmax = int(xxx[1])
				except:
					valuesDict, errorDict  = self.setErrorCode(valuesDict,errorDict,  "devtype not defined for neopixel" )
					return ( False, valuesDict, errorDict )

				pixels = "; pix="
				if valuesDict["pixelMenulist"] !="": pixels +=valuesDict["pixelMenulist"]
				else:
					for ii in range(20):
						if "pixelMenu{}".format(ii) in valuesDict and valuesDict["pixelMenu{}".format(ii)] !="":
							pixel =valuesDict["pixelMenu{}".format(ii)]
							if "," not in pixel:
								# try just one dim.
								valuesDict["pixelMenu{}".format(ii)]= "0,"+pixel

							pixel =valuesDict["pixelMenu{}".format(ii)]
							xxx = pixel.split(",")
							x = xxx[1]
							y = xxx[0]
							if	int(x) >= xmax : x = "{}".format(max(0,xmax-1))
							if	int(y) >= ymax : y = "{}".format(max(0,ymax-1))
							pixels +=y+","+x+" "
							valuesDict["pixelMenu{}".format(ii)] = y+","+x
					pixels =pixels.strip(" ")
				valuesDict["description"]	= "rampSp="+ valuesDict["speedOfChange"]+"[sec]"+ pixels

			elif typeId=="neopixel2":
				try:
					piU = valuesDict["piServerNumber"]
					pi = int(piU)
					self.rPiRestartCommand[pi] += "neopixel2,"
					valuesDict["address"]		 = "Pi-"+valuesDict["piServerNumber"]
					valuesDict["devType"]		 = valuesDict["devTypeROWs"] +"x"+valuesDict["devTypeLEDs"]
					valuesDict["description"]	 = "type="+valuesDict["devType"]
					self.setONErPiV(piU, "piUpToDate", ["updateParamsFTP"])
				except:
					pass
			elif typeId=="neopixel3":
				try:
					piU = valuesDict["piServerNumber"]
					pi = int(piU)
					self.rPiRestartCommand[pi] += "neopixel3,"
					valuesDict["address"]		 = "Pi-"+valuesDict["piServerNumber"]
					valuesDict["devType"]		 = valuesDict["devTypeROWs"] +"x"+valuesDict["devTypeLEDs"]
					valuesDict["description"]	 = "type="+valuesDict["devType"]
					self.setONErPiV(piU, "piUpToDate", ["updateParamsFTP"])
				except:
					pass
			elif typeId=="sundial":
				try:
					piU = valuesDict["piServerNumber"]
					pi = int(piU)
					self.rPiRestartCommand[pi] += "sundial,"
					valuesDict["address"]		 = "Pi-"+valuesDict["piServerNumber"]
					valuesDict["description"]	 = "TZ="+valuesDict["timeZone"]+"; motorType"+valuesDict["motorType"]
					self.setONErPiV(piU, "piUpToDate", ["updateParamsFTP"])
				except:
					pass
			elif typeId=="setStepperMotor":
				try:
					piU = valuesDict["piServerNumber"]
					pi = int(piU)
					self.rPiRestartCommand[pi] += "setStepperMotor,"
					valuesDict["address"]		 = "Pi-"+valuesDict["piServerNumber"]
					valuesDict["description"]	 = "motorTypes: "+valuesDict["motorType"]
					self.setONErPiV(piU, "piUpToDate", ["updateParamsFTP"])
				except:
					pass
			else:
				piU = valuesDict["piServerNumber"]
				pi = int(piU)
				valuesDict["address"] = "PI-" + piU

				if pi >= 0:
					if "piServerNumber" in props:
						if pi != int(props["piServerNumber"]):
							self.updateNeeded += " fixConfig "
							oldPiU = "{}".format(int(props["piServerNumber"]))
							if oldPiU in self.RPI:
								if "output" in self.RPI[oldPiU]:
									if typeId in self.RPI[oldPiU]["output"]:
										if "{}".format(dev.id) in self.RPI[oldPiU]["output"][typeId]:
											del self.RPI[oldPiU]["output"][typeId]["{}".format(dev.id)]
										if self.RPI[oldPiU]["output"][typeId] == {}:
											del self.RPI[oldPiU]["output"][typeId]
		
					cAddress = ""
					devType = ""

					if "devType" in valuesDict:
						devType = valuesDict["devType"]

					if "output" not in			self.RPI[piU]:
						self.RPI[piU]["output"] = {}

					if typeId not in			self.RPI[piU]["output"]:
						self.RPI[piU]["output"][typeId] = {}

					if "{}".format(dev.id) not in	self.RPI[piU]["output"][typeId]:
						self.RPI[piU]["output"][typeId]["{}".format(dev.id)] = {}

					if type(self.RPI[piU]["output"][typeId]["{}".format(dev.id)]) != type({}):
							self.RPI[piU]["output"][typeId]["{}".format(dev.id)] = {}

						

					if "i2cAddress" in valuesDict:
						cAddress = valuesDict["i2cAddress"]
						self.RPI[piU]["output"][typeId]["{}".format(dev.id)] = [{"i2cAddress":cAddress},{"devType":devType}]

					elif "spiAddress" in valuesDict:
						cAddress = "{}".format(int(valuesDict["spiAddress"]))
						self.RPI[piU]["output"][typeId]["{}".format(dev.id)] = [{"spi":cAddress},{"devType":devType}]

					if "mac" in valuesDict:
						if not self.isValidMAC(valuesDict["mac"]):
							valuesDict["MSG"] = "enter valid MAC number"
							return ( False, valuesDict, errorDict )
						self.RPI[piU]["output"][typeId]["{}".format(dev.id)]["mac"] = valuesDict["mac"]

					sendupdateSwitchBot = False
					if typeId in ["OUTPUTswitchbotCurtain","OUTPUTswitchbotCurtain3", "OUTPUTswitchbotRelay"]:
						if "modeOfDevice" in valuesDict:
							if "modeOfDevice" not in self.RPI[piU]["output"][typeId]["{}".format(dev.id)]:
								self.RPI[piU]["output"][typeId]["{}".format(dev.id)]["modeOfDevice"] = "donotset"
								sendupdateSwitchBot = True

							if  valuesDict["modeOfDevice"] != self.RPI[piU]["output"][typeId]["{}".format(dev.id)]["modeOfDevice"]:
								sendupdateSwitchBot = True
							self.RPI[piU]["output"][typeId]["{}".format(dev.id)]["modeOfDevice"] = valuesDict["modeOfDevice"]

							try:	self.RPI[piU]["output"][typeId]["{}".format(dev.id)]["suppressQuickSecond"] = float(valuesDict["suppressQuickSecond"])
							except:	self.RPI[piU]["output"][typeId]["{}".format(dev.id)]["suppressQuickSecond"] = -10

						if "holdSeconds" in valuesDict:
							if "holdSeconds" not in self.RPI[piU]["output"][typeId]["{}".format(dev.id)]:
								self.RPI[piU]["output"][typeId]["{}".format(dev.id)]["holdSeconds"] = "-1"
								sendupdateSwitchBot = True
							if valuesDict["holdSeconds"] != self.RPI[piU]["output"][typeId]["{}".format(dev.id)]["holdSeconds"]:
								sendupdateSwitchBot = True
							self.RPI[piU]["output"][typeId]["{}".format(dev.id)]["holdSeconds"] = valuesDict["holdSeconds"]

							try:	self.RPI[piU]["output"][typeId]["{}".format(dev.id)]["suppressQuickSecond"] = float(valuesDict["suppressQuickSecond"])
							except:	self.RPI[piU]["output"][typeId]["{}".format(dev.id)]["suppressQuickSecond"] = -10


					if sendupdateSwitchBot:
						#								give regular update time to send config, only then send command
						self.delayedActions["data"].put({"actionTime":time.time()+20 , "devId":dev.id, "updateItems":["OUTPUTswitchbotRelay-setParameters"]})
						self.updateNeeded += " fixConfig "
						#self.indiLOG.log(20,"add to delayed action queue:{}".format(addToAction))
						

					self.updateNeeded += " fixConfig "
					self.rPiRestartCommand[pi] += "receiveGPIOcommands,"
					self.setONErPiV(piU, "piUpToDate", ["updateParamsFTP"])


					if typeId == "display":
						valuesDict = self.fixDisplayProps(valuesDict,typeId,devType)

						self.rPiRestartCommand[pi] += "display,"
						self.setONErPiV(piU, "piUpToDate", ["updateAllFilesFTP"]) # this will send images and fonts too
						valuesDict,error = self.addBracketsPOS(valuesDict,"pos1")
						if error == "":
							valuesDict,error = self.addBracketsPOS(valuesDict, "pos2")
							if error == "":
								valuesDict,error = self.addBracketsPOS(valuesDict, "pos3")

						if devType == "screen":
							valuesDict["description"] = "res: {}".format(valuesDict["displayResolution"])

					if typeId=="OUTPUTxWindows":
						self.rPiRestartCommand[pi] += "xWindows,"
						self.setONErPiV(piU, "piUpToDate", ["updateParamsFTP"]) # this will send images and fonts too
						valuesDict["description"]	 = "GUI: "+valuesDict["xWindows"]


					if typeId == "setTEA5767":
						self.setONErPiV(piU, "piUpToDate", ["updateParamsFTP"]) # this will send config only
						self.addToStatesUpdateDict(dev.id, "status"   ,"f= "+valuesDict["defFreq"] + "; mute= " +valuesDict["mute"])
						self.addToStatesUpdateDict(dev.id, "frequency",valuesDict["defFreq"] )
						self.addToStatesUpdateDict(dev.id, "mute"     ,valuesDict["mute"])
						self.devUpdateList["{}".format(dev.id)] = True
			valuesDict["MSG"] = error
			if error == "":
				self.updateNeeded += " fixConfig "
				return (True, valuesDict, errorDict)
			else:
				valuesDict, errorDict  = self.setErrorCode(valuesDict,errorDict,  error )
				return ( False, valuesDict, errorDict )

		except Exception as e:
			self.indiLOG.log(40,"setting up OUTPUT Line {} has error={}".format(sys.exc_info()[2].tb_lineno, e))
			valuesDict, errorDict  = self.setErrorCode(valuesDict,errorDict, "pgm error, check log")
		return ( False, valuesDict, errorDict )


####-------------------------------------------------------------------------####
	def setErrorCode(self,valuesDict, errorDict, error):
		try:
			valuesDict["MSG"] = error
			errorDict["MSG"]  = error
			self.indiLOG.log(40,"validateDeviceConfigUi "+error)
		except Exception as e:
			self.exceptionHandler(40, e)
		return   valuesDict, errorDict


####-------------------------------------------------------------------------####
	def execdevUpdateList(self):
		if self.devUpdateList == {}: return
		for devId in self.devUpdateList:
			try:
				dev = indigo.devices[int(devId)]
				if dev.states["mute"] == "1":
					dev.updateStateImageOnServer(indigo.kStateImageSel.SensorOff)
				else:
					dev.updateStateImageOnServer(indigo.kStateImageSel.SensorOn)
			except Exception as e:
					self.exceptionHandler(40, e)
		self.devUpdateList ={}

####-------------------------------------------------------------------------####
	def fixDisplayProps(self, valuesDict,typeId,devType):
		try:
			if typeId=="display":
				if devType =="LCD1602":
					if "displayResolution" in valuesDict: del valuesDict["displayResolution"]
					if "textForssd1351-1"	in valuesDict: del valuesDict["textForssd1351-1"]
					if "textForssd1351-2"	in valuesDict: del valuesDict["textForssd1351-2"]
					if "PIN_RST"			in valuesDict: del valuesDict["PIN_RST"]
					if "PIN_CS"				in valuesDict: del valuesDict["PIN_CS"]
					if "PIN_DC"				in valuesDict: del valuesDict["PIN_DC"]
					if "PIN_CE"				in valuesDict: del valuesDict["PIN_CE"]
					if "intensity"			in valuesDict: del valuesDict["intensity"]
					if "flipDisplay"		in valuesDict: del valuesDict["flipDisplay"]
					if "scrollSpeed"		in valuesDict: del valuesDict["scrollSpeed"]
					if "extraPage0Line0"	in valuesDict: del valuesDict["extraPage0Line0"]
					if "extraPage0Line1"	in valuesDict: del valuesDict["extraPage0Line1"]
					if "extraPage0Color"	in valuesDict: del valuesDict["extraPage0Color"]
					if "extraPage1Line0"	in valuesDict: del valuesDict["extraPage1Line0"]
					if "extraPage1Line1"	in valuesDict: del valuesDict["extraPage1Line1"]
					if "extraPage1Color"	in valuesDict: del valuesDict["extraPage1Color"]
					valuesDict["scrollxy"]		= "0"
					valuesDict["showDateTime"] = "0"
		except Exception as e:
			if "{}".format(e).find("timeout waiting") > -1:
				self.exceptionHandler(40, e)
		return valuesDict


####-------------------------------------------------------------------------####
	def addBracketsPOS(self, valuesDict, pos):
		error = ""
		if pos in valuesDict:
			if valuesDict[pos].find("[") !=0:
				valuesDict[pos] ="["+valuesDict[pos]
			if valuesDict[pos].find("]") != len(valuesDict[pos])-1:
				valuesDict[pos] =valuesDict[pos]+"]"
			if len(valuesDict[pos]) > 2:
				if valuesDict[pos].find(",") ==-1:
					valuesDict[pos]="error"
					error ="comma missing"
		return valuesDict, error


####-------------------------------------------------------------------------####
####-------------------------------------------------------------------------####
####----------- device edit validation section END    -----------------------####
####-------------------------------------------------------------------------####


		###########################		MENU  #################################
	def buttonprintHelpMenu(self, valuesDict=None, typeId="", devId=0):
		self.printHelp()
		return valuesDict
####-------------------------------------------------------------------------####
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
		devId= int(valuesDict["printDeviceDict"])
		dev=indigo.devices[devId]
		self.myLog( theText = dev.name+"/{}".format(devId)+" -------------------------------",mType="printing dev info for" )
		props=dev.pluginProps
		states=dev.states
		self.myLog( theText = "\n{}".format(props),mType="props:")
		self.myLog( theText = "\n{}".format(states),mType="states:")
		try:  self.myLog( theText = dev.description,mType="description:")
		except: pass
		try:  self.myLog( theText = dev.address,mType="address:")
		except: pass
		try:  self.myLog( theText = dev.deviceTypeId,mType="deviceTypeId:")
		except: pass
		try:  self.myLog( theText = "{}".format(dev.enabled),mType="enabled:")
		except: pass
		try:  self.myLog( theText = dev.model,mType="model:")
		except: pass
		if "piServerNumber" in props:
			if props["piServerNumber"]!="":
				pi= int(props["piServerNumber"])
				piU = "{}".format(pi)
				self.myLog( theText = "pi#:{}\n{}".format(piU, self.writeJson(self.RPI[piU], fmtOn=True )),mType="RPI info:")
		else:
			for piU in _rpiBeaconList:
				if props.get("rPiEnable"+piU,"True"):
					self.myLog( theText = "pi#:{}\n{}".format(piU, self.writeJson(self.RPI[piU], fmtOn=True )),mType="RPI info:")


		return valuesDict


####-------------------------------------------------------------------------####
	def buttonConfirmchangeLogfile(self, valuesDict=None, typeId="", devId=0):
		self.myLog( theText = "  starting to modify "+self.indigoPath + 'IndigoWebServer/indigopy/indigoconn.py')
		if not os.path.isfile(self.indigoPath + 'IndigoWebServer/indigopy/indigoconn.py'): return valuesDict
		f = open(self.indigoPath + 'IndigoWebServer/indigopy/indigoconn.py', "r")
		g = open(self.indigoPath + 'IndigoWebServer/indigopy/indigoconn.py-1', "w")
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
			self.indiLOG.log(10,"....modified version already inplace, do nothing")
			return valuesDict

		if os.path.isfile(self.indigoPath + 'IndigoWebServer/indigopy/indigoconn.py.original'):
			os.remove(self.indigoPath + 'IndigoWebServer/indigopy/indigoconn.py.original')
		os.rename(self.indigoPath + 'IndigoWebServer/indigopy/indigoconn.py',
				  self.indigoPath + 'IndigoWebServer/indigopy/indigoconn.py.original')
		os.rename(self.indigoPath + 'IndigoWebServer/indigopy/indigoconn.py-1',
				  self.indigoPath + 'IndigoWebServer/indigopy/indigoconn.py')
		self.indiLOG.log(10,"/Library/Application Support/Perceptive Automation/Indigo x/IndigoWebServer/indigopy/indigoconn.py has been replace with modified version(logging suppressed)")
		self.indiLOG.log(10,"  the original has been renamed to indigoconn.py.original, you will need to restart indigo server to activate new version")
		self.indiLOG.log(10,"  to go back to the original version replace/rename the new version with the saved .../IndigoWebServer/indigopy/indigoconn.py.original file")

		return valuesDict

####-------------------------------------------------------------------------####
	def buttonConfirmReversechangeLogfile(self, valuesDict=None, typeId="", devId=0):

		if os.path.isfile(self.indigoPath + 'IndigoWebServer/indigopy/indigoconn.py.original'):
			os.remove(self.indigoPath + 'IndigoWebServer/indigopy/indigoconn.py')
			os.rename(self.indigoPath + 'IndigoWebServer/indigopy/indigoconn.py.original',
				  self.indigoPath + 'IndigoWebServer/indigopy/indigoconn.py')
			self.indiLOG.log(10,"/Library/Application Support/Perceptive Automation/Indigo x/IndigoWebServer/indigopy/indigoconn.py.original has been restored")
			self.indiLOG.log(10," you will need to restart indigo server to activate new version")
		else:
			self.indiLOG.log(10,"no file ... indigopy.py.original found to restore")

		return valuesDict


####-------------------------------------------------------------------------####
	def setALLrPiV(self, item, value, resetQueue=False):
		if resetQueue:
			for piU in self.RPI:
				self.resetUpdateQueue(piU)
			self.sleep(1.5) # give rest >2 cycles in execute commands to reset everything 
			
		for piU in self.RPI:
			self.setONErPiV(piU, item, value, resetQueue=False)
		return

####-------------------------------------------------------------------------####
	def setONErPiV(self,piU, item, value, resetQueue=False):
		try:
			if piU in self.RPI:
				if resetQueue:
					self.resetUpdateQueue(piU)
					self.sleep(1.5) # give rest >2 cycles in execute commands to reset everything 
			
				if self.RPI[piU]["ipNumberPi"] != "":
					if self.RPI[piU]["piOnOff"] == "1":
						if value == "" or value == [] or value == [""] or isinstance(self.RPI[piU][item], ( int, long ) ) or isinstance(self.RPI[piU][item],str):
							self.RPI[piU][item] = []
						else:
							for v in value:
								if v not in self.RPI[piU][item]:
									self.RPI[piU][item].append(v)
			return
		except Exception as e:
			self.exceptionHandler(40, e)


####-------------------------------------------------------------------------####
	def removeAllPiV(self, item, value):
		for piU in self.RPI:
			self.removeONErPiV(piU, item, value)
		return

####-------------------------------------------------------------------------####
	def removeONErPiV(self, pix, item, value):
		piU = "{}".format(pix)
		if piU in self.RPI:
			for v in value:
				vv = v.split(".exp")[0]
				if vv in self.RPI[piU][item]:
					self.RPI[piU][item].remove(vv)
		return




####-------------------------------------------------------------------------####
	def filterRPIForSensorForRpiAction(self, filter="", valuesDict=None, typeId="", devId=""):
		xList = []
		try: 	sensDev = indigo.devices[int(valuesDict["sensor"])]
		except: return xList

		props = sensDev.pluginProps
		if  "rPiEnable0" in props:
			for nn in range(_GlobalConst_numberOfiBeaconRPI):
				if props.get("rPiEnable{}".format(nn), False):
					xList.append((str(nn), "rpi-{}".format(nn) ))
		elif "piServerNumber" in props:
				if props.get("piServerNumber","") !="":
					xList.append( (props.get("piServerNumber"), "rpi-{}".format(props.get("piServerNumber")) ))
		return xList


####-------------------------------------------------------------------------####
	def filterSensorForRpiAction(self, filter="", valuesDict=None, typeId="", devId=""):
		xList = []
		for dev in indigo.devices.iter("props.isSensorDevice"):
			if dev.pluginProps.get("SupportsOnState",False):
				xList.append((dev.id, dev.name))
		xList = sorted(xList, key=lambda tup: tup[1])
		xList.append(("0", "none = OFF"))
		return xList

####-------------------------------------------------------------------------####
	def filterBeaconTags_and_all(self, filter="", valuesDict=None, typeId="", devId=""):
		xList = []
		for dd in self.knownBeaconTags["input"]:
			if "text" not in self.knownBeaconTags["input"][dd] or "pos" not in self.knownBeaconTags["input"][dd]:
				self.indiLOG.log(30, "filterBeaconTypes:  tag:{}, not complete:{}\n contact author".format(dd,self.knownBeaconTags["input"][dd] ))
				continue
			if self.knownBeaconTags["input"][dd]["pos"] >= 0:
				xList.append((dd,self.knownBeaconTags["input"][dd]["text"]))
		xList = sorted(xList, key=lambda tup: tup[1])
		xList.append(("all", "USE ALL KNOWN"))
		xList.append(("off", "none = OFF"))
		return xList

####-------------------------------------------------------------------------####
	def filterBeaconKnownMfgNames(self, filter="", valuesDict=None, typeId="", devId=""):
		xList = []
		for dd in self.knownBeaconTags["mfgNames"]:
			xList.append((dd,"{} - {} ".format(dd, self.knownBeaconTags["mfgNames"][dd])))
		xList = sorted(xList, key=lambda tup: tup[1])
		xList.append(["off","off"])
		return xList

####-------------------------------------------------------------------------####
	def filterBeaconTypes(self, filter="", valuesDict=None, typeId="", devId=""):
		xList = []

		for dd in self.knownBeaconTags["input"]:
			if "text" not in self.knownBeaconTags["input"][dd] or "dBm" not in self.knownBeaconTags["input"][dd]:
				self.indiLOG.log(30, "filterBeaconTypes:  tag:{}, not complete:{}\n contact author".format(dd,self.knownBeaconTags["input"][dd] ))
				continue
			xList.append((dd,self.knownBeaconTags["input"][dd]["text"]+" txPower: "+self.knownBeaconTags["input"][dd]["dBm"]+"dBm"))
		xList = sorted(xList, key=lambda tup: tup[1])
		return xList


####-------------------------------------------------------------------------####
	def filterBeaconsThatCanBeepOrSetTime(self, filter="beep", valuesDict=None, typeId="", devId=""):
		xList = []
		deb = False 
		if filter == "setTime":
			for dev in indigo.devices.iter("props.isBeaconDevice"):
				if not dev.enabled: continue
				if dev.pluginProps.get("typeOfBeacon","") == "XiaomiMiBLETempHumClock":
					xList.append( ("{}".format(dev.id), dev.name ) )
		else:
			#for dev in indigo.devices.iter("props.isBeaconDevice"):
			for dev in indigo.devices:
				if not dev.enabled: continue
				props = dev.pluginProps
				if deb: self.indiLOG.log(10, "filterBeacon-beep :  testing{}, -{}".format(dev.name, props.get("beaconBeepUUID","")))
				if props.get("beaconBeepUUID","") != "gatttool": continue
				if deb: self.indiLOG.log(10, "filterBeacon-beep :  pass2, -{} ".format( props.get("typeOfBeacon","") ))
				if props.get("typeOfBeacon","") == "": continue
				if deb: self.indiLOG.log(10, "filterBeacon-beep :  pass3, {}".format(props["typeOfBeacon"]))
				if props["typeOfBeacon"] not in self.knownBeaconTags["input"]: continue
				if deb: self.indiLOG.log(10, "filterBeacon-beep :  pass4,{} ".format(self.knownBeaconTags[props["typeOfBeacon"]]))
				if "commands" not in self.knownBeaconTags["input"][props["typeOfBeacon"]]: continue 
				if deb: self.indiLOG.log(10, "filterBeacon-beep :  pass5, {}".format(self.knownBeaconTags["input"][props["typeOfBeacon"]]["commands"]))
				if "beep" not in self.knownBeaconTags["input"][props["typeOfBeacon"]]["commands"]: continue 
				if deb: self.indiLOG.log(10, "filterBeacon-beep :  pass6, {}".format(self.knownBeaconTags["input"][props["typeOfBeacon"]]["commands"]["beep"]["type"] ))
				if self.knownBeaconTags["input"][props["typeOfBeacon"]]["commands"]["beep"]["type"] == "BLEconnect":
					xList.append( ("{}".format(dev.id), dev.name ) )

		return xList




####-------------------------------------------------------------------------####
	def filterOnewireSensors(self, filter="", valuesDict=None, typeId="", devId=""):
		xList = []
		for dev in indigo.devices.iter("props.isSensorDevice"):
				if dev.deviceTypeId != "Wire18B20": continue
				xList.append( ("{}".format(dev.id), dev.name ) )
		xList.append( ("-1","off") )
		return xList



####-------------------------------------------------------------------------####
	def filterHomematicWTH(self, filter="", valuesDict=None, typeId="", devId=""):
		xList = []
		for dev in indigo.devices:
				if dev.deviceTypeId != "HMIP-WTH": continue
				xList.append( ("{}".format(dev.id), dev.name ) )
		xList.append( ("-1","off") )
		return xList



####-------------------------------------------------------------------------####
	def filterHomematicFALMOT(self, filter="", valuesDict=None, typeId="", devId=""):
		xList = []
		deb = False
		for dev in indigo.devices.iter("props.numberOfPhysicalChannels"):
			if deb: self.indiLOG.log(20, "filterHomematicFALMOT :  dev:{}".format(dev.name ))
			if dev.deviceTypeId != "HMIP-FALMOT": continue
			valves = json.loads(dev.states.get("childInfo","{}"))
			if deb: self.indiLOG.log(20, "filterHomematicFALMOT :  valves:{}".format(valves ))
			for nn in valves:
				if deb: self.indiLOG.log(20, "filterHomematicFALMOT : nn:{} valve:{}".format(nn, valves[nn] ))
				try: int(nn)
				except: continue
				devId, valveNumber, childDevType = valves[nn]
				if childDevType != "HMIP-LEVEL" : continue
				if devId not in indigo.devices: continue
				xList.append(("{}".format(devId), "{}-{}".format(dev.name, valveNumber)))
		xList.append( ("-1","off") )
		return xList



####-------------------------------------------------------------------------####
	def filterOnOffSensors(self, filter="", valuesDict=None, typeId="", devId=""):
		xList = []
		for dev in indigo.devices.iter("props.isSensorDevice,props.SupportsOnState"):
				props = dev.pluginProps
				if not props.get("SupportsOnState", False): continue
				xList.append( ("{}".format(dev.id), dev.name ) )
		return xList


####-------------------------------------------------------------------------####
	def filterStateOfSensor(self, filter="", valuesDict=None, typeId="", devId=""):
		xList = []
		try:	dev = indigo.devices[int(valuesDict.get(filter,"-"))]
		except: return xList

		for theState in dev.states:
			xList.append( (theState, theState) )
		return xList


####-------------------------------------------------------------------------####
	def filterAllpiSimple(self, filter="", valuesDict=None, typeId="", devId=""):
		xList = []
		for piU in _rpiList:
			name = ""
			try:
				devId= int(self.RPI[piU]["piDevId"])
				if devId > 0:
					name = "-"+indigo.devices[devId].name
			except: pass
			xList.append(( piU,"#{}-{}{}".format(piU, self.RPI[piU]["ipNumberPi"], name) ))
		return xList

####-------------------------------------------------------------------------####
	def filterNeopixelDevice(self, filter="", valuesDict=None, typeId="", devId=""):
		xList=[("0", "not active")]
		return xList

####-------------------------------------------------------------------------####
	def filterNeopixelType(self, filter="", valuesDict=None, typeId="", devId=""):
		xList=[("0", 	"not active")
			 ,("sLine",		"1D-LINE  enter left and right end")
			 ,("line",		"2D-LINE  enter left and right end")
			 ,("sPoint",	"ONE      POINT ")
			 ,("points",	"MULTIPLE POINTS ")
			 ,("rectangle", "RECTANGLE ")
			 ,("knightrider", "KNIGHTRIDER moving line left right")
			 ,("colorknightrider", "KNIGHTRIDER moving line left right, each LED differnt RGB value")
			 ,("thermometer", "THERMOMETER enter start, end pixels and color delta")
			 ,("NOP",		"No operation, use to wait before next action")
			 ,("image",		"IMAGE  not implemnted yet")
			 ,("exec",		"execute, not implemened yet")]
		return xList


####-------------------------------------------------------------------------####
	def filterNeopixeldevices(self, filter="", valuesDict=None, typeId="", devId=""):
		xList = []
		for dev in indigo.devices:
			if dev.deviceTypeId in ["neopixel"]:
				xList.append((dev.id,"{}".format(dev.name)))
		return xList


####-------------------------------------------------------------------------####
	def filterSensorswPause(self, filter="", valuesDict=None, typeId="", devId=""):
		xList = []
		for dev in indigo.devices.iter("props.isPauseSensor"):
			piServerNumber = dev.pluginProps.get("piServerNumber","-1")
			if piServerNumber != "-1":
				devType = dev.deviceTypeId
				xList.append((dev.id,"{} on:{}, sensor:{}".format(dev.name, piServerNumber, devType)))
		#indigo.server.log("{}".format(xList))
		return xList



####-------------------------------------------------------------------------####
	def filterNeopixeldevices(self, filter="", valuesDict=None, typeId="", devId=""):
		xList = []
		for dev in indigo.devices:
			if dev.deviceTypeId in ["neopixel"]:
				xList.append((dev.id,"{}".format(dev.name)))
		return xList


####-------------------------------------------------------------------------####
	def filterDisplayType(self, filter="", valuesDict=None, typeId="", devId=""):
		xList=[("0", "not active")
			 ,("text"			, "text: eg %%d:sensorX:input%%[mV]  .. you can also use %%eval:%3.1f%(float(%%d:123:state:%%))%%[mV]")
			 ,("textWformat"	, "text: with format string eg %%v:123%%%%FORMAT:%3.1f[mV]; only for numbers")
			 ,("date"			, "date:  %Y-%m-%d full screen")
			 ,("clock"			, "clock: %H:%M full screen")
			 ,("dateString"	, "date time: string format eg %HH:%M:%S")
			 ,("line"			, "line [Xstart,Ystart,Xend,Yend], width")
			 ,("point"			, "point-s: ([[x,y],[x,y],..] ")
			 ,("dot"			, "dot: [x,y] size radius or x,y size")
			 ,("rectangle"		, "rectangle [Xtl,Ytl,Xrb,Yrb]")
			 ,("triangle"		, "triangle [X1,Y1,X2,Y2,Y3,Y3]")
			 ,("ellipse"		, "ellipse, [Xtl,Ytl,Xrb,Yrb]")
			 ,("image"			, "image: file name ")
			 ,("vBar"			, "vertical bar: x0, y0, L")
			 ,("hBar"			, "horizontal bar: x0, y0, L")
			 ,("vBarwBox"		, "vertical bar with box: x0, y0,L,value")
			 ,("hBarwBox"		, "horizontal bar with box: x0, y0,L,value")
			 ,("labelsForPreviousObject"	    , "ticks,labels for prev box:[LR,lineW,[[10,10],[20,""]...[]]]")
			 ,("hist"			, "histogram ")
			 ,("NOP"			, "No operation, use to wait before next action")
			 ,("exec"			, "execute")]
		return xList


####-------------------------------------------------------------------------####
	def filterNeoPixelRings(self, filter="", valuesDict=None, typeId="", devId=""):
		xList=[("1", "1")
			 ,("6", "6")
			 ,("8", "8")
			 ,("10", "10")
			 ,("12", "12")
			 ,("14", "14")
			 ,("16", "16")
			 ,("20", "20")
			 ,("24", "24")
			 ,("28", "28")
			 ,("30", "30")
			 ,("32", "32")
			 ,("36", "36")
			 ,("40", "40")
			 ,("48", "48")
			 ,("60", "60")
			 ,("72", "72")]
		return xList


####-------------------------------------------------------------------------####
	def filter10To100(self, filter="", valuesDict=None, typeId="", devId=""):
		xList=[("10", "10")
			 ,("20", "20")
			 ,("30", "30")
			 ,("40", "40")
			 ,("50", "50")
			 ,("60", "60")
			 ,("70", "70")
			 ,("80", "80")
			 ,("90", "90")
			 ,("100", "100")]
		return xList

####-------------------------------------------------------------------------####
	def filterDisplayPages(self, filter="", valuesDict=None, typeId="", devId=""):
		xList=[("1", "1")
			 ,("2", "2")
			 ,("3", "3")
			 ,("4", "4")
			 ,("5", "5")
			 ,("6", "6")
			 ,("7", "7")
			 ,("8", "8")]
		return xList

####-------------------------------------------------------------------------####
	def filterDisplayScrollDelay(self, filter="", valuesDict=None, typeId="", devId=""):
		xList=[("0.015", "0.015 secs")
			 ,("0.025", "0.025 secs")
			 ,("0.05" , "0.05 secs")
			 ,("0.1"  , "0.1 secs")
			 ,("0.2"  , "0.2 secs")
			 ,("0.3"  , "0.3 secs")
			 ,("0.4"  , "0.4 secs")
			 ,("0.6"  , "0.6 secs")]
		return xList

####-------------------------------------------------------------------------####
	def filterDisplayNumberOfRepeats(self, filter="", valuesDict=None, typeId="", devId=""):
		xList=[("1" , "1")
			 ,("2" , "2 ")
			 ,("3" , "3")
			 ,("4" , "4")
			 ,("5" , "5")
			 ,("6" , "8")
			 ,("7" , "7")
			 ,("8" , "8")
			 ,("9" , "9")
			 ,("10" ,	"10")
			 ,("12" , "12")
			 ,("15" , "15")
			 ,("20" , "20")
			 ,("25" , "25")
			 ,("30" , "30")
			 ,("50" , "50")
			 ,("60" , "60")
			 ,("100" , "100")
			 ,("500" , "500")
			 ,("9999999" , "infinit")]
		return xList

####-------------------------------------------------------------------------####
	def filterscrollDelayBetweenPages(self, filter="", valuesDict=None, typeId="", devId=""):
		xList=[("0", "no delay")
			 ,("0.5", "0.5 sec delay")
			 ,("1"	 , "1 sec delay")
			 ,("2"	 , "2 sec delay")
			 ,("3"	 , "3 sec delay")
			 ,("4"	 , "4 sec delay")
			 ,("5"	 , "5 sec delay")
			 ,("8"	 , "8 sec delay")
			 ,("10" , "10 sec delay")
			 ,("15" , "15 sec delay")
			 ,("20" , "20 sec delay")]
		return xList

####-------------------------------------------------------------------------####
	def filterDisplayScroll(self, filter="", valuesDict=None, typeId="", devId=""):
		xList=[("0"			   , "no scrolling")
			 ,("left"		   , "scroll to left ")
			 ,("right"		   , "scroll to right")
			 ,("up"		   , "scroll up ")
			 ,("down"		   , "scroll down")]
		return xList

####-------------------------------------------------------------------------####
	def filterDisplayFonts(self, filter="", valuesDict=None, typeId="", devId=""):

		fonts=	   [["4x6.pil", "4x6 for LED display"],
					["5x7.pil", "5x7 for LED display"],
					["5x8.pil", "5x8 for LED display"],
					["6x10.pil", "6x10 for LED display"],
					["6x12.pil", "6x12 for LED display"],
					["6x13.pil", "6x13 for LED display"],
					["6x13B.pil", "6x138 for LED display"],
					["6x13O.pil", "6x130 for LED display"],
					["6x9.pil", "6x9 for LED display"],
					["7x13.pil", "7x13 for LED display"],
					["7x13B.pil", "7x138 for LED display"],
					["7x13O.pil", "7x130 for LED display"],
					["7x14.pil", "7x14 for LED display"],
					["7x14B.pil", "7x148 for LED display"],
					["8x13.pil", "8x13 for LED display"],
					["8x13B.pil", "8x138 for LED display"],
					["8x13O.pil", "8x130 for LED display"],
					["9x15.pil", "9x15 for LED display"],
					["9x15B.pil", "9x158 for LED display"],
					["9x18.pil", "9x18 for LED display"],
					["9x18B.pil", "9x188 for LED display"],
					["10x20.pil", "10x20 for LED display"],
					["clR6x12.pil", "clR6x12 for LED display"],
					["RedAlert.ttf", "RedAlert small displays"],
					["Courier New.ttf", "Courier New, Mono spaced"],
					["Andale Mono.ttf", "Andale, Mono spaced"],
					["Volter__28Goldfish_29.ttf", "Volter__28Goldfish_29 for small displays"],
					["Arial.ttf", "arial for regular monitors and small displays"]]
		return fonts


####-------------------------------------------------------------------------####
	def filterPiI(self, valuesDict=None, filter="self", typeId="", devId="x",action =""):

		xList = []
		for piU in _rpiBeaconList:
			if self.RPI[piU]["piOnOff"] != "0":
				xList.append([piU, piU])
		for piU in _rpiSensorList:
			if self.RPI[piU]["piOnOff"] != "0":
				xList.append([piU, piU ])

		return xList
####-------------------------------------------------------------------------####
	def confirmPiNumberBUTTONI(self, valuesDict=None, typeId="", devId="x"):
		try:
			piN 	= valuesDict["piServerNumber"]
			nChan 	= self.getTypeIDLength(typeId)
			valuesDict["piDone"]	 = True
			valuesDict["stateDone"] = True

			self.stateNumberForInputGPIOX = ""
			if valuesDict["deviceDefs"] == "":
				valuesDict["deviceDefs"]=json.dumps([{} for i in range(nChan)])

			xxx= json.loads(valuesDict["deviceDefs"])
			pinMappings	= ""
			nChan 		= min(nChan,len(xxx))
			for n in range(nChan):
				if "gpio" in xxx[n]:
					pinMappings += "{}".format(n) + ":" + xxx[n]["gpio"] + "|"
			valuesDict["pinMappings"] = pinMappings
		except Exception as e:
			self.exceptionHandler(40, e)


		return valuesDict

####-------------------------------------------------------------------------####
	def getTypeIDLength(self,typeId):
		if typeId.find("INPUT") == -1 and	typeId.find("OUTPUT") == -1:
			return 0
		nn = 1
		tt = typeId.split("-")
		if len(tt)==1:
			tt= typeId
		else:
			tt= tt[1]

		if	 tt.find("10") > -1: nn=10
		elif tt.find("12") > -1: nn=12
		elif tt.find("16") > -1: nn=16
		elif tt.find("20") > -1: nn=20
		elif tt.find("26") > -1: nn=26
		elif tt.find("1")	> -1: nn=1
		elif tt.find("4")	> -1: nn=4
		elif tt.find("8")	> -1: nn=8
		return nn

####-------------------------------------------------------------------------####
	def filterINPUTchannels(self, filter="", valuesDict=None, typeId="", devId="x"):
		xList = []
		for i in range(self.getTypeIDLength(typeId)):
			xList.append(("{}".format(i), "{}".format(i)))
		return xList


####-------------------------------------------------------------------------####
	def confirmStateBUTTONI(self, valuesDict=None, typeId="", devId="x"):
		piN	 	= valuesDict["piServerNumber"]
		inS	 	= valuesDict["INPUTstate"]
		inSi 	= int(inS)
		nChan 	= self.getTypeIDLength(typeId)
		if valuesDict["deviceDefs"]!="":
			xxx = json.loads(valuesDict["deviceDefs"])
			if len(xxx) < nChan:
				for ll in range(nChan-len(xxx)):
					xxx.append({"gpio":"", "inpType":"", "count": "off"})
			if	"gpio" in xxx[inSi] and xxx[inSi]["gpio"] !="":
				valuesDict["gpio"]		 = xxx[inSi]["gpio"]
				if	"inpType" in xxx[inSi]:
					valuesDict["inpType"]	= xxx[inSi]["inpType"]
				valuesDict["count"]	 	= xxx[inSi]["count"]

		valuesDict["stateDone"] = True
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
			piN	 = valuesDict["piServerNumber"]
			try:	 inSi = int(valuesDict["INPUTstate"])
			except:	 inSi = -1
			inS	 = "{}".format(inSi)
			try:	 gpio = "{}".format(int(valuesDict["gpio"]))
			except:	 gpio = "-1"

			if valuesDict["deviceDefs"]!="":
				xxx=json.loads(valuesDict["deviceDefs"])
				if len(xxx) < nChannels:
					for ll in range(nChannels-len(xxx)):
						xxx.append({"gpio":"", "inpType":"", "count": "off"})
			else:
				xxx=[]
				for ll in range(nChannels):
						xxx.append({"gpio":"", "inpType":"", "count": "off"})

			valuesDict["stateDone"] = True


			if valuesDict["gpio"] =="-1":
				xxx[inSi]={}
			else:
				if	   "inpType" in valuesDict:
					xxx[inSi]	= {"gpio": gpio, "inpType": valuesDict["inpType"], "count": valuesDict["count"]}
				else:
					xxx[inSi]	= {"gpio": gpio, "inpType": "", "count": valuesDict["count"]}


			pinMappings =""
			# clean up
			for n in range(nChannels):
				if "gpio" in xxx[n]:
					if xxx[n]["gpio"] == "-1" or xxx[n]["gpio"] =="":
						xxx[n]={}

					pinMappings+= "{}".format(n)+":"+xxx[n]["gpio"]+"|"
					for l in range(n,nChannels):
						if l==n: continue
						if "gpio" not in xxx[l]:	continue
						if xxx[l]["gpio"] == "-1":  continue
						if xxx[n]["gpio"] == xxx[l]["gpio"]:
							pinMappings="error # {}".format(n)+" same pin as #{}".format(l)
							xxx[l]["gpio"]="-1"
							valuesDict["gpio"] = "-1"
							break
					if "error" in pinMappings: break



			valuesDict["pinMappings"] = pinMappings
			valuesDict["deviceDefs"] = json.dumps(xxx)
			return valuesDict

####-------------------------------------------------------------------------####
	def filterPiO(self, valuesDict=None, filter="self", typeId="", devId="x",action= ""):

			xList = []
			for piU in _rpiBeaconList:
				if self.RPI[piU]["piOnOff"] != "0":
					try:
						devId= int(self.RPI[piU]["piDevId"])
						if devId >0:
							name= "-"+indigo.devices[devId].name
					except: name=""
					xList.append([piU, "#"+piU+"-"+self.RPI[piU]["ipNumberPi"]+name])

			return xList

####-------------------------------------------------------------------------####
	def confirmPiNumberBUTTONO(self, valuesDict=None, typeId="", devId="x"):
			piN 	= valuesDict["piServerNumber"]
			nChan 	= self.getTypeIDLength(typeId)
			try:
				idevId = int(devId)
				if idevId != 0:
					dev = indigo.devices[idevId]
					props = dev.pluginProps
			except:
				props = []

			valuesDict["piDone"] = True
			valuesDict["stateDone"] = False
			self.stateNumberForInputGPIOX = ""


			if valuesDict["deviceDefs"] == "" or len(json.loads(valuesDict["deviceDefs"])) != nChan:
				valuesDict["deviceDefs"] = json.dumps([{} for i in range(nChan)])

			xxx 		= json.loads(valuesDict["deviceDefs"])
			pinMappings	= ""
			update		= False
			for n in range(nChan):
				if "gpio" in xxx[n]:
					if "initialValue" not in xxx[n]:
						xxx[n]["initialValue"] ="float"
						update= True
					pinMappings += "{}".format(n) + ":" + xxx[n]["gpio"]+"," + xxx[n]["outType"]+"," + xxx[n]["initialValue"] + "|"
			valuesDict["pinMappings"] = pinMappings
			if update:
				valuesDict["deviceDefs"] = json.dumps(xxx)

			inSi	= 0
			if valuesDict["deviceDefs"] != "":
				if "gpio" in xxx[inSi] and xxx[inSi]["gpio"] != "":
					valuesDict["gpio"]			= xxx[inSi]["gpio"]
					valuesDict["outType"]		= xxx[inSi]["outType"]
					valuesDict["initialValue"]	= xxx[inSi]["initialValue"]

			valuesDict["stateDone"] = True

			return valuesDict



####-------------------------------------------------------------------------####
	def filterSwitchbot(self, filter="", valuesDict=None, typeId="", devId="x"):
			xList = [("-1","off")]
			for dev in indigo.devices.iter("props.isSwitchbotDevice"):
				if dev.deviceTypeId == "OUTPUTswitchbotRelay":
					xList.append(("{}".format(dev.id), "{}".format(dev.name)))
			return xList


####-------------------------------------------------------------------------####
	def filterOUTPUTchannels(self, filter="", valuesDict=None, typeId="", devId="x"):
			xList = []
			for i in range(self.getTypeIDLength(typeId)):
				xList.append(("{}".format(i), "{}".format(i)))
			return xList

####-------------------------------------------------------------------------####
	def filterTempSensorsOnThisRPI(self, filter="", valuesDict=None, typeId="", devId="x"):
		xList = [("0", "internal temp sensor of RPI")]
		try:
			piN = indigo.devices[devId].pluginProps.get("RPINumber","")
			#indigo.server.log(" dev Pi #sensor: " + piN)
			for dev in indigo.devices.iter("props.isTempSensor"):
				props = dev.pluginProps
				#self.indiLOG.log(10," selecting devid name temp sensor: {} pi#: {}".format(dev.name, props["piServerNumber"]) )
				if props["piServerNumber"] == piN:
					xList.append( ("{}".format(dev.id), "{} {}".format(dev.name, dev.id) ))

		except Exception as e:
			self.exceptionHandler(40, e)

		return xList



####-------------------------------------------------------------------------####
	def filtergpioList(self, filter="", valuesDict=None, typeId="", devId="x"):
			return _GlobalConst_allGPIOlist

####-------------------------------------------------------------------------####
	def filterList16(self, filter="", valuesDict=None, typeId="", devId="x"):
			xList = []
			for ii in range(16):
				xList.append((ii,ii))
			return xList

####-------------------------------------------------------------------------####
	def filterList12(self, filter="", valuesDict=None, typeId="", devId="x"):
			xList = []
			for ii in range(12):
				xList.append((ii,ii))
			return xList

####-------------------------------------------------------------------------####
	def filterList10(self, filter="", valuesDict=None, typeId="", devId="x"):
			xList = []
			for ii in range(10):
				xList.append((ii,ii))
			return xList

####-------------------------------------------------------------------------####
	def filterList8(self, filter="", valuesDict=None, typeId="", devId="x"):
			xList = []
			for ii in range(8):
				xList.append((ii,ii))
			return xList

####-------------------------------------------------------------------------####
	def filterList4(self, filter="", valuesDict=None, typeId="", devId="x"):
			xList = []
			for ii in range(4):
				xList.append((ii,ii))
			return xList

####-------------------------------------------------------------------------####
	def filterList1(self, filter="", valuesDict=None, typeId="", devId="x"):
			xList = []
			for ii in range(1):
				xList.append((ii,ii))
			return xList



####-------------------------------------------------------------------------####
	def filteri2cChannelS(self, filter="", valuesDict=None, typeId="", devId="x"):
			piN = valuesDict["piServerNumber"]
			valuesDict["i2cActive"] = "test"
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
				xxx = json.loads(valuesDict["deviceDefs"])
			except:
				xxx=[]
			try:
				oldxxx = json.loads(props["deviceDefs"])
			except:
				oldxxx = copy.deepcopy(xxx)
				for n in range(len(oldxxx)):
					oldxxx[n]["initialValue"] ="x"

			inS = "0"
			inSi = int(inS)
			if valuesDict["gpio"] == "0":
				xxx[inSi] = {}
			else:
				xxx[inSi] = {"gpio": valuesDict["gpio"],"outType": valuesDict["outType"],"initialValue": valuesDict["initialValue"]}
			pinMappings = ""
			# clean up
			for n in range(nChannels):
				if "gpio" in xxx[n]:
					if xxx[n]["gpio"] == "0":
						del xxx[n]
					if	len(oldxxx) < (n+1) or "initialValue" not in oldxxx[n] or (xxx[n]["initialValue"] != oldxxx[n]["initialValue"]):
						self.sendInitialValue = dev.id
					pinMappings += "{}".format(n) + ":" + xxx[n]["gpio"]+ "," + xxx[n]["outType"]+ "," + xxx[n]["initialValue"] + "|"
					if "inverse" in dev.states:
						dev.updateStateOnServer("inverse", "yes" if xxx[n]["outType"] == "1"  else "no")
					elif "inverse_{:2d}".format(n) in dev.states:
						dev.updateStateOnServer("inverse_{:2d}".format(n), "yes" if xxx[n]["outType"] == "1"  else "no")

					if "initial" in dev.states:
						dev.updateStateOnServer("initial", xxx[n]["initialValue"])
					elif "initial{:2d}".format(n) in dev.states:
						dev.updateStateOnServer("initial{:2d}".format(n), xxx[n]["initialValue"] )

					for l in range(n, nChannels):
						if l == n: continue
						if "gpio" not in xxx[l]:	continue
						if xxx[l]["gpio"] == "0":	continue
						if xxx[n]["gpio"] == xxx[l]["gpio"]:
							pinMappings = "error # {} same pin as #{}".format(n, l)
							xxx[l]["gpio"] = "0"
							valuesDict["gpio"] = "0"
							break
					if "error" in pinMappings: break

			valuesDict["pinMappings"] = pinMappings
			valuesDict["deviceDefs"] = json.dumps(xxx)
			self.indiLOG.log(10,"confirmSelectionBUTTONO len:{};  deviceDefs:{}".format(nChannels, valuesDict["deviceDefs"]))
			return valuesDict

####-------------------------------------------------------------------------####
	def sendConfigCALLBACKaction(self, action1=None, typeId="", devId=0):
		try:
			valuesDict = action1.props
			if valuesDict["configurePi"] =="": return
			return self.execButtonConfig(valuesDict, level="0,", action=["updateParamsFTP"], Text="send Config Files to pi# ")
		except:
			self.indiLOG.log(10,"sendConfigCALLBACKaction  bad rPi number:{}".format(valuesDict))

####-------------------------------------------------------------------------####
	def buttonConfirmSendOnlyParamssshCALLBACK(self, valuesDict=None, typeId="", devId=0):
		return self.execButtonConfig(valuesDict, level="0,", action=["updateParamsFTP"], Text="send Config Files to pi# ")

####-------------------------------------------------------------------------####
	def buttonConfirmSendRestartPysshCALLBACK(self, valuesDict=None, typeId="", devId=0):
		return self.execButtonConfig(valuesDict, level="master,", action=["updateParamsFTP"], Text="send Config Files and restart master.py  ")

####-------------------------------------------------------------------------####
	def buttonConfirmRestartMastersshCALLBACK(self, valuesDict=None, typeId="", devId=0):
		return self.execButtonConfig(valuesDict, level="", action=["restartmasterSSH"], Text="restart master.py  ")

####-------------------------------------------------------------------------####
	def buttonConfirmConfigureCALLBACK(self, valuesDict=None, typeId="", devId=0):
		return self.execButtonConfig(valuesDict, level="reboot,", action=["updateParamsFTP"], Text="send Config Files and restart rPI")
####-------------------------------------------------------------------------####
	def buttonResetOutputCALLBACK(self, valuesDict=None, typeId="", devId=0):
		return self.execButtonConfig(valuesDict, level="0,", action=["resetOutputSSH"], Text="reset output file  and reboot pi# ")


####-------------------------------------------------------------------------####
	def buttonShutdownsshCALLBACKaction(self, action1=None, typeId="", devId=0):
		return self.buttonShutdownsshCALLBACK(valuesDict=action1.props)

####-------------------------------------------------------------------------####
	def buttonShutdownsshCALLBACK(self, valuesDict=None, typeId="", devId=0):
		self.setCurrentlyBooting(self.bootWaitTime, setBy="buttonShutdownsshCALLBACK")
		return self.execButtonConfig(valuesDict, level="0,", action=["shutdownSSH"], Text="shut down rPi# ")

####-------------------------------------------------------------------------####
	def buttonSendAllandsshCALLBACK(self, valuesDict=None, typeId="", devId=0):
		self.setCurrentlyBooting(self.bootWaitTime, setBy="buttonSendAllandsshCALLBACK")
		return self.execButtonConfig(valuesDict, level="0,", action=["initSSH", "updateAllFilesFTP","restartmasterSSH"], Text="rPi send pgm and config to pi# ")

####-------------------------------------------------------------------------####
	def buttonSendAllAllandRebootsshCALLBACK(self, valuesDict=None, typeId="", devId=0):
		self.setCurrentlyBooting(self.bootWaitTime, setBy="buttonSendAllAllandRebootsshCALLBACK")
		return self.execButtonConfig(valuesDict, level="0,", action=["initSSH", "updateAllAllFilesFTP", "restartmasterSSH"], Text="rPi configure and reboot pi# ")


####-------------------------------------------------------------------------####
	def buttonRebootsshCALLBACKaction(self,	action1=None, typeId="", devId=0):
		self.buttonRebootSocketCALLBACK(valuesDict=action1.props)

####-------------------------------------------------------------------------####
	def buttonRebootsshCALLBACK(self, valuesDict=None, typeId="", devId=0):
		self.setCurrentlyBooting(self.bootWaitTime, setBy="buttonRebootsshCALLBACK")
		return self.execButtonConfig(valuesDict, level="0,", action=["rebootSSH"], Text="rPi reboot")

####-------------------------------------------------------------------------####
	def buttonStopConfigCALLBACK(self, valuesDict=None, typeId="", devId=0):
		return self.execButtonConfig(valuesDict, level="0,", action=[""], Text="rPi stop Configure ")


####-------------------------------------------------------------------------####
	def buttonGetSystemParametersCALLBACK(self, valuesDict=None, typeId="", devId=0):
		return self.execButtonConfig(valuesDict, level="0,", action=["getStatsSSH"], Text="get stats from rpi")


###-------------------------------------------------------------------------####
	def buttonUpgradeCALLBACK(self, valuesDict=None, typeId="", devId=0):
		return self.execButtonConfig(valuesDict, level="0,", action=["upgradeSSH"], Text="apt-get update and apt-get upgrade")

####-------------------------------------------------------------------------####
	def buttonbuttonGetpiBeaconLogCALLBACK(self, valuesDict=None, typeId="", devId=0):
		return self.execButtonConfig(valuesDict, level="0,", action=["getLogFileSSH"], Text="get pibeacon logfile from rpi")

####-------------------------------------------------------------------------####
	def execButtonConfig(self, valuesDict, level="0,", action=[], Text=""):
		valuesDict["MSG"] = "Error"
		try:
			try:
				pi = int(valuesDict["configurePi"])
			except:
				return valuesDict
			piU = "{}".format(pi)

			if pi == 999:
				self.setALLrPiV("piUpToDate", action, resetQueue=True)
				self.rPiRestartCommand = [level for ii in range(_GlobalConst_numberOfRPI)]	## which part need to restart on rpi
				return valuesDict
			if pi < 99:
				if self.decideMyLog("UpdateRPI"): self.indiLOG.log(5,"{} {}  action string:{}".format(Text,piU, action)	 )
				self.rPiRestartCommand[pi] = level	## which part need to restart on rpi
				self.setONErPiV(piU, "piUpToDate", action, resetQueue=True)
			valuesDict["MSG"] = "command {} submitted".format(action)
			return valuesDict
		except Exception as e:
			self.exceptionHandler(40, e)
		valuesDict["MSG"] = "Error, see log"
		return valuesDict


####-------------------------------------------------------------------------####
	def buttonConfirmWiFiCALLBACK(self, valuesDict=None, typeId="", devId=0):
		valuesDict["MSG"] = "Error"
		try:
			pi = int(valuesDict["configurePi"])
		except:
			return valuesDict
		piU = "{}".format(pi)
		for piU in self.RPI:
				if self.wifiSSID != "" and self.wifiPassword != "":
					if self.decideMyLog("UpdateRPI"): self.indiLOG.log(5,"configuring WiFi on pi#".format(piU))
					self.rPiRestartCommand = ["restart" for ii in range(_GlobalConst_numberOfRPI)]	 ## which part need to restart on rpi
					self.configureWifi(piU)
				else:
					self.indiLOG.log(10,"buttonConfirmWiFiCALLBACK configuring WiFi: SSID and password not set")

		if pi < 99:
			if self.wifiSSID != "" and self.wifiPassword != "":
				if self.decideMyLog("UpdateRPI"): self.indiLOG.log(5,"configuring WiFi on pi#{}".format(piU))
				self.rPiRestartCommand[pi] = "reboot"  ## which part need to restart on rpi
				self.configureWifi(piU)
			else:
				self.indiLOG.log(10,"buttonConfirmWiFiCALLBACK configuring WiFi: SSID and password not set")

		valuesDict["MSG"] = "command submitted"
		return valuesDict


####-------------------------------------------------------------------------####
	def buttonShutdownHardSocketCALLBACKaction(self,  action1=None, typeId="", devId=0):
		self.buttonShutdownHardSocketCALLBACK(valuesDict=action1.props)

####-------------------------------------------------------------------------####
	def buttonShutdownHardSocketCALLBACK(self, valuesDict=None ,typeId="", devId=0):
		valuesDict["MSG"] = "Error"
		try:
			pi = int(valuesDict["configurePi"])
		except:
			return valuesDict
		piU = "{}".format(pi)
		out= [{"command":"general", "cmdLine":"sudo killall -9 python;sudo killall -9 python3;sync;sleep 5;sudo halt &"}]
		if pi == 999:
			for piU in self.RPI:
				self.indiLOG.log(10,"hard shutdown of rpi {};   {}".format(self.RPI[piU]["ipNumberPi"], out) )
				self.presendtoRPI(piU,out)
		else:
				self.indiLOG.log(10,"hard shutdown of rpi {};   {}".format(self.RPI[piU]["ipNumberPi"], out) )
				self.presendtoRPI(piU,out)
		valuesDict["MSG"] = "command halt submitted"
		return


####-------------------------------------------------------------------------####
	def buttonRebootHardSocketCALLBACKaction(self,	action1=None, typeId="", devId=0):
		self.buttonRebootHardSocketCALLBACK(valuesDict=action1.props)

####-------------------------------------------------------------------------####
	def buttonRebootHardSocketCALLBACK(self, valuesDict=None, typeId="", devId=0):
		valuesDict["MSG"] = "Error"
		pi = valuesDict["configurePi"]
		try:
			pi = int(valuesDict["configurePi"])
		except:
			return valuesDict
		piU = "{}".format(pi)

		out= [{"command":"general", "cmdLine":"sudo killall -9 python;sudo killall -9 python3;sync;sleep 5;sudo reboot -f &"}]
		if pi == 999:
			for piU in self.RPI:
				self.presendtoRPI(piU,out)
		else:
				self.indiLOG.log(10,"hard reboot of rpi{};   {}".format(self.RPI[piU]["ipNumberPi"], out) )
				self.presendtoRPI(piU,out)
		valuesDict["MSG"] = "command reboot -f submitted"
		return




####-------------------------------------------------------------------------####
	def buttonRebootSocketCALLBACKaction(self,	action1=None, typeId="", devId=0):
		self.buttonRebootSocketCALLBACK(valuesDict=action1.props)

####-------------------------------------------------------------------------####
	def buttonRebootSocketCALLBACK(self, valuesDict=None, typeId="", devId=0):
		valuesDict["MSG"] = "Error"
		try:
			pi = int(valuesDict["configurePi"])
		except:
			return valuesDict
		piU = "{}".format(pi)

		out= [{"command":"general", "cmdLine":"sudo killall -9 python;sudo killall -9 python3;sleep 4; sudo reboot &"}]
		if pi == 999:
			for piU in self.RPI:
				self.indiLOG.log(10,"regular reboot of rpi {};  {}".format(self.RPI[piU]["ipNumberPi"], out) )
				self.presendtoRPI(piU,out)
		else:
				self.indiLOG.log(10,"regular reboot of rpi {};  {}".format(self.RPI[piU]["ipNumberPi"], out) )
				self.presendtoRPI(piU,out)

		valuesDict["MSG"] = "command reboot submitted"
		return valuesDict


####-------------------------------------------------------------------------####
	def setTimeCALLBACKaction(self, action1=None, typeId="", devId=0):
		self.doActionSetTime(action1.props["configurePi"])# do it now
		return 

####-------------------------------------------------------------------------####
	def buttonsetTimeCALLBACK(self, valuesDict=None, typeId="", devId=0):
		self.actionList["setTime"].append({"action":"setTime", "value":valuesDict["configurePi"]}) # put it into queue and return to menu
		valuesDict["MSG"] = "command setTime started"
		return valuesDict

####-------------------------------------------------------------------------####
	def refreshNTPCALLBACKaction(self, action1=None, typeId="", devId=0):
		valuesDict = action1.props
		self.buttonrefreshNTPCALLBACK(valuesDict)
		return 

####-------------------------------------------------------------------------####
	def buttonrefreshNTPCALLBACK(self, valuesDict=None, typeId="", devId=0):
		self.buttonAnycommandCALLBACK(valuesDict)
		valuesDict["MSG"] = "command refreshNTP started"
		return valuesDict

####-------------------------------------------------------------------------####
	def stopNTPCALLBACKaction(self,	 action1=None, typeId="", devId=0):
		valuesDict = action1.props
		self.buttonstopNTPCALLBACK(valuesDict)
		return 

####-------------------------------------------------------------------------####
	def buttonstopNTPCALLBACK(self, valuesDict=None, typeId="", devId=0):
		self.buttonAnycommandCALLBACK(valuesDict)
		valuesDict["MSG"] = "command "+valuesDict["anyCmdText"] +" started"
		return valuesDict


####-------------------------------------------------------------------------####
	def doActionSetTime(self, piU):
		try:
			if piU not in self.RPI: return

		except:
			self.indiLOG.log(10,"ERROR	set time of rpi	 bad PI# given:"+piU )
			return

		try:

			ipNumberPi = self.RPI[piU]["ipNumberPi"]
			dt =0
			xx, retC = self.testDeltaTime( piU, ipNumberPi,dt)
			for ii in range(5):
				dt , retC  = self.testDeltaTime( piU, ipNumberPi, dt*0.9)
				if retC !=0:
					self.indiLOG.log(10,"sync time	MAC --> RPI, did not work, no connection to RPI# {}".format(piU) )
					return
				if abs(dt) < 0.5: break

			self.indiLOG.log(10,"set time of RPI# {}  finished, new delta time ={:6.1f}[secs]".format(piU,dt))

		except Exception as e:
			self.exceptionHandler(40, e)

		return

####-------------------------------------------------------------------------####
	def testDeltaTime(self, piU, ipNumberPi, tOffset):
		try:

			dateTimeString = datetime.datetime.fromtimestamp(time.time()+ tOffset).strftime(_defaultDateStampFormat+".%f")
			out= [{"command":"general", "cmdLine":"setTime="+dateTimeString}]
			retC = self.presendtoRPI(piU,out)
			if retC !=0: return 0, retC
			if self.decideMyLog("UpdateRPI"):self.indiLOG.log(10,"set time # of rpi:{}; ip:{};  offset-used:{:5.2f};  cmd:{}".format(piU, ipNumberPi, tOffset, out) )

			self.RPI[piU]["deltaTime1"] =-99999
			for ii in range(20):
				if self.RPI[piU]["deltaTime1"] != -99999: break
				time.sleep(0.1)

			delta1 = self.RPI[piU]["deltaTime1"]
			delta2 = self.RPI[piU]["deltaTime2"]
			if abs(delta1) < 1.5 and abs(delta2) < 1.5:
				dt = abs(delta1*3.+delta2) /4.
			else:
				if abs(delta1) < abs(delta2): dt = delta1
				else:						  dt = delta2

			return dt, retC

		except Exception as e:
			self.exceptionHandler(40, e)


		return 0, -1


####-------------------------------------------------------------------------####
	def sendAnycommandCALLBACKaction(self, action1=None, typeId="", devId=0):
		self.buttonAnycommandCALLBACK(valuesDict=action1.props)
		return

####-------------------------------------------------------------------------####
	def buttonAnycommandCALLBACK(self, valuesDict=None, typeId="", devId=0):
		piU = valuesDict["configurePi"]
		if piU =="":
			self.indiLOG.log(10,"send YOUR command to rpi ...  no RPI selected")
			return
		if piU == "999":
			for piU in self.RPI:
				out= [{"command":"general", "cmdLine":valuesDict["anyCmdText"]}]
				if self.RPI[piU]["ipNumberPi"] !="":
					self.indiLOG.log(10,"send YOUR command to rpi:{}  {};  {}".format(piU, self.RPI[piU]["ipNumberPi"], out) )
					self.presendtoRPI(piU,out)
		else:
				out= [{"command":"general", "cmdLine":valuesDict["anyCmdText"]}]
				self.indiLOG.log(10,"send YOUR command to rpi:{}  {};  {}".format(piU, self.RPI[piU]["ipNumberPi"], out) )
				self.presendtoRPI(piU,out)

		return


####-------------------------------------------------------------------------####
	def filterBeacons(self, filter="", valuesDict=None, typeId="", devId=0, action=""):
		xList = []
		for dev in indigo.devices.iter("props.isBeaconDevice"):
			xList.append((dev.id,"{}".format(dev.name)))
		xList.append((0, "delete"))
		return xList

####-------------------------------------------------------------------------####
	def filterBeaconsWithBattery(self, filter="", valuesDict=None, typeId="", devId=0, action=""):
		xList = []
		for dev in indigo.devices.iter("props.isBeaconDevice"):
			if not dev.enabled:													continue
			if not dev.pluginProps.get("SupportsBatteryLevel", False): 			continue
			if not dev.pluginProps.get("batteryLevelUUID","") == "gatttool":	continue
			xList.append((dev.id, "{} - {}".format(dev.name, dev.address) ))
		xList.append(["0", "all"])
		return xList


####-------------------------------------------------------------------------####
	def filterSoundFiles(self, filter="", valuesDict=None, typeId="", devId=0, action=""):
		xList = []
		for fileName in os.listdir(self.indigoPreferencesPluginDir+"soundFiles/"):
			xList.append((fileName,fileName))
		return xList

####-------------------------------------------------------------------------####
	def filterSensorONoffIcons(self, filter="", valuesDict=None, typeId="", devId=0, action=""):
		xList = []
		for ll in _GlobalConst_ICONLIST:
			xList.append((ll[0]+"-"+ll[1],ll[0]+", "+ll[1]))
		xList.append(("-", "     "))
		return xList


####-------------------------------------------------------------------------####
	def filterPiD(self, filter="", valuesDict=None, typeId="", devId=0, action=""):
		xList = []
		for piU in _rpiBeaconList:
			if self.RPI[piU]["piOnOff"] == "0" or self.RPI[piU]["ipNumberPi"] == "":
				xList.append([piU, piU + "-"])
			else:
				xList.append([piU, piU + "-" + self.RPI[piU]["ipNumberPi"] + "-" + self.RPI[piU]["piMAC"]])
		for piU in _rpiSensorList:
			if self.RPI[piU]["piOnOff"] == "0" or self.RPI[piU]["ipNumberPi"] == "":
				xList.append([piU, piU + "-  - Sensor Only"])
			else:
				xList.append([piU, piU + "-" + self.RPI[piU]["ipNumberPi"] + "- Sensor Only"])
		return xList

####-------------------------------------------------------------------------####
	def filterPiDONoff(self, filter="", valuesDict=None, typeId="", devId=0, action=""):
		xList = [["-1", "off"]]
		for piU in _rpiBeaconList:
			if self.RPI[piU]["piOnOff"] == "0" or self.RPI[piU]["ipNumberPi"] == "":
				xList.append([piU, piU + "-"])
			else:
				xList.append([piU, piU + "-" + self.RPI[piU]["ipNumberPi"] + "-" + self.RPI[piU]["piMAC"]])
		for piU in _rpiSensorList:
			if self.RPI[piU]["piOnOff"] == "0" or self.RPI[piU]["ipNumberPi"] == "":
				xList.append([piU, piU + "-  - Sensor Only"])
			else:
				xList.append([piU, piU + "-" + self.RPI[piU]["ipNumberPi"] + "- Sensor Only"])
		return xList

####-------------------------------------------------------------------------####
	def filterPiOnlyBlue(self, filter="", valuesDict=None, typeId="", devId=0, action=""):
		xList = []
		for piU in _rpiBeaconList:
			if self.RPI[piU]["piOnOff"] == "0" or self.RPI[piU]["ipNumberPi"] == "":
				pass
			else:
				xList.append([piU, piU + "-" + self.RPI[piU]["ipNumberPi"] + "-" + self.RPI[piU]["piMAC"]])
		return xList

####-------------------------------------------------------------------------####
	def filterPibeaconOne(self, filter="", valuesDict=None, typeId="", devId=0, action=""):
		xList = []
		for piU in _rpiBeaconList:
			if self.RPI[piU]["piOnOff"] == "0" or self.RPI[piU]["ipNumberPi"] == "":
				pass
			else:
				xList.append([piU, piU + "-" + self.RPI[piU]["ipNumberPi"] + "-" + self.RPI[piU]["piMAC"]])
		xList.append([-1,"use closest" ])
		return xList


####-------------------------------------------------------------------------####
	def filterPiC(self, filter="", valuesDict=None, typeId="", devId=0, action=""):
		xList = []
		for piU in _rpiBeaconList:
			if self.RPI[piU]["piOnOff"] == "0" or self.RPI[piU]["ipNumberPi"] == "": continue
			xList.append([piU, piU + "-" + self.RPI[piU]["ipNumberPi"] + "-" + self.RPI[piU]["piMAC"]])
		for piU in _rpiSensorList:
			if self.RPI[piU]["piOnOff"] == "0" or self.RPI[piU]["ipNumberPi"] == "": continue
			xList.append([piU, piU + "-" + self.RPI[piU]["ipNumberPi"] + "- Sensor Only"])
		xList.append([-1, "off"])
		return xList


####-------------------------------------------------------------------------####
	def filterPiBLE(self, filter="", valuesDict=None, typeId="", devId=0, action=""):
		xList = []
		for piU in _rpiBeaconList:
			if self.RPI[piU]["piOnOff"] == "0" or self.RPI[piU]["ipNumberPi"] == "": continue
			xList.append([piU, piU + "-" + self.RPI[piU]["ipNumberPi"] + "-" + self.RPI[piU]["piMAC"]])
		xList.append([999, "all"])
		return xList


####-------------------------------------------------------------------------####
	def filterPi(self, filter="", valuesDict=None, typeId="", devId=0, action=""):
		xList = []
		for piU in _rpiBeaconList:
			if self.RPI[piU]["piOnOff"] == "0" or self.RPI[piU]["ipNumberPi"] == "": continue
			xList.append([piU, piU + "-" + self.RPI[piU]["ipNumberPi"] + "-" + self.RPI[piU]["piMAC"]])
		for piU in _rpiSensorList:
			if self.RPI[piU]["piOnOff"] == "0" or self.RPI[piU]["ipNumberPi"] == "": continue
			xList.append([piU, piU + "-" + self.RPI[piU]["ipNumberPi"] + "- Sensor Only"])
		xList.append([999, "all"])
		return xList

####-------------------------------------------------------------------------####
	def filterPiNoAll(self, filter="", valuesDict=None, typeId="", devId=0, action=""):
		xList = []
		for piU in _rpiBeaconList:
			if self.RPI[piU]["piOnOff"] == "0": 	continue
			if self.RPI[piU]["ipNumberPi"] == "": 	continue
			xList.append([piU, piU + "-" + self.RPI[piU]["ipNumberPi"] + "-" + self.RPI[piU]["piMAC"]])
		for piU in _rpiSensorList:
			if self.RPI[piU]["piOnOff"] == "0": 	continue
			if self.RPI[piU]["ipNumberPi"] == "": 	continue
			xList.append([piU, piU + "-" + self.RPI[piU]["ipNumberPi"] + "- Sensor Only"])
		return xList

####-------------------------------------------------------------------------####
	def filterPiOUT(self, filter="", valuesDict=None, typeId="", devId=0, action=""):
		xList = []
		default = ""
		for piU in self.RPI:
			if self.RPI[piU]["piOnOff"] == "0": 	continue
			if self.RPI[piU]["ipNumberPi"] == "": 	continue
			if self.RPI[piU]["piDevId"] == 0: 		continue
			devIDpi = self.RPI[piU]["piDevId"]
			if typeId in self.RPI[piU]["output"] and "{}".format(devId) in self.RPI[piU]["output"][typeId]:
				try:
					default = (piU, "Pi-" + piU + "-" + self.RPI[piU]["ipNumberPi"] + ";  Name =" + indigo.devices[devIDpi].name)
				except Exception as e:
					self.exceptionHandler(40, e)
					self.indiLOG.log(40," devid {}".format(devIDpi))
				continue
			else:
				try:
					xList.append((piU, "Pi-" + piU + "-" + self.RPI[piU]["ipNumberPi"] + ";  Name =" + indigo.devices[devIDpi].name))
				except Exception as e:
					self.exceptionHandler(40, e)
					self.indiLOG.log(40," devid {}".format(devIDpi))

		if default != "":
			xList.append(default)

		return xList



####-------------------------------------------------------------------------####
	def filterActiveBEACONs(self, filter="", valuesDict=None, typeId="", devId=0, action=""):

		try:
			listActive = []
			for mac in self.beacons:
				if len(mac) < 5 or mac.find("00:00:00:00") ==0: continue
				try:
					name = indigo.devices[self.beacons[mac]["indigoId"]].name
				except:
					continue
				if self.beacons[mac]["ignore"] <= 0 and self.beacons[mac]["indigoId"] != 0:
					listActive.append([mac, name + "- active, used"])
			listActive = sorted(listActive, key=lambda tup: tup[1])
		except Exception as e:
			self.exceptionHandler(40, e)
			listActive = []
		return listActive

####-------------------------------------------------------------------------####
	def filterMACs(self, filter="", valuesDict=None, typeId="", devId=0, action=""):

		try:
			listActive		 = []
			listDeleted		 = []
			listIgnored		 = []
			listOldIgnored	 = []


			for mac in self.beacons:
				if len(mac) < 5: continue
				try:
					name = indigo.devices[self.beacons[mac]["indigoId"]].name
				except:
					name = mac


				if self.beacons[mac]["ignore"] <= 0 and self.beacons[mac]["indigoId"] != 0:
					listActive.append([mac, "{}- active, used".format(name)])

				elif self.beacons[mac]["ignore"] == 0 and self.beacons[mac]["indigoId"] == 0:
					listDeleted.append([mac, "{}- deleted previously".format(name)])

				elif self.beacons[mac]["ignore"] == 1:
					listIgnored.append([mac, "{}- on ignoredList".format(name)])

				elif self.beacons[mac]["ignore"] == 2:
					listOldIgnored.append([mac, "{}- on ignoredList- old".format(mac)])

			listActive 		= sorted(listActive, key=lambda tup: tup[1])
			listDeleted 	= sorted(listDeleted, key=lambda tup: tup[1])
			listIgnored 	= sorted(listIgnored, key=lambda tup: tup[1])
			listOldIgnored 	= sorted(listOldIgnored, key=lambda tup: tup[1])
			#self.indiLOG.log(20,"listActive:{}\nlistDeleted:{}\nlistIgnored:{}\nlistOldIgnored:{}".format(listActive, listDeleted, listIgnored, listOldIgnored))

			return  listOldIgnored + listDeleted + listIgnored + listActive
		except Exception as e:
			self.exceptionHandler(40, e)
		return []


####-------------------------------------------------------------------------####
	def filterRPIs(self, filter="", valuesDict=None, typeId="", devId=0, action=""):

		try:
			xList = []
			for dev in indigo.devices.iter("props.isRPIDevice"):
				if dev.deviceTypeId !="rPI": continue
				try:
					name = dev.name
					ipN	 = dev.description
					xList.append(["{}".format(dev.id), "{} - {}".format(name, ipN) ])

				except:
					pass
			return sorted(xList, key=lambda tup: tup[1])

		except Exception as e:
			self.exceptionHandler(40, e)
		return []


####-------------------------------------------------------------------------####
	def filterActiveSensors(self, filter="", valuesDict=None, typeId="", devId=0, action=""):

		try:
			xList = []
			for dev in indigo.devices.iter("props.isSensorDevice"):
				if dev.deviceTypeId == "BLEconnect": continue
				try:
					name = dev.name
					xList.append(["{}".format(dev.id), "{}".format(name) ])

				except:
					pass
			return sorted(xList, key=lambda tup: tup[1])

		except Exception as e:
			self.exceptionHandler(40, e)
		return []



####-------------------------------------------------------------------------####
	def filterLightSensorOnRpi(self, filter="", valuesDict=None, typeId="", devId=0, action=""):

		try:
			#self.indiLOG.log(20," filter {}; valuesDict {}".format(filter, valuesDict))
			xList = []
			piServerNumber = valuesDict.get("piServerNumber","-2")
			for dev in indigo.devices.iter("props.isSensorDevice"):
				if piServerNumber != dev.pluginProps.get("piServerNumber","-1"): continue
				if dev.deviceTypeId not in _GlobalConst_lightSensors: continue
				try:
					name = dev.name
					xList.append(["{}-{}".format(dev.id,dev.deviceTypeId), "{}".format(name) ])

				except:
					pass
			return sorted(xList, key=lambda tup: tup[1])

		except Exception as e:
			self.exceptionHandler(40, e)
		return []


####-------------------------------------------------------------------------####

	def getMenuActionConfigUiValues(self, menuId):
		#self.indiLOG.log(10,"getMenuActionConfigUiValues menuId".format(menuId) )
		valuesDict = indigo.Dict()
		errorMsgDict = indigo.Dict()
		if  menuId == "AcceptNewBeacons":
			valuesDict["acceptNewiBeacons"] = "999"
			valuesDict["acceptNewTagiBeacons"] = "off"
			valuesDict["acceptNewMFGNameBeaconsText"] = ""
			valuesDict["acceptNewMFGNameBeacons"] = "off"
			valuesDict["MSG"] = "RSSI >{}; Tag={}, mfgName:{}".format(self.acceptNewiBeacons, self.acceptNewTagiBeacons, self.acceptNewMFGNameBeacons)
		elif menuId == "xx":
			pass
		else:
			pass
		return (valuesDict, errorMsgDict)

####-------------------------------------------------------------------------####
	def buttonConfirmnewBeaconsLogTimerCALLBACK(self, valuesDict=None, typeId="", devId=0):
		try:
			xx = float(valuesDict["newBeaconsLogTimer"])
			if xx > 0:
				self.newBeaconsLogTimer = time.time() + xx*60
				self.indiLOG.log(10,"newBeaconsLogTimer set to: {} minutes".format(valuesDict["newBeaconsLogTimer"]) )
				valuesDict["MSG"]  = "newBeaconsLogTimer: {} min".format(valuesDict["newBeaconsLogTimer"])
			else:
				self.newBeaconsLogTimer = 0
				valuesDict["MSG"]  = "newBeaconsLogTimer:off"
		except Exception as e:
			self.exceptionHandler(40, e)
			valuesDict["MSG"]  = "error, check log"
			self.newBeaconsLogTimer = 0
		return valuesDict




####-------------------------------------------------------------------------####
	def buttonConfirmStopSelectBeaconCALLBACK(self, valuesDict=None, typeId="", devId=0):
		self.selectBeaconsLogTimer = {}
		return valuesDict

####-------------------------------------------------------------------------####
	def buttonConfirmSelectBeaconCALLBACK(self, valuesDict=None, typeId="", devId=0):
		try:
			if self.isValidMAC(valuesDict["selectBEACONmanual"]):
				mac = valuesDict["selectBEACONmanual"]
				self.selectBeaconsLogTimer[mac]	 = 17
				self.indiLOG.log(10,"log messages for mac:{}".format(mac) )
				valuesDict["MSG"]  = "tracking of new beacon started:" + mac
				return valuesDict

			elif len(valuesDict["selectBEACONmanual"]) >0:
				self.indiLOG.log(30,"bad mac given:{}".format(valuesDict["selectBEACONmanual"]))
				valuesDict["MSG"]  = "bad mac given:{}".format(valuesDict["selectBEACONmanual"])
				return valuesDict

			else:
				id	= self.beacons[valuesDict["selectBEACON"]]["indigoId"]
				length = int(valuesDict["selectBEACONlen"])
				dev = indigo.devices[int(id)]
				self.indiLOG.log(10,"log messages for  beacon:{} mac:{}".format(dev.name, valuesDict["selectBEACON"][:length]) )
				self.selectBeaconsLogTimer[valuesDict["selectBEACON"]]	 = length
				valuesDict["MSG"]  = "track beacon:{}".format(dev.name)

		except Exception as e:
			self.exceptionHandler(40, e)
			return valuesDict
		return valuesDict


####-------------------------------------------------------------------------####
	def buttonConfirmSelectSensorCALLBACK(self, valuesDict=None, typeId="", devId=0):
		try:
			self.trackSensorId.append(valuesDict["selectSensor"])
			devName = indigo.devices[int(valuesDict["selectSensor"])].name
			self.indiLOG.log(20,"logging all messages for sensor >>{}<<".format(devName) )
			valuesDict["MSG"]  = "{} logging started".format(devName)
			return valuesDict

		except Exception as e:
			self.exceptionHandler(40, e)
			return valuesDict
		return valuesDict

####-------------------------------------------------------------------------####
	def buttonConfirmStopSelectSensorCALLBACK(self, valuesDict=None, typeId="", devId=0):
		try:
			for devIds in self.trackSensorId:
				self.indiLOG.log(20,"logging messages stopped for sensor >>{}<< ".format(indigo.devices[int(devIds)].name))
			valuesDict["MSG"] = "logging sensors stopped"
		except: pass
		self.trackSensorId = []
		return valuesDict



####-------------------------------------------------------------------------####
	def buttonConfirmselectLargeChangeInSignalCALLBACK(self, valuesDict=None, typeId="", devId=0):
		xx =  valuesDict["trackSignalStrengthIfGeaterThan"].split(",")
		self.trackSignalStrengthIfGeaterThan = [float(xx[0]),xx[1]]

		if self.trackSignalStrengthIfGeaterThan[0] > 150:
			startStop  = "stopped"
		else:
			startStop  = "started"

		if xx[1] =="i":
			if startStop == "started":
				self.indiLOG.log(10,"log messages for beacons with signal strength change GT {}  including ON->off and off-ON".format(self.trackSignalStrengthIfGeaterThan[0]))
				valuesDict["MSG"]  = "signl > {} w on/off".format(self.trackSignalStrengthIfGeaterThan[0])
			else:
				self.indiLOG.log(10,"log messages for beacons with signal strength ... stopped")
				valuesDict["MSG"]  = "signl logging   stopped"
		else:
			if startStop == "started":
				self.indiLOG.log(10,"log messages for beacons with signal strength change GT {}  excluding ON->off and off-ON".format(self.trackSignalStrengthIfGeaterThan[0]))
				valuesDict["MSG"]  = "signl > {} w/o on/off".format(self.trackSignalStrengthIfGeaterThan[0])
			else:
				self.indiLOG.log(10,"log messages for beacons with signal strength ... stopped")
				valuesDict["MSG"]  = "signl logging   stopped"
		return valuesDict

####-------------------------------------------------------------------------####
	def buttonConfirmselectChangeOfRPICALLBACK(self, valuesDict=None, typeId="", devId=0):
		self.trackSignalChangeOfRPI = valuesDict["trackSignalChangeOfRPI"] =="1"
		self.indiLOG.log(10,"log messages for beacons that change closest RPI: {}".format(self.trackSignalChangeOfRPI))
		valuesDict["MSG"] = "log changing closest RPI: {}".format(self.trackSignalChangeOfRPI)
		return valuesDict


####-------------------------------------------------------------------------####
	def buttonExecuteReloadKnownBeaconsTagsCALLBACK(self, valuesDict=None, typeId="", devId=0):

		retCode = self.readknownBeacontags()
		if retCode:
			self.indiLOG.log(10,"knownbeacontags file reloaded, and RPI update initiated")
			valuesDict["MSG"] = "file reloaded, and RPI update initiated"
			self.updateNeeded = " fixConfig "
			self.setALLrPiV("piUpToDate", ["updateParamsFTP"])
		else:
			self.indiLOG.log(10,"inputfile seems to be corrupt")
			valuesDict["MSG"] = "inputfile seems to be corrupt"

		return valuesDict


####-------------------------------------------------------------------------####
	def buttonConfirmselectRPImessagesCALLBACK(self, valuesDict=None, typeId="", devId=0):

		try:	self.trackRPImessages = int(valuesDict["piServerNumber"])
		except: self.trackRPImessages = -1
		if self.trackRPImessages == -1:
			self.indiLOG.log(10,"log all messages from pi: off" )
		else:
			self.indiLOG.log(10,"log all messages from pi: {}".format(self.trackRPImessages ))

		return valuesDict


####-------------------------------------------------------------------------####
	def buttonExecuteReplaceBeaconCALLBACK(self, valuesDict=None, typeId="", devId=0):

		try:

			oldMAC = valuesDict["oldMAC"]
			newMAC = valuesDict["newMAC"]
			oldINDIGOid = self.beacons[oldMAC]["indigoId"]
			newINDIGOid = self.beacons[newMAC]["indigoId"]
			oldDEV = indigo.devices[oldINDIGOid]
			newDEV = indigo.devices[newINDIGOid]
			oldName = oldDEV.name
			newName = newDEV.name
			oldPROPS = oldDEV.pluginProps



			if oldDEV.states["status"].lower() != "expired":
				self.indiLOG.log(10,"ERROR can not replace existing active beacon;{}   still active".format(oldName) )
				valuesDict["MSG"] = "ERROR can not replace existing ACTIVE beacon"
				return valuesDict
			if oldMAC == newMAC:
				self.indiLOG.log(10,"ERROR, can't replace itself")
				valuesDict["MSG"] = "ERROR,choose 2 different beacons"
				return valuesDict

			oldPROPS["address"] = newMAC
			
			oldDEV.replacePluginPropsOnServer(oldPROPS)

			self.beacons[newMAC] = copy.deepcopy(self.beacons[oldMAC])
			self.beacons[newMAC]["indigoId"] = oldINDIGOid
			del self.beacons[oldMAC]
			indigo.device.delete(newDEV)

			self.indiLOG.log(30,"=== deleting  === replaced MAC number {}  of device {} with {} --	and deleted device {}    ===".format(oldMAC, oldName, newMAC, newName) )
			valuesDict["MSG"] = "replaced, moved MAC number"

		except Exception as e:
			self.exceptionHandler(40, e)
		return valuesDict

####-------------------------------------------------------------------------####
	def buttonExecuteReplaceRPICALLBACK(self, valuesDict=None, typeId="", devId=0):

		try:

			oldID = valuesDict["oldID"]
			newID = valuesDict["newID"]
			if oldID == newID:
				valuesDict["MSG"] = "must use 2 different RPI"
				return

			oldDEV	 = indigo.devices[int(oldID)]
			newDEV	 = indigo.devices[int(newID)]
			oldName	 = oldDEV.name
			newName	 = newDEV.name
			oldPROPS = oldDEV.pluginProps
			newPROPS = newDEV.pluginProps
			oldMAC	 =	copy.deepcopy(oldPROPS["address"])
			newMAC	 =	copy.deepcopy(newPROPS["address"])

			oldPROPS["address"] = newMAC
			
			oldDEV.replacePluginPropsOnServer(oldPROPS)
			newPROPS["address"] = newMAC[:-1]+"x"
			
			newDEV.replacePluginPropsOnServer(newPROPS)


			self.beacons[newMAC] = self.beacons[oldMAC]
			self.beacons[newMAC]["indigoId"]= oldDEV.id

			if oldMAC not in self.beacons:
				self.beacons[oldMAC] = copy.deepcopy(_GlobalConst_emptyRPI)
			self.beacons[oldMAC]["indigoId"]= newDEV.id


			try:
				piN = oldPROPS.props.get("RPINumber","")
				self.RPI[piN]["piMAC"] = newMAC
			except:
				pass

			self.fixConfig(checkOnly = ["all", "rpi"],fromPGM="buttonExecuteReplaceRPICALLBACK")
			self.indiLOG.log(30,"=== replaced MAC number {}  of device {} with {} --	and deleted device {}    ===".format(oldMAC, oldName, newMAC, newName) )
			valuesDict["MSG"] = "replaced, moved MAC number"

		except Exception as e:
			self.exceptionHandler(40, e)
		return valuesDict

####-------------------------------------------------------------------------####
	def inpDummy(self, valuesDict=None, typeId="", devId=0):
		return

####-------------------------------------------------------------------------####
	def buttonConfirmMACIgnoreCALLBACK(self, valuesDict=None, typeId="", devId=0):
		mac = valuesDict["ignoreMAC"]
		if mac in self.beacons:
			if self.beacons[mac]["ignore"] == 0:
				self.beacons[mac]["ignore"] = 1
				self.newIgnoreMAC += 1

				for piU in _rpiBeaconList:
					self.setONErPiV(piU, "piUpToDate", ["updateParamsFTP"], resetQueue=True)
		else:
			self.beacons[mac] = copy.deepcopy(_GlobalConst_emptyBeacon)
			self.beacons[mac]["ignore"] = 1
			self.newIgnoreMAC += 1
			self.beacons[mac]["created"] = datetime.datetime.now().strftime(_defaultDateStampFormat)
		self.indiLOG.log(20,"setting {};  indigoId: {} to ignore -mode: {}".format(mac, self.beacons[mac]["indigoId"], self.beacons[mac]["ignore"]) )
		self.beacons[mac]["status"] = "ignored"
		if self.beacons[mac]["indigoId"] >0:
			try:
				self.indiLOG.log(30,"===buttonConfirmMACIgnoreCALLBACK deleting dev  MAC#{}  indigoID ==0".format(mac) )
				indigo.device.delete(indigo.devices[self.beacons[mac]["indigoId"]])
			except:
				self.indiLOG.log(40,"buttonConfirmMACIgnoreCALLBACK error deleting dev  MAC#{}".format(mac) )

		self.makeBeacons_parameterFile()
		for piU in _rpiBeaconList:
			self.setONErPiV(piU, "piUpToDate", ["updateParamsFTP"], resetQueue=True)


		return valuesDict

####-------------------------------------------------------------------------####
	def buttonConfirmMACunIgnoreCALLBACK(self, valuesDict=None, typeId="", devId=0):
		mac = valuesDict["ignoreMAC"]
		if mac in self.beacons:
			if self.beacons[mac]["ignore"] != 0:
				self.beacons[mac]["ignore"] = 0
				if self.beacons[mac]["indigoId"] ==0:
					self.beacons[mac]["ignore"] = -1
				self.newIgnoreMAC += 1
		else:
			self.newIgnoreMAC += 1
			self.beacons[mac] = copy.deepcopy(_GlobalConst_emptyBeacon)
			self.beacons[mac]["ignore"] = 0
			self.beacons[mac]["created"] = datetime.datetime.now().strftime(_defaultDateStampFormat)

		self.indiLOG.log(10,"setting {} indigoId: {} to un-ignore -mode:{}".format(mac, self.beacons[mac]["indigoId"], self.beacons[mac]["ignore"]) )
		if self.beacons[mac]["indigoId"] ==0:
			self.createNewiBeaconDeviceFromBeacons(mac)

		self.makeBeacons_parameterFile()
		for piU in _rpiBeaconList:
			self.setONErPiV(piU, "piUpToDate", ["updateParamsFTP"], resetQueue=True)

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
				props		    = copy.deepcopy(_GlobalConst_emptyBeaconProps_)
				)
			self.beacons[mac]["indigoId"] = dev.id
			dev = indigo.devices[dev.id]

		except Exception as e:
				if "{}".format(e).find("timeout waiting") > -1:
					self.exceptionHandler(40, e)



####-------------------------------------------------------------------------####
	def buttonConfirmMACDeleteCALLBACK(self, valuesDict=None, typeId="", devId=0):
		mac = valuesDict["ignoreMAC"]
		if mac in self.beacons:
			for piU in _rpiBeaconList:
				self.setONErPiV(piU, "piUpToDate", ["updateParamsFTP"], resetQueue=True)
			del self.beacons[mac]
		self.fixConfig(checkOnly = ["all", "rpi"],fromPGM="buttonConfirmMACDeleteCALLBACK")
		return valuesDict

####-------------------------------------------------------------------------####
	def buttonConfirmMACDeleteALLCALLBACK(self, valuesDict=None, typeId="", devId=0):

		### this is very bad !!!
		#self.beacons = {}

		self.fixConfig(checkOnly = ["all", "rpi"],fromPGM="buttonConfirmMACDeleteALLCALLBACK")
		for piU in _rpiBeaconList:
			self.setONErPiV(piU, "piUpToDate", ["updateParamsFTP"], resetQueue=True)
		try:
			subprocess.call("rm '"+ self.indigoPreferencesPluginDir + "rejected/reject-1'", shell=True )
			subprocess.call("cp '"+ self.indigoPreferencesPluginDir + "rejected/rejects' '"+ self.indigoPreferencesPluginDir + "rejected/reject-1'" , shell=True)
			subprocess.call("rm '"+ self.indigoPreferencesPluginDir + "rejected/rejects*'" , shell=True)
		except: pass
		return valuesDict

####-------------------------------------------------------------------------####

### not used
	def buttonConfirmMACnonactiveCALLBACK(self, valuesDict=None, typeId="", devId=0):
		try:
			ll0 = len(self.beacons)
			for beacon in copy.deepcopy(self.beacons):
				if self.beacons[beacon]["indigoId"] != 0:		continue
				if int(self.beacons[beacon]["ignore"]) == 0:	continue
				del self.beacons[beacon]

			self.fixConfig(checkOnly = ["all", "rpi"],fromPGM="buttonConfirmMACnonactiveCALLBACK")
			self.indiLOG.log(10,"from initially {} beacons in internal list,  {} ignored/inactive were removed".format(ll0, ll0-len(self.beacons)) )
		except Exception as e:
			self.exceptionHandler(40, e)
		return

####-------------------------------------------------------------------------####
	def buttonConfirmMACDeleteOLDHISTORYCALLBACK(self, valuesDict=None, typeId="", devId=0):
		try:
			delB = []
			ll0 = len(self.beacons)
			for beacon in copy.deepcopy(self.beacons):
				#self.indiLOG.log(10,"beacon= {} testing  , indigoID:{}".format(beacon, self.beacons[beacon]["indigoId"]) )
				if self.beacons[beacon]["indigoId"] != 0:
					try:
						dd= indigo.devices[self.beacons[beacon]["indigoId"]]
						continue
					except Exception as e:
						if "{}".format(e).find("timeout waiting") >-1: continue
						self.exceptionHandler(40, e)

				#self.indiLOG.log(10,"beacon= {} selected  (deleted/ignored) history .. can be used again -- 1".format(beacon) )
				delB.append(beacon)

			for beacon in delB:
				self.indiLOG.log(10,"beacon= {} removing from (deleted/ignored) history .. can be used again".format(beacon) )
				del self.beacons[beacon]
			if len(delB) > 0:
				self.writeJson(self.beacons, fName=self.indigoPreferencesPluginDir + "beacons", fmtOn=self.beaconsFileSort)


			try:
				subprocess.call("rm '{}rejected/rejects*'".format(self.indigoPreferencesPluginDir), shell=True )
				self.indiLOG.log(10,"old rejected/rejects files removed".format(self.indigoPreferencesPluginDir))
			except: pass


			self.fixConfig(checkOnly = ["all", "rpi"],fromPGM="buttonConfirmMACDeleteOLDHISTORYCALLBACK")
			ll2 = len(self.beacons)
			self.indiLOG.log(10,"from initially good {} beacons # of beacons removed from BEACONlist: {}".format(ll0, ll0-ll2) )
			self.setALLrPiV("piUpToDate", ["updateParamsFTP"])
		except Exception as e:
			self.exceptionHandler(40, e)
		valuesDict["MSG"] = "delete history initiated"
		return valuesDict

####-------------------------------------------------------------------------####
	def buttonSetAllExistingDevicesToActiveCALLBACK(self, valuesDict=None, typeId="", devId=0):
		try:
			for beacon in copy.deepcopy(self.beacons):
				if self.beacons[beacon]["indigoId"] != 0:
					self.beacons[beacon]["ignore"] = 0
					try:
						dev = indigo.devices[int(self.beacons[beacon]["indigoId"])]
						props = dev.pluginProps
						props["ignore"] = "0"
						props["enabled"] = True

						dev.replacePluginPropsOnServer(props)
					except:
						pass
			self.indiLOG.log(10,"set all existing iBeacon devices to active")
		except Exception as e:
			self.exceptionHandler(40, e)

		return valuesDict
####-------------------------------------------------------------------------####
	def buttonSetAllExistingDevicesToOFFCALLBACK(self, valuesDict=None, typeId="", devId=0):
		try:
			for beacon in copy.deepcopy(self.beacons):
				if self.beacons[beacon]["indigoId"] != 0:
					self.beacons[beacon]["ignore"] = 1
					try:
						dev = indigo.devices[int(self.beacons[beacon]["indigoId"])]
						props = dev.pluginProps
						props["ignore"] = "1"
						props["enabled"] = False

						dev.replacePluginPropsOnServer(props)
					except:
						pass
			self.indiLOG.log(10,"set all existing iBeacon devices to in active")
		except Exception as e:
			self.exceptionHandler(40, e)

		return valuesDict
####-------------------------------------------------------------------------####
	def buttonSetAllbeaconsTonoFastDownCALLBACK(self, valuesDict=None, typeId="", devId=0):
		try:
			for dev in indigo.devices.iter("props.isBeaconDevice"):
				try:
					props = dev.pluginProps
					props["fastDown"] = "0"

					dev.replacePluginPropsOnServer(props)
				except:
					pass
			self.indiLOG.log(10,"set all existing iBeacon devices to no fastDown")
			self.fixConfig(checkOnly = ["all", "rpi"],fromPGM="buttonSetAllbeaconsTonoFastDownCALLBACK")
			self.setALLrPiV("piUpToDate", ["updateParamsFTP"])
			valuesDict["MSG"] = "all beacon set to no Fast Down"
		except Exception as e:
			self.exceptionHandler(40, e)
		return valuesDict
###-------------------------------------------------------------------------####
	def buttonSetAllbeaconsTonoSignalDeltaCALLBACK(self, valuesDict=None, typeId="", devId=0):
		try:
			for dev in indigo.devices.iter("props.isBeaconDevice"):
				try:
					props = dev.pluginProps
					props["signalDelta"] = "999"

					dev.replacePluginPropsOnServer(props)
				except:
					pass
			self.indiLOG.log(10,"set all existing iBeacon devices to no Signal Delta")
			self.fixConfig(checkOnly = ["all", "rpi"],fromPGM="buttonSetAllbeaconsTonoSignalDeltaCALLBACK")
			self.setALLrPiV("piUpToDate", ["updateParamsFTP"])
			valuesDict["MSG"] = "all beacon set to no Signal Delta"
		except Exception as e:
			self.exceptionHandler(40, e)
		return valuesDict
###-------------------------------------------------------------------------####
	def buttonSetAllbeaconsTonominSignalOffCALLBACK(self, valuesDict=None, typeId="", devId=0):
		try:
			for dev in indigo.devices.iter("props.isBeaconDevice"):
				try:
					props = dev.pluginProps
					props["minSignalOff"] = "-999"
					dev.replacePluginPropsOnServer(props)
				except:
					pass
			self.indiLOG.log(10,"set all existing iBeacon devices to no Signal min off")
			self.fixConfig(checkOnly = ["all", "rpi"],fromPGM="buttonSetAllbeaconsTonominSignalOffCALLBACK")
			self.setALLrPiV("piUpToDate", ["updateParamsFTP"])
			valuesDict["MSG"] = "all beacon set to no Signal min off "
		except Exception as e:
			self.exceptionHandler(40, e)
		return valuesDict
###-------------------------------------------------------------------------####
	def buttonSetAllbeaconsTonominSignalOnCALLBACK(self, valuesDict=None, typeId="", devId=0):
		try:
			for dev in indigo.devices.iter("props.isBeaconDevice"):
				try:
					props = dev.pluginProps
					props["minSignalOn"] = _GlobalConst_emptyBeaconProps["minSignalOn"]
					dev.replacePluginPropsOnServer(props)
				except:
					pass
			self.indiLOG.log(10,"set all existing iBeacon devices to no fastDown")
			self.fixConfig(checkOnly = ["all", "rpi"],fromPGM="buttonSetAllbeaconsTonominSignalOnCALLBACK")
			self.setALLrPiV("piUpToDate", ["updateParamsFTP"])
			valuesDict["MSG"] = "all beacon set to no Signal min ON"
		except Exception as e:
			self.exceptionHandler(40, e)
		return valuesDict


####-------------------------------------------------------------------------####
	def confirmdeviceIDINPUTBUTTONmenu(self, valuesDict=None, typeId="", devId=""):
		try:
			devId = int(valuesDict["inputDev"])
			dev = indigo.devices[devId]
			props = dev.pluginProps
			for ii in range(30):
				valuesDict["i{}".format(ii)] = False
			if "deviceDefs" in props:
				gpioList = json.loads(props["deviceDefs"])
				for ii in range(30):
					if ii < len(gpioList) and "gpio" in gpioList[ii]:
						valuesDict["i{}".format(ii)] = True
			elif "gpio" in props:
				valuesDict["i" + props["gpio"]] = True
			else:
				for ii in range(10):
					if "INPUTdevId"+str(ii) in props and len(props["INPUTdevId"+str(ii)]) >3:
						valuesDict["i"+str(ii)] = True
		except Exception as e:
			self.exceptionHandler(40, e)
		return valuesDict

####-------------------------------------------------------------------------####
	def resetGPIOCountCALLBACKmenu(self, valuesDict=None, typeId="", devId=0):
		try:
			try:
				dev = indigo.devices[int(valuesDict["inputDev"])]
			except:
				try:
					dev = indigo.devices[valuesDict["inputDev"]]
				except:
					self.indiLOG.log(30,"ERROR:  Reset counter of GPIO pin on rPi; dev:{}  not defined".format(valuesDict["inputDev"]))
					return


			devId=dev.id
			props = dev.pluginProps
			if "displayS" in props:
				whichKeysToDisplay = props["displayS"]
			else:
				whichKeysToDisplay = ""
			piU = props["piServerNumber"]
			resetGPIOCount = []
			theType= dev.deviceTypeId.split("-")[0]
			if "deviceDefs" in props:
				listGPIO= json.loads(props["deviceDefs"])
				if False and "GPIOpins" in valuesDict:
					for pin in valuesDict["GPIOpins"]:
						for items in listGPIO:
							if "gpio" not in items: continue
							if pin == items["gpio"]:
								resetGPIOCount.append(pin)

				else:
					for ii in range(len(listGPIO)):
						if "INPUT_{}".format(ii) in valuesDict and valuesDict["INPUT_{}".format(ii)]:
							if "gpio" in listGPIO[ii]:
								resetGPIOCount.append(listGPIO[ii]["gpio"])
								if theType in ["INPUTcoincidence","INPUTpulse"]:
									self.updatePULSE(dev, {"count":-1}, whichKeysToDisplay)
								else:
									dev.updateStateOnServer("INPUT_"+str(ii), 0)


			elif "gpio" in props:
				gpio = props["gpio"]
				if valuesDict["INPUT_" +gpio]:
					resetGPIOCount.append(gpio)
					if theType in ["INPUTcoincidence","INPUTpulse"]:
						self.updatePULSE(dev, {"count":-1}, whichKeysToDisplay)

				for ii in range(10):
					if valuesDict["INPUT_"+str(ii)]:
						if theType == "INPUTcoincidence":
							theType = "INPUTpulse"
							if "INPUTdevId"+str(ii) in props and len(props["INPUTdevId"+str(ii)])>3:
									resetGPIOCount.append(devId)
									self.updatePULSE(dev, {"count":-1}, whichKeysToDisplay)
									break

			if resetGPIOCount == []: return valuesDict


			toSend = [{"device": typeId, "command":"file", "fileName":"/home/pi/pibeacon/temp/"+theType+".reset", "fileContents":resetGPIOCount}]
			self.sendtoRPI(self.RPI[piU]["ipNumberPi"], piU, toSend, calledFrom="resetGPIOCountCALLBACKmenu")

		except Exception as e:
			self.exceptionHandler(40, e)
		return valuesDict

####-------------------------------------------------------------------------####
	def resetGPIOCountCALLBACKaction(self, action1=None, typeId="", devId=0):
		self.resetGPIOCountCALLBACKmenu(action1.props)
		return




####-------------------------------------------------------------------------####
	def filterChannels(self, filter="", valuesDict=None, typeId="", devId=""):
		#indigo.server.log("filterChannels {}".format(valuesDict))
		xList = []
		for ii in range(41):
			xList.append(("{}".format(41-ii), "Channel-{}".format(41-ii)))
		xList.append(("0", "no pick"))
		return xList


####-------------------------------------------------------------------------####
	def confirmdeviceRPIanyPropBUTTON(self, valuesDict, typeId="", devId=""):
		try:
			self.anyProperTydeviceNameOrId = valuesDict["deviceNameOrId"]
		except:
			self.indiLOG.log(40,self.anyProperTydeviceNameOrId +" not in defined")
		return valuesDict

####-------------------------------------------------------------------------####
	def filterAnyPropertyNameACTION(self, filter="", valuesDict=None, typeId="", devId=""):
		xList = []
		if self.anyProperTydeviceNameOrId ==0:
			return xList
		try: id = int(self.anyProperTydeviceNameOrId)
		except: id =self.anyProperTydeviceNameOrId
		try: dev = indigo.devices[id]
		except:
			self.indiLOG.log(40, "{}".format(self.anyProperTydeviceNameOrId) +" not in defined")
			return xList
		props = dev.pluginProps
		for nn in props:
			xList.append([nn,nn])
		return xList

####-------------------------------------------------------------------------####
	def setAnyPropertyCALLBACKaction(self, action1=None, typeId="", devId=0):
		try:
			valuesDict = action1.props

			try: id = int(valuesDict["deviceNameOrId"])
			except: id = valuesDict["deviceNameOrId"]
			try: dev = indigo.devices[id]
			except:
				self.indiLOG.log(40,valuesDict["deviceNameOrId"] +" not in indigodevices")
				return

			if "propertyName" not in valuesDict:
				self.indiLOG.log(40,"u propertyName not in valuesDict")
				return
			props = dev.pluginProps
			propertyName =valuesDict["propertyName"]
			if propertyName not in props:
				self.indiLOG.log(40,propertyName+" not in pluginProps")
				return
			if "propertyContents" not in valuesDict:
				self.indiLOG.log(40,"propertyContents not in valuesDict")
				return
			self.indiLOG.log(10,"updating {}     {}  {}".format(dev.name, propertyName, props[propertyName]))

			props[propertyName] = self.convertVariableOrDeviceStateToText(valuesDict["propertyContents"])

			
			dev.replacePluginPropsOnServer(props)
		except Exception as e:
			self.exceptionHandler(40, e)
		return

####-------------------------------------------------------------------------####
	def getAnyPropertyCALLBACKaction(self, action1=None, typeId="", devId=0):
		try:
			retJ = ""
			valuesDict = action1.props
			##self.indiLOG.log(10," property request:{}".format(valuesDict) )
			try:
				var = indigo.variables["piBeacon_property"]
			except:
				indigo.variable.create("piBeacon_property", "", self.iBeaconFolderVariablesName)

			try: id = int(valuesDict["deviceNameOrId"])
			except: id = valuesDict["deviceNameOrId"]
			try: dev = indigo.devices[id]
			except:
				self.indiLOG.log(40,valuesDict["deviceNameOrId"] +" not in indigodevices")
				indigo.variable.updateValue("piBeacon_property","{} not in indigodevices".format(valuesDict["deviceNameOrId"]))
				return {"propertyName":"ERROR: " +valuesDict["deviceNameOrId"] +" not in indigodevices"}

			if "propertyName" not in valuesDict:
				self.indiLOG.log(40,"propertyName not in valuesDict")
				indigo.variable.updateValue("piBeacon_property", "propertyNamenot in valuesDict")
				return {"propertyName":"ERROR:  propertyName  not in valuesDict"}
			props = dev.pluginProps
			propertyName =valuesDict["propertyName"]
			if propertyName not in props:
				self.indiLOG.log(40,propertyName+" not in pluginProps")
				indigo.variable.updateValue("piBeacon_property",)
				return {"propertyName":"ERROR: {} not in pluginProps".format(propertyName)}
			propertyContents = props[propertyName]


			indigo.variable.updateValue("piBeacon_property", propertyContents)
			retJ = json.dumps({propertyName:"{}".format(propertyContents)}) #
		except Exception as e:
			self.exceptionHandler(40, e)

		return retJ


####-------------------------------------------------------------------------####
	def dynamicCallbackSetSwitchbotactionsFields(self, valuesDict, x="",y=""):

		errorsDict = indigo.Dict()

		try:
			valuesDict['piVisible']						= False
			valuesDict['sensorVisible']					= False
			valuesDict['sensorTriggerValueVisible']		= False
			valuesDict['stopVisible']					= False
			valuesDict['switchBotModeVisible']			= False
			valuesDict['repeatVisible']					= False
			valuesDict['repeatDelayVisible']			= False
			valuesDict['pulsesVisible']					= False
			valuesDict['pulseLengthOnVisible']			= False
			valuesDict['pulseLengthOffVisible']			= False
			valuesDict['pulseDelayVisible']				= False
			valuesDict['execRPItoRPIVisible']			= False
			valuesDict['outputDevVisible']				= False
			valuesDict['MSGVisible']					= False
			valuesDict['infoLabelDIRECTVisible']		= False
			valuesDict['infoLabelActionVisible']		= False
			valuesDict['infoLabelSAVEVisible']			= ""
			valuesDict['stopActionsForSecondsVisible']	= False

			if valuesDict['selectActionType']		== "deleteRPIaction":
				valuesDict['sensorVisible']				= True
				valuesDict['execRPItoRPIVisible']		= True
				valuesDict['infoLabelSAVEVisible']		= True
				valuesDict['infoLabelDIRECTVisible']	= True

			elif valuesDict['selectActionType']		== "addRPIAction":
				valuesDict['piVisible']					= True
				valuesDict['sensorVisible']				= True
				valuesDict['sensorTriggerValueVisible']	= True
				valuesDict['outputDevVisible']			= True
				valuesDict['stopVisible']				= True
				valuesDict['execRPItoRPIVisible']		= True
				valuesDict['infoLabelSAVEVisible']		= True
				valuesDict['infoLabelActionVisible']	= True
				valuesDict['switchBotModeVisible']		= True
				valuesDict['repeatVisible']				= True
				valuesDict['repeatDelayVisible']		= True
				valuesDict['pulsesVisible']				= True
				if valuesDict['switchBotMode'] == "interactive":
					valuesDict['pulseLengthOnVisible']	= True
					valuesDict['pulseLengthOffVisible']	= True
					valuesDict['pulseDelayVisible']		= True

			else:
				valuesDict['piVisible']					= True
				valuesDict['infoLabelActionVisible']	= True
				valuesDict['outputDevVisible']			= True
				valuesDict['stopVisible']				= True
				if  valuesDict['stop'] == "0": # = do not stop previous action
					valuesDict['switchBotModeVisible']	= True
					valuesDict['repeatVisible']			= True
					valuesDict['repeatDelayVisible']	= True
					valuesDict['pulsesVisible']			= True

					if valuesDict['switchBotMode'] == "interactive":
						valuesDict['pulseLengthOnVisible']	= True
						valuesDict['pulseLengthOffVisible']	= True
						valuesDict['pulseDelayVisible']		= True
				else:
					valuesDict['stopActionsForSecondsVisible'] = True


		except Exception as e:
			self.exceptionHandler(40, e)
		return (valuesDict, errorsDict)

####-------------------------------------------------------------------------####
	def setupRPItoRPIactionCALLBACKaction(self,valuesDict=None, typeId="", devId=0):
		self.setupRPItoRPIactionCALLBACKmenu(valuesDict)


####-------------------------------------------------------------------------####
	def setupRPItoRPIactionCALLBACKmenu(self, valuesDict=None, typeId="", devId=0):
		try:

			#self.indiLOG.log(20,"valuesDict:{}".format(valuesDict))

			if valuesDict.get("selectActionType","") ==  "regular": return 

			try: sensDev = indigo.devices[int(valuesDict.get("sensor","x"))]
			except: return 

			if self.isValidMAC( sensDev.states.get("mac","-1")): 			macSens = sensDev.states["mac"]
			elif self.isValidMAC( sensDev.pluginProps.get("address","-1")):	macSens = sensDev.pluginProps["address"]
			else: return 

			sensorPi			= valuesDict.get("sensorPi","")

			valuesDict["configurePi"] = sensorPi

			if valuesDict.get("selectActionType","") ==  "deleteRPIaction": 
				if macSens in self.fastBLEReaction:
					self.indiLOG.log(20,"deleting rpi-rpi action  macSens:{}, to pi:{}  fastBLEReaction:{}".format(macSens, sensorPi, self.fastBLEReaction[macSens]))
					del self.fastBLEReaction[macSens] 
					self.savefastBLEReaction()
					self.makeBeacons_parameterFile()
					self.execButtonConfig(valuesDict, level="0,", action=["updateParamsFTP"], Text="send Config Files to pi s ")
				return valuesDict
 

			try: outputDev = indigo.devices[int(valuesDict.get("outputDev","x"))]
			except: return 


			macOfSwitchbot = outputDev.pluginProps.get("mac","")
			if not self.isValidMAC(macOfSwitchbot): return 


			piU = outputDev.pluginProps.get("piServerNumber")
			int(piU)
			IPOfSwitchbotRPI 	= self.RPI[piU]["ipNumberPi"]
			IdOfSwitchbotRPI 	= self.RPI[piU]["userIdPi"]
			pwdOfSwitchbotRPI	= self.RPI[piU]["passwordPi"]

			sensorTriggerValue = valuesDict.get("sensorTriggerValue","on")


			sensorTriggerValue	= valuesDict.get("sensorTriggerValue","on")
			repeat 				= valuesDict.get("repeat","0")
			repeatDelay 		= valuesDict.get("repeatDelay","0")
			pulses 				= valuesDict.get("pulses","on")
			pulseLengthOn 		= valuesDict.get("pulseLengthOn","0")
			pulseLengthOff	 	= valuesDict.get("pulseLengthOff","2.0")
			pulseDelay 			= valuesDict.get("pulseDelay","0.0")
			switchBotMode 		= valuesDict.get("switchBotMode","batch")
			cmdMode 			= "onOff" 
			if pulses not in ["off","on"]: 
				switchBotMode 			= "interactive"
				cmdMode 				= "onOff" 
				onOff 					= "1"
			elif pulses == "on":  onOff = "1"
			elif pulses == "off": onOff = "0"
			else:				  onOff = "1"
			
			cmd = {"mac":macOfSwitchbot,"cmd":cmdMode,"onOff":onOff,"pulses":pulses, "pulseLengthOn":pulseLengthOn, "pulseLengthOff":pulseLengthOff, "pulseDelay":pulseDelay, "repeat":repeat, "repeatDelay":repeatDelay, "outputDev":  outputDev.id, "mode":switchBotMode,"sensorTriggerValue":sensorTriggerValue}

			self.fastBLEReaction[macSens] = {"cmd":cmd,"piU":piU, "indigoIdOfSwitchbot":outputDev.id, "macOfSwitchbot":macOfSwitchbot,"IPOfSwitchbotRPI":IPOfSwitchbotRPI,"IdOfSwitchbotRPI":IdOfSwitchbotRPI,"pwdOfSwitchbotRPI":pwdOfSwitchbotRPI}
			self.savefastBLEReaction()

			self.indiLOG.log(20,"setting rpi-rpi action  macSens:{}, to pi:{}  fastBLEReaction:{}".format(macSens, sensorPi, self.fastBLEReaction[macSens]))

			self.makeBeacons_parameterFile()
			self.execButtonConfig(valuesDict, level="0,", action=["updateParamsFTP"], Text="send switchbot command to pi# ")


		except Exception as e:
			self.exceptionHandler(40, e)

		return valuesDict



####-------------------------------------------------------------------------####
	def setTEA5767CALLBACKaction(self, action1=None, typeId="", devId=0):
		valuesDict = action1.props
		self.setTEA5767CALLBACKmenu(valuesDict)


####-------------------------------------------------------------------------####
	def setTEA5767CALLBACKmenu(self, valuesDict=None, typeId="", devId=0):
		try:
			vd=valuesDict
			try:
				devId = int(vd["outputDev"])
				dev = indigo.devices[devId]
			except:
				try:
					dev = indigo.devices[vd["outputDev"]]
					devId = dev.id
				except:
					self.indiLOG.log(40,"error outputDev not set")
					vd["MSG"] = "error outputDev not set"
					return
###			   #self.indiLOG.log(10, "{}".format(vd))

			typeId			  = "setTEA5767"
			props			  = dev.pluginProps
			piServerNumber	  = props["address"].split("-")[1]
			ip				  = self.RPI[piServerNumber]["ipNumberPi"]
			if self.decideMyLog("OutputDevice"): self.indiLOG.log(5,"pi: {}".format(ip)+"  {}".format(vd))

			cmds={}
			if "command" in vd:
				command = vd["command"]
			else:
				command = vd

			updateProps = False
			if "frequency" in command and command["frequency"] !="":
				cmds["frequency"] = self.convertVariableOrDeviceStateToText(command["frequency"])
				props["defFreq"]  = cmds["frequency"]
				updateProps = True
			if "mute" in command and command["mute"] !="":
				cmds["mute"] = self.convertVariableOrDeviceStateToText(command["mute"])
				props["mute"]	= cmds["mute"]
				updateProps = True
			if "mono" in command and command["mono"] !="":
				cmds["mono"] = self.convertVariableOrDeviceStateToText(command["mono"])
				props["mono"]	= cmds["mono"]
				updateProps = True
			if "restart" in command and command["restart"] =="1":
				cmds["restart"] = "1"
			if "scan" in command and command["scan"] !="":
				cmds["scan"] = self.convertVariableOrDeviceStateToText(command["scan"])
				if "minSignal" in command and command["minSignal"] !="":
					cmds["minSignal"] = self.convertVariableOrDeviceStateToText(command["minSignal"])
			if updateProps:
				
				dev.replacePluginPropsOnServer(props)
				dev = indigo.devices[devId]
				self.addToStatesUpdateDict(devId,"status"   ,"f= {}".format(props["defFreq"]) + "; mute= {}".format(props["mute"]))
				self.addToStatesUpdateDict(devId,"frequency",props["defFreq"],decimalPlaces=1)
				self.addToStatesUpdateDict(devId,"mute"     ,props["mute"])
				self.executeUpdateStatesDict(onlyDevID= "{}".format(devId), calledFrom="setTEA5767CALLBACKmenu")
				if props["mute"] =="1":
						dev.updateStateImageOnServer(indigo.kStateImageSel.SensorOff)
				else:
						dev.updateStateImageOnServer(indigo.kStateImageSel.SensorOn)

			startAtDateTime = 0
			if "startAtDateTime" in valuesDict:
				startAtDateTime = self.setDelay(startAtDateTimeIN=self.convertVariableOrDeviceStateToText(vd["startAtDateTime"]))

			toSend = [{"device": typeId, "startAtDateTime":startAtDateTime,"command":"file", "fileName":"/home/pi/pibeacon/setTEA5767.inp", "fileContents":cmds}]

			try:
				line = "\n##=======use this as a python script in an action group action :=====\n"
				line +="plug = indigo.server.getPlugin(\"com.karlwachs.piBeacon\")"
				line +="\nplug.executeAction(\"setTEA5767\" , props ={"
				line +="\n	 \"outputDev\":\"{}".format(vd["outputDev"])+"\""
				line +="\n	,\"device\":\"{}".format(typeId)+"\""
				line +="\n	,\"startAtDateTime\":\"{}".format(startAtDateTime)+"\""
				for cc in cmds:
					line +="\n	,\""+cc+"\":\"{}".format(cmds[cc])+"\""
				line +="})\n"
				line+= "##=======	end	   =====\n"
				if self.decideMyLog("OutputDevice"): self.indiLOG.log(5,"\n"+line+"\n")
			except:
				if self.decideMyLog("OutputDevice"): self.indiLOG.log(5,"use this as a python script command:\n"+"plug = indigo.server.getPlugin(\"com.karlwachs.piBeacon\")\nplug.executeAction(\"setTEA5767\" , props =("+
				  json.dumps({"outputDev":vd["outputDev"],"device": typeId})+" error")
			self.sendtoRPI(ip, piServerNumber, toSend, calledFrom="setTEA5767CALLBACKmenu")
			vd["MSG"] = " ok"
		except Exception as e:
			self.exceptionHandler(40, e)


####-------------------------------------------------------------------------####
	def confirmduplicateBUTTONmenu(self, valuesDict=None, typeId="", devId="x"):
		try:
			vd = valuesDict

			## first save
			cd = self.savedisplayPropsWindowCALLBACKbutton(valuesDict=vd)

			## copy from to
			dublicateFrom = vd["dublicateFrom"]
			dublicateTo	  = vd["dublicateTo"]
			if dublicateFrom == dublicateTo: return vd
			# copy the props shown in the action
			for xxx in ["type", "text", "delayStart", "offONTime", "reset", "font", "width", "fill", "position", "display"]:
				vd[xxx+dublicateTo] = vd[xxx+dublicateFrom]

			## show new ones on screen
			vd = self.setdisplayPropsWindowCALLBACKbutton(valuesDict=vd)

		except Exception as e:
			self.exceptionHandler(40, e)
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
				fromProp =	yy[0]+ "{}".format(int(yy[1])+fromWindow)
				if fromProp in vd:
					vd[xx] = vd[fromProp]
		vd["windowStart"] = vd["fromWindow"]+" .. to {}".format(int(vd["fromWindow"])+10)
		return vd

####-------------------------------------------------------------------------####
	def savedisplayPropsWindowCALLBACKbutton(self, valuesDict=None, typeId="", devId=0):
		vd = valuesDict
		try:	fromWindow = int(vd["fromWindow"])
		except: return vd
		for xx in vd:
			if "xYAYx" in xx:
				yy = xx.split("xYAYx")
				vd[ yy[0] + "{}".format(int(yy[1])+fromWindow) ] = vd[xx]
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
			###if self.decideMyLog("OutputDevice"): self.indiLOG.log(5,"setdisplayCALLBACKmenu: {}".format(vd))
			try:
				dev = indigo.devices[int(vd["outputDev"])]
			except:
				try:
					dev = indigo.devices[vd["outputDev"]]
				except:
					self.indiLOG.log(10,"setdisplayCALLBACKmenu error outputDev not set")
					vd["MSG"] = "error outputDev not set"
					return
###			   #self.indiLOG.log(10, "{}".format(vd))

			props = dev.pluginProps
			piServerNumber	  = props["address"].split("-")[1]
			typeId			  = "OUTPUT-Display"
			if "command" in vd:
				cmds = vd["command"]
				for iii in range(200):
					if "%%v:" not in cmds and "%%d:" not in cmds and "%%eval:" not in cmds and "%%FtoC:" not in cmds: break
					cmds= self.convertVariableOrDeviceStateToText(self.convertVariableOrDeviceStateToText(cmds))

				if cmds .find("[{'") ==0: #  this will not work for json  replace ' with " as text delimiters and save any "
					cmds = cmds.replace("'", "aa123xxx123xxxaa").replace('"',"'").replace("aa123xxx123xxxaa",'"')

				try:
					cmds = json.loads(cmds)
				except Exception as e:
					if "{}".format(e) != "None":
						self.exceptionHandler(40, e)
					self.indiLOG.log(40,"setdisplayCALLBACKmenuv error in json conversion for {}".format(cmds))
					vd["MSG"] = "error in json conversion"
					return
				if self.decideMyLog("OutputDevice"): self.indiLOG.log(5," after json conversion:{}".format(cmds)+"\n")

				delCMDS =[]
				for ii in range(len(cmds)):
					cType = cmds[ii]["type"]
					if cType == "0" or cType == "" or \
						cType not in ["text", "textWformat", "clock", "dateString", "analogClock", "digitalClock", "date", "NOP", "line", "point", "ellipse", "vBar", "hBar", "vBarwBox", "hBarwBox", "labelsForPreviousObject", "rectangle", "triangle", "hist", "exec", "image", "dot"]:
						delCMDS.append(ii)
						continue
					if "position" in cmds[ii]:
						try:
							xx					   = json.loads(cmds[ii]["position"])
							cmds[ii]["position"]  = xx
						except:
							try:
								xx = json.loads(json.dumps (cmds[ii]["position"]))
								# is ok was already	 loaded
							except:
								self.indiLOG.log(40," error in input: position= {}".format(cmds[ii]["position"]) )
								valuesDict["MSG"] = "error in position"
					if cType =="textWformat" and "text" in cmds[ii] and "FORMAT" in cmds[ii]["text"]:
						try:
							xx = cmds[ii]["text"].split("FORMAT")
							cmds[ii]["text"] = xx[1]%(float(xx[0]))
						except:
							self.indiLOG.log(40,"setdisplayCALLBACK error in formatting:{}".format(cmds[ii]["text"]))
					if cType not in["text", "textWformat", "dateString", "image"]:
						if "text" in cmds[ii]: del cmds[ii]["text"]
				if len(delCMDS) >0:
					for ii in delCMDS[::-1]:
						del cmds[ii]

			else:
				###if self.decideMyLog("OutputDevice"): self.indiLOG.log(5,"input:{}".format(vd))
				cmds =[]
				nn =-1
				for ii in range(100):
					iiS = "{}".format(ii)
					if "type"+iiS not in vd: continue
					cType = vd["type"+iiS]
					if cType == "0":				  continue
					if cType == "":					  continue
					if cType in ["text", "textWformat", "clock", "dateString", "digitalClock", "analogClock", "date", "NOP", "line", "point", "ellipse", "vBar", "hBar", "vBarwBox", "hBarwBox", "labelsForPreviousObject", "rectangle", "triangle", "hist", "exec", "image", "dot"]:
						cmds.append({})
						nn+=1
						cmds[nn]["type"]				  = cType
						if cType =="analogClock":
							cmds[nn]["hh"]	  = {}
							cmds[nn]["mm"]	  = {}
							cmds[nn]["ss"]	  = {}
							cmds[nn]["ticks"] = {}
							cmds[nn]["box"]	  = {}

						if "text"+iiS in vd:
							cmds[nn]["text"]			  = self.convertVariableOrDeviceStateToText(vd["text"+iiS])
							if cType =="textWformat" and "%%FORMAT:" in cmds[nn]["text"]:
								try:
									xx = cmds[nn]["text"].split("%%FORMAT:")
									cmds[nn]["text"] = xx[1]%(float(xx[0]))
								except:
									self.indiLOG.log(40,"setdisplayCALLBACK error in formatting: {}".format(cmds[nn]["text"]))

						if "font"+iiS in vd:
							cmds[nn]["font"]			  = self.convertVariableOrDeviceStateToText(vd["font"+iiS])

						if "delayStart"+iiS in vd:
							cmds[nn]["delayStart"]		  = self.convertVariableOrDeviceStateToText(vd["delayStart"+iiS])



						cmds[nn]["fill"]	 = self.setupListDisplay(vd, "fill"+iiS,  lenItem=3,default="")
						cmds[nn]["reset"]	 = self.setupListDisplay(vd, "reset"+iiS, lenItem=3,default="")

						if "width"+iiS in vd:
							cmds[nn]["width"]			  = self.setupListDisplay(vd, "width"+iiS, lenItem=2,default="")

						if "format"+iiS in vd:
							cmds[nn]["format"]			   = self.convertVariableOrDeviceStateToText(vd["format"+iiS])

						if "radius"+iiS in vd:
							cmds[nn]["radius"]			  = self.setupListDisplay(vd, "radius"+iiS,lenItem=2,default="")

						if "fillhh"+iiS in vd:
							cmds[nn]["hh"]["fill"]	  = self.setupListDisplay(vd, "fillhh"+iiS, lenItem=3,default="")

						if "fillmm"+iiS in vd:
							cmds[nn]["mm"]["fill"]	  = self.setupListDisplay(vd, "fillmm"+iiS, lenItem=3,default="")

						if "fillss"+iiS in vd:
							cmds[nn]["ss"]["fill"]	  = self.setupListDisplay(vd, "fillss"+iiS, lenItem=3,default="")

						if "fillticks"+iiS in vd:
							cmds[nn]["ticks"]["fill"]	  = self.setupListDisplay(vd, "fillticks"+iiS, lenItem=3,default="")

						if "mode"+iiS in vd:
							cmds[nn]["mode"]			  = self.convertVariableOrDeviceStateToText(vd["mode"+iiS])

						if "box"+iiS in vd:
							cmds[nn]["box"]["on"]		  = self.convertVariableOrDeviceStateToText(vd["box"+iiS])

						if "fillBox"+iiS in vd:
							cmds[nn]["box"]["fill"]	  = self.addBrackets(self.convertVariableOrDeviceStateToText(vd["fillBox"+iiS]),cType=3)

						if "widthBox"+iiS in vd:
							cmds[nn]["box"]["width"]	  = self.convertVariableOrDeviceStateToText(vd["widthBox"+iiS])
						if "heightBox"+iiS in vd:
							cmds[nn]["box"]["height"]	   = self.convertVariableOrDeviceStateToText(vd["heightBox"+iiS])


						if "display"+iiS in vd:
							cmds[nn]["display"]		  = self.convertVariableOrDeviceStateToText(vd["display"+iiS])

						if "position"+iiS in vd:
							if cType == "labelsForPreviousObject":
								try: cmds[nn]["position"]	= json.loads(self.convertVariableOrDeviceStateToText(vd["position"+iiS]))
								except: pass
							else:
								cmds[nn]["position"]		= self.addBrackets(self.convertVariableOrDeviceStateToText(vd["position"+iiS]),cType=cType)

						if "offONTime"+iiS in vd:
							cmds[nn]["offONTime"]		  = self.addBrackets( self.convertVariableOrDeviceStateToText(vd["offONTime"+iiS]), cType=3, default=[0,999999999,0] )

						if cType not in["text", "textWformat", "dateString", "image", "labelsForPreviousObject"]:
							if "text" in cmds[nn]:	 del cmds[nn]["text"]
						if cType == "point":
							if "width" in cmds[nn]: del cmds[nn]["width"]


				#self.indiLOG.log(10,	"{}".format(vd))
			ip = self.RPI[piServerNumber]["ipNumberPi"]

			startAtDateTime = 0
			if "startAtDateTime" in valuesDict:
				startAtDateTime = self.setDelay(startAtDateTimeIN=self.convertVariableOrDeviceStateToText(vd["startAtDateTime"]))

			repeat				= 1
			resetInitial		= ""
			scrollxy			= ""
			scrollPages			= 1
			scrollDelay			= 0
			scrollDelayBetweenPages = 0
			intensity			= "100"
			showDateTime		= "0"
			restoreAfterBoot	= "0"
			xwindowSize 		= "0,0"
			xwindows			= "off"
			zoom 				= 1.0
			source 				= ""

			if "repeat" in vd:
				repeat = self.convertVariableOrDeviceStateToText(vd["repeat"])
			if "{}".format(repeat) == "": repeat = 1


			if "xwindows" in vd and vd["xwindows"].lower() == "on":
				if "xwindowSize" in vd:
					xwindows	= "ON"
					xwindowSize = self.convertVariableOrDeviceStateToText(vd["xwindowSize"])

			if "intensity" in vd:
				intensity = self.convertVariableOrDeviceStateToText(vd["intensity"])
			if "{}".format(intensity) == "": intensity = 100

			if "resetInitial" in vd:
				resetInitial = self.convertVariableOrDeviceStateToText(vd["resetInitial"])

			if "zoom" in vd:
				zoom = self.convertVariableOrDeviceStateToText(vd["zoom"])

			if "scrollxy" in vd:
				scrollxy		   = self.convertVariableOrDeviceStateToText(vd["scrollxy"])

			if "showDateTime" in vd:
				showDateTime		   = self.convertVariableOrDeviceStateToText(vd["showDateTime"])

			if "scrollPages" in vd:
				scrollPages		 = self.convertVariableOrDeviceStateToText(vd["scrollPages"])

			if "scrollDelay" in vd:
				scrollDelay		 = self.convertVariableOrDeviceStateToText(vd["scrollDelay"])

			if "scrollDelayBetweenPages" in vd:
				scrollDelayBetweenPages = self.convertVariableOrDeviceStateToText(vd["scrollDelayBetweenPages"])

			restoreAfterBoot = vd.get("restoreAfterBoot","0")
			if "{}".format(restoreAfterBoot) not in ["0","1"]: 
				if restoreAfterBoot in [True,"True","true"]: restoreAfterBoot = "1"
				if restoreAfterBoot in [False,"False","false"]: restoreAfterBoot = "0"

			if "source" in vd:
				source = vd["source"]

			try:
				line = "\n##=======use this as a python script in an action group action :=====\n"
				line +="plug = indigo.server.getPlugin(\"com.karlwachs.piBeacon\")"
				line +="\nplug.executeAction(\"Display\" ,	props ={"
				line +="\n     \"outputDev\":\"{}".format(vd["outputDev"])+"\""
				line +="\n    ,\"device\":\"{}".format(typeId)+"\""
				line +="\n    ,\"restoreAfterBoot\":\"{}".format(restoreAfterBoot)+"\""
				line +="\n    ,\"intensity\":\"{}".format(intensity)+"\""
				line +="\n    ,\"xwindows\":\""+(xwindows)+"\""
				line +="\n    ,\"xwindowSize\":\"{}".format(xwindowSize)+"\""
				line +="\n    ,\"zoom\":\"{}".format(zoom)+"\""
				line +="\n    ,\"repeat\":\"{}".format(repeat)+"\""
				line +="\n    ,\"resetInitial\":\"{}".format(resetInitial)+"\""
				line +="\n    ,\"scrollxy\":\"{}".format(scrollxy)+"\""
				line +="\n    ,\"showDateTime\":\"{}".format(showDateTime)+"\""
				line +="\n    ,\"startAtDateTime\":\"{}".format(startAtDateTime)+"\""
				line +="\n    ,\"scrollPages\":\"{}".format(scrollPages)+"\""
				line +="\n    ,\"scrollDelay\":\"{}".format(scrollDelay)+"\""
				line +="\n    ,\"source\":\"{}".format(source)+"\""
				line +="\n    ,\"scrollDelayBetweenPages\":\"{}".format(scrollDelayBetweenPages)+"\""
				line +="\n    ,\"command\":'['+\n     '"

				### this will create list of dicts, one per command, remove blank items, sort  ,..
				doList =["type", "position", "width", "fill", "font", "text", "offONTime", "display", "reset", "labelsForPreviousObject"] # sorted by this
				noFont =["NOP", "line", "point", "ellipse", "vBar", "hBar", "vBarwBox", "hBarwBox", "rectangle", "triangle", "hist", "exec", "image", "dot"]
				for cc in range(len(cmds)):
					delItem=[]
					if len(cmds[cc]) > 0:
						line += "{"
						for item in doList:
							if item in cmds[cc]:
								if cmds[cc][item] !="" and not ( item =="font" and cmds[cc]["type"] in noFont) :
									line +='"'+item+'":'+json.dumps(cmds[cc][item]).strip(" ")+", "
								else:# this is blank
									delItem.append(item)

						for item in cmds[cc]: # this is for the others not listed in the sort List
							if item in doList: continue
							if cmds[cc][item] != "":
								line += '"'+item+'":'+json.dumps(cmds[cc][item]).strip(" ")+", "
							else: # this is blank
								delItem.append(item)

						## remove blanks
						for item in delItem:
							del cmds[cc][item]
						# close line
						line  = line.strip(", ") + "}'+\n     ',"

				## finish cmd lines
				line  = line.strip("'+\n      ',")	+ "]'\n  })\n"
				## end of output
				line += "##=======   end  =====\n"

				if self.decideMyLog("OutputDevice"): self.indiLOG.log(5,"\n"+line+"\n")
				vd["MSG"] = " ok"

			except Exception as e:
				if "{}".format(e) != "None":
					self.exceptionHandler(40, e)
					vd["MSG"] = "error"
			jData = {"device": typeId,  "restoreAfterBoot": "0", "intensity":intensity, "zoom":zoom,"repeat":repeat,"resetInitial":resetInitial,"startAtDateTime":startAtDateTime,
				"scrollxy":scrollxy, "showDateTime":showDateTime,"scrollPages":scrollPages,"scrollDelay":scrollDelay,"source":source,"scrollDelayBetweenPages":scrollDelayBetweenPages,
				"command": cmds}
			if xwindows.lower() == "on" and xwindowSize !="0,0":
				jData["xwindows"] = xwindows
				jData["xwindowSize"] = xwindowSize
			self.sendtoRPI(ip, piServerNumber, [jData], calledFrom="setdisplayCALLBACKmenu")

		except Exception as e:
			self.exceptionHandler(40, e)
			self.indiLOG.log(40,"error display check {}".format(vd))
			valuesDict["MSG"] = "error in parameters"
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
		except Exception as e:
			self.exceptionHandler(40, e)
		return ret
####-------------------------------------------------------------------------####
	def addBrackets(self,pos,cType="",default=[]):
		try:
			test = "{}".format(pos).strip(",")

			if len(test) ==0: return default
			if cType == "point":
				return json.loads(test)


			if		type(cType) == type(2):	 nItems = cType
			elif	cType =="text":		 nItems = 2
			elif	cType =="line":		 nItems = 4
			elif	cType =="ellipse" :	 nItems = 4
			elif	cType =="dot" :		 nItems = 2
			elif	cType =="radius"  :	 nItems = 2
			elif	cType =="center"  :	 nItems = 2
			elif	cType =="vBar"	   :	 nItems = 3
			elif	cType =="hBar"	   :	 nItems = 3
			elif	cType =="vBarwBox":	 nItems = 3
			elif	cType =="hBarwBox":	 nItems = 3
			elif	cType =="rectangle":	 nItems = 4
			elif	cType =="triangle":	 nItems = 6
			elif	cType =="dateString":	 nItems = 2
			elif	cType =="analogClock":	 nItems = 2
			elif	cType =="digitalClock": nItems = 2
			elif	cType =="labelsForPreviousObject":	 nItems = 0
			else:							 nItems = -1

			if nItems == 0:
				return pos
			if len(test) >0 and test[0]	 =="[": test = test[1:]
			if len(test) >0 and test[-1] =="[": test = test[:-1]
			test = test.split(",")
			pp = []
			for t in test:
					try:	x = int(float(t))
					except: x = t
					pp.append(x)
			if nItems !=-1 and nItems != len(pp):
				self.indiLOG.log(10,"addBrackets error in input: pos= {}; wrong number of coordinates, should be: {}".format(pos, nItems) )

			return pp
		except Exception as e:
			self.exceptionHandler(40, e)
			self.indiLOG.log(40,"addBrackets error in input: cType:{};  default= {};  pos= {}".format(cType, default, pos) )
		return default



####-------------------------------------------------------------------------####
	def setneopixelCALLBACKaction(self, action1=None, typeId="", devId=0):
		valuesDict = action1.props
		return self.setneopixelCALLBACKmenu(valuesDict)["MSG"]

####-------------------------------------------------------------------------####
	def setneopixelCALLBACKmenu(self, valuesDict=None, typeId="", devId=0):
		try:
			vd=valuesDict
			vd["MSG"] = ""
			try:
				devId = int(vd["outputDev"])
				dev = indigo.devices[devId]
			except:
				try:
					dev = indigo.devices[vd["outputDev"]]
					devId = dev.id
				except:
					self.indiLOG.log(40,"error outputDev not set")
					vd["MSG"] = "error outputDev not set"
					return vd
###			   #self.indiLOG.log(10, "{}".format(vd))

			props = dev.pluginProps
			piServerNumber	  = props["address"].split("-")[1]
			
			typeId		= dev.deviceTypeId #  "OUTPUT-neopixel"
			lightON 	= False
			maxRGB		= 0
			#if self.decideMyLog("OutputDevice"): self.indiLOG.log(20,"dev.deviceTypeId : {}".format(dev.deviceTypeId ))
			if "command" in vd:
				cmds = vd["command"]
				for iii in range(200):
					if "%%v:" not in cmds and "%%d:" not in cmds: break
					cmds= self.convertVariableOrDeviceStateToText(cmds)
				if self.decideMyLog("OutputDevice"): self.indiLOG.log(5,"input:\n{}".format(vd["command"])+"\n result:\n{}".format(cmds)+"\n")

				if cmds .find("[{'") ==0: #  this will not work for json  replace ' with " as text delimiters and save any "
					cmds = cmds.replace("'", "aa123xxx123xxxaa").replace('"',"'").replace("aa123xxx123xxxaa",'"')

				try:
					cmds = json.loads(cmds)
				except Exception as e:
					if "{}".format(e) != "None":
						self.exceptionHandler(40, e)
					self.indiLOG.log(40,"error in json conversion for {}".format(cmds))
					vd["MSG"] = "error in json conversion"
					return
				if self.decideMyLog("OutputDevice"): self.indiLOG.log(5," after json conversion:\n{}".format(cmds)+"\n")

				for ii in range(len(cmds)):
					cType = cmds[ii]["type"]
					if "position" in cmds[ii]:
							cmds, xx, ok = self.makeACompleteList("position", cmds[ii],cmds,ii,ii)
							if not ok: return vd
					if not (cType == "image"):
						if "text" in cmds[ii]: del cmds[ii]["text"]

			else:
				cmds =[]
				nn =-1
				for ii in range(100):
					iiC= "{}".format(ii)
					if "type{}".format(ii) not in vd: continue
					cType = vd["type"+iiC]
					if cType  == "0":					continue
					if cType  == "none":				continue
					if cType  == "":					continue
					#self.indiLOG.log(20,"ctype: {}".format(cType))
					if cType in ["text", "NOP", "sLine", "line", "points","sPoint", "rectangle", "knightrider", "colorknightrider", "exec", "image", "sl","l","r","p","sp","kn","ckn"]:
						cmds.append({})
						nn+=1
						cmds[nn]["type"]					= cType
						#if cType == "knightrider" :self.indiLOG.log(20,"{}, {}".format(cmds, vd))
						if "text"+iiC in vd:
							cmds[nn]["text"]				= self.convertVariableOrDeviceStateToText(vd["text"+iiC])
						if "delayStart"+iiC in vd:
							cmds[nn]["delayStart"]			= self.convertVariableOrDeviceStateToText(vd["delayStart"+iiC])
						if "reset"+iiC in vd:
							cmds, vd, ok = self.makeACompleteList("reset", vd,cmds,nn,ii)
						if "rotate"+iiC in vd:
							cmds[nn]["rotate"]			 	= self.convertVariableOrDeviceStateToText(vd["rotate"+iiC])
						if "rotateSeconds"+iiC in vd:
							cmds[nn]["rotateSeconds"]		= self.convertVariableOrDeviceStateToText(vd["rotateSeconds"+iiC])
						if "display"+iiC in vd:
							cmds[nn]["display"]		  		= self.convertVariableOrDeviceStateToText(vd["display"+iiC])
						if "position"+iiC in vd:
							cmds, vd, ok = self.makeACompleteList("position", vd,cmds,nn,ii)
							if not ok: return vd
						if "speedOfChange"+iiC in vd:
							cmds[nn]["speedOfChange"] 		= self.convertVariableOrDeviceStateToText(vd["speedOfChange"+iiC])

						if	cType != "image" :
							if "text" in cmds[nn]:	 del cmds[nn]["text"]

					elif cType =="thermometer":
						if "startPixelx"+iiC in vd and "endPixelx"+iiC in vd and "startPixelRGB"+iiC in vd and "endPixelRGB"+iiC in vd and "deltaColorSteps"+iiC in vd:
							cmds.append({})
							nn+=1
							cmds[nn]["type"]				= "points"
							if "position"+iiC in vd:
								cmds, vd, ok = self.makeACompleteList("position", vd,cmds,nn,ii)
								if not ok: return vd
							if "speedOfChange"+iiC in vd:
								cmds[nn]["speedOfChange"] 	= self.convertVariableOrDeviceStateToText(vd["speedOfChange"+iiC])
							if "delayStart"+iiC in vd:
								cmds[nn]["delayStart"]		= self.convertVariableOrDeviceStateToText(vd["delayStart"+iiC])
							if "reset"+iiC in vd:
								cmds, vd, ok = self.makeACompleteList("reset", vd,cmds,nn,ii)

							startPixelx		= int(self.convertVariableOrDeviceStateToText(vd["startPixelx"+iiC]))
							endPixelx		= int(self.convertVariableOrDeviceStateToText(vd["endPixelx"+iiC]))
							startPixelRGB	= map(int, self.convertVariableOrDeviceStateToText(vd["startPixelRGB"+iiC]).split(",")  )
							endPixelRGB		= map(int, self.convertVariableOrDeviceStateToText(vd["endPixelRGB"+iiC]).split(",")	  )
							deltaColorSteps = map(int, self.convertVariableOrDeviceStateToText(vd["deltaColorSteps"+iiC]).split(","))
							if self.decideMyLog("OutputDevice"): self.indiLOG.log(10,";  startPixelx:{}".format(startPixelx) +";  endPixelx:{}".format(endPixelx) +";  startPixelRGB:{}".format(startPixelRGB)+";   endPixelRGB:{}".format(endPixelRGB) +";   deltaColorSteps:{}".format(deltaColorSteps)	 )
							nsteps	   =  max(0,abs(endPixelx - startPixelx))
							deltaC	   =  [endPixelRGB[ll] - startPixelRGB[ll] for ll in range(3)]
							deltaCabs  =  map(abs, deltaC)
							deltaCN	   =  sum(deltaCabs)
							stepSize   =  float(deltaCN)/ max(1,nsteps)
							stepSizeSign   =  [cmp(deltaC[0],0),cmp(deltaC[1],0),cmp(deltaC[2],0)]
							if self.decideMyLog("OutputDevice"):self.indiLOG.log(10,";  nsteps:{}".format(nsteps) +";  deltaC:{}".format(deltaC) +";  deltaCabs:{}".format(deltaCabs) +";  deltaCN:{}".format(deltaCN) +";  stepSize:{}".format(stepSize)+";  stepSizeSign:{}".format(stepSizeSign) )
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
							if self.decideMyLog("OutputDevice"):self.indiLOG.log(10, "{}".format(pos))
							cmds[nn]["position"] = pos
						else:
							vd["MSG"] = "error in type"
							return vd


				#self.indiLOG.log(10,	"{}".format(vd))
			ip = self.RPI[piServerNumber]["ipNumberPi"]

			startAtDateTime = 0
			if "startAtDateTime" in valuesDict:
				startAtDateTime = self.setDelay(startAtDateTimeIN=self.convertVariableOrDeviceStateToText(vd["startAtDateTime"]))

			repeat =1
			resetInitial = ""
			scrollxy = ""
			scrollPages = 1
			scrollDelay = 0
			scrollDelayBetweenPages = 0
			intensity = "100"
			showDateTime = "0"
			status = vd.get("status","notSet")

			if "repeat" in vd:
				repeat = self.convertVariableOrDeviceStateToText(vd["repeat"])
			else:
				repeat = 1
			if "{}".format(repeat) == "": repeat = 1

			if "intensity" in vd:
				intensity = self.convertVariableOrDeviceStateToText(vd["intensity"])
			if "{}".format(intensity) == "": intensity = 100

			if "resetInitial" in vd:
				resetInitial, vd, ok = self.makeACompleteList("resetInitial", vd)
				if not ok: return vd

			restoreAfterBoot = vd.get("restoreAfterBoot","0")
			if "{}".format(restoreAfterBoot) not in ["0","1"]: 
				if restoreAfterBoot in [True,"True","true"]: restoreAfterBoot = "1"
				if restoreAfterBoot in [False,"False","false"]: restoreAfterBoot = "0"

			try:
				line = "\n##=======use this as a python script in an action group action :=====\n"
				line +="plug = indigo.server.getPlugin(\"com.karlwachs.piBeacon\")"
				line +="\nplug.executeAction(\"Neopixel\" , props ={"
				line +="\n     \"outputDev\":\"{}".format(vd["outputDev"])+"\""
				line +="\n    ,\"device\":\"{}".format(typeId)+"\""
				line +="\n    ,\"restoreAfterBoot\":\"{}".format(restoreAfterBoot)+"\""
				line +="\n    ,\"intensity\":\"{}".format(intensity)+"\""
				line +="\n    ,\"status\":\"{}".format(status)+"\""
				line +="\n    ,\"repeat\":\"{}".format(repeat)+"\""
				line +="\n    ,\"resetInitial\":\"{}".format(resetInitial)+"\""
				line +="\n    ,\"command\":'['+\n     '"
				for cc in cmds:
					line += json.dumps(cc)+"'+\n    ',"
					if "position" not in cc: continue
					if "type" not in cc: continue
					ctype = cc["type"]
					if cType.lower() not  in ["text", "NOP", "sLine", "line", "points","sPoint", "rectangle", "knightrider", "colorknightrider", "exec", "image", "sl","l","r","p","sp","kn","ckn"]: continue
					position = cc["position"]

					#self.indiLOG.log(20,"type:{}, position: {}".format(ctype, position))
					pos = cc["position"]
					if ctype == "points": 
						for xx in pos: 
							maxRGB = max( maxRGB, self.findMaxRGB(xx))
					else:
							maxRGB = max( maxRGB, self.findMaxRGB(pos))
					if maxRGB > 0:
						lightON = True


				line = line.strip("'+\n     ',")
				line+="]'\n })\n"
				line+= "##=======   end   =====\n"
				if self.decideMyLog("OutputDevice"): self.indiLOG.log(5,"\n"+line+"\n")
			except Exception as e:
				if "{}".format(e) != "None":
					self.exceptionHandler(40, e)
				if self.decideMyLog("OutputDevice"): self.indiLOG.log(40,"use this as a ppython script command:\n"+"plug = indigo.server.getPlugin(\"com.karlwachs.piBeacon\")\nplug.executeAction(\"Neopixel\" , props ="+
				  (json.dumps({"outputDev":vd["outputDev"],"device": typeId, "restoreAfterBoot": "0", "intensity":intensity,"repeat":repeat,"resetInitial":resetInitial})).strip("}").replace("false", "False").replace("true", "True")+"\n,\"command\":'"+json.dumps(cmds) +"'})"+"\n")
				self.indiLOG.log(10,"vd: {}".format(vd))

			chList= []
			if "writeOutputToState" not in props or ("writeOutputToState" in props and props["writeOutputToState"] == "1"):
				chList.append({"key":"OUTPUT", "value": "{}".format(cmds).replace(" ","")})
			chList.append({"key":"status", "value": round(maxRGB/2.55,0)})
			self.execUpdateStatesList(dev,chList)
			if lightON:
				dev.updateStateImageOnServer(indigo.kStateImageSel.PowerOn)
			else:
				dev.updateStateImageOnServer(indigo.kStateImageSel.PowerOff)

			toSend = [{"device": typeId,  "restoreAfterBoot": restoreAfterBoot, "intensity":intensity,"repeat":repeat,"resetInitial":resetInitial,"status":status,"startAtDateTime":startAtDateTime,"command": cmds}]
			self.sendtoRPI(ip, piServerNumber, toSend, calledFrom="setneopixelCALLBACKmenu")
			vd["MSG"] = " ok"

		except Exception as e:
			self.exceptionHandler(40, e)
			self.indiLOG.log(40,"error display check {}".format(vd))
			valuesDict["MSG"] = "error in parameters"
		return vd

	def findMaxRGB(self, findRGB):
		try:
			maxRGB = 0
			if len(findRGB) < 3: return 0
			for RGB  in findRGB[-3:]:
				try:
					#self.indiLOG.log(20,"RGB:{}".format(RGB))
					rgbV =  int(RGB)
					if rgbV > maxRGB:
						maxRGB	= rgbV
				except: pass
		except Exception as e:
			self.exceptionHandler(40, e)
		return maxRGB


####-------------------------------------------------------------------------####
	def setStepperMotorCALLBACKaction(self, action1=None, typeId="", devId=0):
		valuesDict = action1.props
		return self.setStepperMotorCALLBACKmenu(valuesDict)

####-------------------------------------------------------------------------####


# noinspection SpellCheckingInspection
	def setStepperMotorCALLBACKmenu(self, valuesDict=None, typeId="", devId=0):
		cmds =[]
		try:
			vd=valuesDict
			if self.decideMyLog("OutputDevice"): self.indiLOG.log(5,"setdisplayCALLBACKmenu: {}".format(vd))
			try:
				dev = indigo.devices[int(vd["outputDev"])]
			except:
				try:
					dev = indigo.devices[vd["outputDev"]]
				except:
					self.indiLOG.log(40,"error outputDev not set")
					vd["MSG"] = "error outputDev not set"
					return
###			   #self.indiLOG.log(10, "{}".format(vd))

			props = dev.pluginProps
			piServerNumber	  = props["address"].split("-")[1]
			typeId			  = "setStepperMotor"
			if "command" in vd:
				cmds = vd["command"]
				for iii in range(200):
					if "%%v:" not in cmds and "%%d:" not in cmds: break
					cmds= self.convertVariableOrDeviceStateToText(self.convertVariableOrDeviceStateToText(cmds))
				if self.decideMyLog("OutputDevice"): self.indiLOG.log(5,"input:{}".format(vd["command"])+" result:{}".format(cmds)+"\n")

				try:
					cmds = json.loads(cmds)
				except Exception as e:
					self.exceptionHandler(40, e)
					self.indiLOG.log(40,"error in json conversion for {}".format(cmds))
					vd["MSG"] = "error in json conversion"
					return
				if self.decideMyLog("OutputDevice"): self.indiLOG.log(5," after json conversion:{}".format(cmds)+"\n")


			else:
				###if self.decideMyLog("OutputDevice"): self.indiLOG.log(5,"input:{}".format(vd))
				cmds =[]
				nn =-1
				for ii in range(100):
						iiS = "{}".format(ii)
						if "cmd-"+iiS in vd:
							cmds.append({}); nn+=1
							if  vd["cmd-"+iiS] =="steps":
								if "steps-"+iiS in vd:
									try:  cmds[nn]["steps"] 		= int(vd["steps-"+iiS])
									except: cmds[nn]["steps"] 		= 0

								if "waitBefore-"+iiS in vd:
									try: cmds[nn]["waitBefore"]		= float(vd["waitBefore-"+iiS])
									except: cmds[nn]["waitBefore"]	= 0

								if "waitAfter-"+iiS in vd:
									try: cmds[nn]["waitAfter"]		= float(vd["waitAfter-"+iiS])
									except: cmds[nn]["waitAfter"]	= 0

								if "stayOn-"+iiS in vd:
									try: cmds[nn]["stayOn"]		= int(vd["stayOn-"+iiS])
									except: cmds[nn]["stayOn"] 		= 1

								if "dir-"+iiS in vd:
									try: cmds[nn]["dir"]			= int(vd["dir-"+iiS])
									except: cmds[nn]["dir"] 		= 1

								if "GPIO.0-"+iiS in vd:
									try: cmds[nn]["GPIO.0"]		= int(vd["GPIO.0-"+iiS])
									except: pass

								if "GPIO.1-"+iiS in vd:
									try: cmds[nn]["GPIO.1"]		= int(vd["GPIO.1-"+iiS])
									except: pass

								if "GPIO.2-"+iiS in vd:
									try: cmds[nn]["GPIO.2"]		= int(vd["GPIO.2-"+iiS])
									except: pass

							elif vd["cmd-"+iiS] == "sleepMotor":
								cmds[nn]["sleepMotor"] 			= 1
								if "waitBefore-"+iiS in vd:
									try: cmds[nn]["waitBefore"]		= float(vd["waitBefore-"+iiS])
									except: cmds[nn]["waitBefore"] 	= 0
								if "waitAfter-"+iiS in vd:
									try: cmds[nn]["waitAfter"]		= float(vd["waitAfter-"+iiS])
									except: cmds[nn]["waitAfter"] 	= 0


							elif vd["cmd-"+iiS] == "wakeMotor":
								cmds[nn]["wakeMotor"] 			= 1
								if "waitBefore-"+iiS in vd:
									try: cmds[nn]["waitBefore"]		= float(vd["waitBefore-"+iiS])
									except: cmds[nn]["waitBefore"] 	= 0
								if "waitAfter-"+iiS in vd:
									try: cmds[nn]["waitAfter"]		= float(vd["waitAfter-"+iiS])
									except: cmds[nn]["waitAfter"] 	= 0

							elif vd["cmd-"+iiS] == "offMotor":
								cmds[nn]["offMotor"] 				= 1
								if "waitBefore-"+iiS in vd:
									try: cmds[nn]["waitBefore"]		= float(vd["waitBefore-"+iiS])
									except: cmds[nn]["waitBefore"] 	= 0
								if "waitAfter-"+iiS in vd:
									try: cmds[nn]["waitAfter"]		= float(vd["waitAfter-"+iiS])
									except: cmds[nn]["waitAfter"] 	= 0

							elif vd["cmd-"+iiS] == "onMotor":
								cmds[nn]["onMotor"] 				= 1
								if "waitBefore-"+iiS in vd:
									try: cmds[nn]["waitBefore"]		= float(vd["waitBefore-"+iiS])
									except: cmds[nn]["waitBefore"] 	= 0
								if "waitAfter-"+iiS in vd:
									try: cmds[nn]["waitAfter"]		= float(vd["waitAfter-"+iiS])
									except: cmds[nn]["waitAfter"] 	= 0


							elif vd["cmd-"+iiS] == "wait":
								cmds[nn]["wait"] 					= int(vd["wait-"+iiS])

							if cmds[nn] == {}: del cmds[-1]

				#self.indiLOG.log(10,	"{}".format(vd))
			ip = self.RPI[piServerNumber]["ipNumberPi"]

			startAtDateTime = 0
			if "startAtDateTime" in valuesDict:
				startAtDateTime = self.setDelay(startAtDateTimeIN=self.convertVariableOrDeviceStateToText(vd["startAtDateTime"]))

			repeat			= 1
			if "repeat" in vd:
				repeat = self.convertVariableOrDeviceStateToText(vd["repeat"])
			if "{}".format(repeat) == "": repeat = 1


			waitForLast				= "1"
			if "waitForLast" in vd:
				waitForLast = self.convertVariableOrDeviceStateToText(vd["waitForLast"])
			if "{}".format(waitForLast) == "":  waitForLast = 1

			try:
				line = "\n##=======use this as a python script in an action group action :=====\n"
				line +="plug = indigo.server.getPlugin(\"com.karlwachs.piBeacon\")"
				line +="\nplug.executeAction(\"StepperMotor\" ,	props ={"
				line +="\n     \"outputDev\":\"{}".format(vd["outputDev"])+"\""
				line +="\n    ,\"device\":\"{}".format(typeId)+"\""
				line +="\n    ,\"dev.id\":\"{}".format(dev.id)+"\""
				line +="\n    ,\"repeat\":\"{}".format(repeat)+"\""
				line +="\n    ,\"waitForLast\":\"{}".format(waitForLast)+"\""
				line +="\n    ,\"command\":'['+\n     '"

				### this will create list of dicts, one per command, remove blank items, sort  ,..
				doList =["steps", "sleepMotor", "offMotor", "wait", "stayON", "waitBefore", "waitAfter", "dir", "GPIO.0", "GPIO.1", "GPIO.2"] # sorted by this
				for cc in range(len(cmds)):
					delItem=[]
					if len(cmds[cc]) > 0:
						line +="{"
						for item in doList:
							if item in cmds[cc]:
								if cmds[cc][item] !="" :
									line +='"'+item+'":'+json.dumps(cmds[cc][item]).strip(" ")+", "
								else:# this is blank
									delItem.append(item)

						## remove blanks
						for item in delItem:
							del cmds[cc][item]
						# close line
						line  = line.strip(", ") + "}'+\n    ',"

				## finish cmd lines
				line  = line.strip("'+\n        ',")	+ "]'\n	 })\n"
				## end of output
				line += "##=======   end   =====\n"

				if self.decideMyLog("OutputDevice"): self.indiLOG.log(5,"\n"+line+"\n")
				vd["MSG"] = " ok"

			except Exception as e:
				if "{}".format(e) != "None":
					self.exceptionHandler(40, e)
					vd["MSG"] = "error"
			toSend = [{"device": typeId, "repeat":repeat, "waitForLast":waitForLast, "dev.id":dev.id, "startAtDateTime":startAtDateTime, "command": cmds}]
			self.sendtoRPI(ip, piServerNumber, toSend, calledFrom="setStepperMotorCALLBACKmenu")

		except Exception as e:
			self.exceptionHandler(40, e)
			self.indiLOG.log(40,"error stepperMotor check {}".format(vd))
			valuesDict["MSG"] = "error in parameters"
		return vd



####-------------------------------------------------------------------------####
	def makeACompleteList(self,item, vd,cmds=[],nn="",ii=""):
		try:
			if item+ "{}".format(ii) in vd:
				xxx				 = "{}".format(self.convertVariableOrDeviceStateToText("{}".format(vd[item+ "{}".format(ii)])))
				if xxx =="": return cmds, vd, True
				if xxx[0]  !="[": xxx = "["+xxx
				if xxx[-1] !="]": xxx =xxx+ "]"
				try:
					if cmds ==[]:
						cmds			 = json.loads(xxx)
					else:
						cmds[nn][item]	 = json.loads(xxx)
					return cmds, vd, True
				except Exception as e:
					self.exceptionHandler(40, e)
					self.indiLOG.log(40," error in input: "+item+" ii={}".format(ii)+" nn={}".format(nn)+ " cmds="+	 "{}".format(cmds) + " xxx="+  "{}".format(xxx))
					vd["MSG"] = "error in parameter"
				return cmds,vd, False
		except Exception as e:
			self.exceptionHandler(40, e)
			self.indiLOG.log(40,"item {}".format(item)+ "{}".format(ii)+"  , vd {}".format(vd))
			return cmds,vd, False
		return cmds,vd, True



####-------------------------------------------------------------------------####
	def sendFileToRPIviaSocket(self,ip, piU, fileName, fileContents, fileMode="w", touchFile=True):
		try:  
			toSend= [{"command":"file", "fileName":fileName, "fileContents":fileContents, "fileMode":fileMode, "touchFile":touchFile}]
			if self.decideMyLog("OutputDevice"): self.indiLOG.log(5, "sending file to  {};  {}".format(ip, toSend) )
			self.sendtoRPI(ip, piU, toSend, calledFrom="sendFileToRPIviaSocket")
		except Exception as e:
			self.exceptionHandler(40, e)
		return




####-------------------------------------------------------------------------####
	def presendtoRPI(self, piU, out):
		retC = 0
		if piU == "999":
			for piU in self.RPI:
				if self.RPI[piU]["ipNumberPi"] == "":	continue
				if self.RPI[piU]["piOnOff"]	== "":	 	continue
				if self.RPI[piU]["piOnOff"]	== "0": 	continue
				retC = max(retC, self.sendtoRPI(self.RPI[piU]["ipNumberPi"], piU, out , calledFrom="presendtoRPI 1") )
		else:
			if self.RPI[piU]["piOnOff"]	== "":		return	 2
			if self.RPI[piU]["piOnOff"]	== "0":		return	 2
			if self.RPI[piU]["ipNumberPi"] == "":	return	 2
			retC = self.sendtoRPI(self.RPI[piU]["ipNumberPi"], piU, out, calledFrom="presendtoRPI 2")

		return retC

####-------------------------------------------------------------------------####
	def sendtoRPI(self, ip, pi, theList, force = False, calledFrom=""):

		try:
			piU = "{}".format(pi)
			if self.RPI[piU]["piOnOff"] == "0": return

			for kk in range(len(theList)):
				theList[kk]["indigoServerIP"] = "{}".format(self.myIpNumber)
				pass
			theStringToRPI = json.dumps(theList)

			if ip not in self.checkIPSendSocketOk:
				self.checkIPSendSocketOk[ip] = {"count":0, "time":0, "pi": piU}

			if self.checkIPSendSocketOk[ip]["count"] > 5 and not force:
				if time.time() + self.checkIPSendSocketOk[ip]["time"] > 120:
					self.checkIPSendSocketOk[ip]["count"] = 0
				else:
					self.indiLOG.log(10,"sendtoRPI sending to pi# {}  {} skipped due to recent failure count, reset by dis-enable & enable rPi ;  calledFrom:{}; command-string={}..{}".format(piU, ip, calledFrom, theStringToRPI[0:100], theStringToRPI[-100:] ) )
					return -1

			if self.decideMyLog("OutputDevice") or self.decideMyLog("SocketRPI"): self.indiLOG.log(5,"sendtoRPI sending to  {} {};  calledFrom:{}; command-string={}".format(piU, ip, calledFrom, theStringToRPI ) )
			#if self.decideMyLog("Special") and ip == "192.168.1.25": self.indiLOG.log(5,"sendtoRPI sending to  {} {};  calledFrom:{}; command-string={}".format(piU, ip, calledFrom, theStringToRPI ) )
				# Create a socket (SOCK_STREAM means a TCP socket)
			sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
			sock.settimeout(3.)
			try:
				# Connect to server and send data
				sock.connect((ip, int(self.rPiCommandPORT)))
				if sys.version_info[0] > 2: 	sock.sendall(bytes(theStringToRPI + "\n",'utf-8'))
				else:							sock.sendall(theStringToRPI + "\n")
			except Exception as e:
					if "{}".format(e) != "None":
						if	time.time() > self.currentlyBooting:  # NO MSG IF RPIS ARE BOOTING
							if piU in self.rpiQueues["busy"]: 
								if time.time() - self.rpiQueues["busy"][piU] > 20: # supress warning if we just updated the RPI
									self.indiLOG.log(10,"socket-send not working,  rPi:{} {} is currently updating, delaying send".format(pi, ip) )
								else:
									if "{}".format(e).find("onnection refused") ==-1:
										self.indiLOG.log(30,"error in socket-send to rPi:{} {}  cmd= {}...{}".format(pi, ip, json.dumps(theList)[0:30],json.dumps(theList)[-30:]) )
									else:
										self.indiLOG.log(30,"error in socket-send to rPi:{} {}, connection refused, rebooting/restarting RPI?".format(pi, ip) )
								self.checkIPSendSocketOk[ip]["count"] += 1
								self.checkIPSendSocketOk[ip]["time"]	= time.time()
						try:	sock.close()
						except: pass
						return -1
			finally:
					sock.close()
		except Exception as e:
			if "{}".format(e) != "None":
				if	time.time() > self.currentlyBooting: # NO MSG IF RPIS ARE BOOTING
					if "{}".format(e).find("onnection refused") ==-1:
						self.indiLOG.log(40,"error in socket-send to rPi:{} {}  cmd= {}..{}".format(pi, ip, json.dumps(theList)[0:30], json.dumps(theList)[-30:]) )
						self.exceptionHandler(40, e)
					else:
						self.indiLOG.log(30,"error in socket-send to rPi:{} (), connection refused,  rebooting/restarting RPI?".format(pi, ip) )
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
			valuesDict["typeId"]		 = "playSound"
			valuesDict["cmd"]			 = "playSound"
			self.setPin(valuesDict)
		except Exception as e:
			self.exceptionHandler(40, e)
			return valuesDict
		return valuesDict

####-------------------------------------------------------------------------####
	def restartPluginCALLBACKaction(self, action1=None, typeId="", devId=0):
		self.quitNow		= "Internal restart requested, ignore indigo warning message >>piBeacon Error ..."
		return


####-------------------------------------------------------------------------####
	def restartPluginCALLBACKmenu(self, valuesDict=None, typeId="", devId=0):
		self.quitNow		 = "Internal restart requested, ignore indigo warning message >>piBeacon Error ..."
		valuesDict["MSG"]	 = "internal restart underway, exit menu"
		return valuesDict


####-------------------------------------------------------------------------####
	def reloadDevStatesCALLBACKmenu(self, valuesDict=None, typeId="", devId=0):
		valuesDict["MSG"]	 = "updating dev states initiated"
		self.indiLOG.log(30,"updating dev states initiated")
		self.checkIfNewStates(force=True)
		return valuesDict



####-------------------------------------------------------------------------####
	def resetHostsFileCALLBACKmenu(self, valuesDict=None, typeId="", devId=0):
		if valuesDict is None: valuesDict = {}
		fn = "{}/.ssh/known_hosts".format(self.MAChome)

		if os.path.isfile(fn):
			os.remove(fn)

		if not os.path.isfile(fn):
			valuesDict["MSG"] = "{} file deleted".format(fn)
			self.indiLOG.log(30,"ssh known hosts file deleted:{}".format(fn))

		else:
			valuesDict["MSG"] = "ERROR {} file NOT deleted".format(fn)
			self.indiLOG.log(30,"Error ssh known hosts file  NOT deleted:{}".format(fn))

		return valuesDict


####-------------------------------------------------------------------------####
	def resetHostsFileOnlyRpiCALLBACKmenu(self, valuesDict=None, typeId="", devId=0):
		if valuesDict is None: valuesDict = {}
		fn = "{}/.ssh/known_hosts".format(self.MAChome)
		removed = ""

		if os.path.isfile(fn):
			try:
				for piU in self.RPI:
					ipN = self.RPI[piU]["ipNumberPi"]
					if  self.isValidIP(ipN):
						f = open(fn, "r")
						lines  = f.readlines()
						f.close()

						f = open(fn, "w")
						for line in lines:
							if len(line) < 10: continue
							if line.find(ipN) >-1:
								self.indiLOG.log(30,"ssh known_hosts: removed line:{}".format(line.strip("\n")))
								removed += piU+"; "
								continue
							f.write(line.strip("\n")+"\n")
						f.close()

			except Exception as e:
				self.exceptionHandler(40, e)

		valuesDict["MSG"] = "rmved pi# {} entries".format(removed.strip("; "))

		return valuesDict


####-------------------------------------------------------------------------####
	def getBeaconParametersCALLBACKaction(self, action1=None, typeId="", devId=0):
		return self.getBeaconParametersCALLBACKmenu(action1.props)

####-------------------------------------------------------------------------####
	def getONEBeaconParametersCALLBACKaction(self, action1=None, typeId="", devId=0):
		return self.getONEBeaconParametersCALLBACKmenu(action1.props)


####-------------------------------------------------------------------------####
	def getONEBeaconParametersCALLBACKmenu(self, valuesDict=None, typeId="", devId=0):

		try:
				devId = int(valuesDict["devIdOfBeacon"])
				return  self.getBeaconParametersCALLBACKmenu( valuesDict=valuesDict, devId=devId, force=True )
		except Exception as e:
			self.exceptionHandler(40, e)
		return valuesDict

####-------------------------------------------------------------------------####
	def getBeaconParametersCALLBACKmenu(self, valuesDict=None, typeId="", devId=0, force=True):

		try:
			# must be enabled in config
			if not force and self.checkBeaconParametersDisabled: return

			if self.decideMyLog("BatteryLevel"): self.indiLOG.log(10,"getBeaconParameters requesting update for beacon devId:{}, parameters:{}".format(devId, valuesDict))

			devices = {}

			if  valuesDict is None:
				self.indiLOG.log(10,"getBeaconParameters no data input")
				return  valuesDict

			# check if it is all beacons
			beacon = ""
			if devId != 0:
				try:
					beaconDev = indigo.devices[devId]
					beacon    =  beaconDev.address
				except:
					# all beacons and rpi
					valuesDict["piServerNumber"]  = "all"


			if "piServerNumber" not in  valuesDict:
				self.indiLOG.log(10,"getBeaconParameters piServerNumber not defined")
				return  valuesDict

			valuesDict["piServerNumber"]  =  "{}".format(valuesDict["piServerNumber"] )

			if valuesDict["piServerNumber"]  == "-1":
				valuesDict["piServerNumber"]  = "all"


			try:beepTime = float(valuesDict.get("beepTime","0"))
			except: beepTime = 0

			# check if anythinges beside "all or a number, if so: set to all"
			if valuesDict["piServerNumber"]  != "all":
				try: 	int(valuesDict["piServerNumber"])
				except: valuesDict["piServerNumber"]  = "all"

			startAtDateTime = 0 
			if "startAtDateTime" in valuesDict:
				try: startAtDateTime = float(valuesDict.get("startAtDateTime", 0))
				except: pass

			elif "delayStart" in valuesDict:
				try: startAtDateTime = float(valuesDict.get("delayStart", 0))
				except: pass

			# make list of devicesper RPI
			for piU in _rpiBeaconList:
				if valuesDict["piServerNumber"] == piU or valuesDict["piServerNumber"] == "all" or valuesDict["piServerNumber"] == "999":
					devices[piU] = {}

			# this is for timeouts for rpis
			minTime ={}
			for piU2 in _rpiList:
				minTime[piU2] = 0

			for dev in indigo.devices.iter("props.isBeaconDevice"):
				props = dev.pluginProps
				if "status" not in dev.states: continue
				if dev.states["status"] !="up": continue
				if not dev.enabled: continue 
				if beacon != "" and (dev.address != beacon or devId != dev.id): continue
				if valuesDict["piServerNumber"] == "all" or valuesDict["piServerNumber"] == "999":
					piU = str(dev.states["closestRPI"])
				else:
					piU = valuesDict["piServerNumber"]

				# just a double check
				if piU not in _rpiBeaconList: continue

				if self.decideMyLog("BatteryLevel"): self.indiLOG.log(10,"getBeaconParameters checking beacon: {:30s};".format(dev.name) )

				mac  = dev.address
				cmdToSend = {}
				typeOfBeacon = self.beacons[mac]["typeOfBeacon"]
				if typeOfBeacon !="":
					if typeOfBeacon not in self.knownBeaconTags["input"]: 						 						continue
					if "commands" not in self.knownBeaconTags["input"][typeOfBeacon]:			 						continue
					if "batteryLevel" not in self.knownBeaconTags["input"][typeOfBeacon]["commands"]: 					continue
					if "type" not in self.knownBeaconTags["input"][typeOfBeacon]["commands"]["batteryLevel"]: 			continue 
					if self.knownBeaconTags["input"][typeOfBeacon]["commands"]["batteryLevel"]["type"] != "BLEconnect": 	continue 
					if self.decideMyLog("BatteryLevel"): self.indiLOG.log(10,"getBeaconParameters checking  passed check 1;" )

					# check if we should do battery time check at this hour, some beacons beep (nutale) if battery level is checked
					if not force and "batteryLevelCheckhours" in props:
						hh = (datetime.datetime.now()).hour
						batteryLevelCheckhours =  props["batteryLevelCheckhours"].split("/")
						if len(batteryLevelCheckhours) > 1:
							found = False
							for bb in batteryLevelCheckhours:
								try:
									if int(bb) == hh:
										found = True
										break
								except:
									found = True
									break
							if not found: continue
					if self.decideMyLog("BatteryLevel"): self.indiLOG.log(10,"getBeaconParameters passed time window check" )

					if "batteryLevelUUID" in props  and props["batteryLevelUUID"]  == "gatttool":
						try: 	lastUpdateBatteryLevel = self.getTimetimeFromDateString(dev.states["lastUpdateBatteryLevel"])
						except: lastUpdateBatteryLevel = 0
						try: 	batteryLevel = int(dev.states["batteryLevel"])
						except: batteryLevel = 0

						if self.decideMyLog("BatteryLevel"): self.indiLOG.log(10,"getBeaconParameters passed gattool check" )
						if force or batteryLevel < 20  or (time.time() - lastUpdateBatteryLevel) > (3600*17): # if successful today and battery level > 20% dont need to redo it again
							#if self.decideMyLog("BatteryLevel"): self.indiLOG.log(10,"getBeaconParameters pass 3" )
							try:
								stateDist = "Pi_{:02d}_Distance".format(int(piU))
								if stateDist not in dev.states: continue
								dist = float( dev.states[stateDist] )
								if dist < 99.:
									cmdToSend = {"battCmd":copy.copy(self.knownBeaconTags["input"][typeOfBeacon]["commands"]["batteryLevel"])}
									if beepTime != -1:
										if "beep" in self.knownBeaconTags["input"][typeOfBeacon]["commands"] and "cmdOff" in self.knownBeaconTags["input"][typeOfBeacon]["commands"] ["beep"]:
											if beepTime == 0:
												if self.knownBeaconTags["input"][typeOfBeacon]["commands"]["beep"]["cmdOff"] != self.knownBeaconTags["input"][typeOfBeacon]["commands"]["beep"]["cmdON"]:
													cmdToSend["battCmd"]["gattcmd"] = self.knownBeaconTags["input"][typeOfBeacon]["commands"]["beep"]["cmdOff"] + cmdToSend["battCmd"]["gattcmd"]
											else:
												cmdToSend["battCmd"]["gattcmd"] = self.knownBeaconTags["input"][typeOfBeacon]["commands"]["beep"]["cmdON"] + [beepTime] +  self.knownBeaconTags["input"][typeOfBeacon]["commands"]["beep"]["cmdOff"] + cmdToSend["battCmd"]["gattcmd"]

									minTime[piU] += 10
									self.beacons[mac]["lastBusy"] = time.time() + 3
									dev.updateStateOnServer("isBeepable", "busy")
									if self.decideMyLog("BatteryLevel"): self.indiLOG.log(10,"getBeaconParameters requesting update from RPI:{:2s} for beacon: {:30s}; lastV: {:3d}; last successful check @: {}; distance to RPI:{:4.1f}; cmd:{}".format(piU, dev.name, dev.states["batteryLevel"], dev.states["lastUpdateBatteryLevel"], dist, cmdToSend) )

								elif force: # if successful today and battery level > 30% dont need to redo it again
									self.indiLOG.log(20,"Battery level update outdated  for beacon: {:30s}; not doable on requested pi#{:}, not visible on that pi, distance > 99".format(dev.name, piU ) )

								if (time.time() - lastUpdateBatteryLevel) > (3600*24*3): # error message if last update > 3 days ago
									self.indiLOG.log(20,"Battery level update outdated  for beacon: {:30s}; lastV: {:3d}; last successful check @: {}, closestRPI:{}".format(dev.name, dev.states["batteryLevel"], dev.states["lastUpdateBatteryLevel"], dev.states["closestRPIText"] ) )
							except Exception as e:
								self.exceptionHandler(40, e)

						else:
							if self.decideMyLog("BatteryLevel"): self.indiLOG.log(10,"getBeaconParameters no update needed              for beacon: {:30s}; lastV: {:3d}; last successful check @: {}, closestRPI:{}".format(dev.name, dev.states["batteryLevel"], dev.states["lastUpdateBatteryLevel"] , dev.states["closestRPIText"] ) )


				# this is the list of beacons for THIS RPI
				if cmdToSend !={}:
					devices[piU][dev.address] = cmdToSend

			minTime    = max(list(minTime.values()))
			nDownAddWait = True
			nothingFor = []
			countB = 0
			countP = 0
			for piU2 in devices:
					if devices[piU2] == {}:
						if valuesDict["piServerNumber"] == "all" or valuesDict["piServerNumber"] == "999":
							nothingFor.append(int(piU2))
					else:
						xx						= {}
						xx["cmd"]		 		= "getBeaconParameters"
						xx["typeId"]			= json.dumps(devices[piU2])
						xx["piServerNumber"]	= piU2
						xx["startAtDateTime"]	= startAtDateTime
						countB += len(devices[piU2])
						countP += 1
						self.indiLOG.log(10,"getBeaconParameters request: {}".format(xx) )

						if nDownAddWait: self.setCurrentlyBooting(minTime+10, setBy="getBeaconParameters (batteryLevel ..)")
						nDownAddWait = False
						self.setPin(xx)

			if nothingFor != "":
				if self.decideMyLog("BatteryLevel"): self.indiLOG.log(10,"getBeaconParameters no active/requested beacons on rpi# {}".format(sorted(nothingFor)) )
			valuesDict["MSG"]  = "get BatL {} beacons on {} Pi".format(countB,countP)

		except Exception as e:
			self.exceptionHandler(40, e)

		return valuesDict


####-------------------------------------------------------------------------####
	def makeBatteryLevelReportCALLBACKmenu(self, valuesDict=None, typeId="", devId=0, force=True):
		try:
			out  = "battery level report:\nDev---------------------------------------     MAC#               Beacon-Type             Status     ClosestRPI   BeepCommand BatteryLevel LastSuccfulBatUpd   daysAgo GetBatMethod lastNewBattery "
			out1 = ""
			out2 = ""
			out3 = ""
			out4 = ""
			out5 = ""
			out6 = ""

			for dev in indigo.devices.iter("props.isBeaconDevice"):
				piU = str(dev.states["closestRPI"])
				mac  = dev.address
				typeOfBeacon = self.beacons[mac]["typeOfBeacon"]

				batlevel  = "         off"
				if typeOfBeacon not in self.knownBeaconTags["input"]:										continue
				if "commands" not in self.knownBeaconTags["input"][typeOfBeacon]:			 				continue
				if "batteryLevel" not in self.knownBeaconTags["input"][typeOfBeacon]["commands"]: 			continue
				if "type" not in self.knownBeaconTags["input"][typeOfBeacon]["commands"]["batteryLevel"]:	continue 
				if "batteryLevel" in dev.states:
					batlevel = "{:12d}".format(dev.states["batteryLevel"])

				benabled = "not capable"
				try: 	benabled = dev.states["isBeepable"]
				except:	pass

				lastU = "xxx"
				lastTimeStamp = time.time() - 999*(24*3600)
				try:
					if dev.enabled:
						lastU = dev.states["lastUpdateBatteryLevel"]
						try:	
								lastTimeStamp = self.getTimetimeFromDateString(lastU)
						except: lastTimeStamp = time.time() - 999*(24*3600)
					else:
						lastU = "disabled"
				except: pass

				batteryLevelUUID = dev.pluginProps.get("batteryLevelUUID","")


				#self.indiLOG.log(5,"  ibeacon: {:30s}  level: {:3d}%,  last update was: {} ".format(dev.name, batteryLevel, lastUpdateBatteryLevel) )
				lastUpDateDaysAgo = int((time.time() - lastTimeStamp)/(24*3600))
				lastUpDateDaysAgo = min(9999, lastUpDateDaysAgo)
				lastBatteryReplaced =  dev.states.get("lastBatteryReplaced"," ")
	
				if lastUpDateDaysAgo < 999:
					if lastUpDateDaysAgo   > 21:
						out4 += "\n{:47s}{:19s}{:24s}{:17s}{:4d}   {:12s}{:13s}{:20s}{:4d}!!! {:12s} {:19s}".format( dev.name, mac, typeOfBeacon, dev.states["status"], int(piU), benabled, batlevel, lastU, lastUpDateDaysAgo, batteryLevelUUID, lastBatteryReplaced)
					elif lastUpDateDaysAgo > 7:
						out3 += "\n{:47s}{:19s}{:24s}{:17s}{:4d}   {:12s}{:13s}{:20s}{:4d}!!  {:12s} {:19s}".format( dev.name, mac, typeOfBeacon, dev.states["status"], int(piU), benabled, batlevel, lastU, lastUpDateDaysAgo, batteryLevelUUID, lastBatteryReplaced)
					elif lastUpDateDaysAgo > 1:
						out2 += "\n{:47s}{:19s}{:24s}{:17s}{:4d}   {:12s}{:13s}{:20s}{:4d}!   {:12s} {:19s}".format( dev.name, mac, typeOfBeacon, dev.states["status"], int(piU), benabled, batlevel, lastU, lastUpDateDaysAgo, batteryLevelUUID, lastBatteryReplaced)
					else:
						out1 += "\n{:47s}{:19s}{:24s}{:17s}{:4d}   {:12s}{:13s}{:20s}{:4d}    {:12s} {:19s}".format( dev.name, mac, typeOfBeacon, dev.states["status"], int(piU), benabled, batlevel, lastU, lastUpDateDaysAgo, batteryLevelUUID, lastBatteryReplaced)
				elif lastUpDateDaysAgo < 9999:
						out5 += "\n{:47s}{:19s}{:24s}{:17s}{:4d}   {:12s}{:13s}{:20s}{:4d}off {:12s} {:19s}".format( dev.name, mac, typeOfBeacon, dev.states["status"], int(piU), benabled, batlevel, lastU, lastUpDateDaysAgo, batteryLevelUUID, lastBatteryReplaced)
				else:
						out6 += "\n{:47s}{:19s}{:24s}{:17s}{:4d}   {:12s}{:13s}{:20s}{:4d}    {:12s} {:19s}".format( dev.name, mac, typeOfBeacon, dev.states["status"], int(piU), benabled, batlevel, lastU, lastUpDateDaysAgo, batteryLevelUUID, lastBatteryReplaced)

			self.indiLOG.log(20,out+out1+out2+out3+out4+out5+out6)
			valuesDict["MSG"]   = "bat report in indigo log"
		except Exception as e:
			self.exceptionHandler(40, e)

		return valuesDict




####-------------------------------------------------------------------------####
	def sendBeepCommandCALLBACKaction(self, action1=None, typeId="", devId=0):
		return self.sendBeepCommandCALLBACKmenu(action1.props)

####-------------------------------------------------------------------------####
	def sendBeepCommandCALLBACKmenu(self, valuesDict=None, typeId="", devId=0, force=True):

		try:
			if  valuesDict is None: return  valuesDict
			if self.decideMyLog("Beep"): self.indiLOG.log(10,"beep beacon {}".format(valuesDict) )

			if "selectbeacon" not in  valuesDict: return  valuesDict
			dev = indigo.devices[int(valuesDict["selectbeacon"])]
			props = dev.pluginProps
			if dev.states["status"] != "up":
				if self.decideMyLog("Beep"): self.indiLOG.log(10,"beep beacon... beacon dev not up {}, no beep".format(dev.name) )
				return valuesDict


			valuesDict["piServerNumber"]  =  "{}".format(valuesDict["piServerNumber"] )

			try:  	int(valuesDict["piServerNumber"])
			except:	valuesDict["piServerNumber"] = "-1"

			if valuesDict["piServerNumber"] != "-1":
				piU= valuesDict["piServerNumber"]
			else:
				piU = str(dev.states["closestRPI"])

			if piU not in _rpiBeaconList: return valuesDict

			if "mustBeUp" in valuesDict and valuesDict["mustBeUp"] == "1":
				mustBeUp = True
			else:
				mustBeUp = False

			if "beepTime" in valuesDict:
				beepTime = float(valuesDict["beepTime"])
			else:
				mustBeUp = 0.1


			beacon  = dev.address
			if  time.time() - self.beacons[beacon]["lastBusy"] < 0:
				if self.decideMyLog("Beep"):
					self.indiLOG.log(10,"beep beacon requested  for {}  rejected as last beep done too short time ago {}".format(beacon, time.time() - self.beacons[beacon]["lastBusy"]) )
					return valuesDict

			typeOfBeacon = props["typeOfBeacon"]
			if self.decideMyLog("Beep"): self.indiLOG.log(10,"beep beacon... beacon type: {}".format(typeOfBeacon) )
			if typeOfBeacon != "":
				if typeOfBeacon not in self.knownBeaconTags["input"]:
					if self.decideMyLog("Beep"): self.indiLOG.log(10,"beep beacon... beacon type not known" )
				else:
					if "commands" in self.knownBeaconTags["input"][typeOfBeacon]:
						if self.decideMyLog("Beep"): self.indiLOG.log(10,"beep beacon checking params  for pi{} and beacon:{}.".format(piU, self.knownBeaconTags["input"][typeOfBeacon]["commands"]) )
						if "beep" in self.knownBeaconTags["input"][typeOfBeacon]["commands"]:
							if "type" in self.knownBeaconTags["input"][typeOfBeacon]["commands"]["beep"]:
								cmd 					= self.knownBeaconTags["input"][typeOfBeacon]["commands"]["beep"]
								cmd["beepTime"] 		= beepTime
								cmd["mustBeUp"] 		= mustBeUp
								xx 						= {"cmd":"beepBeacon", "piServerNumber":piU, "typeId":json.dumps({beacon:cmd})}
								self.indiLOG.log(10,"beep beacon requested:  {}".format( xx) )
								self.beacons[beacon]["lastBusy"] = time.time() + beepTime + 3
								self.setCurrentlyBooting(20, setBy="beep beacon")
								self.setPin(xx)
								valuesDict["MSG"] = "beep {} on pi{} ".format(beacon, piU)
								dev.updateStateOnServer("isBeepable", "busy")
		except Exception as e:
			self.exceptionHandler(40, e)
		return valuesDict



####-------------------------------------------------------------------------####
	def sendSetTimeAndZoneOnDeviceCALLBACKaction(self, action1=None, typeId="", devId=0):
		return self.sendBeepCommandCALLBACKmenu(action1.props)

####-------------------------------------------------------------------------####
	def sendSetTimeAndZoneOnDeviceCALLBACKmenu(self, valuesDict=None, typeId="", devId=0, force=True):

		if  valuesDict is None: return  valuesDict
		if self.decideMyLog("UpdateTimeAndZone"): self.indiLOG.log(10,"UpdateTimeAndZone {}".format(valuesDict) )

		if "selectbeacon" not in  valuesDict: 
			valuesDict["MSG"] = "dev not selected"
			self.indiLOG.log(30,"UpdateTimeAndZone... beacon dev not selected")
			return  valuesDict
		devId = valuesDict["selectbeacon"]
		try: 
			devId = int(devId)
		except:
			valuesDict["MSG"] = "dev not selected"
			self.indiLOG.log(30,"UpdateTimeAndZone... beacon dev not selected")
			return valuesDict
		dev = indigo.devices[devId]

		try:  	int(valuesDict["piServerNumber"])
		except:	valuesDict["piServerNumber"] = "-1"

		if valuesDict["piServerNumber"] != "-1":
			piU = valuesDict["piServerNumber"]
		else:
			valuesDict["MSG"] = "pi  not selected"
			self.indiLOG.log(30,"UpdateTimeAndZone...pi  not selected")
			return valuesDict

		if piU not in _rpiBeaconList: 
			valuesDict["MSG"] = "pi  not selected"
			self.indiLOG.log(30,"UpdateTimeAndZone...pi  not selected")
			return valuesDict

		beacon  = dev.address

		xx 	= {"cmd":"updateTimeAndZone", "piServerNumber":piU, "typeId":json.dumps({beacon:"settime"})}
		if self.decideMyLog("UpdateTimeAndZone"): self.indiLOG.log(20,"updateTimeAndZone beacon requested  on pi{};  {}".format(piU, xx) )
		self.setCurrentlyBooting(20, setBy="updateTimeAndZone beacon")
		self.setPin(xx)
		valuesDict["MSG"] = "exec for {} on pi{}".format(beacon, piU)
		return valuesDict

####-------------------------------------------------------------------------####
	def startCalibrationCALLBACKmenu(self, valuesDict=None, typeId="", devId=0):
		valuesDict["cmd"]		 = "startCalibration"
		#self.indiLOG.log(20,"set calibration (1) ")
		if len(valuesDict["value"]) > 0:
			#self.indiLOG.log(20,"set calibration (2) ")
			try: 
				int(valuesDict["value"])
				theType = valuesDict["typeId"] 
				#self.indiLOG.log(20,"set calibration for sensirion co2 sensor : valuesDict:{}".format(valuesDict) )
				valuesDict["typeId"] = valuesDict["typeId"] + "." + valuesDict["value"]
				if theType in ["sensirionscd30","sensirionscd40"]:
					for dev in indigo.devices.iter("props.isSensorDevice"):
						#self.indiLOG.log(20,"set calibration checking typeId {}".format(dev.deviceTypeId) )
						if dev.deviceTypeId != theType: continue
						#self.indiLOG.log(20,"set calibration checking pi#:{}".format(dev.pluginProps["piServerNumber"] , valuesDict["piServerNumber"]) )
						if dev.pluginProps["piServerNumber"] != valuesDict["piServerNumber"]: continue
						props = dev.pluginProps
						if valuesDict["value"] != "400":
							props["autoCalibration"] = "0"
						else:
							props["autoCalibration"] = "1"
						dev.replacePluginPropsOnServer(props)
						self.setONErPiV(valuesDict["piServerNumber"], "piUpToDate", ["updateParamsFTP"])
						self.indiLOG.log(20,"{}  set calibration to autocalibration={}, co2_target = {} ".format(dev.name, props["autoCalibration"] , valuesDict["value"] ))
						self.sleep(2)
						break
			
			except Exception as e:
				self.exceptionHandler(40, e)

		self.setPin(valuesDict)


####-------------------------------------------------------------------------####
	def execAcceptNewBeaconsCALLBACKmenu(self, valuesDict=None, typeId="", devId=0):

		xx = valuesDict["acceptNewBeaconMAC"].upper()
		if self.acceptNewBeaconMAC != xx:
			if len(xx) > 0:
				if self.isValidMAC(xx):
					self.acceptNewBeaconMAC = xx
					self.pluginPrefs["acceptNewBeaconMAC"] = xx
					valuesDict["MSG"] = "mac={}".format(xx)
					self.setALLrPiV("piUpToDate", ["updateParamsFTP"])
					self.setALLrPiV("piUpToDate", ["updateParamsFTP"])
				else:
					xx = ""
					valuesDict["MSG"] = "bad mac number, rerenter"
			self.acceptNewBeaconMAC = xx
			self.pluginPrefs["acceptNewBeaconMAC"] = xx
			self.setALLrPiV("piUpToDate", ["updateParamsFTP"])
			return valuesDict

		if self.acceptNewTagiBeacons != valuesDict["acceptNewTagiBeacons"]:
			self.setALLrPiV("piUpToDate", ["updateParamsFTP"])
		self.acceptNewTagiBeacons = valuesDict["acceptNewTagiBeacons"]
		self.pluginPrefs["acceptNewTagiBeacons"] = valuesDict["acceptNewTagiBeacons"]


		if len(valuesDict["acceptNewMFGNameBeaconsText"]) >1:
			valuesDict["acceptNewMFGNameBeacons"] = valuesDict["acceptNewMFGNameBeaconsText"]

		if self.acceptNewMFGNameBeacons != valuesDict["acceptNewMFGNameBeacons"]:
			self.setALLrPiV("piUpToDate", ["updateParamsFTP"])
		self.acceptNewMFGNameBeacons = valuesDict["acceptNewMFGNameBeacons"]
		self.pluginPrefs["acceptNewMFGNameBeacons"] = valuesDict["acceptNewMFGNameBeacons"]


		if "{}".format(self.acceptNewiBeacons) != valuesDict["acceptNewiBeacons"]:
			self.setALLrPiV("piUpToDate", ["updateParamsFTP"])
			try: 	xxx = int(valuesDict["acceptNewiBeacons"])
			except: xxx = 999 # do not accept new beacons
			self.acceptNewiBeacons = xxx
			self.pluginPrefs["acceptNewiBeacons"] = xxx

		valuesDict["MSG"] = "RSSI >{}; Tag={}, MfgName:{}".format(valuesDict["acceptNewiBeacons"], valuesDict["acceptNewTagiBeacons"], valuesDict["acceptNewMFGNameBeacons"])
		return valuesDict

####-------------------------------------------------------------------------####
	def printBLEAnalysisCALLBACKmenu(self, valuesDict=None, typeId="", devId=0):
		valuesDict["cmd"]	 			= "BLEAnalysis"
		valuesDict["typeId"]	 		= valuesDict["minRSSI"]
		self.setPin(valuesDict)
		valuesDict["MSG"]	 			= "send to rpi#:{}, minRSSI:{}".format(valuesDict["piServerNumber"],valuesDict["minRSSI"])
		return valuesDict
####-------------------------------------------------------------------------####
	def printtrackMacCALLBACKmenu(self, valuesDict=None, typeId="", devId=0):


		mac = valuesDict["mac"].upper()
		existingMAC = valuesDict["existingMAC"].upper()
		valuesDict["typeId"] = mac
		if mac != "*":
			if not self.isValidMAC(mac):
				if not self.isValidMAC(existingMAC):
					valuesDict["MSG"]	= "bad MAC number"
					return valuesDict
				else:
					valuesDict["typeId"]	= existingMAC


		valuesDict["cmd"]	 	= "trackMac"
		self.setPin(valuesDict)
		valuesDict["MSG"] 		= "cmd sub. for:"+ valuesDict["typeId"]
		return valuesDict

####-------------------------------------------------------------------------####
	def setnewMessageCALLBACKmenu(self, valuesDict=None, typeId="", devId=0):
		valuesDict["cmd"]		 = "newMessage"
		self.setPin(valuesDict)

####-------------------------------------------------------------------------####
	def setresetDeviceCALLBACKmenu(self, valuesDict=None, typeId="", devId=0):
		valuesDict["cmd"]		 = "resetDevice"
		self.setPin(valuesDict)
		if valuesDict["typeId"] != "rainSensorRG11": return

		# reseting plugin data for rain sensor:
		piServerNumber = int(valuesDict["piServerNumber"] )
		for dev in indigo.devices.iter("props.isSensorDevice"):
			if dev.deviceTypeId !="rainSensorRG11": continue

			for key in ["rainRate", "rainRateMinToday", "rainRateMaxToday", "rainRateMinYesterday", "rainRateMaxYesterday", "hourRain", "lasthourRain", "dayRain", "lastdayRain", "weekRain", "lastweekRain", "monthRain", "lastmonthRain", "yearRain", "lastyearRain"]:
				self.addToStatesUpdateDict(dev.id, key, 0)
			self.addToStatesUpdateDict(dev.id, "resetDate", datetime.datetime.now().strftime(_defaultDateStampFormat))
			self.executeUpdateStatesDict(onlyDevID=dev.id, calledFrom="setresetDeviceCALLBACKmenu")

			dev2 = indigo.devices[dev.id]
			props= dev2.pluginProps
			for key in ["hourRainTotal", "dayRainTotal" ,"weekRainTotal", "monthRainTotal", "yearRainTotal"]:
				props[key] = 0
			
			dev2.replacePluginPropsOnServer(props)
		return



####-------------------------------------------------------------------------####
	def setMyoutputCALLBACKmenu(self, valuesDict=None, typeId="", devId=0):
		valuesDict["typeId"]			 = "myoutput"
		valuesDict["cmd"]				 = "myoutput"
		self.setPin(valuesDict)

####-------------------------------------------------------------------------####
	def setMCP4725CALLBACKmenu(self, valuesDict=None, typeId="", devId=0):
		devId = int(valuesDict["outputDev"])
		dev = indigo.devices[devId]
		props = dev.pluginProps
		valuesDict["typeId"]			 = "setMCP4725"
		valuesDict["devId"]			 = dev.id
		valuesDict["i2cAddress"]		 = props["i2cAddress"]
		valuesDict["piServerNumber"]	 = props["address"].split("-")[1]
		#valuesDict["cmd"]				  = "analogWrite"
		self.setPin(valuesDict)

####-------------------------------------------------------------------------####
	def setPCF8591dacCALLBACKmenu(self, valuesDict=None, typeId="", devId=0):
		devId = int(valuesDict["outputDev"])
		dev = indigo.devices[devId]
		props = dev.pluginProps
		valuesDict["typeId"]			 = "setPCF8591dac"
		valuesDict["devId"]			 = dev.id
		valuesDict["i2cAddress"]		 = props["i2cAddress"]
		valuesDict["piServerNumber"]	 = props["address"].split("-")[1]
		#valuesDict["cmd"]				  = "analogWrite"
		self.setPin(valuesDict)


####-------------------------------------------------------------------------####


# noinspection SpellCheckingInspection
	def actionControlDimmerRelay(self, action, dev0):
		try:
			#self.indiLOG.log(10,"sent \"{}\"  deviceAction:{}".format(dev0.name, action.deviceAction) )


			props0 = dev0.pluginProps
			if dev0.deviceTypeId == "neopixel-dimmer":
				valuesDict={}

				try:
						devNEO		= indigo.devices[int(props0["neopixelDevice"])]
						typeId		= devNEO.deviceTypeId
						devId		= devNEO.id
						propsNEO	= devNEO.pluginProps
						devTypeNEO	= propsNEO["devType"]
						try:
							xxx= propsNEO["devType"].split("x")
							ymax = int(xxx[0])
							xmax = int(xxx[1])
						except Exception as e:
							self.exceptionHandler(40, e)
							return
				except Exception as e:
					self.exceptionHandler(40, e)
					return

				if self.decideMyLog("OutputDevice"): self.indiLOG.log(5,"{}".format(action) )

				if not action.configured:
					self.indiLOG.log(10,"actionControlDimmerRelay neopixel-dimmer not enabled:{}".format("{}".format(dev0.name)) )
					return
				###action = dev.deviceAction
				if "pixelMenulist" in props0 and props0["pixelMenulist"] != "":
					position = props0["pixelMenulist"]
					if position.find("*") >-1:
						position='u["*","*"]'
				else:
					try:
						position = "["
						for ii in range(100):
							mmm = "pixelMenu{}".format(ii)
							if	mmm not in props0 or props0[mmm] =="":		continue
							if len(props0[mmm].split(",")) !=2:			continue
							position += "[{}],".format(props0[mmm])
						position  = position.strip(",") +"]"
						position = json.loads(position)
					except Exception as e:
						self.exceptionHandler(40, e)
						self.indiLOG.log(40,"position data: ".format(position))
						position=[]
				chList =[]


				RGB = [0,0,0,-1]

				channelKeys={"redLevel":0, "greenLevel":1, "blueLevel":2, "whiteLevel":3}
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

				#if "whiteLevel" in chList: del chList["whiteLevel"]
				self.execUpdateStatesList(dev0,chList)

				ppp =[]
				if "{}".format(position).find("*") > -1:
					ppp=["*", "*",RGB[0],RGB[1],RGB[2]]
				else:
					for p in position:
						p[0] = min(	 max((ymax-1),0),int(p[0])	)
						p[1] = min(	 max((xmax-1),0),int(p[1])	)
						ppp.append([p[0],p[1],RGB[0],RGB[1],RGB[2]])
				if "speedOfChange" in props0 and props0["speedOfChange"] !="":
					try:
						valuesDict["speedOfChange0"]		  = int(props0["speedOfChange"])
					except Exception as e:
						self.exceptionHandler(40, e)
				if self.decideMyLog("OutputDevice"): self.indiLOG.log(5,"props0 {}".format(props0) )

				valuesDict["outputDev"]			 = devId
				valuesDict["type0"]				 = "points"
				valuesDict["position0"]			 = json.dumps(ppp)
				valuesDict["display0"]			 = "immediate"
				valuesDict["reset0"]			 = ""
				valuesDict["restoreAfterBoot"]	 = "1"

				if self.decideMyLog("OutputDevice"): self.indiLOG.log(5,"valuesDict {}".format(valuesDict) )

				self.setneopixelCALLBACKmenu(valuesDict)

				return

			elif dev0.deviceTypeId == "OUTPUTswitchbotRelay":
				piU = props0["piServerNumber"]
				if action.deviceAction == indigo.kDimmerRelayAction.TurnOn:
											onOff = 1
				elif action.deviceAction == indigo.kDimmerRelayAction.Toggle:
					if not dev0.onState:	onOff = 1
					else:					onOff = 0
				elif action.deviceAction == indigo.kDimmerRelayAction.TurnOff:
											onOff = 0
				else:
					self.indiLOG.log(10,"action dimmer relay requested: for {} on pi:{};  command not supported:'{}; defined st req:'{}'".format(dev0.name, piU, action.deviceAction, indigo.kUniversalAction.RequestStatus))
					return 


				dev0.updateStateOnServer("status", "send: {}".format("on" if onOff == 1 else "off"))
	
				fileContents = {"mac":props0["mac"], "cmd":"onOff", "onOff":onOff,"mode":props0.get("gatMode","interactive")}

				toSend = [{"device": "OUTPUTswitchbotRelay", "command":"file", "fileName":"/home/pi/pibeacon/temp/switchbot.cmd", "fileContents":fileContents}]
				self.sendtoRPI(self.RPI[piU]["ipNumberPi"], piU, toSend, calledFrom="switchBotRelaySet")

				if self.decideMyLog("UpdateRPI"): self.indiLOG.log(10,"action dimmer relay requested: for {} on pi:{}; text to send:{}".format(dev0.name, piU, textToSend))
				return 

			elif dev0.deviceTypeId in ["OUTPUTswitchbotCurtain","OUTPUTswitchbotCurtain3"]:
				piU = props0["piServerNumber"]
				moveTo = "position"
				position = 50
				if action.deviceAction == indigo.kDimmerRelayAction.TurnOn:
											moveTo = "close"
											position = 100
											self.addToStatesUpdateDict(dev0.id, "status","send pos=closed" )
				elif action.deviceAction == indigo.kDimmerRelayAction.TurnOff:
											moveTo = "open"
											position = 0
											self.addToStatesUpdateDict(dev0.id, "status","send pos=open")
				elif action.deviceAction == indigo.kDeviceAction.SetBrightness:
											moveTo = "position"
											position = action.actionValue
											self.addToStatesUpdateDict(dev0.id, "status","send pos={}".format(position) )

				else:
					self.indiLOG.log(10,"action dimmer relay requested: for {} on pi:{};  command not supported:'{}; defined st req:'{}'".format(dev0.name, piU, action.deviceAction, indigo.kUniversalAction.RequestStatus))
					return 

				fileContents = {"mac":props0["mac"], "cmd":"moveTo", "moveTo":moveTo, "position":position, "mode":"interactive"}

				toSend = [{"device": dev0.deviceTypeId, "command":"file", "fileName":"/home/pi/pibeacon/temp/switchbot.cmd", "fileContents":fileContents}]
				self.sendtoRPI(self.RPI[piU]["ipNumberPi"], piU, toSend, calledFrom="switchBotCurtainSet")

				if self.decideMyLog("UpdateRPI"): self.indiLOG.log(10,"action dimmer relay requested: for {} on pi:{}; text to send:{}".format(dev0.name, piU, textToSend))
				return 

			#####  GPIO
			else:
				dev= dev0
			props = dev.pluginProps

			if self.decideMyLog("OutputDevice"): self.indiLOG.log(5,"deviceAction \n{}\n props {}".format(action, props))
			valuesDict={}
			valuesDict["outputDev"] = dev.id
			valuesDict["piServerNumber"] = props["piServerNumber"]
			valuesDict["deviceDefs"]	  = props["deviceDefs"]
			if dev.deviceTypeId =="OUTPUTgpio-1-ONoff":
				valuesDict["typeId"]	  = "OUTPUTgpio-1-ONoff"
				typeId					  = "OUTPUTgpio-1-ONoff"
			else:
				valuesDict["typeId"]	  = "OUTPUTgpio-1"
				typeId					  = "OUTPUTgpio-1"
			if "deviceDefs" in props:
				dd = json.loads(props["deviceDefs"])
				if len(dd) >0 and "gpio" in dd[0]:
					valuesDict["GPIOpin"]	  = dd[0]["gpio"]
				elif "gpio" in props:
					valuesDict["GPIOpin"] = props["gpio"]
				else:
					self.indiLOG.log(10,"deviceAction error, gpio not defined action={}\n props {}".format(action.replace("\n",""), props) )
			elif "gpio" in props:
				valuesDict["GPIOpin"] = props["gpio"]
			else:
				self.indiLOG.log(10,"deviceAction error, gpio not defined action={}\n props {}".format(action.replace("\n",""), props) )



			###### TURN ON ######
			if action.deviceAction == indigo.kDimmerRelayAction.TurnOn:
				valuesDict["cmd"] = "up"

			###### TURN OFF ######
			elif action.deviceAction == indigo.kDimmerRelayAction.TurnOff:
				valuesDict["cmd"] = "down"

			###### TOGGLE ######
			elif action.deviceAction == indigo.kDimmerRelayAction.Toggle:
				newOnState = not dev.onState
				if newOnState: valuesDict["cmd"] = "up"
				else:		   valuesDict["cmd"] = "down"

			###### SET BRIGHTNESS ######
			elif action.deviceAction == indigo.kDimmerRelayAction.SetBrightness:
				newBrightness = action.actionValue
				valuesDict["cmd"] = "analogWrite"
				valuesDict["analogValue"] = "{}".format(float(newBrightness))


			###### BRIGHTEN BY ######
			elif action.deviceAction == indigo.kDimmerRelayAction.BrightenBy:
				newBrightness = dev.brightness + action.actionValue
				if newBrightness > 100:
					newBrightness = 100
				valuesDict["cmd"] = "analogWrite"
				valuesDict["analogValue"] = "{}".format(float(newBrightness))

			###### DIM BY ######
			elif action.deviceAction == indigo.kDimmerRelayAction.DimBy:
				newBrightness = dev.brightness - action.actionValue
				if newBrightness < 0:
					newBrightness = 0
				valuesDict["cmd"] = "analogWrite"
				valuesDict["analogValue"] = "{}".format(float(newBrightness))

			else:
				return

			self.setPinCALLBACKmenu(valuesDict, typeId)
			return
		except Exception as e:
			self.exceptionHandler(40, e)



####-------------------------------------------------------------------------####
	def actionControlGeneral(self, action, dev):
		###### STATUS REQUEST ######
		#if action.deviceAction == indigo.kDeviceGeneralAction.RequestStatus:
		self.indiLOG.log(30,"actionControlGeneral \"{}\"  status request:{}".format(dev.name, action) )

####-------------------------------------------------------------------------####
	def setBacklightBrightness(self, pluginAction, dev):
		return

####-------------------------------------------------------------------------####
	def confirmdeviceIDOUTPUTBUTTONmenu(self, valuesDict=None, typeId="", devId=""):
		try:
			devId = int(valuesDict["outputDev"])
			dev = indigo.devices[devId]
			self.outdeviceForOUTPUTgpio = devId
		except:
			self.outdeviceForOUTPUTgpio = ""
		return valuesDict

####-------------------------------------------------------------------------####
	def filterINPUTpulseDevices(self, filter="", valuesDict=None, typeId="", devId=""):
			xList = [(-1,"do not use")]
			for dev in indigo.devices.iter("props.isSensorDevice"):
				if dev.deviceTypeId==  "INPUTpulse":
					xList.append((dev.id, "{}".format(dev.name)))
			return xList


####-------------------------------------------------------------------------####
	def filterINPUTdevices(self, filter="", valuesDict=None, typeId="", devId=""):
			xList = []
			for dev in indigo.devices.iter("props.isSensorDevice"):
				if dev.deviceTypeId.find("INPUTgpio") == -1 and dev.deviceTypeId.find("INPUTtouch") == -1 and dev.deviceTypeId.find("INPUTpulse") == -1 and dev.deviceTypeId.find("INPUTcoincidence") == -1: continue
				xList.append((dev.id, "{}".format(dev.name)))
			return xList




####-------------------------------------------------------------------------####
	def filterOUTPUTdevicesACTION(self, filter="", valuesDict=None, typeId="",devId=""):
		xList = []
		for dev in indigo.devices.iter("props.isOutputDevice"):
			if dev.deviceTypeId.find("OUTPUTgpio") ==-1: continue
			xList.append((dev.id,"{}".format(dev.name)))
		return xList
####-------------------------------------------------------------------------####
	def filterOUTPUTrelaydevicesACTION(self, filter="", valuesDict=None, typeId="",devId=""):
		xList = []
		for dev in indigo.devices.iter("props.isOutputDevice"):
			if dev.deviceTypeId.find("OUTPUTi2cRelay") ==-1: continue
			xList.append((dev.id,"{}".format(dev.name)))
		return xList

####-------------------------------------------------------------------------####
	def filterOUTPUTchannelsACTION(self, filter="", valuesDict=None, typeId="", devId=""):
		okList = []
		#self.indiLOG.log(10,	"self.outdeviceForOUTPUTgpio {}".format(self.outdeviceForOUTPUTgpio))
		if self.outdeviceForOUTPUTgpio =="": return []
		try:	dev = indigo.devices[int(self.outdeviceForOUTPUTgpio)]
		except: return []
		try:
			props= dev.pluginProps
			gpioList= json.loads(props["deviceDefs"])
			xList = copy.deepcopy(_GlobalConst_allGPIOlist)
			#self.indiLOG.log(10,	"gpioList {}".format(props))
			for ll in xList:
				if ll[0] =="0": continue
				#self.indiLOG.log(10,	"ll {}".format(ll))
				for ii in range(len(gpioList)):
					if "gpio" not in  gpioList[ii]: continue
					if gpioList[ii]["gpio"] != ll[0]: continue
					okList.append((ll[0], "OUTPUT_{}".format(ii)+" "+ll[1]))
					break
			#self.indiLOG.log(10, "{}".format(okList))
		except Exception as e:
			self.exceptionHandler(40, e)
		return okList


####-------------------------------------------------------------------------####
	def filterTimezones(self, filter="", valuesDict=None, typeId="", devId=""):

		timeZones =[]
		xxx=[]
		for ii in range(-12,13):
			if ii<0:
				timeZones.append("/Etc/GMT+{}".format(abs(ii)))
			else:
				timeZones.append("/Etc/GMT-{}".format(ii))
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
				xxx.append(("{}".format(ii-12)+" "+timeZones[ii], "+{}".format(abs(ii-12))+" "+timeZones[ii]))
			else:
				xxx.append(("{}".format(ii-12)+" "+timeZones[ii], ("{}".format(ii-12))+" "+timeZones[ii]))
		xxx.append(("99 -", "do not set"))
		return xxx

####-------------------------------------------------------------------------####
	def setSWITCHBOTBOTCALLBACKmenu(self, valuesDict=None, typeId=""):
		try:
			devId = int(valuesDict["outputDev"])
			dev = indigo.devices[devId]
			props = dev.pluginProps
			piU = props["piServerNumber"]
		except:
			self.indiLOG.log(10,"device not properly defined, please define OUTPUT ")
			return valuesDict

		fileContents = {"mac":props["mac"], "cmd":"setParameters",  "setParameters":True, "outputDev":  dev.id, "mode":"interactive"}
		textToSend = [{"device": "OUTPUTswitchbotRelay", "command":"file", "fileName":"/home/pi/pibeacon/temp/switchbot.cmd", "fileContents":fileContents}]
		self.sendtoRPI(self.RPI[piU]["ipNumberPi"], piU, textToSend, calledFrom="switchBotRelaySet")
		if self.decideMyLog("UpdateRPI"): self.indiLOG.log(10,"action set switchbot params requested: for {} on pi:{}; text to send:{}".format(dev.name, piU, textToSend))
		return 


####-------------------------------------------------------------------------####
	def sendPulsesToSwitchBotCALLBACKaction(self, action1=None, typeId=""):
		self.sendPulsesToSwitchBotCALLBACKmenu(valuesDict=action1.props)
		return 


####-------------------------------------------------------------------------####
	def sendPulsesToSwitchBotCALLBACKmenu(self, valuesDict=None, typeId=""):
		try:
			devId = int(valuesDict["outputDev"])
			dev = indigo.devices[devId]
			props = dev.pluginProps
			piU = props["piServerNumber"]
		except:
			self.indiLOG.log(10,"device not properly defined, please define OUTPUT ")
			return valuesDict
		if valuesDict.get("stop","0") != "0":
			fileContents = {"mac":props["mac"],"stop":True,"stopActionsForSeconds": float(valuesDict.get("stopActionsForSeconds","0"))}
		else:
			repeat 			= int(valuesDict.get("repeat","0"))
			repeatDelay		= float(valuesDict.get("repeatDelay","0"))
			pulses 			= int(valuesDict.get("pulses","1"))
			pulseLengthOn	= float(valuesDict.get("pulseLengthOn","0"))
			pulseLengthOff	= float(valuesDict.get("pulseLengthOff","0"))
			pulseDelay		= float(valuesDict.get("pulseDelay","0"))
			fileContents = {"mac":props["mac"],"cmd":"pulses","pulses":pulses, "pulseLengthOn":pulseLengthOn, "pulseLengthOff":pulseLengthOff, "pulseDelay":pulseDelay, "repeat":repeat, "repeatDelay":repeatDelay, "outputDev":  dev.id, "mode":"interactive"}

		textToSend = [{"device": "OUTPUTswitchbotRelay", "command":"file", "fileName":"/home/pi/pibeacon/temp/switchbot.cmd", "fileContents":fileContents}]
		self.sendtoRPI(self.RPI[piU]["ipNumberPi"], piU, textToSend, calledFrom="switchBotRelaySet")
		#self.indiLOG.log(10,"action set switchbot params requested: for {} on pi:{}; text to send:{}, valuesDict:{}".format(dev.name, piU, textToSend, valuesDict))

		#if self.decideMyLog("Special"): self.indiLOG.log(10,"action set switchbot params requested: for {} on pi:{}; text to send:{}".format(dev.name, piU, textToSend))
		return 




####-------------------------------------------------------------------------####
	def setPinCALLBACKmenu(self, valuesDict=None, typeId=""):
		#self.indiLOG.log(10,	"{}".format(valuesDict))

		try:
			devId = int(valuesDict["outputDev"])
			dev = indigo.devices[devId]
			props = dev.pluginProps
			valuesDict["piServerNumber"] = props["piServerNumber"]
			if "deviceDefs" not in props:
				self.indiLOG.log(10,"deviceDefs not in valuesDict, need to define OUTPUT device properly " )
				return valuesDict
			valuesDict["deviceDefs"] = props["deviceDefs"]
		except:
			self.indiLOG.log(10,"device not properly defined, please define OUTPUT ")
			return valuesDict

		#self.outdeviceForOUTPUTgpio = ""
		dev = indigo.devices[devId]
		props = dev.pluginProps
		valuesDict["typeId"]	  = dev.deviceTypeId
		valuesDict["devId"]	  = devId
		if "i2cAddress" in props:
			valuesDict["i2cAddress"]	  = props["i2cAddress"]
		if self.decideMyLog("OutputDevice"): self.indiLOG.log(5,"setPinCALLBACKmenu  valuesDict\n{}".format(valuesDict))
		self.setPin(valuesDict)


####-------------------------------------------------------------------------####
	def setDelay(self, startAtDateTimeIN=""):
		startAtDateTimeIN = "{}".format(startAtDateTimeIN)
		if  self.decideMyLog("OutputDevice"): self.indiLOG.log(5,"startAtDateTimeIN: {}".format(startAtDateTimeIN))
		try:
			#  12345678901234567
			#  1679646670.466054
			#  2022-12-03 14:12:12
			if len(startAtDateTimeIN) == 0 :  return 0
			lsTime = len(startAtDateTimeIN)
			if (lsTime < 11 and startAtDateTimeIN.find(":") == -1 and startAtDateTimeIN.find("-") == -1) or (
					startAtDateTimeIN.find(".") >-1 and 9 < lsTime < 14):	## max 9,999,999 = 120 days, vs 2014 12 12 0 0 00 date string
					try:
						sd =   float(startAtDateTimeIN)
						if sd < 1:
							return	0
						return	sd
					except:
						return 0
			else:
				try:
					if self.decideMyLog("OutputDevice"): self.indiLOG.log(5,"startAtDateTimeIN: doing datetime")
					startAtDateTime	   = startAtDateTimeIN.replace("-","").replace(":","").replace(" ","").replace("/","").replace(".","").replace(",","")
					startAtDateTime	   = startAtDateTime.ljust(14,"0")
					return	 max(0, self.getTimetimeFromDateString(startAtDateTime, fmrt= "%Y%m%d%H%M%S") - time.time() )
				except Exception as e:
					self.exceptionHandler(40, e)
					return 0
		except Exception as e:
			self.exceptionHandler(40, e)
		return 0



####-------------------------------------------------------------------------####
	def setPin(self, valuesDict=None):
		#self.indiLOG.log(10,	"{}".format(valuesDict))

		#self.outdeviceForOUTPUTgpio =""
		try:
			if "piServerNumber" not in valuesDict:
				self.indiLOG.log(10,"setPIN missing parameter: piServerNumber not defined")
				return
			piU = valuesDict["piServerNumber"]
			pi = int(piU)
			if piU not in _rpiList:
				self.indiLOG.log(10,"setPIN bad parameter: piServerNumber out of range: {} ".format(piU))
				return

			if self.RPI[piU]["piOnOff"] != "1":
				self.indiLOG.log(10,"setPIN bad parameter: piServer is not enabled: {} ".format(piU))
				return

			try:
				if not indigo.devices[int(self.RPI[piU]["piDevId"])].enabled:
					return
			except:
				return

			ip = self.RPI[piU]["ipNumberPi"]
			if "typeId" in valuesDict:	typeId = valuesDict["typeId"]
			else:						typeId = ""

			startAtDateTime = 0
			if "startAtDateTime" in valuesDict:
				startAtDateTime = self.setDelay(startAtDateTimeIN=valuesDict["startAtDateTime"])

			restoreAfterBoot = valuesDict.get("restoreAfterBoot","0")
			if "{}".format(restoreAfterBoot) not in ["0","1"]: 
				if restoreAfterBoot in [True,"True","true"]: restoreAfterBoot = "1"
				if restoreAfterBoot in [False,"False","false"]: restoreAfterBoot = "0"

			if "pulseUp"		 in valuesDict:
				try:
					pulseUp = float(valuesDict["pulseUp"])
				except:
					pulseUp = 0.
			else:
				pulseUp = 0.

			if "pulseDown"		   in valuesDict:
				try:
					pulseDown = float(valuesDict["pulseDown"])
				except:
					pulseDown = 0.
			else:
				pulseDown = 0.

			if "nPulses"		 in valuesDict:
				try:
					nPulses = int(valuesDict["nPulses"])
				except:
					nPulses = 0
			else:
				nPulses = 0


			if "analogValue" in valuesDict:
				try:
					analogValue = float(valuesDict["analogValue"])
				except:
					analogValue = 0.
			else:
				analogValue = 0.

			if "rampTime" in valuesDict:
				try:
					rampTime = float(valuesDict["rampTime"])
				except:
					rampTime = 0.
			else:
				rampTime = 0.


			inverseGPIO = False

			if typeId == "myoutput":
				if "text" not in valuesDict:
					self.indiLOG.log(10,"setPIN bad parameter: text not supplied: for pi#" + piU)
					return

				if self.decideMyLog("OutputDevice"): self.indiLOG.log(5,	"sending command to rPi at " + ip + "; port: {}".format(self.rPiCommandPORT) + "; cmd: myoutput;    "+ valuesDict["text"]		)
				self.sendGPIOCommand(ip, pi, typeId, "myoutput",  text=valuesDict["text"])
				return


			if typeId == "playSound":
					if "soundFile" not in valuesDict:
						self.indiLOG.log(10,"setPIN bad parameter: soundFile not supplied: for pi#" + piU)
						return
					try:
						line = "\n##=======use this as a python script in an action group action :=====\n"
						line +="plug = indigo.server.getPlugin(\"com.karlwachs.piBeacon\")"
						line +="\nplug.executeAction(\"playSoundFile\" , props ={"
						line +="\n	 \"outputDev\":\"{}".format(valuesDict["outputDev"])+"\""
						line +="\n	,\"device\":\"{}".format(typeId)+"\""
						line +="\n	,\"restoreAfterBoot\":{}".format(restoreAfterBoot)
						line +="\n	,\"startAtDateTime\":\"{}".format(startAtDateTime)+"\""
						line +="\n	,\"cmd\":\""+valuesDict["cmd"]+"\""
						line +="\n	,\"soundFile\":\""+valuesDict["soundFile"]+"\"})\n"
						line+= "##=======	end	   =====\n"
						if self.decideMyLog("OutputDevice"): self.indiLOG.log(5,"\n"+line+"\n")
					except:
						if self.decideMyLog("OutputDevice"): self.indiLOG.log(5,	"sending command to rPi at " + ip + "; port: {}".format(self.rPiCommandPORT) + "; cmd: " + valuesDict["cmd"] + ";  " + valuesDict["soundFile"])
					self.sendGPIOCommand(ip, pi,typeId, valuesDict["cmd"], soundFile=valuesDict["soundFile"])
					return

			if "cmd" not in valuesDict:
				self.indiLOG.log(10," setPIN bad parameter: cmd not set:")
				return
			cmd = valuesDict["cmd"]

			if cmd not in _GlobalConst_allowedCommands:
				self.indiLOG.log(10," setPIN bad parameter: cmd bad:{}; allowed commands= {}".format(cmd, _GlobalConst_allowedCommands))
				return

			if cmd == "getBeaconParameters":
				#self.indiLOG.log(10,"sending command to rPi at {}; port: {}; cmd:{} ;  devices:{}, startAtDateTime:{}".format(pi, self.rPiCommandPORT, valuesDict["cmd"], valuesDict["typeId"], startAtDateTime) )
				self.sendGPIOCommand(ip, pi, valuesDict["typeId"], valuesDict["cmd"], startAtDateTime=startAtDateTime)
				return

			if cmd in ["beepBeacon", "updateTimeAndZone"]:
				if self.decideMyLog("OutputDevice") or self.decideMyLog("UpdateTimeAndZone") : self.indiLOG.log(5,"sending command to rPi at {}; port: {}; cmd:{} ;  devices:{}".format(pi, self.rPiCommandPORT, valuesDict["cmd"], valuesDict["typeId"]) )
				self.sendGPIOCommand(ip, pi, valuesDict["typeId"], valuesDict["cmd"], startAtDateTime=startAtDateTime )
				return

			if cmd == "newMessage":
				if "typeId" not in valuesDict:
					self.indiLOG.log(10,"setPIN bad parameter: typeId not supplied: for pi#{}".format(piU))
					return

				if self.decideMyLog("OutputDevice"): self.indiLOG.log(5,"sending command to rPi at {}; port: {}; cmd:{} ;  typeId:{}".format(piU, self.rPiCommandPORT, valuesDict["cmd"], valuesDict["typeId"]) )
				self.sendGPIOCommand(ip, pi, typeId, valuesDict["cmd"])
				return


			if cmd == "resetDevice":
				if "typeId" not in valuesDict:
					self.indiLOG.log(10,"setPIN bad parameter: typeId not supplied: for pi#{}".format(piU))
					return

				if self.decideMyLog("OutputDevice"): sself.indiLOG.log(5,"sending command to rPi at {}; port: {}; cmd:{} ;  typeId:{}".format(piU, self.rPiCommandPORT, valuesDict["cmd"], valuesDict["typeId"]) )
				self.sendGPIOCommand(ip, pi, typeId, valuesDict["cmd"])
				return

			if cmd == "startCalibration":
				if "typeId" not in valuesDict:
					self.indiLOG.log(10,"setPIN bad parameter: typeId not supplied: for pi#{}".format(piU))
					return

				if True:  self.indiLOG.log(10,"sending command to rPi at {}; port: {}; cmd:{} ;  typeId:{}".format(piU, self.rPiCommandPORT, valuesDict["cmd"], valuesDict["typeId"]) )
				self.sendGPIOCommand(ip, pi, typeId, valuesDict["cmd"])
				return
			if cmd == "BLEAnalysis":
				if True:  self.indiLOG.log(10,"sending command to rPi at {}; port: {}; cmd:{} ".format(ip, self.rPiCommandPORT, valuesDict["cmd"]) )
				self.sendGPIOCommand(ip, pi, typeId, valuesDict["cmd"])
				return
			if cmd == "trackMac":
				if True:  self.indiLOG.log(10,"sending command to rPi at {}; port: {}; cmd:{} ".format(ip, self.rPiCommandPORT, valuesDict["cmd"]) )
				self.sendGPIOCommand(ip, pi, typeId, valuesDict["cmd"])
				return


			try:
				devIds = "{}".format(valuesDict["devId"])
				devId = int(devIds)
				dev = indigo.devices[devId]
				props=dev.pluginProps
			except:
				self.indiLOG.log(10," setPIN bad parameter: OUTPUT device not created: for pi#{}".format(piU))
				return

			if typeId in ["setMCP4725", "setPCF8591dac"]:
				try:
					i2cAddress = props["i2cAddress"]
					out = ""
					# _GlobalConst_allowedCommands		=["up", "down", "pulseUp", "pulseDown", "continuousUpDown", "disable"]	# commands support for GPIO pins
					if cmd == "analogWrite":
						out = cmd
					elif cmd == "pulseUp":
						out = cmd + ",{}".format(pulseUp)
					elif cmd == "pulseDown":
						out = cmd + ",{}".format(pulseDown)
					elif cmd == "continuousUpDown":
						out = cmd + ",{}".format(pulseUp) + "{}".format(pulseUp) + ",{}".format(nPulses)
					out += cmd + ",{}".format(analogValue)
					out += cmd + ",{}".format(rampTime)
					if "writeOutputToState" not in props or ("writeOutputToState" in props and props["writeOutputToState"] == "1"): self.addToStatesUpdateDict(dev.id, "OUTPUT", out)
				except Exception as e:
					self.exceptionHandler(40, e)
					outN = 0
				try:
					line = "\n##=======use this as a python script in an action group action :=====\n"
					line +="plug = indigo.server.getPlugin(\"com.karlwachs.piBeacon\")"
					line +="\nplug.executeAction(\"set"+typeId+"\" , props ={"
					line +="\n	 \"outputDev\":\"{}".format(valuesDict["outputDev"])+"\""
					line +="\n	,\"device\":\"{}".format(typeId)+"\""
					line +="\n	,\"restoreAfterBoot\":{}".format(restoreAfterBoot)
					line +="\n	,\"startAtDateTime\":\"{}".format(startAtDateTime)+"\""
					line +="\n	,\"cmd\":\""+valuesDict["cmd"]+"\""
					line +="\n	,\"pulseUp\":\"{}".format(pulseUp)+"\""
					line +="\n	,\"pulseDown\":\"{}".format(pulseDown)+"\""
					line +="\n	,\"rampTime\":\"{}".format(rampTime)+"\""
					line +="\n	,\"analogValue\":\"{}".format(analogValue)+"\"})\n"
					line +="##=======	end	   =====\n"
					if self.decideMyLog("OutputDevice"): self.indiLOG.log(5,"\n"+line+"\n")
				except:
					if self.decideMyLog("OutputDevice"): self.indiLOG.log(5,"sending command to rPi at " + ip + "; port: {}".format(self.rPiCommandPORT) +
							   "; cmd: {}".format(cmd) + ";  pulseUp: {}".format(pulseUp) + ";  pulseDown: " +
							   "{}".format(pulseDown) + ";  nPulses: {}".format(nPulses) + ";  analogValue: {}".format(analogValue)+ ";  rampTime: {}".format(rampTime)+
							   ";  restoreAfterBoot:{}".format(restoreAfterBoot)+ ";   startAtDateTime: " + startAtDateTime)

				self.sendGPIOCommand(ip, pi, typeId, cmd, i2cAddress=i2cAddress,pulseUp=pulseUp, pulseDown=pulseDown, nPulses=nPulses, analogValue=analogValue,rampTime=rampTime, restoreAfterBoot=restoreAfterBoot, startAtDateTime=startAtDateTime, inverseGPIO =inverseGPIO, devId=devId )
				self.executeUpdateStatesDict(onlyDevID=dev.id, calledFrom="setPin")
				return

			if typeId.find("OUTPUTgpio") > -1 or typeId.find("OUTPUTi2cRelay") > -1:
				i2cAddress = ""
				if "i2cAddress" in valuesDict:
					i2cAddress = valuesDict["i2cAddress"]
				if "GPIOpin" in valuesDict:
					GPIOpin = valuesDict["GPIOpin"]
					deviceDefs = json.loads(valuesDict["deviceDefs"])
					output="0"
					for nn in range(len(deviceDefs)):
						if "gpio" in deviceDefs[nn]:
							if GPIOpin == deviceDefs[nn]["gpio"] :
								output= "{}".format(nn)
								break
				elif  "OUTPUT" in valuesDict:
					output = int(valuesDict["OUTPUT"])
					deviceDefs = json.loads(valuesDict["deviceDefs"])
					if output <= len(deviceDefs):
						if "gpio" in deviceDefs[output]:
							GPIOpin = deviceDefs[output]["gpio"]
						else:
							self.indiLOG.log(10," setPIN bad parameter: no GPIOpin defined:{}".format(valuesDict))
							return
					else:
						self.indiLOG.log(10," setPIN bad parameter: no GPIOpin defined:{}".format(valuesDict))
						return
				else:
					self.indiLOG.log(10," setPIN bad parameter: no GPIOpin defined:{}".format(valuesDict))
					return

				#self.indiLOG.log(20,"{}:  valuesDict:{}".format(dev.name, valuesDict))
				if "inverseGPIO" in valuesDict:  # overwrite individual defs  if explicitely inverse defined
					try: 											inverseGPIO = (valuesDict["inverseGPIO"])
					except:											inverseGPIO = False
				else:
					#self.indiLOG.log(20," deviceDefs[int(output)]:{}".format(deviceDefs[int(output)]))
					if deviceDefs[int(output)]["outType"] == "0":	inverseGPIO = False
					else:										  	inverseGPIO = True

				if typeId == "OUTPUTgpio-1":
					analogValue = float(analogValue)
					b = ""
					if cmd == "up":
						b = 100
					elif cmd == "down":
						b = 0
					elif cmd == "analogWrite":
						b = int(float(analogValue))
					if b != "" and "onOffState" in dev.states:
						self.addToStatesUpdateDict(dev.id, "brightnessLevel", b)
						if b >1:
							self.addToStatesUpdateDict(dev.id, "onOffState", True)
						else:
							self.addToStatesUpdateDict(dev.id, "onOffState", False)
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
					if b != "" and "onOffState" in dev.states:
						if b >1:
							self.addToStatesUpdateDict(dev.id, "onOffState", True)
						else:
							self.addToStatesUpdateDict(dev.id, "onOffState", False)
				if typeId == "OUTPUTi2cRelay":
					b = ""
					if cmd == "up":
						b = 100
					elif cmd == "down":
						b = 0
					if b != "" and "onOffState" in dev.states:
						if b >1:
							self.addToStatesUpdateDict(dev.id, "onOffState", True)
						else:
							self.addToStatesUpdateDict(dev.id, "onOffState", False)


				try:
					out = ""
					# _GlobalConst_allowedCommands		=["up", "down", "pulseUp", "pulseDown", "continuousUpDown", "disable"]	# commands support for GPIO pins
					if cmd == "up" or cmd == "down":
						out = cmd
					elif cmd == "pulseUp":
						out = cmd + ",{}".format(pulseUp)
					elif cmd == "pulseDown":
						out = cmd + ",{}".format(pulseDown)
					elif cmd == "continuousUpDown":
						out = cmd + ",{}".format(pulseUp) + ",{}".format(pulseUp) + ",{}".format(nPulses)
					elif cmd == "rampUp" or cmd == "rampDown" or cmd == "rampUpDown":
						out = cmd + ",{}".format(pulseUp) + ",{}".format(pulseUp) + ",{}".format(nPulses)+ ",{}".format(rampTime)
					elif cmd == "analogWrite":
						out = cmd + ",{}".format(analogValue)
					outN = int(output)
					if "OUTPUT_{:02d}".format(outN) in dev.states: self.addToStatesUpdateDict(dev.id, "OUTPUT_{:02d}".format(outN), out)
					if "OUTPUT" in dev.states and ("writeOutputToState" not in props or ("writeOutputToState" in props and props["writeOutputToState"] == "1") ): self.addToStatesUpdateDict(dev.id, "OUTPUT", out)
				except Exception as e:
					self.exceptionHandler(40, e)
					outN = 0
				try:
					line = "\n##=======use this as a python script in an action group action :=====\n"
					line +="plug = indigo.server.getPlugin(\"com.karlwachs.piBeacon\")"
					line +="\nplug.executeAction(\"setPins\" , props ={"
					line +="\n	 \"outputDev\":\"{}".format(valuesDict["outputDev"])+"\""
					line +="\n	,\"device\":\"{}".format(typeId)+"\""
					line +="\n	,\"restoreAfterBoot\":{}".format(restoreAfterBoot)
					line +="\n	,\"startAtDateTime\":\"{}".format(startAtDateTime)+"\""
					line +="\n	,\"cmd\":\""+valuesDict["cmd"]+"\""
					line +="\n	,\"pulseUp\":\"{}".format(pulseUp)+"\""
					line +="\n	,\"pulseDown\":\"{}".format(pulseDown)+"\""
					line +="\n	,\"rampTime\":\"{}".format(rampTime)+"\""
					line +="\n	,\"analogValue\":\"{}".format(analogValue)+"\""
					line +="\n	,\"i2cAddress\":\"{}".format(i2cAddress)+"\""
					line +="\n	,\"GPIOpin\":\"{}".format(GPIOpin)+"\"})\n"
					line+= "##=======  end  =====\n"
					if self.decideMyLog("OutputDevice"): self.indiLOG.log(5,"\n"+line+"\n")
				except:
					if self.decideMyLog("OutputDevice"): self.indiLOG.log(5,"sending command to rPi at " + ip + "; port: {}".format(self.rPiCommandPORT) + " pin: " +
							   "{}".format(GPIOpin) + "; GPIOpin: {}".format(GPIOpin) + "OUTPUT#{}".format(outN) + "i2cAddress{}".format(i2cAddress) + "; cmd: " +
							   "{}".format(cmd) + ";  pulseUp: {}".format(pulseUp) + ";  pulseDown: " +
							   "{}".format(pulseDown) + "; nPulses: {}".format(nPulses) + "; analogValue: {}".format(analogValue)+ "; rampTime: {}".format(rampTime)+ ";  restoreAfterBoot: {}".format(restoreAfterBoot)+ "; startAtDateTime: " + startAtDateTime)

				self.sendGPIOCommand(ip, pi, typeId, cmd, GPIOpin=GPIOpin, i2cAddress=i2cAddress, pulseUp=pulseUp, pulseDown=pulseDown, nPulses=nPulses, analogValue=analogValue, rampTime=rampTime, restoreAfterBoot=restoreAfterBoot, startAtDateTime=startAtDateTime, inverseGPIO =inverseGPIO, devId=devId )
				self.executeUpdateStatesDict(onlyDevID= devIds, calledFrom="setPin END")
				return

			self.indiLOG.log(10,"setPIN:   no condition met, returning")

		except Exception as e:
			self.exceptionHandler(40, e)

####-------------------------------------------------------------------------####
	def buttonConfirmoldIPCALLBACK(self, valuesDict=None, typeId="", devId=0):
		piU = valuesDict["PINumberForIPChange"]
		valuesDict["oldipNumberPi"] = self.RPI[piU]["ipNumberPi"]
		valuesDict["newipNumberPi"] = self.RPI[piU]["ipNumberPi"]
		return valuesDict


####-------------------------------------------------------------------------####
	def buttonConfirmIPnumberCALLBACK(self, valuesDict=None, typeId="", devId=0):
		piU = valuesDict["PINumberForIPChange"]
		pi = int(piU)
		if valuesDict["oldipNumberPi"] != valuesDict["newipNumberPi"]:
			self.RPI[piU]["ipNumberPi"] = valuesDict["newipNumberPi"]
			self.setONErPiV(piU, "piUpToDate",["updateParamsFTP", "rebootSSH"])
			self.rPiRestartCommand[pi]		= "rebootSSH"  ## which part need to restart on rpi
		return valuesDict


	###########################		MENU   END #################################




	###########################		ACTION	#################################

####-------------------------------------------------------------------------####
	def sendConfigviaSocketCALLBACKaction(self, action1=None, typeId="", devId=0):
		try:
			v = action1.props
			if v["configurePi"] =="": return
			piU= "{}".format(v["configurePi"])
			ip= self.RPI[piU]["ipNumberPi"]
			if len(ip.split(".")) != 4:
				self.indiLOG.log(10,"sendingFile to rPI,  bad parameters:"+piU+"  "+ip+"  {}".format(v))
				return
			try:
				if not	indigo.devices[int(self.RPI[piS]["piDevId"])].enabled: return
			except:
				return

			fileContents = self.makeParametersFile(piS,retFile=True)
			if len(fileContents) >0:
				if self.decideMyLog("OutputDevice"): self.indiLOG.log(5,"sending parameters file via socket: {}".format(v)+" \n"+fileContents)
				self.sendFileToRPIviaSocket(ip,piU, "/home/pi/pibeacon/parameters", fileContents, fileMode="w")

		except Exception as e:
			self.exceptionHandler(40, e)
		return


####-------------------------------------------------------------------------####
	def sendExtraPagesToRpiViaSocketCALLBACKaction(self, action1=None, typeId="", devId=0):
		try:
			v = action1.props
			if v["configurePi"] =="": return
			piU= "{}".format(v["configurePi"])
			ip= self.RPI[piU]["ipNumberPi"]
			if len(ip.split(".")) != 4:
				self.indiLOG.log(10,"sendingFile to rPI,  bad parameters:"+piU+"  "+ip+"  {}".format(v))
				return
			try:
				if not	indigo.devices[int(self.RPI[piU]["piDevId"])].enabled: return
			except:
				return

			#if self.decideMyLog("OutputDevice"): self.indiLOG.log(5,"sending extrapage file via socket: {}".format(v))
			fileContents =[]
			#self.indiLOG.log(10, "{}".format(propsOut))
			for ii in range(10):
				if "extraPage{}".format(ii)+"Line0" in v and "extraPage{}".format(ii)+"Line1" in v and "extraPage{}".format(ii)+"Color" in v:
					line0 = self.convertVariableOrDeviceStateToText(v["extraPage{}".format(ii)+"Line0"])
					line1 = self.convertVariableOrDeviceStateToText(v["extraPage{}".format(ii)+"Line1"])
					color = self.convertVariableOrDeviceStateToText(v["extraPage{}".format(ii)+"Color"])
					fileContents.append([line0,line1,color])
			if len(fileContents) >0:
				self.sendFileToRPIviaSocket(ip, piU, "/home/pi/pibeacon/temp/extraPageForDisplay.inp",json.dumps(fileContents),fileMode="w",touchFile=False)

		except Exception as e:
			self.exceptionHandler(40, e)
		return

####-------------------------------------------------------------------------####
	def setPinCALLBACKaction(self, action1):
		valuesDict = action1.props
		try:
			try:
				devId = int(valuesDict["outputDev"])
				dev = indigo.devices[devId]
			except:
				try:
					dev = indigo.devices[valuesDict["outputDev"]]
					devId = dev.id
				except:
					self.indiLOG.log(10,"device not in valuesDict, need to define parameters properly ")
					return

			props = dev.pluginProps
			if "deviceDefs" not in props:
				self.indiLOG.log(10,"deviceDefs not in valuesDict, need to define OUTPUT device properly ")
				return
			valuesDict["deviceDefs"] = props["deviceDefs"]
			valuesDict["piServerNumber"] = props["piServerNumber"]
			if "i2cAddress" in props:
				valuesDict["i2cAddress"] = props["i2cAddress"]


		except:
			self.indiLOG.log(10,"setPinCALLBACKaction device not properly defined, please define OUTPUT ")
			return valuesDict
		valuesDict["typeId"]	= dev.deviceTypeId
		valuesDict["devId"] 	= devId
		#self.indiLOG.log(10,	"valuesDict {}".format(valuesDict))
		#self.indiLOG.log(20,"setPinCALLBACKaction outputdev:{}, valuesDict:{} ".format(dev.name, valuesDict))
		self.setPin(valuesDict)

		return

####-------------------------------------------------------------------------####
	def setMCP4725CALLBACKaction(self, action1):
		valuesDict = action1.props
		try:
			devId = int(valuesDict["outputDev"])
			dev = indigo.devices[devId]
		except:
			try:
				dev = indigo.devices[valuesDict["outputDev"]]
			except:
				self.indiLOG.log(10,"setMCP4725CALLBACKaction action put wrong, device name/id	not installed/ configured:{}".format(valuesDict))
				return

		props = dev.pluginProps
		typeId							= "setMCP4725"
		valuesDict["typeId"]			 = typeId
		valuesDict["devId"]			 = dev.id
		valuesDict["i2cAddress"]		 = props["i2cAddress"]
		valuesDict["piServerNumber"]	 = props["address"].split("-")[1]
		valuesDict["cmd"]				 = "analogWrite"
		self.setPin(valuesDict)
		return

####-------------------------------------------------------------------------####
	def setPCF8591dacCALLBACKaction(self, action1):
		valuesDict = action1.props
		try:
			devId = int(valuesDict["outputDev"])
			dev = indigo.devices[devId]
		except:
			try:
				dev = indigo.devices[valuesDict["outputDev"]]
			except:
				self.indiLOG.log(10,"setPCF8591dacCALLBACKaction action put wrong, device name/id  not installed/ configured:{}".format(valuesDict))
				return

		props = dev.pluginProps
		typeId							 = "setPCF8591dac"
		valuesDict["typeId"]			 = typeId
		valuesDict["devId"]			 = dev.id
		valuesDict["i2cAddress"]		 = props["i2cAddress"]
		valuesDict["piServerNumber"]	 = props["address"].split("-")[1]
		valuesDict["cmd"]				 = "analogWrite"
		self.setPin(valuesDict)
		return


####-------------------------------------------------------------------------####
	def startCalibrationCALLBACKaction(self, action1):
		valuesDict = action1.props
		valuesDict["cmd"] = "startCalibration"
		self.setPin(valuesDict)

####-------------------------------------------------------------------------####
	def setnewMessageCALLBACKaction(self, action1):
		valuesDict = action1.props
		valuesDict["cmd"] 				= "newMessage"
		self.setPin(valuesDict)
		valuesDict["cmd"]	 			= "resetDevice"

####-------------------------------------------------------------------------####
	def setresetDeviceCALLBACKAction(self, action1):
		valuesDict = action1.props
		valuesDict["cmd"]		 		= "resetDevice"
		self.setPin(valuesDict)

####-------------------------------------------------------------------------####
	def setMyoutputCALLBACKaction(self, action1):
		valuesDict = action1.props
		valuesDict["typeId"]			 = "myoutput"
		valuesDict["cmd"]				 = "myoutput"
		self.setPin(valuesDict)
		return

####-------------------------------------------------------------------------####
	def playSoundFileCALLBACKaction(self, action1):
		valuesDict = action1.props
		valuesDict["typeId"]			 = "playSound"
		valuesDict["cmd"]				 = "playSound"
		self.setPin(valuesDict)
		return

####-------------------------------------------------------------------------####
	def pauseSensorCALLBACKaction(self, action1):
		valuesDict = action1.props
		devId = valuesDict.get("selectSensor","")
		if devId == "": return 
		dev = indigo.devices[int(devId)]
		devType = dev.deviceTypeId 
		piU	 = dev.pluginProps.get("piServerNumber","")
		sleepFor = valuesDict.get("sleepFor","5")

		cmd1 = {"command": "file","fileName":"temp/pauseSensor","fileContents":{devType:sleepFor}}
		#self.indiLOG.log(20,"piu:{}, ip:{}, cmd1:{}".format(piU, self.RPI[piU]["ipNumberPi"], cmd1))
		self.sendtoRPI(self.RPI[piU]["ipNumberPi"], piU, [cmd1], calledFrom="pauseSensorCALLBACKaction")

		return
	###########################		ACTION	 END #################################


	###########################	   Config  #################################
####-------------------------------------------------------------------------####
	def XXgetPrefsConfigUiValues(self):
		valuesDict= indigo.Dict()
		valuesDict["piServerNumber"]  = 99
		valuesDict["ipNumberPi"]	   = "192.168.1.999"
		valuesDict["enablePiEntries"] = False
		return valuesDict

####-------------------------------------------------------------------------####
	def buttonConfirmPiServerCALLBACK(self, valuesDict=None, typeId=""):

		try:
			piU = valuesDict["piServerNumber"]
			pi = int(piU)
		except:
			return valuesDict
		self.selectedPiServer		  = pi
		if piU in  _rpiBeaconList:
			valuesDict["beaconOrSensor"] = "iBeacon and Sensor rPi"
		else:
			valuesDict["beaconOrSensor"] = "Sensor only rPi"
		usePassword = self.RPI[piU]["passwordPi"]
		if	self.RPI[piU]["passwordPi"] == "raspberry":
			for piU0 in self.RPI:
				if self.RPI[piU0]["passwordPi"] !="raspberry":
					usePassword = self.RPI[piU0]["passwordPi"]
					break
		valuesDict["passwordPi"]		 = usePassword

		useID = self.RPI[piU]["userIdPi"]
		if	self.RPI[piU]["userIdPi"] == "pi":
			for piU0 in self.RPI:
				if self.RPI[piU0]["userIdPi"] !="pi" and len(self.RPI[piU0]["userIdPi"]) > 1:
					useID = self.RPI[piU0]["userIdPi"]
					break
		valuesDict["userIdPi"]			 = useID

		valuesDict["ipNumberPi"]		 = self.RPI[piU]["ipNumberPi"]

		valuesDict["enablePiEntries"]	 = True
		valuesDict["piOnOff"]			 = self.RPI[piU]["piOnOff"]
		valuesDict["enableRebootCheck"] = self.RPI[piU]["enableRebootCheck"]
		valuesDict["MSG"]				 = "enter configuration"
		return valuesDict

####-------------------------------------------------------------------------####
	def buttonConfirmPiServerConfigCALLBACK(self, valuesDict=None, typeId="", devId=0):
		try:
			piU = valuesDict["piServerNumber"]
			pi = int(piU)
		#### check pi on/off
			p01 = valuesDict["piOnOff"]

			if p01 =="delete":
				self.delRPI(pi=pi, calledFrom="buttonConfirmPiServerConfigCALLBACK" )
				valuesDict["MSG"] = "Pi server deleted"
				return valuesDict

			if p01 == "0":  # off
				self.RPI[piU]["piOnOff"] = "0"
				self.resetUpdateQueue(piU)
				valuesDict["MSG"] = "Pi server disabled"
				try:
					dev= indigo.devices[self.RPI[piU]["piDevId"]]
					dev.enabled = False
					dev.replaceOnServer()
					self.stopOneUpdateRPIqueues(piU, reason="set RPI off")
				except:
					pass
				self.rePopulateStates = "save server config, set off / delete"
				return valuesDict

########## from here on it is ON
			dateString	= datetime.datetime.now().strftime(_defaultDateStampFormat)

		####### check ipnumber
			ipn = valuesDict["ipNumberPi"]
			if not self.isValidIP(ipn):
				valuesDict["MSG"] = "ip number not correct"
				return valuesDict

			# first test if already used somewhere else
			for piU3 in self.RPI:
				if piU == piU3: continue
				if self.RPI[piU3]["piOnOff"] == "0": continue
				if self.RPI[piU3]["ipNumberPi"] == ipn:
						valuesDict["MSG"] = "ip number already in use"
						self.indiLOG.log(30,"ip number already in use for ip:{} pi#selected:{}, pi#already exists:{}".format(ipn, piU, piU3 ))
						return valuesDict

			if self.RPI[piU]["ipNumberPi"]	  != ipn:
				self.RPI[piU]["ipNumberPi"]   = ipn
				self.setONErPiV(piU, "piUpToDate", ["updateParamsFTP"])

			#### check authkey vs std password ..
			self.RPI[piU]["authKeyOrPassword"] = valuesDict["authKeyOrPassword"]
			self.RPI[piU]["hostFileCheck"] = valuesDict.get("hostFileCheck","")


			#### check userid password ..
			if self.RPI[piU]["userIdPi"]	  != valuesDict["userIdPi"]:
				self.RPI[piU]["userIdPi"]	   = valuesDict["userIdPi"]
				self.setONErPiV(piU, "piUpToDate", ["updateParamsFTP"])

			if self.RPI[piU]["passwordPi"]	  != valuesDict["passwordPi"]:
				self.RPI[piU]["passwordPi"]   = valuesDict["passwordPi"]
				self.setONErPiV(piU, "piUpToDate", ["updateParamsFTP"])

			if self.RPI[piU]["enableRebootCheck"] != valuesDict["enableRebootCheck"]:
				self.RPI[piU]["enableRebootCheck"] = valuesDict["enableRebootCheck"]
				self.setONErPiV(piU, "piUpToDate", ["updateParamsFTP"])


			valuesDict["MSG"] = "Pi server configuration set"

			valuesDict["enablePiEntries"] = False
			if self.decideMyLog("UpdateRPI"): self.indiLOG.log(5,"buttonConfirmPiServerConfigCALLBACK... pi#=        {}".format(piU))
			if self.decideMyLog("UpdateRPI"): self.indiLOG.log(5,"valuesDict= {}".format(valuesDict))
			if self.decideMyLog("UpdateRPI"): self.indiLOG.log(5,"RPI=        {}".format(self.RPI[piU]))

			if piU in  _rpiBeaconList:
						if self.RPI[piU]["piDevId"] == 0: # check if  existing device
							found =False
							for dev in indigo.devices.iter("props.isRPIDevice"):
								try:
									if dev.description.split("-")[1] == piU:
										props=dev.pluginProps
										if props["ipNumberPi"] != ipn:
											props["ipNumberPi"] = ipn
					
											dev.replacePluginPropsOnServer(props)
											self.updateNeeded += "fixConfig"
											self.setONErPiV(piU, "piUpToDate", ["updateParamsFTP"])

										self.RPI[piU]["piDevId"] = dev.id
										found = True
										break
								except:
									pass
							if not found:
									self.indiLOG.log(20,"making new RPI: {};   ip: {}".format(pi, ipn))
									priProps			= copy.deepcopy(_GlobalConst_emptyrPiProps)
									priProps["RPINumber"] = piU
									priProps["ipNumberPi"] = ipn
									dev = indigo.device.create(
										protocol		= indigo.kProtocol.Plugin,
										address			= "00:00:00:00:pi:{:02d}".format(pi),
										name			= "Pi_{}".format(pi),
										description		= "Pi-{}-{}".format(pi,ipn),
										pluginId		= self.pluginId,
										deviceTypeId	= "rPI",
										folder			= self.piFolderId,
										props			= priProps
										)

									try:
										dev = indigo.devices[dev.id]
									except Exception as e:
										if "{}".format(e).find("timeout waiting") > -1:
											self.exceptionHandler(40, e)
											self.indiLOG.log(40,"communication to indigo is interrupted")
											return valuesDict
										if "{}".format(e).find("not found in database") ==-1:
											self.exceptionHandler(40, e)
											return valuesDict
										self.exceptionHandler(40, e)

									dev.updateStateImageOnServer(indigo.kStateImageSel.SensorOn)
									self.addToStatesUpdateDict(dev.id, "status", "expired")
									self.addToStatesUpdateDict(dev.id, "note", "Pi-" + piU)
									self.addToStatesUpdateDict(dev.id, "created",dateString)
									self.addToStatesUpdateDict(dev.id, "groupMember","PI")
									self.executeUpdateStatesDict(onlyDevID=dev.id, calledFrom="updateBeaconStates new rpi")
									self.RPI[piU]["piMAC"] = "00:00:00:00:pi:{:02d}".format(pi)
									self.RPI[piU]["piDevId"] = dev.id
									self.setGroupStatusNextCheck = -1

						else:
							try:
								dev= indigo.devices[self.RPI[piU]["piDevId"]]
							except Exception as e:
								if "{}".format(e).find("not found in database") >-1:
									priProps			= copy.deepcopy(_GlobalConst_emptyrPiProps)
									priProps["ipNumberPi"] = ipn
									dev = indigo.device.create(
										protocol		= indigo.kProtocol.Plugin,
										address			= "Pi-{:02d}".format(pi),
										name			= "Pi_{}".format(pi),
										description		= "Pi-{:02d}-{}".format(pi,ipn),
										pluginId		= self.pluginId,
										deviceTypeId	= "rPI",
										folder			= self.piFolderId,
										props			= priProps
										)
									self.RPI[piU]["piMAC"] = "00:00:00:00:pi:{:02d}".format(pi)
									self.RPI[piU]["piDevId"] = dev.id
									dev = indigo.devices[dev.id]
						props= dev.pluginProps
						self.addToStatesUpdateDict(dev.id, "note", "Pi-{}".format(pi))
						self.addToStatesUpdateDict(dev.id, "groupMember","PI")
						props["description"] 				= "Pi-{}-{}".format(pi,ipn)
						self.deviceStopCommIgnore 			= time.time()
						dev.replacePluginPropsOnServer(props)
						self.RPI[piU]["piOnOff"] 	= "1"
						dev.enabled = (p01 == "1")
						self.setGroupStatusNextCheck = -1

######
			if piU in _rpiSensorList:
						self.indiLOG.log(10,"rpiSensor checking  RPI: {};   ip:{}; piDevId:{}".format(pi, ipn, self.RPI[piU]["piDevId"]))
						if self.RPI[piU]["piDevId"] == 0: # check if  existing device
							found =False
							for dev in indigo.devices.iter("props.isRPISensorDevice"):
								if dev.address.split("-")[1] == piU:
									props=dev.pluginProps
									if props["ipNumberPi"] != ipn:
										props["ipNumberPi"] = ipn
				
										dev.replacePluginPropsOnServer(props)
										self.updateNeeded += "fixConfig"
										self.setONErPiV(piU, "piUpToDate", ["updateParamsFTP"])

									self.RPI[piU]["piDevId"] = dev.id
									found = True
									break
							if not found:
								self.indiLOG.log(10,"rpiSensor not found making new RPI")
								dev= indigo.device.create(
									protocol		= indigo.kProtocol.Plugin,
									address			= "Pi-"+piU,
									name			= "Pi_Sensor_" + piU,
									description		= "Pi-" + piU+"-"+ipn,
									pluginId		= self.pluginId,
									deviceTypeId	= "rPI-Sensor",
									folder			= self.piFolderId,
									props		= {
											"typeOfBeacon": "rPi-Sensor",
											"sendToIndigoSecs": 90,
											"shutDownPinInput" : "-1",
											"shutDownPinOutput" : "-1",
											"expirationTime" : "90",
											"isRPISensorDevice" : True,
											"SupportsStatusRequest": 	  _GlobalConst_emptyrPiProps["SupportsStatusRequest"],
											"AllowOnStateChange": 		  _GlobalConst_emptyrPiProps["AllowOnStateChange"],
											"AllowSensorValueChange":    _GlobalConst_emptyrPiProps["AllowSensorValueChange"],
											"fastDown" : "-1",
											"RPINumber" : piU,
											"ipNumberPi":ipn}
									)
								dev = indigo.devices[dev.id]
								self.addToStatesUpdateDict(dev.id, "created",datetime.datetime.now().strftime(_defaultDateStampFormat))
								self.addToStatesUpdateDict(dev.id, "note", "Pi-" + piU)
								self.RPI[piU]["piDevId"] = dev.id
								self.updateNeeded += "fixConfig"
								self.setONErPiV(piU, "piUpToDate", ["updateParamsFTP"])
								try: self.indiLOG.log(10,"rpiSensor created:{}, in folder:{}".format(dev.name,indigo.devices.folders.getName(self.piFolderId)))
								except: pass
						else:
							self.indiLOG.log(10,"rpiSensor exists, no need to make new one")
							try:
								dev= indigo.devices[self.RPI[piU]["piDevId"]]
							except Exception as e:
								self.indiLOG.log(10,"rpiSensor .. does not exists, failed to find")
								if "{}".format(e).find("not found in database") >-1:
									dev= indigo.device.create(
										protocol		= indigo.kProtocol.Plugin,
										address			= "Pi-"+piU,
										name			= "Pi_Sensor_" +piU,
										description		= "Pi-" + piU+"-"+ipn,
										pluginId		= self.pluginId,
										deviceTypeId	= "rPI-Sensor",
										folder			= self.piFolderId,
										props		= {
											"typeOfBeacon": "rPi-Sensor",
											"sendToIndigoSecs": 90,
											"shutDownPinInput" : "-1",
											"shutDownPinOutput" : "-1",
											"expirationTime" : "90",
											"isRPISensorDevice" : True,
											"SupportsStatusRequest": 	  _GlobalConst_emptyrPiProps["SupportsStatusRequest"],
											"AllowOnStateChange": 		  _GlobalConst_emptyrPiProps["AllowOnStateChange"],
											"AllowSensorValueChange":    _GlobalConst_emptyrPiProps["AllowSensorValueChange"],
											"fastDown" : "-1",
											"RPINumber" : piU,
											"ipNumberPi":ipn}
										)
									dev = indigo.devices[dev.id]
									self.addToStatesUpdateDict(dev.id, "created",dateString)
									self.addToStatesUpdateDict(dev.id, "note", "Pi-" + piU)
									self.addToStatesUpdateDict(dev.id, "groupMember","PI" )
									self.RPI[piU]["piDevId"] = dev.id
									self.updateNeeded += "fixConfig"
									self.setONErPiV(piU, "piUpToDate", ["updateParamsFTP"])
						dev= indigo.devices[self.RPI[piU]["piDevId"]]
						props= dev.pluginProps
						self.addToStatesUpdateDict(dev.id, "note", "Pi-" + piU)
						props["description"] 				= "Pi-"+piU+"-"+ipn
						self.RPI[piU]["piMAC"] 				= piU
						self.deviceStopCommIgnore 			= time.time()
						dev.replacePluginPropsOnServer(props)
						self.RPI[piU]["piOnOff"] 			= "1"
						self.setGroupStatusNextCheck = -1
			try:
				dev= indigo.devices[self.RPI[piU]["piDevId"]]
				dev.enabled = True
				#try:	del self.checkIPSendSocketOk[self.RPI[piU]["ipNumberPi"]]
				#except: pass
				self.executeUpdateStatesDict(onlyDevID=dev.id, calledFrom="buttonConfirmPiServerConfigCALLBACK end")
			except:
				pass
			self.RPI[piU]["piOnOff"] = "1"
			self.startOneUpdateRPIqueue(piU, reason="; from basic setup")

			self.fixConfig(checkOnly = ["all", "rpi"],fromPGM="buttonConfirmPiServerConfigCALLBACK")

		except Exception as e:
			self.exceptionHandler(40, e)


		self.RPI[piU]["piOnOff"] = "1"
		self.writeJson(self.RPI, fName=self.indigoPreferencesPluginDir + "RPIconf", fmtOn=self.RPIFileSort)
		self.startUpdateRPIqueues("restart", piSelect=piU)
		self.setONErPiV(piU, "piUpToDate", ["initSSH","updateAllAllFilesFTP","restartmasterSSH"])
		self.rePopulateStates = "save server config after change in config"


		return valuesDict

####-------------------------------------------------------------------------####
	def delRPI(self, pi="", dev="none", calledFrom=""):
		try:
			devID = "none"

			if dev == "none" and pi == "": return
			if pi !="":
				try: pi = int(pi)
				except: return
				piU = "{}".format(pi)
				devID = int(self.RPI[piU]["piDevId"])
				self.indiLOG.log(30,"=== delRPI:  deleting pi:{}  devID:{}, calledFrom: {} ".format(pi, devID, calledFrom) )
				try: indigo.device.delete(devID)
				except: pass
				self.resetRPI(piU)
				return

			if dev !="none":
				devID = dev.id
				self.indiLOG.log(30,"=== delRPI:  deleting dev:{}, calledFrom: {} ".format(dev.name, calledFrom) )
				pp =  dev.description.split("-")
				try: indigo.device.delete(devID)
				except: pass
				if len(pp) >1:
					try: pi = int(pp[1])
					except: return
					self.resetRPI(piU)
				return

		except Exception as e:
			self.exceptionHandler(40, e)
			self.indiLOG.log(40,"trying to delete indigo device for pi# {};  devID:{}; calledFrom:{}".format(pi, devID, calledFrom))
		return

####-------------------------------------------------------------------------####
	def resetRPI(self, pi):
		piU = "{}".format(pi)
		if piU not in _rpiList: return
		if piU in _rpiSensorList:
			self.RPI[piU] = copy.copy(_GlobalConst_emptyRPISENSOR)
		else:
			self.RPI[piU] = copy.copy(_GlobalConst_emptyRPI)
		self.RPI[piU]["piOnOff"] = "0"
		self.rePopulateStates = "reset RPI"
		self.writeJson(self.RPI, fName=self.indigoPreferencesPluginDir + "RPIconf", fmtOn=self.RPIFileSort)
		self.stopOneUpdateRPIqueues(piU, reason="rpi deleted / reset")

####-------------------------------------------------------------------------####

	def validatePrefsConfigUi(self, valuesDict):

		try:
			self.getDebugLevels(useMe=valuesDict)

			test = valuesDict["debugRPI"]
			try: 	test = int(test)
			except:	test = -1
			if self.debugRPI != test: self.setALLrPiV("piUpToDate", ["updateParamsFTP"])
			self.debugRPI		= test
			valuesDict["debugRPI"] = str(test)


			self.cycleVariables = valuesDict["cycleVariables"]

			try:
				xx = valuesDict["SQLLoggingEnable"].split("-")
				yy = {"devices":xx[0]=="on", "variables":xx[1]=="on"}
				if yy != self.SQLLoggingEnable:
					self.SQLLoggingEnable = yy
					self.actionList["setSqlLoggerIgnoreStatesAndVariables"] = True
			except Exception as e:
				self.exceptionHandler(40, e)
				self.SQLLoggingEnable = {"devices":True, "variables":True}



			try: self.speedUnits					= max(0.01, float(valuesDict["speedUnits"]))
			except: self.speedUnits					= 1.
			try: self.distanceUnits					=  max(0.0254, float(valuesDict["distanceUnits"]))
			except: self.distanceUnits				= 1.
			try: self.lightningTimeWindow			= float(valuesDict["lightningTimeWindow"])
			except: self.lightningTimeWindow		= 10.
			try: self.lightningNumerOfSensors		= int(valuesDict["lightningNumerOfSensors"])
			except: self.lightningNumerOfSensors	= 1

			self.setClostestRPItextToBlank 			= valuesDict["setClostestRPItextToBlank"] !="1"

			for nn in range(len(_GlobalConst_groupList)):
				group = _GlobalConst_groupList[nn]
				self.groupListUsedNames[group] = valuesDict["groupName{}".format(nn)]

			try: self.awayWhenNochangeInSeconds		= int(valuesDict["awayWhenNochangeInSeconds"])
			except: self.awayWhenNochangeInSeconds	= 600

			self.pressureUnits						= valuesDict["pressureUnits"]	# 1 for Pascal
			self.tempUnits							= valuesDict["tempUnits"]	# Celsius, Fahrenheit, Kelvin
			self.tempDigits							= int(valuesDict["tempDigits"])  # 0/1/2

			newRain									= valuesDict["rainUnits"]	# mm inches
			self.rainDigits							= int(valuesDict["rainDigits"])  # 0/1/2
			if newRain != self.rainUnits:
				mult = 1.
				if	 newRain == "inch"	and self.rainUnits == "mm":	mult = 1./25.4
				elif newRain == "inch"	and self.rainUnits == "cm":	mult = 1./2.54
				elif newRain == "mm"	and self.rainUnits == "cm":	mult = 10.
				elif newRain == "mm"	and self.rainUnits == "inch": mult = 25.4
				elif newRain == "cm"	and self.rainUnits == "inch": mult = 2.54
				elif newRain == "cm"	and self.rainUnits == "mm":	mult = 0.1
				for dev in indigo.devices.iter("props.isSensorDevice"):
					if dev.deviceTypeId.find("rainSensorRG11") != -1:
						props = dev.pluginProps
						for state in dev.states:
							if state.find("Rain") >-1 or state.find("rainRate") >-1:
								try: x = float(dev.states[state])
								except: continue
								self.addToStatesUpdateDict(dev.id,state, x*mult, decimalPlaces=self.rainDigits )
						self.executeUpdateStatesDict(onlyDevID=dev.id, calledFrom="validatePrefsConfigUi")

						for prop in ["hourRainTotal", "lasthourRainTotal", "dayRainTotal" ,"lastdayRainTotal", "weekRainTotal", "lastWeekRainTotal", "monthRainTotal" , "lastmonthRainTotal", "yearRainTotal"]:
								try:	props[prop] = float(props[prop]) * mult
								except: pass

						dev.replacePluginPropsOnServer(props)

			self.rainUnits =   newRain
			self.removeJunkBeacons					= valuesDict["removeJunkBeacons"] == "1"
			xxx										= valuesDict["restartBLEifNoConnect"] == "1"
			if xxx != self.restartBLEifNoConnect:
				self.setALLrPiV("piUpToDate", ["updateParamsFTP"])
			self.restartBLEifNoConnect				= xxx


			try: self.enableRebootRPIifNoMessages	 = int(valuesDict["enableRebootRPIifNoMessages"])
			except: self.enableRebootRPIifNoMessages = 999999999

			xxx = valuesDict["rpiDataAcquistionMethod"]
			if xxx != self.rpiDataAcquistionMethod:
				self.setALLrPiV("piUpToDate", ["updateParamsFTP"])
			self.rpiDataAcquistionMethod = xxx


			try:
				self.automaticRPIReplacement		= "{}".format(valuesDict["automaticRPIReplacement"]).lower() == "true"
			except:
				self.automaticRPIReplacement		= False

			try:	self.maxSocksErrorTime			= float(valuesDict["maxSocksErrorTime"])
			except: self.maxSocksErrorTime			= 600.
			try: self.compressRPItoPlugin			= min(40000,int(valuesDict["compressRPItoPlugin"]))
			except: pass


			try:
				self.piUpdateWindow 				= float(valuesDict["piUpdateWindow"])
			except:
				valuesDict["piUpdateWindow"] 		= 0
				self.piUpdateWindow 				= 0.


			try:	self.beaconPositionsUpdateTime 	= float(valuesDict["beaconPositionsUpdateTime"])
			except: pass
			try:	self.beaconPositionsdeltaDistanceMinForImage = float(valuesDict["beaconPositionsdeltaDistanceMinForImage"])
			except: pass
			self.beaconPositionsData["Xscale"]				= (valuesDict["beaconPositionsimageXscale"])
			self.beaconPositionsData["Yscale"]				= (valuesDict["beaconPositionsimageYscale"])
			self.beaconPositionsData["Zlevels"]				= (valuesDict["beaconPositionsimageZlevels"])
			self.beaconPositionsData["dotsY"]				= (valuesDict["beaconPositionsimageDotsY"])

			self.beaconPositionsData["captionTextSize"]	= (valuesDict["beaconPositionsCaptionTextSize"])
			self.beaconPositionsData["textPosLargeCircle"]	= (valuesDict["beaconPositionstextPosLargeCircle"])
			self.beaconPositionsData["labelTextSize"]		= (valuesDict["beaconPositionsLabelTextSize"])
			self.beaconPositionsData["titleTextSize"]		= (valuesDict["beaconPositionsTitleTextSize"])
			self.beaconPositionsData["titleText"]			= (valuesDict["beaconPositionsTitleText"])
			self.beaconPositionsData["titleTextColor"]		= (valuesDict["beaconPositionsTitleTextColor"])
			self.beaconPositionsData["titleTextPos"]		= (valuesDict["beaconPositionsTitleTextPos"])
			self.beaconPositionsData["titleTextRotation"]	= (valuesDict["beaconPositionsTitleTextRotation"])

			self.beaconPositionsData["randomBeacons"] 		= (valuesDict["beaconRandomBeacons"])
			self.beaconPositionsData["LargeCircleSize"] 	= (valuesDict["beaconLargeCircleSize"])
			self.beaconPositionsData["SymbolSize"] 			= (valuesDict["beaconSymbolSize"])
			self.beaconPositionsData["ShowExpiredBeacons"] 	= (valuesDict["beaconShowExpiredBeacons"])
			self.beaconPositionsData["ShowCaption"]			= (valuesDict["beaconPositionsimageShowCaption"])
			self.beaconPositionsData["showTimeStamp"]		= (valuesDict["beaconPositionsShowTimeStamp"]) =="1"

			self.beaconPositionsData["Outfile"]				= (valuesDict["beaconPositionsimageOutfile"])
			self.beaconPositionsData["ShowRPIs"]			= (valuesDict["beaconPositionsimageShowRPIs"])
			self.beaconPositionsData["compress"]			= (valuesDict["beaconPositionsimageCompress"])
			self.beaconPositionsUpdated						= 2


			if valuesDict.get("rebootHour","-") != self.pluginPrefs.get("rebootHour","-1"):
				self.setALLrPiV("piUpToDate", ["updateParamsFTP"])

			if self.pluginPrefs.get("execcommandsListAction","") !=  valuesDict["execcommandsListAction"]:
				self.setALLrPiV("piUpToDate", ["updateParamsFTP"])

			xxx = valuesDict["rebootWatchDogTime"]
			if xxx != self.rebootWatchDogTime:
				self.setALLrPiV("piUpToDate", ["updateParamsFTP"])
			self.rebootWatchDogTime = xxx

			self.expectTimeout = valuesDict["expectTimeout"]


			try:
				xx = int(valuesDict["rPiCommandPORT"])
			except:
				xx = 9999
			if xx != self.rPiCommandPORT:
				self.setALLrPiV("piUpToDate", ["updateParamsFTP"])
			self.rPiCommandPORT = xx


			try:
				xx = int(valuesDict["indigoInputPORT"])
			except:
				xx = 9999
			if xx != self.indigoInputPORT:
				self.quitNow = "restart needed, commnunication was switched "
				self.indiLOG.log(10,"switching communication, will send new config to all RPI and restart plugin")
				self.setALLrPiV("piUpToDate", ["updateParamsFTP"])
			self.indigoInputPORT = xx


			if True: # set to fixed socket only switch off http / restful
				try:
					xx = (valuesDict["IndigoOrSocket"])
				except:
					xx = 9999
				if xx != self.IndigoOrSocket:
					self.quitNow = "restart, commnunication was switched "
					self.indiLOG.log(10,"switching communication, will send new config to all RPI and restart plugin")
					self.setALLrPiV("piUpToDate", ["updateParamsFTP"])
				self.IndigoOrSocket = xx

			try: 	xx = valuesDict["iBeaconFolderName"]
			except:	xx = "PI_Beacons_new"
			if xx != self.iBeaconDevicesFolderName:
				self.iBeaconDevicesFolderName = xx

			try:	xx = valuesDict["iBeaconFolderVariablesName"]
			except:	xx = "piBeacons"
			if xx != self.iBeaconFolderVariablesName:
				self.iBeaconFolderVariablesName = xx

			upNames = False
			if self.groupCountNameDefault != valuesDict["groupCountNameDefault"]:	   upNames = True
			if self.ibeaconNameDefault	  != valuesDict["ibeaconNameDefault"]:		   upNames = True
			self.groupCountNameDefault = valuesDict["groupCountNameDefault"]
			self.ibeaconNameDefault	   = valuesDict["ibeaconNameDefault"]
			if upNames:
				self.varExcludeSQLList = ["pi_IN_"+str(ii) for ii in _rpiList]
				self.varExcludeSQLList.append(self.ibeaconNameDefault+"With_ClosestRPI_Change")
				self.varExcludeSQLList.append(self.ibeaconNameDefault+"Rebooting")
				self.varExcludeSQLList.append(self.ibeaconNameDefault+"With_Status_Change")
				for group in _GlobalConst_groupList:
					for tType in ["Home", "Away"]:
						self.varExcludeSQLList.append(self.groupCountNameDefault+group+"_"+tType)
				self.actionList["setSqlLoggerIgnoreStatesAndVariables"] = True


			self.deleteAndCeateVariablesAndDeviceFolder(False)
			self.checkBeaconParametersDisabled	= valuesDict["checkBeaconParametersDisabled"]


			self.myIpNumber = valuesDict["myIpNumber"]
			try:
				self.secToDown = float(valuesDict["secToDown"])
			except:
				self.secToDown = 90.

			pp = valuesDict["myIpNumber"]
			if pp != self.myIpNumber:
				self.setALLrPiV("piUpToDate", ["updateParamsFTP"])
			self.myIpNumber = pp

			self.blockNonLocalIp			= valuesDict["blockNonLocalIp"]
			self.checkRPIipForReject		= valuesDict["checkRPIipForReject"]


			if valuesDict["getBatteryMethod"] != self.pluginPrefs.get("getBatteryMethod","interactive"):
				self.setALLrPiV("piUpToDate", ["updateParamsFTP"])

			pp = valuesDict["portOfServer"]
			if pp != self.portOfServer:
				self.setALLrPiV("piUpToDate", ["updateParamsFTP"])
			self.portOfServer = pp

			pp = valuesDict["userIdOfServer"]
			if pp != self.userIdOfServer:
				self.setALLrPiV("piUpToDate", ["updateParamsFTP"])
			self.userIdOfServer = pp

			pp = valuesDict["passwordOfServer"]
			if pp != self.passwordOfServer:
				self.setALLrPiV("piUpToDate", ["updateParamsFTP"])
			self.passwordOfServer = pp

			pp = valuesDict["authentication"]
			if pp != self.authentication:
				self.setALLrPiV("piUpToDate", ["updateParamsFTP"])
			self.authentication = pp


			pp = valuesDict["apiKey"]
			if pp != self.apiKey:
				self.setALLrPiV("piUpToDate", ["updateParamsFTP"])
			self.apiKey = pp

			pp = valuesDict["GPIOpwm"]
			if pp != self.GPIOpwm:
				self.setALLrPiV("piUpToDate", ["updateParamsFTP"])
			self.GPIOpwm = pp


			ss = valuesDict["wifiSSID"]
			pp = valuesDict["wifiPassword"]
			kk = valuesDict["key_mgmt"]
			eth0					= '{"on":"dontChange",	"useIP":"use"}'
			wlan0					= '{"on":"dontChange",	"useIP":"useIf"}'
			try:	mm  			= {"eth0":json.loads(valuesDict["eth0"]), "wlan0":json.loads(valuesDict["wlan0"]) }
			except: mm  			= {"eth0":json.loads(eth0), "wlan0":json.loads(wlan0)}

			if ss != self.wifiSSID or pp != self.wifiPassword or kk != self.key_mgmt or mm != self.wifiEth:
				self.wifiSSID		= ss
				self.wifiPassword	= pp
				self.key_mgmt		= kk
				self.wifiEth		= mm
				self.setALLrPiV("piUpToDate", ["updateParamsFTP"])

			if "all" in self.debugLevel:
				self.printConfig()

			self.fixConfig(checkOnly = ["all", "rpi", "force"],fromPGM="validatePrefsConfigUi")
		except Exception as e:
			self.exceptionHandler(40, e)
		return True, valuesDict

####-------------------------------------------------------------------------####
	def confirmDevicex(self, valuesDict=None, typeId="", devId=0):

		piU = valuesDict["piServerNumber"]
		pi  = int(piU)
		if devId == 0:
			self.selectedPiServer = pi
			valuesDict["enablePiEntries"]	 = True
			valuesDict["ipNumberPi"]		 = self.RPI[piU]["ipNumberPi"]
			valuesDict["userIdPi"]			 = self.RPI[piU]["userIdPi"]
			valuesDict["piOnOff"]			 = self.RPI[piU]["piOnOff"]
			valuesDict["MSG"]				 = "enter configuration"
			return valuesDict
		return valuesDict


	###########################	   MAIN   ############################
####-------------------------------------------------------------------------####
	def initConcurrentThread(self):
		self.countP				 = 0
		self.countPTotal		 = 0
		self.updateNeeded		 = ""

		now = datetime.datetime.now()
		self.messagesQueue	  = Queue.Queue()
		self.messagesQueueBLE = Queue.Queue()
		self.queueActiveBLE	  = False
		self.quitNow		  = ""

		self.startTime		  = time.time()
		self.stackReady		  = False
		self.socServ	  = None

		self.indiLOG.log(20,"entering init runConcurrentThread")

		self.initMac2Vendor()



		for ii in range(2):
			if self.pluginPrefs.get("authentication", "digest") == "none": break
			if self.userIdOfServer !="" and self.passwordOfServer != "": break
			self.indiLOG.log(30,"indigo server userid or password not configured in config and security level is set to digest or basic")
			self.sleep(10)

		self.initSprinkler()

		if self.indigoInputPORT > 0 and self.IndigoOrSocket == "socket":
			self.setCurrentlyBooting(50, setBy="initConcurrentThread")
			self.socServ, self.stackReady	= self.startTcpipListening(self.myIpNumber, self.indigoInputPORT)
			self.setCurrentlyBooting(40, setBy="initConcurrentThread")
		else:
			self.indiLOG.log(10," ..  subscribing to indigo variable changes" )
			indigo.variables.subscribeToChanges()
			self.setCurrentlyBooting(40, setBy="initConcurrentThread")
			self.stackReady			= True

		self.lastMinuteChecked	= now.minute
		self.lastHourChecked	= now.hour
		self.lastDayChecked		= [-1 for ii in range(len(self.checkBatteryLevelHours)+2)]
		self.lastSecChecked		= 0
		self.countLoop			= 0
		self.indiLOG.log(5," ..   checking sensors" )
		self.syncSensors()

		self.indiLOG.log(5," ..   checking BLEconnect" )
		self.BLEconnectCheckPeriod(force=True)
		self.indiLOG.log(5," ..   checking beacons" )
		self.BeaconsCheckPeriod(now, force=True)

		self.rPiRestartCommand = ["master" for ii in range(_GlobalConst_numberOfRPI)]	## which part need to restart on rpi
		self.setupFilesForPi()
		self.indiLOG.log(20," ..  checking for new py programs for RPIs;  currentV:{}, newV:{}".format(self.currentVersion, self.pluginVersion))
		if self.currentVersion != self.pluginVersion:
			self.setCurrentlyBooting(40, setBy="initConcurrentThread")
			self.indiLOG.log(20," ..  new py programs  etc will be send to rPis")
			for piU in self.RPI:
				if self.RPI[piU]["ipNumberPi"] != "":
					self.setONErPiV(piU, "piUpToDate", ["updateAllFilesFTP", "restartmasterSSH"])
			self.indiLOG.log(20," ..  new pgm versions send to rPis")
			self.sleep(10)
		else:
			for piU in self.RPI:
				if self.RPI[piU]["ipNumberPi"] != "":
					self.setONErPiV(piU, "piUpToDate", ["updateParamsFTP"])

		if len(self.checkCarsNeed) > 0:
			for carId in copy.copy(self.checkCarsNeed):
				self.updateAllCARbeacons(carId, force=True)

		self.checkForUpdates(datetime.datetime.now())

		self.lastUpdateSend = time.time()  # used to send updates to all rPis if not done anyway every day
		self.pluginState	= "run"
		self.setCurrentlyBooting(50, setBy="initConcurrentThread")
		self.writeJson(self.pluginVersion, fName=self.indigoPreferencesPluginDir + "currentVersion")

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
		except Exception as e:
			pass

		self.timeTrackWaitTime = 60
		return "off",""

####-----------------            ---------
	def printcProfileStats(self,pri=""):
		try:
			if pri !="": pick = pri
			else:		 pick = 'cumtime'
			outFile		= self.indigoPreferencesPluginDir+"timeStats"
			self.indiLOG.log(20," print time track stats to: {}.dump / txt  with option: {}".format(outFile, pick) )
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
			self.timeTrVarName 			= "enableTimeTracking_"+self.pluginShortName
			self.indiLOG.log(10,"testing if variable {} is == on/off/print-option to enable/end/print time tracking of all functions and methods (option:'',calls,cumtime,pcalls,time)".format(self.timeTrVarName))

		self.lastTimegetcProfileVariable = time.time()

		cmd, pri = self.getcProfileVariable()
		if self.do_cProfile != cmd:
			if cmd == "on":
				if  self.cProfileVariableLoaded ==0:
					self.indiLOG.log(20,"======>>>>   loading cProfile & pstats libs for time tracking;  starting w cProfile ")
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
				indigo.variable.updateValue(self.timeTrVarName, "done")

		self.do_cProfile = cmd
		return

####-----------------            ---------
	def checkcProfileEND(self):
		if self.do_cProfile in["on", "print"] and self.cProfileVariableLoaded >0:
			self.printcProfileStats(pri="")
		return
	###########################	   cProfile stuff   ############################ END



####-----------------   main loop          ---------
	def runConcurrentThread(self):

		self.dorunConcurrentThread()
		self.checkcProfileEND()
		self.sleep(1)
		if self.quitNow !="":
			indigo.server.log("runConcurrentThread stopping plugin due to:  ::::: {} :::::".format(self.quitNow))
			serverPlugin = indigo.server.getPlugin(self.pluginId)
			serverPlugin.restart(waitUntilDone=False)


		subprocess.call("/bin/kill -9 {}".format(self.myPID), shell=True )

		return



####-----------------   main loop          ---------
	def dorunConcurrentThread(self):

		self.initConcurrentThread()

		self.indiLOG.log(20," ..  initialized, starting loop" )
		theHourToCheckversion = 12


		########   ------- here the loop starts	   --------------
		try:
			while self.quitNow == "":
				self.countLoop += 1
				self.sleep(self.loopSleepTime)

				if self.countLoop > 2:
					anyChange = self.periodCheck()
					self.setGroupStatus()

		except self.StopThread:
			indigo.server.log("stop requested from indigo ")
		## stop and processing of messages received
		if self.quitNow !="": indigo.server.log( " .. quitNow: {}--- you might see an indigo error message, can be ignored ".format(self.quitNow))
		else: indigo.server.log(" .. stopping plugin  from external source")

		self.saveChangedValues()

		self.stackReady	 = False
		self.pluginState = "stop"


		# save all parameters to file
		self.fixConfig(checkOnly = ["all", "rpi", "beacon", "CARS", "sensors", "output", "force"],fromPGM="finish") # runConcurrentThread end

		self.stopUpdateRPIqueues()
		self.stopbeaconMessageQueue()
		self.stopDelayedActionQueue()
		time.sleep(1)

		if self.socServ is not None:
			self.indiLOG.log(10," ..   stopping tcpip stack")
			self.socServ.shutdown()
			self.socServ.server_close()
			time.sleep(1)
			# kill procs that might still be waiting / ...
			lsofCMD	 = "/usr/sbin/lsof -i tcp:{}".format(self.indigoInputPORT)
			ret, err = self.readPopen(lsofCMD)
			#indigo.server.log(".. stopping tcpip stack: lsof cmd result:\n{}".format(ret[0]))
			self.killHangingProcess(ret)



		return


####-------------------------------------------------------------------------####


####-------------------------------------------------------------------------####
	def printpiUpToDate(self):
		try:
			xList = ""
			for piU in self.RPI:
				xList += piU+":{}".format(self.RPI[piU]["piUpToDate"])+"; "
			if self.decideMyLog("OfflineRPI"): self.indiLOG.log(5,"printpiUpToDate list .. pi#:[actionLeft];.. ([]=ok): "+ xList	 )
		except Exception as e:
			self.exceptionHandler(40, e)
		return

####-------------------------------------------------------------------------####
	def findAnyTaskPi(self, item):
		try:
			for piU in self.RPI:
				if self.RPI[piU][item] !=[]:
					return True
		except Exception as e:
			self.exceptionHandler(40, e)
		return False

####-------------------------------------------------------------------------####
	def findTaskPi(self, item,findTask):
		for piU in self.RPI:
			if findTask in self.RPI[piU][item]:	return True
		return False

####-------------------------------------------------------------------------####
	def periodCheck(self):
		anyChange= False
		try:
			tt = time.time()
			if time.time()- self.lastSecChecked < 9. or time.time()- self.startTime < 30: return anyChange

			self.performActionList()

			self.checkIfNewStates()

			self.checkcProfile()

			now = datetime.datetime.now()
			self.freezeAddRemove =False

			self.replaceAddress()

			self.checkForUpdates(now)

			if self.sendInitialValue != "": self.sendInitialValuesToOutput()

			self.checkMinute(now)

			self.sprinklerStats()


			if self.queueList !="":
				for ii in range(40):
					if ii > 0 and self.decideMyLog("BeaconData"): self.indiLOG.log(5,"wait for queue to become available in main loop,   ii={}  {}".format(ii, self.queueList))
					if self.queueList =="": break
					self.sleep(0.05)

			self.startUpdateRPIqueues("restart")

			self.queueList = "periodCheck"		 # block incoming messages from processing
			self.BLEconnectCheckPeriod()

			anyChange = self.BeaconsCheckPeriod(now)

			self.checkIfupdateCARStimeHasCome()

			self.queueList = ""					# unblock incoming messages from processing

			self.checkIfNotBeepableExpired()

			if self.lastMinuteChecked != now.minute:
				anyChange = True


			self.checkHour(now)
			self.checkDay(now)

			self.execdevUpdateList()

			if	(  self.beaconPositionsUpdated !=0 or
				  (self.beaconPositionsUpdateTime > 0 and (time.time()- self.beaconPositionsLastCheck)	> self.beaconPositionsUpdateTime )	 ):
					self.makeNewBeaconPositionPlots()

			self.lastSecChecked		= time.time()
			self.lastMinuteChecked	= now.minute
			self.lastHourChecked	= now.hour

			self.freezeAddRemove	= False
			self.initStatesOnServer = False
		except Exception as e:
			self.exceptionHandler(40, e)

		return anyChange




####-------------------------------------------------------------------------####
	def checkIfNewStates(self, force=False):
		try:
			if force: 
				oldDebug = self.pluginPrefs.get("debugSpecial")
				self.pluginPrefs["debugSpecial"] = True
				self.getDebugLevels()
			if self.rePopulateStates != "" or force:
				if force: self.debugNewDevStates = True
				self.indiLOG.log(20,"updating dev states, trying to add missing states, check pibeacon.log file for details, switch on SPECIAL log in config for more info , trigger is:{}".format(self.rePopulateStates))
				for dev in indigo.devices.iter(self.pluginId):
					dev.stateListOrDisplayStateIdChanged()	# update  states, add keys if missing
		except Exception as e:
			self.exceptionHandler(40, e)
		self.rePopulateStates = ""
		if force: 
				self.pluginPrefs["debugSpecial"]  = oldDebug
				self.getDebugLevels()
		self.debugNewDevStates = False
		return 


####-------------------------------------------------------------------------####
	def checkIfNotBeepableExpired(self):
		try:
			for beacon in copy.deepcopy(self.beacons):
				if "lastBusy" not in self.beacons[beacon] or self.beacons[beacon]["lastBusy"] < 20000:
					self.beacons[beacon]["lastBusy"] = time.time() - 1000
				if self.beacons[beacon]["indigoId"] > 0:
					if self.beacons[beacon]["note"].find("beacon") > -1:
						if self.beacons[beacon]["lastBusy"] > 10000:
							if self.beacons[beacon]["lastBusy"] > 0:
								if time.time() - self.beacons[beacon]["lastBusy"] > -5:
									try: dev = indigo.devices[self.beacons[beacon]["indigoId"]]
									except: continue
									if dev.enabled:
										if "isBeepable" in dev.states:  # wait until created, next reload
											tag = dev.states["typeOfBeacon"].split("-")[0]
											if tag in self.knownBeaconTags["input"] and "commands" in self.knownBeaconTags["input"][tag] and "beep" in self.knownBeaconTags["input"][tag]["commands"] and self.knownBeaconTags["input"][tag]["commands"]["beep"]["type"] == "BLEconnect":
												dev.updateStateOnServer("isBeepable", "YES")
												self.beacons[beacon]["lastBusy"] = time.time() - 1000
											else:
												dev.updateStateOnServer("isBeepable", "not capable")

		except Exception as e:
			self.exceptionHandler(40, e)
		return


####-------------------------------------------------------------------------####
	def performActionList(self):
		try:
			if self.actionList["setTime"] != []:

				for action in self.actionList["setTime"]:
					if action["action"] == "setTime":
						self.doActionSetTime(action["value"])

			if self.actionList["setSqlLoggerIgnoreStatesAndVariables"] :
				self.actionList["setSqlLoggerIgnoreStatesAndVariables"] = False
				self.setSqlLoggerIgnoreStatesAndVariables()

		except Exception as e:
			self.exceptionHandler(40, e)
		self.actionList["setTime"] = []
		return


####-------------------------------------------------------------------------####
	def replaceAddress(self):
		try:
			if self.newADDRESS !={}:
				for devId in self.newADDRESS:
					try:
						dev = indigo.devices[devId]
						if len(self.newADDRESS[devId]) == len("01:02:03:04:05:06"):
							self.indiLOG.log(10,"updating {}  address with: {}".format(dev.name, self.newADDRESS[devId]))
							props = dev.pluginProps
							props["address"]= self.newADDRESS[devId]
	
							dev.replacePluginPropsOnServer(props)
							dev = indigo.devices[devId]
							props = dev.pluginProps
					except Exception as e:
						if "{}".format(e) != "None":
							self.exceptionHandler(40, e)
							self.indiLOG.log(40,"ok if replacing RPI")
				self.newADDRESS={}

		except Exception as e:
			self.exceptionHandler(40, e)



####-------------------------------------------------------------------------####
	def sendInitialValuesToOutput(self):
		try:
			dev = indigo.devices[self.sendInitialValue]
			props= dev.pluginProps
			deviceDefs = json.loads(props.get("deviceDefs",""))
			nn = len(deviceDefs)
			piServerNumber = props["piServerNumber"]
			ip = self.RPI["{}".format(props["piServerNumber"])]["ipNumberPi"]
			for n in range(nn):
				cmd = deviceDefs[n]["initialValue"]
				if cmd =="up" or  cmd =="down":
					inverseGPIO = (deviceDefs[n]["outType"] == "1")
					gpio = deviceDefs[n]["gpio"]
					if self.decideMyLog("OutputDevice"): self.indiLOG.log(5,"sendInitialValuesToOutput init pin: sending to pi# {}; pin: {}  {};  deviceDefs: {}".format(piServerNumber, props["gpio"], cmd, props["deviceDefs"]) )
					self.sendGPIOCommand(ip, int(piServerNumber), dev.deviceTypeId, cmd, GPIOpin=gpio, restoreAfterBoot="1", inverseGPIO =inverseGPIO )

		except Exception as e:
			self.exceptionHandler(40, e)
		self.sendInitialValue = ""
		return


####-------------------------------------------------------------------------####
	def checkForUpdates(self,now):
		anyChange= False
		try:

			if time.time()- self.lastUpdateSend > 3600:	 ## send config every hour, no other action
				self.rPiRestartCommand = ["" for ii in range(_GlobalConst_numberOfRPI)]  # soft update, no restart required
				self.setALLrPiV("piUpToDate", ["updateParamsFTP"])

			if (self.updateNeeded.find("enable") > -1) or (self.updateNeeded.find("disable") > -1):
				self.fixConfig(checkOnly = ["all", "rpi", "force"], fromPGM="checkForUpdates"+ self.updateNeeded) # checkForUpdates  # ok only if changes requested
				#self.syncSensors()
				self.setupFilesForPi(calledFrom="checkForUpdates enable/disable")
				try:
					pi = self.updateNeeded.split("-")
					if len(pi) >1:
						self.setONErPiV(pi[1],"piUpToDate", ["updateParamsFTP"])
						if self.decideMyLog("UpdateRPI"): self.indiLOG.log(5,"sending update to pi#{}".format(pi))
				except Exception as e:
					if "{}".format(e) != "None":
						self.exceptionHandler(40, e)

				self.updateNeeded = ""

			if self.updateNeeded.find("fixConfig") > -1 or self.findAnyTaskPi("piUpToDate"):
				if self.decideMyLog("UpdateRPI"): self.indiLOG.log(5,"checkForUpdates updateNeeded:{},  findAnyTaskPi: {}".format(self.updateNeeded, self.findAnyTaskPi("piUpToDate")) )
				self.fixConfig(checkOnly = ["all", "rpi", "force"],fromPGM="checkForUpdates"+self.updateNeeded) # checkForUpdates  # ok only if changes requested
				self.setupFilesForPi(calledFrom="checkForUpdates")
				self.updateNeeded = ""


			if not self.findAnyTaskPi("piUpToDate"):
				self.updateRejectListsCount =0
			else:
					self.newIgnoreMAC = 0
					for piU in self.RPI:

						if "initSSH" in self.RPI[piU]["piUpToDate"]:
							self.sshToRPI(piU, expFile="initSSH.exp")

						if "updateAllFilesFTP" in self.RPI[piU]["piUpToDate"]:
							self.sendFilesToPiFTP(piU, expFile="updateAllFilesFTP.exp")

						if "updateAllAllFilesFTP" in self.RPI[piU]["piUpToDate"]:
							self.sendFilesToPiFTP(piU, expFile="updateAllAllFilesFTP.exp")

						if "updateParamsFTP" in self.RPI[piU]["piUpToDate"]:
							self.sendFilesToPiFTP(piU, expFile="updateParamsFTP.exp")

						if "updateBeaconParamsFTP" in self.RPI[piU]["piUpToDate"]:
							self.sendFilesToPiFTP(piU, expFile="updateBeaconParamsFTP.exp")

						if "restartmasterSSH" in self.RPI[piU]["piUpToDate"]:
							self.sshToRPI(piU, expFile="restartmasterSSH.exp")

						if "upgradeSSH" in self.RPI[piU]["piUpToDate"]:
							self.sshToRPI(piU, expFile="upgradeSSH.exp")

						if self.updateRejectListsCount < _GlobalConst_numberOfRPI:
							self.updateRejectListsCount +=1
							self.updateRejectLists()
						else:
							self.printpiUpToDate()

					if self.findTaskPi("piUpToDate", "getStatsSSH"):
						for piU in self.RPI:
							if "getStatsSSH" in self.RPI[piU]["piUpToDate"]:
								self.sshToRPI(piU,expFile="getStatsSSH.exp")

					if self.findTaskPi("piUpToDate", "getLogFileSSH"):
						for piU in self.RPI:
							if "getLogFileSSH" in self.RPI[piU]["piUpToDate"]:
								self.sshToRPI(piU,expFile="getLogFileSSH.exp")

					if self.findTaskPi("piUpToDate", "shutdownSSH"):
						for piU in self.RPI:
							if "shutdownSSH" in self.RPI[piU]["piUpToDate"]:
								self.sshToRPI(piU,expFile="shutdownSSH.exp")

					if self.findTaskPi("piUpToDate", "rebootSSH"):
						for piU in self.RPI:
							if "rebootSSH" in self.RPI[piU]["piUpToDate"] and not  "updateParamsFTP" in self.RPI[piU]["piUpToDate"]:
								self.sshToRPI(piU,expFile="rebootSSH.exp")

					if self.findTaskPi("piUpToDate", "resetOutputSSH"):
						for piU in self.RPI:
							if "resetOutputSSH" in self.RPI[piU]["piUpToDate"]  and not  "updateParamsFTP" in self.RPI[piU]["piUpToDate"]:
								self.sshToRPI(piU,expFile="resetOutputSSH.exp")

		except Exception as e:
			self.exceptionHandler(40, e)
		return anyChange


####-------------------------------------------------------------------------####
	def checkMinute(self, now):
		if now.minute == self.lastMinuteChecked: return

		try:
			self.fixConfig(checkOnly = ["all"], fromPGM="checkMinute") # checkMinute
			self.checkRPIStatus()
			self.checkSensorStatus()
			self.saveTcpipSocketStats()

			self.freezeAddRemove = False
			self.saveChangedValues()

			if now.minute % 5 == 0:
				if self.newIgnoreMAC > 0:
					for piU in self.RPI:
						self.setONErPiV(piU, "piUpToDate", ["updateParamsFTP"])
					self.newIgnoreMAC = 0

				for piU in self.RPI:
					if self.RPI[piU]["piOnOff"] == "0":					continue
					if self.RPI[piU]["piDevId"] ==	 0:						continue
					if time.time() - self.RPI[piU]["lastMessage"] < 330.:	continue
					if self.decideMyLog("Logic"): self.indiLOG.log(5,"pi server # {}  ip# {}  has not send a message in the last {:.0f} seconds".format(piU, self.RPI[piU]["ipNumberPi"], time.time() - self.RPI[piU]["lastMessage"]))

		except Exception as e:
			self.exceptionHandler(40, e)
		return

####-------------------------------------------------------------------------####
	def BLEconnectCheckPeriod(self, force = False):
		try:
			updBLE = False
			sendToRPI = {}
			if time.time()< self.currentlyBooting:
				return
			for dev in indigo.devices.iter("props.isBLEconnectDevice"):
				if not dev.enabled: continue
				if self.queueListBLE == "update": self.sleep(0.1)
				lastStatusChangeDT = 99999
				props = dev.pluginProps
				try:
					expirationTime = float(props["expirationTime"]) + 0.1
				except:
					continue
				status = "expired"
				lastUp = dev.states["lastUp"]
				dt = time.time() - self.getTimetimeFromDateString(lastUp)
				if dt <= 1 * expirationTime:
					status = "up"
				elif dt <= 2 * expirationTime:
					status = "down"

				if self.decideMyLog("BLE"): self.indiLOG.log(5,"BLEconnectCheckPeriod:  {} = lastUP:{}, dt:{}, status:{}, oldStatus:{}".format(dev.name, lastUp, dt, status, dev.states["status"]))

				if dev.states["status"] != status or self.initStatesOnServer or force:
					self.statusChanged = 3
					if "lastStatusChange" in dev.states:
						lastStatusChangeDT   =  time.time() - self.getTimetimeFromDateString(dev.states["lastStatusChange"])
					if lastStatusChangeDT > 3:
						#if self.decideMyLog("BLE") and dev.name.find("BLE-C") >-1: self.indiLOG.log(5,"BLEconnectCheckPeriod :"+dev.name+";  new status:"+ status+"; old status:"+ dev.states["status"]+"   dt={}".format(dt) +"; lastUp={}".format(lastUp)+"; expirationTime={}".format(expirationTime))
						if status == "up":
							dev.updateStateImageOnServer(indigo.kStateImageSel.SensorOn)
						elif status == "down":
							dev.updateStateImageOnServer(indigo.kStateImageSel.SensorOff)
						else:
							dev.updateStateImageOnServer(indigo.kStateImageSel.SensorTripped)
					self.addToStatesUpdateDict(dev.id, "status", status)

				if status != "up":
					if "{}".format(dev.states["closestRPI"]) != "-1":
						self.addToStatesUpdateDict(dev.id, "closestRPI", -1)

				self.executeUpdateStatesDict(onlyDevID=dev.id, calledFrom="BLEconnectCheckPeriod end")

				#### check for last up and send to rpi to avoid extra pings to phone if last up was recent ------
				if props.get("shareUpstatusAcrossRPis",True):
					if dev.id not in self.lastBLEconnectSeen:
						self.lastBLEconnectSeen[dev.id] = self.getTimetimeFromDateString(lastUp)

					if dev.id not in self.BLEconnectSendStopToRpi:
						self.BLEconnectSendStopToRpi[dev.id] = {"mac":dev.address, "send":True, "test1":False, "test2":False, "lastUp":0, "previous":0, "lastSeen":0}

					self.BLEconnectSendStopToRpi[dev.id]["test1"] = self.lastBLEconnectSeen[dev.id] 	- self.BLEconnectSendStopToRpi[dev.id]["lastUp"] 	> 20.
					self.BLEconnectSendStopToRpi[dev.id]["test2"] = time.time() 						- self.lastBLEconnectSeen[dev.id] 					< max(float(props.get("iPhoneRefreshUpSecs",60.)),60.) 
					self.BLEconnectSendStopToRpi[dev.id]["send"]  = self.BLEconnectSendStopToRpi[dev.id]["test1"] and self.BLEconnectSendStopToRpi[dev.id]["test2"] 

					if self.BLEconnectSendStopToRpi[dev.id]["send"] :
						self.BLEconnectSendStopToRpi[dev.id]["previous"]	= self.BLEconnectSendStopToRpi[dev.id]["lastUp"] 
						self.BLEconnectSendStopToRpi[dev.id]["lastUp"] 		= self.lastBLEconnectSeen[dev.id]
						updBLE = True
						for ii in _rpiBeaconList:
							if props.get("rPiEnable{}".format(ii),False): sendToRPI[ii]=True
					self.BLEconnectSendStopToRpi[dev.id]["lastSeen"] = self.lastBLEconnectSeen[dev.id]


				#### check for last up and send to rpi to avoid extra pings to phone if last up was recent ------
			
			self.updateBLEconenctStatusOnRpi(updBLE, sendToRPI)
			#### check for last up and send to rpi to avoid extra pings to phone if last up was recent ------

		except Exception as e:
			self.exceptionHandler(40, e)
		return


####-------------------------------------------------------------------------####
	def updateBLEconenctStatusOnRpi(self, updBLE, sendToRPI):
		try:
			#self.indiLOG.log(20,"updateBLEconenctStatusOnRpi: updBLE:{}, sendToRPI:{},  self.BLEconnectSendStopToRpi :{} ".format(updBLE, sendToRPI, self.BLEconnectSendStopToRpi) )
			if self.BLEconnectSendStopToRpi == {}: return 
			self.BLEconnectLastUp = {}
			if updBLE:
				for devId in self.BLEconnectSendStopToRpi:
					self.BLEconnectSendStopToRpi[devId]["lastUp"] = self.BLEconnectSendStopToRpi[devId]["lastSeen"]
				self.BLEconnectLastUp = copy.deepcopy(self.BLEconnectSendStopToRpi)

				if self.BLEconnectLastUp != {}:
					#self.indiLOG.log(20,"updateBLEconenctStatusOnRpi: self.BLEconnectLastUp :{} ".format(self.BLEconnectLastUp) )
					self.makeBeacons_parameterFile()
					for pi in sendToRPI:
						self.setONErPiV("{}".format(pi), "piUpToDate", ["updateBeaconParamsFTP"])


		except Exception as e:
			self.exceptionHandler(40, e)
		return

####-------------------------------------------------------------------------####
	def checkSensorStatus(self):

		return 
		# thsi is left over should be deleted 
		try:
			for dev in indigo.devices.iter("props.isSensorDevice"):
				if dev.deviceTypeId not in _GlobalConst_allowedSensors and dev.deviceTypeId not in _BLEsensorTypes: continue
				dt = time.time()- self.checkSensorMessages(dev.id, "lastMessage", default=time.time())

				if time.time()< self.currentlyBooting: continue
				if dt > 600:
					try:
						if	dev.pluginProps["displayS"].lower().find("temp")==-1:
							dev.updateStateImageOnServer(indigo.kStateImageSel.PowerOff)
						else:
							dev.updateStateImageOnServer(indigo.kStateImageSel.PowerOff)
					except:
						self.indiLOG.log(10,"checkSensorStatus: {} property displayS missing, please edit and save ".format(dev.name) )
						dev.updateStateImageOnServer(indigo.kStateImageSel.Error)
			self.saveSensorMessages(devId="")

		except Exception as e:
			self.exceptionHandler(40, e)
			try:
				self.indiLOG.log(40, "{}".format(dev.pluginProps))
			except:
				pass
		return


####-------------------------------------------------------------------------####
	def checkRPIStatus(self):
		try:
			if	time.time()< self.currentlyBooting: return

			for piU in self.RPI:
				if self.RPI[piU]["piDevId"] == 0:	 continue
				try:
					dev = indigo.devices[self.RPI[piU]["piDevId"]]
				except:
					continue
				if self.RPI[piU]["piOnOff"] == "0":
					if time.time()- self.RPI[piU]["lastMessage"] > 500:
						self.addToStatesUpdateDict(dev.id, "online", "expired")
						dev.updateStateImageOnServer(indigo.kStateImageSel.PowerOff)
						if piU in _rpiBeaconList:
							if dev.states["status"] != "expired":
								self.addToStatesUpdateDict(dev.id, "status", "expired")
								self.statusChanged = 4

					continue

				if time.time()- self.RPI[piU]["lastMessage"] > 240:
					self.addToStatesUpdateDict(dev.id, "online", "expired")
					if piU in _rpiSensorList:
						if dev.states["status"] != "expired":
							self.addToStatesUpdateDict(dev.id, "status", "expired")
							self.statusChanged = 5
						dev.updateStateImageOnServer(indigo.kStateImageSel.PowerOff)
					else:
						if dev.states["status"] in ["down", "expired"]:
							dev.setErrorStateOnServer("Pconnection and BLE down")
							dev.updateStateImageOnServer(indigo.kStateImageSel.SensorTripped)
						else:
							dev.setErrorStateOnServer("")
							dev.updateStateImageOnServer(indigo.kStateImageSel.PowerOff)

				elif time.time()- self.RPI[piU]["lastMessage"] >120:
					self.addToStatesUpdateDict(dev.id, "online", "down")
					if piU in _rpiSensorList:
						if dev.states["status"] != "down":
							self.addToStatesUpdateDict(dev.id, "status", "down")
							self.statusChanged = 6
						dev.updateStateImageOnServer(indigo.kStateImageSel.PowerOff)
					else:
						if dev.states["status"] in ["down", "expired"]:
							dev.setErrorStateOnServer("IPconnection and BLE down")
							dev.updateStateImageOnServer(indigo.kStateImageSel.SensorTripped)
						else:
							dev.setErrorStateOnServer("")
							dev.updateStateImageOnServer(indigo.kStateImageSel.PowerOff)

				else:
					self.addToStatesUpdateDict(dev.id, "online", "up")
					self.addToStatesUpdateDict(dev.id, "status", "up")
					dev.setErrorStateOnServer("")
					if piU in _rpiSensorList:
							dev.updateStateImageOnServer(indigo.kStateImageSel.SensorOn)
					else:
						if dev.states["status"] in ["down", "expired"]:
							dev.updateStateImageOnServer(indigo.kStateImageSel.SensorOff)
						else:
							dev.updateStateImageOnServer(indigo.kStateImageSel.SensorOn)

		except Exception as e:
			self.exceptionHandler(40, e)


		return



####-------------------------------------------------------------------------####


# noinspection SpellCheckingInspection
	def BeaconsCheckPeriod(self, now, force = False):
		try:
			if	time.time()< self.currentlyBooting:
				if time.time()> self.lastUPtoDown:
					self.indiLOG.log(10,"BeaconsCheckPeriod waiting for reboot, no changes in up--> down status for another {:.0f}[secs]".format(self.currentlyBooting - time.time()))
					self.lastUPtoDown  = time.time()+90
				return False # noting for the next x minutes due to reboot
			anyChange = False
			for beacon in copy.deepcopy(self.beacons):
				if not self.beacons[beacon]["enabled"]: continue
				if self.beacons[beacon]["ignore"] > 0 : continue

				if len(self.beacons[beacon]["receivedSignals"]) < len(_rpiBeaconList):
					self.fixBeaconPILength(beacon, "receivedSignals")

				if beacon.find("00:00:00:00") ==0: continue
				dev = ""
				if self.selectBeaconsLogTimer !={}:
					for sMAC in self.selectBeaconsLogTimer:
						if beacon.find(sMAC[:self.selectBeaconsLogTimer[sMAC]]) ==0:
							self.indiLOG.log(10,"sel.beacon logging: CheckPeriod -0- :{};".format(beacon)  )
				changed = False
				if "status" not in self.beacons[beacon] : continue
				## pause is set at device stop, check if still paused skip


				if self.selectBeaconsLogTimer !={}:
					for sMAC in self.selectBeaconsLogTimer:
						if beacon.find(sMAC[:self.selectBeaconsLogTimer[sMAC]]) ==0:
							self.indiLOG.log(10,"sel.beacon logging: CheckPeriod -1- :{}; passed pause".format(beacon) )

				if self.beacons[beacon]["lastUp"] > 0:
					if self.beacons[beacon]["ignore"] == 1 :
						if time.time()- self.beacons[beacon]["lastUp"] > 3 * 86000 :  ## 3 days
							self.beacons[beacon]["ignore"] = 2
					# if self.beacons[beacon]["status"] =="expired": continue
					if self.beacons[beacon]["ignore"] > 0 : continue
				if self.selectBeaconsLogTimer !={}:
					for sMAC in self.selectBeaconsLogTimer:
						if beacon.find(sMAC[:self.selectBeaconsLogTimer[sMAC]]) ==0:
							self.indiLOG.log(10,"sel.beacon logging: CheckPeriod -2- :{}; passed ignore".format(beacon) )

				expT = float(self.beacons[beacon]["expirationTime"])
				if self.beacons[beacon]["lastUp"] < 0:	 # fast down was last                  event, block for 5 secs after that
					if time.time() + self.beacons[beacon]["lastUp"] > 5:
						self.beacons[beacon]["lastUp"] = time.time()- expT-0.1
					else:
						if self.selectBeaconsLogTimer !={}:
							for sMAC in self.selectBeaconsLogTimer:
								if beacon.find(sMAC[:self.selectBeaconsLogTimer[sMAC]]) ==0:
									self.indiLOG.log(10,"sel.beacon logging: CheckPeriod -3- :{};  no change in up status, dt:{:.0f}".format(beacon, time.time() + self.beacons[beacon]["lastUp"]) )
						continue

				delta = time.time()- self.beacons[beacon]["lastUp"]  ##  no !! - self.beacons[beacon]["updateSignalValuesSeconds"]

				if self.beacons[beacon]["status"] == "up" :
					if delta >  2*expT:
						self.beacons[beacon]["status"] = "expired"
					elif delta > expT :
						self.beacons[beacon]["status"] = "down"
						#self.indiLOG.log(10,	" up to down secs: delta= {}".format(delta) + " expT: {}".format(expT) + "  " + beacon)
						changed = True
						changed = True
				elif self.beacons[beacon]["status"] == "down" :
					if delta >  2*expT:
						self.beacons[beacon]["status"] = "expired"
						changed = True
				elif self.beacons[beacon]["status"] == "":
					self.beacons[beacon]["status"] = "expired"
					changed = True
				if	self.initStatesOnServer: changed = True
				if self.selectBeaconsLogTimer !={}:
					for sMAC in self.selectBeaconsLogTimer:
						if beacon.find(sMAC[:self.selectBeaconsLogTimer[sMAC]]) ==0:
							self.indiLOG.log(10,"sel.beacon logging: CheckPeriod -4- :{}; status: {};  deltaT: {}".format(beacon, self.beacons[beacon]["status"], delta))


				if changed or force:
					if self.decideMyLog("BeaconData"): self.indiLOG.log(5," CheckPeriod -5- :{}; changed=true or force {}" .format(beacon, self.beacons[beacon]["status"]) )

					self.statusChanged = 7

					try :
						dev = indigo.devices[self.beacons[beacon]["indigoId"]]
						props = dev.pluginProps
						if dev.states["groupMember"] != "": anyChange = True
						self.addToStatesUpdateDict(dev.id, "status", self.beacons[beacon]["status"])

						if self.beacons[beacon]["status"] == "up":
							if "closestRPI" in dev.states:
								closest =  self.findClosestRPI(beacon,dev)
								if closest != dev.states["closestRPI"]:
									if "{}".format(dev.states["closestRPI"]) != "-1":
										self.addToStatesUpdateDict(dev.id, "closestRPILast", dev.states["closestRPI"])
										self.addToStatesUpdateDict(dev.id, "closestRPITextLast", dev.states["closestRPIText"])
									self.addToStatesUpdateDict(dev.id, "closestRPI", closest)
									self.addToStatesUpdateDict(dev.id, "closestRPIText",self.getRPIdevName((closest)))
							if self.beacons[beacon]["note"].find("beacon")>-1:
								dev.updateStateImageOnServer(indigo.kStateImageSel.SensorOn) # not for RPI's

						elif self.beacons[beacon]["status"] == "down":
							if self.beacons[beacon]["note"].find("beacon") > -1:
								if "closestRPI" in dev.states:
									if closestRPI != dev.states["closestRPI"]:
										if "{}".format(dev.states["closestRPI"]) != "-1":
											self.addToStatesUpdateDict(dev.id, "closestRPILast", dev.states["closestRPI"])
											self.addToStatesUpdateDict(dev.id, "closestRPITextLast", dev.states["closestRPIText"])
									self.addToStatesUpdateDict(dev.id, "closestRPI", -1)
									if self.setClostestRPItextToBlank:self.addToStatesUpdateDict(dev.id, "closestRPIText", "")
								dev.updateStateImageOnServer(indigo.kStateImageSel.SensorOff)
							#else: this is handled in RPI update
							#	 dev.updateStateImageOnServer(indigo.kStateImageSel.Error)

						else:
							if self.beacons[beacon]["note"].find("beacon") > -1:
								dev.updateStateImageOnServer(indigo.kStateImageSel.SensorTripped)
								if "closestRPI" in dev.states:
									if closestRPI != dev.states["closestRPI"]:
										if "{}".format(dev.states["closestRPI"]) != "-1":
											self.addToStatesUpdateDict(dev.id, "closestRPILast", dev.states["closestRPI"])
											self.addToStatesUpdateDict(dev.id, "closestRPITextLast", dev.states["closestRPIText"])
									self.addToStatesUpdateDict(dev.id, "closestRPI", -1)
									if self.setClostestRPItextToBlank: self.addToStatesUpdateDict(dev.id, "closestRPIText", "")
							#else: this is handled in RPI update
							#	 dev.updateStateImageOnServer(indigo.kStateImageSel.Error)

						if "showBeaconOnMap" in props and props["showBeaconOnMap"] in _GlobalConst_beaconPlotSymbols:self.beaconPositionsUpdated =3

					except Exception as e:
						if "{}".format(e).find("timeout waiting") > -1:
							self.exceptionHandler(40, e)
							self.indiLOG.log(40,"BeaconsCheckPeriod communication to indigo is interrupted")
							return

				if now.minute != self.lastMinuteChecked:
					try :
						devId = int(self.beacons[beacon]["indigoId"])
						if devId > 0 :
							try:
								dev = indigo.devices[self.beacons[beacon]["indigoId"]]
								if self.beacons[beacon]["ignore"]	 == -1: # was special, device exists now, set back to normal
									self.indiLOG.log(10,"BeaconsCheckPeriod minute resetting ignore from -1 to 0 for beacon: {}   beaconDict: {}".format(beacon, self.beacons[beacon]))
									self.beacons[beacon]["ignore"] = 0
							except Exception as e:
								if "{}".format(e).find("timeout waiting") > -1:
									self.exceptionHandler(40, e)
									self.indiLOG.log(40,"BeaconsCheckPeriod communication to indigo is interrupted")
									return
								if "{}".format(e).find("not found in database") ==-1:
									self.exceptionHandler(40, e)
									return

								self.indiLOG.log(10,"=== deleting device beaconDict: {}".format(self.beacons[beacon]))
								self.beacons[beacon]["indigoId"] = 0
								self.beacons[beacon]["ignore"]	  = 1
								dev = ""
								continue

							if dev != "" and dev.states["status"] == "up":
								maxTimeWOutSignal = 330.
								try: 	 maxTimeWOutSignal = max(maxTimeWOutSignal,float(self.beacons[beacon]["expirationTime"]))
								except: pass

								for piU in _rpiBeaconList:
									piXX = "Pi_{:02d}".format(int(piU))
									if piXX+"_Distance" not in dev.states: continue
									if dev.states[piXX+"_Distance"] == 99999.: continue
									if dev.states[piXX+"_Time"] != "":
										piTime = self.getTimetimeFromDateString(dev.states[piXX+"_Time".format(int(piU))])
										if time.time()- piTime> max(maxTimeWOutSignal, self.beacons[beacon]["updateSignalValuesSeconds"]):
											self.addToStatesUpdateDict(dev.id,piXX+"_Distance", 99999.,decimalPlaces=1)
									else:
										self.addToStatesUpdateDict(dev.id,piXX+"_Distance", 99999.,decimalPlaces=1)

					except Exception as e:
						if "{}".format(e) != "None":
							self.exceptionHandler(40, e)
				if dev !="":
					self.executeUpdateStatesDict(onlyDevID=dev.id, calledFrom="BeaconsCheckPeriod end")

		except Exception as e:
			self.exceptionHandler(40, e)
			try: self.indiLOG.log(40,"============= {}".format(dev.name))
			except: pass
		return anyChange

####-------------------------------------------------------------------------####
	def checkHour(self,now):
		try:

			if now.hour == self.lastHourChecked: return
			if now.hour == 0:
				self.resetMinMaxSensors()
			self.rollOverRainSensors()

			self.fixConfig(checkOnly = ["all", "rpi", "force"],fromPGM="checkHour")
			if now.hour == 0 :
				self.checkPiEnabled()

			self.saveCARS(force=True)
			try:
				for beacon in copy.deepcopy(self.beacons):	 # sync with indigo
					if beacon.find("00:00:00:00") ==0: continue
					if self.beacons[beacon]["indigoId"] != 0:	# sync with indigo
						try :
							dev = indigo.devices[self.beacons[beacon]["indigoId"]]
							if self.beacons[beacon]["ignore"] == 1:
								self.indiLOG.log(10,"=== deleting device: {} beacon to be ignored, clean up ".format(dev.name))
								indigo.device.delete(dev)
								continue
							self.beacons[beacon]["status"] = dev.states["status"]
							self.beacons[beacon]["note"] = dev.states["note"]


							if self.removeJunkBeacons:
								if dev.name == "beacon_" + beacon and self.beacons[beacon]["status"] == "expired" and time.time()- self.beacons[beacon]["lastUp"] > 3600 and self.countLoop > 10 :
									self.indiLOG.log(30,"=== deleting beacon: {}  expired, no messages for > 1 hour and still old name, if you want to keep beacons, you must rename them after they are created".format(dev.name))
									self.beacons[beacon]["ignore"] = 1
									self.newIgnoreMAC += 1
									indigo.device.delete(dev)
						except Exception as e:
							if "{}".format(e) != "None":
								self.exceptionHandler(40, e)
							if "{}".format(e).find("timeout waiting") >-1:
								self.indiLOG.log(40,"communication to indigo is interrupted")
								return
							if "{}".format(e).find("not found in database") >-1:
								self.indiLOG.log(40,"=== deleting mark .. indigoId lookup error, setting to ignore beaconDict: {}".format(self.beacons[beacon]) )
								self.beacons[beacon]["indigoId"] = 0
								self.beacons[beacon]["ignore"]   = 1
								self.beacons[beacon]["status"]   = "ignored"
							else:
								return

					else :
						self.beacons[beacon]["status"] = "ignored"
						if self.beacons[beacon]["ignore"] == 0:
							self.indiLOG.log(10,"setting beacon: {}  to ignore --  was set to indigo-id=0 before".format(beacon) )
							self.indiLOG.log(10,"       contents: {}".format(self.beacons[beacon])  )
							self.beacons[beacon]["ignore"]	 = 1
							self.newIgnoreMAC 				+= 1
							self.writeJson(self.beacons, fName=self.indigoPreferencesPluginDir + "beacons", fmtOn=self.beaconsFileSort)


			except Exception as e:
				if "{}".format(e) != "None":
					self.exceptionHandler(40, e)

			try:
				if now.hour == 0:
					if self.cycleVariables:
						self.deleteAndCeateVariablesAndDeviceFolder(True)	# delete and recreate the variables at midnight to remove their sql database entries
					self.setALLrPiV("piUpToDate", ["updateParamsFTP"])
					##self.rPiRestartCommand = ["" for ii in range(_GlobalConst_numberOfRPI)] # dont do this use the default for each pibeacon
					self.setupFilesForPi()
					for piU in self.RPI:
						self.sendFilesToPiFTP(piU, expFile="updateParamsFTP.exp")
					self.updateRejectLists()
			except Exception as e:
				if "{}".format(e) != "None":
					self.exceptionHandler(40, e)
		except Exception as e:
			self.exceptionHandler(40, e)

####-------------------------------------------------------------------------####
	def checkDay(self,now):
			# do check once a day at 10 am

		if time.time() <= self.currentlyBooting + 130: return


		##### first check ibeacons battery updates:
		### get battery status from ibeacon
		try:
				for ii in range(len(self.checkBatteryLevelHours)):
					if self.lastDayChecked[ii] != now.day and now.hour == self.checkBatteryLevelHours[ii]:
						self.getBeaconParametersCALLBACKmenu(valuesDict={"piServerNumber":"all"}, force=False)
						self.lastDayChecked[ii] = now.day
						return
		except Exception as e:
			self.exceptionHandler(40, e)

		try:
		### report on bad ibeacon battery status
			if self.lastDayChecked[len(self.checkBatteryLevelHours)] != now.day and now.hour == 8:
				badBeacons	= 0
				testBeacons	= 0
				out			= ""
				for dev in indigo.devices.iter("props.isBeaconDevice"):
					props = dev.pluginProps
					if "batteryLevelUUID" not in props: 				continue
					if props["batteryLevelUUID"] != "gatttool":			continue
					if "batteryLevel" not in dev.states: 				continue
					if "lastUpdateBatteryLevel" not in dev.states: 		continue
					if  not dev.enabled:						 		continue

					testBeacons += 1
					try: 	batteryLevel = int(dev.states["batteryLevel"])
					except: batteryLevel = 0
					lastUpdateBatteryLevel = dev.states["lastUpdateBatteryLevel"]
					if len(lastUpdateBatteryLevel) < 19: lastUpdateBatteryLevel = "2000-01-01 00:00:00"
					lastTimeStamp = self.getTimetimeFromDateString(lastUpdateBatteryLevel)
					#self.indiLOG.log(5,"  ibeacon: {:30s}  level: {:3d}%,  last update was: {} ".format(dev.name, batteryLevel, lastUpdateBatteryLevel) )
					if time.time() - lastTimeStamp > 2*24*3600:
						badBeacons+=1
						out += "{:40s}last level reported: {:3d}%, has not been updated for > 2 days: {}; clostest RPI:{}\n".format(dev.name, batteryLevel, lastUpdateBatteryLevel, dev.states["closestRPIText"])
						#trigger  tbi
					elif batteryLevel < 20:
						badBeacons+=1
						out += "{:40s}      level down to: {:3d}% ... charge or replace battery; clostest RPI:{}\n".format(dev.name, batteryLevel, dev.states["closestRPIText"] )
						#trigger tbi
				if out != "":
					self.indiLOG.log(30,"batterylevel level test:\n{}".format(out) )
				elif testBeacons > 0 and badBeacons == 0: self.indiLOG.log(10,"batterylevel level test:  no iBeacon found with low battery indicator or old update")
				self.lastDayChecked[len(self.checkBatteryLevelHours)] = now.day


		except Exception as e:
			self.exceptionHandler(40, e)

		##### second .. nothing yet

		return



####-------------------------------------------------------------------------####
	def checkPiEnabled(self): # check if pi is defined, but not enabled, give warning at startup
		try:
			for piU in self.RPI:
				if self.RPI[piU]["piOnOff"] != "0": continue
				if self.RPI[piU]["piDevId"] ==	   0: continue

				if (self.RPI[piU]["passwordPi"]		 	!=""  and
					self.RPI[piU]["userIdPi"]			 !=""  and
					self.RPI[piU]["ipNumberPi"]			 != "" and
					self.RPI[piU]["piMAC"]				 != ""):
						self.indiLOG.log(10,"pi# {} is configured but not enabled, mistake? This is checked once a day;  to turn it off set userId or password of unused rPi to empty ".format(piU))
		except Exception as e:
			self.exceptionHandler(40, e)

####-------------------------------------------------------------------------####
	def syncSensors(self):
		try:
			anyChange = False
			#ss = time.time()
			for dev in indigo.devices.iter("props.isSensorDevice, props.isOutputDevice"):
				sensor = dev.deviceTypeId
				devId  = dev.id
				props  = dev.pluginProps
				testpiU  =[]
				if "rPiEnable0" in props:
					for piU in _rpiBeaconList:
						testpiU.append(piU)
				elif "piServerNumber" in props:
						testpiU.append(props["piServerNumber"])

				for pix in testpiU:
					try:
						pi = int(pi)
						piU = "{}".format(pi)
					except:
						continue
					if self.checkDevToPi(piU, devId, dev.name, "input", "in",  sensor, _GlobalConst_allowedSensors + _BLEsensorTypes): anyChange= True
					#indigo.server.log("syncSensors A01: {}".format(anyChange)+"  {}".format(time.time() - ss))
					if self.checkDevToPi(piU, devId, dev.name, "output", "out", sensor, _GlobalConst_allowedOUTPUT):  anyChange= True

					if "description" in props:
						if props["description"] !="" and props["description"] != dev.description:
							dev.description =  props["description"]
							dev.replaceOnServer()
							anyChange = True

			for piU in self.RPI:
				self.checkSensortoPi(piU, "input")
				self.checkSensortoPi(piU, "output")
				if self.mkSensorList(piU): anyChange =True
			#indigo.server.log("syncSensors BT: {}".format(anyChange)+"  {}".format(time.time() - ss))

		except Exception as e:
			self.exceptionHandler(40, e)
		return anyChange



####-------------------------------------------------------------------------####
	def checkDevToPi(self, piU, devId, name, io, io2, sensor, allowedS):
		try:
			anyChange = False
			if sensor not in allowedS: return False

			if sensor not in self.RPI[piU][io]:
				try:
					dev=indigo.devices[int(devId)]
					name=dev.name
				except Exception as e:

					self.exceptionHandler(40, e)
					if "{}".format(e).find("timeout waiting") > -1:
						self.indiLOG.log(40,"communication to indigo is interrupted")
						return False
					if "{}".format(e).find("not found in database") ==-1:
						return False
					name=""
				self.indiLOG.log(10,"fixing 1  {}   {} pi {}; sensor: {} devName: {}".format(name, devId, piU, sensor, name) )
				self.indiLOG.log(10,"fixing 1  rpi {}".format(self.RPI[piU][io]))
				self.RPI[piU][io][sensor] = {"{}".format(devId): ""}
				self.setONErPiV(piU, "piUpToDate", ["updateParamsFTP"])
				anyChange = True
			if len(self.RPI[piU][io][sensor]) == 0:
				self.RPI[piU][io][sensor] = {"{}".format(devId): ""}
				anyChange = True

			elif "{}".format(devId) not in self.RPI[piU][io][sensor]:
				self.indiLOG.log(10,"fixing 2  {}   {}  pi {} sensor{}".format(name, devId, piU, sensor) )
				self.RPI[piU][io][sensor]["{}".format(devId)] = ""
				anyChange = True
		except Exception as e:
			self.exceptionHandler(40, e)
		return anyChange



####-------------------------------------------------------------------------####
	def checkSensortoPi(self, pi, io):
		try:
			anyChange = False
			piU = "{}".format(pi)
			pi = int(pi)
			for sensor in self.RPI[piU][io]:
				if len(self.RPI[piU][io][sensor]) > 0:
					deldevID = {}
					for devIDrpi in self.RPI[piU][io][sensor]:
						try:
							try:
								devID = int(devIDrpi)
								dev = indigo.devices[devID]
							except Exception as e:
								if "{}".format(e).find("timeout waiting") > -1:
									self.exceptionHandler(40, e)
									self.indiLOG.log(40,"communication to indigo is interrupted")
									return True
								if "{}".format(e).find(" not found in database") ==-1:
									self.exceptionHandler(40, e)
									return True

								deldevID[devIDrpi] = 1
								self.indiLOG.log(30,"device not found in indigo DB, ok if device was just deleted")
								self.indiLOG.log(30,"removing input device from parameters for pi#:{}  devID={}".format(piU, devIDrpi))
								anyChange = True
								continue


							props = dev.pluginProps
							if "rPiEnable"+piU not in props and  "piServerNumber" not in props:
								self.indiLOG.log(10,"piServerNumber not in props for pi#: {}  devID= {}   removing sensor{}".format(piU, devID, self.RPI[piU][io][sensor]) )
								self.RPI[piU][io][sensor] = {}
								anyChange = True
								continue

							if "piServerNumber" in props and "rPiEnable"+piU not in props:
								if sensor != dev.deviceTypeId or devID != dev.id or piU != props["piServerNumber"]:
									self.indiLOG.log(10,"sensor/devid/pi/wrong for  pi#: {}  devID= {} props{}\n >>>>> removing sensor <<<<".format(piU, self.RPI[piU][io][sensor], "{}".format(props)) )
									self.RPI[piU][io][sensor] = {}
									anyChange = True
								if dev.deviceTypeId  not in _BLEsensorTypes:
									if "address" in props:
										if props["address"] != "Pi-" + piU:
											props["address"] = "Pi-" + piU
											if self.decideMyLog("Logic"): self.indiLOG.log(5,"updating address for {}".format(piU) )
											dev.replacePluginPropsOnServer(props)
											anyChange = True
									else:
											props["address"] = "Pi-" + piU
											dev.replacePluginPropsOnServer(props)
											if self.decideMyLog("Logic"): self.indiLOG.log(5,"updating address for {}".format(piU) )
											anyChange = True

							if  "rPiEnable"+piU in props:
								if sensor != dev.deviceTypeId or devID != dev.id or not props["rPiEnable"+piU]:
									self.indiLOG.log(10,"sensor/devid/pi/wrong for  pi#: {}  devID= {} props{}\n >>>>> removing sensor <<<<".format(piU, self.RPI[piU][io][sensor], "{}".format(props)) )
									self.RPI[piU][io][sensor] = {}
									anyChange = True
							else:
								pass

						except Exception as e:
							self.exceptionHandler(40, e)
							if "{}".format(e).find("not found in database") ==-1:
								return True
							self.indiLOG.log(40,"removing input device from parameters for pi# {}  {}".format(piU, self.RPI[piU][io][sensor]) )
							deldevID[devIDrpi] = 1
					for devIDrpi in deldevID:
						del self.RPI[piU][io][sensor][devIDrpi]
						anyChange = True

			delsen = {}
			for sensor in self.RPI[piU][io]:
				if len(self.RPI[piU][io][sensor]) == 0:
					delsen[sensor] = 1
			for sensor in delsen:
				anyChange = True
				del self.RPI[piU][io][sensor]

		except Exception as e:
			self.exceptionHandler(40, e)
		return anyChange

####----------------------reset sensor min max at midnight -----------------------------------####
	def resetMinMaxSensors(self, init=False):
		try:
			dd = datetime.datetime.now()
			nHour = dd.hour
			day = dd.day
			try:	resetMinMaxDayDoneToday = float(self.pluginPrefs.get("resetMinMaxDayDoneToday", -1.))
			except:	resetMinMaxDayDoneToday = -1.


			if time.time() - resetMinMaxDayDoneToday > 3600.:
				for dev in indigo.devices.iter(self.pluginId):
					if dev.enabled:
						try:
							for ttx in _GlobalConst_fillMinMaxStates:
								if ttx in dev.states and ttx+"MaxToday" in dev.states:
									try:	val = float(dev.states[ttx])
									except: val = 0
									try:
										xxx = "{}".format(dev.states[ttx]).split(".")
										if len(xxx) == 1:
											decimalPlaces = 0
										else:
											decimalPlaces = len(xxx[1])
									except:
										decimalPlaces = 2


									if init: # at start of pgm
										reset = False
										try: 	int(dev.states[ttx+"MinYesterday"])
										except:	reset = True

										if not reset:
											try:
												if (float(dev.states[ttx+"MaxToday"]) == float(dev.states[ttx+"MinToday"]) and float(dev.states[ttx+"MaxToday"]) == 0. and
												 	ttx+"MeasurementsToday" in dev.states and  str(dev.states[ttx+"MeasurementsToday"]) == "0"):	 reset = True
											except: pass

										if reset: # ony if not initialized
											self.addToStatesUpdateDict(dev.id,ttx+"MaxYesterday",	val,decimalPlaces=decimalPlaces)
											self.addToStatesUpdateDict(dev.id,ttx+"MinYesterday",	val,decimalPlaces=decimalPlaces)
											self.addToStatesUpdateDict(dev.id,ttx+"MaxToday",		val,decimalPlaces=decimalPlaces)
											self.addToStatesUpdateDict(dev.id,ttx+"MinToday",		val,decimalPlaces=decimalPlaces)
											if ttx+"MeasurementsToday" in dev.states: 
												self.addToStatesUpdateDict(dev.id,ttx+"MeasurementsYesterday",		dev.states[ttx+"MeasurementsToday"],	decimalPlaces=0)
												self.addToStatesUpdateDict(dev.id,ttx+"MeasurementsToday", 			1, 										decimalPlaces=0)

									elif nHour == 0:	 # update at midnight
										self.addToStatesUpdateDict(dev.id,ttx+"MaxYesterday",	dev.states[ttx+"MaxToday"], decimalPlaces=decimalPlaces)
										self.addToStatesUpdateDict(dev.id,ttx+"MinYesterday",	dev.states[ttx+"MinToday"], decimalPlaces=decimalPlaces)
										self.addToStatesUpdateDict(dev.id,ttx+"MaxToday",		dev.states[ttx],			decimalPlaces=decimalPlaces)
										self.addToStatesUpdateDict(dev.id,ttx+"MinToday",		dev.states[ttx], 			decimalPlaces=decimalPlaces)
										if ttx+"AveToday" in dev.states: 
											self.addToStatesUpdateDict(dev.id,ttx+"AveYesterday",	dev.states[ttx+"AveToday"], decimalPlaces=decimalPlaces)
											self.addToStatesUpdateDict(dev.id,ttx+"AveToday",		dev.states[ttx], 			decimalPlaces=decimalPlaces)
											if ttx+"MeasurementsToday" in dev.states: 
												self.addToStatesUpdateDict(dev.id,ttx+"MeasurementsYesterday",		dev.states[ttx+"MeasurementsToday"],	decimalPlaces=0)
												self.addToStatesUpdateDict(dev.id,ttx+"MeasurementsToday", 			1, 										decimalPlaces=0)
						except Exception as e:
							if "{}".format(e) != "None":
								self.exceptionHandler(40, e)
						self.executeUpdateStatesDict(onlyDevID=dev.id, calledFrom="resetMinMaxSensors")
				self.pluginPrefs["resetMinMaxDayDoneToday"] = time.time()
		except Exception as e:
			self.exceptionHandler(40, e)

####----------------------reset sensor min max at midnight -----------------------------------####
	def fillMinMaxSensors(self, dev, stateName, value, decimalPlaces):
		try:
			if value == "": return
			if stateName not in _GlobalConst_fillMinMaxStates: return
			if stateName in dev.states and stateName+"MaxToday" in dev.states:
				val = float(value)
				if val > float(dev.states[stateName+"MaxToday"]):
					self.addToStatesUpdateDict(dev.id,stateName+"MaxToday",	 val, decimalPlaces=decimalPlaces)
				if val < float(dev.states[stateName+"MinToday"]):
					self.addToStatesUpdateDict(dev.id,stateName+"MinToday",	 val, decimalPlaces=decimalPlaces)
				if stateName+"AveToday" in dev.states and stateName+"MeasurementsToday" in dev.states:
						currentAve = dev.states[stateName+"AveToday"]
						nMeas = max(0,dev.states[stateName+"MeasurementsToday"])
						newAve = ( currentAve*nMeas + val )/ (nMeas+1)
						if decimalPlaces == 0: newAve = int(newAve)
						self.addToStatesUpdateDict(dev.id,stateName+"AveToday",	 newAve, decimalPlaces=decimalPlaces)
						self.addToStatesUpdateDict(dev.id,stateName+"MeasurementsToday", nMeas+1, decimalPlaces=0)
					


		except Exception as e:
			self.exceptionHandler(40, e)

####----------------------reset rain sensor every hour/day/week/month/year -----------------------------------####
	def rollOverRainSensors(self):
		try:
			dd = datetime.datetime.now()
			currDate = (dd.strftime("%Y-%m-%d-%H")).split("-")
			weekNumber = dd.isocalendar()[1]

			#self.indiLOG.log(10,	"currDate: {}".format(currDate), mType="rollOverRainSensors")
			for dev in indigo.devices.iter("props.isSensorDevice"):
				if dev.deviceTypeId.find("rainSensorRG11") == -1: continue
				if	not dev.enabled: continue
				props = dev.pluginProps
				lastTest = props["lastDateCheck"].split("-")
				try:
					ff = datetime.datetime.strptime(props["lastDateCheck"], "%Y-%m-%d-%H")
					lastweek = ff.isocalendar()[1]
				except:
					lastweek = -1

				#self.indiLOG.log(10,	"lasttest: {}".format(lastTest), mType="rollOverRainSensors")
				oneUpdate = False
				for test in ["hour", "day", "week", "month", "year"]:
					if test == "hour"	and int(lastTest[3]) == int(currDate[3]): continue
					if test == "day"	and int(lastTest[2]) == int(currDate[2]): continue
					if test == "month"	and int(lastTest[1]) == int(currDate[1]): continue
					if test == "year"	and int(lastTest[0]) == int(currDate[0]): continue
					if test == "week"	and lastweek		 == weekNumber:		  continue
					oneUpdate = True
					ttx = test+"Rain"
					val = dev.states[ttx]
					#self.indiLOG.log(10,	"rolling over: {}".format(ttx)+";  using current val: {}".format(val), mType="rollOverRainSensors")
					self.addToStatesUpdateDict(dev.id, "last"+ttx, val,decimalPlaces=self.rainDigits)
					self.addToStatesUpdateDict(dev.id,ttx, 0,decimalPlaces=self.rainDigits)

				if oneUpdate: 
					props["lastDateCheck"] = dd.strftime("%Y-%m-%d-%H")
					dev.replacePluginPropsOnServer(props)
				self.executeUpdateStatesDict(onlyDevID=dev.id, calledFrom="rollOverRainSensors")
		except Exception as e:
			self.exceptionHandler(40, e)


####-------------------------------------------------------------------------####
	def mkSensorList(self, pi):
		try:
			anyChange = False
			sensorList = ""
			INPgpioTypes = []
			piU = "{}".format(pi)
			for sensor in self.RPI[piU]["input"]:
				if sensor not in _GlobalConst_allowedSensors and sensor not in _BLEsensorTypes: continue
				if sensor =="ultrasoundDistance": continue
				try:
					#					 devId= int(self.RPI[piU]["input"][sensor].keys()[0])# we only need the first one
					for devIds in self.RPI[piU]["input"][sensor]:
						devId = int(devIds)
						if devId < 1: xxx=1 / 0
						dev = indigo.devices[devId]
						props = dev.pluginProps
						if dev.enabled:
							sensorList += sensor+"*{}".format(devId)	 # added; below only works if just one BLE if several and only one gets disabled it is still present, hence we need to add extra
							if "i2cAddress" in props:
								sensorList+= "*"+props["i2cAddress"]
							if "spiAddress" in props:
								sensorList+= "*"+props["spiAddress"]
							if "gpioPin" in props:
								sensorList+= "*"+props["gpioPin"]
							if "gain" in props:
								sensorList+= "*"+props["gain"]
							if "sps" in props:
								sensorList+= "*"+props["sps"]
							sensorList+=","

				except Exception as e:
					self.exceptionHandler(40, e)
					if "{}".format(e).find("timeout waiting") > -1:
						self.indiLOG.log(40,"communication to indigo is interrupted")
						return
					if "{}".format(e).find("not found in database") == -1:
						return
					self.RPI[piU]["input"][sensor] = {}
			if sensorList != self.RPI[piU]["sensorList"]:
				self.setONErPiV(piU, "piUpToDate", ["updateParamsFTP"])
				anyChange = True
			self.RPI[piU]["sensorList"] = sensorList

		except Exception as e:
			self.exceptionHandler(40, e)
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
			if newVar.name.find("pi_IN_") != 0:   return
			if len(newVar.value) < 3:			   return
			theValue = newVar.value

			if theValue.find("NaN") > -1:
				theValue = theValue.replace("NaN","-9999")
			self.addToDataQueue(newVar.name, json.loads(theValue), theValue )
			return
		except Exception as e:
			self.exceptionHandler(40, e)
			self.indiLOG.log(40,newVar.value)


####-------------------------------------------------------------------------####
	def addToDataQueue(self,  varNameIN, varJson, varUnicode):	#
		try:
			if not self.stackReady : return



			## alive message?
			if varNameIN == "pi_IN_Alive":
				self.updateRPIAlive(varJson,varUnicode, time.time())
				return

			## check pi#s  etc
			try:
				pi = int(varNameIN.split("_IN_")[1])
				piU = "{}".format(pi)  ## it is pi_IN_0 .. pi_IN_99
			except:
				self.indiLOG.log(10,"bad data  Pi not integer:  {}".format(varNameIN) )
				return

			if self.trackRPImessages == pi:
				self.indiLOG.log(10,"pi# {} msg tracking: {} ".format(piU, varUnicode ) )

			if piU not in _rpiList:
				self.indiLOG.log(10,"pi# rejected outside range:  {}".format(varNameIN) )
				return


			#if piU == "3" : self.indiLOG.log(20,"updateSensors    varUnicode: {}" .format( varUnicode))

			self.upDateHCIinfo(piU, varJson, varUnicode)

			## add to message queue
			self.beaconMessages["data"].put((time.time(), piU, varJson, varUnicode))

			##
			# update non competing stuff, does not have be done sequential
			##
			# update RPI expirations
			self.RPI[piU]["lastMessage"] = time.time()
			self.setRPIonline(piU, setLastMessage=True)

			# error message
			if "data" in varJson and "error" in varJson["data"]:
				self.indiLOG.log(40,"pi#{} error message{}".format(piU, varJson["data"]["error"]) )

			##
			# update sensors
			if "sensors" in varJson:
				if "BLEconnect" in varJson["sensors"]:
					self.BLEconnectupdateAll(piU, varJson["sensors"])
				self.updateSensors(piU, varJson["sensors"])


			# print BLE report
			if  "trackMac" in varJson:
				#self.indiLOG.log(20,varNameIN+"  " + varUnicode[0:100])
				self.printtrackMac(piU, varJson["trackMac"])


			# print BLE report
			if  "BLEAnalysis" in varJson:
				#self.indiLOG.log(20,varNameIN+"  " + varUnicode[0:100])
				self.printBLEAnalysis(piU, varJson["BLEAnalysis"])

			##
			# update outputState
			if "outputs" in varJson:
				self.updateOutput(piU, varJson["outputs"])

			##
			if "BLEreport" in varJson:
				self.printBLEreport(varJson["BLEreport"])
				return

			##
			if "i2c" in varJson:
				self.checkI2c(piU, varJson["i2c"])

			##
			if "bluetooth" in varJson:
				self.checkBlueTooth(piU, varJson["bluetooth"])



		except Exception as e:
			self.exceptionHandler(40, e)
			self.indiLOG.log(40,varNameIN+"  " + varUnicode[0:30])




####-------------------------------------------------------------------------####
####------------------beacon  queue management ------------------------
####-------------------------------------------------------------------------####
	def startbeaconMessageQueue(self):

		if self.beaconMessages == {}:
			self.beaconMessages["thread"]		= ""
			self.beaconMessages["data"]		= Queue.Queue()
			self.beaconMessages["state"]		= ""

		if self.beaconMessages["state"] == "running":
				self.indiLOG.log(10,"no need to start Thread, workOnBeaconMessages already running" )
				return

		self.beaconMessages["lastCheck"] = time.time()
		self.beaconMessages["state"] = "started"
		self.sleep(0.1)
		self.beaconMessages["thread"]  = threading.Thread(name='workOnBeaconMessages', target=self.workOnBeaconMessages)
		self.beaconMessages["thread"].start()
		return

####-------------------------------------------------------------------------####
	def stopbeaconMessageQueue(self):
		self.beaconMessages["state"] = "stop"
		self.indiLOG.log(10,"Stopping   thread for beaconMessages, state is: {}".format(self.beaconMessages["state"]) )
		return 

####-------------------------------------------------------------------------####
	def workOnBeaconMessages(self):

		try:
			self.indiLOG.log(10," .. (re)starting   thread for beaconMessages , state is: {}".format(self.beaconMessages["state"]) )
			self.beaconMessages["state"] = "running"
			beaconUpdatedIds = []
			lastPi = ""
			self.queueList = "update"
			while self.beaconMessages["state"] == "running":
				try:
					while not self.beaconMessages["data"].empty():
						if self.beaconMessages["state"] != "running":	break
						if self.pluginState == "stop": 				break

						item = self.beaconMessages["data"].get()
						if self.queueList != "update":
							for ii in range(200):
								if self.queueList == "update"	: break
								if self.queueList == ""		: break
								if ii > 0:	pass
								self.sleep(0.01)
							self.queueList = "update"

						if lastPi != "" and lastPi != item[1] and beaconUpdatedIds !=[]:
							self.findClosestiBeaconToRPI(lastPi, beaconUpdatedIds=beaconUpdatedIds, BeaconOrBLE="beacon")
							self.executeUpdateStatesDict(calledFrom="workOnBeaconMessages(1)")
							beaconUpdatedIds = []
						lastPi = item[1]
						beaconUpdatedIds += self.execBeaconUpdate(item[0],item[1],item[2],item[3])
						#### indigo.server.log("{}".format(item[1])+"  {}".format(beaconUpdatedIds)+" "+ item[3])
						self.beaconMessages["data"].task_done()

					if lastPi != "" and beaconUpdatedIds !=[]:
						self.findClosestiBeaconToRPI(lastPi, beaconUpdatedIds=beaconUpdatedIds, BeaconOrBLE="beacon")
						self.executeUpdateStatesDict(calledFrom="workOnBeaconMessages(2)")
					lastPi = ""
					beaconUpdatedIds = []
					self.queueList = ""
					self.sleep(0.05)
				except Exception as e:
					if "{}".format(e) != "None":
						self.exceptionHandler(40, e)


			self.beaconMessages["state"] = "stopped - exiting thread"
			self.indiLOG.log(10," .. stopped   thread for beaconMessages, state is: {}".format(self.beaconMessages["state"]) )
		except Exception as e:
			self.exceptionHandler(40, e)
			self.indiLOG.log(40,varNameIN+"  " + varUnicode[0:30])
		return 
####-------------------------------------------------------------------------####
	def execBeaconUpdate(self, timeStampOfReceive, pi, data, varUnicode):

		beaconUpdatedIds = []
		try:

			if "msgs" not in data: return beaconUpdatedIds
			piU = "{}".format(pi)
			retCode, piMAC, piN = self.checkincomingMACNo(data, piU, timeStampOfReceive)
			if not retCode: return beaconUpdatedIds
			if piU not in  _rpiBeaconList: return beaconUpdatedIds


			### here goes the beacon data updates  -->

			if self.selectBeaconsLogTimer !={}:
				for sMAC in self.selectBeaconsLogTimer:
					if piMAC.find(sMAC[:self.selectBeaconsLogTimer[sMAC]]) ==0:
						self.indiLOG.log(10,"sel.beacon logging: RPI MAC#:{} ; pi#={} ".format(piMAC, piU) )

			if "piMAC" in data:
				if self.decideMyLog("BeaconData"): self.indiLOG.log(5,"new iBeacon message----------------------------------- \n {}".format(varUnicode) )
				secondsCollected = 0
				if "secsCol" in data:
					secondsCollected = data["secsCol"]
				msgs = data["msgs"]
				if len(msgs) > 0 and piMAC != "":
					if "ipAddress" in data:
						ipAddress = data["ipAddress"]
					else:
						self.indiLOG.log(30,"rPi#:{} {}: ipAddress not in data".format(piU, self.RPI[piU]["ipNumberPi"]))
						return beaconUpdatedIds

					if ipAddress == "":
						self.setONErPiV(piU, "piUpToDate", ["updateParamsFTP", "rebootSSH"])
						self.indiLOG.log(30,"rPi#: {}  ip# send from rPi is empty, you should restart rPi, ip# should be {}".format(piU, self.RPI[piU]["ipNumberPi"] ))
						return beaconUpdatedIds

					if self.RPI[piU]["ipNumberPi"] != ipAddress:
						self.indiLOG.log(30,"rPi#:{} {}: IP number has changed to {}, please fix in menu/pibeacon/setup RPI to reflect changed IP number or fix IP# on RPI\n this can happen when WiFi and ethernet are both active, try setting wlan/eth parameters in RPI device edit;  ==> ignoring data".format(piU, self.RPI[piU]["ipNumberPi"], ipAddress ))
						self.RPI[piU]["ipNumberPi"] = ipAddress

					beaconUpdatedIds = self.updateBeaconStates(piU, piN, ipAddress, piMAC, secondsCollected, msgs)
					self.RPI[piU]["emptyMessages"] = 0

				elif len(msgs) == 0 and piMAC != "":
					self.RPI[piU]["emptyMessages"] +=1
					if	self.RPI[piU]["emptyMessages"] >  min(self.enableRebootRPIifNoMessages,10) :
						if	self.RPI[piU]["emptyMessages"] %5 ==0:
							self.indiLOG.log(10,"RPI# {} check , too many empty messages in a row: {}".format(piU, self.RPI[piU]["emptyMessages"]) )
							self.indiLOG.log(10," please check RPI" )
						if	self.RPI[piU]["emptyMessages"] > self.enableRebootRPIifNoMessages:
							self.indiLOG.log(30,"RPI# {} check , too many empty messages in a row: {}".format(piU, self.RPI[piU]["emptyMessages"]) )
							self.indiLOG.log(30,"sending reboot command to RPI")
							self.setONErPiV(piU, "piUpToDate",["updateParamsFTP", "rebootSSH"])
							self.RPI[piU]["emptyMessages"] = 0
				else:
						self.indiLOG.log(30,"rPi#:{} {}: piMAC empty ".format(piU, self.RPI[piU]["ipNumberPi"]))
						return beaconUpdatedIds

		except Exception as e:
			self.exceptionHandler(40, e)
			self.indiLOG.log(40,varUnicode)
		return beaconUpdatedIds

####-------------------------------------------------------------------------####
	def findClosestiBeaconToRPI(self, piU, beaconUpdatedIds=[], BeaconOrBLE=""):
		try:
			if BeaconOrBLE !="beacon": 		return
			if len(beaconUpdatedIds) ==0: 	return
			if piU not in _rpiBeaconList: 	return

			rpiDev = indigo.devices[self.RPI[piU]["piDevId"]]
			if "closestiBeacon" not in rpiDev.states:		return

			rpiProps = rpiDev.pluginProps
			cutOffForClosestBeacon = 300
			if "cutOffForClosestBeacon" in rpiProps:
				try:	cutOffForClosestBeacon = float(rpiprops["cutOffForClosestBeacon"])
				except:	pass
			cutOffForClosestBeacon /= self.distanceUnits
			closestName = ""
			closestDist = 99999

			for tup in beaconUpdatedIds:
				piIn	= tup[0]
				devid	= tup[1]
				dist	= tup[2]
				if dist > cutOffForClosestBeacon:															continue
				dev		= indigo.devices[devid]

				if not dev.enabled:																			continue
				if not dev.onState:																			continue

				props = dev.pluginProps
				if "isRPIDevice" 		in props:															continue
				if "isRPISensorDevice"	in props:															continue
				if "IgnoreBeaconForClosestToRPI" in props and props["IgnoreBeaconForClosestToRPI"] !="0":	continue



				try:
					if dist  < closestDist:
						closestDist = dist
						closestName = dev.name
				except Exception as e:
					self.exceptionHandler(40, e)

			if closestDist < cutOffForClosestBeacon:
					cN = closestName+"@{}".format(closestDist)
					if rpiDev.states["closestiBeacon"] !=cN:
						self.addToStatesUpdateDict("{}".format(rpiDev.id), "closestiBeacon", cN)
						self.addToStatesUpdateDict("{}".format(rpiDev.id), "closestiBeaconLast", rpiDev.states["closestiBeacon"])
			else:
				if rpiDev.states["closestiBeacon"] != "None":
					self.addToStatesUpdateDict("{}".format(rpiDev.id), "closestiBeacon", "None")


		except Exception as e:
			self.exceptionHandler(40, e)


####-------------------------------------------------------------------------####
	def checkincomingMACNo(self, data, pi, timeStampOfReceive):

		piU = "{}".format(pi)
		piMAC = ""
		piN   = -1
		try:

			if "piMAC" in data:
				piMAC = "{}".format(data["piMAC"])
			if piMAC == "0" or piMAC == "":
				#self.indiLOG.log(10,"checkincomingMACNo, piMAC is wrong# {};  piU:{}, data:{}".format(piMAC, pi, data) )
				return False, "", ""

			#if str(pi) =="9": self.indiLOG.log(10,"receiving: pi "+piU+"  piMAC:" + piMAC)
			piN = int(data["pi"])
			piNU = "{}".format(piN)
			if piNU not in _rpiList :
				self.indiLOG.log(30,"bad data  Pi# not in range: {}".format(piNU))
				return	False, "", ""

			try:
				devPI = indigo.devices[self.RPI[piNU]["piDevId"]]
				if "ts" in data and devPI !="":
					self.compareRpiTime(data, piU, devPI, timeStampOfReceive)
			except:
				pass

			if piU not in _rpiBeaconList:
				self.checkSensorPiSetup(piU, data, piNU)
				return True, piMAC, piNU

			if piMAC !="":
				beacon = self.RPI[piU]["piMAC"]
				if piMAC != beacon:
					self.indiLOG.log(10,"MAC# from RPI message, has new MAC# {} changing to new BLE-MAC number, old MAC#{}--  pi# {}".format(piMAC, beacon, piU) )
					beacon = piMAC
				if len(beacon) == 17: ## len("11:22:33:44:55:66")
						indigoId = int(self.RPI[piU]["piDevId"])
						if len(self.RPI[piU]["piMAC"]) != 17 or indigoId == 0:
							self.indiLOG.log(5,"MAC# from RPI message is new {} not in internal list .. new RPI?{}".format(beacon, piU))

						else: # existing RPI with valid MAC # and indigo ID
							if self.RPI[piU]["piMAC"] != beacon and indigoId > 0:
								try:
									devPI = indigo.devices[indigoId]
									props= devPI.pluginProps
									props["address"] = beacon
			
									devPI.replacePluginPropsOnServer(props)
									if self.RPI[piU]["piMAC"] in self.beacons:
										self.beacons[beacon]			 = copy.deepcopy(self.beacons[self.RPI[piU]["piMAC"]] )
									else:
										self.beacons[beacon]			 = copy.deepcopy(_GlobalConst_emptyBeacon)

									self.beacons[piMAC]["indigoId"] = indigoId
									self.RPI[piU]["piMAC"] = beacon
									if self.decideMyLog("Logic"): self.indiLOG.log(5,"MAC# from RPI  was updated")
								except Exception as e:
									self.exceptionHandler(40, e)
									if self.decideMyLog("Logic"): self.indiLOG.log(5,"MAC# from RPI...	 indigoId: {} does not exist, ignoring".format(indigoId) )

						# added to cover situation when RPI was set to expire by mistake ==>  reset it to ok
						if beacon in self.beacons:
							if self.beacons[beacon]["ignore"] > 0: self.beacons[beacon]["ignore"] = 0
							self.beacons[beacon]["lastUp"] = time.time()

		except Exception as e:
			self.exceptionHandler(40, e)
			return False, "", ""

		return True, piMAC, piNU



####-------------------------------------------------------------------------####
	def compareRpiTime(self, data, pi, devPI, timeStampOfReceive):
		piU = "{}".format(pi)
		pi = int(pi)
		dt = time.time() - timeStampOfReceive
		if dt > 4.: self.indiLOG.log(5,"significant internal delay occured digesting data from rPi:{}    {:.1f} [secs]".format(piU, dt) )
		try:
			if "ts" not in data: return
			tzMAC = time.tzname[1]
			if len(tzMAC) <3: tzMAC=time.tzname[0]
			if "deltaTime" in data:
				self.RPI[piU]["deltaTime1"] = data["deltaTime"]
			else:
				deltaTime = 0


			if "ts" not in data:
				return
			if "time" not in data["ts"]:
				return
			ts = data["ts"]["time"]
			tz = data["ts"]["tz"]
			try:	  deltaT = time.time()- ts
			except:	  deltaT = 101
			self.RPI[piU]["deltaTime2"] = deltaT

			props = devPI.pluginProps
			if "syncTimeWithMAC" in props and props["syncTimeWithMAC"] !="" and props["syncTimeWithMAC"] =="0": return

			if tz!= tzMAC:
				if self.timeErrorCount[pi]	 < 2:
					self.indiLOG.log(10,"rPi "+piU+" wrong time zone: " + tz + "    vs "+ tzMAC+"    on MAC ")
					self.timeErrorCount[pi] +=1
					return

			if devPI !="":
					try:
						sT= float(props["syncTimeWithMAC"])
						if abs(time.time()-float(ts)) > sT and tz == tzMAC and self.timeErrorCount[pi] < 5:
							self.timeErrorCount[pi]  +=5
							alreadyUnderway = False
							for action in self.actionList:
								if "action" in action and action["action"] == "setTime" and action["value"] == piU:
									alreadyUnderway = True
									break
							if not alreadyUnderway:
								self.actionList.append({"action":"setTime", "value":piU})
								self.indiLOG.log(10,"rPi {:} do a time sync MAC --> RPI, time off by: {:5.1f}[secs]".format(piU, time.time()-ts) )
					except: pass


			if tz != tzMAC or (abs(deltaT) > 100):
				# do not check time / time zone if disabled
					self.timeErrorCount[pi] +=1
					if self.timeErrorCount[pi]	 < 3:
						try:	  deltaT = "{}".format(deltaT)
						except:	  deltaT = "{:.0f} - {}".format(time.time, ts)
						self.indiLOG.log(10,"please do \"sudo raspi-config\" on rPi: {}, set time, reboot ...      send: TIME-Tsend= {}      /epoch seconds UTC/  timestamp send= {}; TZ send is={}".format(piU, deltaT, ts, tz) )

			if (abs(time.time()-float(ts)) < 2. and tz == tzMAC)  or self.timeErrorCount[pi] > 1000:
				self.timeErrorCount[pi] = 0

		except Exception as e:
			if "{}".format(e).find("timeout waiting") > -1:
				self.indiLOG.log(40,"communication to indigo is interrupted")
			self.exceptionHandler(40, e)
		return


####-------------------------------------------------------------------------####
	def printBLEreport(self, BLEreport):
		try:
			self.indiLOG.log(10,"BLEreport received:")
			for rep in BLEreport:
					self.indiLOG.log(10,"=======================================\n"+BLEreport[rep][0].strip("\n"))
					if len(BLEreport[rep][1]) < 5:
						self.indiLOG.log(10,"no errors")
					else:
						self.indiLOG.log(10,"errors:\n"+BLEreport[rep][1].strip("\n"))
		except Exception as e:
			self.exceptionHandler(40, e)


####-------------------------------------------------------------------------####
	def printtrackMac(self, piU, report):
		name = ""
		try:
			out = "\ntrackMac report received  from RPI#:{}\n".format( piU)
			out += report.replace(";;", "\n")
			self.myLog(theText= out)
		except Exception as e:
			self.exceptionHandler(40, e)




####-------------------------------------------------------------------------####
	def printBLEAnalysis(self, piU, report):
		name = ""
		try:
			ServiceSections = [
			["01", "Flags"],
			["02", "16BServClinc"],
			["03", "16BServClcmplt"],
			["04", "32BServClinc"],
			["05", "32BServClcmplt"],
			["06", "128BServClinc"],
			["07", "128BServClcmplt"],
			["08", "ShortName"],
			["09", "Name"],
			["0A", "TxPowerLevel"],
			["10", "DeviceID"],
			["12", "SlaveConnectionIntervalRange"],
			["16", "ServiceData"],
			["19", "Appearance"],
			["1A", "AdvertisingInterval"],
			["1B", "DeviceAddress"],
			["20", "ServiceData-32B"],
			["21", "ServiceData-128B"],
			["FF", "UUID"],
			["", "iBeacon"],
			["", "TLM"],
			["", "pos_of_MAC"],
			["", "pos_of_r-MAC"]]
			out = "\n\nBLEAnalysis received for beacons with signal (rssi) > {}; from RPI#:{}".format(report["rssiCutoff"], piU)
			#self.indiLOG.log(10,"BLEAnalysis :{}".format(report))
			for existing in ["new_Beacons", "existing_Beacons", "rejected_Beacons"]:
				out+= "\n===================== {:16s} ==================== ".format(existing)
				if existing in ["new_Beacons", "existing_Beacons"]:
					out +=   "   char pos       01  23 45 67 89 A1 23 45 67 89 B1 01 23 45 67 89 C1 23 45 67 89 D1 23 45 67 89 E1 23 45 67 89 F1"
				rr = report[existing]
				for mac in rr:
					name = ""
					if mac in self.beacons and self.beacons[mac]["indigoId"] >0:
						try:	name = "-"+indigo.devices[int(self.beacons[mac]["indigoId"])].name
						except:	pass

					if existing == "rejected_Beacons":
						out += "\n===MAC# "+mac+"  "+name+" == {}\n".format(rr[mac])

					else:
						out += "\n===MAC# "+mac+"  "+name+"\n"
						for item in [ "raw_data", "n_of_MSG_Types", "MSG_in_10Secs", "max_rssi", "max_TX"]: #, "mfg_info", "iBeacon", "pos_of_reverse_MAC_in_UUID", "pos_of_MAC_in_UUID"]: #, "typeOfBeacon", "possible_knownTag_options"]:
							if item not in rr[mac]:
								out += "missing: "+item+"\n"
								continue


							if item == "raw_data":
								out +=   "tag ----------        msg-Type : raw data: preamble->   [-- mac # ------] dat ll   1  2  3  4  5  6  7  8  9 10 11 12 13 14 15 16 17 18 19 20 21 22 23 24 25 26 27 28 29 30 31 .. RSSI\n"
								for ii in range(len(rr[mac]["raw_data"])):
									rawData  = rr[mac]["raw_data"][ii][:20] + "  " + rr[mac]["raw_data"][ii][20:38] +  "    " + rr[mac]["raw_data"][ii][38:42] + " " +rr[mac]["raw_data"][ii][42:-2]
									rawData += (" ").ljust( max(3, 35*3 -1 - len(rawData[38:-3])) )
									rssi = rr[mac]["raw_data"][ii][-2:]
									rssiInt = int(rssi,16)
									if rssiInt > 127: rssiInt -= 256
									out+= "{:24s}Nmsg:{:2d}: {}{}={}\n".format(rr[mac]["typeOfBeacon"][ii], rr[mac]["nMessages"][ii],  rawData, rssi, rssiInt)

									for ss in ServiceSections:
										try:
											if ss[1] not in rr[mac]: continue

											if len(ss[0]) >0:	pp = ss[1]+"-"+ss[0]
											else: 				pp = ss[1]

											if ss[1].find("pos_of_") == 0:
												mPos = rr[mac][ss[1]][ii]/2
												if mPos > 0: out += "{:>30} : {:}\n".format(pp, mPos)

											elif rr[mac][ss[1]][ii] != "":
												out += "{:>30} : {:}\n".format(pp, rr[mac][ss[1]][ii])

										except Exception as e:
											self.indiLOG.log(10,"ServiceSections mac:{} serv{} data:{}".format(mac, ss, rr[mac][ss[1]]))


							elif item == "possible_knownTag_options":
								out += "possible knownTag options:\n"
								for ii in rr[mac][item]:
									out+= "-- {}\n".format(ii)

							else:
								out += "{:31s}: {}\n".format(item, rr[mac][item])
			self.myLog(theText= out)
		except Exception as e:
			self.exceptionHandler(40, e)
			self.myLog(theText= out)
			indigo.server.log("printBLEAnalysis :{}".format(report))
		return

####-------------------------------------------------------------------------####
	def checkI2c(self, piU, i2c):
		try:
			for i2cChannel in i2c:
				if i2cChannel is not None:
					if i2cChannel.find("i2c.ERROR:.no.such.file....redo..SSD?") > -1 :
						self.indiLOG.log(10," pi#{}  has bad i2c config. you might need to replace SSD".format(piU))
		except:
			pass


####-------------------------------------------------------------------------####
	def checkBlueTooth(self, piU, blueTooth):
		try:
			if blueTooth is not None:
				if blueTooth.find("startup.ERROR:...SSD.damaged?") > -1 :
					self.indiLOG.log(30," pi#{} bluetooth did not startup. you might need to replace SSD".format(piU))
		except:
			pass

####-------------------------------------------------------------------------####
	def upDateHCIinfo(self, piU, varJson, varUnicode):
		# {"pi":"11","program":"beaconloop","data":{"hciInfo":"hci0-USB-5C:F3:70:6D:DA:75"},"ipAddress":"192.168.1.204"}
		try:

			if "ERROR" in varJson:
				devId = int(self.RPI[piU]["piDevId"])
				dev = indigo.devices[devId]
				if "hciInfo" in dev.states:
					if dev.states["hciInfo"] != "error":
						dev.updateStateOnServer("hciInfo", "error")
						self.indiLOG.log(40," pi#{} bluetooth did not startup, wrong parameters? error msg:\n{}".format(piU, varJson["ERROR"]))
				return 

			if "hciInfo" not in varUnicode: return 
			if "program" not in varUnicode: return 
			if "pi" 	 not in varUnicode: return 

			#self.indiLOG.log(20,"pi:{}; hciinfo: {}".format(piU, varJson))
			program =varJson["program"]

			devId = int(self.RPI[piU]["piDevId"])
			dev = indigo.devices[devId]

			#{"data":{"hciInfo":"hci0-UP-USB-5C:F3:70:6B:BE:A8,hci1-UP-UART-B8:27:EB:D9:11:18",
			#  "hciInfo_beacon":"hci0-USB-5C:F3:70:6B:BE:A8"},"program":"beaconloop","pi":"7","ipAddress":"192.168.1.27"}

			if "hciInfo_BLEconnect" in dev.states and "hciInfo_BLEconnect" in varJson["data"]:
				if dev.states["hciInfo_BLEconnect"] != varJson["data"]["hciInfo_BLEconnect"]:
					dev.updateStateOnServer("hciInfo_BLEconnect", varJson["data"]["hciInfo_BLEconnect"])
	
			if "hciInfo_beacons" in dev.states and "hciInfo_beacons" in varJson["data"]:
				if dev.states["hciInfo_beacons"] != varJson["data"]["hciInfo_beacons"]:
					dev.updateStateOnServer("hciInfo_beacons", varJson["data"]["hciInfo_beacons"])
	
			if "hciInfo_beep" in dev.states and "hciInfo_beep" in varJson["data"]:
				if dev.states["hciInfo_beacons"] != varJson["data"]["hciInfo_beep"]:
					dev.updateStateOnServer("hciInfo_beep", varJson["data"]["hciInfo_beep"])

			if "hciInfo" in dev.states and "hciInfo" in varJson["data"]: 
				dev.updateStateOnServer("hciInfo",  varJson["data"]["hciInfo"])



		except Exception as e:
			self.exceptionHandler(40, e)
		return 

####-------------------------------------------------------------------------####
	def updateRPIAlive(self, varJson,varUnicode,  timeStampOfReceive):
		if "pi" not in varJson : return
		try:
			if self.decideMyLog("DevMgmt"):	 self.indiLOG.log(10,"rPi alive message :  {}".format(varUnicode))
			if (varUnicode).find("_dump_") >-1:
				self.indiLOG.log(40,"rPi error message: Please check that RPI  you might need to replace SD")
				self.indiLOG.log(40,varUnicode)
				return
			if (varUnicode).find("data may be corrupt") >-1:
				self.indiLOG.log(30,"rPi error message: >>dosfsck has error: data may be corrupt<<<   Please check that RPI  you might need to replace SD")
				self.indiLOG.log(30,varUnicode)
				return
			pi = int(varJson["pi"])
			piU = "{}".format(pi)
			if piU not in _rpiList:
				self.indiLOG.log(10,"pi# out of range:  {}".format(varUnicode))
				return

			if self.trackRPImessages  == pi:
				self.indiLOG.log(10,"pi# {} msg tracking:  {}".format(piU,varUnicode))

			self.RPI[piU]["lastMessage"] = time.time()

			if "reboot" in varJson:
				self.setRPIonline(piU,new="reboot")
				indigo.variable.updateValue(self.ibeaconNameDefault+"Rebooting", "reset from :{} at {}".format(piU, datetime.datetime.now().strftime(_defaultDateStampFormat)))
				if "text" in varJson and varJson["text"].find("bluetooth_startup.ERROR:") >-1:
					self.indiLOG.log(20,"RPI# {}; Please check that RPI {} ".format(piU, varJson["text"]))
				else:
					self.indiLOG.log(20,"RPI# {}; rebooting, reason: {} ".format(piU, varJson["text"]))

				return

			try:
				dev = indigo.devices[self.RPI[piU]["piDevId"]]
			except Exception as e:

				if "{}".format(e).find("timeout waiting") > -1:
					self.exceptionHandler(40, e)
					self.indiLOG.log(40,"communication to indigo is interrupted")
					return
				if "{}".format(e).find("not found in database") ==-1:
					self.exceptionHandler(40, e)
					return
				self.RPI[piU]["piDevId"]=0
				return
			self.compareRpiTime(varJson,piU,dev, timeStampOfReceive)
			self.setRPIonline(piU)


			self.updateStateIf(piU, dev, varJson, "sensors_active")
			self.updateStateIf(piU, dev, varJson, "i2c_active")
			self.updateStateIf(piU, dev, varJson, "rpi_type")
			self.updateStateIf(piU, dev, varJson, "fan_OnTime_Percent", decimalPlaces=0)
			self.updateStateIf(piU, dev, varJson, "op_sys")
			self.updateStateIf(piU, dev, varJson, "last_boot")
			self.updateStateIf(piU, dev, varJson, "last_masterStart")
			self.updateStateIf(piU, dev, varJson, "RPI_throttled")
			self.updateStateIf(piU, dev, varJson, "temp", deviceStateName="Temperature")

			if "i2cError" in varJson:
				self.indiLOG.log(30,"RPi# {} has i2c error, not found in i2cdetect {}".format(piU,varJson["i2cError"]) )

			dev.updateStateImageOnServer(indigo.kStateImageSel.SensorOn)
			if dev.states["status"] != "up" :
				self.addToStatesUpdateDict(dev.id, "status", "up")
				self.statusChanged = 8

			if dev.states["online"] != "up":
				self.addToStatesUpdateDict(dev.id, "online", "up")

			if pi < _GlobalConst_numberOfiBeaconRPI:
				if self.RPI[piU]["piMAC"] in self.beacons:
					self.beacons[self.RPI[piU]["piMAC"]]["lastUp"] = time.time()

			self.executeUpdateStatesDict(onlyDevID=dev.id, calledFrom="addToDataQueue pi_IN_Alive")

		except Exception as e:
			if "{}".format(e).find("timeout waiting") > -1:
				self.exceptionHandler(40, e)
				self.indiLOG.log(40,"communication to indigo is interrupted")
				return
			self.exceptionHandler(40, e)
			self.indiLOG.log(40,"variable pi_IN_Alive wrong format: {} you need to push new upgrade to rPi".format(varUnicode))

		return


####-------------------------------------------------------------------------####
	def updateStateIf(self, piU, dev, varJson, stateName, deviceStateName="", makeString=False, decimalPlaces=1 ):

		try:
			if deviceStateName == "": deviceStateName = stateName
			if deviceStateName not in dev.states: return ""
			if stateName in varJson:
				###self.indiLOG.log(10,"updateStateIf : "+statename+"  {}".format(varJson[statename]))
				if deviceStateName == "Temperature":
					x, UI, decimalPlaces, useFormat = self.convTemp(varJson[stateName])
					if x > 500. or x < -500.:
						x = "bad data"
						UI = "bad data"
						decimalPlaces = ""

				elif makeString:
					x  = varJson[stateName].strip("{").strip("}")
					UI = x
					decimalPlaces = 0
				else:
					x, UI, decimalPlaces  =  varJson[stateName], varJson[stateName], decimalPlaces

				if deviceStateName == "RPI_throttled":
					decimalPlaces=""
					old = dev.states[deviceStateName]
					if old != x:
						if x != "none" and x != "" and x != "no_problem_detected":
							self.indiLOG.log(30,"RPi# {} has power state has problem   new:>>{}<<, previous:{}".format(piU, x, old) )
						if x == "none" or x == "no_problem_detected":
							self.indiLOG.log(30,"RPi# {} has power state has recovered  new:>>{}<<, previous:{}".format(piU, x, old) )

				self.setStatusCol( dev, deviceStateName, x, UI, "", "", "", decimalPlaces=decimalPlaces)
				return x
		except Exception as e:
			self.exceptionHandler(40, e)
		return ""

####-------------------------------------------------------------------------####
	def setRPIonline(self, piU, new="up", setLastMessage=False):
		try:
			try:	devID = int(self.RPI[piU]["piDevId"])
			except: devID = 0
			if devID ==0: return  # not setup yet
			#self.indiLOG.log(10," into setting online status of pi:{}, setLastMessage:{}".format(piU, setLastMessage) )

			now = datetime.datetime.now().strftime(_defaultDateStampFormat)
			try: dev = indigo.devices[self.RPI[piU]["piDevId"]]
			except:
				self.sleep(1)
				try: dev = indigo.devices[self.RPI[piU]["piDevId"]]
				except:
					self.indiLOG.log(10,"setRPIonline looks like device has been deleted..  setting pi:{}  indigo.devices[{}] returns error   marking for delete".format(devID,piU) )
					self.delRPI(pi=piU, calledFrom="setRPIonline")
					return

			if setLastMessage:
				self.addToStatesUpdateDict(dev.id, "lastMessageFromRpi", datetime.datetime.now().strftime(_defaultDateStampFormat))


			if new == "up":
				#self.addToStatesUpdateDict(dev.id, "lastMessage", now)
				dev.updateStateImageOnServer(indigo.kStateImageSel.SensorOn)
				if "status" in dev.states and dev.states["status"] != "up":
					self.addToStatesUpdateDict("{}".format(devID), "status", "up")
					self.statusChanged = 9
				if "online" in dev.states and dev.states["online"] != "up":
					self.addToStatesUpdateDict(dev.id, "online", "up")
				return
			if new == "reboot":
				#self.addToStatesUpdateDict(dev.id, "lastMessage", now)
				if dev.states["online"] != "reboot":
					dev.updateStateImageOnServer(indigo.kStateImageSel.SensorOff)
					self.addToStatesUpdateDict(dev.id, "online", "reboot")
					self.setCurrentlyBooting(self.bootWaitTime, setBy="setting status of pi# {}   to reboot  or until new message arrives".format(piU))
					if piU not in _rpiBeaconList:
						self.addToStatesUpdateDict(dev.id, "status", "reboot")
					return
			if new == "offline":
				if dev.states["online"] != "down":
					#dev.updateStateImageOnServer(indigo.kStateImageSel.SensorOff)
					self.addToStatesUpdateDict(dev.id, "online", "down")
					if piU in _rpiSensorList:
						if "status" in dev.states and dev.states["status"] != "down":
							self.addToStatesUpdateDict(dev.id, "status", "down")
							self.statusChanged = 10
					return



		except Exception as e:
			if "{}".format(e).find("timeout waiting") > -1:
				self.exceptionHandler(40, e)
				self.indiLOG.log(40,"communication to indigo is interrupted")
				return
			self.exceptionHandler(40, e)
			self.indiLOG.log(40," pi{}  RPI{}".format(piU, self.RPI[piU]) )
		return
####-------------------------------------------------------------------------####
	def checkSensorPiSetup(self, piSend, data, piNReceived):

		try:
			#self.indiLOG.log(10,	"called checkSensorPiSetup")
			if piSend != piNReceived:
				self.indiLOG.log(10,"sensor pi {} wrong pi# {} number please fix in setup rPi".format(piSend, piNReceived))
				return -1
			if "ipAddress" in data:
				if self.RPI[piSend]["ipNumberPi"] != data["ipAddress"]:
					self.indiLOG.log(10,"sensor pi {} wrong IP number please fix in setup rPi, received: -->{}<-- if it is empty a rPi reboot might solve it".format(piSend, data["ipAddress"]))
					return -1
			devId = self.RPI[piSend]["piDevId"]
			Found= False
			try:
				dev= indigo.devices[devId]
				Found =True
			except Exception as e:

				self.exceptionHandler(40, e)
				if "{}".format(e).find("timeout waiting") > -1:
					self.indiLOG.log(40,"communication to indigo is interrupted")
					return -1

			if not Found:
				self.indiLOG.log(10,"sensor pi {}- devId: {} not found, please configure the rPi:  {}".format(piSend, devId, self.RPI[piSend]))
			if Found:
				if dev.states["status"] != "up":
						self.addToStatesUpdateDict(dev.id, "status", "up")
						dev.updateStateImageOnServer(indigo.kStateImageSel.SensorOn)
				if dev.states["online"] != "up":
						self.addToStatesUpdateDict(dev.id, "online", "up")
						dev.updateStateImageOnServer(indigo.kStateImageSel.SensorOn)

		except Exception as e:
			self.exceptionHandler(40, e)
			self.indiLOG.log(40, "{}".format(data))
		return 0



####-------------------------------------------------------------------------####
	## as we accumulate changes , dev.states does not contain the latest. check update list and if not there then check dev.states
	def getCurrentState(self, dev, devIds, state, fromMETHOD=""):
		try:
			if devIds in self.updateStatesDict and state in self.updateStatesDict[devIds]:
				return self.updateStatesDict[devIds][state]["value"]
			else:
				return dev.states[state]

		except Exception as e1:
			try:  # rare case that updateStatesDict has been updated and clear whil we do this, then take new dev.state happens ~ 1/week with MANY devices
				#self.indiLOG.log(5,"in Line {} has error(s) ={}, getCurrentState not in dyn list, trying to use indigo state... " .format(sys.exc_info()[2].tb_lineno, e1))
				ret =  indigo.devices[dev.id].states[state]
				#self.indiLOG.log(5,"...  was fixed using indigo states")
				return ret
			except Exception as e:
				self.exceptionHandler(40, e)
				self.indiLOG.log(40,"  .. called from= {};  state= {};  updateStatesDict= {}".format(fromMETHOD, state, self.updateStatesDict) )
				try:	self.indiLOG.log(40,"  .. dev= {}".format(dev.name) )
				except: self.indiLOG.log(40,"  .. device does not exist, just deleted? .. IndigoId={}".format(devIds) )
				return ""


####-------------------------------------------------------------------------####
	def getTimetimeFromDateString(self, dateString, fmrt=_defaultDateStampFormat):
		if len(dateString) > 9:
			try:
				return  time.mktime(  datetime.datetime.strptime(dateString, fmrt).timetuple()  )
			except:
				return 0
		else:
			return 0

####-------------------------------------------------------------------------####
	def calcPostion(self, dev, expirationTime, rssi=""): ## add Signal time dist status
		try:
			devID			= dev.id
			name			= dev.name
			devIds			= "{}".format(dev.id)
			deltaDistance	= 0.
			status			= "expired"
			distanceToRpi	 = []
			pitimeNearest	= "1900-00-00 00:00:00"
			lastUp			= 0
			lastUpS			= ""
			update			= False
			#if devID ==78067927: self.indiLOG.log(5,"dist  "+ dev.name)
			lastStatusChangeDT = 99999
			try:
				if "lastUp" in dev.states:
					lastUp =  float(self.getTimetimeFromDateString(self.getCurrentState(dev,devIds,"lastUp", fromMETHOD="calcPostion1")))

			except Exception as e:
				self.exceptionHandler(40, e)
				lastUp	= 0

			if dev.deviceTypeId == "BLEconnect":
				activePis = self.getActiveBLERPI(dev)
				lastBusy = 0
			else:
				activePis = range(_GlobalConst_numberOfiBeaconRPI)
				try: 	lastBusy = self.beacons[dev.address]["lastBusy"]
				except:	lastBusy = 0

			# do not calculate new position if beacon is busy eg beep, get battery
			if time.time() - lastBusy < 0: return False, 0

			for pi1 in activePis:
				pi1U = "{}".format(pi1)
				piXX = "Pi_{:02d}".format(pi1)
				if piXX+"_Signal" not in dev.states: 
					continue

				signal = self.getCurrentState(dev,devIds,piXX+"_Signal", fromMETHOD="calcPostion2")
				if signal == "": continue
				txPower = self.getCurrentState(dev,devIds,"TxPowerReceived")
				if txPower == "": txPower =-30

				piTimeS = self.getCurrentState(dev,devIds,piXX+"_Time", fromMETHOD="calcPostion3")
				if piTimeS is not None and len(piTimeS) < 5: continue

				if piTimeS > pitimeNearest:
					pitimeNearest = piTimeS

				piT2 = self.getTimetimeFromDateString(piTimeS)
				if piT2 < 10: piT2 = time.time()
				try:
					dist = self.getCurrentState(dev,devIds,piXX+"_Distance", fromMETHOD="calcPostion4")
					dist = float(dist)
				except Exception as e:
					self.indiLOG.log(40,"Line {} has error={}".format(sys.exc_info()[2].tb_lineno, e) )
					dist = 99999.

				piTimeUse = piT2
				if dist == 9999. and  lastUp != 0:
					piTimeUse = float(lastUp)

				if signal == -999:
					if	 (time.time()- piTimeUse < expirationTime):
						status =  "up"
						#if dev.name.find("BLE-") >-1:	self.indiLOG.log(5,"setting status up  calcPostion sig  = -999  "  )
					elif (time.time()- piTimeUse < expirationTime)	and status != "up":
						status = "down"
						#if dev.name.find("BLE-") >-1:	self.indiLOG.log(5,"setting status up  calcPostion sig  = -999  "  )
				else:
					if dist >= 99990. and txPower < -20:							 continue
					if dist == "" or (dist >= 99990. and signal > -50):				 continue # fake signals with bad TXpower
					if dist > 50./max(self.distanceUnits, 0.3) and signal > -50:	 continue # fake signals with bad TXpower
					if time.time()- piTimeUse  < expirationTime:
						status = "up"
					elif (time.time()- piTimeUse < expirationTime)	and status != "up":
						status = "down"

					if time.time()- piTimeUse  < max(90.,expirationTime):								   # last signal not in expiration range anymore , use at least 90 secs.. for cars exp is 15 secs and it forgets the last signals too quickly
						distanceToRpi.append([dist , pi1])

			if rssi !=-999: # dont set status for fast down messages, is done before
				currStatus =  self.getCurrentState(dev,devIds,"status", fromMETHOD="calcPostion5")
				if currStatus != status :
					if "lastStatusChange" in dev.states:
						try: lastStatusChangeDT  =  time.time() - self.getTimetimeFromDateString(dev.states["lastStatusChange"])
						except Exception as e:
								if "{}".format(e) != "None":
									self.exceptionHandler(40, e)
					if lastStatusChangeDT > 3.:
						update = True
						self.addToStatesUpdateDict(dev.id, "status", status)
						if	("note" in dev.states and dev.states["note"].find("beacon") >-1) or dev.deviceTypeId =="BLEconnect":
							if status =="up":
								dev.updateStateImageOnServer(indigo.kStateImageSel.SensorOn)
							elif status =="down":
								dev.updateStateImageOnServer(indigo.kStateImageSel.SensorOff)
							elif status =="expired":
								dev.updateStateImageOnServer(indigo.kStateImageSel.SensorOff)
					self.statusChanged = 11

			distanceToRpi = sorted(distanceToRpi)
			PijjPosition	= []

			if len(distanceToRpi) > 0:
				closestPi				= distanceToRpi[0][1]
				distanceToClosestRpi	= distanceToRpi[0][0]
				closestRpiPos			= self.piPosition[closestPi] # set to closest RPI position
				newPos					= [closestRpiPos[0],closestRpiPos[1],closestRpiPos[2]]					   # set to closest RPI position

				# calculate the direction vector
				Npoints=0
				if len(distanceToRpi) > 1:
					piJJ = distanceToRpi[1][1] # 2. pi#
					#    same RPI			  not set should not be 0 c         position of RPi are not set or all the same
					if piJJ != closestPi and self.piPosition[piJJ][0] >0 and  self.piToPiDistance[piJJ][closestPi][3] !=0:
						## restrict dist to maximum  half distance to next RPI
						dist =	min(distanceToClosestRpi, self.piToPiDistance[piJJ][closestPi][3]/2.)
						# x, y position away from pi closest   x y / length
						newPos[0] += dist * (self.piToPiDistance[piJJ][closestPi][0])/max(0.2,self.piToPiDistance[piJJ][closestPi][3])
						newPos[1] += dist * (self.piToPiDistance[piJJ][closestPi][1])/max(0.2,self.piToPiDistance[piJJ][closestPi][3])

				pos =["PosX", "PosY", "PosZ"]
				for ii in range(3):
					dd = abs(float(dev.states[pos[ii]]) - newPos[ii])
					if dd > 1./self.distanceUnits:	 # min delta = 1 meter
						self.addToStatesUpdateDict(devIds,pos[ii], newPos[ii],decimalPlaces=1)
						deltaDistance +=dd

		except Exception as e:
			self.exceptionHandler(40, e)
		return update, deltaDistance



####-------------------------------------------------------------------------####
	def BLEconnectupdateAll(self, piU, sensors):
		pi = int(piU)
		for sensor in sensors:
			if sensor == "BLEconnect":
				if self.decideMyLog("BLE"): self.indiLOG.log(10,"BLEconnectupdateAll pi:{};  sensor data:{},".format(piU,  sensors[sensor]))
				self.messagesQueueBLE.put((piU, sensors[sensor]))

		if not self.queueActiveBLE:
				self.workOnQueueBLE()

####-------------------------------------------------------------------------####
	def workOnQueueBLE(self):

		self.queueActiveBLE	 = True
		while not self.messagesQueueBLE.empty():
			item = self.messagesQueueBLE.get()
			for ii in range(40):
				if self.queueListBLE == "update" : break
				if self.queueListBLE == ""		 : break
				if ii > 0:	pass
				time.sleep(0.05)
			self.BLEconnectupdate("{}".format(item[0]),item[1])
			self.queueListBLE = "update"

		self.messagesQueueBLE.task_done()
		self.queueActiveBLE	 = False
		self.queueListBLE = ""
		return


####-------------------------------------------------------------------------####
	def BLEconnectupdate(self, piU, info):
		updateBLE = False
		piI = int(piU)
		if self.decideMyLog("BLE"): self.indiLOG.log(10,"BLEconnectupdate pi:{};  info:{} ".format(piU, info))
		try:
			for devId in info:
				try:
					dev = indigo.devices[int(devId)]
				except Exception as e:

					if "{}".format(e).find("timeout waiting") > -1:
						self.exceptionHandler(40, e)
						self.indiLOG.log(40,"BLEconnectupdate communication to indigo is interrupted")
						return
					self.indiLOG.log(10,"BLEconnectupdate devId not defined in devices pi:{}; devId={}; info:{}".format( piU, devId, info))
					continue
				if not dev.enabled: continue
				props = dev.pluginProps
				data = {}
				for mac in info[devId]:
					if mac.upper() != props["macAddress"].upper() : continue
					data= info[devId][mac]
					break
				if data == {}:
					self.indiLOG.log(10,"data empty for info[devid][mac];  pi:{}; devId={}; info:{} ".format( piU, devId, info) )
					continue

				if "rssi" not in data:
					self.indiLOG.log(5,"BLEconnectupdate ignoring msg; rssi missing; PI= {}; mac:{};  data:{}".format(piU, mac, data))
					return updateBLE
				rssi	  = int(data["rssi"])
				txPowerR  = int(data["txPower"])
				if self.decideMyLog("BLE"): self.indiLOG.log(5,"BLEconnectupdate PI= {}; mac:{}  rssi:{}  txPowerR:{} TxPowerSet:{}".format(piU, mac, rssi, txPowerR, props["beaconTxPower"]))

				txSet = 999
				try: txSet = int(props["beaconTxPower"])
				except: pass
				if txSet != 999:
					txPower = int(txSet)
				else:
					txPower = txPowerR

				expirationTime = int(props["expirationTime"])

				if dev.states["created"] == "":
					self.addToStatesUpdateDict(dev.id, "created", datetime.datetime.now().strftime(_defaultDateStampFormat))

				piXX = "Pi_{:02d}".format(piI)
				if piXX+"_Signal" not in dev.states: continue

				if rssi > -160 and "{}".format(dev.states[piXX+"_Signal"]) != "{}".format(rssi):
					self.addToStatesUpdateDict(dev.id, piXX+"_Signal",int(rssi) )
				if txPowerR !=-999 and	"{}".format(dev.states["TxPowerReceived"]) != "{}".format(txPowerR):
					self.addToStatesUpdateDict(dev.id, "TxPowerReceived",txPowerR  )

				if rssi < -160: upD = "down"
				else:			upD = "up"

				if upD == "up":
					dist = round( self.calcDist(txPower,  rssi) / self.distanceUnits, 1)
					if self.decideMyLog("BLE"): self.indiLOG.log(5,"rssi txP dist dist-Corrected.. rssi:{} txPower:{}  dist:{}  rssiCaped:{}".format(rssi, txPower, dist, min(txPower,rssi)))
					self.addToStatesUpdateDict(dev.id,piXX+"_Time",	datetime.datetime.now().strftime(_defaultDateStampFormat)  )
					self.addToStatesUpdateDict(dev.id, "lastUp",datetime.datetime.now().strftime(_defaultDateStampFormat))
					if abs(dev.states[piXX+"_Distance"] - dist) > 0.5 and abs(dev.states[piXX+"_Distance"] - dist)/max(0.5,dist) > 0.05:
						self.addToStatesUpdateDict(dev.id,piXX+"_Distance", dist,decimalPlaces=1)
					self.lastBLEconnectSeen[int(devId)] = time.time()
				else:
					dist = 99999.
					if dev.states["status"] == "up":
						if self.decideMyLog("BLE"): self.indiLOG.log(5,"NOT UPDATING::::  updating time  status was up, is down now dist = 99999 for MAC: {}".format(mac) )
						#self.addToStatesUpdateDict(dev.id, "Pi_{:02d}_Time".format(piU),	datetime.datetime.now().strftime(_defaultDateStampFormat))
				#self.executeUpdateStatesDict()
				update, deltaDistance = self.calcPostion(dev, expirationTime)
				updateBLE = update or updateBLE

				if rssi > -160:
					newClosestRPI = self.findClosestRPIForBLEConnect(dev, piU, dist)
					if newClosestRPI != dev.states["closestRPI"]:
						#indigo.server.log(dev.name+", newClosestRPI: {}".format(newClosestRPI))
						if newClosestRPI == -1:
							self.addToStatesUpdateDict(dev.id, "closestRPI", -1)
							if self.setClostestRPItextToBlank: self.addToStatesUpdateDict(dev.id, "closestRPIText", "")
						else:
							#indigo.server.log(dev.name+", uodateing  newClosestRPI: {}".format(newClosestRPI)+ " getRPIdevName:  "+self.getRPIdevName(newClosestRPI) )
							if "{}".format(dev.states["closestRPI"]) !="-1":
								self.addToStatesUpdateDict(dev.id, "closestRPILast", dev.states["closestRPI"])
								self.addToStatesUpdateDict(dev.id, "closestRPITextLast", dev.states["closestRPIText"])
							self.addToStatesUpdateDict(dev.id, "closestRPI", newClosestRPI)
							self.addToStatesUpdateDict(dev.id, "closestRPIText", self.getRPIdevName((newClosestRPI)))

				if dev.states["lastUpdateFromRPI"] != piU: 
					self.addToStatesUpdateDict(dev.id, "lastUpdateFromRPI", piU)

				self.executeUpdateStatesDict(onlyDevID=dev.id, calledFrom="BLEconnectupdate end")


		except Exception as e:
			self.exceptionHandler(40, e)
			if "{}".format(e).find("timeout waiting") > -1:
				self.indiLOG.log(40,"communication to indigo is interrupted")

		return 


####-------------------------------------------------------------------------####
	def updateOutput(self, piU, outputs):
		data = ""
		dateString = datetime.datetime.now().strftime(_defaultDateStampFormat)
		try:
			if self.decideMyLog("OutputDevice"):self.indiLOG.log(20,"updateOutput from pi:{}; outputs:{}".format(piU, outputs) )
							#  updateOutput from pi:11; outputs:{'OUTPUTswitchbotRelay': {'1631600841': {'actualStatus': 'on'}}}

			for output in outputs:
				if output.find("neopixel") == -1 and output.find("OUTPUTgpio") == -1 and output.find("OUTPUTi2cRelay") == -1 and output.find("OUTPUTswitchbotRelay") == -1 and output.find("OUTPUTswitchbotCurtain") == -1: continue

				devUpdate = {}
				for devIds in outputs[output]:
					devUpdate[devIds] = True
					try:
						try:	devId = int(devIds)
						except: devId = 0
						if devId == 0: continue
						dev = indigo.devices[devId]
						props = dev.pluginProps
						#self.indiLOG.log(40,"piu:{};  dev:{};  props:{}".format(piU, dev.name, props))
					except Exception as e:

						if "{}".format(e).find("timeout waiting") > -1:
							self.exceptionHandler(40, e)
							self.indiLOG.log(40,"communication to indigo is interrupted")
							return
						if "{}".format(e).find("not found in database") ==-1:
							self.exceptionHandler(40, e)
							return

						self.indiLOG.log(40,f"bad devId send from pi:{piU}; devId: {devIds}, deleted? " )
						continue

					if not dev.enabled:
						self.indiLOG.log(10,f"dev not enabled send from pi:{piU} dev: {dev.name}" )
						continue

					data = outputs[output][devIds]
					uData = "{}".format(data)
					if "badSensor" in uData:
						self.addToStatesUpdateDict(dev.id, "status", "bad Output data, disconnected?")
						try: dev.updateStateImageOnServer(indigo.kStateImageSel.PowerOff)
						except: pass
						continue

					if self.decideMyLog("OutputDevice"): self.indiLOG.log(5,"{} received {}".format(output, uData) )
					if output == "neopixel":
						if "status" in data:
							dev.updateStateOnServer("status", data["status"])
					else:
						self.setActualRelayStatus(piU, dev, props, data)

				for devIds in devUpdate:
					if devIds in self.updateStatesDict:
						if self.decideMyLog("OutputDevice"): self.indiLOG.log(5,"pi# {}  {}  {}".format(piU, devIds, self.updateStatesDict) )
						self.executeUpdateStatesDict(onlyDevID=devIds, calledFrom="updateOutput end")

		except Exception as e:
			self.exceptionHandler(40, e)
			if "{}".format(e).find("timeout waiting") > -1:
				self.indiLOG.log(40,"updateOutput communication to indigo is interrupted")


####-------------------------------------------------------------------------####
	def setActualRelayStatus(self, piU, dev, props, data):
		try:

			# switchbot: {"outputs":{"OUTPUTswitchbotRelay":{"77309094":{"actualStatus":"on"}}},"program":"BLEconnect","ipAddress":"192.168.1.35","pi":"12","ts":{"tz":"CEST","time":1659629713.54}}

			if "actualGpioValue" in data and  "outType" in props: 

				upState = data["actualGpioValue"]
				actualStatus = upState.lower()
				if actualStatus not in ["on", "off"]:
					if props["outType"] == "0": # not inverse
						if actualStatus == "high":	upState = "on"
						else:						upState = "off"
					else:
						if actualStatus == "low":	upState = "on"
						else:						upState = "off"

				if self.decideMyLog("OutputDevice"): self.indiLOG.log(5,"RPi:{}, {} update from  {}; actualStatus:{}, upState:{}".format(piU, dev.name, data, actualStatus, upState) )
				self.addToStatesUpdateDict(dev.id, "actualStatus", actualStatus)
				self.addToStatesUpdateDict(dev.id, "onOffState", upState == "on")
				self.addToStatesUpdateDict(dev.id, "status", upState)

			connectionStatusUpdated = False
			for xx in [ "error", "warning", "batteryLevel", "version", "holdSeconds", "mode", "inverseDirection", "actualStatus", "position" ]:
				if xx in data:

					if xx == "error" and xx in data:
						self.indiLOG.log(30,"received status update from RPi:{}, for {}:  {}".format(piU, dev.name, data[xx]) )
						if "actualStatus" in dev.states:
							if "actualStatus" in data:
								dev.updateStateOnServer("actualStatus", data["actualStatus"])
							else:
								dev.updateStateOnServer("actualStatus", "connectionError")

						if dev.deviceTypeId in ["OUTPUTswitchbotCurtain","OUTPUTswitchbotCurtain3"]:
							self.addToStatesUpdateDict(dev.id, "status", "posCmd:{}".format(str(data[xx])[0:17]) )
						connectionStatusUpdated = True
						dev.updateStateImageOnServer(indigo.kStateImageSel.SensorTripped)
						break

					elif xx == "warning" and xx in data:
						if "actualStatus" in dev.states:
							self.indiLOG.log(30,"received status update from RPi:{} for {}:  {}".format(piU, dev.name, data[xx]) )
							if "actualStatus" in data:
								dev.updateStateOnServer("actualStatus", data["actualStatus"])
							else:
								dev.updateStateOnServer("actualStatus", data[xx])
							dev.updateStateImageOnServer(indigo.kStateImageSel.SensorTripped)
							connectionStatusUpdated = True
						continue

					elif xx == "actualStatus" and not connectionStatusUpdated  and data[xx] !="":
						connectionStatusUpdated = True
						if "mode" in data and  data["mode"] == "pressMode":
							onB = data[xx] == "on"
							onT = "on"  if onB else "off"
							self.addToStatesUpdateDict(dev.id, "onOffState", onB , uiValue=onT)
							if "actualStatus" in dev.states:
								self.addToStatesUpdateDict(dev.id, "actualStatus", onT)
							if onB: dev.updateStateImageOnServer(indigo.kStateImageSel.SensorOn)
							else:	dev.updateStateImageOnServer(indigo.kStateImageSel.SensorOff)
							if "holdSeconds" in data and data["holdSeconds"] != "":
								try:
									#self.indiLOG.log(20,"received status update from RPi for {} update  {}".format(dev.name, data) )
									secs = max(1.5,float(data["holdSeconds"]))
									onB = data[xx] != "on"
									onT = "SensorOn"  if onB else "SensorOff"
									if secs > 0:
										#self.indiLOG.log(20,"{} update delayed action".format(dev.name) )
										if "actualStatus" in dev.states:
											self.delayedActions["data"].put( 
												{	"actionTime":time.time()+secs, "devId":dev.id, 
													"updateItems":[
														{"stateName":"onOffState", "value": onB, "uiValue":onT, "image":onT}, 
														{"stateName":"actualStatus", "value": onT, "image":onT}
													]
												} 
											)
										else:
											self.delayedActions["data"].put( 
												{	"actionTime":time.time()+secs, "devId":dev.id, 
													"updateItems":[
														{"stateName":"onOffState", "value": onB, "uiValue":onT, "image":onT} 
													]
												} 
											)

								except Exception as e:
									self.exceptionHandler(40, e)
						else:
							onB = data[xx] == "on"
							onT = "on"  if onB else "off"
							self.addToStatesUpdateDict(dev.id, "onOffState", onB , uiValue=onT,image=onT)
							if "actualStatus" in dev.states:
								self.addToStatesUpdateDict(dev.id, "actualStatus", onT)

					elif xx == "batteryLevel" and "lastUpdateBatteryLevel" in dev.states:
						self.addToStatesUpdateDict(dev.id, "lastUpdateBatteryLevel", datetime.datetime.now().strftime(_defaultDateStampFormat))

					elif xx == "position" and "brightnessLevel" in dev.states: 
						#self.indiLOG.log(20,"sensor pi: {}-{}; dev.deviceTypeId:{};  data {}" .format(piU, dev.name, dev.deviceTypeId , data))
						if dev.deviceTypeId in ["OUTPUTswitchbotCurtain","OUTPUTswitchbotCurtain3"]:
							self.addToStatesUpdateDict(dev.id, "status", "posCmd=ok" )
						else:
							self.addToStatesUpdateDict(dev.id, "brightnessLevel", int(data["position"]) )


					elif xx != "actualStatus" and xx in dev.states : self.addToStatesUpdateDict(dev.id, xx, data[xx])


		except Exception as e:
			self.exceptionHandler(40, e)
			self.indiLOG.log(40, "{}".format(data))
		return



####-------------------------------------------------------------------------####
	def updateSensors(self, pi, sensors):
		data = ""
		dateString = datetime.datetime.now().strftime(_defaultDateStampFormat)
		piU = "{}".format(pi)
		try:
			if self.decideMyLog("SensorData"): self.indiLOG.log(5,"sensor input  pi: {}; data {}" .format(piU, sensors))
			# data["sensors"][sensor]["temp,hum,press,INPUT"]

			#if piU == "3" : self.indiLOG.log(20,"updateSensors    sensors: {}" .format( sensors))
			for sensor in sensors:
				if sensor == "i2cChannels":
					continue  # need to implement test for i2c channel active

				if sensor == "BLEconnect":
					continue

				if sensor == "setTEA5767":
					self.updateTEA5767(sensors[sensor],sensor)
					continue

				if sensor == "getBeaconParameters":
					self.updateGetBeaconParameters(piU,sensors[sensor])
					continue



				devUpdate = {}
				for devIds in sensors[sensor]:
					updateProps = False
					devUpdate[devIds] = True
					try:
						try:	devId = int(devIds)
						except: devId = 0
						if devId == 0: continue
						dev = indigo.devices[devId]
						props = dev.pluginProps
					except Exception as e:

						if "{}".format(e).find("timeout waiting") > -1:
							self.exceptionHandler(40, e)
							self.indiLOG.log(40,"communication to indigo is interrupted")
							return
						if "{}".format(e).find("not found in database") ==-1:
							self.exceptionHandler(40, e)
							return

						self.indiLOG.log(10,f"bad devId send from pi:{piU} devId: {devIds} deleted?")
						continue
					if devIds in self.trackSensorId:
						self.indiLOG.log(20,"logging: pi:{:2s}, dev:{}  data:{} ".format(piU, dev.id, sensors[sensor][devIds]) )
						

					if not dev.enabled:
						if self.decideMyLog("UpdateRPI"): self.indiLOG.log(5,"dev not enabled send from pi:{} dev: {}".format(dev.id, data) )
						continue

					self.alertGarageDoor(devId)
					self.saveSensorMessages(devId=devIds, item="lastMessage", value=time.time())


					#if devIds == "1013878981":self.indiLOG.log(20,"dev.id:{},  data:{}".format(dev.id, sensors[sensor][devIds]) )

					data = sensors[sensor][devIds]
					uData = "{}".format(data)
					if sensor=="mysensors":
						self.indiLOG.log(10,sensor+" received "+ uData)

					if "calibrating" in uData:
						self.addToStatesUpdateDict(dev.id, "status", "Sensor calibrating")
						try: dev.updateStateImageOnServer(indigo.kStateImageSel.SensorOff)
						except: pass

					if "badsensor" in uData.lower():
						self.addToStatesUpdateDict(dev.id, "status", "bad Sensor data, disconnected?")
						try: dev.updateStateImageOnServer(indigo.kStateImageSel.PowerOff)
						except: pass
						continue

					if "displayS" in props:
						whichKeysToDisplay = props["displayS"]
					else:
						whichKeysToDisplay = ""

					self.updateCommonStates(dev, props, data, whichKeysToDisplay, pi)


					if dev.deviceTypeId == "as726x":
						if "green" in data:
							data["illuminance"] = float(data["green"])*6.83
						self.updateRGB(dev, props, data, whichKeysToDisplay, dispType=4)

						if "LEDcurrent" in data:
							self.addToStatesUpdateDict(dev.id, "LEDcurrent", data["LEDcurrent"], decimalPlaces=1)

					if sensor == "i2cTCS34725" :
						self.updateRGB(dev, props, data, whichKeysToDisplay)
						continue

					self.updateLight(dev, props, data, whichKeysToDisplay)
					

					if sensor in ["vl503l0xDistance","vl503l1xDistance","vl6180xDistance","vcnl4010Distance","ultrasoundDistance"] :
						self.updateDistance(dev, data, whichKeysToDisplay)
						continue

					if sensor == "apds9960" :
						self.updateapds9960(dev, data)
						continue

					if sensor.find("INPUTgpio-") >-1:
						self.updateINPUT(dev, data, whichKeysToDisplay, int(sensor.split("INPUTgpio-")[1]), sensor)
						continue

					if sensor.find("INPUTtouch-") >-1:
						self.updateINPUT(dev, data, whichKeysToDisplay, int(sensor.split("INPUTtouch-")[1]), sensor)
						continue

					if sensor.find("INPUTtouch12-") >-1:
						self.updateINPUT(dev, data, whichKeysToDisplay, int(sensor.split("INPUTtouch12-")[1]), sensor)
						continue

					if sensor.find("INPUTtouch16-") >-1:
						self.updateINPUT(dev, data, whichKeysToDisplay, int(sensor.split("INPUTtouch16-")[1]), sensor)
						continue

					if sensor == "spiMCP3008" :
						self.updateINPUT(dev, data, whichKeysToDisplay,	 8, sensor)
						continue

					if sensor == "spiMCP3008-1" :
						self.updateINPUT(dev, data, "INPUT_0",	 1, sensor)
						continue

					if sensor == "PCF8591" :
						self.updateINPUT(dev, data, whichKeysToDisplay, 0, sensor)
						continue

					if sensor == "ADS1x15" :
						self.updateINPUT(dev, data, whichKeysToDisplay, 0, sensor)
						continue

					if sensor == "INPUTRotarySwitchAbsolute":
						self.updateINPUT(dev, data, whichKeysToDisplay, 1, sensor)
						continue

					if sensor == "INPUTRotarySwitchIncremental":
						self.updateINPUT(dev, data, whichKeysToDisplay, 1, sensor)
						continue

					if sensor == "mysensors" :
						self.indiLOG.log(10,sensor+"  into input")
						self.updateINPUT(dev, data, whichKeysToDisplay, 10, sensor)
						continue

					if sensor == "myprogram" :
						self.updateINPUT(dev, data, whichKeysToDisplay, 10, sensor)
						continue

					if dev.deviceTypeId == "Wire18B20":
						self.updateOneWire(dev,data,whichKeysToDisplay,piU)
						continue

					if dev.deviceTypeId == "BLEmyBLUEt":
						self.updateBLEmyBLUEt(dev,data,props,whichKeysToDisplay)
						continue

					if dev.deviceTypeId == "ina219":
						self.updateina219(dev,data,whichKeysToDisplay)
						continue

					if dev.deviceTypeId == "ina3221":
						self.updateina3221(dev,data,whichKeysToDisplay)
						continue

					if dev.deviceTypeId == "i2cADC121":
						self.updateADC121(dev,data,whichKeysToDisplay)
						continue

					if dev.deviceTypeId in ["l3g4200", "bno055", "mag3110", "hmc5883L", "mpu6050", "mpu9255", "lsm303"]:
						self.updateGYROS(dev,data,whichKeysToDisplay)
						continue

					if dev.deviceTypeId in ["INPUTpulse", "INPUTcoincidence"]:
						self.updatePULSE(dev,data,whichKeysToDisplay)
						continue


					if sensor == "rainSensorRG11":
						self.updaterainSensorRG11(dev,data,whichKeysToDisplay)
						continue


					if sensor == "pmairquality":
						self.updatePMAIRQUALITY(dev, props, data, whichKeysToDisplay)
						continue

					if sensor == "launchpgm":
						st = data["status"]
						self.addToStatesUpdateDict(dev.id, "status", st)
						if st == "running":
							dev.updateStateImageOnServer(indigo.kStateImageSel.SensorOn)
						elif st == "not running":
							dev.updateStateImageOnServer(indigo.kStateImageSel.SensorOff)
						elif st == "not checked":
							dev.updateStateImageOnServer(indigo.kStateImageSel.SensorTripped)
						continue

					try: 	newStatus = dev.states["status"]
					except: newStatus = ""


					if sensor in["mhzCO2"]:
						try:
							if abs( float(dev.states["CO2offset"]) - float(data["CO2offset"])	) > 1:
								self.setONErPiV(piU, "piUpToDate", ["updateParamsFTP"])
							self.addToStatesUpdateDict(dev.id, "CO2calibration", data["calibration"])
							self.addToStatesUpdateDict(dev.id, "raw", float(data["raw"]),	decimalPlaces = 1)
							self.addToStatesUpdateDict(dev.id, "CO2offset", float(data["CO2offset"]),	decimalPlaces = 1)
						except Exception as e:
							self.exceptionHandler(40, e)
							self.indiLOG.log(40,"props:{}\nstates:{}\n:data:{}".format("{}".format(props), dev.states, data) )

					if "VOC" in data:
						x, UI  = int(float(data["VOC"])), "VOC {:.0f}[ppb]".format(float(data["VOC"]))
						newStatus = self.setStatusCol( dev, "VOC", x, UI, whichKeysToDisplay, indigo.kStateImageSel.TemperatureSensorOn,newStatus, decimalPlaces = 1)
						

					if sensor in ["sgp40"]:
						try:
							x = int(float(data["VOC"]))
							UI = "VOC index {:.0f}".format(float(data["VOC"]))
							if   x < 101: UI += " very good"
							elif x < 201: UI += " good"
							elif x < 301: UI += " ok"
							elif x < 401: UI += " bad"
							else:         UI += " very bad"
							newStatus = self.setStatusCol( dev, "VOC", x, UI, whichKeysToDisplay, indigo.kStateImageSel.TemperatureSensorOn,newStatus, decimalPlaces = 1)
							
							self.addToStatesUpdateDict(dev.id, "raw", float(data["raw"]))

						except Exception as e:
							self.exceptionHandler(40, e)
							self.indiLOG.log(10, "{}".format(props))


					if sensor == "as3935":
						try:
							if data["eventType"]  == "no Action yet":
								self.addToStatesUpdateDict(dev.id, "eventType", "no Data")
							elif data["eventType"]	 == "no lightning today":
								self.addToStatesUpdateDict(dev.id, "eventType", "no lightning today")
							elif data["eventType"]	 == "measurement":
								self.addToStatesUpdateDict(dev.id, "eventType", "measurement")
								if data["lightning"]  == "lightning detected":
									x, UI  = int(float(data["distance"])),	  "Distance {:.0f}[km]".format(float(data["distance"]))
									newStatus = self.setStatusCol( dev, "distance", x, UI, whichKeysToDisplay, indigo.kStateImageSel.TemperatureSensorOn,newStatus, decimalPlaces = 0)
									self.addToStatesUpdateDict(dev.id, "energy", float(data["energy"]))
									newStatus = self.setStatusCol( dev, "lightning", data["lightning"], "lightning "+datetime.datetime.now().strftime("%m-%d %H:%M:%S"), whichKeysToDisplay, indigo.kStateImageSel.TemperatureSensorOn,newStatus)
									self.addToStatesUpdateDict(dev.id, "lastLightning", datetime.datetime.now().strftime(_defaultDateStampFormat))
									rightNow = time.time()
									nDevs = 1
									#indigo.server.log("  checking devL for "+ dev.name )
									for devL in indigo.devices.iter("props.isLightningDevice"):
										if devL.id == dev.id: continue
										deltaTime = time.time() - self.getTimetimeFromDateString( devL.states["lastLightning"])
										if deltaTime < self.lightningTimeWindow :
											nDevs += 1
										#indigo.server.log(" deltaTime: {}".format(deltaTime))
									if nDevs >= self.lightningNumerOfSensors:
										indigo.variable.updateValue("lightningEventDevices", "{}".format(nDevs))
										time.sleep(0.01) # make shure the # of devs gets updated first
										indigo.variable.updateValue("lightningEventDate",datetime.datetime.now().strftime(_defaultDateStampFormat))

								elif data["lightning"].find("Noise") == 0:
									self.addToStatesUpdateDict(dev.id, "lightning", "calibrating,- sensitivity ")
								elif data["lightning"].find("Disturber") == 0:
									self.addToStatesUpdateDict(dev.id, "lightning", "calibrating,- Disturber event ")
						except Exception as e:
							self.exceptionHandler(40, e)
							self.indiLOG.log(40, "{}".format(props) +"\n{}".format(data))
						continue


					if "CO2" in data:
						x, UI  = int(float(data["CO2"])),   "CO2 {:.0f}[ppm] ".format(float(data["CO2"]))
						newStatus = self.setStatusCol( dev, "CO2", x, UI, whichKeysToDisplay, indigo.kStateImageSel.TemperatureSensorOn,"", decimalPlaces = 1)

					if "hum" in data:
						if data["hum"] > -1:
							hum = max(0., min(data["hum"],100.))
							x, UI, decimalPlaces  = self.convHum(hum)
							#indigo.server.log("Humidity dev:{}, x:{}, UI:{}, decimalPlaces:{}".format(dev.name, x, UI, decimalPlaces ))
							newStatus = self.setStatusCol( dev, "Humidity", x, UI, whichKeysToDisplay, indigo.kStateImageSel.HumiditySensor,newStatus, decimalPlaces = 0 )
							

					if dev.deviceTypeId in ["BLEMKKsensor"]:
						self.updateBLEMKKon(dev,data,whichKeysToDisplay, pi)

					if "temp" in data:
						temp = data["temp"]
						x, UI, decimalPlaces, useFormat = self.convTemp(temp)
						if x > 500. or x < -500.:
							x = "bad data"
							UI = "bad data"
							decimalPlaces = ""
						newStatus = self.setStatusCol( dev, "Temperature", x, UI, whichKeysToDisplay, indigo.kStateImageSel.TemperatureSensorOn,newStatus, decimalPlaces = decimalPlaces )
						

					if "AmbientTemperature" in data:
						temp = data["AmbientTemperature"]
						x, UI, decimalPlaces, useFormat  = self.convTemp(temp)
						if x > 500. or x < -500.:
							x = "bad data"
							UI = "bad data"
							decimalPlaces = ""
						newStatus = self.setStatusCol( dev, "AmbientTemperature", x, UI, whichKeysToDisplay, indigo.kStateImageSel.TemperatureSensorOn,newStatus, decimalPlaces = decimalPlaces )


					if "press" in data:
						x, UI, decimalPlaces, useFormat  = self.getPressureDisplay(data)
						newStatus = self.setStatusCol(dev, "Pressure", x, UI,  whichKeysToDisplay, "", newStatus, decimalPlaces = decimalPlaces)
						

					if dev.deviceTypeId == "BLEiTrackButton":
						self.updateBLEiTrack(dev,data,whichKeysToDisplay, pi)
						
					if dev.deviceTypeId.find("BLEShelly") == 0:
						self.updateBLEShelly(dev,data,whichKeysToDisplay, pi)
						

					if dev.deviceTypeId == "BLEblueradio":
						self.updateBLEblueradio(dev,data,whichKeysToDisplay, pi)

					if dev.deviceTypeId == "BLEaprilAccel":
						self.updateAPRILaccel(dev,data,whichKeysToDisplay, pi)

					if dev.deviceTypeId in ["BLEiBS01", "BLEiBS02", "BLEiBS03"]:
						self.updateBLEiBSxxOneOnOff(dev,data,whichKeysToDisplay, pi)

					if dev.deviceTypeId == "BLEiBS03G":
						self.updateBLEiBS03G(dev,data,whichKeysToDisplay, pi)

					if dev.deviceTypeId in ["BLEMKKsensor"]:
						self.updateBLEMKKon(dev,data,whichKeysToDisplay, pi)

					if dev.deviceTypeId in ["BLEiBS03RG", "BLEiBS01RG", "BLESatech"]:
						self.updateBLEiBS0xRG(dev,data,whichKeysToDisplay, pi)

					if dev.deviceTypeId in ["BLEiSensor-onOff", "BLEiSensor-on", "BLEiSensor-RemoteKeyFob", "BLEiSensor-TempHum"]:
						self.updateBLEiSensor(dev,data,whichKeysToDisplay, pi)

					if "proximity" in data:
						newStatus, self.setProximity(dev, props, data, whichKeysToDisplay,newStatus)

					if dev.deviceTypeId in ["BLEthermoBeacon"]:
						self.updateOnOffState(dev,data,whichKeysToDisplay, pi)

					if "moisture" in data:
						newStatus, self.setMoistureDisplay(dev, props, data, whichKeysToDisplay,newStatus)

					if "Vertical" in data:
						try:
							x, UI  = float(data["Vertical"]),  "{:7.3f}".format(float(data["Vertical"]))
							newStatus = self.setStatusCol( dev, "VerticalMovement", x, UI, whichKeysToDisplay, indigo.kStateImageSel.TemperatureSensorOn,newStatus, decimalPlaces = 3)
						except: pass

					if "Horizontal" in data:
						try:
							x, UI  = float(data["Horizontal"]), "{:7.3f}".format(float(data["Horizontal"]))
							newStatus = self.setStatusCol( dev, "HorizontalMovement", x, UI, whichKeysToDisplay, indigo.kStateImageSel.TemperatureSensorOn,newStatus, decimalPlaces = 3)
						except: pass

					if "MinimumPixel" in data:
						x, UI, decimalPlaces, useFormat  = self.convTemp(data["MinimumPixel"])
						newStatus = self.setStatusCol( dev, "MinimumPixel", x, UI, whichKeysToDisplay, indigo.kStateImageSel.TemperatureSensorOn,newStatus, decimalPlaces = decimalPlaces)

					if "MaximumPixel" in data:
						x, UI, decimalPlaces, useFormat  = self.convTemp(data["MaximumPixel"])
						newStatus = self.setStatusCol( dev, "MaximumPixel", x, UI, whichKeysToDisplay, indigo.kStateImageSel.TemperatureSensorOn,newStatus, decimalPlaces = decimalPlaces)

					if "GasResistance" in data:
						gr,grUI, aq, aqUI, gb, gbUI, SensorStatus, AirQualityText = self.convGas(data, dev, props)
						newStatus = self.setStatusCol( dev, "GasResistance",	gr, 			grUI, 			whichKeysToDisplay, indigo.kStateImageSel.TemperatureSensorOn,newStatus, decimalPlaces = 0)
						newStatus = self.setStatusCol( dev, "AirQuality",		aq, 			aqUI, 			whichKeysToDisplay, indigo.kStateImageSel.TemperatureSensorOn,newStatus, decimalPlaces = 0)
						newStatus = self.setStatusCol( dev, "GasBaseline",		gb, 			gbUI, 			whichKeysToDisplay, indigo.kStateImageSel.TemperatureSensorOn,newStatus, decimalPlaces = 0)
						newStatus = self.setStatusCol( dev, "SensorStatus",		SensorStatus, 	SensorStatus, 	whichKeysToDisplay, indigo.kStateImageSel.TemperatureSensorOn,newStatus, decimalPlaces = 0)
						newStatus = self.setStatusCol( dev, "AirQualityText",	AirQualityText, AirQualityText,	whichKeysToDisplay, indigo.kStateImageSel.TemperatureSensorOn,newStatus, decimalPlaces = 0)
						

					if "MovementAbs" in data:
						try:
							x, UI  = float(data["MovementAbs"]), "{:5.2f}".format(float(data["MovementAbs"]))
							newStatus = self.setStatusCol( dev, "MovementAbs", x, UI, whichKeysToDisplay, indigo.kStateImageSel.TemperatureSensorOn,newStatus, decimalPlaces = 2)
						except: pass

					if "Movement" in data:
						try:
							x, UI  = float(data["Movement"]), "{:5.2f}".format(float(data["Movement"]))
							newStatus = self.setStatusCol( dev, "Movement", x, UI, whichKeysToDisplay, indigo.kStateImageSel.TemperatureSensorOn,newStatus, decimalPlaces = 2)
						except: pass

					if "Uniformity" in data:
						try:
							x, UI  = float(data["Uniformity"]), "{:5.1f}".format(float(data["Uniformity"]))
							newStatus = self.setStatusCol( dev, "Uniformity", x, UI, whichKeysToDisplay, indigo.kStateImageSel.TemperatureSensorOn,newStatus, decimalPlaces = 1)
						except: pass

					if sensor == "amg88xx" and "rawData" in data :
						try:
							if ("imageFilesaveRawData" in props and props["imageFilesaveRawData"] =="1") or ("imageFileNumberOfDots" in props and props["imageFileNumberOfDots"] !="-"):
								# exapnd to 8x8 matrix, data is in 4 byte packages *100
								pixPerRow = 8
								dataRaw = json.loads(data["rawData"])
								dataRaw = json.dumps([[dataRaw[kkkx] for kkkx in range(pixPerRow*(iiix), pixPerRow*(iiix+1))] for iiix in range(pixPerRow)])

								if "imageFilesaveRawData" in props and props["imageFilesaveRawData"] == "1":
										newStatus = self.setStatusCol( dev, "rawData", dataRaw,"", whichKeysToDisplay, indigo.kStateImageSel.TemperatureSensorOn,newStatus, decimalPlaces = "")
								if "imageFileNumberOfDots" in props and props["imageFileNumberOfDots"] != "-":
									if "imageFileName" in props and len(props["imageFileName"])>1:
										imageParams	  = json.dumps( {"logFile":self.PluginLogFile, "logLevel":props["imageFilelogLevel"], "compress":props["imageFileCompress"], "fileName":self.cameraImagesDir+props["imageFileName"], "numberOfDots":props["imageFileNumberOfDots"], "dynamic":props["imageFileDynamic"], "colorBar":props["imageFileColorBar"]} )
										cmd = self.pythonPath + " '" + self.pathToPlugin + "makeCameraPlot.py' '" +imageParams+"' '"+dataRaw+"' & "
										if props["imageFilelogLevel"] == "1": self.indiLOG.log(10,"AMG88 command:{}".format(cmd))
										#self.indiLOG.log(30," cmd:{}".format(cmd))
										subprocess.call(cmd, shell=True)
						except Exception as e:
							self.exceptionHandler(40, e)
							self.indiLOG.log(40, "{}".format(props))
							self.indiLOG.log(40, "{}".format(len(data["rawData"]))+"     "+data["rawData"])

					if sensor == "mlx90640" and "rawData" in data :
						try:
							if ("imageFilesaveRawData" in props and props["imageFilesaveRawData"] == "1") or ("imageFileNumberOfDots" in props and props["imageFileNumberOfDots"] != "-"):
								# exapnd to 8x8 matrix, data is in 4 byte packages *100
								dataRaw = data["rawData"]

								if "imageFilesaveRawData" in props and props["imageFilesaveRawData"] == "1" and False:
										newStatus = self.setStatusCol( dev, "rawData", dataRaw,"", whichKeysToDisplay, indigo.kStateImageSel.TemperatureSensorOn,newStatus, decimalPlaces = "")
								if "imageFileNumberOfDots" in props and props["imageFileNumberOfDots"] !="-":
									if "imageFileName" in props and len(props["imageFileName"])>1:
										imageParams	  = json.dumps( {"logFile":self.PluginLogFile, "logLevel":props["imageFilelogLevel"],"compress":props["imageFileCompress"], "fileName":self.cameraImagesDir+props["imageFileName"], "numberOfDots":props["imageFileNumberOfDots"], "dynamic":props["imageFileDynamic"], "colorBar":props["imageFileColorBar"]} )
										cmd = self.pythonPath + " '" + self.pathToPlugin + "makeCameraPlot.py' '" +imageParams+"' '"+dataRaw+"' & "
										#self.indiLOG.log(30," cmd:{}".format(cmd))
										if props["imageFilelogLevel"] == "1": self.indiLOG.log(10,"mlx90640 command:{}".format(cmd))
										subprocess.call(cmd, shell=True)
						except Exception as e:
							self.exceptionHandler(40, e)
							self.indiLOG.log(40, "{}".format(props))
							self.indiLOG.log(40, "{}".format(len(data["rawData"]))+"     "+data["rawData"])


					if sensor == "lidar360" :
						try:
								xx = data["triggerValues"]
								newStatus = self.setStatusCol( dev, "Leaving_count", 					xx["current"]["GT"]["totalCount"],	"leaving Count:{}".format(xx["current"]["GT"]["totalCount"]),			whichKeysToDisplay, indigo.kStateImageSel.TemperatureSensorOn,newStatus, decimalPlaces = 0)
								newStatus = self.setStatusCol( dev, "Approaching_count", 				xx["current"]["LT"]["totalCount"],	"approaching Count:{}".format(xx["current"]["LT"]["totalCount"]),		whichKeysToDisplay, indigo.kStateImageSel.TemperatureSensorOn,newStatus, decimalPlaces = 0)
								newStatus = self.setStatusCol( dev, "Re-Calibration_needed_count",		xx["calibrated"]["GT"]["totalCount"], "calibration Count:{}".format(xx["calibrated"]["GT"]["totalCount"]), 	whichKeysToDisplay, indigo.kStateImageSel.TemperatureSensorOn,newStatus, decimalPlaces = 0)
								newStatus = self.setStatusCol( dev, "Room_occupied_count", 			xx["calibrated"]["LT"]["totalCount"], "occupied Count:{}".format(xx["calibrated"]["LT"]["totalCount"]),		whichKeysToDisplay, indigo.kStateImageSel.TemperatureSensorOn,newStatus, decimalPlaces = 0)

								newStatus = self.setStatusCol( dev, "Leaving_value", 					xx["current"]["GT"]["totalSum"],		"leaving value:{}".format(xx["current"]["GT"]["totalSum"]),				whichKeysToDisplay, indigo.kStateImageSel.TemperatureSensorOn,newStatus, decimalPlaces = 0)
								newStatus = self.setStatusCol( dev, "Approaching_value", 				xx["current"]["LT"]["totalSum"],		"approcahing value:{}".format(xx["current"]["LT"]["totalSum"]), 		whichKeysToDisplay, indigo.kStateImageSel.TemperatureSensorOn,newStatus, decimalPlaces = 0)
								newStatus = self.setStatusCol( dev, "Re-Calibration_needed_value", 	xx["calibrated"]["GT"]["totalSum"],	"calibration value:{}".format(xx["calibrated"]["GT"]["totalSum"]),		whichKeysToDisplay, indigo.kStateImageSel.TemperatureSensorOn,newStatus, decimalPlaces = 0)
								newStatus = self.setStatusCol( dev, "Room_occupied_value", 			xx["calibrated"]["LT"]["totalSum"],	"occupied value:{}".format(xx["calibrated"]["LT"]["totalSum"]),			whichKeysToDisplay, indigo.kStateImageSel.TemperatureSensorOn,newStatus, decimalPlaces = 0)

								newStatus = self.setStatusCol( dev, "Current_NonZeroBins", 			xx["current"]["nonZero"],				"current non zero bins:{}".format(xx["current"]["nonZero"]),			whichKeysToDisplay, indigo.kStateImageSel.TemperatureSensorOn,newStatus, decimalPlaces = 0)
								newStatus = self.setStatusCol( dev, "Calibration_NonZeroBins", 		xx["calibrated"]["nonZero"],			"calibration non zero bins:{}".format(xx["calibrated"]["nonZero"]),		whichKeysToDisplay, indigo.kStateImageSel.TemperatureSensorOn,newStatus, decimalPlaces = 0)
								newStatus = self.setStatusCol( dev, "ubsPortUsed", 					xx["port"],							xx["port"],																whichKeysToDisplay, indigo.kStateImageSel.TemperatureSensorOn,newStatus, decimalPlaces = 0)

								varName =(dev.name+"_calibrated").replace(" ","_")
								try:
									var = indigo.variables[varName]
								except:
									var = indigo.variable.create(varName,"", self.iBeaconFolderVariablesName_ID)
									self.varExcludeSQLList.append(var)

								if "calibrated" in data and len(data["calibrated"]) > 10:
									indigo.variable.updateValue(varName, json.dumps(data["calibrated"]))
								else:
									try:	data["calibrated"] =  json.loads(var.value)
									except: data["calibrated"] = []

								if "saveRawData" in props and props["saveRawData"] == "1":
									varName =(dev.name+"_data").replace(" ","_")
									try:
										var = indigo.variables[varName]
									except:
										indigo.variable.create(varName, varName, self.iBeaconFolderVariablesName_ID)
										self.varExcludeSQLList.append(varName)
									indigo.variable.updateValue(varName, json.dumps(data))


								if len(props["fileName"]) < 5:	fileName = self.indigoPreferencesPluginDir+"lidar360Images/"+dev.name+".png"
								else: 						  	fileName = props["fileName"]

								if "mode" in props and props["mode"] in ["manual", "auto"] and ("sendPixelData" in props and props["sendPixelData"] =="1"):
									dataFile = "/tmp/makelidar360.dat"
									if  os.path.isfile(dataFile):
										lastlidar360PlotTime = os.path.getmtime(dataFile)
									else: lastlidar360PlotTime = 0
									if (    "showImageWhen" not in props or
											( time.time() - lastlidar360PlotTime > float(props["showImageWhen"]) ) or
											data["triggerValues"]["current"]["GT"]["totalCount"] != 0 or
											data["triggerValues"]["current"]["LT"]["totalCount"] != 0 or
											data["triggerValues"]["calibrated"]["GT"]["totalCount"] != 0 or
											data["triggerValues"]["calibrated"]["LT"]["totalCount"] != 0    ):

										imageParams	  ={"logFile":self.PluginLogFile,
													"logLevel":props["logLevel"],
													"dataFile":"/tmp/makelidar360.dat",
													"compress":props["fileCompress"],
													"fileName":fileName,
													"xMin":props["xMin"],
													"xMax":props["xMax"],
													"yMin":props["yMin"],
													"yMax":props["yMax"],
													"scalefactor":props["scalefactor"],
													"showZeroValues":props["showZeroValues"],
													"mode":props["mode"],
													"showPhi0":props["showPhi0"],
													"showZeroDot":props["showZeroDot"],
													"frameON":props["frameON"],
													"DPI":props["DPI"],
													"showTriggerValues":props["showTriggerValues"],
													"doNotUseDataRanges":props["doNotUseDataRanges"],
													"showTimeStamp":props["showTimeStamp"],
													"showDoNotTrigger":props["showDoNotTrigger"],
													"fontSize":props["fontSize"],
													"showLegend":props["showLegend"],
													"topText":props["topText"],
													"frameTight":props["frameTight"],
													"yOffset":props["yOffset"],
													"xOffset":props["xOffset"],
													"numberOfDotsX":props["numberOfDotsX"],
													"numberOfDotsY":props["numberOfDotsY"],
													"phiOffset":props["phiOffset"],
													"anglesInOneBin":props["anglesInOneBin"],
													"colorCurrent":props["colorCurrent"],
													"colorCalibrated":props["colorCalibrated"],
													"colorLast":props["colorLast"],
													"colorBackground":props["colorBackground"]}
										#allData = json.dumps({"imageParams":imageParams, "data":data})
										cmd = self.pythonPath + " '" + self.pathToPlugin + "makeLidar360Plot.py' '" +json.dumps(imageParams)+"'  & "
										#self.indiLOG.log(30," cmd:{}".format(cmd))
										if props["logLevel"] in ["1", "3"] : self.indiLOG.log(10,"lidar360 command:{}".format(cmd))
										self.writeJson(data, fName="/tmp/makeLidar360.dat")
										subprocess.call(cmd, shell=True)
						except Exception as e:
							self.exceptionHandler(40, e)
							self.indiLOG.log(40,"props: {}".format(props))
							self.indiLOG.log(40,"triggervalues: {}".format(data["triggerValues"]) )

					if updateProps:
						dev.replacePluginPropsOnServer(props)


				for devIds in devUpdate:
					if devIds in self.updateStatesDict:
						if self.decideMyLog("SensorData"): self.indiLOG.log(5,"pi# {}  {}  {}".format(piU, devIds, self.updateStatesDict))
						self.executeUpdateStatesDict(onlyDevID=devIds, calledFrom="updateSensors end")
			self.saveSensorMessages(devId="")

			self.checkGarageDoor()

		except Exception as e:
			self.exceptionHandler(40, e)
			self.indiLOG.log(40,"pi# {}  {}".format(piU, sensors))

		return

####-------------------------------------------------------------------------####
	def updaterainSensorRG11(self, dev, data, whichKeysToDisplay):
		try:
			props = dev.pluginProps
			if "lastUpdate" not in props or props["lastUpdate"]=="0":
				props["lastUpdate"] = time.time()
			dd = datetime.datetime.now().strftime(_defaultDateStampFormat)
			updateDev = False
			##indigo.server.log("{}".format(data))
			rainChanges = []
			if len(dev.states["resetDate"]) < 5:
				rainChanges.append(["resetDate", dd, dd,""])
				#self.addToStatesUpdateDict(dev.id, "resetDate", datetime.datetime.now().strftime(_defaultDateStampFormat))

			if	 self.rainUnits == "inch":	   mult = 1/25.4	; unit = "in"
			elif self.rainUnits == "cm":	   mult = 0.1 		; unit = "cm"
			else:                              mult = 1 		; unit = "mm"

			if "format" in props and len(props["format"])<2: form = "%.{}f[{}]".format(self.rainDigits+1, self.rainUnits)
			else:											  form = props["format"]

			for cc in ["totalRain", "rainRate", "measurementTime", "mode", "rainLevel", "sensitivity", "nBuckets", "nBucketsTotal", "bucketSize"]:
				if cc in data:

					if cc == "totalRain":
						x = float(data[cc])*mult	 # is in mm
						rainChanges.append([cc, x, form%x, self.rainDigits])
						for zz in ["hourRain", "dayRain", "weekRain", "monthRain", "yearRain"]:
							zzP= zz+"Total"
							if zzP in props:
								oldV = float(props[zzP])
								if oldV > x:
									props[zzP] = x
									updateDev = True
									oldV = x
								rainChanges.append([zz, x-oldV, "{}".format(x-oldV), self.rainDigits])


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
										rainChanges.append(["rainText", item[1], "{}".format(item[1]),""])
										break
								except: pass

					elif cc == "measurementTime":
						x = data[cc]
						rainChanges.append([cc, int(x), "{}".format(int(x)),""])

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
									rainChanges.append(["status", labels[x], labels[x],""])
					elif cc == "nBuckets":
						try: x = int(data[cc])
						except: x = 0
						rainChanges.append([cc, int(x), "{}".format(int(x)),""])
					elif cc == "nBucketsTotal":
						try: x = int(data[cc])
						except: x = 0
						rainChanges.append([cc, int(x), "{}".format(int(x)),""])
					elif cc == "bucketSize":
						try:
							xx = "0[{}]".format(unit)
							x = float(data[cc])*mult
							if x > 0:  xx = "{:.2f}[{}]".format(x, unit)
						except: pass
						rainChanges.append([cc, x,xx, 4])
					else:
						x = data[cc]
						rainChanges.append([cc, x, "{}".format(x),""])
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

		except Exception as e:
			self.exceptionHandler(40, e)
			self.indiLOG.log(40, "{}".format(data))
		return



###-------------------------------------------------------------------------####
	def getDeviceStateList(self, dev):
		try:
			if self.getDeviceStateListCalls < 400 and self.debugNewDevStates: self.indiLOG.log(10,"populating device state lists, #:{} calls, dev:{}".format(self.getDeviceStateListCalls, dev.name))
			self.getDeviceStateListCalls  += 1
			#if called for one make it call for device 

			statesCategoriesForDevtype = self.setstatesCategoriesForDevtype(dev)
			#if dev.name.find("s-x-BLEXiaomiMiformaldehyde-48:57:43:00:10:FC") >-1:self.indiLOG.log(20,"dev:{};  statesCategoriesForDevtype:{}".format(dev.name, statesCategoriesForDevtype ))

			newStateList  = super(Plugin, self).getDeviceStateList(dev)

			props = dev.pluginProps
			xx = props.get("removeStates","")
			if len(xx) < 2: removeStates = []
			else:
				removeStates = xx.strip(",").split(",")
				#self.indiLOG.log(20,"getDeviceStateList {}:  removing states:{};".format(dev.name, removeStates ))

			stateAlreadyDone = {}
			for addStateCat in statesCategoriesForDevtype: #  eg (Temperature, Humidity, CO2, beacon ,......)
				if addStateCat in removeStates:
					#self.indiLOG.log(20,"getDeviceStateList {}:  removing state:{};".format(dev.name, addStateCat ))
					continue  # dynamically exclude states
				#if dev.name.find("s-x-BLEXiaomiMiformaldehyde-48:57:43:00:10:FC") >-1: self.indiLOG.log(20,"addStateCat:{};".format(addStateCat  ))
				if  addStateCat in _addingstates: # (Temperature, Humidity, CO2, ...)
					#if dev.name.find("s-x-BLEXiaomiMiformaldehyde-48:57:43:00:10:FC") >-1: self.indiLOG.log(20,"addState:{}; _addingstates:{}".format(addStateCat, _addingstates[addStateCat]["States"]  ))
					for state in _addingstates[addStateCat]["States"]:
						stateType = _addingstates[addStateCat]["States"][state] 
						if state.find("Pi_") == 0:
							if state.find("_Signal") == 5 or state.find("_Distance") == 5 or state.find("_Time") == 5:
								piIDs = str(int(state[3:5]))
								if self.RPI[piIDs]["piOnOff"] == "0": 
									#if self.decideMyLog("Special"): self.indiLOG.log(20,"rej  pi dist..:{}; st:{}; id:{}; active:{} ".format(dev.name, state, piIDs, self.RPI[piIDs]["piOnOff"]))
									continue
						if _addingstates[addStateCat]["addTag"]:
							xx = addStateCat+state  # eg Temperature+MinYesterday
						else:
							xx = state  # eg  PosX PosY
						#if dev.name.find("s-x-BLEXiaomiMiformaldehyde-48:57:43:00:10:FC") >-1: self.indiLOG.log(20,"state:{}, stateSub:{}, stateType:{}; addTag:{}".format(xx, state, stateType,_addingstates[addStateCat]["addTag"] ))

						if xx in stateAlreadyDone: continue
						stateAlreadyDone[xx] = 1

						if stateType.lower() == "real":
							stateToBeadded = self.getDeviceStateDictForRealType(xx, xx, xx)

						elif stateType.lower() == "integer":
							stateToBeadded = self.getDeviceStateDictForIntegerType(xx, xx, xx)

						elif stateType.lower() == "number":
							stateToBeadded = self.getDeviceStateDictForNumberType(xx, xx, xx)

						elif stateType.lower() == "string":
							stateToBeadded = self.getDeviceStateDictForStringType(xx, xx, xx)

						elif stateType.lower() == "booltruefalse":
							stateToBeadded = self.getDeviceStateDictForBoolTrueFalseType(xx, xx, xx)

						elif stateType.lower() == "boolonezero":
							stateToBeadded = self.getDeviceStateDictForBoolTrueFalseType(xx, xx, xx)

						elif stateType.lower() == "Boolonoff":
							stateToBeadded = self.getDeviceStateDictForBoolTrueFalseType(xx, xx, xx)

						elif stateType.lower() == "boolyesno":
							stateToBeadded = self.getDeviceStateDictForBoolTrueFalseType(xx, xx, xx)

						elif stateType.lower() == "enum":
							stateToBeadded = self.getDeviceStateDictForEnumType(xx, xx, xx)

						elif stateType.lower() == "separator":
							stateToBeadded = self.getDeviceStateDictForSeparatorType(xx, xx, xx)

						else:
							continue

						newStateList.append(stateToBeadded)
			if self.debugNewDevStates:
				self.printStatelist(dev, newStateList)
			return newStateList

		
		except Exception as e:
			self.exceptionHandler(40, e)
		return {}

###-------------------------------------------------------------------------####
	def printStatelist(self, dev, stateList):
		try:
				xList = ""
				for ll in stateList:
					for xx in ll: 
						if xx == "Key":
							xList += "{};".format(ll[xx])
				self.indiLOG.log(10,"updating states:{}, len:{}, ret={}.. ".format(dev.name, len(stateList), xList[0:200]))
		except Exception as e:
			self.exceptionHandler(40, e)
		return 
####-------------------------------------------------------------------------####
	def setstatesCategoriesForDevtype(self, dev):
		try:
			props = dev.pluginProps
			test = "allDevHaveTheseStates,"
			for state in _stateListToDevTypes:
					if dev.deviceTypeId in _stateListToDevTypes[state]:
						test += state+","

			if dev.pluginProps.get("SupportsBatteryLevel",False):
				test += "lastBatteryReplaced"
			return test.strip(",").split(",")
			 

		except Exception as e:
			self.exceptionHandler(40, e)
		return []



	def setlastBatteryReplaced(self, dev, newBatL):
		try:	

			if "lastBatteryReplaced"  not in dev.states: return 
			if "batteryLevel"  not in dev.states: return 

			upd = False
			# remember the last datetime when batlevel was 100%
			if len(dev.states["lastBatteryReplaced"]) < 5:
					upd = True

			if  newBatL == 100:
				if len(str(dev.states["batteryLevel"])) < 1:# not set yet
					upd = True

				elif  dev.states["batteryLevel"] < 95: # update if new 100, and old < 95% dot do 99-100-99-100, switch back and forth 
					upd = True

			elif newBatL - dev.states["batteryLevel"] > 30: # update if new > 30% of old
					upd = True

			if upd:
				self.addToStatesUpdateDict(dev.id, "lastBatteryReplaced",	datetime.datetime.now().strftime(_defaultDateStampFormat))


		except Exception as e:
			self.exceptionHandler(40, e)


###-------------------------------------------------------------------------####
	def updateCommonStates(self, dev, props, data, whichKeysToDisplay, pi):
		try:
				if "deviceVersion" in data 				and "deviceVersion" in dev.states 			and "{}".format(data["deviceVersion"]) != "{}".format(dev.states["deviceVersion"]):
									self.addToStatesUpdateDict(dev.id, "deviceVersion", 		data["deviceVersion"])

				if "serialNumber" in data 				and "serialNumber" in dev.states 			and "{}".format(data["serialNumber"]) != "{}".format(dev.states["serialNumber"]):
									self.addToStatesUpdateDict(dev.id, "serialNumber", 		data["serialNumber"])

				if "lastReset" in data 				and "lastReset" in dev.states 			and "{}".format(data["lastReset"]) !="" 	and "{}".format(data["lastReset"]) != "{}".format(dev.states["lastReset"]):
									self.addToStatesUpdateDict(dev.id, "lastReset", 		data["lastReset"])

				if "lastBadRead" in data 				and "lastBadRead" in dev.states 			and "{}".format(data["lastBadRead"]) !="" 	and "{}".format(data["lastBadRead"]) != "{}".format(dev.states["lastBadRead"]):
									self.addToStatesUpdateDict(dev.id, "lastBadRead", 		data["lastBadRead"])


				if "fastSlowRead" in data 				and "fastSlowRead" in dev.states 			and "{}".format(data["fastSlowRead"]) != "{}".format(dev.states["fastSlowRead"]):
									self.addToStatesUpdateDict(dev.id, "fastSlowRead", 		data["fastSlowRead"])


				if "sensorCo2Target" in data 	and "sensorCo2Target" in dev.states and "{}".format(data["sensorCo2Target"]) != "{}".format(dev.states["sensorCo2Target"]):
									self.addToStatesUpdateDict(dev.id, "sensorCo2Target", data["sensorCo2Target"])

				if "altitudeCompensation" in data 	and "altitudeCompensation" in dev.states and "{}".format(data["altitudeCompensation"]) != "{}".format(dev.states["altitudeCompensation"]):
									self.addToStatesUpdateDict(dev.id, "altitudeCompensation", data["altitudeCompensation"])

				if "sensorTemperatureOffset" in data 	and "sensorTemperatureOffset" in dev.states and "{}".format(data["sensorTemperatureOffset"]) != "{}".format(dev.states["sensorTemperatureOffset"]):
									self.addToStatesUpdateDict(dev.id, "sensorTemperatureOffset", data["sensorTemperatureOffset"])

				if "autoCalibration" in data 			and "autoCalibration" in dev.states 		and ("on" if str(data["autoCalibration"]) == "1" else "off") != "{}".format(dev.states["autoCalibration"]):
									self.addToStatesUpdateDict(dev.id, "autoCalibration", 		"on" if str(data["autoCalibration"]) == "1" else "off")

				if "rssi" 			in data 			and "rssi" in dev.states 					and "{}".format(data["rssi"]) != "{}".format(dev.states["rssi"]):
									self.addToStatesUpdateDict(dev.id, "rssi",					data["rssi"])

				if "txPower" 		in data 			and "txPower" in dev.states 				and "{}".format(data["txPower"]) != "{}".format(dev.states["txPower"]):
									self.addToStatesUpdateDict(dev.id, "txPower", 				data["txPower"])

				if "batteryLevel" 	in data 			and data["batteryLevel"] != "" and "batteryLevel" in dev.states :
								batL = int(data["batteryLevel"])
								if												 			"{}".format(data["batteryLevel"]) != "{}".format(dev.states["batteryLevel"]):
									self.addToStatesUpdateDict(dev.id, "batteryLevel",		 	batL)
									if "lastUpdateBatteryLevel" in dev.states:
										self.addToStatesUpdateDict(devBeacon.id, "lastUpdateBatteryLevel",	datetime.datetime.now().strftime(_defaultDateStampFormat))
									self.setlastBatteryReplaced(dev, batL)
								if props.get("isBLElongConnectDevice",False):
									if  int(props.get("beaconDevId",0)) > 0:
										devBatid =  int(props["beaconDevId"])
										if devBatid not in indigo.devices:
											self.indiLOG.log(30, f"updateCommonStates: from {pi:} updating batterylevels, dev:(dev.id:)/{dev.name:} linked beacon device w devid:{devBatid:} is not an existing indigo device, please check; incoming data:\n{data:}\n try to delete the sensor dev it should fix itself then ")
										else:
											devBeacon = indigo.devices[devBatid]
											if devBeacon.pluginProps.get("SupportsBatteryLevel","") != True:
												props = devBeacon.pluginProps
												props["SupportsBatteryLevel"] = True
												props["batteryLevelUUID"] = "inherit"
												devBeacon.replacePluginPropsOnServer(props)

											self.addToStatesUpdateDict(devBeacon.id, "batteryLevel",		 	batL)
											self.addToStatesUpdateDict(devBeacon.id, "lastUpdateBatteryLevel",	datetime.datetime.now().strftime(_defaultDateStampFormat))
											self.setlastBatteryReplaced(devBeacon, batL)

				if "batteryVoltage" in data 			and data["batteryVoltage"] !="" 			and "batteryVoltage" in dev.states and "{}".format(data["batteryVoltage"]) != "{}".format(dev.states["batteryVoltage"]):
									self.addToStatesUpdateDict(dev.id, "batteryVoltage", 		data["batteryVoltage"])

				if "modelId" in data 			and data["modelId"] !="" 			and "modelId" in dev.states and "{}".format(data["modelId"]) != "{}".format(dev.states["modelId"]):
									self.addToStatesUpdateDict(dev.id, "modelId", 		data["modelId"])


				if "mfg_info" in data 			and data["mfg_info"] !="" 			and "mfg_info" in dev.states and "{}".format(data["mfg_info"]) != "{}".format(dev.states["mfg_info"]):
									self.addToStatesUpdateDict(dev.id, "mfg_info", 		data["mfg_info"])

				if "softwareVersion" in data 			and data["softwareVersion"] !="" 			and "softwareVersion" in dev.states and "{}".format(data["softwareVersion"]) != "{}".format(dev.states["softwareVersion"]):
									self.addToStatesUpdateDict(dev.id, "softwareVersion", 		data["softwareVersion"])

				if "bits" 			in data  			and "bits" in dev.states 					and "{}".format(data["bits"]) != "{}".format(dev.states["bits"]):	
									self.addToStatesUpdateDict(dev.id, "bits", 					data["bits"])

				if "state" 			in data 			and "state"	in dev.states 					and "{}".format(data["state"]) != "{}".format(dev.states["state"]):	
									self.addToStatesUpdateDict(dev.id, "state", 				data["state"])

				if "sensorType"		 in data  			and "sensorType" 	in dev.states 			and "{}".format(data["sensorType"]) != "{}".format(dev.states["sensorType"]):	
									self.addToStatesUpdateDict(dev.id, "sensorType", 			data["sensorType"])

				if "sendsAlive" 	in data  			and "sendsAlive" 	in dev.states 			and "{}".format(data["sendsAlive"]) != "{}".format(dev.states["sendsAlive"]):	
									self.addToStatesUpdateDict(dev.id, "sendsAlive", 			"{}".format(data["sendsAlive"]))

				if "lowVoltage"		 in data  			and "lowVoltage" 	in dev.states:	
									if "lastBatteryReplaced" in dev.states and  "{}".format(data["lowVoltage"]).lower()  == "false" and (
										len(dev.states["lastBatteryReplaced"]) < 10 or  "{}".format(dev.states["lowVoltage"]).lower() not in ["true","false"]  or "{}".format(dev.states["lowVoltage"]).lower()  == "true" 	):
										self.addToStatesUpdateDict(dev.id, "lastBatteryReplaced", datetime.datetime.now().strftime(_defaultDateStampFormat) )

									if "{}".format(data["lowVoltage"]) != "{}".format(dev.states["lowVoltage"]):	
										self.addToStatesUpdateDict(dev.id, "lowVoltage", 			"{}".format(dev.states["lowVoltage"]))

				if "tampered" in data and data["tampered"] !="":
					#if True or  dev.id == 1544693341: self.indiLOG.log(20, "{}, setting state.. tampered: to {}".format(dev.name, data["tampered"] ))
					self.addToStatesUpdateDict(dev.id, "tampered", 					"{}".format(data["tampered"]))

				if "distanceEvent" in data:
					self.setStatusCol(dev, "distanceEvent",					data["distanceEvent"],						"{}".format(data["distanceEvent"]),							whichKeysToDisplay,"","",decimalPlaces=0)

				if "stopped" in data:
					self.setStatusCol(dev, "stopped",						data["stopped"],							"{}".format(data["stopped"]),								whichKeysToDisplay,"","",decimalPlaces=0)

				if "trigger" in data:
					self.setStatusCol(dev, "trigger",						data["trigger"],							"{}".format(data["trigger"]),								whichKeysToDisplay,"","",decimalPlaces=0)

				if "triggers" in data:
					self.setStatusCol(dev, "triggers",						data["triggers"],							"{}".format(data["triggers"]),								whichKeysToDisplay,"","",decimalPlaces=0)

				if "accelerationX" in data:
					self.setStatusCol(dev, "accelerationX",					data["accelerationX"],			 			"{} [cm/s^2]".format(data["accelerationX"]),				whichKeysToDisplay,"","",decimalPlaces=0)

				if "accelerationY" in data:
					self.setStatusCol(dev, "accelerationY",					data["accelerationY"],						"{} [cm/s^2]".format(data["accelerationY"]),				whichKeysToDisplay,"","",decimalPlaces=0)

				if "accelerationZ" in data:
					self.setStatusCol(dev, "accelerationZ",					data["accelerationZ"],			 			"{} [cm/s^2]".format(data["accelerationZ"]),				whichKeysToDisplay,"","",decimalPlaces=0)

				if "accelerationTotal" in data:
					self.setStatusCol(dev, "accelerationTotal",				data["accelerationTotal"],					"{} [cm/s^2]".format(data["accelerationTotal"]),			whichKeysToDisplay,"","",decimalPlaces=0)

				if "accelerationXYZMaxDelta" in data:
					self.setStatusCol(dev, "accelerationXYZMaxDelta",		data["accelerationXYZMaxDelta"],			"{} [cm/s^2]".format(data["accelerationXYZMaxDelta"]),		whichKeysToDisplay,"","",decimalPlaces=0)

				if "accelerationVectorDelta" in data:
					self.setStatusCol(dev, "accelerationVectorDelta",		data["accelerationVectorDelta"],			"{} %".format(data["accelerationVectorDelta"]),				whichKeysToDisplay,"","",decimalPlaces=0)

				if "secsSinceStart" in data:
					self.setStatusCol(dev, "secsSinceStart",				data["secsSinceStart"],						"{}".format(data["secsSinceStart"]),						whichKeysToDisplay,"","",decimalPlaces=0)

				if "measurementCount" in data:
					self.setStatusCol(dev, "measurementCount",		 		data["measurementCount"],					"{}".format(data["measurementCount"]),						whichKeysToDisplay,"","",decimalPlaces=0)

				if "movementCount" in data:
					self.setStatusCol(dev, "movementCount",			 		data["movementCount"],						"{}".format(data["movementCount"]),						whichKeysToDisplay,"","",decimalPlaces=0)
	

				if  "i2c" in data and  data["i2c"] != "" and "i2c" in dev.states and "{}".format(data["i2c"]) != "{}".format(dev.states["i2c"]):
					self.addToStatesUpdateDict(dev.id, "i2c", data["i2c"])


				if  "Formaldehyde" in data and "Formaldehyde" in dev.states:
					try:
						useData = float(data["Formaldehyde"])
						if useData >= 0:
							useData = round(useData,2)
							if props.get("FormaldehydeUnit","") == "ppm":
								useData *= 0.815
								useData = round(useData,2)
								self.setStatusCol(dev, "Formaldehyde", 		useData, 				"{}[ppm]".format(useData),					whichKeysToDisplay, "", "" ,decimalPlaces=2)
							else:
								self.setStatusCol(dev, "Formaldehyde", 		useData, 				"{}[mg/m3]".format(useData),				whichKeysToDisplay, "", "", decimalPlaces=2)

					except: pass

				if  "Conductivity" in data and  data["Conductivity"] != "" and "Conductivity" in dev.states:
						self.setStatusCol(dev, "Conductivity",		data["Conductivity"],	"{}[µS/cm]".format(data["Conductivity"]),	whichKeysToDisplay, indigo.kStateImageSel.TemperatureSensorOn, "", decimalPlaces=0)

				if  "connected" in data and  data["connected"] != "" and "connected" in dev.states and "{}".format(data["connected"]) != "{}".format(dev.states["connected"]):
						if not data["connected"]:
									self.setStatusCol(dev, "connected",			data["connected"],		"{}".format(data["connected"]),				whichKeysToDisplay, indigo.kStateImageSel.SensorOff,"")
									dev.updateStateImageOnServer(indigo.kStateImageSel.SensorOff)
						else:
									self.setStatusCol(dev, "connected",			data["connected"],		"{}".format(data["connected"]),				whichKeysToDisplay, "", "")

				for statename in ["lastMotion"]:
					if  statename in data: 
						xx = time.strftime(_defaultDateStampFormat, time.localtime(data[statename]))
						xxF = "LastM:{}".format(xx)
						self.setStatusCol(dev, statename, xx,xxF, whichKeysToDisplay, "","", decimalPlaces=0)


				# numbers
				for statename in ["lightCounter", "buttonCounter", "secsSinceLastMotion", "counter", "motionDuration"]:
					if  statename in data and  data[statename] != "" and statename in dev.states:
						if  data[statename] != dev.states[statename]:
							self.addToStatesUpdateDict(dev.id,statename,data[statename])

				# bool
				for statename in [ "shortOpen", "longOpen"]:
					if  statename in data and  data[statename] != "" and statename in dev.states:
						if  data[statename] != dev.states[statename]:
							self.addToStatesUpdateDict(dev.id,statename,data[statename])


				#text
				for statename in ["sensitivity", "model", "mode", "sensorSetup", "Version", "version", "light"]:
					if  statename in data and  data[statename] != "" and statename in dev.states:
						if  data[statename] != dev.states[statename]:
							self.addToStatesUpdateDict(dev.id,statename,data[statename])

				#time.time() --> datetime
				for statename in ["lastLightChange", "lastClose", "lastShortOpen", "lastLongOpen", "lastButton", "lastOn"]:
					if  statename in data and  data[statename] != "" and statename in dev.states:
						xx = time.strftime(_defaultDateStampFormat, time.localtime(data[statename]))
						if  xx != dev.states[statename] or len(dev.states[statename]) < 10:
								self.addToStatesUpdateDict(dev.id, statename, xx)

				for statename in ["onOffState"]:
					if  statename in data and  data[statename] != "" and statename in dev.states:
						#if  dev.id == 1544693341: self.indiLOG.log(20, "received.. {}:  {}, old:{}".format(dev.name, data[statename], dev.states[statename]))
						xx = str(data[statename])
						uiValue = props.get("onOffui"+xx, "on" if data[statename] else "off")
						if data[statename]:	image = "SensorOn"
						else:				image = "SensorOff"
						delayOff = float(props.get("delayOff", "0"))
						# check if we want to keep the state = "ON" for some time instead of immediately going "off" if off received
						# added delayed action of adding setting to off IF currently on and delay is set 
						if not data[statename] and delayOff > 0 and dev.states[statename]:
							self.delayedActions["data"].put( {"actionTime":time.time()+delayOff, "devId":dev.id, "updateItems":[{"stateName":statename, "value":data[statename], "uiValue":uiValue, "image":image}]})
							#if  dev.id == 1544693341: self.indiLOG.log(20, "setting delay action.. {}: new:{}, current:{}, uiValue:{}, delayOff:{}".format(dev.name, data[statename] , dev.states[statename], uiValue, delayOff))

						else:
							if data[statename]:
								# remove any delayed action off items
								#if  dev.id == 1544693341: self.indiLOG.log(20, "setting delay action.. {}: remove".format(dev.name))
								if delayOff >0:
									self.delayedActions["data"].put( {"actionTime":time.time(), "activeUntil":time.time()+delayOff, "devId":dev.id, "updateItems":[{"disable":"onOffState"}]})

							if  data[statename] != dev.states[statename]:
								#if  dev.id == 1544693341: self.indiLOG.log(20, "setting state.. {}: to {}".format(dev.name, uiValue))
								self.addToStatesUpdateDict(dev.id,statename, data[statename], uiValue=uiValue)
								if data[statename]:
									dev.updateStateImageOnServer(indigo.kStateImageSel.SensorOn)
								else:
									dev.updateStateImageOnServer(indigo.kStateImageSel.SensorOff)

				if  "chipTemperature" in data and  data["chipTemperature"] != "" and "chipTemperature" in dev.states:
					x, UI, decimalPlaces, useFormat  = self.convTemp(data["chipTemperature"])
					if "{}".format(x) != "{}".format(dev.states["chipTemperature"]):
									self.addToStatesUpdateDict(dev.id, "chipTemperature", x)

				if  "analyzed" in data and "ServiceData" in data["analyzed"] and "ServiceData" in dev.states:
					if data["analyzed"]["ServiceData"] != dev.states["ServiceData"]:
									self.addToStatesUpdateDict(dev.id, "ServiceData", data["analyzed"]["ServiceData"])

				if  "lastUpdateFromRPI" in dev.states and  "{}".format(pi) != "{}".format(dev.states["lastUpdateFromRPI"]):
									self.addToStatesUpdateDict(dev.id, "lastUpdateFromRPI", pi)


		except Exception as e:
			self.exceptionHandler(40, e)
			self.indiLOG.log(40, "{}".format(data))




###-------------------------------------------------------------------------####
	def updateBLEMKKon(self, dev, data, whichKeysToDisplay,pi):
		try:
			props = dev.pluginProps

			# check if setup of states is correct. (remove temp hum acc if on/off device only)
			SupportsSensorValue = data.get("SupportsSensorValue","")
			if SupportsSensorValue != "":
				upd = False
				if SupportsSensorValue != props["SupportsSensorValue"]:
					props["SupportsSensorValue"] = SupportsSensorValue
					upd = True
				if not SupportsSensorValue and not props["SupportsOnState"]:
					props["SupportsOnState"] = True
					upd = True
				if SupportsSensorValue and props["SupportsOnState"]:
					props["SupportsOnState"] = False
					upd = True
				if upd:
					self.indiLOG.log(20, "dev:{}, updating SupportsSensorValue:{}  SupportsOnState:{}, data:{}".format(dev.name,  SupportsSensorValue, props["SupportsOnState"], data))
					dev.replacePluginPropsOnServer(props)
					props = dev.pluginProps

			if "button" not in dev.states: return 

			if props["SupportsOnState"]: # for button only device, remove temp ..
				removeStates = ""
				if "Temperature" in dev.states:
					for st in dev.states:
						if st.lower().find("temp") > -1:
							removeStates += st+","
						if st.lower().find("hum") > -1:
							removeStates += st+","
						if st.lower().find("accel") > -1:
							removeStates += st+","
					self.indiLOG.log(20, "updateBLEMKKon:  dev:{}, removing states list:{}".format(dev.name, removeStates))
					if removeStates != "":
						props["removeStates"] = removeStates.strip(",")
						dev.replacePluginPropsOnServer(props)
						dev = indigo.devices[dev.id]
						props = dev.pluginProps
						dev.stateListOrDisplayStateIdChanged()
				

			#self.indiLOG.log(20, "dev:{},  data:{}".format(dev.name, data))

			if   data.get("onOff",False):  state = "press"
			elif data.get("onOff1",False): state = "double_press"
			elif data.get("onOff2",False): state = "long_press"
			else: return 

			#self.indiLOG.log(20, "dev:{},  state:{}; dev.state:{}".format(dev.name, state, dev.states["button"]))
			if state != dev.states["button"]:
				self.cancelDelayedActions[dev.id] = True
				#self.indiLOG.log(20, "dev:{},  chnaged, updating".format(dev.name))
				self.addToStatesUpdateDict(dev.id, "previousOnEvent", 	dev.states["currentOnEvent"])
				self.addToStatesUpdateDict(dev.id, "currentOnEvent", 	datetime.datetime.now().strftime(_defaultDateStampFormat))
				self.addToStatesUpdateDict(dev.id, "button",  		state)
				if props["displayS"] == "button":
					self.addToStatesUpdateDict(dev.id, "status",  		state, force=True)
				if not SupportsSensorValue:
					self.addToStatesUpdateDict(dev.id, "onOffState",  		True, uiValue = state, force=True)

				dev.updateStateImageOnServer(indigo.kStateImageSel.SensorOn)
				indigo.variable.updateValue("lastButtonOnBeaconDevId", "{}".format(dev.pluginProps.get("beaconDevId","0")))
				indigo.variable.updateValue("lastButtonOnDevId", "{}".format(dev.id))

				delayOff = float(props.get("delayOff", "1"))
				actions = [{"stateName":"button", "value":"off", "image":"Sensoroff"}]
				if props["displayS"] == "button":
					actions.append({"stateName":"status", "value":"off", "image":"Sensoroff"})
				if not SupportsSensorValue:
					actions.append({"stateName":"onOffState", "value":False, "uiValue":"off", "image":"Sensoroff"})
				self.sleep(0.5)
				self.delayedActions["data"].put( {"actionTime":time.time()+delayOff, "devId":dev.id, "updateItems":actions})

		except Exception as e:
			self.exceptionHandler(40, e)
			self.indiLOG.log(40, "{}".format(data))
		return




###-------------------------------------------------------------------------####
	def updateBLEiBS0xRG(self, dev, data, whichKeysToDisplay,pi):
		try:

				if "onOff1" in data and "button" in dev.states:
					self.setStatusCol(dev, "button",		 	data["onOff1"],			 		 	"{}".format(data["onOff1"]),						whichKeysToDisplay,"","",decimalPlaces=0)

				if "onOff" in data and "onOffState" in dev.states: 		self.addToStatesUpdateDict(dev.id, "onOffState", data["onOff"])

		except Exception as e:
			self.exceptionHandler(40, e)
			self.indiLOG.log(40, "{}".format(data))


###-------------------------------------------------------------------------####
	def updateBLEblueradio(self, dev, data, whichKeysToDisplay,pi):
		try:
				if "onOff" in data and "onOffState" in dev.states: 		self.addToStatesUpdateDict(dev.id, "onOffState", data["onOff"])

		except Exception as e:
			self.exceptionHandler(40, e)
			self.indiLOG.log(40, "{}".format(data))



###-------------------------------------------------------------------------####
	def getpropForonOffTrueFalse(self, props):
		if "onOffSetting" in props and props["onOffSetting"] == "on=green,off=grey":
			return False
		else:
			return  True

###-------------------------------------------------------------------------####
	def getpropForonOffText(self,dev,  props, data):
		if "onOff" not in data: return ""
		return props.get("onOffui{}".format(data["onOff"]), "on" if data["onOff"] else "off")


###-------------------------------------------------------------------------####
	def updateOnOffState(self, dev, data, whichKeysToDisplay,pi):
		if "onOff" in data and "onOffState" in dev.states:
			if data["onOff"] != dev.states["onOffState"]:
				self.addToStatesUpdateDict(dev.id, "onOffState", data["onOff"])
		return 



###-------------------------------------------------------------------------####
	def updateBLEiSensor(self, dev, data, whichKeysToDisplay,pi):
		try:


			props = dev.pluginProps
			inverse = self.getpropForonOffTrueFalse(props)
			uiValue = self.getpropForonOffText(dev, props, data)
			if dev.deviceTypeId == "BLEiSensor-on":
				if "onOff" in data and data["onOff"]:
					self.addToStatesUpdateDict(dev.id, "previousOnEvent", 	dev.states["currentOnEvent"])
					self.addToStatesUpdateDict(dev.id, "currentOnEvent", 	datetime.datetime.now().strftime(_defaultDateStampFormat))
					self.addToStatesUpdateDict(dev.id, "onOffState",  		True, uiValue=uiValue, image="SensorOn")
					dev.updateStateImageOnServer(indigo.kStateImageSel.SensorOn)
					delayOff = float(props.get("delayOff", "1"))
					self.delayedActions["data"].put( {"actionTime":time.time()+delayOff , "devId":dev.id, "updateItems":[{"stateName":"onOffState", "value":False, "uiValue":self.getpropForonOffText(dev, props, {"onOff":False}), "image":"SensorOff"}]})
					indigo.variable.updateValue("lastButtonOnBeaconDevId", "{}".format(dev.pluginProps.get("beaconDevId","0")))
					indigo.variable.updateValue("lastButtonOnDevId", "{}".format(dev.id))
			else:
				if "onOff" in data and "onOffState" in dev.states:
					if data["onOff"]:
						if not dev.states["onOffState"]:
							self.addToStatesUpdateDict(dev.id, "previousOnEvent", 	dev.states["currentOnEvent"])
							self.addToStatesUpdateDict(dev.id, "currentOnEvent", 	datetime.datetime.now().strftime(_defaultDateStampFormat))
							self.addToStatesUpdateDict(dev.id, "onOffState",  		True, uiValue=uiValue, image="Tripped" if inverse else "SensorOn")
							#self.addToStatesUpdateDict(dev.id, "sensorValue", 		1, uiValue="on")
							indigo.variable.updateValue("lastButtonOnBeaconDevId", "{}".format(dev.pluginProps.get("beaconDevId","0")))
							indigo.variable.updateValue("lastButtonOnDevId", "{}".format(dev.id))
					else:
						if dev.states["onOffState"]:
							delayOff = float(props.get("delayOff", "0"))
							if not data["onOff"] and delayOff > 0 and dev.states["onOffState"]:
								self.delayedActions["data"].put( {"actionTime":time.time()+delayOff, "devId":dev.id, "updateItems":[{"stateName":"onOffState", "value":False,  "uiValue":uiValue, "image":"SensorOn" if inverse else "SensorOff"}]})
							#if  dev.id == 1544693341: self.indiLOG.log(20, "setting delay action.. {}: new:{}, current:{}, uiValue:{}, delayOff:{}".format(dev.name, data[statename] ," dev.states[statename], uiValue, delayOff))
							else:	
								self.addToStatesUpdateDict(dev.id, "onOffState",  False, uiValue=uiValue, image="SensorOn" if inverse else "SensorOff")
				else: pass

				#{"BLEiSensor-RemoteKeyFob":{"431446557":{"sensorType":"RemoteKeyFob","SOS":true,"rssi":-76,"home":false,"away":false,"counter":1,"disarm":false,"sendsAlive":false}}}
			for xState in["SOS", "home", "away", "disarm"]:
				if xState 		in data and xState 			in dev.states:
					if data[xState]:
						self.addToStatesUpdateDict(dev.id, "previousOnEvent", 	dev.states["currentOnEvent"])
						self.addToStatesUpdateDict(dev.id, "currentOnEvent", 	datetime.datetime.now().strftime(_defaultDateStampFormat))
						self.addToStatesUpdateDict(dev.id, "previousOnType", 	dev.states["currentOnType"])
						self.addToStatesUpdateDict(dev.id, "currentOnType",  	xState)
						self.addToStatesUpdateDict(dev.id, "sensorValue", 		2, uiValue=xState)
						self.addToStatesUpdateDict(dev.id, "status", 			data[xState], uiValue=xState )
						self.addToStatesUpdateDict(dev.id, "onOffState",  		True, image="SensorOn" )
						self.delayedActions["data"].put( {"actionTime":time.time()+3.  , "devId":dev.id, "updateItems":[{"stateName":"onOffState", "value":False, "image":"SensorOff"}, {"stateName":xState, "value":False}]})
					self.addToStatesUpdateDict(dev.id, xState, 					data[xState])

			if 						"lastAliveMessage" in dev.states: 	self.addToStatesUpdateDict(dev.id, "lastAliveMessage", 	datetime.datetime.now().strftime(_defaultDateStampFormat))


		# set to grey if expired	 dev.updateStateImageOnServer(indigo.kStateImageSel.SensorOff)

		except Exception as e:
			self.exceptionHandler(40, e)
			self.indiLOG.log(40, "{}".format(data))
		return


###-------------------------------------------------------------------------####
	def updateBLEShelly(self, dev, data, whichKeysToDisplay, pi):
		try:
			props = dev.pluginProps
			inverse = self.getpropForonOffTrueFalse(props)
			uiValue = self.getpropForonOffText(dev, props, data)

			if dev.states.get("packetId",-991) == data.get("packetId",-9999): return 
			#self.indiLOG.log(20, "updateBLEShelly; dev:{}, data:{}".format(dev.name, data))

			self.addToStatesUpdateDict(dev.id, "packetId",  								data["packetId"] )

			if "button" in data:
				if data["button"] == "None":
					if dev.states["onOffState"]:
						#self.indiLOG.log(20, "updateBLEMusegear; dev:{}, uiValue:{}".format(dev.name, uiValue))
						self.addToStatesUpdateDict(dev.id, "onOffState",  				False)
						self.addToStatesUpdateDict(dev.id, "status",  					data["button"] )
					dev.updateStateImageOnServer(indigo.kStateImageSel.SensorOff)
				else:
					if not dev.states["onOffState"]:
					#self.indiLOG.log(20, "updateBLEMusegear; dev:{}, uiValue:{}".format(dev.name, uiValue))
						if "currentEventType" in dev.states:
							self.addToStatesUpdateDict(dev.id, "previousEventType", 	dev.states["currentEventType"])
							self.addToStatesUpdateDict(dev.id, "currentEventType", 		data["button"] )
						self.addToStatesUpdateDict(dev.id, "previousEvent", 			dev.states["currentEvent"])
						self.addToStatesUpdateDict(dev.id, "status",  					data["button"])
						self.addToStatesUpdateDict(dev.id, "onOffState",  				True)
						self.addToStatesUpdateDict(dev.id, "currentEvent", 				datetime.datetime.now().strftime(_defaultDateStampFormat))

						indigo.variable.updateValue("lastButtonOnBeaconDevId", "{}".format(dev.pluginProps.get("beaconDevId","0")))
						indigo.variable.updateValue("lastButtonOnDevId", "{}".format(dev.id))
						self.delayedActions["data"].put( {"actionTime":time.time()+2., "devId":dev.id, "updateItems":[{"stateName":"onOffState", "value":False, "image":"SensorOff"}, {"stateName":"status", "value":"None"}]})
						dev.updateStateImageOnServer(indigo.kStateImageSel.SensorOn)

			elif "motion" in data:
				if not dev.states["onOffState"] and  data["motion"] == "motion":
						self.addToStatesUpdateDict(dev.id, "previousEvent", 			dev.states["currentEvent"])
						self.addToStatesUpdateDict(dev.id, "status",  					data["motion"])
						self.addToStatesUpdateDict(dev.id, "onOffState",  				True)
						self.addToStatesUpdateDict(dev.id, "currentEvent", 				datetime.datetime.now().strftime(_defaultDateStampFormat))

						indigo.variable.updateValue("lastButtonOnBeaconDevId", "{}".format(dev.pluginProps.get("beaconDevId","0")))
						indigo.variable.updateValue("lastButtonOnDevId", "{}".format(dev.id))
						self.delayedActions["data"].put( {"actionTime":time.time()+2., "devId":dev.id, "updateItems":[{"stateName":"onOffState", "value":False, "image":"SensorOn"}, {"stateName":"status", "value":"None"}]})
						dev.updateStateImageOnServer(indigo.kStateImageSel.SensorTripped)

						#self.indiLOG.log(20, "updateBLEMusegear; dev:{}, uiValue:{}".format(dev.name, uiValue))
				if dev.states["onOffState"] and  data["motion"] != "motion":
						self.addToStatesUpdateDict(dev.id, "onOffState",  				False)
						self.addToStatesUpdateDict(dev.id, "status",  					data["motion"] )
						dev.updateStateImageOnServer(indigo.kStateImageSel.SensorOff)

			elif "isOpen" in data:
				if data["isOpen"] != dev.states["status"]:
						self.addToStatesUpdateDict(dev.id, "status",  					data["isOpen"])

				if not dev.states["onOffState"] and  data["isOpen"] == "isOpen":
						self.addToStatesUpdateDict(dev.id, "previousEvent", 			dev.states["currentEvent"])
						self.addToStatesUpdateDict(dev.id, "onOffState",  				True)
						self.addToStatesUpdateDict(dev.id, "currentEvent", 				datetime.datetime.now().strftime(_defaultDateStampFormat))

						indigo.variable.updateValue("lastButtonOnBeaconDevId", "{}".format(dev.pluginProps.get("beaconDevId","0")))
						indigo.variable.updateValue("lastButtonOnDevId", "{}".format(dev.id))
						dev.updateStateImageOnServer(indigo.kStateImageSel.SensorTripped)

						#self.indiLOG.log(20, "updateBLEMusegear; dev:{}, uiValue:{}".format(dev.name, uiValue))
				if dev.states["onOffState"] and  data["isOpen"] != "isOpen":
						self.addToStatesUpdateDict(dev.id, "onOffState",  		False)
						dev.updateStateImageOnServer(indigo.kStateImageSel.SensorOn)


			if "illuminance" in data:
						self.addToStatesUpdateDict(dev.id, "illuminance",  				data["illuminance"] )

			if "rotation" in data:
						self.addToStatesUpdateDict(dev.id, "rotation",  				data["rotation"] )



		except Exception as e:
			self.exceptionHandler(40, e)
			self.indiLOG.log(40, "{}".format(data))
		return


###-------------------------------------------------------------------------####
	def updateBLEiTrack(self, dev, data, whichKeysToDisplay, pi):
		try:
			props = dev.pluginProps
			inverse = self.getpropForonOffTrueFalse(props)
			uiValue = self.getpropForonOffText(dev, props, data)


			if data["onOff"]:
				if not dev.states["onOffState"]:
					#self.indiLOG.log(20, "updateBLEMusegear; dev:{}, uiValue:{}".format(dev.name, uiValue))
					self.addToStatesUpdateDict(dev.id, "previousOnEvent", 	dev.states["currentOnEvent"])
					self.addToStatesUpdateDict(dev.id, "currentOnEvent", 	datetime.datetime.now().strftime(_defaultDateStampFormat))
					self.addToStatesUpdateDict(dev.id, "onOffState",  		True, uiValue=uiValue)
					self.addToStatesUpdateDict(dev.id, "status",  			uiValue, uiValue=uiValue)
					if not inverse:	dev.updateStateImageOnServer(indigo.kStateImageSel.SensorOn)
					else:			dev.updateStateImageOnServer(indigo.kStateImageSel.SensorTripped)
					indigo.variable.updateValue("lastButtonOnBeaconDevId", "{}".format(dev.pluginProps.get("beaconDevId","0")))
					indigo.variable.updateValue("lastButtonOnDevId", "{}".format(dev.id))

			else:
				if dev.states["onOffState"]:
					#self.indiLOG.log(20, "updateBLEMusegear; dev:{}, uiValue:{}".format(dev.name, uiValue))
					self.addToStatesUpdateDict(dev.id, "status",  		   uiValue, uiValue=uiValue)
					self.addToStatesUpdateDict(dev.id, "onOffState",  		False, uiValue=uiValue)
					self.addToStatesUpdateDict(dev.id, "previousOffEvent", 	dev.states["currentOffEvent"])
					self.addToStatesUpdateDict(dev.id, "currentOffEvent", 	datetime.datetime.now().strftime(_defaultDateStampFormat))
					if inverse:		dev.updateStateImageOnServer(indigo.kStateImageSel.SensorOn)
					else:			dev.updateStateImageOnServer(indigo.kStateImageSel.SensorOff)


			if "stateOfBeacon" in data and "stateOfBeacon" in dev.states:
				if data["stateOfBeacon"] != dev.states["stateOfBeacon"]:
					self.addToStatesUpdateDict(dev.id, "stateOfBeacon", data["stateOfBeacon"])
					self.addToStatesUpdateDict(dev.id, "stateOfBeaconChange", "{}".format(datetime.datetime.now().strftime(_defaultDateStampFormat)) )

			if  "devType" in data and "devType" in dev.states:
				if data["devType"] != dev.states["devType"]:
					self.addToStatesUpdateDict(dev.id, "devType", data["devType"])


		except Exception as e:
			self.exceptionHandler(40, e)
			self.indiLOG.log(40, "{}".format(data))
		return



###-------------------------------------------------------------------------####
	def updateBLEiBSxxOneOnOff(self, dev, data, whichKeysToDisplay,pi):
		try:
			props = dev.pluginProps
			inverse = self.getpropForonOffTrueFalse(props)
			uiValue = self.getpropForonOffText(dev, props, data)

			if data["onOff"]:
				if not dev.states["onOffState"]:
					self.addToStatesUpdateDict(dev.id, "previousOnEvent", 	dev.states["currentOnEvent"])
					self.addToStatesUpdateDict(dev.id, "currentOnEvent", 	datetime.datetime.now().strftime(_defaultDateStampFormat))
					self.addToStatesUpdateDict(dev.id, "onOffState",  		True, uiValue=uiValue)
					self.addToStatesUpdateDict(dev.id, "status",  			True, uiValue=uiValue)
					if not inverse:	dev.updateStateImageOnServer(indigo.kStateImageSel.SensorOn)
					else:			dev.updateStateImageOnServer(indigo.kStateImageSel.SensorTripped)
					indigo.variable.updateValue("lastButtonOnBeaconDevId", "{}".format(dev.pluginProps.get("beaconDevId","0")))
					indigo.variable.updateValue("lastButtonOnDevId", "{}".format(dev.id))

			else:
				if dev.states["onOffState"]:
					delayOff = float(props.get("delayOff", "0"))
					# check if we want to keep the state = "ON" for some time instead of immediately going "off" if off received
					# added delayed action of adding setting to off IF currently on and delay is set 
					if not data["onOff"] and delayOff > 0 and dev.states["onOffState"]:
						image = "Sensoroff"
						if inverse: image = "SensorOn"
						self.delayedActions["data"].put( {"actionTime":time.time()+delayOff, "devId":dev.id, "updateItems":[{"stateName":"onOffState", "value":False, "uiValue":uiValue, "image":image}, {"stateName":"status", "value":False, "uiValue":uiValue, "image":image}]})
						#if  dev.id == 1544693341: self.indiLOG.log(20, "setting delay action.. {}: new:{}, current:{}, uiValue:{}, delayOff:{}".format(dev.name, data[statename] , dev.states[statename], uiValue, delayOff))

					else:
						self.addToStatesUpdateDict(dev.id, "status",  			False, uiValue=uiValue)
						self.addToStatesUpdateDict(dev.id, "onOffState",  		False, uiValue=uiValue)
						self.addToStatesUpdateDict(dev.id, "previousOffEvent", 	dev.states["currentOffEvent"])
						self.addToStatesUpdateDict(dev.id, "currentOffEvent", 	datetime.datetime.now().strftime(_defaultDateStampFormat))
						if inverse:		dev.updateStateImageOnServer(indigo.kStateImageSel.SensorOn)
						else:			dev.updateStateImageOnServer(indigo.kStateImageSel.SensorOff)



		except Exception as e:
			self.exceptionHandler(40, e)
			self.indiLOG.log(40, "{}".format(data))
		return


###-------------------------------------------------------------------------####
	def updateAPRILaccel(self, dev, data, whichKeysToDisplay,pi):
		try:
			if "onOff1" in data:
				self.addToStatesUpdateDict(dev.id, "onOffState",  	data["onOff1"])
				self.setStatusCol(dev, "move",		 		  		data["onOff1"],				 	 "{}".format(data["onOff1"]),						whichKeysToDisplay,"","")
				if data["onOff1"]:
						self.addToStatesUpdateDict(dev.id, "previousMove", dev.states["currentMove"])
						self.addToStatesUpdateDict(dev.id, "currentMove", datetime.datetime.now().strftime(_defaultDateStampFormat))
						indigo.variable.updateValue("lastButtonOnBeaconDevId", "{}".format(dev.pluginProps.get("beaconDevId","0")))
						indigo.variable.updateValue("lastButtonOnDevId", "{}".format(dev.id))

			if "onOff" in data:
				self.setStatusCol(dev, "button",		 		  	data["onOff"],				 		 "{}".format(data["onOff"]),						whichKeysToDisplay,"","")
				if data["onOff"]:
						self.addToStatesUpdateDict(dev.id, "previousOnEvent", dev.states["currentOnEvent"])
						self.addToStatesUpdateDict(dev.id, "currentOnEvent", datetime.datetime.now().strftime(_defaultDateStampFormat))
						indigo.variable.updateValue("lastButtonOnBeaconDevId", "{}".format(dev.pluginProps.get("beaconDevId","0")))
						indigo.variable.updateValue("lastButtonOnDevId", "{}".format(dev.id))
		except Exception as e:
			self.exceptionHandler(40, e)
			self.indiLOG.log(40, "{}".format(data))
		return



####-------------------------------------------------------------------------####
	def updatePMAIRQUALITY(self, dev, props, data, whichKeysToDisplay):
		try:
			for cc in ["pm10_standard", "pm25_standard", "pm100_standard", "pm10_env", "pm25_env", "pm100_env", "particles_03um", "particles_05um", "particles_10um", "particles_25um", "particles_50um", "particles_100um"]:
				if cc in data:
					if cc.find("pm") >-1: units = "ug/m3"
					else:				  units  = "C/0.1L"
					x, UI  = int(float(data[cc])), "{}={:.0f}[{}]".format(cc,float(data[cc]),units)

					self.setStatusCol(dev,cc,x,UI,whichKeysToDisplay,"","",decimalPlaces=0)


					if cc == "pm25_standard":
						limitNames   = ["Good","Moderate","Unhealthy_Sensitve", "Unhealthy", "Very_Unhealthy", "Hazardous"]
						limitValues  = [12.0,   35.4,      55.4,                  150.4,          250.4,        99999. ]
						for ln in range(len(limitNames)):
							if limitNames[ln] in props:
								try: 	limitValues[ln] = float(props[limitNames[ln]])
								except: pass
							if x < limitValues[ln]: 
								AirQualityText = limitNames[ln]
								break


						self.setStatusCol(dev, "AirQualityText",AirQualityText,"Air Quality is "+AirQualityText,whichKeysToDisplay,"","",decimalPlaces=1)

						useSetStateColor = False
						if  cc == whichKeysToDisplay:
							useSetStateColor = self.setStateColor(dev, dev.pluginProps, data[cc])
						if not useSetStateColor:
							if	 AirQualityText == "Good":		 dev.updateStateImageOnServer(indigo.kStateImageSel.SensorOn)
							elif AirQualityText == "Moderate":	 dev.updateStateImageOnServer(indigo.kStateImageSel.SensorOff)
							else:								 dev.updateStateImageOnServer(indigo.kStateImageSel.SensorTripped)

		except Exception as e:
			self.exceptionHandler(40, e)
			self.indiLOG.log(40, "{}".format(data))
		return



####-------------------------------------------------------------------------####
	def getPressureDisplay(self, data):
		try:
			p = 0
			pu = ""
			useFormat = ""
			decimalPlaces = 0
			if "press" in data:
				p = float(data["press"])
				if self.pressureUnits == "atm":
					useFormat = "{:6.3f} atm" ;		decimalPlaces = 4; mult = 0.000009869233
					p *= mult ; pu = useFormat.format(p)
				elif self.pressureUnits == "bar":
					useFormat = "{:6.3f} Bar" ;		decimalPlaces = 4; mult = 0.00001
					p *= mult ; pu = useFormat.format(p)
				elif self.pressureUnits.lower() == "mbar":
					useFormat = "{:6.0f} mBar";		decimalPlaces = 0; mult = 0.01
					p *= mult; pu = useFormat.format(p)
					p = int(p)
				elif self.pressureUnits == "mm":
					useFormat = "{:6.0f} mmHg";		decimalPlaces = 0; mult = 0.00750063
					p *= mult ; pu = useFormat.format(p)
					p = int(p)
				elif self.pressureUnits == "Torr":
					useFormat = "{:.0f} Torr" ;		decimalPlaces = 0; mult = 0.00750063
					p *= mult; pu = useFormat.format(p)
					p = int(p)
				elif self.pressureUnits == "inches":
					useFormat = "{:6.2f} inches";	decimalPlaces = 2; mult = 0.000295299802
					p *= mult ; pu = useFormat.format(p)
				elif self.pressureUnits == "PSI":
					useFormat = "{:6.2f} PSI";		decimalPlaces = 2; mult = 0.000145038
					p *= mult ; pu = useFormat.format(p)
				elif self.pressureUnits == "hPascal":
					useFormat = "{:.0f} hPa";		decimalPlaces = 0; mult = 0.01
					p *= mult ; pu = useFormat.format(p)
					p = int(p)
				else:
					useFormat = "{:.0f}  Pa"; 		decimalPlaces = 0; mult = 1.
					p *= mult ; pu = useFormat.format(p)
					p = int(p)
				pu = pu.strip()

		except Exception as e:
			self.exceptionHandler(40, e)
		#self.indiLOG.log(10,"returning {} {} dat:{} ".format( decimalPlaces, p, data) )
		return p, pu, decimalPlaces, useFormat


####-------------------------------------------------------------------------####
	def setProximityDisplay(self, dev, props, data, whichKeysToDisplay, newStatus):
		try:
			if "proximity" in data:
				p = float(data["proximity"])
				useFormat = "{:.1f} m"; 		decimalPlaces = 0; mult = 1.
				p *= mult ; pu = useFormat.format(p)
				#self.indiLOG.log(10,"p ={}  units:{}".format( p, self.pressureUnits ) )
				pu = pu.strip()
				newStatus = self.setStatusCol(dev, "Proximity", p, pu, whichKeysToDisplay, "",newStatus, decimalPlaces = 0)

		except Exception as e:
			self.exceptionHandler(40, e)
		#self.indiLOG.log(10,"returning {} {} {} dat:{} ".format( decimalPlaces, p, data) )
		return newStatus



####-------------------------------------------------------------------------####
	def setMoistureDisplay(self, dev, props, data, whichKeysToDisplay, newStatus):
		try:
			if "moisture" in data:
				raw = int(float(data["moisture"]))
				try: 	minM = float(props["minMoisture"])
				except: minM = 0
				try: 	maxM = float(props["maxMoisture"])
				except: maxM = 100.
				relM = int(100*float(raw-minM)/max(1.,maxM-minM))
				relMU = "{}%".format(relM)
				if "Moisture_raw" in dev.states:
					self.addToStatesUpdateDict(dev.id, "Moisture_raw", raw)
				newStatus = self.setStatusCol(dev, "Moisture", relM, relMU, "Moisture", indigo.kStateImageSel.TemperatureSensorOn, newStatus, decimalPlaces = 0)

		except Exception as e:
			self.exceptionHandler(40, e)
		#self.indiLOG.log(10,"returning {} {} {} dat:{} ".format( decimalPlaces, p, data) )
		return newStatus

####-------------------------------------------------------------------------####
	def setStatusCol(self,dev, key, value, valueUI, whichKeysToDisplay, image, oldStatus, decimalPlaces=1, force=False):
		try:
			newStatus = oldStatus
			if key not in dev.states:
				#self.indiLOG.log(30,"setStatusCol: dev:{} does not have state key:{}".format(dev.name, key))
				return newStatus

			if whichKeysToDisplay != "":
				whichKeysToDisplayList = whichKeysToDisplay.split("/")
				whichKeysToDisplaylength = len(whichKeysToDisplayList)
				currentDisplay = oldStatus.split("/")
				if len(currentDisplay) != whichKeysToDisplaylength: # reset? display selection changed?
					currentDisplay = whichKeysToDisplay.split("/")

			
			if "{}".format(dev.states[key]) != "{}".format(value):
				self.addToStatesUpdateDict(dev.id, key, value, decimalPlaces=decimalPlaces, force=force)
			if decimalPlaces !="":
				self.fillMinMaxSensors(dev, key, value, decimalPlaces=decimalPlaces)
				#if dev.id == 1062219179: indigo.server.log("setStatusCol {}  in setStatusCol key:{}  value:{}  valueUI:{}".format(dev.name, key, value, valueUI))
				self.updateChangedValuesInLastXXMinutes(dev, value, key, decimalPlaces)


			if whichKeysToDisplay !="":
				for i in range(whichKeysToDisplaylength):
					if whichKeysToDisplayList[i] == key:
						#if dev.name == "s-11-iSensor-door-button": indigo.server.log(dev.name+"  in after  whichKeysToDisplayList")

						if currentDisplay[i] != valueUI:
							if i ==0 :
								if self.setStateColor(dev, dev.pluginProps, value):
									image = ""

							currentDisplay[i] = valueUI
							newStatus= "/".join(currentDisplay)
							#if dev.name == "s-11-iSensor-door-button": indigo.server.log(dev.name+"  in bf   sensorValue  states:{}".format(dev.states))
							if "sensorValue" in dev.states:
								#if dev.name =="s-3-rainSensorRG11": indigo.server.log(dev.name+" af sensorValue")

								# make a very small random number must not be same, otherwise no update if it is not a number
								try: 	x = float(value)
								except:
									tt = time.time()
									x = (tt - int(tt))/10000000000000.
									decimalPlaces = ""
									##indigo.server.log(dev.name+"  setStatusCol key:"+key+"  value:{}".format(value) +"  x:{}".format(x)+"  decimalPlaces:{}".format(decimalPlaces))
								#if dev.name =="s-3-rainSensorRG11": indigo.server.log(dev.name+"  "+key+"  {}".format(value)+"   {}".format(x)+"  "+valueUI)
								#if dev.id == 1513601426: self.indiLOG.log(30,"dev: {} x:{} ui:{}".format(dev.name, int(x),newStatus))
								if decimalPlaces != "":
									self.addToStatesUpdateDict(dev.id, "sensorValue", round(x,decimalPlaces), decimalPlaces=decimalPlaces, uiValue=newStatus,image=image,force=force)
								else:
									self.addToStatesUpdateDict(dev.id, "sensorValue", x, uiValue=newStatus, image=image,force=force)
							self.addToStatesUpdateDict(dev.id, "status", newStatus, image=image,force=force)
							break


		except Exception as e:
			if "{}".format(e) != "None":##
				self.exceptionHandler(40, e)
				self.indiLOG.log(40,"dev:{}, key:{}".format(dev.name, key))
		return newStatus


####-------------------------------------------------------------------------####
	def updateOneWire(self,dev, data, whichKeysToDisplay, piU):

		## add check for oneWireAddNewSensors only add new one if TRUE
		## format:
		#"sensors":{"Wire18B20":{
		#"1565508294":{"temp":[{"28-0316b5fa44ff":"24.3"}]},
		#"1447141059":{"temp":[{"28-0516b332fbff":"24.8"}]},
		#"416059968": {"temp":[{"28-800000035de5":"21.8"},	{"28-0416b39944ff":"24.6"}]},  ## can be multiple
		#"1874530568":{"temp":[{"28-0516b33621ff":"24.6"}]}}}
		##

 		# updateOneWire: dev:s-3-onewire-1_28-800000035b85, data:{'temp': [{'28-800000035b85': 23.2}, {'28-800000035de5': 24.3}, {'28-031500c05bff': 23.9}]}

   		# updateOneWire: NNN:{'28-800000035b85': 23.2}
		# updateOneWire: serialNumber:28-800000035b85
		# updateOneWire:  if (1) ok

		# updateOneWire: NNN:{'28-800000035de5': 24.3}
		# updateOneWire: serialNumber:28-800000035de5
		# updateOneWire:  else (2) 
		# updateOneWire:  else (2) : foundSelf

		# updateOneWire: NNN:{'28-031500c05bff': 23.9}
		# updateOneWire: serialNumber:28-031500c05bff
		# updateOneWire:  else (2) 
		# updateOneWire:  else (2) : foundSelf
 
		doPrint = False
		try:
			if doPrint: self.indiLOG.log(20,"updateOneWire: dev:{}, data:{}".format(dev.name, data))
			busMaster = data.get("busMaster","")
			gpioUsed = data.get("gpioUsed","")
			for NNN in data["temp"]:
				if not isinstance(NNN, type({})):
					continue ## old format , skip ; must be list
				if doPrint: self.indiLOG.log(20,"updateOneWire: NNN:{}".format(NNN))
				for serialNumber in NNN:
					temp = NNN[serialNumber]
					if temp == 85.0:	continue  # this is not a valid data point. sensor in boot process,  this should not happen at all
					x, UI, decimalPlaces, useFormat  = self.convTemp(temp)
					if x > 500. or x < -500.:
						x = "bad data"
						UI = "bad data"
						decimalPlaces = ""
					if doPrint: self.indiLOG.log(20,"updateOneWire: serialNumber:{}".format(serialNumber))
					if dev.states["serialNumber"] == "" or dev.states["serialNumber"] == serialNumber: # =="" new, ==Serial# already setup
						if doPrint: self.indiLOG.log(20,"updateOneWire:  if (1) ok")
						if dev.states["serialNumber"] == "":
							self.addToStatesUpdateDict(dev.id, "serialNumber",serialNumber)

							self.setONErPiV(piU, "piUpToDate", ["updateParamsFTP"])
						self.setStatusCol( dev, "Temperature", x, UI, whichKeysToDisplay, indigo.kStateImageSel.TemperatureSensorOn,dev.states["status"], decimalPlaces = decimalPlaces )

						if busMaster != "":
							self.addToStatesUpdateDict(dev.id, "busMaster", busMaster)
						if gpioUsed != "":
							self.addToStatesUpdateDict(dev.id, "gpioUsed", gpioUsed)

					else: # try to somewhere else
						#indigo.server.log("  not present, checking other " )
						if doPrint: self.indiLOG.log(20,"updateOneWire:  else (2) ")
						foundSelf	= False
						for dev0 in indigo.devices.iter("props.isSensorDevice"):
							if dev0.deviceTypeId != "Wire18B20": continue
							if dev0.name == dev.name: continue
							if dev0.states["serialNumber"] == serialNumber:
								if doPrint: self.indiLOG.log(20,"updateOneWire:  else (2) : found dev:{}, dev.id".format(dev0.name, dev.id))
								#indigo.server.log("  found serial number " +dev0.name +"  "+ serialNumber	)
								foundSelf = True
								self.setStatusCol( dev0, "Temperature", x, UI, whichKeysToDisplay, indigo.kStateImageSel.TemperatureSensorOn,dev0.states["status"],decimalPlaces = decimalPlaces )
								if serialNumber != "sN= " + dev0.description:
									dev0.description = "sN= " + serialNumber
									dev0.replaceOnServer()
								break
						if doPrint: self.indiLOG.log(20,"updateOneWire:  else (2) : foundSelf:{}".format(foundSelf))
						if not foundSelf : # really not setup
							try:
								props = indigo.devices[int(self.RPI[piU]["piDevId"])].pluginProps
								if props.get("oneWireAddNewSensors","0") == "1":
									self.indiLOG.log(20,"updateOneWire:  create new dev".format())
									dev1 = indigo.device.create(
											protocol		= indigo.kProtocol.Plugin,
											address			= "Pi-"+piU,
											name			= dev.name+"_"+serialNumber,
											pluginId		= self.pluginId,
											deviceTypeId	= "Wire18B20",
											folder			= self.piFolderId,
											description		= "sN= " + serialNumber,
											props			= {"piServerNumber":piU, "displayState":"status", "displayS":"Temperature", "offsetTemp":"0", "displayEnable": "0", "isSensorDevice":True,
																"SupportsSensorValue":True, "SupportsOnState":False, "AllowSensorValueChange":False, "AllowOnStateChange":False, "SupportsStatusRequest":False}
											)
									dev1 = indigo.devices[dev1.id]

									if "input"	   not in self.RPI[piU]			 : self.RPI[piU]["input"] ={}
									if "Wire18B20" not in self.RPI[piU]["input"] : self.RPI[piU]["input"]["Wire18B20"] ={}
									self.RPI[piU]["input"]["Wire18B20"]["{}".format(dev1.id)] = ""
									self.addToStatesUpdateDict(dev.id, "busMaster",busMaster)
									self.addToStatesUpdateDict("{}".format(dev1.id), "serialNumber",serialNumber)
									self.setStatusCol( dev1, "Temperature", x, UI, whichKeysToDisplay, indigo.kStateImageSel.TemperatureSensorOn,dev1.states["status"], decimalPlaces = decimalPlaces )
									props = dev1.pluginProps
									self.addToStatesUpdateDict(dev.id, "groupMember","SENSOR" )
									self.executeUpdateStatesDict(onlyDevID= "{}".format(dev1.id), calledFrom="updateOneWire")
									self.setONErPiV(piU, "piUpToDate", ["updateParamsFTP"])
									self.saveConfig(calledFrom="oneWire")
								else:
									self.indiLOG.log(20,"updateOneWire:   do not create new device not enabled for sn:{}".format(serialNumber))

							except Exception as e:
								self.exceptionHandler(40, e)
								continue

		except Exception as e:
			self.exceptionHandler(40, e)



####-------------------------------------------------------------------------####
	def updateBLEmyBLUEt(self, dev, data, props, whichKeysToDisplay):
		try:
			x, UI, decimalPlaces, useFormat  = self.convTemp(data["temp"])
			self.setStatusCol( dev, "Temperature", x, UI, whichKeysToDisplay, indigo.kStateImageSel.TemperatureSensorOn,dev.states["status"], decimalPlaces = decimalPlaces )

		except Exception as e:
			self.exceptionHandler(40, e)



####-------------------------------------------------------------------------####
	def updatePULSE(self, dev, data, whichKeysToDisplay):
		if self.decideMyLog("SensorData"): self.indiLOG.log(5,"updatePULSE {}".format(data))
		props = dev.pluginProps
		try:
			if "time" in data:	timeStamp = data["time"]
			else:				timeStamp = time.time()
			now = datetime.datetime.fromtimestamp(timeStamp)
			dd = now.strftime(_defaultDateStampFormat)
			defCountList = {"lastReset":0, "timeLastwData":0, "timePreviouswData":0.,"data": [{"time":0., "count":0}]} # is list of [[time0 ,count0], [time1 ,count1],...]  last counts up to 3600 secs,  then pop out last

			countList = defCountList
			if "countList" in props:
				try:
					countList = json.loads(props["countList"])
					if "lastReset" not in countList:
						countList = defCountList
				except:	countList = defCountList

			if time.time() - countList["lastReset"] < 3:
				if self.decideMyLog("SensorData"): self.indiLOG.log(10,"updatePULSE ignore new data after reset")
				# ignore new data after last reset if too close, get reset from plugin, and then also from RPI
				return


			if "count" in data:
				try: 	cOld = int(dev.states["count"])
				except: cOld = 0

				## is there a count reset?, if yes remove old counts
				ll = len(countList)
				if ll > 0:
					if  data["count"] < 0:
						if self.decideMyLog("SensorData"): self.indiLOG.log(10,"updatePULSE resetting countList, requested from menu")
						data["count"] = 0
						countList = defCountList
						cOld = 0
						countList["lastReset"] = time.time()

					elif data["count"] <  cOld:
						if self.decideMyLog("SensorData"): self.indiLOG.log(10,"updatePULSE resetting countList, new count < stored count")
						countList = defCountList
						cOld = 0
						countList["lastReset"] = time.time()

				countList["data"].append({"time": timeStamp, "count": data["count"]})

				#if self.decideMyLog("Special"): self.indiLOG.log(10,"updatePULSE  countList:{}".format(countList)  )

				ll = len(countList["data"])
				if len(countList["data"]) >2:
					dT =  max( countList["data"][-1]["time"] - countList["data"][-2]["time"],1.)
				else:
					countPerSecond = 0.

				## remove not used data
				ll = len(countList["data"])
				if ll > 2:
					for ii in range(ll):
						if len(countList["data"]) <=2: break
						if countList["data"][0]["count"] >  countList["data"][-1]["count"]: countList["data"].pop(0)# remove data if less than last entry
						else: break

				ll = len(countList["data"])
				if ll > 2:
					for ii in range(ll):
						if len(countList["data"]) <= 2: break
						if countList["data"][0]["time"] < countList["data"][-1]["time"] - 3600*24: countList["data"].pop(0) # ? older than 24 hours?, yes remove
						else: 				    break
				ll = len(countList["data"])

				minPointer  				= ll -1
				hourPointer 				= ll -1
				countPerSecondMaxLastHour	= 0


				if ll > 1:
					for ii in range(1,ll):
						if countList["data"][ll-ii]["time"] == 0: continue
					# 	find last hour entry
						pp = max(0,ll-ii -1)
						dT = countList["data"][-1]["time"] - countList["data"][ll-ii]["time"]

						if  dT <= 3600:
							hourPointer = pp
							countPerSecondMaxLastHour = max(countPerSecondMaxLastHour,  max(0,(countList["data"][pp+1]["count"] - countList["data"][pp]["count"]) / max( countList["data"][pp+1]["time"] - countList["data"][pp]["time"],1.)) )

							# find last minute entry
							if dT <= 60:
								minPointer = pp # use previous

						else: #
							break

				#if self.decideMyLog("Special"):  self.indiLOG.log(10,"updatePULSE cOld:{}; count:{}; timeLastwData:{} timePreviouswData:{}; countList[data][-3:]:{}".format(cOld, countList["data"][-1]["count"], countList["timeLastwData"], countList["timePreviouswData"], countList["data"][-3:])  )
				if countList["data"][0]["time"] == 0:
					countList["timeLastwData"] 	= timeStamp
					self.setStatusCol( dev, "count", countList["data"][-1]["count"], 			"{:.0f}[c]".format(countList["data"][-1]["count"]), whichKeysToDisplay, "","", decimalPlaces = "" )

				elif cOld - countList["data"][-1]["count"] != 0:
					countList["timePreviouswData"]	= countList["timeLastwData"]
					countList["timeLastwData"] 	= timeStamp
					countTimePrevious				= max(1., timeStamp - countList["timePreviouswData"])
					countPrevious 					= cOld

					self.addToStatesUpdateDict(dev.id, "countTimePrevious", 	-round(countTimePrevious,1) )
					self.addToStatesUpdateDict(dev.id, "countPrevious", 		int(countPrevious))
					self.addToStatesUpdateDict(dev.id, "countTime",  			time.strftime(_defaultDateStampFormat, time.localtime(timeStamp)) )
					self.setStatusCol( dev, "count", countList["data"][-1]["count"], 			"{:.0f}[c]".format(countList["data"][-1]["count"]), whichKeysToDisplay, "","", decimalPlaces = "" )

				else:
					countList["timePreviouswData"]	= countList["timeLastwData"]
					countTimePrevious				= max(1., timeStamp - countList["timePreviouswData"])
					countPrevious 					= dev.states["countPrevious"]

				#if self.decideMyLog("Special"): self.indiLOG.log(10,"updatePULSE                timeLastwData:{} timePreviouswData:{}; countList[data][-3:]:{}".format(countList["timeLastwData"], countList["timePreviouswData"], countList["data"][-3:]) )

				if cOld <= data["count"] and countList["data"][0]["time"] > 0:
					dtSecs = max(1, countList["data"][-1]["time"] 		 	 - countList["data"][-2]["time"])
					countPerSecond 		= round(float(countList["data"][-1]["count"] - cOld)			/ dtSecs,       	2)
					countPerSecSmooth	= round(float(countList["data"][-1]["count"] - countPrevious)	/ countTimePrevious,2)
					#self.indiLOG.log(10,"updatePULSE                count:{} cprev:{}; countTimePrevious:{}; countPerSecSmooth:{}".format(countList["data"][-1]["count"], countPrevious, countTimePrevious, countPerSecSmooth ))


					countPerMinute 		=   60.        * ( countList["data"][-1]["count"] - countList["data"][minPointer]["count"]  ) /  max(1., ( countList["data"][-1]["time"] - countList["data"][minPointer]["time"]) )
					countPerHour   		= int(3600.    * ( countList["data"][-1]["count"] - countList["data"][hourPointer]["count"] ) /  max(1., ( countList["data"][-1]["time"] - countList["data"][hourPointer]["time"]) ))
					countPerDay    		= int(3600.*24 * ( countList["data"][-1]["count"] - countList["data"][0]["count"]            ) /  max(1., ( countList["data"][-1]["time"] - countList["data"][0]["time"]) ))


					scaleFactorForMinuteCount = 0
					try: 	scaleFactorForMinuteCount = float(eval(props["scaleFactorForMinuteCount"]))
					except: scaleFactorForMinuteCount = 1.
					scfm = scaleFactorForMinuteCount * countPerMinute

					try: 	significantDigits = int(props["significantDigits"])
					except: significantDigits = 3
					countPerMinuteDP			= self.getNumberOfdecPoints(countPerMinute,				significantDigits=significantDigits)
					countPerHourDP				= self.getNumberOfdecPoints(countPerHour,				significantDigits=significantDigits)
					countPerDayDP				= self.getNumberOfdecPoints(countPerDay,				significantDigits=significantDigits)
					scfmDP						= self.getNumberOfdecPoints(scfm,						significantDigits=significantDigits)
					countPerSecondDP			= self.getNumberOfdecPoints(countPerSecond,				significantDigits=significantDigits)
					countPerSecSmoothDP			= self.getNumberOfdecPoints(countPerSecSmooth,			significantDigits=significantDigits)
					countPerSecondMaxLastHourDP	= self.getNumberOfdecPoints(countPerSecondMaxLastHour,	significantDigits=significantDigits)


					if "scaleFactorForMinuteCountUnit" in props and len(props["scaleFactorForMinuteCountUnit"]) < 2:
																		scaleFactorForMinuteCountUnit = "{:.1f}[c/m*{}]".format(scfm, props["scaleFactorForMinuteCount"])
					else:												scaleFactorForMinuteCountUnit = props["scaleFactorForMinuteCountUnit"].format(scfm)

					self.setStatusCol( dev, "countPerMinuteScaled",		scfm,						scaleFactorForMinuteCountUnit,														whichKeysToDisplay, "","", decimalPlaces = scfmDP )
					self.setStatusCol( dev, "countPerSecSmooth",			countPerSecSmooth, 			"{}[c/s]".format(round(countPerSecSmooth,countPerSecSmoothDP)), 					whichKeysToDisplay, "","", decimalPlaces = countPerSecSmoothDP )
					self.setStatusCol( dev, "countPerSecond",				countPerSecond, 			"{}[c/s]".format(round(countPerSecond,countPerSecondDP)), 							whichKeysToDisplay, "","", decimalPlaces = countPerSecondDP )
					self.setStatusCol( dev, "countPerSecondMaxLastHour",	countPerSecondMaxLastHour,	"{}[c/s]".format(round(countPerSecondMaxLastHour,countPerSecondMaxLastHourDP)),	whichKeysToDisplay, "","", decimalPlaces = countPerSecondMaxLastHourDP )
					self.setStatusCol( dev, "countPerMinute",				countPerMinute, 			"{}[c/m]".format(round(countPerMinute,countPerMinuteDP)), 							whichKeysToDisplay, "","", decimalPlaces = countPerMinuteDP )
					self.setStatusCol( dev, "countPerHour",				countPerHour,   			"{}[c/h]".format(round(countPerHour,countPerHourDP)),								whichKeysToDisplay, "","", decimalPlaces = countPerHourDP )
					self.setStatusCol( dev, "countPerDay",    				countPerDay,  	 			"{}[c/d]".format(countPerDay),    													whichKeysToDisplay, "","", decimalPlaces = countPerDayDP )



			#if self.decideMyLog("Special"): self.indiLOG.log(10,"updatePULSE  writing to props: countList:{}".format(countList)  )
			props["countList"] = json.dumps(countList)
			
			dev.replacePluginPropsOnServer(props)

			if "burst" in data and data["burst"] !=0 and data["burst"] !="":
					self.addToStatesUpdateDict(dev.id, "lastBurstTime", dd )

			if "continuous" in data and data["continuous"] !="":
					if data["continuous"] > 0:
						self.addToStatesUpdateDict(dev.id, "lastContinuousEventTime", dd )
						self.addToStatesUpdateDict(dev.id, "lastContinuousEventStopTime","")
					else:
						if dev.states["lastContinuousEventStopTime"] == "":
							self.addToStatesUpdateDict(dev.id, "lastContinuousEventStopTime", dd)
			#if self.decideMyLog("Special"): self.indiLOG.log(5,"updatePULSE  ll-1:{}, minPointer:{}, cpm:{}, dc:{}, dt:{},  cps:{}\n     data:{}\n cllistmin:{},".format( ll-1, minPointer, countPerMinute, countList[-1]["count"] - countList[minPointer]["count"], countList[-1]["time"] - countList[minPointer]["time"] ,  countPerSecond,  data, countList[minPointer] ))

		except Exception as e:
			self.exceptionHandler(40, e)
		return

####-------------------------------------------------------------------------####
	def getNumberOfdecPoints(self, value, significantDigits=3):
		decPoint = 1
		try:
			if value == 0: return decPoint
			x = int(math.log10(abs(value)))
			decPoints = max(0,min(7, significantDigits - x))
		except Exception as e:
			self.exceptionHandler(40, e)
		return decPoints

####-------------------------------------------------------------------------####
####-------------------------------------------------------------------------####



####-------------------------------------------------------------------------####
## this will update the states xxxChangeXXMinutes / Hours eg TemperatureChange10Minutes TemperatureChange1Hour TemperatureChange6Hour
## has problems when there are no updates, values can be  stale over days
	def updateChangedValuesInLastXXMinutes(self,dev, value, stateToUpdate, decimalPlaces):
		try:
			if stateToUpdate not in dev.states:
				self.indiLOG.log(10,"updateChangedValuesInLastXXMinutes: {}, state {}   not defined".format(dev.name, stateToUpdate))
				return 

			#self.indiLOG.log(20,"updateChangedValuesInLastXXMinutes: {}, state {}, updateListStates:{}".format(dev.name, stateToUpdate, dev.pluginProps.get("isMememberOfChangedValues","")))
			if stateToUpdate not in dev.pluginProps.get("isMememberOfChangedValues","").split(","): 
				return 

			doPrint = False

			updateList = []

			devIdS = str(dev.id)

			# create the measurement time stamps in minutes
			for state in dev.states:
				## state  eg =  "temperatureChange1Hour"
				if state.find(stateToUpdate+"Change") == 0:
					if state.find(".ui") > 8: continue
					if state.find("_ui") > 8: continue
					upU = state.split("Change")[1]
					if len(upU) < 2: continue
					if upU.find("Hours") > -1:     updateN = "Hours";   updateMinutes = 3600
					elif upU.find("Minutes") > -1: updateN = "Minutes"; updateMinutes = 60
					else: continue
					amount = int(upU.split(updateN)[1])
					updateList.append( {"state":state, "unit":updateN, "deltaSecs":updateMinutes * amount, "pointer":0, "changed":0} )

			if len(updateList) < 1: 
				#self.indiLOG.log(10,"updateChangedValuesInLastXXMinutes:{},  state:{}Changexx value:{} \nnot in states: {}".format(dev.name, stateToUpdate, value, dev.states))
				return

			## get last list
			if devIdS not in self.changedValues:
				self.changedValues[devIdS] = {}



			updateList = sorted(updateList, key = lambda x: x["deltaSecs"])
			if doPrint: self.indiLOG.log(20,"{}: {}, = {}  updateList:{},  ".format(dev.name, stateToUpdate, value, updateList))
			#if doPrint: self.indiLOG.log(20,"{}: start changedValues:{},  ".format(dev.name, self.changedValues[devIdS][stateToUpdate+"list"]))


			if stateToUpdate+"list" in self.changedValues[devIdS]:
				valueList = self.changedValues[devIdS][stateToUpdate+"list"]
			else:
				valueList = [(0,0),(0,0)]


			try: decimalPlaces = int(decimalPlaces)
			except: 
				self.indiLOG.log(20,"updateChangedValuesInLastXXMinutes dev{}: bad decimalPlaces {}: type:{}  must be >=0 and integer ".format(dev.name, decimalPlaces, type(decimalPlaces)))
				return

			if decimalPlaces == 0: 
				valueList.append([int(time.time()),int(value)])
			elif decimalPlaces > 0: 
				valueList.append([int(time.time()), round(value,decimalPlaces)])
			else:  
				self.indiLOG.log(20,"updateChangedValuesInLastXXMinutes dev{}: bad decimalPlaces {}: type:{}  must be >=0 and integer ".format(dev.name, decimalPlaces, type(decimalPlaces)))
				return

			jj 		= len(updateList)
			cutMax	= updateList[-1]["deltaSecs"] # this is for 172800 secs = 48 hours
			ll		= len(valueList)
			for ii in range(ll):
				if len(valueList) <= 2: break
				if (valueList[-1][0] - valueList[0][0]) > cutMax: valueList.pop(0)
				else: 				    break


			ll = len(valueList)
			if ll > 1:
				for kk in range(jj):
					cut = updateList[kk]["deltaSecs"] # = 5 min = 300, 10 min = 600, 20 min=1200, 1 hour = 3600 ... 48hours = 172800 secs
					updateList[kk]["pointer"] = 0
					if cut != cutMax: # we can skip the largest, must be first and last entry
						for ii in range(ll-1,-1,-1):
							if (valueList[-1][0] - valueList[ii][0]) <= cut:
								updateList[kk]["pointer"] = ii
							else:
								break

					if decimalPlaces == "":
						changed			 = round(( valueList[-1][1] - valueList[updateList[kk]["pointer"]][1] ))
					elif decimalPlaces == 0:
						changed			 = int(valueList[-1][1] - valueList[updateList[kk]["pointer"]][1] )
					else:
						changed			 = round(( valueList[-1][1] - valueList[updateList[kk]["pointer"]][1] ), decimalPlaces)

					self.addToStatesUpdateDict(dev.id, updateList[kk]["state"], changed, decimalPlaces=decimalPlaces, force=False)
					if doPrint: self.indiLOG.log(20,"{}:  updateList:{}, changed:{}, dec:{} ".format(dev.name, updateList[kk]["state"], changed, decimalPlaces))

			self.changedValues[devIdS][stateToUpdate+"list"] = valueList

			return 

		except Exception as e:
			self.exceptionHandler(40, e)
		return 


####-------------------------------------------------------------------------####
	def updateTEA5767(self,sensors,sensor):
		if self.decideMyLog("OutputDevice"): self.indiLOG.log(5,sensor+"     {}".format(sensors))
		for devId in sensors:
			try:
				dev = indigo.devices[int(devId)]
				iii = 0
				for channels in sensors[devId]["channels"]:
					self.indiLOG.log(10,"updateTEA5767 sensor: "+sensor+"  {}".format(channels))
					freq   = channels["freq"]
					Signal = channels["Signal"]
					ch = "Channel-{:02d}".format(iii)
					self.addToStatesUpdateDict(devId,ch,"f={}".format(freq)+"; Sig={}".format(Signal))
					iii+=1
				for ii in range(iii,41):
					ch = "Channel-{:02d}".format(ii)
					self.addToStatesUpdateDict(devId,ch,"")
			except Exception as e:
				if "{}".format(e) != "None":
					self.exceptionHandler(40, e)
		return

####-------------------------------------------------------------------------####
	def updateGetBeaconParameters(self, pi, data):
## 		format:		data["sensors"]["getBeaconParameters"][mac] = {state:{value}}}

		try:
			if self.decideMyLog("BatteryLevel"): self.indiLOG.log(10,"GetBeaconParameters update received  pi#:{};  data:{}".format(pi, data) )
			for beacon in data:
				if beacon in self.beacons:
					indigoId = int(self.beacons[beacon]["indigoId"])
					if indigoId > 0:
						if not self.beacons[beacon]["enabled"]: continue
						dev = indigo.devices[int(indigoId)]
						props = dev.pluginProps
						try: 	lastUpdateBatteryLevel = time.mktime(time.strptime(dev.states["lastUpdateBatteryLevel"], _defaultDateStampFormat ))
						except: lastUpdateBatteryLevel = time.mktime(time.strptime("2000-01-01 00:00:00", _defaultDateStampFormat ))
						for state in data[beacon]:

							if state == "batteryLevel"  and "batteryLevel" in dev.states and "lastUpdateBatteryLevel" in dev.states:
								# this with an integer data payload = battery level
								if type(data[beacon][state]) == type(1):
									if  data[beacon][state] > 0:
										if self.decideMyLog("BatteryLevel"): self.indiLOG.log(10,"GetBeaconParameters updating state:{} with:{}".format(state, data[beacon][state]) )
										self.addToStatesUpdateDict(indigoId, state, data[beacon][state])
										self.addToStatesUpdateDict(indigoId, "lastUpdateBatteryLevel", datetime.datetime.now().strftime(_defaultDateStampFormat))
										self.setlastBatteryReplaced(dev, data[beacon][state])
									else:
										if time.time() - lastUpdateBatteryLevel > 24*3600: self.indiLOG.log(10,"GetBeaconParameters update received pi:{} beacon:{} .. {};  bad data read; last good update was {}, current batterylevel status: {}".format(pi,beacon, data[beacon], dev.states["lastUpdateBatteryLevel"], dev.states["batteryLevel"]  ) )

								# this with a text payload, error message
								else:
									if len(dev.states["lastUpdateBatteryLevel"] ) < 10:
										self.addToStatesUpdateDict(indigoId, "lastUpdateBatteryLevel", "2000-01-01 00:00:00")
									if time.time() - lastUpdateBatteryLevel > 24*3600: self.indiLOG.log(10,"GetBeaconParameters update received pi:{}  beacon:{} .. error msg: {}; last update was {}, current batterylevel status: {}".format(pi,beacon, data[beacon][state], dev.states["lastUpdateBatteryLevel"], dev.states["batteryLevel"] ) )
							else:
								if time.time() - lastUpdateBatteryLevel > 24*3600: self.indiLOG.log(10,"GetBeaconParameters update received pi:{} beacon:{},  wrong beacon device.. error msg: {}".format(pi, beacon, data[beacon][state] ) )
					else:
						self.indiLOG.log(10,"GetBeaconParameters update received pi:{} beacon:{},  no indigo device present, data:{}".format(pi, beacon, data ) )

		except Exception as e:
			self.exceptionHandler(40, e)

####-------------------------------------------------------------------------####
	def updateINPUT(self, dev, data, upState, nInputs, sensor):
		# {"pi_IN_":"0","sensors":{"spiMCP3008":{"INPUT_6":3,"INPUT_7":9,"INPUT_4":0,"INPUT_5":0,"INPUT_2":19,"INPUT_3":534,"INPUT_0":3296,"INPUT_1":3296}}}
		#									 {'INPUT_6': 0, 'INPUT_7': 0, 'INPUT_4': 0, 'INPUT_5': 0, 'INPUT_2': 0, 'INPUT_3': 518, 'INPUT_0': 3296, 'INPUT_1': 3296}
		try:
			props = dev.pluginProps
			if "addToInputName" in props:
				try:   addToInputName = int(props["addToInputName"])
				except:addToInputName = 0
			else:	   addToInputName = 0

			try:
				upS = int(upState)
				upState = "INPUT_{}".format(upS)
			except:pass
			decimalPlaces = 0

			for ii in range(max(1,nInputs)):
				INPUT_raw = False

				if nInputs >10:
						inputState = "INPUT_{:02d}" .format(ii+addToInputName)
				elif nInputs == 1 and  "INPUT" in dev.states:
						inputState = "INPUT"
						upState	   = "INPUT"
				elif nInputs == 0 and  "INPUT" in dev.states:
						inputState = "INPUT"
						if "INPUT_raw" in dev.states:
							INPUT_raw = True
				else:	inputState = "INPUT_{}".format(ii+addToInputName)


				if self.decideMyLog("SensorData"): self.indiLOG.log(10,"updateINPUT: {};  sensor: {};  upState: {}; inputState: {};  data: {}".format(dev.name, sensor, upState, inputState, data) )
				if inputState in data:
					if INPUT_raw: 	 self.addToStatesUpdateDict(dev.id, "INPUT_raw", data[inputState])
					ss, ssUI, unit = self.addmultOffsetUnit(data[inputState], props)
					if dev.states[inputState] != ss:
						self.addToStatesUpdateDict(dev.id,inputState, ss)
						### minmax if deice.xml has that field
						decimalPlaces = 1
						v = ss
						if upState == inputState:
							try:
								v = float(self.getNumber(ssUI))
								dp = "{}".format(v).split(".")
								if len(dp)   == 0:	decimalPlaces = 0
								elif len(dp) == 2:	decimalPlaces = len(dp[1])
							except: pass

						if INPUT_raw: ss = v

						if inputState+"MaxYesterday" in dev.states:
							self.fillMinMaxSensors(dev,inputState,v,decimalPlaces=decimalPlaces)

						if upState == inputState:
							if not self.setStateColor(dev,props,ss):
								fs = self.getNumber(ss)
								if ss == "1" or ss == "up" or (fs != 0. and fs != "x"):
									on = True; image = "SensorOn"
								else:
									on = False; image = "SensorOff"

							if "onOffState" in dev.states:
								delayOff = float(props.get("delayOff", "0"))
								# check if we want to keep the state = "ON" for some time instead of immediately going "off" if off received
								# added delayed action of adding setting to off IF currently on and delay is set 
								if not on and delayOff > 0 and dev.states["onOffState"]:
									self.delayedActions["data"].put( {"actionTime":time.time()+delayOff, "devId":dev.id, "updateItems":[{"stateName":"onOffState", "value":False, "uiValue":ssUI, "image":image}]})

								else:
									self.addToStatesUpdateDict(dev.id, "onOffState", on, uiValue=ssUI)
									if dev.states["status"] != ssUI + unit:
										self.addToStatesUpdateDict(dev.id, "status", ssUI)

									if on:	self.setIcon(dev,props, "SensorOff-SensorOn",1)
									else:	self.setIcon(dev,props, "SensorOff-SensorOn",0)


							if "sensorValue" in dev.states:
								if self.decideMyLog("SensorData"): self.indiLOG.log(20,"{};  sensor:{};  sensorValue".format(dev.name, sensor) )
								self.setStatusCol(dev, upState, ss, ssUI + unit, upState, "","", decimalPlaces = decimalPlaces)
							else:
								if dev.states["status"] != ssUI + unit:
									self.addToStatesUpdateDict(dev.id, "status", ssUI+unit)

		except Exception as e:
			self.exceptionHandler(40, e)

####-------------------------------------------------------------------------####
	def setStateColor(self, dev, props, ss):
		try:
			if not("stateGreen" in props and "stateGrey" in props and "stateRed" in props): return False
			try:
				commands = {"green":props["stateGreen"], "grey":props["stateGrey"], "red":props["stateRed"]}
				ok = False
				for cmd in commands:
					if len(commands[cmd]) > 0: ok = True
				if commands["green"] == commands["grey"] and commands["grey"] == commands["red"]: return False
			except: return False
			if not ok: return False

			x = self.getNumber(ss)
			#if self.decideMyLog("Special"):self.indiLOG.log(10,"setStateColor for dev {}, x={};  eval syntax: {}".format(dev.name, x, commands) )
			for col in ["green", "grey", "red"]:
				try:
					if len(commands[col]) == 0: continue
					if eval(commands[col]) :
						if col == "green": dev.updateStateImageOnServer(indigo.kStateImageSel.SensorOn)
						if col == "grey": dev.updateStateImageOnServer(indigo.kStateImageSel.SensorOff)
						if col == "red": dev.updateStateImageOnServer(indigo.kStateImageSel.SensorTripped)
						return True
				except:
					if commands[col].find("x") ==-1:
						self.indiLOG.log(10,"setStateColor for dev {}, x={};  color: {};  wrong eval syntax: {};  x=  x> ... statement part missing, eg x>25; not just >25".format(dev.name, x, col, commands[col]) )
					else:
						self.indiLOG.log(10,"setStateColor for dev {}, x={};  color: {};  wrong eval syntax: {}".format(dev.name, x, col, commands[col]) )



		except Exception as e:
			self.exceptionHandler(40, e)
		return False


####-------------------------------------------------------------------------####
	def setIcon(self, dev, iconProps, default, UPdown):
		try:
			if "iconPair" in iconProps and	iconProps ["iconPair"] !="":
				icon = iconProps ["iconPair"].split("-")[UPdown]
			else:
				icon = default.split("-")[UPdown]
			try:
				dev.updateStateImageOnServer(getattr(indigo.kStateImageSel, icon, None))
			except Exception as e:
				if UPdown ==0:					 dev.updateStateImageOnServer(indigo.kStateImageSel.SensorOff)
				else:							 dev.updateStateImageOnServer(indigo.kStateImageSel.SensorOn)
		except Exception as e:
			if self.decideMyLog("SensorData"): self.exceptionHandler(40, e)
			return



####-------------------------------------------------------------------------####
	def updateapds9960(self, dev, data):
		try:
			props = dev.pluginProps
			input = "gesture"
			if input in data:
				if "{}".format(data[input]).find("bad") >-1:
					self.addToStatesUpdateDict(dev.id, "status", "no sensor data - disconnected?")
					self.setIcon(dev,props, "SensorOff-SensorOn",0)
					return
				else:
					if data[input] !="NONE":
						if props["displayS"] == input:
							self.addToStatesUpdateDict(dev.id, "status", data[input])
						self.addToStatesUpdateDict(dev.id,input,data[input])
						self.addToStatesUpdateDict(dev.id,input+"Date",datetime.datetime.now().strftime(_defaultDateStampFormat))
						self.setIcon(dev,props, "SensorOff-SensorOn",1)


			input = "gestureData"
			if input in data:
					if data[input] !="":
						if props["displayS"] == input:
							self.addToStatesUpdateDict(dev.id, "status", data[input])
						self.addToStatesUpdateDict(dev.id,input,data[input])
						self.setIcon(dev,props, "SensorOff-SensorOn",1)

			input = "distance"
			if input in data:
				if "{}".format(data[input]).find("bad") >-1:
					self.addToStatesUpdateDict(dev.id, "status", "no sensor data - disconnected?")
					self.setIcon(dev,props, "SensorOff-SensorOn",0)
				else:
					if data[input] !="NONE":
						if props["displayS"] == input:
							self.addToStatesUpdateDict(dev.id, "status", data[input])
						self.addToStatesUpdateDict(dev.id,input,data[input])
						self.addToStatesUpdateDict(dev.id,input+"Date",datetime.datetime.now().strftime(_defaultDateStampFormat))
						self.setIcon(dev,props, "SensorOff-SensorOn",1)

			input = "proximity"
			if input in data:
				if "{}".format(data[input]).find("bad") >-1:
					self.addToStatesUpdateDict(dev.id, "status", "no sensor data - disconnected?")
					self.setIcon(dev,props, "SensorOff-SensorOn",0)
				else:
						if props["displayS"] == input:
							self.addToStatesUpdateDict(dev.id, "status", data[input])
						self.addToStatesUpdateDict(dev.id,input,data[input])
						self.addToStatesUpdateDict(dev.id,input+"Date",datetime.datetime.now().strftime(_defaultDateStampFormat))
						self.setIcon(dev,props, "SensorOff-SensorOn",1)

			self.updateRGB(dev, props, data, props["displayS"])

		except Exception as e:
			if self.decideMyLog("SensorData"): self.exceptionHandler(40, e)



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
				for input in ["Current{}".format(jj), "ShuntVoltage{}".format(jj), "BusVoltage{}".format(jj)]:
					if input in data:
						if "{}".format(data[input]).find("bad") >-1:
							self.setStatusCol( dev, input, 0, "no sensor data - disconnected?", "Current{}".format(jj), "","" )
							self.setIcon(dev,props, "SensorOff-SensorOn",0)
							return
						if data[input] !="":
							ss, ssUI, unit = self.addmultOffsetUnit(data[input], dev.pluginProps)
							self.setStatusCol( dev, input, ss, ssUI+unit, whichKeysToDisplay, "","" )
				self.setIcon(dev,props, "SensorOff-SensorOn",1)
		except Exception as e:
			if self.decideMyLog("SensorData"): self.exceptionHandler(40, e)

####-------------------------------------------------------------------------####
	def updateADC121(self,dev,data,whichKeysToDisplay):
		try:
			input = "adc"
			props = dev.pluginProps
			xType = props["type"]
			pp = {"offset": props["offset"], "mult":props["mult"], "unit": "ppm", "format":"%2d"}

			if "{}".format(data[input]).find("bad") >-1:
					self.addToStatesUpdateDict(dev.id, "status", "no sensor data - disconnected?")
					self.setIcon(dev,props, "SensorOff-SensorOn",0)
					return

			self.setIcon(dev,props, "SensorOff-SensorOn",1)
			if input in data:
					if data[input] != "":
						ADC = data[input]
						MaxBits = 4095.	  # 12 bits
						Vcc		= 5000.	  # mVolt max

						if	 xType.find("MQ") > -1:
							try:	Vca		= float(dev.props["Vca"] )	  # mVolt  at clean Air / calibration
							except: Vca		= 3710.

						if	xType =="MQ7": #CO
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

						elif   xType =="MQ9": # CO
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

						elif   xType =="MQ9-5LPG": # LPG
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

						elif   xType =="MQ9-5CH4": # CH4
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

						elif  xType =="MQ4": # LNG
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


						elif xType =="MQ3-Alcohol": #alcohol
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

						elif xType =="MQ3-Benzene": #alcohol
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

						elif xType =="MQ131": #Ozone
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

						elif xType =="A13XX": # hall effect sensor
							pp["unit"]		="¼"
							pp["format"]	="%.2f"
							val		= (ADC / MaxBits) * 360.0

						elif xType =="TA12_200": # linear current sensor
							pp["unit"]		="mA"
							pp["format"]	="%.1f"
							val		= ADC

						elif xType =="adc": # simple ADC
							pp["unit"]	="mV"
							pp["format"]="%0d"
							val			= ADC *(Vcc/MaxBits)


						ss, ssUI, unit = self.addmultOffsetUnit(val, pp)

						self.setStatusCol( dev, "value", ss, ssUI+unit, whichKeysToDisplay, "","" )
						self.setStatusCol( dev, "adc", ADC, "{}".format(ADC), whichKeysToDisplay,"","" )
		except Exception as e:
			if self.decideMyLog("SensorData"): self.exceptionHandler(40, e)


####-------------------------------------------------------------------------####
	def updateGYROS(self,dev,data,upState):
		try:
			props = dev.pluginProps
			if "{}".format(data).find("bad") >-1:
					self.addToStatesUpdateDict(dev.id, "status", "no sensor data - disconnected?")
					self.setIcon(dev, props, "SensorOff-SensorOn" ,0)
					return
			#self.indiLOG.log(20,"updateGYROS {}  data:{}".format(dev.name, data))
			self.setIcon(dev, props, "SensorOff-SensorOn", 1)
			theList = ["EULER", "QUAT", "MAG", "GYR", "ACC", "LIN", "GRAV", "ROT"]
			XYZSumSQ = 0
			for input in theList:
				if input not in data: continue
				out = ""
				if input =="EULER":
					for dim in ["heading", "pitch", "roll"]:
						if dim not in data[input]: continue
						if data[input][dim] =="":	continue
						ss, ssUI, unit = self.addmultOffsetUnit(data[input][dim], dev.pluginProps)
						out+=ss+","
						self.addToStatesUpdateDict(dev.id,dim,ss)
				else:
					for dim in ["x", "y", "z", "w", "q", "r", "s"]:
						if dim not in data[input]: continue
						if data[input][dim] =="":	continue
						ss, ssUI, unit = self.addmultOffsetUnit(data[input][dim], dev.pluginProps)
						out+=ss+","
						self.addToStatesUpdateDict(dev.id,input+dim,ss)
						if "XYZSumSQ" in dev.states and (input in ["GYR","ACC"]):
							XYZSumSQ +=data[input][dim]*data[input][dim]
				if upState == input:
					self.addToStatesUpdateDict(dev.id, "status", out.strip(","))

				if "XYZSumSQ" in dev.states and (input in ["GYR","ACC"]):
					xys= "{:7.2f}".format(math.sqrt(XYZSumSQ)).strip()
					self.addToStatesUpdateDict(dev.id, "XYZSumSQ",xys)
					if upState == "XYZSumSQ":
						self.addToStatesUpdateDict(dev.id, "status", xys)


			input = "calibration"
			stateName  = "calibration"
			if stateName in dev.states and input in data:
				if data[input] !="":
					out=""
					for dim in data[input]:
						out += dim+":{}".format(data[input][dim])+","
					out= out.strip(",").strip(" ")
					if	upState == input:
						self.addToStatesUpdateDict(dev.id, "status",out)
					self.addToStatesUpdateDict(dev.id,stateName,out)

		except Exception as e:
			self.exceptionHandler(40, e)


####-------------------------------------------------------------------------####
	def updateDistance(self, dev, data, whichKeysToDisplay):
			#{"ultrasoundDistance":{"477759402":{"distance":1700.3591060638428}}
		try:

			input = "distance"
			if input in data:
				if "{}".format(data[input]).find("bad") >-1:
					self.addToStatesUpdateDict(dev.id, "status", "no sensor data - disconnected?")
					self.setIcon(dev,props, "SensorOff-SensorOn",0)
					return

				props = dev.pluginProps
				units = "cm"
				dist0 = 1.
				offset= 0.
				multiply=1.
				if	   "dUnits" in props: units  = props["dUnits"]
				try:
					if "offset" in props: offset = float(props["offset"])
				except: pass

				try:
					if "multiply" in props:
						mm = float(props["multiply"])
						if mm != 0: multiply=mm
				except: pass

				raw = round(float(data[input]),2)
				if "distanceRaw" in dev.states: self.addToStatesUpdateDict(dev.id, "distanceRaw", raw)

				if	   "cutMax" in props:
					try:
						raw = min( raw, float(props["cutMax"]))
					except: pass

				if	   "cutMin" in props:
					try:
						raw = max( raw, float(props["cutMin"]))
					except: pass


				distR= (raw+offset)*multiply
				dist = distR
				ud   = "[]"
				if units == "cm":
					ud = " [cm]"
					dist = distR
					dist0 = "{:.1f}{}".format(distR, ud)
				elif units == "m":
					ud = " [m]"
					dist = distR*0.01
					dist0 = "{:.2f}{}".format(dist, ud)
				elif units == "inches":
					ud = ' "'
					dist = distR*0.3937
					dist0 = "{:.1f}{}".format(dist, ud)
				elif units == "feet":
					ud = " '"
					dist = distR*0.03280839895
					dist0 = "{:.2f}{}".format(dist, ud)
				self.setStatusCol(dev, "distance", dist, dist0, whichKeysToDisplay, "","", decimalPlaces = 2)

				if "measuredNumber" in dev.states: self.addToStatesUpdateDict(dev.id, "measuredNumber", raw)

				if "speed" in data:
					try:
						speed = float(data["speed"]) / max(self.speedUnits*100., 0.01)	 # comes in cm/sec
						units = self.speedUnits
						sp = "{}".format(speed)
						ud = "[]"
						if units == 0.01:
							ud = " [cm/s]"
							sp = "{:.1f}".format(speed)
							decimalPlaces = 1
						elif units == 1.0:
							ud = " [m/s]"
							sp = "{:.2f}".format(speed)
							decimalPlaces = 2
						elif units == 0.0254:
							ud = ' [i/s]'
							sp = "{:.1f}".format(speed)
							decimalPlaces = 1
						elif units == 0.348:
							ud = " [f/s]"
							sp = "{:.2f}".format(speed)
							decimalPlaces = 2
						elif units == 0.9144:
							ud = " [y/s]"
							sp = "{:.2f}".format(speed)
							decimalPlaces = 2
						elif units == 3.6:
							ud = " [kmh]"
							sp = "{:.3f}".format(speed)
							decimalPlaces = 2
						elif units == 2.2369356:
							ud = " [mph]"
							sp = "{:.3f}".format(speed)
							decimalPlaces = 2
						self.setStatusCol(dev, "speed", speed, sp+ud, whichKeysToDisplay, "","", decimalPlaces = decimalPlaces)
					except Exception as e:
						self.exceptionHandler(40, e)

				if not self.setStateColor( dev, props, dist):
					if "actionShortDistanceLimit" in props:
						try: cutoff= float(props["actionShortDistanceLimit"])
						except: cutoff= 50
					else:		cutoff= 50
					if dist < cutoff:
							self.setIcon(dev,props, "SensorOff-SensorOn",1)
					else:
							self.setIcon(dev,props, "SensorOff-SensorOn",0)

		except Exception as e:
			self.exceptionHandler(40, e)





####-------------------------------------------------------------------------####
	def getNumber(self,val):
		# test if a val contains a valid number, if not return ""
		# return the number if any meaningful number (with letters before and after return that number)
		# "a-123.5e" returns -123.5
		# -1.3e5 returns -130000.0
		# -1.3e-5 returns -0.000013
		# "1.3e-5" returns -0.000013
		# "1.3e-5x" returns "" ( - sign not first position	 ..need to include)
		# True, "truE" "on" "ON".. returns 1.0;  False "faLse" "off" returns 0.0
		# "1 2 3" returns ""
		# "1.2.3" returns ""
		# "12-5" returns ""
		try:
			return float(val)
		except:
			if val == ""														: return "x"
			try:
				ttt = "{}".format(val).upper()															# if unicode return ""	 (-->except:)
				if ttt== "TRUE"  or ttt == "ON"  or ttt == "T" or ttt== "UP"						: return 1.0	 # true/on	 --> 1
				if ttt== "FALSE" or ttt == "OFF" or ttt == "F" or ttt== "DOWN" or ttt==  "EXPIRED"	: return 0.0		# false/off --> 0
			except:
				pass
			try:
				xx = ''.join([c for c in val if c in  '-1234567890.'])								# remove non numbers
				lenXX= len(xx)
				if	lenXX > 0:																		# found numbers..if len( ''.join([c for cin xx if c in	'.']) )			  >1	: return "x"		# remove strings that have 2 or more dots " 5.5 6.6"
					if len(''.join([c for c in	xx if c in '-']) )			 >1 : return "x"		# remove strings that have 2 or more -	  " 5-5 6-6"
					if len( ''.join([c for c  in xx if c in '1234567890']) ) ==0: return "x"		# remove strings that just no numbers, just . amd - eg "abc.xyz- hij"
					if lenXX ==1												: return float(xx)	# just one number
					if xx.find("-") > 0										: return "x"		 # reject if "-" is not in first position
					valList =  list(val)															# make it a list
					count =	 0																		# count number of numbers
					for i in range(len(val)-1):														# reject -0 1 2.3 4  not consecutive numbers:..
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
			dd = "{}".format(data)
			if "onOff" in props:
				if props["onOff"] == "ON-off":
					if ui ==1.:
						return "1", "off", ""
					else:
						return "0", "ON", ""

				if props["onOff"] == "on-off":
					if ui ==1.:
						return "1", "off", ""
					else:
						return "0", "on", ""

				if props["onOff"] == "off-ON":
					if ui ==1.:
						return "1", "ON", ""
					else:
						return "0", "off", ""

				if props["onOff"] == "off-on":
					if ui ==1.:
						return "1", "on", ""
					else:
						return "0", "off", ""

				if props["onOff"] == "open-closed":
					if ui ==1.:
						return "1", "open", ""
					else:
						return "0", "closed", ""

				if props["onOff"] == "closed-open":
					if ui ==1.:
						return "1", "closed", ""
					else:
						return "0", "open", ""

				if props["onOff"] == "up-down":
					if ui ==1.:
						return "1", "up", ""
					else:
						return "0", "down", ""

				if props["onOff"] == "closed-open":
					if ui ==1.:
						return "1", "closed", ""
					else:
						return "0", "open", ""

				if props["onOff"] == "down-up":
					if ui ==1.:
						return "1", "down", ""
					else:
						return "0", "up", ""

			offset = 0.
			mult   = 1.
			if "offset" in props and props["offset"] != "":
				try: 	offset = eval(props["offset"])
				except: offset = float(props["offset"])

			if "mult" in props and props["mult"] != "":
				try: 	mult = eval(props["mult"])
				except: mult = float(props["mult"])

			ui = (ui+offset) * mult

			offset2 = 0.
			mult2   = 1.
			if "offset2" in props and props["offset2"] != "":
				try: 	offset2 = eval(props["offset2"])
				except: offset2 = float(props["offset2"])

			if "mult2" in props and props["mult2"] != "":
				try: 	mult2 = eval(props["mult2"])
				except: mult2 = float(props["mult2"])

			if "resistorSensor" in props and props["resistorSensor"] != "0":
				feedVolt = max(1.,float(props["feedVolt"]))
				feedResistor = max(1., float(props["feedResistor"]))
				if props["resistorSensor"] == "ground": # sensor is towards ground
					ui = feedResistor / max(((feedVolt / max(ui, 0.0001)) - 1.), 0.001)
				elif props["resistorSensor"] == "V+": # sensor is towards V+
					ui = feedResistor *(feedVolt / max(ui, 0.0001) -1.)

			if "maxMin" in props and props["maxMin"] == "1":
				MAXRange = 100; MINRange = 10
				if "MAXRange" in props and props["MAXRange"] != "" and "MINRange" in props and props["MAXRange"] != "":
					try: 	MAXRange = eval(props["MAXRange"])
					except: pass
					try: 	MINRange = eval(props["MINRange"])
					except: pass
					ui = (ui - MINRange) / max(MAXRange - MINRange,1)


			if "valueOrdivValue" in props and props["valueOrdivValue"] == "1/value":
				ui = 1. / max(ui, 0.000001)

			if "logScale" in props and props["logScale"] == "1":
					ui = math.log10(max(0.00000001,ui))

			ui = (ui + offset2)*mult2


			dd = "{}".format(ui)
			if "unit" in props and props["unit"] != "":
				unit = props["unit"]
			else:
				unit = ""

			if "format" in props and props["format"] != "":
				ui = props["format"] % ui
			else:
				ui = "{}".format(ui)
		except Exception as e:
			self.exceptionHandler(40, e)
			ui   = "{}".format(data)
			unit = ""
		return dd, ui, unit


####-------------------------------------------------------------------------####
	def updateLight(self, dev, props, data, whichKeysToDisplay ):
		try:
		
			if "illuminance" in data or "lux" in data or "UV" in data or "UVA" in data or "UVB" in data or "IR" in data or "ambient" in data or "white"  or "visible" in data:
				if "unit" in props: unit = props["unit"]
				else:				unit = ""
				if "format" in props: formatN = props["format"]
				else:				   formatN = "%7.2f"
				logScale="0"
				if "logScale" in props:
					logScale = props["logScale"]
					if logScale =="1":
						if "format" in props: formatN = props["format"]
						else:				  formatN = "%7.2f"


				if "UVA" in data and "UVB" in data and not "UV" in data and "UV" in dev.states:
					data["UV"] = (float(data["UVA"]) + float(data["UVB"]) )/2.

				for  state, key in [["illuminance", "lux"],["illuminance", "illuminance"],["IR", "IR"],["UVA", "UVA"],["UVB", "UVB"],["UV", "UV"],["ambient", "ambient"],["white", "white"],["visible", "visible"]]:
					if state in dev.states and key in data :
						if logScale !="1": self.setStatusCol(dev, state, round(float(data[key]),2),  formatN % (float(data[key]))+unit,                                         whichKeysToDisplay, "","",decimalPlaces=2 )
						else:				self.setStatusCol(dev, state, round(float(data[key]),2), (formatN % math.log10(max(0.1,float(data[key]))) ).replace(" ", "")+unit, whichKeysToDisplay, "","",decimalPlaces=2 )

				if "red" in data:
					self.updateRGB( dev, props, data, whichKeysToDisplay, theType="")


		except Exception as e:
			if "{}".format(e) != "None":
				if self.decideMyLog("SensorData"): self.exceptionHandler(40, e)
		return 
####-------------------------------------------------------------------------####
	def updateRGB(self, dev, props, data, whichKeysToDisplay, theType="",dispType =""):
		try:
			if "unit" in props: unit = props["unit"]
			else:				unit = ""

			changed = 0
			if "ambient"	in data: changed += self.updateRGB2(dev, "ambient",	  data, whichKeysToDisplay,unit, dispType=dispType)
			if "clear"		in data: changed += self.updateRGB2(dev, "clear",	  data, whichKeysToDisplay,unit, dispType=dispType)
			if "red"		in data: changed += self.updateRGB2(dev, "red",		  data, whichKeysToDisplay,unit, dispType=dispType)
			if "green"		in data: changed += self.updateRGB2(dev, "green",	  data, whichKeysToDisplay,unit, dispType=dispType)
			if "blue"		in data: changed += self.updateRGB2(dev, "blue",	  data, whichKeysToDisplay,unit, dispType=dispType)
			if "violet"	  	in data: changed += self.updateRGB2(dev, "violet",	  data, whichKeysToDisplay,unit, dispType=dispType)
			if "orange"	  	in data: changed += self.updateRGB2(dev, "orange",	  data, whichKeysToDisplay,unit, dispType=dispType)
			if "yellow"	  	in data: changed += self.updateRGB2(dev, "yellow",	  data, whichKeysToDisplay,unit, dispType=dispType)
			if "lux"		in data: changed += self.updateRGB2(dev, "lux",		  data, whichKeysToDisplay,unit, dispType=dispType)
			if "illuminance" in data: 
					changed += self.updateRGB2(dev, "illuminance",data, whichKeysToDisplay,unit, dispType=dispType)

			if changed > 0:
					if "stateGreen" not in props: dev.updateStateImageOnServer(indigo.kStateImageSel.LightSensorOn)
					if "illuminance" in dev.states and "illuminance" not in data:
						il = (-0.32466 * data['red']) + (1.57837 * data['green']) + (-0.73191 * data['blue'])  # fron adafruit
						ilUI = "{:.1f}[Lux]".format(il)
						self.setStatusCol(dev, "illuminance", round(il,1), ilUI, whichKeysToDisplay, "","",decimalPlaces=1 )
					if "kelvin" in dev.states:
						k = int(self.calcKelvin(data))
						self.setStatusCol(dev, "kelvin", k, "{}[ºK]".format(k), whichKeysToDisplay, "","",decimalPlaces=0 )
			if whichKeysToDisplay == "red/green/blue":
						self.addToStatesUpdateDict(dev.id, "status", "r/g/b: {}/{}/{} {}".format(data['red'], data['green'], data['blue'], unit ) )

		except Exception as e:
			self.exceptionHandler(40, e)
		return 

####-------------------------------------------------------------------------####
	def updateRGB2(self, dev, color, data, whichKeysToDisplay, unit, dispType=""):

		try:
			if color not in dev.states:
				return 0
			if dispType != "":
				try:
					delta = abs(dev.states[color] - float(data[color]))
				except:
					delta = 10000
				if delta < 10 ** (-int(dispType)): return 0

				if color == "lux"  or color == "illuminance":	 dispType=2
				self.setStatusCol(dev, color, float(data[color]), color+" {}".format(data[color])+unit, whichKeysToDisplay, "","",decimalPlaces=dispType )
				return 1

			if dev.states[color] != "{}".format(data[color]):
				self.setStatusCol(dev, color, float(data[color]), "color {}".format(data[color])+unit, whichKeysToDisplay, "","",decimalPlaces=dispType )
				return 1
			return 0
		except Exception as e:
			self.exceptionHandler(40, e)
		return 0
####-------------------------------------------------------------------------####
	def calcKelvin(self, data):	 # from adafruit
		X = (-0.14282 * data['red']) + (1.54924 * data['green']) + (-0.95641 * data['blue'])
		Y = (-0.32466 * data['red']) + (1.57837 * data['green']) + (-0.73191 * data['blue'])
		Z = (-0.68202 * data['red']) + (0.77073 * data['green']) + (0.56332  * data['blue'])

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
			useFormat = "{{:.{}f}}".format(self.tempDigits)
			suff = "ºC"
			temp = float(temp)

			if temp == 999.9:
				return 999.9, "badSensor", 1, useFormat

			if self.tempUnits == "Fahrenheit":
				temp = temp * 9. / 5. + 32.
				suff = "ºF"
			elif self.tempUnits == "Kelvin":
				temp += 273.15
				suff = "ºK"

			temp = round(temp,self.tempDigits)
			tempU = useFormat.format(temp)
			return temp, tempU + suff,self.tempDigits, useFormat

		except Exception as e:
			self.exceptionHandler(40, e)
		return -99, "",self.tempDigits, useFormat


####-------------------------------------------------------------------------####
	def convAlt(self, press, props, temp):
		try:
			offsetAlt 	= 0.
			useFormat 	= "{:.1f}"
			suff 		= "[m]"
			cString 	= "%.1f"
			aD 			= 1
			if "offsetAlt" in props:
				try: offsetAlt = float(props["offsetAlt"])
				except: pass
			pAtSeeLevel = 101325.0 # in pascal

			alt = ((temp + 273.15)/0.0065)  *  ( 1. - pow( pAtSeeLevel / press, 0.1902843) ) + offsetAlt

			alt = float(alt)
			if self.distanceUnits == "0.01":
				alt *= 100.
				suff = " cm"
				cString = "%.0f"
				aD = 0
			elif self.distanceUnits == "0.0254":
				alt /= 0.0254
				suff = ' inch'
				cString = "%.0f"
				aD = 0
			elif self.distanceUnits == "0.348":
				alt /= 2.54
				suff = " feet"
				cString = "%.1f"
				aD = 1
			elif self.distanceUnits == "0.9144":
				alt /= 0.9144
				suff = " y"
				cString = "%.2f"
				aD = 1
			else:
				pass
			altU = (cString % alt).strip()
			return round(alt,aD) , altU + suff,aD, useFormat
		except Exception as e:
			self.exceptionHandler(40, e)
		return -99, "",aD, useFormat



####-------------------------------------------------------------------------####
	def convHum(self, hum):
		try:
			return int(float(hum)), "{:.0f}%".format(float(hum)) ,0
		except Exception as e:
			self.exceptionHandler(40, e)
			return -99, "",0

####-------------------------------------------------------------------------####
	def convGas(self, GasIN, dev, props):
		#data["GasResistance"], data["AirQuality"], data["GasBaseline"],data["SensorStatus"]
		try:
			bad = False
			try:
					GasResistance	 = "{:.0f}KOhm" .format(float(GasIN["GasResistance"])/1000.)
					GasResistanceInt = int(float(GasIN["GasResistance"]))
			except:
					bad = True
			try:
					AirQuality	  = "{:.0f}%".format(float(GasIN["AirQuality"]))
					AirQualityInt = int(float(GasIN["AirQuality"]) )
					AirQualityTextItems = props.get("AirQuality0-100ToTextMapping", "90=Good/70=Average/55=little bad/40=bad/25=worse/0=very bad").split("/")
					ok = False
					if len(AirQualityTextItems) >2:
						try:
							aq = []
							for ii in AirQualityTextItems:
								xx = ii.split("=")
								aq.append([int(xx[0]),xx[1]])
							ok = True
						except:
							pass
					if not ok:
						aq = []
						AirQualityTextItems = "95=Good/85=Average/75=Little Bad/65=Bad/50=Worse/0=Very Bad".split("/")
						for ii in AirQualityTextItems:
							xx = ii.split("=")
							aq.append([int(xx[0]),xx[1]])

					AirQualityText = aq[-1][1]
					for ii in aq:
						if AirQualityInt > ii[0]:
							AirQualityText = ii[1]
							#self.indiLOG.log(20,"AirQuality:{}; result:{}; aq {} --> {}".format(AirQuality, ii, AirQualityTextItems, aq))
							break
			except:
					bad = True
					AirQualityText  = ""
			try:
					baseline	  = ("%.0f" % (float(GasIN["GasBaseline"]))).strip()+"%"
					baselineInt	  = int(float(GasIN["GasBaseline"]))
			except:
					bad = True
			try:
					SensorStatus  = GasIN["SensorStatus"]
					if SensorStatus.find("measuring") ==-1:
						AirQuality = SensorStatus
			except:
					bad = True

			if not bad:
				#self.indiLOG.log(20,"{} returning: {} {} {} {} {} {} {} {}".format(dev.name, GasResistanceInt, GasResistance , AirQualityInt, AirQuality, baselineInt, baseline, SensorStatus, AirQualityText))
				return GasResistanceInt, GasResistance , AirQualityInt, AirQuality, baselineInt, baseline, SensorStatus, AirQualityText
			else:
				return "", "","", "","", "", "", ""
		except:
			return "", "","", "","", "", "", ""


####-------------------------------------------------------------------------####
	def getDeviceDisplayStateId(self, dev):
		if dev.pluginProps.get("displayState","") !="": 	return dev.pluginProps["displayState"]
		elif "displayStatus" in dev.states:					return "displayStatus"
		else:												return "status"

###-------------------------------------------------------------------------####
	def checkForFastDown(self, mac, piMACSend, dev, props, rssi, fromPiU, newStates):
		try:
			if mac == piMACSend: return 
			if rssi > -999: return 

			if newStates["status"] != "up" or rssi > -999. or time.time() < self.currentlyBooting:	 return ## check for fast down signal ==-999

			piI = int(fromPiU)

			if self.decideMyLog("CAR") and self.decideMyLog("BeaconData"): self.indiLOG.log(5,"testing fastdown from pi:{:2s}  for:{};  piStillUp? {}, new sig=-999; oldsig={:4d}  status={} ".format(fromPiU, mac, piStillUp, self.beacons[mac]["receivedSignals"][piI]["rssi"] , dev.states["status"]))

			try:	fastDownTime = float(props.get("fastDown","-1"))
			except: fastDownTime = -1.
			if fastDownTime <=0: return 

			self.beacons[mac]["receivedSignals"][piI]["lastSignal"] = time.time() 
			self.beacons[mac]["receivedSignals"][piI]["rssi"] = rssi

			atLEastOneUp = []
			for piyy in range(_GlobalConst_numberOfiBeaconRPI):
				if piyy  == piI: continue
				if ( time.time() - self.beacons[mac]["receivedSignals"][piyy]["lastSignal"] < fastDownTime and self.beacons[mac]["receivedSignals"][piyy]["rssi"]  != -999):
					atLEastOneUp.append(piyy) 

			if self.selectBeaconsLogTimer !={}:
				for sMAC in self.selectBeaconsLogTimer:
					if mac.find(sMAC[:self.selectBeaconsLogTimer[sMAC]]) == 0:
						self.indiLOG.log(10,"sel.beacon logging: Fstdwn-999-1  - :{} -999 receivedfrom:{}, rpi(s) till w signal:{}".format(mac, fromPiU, atLEastOneUp))

			if atLEastOneUp == []:
				delayF = self.delayFastDownBy
				piXX = "Pi_{:02d}".format(int(fromPiU))
				self.delayedActions["data"].put( {"actionTime":time.time() + delayF,  "devId":dev.id, "updateItems":[ {"fastDown":{"mac":mac, "piSignal":piXX+"_Signal", "fastDownTime": fastDownTime, "delayF":delayF, "lastRpiWithSignal":dev.states["lastUpdateFromRPI"]}} ] })  
			return 

		except Exception as e:

			if "{}".format(e).find("timeout waiting") > -1:
				self.exceptionHandler(40, e)
				self.indiLOG.log(40,"communication to indigo is interrupted")
				return
			if e is not None	and "{}".format(e).find("not found in database") ==-1:
				self.exceptionHandler(40, e)
		return 

###-------------------------------------------------------------------------####
	def execDelaytedActionForFastDown(self, dev, actionItems):
		try:
			
			mac = actionItems["mac"]
			piSignal = actionItems["piSignal"]
			fastDownTime = actionItems["fastDownTime"]
			delayF = actionItems["delayF"]
			lastRpiWithSignal = actionItems["lastRpiWithSignal"]
			if self.decideMyLog("DelayedActions"): self.indiLOG.log(10,"delayedActionsThread  check if execute fastDown, for dev:{}, mac:{}, fastDownTime:{:.1f}, dt-lastUp:{:.1f} > {:.1f}: {:1}, lastRpiWithSignal:{}".format(dev.name, mac, fastDownTime, time.time() - self.beacons[mac]["lastUp"],  delayF, time.time() - self.beacons[mac]["lastUp"] <= delayF, lastRpiWithSignal))
			if self.beacons[mac]["status"]  == "up" and time.time() - self.beacons[mac]["lastUp"] < delayF: return 

			self.addToStatesUpdateDict(dev.id,piSignal, -999)

			if self.decideMyLog("DelayedActions"): self.indiLOG.log(10,"delayedActionsThread  check if execute fastDown  -- yes".format())
			dev.updateStateImageOnServer(indigo.kStateImageSel.SensorOff)	# only for regluar ibeacons..
			self.addToStatesUpdateDict(dev.id, "status", "down")
			self.beacons[mac]["status"] = "down"
			self.beacons[mac]["lastUp"] = -time.time()

			self.addToStatesUpdateDict(dev.id, "closestRPILast", dev.states["closestRPI"])
			self.addToStatesUpdateDict(dev.id, "closestRPI", -1)
			if self.setClostestRPItextToBlank: 
				self.addToStatesUpdateDict(dev.id, "closestRPITextLast", dev.states["closestRPI"])
				self.addToStatesUpdateDict(dev.id, "closestRPIText", "")
			props = dev.pluginProps
			if "showBeaconOnMap" in props and props["showBeaconOnMap"] in _GlobalConst_beaconPlotSymbols: self.beaconPositionsUpdated =4
			if self.selectBeaconsLogTimer !={}:
				for sMAC in self.selectBeaconsLogTimer:
					if mac.find(sMAC[:self.selectBeaconsLogTimer[sMAC]]) == 0:
						self.indiLOG.log(10,"sel.beacon logging: Fstdwn-999-2  - :{} / {};  set status to down".format(dev.name, mac) )

		except Exception as e:

			if "{}".format(e).find("timeout waiting") > -1:
				self.exceptionHandler(40, e)
				self.indiLOG.log(40,"communication to indigo is interrupted")
				return
			if e is not None	and "{}".format(e).find("not found in database") ==-1:
				self.exceptionHandler(40, e)
		return 

###-------------------------------------------------------------------------####
	def handleBeaconRealSignal(self, mac, piMACSend, dev, props, beaconUpdatedIds, rssi, txPower, rssiOffset, fromPiU, newStates, dateString ):

		try:
			fromPiI = int(fromPiU)
			logTRUEfromChangeOFRPI = False
			updateSignal = False
			closestRPI = -1
			oldRPI = -1
			piXX = "Pi_{:02d}".format(fromPiI)
			if piXX+"_Signal" not in dev.states: 
				return updateSignal, newStates, logTRUEfromChangeOFRPI, oldRPI, closestRPI, [[fromPiI,dev.id, 99999]]

			if dev.deviceTypeId == "beacon":
				try:	oldRPI = int(dev.states["closestRPI"])
				except: oldRPI =-1

			try:     distCalc = float(dev.states[piXX+"_Distance"])
			except:  distCalc = 99999.

			if rssi != -999.:
				if self.selectBeaconsLogTimer !={}:
					for sMAC in self.selectBeaconsLogTimer:
						if mac.find(sMAC[:self.selectBeaconsLogTimer[sMAC]]) ==0:
							self.indiLOG.log(10,"sel.beacon logging: newMSG    up  - :{}; set status up, rssi:{}".format(mac, rssi))

				if ( self.beacons[mac]["lastUp"] > -1) :
					self.beacons[mac]["receivedSignals"][fromPiI]["rssi"]  = rssi
					self.beacons[mac]["receivedSignals"][fromPiI]["lastSignal"]  = time.time()
					self.beacons[mac]["lastUp"] = time.time()
					distCalc = 9999.
					closestRPI = -1
					try:
						minTxPower = float(self.beacons[mac]["beaconTxPower"])
					except:
						minTxPower = 99999.
					if dev.deviceTypeId in ["beacon", "rPI"]:
						txx = float(txPower)
						if minTxPower <	 991.:
							txx = minTxPower
							distCalc = self.calcDist(  txx, (rssi+rssiOffset) )/ self.distanceUnits
							self.beacons[mac]["receivedSignals"][fromPiI]["distance"]  = distCalc
						closestRPI = self.findClosestRPI(mac, dev)

					if	( time.time()- self.beacons[mac]["updateWindow"] > self.beacons[mac]["updateSignalValuesSeconds"] or
						  time.time()- self.beacons[mac]["receivedSignals"][fromPiI]["lastSignal"] > 100. ):  # ==0 or xx seconds updates for 75 seconds, this RPI msg older than 100 secs then xx secs no update for next time
						self.beacons[mac]["updateWindow"] = time.time()

					if (dev.deviceTypeId == "beacon" and closestRPI != oldRPI) and self.trackSignalChangeOfRPI:
						logTRUEfromChangeOFRPI = True

					try: newStates[piXX+"_Signal"]
					except: self.indiLOG.log(40,"{} no state {}".format(dev.name ,piXX+"_Signal") )

					if (
						( self.beacons[mac]["status"] != "up" )																or	# was down now up
						( time.time() - self.beacons[mac]["updateWindow"] < 70 )												or	# update for 70 seconds then break
						( newStates[piXX+"_Signal"] == -999 )																	or	# was down now up
						( abs( newStates[piXX+"_Signal"] - self.beacons[mac]["receivedSignals"][fromPiI]["rssi"] ) >20 )		or	# signal change large
						( dev.deviceTypeId == "beacon" and closestRPI != newStates["closestRPI"] )							# clostest RPi has changed
						):
							updateSignal = True
							newStates = self.addToStatesUpdateDict(dev.id,piXX+"_Signal", int(rssi-rssiOffset),newStates=newStates)
							newStates = self.addToStatesUpdateDict(dev.id, "TxPowerReceived",int(txPower),newStates=newStates)

							if dev.deviceTypeId == "beacon"  and distCalc < 100/self.distanceUnits and not ("IgnoreBeaconForClosestToRPI" in props and props["IgnoreBeaconForClosestToRPI"] !="0"):
								beaconUpdatedIds.append([fromPiI,dev.id, distCalc])
								self.beacons[mac]["receivedSignals"][fromPiI]["distance"] = distCalc
							newStates = self.addToStatesUpdateDict(dev.id,piXX+"_Distance", distCalc,newStates=newStates ,decimalPlaces=1  )
							newStates = self.addToStatesUpdateDict(dev.id,piXX+"_Time", dateString,newStates=newStates)
					if newStates["status"] != "up":
						if mac != piMACSend: dev.updateStateImageOnServer(indigo.kStateImageSel.SensorOn)
						newStates=self.addToStatesUpdateDict(dev.id, "status", "up", newStates=newStates)
						self.statusChanged = 13
						self.beacons[mac]["status"] = "up"
						if "showBeaconOnMap" in props and props["showBeaconOnMap"] in _GlobalConst_beaconPlotSymbols: self.beaconPositionsUpdated =5

					if dev.deviceTypeId == "beacon" or dev.deviceTypeId == "rPI":
						if closestRPI != dev.states["closestRPI"]:
							if "{}".format(dev.states["closestRPI"]) != "-1":
								self.addToStatesUpdateDict(dev.id, "closestRPILast", dev.states["closestRPI"])
								self.addToStatesUpdateDict(dev.id, "closestRPITextLast", dev.states["closestRPIText"])
						newStates = self.addToStatesUpdateDict(dev.id, "closestRPI",     closestRPI,newStates=newStates)
						newStates = self.addToStatesUpdateDict(dev.id, "closestRPIText", self.getRPIdevName((closestRPI)),newStates=newStates)

					newStates = self.addToStatesUpdateDict(dev.id, "lastUpdateFromRPI", fromPiI, newStates=newStates)

				self.beacons[mac]["indigoId"] = dev.id
				self.beacons[mac]["receivedSignals"][fromPiI]["rssi"]  = rssi
				self.beacons[mac]["receivedSignals"][fromPiI]["lastSignal"]  = time.time()
				self.beacons[mac]["lastUp"] = time.time()

				if self.beacons[mac]["receivedSignals"][fromPiI]["rssi"] != rssi+rssiOffset:
					self.beacons[mac]["receivedSignals"][fromPiI] = {"rssi":rssi+rssiOffset, "lastSignal":time.time(), "distance":distCalc}

			newStates = self.addToStatesUpdateDict(dev.id, "lastUpdateFromRPI", fromPiI, newStates=newStates)
			return updateSignal, newStates, logTRUEfromChangeOFRPI, oldRPI, closestRPI, beaconUpdatedIds


		except Exception as e:

			if "{}".format(e).find("timeout waiting") > -1:
				self.exceptionHandler(40, e)
				self.indiLOG.log(40,"communication to indigo is interrupted")
				return
			if e is not None	and "{}".format(e).find("not found in database") ==-1:
				self.exceptionHandler(40, e)
		return updateSignal, newStates, logTRUEfromChangeOFRPI, oldRPI, closestRPI, beaconUpdatedIds

###-------------------------------------------------------------------------####

	def handleRPIMessagePart(self, piMACSend, newRPI, fromPiU, piNReceived, ipAddress, dateString, beaconUpdatedIds):
		try:


			if self.RPI[fromPiU]["piMAC"] != piMACSend:
				if self.RPI[fromPiU]["piMAC"] == "" or self.RPI[fromPiU]["piMAC"].find("00:00:") ==0 :
					newRPI = self.RPI[fromPiU]["piMAC"]
					self.indiLOG.log(10,"pi#: {};  MAC number change from: {}; to: {}".format(fromPiU, newRPI, piMACSend) )
					self.RPI[fromPiU]["piMAC"] = piMACSend

				else:
					try:
						existingIndigoId = int(self.RPI[fromPiU]["piDevId"])
						existingPiDev	 = indigo.devices[existingIndigoId]
						props			 = existingPiDev.pluginProps
						try:
							oldMAC		 = props["address"]
						except:
							oldMAC		 = existingPiDev.description

						if oldMAC != piMACSend:	 # should always be !=
							self.indiLOG.log(10,"trying: to replace , create new RPI for   "+piMACSend+"  {}".format(props))
							if piMACSend not in self.beacons:
								replaceRPIBeacon =""
								for btest in self.beacons:
									if self.beacons[btest]["indigoId"] == existingIndigoId:
										replaceRPIBeacon = btest
										break
								if replaceRPIBeacon !="":
									self.beacons[piMACSend] = copy.deepcopy(self.beacons[replaceRPIBeacon])
									del self.beacons[replaceRPIBeacon]
									self.indiLOG.log(10," replacing old beacon")
								else:
									self.beacons[piMACSend]					  	= copy.deepcopy(_GlobalConst_emptyBeacon)
									self.beacons[piMACSend]["ignore"]		  	= 0
									self.beacons[piMACSend]["indigoId"]	  		= existingIndigoId
									self.beacons[piMACSend]["note"]		  		= "Pi-{}".format(fromPiU)
									self.beacons[piMACSend]["RPINumber"]  		= fromPiU
									self.beacons[piMACSend]["status"]		 	= "up"
								props["address"]	 = piMACSend
								props["ipNumberPi"]  = ipAddress
		
								existingPiDev.replacePluginPropsOnServer(props)
								existingPiDev = indigo.device[existingIndigoId]
								try:
									existingPiDev.address = piMACSend
									existingPiDev.replaceOnServer()
								except: pass
								self.RPI[fromPiU]["piMAC"]	 = piMACSend
								self.RPI[fromPiU]["ipNumberPi"] = ipAddress
								if oldMAC in self.beacons: del self.beacons[oldMAC]
								self.setALLrPiV("piUpToDate", ["updateParamsFTP"])
								self.fixConfig(checkOnly = ["all", "rpi"],fromPGM="updateBeaconStates pichanged") # updateBeaconStates # ok only if new MAC for rpi ...
								self.addToStatesUpdateDict("{}".format(existingPiDev.id), "vendorName", self.getVendortName(piMACSend))
							else:
								if self.beacons[piMACSend]["typeOfBeacon"].lower() !="rpi":
									pass # let the normal process replace the beacon with the RPI
								else:
									self.RPI[fromPiU]["piMAC"] = piMACSend
									self.indiLOG.log(10,"might have failed to replace RPI pi#: {}; piMACSend: {}; , you have to do it manually; beacon with type = rpi already exist ".format(fromPiU, piMACSend) )

					except Exception as e:
							self.exceptionHandler(40, e)
							self.indiLOG.log(40,"failed to replace RPI pi#= {};  piMACSend: {};  you have to do it manually".format(fromPiU, piMACSend) )

			keepThisMessage = 0
			foundPI = False
			if piMACSend in self.beacons:
				indigoId = self.beacons[piMACSend]["indigoId"]
				if indigoId == 0:
					indigoId = int(self.RPI[fromPiU]["piDevId"])
					if indigoId >0:
						self.beacons[piMACSend]["indigoId"] = indigoId
						self.beacons[piMACSend]["RPINumber"] = fromPiU

						self.indiLOG.log(30,"fixing tables for pi#= {};  piMACSend: {} beacon ID was 0 to :{}".format(fromPiU, piMACSend, indigoId) )
						self.saveConfig(only="beacons")
					else:
						return 11, beaconUpdatedIds


				if self.beacons[piMACSend]["RPINumber"] == "-1":
					self.beacons[piMACSend]["RPINumber"] = fromPiU
					self.indiLOG.log(30,"fixing tables for pi#= {};  piMACSend: {} RPINumber was -1 to :{}".format(fromPiU, piMACSend, fromPiU) )
					self.saveConfig(only="beacons")


				try:
					dev = indigo.devices[indigoId]
					props = dev.pluginProps
				except Exception as e:

					if "{}".format(e).find("timeout waiting") > -1:
						self.exceptionHandler(40, e)
						self.indiLOG.log(40,"communication to indigo is interrupted")
						return 1, beaconUpdatedIds
					if "{}".format(e).find("not found in database") ==-1:
						self.exceptionHandler(40, e)
						self.indiLOG.log(40,"updateBeaconStates beacons dict: {}".format(self.beacons[piMACSend]))
					return 2, beaconUpdatedIds

				try:
					if dev.deviceTypeId == "rPI":
						props = dev.pluginProps
						foundPI = True
						if dev.states["note"] != "Pi-" + fromPiU:
							dev.updateStateOnServer("note", "Pi-" + fromPiU)
							#self.addToStatesUpdateDict(dev.id, "note", "Pi-" + fromPiU)
						if props.get("RPINumber","=-=") != fromPiU:
							props["RPINumber"] = fromPiU
							dev.replacePluginPropsOnServer(props)

						self.beacons[piMACSend]["lastUp"] = time.time()

						self.RPI[fromPiU]["piDevId"] = dev.id
						if dev.description != "Pi-"+ fromPiU+"-"+ipAddress:
							dev.description = "Pi-"+ fromPiU+"-"+ipAddress
							dev.replaceOnServer()
						self.beacons[piMACSend]["RPINumber"] = fromPiU

					else:
						self.indiLOG.log(30,"=== deleting beacon: {} replacing simple beacon with rPi model(1)".format(dev.name) )
						del self.beacons[dev.pluginProps["address"]]
						indigo.device.delete(dev)

				except Exception as e:
					if "{}".format(e) != "None":
						self.exceptionHandler(40, e)
						self.indiLOG.log(40,"beacons[piMACSend] pi#: {}; Pisend: {}; indigoID: {}; beaconsDict: {}".format(fromPiU,  piMACSend, indigoId, self.beacons[piMACSend] ) )
						if "{}".format(e).find("timeout waiting") > -1:
							self.exceptionHandler(40, e)
							self.indiLOG.log(40,"communication to indigo is interrupted")
							return 3, beaconUpdatedIds
						self.indiLOG.log(30,"error ok if new / replaced RPI")

					del self.beacons[piMACSend]

			if not foundPI:
				if piMACSend in self.beacons: del self.beacons[piMACSend]
				delDEV = []
				dev = ""
				for dev in indigo.devices.iter("props.isRPIDevice"):
					props = dev.pluginProps

					try:
						if props["address"] == newRPI and newRPI != "":
							newRPI = "found"
							break

						elif props["address"] == piMACSend:
							delDEV.append(dev)
							self.RPI[fromPiU]["piDevId"] = 0
					except:

						self.indiLOG.log(10,"device has no address, setting piDevId=0: {}  {} {}".format(dev.name, dev.id, "{}".format(props)) )
						delDEV.append(dev)
						self.RPI[fromPiU]["piDevId"] = 0

				for devx in delDEV:
					self.indiLOG.log(10,"===  deleting beacon: {}  replacing simple beacon with rPi model(2)".format(devx.name) )
					try:
						indigo.device.delete(devx)
					except:
						pass

				if newRPI != "found":
					self.indiLOG.log(10,"creating new pi (3.)  -- fromPI: {};   piNR: {};   piMACSend: {};   ipAddress: {} " .format(fromPiU, piNReceived, piMACSend, ipAddress) )

					newProps = copy.copy(_GlobalConst_emptyrPiProps)
					newProps["rpiDataAcquistionMethod"] = self.rpiDataAcquistionMethod
					newProps["RPINumber"] = fromPiU
					# reset dev states 
					self.rePopulateStates = "add new rpi"
					indigo.device.create(
						protocol		= indigo.kProtocol.Plugin,
						address			= piMACSend,
						name			= "Pi_" + piMACSend,
						description		= "Pi-" + fromPiU+"-"+ipAddress,
						pluginId		= self.pluginId,
						deviceTypeId	= "rPI",
						folder			= self.piFolderId,
						props			= newProps
						)

					try:
						dev = indigo.devices["Pi_" + piMACSend]
					except Exception as e:
						if "{}".format(e).find("timeout waiting") > -1:
							self.exceptionHandler(40, e)
							self.indiLOG.log(40,"communication to indigo is interrupted")
							return  4, beaconUpdatedIds
						if "{}".format(e).find("not found in database") ==-1:
							self.exceptionHandler(40, e)
							return  5, beaconUpdatedIds
						self.exceptionHandler(40, e)
						return  6, beaconUpdatedIds

				dev.updateStateImageOnServer(indigo.kStateImageSel.SensorOn)
				self.addToStatesUpdateDict(dev.id, "vendorName", self.getVendortName(piMACSend))
				self.addToStatesUpdateDict(dev.id, "status", "up")
				self.addToStatesUpdateDict(dev.id, "note", "Pi-" + fromPiU)
				self.addToStatesUpdateDict(dev.id, "TxPowerSet", int(_GlobalConst_emptyrPiProps["beaconTxPower"]))
				self.addToStatesUpdateDict(dev.id, "created", dateString)
				self.addToStatesUpdateDict(dev.id, "Pi_{:02d}_Signal".format(int(fromPiU)), 0)
				self.addToStatesUpdateDict(dev.id, "TxPowerReceived",0)
				self.addToStatesUpdateDict(dev.id, "groupMember","PI" )
				self.executeUpdateStatesDict(onlyDevID=dev.id, calledFrom="updateBeaconStates new rpi")

				self.updatePiBeaconNote[piMACSend] 				= 1
				self.beacons[piMACSend]							= copy.deepcopy(_GlobalConst_emptyBeacon)
				self.beacons[piMACSend]["expirationTime"]		= self.secToDown
				self.beacons[piMACSend]["indigoId"]				= dev.id
				self.beacons[piMACSend]["status"]				= "up"
				self.beacons[piMACSend]["lastUp"]				= time.time()
				self.beacons[piMACSend]["note"]					= "Pi-" + fromPiU
				self.beacons[piMACSend]["RPINumber"]			= fromPiU
				self.beacons[piMACSend]["typeOfBeacon"]			= "rPI"
				self.beacons[piMACSend]["created"]				= dateString
				self.RPI[fromPiU]["piDevId"]					= dev.id  # used to quickly look up the rPI devices in indigo
				self.RPI[fromPiU]["piMAC"]						= piMACSend
				self.setGroupStatusNextCheck = -1
				self.setONErPiV(fromPiU, "piUpToDate", ["updateParamsFTP", "rebootSSH"])
				self.fixConfig(checkOnly = ["all", "rpi", "force"],fromPGM="updateBeaconStates1") # updateBeaconStates # ok only if new MAC for rpi ...
				self.statusChanged = 14

		except Exception as e:
			if "{}".format(e).find("timeout waiting") > -1:
				self.exceptionHandler(40, e)
				self.indiLOG.log(40,"communication to indigo is interrupted")
			if e is not None	and "{}".format(e).find("not found in database") ==-1:
				self.exceptionHandler(40, e)
			keepThisMessage = 7

		return  keepThisMessage, beaconUpdatedIds


###-------------------------------------------------------------------------####
	def getBeaconDeviceAndCheck(self, mac, typeOfBeacon, rssi, txPower, fromPiU, piMACSend, dateString, rssiOffset):
		try:
			keepThisMessage = True
			dev = {}
			props = {}
			newStates = {}
			setALLrPiVUpdate = ""
			fromPiI = int(fromPiU)
			## found valid msg and beacon, update indigo etc
			name = ""
			indigoId = self.beacons[mac]["indigoId"]
			if indigoId != 0:
				try:
					dev = indigo.devices[indigoId]
					name = dev.name
					props = dev.pluginProps
					newStates = copy.copy(dev.states)
				except Exception as e:
					if "{}".format(e).find("timeout waiting") > -1:
						self.exceptionHandler(40, e)
						self.indiLOG.log(40,"communication to indigo is interrupted")
						return setALLrPiVUpdate, dev, props, newStates, False
					if "{}".format(e).find("not found in database") ==-1:
						self.exceptionHandler(40, e)
						return setALLrPiVUpdate, dev, props, newStates, False
					self.indiLOG.log(40,"Line {} has error={}".format(sys.exc_info()[2].tb_lineno, e)   + " indigoId:{}".format(self.beacons[mac]["indigoId"]))
					self.beacons[mac]["indigoId"] = 0

			else: # no indigoId found, double check
				for dev in indigo.devices.iter("props.isBeaconDevice,props.isRPIDevice"):
					props = dev.pluginProps
					if "address" in props:
						if props["address"] == mac:
							if dev.deviceTypeId != "beacon":
								self.indiLOG.log(5," rejecting new beacon, same mac number already exist for different device type: {}  dev: {}".format(dev.deviceTypeId, dev.name))
								continue
							else:
								self.beacons[mac]["indigoId"] = dev.id
								name = dev.name
								newStates = copy.copy(dev.states)
								break

			if self.selectBeaconsLogTimer !={}:
					for sMAC in self.selectBeaconsLogTimer:
						if mac.find(sMAC[:self.selectBeaconsLogTimer[sMAC]]) ==0:
							self.indiLOG.log(10,"sel.beacon logging: pass 1          :{}; getBeaconDeviceAndCheck".format(mac)  )

			if rssi < self.acceptNewiBeacons and name == "" and self.beacons[mac]["ignore"] > 0:
				if self.selectBeaconsLogTimer !={}:
					for sMAC in self.selectBeaconsLogTimer:
						if mac.find(sMAC[:self.selectBeaconsLogTimer[sMAC]]) ==0:
							self.indiLOG.log(10,"sel.beacon logging: newMSG rej rssi :{}; name= empty and ignore > 0".format(mac)  )
				return setALLrPiVUpdate, dev, props, newStates, False

			if self.selectBeaconsLogTimer !={}:
					for sMAC in self.selectBeaconsLogTimer:
						if mac.find(sMAC[:self.selectBeaconsLogTimer[sMAC]]) ==0:
							self.indiLOG.log(10,"sel.beacon logging: pass 2          :{}; getBeaconDeviceAndCheck".format(mac)  )

			if name == "":
				self.indiLOG.log(10,"creating new beacon,  received from pi #  {}/{}:   beacon-{}  typeOfBeacon: {}".format(fromPiU, piMACSend, mac, typeOfBeacon) )

				name 				 		= "beacon_" + mac
				desc 		 		 		= "detected on pi#{}".format(fromPiU)
				SupportsBatteryLevel 		= False
				batteryLevelUUID	 		= "off"
				beaconBeepUUID 		 		= "off"
				useOnlyPrioTagMessageTypes	= "0"
				if typeOfBeacon in self.knownBeaconTags["input"]:
					if "commands" in self.knownBeaconTags["input"][typeOfBeacon]:
						if "batteryLevel" in self.knownBeaconTags["input"][typeOfBeacon]["commands"]:
							if  self.knownBeaconTags["input"][typeOfBeacon]["commands"]["batteryLevel"]["type"] == "BLEconnect" and "gattcmd" in self.knownBeaconTags["input"][typeOfBeacon]["commands"].get("batteryLevel",""):
								SupportsBatteryLevel = True
								batteryLevelUUID	 = "gatttool"
							if  self.knownBeaconTags["input"][typeOfBeacon]["commands"]["batteryLevel"]["type"].find("msg") >-1:
								SupportsBatteryLevel = True
								batteryLevelUUID	 = "msg"
						if "beep" in self.knownBeaconTags["input"][typeOfBeacon]["commands"]:
							if  "cmdON" in self.knownBeaconTags["input"][typeOfBeacon]["commands"]["beep"]:
								beaconBeepUUID	 = "gatttool"
					useOnlyPrioTagMessageTypes = self.knownBeaconTags["input"][typeOfBeacon]["useOnlyThisTagToAcceptBeaconMsgDefault"]

				newprops = copy.copy(_GlobalConst_emptyBeaconProps)
				newprops["typeOfBeacon"] 				= typeOfBeacon
				newprops["version"] 					= typeOfBeacon # this is for  the firmware field
				newprops["SupportsBatteryLevel"] 		= SupportsBatteryLevel
				newprops["batteryLevelUUID"] 			= batteryLevelUUID
				newprops["beaconBeepUUID"]				= beaconBeepUUID
				newprops["useOnlyPrioTagMessageTypes"]	= "0"
				newprops["batteryLevelUUID"]			= batteryLevelUUID
				newprops["beaconTxPower"]				= -60

				dev = indigo.device.create(
					protocol		= indigo.kProtocol.Plugin,
					address			= mac,
					name			= name,
					description		= desc,
					pluginId		= self.pluginId,
					deviceTypeId	= "beacon",
					folder			= self.piFolderId,
					props			= newprops
					)
				try:
					dev = indigo.devices[dev.id]
					props = dev.pluginProps
				except Exception as e:

					if "{}".format(e).find("timeout waiting") > -1:
						self.exceptionHandler(40, e)
						self.indiLOG.log(40,"communication to indigo is interrupted")
						return setALLrPiVUpdate, dev, props, newStates, False
				dev.updateStateImageOnServer(indigo.kStateImageSel.SensorOn)
				self.addToStatesUpdateDict(dev.id, "vendorName", self.getVendortName(mac))
				self.addToStatesUpdateDict(dev.id, "status", "up")
				self.addToStatesUpdateDict(dev.id, "typeOfBeacon", typeOfBeacon)
				self.addToStatesUpdateDict(dev.id, "note", "beacon-"+typeOfBeacon)
				self.addToStatesUpdateDict(dev.id, "created", dateString)
				self.addToStatesUpdateDict(dev.id, "TxPowerSet", int(_GlobalConst_emptyBeaconProps["beaconTxPower"]))

				for iiU in _rpiBeaconList:
					if iiU == fromPiU: continue
					if "Pi_{:02d}_Signal".format(int(iiU)) in dev.states:
						self.addToStatesUpdateDict(dev.id, "Pi_{:02d}_Signal".format(int(iiU)),-999)

				self.addToStatesUpdateDict(dev.id, "Pi_{:02d}_Signal".format(fromPiI), int(rssi+rssiOffset))
				self.addToStatesUpdateDict(dev.id, "TxPowerReceived",int(txPower))
				self.addToStatesUpdateDict(dev.id, "closestRPI",fromPiI)
				self.addToStatesUpdateDict(dev.id, "closestRPIText",self.getRPIdevName(fromPiU) )
				self.addToStatesUpdateDict(dev.id, "closestRPILast",fromPiI)
				self.addToStatesUpdateDict(dev.id, "closestRPITextLast",self.getRPIdevName(fromPiU) )
				self.addToStatesUpdateDict(dev.id, "groupMember","BEACON")

				self.beacons[mac]["typeOfBeacon"] = "other"
				self.beacons[mac]["created"] = dateString
				self.beacons[mac]["expirationTime"] = self.secToDown
				self.beacons[mac]["lastUp"] = time.time()
				self.beacons[mac]["enabled"] = True

				self.executeUpdateStatesDict(onlyDevID=dev.id, calledFrom="updateBeaconStates new beacon")
				self.fixConfig(checkOnly = ["beacon"],fromPGM="updateBeaconStates new beacon") # updateBeaconStates
				if self.newBeaconsLogTimer >0:
					if time.time()> self.newBeaconsLogTimer:
						self.newBeaconsLogTimer =0
					else:
						self.indiLOG.log(10,"new beacon logging: created:{}".format(dateString.split(" ")[1])+" "+mac+" "+ name.ljust(20)+" "+ typeOfBeacon.ljust(25)+ "  pi#="+fromPiU+ " rssi={}".format(rssi)+ "  txPower={}".format(txPower))

				setALLrPiVUpdate = "updateParamsFTP"
				self.statusChanged = 15

				dev = indigo.devices[name]
				newStates = copy.copy(dev.states)
				self.setGroupStatusNextCheck = -1



		except Exception as e:
			if "{}".format(e).find("timeout waiting") > -1:
				self.exceptionHandler(40, e)
				self.indiLOG.log(40,"communication to indigo is interrupted")
			if e is not None and "{}".format(e).find("not found in database") ==-1:
				self.exceptionHandler(40, e)
			keepThisMessage = False


		return setALLrPiVUpdate, dev, props, newStates, keepThisMessage



####-------------------------------------------------------------------------####
	def autoCreateCorrespondingSensorDev(self, mac, fromPiU, typeOfBeacon, msg):
		try:
			# check if type is supported
			if typeOfBeacon not in self.knownBeaconTags["input"]:  return 

			verbose = mac == "xxxD1:AD:6B:3D:AB:2D"
			if verbose: self.indiLOG.log(20,"autoCreateCorrespondingSensorDev received mac:{}  typeOfBeacon:{}, isSwitchbotDevice:{},..{}?..{}?;  msg:{}".format(mac, typeOfBeacon, mac in self.isSwitchbotDevice,  mac in self.isBLESensorDevice,  mac in self.isBLElongConnectDevice, msg))
			# check if dev already exists
			if mac in self.isSwitchbotDevice: # only after it is already created
				try: 
					try:
						devBot = indigo.devices[self.isSwitchbotDevice[mac]]
					except:
						self.indiLOG.log(20,"autoCreateCorrespondingSensorDev removing mac:{} from switchbot dict".format(mac))
						del self.isSwitchbotDevice[mac]
						return 

						
					if typeOfBeacon in ["Switchbot", "SwitchbotCurtain", "SwitchbotCurtain3"]:
						botProps = devBot.pluginProps
						if verbose: self.indiLOG.log(20,"autoCreateCorrespondingSensorDev passed 2, from right piu:{}?".format(botProps.get("piServerNumber","") == fromPiU))
						if botProps.get("piServerNumber","") == fromPiU:

							if botProps.get("mac","") == mac:
								if  "analyzed" in msg and "ServiceData" in msg["analyzed"] and "ServiceData" in devBot.states:
									if msg["analyzed"]["ServiceData"] != devBot.states["ServiceData"]:
										self.addToStatesUpdateDict(devBot.id, "ServiceData", msg["analyzed"]["ServiceData"])

								if verbose: self.indiLOG.log(20,"mac:{}, fromPiU:{}, msg:{}".format(mac, fromPiU, msg))
								for xx in ["light", "calibrated", "position", "onOffState", "mode", "batteryLevel", "inMotion", "allowsConnection"]:
									if xx == "position": statename = "brightnessLevel"
									else:				 statename = xx 

									if xx == "onOffState" and xx in msg and xx in devBot.states:
										if "mode" in msg and msg["mode"] == "pressMode": msg[xx] = "off"
										onB = msg[xx] == "on"
										onT = "on"  if onB else "off"
										if  onB != devBot.states[statename]:
											self.addToStatesUpdateDict(devBot.id,"actualStatus",onT )
											self.addToStatesUpdateDict(devBot.id,"onOffState",	onB, uiValue= onT)
											if onB: devBot.updateStateImageOnServer(indigo.kStateImageSel.SensorOn)
											else:	devBot.updateStateImageOnServer(indigo.kStateImageSel.SensorOff)

									elif xx == "mode" and xx in msg and xx in devBot.states and msg[xx] != devBot.states[statename]:
										self.addToStatesUpdateDict(devBot.id, statename,	msg[xx] )


									elif xx == "inMotion" and xx in msg and xx in devBot.states and msg[xx] != devBot.states[statename]:
										if msg[xx]:
											self.delayedActions["data"].put({"actionTime":time.time()+10 , "devId":devBot.id,  "updateItems":[{"stateName":xx,"value":False}]})
										self.addToStatesUpdateDict(devBot.id, statename,	msg[xx] )


									elif xx == "position" and xx in msg and msg[xx] != "" and statename in devBot.states:
										if   msg[xx] < 10: uiValue = "open";	val = False
										elif msg[xx] > 90: uiValue = "closed";	val = True
										else:			   uiValue = "open";	val = False	

										self.addToStatesUpdateDict(devBot.id, statename,	msg[xx] )

										if "onOffState" in devBot.states:
											if devBot.deviceTypeId in ["OUTPUTswitchbotCurtain","OUTPUTswitchbotCurtain3"]:  # onOffstates confuses position and visa versa, cant switch it of for a dimmer device, so set text to "ignore"
												if botProps.get("onstateDisabled","") != "ignore":
													self.addToStatesUpdateDict(devBot.id,"onOffState", True, uiValue="ignore")
													botProps["onstateDisabled"] = "ignore"
													devBot.replacePluginPropsOnServer(botProps)
													#self.indiLOG.log(20,"mac:{}, fromPiU:{}, msg:{}\n props:{}, \nstates:{}".format(mac, fromPiU, msg,devBot, devBot.states))

											elif val != devBot.states["onOffState"]:
												self.addToStatesUpdateDict(devBot.id,"onOffState", val, uiValue=uiValue)

									elif xx in msg and msg[xx] != "" and statename in devBot.states and msg[xx] != devBot.states[statename]:
										self.addToStatesUpdateDict(devBot.id, statename,	msg[xx] )
								
								
								self.addToStatesUpdateDict(devBot.id, "lastUpdateBatteryLevel", datetime.datetime.now().strftime(_defaultDateStampFormat))
								self.executeUpdateStatesDict(onlyDevID=devBot.id, calledFrom="updateBeaconStates isSwitchbotDevice")
				except Exception as e:
					self.exceptionHandler(40, e)
				return		

			if mac in self.isBLESensorDevice: 		return 
			if mac in self.isBLElongConnectDevice: 	return 
			#indigo.server.log("mac:{}, msg:{}".format(mac, msg))

			newprops 							= {}
			sensorInfo 							= self.knownBeaconTags["input"][typeOfBeacon]
			isSens 								= False
			correspondingiTrackButtonDevice 	= sensorInfo.get("correspondingiTrackButtonDevice", "")
			correspondingShellyButtonDevice 	= sensorInfo.get("correspondingShellyButtonDevice", "")
			correspondingBLEConnectSensorType 	= sensorInfo.get("correspondingBLEConnectSensorType", "")
			correspondingSensorType 			= sensorInfo.get("correspondingSensorType", "")
			correspondingSwitchbotDevice 		= sensorInfo.get("correspondingSwitchbotDevice", "")
			subtypeOfBeacon 					= msg.get("subtypeOfBeacon", "")
			
			if subtypeOfBeacon != "":
				for tag in self.knownBeaconTags["input"]:
					if "subtypeOfBeacon" not in self.knownBeaconTags["input"][tag]: continue
					if "devTypeID" not in self.knownBeaconTags["input"][tag]["subtypeOfBeacon"]: continue
					for subtypeID in self.knownBeaconTags["input"][tag]["subtypeOfBeacon"]["devTypeID"]:
						if self.knownBeaconTags["input"][tag]["subtypeOfBeacon"]["devTypeID"][subtypeID] == subtypeOfBeacon:
							correspondingSensorType = tag
							break

			if correspondingSensorType == "" and correspondingBLEConnectSensorType == "" and correspondingSwitchbotDevice == "" and correspondingiTrackButtonDevice == "" and correspondingShellyButtonDevice == "": return   

			textHint = sensorInfo.get("text","")
			if subtypeOfBeacon != "":
				for devTest in indigo.devices.iter("props.isBLESensorDevice"):
					if mac == devTest.pluginProps.get("mac","xx"):
						return 
				devType 									= subtypeOfBeacon
				if devType.find("-on") == -1:
					isSens 										= True
				newprops["isBLESensorDevice"]				= True
				name 										= "s-{}-{}-{}".format(devType, mac, fromPiU)

			elif correspondingSensorType != "":
				for devTest in indigo.devices.iter("props.isBLESensorDevice"):
					if mac == devTest.pluginProps.get("mac","xx"):
						return 
				devType 									= correspondingSensorType
				isSens 										= True
				newprops["isBLESensorDevice"]				= True
				name 										= "s-{}-{}-{}".format(devType, mac, fromPiU)

			elif correspondingBLEConnectSensorType != "":
				for devTest in indigo.devices.iter("props.isBLElongConnectDevice"):
					if mac == devTest.pluginProps.get("mac","xx"):
						return 
				devType										= correspondingBLEConnectSensorType
				isSens 										= True
				newprops["isBLElongConnectDevice"]			= True
				name 										= "s-{}-{}-{}".format(devType, mac, fromPiU)

			elif correspondingSwitchbotDevice != "":
				for devTest in indigo.devices.iter("props.isSwitchbotDevice"):
					if mac == devTest.pluginProps.get("mac","xx"):
						return 
				devType 									= correspondingSwitchbotDevice
				newprops["isSwitchbotDevice"]				= True
				name 										= "o-{}-{}-{}".format(devType, mac, fromPiU)

			elif correspondingiTrackButtonDevice != "":
				for devTest in indigo.devices.iter("props.isBLESensorDevice"):
					if mac == devTest.pluginProps.get("mac","xx"):
						return 
				devType 									= correspondingiTrackButtonDevice
				newprops["isBLESensorDevice"]				= True
				name 										= "b-{}-{}-{}".format(devType, mac, fromPiU)

			elif correspondingShellyButtonDevice != "":
				for devTest in indigo.devices.iter("props.isBLESensorDevice"):
					if mac == devTest.pluginProps.get("mac","xx"):
						return 
				isSens 										= True
				devType 									= correspondingShellyButtonDevice
				newprops["isBLESensorDevice"]				= True
				name 										= "b-{}-{}-{}".format(devType, mac, fromPiU)

			else:
				return 
			# does not exist and type is supported: create corresponding BLE sensor device 


			self.indiLOG.log(20,"checking if new sensor dev is needed mac:{}, msg:{}, BLEConnect:{}, SensorType:{}, SwitchbotDevice:{}, subtypeOfBeacon:{} devType:{}".format(mac, msg, correspondingBLEConnectSensorType, correspondingSensorType, correspondingSwitchbotDevice, subtypeOfBeacon, devType))

			# set what should be displayed in status column
			temp 	= False
			hum 	= False
			press 	= False
			accell	= False
			motion 	= False
			contact = False
			formal 	= False
			cond 	= False
			illum 	= False
			moist 	= False
			swit	= False
			button	= False

			if textHint.lower().find("temp") > -1:		temp 	= True
			if textHint.lower().find("hum") > -1:		hum 	= True
			if textHint.lower().find("accell") > -1:	accell 	= True
			if textHint.lower().find("contact") > -1:	contact = True
			if textHint.find("switch") > -1: 			swit	= True
			if textHint.lower().find("moti") > -1:		motion 	= True
			if textHint.lower().find("formal") > -1:	formal 	= True
			if textHint.lower().find("button") > -1:	button 	= True

			if devType.lower().find("temp") > -1:		temp 	= True
			if devType.lower().find("press") > -1:		press 	= True
			if devType.lower().find("hum") > -1: 		hum 	= True
			if devType.lower().find("moti") > -1:		motion 	= True
			if devType.lower().find("contact") > -1:	contact = True
			if devType.lower().find("formal") > -1:		formal 	= True
			if devType.lower().find("Cond") > -1:		cond 	= True
			if devType.lower().find("Illum") > -1:		illum 	= True
			if devType.lower().find("Moist") > -1:		moist 	= True
			if devType.lower().find("button") > -1:		button 	= True

			newprops["mac"] 								= mac
			if isSens:
				newprops["isSensorDevice"] 					= True
				if devType != "SwitchbotContact" and correspondingShellyButtonDevice == "" and devType.find("-on") == --1:
					newprops["SupportsSensorValue"] 		= True
				else:
					newprops["SupportsSensorValue"] 		= False

				newprops["SupportsStatusRequest"] 			= False
				newprops["AllowOnStateChange"] 				= False
				newprops["AllowSensorValueChange"] 			= False
				newprops["SupportsBatteryLevel"] 			= True
				newprops["SupportsOnState"] 				= motion or contact or swit or button or devType.find("-on") >-1
				rPiEnable 									= "rPiEnable{}".format(fromPiU)
				newprops[rPiEnable]							= True
			if swit:
				newprops["isOutputDevice"] 					= True
				newprops["SupportsStatusRequest"] 			= True
				newprops["SupportsBatteryLevel"] 			= True
				newprops["piServerNumber"]					= "{}".format(fromPiU)
				rPiEnable 									= "rPiEnable{}".format(fromPiU)
				newprops[rPiEnable]							= True

			if button and  correspondingShellyButtonDevice == "":
				newprops["SupportsBatteryLevel"] 			= False


			newprops["noI2cCheck"] 							= True

			if moist:
				newprops["displayS"]						= "Moisture"

			elif formal:
				newprops["displayS"]						= "Formaldehyde"

			elif temp:
				newprops["displayS"]						= "Temperature"

			elif illum:
				newprops["displayS"]						= "illuminance"

			else:
				newprops["displayS"]						= ""

			if isSens:
				if temp: newprops["offsetTemp"]				= "0"
				if hum: newprops["offsetHum"]				= "0"
				if press: newprops["offsetPress"]			= "0"
				descr = "on Pi:{}".format(fromPiU)
				newprops["isBLESensorDevice"]				= True
			else:
				descr = mac
			newprops["minSendDelta"]						= "4"
			newprops["updateIndigoTiming"]					= "60"
			newprops["updateIndigoDeltaTemp"]				= "1.0"
			newprops["stateGreen"]							= ""
			newprops["stateGrey"]							= ""
			newprops["stateRed"]							= ""
			newprops["isBLESensorDevice"]					= True

			if accell:
				newprops["updateIndigoDeltaAccelVector"] 	= "50"
				newprops["updateIndigoDeltaMaxXYZ"]			= "50"

			self.indiLOG.log(30,"corresponding BLE-sensor device not found, will try to create one:{}.. details in plugin.log".format(name))
			self.indiLOG.log(30,"=====> please finish setup for new device {} in device edit, ie which RPI this device is linked to;  etc<=== ".format(name))
			self.indiLOG.log(10,"... beacontype: {}".format(typeOfBeacon))
			self.indiLOG.log(10,"... info:       {}".format(self.knownBeaconTags["input"][typeOfBeacon]))
			self.indiLOG.log(10,"... props:      {}".format(newprops))

			try:
				dev = indigo.device.create(
					protocol		= indigo.kProtocol.Plugin,
					address			= mac,
					name			= name,
					description		= descr,
					pluginId		= self.pluginId,
					deviceTypeId	= devType,
					folder			= self.piFolderId,
					props			= newprops
					)
			except Exception as e:
				self.exceptionHandler(40, e)
				self.indiLOG.log(40,"name: {}".format(name))
				return 

			dev.updateStateOnServer("created", datetime.datetime.now().strftime(_defaultDateStampFormat) )
			if "lastSensorChange" in dev.states:
				dev.updateStateOnServer("lastSensorChange", datetime.datetime.now().strftime(_defaultDateStampFormat) )

			if correspondingSensorType != "":
				self.isBLESensorDevice[mac]			= dev.id

			elif correspondingBLEConnectSensorType != "":
				self.isBLElongConnectDevice[mac]	= dev.id

			elif correspondingSwitchbotDevice != "":
				self.isSwitchbotDevice[mac]			= dev.id
				if correspondingSwitchbotDevice in ["OUTPUTswitchbotCurtain","OUTPUTswitchbotCurtain3","OUTPUTswitchbotRelay"]:
					props = dev.pluginProps
					props["address"] ="Pi-"+fromPiU
					props["piServerNumber"] = fromPiU
					props["suppressQuickSecond"] = "-10"
					dev.replacePluginPropsOnServer(props)
					#self.indiLOG.log(20,"updated props: {}".format(dev.pluginProps))
					if "output" not in self.RPI[fromPiU]: 					self.RPI[fromPiU]["output"] 			= {}
					if devType not in self.RPI[fromPiU]["output"]: 			self.RPI[fromPiU]["output"][devType] 	= {}
					self.RPI[fromPiU]["output"][devType]["{}".format(dev.id)] 										= {"modeOfDevice":"donotset", "holdSeconds": "-1", "mac":mac,"suppressQuickSecond":-10}

			if   newprops["displayS"] in ["Temperature"]: 					dev.updateStateImageOnServer(indigo.kStateImageSel.TemperatureSensorOn)
			elif newprops["displayS"] in ["Moisture","Formaldehyde"]:		dev.updateStateImageOnServer(indigo.kStateImageSel.HumiditySensorOn)
			elif newprops["displayS"] in ["illuminance"]:					dev.updateStateImageOnServer(indigo.kStateImageSel.LightSensorOn)
			else:															dev.updateStateImageOnServer(indigo.kStateImageSel.TemperatureSensor)

			self.setONErPiV(fromPiU,"piUpToDate", ["updateParamsFTP"])
				#indigo.server.log("devtype:{}, RPI dict:{}<".format(devType, self.RPI[fromPiU]))
			self.setGroupStatusNextCheck = -1

		except Exception as e:
			self.exceptionHandler(40, e)
		return 

####-------------------------------------------------------------------------####
	def checkBeaconDictIfok(self, mac, dateString, rssi, fromPiU, msg, keepNew, acceptMAC):
		try:
			if (mac in self.beacons and self.beacons[mac]["ignore"] >0 ):
				if self.decideMyLog("BeaconData"): self.indiLOG.log(5," rejected beacon because its in reject family: pi: {}; beacon: {}".format(fromPiU, msg) )
				return False  # ignore certain type of beacons, but only for new ones, old ones must be excluded individually

			if mac not in self.beacons:
				if  rssi >  self.acceptNewiBeacons or keepNew or acceptMAC:
					self.beacons[mac] = copy.deepcopy(_GlobalConst_emptyBeacon)
					self.beacons[mac]["created"] = dateString
					self.beacons[mac]["lastUp"]  = time.time()
				else:
					self.indiLOG.log(10," rejected beacon because do not accept new beacons is on or rssi:{}<{};  types{};{}; pi:{}; beaconMSG:{} ".format(rssi, self.acceptNewiBeacons, type(rssi), type(self.acceptNewiBeacons), fromPiU, msg))
					return False
			else:
				if self.beacons[mac]["ignore"] == 0 and self.beacons[mac]["indigoId"] == 0 and keepNew:
					self.beacons[mac] = copy.deepcopy(_GlobalConst_emptyBeacon)
					self.beacons[mac]["created"] = dateString
					self.beacons[mac]["lastUp"]  = time.time()
					self.beacons[mac]["ignore"] = -1
					self.indiLOG.log(10,"new beacon from type ID (2)  rssi:{}<{};   pi:{}; typeID:{}; beaconMSG:{} ".format(rssi, self.acceptNewiBeacons, fromPiU, self.acceptNewTagiBeacons, msg))
				if not self.beacons[mac]["enabled"]: return False

			if self.beacons[mac]["ignore"] > 0: 	return False

			return True

		except Exception as e:
			if "{}".format(e).find("timeout waiting") > -1:
				self.exceptionHandler(40, e)
				self.indiLOG.log(40,"communication to indigo is interrupted")
			if e is not None	and "{}".format(e).find("not found in database") ==-1:
				self.exceptionHandler(40, e)
		return  False


####-------------------------------------------------------------------------####
	def updateBeaconStates(self, fromPi, piNReceived, ipAddress, piMACSend, nOfSecs, msgs):

		try:
			setALLrPiVUpdate = ""
			beaconUpdatedIds = []
			ln = len(msgs)
			if ln < 1: 
				self.indiLOG.log(30,"updateBeaconStates: message rejected RPI piMACSend: {}; pi#: {:2s}; MSGS EMPTY:{}".format(piMACSend, fromPiU, msgs) )
				return beaconUpdatedIds
			dateString = datetime.datetime.now().strftime(_defaultDateStampFormat)

			newRPI			= ""
			fromPiU 		= "{}".format(fromPi)
			fromPiI			= int(fromPi)
			piNReceived		= "{}".format(piNReceived)
			if self.selectBeaconsLogTimer !={}:
				for sMAC in self.selectBeaconsLogTimer:
					if piMACSend.find(sMAC[:self.selectBeaconsLogTimer[sMAC]]) ==0:
						self.indiLOG.log(10,"sel.beacon logging: RPI msg: {}; pi#: {:2s};  {:}".format(piMACSend, fromPiU, msgs) )

			# rpi
			keepThisMessage, beaconUpdatedIds = self.handleRPIMessagePart(piMACSend, newRPI, fromPiU, piNReceived, ipAddress, dateString, beaconUpdatedIds)
			if  keepThisMessage !=0:
				self.indiLOG.log(30,"message rejected RPI piMACSend: {}; pi#: {:2s};  reason:{}, msg:{}".format(piMACSend, fromPiU, keepThisMessage, msgs) )
				return beaconUpdatedIds


			###########################	 ibeacons ############################
			#### ---- update ibeacon info
			for msg in msgs:
				if self.decideMyLog("BeaconData"): self.indiLOG.log(5,"updateBeaconStates new iBeacon message 2 \n {}".format(msg) )
				if True: # get data from message
					if type(msg) != type({}): continue
					mac		= msg["mac"].upper()
					reason	= msg["reason"]
					mfgName	= msg.get("mfg_info","")
					if "typeOfBeacon" not in msg:
						self.indiLOG.log(10,"msg not complete  mac:{}; pi#={:2s}; msg:{}".format(mac, fromPiU, msg) )
						continue
					typeOfBeacon = msg["typeOfBeacon"]
					keepNew = (self.acceptNewTagiBeacons == "all" and typeOfBeacon in self.knownBeaconTags["input"]) or typeOfBeacon == self.acceptNewTagiBeacons or ( len(self.acceptNewMFGNameBeacons) >1 and mfgName.lower().find(self.acceptNewMFGNameBeacons.lower()) == 0 )
					acceptMAC   = mac == self.acceptNewBeaconMAC
					if acceptMAC:
						self.acceptNewBeaconMAC = ""
						self.updateNeeded += " fixConfig "
					try:	rssi = float(msg["rssi"])
					except: rssi = -999.
					txPower = msg["txPower"]
					lCount	= msg["count"]
					rssiOffset = 0
					if rssi == -999 :
						txPower = 0
					else:
						try:	rssiOffset = float(self.RPI[fromPiU]["rssiOffset"] )
						except: rssiOffset = 0
					try:	batteryLevel = int(msg["batteryLevel"])
					except: batteryLevel = ""
					try:	iBeacon	 = msg["iBeacon"]
					except: iBeacon  = ""
					if "mfg_info" in msg: 	mfg_info = msg["mfg_info"]
					else:					mfg_info = ""
					if "TLMenabled" in msg: TLMenabled = msg["TLMenabled"]
					else:					TLMenabled = False


				if self.selectBeaconsLogTimer !={}:
					for sMAC in self.selectBeaconsLogTimer:
						if mac.find(sMAC[:self.selectBeaconsLogTimer[sMAC]]) ==0:
							self.indiLOG.log(10,"sel.beacon logging: newMSG    -1  - :{}; pi#={:2s}; msg{}".format(mac, fromPiU, msg) )

				if not self.checkBeaconDictIfok( mac, dateString, rssi, fromPiU, msg, keepNew, acceptMAC): continue

				if self.selectBeaconsLogTimer !={}:
					for sMAC in self.selectBeaconsLogTimer:
						if mac.find(sMAC[:self.selectBeaconsLogTimer[sMAC]]) ==0:
							self.indiLOG.log(10,"sel.beacon logging: newMSG    -1a - :{}; after checkBeaconDictIfok".format(mac))


				setALLrPiVUpdate, dev, props, newStates, keepThisMessage = self.getBeaconDeviceAndCheck( mac, typeOfBeacon, rssi, txPower, fromPiU, piMACSend, dateString, rssiOffset)
				if not keepThisMessage:  continue
				if self.selectBeaconsLogTimer !={}:
					for sMAC in self.selectBeaconsLogTimer:
						if mac.find(sMAC[:self.selectBeaconsLogTimer[sMAC]]) ==0:
							self.indiLOG.log(10,"sel.beacon logging: newMSG    -1b - :{}; after getBeaconDeviceAndCheck".format(mac))


				self.addToStatesUpdateDict(dev.id, "updateReason", reason)

				if iBeacon  != "" and "iBeacon"  in dev.states:						newStates = self.addToStatesUpdateDict(dev.id, "iBeacon", iBeacon, newStates=newStates)
				if mfg_info != "" and "mfg_info" in dev.states:						newStates = self.addToStatesUpdateDict(dev.id, "mfg_info", mfg_info, newStates=newStates)

				oldTag = dev.states.get("typeOfBeacon","")

				#if dev.id == 970830152: self.indiLOG.log(20,"capable ..   typeOfBeacon: {}, states:{}; props:{}".format(typeOfBeacon, dev.states.get("typeOfBeacon","other", props.get("version","")) )  )
				if (oldTag == "" and typeOfBeacon != "" ) or (oldTag == "other" and typeOfBeacon not in ["other",""]):
							newStates = self.addToStatesUpdateDict(dev.id, "typeOfBeacon", typeOfBeacon, newStates=newStates)
							if dev.deviceTypeId != "rPI":
								newStates = self.addToStatesUpdateDict(dev.id, "note", "beacon-"+typeOfBeacon, newStates=newStates)
							self.beacons[mac]["typeOfBeacon"] = typeOfBeacon
							props["typeOfBeacon"] = typeOfBeacon
							props["version"] = typeOfBeacon
							dev.replacePluginPropsOnServer(props)
							setALLrPiVUpdate = "updateParamsFTP"
				elif props.get("version","") != oldTag:
					props["version"] = typeOfBeacon
					dev.replacePluginPropsOnServer(props)
				if dev.deviceTypeId != "rPI":
					if "beacon-"+oldTag != dev.states.get("note",""):
						newStates = self.addToStatesUpdateDict(dev.id, "note", "beacon-"+oldTag, newStates=newStates)

				if TLMenabled and ("batteryLevelUUID" not in props or props["batteryLevelUUID"] == "off"):
					props["SupportsBatteryLevel"] = True
					props["batteryLevelUUID"]     = "TLM-3000-2800"
					dev.replacePluginPropsOnServer(props)

				#if dev.id == 739817084: self.indiLOG.log(20,"739817084   batteryLevel: {}, type:{}".format(batteryLevel, type(batteryLevel))  )
				if batteryLevel != "" and type(batteryLevel) == type(1):
					if  "batteryLevel" not in dev.states:
						if not props["SupportsBatteryLevel"]:
							props["SupportsBatteryLevel"] = True
							if TLMenabled:
								props["batteryLevelUUID"] 	= "TLM-3000-2800"
							else:
								props["batteryLevelUUID"] 	= "msg"
							dev.replacePluginPropsOnServer(props)
							self.sleep(0.5)
							dev = indigo.devices[dev.id]
							props = dev.pluginProps

					if  "batteryLevel" in dev.states:
						#if dev.id == 739817084: self.indiLOG.log(20,"739817084  adding  batteryLevel: to states update " )
						newStates = self.addToStatesUpdateDict(dev.id, "batteryLevel", batteryLevel, newStates=newStates)
						newStates = self.addToStatesUpdateDict(dev.id, "lastUpdateBatteryLevel", datetime.datetime.now().strftime(_defaultDateStampFormat), newStates=newStates)
						self.setlastBatteryReplaced(dev, batteryLevel)

				self.autoCreateCorrespondingSensorDev(mac, fromPiU, typeOfBeacon, msg)

				self.checkForFastDown(mac, piMACSend, dev, props, rssi, fromPiU, newStates)

				# thsi enables better / faster location bounding to only specific room/ rpi
				logTRUEfromSignal = False
				if self.trackSignalStrengthIfGeaterThan[0] <99.:
					try:
						deltaSignalLOG = (rssi + rssiOffset - float(self.beacons[mac]["receivedSignals"][fromPiI]["rssi"]))
						if self.trackSignalStrengthIfGeaterThan[1] == "i":
							logTRUEfromSignal =	 ( abs(deltaSignalLOG) > self.trackSignalStrengthIfGeaterThan[0]  ) or	(rssi ==-999. and float(self.beacons[mac]["receivedSignals"][fromPiI]["rssi"]) !=-999)
						else:
							logTRUEfromSignal =	 ( abs(deltaSignalLOG) > self.trackSignalStrengthIfGeaterThan[0]  ) and ( rssi !=-999 and self.beacons[mac]["receivedSignals"][fromPiI]["rssi"] !=-999)

					except Exception as e:

						self.exceptionHandler(40, e)
						logTRUEfromSignal = False



				updateSignal, newStates, logTRUEfromChangeOFRPI, oldRPI, closestRPI, beaconUpdatedIds = self.handleBeaconRealSignal(mac, piMACSend, dev, props, beaconUpdatedIds, rssi, txPower, rssiOffset, fromPiU, newStates, dateString )


				if self.selectBeaconsLogTimer !={}:
					for sMAC in self.selectBeaconsLogTimer:
						if mac.find(sMAC[:self.selectBeaconsLogTimer[sMAC]]) ==0:
							self.indiLOG.log(10,"sel.beacon logging: newMSG    -3  - :{}; bf cars".format(mac))

				if self.selectBeaconsLogTimer !={}:
					for sMAC in self.selectBeaconsLogTimer:
						if mac.find(sMAC[:self.selectBeaconsLogTimer[sMAC]]) ==0:
							self.indiLOG.log(10,"sel.beacon logging: newMSG    -4  - :{}; bf calc dist".format(mac))

				if updateSignal and "note" in dev.states and dev.states["note"].find("beacon") >-1:
					try:
						props = dev.pluginProps
						expirationTime = float(props["expirationTime"])
						update, deltaDistance = self.calcPostion(dev, expirationTime, rssi=rssi)
						if ( update or (deltaDistance > self.beaconPositionsdeltaDistanceMinForImage) ) and "showBeaconOnMap" in props and props["showBeaconOnMap"] in _GlobalConst_beaconPlotSymbols:
							#self.indiLOG.log(10,"beaconPositionsUpdated; calcPostion:"+name+" pi#="+fromPiU	  +"   deltaDistance:{}".format(deltaDistance)	  +"   update:{}".format(update)  )
							self.beaconPositionsUpdated =6

					except Exception as e:
						if "{}".format(e) != "None":
							self.exceptionHandler(40, e)

				if self.newBeaconsLogTimer > 0:
						try:
							created = self.getTimetimeFromDateString(dev.states["created"])
							if created + self.newBeaconsLogTimer > 2*time.time():
								self.indiLOG.log(10,"new.beacon logging: newMSG     -2- :"+mac+";  "+dev.name+ " pi#="+fromPiU +";  #Msgs={}".format(lCount).ljust(2)    + "  rssi={}".format(rssi).rjust(6)      +"                      txPow={}".format(txPower).rjust(6)+" cr="+dev.states["created"]+" typeOfBeacon="+ typeOfBeacon)
							if self.newBeaconsLogTimer < time.time():
								self.indiLOG.log(10,"new.beacon logging: resetting  newBeaconsLogTimer to OFF")
								self.newBeaconsLogTimer =0
						except Exception as e:
							self.exceptionHandler(40, e)

				if self.selectBeaconsLogTimer !={}:
					for sMAC in self.selectBeaconsLogTimer:
						if mac.find(sMAC[:self.selectBeaconsLogTimer[sMAC]]) ==0:
							self.indiLOG.log(10,"sel.beacon logging: newMSG    -5  - :{}; passed".format(mac))

				if logTRUEfromChangeOFRPI:
					self.indiLOG.log(10,"ChangeOfRPI.beacon logging     :"+mac+"  "+dev.name       + " pi#={}".format(closestRPI)+" oldpi={}".format(oldRPI)+";   #Msgs={}".format(lCount).ljust(2)    + "  rssi={}".format(rssi).rjust(6)    + "                        txPow={}".format(txPower).rjust(6))

				if logTRUEfromSignal:
					if abs(deltaSignalLOG)	 > 500 and rssi > -200:
						self.indiLOG.log(10,"ChangeOfSignal.beacon logging:        "+mac+";  "+dev.name+ " pi#="+fromPiU     +";  #Msgs={}".format(lCount).ljust(2)     +"  rssi={}".format(rssi).rjust(6)         + " off --> ON             txPow={}".format(txPower).rjust(6))
					elif abs(deltaSignalLOG) > 500 and rssi < -200:
						self.indiLOG.log(10,"ChangeOfSignal.beacon logging:        "+mac+";  "+dev.name+ " pi#="+fromPiU     +";  #Msgs={}".format(lCount).ljust(2)     +"  rssi={}".format(rssi).rjust(6)         + " ON  --> off            txPow={}".format(txPower).rjust(6))
					else:
						self.indiLOG.log(10,"ChangeOfSignal.beacon logging:        "+mac+";  "+dev.name+ " pi#="+fromPiU     +";  #Msgs={}".format(lCount).ljust(2)     +"  rssi={}".format(rssi).rjust(6)         + " new-old_Sig.= {}".format(deltaSignalLOG).rjust(5)+ "     txPow={}".format(txPower).rjust(6))

				self.executeUpdateStatesDict(onlyDevID=dev.id, calledFrom="updateBeaconStates 1")


		except Exception as e:

			if "{}".format(e).find("timeout waiting") > -1:
				self.exceptionHandler(40, e)
				self.indiLOG.log(40,"communication to indigo is interrupted")
				return
			if e is not None	and "{}".format(e).find("not found in database") ==-1:
				self.exceptionHandler(40, e)

		if setALLrPiVUpdate == "updateParamsFTP":
			self.setALLrPiV("piUpToDate", ["updateParamsFTP"])


		return beaconUpdatedIds



####-------------------------------------------------------------------------####
	def manageDescription(self, existing, newFirstPart):
		try:
			newresult  = existing.split(" ")
			if newresult[0] == newFirstPart: return existing
			newresult[0] = newFirstPart
			return " ".join(newresult)
		except Exception as e:
			self.exceptionHandler(40, e)
		return existing


####-------------------------------------------------------------------------####
	def getRPIdevName(self, closestRPI):
		closestRPIText =""
		if closestRPI != "-1":
			try: closestRPIText = indigo.devices[int(self.RPI["{}".format(closestRPI)]["piDevId"])].name
			except: pass
		return closestRPIText



####-------------------------------------------------------------------------####
	####calc distance from received signal and transmitted power assuming Signal ~ Power/r**2---------
	def findClosestRPI(self,mac,deviBeacon):
		try:
			if mac				  not in self.beacons:		return -2
			if "receivedSignals" not in self.beacons[mac]: return -3
			if "closestRPI"	  not in deviBeacon.states: return -4
		except:
															return -5
		newMinDist   = 99999.
		currMinDist  = 99999.
		newClosestRPI  = -1
		currClosestRPI = -1


		try:
			currClosestRPI	= int(deviBeacon.states["closestRPI"])
			if currClosestRPI !=-1	and (time.time() - self.beacons[mac]["receivedSignals"][currClosestRPI]["lastSignal"]) <70.: # ["receivedSignals"] =[rssi, timestamp,dist]
				currMinDist	= self.beacons[mac]["receivedSignals"][currClosestRPI]["distance"]
		except Exception as e:
			self.exceptionHandler(40, e)
			currClosestRPI =-1; currMinDist = -9999.

		for sMAC in self.selectBeaconsLogTimer:
			if mac.find(sMAC[:self.selectBeaconsLogTimer[sMAC]]) ==0:
				self.indiLOG.log(10,"sel.beacon logging: ClostR 1        :{}; currClosestRPIL:{}, newClosestRPI:{},  newMinDist:{}   currMinDist:{}".format(mac, currClosestRPI, newClosestRPI, newMinDist,  currMinDist))


		try:
			for piU in _rpiBeaconList:
				pi = int(piU)
				if self.RPI[piU]["piOnOff"] != "0":
					bbb = self.beacons[mac]["receivedSignals"][pi]
					try: # if empty field skip
						if time.time() - bbb["lastSignal"]  < 100.:  # signal recent enough
							if bbb["rssi"] > -300:
								if bbb["distance"] < newMinDist:
									newMinDist   = bbb["distance"]
									newClosestRPI  = pi
						for sMAC in self.selectBeaconsLogTimer:
							if False and mac.find(sMAC[:self.selectBeaconsLogTimer[sMAC]]) ==0:
								self.indiLOG.log(10,"sel.beacon logging: ClostR 2 :{}; piU:{}, t-lastSignal:{}, distance:{}; newClosestRPI:{}".format(mac,piU,  time.time() - bbb["lastSignal"],  bbb["distance"], newClosestRPI) )
					except:
						pass
			# dont switch if: <	 4 dBm diff and	 not defined then keep current

			#if deviBeacon.states["note"].find("Pi-") > -1: self.indiLOG.log(10,"checking for clostest RPI- {} {} {} {} ".format(mac, deviBeacon.name, newClosestRPI, newMinDist))

			if abs(newMinDist - currMinDist)  < 0.5 and  currClosestRPI !=-1: #
				newClosestRPI = currClosestRPI
			for sMAC in self.selectBeaconsLogTimer:
				if mac.find(sMAC[:self.selectBeaconsLogTimer[sMAC]]) ==0:
					self.indiLOG.log(10,"sel.beacon logging: ClostR 3        :{}; currClosestRPI:{}, newClosestRPI:{},  newMinDist:{}   currMinDist:{}".format(mac, currClosestRPI, newClosestRPI, newMinDist,  currMinDist) )

		except Exception as e:
			self.exceptionHandler(40, e)
		return newClosestRPI


#		####calc distance from received signal and transmitted power assuming Signal ~ Power/r**2---------
####-------------------------------------------------------------------------####
	def findClosestRPIForBLEConnect(self, devBLE, pi, dist):
		if self.decideMyLog("BLE"): self.indiLOG.log(5,"findClosestRPIForBLEConnect into   dev:{}, pi:{}, dist:{}".format(devBLE.name, pi, dist) )
		if "closestRPI" not in devBLE.states: return -4

		newMinDist     = 99999.
		currMinDist    = 99999.
		newClosestRPI  = -1
		currClosestRPI = -1

		try:

			currClosestRPI	= int(devBLE.states["closestRPI"])
			piXX = "Pi_{:02d}".format(currClosestRPI)
			if currClosestRPI != -1:
				deltaSec = time.time() - self.getTimetimeFromDateString(devBLE.states[piXX+"_Time"])
				if deltaSec < 120.:
					currMinDist	= devBLE.states[piXX+"_Distance"]
		except:
			currClosestRPI =-1
			currMinDist = 9999.

		newMinDist    = dist
		newClosestRPI = int(pi)

		activePis = self.getActiveBLERPI(devBLE)
		#indigo.server.log(devBLE.name+ " activePis {}".format(activePis))

		try:
			for piU in _rpiBeaconList:
				pix = int(piU)
				if pix not in activePis: 				continue
				if self.RPI[piU]["piOnOff"] == "0": 	continue
				piXX = "Pi_{:02d}".format(pix)
				try: # if empty field skip
					deltaSec = time.time() - self.getTimetimeFromDateString(devBLE.states[piXX+"_Time"])
					if deltaSec  < 120.:  # signal recent enough
						if float(devBLE.states[piXX+"_Distance"]) <  newMinDist:
								newMinDist   =  float(devBLE.states[piXX+"_Distance"])
								newClosestRPI  = pix
					if self.decideMyLog("BLE"): self.indiLOG.log(5,"findClosestRPIForBLEConnect loop pi:{}, newClosestRPI:{}, devdist:{}, newDist:{} deltaS:{}".format(piU, newClosestRPI, devBLE.states[piXX+"_Distance"],newMinDist, deltaSec ) )
				except Exception as e:
					if "{}".format(e) != "None":
						self.indiLOG.log(40,"Line {} has error={}".format(sys.exc_info()[2].tb_lineno, e) )
			# dont switch if: <	 4 dBm diff and	 not defined then keep current
			if abs(newMinDist - currMinDist) < 2 and  currClosestRPI !=-1: #
				newClosestRPI = currClosestRPI
		except Exception as e:
			self.exceptionHandler(40, e)
		if self.decideMyLog("BLE"): self.indiLOG.log(5,"findClosestRPIForBLEConnect return w  newClosestRPI:{}".format(newClosestRPI) )

		return newClosestRPI


####-------------------------------------------------------------------------####
	def calcDist(self, power, rssi):
		try:
			power = float(power)
			if power > 100: return 99999.
			rssi = float(rssi)
			if rssi > 100:	return 99999.
			if rssi < -105: return 99999.

			# sqrt( 10**(  (p-s)/10 )  ) = 10**((p-s/20)  (sqrt replace with **1/2	;  **1/10 ==> **1/20)
			exp = max( (power - rssi), -40.) / 20.
			dist = min(  99999., math.pow(10.0, exp)  )
			dist = round(dist, 1)
			###self.indiLOG.log(10, "{}".format(power)+"  {}".format(rssi) +" {}".format(dist))
			return dist

		except	 Exception as e:
			self.exceptionHandler(40, e)
		return 99999.


	def getActiveBLERPI(self, dev):
		xx = dev.description.lower().split("pi")
		activePis =[]
		if len(xx) == 2:
			xx = xx[1].split(",")
			for x in xx:
				try: activePis.append( int(x.replace(" ","") ) )
				except: pass
		else:
			activePis =[]
		return activePis

####-------------------------------------------------------------------------####
	def sendGPIOCommand(self, ip, pi, typeId, cmd, GPIOpin=0, pulseUp=0, pulseDown=0, nPulses=0, analogValue=0,rampTime=0, i2cAddress=0,text="",soundFile="",restoreAfterBoot="0",startAtDateTime=0, inverseGPIO=False, devId=0):
		cmd1 =""
		try:
			if cmd in["updateTimeAndZone", "beepBeacon", "getBeaconParameters", "resetDevice", "startCalibration", "newMessage"]:
				cmd1 = {"device": typeId, "command":cmd, "startAtDateTime": startAtDateTime}
			elif cmd == "BLEAnalysis":
				cmd1 = {"minRSSI": typeId, "command":cmd, "startAtDateTime": startAtDateTime}
			elif cmd == "trackMac":
				cmd1 = {"mac": typeId, "command":cmd, "startAtDateTime": startAtDateTime}
			else:
				if typeId == "setMCP4725":
					cmd1 = {"device": typeId, "command": cmd, "i2cAddress": i2cAddress, "values":{"analogValue":analogValue,"rampTime":rampTime,"pulseUp":pulseUp,"pulseDown": pulseDown,"nPulses":nPulses},"restoreAfterBoot": restoreAfterBoot, "startAtDateTime": startAtDateTime, "devId": devId}

				elif typeId == "setPCF8591dac":
					cmd1 = {"device": typeId, "command": cmd, "i2cAddress": i2cAddress, "values":{"analogValue":analogValue,"rampTime":rampTime,"pulseUp":pulseUp,"pulseDown": pulseDown,"nPulses":nPulses},"restoreAfterBoot": restoreAfterBoot, "startAtDateTime": startAtDateTime, "devId": devId}

				elif typeId == "myoutput":
					cmd1 = {"device": typeId, "command": "myoutput", "text": text, "restoreAfterBoot": restoreAfterBoot, "startAtDateTime": startAtDateTime, "devId": devId}

				elif typeId == "playSound":
					cmd1 = {"device": typeId, "command": cmd, "soundFile": soundFile, "startAtDateTime": startAtDateTime, "devId": devId}

				elif typeId.find("OUTPUTgpio") > -1:
					if cmd == "up" or cmd == "down":
						cmd1 = {"device": typeId, "command": cmd, "pin": GPIOpin, "restoreAfterBoot": restoreAfterBoot, "startAtDateTime": startAtDateTime, "inverseGPIO": inverseGPIO, "devId": devId}
					elif cmd in["pulseUp", "pulseDown", "continuousUpDown", "analogWrite"]:
						cmd1 = {"device": typeId, "command": cmd, "pin": GPIOpin, "values": {"analogValue":analogValue,"pulseUp":pulseUp,"pulseDown": pulseDown,"nPulses":nPulses}, "restoreAfterBoot": restoreAfterBoot, "startAtDateTime": startAtDateTime, "inverseGPIO": inverseGPIO, "devId": devId}
					elif cmd == "disable":
						cmd1 = {"device": typeId, "command": cmd, "pin": GPIOpin, "devId": devId}

				elif typeId.find("OUTPUTi2cRelay") > -1:
					if cmd == "up" or cmd == "down":
						cmd1 = {"device": typeId, "command": cmd, "pin": GPIOpin, "restoreAfterBoot": restoreAfterBoot, "startAtDateTime": startAtDateTime, "inverseGPIO": inverseGPIO, "devId": devId, "i2cAddress":i2cAddress}
					elif cmd in["pulseUp", "pulseDown", "continuousUpDown"]:
						cmd1 = {"device": typeId, "command": cmd, "pin": GPIOpin, "values": {"pulseUp":pulseUp, "pulseDown": pulseDown, "nPulses":nPulses}, "restoreAfterBoot": restoreAfterBoot, "startAtDateTime": startAtDateTime, "inverseGPIO": inverseGPIO, "devId": devId, "i2cAddress":i2cAddress}
					elif cmd == "disable":
						cmd1 = {"device": typeId, "command": cmd, "pin": GPIOpin, "devId": devId}

				elif typeId.find("display") > -1:
					if cmd == "up" or cmd == "down":
						cmd1 = {"device": typeId, "command": cmd,	 "restoreAfterBoot": restoreAfterBoot, "devId": devId}


			if self.decideMyLog("OutputDevice"): self.indiLOG.log(5, "sendGPIOCommand: {}".format(cmd1))

			self.sendtoRPI(ip, pi, [cmd1], calledFrom="sendGPIOCommand")

		except Exception as e:
			self.exceptionHandler(40, e)



####-------------------------------------------------------------------------####
	def sendGPIOCommands(self, ip, pi, cmd, GPIOpin, inverseGPIO):
		nCmds = len(cmd)
		cmds =[]
		try:
			for kk in range(nCmds):
				if cmd[kk] == "up" or cmd[kk] == "down":
					cmds.append({"device": "OUTPUTgpio-1", "command": cmd[kk], "pin": GPIOpin[kk], "inverseGPIO": inverseGPIO[kk]})

			if self.decideMyLog("OutputDevice"): self.indiLOG.log(5,"sendGPIOCommand-s-: {}".format(cmds) )
			self.sendtoRPI(ip, pi ,cmds, calledFrom="sendGPIOCommand")

		except Exception as e:
			self.exceptionHandler(40, e)




			###########################	   UTILITIES  #### START #################


####-------------------------------------------------------------------------####
	def setupFilesForPi(self, calledFrom=""):
		try:
			if time.time() - self.lastsetupFilesForPi < 5: return
			self.lastsetupFilesForPi = time.time()
			if self.decideMyLog("UpdateRPI"): self.indiLOG.log(5,"updating pi server files called from: {}".format(calledFrom) )

			self.makeBeacons_parameterFile()

			for piU in self.RPI:
				if self.RPI[piU]["piOnOff"] == "0": continue
				self.makeParametersFile(piU)
				self.makeInterfacesFile(piU)
				self.makeSupplicantFile(piU)


		except Exception as e:
			self.exceptionHandler(40, e)
		return




####-------------------------------------------------------------------------####
	def makeBeacons_parameterFile(self):
		try:
			out={}
			xx1 = []
			xx2 = {}
			xx4 = {}
			xx5 = {}
			xx6 = {}
			xx8 = {}
			xx9 = {}
			for beacon in copy.deepcopy(self.beacons):
				if self.beacons[beacon]["ignore"] >= 1 or self.beacons[beacon]["ignore"] == -1:  xx1.append(beacon)
				devId = self.beacons[beacon]["indigoId"]
				if devId > 0:
					try:	dev = indigo.devices[devId]
					except: continue
					props = dev.pluginProps
					if self.beacons[beacon]["ignore"] == 0 and dev.enabled:
						xx2[beacon] = { "typeOfBeacon":"", "useOnlyIfTagged":""}
						tag = self.beacons[beacon]["typeOfBeacon"]
						xx2[beacon]["typeOfBeacon"] = tag

						xx2[beacon]["useOnlyIfTagged"] = 0
						try:
							xx2[beacon]["useOnlyIfTagged"] = int(self.beacons[beacon]["useOnlyPrioTagMessageTypes"])
						except:
							if tag in self.knownBeaconTags["input"]:
								xx2[beacon]["useOnlyIfTagged"] = self.knownBeaconTags["input"][tag]["useOnlyThisTagToAcceptBeaconMsgDefault"]

					if  "batteryLevelUUID" in props and props["batteryLevelUUID"].find("TLM") == 0:
							#self.indiLOG.log(30,"beacon:{};  batteryLevelUUID:{}".format(beacon, props["batteryLevelUUID"]))
							xx9[beacon] = props["batteryLevelUUID"]
					try:
						if int(props["signalDelta"]) < 200:
							xx4[beacon] = int(props["signalDelta"])
					except:pass
					try:
						if int(props["minSignalOn"]) >-200:
							xx5[beacon] = int(props["minSignalOn"])
					except:	pass
					try:
						if int(props["minSignalOff"]) >200:
							xx5[beacon] = int(props["minSignalOff"])
					except:	pass
					try:
						if int(props["fastDown"]) >0:
							xx8[beacon] = {"seconds":int(props["fastDown"])}
					except:	pass

			out["ignoreMAC"]			= xx1
			out["onlyTheseMAC"]			= xx2
			out["signalDelta"]			= xx4
			out["minSignalOn"]			= xx5
			out["minSignalOff"]			= xx6
			out["fastDownList"]			= xx8
			out["batteryLevelUUID"]		= xx9
			# make mac the index, BLEconnect runs on MACs not on devIds
			out["BLEconnectLastUp"]		= {}
			for devId in self.BLEconnectLastUp:
				out["BLEconnectLastUp"][self.BLEconnectLastUp[devId]["mac"]]= {"devId":devId, "lastUp": self.BLEconnectLastUp[devId]["lastUp"]}

			#self.indiLOG.log(20,"fastBLEReaction: {}".format(self.fastBLEReaction))
			for mac in copy.copy(self.fastBLEReaction):
				if not self.isValidMAC(mac): 
					del self.fastBLEReaction[mac]
				if type(self.fastBLEReaction[mac]) != type({}):
					del self.fastBLEReaction[mac]
			#self.indiLOG.log(20,"fastBLEReaction: {}".format(self.fastBLEReaction))

			out["fastBLEReaction"] = self.fastBLEReaction

			out = json.dumps(out, sort_keys=True, indent=2)
			f = open(self.indigoPreferencesPluginDir + "all/beacon_parameters", "w")
			f.write(out)
			f.close()
			if len(out) > 50000:
					self.indiLOG.log(50,"parameter file:\n{}all/beacon_parameters\n has become TOOO BIG, \nplease do menu/ignore individual beacons and reset history.\nyou might also want to switch off accept new ibeacons in config\n".format(self.indigoPreferencesPluginDir) )

			try:
				f = open(self.indigoPreferencesPluginDir + "all/knownBeaconTags", "w")
				f.write(json.dumps(self.knownBeaconTags))
				f.close()
			except Exception as e:
					self.exceptionHandler(40, e)

		except Exception as e:
			self.exceptionHandler(40, e)
		return



####-------------------------------------------------------------------------####
	def makeInterfacesFile(self,piU):
		return 
		try:
			if self.RPI[piU]["piOnOff"] == "0": return
			f = open(self.indigoPreferencesPluginDir + "interfaceFiles/interfaces." + piU, "w")
			f.write("source-directory /etc/network/interfaces.d\n")
			f.write("auto lo\n")
			f.write("iface lo inet loopback\n")
			f.write("auto eth0\n")
			f.write("allow-hotplug eth0\n")
			f.write("iface eth0 inet dhcp\n\n")
			f.write("allow-hotplug wlan0\n")
			f.write("auto wlan0\n")
			f.write("iface wlan0 inet manual\n")
			f.write("   wpa-conf /etc/wpa_supplicant/wpa_supplicant.conf\n")
			f.close()
		except Exception as e:
			self.exceptionHandler(40, e)
		return

####-------------------------------------------------------------------------####
	def makeSupplicantFile(self,piU):
		return 
		try:
			if self.RPI[piU]["piOnOff"] == "0": return
			f = open(self.indigoPreferencesPluginDir + "interfaceFiles/wpa_supplicant.conf." + piU, "w")
			f.write("ctrl_interface=DIR=/var/run/wpa_supplicant GROUP=netdev\n")
			f.write("update_config=1\n")
			f.write("country=US\n")
			f.write("network={\n")
			f.write('   ssid="' + self.wifiSSID + '"\n')
			f.write('   psk="' + self.wifiPassword + '"\n')
			if self.key_mgmt != "" and self.key_mgmt != "NONE":
				f.write('   key_mgmt="' + self.key_mgmt + '"\n')
			f.write("}\n")
			f.close()
		except Exception as e:
			self.exceptionHandler(40, e)
		return

####-------------------------------------------------------------------------####
	def makeParametersFile(self, piU, retFile=False):
		try:
				if self.RPI[piU]["piOnOff"] == "0": return
				out = {}
				pi = int(piU)

				out["configured"]		  		  = (datetime.datetime.now()).strftime(_defaultDateStampFormat)
				out["rebootWatchDogTime"]		  = self.rebootWatchDogTime
				out["GPIOpwm"]					  = self.GPIOpwm
				if pi == self.debugRPI:	out["debugRPI"] = 1
				else:					out["debugRPI"] = 0
				out["restartBLEifNoConnect"]		= self.restartBLEifNoConnect
				out["acceptNewiBeacons"]			= self.acceptNewiBeacons
				out["acceptNewBeaconMAC"]			= self.acceptNewBeaconMAC
				out["acceptNewMFGNameBeacons"]		= self.pluginPrefs.get("acceptNewMFGNameBeacons","")
				out["acceptNewTagiBeacons"]			= self.acceptNewTagiBeacons
				out["rebootHour"]			 		= self.pluginPrefs.get("rebootHour", -1)
				out["ipOfServer"]					= self.myIpNumber
				out["portOfServer"]					= self.portOfServer
				out["portOfServer"]					= self.portOfServer
				out["getBatteryMethod"]				= "interactive"
				out["compressRPItoPlugin"]			= self.compressRPItoPlugin
				out["userIdOfServer"]				= self.userIdOfServer
				out["indigoInputPORT"]				= self.indigoInputPORT
				out["IndigoOrSocket"]				= self.IndigoOrSocket
				out["passwordOfServer"]				= self.passwordOfServer
				out["authentication"]				= self.authentication
				out["apiKey"]						= self.apiKey
				out["wifiEth"]						= self.wifiEth
				out["myPiNumber"]					= piU
				out["enableRebootCheck"]			= self.RPI[piU]["enableRebootCheck"]
				out["rPiCommandPORT"]				= self.rPiCommandPORT
				out["sendToIndigoSecs"]				= self.RPI[piU]["sendToIndigoSecs"]
				out["enableiBeacons"]				= self.RPI[piU]["enableiBeacons"]
				out["pressureUnits"]				= self.pluginPrefs.get("pressureUnits", "hPascal")
				out["distanceUnits"]				= self.pluginPrefs.get("distanceUnits", "1.0")
				out["tempUnits"]					= self.pluginPrefs.get("tempUnits", "C")
				out["ipNumberPi"]					= self.RPI[piU]["ipNumberPi"]
				out["deltaChangedSensor"]			= self.RPI[piU]["deltaChangedSensor"]
				out["sensorRefreshSecs"]			= float(self.RPI[piU]["sensorRefreshSecs"])
				out["rebootIfNoMessagesSeconds"]	= self.pluginPrefs.get("rebootIfNoMessagesSeconds", 999999999)
				out["maxSizeOfLogfileOnRPI"]		= int(self.pluginPrefs.get("maxSizeOfLogfileOnRPI", 10000000))



				try :
					piDeviceExist=False
					try:
						try:	  piID= int(self.RPI[piU]["piDevId"])
						except:	  piID=0
						if piID !=0:
							piDev = indigo.devices[piID]
							props = piDev.pluginProps
							piDeviceExist=True
					except Exception as e:
						if "{}".format(e).find("timeout waiting") > -1:
							self.exceptionHandler(40, e)
							self.indiLOG.log(40,"communication to indigo is interrupted")
							return
						if "{}".format(e).find("not found in database") >-1:
							self.exceptionHandler(40, e)
							self.indiLOG.log(40,"RPI:{} devid:{} not in indigo, if RPI justd eleted, it will resolve itself ".format(piU ,piID))
							self.delRPI(pi=piU, calledFrom="makeParametersFile")
							self.updateNeeded += ",fixConfig"
							self.fixConfig(checkOnly = ["all", "rpi", "force"],fromPGM="makeParametersFile bad rpi")
						else:
							self.exceptionHandler(40, e)
							self.indiLOG.log(40,"RPI: {} error ..  piDevId not set:{}".format(piU ,self.RPI[piU]))
							self.updateNeeded += ",fixConfig"
							self.fixConfig(checkOnly = ["all", "rpi"],fromPGM="makeParametersFile2")

					if piDeviceExist:

						if "rpiDataAcquistionMethod" in props and props["rpiDataAcquistionMethod"] in ["socket", "hcidumpWithRestart", "hcidump"]:
								out["rpiDataAcquistionMethod"]	  = props["rpiDataAcquistionMethod"]
						else:
								out["rpiDataAcquistionMethod"]	  = self.rpiDataAcquistionMethod

						out["oneWireGpios"]					= props.get("oneWireGpios", "")

						if "compressRPItoPlugin" in props:
							try: 	 min(self.compressRPItoPlugin, out["compressRPItoPlugin"],40000)
							except: out["compressRPItoPlugin"] = self.compressRPItoPlugin

						out["usePython3"] = self.pluginPrefs.get("usePython3","-1")  # general setting  -1 0 1  if -1 dont, if +1 yes, if 0 check individual setting for rpi
						if  out["usePython3"] == "0":
							try: 	out["usePython3"] = props.get("usePython3","-1")
							except: pass

						out["execcommandsListAction"] = props.get("execcommandsListAction","delete")

						if "eth0" in props and "wlan0" in props:
							try: 	out["wifiEth"] =  {"eth0":json.loads(props["eth0"]), "wlan0":json.loads(props["wlan0"])}
							except: pass

						if "startXonPi" in props:
							try:    out["startXonPi"]  = props["startXonPi"]
							except: out["startXonPi"]  = "leaveAlone"


						if "startXonPi" in props:
							try:    out["startXonPi"]  = props["startXonPi"]
							except: out["startXonPi"]  = "leaveAlone"

						if "macIfWOLsendToIndigoServer" in props:
							try:    out["macIfWOLsendToIndigoServer"]  = props["macIfWOLsendToIndigoServer"].upper()
							except: pass

						if "IpnumberIfWOLsendToIndigoServer" in props:
							try:    out["IpnumberIfWOLsendToIndigoServer"]  = props["IpnumberIfWOLsendToIndigoServer"]
							except: pass


						if "timeZone" in props:
							try:    out["timeZone"]  = props["timeZone"]
							except: out["timeZone"]  = "99"

						if "startOtherProgram" in props:
							out["startOtherProgram"]				=  (props["startOtherProgram"])
							out["startOtherProgramKeepRunning"]	=  (props["startOtherProgramKeepRunning"])

						out["clearHostsFile"]		= props.get("clearHostsFile","0")

						out["ifNetworkChanges"]		= props.get("ifNetworkChanges","0")

						out["oneWireForceReboot"]	= props.get("oneWireForceReboot","-1")

						out["oneWireAddNewSensors"]	= props.get("oneWireAddNewSensors","0")

						out["oneWireResetIsUpDown"]	= props.get("oneWireResetIsUpDown","0")

						out["oneWireResetGpio"]		= props.get("oneWireResetGpio","")

						out["oneWireGpios"]			= props.get("oneWireGpios", "")

						out["startWebServerSTATUS"]	= props.get("startWebServerSTATUS","0")

						out["startWebServerINPUT"]	= props.get("startWebServerINPUT","0")

						out["GPIOTypeAfterBoot1"]	= props.get("GPIOTypeAfterBoot1","off")

						out["GPIOTypeAfterBoot2"]	= props.get("GPIOTypeAfterBoot2","off")

						out["GPIONumberAfterBoot1"]	= props.get("GPIONumberAfterBoot1","-1")

						out["GPIONumberAfterBoot2"]	= props.get("GPIONumberAfterBoot2","-1")

						out["typeOfUPS"]	=  props.get("typeOfUPS","")


						out["simpleBatteryBackupEnable"]  =  "0"
						if "simpleBatteryBackupEnable" in props:
							try:	 out["simpleBatteryBackupEnable"]	=  int(props["simpleBatteryBackupEnable"])
							except: pass
							if out["simpleBatteryBackupEnable"]  ==  1:
								out["shutdownPinVoltSensor"]  = -1
								if "shutdownPinVoltSensor" in props:
									try:  out["shutdownPinVoltSensor"]	=  int(props["shutdownPinVoltSensor"])
									except: pass

								out["shutDownPinVetoOutput"]  = -1
								if "shutDownPinVetoOutput" in props:
									try:	 out["shutDownPinVetoOutput"]	=  int(props["shutDownPinVetoOutput"])
									except: pass

						#out["batteryMinPinActiveTimeForShutdown"]  = 99999999999
						if "batteryMinPinActiveTimeForShutdown" in props:
							try:  out["batteryMinPinActiveTimeForShutdown"]	=  int(props["batteryMinPinActiveTimeForShutdown"])
							except: pass

						#out["batteryChargeTimeForMaxCapacity"]  =  2*3600
						if "batteryChargeTimeForMaxCapacity" in props:
							try:	 out["batteryChargeTimeForMaxCapacity"]	=  int(props["batteryChargeTimeForMaxCapacity"])
							except: pass

						#out["batteryCapacitySeconds"]  =  5
						if "batteryCapacitySeconds" in props:
							try:	 out["batteryCapacitySeconds"]	=  int(props["batteryCapacitySeconds"])
							except: pass


						out["shutDownPinEnable"]  =  "0"
						if "shutDownPinEnable" in props:
							try:	 out["shutDownPinEnable"]	=  int(props["shutDownPinEnable"])
							except: pass
							if out["shutDownPinEnable"]  ==  1:
								out["shutDownPinOutput"]  = -1
								if "shutDownPinOutput" in props:
									try:	 out["shutDownPinOutput"]		=  int(props["shutDownPinOutput"])
									except: pass
								out["shutdownInputPin"]  = -1
								if "shutdownInputPin" in props:
									try:  out["shutdownInputPin"]		=  int(props["shutdownInputPin"])
									except: pass


						out["batteryUPSshutdownEnable"]  =  "0"
						if "batteryUPSshutdownEnable" in props:
							try:	 out["batteryUPSshutdownEnable"]	=  int(props["batteryUPSshutdownEnable"])
							except: pass
							if out["batteryUPSshutdownEnable"]  ==  1:
								out["batteryUPSshutdownAtxPercent"]  =  -1
								if "batteryUPSshutdownAtxPercent" in props:
									try:	 out["batteryUPSshutdownAtxPercent"]	=  int(props["batteryUPSshutdownAtxPercent"])
									except: pass

								out["shutdownSignalFromUPSPin"]  =  -1
								if "shutdownSignalFromUPSPin" in props:
									try:	 out["shutdownSignalFromUPSPin"]	=  int(props["shutdownSignalFromUPSPin"])
									except: pass

						if "batteryUPSshutdownAtxPercent" in props and props["batteryUPSshutdownAtxPercent"] != "":
							try:	 out["batteryUPSshutdownAtxPercent"]	=  int(props["batteryUPSshutdownAtxPercent"])
							except: pass


						if "batteryUPSshutdownALCHEMYupcI2C" in props and props["batteryUPSshutdownALCHEMYupcI2C"] != "":
							out["batteryUPSshutdownALCHEMYupcI2C"]	=  int(props["batteryUPSshutdownALCHEMYupcI2C"])

						if "display" in props:
							try: out["display"]  =	 int(props["display"])
							except: pass


						if "sleepAfterBoot" in props and props["sleepAfterBoot"] in ["0", "5", "10", "15"]:
							out["sleepAfterBoot"]			 = props["sleepAfterBoot"]
						else:
							out["sleepAfterBoot"]			 = "10"


						out = self.updateSensProps(out, props, "fanEnable", elseSet="-")
						out = self.updateSensProps(out, props, "fanGPIOPin", elseSet="-1")
						out = self.updateSensProps(out, props, "fanTempOnAtTempValue", elseSet="60")
						out = self.updateSensProps(out, props, "fanTempOffAtTempValue", elseSet="2")
						out = self.updateSensProps(out, props, "fanTempDevId", elseSet="0")


						out = self.updateSensProps(out, props, "networkType", elseSet="fullIndigo")
						out = self.updateSensProps(out, props, "BeaconUseHCINo")
						out = self.updateSensProps(out, props, "BLEconnectUseHCINo")
						out = self.updateSensProps(out, props, "BLEconnectMode")
						out = self.updateSensProps(out, props, "enableMuxI2C")
						out = self.updateSensProps(out, props, "bluetoothONoff")
						out = self.updateSensProps(out, props, "useRTC", elseSet="")
						out = self.updateSensProps(out, props, "pin_webAdhoc")
						out = self.updateSensProps(out, props, "useRamDiskForLogfiles", elseSet="0")
						out = self.updateSensProps(out, props, "BLEserial", elseSet="sequential")
						out = self.updateSensProps(out, props, "sendToIndigoSecs")

				except Exception as e:
					self.exceptionHandler(40, e)
					return ""



				out["rPiRestartCommand"]	 = self.rPiRestartCommand[pi]
				if self.rPiRestartCommand[pi].find("reboot") > -1:
					out["reboot"] = datetime.datetime.now().strftime("%Y-%m-%d-%H:%M:%S")

				out["timeStamp"]  = datetime.datetime.now().strftime("%Y-%m-%d-%H:%M:%S")

				self.rPiRestartCommand[pi]= ""


				out["sensors"]				 = {}
				for sensor in self.RPI[piU]["input"]:
					try:

						if sensor not in _GlobalConst_allowedSensors and sensor not in _BLEsensorTypes: continue
						if len(self.RPI[piU]["input"][sensor]) == 0: continue
						sens = {}
						for devIdS in self.RPI[piU]["input"][sensor]:
							if devIdS == "0" or devIdS == "": continue
							try:
								devId = int(devIdS)
								dev = indigo.devices[devId]
							except Exception as e:
								if "{}".format(e).find("timeout waiting") > -1:
									self.exceptionHandler(40, e)
									self.indiLOG.log(40,"communication to indigo is interrupted")
									return
								self.exceptionHandler(40, e)
								continue
							#if dev.id in [1697729290,1707940373]: self.indiLOG.log(20,"====== dev:{}, piU:{}, enabled:{}, input:{}".format(dev.name, piU, dev.enabled, self.RPI[piU]["input"]))

							if not dev.enabled: continue
							props = dev.pluginProps
							sens[devIdS] = {}
							#if dev.id in [49344355]: self.indiLOG.log(20,"pass 1 props:{}".format(props))

							sens[devIdS]["name"] = dev.name


							if "deviceDefs" in props:
								try:    sens[devIdS] = {"INPUTS":json.loads(props["deviceDefs"])}
								except: pass



							if "serialNumber" in dev.states:
								sens[devIdS] = self.updateSensProps(sens[devIdS], dev.states, "serialNumber",elseSet="--force--")
							else:
								sens[devIdS] = self.updateSensProps(sens[devIdS], props, "serialNumber",elseSet=None)

							if "iPhoneRefreshDownSecs" in props:
								sens[devIdS] = self.updateSensProps(sens[devIdS], props, "iPhoneRefreshUpSecs",elseSet=300)
								sens[devIdS] = self.updateSensProps(sens[devIdS], props, "iPhoneRefreshDownSecs",elseSet=10)
								sens[devIdS] = self.updateSensProps(sens[devIdS], props, "BLEtimeout",elseSet=10)
								sens[devIdS] = self.updateSensProps(sens[devIdS], props, "macAddress")

							for jj in range(27):
								if "INPUT_{}".format(jj) in props:
									try:    iiii = int(props["INPUT_{}".format(jj)])
									except: iiii = -1
									if iiii > 0:
										sens[devIdS] = self.updateSensProps(sens[devIdS], props, "INPUT_{}".format(jj))

							for jj in range(27):
								if "OUTPUT_{}".format(jj) in props:
									try:    iiii = int(props["OUTPUT_{}".format(jj)])
									except: iiii = -1
									if iiii > 0:
										sens[devIdS] = self.updateSensProps(sens[devIdS], props, "OUTPUT_{}".format(jj))

							if "noI2cCheck" not in props or not props["noI2cCheck"]:
								sens[devIdS] = self.updateSensProps(sens[devIdS], props, "i2cAddress")

							sens[devIdS] = self.updateSensProps(sens[devIdS], dev.states, "CO2offset")


							for propToUpdate in ["sendToRpi","numberOfMeasurementToAverage","sensorRefreshSecs","readSensorEvery","codeType","nBits","nInputs","isBLESensorDevice","incrementIfGT4Signals","inverse","ignorePinValue",
										"distinctTransition","resetTimeCheck","useWhichGPIO",
										"GPIOcsPin","GPIOmisoPin","GPIOmosiPin","GPIOclkPin",
										"nWires","referenceResistor","resistorAt0C","hertz50_60",
										"rainScaleFactor","gpioIn","gpioSW1","gpioSW2","gpioSW5","gpioSWP","cyclePower","sensorMode","sendMSGEverySecs","dhtType","useCircuitpython",
										"timeaboveCalibrationMAX","launchCommand","launchCheck","amplification","sensitivity","CO2normal","resetPin","shuntResistor","shuntResistor1","shuntResistor2","shuntResistor3",
										"useMuxChannel","inside","minStrikes","tuneCapacitor","calibrationDynamic","minNoiseFloor","noiseFloor",
										"displayEnable","freeParameter","display","isBLElongConnectDevice",
										"gpioEcho","gpioTrigger","xShutPin","gpio",
										"calibrateSetting","recalibrateIfGT","setCalibrationFixedValue","deltaDist","deltaDistAbs","units","dUnits","multiply","offset",
										"format","sensorTemperatureOffset","autoCalibration","fastSlowRead","altitudeCompensation","multTemp","offsetTemp","offsetCO2","offsetAlt","enableCalibration","multiplyPress","offsetPress","offsetGas","multiplyHum","offsetHum",
										"input","spiAddress","gpioPin","sps","gain","integrationTime","doAverage","LEDBlink","LEDmA","font","width","width1","width2","width3","pos1","pos2","pos3","pos3LinLog","logScale","displayText","normalizeDistance","colorOfDistanceBar","inverseDistance",
										"intensity","freeParameter","refreshColor","deltaColor","refreshProximity","deltaProximity","enableGesture","interruptGPIO",
										"actionPulseBurst","actionPulseContinuous","actionLEFT","actionRIGHT","actionUP","actionDOWN","actionDoubleClick","actionLongClick","actionNEAR","actionFAR","actionPROXup","actionPROXdown","acuracyDistanceMode","mode","waitIfNone","restartAfterNones",
										"actionShortDistance","actionShortDistanceLimit","actionMediumDistance","actionLongDistance","actionLongDistanceLimit","actionStopDistance","actionStopMinSpeed","actionStopWait",
										"actionVeryShortDistanceLimit","actionVeryLongDistanceLimit","actionVeryLongDistance","actionVeryShortDistance","actionEnable",
										"maxCurrent","integrationTime","rSet","SCLPin","SDOPin","deltaCurrent","deltaX","threshold","sensorLoopWait","resetPin","minSendDelta",
										"magResolution","declinationOffset","magOffsetX","magOffsetY","magOffsetZ","magDivider","accelerationGain","accelRes","magGain","magFregRate","devType","lowHighAs",
										"risingOrFalling","deadTime","deadTimeBurst","timeWindowForBursts","minEventsinTimeWindowToTriggerBursts","inpType","bounceTime","timeWindowForContinuousEvents",
										"mac","type","INPUTdevId0","INPUTdevId1","INPUTdevId2","INPUTdevId3","coincidenceTimeInterval","updateIndigoTiming","updateIndigoDeltaTemp","updateIndigoDeltaAccelVector","updateIndigoDeltaMaxXYZ",
										"usbPort","motorFrequency","nContiguousAngles","contiguousDeltaValue","triggerLast","triggerCalibrated","sendToIndigoEvery",
										"anglesInOneBin","measurementsNeededForCalib","sendPixelData","doNotUseDataRanges","minSignalStrength","relayType","python3","bleHandle"]:
								sens[devIdS] = self.updateSensProps(sens[devIdS], props, propToUpdate)
							#if dev.id == 49344355: self.indiLOG.log(20,"pass 9 sens:{}".format(sens))
							#if dev.id == 1974364636: self.indiLOG.log(20,"dev:{}, props:{} ".format(dev.name, props))

							dev.replacePluginPropsOnServer(props)

						if sens != {}:
							out["sensors"][sensor] = sens
					except Exception as e:
						self.exceptionHandler(40, e)
						#self.indiLOG.log(40, "{}".format(sens))

				out["sensorList"] = self.RPI[piU]["sensorList"]

				out["output"] = {}
				for devOut in indigo.devices.iter("props.isOutputDevice"):
					typeId = devOut.deviceTypeId
					if typeId not in _GlobalConst_allowedOUTPUT: 								continue
					if not devOut.enabled: 														continue
					propsOut= devOut.pluginProps
					if "piServerNumber" in propsOut and propsOut["piServerNumber"] != piU:	continue
					if typeId.find("OUTPUTgpio") > -1 or typeId.find("OUTPUTi2cRelay") > -1 or typeId.find("OUTPUTswitchbot") > -1: 
						if typeId in self.RPI[piU]["output"]:
							if typeId.find("OUTPUTswitchbot") > -1:
								out["output"][typeId] = {}
								for devId in self.RPI[piU]["output"][typeId]:
									if self.RPI[piU]["output"][typeId][devId] in [{},""]: continue
									out["output"][typeId][devId] = copy.deepcopy(self.RPI[piU]["output"][typeId][devId])
								if out["output"][typeId] == {}:
									del out["output"][typeId]
							else:
								out["output"][typeId] = copy.deepcopy(self.RPI[piU]["output"][typeId])


						else:
							self.indiLOG.log(30,"creating parametersfile .. please fix device {}; rpi number:{} , outdput dev not linked ?, typeId: {}, self.RPI[piU][output]: {}".format(devOut.name, piU, typeId, self.RPI[piU]["output"]))
							continue
					else:
						devIdoutS  = "{}".format(devOut.id)
						i2cAddress = ""
						spiAddress = ""
						if typeId not in out["output"]: out["output"][typeId] = {}
						out["output"][typeId][devIdoutS] = [{}]

						out["output"][typeId][devIdoutS][0]["name"] = devOut.name

						for xxxx in ["lightSensorOnForDisplay","lightSensorForDisplayDevIdType","lightSensorSlopeForDisplay","clockLightSet","minLightNotOff","devType","devTypeROWs","devTypeLEDs",
								"interfaceType","spiAddress","PIN_RST","PIN_DC","PIN_CE","PIN_CS","width","mono",
								"font","mute","highCut","noiseCancel","bandLimit","DTCon","PLLREF","XTAL","defFreq","HLSI","signalPin",
								"PWMchannel","frequency","DMAchannel","OrderOfMatrix","intensity","flipDisplay","lightMinDimForDisplay","lightMaxDimForDisplay","intensity"]:
							out["output"][typeId][devIdoutS][0] = self.updateSensProps(out["output"][typeId][devIdoutS][0], propsOut, xxxx)


						if typeId.find("neopixelClock") >-1:
								if self.decideMyLog("OutputDevice"): self.indiLOG.log(5,	" neoPixelClock props:\n{}".format(propsOut) )
								theDict={}
								theDict["ticks"] = {"HH":{},"MM":{},"SS":{}}
								theDict["marks"] = {"HH":{},"MM":{},"SS":{}}
								theDict["rings"] = []

								theDict["ticks"]["HH"] = {"ringNo":json.loads("["+propsOut["clockHHRings"]+"]"),
														  "RGB":json.loads("["+propsOut["clockHHRGB"]+"]"),
														  "npix":int(propsOut["clockHHnPIX"]),
														  "blink":json.loads(propsOut["clockHHBlink"])}

								theDict["ticks"]["MM"] = {"ringNo":json.loads("["+propsOut["clockMMRings"]+"]"),
														  "RGB":json.loads("["+propsOut["clockMMRGB"]+"]"),
														  "npix":int(propsOut["clockMMnPIX"]),
														  "blink":json.loads(propsOut["clockMMBlink"])}

								theDict["ticks"]["SS"] = {"ringNo":json.loads("["+propsOut["clockSSRings"]+"]"),
														  "RGB":json.loads("["+propsOut["clockSSRGB"]+"]"),
														  "npix":int(propsOut["clockSSnPIX"]),
														  "blink":json.loads(propsOut["clockSSBlink"])}

								theDict["ticks"]["DD"] = {"ringNo":json.loads("["+propsOut["clockDDRings"]+"]"),
														  "RGB":json.loads("["+propsOut["clockDDRGB"]+"]"),
														  "npix":int(propsOut["clockDDnPIX"]),
														  "blink":json.loads(propsOut["clockDDBlink"])}

								theDict["marks"]["HH"] = {"ringNo":json.loads("["+propsOut["clockHHmarksRings"]+"]"),
														  "RGB":json.loads("["+propsOut["clockHHmarksRGB"]+"]"),
														  "marks":json.loads(propsOut["clockHHmarks"])}

								theDict["marks"]["MM"] = {"ringNo":json.loads("["+propsOut["clockMMmarksRings"]+"]"),
														  "RGB":json.loads("["+propsOut["clockMMmarksRGB"]+"]"),
														  "marks":json.loads(propsOut["clockMMmarks"])}

								theDict["marks"]["SS"] = {"ringNo":json.loads("["+propsOut["clockSSmarksRings"]+"]"),
														  "RGB":json.loads("["+propsOut["clockSSmarksRGB"]+"]"),
														  "marks":json.loads(propsOut["clockSSmarks"])}

								theDict["marks"]["DD"] = {"ringNo":json.loads("["+propsOut["clockDDmarksRings"]+"]"),
														  "RGB":json.loads("["+propsOut["clockDDmarksRGB"]+"]"),
														  "marks":json.loads(propsOut["clockDDmarks"])}
								try:
									theDict["extraLED"]= {"ticks":json.loads("["+propsOut["clockEXTRAticks"]+"]"),
														  "RGB":json.loads("["+propsOut["clockEXTRARGB"]+"]"),
														  "blink":json.loads(propsOut["clockEXTRAblink"])}
								except:
									theDict["extraLED"]   = ""
								for jj in range(20):
									if "ring{}".format(jj) in propsOut:
										try: theDict["rings"].append(int(propsOut["ring{}".format(jj)]))
										except:pass
								nLEDs = sum(theDict["rings"])

								propsOut["devTypeLEDs"]		  = "{}".format(nLEDs)
								propsOut["devTypeROWs"]		  = "1"
								propsOut["devType"]			  = "1x{}".format(nLEDs)
								theDict["speed"]			  = propsOut["speed"]
								theDict["speedOfChange"]	  = propsOut["speedOfChange"]
								theDict["GPIOsetA"]			  = propsOut["GPIOsetA"]
								theDict["GPIOsetB"]			  = propsOut["GPIOsetB"]
								theDict["GPIOsetC"]			  = propsOut["GPIOsetC"]
								theDict["GPIOup"]			  = propsOut["GPIOup"]
								theDict["GPIOdown"]			  = propsOut["GPIOdown"]

								out["output"][typeId][devIdoutS][0]=  copy.deepcopy(theDict)
								if self.decideMyLog("OutputDevice"): self.indiLOG.log(5,	"neoPixelClock out:\n".format(theDict))

						if typeId.find("sundial") >-1:
								out["output"][typeId][devIdoutS][0] = self.updateSensProps(out["output"][typeId][devIdoutS][0], propsOut, "updateDownloadEnable")



						if typeId.find("FBHtempshow") > -1:
							out["output"][typeId][devIdoutS][0] = {"name":dev.name,"data":{}}
							#self.indiLOG.log(20, "FBHtempshow    bef devIdoutS:{}".format(self.RPI[piU]["output"][typeId][devIdoutS]))
							for devS in self.RPI[piU]["output"][typeId][devIdoutS]:
								if devS == "": continue
								dev1Id  = self.RPI[piU]["output"][typeId][devIdoutS][devS].get("LEVEL","0")
								dev2Id  = self.RPI[piU]["output"][typeId][devIdoutS][devS].get("setpointHeat","0")
								try:
									dev1Id = int(dev1Id)
									dev1Name =  indigo.devices[dev1Id].name
									LEVEL = indigo.devices[dev1Id].states["LEVEL"]
								except: 
									LEVEL = 0
									dev1Name = ""
								try:
									dev2Id = int(dev2Id)
									dev2Name =  indigo.devices[dev2Id].name
									setpointHeat = indigo.devices[dev2Id].states["setpointHeat"]
									roomTemperature = indigo.devices[dev2Id].states["temperatureInput1"]
								except: 
									setpointHeat = 0
									roomTemperature = -1
									dev2Name =  ""
								#self.indiLOG.log(20, "FBHtempshow     devS:{}, dev1Id:{}, LEVEL:{}, dev2Id:{}, setpointHeat:{}".format(devS, dev1Id, LEVEL, dev2Id, setpointHeat))

								out["output"][typeId][devIdoutS][0]["data"][devS] = {"setpointHeat":setpointHeat,"roomName":dev2Name,"LEVELName":dev1Name, "LEVEL":LEVEL, "roomTemperature": roomTemperature}
							#self.indiLOG.log(20, "FBHtempshow after  out:{}".format(json.dumps(out["output"][typeId], sort_keys=True, indent=2)))


						if typeId.find("setStepperMotor") >-1:
								theDict={}

								if "motorType" in propsOut:
									theDict["motorType"]				= propsOut["motorType"]
									if propsOut["motorType"].find("unipolar") > -1 or propsOut["motorType"].find("bipolar") > -1:
										theDict["pin_CoilA1"]			= propsOut["pin_CoilA1"]
										theDict["pin_CoilA2"]			= propsOut["pin_CoilA2"]
										theDict["pin_CoilB1"]			= propsOut["pin_CoilB1"]
										theDict["pin_CoilB2"]			= propsOut["pin_CoilB2"]
									elif propsOut["motorType"].find("DRV8834") > -1:
										theDict["pin_Step"]				= propsOut["pin_Step"]
										theDict["pin_Dir"]				= propsOut["pin_Dir"]
										theDict["pin_Sleep"]			= propsOut["pin_Sleep"]
									elif propsOut["motorType"].find("A4988") > -1:
										theDict["pin_Step"]				= propsOut["pin_Step"]
										theDict["pin_Dir"]				= propsOut["pin_Dir"]
										theDict["pin_Sleep"]			= propsOut["pin_Sleep"]


								out["output"][typeId][devIdoutS][0]=  copy.deepcopy(theDict)
								if self.decideMyLog("OutputDevice"): self.indiLOG.log(5,	" neoPixelClock: "+json.dumps(theDict))


						if "noI2cCheck" not in propsOut or  not propsOut["noI2cCheck"]:
							out["output"][typeId][devIdoutS][0] = self.updateSensProps(out["output"][typeId][devIdoutS][0], propsOut, "i2cAddress")


						if typeId =="display":
							##self.indiLOG.log(10, "{}".format(propsOut))
							extraPageForDisplay = []
							#self.indiLOG.log(10, "{}".format(propsOut))
							for ii in range(10):
								if "extraPage{}".format(ii)+"Line0" in propsOut and "extraPage{}".format(ii)+"Line1" in propsOut and "extraPage{}".format(ii)+"Color" in propsOut:
									line0 = self.convertVariableOrDeviceStateToText(propsOut["extraPage{}".format(ii)+"Line0"])
									line1 = self.convertVariableOrDeviceStateToText(propsOut["extraPage{}".format(ii)+"Line1"])
									color = self.convertVariableOrDeviceStateToText(propsOut["extraPage{}".format(ii)+"Color"])
									extraPageForDisplay.append([line0,line1,color])
							if len(extraPageForDisplay) > 0: out["output"][typeId][devIdoutS][0]["extraPageForDisplay"]  =	 extraPageForDisplay

							for xxxx in ["scrollxy","scrollSpeed","showDateTime","scrollxy","flipDisplay","displayResolution"]:
								out["output"][typeId][devIdoutS][0] = self.updateSensProps(out["output"][typeId][devIdoutS][0], propsOut, xxxx)

						if out["output"][typeId][devIdoutS] == [{}]:
							del out["output"][typeId][devIdoutS]
					try:
						if out["output"][typeId] == {}:
							del out["output"][typeId]
					except Exception as e:
						self.indiLOG.log(30,"creating parametersfile .. please fix device {}; rpi number:{} , outdput dev not linked ?, typeId: {}, out[output]: {}".format(devOut.name, piU, typeId, out["output"]))


				out = self.writeJson(out, fName = self.indigoPreferencesPluginDir + "interfaceFiles/parameters." + piU , fmtOn=self.parametersFileSort )

		except Exception as e:
			self.exceptionHandler(40, e)
		if retFile: return out
		return

####-------------------------------------------------------------------------####
	def updateSensProps(self, sens, props, param, elseSet=None):
		if param in props and props[param] !="":
			sens[param] = props[param]
		elif  param in props and props[param] == "" and elseSet	 == "--force--":
			sens[param] = ""
		elif elseSet  is not None:
			sens[param] = elseSet

		return sens



####-------------------------------------------------------------------------####
####------------------delayed action queu management ------------------------START
####-------------------------------------------------------------------------####
	def startDelayedActionQueue(self):
		self.cancelDelayedActions = {}
		if self.delayedActions == {}:
			self.delayedActions["thread"]		= ""
			self.delayedActions["data"]		= Queue.Queue()
			self.delayedActions["lastData"]	= 0
			self.delayedActions["state"]		= ""
			self.delayedActions["lastActive"]	= 0


		if self.delayedActions["state"] == "running":
				self.indiLOG.log(10,"no need to start Thread, delayed action thread already running" )
				return

		self.indiLOG.log(10," .. (re)starting   thread for delayed actions, state was: {}".format(self.delayedActions["state"]) )
		self.delayedActions["lastCheck"] = time.time()
		self.delayedActions["state"] = "start"
		self.sleep(0.1)
		self.delayedActions["thread"]  = threading.Thread(name='self.delayedActionsThread', target=self.delayedActionsThread)
		self.delayedActions["thread"].start()
		return
###-------------------------------------------------------------------------####
	def stopDelayedActionQueue(self):

		if self.delayedActions["state"] != "running":
				self.indiLOG.log(10,"no need to stop Thread, delayed action thread already stopped" )
				return

		self.indiLOG.log(10,"Stopping   thread for delayed actions, state is: {}".format(self.delayedActions["state"]) )
		self.delayedActions["lastCheck"] = time.time()
		self.delayedActions["state"] = "stop"
		return

####-------------------------------------------------------------------------####
	def delayedActionsThread(self):
		

		"""
			structure of dict:
				basic see startDelayedActionQueue()
				action: is a dict
					devId = id of indigo dev id if present
					updateItems[] =
							{statename:name, value: value, uiValue;uiValue,image = on/off/trip }
							{remove: statename} will remove any update for a state with name statename
							"setParameters" if present = set parameters for set switchbot curtain
							"setupCARS" if present = start cars in plugin

	"""
		try:
			self.delayedActions["state"] = "running"
			pendingDisableItems ={}
			while self.delayedActions["state"] == "running":
				try:
					self.sleep(0.5)
					self.delayedActions["lastCheck"] = time.time()

					# cleanup pendingDisableItems from expired remove actions 
					for devId in copy.deepcopy(pendingDisableItems):
						if time.time() - pendingDisableItems[devId]["activeUntil"] > 0: 
							del pendingDisableItems[devId]


					addback = []
					while not self.delayedActions["data"].empty():
						if self.delayedActions["state"] != "running": break
						action = self.delayedActions["data"].get()
						self.delayedActions["lastActive"]  = time.time()

						if time.time() - action.get("activeUntil", 99999999999999) >0: continue # remove by skipping and not adding back 
						devId = action.get("devId",0)

						if devId > 0:
							thisIsRemoveAction = False
							for updateItem in action["updateItems"]:
								if "disable" in updateItem:
									if devId not in pendingDisableItems: pendingDisableItems[devId] = {}
									pendingDisableItems[devId] = {"stateName":updateItem["disable"],"activeUntil": action.get("activeUntil", action["actionTime"]+0.05)}
									thisIsRemoveAction = True
									break

							if self.decideMyLog("DelayedActions"): self.indiLOG.log(10,"delayedActionsThread time?{:.1f}; action:{} , rmitem:{}".format(time.time() - action["actionTime"], action, pendingDisableItems))
							if thisIsRemoveAction: continue

						if time.time() - action["actionTime"] < 0:
							addback.append(action)
							continue

						if devId > 0:
							try:	dev = indigo.devices[devId]
							except: continue
							execUpdate = False
							if dev.id in self.cancelDelayedActions:
								del self.cancelDelayedActions[dev.id]
								continue
							for updateItem in action["updateItems"]:
								if self.decideMyLog("DelayedActions"): self.indiLOG.log(10,"delayedActionsThread updateItem:{} ".format(updateItem))

								if updateItem == "setupCARS":
									if self.decideMyLog("DelayedActions"): self.indiLOG.log(10,"delayedActionsThread  setupCARS {}".format(dev.name))
									self.setupCARS(dev.id, dev.pluginProps, mode="init")

								if updateItem == "updateCars":
									if self.decideMyLog("DelayedActions"): self.indiLOG.log(10,"delayedActionsThread updateCars:{}; {}; {}".format(dev.address, dev.name, dev.states["status"]))
									self.updateCARS(dev.address, dev, dev.states["status"])

								elif updateItem == "OUTPUTswitchbotRelay-setParameters":
									if self.decideMyLog("DelayedActions"): self.indiLOG.log(10,"delayedActionsThread  OUTPUTswitchbotRelay-setParameters".format())
									if dev.deviceTypeId in ["OUTPUTswitchbotRelay"]: ##,"OUTPUTswitchbotCurtain"]:
										self.setSWITCHBOTBOTCALLBACKmenu({"outputDev":dev.id})

								elif  "fastDown" in updateItem:
									self.execDelaytedActionForFastDown(dev, updateItem["fastDown"])

								elif "stateName" in updateItem:
									if updateItem["stateName"] in dev.states:

										image = ""
										if "image" in updateItem:
											if   updateItem["image"].lower().find("on") > -1: 		image = "SensorOn"
											elif updateItem["image"].lower().find("off") > -1:		image = "SensorOff"
											elif updateItem["image"].lower().find("tripped") > -1:	image = "SensorTripped"

										if devId in pendingDisableItems and pendingDisableItems[devId]["stateName"] == updateItem["stateName"]:
											if time.time() - pendingDisableItems[devId]["activeUntil"] > 0: 
												del pendingDisableItems[devId]
											else:
												if self.decideMyLog("DelayedActions"): self.indiLOG.log(10,"delayedActionsThread skipping updateItem:{} ".format(updateItem))
												continue

										if updateItem["value"] != dev.states[updateItem["stateName"]]:
											execUpdate = True
											if self.decideMyLog("DelayedActions"): self.indiLOG.log(10,"delayedActionsThread executing dev.states[stateName]:{}  updateItem:{} , image:{}".format(dev.states[updateItem["stateName"]], updateItem, image))
											if "uiValue" in updateItem:
												self.addToStatesUpdateDict(dev.id, updateItem["stateName"],updateItem["value"], uiValue=updateItem["uiValue"], image=image)
											else:
												self.addToStatesUpdateDict(dev.id, updateItem["stateName"],updateItem["value"], image=image)
											self.alertGarageDoor(dev.id)
										else:
											if self.decideMyLog("DelayedActions"): self.indiLOG.log(10,"delayedActionsThread skipping state has not changed, no update")
									else:
										if self.decideMyLog("DelayedActions"): self.indiLOG.log(10,"delayedActionsThread skipping due to cond not met; statename:{} not in dev.states".format(updateItem["stateName"]))
								else:
									if self.decideMyLog("DelayedActions"): self.indiLOG.log(10,"delayedActionsThread skipping due to cond not met")

							if execUpdate: self.executeUpdateStatesDict(onlyDevID=dev.id)


					for action in addback:
						self.delayedActions["data"].put(action)
				except Exception as e:
					self.exceptionHandler(40, e)
					self.sleep(3)

		except Exception as e:
			self.exceptionHandler(40, e)
		self.delayedActions["state"] = "stopped - exiting thread"
		self.indiLOG.log(10,"delayedActions  update thread stopped, state is:{}".format(self.delayedActions["state"]) )
		return

###-------------------------------------------------------------------------####
####------------------delayed action queue management -----------------------end
###-------------------------------------------------------------------------####




####------------------rpi update queue management ----------------------------START
####------------------rpi update queue management ----------------------------START
####------------------rpi update queue management ----------------------------START

####-------------------------------------------------------------------------####
	def startUpdateRPIqueues(self, state, piSelect="all"):
		try:
			if self.rpiQueues == {}:
				self.initrpiQueues()

			if state =="start":
				self.laststartUpdateRPIqueues = time.time()
				self.indiLOG.log(5,"starting UpdateRPIqueues ")
				for piU in self.RPI:
					if self.RPI[piU]["piOnOff"] != "1": continue
					if piSelect == "all" or piU == piSelect:
							self.startOneUpdateRPIqueue(piU)

			elif state == "restart":
				if (piSelect == "all" and time.time() - self.laststartUpdateRPIqueues > 70) or piSelect != "all":
					self.laststartUpdateRPIqueues = time.time()
					for piU in self.RPI:
						if self.RPI[piU]["piOnOff"] != "1": continue
						if piSelect == "all" or piU == piSelect:
							if piU not in self.rpiQueues["state"]: 
								self.startOneUpdateRPIqueue(piU, reason="not running")
								self.sleep(0.2)
							if time.time() - self.rpiQueues["lastCheck"][piU] > 100:
								self.stopUpdateRPIqueues(piSelect=piU)
								time.sleep(0.5)
							if  time.time() - self.rpiQueues["lastCheck"][piU] > 100:
								self.startOneUpdateRPIqueue(piU, reason="active messages pending timeout")
							elif self.rpiQueues["state"][piU] != "running":
								self.startOneUpdateRPIqueue(piU, reason="not running")
		except Exception as e:
			self.exceptionHandler(40, e)
		return

####-------------------------------------------------------------------------####
	def initrpiQueues(self):
		self.rpiQueues = {}
		self.rpiQueues["reset"]			= {}
		self.rpiQueues["data"]			= {}
		self.rpiQueues["state"]			= {}
		self.rpiQueues["lastActive"]	= {}
		self.rpiQueues["lastCheck"]		= {}
		self.rpiQueues["thread"] 		= {}
		self.rpiQueues["lastData"] 		= {}
		self.rpiQueues["busy"] 			= {}
		return 
####-------------------------------------------------------------------------####
	def startOneUpdateRPIqueue(self, piU, reason=""):
		try:		
			if "state"  not in self.rpiQueues: 
				self.initrpiQueues()

			if self.RPI[piU]["piOnOff"] != "1": return


			if piU in self.rpiQueues["state"]:
				if self.rpiQueues["state"][piU] == "running":
					self.indiLOG.log(10,"no need to start Thread, pi# {} thread already running".format(piU) )
					return
			else:
				self.rpiQueues["reset"][piU]		= 0
				self.rpiQueues["data"][piU]			= Queue.Queue()
				self.rpiQueues["state"][piU]		= ""
				self.rpiQueues["lastActive"][piU]	= time.time() - 900000
				self.rpiQueues["lastCheck"][piU]	= time.time() - 900000
				self.rpiQueues["lastData"][piU]		= ""
				self.rpiQueues["busy"][piU]			= 0

			self.indiLOG.log(10," .. (re)starting   thread for pi# {}, state was : {} - {}".format(piU, self.rpiQueues["state"][piU], reason) )
			self.rpiQueues["lastCheck"][piU] = time.time()
			self.rpiQueues["state"][piU]	= "start"
			self.sleep(0.1)
			self.rpiQueues["thread"][piU]  = threading.Thread(name='self.rpiUpdateThread', target=self.rpiUpdateThread, args=(piU,))
			self.rpiQueues["thread"][piU].start()
		except Exception as e:
			self.exceptionHandler(40, e)
		return
###-------------------------------------------------------------------------####
	def stopUpdateRPIqueues(self, piSelect="all"):
		self.rpiQueues["reset"]		= {}
		for piU in self.RPI:
			if piU == piSelect or piSelect == "all":
				self.stopOneUpdateRPIqueues(piU, reason="; "+ piSelect+";")
		return
###-------------------------------------------------------------------------####
	def stopOneUpdateRPIqueues(self, piU, reason=""):
		self.rpiQueues["state"][piU]	= "stop "+reason
		self.rpiQueues["reset"][piU]	= 1
		self.indiLOG.log(10,"w () , state is: {}".format(piU, self.rpiQueues["state"][piU]) )
		return


####-------------------------------------------------------------------------####
	def sendFilesToPiFTP(self, piU, expFile="",endAction="repeatUntilFinished"):
		if piU not in self.rpiQueues["state"]: return 
		if time.time() - self.rpiQueues["lastCheck"][piU] > 100 or self.rpiQueues["state"][piU] != "running":
			self.startUpdateRPIqueues("restart", piSelect=piU)

		next = {"pi":piU, "expFile":expFile, "endAction":endAction, "type":"ftp", "tries":0, "exeTime":time.time()}
		self.removeONErPiV(piU, "piUpToDate", [expFile])
		if self.testIfAlreadyInQ(next,piU): 	return
		if self.decideMyLog("UpdateRPI"): self.indiLOG.log(5,"FTP adding to update list {}".format(next) )
		self.rpiQueues["data"][piU].put(next)
		return
####-------------------------------------------------------------------------####
	def sshToRPI(self, piU, expFile="", endAction="repeatUntilFinished"):
		if time.time() - self.rpiQueues["lastCheck"][piU] > 100:
			self.startUpdateRPIqueues("restart", piSelect=piU)

		next = {"pi":piU, "expFile":expFile, "endAction":endAction, "type":"ssh", "tries":0, "exeTime":time.time()}
		self.removeONErPiV(piU, "piUpToDate", [expFile])
		if self.testIfAlreadyInQ(next,piU): 	return
		if self.decideMyLog("UpdateRPI"): self.indiLOG.log(5,"SSH adding to update list {}".format(next) )
		self.rpiQueues["data"][piU].put(next)
		return
####-------------------------------------------------------------------------####
	def resetUpdateQueue(self, piU):
		if "reset"  not in self.rpiQueues:
			self.initrpiQueues()
		self.rpiQueues["reset"][piU] = 2
		return
####-------------------------------------------------------------------------####
	def testIfAlreadyInQ(self, next, piU):
		if piU not in self.rpiQueues["data"]:
			self.startOneUpdateRPIqueue(piU) 
		currentQueue = list(self.rpiQueues["data"][piU].queue)
		for q in currentQueue:
			if q["pi"] == next["pi"] and q["expFile"] == next["expFile"]:
				if self.decideMyLog("UpdateRPI"): self.indiLOG.log(5,"FTP NOT adding to update list already presend {}".format(next) )
				return True
		return False

####-------------------------------------------------------------------------####
	def rpiUpdateThread(self,piU):
		try:
			if piU not in self.rpiQueues["state"]: return 
			self.rpiQueues["state"][piU] = "running"
			self.rpiQueues["busy"][piU]	= 0
			if self.decideMyLog("UpdateRPI"): self.indiLOG.log(10,"rpiUpdateThread starting  for pi# {}".format(piU) )
			while self.rpiQueues["state"][piU] == "running":
				self.rpiQueues["lastCheck"][piU]  = time.time()
				time.sleep(0.7)
				addBack = []
				while not self.rpiQueues["data"][piU].empty():
					self.rpiQueues["lastActive"][piU]  = time.time()
					next = self.rpiQueues["data"][piU].get()
					self.rpiQueues["lastData"][piU] = "{}".format(next)
					##if self.decideMyLog("UpdateRPI"): self.indiLOG.log(10,"reset on/off  update queue for pi#{} .. {}".format(piU, self.rpiQueues["reset"][piU]) )

					if self.RPI[piU]["piOnOff"] == "0":
						if self.decideMyLog("UpdateRPI"): self.indiLOG.log(10,"rpiUpdateThread skipping;  Pi#: {} is OFF".format(piU) )
						self.rpiQueues["reset"][piU] = 3
						break
					if self.decideMyLog("UpdateRPI"): self.indiLOG.log(10,"rpiUpdateThread executing  {}".format(next) )
					if piU != "{}".format(next["pi"]):
						if self.decideMyLog("UpdateRPI"): self.indiLOG.log(10,"rpiUpdateThread skipping; pi numbers wrong  {} vs {} ".format(piU, next["pi"]) )
						continue
					if self.RPI[piU]["piOnOff"] == "0":
						if self.decideMyLog("UpdateRPI"): self.indiLOG.log(10,"rpiUpdateThread skipping;  Pi#: {} is OFF".format(piU) )
						continue
					if self.RPI[piU]["ipNumberPi"] == "":
						if self.decideMyLog("UpdateRPI"): self.indiLOG.log(10,"rpiUpdateThread skipping pi#:{}  ip number blank".format(piU)  )
						continue
					if piU in self.rpiQueues["reset"] and self.rpiQueues["reset"][piU] != 0:
						if self.decideMyLog("UpdateRPI"): self.indiLOG.log(10,"rpiUpdateThread resetting queue data for pi#:{}, reason:{}".format(piU, self.rpiQueues["reset"][piU]) )
						continue
					try:
						id = int(self.RPI[piU]["piDevId"])
						if id != 0 and id in indigo.devices  and not indigo.devices[id].enabled:
							self.rpiQueues["reset"][piU] = 4
							if self.decideMyLog("OfflineRPI"): self.indiLOG.log(10,"device {} not enabled, no sending to RPI".format(indigo.devices[id].name) )
							continue
					except Exception as e:
						if "{}".format(e) != "None":
							self.exceptionHandler(40, e)
							self.indiLOG.log(10,"setting update queue for pi#{} to empty".format(piU))
						self.rpiQueues["reset"][piU] = 5

					# time for sending?
					if next["exeTime"] > time.time():
						addBack.append((next)) # no , wait
						continue
					self.rpiQueues["busy"][piU]	= time.time()

					if next["type"] == "ftp":
						retCode = self.execSendFilesToPiFTP(piU, expFile=next["expFile"], endAction= next["endAction"])
					else:
						retCode = self.execSshToRPI(piU, expFile=next["expFile"], endAction= next["endAction"])

					if retCode ==0: # all ok?
						self.setRPIonline(piU)
						self.RPI[piU]["lastMessage"] = time.time()
						continue

					else: # some issues
						next["tries"] +=1
						next["exeTime"]  = time.time()+5

						if 5 < next["tries"] and next["tries"] < 10: # wait a little longer
							if self.decideMyLog("UpdateRPI"): self.indiLOG.log(10,"last updates were not successful wait, then try again")
							next["exeTime"] = time.time()+10

						elif next["tries"] > 9:  # wait a BIT longer before trying again
							if self.decideMyLog("OfflineRPI"): self.indiLOG.log(10,"rPi update delayed due to failed updates rPI# {}".format(piU) )
							self.setRPIonline(piU, new="offline")
							next["exeTime"]  = time.time()+20
							next["tries"] = 0

						addBack.append(next)
				try: 	self.rpiQueues["data"][piU].task_done()
				except: pass
				if addBack !=[]:
					for nxt in addBack:
						self.rpiQueues["data"][piU].put(nxt)
				self.rpiQueues["reset"][piU] = 0
		except Exception as e:
			self.exceptionHandler(40, e)
		self.rpiQueues["state"][piU] = "stopped - exiting thread"
		self.indiLOG.log(10,"rpi: {}  update thread stopped, state is:{}".format(piU,self.rpiQueues["state"][piU] ) )
		return



####-------------------------------------------------------------------------####
	def execSendFilesToPiFTP(self, piU, expFile="updateParamsFTP.exp",endAction="repeatUntilFinished"):

		try:
			if self.decideMyLog("UpdateRPI"): self.indiLOG.log(10,"enter  sendFilesToPiFTP #{}  expFile:".format(piU, expFile) )
			if expFile=="updateParamsFTP.exp": self.newIgnoreMAC = 0
			self.lastUpdateSend = time.time()


			pingR = self.testPing(self.RPI[piU]["ipNumberPi"])
			if pingR != 0:
				if self.decideMyLog("OfflineRPI") or self.decideMyLog("UpdateRPI"): self.indiLOG.log(10," pi server # {}  PI# {}    not online - does not answer ping - , skipping update".format(piU, self.RPI[piU]["ipNumberPi"]) )
				self.setRPIonline(piU,new="offline")
				return 1, ["ping offline",""]

			prompt = self.getPasswordSshPrompt(piU,expFile)
			hostCheck = self.getHostFileCheck(piU)

			cmd = "/usr/bin/expect '" + self.pathToPlugin + expFile + "' "
			cmd+=	self.RPI[piU]["userIdPi"] + " " + self.RPI[piU]["passwordPi"]+" " + prompt+" "
			cmd+=	self.RPI[piU]["ipNumberPi"] + " "
			cmd+=	piU + " '" + self.indigoPreferencesPluginDir + "' '" + self.pathToPlugin + "pi' "+self.expectTimeout+ " "+hostCheck

			if self.decideMyLog("UpdateRPI"): self.indiLOG.log(10,"updating pi server config for # {} executing\n{}".format(piU, cmd) )
			ret, err = self.readPopen(cmd)

			if expFile == "upgradeOpSysSSH.exp" :
				return 0

			if len(err) > 0:
				ok = self.fixHostsFile(ret, err, piU)
				if not ok: return 0
				self.indiLOG.log(10,"return code from fix {}  trying again to configure PI".format(ret))
				ret, err = self.readPopen(cmd)

			if ret[-600:].find("sftp> ") > -1:
				if self.decideMyLog("UpdateRPI"): self.indiLOG.log(10,"UpdateRPI seems to have been completed for pi# {}  {}".format(piU, expFile) )
				return 0
			else:
				self.sleep(2)  # try it again after 2 seconds
				ret, err = self.readPopen(cmd)
				if ret[-600:].find("sftp> ") > -1:
					if self.decideMyLog("UpdateRPI"): self.indiLOG.log(10,"UpdateRPI seems to have been completed for pi# {}  {}".format(piU, expFile) )
					return 0
				else:
					self.indiLOG.log(10,"setup pi response (2) message>>>> \n{}\n<<<<<<".format(ret.strip("\n")) )
				return 1
			return 0
		except Exception as e:
			self.exceptionHandler(40, e)
		return 1




####-------------------------------------------------------------------------####
	def execSshToRPI(self, piU, expFile="", endAction="repeatUntilFinished"):

		try:
			if self.testPing(self.RPI[piU]["ipNumberPi"]) != 0:
				if self.decideMyLog("OfflineRPI") or self.decideMyLog("UpdateRPI"): self.indiLOG.log(10," pi server # {} PI# {}  not online - does not answer ping - , skipping update".format(piU, self.RPI[piU]["ipNumberPi"] ))
				if endAction =="repeatUntilFinished":
					return 1
				else:
					return 0

			if expFile in ["shutdownSSH.exp", "rebootSSH.exp", "resetOutputSSH.exp", "shutdownSSH.exp"]:
				batch =" &"
			else:
				batch =" "

			prompt = self.getPasswordSshPrompt(piU, expFile)
			checkHostfile = self.getHostFileCheck(piU)
			cmd = "/usr/bin/expect '" + self.pathToPlugin + expFile+"'  " + self.RPI[piU]["userIdPi"] + " " + self.RPI[piU]["passwordPi"] + " " + prompt+" "+ self.RPI[piU]["ipNumberPi"]+ " "+self.expectTimeout+ " "+checkHostfile+ " "+batch

			if self.decideMyLog("UpdateRPI") : self.indiLOG.log(5,expFile+" Pi# {}\n{}".format(piU, cmd) )
			if batch == " ":
				ret, err = self.readPopen(cmd)
				if self.decideMyLog("UpdateRPI"): self.indiLOG.log(5,"response: {} - {}".format(ret, err) )
				if len(err) > 0:
					ok = self.fixHostsFile(ret, err, piU)
					if not ok:
						if endAction =="repeatUntilFinished":
							return 1
						else:
							return 0
					ret, err = self.readPopen(cmd)

			else:
				ret, err = self.readPopen(cmd)

			if expFile.find("shutdown") >-1:
				return 0

			tag ="\nPi#{} - ".format(piU)

			if len(err) > 0:
				err= err.replace("\n\n", "\n").replace("\n", tag)
				self.indiLOG.log(10,"{} Pi# {}  {}".format(expFile, piU, err) )

			if expFile.find("getStats") >-1:
				try:
					ret1= ((ret.split("===fix==="))[-1]).replace("\n\n", "\n").replace("\n", tag)
					self.indiLOG.log(10,"stats from Pi# {}{}{}{}Stats end ===========".format(piU, tag, ret, tag ) )
				except:
					self.indiLOG.log(10,"stats from Pi# {} raw \n {} \n errors:\n{}" .format(piU, ret.replace("\n\n", "\n"), err.replace("\n\n", "\n")) )

				return 0

			if expFile.find("getLogFileSSH") >-1:
				try:
					ret1= ( ( (ret.split("tail -1000 /var/log/pibeacon.log"))[1] ).split("echo 'end token' >")[0] ).replace("\n\n", "\n").replace("\n", tag)
					self.indiLOG.log(10,"{}pibeacon logfile from Pi# {}  ==============:  {}{}{}pibeacon logfile  END    ===================================\n".format(tag, piU, tag, ret1,tag) )
				except Exception as e:
					if "{}".format(e) != "None":
						self.exceptionHandler(40, e)
						self.indiLOG.log(10,"pibeacon logfile from Pi# {} raw \n {} \n errors:\n{}" .format(piU, ret.replace("\n\n", "\n"), err.replace("\n\n", "\n")) )

				return 0

			return 0

		except Exception as e:
			self.exceptionHandler(40, e)
		return 1




####-------------------------------------------------------------------------####
	def getPasswordSshPrompt(self, piU,expFile):
		prompt = "assword"
		if self.RPI[piU]["authKeyOrPassword"] == "login:":
			if expFile.find("FTP") >-1:
				prompt ="connect"
			else:
				prompt ="login:"

		return prompt


####-------------------------------------------------------------------------####
	def getHostFileCheck(self, piU):
		if self.RPI[piU]["hostFileCheck"] == "ignore":
			return "'-o StrictHostKeyChecking=no'"
		return ""


####-------------------------------------------------------------------------####
	def fixHostsFile(self, ret, err, pi):
		try:
			piU = "{}".format(pi)
			self.indiLOG.log(20,"fixHostsFile .ssh/known_hosts  for pi{} response \nret:{}\nerr:{}".format(piU, ret, err))
			if ret.find(".ssh/known_hosts:") > -1:
				ipN = self.RPI[piU]["ipNumberPi"]
				self.indiLOG.log(30,"trying to fix from within plugin (deleting line for pi:{} @ {}), if it happens again you need to do it manually".format(piU, ipN))
				try:

					f = open(self.MAChome+'/.ssh/known_hosts', "r")
					lines  = f.readlines()
					f.close()

					f = open(self.MAChome+'/.ssh/known_hosts', "w")
					for line in lines:
						if len(line) < 10: continue
						if line.find(ipN) > -1:
							self.indiLOG.log(30,"removing line:{}".format(line))
							continue
						f.write(line.strip("\n")+"\n")
					f.close()

				except Exception as e:
					self.exceptionHandler(40, e)

		except Exception as e:
			self.exceptionHandler(40, e)
		return  True

####------------------rpi update queue management ----------------------------END
####------------------rpi update queue management ----------------------------END
####------------------rpi update queue management ----------------------------END



####-------------------------------------------------------------------------####
	def configureWifi(self, pi):
		return
		try:
			self.setupFilesForPi(calledFrom="configureWifi")
		except Exception as e:
			self.exceptionHandler(40, e)
		return

####-------------------------------------------------------------------------####
	def testPing(self, ipN):
		try:
			ss = time.time()
			ret = subprocess.call("/sbin/ping  -c 1 -W 40 -o " + ipN, shell=True) # send max 2 packets, wait 40 msec   if one gets back stop
			if self.decideMyLog("UpdateRPI"): self.indiLOG.log(5," sbin/ping  -c 1 -W 40 -o {} return-code: {}".format(ipN, ret) )

			#indigo.server.log(  ipN+"-1  {}".format(ret) +"  {}".format(time.time() - ss)  )

			if int(ret) ==0:  return 0
			self.sleep(0.1)
			ret = subprocess.call("/sbin/ping  -c 1 -W 400 -o " + ipN, shell=True)
			if self.decideMyLog("UpdateRPI"): self.indiLOG.log(5,"/sbin/ping  -c 1 -W 400 -o {} ret-code: ".format(ipN, ret) )

			#indigo.server.log(  ipN+"-2  {}".format(ret) +"  {}".format(time.time() - ss)  )

			if int(ret) ==0:  return 0
			return 1
		except Exception as e:
			self.exceptionHandler(40, e)

		#indigo.server.log(  ipN+"-3  {}".format(ret) +"  {}".format(time.time() - ss)  )
		return 1


####-------------------------------------------------------------------------####
	def printBeaconsIgnoredButton(self, valuesDict=None, typeId=""):

		############## list of beacons in history
		#				  1234567890123456	1234567890123456789012 1234567890 123456 123456789
		#				  75:66:B5:0A:9F:DB beacon-75:66:B5:0A:9   expired		   0	  1346
		self.myLog( theText = "#	defined beacons-------------", mType="pi configuration")
		self.myLog( theText = "indigoName                 indigoId Status enabled               type txMin ignore Pos X,Y,Z   fastDw sigDlt min-on/off batteryUUID lastUpdate/level         LastUp[s] ExpTime updDelay lastStatusChange    created ", mType= "pi configuration")
		for status in ["ignored", ""]:
			for beaconDeviceType in self.knownBeaconTags["input"]:
				self.printBeaconInfoLine(status, beaconDeviceType)

####-------------------------------------------------------------------------####
	def printHelpActionsCALLBACKmenu(self, x="",y="",z=""):
		try:
			helpText  = '  \n'
			helpText += '=============== help for ACTIONS triggered by distance sensors  eg at stop, dist > xx dist < yy etc          ======  \n'
			helpText += '  \n'
			helpText += '  \n'
			helpText += '====  They are executed w/o indigo directly on the RPI sensor -> GPIO or neopixel or display   \n'
			helpText += 'first setup distance limits eg VerShort= 5, Short =20, Long=100, VeryLong=200 cm  \n'
			helpText += '            and time and speed limit for STOP state; (minimum time speed has to be below speed limit for stop action to trigger  \n'
			helpText += '====  EXAMPLES for actions, esstially any valid unix command is ok  \n'
			helpText += '==== \n'
			helpText += 'Simple unix command \n'
			helpText += ' will print the directory to a file temp/thisIsTheDirectory  \n'
			helpText += ' ls -l  > temp/thisIsTheDirectory  \n'
			helpText += '  \n'
			helpText += '==== \n'
			helpText += 'SET GPIO output \n'
			helpText += ' set gpio 18 on, wait 1 sec, set gpio 18 off, and print timestamp to pibeacon logfile:  \n'
			helpText += ' gpio -g mode 18 out;gpio -g write 18 1;sleep 1;gpio -g write 18 0; date >> /var/log/pibeacon  \n'
			helpText += '  \n'
			helpText += '=====  \n'
			helpText += 'NEOPIXEL, set LEDs on neopixel device on/off, blink,..  \n'
			helpText += ' The "status" value (any text you like, but no spaces) will be shown in the neopixel indigo device status \n'
			helpText += ' The neopixel syntax is the the same as for neopixel actions in indigo. You can set one up there and switch on debug output \n'
			helpText += '       then in the logfile you can see the commands like the ones below send to the neopixel device on the RPI\n'
			helpText += ' The following is assumimg an LED chain of 8 LED (LED#s: 0-7)  is setup as a neopixel output indigo device on the same RPI \n'
			helpText += '  \n'
			helpText += ' -Blinking red  every 0.2 secs, LED 0-7, RGB= 255,0,0 and 0,0,0:  sl or sLine = simpleline  p=[start LED,end LED,R,G,B]   send "VeryShort" to indigo status  \n'
			helpText += ' echo \'{"status":"VeryShort","repeat":1000,"command":[{"delayStart":0.2,"type":"sl","p":[0,7,255,0,0]},{"delayStart":0.4,"type":"sl","p":[0,7,0,0,0]}]}\' > temp/neopixel.inp  \n'
			helpText += '  \n'
			helpText += ' -simple red line LED 0-7, RGB= 255,0,0: p=[start LED,end LED,R,G,B]  \n'
			helpText += ' echo \'{"status":"Short","command":[{"type":"sl","p":[0,7,255,0,0]}]}\' > temp/neopixel.inp  \n'
			helpText += '  \n'
			helpText += ' -simple yellow line LED 2-3, RGB= 20,20,0 p=[start LED,end LED,R,G,B]; send "ThisIsEnaExample-Medium" to indigo status and reset all LED before start:  \n'
			helpText += ' echo \'{"status":"ThisIsEnaExample-Medium","res":"[0,0,0]","command":[{"type":"sl","p":[2,3,20,20,0]}]}\' > temp/neopixel.inp  \n'
			helpText += '  \n'
			helpText += ' -simple blueLine LED 5-7, RGB= 0,0,30;  send "Long" to indigo status and reset all LED before start:\n'
			helpText += ' echo \'{"status":"Long","res":"[0,0,0]","command":[{"type":"sl","p":[5,7,0,0,30]}]}\' > temp/neopixel.inp  \n'
			helpText += '  \n'
			helpText += ' -knightRider: send "knightrider" to indigo status, swinging green LED 3-4 making 8 steps right - left every 0.2s  p=[wait between steps, # of steps left and right, led-start, led-end, R,G,B]:  \n'
			helpText += ' echo \'{"status":"knightrider","res":"[0,0,0]","command":[{"type":"kr","p":[0.2,8,3,4,0,30,0]}]}\' > temp/neopixel.inp  \n'
			helpText += '  \n'
			helpText += ' -colorknightRider:  send "color" to indigo status,  swinging 3 LEDs (red,green,blue) #3,4,5 making 10 steps right - left every 0.1s  p=[wait between steps, # of steps left and right, led-start R1,G1,B1, R2,G2,B2,..., Rn,Gn,Bn]:  \n'
			helpText += ' echo \'{"status":"color","res":"[0,0,0]","command":[{"type":"ckr","p":[0.1, 10, 3,   30,0,0,   0,30,0,   0,0,30]}]}\' > temp/neopixel.inp  \n'
			helpText += '  \n'
			helpText += ' -clear  send "Stop" to indigo status and clear LEDs \n'
			helpText += ' echo \'{"status":"Stop","res":"[0,0,0]"}\' > temp/neopixel.inp  \n'
			helpText += '  \n'
			helpText += '  \n'
			helpText += '=============== help for GPIO or neopixel actions triggered by distance sensors                       END    ======  \n'
			self.myLog( theText = helpText, destination="standard")
		except Exception as e:
			self.exceptionHandler(40, e)



	def printHelp(self):
		try:
			helpText  = '  \n'
			helpText += '=============== setup HELP ======  \n'
			helpText += '  \n'
			helpText += '  To START,  here the basic steps:   \n'
			helpText += '  1.  in CONFIG setup at minimum userID,PassWD, ipNumber of indigo server    n'
			helpText += '  2.  Setup of physical rPi servers:    \n'
			helpText += '      ssh pi@ipnumber      password default = pibeacon    \n'
			helpText += '      passwd                   to change default pasword    \n'
			helpText += '      sudo raspi-config    to set time zone, expand SD ..,   \n'
			helpText += '         get ip number of RPI w ifconfig  \n'
			helpText += '  3.  in menu   Initial BASIC setup of rPi servers      \n'
			helpText += '          set ipNumber, userID, password of RPI# x (0-19)  \n'
			helpText += '  \n'
			helpText += '  4. Now wait until the first ibeacon and RPI devices show up in indigo  \n'
			helpText += '    If nothing happens, do a  Send Config/Restart/PGM/Sound/...       \n'
			helpText += '    to send all files to RPI, then  \n'
			helpText += '    ssh to RPI and check programs that are running: ps -ef | grep .py  \n'
			helpText += '       At minimum master.py, beaconloop.py, receiveGPIOcommands.py   \n'
			helpText += '           should be running  \n'
			helpText += '       if installLibs.py is running, it is updating op-sys files.   \n'
			helpText += '           That might take several hours  \n'
			helpText += '  5. You then want to disable accept new beacons in config  \n'
			helpText += '     any car driving by likely has some beacons sending messages.  \n'
			helpText += '     To add new beacons set accept new beacons to eg -60  dBm  \n'
			helpText += '       Put your new beacon onto the rpi, wait a minute  \n'
			helpText += '          and check the new beacon(s) created  \n'
			helpText += '       Set accept new beacons to off in config  \n'
			helpText += '       Then move the beacon far away and check again,   \n'
			helpText += '          find the beacon that has the signal reduced  \n'
			helpText += '       Then move it back to the RPI and check if signal is high again.  \n'
			helpText += '       Then set the beacon at 1m distance and note the signal strength.   \n'
			helpText += '         Edit the beacon and set TX power to that value(it is likely ~ -60).   \n'
			helpText += '         That will make the distance calulation more accurate  \n'
			helpText += '  \n'
			helpText += '  Other remarks...  \n'
			helpText += '  1. Some beacon types are automatically recognized by the plugin:  see section below\n'
			helpText += '     checkout the file "knownBeaconTags.full_copy_to_use_as_example"  \n'
			helpText += '     in the plugin prefrence directory for a full list  \n'
			helpText += '     Using these types makes your live much easier  \n'
			helpText += '  2. It is advisable to have at least 2 RPI that "see" each other (in bluetooth range)  \n'
			helpText += '     that makes the overall system more stable and enables   \n'
			helpText += '     location mapping in x,y,z coordinates  \n'
			helpText += '     The location mapping gets much better if you have an RPI in each room  \n'
			helpText += '  \n'
			helpText += '=============== END setup HELP ===========  \n'
			helpText += '  \n'
			helpText += '  \n'

# /Library/Application Support/Perceptive Automation/Indigo 7.4/Plugins/piBeacon.indigoPlugin/Contents/Server Plugin/
			filesIn   = self.pathToPlugin.split("Server Plugin/")[0]
			helpText += '  for changelog: check out {}changelist.txt  \n'.format(filesIn)
			helpText += '  \n'
			helpText += '  \n'
			f = open(filesIn+"beaconTypes.txt","r")
			fff = f.read()
			f.close()
			helpText += '=============== BEACONS            ===========  \n'
			helpText += fff
			helpText += '=============== BEACONS     .. END ===========  \n'

			f = open(filesIn+"BLE-sensorTypes.txt","r")
			fff = f.read()
			f.close()

			helpText += '  \n'
			helpText += '=============== BLE-Sensors        ===========  \n'
			helpText += fff
			helpText += '=============== BLE SENSORS .. END ===========  \n'
			helpText += '  \n'
			self.myLog( theText = helpText, destination="")
			self.myLog( theText = helpText, destination="standard")
		except Exception as e:
			self.exceptionHandler(40, e)


####-------------------------------------------------------------------------####
	def printConfig(self):
		try:
			self.myLog( theText = " ========== Parameters START ================",															mType= "pi configuration")
			self.myLog( theText = "data path used               {}" .format(self.indigoPreferencesPluginDir),								mType= "pi configuration")
			self.myLog( theText = "path for Pi_IN_xx            {}" .format(self.iBeaconFolderVariableDataTransferVarsName),				mType= "pi configuration")
			self.myLog( theText = "path for status variables    {}" .format(self.iBeaconFolderVariablesName),								mType= "pi configuration")
			self.myLog( theText = "debugLevel Indigo            {}-".format(self.debugLevel),												mType= "pi configuration")
			self.myLog( theText = "debug which Pi#              {} ".format(self.debugRPI),													mType= "pi configuration")
			self.myLog( theText = "maxSizeOfLogfileOnRPI        {}" .format(self.pluginPrefs.get("maxSizeOfLogfileOnRPI", 10000000)),		mType= "pi configuration")
			self.myLog( theText = "automaticRPIReplacement      {}" .format(self.automaticRPIReplacement),									mType= "pi configuration")
			self.myLog( theText = "myIp Number                  {}" .format(self.myIpNumber),												mType= "pi configuration")
			self.myLog( theText = "check RPI ip if registered   {}; turn off if rpi is in separate subnet" .format(self.checkRPIipForReject), mType= "pi configuration")
			self.myLog( theText = "blockNonLocalIp              {}" .format(self.blockNonLocalIp),											mType= "pi configuration")
			self.myLog( theText = ".. ip#s accepted             {}.{}.x.x" .format(self.myIpNumberRange[0],self.myIpNumberRange[1]),		mType= "pi configuration")
			self.myLog( theText = "port# of indigoWebServer     {}" .format(self.portOfServer),												mType= "pi configuration")
			self.myLog( theText = "indigo UserID                ....{}" .format(self.userIdOfServer[4:]),									mType= "pi configuration")
			self.myLog( theText = "indigo Password              ....{}" .format(self.passwordOfServer[4:]),									mType= "pi configuration")
			self.myLog( theText = "wifi OFF if ETH0             {}" .format(self.wifiEth),													mType= "pi configuration")
			self.myLog( theText = "Seconds UP to DOWN           {}" .format(self.secToDown),												mType= "pi configuration")
			self.myLog( theText = "beacon indigo folder Name    {}" .format(self.iBeaconDevicesFolderName),									mType= "pi configuration")
			self.myLog( theText = "accept newiBeacons           {}" .format(self.acceptNewiBeacons),										mType= "pi configuration")
			self.myLog( theText = "recycle indigo varibles      {}" .format(self.cycleVariables),											mType= "pi configuration")
			self.myLog( theText = "distance Units               {}; 1=m, 0.01=cm , 0.0254=in, 0.3=f, 0.9=y".format(self.distanceUnits),		mType= "pi configuration")
			self.myLog( theText = "", 																										mType= "pi configuration")
			self.myLog( theText = " ========== EXPERT parameters for each PI:----------", 													mType= "pi configuration")
			self.myLog( theText = "port# on rPi 4 GPIO commands {}" .format(self.rPiCommandPORT),											mType= "pi configuration")
			self.myLog( theText = " ",																										mType= "pi configuration")

			self.myLog( theText = "beacon-MAC        indigoName                 Pos X,Y,Z    indigoID UserID    Password       If-rPI-Hangs   SensorAttached",mType= "Raspberry Pis")
			for piU  in self.RPI:
				try:
					pi = int(piU)
					if self.RPI[piU]["piDevId"] == 0:	 continue
					try:
						dev = indigo.devices[self.RPI[piU]["piDevId"]]
					except Exception as e:
						if "{}".format(e).find("timeout waiting") > -1:
							self.exceptionHandler(40, e)
							self.indiLOG.log(40,"communication to indigo is interrupted")
							return

						self.exceptionHandler(40, e)
						self.indiLOG.log(40,"self.RPI[piU][piDevId] not defined for pi: {}".format(piU))
						continue
					line = ""
					#line += self.RPI[piU]["ipNumberPi"].ljust(15) + " "
					line += self.RPI[piU]["piMAC"].rjust(17) + " "
					line += (dev.name).ljust(25) + " "
					if piU  in _rpiBeaconList:
						line += ("{}".format(dev.states["PosX"]).split(".")[0] + ",{}".format(dev.states["PosY"]).split(".")[0] + ",{}".format(dev.states["PosZ"]).split(".")[0]).rjust(10)
					else:
						line+=" ".rjust(10)
					line += "{}".format(self.RPI[piU]["piDevId"]).rjust(12) + " "
					line += self.RPI[piU]["userIdPi"].ljust(10) + " "
					line += self.RPI[piU]["passwordPi"].ljust(15)
					line += self.RPI[piU]["enableRebootCheck"].ljust(14)
					## make nice list at end of line
					line += self.makLineForSensors(piU)
					onOff= " on"
					if self.RPI[piU]["piOnOff"] != "1": onOff = "off"
					self.myLog( theText = line, mType= f"pi#: {pi:2d} {onOff} {self.RPI[piU]['ipNumberPi']}")
				except Exception as e:
					self.exceptionHandler(40, e)
					self.indiLOG.log(40,"RPI#{} has problem:  disabled?".format(piU))
		


			self.myLog( theText = "", mType="pi configuration")
			if len(self.CARS["carId"]) > 0:
				self.myLog( theText = " ===================================", mType="CARS")
				self.myLog( theText = "CAR device-------------       HomeS     AwayS    BAT-beacon                     USB-beacon                     KEY0-beacon                    KEY1-beacon                    KEY2-beacon", mType= "pi configuration")
				bNames = ["beaconBattery", "beaconUSB", "beaconKey0", "beaconKey1", "beaconKey2"]
				bN = [" ", " ", " ", " ", " "]
				bF = [" ", " ", " ", " ", " "]
				for dd in self.CARS["carId"]:
					carDevId = int(dd)
					carDev	= indigo.devices[carDevId]
					props	= carDev.pluginProps
					carName =(carDev.name).strip().ljust(30)
					for nn in range(len(bNames)):
						beaconType= bNames[nn]
						try:
							beaconId = int(props[beaconType])
							if beaconId == 0: continue
						except: continue
						if beaconId not in indigo.devices:
							self.indiLOG.log(30," beaconId not in devices:{} ; type: {}; car name:{}".format(beaconId, bNames[nn], carName))
							continue
						beaconDev= indigo.devices[beaconId]
						propsB = beaconDev.pluginProps
						bN[nn] = (beaconDev.name)
						bF[nn] = propsB["fastDown"]
					homeSince = int(time.time() - self.CARS["carId"][dd]["homeSince"])
					if homeSince > 9999999: homeSince = " "
					awaySince = int(time.time() - self.CARS["carId"][dd]["awaySince"])
					if awaySince > 9999999: awaySince= " "
					homeSince = "{}".format(homeSince).ljust(7)
					awaySince = "{}".format(awaySince).ljust(7)
					out =  carName +" "+homeSince+" - "+awaySince
					for n in range(len(bNames)):
						out += " " + bN[n].strip().ljust(30)

					self.myLog( theText = out, mType= "CARS")
					out =  "         ....FastDown beacons".ljust(30)+ " ".ljust(18)
					for n in range(len(bNames)):
						if bF[n] !=" ":
							out += " " + (bF[n]+"[sec]").strip().ljust(30)
						else:
							out += " " + (" ").ljust(30)

					self.myLog( theText = out, mType= "CARS")
				self.myLog( theText = "", mType= "pi configuration")
				"""
configuration         - ==========  defined beacons ==============
  08:31:46 pi configuration         -#  Beacon MAC        indigoName                 indigoId Status enabled               type txMin ignore  Pos X,Y,Z    fastDw sigDlt min on/off battery UUIDlastUpdate/level         LastUp[s] ExpTime updDelay lastStatusChange    created
  08:31:46 pi configuration         -1  24:DA:11:27:E5:D4 b-iHere_black-C          1940213429 up       True         Nonda_iHere   -55      0      0    999 -999/-999                                              45     120        0 2019-01-09 23:58:14 2020-09-14 08:06:47
  08:31:46 pi configuration         -6  00:EA:23:11:2B:E4 b-xy-Mazda -red-1-2        60052985 up       True                XY_1   -59      0      0    999 -999/-999random127/100 -09-05 09:20:18,l=0             45      90        0 2017-09-07 23:44:36 2020-09-14 08:07:49
				"""
			if True:
				self.myLog( theText = " ========================", mType= "")
				self.myLog( theText = " indigoName                 indigoId Status enabled               type txMin ignore  Pos X,Y,Z  fastDw sigDlt min-on/off batteryUUID lastUpdate/level         LastUp[s] ExpTime updDelay lastStatusChange    created ", mType= "defined beacons")
				for status in ["up", "down", "expired"]:
					for beaconDeviceType in self.knownBeaconTags["input"]:
						self.printBeaconInfoLine(status, beaconDeviceType)

				self.myLog( theText = "", mType= "pi configuration --")

			if True:
				self.myLog( theText = " ========================", mType= "update-thread status")
				self.myLog( theText = "lastCheck lastActive   lastData", mType= "update-thread status")
				if "state" in self.rpiQueues:
					for piU in self.RPI:
						if piU not in self.rpiQueues["state"]: continue
						self.myLog( theText = "{:10.1f} {:10.1f}   >{:} ...".format(time.time()-self.rpiQueues["lastCheck"][piU], time.time()-self.rpiQueues["lastActive"][piU], self.rpiQueues["lastData"][piU][0:120] ),  mType=  "{:3s} {:10s}".format( piU, self.rpiQueues["state"][piU]))
					self.myLog( theText = "", mType= "pi configuration")

		except Exception as e:
			self.exceptionHandler(40, e)



####-------------------------------------------------------------------------####
	def makLineForSensors(self, piU):
		try:
			line = ""
			sLine = ""
			eofl = 1
			lastName = ""
			for xx in self.RPI[piU]["sensorList"].strip(",").split(","):
				yy = xx.split("*")
				sName =  yy[0]
				sId   =  yy[1]

				if eofl != 1:
					line+= "\n                                                                                                                                                                                   "
				eofl = 1
				if sName != lastName: 
					if sLine !="": sLine+= " "
					sLine += sName+":"
					lastName = sName
				sLine +=  sId+","
				if len(sLine) > 70: 
					line += sLine.strip(",")
					eofl = 0
					sLine = ""
			if sLine != "": line += sLine	
			return line.strip(",").strip("\n")

		except Exception as e:
			self.exceptionHandler(40, e)
			self.indiLOG.log(40,"RPI#{} has problem:  disabled?".format(piU))
		return ""

####-------------------------------------------------------------------------####
	def printGroups(self):
		############## list groups with members
		try:
			out = "printGroups============ "
			out+= "\ngroupListUsedNames:{}".format(self.groupListUsedNames)
			for gr in self.groupStatusList:
				out+= "\n{} : {}".format(gr,self.groupStatusList[gr])

			out+= "\n"
			out+= "\n========== beacon groups    ===================================="
			out+= "\ndev                                                           groupMember in"

			groupMemberNames = {}
			for group in _GlobalConst_groupList+_GlobalConst_groupListDef:
				groupMemberNames[group] = ""

			for dev	in indigo.devices.iter(self.pluginId):
				if not dev.enabled:  continue
				if "groupMember" not in dev.states:  continue
				if dev.states["groupMember"] == "": continue
				out+= "\n{:57s}: {}".format(dev.name, dev.states["groupMember"])

				gps = dev.states["groupMember"].split("/")
				if len(gps) >0:
					for groupName in gps:
						for group in self.groupListUsedNames:
							if groupName == self.groupListUsedNames[group]:
								groupMemberNames[group] += "{},".format(dev.name)
				 
			out+= "\ngroup       groupNameUsedForVar groupMemberNames, IDs,... ------------------  "
			for group in _GlobalConst_groupList+_GlobalConst_groupListDef:
				groupNameUsedForVar = self.groupListUsedNames[group]
				if groupNameUsedForVar == "" and groupMemberNames[group] !="":
					groupNameUsedForVar = "please edit devs, set member"
				out+= "\n{}/{:20s}:{}" .format(group, groupNameUsedForVar, groupMemberNames[group])
				out+= "\n                    counts: "
				out+= "nHome: {};".format(self.groupStatusList[group]["nHome"])
				out+= " oneHome: {};".format(self.groupStatusList[group]["oneHome"])
				out+= " allHome: {};".format(self.groupStatusList[group]["allHome"])
				out+= "   nAway: {};".format(self.groupStatusList[group]["nAway"])
				out+= " oneAway: {};".format(self.groupStatusList[group]["oneAway"])
				out+= " allAway: {};".format(self.groupStatusList[group]["allAway"])
				out+= "\n            memberIDs:Name: "
				for member in self.groupStatusList[group]["members"]:
					out+= "{}:{};  ".format(member,self.groupStatusList[group]["members"][member])
				out+= "\n"
				out+= "\n---------------------------"
			out+= "\n ==========  Parameters END ================"
			out+= "\n"
			self.indiLOG.log(20,out)

		except Exception as e:
			self.exceptionHandler(40, e)

		return

####-------------------------------------------------------------------------####
	def resetTcpipSocketStatsCALLBACK(self, valuesDict=None, typeId=""):
		self.dataStats={"startTime":time.time(),"data":{}}


####-------------------------------------------------------------------------####
	def printTCPIPstats(self, all="yes"):

		############## tcpip stats
		if self.socServ is not None or True:
			if all == "yes":
					startDate= time.strftime(_defaultDateStampFormat,time.localtime(self.dataStats["startTime"]))
					self.myLog( theText = "", mType= "pi TCPIP socket")
					self.myLog( theText = "Stats for RPI-->INDIGO data transfers. Tracking started {}. Report TX errors if time between errors is <{:.0f} Min".format(startDate, self.maxSocksErrorTime/60), mType=	"pi TCPIP socket")
			self.myLog( theText = "IP              name          type      first               last                    #MSGs       #bytes bytes/MSG  maxBytes  bytes/min   MSGs/min", mType= "pi TCPIP socket")

			### self.dataStats["data"][IPN][name][type] = {"firstTime":time.time(),"lastTime":0,"count":0,"bytes":0}

			secMeasured	  = max(1., (time.time() - self.dataStats["startTime"]))
			minMeasured	  = secMeasured/60.
			totBytes = 0.0
			totMsg	 = 0.0
			maxBytes = 0
			for IPN in sorted(self.dataStats["data"].keys()):
				if all == "yes" or all==IPN:
					for name  in sorted(self.dataStats["data"][IPN].keys()):
						for xType in sorted(self.dataStats["data"][IPN][name].keys()):
							if "maxBytes"	not in self.dataStats["data"][IPN][name][xType]:
								self.resetDataStats()
								return
							FT		= self.dataStats["data"][IPN][name][xType]["firstTime"]
							LT		= self.dataStats["data"][IPN][name][xType]["lastTime"]

							dtFT	= datetime.datetime.fromtimestamp(FT).strftime(_defaultDateStampFormat)
							dtLT	= datetime.datetime.fromtimestamp(LT).strftime(_defaultDateStampFormat)
							bytesN	= self.dataStats["data"][IPN][name][xType]["bytes"]
							bytesT	= "{}".format(bytesN).rjust(12)
							countN	= self.dataStats["data"][IPN][name][xType]["count"]
							count	= "{}".format(countN).rjust(9)
							maxBytN = self.dataStats["data"][IPN][name][xType]["maxBytes"]
							maxByt	= "{}".format(maxBytN).rjust(9)
							totMsg	  += countN
							totBytes  += bytesN
							try:	bytesPerMsg = "{}".format(int(self.dataStats["data"][IPN][name][xType]["bytes"]/float(self.dataStats["data"][IPN][name][xType]["count"]))).rjust(9)
							except: bytesPerMsg = " ".rjust(9)

							try:
									bytesPerMin = self.dataStats["data"][IPN][name][xType]["bytes"]/minMeasured
									bytesPerMin	  = ("{:9.1f}".format(bytesPerMin)).rjust(9)
							except: bytesPerMin = " ".rjust(9)
							try:
									msgsPerMin	 = self.dataStats["data"][IPN][name][xType]["count"]/minMeasured
									msgsPerMin	 = ("{:9.1f}".format(msgsPerMin)).rjust(9)
							except: msgsPerMin	 = " ".rjust(9)

							maxBytes   = max(maxBytN,maxBytes)

							self.myLog( theText = "{} {} {} {} {} {} {} {} {}  {}  {}".format(IPN.ljust(15), name.ljust(12), xType.ljust(10), dtFT, dtLT, count, bytesT, bytesPerMsg, maxByt, bytesPerMin, msgsPerMin),mType=" ")
			if all == "yes" and totMsg >0:
				bytesPerMsg	  = "{}".format(int(totBytes/totMsg)).rjust(9)
				bytesPerMin	  = ("%9.1f"% (totBytes/minMeasured)  ).rjust(9)
				msgsPerMin	  = ("%9.2f"% (totMsg/minMeasured)	   ).rjust(9)
				maxBytes	  =	 "{}".format(maxBytes).rjust(9)
				self.myLog( theText = "total                                                                          {:10d}{:13d} {} {}  {}  {}".format(int(totMsg), int(totBytes), bytesPerMsg, maxBytes, bytesPerMin, msgsPerMin ),mType=" ")
				self.myLog( theText = " ===  Stats for RPI --> INDIGO data transfers ==  END total time measured: {:.0f} {} ; min measured: {:.0f}".format( int(time.strftime("%d", time.gmtime(secMeasured)))-1, time.strftime("%H:%M:%S", time.gmtime(secMeasured)), minMeasured ), mType=	 "pi TCPIP socket")
		return

####-------------------------------------------------------------------------####
	def printUpdateStats(self,):
		if len(self.dataStats["updates"]) ==0: return
		nSecs = max(1,(time.time()-	 self.dataStats["updates"]["startTime"]))
		nMin  = nSecs/60.
		startDate= time.strftime(_defaultDateStampFormat,time.localtime(self.dataStats["updates"]["startTime"]))
		self.myLog( theText = "",mType=" " )
		self.myLog( theText = "===    measuring started at: {}".format(startDate), mType="indigo update stats " )
		self.myLog( theText = "total device updates: {:10d};   updates/sec: {:10.2f};   updates/minute: {:10.2f}".format(self.dataStats["updates"]["devs"], self.dataStats["updates"]["devs"] /nSecs, self.dataStats["updates"]["devs"]  /nMin), mType= "indigo update stats")
		self.myLog( theText =    " #states   #updates   #updates/min  to indigo and logging" ,mType= "indigo update stats")
		for ii in range(1,10): #  1234567   891234567891 123456789012
			self.myLog( theText ="     {:2d}  {:10d}     {:6.1f}".format(ii, self.dataStats["updates"]["nstates"][ii], self.dataStats["updates"]["nstates"][ii]/nMin),mType= "indigo update stats")
		ii = 10
		self.myLog( theText     ="   >={:2d}  {:10d}     {:6.1f}".format(ii, self.dataStats["updates"]["nstates"][ii], self.dataStats["updates"]["nstates"][ii]/nMin),mType= "indigo update stats")

		self.myLog( theText = "=== total time measured: Days:{}  HH:MM:SS {}".format( str(int(time.strftime("%d", time.gmtime(nSecs)))-1), str(time.strftime("%H:%M:%S", time.gmtime(nSecs))) ), mType= "indigo update stats" )
		return


####-------------------------------------------------------------------------####
	def printBeaconInfoLine(self, status, xType):

		try:
			cc = 0
			for beacon in copy.deepcopy(self.beacons):
				if self.beacons[beacon]["typeOfBeacon"] != xType: continue
				if self.beacons[beacon]["status"] 		!= status: continue
				lastUpdateBatteryLevel = ""
				batteryLevelUUID = ""
				name = " "
				lastStatusChange = " "
				try:
					dev = indigo.devices[self.beacons[beacon]["indigoId"]]
					name = dev.name
					props = dev.pluginProps
					if "minSignalOn" not in props: continue # old device
					lastStatusChange = dev.states["lastStatusChange"]
					if "batteryLevelUUID" in props and props["batteryLevelUUID"].find("batteryLevel") >-1:
						batteryLevelUUID = props["batteryLevelUUID"]# .replace("-batteryLevel-int-bits=","").replace("2A19-","").replace("-norm=", "/").replace("randomON", "random")
						if "lastUpdateBatteryLevel" in dev.states:
							lastUpdateBatteryLevel = dev.states["lastUpdateBatteryLevel"][4:]
							if len(lastUpdateBatteryLevel) < 10: lastUpdateBatteryLevel = "01-01 00:00:00"
							lastUpdateBatteryLevel += ",l={}".format(dev.states["batteryLevel"])
							lastUpdateBatteryLevel = lastUpdateBatteryLevel
				except Exception as e:
					if "{}".format(e).find("timeout waiting") > -1:
						self.exceptionHandler(40, e)
						self.indiLOG.log(40,"communication to indigo is interrupted")
					continue
				if len(batteryLevelUUID) != 14: batteryLevelUUID = batteryLevelUUID.ljust(14)
				if len(lastUpdateBatteryLevel) !=21: lastUpdateBatteryLevel = lastUpdateBatteryLevel.ljust(21)

				cc += 1
				if len(name) > 22: name = name[:21] + ".."
				line = name.ljust(24) + " " +  "{}".format(self.beacons[beacon]["indigoId"]).rjust(10) + " "+\
					   self.beacons[beacon]["status"].ljust(8) +\
					   "{}".format(dev.enabled).rjust(5) + \
					   self.beacons[beacon]["typeOfBeacon"].rjust(20)+\
					   "{}".format(self.beacons[beacon]["beaconTxPower"]).rjust(6) + " " + \
					   "{}".format(self.beacons[beacon]["ignore"]).rjust(6) + " " + \
					   ("{}".format(dev.states["PosX"]).split(".")[0] + ",{}".format(dev.states["PosY"]).split(".")[0] + ",{}".format(dev.states["PosZ"]).split(".")[0]).rjust(10)+\
					   "{}".format(props["fastDown"]).rjust(6) + " " + \
					   "{}".format(props["signalDelta"]).rjust(6) + " " + \
					   "{}".format(props["minSignalOn"]).rjust(4) +"/{}".format(props["minSignalOff"]).rjust(4) + \
					   batteryLevelUUID +\
					   lastUpdateBatteryLevel +\
					   "{}".format(min(999999999,int(time.time() - self.beacons[beacon]["lastUp"])      ) ).rjust(13) + " " + \
					   "{}".format(min(999999,   int(self.beacons[beacon]["expirationTime"])            ) ).rjust(7)  + " " + \
					   "{}".format(min(9999999,  int(self.beacons[beacon]["updateSignalValuesSeconds"]) ) ).rjust(8)  + " " + \
					   "{}".format(self.beacons[beacon]["created"]).ljust(19) +" "+\
					   lastStatusChange.ljust(19)
				self.myLog( theText = line, mType=  f"pi {cc:3d} {beacon:}")

			if status == "ignored":
				for beacon in copy.deepcopy(self.beacons):
					if self.beacons[beacon]["typeOfBeacon"] != type: continue
					if self.beacons[beacon]["status"] != status: continue
					if self.beacons[beacon]["ignore"] == 1:
						name = " "
						cc += 1
						line = name.ljust(24) + " ".ljust(11) + " "+ \
							   self.beacons[beacon]["status"].ljust(8)  + \
							   "{}".format(dev.enabled).rjust(5) + \
							   self.beacons[beacon]["typeOfBeacon"].rjust(20)  + \
							   " ".rjust(6) + " " + \
							   " ".rjust(6) + " " + \
							   " ".rjust(6) + " " + \
							   " ".rjust(6) + " " + \
							   "{}".format("-").rjust(23) +\
							   "{}".format(min(999999999,int(time.time() - self.beacons[beacon]["lastUp"]))).rjust(13) + " " + \
							   "{}".format(min(999999,int(self.beacons[beacon]["expirationTime"]))).rjust(7) + " " + \
							   "{}".format(min(9999999,int(self.beacons[beacon]["updateSignalValuesSeconds"]))).rjust(8) + " " + \
							   "{}".format(self.beacons[beacon]["created"]).ljust(19)
						self.myLog( theText = line, mType=	 f"pi {cc:3d} {beacon:}")
				for beacon in copy.deepcopy(self.beacons):
					if self.beacons[beacon]["typeOfBeacon"] != type: continue
					if self.beacons[beacon]["status"] != status:	  continue
					if self.beacons[beacon]["ignore"] == 2:
						name = " "
						cc += 1
						line = name.ljust(24) + " ".ljust(11) + " "+ \
							   self.beacons[beacon]["status"].ljust(8) + \
							   "     "  + \
							   self.beacons[beacon]["typeOfBeacon"].rjust(10) + " " + \
							   "{}".format(self.beacons[beacon]["beaconTxPower"]).rjust(6)  + \
							   " ".rjust(6) + " " + \
							   " ".rjust(6) + " " + \
							   " ".rjust(6) + " " + \
							   "{}".format("-").rjust(23) +\
							   "{}".format(min(999999999,int(time.time() - self.beacons[beacon]["lastUp"]))).rjust(12) + " " + \
							   "{}".format(min(999999,int(self.beacons[beacon]["expirationTime"]))).rjust(7) + " " + \
							   "{}".format(min(9999999,int(self.beacons[beacon]["updateSignalValuesSeconds"]))).rjust(8) + " " + \
							   "{}".format(self.beacons[beacon]["created"]).ljust(19)
						self.myLog( theText = line, mType=  f"pi {cc:3d} {beacon:}")


		except Exception as e:
			if	"{}".format(e).find("UnexpectedNullErrorxxxx") >-1: return newStates
			self.exceptionHandler(40, e)



####-------------------------------------------------------------------------####
	def updateRejectLists(self):
		if "UpdateRPI" in self.debugLevel: deb = "1"
		else: deb =""
		cmd = self.pythonPath + " '" + self.pathToPlugin + "updateRejects.py' "+ deb +" & "
		#self.indiLOG.log(30," cmd:{}".format(cmd))
		if self.doRejects:	subprocess.call(cmd, shell=True)
		else:				subprocess.call("rm '"+ self.indigoPreferencesPluginDir + "rejected/rejects*'  > /dev/null 2>&1 " , shell=True)

		return 



####-----------------
	########################################
	# General Action callback
	######################
	def actionControlUniversal(self, action, dev):
		###### BEEP ######
		if action.deviceAction == indigo.kUniversalAction.Beep:
			# Beep the hardware module (dev) here:
			# ** IMPLEMENT ME **
			indigo.server.log("sent \"{}\" beep request not implemented".format(dev.name))

		###### STATUS REQUEST ######
		elif action.deviceAction == indigo.kUniversalAction.RequestStatus:
			if dev.deviceTypeId == "OUTPUTswitchbotRelay":
				props = dev.pluginProps
				piU = props["piServerNumber"]
				fileContents = {"mac":props["mac"], "cmd":"statusRequest", "statusRequest":True, "outputDev":  dev.id,"mode":"interactive"}
				toSend = [{"device": "OUTPUTswitchbotRelay", "command":"file", "fileName":"/home/pi/pibeacon/temp/switchbot.cmd", "fileContents":fileContents}]
				self.sendtoRPI(self.RPI[piU]["ipNumberPi"], piU, toSend, calledFrom="switchBotRelaySet")
				if self.decideMyLog("UpdateRPI"): self.indiLOG.log(10,"action dimmer relay requested: for {} on pi:{}; text to send:{}".format(dev.name, piU, toSend))
				return 

			indigo.server.log("sent \"{}\" status request not implemented".format(dev.name))

	########################################
	# Sensor Action callback
	######################
	def actionControlSensor(self, action, dev):
		if dev.address in self.beacons:
			self.beacons[dev.address]["lastUp"] = time.time()

		elif  dev.deviceTypeId =="rPI":
			piU = dev.pluginProps.get("RPINumber","")
			self.RPI[piU]["lastMessage"]=time.time()

		elif dev.deviceTypeId =="BLEconnect":
			self.addToStatesUpdateDict(dev.id, "lastUp",datetime.datetime.now().strftime(_defaultDateStampFormat))

		###### TURN ON ######
		if action.sensorAction == indigo.kSensorAction.TurnOn:
			self.addToStatesUpdateDict(dev.id, "status", "up")

		###### TURN OFF ######
		elif action.sensorAction == indigo.kSensorAction.TurnOff:
			self.addToStatesUpdateDict(dev.id, "status", "down")

		###### TOGGLE ######
		elif action.sensorAction == indigo.kSensorAction.Toggle:
			if dev.onState:
				self.addToStatesUpdateDict(dev.id, "status", "down")
				dev.updateStateImageOnServer(indigo.kStateImageSel.PowerOff)
			else:
				self.addToStatesUpdateDict(dev.id, "status", "up")

		self.executeUpdateStatesDict()

##############################################################################################

####-------------------------------------------------------------------------####


	def addToStatesUpdateDict(self,devId, key, value, newStates="",decimalPlaces="",uiValue="", image="", force=False):
		devId= "{}".format(devId)
		try:
			try:
				#if "1076556263" ==devId: self.indiLOG.log(10,"addToStatesUpdateDict(1) {}".format(devId, key, value))

				for ii in range(10):
					if self.executeUpdateStatesDictActive == "":
						break
					self.sleep(0.05)
				self.executeUpdateStatesDictActive = devId+"-add"

				if devId not in self.updateStatesDict:
					self.updateStatesDict[devId] = {}

				if key in self.updateStatesDict[devId]:
					if value != self.updateStatesDict[devId][key]["value"]:
						self.updateStatesDict[devId][key] = {}
						if newStates != "":
							newStates[key] = {}

				self.updateStatesDict[devId][key] = {"value":value, "decimalPlaces":decimalPlaces, "force":force, "uiValue":uiValue, "image":image}
				if isinstance(value, float) and  math.isnan(value): self.indiLOG.log(20,"updateStatesDict[devId]:{}, key:{}, value:{} is NaN, please check rpi program, contact KW".format(self.updateStatesDict[devId] , key,  value))

				if newStates != "": newStates[key] = value

			except Exception as e:
				if "{}".format(e).find("UnexpectedNullErrorxxxx") == -1:
					if "{}".format(e).find(str(devId)) == -1:
						self.indiLOG.log(40,"Line {} has error={}".format(sys.exc_info()[2].tb_lineno, e)   )
						self.indiLOG.log(40,"addToStatesUpdateDict: this happens when 2 update processes overlap. should not be a probelm if it happens not too frequently")
						self.indiLOG.log(40,"devId:{};  key:{}; value:{}; newStates:{};".format(devId, key, value, newStates))



		except Exception as e:
			if	"{}".format(e).find("UnexpectedNullErrorxxxx") >-1: return newStates
			self.exceptionHandler(40, e)
		self.executeUpdateStatesDictActive = ""
		#if "1076556263" == devId: self.indiLOG.log(10,"addToStatesUpdateDict(2) {}, updateStatesDict".format(devId,self.updateStatesDict[devId]))
		return newStates

####-------------------------------------------------------------------------####
	def executeUpdateStatesDict(self,onlyDevID="0", calledFrom=""):
		try:
			if len(self.updateStatesDict) == 0: return
			onlyDevID = "{}".format(onlyDevID)
			#if "1076556263" in self.updateStatesDict: self.indiLOG.log(20,"executeUpdateStatesList calledfrom: {}; onlyDevID: {}; updateStatesList: {}".format(calledFrom, onlyDevID, self.updateStatesDict))

			for ii in range(10):
				if	self.executeUpdateStatesDictActive == "":
					break
				self.sleep(0.05)

			self.executeUpdateStatesDictActive = onlyDevID+"-exe"


			local = {}
			#
			if onlyDevID == "0":
				for ii in range(5):
					try:
						local = copy.deepcopy(self.updateStatesDict)
						break
					except Exception as e:
						self.sleep(0.05)
				self.updateStatesDict={}

			elif onlyDevID in self.updateStatesDict:
				for ii in range(5):
					try:
						local = {onlyDevID: copy.deepcopy(self.updateStatesDict[onlyDevID])}
						break
					except Exception as e:
						self.sleep(0.05)

				try:
					del self.updateStatesDict[onlyDevID]
				except Exception as e:
					pass
			else:
				self.executeUpdateStatesDictActive = ""
				return
			self.executeUpdateStatesDictActive = ""


			changedOnly = {}
			trigStatus	   = ""
			trigRPIchanged = ""
			devnamechangedStat= ""
			image = ""
			dateString = datetime.datetime.now().strftime(_defaultDateStampFormat)

			for devId in local:
				if onlyDevID !="0" and onlyDevID != devId: continue
				if len(local) > 0:
					dev =indigo.devices[int(devId)]
					lastSensorChangePresent = False
					nKeys = 0
					#if dev.id ==739817084: self.indiLOG.log(20,	"image:{}, local:{} \nchangedOnly:{}".format(image, local[devId], changedOnly ))
					for key in local[devId]:
						if local[devId][key].get("image","") != "" : image = local[devId][key]["image"]
						value = local[devId][key]["value"]
						if key not in dev.states and key != "lastSensorChange":
							self.indiLOG.log(10,"executeUpdateStatesDict: key: {}  not in states for dev:{}".format(key, dev.name) )
							self.rePopulateStates = "key:{} not defined in {}".format(key, dev.name) # try to re-do state list
						elif key in dev.states:
							upd = False
							if local[devId][key]["force"]:
										upd = True
							else:
								if local[devId][key]["decimalPlaces"] != "": # decimal places present?
									try:
										if round(value,local[devId][key]["decimalPlaces"]) !=	 round(dev.states[key],local[devId][key]["decimalPlaces"]):
											upd=True
									except:
											upd=True
								else:
									if "{}".format(value) != "{}".format(dev.states[key]): 
											upd = True
							if upd:
								nKeys += 1
								if devId not in changedOnly: changedOnly[devId]={}
								changedOnly[devId][key] = {"value":local[devId][key]["value"], "decimalPlaces":local[devId][key]["decimalPlaces"], "uiValue":local[devId][key]["uiValue"]}
								if not lastSensorChangePresent:
									if "lastSensorChange" in dev.states and key not in ["lastUpdateFromRPI", "lastMessageFromRpi"] and  "lastSensorChange" not in changedOnly[devId]:
										nKeys +=1
										changedOnly[devId]["lastSensorChange"] = {"value":dateString, "decimalPlaces":"", "uiValue":""}
										lastSensorChangePresent = True


					#if dev.id ==739817084: self.indiLOG.log(20,	"image:{}, local:{} \nchangedOnly:{}".format(image, local[devId], changedOnly ))
					
					if "created" in dev.states and dev.states["created"] == "": 
						createdSet = False
					else:
						createdSet = True
					#if "created" not in dev.states: 
					#	self.indiLOG.log(20,	"dev {} does not have created state".format(dev.name))


					if devId in changedOnly and len(changedOnly[devId]) >0:
						chList=[]
						if "created" in changedOnly[devId]:
							createdSet = True
						for key in changedOnly[devId]:
							if key == "lastSensorChange": lastSensorChangePresent = True

							if key == "status":
								value = changedOnly[devId][key]["value"]
								if "lastStatusChange" in dev.states and "lastStatusChange" not in changedOnly[devId]:
									try:
										st	= "{}".format(value).lower().split(" ")[0] # remove strings after up down ie dates 
										if st in ["up", "down", "expired", "on", "off", "1", "0"]:
											if dateString != dev.states["lastStatusChange"]:
												chList.append({"key": "lastStatusChange", "value":dateString})
									except: pass

								#if dev.id == 833765526: indigo.server.log("{}  key:{}, value:{},  changed1 {}".format(dev.name, key, value, chList))

								if dev.deviceTypeId == "beacon" or dev.deviceTypeId.find("rPI") > -1 or dev.deviceTypeId == "BLEconnect":

									chList.append({"key":"displayStatus", "value":self.padDisplay(value)+dateString[5:] })

									if	 value == "up":
										chList.append({"key":"onOffState", "value":True, "uiValue":self.padDisplay(value)+dateString[5:] })
										chList.append({"key":"status", "value":"up", "uiValue":self.padDisplay(value)+dateString[5:]  })
										dev.updateStateImageOnServer(indigo.kStateImageSel.SensorOn)

									elif value == "down":
										chList.append({"key":"onOffState", "value":False, "uiValue":self.padDisplay(value)+dateString[5:] })
										chList.append({"key":"status", "value":"down", "uiValue":self.padDisplay(value)+dateString[5:] })
										dev.updateStateImageOnServer(indigo.kStateImageSel.SensorOff)

									else:
										chList.append({"key":"onOffState", "value":False, "uiValue":self.padDisplay(value)+dateString[5:] })
										chList.append({"key":"status", "value":"expired", "uiValue":self.padDisplay(value)+dateString[5:] })
										dev.updateStateImageOnServer(indigo.kStateImageSel.SensorTripped)

									if dev.deviceTypeId == "beacon":
										trigStatus			 = dev.name
										devnamechangedStat	 =  "{}     {}    old={}     new={}".format(dev.name, key, dev.states[key], changedOnly[devId][key]["value"])

										if dev.address in self.CARS["beacon"] and changedOnly[devId][key]["value"] in ["up","down"]:
											self.delayedActions["data"].put({"actionTime":time.time()+0.2 , "devId":dev.id, "updateItems":["updateCars"]})

								else: # not beacon ... 
									if changedOnly[devId][key]["uiValue"] != "":
										if changedOnly[devId][key]["decimalPlaces"] != "" and key in dev.states:
											chList.append({"key":key, "value":changedOnly[devId][key]["value"], "decimalPlaces":changedOnly[devId][key]["decimalPlaces"], "uiValue":changedOnly[devId][key]["uiValue"]})
										else:
											chList.append({"key":key,"value":changedOnly[devId][key]["value"],"uiValue":changedOnly[devId][key]["uiValue"]})
											#indigo.server.log(dev.name+"  into changed {}".format(chList))
									else:
										if changedOnly[devId][key]["decimalPlaces"] != "" and key in dev.states:
											chList.append({"key":key,"value":changedOnly[devId][key]["value"], "decimalPlaces":changedOnly[devId][key]["decimalPlaces"]})
										else:
											chList.append({"key":key,"value":changedOnly[devId][key]["value"]})

									if not lastSensorChangePresent and "lastSensorChange"  in dev.states :
										if  (key != "lastSensorChange" and key not in ["lastUpdateFromRPI","lastMessageFromRpi"] ) or ( key == "lastSensorChange" and nKeys >0):
											chList.append({"key":"lastSensorChange", "value":dateString})

							else: # not status 

								if changedOnly[devId][key]["uiValue"] != "":
									if changedOnly[devId][key]["decimalPlaces"] != "" and key in dev.states:
										chList.append({"key":key, "value":changedOnly[devId][key]["value"], "decimalPlaces":changedOnly[devId][key]["decimalPlaces"], "uiValue":changedOnly[devId][key]["uiValue"]})
									else:
										chList.append({"key":key,"value":changedOnly[devId][key]["value"],"uiValue":changedOnly[devId][key]["uiValue"]})
										#indigo.server.log(dev.name+"  into changed {}".format(chList))
								else:
									if changedOnly[devId][key]["decimalPlaces"] != "" and key in dev.states:
										chList.append({"key":key,"value":changedOnly[devId][key]["value"], "decimalPlaces":changedOnly[devId][key]["decimalPlaces"]})
									else:
										chList.append({"key":key,"value":changedOnly[devId][key]["value"]})

								if not lastSensorChangePresent and "lastSensorChange"  in dev.states :
									if  (key != "lastSensorChange" and key not in ["lastUpdateFromRPI","lastMessageFromRpi"] ) or ( key == "lastSensorChange" and nKeys >0):
										chList.append({"key":"lastSensorChange", "value":dateString})
										lastSensorChangePresent = True
				


								if key == "closestRPI":
									trigRPIchanged		 = dev.name
									devnamechangedStat	 =  "{}     {}    old={}     new={}".format(dev.name, key, dev.states[key], changedOnly[devId][key]["value"])


						##if dev.name =="b-radius_3": self.indiLOG.log(5,	"chList {}".format(chList))

						#if dev.id ==1076556263: self.indiLOG.log(10,	"chList {}".format(chList))
						if not createdSet:
							chList.append({"key":"created","value":dateString})
																		 
						self.execUpdateStatesList(dev,chList)
						if image !="":
							#self.indiLOG.log(20,"{} set image>{}<".format(dev.name, image))
							if   image == "SensorOn":				dev.updateStateImageOnServer(indigo.kStateImageSel.SensorOn)
							elif image == "SensorOff": 				dev.updateStateImageOnServer(indigo.kStateImageSel.SensorOff)
							elif image == "SensorTripped": 			dev.updateStateImageOnServer(indigo.kStateImageSel.SensorTripped)
							elif image == "TemperatureSensorOn": 	dev.updateStateImageOnServer(indigo.kStateImageSel.TemperatureSensorOn)
							elif image == "TemperatureSensor": 		dev.updateStateImageOnServer(indigo.kStateImageSel.TemperatureSensor)
							elif image == "HumiditySensor": 		dev.updateStateImageOnServer(indigo.kStateImageSel.HumiditySensor)
							elif image == "HumiditySensorOn": 		dev.updateStateImageOnServer(indigo.kStateImageSel.HumiditySensorOn)
							elif image == "MotionSensor": 			dev.updateStateImageOnServer(indigo.kStateImageSel.MotionSensor)
							elif image == "LightSensor": 			dev.updateStateImageOnServer(indigo.kStateImageSel.LightSensor)
							elif image == "LightSensorOn": 			dev.updateStateImageOnServer(indigo.kStateImageSel.LightSensorOn)
							elif image == "PowerOn": 				dev.updateStateImageOnServer(indigo.kStateImageSel.PowerOn)
							elif image == "PowerOff": 				dev.updateStateImageOnServer(indigo.kStateImageSel.PowerOff)
							elif image == "DimmerOn": 				dev.updateStateImageOnServer(indigo.kStateImageSel.DimmerOn)
							elif image == "DimmerOff": 				dev.updateStateImageOnServer(indigo.kStateImageSel.DimmerOff)
							elif image == "EnergyMeterOn": 			dev.updateStateImageOnServer(indigo.kStateImageSel.EnergyMeterOn)
							elif image == "EnergyMeterOff": 		dev.updateStateImageOnServer(indigo.kStateImageSel.EnergyMeterOff)
							elif image == "PowerOff": 				dev.updateStateImageOnServer(indigo.kStateImageSel.PowerOff)
							elif image == "Error": 					dev.updateStateImageOnServer(indigo.kStateImageSel.Error)

				if trigStatus != "":
					try:
						indigo.variable.updateValue(self.ibeaconNameDefault+"With_Status_Change",trigStatus)
					except Exception as e:
							self.indiLOG.log(40,"Line {} has error={}".format(sys.exc_info()[2].tb_lineno, e)   + " trying again")
							time.sleep(0.5)
							indigo.variable.updateValue(self.ibeaconNameDefault+"With_Status_Change",trigStatus)
							self.indiLOG.log(40,"worked 2. time")
					self.triggerEvent("someStatusHasChanged")

				if trigRPIchanged !="":
					try:
						indigo.variable.updateValue(self.ibeaconNameDefault+"With_ClosestRPI_Change",trigRPIchanged)
					except Exception as e:
							self.indiLOG.log(40,"RPI   changed: {}".format(devnamechangedRPI))
							self.indiLOG.log(40,"Line {} has error={}".format(sys.exc_info()[2].tb_lineno, e)   + " trying again")
							time.sleep(0.5)
							indigo.variable.updateValue(self.ibeaconNameDefault+"With_ClosestRPI_Change",trigRPIchanged)
							self.indiLOG.log(40,"worked 2. time")
					self.triggerEvent("someClosestrPiHasChanged")

		except Exception as e:
			if	"{}".format(e).find("UnexpectedNullErrorxxxx") ==-1:
				self.exceptionHandler(40, e)
		self.executeUpdateStatesDictActive = ""
		return

####-------------------------------------------------------------------------####
	def execUpdateStatesList(self, dev, chList):
		try:
			if len(chList) == 0: return
			self.dataStats["updates"]["devs"]	+=1
			self.dataStats["updates"]["states"] += len(chList)
			self.dataStats["updates"]["nstates"][min(len(chList),10)] += 1

			### debug 
			if False and len(chList) == 2:
				for xxx in chList:
					if "lastSensorChange" == xxx["key"]:
						self.indiLOG.log(20,"execUpdateStatesList, dev:{:40s};  change list:{:} ".format(dev.name, chList))
						break


			if self.indigoVersion >6:
				try:
					#if dev.id == 833765526: indigo.server.log("-----------old status:{}; executed chList {}".format(dev.states["status"], chList))
					dev.updateStatesOnServer(chList)
				except:
					self.rePopulateStates = "error update states on server for dev:{}, changelist:{}".format(dev.name, chList) # try to re-do state list
			else:
				for uu in chList:
					try:
						dev.updateStateOnServer(uu["key"],uu["value"])
					except:
						self.rePopulateStates = "error update state:{} on server, dev:{}".format(uu["key"], dev.name)  # try to re-do state list


		except Exception as e:
			self.exceptionHandler(40, e)
			self.indiLOG.log(40,"chList: {}".format(chList))

###############################################################################################



####-------------------------------------------------------------------------####
	def convertVariableOrDeviceStateToText(self,textIn,enableEval=False):
		try:
			if not isinstance(textIn, str): return textIn
			oneFound=False
			for ii in range(50):	 # safety, no forever loop
				if textIn.find("%%v:") ==-1: break
				oneFound=True
				textIn,rCode = self.convertVariableToText0(textIn)
				if not rCode: break
			for ii in range(50):	 # safety, no forever loop
				if textIn.find("%%d:") ==-1: break
				oneFound=True
				textIn,rCode = self.convertDeviceStateToText0(textIn)
				if not rCode: break
			for ii in range(50):	 # safety, no forever loop
				if textIn.find("%%FtoC:") ==-1: break
				oneFound=True
				textIn,rCode = self.convertFtoC(textIn)
				if not rCode: break
			for ii in range(50):	 # safety, no forever loop
				if textIn.find("%%CtoF:") ==-1: break
				oneFound=True
				textIn,rCode = self.convertCtoF(textIn)
				if not rCode: break
			for ii in range(50):	 # safety, no forever loop
				if textIn.find("%%eval:") ==-1: break
				oneFound=True
				textIn,rCode = self.evalString(textIn)
				if not rCode: break
			try:
				if enableEval and oneFound and (textIn.find("+")>-1 or	 textIn.find("-")>-1 or textIn.find("/")>-1 or textIn.find("*")>-1):
					textIn = "{}".format(eval(textIn))
			except: pass
		except Exception as e:
			self.exceptionHandler(40, e)
		return textIn
####-------------------------------------------------------------------------####
	def convertFtoC(self,textIn):
		#  converts eg:
		#"abc%%FtoC:1234%%xyz"	  to abcxyz
		try:
			try:
				start= textIn.find("%%FtoC:")
			except:
				return textIn, False

			if start==-1:
				return textIn, False
			textOut= textIn[start+7:]
			end = textOut.find("%%")
			if end ==-1:
				return textIn, False
			var = textOut[:end]
			try:
				vText= "{:.1f}".format((float(var)-32.)*5./9.)
			except Exception as e:
				self.exceptionHandler(40, e)
				return textIn, False

			try:
				if end+2 >= len(textOut)-1:
					textOut= textIn[:start]+vText
					return textOut, True
				textOut= textIn[:start]+vText+textOut[end+2:]
				return textOut, True
			except:
				return textIn, False
		except Exception as e:
			self.exceptionHandler(40, e)
		return textIn, False
####-------------------------------------------------------------------------####
	def convertCtoF(self,textIn):
		#  converts eg:
		#"abc%%FtoC:1234%%xyz"	  to abcxyz
		try:
			try:
				start= textIn.find("%%CtoF:")
			except:
				return textIn, False

			if start==-1:
				return textIn, False
			textOut= textIn[start+7:]
			end = textOut.find("%%")
			if end ==-1:
				return textIn, False
			var = textOut[:end]
			try:
				vText= "{:.1f}".format((float(var)*9./5.) + 32)
			except Exception as e:
				self.exceptionHandler(40, e)
				return textIn, False

			try:
				if end+2 >= len(textOut)-1:
					textOut= textIn[:start]+vText
					return textOut, True
				textOut= textIn[:start]+vText+textOut[end+2:]
				return textOut, True
			except:
				return textIn, False
		except Exception as e:
			self.exceptionHandler(40, e)
		return textIn, False

####-------------------------------------------------------------------------####
	def evalString(self,textIn):
		#  converts eg:
		#"abc%%FtoC:1234%%xyz"	  to abcxyz
		try:
			try:
				start= textIn.find("%%eval:")
			except:
				return textIn, False

			if start==-1:
				return textIn, False
			textOut= textIn[start+7:]
			end = textOut.find("%%")
			if end ==-1:
				return textIn, False
			var = textOut[:end]
			try:
				vText= eval(var)
			except Exception as e:
				self.exceptionHandler(40, e)
				self.indiLOG.log(10,var)
				self.indiLOG.log(10,textOut[:50])
				return textIn, False

			try:
				if end+2 >= len(textOut)-1:
					textOut= textIn[:start]+vText
					self.indiLOG.log(10,textOut)
					return textOut, True
				textOut= textIn[:start]+vText+textOut[end+2:]
				self.indiLOG.log(10,textOut)
				return textOut, True
			except Exception as e:
				self.exceptionHandler(40, e)
				return textIn, False
		except Exception as e:
			self.exceptionHandler(40, e)
		return textIn, False


####-------------------------------------------------------------------------####
	def convertVariableToText0(self,textIn):
		#  converts eg:
		#"abc%%v:VariName%%xyz"	  to abcCONTENTSOFVARIABLExyz
		#"abc%%V:VariNumber%%xyz to abcCONTENTSOFVARIABLExyz
		try:
			try:
				start= textIn.find("%%v:")
			except:
				return textIn, False

			if start==-1:
				return textIn, False
			textOut= textIn[start+4:]
			end = textOut.find("%%")
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
		except Exception as e:
			self.exceptionHandler(40, e)
		return textIn, False



####-------------------------------------------------------------------------####
	def convertDeviceStateToText0(self,textIn):
		#  converts eg:
		#"abc%%d:devName:stateName%%xyz"   to abcdevicestatexyz
		#"abc%%V:devId:stateName%%xyz to abcdevicestatexyz
		try:
			try:
				start= textIn.find("%%d:")
			except:
				return textIn, False
			if start==-1:
				return textIn, False
			textOut= textIn[start+4:]

			secondCol = textOut.find(":")
			if secondCol ==-1:
				return textIn, False
			dev		= textOut[:secondCol]
			textOut = textOut[secondCol+1:]
			percent = textOut.find("%%")

			if percent ==-1: return textIn, False
			state	= textOut[:percent]
			textOut = textOut[percent+2:]
			try:
				vText= "{}".format(indigo.devices[int(dev)].states[state])
			except:
				try:
					vText= "{}".format(indigo.devices[dev].states[state])
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
		except Exception as e:
			self.exceptionHandler(40, e)
		return textIn, False



####-----------------  calc # of blanks to be added to state column to make things look better aligned. ---------
	def padDisplay(self,status):
		if	 status == "up":		return status.ljust(11)
		elif status == "expired":	return status.ljust(8)
		elif status == "down":		return status.ljust(9)
		elif status == "changed":	return status.ljust(8)
		elif status == "double":	return status.ljust(8)
		elif status == "ignored":	return status.ljust(8)
		else:						return status.ljust(10)



####-----------------	 ---------
	def completePath(self,inPath):
		if len(inPath) == 0: return ""
		if inPath == " ":	 return ""
		if inPath[-1] !="/": inPath +="/"
		return inPath


########################################
########################################
####----move files to ...indigo x.y/Preferences/Plugins/< pluginID >.----
########################################
########################################
####------ --------
	def moveToIndigoPrefsDir(self, fromPath, toPath):
		if os.path.isdir(toPath):
			return True
		indigo.server.log("--------------------------------------------------------------------------------------------------------------")
		indigo.server.log("creating plugin prefs directory ")
		os.mkdir(toPath)
		if not os.path.isdir(toPath):
			self.indiLOG.log(50,"| preference directory can not be created. stopping plugin:  "+ toPath)
			self.indiLOG.log(50,"--------------------------------------------------------------------------------------------------------------")
			self.sleep(100)
			return False
		indigo.server.log("| preference directory created;  all config.. files will be here: "+ toPath)

		if not os.path.isdir(fromPath):
			indigo.server.log("--------------------------------------------------------------------------------------------------------------")
			return True
		cmd = "cp -R '"+ fromPath+"'  '"+ toPath+"'"
		subprocess.call(cmd, shell=True )
		self.sleep(1)
		indigo.server.log("| plugin files moved:  "+ cmd)
		indigo.server.log("| please delete old files")
		indigo.server.log("--------------------------------------------------------------------------------------------------------------")
		return True


####-----------------  exception logging ---------
	def exceptionHandler(self, level, exception_error_message, extraText=""):

		try: 
			if "{}".format(exception_error_message).find("None") >-1: return 
		except: 
			pass

		filename, line_number, method, statement = traceback.extract_tb(sys.exc_info()[2])[-1]
		#module = filename.split('/')
		log_message = "'{}'".format(exception_error_message )
		log_message +=  "\n{} @line {}: '{}'".format(method, line_number, statement)
		if extraText !="":
			log_message +=  "\n{}".format(extraText)
		self.indiLOG.log(level, log_message)


########################################
########################################
####-----------------  logging ---------
########################################
########################################


####-----------------	 ---------
	def decideMyLog(self, msgLevel):
		try:
			if msgLevel	 == "all" or "all" in self.debugLevel:	 return True
			if msgLevel	 == ""	  and "all" not in self.debugLevel: return False
			if msgLevel in self.debugLevel:							 return True
			return False
		except	Exception as e:
			if "{}".format(e) != "None":
				indigo.server.log("decideMyLog Line {} has error={}".format(sys.exc_info()[2].tb_lineno, e))
		return False

####-----------------  print to logfile or indigo log  ---------
	def myLog(self, theText="", mType="", errorType="", showDate=True, destination=""):

		level = 20
		try:	theText = theText.decode('utf-8')
		except: pass
		try:

			ts = ""
			if errorType == "smallErr":
				if showDate: ts = datetime.datetime.now().strftime("%H:%M:%S")
				self.indiLOG.log(level, "----------------------------------------------------------------------------------")
				self.indiLOG.log(level,"{} {:12}-{}\n".format(ts, " ", theText))
				self.indiLOG.log(level, "----------------------------------------------------------------------------------")
				return

			if errorType == "bigErr":
				if showDate: ts = datetime.datetime.now().strftime("%H:%M:%S")
				self.indiLOG.log(level, "==================================================================================")
				self.indiLOG.log(level, "{} {:12}-{}\n".format(ts, " ", theText))
				self.indiLOG.log(level, "==================================================================================")
				return
			if showDate: ts = datetime.datetime.now().strftime("%H:%M:%S")
			if mType == "":
				self.indiLOG.log(level,"{} {:25} - {}".format(ts, " ", theText) )
			else:
				self.indiLOG.log(level,"{} {:25} - {}".format(ts, mType, theText) )
			return

		except	Exception as e:
			self.exceptionHandler(40, e)
			indigo.server.log(theText)
			indigo.server.log("type: {}".format(type(theText)))
			try: f.close()
			except: pass


##################################################################################################################
##################################################################################################################
##################################################################################################################
###################	 TCPIP listen section  receive data from RPI via socket comm  #####################

####-------------------------------------------------------------------------####
	def ipNumberOK(self, ipcheck):
		if not self.isValidIP(ipcheck): 					return False	# bad ip number 
		if not self.checkRPIipForReject: 					return True		# skip this test 
		for piU in self.RPI:   #OKconvert
			if self.RPI[piU]["piOnOff"] == "0": continue 					# not on, ignore for test
			if ipcheck == self.RPI[piU]["ipNumberPi"]:		return True		# test passed  return True

		if True:											return False	# test Failed

####-------------------------------------------------------------------------####
	def ipNumbernotInRange(self, ipcheck):
		if not self.blockNonLocalIp: 						return False # test not enabled
		if self.myIpNumberRange[0] == "-1":					return False # ip range not set
		ipcheck2	= ipcheck.split(".")
		if ipcheck2[0] != self.myIpNumberRange[0]: 			return True  # first  octet wrong
		if ipcheck2[1] != self.myIpNumberRange[1]: 			return True  # second octet wrong
		if True:											return False # test passed

####-------------------------------------------------------------------------####
	def isValidIP(self, ip0):
		ipx = ip0.split(".")
		if len(ipx) != 4:									return False	# not complete
		else:
			for ip in ipx:
				try:
					if int(ip) < 0 or  int(ip) > 255: 		return False	# out of range
				except:										return False	# not integer
		if True:											return True		# test passed 

####-------------------------------------------------------------------------####
	def isValidMAC(self, mac0):
		macx = mac0.split(":")
		if len(macx) != 6:									return False	# len(mac.split("D0:D2:B0:88:7B:76")):

		for xx in macx:
			if len(xx) !=2:									return False	# not 2 digits
			try: 	int(xx,16)
			except: 										return False	# is not a hex number

		if True:											return True		# test passed

####-------------------------------------------------------------------------####
	def handlesockReporting(self, IPN, nBytes, msgName, xType, msg=""):

		try:
			if IPN not in self.dataStats["data"]:
				self.dataStats["data"][IPN]={}

			if msgName not in self.dataStats["data"][IPN]:
				self.dataStats["data"][IPN][msgName]={}

			if xType not in self.dataStats["data"][IPN][msgName]:
				self.dataStats["data"][IPN][msgName][xType] = {"firstTime":time.time(), "lastTime":time.time()-1000, "count":0, "bytes":0,"maxBytes":0}
			if "maxBytes" not in self.dataStats["data"][IPN][msgName][xType]:
				self.dataStats["data"][IPN][msgName][xType]["maxBytes"]=0
			self.dataStats["data"][IPN][msgName][xType]["count"] += 1
			self.dataStats["data"][IPN][msgName][xType]["bytes"] += nBytes
			self.dataStats["data"][IPN][msgName][xType]["lastTime"] = time.time()
			self.dataStats["data"][IPN][msgName][xType]["maxBytes"] = max(self.dataStats["data"][IPN][msgName][xType]["maxBytes"], nBytes)

			if xType != "ok" : # log if "errxxx" and previous event was less than xxx min ago
				if time.time() - self.dataStats["data"][IPN][msgName][xType]["lastTime"] < self.maxSocksErrorTime : # log if previous event was less than 10 minutes ago
					dtLT = datetime.datetime.fromtimestamp(self.dataStats["data"][IPN][msgName][xType]["lastTime"] ).strftime(_defaultDateStampFormat)
					self.indiLOG.log(10,"TCPIP socket error rate high for {} msg:{}, Type:{}; previous:{}".format(IPN, msgName, xType, dtLT) )
					self.printTCPIPstats(all=IPN)
				self.saveTcpipSocketStats()
			elif "Socket" in self.debugLevel:
					pass


		except Exception as e:
			self.exceptionHandler(40, e)
		return


####-------------------------------------------------------------------------####
	def startTcpipListening(self, myIpNumber, indigoInputPORT):
			self.socServ = None
			stackReady	 = False
			self.indiLOG.log(10," ..   starting tcpip socket listener, for RPI data, might take some time, using: ip#={} ;  port#= {}".format(myIpNumber, indigoInputPORT) )
			tcpStart = time.time()
			lsofCMD	 ="/usr/sbin/lsof -i tcp:{}".format(indigoInputPORT)
			ret, err = self.readPopen(lsofCMD)
			if self.decideMyLog("StartSocket"): self.indiLOG.log(5," ..   startTcpipListening lsof output:{} - {}".format(ret, err) )
			self.killHangingProcess(ret)
			for ii in range(90):  #	 gives port busy for ~ 60 secs if restart, new start it is fine, error message continues even if it works -- indicator =ok: if lsof gives port number
				try:
					socS = ThreadedTCPServer((myIpNumber,int(indigoInputPORT)), ThreadedTCPRequestHandler)
					if self.decideMyLog("StartSocket"): self.indiLOG.log(5," ..   startTcpipListening try#: {:d} time elapsed: {:4.1f} secs; setting re-use = 1; timout = 5 ".format(ii, time.time()-tcpStart) )
					socS.socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
					#socketServer.socket.setsockopt(socket.SOL_SOCKET, socket.timeout, 5 )
					socS.socket.settimeout( 5 )
				except Exception as e:
					if self.decideMyLog("StartSocket"): self.indiLOG.log(5," ..   startTcpipListening try#: {:d} time elapsed: {:4.1f} secs; resp: {}".format(ii, time.time()-tcpStart, e ) )

				try:
					ret, err = self.readPopen(lsofCMD)
					if len(ret) >0: #  if lsof gives port number it works..
						if self.decideMyLog("StartSocket"): self.indiLOG.log(5," ..   startTcpipListening {}   output:\n{}".format(lsofCMD, ret.strip("\n")) )
						TCPserverHandle = threading.Thread(target=socS.serve_forever)
						TCPserverHandle.daemon =True # don't hang on exit
						TCPserverHandle.start()
						break
				except Exception as e:
					if "{}".format(e).find("serve_forever") == -1:
						self.exceptionHandler(40, e)
					self.killHangingProcess(ret)

				self.sleep(1)
				if	 ii <= 2:	self.sleep(6)

			try:
				tcpName = TCPserverHandle.getName()
				self.indiLOG.log(10,' ..   startTcpipListening tcpip socket listener running; thread-ID: {}'.format(tcpName) )#	+ " try:{}".format(ii)+"  time elapsed:{}".format(time.time()-tcpStart) )
				stackReady = True


			except Exception as e:
				self.exceptionHandler(40, e, extraText="..   startTcpipListening tcpip stack did not load, restarting.. if this error continues, try restarting indigo server")
				self.quitNow = " tcpip stack did not load, restart"
			return	socS, stackReady



####-------------------------------------------------------------------------####
	def readPopen(self, cmd):
		try:
			ret, err = subprocess.Popen(cmd, shell=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE).communicate()
			return ret.decode('utf_8'), err.decode('utf_8')
		except Exception as e:
			self.exceptionHandler(40, e)

####-------------------------------------------------------------------------####
	def killHangingProcess(self, ret):
		try:
			test = ret.strip("\n").split("\n")

			if len(test) > 1:
				try:
					for xx in test[1:]: # skip headerline
						pidTokill = int((xx.split())[1])
						killcmd = "/bin/kill -9 {}".format(pidTokill)
						self.indiLOG.log(10," ..   startTcpipListening .. trying to kill hanging process with: {}, process:{} ".format(killcmd, xx) )
						subprocess.call(killcmd, shell=True)
				except Exception as e:
					self.exceptionHandler(40, e)
		except Exception as e:
			self.exceptionHandler(40, e)


####-------------------------------------------------------------------------####
####-------------------------------------------------------------------------####
####-------------------------------------------------------------------------####
class ThreadedTCPRequestHandler(SocketServer.BaseRequestHandler):

####-------------------------------------------------------------------------####
	def handle(self):
		try:
			data0 = ""
			dataS =[]
			tStart=time.time()
			maxWaitTime = 20.
			len0 = 0
			piName = "none"
			wrongIP = 0
			idTag = "x-6-a"
			header = ""
			nBytes = 0

			#indigo.server.log("hello")
			if	indigo.activePlugin.ipNumberOK(self.client_address[0]):
				pass
			elif indigo.activePlugin.ipNumbernotInRange(self.client_address[0]):
				indigo.activePlugin.indiLOG.log(30, "TCPIP socket data receiving from {} outside ip number range<<   allowed:{}.{}.x.x".format(self.client_address, indigo.activePlugin.myIpNumberRange[0], indigo.activePlugin.myIpNumberRange[1])  )
				indigo.activePlugin.handlesockReporting(self.client_address[0],0, "badIP", "extIP" )
				self.request.close()
				return 
			else:
				wrongIP = 2
				indigo.activePlugin.indiLOG.log(30, "TCPIP socket data receiving from {} not in accepted ip number list, please fix in >>initial setup RPI<<".format(self.client_address)  )
				#  add looking for ip = ,"ipAddress":"192.168.1.20"
				# but need first to read data
				indigo.activePlugin.handlesockReporting(self.client_address[0],0, "IP#-Wrong", "errIP" )
				#self.request.close()
				#return
			#indigo.activePlugin.indiLOG.log(30, "testing  ip number range<< from :{};  allowed:{}.{}.x.x".format(self.client_address, indigo.activePlugin.myIpNumberRange[0], indigo.activePlugin.myIpNumberRange[1])  )

			# 3 secs should be enough even for slow network mostly one package, should all be send in one package
			self.request.settimeout(10)
			seqN = 0
			nMaxSeq = 1000
			try: # to catch timeout
				while True: # until end of message
					if seqN > nMaxSeq: break # safety valve , nothing > 1Mb
					piName = ""
					nBytes = 0
					seqN +=1
					buff = self.request.recv(4096)
					
					if not buff or len(buff) == 0:
						break
					if data0 == "":	data0  = buff
					else:			data0 += buff
					len0  = len(data0)

					### check if package is complete:
					## first part is : "{}x-6-a{}x-6-a{} padded w blanks for 30 characters
					try: 	header = data0[:30].decode('utf-8')
					except:	header = data0[:30]
					actualData = data0[30:]
					#indigo.activePlugin.indiLOG.log(20,"ThreadedTCPRequestHandler test {} type {}".format(test, type(test)) )

					#indigo.activePlugin.indiLOG.log(20,"ThreadedTCPRequestHandler header :{}, len:{}, seq:{} , type of header:{} type of actualData:{}".format(header, len0, seqN, type(header), type(actualData)) )
					headerSplit = header.split(idTag)
					if len(headerSplit) < 3: continue
					try:
						nBytes = int(headerSplit[0])
						piName = headerSplit[1]
						isCompressed =  headerSplit[2].strip().find("+comp") > -1
						#indigo.activePlugin.indiLOG.log(20,"ThreadedTCPRequestHandler header :{}, nBytes:{}, name:{}, isCompressed:{}".format(header, nBytes, piName, isCompressed) )
					except Exception as e:
						indigo.activePlugin.indiLOG.log(30,"ThreadedTCPRequestHandler Line {} has error={}".format(sys.exc_info()[2].tb_lineno, e) )
						break

					if len(headerSplit) == 3 and nBytes == len(actualData):
						break

					#safety valves
					if time.time() - tStart > maxWaitTime: break
					if	len0 > nMaxSeq*4096: # check for overflow
						indigo.activePlugin.handlesockReporting(self.client_address[0],len0, "unknown", "errBuffOvfl" )
						indigo.activePlugin.indiLOG.log(30,"ThreadedTCPRequestHandler buffer overflow ={}".format(time.time() - tStart ) )
						self.request.close()
						return

			except Exception as e:
				e = str(e)
				sendError = e[0:min(10,len(e))]
				self.request.settimeout(1)

				self.sendResponse("{}; received bytes:{} in {} packets".format(sendError, len0, seqN))	
				indigo.activePlugin.indiLOG.log(40,"ThreadedTCPRequestHandler Line {} has error={}".format(sys.exc_info()[2].tb_lineno, e) )
				if e.find("timed out") == -1:
					indigo.activePlugin.handlesockReporting( self.client_address[0],len0, piName,e[0:min(10,len(e))] )
				else:
					indigo.activePlugin.indiLOG.log(30,".. received data  tries:{}, len:{}, dt:{:.1f}, header:{}".format(seqN, nBytes, time.time() - tStart, header) )
					indigo.activePlugin.handlesockReporting( self.client_address[0], len0, piName, "timeout" )
				return

			self.request.settimeout(3)

			try:
				## split message should look like:  len-TAG-piName-TAG-data; -TAG- = x-6-a
				if piName == "": # tag not found
					if indigo.activePlugin.decideMyLog("Socket"): indigo.activePlugin.indiLOG.log(10,"TCPIP socket  \"x-6-a\"   not found in header: \"{}\", headerSplit:\"{}\", nbytes:{}, seqN:{}".format(header, headerSplit, nBytes, seqN) )
					self.sendResponse("error-tag missing")
					self.sendResponse("error")	
					indigo.activePlugin.handlesockReporting(self.client_address[0],len0,piName, "errTag" )
					return

				lenData   = len(actualData)

				if lenData != nBytes: # expected # of bytes not received
					if lenData < nBytes:
						if indigo.activePlugin.decideMyLog("Socket"): indigo.indigoLOG.log(30,"TCPIP socket length of {} data too short, len:{};   piName:; {}".format(header, nBytes, piName) )
						self.sendResponse("error-lenDatawrong-{}".format(lenData0))	
						self.sendResponse("error,len-short")	
						indigo.activePlugin.handlesockReporting(self.client_address[0],len0,piName, "tooShort" )
						return
					else:
						# check if we received a complete package + extra
						package1 = actualData
						if isCompressed:
							package1 = zlib.decompress(actualData)
						try:
							json.loads(package1.decode('utf-8'))
							if indigo.activePlugindecideMyLog("Socket"): indigo.activePlugin.indiLOG.log(30,"TCPIP socket length of data wrong -fixed- {};   nBytes:{};   piName:{} ".format(header, nBytes, piName) )
						except:
							if indigo.activePlugindecideMyLog("Socket"): indigo.activePlugin.indiLOG.log(30,"TCPIP socket length of data wrong exp:{};   nBytes:{};   piName:; {}".format(header, nBytes, piName) )
	
							self.sendResponse("error-lenDatawrong-{}".format(lenData))	
							indigo.activePlugin.handlesockReporting(self.client_address[0],lenData,piName, "tooLong" )
							return

			except Exception as e:
				if indigo.activePlugin.decideMyLog("Socket"): indigo.activePlugin.indiLOG.log(30,"ThreadedTCPRequestHandler Line {} has error={}".format(sys.exc_info()[2].tb_lineno, e))
				if indigo.activePlugin.decideMyLog("Socket"): indigo.activePlugin.indiLOG.log(30, "TCPIP socket, len:{:d} header: {:} ".format(nBytes, header) )
				if indigo.activePlugin.decideMyLog("Socket"): indigo.activePlugin.handlesockReporting(self.client_address[0],lenData,piName, "unknown" )
				self.sendResponse("error-general")	
				return

			try:
				if isCompressed:
					dataJIn = zlib.decompress(actualData).decode('utf-8')
					if indigo.activePlugin.decideMyLog("Socket"): indigo.activePlugin.indiLOG.log(10,"TCPIP socket  listener pi:{}, compressed:{}/ uncompressedfile len:{}".format(piName, len(actualData), len(dataJIn)) )
				else:
					dataJIn = actualData.decode('utf-8')
				if dataJIn.find("NaN") > -1:
					dataJIn.replace("NaN","-9999")
				dataJ = json.loads(dataJIn)  
			except Exception as e:
				indigo.activePlugin.indiLOG.log(30, "ThreadedTCPRequestHandler Line {} has error={}".format(sys.exc_info()[2].tb_lineno, e))
				if indigo.activePlugin.decideMyLog("Socket"): indigo.activePlugin.indiLOG.log(30,"TCPIP socket json error; len of data: {:d}  time used: {:5.1f}".format(nBytes, time.time()-tStart )  )
				if indigo.activePlugin.decideMyLog("Socket"): indigo.activePlugin.indiLOG.log(30,+"{}  ..  {}".format(dataJIn[0:50], dataJIn[-10:]) )
				self.sendResponse("error-Json-{}".format(lenData))	
				indigo.activePlugin.handlesockReporting(self.client_address[0],nBytes,piName, "errJson" )
				return

			if piName.find("pi_IN_") != 0 :
				if indigo.activePlugin.decideMyLog("Socket"): indigo.activePlugin.indiLOG.log(30,"TCPIP socket  listener bad piName {}".format(piName) )
				indigo.activePlugin.handlesockReporting(self.client_address[0],nBytes,piName, "badpiName" )
			else:
				wrongIP -= 1
				#### now update Indigo dev/ states
				#indigo.activePlugin.indiLOG.log(30, "ThreadedTCPRequestHandler adding to queue: {} --- {} bad ip count:{}".format(piName, dataJIn[:30], wrongIP))
				indigo.activePlugin.addToDataQueue( piName, dataJ, dataJIn )
				indigo.activePlugin.handlesockReporting(self.client_address[0],nBytes,piName, "ok",msg=header )

				if wrongIP < 2:
					if indigo.activePlugin.decideMyLog("Socket"):
						indigo.activePlugin.indiLOG.log(10, " sending ok to {} data: {}..{}".format(piName.ljust(13),dataJIn[0:50], dataJIn[:-20]) )
					self.sendResponse("ok-{}-{}".format(len0,lenData))

		except Exception as e:
			indigo.activePlugin.indiLOG.log(30, "ThreadedTCPRequestHandler Line {} has error={}".format(sys.exc_info()[2].tb_lineno, e))
			indigo.activePlugin.indiLOG.log(30, "TCPIP socket data:{}<<".format(data0[0:50]) )
			indigo.activePlugin.handlesockReporting(self.client_address[0],nBytes,piName, "Exception" )

		try:	self.request.close()
		except: pass
		return

	def sendResponse(self, strSend):
		try:
			if indigo.activePlugin.decideMyLog("Socket"): indigo.activePlugin.indiLOG.log(10,"TCPIP socket  closing connection {}".format(strSend) )
			if sys.version_info[0] == 3: 	self.request.send(bytes(strSend,'utf-8'))
			else:							self.request.send(strSend)
			self.request.close()
		except Exception as e:
			indigo.activePlugin.indiLOG.log(30, "ThreadedTCPRequestHandler Line {} has error={}".format(sys.exc_info()[2].tb_lineno, e))

####-------------------------------------------------------------------------####
####-------------------------------------------------------------------------####
class ThreadedTCPServer(SocketServer.ThreadingMixIn, SocketServer.TCPServer):
	pass

###################	 TCPIP listen section  receive data from RPI via socket comm  end			 #################
##################################################################################################################
##################################################################################################################




##################################################################################################################
####-----------------  valiable formatter for differnt log levels ---------
# call with:
# formatter = LevelFormatter(fmt='<default log format>', level_fmts={logging.INFO: '<format string for info>'})
# handler.setFormatter(formatter)
class LevelFormatter(logging.Formatter):
####-------------------------------------------------------------------------####
	def __init__(self, fmt=None, datefmt=None, level_fmts={}, level_date={}):
		self._level_formatters = {}
		self._level_date_format = {}
		for level, formt in level_fmts.items():
			# Could optionally support level names too
			self._level_formatters[level] = logging.Formatter(fmt=formt, datefmt=level_date[level])
		# self._fmt will be the default format
		super(LevelFormatter, self).__init__(fmt=formt, datefmt=datefmt)

####-------------------------------------------------------------------------####
	def format(self, record):
		if record.levelno in self._level_formatters:
			return self._level_formatters[record.levelno].format(record)

		return super(LevelFormatter, self).format(record)




