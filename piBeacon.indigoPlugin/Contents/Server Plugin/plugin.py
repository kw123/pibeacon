#! /usr/bin/env python
# -*- coding: utf-8 -*-
####################
# pibeacon Plugin
# Developed by Karl Wachs
# karlwachs@me.com

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
import SocketServer
import Queue
import cProfile
import pstats
import logging

import MACMAP.MAC2Vendor as M2Vclass
#import pydevd_pycharm
#pydevd_pycharm.settrace('localhost', port=5678, stdoutToServer=True, stderrToServer=True)

try:
	# noinspection PyUnresolvedReferences
	import indigo
except ImportError:
	pass
################################################################################
##########  Static parameters, not changed in pgm
################################################################################
_GlobalConst_numberOfiBeaconRPI	 = 20
_GlobalConst_numberOfRPI		 = 41
_rpiList = [str(ii) for ii in range(_GlobalConst_numberOfRPI)]
_rpiBeaconList = [str(ii) for ii in range(_GlobalConst_numberOfiBeaconRPI)]
_rpiSensorList = [str(ii) for ii in range(_GlobalConst_numberOfiBeaconRPI, _GlobalConst_numberOfRPI)]
_sqlLoggerDevTypes  = ["isBeaconDevice","isRPIDevice","isRPISensorDevice","isBLEconnectDevice", "isSensorDevice"]
_sqlLoggerDevTypesNotSensor = _sqlLoggerDevTypes[:-1]
_sqlLoggerIgnoreStates = {"isBeaconDevice":		"Pi_00_Time,Pi_01_Time,Pi_02_Time,Pi_03_Time,Pi_04_Time,Pi_05_Time,Pi_06_Time,Pi_07_Time,Pi_08_Time,Pi_09_Time,Pi_10_Time,Pi_11_Time,Pi_12_Time,Pi_13_Time,Pi_14_Time,Pi_15_Time,Pi_16_Time,Pi_17_Time,Pi_18_Time,Pi_19_Time,TxPowerReceived,UUID,closestRPIText,closestRPITextLast,displayStatus,status,batteryLevelLastUpdate,pktInfo,sensorvalue_ui,updateReason,lastStatusChange"
				         ,"isRPIDevice":		"Pi_00_Time,Pi_01_Time,Pi_02_Time,Pi_03_Time,Pi_04_Time,Pi_05_Time,Pi_06_Time,Pi_07_Time,Pi_08_Time,Pi_09_Time,Pi_10_Time,Pi_11_Time,Pi_12_Time,Pi_13_Time,Pi_14_Time,Pi_15_Time,Pi_16_Time,Pi_17_Time,Pi_18_Time,Pi_19_Time,TxPowerReceived,UUID,closestRPIText,closestRPITextLast,displayStatus,status,pktInfo,online,i2cactive,sensorvalue_ui,updateReason,lastStatusChange,last_MessageFromRpi"
						 ,"isBLEconnectDevice":	"Pi_00_Time,Pi_01_Time,Pi_02_Time,Pi_03_Time,Pi_04_Time,Pi_05_Time,Pi_06_Time,Pi_07_Time,Pi_08_Time,Pi_09_Time,Pi_10_Time,Pi_11_Time,Pi_12_Time,Pi_13_Time,Pi_14_Time,Pi_15_Time,Pi_16_Time,Pi_17_Time,Pi_18_Time,Pi_19_Time,TxPowerReceived,closestRPIText,closestRPITextLast,displayStatus,status,sensorvalue_ui,lastStatusChange"
				         ,"isRPISensorDevice":	"displayStatus,status,sensorvalue_ui,lastStatusChange,last_MessageFromRpi"
				         ,"isSensorDevice":		"displayStatus,status,sensorvalue_ui,lastStatusChange"}
_debugAreas = ["Logic","DevMgmt","BeaconData","SensorData","OutputDevice","UpdateRPI","OfflineRPI","Fing","BLE","CAR","BC","all","Socket","Special","PlotPositions","SocketRPI","BatteryLevel","SQLlogger","SQLSuppresslog"]

_GlobalConst_emptyBeacon = {u"indigoId": 0, u"ignore": 0, u"status": u"up", u"lastUp": 0, u"note": u"beacon", u"expirationTime": 90,
			   u"created": 0, u"updateFING": 0, u"updateWindow": 0, u"updateSignalValuesSeconds": 0, u"signalDelta": 999, u"minSignalCutoff": -999,
			   u"PosX": 0., u"PosY": 0., u"PosZ": 0., u"typeOfBeacon": u"other", u"beaconTxPower": +999, u"fastDown": u"0",
			   u"fastDownMinSignal":	-999,
			   u"showBeaconOnMap": 		u"0","showBeaconNickName": u"",u"showBeaconSymbolAlpha": u"0.5",u"showBeaconSymboluseErrorSize": u"1",u"showBeaconSymbolColor": u"b",
			   u"receivedSignals":		[{"rssi":-999, "lastSignal": 0, "distance":99999} for kk in range(_GlobalConst_numberOfiBeaconRPI)]} #  for 10 RPI
_GlobalConst_typeOfBeacons = {
				u"xy":			u"07775dd0111b11e491910800200c9a66",
				 u"tile":		u"01",
				 u"sanwo":		u"fda50693a4e24fb1afcfc6eb07647825",
				 u"radius":		u"2f234454cf6d4a0fadf2f4911ba9ffa6",
				 u"rPI":		u"2f234454cf6d4a0fadf2f4911ba9ffa6-9",
				 u"pebbleBee":	u"1804180f1803190002020a0808ff0e0a",
				 u"JINOU":		u"e2c56db5dffb48d2b060d0f5a71096e0",
				 u"Jaalee":		u"ebefd08370a247c89837e7b5634df524",
				 u"other":		u"",
				 u"Other1":		u"",
				 u"Other2":		u"",
				 u"highTx":		u"",
				 }
_GlobalConst_emptyBeaconProps = {
					u"note":						u"beacon",
					u"expirationTime":				90,
					u"created":						0,
					u"updateSignalValuesSeconds":	0,
					u"signalDelta":					999,
					u"minSignalCutoff":				-999,
					u"typeOfBeacon":				u"other",
					u"beaconTxPower":				999,
					u"memberOfFamily":				0,
					u"memberOfGuests":				0,
					u"memberOfOther1":				0,
					u"memberOfOther2":				0,
					u"ignore":						0,
					u"enableBroadCastEvents":		"0",
					u"fastDownMinSignal":			-999,
					u"showBeaconOnMap": 			u"0",u"showBeaconNickName": u"",u"showBeaconSymbolType": u",",u"showBeaconSymbolAlpha": u"0.5",u"showBeaconSymboluseErrorSize": u"1",u"showBeaconSymbolColor": u"b",
					u"fastDown": 					u"0"}

_GlobalConst_emptyrPiProps	  ={u"typeOfBeacon":		u"rPI",
						u"updateSignalValuesSeconds":	300,
						u"beaconTxPower":				999,
						u"SupportsBatteryLevel":		False,
						u"sendToIndigoSecs":			90,
						u"sensorRefreshSecs":			90,
						u"deltaChangedSensor":			5,
						u"PosXYZ":						u"0.,0.,0.",
						u"BLEserial":					u"sequential",
						u"shutDownPinInput" :			u"-1",
						u"signalDelta" :				u"999",
						u"minSignalCutoff" :			u"-999",
						u"expirationTime" :				u"90",
						u"fastDown" :					u"0",
						u"enableBroadCastEvents":		"0",
						u"rssiOffset" :					0,
						u"shutDownPinOutput" :			u"-1" }

_GlobalConst_fillMinMaxStates = ["Temperature","AmbientTemperature","Pressure","Humidity","AirQuality","visible","ambient","white","illuminance","IR","CO2","VOC","INPUT_0","rainRate","Moisture","INPUT"]

_GlobalConst_emptyRPI =	  {
	u"rpiType":					u"rPi",
	u"enableRebootCheck":		u"restartLoop",
	u"enableiBeacons":			u"1",
	u"input":					{},
	u"ipNumberPi":				u"",
	u"ipNumberPiSendTo":		u"",
	u"output":					{},
	u"passwordPi":				u"raspberry",
	u"piDevId":					0,
	u"piMAC":					u"",
	u"piNumberReceived":		u"",
	u"piOnOff":					u"0",
	u"authKeyOrPassword":		u"assword",
	u"piUpToDate": 				[],
	u"sensorList": 				u"0,",
	u"lastMessage":				0,
	u"sendToIndigoSecs":		90,
	u"sensorRefreshSecs":		20,
	u"deltaChangedSensor":		5,
	u"rssiOffset" :				0,
	u"emptyMessages":			0,
	u"deltaTime1":				100,
	u"deltaTime2": 				100,
	u"PosX": 					0,
	u"PosY": 					0,
	u"PosZ": 					0,
	u"userIdPi": 				u"pi"}


_GlobalConst_emptyRPISENSOR =	{
	u"rpiType":				u"rPiSensor",
	u"enableRebootCheck":	u"restartLoop",
	u"enableiBeacons":		u"0",
	u"input":				{},
	u"ipNumberPi":			u"",
	u"ipNumberPiSendTo":	u"",
	u"lastUpPi":			0,
	u"output":				{},
	u"passwordPi":			u"raspberry",
	u"authKeyOrPassword": 	u"assword",
	u"piDevId":				0,
	u"piMAC":				u"",
	u"piNumberReceived":	u"",
	u"piOnOff":				u"0",
	u"piUpToDate":			[],
	u"sensorList":			u"0,",
	u"lastMessage":			0,
	u"sendToIndigoSecs":	90,
	u"sensorRefreshSecs":	20,
	u"deltaChangedSensor":	5,
	u"emptyMessages":		0,
	u"userIdPi": 			u"pi"}

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



_GlobalConst_allowedCommands	   = [u"up", u"down", u"pulseUp", u"pulseDown", u"continuousUpDown", u"analogWrite", u"disable", u"newMessage", u"resetDevice", u"getBeaconParameters", u"startCalibration", u"rampUp", u"rampDown", u"rampUpDown"]	 # commands support for GPIO pins

_GlobalConst_allowedSensors		   = [u"ultrasoundDistance", u"vl503l0xDistance", u"vl6180xDistance", u"vcnl4010Distance", # dist / light
						 u"apds9960",															  # dist gesture
						 u"i2cTCS34725", u"i2cTSL2561", u"i2cVEML6070", u"i2cVEML6030", u"i2cVEML6040", u"i2cVEML7700",		# light 
						 u"i2cVEML6075", u"i2cIS1145", u"i2cOPT3001",									# light	  
						 u"BLEsensor",
						 u"Wire18B20", u"i2cTMP102", u"i2cMCP9808", u"i2cLM35A",						 # temp 
						 u"DHT", u"i2cAM2320", u"i2cSHT21","si7021",						 # temp / hum
						 u"i2cBMPxx", u"i2cT5403", u"i2cBMP280","i2cMS5803",						 # temp / press
						 u"i2cBMExx",															 # temp / press/ hum /
						 u"bme680",																   # temp / press/ hum / gas
						 u"tmp006",																   # temp rmote infrared
						 u"tmp007",																   # temp rmote infrared
						 u"max31865",																# platinum temp resistor 
						 u"pmairquality",
						 u"amg88xx","mlx90640",													# infrared camera
						 u"lidar360",															# rd lidar 
						 u"ccs811",																   # co2 voc 
						 u"mhzCO2",																# co2 temp 
						 u"rainSensorRG11",
						 u"moistureSensor",
						 u"launchpgm",
						 u"sgp30",																  # co2 voc 
						 u"as3935",																	# lightning sensor 
						 u"i2cMLX90614", u"mlx90614",												   # remote	 temp &ambient temp 
						 u"ina219",																	 # current and V 
						 u"ina3221",																  # current and V 3 channels
						 u"PCF8591",																  #  V 4 channels
						 u"ADS1x15",																  #  V 4 channels
						 u"as726x",																	 # rgb yellow orange violot
						 u"MAX44009",																# illuminance sensor
						 u"l3g4200", u"bno055", u"mag3110", u"mpu6050", u"hmc5883L", u"mpu9255", u"lsm303",	   # gyroscope
						 u"INPgpio", u"INPUTgpio-1", u"INPUTgpio-4", u"INPUTgpio-8", u"INPUTgpio-26",		# gpio inputs
						 u"INPUTtouch-1", u"INPUTtouch-4", u"INPUTtouch-8", u"INPUTtouch-12", u"INPUTtouch-16",		 # capacitor inputs
						 u"INPUTtouch12-1", u"INPUTtouch12-4", u"INPUTtouch12-8", u"INPUTtouch12-12",	   # capacitor inputs
						 u"INPUTtouch16-1", u"INPUTtouch16-4", u"INPUTtouch16-8", u"INPUTtouch16-16",	   # capacitor inputs
						 u"INPUTRotarySwitchAbsolute","INPUTRotarySwitchIncremental",
						 u"spiMCP3008", u"spiMCP3008-1","i2cADC121",
						 u"INPUTpulse", "INPUTcoincidence",
						 u"mysensors", u"myprogram",
						 u"BLEconnect"]

_GlobalConst_lightSensors =["i2cVEML6075","i2cIS1145","i2cOPT3001","i2cTCS34725","i2cTSL2561","i2cVEML6070","i2cVEML6040","i2cVEML7700"]

_GlobalConst_i2cSensors				 = ["si7021","bme680","amg88xx","mlx90640",	"ccs811",u"sgp30", u"mlx90614",	 "ina219","ina3221","as726x","as3935","moistureSensor", "PCF8591","ADS1x15",
										u"l3g4200", u"bno055", u"mag3110", u"mpu6050", u"hmc5883L", u"mpu9255", u"lsm303", u"vl6180xDistance", u"vcnl4010Distance",u"apds9960"]

_GlobalConst_allowedOUTPUT			= [u"neopixel", u"neopixel-dimmer", u"neopixelClock", u"OUTPUTgpio-1-ONoff", u"OUTPUTgpio-1", u"OUTPUTi2cRelay", u"OUTPUTgpio-4", u"OUTPUTgpio-10", u"OUTPUTgpio-26", u"setMCP4725",  u"OUTPUTxWindows", u"display", u"setPCF8591dac", u"setTEA5767", u"sundial", u"setStepperMotor"]

_GlobalConst_allowedpiSends			= [u"updateParamsFTP", u"updateAllFilesFTP", u"rebootSSH", u"resetOutputSSH", u"shutdownSSH", u"getStatsSSH", u"initSSH", u"upgradeOpSysSSH"]


_GlobalConst_groupList				= [u"Family", u"Guests", u"Other1", u"Other2"]

_defaultDateStampFormat				= u"%Y-%m-%d %H:%M:%S"

################################################################################
################################################################################
################################################################################

# 
# noinspection PySimplifyBooleanCheck,PySimplifyBooleanCheck,PySimplifyBooleanCheck,PySimplifyBooleanCheck,PySimplifyBooleanCheck,PySimplifyBooleanCheck,PySimplifyBooleanCheck,PyAttributeOutsideInit,PyAttributeOutsideInit,PyAttributeOutsideInit,PyAttributeOutsideInit,PyAttributeOutsideInit,PyAttributeOutsideInit,PyAttributeOutsideInit,PyAttributeOutsideInit,PyAttributeOutsideInit,PyAttributeOutsideInit,PyAttributeOutsideInit,PyAttributeOutsideInit,PyAttributeOutsideInit,PyAttributeOutsideInit,PyAttributeOutsideInit,PyAttributeOutsideInit,PyAttributeOutsideInit,PyAttributeOutsideInit,PyAttributeOutsideInit,PyAttributeOutsideInit,PyAttributeOutsideInit,PyAttributeOutsideInit,PyAttributeOutsideInit,PyAttributeOutsideInit,PyAttributeOutsideInit,PyAttributeOutsideInit,PyAttributeOutsideInit,PyAttributeOutsideInit,PyAttributeOutsideInit,PyAttributeOutsideInit,PyAttributeOutsideInit,PyAttributeOutsideInit,PyAttributeOutsideInit,PyAttributeOutsideInit,PyAttributeOutsideInit,PyAttributeOutsideInit,PyAttributeOutsideInit,PyAttributeOutsideInit,PyAttributeOutsideInit,PyAttributeOutsideInit,PyAttributeOutsideInit,PyAttributeOutsideInit,PyAttributeOutsideInit,PyAttributeOutsideInit,PyAttributeOutsideInit,PyAttributeOutsideInit,PyAttributeOutsideInit,PyAttributeOutsideInit,PyAttributeOutsideInit,PyAttributeOutsideInit,PyAttributeOutsideInit,PyAttributeOutsideInit,PyAttributeOutsideInit,PyAttributeOutsideInit,PyAttributeOutsideInit,PyAttributeOutsideInit,PyAttributeOutsideInit,PyAttributeOutsideInit,PyAttributeOutsideInit,PyAttributeOutsideInit,PyAttributeOutsideInit,PyAttributeOutsideInit,PyAttributeOutsideInit,PyAttributeOutsideInit,PyAttributeOutsideInit,PyAttributeOutsideInit,PyAttributeOutsideInit,PyAttributeOutsideInit,PyAttributeOutsideInit,PyAttributeOutsideInit,PyAttributeOutsideInit,PyAttributeOutsideInit,PyAttributeOutsideInit,PyAttributeOutsideInit,PyAttributeOutsideInit,PyAttributeOutsideInit,PyAttributeOutsideInit,PyAttributeOutsideInit,PyAttributeOutsideInit,PyAttributeOutsideInit,PyAttributeOutsideInit,PyAttributeOutsideInit,PyAttributeOutsideInit,PyAttributeOutsideInit,PyAttributeOutsideInit,PyAttributeOutsideInit,PyAttributeOutsideInit,PyAttributeOutsideInit,PyAttributeOutsideInit,PyAttributeOutsideInit,PyAttributeOutsideInit,PyAttributeOutsideInit,PyAttributeOutsideInit,PyAttributeOutsideInit,PyAttributeOutsideInit,PyAttributeOutsideInit,PyAttributeOutsideInit,PyAttributeOutsideInit,PyAttributeOutsideInit,PyAttributeOutsideInit,PyAttributeOutsideInit,PyAttributeOutsideInit,PyAttributeOutsideInit,PyAttributeOutsideInit,PyAttributeOutsideInit,PyAttributeOutsideInit,PyAttributeOutsideInit,PyAttributeOutsideInit,PyAttributeOutsideInit,PyAttributeOutsideInit,PyAttributeOutsideInit,PyAttributeOutsideInit,PyAttributeOutsideInit,PyAttributeOutsideInit,PyAttributeOutsideInit,PyAttributeOutsideInit,PyAttributeOutsideInit,PyAttributeOutsideInit,PyAttributeOutsideInit,PyAttributeOutsideInit,PyAttributeOutsideInit,PyAttributeOutsideInit,PyAttributeOutsideInit,PyAttributeOutsideInit,PyAttributeOutsideInit,PyAttributeOutsideInit,PyAttributeOutsideInit,PyAttributeOutsideInit,PyAttributeOutsideInit,PyAttributeOutsideInit,PyAttributeOutsideInit,PyAttributeOutsideInit,PyAttributeOutsideInit,PyAttributeOutsideInit,PyAttributeOutsideInit,PyAttributeOutsideInit,PyAttributeOutsideInit,PyAttributeOutsideInit,PyAttributeOutsideInit,PyAttributeOutsideInit,PyAttributeOutsideInit,PyAttributeOutsideInit,PyAttributeOutsideInit,PyAttributeOutsideInit,PyAttributeOutsideInit,PyAttributeOutsideInit,PyAttributeOutsideInit,PyAttributeOutsideInit,PyAttributeOutsideInit,PyAttributeOutsideInit,PyAttributeOutsideInit,PyAttributeOutsideInit,PyAttributeOutsideInit,PyAttributeOutsideInit,PyAttributeOutsideInit,PyAttributeOutsideInit,PyAttributeOutsideInit,PyAttributeOutsideInit,PyAttributeOutsideInit,PyAttributeOutsideInit,PyAttributeOutsideInit,PyAttributeOutsideInit,PyAttributeOutsideInit,PyAttributeOutsideInit,PyAttributeOutsideInit,PyAttributeOutsideInit,PyAttributeOutsideInit,PyAttributeOutsideInit,PyAttributeOutsideInit,PyAttributeOutsideInit,PyAttributeOutsideInit,PyAttributeOutsideInit,PyAttributeOutsideInit,PyAttributeOutsideInit,PyAttributeOutsideInit,PyAttributeOutsideInit,PyAttributeOutsideInit,PyAttributeOutsideInit,PyAttributeOutsideInit,PyAttributeOutsideInit,PyAttributeOutsideInit,PyAttributeOutsideInit,PyAttributeOutsideInit,PyAttributeOutsideInit,PyAttributeOutsideInit,PyAttributeOutsideInit,PyAttributeOutsideInit,PyAttributeOutsideInit,PyAttributeOutsideInit,PyAttributeOutsideInit,PyAttributeOutsideInit,PyAttributeOutsideInit,PyAttributeOutsideInit,PyAttributeOutsideInit,PyAttributeOutsideInit,PyAttributeOutsideInit,PyAttributeOutsideInit,PyAttributeOutsideInit,PyAttributeOutsideInit,PyAttributeOutsideInit,PyAttributeOutsideInit,PyAttributeOutsideInit,PyAttributeOutsideInit,PyAttributeOutsideInit,PyAttributeOutsideInit,PyAttributeOutsideInit,PyAttributeOutsideInit,PyAttributeOutsideInit,PyAttributeOutsideInit,PyAttributeOutsideInit,PyAttributeOutsideInit,PyAttributeOutsideInit,PyAttributeOutsideInit,PyAttributeOutsideInit,PyAttributeOutsideInit,PyAttributeOutsideInit,PyAttributeOutsideInit,PyAttributeOutsideInit,PyAttributeOutsideInit,PyAttributeOutsideInit,PyAttributeOutsideInit,PyAttributeOutsideInit,PyAttributeOutsideInit,PyAttributeOutsideInit,PyAttributeOutsideInit,PyAttributeOutsideInit,PyAttributeOutsideInit,PyAttributeOutsideInit,PyAttributeOutsideInit,PyAttributeOutsideInit,PyAttributeOutsideInit,PyAttributeOutsideInit,PyAttributeOutsideInit,PyAttributeOutsideInit,PyAttributeOutsideInit,PyAttributeOutsideInit,PyAttributeOutsideInit,PyAttributeOutsideInit,PyAttributeOutsideInit,PyAttributeOutsideInit,PyAttributeOutsideInit,PyAttributeOutsideInit,PyAttributeOutsideInit,PyAttributeOutsideInit,PyAttributeOutsideInit,PyAttributeOutsideInit,PyAttributeOutsideInit,PyAttributeOutsideInit,PyAttributeOutsideInit,PyAttributeOutsideInit,PyAttributeOutsideInit,PyAttributeOutsideInit,PyAttributeOutsideInit,PyAttributeOutsideInit,PyAttributeOutsideInit,PyAttributeOutsideInit,PyAttributeOutsideInit,PyAttributeOutsideInit,PyAttributeOutsideInit,PyAttributeOutsideInit,PyAttributeOutsideInit,PyAttributeOutsideInit,PyAttributeOutsideInit,PyAttributeOutsideInit,PyAttributeOutsideInit,PyAttributeOutsideInit,PyAttributeOutsideInit,PyAttributeOutsideInit,PyAttributeOutsideInit,PyAttributeOutsideInit,PyAttributeOutsideInit,PyAttributeOutsideInit,PyAttributeOutsideInit,PyAttributeOutsideInit,PyAttributeOutsideInit,PyAttributeOutsideInit,PyAttributeOutsideInit,PyAttributeOutsideInit,PyAttributeOutsideInit,PyAttributeOutsideInit,PyAttributeOutsideInit,PyAttributeOutsideInit,PyAttributeOutsideInit,PyAttributeOutsideInit,PyAttributeOutsideInit,PyAttributeOutsideInit,PyAttributeOutsideInit,PyAttributeOutsideInit,PyAttributeOutsideInit,PyAttributeOutsideInit,PyAttributeOutsideInit,PyAttributeOutsideInit,PyAttributeOutsideInit,PyAttributeOutsideInit,PyAttributeOutsideInit,PyAttributeOutsideInit,PyAttributeOutsideInit,PyAttributeOutsideInit,PyAttributeOutsideInit,PyAttributeOutsideInit,PyAttributeOutsideInit,PyAttributeOutsideInit,PyAttributeOutsideInit,PyUnresolvedReferences,PyUnresolvedReferences,PyUnresolvedReferences,PyUnresolvedReferences
class Plugin(indigo.PluginBase):
####-------------------------------------------------------------------------####
	def __init__(self, pluginId, pluginDisplayName, pluginVersion, pluginPrefs):
		indigo.PluginBase.__init__(self, pluginId, pluginDisplayName, pluginVersion, pluginPrefs)

		self.pluginShortName 			= "piBeacon"

		self.quitNow					= ""
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

		self.MAChome					= os.path.expanduser(u"~")
		self.userIndigoDir				= self.MAChome + "/indigo/"
		self.indigoPreferencesPluginDir = self.getInstallFolderPath+"Preferences/Plugins/"+self.pluginId+"/"
		self.indigoPluginDirOld			= self.userIndigoDir + self.pluginShortName+"/"
		self.PluginLogFile				= indigo.server.getLogsFolderPath(pluginId=self.pluginId) +"/plugin.log"


		formats=	{   logging.THREADDEBUG: "%(asctime)s %(msg)s",
						logging.DEBUG:       "%(asctime)s %(msg)s",
						logging.INFO:        "%(asctime)s %(msg)s",
						logging.WARNING:     "%(asctime)s %(msg)s",
						logging.ERROR:       "%(asctime)s.%(msecs)03d\t%(levelname)-12s\t%(name)s.%(funcName)-25s %(msg)s",
						logging.CRITICAL:    "%(asctime)s.%(msecs)03d\t%(levelname)-12s\t%(name)s.%(funcName)-25s %(msg)s" }

		date_Format = { logging.THREADDEBUG: "%Y-%m-%d %H:%M:%S",
						logging.DEBUG:       "%Y-%m-%d %H:%M:%S",
						logging.INFO:        "%Y-%m-%d %H:%M:%S",
						logging.WARNING:     "%Y-%m-%d %H:%M:%S",
						logging.ERROR:       "%Y-%m-%d %H:%M:%S",
						logging.CRITICAL:    "%Y-%m-%d %H:%M:%S" }
		formatter = LevelFormatter(fmt="%(msg)s", datefmt="%Y-%m-%d %H:%M:%S", level_fmts=formats, level_date=date_Format)

		self.plugin_file_handler.setFormatter(formatter)
		self.indiLOG = logging.getLogger("Plugin")  
		self.indiLOG.setLevel(logging.THREADDEBUG)

		self.indigo_log_handler.setLevel(logging.WARNING)
		indigo.server.log("initializing	 ... ")

		indigo.server.log(  u"path To files:          =================")
		indigo.server.log(  u"indigo                  {}".format(self.indigoRootPath))
		indigo.server.log(  u"installFolder           {}".format(self.indigoPath))
		indigo.server.log(  u"plugin.py               {}".format(self.pathToPlugin))
		indigo.server.log(  u"Plugin params           {}".format(self.indigoPreferencesPluginDir))

		self.indiLOG.log( 0, "!!!!INFO ONLY!!!!  logger  enabled for   0             !!!!INFO ONLY!!!!")
		self.indiLOG.log( 5, "!!!!INFO ONLY!!!!  logger  enabled for   THREADDEBUG   !!!!INFO ONLY!!!!")
		self.indiLOG.log(10, "!!!!INFO ONLY!!!!  logger  enabled for   DEBUG         !!!!INFO ONLY!!!!")
		self.indiLOG.log(20, "!!!!INFO ONLY!!!!  logger  enabled for   INFO          !!!!INFO ONLY!!!!")
		self.indiLOG.log(30, "!!!!INFO ONLY!!!!  logger  enabled for   WARNING       !!!!INFO ONLY!!!!")
		self.indiLOG.log(40, "!!!!INFO ONLY!!!!  logger  enabled for   ERROR         !!!!INFO ONLY!!!!")
		self.indiLOG.log(50, "!!!!INFO ONLY!!!!  logger  enabled for   CRITICAL      !!!!INFO ONLY!!!!")

		indigo.server.log(  u"check                   {}  <<<<    for detailed logging".format(self.PluginLogFile))
		indigo.server.log(  u"Plugin short Name       {}".format(self.pluginShortName))
		indigo.server.log(  u"my PID                  {}".format(self.myPID))	 
		indigo.server.log(  u"set params for indigo V {}".format(self.indigoVersion))	 

####-------------------------------------------------------------------------####
	def __del__(self):
		indigo.PluginBase.__del__(self)

	###########################		INIT	## START ########################

####-------------------------------------------------------------------------####
	def startup(self):
		try:
			if self.pathToPlugin.find("/"+self.pluginName+".indigoPlugin/")==-1:
				self.errorLog(u"---------------------------------------------------------------------------------------------------------------" )
				self.errorLog(u"---------------------------------------------------------------------------------------------------------------" )
				self.errorLog(u"---------------------------------------------------------------------------------------------------------------" )
				self.errorLog(u"---------------------------------------------------------------------------------------------------------------" )
				self.errorLog(u"---------------------------------------------------------------------------------------------------------------" )
				self.errorLog(u"---------------------------------------------------------------------------------------------------------------" )
				self.errorLog(u"---------------------------------------------------------------------------------------------------------------" )
				self.errorLog(u"---------------------------------------------------------------------------------------------------------------" )
				self.errorLog(u"The pluginname is not correct, please reinstall or rename")
				self.errorLog(u"It should be   /Libray/....../Plugins/"+self.pluginName+".indigPlugin")
				p=max(0,self.pathToPlugin.find("/Contents/Server"))
				self.errorLog(u"It is: "+self.pathToPlugin[:p])
				self.errorLog(u"please check your download folder, delete old *.indigoPlugin files or this will happen again during next update")
				self.errorLog(u"---------------------------------------------------------------------------------------------------------------" )
				self.errorLog(u"---------------------------------------------------------------------------------------------------------------" )
				self.errorLog(u"---------------------------------------------------------------------------------------------------------------" )
				self.errorLog(u"---------------------------------------------------------------------------------------------------------------" )
				self.errorLog(u"---------------------------------------------------------------------------------------------------------------" )
				self.errorLog(u"---------------------------------------------------------------------------------------------------------------" )
				self.errorLog(u"---------------------------------------------------------------------------------------------------------------" )
				self.sleep(100000)
				self.quitNOW="wromg plugin name"
				return

			if not self.checkPluginPath(self.pluginName,  self.pathToPlugin):
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

			self.myLog( text = " --V {}   initializing  -- ".format(self.pluginVersion), destination="standard")

			self.setupBasicFiles()

			self.startupFIXES0()

			self.getFolderIdOfBeacons()

			self.deleteAndCeateVariables(False)

			self.initCARS()

			self.readConfig()

			self.initMac2Vendor()

			self.startupFIXES1()

			self.resetMinMaxSensors(init=True)

			self.statusChanged = 0

			self.setGroupStatus(init=True)		  

			self.checkPiEnabled()

			if self.userIdOfServer !="": 
				cmd = "echo '"+self.passwordOfServer+ "' | sudo -S /usr/bin/xattr -rd com.apple.quarantine '"+self.pathToPlugin+"pngquant'"
				ret = subprocess.Popen(cmd,shell=True,stdout=subprocess.PIPE,stderr=subprocess.PIPE).communicate()
				if self.decideMyLog(u"Logic"): self.indiLOG.log(20,"setting attribute for catalina  with:  {}".format(cmd))
				if self.decideMyLog(u"Logic"): self.indiLOG.log(20," ......... result:{}".format(ret))

			self.setSqlLoggerIgnoreStatesAndVariables()
	  
 			self.indiLOG.log(10, "startup(self): setting variables, debug ..   finished ")

		except Exception, e:
			self.indiLOG.log(50,u"--------------------------------------------------------------------------------------------------------------")
			self.indiLOG.log(50,u"Line {} has error={}".format(sys.exc_traceback.tb_lineno, e))
			self.indiLOG.log(50,u"Error in startup of plugin, waiting for 2000 secs then restarting plugin")
			self.indiLOG.log(50,u"--------------------------------------------------------------------------------------------------------------")
			self.sleep(2000)
			exit(1)
		return


	####-----------------	 ---------
	def setSqlLoggerIgnoreStatesAndVariables(self):
		try:
#_sqlLoggerIgnoreStates = {"beacon":	"Pi_0_Time,Pi_1_Time,Pi_2_Time,Pi_3_Time,Pi_4_Time,Pi_5_Time,Pi_6_Time,Pi_7_Time,Pi_8_Time,Pi_9_Time,Pi_10_Time,Pi_11_Time,Pi_12_Time,Pi_13_Time,Pi_14_Time,Pi_15_Time,TxPowerReceived,UUID,closestRPIText,displayStatus,status,batteryLevelLastUpdate,pktInfo"
#				         ,"rPI":		"Pi_0_Time,Pi_1_Time,Pi_2_Time,Pi_3_Time,Pi_4_Time,Pi_5_Time,Pi_6_Time,Pi_7_Time,Pi_8_Time,Pi_9_Time,Pi_10_Time,Pi_11_Time,Pi_12_Time,Pi_13_Time,Pi_14_Time,Pi_15_Time,TxPowerReceived,UUID,closestRPIText,displayStatus,status,batteryLevelLastUpdate,pktInfo,online,i2cactive"
#				         ,"rPI-Sensor":	",displayStatus,status"
#						 ,"BLEconnect":	"Pi_0_Time,Pi_1_Time,Pi_2_Time,Pi_3_Time,Pi_4_Time,Pi_5_Time,Pi_6_Time,Pi_7_Time,Pi_8_Time,Pi_9_Time,Pi_10_Time,Pi_11_Time,Pi_12_Time,Pi_13_Time,Pi_14_Time,Pi_15_Time,TxPowerReceived,closestRPIText,displayStatus,status"
#				         ,"sensor":		"displayStatus,status"}
			if self.indigoVersion <  7.4:                             return 
			if self.indigoVersion == 7.4 and self.indigoRelease == 0: return 
			#tt = ["beacon",              "rPI","rPI-Sensor","BLEconnect","sensor"]

			outOND  = ""
			outOffD = ""
			outONV  = ""
			outOffV = ""
			if self.decideMyLog(u"SQLSuppresslog"): self.indiLOG.log(20,"setSqlLoggerIgnoreStatesAndVariables settings:{} ".format( self.SQLLoggingEnable) )
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
						#if self.decideMyLog(u"SQLSuppresslog"): self.indiLOG.log(20,"\n1 dev: {} current sharedProps: testing for off \n{}".format(dev.name.encode("utf8"), unicode(sp).replace("\n","")) )
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
						var = indigo.variables[v]
						sp = var.sharedProps
						if "sqlLoggerIgnoreChanges" not in sp  or sp["sqlLoggerIgnoreChanges"] != "true": 
							continue
						outONV += var.name+"; "
						sp["sqlLoggerIgnoreChanges"] = ""
						var.replaceSharedPropsOnServer(sp)
					except: pass

			if self.decideMyLog(u"SQLSuppresslog"): 
				self.indiLOG.log(20," \n\n")
				if outOffD !="":
					self.indiLOG.log(20," switching off SQL logging for special devtypes/states:\n{}\n for devices:\n>>>{}<<<".format(json.dumps(_sqlLoggerIgnoreStates, sort_keys=True, indent=2), outOffD.encode("utf8")) )

				if outOND !="":
					self.indiLOG.log(20," switching ON SQL logging for special states for devices: {}".format(outOND.encode("utf8")) )

				if outOffV !="":
					self.indiLOG.log(20," switching off SQL logging for variables :{}".format(outOffV.encode("utf8")) )

				if outONV !="":
					self.indiLOG.log(20," switching ON SQL logging for variables :{}".format(outONV.encode("utf8")) )
				self.indiLOG.log(20,"setSqlLoggerIgnoreStatesAndVariables settings end\n")



		except Exception, e:
			self.indiLOG.log(40,u"Line {} has error={}".format(sys.exc_traceback.tb_lineno, e))
		return 

	####-----------------	 ---------
	def initMac2Vendor(self):
		self.waitForMAC2vendor = False
		self.enableMACtoVENDORlookup	= int(self.pluginPrefs.get(u"enableMACtoVENDORlookup","21"))
		if self.enableMACtoVENDORlookup != "0":
			self.M2V =  M2Vclass.MAP2Vendor( pathToMACFiles=self.indigoPreferencesPluginDir+"mac2Vendor/", refreshFromIeeAfterDays = self.enableMACtoVENDORlookup, myLogger = self.indiLOG.log )
			self.waitForMAC2vendor = self.M2V.makeFinalTable()

	####-----------------	 ---------
	def getVendortName(self,MAC):
		if self.enableMACtoVENDORlookup !="0" and not self.waitForMAC2vendor:
			self.waitForMAC2vendor = self.M2V.makeFinalTable()

		return self.M2V.getVendorOfMAC(MAC)


####-------------------------------------------------------------------------####
	def setCurrentlyBooting(self, addTime, setBy=""):
		try:	self.currentlyBooting = time.time() + addTime
		except: self.errorLog("setCurrentlyBooting:  setting BeaconsCheck,  bad number requested {}, called from: {} ".format(addTime, setBy))
		try:
			self.indiLOG.log(20,"setting BeaconsCheck to off (no up-->down) for {:3d} secs requested by: {} ".format(addTime, setBy))
		except:
			indigo.server.log(  "setting BeaconsCheck to off (no up-->down) for {:3d} secs requested by: {} ".format(addTime, setBy))
		return 


####-------------------------------------------------------------------------####
	def initFileDir(self):



			if not os.path.exists(self.indigoPreferencesPluginDir):
				os.mkdir(self.indigoPreferencesPluginDir)
			if not os.path.exists(self.indigoPreferencesPluginDir):
				self.indiLOG.log(50,u"error creating the plugin data dir did not work, can not create: {}".format(self.indigoPreferencesPluginDir)  )
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

				except Exception, e:
						self.indiLOG.log(40,"Line {} has error={}".format(sys.exc_traceback.tb_lineno, e))
		except Exception, e:
				self.indiLOG.log(40,"Line {} has error={}".format(sys.exc_traceback.tb_lineno, e))
		return
		

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
						for piU in _rpiBeaconList:
							try: 
								if len(dev.states[u"Pi_"+piU.rjust(2,"0")+"_Time"]) < 5 or dev.states[u"Pi_"+piU.rjust(2,"0")+u"_Time"] is None :
									if unicode(dev.states[u"Pi_"+piU.rjust(2,"0")+u"_Signal"]) == "0":
										self.addToStatesUpdateDict(dev.id,u"Pi_"+piU.rjust(2,"0")+u"_Signal",-999)
							except:
								if not self.RPIVersion20:
									self.indiLOG.log(30, u"{}  error pi#: {}, state missing ignored/disabled device?".format(dev.name.encode("utf8"), piU) )
								continue
							
						self.executeUpdateStatesDict(calledFrom="startupFIXES1")

					if dev.deviceTypeId.lower() == u"rpi" and "note" in dev.states:
						piString = dev.states["note"].split("-")
						if len(piString) == 2:
							piU = piString[1]
							for xyz in ["PosX","PosY","PosZ"]:
								self.RPI[piU][xyz] = dev.states[xyz]

					upd = False
					props = dev.pluginProps
					#if u"SupportsBatteryLevel" in props:
					#	props[u"SupportsBatteryLevel"] = False
					#s	upd = True

					if u"addNewOneWireSensors" in props:   # reset accept new one wire devices
						props[u"addNewOneWireSensors"] = "0"
						upd = True


					if "lastSensorChange" in dev.states:
						if len(dev.states["lastSensorChange"]) < 5:
							dev.updateStateOnServer(u"lastSensorChange",dateString)

					if dev.deviceTypeId == u"BLEconnect":
						props[u"isBLEconnectDevice"] = True

					if dev.deviceTypeId in _GlobalConst_allowedSensors:
						props[u"isSensorDevice"] = True
						upd = True

					if dev.deviceTypeId in _GlobalConst_allowedOUTPUT:
						props[u"isOutputDevice"] = True
						upd = True

					if (dev.deviceTypeId.lower()) =="rpi":
						props[u"isRPIDevice"] = True
						props[u"typeOfBeacon"] = u"rPI"
						upd = True
						if props[u"address"] in self.beacons:
							self.beacons[props[u"address"]][u"typeOfBeacon"] = u"rPI"

					if dev.deviceTypeId =="rPI-Sensor":
						props[u"isRPISensorDevice"] = True
						upd = True

					if dev.deviceTypeId =="beacon":
						props[u"isBeaconDevice"] = True
						upd = True

					if dev.deviceTypeId =="car":
						props[u"isCARDevice"] = True
						upd = True

					if upd:
						self.deviceStopCommIgnore = time.time()
						dev.replacePluginPropsOnServer(props)

				self.writeJson(self.RPI, fName=self.indigoPreferencesPluginDir + u"RPIconf", fmtOn=self.RPIFileSort)

			except Exception, e:
				self.indiLOG.log(40,"Line {} has error={}".format(sys.exc_traceback.tb_lineno, e))
			try:
				os.remove(self.indigoPreferencesPluginDir + "config")
			except:
				pass


			self.indiLOG.log(10, u" ..   checking devices tables" )

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
							dev.updateStateOnServer("note","Pi-"+dev.address)
					else:
						if dev.description.find("Pi-"):
							nn = dev.states["note"].split("-")
							if len(nn) == 3:
								dev.updateStateOnServer("note","Pi-"+nn[1])


	######## fix  address vendors ..
			for dev in indigo.devices.iter(self.pluginId):
				props = dev.pluginProps

				if dev.deviceTypeId == u"rPi" or dev.deviceTypeId == u"beacon":
					self.freezeAddRemove = False

					try:
						beacon = props[u"address"]
					except:
						self.indiLOG.log(40, "device has no address: " + dev.name.encode("utf8") + u" " + unicode(dev.id) +
							unicode(props) + u" " + unicode(dev.globalProps) + u" please delete and let the plugin create the devices")
						continue

					if beacon not in self.beacons:
						self.beacons[beacon]			 = copy.deepcopy(_GlobalConst_emptyBeacon)
						self.beacons[beacon][u"indigoId"] = dev.id
						self.beacons[beacon][u"created"]  = dev.states[u"created"]

					if "vendorName" in dev.states and  len(dev.states["vendorName"]) == 0:
						vname = self.getVendortName(beacon)
						if vname !="" and  vname != dev.states["vendorName"]:
							dev.updateStateOnServer( "vendorName", vname)


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
						self.deviceStopCommIgnore = time.time()
						dev.replacePluginPropsOnServer(props)
					###indigo.server.log(dev.name+" "+unicode(props))

				if dev.deviceTypeId.find(u"OUTPUTi2cRelay") > -1:
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
						self.deviceStopCommIgnore = time.time()
						dev.replacePluginPropsOnServer(props)
					###indigo.server.log(dev.name+" "+unicode(props))


				if "description" in props: 
					props["description"] =""
					self.deviceStopCommIgnore = time.time()
					dev.replacePluginPropsOnServer(props)



		except Exception, e:
			self.indiLOG.log(50,u"--------------------------------------------------------------------------------------------------------------")
			self.indiLOG.log(50,u"Error in startup of plugin, waiting for 2000 secs then restarting plugin")
			self.indiLOG.log(50,u"Line {} has error={}".format(sys.exc_traceback.tb_lineno, e))
			self.indiLOG.log(50,u"--------------------------------------------------------------------------------------------------------------")
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
							indigoId = self.beacons[beacon][u"indigoId"]
							if indogoId >0:
								dev= indigo.devices[self.beacons[beacon][u"indigoId"]]
								self.updateCARS(beacon,dev,dev.states,force=True)
						except: pass

			except:
				pass
###-------------------------------------------------------------------------####
	def fixBeaconPILength(self,mac, area):
		try:
			if mac not in self.beacons: return 
			lx = len(self.beacons[mac][area]) 
			if lx < _rpiBeaconList:
				for ll in range(lx,len(_rpiBeaconList)):
					self.beacons[mac][area].append({"distance": 99999,"lastSignal": 0, "rssi": -999})

		except Exception, e: 
			if len(unicode(e)) > 5 :
				self.indiLOG.log(40,"Line {} has error={}".format(sys.exc_traceback.tb_lineno, e))



####-------------------------------------------------------------------------####
	def setupBasicFiles(self):
		try:

			if not os.path.exists(self.indigoPreferencesPluginDir + u"all"):
				os.mkdir(self.indigoPreferencesPluginDir + u"all")
			if not os.path.exists(self.indigoPreferencesPluginDir + u"rejected"):
				os.mkdir(self.indigoPreferencesPluginDir + u"rejected")
				subprocess.call(u" mv '" + self.indigoPreferencesPluginDir + u"reject*' '" + self.indigoPreferencesPluginDir + u"rejected'", shell=True)
			if not os.path.exists(self.indigoPreferencesPluginDir + u"interfaceFiles"):
				os.mkdir(self.indigoPreferencesPluginDir + u"interfaceFiles")
				subprocess.call(u"rm '" + self.indigoPreferencesPluginDir + u"param*'", shell=True)
				subprocess.call(u"rm '" + self.indigoPreferencesPluginDir + u"interfa*'", shell=True)
				subprocess.call(u"rm '" + self.indigoPreferencesPluginDir + u"wpa_supplicant'*", shell=True)
			if not os.path.exists(self.indigoPreferencesPluginDir + u"soundFiles"):
				os.mkdir(self.indigoPreferencesPluginDir + u"soundFiles")
			if not os.path.exists(self.indigoPreferencesPluginDir + u"displayFiles"):
				os.mkdir(self.indigoPreferencesPluginDir + u"displayFiles")
			if not os.path.exists(self.cameraImagesDir):
				os.mkdir(self.cameraImagesDir)

		except Exception, e:
			self.indiLOG.log(50,u"--------------------------------------------------------------------------------------------------------------")
			self.indiLOG.log(50,u"Line {} has error={}".format(sys.exc_traceback.tb_lineno, e) )
			self.indiLOG.log(50,u"Error in startup of plugin, waiting for 2000 secs then restarting plugin")
			self.indiLOG.log(50,u"--------------------------------------------------------------------------------------------------------------")
			self.sleep(2000)
			exit(1)
		return



####-------------------------------------------------------------------------####
	def getDebugLevels(self):
		try:
			self.debugLevel			= []
			for d in _debugAreas:
				if self.pluginPrefs.get(u"debug"+d, False): self.debugLevel.append(d)


			try: self.debugRPI			 = int(self.pluginPrefs.get(u"debugRPI", -1))
			except: self.debugRPI=-1
		except Exception, e:
			self.indiLOG.log(50,u"--------------------------------------------------------------------------------------------------------------")
			self.indiLOG.log(50,u"Line {} has error={}".format(sys.exc_traceback.tb_lineno, e) )
			self.indiLOG.log(50,u"Error in startup of plugin, plugin prefs are wrong ")
			self.indiLOG.log(50,u"--------------------------------------------------------------------------------------------------------------")
		return




####-------------------------------------------------------------------------####
	def setVariables(self):
		try:
			self.deviceStopCommIgnore 		= 0
			self.cameraImagesDir			= self.indigoPreferencesPluginDir+"cameraImages/"

			self.setLogfile(self.pluginPrefs.get("logFileActive2", "standard"))

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
			self.checkBatteryLevelHours		= [4,12,20] # which hour to check battery levels
			self.lastUPtoDown				= time.time() + 35
			self.lastsetupFilesForPi 		= time.time()
			self.checkIPSendSocketOk		= {}
			self.actionList					= {"setTime":[],"setSqlLoggerIgnoreStatesAndVariables":False}
			self.updateStatesDict			= {}
			self.executeUpdateStatesDictActive = ""

			self.rpiQueues					= {}
			self.rpiQueues["reset"]			= {}
			self.rpiQueues["data"]			= {}
			self.rpiQueues["state"]			= {}
			self.rpiQueues["lastActive"]	= {}
			self.rpiQueues["lastCheck"]		= {}
			self.rpiQueues["thread"] 		= {}
			self.rpiQueues["lastData"] 		= {}
			self.RPIBusy					= {}
			for ii in range(_GlobalConst_numberOfRPI):
				iiU = unicode(ii)
				self.rpiQueues["reset"][iiU] 		= False
				self.rpiQueues["data"][iiU]			= Queue.Queue()
				self.rpiQueues["state"][iiU]		= ""
				self.rpiQueues["lastActive"][iiU]	= time.time() - 900000
				self.rpiQueues["lastCheck"][iiU]	= time.time() - 900000
				self.rpiQueues["lastData"][iiU]		= ""
				self.RPIBusy[iiU]					= 0


			self.newBeaconsLogTimer			= 0
			self.selectBeaconsLogTimer		= {}

			self.RPI						= {}
			self.beacons					= {}

			self.PasswordsAreSet			= 0
			self.indigoCommand				= ""
			self.countLoop					= 0
			self.selectedPiServer			= 0
			self.statusChanged				= 0

			self.maxParseSec				= "1.0"
			self.newIgnoreMAC				= 0
			self.lastUpdateSend				= time.time()
			self.rejectedByPi				= {}
			self.sendInitialValue			= "" # will be dev.id if output should be send 

			self.beaconsIgnoreUUID			= {}
			self.updatePiBeaconNote			= {}
			self.updateNeeded				= ""
			self.updateNeededTimeOut		= 9999999999999999999999999999		  
			self.devUpdateList				= {}



			self.enableFING					= "0"
			self.timeErrorCount				= [0 for ii in _rpiList]
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
				self.setClostestRPItextToBlank= self.pluginPrefs.get(u"setClostestRPItextToBlank","1") !="1"
			except:
				self.setClostestRPItextToBlank= False

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
			if 	self.pressureUnits			== u"mbar": self.pressureUnits = u"mBar"
 
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
				self.expectTimeout			= self.pluginPrefs.get(u"expectTimeout", u"20")
			except:
				self.expectTimeout			= "20"


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
			eth0							= '{"on":"dontChange",	"useIP":"use"}'
			wlan0							= '{"on":"dontChange",	"useIP":"useIf"}'
			try: 
				self.wifiEth				= {"eth0":json.loads(self.pluginPrefs.get(u"eth0", eth0)), "wlan0":json.loads(self.pluginPrefs.get(u"wlan0", wlan0))}
			except: self.wifiEth			= {"eth0":json.loads(eth0),"wlan0":json.loads(wlan0)}

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
			self.trackRPImessages			= -1
			self.pythonPath					= u"/usr/bin/python2.6"
			if os.path.isfile(u"/usr/bin/python2.7"):
				self.pythonPath				= u"/usr/bin/python2.7"
			elif os.path.isfile(u"/usr/bin/python2.6"):
				self.pythonPath				= u"/usr/bin/python2.6"


			self.trackSignalStrengthIfGeaterThan = [99999.,"i"]
			self.trackSignalChangeOfRPI			 = False

			self.beaconPositionsUpdated			= 0

			self.lastFixConfig = 0

			self.pluginPrefs["wifiOFF"] = ""


			############ plot beacon positions 
			try:	self.beaconPositionsUpdateTime					= float(self.pluginPrefs.get(u"beaconPositionsUpdateTime", -1))
			except: self.beaconPositionsUpdateTime					= -1.
			try:	self.beaconPositionsdeltaDistanceMinForImage	= float(self.pluginPrefs.get(u"beaconPositionsdeltaDistanceMinForImage",	 1.))
			except: self.beaconPositionsdeltaDistanceMinForImage	= 1.

			self.beaconPositionsData								= {u"mac":{}}
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


			self.varExcludeSQLList = [ "pi_IN_"+str(ii) for ii in _rpiList]
			self.varExcludeSQLList.append(self.ibeaconNameDefault+"With_ClosestRPI_Change")
			self.varExcludeSQLList.append(self.ibeaconNameDefault+"Rebooting")
			self.varExcludeSQLList.append(self.ibeaconNameDefault+"With_Status_Change")
			for group in _GlobalConst_groupList:
				for tType in [u"Home", u"Away"]:
					self.varExcludeSQLList.append(self.groupCountNameDefault+group+"_"+tType)

			self.checkBeaconParametersDisabled						= self.pluginPrefs.get(u"checkBeaconParametersDisabled", False )


		except Exception, e:
			self.indiLOG.log(50,u"--------------------------------------------------------------------------------------------------------------")
			self.indiLOG.log(50,u"Line {} has error={}".format(sys.exc_traceback.tb_lineno, e))
			self.indiLOG.log(50,u"Error in startup of plugin, waiting for 2000 secs then restarting plugin")
			self.indiLOG.log(50,u"--------------------------------------------------------------------------------------------------------------")
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
								triggerGroup[group][u"oneHome"]			= True
								self.groupStatusList[group][u"oneHome"]	= u"1"
							self.groupStatusList[group][u"nHome"]		+=1
						else:
							if self.groupStatusList[group][u"oneAway"] ==u"0":
								triggerGroup[group][u"oneAway"]			= True
							self.groupStatusList[group][u"oneAway"]		= u"1"
							self.groupStatusList[group][u"nAway"]		+=1
 
 


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


			if	init != u"init" and len(self.triggerList) > 0:
				for group in triggerGroup:
					for tType in triggerGroup[group]:
						if triggerGroup[group][tType]:
							self.triggerEvent(group+"-"+tType)

		except Exception, e:
			if len(unicode(e)) > 5 :
				self.indiLOG.log(40,"Line {} has error={}".format(sys.exc_traceback.tb_lineno, e))


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
			#self.indiLOG.log(10, u"triggerEvent: %s suppressed due to reboot" % eventId)
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
			try:		indigo.variable.delete(self.ibeaconNameDefault+u"Rebooting")
			except:		pass
			for dev in indigo.devices.iter("props.isSensorDevice"):
				if dev.deviceTypeId ==  "lidar360": 
					try:	indigo.variable.delete((dev.name+"_data").replace(" ","_"))
					except:	pass 

		try:			indigo.variable.create(u"pi_IN_Alive", u"", piFolder)
		except:			pass
		try:			indigo.variable.create(self.ibeaconNameDefault+u"With_Status_Change", u"", piFolder)
		except:			pass
		try:			indigo.variable.create(self.ibeaconNameDefault+u"With_ClosestRPI_Change", u"", piFolder)
		except:			pass
		try:			indigo.variable.create(self.ibeaconNameDefault+u"Rebooting", u"", piFolder)
		except:			pass
		for dev in indigo.devices.iter("props.isSensorDevice"):
			if dev.deviceTypeId ==  "lidar360": 
				try:	
						indigo.variable.create((dev.name+"_data").replace(" ","_"), u"", piFolder)
				except: pass
				try:	
						indigo.variable.create((dev.name+"_calibrated").replace(" ","_"), u"", piFolder)
				except: pass


		for piU in self.RPI:
			if delete:
				try:
					indigo.variable.delete(u"pi_IN_{}".format(piU) )
				except:
					pass
			try:
				indigo.variable.create(u"pi_IN_{}".format(piU), u"", piFolder)
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
			if os.path.isfile(self.indigoPreferencesPluginDir + "dataStats"):
				f = open(self.indigoPreferencesPluginDir + "dataStats", u"r")
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
			if u"updates" not in self.dataStats:
				self.resetDataStats()
				return
			if u"nstates" not in self.dataStats[u"updates"]:
				self.resetDataStats()
				return
		except Exception, e:
			self.resetDataStats() 
			self.indiLOG.log(40,"Line {} has error={}".format(sys.exc_traceback.tb_lineno, e))
		if u"data" not in self.dataStats:
			self.resetDataStats() 

####-------------------------------------------------------------------------####
	def resetDataStats(self):
		self.dataStats={u"startTime": time.time(),"data":{},"updates":{u"devs":0,"states":0,"startTime": time.time(),"nstates":[0 for ii in range(11)]}}
		self.saveTcpipSocketStats()

####-------------------------------------------------------------------------####
	def saveTcpipSocketStats(self):
		self.writeJson(self.dataStats, fName=self.indigoPreferencesPluginDir + u"dataStats", fmtOn=True )


####------================----------- CARS ------================-----------
####-------------------------------------------------------------------------####
	def saveCARS(self,force=False):
		if force: self.cleanupDeepCARS()
		self.writeJson(self.CARS,fName=self.indigoPreferencesPluginDir + u"CARS" )

####-------------------------------------------------------------------------####
	def readCARS(self):
		try:
			f = open(self.indigoPreferencesPluginDir + "CARS", u"r")
			self.CARS = json.loads(f.read())
			f.close()
		except:
			self.sleep(1)
			try:
				f = open(self.indigoPreferencesPluginDir + "CARS", u"r")
				self.CARS = json.loads(f.read())
				f.close()
			except Exception, e:
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
					self.indiLOG.log(40,"Line {} has error={}".format(sys.exc_traceback.tb_lineno, e))
					if unicode(e).find(u"timeout waiting") > -1:
						self.indiLOG.log(40, u"communication to indigo is interrupted")
						return
					self.indiLOG.log(40, u"devId {} not defined in devices  removing from	 CARS:".format(carIds,unicode(self.CARS)) )
					delDD.append(carIds)
				if u"homeSince"	not in self.CARS[u"carId"][carIds]:	 self.CARS[u"carId"][carIds][u"homeSince"] = 0
				if u"awaySince"	not in self.CARS[u"carId"][carIds]:	 self.CARS[u"carId"][carIds][u"awaySince"] = 0
				if u"beacons"	not in self.CARS[u"carId"][carIds]:	 self.CARS[u"carId"][carIds][u"beacons"]   = {}
			for carIds in delDD:
				del self.CARS[u"carId"][carIds]

		except Exception, e:
			self.indiLOG.log(40,"Line {} has error={}".format(sys.exc_traceback.tb_lineno, e))


####-------------------------------------------------------------------------####
	def updateAllCARbeacons(self,indigoCarIds,force=False):
		try:
				beacon = ""
				if self.decideMyLog(u"CAR"): self.indiLOG.log(10, u"updateAllCARbeacons	 CARS:" + unicode(self.CARS))
				for beacon in self.CARS[u"beacon"]:
					if indigoCarIds	 !=	 unicode(self.CARS[u"beacon"][beacon][u"carId"]) and not force: continue
					beaconDevId = self.beacons[beacon][u"indigoId"]
					beaconDev	= indigo.devices[beaconDevId]
					if self.decideMyLog(u"CAR"): self.indiLOG.log(10, u"updating all cars")
					self.updateCARS(beacon,beaconDev,beaconDev.states, force=True)
					break

		except Exception, e:
			self.indiLOG.log(40,"Line {} has error={}".format(sys.exc_traceback.tb_lineno, e))
			self.indiLOG.log(40,u"beacon       {}".format(beacon) )
			self.indiLOG.log(40,u"indigoCarIds {}".format(indigoCarIds) )

####-------------------------------------------------------------------------####
	def updateCARS(self,beacon,beaconDev,beaconNewStates,force=False):
		try:
			if beacon not in self.CARS[u"beacon"]: return
			if len(beacon) < 10: return
			indigoCarIds = unicode(self.CARS[u"beacon"][beacon][u"carId"])
			if indigoCarIds not in self.CARS[u"carId"]: # pointer to indigo ID
				self.indiLOG.log(10, u"{} beacon: not found in CARS[carId], removing from dict;  CARSdict: {}".format(beacon, unicode(self.CARS)) )
				del self.CARS[u"beacon"][beacon]
				return
			indigoIDofBeacon = beaconDev.id
			carDev			 = indigo.devices[int(indigoCarIds)]
			props			 = carDev.pluginProps
			carName			 = carDev.name
			if beaconDev.states[u"status"] == beaconNewStates[u"status"] and not force:
				if self.decideMyLog(u"CAR"): self.indiLOG.log(10, "updateCARS:    {}   {}  no change".format(carName, beacon))
				return

				 
			try:	whatForStatus = carDev.pluginProps[u"displayS"]	 
			except: whatForStatus = ""
			if whatForStatus ==u"": whatForStatus="location" 

			oldCarStatus	= carDev.states[u"location"]
			oldCarEngine	= carDev.states[u"engine"]
			oldCarMotion	= carDev.states[u"motion"]
			oldBeaconStatus	= beaconDev.states[u"status"]
			newBeaconStatus	= beaconNewStates[u"status"]
			beaconType		= self.CARS[u"beacon"][beacon][u"beaconType"]
			beaconBattery	= 0
			beaconUSB		= 0
			beaconKey		= 2
			nKeysFound		= 0
			oldAwaySince = self.CARS[u"carId"][indigoCarIds][u"awaySince"] 
			oldHomeSince = self.CARS[u"carId"][indigoCarIds][u"homeSince"] 
			if self.decideMyLog(u"CAR"): self.indiLOG.log(10,"{}-{}  {} updating {}, oldBeaconStatus={}, newBeaconStatus={}  oldAwaySince:{}  oldHomeSince:{}, oldCarStatus={}, oldCarEngine={}, oldCarMotion={}".format(carName, indigoCarIds, beacon, beaconType, oldBeaconStatus, newBeaconStatus, unicode(time.time()-oldAwaySince), unicode(time.time()-oldHomeSince), oldCarStatus, oldCarEngine, oldCarMotion) ) 

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
				if self.decideMyLog(u"CAR"): self.indiLOG.log(10, "{}-{} testing dev={}  st=".format(carName, indigoCarIds, indigoDEV.name, st) ) 

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
				props[u"address"] = u"away"
				updateProps=True
			if (beaconBattery==2 or beaconUSB==2 or beaconKey==2) and props[u"address"] == u"away":
				props[u"address"] = u"home"
				updateProps=True
			elif not (beaconBattery==2 or beaconUSB==2 or beaconKey==2) and props[u"address"] == u"home":
				props[u"address"] = u"away" 
				updateProps=True

			self.addToStatesUpdateDict(indigoCarIds,"motion",carDev.states[u"motion"])

			if	 beaconUSB==2: 
				self.addToStatesUpdateDict(indigoCarIds,"engine", u"on")
			elif beaconUSB==1:
				self.addToStatesUpdateDict(indigoCarIds,"engine", u"off")

			if not (beaconBattery==2 or beaconUSB==2 or beaconKey==2):	# nothing on = gone , away ..
				self.addToStatesUpdateDict(indigoCarIds, u"location", u"away")
				if oldCarStatus != u"away": 
					self.setIcon(carDev,props, u"SensorOff-SensorOn",0)
					self.CARS[u"carId"][indigoCarIds][u"awaySince"] = time.time()
					self.addToStatesUpdateDict(indigoCarIds,"LastLeaveFromHome",datetime.datetime.now().strftime(_defaultDateStampFormat))
				self.addToStatesUpdateDict(indigoCarIds, u"motion", u"left")
				self.addToStatesUpdateDict(indigoCarIds, u"engine", u"unknown")
				self.checkCarsNeed[indigoCarIds]= 0

			else:	  # something on, we are home.
				if self.decideMyLog(u"CAR"): self.indiLOG.log(10, "{} - setting to be home,   oldCarStatus: {}".format(carName ,oldCarStatus) )
				self.addToStatesUpdateDict(indigoCarIds, u"location", u"home")
				if oldCarStatus != u"home": 
					self.CARS[u"carId"][indigoCarIds][u"homeSince"] = time.time()
					self.addToStatesUpdateDict(indigoCarIds, u"LastArrivalAtHome",datetime.datetime.now().strftime(_defaultDateStampFormat))



			if self.decideMyLog(u"CAR"): self.indiLOG.log(10, carName+"-"+indigoCarIds+ u" update states (1)    : type: "+beaconType+ u"    bat="+unicode(beaconBattery)+ u"    USB="+unicode(beaconUSB)+ u"    Key="+unicode(beaconKey)+  u"     car newawaySince="+unicode(int(time.time()-self.CARS[u"carId"][indigoCarIds][u"awaySince"]))+ u" newhomeSince="+unicode(int(time.time()-self.CARS[u"carId"][indigoCarIds][u"homeSince"])) )

			if	oldCarStatus == u"away":

				if beaconBattery==2 or beaconUSB==2 or beaconKey==2: 
					self.setIcon(carDev,props, u"SensorOff-SensorOn",1)
					if time.time() - self.CARS[u"carId"][indigoCarIds][u"awaySince"]  > 120: # just arriving home, was away for some time
						self.addToStatesUpdateDict(indigoCarIds,"motion", u"arriving")
						self.checkCarsNeed[indigoCarIds] = 0

					else : # is this a fluke?
						self.addToStatesUpdateDict(indigoCarIds, u"motion", u"unknown")
						self.checkCarsNeed[indigoCarIds]= time.time() + 20

				elif indigoCarIds in self.updateStatesDict and u"location" in self.updateStatesDict[indigoCarIds] and self.updateStatesDict[indigoCarIds][u"location"][u"value"] == u"home":
						self.indiLOG.log(30, "{}-{};  beacon: {} bad state , coming home, but no beacon is on".format(carName, indigoCarIds, beacon) )
						self.checkCarsNeed[indigoCarIds]= time.time() + 20

				if carDev.states[u"LastLeaveFromHome"] == u"": self.addToStatesUpdateDict(indigoCarIds, u"LastLeaveFromHome",datetime.datetime.now().strftime(_defaultDateStampFormat))



			else:  ## home
				if (beaconBattery==2 or beaconUSB==2 or beaconKey==2): 
					if	beaconUSB==1 : # engine is off
						if	 oldCarMotion == u"arriving" and time.time() - self.CARS[u"carId"][indigoCarIds][u"homeSince"] > 10:	 
								self.addToStatesUpdateDict(indigoCarIds, u"motion", u"stop")
						elif oldCarMotion == "leaving"	and time.time() - self.CARS[u"carId"][indigoCarIds][u"homeSince"] > 200: 
								self.addToStatesUpdateDict(indigoCarIds, u"motion", u"stop")
						elif oldCarMotion == u"left"		and time.time() - self.CARS[u"carId"][indigoCarIds][u"homeSince"] < 60: 
								self.addToStatesUpdateDict(indigoCarIds, u"motion", u"arriving")
						elif oldCarMotion == u"": 
								self.addToStatesUpdateDict(indigoCarIds, u"motion", u"stop")
						elif oldCarMotion == u"unknown": 
								self.addToStatesUpdateDict(indigoCarIds, u"motion", u"stop")
						elif oldCarMotion == u"stop": 
								pass
						else:
								self.checkCarsNeed[indigoCarIds]= time.time() + 20

					if	beaconUSB==2 : # engine is on
						if time.time() - self.CARS[u"carId"][indigoCarIds][u"homeSince"] >600: 
							self.addToStatesUpdateDict(indigoCarIds, u"motion", u"leaving")
						elif time.time() - self.CARS[u"carId"][indigoCarIds][u"homeSince"] >60 and oldCarMotion == "stop": 
							self.addToStatesUpdateDict(indigoCarIds, u"motion", u"leaving")
						elif time.time() - self.CARS[u"carId"][indigoCarIds][u"homeSince"] <30 and oldCarMotion in[u"unknown", u"leaving"]: 
							self.addToStatesUpdateDict(indigoCarIds, u"motion", u"arriving")
						else:
							self.checkCarsNeed[indigoCarIds]= time.time() + 20

				else:
					self.checkCarsNeed[indigoCarIds]= time.time() + 20

				if carDev.states[u"LastArrivalAtHome"] ==u"": self.addToStatesUpdateDict(indigoCarIds, u"LastArrivalAtHome",datetime.datetime.now().strftime(_defaultDateStampFormat))

			if updateProps:
					self.deviceStopCommIgnore = time.time()
					carDev.replacePluginPropsOnServer(props)
					carDev	= indigo.devices[int(indigoCarIds)]

			st= ""
			whatForStatus = whatForStatus.split(u"/")
			if u"location" in whatForStatus: st =	   self.updateStatesDict[indigoCarIds][u"location"]["value"]
			if u"engine"   in whatForStatus: st +="/"+ self.updateStatesDict[indigoCarIds][u"engine"]["value"]
			if u"motion"   in whatForStatus: st +="/"+ self.updateStatesDict[indigoCarIds][u"motion"]["value"]
			st = st.strip(u"/").strip(u"/")
			self.addToStatesUpdateDict(indigoCarIds, u"status",st)
			if self.updateStatesDict[indigoCarIds][u"location"]["value"] == u"home":
				carDev.updateStateImageOnServer(indigo.kStateImageSel.SensorOn)
			else:
				carDev.updateStateImageOnServer(indigo.kStateImageSel.SensorTripped)

			if self.decideMyLog(u"CAR"): self.indiLOG.log(10,"{}-{}  update states (2)  : type:{}     car newawaySince: {:.0f}; newhomeSince: {:.0f}".format(carName, indigoCarIds, beaconType, (time.time() - self.CARS[u"carId"][indigoCarIds][u"awaySince"]), (time.time() - self.CARS[u"carId"][indigoCarIds][u"homeSince"]) ) )
			if indigoCarIds in self.checkCarsNeed: 
				if self.decideMyLog(u"CAR"): self.indiLOG.log(10,"{}-{} update states (2)  checkCarsNeed time since last= {:.0f}".format(carName, indigoCarIds, (time.time() - self.checkCarsNeed[indigoCarIds])))
			if self.decideMyLog(u"CAR"): self.indiLOG.log(10, "{}-{} updateStatesList(2): {}".format(carName, indigoCarIds, self.updateStatesDict) )
		except Exception, e:
			self.indiLOG.log(40,"Line {} has error={}".format(sys.exc_traceback.tb_lineno, e))


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
	 
		except Exception, e:
			self.indiLOG.log(40,"Line {} has error={}".format(sys.exc_traceback.tb_lineno, e))
			if unicode(e).find(u"timeout waiting") > -1:
				self.indiLOG.log(40,u"communication to indigo is interrupted")
			self.indiLOG.log(40,u"devId "+carIds+ u" indigo lookup/save problem")
			return 

		try:
			if mode in [u"init", u"validate"]:
				if self.decideMyLog(u"CAR"): self.indiLOG.log(10, u"setupCARS updating states mode:{};  updateStatesList: {}".format(mode, self.updateStatesDict))
				if u"description" not in props: props[u"description"]=""
				if props[u"description"] != text:
					props[u"description"]= text
					self.deviceStopCommIgnore = time.time()
					dev.replacePluginPropsOnServer(props)
				self.executeUpdateStatesDict(onlyDevID=carIds,calledFrom= u"setupCARS ")
			if update: 
				self.setALLrPiV(u"piUpToDate", [u"updateParamsFTP"])
		except Exception, e:
			self.indiLOG.log(40,"Line {} has error={}".format(sys.exc_traceback.tb_lineno, e))
			return props
		return	props

####-------------------------------------------------------------------------####
	def setupBeaconsForCARS(self,propsCar,carIds):
		try:
			beaconList=[]
			text = u"Beacons:"
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
				self.CARS[u"beacon"][beacon]= {u"carId":carIds, u"beaconType":beaconType}
				if beacon not in self.CARS[u"carId"][carIds][u"beacons"]:  self.CARS[u"carId"][carIds][u"beacons"][beacon]=beaconID
				text += beaconType.split(u"beacon")[1]+"="+beaconDev.name+ u";"
				props = beaconDev.pluginProps
				if props[u"fastDown"] ==   u"0":
					props[u"fastDown"] =   u"15"
					if self.decideMyLog(u"CAR"): self.indiLOG.log(10, u"updating fastdown for {} to 0".format(beaconDev.name.encode("utf8")) )
					update=True
					self.deviceStopCommIgnore = time.time()
					beaconDev.replacePluginPropsOnServer(props)
				delB={}
				for b in self.CARS[u"carId"][carIds][u"beacons"]:
					if b not in self.CARS[u"beacon"] or b not in beaconList:
						delB[b]=1
				for b in delB:
					del self.CARS[u"carId"][carIds][u"beacons"][b]
					del self.CARS[u"beacon"][b]
		except Exception, e:
			self.indiLOG.log(40,"Line {} has error={}".format(sys.exc_traceback.tb_lineno, e))
			if unicode(e).find(u"timeout waiting") > -1:
				self.indiLOG.log(40,u"communication to indigo is interrupted")
				return 1/0
			self.indiLOG.log(40, u"devId: {}; indigo lookup/save problem,  in props:{}   CARS:{}".format(carIds, unicode(props), self.CARS))
		return update,text.strip(u";")

####------================----------- CARS ------================-----------END


####------================------- sprinkler ------================-----------
	########################################
	# Sprinkler Control Action callback
	######################
	def actionControlSprinkler(self, action, dev):
		props		= dev.pluginProps
		#indigo.server.log("actionControlSprinkler: "+ unicode(props)+"\n\n"+ unicode(action))
		piU			= props[ u"piServerNumber"]
		ipNumberPi	= self.RPI[piU][ u"ipNumberPi"]
		devId		= int(self.RPI[piU][ u"piDevId"])
		deviceDefs	= [{ u"gpio":-1,u"outType":1}]
		dictForRPI	= { u"cmd":"",u"OUTPUT":0,u"deviceDefs":json.dumps(deviceDefs),u"typeId": u"OUTPUTgpio-1",u"outputDev": u"Sprinkler", u"piServerNumber": piU, u"ipNumberPi":ipNumberPi, u"nPulses":0,u"devId":devId}

		### !!!	 zoneindex goes from 1 ... n !!!

		########################################
		# Required plugin sprinkler actions: These actions must be handled by the plugin.
		########################################
		###### ZONE ON ######
		if action.sprinklerAction == indigo.kSprinklerAction.ZoneOn:
			# first reset all relays -- besides the new and controll 
			if props[u"PumpControlOn"]: nValves = dev.zoneCount-1
			else: nValves = dev.zoneCount
			try:	activeZone = int(int(action.zoneIndex))
			except: activeZone = 0
			if activeZone == 0: return 

			GPIOpin			   = []
			cmd				   = []
			inverseGPIO		   = []
			for nn in range(nValves):
				if nn+1 == int(action.zoneIndex):							 continue
				##if nn-1 ==  nValves and dev.pluginprops[u"PumpControlOn"]: continue 
				GPIOpin.append(props[u"GPIOzone"+unicode(nn+1)])
				dictForRPI["deviceDefs"] = json.dumps(deviceDefs)
				cmd.append("down")
				if "relayOnIfLow" in props and not props[u"relayOnIfLow"]:
					inverseGPIO.append(False)
				else:
					inverseGPIO.append(True)
			self.sendGPIOCommands( ipNumberPi, piU, cmd, GPIOpin, inverseGPIO)
			if props[ u"PumpControlOn"]: # last valve is the control valve 
				deviceDefs[0]["gpio"]	   = props[ u"GPIOzone"+unicode(dev.zoneCount)]
				dictForRPI[ u"deviceDefs"] = json.dumps(deviceDefs)
				dictForRPI[ u"cmd"]		   =  u"pulseUp"
				dictForRPI[ u"pulseUp"]	   = dev.zoneMaxDurations[action.zoneIndex-1]*60
				if "relayOnIfLow" in props and not props[u"relayOnIfLow"]:
					dictForRPI[ u"inverseGPIO"] = False
				else:
					dictForRPI[ u"inverseGPIO"] = True
				self.setPin(dictForRPI)

			self.sleep(0.1)	   ## we need to wait until all gpios are of, other wise then next might be before one of the last off
			deviceDefs[0][ u"gpio"]		= props[u"GPIOzone"+unicode(action.zoneIndex)]
			dictForRPI[ u"deviceDefs"]	= json.dumps(deviceDefs)
			dictForRPI[ u"cmd"]			=  u"pulseUp"
			dictForRPI[ u"pulseUp"]		= dev.zoneMaxDurations[action.zoneIndex-1]*60
			if "relayOnIfLow" in props and not props[u"relayOnIfLow"]:
				dictForRPI[ u"inverseGPIO"] = False
			else:
				dictForRPI[ u"inverseGPIO"] = True
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
					if len(durations) >= activeZone > 1:
						for mm in durations[0:activeZone-1]:
							allMinutes += mm
				else : # single zone manual, check if overwrite max duration
					if "sprinklerActiveZoneSetManualDuration" in indigo.variables:
						try:	dur = max(0,float(indigo.variables["sprinklerActiveZoneSetManualDuration"].value ) )
						except Exception, e:
							self.indiLOG.log(40,"Line {} has error={}".format(sys.exc_traceback.tb_lineno, e))
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
				GPIOpin.append(props[u"GPIOzone"+unicode(nn+1)])
				dictForRPI["deviceDefs"] = json.dumps(deviceDefs)
				cmd.append("down")
				if "relayOnIfLow" in props and not props[u"relayOnIfLow"]:
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

		self.executeUpdateStatesDict(onlyDevID=dev.id,calledFrom="")
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
					self.addToStatesUpdateDict(dev.id,"minutesRunYesterday",dev.states["minutesRunToday"])
					lastList = ["0" for ii in range(dev.zoneCount)]
					lastList = ",".join(lastList)
					self.addToStatesUpdateDict(dev.id,"minutesRunToday",lastList)

					if newWeek:
						self.addToStatesUpdateDict(dev.id,"minutesRunLastWeek",dev.states["minutesRunThisWeek"])
						lastList = ["0" for ii in range(dev.zoneCount)]
						lastList = ",".join(lastList)
						self.addToStatesUpdateDict(dev.id,"minutesRunThisWeek",lastList)

					if newMonth:
						self.addToStatesUpdateDict(dev.id,"minutesRunLastMonth",dev.states["minutesRunThisMonth"])
						lastList = ["0" for ii in range(dev.zoneCount)]
						lastList = ",".join(lastList)
						self.addToStatesUpdateDict(dev.id,"minutesRunThisMonth",lastList)

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
					if props[u"PumpControlOn"]: nValves = dev.zoneCount-1
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


						self.addToStatesUpdateDict(dev.id, "activeZoneMinutesLeft",   timeLeft)
						self.addToStatesUpdateDict(dev.id, "allZonesMinutesLeft",	   timeLeftAll)

					else: # show date time when started .if short , not started
						self.addToStatesUpdateDict(dev.id, "activeZoneMinutesLeft",   0)
						self.addToStatesUpdateDict(dev.id, "allZonesMinutesLeft",	   0)


					for xx in ["minutesRunToday", "minutesRunThisWeek", "minutesRunThisMonth"]:
						lastList = dev.states[xx].split(",")
						if len(lastList) != dev.zoneCount:
							lastList = ["0" for ii in range(dev.zoneCount)]
						lastList[activeZone-1] = unicode( int(lastList[activeZone-1])+1 )
						if props[u"PumpControlOn"] :
							lastList[dev.zoneCount-1] = unicode( int(lastList[dev.zoneCount-1])+1 )
						lastList = ",".join(lastList)
						self.addToStatesUpdateDict(dev.id,xx,lastList)


				self.executeUpdateStatesDict(onlyDevID=dev.id)
		except Exception, e:
			self.indiLOG.log(40,"Line {} has error={}".format(sys.exc_traceback.tb_lineno, e))

####------================------- sprinkler ------================-----------END


####-------------------------------------------------------------------------####
	def readConfig(self):  ## only once at startup
		try:

			self.readTcpipSocketStats()

			self.RPI = self.getParamsFromFile(self.indigoPreferencesPluginDir+"RPIconf")
			if self.RPI =={}: 
				self.indiLOG.log(20, self.indigoPreferencesPluginDir + "RPIconf file does not exist or has bad data, will do a new setup ")


			self.RPIVersion20 = (len(self.RPI) == 20) and len(self.RPI) > 0
			if self.RPIVersion20:
				self.indiLOG.log(30, "RPIconf adding # of rpi  from 20 ..40 ")

			delRPI =[]
			for piU in self.RPI:
				if piU not in _rpiList:
					delRPI.append(piU)
			for piU in delRPI:
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


				delProp=[]
				for piProp in self.RPI[piU]:
					if piProp not in _GlobalConst_emptyRPI:
						delProp.append(piProp)
				for piProp in delProp:
					del self.RPI[piU][piProp]
				delSen={}
				for sensor in self.RPI[piU][u"input"]:
					if sensor not in _GlobalConst_allowedSensors: delSen[sensor]=1
				for sensor in delSen :
					del self.RPI[piU][u"input"][sensor]



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

				for iii in ["input","output"]:
					delSens={}
					for sensor in self.RPI[piU][iii]:

						delDev ={}
						for devId in self.RPI[piU][iii][sensor]:
							try:	 indigo.devices[int(devId)]
							except:	 delDev[devId] = True
						for devId in delDev:
							del self.RPI[piU][iii][sensor][devId]
							self.indiLOG.log(20,"RPI cleanup {} del {} devId:{}".format(piU, iii, devId)  )

						if self.RPI[piU][iii][sensor] =={}:
							delSens[sensor]=True

					for sensor in delSens:
						self.indiLOG.log(20,"RPI cleanup {} deleting {}  {}".format(piU, iii, sensor) )
						del self.RPI[piU][iii][sensor]


			for piU in self.RPI:
				if self.RPI[piU][u"piOnOff"] == "0": 
					self.resetUpdateQueue(piU)


			self.beacons = self.getParamsFromFile(self.indigoPreferencesPluginDir+ "beacons")

			delList={}
			for beacon in self.beacons:
				for nn in _GlobalConst_emptyBeacon:
					if nn not in self.beacons[beacon]:
						self.beacons[beacon][nn]=copy.deepcopy(_GlobalConst_emptyBeacon[nn])

				if self.beacons[beacon][u"indigoId"] == 0: continue

				try:
					dev = indigo.devices[self.beacons[beacon][u"indigoId"]]
				except Exception, e:
					self.indiLOG.log(40,"Line {} has error={}".format(sys.exc_traceback.tb_lineno, e))
					self.indiLOG.log(40,"beacon: {} not an indigo device, removing from beacon list".format(beacon))
					delList[beacon]= True
					continue

				chList=[]
				if "closestRPI" in dev.states: # must be RPI ..
					if dev.states[u"closestRPI"] == "": 
						chList.append({u"key":"closestRPI", u"value":-1})
						if self.setClostestRPItextToBlank: chList.append({u"key":"closestRPIText", u"value":""})
					self.execUpdateStatesList(dev,chList)

				for piU in _rpiBeaconList:
					pi= int(piU)
					try:
						try:    d =  float(dev.states["Pi_"+piU.rjust(2,"0")+"_Distance"])
						except: d = 99999.
						try:    s =  float(dev.states["Pi_"+piU.rjust(2,"0")+"Signal"])
						except: s = -999
						try:    t =  float(dev.states["Pi_"+piU.rjust(2,"0")+"Time"])
						except: t = 0.
						try: 	self.beacons[beacon][u"receivedSignals"][pi]
						except: self.beacons[beacon][u"receivedSignals"].append({})
						if len(self.beacons[beacon][u"receivedSignals"][pi]) == 2:
							self.beacons[beacon][u"receivedSignals"][pi] = {"rssi":s, "lastSignal":t, "distance":d}
						elif len(self.beacons[beacon][u"receivedSignals"][pi]) !=3:
							self.beacons[beacon][u"receivedSignals"][pi] = {"rssi":s, "lastSignal":t, "distance":d}
						elif type(self.beacons[beacon][u"receivedSignals"][pi]) != type({}):
							self.beacons[beacon][u"receivedSignals"][pi] = {"rssi":s, "lastSignal":t, "distance":d}

						lastUp= self.getTimetimeFromDateString(dev.states[u"Pi_"+piU.rjust(2,"0")+"_Time"])
						if self.beacons[beacon][u"receivedSignals"][pi]["lastSignal"] > lastUp: continue # time entry
						self.beacons[beacon][u"receivedSignals"][pi]["rssi"] = float(dev.states[u"Pi_"+piU.rjust(2,"0")+"_Signal"])
						self.beacons[beacon][u"receivedSignals"][pi]["lastSignal"] = lastUp
					except:
						pass
			for beacon in delList:
				del self.beacons[beacon]

			self.beaconsUUIDtoName	 = self.getParamsFromFile(self.indigoPreferencesPluginDir+"beaconsUUIDtoName",		oldName= self.indigoPreferencesPluginDir+"UUIDtoName")
			self.beaconsUUIDtoIphone = self.getParamsFromFile(self.indigoPreferencesPluginDir+"beaconsUUIDtoIphone",	oldName= self.indigoPreferencesPluginDir+"UUIDtoIphone")
			self.beaconsIgnoreUUID	 = self.getParamsFromFile(self.indigoPreferencesPluginDir+"beaconsIgnoreUUID",		oldName= self.indigoPreferencesPluginDir+"beaconsIgnoreFamily")
			self.rejectedByPi		 = self.getParamsFromFile(self.indigoPreferencesPluginDir+"rejected/rejectedByPi.json")
			self.currentVersion		 = self.getParamsFromFile(self.indigoPreferencesPluginDir+"currentVersion", default="0")



			self.readCARS()

			self.startUpdateRPIqueues("start")

			self.checkDEvtoRPIlinks()

			self.indiLOG.log(10, u" ..   config read from files")
			self.fixConfig(checkOnly = ["all","rpi","beacon","CARS","sensors","output","force"], fromPGM="readconfig") 
			self.saveConfig()

		except Exception, e:
			self.indiLOG.log(40,"Line {} has error={}".format(sys.exc_traceback.tb_lineno, e))
			exit(1)

####-------------------------------------------------------------------------####
	def checkDEvtoRPIlinks(self): # called from read config for various input files
		try:

			for dev in indigo.devices.iter("props.isSensorDevice"):
				props = dev.pluginProps
				if "piServerNumber" in props:
					try: piU = unicode(int(props["piServerNumber"]))
					except: continue
				else: continue
				if "input" not in self.RPI[piU]: continue
				typeId = dev.deviceTypeId 
				if typeId not in self.RPI[piU]["input"]:
					self.RPI[piU]["input"][typeId] ={}
				if str(dev.id) not in self.RPI[piU]["input"][typeId]:
					self.indiLOG.log(30,"adding back input sensor {} to RPI:{}".format(dev.name.encode("utf8"), piU))
					self.RPI[piU]["input"][typeId][str(dev.id)] = {}


			for dev in indigo.devices.iter("props.isOutputDevice"):
				props = dev.pluginProps
				if "piServerNumber" in props:
					try: piU = unicode(int(props["piServerNumber"]))
					except: continue
				else: continue
				if "output" not in self.RPI[piU]: continue
				typeId = dev.deviceTypeId 
				if typeId not in self.RPI[piU]["output"]:
					self.RPI[piU]["output"][typeId] ={}
				if str(dev.id) not in self.RPI[piU]["output"][typeId]:
					self.indiLOG.log(30,"adding back out device {} to RPI:{}".format(dev.name.encode("utf8"), piU))
					self.RPI[piU]["output"][typeId][str(dev.id)] = {}


		except Exception, e:
			self.indiLOG.log(40,"Line {} has error={}".format(sys.exc_traceback.tb_lineno, e))

####-------------------------------------------------------------------------####
	def getParamsFromFile(self, newName, oldName="", default={}): # called from read config for various input files
		try:
			out = copy.deepcopy(default)
			#self.indiLOG.log(20,"getParamsFromFile newName:{} oldName: {}; default:{}".format(newName, oldName, unicode(default)[0:100]))
			if os.path.isfile(newName):
				try:
					f = open(newName, u"r")
					out	 = json.loads(f.read())
					f.close()
					if oldName !="" and os.path.isfile(oldName):
						subprocess.call("rm "+oldName, shell=True)
				except Exception, e:
					self.indiLOG.log(40,"Line {} has error={}".format(sys.exc_traceback.tb_lineno, e))
					out =copy.deepcopy(default)
			else:
				out = copy.deepcopy(default)
			if oldName !="" and os.path.isfile(oldName):
				try:
					f = open(oldName, u"r")
					out	 = json.loads(f.read())
					f.close()
					subprocess.call("rm "+oldName, shell=True)
				except Exception, e:
					self.indiLOG.log(40,"Line {} has error={}".format(sys.exc_traceback.tb_lineno, e))
					out = copy.deepcopy(default)
			#self.indiLOG.log(20,"getParamsFromFile out:{} ".format(unicode(out)[0:100]) )
		except Exception, e:
			self.indiLOG.log(40,"Line {} has error={}".format(sys.exc_traceback.tb_lineno, e))
		return out

####-------------------------------------------------------------------------####
	def savebeaconPositionsFile(self):
		try:	
			self.setImageParameters()
			f = open(self.indigoPreferencesPluginDir + "plotPositions/positions.json", u"w")
			f.write(json.dumps(self.beaconPositionsData))
			f.close()
			if self.decideMyLog(u"PlotPositions"): self.indiLOG.log(10, u"savebeaconPositionsFile {}".format(unicode(self.beaconPositionsData[u"mac"])[0:100])  )
		except Exception, e:
			self.indiLOG.log(40,"Line {} has error={}".format(sys.exc_traceback.tb_lineno, e))
		return

####-------------------------------------------------------------------------####
	def setImageParameters(self):
		try:	
			self.beaconPositionsData[u"piDir"]			= self.indigoPreferencesPluginDir+"plotPositions"
			self.beaconPositionsData[u"logLevel"]		= "PlotPositions" in self.debugLevel
			self.beaconPositionsData[u"logFile"]		= self.PluginLogFile
			self.beaconPositionsData[u"distanceUnits"]	= self.distanceUnits
		except Exception, e:
			self.indiLOG.log(40,"Line {} has error={}".format(sys.exc_traceback.tb_lineno, e))
		return

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
							try:	distanceToRPI = float(dev.states["Pi_"+unicode(dev.states[u"closestRPI"]).rjust(2,"0")+"_Distance"])
							except: distanceToRPI = 0.5
							# State "Pi_8_Signal" of "b-radius-3"
							if dev.states["status"] == u"expired": useSymbol = "square45"
							else:								   useSymbol = props[u"showBeaconOnMap"]
							if len(props[u"showBeaconSymbolColor"])!= 7: showBeaconSymbolColor = "#0F0F0F"
							else:								   		 showBeaconSymbolColor = props[u"showBeaconSymbolColor"]
							if len(props[u"showBeaconTextColor"])!= 7:   showBeaconTextColor = "#0FFF0F"
							else:								   		 showBeaconTextColor = props[u"showBeaconTextColor"]
							self.beaconPositionsData[u"mac"][beacon]={u"name":dev.name.encode("utf8"),
								u"position":			[float(dev.states[u"PosX"]),float(dev.states[u"PosY"]),float(dev.states[u"PosZ"])],
								u"nickName":			props[u"showBeaconNickName"],
								u"symbolType":			useSymbol,
								u"symbolColor":			showBeaconSymbolColor,
								u"symbolAlpha":			props[u"showBeaconSymbolAlpha"] ,
								u"distanceToRPI":		distanceToRPI ,
								u"textColor":			showBeaconTextColor ,
								u"status":				dev.states[u"status"]					}
					except Exception, e:
							self.indiLOG.log(40, "Line {} has error={}".format(sys.exc_traceback.tb_lineno, e))

			for dev in indigo.devices.iter("props.isBLEconnectDevice"):
					try:
						props = dev.pluginProps
						beacon = props[u"macAddress"]
						if "showBeaconOnMap" not in props: continue
						if props[u"showBeaconOnMap"] =="0": continue
						if self.beaconPositionsData[u"ShowExpiredBeacons"] == "0" and dev.states["status"] == u"expired": continue
						props = dev.pluginProps

						if u"showBeaconOnMap" not in props or props[u"showBeaconOnMap"] ==u"0":
							if beacon in self.beaconPositionsData[u"mac"]:
								del self.beaconPositionsData[u"mac"][beacon]
							changed = True

						elif "showBeaconOnMap"	in props and props[u"showBeaconOnMap"] in _GlobalConst_beaconPlotSymbols:
							if beacon not in self.beaconPositionsData[u"mac"]:
								changed = True
							try:	distanceToRPI = float(dev.states["Pi_"+unicode(dev.states[u"closestRPI"]).rjust(2,"0")+"_Distance"])
							except: distanceToRPI = 0.5
							if dev.states["status"] == u"expired": useSymbol = "square45"
							else:								   useSymbol = props[u"showBeaconOnMap"]
							if len(props[u"showBeaconSymbolColor"])!= 7: showBeaconSymbolColor = "#0F0F0F"
							else:								   		 showBeaconSymbolColor = props[u"showBeaconSymbolColor"]
							if len(props[u"showBeaconTextColor"])!= 7:   showBeaconTextColor = "#0FFF0F"
							else:								   		 showBeaconTextColor = props[u"showBeaconTextColor"]
							self.beaconPositionsData[u"mac"][beacon]={u"name":dev.name.encode("utf8"),
								u"position":			[float(dev.states[u"PosX"]),float(dev.states[u"PosY"]),float(dev.states[u"PosZ"])],
								u"nickName":			props[u"showBeaconNickName"],
								u"symbolType":			useSymbol,
								u"symbolColor":			showBeaconSymbolColor,
								u"symbolAlpha":			props[u"showBeaconSymbolAlpha"] ,
								u"distanceToRPI":		distanceToRPI ,
								u"textColor":			showBeaconTextColor ,
								u"status":				dev.states[u"status"]					}
					except Exception, e:
							self.indiLOG.log(40,"Line {} has error={}".format(sys.exc_traceback.tb_lineno, e))



			if self.beaconPositionsData[u"ShowRPIs"] in	 _GlobalConst_beaconPlotSymbols:
				for piU in _rpiBeaconList:
					if self.RPI[piU][u"piOnOff"]  == "0": continue
					if self.RPI[piU][u"piDevId"]  == "0": continue
					if self.RPI[piU][u"piDevId"]  == "":  continue
					try:
							dev = indigo.devices[self.RPI[piU][u"piDevId"]]
							props = dev.pluginProps

							p = props[u"PosXYZ"].split(u",")
							pos =[0,0,0] 
							try:
								if len(pos)==3:	pos = [float(p[0]),float(p[1]),float(p[2])]
							except:	 
												pos = [0,0,0]

							beacon = dev.address
							if self.beaconPositionsData[u"ShowRPIs"] ==u"square": nickN =  " R-"+piU
							else:												  nickN =  "R-"+piU
							self.beaconPositionsData[u"mac"][beacon]={u"name":"RPI-"+piU,
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
	#						 self.indiLOG.log(40,"Line {} has error={}".format(sys.exc_traceback.tb_lineno, e))
	 
			if changed or self.beaconPositionsUpdated>0: 
					self.savebeaconPositionsFile()
					cmd = self.pythonPath + " '" + self.pathToPlugin + "makeBeaconPositionPlots.py' '"+self.indigoPreferencesPluginDir+"plotPositions/' & "
					if self.decideMyLog(u"PlotPositions"): 
						self.indiLOG.log(20, u"makeNewBeaconPositionPlots .. beaconPositionsUpdated: {}".format(self.beaconPositionsUpdated))
						self.indiLOG.log(20, u"makeNewBeaconPositionPlots cmd: {} ".format(cmd) )
					subprocess.call(cmd, shell=True)

		except Exception, e:
			if unicode(e).find(u"timeout waiting") > -1:
				self.indiLOG.log(40,"Line {} has error={}".format(sys.exc_traceback.tb_lineno, e))
				self.indiLOG.log(40,u"communication to indigo is interrupted")
				return 
			if len(unicode(e)) > 5	and unicode(e).find(u"not found in database") ==-1:
				self.indiLOG.log(40,"Line {} has error={}".format(sys.exc_traceback.tb_lineno, e))

		self.beaconPositionsUpdated		= 0
		self.beaconPositionsLastCheck	= time.time()

		return 





####-------------------------------------------------------------------------####
	def calcPitoPidist(self):
		self.piToPiDistance =[[[-1,-1,-1,-1] for ii in _rpiBeaconList] for jj in _rpiBeaconList]
		self.piPosition = [[-1,-1,-1] for ii in _rpiBeaconList]
		#self.indiLOG.log(30, "rpi:{}".format(self.RPI) )
		for piU in _rpiBeaconList:
			ii = int(piU)
			try:
				if self.RPI[piU][u"piDevId"] ==0: continue
				if self.RPI[piU][u"piDevId"] ==u"": continue
				devii = indigo.devices[self.RPI[piU][u"piDevId"]]
				propsii= devii.pluginProps
				Pii = self.getPosXYZ(devii,propsii,piU)
				self.piPosition[ii]=Pii
				for jj in range(ii+1, _GlobalConst_numberOfiBeaconRPI):
					piU2 = unicode(jj)
					try:
						if self.RPI[piU2][u"piDevId"] == 0: continue
						if self.RPI[piU2][u"piDevId"] ==u"": continue
						devjj = indigo.devices[self.RPI[piU2][u"piDevId"]]
						propsjj= devjj.pluginProps
						Pjj = self.getPosXYZ(devjj,propsjj,piU2)
						deltaDist =0
						for kk in range(2):
							delD = Pii[kk]-Pjj[kk] 
							deltaDist+= (delD)**2 
							self.piToPiDistance[ii][jj][kk] =  delD
							self.piToPiDistance[jj][ii][kk] = -delD
						deltaDist = math.sqrt(deltaDist)
						self.piToPiDistance[ii][jj][3] = deltaDist
						self.piToPiDistance[jj][ii][3] = deltaDist
					except Exception, e:
						self.indiLOG.log(40,"Line {} has error={}".format(sys.exc_traceback.tb_lineno, e))
			except Exception, e:
				self.indiLOG.log(40,"Line {} has error={}".format(sys.exc_traceback.tb_lineno, e))
		return True

####-------------------------------------------------------------------------####
	def getPosXYZ(self,dev,props,piU):
		try: 
			if u"PosXYZ" not in props:
				props[u"PosXYZ"] ="0,0,0"
				self.deviceStopCommIgnore = time.time()
				dev.replacePluginPropsOnServer(props)
				self.indiLOG.log(40,"Error= fixing props for  RPI#"+piU)
			Pjj = props[u"PosXYZ"].split(u",")

			if len(Pjj) != 3:
				props[u"PosXYZ"] ="0,0,0"
				self.deviceStopCommIgnore = time.time()
				dev.replacePluginPropsOnServer(props)

			Pjj = props[u"PosXYZ"].split(u",")
			return [float(Pjj[0]),float(Pjj[1]),float(Pjj[2])]

		except Exception, e:
			self.indiLOG.log(40,"Line {} has error={}".format(sys.exc_traceback.tb_lineno, e)  +" fixing props, you might need to edit RPI#"+piU)
			props[u"PosXYZ"] ="0,0,0"
			self.deviceStopCommIgnore = time.time()
			dev.replacePluginPropsOnServer(props)
		return [0,0,0]

####-------------------------------------------------------------------------####
	def fixConfig(self,checkOnly = ["all"],fromPGM=""):
		if  self.decideMyLog(u"Logic"): self.indiLOG.log(10, u"fixConfig called from "+fromPGM +u"; with:"+unicode(checkOnly) )
		# dont do it too often
		if time.time() - self.lastFixConfig < 25: return
		self.lastFixConfig	= time.time()

		nowDD = datetime.datetime.now()
		dateString = nowDD.strftime(_defaultDateStampFormat)
		anyChange= False

		try:
			if "rpi" in checkOnly or "all" in checkOnly:
				for piU in self.RPI:
					if self.RPI[piU][u"ipNumberPi"] != "":
						if self.RPI[piU][u"ipNumberPiSendTo"] != self.RPI[piU][u"ipNumberPi"]:
							self.RPI[piU][u"ipNumberPiSendTo"] = copy.copy(self.RPI[piU][u"ipNumberPi"])
							anyChange = True

					try:
						piDevId = int(self.RPI[piU][u"piDevId"])
						if piDevId >0:
							dev= indigo.devices[piDevId]
							props = dev.pluginProps
							upd=False
							if nowDD.hour < 5 and u"addNewOneWireSensors" in props: # reset after midnight
								props[u"addNewOneWireSensors"] = "0"
								upd = True

							if u"ipNumberPi" not in props or (self.isValidIP(self.RPI[piU][u"ipNumberPi"]) and self.RPI[piU][u"ipNumberPi"] != props[u"ipNumberPi"]):
								upd=True
								props[u"ipNumberPi"] = self.RPI[piU][u"ipNumberPi"]

							if u"userIdPi" not in props or self.RPI[piU][u"userIdPi"] != props[u"userIdPi"]:
								upd=True
								props[u"userIdPi"]	 = self.RPI[piU][u"userIdPi"]

							if u"passwordPi" not in props or self.RPI[piU][u"passwordPi"] != props[u"passwordPi"]:
								upd=True
								props[u"passwordPi"] = self.RPI[piU][u"passwordPi"]

							if u"sendToIndigoSecs" not in props and "sensorRefreshSecs" in props:
								upd=True
								props[u"sendToIndigoSecs"] = copy.deepcopy(props[u"sensorRefreshSecs"])

							if u"sendToIndigoSecs" not in props :
								upd=True
								props[u"sendToIndigoSecs"] = copy.copy(_GlobalConst_emptyRPI[u"sensorRefreshSecs"])

							if u"sensorRefreshSecs" not in props :
								upd=True
								props[u"sensorRefreshSecs"] = copy.copy(_GlobalConst_emptyRPI[u"sensorRefreshSecs"])

							if u"rssiOffset" not in props :
								upd=True
								props[u"rssiOffset"] = copy.copy(_GlobalConst_emptyRPI[u"rssiOffset"])

							if dev.enabled:
								if self.RPI[piU][u"piOnOff"] != "1":
									try:	del self.checkIPSendSocketOk[self.RPI[piU][u"ipNumberPi"]]
									except: pass
								self.RPI[piU][u"piOnOff"] = "1"
							else:
								self.RPI[piU][u"piOnOff"] = "0"

							if upd:
								self.deviceStopCommIgnore = time.time()
								dev.replacePluginPropsOnServer(props)
								dev= indigo.devices[piDevId]
								anyChange = True

					except Exception, e:
						if unicode(e).find(u"timeout waiting") > -1:
							self.indiLOG.log(40,"Line {} has error={}".format(sys.exc_traceback.tb_lineno, e))
							self.indiLOG.log(40, u"communication to indigo is interrupted")
							return
						self.sleep(0.2)
						if self.RPI[piU][u"piDevId"] !=0:
							try:
								self.indiLOG.log(40,"Line {} has error={}".format(sys.exc_traceback.tb_lineno, e))
								self.indiLOG.log(40,u"error normal if rpi has been deleted, removing from list: setting piDevId=0")
							except: pass
							self.delRPI(pi=pi, calledFrom="fixConfig")
						anyChange = True

					if self.RPI[piU][u"piOnOff"] != "0":
						if not self.isValidIP(self.RPI[piU][u"ipNumberPi"]):
							self.RPI[piU][u"piOnOff"] = "0"
							anyChange = True
							continue
		except Exception, e:
			self.indiLOG.log(40,"Line {} has error={}".format(sys.exc_traceback.tb_lineno, e))

		try:
			if "all" in checkOnly:
				delDEV = []
				for dev in indigo.devices.iter("props.isCARDevice,props.isBeaconDevice,props.isRPIDevice,props.isRPISensorDevice"):
					props=dev.pluginProps
					if dev.deviceTypeId==u"car": 
						newP = self.setupCARS(dev.id,props,mode="init")
						if newP[u"description"] != dev.description:
							if self.decideMyLog(u"CAR"): self.indiLOG.log(10, u"replacing car props {}  {}  {}".format(dev.name.encode("utf8"),  newP[u"description"], dev.description) )
							dev.description =  newP[u"description"] 
							dev.replaceOnServer()
							anyChange = True
						continue


					if u"description" in props:
						if props[u"description"] !="":
							if dev.description != props[u"description"]:
								dev.description = props[u"description"]
								self.indiLOG.log(20,"{} updating descriptions {}".format(dev.name.encode("utf8"), props[u"description"]))
								props[u"description"] =""
								dev.replaceOnServer()
								updateProps = True

					if dev.deviceTypeId.find(u"rPI") >-1: 
						props= dev.pluginProps
						try:	pi = int(dev.states[u"note"].split(u"-")[1])
						except: continue
						try:	beacon = props[u"address"]
						except: beacon =""
						piU = unicode(pi)

						if u"ipNumberPi" in props and self.isValidIP(self.RPI[piU][u"ipNumberPi"]) and self.RPI[piU][u"ipNumberPi"] != props[u"ipNumberPi"]:
							self.indiLOG.log(20, "{} fixing ipNumber in RPI device props to {}".format(dev.name.encode("utf8"), self.RPI[piU][u"ipNumberPi"]))
							dev.description = "Pi-{}-{}".format(pi,self.RPI[piU][u"ipNumberPi"])
							dev.replaceOnServer()
							props[u"ipNumberPi"] = self.RPI[piU][u"ipNumberPi"]  
							self.deviceStopCommIgnore = time.time()
							dev.replacePluginPropsOnServer(props)
							anyChange = True

						if u"ipNumberPi" in props and self.isValidIP(props[u"ipNumberPi"]) and self.RPI[piU][u"ipNumberPi"] != props[u"ipNumberPi"]:
							self.indiLOG.log(20, "{} fixing ipNumber in RPI device props to {}".format(dev.name.encode("utf8"), props[u"ipNumberPi"]))
							self.RPI[piU][u"ipNumberPi"]  = props[u"ipNumberPi"]
							anyChange = True

						if dev.id != self.RPI[piU][u"piDevId"]:
							self.indiLOG.log(20, u"dev :{} fixing piDevId in RPI".format(dev.name.encode("utf8")) )
							self.RPI[piU][u"piDevId"]	 = dev.id
							anyChange = True

						if len(beacon)> 6 and self.RPI[piU][u"piMAC"] != beacon:
							self.indiLOG.log(20, u"dev: {}  fixing piMAC in RPI".format(dev.name.encode("utf8")))
							self.RPI[piU][u"piMAC"]	   = beacon
							anyChange = True

						if u"userIdPi" in props and	 self.RPI[piU][u"userIdPi"] != props[u"userIdPi"]:
							self.indiLOG.log(20, u"dev: {} fixing userIdPi in RPI".format(dev.name.encode("utf8")))
							self.RPI[piU][u"userIdPi"]	  = props[u"userIdPi"]
							anyChange = True

						if u"passwordPi" in props and  self.RPI[piU][u"passwordPi"] != props[u"passwordPi"]:
							self.indiLOG.log(20, u"dev: {} fixing passwordPi in RPI".format(dev.name.encode("utf8")))
							self.RPI[piU][u"passwordPi"]	= props[u"passwordPi"]
							anyChange = True

						if dev.deviceTypeId == u"rPI":
							beacon = dev.address
							if self.isValidMAC(beacon):
								if beacon not in self.beacons:
									self.beacons[beacon] = copy.deepcopy(_GlobalConst_emptyBeacon)
									self.beacons[beacon][u"typeOfBeacon"] = u"rPI"
									self.beacons[beacon][u"indigoId"] = dev.id
									checkOnly.append("beacon")
									checkOnly.append("force")
									

					if dev.deviceTypeId.find(u"beacon") >-1: 
						props		= dev.pluginProps
						updateProps = False
						for propEmpty in _GlobalConst_emptyBeaconProps:
							if propEmpty not in props:
								props[propEmpty] = _GlobalConst_emptyBeaconProps[propEmpty]
								updateProps=True
						if updateProps:
							self.deviceStopCommIgnore = time.time()
							dev.replacePluginPropsOnServer(props)
							anyChange = True

					if "force" in checkOnly:
						if self.fixDevProps(dev) == -1:
							delDEV.append(dev)
							anyChange = True

				for dev in delDEV:
					self.indiLOG.log(30, u"fixConfig dev: {}  has no addressfield".format(dev.name.encode("utf8")))
					# indigo.device.delete(dev)
		except Exception, e:
			self.indiLOG.log(40,"Line {} has error={}".format(sys.exc_traceback.tb_lineno, e))

		try:
			if "all" in checkOnly or "beacon" in checkOnly:
				# remove junk:
				remove = []
				for beacon in self.beacons:
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
										self.indiLOG.log(30,u"fixConfig fixing: beacon should not in beacon list: {}  {}  {}".format(beacon, dev.name.encode("utf8"), dev.deviceTypeId ) )
									except:
										self.indiLOG.log(30, u"fixConfig fixing: beacon should not in beacon list: {} no name / device {}".format(beacon, dev.deviceTypeId ) )
									remove.append(beacon)
									anyChange = True
									continue



								beaconDEV = props[u"address"]
								if beaconDEV != beacon:
									self.beacons[beacon][u"indigoId"] = 0
									self.indiLOG.log(20, u"fixing: {}  beaconDEV:{}  beacon:{} beacon wrong, using current beacon-mac".format(dev.name.encode("utf8"), beaconDEV, beacon))
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
									self.indiLOG.log(20, dev.name.encode("utf8")+" has no fastDown")
									self.beacons[beacon][u"fastDown"]			 = "0"
								if u"fastDownMinSignal" in props: # not for RPI
									self.beacons[beacon][u"fastDownMinSignal"]			  = props[u"fastDownMinSignal"]
								else:
									self.beacons[beacon][u"fastDownMinSignal"]			  = -999

								if u"updateSignalValuesSeconds" in props: # not for RPIindigoIdindigoIdindigoIdindigoIdindigoId
									self.beacons[beacon][u"updateSignalValuesSeconds"] = float(props[u"updateSignalValuesSeconds"])
								else:
									self.beacons[beacon][u"updateSignalValuesSeconds"] = 300
							except Exception, e:
								anyChange = True
								if unicode(e).find(u"timeout waiting") > -1:
									self.indiLOG.log(40,"Line {} has error={}".format(sys.exc_traceback.tb_lineno, e))
									self.indiLOG.log(40,u"communication to indigo is interrupted")
									return 
								elif unicode(e).find(u"not found in database") >-1:
									self.beacons[beacon][u"indigoId"] =0
									continue
								else:
									self.indiLOG.log(40,"Line {} has error={}".format(sys.exc_traceback.tb_lineno, e))
									try:
										self.indiLOG.log(40,u"device:{}  {}\n  beacon:{}" +format(dev.name.encode("utf8"), dev.states, self.beacons[beacon]) )
									except Exception, e:
										self.indiLOG.log(40,"Line {} has error={}".format(sys.exc_traceback.tb_lineno, e))
									return 


						else:
							self.beacons[beacon][u"updateSignalValuesSeconds"] = copy.copy(_GlobalConst_emptyBeacon[u"updateSignalValuesSeconds"])
				for beacon in remove:
					self.indiLOG.log(20,  u"fixConfig:  deleting beacon:{}  {}".format(beacon, self.beacons[beacon]))
					del self.beacons[beacon]

		except Exception, e:
			self.indiLOG.log(40,"Line {} has error={}".format(sys.exc_traceback.tb_lineno, e))
		#self.indiLOG.log(20, u"fixConfig time elapsed point C  "+unicode(time.time()- self.lastFixConfig) +"     anyChange: "+ unicode(anyChange))

		try:
			if "rpi" in checkOnly or "all" in checkOnly:
				for beacon in self.beacons:
					if self.beacons[beacon][u"typeOfBeacon"].lower() == "rpi":
						if self.beacons[beacon][u"note"].find(u"Pi-") == 0:
							try:
								pi = int(self.beacons[beacon][u"note"].split("-")[1])
							except:
								continue
							if self.beacons[beacon][u"indigoId"] != 0 :# and self.beacons[beacon][u"ignore"] ==0:
								piU = unicode(pi)
								try:
									devId   = indigo.devices[self.beacons[beacon][u"indigoId"]].id
									if self.RPI[piU][u"piDevId"] != devId:
										self.RPI[piU][u"piDevId"] = devId
										anyChange = True
									if self.RPI[piU][u"PosX"] !=0 or self.RPI[piU][u"PosY"] !=0 or self.RPI[piU][u"PosZ"] !=0 :
										dev   = indigo.devices[devId]
										for xyz in ["PosX","PosY","PosZ"]:
											if dev.states[xyz] != self.RPI[piU][xyz]: dev.updateStateOnServer(xyz, self.RPI[piU][xyz] )

								except Exception, e:
									if unicode(e).find(u"timeout waiting") > -1:
										self.indiLOG.log(40,"Line {} has error={}".format(sys.exc_traceback.tb_lineno, e))
										self.indiLOG.log(40, u"communication to indigo is interrupted")
										return
									elif unicode(e).find(u"not found in database") >-1:
										self.beacons[beacon][u"indigoId"] = 0
										anyChange = True
										self.indiLOG.log(20,	u"fixConfig anychange: (fix) set indigoID=0,  beacon, pi, devid "+ unicode(beacon) +"  "+ piU +"  "+ unicode(devId) )
										continue
									else:
										self.indiLOG.log(40,"Line {} has error={}".format(sys.exc_traceback.tb_lineno, e))
										self.indiLOG.log(40,u"unknown error")
										return

			if "all" in checkOnly or "beacon" in checkOnly :
				for beacon in self.beacons:
					if self.beacons[beacon][u"indigoId"] == 0:	# remove iphones if the devices was deleted
						if beacon in self.beaconsUUIDtoIphone:
							del self.beaconsUUIDtoIphone[beacon]
							anyChange = True
							#self.indiLOG.log(20,	u"fixConfig anychange: D-3  beacon,  "+ unicode(beacon) )
		except Exception, e:
			self.indiLOG.log(40,"Line {} has error={}".format(sys.exc_traceback.tb_lineno, e))


		if "rpi" in checkOnly:
			self.calcPitoPidist()

		if "all" in checkOnly:
			if self.syncSensors(): anyChange = True

		if anyChange or (time.time() - self.lastSaveConfig) > 100:
			self.lastSaveConfig = time.time() 
			self.saveConfig()
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
		except Exception, e:
			self.indiLOG.log(40,"Line {} has error={}".format(sys.exc_traceback.tb_lineno, e))
		return 1


####-------------------------------------------------------------------------####
	def saveSensorMessages(self,devId="",item="", value=0):
		try:
			if devId != "":
				self.checkSensorMessages(devId, item="lastMessage", default=value)
			else:
				self.writeJson(self.sensorMessages,fName=self.indigoPreferencesPluginDir + u"sensorMessages")
			return
		except Exception, e:
			self.indiLOG.log(40,"Line {} has error={}".format(sys.exc_traceback.tb_lineno, e))


####-------------------------------------------------------------------------####
	def writeJson(self,data, fName="", fmtOn=False ):
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

		except Exception, e:
			self.indiLOG.log(40,"Line {} has error={}".format(sys.exc_traceback.tb_lineno, e))
		return ""

####-------------------------------------------------------------------------####
	def saveConfig(self, only="all"):

		if only in ["all", "RPIconf"]:
			self.writeJson(self.RPI, fName=self.indigoPreferencesPluginDir + u"RPIconf", fmtOn=self.RPIFileSort)

		if only in ["all"]:
			self.saveCARS()

		if only in ["all"]:
			self.writeJson(self.beacons, fName=self.indigoPreferencesPluginDir + "beacons", fmtOn=self.beaconsFileSort)

		if only in ["all"]:
			self.makeBeacons_parameterFile()

		if only in ["all"]:
			self.writeJson( self.beaconsUUIDtoName, fName=self.indigoPreferencesPluginDir + u"beaconsUUIDtoName")

		if only in ["all"]:
			self.writeJson( self.beaconsIgnoreUUID, fName=self.indigoPreferencesPluginDir + u"beaconsIgnoreUUID")

		if only in ["all"]:
			self.writeJson(self.beaconsUUIDtoIphone,fName=self.indigoPreferencesPluginDir + u"beaconsUUIDtoIphone")


####-------------------------------------------------------------------------####
	def fixDevProps(self, dev):
		dateString = datetime.datetime.now().strftime(_defaultDateStampFormat)
		updateProps = False
		props = dev.pluginProps
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
				self.deviceStopCommIgnore = time.time()
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

 

		updatedev = False
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
			
			if dev.description.find(u"Pi-") > -1:
				if dev.states[u"note"].find(u"Pi-") > -1:
					piU= dev.states[u"note"].split(u"-")[1]
					self.RPI[piU][u"piDevId"] = dev.id


		if updatedev:
			dev.replaceOnServer()


		if updateProps:
			updateProps= False
			self.deviceStopCommIgnore = time.time()
			dev.replacePluginPropsOnServer(props)
			props=dev.pluginProps

		if u"lastStatusChange" in dev.states and len(dev.states[u"lastStatusChange"]) < 5:
			dev.updateStateOnServer(u"lastStatusChange",dateString)


		# only rPi and iBeacon from here on
		if u"address" not in props:
			self.indiLOG.log(30, "=== deleting dev :" + dev.name.encode("utf8") + " has no address field, please do NOT manually create beacon devices")
			self.indiLOG.log(30, u"fixDevProps  props" + unicode(props))
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
				self.addToStatesUpdateDict(dev.id,"created", dateString)
			if u"expirationTime" not in props:
				updateProps = True
				props[u"expirationTime"] = 90.

			if updateProps:
				self.deviceStopCommIgnore = time.time()
				dev.replacePluginPropsOnServer(props)
				if self.decideMyLog(u"Logic"): self.indiLOG.log(10, u"updating props for " + dev.name.encode("utf8") + " in fix props")

			if dev.deviceTypeId == "beacon" :
				noteState = "beacon-" + props[u"typeOfBeacon"] 
				if dev.states[u"note"] != noteState:
					self.addToStatesUpdateDict(dev.id,"note",noteState)
			else:  
				noteState = dev.states[u"note"]		 


			if beacon not in self.beacons:
				self.indiLOG.log(10, u"fixDevProps: adding beacon from devices to self.beacons: "+beacon+"  dev:"+dev.name.encode("utf8"))
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
			self.beacons[beacon][u"updateSignalValuesSeconds"] = float(props[u"updateSignalValuesSeconds"])

		except Exception, e:
			self.indiLOG.log(40,"Line {} has error={}".format(sys.exc_traceback.tb_lineno, e))

		return 0





####-------------------------------------------------------------------------####
	def deviceStartComm(self, dev):
		try:
			#self.indiLOG.log(20,"deviceStartComm called for dev={}, stopcom ignore:{}".format(dev.name, self.deviceStopCommIgnore) )

			if self.pluginState == "init":

				doSensorValueAnalog =["Wire18B20","DHT","i2cTMP102","i2cMCP9808","i2cLM35A","i2cT5403",
				"i2cMS5803","i2cBMPxx","tmp006","tmp007","i2cSHT21""i2cAM2320","i2cBMExx","bme680","si7021",
				"max31865",
				"pmairquality",
				"BLEsensor","sgp30",
				"mhzCO2",
				"ccs811","rainSensorRG11","as3935",
				"ina3221", "ina219",
				"i2cADC121",
				"i2cADS1x15-1", "i2cADS1x15"
				"spiMCP3008-1", "spiMCP3008",
				"PCF8591","ADS1x15",
				"MAX44009",
				"i2cTCS34725", "as726x", "i2cOPT3001", "i2cVEML7700", "i2cVEML6030", "i2cVEML6040", "i2cVEML6070", "i2cVEML6075", "i2cTSL2561", 
				"mlx90614", "amg88xx", "mlx90640","lidar360",
				"vl503l0xDistance", "vcnl4010Distance", "vl6180xDistance", "apds9960", "ultrasoundDistance",
				"INPUTpulse"]

				doSensorValueOnOff =["INPUTgpio-1","INPUTgpio-4","INPUTgpio-8","INPUTgpio-26",
				"INPUTtouch-1","INPUTtouch-4","INPUTtouch-12","INPUTtouch-16",
				"rPI","rPI-Sensor","beacon","BLEconnect"]

				dev.stateListOrDisplayStateIdChanged()	# update  from device.xml info if changed
				if int(self.currentVersion.split(".")[0]) < 7:
					self.indiLOG.log(20," checking for deviceType upgrades: {}".format(dev.name.encode("utf8")) )
					if dev.deviceTypeId in doSensorValueAnalog:
						props = dev.pluginProps
						if "SupportsSensorValue" not in props:
							self.indiLOG.log(20," processing: {}".format(dev.name.encode("utf8")) )
							dev = indigo.device.changeDeviceTypeId(dev, dev.deviceTypeId)
							dev.replaceOnServer()
							dev = indigo.devices[dev.id]
							props = dev.pluginProps
							props[u"SupportsSensorValue"] 		= True
							props[u"SupportsOnState"] 			= False
							props[u"AllowSensorValueChange"] 	= False
							props[u"AllowOnStateChange"] 		= False
							props[u"SupportsStatusRequest"] 		= False
							self.deviceStopCommIgnore = time.time()
							dev.replacePluginPropsOnServer(props)
							self.indiLOG.log(20,"SupportsSensorValue  after replacePluginPropsOnServer")

					if dev.deviceTypeId in doSensorValueOnOff:
						props = dev.pluginProps
						if "SupportsOnState" not in props:
							self.indiLOG.log(20," processing: {}".format(dev.name.encode("utf8")) )
							dev = indigo.device.changeDeviceTypeId(dev, dev.deviceTypeId)
							dev.replaceOnServer()
							dev = indigo.devices[dev.id]
							props = dev.pluginProps
							props[u"SupportsSensorValue"] 		= False
							props[u"SupportsOnState"] 			= True
							props[u"AllowSensorValueChange"] 	= False
							props[u"AllowOnStateChange"] 		= False
							props[u"SupportsStatusRequest"] 	= False
							self.deviceStopCommIgnore = time.time()
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

							self.indiLOG.log(20,"SupportsOnState after replacePluginPropsOnServer")



				props= dev.pluginProps
				if dev.deviceTypeId in ["rPI","rPI-Sensor"]:
					upd = False
					if "ipNumber" in props:
						if "ipNumberPi" not in props:
							props[u"ipNumberPi"] = props["ipNumber"]
						del props["ipNumber"]
						upd = True
					piNo = dev.states["note"].split("-")
					if len(piNo) !=2:
						self.deviceStopCommIgnore = time.time()
						dev.updateStateOnServer("note","Pi-"+piNo[-1])

					if upd: 
						self.deviceStopCommIgnore = time.time()
						dev.replacePluginPropsOnServer(props)

				self.statusChanged=2


			if dev.deviceTypeId.find("rPI") > -1:
				piNo = dev.states["note"].split("-")
				try: 	self.RPI[str(int(piNo[-1]))]["piOnOff"] ="1"
				except: pass
				if time.time() - self.deviceStopCommIgnore  > 0.1:
					self.deviceStopCommIgnore = 0
					self.updateNeeded = " enable startcomm called "

			if dev.deviceTypeId == "sprinkler":
				self.sprinklerDeviceActive = True

		except Exception, e:
			self.indiLOG.log(40,"Line {} has error={}".format(sys.exc_traceback.tb_lineno, e))

####-------------------------------------------------------------------------####
	def deviceDeleted(self, dev):  ### indigo calls this 
		props= dev.pluginProps

		if u"address" in props: 
				beacon = props[u"address"]
				if beacon in self.beacons and beacon.find("00:00:00:00") ==-1:
					if u"indigoId" in self.beacons[beacon] and	self.beacons[beacon][u"indigoId"] == dev.id:
						self.indiLOG.log(20, u"-setting beacon device in internal tables to 0:  " + dev.name.encode("utf8")+"  "+unicode(dev.id)+" enabled:"+ unicode(dev.enabled)+ "  pluginState:"+ self.pluginState)
						self.beacons[beacon][u"indigoId"] = 0
						self.beacons[beacon][u"ignore"]	  = 1
						self.writeJson(self.beacons, fName=self.indigoPreferencesPluginDir + "beacons", fmtOn=self.beaconsFileSort)
		if dev.deviceTypeId.find("rPI") > -1:
			try:
				pi = dev.description.split("-")
				if len(pi) > 0:
					self.delRPI(pi=pi[1], calledFrom="deviceDeleted")
			except:
				pass
		self.deviceStopComm(dev)
		return

####-------------------------------------------------------------------------####
	def deviceStopComm(self, dev):
		#self.indiLOG.log(20,"deviceStopComm called for dev={}, stopcom ignore:{}".format(dev.name, self.deviceStopCommIgnore) )
		try:
			props= dev.pluginProps
			if self.pluginState != "stop":

				if self.freezeAddRemove : self.sleep(0.2)

				if time.time() - self.deviceStopCommIgnore  > 0.1:
					self.deviceStopCommIgnore = 0
					self.updateNeeded = " disable stopcomm called "

				self.statusChanged=2

			if dev.deviceTypeId.find("rPI") > -1:
				piNo = dev.states["note"].split("-")
				try: 	self.RPI[str(int(piNo[-1]))]["piOnOff"] ="0"
				except: pass

		except Exception, e:
			self.indiLOG.log(40,"Line {} has error={}".format(sys.exc_traceback.tb_lineno, e))


####-------------------------------------------------------------------------####
	#def didDeviceCommPropertyChange(self, origDev, newDev):
	#	 #if origDev.pluginProps['xxx'] != newDev.pluginProps['address']:
	#	 #	  return True
	#	 return False
	###########################		INIT	## END	 ########################




	###########################		DEVICE	#################################
####-------------------------------------------------------------------------####
	def getDeviceConfigUiValues(self, pluginProps, typeId="", devId=0):
		if typeId in [u"beacon", u"rPI", u"rPI-Sensor"]:
			try:
				theDictList =  super(Plugin, self).getDeviceConfigUiValues(pluginProps, typeId, devId)
				if typeId != "rPI-Sensor":
					if u"address" in theDictList[0]: # 0= valuesDict,1 = errors dict
						if theDictList[0][u"address"] != "00:00:00:00:00:00": 
							theDictList[0][u"newMACNumber"] = copy.copy(theDictList[0][u"address"])
						else:
							theDictList[0][u"newMACNumber"] = ""

				dev = indigo.devices[devId]


				if typeId.find("rPI") >- 1:
					try:
						if "MSG" in theDictList[0]:
							theDictList[0][u"enablePiNumberMenu"]  = True
						else:
							theDictList[0][u"newauthKeyOrPassword"]  = "assword"
							theDictList[0][u"newenableRebootCheck"]  = "restartLoop"
							theDictList[0][u"enablePiNumberMenu"]  = True


						piU= "-1"
						rpiNo = dev.states["note"].split("-")

						try:	
							piU = str(int(rpiNo[1]))
							theDictList[0][u"RPINumber"] = piU
						except: 
							if typeId == "rPI-Sensor":
								for piU1 in _rpiSensorList:
									if self.RPI[piU1]["piDevId"] == 0:
										theDictList[0][u"RPINumber"] = piU1
										break
							else:
								for piU2 in _rpiList:
									if self.RPI[piU2]["piDevId"] == 0:
										theDictList[0][u"RPINumber"] = piU2
										break

						theDictList[0][u"newIPNumber"]   = self.RPI[piU][u"ipNumberPi"]
						theDictList[0][u"newpasswordPi"] = self.RPI[piU]["passwordPi"]
						theDictList[0][u"newuserIdPi"]   = self.RPI[piU]["userIdPi"]
						theDictList[0][u"newauthKeyOrPassword"]   = self.RPI[piU]["authKeyOrPassword"]

						if typeId =="rPI" and piU == "-1":
								theDictList[0][u"newMACNumber"] = "00:00:00:00:pi:00"
					except Exception, e:
						self.indiLOG.log(30,"Line {} has error={}".format(sys.exc_traceback.tb_lineno, e))

				return theDictList 
			except Exception, e:
				self.indiLOG.log(40,"Line {} has error={}".format(sys.exc_traceback.tb_lineno, e))

		return super(Plugin, self).getDeviceConfigUiValues(pluginProps, typeId, devId)



####-------------------------------------------------------------------------####
	def validateDeviceConfigUi(self, valuesDict, typeId, devId):

		error =""
		errorDict = indigo.Dict()
		valuesDict[u"MSG"] = "OK"
		update = 0
		beacon = "xx"
		try:
			dev = indigo.devices[devId]
			props = dev.pluginProps	
			#self.indiLOG.log(20, u"{} devid:{} typeId:{} ".format(dev.name, devId, typeId) )
				
			# just a  reminder: new devices have props ={}, need to use valueDict
		

			if typeId == "car":
				valuesDict = self.setupCARS(devId,valuesDict,mode="validate")
				return (True, valuesDict)


			if typeId == "sprinkler":
				#valuesDict[u"description"] = "Pi-"+valuesDict[u"piServerNumber"]
				valuesDict[u"address"] = "Pi-"+valuesDict[u"piServerNumber"]
				#self.updateNeeded += " fixConfig "
				return (True, valuesDict)

			beacon = ""
			if typeId in [u"beacon", u"rPI"]:
				try:
					beacon = props[u"address"]
				except: pass
			if  len(beacon) < 8: 
				beacon = "00:00:00:00:pi:00"

			thisPi = "-1"
			if typeId.find(u"rPI") > -1:
				for piU in self.RPI:
					if devId == self.RPI[piU][u"piDevId"]:
						thisPi = piU
						break
				try: thisPiV = unicode(int(valuesDict["RPINumber"]))
				except: thisPiV = "-1"
				if thisPi =="-1" or (thisPiV != "-1" and thisPi != thisPiV): 

					if  thisPi != "-1":
						self.RPI[thisPiV] = copy.deepcopy(self.RPI[thisPi])
					self.RPI[thisPi] = copy.deepcopy(_GlobalConst_emptyRPI)

					thisPi = thisPiV

				valuesDict["RPINumber"] = thisPi 

			if typeId in [u"rPI-Sensor",u"rPI"]:
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


############ RPI  -------
			if typeId == "rPI":
				try:
					if u"address" not in props: new = True
					else:						new = False
					newMAC = valuesDict[u"newMACNumber"].upper()
					valuesDict[u"newMACNumber"] = newMAC
					if not self.isValidMAC(newMAC):
						valuesDict[u"newMACNumber"] = beacon
						valuesDict, errorDict  = self.setErrorCode(valuesDict,errorDict,  "bad Mac Number")
						return ( False, valuesDict, errorDict )

					if not new:
						if beacon != newMAC:
							self.indiLOG.log(20, u"replacing RPI BLE mac {} with {}".format(beacon, newMAC) )
							piFound =-1
							for piU in _rpiBeaconList: 
								if self.RPI[piU][u"piMAC"] == newMAC:
									self.indiLOG.log(20, u"replacing RPI BLE mac failed. rpi already exists with this MAC number")
									valuesDict, errorDict  = self.setErrorCode(valuesDict,errorDict,  "bad beacon#, already exist as RPI")
									return ( False, valuesDict, errorDict )

							self.indiLOG.log(20, u"replacing existing beacon")
							if newMAC not in self.beacons:
								self.beacons[newMAC] = copy.deepcopy(_GlobalConst_emptyBeacon)
								self.beacons[newMAC][u"note"] = "PI-"+thisPi
							else:
								if beacon in self.beacons:
									self.beacons[newMAC] = copy.deepcopy(self.beacons[beacon])
								else:
									self.beacons[newMAC] = copy.deepcopy(_GlobalConst_emptyBeacon)
							self.newADDRESS[devId]			= newMAC
							valuesDict[u"address"]			= newMAC
							self.RPI[thisPi][u"piMAC"]		= newMAC
							if beacon in self.beacons:
								self.beacons[beacon][u"indigoId"]= 0
							beacon = newMAC
					if new:
						for piU in self.RPI: 
							if self.RPI[piU][u"piMAC"] == newMAC:
								self.indiLOG.log(20, u"adding new RPI another RPI(#{}) has already that this MAC number:{}".format(piU, newMAC ))
								valuesDict, errorDict  = self.setErrorCode(valuesDict,errorDict,  "bad beacon#, already exist as RPI")
								return ( False, valuesDict, errorDict )
						self.indiLOG.log(20, u"setting up new RPI device for pi#{} mac#  {}".format(thisPi, newMAC) )
						for ll in _GlobalConst_emptyrPiProps:
							if ll not in valuesDict: valuesDict[ll]= _GlobalConst_emptyrPiProps[ll]

					self.RPI[thisPi][u"piDevId"] 			= devId
					valuesDict[u"address"]					= newMAC
					self.RPI[thisPi][u"piMAC"]				= newMAC
					beacon 									= newMAC


					self.RPI[thisPi][u"ipNumberPi"] 		= valuesDict["newIPNumber"]
					self.RPI[thisPi][u"ipNumberPiSendTo"] 	= valuesDict["newIPNumber"]
					self.RPI[thisPi]["userIdPi"] 			= valuesDict["newuserIdPi"]
					self.RPI[thisPi]["passwordPi"]			= valuesDict["newpasswordPi"]
					valuesDict["passwordPi"] 				= valuesDict["newpasswordPi"]
					valuesDict["userIdPi"] 					= valuesDict["newuserIdPi"]
					valuesDict[u"description"] 				= "Pi-{}-{}".format(thisPi, valuesDict["newIPNumber"])


					if beacon in self.beacons and beacon.find("00:00:00:00") ==-1:
						self.beacons[beacon][u"expirationTime"] 			= float(valuesDict[u"expirationTime"])
						self.beacons[beacon][u"updateSignalValuesSeconds"]	= float(valuesDict[u"updateSignalValuesSeconds"])
						self.beacons[beacon][u"beaconTxPower"] 				= int(valuesDict[u"beaconTxPower"])
						self.beacons[beacon][u"ignore"] 					= int(valuesDict[u"ignore"])
						dev.updateStateOnServer(u"TxPowerSet",int(valuesDict[u"beaconTxPower"]))

					self.RPI[thisPi][u"sendToIndigoSecs"] 					= valuesDict[u"sendToIndigoSecs"]	
					self.RPI[thisPi][u"sensorRefreshSecs"] 					= valuesDict[u"sensorRefreshSecs"]
					self.RPI[thisPi][u"deltaChangedSensor"] 				= valuesDict[u"deltaChangedSensor"]
					try:	 self.RPI[thisPi][u"rssiOffset"]				= float(valuesDict["rssiOffset"])
					except:	 self.RPI[thisPi][u"rssiOffset"]				= 0.
					self.RPI[thisPi][u"BLEserial"] 							= valuesDict[u"BLEserial"]
					self.setONErPiV(thisPi,"piUpToDate", [u"updateParamsFTP"])
					self.rPiRestartCommand[int(thisPi)] 					= "master"
					self.RPI[thisPi]["authKeyOrPassword"]					= valuesDict[u"newauthKeyOrPassword"]  
					self.RPI[thisPi]["enableRebootCheck"]					= valuesDict[u"newenableRebootCheck"]  
					self.RPI[piU][u"piOnOff"] 								= "1"

					xyz = valuesDict[u"PosXYZ"]
					try:
						xyz = xyz.split(u",")
						if len(xyz) == 3:
							self.RPI[thisPi][u"PosX"] = float(xyz[0]) * self.distanceUnits
							self.RPI[thisPi][u"PosY"] = float(xyz[1]) * self.distanceUnits
							self.RPI[thisPi][u"PosZ"] = float(xyz[2]) * self.distanceUnits
					except Exception, e:
						self.indiLOG.log(40,"Line {} has error={}".format(sys.exc_traceback.tb_lineno, e))
						self.indiLOG.log(40,u"bad input for xyz-coordinates:{}".format(valuesDict[u"PosXYZ"]) )

					self.executeUpdateStatesDict(calledFrom="validateDeviceConfigUi RPI")
					self.updateNeeded += " fixConfig "
					self.saveConfig(only="RPIconf")

					return (True, valuesDict)
				except Exception, e:
					self.indiLOG.log(40,"setting up RPI Line {} has error={}".format(sys.exc_traceback.tb_lineno, e))
					valuesDict, errorDict  = self.setErrorCode(valuesDict,errorDict,  "pgm error, check log")
					return ( False, valuesDict, errorDict )


				
	
############ RPI- sensors  -------
			if typeId == "rPI-Sensor":
				try: 
					self.RPI[piU][u"piOnOff"] 				= "1"
					self.RPI[thisPi][u"piDevId"] 			= devId
					self.RPI[thisPi]["userIdPi"] 			= valuesDict["newuserIdPi"]
					self.RPI[thisPi]["passwordPi"] 			= valuesDict["newpasswordPi"]
					self.RPI[thisPi]["authKeyOrPassword"]	= valuesDict[u"newauthKeyOrPassword"]  
					self.RPI[thisPi]["enableRebootCheck"]	= valuesDict[u"newenableRebootCheck"]  
					valuesDict["passwordPi"]				= valuesDict["newpasswordPi"]
					valuesDict["userIdPi"] 					= valuesDict["newuserIdPi"]
					self.RPI[thisPi][u"ipNumberPi"]			= valuesDict["newIPNumber"]
					valuesDict["ipNumberPi"] 				= valuesDict["newIPNumber"]
					valuesDict[u"address"] 					= "Pi-{}".format(thisPi)
					valuesDict[u"description"] 				= "Pi-{}-{}".format(thisPi, valuesDict["newIPNumber"])
					self.RPI[thisPi][u"sendToIndigoSecs"]	= valuesDict[u"sendToIndigoSecs"]
					self.RPI[thisPi][u"sensorRefreshSecs"]	= valuesDict[u"sensorRefreshSecs"]
					self.RPI[thisPi][u"deltaChangedSensor"]	=  valuesDict[u"deltaChangedSensor"]
					self.setONErPiV(thisPi,"piUpToDate", [u"updateParamsFTP"])
					self.rPiRestartCommand[int(thisPi)] 	= "master"
					self.updateNeeded 					   += " fixConfig "
					self.saveConfig(only="RPIconf")
					return (True, valuesDict)
				except Exception, e:
					self.indiLOG.log(40,"setting up RPI-Sensor Line {} has error={}".format(sys.exc_traceback.tb_lineno, e))
					valuesDict, errorDict  = self.setErrorCode(valuesDict,errorDict,  "pgm error, check log")
					return ( False, valuesDict, errorDict )


############ beacons  -------
			if typeId == "beacon":
				try:
					newMAC = valuesDict[u"newMACNumber"].upper()
					if u"address" not in props: 
						new = True
						beacon = newMAC
					else:						new = False
					newMAC = valuesDict[u"newMACNumber"].upper()
					valuesDict[u"newMACNumber"] = newMAC
					if self.isValidMAC(newMAC):
						if beacon != newMAC:
							self.indiLOG.log(20, u"replacing beacon mac "+beacon+u" with "+newMAC)
							if beacon !="xx" and beacon in self.beacons:
								self.indiLOG.log(20, u"replacing existing beacon")
								self.beacons[newMAC]	= copy.deepcopy(self.beacons[beacon])
								self.beacons[beacon][u"indigoId"] = 0
								self.newADDRESS[devId]	= newMAC
								props[u"address"]= self.newADDRESS[devId]
								self.deviceStopCommIgnore = time.time()
								dev.replacePluginPropsOnServer(props)
								dev = indigo.devices[devId]
								props = dev.pluginProps
							else:
								self.indiLOG.log(20, u"creating a new beacon")
								self.beacons[newMAC]	= copy.deepcopy(_GlobalConst_emptyBeacon)
								self.newADDRESS[devId]	= newMAC
								valuesDict[u"address"]		= newMAC
								self.deviceStopCommIgnore = time.time()
								dev.replacePluginPropsOnServer(props)
								dev = indigo.devices[devId]
								props = dev.pluginProps
							beacon = newMAC
						elif new:
							self.indiLOG.log(20, u"creating a new beacon")
							self.beacons[newMAC]	= copy.deepcopy(_GlobalConst_emptyBeacon)
							self.newADDRESS[devId]	= newMAC
							valuesDict[u"address"]		= newMAC
							self.deviceStopCommIgnore = time.time()
							dev.replacePluginPropsOnServer(props)
							dev = indigo.devices[devId]
							props = dev.pluginProps
							beacon = newMAC
					else:
						valuesDict[u"newMACNumber"] = beacon
						valuesDict, errorDict  = self.setErrorCode(valuesDict,errorDict,  "bad Mac Number")
						return ( False, valuesDict, errorDict )
					self.beaconPositionsUpdated = 1
	
					if not self.isValidMAC(beacon):
						error = "bad Mac Number"
						valuesDict, errorDict  = self.setErrorCode(valuesDict,errorDict,  "bad Mac Number")
						return ( False, valuesDict, errorDict )
					self.beaconPositionsUpdated = 1

					if beacon in self.beacons and beacon.find("00:00:00:00") ==-1:
						self.beacons[beacon][u"expirationTime"] = float(valuesDict[u"expirationTime"])
						self.beacons[beacon][u"updateSignalValuesSeconds"] = float(valuesDict[u"updateSignalValuesSeconds"])
						self.beacons[beacon][u"beaconTxPower"] = int(valuesDict[u"beaconTxPower"])
						dev.updateStateOnServer(u"TxPowerSet",int(valuesDict[u"beaconTxPower"]))
						self.beacons[beacon][u"ignore"] = int(valuesDict[u"ignore"])

						self.beacons[beacon][u"note"] = "beacon-" + valuesDict[u"typeOfBeacon"]
						self.addToStatesUpdateDict(dev.id,"note", self.beacons[beacon][u"note"])

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
						self.setALLrPiV(u"piUpToDate", [u"updateParamsFTP"])
				except Exception, e:
					self.indiLOG.log(40,"setting up iBeacon Line {} has error={}".format(sys.exc_traceback.tb_lineno, e))
					valuesDict, errorDict  = self.setErrorCode(valuesDict,errorDict,  "pgm error, check log")
					return ( False, valuesDict, errorDict )




############ RPI- BLEconnect  -------
			if typeId ==u"BLEconnect":
				try:
					if len(valuesDict[u"macAddress"]) == len(u"01:02:03:04:05:06"):
						dev.updateStateOnServer(u"TxPowerSet",int(valuesDict[u"beaconTxPower"]))
						valuesDict[u"macAddress"] = valuesDict[u"macAddress"].upper()
					else:
						valuesDict, errorDict  = self.setErrorCode(valuesDict,errorDict,  "bad Mac Number")
						return ( False, valuesDict, errorDict )
					BLEMAC = valuesDict[u"macAddress"].upper()

					active=""
					for piU in _rpiBeaconList:
						pi = int(piU)
						if valuesDict[u"rPiEnable"+piU]:
							if typeId not in self.RPI[piU][u"input"]:
								self.RPI[piU][u"input"][typeId]={}
							if unicode(devId) not in self.RPI[piU][u"input"][typeId]:
								self.RPI[piU][u"input"][typeId][unicode(devId)]=""
							self.RPI[piU][u"input"][typeId][unicode(devId)] = BLEMAC
							active+=" "+piU+","
						else:
							if typeId in self.RPI[piU][u"input"] and  unicode(devId) in self.RPI[piU][u"input"][typeId]:
								del	 self.RPI[piU][u"input"][typeId][unicode(devId)]
						valuesDict[u"description"] = "on Pi "+ active
						valuesDict[u"address"] = BLEMAC

						### remove if not un this pi:
						if typeId in self.RPI[piU][u"input"] and self.RPI[piU][u"input"][typeId] == {}:
							del self.RPI[piU][u"input"][typeId]
						if typeId not in self.RPI[piU][u"input"] and typeId in self.RPI[piU][u"sensorList"]:
								self.RPI[piU][u"sensorList"] = self.RPI[piU][u"sensorList"].replace(typeId+",","")

						if True:
							self.rPiRestartCommand[pi] +="BLEconnect,"
							self.updateNeeded += " fixConfig "
							self.setONErPiV(piU,"piUpToDate", [u"updateParamsFTP"])
					return (True, valuesDict)
				except Exception, e:
					self.indiLOG.log(40,"setting up BLEconnect Line {} has error={}".format(sys.exc_traceback.tb_lineno, e))
					valuesDict, errorDict  = self.setErrorCode(valuesDict,errorDict,  "pgm error, check log")
					return ( False, valuesDict, errorDict )



###########  sensors --------
			if typeId.find(u"INPUTRotatary")>-1 :
				active = ""
				update = 0

				piU = valuesDict[u"piServerNumber"]
				pi  = int(piU)
				for piU0 in self.RPI:
					if piU == piU0:											  continue
					if u"input" not in self.RPI[piU0]:						  continue
					if typeId not in self.RPI[piU0][u"input"]:				  continue
					if unicode(devId) not in self.RPI[piU0][u"input"][typeId]:continue
					del self.RPI[piU0][u"input"][typeId][unicode(devId)]
					self.setONErPiV(piU0,"piUpToDate",[u"updateParamsFTP"])
					self.rPiRestartCommand[int(piU0)] += typeId+","
					update = 1

				if pi >= 0:
					if u"piServerNumber" in props:
						if pi != int(props[u"piServerNumber"]):
							self.setONErPiV(piU,"piUpToDate",[u"updateParamsFTP"])
							self.rPiRestartCommand[int(props[u"piServerNumber"])] += typeId+","
							update = 1
					self.setONErPiV(piU,"piUpToDate", [u"updateParamsFTP"])
					self.rPiRestartCommand[pi] += typeId+","

				pinMappings = "GPIOs:"
				for jj in range(10):
					if "INPUT_"+unicode(jj) in valuesDict:
						pinMappings+= valuesDict["INPUT_"+unicode(jj)]+", "
				valuesDict[u"description"] = pinMappings.strip(", ")



			if typeId.find(u"INPUTgpio")>-1 or typeId.find(u"INPUTtouch")>-1:
				if typeId.find(u"INPUTgpio")>-1:	typeINPUT = "INPUTgpio"
				if typeId.find(u"INPUTtouch")>-1:	typeINPUT = "INPUTtouch"

				active = ""
				update = 0

				piU = valuesDict[u"piServerNumber"]
				pi  = int(piU)
				for piU0 in self.RPI:
					if piU == piU0:											  continue
					if u"input" not in self.RPI[piU0]:						  continue
					if typeId not in self.RPI[piU0][u"input"]:				  continue
					if unicode(devId) not in self.RPI[piU0][u"input"][typeId]:continue
					del self.RPI[piU0][u"input"][typeId][unicode(devId)]
					self.setONErPiV(piU0,"piUpToDate",[u"updateParamsFTP"])
					self.rPiRestartCommand[int(piU0)] += typeINPUT+","
					update = 1

				if pi >= 0:
					if u"piServerNumber" in props:
						if pi != int(props[u"piServerNumber"]):
							self.setONErPiV(piU,"piUpToDate",[u"updateParamsFTP"])
							self.rPiRestartCommand[int(props[u"piServerNumber"])] += typeINPUT+","
							update = 1
					self.setONErPiV(piU,"piUpToDate", [u"updateParamsFTP"])
					self.rPiRestartCommand[pi] += typeINPUT+","

				if typeId not in self.RPI[piU][u"input"]:
						self.RPI[piU][u"input"][typeId] = {}
						update = 1
				if unicode(devId) not in self.RPI[piU][u"input"][typeId]:
					self.RPI[piU][u"input"][typeId][unicode(devId)] = []
					update = 1
				newDeviceDefs = json.loads(valuesDict[u"deviceDefs"])

				try:
					if len(newDeviceDefs) != len(self.RPI[piU][u"input"][typeId][unicode(devId)]):
						update = 1
					for n in range(len(newDeviceDefs)):
						if update == 1: break
						for item in newDeviceDefs[n]:
							if newDeviceDefs[n][item] != self.RPI[piU][u"input"][typeId][unicode(devId)][n][item]:
								update = 1
								break
				except:
					update = 1

				self.RPI[piU][u"input"][typeId][unicode(devId)] = newDeviceDefs

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
							pinMappings += "(u" + unicode(n) + ":" + newDeviceDefs[n][u"gpio"]+ "," + newDeviceDefs[n][u"count"] + ");"
				valuesDict[u"description"] = pinMappings

				if update == 1:
					self.rPiRestartCommand[pi] += typeINPUT+","
					self.updateNeeded += " fixConfig "
					self.setONErPiV(piU,"piUpToDate", [u"updateParamsFTP"])

				if valuesDict["count"]  == "off":
					valuesDict["SupportsOnState"]		= True
					valuesDict["SupportsSensorValue"]	= False
				else:
					valuesDict["SupportsOnState"]		= False
					valuesDict["SupportsSensorValue"]	= True


				valuesDict[u"piDone"]		= False
				valuesDict[u"stateDone"]	= False
				dev.replaceOnServer()
				self.indiLOG.log(20, u" piUpToDate pi: " +piU+ "    value:"+ unicode(self.RPI[piU][u"piUpToDate"]))
				self.indiLOG.log(20, unicode(valuesDict) )
				return (True, valuesDict)


	 

			if typeId.find(u"OUTPUTgpio-") > -1 or typeId.find(u"OUTPUTi2cRelay") > -1:
				self.indiLOG.log(20,"into validate relay")
				update = 0
				active = ""
				piU = (valuesDict[u"piServerNumber"])
				for piU0 in self.RPI:
					if piU == piU0:												continue
					if u"output" not in self.RPI[piU0]:							continue
					if typeId not in self.RPI[piU0][u"output"]:					continue
					if unicode(devId) not in self.RPI[piU0][u"output"][typeId]: continue
					del self.RPI[piU0][u"output"][typeId][unicode(devId)]
					self.setONErPiV(piU0,"piUpToDate",[u"updateParamsFTP"])

				if piU >= 0:
					if u"piServerNumber" in props:
						if piU != props[u"piServerNumber"]:
							self.setONErPiV(piU,"piUpToDate", [u"updateParamsFTP"])
							update=1



				if typeId not in self.RPI[piU][u"output"]:
					self.RPI[piU][u"output"][typeId] = {}
					update = 1
				if unicode(devId) not in self.RPI[piU][u"output"][typeId]:
					self.RPI[piU][u"output"][typeId][unicode(devId)] = []
					update = 1
				new = json.loads(valuesDict[u"deviceDefs"])
				self.indiLOG.log(20,"deviceDefs:{}".format(valuesDict[u"deviceDefs"]))

				try:
					if len(new) != len(self.RPI[piU][u"output"][typeId][unicode(devId)]):
						update = 1
					for n in range(len(new)):
						if update == 1: break
						for item in new[n]:
							if new[n] != self.RPI[piU][u"output"][typeId][unicode(devId)][n][item]:
								update = 1
								break
				except:
					update = 1

				self.RPI[piU][u"output"][typeId][unicode(devId)] = new

				if typeId.find(u"OUTPUTi2cRelay") ==-1: pinMappings ="(#,gpio,type,init)"
				else:									pinMappings ="(ch#,type,init)"
				for n in range(len(new)):
					if u"gpio" in new[n]:
						pinMappings += "(u" + unicode(n) + ":" + new[n][u"gpio"]+"," + new[n][u"outType"] +"," +  new[n][u"initialValue"]  +");"
					else:
						pinMappings += "(u" + unicode(n) + ":-);"
					if "inverse" in dev.states:
						if (dev.states["inverse"]) != (new[n][u"outType"]=="1"): 
							dev.updateStateOnServer("inverse", new[n][u"outType"]=="1" )
					elif "inverse_{:2d}".format(n) in dev.states:
						if (dev.states["inverse_{:2d}".format(n)]) != (new[n][u"outType"]=="1"): dev.updateStateOnServer("inverse_{:2d}".format(n), new[n][u"outType"]=="1" )
					if "initial" in dev.states:
						if dev.states["initial"] != new[n][u"initialValue"]: dev.updateStateOnServer("initial", new[n][u"initialValue"])
					elif "initial{:2d}".format(n) in dev.states:
						if dev.states["initial{:2d}".format(n)] != new[n][u"initialValue"]: dev.updateStateOnServer("initial{:2d}".format(n), new[n][u"initialValue"] )
					
				valuesDict[u"description"] = pinMappings

				if update == 1:
					self.rPiRestartCommand[int(piU)] += typeId+","
					self.updateNeeded += " fixConfig "
					self.setONErPiV(piU,"piUpToDate", [u"updateParamsFTP"])

				valuesDict[u"piDone"] = False
				valuesDict[u"stateDone"] = False
				dev.replaceOnServer()
				return (True, valuesDict)



			if typeId in _GlobalConst_allowedSensors:
				update = 0
				piU = valuesDict[u"piServerNumber"]
				pi = int(piU)
				if pi >= 0:
					if u"piServerNumber" in props:
						if piU != props[u"piServerNumber"]:
							self.updateNeeded += " fixConfig "
							self.rPiRestartCommand[pi] += "master,"
							self.rPiRestartCommand[int(props[u"piServerNumber"])] += "master,"
							self.setONErPiV(props[u"piServerNumber"],"piUpToDate",[u"updateParamsFTP"])

					valuesDict[u"address"] = "PI-" + piU
					if typeId not in self.RPI[piU][u"input"]:
						self.RPI[piU][u"input"][typeId] = {}
						self.rPiRestartCommand[pi] += "master,"
						self.updateNeeded += " fixConfig "

					if unicode(dev.id) not in self.RPI[piU][u"input"][typeId]:
						self.RPI[piU][u"input"][typeId][unicode(dev.id)]={}
						self.updateNeeded += " fixConfig "
					self.setONErPiV(piU,"piUpToDate", [u"updateParamsFTP"])


				if u"BLEsensor" == typeId :
					valuesDict[u"description"] = valuesDict[u"type"] +"-"+ valuesDict[u"mac"]


				if u"launchpgm" == typeId :
					valuesDict[u"description"] =  "pgm: "+valuesDict[u"launchCommand"]


				if	typeId	in ["mhzCO2"]:
					dev.updateStateOnServer("CO2calibration",valuesDict["CO2normal"])


				if	typeId	=="rainSensorRG11":
						valuesDict[u"description"] = "INP:"+valuesDict[u"gpioIn"]+"-SW5:"+valuesDict[u"gpioSW5"]+"-SW2:"+valuesDict[u"gpioSW2"]+"-SW1:"+valuesDict[u"gpioSW1"]+"-SW12V:"+valuesDict[u"gpioSWP"]


				if	typeId =="pmairquality":
					if valuesDict[u"resetPin"] !="-1" and valuesDict[u"resetPin"] !="":
						valuesDict[u"description"] = "reset-GPIO: " +valuesDict[u"resetPin"]
					else:
						valuesDict[u"description"] = "reset-GPIO not used"

				if	typeId =="lidar360":
						valuesDict[u"description"] = "MotorFrq: {}Hz; {}º in 1 bin; {}; MinSignal: {}".format( int(10*float(valuesDict[u"motorFrequency"])), valuesDict[u"anglesInOneBin"], valuesDict[u"usbPort"],  valuesDict[u"minSignalStrength"]) 


				if	typeId =="Wire18B20" : # update serial number in states in case we jumped around with dev types. 
					if len(dev.states["serialNumber"]) < 5  and dev.description.find("sN= 28")>-1:
						dev.updateStateOnServer("serialNumber", dev.description.split("sN= ")[1])

				if	typeId.find(u"DHT") >-1:
					if u"gpioPin" in valuesDict:
						valuesDict[u"description"] = "GPIO-PIN: " +valuesDict[u"gpioPin"]+"; type: "+valuesDict[u"dhtType"]

				if ("i2c" in typeId.lower() or typeId in _GlobalConst_i2cSensors) or "interfaceType" in valuesDict:  
					if "interfaceType" in valuesDict and valuesDict[u"interfaceType"] == "i2c":
						if "i2cAddress" in valuesDict:
							try:
								addrhex = "=#"+hex(int(valuesDict[u"i2cAddress"]))
							except:
								addrhex =""
							if u"useMuxChannel" in valuesDict and valuesDict[u"useMuxChannel"] !="-1":
									valuesDict[u"description"] = "i2c: " +valuesDict[u"i2cAddress"]+addrhex +u"; mux-channel: "+valuesDict[u"useMuxChannel"]
							else:
									valuesDict[u"description"] = "i2c: " +valuesDict[u"i2cAddress"]+addrhex
						
					elif "interfaceType" in valuesDict and valuesDict[u"interfaceType"] == "serial":
						valuesDict[u"description"] = "serial port vers."

					else:
						if "i2cAddress" in valuesDict:
							try:
								addrhex = "=#"+hex(int(valuesDict[u"i2cAddress"]))
							except:
								addrhex =""
							if u"useMuxChannel" in valuesDict and valuesDict[u"useMuxChannel"] !="-1":
									valuesDict[u"description"] = "i2c: " +valuesDict[u"i2cAddress"]+addrhex +u"; mux-channel: "+valuesDict[u"useMuxChannel"]
							else:
									valuesDict[u"description"] = "i2c: " +valuesDict[u"i2cAddress"]+addrhex

				if typeId.find(u"bme680") >-1:
					if   valuesDict["calibrateSetting"] == "setFixedValue": valuesDict[u"description"] += ", set calib to "+ valuesDict[u"setCalibrationFixedValue"]
					elif valuesDict["calibrateSetting"] == "readFromFile":	valuesDict[u"description"] += ", set calib to read from file"
					else:											        valuesDict[u"description"] += ", recalib if > "+valuesDict["recalibrateIfGT"]+"%"
				if typeId.find(u"moistureSensor") >-1:
					valuesDict[u"description"] +=  ";"+valuesDict[u"minMoisture"]+"<V<"+ valuesDict[u"maxMoisture"]

				if typeId in [u"PCF8591","ADS1x15"]:
					if "input" 		in valuesDict:  			 		valuesDict[u"description"] 	+= " C#="+valuesDict[u"input"]+";"
					if "resModel" 	in valuesDict:  			 		valuesDict[u"description"] 	+= "M="+valuesDict[u"resModel"]+";"
					if "gain" 		in valuesDict:  			 		valuesDict[u"description"] 	+= "G="+valuesDict[u"gain"]+";"
					try: 
						o = float(valuesDict[u"offset"])
						if o != 0.:
							if o > 0: 	 								valuesDict[u"description"] 	+= "+"+valuesDict[u"offset"]+";"
							else:									 	valuesDict[u"description"] 	+=     valuesDict[u"offset"]+";"
					except: pass
					try: 
						m = float(valuesDict[u"mult"])
						if m != 1.: 	 								valuesDict[u"description"] 	+= "*"+valuesDict[u"mult"]+";"
					except: pass
					if valuesDict[u"resistorSensor"]	== "ground":	valuesDict[u"description"] 	+= "RG="+valuesDict[u"feedResistor"]+";V="+valuesDict[u"feedVolt"]+";"
					if valuesDict[u"resistorSensor"]	== "V+": 		valuesDict[u"description"] 	+= "R+="+valuesDict[u"feedResistor"]+";V="+valuesDict[u"feedVolt"]+";"
					if valuesDict[u"maxMin"] 			== "1":		 	valuesDict[u"description"] 	+= ""+valuesDict[u"MINRange"]+";<V<"+valuesDict[u"MAXRange"]+";"
					if valuesDict[u"valueOrdivValue"]	== "1/value":	valuesDict[u"description"] 	+= "1/v;"
					if valuesDict[u"logScale"] 			== "1":  	 	valuesDict[u"description"] 	+= "LOG"+";"
					try: 
						o = float(valuesDict[u"offset2"])
						if o != 0.:
							if o > 0: 	 								valuesDict[u"description"] 	+= "+"+valuesDict[u"offset2"]+";"
							else:										valuesDict[u"description"] 	+=     valuesDict[u"offset2"]+";"
					except: pass
					try: 
						m = float(valuesDict[u"mult"])
						if m != 1.:										valuesDict[u"description"] 	+= "*"+valuesDict[u"mult"]+";"
					except: pass
					if valuesDict[u"format"] 			!= "":  		valuesDict[u"description"] 	+= "F="+valuesDict[u"format"]+";"
					if valuesDict[u"unit"] 				!= "":   		valuesDict[u"description"] 	+= "U="+valuesDict[u"unit"]+";"
					valuesDict[u"description"] = valuesDict[u"description"].strip(";")

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
					if typeId not in self.RPI[piU][u"input"]:
						self.RPI[piU][u"input"][typeId] = {}
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
					pinMappings = "gpio="+valuesDict[u"gpio"]+ "," +valuesDict[u"risingOrFalling"]+ " Edge, " +valuesDict[u"deadTime"]+ "secs deadTime"
					valuesDict[u"description"] = pinMappings


				if "INPUTcoincidence" == typeId :
					theText = "coincidenceWindow = {} msecs".format(valuesDict[u"coincidenceTimeInterval"])
					valuesDict[u"description"] = theText

				self.setONErPiV(piU,"piUpToDate", [u"updateParamsFTP"])
				self.updateNeeded += " fixConfig "
				valuesDict[u"MSG"] =error
				if error ==u"":
					self.updateNeeded += " fixConfig "
					self.setONErPiV(piU,"piUpToDate", [u"updateParamsFTP"])
					return (True, valuesDict)
				else:
					self.indiLOG.log(40, u"validating device error:" +error+"     fields:"+unicode(valuesDict))
					valuesDict, errorDict  = self.setErrorCode(valuesDict,errorDict,  error)
					return ( False, valuesDict, errorDict )


			if typeId in _GlobalConst_allowedOUTPUT:
				if typeId==u"neopixel-dimmer":
					try:
						neopixelDevice = indigo.devices[int(valuesDict[u"neopixelDevice"])]
						propsX = neopixelDevice.pluginProps
						piU = propsX[u"piServerNumber"]
						pi = int(piU)
						self.rPiRestartCommand[pi] += "neopixel,"
						self.setONErPiV(piU,"piUpToDate", [u"updateParamsFTP"]) 
						valuesDict[u"address"] = neopixelDevice.name
						try: 
							xxx= propsX[u"devType"].split(u"x")
							ymax = int(xxx[0])
							xmax = int(xxx[1])
						except:
							valuesDict, errorDict  = self.setErrorCode(valuesDict,errorDict,  "devtype not defined for neopixel" )
							return ( False, valuesDict, errorDict )

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


					except Exception, e:
						if unicode(e).find(u"timeout waiting") > -1:
							self.indiLOG.log(40,"Line {} has error={}".format(sys.exc_traceback.tb_lineno, e))
							self.indiLOG.log(40,u"communication to indigo is interrupted")
						valuesDict, errorDict  = self.setErrorCode(valuesDict,errorDict,  unicode(e) )
						return ( False, valuesDict, errorDict )

				elif typeId==u"neopixel":
					try:
						piU = valuesDict[u"piServerNumber"]
						pi = int(piU)
						self.rPiRestartCommand[pi] += "neopixel,"
						valuesDict[u"address"]		 = "Pi-"+valuesDict[u"piServerNumber"]
						valuesDict[u"devType"]		 = valuesDict[u"devTypeROWs"] +"x"+valuesDict[u"devTypeLEDs"]
						valuesDict[u"description"]	 = "type="+valuesDict[u"devType"]
						self.setONErPiV(piU,"piUpToDate", [u"updateParamsFTP"]) 
					except:
						pass
				elif typeId==u"sundial":
					try:
						piU = valuesDict[u"piServerNumber"]
						pi = int(piU)
						self.rPiRestartCommand[pi] += "sundial,"
						valuesDict[u"address"]		 = "Pi-"+valuesDict[u"piServerNumber"]
						valuesDict[u"description"]	 = "TZ="+valuesDict[u"timeZone"]+"; motorType"+valuesDict[u"motorType"]
						self.setONErPiV(piU,"piUpToDate", [u"updateParamsFTP"]) 
					except:
						pass
				elif typeId==u"setStepperMotor":
					try:
						piU = valuesDict[u"piServerNumber"]
						pi = int(piU)
						self.rPiRestartCommand[pi] += "sundial,"
						valuesDict[u"address"]		 = "Pi-"+valuesDict[u"piServerNumber"]
						valuesDict[u"description"]	 = "motorTypes: "+valuesDict[u"motorType"]
						self.setONErPiV(piU,"piUpToDate", [u"updateParamsFTP"]) 
					except:
						pass
				else:
					piU = valuesDict[u"piServerNumber"]
					pi = int(piU)
					valuesDict[u"address"] = "PI-" + piU
					if pi >= 0:
						if u"piServerNumber" in props:
							if pi != int(props[u"piServerNumber"]):
								self.updateNeeded += " fixConfig "
						cAddress = ""
						devType=""

						if u"devType" in valuesDict:
							devType = valuesDict[u"devType"]

						if u"output" not in			self.RPI[piU]:  
							self.RPI[piU][u"output"]={}
						if typeId not in			self.RPI[piU][u"output"]:  
							self.RPI[piU][u"output"][typeId]={}
						if unicode(devId) not in	self.RPI[piU][u"output"][typeId]:  
							self.RPI[piU][u"output"][typeId][unicode(devId)]={}

						if u"i2cAddress" in valuesDict:
							cAddress = valuesDict[u"i2cAddress"]
							self.RPI[piU][u"output"][typeId][unicode(devId)] = [{u"i2cAddress":cAddress},{u"devType":devType}]

						elif "spiAddress" in valuesDict:
							cAddress = unicode(int(valuesDict[u"spiAddress"]))
							self.RPI[piU][u"output"][typeId][unicode(devId)] = [{u"spi":cAddress},{u"devType":devType}]

						self.updateNeeded += " fixConfig "
						self.rPiRestartCommand[pi] += "receiveGPIOcommands,"
						self.setONErPiV(piU,"piUpToDate", [u"updateParamsFTP"])


						if typeId == u"display":
							valuesDict = self.fixDisplayProps(valuesDict,typeId,devType)

							self.rPiRestartCommand[pi] += "display,"
							self.setONErPiV(piU,"piUpToDate", [u"updateAllFilesFTP"]) # this will send images and fonts too
							valuesDict,error = self.addBracketsPOS(valuesDict,"pos1")
							if error ==u"":
								valuesDict,error = self.addBracketsPOS(valuesDict,"pos2")
								if error ==u"":
									valuesDict,error = self.addBracketsPOS(valuesDict,"pos3")

							if devType == "screen":
								valuesDict[u"description"] = "res: {}".format(valuesDict["displayResolution"])

						if typeId==u"OUTPUTxWindows":
							self.rPiRestartCommand[pi] += "xWindows,"
							self.setONErPiV(piU,"piUpToDate", [u"updateParamsFTP"]) # this will send images and fonts too
							valuesDict[u"description"]	 = "GUI: "+valuesDict[u"xWindows"]


						if typeId==u"setTEA5767":
							dev = indigo.devices[devId]
							self.setONErPiV(piU,"piUpToDate", [u"updateParamsFTP"]) # this will send config only
							self.addToStatesUpdateDict(devId,"status"   ,"f= "+valuesDict[u"defFreq"] + "; mute= " +valuesDict[u"mute"])
							self.addToStatesUpdateDict(devId,"frequency",valuesDict[u"defFreq"] )
							self.addToStatesUpdateDict(devId,"mute"     ,valuesDict[u"mute"])
							self.executeUpdateStatesDict(onlyDevID=unicode(devId),calledFrom="validateDeviceConfigUi set TEA")
							self.devUpdateList[unicode(devId)] = True

			else:
				pass
			valuesDict[u"MSG"] =error
			if error == u"":
				self.updateNeeded += " fixConfig "
				return (True, valuesDict)
			else:
				valuesDict, errorDict  = self.setErrorCode(valuesDict,errorDict,  error )
				return ( False, valuesDict, errorDict )


		except Exception, e:
			self.indiLOG.log(40,"Line {} has error={}".format(sys.exc_traceback.tb_lineno, e))
			if unicode(e).find(u"timeout waiting") > -1:
				valuesDict, errorDict  = self.setErrorCode(valuesDict,errorDict,  "communication to indigo is interrupted")
			else:
				valuesDict, errorDict  = self.setErrorCode(valuesDict,errorDict, "please fill out all fields")
			return ( False, valuesDict, errorDict )

		self.updateNeeded += " fixConfig "
		valuesDict, errorDict = self.setErrorCode(valuesDict,errorDict,  "  ??   error .. ?? " ) 
		return ( False, valuesDict, errorDict )




####-------------------------------------------------------------------------####
	def setErrorCode(self,valuesDict,errorDict, error):
		valuesDict[u"MSG"] = error
		errorDict[u"MSG"]  = error
		self.indiLOG.log(40,"validateDeviceConfigUi "+error)
		return   valuesDict, errorDict


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
					self.indiLOG.log(40,"Line {} has error={}".format(sys.exc_traceback.tb_lineno, e))
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
		except Exception, e:
			if unicode(e).find(u"timeout waiting") > -1:
				self.indiLOG.log(40,"Line {} has error={}".format(sys.exc_traceback.tb_lineno, e))
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
		self.myLog( text = dev.name+"/"+unicode(devId)+" -------------------------------",mType="printing dev info for" )
		props=dev.pluginProps
		states=dev.states
		self.myLog( text = u"\n"+unicode(props),mType="props:")
		self.myLog( text = u"\n"+unicode(states),mType="states:")
		try:  self.myLog( text = dev.description,mType="description:")
		except: pass
		try:  self.myLog( text = dev.address,mType="address:")
		except: pass
		try:  self.myLog( text = dev.deviceTypeId,mType="deviceTypeId:")
		except: pass
		try:  self.myLog( text = unicode(dev.enabled),mType="enabled:")
		except: pass
		try:  self.myLog( text = dev.model,mType="model:")
		except: pass
		if u"piServerNumber" in props:
			if props[u"piServerNumber"]!="":
				pi= int(props[u"piServerNumber"])
				piU = unicode(pi)
				self.myLog( text = u"\n"+self.writeJson(self.RPI[piU], fmtOn=True ),mType="RPI info:")
		else:
			for piU in _rpiBeaconList:
				if u"rPiEnable"+piU in props:
					self.myLog( text =	u"\n"+self.writeJson(self.RPI[piU], fmtOn=True ),mType="RPI info:")


		return valuesDict

####-------------------------------------------------------------------------####
	def printBLEreportCALLBACK(self, valuesDict=None, typeId=""):

		self.setCurrentlyBooting(80, setBy="printBLEreportCALLBACK")
		piU = valuesDict[u"configurePi"]
		if piU ==u"": return
		out= json.dumps([{u"command":"BLEreport"}])
		self.presendtoRPI(piU,out)

		return valuesDict


####-------------------------------------------------------------------------####
	def buttonConfirmchangeLogfile(self, valuesDict=None, typeId="", devId=0):
		self.myLog( text = u"  starting to modify "+self.indigoPath + 'IndigoWebServer/indigopy/indigoconn.py')
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
			self.indiLOG.log(20, u"....modified version already inplace, do nothing")
			return valuesDict

		if os.path.isfile(self.indigoPath + 'IndigoWebServer/indigopy/indigoconn.py.original'):
			os.remove(self.indigoPath + 'IndigoWebServer/indigopy/indigoconn.py.original')
		os.rename(self.indigoPath + 'IndigoWebServer/indigopy/indigoconn.py',
				  self.indigoPath + 'IndigoWebServer/indigopy/indigoconn.py.original')
		os.rename(self.indigoPath + 'IndigoWebServer/indigopy/indigoconn.py-1',
				  self.indigoPath + 'IndigoWebServer/indigopy/indigoconn.py')
		self.indiLOG.log(20, u"/Library/Application Support/Perceptive Automation/Indigo x/IndigoWebServer/indigopy/indigoconn.py has been replace with modified version(logging suppressed)")
		self.indiLOG.log(20, u"  the original has been renamed to indigoconn.py.original, you will need to restart indigo server to activate new version")
		self.indiLOG.log(20, u"  to go back to the original version replace/rename the new version with the saved .../IndigoWebServer/indigopy/indigoconn.py.original file")

		return valuesDict

####-------------------------------------------------------------------------####
	def buttonConfirmReversechangeLogfile(self, valuesDict=None, typeId="", devId=0):

		if os.path.isfile(self.indigoPath + 'IndigoWebServer/indigopy/indigoconn.py.original'):
			os.remove(self.indigoPath + 'IndigoWebServer/indigopy/indigoconn.py')
			os.rename(self.indigoPath + 'IndigoWebServer/indigopy/indigoconn.py.original',
				  self.indigoPath + 'IndigoWebServer/indigopy/indigoconn.py')
			self.indiLOG.log(20, u"/Library/Application Support/Perceptive Automation/Indigo x/IndigoWebServer/indigopy/indigoconn.py.original has been restored")
			self.indiLOG.log(20, u" you will need to restart indigo server to activate new version")
		else:
			self.indiLOG.log(20, u"no file ... indigopy.py.original found to restore")

		return valuesDict


####-------------------------------------------------------------------------####
	def setALLrPiV(self, item, value, resetQueue =False):
		for piU in self.RPI:
			self.setONErPiV(piU, item, value, resetQueue=resetQueue)
		return	  

####-------------------------------------------------------------------------####
	def setONErPiV(self,piU, item, value, resetQueue=False):
		try:
			if piU in self.RPI:
				if resetQueue:
					self.resetUpdateQueue(piU)
				if self.RPI[piU][u"ipNumberPi"] != "":
					if self.RPI[piU][u"piOnOff"] == "1":
						if value ==u"" or value ==[] or value ==[u""] or isinstance(self.RPI[piU][item], ( int, long ) ) or isinstance(self.RPI[piU][item],(str, unicode)):
							self.RPI[piU][item]=[]
						else:
							for v in value:
								if v not in self.RPI[piU][item]:
									self.RPI[piU][item].append(v)
			return
		except Exception, e:
			self.indiLOG.log(40,"Line {} has error={}".format(sys.exc_traceback.tb_lineno, e))


####-------------------------------------------------------------------------####
	def removeAllPiV(self, item, value):
		for piU in self.RPI:
			self.removeONErPiV(piU, item, value)
		return	  

####-------------------------------------------------------------------------####
	def removeONErPiV(self,pix, item, value):
		piU = unicode(pix)
		if piU in self.RPI:
			for v in value:
				vv = v.split(".exp")[0]
				if vv in self.RPI[piU][item]:
					self.RPI[piU][item].remove(vv)


		return

####-------------------------------------------------------------------------####
	def filterAllpiSimple(self, filter="", valuesDict=None, typeId="", devId=""):
		xList=[]
		for piU in _rpiList:
			name = ""
			try:
				devId= int(self.RPI[piU][u"piDevId"])
				if devId >0:
					name= "-"+indigo.devices[devId].name
			except: pass
			xList.append((piU,"#"+piU+"-"+self.RPI[piU][u"ipNumberPi"]+name))
		return xList

####-------------------------------------------------------------------------####
	def filterNeopixelDevice(self, filter="", valuesDict=None, typeId="", devId=""):
		xList=[(u"0", u"not active")]
		return xList

####-------------------------------------------------------------------------####
	def filterNeopixelType(self, filter="", valuesDict=None, typeId="", devId=""):
		xList=[(u"0", u"not active")
			 ,(u"line"		 , u"LINE  enter left and right end")
			 ,(u"sPoint"	 , u"ONE	  POINT	 ")
			 ,(u"points"	 , u"MULTIPLE POINTS ")
			 ,(u"rectangle"	 , u"RECTANGLE ")
			 ,(u"image"		 , u"IMAGE	not implemnted yet")
			 ,(u"matrix"	 , u"MATRIX enter only RGB values for EACH point ")
			 ,(u"thermometer", u"THERMOMETER enter start, end pixels and color delta")
			 ,(u"NOP"		 , u"No operation, use to wait before next action")
			 ,(u"exec"		 , u"execute , not implemened yet")]
		return xList


####-------------------------------------------------------------------------####
	def filterLightSensorOnRpi(self, filter="", valuesDict=None, typeId="", devId=""):
		xList=[]
		for dev in indigo.devices.iter("props.isSensorDevice"):
			if dev.deviceTypeId in _GlobalConst_lightSensors: 
				xList.append((str(dev.id)+"-"+dev.deviceTypeId, dev.name.encode("utf8")))

		return xList



####-------------------------------------------------------------------------####
	def filterDisplayType(self, filter="", valuesDict=None, typeId="", devId=""):
		xList=[(u"0", u"not active")
			 ,(u"text"			, u"text: eg %%d:sensorX:input%%[mV]  .. you can also use %%eval:%3.1f%(float(%%d:123:state:%%))%%[mV]")
			 ,(u"textWformat"	, u"text: with format string eg %%v:123%%%%FORMAT:%3.1f[mV]; only for numbers")
			 ,(u"date"			, u"date:  %Y-%m-%d full screen")
			 ,(u"clock"			, u"clock: %H:%M full screen")
			 ,(u"dateString"	, u"date time: string format eg %HH:%M:%S")
			 ,(u"line"			, u"line [Xstart,Ystart,Xend,Yend], width")
			 ,(u"point"			, u"point-s: ([[x,y],[x,y],..] ")
			 ,(u"dot"			, u"dot: [x,y] size radius or x,y size")
			 ,(u"rectangle"		, u"rectangle [Xtl,Ytl,Xrb,Yrb]")
			 ,(u"triangle"		, u"triangle [X1,Y1,X2,Y2,Y3,Y3]")
			 ,(u"ellipse"		, u"ellipse, [Xtl,Ytl,Xrb,Yrb]")
			 ,(u"image"			, u"image: file name ")
			 ,(u"vBar"			, u"vertical bar: x0, y0, L")
			 ,(u"hBar"			, u"horizontal bar: x0, y0, L")
			 ,(u"vBarwBox"		, u"vertical bar with box: x0, y0,L,value")
			 ,(u"hBarwBox"		, u"horizontal bar with box: x0, y0,L,value")
			 ,(u"labelsForPreviousObject"	    , u"ticks,labels for prev box:[LR,lineW,[[10,10],[20,""]...[]]]")
			 ,(u"hist"			, u"histogram ")
			 ,(u"NOP"			, u"No operation, use to wait before next action")
			 ,(u"exec"			, u"execute")]
		return xList


####-------------------------------------------------------------------------####
	def filterNeoPixelRings(self, filter="", valuesDict=None, typeId="", devId=""):
		xList=[(u"1", u"1")
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
		return xList


####-------------------------------------------------------------------------####
	def filter10To100(self, filter="", valuesDict=None, typeId="", devId=""):
		xList=[(u"10", u"10")
			 ,(u"20", u"20")
			 ,(u"30", u"30")
			 ,(u"40", u"40")
			 ,(u"50", u"50")
			 ,(u"60", u"60")
			 ,(u"70", u"70")
			 ,(u"80", u"80")
			 ,(u"90", u"90")
			 ,(u"100", u"100")]
		return xList

####-------------------------------------------------------------------------####
	def filterDisplayPages(self, filter="", valuesDict=None, typeId="", devId=""):
		xList=[(u"1", u"1")
			 ,(u"2", u"2")
			 ,(u"3", u"3")
			 ,(u"4", u"4")
			 ,(u"5", u"5")
			 ,(u"6", u"6")
			 ,(u"7", u"7")
			 ,(u"8", u"8")]
		return xList
	   
####-------------------------------------------------------------------------####
	def filterDisplayScrollDelay(self, filter="", valuesDict=None, typeId="", devId=""):
		xList=[(u"0.015", u"0.015 secs")
			 ,(u"0.025", u"0.025 secs")
			 ,(u"0.05" , u"0.05 secs")
			 ,(u"0.1"  , u"0.1 secs")
			 ,(u"0.2"  , u"0.2 secs")
			 ,(u"0.3"  , u"0.3 secs")
			 ,(u"0.4"  , u"0.4 secs")
			 ,(u"0.6"  , u"0.6 secs")]
		return xList
  
####-------------------------------------------------------------------------####
	def filterDisplayNumberOfRepeats(self, filter="", valuesDict=None, typeId="", devId=""):
		xList=[(u"1" , u"1")
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
		return xList

####-------------------------------------------------------------------------####
	def filterscrollDelayBetweenPages(self, filter="", valuesDict=None, typeId="", devId=""):
		xList=[(u"0", u"no delay")
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
		return xList
	   
####-------------------------------------------------------------------------####
	def filterDisplayScroll(self, filter="", valuesDict=None, typeId="", devId=""):
		xList=[(u"0"			   , u"no scrolling")
			 ,(u"left"		   , u"scroll to left ")
			 ,(u"right"		   , u"scroll to right")
			 ,(u"up"		   , u"scroll up ")
			 ,(u"down"		   , u"scroll down")]
		return xList

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
	def filterPiI(self, valuesDict=None, filter="self", typeId="", devId="x",action =""):

		xList = []
		for piU in _rpiBeaconList:
			if self.RPI[piU][u"piOnOff"] != "0":
				xList.append([piU, piU])
		for piU in _rpiSensorList:
			if self.RPI[piU][u"piOnOff"] != "0":
				xList.append([piU, piU ])

		return xList
####-------------------------------------------------------------------------####
	def confirmPiNumberBUTTONI(self, valuesDict=None, typeId="", devId="x"):
		try:
			piN 	= valuesDict[u"piServerNumber"]
			nChan 	= self.getTypeIDLength(typeId)
			valuesDict[u"piDone"]	 = True
			valuesDict[u"stateDone"] = True

			self.stateNumberForInputGPIOX = ""
			if valuesDict[u"deviceDefs"] == "":
				valuesDict[u"deviceDefs"]=json.dumps([{} for i in range(nChan)])

			xxx= json.loads(valuesDict[u"deviceDefs"])
			pinMappings	= ""
			nChan 		= min(nChan,len(xxx))
			for n in range(nChan):
				if u"gpio" in xxx[n]:
					pinMappings += unicode(n) + ":" + xxx[n][u"gpio"] + "|"
			valuesDict[u"pinMappings"] = pinMappings
		except Exception, e:
			self.indiLOG.log(40,"Line {} has error={}".format(sys.exc_traceback.tb_lineno, e))


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
		xList = []
		for i in range(self.getTypeIDLength(typeId)):
			xList.append((unicode(i), unicode(i)))
		return xList


####-------------------------------------------------------------------------####
	def confirmStateBUTTONI(self, valuesDict=None, typeId="", devId="x"):
		piN	 	= valuesDict[u"piServerNumber"]
		inS	 	= valuesDict[u"INPUTstate"]
		inSi 	= int(inS)
		nChan 	= self.getTypeIDLength(typeId)
		if valuesDict[u"deviceDefs"]!="":
			xxx=json.loads(valuesDict[u"deviceDefs"])
			if len(xxx) < nChan:
				for ll in range(nChan-len(xxx)):
					xxx.append({u"gpio":"", u"inpType":"", u"count": u"off"})
			if	u"gpio" in xxx[inSi] and xxx[inSi][u"gpio"] !="":
				valuesDict[u"gpio"]		 = xxx[inSi][u"gpio"]
				if	u"inpType" in xxx[inSi]:
					valuesDict[u"inpType"]	= xxx[inSi][u"inpType"]
				valuesDict[u"count"]	 	= xxx[inSi][u"count"]

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
			inS	 = unicode(inSi)
			try:	 gpio = unicode(int(valuesDict[u"gpio"]))
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
							valuesDict[u"gpio"] = u"-1"
							break
					if u"error" in pinMappings: break



			valuesDict[u"pinMappings"] = pinMappings
			valuesDict[u"deviceDefs"] = json.dumps(xxx)
			return valuesDict

####-------------------------------------------------------------------------####
	def filterPiO(self, valuesDict=None, filter="self", typeId="", devId="x",action= ""):

			xList = []
			for piU in _rpiBeaconList:
				if self.RPI[piU][u"piOnOff"] != u"0":
					try:
						devId= int(self.RPI[piU][u"piDevId"])
						if devId >0:
							name= u"-"+indigo.devices[devId].name
					except: name=""
					xList.append([piU,u"#"+piU+"-"+self.RPI[piU][u"ipNumberPi"]+name])

			return xList

####-------------------------------------------------------------------------####
	def confirmPiNumberBUTTONO(self, valuesDict=None, typeId="", devId="x"):
			piN 	= valuesDict[u"piServerNumber"]
			nChan 	= self.getTypeIDLength(typeId)
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


			if valuesDict[u"deviceDefs"] == "" or len(json.loads(valuesDict[u"deviceDefs"])) != nChan:
				valuesDict[u"deviceDefs"] = json.dumps([{} for i in range(nChan)])

			xxx 		= json.loads(valuesDict[u"deviceDefs"])
			pinMappings	= ""
			update		= False
			for n in range(nChan):
				if u"gpio" in xxx[n]:
					if u"initialValue" not in xxx[n]: 
						xxx[n][u"initialValue"] ="-"
						update= True
					pinMappings += unicode(n) + ":" + xxx[n][u"gpio"]+"," + xxx[n][u"outType"]+"," + xxx[n][u"initialValue"] + u"|"
			valuesDict[u"pinMappings"] = pinMappings
			if update:
				valuesDict[u"deviceDefs"] = json.dumps(xxx)

			inSi	= 0
			if valuesDict[u"deviceDefs"] != "":
				if u"gpio" in xxx[inSi] and xxx[inSi][u"gpio"] != "":
					valuesDict[u"gpio"]			= xxx[inSi][u"gpio"]
					valuesDict[u"outType"]		= xxx[inSi][u"outType"]
					valuesDict[u"initialValue"] = xxx[inSi][u"initialValue"]

			valuesDict[u"stateDone"] = True

			return valuesDict

####-------------------------------------------------------------------------####
	def filterOUTPUTchannels(self, valuesDict=None, filter="", typeId="", devId="x"):
			xList = []
			for i in range(self.getTypeIDLength(typeId)):
				xList.append((unicode(i), unicode(i)))
			return xList

####-------------------------------------------------------------------------####
	def filterTempSensorsOnThisRPI(self, valuesDict=None, filter="", typeId="", devId="x"):
		xList = [("0","internal temp sensor of RPI")]
		try:
			piN = indigo.devices[devId].states["note"].split("-")
			if len(piN) >1:
				piN = piN[1]
				#indigo.server.log(" dev Pi #sensor: " + piN)
				for dev in indigo.devices.iter("props.isTempSensor"):
					props = dev.pluginProps
					#self.indiLOG.log(20," selecting devid name temp sensor: {} pi#: {}".format(dev.name, props[u"piServerNumber"]) )
					if props[u"piServerNumber"] == piN:
						xList.append( (unicode(dev.id), dev.name.encode("utf8") +" " + unicode(dev.id)) )

		except Exception, e:
			self.indiLOG.log(40,"Line {} has error={}".format(sys.exc_traceback.tb_lineno, e))

		return xList



####-------------------------------------------------------------------------####
	def filtergpioList(self, valuesDict=None, filter="", typeId="", devId="x"):
			return _GlobalConst_allGPIOlist

####-------------------------------------------------------------------------####
	def filterList16(self, valuesDict=None, filter="", typeId="", devId="x"):
			xList = []
			for ii in range(16):
				xList.append((ii,ii))
			return xList

####-------------------------------------------------------------------------####
	def filterList12(self, valuesDict=None, filter="", typeId="", devId="x"):
			xList = []
			for ii in range(12):
				xList.append((ii,ii))
			return xList

####-------------------------------------------------------------------------####
	def filterList10(self, valuesDict=None, filter="", typeId="", devId="x"):
			xList = []
			for ii in range(10):
				xList.append((ii,ii))
			return xList

####-------------------------------------------------------------------------####
	def filterList8(self, valuesDict=None, filter="", typeId="", devId="x"):
			xList = []
			for ii in range(8):
				xList.append((ii,ii))
			return xList

####-------------------------------------------------------------------------####
	def filterList4(self, valuesDict=None, filter="", typeId="", devId="x"):
			xList = []
			for ii in range(4):
				xList.append((ii,ii))
			return xList

####-------------------------------------------------------------------------####
	def filterList1(self, valuesDict=None, filter="", typeId="", devId="x"):
			xList = []
			for ii in range(1):
				xList.append((ii,ii))
			return xList



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
					   
			inS = "0"
			inSi = int(inS)
			if valuesDict[u"gpio"] == "0":
				xxx[inSi] = {}
			else:
				xxx[inSi] = {u"gpio": valuesDict[u"gpio"],"outType": valuesDict[u"outType"],"initialValue": valuesDict[u"initialValue"]}
			pinMappings = ""
			# clean up
			for n in range(nChannels):
				if u"gpio" in xxx[n]:
					if xxx[n][u"gpio"] == "0":
						del xxx[n]
					if	len(oldxxx) < (n+1) or "initialValue" not in oldxxx[n] or (xxx[n][u"initialValue"] != oldxxx[n][u"initialValue"]):
						self.sendInitialValue = dev.id
					pinMappings += unicode(n) + ":" + xxx[n][u"gpio"]+ "," + xxx[n][u"outType"]+ "," + xxx[n][u"initialValue"]+"|"
					if "inverse" in dev.states:
						if (dev.states["inverse"] =="yes") != (xxx[n][u"outType"]=="1"): dev.updateStateOnServer("inverse", xxx[n][u"outType"]=="1" )
					elif "inverse_{:2d}".format(n) in dev.states:
						if (dev.states["inverse_{:2d}".format(n)] =="yes") != (xxx[n][u"outType"]=="1"): dev.updateStateOnServer("inverse_{:2d}".format(n), xxx[n][u"outType"]=="1" )
					if "initial" in dev.states:
						if dev.states["initial"] != xxx[n][u"initialValue"]: dev.updateStateOnServer("initial", xxx[n][u"initialValue"])
					elif "initial{:2d}".format(n) in dev.states:
						if dev.states["initial{:2d}".format(n)] != xxx[n][u"initialValue"]: dev.updateStateOnServer("initial{:2d}".format(n), xxx[n][u"initialValue"] )
					
					for l in range(n, nChannels):
						if l == n: continue
						if u"gpio" not in xxx[l]:	continue
						if xxx[l][u"gpio"] == "0":	continue
						if xxx[n][u"gpio"] == xxx[l][u"gpio"]:
							pinMappings = "error # " + unicode(n) + " same pin as #" + unicode(l)
							xxx[l][u"gpio"] = "0"
							valuesDict[u"gpio"] = "0"
							break
					if u"error" in pinMappings: break

			valuesDict[u"pinMappings"] = pinMappings
			valuesDict[u"deviceDefs"] = json.dumps(xxx)
			self.indiLOG.log(10, u"len:{};  deviceDefs:{}".format(nChannels, valuesDict[u"deviceDefs"]))
			return valuesDict

####-------------------------------------------------------------------------####
	def sendConfigCALLBACKaction(self, action1=None, typeId="", devId=0):
		try:
			valuesDict = action1.props
			if valuesDict[u"configurePi"] ==u"": return
			return self.execButtonConfig(valuesDict, level="0,", action=[u"updateParamsFTP"], Text="send Config Files to pi# ")
		except:
			self.indiLOG.log(20, u"sendConfigCALLBACKaction  bad rPi number:"+ unicode(valuesDict))


####-------------------------------------------------------------------------####
	def buttonConfirmSendOnlyCALLBACKaction(self, action1=None, typeId="", devId=0):
		return self.buttonConfirmSendOnlyCALLBACK(action1.props)

####-------------------------------------------------------------------------####
	def buttonConfirmSendOnlyParamssshCALLBACK(self, valuesDict=None, typeId="", devId=0):
		return self.execButtonConfig(valuesDict, level="0,", action=[u"updateParamsFTP"], Text="send Config Files to pi# ")

####-------------------------------------------------------------------------####
	def buttonConfirmSendRestartPysshCALLBACK(self, valuesDict=None, typeId="", devId=0):
		return self.execButtonConfig(valuesDict, level="master,", action=[u"updateParamsFTP"], Text="send Config Files and restart master.py  ")

####-------------------------------------------------------------------------####
	def buttonConfirmRestartMastersshCALLBACK(self, valuesDict=None, typeId="", devId=0):
		return self.execButtonConfig(valuesDict, level="", action=[u"restartmasterSSH"], Text="restart master.py  ")

####-------------------------------------------------------------------------####
	def buttonConfirmConfigureCALLBACK(self, valuesDict=None, typeId="", devId=0):
		return self.execButtonConfig(valuesDict, level="reboot,", action=[u"updateParamsFTP"], Text="send Config Files and restart rPI")

	def buttonUpgradeCALLBACK(self, valuesDict=None, typeId="", devId=0):
		return self.execButtonConfig(valuesDict, level="0,", action=[u"upgradeOpSysSSH"], Text="upgrade rPi")

####-------------------------------------------------------------------------####
	def buttonResetOutputCALLBACK(self, valuesDict=None, typeId="", devId=0):
		return self.execButtonConfig(valuesDict, level="0,", action=[u"resetOutputSSH"], Text="reset output file  and reboot pi# ")

####-------------------------------------------------------------------------####
	def buttonSendBigFilessshCALLBACK(self, valuesDict=None, typeId="", devId=0):
		return self.execButtonConfig(valuesDict, level="master,", action=[u"initSSH",u"updateAllFilesFTP"], Text="send ALL Files to pi# ")

####-------------------------------------------------------------------------####
	def buttonSendINITCALLBACK(self, valuesDict=None, typeId="", devId=0):
		return self.execButtonConfig(valuesDict, level="0,", action=[u"initSSH",u"updateAllFilesFTP","rebootSSH"], Text="make dirs etc on RPI, send pgms,... only once")


####-------------------------------------------------------------------------####
	def buttonShutdownsshCALLBACKaction(self, action1=None, typeId="", devId=0):
		return self.buttonShutdownsshCALLBACK(valuesDict=action1.props)

####-------------------------------------------------------------------------####
	def buttonShutdownsshCALLBACK(self, valuesDict=None, typeId="", devId=0):
		self.setCurrentlyBooting(self.bootWaitTime, setBy="buttonShutdownsshCALLBACK")
		return self.execButtonConfig(valuesDict, level="0,", action=[u"shutdownSSH"], Text="shut down rPi# ")

####-------------------------------------------------------------------------####
	def buttonSendAllandRebootsshCALLBACK(self, valuesDict=None, typeId="", devId=0):
		self.setCurrentlyBooting(self.bootWaitTime, setBy="buttonSendAllandRebootsshCALLBACK")
		return self.execButtonConfig(valuesDict, level="0,", action=[u"initSSH",u"updateAllFilesFTP","rebootSSH"], Text="rPi configure and reboot pi# ")


####-------------------------------------------------------------------------####
	def buttonRebootsshCALLBACKaction(self,	action1=None, typeId="", devId=0):
		self.buttonRebootSocketCALLBACK(valuesDict=action1.props)

####-------------------------------------------------------------------------####
	def buttonRebootsshCALLBACK(self, valuesDict=None, typeId="", devId=0):
		self.setCurrentlyBooting(self.bootWaitTime, setBy="buttonRebootsshCALLBACK")
		return self.execButtonConfig(valuesDict, level="0,", action=[u"rebootSSH"], Text="rPi reboot")

####-------------------------------------------------------------------------####
	def buttonStopConfigCALLBACK(self, valuesDict=None, typeId="", devId=0):
		return self.execButtonConfig(valuesDict, level="0,", action=[u""], Text="rPi stop Configure ")


####-------------------------------------------------------------------------####
	def buttonGetSystemParametersCALLBACK(self, valuesDict=None, typeId="", devId=0):
		return self.execButtonConfig(valuesDict, level="0,", action=[u"getStatsSSH"], Text="get stats from rpi")


####-------------------------------------------------------------------------####
	def buttonbuttonGetpiBeaconLogCALLBACK(self, valuesDict=None, typeId="", devId=0):
		return self.execButtonConfig(valuesDict, level="0,", action=[u"getLogFileSSH"], Text="get pibeacon logfile from rpi")

####------------------------------------------------------------------------####
	def buttonGetiBeaconList0CALLBACK(self, valuesDict=None, typeId="", devId=0):
		return self.execButtonConfig(valuesDict, level="0,", action=[u"getiBeaconList0SSH"], Text="get stats from rpi")

####------------------------------------------------------------------------####
	def buttonGetiBeaconList1CALLBACK(self, valuesDict=None, typeId="", devId=0):
		return self.execButtonConfig(valuesDict, level="0,", action=[u"getiBeaconList1SSH"], Text="get stats from rpi")


####-------------------------------------------------------------------------####
	def execButtonConfig(self, valuesDict, level="0,", action=[], Text=""):
		try:
			try:
				pi = int(valuesDict[u"configurePi"])
			except:
				return valuesDict
			piU = unicode(pi)

			if pi == 999:
				self.setALLrPiV(u"piUpToDate", action, resetQueue=True)
				self.rPiRestartCommand = [level for ii in range(_GlobalConst_numberOfRPI)]	## which part need to restart on rpi
				return valuesDict
			if pi < 99:
				if self.decideMyLog(u"UpdateRPI"): self.indiLOG.log(10, Text + piU+"  action string:"+ unicode(action)	 )
				self.rPiRestartCommand[pi] = level	## which part need to restart on rpi
				self.setONErPiV(piU,"piUpToDate", action, resetQueue=True)
		except Exception, e:
			self.indiLOG.log(40,"Line {} has error={}".format(sys.exc_traceback.tb_lineno, e))
		return valuesDict


####-------------------------------------------------------------------------####
	def buttonConfirmWiFiCALLBACK(self, valuesDict=None, typeId="", devId=0):
		try:
			pi = int(valuesDict[u"configurePi"])
		except:
			return valuesDict
		piU = unicode(pi)
		for piU in self.RPI:
				if self.wifiSSID != "" and self.wifiPassword != "":
					if self.decideMyLog(u"UpdateRPI"): self.indiLOG.log(10, u"configuring WiFi on pi#" + piU)
					self.rPiRestartCommand = [u"restart" for ii in range(_GlobalConst_numberOfRPI)]	 ## which part need to restart on rpi
					self.configureWifi(piU)
				else:
					self.indiLOG.log(20, u"buttonConfirmWiFiCALLBACK configuring WiFi: SSID and password not set")

		if pi < 99:
			if self.wifiSSID != "" and self.wifiPassword != "":
				if self.decideMyLog(u"UpdateRPI"): self.indiLOG.log(10, u"configuring WiFi on pi#" + piU)
				self.rPiRestartCommand[pi] = "reboot"  ## which part need to restart on rpi
				self.configureWifi(piU)
			else:
				self.indiLOG.log(20, u"buttonConfirmWiFiCALLBACK configuring WiFi: SSID and password not set")

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
		piU = unicode(pi)
		out= json.dumps([{u"command":"general","cmdLine":"sudo killall -9 python;sync;sleep 5;sudo halt &"}])
		if pi == 999:
			for piU in self.RPI:
				self.indiLOG.log(20, u"hard shutdown of rpi {};   ".format(self.RPI[piU][u"ipNumberPi"], out) )
				self.presendtoRPI(piU,out)
		else:
				self.indiLOG.log(20, u"hard shutdown of rpi {};   ".format(self.RPI[piU][u"ipNumberPi"], out) )
				self.presendtoRPI(piU,out)
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
		piU = unicode(pi)

		out= json.dumps([{u"command":"general","cmdLine":"sudo killall -9 python;sync;sleep 5;sudo reboot -f &"}])
		if pi == 999:
			for piU in self.RPI:
				self.presendtoRPI(piU,out)
		else:
				self.indiLOG.log(20, u"hard reboot of rpi{};   ".format(self.RPI[piU][u"ipNumberPi"], out) )
				self.presendtoRPI(piU,out)
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
		piU = unicode(pi)

		out= json.dumps([{u"command":"general","cmdLine":"sudo killall -9 python;sleep 4; sudo reboot &"}])
		if pi == 999:
			for piU in self.RPI:
				self.indiLOG.log(20, u"regular reboot of rpi {};  {}".format(self.RPI[piU][u"ipNumberPi"], out) )
				self.presendtoRPI(piU,out)
		else:
				self.indiLOG.log(20, u"regular reboot of rpi {};  {}".format(self.RPI[piU][u"ipNumberPi"], out) )
				self.presendtoRPI(piU,out)

		return


####-------------------------------------------------------------------------####
	def setTimeCALLBACKaction(self, action1=None, typeId="", devId=0):
		self.doActionSetTime(action1.props[u"configurePi"])# do it now
		return

####-------------------------------------------------------------------------####
	def buttonsetTimeCALLBACK(self, valuesDict=None, typeId="", devId=0):
		self.actionList["setTime"].append({u"action":"setTime","value":valuesDict[u"configurePi"]}) # put it into queue and return to menu
		return

####-------------------------------------------------------------------------####
	def refreshNTPCALLBACKaction(self, action1=None, typeId="", devId=0):
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
	def doActionSetTime(self, piU):
		try: 
			if piU not in self.RPI: return 

		except: 
			self.indiLOG.log(20, u"ERROR	set time of rpi	 bad PI# given:"+piU )
			return

		try: 

			ipNumberPi = self.RPI[piU][u"ipNumberPi"]
			dt =0
			xx, retC = self.testDeltaTime( piU, ipNumberPi,dt)
			for ii in range(5):
				dt , retC  = self.testDeltaTime( piU, ipNumberPi, dt*0.9)
				if retC !=0:
					self.indiLOG.log(20, u"sync time	MAC --> RPI, did not work, no connection to RPI# {}".format(piU) )
					return 
				if abs(dt) < 0.5: break 

			self.indiLOG.log(20, u"set time of RPI# {}  finished, new delta time ={:6.1f}[secs]".format(piU,dt))

		except Exception, e:
			self.indiLOG.log(40,"Line {} has error={}".format(sys.exc_traceback.tb_lineno, e))

		return

####-------------------------------------------------------------------------####
	def testDeltaTime(self, piU, ipNumberPi, tOffset):
		try: 

			dateTimeString = datetime.datetime.fromtimestamp(time.time()+ tOffset).strftime(_defaultDateStampFormat+".%f")
			out= json.dumps([{u"command":"general","cmdLine":"setTime="+dateTimeString}])
			retC = self.presendtoRPI(piU,out)
			if retC !=0: return 0, retC
			if self.decideMyLog(u"UpdateRPI"):self.indiLOG.log(20, u"set time # of rpi:{}; ip:{};  offset-used:{:5.2f};  cmd:{}".format(piU, ipNumberPi, tOffset, json.dumps(out)) )

			self.RPI[piU][u"deltaTime1"] =-99999
			for ii in range(20):
				if self.RPI[piU][u"deltaTime1"] != -99999: break
				time.sleep(0.1)

			delta1 = self.RPI[piU][u"deltaTime1"]
			delta2 = self.RPI[piU][u"deltaTime2"]
			if abs(delta1) < 1.5 and abs(delta2) < 1.5:
				dt = abs(delta1*3.+delta2) /4.
			else:
				if abs(delta1) < abs(delta2): dt = delta1
				else:						  dt = delta2

			return dt, retC

		except Exception, e:
			self.indiLOG.log(40,"Line {} has error={}".format(sys.exc_traceback.tb_lineno, e))


		return 0, -1


####-------------------------------------------------------------------------####
	def sendAnycommandCALLBACKaction(self, action1=None, typeId="", devId=0):
		self.buttonAnycommandCALLBACK(valuesDict=action1.props)
		return

####-------------------------------------------------------------------------####
	def buttonAnycommandCALLBACK(self, valuesDict=None, typeId="", devId=0):
		piU = valuesDict[u"configurePi"]
		if piU ==u"": 
			self.indiLOG.log(20, u"send YOUR command to rpi ...  no RPI selected")
			return
		if piU == "999":
			for piU in self.RPI:
				out= json.dumps([{u"command":"general","cmdLine":valuesDict[u"anyCmdText"]}])
				if self.RPI[piU][u"ipNumberPi"] !="":
					self.indiLOG.log(20, u"send YOUR command to rpi:{}  {};  {}".format(piU, self.RPI[piU][u"ipNumberPi"], json.dumps(out)) )
					self.presendtoRPI(piU,out)
		else:
				out= json.dumps([{u"command":"general","cmdLine":valuesDict[u"anyCmdText"]}])
				self.indiLOG.log(20, u"send YOUR command to rpi:{}  {};  {}".format(piU, self.RPI[piU][u"ipNumberPi"], json.dumps(out)) )
				self.presendtoRPI(piU,out)
			
		return


####-------------------------------------------------------------------------####
	def filterBeacons(self, valuesDict=None, filter="", typeId="", devId=0, action=""):
		xList = []
		for dev in indigo.devices.iter("props.isBeaconDevice"):
			xList.append((dev.id,"{}".format(dev.name.encode("utf8"))))
		xList.append((0,"delete"))
		return xList

####-------------------------------------------------------------------------####
	def filterBeaconsWithBattery(self, valuesDict=None, filter="", typeId="", devId=0, action=""):
		xList = []
		for dev in indigo.devices.iter("props.isBeaconDevice"):
			props = dev.pluginProps
			if "SupportsBatteryLevel" not in props or not props["SupportsBatteryLevel"]: continue
			if "batteryLevelUUID" not in props or props["batteryLevelUUID"] == "off": continue
			xList.append((dev.id, "{} - {}".format(dev.name.encode("utf8"), dev.address) ))
		return xList


####-------------------------------------------------------------------------####
	def filterSoundFiles(self, valuesDict=None, filter="", typeId="", devId=0, action=""):
		xList = []
		for fileName in os.listdir(self.indigoPreferencesPluginDir+"soundFiles/"):
			xList.append((fileName,fileName))
		return xList

####-------------------------------------------------------------------------####
	def filterSensorONoffIcons(self, valuesDict=None, filter="", typeId="", devId=0, action=""):
		xList = []
		for ll in _GlobalConst_ICONLIST:
			xList.append((ll[0]+"-"+ll[1],ll[0]+", u"+ll[1]))
		xList.append((u"-","     "))
		return xList


####-------------------------------------------------------------------------####
	def filterPiD(self, valuesDict=None, filter="", typeId="", devId=0, action=""):
		xList = []
		for piU in _rpiBeaconList:
			if self.RPI[piU][u"piOnOff"] == "0" or self.RPI[piU][u"ipNumberPi"] == "":
				xList.append([piU, piU + "-"])
			else:
				xList.append([piU, piU + "-" + self.RPI[piU][u"ipNumberPi"] + "-" + self.RPI[piU][u"piMAC"]])
		for piU in _rpiSensorList:
			if self.RPI[piU][u"piOnOff"] == "0" or self.RPI[piU][u"ipNumberPi"] == "":
				xList.append([piU, piU + "-  - Sensor Only"])
			else:
				xList.append([piU, piU + "-" + self.RPI[piU][u"ipNumberPi"] + "- Sensor Only"])
		return xList

####-------------------------------------------------------------------------####
	def filterPiDONoff(self, valuesDict=None, filter="", typeId="", devId=0, action=""):
		xList = [["-1","off"]]
		for piU in _rpiBeaconList:
			if self.RPI[piU][u"piOnOff"] == "0" or self.RPI[piU][u"ipNumberPi"] == "":
				xList.append([piU, piU + "-"])
			else:
				xList.append([piU, piU + "-" + self.RPI[piU][u"ipNumberPi"] + "-" + self.RPI[piU][u"piMAC"]])
		for piU in _rpiSensorList:
			if self.RPI[piU][u"piOnOff"] == "0" or self.RPI[piU][u"ipNumberPi"] == "":
				xList.append([piU, piU + "-  - Sensor Only"])
			else:
				xList.append([piU, piU + "-" + self.RPI[piU][u"ipNumberPi"] + "- Sensor Only"])
		return xList

####-------------------------------------------------------------------------####
	def filterPiOnlyBlue(self, valuesDict=None, filter="", typeId="", devId=0, action=""):
		xList = []
		for piU in _rpiBeaconList:
			if self.RPI[piU][u"piOnOff"] == "0" or self.RPI[piU][u"ipNumberPi"] == "":
				pass
			else:
				xList.append([piU, piU + "-" + self.RPI[piU][u"ipNumberPi"] + "-" + self.RPI[piU][u"piMAC"]])
		return xList


####-------------------------------------------------------------------------####
	def filterPiC(self, valuesDict=None, typeId="", devId=0, action=""):
		xList = []
		for piU in _rpiBeaconList:
			if self.RPI[piU][u"piOnOff"] == "0" or	self.RPI[piU][u"ipNumberPi"] == "": continue
			xList.append([piU, piU + "-" + self.RPI[piU][u"ipNumberPi"] + "-" + self.RPI[piU][u"piMAC"]])
		for piU in _rpiSensorList:
			if self.RPI[piU][u"piOnOff"] == "0" or	self.RPI[piU][u"ipNumberPi"] == "": continue
			xList.append([piU, piU + "-" + self.RPI[piU][u"ipNumberPi"] + "- Sensor Only"])
		xList.append([-1, u"off"])
		return xList


####-------------------------------------------------------------------------####
	def filterPiBLE(self, valuesDict=None, typeId="", devId=0, action=""):
		xList = []
		for piU in _rpiBeaconList:
			if self.RPI[piU][u"piOnOff"] == "0" or	self.RPI[piU][u"ipNumberPi"] == "": continue
			xList.append([piU, piU + "-" + self.RPI[piU][u"ipNumberPi"] + "-" + self.RPI[piU][u"piMAC"]])
		xList.append([999, u"all"])
		return xList


####-------------------------------------------------------------------------####
	def filterPi(self, valuesDict=None, typeId="", devId=0, action=""):
		xList = []
		for piU in _rpiBeaconList:
			if self.RPI[piU][u"piOnOff"] == "0" or	self.RPI[piU][u"ipNumberPi"] == "": continue
			xList.append([piU, piU + "-" + self.RPI[piU][u"ipNumberPi"] + "-" + self.RPI[piU][u"piMAC"]])
		for piU in _rpiSensorList:
			if self.RPI[piU][u"piOnOff"] == "0" or	self.RPI[piU][u"ipNumberPi"] == "": continue
			xList.append([piU, piU + "-" + self.RPI[piU][u"ipNumberPi"] + "- Sensor Only"])
		xList.append([999, u"all"])
		return xList

####-------------------------------------------------------------------------####
	def filterPiNoAll(self, valuesDict=None, typeId="", devId=0, action=""):
		xList = []
		for piU in _rpiBeaconList:
			if self.RPI[piU][u"piOnOff"] == "0": 	continue
			if self.RPI[piU][u"ipNumberPi"] == "": 	continue
			xList.append([piU, piU + "-" + self.RPI[piU][u"ipNumberPi"] + "-" + self.RPI[piU][u"piMAC"]])
		for piU in _rpiSensorList:
			if self.RPI[piU][u"piOnOff"] == "0": 	continue
			if self.RPI[piU][u"ipNumberPi"] == "": 	continue
			xList.append([piU, piU + "-" + self.RPI[piU][u"ipNumberPi"] + "- Sensor Only"])
		return xList

####-------------------------------------------------------------------------####
	def filterPiOUT(self, filter="", valuesDict=None, typeId="", devId=0, action=""):
		xList = []
		default = ""
		for piU in self.RPI:
			if self.RPI[piU][u"piOnOff"] == "0": 	continue
			if self.RPI[piU][u"ipNumberPi"] == "": 	continue
			if self.RPI[piU][u"piDevId"] == 0: 		continue
			devIDpi = self.RPI[piU][u"piDevId"]
			if typeId in self.RPI[piU][u"output"] and unicode(devId) in self.RPI[piU][u"output"][typeId]:
				try:
					default = (piU, u"Pi-" + piU + "-" + self.RPI[piU][u"ipNumberPi"] + ";  Name =" + indigo.devices[devIDpi].name)
				except Exception, e:
					self.indiLOG.log(40,"Line {} has error={}".format(sys.exc_traceback.tb_lineno, e))
					self.indiLOG.log(40,u" devid " + unicode(devIDpi))
				continue
			else:
				try:
					xList.append((piU, u"Pi-" + piU + "-" + self.RPI[piU][u"ipNumberPi"] + ";  Name =" + indigo.devices[devIDpi].name))
				except Exception, e:
					self.indiLOG.log(40,"Line {} has error={}".format(sys.exc_traceback.tb_lineno, e))
					self.indiLOG.log(40, u" devid " + unicode(devIDpi))

		if default != "":
			xList.append(default)

		return xList



####-------------------------------------------------------------------------####
	def filterActiveBEACONs(self, valuesDict=None, typeId="", devId=0, action=""):

		try:
			listActive = []
			for mac in self.beacons:
				if len(mac) < 5 or mac.find("00:00:00:00") ==0: continue
				try:
					name = indigo.devices[self.beacons[mac][u"indigoId"]].name
				except:
					continue
				if self.beacons[mac][u"ignore"] <= 0 and self.beacons[mac][u"indigoId"] != 0:
					listActive.append([mac, name + "- active, used"])
			listActive = sorted(listActive, key=lambda tup: tup[1])
		except Exception, e:
			self.indiLOG.log(40,"Line {} has error={}".format(sys.exc_traceback.tb_lineno, e))
			listActive = []
		return listActive

####-------------------------------------------------------------------------####
	def filterMACs(self, valuesDict=None, typeId="", devId=0, action=""):

		listrejectedByPi = []
		listActive		 = []
		listDeleted		 = []
		listIgnored		 = []
		listOldIgnored	 = []

		if False:
			try:
				f = open(self.indigoPreferencesPluginDir + "rejected/rejectedByPi.json", u"r")
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
			except Exception, e:
				if unicode(e).find(u"timeout waiting") > -1:
					self.indiLOG.log(40,"Line {} has error={}".format(sys.exc_traceback.tb_lineno, e))
					self.indiLOG.log(40, u"communication to indigo is interrupted")
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
	def filterRPIs(self, valuesDict=None, typeId="", devId=0, action=""):

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
				listActive.append([unicode(indigoId), "{} - {}".format(name.encode("utf8"), mac) ])

			except:
				pass
		listActive = sorted(listActive, key=lambda tup: tup[1])


		return listActive


####-------------------------------------------------------------------------####
	def filterUUIDiphone(self, valuesDict=None, typeId="", devId=0, action=""):
		xList = []
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
					xList.append((dev.id, u"already defined: " +name + "  UUID: " + uuid))
			else:
					xList.append((dev.id, u"      available: " +name + "  UUID: " + uuid))

		xList = sorted(xList, key=lambda tup: tup[1])

		return xList


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
		xList = []
		xList1 = {}
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
				if uuid not in xList1:
					xList1[uuid] = 1
					xList.append((uuid, name+ "-"+ uuid ))
			except:
				continue

		xList = sorted(xList, key=lambda tup: tup[1])
		return xList

####-------------------------------------------------------------------------####
	def filterUUIDNameExisting(self, valuesDict=None, typeId="", devId=0):
		xList = []
		for uuid in self.beaconsUUIDtoName:
			if uuid != "" and self.beaconsUUIDtoName != "":
				xList.append([uuid, self.beaconsUUIDtoName[uuid]+"-"+ uuid])
		xList = sorted(xList, key=lambda tup: tup[1])
		return xList




####-------------------------------------------------------------------------####
	def buttonconfirmPreselectCALLBACK(self, valuesDict=None, typeId="", devId=0):
		try:
			self.constantUUIDmajMIN = valuesDict[u"constantUUIDmajMIN"]
			try: self.lenOfUUID		= int(valuesDict[u"lenOfUUID"])
			except: self.lenOfUUID	=  32
		except Exception, e:
			self.indiLOG.log(40,"Line {} has error={}".format(sys.exc_traceback.tb_lineno, e))
			return valuesDict

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

		except Exception, e:
			self.indiLOG.log(40,"Line {} has error={}".format(sys.exc_traceback.tb_lineno, e))

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
					for piU in _rpiBeaconList:
						self.setONErPiV(piU,"piUpToDate", [u"updateParamsFTP"], resetQueue=True)
				valuesDict[u"nameForIphone"] = self.beaconsUUIDtoIphone[beacon][3]

		except Exception, e:
			self.indiLOG.log(40,"Line {} has error={}".format(sys.exc_traceback.tb_lineno, e))
			return valuesDict

		self.indiLOG.log(20, u"buttonConfirmSelectIphoneUUIDtoMACCALLBACK: UUIDtoIphone=" + unicode(self.beaconsUUIDtoIphone))
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
					for piU in _rpiBeaconList:
						self.setONErPiV(piU,"piUpToDate", [u"updateParamsFTP"], resetQueue=True)

		except Exception, e:
			self.indiLOG.log(40,"Line {} has error={}".format(sys.exc_traceback.tb_lineno, e))
			return valuesDict

		return valuesDict

 
 
 
####-------------------------------------------------------------------------####
	def buttonConfirmSelectUUIDtoNameCALLBACK(self, valuesDict=None, typeId="", devId=0):
		uuid = valuesDict[u"selectUUID"]
		uname = valuesDict[u"uuidtoName"]
		if uuid != "" and uname != "":
			self.beaconsUUIDtoName[uuid] = uname

		return valuesDict

####-------------------------------------------------------------------------####
	def buttonConfirmDeleteUUIDtoNameCALLBACK(self, valuesDict=None, typeId="", devId=0):
		uuid = valuesDict[u"selectUUIDexistingMap"]
		if uuid != "":
			if uuid in self.beaconsUUIDtoName:
				del self.beaconsUUIDtoName[uuid]

		return valuesDict



####-------------------------------------------------------------------------####
	def mapNametoUUID(self, name):
		try:
			for uuid in self.beaconsUUIDtoName:
				if name == self.beaconsUUIDtoName[uuid]:
					return uuid
			return ""
		except Exception, e:
			self.indiLOG.log(40,"Line {} has error={}".format(sys.exc_traceback.tb_lineno, e))
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
		except Exception, e:
			self.indiLOG.log(40,"Line {} has error={}".format(sys.exc_traceback.tb_lineno, e))
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
		except Exception, e:
			self.indiLOG.log(40,"Line {} has error={}".format(sys.exc_traceback.tb_lineno, e))
		return 1,uuid



####-------------------------------------------------------------------------####
	def buttonConfirmnewBeaconsLogTimerCALLBACK(self, valuesDict=None, typeId="", devId=0):
		try:
			xx = float(valuesDict[u"newBeaconsLogTimer"])
			if xx > 0: 
				self.newBeaconsLogTimer = time.time() + xx*60
				self.indiLOG.log(20, u"newBeaconsLogTimer set to: {} minutes".format(valuesDict[u"newBeaconsLogTimer"]) )
			else:
				self.newBeaconsLogTimer = 0
		except Exception, e:
			self.indiLOG.log(40,"Line {} has error={}".format(sys.exc_traceback.tb_lineno, e))
			self.newBeaconsLogTimer = 0
		return valuesDict


####-------------------------------------------------------------------------####
	def buttonConfirmSelectBeaconCALLBACK(self, valuesDict=None, typeId="", devId=0):
		try:
			id	= self.beacons[valuesDict[u"selectBEACON"]][u"indigoId"]
			length = int(valuesDict[u"selectBEACONlen"])
			dev = indigo.devices[int(id)]
		except Exception, e:
			self.indiLOG.log(40,"Line {} has error={}".format(sys.exc_traceback.tb_lineno, e))
			return valuesDict
		self.indiLOG.log(20, "log messages for	 beacon:{} mac:{}".format(dev.name.encode("utf8"), valuesDict[u"selectBEACON"][:length]) )
		self.selectBeaconsLogTimer[valuesDict[u"selectBEACON"]]	 = length
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
			self.indiLOG.log(20, "log messages for beacons with signal strength change GT {}  including ON->off and off-ON".format(self.trackSignalStrengthIfGeaterThan[0]))
		else:
			self.indiLOG.log(20, "log messages for beacons with signal strength change GT {}  excluding ON->off and off-ON".format(self.trackSignalStrengthIfGeaterThan[0]))
		return valuesDict

####-------------------------------------------------------------------------####
	def buttonConfirmselectChangeOfRPICALLBACK(self, valuesDict=None, typeId="", devId=0):
		self.trackSignalChangeOfRPI = valuesDict[u"trackSignalChangeOfRPI"] ==u"1"
		self.indiLOG.log(20, "log messages for beacons that change closest RPI: {}".format(self.trackSignalChangeOfRPI))
		return valuesDict


####-------------------------------------------------------------------------####
	def buttonConfirmselectRPImessagesCALLBACK(self, valuesDict=None, typeId="", devId=0):
		
		try:	self.trackRPImessages = int(valuesDict[u"piServerNumber"])
		except: self.trackRPImessages = -1 
		if self.trackRPImessages == -1: 	
			self.indiLOG.log(20, "log all messages from pi: off" )
		else:
			self.indiLOG.log(20, "log all messages from pi: {}".format(self.trackRPImessages ))

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
				self.indiLOG.log(20, "ERROR can not replace existing active beacon;{}   still active".format(oldName) )
				valuesDict[u"MSG"] = "ERROR can not replace existing ACTIVE beacon"
				return valuesDict
			if oldMAC == newMAC:
				self.indiLOG.log(20, "ERROR, can't replace itself")
				valuesDict[u"MSG"] = "ERROR,choose 2 different beacons"
				return valuesDict

			oldPROPS[u"address"] = newMAC
			self.deviceStopCommIgnore = time.time()
			oldDEV.replacePluginPropsOnServer(oldPROPS)

			self.beacons[newMAC] = copy.deepcopy(self.beacons[oldMAC])
			self.beacons[newMAC][u"indigoId"] = oldINDIGOid
			del self.beacons[oldMAC]
			indigo.device.delete(newDEV)

			self.indiLOG.log(30, "=== deleting  === replaced MAC number {}  of device {} with {} --	and deleted device {}    ===".format(oldMAC, oldName.encode("utf8"), newMAC, newName.encode("utf8")) )
			valuesDict[u"MSG"] = "replaced, moved MAC number"

		except Exception, e:
			self.indiLOG.log(40,"Line {} has error={}".format(sys.exc_traceback.tb_lineno, e))
		return valuesDict

####-------------------------------------------------------------------------####
	def buttonExecuteReplaceRPICALLBACK(self, valuesDict=None, typeId="", devId=0):

		try:

			oldID = valuesDict[u"oldID"]
			newID = valuesDict[u"newID"]
			if oldID == newID: 
				valuesDict[u"MSG"] = "must use 2 different RPI"
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
			self.deviceStopCommIgnore = time.time()
			oldDEV.replacePluginPropsOnServer(oldPROPS)
			newPROPS[u"address"] = newMAC[:-1]+"x"
			self.deviceStopCommIgnore = time.time()
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
			self.indiLOG.log(30, "=== replaced MAC number {}  of device {} with {} --	and deleted device {}    ===".format(oldMAC, oldName, newMAC, newName) )
			valuesDict[u"MSG"] = "replaced, moved MAC number"

		except Exception, e:
			self.indiLOG.log(40,"Line {} has error={}".format(sys.exc_traceback.tb_lineno, e))
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

				for piU in _rpiBeaconList:
					self.setONErPiV(piU,"piUpToDate", [u"updateParamsFTP"], resetQueue=True)
		else:
			self.beacons[mac] = copy.deepcopy(_GlobalConst_emptyBeacon)
			self.beacons[mac][u"ignore"] = 1
			self.newIgnoreMAC += 1
			self.beacons[mac][u"created"] = datetime.datetime.now().strftime(_defaultDateStampFormat)
		self.indiLOG.log(30, u"setting {};  indigoId: {} to ignore -mode: {}".format(mac, self.beacons[mac][u"indigoId"], self.beacons[mac][u"ignore"]) )
		self.beacons[mac][u"status"] = "ignored"
		if self.beacons[mac][u"indigoId"] >0: 
			try:
				self.indiLOG.log(30, u"=== deleting buttonConfirmMACIgnoreCALLBACK deleting dev  MAC#{}  indigoID ==0".format(mac) )
				indigo.device.delete(indigo.devices[self.beacons[mac][u"indigoId"]])
			except:
				self.indiLOG.log(40, u"buttonConfirmMACIgnoreCALLBACK error deleting dev  MAC#{}".format(mac) )

		self.makeBeacons_parameterFile()
		for piU in _rpiBeaconList:
			self.setONErPiV(piU,"piUpToDate", [u"updateParamsFTP"], resetQueue=True)


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
					f = open(self.indigoPreferencesPluginDir + "rejected/rejectedByPi.json", u"w")
					f.write(json.dumps(self.rejectedByPi))
					f.close()
				except:
					pass
		self.indiLOG.log(20, u"setting {} indigoId: {} to un-ignore -mode:{}".format(mac, self.beacons[mac][u"indigoId"], self.beacons[mac][u"ignore"]) )
		if self.beacons[mac][u"indigoId"] ==0:
			self.createNewiBeaconDeviceFromBeacons(mac)

		self.makeBeacons_parameterFile()
		for piU in _rpiBeaconList:
			self.setONErPiV(piU,"piUpToDate", [u"updateParamsFTP"], resetQueue=True)

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

		except Exception, e:
				if unicode(e).find(u"timeout waiting") > -1:
					self.indiLOG.log(40,"Line {} has error={}".format(sys.exc_traceback.tb_lineno, e))



####-------------------------------------------------------------------------####
	def buttonConfirmMACDeleteCALLBACK(self, valuesDict=None, typeId="", devId=0):
		mac = valuesDict[u"ignoreMAC"]
		if mac in self.beacons:
			for piU in _rpiBeaconList:
				self.setONErPiV(piU,"piUpToDate", [u"updateParamsFTP"], resetQueue=True)
			del self.beacons[mac]
		self.fixConfig(checkOnly = ["all","rpi"],fromPGM="buttonConfirmMACDeleteCALLBACK")
		return valuesDict

####-------------------------------------------------------------------------####
	def buttonConfirmMACDeleteALLCALLBACK(self, valuesDict=None, typeId="", devId=0):

		### this is very bad !!!
		#self.beacons = {}

		self.fixConfig(checkOnly = ["all","rpi"],fromPGM="buttonConfirmMACDeleteALLCALLBACK")
		for piU in _rpiBeaconList:
			self.setONErPiV(piU,"piUpToDate", [u"updateParamsFTP"], resetQueue=True)
		try:
			subprocess.call(u"rm '"+ self.indigoPreferencesPluginDir + "rejected/reject-1'", shell=True )
			subprocess.call(u"cp '"+ self.indigoPreferencesPluginDir + "rejected/rejects' '"+ self.indigoPreferencesPluginDir + "rejected/reject-1'" , shell=True)
			subprocess.call(u"rm '"+ self.indigoPreferencesPluginDir + "rejected/rejects*'" , shell=True)
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
			f = open(self.indigoPreferencesPluginDir + "rejected/rejectedByPi.json", u"r")
			self.rejectedByPi = json.loads(f.read())
			f.close()
		except:
			self.rejectedByPi = {}

		delB=[]
		for mac in self.rejectedByPi:
			if mac not in self.beacons:
				delB.append(mac)
		for mac in delB:
			self.indiLOG.log(20, u"removing "+mac+" from rejected history ")
			del self.rejectedByPi[mac]

		try:
			f = open(self.indigoPreferencesPluginDir + "rejected/rejectedByPi.json", u"w")
			f.write(json.dumps(self.rejectedByPi))
			f.close()
			subprocess.call(u"rm '"+ self.indigoPreferencesPluginDir + "rejected/reject-1'", shell=True )
			subprocess.call(u"cp '"+ self.indigoPreferencesPluginDir + "rejected/rejects' '"+ self.indigoPreferencesPluginDir + "rejected/reject-1'", shell=True )
			subprocess.call(u"rm '"+ self.indigoPreferencesPluginDir + "rejected/rejects*'", shell=True )
			self.indiLOG.log(20, u"old rejected/rejects file renamed to {} rejected/reject-1".format(self.indigoPreferencesPluginDir))
		except: pass


		self.fixConfig(checkOnly = ["all","rpi"],fromPGM="buttonConfirmMACnonactiveCALLBACK")
		ll2 = len(self.beacons)
		self.indiLOG.log(20, u"from initially good {} beacons # of beacons removed from BEACONlist:{}".format(ll0, ll0-ll2) )


####-------------------------------------------------------------------------####
	def buttonConfirmMACDeleteOLDHISTORYCALLBACK(self, valuesDict=None, typeId="", devId=0):
		delB = []
		ll0 = len(self.beacons)
		for beacon in self.beacons:
			if self.beacons[beacon][u"indigoId"] != 0:
				try:
					dd= indigo.devices[self.beacons[beacon][u"indigoId"]]
					continue
				except Exception, e:
					if unicode(e).find(u"timeout waiting") >-1: continue
					self.indiLOG.log(40,"Line {} has error={}".format(sys.exc_traceback.tb_lineno, e))

			#if int(self.beacons[beacon][u"ignore"]) != 2:			continue
			delB.append(beacon)

		for beacon in delB:
			self.indiLOG.log(20, u"beacon= {} removing from (deleted/ignored) history .. can be used again".format(beacon) )
			del self.beacons[beacon]

		delB=[]
		for mac in self.rejectedByPi:
			if mac not in self.beacons:
				delB.append(mac)
		for mac in delB:
			del self.rejectedByPi[mac]

		try:
			f = open(self.indigoPreferencesPluginDir + "rejected/rejectedByPi.json", u"r")
			self.rejectedByPi = json.loads(f.read())
			f.close()
		except:
			self.rejectedByPi = {}
	 
		try:
			f = open(self.indigoPreferencesPluginDir + "rejected/rejectedByPi.json", u"w")
			f.write(json.dumps(self.rejectedByPi))
			f.close()
			subprocess.call(u"rm '{}rejected/reject-1'".format(self.indigoPreferencesPluginDir), shell=True )
			subprocess.call(u"cp '{}rejected/rejects' '{}rejected/reject-1'".format(self.indigoPreferencesPluginDir, self.indigoPreferencesPluginDir), shell=True)
			subprocess.call(u"rm '{}rejected/rejects*'".format(self.indigoPreferencesPluginDir), shell=True )
			self.indiLOG.log(20, u"old rejected/rejects file renamed to {}rejected/reject-1".format(self.indigoPreferencesPluginDir))
		except: pass


		self.fixConfig(checkOnly = ["all","rpi"],fromPGM="buttonConfirmMACDeleteOLDHISTORYCALLBACK")
		ll2 = len(self.beacons)
		self.indiLOG.log(20, u"from initially good {} beacons # of beacons removed from BEACONlist: {}".format(ll0, ll0-ll2) )

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
					self.deviceStopCommIgnore = time.time()
					dev.replacePluginPropsOnServer(props)
				except:
					pass
		self.indiLOG.log(20, u"set all existing iBeacon devices to active")

		return valuesDict


####-------------------------------------------------------------------------####
	def filterMACfamilies(self, valuesDict=None, typeId="", devId=0):
		xList = []
		for uuid in self.beaconsIgnoreUUID:
			if uuid == "": continue
			xList.append((uuid, u"UUID family already ignored: " + uuid))  # 1a13ff4c00 up to here0c0e00931210948d9701e5
		xList = sorted(xList, key=lambda tup: tup[0])

		xList1 = []
		for mac in self.beacons:
			if len(mac) < 5: continue
			try:
				dev = indigo.devices[self.beacons[mac][u"indigoId"]]
				name = dev.name
				note12 = dev.description[:12]
				if note12 == "": continue
				xList1.append([note12,  + "{}    UUID: {}".format(name.encode("utf8"), note12)])
			except Exception, e:
				if unicode(e).find(u"timeout waiting") > -1:
					self.indiLOG.log(40,"Line {} has error={}".format(sys.exc_traceback.tb_lineno, e))
					self.indiLOG.log(40,u"communication to indigo is interrupted")
					return

		xList1 = sorted(xList1, key=lambda tup: tup[1])
		if self.decideMyLog(u"Logic"): self.indiLOG.log(10, u" family list:{}".format(xList + xList1))

		return xList + xList1

####-------------------------------------------------------------------------####
	def buttonConfirmMACIgnoreFamilyCALLBACK(self, valuesDict=None, typeId="", devId=0):
		uuid = valuesDict[u"ignoreMACfamily"]
		if uuid not in self.beaconsIgnoreUUID:
			self.beaconsIgnoreUUID[uuid]=True # 1a13ff4c00 up to here0c0e00931210948d9701e5
			self.setALLrPiV(u"piUpToDate", [u"updateParamsFTP"], resetQueue=True)
		return valuesDict

####-------------------------------------------------------------------------####
	def buttonConfirmMACunIgnoreFamilyCALLBACK(self, valuesDict=None, typeId="", devId=0):
		uuid = valuesDict[u"ignoreMACfamily"]
		if uuid in self.beaconsIgnoreUUID:
			del self.beaconsIgnoreUUID[uuid]
			self.setALLrPiV(u"piUpToDate", [u"updateParamsFTP"], resetQueue=True)

####-------------------------------------------------------------------------####
	def buttonConfirmMACemptyFamilyCALLBACK(self, valuesDict=None, typeId="", devId=0):
		self.beaconsIgnoreUUID = {}
		for piU in _rpiBeaconList:
			self.setONErPiV(piU,"piUpToDate", [u"updateParamsFTP"], resetQueue=True)
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
			else:
				for ii in range(10):
					if "INPUTdevId"+str(ii) in props and len(props["INPUTdevId"+str(ii)]) >3:
						valuesDict[u"i"+str(ii)] = True
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
				self.indiLOG.log(30,u"ERROR:  Reset counter of GPIO pin on rPi;	 dev:{}  not defined".format(valuesDict[u"inputDev"]))
				return

		devId=dev.id
		props = dev.pluginProps
		piU = props[u"piServerNumber"]
		resetGPIOCount = []
		theType= dev.deviceTypeId.split(u"-")[0]
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
						if u"gpio" in listGPIO[ii]:
							resetGPIOCount.append(listGPIO[ii][u"gpio"])

		elif "gpio" in props:
			gpio = props[u"gpio"]
			if valuesDict[u"INPUT_" +gpio]:
				resetGPIOCount.append(gpio)
		else:
			for ii in range(10):
				if valuesDict["INPUT_"+str(ii)] == True:
					if theType == "INPUTcoincidence":
						theType= "INPUTpulse"
						if "INPUTdevId"+str(ii) in props and len(props["INPUTdevId"+str(ii)])>3:
								resetGPIOCount.append(devId)
								break
				 
		if resetGPIOCount == []: return valuesDict

		textToSend = json.dumps([{u"device": typeId, u"command":"file","fileName":"/home/pi/pibeacon/temp/"+theType+".reset","fileContents":resetGPIOCount}])
		self.sendtoRPI(self.RPI[piU][u"ipNumberPi"], piU, textToSend, calledFrom="resetGPIOCountCALLBACKmenu")

		if self.decideMyLog(u"UpdateRPI"): self.indiLOG.log(10, u"resetGPIOCount requested: for {} on pi:{}; pins:{}".format(dev.name.encode("utf8"), piU, resetGPIOCount))
		return valuesDict

####-------------------------------------------------------------------------####
	def resetGPIOCountCALLBACKaction(self, action1=None, typeId="", devId=0):
		self.resetGPIOCountCALLBACKmenu(action1.props)
		return



####-------------------------------------------------------------------------####
	def filterChannels(self, filter="", valuesDict=None, typeId="", devId=""):
		#indigo.server.log(u"filterChannels "+unicode(valuesDict))
		xList=[]
		for ii in range(41):
			xList.append((unicode(41-ii),"Channel-"+unicode(41-ii)))
		xList.append((u"0","no pick"))
		return xList


####-------------------------------------------------------------------------####
	def confirmdeviceRPIanyPropBUTTON(self, valuesDict, typeId="", devId=""):
		try:
			self.anyProperTydeviceNameOrId = valuesDict[u"deviceNameOrId"]
		except:
			self.indiLOG.log(40, self.anyProperTydeviceNameOrId +" not in defined")
		return valuesDict

####-------------------------------------------------------------------------####
	def filterAnyPropertyNameACTION(self, filter="", valuesDict=None, typeId="", devId=""):
		xList=[]
		if self.anyProperTydeviceNameOrId ==0:
			return xList
		try: id = int(self.anyProperTydeviceNameOrId)
		except: id =self.anyProperTydeviceNameOrId
		try: dev = indigo.devices[id]
		except:
			self.indiLOG.log(40, unicode(self.anyProperTydeviceNameOrId) +" not in defined")
			return xList
		props = dev.pluginProps
		for nn in props:
			xList.append([nn,nn])
		return xList

####-------------------------------------------------------------------------####
	def setAnyPropertyCALLBACKaction(self, action1=None, typeId="", devId=0):
		valuesDict = action1.props

		try: id = int(valuesDict[u"deviceNameOrId"])
		except: id = valuesDict[u"deviceNameOrId"]
		try: dev = indigo.devices[id]
		except:
			self.indiLOG.log(40, valuesDict[u"deviceNameOrId"] +" not in indigodevices")
			return

		if u"propertyName" not in valuesDict:
			self.indiLOG.log(40, "u propertyName not in valuesDict")
			return
		props = dev.pluginProps
		propertyName =valuesDict[u"propertyName"] 
		if propertyName not in props:
			self.indiLOG.log(40, propertyName+" not in pluginProps")
			return
		if u"propertyContents" not in valuesDict:
			self.indiLOG.log(40,"propertyContents not in valuesDict")
			return
		self.indiLOG.log(20, u"updating {}     {}  {}".format(dev.name.encode("utf8"), propertyName, props[propertyName]))

		props[propertyName] = self.convertVariableOrDeviceStateToText(valuesDict[u"propertyContents"])

		self.deviceStopCommIgnore = time.time()
		dev.replacePluginPropsOnServer(props)
		return

####-------------------------------------------------------------------------####
	def getAnyPropertyCALLBACKaction(self, action1=None, typeId="", devId=0):
		valuesDict = action1.props
		##self.indiLOG.log(20, " property request:"+ unicode(valuesDict) )
		try:
			var = indigo.variables[u"piBeacon_property"]
		except:
			indigo.variable.create(u"piBeacon_property", u"", self.iBeaconFolderNameVariables)

		try: id = int(valuesDict[u"deviceNameOrId"])
		except: id = valuesDict[u"deviceNameOrId"]
		try: dev = indigo.devices[id]
		except: 
			self.indiLOG.log(40, valuesDict[u"deviceNameOrId"] +" not in indigodevices")
			indigo.variable.updateValue(u"piBeacon_property","{} not in indigodevices".format(valuesDict[u"deviceNameOrId"]))
			return {u"propertyName":"ERROR: " +valuesDict[u"deviceNameOrId"] +" not in indigodevices"}

		if u"propertyName" not in valuesDict:
			self.indiLOG.log(40, "propertyName not in valuesDict")
			indigo.variable.updateValue(u"piBeacon_property","propertyNamenot in valuesDict")
			return {u"propertyName":"ERROR:  propertyName  not in valuesDict"}
		props = dev.pluginProps
		propertyName =valuesDict[u"propertyName"] 
		if propertyName not in props:
			self.indiLOG.log(40, propertyName+" not in pluginProps")
			indigo.variable.updateValue(u"piBeacon_property",)
			return {u"propertyName":"ERROR: {} not in pluginProps".format(propertyName)}
		propertyContents = props[propertyName]
 

		indigo.variable.updateValue(u"piBeacon_property", propertyContents)

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
					self.indiLOG.log(40,u"error outputDev not set")
					vd[u"MSG"] = "error outputDev not set"
					return
###			   #self.indiLOG.log(20, unicode(vd))

			typeId			  = "setTEA5767"
			props			  = dev.pluginProps
			piServerNumber	  = props[u"address"].split(u"-")[1]
			ip				  = self.RPI[piServerNumber][u"ipNumberPi"]
			if self.decideMyLog(u"OutputDevice"): self.indiLOG.log(10, "pi: "+unicode(ip)+"  "+unicode(vd))

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
				self.deviceStopCommIgnore = time.time()
				dev.replacePluginPropsOnServer(props)
				dev = indigo.devices[devId]
				self.addToStatesUpdateDict(devId,"status"   ,"f= "+unicode(props[u"defFreq"]) + "; mute= " +unicode(props[u"mute"]))
				self.addToStatesUpdateDict(devId,"frequency",props[u"defFreq"],decimalPlaces=1)
				self.addToStatesUpdateDict(devId,"mute"     ,props[u"mute"])
				self.executeUpdateStatesDict(onlyDevID=unicode(devId), calledFrom="setTEA5767CALLBACKmenu")
				if props[u"mute"] ==u"1":
						dev.updateStateImageOnServer(indigo.kStateImageSel.SensorOff)
				else:
						dev.updateStateImageOnServer(indigo.kStateImageSel.SensorOn)

			startAtDateTime = 0
			if u"startAtDateTime" in valuesDict:
				startAtDateTime = self.setDelay(startAtDateTimeIN=self.convertVariableOrDeviceStateToText(vd[u"startAtDateTime"]))

			textToSend = json.dumps([{u"device": typeId, u"startAtDateTime":startAtDateTime,"command":"file","fileName":"/home/pi/pibeacon/setTEA5767.inp","fileContents":cmds}])


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
				if self.decideMyLog(u"OutputDevice"): self.indiLOG.log(10, "\n"+line+"\n")
			except:
				if self.decideMyLog(u"OutputDevice"): self.indiLOG.log(10, "use this as a python script command:\n"+"plug = indigo.server.getPlugin(\"com.karlwachs.piBeacon\")\nplug.executeAction(\"setTEA5767\" ,	props =(u"+
				  json.dumps({u"outputDev":vd[u"outputDev"],"device": typeId})+" error")
			self.sendtoRPI(ip, piServerNumber, textToSend, calledFrom="setTEA5767CALLBACKmenu")
			vd[u"MSG"] = " ok"
		except Exception, e:
				self.indiLOG.log(40,"Line {} has error={}".format(sys.exc_traceback.tb_lineno, e))


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

		except Exception, e:
			self.indiLOG.log(40,"Line {} has error={}".format(sys.exc_traceback.tb_lineno, e))
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
		vd["windowStart"] = vd["fromWindow"]+" .. to "+ unicode(int(vd["fromWindow"])+10)
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
			###if self.decideMyLog(u"OutputDevice"): self.indiLOG.log(10, "setdisplayCALLBACKmenu: "+ unicode(vd))
			try:
				dev = indigo.devices[int(vd[u"outputDev"])]
			except:
				try:
					dev = indigo.devices[vd[u"outputDev"]]
				except:
					self.indiLOG.log(20, u"setdisplayCALLBACKmenu error outputDev not set")
					vd[u"MSG"] = "error outputDev not set"
					return
###			   #self.indiLOG.log(20, unicode(vd))

			props = dev.pluginProps
			piServerNumber	  = props[u"address"].split(u"-")[1]
			typeId			  = "OUTPUT-Display"
			if u"command" in vd:
				cmds = vd[u"command"]
				for iii in range(200):
					if u"%%v:" not in cmds and "%%d:" not in cmds and "%%eval:" not in cmds and "%%FtoC:" not in cmds: break
					cmds= self.convertVariableOrDeviceStateToText(self.convertVariableOrDeviceStateToText(cmds))

				if cmds .find(u"[{'") ==0: #  this will not work for json  replace ' with " as text delimiters and save any " 
					cmds = cmds.replace(u"'","aa123xxx123xxxaa").replace('"',"'").replace(u"aa123xxx123xxxaa",'"')

				try:
					cmds = json.loads(cmds)
				except Exception, e:
					if len(unicode(e)) > 5 :
						self.indiLOG.log(40,"Line {} has error={}".format(sys.exc_traceback.tb_lineno, e))
					self.indiLOG.log(40,u"setdisplayCALLBACKmenuv error in json conversion for "+unicode(cmds))
					vd[u"MSG"] = "error in json conversion"
					return
				if self.decideMyLog(u"OutputDevice"): self.indiLOG.log(10, " after json conversion:"+unicode(cmds)+"\n")

				delCMDS =[]					   
				for ii in range(len(cmds)):
					cType = cmds[ii][u"type"]
					if cType == "0" or cType == "" or \
						cType not in [u"text",u"textWformat",u"clock",u"dateString",u"analogClock",u"digitalClock",u"date",u"NOP",u"line",u"point",u"ellipse",u"vBar",u"hBar",u"vBarwBox",u"hBarwBox",u"labelsForPreviousObject",u"rectangle",u"triangle",u"hist",u"exec",u"image",u"dot"]:
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
								self.indiLOG.log(40," error in input: position= "+  unicode(cmds[ii][u"position"]) )	 
								valuesDict[u"MSG"] = "error in position"
					if cType =="textWformat" and u"text" in cmds[ii] and "FORMAT" in cmds[ii][u"text"]: 
						try:
							xx = cmds[ii][u"text"].split("FORMAT")
							cmds[ii][u"text"] = xx[1]%(float(xx[0]))
						except:
							self.indiLOG.log(40,"setdisplayCALLBACK error in formatting: "+ unicode(cmds[ii][u"text"]))
					if cType not in[u"text",u"textWformat",u"dateString",u"image"]:
						if u"text" in cmds[ii]: del cmds[ii][u"text"]
				if len(delCMDS) >0:
					for ii in delCMDS[::-1]:
						del cmds[ii]

			else:
				###if self.decideMyLog(u"OutputDevice"): self.indiLOG.log(10, "input:"+ unicode(vd))
				cmds =[]
				nn =-1
				for ii in range(100):
					iiS = unicode(ii)
					if u"type"+iiS not in vd: continue
					cType = vd[u"type"+iiS]
					if cType == "0":				  continue
					if cType == "":					  continue
					if cType in [u"text",u"textWformat",u"clock",u"dateString",u"digitalClock",u"analogClock",u"date",u"NOP",u"line",u"point",u"ellipse",u"vBar",u"hBar",u"vBarwBox",u"hBarwBox",u"labelsForPreviousObject",u"rectangle",u"triangle",u"hist",u"exec",u"image",u"dot"]:
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
							if cType =="textWformat" and "%%FORMAT:" in cmds[nn][u"text"]: 
								try:
									xx = cmds[nn][u"text"].split("%%FORMAT:")
									cmds[nn][u"text"] = xx[1]%(float(xx[0]))
								except:
									self.indiLOG.log(40,"setdisplayCALLBACK error in formatting: "+ unicode(cmds[nn][u"text"]))
							   
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
							if cType == u"labelsForPreviousObject":
								try: cmds[nn][u"position"]	= json.loads(self.convertVariableOrDeviceStateToText(vd[u"position"+iiS]))
								except: pass
							else:
								cmds[nn][u"position"]		= self.addBrackets(self.convertVariableOrDeviceStateToText(vd[u"position"+iiS]),cType=cType)

						if u"offONTime"+iiS in vd:
							cmds[nn][u"offONTime"]		  = self.addBrackets( self.convertVariableOrDeviceStateToText(vd[u"offONTime"+iiS]), cType=3, default=[0,999999999,0] )

						if cType not in[u"text",u"textWformat",u"dateString",u"image","labelsForPreviousObject"]:
							if u"text" in cmds[nn]:	 del cmds[nn][u"text"]
						if cType == "point":
							if u"width" in cmds[nn]: del cmds[nn][u"width"]


				#self.indiLOG.log(20,	unicode(vd))
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
			xwindowSize 		= "0,0"
			xwindows			= "off"
			zoom 				= 1.0

			if u"repeat" in vd:
				repeat = self.convertVariableOrDeviceStateToText(vd[u"repeat"])

			if u"xwindows" in vd and vd["xwindows"].lower() == "on":
				if u"xwindowSize" in vd:
					xwindows	= "ON"
					xwindowSize = self.convertVariableOrDeviceStateToText(vd[u"xwindowSize"])
		
			if u"intensity" in vd:
				intensity = self.convertVariableOrDeviceStateToText(vd[u"intensity"])

			if u"resetInitial" in vd:
				resetInitial = self.convertVariableOrDeviceStateToText(vd[u"resetInitial"])

			if u"zoom" in vd:
				zoom = self.convertVariableOrDeviceStateToText(vd[u"zoom"])

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
				line +="\n     \"outputDev\":\""+unicode(vd[u"outputDev"])+"\""
				line +="\n    ,\"device\":\"" +unicode(typeId)+"\""
				line +="\n    ,\"restoreAfterBoot\":\""+unicode(restoreAfterBoot)+"\""
				line +="\n    ,\"intensity\":\""+unicode(intensity)+"\""
				line +="\n    ,\"xwindows\":\""+(xwindows)+"\""
				line +="\n    ,\"xwindowSize\":\""+unicode(xwindowSize)+"\""
				line +="\n    ,\"zoom\":\""+unicode(zoom)+"\""
				line +="\n    ,\"repeat\":\""+unicode(repeat)+"\""
				line +="\n    ,\"resetInitial\":\""+unicode(resetInitial)+"\""
				line +="\n    ,\"scrollxy\":\""+unicode(scrollxy)+"\""
				line +="\n    ,\"showDateTime\":\""+unicode(showDateTime)+"\""
				line +="\n    ,\"startAtDateTime\":\""+unicode(startAtDateTime)+"\""
				line +="\n    ,\"scrollPages\":\""+unicode(scrollPages)+"\""
				line +="\n    ,\"scrollDelay\":\""+unicode(scrollDelay)+"\""
				line +="\n    ,\"scrollDelayBetweenPages\":\""+unicode(scrollDelayBetweenPages)+"\""
				line +="\n    ,\"command\":'['+\n     '"

				### this will create list of dicts, one per command, remove blank items, sort  ,.. 
				doList =[u"type",u"position",u"width",u"fill",u"font",u"text",u"offONTime",u"display",u"reset",u"labelsForPreviousObject"] # sorted by this
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
						line  = line.strip(u", ") + "}'+\n     ',"

				## finish cmd lines
				line  = line.strip(u"'+\n      ',")	+ "]'\n  })\n"
				## end of output
				line += "##=======   end  =====\n"

				if self.decideMyLog(u"OutputDevice"): self.indiLOG.log(10, "\n"+line+"\n")
				vd[u"MSG"] = " ok"

			except Exception, e:
				if len(unicode(e)) > 5 :
					self.indiLOG.log(40,"Line {} has error={}".format(sys.exc_traceback.tb_lineno, e))
					vd[u"MSG"] = "error"
			jData = {u"device": typeId,  "restoreAfterBoot": False, u"intensity":intensity, u"zoom":zoom,"repeat":repeat,"resetInitial":resetInitial,"startAtDateTime":startAtDateTime,
				u"scrollxy":scrollxy, u"showDateTime":showDateTime,"scrollPages":scrollPages,"scrollDelay":scrollDelay,"scrollDelayBetweenPages":scrollDelayBetweenPages,
				u"command": cmds}
			if xwindows.lower() == "on" and xwindowSize !="0,0":
				jData["xwindows"] = xwindows
				jData["xwindowSize"] = xwindowSize
			textToSend = json.dumps([jData])
			self.sendtoRPI(ip, piServerNumber, textToSend, calledFrom="setdisplayCALLBACKmenu")

		except Exception, e:
			if len(unicode(e)) > 5 :
				self.indiLOG.log(40,"Line {} has error={}".format(sys.exc_traceback.tb_lineno, e))
				self.indiLOG.log(40,u"error display check "+unicode(vd))
				valuesDict[u"MSG"] = "error in parameters"
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
		except Exception, e:
			if len(unicode(e)) > 5 :
				self.indiLOG.log(40,"Line {} has error={}".format(sys.exc_traceback.tb_lineno, e))
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
			elif	cType ==u"labelsForPreviousObject":	 nItems = 0
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
				self.indiLOG.log(20, "addBrackets error in input: pos= {}; wrong number of coordinates, should be: {}".format(pos, nItems) )

			return pp
		except Exception, e:
			self.indiLOG.log(40,"Line {} has error={}".format(sys.exc_traceback.tb_lineno, e))
			self.indiLOG.log(40,"addBrackets error in input: cType:{};  default= {};  pos= {}".format(cType, default, pos) )	 
		return default



####-------------------------------------------------------------------------####
	def setneopixelCALLBACKaction(self, action1=None, typeId="", devId=0):
		valuesDict = action1.props
		return self.setneopixelCALLBACKmenu(valuesDict)[u"MSG"]

####-------------------------------------------------------------------------####
	def setneopixelCALLBACKmenu(self, valuesDict=None, typeId="", devId=0):
		try:
			vd=valuesDict
			vd[u"MSG"] = ""
			try:
				devId = int(vd[u"outputDev"])
				dev = indigo.devices[devId]
			except:
				try:
					dev = indigo.devices[vd[u"outputDev"]]
					devId = dev.id
				except:
					self.indiLOG.log(40, u"error outputDev not set")
					vd[u"MSG"] = "error outputDev not set"
					return vd
###			   #self.indiLOG.log(20, unicode(vd))

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
				if self.decideMyLog(u"OutputDevice"): self.indiLOG.log(10, "input:\n"+ unicode(vd[u"command"])+"\n result:\n"+unicode(cmds)+"\n")

				if cmds .find(u"[{'") ==0: #  this will not work for json  replace ' with " as text delimiters and save any " 
					cmds = cmds.replace(u"'","aa123xxx123xxxaa").replace('"',"'").replace(u"aa123xxx123xxxaa",'"')

				try:
					cmds = json.loads(cmds)
				except Exception, e:
					if len(unicode(e)) > 5 :
						self.indiLOG.log(40,"Line {} has error={}".format(sys.exc_traceback.tb_lineno, e))
					self.indiLOG.log(40,u"error in json conversion for "+unicode(cmds))
					vd[u"MSG"] = "error in json conversion"
					return
				if self.decideMyLog(u"OutputDevice"): self.indiLOG.log(10, " after json conversion:\n"+unicode(cmds)+"\n")

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
					iiC= unicode(ii)
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
							if self.decideMyLog(u"OutputDevice"):self.indiLOG.log(20, ";  startPixelx:"+unicode(startPixelx) +";  endPixelx:"+unicode(endPixelx) +";  startPixelRGB:"+unicode(startPixelRGB)+";   endPixelRGB:"+unicode(endPixelRGB) +";   deltaColorSteps:"+unicode(deltaColorSteps)	 ) 
							nsteps	   =  max(0,abs(endPixelx - startPixelx))
							deltaC	   =  [endPixelRGB[ll] - startPixelRGB[ll] for ll in range(3)]
							deltaCabs  =  map(abs, deltaC)
							deltaCN	   =  sum(deltaCabs)
							stepSize   =  float(deltaCN)/ max(1,nsteps)	 
							stepSizeSign   =  [cmp(deltaC[0],0),cmp(deltaC[1],0),cmp(deltaC[2],0)] 
							if self.decideMyLog(u"OutputDevice"):self.indiLOG.log(20, ";  nsteps:"+unicode(nsteps) +";  deltaC:"+unicode(deltaC) +";  deltaCabs:"+unicode(deltaCabs) +";  deltaCN:"+unicode(deltaCN) +";  stepSize:"+unicode(stepSize)+";  stepSizeSign:"+unicode(stepSizeSign) ) 
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
							if self.decideMyLog(u"OutputDevice"):self.indiLOG.log(20, unicode(pos)) 
							cmds[nn][u"position"] = pos
						else:
							vd[u"MSG"] = "error in type"
							return vd


				#self.indiLOG.log(20,	unicode(vd))
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
				line +="\n     \"outputDev\":\""+unicode(vd[u"outputDev"])+"\""
				line +="\n    ,\"device\":\"" +unicode(typeId)+"\""
				line +="\n    ,\"restoreAfterBoot\":"+unicode(restoreAfterBoot)
				line +="\n    ,\"intensity\":"+unicode(intensity)
				line +="\n    ,\"repeat\":"+unicode(repeat)
				line +="\n    ,\"resetInitial\":\""+unicode(resetInitial)+"\""
				line +="\n    ,\"command\":'['+\n     '"
				for cc in cmds:
					line+=json.dumps(cc)+"'+\n    ',"
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


				line = line.strip(u"'+\n     ',")	 
				line+="]'\n	 })\n"
				line+= "##=======   end   =====\n"
				if self.decideMyLog(u"OutputDevice"): self.indiLOG.log(10, "\n"+line+"\n")
			except Exception, e:
				if len(unicode(e)) > 5 :
					self.indiLOG.log(40,"Line {} has error={}".format(sys.exc_traceback.tb_lineno, e))
				if self.decideMyLog(u"OutputDevice"): self.indiLOG.log(40,"use this as a ppython script command:\n"+"plug = indigo.server.getPlugin(\"com.karlwachs.piBeacon\")\nplug.executeAction(\"Neopixel\" , props ="+
				  (json.dumps({u"outputDev":vd[u"outputDev"],"device": typeId, "restoreAfterBoot": False, u"intensity":intensity,"repeat":repeat,"resetInitial":resetInitial})).strip(u"}").replace(u"false","False").replace(u"true","True")+"\n,\"command\":'"+json.dumps(cmds) +"'})"+"\n")
				self.indiLOG.log(20, u"vd: "+unicode(vd))

			chList= []
			if "writeOutputToState" not in props or ("writeOutputToState" in props and props["writeOutputToState"] == "1"):
				chList.append({u"key":u"OUTPUT",u"value": unicode(cmds).replace(u" ","")})
			chList.append({u"key":u"status",u"value": round(maxRGB/2.55)})
			self.execUpdateStatesList(dev,chList)
			if lightON:
				dev.updateStateImageOnServer(indigo.kStateImageSel.PowerOn)
			else:
				dev.updateStateImageOnServer(indigo.kStateImageSel.PowerOff)

			self.sendtoRPI(ip, piServerNumber, textToSend, calledFrom="setneopixelCALLBACKmenu")
			vd[u"MSG"] = " ok"

		except Exception, e:
			if len(unicode(e)) > 5 :
				self.indiLOG.log(40,"Line {} has error={}".format(sys.exc_traceback.tb_lineno, e))
				self.indiLOG.log(40,u"error display check "+unicode(vd))
				valuesDict[u"MSG"] = "error in parameters"
		return vd


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
			if self.decideMyLog(u"OutputDevice"): self.indiLOG.log(10, "setdisplayCALLBACKmenu: "+ unicode(vd))
			try:
				dev = indigo.devices[int(vd[u"outputDev"])]
			except:
				try:
					dev = indigo.devices[vd[u"outputDev"]]
				except:
					self.indiLOG.log(40, u"error outputDev not set")
					vd[u"MSG"] = "error outputDev not set"
					return
###			   #self.indiLOG.log(20, unicode(vd))

			props = dev.pluginProps
			piServerNumber	  = props[u"address"].split(u"-")[1]
			typeId			  = "setStepperMotor"
			if u"command" in vd:
				cmds = vd[u"command"]
				for iii in range(200):
					if u"%%v:" not in cmds and "%%d:" not in cmds: break
					cmds= self.convertVariableOrDeviceStateToText(self.convertVariableOrDeviceStateToText(cmds))
				if self.decideMyLog(u"OutputDevice"): self.indiLOG.log(10, "input:"+ unicode(vd[u"command"])+" result:"+unicode(cmds)+"\n")

				try:
					cmds = json.loads(cmds)
				except Exception, e:
					if len(unicode(e)) > 5 :
						self.indiLOG.log(40,"Line {} has error={}".format(sys.exc_traceback.tb_lineno, e))
					self.indiLOG.log(40,u"error in json conversion for "+unicode(cmds))
					vd[u"MSG"] = "error in json conversion"
					return
				if self.decideMyLog(u"OutputDevice"): self.indiLOG.log(10, " after json conversion:"+unicode(cmds)+"\n")


			else:
				###if self.decideMyLog(u"OutputDevice"): self.indiLOG.log(10, "input:"+ unicode(vd))
				cmds =[]
				nn =-1
				for ii in range(100):
						iiS = unicode(ii)
						if u"cmd-"+iiS in vd:
							cmds.append({}); nn+=1
							if  vd["cmd-"+iiS] =="steps":
								if u"steps-"+iiS in vd:		
									try:  cmds[nn][u"steps"] 		= int(vd["steps-"+iiS])
									except: cmds[nn][u"steps"] 		= 0

								if u"waitBefore-"+iiS in vd:	
									try: cmds[nn][u"waitBefore"]		= float(vd["waitBefore-"+iiS])
									except: cmds[nn][u"waitBefore"]	= 0

								if u"waitAfter-"+iiS in vd:	
									try: cmds[nn][u"waitAfter"]		= float(vd["waitAfter-"+iiS])
									except: cmds[nn][u"waitAfter"]	= 0

								if u"stayOn-"+iiS in vd:	
									try: cmds[nn][u"stayOn"]		= int(vd["stayOn-"+iiS])
									except: cmds[nn][u"stayOn"] 		= 1

								if u"dir-"+iiS in vd:	
									try: cmds[nn][u"dir"]			= int(vd["dir-"+iiS])
									except: cmds[nn][u"dir"] 		= 1

								if u"GPIO.0-"+iiS in vd:
									try: cmds[nn][u"GPIO.0"]		= int(vd["GPIO.0-"+iiS])
									except: pass

								if u"GPIO.1-"+iiS in vd:
									try: cmds[nn][u"GPIO.1"]		= int(vd["GPIO.1-"+iiS])
									except: pass

								if u"GPIO.2-"+iiS in vd:
									try: cmds[nn][u"GPIO.2"]		= int(vd["GPIO.2-"+iiS])
									except: pass

							elif vd["cmd-"+iiS] == "sleepMotor":
								cmds[nn][u"sleepMotor"] 			= 1
								if u"waitBefore-"+iiS in vd:	
									try: cmds[nn][u"waitBefore"]		= float(vd["waitBefore-"+iiS])
									except: cmds[nn][u"waitBefore"] 	= 0
								if u"waitAfter-"+iiS in vd:	
									try: cmds[nn][u"waitAfter"]		= float(vd["waitAfter-"+iiS])
									except: cmds[nn][u"waitAfter"] 	= 0


							elif vd["cmd-"+iiS] == "wakeMotor":
								cmds[nn][u"wakeMotor"] 			= 1
								if u"waitBefore-"+iiS in vd:	
									try: cmds[nn][u"waitBefore"]		= float(vd["waitBefore-"+iiS])
									except: cmds[nn][u"waitBefore"] 	= 0
								if u"waitAfter-"+iiS in vd:	
									try: cmds[nn][u"waitAfter"]		= float(vd["waitAfter-"+iiS])
									except: cmds[nn][u"waitAfter"] 	= 0

							elif vd["cmd-"+iiS] == "offMotor":
								cmds[nn][u"offMotor"] 				= 1
								if u"waitBefore-"+iiS in vd:	
									try: cmds[nn][u"waitBefore"]		= float(vd["waitBefore-"+iiS])
									except: cmds[nn][u"waitBefore"] 	= 0
								if u"waitAfter-"+iiS in vd:	
									try: cmds[nn][u"waitAfter"]		= float(vd["waitAfter-"+iiS])
									except: cmds[nn][u"waitAfter"] 	= 0

							elif vd["cmd-"+iiS] == "onMotor":
								cmds[nn][u"onMotor"] 				= 1
								if u"waitBefore-"+iiS in vd:	
									try: cmds[nn][u"waitBefore"]		= float(vd["waitBefore-"+iiS])
									except: cmds[nn][u"waitBefore"] 	= 0
								if u"waitAfter-"+iiS in vd:	
									try: cmds[nn][u"waitAfter"]		= float(vd["waitAfter-"+iiS])
									except: cmds[nn][u"waitAfter"] 	= 0


							elif vd["cmd-"+iiS] == "wait":
								cmds[nn][u"wait"] 					= int(vd["wait-"+iiS])
								
							if cmds[nn] == {}: del cmds[-1]

				#self.indiLOG.log(20,	unicode(vd))
			ip = self.RPI[piServerNumber][u"ipNumberPi"]

			startAtDateTime = 0
			if u"startAtDateTime" in valuesDict:
				startAtDateTime = self.setDelay(startAtDateTimeIN=self.convertVariableOrDeviceStateToText(vd[u"startAtDateTime"]))

			repeat				= 1
			if u"repeat" in vd:
				repeat = self.convertVariableOrDeviceStateToText(vd[u"repeat"])

			waitForLast				= "1"
			if u"waitForLast" in vd:
				waitForLast = self.convertVariableOrDeviceStateToText(vd[u"waitForLast"])

			try:
				line = "\n##=======use this as a python script in an action group action :=====\n"
				line +="plug = indigo.server.getPlugin(\"com.karlwachs.piBeacon\")"
				line +="\nplug.executeAction(\"StepperMotor\" ,	props ={"
				line +="\n     \"outputDev\":\""+unicode(vd[u"outputDev"])+"\""
				line +="\n    ,\"device\":\"" +unicode(typeId)+"\""
				line +="\n    ,\"dev.id\":\"" +unicode(dev.id)+"\""
				line +="\n    ,\"repeat\":\""+unicode(repeat)+"\""
				line +="\n    ,\"waitForLast\":\""+unicode(waitForLast)+"\""
				line +="\n    ,\"command\":'['+\n     '"

				### this will create list of dicts, one per command, remove blank items, sort  ,.. 
				doList =["steps", "sleepMotor",  "offMotor", "wait", "stayON", "waitBefore", "waitAfter", "dir", "GPIO.0", "GPIO.1", "GPIO.2"] # sorted by this
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
						line  = line.strip(u", ") + "}'+\n    ',"

				## finish cmd lines
				line  = line.strip(u"'+\n        ',")	+ "]'\n	 })\n"
				## end of output
				line += "##=======   end   =====\n"

				if self.decideMyLog(u"OutputDevice"): self.indiLOG.log(10, "\n"+line+"\n")
				vd[u"MSG"] = " ok"

			except Exception, e:
				if len(unicode(e)) > 5 :
					self.indiLOG.log(40,"Line {} has error={}".format(sys.exc_traceback.tb_lineno, e))
					vd[u"MSG"] = "error"
			textToSend = json.dumps([{u"device": typeId, "repeat":repeat, "waitForLast":waitForLast,"dev.id":dev.id, "startAtDateTime":startAtDateTime, u"command": cmds}])
			self.sendtoRPI(ip, piServerNumber, textToSend, calledFrom="setStepperMotorCALLBACKmenu")

		except Exception, e:
			if len(unicode(e)) > 5 :
				self.indiLOG.log(40,"Line {} has error={}".format(sys.exc_traceback.tb_lineno, e))
				self.indiLOG.log(40,u"error stepperMotor check "+unicode(vd))
				valuesDict[u"MSG"] = "error in parameters"
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
					self.indiLOG.log(40,"Line {} has error={}".format(sys.exc_traceback.tb_lineno, e))
					self.indiLOG.log(40," error in input: "+item+" ii="+unicode(ii)+" nn="+unicode(nn)+ " cmds="+	 unicode(cmds) + " xxx="+  unicode(xxx))
					vd[u"MSG"] = "error in parameter"
				return cmds,vd, False
		except Exception, e:
			if len(unicode(e)) > 5 :
				self.indiLOG.log(40,"Line {} has error={}".format(sys.exc_traceback.tb_lineno, e))
				self.indiLOG.log(40,u"item " +unicode(item)+unicode(ii)+"  , vd "+unicode(vd))
			return cmds,vd, False
		return cmds,vd, True



####-------------------------------------------------------------------------####
	def sendFileToRPIviaSocket(self,ip, piU, fileName,fileContents,fileMode="w",touchFile=True):
		try: 
			out= (json.dumps([{u"command":"file","fileName":fileName,"fileContents":fileContents,"fileMode":fileMode,"touchFile":touchFile}]))
			if self.decideMyLog(u"OutputDevice"): self.indiLOG.log(10,	u"sending file to  "+ip+";  "+ out )
			self.sendtoRPI(ip, piU, out, calledFrom="sendFileToRPIviaSocket")
		except Exception, e:
				self.indiLOG.log(40,"Line {} has error={}".format(sys.exc_traceback.tb_lineno, e))
		return




####-------------------------------------------------------------------------####
	def presendtoRPI(self, piU, out):
		retC = 0
		if piU == u"999":
			for piU in self.RPI:
				if self.RPI[piU][u"ipNumberPi"] == "":	 continue
				if self.RPI[piU][u"piOnOff"]	== u"":	 continue
				if self.RPI[piU][u"piOnOff"]	== u"0": continue
				retC = max(retC, self.sendtoRPI(self.RPI[piU][u"ipNumberPi"], piU, out , calledFrom="presendtoRPI 1") )
		else:
			if self.RPI[piU][u"piOnOff"]	== u"":	 return	 2
			if self.RPI[piU][u"piOnOff"]	== u"0": return	 2
			if self.RPI[piU][u"ipNumberPi"] == u"":	 return	 2
			retC = self.sendtoRPI(self.RPI[piU][u"ipNumberPi"], piU, out, calledFrom="presendtoRPI 2")

		return retC

####-------------------------------------------------------------------------####
	def sendtoRPI(self, ip, pi, theString, force = False, calledFrom=""):

		try:
			piU = unicode(pi)
			if ip not in self.checkIPSendSocketOk:
				self.checkIPSendSocketOk[ip] = {u"count":0,u"time":0, u"pi": piU}

			if self.checkIPSendSocketOk[ip][u"count"] > 5 and not force:
				if time.time() + self.checkIPSendSocketOk[ip][u"time"] > 120:
					self.checkIPSendSocketOk[ip][u"count"] = 0
				else: 
					self.indiLOG.log(20, u"sendtoRPI sending to pi# {}  {} skipped due to recent failure count, reset by dis-enable & enable rPi ;  command-string={};  calledFrom:{}".format(piU, ip, theString, calledFrom) )
					return -1

			if self.decideMyLog(u"OutputDevice") or self.decideMyLog(u"SocketRPI"): self.indiLOG.log(10, u"sendtoRPI sending to  {} {} command-string={};  calledFrom:{}".format(piU, ip, theString, calledFrom) )
				# Create a socket (SOCK_STREAM means a TCP socket)
			sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
			sock.settimeout(3.)
			try:
					# Connect to server and send data
					sock.connect((ip, int(self.rPiCommandPORT)))
					sock.sendall(theString + "\n")
			except Exception, e:
					if len(unicode(e)) > 5 :
						if	time.time() > self.currentlyBooting:  # NO MSG IF RPIS ARE BOOTING
							if time.time() - self.RPIBusy[piU]  > 20: # supress warning if we just updated the RPI
								self.indiLOG.log(20, u"socket-send not working,  rPi:{} {} is currently updating, delaying send".format(piU, ip) )
							else:
								if unicode(e).find("onnection refused") ==-1:
									self.indiLOG.log(30, u"error in socket-send to rPi:{} {}  cmd= {}...{}".format(piU, ip, theString[0:30],theString[-30:]) )
								else:
									self.indiLOG.log(30, u"error in socket-send to rPi:{} {}, connection refused, rebooting/restarting RPI?".format(piU, ip) )
							self.checkIPSendSocketOk[ip][u"count"] += 1 
							self.checkIPSendSocketOk[ip][u"time"]	= time.time()
						try:	sock.close()
						except: pass
						return -1
			finally:
					sock.close()
		except Exception, e:
			if len(unicode(e)) > 5 :
				if	time.time() > self.currentlyBooting: # NO MSG IF RPIS ARE BOOTING
					if unicode(e).find("onnection refused") ==-1:
						self.indiLOG.log(40, u"error in socket-send to rPi:{} {}  cmd= {}..{}".format(piU, ip, theString[0:30],theString[-30:]) )
						self.indiLOG.log(40,"Line {} has error={}".format(sys.exc_traceback.tb_lineno, e))
					else:
						self.indiLOG.log(30, u"error in socket-send to rPi:{} (), connection refused,  rebooting/restarting RPI?".format(piU, ip) )
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
		except Exception, e:
			self.indiLOG.log(40,"Line {} has error={}".format(sys.exc_traceback.tb_lineno, e))
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
		except Exception, e:
			self.indiLOG.log(40,"Line {} has error={}".format(sys.exc_traceback.tb_lineno, e))
		return valuesDict

####-------------------------------------------------------------------------####
	def getBeaconParametersCALLBACKmenu(self, valuesDict=None, typeId="", devId=0, force=True):
		

		if not force and self.checkBeaconParametersDisabled: return 

		devices = {}

		if  valuesDict is None: return  valuesDict
		beacon = ""
		if devId != 0: 
			try: 
				beaconDev = indigo.devices[devId]
				beacon =  beaconDev.address
				valuesDict["piServerNumber"]  = "all"
			except:
				pass

		if "piServerNumber" not in  valuesDict: return  valuesDict
		if valuesDict["piServerNumber"]  == "-1": return  valuesDict
		for piU in _rpiBeaconList:
			if valuesDict["piServerNumber"] == piU or valuesDict["piServerNumber"] == "all" or valuesDict["piServerNumber"] == "999":
				devices[piU] = {} 

		minTime ={}
		for piU2 in _rpiList:
			minTime[piU2] = 0 

		for dev in indigo.devices.iter("props.isBeaconDevice"):
			props = dev.pluginProps
			if dev.states["status"] !="up": continue
			if beacon != "" and (dev.address != beacon or devId != dev.id): continue
			if valuesDict["piServerNumber"] == "all" or valuesDict["piServerNumber"] == "999":
				piU = str(dev.states["closestRPI"])
			else:
				piU = valuesDict["piServerNumber"]

			if piU not in _rpiBeaconList: continue

			dd = []
			if "SupportsBatteryLevel" in props and props["SupportsBatteryLevel"]:
				if "batteryLevelUUID" in props  and len(props["batteryLevelUUID"]) >2 and props["batteryLevelUUID"] !="off":
					try: 	batteryLevelLastUpdate = self.getTimetimeFromDateString(dev.states["batteryLevelLastUpdate"])
					except: batteryLevelLastUpdate = 0
					try: 	batteryLevel = int(dev.states["batteryLevel"])
					except: batteryLevel = 0
					if force or   batteryLevel < 20   or   (time.time() - batteryLevelLastUpdate) > (3600*17): # if successful today and battery level > 30% dont need to redo it again
						try: 
							dist= float( dev.states["Pi_"+piU.rjust(2,"0")+"_Distance"] )
							if dist < 99.:
								dd.append(props["batteryLevelUUID"])
								minTime[piU] += 10
								if self.decideMyLog(u"BatteryLevel"): self.indiLOG.log(20,"getBeaconParameters requesting update from RPI:{:2s} for beacon: {:30s}; lastV: {:3d}; last sucessfull check @: {}; distance to RPI:{:4.1f};".format(piU, dev.name.encode("utf8"), dev.states["batteryLevel"], dev.states["batteryLevelLastUpdate"], dist) )
						except Exception, e:
							self.indiLOG.log(40,"Line {} has error={}".format(sys.exc_traceback.tb_lineno, e))

					else:
						if self.decideMyLog(u"BatteryLevel"): self.indiLOG.log(20, "getBeaconParameters no update needed              for beacon: {:30s}; lastV: {:3d}; last sucessfull check @: {}".format(dev.name.encode("utf8"), dev.states["batteryLevel"], dev.states["batteryLevelLastUpdate"] ) )

				if "txPowerlevelUUID" in props  and len(props["txPowerlevelUUID"]) >2 and props["txPowerlevelUUID"] !="off":
					dd.append(props["txPowerlevelUUID"])
					

			if dd !=[]:
				devices[piU][dev.address] =dd

		minTime    = max(list(minTime.values()))
		nDownAddWait = True
		for piU2 in devices:
				if devices[piU2] == {}: 
					if valuesDict["piServerNumber"] == "all" or valuesDict["piServerNumber"] == "999":
						if self.decideMyLog(u"BatteryLevel"): self.indiLOG.log(20,"no active beacons on rpi#{}".format(piU) )
				else:
					xx={}
					xx[u"cmd"]		 		= "getBeaconParameters"
					xx[u"typeId"]			= json.dumps(devices[piU2])
					xx[u"piServerNumber"]	= piU2

					if self.decideMyLog(u"BatteryLevel"): self.indiLOG.log(20,"getBeaconParameters request list for pi{};  {}".format(piU2, xx) )

					if nDownAddWait: self.setCurrentlyBooting(minTime+10, setBy="getBeaconParameters (batteryLevel ..)")
					nDownAddWait = False
					self.setPin(xx)

		return valuesDict

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
				self.addToStatesUpdateDict(dev.id, key, 0)
			self.addToStatesUpdateDict(dev.id, "resetDate", datetime.datetime.now().strftime(_defaultDateStampFormat))
			self.executeUpdateStatesDict(onlyDevID=dev.id,calledFrom="setresetDeviceCALLBACKmenu")

			dev2 = indigo.devices[dev.id]
			props= dev2.pluginProps
			for key in ["hourRainTotal","dayRainTotal" ,"weekRainTotal","monthRainTotal","yearRainTotal"]:
				props[key] = 0
			self.deviceStopCommIgnore = time.time()
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


# noinspection SpellCheckingInspection
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
						except Exception, e:
							self.indiLOG.log(40,"Line {} has error={}".format(sys.exc_traceback.tb_lineno, e))
							return
				except Exception, e:
					self.indiLOG.log(40,"Line {} has error={}".format(sys.exc_traceback.tb_lineno, e))
					return

				if self.decideMyLog(u"OutputDevice"): self.indiLOG.log(10, "{}".format(action) )
	 
				if not action.configured:
					self.indiLOG.log(20, "actionControlDimmerRelay neopixel-dimmer not enabled:{}".format(unicode(dev0.name)) )
					return
				###action = dev.deviceAction
				if u"pixelMenulist" in props0 and props0[u"pixelMenulist"] != "":
					position = props0[u"pixelMenulist"]
					if position.find(u"*") >-1:
						position='["*","*"]'
				else:
					try:
						position = u"["
						for ii in range(100):
							mmm = "pixelMenu{}".format(ii)
							if	mmm not in props0 or props0[mmm] ==u"":		continue
							if len(props0[mmm].split(u",")) !=2:			continue
							position += u"[{}],".format(props0[mmm])
						position  = position.strip(u",") +u"]"
						position = json.loads(position)
					except Exception, e:
						self.indiLOG.log(40,"Line {} has error={}".format(sys.exc_traceback.tb_lineno, e))
						self.indiLOG.log(40,"position data: ".format(position))
						position=[]
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
					except Exception, e:
						self.indiLOG.log(40,"Line {} has error={}".format(sys.exc_traceback.tb_lineno, e))
				if self.decideMyLog(u"OutputDevice"): self.indiLOG.log(10, "props0 {}".format(props0) )

				valuesDict[u"outputDev"]		 = devId
				valuesDict[u"type0"]			 = "points"
				valuesDict[u"position0"]		 = json.dumps(ppp)
				valuesDict[u"display0"]			 = "immediate"
				valuesDict[u"reset0"]			 = ""
				valuesDict[u"restoreAfterBoot"]	 = True

				if self.decideMyLog(u"OutputDevice"): self.indiLOG.log(10, "valuesDict {}".format(valuesDict) )

				self.setneopixelCALLBACKmenu(valuesDict)

				return


			#####  GPIO		 
			else:
				dev= dev0
			props = dev.pluginProps

			if self.decideMyLog(u"OutputDevice"): self.indiLOG.log(10, "deviceAction \n{}\n props {}".format(action, props))
			valuesDict={}
			valuesDict[u"outputDev"]=dev.id
			valuesDict[u"piServerNumber"] = props[u"piServerNumber"]
			valuesDict[u"deviceDefs"]	  = props[u"deviceDefs"]
			if dev.deviceTypeId ==u"OUTPUTgpio-1-ONoff":
				valuesDict[u"typeId"]	  = "OUTPUTgpio-1-ONoff"
				typeId					  = "OUTPUTgpio-1-ONoff"
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
					self.indiLOG.log(20, "deviceAction error, gpio not defined action={}\n props {}".format(action.replace(u"\n",""), props) )
			elif "gpio" in props:
				valuesDict[u"GPIOpin"] = props[u"gpio"]
			else:
				self.indiLOG.log(20, "deviceAction error, gpio not defined action={}\n props {}".format(action.replace(u"\n",""), props) )
			   


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
		except Exception, e:
			self.indiLOG.log(40,"Line {} has error={}".format(sys.exc_traceback.tb_lineno, e))


####-------------------------------------------------------------------------####
	def actionControlGeneral(self, action, dev):
		###### STATUS REQUEST ######
		if action.deviceAction == indigo.kDeviceGeneralAction.RequestStatus:
			self.indiLOG.log(20,u"sent \"{}\"  status request".format(dev.name.encode("utf8")) )

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
	def filerINPUTpulseDevices(self, valuesDict=None, filter="", typeId="", devId=""):
			xList = [(-1,"do not use")]
			for dev in indigo.devices.iter("props.isSensorDevice"):
				if dev.deviceTypeId==  "INPUTpulse": 
					xList.append((dev.id, "{}".format(dev.name.encode("utf8"))))
			return xList


####-------------------------------------------------------------------------####
	def filterINPUTdevices(self, valuesDict=None, filter="", typeId="", devId=""):
			xList = []
			for dev in indigo.devices.iter("props.isSensorDevice"):
				if dev.deviceTypeId.find(u"INPUTgpio") == -1 and dev.deviceTypeId.find(u"INPUTtouch") == -1 and dev.deviceTypeId.find(u"INPUTpulse") == -1 and dev.deviceTypeId.find(u"INPUTcoincidence") == -1: continue
				xList.append((dev.id, "{}".format(dev.name.encode("utf8"))))
			return xList




####-------------------------------------------------------------------------####
	def filterOUTPUTdevicesACTION(self, valuesDict=None, filter="", typeId="",devId=""):
		xList = []
		for dev in indigo.devices.iter("props.isOutputDevice"):
			if dev.deviceTypeId.find(u"OUTPUTgpio") ==-1: continue
			xList.append((dev.id,"{}".format(dev.name.encode("utf8"))))
		return xList
####-------------------------------------------------------------------------####
	def filterOUTPUTrelaydevicesACTION(self, valuesDict=None, filter="", typeId="",devId=""):
		xList = []
		for dev in indigo.devices.iter("props.isOutputDevice"):
			if dev.deviceTypeId.find(u"OUTPUTi2cRelay") ==-1: continue
			xList.append((dev.id,"{}".format(dev.name.encode("utf8"))))
		return xList

####-------------------------------------------------------------------------####
	def filterOUTPUTchannelsACTION(self, valuesDict=None, filter="", typeId="", devId=""):
		okList = []
		#self.indiLOG.log(20,	u"self.outdeviceForOUTPUTgpio " + unicode(self.outdeviceForOUTPUTgpio))
		if self.outdeviceForOUTPUTgpio ==u"": return []
		try:	dev = indigo.devices[int(self.outdeviceForOUTPUTgpio)]
		except: return []
		try:
			props= dev.pluginProps
			gpioList= json.loads(props[u"deviceDefs"])
			xList = copy.deepcopy(_GlobalConst_allGPIOlist)
			#self.indiLOG.log(20,	u"gpioList " + unicode(props))
			for ll in xList:
				if ll[0] ==u"0": continue
				#self.indiLOG.log(20,	u"ll "+ unicode(ll))
				for ii in range(len(gpioList)):
					if u"gpio" not in  gpioList[ii]: continue
					if gpioList[ii][u"gpio"] != ll[0]: continue
					okList.append((ll[0],"OUTPUT_"+unicode(ii)+" "+ll[1]))
					break
			#self.indiLOG.log(20, unicode(okList))
		except Exception, e:
			self.indiLOG.log(40,"Line {} has error={}".format(sys.exc_traceback.tb_lineno, e))
		return okList


####-------------------------------------------------------------------------####
	def filterTimezones(self, valuesDict=None, filter="", typeId="", devId=""):

		timeZones =[]
		xxx=[]
		for ii in range(-12,13):
			if ii<0:
				timeZones.append(u"/Etc/GMT+" +unicode(abs(ii)))
			else:
				timeZones.append(u"/Etc/GMT-"+unicode(ii))
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
				xxx.append((unicode(ii-12)+" "+timeZones[ii], u"+"+unicode(abs(ii-12))+" "+timeZones[ii]))
			else:
				xxx.append((unicode(ii-12)+" "+timeZones[ii], (unicode(ii-12))+" "+timeZones[ii]))
		xxx.append(("99 -", "do not set"))
		return xxx

####-------------------------------------------------------------------------####
	def setPinCALLBACKmenu(self, valuesDict=None, typeId=""):
		#self.indiLOG.log(20,	unicode(valuesDict))

		try:
			devId = int(valuesDict[u"outputDev"])
			dev = indigo.devices[devId]
			props = dev.pluginProps
			valuesDict[u"piServerNumber"] = props[u"piServerNumber"]
			if u"deviceDefs" not in props:
				self.indiLOG.log(20, u"deviceDefs not in valuesDict, need to define OUTPUT device properly " )
				return valuesDict
			valuesDict[u"deviceDefs"] = props[u"deviceDefs"]
		except:
			self.indiLOG.log(20, u"device not properly defined, please define OUTPUT ")
			return valuesDict

		#self.outdeviceForOUTPUTgpio = ""
		dev = indigo.devices[devId]
		props = dev.pluginProps
		valuesDict[u"typeId"]	  = dev.deviceTypeId
		valuesDict[u"devId"]	  = devId
		if "i2cAddress" in props:
			valuesDict[u"i2cAddress"]	  = props[u"i2cAddress"]
		if self.decideMyLog(u"OutputDevice"): self.indiLOG.log(10, "setPinCALLBACKmenu  valuesDict\n{}".format(valuesDict))
		self.setPin(valuesDict)


####-------------------------------------------------------------------------####
	def setDelay(self, startAtDateTimeIN=""):
		startAtDateTimeIN = unicode(startAtDateTimeIN)
		if self.decideMyLog(u"OutputDevice"): self.indiLOG.log(10, "startAtDateTimeIN: "+ startAtDateTimeIN)
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
					if self.decideMyLog(u"OutputDevice"): self.indiLOG.log(10, "startAtDateTimeIN: doing datetime")
					startAtDateTime	   = startAtDateTimeIN.replace(u"-","").replace(u":","").replace(u" ","").replace(u"/","").replace(u".","").replace(u",","")
					startAtDateTime	   = startAtDateTime.ljust(14,"0")
					return	 max(0, self.getTimetimeFromDateString(startAtDateTime, fmrt= u"%Y%m%d%H%M%S") - time.time() )
				except Exception, e:
					self.indiLOG.log(40,"Line {} has error={}".format(sys.exc_traceback.tb_lineno, e))
					return 0
		except Exception, e:
			self.indiLOG.log(40, u"Line {} has error={}".format(sys.exc_traceback.tb_lineno, e))
		return 0



####-------------------------------------------------------------------------####
	def setPin(self, valuesDict=None):
		#self.indiLOG.log(20,	unicode(valuesDict))

		#self.outdeviceForOUTPUTgpio =""
		try:
			if u"piServerNumber" not in valuesDict:
				self.indiLOG.log(20, u"setPIN missing parameter: piServerNumber not defined")
				return
			piU = valuesDict[u"piServerNumber"]
			pi = int(piU)
			if piU not in _rpiList:
				self.indiLOG.log(20, u"setPIN bad parameter: piServerNumber out of range: " + piU)
				return

			if self.RPI[piU][u"piOnOff"] != "1":
				self.indiLOG.log(20, u"setPIN bad parameter: piServer is not enabled: " + piU)
				return

			try:
				if not indigo.devices[int(self.RPI[piU][u"piDevId"])].enabled:
					return 
			except:
				return

			ip = self.RPI[piU][u"ipNumberPi"]
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


			inverseGPIO = False

			if typeId == "myoutput":
				if u"text" not in valuesDict:
					self.indiLOG.log(20, u"setPIN bad parameter: text not supplied: for pi#" + piU)
					return

				if self.decideMyLog(u"OutputDevice"): self.indiLOG.log(10,	u"sending command to rPi at " + ip + "; port: " + unicode(self.rPiCommandPORT) + "; cmd: myoutput;    "+ valuesDict[u"text"]		)
				self.sendGPIOCommand(ip, pi, typeId, u"myoutput",  text=valuesDict[u"text"])
				return


			if typeId == "playSound":
					if u"soundFile" not in valuesDict:
						self.indiLOG.log(20, u"setPIN bad parameter: soundFile not supplied: for pi#" + piU)
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
						if self.decideMyLog(u"OutputDevice"): self.indiLOG.log(10, "\n"+line+"\n")
					except:
						if self.decideMyLog(u"OutputDevice"): self.indiLOG.log(10,	u"sending command to rPi at " + ip + "; port: " + unicode(self.rPiCommandPORT) + "; cmd: " + valuesDict[u"cmd"] + ";  " + valuesDict[u"soundFile"])
					self.sendGPIOCommand(ip, pi,typeId, valuesDict[u"cmd"], soundFile=valuesDict[u"soundFile"])
					return

			if u"cmd" not in valuesDict:
				self.indiLOG.log(20, u" setPIN bad parameter: cmd not set:")
				return
			cmd = valuesDict[u"cmd"]

			if cmd not in _GlobalConst_allowedCommands:
				self.indiLOG.log(20, u" setPIN bad parameter: cmd bad:{}; allowed commands= {}" + format(cmd, _GlobalConst_allowedCommands))
				return

			if cmd == "getBeaconParameters":
				#self.indiLOG.log(10, u"sending command to rPi at {}; port: {}; cmd:{} ;  devices".format(pi, self.rPiCommandPORT, valuesDict[u"cmd"], valuesDict[u"typeId"]) )
				self.sendGPIOCommand(ip, pi, valuesDict[u"typeId"], valuesDict[u"cmd"])
				return

			if cmd == "newMessage":
				if u"typeId" not in valuesDict:
					self.indiLOG.log(20, u"setPIN bad parameter: typeId not supplied: for pi#{}".format(piU))
					return

				if self.decideMyLog(u"OutputDevice"): self.indiLOG.log(10, u"sending command to rPi at {}; port: {}; cmd:{} ;  typeId:{}".format(piU, self.rPiCommandPORT, valuesDict[u"cmd"], valuesDict[u"typeId"]) )
				self.sendGPIOCommand(ip, pi, typeId, valuesDict[u"cmd"])
				return


			if cmd == "resetDevice":
				if u"typeId" not in valuesDict:
					self.indiLOG.log(20, u"setPIN bad parameter: typeId not supplied: for pi#{}".format(piU))
					return

				if self.decideMyLog(u"OutputDevice"): sself.indiLOG.log(10, u"sending command to rPi at {}; port: {}; cmd:{} ;  typeId:{}".format(piU, self.rPiCommandPORT, valuesDict[u"cmd"], valuesDict[u"typeId"]) )
				self.sendGPIOCommand(ip, pi, typeId, valuesDict[u"cmd"])
				return

			if cmd == "startCalibration":
				if u"typeId" not in valuesDict:
					self.indiLOG.log(20, u"setPIN bad parameter: typeId not supplied: for pi#{}".format(piU))
					return

				if True:  self.indiLOG.log(20, u"sending command to rPi at {}; port: {}; cmd:{} ;  typeId:{}".format(piU, self.rPiCommandPORT, valuesDict[u"cmd"], valuesDict[u"typeId"]) )
				self.sendGPIOCommand(ip, pi, typeId, valuesDict[u"cmd"])
				return


			try:
				devIds = unicode(valuesDict[u"devId"])
				devId = int(devIds)
				dev = indigo.devices[devId]
				props=dev.pluginProps
			except:
				self.indiLOG.log(20, u" setPIN bad parameter: OUTPUT device not created: for pi#{}".format(piU))
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
					out += cmd + "," + unicode(analogValue)
					out += cmd + "," + unicode(rampTime)
					if "writeOutputToState" not in props or ("writeOutputToState" in props and props["writeOutputToState"] == "1"): self.addToStatesUpdateDict(dev.id, "OUTPUT", out)
				except Exception, e:
					self.indiLOG.log(40,"Line {} has error={}".format(sys.exc_traceback.tb_lineno, e))
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
					line += "##=======	end	   =====\n"
					if self.decideMyLog(u"OutputDevice"): self.indiLOG.log(10, "\n"+line+"\n")
				except:
					if self.decideMyLog(u"OutputDevice"): self.indiLOG.log(10, u"sending command to rPi at " + ip + "; port: " + unicode(self.rPiCommandPORT) +
							   u"; cmd: " + unicode(cmd) + ";  pulseUp: " + unicode(pulseUp) + ";  pulseDown: " +
							   unicode(pulseDown) + ";  nPulses: " + unicode(nPulses) + ";  analogValue: " + unicode(analogValue)+ ";  rampTime: " + unicode(rampTime)+ 
							   u";  restoreAfterBoot: " + unicode(restoreAfterBoot)+ ";   startAtDateTime: " + startAtDateTime)

				self.sendGPIOCommand(ip, pi, typeId, cmd, i2cAddress=i2cAddress,pulseUp=pulseUp, pulseDown=pulseDown, nPulses=nPulses, analogValue=analogValue,rampTime=rampTime, restoreAfterBoot=restoreAfterBoot , startAtDateTime=startAtDateTime, inverseGPIO =inverseGPIO, devId=devId )
				self.executeUpdateStatesDict(onlyDevID=dev.id, calledFrom="setPin")
				return

			if typeId.find(u"OUTPUTgpio") > -1 or typeId.find(u"OUTPUTi2cRelay") > -1:
				i2cAddress = ""
				if u"i2cAddress" in valuesDict:
					i2cAddress = valuesDict[u"i2cAddress"]
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
							self.indiLOG.log(20, u" setPIN bad parameter: no GPIOpin defined:" + unicode(valuesDict))
							return
					else:
						self.indiLOG.log(20, u" setPIN bad parameter: no GPIOpin defined:" + unicode(valuesDict))
						return
				else:
					self.indiLOG.log(20, u" setPIN bad parameter: no GPIOpin defined:" + unicode(valuesDict))
					return

				if u"inverseGPIO" in valuesDict:  # overwrite individual defs  if explicitely inverse defined 
					try: 											inverseGPIO = (valuesDict[u"inverseGPIO"])
					except:											inverseGPIO = False
				else:
					if deviceDefs[int(output)][u"outType"] == "0":	inverseGPIO = False
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
						self.addToStatesUpdateDict(dev.id,"brightnessLevel", b)
						if b >1: 
							self.addToStatesUpdateDict(dev.id,"onOffState", True)
						else:
							self.addToStatesUpdateDict(dev.id,"onOffState", False)
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
							self.addToStatesUpdateDict(dev.id,"onOffState", True)
						else:
							self.addToStatesUpdateDict(dev.id,"onOffState", False)
				if typeId == "OUTPUTi2cRelay":
					b = ""
					if cmd == "up":
						b = 100
					elif cmd == "down":
						b = 0
					if b != "" and "onOffState" in dev.states:
						if b >1:
							self.addToStatesUpdateDict(dev.id,"onOffState", True)
						else:
							self.addToStatesUpdateDict(dev.id,"onOffState", False)


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
						out = cmd + "," + unicode(pulseUp) + "," + unicode(pulseUp) + "," + unicode(nPulses)
					elif cmd == "rampUp" or cmd == "rampDown" or cmd == "rampUpDown":
						out = cmd + "," + unicode(pulseUp) + "," + unicode(pulseUp) + "," + unicode(nPulses)+ "," + unicode(rampTime)
					elif cmd == "analogWrite":
						out = cmd + "," + unicode(analogValue)
					outN = int(output)
					if "OUTPUT_%0.2d"%outN in dev.states: self.addToStatesUpdateDict(dev.id,"OUTPUT_%0.2d"%outN, out)
					if "OUTPUT" in dev.states and ( "writeOutputToState" not in props or ("writeOutputToState" in props and props["writeOutputToState"] == "1") ): self.addToStatesUpdateDict(dev.id,"OUTPUT", out)
				except Exception, e:
					self.indiLOG.log(40,"Line {} has error={}".format(sys.exc_traceback.tb_lineno, e))
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
					line +="\n	,\"i2cAddress\":\""+unicode(i2cAddress)+"\""
					line +="\n	,\"GPIOpin\":\""+unicode(GPIOpin)+"\"})\n"
					line+= "##=======  end  =====\n"
					if self.decideMyLog(u"OutputDevice"): self.indiLOG.log(10, "\n"+line+"\n")
				except:
					if self.decideMyLog(u"OutputDevice"): self.indiLOG.log(10, u"sending command to rPi at " + ip + "; port: " + unicode(self.rPiCommandPORT) + " pin: " +
							   unicode(GPIOpin) + "; GPIOpin: " + unicode(GPIOpin) + "OUTPUT#" + unicode(outN) + "i2cAddress" + unicode(i2cAddress) + "; cmd: " +
							   unicode(cmd) + ";  pulseUp: " + unicode(pulseUp) + ";  pulseDown: " +
							   unicode(pulseDown) + "; nPulses: " + unicode(nPulses) + "; analogValue: " + unicode(analogValue)+ "; rampTime: " + unicode(rampTime)+ ";  restoreAfterBoot: " + unicode(restoreAfterBoot)+ "; startAtDateTime: " + startAtDateTime)

				self.sendGPIOCommand(ip, pi, typeId, cmd, GPIOpin=GPIOpin, i2cAddress=i2cAddress, pulseUp=pulseUp, pulseDown=pulseDown, nPulses=nPulses, analogValue=analogValue, rampTime=rampTime, restoreAfterBoot=restoreAfterBoot , startAtDateTime=startAtDateTime, inverseGPIO =inverseGPIO, devId=devId )
				self.executeUpdateStatesDict(onlyDevID= devIds, calledFrom="setPin END")
				return

			self.indiLOG.log(20, u"setPIN:   no condition met, returning")

		except Exception, e:
			self.indiLOG.log(40,"Line {} has error={}".format(sys.exc_traceback.tb_lineno, e))

####-------------------------------------------------------------------------####
	def buttonConfirmoldIPCALLBACK(self, valuesDict=None, typeId="", devId=0):
		piU = valuesDict[u"PINumberForIPChange"]
		valuesDict[u"oldipNumberPi"] = self.RPI[piU][u"ipNumberPi"]
		valuesDict[u"newipNumberPi"] = self.RPI[piU][u"ipNumberPi"]
		return valuesDict


####-------------------------------------------------------------------------####
	def buttonConfirmIPnumberCALLBACK(self, valuesDict=None, typeId="", devId=0):
		piU = valuesDict[u"PINumberForIPChange"]
		pi = int(piU)
		if valuesDict[u"oldipNumberPi"] != valuesDict[u"newipNumberPi"]:
			self.RPI[piU][u"ipNumberPiSendTo"] = valuesDict[u"oldipNumberPi"]
			self.RPI[piU][u"ipNumberPi"] = valuesDict[u"newipNumberPi"]
			self.setONErPiV(piU,"piUpToDate",[u"updateParamsFTP","rebootSSH"])
			self.rPiRestartCommand[pi]		= "rebootSSH"  ## which part need to restart on rpi
			self.RPI[piU][u"ipNumberPiSendTo"] = self.RPI[piU][u"ipNumberPi"]
		return valuesDict


	###########################		MENU   END #################################




	###########################		ACTION	#################################

####-------------------------------------------------------------------------####
	def sendConfigviaSocketCALLBACKaction(self, action1=None, typeId="", devId=0):
		try:
			v = action1.props
			if v[u"configurePi"] ==u"": return
			piU= unicode(v[u"configurePi"])
			ip= self.RPI[piU][u"ipNumberPi"]
			if len(ip.split(u".")) != 4:
				self.indiLOG.log(20, u"sendingFile to rPI,  bad parameters:"+piU+"  "+ip+"  "+ unicode(v))
				return
			try:
				if not	indigo.devices[int(self.RPI[piS][u"piDevId"])].enabled: return
			except:
				return

			fileContents = self.makeParametersFile(piS,retFile=True)
			if len(fileContents) >0:
				if self.decideMyLog(u"OutputDevice"): self.indiLOG.log(10,	u"sending parameters file via socket: "+unicode(v)+" \n"+fileContents)
				self.sendFileToRPIviaSocket(ip,piU,"/home/pi/pibeacon/parameters",fileContents,fileMode="w")

		except Exception, e:
			self.indiLOG.log(40,"Line {} has error={}".format(sys.exc_traceback.tb_lineno, e))
		return


####-------------------------------------------------------------------------####
	def sendExtraPagesToRpiViaSocketCALLBACKaction(self, action1=None, typeId="", devId=0):
		try:
			v = action1.props
			if v[u"configurePi"] ==u"": return
			piU= unicode(v[u"configurePi"])
			ip= self.RPI[piU][u"ipNumberPi"]
			if len(ip.split(u".")) != 4:
				self.indiLOG.log(20, u"sendingFile to rPI,  bad parameters:"+piU+"  "+ip+"  "+ unicode(v))
				return
			try:
				if not	indigo.devices[int(self.RPI[piU][u"piDevId"])].enabled: return
			except:
				return

			#if self.decideMyLog(u"OutputDevice"): self.indiLOG.log(10, u"sending extrapage file via socket: "+unicode(v))
			fileContents =[]
			#self.indiLOG.log(20, unicode(propsOut))
			for ii in range(10):
				if u"extraPage"+unicode(ii)+"Line0" in v and "extraPage"+unicode(ii)+"Line1" in v and "extraPage"+unicode(ii)+"Color" in v:
					line0 = self.convertVariableOrDeviceStateToText(v[u"extraPage"+unicode(ii)+"Line0"])
					line1 = self.convertVariableOrDeviceStateToText(v[u"extraPage"+unicode(ii)+"Line1"])
					color = self.convertVariableOrDeviceStateToText(v[u"extraPage"+unicode(ii)+"Color"])
					fileContents.append([line0,line1,color])
			if len(fileContents) >0:
				self.sendFileToRPIviaSocket(ip, piU, "/home/pi/pibeacon/temp/extraPageForDisplay.inp",json.dumps(fileContents),fileMode="w",touchFile=False)

		except Exception, e:
			self.indiLOG.log(40,"Line {} has error={}".format(sys.exc_traceback.tb_lineno, e))
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
					self.indiLOG.log(20, u"device not in valuesDict, need to define parameters properly ")
					return

			props = dev.pluginProps
			if u"deviceDefs" not in props:
				self.indiLOG.log(20, u"deviceDefs not in valuesDict, need to define OUTPUT device properly ")
				return
			valuesDict[u"deviceDefs"] = props[u"deviceDefs"]
			valuesDict[u"piServerNumber"] = props[u"piServerNumber"]
			if "i2cAddress" in props:
				valuesDict[u"i2cAddress"] = props[u"i2cAddress"]


		except:
			self.indiLOG.log(20, u"setPinCALLBACKaction device not properly defined, please define OUTPUT ")
			return valuesDict
		valuesDict[u"typeId"]	  = dev.deviceTypeId
		valuesDict[u"devId"] = devId
		#self.indiLOG.log(20,	u"valuesDict "+unicode(valuesDict))
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
				self.indiLOG.log(20, u"setMCP4725CALLBACKaction action put wrong, device name/id	not installed/ configured:" + unicode(valuesDict))
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
				self.indiLOG.log(20, u"setPCF8591dacCALLBACKaction action put wrong, device name/id  not installed/ configured:" + unicode(valuesDict))
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
	def startCalibrationCALLBACKaction(self, action1):
		valuesDict = action1.props
		valuesDict[u"cmd"] = "startCalibration"
		self.setPin(valuesDict)

####-------------------------------------------------------------------------####
	def setnewMessageCALLBACKaction(self, action1):
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
			piU = valuesDict[u"piServerNumber"]
			pi = int(piU)
		except:
			return valuesDict
		self.selectedPiServer		  = pi
		if piU in  _rpiBeaconList:
			valuesDict[u"beaconOrSensor"] = "iBeacon and Sensor rPi"
		else:
			valuesDict[u"beaconOrSensor"] = "Sensor only rPi"
		usePassword = self.RPI[piU][u"passwordPi"]
		if	self.RPI[piU][u"passwordPi"] == "raspberry":
			for piU0 in self.RPI:
				if self.RPI[piU0][u"passwordPi"] !="raspberry":
					usePassword = self.RPI[piU0][u"passwordPi"]
					break
		valuesDict[u"passwordPi"]		 = usePassword

		useID = self.RPI[piU][u"userIdPi"]
		if	self.RPI[piU][u"userIdPi"] == "pi":
			for piU0 in self.RPI:
				if self.RPI[piU0][u"userIdPi"] !="pi" and len(self.RPI[piU0][u"userIdPi"]) > 1:
					useID = self.RPI[piU0][u"userIdPi"]
					break
		valuesDict[u"userIdPi"]			 = useID

		useIP = self.RPI[piU][u"ipNumberPi"]
		if self.RPI[piU][u"ipNumberPi"] == "":
			for piU0 in self.RPI:
				if self.RPI[piU0][u"ipNumberPi"] !="":
					useIP = self.RPI[piU0][u"ipNumberPi"]+"x"
					break
		valuesDict[u"ipNumberPi"]		 = useIP

		valuesDict[u"enablePiEntries"]	 = True
		valuesDict[u"piOnOff"]			 = self.RPI[piU][u"piOnOff"]
		valuesDict[u"enableRebootCheck"] = self.RPI[piU][u"enableRebootCheck"]
		valuesDict[u"MSG"]				 = "enter configuration"
		return valuesDict

####-------------------------------------------------------------------------####
	def buttonConfirmPiServerConfigCALLBACK(self, valuesDict=None, typeId="", devId=0):
		try:
			piU = valuesDict[u"piServerNumber"]
			pi = int(piU)
		#### check pi on/off
			p01 = valuesDict[u"piOnOff"]

			if p01 =="delete":
				self.delRPI(pi=pi, calledFrom="buttonConfirmPiServerConfigCALLBACK" )
				return valuesDict

			if p01 == u"0":  # off 
				self.RPI[piU][u"piOnOff"] = "0"
				self.resetUpdateQueue(piU)
				valuesDict[u"MSG"] = "Pi server disabled"
				try:
					dev= indigo.devices[self.RPI[piU][u"piDevId"]]
					dev.enabled = False
					dev.replaceOnServer()
					self.stopOneUpdateRPIqueues(piU, reason=" set RPI off")
				except:
					pass
				return valuesDict
				
########## from here on it is ON 
			dateString	= datetime.datetime.now().strftime(_defaultDateStampFormat)

		####### check ipnumber
			ipn = valuesDict[u"ipNumberPi"]
			if not self.isValidIP(ipn):
				valuesDict[u"MSG"] = "ip number not correct"
				return valuesDict



			# first test if already used somewhere else
			for piU3 in self.RPI:
				if piU == piU3: continue
				if self.RPI[piU3][u"piOnOff"] == "0": continue
				if self.RPI[piU3][u"ipNumberPi"] == ipn:
						valuesDict[u"MSG"] = "ip number already in use"
						return valuesDict

			if self.RPI[piU][u"ipNumberPi"]	  != ipn:
				self.RPI[piU][u"ipNumberPi"]   = ipn
				self.setONErPiV(piU,"piUpToDate", [u"updateParamsFTP"])
			self.RPI[piU][u"ipNumberPiSendTo"] = ipn

			#### check authkey vs std password ..
			self.RPI[piU][u"authKeyOrPassword"] = valuesDict[u"authKeyOrPassword"]


			#### check userid password ..
			if self.RPI[piU][u"userIdPi"]	  != valuesDict[u"userIdPi"]:
				self.RPI[piU][u"userIdPi"]	   = valuesDict[u"userIdPi"]
				self.setONErPiV(piU,"piUpToDate", [u"updateParamsFTP"])

			if self.RPI[piU][u"passwordPi"]	  != valuesDict[u"passwordPi"]:
				self.RPI[piU][u"passwordPi"]   = valuesDict[u"passwordPi"]
				self.setONErPiV(piU,"piUpToDate", [u"updateParamsFTP"])

			if self.RPI[piU][u"enableRebootCheck"] != valuesDict[u"enableRebootCheck"]:
				self.RPI[piU][u"enableRebootCheck"] = valuesDict[u"enableRebootCheck"]
				self.setONErPiV(piU,"piUpToDate", [u"updateParamsFTP"])


			valuesDict[u"MSG"] = "Pi server configuration set"

			valuesDict[u"enablePiEntries"] = False
			if self.decideMyLog(u"UpdateRPI"): self.indiLOG.log(10, u"buttonConfirmPiServerConfigCALLBACK... pi#=        {}".format(piU))
			if self.decideMyLog(u"UpdateRPI"): self.indiLOG.log(10, u"valuesDict= {}".format(valuesDict))
			if self.decideMyLog(u"UpdateRPI"): self.indiLOG.log(10, u"RPI=        {}".format(self.RPI[piU]))

			if piU in  _rpiBeaconList:
						if self.RPI[piU][u"piDevId"] == 0: # check if  existing device
							found =False
							for dev in indigo.devices.iter("props.isRPIDevice"):
								try: 
									if dev.description.split(u"-")[1] == piU:
										props=dev.pluginProps
										if props[u"ipNumberPi"] != ipn:
											props[u"ipNumberPi"] = ipn
											self.deviceStopCommIgnore = time.time()
											dev.replacePluginPropsOnServer(props)
											self.updateNeeded += "fixConfig"
											self.setONErPiV(piU,"piUpToDate", [u"updateParamsFTP"])

										self.RPI[piU][u"piDevId"] = dev.id
										found = True
										break
								except:
									pass
							if not found:
									#self.indiLOG.log(30,"making new RPI: {};   ip: {}".format(pi, ipn))
									indigo.device.create(
										protocol		= indigo.kProtocol.Plugin,
										address			= "00:00:00:00:pi:{:02d}".format(pi),
										name			= "Pi_{}".format(pi),
										description		= "Pi-{}-{}".format(pi,ipn),
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
										dev = indigo.devices[u"Pi_" +piU]
									except Exception, e:
										if unicode(e).find(u"timeout waiting") > -1:
											self.indiLOG.log(40,"Line {} has error={}".format(sys.exc_traceback.tb_lineno, e))
											self.indiLOG.log(40, u"communication to indigo is interrupted")
											return valuesDict
										if unicode(e).find(u"not found in database") ==-1:
											self.indiLOG.log(40,"Line {} has error={}".format(sys.exc_traceback.tb_lineno, e))
											return valuesDict
										self.indiLOG.log(40,"Line {} has error={}".format(sys.exc_traceback.tb_lineno, e))

									dev.updateStateImageOnServer(indigo.kStateImageSel.SensorOn)
									self.addToStatesUpdateDict(dev.id,u"status", u"expired")
									self.addToStatesUpdateDict(dev.id,u"note", u"Pi-" + piU)
									self.addToStatesUpdateDict(dev.id,u"created",dateString)
									self.executeUpdateStatesDict(onlyDevID=dev.id,calledFrom="updateBeaconStates new rpi")
									self.RPI[piU][u"piMAC"] = "00:00:00:00:pi:{:02d}".format(pi)
									self.RPI[piU][u"piDevId"] = dev.id

						else:
							try:
								dev= indigo.devices[self.RPI[piU][u"piDevId"]]
							except Exception, e: 
								if unicode(e).find(u"not found in database") >-1:
									dev = indigo.device.create(
										protocol		= indigo.kProtocol.Plugin,
										address			= "Pi-{:02d}".format(pi),
										name			= "Pi_{}".format(pi),
										description		= "Pi-{:02d}-{}".format(pi,ipn),
										pluginId		= self.pluginId,
										deviceTypeId	= "rPI",
										folder			= self.piFolderId,
										props		= {
											u"updateSignalValuesSeconds": _GlobalConst_emptyrPiProps[u"updateSignalValuesSeconds"],
											u"beaconTxPower":			  _GlobalConst_emptyrPiProps[u"beaconTxPower"],
											u"SupportsBatteryLevel":	  _GlobalConst_emptyrPiProps[u"SupportsBatteryLevel"],
											u"sendToIndigoSecs":		  _GlobalConst_emptyrPiProps[u"sendToIndigoSecs"],
											u"shutDownPinInput":		  _GlobalConst_emptyrPiProps[u"shutDownPinInput"],
											u"shutDownPinOutput" :		  _GlobalConst_emptyrPiProps[u"shutDownPinOutput"],
											u"signalDelta" :			  _GlobalConst_emptyrPiProps[u"signalDelta"],
											u"minSignalCutoff" :		  _GlobalConst_emptyrPiProps[u"minSignalCutoff"],
											u"expirationTime" :			  _GlobalConst_emptyrPiProps[u"expirationTime"],
											u"isRPIDevice":				  True,
											u"rssiOffset":				  _GlobalConst_emptyrPiProps[u"rssiOffset"]
											}
										)
									self.RPI[piU][u"piMAC"] = "00:00:00:00:pi:{:02d}".format(pi)
									self.RPI[piU][u"piDevId"] = dev.id
						props= dev.pluginProps
						self.addToStatesUpdateDict(dev.id,u"note", u"Pi-{}".format(pi))
						props[u"description"] 				= "Pi-{}-{}".format(pi,ipn)
						self.deviceStopCommIgnore 			= time.time()
						dev.replacePluginPropsOnServer(props)
						self.RPI[piU][u"piOnOff"] 	= "1"
						dev.enabled = (p01 == "1")

###### 
			if piU in _rpiSensorList:
						if self.RPI[piU][u"piDevId"] == 0: # check if  existing device
							found =False
							for dev in indigo.devices.iter("props.isRPISensorDevice"):
								if dev.address.split(u"-")[1] == piU:
									props=dev.pluginProps
									if props[u"ipNumberPi"] != ipn:
										props[u"ipNumberPi"] = ipn
										self.deviceStopCommIgnore = time.time()
										dev.replacePluginPropsOnServer(props)
										self.updateNeeded += "fixConfig"
										self.setONErPiV(piU,"piUpToDate", [u"updateParamsFTP"])

									self.RPI[piU][u"piDevId"] = dev.id
									found = True
									break
							if not found:
								dev= indigo.device.create(
									protocol		= indigo.kProtocol.Plugin,
									address			= "Pi-"+piU,
									name			= "Pi_Sensor_" + piU,
									description		= "Pi-" + piU+"-"+ipn,
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
										   u"ipNumberPi":ipn}
									)
								self.addToStatesUpdateDict(dev.id,u"created",datetime.datetime.now().strftime(_defaultDateStampFormat))
								self.addToStatesUpdateDict(dev.id,u"note", u"Pi-" + piU)
								self.RPI[piU][u"piDevId"] = dev.id
								self.updateNeeded += "fixConfig"
								self.setONErPiV(piU,"piUpToDate", [u"updateParamsFTP"])
						else:
							try:
								dev= indigo.devices[self.RPI[piU][u"piDevId"]]
							except Exception, e: 
								if unicode(e).find(u"not found in database") >-1:
									dev= indigo.device.create(
										protocol		= indigo.kProtocol.Plugin,
										address			= "Pi-"+piU,
										name			= "Pi_Sensor_" +piU,
										description		= "Pi-" + piU+"-"+ipn,
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
											   u"ipNumberPi":ipn}
										)
									self.addToStatesUpdateDict(dev.id,"created",dateString)
									self.addToStatesUpdateDict(dev.id,u"note", u"Pi-" + piU)
									self.RPI[piU][u"piDevId"] = dev.id
									self.updateNeeded += "fixConfig"
									self.setONErPiV(piU,"piUpToDate", [u"updateParamsFTP"])
						dev= indigo.devices[self.RPI[piU][u"piDevId"]]
						props= dev.pluginProps
						self.addToStatesUpdateDict(dev.id,u"note", u"Pi-" + piU)
						props[u"description"] 				= "Pi-"+piU+"-"+ipn
						self.RPI[piU][u"piMAC"] 			= piU
						self.deviceStopCommIgnore 			= time.time()
						dev.replacePluginPropsOnServer(props)
						self.RPI[piU][u"piOnOff"] 			= "1"
			try:
				dev= indigo.devices[self.RPI[piU][u"piDevId"]]
				dev.enabled = True
				#try:	del self.checkIPSendSocketOk[self.RPI[piU][u"ipNumberPi"]]
				#except: pass
				self.executeUpdateStatesDict(onlyDevID=dev.id, calledFrom="buttonConfirmPiServerConfigCALLBACK end")
			except:
				pass
			self.RPI[piU][u"piOnOff"] = "1"
			self.startOneUpdateRPIqueue(piU, reason="; from basic setup")

			self.fixConfig(checkOnly = ["all","rpi"],fromPGM="buttonConfirmPiServerConfigCALLBACK")

		except Exception, e:
			self.indiLOG.log(40,"Line {} has error={}".format(sys.exc_traceback.tb_lineno, e))


		self.RPI[piU][u"piOnOff"] = "1"
		self.writeJson(self.RPI, fName=self.indigoPreferencesPluginDir + u"RPIconf", fmtOn=self.RPIFileSort)
		self.startUpdateRPIqueues("restart", piSelect=piU)
		self.setONErPiV(piU,"piUpToDate", [u"updateAllFilesFTP"])


		return valuesDict

####-------------------------------------------------------------------------####
	def delRPI(self, pi="", dev="none", calledFrom=""):
		try:
			devID ="none"
			if dev == "none" and pi == "": return
			if pi !="":
				try: pi = int(pi)
				except: return 
				piU = unicode(pi)
				devID = int(self.RPI[piU]["piDevId"])
				self.indiLOG.log(30,"=== delRPI:  deleting pi:{}  devID:{}, calledFrom: {} ".format(pi, devID, calledFrom) )
				try: indigo.device.delete(devID)
				except: pass
				self.resetRPI(piU)	
				return

			if dev !="none":
				devID = dev.id
				self.indiLOG.log(30,"=== delRPI:  deleting dev:{}, calledFrom: {} ".format(dev.name.encode("utf8"), calledFrom) )
				pp =  dev.description.split("-")
				try: indigo.device.delete(devID)
				except: pass
				if len(pp) >1:
					try: pi = int(pp[1])
					except: return
					self.resetRPI(piU)	
				return

		except Exception, e:
			self.indiLOG.log(40,"Line {} has error={}".format(sys.exc_traceback.tb_lineno, e))
			self.indiLOG.log(40,"trying to delete indigo device for pi# {};  devID:{}; calledFrom:{}".format(pi, devID, calledFrom))
		return 

####-------------------------------------------------------------------------####
	def resetRPI(self, pi):
		piU = unicode(pi)
		if piU not in _rpiList: return 
		if piU in _rpiSensorList:
			self.RPI[piU] = copy.copy(_GlobalConst_emptyRPISENSOR)
		else: 
			self.RPI[piU] = copy.copy(_GlobalConst_emptyRPI)
		self.RPI[piU][u"piOnOff"] = "0" 
		self.writeJson(self.RPI, fName=self.indigoPreferencesPluginDir + u"RPIconf", fmtOn=self.RPIFileSort)
		self.stopOneUpdateRPIqueues(piU, reason="rpi deleted / reset")

####-------------------------------------------------------------------------####

# noinspection SpellCheckingInspection
	def validatePrefsConfigUi(self, valuesDict):

		try:
			try: self.enableFING				= valuesDict[u"enableFING"]
			except: self.enableFING				= "0"
				####-----------------	 ---------

			self.debugLevel			= []
			for d in _debugAreas:
				if valuesDict[u"debug"+d]: self.debugLevel.append(d)
			try:			   
				if self.debugRPI	   != int(valuesDict[u"debugRPI"]):	   self.setALLrPiV(u"piUpToDate", [u"updateParamsFTP"])
				self.debugRPI			= int(valuesDict[u"debugRPI"])
			except: pass

			self.setLogfile(valuesDict[u"logFileActive2"])
	 
			self.enableBroadCastEvents					= valuesDict[u"enableBroadCastEvents"]

			try: 
				xx = valuesDict["SQLLoggingEnable"].split("-")
				yy = {"devices":xx[0]=="on", "variables":xx[1]=="on"}
				if yy != self.SQLLoggingEnable:
					self.SQLLoggingEnable = yy
					self.actionList["setSqlLoggerIgnoreStatesAndVariables"] = True
			except Exception, e:
				self.indiLOG.log(30,"Line {} has error={}".format(sys.exc_traceback.tb_lineno, e))
				self.SQLLoggingEnable = {"devices":True, "variables":True}


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

			self.setClostestRPItextToBlank = valuesDict[u"setClostestRPItextToBlank"] !="1"


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
								self.addToStatesUpdateDict(dev.id,state, x*mult, decimalPlaces=self.rainDigits )
						self.executeUpdateStatesDict(onlyDevID=dev.id,calledFrom="validatePrefsConfigUi")
					   
						for prop in ["hourRainTotal","lasthourRainTotal","dayRainTotal" ,"lastdayRainTotal","weekRainTotal","lastWeekRainTotal","monthRainTotal" ,"lastmonthRainTotal","yearRainTotal"]:
								try:	props[prop] = float(props[prop]) * mult
								except: pass
						self.deviceStopCommIgnore = time.time()
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
				self.automaticRPIReplacement	= unicode(valuesDict[u"automaticRPIReplacement"]).lower() == u"true" 
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
				self.indiLOG.log(20, u"switching communication, will send new config to all RPI and restart plugin")
				self.setALLrPiV(u"piUpToDate", [u"updateParamsFTP"])
			self.indigoInputPORT = xx

			try:
				xx = (valuesDict[u"IndigoOrSocket"])
			except:
				xx = 9999
			if xx != self.IndigoOrSocket:
				self.quitNow = u"restart, commnunication was switched "
				self.indiLOG.log(20, u"switching communication, will send new config to all RPI and restart plugin")
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
				self.varExcludeSQLList = [ "pi_IN_"+str(ii) for ii in _rpiList]
				self.varExcludeSQLList.append(self.ibeaconNameDefault+"With_ClosestRPI_Change")
				self.varExcludeSQLList.append(self.ibeaconNameDefault+"Rebooting")
				self.varExcludeSQLList.append(self.ibeaconNameDefault+"With_Status_Change")
				for group in _GlobalConst_groupList:
					for tType in [u"Home", u"Away"]:
						self.varExcludeSQLList.append(self.groupCountNameDefault+group+"_"+tType)
				self.actionList["setSqlLoggerIgnoreStatesAndVariables"] = True


			self.checkBeaconParametersDisabled	= valuesDict[u"checkBeaconParametersDisabled"]


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
			eth0					= '{"on":"dontChange",	"useIP":"use"}'
			wlan0					= '{"on":"dontChange",	"useIP":"useIf"}'
			try:	mm  			= { "eth0":json.loads(valuesDict[u"eth0"]), "wlan0":json.loads(valuesDict["wlan0"]) }
			except: mm  			= {"eth0":json.loads(eth0),"wlan0":json.loads(wlan0)}

			if ss != self.wifiSSID or pp != self.wifiPassword or kk != self.key_mgmt or mm != self.wifiEth:
				self.wifiSSID		= ss
				self.wifiPassword	= pp
				self.key_mgmt		= kk
				self.wifiEth		= mm
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
		except Exception, e:
			self.indiLOG.log(40,"Line {} has error={}".format(sys.exc_traceback.tb_lineno, e))
		return True, valuesDict

####-------------------------------------------------------------------------####
	def confirmDevicex(self, valuesDict=None, typeId="", devId=0):

		piU = valuesDict[u"piServerNumber"]
		pi  = int(piU)
		if devId == 0:
			self.selectedPiServer = pi
			valuesDict[u"enablePiEntries"]	 = True
			valuesDict[u"ipNumberPi"]		 = self.RPI[piU][u"ipNumberPi"]
			valuesDict[u"userIdPi"]			 = self.RPI[piU][u"userIdPi"]
			valuesDict[u"piOnOff"]			 = self.RPI[piU][u"piOnOff"]
			valuesDict[u"MSG"]				 = u"enter configuration"
			return valuesDict
		return valuesDict


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


		for ii in range(2):
			if self.pluginPrefs.get(u"authentication", u"digest") == "none": break
			if self.userIdOfServer !="" and self.passwordOfServer !="": break
			self.indiLOG.log(30, u"indigo server userid or password not configured in config and security level is set to digest or basic")
			self.sleep(10)



		self.writeJson(self.pluginVersion, fName=self.indigoPreferencesPluginDir + "currentVersion")

		self.initSprinkler()

		if self.indigoInputPORT > 0 and self.IndigoOrSocket == u"socket":
			self.setCurrentlyBooting(50, setBy="initConcurrentThread")
			self.socketServer, self.stackReady	= self.startTcpipListening(self.myIpNumber, self.indigoInputPORT)
			self.setCurrentlyBooting(40, setBy="initConcurrentThread")
		else:
			self.indiLOG.log(20,u" ..  subscribing to indigo variable changes" )
			indigo.variables.subscribeToChanges()
			self.setCurrentlyBooting(40, setBy="initConcurrentThread")
			self.stackReady			= True

		self.lastMinuteChecked	= now.minute
		self.lastHourChecked	= now.hour
		self.lastDayChecked		= [-1 for ii in range(len(self.checkBatteryLevelHours)+2)]
		self.lastSecChecked		= 0
		self.countLoop			= 0
		self.indiLOG.log(10, u" ..   checking sensors" )
		self.syncSensors()

		self.indiLOG.log(10, u" ..   checking BLEconnect" )
		self.BLEconnectCheckPeriod(force=True)
		self.indiLOG.log(10, u" ..   checking beacons" )
		self.BeaconsCheckPeriod(now, force=True)

		self.rPiRestartCommand = [u"master" for ii in range(_GlobalConst_numberOfRPI)]	## which part need to restart on rpi
		self.setupFilesForPi()
		if self.currentVersion != self.pluginVersion :
			self.setCurrentlyBooting(40, setBy="initConcurrentThread")
			self.indiLOG.log(10, u" ..  new py programs  etc will be send to rPis")
			for piU in self.RPI:
				if self.RPI[piU][u"ipNumberPi"] != "":
					self.setONErPiV(piU,"piUpToDate", [u"updateAllFilesFTP","restartmasterSSH"])
			self.indiLOG.log(10, u" ..  new pgm versions send to rPis")
		else:
			for piU in self.RPI:
				if self.RPI[piU][u"ipNumberPi"] != "":
					self.setONErPiV(piU,"piUpToDate", [u"updateParamsFTP"])

		if len(self.checkCarsNeed) > 0:
			for carId in self.checkCarsNeed:
				self.updateAllCARbeacons(carId,force=True)

		self.checkForUpdates(datetime.datetime.now())

		self.lastUpdateSend = time.time()  # used to send updates to all rPis if not done anyway every day
		self.pluginState	= "run"
		self.setCurrentlyBooting(50, setBy="initConcurrentThread")

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
		except Exception, e:
			pass

		self.timeTrackWaitTime = 60
		return "off",""

	####-----------------            ---------
	def printcProfileStats(self,pri=""):
		try:
			if pri !="": pick = pri
			else:		 pick = 'cumtime'
			outFile		= self.indigoPreferencesPluginDir+"timeStats"
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
			self.timeTrVarName 			= "enableTimeTracking_"+self.pluginShortName
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


		self.indiLOG.log(20, u"killing 2")
		subprocess.call("/bin/kill -9 "+unicode(self.myPID), shell=True )

		return



####-----------------   main loop          ---------
	def dorunConcurrentThread(self): 

		self.initConcurrentThread()


		if self.logFileActive !="standard":
			indigo.server.log(u" ..  initialized")
			self.indiLOG.log(10, u" ..  initialized, starting loop" )
		else:	 
			indigo.server.log(u" ..  initialized, starting loop ")
		theHourToCheckversion = 12

		########   ------- here the loop starts	   --------------
		try:
			while self.quitNow == "":
				self.countLoop += 1
				self.sleep(9.)

				if self.countLoop > 2: 
					anyChange= self.periodCheck()
					self.checkGroups()
					if self.enableFING == "1":
						self.updateFING(u"loop ")
					if len(self.sendBroadCastEventsList) >0: self.sendBroadCastNOW()

		except self.StopThread:
			indigo.server.log( u"stop requested from indigo ")
		## stop and processing of messages received 
		if self.quitNow !="": indigo.server.log( "quitNow: "+self.quitNow +"--- you might see an indigo error message, can be ignored ")
		else: indigo.server.log( "quitNow:  empty")

		self.stackReady	 = False 
		self.pluginState = "stop"


		# save all parameters to file 
		self.fixConfig(checkOnly = ["all","rpi","beacon","CARS","sensors","output","force"],fromPGM="finish") # runConcurrentThread end

		self.stopUpdateRPIqueues()
		self.sleep(0.1)
		self.stopUpdateRPIqueues()

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


# noinspection SpellCheckingInspection
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
				except Exception, e:
					if unicode(e).find(u"timeout waiting") > -1:
						self.indiLOG.log(40,"Line {} has error={}".format(sys.exc_traceback.tb_lineno, e))
						self.indiLOG.log(40,u"communication to indigo is interrupted")
						return
					if unicode(e).find(u"not found in database") >-1:	 
						name = ""
					else:
						return

				names.append(name)
				self.beacons[beacon][u"updateFING"] = 0

			if devIDs != []:
				for i in range(3):
					if self.decideMyLog(u"Fing"): self.indiLOG.log(10,	u"updating fingscan ; source:" + source + "     try# " + unicode(i + 1) + u";   with " + unicode(names) + " " + unicode(devIDs) + " " + unicode(states))
					plug = indigo.server.getPlugin(u"com.karlwachs.fingscan")
					if plug.isEnabled():
						plug.executeAction(u"piBeaconUpdate", props={u"deviceId": devIDs})
						self.fingscanTryAgain = False
						break
					else:
						if i == 2:
							self.indiLOG.log(20, u"fingscan plugin not reachable")
							self.fingscanTryAgain = True
						self.sleep(1)
		except Exception, e:
			if len(unicode(e)) > 5 :
				self.indiLOG.log(40,"Line {} has error={}".format(sys.exc_traceback.tb_lineno, e))

		return
	####----------------- if FINGSCAN is enabled send update signal	 ---------
	def sendBroadCastNOW(self):
		try:
			x = False
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
					if self.decideMyLog(u"BC"): self.myLog( text=u"updating BC with " + unicode(msg),mType=u"BroadCast" )
					indigo.server.broadcastToSubscribers(u"deviceStatusChanged", json.dumps(msg))
				except Exception, e:
					if len(unicode(e)) > 5:
						self.indiLOG.log(40, u"updating sendBroadCastNOW has error Line {} has error={};    fingscan update failed".format(sys.exc_traceback.tb_lineno, e))

		except Exception, e:
			if len(unicode(e)) > 5:
				self.indiLOG.log(40,u"updating sendBroadCastNOW has error Line {} has error={}".format(sys.exc_traceback.tb_lineno, e))
			else:
				x = True
		return x


####-------------------------------------------------------------------------####
	def printpiUpToDate(self):
		try:
			xList= ""
			for piU in self.RPI:
				ok = True
				for action	in self.RPI[piU][u"piUpToDate"]:
					if action not in _GlobalConst_allowedpiSends:
						ok = False
						break
				xList += piU+":"+unicode(self.RPI[piU][u"piUpToDate"])+"; "
				if not ok: self.RPI[piU][u"piUpToDate"]=[]
			if self.decideMyLog(u"OfflineRPI"): self.indiLOG.log(10, u"printpiUpToDate list .. pi#:[actionLeft];.. ([]=ok): "+ xList	 ) 
		except Exception, e:
			if len(unicode(e)) > 5 :
				self.indiLOG.log(40,"Line {} has error={}".format(sys.exc_traceback.tb_lineno, e))
		return

####-------------------------------------------------------------------------####
	def findAnyTaskPi(self, item):
		for piU in self.RPI:
			if self.RPI[piU][item] !=[]:
				return True
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

			self.checkcProfile()

			now = datetime.datetime.now()
			self.freezeAddRemove =False

			self.replaceAddress()

			self.checkForUpdates(now )
			if self.sendInitialValue != "": self.sendInitialValuesToOutput()
			self.checkMinute(now )

			self.sprinklerStats()


			if self.queueList !="":
				for ii in range(40):
					if ii > 0 and self.decideMyLog(u"BeaconData"): self.indiLOG.log(10, u"wait for queue to become available in main loop,   ii={}  {}".format(ii, self.queueList))
					if self.queueList ==u"": break
					self.sleep(0.05)

			self.startUpdateRPIqueues("restart")

			self.queueList = u"periodCheck"		 # block incoming messages from processing
			self.BLEconnectCheckPeriod()
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
			self.queueList = ""					# unblock incoming messages from processing


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
		except Exception, e:
			if len(unicode(e)) > 5 :
				self.indiLOG.log(40,"Line {} has error={}".format(sys.exc_traceback.tb_lineno, e))

		return anyChange


####-------------------------------------------------------------------------####
	def performActionList(self):
		try:
			if self.actionList["setTime"] != []: 

				for action in self.actionList["setTime"]:
					if action[u"action"] == "setTime":
						self.doActionSetTime(action[u"value"])

			if self.actionList["setSqlLoggerIgnoreStatesAndVariables"] :
				self.actionList["setSqlLoggerIgnoreStatesAndVariables"] = False
				self.setSqlLoggerIgnoreStatesAndVariables()

		except Exception, e:
			if len(unicode(e)) > 5 :
				self.indiLOG.log(40,"Line {} has error={}".format(sys.exc_traceback.tb_lineno, e))
		self.actionList["setTime"] = []
		return


####-------------------------------------------------------------------------####
	def replaceAddress(self):
		try:
			if self.newADDRESS !={}:
				for devId in self.newADDRESS:
					try:
						dev = indigo.devices[devId]
						if len(self.newADDRESS[devId]) == len(u"01:02:03:04:05:06"):
							self.indiLOG.log(20, u"updating {}  address with: {}".format(dev.name.encode("utf8"), self.newADDRESS[devId]))
							props = dev.pluginProps
							props[u"address"]= self.newADDRESS[devId]
							self.deviceStopCommIgnore = time.time()
							dev.replacePluginPropsOnServer(props)
							dev = indigo.devices[devId]
							props = dev.pluginProps
					except Exception, e:
						if len(unicode(e)) > 5 :
							self.indiLOG.log(40,"Line {} has error={}".format(sys.exc_traceback.tb_lineno, e))
							self.indiLOG.log(40,u"ok if replacing RPI")
				self.newADDRESS={}

		except Exception, e:
			if len(unicode(e)) > 5 :
				self.indiLOG.log(40,"Line {} has error={}".format(sys.exc_traceback.tb_lineno, e))



####-------------------------------------------------------------------------####
	def sendInitialValuesToOutput(self):
		try:
			dev= indigo.devices[self.sendInitialValue]
			props= dev.pluginProps
			deviceDefs = json.loads(props[u"deviceDefs"])
			nn = len(deviceDefs)
			piServerNumber = props[u"piServerNumber"]
			ip = self.RPI[unicode(props[u"piServerNumber"])][u"ipNumberPi"]
			for n in range(nn):
				cmd = deviceDefs[n][u"initialValue"]
				if cmd ==u"up" or  cmd ==u"down": 
					inverseGPIO = (deviceDefs[n][u"outType"] == "1")
					gpio = deviceDefs[n][u"gpio"]
					if self.decideMyLog(u"OutputDevice"): self.indiLOG.log(10, "sendInitialValuesToOutput init pin: sending to pi# {}; pin: {}  {};  deviceDefs: {}".format(piServerNumber, props[u"gpio"], cmd, props[u"deviceDefs"]) )
					self.sendGPIOCommand(ip, int(piServerNumber), dev.deviceTypeId, cmd, GPIOpin=gpio, restoreAfterBoot="1", inverseGPIO =inverseGPIO )

		except Exception, e:
			if len(unicode(e)) > 5 :
				self.indiLOG.log(40,"Line {} has error={}".format(sys.exc_traceback.tb_lineno, e))
		self.sendInitialValue = ""
		return


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

			if (self.updateNeeded.find(u"enable") > -1) or (self.updateNeeded.find(u"disable") > -1): 
				self.fixConfig(checkOnly = ["all","rpi","force"], fromPGM="checkForUpdates") # checkForUpdates  # ok only if changes requested
				#self.syncSensors()
				self.setupFilesForPi(calledFrom="checkForUpdates enable/disable")
				try:
					pi = self.updateNeeded.split(u"-")
					if len(pi) >1:
						self.setONErPiV(pi[1],"piUpToDate", [u"updateParamsFTP"])
						if self.decideMyLog(u"UpdateRPI"): self.indiLOG.log(10, u"sending update to pi#{}".format(pi))
				except Exception, e:
					if len(unicode(e)) > 5 :
						self.indiLOG.log(40,"Line {} has error={}".format(sys.exc_traceback.tb_lineno, e))

				self.updateNeeded = "" 
	 
			if self.updateNeeded.find(u"fixConfig") > -1 or self.findAnyTaskPi(u"piUpToDate"):
				if self.decideMyLog(u"UpdateRPI"): self.indiLOG.log(10, u"checkForUpdates updateNeeded {}  findAnyTaskPi: {}".format(self.updateNeeded, self.findAnyTaskPi(u"piUpToDate")) )
				self.fixConfig(checkOnly = ["all","rpi","force"],fromPGM="checkForUpdates") # checkForUpdates  # ok only if changes requested
				self.setupFilesForPi(calledFrom="checkForUpdates")
				self.updateNeeded = ""


			if not self.findAnyTaskPi(u"piUpToDate"):
				self.updateRejectListsCount =0
			else:
					self.newIgnoreMAC = 0
					for piU in self.RPI:

						if u"initSSH" in self.RPI[piU][u"piUpToDate"]:
							self.sshToRPI(piU, fileToSend="initSSH.exp")

						if u"upgradeOpSysSSH" in self.RPI[piU][u"piUpToDate"]:
							self.sshToRPI(piU, fileToSend="upgradeOpSysSSH.exp", endAction= "end")

						if u"updateAllFilesFTP" in self.RPI[piU][u"piUpToDate"]:
							self.sendFilesToPiFTP(piU, fileToSend="updateAllFilesFTP.exp")

						if u"updateParamsFTP" in self.RPI[piU][u"piUpToDate"]:
							self.sendFilesToPiFTP(piU, fileToSend="updateParamsFTP.exp")

						if u"restartmasterSSH" in self.RPI[piU][u"piUpToDate"]:
							self.sshToRPI(piU, fileToSend="restartmasterSSH.exp")

						if self.updateRejectListsCount < _GlobalConst_numberOfRPI:
							self.updateRejectListsCount +=1
							self.updateRejectLists()
						else:
							self.printpiUpToDate()

					if self.findTaskPi(u"piUpToDate","getStatsSSH"):
						for piU in self.RPI:
							if u"getStatsSSH" in self.RPI[piU][u"piUpToDate"]:
								self.sshToRPI(piU,fileToSend="getStatsSSH.exp")

					if self.findTaskPi(u"piUpToDate","getLogFileSSH"):
						for piU in self.RPI:
							if u"getLogFileSSH" in self.RPI[piU][u"piUpToDate"]:
								self.sshToRPI(piU,fileToSend="getLogFileSSH.exp")

					if self.findTaskPi(u"piUpToDate","getiBeaconList1SSH"):
						for piU in self.RPI:
							if u"getiBeaconList1SSH" in self.RPI[piU][u"piUpToDate"]:
								self.sshToRPI(piU,fileToSend="getiBeaconList1SSH.exp")

					if self.findTaskPi(u"piUpToDate","getiBeaconList0SSH"):
						for piU in self.RPI:
							if u"getiBeaconList0SSH" in self.RPI[piU][u"piUpToDate"]:
								self.sshToRPI(piU,fileToSend="getiBeaconList0SSH.exp")

					if self.findTaskPi(u"piUpToDate","shutdownSSH"):
						for piU in self.RPI:
							if u"shutdownSSH" in self.RPI[piU][u"piUpToDate"]:
								self.sshToRPI(piU,fileToSend="shutdownSSH.exp")

					if self.findTaskPi(u"piUpToDate","rebootSSH"):
						for piU in self.RPI:
							if u"rebootSSH" in self.RPI[piU][u"piUpToDate"] and not  "updateParamsFTP" in self.RPI[piU][u"piUpToDate"]:
								self.sshToRPI(piU,fileToSend="rebootSSH.exp")

					if self.findTaskPi(u"piUpToDate","resetOutputSSH"):
						for piU in self.RPI:
							if u"resetOutputSSH" in self.RPI[piU][u"piUpToDate"]  and not  "updateParamsFTP" in self.RPI[pIU][u"piUpToDate"]:
								self.sshToRPI(piU,fileToSend="resetOutputSSH.exp")

		except Exception, e:
			if len(unicode(e)) > 5 :
				self.indiLOG.log(40,"Line {} has error={}".format(sys.exc_traceback.tb_lineno, e))
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

			if now.minute % 5 == 0:
				if self.newIgnoreMAC > 0:
					for piU in self.RPI:
						self.setONErPiV(piU,"piUpToDate", [u"updateParamsFTP"])
					self.newIgnoreMAC = 0

				for piU in self.RPI:
					if self.RPI[piU][u"piOnOff"] == "0":					continue
					if self.RPI[piU][u"piDevId"] ==	 0:						continue
					if time.time() - self.RPI[piU][u"lastMessage"] < 330.:	continue
					if self.decideMyLog(u"Logic"): self.indiLOG.log(10, u"pi server # {}  ip# {}  has not send a message in the last {:.0f} seconds".format(piU, self.RPI[piU][u"ipNumberPi"], time.time() - self.RPI[piU][u"lastMessage"]))

		except Exception, e:
			if len(unicode(e)) > 5 :
				self.indiLOG.log(40,"Line {} has error={}".format(sys.exc_traceback.tb_lineno, e))
		return

####-------------------------------------------------------------------------####
	def BLEconnectCheckPeriod(self, force = False):
		try:
			if time.time()< self.currentlyBooting:
				return
			for dev in indigo.devices.iter("props.isBLEconnectDevice"):
				if self.queueListBLE == "update": self.sleep(0.1)

				lastStatusChangeDT = 99999
				props = dev.pluginProps
				try:
					expirationTime = float(props[u"expirationTime"]) + 0.1
				except:
					continue
				status = "expired"
				lastUp = dev.states[u"lastUp"]
				dt = time.time() - self.getTimetimeFromDateString(lastUp)
				if dt <= 1 * expirationTime:
					status = "up"
				elif dt <= self.expTimeMultiplier * expirationTime:
					status = "down"

				if dev.states[u"status"] != status or self.initStatesOnServer or force:
					if "lastStatusChange" in dev.states: 
						lastStatusChangeDT   =  time.time() - self.getTimetimeFromDateString(dev.states[u"lastStatusChange"]) 
					if lastStatusChangeDT > 3: 
						#if self.decideMyLog(u"BLE") and dev.name.find("BLE-C") >-1: self.indiLOG.log(10, u"BLEconnectCheckPeriod :"+dev.name+";  new status:"+ status+"; old status:"+ dev.states[u"status"]+"   dt="+ unicode(dt) +"; lastUp="+unicode(lastUp)+"; expirationTime="+unicode(expirationTime))
						if status == "up":
							dev.updateStateImageOnServer(indigo.kStateImageSel.SensorOn)
						elif status == "down":
							dev.updateStateImageOnServer(indigo.kStateImageSel.SensorOff)
						else:
							dev.updateStateImageOnServer(indigo.kStateImageSel.SensorTripped)
					self.addToStatesUpdateDict(dev.id,u"status", status)

				if status != "up":
					if unicode(dev.states[u"closestRPI"]) != "-1":
						self.addToStatesUpdateDict(dev.id,u"closestRPI", -1)

				self.executeUpdateStatesDict(onlyDevID=dev.id,calledFrom="BLEconnectCheckPeriod end")	  


		except Exception, e:
			if len(unicode(e)) > 5 :
				self.indiLOG.log(40,"Line {} has error={}".format(sys.exc_traceback.tb_lineno, e))
		return

####-------------------------------------------------------------------------####
	def checkSensorStatus(self):

		try:
			for dev in indigo.devices.iter("props.isSensorDevice"):
				if dev.deviceTypeId not in _GlobalConst_allowedSensors: continue
				dt = time.time()- self.checkSensorMessages(dev.id,"lastMessage", default=time.time())

				if time.time()< self.currentlyBooting: continue 
				if dt > 600:
					try:
						if	dev.pluginProps[u"displayS"].lower().find(u"temp")==-1:
							dev.updateStateImageOnServer(indigo.kStateImageSel.PowerOff)
						else:
							dev.updateStateImageOnServer(indigo.kStateImageSel.PowerOff)
					except:
						self.indiLOG.log(20, "checkSensorStatus: {} property displayS missing, please edit and save ".format(dev.name.encode("utf8")) )
						dev.updateStateImageOnServer(indigo.kStateImageSel.Error)
			self.saveSensorMessages(devId="")

		except Exception, e:
			if len(unicode(e)) > 5 :
				self.indiLOG.log(40,"Line {} has error={}".format(sys.exc_traceback.tb_lineno, e))
				try:
					self.indiLOG.log(40,unicode(dev.pluginProps))
				except:
					pass
		return


####-------------------------------------------------------------------------####
	def checkRPIStatus(self):
		try:
			if	time.time()< self.currentlyBooting: return 

			for piU in self.RPI:
				if self.RPI[piU][u"piDevId"] == 0:	 continue
				try:
					dev = indigo.devices[self.RPI[piU][u"piDevId"]]
				except:
					continue
				if self.RPI[piU][u"piOnOff"] == "0": 
					if time.time()- self.RPI[piU][u"lastMessage"] > 500:
						self.addToStatesUpdateDict(dev.id,u"online", u"expired")
						dev.updateStateImageOnServer(indigo.kStateImageSel.PowerOff)
						if piU in _rpiBeaconList: 
							self.addToStatesUpdateDict(dev.id,u"status", u"expired")
					continue

				if time.time()- self.RPI[piU][u"lastMessage"] > 240:
					self.addToStatesUpdateDict(dev.id,u"online", u"expired")
					if piU in _rpiSensorList: 
						self.addToStatesUpdateDict(dev.id,u"status", u"expired")
						dev.updateStateImageOnServer(indigo.kStateImageSel.PowerOff)
					else:
						if dev.states[u"status"] in [u"down","expired"]:
							dev.setErrorStateOnServer('IPconnection and BLE down')
							dev.updateStateImageOnServer(indigo.kStateImageSel.SensorTripped)
						else:
							dev.setErrorStateOnServer(u"")
							dev.updateStateImageOnServer(indigo.kStateImageSel.PowerOff)

				elif time.time()- self.RPI[piU][u"lastMessage"] >120:
					self.addToStatesUpdateDict(dev.id,u"online", u"down")
					if piU in _rpiSensorList: 
						self.addToStatesUpdateDict(dev.id,u"status", u"down")
						dev.updateStateImageOnServer(indigo.kStateImageSel.PowerOff)
					else:
						if dev.states[u"status"] in [u"down","expired"]:
							dev.setErrorStateOnServer('IPconnection and BLE down')
							dev.updateStateImageOnServer(indigo.kStateImageSel.SensorTripped)
						else:
							dev.setErrorStateOnServer(u"")
							dev.updateStateImageOnServer(indigo.kStateImageSel.PowerOff)

				else:
					self.addToStatesUpdateDict(dev.id,u"online", u"up")
					self.addToStatesUpdateDict(dev.id,u"status", u"up")
					dev.setErrorStateOnServer(u"")
					if piU in _rpiSensorList: 
							dev.updateStateImageOnServer(indigo.kStateImageSel.SensorOn)
					else:
						if dev.states[u"status"] in [u"down","expired"]:
							dev.updateStateImageOnServer(indigo.kStateImageSel.SensorOff)
						else:
							dev.updateStateImageOnServer(indigo.kStateImageSel.SensorOn)

		except Exception, e:
			if len(unicode(e)) > 5 :
				self.indiLOG.log(40,"Line {} has error={}".format(sys.exc_traceback.tb_lineno, e))


		return



####-------------------------------------------------------------------------####


# noinspection SpellCheckingInspection
	def BeaconsCheckPeriod(self, now, force = False):
		try:
			if	time.time()< self.currentlyBooting:
				if time.time()> self.lastUPtoDown:
					self.indiLOG.log(20, u"BeaconsCheckPeriod waiting for reboot, no changes in up--> down status for another {:.0f}[secs]".format(self.currentlyBooting - time.time())) 
					self.lastUPtoDown  = time.time()+90
				return False # noting for the next x minutes due to reboot 
			anyChange = False
			for beacon in self.beacons :
				if len(self.beacons[beacon][u"receivedSignals"]) < len(_rpiBeaconList):  
					self.fixBeaconPILength(beacon, u"receivedSignals")

				if beacon.find("00:00:00:00") ==0: continue
				dev =""
				if self.selectBeaconsLogTimer !={}: 
					for sMAC in self.selectBeaconsLogTimer:
						if beacon.find(sMAC[:self.selectBeaconsLogTimer[sMAC]]) ==0:
							self.indiLOG.log(20, u"sel.beacon logging: BeaconsCheckPeriod :"+beacon+"; "+(" ").ljust(30)  )
				changed = False
				if u"status" not in self.beacons[beacon] : continue
				## pause is set at device stop, check if still paused skip


				if self.selectBeaconsLogTimer !={}: 
					for sMAC in self.selectBeaconsLogTimer:
						if beacon.find(sMAC[:self.selectBeaconsLogTimer[sMAC]]) ==0:
							self.indiLOG.log(20, u"sel.beacon logging: BeaconsCheckPeriod :"+beacon+"; "+(" ").ljust(30) +"    passed pause" )

				if self.beacons[beacon][u"lastUp"] > 0:
					if self.beacons[beacon][u"ignore"] == 1 :
						if time.time()- self.beacons[beacon][u"lastUp"] > 3 * 86000 :  ## 3 days
							self.beacons[beacon][u"ignore"] = 2
					# if self.beacons[beacon][u"status"] ==u"expired": continue
					if self.beacons[beacon][u"ignore"] > 0 : continue
				if self.selectBeaconsLogTimer !={}: 
					for sMAC in self.selectBeaconsLogTimer:
						if beacon.find(sMAC[:self.selectBeaconsLogTimer[sMAC]]) ==0:
							self.indiLOG.log(20, u"sel.beacon logging: BeaconsCheckPeriod :"+beacon+"; "+(" ").ljust(30) +"    passed ignore" )

				expT = float(self.beacons[beacon][u"expirationTime"])
				if self.beacons[beacon][u"lastUp"] < 0:	 # fast down was last event, block for 5 secs after that
					if time.time() + self.beacons[beacon][u"lastUp"] > 5:
						self.beacons[beacon][u"lastUp"] = time.time()- expT-0.1
					else:
						if self.selectBeaconsLogTimer !={}: 
							for sMAC in self.selectBeaconsLogTimer:
								if beacon.find(sMAC[:self.selectBeaconsLogTimer[sMAC]]) ==0:
									self.indiLOG.log(20, u"sel.beacon logging: BeaconsCheckPeriod :{:30s}    no change in up status, dt:{:.0f}".format(beacon, time.time() + self.beacons[beacon][u"lastUp"]) )
						continue

				delta = time.time()- self.beacons[beacon][u"lastUp"]  ##  no !! - self.beacons[beacon][u"updateSignalValuesSeconds"]
				if self.beacons[beacon][u"status"] == u"up" :
					if delta > expT :
						self.beacons[beacon][u"status"] = u"down"
						self.beacons[beacon][u"updateFING"] = 1
						#self.indiLOG.log(20,	u" up to down secs: delta= " + unicode(delta) + " expT: " + unicode(expT) + "  " + beacon)
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
						#self.indiLOG.log(20,	u" down to up secs: delta= " + unicode(delta) + " expT: " + unicode(expT) + "  " + beacon)
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
							self.indiLOG.log(20, u"sel.beacon logging: BeaconsCheckPeriod: {:30s}    status: {};  deltaT: {}".format(beacon, self.beacons[beacon][u"status"], delta))


				if changed or force:
					if self.decideMyLog(u"BeaconData"): self.indiLOG.log(10, u"BeaconsCheckPeriod changed=true or force {}  {}" .format(beacon, self.beacons[beacon][u"status"]) )

					try :
						dev = indigo.devices[self.beacons[beacon][u"indigoId"]]
						props = dev.pluginProps
						if dev.states[u"groupMember"] !="": anyChange = True
						self.addToStatesUpdateDict(dev.id,u"status", self.beacons[beacon][u"status"])

						if self.beacons[beacon][u"status"] == u"up":
							if u"closestRPI" in dev.states: 
								closest =  self.findClosestRPI(beacon,dev)
								if closest != dev.states[u"closestRPI"]:
									if unicode(dev.states[u"closestRPI"]) !="-1":
										self.addToStatesUpdateDict(dev.id,u"closestRPILast", dev.states["closestRPI"])
										self.addToStatesUpdateDict(dev.id,u"closestRPITextLast", dev.states["closestRPIText"])
									self.addToStatesUpdateDict(dev.id,u"closestRPI", closest)
									self.addToStatesUpdateDict(dev.id,u"closestRPIText",self.getRPIdevName((closest)))
							if self.beacons[beacon][u"note"].find(u"beacon")>-1: 
								dev.updateStateImageOnServer(indigo.kStateImageSel.SensorOn) # not for RPI's

						elif self.beacons[beacon][u"status"] == u"down":
							if self.beacons[beacon][u"note"].find(u"beacon")>-1:
								if u"closestRPI" in dev.states:
									if closestRPI != dev.states["closestRPI"]:
										if unicode(dev.states[u"closestRPI"]) !="-1":
											self.addToStatesUpdateDict(dev.id,u"closestRPILast", dev.states["closestRPI"])
											self.addToStatesUpdateDict(dev.id,u"closestRPITextLast", dev.states["closestRPIText"])
									self.addToStatesUpdateDict(dev.id,u"closestRPI", -1)
									if self.setClostestRPItextToBlank:self.addToStatesUpdateDict(dev.id,u"closestRPIText", "")
								dev.updateStateImageOnServer(indigo.kStateImageSel.SensorOff)
							#else: this is handled in RPI update
							#	 dev.updateStateImageOnServer(indigo.kStateImageSel.Error)

						else:
							if self.beacons[beacon][u"note"].find(u"beacon") > -1:
								dev.updateStateImageOnServer(indigo.kStateImageSel.SensorTripped)
								if u"closestRPI" in dev.states:
									if closestRPI != dev.states["closestRPI"]:
										if unicode(dev.states[u"closestRPI"]) !="-1":
											self.addToStatesUpdateDict(dev.id,u"closestRPILast", dev.states["closestRPI"])
											self.addToStatesUpdateDict(dev.id,u"closestRPITextLast", dev.states["closestRPIText"])
									self.addToStatesUpdateDict(dev.id,u"closestRPI", -1)
									if self.setClostestRPItextToBlank: self.addToStatesUpdateDict(dev.id,u"closestRPIText", "")
							#else: this is handled in RPI update
							#	 dev.updateStateImageOnServer(indigo.kStateImageSel.Error)

						if beacon in self.CARS[u"beacon"]: 
							self.updateCARS(beacon,dev,self.beacons[beacon])

						if u"showBeaconOnMap" in props and props[u"showBeaconOnMap"] in _GlobalConst_beaconPlotSymbols:self.beaconPositionsUpdated =3

					except Exception, e:
						if unicode(e).find(u"timeout waiting") > -1:
							self.indiLOG.log(40,"Line {} has error={}".format(sys.exc_traceback.tb_lineno, e))
							self.indiLOG.log(40,u"BeaconsCheckPeriod communication to indigo is interrupted")
							return

				if now.minute != self.lastMinuteChecked:
					try :
						devId = int(self.beacons[beacon][u"indigoId"])
						if devId > 0 :
							try:
								dev = indigo.devices[self.beacons[beacon][u"indigoId"]]
								if self.beacons[beacon][u"ignore"]	 ==-1: # was special, device exists now, set back to normal 
									self.indiLOG.log(20, u"BeaconsCheckPeriod minute resetting ignore from -1 to 0 for beacon: {}   beaconDict: {}".format(beacon, self.beacons[beacon]))
									self.beacons[beacon][u"ignore"] = 0
							except Exception, e:
								if unicode(e).find(u"timeout waiting") > -1:
									self.indiLOG.log(40,"Line {} has error={}".format(sys.exc_traceback.tb_lineno, e))
									self.indiLOG.log(40,u"BeaconsCheckPeriod communication to indigo is interrupted")
									return
								if unicode(e).find(u"not found in database") ==-1:
									self.indiLOG.log(40,"Line {} has error={}".format(sys.exc_traceback.tb_lineno, e))
									return

								self.indiLOG.log(20, u"=== deleting device beaconDict: " + unicode(self.beacons[beacon]))
								self.beacons[beacon][u"indigoId"] = 0
								self.beacons[beacon][u"ignore"]	  = 1
								dev =""
								continue

							if dev != "" and dev.states[u"status"] == "up":

								for piU in _rpiBeaconList:
									if	dev.states[u"Pi_" + piU.rjust(2,"0")  + u"_Distance"] == 99999.: continue
									if dev.states[u"Pi_" + piU.rjust(2,"0")  + u"_Time"] != "":
										piTime = self.getTimetimeFromDateString(dev.states[u"Pi_" + piU.rjust(2,"0")  + u"_Time"]) 
										if time.time()- piTime> max(330., self.beacons[beacon][u"updateSignalValuesSeconds"]):
											if	dev.states[u"Pi_" + piU.rjust(2,"0") + u"_Distance"] != 99999.:
												self.addToStatesUpdateDict(dev.id,u"Pi_" + piU.rjust(2,"0")  + u"_Distance", 99999.,decimalPlaces=1)
									else :
										self.addToStatesUpdateDict(dev.id,u"Pi_" + piU.rjust(2,"0")  + u"_Distance", 99999.,decimalPlaces=1)
							self.executeUpdateStatesDict(onlyDevID=dev.id, calledFrom="BeaconsCheckPeriod 2")

							if beacon in self.CARS[u"beacon"]: 
								self.updateCARS(beacon,dev,self.beacons[beacon])


					except Exception, e:
						if len(unicode(e)) > 5 :
							self.indiLOG.log(40,"Line {} has error={}".format(sys.exc_traceback.tb_lineno, e))

				if dev !="":
					self.executeUpdateStatesDict(onlyDevID=dev.id,calledFrom="BeaconsCheckPeriod end")

		except Exception, e:
			if len(unicode(e)) > 5 :
				self.indiLOG.log(40,"Line {} has error={}".format(sys.exc_traceback.tb_lineno, e))
				try: self.indiLOG.log(40,"============= {}".format(dev.name.encode("utf8")))
				except: pass
		return anyChange

####-------------------------------------------------------------------------####
	def checkHour(self,now):
		try:
		
			if now.hour == self.lastHourChecked: return
			if now.hour ==0:
				self.resetMinMaxSensors()
			self.rollOverRainSensors()

			self.fixConfig(checkOnly = ["all","rpi","force"],fromPGM="checkHour")
			if now.hour ==0 :
				self.checkPiEnabled()

			self.saveCARS(force=True)
			try:
				for beacon in self.beacons:	 # sync with indigo
					if beacon.find("00:00:00:00") ==0: continue
					if self.beacons[beacon][u"indigoId"] != 0:	# sync with indigo
						try :
							dev = indigo.devices[self.beacons[beacon][u"indigoId"]]
							if self.beacons[beacon][u"ignore"] == 1:
								self.indiLOG.log(20, u"=== deleting device: {} beacon to be ignored, clean up ".format(dev.name.encode("utf8")))
								indigo.device.delete(dev)
								continue
							self.beacons[beacon][u"status"] = dev.states[u"status"]
							self.beacons[beacon][u"note"] = dev.states[u"note"]

	 
							if self.removeJunkBeacons:
								if dev.name == u"beacon_" + beacon and self.beacons[beacon][u"status"] == u"expired" and time.time()- self.beacons[beacon][u"lastUp"] > 3600 and self.countLoop > 10 :
									self.indiLOG.log(30, u"=== deleting beacon: {}  expired, no messages for > 1 hour and still old name, if you want to keep beacons, you must rename them after they are created".format(dev.name.encode("utf8")))
									self.beacons[beacon][u"ignore"] = 1
									self.newIgnoreMAC += 1
									indigo.device.delete(dev)
						except Exception, e:
							if len(unicode(e)) > 5 :
								self.indiLOG.log(40,"Line {} has error={}".format(sys.exc_traceback.tb_lineno, e))
							if unicode(e).find(u"timeout waiting") >-1:
								self.indiLOG.log(40, u"communication to indigo is interrupted")
								return
							if unicode(e).find(u"not found in database") >-1:
								self.indiLOG.log(40, "=== deleting mark .. indigoId lookup error, setting to ignore beaconDict: {}".format(self.beacons[beacon]) )
								self.beacons[beacon][u"indigoId"] = 0
								self.beacons[beacon][u"ignore"]   = 1
								self.beacons[beacon][u"status"]   = u"ignored"
							else:
								return

					else :
						self.beacons[beacon][u"status"] = u"ignored"
						if self.beacons[beacon][u"ignore"] == 0:
							self.indiLOG.log(20, u"setting beacon: {}  to ignore --  was set to indigo-id=0 before".format(beacon) )
							self.indiLOG.log(20, "       contents: {}".format(self.beacons[beacon])  )
							self.beacons[beacon][u"ignore"]	 = 1
							self.newIgnoreMAC 				+= 1
							self.writeJson(self.beacons, fName=self.indigoPreferencesPluginDir + "beacons", fmtOn=self.beaconsFileSort)


			except Exception, e:
				if len(unicode(e)) > 5 :
					self.indiLOG.log(40,"Line {} has error={}".format(sys.exc_traceback.tb_lineno, e))

			try:
				if now.hour == 0:
					self.deleteAndCeateVariables(True)	# delete and recreate the variables at midnight to remove their sql database entries
					self.setALLrPiV(u"piUpToDate", [u"updateParamsFTP"])
					##self.rPiRestartCommand = [u"" for ii in range(_GlobalConst_numberOfRPI)] # dont do this use the default for each pibeacon
					self.setupFilesForPi()
					for piU in self.RPI:
						self.sendFilesToPiFTP(piU, fileToSend=u"updateParamsFTP.exp")
					self.updateRejectLists()
			except Exception, e:
				if len(unicode(e)) > 5 :
					self.indiLOG.log(40,"Line {} has error={}".format(sys.exc_traceback.tb_lineno, e))
		except Exception, e:
			if len(unicode(e)) > 5 :
				self.indiLOG.log(40,"Line {} has error={}".format(sys.exc_traceback.tb_lineno, e))

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
		except Exception, e:
			if len(unicode(e)) > 5 :
				self.indiLOG.log(40,"Line {} has error={}".format(sys.exc_traceback.tb_lineno, e))

		try:
		### report on bad ibeacon battery status
			if self.lastDayChecked[len(self.checkBatteryLevelHours)] != now.day and now.hour == 8:
				badBeacons	= 0
				testBeacons	= 0
				out			= ""
				for dev in indigo.devices.iter("props.isBeaconDevice"):
					props = dev.pluginProps
					if "batteryLevelUUID" not in props: 					continue
					if props["batteryLevelUUID"].find("batteryLevel") ==-1: continue
					if "batteryLevel" not in dev.states: 					continue
					if "batteryLevelLastUpdate" not in dev.states: 			continue
					testBeacons += 1
					try: 	batteryLevel = int(dev.states["batteryLevel"])	
					except: batteryLevel = 0
					batteryLevelLastUpdate = dev.states["batteryLevelLastUpdate"]	
					if len(batteryLevelLastUpdate) < 19: batteryLevelLastUpdate = "2000-01-01 00:00:00"
					lastTimeStamp = self.getTimetimeFromDateString(batteryLevelLastUpdate)
					#self.indiLOG.log(10,"  ibeacon: {:30s}  level: {:3d}%,  last update was: {} ".format(dev.name, batteryLevel, batteryLevelLastUpdate) )
					if time.time() - lastTimeStamp > 2*24*3600:
						badBeacons+=1
						out += "{:35s}last level reported: {:3d}%, has not been updated for > 2 days: {}\n".format(dev.name.encode("utf8"), batteryLevel, batteryLevelLastUpdate) 
						#trigger  tbi
					elif batteryLevel < 20:
						badBeacons+=1
						out += "{:35s}      level down to: {:3d}% ... charge or replace battery\n".format(dev.name.encode("utf8"), batteryLevel) 
						#trigger tbi
				if out != "":
					self.indiLOG.log(30,"batterylevel level test:\n{}".format(out) )
				elif testBeacons > 0 and badBeacons == 0: self.indiLOG.log(20,"batterylevel level test:  no iBeacon found with low battery indicator or old update")
				self.lastDayChecked[len(self.checkBatteryLevelHours)] = now.day

		
		except Exception, e:
			if len(unicode(e)) > 5 :
				self.indiLOG.log(40,"Line {} has error={}".format(sys.exc_traceback.tb_lineno, e))

		##### second .. nothing yet
		
		return 



####-------------------------------------------------------------------------####
	def checkPiEnabled(self): # check if pi is defined, but not enabled, give warning at startup
		try:
			for piU in self.RPI:
				if self.RPI[piU][u"piOnOff"] != u"0": continue
				if self.RPI[piU][u"piDevId"] ==	   0: continue

				if (self.RPI[piU][u"passwordPi"]		 !=""  and
					self.RPI[piU][u"userIdPi"]			 !=""  and
					self.RPI[piU][u"ipNumberPi"]		 != "" and
					self.RPI[piU][u"piMAC"]				 != "" and
					self.RPI[piU][u"ipNumberPiSendTo"]	 != "" ):
						self.indiLOG.log(20, u"pi# " + piU + " is configured but not enabled, mistake? This is checked once a day;  to turn it off set userId or password of unused rPi to empty ")
		except Exception, e:
			self.indiLOG.log(40,"Line {} has error={}".format(sys.exc_traceback.tb_lineno, e))

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
						piU = unicode(pi)
					except:
						self.indiLOG.log(20, u"device not fully defined, please edit {} pi# not defined:  {}".format(dev.name.encode("utf8"), unicode(props)))
						continue

					if self.checkDevToPi(piU, devId, dev.name, u"input",  u"in",  sensor, _GlobalConst_allowedSensors): anyChange= True
					#indigo.server.log("syncSensors A01: "+ unicode(anyChange)+"  "+ unicode(time.time() - ss))
					if self.checkDevToPi(piU, devId, dev.name, u"output", u"out", sensor, _GlobalConst_allowedOUTPUT):  anyChange= True
					#indigo.server.log("syncSensors A02: "+ unicode(anyChange)+"  "+ unicode(time.time() - ss))

				if u"description" in props and	props[u"description"] !="" and props[u"description"] != dev.description:
					dev.description =  props[u"description"] 
					dev.replaceOnServer()
					anyChange = True
			#indigo.server.log("syncSensors AT: "+ unicode(anyChange)+"  "+ unicode(time.time() - ss))

			for piU in self.RPI:
				self.checkSensortoPi(piU, u"input")
				self.checkSensortoPi(piU, u"output")
				if self.mkSensorList(piU): anyChange =True
			#indigo.server.log("syncSensors BT: "+ unicode(anyChange)+"  "+ unicode(time.time() - ss))

		except Exception, e:
			self.indiLOG.log(40,"Line {} has error={}".format(sys.exc_traceback.tb_lineno, e))
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
				except Exception, e:

					self.indiLOG.log(40,"Line {} has error={}".format(sys.exc_traceback.tb_lineno, e))
					if unicode(e).find(u"timeout waiting") > -1:
						self.indiLOG.log(40,u"communication to indigo is interrupted")
						return False
					if unicode(e).find(u"not found in database") ==-1:
						return False
					name=""
				self.indiLOG.log(20, u"fixing 1  {}   {} pi {}; sensor: {} devName: {}".format(name.encode("utf8"), devId, piU, sensor, name) )
				self.indiLOG.log(20, u"fixing 1  rpi {}".format(self.RPI[piU][io]))
				self.RPI[piU][io][sensor] = {unicode(devId): ""}
				self.setONErPiV(piU,"piUpToDate", [u"updateParamsFTP"])
				anyChange = True
			if len(self.RPI[piU][io][sensor]) == 0:
				self.RPI[piU][io][sensor] = {unicode(devId): ""}
				anyChange = True

			elif unicode(devId) not in self.RPI[piU][io][sensor]:
				self.indiLOG.log(20, u"fixing 2  {}   {}  pi {} sensor{}".format(name.encode("utf8"), devId, piU, sensor) )
				self.RPI[piU][io][sensor][unicode(devId)] = ""
				anyChange = True
		except Exception, e:
			self.indiLOG.log(40,"Line {} has error={}".format(sys.exc_traceback.tb_lineno, e))
		return anyChange



####-------------------------------------------------------------------------####
	def checkSensortoPi(self, pi, io):
		try:
			anyChange = False
			piU = unicode(pi)
			pi = int(pi)
			for sensor in self.RPI[piU][io]:
				if len(self.RPI[piU][io][sensor]) > 0:
					deldevID = {}
					for devIDrpi in self.RPI[piU][io][sensor]:
						try:
							try:
								devID = int(devIDrpi)
								dev = indigo.devices[devID]
							except Exception, e:
								if unicode(e).find(u"timeout waiting") > -1:
									self.indiLOG.log(40,"Line {} has error={}".format(sys.exc_traceback.tb_lineno, e))
									self.indiLOG.log(40,u"communication to indigo is interrupted")
									return True
								if unicode(e).find(u" not found in database") ==-1:
									self.indiLOG.log(40,"Line {} has error={}".format(sys.exc_traceback.tb_lineno, e))
									return True

								deldevID[devIDrpi] = 1
								self.indiLOG.log(40,"device not found in indigo DB, ok if device was just deleted")
								self.indiLOG.log(40,"removing input device from parameters for pi#:{}  devID={}".format(piU, devIDrpi))
								anyChange = True
								continue


							props = dev.pluginProps
							if u"rPiEnable"+piU not in props and  u"piServerNumber" not in props:
								self.indiLOG.log(20, "piServerNumber not in props for pi#: {}  devID= {}   removing sensor{}".format(piU, devID, self.RPI[piU][io][sensor]) )
								self.RPI[piU][io][sensor] = {}
								anyChange = True
								continue

							if u"piServerNumber" in props:
								if sensor != dev.deviceTypeId or devID != dev.id or piU != props[u"piServerNumber"]:
									self.indiLOG.log(20, u"sensor/devid/pi/wrong for  pi#: {}  devID= {} props{}\n >>>>> removing sensor <<<<".format(piU, self.RPI[piU][io][sensor], unicode(props)) )
									self.RPI[piU][io][sensor] = {}
									anyChange = True
								if u"address" in props:
									if props[u"address"] != u"Pi-" + piU:
										props[u"address"] = u"Pi-" + piU
										if self.decideMyLog(u"Logic"): self.indiLOG.log(10, "updating address for {}".format(piU) )
										self.deviceStopCommIgnore = time.time()
										dev.replacePluginPropsOnServer(props)
										anyChange = True
								else:
									props[u"address"] = u"Pi-" + piU
									self.deviceStopCommIgnore = time.time()
									dev.replacePluginPropsOnServer(props)
									if self.decideMyLog(u"Logic"): self.indiLOG.log(10, "updating address for {}".format(piU) )
									anyChange = True
							else:
								pass

						except Exception, e:
							self.indiLOG.log(40,"Line {} has error={}".format(sys.exc_traceback.tb_lineno, e))
							if unicode(e).find(u"not found in database") ==-1:
								return True
							self.indiLOG.log(40,u"removing input device from parameters for pi# {}  {}".format(piU, self.RPI[piU][io][sensor]) )
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

		except Exception, e:
			self.indiLOG.log(40,"Line {} has error={}".format(sys.exc_traceback.tb_lineno, e))
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
									decimalPlaces = len(xxx[1])
							except:
								decimalPlaces = 2

							if init: # at start of pgm
								reset = False
								try: 
									int(dev.states[ttx+u"MinYesterday"])
								except:
									reset = True
								if not reset: 
									try:
										if	(float(dev.states[ttx+u"MaxToday"]) == float(dev.states[ttx+u"MinToday"]) and float(dev.states[ttx+u"MaxToday"]) == 0.) :	 reset = True
									except: pass
								if reset:
									self.addToStatesUpdateDict(dev.id,ttx+u"MaxYesterday", val,decimalPlaces=decimalPlaces)
									self.addToStatesUpdateDict(dev.id,ttx+u"MinYesterday", val,decimalPlaces=decimalPlaces)
									self.addToStatesUpdateDict(dev.id,ttx+u"MaxToday",		val,decimalPlaces=decimalPlaces)
									self.addToStatesUpdateDict(dev.id,ttx+u"MinToday",		val,decimalPlaces=decimalPlaces)

							elif nHour ==0:	 # update at midnight 
									self.addToStatesUpdateDict(dev.id,ttx+u"MaxYesterday", dev.states[ttx+u"MaxToday"], decimalPlaces = decimalPlaces)
									self.addToStatesUpdateDict(dev.id,ttx+u"MinYesterday", dev.states[ttx+u"MinToday"], decimalPlaces = decimalPlaces)
									self.addToStatesUpdateDict(dev.id,ttx+u"MaxToday",		dev.states[ttx], decimalPlaces = decimalPlaces)
									self.addToStatesUpdateDict(dev.id,ttx+u"MinToday",		dev.states[ttx], decimalPlaces = decimalPlaces)
							self.executeUpdateStatesDict(onlyDevID=dev.id,calledFrom="resetMinMaxSensors")
		except Exception, e:
			self.indiLOG.log(40,"Line {} has error={}".format(sys.exc_traceback.tb_lineno, e))

####----------------------reset sensor min max at midnight -----------------------------------####
	def fillMinMaxSensors(self,dev,stateName,value,decimalPlaces):
		try:
			if value == "": return 
			if stateName not in _GlobalConst_fillMinMaxStates: return 
			if stateName in dev.states and stateName+u"MaxToday" in dev.states:
				val = float(value)
				if val > float(dev.states[stateName+u"MaxToday"]):
					self.addToStatesUpdateDict(dev.id,stateName+u"MaxToday",	 val, decimalPlaces=decimalPlaces)
				if val < float(dev.states[stateName+u"MinToday"]):
					self.addToStatesUpdateDict(dev.id,stateName+u"MinToday",	 val, decimalPlaces=decimalPlaces)
		except Exception, e:
			self.indiLOG.log(40,"Line {} has error={}".format(sys.exc_traceback.tb_lineno, e))

####----------------------reset rain sensor every hour/day/week/month/year -----------------------------------####
	def rollOverRainSensors(self):
		try:
			dd = datetime.datetime.now()
			currDate = (dd.strftime("%Y-%m-%d-%H")).split("-")
			weekNumber = dd.isocalendar()[1]

			#self.indiLOG.log(20,	u"currDate: " +unicode(currDate), mType="rollOverRainSensors")
			for dev in indigo.devices.iter("props.isSensorDevice"):
				if dev.deviceTypeId.find(u"rainSensorRG11") == -1: continue
				if	not dev.enabled: continue
				props = dev.pluginProps
				lastTest = props[u"lastDateCheck"].split("-")
				try:
					ff = datetime.datetime.strptime(props[u"lastDateCheck"], "%Y-%m-%d-%H")
					lastweek = ff.isocalendar()[1]
				except:
					lastweek = -1

				#self.indiLOG.log(20,	u"lasttest: " +unicode(lastTest), mType="rollOverRainSensors")
				for test in ["hour","day","week","month","year"]:
					if test == "hour"	and int(lastTest[3]) == int(currDate[3]): continue
					if test == "day"	and int(lastTest[2]) == int(currDate[2]): continue
					if test == "month"	and int(lastTest[1]) == int(currDate[1]): continue
					if test == "year"	and int(lastTest[0]) == int(currDate[0]): continue
					if test == "week"	and lastweek		 == weekNumber:		  continue
					ttx = test+"Rain"
					val = dev.states[ttx]
					#self.indiLOG.log(20,	u"rolling over: " +unicode(ttx)+";  using current val: "+ unicode(val), mType="rollOverRainSensors")
					self.addToStatesUpdateDict(dev.id,"last"+ttx, val,decimalPlaces=self.rainDigits)
					self.addToStatesUpdateDict(dev.id,ttx, 0,decimalPlaces=self.rainDigits)
					try:	 props[test+"RainTotal"]  = float(dev.states["totalRain"])
					except:	 props[test+"RainTotal"]  = 0
				props[u"lastDateCheck"] = dd.strftime("%Y-%m-%d-%H")
				self.deviceStopCommIgnore = time.time()
				dev.replacePluginPropsOnServer(props)
				self.executeUpdateStatesDict(onlyDevID=dev.id,calledFrom="rollOverRainSensors")
		except Exception, e:
			self.indiLOG.log(40,"Line {} has error={}".format(sys.exc_traceback.tb_lineno, e))


####-------------------------------------------------------------------------####
	def mkSensorList(self, pi):
		try:
			anyChange = False
			sensorList = ""
			INPgpioTypes = []
			piU = unicode(pi)
			for sensor in self.RPI[piU][u"input"]:
				if sensor not in _GlobalConst_allowedSensors and sensor not in _GlobalConst_allowedOUTPUT : continue
				if sensor ==u"ultrasoundDistance": continue
				try:
					#					 devId= int(self.RPI[piU][u"input"][sensor].keys()[0])# we only need the first one
					for devIds in self.RPI[piU][u"input"][sensor]:
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

				except Exception, e:
					self.indiLOG.log(40,"Line {} has error={}".format(sys.exc_traceback.tb_lineno, e))
					if unicode(e).find(u"timeout waiting") > -1:
						self.indiLOG.log(40,u"communication to indigo is interrupted")
						return
					if unicode(e).find(u"not found in database") ==-1:
						return
					self.RPI[piU][u"input"][sensor] = {}
			if sensorList != self.RPI[piU][u"sensorList"]:
				self.setONErPiV(piU,"piUpToDate", [u"updateParamsFTP"])
				anyChange = True
			self.RPI[piU][u"sensorList"] = sensorList

		except Exception, e:
			self.indiLOG.log(40,"Line {} has error={}".format(sys.exc_traceback.tb_lineno, e))
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
			if newVar.name.find(u"pi_IN_") != 0:   return
			if len(newVar.value) < 3:			   return
			self.addToDataQueue(newVar.name,json.loads(newVar.value),newVar.value )
			return
		except Exception, e:
			self.indiLOG.log(40,"Line {} has error={}".format(sys.exc_traceback.tb_lineno, e))
			self.indiLOG.log(40, newVar.value)


####-------------------------------------------------------------------------####
	def addToDataQueue(self,  varNameIN, varJson, varUnicode):	#
		try:
			if not self.stackReady : return 


				
			## alive message?
			if varNameIN == u"pi_IN_Alive":
				self.updateAlive(varJson,varUnicode, time.time())
				if self.statusChanged > 0:	  
					self.setGroupStatus()
				return

			## check pi#s  etc 
			try:
				pi = int(varNameIN.split(u"_IN_")[1])
				piU = unicode(pi)  ## it is pi_IN_0 .. pi_IN_99
			except:
				self.indiLOG.log(20, u"bad data  Pi not integer:  {}".format(varNameIN) )
				return

			if self.trackRPImessages == pi:
				self.indiLOG.log(20, u"pi# {} msg tracking: {} ".format(piU, varUnicode ) )

			if piU not in _rpiList:
				self.indiLOG.log(20, u"pi# rejected outside range:  {}".format(varNameIN) )
				return


			## add to message queue
			beaconUpdatedIds =[]
			self.messagesQueue.put((time.time(), piU, varJson, varUnicode))
			if not self.queueActive: 
				beaconUpdatedIds += self.workOnQueue()


			##
			# update non competing stuff, does not have be done sequential

			##
			# update RPI expirations
			self.RPI[piU][u"lastMessage"] = time.time()
			self.setRPIonline(piU, setLastMessage=True)

			##
			# update sensors
			if u"sensors" in varJson:
				if "BLEconnect" in varJson[u"sensors"]:
					self.BLEconnectupdateAll(piU, varJson[u"sensors"])
				self.updateSensors(piU, varJson[u"sensors"])

			##
			# update outputState
			if u"outputs" in varJson:
				self.updateOutput(piU, varJson[u"outputs"])

			##
			if u"BLEreport" in varJson: 
				self.printBLEreport(varJson["BLEreport"])
				return 

			##
			if u"i2c" in varJson:
				self.checkI2c(piU, varJson[u"i2c"])

			##
			if u"bluetooth" in varJson:
				self.checkBlueTooth(piU, varJson[u"bluetooth"])

			self.findClosestiBeaconToRPI(piU, beaconUpdatedIds=beaconUpdatedIds, BeaconOrBLE="beacon")
			self.executeUpdateStatesDict(calledFrom="addToDataQueue")


		except Exception, e:
			self.indiLOG.log(40,"Line {} has error={}".format(sys.exc_traceback.tb_lineno, e))
			self.indiLOG.log(40,varNameIN+     + varUnicode[0:30])


####-------------------------------------------------------------------------####
	def workOnQueue(self):

		beaconUpdatedIds =[]
		self.queueActive  = True
		while not self.messagesQueue.empty():
			item = self.messagesQueue.get() 
			for ii in range(40):
				if self.queueList ==u"update" : break
				if self.queueList ==u""		  : break
				if ii > 0:	pass
				time.sleep(0.05)
			self.queueList = "update"  
			beaconUpdatedIds += self.execUpdate(item[0],item[1],item[2],item[3])
			#### indigo.server.log(unicode(item[1])+"  "+ unicode(beaconUpdatedIds)+" "+ item[3])
		self.messagesQueue.task_done()
		self.queueActive  = False
		self.queueList = ""	 
		if len(self.sendBroadCastEventsList): self.sendBroadCastNOW()
		return beaconUpdatedIds
 
####-------------------------------------------------------------------------####
	def execUpdate(self, timeStampOfReceive, pi, data, varUnicode):

		beaconUpdatedIds = []
		try:

			piU = unicode(pi)
			retCode, piMAC, piN = self.checkincomingMACNo(data, piU, timeStampOfReceive)
			if not retCode: return beaconUpdatedIds
			if piU not in  _rpiBeaconList: return beaconUpdatedIds


			### here goes the beacon data updates  -->

			if self.selectBeaconsLogTimer !={}: 
				for sMAC in self.selectBeaconsLogTimer:
					if piMAC.find(sMAC[:self.selectBeaconsLogTimer[sMAC]]) ==0:
						self.indiLOG.log(20, u"sel.beacon logging: RPI msg{} ; {} ; pi#={} ".format(piMAC, (" ").ljust(36) ,piU) )

			if u"piMAC" in data:
				if self.decideMyLog(u"BeaconData"): self.indiLOG.log(10, u"new iBeacon message----------------------------------- \n {}".format(varUnicode) )
				secondsCollected = 0
				if u"secsCol" in data:
					secondsCollected = data[u"secsCol"]
				msgs = data[u"msgs"]
				if len(msgs) > 0 and piMAC != "":
					if u"ipAddress" in data:
						ipAddress = data[u"ipAddress"]
						if self.RPI[piU][u"ipNumberPi"] != "" and self.RPI[piU][u"ipNumberPi"] != ipAddress:
							if ipAddress == "":
								self.setONErPiV(piU,"piUpToDate", [u"updateParamsFTP","rebootSSH"])
								self.indiLOG.log(30, u"rPi#: {}  ip# send from rPi is empty, you should restart rPi, ip# should be {}".format(piU, self.RPI[piU][u"ipNumberPi"] ))
								return beaconUpdatedIds
							else:
								self.indiLOG.log(30, u"rPi#:{} {}: IP number has changed to {}, please fix in menue/pibeacon/setup RPI to reflect changed IP number or fix IP# on RPI\n this can happen when WiFi and ethernet are both active, try setting wlan/eth parameters in RPI device edit;  ==> ignoring data".format(piU, self.RPI[piU][u"ipNumberPi"], ipAddress ))
								return beaconUpdatedIds
					else:
						return beaconUpdatedIds

					beaconUpdatedIds = self.updateBeaconStates(piU, piN, ipAddress, piMAC, secondsCollected, msgs)
					self.RPI[piU][u"emptyMessages"] = 0
				elif len(msgs) == 0 and piMAC != "":
					self.RPI[piU][u"emptyMessages"] +=1
					if	self.RPI[piU][u"emptyMessages"] >  min(self.enableRebootRPIifNoMessages,10) :
						if	self.RPI[piU][u"emptyMessages"] %5 ==0:
							self.indiLOG.log(20, "RPI# {} check , too many empty messages in a row: {}".format(piU, self.RPI[piU][u"emptyMessages"]) )
							self.indiLOG.log(20, " please check RPI" )
						if	self.RPI[piU][u"emptyMessages"] > self.enableRebootRPIifNoMessages:
							self.indiLOG.log(30, "RPI# {} check , too many empty messages in a row: {}".format(piU, self.RPI[piU][u"emptyMessages"]) )
							self.indiLOG.log(30, "sending reboot command to RPI")
							self.setONErPiV(piU,"piUpToDate",[u"updateParamsFTP","rebootSSH"])
							self.RPI[piU][u"emptyMessages"] = 0

		except Exception, e:
			self.indiLOG.log(40,"Line {} has error={}".format(sys.exc_traceback.tb_lineno, e))
			self.indiLOG.log(40,varUnicode)

		if self.statusChanged > 0:
			self.setGroupStatus()
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
				try:	cutOffForClosestBeacon = float(rpiprops[u"cutOffForClosestBeacon"])
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
				if "IgnoreBeaconForClosestToRPI" in props and props[u"IgnoreBeaconForClosestToRPI"] !="0":	continue



				try: 
					if dist  < closestDist:
						closestDist = dist
						closestName = dev.name
				except Exception, e:
					self.indiLOG.log(40,"Line {} has error={}".format(sys.exc_traceback.tb_lineno, e))
					
			if closestDist < cutOffForClosestBeacon:
					cN = closestName+"@"+unicode(closestDist)
					if rpiDev.states["closestiBeacon"] !=cN:
						self.addToStatesUpdateDict(unicode(rpiDev.id),u"closestiBeacon", cN)
						self.addToStatesUpdateDict(unicode(rpiDev.id),u"closestiBeaconLast", rpiDev.states["closestiBeacon"])
			else:
				if rpiDev.states["closestiBeacon"] !="None":
					self.addToStatesUpdateDict(unicode(rpiDev.id),"closestiBeacon","None")
					
					 
		except Exception, e:
			self.indiLOG.log(40,"Line {} has error={}".format(sys.exc_traceback.tb_lineno, e))


####-------------------------------------------------------------------------####
	def checkincomingMACNo(self, data, pi, timeStampOfReceive):

		piU = unicode(pi)
		piMAC = ""
		piN   = -1
		try:

			if u"piMAC" in data:
				piMAC = unicode(data[u"piMAC"])
			if piMAC == "0" or piMAC == "": 
				return False, "", ""

			#if str(pi) =="9": self.indiLOG.log(20, u"receiving: pi "+piU+"  piMAC:" + piMAC)
			piN = int(data[u"pi"])
			piNU = unicode(piN)
			if piNU not in _rpiList :
				if self.decideMyLog(u"all"): self.indiLOG.log(10, u"bad data  Pi# not in range: {}".format(piNU))
				return	False, "", ""

			try:
				devPI = indigo.devices[self.RPI[piNU][u"piDevId"]]
				if u"ts" in data and devPI !="":
					self.compareRpiTime(data, piU, devPI, timeStampOfReceive)
			except: 
				pass

			if piU not in _rpiBeaconList:
				self.checkSensorPiSetup(piU, data, piNU)
				return True, piMAC, piNU

			if piMAC !="":
				beacon = self.RPI[piU][u"piMAC"]
				if piMAC != beacon:
					self.indiLOG.log(20, u"MAC# from RPI message, has new MAC# {} changing to new BLE-MAC number, old MAC#{}--  pi# {}".format(piMAC, beacon, piU) )
					beacon = piMAC
				if len(beacon) == 17: ## len(u"11:22:33:44:55:66")
						indigoId = int(self.RPI[piU][u"piDevId"])
						if len(self.RPI[piU][u"piMAC"]) != 17 or indigoId == 0:
							self.indiLOG.log(10, u"MAC# from RPI message is new {} not in internal list .. new RPI?{}".format(beacon, piU))

						else: # existing RPI with valid MAC # and indigo ID 
							if self.RPI[piU][u"piMAC"] != beacon and indigoId > 0:
								try:
									devPI = indigo.devices[indigoId]
									props= devPI.pluginProps
									props[u"address"] = beacon
									self.deviceStopCommIgnore = time.time()
									devPI.replacePluginPropsOnServer(props)
									if self.RPI[piU][u"piMAC"] in self.beacons:
										self.beacons[beacon]			 = copy.deepcopy(self.beacons[self.RPI[piU][u"piMAC"]] )
									else:
										self.beacons[beacon]			 = copy.deepcopy(_GlobalConst_emptyBeacon)

									self.beacons[piMAC][u"indigoId"] = indigoId
									self.RPI[piU][u"piMAC"] = beacon
									if self.decideMyLog(u"Logic"): self.indiLOG.log(10, u"MAC# from RPI  was updated")
								except Exception, e:
									self.indiLOG.log(40,"Line {} has error={}".format(sys.exc_traceback.tb_lineno, e))
									if self.decideMyLog(u"Logic"): self.indiLOG.log(10, u"MAC# from RPI...	 indigoId: {} does not exist, ignoring".format(indigoId) )

						# added to cover situation when RPI was set to expire by mistake ==>  reset it to ok
						if beacon in self.beacons: 
							if self.beacons[beacon][u"ignore"] > 0: self.beacons[beacon][u"ignore"] = 0
							self.beacons[beacon][u"lastUp"] = time.time()

		except Exception, e:
			self.indiLOG.log(40,"Line {} has error={}".format(sys.exc_traceback.tb_lineno, e))
			return False, "", ""

		return True, piMAC, piNU



####-------------------------------------------------------------------------####
	def compareRpiTime(self, data, pi, devPI, timeStampOfReceive):
		piU = unicode(pi)
		pi = int(pi)
		dt = time.time() - timeStampOfReceive
		if dt > 4.: self.indiLOG.log(10, u"significant internal delay occured digesting data from	 rPi:{}    {:.1f} [secs]".format(piU, dt) )
		try:
			if u"ts" not in data: return 
			tzMAC = time.tzname[1]
			if len(tzMAC) <3: tzMAC=time.tzname[0]
			if u"deltaTime" in data:
				self.RPI[piU][u"deltaTime1"] = data[u"deltaTime"]
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
			self.RPI[piU][u"deltaTime2"] = deltaT

			props = devPI.pluginProps
			if u"syncTimeWithMAC" in props and props[u"syncTimeWithMAC"] !="" and props[u"syncTimeWithMAC"] =="0": return 

			if tz!= tzMAC:
				if self.timeErrorCount[pi]	 < 2:
					self.indiLOG.log(20, u"rPi "+piU+u" wrong time zone: " + tz + u"    vs "+ tzMAC+u"    on MAC ")
					self.timeErrorCount[pi] +=1
					return

			if devPI !="":
					try:
						sT= float(props[u"syncTimeWithMAC"])
						if abs(time.time()-float(ts)) > sT and tz == tzMAC and self.timeErrorCount[pi] < 5:
							self.timeErrorCount[pi]  +=5
							alreadyUnderway = False
							for action in self.actionList:
								if u"action" in action and action[u"action"] == u"setTime" and action[u"value"] == piU:
									alreadyUnderway = True
									break
							if not alreadyUnderway:
								self.actionList.append({u"action":"setTime","value":piU})
								self.indiLOG.log(20, u"rPi "+piU+u" do a time sync MAC --> RPI, time off by: %5.1f"%(time.time()-ts)+u"[secs]"  )
					except: pass


			if tz != tzMAC or (abs(deltaT) > 100):
				# do not check time / time zone if disabled 
					self.timeErrorCount[pi] +=1
					if self.timeErrorCount[pi]	 < 3:
						try:	  deltaT = "{}".format(deltaT)
						except:	  deltaT = "{:.0f} - {}".format(time.time, ts)
						self.indiLOG.log(20, u"please do \"sudo raspi-config\" on rPi: {}, set time, reboot ...      send: TIME-Tsend= {}      /epoch seconds UTC/  timestamp send= {}; TZ send is={}".format(piU, deltaT, ts, tz) )

			if (abs(time.time()-float(ts)) < 2. and tz == tzMAC)  or self.timeErrorCount[pi] > 1000:
				self.timeErrorCount[pi] = 0

		except Exception, e:
			if unicode(e).find(u"timeout waiting") > -1:
				self.indiLOG.log(40,u"communication to indigo is interrupted")
			self.indiLOG.log(40,"Line {} has error={}".format(sys.exc_traceback.tb_lineno, e))
		return


####-------------------------------------------------------------------------####
	def printBLEreport(self, BLEreport):
		try:
			self.indiLOG.log(20, u"BLEreport received:")
			for rep in BLEreport:
					self.indiLOG.log(20, u"=======================================\n"+BLEreport[rep][0].strip(u"\n"),mType = rep)
					if len(BLEreport[rep][1]) < 5:
						self.indiLOG.log(20, u"no errors")
					else:
						self.indiLOG.log(20, u"errors:\n"+BLEreport[rep][1].strip(u"\n"),mType = rep)
		except Exception, e:
			self.indiLOG.log(40,"Line {} has error={}".format(sys.exc_traceback.tb_lineno, e))


####-------------------------------------------------------------------------####
	def checkI2c(self, piU, i2c):
		try:
			for i2cChannel in i2c:
				if i2cChannel is not None:
					if i2cChannel.find(u"i2c.ERROR:.no.such.file....redo..SSD?") > -1 :
						self.indiLOG.log(20, u" pi#"+piU+u"  has bad i2c config. you might need to replace SSD")
		except:
			pass


####-------------------------------------------------------------------------####
	def checkBlueTooth(self, piU, blueTooth):
		try:
			if blueTooth is not None:
				if blueTooth.find(u"startup.ERROR:...SSD.damaged?") > -1 :
					self.indiLOG.log(30,u" pi#"+piU+u" bluetooth did not startup. you might need to replace SSD")
		except:
			pass


####-------------------------------------------------------------------------####
	def updateAlive(self, varJson,varUnicode,  timeStampOfReceive):
		if u"pi" not in varJson : return 
		try:
			if self.decideMyLog(u"DevMgmt"):	 self.indiLOG.log(20,u"rPi alive message :  " + varUnicode)
			if (varUnicode).find(u"_dump_") >-1: 
				self.indiLOG.log(40, u"rPi error message: Please check that RPI  you might need to replace SD")
				self.indiLOG.log(40, varUnicode)
				return 
			if (varUnicode).find(u"data may be corrupt") >-1: 
				self.indiLOG.log(30, u"rPi error message: >>dosfsck has error: data may be corrupt<<<   Please check that RPI  you might need to replace SD")
				self.indiLOG.log(30, varUnicode)
				return 
			pi = int(varJson[u"pi"])
			piU = unicode(pi)
			if piU not in _rpiList:
				self.indiLOG.log(20, u"pi# out of range: " + varUnicode)
				return

			if self.trackRPImessages  == pi:
				self.indiLOG.log(20, u"pi# {} msg tracking: {} ".format(piU, varUnicode ))

			self.RPI[piU][u"lastMessage"] = time.time()

			if u"reboot" in varJson:
				self.setRPIonline(piU,new="reboot")
				indigo.variable.updateValue(self.ibeaconNameDefault+u"Rebooting","reset from :"+piU+" at "+datetime.datetime.now().strftime(_defaultDateStampFormat))
				if u"text" in varJson and varJson[u"text"].find(u"bluetooth_startup.ERROR:") >-1:
					self.indiLOG.log(20, u"RPI# "+piU+ " "+varJson[u"text"]+u" Please check that RPI ")
				return

			try:
				dev = indigo.devices[self.RPI[piU][u"piDevId"]]
			except Exception, e:

				if unicode(e).find(u"timeout waiting") > -1:
					self.indiLOG.log(40,"Line {} has error={}".format(sys.exc_traceback.tb_lineno, e))
					self.indiLOG.log(40,u"communication to indigo is interrupted")
					return
				if unicode(e).find(u"not found in database") ==-1:
					self.indiLOG.log(40,"Line {} has error={}".format(sys.exc_traceback.tb_lineno, e))
					return
				self.RPI[piU][u"piDevId"]=0
				return
			self.compareRpiTime(varJson,piU,dev, timeStampOfReceive)
			self.setRPIonline(piU)


			self.updateStateIf(piU, dev, varJson, u"sensors_active")
			self.updateStateIf(piU, dev, varJson, u"i2c_active")
			self.updateStateIf(piU, dev, varJson, u"rpi_type")
			self.updateStateIf(piU, dev, varJson, u"op_sys")
			self.updateStateIf(piU, dev, varJson, u"last_boot")
			self.updateStateIf(piU, dev, varJson, u"last_masterStart")
			self.updateStateIf(piU, dev, varJson, u"RPI_throttled")
			self.updateStateIf(piU, dev, varJson, u"temp", deviceStateName="Temperature")

			if "i2cError" in varJson:
				self.indiLOG.log(30,"RPi# {} has i2c error, not found in i2cdetect {}".format(piU,varJson["i2cError"]) )

			dev.updateStateImageOnServer(indigo.kStateImageSel.SensorOn)
			if dev.states[u"status"] != "up" :
				self.addToStatesUpdateDict(dev.id,u"status", u"up")

			if dev.states[u"online"] != "up":
				self.addToStatesUpdateDict(dev.id,u"online", u"up")

			if pi < _GlobalConst_numberOfiBeaconRPI:
				if self.RPI[piU][u"piMAC"] in self.beacons:
					self.beacons[self.RPI[piU][u"piMAC"]][u"lastUp"] = time.time()

			self.executeUpdateStatesDict(onlyDevID=dev.id, calledFrom="addToDataQueue pi_IN_Alive")

		except Exception, e:
			if unicode(e).find(u"timeout waiting") > -1:
				self.indiLOG.log(40,"Line {} has error={}".format(sys.exc_traceback.tb_lineno, e))
				self.indiLOG.log(40,u"communication to indigo is interrupted")
				return
			if len(unicode(e)) > 5 :
				self.indiLOG.log(40,"Line {} has error={}".format(sys.exc_traceback.tb_lineno, e))
				self.indiLOG.log(40,u"variable pi_IN_Alive wrong format: " + varUnicode+" you need to push new upgrade to rPi")

		return


####-------------------------------------------------------------------------####
	def updateStateIf(self, piU, dev, varJson, stateName, deviceStateName="",makeString=False ):

		try:
			if deviceStateName == "": deviceStateName = stateName
			if stateName in varJson:
				###self.indiLOG.log(20, u"updateStateIf : "+statename+"  "+ unicode(varJson[statename]))
				if deviceStateName =="Temperature": 
					x, UI, decimalPlaces, useFormat = self.convTemp(varJson[stateName])
				elif makeString:
					x  = varJson[stateName].strip("{").strip("}")
					UI = x
					decimalPlaces = 0
				else: 
					x, UI, decimalPlaces  =  varJson[stateName], varJson[stateName], 1

				if deviceStateName =="RPI_throttled": 
					old = dev.states[deviceStateName] 
					if old != x:
						if x != "none" and x != "" and x != "no_problem_detected":
							self.indiLOG.log(40,"RPi# {} has power state has problem   new:>>{}<<, previous:{}".format(piU, x, old) )
						if x == "none" or x == "no_problem_detected":
							self.indiLOG.log(40,"RPi# {} has power state has recovered  new:>>{}<<, previous:{}".format(piU, x, old) )

				self.setStatusCol( dev, deviceStateName, x, UI, "", "",{})
				return x
		except Exception, e:
				self.indiLOG.log(40,"Line {} has error={}".format(sys.exc_traceback.tb_lineno, e))
		return ""

####-------------------------------------------------------------------------####
	def setRPIonline(self, piU, new="up", setLastMessage=False):
		try:
			try:	devID = int(self.RPI[piU][u"piDevId"])
			except: devID = 0
			if devID ==0: return  # not setup yet 
			#self.indiLOG.log(20,u" into setting online status of pi:{}, setLastMessage:{}".format(piU, setLastMessage) )

			now = datetime.datetime.now().strftime(_defaultDateStampFormat)
			try: dev = indigo.devices[self.RPI[piU][u"piDevId"]]
			except:
				self.sleep(1)
				try: dev = indigo.devices[self.RPI[piU][u"piDevId"]]
				except:
					self.indiLOG.log(20,u"setRPIonline looks like device has been deleted..  setting pi:{}  indigo.devices[{}] returns error   marking for delete".format(devID,pi) )
					self.delRPI(pi=pi, calledFrom="setRPIonline")
					return 

			if setLastMessage:
				self.addToStatesUpdateDict(dev.id,u"last_MessageFromRpi", datetime.datetime.now().strftime(_defaultDateStampFormat))
		

			if new==u"up":
				#self.addToStatesUpdateDict(dev.id,u"lastMessage", now)
				dev.updateStateImageOnServer(indigo.kStateImageSel.SensorOn)
				if u"status" in dev.states and dev.states[u"status"] != "up":
					self.addToStatesUpdateDict(unicode(devID),u"status", u"up")
				if u"online" in dev.states and dev.states[u"online"] != "up":
					self.addToStatesUpdateDict(dev.id,u"online", u"up")
				return
			if new == u"reboot":
				#self.addToStatesUpdateDict(dev.id,u"lastMessage", now)
				if dev.states[u"online"] != "reboot":
					dev.updateStateImageOnServer(indigo.kStateImageSel.SensorOff)
					self.addToStatesUpdateDict(dev.id,u"online", u"reboot")
					self.setCurrentlyBooting(self.bootWaitTime, setBy=u"setting status of pi# "+piU+"   to reboot  or until new message arrives")
					if piU not in _rpiBeaconList: 
						self.addToStatesUpdateDict(dev.id,u"status", u"reboot")
					return
			if new == u"offline":
				if dev.states[u"online"] != "down":
					#dev.updateStateImageOnServer(indigo.kStateImageSel.SensorOff)
					self.addToStatesUpdateDict(dev.id,u"online", u"down")
					if piU in _rpiSensorList: 
						self.addToStatesUpdateDict(dev.id,u"status", u"down")
					return



		except Exception, e:
			if unicode(e).find(u"timeout waiting") > -1:
				self.indiLOG.log(40,"Line {} has error={}".format(sys.exc_traceback.tb_lineno, e))
				self.indiLOG.log(40,u"communication to indigo is interrupted")
				return
			if len(unicode(e)) > 5 :
				self.indiLOG.log(40,"Line {} has error={}".format(sys.exc_traceback.tb_lineno, e))
				self.indiLOG.log(40,u" pi" + piU+"  RPI"+ unicode(self.RPI[piU]) )
		return
####-------------------------------------------------------------------------####
	def checkSensorPiSetup(self, piSend, data, piNReceived):

		try:
			#self.indiLOG.log(20,	u"called checkSensorPiSetup")
			if piSend != piNReceived:
				self.indiLOG.log(20, u"sensor pi " + piSend + " wrong pi# "+piNReceived+" number please fix in setup rPi")
				return -1
			if u"ipAddress" in data:
				if self.RPI[piSend][u"ipNumberPi"] != data[u"ipAddress"]:
					self.indiLOG.log(20, u"sensor pi " + piSend + " wrong IP number please fix in setup rPi, received: -->" +data[u"ipAddress"]+"<-- if it is empty a rPi reboot might solve it")
					return -1
			devId = self.RPI[piSend][u"piDevId"]
			Found= False
			try:
				dev= indigo.devices[devId]
				Found =True
			except Exception, e:
			   
				self.indiLOG.log(40,"Line {} has error={}".format(sys.exc_traceback.tb_lineno, e))
				if unicode(e).find(u"timeout waiting") > -1:
					self.indiLOG.log(40, u"communication to indigo is interrupted")
					return -1

			if not Found:
				self.indiLOG.log(20, u"sensor pi " + piSend + "- devId: " + unicode(devId) +" not found, please configure the rPi:  "+ unicode(self.RPI[piSend]))
			if Found:
				if dev.states[u"status"] != "up":
						self.addToStatesUpdateDict(dev.id,u"status",u"up")
						dev.updateStateImageOnServer(indigo.kStateImageSel.SensorOn)
				if dev.states[u"online"] != "up":
						self.addToStatesUpdateDict(dev.id,u"online",u"up")
						dev.updateStateImageOnServer(indigo.kStateImageSel.SensorOn)

		except Exception, e:
			if len(unicode(e)) > 5 :
				self.indiLOG.log(40,"Line {} has error={}".format(sys.exc_traceback.tb_lineno, e))
				self.indiLOG.log(40,unicode(data))
		return 0



####-------------------------------------------------------------------------####
	## as we accumulate changes , dev.states does not contain the latest. check update list and if not there then check dev.states
	def getCurrentState(self, dev, devIds, state, fromMETHOD=""):
		try:
			if devIds in self.updateStatesDict and state in self.updateStatesDict[devIds]:
				return self.updateStatesDict[devIds][state]["value"] 
			else:  
				return dev.states[state] 

		except Exception, e1:
			try:  # rare case that updateStatesDict has been updated and clear whil we do this, then take new dev.state happens ~ 1/week with MANY devices
				self.indiLOG.log(10,"in Line {} has error(s) ={}, getCurrentState not in dyn list, trying to use indigo state... " .format(sys.exc_traceback.tb_lineno, e1))
				ret=  indigo.devices[dev.id].states[state] 
				self.indiLOG.log(10,"...  was fixed using indigo states")
				return ret
			except Exception, e:
				self.indiLOG.log(40,"in Line {} has error(s) ={} {}".format(sys.exc_traceback.tb_lineno, e, e1))
				self.indiLOG.log(40,u"  .. called from= {};  state= {};  updateStatesDict= {}".format(fromMETHOD, state, self.updateStatesDict) )
				try:	self.indiLOG.log(40, u"  .. dev= {}".format(dev.name.encode("utf8")) )
				except: self.indiLOG.log(40,u"  .. device does not exist, just deleted? .. IndigoId={}".format(devIds) )
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
	def calcPostion(self, dev, expirationTime): ## add Signal time dist status
		try:
			devID			= dev.id
			name			= dev.name
			devIds			= unicode(dev.id)
			deltaDistance	= 0.
			status			= "expired"
			distanceToRpi	 = []
			pitimeNearest	= "1900-00-00 00:00:00"
			lastUp			= 0
			lastUpS			= ""
			update			= False
			#if devID ==78067927: self.indiLOG.log(10, "dist  "+ dev.name)
			lastStatusChangeDT = 99999
			try:
				if u"lastUp" in dev.states: 
					lastUp =  self.getTimetimeFromDateString(self.getCurrentState(dev,devIds,"lastUp", fromMETHOD="calcPostion1"))

			except Exception, e:
				self.indiLOG.log(40,"Line {} has error={}".format(sys.exc_traceback.tb_lineno, e))
				lastUp	= 0

			if dev.deviceTypeId == "BLEconnect":
				activePis = self.getActiveBLERPI(dev)
			else:
				activePis = range(_GlobalConst_numberOfiBeaconRPI)

			for pi1 in activePis:
				pi1U = unicode(pi1)
				signal = self.getCurrentState(dev,devIds,"Pi_" + pi1U.rjust(2,"0") + "_Signal", fromMETHOD="calcPostion2")
				if signal == "": continue
				txPower = self.getCurrentState(dev,devIds,"TxPowerReceived")
				if txPower == "": txPower =-30

				piTimeS = self.getCurrentState(dev,devIds,"Pi_" + pi1U.rjust(2,"0") + "_Time", fromMETHOD="calcPostion3")
				if piTimeS is not None and len(piTimeS) < 5: continue

				if piTimeS > pitimeNearest:
					pitimeNearest = piTimeS

				piT2 = self.getTimetimeFromDateString(piTimeS) 
				if piT2 < 10: piT2 = time.time()
				try:
					dist = self.getCurrentState(dev,devIds,"Pi_" + pi1U.rjust(2,"0") + "_Distance", fromMETHOD="calcPostion4")
					dist = float(dist)
				except Exception, e:
					self.indiLOG.log(40,"Line {} has error={}".format(sys.exc_traceback.tb_lineno, e) )
					dist = 99999.

				piTimeUse = piT2
				if dist == 9999. and  lastUp != 0: 
					piTimeUse = lastUp

				if signal ==-999:
					if	 (time.time()- piTimeUse <   					 expirationTime) :	    
						status =  "up"
						#if dev.name.find("BLE-") >-1:	self.indiLOG.log(10,"setting status up  calcPostion sig  = -999  "  )
					elif (time.time()- piTimeUse < self.expTimeMultiplier*expirationTime)	and status != "up": 
						status = "down"
						#if dev.name.find("BLE-") >-1:	self.indiLOG.log(10,"setting status up  calcPostion sig  = -999  "  )
				else:
					if dist >= 99990. and txPower < -20:							 continue
					if dist == "" or (dist >= 99990. and signal > -50):				 continue # fake signals with bad TXpower 
					if dist > 50./max(self.distanceUnits,0.3) and signal > -50:		 continue # fake signals with bad TXpower 
					if time.time()- piTimeUse  < expirationTime:  
						status = "up"
					elif (time.time()- piTimeUse < self.expTimeMultiplier*expirationTime)	and status != "up": 
						status = "down"

					if time.time()- piTimeUse  < max(90.,expirationTime):								   # last signal not in expiration range anymore , use at least 90 secs.. for cars exp is 15 secs and it forgets the last signals too quickly
						distanceToRpi.append([dist , pi1])

			currStatus =  self.getCurrentState(dev,devIds,"status", fromMETHOD="calcPostion5") 
			if currStatus!= status :
				if "lastStatusChange" in dev.states: 
					try: lastStatusChangeDT  =  time.time() - self.getTimetimeFromDateString(dev.states[u"lastStatusChange"])
					except Exception, e:
							if len(unicode(e)) > 5 :
								self.indiLOG.log(40,"Line {} has error={}".format(sys.exc_traceback.tb_lineno, e))
				if lastStatusChangeDT > 3. :
					update=True
					self.addToStatesUpdateDict(dev.id,u"status", status)
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

				# calculate the direction vector 
				Npoints=0
				if len(distanceToRpi) > 1:
					for jj in range(1, 2): 
						piJJ = distanceToRpi[jj][1]
						if piJJ == clostetPi:							continue # no distance to itself 
						if self.piPosition[piJJ][0]	 <=0:				continue # not set should not be 0 
						if self.piToPiDistance[piJJ][clostetPi][3] ==0: continue # position of RPi are not set or all the same 

						dist =	distanceToClosestRpi 
						if distanceToRpi[jj][0] <  self.piToPiDistance[piJJ][clostetPi][3]:	 # take radius and use direction to next RPI only
							dist   +=  (distanceToClosestRpi /( 1 + 1.2*distanceToRpi[jj][0])) **2	*self.piToPiDistance[piJJ][clostetPi][3]

						xDir  = (self.piToPiDistance[piJJ][clostetPi][0])/self.piToPiDistance[piJJ][clostetPi][3]
						yDir  = (self.piToPiDistance[piJJ][clostetPi][1])/self.piToPiDistance[piJJ][clostetPi][3]
						newPos[0] += xDir * dist 
						newPos[1] += yDir * dist

				pos =[u"PosX","PosY","PosZ"]
				for ii in range(3):
					dd = abs(float(dev.states[pos[ii]]) - newPos[ii])
					if dd > 1./self.distanceUnits:	 # min delta = 1 meter
						self.addToStatesUpdateDict(devIds,pos[ii], newPos[ii],decimalPlaces=1)
						deltaDistance +=dd

		except Exception, e:
			self.indiLOG.log(40,"Line {} has error={}".format(sys.exc_traceback.tb_lineno, e))
		return update, deltaDistance



####-------------------------------------------------------------------------####
	def BLEconnectupdateAll(self, piU, sensors):
		pi = int(piU)
		for sensor in sensors:
			if sensor == "BLEconnect":
				self.messagesQueueBLE.put(( piU,sensors[sensor]))

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
				if ii > 0:	pass
				time.sleep(0.05)
			self.queueListBLE = "update"  
			updateFing = self.BLEconnectupdate(unicode(item[0]),item[1])
			if updateFing: self.updateFING(u"event")

		if len(self.sendBroadCastEventsList): self.sendBroadCastNOW()
		self.messagesQueueBLE.task_done()
		self.queueActiveBLE	 = False
		self.queueListBLE = ""
		return


####-------------------------------------------------------------------------####
	def BLEconnectupdate(self, piU, info):
		updateBLE = False
		try:
			for devId in info:
				if self.decideMyLog(u"BLE"): self.indiLOG.log(10, u"BLEconnect pi:{};  data:{} ".format(piU, info))
				try:
					dev = indigo.devices[int(devId)]
				except Exception, e:

					if unicode(e).find(u"timeout waiting") > -1:
						self.indiLOG.log(40,"Line {} has error={}".format(sys.exc_traceback.tb_lineno, e))
						self.indiLOG.log(40,u"BLEconnectupdate communication to indigo is interrupted")
						return
					self.indiLOG.log(20, u"BLEconnectupdate devId not defined in devices pi:{}; devId={}; info:{}".format( piU, devId, info))
					continue
				props = dev.pluginProps
				data={}
				for mac in info[devId]:
					if mac.upper() != props[u"macAddress"].upper() : continue
					data= info[devId][mac]
					break
				if data == {}:
					self.indiLOG.log(20, u"data empty for info[devid][mac];  pi:{}; devId={}; info:{} ".format( piU, devId, info) )
					continue

				if "rssi" not in data:
					self.indiLOG.log(10, "BLEconnectupdate ignoring msg; rssi missing; PI= {}; mac:{};  data:{}".format(piU, mac, data))
					return updateBLE
				rssi	  = float(data[u"rssi"])
				txPowerR  = float(data[u"txPower"])
				if self.decideMyLog(u"BLE"): self.indiLOG.log(10, "BLEconnectupdate PI= {}; mac:{}  rssi:{}  txPowerR:{} TxPowerSet:{}".format(piU, mac, rssi, txPowerR, props[u"beaconTxPower"]))

				txSet = 999
				try: txSet = int(props[u"beaconTxPower"]) 
				except: pass
				if txSet != 999: 
					txPower = float(txSet)
				else:
					txPower = txPowerR
	
				expirationTime = int(props[u"expirationTime"])

				if dev.states[u"created"] == u"":
					self.addToStatesUpdateDict(dev.id,"created", datetime.datetime.now().strftime(_defaultDateStampFormat))

				if rssi > -160 and unicode(dev.states[u"Pi_"+piU.rjust(2,"0")+"_Signal"]) != unicode(rssi):
					self.addToStatesUpdateDict(dev.id, u"Pi_"+piU.rjust(2,"0")+"_Signal",int(rssi) )
				if txPowerR !=-999 and	unicode(dev.states[u"TxPowerReceived"]) != unicode(txPowerR):
					self.addToStatesUpdateDict(dev.id, u"TxPowerReceived",txPowerR  )

				if rssi < -160: upD = "down"
				else:			upD = "up"

				if upD==u"up":
					dist=	 round( self.calcDist(txPower,  rssi) / self.distanceUnits, 1)
					if self.decideMyLog(u"BLE"): self.indiLOG.log(10, u"rssi txP dist dist-Corrected.. rssi:{} txPower:{}  dist:{}  rssiCaped:{}".format(rssi, txPower, dist, min(txPower,rssi)))
					self.addToStatesUpdateDict(dev.id,u"Pi_"+piU.rjust(2,"0")+"_Time",	datetime.datetime.now().strftime(_defaultDateStampFormat)  )
					self.addToStatesUpdateDict(dev.id,"lastUp",datetime.datetime.now().strftime(_defaultDateStampFormat))
					if abs(dev.states[u"Pi_"+piU.rjust(2,"0")+"_Distance"] - dist) > 0.5 and abs(dev.states[u"Pi_"+piU.rjust(2,"0")+"_Distance"] - dist)/max(0.5,dist) > 0.05:
						self.addToStatesUpdateDict(dev.id,u"Pi_" + piU.rjust(2,"0")  + "_Distance", dist,decimalPlaces=1)
				else:
					dist=99999.
					if dev.states[u"status"] == "up":
						if self.decideMyLog(u"BLE"): self.indiLOG.log(10, u"NOT UPDATING::::  updating time  status was up, is down now dist = 99999 for MAC: {}".format(mac) )
						#self.addToStatesUpdateDict(dev.id,u"Pi_"+piU.rjust(2,"0")+"_Time",	datetime.datetime.now().strftime(_defaultDateStampFormat))
				#self.executeUpdateStatesDict()
				update, deltaDistance = self.calcPostion(dev,expirationTime)
				updateBLE = update or updateBLE

				if rssi > -160: 
					newClosestRPI = self.findClosestRPIForBLEConnect(dev, piU, dist)
					if newClosestRPI != dev.states["closestRPI"]:
						#indigo.server.log(dev.name+", newClosestRPI: "+unicode(newClosestRPI)) 
						if newClosestRPI == -1:
							self.addToStatesUpdateDict(dev.id,u"closestRPI", -1)
							if self.setClostestRPItextToBlank: self.addToStatesUpdateDict(dev.id,u"closestRPIText", "")
						else:
							#indigo.server.log(dev.name+", uodateing  newClosestRPI: "+unicode(newClosestRPI)+ " getRPIdevName:  "+self.getRPIdevName(newClosestRPI) ) 
							if unicode(dev.states[u"closestRPI"]) !="-1":
								self.addToStatesUpdateDict(dev.id,u"closestRPILast", dev.states["closestRPI"])
								self.addToStatesUpdateDict(dev.id,u"closestRPITextLast", dev.states["closestRPIText"])
							self.addToStatesUpdateDict(dev.id,"closestRPI", newClosestRPI)
							self.addToStatesUpdateDict(dev.id,"closestRPIText", self.getRPIdevName((newClosestRPI)))

				self.executeUpdateStatesDict(onlyDevID=dev.id,calledFrom="BLEconnectupdate end")	
 
		except Exception, e:
			if len(unicode(e)) > 5 :
				self.indiLOG.log(40,"Line {} has error={}".format(sys.exc_traceback.tb_lineno, e))
				if unicode(e).find(u"timeout waiting") > -1:
					self.indiLOG.log(40,u"communication to indigo is interrupted")

		return updateBLE


####-------------------------------------------------------------------------####
	def updateOutput(self, piU, outputs):
		data=""
		dateString = datetime.datetime.now().strftime(_defaultDateStampFormat)
		try:

			for output in outputs:
				if output.find("OUTPUTgpio") == -1 and output.find("OUTPUTi2cRelay") == -1: continue

				devUpdate = {}
				for devIds in outputs[output]:
					devUpdate[devIds] = True
					try:
						try:	devId = int(devIds)
						except: devId = 0
						if devId == 0: continue
						dev = indigo.devices[devId]
						props = dev.pluginProps
						#self.indiLOG.log(40,u"piu:{};  dev:{};  props:{}".format(piU, dev.name, props))
					except Exception, e:

						if unicode(e).find(u"timeout waiting") > -1:
							self.indiLOG.log(40,"Line {} has error={}".format(sys.exc_traceback.tb_lineno, e))
							self.indiLOG.log(40,u"communication to indigo is interrupted")
							return
						if unicode(e).find(u"not found in database") ==-1:
							self.indiLOG.log(40,"Line {} has error={}".format(sys.exc_traceback.tb_lineno, e))
							return

						self.indiLOG.log(40,u"bad devId send from pi:"+ piU+ u"devId: "+devIds+u" deleted?")
						continue

					if not dev.enabled:
						self.indiLOG.log(20, u"dev not enabled send from pi:{} dev: {}".format(piU, dev.name.encode("utf8")) )
						continue

					data = outputs[output][devIds]
					uData = unicode(data)
					if u"badSensor" in uData:
						self.addToStatesUpdateDict(dev.id,u"status",u"bad Output data, disconnected?")
						try: dev.updateStateImageOnServer(indigo.kStateImageSel.PowerOff)
						except: pass
						continue

					if u"displayS" in props:
						whichKeysToDisplay = props[u"displayS"]
					else:
						whichKeysToDisplay = ""

					if output.find("OUTPUTgpio-1") > -1 or output.find("OUTPUTi2cRelay") > -1:
						if self.decideMyLog(u"SensorData"): self.indiLOG.log(10, "{} received {}".format(output, Data) )
						self.OUTPUTgpio1(dev, props, data)
						continue


				for devIds in devUpdate:
					if devIds in self.updateStatesDict:
						if self.decideMyLog(u"SensorData"): self.indiLOG.log(10, u"pi# {}  {}  {}".format(piU, devIds, self.updateStatesDict) )
						self.executeUpdateStatesDict(onlyDevID=devIds,calledFrom="updateOutput end")

		except Exception, e:
			if len(unicode(e)) > 5 :
				self.indiLOG.log(40,"Line {} has error={}".format(sys.exc_traceback.tb_lineno, e))
				if unicode(e).find(u"timeout waiting") > -1:
					self.indiLOG.log(40, u"updateOutput communication to indigo is interrupted")


####-------------------------------------------------------------------------####
	def OUTPUTgpio1(self, dev, props, data):
		try:
			if "actualGpioValue" in data and "outputType" in props:
				actualGpioValue = unicode(data["actualGpioValue"]).lower()

				self.addToStatesUpdateDict(dev.id,u"actualGpioValue", data["actualGpioValue"])
				if props[u"outType"] == "0": # not inverse
					if actualGpioValue =="high" :upState = "on"
					else:               		 upState = "off"
				else:
					if actualGpioValue =="low"  :upState = "on"
					else:               		 upState = "off"

				self.addToStatesUpdateDict(dev.id,u"status", upState)
				self.addToStatesUpdateDict(dev.id,"onOffState", upState=="on")

		except Exception, e:
			self.indiLOG.log(40,"Line {} has error={}".format(sys.exc_traceback.tb_lineno, e))
			self.indiLOG.log(40,unicode(data))
		return



####-------------------------------------------------------------------------####
	def updateSensors(self, pi, sensors):
		data=""
		dateString = datetime.datetime.now().strftime(_defaultDateStampFormat)
		piU = unicode(pi)
		try:
			if self.decideMyLog(u"SensorData"): self.indiLOG.log(10, u"sensor input  pi: {}; data {}" .format(piU, sensors))
			# data[u"sensors"][sensor][u"temp,hum,press,INPUT"]

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
						dev= indigo.devices[devId]
						props= dev.pluginProps
					except Exception, e:

						if unicode(e).find(u"timeout waiting") > -1:
							self.indiLOG.log(40,"Line {} has error={}".format(sys.exc_traceback.tb_lineno, e))
							self.indiLOG.log(40,u"communication to indigo is interrupted")
							return
						if unicode(e).find(u"not found in database") ==-1:
							self.indiLOG.log(40,"Line {} has error={}".format(sys.exc_traceback.tb_lineno, e))
							return

						self.indiLOG.log(20, u"bad devId send from pi:"+ piU+ u"devId: "+devIds+u" deleted?")
						continue

					if not dev.enabled:
						if self.decideMyLog(u"UpdateRPI"): self.indiLOG.log(10, u"dev not enabled send from pi:{} dev: {}".format(piU, dev.name.encode("utf8")) )
						continue

					self.saveSensorMessages(devId=devIds, item=u"lastMessage", value=time.time())


					data = sensors[sensor][devIds]
					uData = unicode(data)
					if sensor=="mysensors":
						self.indiLOG.log(20, sensor+" received "+ uData)

					if u"calibrating" in uData:
						self.addToStatesUpdateDict(dev.id,u"status",u"Sensor calibrating")
						try: dev.updateStateImageOnServer(indigo.kStateImageSel.SensorOff)
						except: pass

					if u"badSensor" in uData:
						self.addToStatesUpdateDict(dev.id,u"status",u"bad Sensor data, disconnected?")
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



					if dev.deviceTypeId == "as726x":
						if "green" in data:
							data["illuminance"] = float(data["green"])*6.83
						self.updateRGB(dev, data, whichKeysToDisplay, dispType=4)
						if u"temp" in data:
							x, UI, decimalPlaces, useFormat  = self.convTemp(data["temp"])
							self.addToStatesUpdateDict(dev.id,u"temperature", x, decimalPlaces=decimalPlaces)
							updateProps0, doUpdate = self.updateChangedValues(dev, x, props, "Temperature", useFormat, whichKeysToDisplay, decimalPlaces)
							if updateProps: 
								props[doUpdate[0]] = doUpdate[1]
								self.deviceStopCommIgnore = time.time()
								dev.replacePluginPropsOnServer(props)

						if u"LEDcurrent" in data:
							self.addToStatesUpdateDict(dev.id,u"LEDcurrent", data["LEDcurrent"], decimalPlaces=1)
						continue

					if sensor == u"MAX44009" :
						self.updateLight(dev, data, whichKeysToDisplay)
						continue

					if sensor == u"i2cVEML6070" :
						self.updateLight(dev, data, whichKeysToDisplay)
						continue

					if sensor == u"i2cVEML6075" :
						self.updateLight(dev, data, whichKeysToDisplay)
						continue

					if sensor == u"i2cVEML6040" :
						self.updateLight(dev, data, whichKeysToDisplay,theType=sensor)
						continue

					if sensor == u"i2cVEML7700" :
						self.updateLight(dev, data, whichKeysToDisplay,theType=sensor)
						continue

					if sensor == u"i2cVEML6030" :
						self.updateLight(dev, data, whichKeysToDisplay)
						continue

					if sensor == u"i2cTSL2561" :
						self.updateLight(dev, data, whichKeysToDisplay)
						continue

					if sensor == u"i2cIS1145" :
						self.updateLight(dev, data, whichKeysToDisplay)
						continue

					if sensor == u"i2cOPT3001" :
						self.updateLight(dev, data, whichKeysToDisplay, theType=sensor)
						continue

					if sensor == u"ultrasoundDistance" :
						self.updateDistance(dev, data, whichKeysToDisplay)
						continue

					if sensor == u"vl503l0xDistance" :
						self.updateDistance(dev, data, whichKeysToDisplay)
						continue

					if sensor == u"vl6180xDistance" :
						self.updateDistance(dev, data, whichKeysToDisplay)
						self.updateLight(dev, data, whichKeysToDisplay)
						continue

					if sensor == u"vcnl4010Distance" :
						self.updateDistance(dev, data, whichKeysToDisplay)
						self.updateLight(dev, data, whichKeysToDisplay)
						continue

					if sensor == u"apds9960" :
						self.updateapds9960(dev, data)
						continue

					if sensor.find(u"INPUTgpio-") >-1:
						self.updateINPUT(dev, data, whichKeysToDisplay, int(sensor.split("INPUTgpio-")[1]), sensor)
						continue

					if sensor.find(u"INPUTtouch-") >-1:
						self.updateINPUT(dev, data, whichKeysToDisplay, int(sensor.split("INPUTtouch-")[1]), sensor)
						continue

					if sensor.find(u"INPUTtouch12-") >-1:
						self.updateINPUT(dev, data, whichKeysToDisplay, int(sensor.split("INPUTtouch12-")[1]), sensor)
						continue

					if sensor.find(u"INPUTtouch16-") >-1:
						self.updateINPUT(dev, data, whichKeysToDisplay, int(sensor.split("INPUTtouch16-")[1]), sensor)
						continue

					if sensor == u"spiMCP3008" :
						self.updateINPUT(dev, data, whichKeysToDisplay,	 8, sensor)
						continue

					if sensor == u"spiMCP3008-1" :
						self.updateINPUT(dev, data, u"INPUT_0",	 1, sensor)
						continue

					if sensor == u"PCF8591" :
						self.updateINPUT(dev, data, whichKeysToDisplay, 0, sensor)
						continue

					if sensor == u"ADS1x15" :
						self.updateINPUT(dev, data, whichKeysToDisplay, 0, sensor)
						continue

					if sensor == u"INPUTRotarySwitchAbsolute":
						self.updateINPUT(dev, data, whichKeysToDisplay, 1, sensor)
						continue

					if sensor == u"INPUTRotarySwitchIncremental":
						self.updateINPUT(dev, data, whichKeysToDisplay, 1, sensor)
						continue

					if sensor == u"mysensors" :
						self.indiLOG.log(20, sensor+"  into input")
						self.updateINPUT(dev, data, whichKeysToDisplay, 10, sensor)
						continue

					if sensor == u"myprogram" :
						self.updateINPUT(dev, data, whichKeysToDisplay, 10, sensor)
						continue

					if dev.deviceTypeId == "Wire18B20":
						self.updateOneWire(dev,data,whichKeysToDisplay,piU)
						continue

					if dev.deviceTypeId == "BLEsensor":
						self.updateBLEsensor(dev,data,props,whichKeysToDisplay)
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

					if dev.deviceTypeId == "l3g4200":
						self.updateGYROS(dev,data,whichKeysToDisplay)
						continue

					if dev.deviceTypeId == "bno055":
						self.updateGYROS(dev,data,whichKeysToDisplay)
						continue

					if dev.deviceTypeId == "mag3110":
						self.updateGYROS(dev,data,whichKeysToDisplay)
						continue

					if dev.deviceTypeId == "hmc5883L":
						self.updateGYROS(dev,data,whichKeysToDisplay)
						continue

					if dev.deviceTypeId == "mpu6050":
						self.updateGYROS(dev,data,whichKeysToDisplay)
						continue

					if dev.deviceTypeId == "mpu9255":
						self.updateGYROS(dev,data,whichKeysToDisplay)
						continue

					if dev.deviceTypeId == "lsm303":
						self.updateGYROS(dev,data,whichKeysToDisplay)
						continue

					if dev.deviceTypeId in ["INPUTpulse","INPUTcoincidence"]:
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
						self.addToStatesUpdateDict(dev.id, "status", st)
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
							x, UI  = int(float(data[u"CO2"])),  u"CO2 %d[ppm] "%(float(data[u"CO2"]))
							newStatus = self.setStatusCol( dev, u"CO2", x, UI, whichKeysToDisplay, indigo.kStateImageSel.TemperatureSensorOn,newStatus, decimalPlaces = 1)
							updateProps0, doUpdate =  self.updateChangedValues(dev, x, props, "CO2", "{:d}%", whichKeysToDisplay, 0)
							if updateProps0: props[doUpdate[0]] = doUpdate[1]; updateProps = updateProps or updateProps0
							x, UI  = int(float(data[u"VOC"])),  u"VOC %d[ppb]"%(float(data[u"VOC"]))
							newStatus = self.setStatusCol( dev, u"VOC", x, UI, whichKeysToDisplay, indigo.kStateImageSel.TemperatureSensorOn,newStatus, decimalPlaces = 1)
							updateProps0, doUpdate = self.updateChangedValues(dev, x, props, "VOC", "{:d}%", whichKeysToDisplay, 0)
							if updateProps0: props[doUpdate[0]] = doUpdate[1]; updateProps = updateProps or updateProps0

						except Exception, e:
							self.indiLOG.log(40,"Line {} has error={}".format(sys.exc_traceback.tb_lineno, e))
							self.indiLOG.log(20, unicode(props))


					if sensor == "as3935":
						try:
							if data[u"eventType"]  == "no Action yet":
								self.addToStatesUpdateDict(dev.id,"eventType", "no Data")
							elif data[u"eventType"]	 == "no lightning today":
								self.addToStatesUpdateDict(dev.id,"eventType", "no lightning today")
							elif data[u"eventType"]	 == "measurement":
								self.addToStatesUpdateDict(dev.id,"eventType", "measurement") 
								if data[u"lightning"]  == "lightning detected":
									x, UI  = int(float(data[u"distance"])),	  "Distance %d[km] "%(float(data[u"distance"]))
									newStatus = self.setStatusCol( dev, u"distance", x, UI, whichKeysToDisplay, indigo.kStateImageSel.TemperatureSensorOn,newStatus, decimalPlaces = 0)
									self.addToStatesUpdateDict(dev.id,"energy", float(data[u"energy"])) 
									newStatus = self.setStatusCol( dev, u"lightning", data[u"lightning"], "lightning "+datetime.datetime.now().strftime("%m-%d %H:%M:%S"), whichKeysToDisplay, indigo.kStateImageSel.TemperatureSensorOn,newStatus)
									self.addToStatesUpdateDict(dev.id,"lastLightning", datetime.datetime.now().strftime(_defaultDateStampFormat)) 
									rightNow = time.time()
									nDevs = 1
									#indigo.server.log("  checking devL for "+ dev.name )
									for devL in indigo.devices.iter("props.isLightningDevice"):
										if devL.id == dev.id: continue
										deltaTime = time.time() - self.getTimetimeFromDateString( devL.states["lastLightning"])
										if deltaTime < self.lightningTimeWindow : 
											nDevs += 1
										#indigo.server.log(" deltaTime: "+ unicode(deltaTime))
									if nDevs >= self.lightningNumerOfSensors:
										indigo.variable.updateValue("lightningEventDevices",unicode(nDevs))
										time.sleep(0.01) # make shure the # of devs gets updated first
										indigo.variable.updateValue("lightningEventDate",datetime.datetime.now().strftime(_defaultDateStampFormat))

								elif data[u"lightning"].find("Noise") == 0: 
									self.addToStatesUpdateDict(dev.id,"lightning", "calibrating,- sensitivity ")
								elif data[u"lightning"].find("Disturber") == 0: 
									self.addToStatesUpdateDict(dev.id,"lightning", "calibrating,- Disturber event ")
						except Exception, e:
							self.indiLOG.log(40,"Line {} has error={}".format(sys.exc_traceback.tb_lineno, e))
							self.indiLOG.log(40,unicode(props) +"\n"+ unicode(data))
						continue


					if sensor in["mhzCO2"]:
						try:
							x, UI  = int(float(data[u"CO2"])),  u"CO2 %d[ppm] "%(float(data[u"CO2"]))
							newStatus   = self.setStatusCol( dev, u"CO2", x, UI, whichKeysToDisplay, indigo.kStateImageSel.TemperatureSensorOn,newStatus, decimalPlaces = 1)
							updateProps0, doUpdate = self.updateChangedValues(dev, x, props, "CO2", "{:d}%", whichKeysToDisplay, 0)
							if updateProps0: props[doUpdate[0]] = doUpdate[1]; updateProps = updateProps or updateProps0

							if abs( float(dev.states["CO2offset"]) - float(data[u"CO2offset"])	) > 1: 
								self.setONErPiV(piU,"piUpToDate", [u"updateParamsFTP"])
							self.addToStatesUpdateDict(dev.id,"calibration", data[u"calibration"]) 
							self.addToStatesUpdateDict(dev.id,"raw", float(data[u"raw"]),	decimalPlaces = 1) 
							self.addToStatesUpdateDict(dev.id,"CO2offset", float(data[u"CO2offset"]),	decimalPlaces = 1) 
						except Exception, e:
							self.indiLOG.log(40,"Line {} has error={}".format(sys.exc_traceback.tb_lineno, e))
							self.indiLOG.log(40, unicode(props))


					if u"hum" in data:
						hum= data[u"hum"]
						x, UI, decimalPlaces  = self.convHum(hum)
						newStatus = self.setStatusCol( dev, u"Humidity", x, UI, whichKeysToDisplay, indigo.kStateImageSel.HumiditySensor,newStatus, decimalPlaces = decimalPlaces )
						updateProps0, doUpdate = self.updateChangedValues(dev, x, props, "Humidity", "{:d}%", whichKeysToDisplay, decimalPlaces)
						if updateProps0: props[doUpdate[0]] = doUpdate[1]; updateProps = updateProps or updateProps0


					if u"temp" in data:
						temp = data[u"temp"]
						x, UI, decimalPlaces, useFormat = self.convTemp(temp)
						newStatus = self.setStatusCol( dev, u"Temperature", x, UI, whichKeysToDisplay, indigo.kStateImageSel.TemperatureSensorOn,newStatus, decimalPlaces = decimalPlaces )
						updateProps0, doUpdate = self.updateChangedValues(dev, x, props, "Temperature", useFormat, whichKeysToDisplay, decimalPlaces)
						if updateProps0: props[doUpdate[0]] = doUpdate[1]; updateProps = updateProps or updateProps0

					if u"AmbientTemperature" in data:
						temp = data[u"AmbientTemperature"]
						x, UI, decimalPlaces, useFormat  = self.convTemp(temp)
						newStatus = self.setStatusCol( dev, u"AmbientTemperature", x, UI, whichKeysToDisplay, indigo.kStateImageSel.TemperatureSensorOn,newStatus, decimalPlaces = decimalPlaces)


					if u"press" in data:
						newStatus, updateProps0, doUpdate = self.setPressureDisplay(dev, props, data, whichKeysToDisplay,newStatus)
						if updateProps0: props[doUpdate[0]] = doUpdate[1]; updateProps = updateProps or updateProps0


					if u"moisture" in data:
						newStatus, updateProps0, doUpdate = self.setMoistureDisplay(dev, props, data, whichKeysToDisplay,newStatus)
						self.updateLight(dev, data, whichKeysToDisplay)
						if updateProps0: props[doUpdate[0]] = doUpdate[1]; updateProps = updateProps or updateProps0

					if u"Vertical" in data:
						try:
							x, UI  = float(data[u"Vertical"]),  "%7.3f"%(float(data[u"Vertical"]))
							newStatus = self.setStatusCol( dev, u"VerticalMovement", x, UI, whichKeysToDisplay, indigo.kStateImageSel.TemperatureSensorOn,newStatus, decimalPlaces = 3)
						except: pass

					if u"Horizontal" in data:
						try:
							x, UI  = float(data[u"Horizontal"]),   "%7.3f"%(float(data[u"Horizontal"]))
							newStatus = self.setStatusCol( dev, u"HorizontalMovement", x, UI, whichKeysToDisplay, indigo.kStateImageSel.TemperatureSensorOn,newStatus, decimalPlaces = 3)
						except: pass

					if u"MinimumPixel" in data:
						x, UI, decimalPlaces, useFormat  = self.convTemp(data[u"MinimumPixel"])
						newStatus = self.setStatusCol( dev, u"MinimumPixel", x, UI, whichKeysToDisplay, indigo.kStateImageSel.TemperatureSensorOn,newStatus, decimalPlaces = decimalPlaces)

					if u"MaximumPixel" in data:
						x, UI, decimalPlaces, useFormat  = self.convTemp(data[u"MaximumPixel"])
						newStatus = self.setStatusCol( dev, u"MaximumPixel", x, UI, whichKeysToDisplay, indigo.kStateImageSel.TemperatureSensorOn,newStatus, decimalPlaces = decimalPlaces)

					if u"GasResistance" in data:
						gr,grUI, aq, aqUI, gb, gbUI, SensorStatus, AirQualityText = self.convGas(data, dev, props)
						newStatus = self.setStatusCol( dev, u"GasResistance",	gr, grUI, whichKeysToDisplay, indigo.kStateImageSel.TemperatureSensorOn,newStatus, decimalPlaces = 0)
						newStatus = self.setStatusCol( dev, u"AirQuality",		aq, aqUI, whichKeysToDisplay, indigo.kStateImageSel.TemperatureSensorOn,newStatus, decimalPlaces = 0)
						newStatus = self.setStatusCol( dev, u"GasBaseline",		gb, gbUI, whichKeysToDisplay, indigo.kStateImageSel.TemperatureSensorOn,newStatus, decimalPlaces = 0)
						newStatus = self.setStatusCol( dev, u"SensorStatus",	SensorStatus, SensorStatus, whichKeysToDisplay, indigo.kStateImageSel.TemperatureSensorOn,newStatus, decimalPlaces = 0)
						newStatus = self.setStatusCol( dev, u"AirQualityText",	AirQualityText, AirQualityText, whichKeysToDisplay, indigo.kStateImageSel.TemperatureSensorOn,newStatus, decimalPlaces = 0)
						updateProps0, doUpdate = self.updateChangedValues(dev, aq, props, "AirQuality", "{:d}%", whichKeysToDisplay, 0)
						if updateProps0: props[doUpdate[0]] = doUpdate[1]; updateProps = updateProps or updateProps0

					if u"MovementAbs" in data:
						try:
							x, UI  = float(data[u"MovementAbs"]), "%5.2f"%(float(data[u"MovementAbs"]))
							newStatus = self.setStatusCol( dev, u"MovementAbs", x, UI, whichKeysToDisplay, indigo.kStateImageSel.TemperatureSensorOn,newStatus, decimalPlaces = 2)
						except: pass

					if u"Movement" in data:
						try:
							x, UI  = float(data[u"Movement"]), "%5.2f"%(float(data[u"Movement"]))
							newStatus = self.setStatusCol( dev, u"Movement", x, UI, whichKeysToDisplay, indigo.kStateImageSel.TemperatureSensorOn,newStatus, decimalPlaces = 2)
						except: pass

					if u"Uniformity" in data:
						try:
							x, UI  = float(data[u"Uniformity"]), "%5.1f"%(float(data[u"Uniformity"]))
							newStatus = self.setStatusCol( dev, u"Uniformity", x, UI, whichKeysToDisplay, indigo.kStateImageSel.TemperatureSensorOn,newStatus, decimalPlaces = 1)
						except: pass

					if sensor == u"amg88xx" and u"rawData" in data :
						try:
							if ("imageFilesaveRawData" in props and props[u"imageFilesaveRawData"] =="1") or ("imageFileNumberOfDots" in props and props[u"imageFileNumberOfDots"] !="-"):
								# exapnd to 8x8 matrix, data is in 4 byte packages *100
								pixPerRow = 8
								dataRaw = json.loads(data[u"rawData"])
								dataRaw = json.dumps([[dataRaw[kkkx] for kkkx in range(pixPerRow*(iiix), pixPerRow*(iiix+1))] for iiix in range(pixPerRow)])

								if "imageFilesaveRawData" in props and props[u"imageFilesaveRawData"] =="1":
										newStatus = self.setStatusCol( dev, u"rawData", dataRaw,"", whichKeysToDisplay, indigo.kStateImageSel.TemperatureSensorOn,newStatus, decimalPlaces = "")
								if "imageFileNumberOfDots" in props and props[u"imageFileNumberOfDots"] !="-":
									if "imageFileName" in props and len(props[u"imageFileName"])>1:
										imageParams	  = json.dumps( {"logFile":self.PluginLogFile, "logLevel":props[u"imageFilelogLevel"],"compress":props[u"imageFileCompress"],"fileName":self.cameraImagesDir+props[u"imageFileName"],"numberOfDots":props[u"imageFileNumberOfDots"],"dynamic":props[u"imageFileDynamic"],"colorBar":props[u"imageFileColorBar"]} )
										cmd = self.pythonPath + u" '" + self.pathToPlugin + u"makeCameraPlot.py' '" +imageParams+"' '"+dataRaw+"' & "  
										if props[u"imageFilelogLevel"] == "1": self.indiLOG.log(20,"AMG88 command:{}".format(cmd))
										subprocess.call(cmd, shell=True)
						except Exception, e:
							self.indiLOG.log(40,"Line {} has error={}".format(sys.exc_traceback.tb_lineno, e))
							self.indiLOG.log(40,unicode(props))
							self.indiLOG.log(40,unicode(len(data[u"rawData"]))+"     "+data[u"rawData"])

					if sensor == u"mlx90640" and u"rawData" in data :
						try:
							if ("imageFilesaveRawData" in props and props[u"imageFilesaveRawData"] =="1") or ("imageFileNumberOfDots" in props and props[u"imageFileNumberOfDots"] !="-"):
								# exapnd to 8x8 matrix, data is in 4 byte packages *100
								dataRaw = data[u"rawData"]

								if "imageFilesaveRawData" in props and props[u"imageFilesaveRawData"] =="1" and False:
										newStatus = self.setStatusCol( dev, u"rawData", dataRaw,"", whichKeysToDisplay, indigo.kStateImageSel.TemperatureSensorOn,newStatus, decimalPlaces = "")
								if "imageFileNumberOfDots" in props and props[u"imageFileNumberOfDots"] !="-":
									if "imageFileName" in props and len(props[u"imageFileName"])>1:
										imageParams	  = json.dumps( {"logFile":self.PluginLogFile, "logLevel":props[u"imageFilelogLevel"],"compress":props[u"imageFileCompress"],"fileName":self.cameraImagesDir+props[u"imageFileName"],"numberOfDots":props[u"imageFileNumberOfDots"],"dynamic":props[u"imageFileDynamic"],"colorBar":props[u"imageFileColorBar"]} )
										cmd = self.pythonPath + u" '" + self.pathToPlugin + u"makeCameraPlot.py' '" +imageParams+"' '"+dataRaw+"' & "  
										if props[u"imageFilelogLevel"] == "1": self.indiLOG.log(20,"mlx90640 command:{}".format(cmd))
										subprocess.call(cmd, shell=True)
						except Exception, e:
							self.indiLOG.log(40,"Line {} has error={}".format(sys.exc_traceback.tb_lineno, e))
							self.indiLOG.log(40,unicode(props))
							self.indiLOG.log(40,unicode(len(data[u"rawData"]))+"     "+data[u"rawData"])


					if sensor == u"lidar360" :
						try:
								xx = data["triggerValues"]
								newStatus = self.setStatusCol( dev, u"Leaving_count", 					xx["current"]["GT"]["totalCount"],		"leaving Count:{}".format(xx["current"]["GT"]["totalCount"]),			whichKeysToDisplay, indigo.kStateImageSel.TemperatureSensorOn,newStatus, decimalPlaces = 0)
								newStatus = self.setStatusCol( dev, u"Approaching_count", 				xx["current"]["LT"]["totalCount"],		"approaching Count:{}".format(xx["current"]["LT"]["totalCount"]),		whichKeysToDisplay, indigo.kStateImageSel.TemperatureSensorOn,newStatus, decimalPlaces = 0)
								newStatus = self.setStatusCol( dev, u"Re-Calibration_needed_count",		xx["calibrated"]["GT"]["totalCount"],	"calibration Count:{}".format(xx["calibrated"]["GT"]["totalCount"]), 	whichKeysToDisplay, indigo.kStateImageSel.TemperatureSensorOn,newStatus, decimalPlaces = 0)
								newStatus = self.setStatusCol( dev, u"Room_occupied_count", 			xx["calibrated"]["LT"]["totalCount"],	"occupied Count:{}".format(xx["calibrated"]["LT"]["totalCount"]),		whichKeysToDisplay, indigo.kStateImageSel.TemperatureSensorOn,newStatus, decimalPlaces = 0)

								newStatus = self.setStatusCol( dev, u"Leaving_value", 					xx["current"]["GT"]["totalSum"],		"leaving value:{}".format(xx["current"]["GT"]["totalSum"]),				whichKeysToDisplay, indigo.kStateImageSel.TemperatureSensorOn,newStatus, decimalPlaces = 0)
								newStatus = self.setStatusCol( dev, u"Approaching_value", 				xx["current"]["LT"]["totalSum"],		"approcahing value:{}".format(xx["current"]["LT"]["totalSum"]), 		whichKeysToDisplay, indigo.kStateImageSel.TemperatureSensorOn,newStatus, decimalPlaces = 0)
								newStatus = self.setStatusCol( dev, u"Re-Calibration_needed_value", 	xx["calibrated"]["GT"]["totalSum"],		"calibration value:{}".format(xx["calibrated"]["GT"]["totalSum"]),		whichKeysToDisplay, indigo.kStateImageSel.TemperatureSensorOn,newStatus, decimalPlaces = 0)
								newStatus = self.setStatusCol( dev, u"Room_occupied_value", 			xx["calibrated"]["LT"]["totalSum"],		"occupied value:{}".format(xx["calibrated"]["LT"]["totalSum"]),			whichKeysToDisplay, indigo.kStateImageSel.TemperatureSensorOn,newStatus, decimalPlaces = 0)

								newStatus = self.setStatusCol( dev, u"Current_NonZeroBins", 			xx["current"]["nonZero"],				"current non zero bins:{}".format(xx["current"]["nonZero"]),			whichKeysToDisplay, indigo.kStateImageSel.TemperatureSensorOn,newStatus, decimalPlaces = 0)
								newStatus = self.setStatusCol( dev, u"Calibration_NonZeroBins", 		xx["calibrated"]["nonZero"],			"calibration non zero bins:{}".format(xx["calibrated"]["nonZero"]),		whichKeysToDisplay, indigo.kStateImageSel.TemperatureSensorOn,newStatus, decimalPlaces = 0)
								newStatus = self.setStatusCol( dev, u"ubsPortUsed", 					xx["port"],								xx["port"],																whichKeysToDisplay, indigo.kStateImageSel.TemperatureSensorOn,newStatus, decimalPlaces = 0)

								varName =(dev.name+"_calibrated").replace(" ","_")
								try:
									var = indigo.variables[varName]
								except:
									var = indigo.variable.create(varName,"")
									self.varExcludeSQLList.append(var)

								if "calibrated" in data and len(data["calibrated"]) > 10:
									indigo.variable.updateValue(varName, json.dumps(data["calibrated"]))
								else:
									try:	data["calibrated"] =  json.loads(var.value)
									except: data["calibrated"] = []

								if "saveRawData" in props and props[u"saveRawData"] == "1":
									varName =(dev.name+"_data").replace(" ","_")
									try:
										var = indigo.variables[varName]
									except:
										indigo.variable.create(varName, varName)
										self.varExcludeSQLList.append(varName)
									indigo.variable.updateValue(varName, json.dumps(data))


								if len(props[u"fileName"]) < 5:	fileName = self.indigoPreferencesPluginDir+"lidar360Images/"+dev.name+".png"
								else: 						  	fileName = props[u"fileName"]
							
								if "mode" in props and props[u"mode"] in ["manual","auto"] and ("sendPixelData" in props and props["sendPixelData"] =="1"):
									dataFile = "/tmp/makelidar360.dat"
									if  os.path.isfile(dataFile):
										lastlidar360PlotTime = os.path.getmtime(dataFile)
									else: lastlidar360PlotTime = 0
									if (    "showImageWhen" not in props or  
											( time.time() - lastlidar360PlotTime > float(props[u"showImageWhen"]) ) or 
											data["triggerValues"]["current"]["GT"]["totalCount"] != 0 or 
											data["triggerValues"]["current"]["LT"]["totalCount"] != 0 or
											data["triggerValues"]["calibrated"]["GT"]["totalCount"] != 0 or
											data["triggerValues"]["calibrated"]["LT"]["totalCount"] != 0    ): 

										imageParams	  ={"logFile":self.PluginLogFile, 
													"logLevel":props[u"logLevel"],
													"dataFile":"/tmp/makelidar360.dat",
													"compress":props[u"fileCompress"],
													"fileName":fileName,
													"xMin":props[u"xMin"],
													"xMax":props[u"xMax"],
													"yMin":props[u"yMin"],
													"yMax":props[u"yMax"],
													"scalefactor":props[u"scalefactor"],
													"showZeroValues":props[u"showZeroValues"],
													"mode":props[u"mode"],
													"showPhi0":props[u"showPhi0"],
													"showZeroDot":props[u"showZeroDot"],
													"frameON":props[u"frameON"],
													"DPI":props[u"DPI"],
													"showTriggerValues":props[u"showTriggerValues"],
													"doNotUseDataRanges":props[u"doNotUseDataRanges"],
													"showTimeStamp":props[u"showTimeStamp"],
													"showDoNotTrigger":props[u"showDoNotTrigger"],
													"fontSize":props[u"fontSize"],
													"showLegend":props[u"showLegend"],
													"topText":props[u"topText"],
													"frameTight":props[u"frameTight"],
													"yOffset":props[u"yOffset"],
													"xOffset":props[u"xOffset"],
													"numberOfDotsX":props[u"numberOfDotsX"],
													"numberOfDotsY":props[u"numberOfDotsY"],
													"phiOffset":props[u"phiOffset"],
													"anglesInOneBin":props[u"anglesInOneBin"],
													"colorCurrent":props[u"colorCurrent"],
													"colorCalibrated":props[u"colorCalibrated"],
													"colorLast":props[u"colorLast"],
													"colorBackground":props[u"colorBackground"]} 
										#allData = json.dumps({"imageParams":imageParams, "data":data})
										cmd = self.pythonPath + u" '" + self.pathToPlugin + u"makeLidar360Plot.py' '" +json.dumps(imageParams)+"'  & "  
										if props[u"logLevel"] in ["1","3"] : self.indiLOG.log(20,"lidar360 command:{}".format(cmd))
										self.writeJson(data, fName="/tmp/makeLidar360.dat") 
										subprocess.call(cmd, shell=True)
						except Exception, e:
							self.indiLOG.log(40,"Line {} has error={}".format(sys.exc_traceback.tb_lineno, e))
							self.indiLOG.log(40,"props: {}".format(props))
							self.indiLOG.log(40,"triggervalues: {}".format(data[u"triggerValues"]) )

					if updateProps:
						self.deviceStopCommIgnore = time.time()
						dev.replacePluginPropsOnServer(props)

		
				for devIds in devUpdate:
					if devIds in self.updateStatesDict:
						if self.decideMyLog(u"SensorData"): self.indiLOG.log(10, u"pi# "+piU + "  " + unicode(devIds)+"  "+unicode(self.updateStatesDict))
						self.executeUpdateStatesDict(onlyDevID=devIds,calledFrom="updateSensors end")
			self.saveSensorMessages(devId="")

		except Exception, e:
			if len(unicode(e)) > 5 :
				self.indiLOG.log(40,"Line {} has error={}".format(sys.exc_traceback.tb_lineno, e))
				self.indiLOG.log(40,u"pi# "+piU + "  " + unicode(sensors))

		return

####-------------------------------------------------------------------------####
	def updaterainSensorRG11(self, dev, data, whichKeysToDisplay):
		try:
			props = dev.pluginProps
			if "lastUpdate" not in props or props[u"lastUpdate"]=="0":
				props[u"lastUpdate"] = time.time()
			dd = datetime.datetime.now().strftime(_defaultDateStampFormat)
			updateDev = False
			##indigo.server.log(unicode(data))
			rainChanges = []
			if len(dev.states["resetDate"]) < 5:
				rainChanges.append(["resetDate", dd, dd,""])
				#self.addToStatesUpdateDict(dev.id, "resetDate", datetime.datetime.now().strftime(_defaultDateStampFormat))

			if	 self.rainUnits == "inch":	   mult = 1/25.4	; unit = "in"
			elif self.rainUnits == "cm":	   mult = 0.1 		; unit = "cm"
			else:                              mult = 1 		; unit = "mm"

			if "format" in props and len(props[u"format"])<2: form = "%.{}f[{}]".format(self.rainDigits+1, self.rainUnits)
			else:											  form = props[u"format"]

			for cc in ["totalRain", "rainRate", "measurementTime", "mode", "rainLevel", "sensitivity","nBuckets","nBucketsTotal","bucketSize"]:
				if cc in data:

					if cc =="totalRain":
						x = float(data[cc])*mult	 # is in mm 
						rainChanges.append([cc, x, form%x, self.rainDigits])
						for zz in ["hourRain","dayRain","weekRain","monthRain","yearRain"]:
							zzP= zz+"Total"
							if zzP in props:
								oldV = float(props[zzP])
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
							rtm	 = props[u"rainTextMap"].split(";")
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

					elif cc == "rainLevel":
						try: x = int(data[cc])
						except: x = 0
						labels = (props[u"rainMsgMap"]).split(";")
						if x in [0,1,2,3,4]:
							if x >1: 
								rainChanges.append(["lastRain",dd,dd,""])
							if len(labels) > x:
								rainChanges.append([cc, labels[x],labels[x],""])
								if whichKeysToDisplay == cc: 
									rainChanges.append([u"status", labels[x], labels[x],""])
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
							xx = "0[{}]".format(unit)
							x = float(data[cc])*mult
							if x > 0:  xx = "{:.2f}[{}]".format(x, unit)
						except: pass 
						rainChanges.append([cc, x,xx, 4])
					else:
						x = data[cc]
						rainChanges.append([cc, x,unicode(x),""])
			if len(rainChanges)>0:
				if time.time() - props[u"lastUpdate"] > 900:	  # force update every 15 minutes
					ff = True
					props[u"lastUpdate"] = time.time()
					updateDev = True
				else:
					ff = False
				for xx in rainChanges:
					self.setStatusCol( dev, xx[0], xx[1], xx[2], whichKeysToDisplay, indigo.kStateImageSel.TemperatureSensorOn,"", decimalPlaces =xx[3], force = ff)
			if updateDev: 
				self.deviceStopCommIgnore = time.time()
				dev.replacePluginPropsOnServer(props)

		except Exception, e:
			self.indiLOG.log(40,"Line {} has error={}".format(sys.exc_traceback.tb_lineno, e))
			self.indiLOG.log(40,unicode(data))
		return



####-------------------------------------------------------------------------####
	def updatePMAIRQUALITY(self, dev, data, whichKeysToDisplay):
		try:
			for cc in ["pm10_standard","pm25_standard","pm100_standard", "pm10_env","pm25_env","pm100_env","particles_03um","particles_05um","particles_10um","particles_25um","particles_50um","particles_100um"]:
				if cc in data:
					if cc.find("pm") >-1: units = "ug/m3"
					else:				  units = "C/0.1L"
					x, UI  = int(float(data[cc])), cc+"=%d["%(int(float(data[cc])))+units+"]"

					self.setStatusCol(dev,cc,x,UI,whichKeysToDisplay,"","",decimalPlaces=0)

					if cc == "pm25_standard":
						if	  x < 12:		airQuality = "Good"
						elif  x < 35.4:		airQuality = "Moderate" 
						elif  x < 55.4:		airQuality = "Unhealthy Sensitve" 
						elif  x < 150.4:	airQuality = "Unhealthy" 
						elif  x < 250.4:	airQuality = "Very Unhealthy" 
						else:				airQuality = "Hazardous"


						self.setStatusCol(dev,u"airQuality",airQuality,"Air Quality is "+airQuality,whichKeysToDisplay,"","",decimalPlaces=1)

						useSetStateColor = False
						if  cc == whichKeysToDisplay: 
							useSetStateColor = self.setStateColor(dev, dev.pluginProps, data[cc])
						if not useSetStateColor:
							if	 airQuality == "Good":		 dev.updateStateImageOnServer(indigo.kStateImageSel.SensorOn)
							elif airQuality == "Moderate":	 dev.updateStateImageOnServer(indigo.kStateImageSel.SensorOff)
							else:							 dev.updateStateImageOnServer(indigo.kStateImageSel.SensorTripped)

		except Exception, e:
			self.indiLOG.log(40,"Line {} has error={}".format(sys.exc_traceback.tb_lineno, e))
			self.indiLOG.log(40, unicode(data))
		return



####-------------------------------------------------------------------------####
	def setPressureDisplay(self, dev, props, data, whichKeysToDisplay, newStatus):
		try:
			updateProps = False
			doUpdate    = []
			if u"press" in data:
				p = float(data[u"press"])

				if self.pressureUnits == "atm":
					useFormat = "{:6.3f} atm" ;		decimalPlaces = 4; mult = 0.000009869233
					p *= mult ; pu = useFormat.format(p)
				elif self.pressureUnits == "bar":
					useFormat = "{:6.3f} Bar" ;		decimalPlaces = 4; mult = 0.00001
					p *= mult ; pu = useFormat.format(p)
				elif self.pressureUnits.lower() == "mbar":
					useFormat = "{:6.1f} mBar";		decimalPlaces = 1; mult = 0.01
					p *= mult; pu = useFormat.format(p)
				elif self.pressureUnits == "mm":
					useFormat = "{:6.0f} mmHg";		decimalPlaces = 0; mult = 0.00750063
					p *= mult ; pu = useFormat.format(p)
				elif self.pressureUnits == "Torr":
					useFormat = "{:.0f} Torr" ;		decimalPlaces = 0; mult = 0.00750063
					p *= mult; pu = useFormat.format(p)
				elif self.pressureUnits == "inches":
					useFormat = "{:6.2f} inches";	decimalPlaces = 2; mult = 0.000295299802
					p *= mult ; pu = useFormat.format(p)
				elif self.pressureUnits == "PSI":
					useFormat = "{:6.2f} PSI";		decimalPlaces = 2; mult = 0.000145038
					p *= mult ; pu = useFormat.format(p)
				elif self.pressureUnits == "hPascal":
					useFormat = "{:.0f} hPa";		decimalPlaces = 0; mult = 0.01
					p *= mult ; pu = useFormat.format(p)
				else:
					useFormat = "{:.0f}  Pa"; 		decimalPlaces = 0; mult = 1.
					p *= mult ; pu = useFormat.format(p)
				#self.indiLOG.log(20,"p ={}  units:{}".format( p, self.pressureUnits ) )
				pu = pu.strip()
				newStatus = self.setStatusCol(dev, u"Pressure", p, pu, whichKeysToDisplay, u"",newStatus, decimalPlaces = 0)
				updateProps, doUpdate = self.updateChangedValues(dev, p, props, "Pressure", useFormat, whichKeysToDisplay, 0)

		except Exception, e:
			if len(unicode(e)) > 5 :
				self.indiLOG.log(40,"Line {} has error={}".format(sys.exc_traceback.tb_lineno, e))
		#self.indiLOG.log(20,"returning {} {} {} dat:{} ".format(useFormat, decimalPlaces, p, data) )
		return newStatus, updateProps, doUpdate



####-------------------------------------------------------------------------####
	def setMoistureDisplay(self, dev, props, data, whichKeysToDisplay, newStatus):
		try:
			updateProps = False
			doUpdate    = []
			if u"moisture" in data:
				raw = int(float(data[u"moisture"]))
				try: 	minM = float(props["minMoisture"])
				except: minM = 330.
				try: 	maxM = float(props["maxMoisture"])
				except: maxM = 630.
				relM = int(100*float(raw-minM)/max(1.,maxM-minM))
				relMU = "{}%".format(relM)
		
				updateProps, doUpdate = self.updateChangedValues(dev, relM, props, "Moisture", "", "",0)
				self.addToStatesUpdateDict(dev.id, "Moisture_raw", raw)
				newStatus = self.setStatusCol(dev, u"Moisture", relM, relMU, "Moisture", u"",newStatus, decimalPlaces = 0)

			
		except Exception, e:
			if len(unicode(e)) > 5 :
				self.indiLOG.log(40,"Line {} has error={}".format(sys.exc_traceback.tb_lineno, e))
		#self.indiLOG.log(20,"returning {} {} {} dat:{} ".format(useFormat, decimalPlaces, p, data) )
		return newStatus, updateProps, doUpdate


####-------------------------------------------------------------------------####
	def setStatusCol(self,dev, key, value, valueUI, whichKeysToDisplay, image, oldStatus, decimalPlaces=1, force=False):
		try:
			newStatus = oldStatus
			if whichKeysToDisplay !="":
				whichKeysToDisplayList = whichKeysToDisplay.split(u"/")
				whichKeysToDisplaylength = len(whichKeysToDisplayList)
				currentDisplay = oldStatus.split(u"/")
				if len(currentDisplay) != whichKeysToDisplaylength: # reset? display selection changed?
					currentDisplay = whichKeysToDisplay.split(u"/")

			if unicode(dev.states[key]) != unicode(value):
				self.addToStatesUpdateDict(dev.id, key, value, decimalPlaces=decimalPlaces,force=force)
				self.fillMinMaxSensors(dev,key,value,decimalPlaces=decimalPlaces)

			#if dev.name =="s-3-rainSensorRG11": indigo.server.log(dev.name+"  in setStatusCol "+key+"  "+unicode(value)+"   "+unicode(valueUI))

			if whichKeysToDisplay !="":
				for i in range(whichKeysToDisplaylength):
					if whichKeysToDisplayList[i] == key:
						#if dev.name =="s-3-rainSensorRG11": indigo.server.log(dev.name+"  in after  whichKeysToDisplayList")

						if currentDisplay[i] != valueUI:
							if i==0:
								if  not self.setStateColor(dev, dev.pluginProps, value):
									if  image != "":
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
									##indigo.server.log(dev.name+"  setStatusCol key:"+key+"  value:"+unicode(value) +"  x:"+unicode(x)+"  decimalPlaces:"+unicode(decimalPlaces))
								#if dev.name =="s-3-rainSensorRG11": indigo.server.log(dev.name+"  "+key+"  "+unicode(value)+"   "+unicode(x)+"  "+valueUI)
								if decimalPlaces !="":
									self.addToStatesUpdateDict(dev.id,u"sensorValue", round(x,decimalPlaces), decimalPlaces=decimalPlaces, uiValue=newStatus,force=force)
								else:
									self.addToStatesUpdateDict(dev.id,u"sensorValue", x, uiValue=newStatus,force=force)
							self.addToStatesUpdateDict(dev.id,u"status", newStatus,force=force)
							break


		except Exception, e:
			if len(unicode(e)) > 5 :##
				self.indiLOG.log(40,"Line {} has error={}".format(sys.exc_traceback.tb_lineno, e))
		return newStatus

 
####-------------------------------------------------------------------------####
	def updateOneWire(self,dev, data, whichKeysToDisplay, piU):

		## add check for addNewOneWireSensors only add new one if TRUE 
		## format:
		#"sensors":{"Wire18B20":{
		#"1565508294":{"temp":[{"28-0316b5fa44ff":"24.3"}]},
		#"1447141059":{"temp":[{"28-0516b332fbff":"24.8"}]},
		#"416059968": {"temp":[{"28-800000035de5":"21.8"},	{"28-0416b39944ff":"24.6"}]},  ## can be multiple 
		#"1874530568":{"temp":[{"28-0516b33621ff":"24.6"}]}}}
		## 
		try:
			for NNN in data[u"temp"]:
				if not isinstance(NNN, type({})): 
					continue ## old format , skip ; must be list
				for serialNumber in NNN:
					temp = NNN[serialNumber]
					if temp == "85.0":	temp = "999.9"
					x, UI, decimalPlaces, useFormat  = self.convTemp(temp)
					if dev.states[u"serialNumber"] == "" or dev.states[u"serialNumber"] == serialNumber: # ==u"" new, ==Serial# already setup
						if dev.states[u"serialNumber"] == "": 
							self.addToStatesUpdateDict(dev.id,"serialNumber",serialNumber)
							self.setONErPiV(piU,"piUpToDate", [u"updateParamsFTP"])
						if serialNumber != u"sN= " + dev.description:
							if dev.description.find("sN= ") == 0:
								snOld = dev.description.split(" ")
								addtext =""
								if len(snOld) >2: addtext= " "+ " ".join(snOld[2:])
								if snOld[1] != serialNumber:
									dev.description = u"sN= " + serialNumber +addtext
									dev.replaceOnServer()
							else:
								dev.description = u"sN= " + serialNumber 
								dev.replaceOnServer()
							dev = indigo.devices[dev.id]
						props = dev.pluginProps
						self.setStatusCol( dev, u"Temperature", x, UI, whichKeysToDisplay, indigo.kStateImageSel.TemperatureSensorOn,dev.states[u"status"], decimalPlaces = decimalPlaces )
						updateProps, doUpdate = self.updateChangedValues(dev, x, props, "Temperature", useFormat, whichKeysToDisplay, decimalPlaces)
						if updateProps: 
							props[doUpdate[0]] = doUpdate[1]
							self.deviceStopCommIgnore = time.time()
							dev.replacePluginPropsOnServer(props)

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
								props = indigo.devices[int(self.RPI[piU]["piDevId"])].pluginProps
								if "addNewOneWireSensors" in props and props[u"addNewOneWireSensors"] == "1":
									dev1 = indigo.device.create(
											protocol		= indigo.kProtocol.Plugin,
											address			= "Pi-"+piU,
											name			= dev.name+"_"+serialNumber,
											pluginId		= self.pluginId,
											deviceTypeId	= "Wire18B20",
											folder			= self.piFolderId,
											description		= u"sN= " + serialNumber,
											props			= {u"piServerNumber":piU, "displayState":"status", "displayS":"Temperature", "offsetTemp":"0",  u"displayEnable": u"0", "isSensorDevice":True,
																"SupportsSensorValue":True, "SupportsOnState":False, "AllowSensorValueChange":False, "AllowOnStateChange":False, "SupportsStatusRequest":False}
											)

									if "input"	   not in self.RPI[piU]			 : self.RPI[piU]["input"] ={}
									if "Wire18B20" not in self.RPI[piU]["input"] : self.RPI[piU]["input"]["Wire18B20"] ={}
									self.RPI[piU]["input"]["Wire18B20"][unicode(dev1.id)] = ""
									self.addToStatesUpdateDict(unicode(dev1.id),"serialNumber",serialNumber)
									self.setStatusCol( dev1, u"Temperature", x, UI, whichKeysToDisplay, indigo.kStateImageSel.TemperatureSensorOn,dev1.states[u"status"], decimalPlaces = decimalPlaces )
									props = dev1.pluginProps
									updateProps, doUpdate = self.updateChangedValues(dev, x, props, "Temperature", useFormat, whichKeysToDisplay, decimalPlaces)
									if updateProps: 
										props[doUpdate[0]] = doUpdate[1]
										self.deviceStopCommIgnore = time.time()
										dev1.replacePluginPropsOnServer(props)
									self.executeUpdateStatesDict(onlyDevID=unicode(dev1.id),calledFrom="updateOneWire")
									self.setONErPiV(piU,"piUpToDate", [u"updateParamsFTP"])
									self.saveConfig()
							except Exception, e:
								self.indiLOG.log(40,"Line {} has error={}".format(sys.exc_traceback.tb_lineno, e))
								continue

		except Exception, e:
				self.indiLOG.log(40,"Line {} has error={}".format(sys.exc_traceback.tb_lineno, e))


 
####-------------------------------------------------------------------------####
	def updateBLEsensor(self, dev, data, props, whichKeysToDisplay):
		try:
			x, UI, decimalPlaces, useFormat  = self.convTemp(data[u"temp"])
			self.addToStatesUpdateDict(dev.id,"TxPower",data[u"txPower"])
			self.addToStatesUpdateDict(dev.id,"rssi"	,data[u"rssi"])
			self.addToStatesUpdateDict(dev.id,"UUID"	,data[u"UUID"])
			self.setStatusCol( dev, u"Temperature", x, UI, whichKeysToDisplay, indigo.kStateImageSel.TemperatureSensorOn,dev.states[u"status"], decimalPlaces = decimalPlaces )
			updateProps, doUpdate = self.updateChangedValues(dev, x, props, "Temperature", useFormat, whichKeysToDisplay, decimalPlaces)
			if updateProps: 
				props[doUpdate[0]] = doUpdate[1]
				self.deviceStopCommIgnore = time.time()
				dev.replacePluginPropsOnServer(props)
				props[doUpdate[0]] = doUpdate[1]

		except Exception, e:
			if len(unicode(e)) > 5 :
				self.indiLOG.log(40,"Line {} has error={}".format(sys.exc_traceback.tb_lineno, e))



 
####-------------------------------------------------------------------------####
	def updatePULSE(self, dev, data, whichKeysToDisplay):
		if self.decideMyLog(u"SensorData"): self.indiLOG.log(10, "updatePULSE {}".format(data))
		props = dev.pluginProps
		try:	
			dd = datetime.datetime.now().strftime(_defaultDateStampFormat) 
			countList = [(0,0),(0,0)] # is list of [[time0 ,count0], [time1 ,count1],...]  last counts up to 3600 secs,  then pop out last
			if "countList" in props: countList= json.loads(props["countList"])
			if u"count" in data:
				try: cOld = float(dev.states[u"count"])
				except: cOld = 0

				## is there a count reset?, if yes remove old counts
				ll = len(countList)
				if countList[-1][1] >  cOld: countList=[]


				countList.append([time.time(),data[u"count"]])
				ll = len(countList)
				if len(countList) >2:
					dT =  max( countList[-1][0]- countList[-2][0],1.)
					countsPerSecond = max(0,(float(data[u"count"]) - cOld) / dT)
				else:
					countsPerSecond = 0
				ll = len(countList)
				if ll >2:
					for ii in range(ll):
						#self.indiLOG.log(10, "updatePULSE bf count pop countList:{}".format(countList) )
						if len(countList) <=2: break
						if countList[0][1] >  countList[-1][1]: countList.pop(0)
						else: break
				ll = len(countList)
				if ll >2:
					for ii in range(ll):
						if len(countList) <= 2: break
						if countList[0][0] < countList[-1][0] -3600*24: countList.pop(0)
						else: 				    break
				ll = len(countList)
				minPointer = ll -1
				if ll > 1:
					for ii in range(1, ll):
							if countList[ll-ii][0] > countList[-1][0] -60:	minPointer = ll-ii
							else:
								if minPointer == ll-1:
									minPointer = ll-ii
								break
				hourPointer = ll -1
				if ll > 1:
					for ii in range(1, ll):
							if countList[ll-ii][0] > countList[-1][0] -60:	hourPointer = ll-ii
							else:
								if hourPointer == ll-1:
									hourPointer = ll-ii
								break
 
				#self.indiLOG.log(20, "updatePULSE minPointer:{}; tt:{:.0f}; countList:{}".format(minPointer, time.time(), countList) )
				self.setStatusCol( dev, u"count", data[u"count"], "{:.0f}[c]".format(data[u"count"]), whichKeysToDisplay, "","", decimalPlaces = "" )
				if cOld <= data[u"count"]: 
					countsPerMinute =   60.    * ( countList[minPointer][1]  - countList[0][1] ) /  max(1., ( countList[minPointer][0]  - countList[0][0]) )
					countsPerHour   = 3600.    * ( countList[hourPointer][1] - countList[0][1] ) /  max(1., ( countList[hourPointer][0] - countList[0][0]) )
					countsPerDay    = 3600.*24 * ( countList[-1][1]          - countList[0][1] ) /  max(1., ( countList[-1][0]          - countList[0][0]) )
					#self.indiLOG.log(10, "updatePULSE cmp:{}; cOld:{};  sdata: {};  tt:{}; dcount:{}; dtt:{}; ll:{}; countList:{}".format(countsPerMinute, cOld, data, time.time(), ( countList[-1][1] - countList[0][1] ), (countList[-1][0]  - countList[0][0]) , len(countList),  countList ) )
					self.setStatusCol( dev, u"countsPerLast", countsPerSecond, u"{:.2f}[c/s]".format(countsPerSecond), whichKeysToDisplay, "","", decimalPlaces = 2 )
					self.setStatusCol( dev, u"countsPerMinute", countsPerMinute, u"{:.2f}[c/m]".format(countsPerMinute), whichKeysToDisplay, "","", decimalPlaces = 2 )
					self.setStatusCol( dev, u"countsPerHour",   countsPerHour,   u"{:.1f}[c/h]".format(countsPerHour),   whichKeysToDisplay, "","", decimalPlaces = 2 )
					self.setStatusCol( dev, u"countsPerDay",    countsPerDay,  	 u"{:.1f}[c/d]".format(countsPerDay),    whichKeysToDisplay, "","", decimalPlaces = 2 )
					if cOld != countList[-1][1]: self.addToStatesUpdateDict(dev.id,"lastCountTime",dd)
				props["countList"] = json.dumps(countList)
				self.deviceStopCommIgnore = time.time()
				dev.replacePluginPropsOnServer(props)
			else:
				pass

			if u"burst" in data and data[u"burst"] !=0 and data[u"burst"] !="":
					self.addToStatesUpdateDict(dev.id,"lastBurstTime",dd )

			if u"continuous" in data and data[u"continuous"] !="":
					if data[u"continuous"] > 0: 
						self.addToStatesUpdateDict(dev.id,"lastContinuousEventTime",dd )
						self.addToStatesUpdateDict(dev.id,"lastContinuousEventStopTime","")
					else: 
						if dev.states["lastContinuousEventStopTime"] == "":
							self.addToStatesUpdateDict(dev.id,"lastContinuousEventStopTime",dd)

		except Exception, e:
			if len(unicode(e)) > 5 :
				self.indiLOG.log(40,"Line {} has error={}".format(sys.exc_traceback.tb_lineno, e))
		return 
 
 


####-------------------------------------------------------------------------####
	def updateChangedValues(self,dev, value, props, propToUpdate, useFormat, whichKeysToDisplay, decimalPlaces):
		try:	
			if propToUpdate not in dev.states: 					
				self.indiLOG.log(20, "updateChangedValues: prop{}  \nnot in props: {}".format(propToUpdate, props))
				return False, []

			updateList = []
			for state in dev.states:
				if state.find(propToUpdate+"Change") == 0:
					upU = state.split("Change")[1]
					if len(upU) < 2: continue
					if upU.find("Hour") >-1:     updateN = "Hour";   updateMinutes = 3600
					elif upU.find("Minute") >-1: updateN = "Minute"; updateMinutes = 60
					else: continue
					amount = upU.split(updateN)[0]
					updateList.append( {"state":state, "unit":updateN, "deltaSecs":updateMinutes * int(amount), "pointer":0, "changed":0} )

			updateList = sorted(updateList, key = lambda x: x["deltaSecs"])				
			if len(updateList) < 1: return False, []

			if propToUpdate+"list" in props: 
				valueList = json.loads(props[propToUpdate+"list"])
			else:
				valueList = [(0,0),(0,0)]


			if type(value) == float and useFormat.find("{:d}") ==-1:	valueList.append([int(time.time()),round(value,decimalPlaces)])
			else:														valueList.append([int(time.time()),int(value)])

			jj 		= len(updateList)
			cutMax	= updateList[-1]["deltaSecs"]
			ll		= len(valueList)
			for ii in range(ll):
				if len(valueList) <= 2: break
				if (valueList[-1][0] - valueList[0][0]) > cutMax: valueList.pop(0)
				else: 				    break

						
			ll = len(valueList)
			if ll > 1:
				for kk in range(jj):
					cut = updateList[kk]["deltaSecs"]
					updateList[kk]["pointer"] = 0
					if cut != cutMax: # we can skip the largest, must be first and last entry
						for ii in range(ll-1,-1,-1):
							if (valueList[-1][0] - valueList[ii][0]) <= cut:
								updateList[kk]["pointer"] = ii
							else:
								break

					changed			 = ( valueList[-1][1] - valueList[updateList[kk]["pointer"]][1] )
					try: 	uChanged = useFormat.format(changed)
					except: uChanged = unicode(changed)
					#updateList[kk]["changed"] = uChanged
					self.setStatusCol( dev, updateList[kk]["state"], changed, uChanged, whichKeysToDisplay, "","", decimalPlaces = decimalPlaces )

			return True, [propToUpdate+"list",json.dumps(valueList).strip(" ")]

		except Exception, e:
			#if len(unicode(e)) > 5 :
				self.indiLOG.log(40,"Line {} has error={}".format(sys.exc_traceback.tb_lineno, e))
		return False, []
 

####-------------------------------------------------------------------------####
	def updateTEA5767(self,sensors,sensor):
		if self.decideMyLog(u"OutputDevice"): self.indiLOG.log(10, sensor+"     "+unicode(sensors))
		for devId in sensors:
			try:
				dev = indigo.devices[int(devId)]
				iii = 0
				for channels in sensors[devId][u"channels"]:
					self.indiLOG.log(20, "updateTEA5767 sensor: "+sensor+"  "+unicode(channels))
					freq   = channels[u"freq"]
					Signal = channels[u"Signal"]
					ch = "Channel-"+"%02d"%iii
					self.addToStatesUpdateDict(devId,ch,"f="+unicode(freq)+"; Sig="+unicode(Signal))
					iii+=1
				for ii in range(iii,41):
					ch = "Channel-"+"%02d"%ii
					self.addToStatesUpdateDict(devId,ch,"")
			except Exception, e:
				if len(unicode(e)) > 5 :
					self.indiLOG.log(40,"Line {} has error={}".format(sys.exc_traceback.tb_lineno, e))
		return 
	   
####-------------------------------------------------------------------------####
	def updateGetBeaconParameters(self,pi,data):
## 		format:		data["sensors"]["getBeaconParameters"][mac] = {state:{value}}}

		try:
			if self.decideMyLog(u"BatteryLevel"): self.indiLOG.log(20,"GetBeaconParameters update received  pi#:{};  data:{}".format(pi, data) )
			for beacon in data:
				if beacon in self.beacons:
					indigoId = int(self.beacons[beacon]["indigoId"])
					if indigoId > 0:
						dev = indigo.devices[int(indigoId)]
						props = dev.pluginProps
						try: 	batteryLevelLastUpdate = time.mktime(time.strptime(dev.states["batteryLevelLastUpdate"], _defaultDateStampFormat ))
						except: batteryLevelLastUpdate = 0
						for state in data[beacon]:

							if type(data[beacon][state]) == type(1):
								upd = True
								if state+"UUID" in props:
									if (props[state+"UUID"]).find("-int") > 5: 
										if data[beacon][state] < 0: 
											upd = False
								if upd:
									try:
										self.addToStatesUpdateDict(indigoId, state, data[beacon][state])
										if state == "batteryLevel": 
											self.addToStatesUpdateDict(indigoId, "batteryLevelLastUpdate", datetime.datetime.now().strftime(_defaultDateStampFormat))
									except Exception, e:
										if len(unicode(e)) > 5 :
											self.indiLOG.log(40,"Line {} has error={}".format(sys.exc_traceback.tb_lineno, e))
								else:
									if time.time() - batteryLevelLastUpdate > 24*3600: self.indiLOG.log(20,"GetBeaconParameters update received pi:{} beacon:{} .. {};  bad data read  < 0; last good update was {}, current batterylevel status: {}".format(pi,beacon, data[beacon], dev.states["batteryLevelLastUpdate"], dev.states["batteryLevel"]  ) )
							else:
								if data[beacon][state].find("error") >-1 or  data[beacon][state].find("timeout") >-1 :
									if state == "batteryLevel" and "batteryLevelLastUpdate" in dev.states: 
											if  len(dev.states["batteryLevelLastUpdate"] ) < 10:
												self.addToStatesUpdateDict(indigoId, "batteryLevelLastUpdate", "2000-01-01 00:00:00")
											if time.time() - batteryLevelLastUpdate > 24*3600: self.indiLOG.log(20,"GetBeaconParameters update received pi:{}  beacon:{} .. error msg: {}; last update was {}, current batterylevel status: {}".format(pi,beacon, data[beacon][state].find("error"), dev.states["batteryLevelLastUpdate"], dev.states["batteryLevel"] ) )
									else:
										if time.time() - batteryLevelLastUpdate > 24*3600: self.indiLOG.log(20,"GetBeaconParameters update received pi:{} beacon:{} .. error msg: {}".format(pi,beacon, data[beacon][state] ) )
								else:
									try:
										if state+"UUID" in props and (props[state+"UUID"]).find("-int") == -1: 
											self.addToStatesUpdateDict(indigoId, state, data[beacon][state])
											if self.decideMyLog(u"BatteryLevel"): self.indiLOG.log(20,"GetBeaconParameters updateing received for {}  value:{}".format(dev.name.encode("utf8"), data[beacon][state]) )
									except Exception, e:
										if len(unicode(e)) > 5 :
											self.indiLOG.log(40,"Line {} has error={}".format(sys.exc_traceback.tb_lineno, e))
						


		except Exception, e:
			self.indiLOG.log(40,"Line {} has error={}".format(sys.exc_traceback.tb_lineno, e))

####-------------------------------------------------------------------------####
	def updateINPUT(self, dev, data, upState, nInputs, sensor):
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
				upState = "INPUT_"+unicode(upS)
			except:pass
			decimalPlaces = 0

			for ii in range(max(1,nInputs)):
				INPUT_raw = False

				if nInputs >10:
						inputState = "INPUT_%0.2d" % (ii+addToInputName)
				elif nInputs == 1 and  u"INPUT" in dev.states:
						inputState = u"INPUT"
						upState	   = u"INPUT"
				elif nInputs == 0 and  u"INPUT" in dev.states:
						inputState = u"INPUT"
						if u"INPUT_raw" in dev.states: 
							INPUT_raw = True
				else:	inputState = u"INPUT_" + unicode(ii+addToInputName)


				if self.decideMyLog(u"SensorData"): self.indiLOG.log(20,"updateINPUT: {};  sensor: {};  upState: {}; inputState: {};  data: {}".format(dev.name.encode("utf8"), sensor, upState, inputState, data) )
				if inputState in data:
					if INPUT_raw: 	 self.addToStatesUpdateDict(dev.id,u"INPUT_raw", data[inputState])
					ss, ssUI, unit = self.addmultOffsetUnit(data[inputState], props)
					if dev.states[inputState] != ss:
						self.addToStatesUpdateDict(dev.id,inputState, ss)
						### minmax if deice.xml has that field
						decimalPlaces = 1
						v = ss
						if upState == inputState:
							try: 
								v = float(self.getNumber(ssUI))
								dp = unicode(v).split(".")
								if len(dp)   == 0:	decimalPlaces = 0
								elif len(dp) == 2:	decimalPlaces = len(dp[1])
							except: pass

						if INPUT_raw: ss = v

						if inputState+"MaxYesterday" in dev.states:
							self.fillMinMaxSensors(dev,inputState,v,decimalPlaces=decimalPlaces)

						if upState == inputState:
							if not self.setStateColor(dev,props,ss):
								fs = self.getNumber(ss)
								if ss == u"1" or ss == u"up" or (fs != 0. and fs != "x"):
									on = True
									self.setIcon(dev,props,"SensorOff-SensorOn",1)
								else:
									on = False
									self.setIcon(dev,props,"SensorOff-SensorOn",0)

							if u"onOffState" in dev.states: 
								self.addToStatesUpdateDict(dev.id,u"onOffState",on, uiValue=ssUI)
								if dev.states[u"status"] != ssUI + unit:
									self.addToStatesUpdateDict(dev.id,u"status", ssUI)
							if u"sensorValue" in dev.states: 
								if self.decideMyLog(u"SensorData"): self.indiLOG.log(30, "{};  sensor:{};  sensorValue".format(dev.name.encode("utf8"), sensor) )
								self.setStatusCol(dev, upState, ss, ssUI + unit, upState, "","", decimalPlaces = decimalPlaces)
							else:
								if dev.states[u"status"] != ssUI + unit:
									self.addToStatesUpdateDict(dev.id,u"status", ssUI+unit)

		except Exception, e:
			self.indiLOG.log(40,"Line {} has error={}".format(sys.exc_traceback.tb_lineno, e))

####-------------------------------------------------------------------------####
	def setStateColor(self, dev, props, ss):
		try:
			if not( "stateGreen" in props and "stateGrey" in props and "stateRed" in props): return False
			try:
				commands = {"green":props["stateGreen"], "grey":props["stateGrey"], "red":props["stateRed"]} 
				ok = False
				for cmd in commands:
					if len(commands[cmd]) > 0: ok = True 
				if commands["green"] == commands["grey"] and commands["grey"] == commands["red"]: return False
			except: return False
			if not ok: return 

			x = self.getNumber(ss)
			if self.decideMyLog(u"Special"):self.indiLOG.log(20,"setStateColor for dev {}, x={};  eval syntax: {}".format(dev.name.encode("utf8"), x, commands) )
			for col in ["green","grey","red"]:
				try: 
					if len(commands[col]) == 0: continue
					if eval(commands[col]) :
						if col =="green": dev.updateStateImageOnServer(indigo.kStateImageSel.SensorOn)
						if col =="grey": dev.updateStateImageOnServer(indigo.kStateImageSel.SensorOff)
						if col =="red": dev.updateStateImageOnServer(indigo.kStateImageSel.SensorTripped)
						return True
				except: 
					self.indiLOG.log(20,"setStateColor for dev {}, x={};  color: {};  wrong eval syntax: {}".format(dev.name.encode("utf8"), x, col, commands[col]) )


		except Exception, e:
			self.indiLOG.log(40,"Line {} has error={}".format(sys.exc_traceback.tb_lineno, e))
		return False


####-------------------------------------------------------------------------####
	def setIcon(self, dev,iconProps,default,UPdown):
		try:
			if u"iconPair" in iconProps and	 iconProps [u"iconPair"] !="":
				icon = iconProps [u"iconPair"].split(u"-")[UPdown]
			else: 
				icon = default.split(u"-")[UPdown]
			try:
				dev.updateStateImageOnServer(getattr(indigo.kStateImageSel, icon, None)) 
			except Exception, e: 
				if UPdown ==0:					 dev.updateStateImageOnServer(indigo.kStateImageSel.SensorOff)
				else:							 dev.updateStateImageOnServer(indigo.kStateImageSel.SensorOn)
		except Exception, e:
			if self.decideMyLog(u"SensorData"): self.indiLOG.log(40,"Line {} has error={}".format(sys.exc_traceback.tb_lineno, e))
			return



####-------------------------------------------------------------------------####
	def updateapds9960(self, dev, data):
		try:
			props = dev.pluginProps
			input = u"gesture"
			if input in data:
				if unicode(data[input]).find(u"bad") >-1:
					self.addToStatesUpdateDict(dev.id,u"status", u"no sensor data - disconnected?")
					self.setIcon(dev,props,"SensorOff-SensorOn",0)
					return
				else:
					if data[input] !="NONE":
						if props[u"displayS"] == input:
							self.addToStatesUpdateDict(dev.id,u"status", data[input])
						self.addToStatesUpdateDict(dev.id,input,data[input])
						self.addToStatesUpdateDict(dev.id,input+"Date",datetime.datetime.now().strftime(_defaultDateStampFormat))
						self.setIcon(dev,props,"SensorOff-SensorOn",1)


			input = u"gestureData"
			if input in data:
					if data[input] !="":
						if props[u"displayS"] == input:
							self.addToStatesUpdateDict(dev.id,u"status", data[input])
						self.addToStatesUpdateDict(dev.id,input,data[input])
						self.setIcon(dev,props,"SensorOff-SensorOn",1)

			input = u"distance"
			if input in data:
				if unicode(data[input]).find(u"bad") >-1:
					self.addToStatesUpdateDict(dev.id,u"status", u"no sensor data - disconnected?")
					self.setIcon(dev,props,"SensorOff-SensorOn",0)
				else:
					if data[input] !="NONE":
						if props[u"displayS"] == input:
							self.addToStatesUpdateDict(dev.id,u"status", data[input])
						self.addToStatesUpdateDict(dev.id,input,data[input])
						self.addToStatesUpdateDict(dev.id,input+"Date",datetime.datetime.now().strftime(_defaultDateStampFormat))
						self.setIcon(dev,props,"SensorOff-SensorOn",1)

			input = u"proximity"
			if input in data:
				if unicode(data[input]).find(u"bad") >-1:
					self.addToStatesUpdateDict(dev.id,u"status", u"no sensor data - disconnected?")
					self.setIcon(dev,props,"SensorOff-SensorOn",0)
				else:
						if props[u"displayS"] == input:
							self.addToStatesUpdateDict(dev.id,u"status", data[input])
						self.addToStatesUpdateDict(dev.id,input,data[input])
						self.addToStatesUpdateDict(dev.id,input+"Date",datetime.datetime.now().strftime(_defaultDateStampFormat))
						self.setIcon(dev,props,"SensorOff-SensorOn",1)

			self.updateRGB(dev, data, props[u"displayS"])

		except Exception, e:
			if self.decideMyLog(u"SensorData"): self.indiLOG.log(40,"Line {} has error={}".format(sys.exc_traceback.tb_lineno, e))



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
				for input in [u"Current"+unicode(jj),"ShuntVoltage"+unicode(jj),"BusVoltage"+unicode(jj)]:
					if input in data:
						if unicode(data[input]).find(u"bad") >-1:
							self.setStatusCol( dev, input, 0,  u"no sensor data - disconnected?", u"Current"+unicode(jj), "","" )
							self.setIcon(dev,props,"SensorOff-SensorOn",0)
							return
						if data[input] !="":
							ss, ssUI, unit = self.addmultOffsetUnit(data[input], dev.pluginProps)
							self.setStatusCol( dev, input, ss, ssUI+unit, whichKeysToDisplay, "","" )
				self.setIcon(dev,props,"SensorOff-SensorOn",1)
		except Exception, e:
			if self.decideMyLog(u"SensorData"): self.indiLOG.log(40,"Line {} has error={}".format(sys.exc_traceback.tb_lineno, e))

####-------------------------------------------------------------------------####
	def updateADC121(self,dev,data,whichKeysToDisplay):
		try:
			input = u"adc"
			props = dev.pluginProps
			xType = props[u"type"]
			pp = {"offset": props[u"offset"],"mult":props[u"mult"], "unit": "ppm","format":"%2d"}

			if unicode(data[input]).find(u"bad") >-1:
					self.addToStatesUpdateDict(dev.id,u"status", u"no sensor data - disconnected?")
					self.setIcon(dev,props,"SensorOff-SensorOn",0)
					return

			self.setIcon(dev,props,"SensorOff-SensorOn",1)
			if input in data:
					if data[input] !="":
						ADC = data[input]
						MaxBits = 4095.	  # 12 bits
						Vcc		= 5000.	  # mVolt max

						if	 xType.find(u"MQ") > -1:
							try:	Vca		= float(dev.props[u"Vca"] )	  # mVolt  at clean Air / calibration
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
							pp["unit"]		="º"
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

						self.setStatusCol( dev, u"value", ss, ssUI+unit, whichKeysToDisplay, "","" )
						self.setStatusCol( dev, u"adc", ADC, unicode(ADC), whichKeysToDisplay,"","" )
		except Exception, e:
			if self.decideMyLog(u"SensorData"): self.indiLOG.log(40,"Line {} has error={}".format(sys.exc_traceback.tb_lineno, e))


####-------------------------------------------------------------------------####
	def updateGYROS(self,dev,data,upState):
		try:
			props = dev.pluginProps
			if unicode(data).find(u"bad") >-1:
					self.addToStatesUpdateDict(dev.id,u"status", u"no sensor data - disconnected?")
					self.setIcon(dev, props, "SensorOff-SensorOn" ,0)
					return
			self.setIcon(dev,props,"SensorOff-SensorOn",1)
			theList = [u"EULER","QUAT", u"MAG","GYR","ACC","LIN","GRAV","ROT"]
			XYZSumSQ = 0
			for input in theList:
				if input not in data: continue
				out=""
				if input ==u"EULER":
					for dim in [u"heading","pitch","roll"]:
						if dim not in data[input]: continue
						if data[input][dim] ==u"":	continue
						ss, ssUI, unit = self.addmultOffsetUnit(data[input][dim], dev.pluginProps)
						out+=ss+","
						self.addToStatesUpdateDict(dev.id,dim,ss)
				else:
					for dim in [u"x","y","z","w","q","r","s"]:
						if dim not in data[input]: continue
						if data[input][dim] ==u"":	continue
						ss, ssUI, unit = self.addmultOffsetUnit(data[input][dim], dev.pluginProps)
						out+=ss+","
						self.addToStatesUpdateDict(dev.id,input+dim,ss)
						if u"XYZSumSQ" in dev.states and (input ==u"GYR" or input ==u"MAG"): 
							XYZSumSQ +=data[input][dim]*data[input][dim]
				if upState == input:
					self.addToStatesUpdateDict(dev.id,u"status", out.strip(u","))

				if u"XYZSumSQ" in dev.states and (input ==u"GYR" or input ==u"MAG"):  
					xys= (u"%7.2f"%math.sqrt(XYZSumSQ)).strip()
					self.addToStatesUpdateDict(dev.id,"XYZSumSQ",xys)
					if upState == "XYZSumSQ":
						self.addToStatesUpdateDict(dev.id,u"status", xys)


			input = "calibration"
			stateName  ="calibration"
			if stateName in dev.states and input in data:
				if data[input] !="": 
					out=""
					for dim in data[input]:
						out += dim+":"+unicode(data[input][dim])+","
					out= out.strip(u",").strip(u" ")
					if	upState == input:
						self.addToStatesUpdateDict(dev.id,u"status",out)
					self.addToStatesUpdateDict(dev.id,stateName,out)

			input	   = "temp"
			stateName  ="Temperature"
			if stateName in dev.states and input in data:
				if data[input] !="": 
					x, UI, decimalPlaces = self.mintoday(data[input])
					if	upState == stateName :
						self.addToStatesUpdateDict(dev.id,u"status",UI)
					self.addToStatesUpdateDict(dev.id,stateName ,x, decimalPlaces= decimalPlaces)

		except Exception, e:
			if self.decideMyLog(u"SensorData"): self.indiLOG.log(40,"Line {} has error={}".format(sys.exc_traceback.tb_lineno, e))


####-------------------------------------------------------------------------####
	def updateDistance(self, dev, data, whichKeysToDisplay):
			#{u"ultrasoundDistance":{u"477759402":{u"distance":1700.3591060638428}}
		try:

			input = u"distance"
			if input in data:
				if unicode(data[input]).find(u"bad") >-1:
					self.addToStatesUpdateDict(dev.id,u"status", u"no sensor data - disconnected?")
					self.setIcon(dev,props,"SensorOff-SensorOn",0)
					return

				props = dev.pluginProps
				units = "cm"
				dist0 = 1.
				offset= 0.
				multiply=1.
				if	   u"dUnits" in props: units  = props[u"dUnits"]
				try:
					if u"offset" in props: offset = float(props[u"offset"])
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
					dist0 = (u"%.1f"%(distR))+ud
				elif units == "m":
					ud = " [m]"
					dist = distR*0.01
					dist0 = (u"%.2f"%(dist))+ud
				elif units == "inches":
					ud = ' "'
					dist = distR*0.3937
					dist0 = (u"%.1f"%(dist))+ud
				elif units == "feet":
					ud = " '"
					dist = distR*0.03280839895
					dist0 = (u"%.2f"%(dist))+ud
				self.setStatusCol(dev, u"distance", dist, dist0, whichKeysToDisplay, u"","", decimalPlaces = 2)

				self.addToStatesUpdateDict(dev.id,"measuredNumber", raw)

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

		except Exception, e:
			if self.decideMyLog(u"SensorData"): self.indiLOG.log(40,"Line {} has error={}".format(sys.exc_traceback.tb_lineno, e))





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
				if ttt== "TRUE"  or ttt ==u"ON"  or ttt == "T" or ttt==u"UP"						: return 1.0	 # true/on	 --> 1
				if ttt== "FALSE" or ttt == "OFF" or ttt == "F" or ttt==u"DOWN" or ttt==  "EXPIRED"	: return 0.0		# false/off --> 0
			except:
				pass
			try:
				xx = ''.join([c for c in val if c in  '-1234567890.'])								# remove non numbers
				lenXX= len(xx)
				if	lenXX > 0:																		# found numbers..if len( ''.join([c for cin xx if c in	'.']) )			  >1	: return "x"		# remove strings that have 2 or more dots " 5.5 6.6"
					if len(''.join([c for c in	xx if c in '-']) )			 >1 : return "x"		# remove strings that have 2 or more -	  u" 5-5 6-6"
					if len( ''.join([c for c  in xx if c in '1234567890']) ) ==0: return "x"		# remove strings that just no numbers, just . amd - eg "abc.xyz- hij"
					if lenXX ==1												: return float(xx)	# just one number
					if xx.find(u"-") > 0										: return "x"		 # reject if "-" is not in first position
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
			dd = unicode(data)
			if u"onOff" in props:
				if props[u"onOff"] == "ON-off":
					if ui ==1.:
						return "1", u"off", u""
					else:
						return "0", u"ON", u""

				if props[u"onOff"] == "on-off":
					if ui ==1.:
						return "1", u"off", u""
					else:
						return "0", u"on", u""

				if props[u"onOff"] == "off-ON":
					if ui ==1.:
						return "1", u"ON", u""
					else:
						return "0", u"off", u""

				if props[u"onOff"] == "off-on":
					if ui ==1.:
						return "1", u"on", u""
					else:
						return "0", u"off", u""

				if props[u"onOff"] == "open-closed":
					if ui ==1.:
						return "1", u"open", u""
					else:
						return "0", u"closed", u""

				if props[u"onOff"] == "closed-open":
					if ui ==1.:
						return "1", u"closed", u""
					else:
						return "0", u"open",  u""

				if props[u"onOff"] == "up-down":
					if ui ==1.:
						return "1", u"up", u""
					else:
						return "0", u"down", u""

				if props[u"onOff"] == "closed-open":
					if ui ==1.:
						return "1", u"closed", u""
					else:
						return "0", u"open", u""

				if props[u"onOff"] == "down-up":
					if ui ==1.:
						return "1", u"down", u""
					else:
						return "0", u"up", u""

			offset = 0.
			mult   = 1.
			if u"offset" in props and props[u"offset"] != "":
				try: 	offset = eval(props[u"offset"])
				except: offset = float(props[u"offset"])

			if u"mult" in props and props[u"mult"] != "":
				try: 	mult = eval(props[u"mult"])
				except: mult = float(props[u"mult"])

			ui = (ui+offset) * mult

			offset2 = 0.
			mult2   = 1.
			if u"offset2" in props and props[u"offset2"] != "":
				try: 	offset2 = eval(props[u"offset2"])
				except: offset2 = float(props[u"offset2"])

			if u"mult2" in props and props[u"mult2"] != "":
				try: 	mult2 = eval(props[u"mult2"])
				except: mult2 = float(props[u"mult2"])

			if u"resistorSensor" in props and props[u"resistorSensor"] != "0":
				feedVolt = float(props[u"feedVolt"])
				feedResistor = float(props[u"feedResistor"])
				if props[u"resistorSensor"] == "ground": # sensor is towards ground
					ui = feedResistor / max(((feedVolt / max(ui, 0.0001)) - 1.), 0.001)
				elif props[u"resistorSensor"] == "V+": # sensor is towards V+
					ui = feedResistor *(feedVolt / max(ui, 0.0001) -1.)

			if u"maxMin" in props and props[u"maxMin"] == "1":
				MAXRange = 100; MINRange = 10
				if u"MAXRange" in props and props[u"MAXRange"] != "" and u"MINRange" in props and props[u"MAXRange"] != "":
					try: 	MAXRange = eval(props[u"MAXRange"])
					except: pass
					try: 	MINRange = eval(props[u"MINRange"])
					except: pass
					ui = (ui - MINRange) / max(MAXRange - MINRange,0001)


			if u"valueOrdivValue" in props and props[u"valueOrdivValue"] == "1/value":
				ui = 11. / max(ui, 0.000001)
				
			if u"logScale" in props and props[u"logScale"] == "1":
					ui = math.log10(max(0.00000001,ui))

			ui = (ui + offset2)*mult2


			dd = unicode(ui)
			if u"unit" in props and props[u"unit"] != "":
				unit = props[u"unit"]
			else:
				unit = ""

			if u"format" in props and props[u"format"] != "":
				ui = props[u"format"] % ui
			else:
				ui = unicode(ui)
		except Exception, e:
			if len(unicode(e)) > 5 :
				self.indiLOG.log(40,"Line {} has error={}".format(sys.exc_traceback.tb_lineno, e))
			ui   = unicode(data)
			unit = ""	   
		return dd, ui, unit


####-------------------------------------------------------------------------####
	def updateLight(self, dev, data, upState,theType=""):
		try:
			if u"illuminance" in data or u"lux" in data or "UV" in data or "UVA" in data or "UVB" in data or "IR" in data or "ambient" in data or "white"  or "visible" in data:
				props =	 dev.pluginProps
				if u"unit" in props: unit = props[u"unit"]
				else:				unit = ""
				if u"format" in props: formatN = props[u"format"]
				else:				   formatN = "%7.2f"
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
						#self.fillMinMaxSensors(dev,state,data[key],decimalPlaces=2)

				if u"red" in data:
					self.updateRGB( dev, data, upState, theType=theType)
			else:
				dev.updateStateImageOnServer(indigo.kStateImageSel.LightSensorOff)

				   
		except Exception, e:
			if len(unicode(e)) > 5 :
				if self.decideMyLog(u"SensorData"): self.indiLOG.log(40,"Line {} has error={}".format(sys.exc_traceback.tb_lineno, e))

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
					if "stateGreen" not in props: dev.updateStateImageOnServer(indigo.kStateImageSel.LightSensorOn)
					if u"illuminance" in dev.states and u"illuminance" not in data:
						il = (-0.32466 * data['red']) + (1.57837 * data['green']) + (-0.73191 * data['blue'])  # fron adafruit
						ilUI = (u"%.1f" % il + "[Lux]").replace(u" ", u"")
						self.setStatusCol(dev, u"illuminance", round(il,1), ilUI, upState, u"",u"",decimalPlaces=1 )
					if u"kelvin" in dev.states:
						k = int(self.calcKelvin(data))
						self.setStatusCol(dev, u"kelvin", k, unicode(k) + u"[ºK]", upState, u"",u"",decimalPlaces=0 )
			if upState == "red/green/blue":
						self.addToStatesUpdateDict(dev.id,"status", u"r/g/b: "+unicode(data['red'])+"/"+unicode(data['green'])+"/"+unicode(data['blue'])+unit )



		except Exception, e:
			if len(unicode(e)) > 5 :
				self.indiLOG.log(40,"Line {} has error={}".format(sys.exc_traceback.tb_lineno, e))

####-------------------------------------------------------------------------####
	def updateRGB2(self, dev, color, data, upState,unit, dispType=""):

		try:
			if color not in dev.states: 
				return 0
			if dispType !="":
				try: 
					delta = abs(dev.states[color] - float(data[color]))
				except:
					delta = 10000
				if delta < 10 ** (-int(dispType)): return 0

				if color =="lux"  or color =="illuminance":	 dispType=2
				self.setStatusCol(dev, color, float(data[color]), color+" "+unicode(data[color])+unit, upState, u"",u"",decimalPlaces=dispType )
				return 1

			if dev.states[color] != unicode(data[color]):
				self.setStatusCol(dev, color, float(data[color]), "color "+unicode(data[color])+unit, upState, u"",u"",decimalPlaces=dispType )
				return 1
			return 0
		except Exception, e:
			if len(unicode(e)) > 5 :
				self.indiLOG.log(40,"Line {} has error={}".format(sys.exc_traceback.tb_lineno, e))
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
			useFormat="{:.1f}"
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
				useFormat ="{:d}"
			else:
				cString = "%."+unicode(self.tempDigits)+"f"
			tempU = (cString % temp).strip()
			return round(temp,self.tempDigits) , tempU + suff,self.tempDigits, useFormat
		except:pass
		return -99, u"",self.tempDigits, useFormat



####-------------------------------------------------------------------------####
	def convHum(self, hum):
		try:
			humU = (u"%3d" %float(hum)).strip()
			return int(float(hum)), humU + u"%",0
		except:
			return -99, u"",0

####-------------------------------------------------------------------------####
	def convGas(self, GasIN, dev, props):
		 #data[u"GasResistance"], data[u"AirQuality"], data[u"GasBaseline"],data["SensorStatus"] 
		try:
			bad = False
			try:
					GasResistance	 = (u"%.0f" % (float(GasIN["GasResistance"])/1000.)).strip()+ u"KOhm"
					GasResistanceInt = int(float(GasIN[u"GasResistance"]))
			except: 
					bad = True
			try:
					AirQuality	  = (u"%.0f "% (float(GasIN["AirQuality"]))).strip()+u"%"
					AirQualityInt = int(float(GasIN[u"AirQuality"]) )
					AirQualityTextItems = props.get("AirQuality0-100ToTextMapping","90=Good/70=Average/55=little bad/40=bad/25=worse/0=very bad").split("/")
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
							#self.indiLOG.log(30,"AirQuality:{}; result:{}; aq {} --> {}".format(AirQuality, ii, AirQualityTextItems, aq))
							break
			except: 
					bad = True
					AirQualityText  =""
			try:
					baseline	  = (u"%.0f" % (float(GasIN[u"GasBaseline"]))).strip()+u"%"
					baselineInt	  = int(float(GasIN[u"GasBaseline"]))
			except: 
					bad = True
			try:
					SensorStatus  = GasIN[u"SensorStatus"]
					if SensorStatus.find("measuring") ==-1:
						AirQuality = SensorStatus
			except: 
					bad = True
				
			if not bad:
				#self.indiLOG.log(30,"{} returning: {} {} {} {} {} {} {} {}".format(dev.name, GasResistanceInt, GasResistance , AirQualityInt, AirQuality, baselineInt, baseline, SensorStatus, AirQualityText))
				return GasResistanceInt, GasResistance , AirQualityInt, AirQuality, baselineInt, baseline, SensorStatus, AirQualityText
			else:
				return "", u"","", u"","", u"", "", ""
		except:
			return "", u"","", u"","", u"", "", ""


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
			beaconUpdatedIds =[]
			updateFINGnow = False
			ln = len(msgs)
			if ln < 1: return beaconUpdatedIds
			dateString = datetime.datetime.now().strftime(_defaultDateStampFormat)

			#######---- update pi-beacon device info
			updatepiIP		= False
			updatepiMAC		= False
			newRPI			= ""
			fromPiU 		= unicode(fromPi)
			fromPiI			= int(fromPi)
			piNReceived		= unicode(piNReceived)
			if self.selectBeaconsLogTimer !={}: 
				for sMAC in self.selectBeaconsLogTimer:
					if piMACSend.find(sMAC[:self.selectBeaconsLogTimer[sMAC]]) ==0:
						self.indiLOG.log(20, u"sel.beacon logging: RPI msg: {}; pi#: {};  {}".format(piMACSend, fromPiU, msgs) )

			##if str(fromPi) =="9": self.indiLOG.log(20, u"testing:  pi#="+fromPiU+	u"  MAC number old: "+self.RPI[fromPiU][u"piMAC"] +"   send: "+piMACSend)

			if self.RPI[fromPiU][u"piMAC"] != piMACSend:
				if self.RPI[fromPiU][u"piMAC"] == u"" or self.RPI[fromPiU][u"piMAC"].find("00:00:") ==0:
					newRPI = self.RPI[fromPiU][u"piMAC"] 
					self.indiLOG.log(20, u"pi#: {};  MAC number change from: {}; to: {}".format(fromPiU, newRPI, piMACSend) )
					self.RPI[fromPiU][u"piMAC"] = piMACSend

				else:
					try:
						existingIndigoId = int(self.RPI[fromPiU][u"piDevId"])
						existingPiDev	 = indigo.devices[existingIndigoId]
						props			 = existingPiDev.pluginProps
						try:
							oldMAC		 = props[u"address"]
						except:
							oldMAC		 = existingPiDev.description

						if oldMAC != piMACSend:	 # should always be !=
							self.indiLOG.log(20, u"trying: to replace , create new RPI for   "+piMACSend+"  "+unicode(props))
							if piMACSend not in self.beacons:
								replaceRPIBeacon =""
								for btest in self.beacons:
									if self.beacons[btest][u"indigoId"] == existingIndigoId:
										replaceRPIBeacon = btest
										break
								if replaceRPIBeacon !="":
									self.beacons[piMACSend] = copy.deepcopy(self.beacons[replaceRPIBeacon])
									del self.beacons[replaceRPIBeacon]
									self.indiLOG.log(20, u" replacing old beacon")
								else:
									self.beacons[piMACSend]					  = copy.deepcopy(_GlobalConst_emptyBeacon) 
									self.beacons[piMACSend][u"ignore"]		  = 0
									self.beacons[piMACSend][u"indigoId"]	  = existingIndigoId
									self.beacons[piMACSend][u"note"]		  = "Pi-"+unicode(fromPiU)
									self.beacons[piMACSend][u"typeOfBeacon"]  = "rPI"
									self.beacons[piMACSend][u"status"]		  = "up" 
								props[u"address"]	  = piMACSend
								props[u"ipNumberPi"]  = ipAddress
								self.deviceStopCommIgnore = time.time()
								existingPiDev.replacePluginPropsOnServer(props)
								existingPiDev = indigo.device[existingIndigoId]
								try:
									existingPiDev.address = piMACSend
									existingPiDev.replaceOnServer()
								except: pass
								self.RPI[fromPiU][u"piMAC"]	 = piMACSend
								self.RPI[fromPiU][u"ipNumberPi"] = ipAddress
								if oldMAC in self.beacons: del self.beacons[oldMAC]
								self.setALLrPiV(u"piUpToDate", [u"updateParamsFTP"])
								self.fixConfig(checkOnly = ["all","rpi"],fromPGM="updateBeaconStates pichanged") # updateBeaconStates # ok only if new MAC for rpi ...
								self.addToStatesUpdateDict(unicode(existingPiDev.id),u"vendorName", self.getVendortName(piMACSend))
							else:
								if self.beacons[piMACSend][u"typeOfBeacon"].lower() !="rpi": 
									pass # let the normal process replace the beacon with the RPI
								else:
									self.RPI[fromPiU][u"piMAC"] = piMACSend
									self.indiLOG.log(20, u"might have failed to replace RPI pi#: {}; piMACSend: {}; , you have to do it manually; beacon with type = rpi already exist ".format(fromPiU, piMACSend) )

					except Exception, e:
							self.indiLOG.log(40,"Line {} has error={}".format(sys.exc_traceback.tb_lineno, e))
							self.indiLOG.log(40,u"failed to replace RPI pi#= {};  piMACSend: {};  you have to do it manually".format(fromPiU, piMACSend) )

				updatepiMAC = True
			if self.RPI[fromPiU][u"piNumberReceived"] != piNReceived:
				self.RPI[fromPiU][u"piNumberReceived"] = piNReceived
				updatepiIP = True
			foundPI = False
			if piMACSend in self.beacons:
				indigoId = self.beacons[piMACSend][u"indigoId"]
				try:
					dev = indigo.devices[indigoId]
				except Exception, e:

					if unicode(e).find(u"timeout waiting") > -1:
						self.indiLOG.log(40,"Line {} has error={}".format(sys.exc_traceback.tb_lineno, e))
						self.indiLOG.log(40,u"communication to indigo is interrupted")
						return beaconUpdatedIds
					if unicode(e).find(u"not found in database") ==-1:
						self.indiLOG.log(40,"Line {} has error={}".format(sys.exc_traceback.tb_lineno, e))
						self.indiLOG.log(40,u"updateBeaconStates beacons dict: "+ unicode(self.beacons[piMACSend]))
					return beaconUpdatedIds

				try:
					if dev.deviceTypeId == "rPI":
						foundPI = True
						if dev.states[u"note"] != "Pi-" + piNReceived:
							dev.updateStateOnServer(u"note", u"Pi-" + piNReceived)
							#self.addToStatesUpdateDict(dev.id,u"note", u"Pi-" + piNReceived)
						self.beacons[piMACSend][u"lastUp"] = time.time()
						self.RPI[piNReceived][u"piDevId"] = dev.id
						if dev.description != "Pi-"+ piNReceived+"-"+ipAddress:
							dev.description = "Pi-"+ piNReceived+"-"+ipAddress
							dev.replaceOnServer()

					else:
						indigo.device.delete(dev)
						self.indiLOG.log(30, u"=== deleting beacon: {} replacing simple beacon with rPi model(1)".format(dev.name.encode("utf8")) )
						del self.beacons[piMACSend]

				except Exception, e:
					if len(unicode(e)) > 5 :
						self.indiLOG.log(40,"Line {} has error={}".format(sys.exc_traceback.tb_lineno, e))
						self.indiLOG.log(40,u"beacons[piMACSend] pi#: {}; Pisend: {}; indigoID: {}; beaconsDict: {}".format(fromPiU,  piMACSend, indigoId, self.beacons[piMACSend] ) )
						if unicode(e).find(u"timeout waiting") > -1:
							self.indiLOG.log(40,"Line {} has error={}".format(sys.exc_traceback.tb_lineno, e))
							self.indiLOG.log(40,u"communication to indigo is interrupted")
							return beaconUpdatedIds
						self.indiLOG.log(40,u"smallErr", text =u" error ok if new / replaced RPI")

					del self.beacons[piMACSend]

			if not foundPI:
				if piMACSend in self.beacons: del self.beacons[piMACSend]
				delDEV = []
				for dev in indigo.devices.iter("props.isRPIDevice"):
					props = dev.pluginProps

					try:
						if props[u"address"] == newRPI and newRPI !="":
							newRPI = "found"
							break

						elif props[u"address"] == piMACSend:
							delDEV.append(dev)
							self.RPI[piNReceived][u"piDevId"] = 0
					except:

						self.indiLOG.log(20, u"device has no address, setting piDevId=0: {}  {} {}".format(dev.name.encode("utf8"), dev.id, unicode(props)) )
						delDEV.append(dev)
						self.RPI[fromPiU][u"piDevId"] = 0

				for devx in delDEV:
					self.indiLOG.log(20, u"===  deleting beacon: {}  replacing simple beacon with rPi model(2)".format(devx.name.encode("utf8")) )
					try:
						indigo.device.delete(devx)
					except:
						pass

				if newRPI != "found":
					self.indiLOG.log(20, u"creating new pi (3.)  -- fromPI: {};   piNR: {};   piMACSend: {};   ipAddress: {} " .format(fromPiU, piNReceived, piMACSend, ipAddress) )
					indigo.device.create(
						protocol		= indigo.kProtocol.Plugin,
						address			= piMACSend,
						name			= "Pi_" + piMACSend,
						description		= "Pi-" + piNReceived+"-"+ipAddress,
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
					except Exception, e:
						if unicode(e).find(u"timeout waiting") > -1:
							self.indiLOG.log(40,"Line {} has error={}".format(sys.exc_traceback.tb_lineno, e))
							self.indiLOG.log(40, u"communication to indigo is interrupted")
							return beaconUpdatedIds
						if unicode(e).find(u"not found in database") ==-1:
							self.indiLOG.log(40,"Line {} has error={}".format(sys.exc_traceback.tb_lineno, e))
							return beaconUpdatedIds
						self.indiLOG.log(40,"Line {} has error={}".format(sys.exc_traceback.tb_lineno, e))
						return beaconUpdatedIds

				dev.updateStateImageOnServer(indigo.kStateImageSel.SensorOn)
				self.addToStatesUpdateDict(dev.id,u"vendorName", self.getVendortName(piMACSend))
				self.addToStatesUpdateDict(dev.id,u"status", u"up")
				self.addToStatesUpdateDict(dev.id,u"note", u"Pi-" + piNReceived)
				self.addToStatesUpdateDict(dev.id,u"TxPowerSet", float(_GlobalConst_emptyrPiProps[u"beaconTxPower"]))
				self.addToStatesUpdateDict(dev.id,u"created", dateString)
				self.addToStatesUpdateDict(dev.id,u"Pi_" + fromPiU.rjust(2,"0")  + "_Signal", 0)
				self.addToStatesUpdateDict(dev.id,u"TxPowerReceived",0)
				self.addToStatesUpdateDict(dev.id,u"pktInfo",0)
				self.executeUpdateStatesDict(onlyDevID=dev.id,calledFrom="updateBeaconStates new rpi")

				self.updatePiBeaconNote[piMACSend] = 1
				self.beacons[piMACSend]							= copy.deepcopy(_GlobalConst_emptyBeacon)
				self.beacons[piMACSend][u"expirationTime"]		= self.secToDown
				self.beacons[piMACSend][u"indigoId"]			= dev.id
				self.beacons[piMACSend][u"updateFING"]			= 0
				self.beacons[piMACSend][u"status"]				= "up"
				self.beacons[piMACSend][u"lastUp"]				= time.time()
				self.beacons[piMACSend][u"note"]				= "Pi-" + piNReceived
				self.beacons[piMACSend][u"typeOfBeacon"]		= "rPI"
				self.beacons[piMACSend][u"created"]				= dateString
				self.RPI[fromPiU][u"piDevId"]					= dev.id  # used to quickly look up the rPI devices in indigo
				self.RPI[fromPiU][u"piNumberReceived"]			= piNReceived
				self.RPI[fromPiU][u"piMAC"]						= piMACSend
				self.setONErPiV(fromPiU,"piUpToDate", [u"updateParamsFTP","rebootSSH"])
				self.fixConfig(checkOnly = ["all","rpi","force"],fromPGM="updateBeaconStates1") # updateBeaconStates # ok only if new MAC for rpi ...


			###########################	 ibeacons ############################
			#### ---- update ibeacon info
			for msg in msgs:
				if False:
					if type(msg) != type([]): return 
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
						try:	rssiOffset = float(self.RPI[fromPiU][u"rssiOffset"] )
						except: rssiOffset = 0
					try:	batteryLevel = msg[6]
					except: batteryLevel = ""
					try:	pktInfo	= msg[7]
					except: pktInfo = 0
				if True:
					if type(msg) != type({}): return 
					mac		= msg["mac"].upper()
					reason	= msg["reason"]
					uuid	= msg["uuid"]
					try:	rssi = float(msg["rssi"])
					except: rssi = -999.
					txPower = msg["txPower"]
					lCount	= msg["count"]
					if rssi ==-999 : 
						txPower=0
					else: 
						try:	rssiOffset = float(self.RPI[fromPiU][u"rssiOffset"] )
						except: rssiOffset = 0
					try:	batteryLevel = msg["batteryLevel"]
					except: batteryLevel = ""
					try:	pktInfo	= msg["pktInfo"]
					except: pktInfo = 0


				if self.selectBeaconsLogTimer !={}: 
					for sMAC in self.selectBeaconsLogTimer:
						if mac.find(sMAC[:self.selectBeaconsLogTimer[sMAC]]) ==0:
							self.indiLOG.log(20, u"sel.beacon logging: newMSG	  -1- :"+mac+"; "+(" ").ljust(36)	 + " pi#="+fromPiU +"; #Msgs="+unicode(lCount).ljust(2)   +";  pktInfo="+unicode(pktInfo).ljust(8)				   +"     rssi="+unicode(rssi).rjust(6)	 + "                      txPow="+unicode(txPower).rjust(6)+" uuid="+ uuid.ljust(44))




				if (len(uuid) > 11 and uuid[:12] in self.beaconsIgnoreUUID) or (mac in self.beacons and self.beacons[mac][u"ignore"] >0 ):
					rj = open(self.indigoPreferencesPluginDir + "rejected/rejects", u"a")
					rj.write("{}  pi: {}; beacon: {} \n".format(dateString, fromPiU, msg))
					rj.close()
					if self.decideMyLog(u"BeaconData"): self.indiLOG.log(10, u" rejected beacon because its in reject family: pi: {}; beacon: {}".format(fromPiU, msg) )
					continue  # ignore certain type of beacons, but only for new ones, old ones must be excluded individually
					####self.indiLOG.log(20, u"pi: "+fromPiU+"  beacon uuid : "+ unicode(msg) )

				if mac not in self.beacons:
					if self.acceptNewiBeacons == 999 or rssi <  self.acceptNewiBeacons:
						self.indiLOG.log(20, u" rejected beacon because do not accept new beacons is on or rssi:{}<{};   pi:{}; beaconMSG:{} ".format(rssi, self.acceptNewiBeacons, fromPiU, msg))
						continue
					else:
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
					except Exception, e:
						if unicode(e).find(u"timeout waiting") > -1:
							self.indiLOG.log(40,"Line {} has error={}".format(sys.exc_traceback.tb_lineno, e))
							self.indiLOG.log(40,u"communication to indigo is interrupted")
							return beaconUpdatedIds
						if unicode(e).find(u"not found in database") ==-1:
							self.indiLOG.log(40,"Line {} has error={}".format(sys.exc_traceback.tb_lineno, e))
							return beaconUpdatedIds
						self.indiLOG.log(40,"Line {} has error={}".format(sys.exc_traceback.tb_lineno, e)   + " indigoId:{}".format(self.beacons[mac][u"indigoId"]))
						self.beacons[mac][u"indigoId"] = 0
				else: # no indigoId found, double check 
					for dev in indigo.devices.iter("props.isBeaconDevice,props.isRPIDevice"):
							props = dev.pluginProps
							if u"address" in props:
								if props[u"address"] == mac:
									if dev.deviceTypeId != "beacon": 
										if self.decideMyLog(u"BeaconData"): self.indiLOG.log(10, u" rejecting new beacon, same mac number already exist for different device type: {}  dev: {}".format(dev.deviceTypeId, dev.name.encode("utf8")))
										continue
									else:
										self.beacons[mac][u"indigoId"] = dev.id
										name = dev.name
										break


				if rssi < self.acceptNewiBeacons and name ==u"" and self.beacons[mac][u"ignore"] >= 0: 
					if self.selectBeaconsLogTimer !={}: 
						for sMAC in self.selectBeaconsLogTimer:
							if mac.find(sMAC[:self.selectBeaconsLogTimer[sMAC]]) ==0:
								self.indiLOG.log(20, u"sel.beacon logging: newMSG rej rssi :"+mac+"; "+("name= empty").ljust(30)  + " pi#="+fromPiU +";  #Msgs="+unicode(lCount).ljust(2)   +";  pktInfo="+unicode(pktInfo).ljust(8)+"                     + rssi="+unicode(rssi).rjust(6)     + "                      txPow="+unicode(txPower).rjust(6)+" uuid="+ uuid.ljust(44))

					continue # to accept new beacon(name=""), signal must be > threshold


				try:
					if name == "":
						self.indiLOG.log(20, u"creating new beacon,  received from pi #  {}/{}:   beacon-{}  UUID: {}".format(fromPiU, piMACSend, mac, uuid) )

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
						except Exception, e:

							if unicode(e).find(u"timeout waiting") > -1:
								self.indiLOG.log(40,"Line {} has error={}".format(sys.exc_traceback.tb_lineno, e))
								self.indiLOG.log(40,u"communication to indigo is interrupted")
								return beaconUpdatedIds
						dev.updateStateImageOnServer(indigo.kStateImageSel.SensorOn)
						self.addToStatesUpdateDict(dev.id,u"vendorName", self.getVendortName(mac))
						self.addToStatesUpdateDict(dev.id,u"status", u"up")
						self.addToStatesUpdateDict(dev.id,u"UUID", uuid)
						self.addToStatesUpdateDict(dev.id,u"note", u"beacon-other")
						self.addToStatesUpdateDict(dev.id,u"created", dateString)
						self.addToStatesUpdateDict(dev.id,u"TxPowerSet", float(_GlobalConst_emptyBeaconProps[u"beaconTxPower"]))

						for iiU in _rpiBeaconList:
							if iiU == fromPiU: continue
							try: self.addToStatesUpdateDict(dev.id,"Pi_"+unicode(iiU).rjust(2,"0")+"_Signal",-999)
							except: pass
						self.addToStatesUpdateDict(dev.id,u"Pi_" + fromPiU.rjust(2,"0")  + "_Signal", int(rssi+rssiOffset))
						self.addToStatesUpdateDict(dev.id,u"TxPowerReceived",float(txPower))
						self.addToStatesUpdateDict(dev.id,u"closestRPI",fromPiI)
						self.addToStatesUpdateDict(dev.id,u"closestRPIText",self.getRPIdevName(fromPiU) )
						self.addToStatesUpdateDict(dev.id,u"closestRPILast",fromPiI)
						self.addToStatesUpdateDict(dev.id,u"closestRPITextLast",self.getRPIdevName(fromPiU) )

						if pktInfo !="": self.addToStatesUpdateDict(dev.id,u"pktInfo",pktInfo)
						self.beacons[mac][u"typeOfBeacon"] = "other"
						self.beacons[mac][u"created"] = dateString
						self.beacons[mac][u"expirationTime"] = self.secToDown
						self.beacons[mac][u"lastUp"] = time.time()
						dev = indigo.devices[u"beacon_" + mac]
						props = dev.pluginProps
						self.executeUpdateStatesDict(onlyDevID=dev.id, calledFrom="updateBeaconStates new beacon")
						self.fixConfig(checkOnly = ["beacon"],fromPGM="updateBeaconStates new beacon") # updateBeaconStates
						if self.newBeaconsLogTimer >0:
							if time.time()> self.newBeaconsLogTimer:
								self.newBeaconsLogTimer =0
							else:
								self.indiLOG.log(20, u"new beacon logging: created:"+unicode(dateString.split(u" ")[1])+" "+mac+" "+ name.ljust(20)+" "+ uuid.ljust(44)+ "  pi#="+fromPiU+ " rssi="+unicode(rssi)+ "  txPower="+unicode(txPower))

				except Exception, e:
					if len(unicode(e)) > 5 :
						self.indiLOG.log(40,"Line {} has error={}".format(sys.exc_traceback.tb_lineno, e))
						if unicode(e).find(u"timeout waiting") > -1:
							self.indiLOG.log(40,u"communication to indigo is interrupted")
							return beaconUpdatedIds
				dev = indigo.devices[name]
				newStates = copy.copy(dev.states)
				props = dev.pluginProps


				self.addToStatesUpdateDict(dev.id,u"updateReason", reason)

				updateSignal = False
				if newStates[u"status"] == "up" and rssi == -999.:	## check for fast down signal ==-999
					piStillUp = "-1"
					ssss =-9999; tttt=-1
					for piU in _rpiBeaconList:
						if piU == fromPiU: continue
						pix = int(piU)
						#if mac ==u"0C:F3:EE:00:66:15" and pix ==0:
						if len(dev.states[u"Pi_"+piU.rjust(2,"0")+"_Time"]) < 18: continue 
						if self.beacons[mac][u"receivedSignals"][pix]["lastSignal"] < 10 or (time.time()- self.beacons[mac][u"receivedSignals"][pix]["lastSignal"]) > 25.: continue # states only get updated > updateSignalValuesSeconds, cant expect better numbers
						if dev.states[u"Pi_"+piU.rjust(2,"0")+"_Signal"] > -500: 
							piStillUp = piU
							ssss = dev.states[u"Pi_"+piU.rjust(2,"0")+"_Signal"]
							tttt = time.time()- self.beacons[mac][u"receivedSignals"][pix]["lastSignal"]
							break
					if self.decideMyLog(u"CAR"): self.indiLOG.log(10, "testing fastdown from pi:"+fromPiU+ "  for:"+mac+";  piStillUp? "+piStillUp+", new sig=-999; oldsig"+ unicode(dev.states[u"Pi_"+fromPiU.rjust(2,"0")+"_Signal"])+"  status:"+ dev.states[u"status"]+ "  lastSig="+unicode(ssss)+"  lastT="+unicode(int(tttt)))

					if piStillUp == "-1":
						updateSignal = True
						if mac != piMACSend: dev.updateStateImageOnServer(indigo.kStateImageSel.SensorOff)	# only for regluar ibeacons..
						newStates = self.addToStatesUpdateDict(dev.id,u"status", u"down",newStates=newStates)
						self.beacons[mac][u"status"] = "down"
						#newStates= self.addToStatesUpdateDict(dev.id,u"pktInfo",pktInfo,newStates=newStates)
						self.beacons[mac][u"updateFING"] = 1
						updateFINGnow = True
						self.beacons[mac][u"lastUp"] = -time.time()
						newStates = self.addToStatesUpdateDict(dev.id,"closestRPI", -1,newStates=newStates)
						if self.setClostestRPItextToBlank: newStates = self.addToStatesUpdateDict(dev.id,"closestRPIText", "",newStates=newStates)
						if u"showBeaconOnMap" in props and props[u"showBeaconOnMap"] in _GlobalConst_beaconPlotSymbols: self.beaconPositionsUpdated =4
					newStates= self.addToStatesUpdateDict(dev.id,u"Pi_" + fromPiU.rjust(2,"0")  + "_Signal", -999,newStates=newStates)



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
						deltaSignalLOG = (rssi + rssiOffset - float(self.beacons[mac][u"receivedSignals"][fromPiI]["rssi"]))
						if self.trackSignalStrengthIfGeaterThan[1] == "i":
							logTRUEfromSignal =	 ( abs(deltaSignalLOG) > self.trackSignalStrengthIfGeaterThan[0]  ) or	(rssi ==-999. and float(self.beacons[mac][u"receivedSignals"][fromPiI]["rssi"]) !=-999)
						else:
							logTRUEfromSignal =	 ( abs(deltaSignalLOG) > self.trackSignalStrengthIfGeaterThan[0]  ) and ( rssi !=-999 and self.beacons[mac][u"receivedSignals"][fromPiI]["rssi"] !=-999)

					except Exception, e:

						self.indiLOG.log(40,"Line {} has error={}".format(sys.exc_traceback.tb_lineno, e))
						logTRUEfromSignal = False

				logTRUEfromChangeOFRPI = False
				if dev.deviceTypeId == "beacon": 
					try:	oldRPI = int(dev.states[u"closestRPI"])
					except: oldRPI =-1

				try:     distCalc = float(dev.states[u"Pi_" + fromPiU.rjust(2,"0")  + "_Distance"])
				except:  distCalc = 99999


				if rssi != -999. :
					if ( self.beacons[mac][u"lastUp"]> -1) :
						self.beacons[mac][u"receivedSignals"][fromPiI]["rssi"]  = rssi
						self.beacons[mac][u"receivedSignals"][fromPiI]["lastSignal"]  = time.time()
						self.beacons[mac][u"lastUp"] = time.time()
						if dev.deviceTypeId in ["beacon","rPI"] : 
							closestRPI = self.findClosestRPI(mac,dev)
							
						if	( time.time()- self.beacons[mac][u"updateWindow"] > self.beacons[mac][ "updateSignalValuesSeconds"] or
							  time.time()- self.beacons[mac][u"receivedSignals"][fromPiI]["lastSignal"] > 100. ):  # ==0 or xx seconds updates for 75 seconds, this RPI msg older than 100 secs then xx secs no update for next time
							self.beacons[mac][u"updateWindow"] = time.time()

						if (dev.deviceTypeId == "beacon" and closestRPI != oldRPI) and self.trackSignalChangeOfRPI:
							logTRUEfromChangeOFRPI = True

						try: newStates[u"Pi_" + fromPiU.rjust(2,"0") + "_Signal"] 
						except: self.indiLOG.log(40,"{} no state {}".format(dev.name.encode("utf8") ,u"Pi_" + fromPiU.rjust(2,"0") + "_Signal"))

						if (self.beacons[mac][u"status"] != "up" or					 # was down now up
							time.time()- self.beacons[mac][u"updateWindow"] < 70 or			 # update for 70 seconds then break 
							newStates[u"Pi_" + fromPiU.rjust(2,"0") + "_Signal"] == -999 or	# was down now up
							abs(newStates[u"Pi_" + fromPiU.rjust(2,"0")+ "_Signal"] - self.beacons[mac][u"receivedSignals"][fromPiI]["rssi"]) >20 or # signal change large
							(dev.deviceTypeId == "beacon" and closestRPI != newStates[u"closestRPI"])):				   # clostest RPi has changed
								try:
									minTxPower = float(self.beacons[mac][u"beaconTxPower"])
								except:
									minTxPower = 99999.
								updateSignal = True
								newStates = self.addToStatesUpdateDict(dev.id,u"Pi_" + fromPiU.rjust(2,"0") + "_Signal", int(rssi-rssiOffset),newStates=newStates)
								newStates = self.addToStatesUpdateDict(dev.id,u"TxPowerReceived",float(txPower),newStates=newStates)
								txx = float(txPower)
								if minTxPower <	 991.: txx = minTxPower
								distCalc = self.calcDist(  txx, (rssi+rssiOffset) )/ self.distanceUnits
								if dev.deviceTypeId == "beacon"  and distCalc < 300*self.distanceUnits and not ("IgnoreBeaconForClosestToRPI" in props and props[u"IgnoreBeaconForClosestToRPI"] !="0"):
									beaconUpdatedIds.append([fromPiI,dev.id, distCalc])
									self.beacons[mac][u"receivedSignals"][fromPiI]["lastSignal"] = distCalc
								newStates = self.addToStatesUpdateDict(dev.id,u"Pi_" + fromPiU.rjust(2,"0") + "_Distance", distCalc,newStates=newStates ,decimalPlaces=1  )
								newStates = self.addToStatesUpdateDict(dev.id,u"Pi_" + fromPiU.rjust(2,"0") + "_Time", dateString,newStates=newStates)
								if newStates[u"status"] != "up":  
									if mac != piMACSend: dev.updateStateImageOnServer(indigo.kStateImageSel.SensorOn)
									newStates=self.addToStatesUpdateDict(dev.id,u"status", u"up",newStates=newStates)
									self.beacons[mac][u"updateFING"] = 1
									updateFINGnow = True
									self.beacons[mac][u"status"] = "up"
									if u"showBeaconOnMap" in props and props[u"showBeaconOnMap"] in _GlobalConst_beaconPlotSymbols: self.beaconPositionsUpdated =5

						if dev.deviceTypeId == "beacon" or dev.deviceTypeId == "rPI": 
							if closestRPI != dev.states["closestRPI"]:
								if unicode(dev.states[u"closestRPI"]) !="-1":
									self.addToStatesUpdateDict(dev.id,u"closestRPILast", dev.states["closestRPI"])
									self.addToStatesUpdateDict(dev.id,u"closestRPITextLast", dev.states["closestRPIText"])
							newStates = self.addToStatesUpdateDict(dev.id,"closestRPI",     closestRPI,newStates=newStates)
							newStates = self.addToStatesUpdateDict(dev.id,"closestRPIText", self.getRPIdevName((closestRPI)),newStates=newStates)

					self.beacons[mac][u"indigoId"] = dev.id
					if pktInfo !="": newStates= self.addToStatesUpdateDict(dev.id,u"pktInfo",pktInfo,newStates=newStates)

				if rssi != -999. or self.beacons[mac][u"receivedSignals"][fromPiI]["rssi"] != rssi+rssiOffset:
					self.beacons[mac][u"receivedSignals"][fromPiI] = {"rssi":rssi+rssiOffset, "lastSignal":time.time(), "distance":distCalc}

				if mac in self.CARS[u"beacon"]:
					if dev.states[u"status"] != newStates[u"status"] and time.time()- self.startTime > 30:
						self.updateCARS(mac,dev,newStates)

				if uuid != "x-x-x" and uuid !="":
					if u"UUID" in dev.states and uuid != dev.states[u"UUID"]:
						newStates = self.addToStatesUpdateDict(dev.id,u"UUID", uuid,newStates=newStates)
					if dev.deviceTypeId != "rPI":
						dev = indigo.devices[name]
						exName = dev.description
						ok1, un1 = self.mapUUIDtoName(uuid, typeId=dev.deviceTypeId)
						ok2, un2 = self.mapMACtoiPhoneUUID(mac, uuid, typeId=dev.deviceTypeId)
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
										self.deviceStopCommIgnore = time.time()
										dev.replacePluginPropsOnServer(props)
										if self.decideMyLog(u"BeaconData"): self.indiLOG.log(10, " creating UUID for " + name + " " + uuid )
									elif props[u"uuid"] != uuid:
										if self.decideMyLog(u"BeaconData"): self.indiLOG.log(10, "updating UUID for " + name + "from  " + props[u"uuid"] + "  to  "+ uuid)
										props[u"uuid"] = uuid
										self.deviceStopCommIgnore = time.time()
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
									self.deviceStopCommIgnore = time.time()
									dev.replacePluginPropsOnServer(props)
									if self.decideMyLog(u"BeaconData"): self.indiLOG.log(10, u" creating UUID for " + name + " " + uuid)
								elif props[u"uuid"] != uuid:
									if self.decideMyLog(u"BeaconData"): self.indiLOG.log(10, u"updating UUID for " + name + "from " + props[u"uuid"] + " to " + uuid)
									props[u"uuid"] = uuid
									self.deviceStopCommIgnore = time.time()
									dev.replacePluginPropsOnServer(props)

				if updateSignal and "note" in dev.states and dev.states[u"note"].find(u"beacon") >-1:  
					try:
						props=dev.pluginProps
						expirationTime=props[u"expirationTime"]
						update, deltaDistance =self.calcPostion(dev, expirationTime)
						if ( update or (deltaDistance > self.beaconPositionsdeltaDistanceMinForImage) ) and "showBeaconOnMap" in props and props[u"showBeaconOnMap"] in _GlobalConst_beaconPlotSymbols:
							#self.indiLOG.log(20, u"beaconPositionsUpdated; calcPostion:"+name+" pi#="+fromPiU	  +"   deltaDistance:"+ unicode(deltaDistance)	  +"   update:"+ unicode(update)  )
							self.beaconPositionsUpdated =6

					except Exception, e:
						if len(unicode(e)) > 5 :
							self.indiLOG.log(40,"Line {} has error={}".format(sys.exc_traceback.tb_lineno, e))

				if self.newBeaconsLogTimer >0:
						try:
							created = self.getTimetimeFromDateString(dev.states[u"created"]) 
							if created + self.newBeaconsLogTimer > 2*time.time():
								self.indiLOG.log(20, u"new.beacon logging: newMSG	 -2- :"+mac+";  "+name.ljust(36)+ " pi#="+fromPiU +";  #Msgs="+unicode(lCount).ljust(2)	  +";  pktInfo="+unicode(pktInfo).ljust(8)                  + "  rssi="+unicode(rssi).rjust(6)      +"                      txPow="+unicode(txPower).rjust(6)+" cr="+dev.states[u"created"]+" uuid="+ uuid.ljust(44))
							if self.newBeaconsLogTimer < time.time():
								self.indiLOG.log(20, u"new.beacon logging: resetting  newBeaconsLogTimer to OFF")
								self.newBeaconsLogTimer =0
						except Exception, e:
							self.indiLOG.log(40,"Line {} has error={}".format(sys.exc_traceback.tb_lineno, e))

				if self.selectBeaconsLogTimer !={}: 
					for sMAC in self.selectBeaconsLogTimer:
						if mac.find(sMAC[:self.selectBeaconsLogTimer[sMAC]]) ==0:
							self.indiLOG.log(20, u"sel.beacon logging: newMSG     -3- :"+mac+"; "+name.ljust(36)       + " pi#="+fromPiU +";  #Msgs="+unicode(lCount).ljust(2)     +";  pktInfo="+unicode(pktInfo).ljust(8)                    +"       rssi="+unicode(rssi).rjust(6)   + "                        txPow="+unicode(txPower).rjust(6)+" uuid="+ uuid.ljust(44))

				if logTRUEfromChangeOFRPI:
					self.indiLOG.log(20, u"ChangeOfRPI.beacon logging     :"+mac+"  "+name.ljust(36)       + " pi#="+unicode(closestRPI)+" oldpi=" + unicode(oldRPI)+";   #Msgs="+unicode(lCount).ljust(2)    +";   pktInfo="+unicode(pktInfo) + "        rssi="+unicode(rssi).rjust(6)        + "                         txPow="+unicode(txPower).rjust(6))
		  
				if logTRUEfromSignal:
					if abs(deltaSignalLOG)	 > 500 and rssi > -200:
						self.indiLOG.log(20, u"ChangeOfSignal.beacon logging:        "+mac+";  "+name.ljust(36)+ " pi#="+fromPiU     +";  #Msgs="+unicode(lCount).ljust(2)     +";  pktInfo="+unicode(pktInfo).ljust(8)                    +"       rssi="+unicode(rssi).rjust(6)    +" off --> ON            txPow="+unicode(txPower).rjust(6))
					elif abs(deltaSignalLOG) > 500 and rssi < -200:
						self.indiLOG.log(20, u"ChangeOfSignal.beacon logging:        "+mac+";  "+name.ljust(36)+ " pi#="+fromPiU     +";  #Msgs="+unicode(lCount).ljust(2)     +";  pktInfo="+unicode(pktInfo).ljust(8)                    +"       rssi="+unicode(rssi).rjust(6)    +" ON  --> off            txPow="+unicode(txPower).rjust(6))
					else:
						self.indiLOG.log(20, u"ChangeOfSignal.beacon logging:        "+mac+";  "+name.ljust(36)+ " pi#="+fromPiU     +";  #Msgs="+unicode(lCount).ljust(2)     +";  pktInfo="+unicode(pktInfo).ljust(8)                    +"       rssi="+unicode(rssi).rjust(6)    +" new-old_Sig.= "+ unicode(deltaSignalLOG).rjust(5)+ "     txPow="+unicode(txPower).rjust(6))

				self.executeUpdateStatesDict(onlyDevID=dev.id,calledFrom="updateBeaconStates 1") 

			if updatepiIP:
				if self.decideMyLog(u"Logic"): self.indiLOG.log(10, u"trying to update device note   for pi# " + fromPiU)
				if piMACSend in self.beacons:
					if self.beacons[piMACSend][u"indigoId"] != 0:
						try:
							dev = indigo.devices[self.beacons[piMACSend][u"indigoId"]]
							dev.updateStateOnServer(unicode(dev.id),u"note", "PI-" + fromPiU)

						except Exception, e:
							if unicode(e).find(u"timeout waiting") > -1:
								self.indiLOG.log(40,"Line {} has error={}".format(sys.exc_traceback.tb_lineno, e))
								self.indiLOG.log(40,u"communication to indigo is interrupted")
								return beaconUpdatedIds

							self.indiLOG.log(20, u"Could not update device for pi# " + fromPiU)


						############DIST CALCULATION for beacon






			if updateFINGnow: 
				self.updateFING(u"event")

		except Exception, e:

			if unicode(e).find(u"timeout waiting") > -1:
				self.indiLOG.log(40,"Line {} has error={}".format(sys.exc_traceback.tb_lineno, e))
				self.indiLOG.log(40,u"communication to indigo is interrupted")
				return 
			if len(unicode(e)) > 5	and unicode(e).find(u"not found in database") ==-1:
				self.indiLOG.log(40,"Line {} has error={}".format(sys.exc_traceback.tb_lineno, e))
		return beaconUpdatedIds



####-------------------------------------------------------------------------####
	def getRPIdevName(self, closestRPI):
		closestRPIText =""
		if closestRPI != "-1":
			try: closestRPIText = indigo.devices[int(self.RPI[unicode(closestRPI)]["piDevId"])].name
			except: pass
		return closestRPIText


####-------------------------------------------------------------------------####
	####calc distance from received signal and transmitted power assuming Signal ~ Power/r**2---------
	def findClosestRPI(self,mac,deviBeacon):
		try:
			if mac				  not in self.beacons:		return -2
			if u"receivedSignals" not in self.beacons[mac]: return -3
			if u"closestRPI"	  not in deviBeacon.states: return -4
		except:
															return -5
		newMinDist   = 99999.
		currMinDist  = 99999.
		newClosestRPI  = -1
		currClosestRPI = -1

			
		try:
			currClosestRPI	= int(deviBeacon.states[u"closestRPI"])
			if currClosestRPI !=-1	and (time.time() - self.beacons[mac][u"receivedSignals"][currClosestRPI]["lastSignal"]) <70.: # [u"receivedSignals"] =[rssi, timestamp,dist]
				currMinDist	= self.beacons[mac][u"receivedSignals"][currClosestRPI]["distance"]
		except Exception, e: 
			if len(unicode(e)) > 5 :
				self.indiLOG.log(40,"Line {} has error={}".format(sys.exc_traceback.tb_lineno, e))
			currClosestRPI =-1; currMinDist = -9999.



		try:
			for piU in _rpiBeaconList:
				pi = int(piU)
				if self.RPI[piU][u"piOnOff"] != "0": 
					bbb = self.beacons[mac][u"receivedSignals"][pi]
					try: # if empty field skip
						if time.time() - bbb["lastSignal"]  < 70.:  # signal recent enough
							if bbb["rssi"] > -300: 
								if bbb["distance"] < newMinDist:
									newMinDist   = bbb["distance"]
									newClosestRPI  = pi
					except:
						pass
			# dont switch if: <	 4 dBm diff and	 not defined then keep current 

			#if deviBeacon.states["note"].find("Pi-") > -1: self.indiLOG.log(20,"checking for clostest RPI- {} {} {} {} ".format(mac, deviBeacon.name, newClosestRPI, newMinDist))

			if abs(newMinDist - currMinDist)  < 2 and  currClosestRPI !=-1: # 
				newClosestRPI = currClosestRPI

		except Exception, e: 
			if len(unicode(e)) > 5 :
				self.indiLOG.log(40,"Line {} has error={}".format(sys.exc_traceback.tb_lineno, e))
		return newClosestRPI

	
#		####calc distance from received signal and transmitted power assuming Signal ~ Power/r**2---------
####-------------------------------------------------------------------------####
	def findClosestRPIForBLEConnect(self, devBLE, pi, dist):
		if self.decideMyLog(u"BLE"): self.indiLOG.log(10, u"findClosestRPIForBLEConnect into   dev:{}, pi:{}, dist:{}".format(devBLE.name.encode("utf8"), pi, dist) )
		if u"closestRPI" not in devBLE.states: return -4

		newMinDist     = 99999.
		currMinDist    = 99999.
		newClosestRPI  = -1
		currClosestRPI = -1

		try:
			currClosestRPI	= int(devBLE.states[u"closestRPI"])
			if currClosestRPI != -1:
				deltaSec = time.time() - self.getTimetimeFromDateString(devBLE.states[u"Pi_"+unicode(currClosestRPI).rjust(2,"0")+"_Time"])
				if deltaSec < 120.:
					currMinDist	= devBLE.states["Pi_"+unicode(currClosestRPI).rjust(2,"0")+"_Distance"]
		except:
			currClosestRPI =-1
			currMinDist = 9999.

		newMinDist    = dist
		newClosestRPI = int(pi)

		activePis = self.getActiveBLERPI(devBLE)
		#indigo.server.log(devBLE.name+ " activePis "+ unicode(activePis))

		try:
			for piU in _rpiBeaconList:
				pix = int(piU)
				if pix not in activePis: 				continue
				if self.RPI[piU][u"piOnOff"] == "0": 	continue
				try: # if empty field skip
					deltaSec = time.time() - self.getTimetimeFromDateString(devBLE.states[u"Pi_"+piU.rjust(2,"0")+"_Time"])
					if deltaSec  < 120.:  # signal recent enough
						if float(devBLE.states["Pi_"+piU.rjust(2,"0")+"_Distance"]) <  newMinDist:
								newMinDist   =  float(devBLE.states["Pi_"+piU.rjust(2,"0")+"_Distance"])
								newClosestRPI  = pix
					if self.decideMyLog(u"BLE"): self.indiLOG.log(10, u"findClosestRPIForBLEConnect loop pi:{}, newClosestRPI:{}, devdist:{}, newDist:{} deltaS:{}".format(piU, newClosestRPI, devBLE.states["Pi_"+piU.rjust(2,"0")+"_Distance"],newMinDist, deltaSec ) )
				except Exception, e: 
					if len(unicode(e)) > 5 :
						self.indiLOG.log(40,"Line {} has error={}".format(sys.exc_traceback.tb_lineno, e) )
			# dont switch if: <	 4 dBm diff and	 not defined then keep current 
			if abs(newMinDist - currMinDist) < 2 and  currClosestRPI !=-1: # 
				newClosestRPI = currClosestRPI
		except Exception, e: 
			if len(unicode(e)) > 5 :
				self.indiLOG.log(40,"Line {} has error={}".format(sys.exc_traceback.tb_lineno, e))
		if self.decideMyLog(u"BLE"): self.indiLOG.log(10, u"findClosestRPIForBLEConnect return w  newClosestRPI:{}".format(newClosestRPI) )
		
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
			###self.indiLOG.log(20, unicode(power)+"  "+ unicode(rssi) +" " +unicode(dist)) 
			return dist

		except	 Exception, e:
			if len(unicode(e)) > 5 :
				self.indiLOG.log(40,"Line {} has error={}".format(sys.exc_traceback.tb_lineno, e))
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
			if	 cmd == "newMessage":
				cmd1 = {u"device": typeId, u"command":cmd, u"startAtDateTime": startAtDateTime}
			elif cmd == "startCalibration":
				cmd1 = {u"device": typeId, u"command":cmd, u"startAtDateTime": startAtDateTime}
			elif cmd == "resetDevice":
				cmd1 = {u"device": typeId, u"command":cmd, u"startAtDateTime": startAtDateTime}
			elif cmd == "getBeaconParameters":
				cmd1 = {u"device": typeId, u"command":cmd, u"startAtDateTime": startAtDateTime}
			else:
				if typeId == "setMCP4725":
					cmd1 = {u"device": typeId, u"command": cmd, u"i2cAddress": i2cAddress, u"values":{u"analogValue":analogValue,"rampTime":rampTime,"pulseUp":pulseUp,"pulseDown": pulseDown,"nPulses":nPulses},"restoreAfterBoot": restoreAfterBoot, u"startAtDateTime": startAtDateTime, u"devId": devId}

				elif typeId == "setPCF8591dac":
					cmd1 = {u"device": typeId, u"command": cmd, u"i2cAddress": i2cAddress, u"values":{u"analogValue":analogValue,"rampTime":rampTime,"pulseUp":pulseUp,"pulseDown": pulseDown,"nPulses":nPulses},"restoreAfterBoot": restoreAfterBoot, u"startAtDateTime": startAtDateTime, u"devId": devId}

				elif typeId == "myoutput":
					cmd1 = {u"device": typeId, u"command": u"myoutput", u"text": text, u"restoreAfterBoot": restoreAfterBoot, u"startAtDateTime": startAtDateTime, u"devId": devId}

				elif typeId == "playSound":
					cmd1 = {u"device": typeId, u"command": cmd, u"soundFile": soundFile, u"startAtDateTime": startAtDateTime, u"devId": devId}

				elif typeId.find(u"OUTPUTgpio") >- 1:
					if cmd == "up" or cmd == "down":
						cmd1 = {u"device": typeId, u"command": cmd, u"pin": GPIOpin, u"restoreAfterBoot": restoreAfterBoot, u"startAtDateTime": startAtDateTime, u"inverseGPIO": inverseGPIO, u"devId": devId}
					elif cmd in[u"pulseUp","pulseDown","continuousUpDown","analogWrite"]:
						cmd1 = {u"device": typeId, u"command": cmd, u"pin": GPIOpin, u"values": {u"analogValue":analogValue,"pulseUp":pulseUp,"pulseDown": pulseDown,"nPulses":nPulses}, u"restoreAfterBoot": restoreAfterBoot, u"startAtDateTime": startAtDateTime, u"inverseGPIO": inverseGPIO, u"devId": devId}
					elif cmd == "disable":
						cmd1 = {u"device": typeId, u"command": cmd, u"pin": GPIOpin, u"devId": devId}

				elif typeId.find(u"OUTPUTi2cRelay") >- 1:
					if cmd == "up" or cmd == "down":
						cmd1 = {u"device": typeId, u"command": cmd, u"pin": GPIOpin, u"restoreAfterBoot": restoreAfterBoot, u"startAtDateTime": startAtDateTime, u"inverseGPIO": inverseGPIO, u"devId": devId, "i2cAddress":i2cAddress}
					elif cmd in[u"pulseUp","pulseDown","continuousUpDown"]:
						cmd1 = {u"device": typeId, u"command": cmd, u"pin": GPIOpin, u"values": {"pulseUp":pulseUp,"pulseDown": pulseDown,"nPulses":nPulses}, u"restoreAfterBoot": restoreAfterBoot, u"startAtDateTime": startAtDateTime, u"inverseGPIO": inverseGPIO, u"devId": devId, "i2cAddress":i2cAddress}
					elif cmd == "disable":
						cmd1 = {u"device": typeId, u"command": cmd, u"pin": GPIOpin, u"devId": devId}

				elif typeId.find(u"display") >- 1:
					if cmd == "up" or cmd == "down":
						cmd1 = {u"device": typeId, u"command": cmd,	 "restoreAfterBoot": restoreAfterBoot, u"devId": devId}

			try: cmds = json.dumps([cmd1])
			except Exception, e:
				self.indiLOG.log(40,"json error for cmds:{}".format(cmd1))
				return

			if self.decideMyLog(u"OutputDevice"): self.indiLOG.log(10,	u"sendGPIOCommand: " + cmds)
			self.sendtoRPI(ip, pi ,cmds, calledFrom="sendGPIOCommand")

		except Exception, e:
			if len(unicode(e)) > 5 :
				self.indiLOG.log(40,"Line {} has error={}".format(sys.exc_traceback.tb_lineno, e))



####-------------------------------------------------------------------------####
	def sendGPIOCommands(self, ip, pi, cmd, GPIOpin, inverseGPIO):
		nCmds = len(cmd)
		cmd1 =[]
		try:
			for kk in range(nCmds):
				if cmd[kk] == "up" or cmd[kk] == "down":
					cmd1.append({u"device": "OUTPUTgpio-1", u"command": cmd[kk], u"pin": GPIOpin[kk], u"inverseGPIO": inverseGPIO[kk]})

			cmds = json.dumps(cmd1)

			if self.decideMyLog(u"OutputDevice"): self.indiLOG.log(10,u"sendGPIOCommand-s-: {}".format(cmds) )
			self.sendtoRPI(ip, pi ,cmds, calledFrom="sendGPIOCommand")

		except Exception, e:
			if len(unicode(e)) > 5 :
				self.indiLOG.log(40,"Line {} has error={}".format(sys.exc_traceback.tb_lineno, e))




			###########################	   UTILITIES  #### START #################


####-------------------------------------------------------------------------####
	def setupFilesForPi(self, calledFrom=""):
		try:
			if time.time() - self.lastsetupFilesForPi < 5: return 
			self.lastsetupFilesForPi = time.time()
			if self.decideMyLog(u"UpdateRPI"): self.indiLOG.log(10, u"updating pi server files called from: {}".format(calledFrom) )

			self.makeBeacons_parameterFile()

			for piU in self.RPI:
				if self.RPI[piU][u"piOnOff"] == "0": continue
				self.makeParametersFile(piU)
				self.makeInterfacesFile(piU)
				self.makeSupplicantFile(piU)

			   
		except Exception, e:
				self.indiLOG.log(40,"Line {} has error={}".format(sys.exc_traceback.tb_lineno, e))
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
				xx6[beacon]	= 1   # offset of uuid-maj-min
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


		out = json.dumps(out)
		f = open(self.indigoPreferencesPluginDir + "all/beacon_parameters", u"w")
		f.write(out)
		f.close()
		if len(out) > 50000:
				self.indiLOG.log(50,"parameter file:\n{}all/beacon_parameters\n has become TOOO BIG, \nplease do menu/ignore individual beacons and reset history.\nyou might also want to switch off accept new ibeacons in config\n".format(self.indigoPreferencesPluginDir) )

		try:
			f = open(self.indigoPreferencesPluginDir + "all/touchFile", u"w")
			f.write(unicode(time.time()))
			f.close()
		except Exception, e:
				self.indiLOG.log(40,"Line {} has error={}".format(sys.exc_traceback.tb_lineno, e))
		return



####-------------------------------------------------------------------------####
	def makeInterfacesFile(self,piU):
		try:
			if self.RPI[piU][u"piOnOff"] == "0": return
			f = open(self.indigoPreferencesPluginDir + "interfaceFiles/interfaces." + piU, u"w")
			f.write(u"source-directory /etc/network/interfaces.d\n")
			f.write(u"auto lo\n")
			f.write(u"iface lo inet loopback\n")
			f.write(u"auto eth0\n")
			f.write(u"allow-hotplug eth0\n")
			f.write(u"iface eth0 inet dhcp\n\n")
			f.write(u"allow-hotplug wlan0\n")
			f.write(u"auto wlan0\n")
			f.write(u"iface wlan0 inet manual\n")
			f.write(u"   wpa-conf /etc/wpa_supplicant/wpa_supplicant.conf\n")
			f.close()
		except Exception, e:
				self.indiLOG.log(40,"Line {} has error={}".format(sys.exc_traceback.tb_lineno, e))
		return

####-------------------------------------------------------------------------####
	def makeSupplicantFile(self,piU):
		try:
			if self.RPI[piU][u"piOnOff"] == "0": return
			f = open(self.indigoPreferencesPluginDir + "interfaceFiles/wpa_supplicant.conf." + piU, u"w")
			f.write(u"ctrl_interface=DIR=/var/run/wpa_supplicant GROUP=netdev\n")
			f.write(u"update_config=1\n")
			f.write(u"country=US\n")
			f.write(u"network={\n")
			f.write('   ssid="' + self.wifiSSID + '"\n')
			f.write('   psk="' + self.wifiPassword + '"\n')
			if self.key_mgmt != "" and self.key_mgmt != "NONE":
				f.write('   key_mgmt="' + self.key_mgmt + '"\n')
			f.write(u"}\n")
			f.close()
		except Exception, e:
				self.indiLOG.log(40,"Line {} has error={}".format(sys.exc_traceback.tb_lineno, e))
		return

####-------------------------------------------------------------------------####
	def makeParametersFile(self, piU,retFile=False):
		try:
				if self.RPI[piU][u"piOnOff"] == "0": return
				out = {}
				pi = int(piU)

				out[u"configured"]		  		  = (datetime.datetime.now()).strftime(_defaultDateStampFormat)
				out[u"rebootWatchDogTime"]		  = self.rebootWatchDogTime
				out[u"GPIOpwm"]					  = self.GPIOpwm
				if pi == self.debugRPI:	out[u"debugRPI"] = 1
				else:					out[u"debugRPI"] = 0
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
				out[u"wifiEth"]					  = self.wifiEth
				out[u"myPiNumber"]				  = piU
				out[u"enableRebootCheck"]		  = self.RPI[piU][u"enableRebootCheck"]
				out[u"rPiCommandPORT"]			  = self.rPiCommandPORT
				out[u"sendToIndigoSecs"]		  = self.RPI[piU][u"sendToIndigoSecs"]
				out[u"deleteHistoryAfterSeconds"] = self.deleteHistoryAfterSeconds
				out[u"enableiBeacons"]			  = self.RPI[piU][u"enableiBeacons"]
				out[u"pressureUnits"]			  = self.pluginPrefs.get(u"pressureUnits", u"hPascal")
				out[u"distanceUnits"]			  = self.pluginPrefs.get(u"distanceUnits", u"1.0")
				out[u"tempUnits"]				  = self.pluginPrefs.get(u"tempUnits", u"C")
				out[u"IPnumberOfRPI"]			  = self.RPI[piU][u"ipNumberPi"]
				out[u"deltaChangedSensor"]		  = self.RPI[piU][u"deltaChangedSensor"]
				out[u"sensorRefreshSecs"]		  = float(self.RPI[piU][u"sensorRefreshSecs"])
				out[u"sendFullUUID"]			  = self.sendFullUUID
				out[u"rebootIfNoMessagesSeconds"]  = self.pluginPrefs.get(u"rebootIfNoMessagesSeconds", 999999999)
				out[u"maxSizeOfLogfileOnRPI"]	  = int(self.pluginPrefs.get(u"maxSizeOfLogfileOnRPI", 10000000))

				try :
					piDeviceExist=False
					try:
						try:	  piID= int(self.RPI[piU][u"piDevId"])
						except:	  piID=0
						if piID !=0: 
							piDev = indigo.devices[piID]
							props = piDev.pluginProps
							piDeviceExist=True
					except Exception, e:
						if unicode(e).find(u"timeout waiting") > -1:
							self.indiLOG.log(40,"Line {} has error={}".format(sys.exc_traceback.tb_lineno, e))
							self.indiLOG.log(40,u"communication to indigo is interrupted")
							return
						if unicode(e).find(u"not found in database") >-1:
							self.indiLOG.log(40,"Line {} has error={}".format(sys.exc_traceback.tb_lineno, e))
							self.indiLOG.log(40,u"RPI:{} devid:{} not in indigo, if RPI justd eleted, it will resolve itself ".format(piU ,piID))
							self.delRPI(pi=piU, calledFrom="makeParametersFile")
							self.updateNeeded += ",fixConfig"
							self.fixConfig(checkOnly = ["all","rpi,force"],fromPGM="makeParametersFile bad rpi") 
						else:	 
							self.indiLOG.log(40,"Line {} has error={}".format(sys.exc_traceback.tb_lineno, e))
							self.indiLOG.log(40,u"RPI: {} error ..  piDevId not set:{}".format(piU ,self.RPI[piU]))
							self.updateNeeded += ",fixConfig"
							self.fixConfig(checkOnly = ["all","rpi"],fromPGM="makeParametersFile2")

					if piDeviceExist: 
						if u"eth0" in props and "wlan0" in props:
							try: 	out[u"wifiEth"] =  {"eth0":json.loads(props[u"eth0"]), "wlan0":json.loads(props[u"wlan0"])}
							except: pass			

						if u"startXonPi" in props:
							try:    out[u"startXonPi"]  = props[u"startXonPi"]
							except: out[u"startXonPi"]  = "leaveAlone"

						if u"typeForPWM" in props:
							try:    out[u"typeForPWM"]  = props[u"typeForPWM"]
							except: out[u"typeForPWM"]  = "GPIO"

						
						if u"timeZone" in props:
							try:    out[u"timeZone"]  = props[u"timeZone"]
							except: out[u"timeZone"]  = "99"

						if u"clearHostsFile" in props:
							try:    out[u"clearHostsFile"]  = props[u"clearHostsFile"]
							except: out[u"clearHostsFile"]  = "0"

						out[u"ifNetworkChanges"]  = "0"
						if u"ifNetworkChanges" in props:
							out[u"ifNetworkChanges"]	=  (props[u"ifNetworkChanges"])

						out[u"addNewOneWireSensors"]  = "0"
						if u"addNewOneWireSensors" in props:
							out[u"addNewOneWireSensors"]	=  (props[u"addNewOneWireSensors"])

						out[u"startWebServerSTATUS"]  = "0"
						if u"startWebServerSTATUS" in props:
							out[u"startWebServerSTATUS"]	=  int(props[u"startWebServerSTATUS"])

						out[u"startWebServerINPUT"]  = "0"
						if u"startWebServerINPUT" in props:
							out[u"startWebServerINPUT"]	=  int(props[u"startWebServerINPUT"])

						out[u"GPIOTypeAfterBoot1"]  = "off"
						if u"GPIOTypeAfterBoot1" in props:
							out[u"GPIOTypeAfterBoot1"]			=  props[u"GPIOTypeAfterBoot1"]

						out[u"GPIOTypeAfterBoot2"]  = "off"
						if u"GPIOTypeAfterBoot2" in props:
							out[u"GPIOTypeAfterBoot2"]			=  props[u"GPIOTypeAfterBoot2"]

						out[u"GPIONumberAfterBoot1"]  = "-1"
						if u"GPIONumberAfterBoot1" in props:
							try:    out[u"GPIONumberAfterBoot1"]	=  int(props[u"GPIONumberAfterBoot1"])
							except: pass
						out[u"GPIONumberAfterBoot2"]  = "-1"
						if u"GPIONumberAfterBoot2" in props:
							try:    out[u"GPIONumberAfterBoot2"]	=  int(props[u"GPIONumberAfterBoot2"])
							except: pass

						out[u"simpleBatteryBackupEnable"]  =  "0"
						if u"simpleBatteryBackupEnable" in props:
							try:	 out[u"simpleBatteryBackupEnable"]	=  int(props[u"simpleBatteryBackupEnable"])
							except: pass
							if out[u"simpleBatteryBackupEnable"]  ==  1:
								out[u"shutdownPinVoltSensor"]  = -1
								if u"shutdownPinVoltSensor" in props:
									try:  out[u"shutdownPinVoltSensor"]	=  int(props[u"shutdownPinVoltSensor"])
									except: pass


								out[u"shutDownPinVetoOutput"]  = -1
								if u"shutDownPinVetoOutput" in props:
									try:	 out[u"shutDownPinVetoOutput"]	=  int(props[u"shutDownPinVetoOutput"])
									except: pass
								out[u"batteryMinPinActiveTimeForShutdown"]  = 99999999999
								if u"batteryMinPinActiveTimeForShutdown" in props:
									try:  out[u"batteryMinPinActiveTimeForShutdown"]	=  int(props[u"batteryMinPinActiveTimeForShutdown"])
									except: pass

								out[u"batteryChargeTimeForMaxCapacity"]  =  2*3600
								if u"batteryChargeTimeForMaxCapacity" in props:
									try:	 out[u"batteryChargeTimeForMaxCapacity"]	=  int(props[u"batteryChargeTimeForMaxCapacity"])
									except: pass
								out[u"batteryCapacitySeconds"]  =  5
								if u"batteryCapacitySeconds" in props:
									try:	 out[u"batteryCapacitySeconds"]	=  int(props[u"batteryCapacitySeconds"])
									except: pass


						out[u"shutDownPinEnable"]  =  "0"
						if u"shutDownPinEnable" in props:
							try:	 out[u"shutDownPinEnable"]	=  int(props[u"shutDownPinEnable"])
							except: pass
							if out[u"shutDownPinEnable"]  ==  1:
								out[u"shutDownPinOutput"]  = -1
								if u"shutDownPinOutput" in props:
									try:	 out[u"shutDownPinOutput"]		=  int(props[u"shutDownPinOutput"])
									except: pass
								out[u"shutdownInputPin"]  = -1
								if u"shutdownInputPin" in props:
									try:  out[u"shutdownInputPin"]		=  int(props[u"shutdownInputPin"])
									except: pass


						out[u"batteryUPSshutdownEnable"]  =  "0"
						if u"batteryUPSshutdownEnable" in props:
							try:	 out[u"batteryUPSshutdownEnable"]	=  int(props[u"batteryUPSshutdownEnable"])
							except: pass
							if out[u"batteryUPSshutdownEnable"]  ==  1:
								out[u"batteryUPSshutdownAtxPercent"]  =  -1
								if u"batteryUPSshutdownAtxPercent" in props:
									try:	 out[u"batteryUPSshutdownAtxPercent"]	=  int(props[u"batteryUPSshutdownAtxPercent"])
									except: pass

								out[u"shutdownSignalFromUPSPin"]  =  -1
								if u"shutdownSignalFromUPSPin" in props:
									try:	 out[u"shutdownSignalFromUPSPin"]	=  int(props[u"shutdownSignalFromUPSPin"])
									except: pass


						if u"display" in props:
							try: out[u"display"]  =	 int(props[u"display"])
							except: pass

						if u"rebootAtMidnight" in props and props[u"rebootAtMidnight"] ==u"0":
							out[u"rebootHour"]			 = -1
						else:	 
							out[u"rebootHour"]			 = self.rebootHour

						if u"sleepAfterBoot" in props and props[u"sleepAfterBoot"] in ["0","5","10","15"]:
							out[u"sleepAfterBoot"]			 = props[u"sleepAfterBoot"]
						else:
							out[u"sleepAfterBoot"]			 = "10"


						out = self.updateSensProps(out, props, u"fanEnable", elseSet="-")
						out = self.updateSensProps(out, props, u"fanGPIOPin", elseSet="-1")
						out = self.updateSensProps(out, props, u"fanTempOnAtTempValue", elseSet="60")
						out = self.updateSensProps(out, props, u"fanTempOffAtTempValue", elseSet="2")
						out = self.updateSensProps(out, props, u"fanTempDevId", elseSet="0")


						out = self.updateSensProps(out, props, u"networkType", elseSet="fullIndigo")
						out = self.updateSensProps(out, props, u"BeaconUseHCINo")
						out = self.updateSensProps(out, props, u"BLEconnectUseHCINo")
						out = self.updateSensProps(out, props, u"BLEconnectMode")
						out = self.updateSensProps(out, props, u"enableMuxI2C")
						out = self.updateSensProps(out, props, u"bluetoothONoff")
						out = self.updateSensProps(out, props, u"useRTC", elseSet="")
						out = self.updateSensProps(out, props, u"pin_webAdhoc")
						out = self.updateSensProps(out, props, u"useRamDiskForLogfiles", elseSet="0")
						out = self.updateSensProps(out, props, u"rebootCommand")
						out = self.updateSensProps(out, props, u"BLEserial", elseSet="sequential")
						out = self.updateSensProps(out, props, u"sendToIndigoSecs")

				except Exception, e:
					self.indiLOG.log(40,"Line {} has error={}".format(sys.exc_traceback.tb_lineno, e))
					return ""



				out[u"rPiRestartCommand"]	 = self.rPiRestartCommand[pi]
				if self.rPiRestartCommand[pi].find(u"reboot") >- 1:
					out[u"reboot"] = datetime.datetime.now().strftime(u"%Y-%m-%d-%H:%M:%S")

				out[u"timeStamp"]  = datetime.datetime.now().strftime(u"%Y-%m-%d-%H:%M:%S")

				self.rPiRestartCommand[pi]= ""


				out[u"sensors"]				 = {}
				for sensor in self.RPI[piU][u"input"]:
					try:
						if sensor not in _GlobalConst_allowedSensors: continue
						if sensor not in self.RPI[piU][u"input"]: continue
						if len(self.RPI[piU][u"input"][sensor]) == 0: continue
						sens={}
						for devIdS in self.RPI[piU][u"input"][sensor]:
							if devIdS == "0" or	 devIdS == "": continue
							try:
								devId = int(devIdS)
								dev = indigo.devices[devId]
							except Exception, e:
								if unicode(e).find(u"timeout waiting") > -1:
									self.indiLOG.log(40,"Line {} has error={}".format(sys.exc_traceback.tb_lineno, e))
									self.indiLOG.log(40,u"communication to indigo is interrupted")
									return
								self.indiLOG.log(40,"Line {} has error={}".format(sys.exc_traceback.tb_lineno, e))
								continue

							if not dev.enabled: continue
							props = dev.pluginProps
							sens[devIdS] = {}

							if u"deviceDefs" in props:
								try:    sens[devIdS] = {u"INPUTS":json.loads(props[u"deviceDefs"])}
								except: pass
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

							for jj in range(27):
								if u"INPUT_"+unicode(jj) in props:
									try:    iiii = int(props[u"INPUT_"+unicode(jj)])
									except: iiii = -1
									if iiii > 0:
										sens[devIdS] = self.updateSensProps(sens[devIdS], props, u"INPUT_"+unicode(jj))

							for jj in range(27):
								if u"OUTPUT_"+unicode(jj) in props:
									try:    iiii = int(props[u"OUTPUT_"+unicode(jj)])
									except: iiii = -1
									if iiii > 0:
										sens[devIdS] = self.updateSensProps(sens[devIdS], props, u"OUTPUT_"+unicode(jj))
							if "noI2cCheck" not in props or  not props["noI2cCheck"]:
								sens[devIdS] = self.updateSensProps(sens[devIdS], props, u"i2cAddress")

							sens[devIdS] = self.updateSensProps(sens[devIdS], props, u"sensorRefreshSecs")
							sens[devIdS] = self.updateSensProps(sens[devIdS], props, u"codeType")
							sens[devIdS] = self.updateSensProps(sens[devIdS], props, u"nBits")
							sens[devIdS] = self.updateSensProps(sens[devIdS], props, u"nInputs")

							sens[devIdS] = self.updateSensProps(sens[devIdS], props, u"incrementIfGT4Signals")
							sens[devIdS] = self.updateSensProps(sens[devIdS], props, u"inverse")
							sens[devIdS] = self.updateSensProps(sens[devIdS], props, u"ignorePinValue")
							sens[devIdS] = self.updateSensProps(sens[devIdS], props, u"distinctTransition")
							sens[devIdS] = self.updateSensProps(sens[devIdS], props, u"resetTimeCheck")
							sens[devIdS] = self.updateSensProps(sens[devIdS], props, u"useWhichGPIO")

							sens[devIdS] = self.updateSensProps(sens[devIdS], props, u"GPIOcsPin")
							sens[devIdS] = self.updateSensProps(sens[devIdS], props, u"GPIOmisoPin")
							sens[devIdS] = self.updateSensProps(sens[devIdS], props, u"GPIOmosiPin")
							sens[devIdS] = self.updateSensProps(sens[devIdS], props, u"GPIOclkPin")
							sens[devIdS] = self.updateSensProps(sens[devIdS], props, u"nWires")
							sens[devIdS] = self.updateSensProps(sens[devIdS], props, u"referenceResistor")
							sens[devIdS] = self.updateSensProps(sens[devIdS], props, u"resistorAt0C")
							sens[devIdS] = self.updateSensProps(sens[devIdS], props, u"hertz50_60")

							sens[devIdS] = self.updateSensProps(sens[devIdS], props, u"rainScaleFactor")
							sens[devIdS] = self.updateSensProps(sens[devIdS], props, u"gpioIn")
							sens[devIdS] = self.updateSensProps(sens[devIdS], props, u"gpioSW1")
							sens[devIdS] = self.updateSensProps(sens[devIdS], props, u"gpioSW2")
							sens[devIdS] = self.updateSensProps(sens[devIdS], props, u"gpioSW5")
							sens[devIdS] = self.updateSensProps(sens[devIdS], props, u"gpioSWP")
							sens[devIdS] = self.updateSensProps(sens[devIdS], props, u"cyclePower")
							sens[devIdS] = self.updateSensProps(sens[devIdS], props, u"sensorMode")
							sens[devIdS] = self.updateSensProps(sens[devIdS], props, u"sendMSGEverySecs")
							sens[devIdS] = self.updateSensProps(sens[devIdS], props, u"dhtType")

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
							sens[devIdS] = self.updateSensProps(sens[devIdS], props, u"displayEnable")
							sens[devIdS] = self.updateSensProps(sens[devIdS], props, u"freeParameter")
							sens[devIdS] = self.updateSensProps(sens[devIdS], props, u"gpioEcho")
							sens[devIdS] = self.updateSensProps(sens[devIdS], props, u"gpioTrigger")
							sens[devIdS] = self.updateSensProps(sens[devIdS], props, u"calibrateSetting")
							sens[devIdS] = self.updateSensProps(sens[devIdS], props, u"recalibrateIfGT")
							sens[devIdS] = self.updateSensProps(sens[devIdS], props, u"setCalibrationFixedValue")
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
							sens[devIdS] = self.updateSensProps(sens[devIdS], props, u"actionPulseBurst")
							sens[devIdS] = self.updateSensProps(sens[devIdS], props, u"actionPulseContinuous")
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
							sens[devIdS] = self.updateSensProps(sens[devIdS], props, u"minEventsinTimeWindowToTriggerBursts")
							sens[devIdS] = self.updateSensProps(sens[devIdS], props, u"inpType")
							sens[devIdS] = self.updateSensProps(sens[devIdS], props, u"bounceTime")
							sens[devIdS] = self.updateSensProps(sens[devIdS], props, u"timeWindowForContinuousEvents")
							sens[devIdS] = self.updateSensProps(sens[devIdS], props, u"mac")
							sens[devIdS] = self.updateSensProps(sens[devIdS], props, u"type")
							sens[devIdS] = self.updateSensProps(sens[devIdS], props, u"INPUTdevId0")
							sens[devIdS] = self.updateSensProps(sens[devIdS], props, u"INPUTdevId1")
							sens[devIdS] = self.updateSensProps(sens[devIdS], props, u"INPUTdevId2")
							sens[devIdS] = self.updateSensProps(sens[devIdS], props, u"INPUTdevId3")
							sens[devIdS] = self.updateSensProps(sens[devIdS], props, u"coincidenceTimeInterval")

							sens[devIdS] = self.updateSensProps(sens[devIdS], props, u"usbPort")
							sens[devIdS] = self.updateSensProps(sens[devIdS], props, u"motorFrequency")
							sens[devIdS] = self.updateSensProps(sens[devIdS], props, u"nContiguousAngles")
							sens[devIdS] = self.updateSensProps(sens[devIdS], props, u"contiguousDeltaValue")
							sens[devIdS] = self.updateSensProps(sens[devIdS], props, u"triggerLast")
							sens[devIdS] = self.updateSensProps(sens[devIdS], props, u"triggerCalibrated")
							sens[devIdS] = self.updateSensProps(sens[devIdS], props, u"sendToIndigoEvery")
							sens[devIdS] = self.updateSensProps(sens[devIdS], props, u"anglesInOneBin")
							sens[devIdS] = self.updateSensProps(sens[devIdS], props, u"measurementsNeededForCalib")
							sens[devIdS] = self.updateSensProps(sens[devIdS], props, u"sendPixelData")
							sens[devIdS] = self.updateSensProps(sens[devIdS], props, u"doNotUseDataRanges")
							sens[devIdS] = self.updateSensProps(sens[devIdS], props, u"minSignalStrength")
							sens[devIdS] = self.updateSensProps(sens[devIdS], props, u"relayType")
							sens[devIdS] = self.updateSensProps(sens[devIdS], props, u"python3")

							self.deviceStopCommIgnore = time.time()
							dev.replacePluginPropsOnServer(props)

						if sens != {}:
							out[u"sensors"][sensor] = sens
							###if self.decideMyLog(u"OfflineRPI"): self.indiLOG.log(10, piU + "  sensor " + unicode(out[u"sensors"][sensor]) )
					except Exception, e:
						self.indiLOG.log(40,"Line {} has error={}".format(sys.exc_traceback.tb_lineno, e))
						self.indiLOG.log(40,unicode(sens))

				out[u"sensorList"] = self.RPI[piU][u"sensorList"]

				out[u"output"]={} 
				for devOut in indigo.devices.iter("props.isOutputDevice"):
					typeId = devOut.deviceTypeId
					if typeId not in _GlobalConst_allowedOUTPUT: 								continue
					if not devOut.enabled: 														continue
					propsOut= devOut.pluginProps
					if u"piServerNumber" in propsOut and propsOut[u"piServerNumber"] != piU:	 continue
					if typeId.find(u"OUTPUTgpio") >-1 or typeId.find(u"OUTPUTi2cRelay") >-1:
						if typeId in self.RPI[piU][u"output"]:
							out[u"output"][typeId] = copy.deepcopy(self.RPI[piU][u"output"][typeId])
					else:
						devIdoutS = unicode(devOut.id)
						i2cAddress =""
						spiAddress =""
						if typeId not in out[u"output"]: out[u"output"][typeId]={}
						out[u"output"][typeId][devIdoutS] = [{}]

						if typeId.find(u"neopixelClock") >-1:
								if self.decideMyLog(u"OutputDevice"): self.indiLOG.log(10,	u" neoPixelClock props:\n{}".format(propsOut) )
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
									if u"ring"+unicode(jj) in propsOut:
										try: theDict[u"rings"].append(int(propsOut[u"ring"+unicode(jj)]))
										except:pass 
								nLEDs = sum(theDict[u"rings"])

								propsOut[u"devTypeLEDs"]		  = unicode(nLEDs)
								propsOut[u"devTypeROWs"]		  = u"1"
								propsOut[u"devType"]			  = u"1x"+unicode(nLEDs)
								theDict[u"speed"]				  = propsOut[u"speed"]
								theDict[u"speedOfChange"]		  = propsOut[u"speedOfChange"]
								theDict[u"GPIOsetA"]			  = propsOut[u"GPIOsetA"]
								theDict[u"GPIOsetB"]			  = propsOut[u"GPIOsetB"]
								theDict[u"GPIOsetC"]			  = propsOut[u"GPIOsetC"]
								theDict[u"GPIOup"]				  = propsOut[u"GPIOup"]
								theDict[u"GPIOdown"]			  = propsOut[u"GPIOdown"]

								out[u"output"][typeId][devIdoutS][0]=  copy.deepcopy(theDict)
								if self.decideMyLog(u"OutputDevice"): self.indiLOG.log(10,	u"neoPixelClock out:\n".format(theDict))

						if typeId.find(u"sundial") >-1:
								out[u"output"][typeId][devIdoutS][0] = self.updateSensProps(out[u"output"][typeId][devIdoutS][0], propsOut, u"updateDownloadEnable")

						if typeId.find(u"setStepperMotor") >-1:
								theDict={}

								if "motorType" in propsOut:
									theDict[u"motorType"]				= propsOut[u"motorType"]
									if propsOut["motorType"].find("unipolar") > -1 or propsOut["motorType"].find("bipolar") > -1:
										theDict[u"pin_CoilA1"]			= propsOut[u"pin_CoilA1"]
										theDict[u"pin_CoilA2"]			= propsOut[u"pin_CoilA2"]
										theDict[u"pin_CoilB1"]			= propsOut[u"pin_CoilB1"]
										theDict[u"pin_CoilB2"]			= propsOut[u"pin_CoilB2"]
									elif propsOut["motorType"].find("DRV8834") > -1:
										theDict[u"pin_Step"]			= propsOut[u"pin_Step"]
										theDict[u"pin_Dir"]				= propsOut[u"pin_Dir"]
										theDict[u"pin_Sleep"]			= propsOut[u"pin_Sleep"]
									elif propsOut["motorType"].find("A4988") > -1:
										theDict[u"pin_Step"]			= propsOut[u"pin_Step"]
										theDict[u"pin_Dir"]				= propsOut[u"pin_Dir"]
										theDict[u"pin_Sleep"]			= propsOut[u"pin_Sleep"]


								out[u"output"][typeId][devIdoutS][0]=  copy.deepcopy(theDict)
								if self.decideMyLog(u"OutputDevice"): self.indiLOG.log(10,	u" neoPixelClock: "+json.dumps(theDict))



						out[u"output"][typeId][devIdoutS][0] = self.updateSensProps(out[u"output"][typeId][devIdoutS][0], propsOut, u"lightSensorOnForDisplay")
						out[u"output"][typeId][devIdoutS][0] = self.updateSensProps(out[u"output"][typeId][devIdoutS][0], propsOut, u"lightSensorForDisplay-DevId-type")
						out[u"output"][typeId][devIdoutS][0] = self.updateSensProps(out[u"output"][typeId][devIdoutS][0], propsOut, u"lightSensorSlopeForDisplay")
						out[u"output"][typeId][devIdoutS][0] = self.updateSensProps(out[u"output"][typeId][devIdoutS][0], propsOut, u"clockLightSet")
						out[u"output"][typeId][devIdoutS][0] = self.updateSensProps(out[u"output"][typeId][devIdoutS][0], propsOut, u"minLightNotOff")
						out[u"output"][typeId][devIdoutS][0] = self.updateSensProps(out[u"output"][typeId][devIdoutS][0], propsOut, u"devType")
						out[u"output"][typeId][devIdoutS][0] = self.updateSensProps(out[u"output"][typeId][devIdoutS][0], propsOut, u"devTypeROWs")
						out[u"output"][typeId][devIdoutS][0] = self.updateSensProps(out[u"output"][typeId][devIdoutS][0], propsOut, u"devTypeLEDs")
						if "noI2cCheck" not in propsOut or  not propsOut["noI2cCheck"]:
							out[u"output"][typeId][devIdoutS][0] = self.updateSensProps(out[u"output"][typeId][devIdoutS][0], propsOut, u"i2cAddress")
						out[u"output"][typeId][devIdoutS][0] = self.updateSensProps(out[u"output"][typeId][devIdoutS][0], propsOut, u"interfaceType")
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
						out[u"output"][typeId][devIdoutS][0] = self.updateSensProps(out[u"output"][typeId][devIdoutS][0], propsOut, u"lightSensorOnForDisplay")
						out[u"output"][typeId][devIdoutS][0] = self.updateSensProps(out[u"output"][typeId][devIdoutS][0], propsOut, u"lightSensorForDisplay-DevId-type")
						out[u"output"][typeId][devIdoutS][0] = self.updateSensProps(out[u"output"][typeId][devIdoutS][0], propsOut, u"lightSensorSlopeForDisplay")
						out[u"output"][typeId][devIdoutS][0] = self.updateSensProps(out[u"output"][typeId][devIdoutS][0], propsOut, u"lightMinDimForDisplay")
						out[u"output"][typeId][devIdoutS][0] = self.updateSensProps(out[u"output"][typeId][devIdoutS][0], propsOut, u"lightMaxDimForDisplay")
						out[u"output"][typeId][devIdoutS][0] = self.updateSensProps(out[u"output"][typeId][devIdoutS][0], propsOut, u"intensity")

						if typeId ==u"display":
							##self.indiLOG.log(20, unicode(propsOut))
							extraPageForDisplay =[]
							#self.indiLOG.log(20, unicode(propsOut))
							for ii in range(10):
								if u"extraPage"+unicode(ii)+u"Line0" in propsOut and "extraPage"+unicode(ii)+"Line1" in propsOut and u"extraPage"+unicode(ii)+u"Color" in propsOut:
									line0 = self.convertVariableOrDeviceStateToText(propsOut[u"extraPage"+unicode(ii)+u"Line0"])
									line1 = self.convertVariableOrDeviceStateToText(propsOut[u"extraPage"+unicode(ii)+u"Line1"])
									color = self.convertVariableOrDeviceStateToText(propsOut[u"extraPage"+unicode(ii)+u"Color"])
									extraPageForDisplay.append([line0,line1,color])
							if len(extraPageForDisplay) > 0: out[u"output"][typeId][devIdoutS][0][u"extraPageForDisplay"]  =	 extraPageForDisplay
							out[u"output"][typeId][devIdoutS][0] = self.updateSensProps(out[u"output"][typeId][devIdoutS][0], propsOut, u"scrollxy")
							out[u"output"][typeId][devIdoutS][0] = self.updateSensProps(out[u"output"][typeId][devIdoutS][0], propsOut, u"scrollSpeed")
							out[u"output"][typeId][devIdoutS][0] = self.updateSensProps(out[u"output"][typeId][devIdoutS][0], propsOut, u"showDateTime")
							out[u"output"][typeId][devIdoutS][0] = self.updateSensProps(out[u"output"][typeId][devIdoutS][0], propsOut, u"scrollxy")
							out[u"output"][typeId][devIdoutS][0] = self.updateSensProps(out[u"output"][typeId][devIdoutS][0], propsOut, u"flipDisplay")
							out[u"output"][typeId][devIdoutS][0] = self.updateSensProps(out[u"output"][typeId][devIdoutS][0], propsOut, u"displayResolution", elseSet="")


						if out[u"output"][typeId][devIdoutS] == [{}]:
							del out[u"output"][typeId][devIdoutS]
					try: 
						if out[u"output"][typeId] == {}:
							del out[u"output"][typeId]
					except Exception, e:
						self.indiLOG.log(30,"creating paramatersfile .. please fix device {}; rpi number wrong {} , outdput dev not linked ?, typeId: {}, out[output]: {}".format(devOut.name, piU, typeId, out[u"output"]))


				out = self.writeJson(out, fName = self.indigoPreferencesPluginDir + u"interfaceFiles/parameters." + piU , fmtOn=self.parametersFileSort )
 
		except Exception, e:
				self.indiLOG.log(40,"Line {} has error={}".format(sys.exc_traceback.tb_lineno, e))
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



####------------------rpi update queue management ----------------------------START
####------------------rpi update queue management ----------------------------START
####------------------rpi update queue management ----------------------------START

####-------------------------------------------------------------------------####
	def startUpdateRPIqueues(self, state, piSelect="all"):
		if state =="start":
			self.laststartUpdateRPIqueues = time.time()
			self.indiLOG.log(10, u"starting UpdateRPIqueues ")
			for piU in self.RPI:
				if self.RPI[piU][u"piOnOff"] != "1": continue
				if piSelect == "all" or piU == piSelect:
						self.startOneUpdateRPIqueue(piU)

		elif state =="restart":
			if (piSelect == "all" and time.time() - self.laststartUpdateRPIqueues > 70) or piSelect != "all":
				self.laststartUpdateRPIqueues = time.time()
				for piU in self.RPI:
					if self.RPI[piU][u"piOnOff"] != "1": continue
					if piSelect == "all" or piU == piSelect:
						if time.time() - self.rpiQueues["lastCheck"][piU] > 100:
							self.stopUpdateRPIqueues(piSelect=piU)
							time.sleep(0.5)
						if  time.time() - self.rpiQueues["lastCheck"][piU] > 100:
							self.startOneUpdateRPIqueue(piU, reason="active messages pending timeout")
						elif self.rpiQueues["state"][piU] != "running":
							self.startOneUpdateRPIqueue(piU, reason="not running")
		return 

####-------------------------------------------------------------------------####
	def startOneUpdateRPIqueue(self, piU, reason=""):

		if self.RPI[piU][u"piOnOff"] != "1": return 
		if piU in self.rpiQueues["state"]:
			if self.rpiQueues["state"][piU] == "running":
				self.indiLOG.log(20, u"no need to start Thread, pi# {} thread already running".format(piU) )
				return 

		self.indiLOG.log(20, u" .. restarting   thread for pi# {}, state was : {} - {}".format(piU, self.rpiQueues["state"][piU], reason) )
		self.rpiQueues["lastCheck"][piU] = time.time()
		self.rpiQueues["state"][piU]	= "start"
		self.sleep(0.1)
		self.rpiQueues["thread"][piU]  = threading.Thread(name=u'self.rpiUpdateThread', target=self.rpiUpdateThread, args=(piU,))
		self.rpiQueues["thread"][piU].start()
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
		self.rpiQueues["reset"][piU]	= True
		return 


####-------------------------------------------------------------------------####
	def sendFilesToPiFTP(self, piU, fileToSend="",endAction="repeatUntilFinished"):
		if time.time() - self.rpiQueues["lastCheck"][piU] > 100 or self.rpiQueues["state"][piU] != "running":
			self.startUpdateRPIqueues("restart", piSelect=piU)
		next = {"pi":piU, "fileToSend":fileToSend, "endAction":endAction, "type":"ftp", "tries":0, "exeTime":time.time()}
		self.removeONErPiV(piU, u"piUpToDate", [fileToSend])
		if self.testIfAlreadyInQ(next,piU): 	return 
		if self.decideMyLog(u"UpdateRPI"): self.indiLOG.log(10, u"FTP adding to update list {}".format(next) )
		self.rpiQueues["data"][piU].put(next)
		return
####-------------------------------------------------------------------------####
	def sshToRPI(self, piU, fileToSend="", endAction="repeatUntilFinished"):
		if time.time() - self.rpiQueues["lastCheck"][piU] > 100:
			self.startUpdateRPIqueues("restart", piSelect=piU)
		next = {"pi":piU, "fileToSend":fileToSend, "endAction":endAction, "type":"ssh", "tries":0, "exeTime":time.time()}
		self.removeONErPiV(piU, u"piUpToDate", [fileToSend])
		if self.testIfAlreadyInQ(next,piU): 	return 
		if self.decideMyLog(u"UpdateRPI"): self.indiLOG.log(10, u"SSH adding to update list {}".format(next) )
		self.rpiQueues["data"][piU].put(next)
		return
####-------------------------------------------------------------------------####
	def resetUpdateQueue(self, piU):
		self.rpiQueues["reset"][piU] = True
		return
####-------------------------------------------------------------------------####
	def testIfAlreadyInQ(self, next, piU):
		currentQueue = list(self.rpiQueues["data"][piU].queue)
		for q in currentQueue:
			if q["pi"] == next["pi"] and q["fileToSend"] == next["fileToSend"]:
				if self.decideMyLog(u"UpdateRPI"): self.indiLOG.log(10, u"FTP NOT adding to update list already presend {}".format(next) )
				return True
		return False

####-------------------------------------------------------------------------####
	def rpiUpdateThread(self,piU):
		try:
			self.rpiQueues["state"][piU] = "running"
			if self.decideMyLog(u"UpdateRPI"): self.indiLOG.log(20, u"rpiUpdateThread starting  for pi# {}".format(piU) )
			while self.rpiQueues["state"][piU] == "running":
				self.rpiQueues["lastCheck"][piU]  = time.time()
				time.sleep(1)
				addBack =[]
				while not self.rpiQueues["data"][piU].empty():
					self.rpiQueues["lastActive"][piU]  = time.time()
					next = self.rpiQueues["data"][piU].get()
					self.rpiQueues["lastData"][piU] = unicode(next)
					##if self.decideMyLog(u"UpdateRPI"): self.indiLOG.log(20, u"reset on/off  update queue for pi#{} .. {}".format(piU, self.rpiQueues["reset"][piU]) )

					if self.RPI[piU][u"piOnOff"] == "0": 		
						if self.decideMyLog(u"UpdateRPI"): self.indiLOG.log(20, u"rpiUpdateThread skipping;  Pi#: {} is OFF".format(piU) )
						self.rpiQueues["reset"][piU] = True
						break
					if self.decideMyLog(u"UpdateRPI"): self.indiLOG.log(20, u"rpiUpdateThread executing  {}".format(next) )
					if piU != unicode(next["pi"]): 			
						if self.decideMyLog(u"UpdateRPI"): self.indiLOG.log(20, u"rpiUpdateThread skipping; pi numbers wrong  {} vs {} ".format(piU, next["pi"]) )
						continue
					if self.RPI[piU][u"piOnOff"] == "0": 		
						if self.decideMyLog(u"UpdateRPI"): self.indiLOG.log(20, u"rpiUpdateThread skipping;  Pi#: {} is OFF".format(piU) )
						continue
					if self.RPI[piU][u"ipNumberPi"] == "": 	
						if self.decideMyLog(u"UpdateRPI"): self.indiLOG.log(20, u"rpiUpdateThread skipping pi#:{}  ip number blank".format(piU)  )
						continue
					if piU in self.rpiQueues["reset"] and self.rpiQueues["reset"][piU]: 
						if self.decideMyLog(u"UpdateRPI"): self.indiLOG.log(20, u"rpiUpdateThread resetting queue data for pi#:{}".format(piU) )
						continue
					try:
						id = int(self.RPI[piU][u"piDevId"])
						if id != 0 and not indigo.devices[id].enabled: 
							self.rpiQueues["reset"][piU] = True
							if self.decideMyLog(u"OfflineRPI"): self.indiLOG.log(20, u"device {} not enabled, no sending to RPI".format(indigo.devices[id].name) )
							continue
					except Exception, e:
						self.indiLOG.log(40,"Line {} has error={}".format(sys.exc_traceback.tb_lineno, e))
						self.indiLOG.log(20,"setting update queue for pi#{} to empty".format(piU))
						self.rpiQueues["reset"][piU] = True

					# time for sending?
					if next["exeTime"] > time.time():
						addBack.append((next)) # no , wait 
						continue
					self.RPIBusy[piU] = time.time()

					if next["type"] =="ftp":
						retCode, text = self.execSendFilesToPiFTP(piU, fileToSend=next["fileToSend"], endAction= next["endAction"])
					else:
						retCode, text = self.execSshToRPI(piU, fileToSend=next["fileToSend"], endAction= next["endAction"])

					if retCode ==0: # all ok?
						self.setRPIonline(piU)
						self.RPI[piU][u"lastMessage"] = time.time()
						continue

					else: # some issues
						next["tries"] +=1
						next["exeTime"]  = time.time()+5

						if 5 < next["tries"] and next["tries"] < 10: # wait a little longer
							if self.decideMyLog(u"UpdateRPI"): self.indiLOG.log(20, u"last updates were not successful wait, then try again")
							next["exeTime"] = time.time()+10

						elif next["tries"] > 9:  # wait a BIT longer before trying again
							if self.decideMyLog(u"OfflineRPI"): self.indiLOG.log(20, u"rPi update delayed due to failed updates rPI# {}".format(piU) )
							self.setRPIonline(piU, new=u"offline")
							next["exeTime"]  = time.time()+20
							next["tries"] = 0

						addBack.append(next)
				try: 	self.rpiQueues["data"][piU].task_done()
				except: pass
				if addBack !=[]:
					for nxt in addBack:
						self.rpiQueues["data"][piU].put(nxt)
				self.rpiQueues["reset"][piU] =False
		except Exception, e:
			self.indiLOG.log(40,"Line {} has error={}".format(sys.exc_traceback.tb_lineno, e))
		self.indiLOG.log(20, u"rpi: {}  update thread stopped, state was:{}".format(piU,self.rpiQueues["state"][piU] ) )
		self.rpiQueues["state"][piU] = "stopped - exiting thread"
		return



####-------------------------------------------------------------------------####
	def execSendFilesToPiFTP(self, piU, fileToSend=u"updateParamsFTP.exp",endAction="repeatUntilFinished"):
		ret =["",""]
		try:
			if self.decideMyLog(u"UpdateRPI"): self.indiLOG.log(20, u"enter  sendFilesToPiFTP #{}  fileToSend:".format(piU, fileToSend) )
			if fileToSend==u"updateParamsFTP.exp": self.newIgnoreMAC = 0
			self.lastUpdateSend = time.time()


			pingR = self.testPing(self.RPI[piU][u"ipNumberPiSendTo"])
			if pingR != 0:
				if self.decideMyLog(u"OfflineRPI") or self.decideMyLog(u"UpdateRPI"): self.indiLOG.log(20,u" pi server # {}  PI# {}    not online - does not answer ping - , skipping update".format(piU, self.RPI[piU][u"ipNumberPiSendTo"]) )
				self.setRPIonline(piU,new="offline")
				return 1, ["ping offline",""]

			prompt = self.getPrompt(piU,fileToSend)

			cmd0 = "/usr/bin/expect '" + self.pathToPlugin + fileToSend + u"'" + u" "
			cmd0+=	self.RPI[piU][u"userIdPi"] + " " + self.RPI[piU][u"passwordPi"]+" " + prompt+" "
			cmd0+=	self.RPI[piU][u"ipNumberPiSendTo"] + " "
			cmd0+=	piU + " '" + self.indigoPreferencesPluginDir + "' '" + self.pathToPlugin + "pi'" + " "+self.expectTimeout

			if self.decideMyLog(u"UpdateRPI"): self.indiLOG.log(20, u"updating pi server config for # {} executing\n{}".format(piU, cmd0) )
			p = subprocess.Popen(cmd0, shell=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
			ret = p.communicate()

			if fileToSend == u"upgradeOpSysSSH.exp" :
				return 0, ret

			if len(ret[1]) > 0:
				ret, ok = self.fixHostsFile(ret, piU)
				if not ok: return 0, ret
				self.indiLOG.log(20, u"return code from fix " + unicode(ret) + u" trying again to configure PI")
				p = subprocess.Popen(cmd0, shell=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
				ret = p.communicate()

			if ret[0][-600:].find(u"sftp> ") > -1:
				if self.decideMyLog(u"UpdateRPI"): self.indiLOG.log(20, u"UpdateRPI seems to have been completed for pi# {}  {}".format(piU, fileToSend) )
				return 0, ["ok",""]
			else:
				self.sleep(2)  # try it again after 2 seconds
				p = subprocess.Popen(cmd0, shell=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
				ret = p.communicate()
				if ret[0][-600:].find(u"sftp> ") > -1:
					if self.decideMyLog(u"UpdateRPI"): self.indiLOG.log(20, u"UpdateRPI seems to have been completed for pi# {}  {}".format(piU, fileToSend) )
					return 0, ["ok",""]
				else:
					self.indiLOG.log(30, u"setup pi response (2) message>>>> \n{}\n<<<<<<".format(ret[0].strip("\n")) )
					self.indiLOG.log(30, u"setup pi response (2) error>>>>>> \n{}\n<<<<<<".format(ret[1].strip("\n")) )
					return 1, ["offline",""]
			return 0, ret
		except Exception, e:
			self.indiLOG.log(40,"Line {} has error={}".format(sys.exc_traceback.tb_lineno, e))
		return 1, ret




####-------------------------------------------------------------------------####
	def execSshToRPI(self, piU, fileToSend="", endAction="repeatUntilFinished"):
		ret=[u"",""]
		try:
			if self.testPing(self.RPI[piU][u"ipNumberPi"]) != 0:
				if self.decideMyLog(u"OfflineRPI") or self.decideMyLog(u"UpdateRPI"): self.indiLOG.log(20, u" pi server # {} PI# {}  not online - does not answer ping - , skipping update".format(piU, self.RPI[piU][u"ipNumberPiSendTo"] ))
				if endAction =="repeatUntilFinished":
					return 1, ret
				else:
					return 0, ret

			if fileToSend in [u"shutdownSSH.exp",u"rebootSSH.exp",u"resetOutputSSH.exp",u"shutdownSSH.exp"]:
				batch =" &"
			else: 
				batch =" "

			prompt = self.getPrompt(piU, fileToSend)

			if fileToSend.find(u"getiBeaconList") >-1: 
				hci="0"
				if fileToSend.find(u"1") >-1:
					hci="1"
				self.indiLOG.log(20, u"getting iBeacon list from PI# {} using hci{} .. this will take > 30 secs".format(piU, hci) )
				ff =fileToSend.replace("0","").replace("1","")
				cmd = "/usr/bin/expect '" + self.pathToPlugin + ff+"' " + " " + self.RPI[piU][u"userIdPi"] + " " + self.RPI[piU][u"passwordPi"] + " " + prompt+  "  "+ self.RPI[piU][u"ipNumberPiSendTo"]+ " "+self.expectTimeout+" hci"+hci

			else:

				cmd = "/usr/bin/expect '" + self.pathToPlugin + fileToSend+"' " + " " + self.RPI[piU][u"userIdPi"] + " " + self.RPI[piU][u"passwordPi"] + " " + prompt+" "+ self.RPI[piU][u"ipNumberPiSendTo"]+ " "+self.expectTimeout+ " "+batch
			if self.decideMyLog(u"UpdateRPI") : self.indiLOG.log(10, fileToSend+u" Pi# {}\n{}".format(piU, cmd) )
			if batch == u" ":
				ret = subprocess.Popen(cmd, shell=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE).communicate()
				if self.decideMyLog(u"UpdateRPI"): self.indiLOG.log(10, u"response: {}".format(ret) )
				if len(ret[1]) > 0:
					ret, ok = self.fixHostsFile(ret,piU)
					if not ok: 
						if endAction =="repeatUntilFinished":
							return 1,ret
						else:
							return 0, ret
					ret = subprocess.Popen(cmd, shell=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE).communicate()

			else:
				ret = subprocess.Popen(cmd, shell=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE).communicate()

			if fileToSend.find(u"shutdown") >-1: 
				return 0, ret

			tag ="\nPi#{} - ".format(piU)

			if len(ret[1]) > 0:
				ret1= ret[1].replace(u"\n\n", u"\n").replace(u"\n", tag)
				self.indiLOG.log(20, "{} Pi# {}  {}".format(fileToSend, piU, ret1) )

			if fileToSend.find(u"getStats") >-1: 
				try:
					ret1= ((ret[0].split(u"===fix==="))[-1]).replace(u"\n\n", u"\n").replace(u"\n", tag)
					self.indiLOG.log(20, u"stats from Pi# {}{}{}{}Stats end ===========".format(piU, tag, ret1, tag ) )
				except:
					self.indiLOG.log(20, u"stats from Pi# {} raw \n {} \n errors:\n{}" .format(piU, ret[0].replace(u"\n\n", u"\n"), ret[1].replace(u"\n\n", u"\n")) )

				return 0, ret

			if fileToSend.find(u"getiBeaconList") >-1: 
				try:
					if ret[0].find("failed: Input/output error")> -1:
						ret1= ret[0].replace(u"\n\n", u"\n").replace(u"\n", tag)
						self.indiLOG.log(20, u"\nibeaconList form Pi# {} error, try with other hci 0/1 channel {}{} {} END ====".format(piU, tag, ret1, tag) )
					else:
						ret1= ((ret[0].split(u"LE Scan ..."))[-1]).split("Killed")[0].replace(u"\n\n", u"\n").replace(u"\n", tag)
						self.indiLOG.log(20, u"\nibeaconList form Pi# {} collected over 20 secs ==============:  {}{}{}ibeaconList  END         ===================================".format(piU, tag, ret1, tag) )
				except:
					self.indiLOG.log(20, u"getiBeaconList from Pi# {} raw \n {} \n errors:\n{}" .format(piU, ret[0].replace(u"\n\n", u"\n"), ret[1].replace(u"\n\n", u"\n")) )

				return 0, ret

			if fileToSend.find(u"getLogFileSSH") >-1: 
				try:	
					ret1= ( ( (ret[0].split(u"tail -1000 /var/log/pibeacon.log"))[1] ).split("echo 'end token' >")[0] ).replace(u"\n\n", u"\n").replace(u"\n", tag)
					self.indiLOG.log(20, u"{}pibeacon logfile from Pi# {}  ==============:  {}{}{}pibeacon logfile  END    ===================================\n".format(tag, piU, tag, ret1,tag) )
				except Exception, e:
					self.indiLOG.log(40,"Line {} has error={}".format(sys.exc_traceback.tb_lineno, e))
					self.indiLOG.log(20, u"pibeacon logfile from Pi# {} raw \n {} \n errors:\n{}" .format(piU, ret[0].replace(u"\n\n", u"\n"), ret[1].replace(u"\n\n", u"\n")) )

				return 0, ret

			return 0, ret

		except Exception, e:
			self.indiLOG.log(40,"Line {} has error={}".format(sys.exc_traceback.tb_lineno, e))
		return 1, ret




####-------------------------------------------------------------------------####
	def getPrompt(self, piU,fileToSend):
		prompt ="assword"
		if self.RPI[piU][u"authKeyOrPassword"] == "login:":
			if fileToSend.find("FTP") >-1:
				prompt ="connect"
			else: 
				prompt ="login:"

		return prompt


####-------------------------------------------------------------------------####
	def fixHostsFile(self, ret, pi):
		try:
			piU = unicode(pi)
			if self.decideMyLog(u"UpdateRPI"): self.indiLOG.log(10, u"setup pi response (1)\n" + unicode(ret))
			if ret[0].find(u".ssh/known_hosts:") > -1:
				if (subprocess.Popen(u"/usr/bin/csrutil status" , shell=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE).communicate()[0].find(u"enabled")) >-1:
					if self.decideMyLog(u"bigErr"): 
						self.indiLOG.log(40,u'ERROR can not update hosts known_hosts file,    "/usr/bin/csrutil status" shows system enabled SIP; please edit manually with \n"nano {}/.ssh/known_hosts"\n and delete line starting with {}'.format(self.RPI[piU][self.MAChome, ipNumberPiSendTo]) )
						self.indiLOG.log(40,u"trying to from within plugin, if it happens again you need to do it manually")
					try:
						f=open(self.MAChome+u'/.ssh/known_hosts',u"r")
						lines= f.readlines()
						f.close()
						f=open(self.MAChome+u'/.ssh/known_hosts',u"w")
						for line in lines:
							if line.find(self.RPI[piU][u"ipNumberPiSendTo"]) >-1:continue
							f.write(line+u"\n")
						f.close()
					except Exception, e:
						self.indiLOG.log(40,"Line {} has error={}".format(sys.exc_traceback.tb_lineno, e))

					return ["",""], False

				fix1 = ret[0].split(u"Offending RSA key in ")
				if len(fix1) > 1:
					fix2 = fix1[1].split(u"\n")[0].strip(u"\n").strip(u"\n")
					fix3 = fix2.split(u":")
					if len(fix3) > 1:
						fixcode = u"/usr/bin/perl -pi -e 's/\Q$_// if ($. == " + fix3[1] + ");' " + fix3[0]
						self.indiLOG.log(40, u"wrong RSA key, trying to fix with: {}".format(fixcode) )
						p = subprocess.Popen(fixcode, shell=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
						ret = p.communicate()
 
		except Exception, e:
			self.indiLOG.log(40,"Line {} has error={}".format(sys.exc_traceback.tb_lineno, e))
		return ret, True

####------------------rpi update queue management ----------------------------END
####------------------rpi update queue management ----------------------------END
####------------------rpi update queue management ----------------------------END



####-------------------------------------------------------------------------####
	def configureWifi(self, pi):
		return
		try:
			self.setupFilesForPi(calledFrom="configureWifi")
		except Exception, e:
			self.indiLOG.log(40,"Line {} has error={}".format(sys.exc_traceback.tb_lineno, e))
		return

####-------------------------------------------------------------------------####
	def testPing(self, ipN):
		try:
			ss = time.time()
			ret = subprocess.call(u"/sbin/ping  -c 1 -W 40 -o " + ipN, shell=True) # send max 2 packets, wait 40 msec   if one gets back stop
			if self.decideMyLog(u"UpdateRPI"): self.indiLOG.log(10, u" sbin/ping  -c 1 -W 40 -o {} return-code: {}".format(ipN, ret) )

			#indigo.server.log(  ipN+"-1  "+ unicode(ret) +"  "+ unicode(time.time() - ss)  )

			if int(ret) ==0:  return 0
			self.sleep(0.1)
			ret = subprocess.call(u"/sbin/ping  -c 1 -W 400 -o " + ipN, shell=True)
			if self.decideMyLog(u"UpdateRPI"): self.indiLOG.log(10, "/sbin/ping  -c 1 -W 400 -o {} ret-code: ".format(ipN, ret) )

			#indigo.server.log(  ipN+"-2  "+ unicode(ret) +"  "+ unicode(time.time() - ss)  )

			if int(ret) ==0:  return 0
			return 1
		except Exception, e:
			self.indiLOG.log(40,"Line {} has error={}".format(sys.exc_traceback.tb_lineno, e))

		#indigo.server.log(  ipN+"-3  "+ unicode(ret) +"  "+ unicode(time.time() - ss)  )
		return 1


####-------------------------------------------------------------------------####
	def printBeaconsIgnoredButton(self, valuesDict=None, typeId=""):

		############## list of beacons in history
		#				  1234567890123456	1234567890123456789012 1234567890 123456 123456789
		#				  75:66:B5:0A:9F:DB beacon-75:66:B5:0A:9   expired		   0	  1346
		self.myLog( text = u"#	defined beacons-------------", mType="pi configuration")
		self.myLog( text = u"#  Beacon MAC        indigoName                 indigoId Status           type    txMin ignore sigDlt minSig    LastUp[s] ExpTime updDelay created   lastStatusChange",  mType=u"pi configuration")
		for status in [u"ignored", u""]:
			for xType in _GlobalConst_typeOfBeacons:
				self.printBeaconInfoLine(status, xType)


####-------------------------------------------------------------------------####
	def printConfig(self):

		self.myLog( text = u" ========== Parameters START ================",  														mType= u"pi configuration")
		self.myLog( text = u"data path used               {}" .format(self.indigoPreferencesPluginDir),  							mType= u"pi configuration")
		self.myLog( text = u"debugLevel Indigo            {}-" .format(self.debugLevel),			   						    	mType= u"pi configuration")
		self.myLog( text = u"debug which Pi#              {} " .format(self.debugRPI),												mType= u"pi configuration")
		self.myLog( text = u"maxSizeOfLogfileOnRPI        {}" .format(self.pluginPrefs.get(u"maxSizeOfLogfileOnRPI", 10000000)),	mType= u"pi configuration")
		self.myLog( text = u"automaticRPIReplacement      {}" .format(self.automaticRPIReplacement),							   	mType= u"pi configuration")
		self.myLog( text = u"myIp Number                  {}" .format(self.myIpNumber),											   	mType= u"pi configuration")
		self.myLog( text = u"port# of indigoWebServer     {}" .format(self.portOfServer),									   		mType= u"pi configuration")
		self.myLog( text = u"indigo UserID                ....{}" .format(self.userIdOfServer[4:]),      					  		mType= u"pi configuration")
		self.myLog( text = u"indigo Password              ....{}" .format(self.passwordOfServer[4:]), 					     		mType= u"pi configuration")
		self.myLog( text = u"WiFi key_mgmt                {}" .format(self.key_mgmt),					   							mType= u"pi configuration")
		self.myLog( text = u"WiFi Password                ....{}" .format(self.wifiPassword[4:]),	      					 		mType= u"pi configuration")
		self.myLog( text = u"WiFi SSID                    {}" .format(self.wifiSSID),					   							mType= u"pi configuration")
		self.myLog( text = u"wifi OFF if ETH0             {}" .format(self.wifiEth),					   							mType= u"pi configuration")
		self.myLog( text = u"Seconds UP to DOWN           {}" .format(self.secToDown),					   							mType= u"pi configuration")
		self.myLog( text = u"enable FINGSCAN interface    {}" .format(self.enableFING),											   	mType= u"pi configuration")
		self.myLog( text = u"rejct Beacons with txPower > {} dbm" .format(self.txPowerCutoffDefault), 						     	mType= u"pi configuration")
		self.myLog( text = u"beacon indigo folder Name    {}" .format(self.iBeaconFolderName),									   	mType= u"pi configuration")
		self.myLog( text = u"accept newiBeacons           {}" .format(self.acceptNewiBeacons),									   	mType= u"pi configuration")
		self.myLog( text = u"accept junk beacons          {}" .format(self.acceptJunkBeacons),									   	mType= u"pi configuration")
		self.myLog( text = u"send Full UUID everytime     {}" .format(self.sendFullUUID),									   		mType= u"pi configuration")
		self.myLog( text = u"distance Units	              {}; 1=m, 0.01=cm , 0.0254=in, 0.3=f, 0.9=y".format(self.distanceUnits), 	mType= u"pi configuration")
		self.myLog( text = u"", 																									mType= u"pi configuration")
		self.myLog( text = u" ========== EXPERT parameters for each PI:----------", 												mType= u"pi configuration")
		self.myLog( text = u"delete History after xSecs   {}" .format(self.deleteHistoryAfterSeconds),								mType= u"pi configuration")
		self.myLog( text = u"collect x secs bf snd        {}" .format(self.sendAfterSeconds), 										mType= u"pi configuration")
		self.myLog( text = u"port# on rPi 4 GPIO commands {}" .format(self.rPiCommandPORT),	   										mType= u"pi configuration")
		self.myLog( text = u" "															  ,	   										mType= u"pi configuration")

		self.myLog( text = u"  # R# 0/1 IP#             beacon-MAC        indigoName                 Pos X,Y,Z    indigoID UserID    Password       If-rPI-Hangs   SensorAttached",mType= u"pi configuration")
		for pi  in range(len(self.RPI)):
			piU = str(pi)

			if self.RPI[piU][u"piDevId"] == 0:	 continue
			try:
				dev = indigo.devices[self.RPI[piU][u"piDevId"]]
			except Exception, e:
				if unicode(e).find(u"timeout waiting") > -1:
					self.indiLOG.log(40,"Line {} has error={}".format(sys.exc_traceback.tb_lineno, e))
					self.indiLOG.log(40, u"communication to indigo is interrupted")
					return

				self.indiLOG.log(40,"Line {} has error={}".format(sys.exc_traceback.tb_lineno, e))
				self.indiLOG.log(40,u"self.RPI[piU][piDevId] not defined for pi: {}".format(piU))
				continue
			line = piU.rjust(3) + " "
			line += self.RPI[piU][u"piNumberReceived"].rjust(2) + u" "
			line += self.RPI[piU][u"piOnOff"].ljust(3) + u" "
			line += self.RPI[piU][u"ipNumberPi"].ljust(15) + u" "
			line += self.RPI[piU][u"piMAC"].rjust(17) + " "
			line += (dev.name).ljust(25) + " "
			if piU  in _rpiBeaconList:
				line += (unicode(dev.states[u"PosX"]).split(u".")[0] + u"," + unicode(dev.states[u"PosY"]).split(u".")[0] + u"," + unicode(dev.states[u"PosZ"]).split(u".")[0]).rjust(10)
			else:
				line+=" ".rjust(10)
			line += unicode(self.RPI[piU][u"piDevId"]).rjust(12) + u" "
			line += self.RPI[piU][u"userIdPi"].ljust(10) + " "
			line += self.RPI[piU][u"passwordPi"].ljust(15)
			line += self.RPI[piU][u"enableRebootCheck"].ljust(14)
			line += unicode(self.RPI[piU][u"sensorList"]).strip(u"[]").ljust(15)
			self.myLog( text = line, mType="pi configuration")



		self.myLog( text = u"", mType="pi configuration")
		if len(self.CARS[u"carId"]) > 0:
			self.myLog( text = u" ==========  CARS =========================", mType="pi configuration")
			self.myLog( text = u"CAR device-------------       HomeS     AwayS    BAT-beacon                     USB-beacon                     KEY0-beacon                    KEY1-beacon                    KEY2-beacon", mType= u"pi configuration")
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
						if beaconId == 0: continue
					except: continue
					if beaconId not in indigo.devices:
						self.indiLOG.log(30," beaconId not in devices:{} ; type: {}; car name:{}".format(beaconId, bNames[nn], carName))
						continue
					beaconDev= indigo.devices[beaconId]
					propsB = beaconDev.pluginProps
					bN[nn] = (beaconDev.name)
					bF[nn]	  = propsB[u"fastDown"]
				homeSince = int(time.time() - self.CARS[u"carId"][dd][u"homeSince"])
				if homeSince > 9999999: homeSince = " "
				awaySince = int(time.time() - self.CARS[u"carId"][dd][u"awaySince"])
				if awaySince > 9999999: awaySince= " "
				homeSince = unicode(homeSince).ljust(7)
				awaySince = unicode(awaySince).ljust(7)
				out =  carName +" "+homeSince+" - "+awaySince
				for n in range(len(bNames)):
					out += " " + bN[n].strip().ljust(30) 
				self.myLog( text = out, mType= u"pi configuration")
				out =  "         ....FastDown".ljust(30)+ " ".ljust(18)
				for n in range(len(bNames)):
					if bF[n] !=" ":
						out += " " + (bF[n]+"[sec]").strip().ljust(30)
					else:
						out += " " + (u" ").ljust(30)

				self.myLog( text = out, mType= u"pi configuration")
			self.myLog( text = u"", mType= u"pi configuration")

		############## list of beacons in history
		#				  1234567890123456	1234567890123456789012 1234567890 123456 123456789
		#				  75:66:B5:0A:9F:DB beacon-75:66:B5:0A:9   expired		   0	  1346
		if True:
			self.myLog( text = u" ==========  defined beacons ==============", mType= "pi configuration")
			self.myLog( text = u"#  Beacon MAC        indigoName                 indigoId Status           type    txMin ignore sigDlt minSig  lastBatteryUpdate/lvl     LastUp[s] ExpTime updDelay lastStatusChange    created ",
					   mType= "pi configuration")
			for status in [u"up", u"down", u"expired"]:
				for cType in _GlobalConst_typeOfBeacons:
					self.printBeaconInfoLine(status, cType)

			self.myLog( text = u"", mType= u"pi configuration")

		if True:
			self.myLog( text = u"update-thread status", mType= "pi configuration")
			self.myLog( text = u"pi# state       lastCheck lastActive   lastData", mType= "pi configuration")
			for ii in range(_GlobalConst_numberOfRPI ):
				piU = unicode(ii)
				self.myLog( text = u"{:3s} {:10s} {:10.1f} {:10.1f}  {}".format( piU, self.rpiQueues["state"][piU], time.time()-self.rpiQueues["lastCheck"][piU], time.time()-self.rpiQueues["lastActive"][piU], self.rpiQueues["lastData"][piU][:99] ),  mType= "pi configuration")
			self.myLog( text = u"", mType= u"pi configuration")



	def printGroups(self):
		############## list groups with members
		if True:
			self.myLog( text = u"", mType= "pi configuration")
			self.myLog( text = u" ========== beacon groups    ================", mType= u"pi configuration")
			self.myLog( text = u" GroupName	 members / counts ",mType= u"pi configuration")

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
				self.myLog( text = " "+ group+u"        "+ unicode(groupMemberNames[group]),mType= u"pi configuration")
				out=u"              "
				out+=u"nHome: "	 + unicode(self.groupStatusList[group][u"nHome"])+u"; "
				out+=u"oneHome: "+ unicode(self.groupStatusList[group][u"oneHome"])+u"; "
				out+=u"allHome: "+ unicode(self.groupStatusList[group][u"allHome"])+u";    "
				out+=u"nAway: "	 + unicode(self.groupStatusList[group][u"nAway"])+u"; "
				out+=u"oneAway: "+ unicode(self.groupStatusList[group][u"oneAway"])+u"; "
				out+=u"allAway: "+ unicode(self.groupStatusList[group][u"allAway"])+u"; "
				out+=u"members: "
				for member in self.groupStatusList[group][u"members"]:
					out+= member+u"; "
				self.myLog( text = out,mType=u"pi configuration")
			self.myLog( text = u"", mType= u"pi configuration")


		############## families of beacons ignore list
		if len(self.beaconsIgnoreUUID) > 0:
			self.myLog( text = u"", mType= u"pi configuration")
			self.myLog( text = u" =========== Ignore this family of beacons with the following first 12 characters in their UUID:", mType= u"pi configuration")

			for uuid in self.beaconsIgnoreUUID:
				self.myLog( text = " "+ uuid, mType=	 u"pi configuration")

		############## iphone UUID list
		if len(self.beaconsUUIDtoIphone) > 0:
			self.myLog( text = u"", mType= u"pi configuration")
			self.myLog( text = u" ======  UUID to device LINKS ==============", mType= u"pi configuration")
			self.myLog( text = u"MAC--------------    IndigoName---------------        UUID-Major-Minor--------------------          nickname--------------------     ConstType",   mType=  u"pi configuration")
			for beacon in self.beaconsUUIDtoIphone:
				if beacon not in self.beacons:			  continue
				if self.beacons[beacon][u"indigoId"] == 0: continue
				try:
					name = indigo.devices[self.beacons[beacon][u"indigoId"]].name
				except Exception, e:
					if unicode(e).find(u"timeout waiting") > -1:
						self.indiLOG.log(40,"Line {} has error={}".format(sys.exc_traceback.tb_lineno, e))
						self.indiLOG.log(40,u"communication to indigo is interrupted")
						return
					continue
				self.myLog( text = "{}  {}    {} {} {}".format( beacon, name.ljust(30), self.beaconsUUIDtoIphone[beacon][0].ljust(45), self.beaconsUUIDtoIphone[beacon][3].ljust(30), self.beaconsUUIDtoIphone[beacon][1].ljust(15) ), mType=  u"pi configuration")

		self.myLog( text = u" ==========  Parameters END ================", mType=  u"pi configuration")


		return 

####-------------------------------------------------------------------------####
	def resetTcpipSocketStatsCALLBACK(self, valuesDict=None, typeId=""):
		self.dataStats={u"startTime":time.time(),"data":{}}


####-------------------------------------------------------------------------####
	def printTCPIPstats(self, all="yes"):

		############## tcpip stats 
		if self.socketServer is not None or True:
			if all == "yes":
					startDate= time.strftime(_defaultDateStampFormat,time.localtime(self.dataStats[u"startTime"]))
					self.myLog( text = u"", mType= "pi TCPIP socket")
					self.myLog( text = u"Stats for RPI-->INDIGO data transfers. Tracking started {}. Report TX errors if time between errors is <{:.0f} Min".format(startDate, self.maxSocksErrorTime/60), mType=	u"pi TCPIP socket")
			self.myLog( text = u"IP              name          type      first               last                    #MSGs       #bytes bytes/MSG  maxBytes  bytes/min   MSGs/min", mType= "pi TCPIP socket")

			### self.dataStats[u"data"][IPN][name][type] = {u"firstTime":time.time(),"lastTime":0,"count":0,"bytes":0}

			secMeasured	  = max(1., (time.time() - self.dataStats[u"startTime"]))
			minMeasured	  = secMeasured/60.
			totBytes = 0.0
			totMsg	 = 0.0
			maxBytes = 0
			for IPN in sorted(self.dataStats[u"data"].keys()):
				if all == "yes" or all==IPN:
					for name  in sorted(self.dataStats[u"data"][IPN].keys()):
						for xType in sorted(self.dataStats[u"data"][IPN][name].keys()):
							if u"maxBytes"	not in self.dataStats[u"data"][IPN][name][xType]:
								self.resetDataStats()
								return 
							FT		= self.dataStats[u"data"][IPN][name][xType][u"firstTime"]
							LT		= self.dataStats[u"data"][IPN][name][xType][u"lastTime"]

							dtFT	= datetime.datetime.fromtimestamp(FT).strftime(_defaultDateStampFormat)
							dtLT	= datetime.datetime.fromtimestamp(LT).strftime(_defaultDateStampFormat)
							bytesN	= self.dataStats[u"data"][IPN][name][xType][u"bytes"]
							bytesT	= unicode(bytesN).rjust(12)
							countN	= self.dataStats[u"data"][IPN][name][xType][u"count"]
							count	= unicode(countN).rjust(9)
							maxBytN = self.dataStats[u"data"][IPN][name][xType][u"maxBytes"]
							maxByt	= unicode(maxBytN).rjust(9)
							totMsg	  += countN
							totBytes  += bytesN
							try:	bytesPerMsg = unicode(int(self.dataStats[u"data"][IPN][name][xType][u"bytes"]/float(self.dataStats[u"data"][IPN][name][xType][u"count"]))).rjust(9)
							except: bytesPerMsg = u" ".rjust(9)

							try:
									bytesPerMin = self.dataStats[u"data"][IPN][name][xType][u"bytes"]/minMeasured
									bytesPerMin	  = (u"%9.1f"% (bytesPerMin)  ).rjust(9)
							except: bytesPerMin = u" ".rjust(9)
							try:
									msgsPerMin	 = self.dataStats[u"data"][IPN][name][xType][u"count"]/minMeasured
									msgsPerMin	 = (u"%9.2f"% (msgsPerMin)	).rjust(9)
							except: msgsPerMin	 = u" ".rjust(9)

							maxBytes   = max(maxBytN,maxBytes)

							self.myLog( text = "{} {} {} {} {} {} {} {} {}  {}  {}".format(IPN.ljust(15), name.ljust(12), xType.ljust(10), dtFT, dtLT, count, bytesT, bytesPerMsg, maxByt, bytesPerMin, msgsPerMin),mType=" ")
			if all == "yes" and totMsg >0:
				bytesPerMsg	  = unicode(int(totBytes/totMsg)).rjust(9)
				bytesPerMin	  = (u"%9.1f"% (totBytes/minMeasured)  ).rjust(9)
				msgsPerMin	  = (u"%9.2f"% (totMsg/minMeasured)	   ).rjust(9)
				maxBytes	  =	 unicode(maxBytes).rjust(9)
				self.myLog( text = "total                                                                          {:10d}{:13d} {} {}  {}  {}".format(int(totMsg), int(totBytes), bytesPerMsg, maxBytes, bytesPerMin, msgsPerMin ),mType=" ")
				self.myLog( text = u" ===  Stats for RPI --> INDIGO data transfers ==  END total time measured: {:.0f} {} ; min measured: {:.0f}".format( int(time.strftime(u"%d", time.gmtime(secMeasured)))-1, time.strftime(u"%H:%M:%S", time.gmtime(secMeasured)), minMeasured ), mType=	 u"pi TCPIP socket")
		return

####-------------------------------------------------------------------------####
	def printUpdateStats(self,):
		if len(self.dataStats[u"updates"]) ==0: return 
		nSecs = max(1,(time.time()-	 self.dataStats[u"updates"][u"startTime"]))
		nMin  = nSecs/60.
		startDate= time.strftime(_defaultDateStampFormat,time.localtime(self.dataStats[u"updates"][u"startTime"]))
		self.myLog( text = "",mType=" " )
		self.myLog( text = "===    measuring started at: {}".format(startDate), mType="indigo update stats " )
		self.myLog( text = "updates: {:10d};   updates/sec: {:10.2f};   updates/minute: {:10.2f}".format(self.dataStats[u"updates"][u"devs"], self.dataStats[u"updates"][u"devs"] /nSecs, self.dataStats[u"updates"][u"devs"]  /nMin), mType=  u"    device ")
		out = "(#states #updates #updates/min) "
		for ii in range(1,10):
			out+= "({:1d} {:1d} {:3.1f}) ".format(ii, self.dataStats[u"updates"][u"nstates"][ii], self.dataStats[u"updates"][u"nstates"][ii]/nMin) 
		out+= "({:1d} {:1d} {:3.1f})".format(10, self.dataStats[u"updates"][u"nstates"][10], self.dataStats[u"updates"][u"nstates"][10]/nMin) 
		self.myLog( text = "updates: {}".format(out), mType=  u"    #states")
		self.myLog( text = "===	total time measured: {}".format( time.strftime(u"%H:%M:%S", time.gmtime(nSecs)) ), mType= "indigo update stats" )
		return 


####-------------------------------------------------------------------------####
	def printBeaconInfoLine(self, status, xType):

		cc = 0
		for beacon in self.beacons:
			if self.beacons[beacon][u"typeOfBeacon"] != xType: continue
			if self.beacons[beacon][u"status"] 		!= status: continue
			batteryLevelLastUpdate =""
			try:
				dev = indigo.devices[self.beacons[beacon][u"indigoId"]]
				name = dev.name
				props = dev.pluginProps
				lastStatusChange = dev.states["lastStatusChange"]
				if "batteryLevelUUID" in props and props["batteryLevelUUID"].find("batteryLevel") >-1:
					if "batteryLevelLastUpdate" in dev.states: 
						batteryLevelLastUpdate = dev.states[u"batteryLevelLastUpdate"]
						if len(batteryLevelLastUpdate) < 18: batteryLevelLastUpdate = "2000-01-01 00:00:00"
						batteryLevelLastUpdate += "/"+str(dev.states[u"batteryLevel"])
						batteryLevelLastUpdate = batteryLevelLastUpdate.ljust(23)
			except Exception, e:
				if unicode(e).find(u"timeout waiting") > -1:
					self.indiLOG.log(40,"Line {} has error={}".format(sys.exc_traceback.tb_lineno, e))
					self.indiLOG.log(40, u"communication to indigo is interrupted")
					return
				name = " "
				lastStatusChange = " "
			if len(batteryLevelLastUpdate) < 23: batteryLevelLastUpdate =" ".ljust(23)

			cc += 1
			if len(name) > 22: name = name[:21] + ".."
			line = unicode(cc).ljust(2) + " " + beacon + " " + name.ljust(24) + " " +  unicode(self.beacons[beacon][u"indigoId"]).rjust(10) + " "+\
				   self.beacons[beacon][u"status"].ljust(10) + " " + \
				   self.beacons[beacon][u"typeOfBeacon"].rjust(10) + " " + \
				   unicode(self.beacons[beacon][u"beaconTxPower"]).rjust(8) + " " + \
				   unicode(self.beacons[beacon][u"ignore"]).rjust(6) + " " + \
				   unicode(self.beacons[beacon][u"signalDelta"]).rjust(6) + " " + \
				   unicode(self.beacons[beacon][u"minSignalCutoff"]).rjust(6) + " " + \
				   batteryLevelLastUpdate +\
				   unicode(min(999999999,int(time.time() - self.beacons[beacon][u"lastUp"])      ) ).rjust(13) + " " + \
				   unicode(min(999999,   int(self.beacons[beacon][u"expirationTime"])            ) ).rjust(7)  + " " + \
				   unicode(min(9999999,  int(self.beacons[beacon][u"updateSignalValuesSeconds"]) ) ).rjust(8)  + " " + \
				   unicode(self.beacons[beacon][u"created"]).ljust(19) +" "+\
				   lastStatusChange.ljust(19)
			self.myLog( text = line, mType= "pi configuration")

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
						   unicode("-").rjust(23) +\
						   unicode(min(999999999,int(time.time() - self.beacons[beacon][u"lastUp"]))).rjust(13) + " " + \
						   unicode(min(999999,int(self.beacons[beacon][u"expirationTime"]))).rjust(7) + " " + \
						   unicode(min(9999999,int(self.beacons[beacon][u"updateSignalValuesSeconds"]))).rjust(8) + " " + \
						   unicode(self.beacons[beacon][u"created"]).ljust(19)
					self.myLog( text = line, mType=	 u"pi configuration")
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
						   unicode("-").rjust(23) +\
						   unicode(min(999999999,int(time.time() - self.beacons[beacon][u"lastUp"]))).rjust(12) + " " + \
						   unicode(min(999999,int(self.beacons[beacon][u"expirationTime"]))).rjust(7) + " " + \
						   unicode(min(9999999,int(self.beacons[beacon][u"updateSignalValuesSeconds"]))).rjust(8) + " " + \
						   unicode(self.beacons[beacon][u"created"]).ljust(19)
					self.myLog( text = line, mType= "pi configuration")





####-------------------------------------------------------------------------####
	def updateRejectLists(self):
		if "UpdateRPI" in self.debugLevel: deb = "1"
		else: deb =""
		cmd = self.pythonPath + u" '" + self.pathToPlugin + u"updateRejects.py' "+ deb +" & "
		subprocess.call(cmd, shell=True)



	####-----------------
	########################################
	# General Action callback
	######################
	def actionControlUniversal(self, action, dev):
		###### BEEP ######
		if action.deviceAction == indigo.kUniversalAction.Beep:
			# Beep the hardware module (dev) here:
			# ** IMPLEMENT ME **
			indigo.server.log(u"sent \"{}\" beep request not implemented".format(dev.name))

		###### STATUS REQUEST ######
		elif action.deviceAction == indigo.kUniversalAction.RequestStatus:
			# Query hardware module (dev) for its current status here:
			# ** IMPLEMENT ME **
			self.indiLOG.log(20,u"sent \"{}\" status request not implemented".format(dev.name))

	########################################
	# Sensor Action callback
	######################
	def actionControlSensor(self, action, dev):
		if dev.address in self.beacons:
			self.beacons[dev.address][u"lastUp"] = time.time()
		elif "note" in dev.states and dev.states["note"].find("Pi") ==0:
			pi= dev.states["note"].split("-")[1]
			self.RPI[piU][u"lastMessage"]=time.time()
		elif dev.deviceTypeId =="BLEconnect":
			self.addToStatesUpdateDict(dev.id,"lastUp",datetime.datetime.now().strftime(_defaultDateStampFormat))

		###### TURN ON ######
		if action.sensorAction == indigo.kSensorAction.TurnOn:
			self.addToStatesUpdateDict(dev.id,u"status", u"up")

		###### TURN OFF ######
		elif action.sensorAction == indigo.kSensorAction.TurnOff:
			self.addToStatesUpdateDict(dev.id,u"status", u"down")

		###### TOGGLE ######
		elif action.sensorAction == indigo.kSensorAction.Toggle:
			if dev.onState: 
				self.addToStatesUpdateDict(dev.id,u"status", "down")
				dev.updateStateImageOnServer(indigo.kStateImageSel.PowerOff)
			else:
				self.addToStatesUpdateDict(dev.id,u"status", "up")

		self.executeUpdateStatesDict()

##############################################################################################

####-------------------------------------------------------------------------####


	def addToStatesUpdateDict(self,devId,key,value,newStates="",decimalPlaces="",uiValue="", force=False):
		devId=unicode(devId)
		try:
			try:

				for ii in range(5):
					if	self.executeUpdateStatesDictActive =="":
						break
					self.sleep(0.05)
				self.executeUpdateStatesDictActive = devId+"-add"


				if devId not in self.updateStatesDict: 
					self.updateStatesDict[devId]={}
				if key in self.updateStatesDict[devId]:
					if value != self.updateStatesDict[devId][key]["value"]:
						self.updateStatesDict[devId][key] = {}
						if newStates !="":
							newStates[key] = {}
				self.updateStatesDict[devId][key] = {"value":value,"decimalPlaces":decimalPlaces,"force":force,"uiValue":uiValue}
				if newStates !="": newStates[key] = value

			except Exception, e:
				if	unicode(e).find(u"UnexpectedNullErrorxxxx") >-1: return newStates
				self.indiLOG.log(40,"Line {} has error={}".format(sys.exc_traceback.tb_lineno, e)   )

			#self.updateStatesDict = local	  
		except Exception, e:
			if	unicode(e).find(u"UnexpectedNullErrorxxxx") >-1: return newStates
			self.indiLOG.log(40,"Line {} has error={}".format(sys.exc_traceback.tb_lineno, e))
		self.executeUpdateStatesDictActive = ""
		return newStates

####-------------------------------------------------------------------------####
	def executeUpdateStatesDict(self,onlyDevID="0",calledFrom=""):
		try:
			if len(self.updateStatesDict) ==0: return
			#if "1929700622" in self.updateStatesDict: self.indiLOG.log(10, u"executeUpdateStatesList calledfrom: "+calledFrom +"; onlyDevID: " +onlyDevID +"; updateStatesList: " +unicode(self.updateStatesDict))
			onlyDevID = unicode(onlyDevID)

			for ii in range(5):
				if	self.executeUpdateStatesDictActive =="":
					break
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
						self.sleep(0.05)
				self.updateStatesDict={} 

			elif onlyDevID in self.updateStatesDict:
				for ii in range(5):
					try: 
						local = {onlyDevID: copy.deepcopy(self.updateStatesDict[onlyDevID])}
						break
					except Exception, e:
						self.sleep(0.05)

				try: 
					del self.updateStatesDict[onlyDevID]
				except Exception, e:
					pass
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
			for devId in local:
				if onlyDevID !="0" and onlyDevID != devId: continue
				if len(local) > 0:
					dev =indigo.devices[int(devId)]
					nKeys =0
					for key in local[devId]:
						value = local[devId][key]["value"]
						if key not in dev.states and key != "lastSensorChange":
							self.indiLOG.log(20, u"executeUpdateStatesDict: key: {}  not in states for dev:{}".format(key, dev.name) )
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
										upd=True
							if upd:
								nKeys +=1
								if devId not in changedOnly: changedOnly[devId]={}
								changedOnly[devId][key] = {"value":local[devId][key]["value"], "decimalPlaces":local[devId][key]["decimalPlaces"], "uiValue":local[devId][key]["uiValue"]}
								if "lastSensorChange" in dev.states and "lastSensorChange" not in changedOnly[devId]:
									nKeys +=1
									changedOnly[devId]["lastSensorChange"] = {"value":dateString,"decimalPlaces":"","uiValue":""}

					##if dev.name =="b-radius_3": self.indiLOG.log(10,	u"changedOnly "+unicode(changedOnly))
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
											if	self.enableBroadCastEvents == "all" or	("enableBroadCastEvents" in props and props[u"enableBroadCastEvents"] == "1" ):
												msg = {"action":"event", "id":unicode(dev.id), "name":dev.name, "state":"status", "valueForON":"up", "newValue":st}
												if self.decideMyLog(u"BC"): self.indiLOG.log(10, u"executeUpdateStatesDict msg added :" + unicode(msg))
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
									devnamechangedStat	 = dev.name+ u"     "+key+ u"    old="+unicode(dev.states[key])+ u"     new="+unicode(changedOnly[devId][key]["value"])
								if key ==u"closestRPI": 
									trigRPIchanged		 = dev.name
									devnamechangedRPI	 = dev.name+ u"     "+key+ u"    old="+unicode(dev.states[key])+ u"     new="+unicode(changedOnly[devId][key]["value"]) 

						##if dev.name =="b-radius_3": self.indiLOG.log(10,	u"chList "+unicode(chList))

						self.execUpdateStatesList(dev,chList)

				if trigStatus !="":
					try:
						indigo.variable.updateValue(self.ibeaconNameDefault+u"With_Status_Change",trigStatus)
					except Exception, e:
							self.indiLOG.log(40,u"status changed: {}".format(devnamechangedStat.encode("utf8")))
							self.indiLOG.log(40,"Line {} has error={}".format(sys.exc_traceback.tb_lineno, e)   + u" trying again")
							time.sleep(0.5)
							indigo.variable.updateValue(self.ibeaconNameDefault+u"With_Status_Change",trigStatus)
							self.indiLOG.log(40, u"worked 2. time")
					self.triggerEvent(u"someStatusHasChanged")

				if trigRPIchanged !="":
					try:
						indigo.variable.updateValue(self.ibeaconNameDefault+u"With_ClosestRPI_Change",trigRPIchanged)
					except Exception, e:
							self.indiLOG.log(40,u"RPI   changed: {}".format(devnamechangedRPI.encode("utf8")))
							self.indiLOG.log(40,"Line {} has error={}".format(sys.exc_traceback.tb_lineno, e)   + u" trying again")
							time.sleep(0.5)
							indigo.variable.updateValue(self.ibeaconNameDefault+u"With_ClosestRPI_Change",trigRPIchanged)
							self.indiLOG.log(40, u"worked 2. time")
					self.triggerEvent(u"someClosestrPiHasChanged")

		except Exception, e:
				if	unicode(e).find(u"UnexpectedNullErrorxxxx") >-1: return 
				self.indiLOG.log(40,"Line {} has error={}".format(sys.exc_traceback.tb_lineno, e))
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

			else:
				for uu in chList:
					dev.updateStateOnServer(uu[u"key"],uu[u"value"])


		except Exception, e:
			self.indiLOG.log(40,"Line {} has error={}".format(sys.exc_traceback.tb_lineno, e))
			self.indiLOG.log(40,u"chList: "+ unicode(chList))

###############################################################################################



####-------------------------------------------------------------------------####
	def convertVariableOrDeviceStateToText(self,textIn,enableEval=False):
		try:
			if not isinstance(textIn, (str, unicode)): return textIn
			oneFound=False
			for ii in range(50):	 # safety, no forever loop
				if textIn.find(u"%%v:") ==-1: break
				oneFound=True
				textIn,rCode = self.convertVariableToText0(textIn)
				if not rCode: break
			for ii in range(50):	 # safety, no forever loop
				if textIn.find(u"%%d:") ==-1: break
				oneFound=True
				textIn,rCode = self.convertDeviceStateToText0(textIn)
				if not rCode: break
			for ii in range(50):	 # safety, no forever loop
				if textIn.find(u"%%FtoC:") ==-1: break
				oneFound=True
				textIn,rCode = self.convertFtoC(textIn)
				if not rCode: break
			for ii in range(50):	 # safety, no forever loop
				if textIn.find(u"%%CtoF:") ==-1: break
				oneFound=True
				textIn,rCode = self.convertCtoF(textIn)
				if not rCode: break
			for ii in range(50):	 # safety, no forever loop
				if textIn.find(u"%%eval:") ==-1: break
				oneFound=True
				textIn,rCode = self.evalString(textIn)
				if not rCode: break
			try:
				if enableEval and oneFound and (textIn.find(u"+")>-1 or	 textIn.find(u"-")>-1 or textIn.find(u"/")>-1 or textIn.find(u"*")>-1):
					textIn = unicode(eval(textIn))
			except: pass
		except Exception, e:
			if len(unicode(e)) > 5 :
				self.indiLOG.log(40,"Line {} has error={}".format(sys.exc_traceback.tb_lineno, e))
		return textIn
####-------------------------------------------------------------------------####
	def convertFtoC(self,textIn):
		#  converts eg: 
		#"abc%%FtoC:1234%%xyz"	  to abcxyz
		try:
			try:
				start= textIn.find(u"%%FtoC:")
			except:
				return textIn, False

			if start==-1:
				return textIn, False
			textOut= textIn[start+7:]
			end = textOut.find(u"%%")
			if end ==-1:
				return textIn, False
			var = textOut[:end]
			try:
				vText= "{:.1f}".format((float(var)-32.)*5./9.)
			except Exception, e:
				self.indiLOG.log(40,"Line {} has error={}".format(sys.exc_traceback.tb_lineno, e))
				return textIn, False

			try:
				if end+2 >= len(textOut)-1:
					textOut= textIn[:start]+vText
					return textOut, True
				textOut= textIn[:start]+vText+textOut[end+2:]
				return textOut, True
			except:
				return textIn, False
		except Exception, e:
			if len(unicode(e)) > 5 :
				self.indiLOG.log(40,"Line {} has error={}".format(sys.exc_traceback.tb_lineno, e))
		return textIn, False
####-------------------------------------------------------------------------####
	def convertCtoF(self,textIn):
		#  converts eg: 
		#"abc%%FtoC:1234%%xyz"	  to abcxyz
		try:
			try:
				start= textIn.find(u"%%CtoF:")
			except:
				return textIn, False

			if start==-1:
				return textIn, False
			textOut= textIn[start+7:]
			end = textOut.find(u"%%")
			if end ==-1:
				return textIn, False
			var = textOut[:end]
			try:
				vText= "{:.1f}".format((float(var)*9./5.) + 32)
			except Exception, e:
				self.indiLOG.log(40,"Line {} has error={}".format(sys.exc_traceback.tb_lineno, e))
				return textIn, False

			try:
				if end+2 >= len(textOut)-1:
					textOut= textIn[:start]+vText
					return textOut, True
				textOut= textIn[:start]+vText+textOut[end+2:]
				return textOut, True
			except:
				return textIn, False
		except Exception, e:
			if len(unicode(e)) > 5 :
				self.indiLOG.log(40,"Line {} has error={}".format(sys.exc_traceback.tb_lineno, e))
		return textIn, False

####-------------------------------------------------------------------------####
	def evalString(self,textIn):
		#  converts eg: 
		#"abc%%FtoC:1234%%xyz"	  to abcxyz
		try:
			try:
				start= textIn.find(u"%%eval:")
			except:
				return textIn, False

			if start==-1:
				return textIn, False
			textOut= textIn[start+7:]
			end = textOut.find(u"%%")
			if end ==-1:
				return textIn, False
			var = textOut[:end]
			try:
				vText= eval(var)
			except Exception, e:
				self.indiLOG.log(40,"Line {} has error={}".format(sys.exc_traceback.tb_lineno, e))
				self.indiLOG.log(20,var)
				self.indiLOG.log(20,textOut[:50])
				return textIn, False

			try:
				if end+2 >= len(textOut)-1:
					textOut= textIn[:start]+vText
					self.indiLOG.log(20,textOut)
					return textOut, True
				textOut= textIn[:start]+vText+textOut[end+2:]
				self.indiLOG.log(20,textOut)
				return textOut, True
			except Exception, e:
				self.indiLOG.log(40,"Line {} has error={}".format(sys.exc_traceback.tb_lineno, e))
				return textIn, False
		except Exception, e:
			if len(unicode(e)) > 5 :
				self.indiLOG.log(40,"Line {} has error={}".format(sys.exc_traceback.tb_lineno, e))
		return textIn, False


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
		except Exception, e:
			if len(unicode(e)) > 5 :
				self.indiLOG.log(40,"Line {} has error={}".format(sys.exc_traceback.tb_lineno, e))
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
		except Exception, e:
			if len(unicode(e)) > 5 :
				self.indiLOG.log(40,"Line {} has error={}".format(sys.exc_traceback.tb_lineno, e))
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



	####-----------------	 ---------
	def completePath(self,inPath):
		if len(inPath) == 0: return ""
		if inPath == " ":	 return ""
		if inPath[-1] !="/": inPath +="/"
		return inPath

########################################
########################################
####----checkPluginPath----
########################################
########################################
	####------ --------
	def checkPluginPath(self, pluginName, pathToPlugin):

		if pathToPlugin.find("/" + self.pluginName + ".indigoPlugin/") == -1:
			self.indiLOG.log(50,u"--------------------------------------------------------------------------------------------------------------")
			self.indiLOG.log(50,u"The pluginName is not correct, please reinstall or rename")
			self.indiLOG.log(50,u"It should be   /Libray/....../Plugins/" + pluginName + ".indigoPlugin")
			p = max(0, pathToPlugin.find("/Contents/Server"))
			self.indiLOG.log(50,u"It is: " + pathToPlugin[:p])
			self.indiLOG.log(50,u"please check your download folder, delete old *.indigoPlugin files or this will happen again during next update")
			self.indiLOG.log(50,u"---------------------------------------------------------------------------------------------------------------")
			self.sleep(100)
			return False
		return True

########################################
########################################
####----move files to ...indigo x.y/Preferences/Plugins/< pluginID >.----
########################################
########################################
	####------ --------
	def moveToIndigoPrefsDir(self, fromPath, toPath):
		if os.path.isdir(toPath): 	
			return True
		indigo.server.log(u"--------------------------------------------------------------------------------------------------------------")
		indigo.server.log("creating plugin prefs directory ")
		os.mkdir(toPath)
		if not os.path.isdir(toPath): 	
			self.indiLOG.log(50,"| preference directory can not be created. stopping plugin:  "+ toPath)
			self.indiLOG.log(50,u"--------------------------------------------------------------------------------------------------------------")
			self.sleep(100)
			return False
		indigo.server.log("| preference directory created;  all config.. files will be here: "+ toPath)
			
		if not os.path.isdir(fromPath): 
			indigo.server.log(u"--------------------------------------------------------------------------------------------------------------")
			return True
		cmd = "cp -R '"+ fromPath+"'  '"+ toPath+"'"
		subprocess.call(cmd, shell=True )
		self.sleep(1)
		indigo.server.log("| plugin files moved:  "+ cmd)
		indigo.server.log("| please delete old files")
		indigo.server.log(u"--------------------------------------------------------------------------------------------------------------")
		return True

########################################
########################################
####-----------------  logging ---------
########################################
########################################

	####----------------- ---------
	def setLogfile(self, lgFile):
		self.logFileActive =lgFile
		if   self.logFileActive =="standard":	self.logFile = ""
		elif self.logFileActive =="indigo":		self.logFile = self.indigoPath.split("Plugins/")[0]+"Logs/"+self.pluginId+"/plugin.log"
		else:									self.logFile = self.indigoPreferencesPluginDir +"plugin.log"
		self.myLog( text="myLogSet setting parameters -- logFileActive= {}; logFile= {};  debug plugin:{}   RPI#:{}".format(self.logFileActive, self.logFile, self.debugLevel, self.debugRPI) , destination="standard")



	####-----------------  check logfile sizes ---------
	def checkLogFiles(self):
		return
		try:
			self.lastCheckLogfile = time.time()
			if self.logFileActive =="standard": return 
			
			fn = self.logFile.split(".log")[0]
			if os.path.isfile(fn + ".log"):
				fs = os.path.getsize(fn + ".log")
				if fs > self.maxLogFileSize:  
					if os.path.isfile(fn + "-2.log"):
						os.remove(fn + "-2.log")
					if os.path.isfile(fn + "-1.log"):
						os.rename(fn + ".log", fn + "-2.log")
						os.remove(fn + "-1.log")
					os.rename(fn + ".log", fn + "-1.log")
					indigo.server.log(" reset logfile due to size > %.1f [MB]" %(self.maxLogFileSize/1024./1024.) )
		except	Exception, e:
				self.indiLOG.log(50, u"checkLogFiles Line {} has error={}".format(sys.exc_traceback.tb_lineno, e))
			
			
	####-----------------	 ---------
	def decideMyLog(self, msgLevel):
		try:
			if msgLevel	 == u"all" or u"all" in self.debugLevel:	 return True
			if msgLevel	 == ""	 and u"all" not in self.debugLevel:	 return False
			if msgLevel in self.debugLevel:							 return True
			return False
		except	Exception, e:
			if len(unicode(e)) > 5:
				indigo.server.log( u"decideMyLog Line {} has error={}".format(sys.exc_traceback.tb_lineno, e))
		return False

	####-----------------  print to logfile or indigo log  ---------
	def myLog(self,	 text="", mType="", errorType="", showDate=True, destination=""):
		   

		try:
			if	self.logFileActive =="standard" or destination.find("standard") >-1:
				if errorType == u"smallErr":
					self.indiLOG.error(u"------------------------------------------------------------------------------")
					self.indiLOG.error(text.encode(u"utf8"))
					self.indiLOG.error(u"------------------------------------------------------------------------------")

				elif errorType == u"bigErr":
					self.indiLOG.error(u"==================================================================================")
					self.indiLOG.error(text.encode(u"utf8"))
					self.indiLOG.error(u"==================================================================================")

				elif mType == "":
					indigo.server.log(text)
				else:
					indigo.server.log(text, type=mType)


			if	self.logFileActive !="standard":

				ts =""
				try:
					if len(self.logFile) < 3: return # not properly defined
					f =  open(self.logFile,"a")
				except Exception, e:
					indigo.server.log(u"Line {} has error={}".format(sys.exc_traceback.tb_lineno, e))
					try:
						f.close()
					except:
						pass
					return
			
				if errorType == u"smallErr":
					if showDate: ts = datetime.datetime.now().strftime(u"%H:%M:%S")
					f.write(u"----------------------------------------------------------------------------------\n")
					f.write((ts+u" ".ljust(12)+u"-"+text+u"\n").encode(u"utf8"))
					f.write(u"----------------------------------------------------------------------------------\n")
					f.close()
					return

				if errorType == u"bigErr":
					if showDate: ts = datetime.datetime.now().strftime(u"%H:%M:%S")
					f.write(u"==================================================================================\n")
					f.write((ts+u" "+u" ".ljust(12)+u"-"+text+u"\n").encode(u"utf8"))
					f.write(u"==================================================================================\n")
					f.close()
					return
				if showDate: ts = datetime.datetime.now().strftime(u"%H:%M:%S")
				if mType == u"":
					f.write((ts+u" " +u" ".ljust(25)  +u"-" + text + u"\n").encode("utf8"))
					#indigo.server.log((ts+u" " +u" ".ljust(25)  +u"-" + text + u"\n").encode("utf8"))
				else:
					f.write((ts+u" " +mType.ljust(25) +u"-" + text + u"\n").encode("utf8"))
					#indigo.server.log((ts+u" " +mType.ljust(25) +u"-" + text + u"\n").encode("utf8"))
				f.close()
				return


		except	Exception, e:
			if len(unicode(e)) > 5:
				self.indiLOG.log(50,u"myLog Line {} has error={}".format(sys.exc_traceback.tb_lineno, e))
				indigo.server.log(text)
				try: f.close()
				except: pass


##################################################################################################################
##################################################################################################################
##################################################################################################################
###################	 TCPIP listen section  receive data from RPI via socket comm  #####################

####-------------------------------------------------------------------------####
	def ipNumberOK(self,ipcheck):
		if not self.isValidIP(ipcheck): return False
		for piU in self.RPI: #OKconvert
			if self.RPI[piU][u"piOnOff"] == "0": continue#OKconvert
			if ipcheck == self.RPI[piU][u"ipNumberPi"]:#OKconvert
				return True

		return False
####-------------------------------------------------------------------------####
	def isValidIP(self, ip0):
		ipx = ip0.split(u".")
		if len(ipx) != 4:
			return False
		else:
			for ip in ipx:
				try:
					if int(ip) < 0 or  int(ip) > 255: return False
				except:
					return False
		return True
####-------------------------------------------------------------------------####
	def isValidMAC(self, mac0):
		macx = mac0.split(u":")
		if len(macx) != 6 : # len(mac.split("D0:D2:B0:88:7B:76")): 
			return False
		else:
			for xx in macx:
				if len(xx) !=2:
					return False
		return True

####-------------------------------------------------------------------------####
	def handlesockReporting(self, IPN, nBytes, name, xType, msg=""):

		try:
			if IPN not in self.dataStats[u"data"]:
				self.dataStats[u"data"][IPN]={}

			if name not in self.dataStats[u"data"][IPN]:
				self.dataStats[u"data"][IPN][name]={}

			if xType not in self.dataStats[u"data"][IPN][name]:
				self.dataStats[u"data"][IPN][name][xType] = {u"firstTime":time.time(),u"lastTime":time.time()-1000,u"count":0,u"bytes":0,"maxBytes":0}
			if u"maxBytes" not in self.dataStats[u"data"][IPN][name][xType]:
				self.dataStats[u"data"][IPN][name][xType][u"maxBytes"]=0
			self.dataStats[u"data"][IPN][name][xType][u"count"] += 1
			self.dataStats[u"data"][IPN][name][xType][u"bytes"] += nBytes
			self.dataStats[u"data"][IPN][name][xType][u"lastTime"] = time.time()
			self.dataStats[u"data"][IPN][name][xType][u"maxBytes"] = max(self.dataStats[u"data"][IPN][name][xType][u"maxBytes"], nBytes)

			if xType != u"ok" : # log if " errxxx" and previous event was less than xxx min ago	ago
				if time.time() - self.dataStats[u"data"][IPN][name][xType][u"lastTime"]	< self.maxSocksErrorTime : # log if previous event was less than 10 minutes ago
					dtLT = datetime.datetime.fromtimestamp(self.dataStats[u"data"][IPN][name][xType][u"lastTime"] ).strftime(_defaultDateStampFormat)
					self.indiLOG.log(30, u"TCPIP socket error rate high for {}/{} ; previous:{}".format(IPN, name, dtLT) )
					self.printTCPIPstats(all=IPN)
				self.saveTcpipSocketStats()
			elif "Socket" in self.debugLevel:
					pass


		except Exception, e:
			if len(unicode(e)) > 5 :
				self.indiLOG.log(40,"Line {} has error={}".format(sys.exc_traceback.tb_lineno, e))
		return 


####-------------------------------------------------------------------------####
	def startTcpipListening(self, myIpNumber, indigoInputPORT):
			self.indiLOG.log(10, u" ..   starting tcpip stack" )
			socketServer = None
			stackReady	 = False
			if self.decideMyLog(u"Socket"): self.indiLOG.log(10, u"starting tcpip socket listener, for RPI data, might take some time, using: ip#={} ;  port#= {}".format(myIpNumber, indigoInputPORT) )
			tcpStart = time.time()
			lsofCMD	 =u"/usr/sbin/lsof -i tcp:{}".format(indigoInputPORT)
			ret = subprocess.Popen(lsofCMD, shell=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE).communicate()
			if self.decideMyLog(u"Socket"): self.indiLOG.log(10, u"lsof output:{}".format(ret) )
			self.killHangingProcess(ret)
			for ii in range(60):  #	 gives port busy for ~ 60 secs if restart, new start it is fine, error message continues even if it works -- indicator =ok: if lsof gives port number  
				try:
					socketServer = ThreadedTCPServer((myIpNumber,int(indigoInputPORT)), ThreadedTCPRequestHandler)
					if self.decideMyLog(u"Socket"): self.indiLOG.log(10, u"TCPIPsocket:: setting reuse	= 1 " )
					socketServer.socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
					if self.decideMyLog(u"Socket"): self.indiLOG.log(10, u"TCPIPsocket:: setting timout = 5 " )
					socketServer.socket.setsockopt(socket.SOL_SOCKET, socket.timeout, 5 )

				except Exception, e:
					if self.decideMyLog(u"Socket"): self.indiLOG.log(10, u"TCPIPsocket:: {0}	  try#: {1:d}	time elapsed: {2:4.1f} secs".format(unicode(e), ii,  (time.time()-tcpStart) ) )
				try:
					ret = subprocess.Popen(lsofCMD, shell=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE).communicate()
					if len(ret[0]) >0: #  if lsof gives port number it works.. 
						if self.decideMyLog(u"Socket"): self.indiLOG.log(10, "{}\n{}".format(lsofCMD, ret[0].strip(u"\n")) )
						TCPserverHandle = threading.Thread(target=socketServer.serve_forever)
						TCPserverHandle.daemon =True # don't hang on exit
						TCPserverHandle.start()
						break
				except Exception, e:
					if unicode(e).find("serve_forever") ==-1:
						self.indiLOG.log(40,"Line {} has error={}".format(sys.exc_traceback.tb_lineno, e))
					self.killHangingProcess(ret)
 
				if	 ii <=2:	tcpWaitTime = 7
				else:			tcpWaitTime = 1
				self.sleep(tcpWaitTime)
			try:
				tcpName = TCPserverHandle.getName() 
				if self.decideMyLog(u"Socket"): self.indiLOG.log(10, u'startTcpipListening tcpip socket listener running; thread:#{}'.format(tcpName) )#	+ " try:"+ unicode(ii)+"  time elapsed:"+ unicode(time.time()-tcpStart) )
				stackReady = True
				self.indiLOG.log(10, u" ..   tcpip stack started" )


			except Exception, e:
				self.indiLOG.log(40,"Line {} has error={}".format(sys.exc_traceback.tb_lineno, e))
				self.indiLOG.log(40,"tcpip stack did not load, restarting.. if this error continues, try restarting indigo server")
				self.quitNow=u" tcpip stack did not load, restart"
			return	socketServer, stackReady

	def killHangingProcess(self, ret):

			test = (ret[0].strip("\n")).split("\n")

			if len(test) ==2:
				try: 
					pidTokill = int((test[1].split())[1])
					killcmd = "/bin/kill -9 {}".format(pidTokill)
					if self.decideMyLog(u"Socket"): self.indiLOG.log(10, u"trying to kill hanging process with: {}".format(killcmd) )
					subprocess.call(killcmd, shell=True)
				except Exception, e:
					self.indiLOG.log(40,"Line {} has error={}".format(sys.exc_traceback.tb_lineno, e))


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
			piName = "none"
			wrongIP = 0

			if	not indigo.activePlugin.ipNumberOK(self.client_address[0]) : 
				wrongIP = 2
				if indigo.activePlugin.decideMyLog(u"Socket"): indigo.activePlugin.indiLOG.log(30, u"TCPIP socket data receiving from {} not in accepted ip number list, please fix in >>initial setup RPI<<".format(self.client_address)  )
				#  add looking for ip = ,"ipAddress":"192.168.1.20"
				# but need first to read data 
				indigo.activePlugin.handlesockReporting(self.client_address[0],0,u"unknown",u"errIP" )
				#self.request.close()
				#return

			# 3 secs should be enough even for slow network mostly one package, should all be send in one package
			self.request.settimeout(5) 

			try: # to catch timeout 
				while True: # until end of message
					buff = self.request.recv(4096)#  max observed is ~ 3000 bytes
					if not buff or len(buff) == 0:#	 or len(buff) < 4096: 
						break
					data0 += buff
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
			except Exception, e:
				e= unicode(e)
				self.request.settimeout(1) 
				self.request.send(u"error")
				self.request.close()
				if e.find("timed out") ==-1: 
					indigo.activePlugin.indiLOG.log(40,u"ThreadedTCPRequestHandler Line {} has error={}".format(sys.exc_traceback.tb_lineno, e) )
					indigo.activePlugin.handlesockReporting( self.client_address[0],len0,piName,e[0:min(10,len(e))] )
				else:
					indigo.activePlugin.handlesockReporting( self.client_address[0],len0,piName,u"timeout" )
				return
			self.request.settimeout(1) 
		   
			try: 
				## dataS =split message should look like:  len-TAG-piName-TAG-data; -TAG- = x-6-a
				if len(dataS) !=3: # tag not found 
					if indigo.activePlugindecideMyLog(u"Socket"): indigo.activePlugin.indiLOG.log(30,u"TCPIP socket  x-6-a  tag not found: {} ... {}".format(data0[0:50], data0[-10:]) )
					try: self.request.send(u"error-tag missing")
					except: pass
					self.request.send(u"error")
					self.request.close()
					indigo.activePlugin.handlesockReporting(self.client_address[0],len0,piName,u"errTag" )
					return

				expLength = int(dataS[0])
				piName	  = dataS[1]
				lenData	  = len(dataS[2])


				if expLength != lenData: # expected # of bytes not received
					if lenData < expLength:
						if indigo.activePlugin.decideMyLog(u"Socket"): indigo.indiLOG.log(30,u"TCPIP socket length of {..} data too short, exp:{};   actual:{};   piName:; {}    ..    {}".format(dataS[0], lenData, piName, dataS[2][0:50], data0[-10:]) )
						try: self.request.send(u"error-lenDatawrong-{}".format(lenData) )
						except: pass
						self.request.send(u"error")
						self.request.close()
						indigo.activePlugin.handlesockReporting(self.client_address[0],len0,piName,u"tooShort" )
						return
					else:
						# check if we received a complete package + extra
						package1 = dataS[2][:expLength]
						try:
							json.loads(package1)
							dataS[2] = package1
							if indigo.activePlugindecideMyLog(u"Socket"): indigo.activePlugin.indiLOG.log(30,u"TCPIP socket length of data wrong -fixed- exp:{};  actual:{};  piName:{}; {}     ..     {}".format(dataS[0], lenData, piName, dataS[2][0:50], data0[-10:]) )
						except:
							if indigo.activePlugindecideMyLog(u"Socket"): indigo.activePlugin.indiLOG.log(30,u"TCPIP socket length of data wrong exp:{};  actual:{};  piName:{}; {}     ..     {}".format(dataS[0], lenData, piName, dataS[2][0:50], data0[-10:]) )
							try: self.request.send(u"error-lenDatawrong-{}".format(lenData) )
							except: pass
							self.request.send(u"error")
							self.request.close()
							indigo.activePlugin.handlesockReporting(self.client_address[0],len0,piName,u"tooLong" )
							return

			except Exception, e:
				if indigo.activePlugin.decideMyLog(u"Socket"): indigo.activePlugin.indiLOG.log(30,u"ThreadedTCPRequestHandler Line {} has error={}".format(sys.exc_traceback.tb_lineno, e))
				if indigo.activePlugin.decideMyLog(u"Socket"): indigo.activePlugin.indiLOG.log(30, u"TCPIP socket, len:{0:d} data: {1}  ..  {2}".format(len0, data0[0:50], data0[-10:]) )
				if indigo.activePlugin.decideMyLog(u"Socket"): indigo.activePlugin.handlesockReporting(self.client_address[0],len0,piName,u"unknown" )
				self.request.send(u"error")
				self.request.close()
				return

			try: 
				dataJ = json.loads(dataS[2])  # dataJ = json object for data
			except Exception, e:
				if indigo.activePlugin.decideMyLog(u"Socket"): indigo.activePlugin.indiLOG.log(30,u"TCPIP socket  json error; len of data: {0:d}  {1}     time used: {2:5.1f}".format(len0, unicode(threading.currentThread()), time.time()-tStart )  )
				if indigo.activePlugin.decideMyLog(u"Socket"): indigo.activePlugin.indiLOG.log(30,data0[0:50]+u"  ..  {}".format(data0[-10:]) ) 
				try: self.request.send(u"error-Json-{}".format(lenData) )
				except: pass
				indigo.activePlugin.handlesockReporting(self.client_address[0],len0,piName,u"errJson" )
				self.request.send(u"error")
				self.request.close()
				return

			if piName.find(u"pi_IN_") != 0 : 
				if indigo.activePlugin.decideMyLog(u"Socket"): indigo.activePlugin.indiLOG.log(30,u"TCPIP socket  listener bad piName {}".format(piName) )
				indigo.activePlugin.handlesockReporting(self.client_address[0],len0,piName,u"badpiName" )
			else:
				wrongIP -= 1
				#### now update Indigo dev/ states 
				indigo.activePlugin.addToDataQueue( piName, dataJ,dataS[2] )
				if wrongIP < 1: indigo.activePlugin.handlesockReporting(self.client_address[0],len0,piName,u"ok",msg=data0 )

			try:	
				if wrongIP < 2: 
					if indigo.activePlugin.decideMyLog(u"Socket"): 
						indigo.activePlugin.indiLOG.log(20, u" sending ok to {} data: {}..{}".format(piName.ljust(13), dataS[2][0:50], dataS[2][-20:]) )
					self.request.send(u"ok-{}".format(lenData) )
			except: pass
			self.request.close()



		except Exception, e:
			if indigo.activePlugin.decideMyLog(u"Socket"): indigo.activePlugin.indiLOG.log(30, u"ThreadedTCPRequestHandler Line {} has error={}".format(sys.exc_traceback.tb_lineno, e))
			if indigo.activePlugin.decideMyLog(u"Socket"): indigo.activePlugin.indiLOG.log(30, u"TCPIP socket {}".format(data0[0:50]) ) 
			indigo.activePlugin.handlesockReporting(self.client_address[0],len0,piName,u"unknown" )
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
####-----------------  valiable formatter for differnt log levels ---------
# call with: 
# formatter = LevelFormatter(fmt='<default log format>', level_fmts={logging.INFO: '<format string for info>'})
# handler.setFormatter(formatter)
class LevelFormatter(logging.Formatter):
	def __init__(self, fmt=None, datefmt=None, level_fmts={}, level_date={}):
		self._level_formatters = {}
		self._level_date_format = {}
		for level, formt in level_fmts.items():
			# Could optionally support level names too
			self._level_formatters[level] = logging.Formatter(fmt=formt, datefmt=level_date[level])
		# self._fmt will be the default format
		super(LevelFormatter, self).__init__(fmt=formt, datefmt=datefmt)

	def format(self, record):
		if record.levelno in self._level_formatters:
			return self._level_formatters[record.levelno].format(record)

		return super(LevelFormatter, self).format(record)




