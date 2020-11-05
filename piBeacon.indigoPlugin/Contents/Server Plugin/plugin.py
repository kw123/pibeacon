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
import zlib

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
_rpiList 						 = [str(ii) for ii in range(_GlobalConst_numberOfRPI)]
_rpiBeaconList 					 = [str(ii) for ii in range(_GlobalConst_numberOfiBeaconRPI)]
_rpiSensorList					 = [str(ii) for ii in range(_GlobalConst_numberOfiBeaconRPI, _GlobalConst_numberOfRPI)]
_sqlLoggerDevTypes				 = [u"isBeaconDevice",u"isRPIDevice",u"isRPISensorDevice",u"isBLEconnectDevice", u"isSensorDevice", u"isBLESensorDevice"]
_sqlLoggerDevTypesNotSensor		 = _sqlLoggerDevTypes[:-1]
_sqlLoggerIgnoreStates = {u"isBeaconDevice":		u"Pi_00_Time,Pi_01_Time,Pi_02_Time,Pi_03_Time,Pi_04_Time,Pi_05_Time,Pi_06_Time,Pi_07_Time,Pi_08_Time,Pi_09_Time,Pi_10_Time,Pi_11_Time,Pi_12_Time,Pi_13_Time,Pi_14_Time,Pi_15_Time,Pi_16_Time,Pi_17_Time,Pi_18_Time,Pi_19_Time,TxPowerReceived,typeOfBeacon,closestRPIText,closestRPITextLast,displayStatus,status,batteryLevelLastUpdate,sensorvalue_ui,updateReason,lastStatusChange,iBeacon,mfg_info"
				         ,u"isRPIDevice":			u"Pi_00_Time,Pi_01_Time,Pi_02_Time,Pi_03_Time,Pi_04_Time,Pi_05_Time,Pi_06_Time,Pi_07_Time,Pi_08_Time,Pi_09_Time,Pi_10_Time,Pi_11_Time,Pi_12_Time,Pi_13_Time,Pi_14_Time,Pi_15_Time,Pi_16_Time,Pi_17_Time,Pi_18_Time,Pi_19_Time,TxPowerReceived,typeOfBeacon,closestRPIText,closestRPITextLast,displayStatus,status,online,i2cactive,sensorvalue_ui,updateReason,lastStatusChange,last_MessageFromRpi"
						 ,u"isBLEconnectDevice":	u"Pi_00_Time,Pi_01_Time,Pi_02_Time,Pi_03_Time,Pi_04_Time,Pi_05_Time,Pi_06_Time,Pi_07_Time,Pi_08_Time,Pi_09_Time,Pi_10_Time,Pi_11_Time,Pi_12_Time,Pi_13_Time,Pi_14_Time,Pi_15_Time,Pi_16_Time,Pi_17_Time,Pi_18_Time,Pi_19_Time,TxPowerReceived,closestRPIText,closestRPITextLast,displayStatus,status,sensorvalue_ui,lastStatusChange"
				         ,u"isRPISensorDevice":		u"displayStatus,status,sensorvalue_ui,lastStatusChange,last_MessageFromRpi"
				         ,u"isBLESensorDevice":		u"displayStatus,status,sensorvalue_ui,lastStatusChange"
				         ,u"isSensorDevice":		u"displayStatus,status,sensorvalue_ui,lastStatusChange"}
_debugAreas = [u"Logic",u"DevMgmt",u"BeaconData",u"SensorData",u"OutputDevice",u"UpdateRPI",u"OfflineRPI",u"Fing",u"BLE",u"CAR",u"BC",u"all",u"Socket",u"StartSocket",u"Special",u"PlotPositions",u"SocketRPI",u"BatteryLevel",u"SQLlogger",u"SQLSuppresslog",u"Beep"]

_GlobalConst_emptyBeacon = {
	u"indigoId": 0, u"ignore": 0, u"status": u"up", u"lastUp": 0, u"note": u"beacon", u"expirationTime": 90,
	u"created": 0, u"updateFING": 0, u"updateWindow": 0, u"updateSignalValuesSeconds": 0, 
	u"PosX": 0., u"PosY": 0., u"PosZ": 0., u"typeOfBeacon": u"other",u"useOnlyPrioTagMessageTypes":u"0", u"beaconTxPower": +999,
	u"lastBusy":20000,
	u"enabled": True,
	u"showBeaconOnMap": 		u"0",u"showBeaconNickName": "",u"showBeaconSymbolAlpha": u"0.5",u"showBeaconSymboluseErrorSize": u"1",u"showBeaconSymbolColor": u"b",
	u"receivedSignals":		[{u"rssi":-999, u"lastSignal": 0, u"distance":99999} for kk in range(_GlobalConst_numberOfiBeaconRPI)]} #  for 10 RPI

_GlobalConst_emptyBeaconProps = {
	u"note":						u"beacon",
	u"expirationTime":				90,
	u"created":						0,
	u"updateSignalValuesSeconds":	0,
	u"signalDelta":					u"999",
	u"fastDown":				    u"0",
	u"minSignalOn":				    u"-999",
	u"minSignalOff":				u"-999",
	u"typeOfBeacon":				u"other",
	u"beaconTxPower":				999,
	u"memberOfFamily":				False,
	u"memberOfGuests":				False,
	u"memberOfOther1":				False,
	u"memberOfOther2":				False,
	u"useOnlyPrioTagMessageTypes":	u"0",
	u"isBeaconDevice":				True,
	u"SupportsStatusRequest":		False,
	u"AllowOnStateChange":			False,
	u"AllowSensorValueChange":		False,
	u"ignore":						0,
	u"enableBroadCastEvents":		u"0",
	u"batteryLevelCheckhours":		u"4/12/20",
	u"beaconBeepUUID":				u"off",
	u"SupportsBatteryLevel":		False,
	u"version":					 	"",	
	u"batteryLevelUUID":			u"off",
	u"showBeaconOnMap": 			u"0",u"showBeaconNickName": "",u"showBeaconSymbolType": u",u",u"showBeaconSymbolAlpha": u"0.5",u"showBeaconSymboluseErrorSize": u"1",u"showBeaconSymbolColor": u"b"
	}

_GlobalConst_emptyrPiProps	  ={
	u"typeOfBeacon":		u"rPI",
	u"updateSignalValuesSeconds":	300,
	u"beaconTxPower":				999,
	u"SupportsBatteryLevel":		False,
	u"sendToIndigoSecs":			90,
	u"sensorRefreshSecs":			90,
	u"deltaChangedSensor":			5,
	u"SupportsStatusRequest":		False,
	u"AllowOnStateChange":			False,
	u"AllowSensorValueChange":		False,
	u"PosXYZ":						u"0.,0.,0.",
	u"BLEserial":					u"sequential",
	u"shutDownPinInput" :			u"-1",
	u"expirationTime" :				u"90",
	u"enableBroadCastEvents":		u"0",
	u"rssiOffset" :					0,
	u"isRPIDevice" :				True,
	u"useOnlyPrioTagMessageTypes":  u"0",
	u"typeOfBeacon":  				u"rPI",
	u"rpiDataAcquistionMethod":  	u"hcidump",
	u"shutDownPinOutput" :			u"-1" }

_GlobalConst_fillMinMaxStates = [u"Temperature",u"AmbientTemperature",u"Pressure",u"Altitude",u"Humidity",u"AirQuality",u"visible",u"ambient",u"white",u"illuminance",u"IR",u"CO2",u"VOC",u"INPUT_0",u"rainRate",u"Moisture",u"INPUT"]

_GlobalConst_emptyRPI =	  {
	u"rpiType":					u"rPi",
	u"enableRebootCheck":		u"restartLoop",
	u"enableiBeacons":			u"1",
	u"input":					{},
	u"ipNumberPi":				"",
	u"ipNumberPiSendTo":		"",
	u"output":					{},
	u"passwordPi":				u"raspberry",
	u"piDevId":					0,
	u"piMAC":					"",
	u"piNumberReceived":		"",
	u"piOnOff":					u"0",
	u"authKeyOrPassword":		u"assword",
	u"piUpToDate": 				[],
	u"sensorList": 				u"0,u",
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
	u"ipNumberPi":			"",
	u"ipNumberPiSendTo":	"",
	u"lastUpPi":			0,
	u"output":				{},
	u"passwordPi":			u"raspberry",
	u"authKeyOrPassword": 	u"assword",
	u"piDevId":				0,
	u"piMAC":				"",
	u"piNumberReceived":	"",
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
	  (u"-1", u"do not use")
	, (u"1",  u"GPIO01 ")
	, (u"2",  u"GPIO02 = pin # 3 -- I2C")
	, (u"3",  u"GPIO03 = pin # 5 -- I2C")
	, (u"4",  u"GPIO04 = pin # 7 -- ONE WIRE")
	, (u"17", u"GPIO17 = pin # 11 -- DHT")
	, (u"27", u"GPIO27 = pin # 13")
	, (u"22", u"GPIO22 = pin # 15")
	, (u"10", u"GPIO10 = pin # 19 -- SPS MOSI")
	, (u"9",  u"GPIO09 = pin # 21 -- SPS MISO")
	, (u"11", u"GPIO11 = pin # 23 -- SPS SCLK")
	, (u"5",  u"GPIO05 = pin # 29")
	, (u"6",  u"GPIO06 = pin # 31")
	, (u"13", u"GPIO13 = pin # 33")
	, (u"19", u"GPIO19 = pin # 35")
	, (u"26", u"GPIO26 = pin # 37")
	, (u"14", u"GPIO14 = pin # 8  -- TX - REBOOT PIN OUT")
	, (u"15", u"GPIO15 = pin # 10 -- RX - REBOOT PIN IN")
	, (u"18", u"GPIO18 = pin # 12")
	, (u"23", u"GPIO23 = pin # 16")
	, (u"24", u"GPIO24 = pin # 18")
	, (u"25", u"GPIO25 = pin # 22")
	, (u"8",  u"GPIO08 = pin # 24 -- SPS CE0")
	, (u"7",  u"GPIO07 = pin # 26 -- SPS CE1")
	, (u"12", u"GPIO12 = pin # 32")
	, (u"16", u"GPIO16 = pin # 36")
	, (u"20", u"GPIO20 = pin # 38")
	, (u"21", u"uGPIO21 = pin # 40")]

_GlobalConst_ICONLIST	= [
	[u"None", u"None"],
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


_GlobalConst_beaconPlotSymbols = [
	u"text", u"dot", u"smallCircle", u"largeCircle", u"square"] # label/text only, dot, small circle, circle prop to dist to rpi, square (for RPI)



_GlobalConst_allowedCommands = [
	u"up", u"down", u"pulseUp", u"pulseDown", u"continuousUpDown", u"analogWrite", u"disable", u"newMessage", u"resetDevice", 
	u"getBeaconParameters", u"startCalibration",u"BLEAnalysis",u"trackMac", u"rampUp", u"rampDown", u"rampUpDown", u"beepBeacon"]	 # commands support for GPIO pins

_BLEsensorTypes =[u"BLERuuviTag", 
				u"BLEiBS01", u"BLEiBS01T", u"BLEiBS01RG", u"BLEiBS03G", u"BLEiBS03T", u"BLEiBS03TP", u"BLEiBS03RG", 
				u"BLEaprilAccel", u"BLEaprilTHL", 
				u"BLEminewE8", u"BLEminewS1TH", u"BLEminewS1TT", 
				u"BLEiSensor-on", u"BLEiSensor-onOff", u"BLEiSensor-RemoteKeyFob", "BLEiSensor-TempHum", 
				u"BLESatech"]
_GlobalConst_allowedSensors = [
	 u"ultrasoundDistance", u"vl503l0xDistance", u"vl6180xDistance", u"vcnl4010Distance", # dist / light
	 u"apds9960",															  # dist gesture
	 u"i2cTCS34725", u"i2cTSL2561", u"i2cVEML6070", u"i2cVEML6030", u"i2cVEML6040", u"i2cVEML7700",		# light 
	 u"i2cVEML6075", u"i2cIS1145", u"i2cOPT3001",									# light	  
	 u"BLEmyBLUEt",
	 u"Wire18B20", u"i2cTMP102", u"i2cMCP9808", u"i2cLM35A",						 # temp 
	 u"DHT", u"i2cAM2320", u"i2cSHT21",u"si7021",						 # temp / hum
	 u"i2cBMPxx", u"i2cT5403", u"i2cBMP280",u"i2cMS5803",						 # temp / press
	 u"i2cBMExx",															 # temp / press/ hum /
	 u"bme680",																   # temp / press/ hum / gas
	 u"bmp388",																   # temp / press/ alt
	 u"tmp006",																   # temp rmote infrared
	 u"tmp007",																   # temp rmote infrared
	 u"max31865",																# platinum temp resistor 
	 u"pmairquality",
	 u"amg88xx",u"mlx90640",													# infrared camera
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
	 u"INPUTRotarySwitchAbsolute",u"INPUTRotarySwitchIncremental",
	 u"spiMCP3008", u"spiMCP3008-1",u"i2cADC121",
	 u"INPUTpulse", u"INPUTcoincidence",
	 u"mysensors", u"myprogram",
	 u"BLEconnect"]

_GlobalConst_lightSensors = [
	u"i2cVEML6075",u"i2cIS1145",u"i2cOPT3001",u"i2cTCS34725",u"i2cTSL2561",u"i2cVEML6070",u"i2cVEML6040",u"i2cVEML7700"]

_GlobalConst_i2cSensors	  = [
	u"si7021",u"bme680",u"bmp388",u"amg88xx",u"mlx90640", u"ccs811",u"sgp30", u"mlx90614", u"ina219", u"ina3221", u"as726x", u"as3935", u"moistureSensor", u"PCF8591", u"ADS1x15",
	u"l3g4200", u"bno055", u"mag3110", u"mpu6050", u"hmc5883L", u"mpu9255", u"lsm303", u"vl6180xDistance", u"vcnl4010Distance",u"apds9960", u"MAX44009"]

_GlobalConst_allowedOUTPUT = [
	u"neopixel", u"neopixel-dimmer", u"neopixelClock", u"OUTPUTgpio-1-ONoff", u"OUTPUTgpio-1", u"OUTPUTi2cRelay", u"OUTPUTgpio-4", u"OUTPUTgpio-10", u"OUTPUTgpio-26", u"setMCP4725",  u"OUTPUTxWindows", u"display", u"setPCF8591dac", u"setTEA5767", u"sundial", u"setStepperMotor"]

_GlobalConst_allowedpiSends = [
	u"updateParamsFTP", u"updateAllFilesFTP", u"rebootSSH", u"resetOutputSSH", u"shutdownSSH", u"getStatsSSH", u"initSSH", u"upgradeOpSysSSH"]


_GlobalConst_groupList = [u"Family", u"Guests", u"Other1", u"Other2", u"Other3"]

_defaultDateStampFormat = u"%Y-%m-%d %H:%M:%S"

################################################################################
################################################################################
################################################################################

# 
# noinspection PySimplifyBooleanCheck,PySimplifyBooleanCheck,PySimplifyBooleanCheck,PySimplifyBooleanCheck,PySimplifyBooleanCheck,PySimplifyBooleanCheck,PySimplifyBooleanCheck,PyAttributeOutsideInit,PyAttributeOutsideInit,PyAttributeOutsideInit,PyAttributeOutsideInit,PyAttributeOutsideInit,PyAttributeOutsideInit,PyAttributeOutsideInit,PyAttributeOutsideInit,PyAttributeOutsideInit,PyAttributeOutsideInit,PyAttributeOutsideInit,PyAttributeOutsideInit,PyAttributeOutsideInit,PyAttributeOutsideInit,PyAttributeOutsideInit,PyAttributeOutsideInit,PyAttributeOutsideInit,PyAttributeOutsideInit,PyAttributeOutsideInit,PyAttributeOutsideInit,PyAttributeOutsideInit,PyAttributeOutsideInit,PyAttributeOutsideInit,PyAttributeOutsideInit,PyAttributeOutsideInit,PyAttributeOutsideInit,PyAttributeOutsideInit,PyAttributeOutsideInit,PyAttributeOutsideInit,PyAttributeOutsideInit,PyAttributeOutsideInit,PyAttributeOutsideInit,PyAttributeOutsideInit,PyAttributeOutsideInit,PyAttributeOutsideInit,PyAttributeOutsideInit,PyAttributeOutsideInit,PyAttributeOutsideInit,PyAttributeOutsideInit,PyAttributeOutsideInit,PyAttributeOutsideInit,PyAttributeOutsideInit,PyAttributeOutsideInit,PyAttributeOutsideInit,PyAttributeOutsideInit,PyAttributeOutsideInit,PyAttributeOutsideInit,PyAttributeOutsideInit,PyAttributeOutsideInit,PyAttributeOutsideInit,PyAttributeOutsideInit,PyAttributeOutsideInit,PyAttributeOutsideInit,PyAttributeOutsideInit,PyAttributeOutsideInit,PyAttributeOutsideInit,PyAttributeOutsideInit,PyAttributeOutsideInit,PyAttributeOutsideInit,PyAttributeOutsideInit,PyAttributeOutsideInit,PyAttributeOutsideInit,PyAttributeOutsideInit,PyAttributeOutsideInit,PyAttributeOutsideInit,PyAttributeOutsideInit,PyAttributeOutsideInit,PyAttributeOutsideInit,PyAttributeOutsideInit,PyAttributeOutsideInit,PyAttributeOutsideInit,PyAttributeOutsideInit,PyAttributeOutsideInit,PyAttributeOutsideInit,PyAttributeOutsideInit,PyAttributeOutsideInit,PyAttributeOutsideInit,PyAttributeOutsideInit,PyAttributeOutsideInit,PyAttributeOutsideInit,PyAttributeOutsideInit,PyAttributeOutsideInit,PyAttributeOutsideInit,PyAttributeOutsideInit,PyAttributeOutsideInit,PyAttributeOutsideInit,PyAttributeOutsideInit,PyAttributeOutsideInit,PyAttributeOutsideInit,PyAttributeOutsideInit,PyAttributeOutsideInit,PyAttributeOutsideInit,PyAttributeOutsideInit,PyAttributeOutsideInit,PyAttributeOutsideInit,PyAttributeOutsideInit,PyAttributeOutsideInit,PyAttributeOutsideInit,PyAttributeOutsideInit,PyAttributeOutsideInit,PyAttributeOutsideInit,PyAttributeOutsideInit,PyAttributeOutsideInit,PyAttributeOutsideInit,PyAttributeOutsideInit,PyAttributeOutsideInit,PyAttributeOutsideInit,PyAttributeOutsideInit,PyAttributeOutsideInit,PyAttributeOutsideInit,PyAttributeOutsideInit,PyAttributeOutsideInit,PyAttributeOutsideInit,PyAttributeOutsideInit,PyAttributeOutsideInit,PyAttributeOutsideInit,PyAttributeOutsideInit,PyAttributeOutsideInit,PyAttributeOutsideInit,PyAttributeOutsideInit,PyAttributeOutsideInit,PyAttributeOutsideInit,PyAttributeOutsideInit,PyAttributeOutsideInit,PyAttributeOutsideInit,PyAttributeOutsideInit,PyAttributeOutsideInit,PyAttributeOutsideInit,PyAttributeOutsideInit,PyAttributeOutsideInit,PyAttributeOutsideInit,PyAttributeOutsideInit,PyAttributeOutsideInit,PyAttributeOutsideInit,PyAttributeOutsideInit,PyAttributeOutsideInit,PyAttributeOutsideInit,PyAttributeOutsideInit,PyAttributeOutsideInit,PyAttributeOutsideInit,PyAttributeOutsideInit,PyAttributeOutsideInit,PyAttributeOutsideInit,PyAttributeOutsideInit,PyAttributeOutsideInit,PyAttributeOutsideInit,PyAttributeOutsideInit,PyAttributeOutsideInit,PyAttributeOutsideInit,PyAttributeOutsideInit,PyAttributeOutsideInit,PyAttributeOutsideInit,PyAttributeOutsideInit,PyAttributeOutsideInit,PyAttributeOutsideInit,PyAttributeOutsideInit,PyAttributeOutsideInit,PyAttributeOutsideInit,PyAttributeOutsideInit,PyAttributeOutsideInit,PyAttributeOutsideInit,PyAttributeOutsideInit,PyAttributeOutsideInit,PyAttributeOutsideInit,PyAttributeOutsideInit,PyAttributeOutsideInit,PyAttributeOutsideInit,PyAttributeOutsideInit,PyAttributeOutsideInit,PyAttributeOutsideInit,PyAttributeOutsideInit,PyAttributeOutsideInit,PyAttributeOutsideInit,PyAttributeOutsideInit,PyAttributeOutsideInit,PyAttributeOutsideInit,PyAttributeOutsideInit,PyAttributeOutsideInit,PyAttributeOutsideInit,PyAttributeOutsideInit,PyAttributeOutsideInit,PyAttributeOutsideInit,PyAttributeOutsideInit,PyAttributeOutsideInit,PyAttributeOutsideInit,PyAttributeOutsideInit,PyAttributeOutsideInit,PyAttributeOutsideInit,PyAttributeOutsideInit,PyAttributeOutsideInit,PyAttributeOutsideInit,PyAttributeOutsideInit,PyAttributeOutsideInit,PyAttributeOutsideInit,PyAttributeOutsideInit,PyAttributeOutsideInit,PyAttributeOutsideInit,PyAttributeOutsideInit,PyAttributeOutsideInit,PyAttributeOutsideInit,PyAttributeOutsideInit,PyAttributeOutsideInit,PyAttributeOutsideInit,PyAttributeOutsideInit,PyAttributeOutsideInit,PyAttributeOutsideInit,PyAttributeOutsideInit,PyAttributeOutsideInit,PyAttributeOutsideInit,PyAttributeOutsideInit,PyAttributeOutsideInit,PyAttributeOutsideInit,PyAttributeOutsideInit,PyAttributeOutsideInit,PyAttributeOutsideInit,PyAttributeOutsideInit,PyAttributeOutsideInit,PyAttributeOutsideInit,PyAttributeOutsideInit,PyAttributeOutsideInit,PyAttributeOutsideInit,PyAttributeOutsideInit,PyAttributeOutsideInit,PyAttributeOutsideInit,PyAttributeOutsideInit,PyAttributeOutsideInit,PyAttributeOutsideInit,PyAttributeOutsideInit,PyAttributeOutsideInit,PyAttributeOutsideInit,PyAttributeOutsideInit,PyAttributeOutsideInit,PyAttributeOutsideInit,PyAttributeOutsideInit,PyAttributeOutsideInit,PyAttributeOutsideInit,PyAttributeOutsideInit,PyAttributeOutsideInit,PyAttributeOutsideInit,PyAttributeOutsideInit,PyAttributeOutsideInit,PyAttributeOutsideInit,PyAttributeOutsideInit,PyAttributeOutsideInit,PyAttributeOutsideInit,PyAttributeOutsideInit,PyAttributeOutsideInit,PyAttributeOutsideInit,PyAttributeOutsideInit,PyAttributeOutsideInit,PyAttributeOutsideInit,PyAttributeOutsideInit,PyAttributeOutsideInit,PyAttributeOutsideInit,PyAttributeOutsideInit,PyAttributeOutsideInit,PyAttributeOutsideInit,PyAttributeOutsideInit,PyAttributeOutsideInit,PyAttributeOutsideInit,PyAttributeOutsideInit,PyAttributeOutsideInit,PyAttributeOutsideInit,PyAttributeOutsideInit,PyAttributeOutsideInit,PyAttributeOutsideInit,PyAttributeOutsideInit,PyAttributeOutsideInit,PyAttributeOutsideInit,PyAttributeOutsideInit,PyAttributeOutsideInit,PyAttributeOutsideInit,PyAttributeOutsideInit,PyAttributeOutsideInit,PyAttributeOutsideInit,PyAttributeOutsideInit,PyAttributeOutsideInit,PyAttributeOutsideInit,PyAttributeOutsideInit,PyAttributeOutsideInit,PyAttributeOutsideInit,PyAttributeOutsideInit,PyAttributeOutsideInit,PyAttributeOutsideInit,PyAttributeOutsideInit,PyAttributeOutsideInit,PyAttributeOutsideInit,PyAttributeOutsideInit,PyAttributeOutsideInit,PyAttributeOutsideInit,PyAttributeOutsideInit,PyAttributeOutsideInit,PyAttributeOutsideInit,PyAttributeOutsideInit,PyAttributeOutsideInit,PyAttributeOutsideInit,PyAttributeOutsideInit,PyAttributeOutsideInit,PyAttributeOutsideInit,PyAttributeOutsideInit,PyAttributeOutsideInit,PyAttributeOutsideInit,PyAttributeOutsideInit,PyUnresolvedReferences,PyUnresolvedReferences,PyUnresolvedReferences,PyUnresolvedReferences
class Plugin(indigo.PluginBase):
####-------------------------------------------------------------------------####
	def __init__(self, pluginId, pluginDisplayName, pluginVersion, pluginPrefs):
		indigo.PluginBase.__init__(self, pluginId, pluginDisplayName, pluginVersion, pluginPrefs)

		self.pluginShortName 			= u"piBeacon"

		self.quitNow					= ""
		self.getInstallFolderPath		= indigo.server.getInstallFolderPath()+u"/"
		self.indigoPath					= indigo.server.getInstallFolderPath()+u"/"
		self.indigoRootPath 			= indigo.server.getInstallFolderPath().split(u"Indigo")[0]
		self.pathToPlugin 				= self.completePath(os.getcwd())

		major, minor, release 			= map(int, indigo.server.version.split(u"."))
		self.indigoVersion 				= float(major)+float(minor)/10.
		self.indigoRelease 				= release
	

		self.pluginVersion				= pluginVersion
		self.pluginId					= pluginId
		self.pluginName					= pluginId.split(u".")[-1]
		self.myPID						= os.getpid()
		self.pluginState				= u"init"

		self.myPID 						= os.getpid()
		self.MACuserName				= pwd.getpwuid(os.getuid())[0]

		self.MAChome					= os.path.expanduser(u"~")
		self.userIndigoDir				= self.MAChome + u"/indigo/"
		self.indigoPreferencesPluginDir = self.getInstallFolderPath+u"Preferences/Plugins/"+self.pluginId+u"/"
		self.indigoPluginDirOld			= self.userIndigoDir + self.pluginShortName+u"/"
		self.PluginLogFile				= indigo.server.getLogsFolderPath(pluginId=self.pluginId) +u"/plugin.log"


		formats=	{   logging.THREADDEBUG: u"%(asctime)s %(msg)s",
						logging.DEBUG:       u"%(asctime)s %(msg)s",
						logging.INFO:        u"%(asctime)s %(msg)s",
						logging.WARNING:     u"%(asctime)s %(msg)s",
						logging.ERROR:       u"%(asctime)s.%(msecs)03d\t%(levelname)-12s\t%(name)s.%(funcName)-25s %(msg)s",
						logging.CRITICAL:    u"%(asctime)s.%(msecs)03d\t%(levelname)-12s\t%(name)s.%(funcName)-25s %(msg)s" }

		date_Format = { logging.THREADDEBUG: u"%Y-%m-%d %H:%M:%S",
						logging.DEBUG:       u"%Y-%m-%d %H:%M:%S",
						logging.INFO:        u"%Y-%m-%d %H:%M:%S",
						logging.WARNING:     u"%Y-%m-%d %H:%M:%S",
						logging.ERROR:       u"%Y-%m-%d %H:%M:%S",
						logging.CRITICAL:    u"%Y-%m-%d %H:%M:%S" }
		formatter = LevelFormatter(fmt=u"%(msg)s", datefmt=u"%Y-%m-%d %H:%M:%S", level_fmts=formats, level_date=date_Format)

		self.plugin_file_handler.setFormatter(formatter)
		self.indiLOG = logging.getLogger(u"Plugin")  
		self.indiLOG.setLevel(logging.THREADDEBUG)

		self.indigo_log_handler.setLevel(logging.WARNING)
		indigo.server.log(u"initializing	 ... ")

		indigo.server.log(  u"path To files:          =================")
		indigo.server.log(  u"indigo                  {}".format(self.indigoRootPath))
		indigo.server.log(  u"installFolder           {}".format(self.indigoPath))
		indigo.server.log(  u"plugin.py               {}".format(self.pathToPlugin))
		indigo.server.log(  u"Plugin params           {}".format(self.indigoPreferencesPluginDir))

		self.indiLOG.log( 0,u"!!!!INFO ONLY!!!!  logger  enabled for   0             !!!!INFO ONLY!!!!")
		self.indiLOG.log( 5,u"!!!!INFO ONLY!!!!  logger  enabled for   THREADDEBUG   !!!!INFO ONLY!!!!")
		self.indiLOG.log(10,u"!!!!INFO ONLY!!!!  logger  enabled for   DEBUG         !!!!INFO ONLY!!!!")
		self.indiLOG.log(20,u"!!!!INFO ONLY!!!!  logger  enabled for   INFO          !!!!INFO ONLY!!!!")
		self.indiLOG.log(30,u"!!!!INFO ONLY!!!!  logger  enabled for   WARNING       !!!!INFO ONLY!!!!")
		self.indiLOG.log(40,u"!!!!INFO ONLY!!!!  logger  enabled for   ERROR         !!!!INFO ONLY!!!!")
		self.indiLOG.log(50,u"!!!!INFO ONLY!!!!  logger  enabled for   CRITICAL      !!!!INFO ONLY!!!!")

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
			if self.pathToPlugin.find(u"/"+self.pluginName+u".indigoPlugin/")==-1:
				self.errorLog(u"---------------------------------------------------------------------------------------------------------------" )
				self.errorLog(u"---------------------------------------------------------------------------------------------------------------" )
				self.errorLog(u"---------------------------------------------------------------------------------------------------------------" )
				self.errorLog(u"---------------------------------------------------------------------------------------------------------------" )
				self.errorLog(u"---------------------------------------------------------------------------------------------------------------" )
				self.errorLog(u"---------------------------------------------------------------------------------------------------------------" )
				self.errorLog(u"---------------------------------------------------------------------------------------------------------------" )
				self.errorLog(u"---------------------------------------------------------------------------------------------------------------" )
				self.errorLog(u"The pluginname is not correct, please reinstall or rename")
				self.errorLog(u"It should be   /Libray/....../Plugins/"+self.pluginName+u".indigPlugin")
				p=max(0,self.pathToPlugin.find(u"/Contents/Server"))
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

			if os.path.isfile(self.indigoPreferencesPluginDir+u"dataVersion"):
				subprocess.call(u"rm '"+self.indigoPreferencesPluginDir+u"dataVersion' &", shell=True)	


			self.startTime = time.time()

			self.getDebugLevels()

			self.setVariables()

			#### basic check if we can do get path for files			 
			self.initFileDir()

			self.checkcProfile()

			self.myLog( text = u" --V {}   initializing  -- ".format(self.pluginVersion), destination="standard")

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
				cmd = u"echo '"+self.passwordOfServer+u"' | sudo -S /usr/bin/xattr -rd com.apple.quarantine '"+self.pathToPlugin+u"pngquant'"
				ret = subprocess.Popen(cmd,shell=True,stdout=subprocess.PIPE,stderr=subprocess.PIPE).communicate()
				if self.decideMyLog(u"Logic"): self.indiLOG.log(20,u"setting attribute for catalina  with:  {}".format(cmd))
				if self.decideMyLog(u"Logic"): self.indiLOG.log(20,u" ......... result:{}".format(ret))

			self.setSqlLoggerIgnoreStatesAndVariables()
	  
 			self.indiLOG.log(10,u" ..   startup(self): setting variables, debug ..   finished ")

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
			if self.indigoVersion <  7.4:                             return 
			if self.indigoVersion == 7.4 and self.indigoRelease == 0: return 
			#tt = [u"beacon",              "rPI",u"rPI-Sensor",u"BLEconnect",u"sensor"]

			outOND  = ""
			outOffD = ""
			outONV  = ""
			outOffV = ""
			if self.decideMyLog(u"SQLSuppresslog"): self.indiLOG.log(20,u"setSqlLoggerIgnoreStatesAndVariables settings:{} ".format( self.SQLLoggingEnable) )
			if not self.SQLLoggingEnable[u"devices"]: # switch sql logging off
				for ff in _sqlLoggerDevTypes:

					statesToInclude = _sqlLoggerIgnoreStates[ff].split(u",")[0]
					for dev in indigo.devices.iter(u"props."+ff):	
						props = dev.pluginProps
						skip = False
						if ff == u"isSensorDevice":
							for kk in _sqlLoggerDevTypesNotSensor:
								if kk in props:
									skip=True
									break
						if skip: continue
						sp = dev.sharedProps
						#if self.decideMyLog(u"SQLSuppresslog"): self.indiLOG.log(20,u"\n1 dev: {} current sharedProps: testing for off \n{}".format(dev.name, unicode(sp).replace(u"\n","")) )
						if u"sqlLoggerIgnoreStates" not in sp or statesToInclude not in sp[u"sqlLoggerIgnoreStates"]: 
							sp[u"sqlLoggerIgnoreStates"] = copy.copy(_sqlLoggerIgnoreStates[ff])
							dev.replaceSharedPropsOnServer(sp)
							outOffD += dev.name+u"; "
							dev2 = indigo.devices[dev.id]
							sp2 = dev2.sharedProps

			else:  # switch sql logging (back) on
				for ff in _sqlLoggerDevTypes:
					for dev in indigo.devices.iter(u"props."+ff):	
						props = dev.pluginProps
						skip = False
						### alsways set completely
						if ff == u"isSensorDevice":
							for kk in _sqlLoggerDevTypesNotSensor:
								if kk in props:
									skip=True
									break
						if skip: continue
						sp = dev.sharedProps
						if u"sqlLoggerIgnoreStates" in sp and len(sp[u"sqlLoggerIgnoreStates"]) > 0: 
							outOffD += dev.name+u"; "
							sp[u"sqlLoggerIgnoreStates"] = ""
							dev.replaceSharedPropsOnServer(sp)



			if not self.SQLLoggingEnable[u"variables"]:

				for v in self.varExcludeSQLList:
					if v not in indigo.variables: continue
					var = indigo.variables[v]
					sp = var.sharedProps
					if u"sqlLoggerIgnoreChanges" in sp and sp[u"sqlLoggerIgnoreChanges"] == u"true": 
						continue
					outOffV += var.name+u"; "
					sp[u"sqlLoggerIgnoreChanges"] = u"true"
					var.replaceSharedPropsOnServer(sp)

			else:
				for v in self.varExcludeSQLList:
					try:
						if v not in indigo.variables: continue
						var = indigo.variables[v]
						sp = var.sharedProps
						if u"sqlLoggerIgnoreChanges" not in sp  or sp[u"sqlLoggerIgnoreChanges"] != u"true": 
							continue
						outONV += var.name+u"; "
						sp[u"sqlLoggerIgnoreChanges"] = ""
						var.replaceSharedPropsOnServer(sp)
					except: pass

			if self.decideMyLog(u"SQLSuppresslog"): 
				self.indiLOG.log(20,u" \n\n")
				if outOffD !="":
					self.indiLOG.log(20,u" switching off SQL logging for special devtypes/states:\n{}\n for devices:\n>>>{}<<<".format(json.dumps(_sqlLoggerIgnoreStates, sort_keys=True, indent=2), outOffD) )

				if outOND !="":
					self.indiLOG.log(20,u" switching ON SQL logging for special states for devices: {}".format(outOND) )

				if outOffV !="":
					self.indiLOG.log(20,u" switching off SQL logging for variables :{}".format(outOffV) )

				if outONV !="":
					self.indiLOG.log(20,u" switching ON SQL logging for variables :{}".format(outONV) )
				self.indiLOG.log(20,u"setSqlLoggerIgnoreStatesAndVariables settings end\n")



		except Exception, e:
			self.indiLOG.log(40,u"Line {} has error={}".format(sys.exc_traceback.tb_lineno, e))
		return 



####-----------------	 ---------
	def xxgetEventConfigUiXml(self, typeId, eventId):
		indigo.server.log(u'Called getEventConfigUiXml(self, typeId:{}, eventId:{},  eventsTypeDict:{}:'.format(typeId, eventId, self.eventsTypeDict) )
		if typeId in self.eventsTypeDict:
			return self.eventsTypeDict[typeId][u"ConfigUIRawXml"]
		return None
		
####-----------------	 ---------
	def xxgetEventConfigUiValues(self, pluginProps, typeId, eventId):
		indigo.server.log(u'Called getEventConfigUiValues(self, pluginProps:{}, typeId:{}, eventId {}:'.format(pluginProps, typeId, eventId) )
		valuesDict = pluginProps
		errorMsgDict = indigo.Dict()
		return (valuesDict, errorMsgDict)


####-----------------	 ---------
	def initMac2Vendor(self):
		self.waitForMAC2vendor = False
		self.enableMACtoVENDORlookup	= int(self.pluginPrefs.get(u"enableMACtoVENDORlookup",u"21"))
		if self.enableMACtoVENDORlookup != u"0":
			self.M2V =  M2Vclass.MAP2Vendor( pathToMACFiles=self.indigoPreferencesPluginDir+u"mac2Vendor/", refreshFromIeeAfterDays = self.enableMACtoVENDORlookup, myLogger = self.indiLOG.log )
			self.waitForMAC2vendor = self.M2V.makeFinalTable()

####-----------------	 ---------
	def getVendortName(self,MAC):
		if self.enableMACtoVENDORlookup != u"0" and not self.waitForMAC2vendor:
			self.waitForMAC2vendor = self.M2V.makeFinalTable()

		return self.M2V.getVendorOfMAC(MAC)


####-------------------------------------------------------------------------####
	def setCurrentlyBooting(self, addTime, setBy=""):
		try:	self.currentlyBooting = time.time() + addTime
		except: self.errorLog(u"setCurrentlyBooting:  setting BeaconsCheck,  bad number requested {}, called from: {} ".format(addTime, setBy))
		try:
			self.indiLOG.log(20,u"setting BeaconsCheck to off (no up-->down) for {:3d} secs requested by: {} ".format(addTime, setBy))
		except:
			indigo.server.log(u"setting BeaconsCheck to off (no up-->down) for {:3d} secs requested by: {} ".format(addTime, setBy))
		return 


####-------------------------------------------------------------------------####
	def initFileDir(self):



			if not os.path.exists(self.indigoPreferencesPluginDir):
				os.mkdir(self.indigoPreferencesPluginDir)
			if not os.path.exists(self.indigoPreferencesPluginDir):
				self.indiLOG.log(50,u"error creating the plugin data dir did not work, can not create: {}".format(self.indigoPreferencesPluginDir)  )
				self.sleep(1000)
				exit()

			if not os.path.exists(self.indigoPreferencesPluginDir+u"plotPositions"):
				os.mkdir(self.indigoPreferencesPluginDir+u"plotPositions")
			if not os.path.exists(self.cameraImagesDir):
				os.mkdir(self.cameraImagesDir)


	
####-------------------------------------------------------------------------####
	def startupFIXES0(self): # change old names used


		try:
			for dev in indigo.devices.iter(u"props.isBeaconDevice,props.isRPIDevice,props.isRPISensorDevice,props.isBLEconnectDevice"):
				if not dev.enabled: continue
				props = dev.pluginProps
				try:
					if u"lastStatusChange" in dev.states:
						dateString	= datetime.datetime.now().strftime(_defaultDateStampFormat)
						dateString2 = dev.states[u"lastStatusChange"]
						if len(dateString2) < 10:
								dev.updateStateOnServer(u"lastStatusChange",dateString)
						else:
							dateString = dateString2

						if u"displayStatus" in dev.states:
							new =  self.padDisplay(dev.states[u"status"]) + dateString[5:]
							if new != dev.states[u"displayStatus"]:
								dev.updateStateOnServer(u"displayStatus",new)
							if	 u"up" in new:
								dev.updateStateImageOnServer(indigo.kStateImageSel.SensorOn)
							elif  u"down" in new:
								dev.updateStateImageOnServer(indigo.kStateImageSel.SensorOff)
							else:
								dev.updateStateImageOnServer(indigo.kStateImageSel.SensorTripped)



				except Exception, e:
						self.indiLOG.log(40,u"Line {} has error={}".format(sys.exc_traceback.tb_lineno, e))
		except Exception, e:
				self.indiLOG.log(40,u"Line {} has error={}".format(sys.exc_traceback.tb_lineno, e))
		return
		

####-------------------------------------------------------------------------####
	def startupFIXES1(self):
		try:
			dateString = datetime.datetime.now().strftime(_defaultDateStampFormat)

			self.sprinklerDeviceActive = False

			######## fix  battery prop	and signal if not used 
			try:
				for dev in indigo.devices.iter(self.pluginId):
					if dev.deviceTypeId == u"beacon" or (dev.deviceTypeId.lower()) == u"rpi":
						for piU in _rpiBeaconList:
							piI = int(piU)
							stateT = u"Pi_{:02d}_Time".format(piI)
							stateS = u"Pi_{:02d}_Signal".format(piI)
							try: 
								if dev.states[stateT] is None or len(dev.states[stateT]) < 5:
									if unicode(dev.states[stateS]) == u"0":
										self.addToStatesUpdateDict(dev.id,stateS,-999)
							except:
								if not self.RPIVersion20:
									self.indiLOG.log(30,u"{}  error pi#: {}, state missing ignored/disabled device? stateS:{}, stateT:{}\n states:{}".format(dev.name, piU,stateS, stateT, dev.states) )
								continue

						self.executeUpdateStatesDict(calledFrom=u"startupFIXES1")

					if dev.deviceTypeId.lower() == u"rpi" and u"note" in dev.states:
						piString = dev.states[u"note"].split(u"-")
						if len(piString) == 2:
							piU = piString[1]
							for xyz in [u"PosX",u"PosY",u"PosZ"]:
								self.RPI[piU][xyz] = dev.states[xyz]

					upd = False
					props = dev.pluginProps
					#if u"SupportsBatteryLevel" in props:
					#	props[u"SupportsBatteryLevel"] = False
					#s	upd = True

					if u"addNewOneWireSensors" in props:   # reset accept new one wire devices
						props[u"addNewOneWireSensors"] = u"0"
						upd = True


					if u"lastSensorChange" in dev.states:
						if len(dev.states[u"lastSensorChange"]) < 5:
							dev.updateStateOnServer(u"lastSensorChange",dateString)

					if dev.deviceTypeId == u"BLEconnect":
						props[u"isBLEconnectDevice"] = True

					if dev.deviceTypeId in _GlobalConst_allowedSensors or dev.deviceTypeId in _BLEsensorTypes:
						props[u"isSensorDevice"] = True
						upd = True

					if dev.deviceTypeId in _GlobalConst_allowedOUTPUT:
						props[u"isOutputDevice"] = True
						upd = True


					if (dev.deviceTypeId.lower()) == u"rpi":
						if u"isBeaconDevice" in props:
							del props[u"isBeaconDevice"]
						props[u"isRPIDevice"] = True
						props[u"typeOfBeacon"] = u"rPI"
						props[u"useOnlyPrioTagMessageTypes"] = u"0"
						upd = True
						if props[u"address"] in self.beacons:
							self.beacons[props[u"address"]][u"typeOfBeacon"] = u"rPI"

					if dev.deviceTypeId == u"rPI-Sensor":
						props[u"isRPISensorDevice"] = True
						upd = True


					if dev.deviceTypeId ==u"car":
						props[u"isCARDevice"] = True
						upd = True

					if dev.deviceTypeId in _BLEsensorTypes:
						if u"isBLESensorDevice" not in props: 
							props[u"isBLESensorDevice"] = True
							upd = True

					if upd:
						self.deviceStopCommIgnore = time.time()
						dev.replacePluginPropsOnServer(props)



				self.writeJson(self.RPI, fName=self.indigoPreferencesPluginDir + u"RPIconf", fmtOn=self.RPIFileSort)

			except Exception, e:
				self.indiLOG.log(40,u"Line {} has error={}".format(sys.exc_traceback.tb_lineno, e))
			try:
				os.remove(self.indigoPreferencesPluginDir + u"config")
			except:
				pass


			self.indiLOG.log(10,u" ..   checking devices tables" )

	######## fix rPi- --> Pi-
			for dev in indigo.devices.iter(u"props.isRPIDevice,props.isRPISensorDevice"):
				dd = dev.description
				if dev.description.find(u"rPI") >-1:
					dd = dd.split(u"-")
					if len(dd) == 3:
						dev.description = u"Pi-"+dd[1]+u"-"+dd[2]
						dev.replaceOnServer()

				props = dev.pluginProps

				if dev.deviceTypeId.find(u"rPI") >-1:
					if dev.deviceTypeId.find(u"rPI-Sensor") >-1:
						if dev.address.find(u"Pi-") == 0:
							dev.updateStateOnServer(u"note",dev.address)
						else:
							dev.updateStateOnServer(u"note",u"Pi-"+dev.address)
					else:
						if dev.description.find(u"Pi-"):
							nn = dev.states[u"note"].split(u"-")
							if len(nn) == 3:
								dev.updateStateOnServer(u"note",u"Pi-"+nn[1])


	######## fix  address vendors ..
			for dev in indigo.devices.iter(self.pluginId):
				props = dev.pluginProps

				if dev.deviceTypeId == u"rPi" or dev.deviceTypeId == u"beacon":
					self.freezeAddRemove = False

					try:
						beacon = props[u"address"]
					except:
						self.indiLOG.log(40,u"device has no address:" + dev.name + u" " + unicode(dev.id) +	unicode(props) + u" " + unicode(dev.globalProps) + u" please delete and let the plugin create the devices")
						continue

					if beacon not in self.beacons:
						self.beacons[beacon]			 = copy.deepcopy(_GlobalConst_emptyBeacon)
						self.beacons[beacon][u"indigoId"] = dev.id
						self.beacons[beacon][u"created"]  = dev.states[u"created"]

					if u"vendorName" in dev.states and  len(dev.states[u"vendorName"]) == 0:
						vname = self.getVendortName(beacon)
						if vname !="" and  vname != dev.states[u"vendorName"]:
							dev.updateStateOnServer( u"vendorName", vname)


				if dev.deviceTypeId.find(u"OUTPUTgpio") > -1:
					xxx = json.loads(props[u"deviceDefs"])
					nn = len(xxx)
					update=False
					for n in range(nn):
						if u"gpio" in xxx[n]:
							if xxx[n][u"gpio"] == u"-1":
								del xxx[n]
								continue
							if	u"initialValue" not in xxx[n]:
								xxx[n][u"initialValue"] = u"-"
								update=True
					if update: 
						props[u"deviceDefs"] = json.dumps(xxx)
						self.deviceStopCommIgnore = time.time()
						dev.replacePluginPropsOnServer(props)
					###indigo.server.log(dev.name+u" "+unicode(props))

				if dev.deviceTypeId.find(u"OUTPUTi2cRelay") > -1:
					xxx = json.loads(props[u"deviceDefs"])
					nn = len(xxx)
					update=False
					for n in range(nn):
						if u"gpio" in xxx[n]:
							if xxx[n][u"gpio"] == u"-1":
								del xxx[n]
								continue
							if	u"initialValue" not in xxx[n]:
								xxx[n][u"initialValue"] = u"-"
								update=True
					if update: 
						props[u"deviceDefs"] = json.dumps(xxx)
						self.deviceStopCommIgnore = time.time()
						dev.replacePluginPropsOnServer(props)
					###indigo.server.log(dev.name+u" "+unicode(props))


				if u"description" in props: 
					props[u"description"] =""
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
				for beacon in self.beacons:
					if beacon in self.CARS[u"beacon"]: 
						try: 
							indigoId = self.beacons[beacon][u"indigoId"]
							if indogoId >0:
								dev = indigo.devices[self.beacons[beacon][u"indigoId"]]
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
					self.beacons[mac][area].append({u"distance": 99999,u"lastSignal": 0, u"rssi": -999})

		except Exception, e: 
			if unicode(e) != u"None":
				self.indiLOG.log(40,u"Line {} has error={}".format(sys.exc_traceback.tb_lineno, e))



####-------------------------------------------------------------------------####
	def setupBasicFiles(self):
		try:

			if not os.path.exists(self.indigoPreferencesPluginDir + u"all"):
				os.mkdir(self.indigoPreferencesPluginDir + u"all")
			if not os.path.exists(self.indigoPreferencesPluginDir + u"rejected"):
				os.mkdir(self.indigoPreferencesPluginDir + u"rejected")
				subprocess.call(u"mv '" + self.indigoPreferencesPluginDir + u"reject*' '" + self.indigoPreferencesPluginDir + u"rejected'", shell=True)
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


			try: self.debugRPI	= int(self.pluginPrefs.get(u"debugRPI", -1))
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
			self.cameraImagesDir			= self.indigoPreferencesPluginDir+u"cameraImages/"
			self.knownBeaconTags 			= {}

			self.setLogfile(self.pluginPrefs.get(u"logFileActive2", u"standard"))

			self.beaconsFileSort			= True
			self.parametersFileSort			= True
			self.RPIFileSort				= True
			try:
				xx = (self.pluginPrefs.get(u"SQLLoggingEnable", u"on-on")).split(u"-")
				self.SQLLoggingEnable ={u"devices":xx[0]==u"on", u"variables":xx[1]==u"on"}
			except:
				self.SQLLoggingEnable ={u"devices":False, u"variables":False}

			self.bootWaitTime				= 100
			self.setCurrentlyBooting(self.bootWaitTime + 25, setBy=u"setVariables")

			self.checkBatteryLevelHours = [int(x) for x in _GlobalConst_emptyBeaconProps[u"batteryLevelCheckhours"].split(u"/")]

			self.lastUPtoDown				= time.time() + 35
			self.lastsetupFilesForPi 		= time.time()
			self.checkIPSendSocketOk		= {}
			self.actionList					= {u"setTime":[],u"setSqlLoggerIgnoreStatesAndVariables":False}
			self.updateStatesDict			= {}
			self.executeUpdateStatesDictActive = ""

			self.rpiQueues					= {}
			self.rpiQueues[u"reset"]		= {}
			self.rpiQueues[u"data"]			= {}
			self.rpiQueues[u"state"]		= {}
			self.rpiQueues[u"lastActive"]	= {}
			self.rpiQueues[u"lastCheck"]	= {}
			self.rpiQueues[u"thread"] 		= {}
			self.rpiQueues[u"lastData"] 	= {}
			self.RPIBusy					= {}
			for ii in range(_GlobalConst_numberOfRPI):
				iiU = unicode(ii)
				self.rpiQueues[u"reset"][iiU] 		= False
				self.rpiQueues[u"data"][iiU]		= Queue.Queue()
				self.rpiQueues[u"state"][iiU]		= ""
				self.rpiQueues[u"lastActive"][iiU]	= time.time() - 900000
				self.rpiQueues[u"lastCheck"][iiU]	= time.time() - 900000
				self.rpiQueues[u"lastData"][iiU]	= ""
				self.RPIBusy[iiU]					= 0

			self.delayedActions				= {}
			self.delayedActions[u"thread"] 	= ""
			self.delayedActions[u"data"]	= Queue.Queue()
			self.delayedActions[u"lastData"] = 0
			self.delayedActions[u"state"]	= ""
			self.delayedActions[u"lastActive"]	= 0


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

			self.doRejects					= False

			self.enableFING					= u"0"
			self.timeErrorCount				= [0 for ii in _rpiList]
			self.configAndReboot			= ""
			self.initStatesOnServer			= True
			try:
				self.rPiCommandPORT			= self.pluginPrefs.get(u"rPiCommandPORT", u"9999")
			except:
				self.rPiCommandPORT			= u"0" # port on rPis to receive commands ==0 disable

			self.groupListUsedNames = {} 
			for nn in range(len(_GlobalConst_groupList)):
				group = _GlobalConst_groupList[nn]
				self.groupListUsedNames[group] = ""
				try: 
					xx = self.pluginPrefs["groupName{}".format(nn)]
					if len(xx) >0: self.groupListUsedNames[group] = xx
				except: pass
			indigo.server.log(unicode(self.groupListUsedNames))

			try:				self.iBeaconDevicesFolderName		= self.pluginPrefs.get(u"iBeaconFolderName", u"Pi_Beacons_new")
			except:				self.iBeaconDevicesFolderName		= u"Pi_Beacons_new" 
			self.pluginPrefs[u"iBeaconFolderName"] = self.iBeaconDevicesFolderName

			try:				self.iBeaconFolderVariablesName	 = self.pluginPrefs.get(u"iBeaconFolderVariablesName", u"piBeacons")
			except:				self.iBeaconFolderVariablesName	 = u"piBeacons" 
			self.pluginPrefs[u"iBeaconFolderVariablesName"] = self.iBeaconFolderVariablesName


			try:				self.iBeaconFolderVariableDataTransferVarsName	 = self.pluginPrefs.get(u"iBeaconFolderVariableDataTransferVarsName", u"piBeacons_dataTransferVars")
			except:				self.iBeaconFolderVariableDataTransferVarsName	 = u"piBeacons_dataTransferVars" 
			self.pluginPrefs[u"iBeaconFolderVariableDataTransferVarsName"] = self.iBeaconFolderVariableDataTransferVarsName
			#indigo.server.log(" self.iBeaconFolderVariablesName:{};   self.iBeaconFolderVariableDataTransferVarsName:{}".format( self.iBeaconFolderVariablesName, self.iBeaconFolderVariableDataTransferVarsName))

			self.getFolderIdOfBeacons()

			try:				self.automaticRPIReplacement= unicode(self.pluginPrefs.get(u"automaticRPIReplacement", u"False")).lower() == u"true" 
			except:				self.automaticRPIReplacement= False 

			try:				self.setClostestRPItextToBlank= self.pluginPrefs.get(u"setClostestRPItextToBlank",u"1") != u"1"
			except:				self.setClostestRPItextToBlank= False

			try:				self.enableRebootRPIifNoMessages  = int(self.pluginPrefs.get(u"enableRebootRPIifNoMessages", 999999999))
			except:				self.enableRebootRPIifNoMessages  = 999999999
			self.pluginPrefs[u"enableRebootRPIifNoMessages"] = self.enableRebootRPIifNoMessages

			try:				self.rpiDataAcquistionMethod  =  self.pluginPrefs.get(u"rpiDataAcquistionMethod", _GlobalConst_emptyrPiProps[u"rpiDataAcquistionMethod"])
			except:				self.rpiDataAcquistionMethod  = _GlobalConst_emptyrPiProps[u"rpiDataAcquistionMethod"]
			self.pluginPrefs[u"rpiDataAcquistionMethod"] = self.rpiDataAcquistionMethod


			try:				self.tempUnits				= self.pluginPrefs.get(u"tempUnits", u"Celsius")
			except:				self.tempUnits				= u"Celsius"

			try:				self.tempDigits				 = int(self.pluginPrefs.get(u"tempDigits", 1))
			except:				self.tempDigits				 = 1

			try:				self.rainUnits				= self.pluginPrefs.get(u"rainUnits", u"mm")
			except:				self.rainUnits				= u"mm"

			try:				self.rainDigits				 = int(self.pluginPrefs.get(u"rainDigits", 0))
			except:				self.rainDigits				 = 0

			try:				self.pressureUnits			= self.pluginPrefs.get(u"pressureUnits", u"mBar")
			except:				self.pressureUnits			= u"hPascal"
			if 	self.pressureUnits==  u"mbar": 				self.pressureUnits = u"mBar"
			self.pluginPrefs[u"pressureUnits"] = self.pressureUnits
 

			try:				self.distanceUnits			= max(0.0254, float(self.pluginPrefs.get(u"distanceUnits", 1.)))
			except:				self.distanceUnits			= 1.0
			try:				self.speedUnits				= max(0.01, float(self.pluginPrefs.get(u"speedUnits", 1.)))
			except:				self.speedUnits				= 1.0

			try:				self.lightningTimeWindow	 = float(self.pluginPrefs.get(u"lightningTimeWindow", 10.))
			except:				self.lightningTimeWindow	 = 10.0


			try:				self.lightningNumerOfSensors = int(self.pluginPrefs.get(u"lightningNumerOfSensors", 1))
			except:				self.lightningNumerOfSensors = 1


			try:				self.secToDown				= float(self.pluginPrefs.get(u"secToDown", u"80"))
			except:				self.secToDown				= 80.

			try:				self.acceptNewiBeacons		= int(self.pluginPrefs.get(u"acceptNewiBeacons", -999))
			except:				self.acceptNewiBeacons		= -999
			if self.acceptNewiBeacons in [u"0", u"1"]: 		self.acceptNewiBeacons  = -999
			self.pluginPrefs[u"acceptNewiBeacons"] 			= self.acceptNewiBeacons

			self.acceptNewTagiBeacons						= self.pluginPrefs.get(u"acceptNewTagiBeacons",u"off")
			self.pluginPrefs[u"acceptNewTagiBeacons"] 		= self.acceptNewTagiBeacons

			try:				self.removeJunkBeacons		= self.pluginPrefs.get(u"removeJunkBeacons", u"1") == u"1"
			except:				self.removeJunkBeacons		= False

			try:				self.restartBLEifNoConnect = self.pluginPrefs.get(u"restartBLEifNoConnect", u"1") == u"1"
			except :				self.restartBLEifNoConnect = True

			try:				self.rebootWatchDogTime		= self.pluginPrefs.get(u"rebootWatchDogTime", u"-1")
			except:				self.rebootWatchDogTime		= u"-1"

			try:				self.expectTimeout			= self.pluginPrefs.get(u"expectTimeout", u"20")
			except:				self.expectTimeout			= u"20"


			self.indigoInputPORT			= int(self.pluginPrefs.get(u"indigoInputPORT", 0))
			self.IndigoOrSocket				= (self.pluginPrefs.get(u"IndigoOrSocket", u"indigo"))
			self.dataStats					= {u"startTime": time.time()}
			try:	self.maxSocksErrorTime	= float(self.pluginPrefs.get(u"maxSocksErrorTime", u"600.")) 
			except: self.maxSocksErrorTime	= 600.
			self.compressRPItoPlugin		= self.pluginPrefs.get(u"compressRPItoPlugin", u"99999999")
			self.portOfServer				= self.pluginPrefs.get(u"portOfServer", u"8176")
			self.userIdOfServer				= self.pluginPrefs.get(u"userIdOfServer", "")
			self.passwordOfServer			= self.pluginPrefs.get(u"passwordOfServer", "")
			self.authentication				= self.pluginPrefs.get(u"authentication", u"digest")
			self.myIpNumber					= self.pluginPrefs.get(u"myIpNumber", u"192.168.1.130")
			self.GPIOpwm					= self.pluginPrefs.get(u"GPIOpwm", 1)

			try:				self.rebootHour			= int(self.pluginPrefs.get(u"rebootHour", -1))
			except: 			self.rebootHour			= -1

			self.updateRejectListsCount		= 0

			try:				self.piUpdateWindow			= float(self.pluginPrefs.get(u"piUpdateWindow", 0))
			except:				self.piUpdateWindow			= 0.

			self.rPiRestartCommand			= ["" for ii in range(_GlobalConst_numberOfRPI)]  ## which part need to restart on rpi

			self.anyProperTydeviceNameOrId = 0

			self.wifiSSID					= self.pluginPrefs.get(u"wifiSSID", "")
			self.wifiPassword				= self.pluginPrefs.get(u"wifiPassword", "")
			self.key_mgmt					= self.pluginPrefs.get(u"key_mgmt", "")
			eth0							= '{"on":"dontChange",	"useIP":"use"}'
			wlan0							= '{"on":"dontChange",	"useIP":"useIf"}'
			try: 			self.wifiEth	= {u"eth0":json.loads(self.pluginPrefs.get(u"eth0", eth0)), u"wlan0":json.loads(self.pluginPrefs.get(u"wlan0", wlan0))}
			except: 		self.wifiEth	= {u"eth0":json.loads(eth0),u"wlan0":json.loads(wlan0)}

			self.fingscanTryAgain			= False
			try:			self.enableFING	= self.pluginPrefs.get(u"enableFING", u"0")
			except:			self.enableFING	= u"0"
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

			self.pluginPrefs[u"wifiOFF"] = ""


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

			self.beaconPositionsData[u"textPosLargeCircle"]			= self.pluginPrefs.get(u"beaconPositionstextPosLargeCircle", u"0" )
			self.beaconPositionsData[u"labelTextSize"]				= self.pluginPrefs.get(u"beaconPositionsLabelTextSize", u"12" )
			self.beaconPositionsData[u"captionTextSize"]			= self.pluginPrefs.get(u"beaconPositionsCaptionTextSize", u"12" )
			self.beaconPositionsData[u"titleTextSize"]				= self.pluginPrefs.get(u"beaconPositionsTitleTextSize", u"12" )
			self.beaconPositionsData[u"titleText"]					= self.pluginPrefs.get(u"beaconPositionsTitleText", u"text on top" )
			self.beaconPositionsData[u"titleTextPos"]				= self.pluginPrefs.get(u"beaconPositionsTitleTextPos", u"0,0" )
			self.beaconPositionsData[u"titleTextColor"]				= self.pluginPrefs.get(u"beaconPositionsTitleTextColor", u"#000000" )
			self.beaconPositionsData[u"titleTextRotation"]			= self.pluginPrefs.get(u"beaconPositionsTitleTextRotation", u"0" )
			self.beaconPositionsData[u"Outfile"]					= self.pluginPrefs.get(u"beaconPositionsimageOutfile", "" )
			self.beaconPositionsData[u"ShowCaption"]				= self.pluginPrefs.get(u"beaconPositionsimageShowCaption", u"0" )
			self.beaconPositionsData[u"showTimeStamp"]				= self.pluginPrefs.get(u"beaconPositionsShowTimeStamp", u"1" ) == u"1"
			self.beaconPositionsData[u"compress"]					= self.pluginPrefs.get(u"beaconPositionsimageCompress",False)
			self.beaconPositionsData[u"ShowRPIs"]					= self.pluginPrefs.get(u"beaconPositionsimageShowRPIs", u"0" )
			self.beaconPositionsData[u"randomBeacons"]				= self.pluginPrefs.get(u"beaconRandomBeacons", u"0" )
			self.beaconPositionsData[u"SymbolSize"]					= self.pluginPrefs.get(u"beaconSymbolSize", u"1.0" )
			self.beaconPositionsData[u"LargeCircleSize"]			= self.pluginPrefs.get(u"beaconLargeCircleSize", u"1.0" )
			self.beaconPositionsData[u"ShowExpiredBeacons"]			= self.pluginPrefs.get(u"beaconShowExpiredBeacons", u"0" )
			self.beaconPositionsLastCheck							= time.time() - 20


			self.varExcludeSQLList = [ "pi_IN_"+str(ii) for ii in _rpiList]
			self.varExcludeSQLList.append(self.ibeaconNameDefault+u"With_ClosestRPI_Change")
			self.varExcludeSQLList.append(self.ibeaconNameDefault+u"Rebooting")
			self.varExcludeSQLList.append(self.ibeaconNameDefault+u"With_Status_Change")
			for group in self.groupListUsedNames:
				if len(group) > 0:
					for tType in [u"Home", u"Away"]:
						self.varExcludeSQLList.append(self.groupCountNameDefault+self.groupListUsedNames[group]+u"_"+tType)

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
				triggerGroup[group]={u"allHome":False,u"allWay":False,u"oneHome":False,u"oneAway":False}

			for group in  _GlobalConst_groupList:
				self.groupStatusList[group][u"nAway"] = 0
				self.groupStatusList[group][u"nHome"] = 0
			self.groupStatusListALL[u"nHome"] = 0
			self.groupStatusListALL[u"nAway"] = 0
   
			okList =[]
						  
			for beacon	in self.beacons:
				if self.beacons[beacon][u"note"].find(u"beacon") !=0: continue
				if self.beacons[beacon][u"indigoId"] ==0 or self.beacons[beacon][u"indigoId"] =="": continue
				try:
					dev= indigo.devices[self.beacons[beacon][u"indigoId"]]
				except:
					continue

				if dev.deviceTypeId != u"beacon":	  continue
				if dev.states[u"status"] == u"up":
					self.groupStatusListALL[u"nHome"]	  +=1
				else:							 
					self.groupStatusListALL[u"nAway"]	  +=1

				if dev.states[u"groupMember"] == "": continue
				if devIdSelected != "" and dev.id  !=devIdSelected:	continue
				if not dev.enabled:	 continue
				okList.append(unicode(dev.id))
				for group in _GlobalConst_groupList:
					groupNameUsedForVar = self.groupListUsedNames[group]
					if groupNameUsedForVar != "" and groupNameUsedForVar in dev.states[u"groupMember"]:
						self.groupStatusList[group][u"members"][unicode(dev.id)] = True
						if dev.states[u"status"] == u"up":
							if self.groupStatusList[group][u"oneHome"] == u"0":
								triggerGroup[group][u"oneHome"]			= True
								self.groupStatusList[group][u"oneHome"]	= u"1"
							self.groupStatusList[group][u"nHome"]		+=1
						else:
							if self.groupStatusList[group][u"oneAway"] == u"0":
								triggerGroup[group][u"oneAway"]			= True
							self.groupStatusList[group][u"oneAway"]		= u"1"
							self.groupStatusList[group][u"nAway"]		+=1
 
 			for dev	in indigo.devices.iter(u"props.isBLEconnectDevice"):
				if not dev.enabled: continue
				okList.append(unicode(dev.id))
				props = dev.pluginProps
				for group in _GlobalConst_groupList:
					if "groupMember" not in dev.states: continue
					groupNameUsedForVar = self.groupListUsedNames[group]
					if groupNameUsedForVar != "" and groupNameUsedForVar in dev.states[u"groupMember"]:
						self.groupStatusList[group][u"members"][unicode(dev.id)] = True
						if dev.states[u"status"] == u"up":
							if self.groupStatusList[group][u"oneHome"] == u"0":
								triggerGroup[group][u"oneHome"]			= True
								self.groupStatusList[group][u"oneHome"]	= u"1"
							self.groupStatusList[group][u"nHome"]		+=1
						else:
							if self.groupStatusList[group][u"oneAway"] == u"0":
								triggerGroup[group][u"oneAway"]			= True
							self.groupStatusList[group][u"oneAway"]		= u"1"
							self.groupStatusList[group][u"nAway"]		+=1
					
				continue


			for group in  _GlobalConst_groupList:
					removeList=[]
					for member in self.groupStatusList[group][u"members"]:
						if member not in okList:
							removeList.append(member)
					for member in  removeList:
						del self.groupStatusList[group][u"members"][member]
					if len(self.groupStatusList[group][u"members"]) ==0:
						for tType in [u"Home", u"Away"]:
							varName = self.groupCountNameDefault+self.groupListUsedNames[group]+u"_"+tType
							if varName in indigo.variables:
								indigo.variable.delete(varName)


			for group in _GlobalConst_groupList:
				if self.groupStatusList[group][u"nAway"] == len(self.groupStatusList[group][u"members"]):
					if self.groupStatusList[group][u"allAway"] == u"0":
						triggerGroup[group][u"allAway"] = True
					self.groupStatusList[group][u"allAway"]	  = u"1"
					self.groupStatusList[group][u"oneHome"]	  = u"0"
				else:		 
					self.groupStatusList[group][u"allAway"]	  = u"0"

				if self.groupStatusList[group][u"nHome"] == len(self.groupStatusList[group][u"members"]):
					if self.groupStatusList[group][u"allHome"] == u"0":
						triggerGroup[group][u"allHome"] = True
					self.groupStatusList[group][u"allHome"]	  = u"1"
					self.groupStatusList[group][u"oneAway"]	  = u"0"
				else:		 
					self.groupStatusList[group][u"allHome"]	  = u"0"


			# now extra variables
			#indigo.server.log("self.groupStatusList:{} ".format(self.groupStatusList))
			for group in _GlobalConst_groupList:
				groupNameUsedForVar = self.groupListUsedNames[group]
				if len(groupNameUsedForVar) < 1: continue
				if len(self.groupStatusList[group]["members"]) >0:
					for tType in [u"Home", u"Away"]:
						varName = self.groupCountNameDefault+groupNameUsedForVar+u"_"+tType
						gName="n"+tType
						try:
							var = indigo.variables[varName]
						except:
							indigo.variable.create(varName, "",self.iBeaconFolderVariablesName)
							var = indigo.variables[varName]

						#indigo.server.log("var:{} group:{}, gName:{} ".format(var.name, group, gName))
						if var.value !=	 unicode(self.groupStatusList[group][gName]):
							indigo.variable.updateValue(varName, unicode(self.groupStatusList[group][gName]))



			for tType in [u"Home", u"Away"]:
				varName = self.groupCountNameDefault+u"ALL_"+tType
				gName = u"n"+tType
				try:
					var = indigo.variables[varName]
				except:
					indigo.variable.create(varName, "", self.iBeaconFolderVariablesName)
					var = indigo.variables[varName]

				if var.value !=	 unicode(self.groupStatusListALL[gName]):
					indigo.variable.updateValue(varName,unicode(self.groupStatusListALL[gName]))


			if	init != u"init" and len(self.triggerList) > 0:
				for group in triggerGroup:
					for tType in triggerGroup[group]:
						if triggerGroup[group][tType]:
							self.triggerEvent(group+u"-"+tType)

		except Exception, e:
			if unicode(e) != u"None":
				self.indiLOG.log(40,u"Line {} has error={}".format(sys.exc_traceback.tb_lineno, e))


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
	def deleteAndCeateVariables(self, delete):
		try:
			piFolder = indigo.variables.folder.create(self.iBeaconFolderVariablesName)
		except :
			piFolder = indigo.variables.folders[self.iBeaconFolderVariablesName]
		if self.iBeaconFolderVariableDataTransferVarsName == self.iBeaconFolderVariablesName:
			piFolder_pi_in = piFolder
		else:
			try:
				piFolder_pi_in = indigo.variables.folder.create(self.iBeaconFolderVariableDataTransferVarsName)
			except :
				piFolder_pi_in = indigo.variables.folders[self.iBeaconFolderVariableDataTransferVarsName]

		#indigo.server.log("deleteAndCeateVariables  iBeaconFolderVariablesName:{} iBeaconFolderVariableDataTransferVarsName: {} piFolder:{}\n piFolder_pi_in:{}".format(self.iBeaconFolderVariablesName, self.iBeaconFolderVariableDataTransferVarsName, piFolder, piFolder_pi_in))

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
			for dev in indigo.devices.iter(u"props.isSensorDevice"):
				if dev.deviceTypeId ==  u"lidar360": 
					try:	indigo.variable.delete((dev.name+u"_data").replace(u" ",u"_"))
					except:	pass 

		try:			indigo.variable.create(u"pi_IN_Alive", "", piFolder_pi_in)
		except:			pass
		try:			indigo.variable.create(self.ibeaconNameDefault+u"With_Status_Change", "", piFolder)
		except:			pass
		try:			indigo.variable.create(self.ibeaconNameDefault+u"With_ClosestRPI_Change", "", piFolder)
		except:			pass
		try:			indigo.variable.create(self.ibeaconNameDefault+u"Rebooting", "", piFolder)
		except:			pass
		for dev in indigo.devices.iter(u"props.isSensorDevice"):
			if dev.deviceTypeId ==  u"lidar360": 
				try:	
						indigo.variable.create((dev.name+u"_data").replace(u" ",u"_"), "", piFolder)
				except: pass
				try:	
						indigo.variable.create((dev.name+u"_calibrated").replace(u" ",u"_"), "", piFolder)
				except: pass


		for piU in self.RPI:
			if delete:
				try:
					indigo.variable.delete(u"pi_IN_{}".format(piU) )
				except:
					pass
			try:
				indigo.variable.create(u"pi_IN_{}".format(piU), "", piFolder_pi_in)
			except:
				pass

		try:			indigo.variable.create(u"lightningEventDate", "", piFolder)
		except:			pass
		try:			indigo.variable.create(u"lightningEventDevices", u"0", piFolder)
		except:			pass

####-------------------------------------------------------------------------####
	def getFolderIdOfBeacons(self):
		self.piFolderId = 0
		try:
			self.piFolderId = indigo.devices.folders.getId(self.iBeaconDevicesFolderName)
		except: pass

		if self.piFolderId ==0:
			try:
				ff = indigo.devices.folder.create(self.iBeaconDevicesFolderName)
				self.piFolderId = ff.id
			except:
				self.piFolderId = 0
				self.iBeaconDevicesFolderName = u"Pi_Beacons_new"

		try:
			self.iBeaconFolderVariablesId = indigo.devices.folders.getId(self.iBeaconFolderVariablesName)
		except: pass

		if self.iBeaconFolderVariablesId ==0:
			try:
				ff = indigo.variables.folder.create(self.iBeaconFolderVariablesName)
				self.iBeaconFolderVariablesId = ff.id
			except:
				self.iBeaconFolderVariablesId = 0

		if self.iBeaconFolderVariableDataTransferVarsName != self.iBeaconFolderVariablesName:

			try:
				self.iBeaconFolderVariableDataTransferVarsId = indigo.devices.folders.getId(self.iBeaconFolderVariableDataTransferVarsName)
			except:	self.iBeaconFolderVariableDataTransferVarsId = 0

			if self.iBeaconFolderVariableDataTransferVarsId ==0:
				try:
					ff = indigo.variables.folder.create(self.iBeaconFolderVariableDataTransferVarsName)
					self.iBeaconFolderVariableDataTransferVarsId = ff.id
				except:
					pass

		self.deleteAndCeateVariables(False)	
	
		return


####-------------------------------------------------------------------------####
	def readTcpipSocketStats(self):
		self.dataStats ={}
		try:
			if os.path.isfile(self.indigoPreferencesPluginDir + u"dataStats"):
				f = open(self.indigoPreferencesPluginDir + u"dataStats", u"r")
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
			self.indiLOG.log(40,u"Line {} has error={}".format(sys.exc_traceback.tb_lineno, e))
		if u"data" not in self.dataStats:
			self.resetDataStats() 

####-------------------------------------------------------------------------####
	def resetDataStats(self):
		self.dataStats={u"startTime": time.time(),u"data":{},"updates":{u"devs":0,u"states":0,u"startTime": time.time(),u"nstates":[0 for ii in range(11)]}}
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
			f = open(self.indigoPreferencesPluginDir + u"CARS", u"r")
			self.CARS = json.loads(f.read())
			f.close()
		except:
			self.sleep(1)
			try:
				f = open(self.indigoPreferencesPluginDir + u"CARS", u"r")
				self.CARS = json.loads(f.read())
				f.close()
			except Exception, e:
				self.CARS={u"carId":{},u"beacon":{}}

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
					self.indiLOG.log(40,u"Line {} has error={}".format(sys.exc_traceback.tb_lineno, e))
					if unicode(e).find(u"timeout waiting") > -1:
						self.indiLOG.log(40,u"communication to indigo is interrupted")
						return
					self.indiLOG.log(40,u"devId {} not defined in devices  removing from	 CARS:".format(carIds,unicode(self.CARS)) )
					delDD.append(carIds)
				if u"homeSince"	not in self.CARS[u"carId"][carIds]:	 self.CARS[u"carId"][carIds][u"homeSince"] = 0
				if u"awaySince"	not in self.CARS[u"carId"][carIds]:	 self.CARS[u"carId"][carIds][u"awaySince"] = 0
				if u"beacons"	not in self.CARS[u"carId"][carIds]:	 self.CARS[u"carId"][carIds][u"beacons"]   = {}
			for carIds in delDD:
				del self.CARS[u"carId"][carIds]

		except Exception, e:
			if unicode(e) != u"None":
				self.indiLOG.log(40,u"Line {} has error={}".format(sys.exc_traceback.tb_lineno, e))


####-------------------------------------------------------------------------####
	def updateAllCARbeacons(self, indigoCarIds, force=False):
		try:
				beacon = ""
				if self.decideMyLog(u"CAR"): self.indiLOG.log(10,u"updateAllCARbeacons	 CARS:" + unicode(self.CARS))
				for beacon in self.CARS[u"beacon"]:
					if indigoCarIds	 !=	 self.CARS[u"beacon"][beacon][u"carId"] and not force: continue
					beaconDevId = self.beacons[beacon][u"indigoId"]
					beaconDev	= indigo.devices[beaconDevId]
					if self.decideMyLog(u"CAR"): self.indiLOG.log(10,u"updating all cars")
					self.updateCARS(beacon, beaconDev, beaconDev.states, force=True)
					break

		except Exception, e:
			if unicode(e) != u"None":
				self.indiLOG.log(40,u"Line {} has error={}".format(sys.exc_traceback.tb_lineno, e))
			self.indiLOG.log(40,u"deleted beacon? .. car beacons beacon#  {}".format(beacon) )
			self.indiLOG.log(40,u"for   indigoCarId {}".format(indigoCarIds) )

####-------------------------------------------------------------------------####
	def updateCARS(self, beacon, beaconDev, beaconNewStates, force=False):
		try:
			if beacon not in self.CARS[u"beacon"]: return
			if len(beacon) < 10: return
			indigoCarIds = unicode(self.CARS[u"beacon"][beacon][u"carId"])
			if indigoCarIds not in self.CARS[u"carId"]: # pointer to indigo ID
				self.indiLOG.log(10,u"{} beacon: not found in CARS[carId], removing from dict;  CARSdict: {}".format(beacon, unicode(self.CARS)) )
				del self.CARS[u"beacon"][beacon]
				return

			####  car status:
			#		Home/away , engine= on/off/unknown, motion: arriving/leaving/ stop   

			if False and beaconDev.states[u"status"] == beaconNewStates[u"status"] and not force:
				if self.decideMyLog(u"CAR"): self.indiLOG.log(10,u"updateCARS: -0-  {}  no change".format(beacon))
				return

			indigoIDofBeacon = beaconDev.id
			carDev			 = indigo.devices[int(indigoCarIds)]
			if not carDev.enabled: return 
			props			 = carDev.pluginProps
			carName			 = carDev.name


				 
			try:	whatForStatus = carDev.pluginProps[u"displayS"]	 
			except: whatForStatus = ""
			if whatForStatus == "": whatForStatus = u"location" 

			oldCarStatus	= carDev.states[u"location"]
			oldCarEngine	= carDev.states[u"engine"]
			oldCarMotion	= carDev.states[u"motion"]
			oldBeaconStatus	= beaconDev.states[u"status"]
			newBeaconStatus	= beaconNewStates[u"status"]
			beaconType		= self.CARS[u"beacon"][beacon][u"beaconType"]
			beaconBattery	= u"noChange"
			beaconUSB		= u"noChange"
			beaconKey		= u"present"
			nKeysFound		= 0
			oldAwaySince = self.CARS[u"carId"][indigoCarIds][u"awaySince"] 
			oldHomeSince = self.CARS[u"carId"][indigoCarIds][u"homeSince"] 
			if self.decideMyLog(u"CAR"): self.indiLOG.log(10,u"{}-{} -1- {} updating {}, oldBeaconStatus={}, newBeaconStatus={}  oldAwaySince:{}  oldHomeSince:{}, oldCarStatus={}, oldCarEngine={}, oldCarMotion={}".format(carName, indigoCarIds, beacon, beaconType, oldBeaconStatus, newBeaconStatus, time.time()-oldAwaySince, time.time()-oldHomeSince, oldCarStatus, oldCarEngine, oldCarMotion) ) 

			if beaconType == u"beaconBattery":	 
				if newBeaconStatus	== u"up": beaconBattery = u"present"	## battery beacon is home
				else:						  beaconBattery = u"away" 

			if beaconType == u"beaconUSB":		 
				if newBeaconStatus	== u"up": beaconUSB	    = u"on"	## usb beacon is home
				else:						  beaconUSB	    = u"off" 

			if beaconType.find(u"beaconKey")>-1: 
				if newBeaconStatus	!= u"up":  beaconKey	    = u"away"   # at least one is missing
				nKeysFound	+= 1

			for b in self.CARS[u"carId"][indigoCarIds][u"beacons"]:
				beaconTypeTest = self.CARS[u"beacon"][b][u"beaconType"]
				if beaconTypeTest == beaconType: continue
				if indigoCarIds != unicode(self.CARS[u"beacon"][b][u"carId"]): continue
				indigoDEV  = indigo.devices[self.beacons[b][u"indigoId"]]
				st = indigoDEV.states[u"status"]
				if self.decideMyLog(u"CAR"): self.indiLOG.log(10,u"{}-{} -2- testing dev={}  st={}".format(carName, indigoCarIds, indigoDEV.name, st) ) 

				if beaconTypeTest == u"beaconBattery":	 
					if st  ==u"up": beaconBattery 	= u"present" ## battery beacon is home
					else:			beaconBattery 	= u"away" 
		
				if beaconTypeTest == u"beaconUSB":		 
					if st  ==u"up": beaconUSB		 = u"on"  ## usb beacon is home
					else:			beaconUSB		 = u"off" 

				if beaconTypeTest.find(u"beaconKey")>-1: 
					if st  != u"up": beaconKey		= u"away" 
					nKeysFound += 1

			if nKeysFound == 0:		beaconKey		= u"away"

			self.checkCarsNeed[indigoCarIds] = 0



			updateProps = False
			if u"address" not in props: 
				props[u"address"] = u"away"
				updateProps = True

			if (beaconBattery == u"present" or beaconUSB == u"on" or beaconKey == u"present") and props[u"address"] == u"away":
				props[u"address"] = u"home"
				updateProps = True

			elif not (beaconBattery == u"present" or beaconUSB == u"on" or beaconKey == u"present") and props[u"address"] == u"home":
				props[u"address"] = u"away" 
				updateProps = True

			self.addToStatesUpdateDict(indigoCarIds,u"motion",carDev.states[u"motion"])

			if  beaconUSB == u"on": 
				self.addToStatesUpdateDict(indigoCarIds,u"engine", u"on")
			else:
				self.addToStatesUpdateDict(indigoCarIds,u"engine", u"off")

			if beaconBattery == u"present" or beaconUSB == u"on" or beaconKey == u"present":	#some thing is on== home
				if self.decideMyLog(u"CAR"): self.indiLOG.log(10,u"{} -3-  setting to be home,   oldCarStatus: {}".format(carName ,oldCarStatus) )
				self.addToStatesUpdateDict(indigoCarIds, u"location", u"home")
				if oldCarStatus != u"home": 
					self.CARS[u"carId"][indigoCarIds][u"homeSince"] = time.time()
					self.addToStatesUpdateDict(indigoCarIds, u"LastArrivalAtHome",datetime.datetime.now().strftime(_defaultDateStampFormat))

			else:	  # nothing on, we are away
				self.addToStatesUpdateDict(indigoCarIds, u"location", u"away")
				if oldCarStatus != u"away": 
					self.setIcon(carDev,props, u"SensorOff-SensorOn",0)
					self.CARS[u"carId"][indigoCarIds][u"awaySince"] = time.time()
					self.addToStatesUpdateDict(indigoCarIds,u"LastLeaveFromHome",datetime.datetime.now().strftime(_defaultDateStampFormat))
				self.addToStatesUpdateDict(indigoCarIds, u"motion", u"left")
				self.addToStatesUpdateDict(indigoCarIds, u"engine", u"unknown")
				self.checkCarsNeed[indigoCarIds] = 0



			if self.decideMyLog(u"CAR"): self.indiLOG.log(10,u"{}-{} -4- update states: type:{}    bat={}    USB={}    Key={}    car newawayFor={:.0f}[secs] newhomeFor={:.0f}[secs]".format(carName, indigoCarIds, beaconType, beaconBattery, beaconUSB, beaconKey, time.time()-self.CARS[u"carId"][indigoCarIds][u"awaySince"], time.time()-self.CARS[u"carId"][indigoCarIds][u"homeSince"] ) )

			if oldCarStatus == u"away":

				if beaconBattery == u"present" or beaconUSB == u"on" or beaconKey == u"present": 
					self.setIcon(carDev,props, u"SensorOff-SensorOn",1)
					if time.time() - self.CARS[u"carId"][indigoCarIds][u"awaySince"]  > 120: # just arriving home, was away for some time
						self.addToStatesUpdateDict(indigoCarIds,u"motion", u"arriving")
						self.checkCarsNeed[indigoCarIds] = 0

					else : # is this a fluke?
						self.addToStatesUpdateDict(indigoCarIds, u"motion", u"unknown")
						self.checkCarsNeed[indigoCarIds]= time.time() + 20

				elif indigoCarIds in self.updateStatesDict and u"location" in self.updateStatesDict[indigoCarIds] and self.updateStatesDict[indigoCarIds][u"location"][u"value"] == u"home":
						self.indiLOG.log(30,u"{}-{}; -5- beacon: {} bad state , coming home, but no beacon is on".format(carName, indigoCarIds, beacon) )
						self.checkCarsNeed[indigoCarIds]= time.time() + 20

				if carDev.states[u"LastLeaveFromHome"] == "": self.addToStatesUpdateDict(indigoCarIds, u"LastLeaveFromHome",datetime.datetime.now().strftime(_defaultDateStampFormat))



			else:  ## home
				if (beaconBattery == u"present" or beaconUSB == u"on" or beaconKey == u"present"): 

					if	beaconUSB == u"off" : # engine is off
						if	 oldCarMotion == u"arriving" and time.time() - self.CARS[u"carId"][indigoCarIds][u"homeSince"] > 10:	 
								self.addToStatesUpdateDict(indigoCarIds, u"motion", u"stop")

						elif oldCarMotion == u"leaving"	and time.time() - self.CARS[u"carId"][indigoCarIds][u"homeSince"] > 200: 
								self.addToStatesUpdateDict(indigoCarIds, u"motion", u"stop")

						elif oldCarMotion == u"left"	and time.time() - self.CARS[u"carId"][indigoCarIds][u"homeSince"] < 60: 
								self.addToStatesUpdateDict(indigoCarIds, u"motion", u"arriving")

						elif oldCarMotion == "": 
								self.addToStatesUpdateDict(indigoCarIds, u"motion", u"stop")

						elif oldCarMotion == u"unknown": 
								self.addToStatesUpdateDict(indigoCarIds, u"motion", u"stop")

						elif oldCarMotion == u"stop": 
								pass
						else:
								self.checkCarsNeed[indigoCarIds]= time.time() + 20

					if	beaconUSB == u"on" : # engine is on
						if time.time() - self.CARS[u"carId"][indigoCarIds][u"homeSince"] > 600: 
							self.addToStatesUpdateDict(indigoCarIds, u"motion", u"leaving")

						elif time.time() - self.CARS[u"carId"][indigoCarIds][u"homeSince"] > 60 and oldCarMotion == u"stop": 
							self.addToStatesUpdateDict(indigoCarIds, u"motion", u"leaving")

						elif time.time() - self.CARS[u"carId"][indigoCarIds][u"homeSince"] < 30 and oldCarMotion in [u"unknown", u"leaving"]: 
							self.addToStatesUpdateDict(indigoCarIds, u"motion", u"arriving")

						else:
							self.checkCarsNeed[indigoCarIds]= time.time() + 20

				else:
					self.checkCarsNeed[indigoCarIds]= time.time() + 20

				if carDev.states[u"LastArrivalAtHome"] == "": self.addToStatesUpdateDict(indigoCarIds, u"LastArrivalAtHome",datetime.datetime.now().strftime(_defaultDateStampFormat))

			if updateProps:
					self.deviceStopCommIgnore = time.time()
					carDev.replacePluginPropsOnServer(props)
					carDev	= indigo.devices[int(indigoCarIds)]

			if indigoCarIds in self.updateStatesDict and u"location" in self.updateStatesDict[indigoCarIds]:
				st= ""
				whatForStatus = whatForStatus.split(u"/")
				if u"location" in whatForStatus: st =	   self.updateStatesDict[indigoCarIds][u"location"][u"value"]
				if u"engine"   in whatForStatus: st +="/"+ self.updateStatesDict[indigoCarIds][u"engine"][u"value"]
				if u"motion"   in whatForStatus: st +="/"+ self.updateStatesDict[indigoCarIds][u"motion"][u"value"]
				st = st.strip(u"/").strip(u"/")
				self.addToStatesUpdateDict(indigoCarIds, u"status",st)
				# double check if not already processed somewhere else
				if self.updateStatesDict[indigoCarIds][u"location"][u"value"] == u"home":
					carDev.updateStateImageOnServer(indigo.kStateImageSel.SensorOn)
				else:
					carDev.updateStateImageOnServer(indigo.kStateImageSel.SensorTripped)

			if self.decideMyLog(u"CAR"): self.indiLOG.log(10,u"{}-{} -6- update states: type:{}     car newawayFor={:.0f}[secs]; newhomeFor={:.0f}[secs]".format(carName, indigoCarIds, beaconType, time.time() - self.CARS[u"carId"][indigoCarIds][u"awaySince"], time.time() - self.CARS[u"carId"][indigoCarIds][u"homeSince"] ) )
			if indigoCarIds in self.checkCarsNeed: 
				if self.decideMyLog(u"CAR"): self.indiLOG.log(10,u"{}-{} -7- update states:  checkCarsNeed last={:.0f}[secs]".format(carName, indigoCarIds, (time.time() - self.checkCarsNeed[indigoCarIds])))
			if self.decideMyLog(u"CAR"): self.indiLOG.log(10,u"{}-{} -8- updateStatesList: {}".format(carName, indigoCarIds, self.updateStatesDict) )
		except Exception, e:
			if unicode(e) != u"None":
				self.indiLOG.log(40,u"Line {} has error={}".format(sys.exc_traceback.tb_lineno, e))


		return 


####-------------------------------------------------------------------------####
	def setupCARS(self, carIdi, props, mode="",valuesDict={}):
		try:
			carIds= unicode(carIdi)
			if carIds not in self.CARS[u"carId"]:
				self.CARS[u"carId"][carIds]= {}
			if u"homeSince" not in self.CARS[u"carId"][carIds]:	 self.CARS[u"carId"][carIds][u"homeSince"] = 0
			if u"awaySince" not in self.CARS[u"carId"][carIds]:	 self.CARS[u"carId"][carIds][u"awaySince"] = 0
			if u"beacons"	not in self.CARS[u"carId"][carIds]:	 self.CARS[u"carId"][carIds][u"beacons"]   = {}

			dev = indigo.devices[carIdi]
			if valuesDict !={}:
				update, text = self.setupBeaconsForCARS(valuesDict, carIds)
			else:
				update, text = self.setupBeaconsForCARS(props, carIds)
	 
		except Exception, e:
			if unicode(e) != u"None":
				self.indiLOG.log(40,u"Line {} has error={}".format(sys.exc_traceback.tb_lineno, e))
			if unicode(e).find(u"timeout waiting") > -1:
				self.indiLOG.log(40,u"communication to indigo is interrupted")
			self.indiLOG.log(40,u"devId "+carIds+ u" indigo lookup/save problem")
			return 

		try:
			if mode in [u"init", u"validate"]:
				if self.decideMyLog(u"CAR"): self.indiLOG.log(10,u"setupCARS updating states mode:{};  updateStatesList: {}".format(mode, self.updateStatesDict))
				if u"description" not in props: props[u"description"] = ""
				if props[u"description"] != text:
					props[u"description"]= text
					self.deviceStopCommIgnore = time.time()
					dev.replacePluginPropsOnServer(props)
				self.executeUpdateStatesDict(onlyDevID=carIds,calledFrom = u"setupCARS")
			if update: 
				self.setALLrPiV(u"piUpToDate", [u"updateParamsFTP"])
		except Exception, e:
			if unicode(e) != u"None":
				self.indiLOG.log(40,u"Line {} has error={}".format(sys.exc_traceback.tb_lineno, e))
			return props
		return	props

####-------------------------------------------------------------------------####
	def setupBeaconsForCARS(self, propsCar, carIds):
		try:
			beaconList=[]
			text = u"Beacons:"
			update = False
			if u"setFastDown" in propsCar and propsCar[u"setFastDown"] != u"0":
				setFastDown = int(propsCar[u"setFastDown"])
			else:
				setFastDown = -1

			for beaconType in propsCar:
				if beaconType.find(u"beacon") == -1: continue
				try: beaconID= int(propsCar[beaconType])
				except: continue
				if int(beaconID) == 0: continue
				try:  beaconDev = indigo.devices[beaconID]
				except: continue
				beacon = beaconDev.address
				beaconList.append(beacon)
				self.CARS[u"beacon"][beacon]= {u"carId":carIds, u"beaconType":beaconType}
				if beacon not in self.CARS[u"carId"][carIds][u"beacons"]:  self.CARS[u"carId"][carIds][u"beacons"][beacon] = beaconID
				text += beaconType.split(u"beacon")[1] + u"=" + beaconDev.name + u";"
				props = beaconDev.pluginProps
				if setFastDown >= 0 and props[u"fastDown"] != str(setFastDown):
					props[u"fastDown"] =  str(setFastDown)
					if self.decideMyLog(u"CAR"): self.indiLOG.log(10,u"updating fastdown for {} to {}".format(beaconDev.name, setFastDown) )
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
			if unicode(e) != u"None":
				self.indiLOG.log(40,u"Line {} has error={}".format(sys.exc_traceback.tb_lineno, e))
			if unicode(e).find(u"timeout waiting") > -1:
				self.indiLOG.log(40,u"communication to indigo is interrupted")
				return 1/0
			self.indiLOG.log(40,u"devId: {}; indigo lookup/save problem,  in props:{}   CARS:{}".format(carIds, unicode(props), self.CARS))
		return update,text.strip(u";")

####------================----------- CARS ------================-----------END


####------================------- sprinkler ------================-----------
	########################################
	# Sprinkler Control Action callback
	######################
	def actionControlSprinkler(self, action, dev):
		props		= dev.pluginProps
		#indigo.server.log(u"actionControlSprinkler: "+ unicode(props)+u"\n\n"+ unicode(action))
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
				dictForRPI[u"deviceDefs"] = json.dumps(deviceDefs)
				cmd.append(u"down")
				if u"relayOnIfLow" in props and not props[u"relayOnIfLow"]:
					inverseGPIO.append(False)
				else:
					inverseGPIO.append(True)
			self.sendGPIOCommands( ipNumberPi, piU, cmd, GPIOpin, inverseGPIO)
			if props[ u"PumpControlOn"]: # last valve is the control valve 
				deviceDefs[0][u"gpio"]	   = props[ u"GPIOzone"+unicode(dev.zoneCount)]
				dictForRPI[ u"deviceDefs"] = json.dumps(deviceDefs)
				dictForRPI[ u"cmd"]		   =  u"pulseUp"
				dictForRPI[ u"pulseUp"]	   = dev.zoneMaxDurations[action.zoneIndex-1]*60
				if u"relayOnIfLow" in props and not props[u"relayOnIfLow"]:
					dictForRPI[ u"inverseGPIO"] = False
				else:
					dictForRPI[ u"inverseGPIO"] = True
				self.setPin(dictForRPI)

			self.sleep(0.1)	   ## we need to wait until all gpios are of, other wise then next might be before one of the last off
			deviceDefs[0][u"gpio"]		= props[u"GPIOzone"+unicode(action.zoneIndex)]
			dictForRPI[ u"deviceDefs"]	= json.dumps(deviceDefs)
			dictForRPI[ u"cmd"]			=  u"pulseUp"
			dictForRPI[ u"pulseUp"]		= dev.zoneMaxDurations[action.zoneIndex-1]*60
			if u"relayOnIfLow" in props and not props[u"relayOnIfLow"]:
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
				secDone = (datetime.datetime.now() - datetime.datetime.strptime(zoneStarted,u"%Y-%m-%d %H:%M:%S")).total_seconds()
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
					if u"sprinklerActiveZoneSetManualDuration" in indigo.variables:
						try:	dur = max(0,float(indigo.variables[u"sprinklerActiveZoneSetManualDuration"].value ) )
						except Exception, e:
							self.indiLOG.log(40,u"Line {} has error={}".format(sys.exc_traceback.tb_lineno, e))
							dur = 0
					if dur == 0:  # no overwrite, use max duration
								dur = zoneMaxDurations[activeZone-1]
					allMinutes = 0
					allDur = dur

				timeLeft	= int(max(0,(dur )))
				timeLeftAll = int(max(0,allDur-allMinutes +0.1) )
				dur			= int(dur)
				allDur		= int(allDur)

				self.addToStatesUpdateDict(dev.id, u"activeZone",				 action.zoneIndex)
				self.addToStatesUpdateDict(dev.id, u"activeZoneStarted",		 datetime.datetime.now().strftime(_defaultDateStampFormat))
				self.addToStatesUpdateDict(dev.id, u"activeZoneMinutesLeft",	 timeLeft)
				self.addToStatesUpdateDict(dev.id, u"activeZoneMinutesDuration", dur)
				self.addToStatesUpdateDict(dev.id, u"allZonesMinutesDuration",	 allDur)
				self.addToStatesUpdateDict(dev.id, u"allZonesMinutesLeft",		 timeLeftAll)





		###### ALL ZONES OFF ######
		elif action.sprinklerAction == indigo.kSprinklerAction.AllZonesOff:
			nValves = dev.zoneCount
			GPIOpin =[]
			cmd=[]
			inverseGPIO =[]
			for nn in range(nValves):
				GPIOpin.append(props[u"GPIOzone"+unicode(nn+1)])
				dictForRPI[u"deviceDefs"] = json.dumps(deviceDefs)
				cmd.append(u"down")
				if u"relayOnIfLow" in props and not props[u"relayOnIfLow"]:
					inverseGPIO.append(False)
				else:
					inverseGPIO.append(True)
			self.sendGPIOCommands( ipNumberPi, piU, cmd, GPIOpin, inverseGPIO)
			self.addToStatesUpdateDict(dev.id, u"activeZoneStarted",		"")
			self.addToStatesUpdateDict(dev.id, u"activeZone",				 0)
			self.addToStatesUpdateDict(dev.id, u"activeZoneMinutesLeft",	 0)
			self.addToStatesUpdateDict(dev.id, u"activeZoneMinutesDuration", 0)
			self.addToStatesUpdateDict(dev.id, u"allZonesMinutesLeft",		 0)
			self.addToStatesUpdateDict(dev.id, u"allZonesMinutesDuration",	 0)

		self.executeUpdateStatesDict(onlyDevID=dev.id, calledFrom="")
		return 



####-------------------------------------------------------------------------####
	def initSprinkler(self, force = False):
		#self.lastSprinklerStats = u"2018-05-31 23:23:00"
		self.lastSprinklerStats = datetime.datetime.now().strftime(_defaultDateStampFormat)

		for dev in indigo.devices.iter(u"props.isSprinklerDevice"):
			self.sprinklerDeviceActive = True
			for xx in [u"minutesRunToday", u"minutesRunThisWeek",u"minutesRunYesterday",u"minutesRunLastWeek",u"minutesRunThisMonth",u"minutesRunLastMonth"]:
				lastList = dev.states[xx].split(u",")
				if len(lastList) != dev.zoneCount or force:
					lastList = [u"0" for ii in range(dev.zoneCount)]
					lastList = u",".join(lastList)
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
				for dev in indigo.devices.iter(u"props.isSprinklerDevice"):
					self.addToStatesUpdateDict(dev.id,u"minutesRunYesterday",dev.states[u"minutesRunToday"])
					lastList = [u"0" for ii in range(dev.zoneCount)]
					lastList = u",".join(lastList)
					self.addToStatesUpdateDict(dev.id,u"minutesRunToday",lastList)

					if newWeek:
						self.addToStatesUpdateDict(dev.id,u"minutesRunLastWeek",dev.states[u"minutesRunThisWeek"])
						lastList = [u"0" for ii in range(dev.zoneCount)]
						lastList = u",".join(lastList)
						self.addToStatesUpdateDict(dev.id,u"minutesRunThisWeek",lastList)

					if newMonth:
						self.addToStatesUpdateDict(dev.id,u"minutesRunLastMonth",dev.states[u"minutesRunThisMonth"])
						lastList = [u"0" for ii in range(dev.zoneCount)]
						lastList = u",".join(lastList)
						self.addToStatesUpdateDict(dev.id,u"minutesRunThisMonth",lastList)

					self.executeUpdateStatesDict(onlyDevID=dev.id)



			for dev in indigo.devices.iter(u"props.isSprinklerDevice"):
				props			   = dev.pluginProps
				try:	activeZone = int(dev.states[u"activeZone"])
				except: activeZone = 0
				if activeZone == 0: 
					self.addToStatesUpdateDict(dev.id, u"activeZoneMinutesLeft",	 0)
					self.addToStatesUpdateDict(dev.id, u"activeZoneMinutesDuration", 0)
					self.addToStatesUpdateDict(dev.id, u"allZonesMinutesLeft",		 0)
					self.addToStatesUpdateDict(dev.id, u"allZonesMinutesDuration",	 0)

				else:
					if props[u"PumpControlOn"]: nValves = dev.zoneCount-1
					else: nValves	 = dev.zoneCount
					durations		 = dev.zoneScheduledDurations
					zoneMaxDurations = dev.zoneMaxDurations
					zoneStarted		 = dev.states[u"activeZoneStarted"] # show date time when started . long string 

					if len(zoneStarted) > 10:  # show date time when started . long string 
						secDone = (datetime.datetime.now() - datetime.datetime.strptime(zoneStarted, "%Y-%m-%d %H:%M:%S")).total_seconds()
						minutes	 = int(secDone/60)

						try:	allDur = int(dev.states[u"allZonesMinutesDuration"])
						except: allDur = 0
						if len(durations) == nValves:
							dur		= min(durations[activeZone-1], zoneMaxDurations[activeZone-1])
							allMinutes = minutes
							if activeZone <= len(durations) and activeZone > 1:
								for mm in durations[0:activeZone-1]:
									allMinutes += mm
						else :
							dur		   = int(dev.states[u"activeZoneMinutesDuration"])
							allMinutes = minutes

						timeLeft	=  int(max(0,(dur	 - minutes)+0.1) )
						timeLeftAll =  int(max(0,(allDur - allMinutes)+0.1) )


						self.addToStatesUpdateDict(dev.id, u"activeZoneMinutesLeft",   timeLeft)
						self.addToStatesUpdateDict(dev.id, u"allZonesMinutesLeft",	   timeLeftAll)

					else: # show date time when started .if short , not started
						self.addToStatesUpdateDict(dev.id, u"activeZoneMinutesLeft",   0)
						self.addToStatesUpdateDict(dev.id, u"allZonesMinutesLeft",	   0)


					for xx in [u"minutesRunToday", u"minutesRunThisWeek", "minutesRunThisMonth"]:
						lastList = dev.states[xx].split(u",")
						if len(lastList) != dev.zoneCount:
							lastList = [u"0" for ii in range(dev.zoneCount)]
						lastList[activeZone-1] = unicode( int(lastList[activeZone-1])+1 )
						if props[u"PumpControlOn"] :
							lastList[dev.zoneCount-1] = unicode( int(lastList[dev.zoneCount-1])+1 )
						lastList = u",".join(lastList)
						self.addToStatesUpdateDict(dev.id,xx,lastList)


				self.executeUpdateStatesDict(onlyDevID=dev.id)
		except Exception, e:
			if unicode(e) != u"None":
				self.indiLOG.log(40,u"Line {} has error={}".format(sys.exc_traceback.tb_lineno, e))

####------================------- sprinkler ------================-----------END


####-------------------------------------------------------------------------####
	def readConfig(self):  ## only once at startup
		try:

			self.readTcpipSocketStats()


			self.RPI = self.getParamsFromFile(self.indigoPreferencesPluginDir+u"RPIconf")
			if self.RPI =={}: 
				self.indiLOG.log(20,self.indigoPreferencesPluginDir + "RPIconf file does not exist or has bad data, will do a new setup ")


			self.RPIVersion20 = (len(self.RPI) == 20) and len(self.RPI) > 0
			if self.RPIVersion20:
				self.indiLOG.log(30,u"RPIconf adding # of rpi  from 20 ..40 ")

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
					if piProp == u"enableiBeacons":
						self.RPI[piU][piProp] = u"1"


				delProp=[]
				for piProp in self.RPI[piU]:
					if piProp not in _GlobalConst_emptyRPI:
						delProp.append(piProp)
				for piProp in delProp:
					del self.RPI[piU][piProp]
				delSen={}
				for sensor in self.RPI[piU][u"input"]:
					if sensor not in _GlobalConst_allowedSensors and sensor not in _BLEsensorTypes: delSen[sensor]=1
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
					if piProp == u"enableiBeacons":
						self.RPI[piU][piProp] = u"0"

				for piProp in delProp:
					del self.RPI[piU][piProp]

				for iii in [u"input",u"output"]:
					delSens={}
					for sensor in self.RPI[piU][iii]:

						delDev ={}
						for devId in self.RPI[piU][iii][sensor]:
							try:	 indigo.devices[int(devId)]
							except:	 delDev[devId] = True
						for devId in delDev:
							del self.RPI[piU][iii][sensor][devId]
							self.indiLOG.log(20,u"RPI cleanup {} del {} devId:{}".format(piU, iii, devId)  )

						if self.RPI[piU][iii][sensor] =={}:
							delSens[sensor]=True

					for sensor in delSens:
						self.indiLOG.log(20,u"RPI cleanup {} deleting {}  {}".format(piU, iii, sensor) )
						del self.RPI[piU][iii][sensor]


			for piU in self.RPI:
				if self.RPI[piU][u"piOnOff"] == u"0": 
					self.resetUpdateQueue(piU)


			self.beacons = self.getParamsFromFile(self.indigoPreferencesPluginDir+ "beacons")

			delList={}
			
			for beacon in self.beacons:
				if type(self.beacons[beacon]) !=type({}):
					self.indiLOG.log(20,u"beacon: {}, type:{}".format(beacon, type(self.beacons[beacon])))
					self.indiLOG.log(20,u"beacons: {}".format(self.beacons[beacon]))
					delList[beacon] = True
					continue
				for nn in _GlobalConst_emptyBeacon:
					if nn not in self.beacons[beacon]:
						self.beacons[beacon][nn]=copy.deepcopy(_GlobalConst_emptyBeacon[nn])

				if self.beacons[beacon][u"indigoId"] == 0: continue

				try:
					dev = indigo.devices[self.beacons[beacon][u"indigoId"]]
				except Exception, e:
					self.indiLOG.log(40,u"Line {} has error={}".format(sys.exc_traceback.tb_lineno, e))
					self.indiLOG.log(40,u"beacon: {} not an indigo device, removing from beacon list".format(beacon))
					delList[beacon]= True
					continue

				chList=[]
				if u"closestRPI" in dev.states: # must be RPI ..
					if dev.states[u"closestRPI"] == "": 
						chList.append({u"key":"closestRPI", u"value":-1})
						if self.setClostestRPItextToBlank: chList.append({u"key":"closestRPIText", u"value":""})
					self.execUpdateStatesList(dev,chList)

				for piU in _rpiBeaconList:
					pi= int(piU)
					try:
						piXX = u"Pi_{:02d}".format(pi)
						try:    d =  float(dev.states[piXX+u"_Distance"])
						except: d = 99999.
						try:    s =  float(dev.states[piXX+u"_Signal"])
						except: s = -999
						try:    t =  float(dev.states[piXX+u"_Time"])
						except: t = 0.
						try: 	self.beacons[beacon][u"receivedSignals"][pi]
						except: self.beacons[beacon][u"receivedSignals"].append({})
						if len(self.beacons[beacon][u"receivedSignals"][pi]) == 2:
							self.beacons[beacon][u"receivedSignals"][pi] = {u"rssi":s, u"lastSignal":t, u"distance":d}
						elif len(self.beacons[beacon][u"receivedSignals"][pi]) !=3:
							self.beacons[beacon][u"receivedSignals"][pi] = {u"rssi":s, u"lastSignal":t, u"distance":d}
						elif type(self.beacons[beacon][u"receivedSignals"][pi]) != type({}):
							self.beacons[beacon][u"receivedSignals"][pi] = {u"rssi":s, u"lastSignal":t, u"distance":d}

						lastUp= self.getTimetimeFromDateString(dev.states[piXX+u"_Time"])
						if self.beacons[beacon][u"receivedSignals"][pi][u"lastSignal"] > lastUp: continue # time entry
						self.beacons[beacon][u"receivedSignals"][pi][u"rssi"] = float(dev.states[piXX+u"_Signal"])
						self.beacons[beacon][u"receivedSignals"][pi][u"lastSignal"] = lastUp
					except:
						pass
			for beacon in delList:
				del self.beacons[beacon]

			self.currentVersion		 	= self.getParamsFromFile(self.indigoPreferencesPluginDir+u"currentVersion", default="0")


			self.readknownBeacontags()


			self.readCARS()

			self.startUpdateRPIqueues(u"start")

			self.startDelayedActionQueue()

			self.checkDevToRPIlinks()

			self.indiLOG.log(10,u" ..   config read from files")
			self.fixConfig(checkOnly = [u"all",u"rpi",u"beacon",u"CARS",u"sensors",u"output",u"force"], fromPGM=u"readconfig") 
			self.saveConfig()

		except Exception, e:
			if unicode(e) != u"None":
				self.indiLOG.log(40,u"Line {} has error={}".format(sys.exc_traceback.tb_lineno, e))
			exit(1)


####-------------------------------------------------------------------------####
	def readknownBeacontags(self):  
		try:
			## cleanup from older version
			if os.path.isfile(self.indigoPreferencesPluginDir+u"knownBeaconTags"):
				os.remove(self.indigoPreferencesPluginDir+u"knownBeaconTags")

			self.knownBeaconTags = {}
			try:
				f = open(self.pathToPlugin + u"knownBeaconTags.json", u"r")
				self.knownBeaconTags = json.loads(f.read())
				f.close()
				for tag in self.knownBeaconTags:
					self.knownBeaconTags[tag][u"hexCode"] = self.knownBeaconTags[tag][u"hexCode"].upper()
			except Exception, e:
				if unicode(e) != u"None":
					self.indiLOG.log(40,u"Line {} has error={}".format(sys.exc_traceback.tb_lineno, e))
				try: f.close()
				except: pass
				return False

			## write empty supplicant file 
			if not os.path.isfile(self.indigoPreferencesPluginDir+u"knownBeaconTags.supplicant"):
				self.writeJson( {}, fName=self.indigoPreferencesPluginDir + u"knownBeaconTags.supplicant")

			## add to default from supplicant if any data, only new tags will be added
			knownBeaconTagsSupplicant 	= self.getParamsFromFile(self.indigoPreferencesPluginDir+u"knownBeaconTags.supplicant")
			if len(knownBeaconTagsSupplicant)> 0:
				self.indiLOG.log(20,u"adding  tags from  knownBeaconTags.supplicant: {} ".format(knownBeaconTagsSupplicant))
				for tag in knownBeaconTagsSupplicant:
					if tag not in self.knownBeaconTags:
						self.knownBeaconTags[tag] = copy.copy(self.knownBeaconTags[u"other"])
						for item in self.knownBeaconTags[u"other"]:
							if type(self.knownBeaconTags[u"other"][item]) == type(1):
								try:	self.knownBeaconTags[tag][item] = int(knownBeaconTagsSupplicant[tag][item])
								except:
										self.indiLOG.log(30,u"bad item in knownBeaconTags.supplicant: {} {}".format(item,knownBeaconTagsSupplicant[tag][item] ))
										continue
							self.knownBeaconTags[tag][item] = copy.copy(knownBeaconTagsSupplicant[tag][item])
							self.indiLOG.log(20,u"added  item from knownBeaconTags.supplicant: {} {}".format(item,knownBeaconTagsSupplicant[tag][item] ))
						
			self.writeJson( self.knownBeaconTags, fName=self.indigoPreferencesPluginDir + u"knownBeaconTags.full_copy_to_use_as_example", fmtOn=True,  toLog=False )
			self.writeJson( self.knownBeaconTags, fName=self.indigoPreferencesPluginDir + u"all/knownBeaconTags", fmtOn=True )

			for typeOfBeacon in self.knownBeaconTags:
				self.knownBeaconTags[typeOfBeacon][u"hexCode"] = self.knownBeaconTags[typeOfBeacon][u"hexCode"].upper()
			### knwon beacon tags section END ###

		except Exception, e:
			if unicode(e) != u"None":
				self.indiLOG.log(40,u"Line {} has error={}".format(sys.exc_traceback.tb_lineno, e))
				return False
		return True


####-------------------------------------------------------------------------####
	def checkDevToRPIlinks(self): # called from read config for various input files
		try:

			for dev in indigo.devices.iter(u"props.isSensorDevice"):
				props = dev.pluginProps
				if u"piServerNumber" in props:
					try: pix = int(props[u"piServerNumber"]) 
					except: continue
				else: continue
				for pi in range(len(self.RPI)):
					if pi == pix or pix == 99 or (pi >= _GlobalConst_numberOfiBeaconRPI and pix == 90):
						piU = str(pi)
						if u"input" not in self.RPI[piU]: continue
						if u"piDevId" not in self.RPI[piU] or self.RPI[piU][u"piDevId"] <=0: continue
						typeId = dev.deviceTypeId 
						if typeId not in self.RPI[piU][u"input"]:
							self.RPI[piU][u"input"][typeId] = {}
						if str(dev.id) not in self.RPI[piU][u"input"][typeId]:
							self.indiLOG.log(30,u"adding back input sensor {:20s}  type:{:30s} to RPI:{:1s}".format(dev.name, dev.deviceTypeId, piU))
							self.RPI[piU][u"input"][typeId][str(dev.id)] = {}


			for dev in indigo.devices.iter(u"props.isOutputDevice"):
				props = dev.pluginProps
				if u"piServerNumber" in props:
					try: piU = unicode(int(props[u"piServerNumber"]))
					except: continue
				else: continue
				if u"output" not in self.RPI[piU]: continue
				typeId = dev.deviceTypeId 
				if typeId not in self.RPI[piU][u"output"]:
					self.RPI[piU][u"output"][typeId] ={}
				if str(dev.id) not in self.RPI[piU][u"output"][typeId]:
					self.indiLOG.log(30,u"adding back out device {} to RPI:{}".format(dev.name, piU))
					self.RPI[piU][u"output"][typeId][str(dev.id)] = {}


		except Exception, e:
			if unicode(e) != u"None":
				self.indiLOG.log(40,u"Line {} has error={}".format(sys.exc_traceback.tb_lineno, e))

####-------------------------------------------------------------------------####
	def getParamsFromFile(self, newName, oldName="", default={}): # called from read config for various input files
		try:
			out = copy.deepcopy(default)
			#self.indiLOG.log(20,u"getParamsFromFile newName:{} oldName: {}; default:{}".format(newName, oldName, unicode(default)[0:100]))
			if os.path.isfile(newName):
				try:
					f = open(newName, u"r")
					out	 = json.loads(f.read())
					f.close()
					if oldName !="" and os.path.isfile(oldName):
						subprocess.call(u"rm "+oldName, shell=True)
				except Exception, e:
					self.indiLOG.log(40,u"Line {} has error={}".format(sys.exc_traceback.tb_lineno, e))
					out =copy.deepcopy(default)
			else:
				out = copy.deepcopy(default)
			if oldName !="" and os.path.isfile(oldName):
				try:
					f = open(oldName, u"r")
					out	 = json.loads(f.read())
					f.close()
					subprocess.call(u"rm "+oldName, shell=True)
				except Exception, e:
					self.indiLOG.log(40,u"Line {} has error={}".format(sys.exc_traceback.tb_lineno, e))
					out = copy.deepcopy(default)
			#self.indiLOG.log(20,u"getParamsFromFile out:{} ".format(unicode(out)[0:100]) )
		except Exception, e:
			if unicode(e) != u"None":
				self.indiLOG.log(40,u"Line {} has error={}".format(sys.exc_traceback.tb_lineno, e))
		return out

####-------------------------------------------------------------------------####
	def savebeaconPositionsFile(self):
		try:	
			self.setImageParameters()
			f = open(self.indigoPreferencesPluginDir + u"plotPositions/positions.json", u"w")
			f.write(json.dumps(self.beaconPositionsData))
			f.close()
			if self.decideMyLog(u"PlotPositions"): self.indiLOG.log(10,u"savebeaconPositionsFile {}".format(unicode(self.beaconPositionsData[u"mac"])[0:100])  )
		except Exception, e:
			if unicode(e) != u"None":
				self.indiLOG.log(40,u"Line {} has error={}".format(sys.exc_traceback.tb_lineno, e))
		return

####-------------------------------------------------------------------------####
	def setImageParameters(self):
		try:	
			self.beaconPositionsData[u"piDir"]			= self.indigoPreferencesPluginDir+u"plotPositions"
			self.beaconPositionsData[u"logLevel"]		= u"PlotPositions" in self.debugLevel
			self.beaconPositionsData[u"logFile"]		= self.PluginLogFile
			self.beaconPositionsData[u"distanceUnits"]	= self.distanceUnits
		except Exception, e:
			if unicode(e) != u"None":
				self.indiLOG.log(40,u"Line {} has error={}".format(sys.exc_traceback.tb_lineno, e))
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
						if indigoId == 0 or indigoId == "":			 continue
						try:	dev = indigo.devices[indigoId]
						except: continue
						if self.beaconPositionsData[u"ShowExpiredBeacons"] == u"0" and dev.states[u"status"] == u"expired": continue
						props = dev.pluginProps

						if u"showBeaconOnMap" not in props or props[u"showBeaconOnMap"] == u"0":
							if beacon in self.beaconPositionsData[u"mac"]:
								del self.beaconPositionsData[u"mac"][beacon]
							changed = True

						elif u"showBeaconOnMap"	in props and props[u"showBeaconOnMap"] in _GlobalConst_beaconPlotSymbols:
							if beacon not in self.beaconPositionsData[u"mac"]:
								changed = True
							try:	distanceToRPI = float(dev.states[u"Pi_{:02d}_Distance".format(int(dev.states[u"closestRPI"]))])
							except: distanceToRPI = 0.5
							# State "Pi_8_Signal" of "b-radius-3"
							if dev.states[u"status"] == u"expired": useSymbol = u"square45"
							else:								   useSymbol = props[u"showBeaconOnMap"]
							if len(props[u"showBeaconSymbolColor"])!= 7: showBeaconSymbolColor = u"#0F0F0F"
							else:								   		 showBeaconSymbolColor = props[u"showBeaconSymbolColor"].upper()
							if len(props[u"showBeaconTextColor"])!= 7:   showBeaconTextColor = u"#0FFF0F"
							else:								   		 showBeaconTextColor = props[u"showBeaconTextColor"].upper()
							self.beaconPositionsData[u"mac"][beacon]={u"name":dev.name,
								u"position":			[float(dev.states[u"PosX"]),float(dev.states[u"PosY"]),float(dev.states[u"PosZ"])],
								u"nickName":			props[u"showBeaconNickName"],
								u"symbolType":			useSymbol,
								u"symbolColor":			showBeaconSymbolColor,
								u"symbolAlpha":			props[u"showBeaconSymbolAlpha"] ,
								u"distanceToRPI":		distanceToRPI ,
								u"textColor":			showBeaconTextColor ,
								u"bType":				u"beacon" ,
								u"status":				dev.states[u"status"]					}
					except Exception, e:
							self.indiLOG.log(40,u"Line {} has error={}".format(sys.exc_traceback.tb_lineno, e))

			for dev in indigo.devices.iter(u"props.isBLEconnectDevice"):
					try:
						props = dev.pluginProps
						beacon = props[u"macAddress"]
						if u"showBeaconOnMap" not in props: continue
						if props[u"showBeaconOnMap"] == u"0": continue
						if self.beaconPositionsData[u"ShowExpiredBeacons"] == u"0" and dev.states[u"status"] == u"expired": continue
						props = dev.pluginProps

						if u"showBeaconOnMap" not in props or props[u"showBeaconOnMap"] ==u"0":
							if beacon in self.beaconPositionsData[u"mac"]:
								del self.beaconPositionsData[u"mac"][beacon]
							changed = True

						elif u"showBeaconOnMap"	in props and props[u"showBeaconOnMap"] in _GlobalConst_beaconPlotSymbols:
							if beacon not in self.beaconPositionsData[u"mac"]:
								changed = True
							try:	distanceToRPI = float(dev.states[u"Pi_{:02d}_Distance".format(int(dev.states[u"closestRPI"]))])
							except: distanceToRPI = 0.5
							if dev.states[u"status"] == u"expired": useSymbol = u"square45"
							else:								   useSymbol = props[u"showBeaconOnMap"]
							if len(props[u"showBeaconSymbolColor"])!= 7: showBeaconSymbolColor = u"#0F0F0F"
							else:								   		 showBeaconSymbolColor = props[u"showBeaconSymbolColor"].upper()
							if len(props[u"showBeaconTextColor"])!= 7:   showBeaconTextColor = u"#0FFF0F"
							else:								   		 showBeaconTextColor = props[u"showBeaconTextColor"].upper()
							self.beaconPositionsData[u"mac"][beacon]={u"name":dev.name,
								u"position":			[float(dev.states[u"PosX"]),float(dev.states[u"PosY"]),float(dev.states[u"PosZ"])],
								u"nickName":			props[u"showBeaconNickName"],
								u"symbolType":			useSymbol,
								u"symbolColor":			showBeaconSymbolColor,
								u"symbolAlpha":			props[u"showBeaconSymbolAlpha"] ,
								u"distanceToRPI":		distanceToRPI ,
								u"textColor":			showBeaconTextColor ,
								u"bType":				u"BLEconnect" ,
								u"status":				dev.states[u"status"]					}
					except Exception, e:
							self.indiLOG.log(40,u"Line {} has error={}".format(sys.exc_traceback.tb_lineno, e))



			if self.beaconPositionsData[u"ShowRPIs"] in	 _GlobalConst_beaconPlotSymbols:
				for piU in _rpiBeaconList:
					if self.RPI[piU][u"piOnOff"]  == u"0": continue
					if self.RPI[piU][u"piDevId"]  == u"0": continue
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
							if self.beaconPositionsData[u"ShowRPIs"] ==u"square": nickN =  u" R-"+piU
							else:												  nickN =  u"R-"+piU
							self.beaconPositionsData[u"mac"][beacon]={u"name":u"RPI-"+piU,
								u"position":			 pos,
								u"nickName":			 nickN,
								u"symbolType":			 self.beaconPositionsData[u"ShowRPIs"],
								u"symbolColor":			 u"#00F000",
								u"symbolAlpha":			 u"0.5" ,
								u"distanceToRPI":		 1.0 ,
								u"textColor":			 u"#008000" ,
								u"bType":				 u"RPI" ,
								u"status":				 dev.states[u"status"]					}
					except:
							continue
	#						 self.indiLOG.log(40,u"Line {} has error={}".format(sys.exc_traceback.tb_lineno, e))
	 
			if changed or self.beaconPositionsUpdated>0: 
					self.savebeaconPositionsFile()
					cmd = self.pythonPath + u" '" + self.pathToPlugin + u"makeBeaconPositionPlots.py' '"+self.indigoPreferencesPluginDir+u"plotPositions/' & "
					if self.decideMyLog(u"PlotPositions"): 
						self.indiLOG.log(20,u"makeNewBeaconPositionPlots .. beaconPositionsUpdated: {}".format(self.beaconPositionsUpdated))
						self.indiLOG.log(20,u"makeNewBeaconPositionPlots cmd: {} ".format(cmd) )
					subprocess.call(cmd, shell=True)

		except Exception, e:
			if unicode(e).find(u"timeout waiting") > -1:
				self.indiLOG.log(40,u"Line {} has error={}".format(sys.exc_traceback.tb_lineno, e))
				self.indiLOG.log(40,u"communication to indigo is interrupted")
				return 
			if e != None	and unicode(e).find(u"not found in database") ==-1:
				self.indiLOG.log(40,u"Line {} has error={}".format(sys.exc_traceback.tb_lineno, e))

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
			#self.indiLOG.log(30,u"rpi:{}".format(self.RPI) )
			for piU1 in _rpiBeaconList:
				pi1 = int(piU1)
				if self.RPI[piU1][u"piDevId"] == 0:   continue
				if self.RPI[piU1][u"piDevId"] == "": continue
				devii = indigo.devices[self.RPI[piU1][u"piDevId"]]
				propsii= devii.pluginProps
				Pii = self.getPosXYZ(devii,propsii,piU1)
				self.piPosition[pi1]=Pii
				for pi2 in range(pi1+1, _GlobalConst_numberOfiBeaconRPI):
					piU2 = unicode(pi2)
					try:
						if self.RPI[piU2][u"piDevId"] == 0:   continue
						if self.RPI[piU2][u"piDevId"] == "": continue
						devjj = indigo.devices[self.RPI[piU2][u"piDevId"]]
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
					except Exception, e:
						self.indiLOG.log(40,u"Line {} has error={}".format(sys.exc_traceback.tb_lineno, e))
		except Exception, e:
			if unicode(e) != u"None":
				self.indiLOG.log(40,u"Line {} has error={}".format(sys.exc_traceback.tb_lineno, e))
		return True

####-------------------------------------------------------------------------####
	def getPosXYZ(self,dev,props,piU):
		try: 
			if u"PosXYZ" not in props:
				props[u"PosXYZ"] = u"0,0,0"
				self.deviceStopCommIgnore = time.time()
				dev.replacePluginPropsOnServer(props)
				self.indiLOG.log(40,u"Error= fixing props for  RPI#"+piU)
			Pjj = props[u"PosXYZ"].split(u",")

			if len(Pjj) != 3:
				props[u"PosXYZ"] = u"0,0,0"
				self.deviceStopCommIgnore = time.time()
				dev.replacePluginPropsOnServer(props)

			Pjj = props[u"PosXYZ"].split(u",")
			return [float(Pjj[0]),float(Pjj[1]),float(Pjj[2])]

		except Exception, e:
			self.indiLOG.log(40,u"Line {} has error={}".format(sys.exc_traceback.tb_lineno, e)  +u" fixing props, you might need to edit RPI#"+piU)
			props[u"PosXYZ"] ="0,0,0"
			self.deviceStopCommIgnore = time.time()
			dev.replacePluginPropsOnServer(props)
		return [0,0,0]

####-------------------------------------------------------------------------####
	def fixConfig(self,checkOnly = [u"all"],fromPGM=""):
		try:
			try:
				if  self.decideMyLog(u"Logic"): self.indiLOG.log(10,u"fixConfig called from "+fromPGM +u"; with:"+unicode(checkOnly) )
				# dont do it too often
				if time.time() - self.lastFixConfig < 25: return
				self.lastFixConfig	= time.time()

				nowDD = datetime.datetime.now()
				dateString = nowDD.strftime(_defaultDateStampFormat)
				anyChange= False

				if u"rpi" in checkOnly or u"all" in checkOnly:
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
									props[u"addNewOneWireSensors"] = u"0"
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
									if self.RPI[piU][u"piOnOff"] != u"1":
										try:	del self.checkIPSendSocketOk[self.RPI[piU][u"ipNumberPi"]]
										except: pass
									self.RPI[piU][u"piOnOff"] = u"1"
								else:
									self.RPI[piU][u"piOnOff"] = u"0"

								if upd:
									self.deviceStopCommIgnore = time.time()
									dev.replacePluginPropsOnServer(props)
									dev= indigo.devices[piDevId]
									anyChange = True

						except Exception, e:
							if unicode(e).find(u"timeout waiting") > -1:
								self.indiLOG.log(40,u"Line {} has error={}".format(sys.exc_traceback.tb_lineno, e))
								self.indiLOG.log(40,u"communication to indigo is interrupted")
								return
							self.sleep(0.2)
							if self.RPI[piU][u"piDevId"] !=0:
								try:
									self.indiLOG.log(40,u"Line {} has error={}".format(sys.exc_traceback.tb_lineno, e))
									self.indiLOG.log(40,u"error normal if rpi has been deleted, removing from list: setting piDevId=0")
								except: pass
								self.delRPI(pi=piU, calledFrom=u"fixConfig")
							anyChange = True

						if self.RPI[piU][u"piOnOff"] != u"0":
							if not self.isValidIP(self.RPI[piU][u"ipNumberPi"]):
								self.RPI[piU][u"piOnOff"] = u"0"
								anyChange = True
								continue
			except Exception, e:
				self.indiLOG.log(40,u"Line {} has error={}".format(sys.exc_traceback.tb_lineno, e))

			try:
				if u"all" in checkOnly:
					delDEV = []
					for dev in indigo.devices.iter(u"props.isCARDevice,props.isBeaconDevice,props.isRPIDevice,props.isRPISensorDevice,props.isSensorDevice"):
						props=dev.pluginProps

						if dev.deviceTypeId==u"car": 
							newP = self.setupCARS(dev.id,props,mode="init")
							if newP[u"description"] != dev.description:
								if self.decideMyLog(u"CAR"): self.indiLOG.log(20,u"replacing car props {}  {}  {}".format(dev.name,  newP[u"description"], dev.description) )
								dev.description =  newP[u"description"] 
								dev.replaceOnServer()
								anyChange = True
							continue

						if dev.deviceTypeId !=u"beacon" and u"description" in props:
							if props[u"description"] !="":
								if dev.description != props[u"description"]:
									dev.description = props[u"description"]
									self.indiLOG.log(20,u"{} updating descriptions {}".format(dev.name, props[u"description"]))
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
								self.indiLOG.log(20,u"{} fixing ipNumber in RPI device props to {}".format(dev.name, self.RPI[piU][u"ipNumberPi"]))
								dev.description = u"Pi-{}-{}".format(pi,self.RPI[piU][u"ipNumberPi"])
								dev.replaceOnServer()
								props[u"ipNumberPi"] = self.RPI[piU][u"ipNumberPi"]  
								self.deviceStopCommIgnore = time.time()
								dev.replacePluginPropsOnServer(props)
								anyChange = True

							if u"ipNumberPi" in props and self.isValidIP(props[u"ipNumberPi"]) and self.RPI[piU][u"ipNumberPi"] != props[u"ipNumberPi"]:
								self.indiLOG.log(20,u"{} fixing ipNumber in RPI device props to {}".format(dev.name, props[u"ipNumberPi"]))
								self.RPI[piU][u"ipNumberPi"]  = props[u"ipNumberPi"]
								anyChange = True

							if dev.id != self.RPI[piU][u"piDevId"]:
								self.indiLOG.log(20,u"dev :{} fixing piDevId in RPI".format(dev.name) )
								self.RPI[piU][u"piDevId"]	 = dev.id
								anyChange = True

							if len(beacon)> 6 and self.RPI[piU][u"piMAC"] != beacon:
								self.indiLOG.log(20,u"dev: {}  fixing piMAC in RPI".format(dev.name))
								self.RPI[piU][u"piMAC"]	   = beacon
								anyChange = True

							if u"userIdPi" in props and	 self.RPI[piU][u"userIdPi"] != props[u"userIdPi"]:
								self.indiLOG.log(20,u"dev: {} fixing userIdPi in RPI".format(dev.name))
								self.RPI[piU][u"userIdPi"]	  = props[u"userIdPi"]
								anyChange = True

							if u"passwordPi" in props and  self.RPI[piU][u"passwordPi"] != props[u"passwordPi"]:
								self.indiLOG.log(20,u"dev: {} fixing passwordPi in RPI".format(dev.name))
								self.RPI[piU][u"passwordPi"]	= props[u"passwordPi"]
								anyChange = True

							if dev.deviceTypeId == u"rPI":
								beacon = dev.address
								if self.isValidMAC(beacon):
									if beacon not in self.beacons:
										self.beacons[beacon] = copy.deepcopy(_GlobalConst_emptyBeacon)
										self.beacons[beacon][u"typeOfBeacon"] = u"rPI"
										self.beacons[beacon][u"indigoId"] = dev.id
										checkOnly.append(u"beacon")
										checkOnly.append(u"force")

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

						if u"force" in checkOnly:
							if self.fixDevProps(dev) == -1:
								delDEV.append(dev)
								anyChange = True

					for dev in delDEV:
						self.indiLOG.log(30,u"fixConfig dev: {}  has no addressfield".format(dev.name))
						# indigo.device.delete(dev)
			except Exception, e:
				self.indiLOG.log(40,u"Line {} has error={}".format(sys.exc_traceback.tb_lineno, e))

			try:
				if u"all" in checkOnly or "beacon" in checkOnly:
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
											self.indiLOG.log(30,u"fixConfig fixing: beacon should not in beacon list: {}  {}  {}".format(beacon, dev.name, dev.deviceTypeId ) )
										except:
											self.indiLOG.log(30,u"fixConfig fixing: beacon should not in beacon list: {} no name / device {}".format(beacon, dev.deviceTypeId ) )
										remove.append(beacon)
										anyChange = True
										continue



									beaconDEV = props[u"address"]
									if beaconDEV != beacon:
										self.beacons[beacon][u"indigoId"] = 0
										self.indiLOG.log(20,u"fixing: {}  beaconDEV:{}  beacon:{} beacon wrong, using current beacon-mac".format(dev.name, beaconDEV, beacon))
										anyChange = True

									self.beacons[beacon][u"enabled"]				 = dev.enabled
									try:
										self.beacons[beacon][u"status"]					 = dev.states[u"status"]
										self.beacons[beacon][u"note"]					 = dev.states[u"note"]
										self.beacons[beacon][u"typeOfBeacon"]			 = props[u"typeOfBeacon"]
										self.beacons[beacon][u"beaconTxPower"]			 = props[u"beaconTxPower"]
										self.beacons[beacon][u"created"]				 = dev.states[u"created"]
										self.beacons[beacon][u"iBeacon"]				 = dev.states[u"iBeacon"]
										self.beacons[beacon][u"showBeaconOnMap"]	 = props[u"showBeaconOnMap"] 
									except: pass

									dev.updateStateOnServer(u"TxPowerSet",int(props[u"beaconTxPower"]))
									if u"fastDown" in props: # not for RPI
										pass
									else:
										self.indiLOG.log(20,u"{} has no fastDown".format(dev.name))

									if u"updateSignalValuesSeconds" in props: # not for RPIindigoIdindigoIdindigoIdindigoIdindigoId
										self.beacons[beacon][u"updateSignalValuesSeconds"] = float(props[u"updateSignalValuesSeconds"])
									else:
										self.beacons[beacon][u"updateSignalValuesSeconds"] = 300
								except Exception, e:
									anyChange = True
									if unicode(e).find(u"timeout waiting") > -1:
										self.indiLOG.log(40,u"Line {} has error={}".format(sys.exc_traceback.tb_lineno, e))
										self.indiLOG.log(40,u"communication to indigo is interrupted")
										return 
									elif unicode(e).find(u"not found in database") >-1:
										self.beacons[beacon][u"indigoId"] =0
										continue
									else:
										self.indiLOG.log(40,u"Line {} has error={}".format(sys.exc_traceback.tb_lineno, e))
										self.indiLOG.log(40,u"dev={}".format(dev.name))
										return 


							else:
								self.beacons[beacon][u"updateSignalValuesSeconds"] = copy.copy(_GlobalConst_emptyBeacon[u"updateSignalValuesSeconds"])
					for beacon in remove:
						self.indiLOG.log(20, u"fixConfig:  deleting beacon:{}  {}".format(beacon, self.beacons[beacon]))
						del self.beacons[beacon]

			except Exception, e:
				self.indiLOG.log(40,u"Line {} has error={}".format(sys.exc_traceback.tb_lineno, e))
			#self.indiLOG.log(20,u"fixConfig time elapsed point C  "+unicode(time.time()- self.lastFixConfig) +u"     anyChange: "+ unicode(anyChange))

			try:
				if u"rpi" in checkOnly or u"all" in checkOnly:
					for beacon in self.beacons:
						if self.beacons[beacon][u"typeOfBeacon"].lower() == u"rpi":
							if self.beacons[beacon][u"note"].find(u"Pi-") == 0:
								try:
									pi = int(self.beacons[beacon][u"note"].split(u"-")[1])
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
											for xyz in [u"PosX",u"PosY",u"PosZ"]:
												if dev.states[xyz] != self.RPI[piU][xyz]: dev.updateStateOnServer(xyz, self.RPI[piU][xyz] )

									except Exception, e:
										if unicode(e).find(u"timeout waiting") > -1:
											self.indiLOG.log(40,u"Line {} has error={}".format(sys.exc_traceback.tb_lineno, e))
											self.indiLOG.log(40,u"communication to indigo is interrupted")
											return
										elif unicode(e).find(u"not found in database") >-1:
											self.beacons[beacon][u"indigoId"] = 0
											anyChange = True
											self.indiLOG.log(20,	u"fixConfig anychange: (fix) set indigoID=0,  beacon, pi, devid "+ unicode(beacon) +u"  "+ piU +u"  "+ unicode(devId) )
											continue
										else:
											self.indiLOG.log(40,u"Line {} has error={}".format(sys.exc_traceback.tb_lineno, e))
											self.indiLOG.log(40,u"unknown error")
											return

			except Exception, e:
				self.indiLOG.log(40,u"Line {} has error={}".format(sys.exc_traceback.tb_lineno, e))


			if u"rpi" in checkOnly:
				self.calcPitoPidist()

			if u"all" in checkOnly:
				if self.syncSensors(): anyChange = True

			if anyChange or (time.time() - self.lastSaveConfig) > 100:
				self.lastSaveConfig = time.time() 
				self.saveConfig()

		except Exception, e:
			if unicode(e) != u"None":
				self.indiLOG.log(40,u"Line {} has error={}".format(sys.exc_traceback.tb_lineno, e))
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
			if unicode(e) != u"None":
				self.indiLOG.log(40,u"Line {} has error={}".format(sys.exc_traceback.tb_lineno, e))
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
			if unicode(e) != u"None":
				self.indiLOG.log(40,u"Line {} has error={}".format(sys.exc_traceback.tb_lineno, e))


####-------------------------------------------------------------------------####
	def writeJson(self,data, fName="", fmtOn=False, toLog=False):
		try:

			if format:
				out = json.dumps(data, sort_keys=True, indent=2)
			else:
				out = json.dumps(data)

			if fName !="":
				if toLog: self.indiLOG.log(20,u"json writing data:\n{}\n to fname:{}".format(data, fName))
				f=open(fName,u"w")
				f.write(out)
				f.close()
			return out

		except Exception, e:
			if unicode(e) != u"None":
				self.indiLOG.log(40,u"Line {} has error={}".format(sys.exc_traceback.tb_lineno, e))
		return ""

####-------------------------------------------------------------------------####
	def saveConfig(self, only="all"):

		try:
			if only in [u"all", "RPIconf"]:
				self.writeJson(self.RPI, fName=self.indigoPreferencesPluginDir + u"RPIconf", fmtOn=self.RPIFileSort)

			if only in [u"all"]:
				self.saveCARS()

			if only in [u"all"]:
				self.writeJson(self.beacons, fName=self.indigoPreferencesPluginDir + "beacons", fmtOn=self.beaconsFileSort)

			if only in [u"all"]:
				self.makeBeacons_parameterFile()

			if only in [u"all"]:
				self.writeJson( self.knownBeaconTags,   fName=self.indigoPreferencesPluginDir + u"all/knownBeaconTags", fmtOn=True)

		except Exception, e:
			if unicode(e) != u"None":
				self.indiLOG.log(40,u"Line {} has error={}".format(sys.exc_traceback.tb_lineno, e))
		return 

####-------------------------------------------------------------------------####
	def fixDevProps(self, dev):
		dateString = datetime.datetime.now().strftime(_defaultDateStampFormat)
		updateProps = False
		props = dev.pluginProps
		if dev.deviceTypeId == u"rPI-Sensor":
			if len(unicode(dev.address)) < 2 or unicode(dev.address) == u"-None-" or dev.address is None:
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

		if dev.deviceTypeId == u"beacon":
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
		if dev.deviceTypeId == u"rPI":
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
			self.indiLOG.log(30,u"=== deleting dev :" + dev.name + " has no address field, please do NOT manually create beacon devices")
			self.indiLOG.log(30,u"fixDevProps  props" + unicode(props))
			indigo.device.delete(dev)
			return -1

	   
		try:
			beacon = props[u"address"]
			if u"beaconTxPower" not in props:
				props[u"beaconTxPower"] = _GlobalConst_emptyBeacon[u"beaconTxPower"]
				updateProps = True

			if u"typeOfBeacon" not in props:
				if dev.deviceTypeId ==u"beacon":
					props[u"typeOfBeacon"] = _GlobalConst_emptyBeacon[u"typeOfBeacon"]
					updateProps = True
				if dev.deviceTypeId == u"rPI" :
					props[u"typeOfBeacon"] = u"rPI"
					updateProps = True

			if props[u"typeOfBeacon"] in self.knownBeaconTags and int(props[u"beaconTxPower"]) == 999:
				props[u"beaconTxPower"] = self.knownBeaconTags[props[u"typeOfBeacon"]][u"dBm"]
				updateProps = True

			if u"updateSignalValuesSeconds" not in props:
				updateProps = True
				if (dev.deviceTypeId.lower()) == u"rpi" :
					props[u"updateSignalValuesSeconds"] = 300
				else:
					props[u"updateSignalValuesSeconds"] = _GlobalConst_emptyBeaconProps[u"updateSignalValuesSeconds"]
			if u"signalDelta" not in props:
				updateProps = True
				props[u"signalDelta"] = _GlobalConst_emptyBeaconProps[u"signalDelta"]
			if u"minSignalOff" not in props:
				updateProps = True
				props[u"minSignalOff"] = _GlobalConst_emptyBeaconProps[u"minSignalOff"]
			if u"minSignalOn" not in props:
				updateProps = True
				props[u"minSignalOn"] = _GlobalConst_emptyBeaconProps[u"minSignalOn"]
			if u"fastDown" not in props:
				updateProps = True
				props[u"fastDown"] = _GlobalConst_emptyBeaconProps[u"fastDown"]

			try:
				created = dev.states[u"created"]
			except:
				created = ""
			if created == "":
				updateProps = True
				self.addToStatesUpdateDict(dev.id,u"created", dateString)
			if u"expirationTime" not in props:
				updateProps = True
				props[u"expirationTime"] = 90.

			if updateProps:
				self.deviceStopCommIgnore = time.time()
				dev.replacePluginPropsOnServer(props)
				if self.decideMyLog(u"Logic"): self.indiLOG.log(10,u"updating props for " + dev.name + " in fix props")

			if dev.deviceTypeId == u"beacon" :
				noteState = u"beacon-" + props[u"typeOfBeacon"] 
				if dev.states[u"note"] != noteState:
					self.addToStatesUpdateDict(dev.id,u"note",noteState)
			else:  
				noteState = dev.states[u"note"]		 


			if beacon not in self.beacons:
				self.indiLOG.log(20,u"fixDevProps: adding beacon from devices to self.beacons: {} dev:{}".format(beacon, dev.name))
				self.beacons[beacon] = copy.deepcopy(_GlobalConst_emptyBeacon)
			self.beacons[beacon][u"created"]		  = dev.states[u"created"]
			self.beacons[beacon][u"indigoId"]		  = dev.id
			self.beacons[beacon][u"status"]			  = dev.states[u"status"]
			if dev.deviceTypeId == u"beacon" :
				self.beacons[beacon][u"typeOfBeacon"] = u"other"
			else:
				self.beacons[beacon][u"typeOfBeacon"] = u"rPI"
			self.beacons[beacon][u"note"]			  = noteState
			self.beacons[beacon][u"typeOfBeacon"]	  = props[u"typeOfBeacon"]
			if u"useOnlyPrioTagMessageTypes" in props:
				self.beacons[beacon][u"useOnlyPrioTagMessageTypes"]	= props[u"useOnlyPrioTagMessageTypes"]
			else:
				self.beacons[beacon][u"useOnlyPrioTagMessageTypes"]	= u"1"
			self.beacons[beacon][u"beaconTxPower"]	  = int(props[u"beaconTxPower"])
			self.beacons[beacon][u"expirationTime"]	  = float(props[u"expirationTime"])
			self.beacons[beacon][u"updateSignalValuesSeconds"] = float(props[u"updateSignalValuesSeconds"])

		except Exception, e:
			if unicode(e) != u"None":
				self.indiLOG.log(40,u"Line {} has error={}".format(sys.exc_traceback.tb_lineno, e))

		return 0





####-------------------------------------------------------------------------####
	def deviceStartComm(self, dev):
		try:
			#self.indiLOG.log(20,u"deviceStartComm called for dev={}, stopcom ignore:{}".format(dev.name, self.deviceStopCommIgnore) )

			props = dev.pluginProps
			dev.stateListOrDisplayStateIdChanged()	# update  from device.xml info if changed
			if self.pluginState == u"init":

				doSensorValueAnalog =[u"Wire18B20",u"DHT",u"i2cTMP102",u"i2cMCP9808",u"i2cLM35A",u"i2cT5403",
				u"i2cMS5803",u"i2cBMPxx",u"tmp006",u"tmp007",u"i2cSHT21""i2cAM2320",u"i2cBMExx",u"bme680",u"bmp388",u"si7021",
				u"BLERuuviTag",
				u"BLEminewE8",
				u"BLEminewS1TH",
				u"BLEminewS1TT",
				u"BLEaprilAccel",u"BLEaprilTHL", 
				"max31865",
				u"pmairquality",
				u"BLEmyBLUEt",u"sgp30",
				u"mhzCO2",
				u"ccs811",u"rainSensorRG11",u"as3935",
				u"ina3221", "ina219",
				u"i2cADC121",
				u"i2cADS1x15-1", u"i2cADS1x15"
				u"spiMCP3008-1", u"spiMCP3008",
				u"PCF8591",u"ADS1x15",
				u"MAX44009",
				u"i2cTCS34725", u"as726x", u"i2cOPT3001", u"i2cVEML7700", u"i2cVEML6030", u"i2cVEML6040", u"i2cVEML6070", u"i2cVEML6075", u"i2cTSL2561", 
				u"mlx90614", u"amg88xx", u"mlx90640",u"lidar360",
				u"vl503l0xDistance", u"vcnl4010Distance", u"vl6180xDistance", u"apds9960", u"ultrasoundDistance",
				u"INPUTpulse"]

				doSensorValueOnOff =[u"INPUTgpio-1",u"INPUTgpio-4",u"INPUTgpio-8",u"INPUTgpio-26",
				"INPUTtouch-1",u"INPUTtouch-4",u"INPUTtouch-12",u"INPUTtouch-16",
				"rPI",u"rPI-Sensor",u"beacon",u"BLEconnect"]

				if int(self.currentVersion.split(u".")[0]) < 7:
					self.indiLOG.log(20,u" checking for deviceType upgrades: {}".format(dev.name) )
					if dev.deviceTypeId in doSensorValueAnalog:
						props = dev.pluginProps
						if u"SupportsSensorValue" not in props:
							self.indiLOG.log(20,u" processing: {}".format(dev.name) )
							dev = indigo.device.changeDeviceTypeId(dev, dev.deviceTypeId)
							dev.replaceOnServer()
							dev = indigo.devices[dev.id]
							props = dev.pluginProps
							props[u"SupportsSensorValue"] 		= True
							props[u"SupportsOnState"] 			= False
							props[u"AllowSensorValueChange"] 	= False
							props[u"AllowOnStateChange"] 		= False
							props[u"SupportsStatusRequest"] 	= False
							self.deviceStopCommIgnore = time.time()
							dev.replacePluginPropsOnServer(props)
							self.indiLOG.log(20,u"SupportsSensorValue  after replacePluginPropsOnServer")

					if dev.deviceTypeId in doSensorValueOnOff:
						props = dev.pluginProps
						if u"SupportsOnState" not in props:
							self.indiLOG.log(20,u" processing: {}".format(dev.name) )
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
							if dev.deviceTypeId in [u"rPI",u"rPI-Sensor",u"beacon",u"BLEconnect"]:
								dev= indigo.devices[dev.id]
								dev.updateStateOnServer(u"onOffState",(dev.states[u"status"].lower()).find(u"up")==0, uiValue=dev.states[u"displayStatus"] )
								if (dev.states[u"status"].lower()) in [u"up",u"on"]:
									dev.updateStateImageOnServer(indigo.kStateImageSel.SensorOn)
								elif (dev.states[u"status"].lower()) in [u"down",u"off"]:
									dev.updateStateImageOnServer(indigo.kStateImageSel.SensorOff)
								else:
									dev.updateStateImageOnServer(indigo.kStateImageSel.SensorTripped)
								dev.replaceOnServer()

							self.indiLOG.log(20,u"SupportsOnState after replacePluginPropsOnServer")

				updProps = False
				if dev.deviceTypeId == u"beacon":
					if u"useOnlyPrioTagMessageTypes" not in props:
						props[u"useOnlyPrioTagMessageTypes"] = u"0"
						updProps = True
					if u"typeOfBeacon" not in props:
						props[u"typeOfBeacon"] = u"other"
						updProps = True

					if props[u"typeOfBeacon"] not in self.knownBeaconTags:
						for tag in self.knownBeaconTags:
							if tag.upper() == props[u"typeOfBeacon"].upper():
								props[u"typeOfBeacon"] = tag
								updProps = True
								break
					if u"version" not in props:
						props[u"version"] = dev.states[u"typeOfBeacon"]
						updProps = True

				if updProps:
					dev.replacePluginPropsOnServer(props)

				if dev.deviceTypeId in [u"rPI",u"rPI-Sensor"]:
					upd = False
					if u"ipNumber" in props:
						if u"ipNumberPi" not in props:
							props[u"ipNumberPi"] = props[u"ipNumber"]
						del props[u"ipNumber"]
						upd = True
					piNo = dev.states[u"note"].split(u"-")
					if len(piNo) !=2:
						self.deviceStopCommIgnore = time.time()
						dev.updateStateOnServer(u"note",u"Pi-"+piNo[-1])

					if upd: 
						self.deviceStopCommIgnore = time.time()
						dev.replacePluginPropsOnServer(props)

				self.statusChanged=2

			if dev.deviceTypeId == u"beacon":
				updProps = False
				if dev.deviceTypeId == u"beacon":
					if u"useOnlyPrioTagMessageTypes" not in props:
						props[u"useOnlyPrioTagMessageTypes"] = u"0"
						updProps = True
					if u"typeOfBeacon" not in props:
						props[u"typeOfBeacon"] = u"other"
						updProps = True

					if props[u"typeOfBeacon"] not in self.knownBeaconTags:
						for tag in self.knownBeaconTags:
							if tag.upper() == props[u"typeOfBeacon"].upper():
								props[u"typeOfBeacon"] = tag
								updProps = True
								break
					if u"version" not in props:
						props[u"version"] = dev.states[u"typeOfBeacon"]
						updProps = True
				typeOfBeacon = props[u"typeOfBeacon"]
				if typeOfBeacon in self.knownBeaconTags and self.knownBeaconTags[typeOfBeacon][u"beepCmd"] == u"off":
					dev.updateStateOnServer(u"isBeepable",u"not capable")
				else:
					dev.updateStateOnServer(u"isBeepable",u"YES")
				beacon = dev.address
				if beacon not in self.beacons:
					self.beacons[beacon] = copy.copy(_GlobalConst_emptyBeacon)
				self.beacons[beacon][u"typeOfBeacon"] = typeOfBeacon
				self.beacons[beacon][u"useOnlyPrioTagMessageTypes"] = props[u"useOnlyPrioTagMessageTypes"]
				self.beacons[beacon][u"enabled"] = dev.enabled

			if dev.deviceTypeId.find(u"rPI") > -1:
				piNo = dev.states[u"note"].split(u"-")
				try: 	self.RPI[str(int(piNo[-1]))][u"piOnOff"] = u"1"
				except: pass
				if time.time() - self.deviceStopCommIgnore  > 0.1:
					self.deviceStopCommIgnore = 0
					self.updateNeeded = u" enable startcomm called "

			if dev.deviceTypeId == u"sprinkler":
				self.sprinklerDeviceActive = True

		except Exception, e:
			if unicode(e) != u"None":
				self.indiLOG.log(40,u"Line {} has error={}".format(sys.exc_traceback.tb_lineno, e))

####-------------------------------------------------------------------------####
	def deviceDeleted(self, dev):  ### indigo calls this 
		props= dev.pluginProps

		if u"address" in props: 
				beacon = props[u"address"]
				if beacon in self.beacons and beacon.find(u"00:00:00:00") ==-1:
					if u"indigoId" in self.beacons[beacon] and	self.beacons[beacon][u"indigoId"] == dev.id:
						self.indiLOG.log(20,u"-setting beacon device in internal tables to 0:  " + dev.name+u"  "+unicode(dev.id)+u" enabled:"+ unicode(dev.enabled)+ "  pluginState:"+ self.pluginState)
						self.beacons[beacon][u"indigoId"] = 0
						self.beacons[beacon][u"ignore"]	  = 1
						self.writeJson(self.beacons, fName=self.indigoPreferencesPluginDir + "beacons", fmtOn=self.beaconsFileSort)
		if dev.deviceTypeId.find(u"rPI") > -1:
			try:
				pi = dev.description.split(u"-")
				if len(pi) > 0:
					self.delRPI(pi=pi[1], calledFrom=u"deviceDeleted")
			except:
				pass
		self.deviceStopComm(dev)
		return

####-------------------------------------------------------------------------####
	def deviceStopComm(self, dev):
		#self.indiLOG.log(20,u"deviceStopComm called for dev={}, stopcom ignore:{}".format(dev.name, self.deviceStopCommIgnore) )
		try:
			props= dev.pluginProps
			if self.pluginState != u"stop":

				if self.freezeAddRemove : self.sleep(0.2)

				if time.time() - self.deviceStopCommIgnore  > 0.1:
					self.deviceStopCommIgnore = 0
					self.updateNeeded = u" disable stopcomm called "

				self.statusChanged=2

			if dev.deviceTypeId.find(u"rPI") > -1:
				piNo = dev.states[u"note"].split(u"-")
				try: 	self.RPI[str(int(piNo[-1]))][u"piOnOff"] ="0"
				except: pass

			if dev.deviceTypeId.find(u"beacon") > -1:
				if dev.address in self.beacons:
					self.beacons[dev.address][u"enabled"] = False


		except Exception, e:
			if unicode(e) != u"None":
				self.indiLOG.log(40,u"Line {} has error={}".format(sys.exc_traceback.tb_lineno, e))


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
			if typeId in [u"beacon", u"rPI", u"rPI-Sensor"]:
				if typeId != u"rPI-Sensor":
					if u"address" in theDictList[0]: # 0= valuesDict,1 = errors dict
						if theDictList[0][u"address"] != u"00:00:00:00:00:00": 
							theDictList[0][u"newMACNumber"] = copy.copy(theDictList[0][u"address"])
						else:
							theDictList[0][u"newMACNumber"] = ""

				dev = indigo.devices[devId]
				props = dev.pluginProps


				if typeId.find(u"rPI") >- 1:
					try:
						if u"MSG" in theDictList[0]:
							theDictList[0][u"enablePiNumberMenu"]  = True
						else:
							theDictList[0][u"newauthKeyOrPassword"]  = u"assword"
							theDictList[0][u"newenableRebootCheck"]  = u"restartLoop"
							theDictList[0][u"enablePiNumberMenu"]  = True


						piU= u"-1"
						rpiNo = dev.states[u"note"].split(u"-")

						try:	
							piU = str(int(rpiNo[1]))
							theDictList[0][u"RPINumber"] = piU
						except: 
							if typeId == u"rPI-Sensor":
								for piU1 in _rpiSensorList:
									if self.RPI[piU1][u"piDevId"] == 0:
										theDictList[0][u"RPINumber"] = piU1
										break
							else:
								for piU2 in _rpiList:
									if self.RPI[piU2][u"piDevId"] == 0:
										theDictList[0][u"RPINumber"] = piU2
										break

						theDictList[0][u"newIPNumber"]   = self.RPI[piU][u"ipNumberPi"]
						theDictList[0][u"newpasswordPi"] = self.RPI[piU][u"passwordPi"]
						theDictList[0][u"newuserIdPi"]   = self.RPI[piU][u"userIdPi"]
						theDictList[0][u"newauthKeyOrPassword"]   = self.RPI[piU][u"authKeyOrPassword"]

						if typeId =="rPI" and piU == u"-1":
								theDictList[0][u"newMACNumber"] = u"00:00:00:00:pi:00"
					except Exception, e:
						self.indiLOG.log(30,u"Line {} has error={}".format(sys.exc_traceback.tb_lineno, e))

				if typeId.find(u"beacon") >- 1:
						beacon = dev.address
						if beacon in self.beacons:
							typeOfBeacon = self.beacons[beacon][u"typeOfBeacon"]
							if u"batteryLevelUUID" not in theDictList[0]: # only for new devices
								if typeOfBeacon in self.knownBeaconTags:
									if  type(self.knownBeaconTags[typeOfBeacon][u"battCmd"]) == type({}) and "uuid" in self.knownBeaconTags[typeOfBeacon][u"battCmd"]:
										theDictList[0][u"SupportsBatteryLevel"]  = True
										theDictList[0][u"batteryLevelUUID"]  	 = u"gatttool"
									if  type(self.knownBeaconTags[typeOfBeacon][u"battCmd"]) == type("") and "msg"  in self.knownBeaconTags[typeOfBeacon][u"battCmd"]:
										theDictList[0][u"SupportsBatteryLevel"]  = True
										theDictList[0][u"batteryLevelUUID"]  	 = u"msg"

			if "isRPION08" in theDictList[0] or "rPiEnable8" in theDictList[0]:
				for piU in _rpiBeaconList:
					piUstr = "{:02d}".format(int(piU))
					if self.RPI[piU]["piOnOff"] == "1" and self.isValidIP(self.RPI[piU]["ipNumberPi"]) :	
						theDictList[0]["isRPION"+piUstr] = True
					else:								
						theDictList[0]["isRPION"+piUstr] = False

			if "memberOfFamily" in theDictList[0] or typeId in [u"beacon", u"rPI", u"BLEconnect"]:
				for nn in range(len(_GlobalConst_groupList)):
					group = _GlobalConst_groupList[nn]
					groupNameUsedForVar = self.groupListUsedNames[group]
					if len(groupNameUsedForVar) < 1:
						theDictList[0][u"groupName{}".format(nn)] = u"this group is not used, set name in config"
						theDictList[0][u"groupEnable{}".format(nn)] = False
						theDictList[0][u"memberOf"+group] = False
					else:
						theDictList[0][u"groupName{}".format(nn)] = groupNameUsedForVar
						theDictList[0][u"groupEnable{}".format(nn)] = True

							
			#self.indiLOG.log(30,u"theDictList {}".format(unicode(theDictList[0])))


			return theDictList 
		except Exception, e:
			self.indiLOG.log(40,u"Line {} has error={}".format(sys.exc_traceback.tb_lineno, e))

		return super(Plugin, self).getDeviceConfigUiValues(pluginProps, typeId, devId)



####-------------------------------------------------------------------------####
####-------------------------------------------------------------------------####
####----------- device edit validation section -      -----------------------####
####-------------------------------------------------------------------------####
	def validateDeviceConfigUi(self, valuesDict, typeId, devId):

		errorCode = False
		errorDict = indigo.Dict()
		valuesDict[u"MSG"] = u"OK"
		update 	= 0
		beacon 	= u"xx"
		thisPi 	= u"-1"
		piU 	= u"-1"
		retCode = False
		try: 
			dev = indigo.devices[devId]
			props = dev.pluginProps	
			beacon = ""
			if typeId in [u"beacon", u"rPI"]:
				try:
					beacon = props[u"address"]
				except: pass
			if  len(beacon) < 8: 
				beacon = u"00:00:00:00:pi:00"

			if typeId.find(u"rPI") > -1:
				for piU in self.RPI:
					if devId == self.RPI[piU][u"piDevId"]:
						thisPi = piU
						break
				try: thisPiV = unicode(int(valuesDict[u"RPINumber"]))
				except: thisPiV = u"-1"
				if thisPi =="-1" or (thisPiV != u"-1" and thisPi != thisPiV): 
					if  thisPi != u"-1":
						self.RPI[thisPiV] = copy.deepcopy(self.RPI[thisPi])
					self.RPI[thisPi] = copy.deepcopy(_GlobalConst_emptyRPI)
					thisPi = thisPiV
				valuesDict[u"RPINumber"] = thisPi 

			if typeId in [u"rPI-Sensor",u"rPI"]:
				if thisPi == u"-1":
					valuesDict[u"enablePiNumberMenu"] = True
					valuesDict, errorDict  = self.setErrorCode(valuesDict,errorDict,  "bad RPI Number")
					return ( False, valuesDict, errorDict )

				if not self.isValidIP(valuesDict[u"newIPNumber"]):
					valuesDict, errorDict  = self.setErrorCode(valuesDict,errorDict,  "bad IP Number")
					return ( False, valuesDict, errorDict )

				if len(valuesDict[u"newpasswordPi"]) < 2:
					valuesDict, errorDict  = self.setErrorCode(valuesDict,errorDict,  "bad password")
					return ( False, valuesDict, errorDict )

				if len(valuesDict[u"newuserIdPi"]) < 2:
					valuesDict, errorDict  = self.setErrorCode(valuesDict,errorDict,  "bad userId for Pi")
					return ( False, valuesDict, errorDict )
		except Exception, e:
			self.indiLOG.log(40,u"setting up RPI--beacon Line {} has error={}".format(sys.exc_traceback.tb_lineno, e))
			valuesDict, errorDict  = self.setErrorCode(valuesDict,errorDict,  "pgm error, check log")
			return ( False, valuesDict, errorDict )


		try:
	
			# fix STATUS state, INPUT_x was split into several devices, each has "INPUT" not INPUT_0/1/2/3/4..  
			if u"displayS" in valuesDict and valuesDict[u"displayS"].find(u"INPUT_") >-1: 
				fix = True
				for state in dev.states:
					if state.find(u"INPUT_") >- 1: 
						fix = False 
						break
				if fix: valuesDict[u"displayS"] = u"INPUT"

			if   typeId == u"car":					retCode, valuesDict, errorDict = self.validateDeviceConfigUi_Cars(		 	valuesDict, errorDict, typeId, thisPi, piU, props, beacon, dev)

			elif typeId == u"sprinkler":				retCode, valuesDict, errorDict = self.validateDeviceConfigUi_Sprinkler(	 	valuesDict, errorDict, typeId, thisPi, piU, props, beacon, dev)

			elif typeId ==u"BLEconnect":			retCode, valuesDict, errorDict = self.validateDeviceConfigUi_BLEconnect(	valuesDict, errorDict, typeId, thisPi, piU, props, beacon, dev)

			elif typeId == u"rPI-Sensor":			retCode, valuesDict, errorDict = self.validateDeviceConfigUi_rPISensor(	 	valuesDict, errorDict, typeId, thisPi, piU, props, beacon, dev)

			elif typeId == u"rPI":					retCode, valuesDict, errorDict = self.validateDeviceConfigUi_rPI(			valuesDict, errorDict, typeId, thisPi, piU, props, beacon, dev)

			elif typeId == u"beacon":				retCode, valuesDict, errorDict = self.validateDeviceConfigUi_beacon(		valuesDict, errorDict, typeId, thisPi, piU, props, beacon, dev)

			elif typeId.find(u"INPUTgpio")>-1 or typeId.find(u"INPUTtouch")>-1:
													retCode, valuesDict, errorDict = self.validateDeviceConfigUi_INPUTG(		valuesDict, errorDict, typeId, thisPi, piU, props, beacon, dev)

			elif typeId.find(u"INPUTRotatary")>-1 :	retCode, valuesDict, errorDict = self.validateDeviceConfigUi_INPUTRotatary(	valuesDict, errorDict, typeId, thisPi, piU, props, beacon, dev)

			elif typeId.find(u"OUTPUTgpio-") > -1 or typeId.find(u"OUTPUTi2cRelay") > -1:
													retCode, valuesDict, errorDict = self.validateDeviceConfigUi_OUTPUTG(		valuesDict, errorDict, typeId, thisPi, piU, props, beacon, dev)

			elif typeId in _GlobalConst_allowedSensors or typeId in _BLEsensorTypes:
													retCode, valuesDict, errorDict = self.validateDeviceConfigUi_sensors(		valuesDict, errorDict, typeId, thisPi, piU, props, beacon, dev)

			elif typeId in _GlobalConst_allowedOUTPUT:
													retCode, valuesDict, errorDict = self.validateDeviceConfigUi_output(		valuesDict, errorDict, typeId, thisPi, piU, props, beacon, dev)

			else:
				valuesDict[u"MSG"] = u" bad dev type:".format(typeId)
				self.indiLOG.log(40,u" bad device type:{} not in registed types:\n,_GlobalConst_allowedSensors:{}\n _BLEsensorTypes:{}\n _GlobalConst_allowedOUTPUT:{}\n... ".format(typeId, _GlobalConst_allowedSensors, _BLEsensorTypes, _GlobalConst_allowedOUTPUT))


			if retCode:	
				self.updateNeeded += u" fixConfig "
				return True, valuesDict

			else: 				
				return (False, valuesDict, errorDict )


		except Exception, e:
			if unicode(e) != u"None":
				self.indiLOG.log(40,u"Line {} has error={}".format(sys.exc_traceback.tb_lineno, e))
			if unicode(e).find(u"timeout waiting") > -1:
				valuesDict, errorDict  = self.setErrorCode(valuesDict,errorDict,  "communication to indigo is interrupted")
			else:
				valuesDict, errorDict  = self.setErrorCode(valuesDict,errorDict, "please fill out all fields")
			return ( False, valuesDict, errorDict )

		self.updateNeeded += u" fixConfig "
		valuesDict, errorDict = self.setErrorCode(valuesDict,errorDict,  "  ??   error .. ?? " ) 
		return ( False, valuesDict, errorDict )





####-------------------------------------------------------------------------####
	def validateDeviceConfigUi_Cars(self, valuesDict, errorDict, typeId, thisPi, piU, props, beacon, dev):
		try:
			self.setupCARS(dev.id,valuesDict,mode="validate")
			return True, errorDict, valuesDict
		except Exception, e:
			if unicode(e) != u"None":
				self.indiLOG.log(40,u"Line {} has error={}".format(sys.exc_traceback.tb_lineno, e))
			return False, errorDict, valuesDict

####-------------------------------------------------------------------------####
	def validateDeviceConfigUi_Sprinkler(self, valuesDict, errorDict, typeId, thisPi, piU, props, beacon, dev):
		try:
			valuesDict[u"address"] = u"Pi-"+valuesDict[u"piServerNumber"]
			return True, errorDict, valuesDict
		except Exception, e:
			if unicode(e) != u"None":
				self.indiLOG.log(40,u"Line {} has error={}".format(sys.exc_traceback.tb_lineno, e))
			return False, errorDict, valuesDict


############ RPI- BLEconnect  -------
	def validateDeviceConfigUi_BLEconnect(self, valuesDict, errorDict, typeId, thisPi, piU, props, beacon, dev):
		try:
			if len(valuesDict[u"macAddress"]) == len(u"01:02:03:04:05:06"):
				self.addToStatesUpdateDict(dev.id,u"TxPowerSet", int(valuesDict[u"beaconTxPower"]))
				valuesDict[u"macAddress"] = valuesDict[u"macAddress"].upper()
			else:
				valuesDict, errorDict  = self.setErrorCode(valuesDict,errorDict,  "bad Mac Number")
				return ( False, valuesDict, errorDict )
			BLEMAC = valuesDict[u"macAddress"].upper()

			active = ""
			for piU in _rpiBeaconList:
				pi = int(piU)
				if valuesDict[u"rPiEnable"+piU] and self.RPI[piU][u"piDevId"] >0:
					if typeId not in self.RPI[piU][u"input"]:
						self.RPI[piU][u"input"][typeId]={}
					if unicode(dev.id) not in self.RPI[piU][u"input"][typeId]:
						self.RPI[piU][u"input"][typeId][unicode(dev.id)]=""
					self.RPI[piU][u"input"][typeId][unicode(dev.id)] = BLEMAC
					active+=" "+piU+u","
				else:
					if typeId in self.RPI[piU][u"input"] and  unicode(dev.id) in self.RPI[piU][u"input"][typeId]:
						del	 self.RPI[piU][u"input"][typeId][unicode(dev.id)]
				valuesDict[u"description"] = u"on Pi "+ active.strip(u",")
				valuesDict[u"address"] = BLEMAC

				### remove if not on this pi:
				if typeId in self.RPI[piU][u"input"] and self.RPI[piU][u"input"][typeId] == {}:
					del self.RPI[piU][u"input"][typeId]
				if typeId not in self.RPI[piU][u"input"] and typeId in self.RPI[piU][u"sensorList"]:
						self.RPI[piU][u"sensorList"] = self.RPI[piU][u"sensorList"].replace(typeId+u",","")

				if True:
					self.rPiRestartCommand[pi] +="BLEconnect,"
					self.updateNeeded += u" fixConfig "
					self.setONErPiV(piU,u"piUpToDate", [u"updateParamsFTP"])

			memberList = ""
			for nn in range(len(_GlobalConst_groupList)):
				group = _GlobalConst_groupList[nn]
				groupNameUsedForVar = self.groupListUsedNames[group]
				GN = u"memberOf"+group

				if GN in valuesDict:
					if len(groupNameUsedForVar) == 0: 
						valuesDict[GN] = False
						
					if unicode(valuesDict[GN]).lower() == u"true":
						memberList += groupNameUsedForVar+u"/"
						if unicode(dev.id) not in self.groupStatusList[group][u"members"]:
							self.groupStatusList[group][u"members"][unicode(dev.id)] = True
					else:
						if unicode(dev.id) in self.groupStatusList[group][u"members"]:
							del self.groupStatusList[group][u"members"][unicode(dev.id)]
						
				else:
						if unicode(dev.id) in self.groupStatusList[group][u"members"]:
							del self.groupStatusList[group][u"members"][unicode(dev.id)]


			memberList = memberList.strip(u"/")
			if dev.states[u"groupMember"] != memberList:
				self.addToStatesUpdateDict(dev.id,u"groupMember", memberList)
	
			indigo.server.log("validateDeviceConfigUi_BLEconnect  groupListUsedNames:{}   \ngroupStatusList{}:".format(self.groupListUsedNames, self.groupStatusList))

			return (True, valuesDict, errorDict)
		except Exception, e:
			self.indiLOG.log(40,u"setting up BLEconnect Line {} has error={}".format(sys.exc_traceback.tb_lineno, e))
			valuesDict, errorDict  = self.setErrorCode(valuesDict,errorDict,  "pgm error, check log")
			return ( False, valuesDict, errorDict )



############ RPI- sensors  -------
	def validateDeviceConfigUi_rPISensor(self, valuesDict, errorDict, typeId, thisPi, piU, props, beacon, dev):
		try: 
			self.RPI[piU][u"piOnOff"] 				= u"1"
			self.RPI[thisPi][u"piDevId"] 			= dev.id
			self.RPI[thisPi][u"userIdPi"] 			= valuesDict[u"newuserIdPi"]
			self.RPI[thisPi][u"passwordPi"] 		= valuesDict[u"newpasswordPi"]
			self.RPI[thisPi][u"authKeyOrPassword"]	= valuesDict[u"newauthKeyOrPassword"]  
			self.RPI[thisPi][u"enableRebootCheck"]	= valuesDict[u"newenableRebootCheck"]  
			valuesDict[u"passwordPi"]				= valuesDict[u"newpasswordPi"]
			valuesDict[u"userIdPi"] 				= valuesDict[u"newuserIdPi"]
			self.RPI[thisPi][u"ipNumberPi"]			= valuesDict[u"newIPNumber"]
			valuesDict[u"ipNumberPi"] 				= valuesDict[u"newIPNumber"]
			valuesDict[u"address"] 					= u"Pi-{}".format(thisPi)
			valuesDict[u"description"] 				= u"Pi-{}-{}".format(thisPi, valuesDict[u"newIPNumber"])
			self.RPI[thisPi][u"sendToIndigoSecs"]	= valuesDict[u"sendToIndigoSecs"]
			self.RPI[thisPi][u"sensorRefreshSecs"]	= valuesDict[u"sensorRefreshSecs"]
			self.RPI[thisPi][u"deltaChangedSensor"]	= valuesDict[u"deltaChangedSensor"]
			self.setONErPiV(thisPi,"piUpToDate", [u"updateParamsFTP"])
			self.rPiRestartCommand[int(thisPi)] 	= u"master"
			self.updateNeeded 					   += u" fixConfig "
			self.saveConfig(only=u"RPIconf")
			return (True, valuesDict, errorDict)
		except Exception, e:
			self.indiLOG.log(40,u"setting up RPI-Sensor Line {} has error={}".format(sys.exc_traceback.tb_lineno, e))
			valuesDict, errorDict  = self.setErrorCode(valuesDict,errorDict,  u"pgm error, check log")
			return ( False, valuesDict, errorDict )




############ RPI  -------
	def validateDeviceConfigUi_rPI(self, valuesDict, errorDict, typeId, thisPi, piU, props, beacon, dev):
		try:
			if u"address" not in props: new = True
			else:						new = False
			newMAC = valuesDict[u"newMACNumber"].upper()
			valuesDict[u"newMACNumber"] = newMAC
			if not self.isValidMAC(newMAC):
				valuesDict[u"newMACNumber"] = beacon
				valuesDict, errorDict  = self.setErrorCode(valuesDict,errorDict,  u"bad Mac Number")
				return ( False, valuesDict, errorDict )

			if not new:
				if beacon != newMAC:
					self.indiLOG.log(20,u"replacing RPI BLE mac {} with {}".format(beacon, newMAC) )
					piFound =-1
					for piU in _rpiBeaconList: 
						if self.RPI[piU][u"piMAC"] == newMAC:
							self.indiLOG.log(20,u"replacing RPI BLE mac failed. rpi already exists with this MAC number")
							valuesDict, errorDict  = self.setErrorCode(valuesDict,errorDict,  "bad beacon#, already exist as RPI")
							return ( False, valuesDict, errorDict )

					self.indiLOG.log(20,u"replacing existing beacon")
					if newMAC not in self.beacons:
						self.beacons[newMAC] = copy.deepcopy(_GlobalConst_emptyBeacon)
						self.beacons[newMAC][u"note"] = u"PI-"+thisPi
					else:
						if beacon in self.beacons:
							self.beacons[newMAC] = copy.deepcopy(self.beacons[beacon])
						else:
							self.beacons[newMAC] = copy.deepcopy(_GlobalConst_emptyBeacon)
					self.newADDRESS[dev.id]			= newMAC
					valuesDict[u"address"]			= newMAC
					self.RPI[thisPi][u"piMAC"]		= newMAC
					if beacon in self.beacons:
						self.beacons[beacon][u"indigoId"]= 0
					beacon = newMAC
			if new:
				for piU in self.RPI: 
					if self.RPI[piU][u"piMAC"] == newMAC:
						self.indiLOG.log(20,u"adding new RPI another RPI(#{}) has already that this MAC number:{}".format(piU, newMAC ))
						valuesDict, errorDict  = self.setErrorCode(valuesDict,errorDict,  u"bad beacon#, already exist as RPI")
						return ( False, valuesDict, errorDict )
				self.indiLOG.log(20,u"setting up new RPI device for pi#{} mac#  {}".format(thisPi, newMAC) )
				for ll in _GlobalConst_emptyrPiProps:
					if ll not in valuesDict: valuesDict[ll]= _GlobalConst_emptyrPiProps[ll]

			self.RPI[thisPi][u"piDevId"] 			= dev.id
			valuesDict[u"address"]					= newMAC
			self.RPI[thisPi][u"piMAC"]				= newMAC
			beacon 									= newMAC


			self.RPI[thisPi][u"ipNumberPi"] 		= valuesDict[u"newIPNumber"]
			self.RPI[thisPi][u"ipNumberPiSendTo"] 	= valuesDict[u"newIPNumber"]
			self.RPI[thisPi][u"userIdPi"] 			= valuesDict[u"newuserIdPi"]
			self.RPI[thisPi][u"passwordPi"]			= valuesDict[u"newpasswordPi"]
			valuesDict[u"passwordPi"] 				= valuesDict[u"newpasswordPi"]
			valuesDict[u"userIdPi"] 				= valuesDict[u"newuserIdPi"]
			valuesDict[u"description"] 				= u"Pi-{}-{}".format(thisPi, valuesDict[u"newIPNumber"])


			if beacon in self.beacons and beacon.find(u"00:00:00:00") ==-1:
				self.beacons[beacon][u"expirationTime"] 			= float(valuesDict[u"expirationTime"])
				self.beacons[beacon][u"updateSignalValuesSeconds"]	= float(valuesDict[u"updateSignalValuesSeconds"])
				self.beacons[beacon][u"beaconTxPower"] 				= int(valuesDict[u"beaconTxPower"])
				self.beacons[beacon][u"ignore"] 					= int(valuesDict[u"ignore"])
				self.addToStatesUpdateDict(dev.id,u"TxPowerSet", int(valuesDict[u"beaconTxPower"]))

			self.RPI[thisPi][u"sendToIndigoSecs"] 					= valuesDict[u"sendToIndigoSecs"]	
			self.RPI[thisPi][u"sensorRefreshSecs"] 					= valuesDict[u"sensorRefreshSecs"]
			self.RPI[thisPi][u"deltaChangedSensor"] 				= valuesDict[u"deltaChangedSensor"]
			try:	 self.RPI[thisPi][u"rssiOffset"]				= float(valuesDict[u"rssiOffset"])
			except:	 self.RPI[thisPi][u"rssiOffset"]				= 0.
			self.RPI[thisPi][u"BLEserial"] 							= valuesDict[u"BLEserial"]
			self.setONErPiV(thisPi,"piUpToDate", [u"updateParamsFTP"])
			self.rPiRestartCommand[int(thisPi)] 					= u"master"
			self.RPI[thisPi][u"authKeyOrPassword"]					= valuesDict[u"newauthKeyOrPassword"]  
			self.RPI[thisPi][u"enableRebootCheck"]					= valuesDict[u"newenableRebootCheck"]  
			self.RPI[piU][u"piOnOff"] 								= u"1"

			xyz = valuesDict[u"PosXYZ"]
			try:
				xyz = xyz.split(u",")
				if len(xyz) == 3:
					self.RPI[thisPi][u"PosX"] = float(xyz[0]) * self.distanceUnits
					self.RPI[thisPi][u"PosY"] = float(xyz[1]) * self.distanceUnits
					self.RPI[thisPi][u"PosZ"] = float(xyz[2]) * self.distanceUnits
			except Exception, e:
				self.indiLOG.log(40,u"Line {} has error={}".format(sys.exc_traceback.tb_lineno, e))
				self.indiLOG.log(40,u"bad input for xyz-coordinates:{}".format(valuesDict[u"PosXYZ"]) )

			memberList = ""
			for nn in range(len(_GlobalConst_groupList)):
				group = _GlobalConst_groupList[nn]
				groupNameUsedForVar = self.groupListUsedNames[group]
				GN = u"memberOf"+group
				if GN in valuesDict:
					if len(groupNameUsedForVar) == 0: 
						valuesDict[GN] = False
					if unicode(valuesDict[GN]).lower() == u"true":
						memberList += groupNameUsedForVar+u"/"
					else:
						if unicode(dev.id) in self.groupStatusList[group][u"members"]:
							del self.groupStatusList[group][u"members"][unicode(dev.id)]
				else:
						if unicode(dev.id) in self.groupStatusList[group][u"members"]:
							del self.groupStatusList[group][u"members"][unicode(dev.id)]


			memberList = memberList.strip(u"/")
			if dev.states[u"groupMember"] != memberList:
				self.addToStatesUpdateDict(dev.id,u"groupMember", memberList)
				self.updateNeeded += u" fixConfig "



			self.executeUpdateStatesDict(calledFrom=u"validateDeviceConfigUi RPI")
			self.updateNeeded += u" fixConfig "
			self.saveConfig(only = u"RPIconf")

			return (True, valuesDict, errorDict)
		except Exception, e:
			self.indiLOG.log(40,u"setting up RPI Line {} has error={}".format(sys.exc_traceback.tb_lineno, e))
			valuesDict, errorDict  = self.setErrorCode(valuesDict,errorDict,  u"pgm error, check log")
			return ( False, valuesDict, errorDict )




############ beacons  -------
	def validateDeviceConfigUi_beacon(self, valuesDict, errorDict, typeId, thisPi, piU, props, beacon, dev):
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
					self.indiLOG.log(20,u"replacing beacon mac "+beacon+u" with "+newMAC)
					if beacon !="xx" and beacon in self.beacons:
						self.indiLOG.log(20,u"replacing existing beacon")
						self.beacons[newMAC]	= copy.deepcopy(self.beacons[beacon])
						self.beacons[beacon][u"indigoId"] = 0
						self.newADDRESS[dev.id]	= newMAC
						valuesDict[u"address"] = self.newADDRESS[dev.id]
						self.deviceStopCommIgnore = time.time()
					else:
						self.indiLOG.log(20,u"creating a new beacon")
						self.beacons[newMAC]	= copy.deepcopy(_GlobalConst_emptyBeacon)
						self.newADDRESS[dev.id]	= newMAC
						valuesDict[u"address"]		= newMAC
						self.deviceStopCommIgnore = time.time()
					beacon = newMAC
				elif new:
					self.indiLOG.log(20,u"creating a new beacon")
					self.beacons[newMAC]	= copy.deepcopy(_GlobalConst_emptyBeacon)
					self.newADDRESS[dev.id]	= newMAC
					valuesDict[u"address"]		= newMAC
					self.deviceStopCommIgnore = time.time()
					beacon = newMAC
			else:
				valuesDict[u"newMACNumber"] = beacon
				valuesDict, errorDict  = self.setErrorCode(valuesDict,errorDict,  "bad Mac Number")
				return ( False, valuesDict, errorDict )
			self.beaconPositionsUpdated = 1

			if not self.isValidMAC(beacon):
				error = u"bad Mac Number"
				valuesDict, errorDict  = self.setErrorCode(valuesDict,errorDict,  "bad Mac Number")
				return ( False, valuesDict, errorDict )
			self.beaconPositionsUpdated = 1

			if beacon in self.beacons and beacon.find(u"00:00:00:00") ==-1:
				self.beacons[beacon][u"expirationTime"] = float(valuesDict[u"expirationTime"])
				self.beacons[beacon][u"updateSignalValuesSeconds"] = float(valuesDict[u"updateSignalValuesSeconds"])
				try: 	self.beacons[beacon][u"beaconTxPower"] = int(valuesDict[u"beaconTxPower"])
				except:	self.beacons[beacon][u"beaconTxPower"] = 999
				self.addToStatesUpdateDict(dev.id,u"TxPowerSet", int(valuesDict[u"beaconTxPower"]))
				try:	self.beacons[beacon][u"ignore"] = int(valuesDict[u"ignore"])
				except:	self.beacons[beacon][u"ignore"] = 0

				self.beacons[beacon][u"note"] = u"beacon-" + valuesDict[u"typeOfBeacon"]
				self.addToStatesUpdateDict(dev.id,u"note", self.beacons[beacon][u"note"])


				self.beacons[beacon][u"showBeaconOnMap"]		 = valuesDict[u"showBeaconOnMap"]
				self.beacons[beacon][u"typeOfBeacon"]			 = valuesDict[u"typeOfBeacon"]
				memberList =""
				for nn in range(len(_GlobalConst_groupList)):
					group = _GlobalConst_groupList[nn]
					groupNameUsedForVar = self.groupListUsedNames[group]
					GN = u"memberOf"+group
					if GN in valuesDict:
						if len(groupNameUsedForVar) == 0: 
							valuesDict[GN] = False

						if unicode(valuesDict[GN]).lower() == u"true":
							memberList += groupNameUsedForVar+u"/"
						else:
							if unicode(dev.id) in self.groupStatusList[group][u"members"]:
								del self.groupStatusList[group][u"members"][unicode(dev.id)]
					else:
							if unicode(dev.id) in self.groupStatusList[group][u"members"]:
								del self.groupStatusList[group][u"members"][unicode(dev.id)]
				memberList = memberList.strip(u"/")
				if dev.states[u"groupMember"] != memberList:
					self.addToStatesUpdateDict(dev.id,u"groupMember", memberList)
					self.updateNeeded += u" fixConfig "

				self.setALLrPiV(u"piUpToDate", [u"updateParamsFTP"])

			if u"batteryLevelUUID" in valuesDict and valuesDict[u"batteryLevelUUID"] in [u"msg",u"gatttool"]:
				valuesDict[u"SupportsBatteryLevel"]  = True
			else:
				valuesDict[u"SupportsBatteryLevel"]  = False


			return ( True, valuesDict, errorDict )
		except Exception, e:
			self.indiLOG.log(40,u"setting up iBeacon Line {} has error={}".format(sys.exc_traceback.tb_lineno, e))
			valuesDict, errorDict  = self.setErrorCode(valuesDict,errorDict,  u"pgm error, check log")
			return ( False, valuesDict, errorDict )




############ sensors  -------
	def validateDeviceConfigUi_sensors(self, valuesDict, errorDict, typeId, thisPi, piU, props, beacon, dev):
		try:
			errorText = ""
			update = 0
			piUx = -1
			try: 	piUx = valuesDict[u"piServerNumber"]
			except: pass
			pix = int(piUx)
			valuesDict[u"address"] = u"PI-" 
			onPi = u"on Pi: "
			for pi in range(len(self.RPI)):
				piU = str(pi)
				if ( pi == pix or pix == 999 or (pi >= _GlobalConst_numberOfiBeaconRPI and pix == 800) or (u"rPiEnable"+piU in valuesDict and valuesDict[u"rPiEnable"+piU])) and self.RPI[piU][u"piDevId"] >0:
					self.updateNeeded += u" fixConfig "
					self.rPiRestartCommand[pi] += u"master,"
					self.rPiRestartCommand[int(piU)] += u"master,"
					self.setONErPiV(piU,u"piUpToDate",[u"updateParamsFTP"])

					if typeId not in self.RPI[piU][u"input"]:
						self.RPI[piU][u"input"][typeId]={}
					if unicode(dev.id) not in self.RPI[piU][u"input"][typeId]:
						self.RPI[piU][u"input"][typeId][unicode(dev.id)] = ""
					valuesDict[u"address"] =  u"PI-"+piU
					onPi += piU+ u","
					valuesDict[u"description"] = onPi.strip(u",")

				else:
					### remove if not on this pi:
					if piU in self.RPI and u"input" in self.RPI[piU]:
						if typeId in self.RPI[piU][u"input"] and unicode(dev.id) in self.RPI[piU][u"input"][typeId]:
							del self.RPI[piU][u"input"][typeId][unicode(dev.id)]
						if typeId in self.RPI[piU][u"input"] and self.RPI[piU][u"input"][typeId] == {}:
							del self.RPI[piU][u"input"][typeId]
						if typeId not in self.RPI[piU][u"input"] and typeId in self.RPI[piU][u"sensorList"]:
							self.RPI[piU][u"sensorList"] = self.RPI[piU][u"sensorList"].replace(typeId+u",","")
					continue

				if typeId == u"BLEmyBLUEt":
					valuesDict[u"description"] = u"myBLUEt" +u"-"+ valuesDict[u"mac"]

				if  typeId in _BLEsensorTypes:
					valuesDict[u"address"] =  valuesDict[u"mac"]

				if  typeId == u"launchpgm":
					valuesDict[u"description"] =  "pgm: "+valuesDict[u"launchCommand"]


				if	typeId	in [u"mhzCO2"]:
					self.addToStatesUpdateDict(dev.id,u"CO2calibration", valuesDict[u"CO2normal"] )

				if	typeId	=="rainSensorRG11":
						valuesDict[u"description"] = u"INP:"+valuesDict[u"gpioIn"]+u"-SW5:"+valuesDict[u"gpioSW5"]+u"-SW2:"+valuesDict[u"gpioSW2"]+u"-SW1:"+valuesDict[u"gpioSW1"]+u"-SW12V:"+valuesDict[u"gpioSWP"]


				if	typeId == u"pmairquality":
					if valuesDict[u"resetPin"] != u"-1" and valuesDict[u"resetPin"] != "":
						valuesDict[u"description"] = u"reset-GPIO: " +valuesDict[u"resetPin"]
					else:
						valuesDict[u"description"] = u"reset-GPIO not used"

				if	typeId == u"lidar360":
						valuesDict[u"description"] = u"MotorFrq: {}Hz; {}º in 1 bin; {}; MinSignal: {}".format( int(10*float(valuesDict[u"motorFrequency"])), valuesDict[u"anglesInOneBin"], valuesDict[u"usbPort"],  valuesDict[u"minSignalStrength"]) 


				if	typeId == u"Wire18B20" : # update serial number in states in case we jumped around with dev types. 
					if len(dev.states[u"serialNumber"]) < 5  and dev.description.find(u"sN= 28")>-1:
						self.addToStatesUpdateDict(dev.id,u"serialNumber", dev.description.split(u"sN= u")[1] )

				if	typeId.find(u"DHT") >-1:
					if u"gpioPin" in valuesDict:
						valuesDict[u"description"] = u"GPIO-PIN: " +valuesDict[u"gpioPin"]+u"; type: "+valuesDict[u"dhtType"]

				if (u"i2c" in typeId.lower() or typeId in _GlobalConst_i2cSensors) or u"interfaceType" in valuesDict:  
					if u"interfaceType" in valuesDict and valuesDict[u"interfaceType"] == u"i2c":
						if u"i2cAddress" in valuesDict:
							try:
								addrhex = u"=#"+hex(int(valuesDict[u"i2cAddress"]))
							except:
								addrhex =""
							if u"useMuxChannel" in valuesDict and valuesDict[u"useMuxChannel"] != u"-1":
									valuesDict[u"description"] = u"i2c: " +valuesDict[u"i2cAddress"]+addrhex +u"; mux-channel: "+valuesDict[u"useMuxChannel"]
							else:
									valuesDict[u"description"] = u"i2c: " +valuesDict[u"i2cAddress"]+addrhex
				
					elif u"interfaceType" in valuesDict and valuesDict[u"interfaceType"] == u"serial":
						valuesDict[u"description"] = u"serial port vers."

					else:
						if u"i2cAddress" in valuesDict:
							try:
								addrhex = u"=#"+hex(int(valuesDict[u"i2cAddress"]))
							except:
								addrhex =""
							if u"useMuxChannel" in valuesDict and valuesDict[u"useMuxChannel"] !="-1":
									valuesDict[u"description"] = u"i2c: " +valuesDict[u"i2cAddress"]+addrhex +u"; mux-channel: "+valuesDict[u"useMuxChannel"]
							else:
									valuesDict[u"description"] = u"i2c: " +valuesDict[u"i2cAddress"]+addrhex

				if typeId.find(u"bme680") >-1:
					if   valuesDict[u"calibrateSetting"] == u"setFixedValue": valuesDict[u"description"] += u", set calib to "+ valuesDict[u"setCalibrationFixedValue"]
					elif valuesDict[u"calibrateSetting"] == u"readFromFile":	valuesDict[u"description"] += u", set calib to read from file"
					else:											        valuesDict[u"description"] += u", recalib if > "+valuesDict[u"recalibrateIfGT"]+u"%"
				if typeId.find(u"moistureSensor") >-1:
					valuesDict[u"description"] +=  ";"+valuesDict[u"minMoisture"]+u"<V<"+ valuesDict[u"maxMoisture"]


				if typeId in [u"PCF8591",u"ADS1x15"]:
					if u"displayS" 	in valuesDict:  			 		valuesDict[u"displayS"] 	= u"INPUT"
					if u"input" 		in valuesDict:  			 	valuesDict[u"description"]	+= u" C#="+valuesDict[u"input"]+u";"
					if u"resModel" 	in valuesDict:  			 		valuesDict[u"description"] 	+= u"M="+valuesDict[u"resModel"]+u";"
					if u"gain" 		in valuesDict:  			 		valuesDict[u"description"] 	+= u"G="+valuesDict[u"gain"]+u";"
					try: 
						o = float(valuesDict[u"offset"])
						if o != 0.:
							if o > 0: 	 								valuesDict[u"description"] 	+= u"+"+valuesDict[u"offset"]+u";"
							else:									 	valuesDict[u"description"] 	+=     valuesDict[u"offset"]+u";"
					except: pass
					try: 
						m = float(valuesDict[u"mult"])
						if m != 1.: 	 								valuesDict[u"description"] 	+= u"*"+valuesDict[u"mult"]+u";"
					except: pass
					if valuesDict[u"resistorSensor"]	== u"ground":	valuesDict[u"description"] 	+= u"RG="+valuesDict[u"feedResistor"]+u";V="+valuesDict[u"feedVolt"]+u";"
					if valuesDict[u"resistorSensor"]	== u"V+": 		valuesDict[u"description"] 	+= u"R+="+valuesDict[u"feedResistor"]+u";V="+valuesDict[u"feedVolt"]+u";"
					if valuesDict[u"maxMin"] 			== u"1":		valuesDict[u"description"] 	+= ""+valuesDict[u"MINRange"]+u";<V<"+valuesDict[u"MAXRange"]+u";"
					if valuesDict[u"valueOrdivValue"]	== u"1/value":	valuesDict[u"description"] 	+= u"1/v;"
					if valuesDict[u"logScale"] 			== u"1":  	 	valuesDict[u"description"] 	+= u"LOG"+u";"
					try: 
						o = float(valuesDict[u"offset2"])
						if o != 0.:
							if o > 0: 	 								valuesDict[u"description"] 	+= u"+"+valuesDict[u"offset2"]+u";"
							else:										valuesDict[u"description"] 	+=     valuesDict[u"offset2"]+u";"
					except: pass
					try: 
						m = float(valuesDict[u"mult"])
						if m != 1.:										valuesDict[u"description"] 	+= u"*"+valuesDict[u"mult"]+u";"
					except: pass
					if valuesDict[u"format"] 			!= "":  		valuesDict[u"description"] 	+= u"F="+valuesDict[u"format"]+u";"
					if valuesDict[u"unit"] 				!= "":   		valuesDict[u"description"] 	+= u"U="+valuesDict[u"unit"]+u";"
					valuesDict[u"description"] = valuesDict[u"description"].strip(u";")

				if u"ultrasoundDistance" == typeId :
					self.rPiRestartCommand[pi] += u"ultrasoundDistance,"
					if u"gpioTrigger" not in props or (props[u"gpioTrigger"] != valuesDict[u"gpioTrigger"]): 
						self.rPiRestartCommand[pi] += u"ultrasoundDistance,"
					if u"gpioEcho" not in props or(props[u"gpioEcho"] != valuesDict[u"gpioEcho"]): 
						self.rPiRestartCommand[pi] += u"ultrasoundDistance,"
					if u"sensorRefreshSecs" not in props or (props[u"sensorRefreshSecs"] != valuesDict[u"sensorRefreshSecs"]): 
						self.rPiRestartCommand[pi] += u"ultrasoundDistance,"
					if u"deltaDist" not in props or (props[u"deltaDist"] != valuesDict[u"deltaDist"]): 
						self.rPiRestartCommand[pi] += u"ultrasoundDistance,"
					valuesDict[u"description"] = u"trigger-pin: " +valuesDict[u"gpioTrigger"] +u"; echo-pin: " +valuesDict[u"gpioEcho"]+u"; refresh:"+valuesDict[u"sensorRefreshSecs"]+u"; unit:"+valuesDict[u"dUnits"]
					valuesDict, errorText = self.addBracketsPOS(valuesDict,u"pos1")
					if errorText == "":
						valuesDict, errorText = self.addBracketsPOS(valuesDict,u"pos2")
						if errorText == "":
							valuesDict, errorText = self.addBracketsPOS(valuesDict,u"pos3")

				if u"vl503l0xDistance" == typeId :
					self.rPiRestartCommand[pi] += u"vl503l0xDistance,"
					if u"sensorRefreshSecs" not in props or (props[u"sensorRefreshSecs"] != valuesDict[u"sensorRefreshSecs"]): 
						self.rPiRestartCommand[pi] += u"vl503l0xDistance,"
					if u"sensorRefreshSecs" not in props or (props[u"sensorRefreshSecs"] != valuesDict[u"sensorRefreshSecs"]): 
						self.rPiRestartCommand[pi] += u"ultrasoundDistance,"
					if u"deltaDist" not in props or (props[u"deltaDist"] != valuesDict[u"deltaDist"]): 
						self.rPiRestartCommand[pi] += u"vl503l0xDistance,"

				if u"vl6180xDistance" == typeId :
					if typeId not in self.RPI[piU][u"input"]:
						self.RPI[piU][u"input"][typeId] = {}
						self.rPiRestartCommand[pi] += u"vl6180xDistance,"
					if u"sensorRefreshSecs" not in props or (props[u"sensorRefreshSecs"] != valuesDict[u"sensorRefreshSecs"]): 
						self.rPiRestartCommand[pi] += u"vl6180xDistance,"
					if u"deltaDist" not in props or (props[u"deltaDist"] != valuesDict[u"deltaDist"]): 
						self.rPiRestartCommand[pi] += u"vl6180xDistance,"

				elif u"vcnl4010Distance" == typeId :
					self.rPiRestartCommand[pi] += u"vcnl4010Distance,"
					if u"sensorRefreshSecs" not in props or (props[u"sensorRefreshSecs"] != valuesDict[u"sensorRefreshSecs"]): 
						self.rPiRestartCommand[pi] += u"vcnl4010Distance,"
					if u"deltaDist" not in props or (props[u"deltaDist"] != valuesDict[u"deltaDist"]): 
						self.rPiRestartCommand[pi] += u"vcnl4010Distance,"

				if u"INPUTpulse" == typeId :
					pinMappings = u"gpio="+valuesDict[u"gpio"]+ u"," +valuesDict[u"risingOrFalling"]+ u" Edge, " +valuesDict[u"deadTime"]+ u"secs deadTime"
					valuesDict[u"description"] = pinMappings


				if u"INPUTcoincidence" == typeId :
					theText = u"coincidenceWindow = {} msecs".format(valuesDict[u"coincidenceTimeInterval"])
					valuesDict[u"description"] = theText

				self.setONErPiV(piU,u"piUpToDate", [u"updateParamsFTP"])
				valuesDict[u"MSG"] = errorText

			if errorText == "":
				self.updateNeeded += u" fixConfig "
				self.setONErPiV(piU,u"piUpToDate", [u"updateParamsFTP"])
				self.updateNeeded += u" fixConfig "
				return (True, valuesDict, errorDict )
			else:
				self.indiLOG.log(40,u"validating device error:{}     fields:{}".format(errorText, valuesDict))
				valuesDict, errorDict  = self.setErrorCode(valuesDict, errorDict,  errorText)
				return ( False, valuesDict, errorDict )
		except Exception, e:
			self.indiLOG.log(40,u"setting up iBeacon Line {} has error={}".format(sys.exc_traceback.tb_lineno, e))
			valuesDict, errorDict  = self.setErrorCode(valuesDict,errorDict,  u"pgm error, check log")
			return ( False, valuesDict, errorDict )



############ INPUTG  -------
	def validateDeviceConfigUi_INPUTG(self, valuesDict, errorDict, typeId, thisPi, piU, props, beacon, dev):
		try:
			if typeId.find(u"INPUTgpio")>-1:	typeINPUT = u"INPUTgpio"
			if typeId.find(u"INPUTtouch")>-1:	typeINPUT = u"INPUTtouch"

			active = ""
			update = 0

			piU = valuesDict[u"piServerNumber"]
			pi  = int(piU)
			for piU0 in self.RPI:
				if piU == piU0:											  continue
				if u"input" not in self.RPI[piU0]:						  continue
				if typeId not in self.RPI[piU0][u"input"]:				  continue
				if unicode(dev.id) not in self.RPI[piU0][u"input"][typeId]:continue
				del self.RPI[piU0][u"input"][typeId][unicode(dev.id)]
				self.setONErPiV(piU0,"piUpToDate",[u"updateParamsFTP"])
				self.rPiRestartCommand[int(piU0)] += typeINPUT+u","
				update = 1

			if pi >= 0:
				if u"piServerNumber" in props:
					if pi != int(props[u"piServerNumber"]):
						self.setONErPiV(piU,u"piUpToDate",[u"updateParamsFTP"])
						self.rPiRestartCommand[int(props[u"piServerNumber"])] += typeINPUT+u","
						update = 1
				self.setONErPiV(piU,u"piUpToDate", [u"updateParamsFTP"])
				self.rPiRestartCommand[pi] += typeINPUT+u","

			if typeId not in self.RPI[piU][u"input"]:
					self.RPI[piU][u"input"][typeId] = {}
					update = 1
			if unicode(dev.id) not in self.RPI[piU][u"input"][typeId]:
				self.RPI[piU][u"input"][typeId][unicode(dev.id)] = []
				update = 1
			newDeviceDefs = json.loads(valuesDict[u"deviceDefs"])

			try:
				if len(newDeviceDefs) != len(self.RPI[piU][u"input"][typeId][unicode(dev.id)]):
					update = 1
				for n in range(len(newDeviceDefs)):
					if update == 1: break
					for item in newDeviceDefs[n]:
						if newDeviceDefs[n][item] != self.RPI[piU][u"input"][typeId][unicode(dev.id)][n][item]:
							update = 1
							break
			except:
				update = 1

			self.RPI[piU][u"input"][typeId][unicode(dev.id)] = newDeviceDefs

			if typeINPUT == u"INPUTgpio":
				pinMappings = u"(#,gpio,inpType,Count)"
			if typeINPUT == u"INPUTtouch":
				pinMappings = u"(#,Chan.,Count)"


			for n in range(len(newDeviceDefs)):
				if u"gpio" in newDeviceDefs[n]:
					if newDeviceDefs[n][u"gpio"]=="": continue
					if typeINPUT == u"INPUTgpio":
						pinMappings += u"(u" + unicode(n) + ":" + newDeviceDefs[n][u"gpio"]+ "," + newDeviceDefs[n][u"inpType"] + "," + newDeviceDefs[n][u"count"] + ");"
					if typeINPUT == u"INPUTtouch":
						pinMappings += u"(u" + unicode(n) + ":" + newDeviceDefs[n][u"gpio"]+ "," + newDeviceDefs[n][u"count"] + ");"
			valuesDict[u"description"] = pinMappings

			if update == 1:
				self.rPiRestartCommand[pi] += typeINPUT+u","
				self.updateNeeded += u" fixConfig "
				self.setONErPiV(piU,u"piUpToDate", [u"updateParamsFTP"])

			if valuesDict[u"count"]  == u"off":
				valuesDict[u"SupportsOnState"]		= True
				valuesDict[u"SupportsSensorValue"]	= False
			else:
				valuesDict[u"SupportsOnState"]		= False
				valuesDict[u"SupportsSensorValue"]	= True


			valuesDict[u"piDone"]		= False
			valuesDict[u"stateDone"]	= False
			self.indiLOG.log(20,u" piUpToDate pi: " +piU+ u"    value:"+ unicode(self.RPI[piU][u"piUpToDate"]))
			self.indiLOG.log(20,unicode(valuesDict) )
			self.updateNeeded += u" fixConfig "
			return (True, valuesDict, errorDict )
		except Exception, e:
			self.indiLOG.log(40,u"setting up INPUTRotatary Line {} has error={}".format(sys.exc_traceback.tb_lineno, e))
			valuesDict, errorDict  = self.setErrorCode(valuesDict,errorDict,  u"pgm error, check log")
			return ( False, valuesDict, errorDict )




############ INPUTRotatary  -------
	def validateDeviceConfigUi_INPUTRotatary(self, valuesDict, errorDict, typeId, thisPi, piU, props, beacon, dev):
		try:
			active = ""
			update = 0

			piU = valuesDict[u"piServerNumber"]
			pi  = int(piU)
			for piU0 in self.RPI:
				if piU == piU0:											  continue
				if u"input" not in self.RPI[piU0]:						  continue
				if typeId not in self.RPI[piU0][u"input"]:				  continue
				if unicode(dev.id) not in self.RPI[piU0][u"input"][typeId]:continue
				del self.RPI[piU0][u"input"][typeId][unicode(dev.id)]
				self.setONErPiV(piU0,"piUpToDate",[u"updateParamsFTP"])
				self.rPiRestartCommand[int(piU0)] += typeId+u","
				update = 1

			if pi >= 0:
				if u"piServerNumber" in props:
					if pi != int(props[u"piServerNumber"]):
						self.setONErPiV(piU,u"piUpToDate",[u"updateParamsFTP"])
						self.rPiRestartCommand[int(props[u"piServerNumber"])] += typeId+u","
						update = 1
				self.setONErPiV(piU,u"piUpToDate", [u"updateParamsFTP"])
				self.rPiRestartCommand[pi] += typeId+u","

			pinMappings = u"GPIOs:"
			for jj in range(10):
				if u"INPUT_"+unicode(jj) in valuesDict:
					pinMappings+= valuesDict[u"INPUT_"+unicode(jj)]+u", "
			valuesDict[u"description"] = pinMappings.strip(u", ")
			self.updateNeeded += u" fixConfig "
			return ( True, valuesDict, errorDict )

		except Exception, e:
			self.indiLOG.log(40,u"setting up INPUTRotatary Line {} has error={}".format(sys.exc_traceback.tb_lineno, e))
			valuesDict, errorDict  = self.setErrorCode(valuesDict,errorDict,  "pgm error, check log")
			return ( False, valuesDict, errorDict )



############ OUTPUTG  -------
	def validateDeviceConfigUi_OUTPUTG(self, valuesDict, errorDict, typeId, thisPi, piU, props, beacon, dev):
		try:
			#self.indiLOG.log(20,u"into validate relay")
			update = 0
			active = ""
			piU = (valuesDict[u"piServerNumber"])
			for piU0 in self.RPI:
				if piU == piU0:												continue
				if u"output" not in self.RPI[piU0]:							continue
				if typeId not in self.RPI[piU0][u"output"]:					continue
				if unicode(dev.id) not in self.RPI[piU0][u"output"][typeId]: continue
				del self.RPI[piU0][u"output"][typeId][unicode(dev.id)]
				self.setONErPiV(piU0,"piUpToDate",[u"updateParamsFTP"])

			if piU >= 0:
				if u"piServerNumber" in props:
					if piU != props[u"piServerNumber"]:
						self.setONErPiV(piU,u"piUpToDate", [u"updateParamsFTP"])
						update=1



			if typeId not in self.RPI[piU][u"output"]:
				self.RPI[piU][u"output"][typeId] = {}
				update = 1
			if unicode(dev.id) not in self.RPI[piU][u"output"][typeId]:
				self.RPI[piU][u"output"][typeId][unicode(dev.id)] = []
				update = 1
			new = json.loads(valuesDict[u"deviceDefs"])
			self.indiLOG.log(20,u"deviceDefs:{}".format(valuesDict[u"deviceDefs"]))

			try:
				if len(new) != len(self.RPI[piU][u"output"][typeId][unicode(dev.id)]):
					update = 1
				for n in range(len(new)):
					if update == 1: break
					for item in new[n]:
						if new[n] != self.RPI[piU][u"output"][typeId][unicode(dev.id)][n][item]:
							update = 1
							break
			except:
				update = 1

			self.RPI[piU][u"output"][typeId][unicode(dev.id)] = new

			if typeId.find(u"OUTPUTi2cRelay") ==-1: pinMappings = u"(#,gpio,type,init)"
			else:									pinMappings = u"(ch#,type,init)"
			for n in range(len(new)):
				if u"gpio" in new[n]:
					pinMappings += u"(" + unicode(n) + ":" + new[n][u"gpio"]+u"," + new[n][u"outType"] +u"," +  new[n][u"initialValue"]  +u");"
				else:
					pinMappings += u"(" + unicode(n) + ":-);"
				if u"inverse" in dev.states:
					if (dev.states[u"inverse"]) != (new[n][u"outType"]== u"1"): 				self.addToStatesUpdateDict(dev.id,u"inverse", new[n][u"outType"]==u"1" )
				elif u"inverse_{:2d}".format(n) in dev.states:
					if (dev.states[u"inverse_{:2d}".format(n)]) != (new[n][u"outType"]== u"1"): self.addToStatesUpdateDict(dev.id,u"inverse_{:2d}".format(n), new[n][u"outType"]==u"1")
				if u"initial" in dev.states:
					if dev.states[u"initial"] != new[n][u"initialValue"]: 					 	self.addToStatesUpdateDict(dev.id,u"initial", new[n][u"initialValue"] )
				elif u"initial{:2d}".format(n) in dev.states:
					if dev.states[u"initial{:2d}".format(n)] != new[n][u"initialValue"]: 	 	self.addToStatesUpdateDict(dev.id,u"initial{:2d}".format(n), new[n][u"initialValue"] )
				
			valuesDict[u"description"] = pinMappings

			if update == 1:
				self.rPiRestartCommand[int(piU)] += typeId+u","
				self.updateNeeded += u" fixConfig "
				self.setONErPiV(piU,u"piUpToDate", [u"updateParamsFTP"])

			valuesDict[u"piDone"] = False
			valuesDict[u"stateDone"] = False
			return (True, valuesDict, errorDict)
			self.updateNeeded += u" fixConfig "

		except Exception, e:
			self.indiLOG.log(40,u"setting up OUTPUT-G Line {} has error={}".format(sys.exc_traceback.tb_lineno, e))
			try:
				valuesDict, errorDict  = self.setErrorCode(valuesDict, errorDict,  u"pgm error, check log")
			except Exception, e:
				self.indiLOG.log(40,u"setting up OUTPUT-G Line {} has error={}".format(sys.exc_traceback.tb_lineno, e))
			return ( False, valuesDict, errorDict )




	def validateDeviceConfigUi_output(self, valuesDict, errorDict, typeId, thisPi, piU, props, beacon, dev):
		try:
			error = ""
			if typeId== u"neopixel-dimmer":
				neopixelDevice = indigo.devices[int(valuesDict[u"neopixelDevice"])]
				propsX = neopixelDevice.pluginProps
				piU = propsX[u"piServerNumber"]
				pi = int(piU)
				self.rPiRestartCommand[pi] += u"neopixel,"
				self.setONErPiV(piU,u"piUpToDate", [u"updateParamsFTP"]) 
				valuesDict[u"address"] = neopixelDevice.name
				try: 
					xxx= propsX[u"devType"].split(u"x")
					ymax = int(xxx[0])
					xmax = int(xxx[1])
				except:
					valuesDict, errorDict  = self.setErrorCode(valuesDict,errorDict,  "devtype not defined for neopixel" )
					return ( False, valuesDict, errorDict )

				pixels=u"; pix="
				if valuesDict[u"pixelMenulist"] !="": pixels +=valuesDict[u"pixelMenulist"]
				else:
					for ii in range(20):
						if u"pixelMenu"+unicode(ii) in valuesDict and valuesDict[u"pixelMenu"+unicode(ii)] !="":
							pixel =valuesDict[u"pixelMenu"+unicode(ii)]
							if u"," not in pixel: 
								# try just one dim.
								valuesDict[u"pixelMenu"+unicode(ii)]= u"0,"+pixel

							pixel =valuesDict[u"pixelMenu"+unicode(ii)]
							xxx = pixel.split(u",")
							x = xxx[1]
							y = xxx[0]
							if	int(x) >= xmax : x = unicode(max(0,xmax-1))
							if	int(y) >= ymax : y = unicode(max(0,ymax-1))
							pixels +=y+u","+x+u" "
							valuesDict[u"pixelMenu"+unicode(ii)] = y+u","+x
					pixels =pixels.strip(u" ")
				valuesDict[u"description"]	= u"rampSp="+ valuesDict[u"speedOfChange"]+u"[sec]"+ pixels

			elif typeId==u"neopixel":
				try:
					piU = valuesDict[u"piServerNumber"]
					pi = int(piU)
					self.rPiRestartCommand[pi] += u"neopixel,"
					valuesDict[u"address"]		 = u"Pi-"+valuesDict[u"piServerNumber"]
					valuesDict[u"devType"]		 = valuesDict[u"devTypeROWs"] +u"x"+valuesDict[u"devTypeLEDs"]
					valuesDict[u"description"]	 = u"type="+valuesDict[u"devType"]
					self.setONErPiV(piU,u"piUpToDate", [u"updateParamsFTP"]) 
				except:
					pass
			elif typeId==u"sundial":
				try:
					piU = valuesDict[u"piServerNumber"]
					pi = int(piU)
					self.rPiRestartCommand[pi] += u"sundial,"
					valuesDict[u"address"]		 = u"Pi-"+valuesDict[u"piServerNumber"]
					valuesDict[u"description"]	 = u"TZ="+valuesDict[u"timeZone"]+u"; motorType"+valuesDict[u"motorType"]
					self.setONErPiV(piU,u"piUpToDate", [u"updateParamsFTP"]) 
				except:
					pass
			elif typeId==u"setStepperMotor":
				try:
					piU = valuesDict[u"piServerNumber"]
					pi = int(piU)
					self.rPiRestartCommand[pi] += u"sundial,"
					valuesDict[u"address"]		 = u"Pi-"+valuesDict[u"piServerNumber"]
					valuesDict[u"description"]	 = u"motorTypes: "+valuesDict[u"motorType"]
					self.setONErPiV(piU,u"piUpToDate", [u"updateParamsFTP"]) 
				except:
					pass
			else:
				piU = valuesDict[u"piServerNumber"]
				pi = int(piU)
				valuesDict[u"address"] = u"PI-" + piU
				if pi >= 0:
					if u"piServerNumber" in props:
						if pi != int(props[u"piServerNumber"]):
							self.updateNeeded += u" fixConfig "
					cAddress = ""
					devType=""

					if u"devType" in valuesDict:
						devType = valuesDict[u"devType"]

					if u"output" not in			self.RPI[piU]:  
						self.RPI[piU][u"output"]={}
					if typeId not in			self.RPI[piU][u"output"]:  
						self.RPI[piU][u"output"][typeId]={}
					if unicode(dev.id) not in	self.RPI[piU][u"output"][typeId]:  
						self.RPI[piU][u"output"][typeId][unicode(dev.id)]={}

					if u"i2cAddress" in valuesDict:
						cAddress = valuesDict[u"i2cAddress"]
						self.RPI[piU][u"output"][typeId][unicode(dev.id)] = [{u"i2cAddress":cAddress},{u"devType":devType}]

					elif u"spiAddress" in valuesDict:
						cAddress = unicode(int(valuesDict[u"spiAddress"]))
						self.RPI[piU][u"output"][typeId][unicode(dev.id)] = [{u"spi":cAddress},{u"devType":devType}]

					self.updateNeeded += u" fixConfig "
					self.rPiRestartCommand[pi] += u"receiveGPIOcommands,"
					self.setONErPiV(piU,u"piUpToDate", [u"updateParamsFTP"])


					if typeId == u"display":
						valuesDict = self.fixDisplayProps(valuesDict,typeId,devType)

						self.rPiRestartCommand[pi] += u"display,"
						self.setONErPiV(piU,u"piUpToDate", [u"updateAllFilesFTP"]) # this will send images and fonts too
						valuesDict,error = self.addBracketsPOS(valuesDict,"pos1")
						if error == "":
							valuesDict,error = self.addBracketsPOS(valuesDict,u"pos2")
							if error == "":
								valuesDict,error = self.addBracketsPOS(valuesDict,u"pos3")

						if devType == u"screen":
							valuesDict[u"description"] = u"res: {}".format(valuesDict[u"displayResolution"])

					if typeId==u"OUTPUTxWindows":
						self.rPiRestartCommand[pi] += u"xWindows,"
						self.setONErPiV(piU,u"piUpToDate", [u"updateParamsFTP"]) # this will send images and fonts too
						valuesDict[u"description"]	 = u"GUI: "+valuesDict[u"xWindows"]


					if typeId == u"setTEA5767":
						self.setONErPiV(piU,u"piUpToDate", [u"updateParamsFTP"]) # this will send config only
						self.addToStatesUpdateDict(dev.id,u"status"   ,"f= u"+valuesDict[u"defFreq"] + u"; mute= u" +valuesDict[u"mute"])
						self.addToStatesUpdateDict(dev.id,u"frequency",valuesDict[u"defFreq"] )
						self.addToStatesUpdateDict(dev.id,u"mute"     ,valuesDict[u"mute"])
						self.devUpdateList[unicode(dev.id)] = True
			valuesDict[u"MSG"] = error
			if error == "":
				self.updateNeeded += u" fixConfig "
				return (True, valuesDict, errorDict)
			else:
				valuesDict, errorDict  = self.setErrorCode(valuesDict,errorDict,  error )
				return ( False, valuesDict, errorDict )

		except Exception, e:
			self.indiLOG.log(40,u"setting up OUTPUT Line {} has error={}".format(sys.exc_traceback.tb_lineno, e))
			valuesDict, errorDict  = self.setErrorCode(valuesDict,errorDict,  u"pgm error, check log")
		return ( False, valuesDict, errorDict )


####-------------------------------------------------------------------------####
	def setErrorCode(self,valuesDict, errorDict, error):
		try:
			valuesDict[u"MSG"] = error
			errorDict[u"MSG"]  = error
			self.indiLOG.log(40,u"validateDeviceConfigUi "+error)
		except Exception, e:
			self.indiLOG.log(40,u"Line {} has error={}".format(sys.exc_traceback.tb_lineno, e))
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
					self.indiLOG.log(40,u"Line {} has error={}".format(sys.exc_traceback.tb_lineno, e))
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
					valuesDict[u"scrollxy"]		= u"0"
					valuesDict[u"showDateTime"] = u"0"
		except Exception, e:
			if unicode(e).find(u"timeout waiting") > -1:
				self.indiLOG.log(40,u"Line {} has error={}".format(sys.exc_traceback.tb_lineno, e))
		return valuesDict


####-------------------------------------------------------------------------####
	def addBracketsPOS(self, valuesDict, pos):
		error = ""
		if pos in valuesDict:
			if valuesDict[pos].find(u"[") !=0:
				valuesDict[pos] =u"["+valuesDict[pos]
			if valuesDict[pos].find(u"]") != len(valuesDict[pos])-1:
				valuesDict[pos] =valuesDict[pos]+u"]"
			if len(valuesDict[pos]) > 2:
				if valuesDict[pos].find(u",") ==-1:
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
		devId= int(valuesDict[u"printDeviceDict"])
		dev=indigo.devices[devId]
		self.myLog( text = dev.name+u"/"+unicode(devId)+u" -------------------------------",mType="printing dev info for" )
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
	def buttonConfirmchangeLogfile(self, valuesDict=None, typeId="", devId=0):
		self.myLog( text = u"  starting to modify "+self.indigoPath + 'IndigoWebServer/indigopy/indigoconn.py')
		if not os.path.isfile(self.indigoPath + 'IndigoWebServer/indigopy/indigoconn.py'): return valuesDict
		f = open(self.indigoPath + 'IndigoWebServer/indigopy/indigoconn.py', u"r")
		g = open(self.indigoPath + 'IndigoWebServer/indigopy/indigoconn.py-1', u"w")
		lev = 0
		tab = u"	"
		for line in f.readlines():
			if lev == 0:
				if line.find('def ServerWriteLog(self, logMessage):') > -1:
					lev = 1
					g.write(line)
					if line[0] == tab:
						tab = u"	"
					else:
						tab = u"    "
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
			self.indiLOG.log(20,u"....modified version already inplace, do nothing")
			return valuesDict

		if os.path.isfile(self.indigoPath + 'IndigoWebServer/indigopy/indigoconn.py.original'):
			os.remove(self.indigoPath + 'IndigoWebServer/indigopy/indigoconn.py.original')
		os.rename(self.indigoPath + 'IndigoWebServer/indigopy/indigoconn.py',
				  self.indigoPath + 'IndigoWebServer/indigopy/indigoconn.py.original')
		os.rename(self.indigoPath + 'IndigoWebServer/indigopy/indigoconn.py-1',
				  self.indigoPath + 'IndigoWebServer/indigopy/indigoconn.py')
		self.indiLOG.log(20,u"/Library/Application Support/Perceptive Automation/Indigo x/IndigoWebServer/indigopy/indigoconn.py has been replace with modified version(logging suppressed)")
		self.indiLOG.log(20,u"  the original has been renamed to indigoconn.py.original, you will need to restart indigo server to activate new version")
		self.indiLOG.log(20,u"  to go back to the original version replace/rename the new version with the saved .../IndigoWebServer/indigopy/indigoconn.py.original file")

		return valuesDict

####-------------------------------------------------------------------------####
	def buttonConfirmReversechangeLogfile(self, valuesDict=None, typeId="", devId=0):

		if os.path.isfile(self.indigoPath + 'IndigoWebServer/indigopy/indigoconn.py.original'):
			os.remove(self.indigoPath + 'IndigoWebServer/indigopy/indigoconn.py')
			os.rename(self.indigoPath + 'IndigoWebServer/indigopy/indigoconn.py.original',
				  self.indigoPath + 'IndigoWebServer/indigopy/indigoconn.py')
			self.indiLOG.log(20,u"/Library/Application Support/Perceptive Automation/Indigo x/IndigoWebServer/indigopy/indigoconn.py.original has been restored")
			self.indiLOG.log(20,u" you will need to restart indigo server to activate new version")
		else:
			self.indiLOG.log(20,u"no file ... indigopy.py.original found to restore")

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
					if self.RPI[piU][u"piOnOff"] == u"1":
						if value =="" or value ==[] or value ==[""] or isinstance(self.RPI[piU][item], ( int, long ) ) or isinstance(self.RPI[piU][item],(str, unicode)):
							self.RPI[piU][item]=[]
						else:
							for v in value:
								if v not in self.RPI[piU][item]:
									self.RPI[piU][item].append(v)
			return
		except Exception, e:
			if unicode(e) != u"None":
				self.indiLOG.log(40,u"Line {} has error={}".format(sys.exc_traceback.tb_lineno, e))


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
				vv = v.split(u".exp")[0]
				if vv in self.RPI[piU][item]:
					self.RPI[piU][item].remove(vv)
		return


####-------------------------------------------------------------------------####
	def filterBeaconTags_and_all(self, filter="", valuesDict=None, typeId="", devId=""):
		xList=[]
		for dd in self.knownBeaconTags:
			if self.knownBeaconTags[dd][u"pos"] >= 0:
				xList.append((dd,self.knownBeaconTags[dd][u"text"]))
		xList = sorted(xList, key=lambda tup: tup[1])
		xList.append((u"all",u"USE ALL KNOWN"))
		xList.append((u"off",u"none = OFF"))
		return xList

####-------------------------------------------------------------------------####
	def filterBeaconTypes(self, filter="", valuesDict=None, typeId="", devId=""):
		xList=[]
		for dd in self.knownBeaconTags:
			xList.append((dd,self.knownBeaconTags[dd][u"text"]+u" txPower: "+self.knownBeaconTags[dd][u"dBm"]+u"dBm"))
		xList = sorted(xList, key=lambda tup: tup[1])
		return xList


####-------------------------------------------------------------------------####
	def filterBeaconsThatCanBeep(self, filter="", valuesDict=None, typeId="", devId=""):
		xList=[]
		for dev in indigo.devices.iter(u"props.isBeaconDevice"):
			props = dev.pluginProps
			#self.indiLOG.log(40,u"trying beacon: {} ".format(dev.name))
			if True or "beaconBeepUUID" in props or props[u"beaconBeepUUID"] == u"gatttool":
				if u"typeOfBeacon" in props:
					#self.indiLOG.log(40,u"trying beacon:  after 2: {}".format(props[u"typeOfBeacon"]))
					if props[u"typeOfBeacon"] != "":
						#self.indiLOG.log(40,u"trying beacon:  after 3: {}".format(self.knownBeaconTags[props[u"typeOfBeacon"]]))
						if props[u"typeOfBeacon"] in self.knownBeaconTags and self.knownBeaconTags[props[u"typeOfBeacon"]][u"beepCmd"] != u"off":
							#self.indiLOG.log(40,u"trying beacon:  after 4")
							xList.append( (unicode(dev.id), dev.name ) )
		return xList


####-------------------------------------------------------------------------####
	def filterAllpiSimple(self, filter="", valuesDict=None, typeId="", devId=""):
		xList=[]
		for piU in _rpiList:
			name = ""
			try:
				devId= int(self.RPI[piU][u"piDevId"])
				if devId >0:
					name= u"-"+indigo.devices[devId].name
			except: pass
			xList.append((piU,"#"+piU+u"-"+self.RPI[piU][u"ipNumberPi"]+name))
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
			 ,(u"image"		 , u"IaccelerationZE	not implemnted yet")
			 ,(u"matrix"	 , u"MATRIX enter only RGB values for EACH point ")
			 ,(u"thermometer", u"THERMOMETER enter start, end pixels and color delta")
			 ,(u"NOP"		 , u"No operation, use to wait before next action")
			 ,(u"exec"		 , u"execute , not implemened yet")]
		return xList


####-------------------------------------------------------------------------####
	def filterLightSensorOnRpi(self, filter="", valuesDict=None, typeId="", devId=""):
		xList=[]
		for dev in indigo.devices.iter(u"props.isSensorDevice"):
			if dev.deviceTypeId in _GlobalConst_lightSensors: 
				xList.append((unicode(dev.id)+u"-"+dev.deviceTypeId, dev.name))

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

		fonts=	   [[u"4x6.pil",u"4x6 for LED display"],
					[u"5x7.pil",u"5x7 for LED display"],
					[u"5x8.pil",u"5x8 for LED display"],
					[u"6x10.pil",u"6x10 for LED display"],
					[u"6x12.pil",u"6x12 for LED display"],
					[u"6x13.pil",u"6x13 for LED display"],
					[u"6x13B.pil",u"6x138 for LED display"],
					[u"6x13O.pil",u"6x130 for LED display"],
					[u"6x9.pil",u"6x9 for LED display"],
					[u"7x13.pil",u"7x13 for LED display"],
					[u"7x13B.pil",u"7x138 for LED display"],
					[u"7x13O.pil",u"7x130 for LED display"],
					[u"7x14.pil",u"7x14 for LED display"],
					[u"7x14B.pil",u"7x148 for LED display"],
					[u"8x13.pil",u"8x13 for LED display"],
					[u"8x13B.pil",u"8x138 for LED display"],
					[u"8x13O.pil",u"8x130 for LED display"],
					[u"9x15.pil",u"9x15 for LED display"],
					[u"9x15B.pil",u"9x158 for LED display"],
					[u"9x18.pil",u"9x18 for LED display"],
					[u"9x18B.pil",u"9x188 for LED display"],
					[u"10x20.pil",u"10x20 for LED display"],
					[u"clR6x12.pil",u"clR6x12 for LED display"],
					[u"RedAlert.ttf",u"RedAlert small displays"],
					[u"Courier New.ttf",u"Courier New, Mono spaced"],
					[u"Andale Mono.ttf",u"Andale, Mono spaced"],
					[u"Volter__28Goldfish_29.ttf",u"Volter__28Goldfish_29 for small displays"],
					[u"Arial.ttf",u"arial for regular monitors and small displays"]]
		return fonts

 
####-------------------------------------------------------------------------####
	def filterPiI(self, valuesDict=None, filter="self", typeId="", devId="x",action =""):

		xList = []
		for piU in _rpiBeaconList:
			if self.RPI[piU][u"piOnOff"] != u"0":
				xList.append([piU, piU])
		for piU in _rpiSensorList:
			if self.RPI[piU][u"piOnOff"] != u"0":
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
			if unicode(e) != u"None":
				self.indiLOG.log(40,u"Line {} has error={}".format(sys.exc_traceback.tb_lineno, e))


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
			except:	 gpio = u"-1"

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
					xxx[inSi]	= {u"gpio": gpio,  u"inpType": "", u"count": valuesDict[u"count"]}


			pinMappings =""
			# clean up
			for n in range(nChannels):
				if u"gpio" in xxx[n]:
					if xxx[n][u"gpio"] == u"-1" or xxx[n][u"gpio"] =="":
						xxx[n]={}

					pinMappings+=unicode(n)+u":"+xxx[n][u"gpio"]+u"|"
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
					xList.append([piU,u"#"+piU+u"-"+self.RPI[piU][u"ipNumberPi"]+name])

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
					pinMappings += unicode(n) + ":" + xxx[n][u"gpio"]+u"," + xxx[n][u"outType"]+u"," + xxx[n][u"initialValue"] + u"|"
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
		xList = [(u"0",u"internal temp sensor of RPI")]
		try:
			piN = indigo.devices[devId].states[u"note"].split(u"-")
			if len(piN) >1:
				piN = piN[1]
				#indigo.server.log(u" dev Pi #sensor: " + piN)
				for dev in indigo.devices.iter(u"props.isTempSensor"):
					props = dev.pluginProps
					#self.indiLOG.log(20,u" selecting devid name temp sensor: {} pi#: {}".format(dev.name, props[u"piServerNumber"]) )
					if props[u"piServerNumber"] == piN:
						xList.append( (unicode(dev.id), u"{} {}".format(dev.name, dev.id) ))

		except Exception, e:
			if unicode(e) != u"None":
				self.indiLOG.log(40,u"Line {} has error={}".format(sys.exc_traceback.tb_lineno, e))

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
					   
			inS = u"0"
			inSi = int(inS)
			if valuesDict[u"gpio"] == u"0":
				xxx[inSi] = {}
			else:
				xxx[inSi] = {u"gpio": valuesDict[u"gpio"],"outType": valuesDict[u"outType"],"initialValue": valuesDict[u"initialValue"]}
			pinMappings = ""
			# clean up
			for n in range(nChannels):
				if u"gpio" in xxx[n]:
					if xxx[n][u"gpio"] == u"0":
						del xxx[n]
					if	len(oldxxx) < (n+1) or "initialValue" not in oldxxx[n] or (xxx[n][u"initialValue"] != oldxxx[n][u"initialValue"]):
						self.sendInitialValue = dev.id
					pinMappings += unicode(n) + u":" + xxx[n][u"gpio"]+ u"," + xxx[n][u"outType"]+ u"," + xxx[n][u"initialValue"]+u"|"
					if u"inverse" in dev.states:
						if (dev.states[u"inverse"] =="yes") != (xxx[n][u"outType"]=="1"): dev.updateStateOnServer(u"inverse", xxx[n][u"outType"]==u"1" )
					elif u"inverse_{:2d}".format(n) in dev.states:
						if (dev.states[u"inverse_{:2d}".format(n)] =="yes") != (xxx[n][u"outType"]==u"1"): dev.updateStateOnServer(u"inverse_{:2d}".format(n), xxx[n][u"outType"]==u"1" )
					if u"initial" in dev.states:
						if dev.states[u"initial"] != xxx[n][u"initialValue"]: dev.updateStateOnServer(u"initial", xxx[n][u"initialValue"])
					elif u"initial{:2d}".format(n) in dev.states:
						if dev.states[u"initial{:2d}".format(n)] != xxx[n][u"initialValue"]: dev.updateStateOnServer(u"initial{:2d}".format(n), xxx[n][u"initialValue"] )
					
					for l in range(n, nChannels):
						if l == n: continue
						if u"gpio" not in xxx[l]:	continue
						if xxx[l][u"gpio"] == u"0":	continue
						if xxx[n][u"gpio"] == xxx[l][u"gpio"]:
							pinMappings = u"error # " + unicode(n) + u" same pin as #" + unicode(l)
							xxx[l][u"gpio"] = u"0"
							valuesDict[u"gpio"] = u"0"
							break
					if u"error" in pinMappings: break

			valuesDict[u"pinMappings"] = pinMappings
			valuesDict[u"deviceDefs"] = json.dumps(xxx)
			self.indiLOG.log(10,u"len:{};  deviceDefs:{}".format(nChannels, valuesDict[u"deviceDefs"]))
			return valuesDict

####-------------------------------------------------------------------------####
	def sendConfigCALLBACKaction(self, action1=None, typeId="", devId=0):
		try:
			valuesDict = action1.props
			if valuesDict[u"configurePi"] =="": return
			return self.execButtonConfig(valuesDict, level="0,", action=[u"updateParamsFTP"], Text="send Config Files to pi# ")
		except:
			self.indiLOG.log(20,u"sendConfigCALLBACKaction  bad rPi number:"+ unicode(valuesDict))


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
		return self.execButtonConfig(valuesDict, level="master,", action=[u"initSSH",u"updateAllFilesFTP",u"restartmasterSSH"], Text="send ALL Files to pi# ")

####-------------------------------------------------------------------------####
	def buttonSendINITCALLBACK(self, valuesDict=None, typeId="", devId=0):
		return self.execButtonConfig(valuesDict, level="0,", action=[u"initSSH",u"updateAllFilesFTP",u"rebootSSH"], Text="make dirs etc on RPI, send pgms,... only once")


####-------------------------------------------------------------------------####
	def buttonShutdownsshCALLBACKaction(self, action1=None, typeId="", devId=0):
		return self.buttonShutdownsshCALLBACK(valuesDict=action1.props)

####-------------------------------------------------------------------------####
	def buttonShutdownsshCALLBACK(self, valuesDict=None, typeId="", devId=0):
		self.setCurrentlyBooting(self.bootWaitTime, setBy=u"buttonShutdownsshCALLBACK")
		return self.execButtonConfig(valuesDict, level="0,", action=[u"shutdownSSH"], Text="shut down rPi# ")

####-------------------------------------------------------------------------####
	def buttonSendAllandRebootsshCALLBACK(self, valuesDict=None, typeId="", devId=0):
		self.setCurrentlyBooting(self.bootWaitTime, setBy=u"buttonSendAllandRebootsshCALLBACK")
		return self.execButtonConfig(valuesDict, level="0,", action=[u"initSSH",u"updateAllFilesFTP",u"rebootSSH"], Text="rPi configure and reboot pi# ")


####-------------------------------------------------------------------------####
	def buttonRebootsshCALLBACKaction(self,	action1=None, typeId="", devId=0):
		self.buttonRebootSocketCALLBACK(valuesDict=action1.props)

####-------------------------------------------------------------------------####
	def buttonRebootsshCALLBACK(self, valuesDict=None, typeId="", devId=0):
		self.setCurrentlyBooting(self.bootWaitTime, setBy=u"buttonRebootsshCALLBACK")
		return self.execButtonConfig(valuesDict, level="0,", action=[u"rebootSSH"], Text="rPi reboot")

####-------------------------------------------------------------------------####
	def buttonStopConfigCALLBACK(self, valuesDict=None, typeId="", devId=0):
		return self.execButtonConfig(valuesDict, level="0,", action=[""], Text="rPi stop Configure ")


####-------------------------------------------------------------------------####
	def buttonGetSystemParametersCALLBACK(self, valuesDict=None, typeId="", devId=0):
		return self.execButtonConfig(valuesDict, level="0,", action=[u"getStatsSSH"], Text="get stats from rpi")


####-------------------------------------------------------------------------####
	def buttonbuttonGetpiBeaconLogCALLBACK(self, valuesDict=None, typeId="", devId=0):
		return self.execButtonConfig(valuesDict, level="0,", action=[u"getLogFileSSH"], Text="get pibeacon logfile from rpi")

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
				if self.decideMyLog(u"UpdateRPI"): self.indiLOG.log(10,Text + piU+u"  action string:"+ unicode(action)	 )
				self.rPiRestartCommand[pi] = level	## which part need to restart on rpi
				self.setONErPiV(piU,u"piUpToDate", action, resetQueue=True)
		except Exception, e:
			if unicode(e) != u"None":
				self.indiLOG.log(40,u"Line {} has error={}".format(sys.exc_traceback.tb_lineno, e))
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
					if self.decideMyLog(u"UpdateRPI"): self.indiLOG.log(10,u"configuring WiFi on pi#" + piU)
					self.rPiRestartCommand = [u"restart" for ii in range(_GlobalConst_numberOfRPI)]	 ## which part need to restart on rpi
					self.configureWifi(piU)
				else:
					self.indiLOG.log(20,u"buttonConfirmWiFiCALLBACK configuring WiFi: SSID and password not set")

		if pi < 99:
			if self.wifiSSID != "" and self.wifiPassword != "":
				if self.decideMyLog(u"UpdateRPI"): self.indiLOG.log(10,u"configuring WiFi on pi#" + piU)
				self.rPiRestartCommand[pi] = u"reboot"  ## which part need to restart on rpi
				self.configureWifi(piU)
			else:
				self.indiLOG.log(20,u"buttonConfirmWiFiCALLBACK configuring WiFi: SSID and password not set")

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
		out= json.dumps([{u"command":"general",u"cmdLine":"sudo killall -9 python;sync;sleep 5;sudo halt &"}])
		if pi == 999:
			for piU in self.RPI:
				self.indiLOG.log(20,u"hard shutdown of rpi {};   ".format(self.RPI[piU][u"ipNumberPi"], out) )
				self.presendtoRPI(piU,out)
		else:
				self.indiLOG.log(20,u"hard shutdown of rpi {};   ".format(self.RPI[piU][u"ipNumberPi"], out) )
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

		out= json.dumps([{u"command":"general",u"cmdLine":"sudo killall -9 python;sync;sleep 5;sudo reboot -f &"}])
		if pi == 999:
			for piU in self.RPI:
				self.presendtoRPI(piU,out)
		else:
				self.indiLOG.log(20,u"hard reboot of rpi{};   ".format(self.RPI[piU][u"ipNumberPi"], out) )
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

		out= json.dumps([{u"command":"general",u"cmdLine":"sudo killall -9 python;sleep 4; sudo reboot &"}])
		if pi == 999:
			for piU in self.RPI:
				self.indiLOG.log(20,u"regular reboot of rpi {};  {}".format(self.RPI[piU][u"ipNumberPi"], out) )
				self.presendtoRPI(piU,out)
		else:
				self.indiLOG.log(20,u"regular reboot of rpi {};  {}".format(self.RPI[piU][u"ipNumberPi"], out) )
				self.presendtoRPI(piU,out)

		return


####-------------------------------------------------------------------------####
	def setTimeCALLBACKaction(self, action1=None, typeId="", devId=0):
		self.doActionSetTime(action1.props[u"configurePi"])# do it now
		return

####-------------------------------------------------------------------------####
	def buttonsetTimeCALLBACK(self, valuesDict=None, typeId="", devId=0):
		self.actionList[u"setTime"].append({u"action":"setTime",u"value":valuesDict[u"configurePi"]}) # put it into queue and return to menu
		return

####-------------------------------------------------------------------------####
	def refreshNTPCALLBACKaction(self, action1=None, typeId="", devId=0):
		valuesDict = action1.props
		self.buttonrefreshNTPCALLBACK(valuesDict)
		return

####-------------------------------------------------------------------------####
	def buttonrefreshNTPCALLBACK(self, valuesDict=None, typeId="", devId=0):
		valuesDict[u"anyCmdText"] = u"refreshNTP"
		self.buttonAnycommandCALLBACK(valuesDict)
		return

####-------------------------------------------------------------------------####
	def stopNTPCALLBACKaction(self,	 action1=None, typeId="", devId=0):
		valuesDict = action1.props
		self.buttonstopNTPCALLBACK(valuesDict)
		return

####-------------------------------------------------------------------------####
	def buttonstopNTPCALLBACK(self, valuesDict=None, typeId="", devId=0):
		valuesDict[u"anyCmdText"] = u"stopNTP"
		self.buttonAnycommandCALLBACK(valuesDict)
		return


####-------------------------------------------------------------------------####
	def doActionSetTime(self, piU):
		try: 
			if piU not in self.RPI: return 

		except: 
			self.indiLOG.log(20,u"ERROR	set time of rpi	 bad PI# given:"+piU )
			return

		try: 

			ipNumberPi = self.RPI[piU][u"ipNumberPi"]
			dt =0
			xx, retC = self.testDeltaTime( piU, ipNumberPi,dt)
			for ii in range(5):
				dt , retC  = self.testDeltaTime( piU, ipNumberPi, dt*0.9)
				if retC !=0:
					self.indiLOG.log(20,u"sync time	MAC --> RPI, did not work, no connection to RPI# {}".format(piU) )
					return 
				if abs(dt) < 0.5: break 

			self.indiLOG.log(20,u"set time of RPI# {}  finished, new delta time ={:6.1f}[secs]".format(piU,dt))

		except Exception, e:
			if unicode(e) != u"None":
				self.indiLOG.log(40,u"Line {} has error={}".format(sys.exc_traceback.tb_lineno, e))

		return

####-------------------------------------------------------------------------####
	def testDeltaTime(self, piU, ipNumberPi, tOffset):
		try: 

			dateTimeString = datetime.datetime.fromtimestamp(time.time()+ tOffset).strftime(_defaultDateStampFormat+u".%f")
			out= json.dumps([{u"command":"general",u"cmdLine":"setTime="+dateTimeString}])
			retC = self.presendtoRPI(piU,out)
			if retC !=0: return 0, retC
			if self.decideMyLog(u"UpdateRPI"):self.indiLOG.log(20,u"set time # of rpi:{}; ip:{};  offset-used:{:5.2f};  cmd:{}".format(piU, ipNumberPi, tOffset, json.dumps(out)) )

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
			if unicode(e) != u"None":
				self.indiLOG.log(40,u"Line {} has error={}".format(sys.exc_traceback.tb_lineno, e))


		return 0, -1


####-------------------------------------------------------------------------####
	def sendAnycommandCALLBACKaction(self, action1=None, typeId="", devId=0):
		self.buttonAnycommandCALLBACK(valuesDict=action1.props)
		return

####-------------------------------------------------------------------------####
	def buttonAnycommandCALLBACK(self, valuesDict=None, typeId="", devId=0):
		piU = valuesDict[u"configurePi"]
		if piU =="": 
			self.indiLOG.log(20,u"send YOUR command to rpi ...  no RPI selected")
			return
		if piU == u"999":
			for piU in self.RPI:
				out= json.dumps([{u"command":"general",u"cmdLine":valuesDict[u"anyCmdText"]}])
				if self.RPI[piU][u"ipNumberPi"] !="":
					self.indiLOG.log(20,u"send YOUR command to rpi:{}  {};  {}".format(piU, self.RPI[piU][u"ipNumberPi"], json.dumps(out)) )
					self.presendtoRPI(piU,out)
		else:
				out= json.dumps([{u"command":"general",u"cmdLine":valuesDict[u"anyCmdText"]}])
				self.indiLOG.log(20,u"send YOUR command to rpi:{}  {};  {}".format(piU, self.RPI[piU][u"ipNumberPi"], json.dumps(out)) )
				self.presendtoRPI(piU,out)
			
		return


####-------------------------------------------------------------------------####
	def filterBeacons(self, valuesDict=None, filter="", typeId="", devId=0, action=""):
		xList = []
		for dev in indigo.devices.iter(u"props.isBeaconDevice"):
			xList.append((dev.id,u"{}".format(dev.name)))
		xList.append((0,u"delete"))
		return xList

####-------------------------------------------------------------------------####
	def filterBeaconsWithBattery(self, valuesDict=None, filter="", typeId="", devId=0, action=""):
		xList = []
		for dev in indigo.devices.iter(u"props.isBeaconDevice"):
			if self.decideMyLog(u"Special"):  
				try: self.indiLOG.log(20,u"filterBeaconsWithBattery: checking:  {}".format(dev.name) )
				except: indigo.server.log(dev.name)
			props = dev.pluginProps
			if u"SupportsBatteryLevel" not in props or not props[u"SupportsBatteryLevel"]: 
				if self.decideMyLog(u"Special"): self.indiLOG.log(20,u"filterBeaconsWithBattery:  ... rejected as SupportsBatteryLevel is not enabled in device edit" )
				continue
			if u"batteryLevelUUID"     not in props or props[u"batteryLevelUUID"] != u"gatttool": 	
				if self.decideMyLog(u"Special"): self.indiLOG.log(20,u"filterBeaconsWithBattery:  ... rejected as gattool is not enabled in device edit..")
				continue
			xList.append((dev.id, u"{} - {}".format(dev.name, dev.address) ))
		xList.append([u"0",u"all"])
		return xList


####-------------------------------------------------------------------------####
	def filterSoundFiles(self, valuesDict=None, filter="", typeId="", devId=0, action=""):
		xList = []
		for fileName in os.listdir(self.indigoPreferencesPluginDir+u"soundFiles/"):
			xList.append((fileName,fileName))
		return xList

####-------------------------------------------------------------------------####
	def filterSensorONoffIcons(self, valuesDict=None, filter="", typeId="", devId=0, action=""):
		xList = []
		for ll in _GlobalConst_ICONLIST:
			xList.append((ll[0]+u"-"+ll[1],ll[0]+u", u"+ll[1]))
		xList.append((u"-",u"     "))
		return xList


####-------------------------------------------------------------------------####
	def filterPiD(self, valuesDict=None, filter="", typeId="", devId=0, action=""):
		xList = []
		for piU in _rpiBeaconList:
			if self.RPI[piU][u"piOnOff"] == u"0" or self.RPI[piU][u"ipNumberPi"] == "":
				xList.append([piU, piU + "-"])
			else:
				xList.append([piU, piU + "-" + self.RPI[piU][u"ipNumberPi"] + "-" + self.RPI[piU][u"piMAC"]])
		for piU in _rpiSensorList:
			if self.RPI[piU][u"piOnOff"] == u"0" or self.RPI[piU][u"ipNumberPi"] == "":
				xList.append([piU, piU + "-  - Sensor Only"])
			else:
				xList.append([piU, piU + "-" + self.RPI[piU][u"ipNumberPi"] + "- Sensor Only"])
		return xList

####-------------------------------------------------------------------------####
	def filterPiDONoff(self, valuesDict=None, filter="", typeId="", devId=0, action=""):
		xList = [[u"-1",u"off"]]
		for piU in _rpiBeaconList:
			if self.RPI[piU][u"piOnOff"] == u"0" or self.RPI[piU][u"ipNumberPi"] == "":
				xList.append([piU, piU + "-"])
			else:
				xList.append([piU, piU + "-" + self.RPI[piU][u"ipNumberPi"] + "-" + self.RPI[piU][u"piMAC"]])
		for piU in _rpiSensorList:
			if self.RPI[piU][u"piOnOff"] == u"0" or self.RPI[piU][u"ipNumberPi"] == "":
				xList.append([piU, piU + "-  - Sensor Only"])
			else:
				xList.append([piU, piU + "-" + self.RPI[piU][u"ipNumberPi"] + "- Sensor Only"])
		return xList

####-------------------------------------------------------------------------####
	def filterPiOnlyBlue(self, valuesDict=None, filter="", typeId="", devId=0, action=""):
		xList = []
		for piU in _rpiBeaconList:
			if self.RPI[piU][u"piOnOff"] == u"0" or self.RPI[piU][u"ipNumberPi"] == "":
				pass
			else:
				xList.append([piU, piU + "-" + self.RPI[piU][u"ipNumberPi"] + "-" + self.RPI[piU][u"piMAC"]])
		return xList

####-------------------------------------------------------------------------####
	def filterPibeaconOne(self, valuesDict=None, filter="", typeId="", devId=0, action=""):
		xList = []
		for piU in _rpiBeaconList:
			if self.RPI[piU][u"piOnOff"] == u"0" or self.RPI[piU][u"ipNumberPi"] == "":
				pass
			else:
				xList.append([piU, piU + "-" + self.RPI[piU][u"ipNumberPi"] + "-" + self.RPI[piU][u"piMAC"]])
		xList.append([-1,"use closest" ])
		return xList


####-------------------------------------------------------------------------####
	def filterPiC(self, valuesDict=None, typeId="", devId=0, action=""):
		xList = []
		for piU in _rpiBeaconList:
			if self.RPI[piU][u"piOnOff"] == u"0" or self.RPI[piU][u"ipNumberPi"] == "": continue
			xList.append([piU, piU + "-" + self.RPI[piU][u"ipNumberPi"] + "-" + self.RPI[piU][u"piMAC"]])
		for piU in _rpiSensorList:
			if self.RPI[piU][u"piOnOff"] == u"0" or self.RPI[piU][u"ipNumberPi"] == "": continue
			xList.append([piU, piU + "-" + self.RPI[piU][u"ipNumberPi"] + "- Sensor Only"])
		xList.append([-1, u"off"])
		return xList


####-------------------------------------------------------------------------####
	def filterPiBLE(self, valuesDict=None, typeId="", devId=0, action=""):
		xList = []
		for piU in _rpiBeaconList:
			if self.RPI[piU][u"piOnOff"] == u"0" or self.RPI[piU][u"ipNumberPi"] == "": continue
			xList.append([piU, piU + "-" + self.RPI[piU][u"ipNumberPi"] + "-" + self.RPI[piU][u"piMAC"]])
		xList.append([999, u"all"])
		return xList


####-------------------------------------------------------------------------####
	def filterPi(self, valuesDict=None, typeId="", devId=0, action=""):
		xList = []
		for piU in _rpiBeaconList:
			if self.RPI[piU][u"piOnOff"] == u"0" or self.RPI[piU][u"ipNumberPi"] == "": continue
			xList.append([piU, piU + "-" + self.RPI[piU][u"ipNumberPi"] + "-" + self.RPI[piU][u"piMAC"]])
		for piU in _rpiSensorList:
			if self.RPI[piU][u"piOnOff"] == u"0" or self.RPI[piU][u"ipNumberPi"] == "": continue
			xList.append([piU, piU + "-" + self.RPI[piU][u"ipNumberPi"] + "- Sensor Only"])
		xList.append([999, u"all"])
		return xList

####-------------------------------------------------------------------------####
	def filterPiNoAll(self, valuesDict=None, typeId="", devId=0, action=""):
		xList = []
		for piU in _rpiBeaconList:
			if self.RPI[piU][u"piOnOff"] == u"0": 	continue
			if self.RPI[piU][u"ipNumberPi"] == "": 	continue
			xList.append([piU, piU + "-" + self.RPI[piU][u"ipNumberPi"] + "-" + self.RPI[piU][u"piMAC"]])
		for piU in _rpiSensorList:
			if self.RPI[piU][u"piOnOff"] == u"0": 	continue
			if self.RPI[piU][u"ipNumberPi"] == "": 	continue
			xList.append([piU, piU + "-" + self.RPI[piU][u"ipNumberPi"] + "- Sensor Only"])
		return xList

####-------------------------------------------------------------------------####
	def filterPiOUT(self, filter="", valuesDict=None, typeId="", devId=0, action=""):
		xList = []
		default = ""
		for piU in self.RPI:
			if self.RPI[piU][u"piOnOff"] == u"0": 	continue
			if self.RPI[piU][u"ipNumberPi"] == "": 	continue
			if self.RPI[piU][u"piDevId"] == 0: 		continue
			devIDpi = self.RPI[piU][u"piDevId"]
			if typeId in self.RPI[piU][u"output"] and unicode(devId) in self.RPI[piU][u"output"][typeId]:
				try:
					default = (piU, u"Pi-" + piU + "-" + self.RPI[piU][u"ipNumberPi"] + ";  Name =" + indigo.devices[devIDpi].name)
				except Exception, e:
					self.indiLOG.log(40,u"Line {} has error={}".format(sys.exc_traceback.tb_lineno, e))
					self.indiLOG.log(40,u" devid " + unicode(devIDpi))
				continue
			else:
				try:
					xList.append((piU, u"Pi-" + piU + u"-" + self.RPI[piU][u"ipNumberPi"] + u";  Name =" + indigo.devices[devIDpi].name))
				except Exception, e:
					self.indiLOG.log(40,u"Line {} has error={}".format(sys.exc_traceback.tb_lineno, e))
					self.indiLOG.log(40,u" devid " + unicode(devIDpi))

		if default != "":
			xList.append(default)

		return xList



####-------------------------------------------------------------------------####
	def filterActiveBEACONs(self, valuesDict=None, typeId="", devId=0, action=""):

		try:
			listActive = []
			for mac in self.beacons:
				if len(mac) < 5 or mac.find(u"00:00:00:00") ==0: continue
				try:
					name = indigo.devices[self.beacons[mac][u"indigoId"]].name
				except:
					continue
				if self.beacons[mac][u"ignore"] <= 0 and self.beacons[mac][u"indigoId"] != 0:
					listActive.append([mac, name + "- active, used"])
			listActive = sorted(listActive, key=lambda tup: tup[1])
		except Exception, e:
			if unicode(e) != u"None":
				self.indiLOG.log(40,u"Line {} has error={}".format(sys.exc_traceback.tb_lineno, e))
			listActive = []
		return listActive

####-------------------------------------------------------------------------####
	def filterMACs(self, valuesDict=None, typeId="", devId=0, action=""):

		try:
			listActive		 = []
			listDeleted		 = []
			listIgnored		 = []
			listOldIgnored	 = []

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
						self.indiLOG.log(40,u"Line {} has error={}".format(sys.exc_traceback.tb_lineno, e))
						self.indiLOG.log(40,u"communication to indigo is interrupted")
						return
					name = mac

				if self.beacons[mac][u"ignore"] == 1:
					listIgnored.append([mac, u"{}- on ignoredList",format(name)])
			listIgnored = sorted(listIgnored, key=lambda tup: tup[1])

			for mac in self.beacons:
				if len(mac) < 5: continue
				if self.beacons[mac][u"ignore"] == 2:
					listOldIgnored.append([mac, u"{}- on ignoredList- old".format(mac)])
			listOldIgnored = sorted(listOldIgnored, key=lambda tup: tup[1])

			return  listOldIgnored + listDeleted + listIgnored + listActive
		except Exception, e:
			if unicode(e) != u"None":
				self.indiLOG.log(40,u"Line {} has error={}".format(sys.exc_traceback.tb_lineno, e))
		return []


####-------------------------------------------------------------------------####
	def filterRPIs(self, valuesDict=None, typeId="", devId=0, action=""):

		try:	
			listActive = []
			for dev in indigo.devices.iter(u"props.isRPIDevice"):
				if dev.deviceTypeId !=u"rPI": continue
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
					ipN	 = dev.description
					listActive.append([unicode(indigoId), u"{} - {}".format(name, ipN) ])

				except:
					pass
			return sorted(listActive, key=lambda tup: tup[1])

		except Exception, e:
			if unicode(e) != u"None":
				self.indiLOG.log(40,u"Line {} has error={}".format(sys.exc_traceback.tb_lineno, e))
		return []




####-------------------------------------------------------------------------####

	def getMenuActionConfigUiValues(self, menuId):
		#self.indiLOG.log(20,u"getMenuActionConfigUiValues menuId".format(menuId) )
		valuesDict = indigo.Dict()
		errorMsgDict = indigo.Dict()
		if  menuId == u"AcceptNewBeacons":
			valuesDict[u"acceptNewiBeacons"] = u"999"
			valuesDict[u"acceptNewTagiBeacons"] = u"off"
			valuesDict[u"MSG"] = u"RSSI >{}; Tag={}".format(self.acceptNewiBeacons, self.acceptNewTagiBeacons)
		elif menuId == u"xx":
			pass
		else:
			pass
		return (valuesDict, errorMsgDict)

####-------------------------------------------------------------------------####
	def buttonConfirmnewBeaconsLogTimerCALLBACK(self, valuesDict=None, typeId="", devId=0):
		try:
			xx = float(valuesDict[u"newBeaconsLogTimer"])
			if xx > 0: 
				self.newBeaconsLogTimer = time.time() + xx*60
				self.indiLOG.log(20,u"newBeaconsLogTimer set to: {} minutes".format(valuesDict[u"newBeaconsLogTimer"]) )
				valuesDict["MSG"]  = u"newBeaconsLogTimer: {} min".format(valuesDict[u"newBeaconsLogTimer"])
			else:
				self.newBeaconsLogTimer = 0
				valuesDict["MSG"]  = u"newBeaconsLogTimer:off"
		except Exception, e:
			if unicode(e) != u"None":
				self.indiLOG.log(40,u"Line {} has error={}".format(sys.exc_traceback.tb_lineno, e))
				valuesDict["MSG"]  = u"error, check log"
			self.newBeaconsLogTimer = 0
		return valuesDict


####-------------------------------------------------------------------------####
	def buttonConfirmSelectBeaconCALLBACK(self, valuesDict=None, typeId="", devId=0):
		try:
			if self.isValidMAC(valuesDict[u"selectBEACONmanual"]):
				mac = valuesDict[u"selectBEACONmanual"]
				self.selectBeaconsLogTimer[mac]	 = 17
				self.indiLOG.log(20,u"log messages for mac:{}".format(mac) )
				valuesDict["MSG"]  = u"tracking of new beacon started:" + mac
				return valuesDict

			elif len(valuesDict[u"selectBEACONmanual"]) >0:
				self.indiLOG.log(30,u"bad mac given:{}".format(valuesDict[u"selectBEACONmanual"]))
				valuesDict["MSG"]  = u"bad mac given:{}".format(valuesDict[u"selectBEACONmanual"])
				return valuesDict
								
			else:
				id	= self.beacons[valuesDict[u"selectBEACON"]][u"indigoId"]
				length = int(valuesDict[u"selectBEACONlen"])
				dev = indigo.devices[int(id)]
				self.indiLOG.log(20,u"log messages for  beacon:{} mac:{}".format(dev.name, valuesDict[u"selectBEACON"][:length]) )
				self.selectBeaconsLogTimer[valuesDict[u"selectBEACON"]]	 = length
				valuesDict["MSG"]  = u"track beacon:{}".format(dev.name)

		except Exception, e:
			if unicode(e) != u"None":
				self.indiLOG.log(40,u"Line {} has error={}".format(sys.exc_traceback.tb_lineno, e))
			return valuesDict
		return valuesDict


####-------------------------------------------------------------------------####
	def buttonConfirmStopSelectBeaconCALLBACK(self, valuesDict=None, typeId="", devId=0):
		self.selectBeaconsLogTimer ={}
		self.indiLOG.log(20,u"log messages stopped")
		valuesDict["MSG"] = u"tracking of beacon stopped"
		return valuesDict



####-------------------------------------------------------------------------####
	def buttonConfirmselectLargeChangeInSignalCALLBACK(self, valuesDict=None, typeId="", devId=0):
		xx =  valuesDict[u"trackSignalStrengthIfGeaterThan"].split(u",")
		self.trackSignalStrengthIfGeaterThan = [float(xx[0]),xx[1]]

		if self.trackSignalStrengthIfGeaterThan[0] > 150:
			startStop  = "stopped"
		else:
			startStop  = "started"
			
		if xx[1] ==u"i":
			if startStop == "started":
				self.indiLOG.log(20,u"log messages for beacons with signal strength change GT {}  including ON->off and off-ON".format(self.trackSignalStrengthIfGeaterThan[0]))
				valuesDict["MSG"]  = u"signl > {} w on/off".format(self.trackSignalStrengthIfGeaterThan[0])
			else:
				self.indiLOG.log(20,u"log messages for beacons with signal strength ... stopped")
				valuesDict["MSG"]  = u"signl logging   stopped"
		else:
			if startStop == "started":
				self.indiLOG.log(20,u"log messages for beacons with signal strength change GT {}  excluding ON->off and off-ON".format(self.trackSignalStrengthIfGeaterThan[0]))
				valuesDict["MSG"]  = u"signl > {} w/o on/off".format(self.trackSignalStrengthIfGeaterThan[0])
			else:
				self.indiLOG.log(20,u"log messages for beacons with signal strength ... stopped")
				valuesDict["MSG"]  = u"signl logging   stopped"
		return valuesDict

####-------------------------------------------------------------------------####
	def buttonConfirmselectChangeOfRPICALLBACK(self, valuesDict=None, typeId="", devId=0):
		self.trackSignalChangeOfRPI = valuesDict[u"trackSignalChangeOfRPI"] ==u"1"
		self.indiLOG.log(20,u"log messages for beacons that change closest RPI: {}".format(self.trackSignalChangeOfRPI))
		valuesDict["MSG"] = u"log changing closest RPI: {}".format(self.trackSignalChangeOfRPI)
		return valuesDict


####-------------------------------------------------------------------------####
	def buttonExecuteReloadKnownBeaconsTagsCALLBACK(self, valuesDict=None, typeId="", devId=0):
		
		retCode = self.readknownBeacontags()
		if retCode:
			self.indiLOG.log(20,u"knownbeacontags file reloaded, and RPI update initiated")
			valuesDict[u"MSG"] = u"file reloaded, and RPI update initiated"
			self.updateNeeded = u" fixConfig "
			self.setALLrPiV(u"piUpToDate", [u"updateParamsFTP"])
		else:
			self.indiLOG.log(20,u"inputfile seems to be corrupt")
			valuesDict[u"MSG"] = u"inputfile seems to be corrupt"

		return valuesDict


####-------------------------------------------------------------------------####
	def buttonConfirmselectRPImessagesCALLBACK(self, valuesDict=None, typeId="", devId=0):
		
		try:	self.trackRPImessages = int(valuesDict[u"piServerNumber"])
		except: self.trackRPImessages = -1 
		if self.trackRPImessages == -1: 	
			self.indiLOG.log(20,u"log all messages from pi: off" )
		else:
			self.indiLOG.log(20,u"log all messages from pi: {}".format(self.trackRPImessages ))

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



			if oldDEV.states[u"status"].lower() != u"expired":
				self.indiLOG.log(20,u"ERROR can not replace existing active beacon;{}   still active".format(oldName) )
				valuesDict[u"MSG"] = u"ERROR can not replace existing ACTIVE beacon"
				return valuesDict
			if oldMAC == newMAC:
				self.indiLOG.log(20,u"ERROR, can't replace itself")
				valuesDict[u"MSG"] = u"ERROR,choose 2 different beacons"
				return valuesDict

			oldPROPS[u"address"] = newMAC
			self.deviceStopCommIgnore = time.time()
			oldDEV.replacePluginPropsOnServer(oldPROPS)

			self.beacons[newMAC] = copy.deepcopy(self.beacons[oldMAC])
			self.beacons[newMAC][u"indigoId"] = oldINDIGOid
			del self.beacons[oldMAC]
			indigo.device.delete(newDEV)

			self.indiLOG.log(30,u"=== deleting  === replaced MAC number {}  of device {} with {} --	and deleted device {}    ===".format(oldMAC, oldName, newMAC, newName) )
			valuesDict[u"MSG"] = u"replaced, moved MAC number"

		except Exception, e:
			if unicode(e) != u"None":
				self.indiLOG.log(40,u"Line {} has error={}".format(sys.exc_traceback.tb_lineno, e))
		return valuesDict

####-------------------------------------------------------------------------####
	def buttonExecuteReplaceRPICALLBACK(self, valuesDict=None, typeId="", devId=0):

		try:

			oldID = valuesDict[u"oldID"]
			newID = valuesDict[u"newID"]
			if oldID == newID: 
				valuesDict[u"MSG"] = u"must use 2 different RPI"
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
			newPROPS[u"address"] = newMAC[:-1]+u"x"
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

			self.fixConfig(checkOnly = [u"all",u"rpi"],fromPGM=u"buttonExecuteReplaceRPICALLBACK")
			self.indiLOG.log(30,u"=== replaced MAC number {}  of device {} with {} --	and deleted device {}    ===".format(oldMAC, oldName, newMAC, newName) )
			valuesDict[u"MSG"] = u"replaced, moved MAC number"

		except Exception, e:
			if unicode(e) != u"None":
				self.indiLOG.log(40,u"Line {} has error={}".format(sys.exc_traceback.tb_lineno, e))
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
					self.setONErPiV(piU,u"piUpToDate", [u"updateParamsFTP"], resetQueue=True)
		else:
			self.beacons[mac] = copy.deepcopy(_GlobalConst_emptyBeacon)
			self.beacons[mac][u"ignore"] = 1
			self.newIgnoreMAC += 1
			self.beacons[mac][u"created"] = datetime.datetime.now().strftime(_defaultDateStampFormat)
		self.indiLOG.log(30,u"setting {};  indigoId: {} to ignore -mode: {}".format(mac, self.beacons[mac][u"indigoId"], self.beacons[mac][u"ignore"]) )
		self.beacons[mac][u"status"] = u"ignored"
		if self.beacons[mac][u"indigoId"] >0: 
			try:
				self.indiLOG.log(30,u"=== deleting buttonConfirmMACIgnoreCALLBACK deleting dev  MAC#{}  indigoID ==0".format(mac) )
				indigo.device.delete(indigo.devices[self.beacons[mac][u"indigoId"]])
			except:
				self.indiLOG.log(40,u"buttonConfirmMACIgnoreCALLBACK error deleting dev  MAC#{}".format(mac) )

		self.makeBeacons_parameterFile()
		for piU in _rpiBeaconList:
			self.setONErPiV(piU,u"piUpToDate", [u"updateParamsFTP"], resetQueue=True)


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

		self.indiLOG.log(20,u"setting {} indigoId: {} to un-ignore -mode:{}".format(mac, self.beacons[mac][u"indigoId"], self.beacons[mac][u"ignore"]) )
		if self.beacons[mac][u"indigoId"] ==0:
			self.createNewiBeaconDeviceFromBeacons(mac)

		self.makeBeacons_parameterFile()
		for piU in _rpiBeaconList:
			self.setONErPiV(piU,u"piUpToDate", [u"updateParamsFTP"], resetQueue=True)

		return valuesDict

####-------------------------------------------------------------------------####
	def createNewiBeaconDeviceFromBeacons(self, mac):
		try:
			name = u"beacon_" + mac
			dev= indigo.device.create(
				protocol		= indigo.kProtocol.Plugin,
				address			= mac,
				name			= name,
				description		= u"a-a-a",
				pluginId		= self.pluginId,
				deviceTypeId	= u"beacon",
				folder			= self.piFolderId,
				props		    = copy.deepcopy(_GlobalConst_emptyBeaconProps_)
				)
			self.beacons[mac][u"indigoId"] = dev.id

		except Exception, e:
				if unicode(e).find(u"timeout waiting") > -1:
					self.indiLOG.log(40,u"Line {} has error={}".format(sys.exc_traceback.tb_lineno, e))



####-------------------------------------------------------------------------####
	def buttonConfirmMACDeleteCALLBACK(self, valuesDict=None, typeId="", devId=0):
		mac = valuesDict[u"ignoreMAC"]
		if mac in self.beacons:
			for piU in _rpiBeaconList:
				self.setONErPiV(piU,u"piUpToDate", [u"updateParamsFTP"], resetQueue=True)
			del self.beacons[mac]
		self.fixConfig(checkOnly = [u"all",u"rpi"],fromPGM=u"buttonConfirmMACDeleteCALLBACK")
		return valuesDict

####-------------------------------------------------------------------------####
	def buttonConfirmMACDeleteALLCALLBACK(self, valuesDict=None, typeId="", devId=0):

		### this is very bad !!!
		#self.beacons = {}

		self.fixConfig(checkOnly = [u"all",u"rpi"],fromPGM=u"buttonConfirmMACDeleteALLCALLBACK")
		for piU in _rpiBeaconList:
			self.setONErPiV(piU,u"piUpToDate", [u"updateParamsFTP"], resetQueue=True)
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
			if self.beacons[beacon][u"indigoId"] != 0:		continue
			if int(self.beacons[beacon][u"ignore"]) == 0:	continue
			delB.append(beacon)

		for beacon in delB:
			del self.beacons[beacon]


		self.fixConfig(checkOnly = [u"all",u"rpi"],fromPGM=u"buttonConfirmMACnonactiveCALLBACK")
		ll2 = len(self.beacons)
		self.indiLOG.log(20,u"from initially good {} beacons # of beacons removed from BEACONlist:{}".format(ll0, ll0-ll2) )


####-------------------------------------------------------------------------####
	def buttonConfirmMACDeleteOLDHISTORYCALLBACK(self, valuesDict=None, typeId="", devId=0):
		delB = []
		ll0 = len(self.beacons)
		for beacon in self.beacons:
			#self.indiLOG.log(20,u"beacon= {} testing  , indigoID:{}".format(beacon, self.beacons[beacon][u"indigoId"]) )
			if self.beacons[beacon][u"indigoId"] != 0:
				try:
					dd= indigo.devices[self.beacons[beacon][u"indigoId"]]
					continue
				except Exception, e:
					if unicode(e).find(u"timeout waiting") >-1: continue
					self.indiLOG.log(40,u"Line {} has error={}".format(sys.exc_traceback.tb_lineno, e))

			#self.indiLOG.log(20,u"beacon= {} selected  (deleted/ignored) history .. can be used again -- 1".format(beacon) )
			delB.append(beacon)

		for beacon in delB:
			self.indiLOG.log(20,u"beacon= {} removing from (deleted/ignored) history .. can be used again".format(beacon) )
			del self.beacons[beacon]
		if len(delB) > 0:
			self.writeJson(self.beacons, fName=self.indigoPreferencesPluginDir + "beacons", fmtOn=self.beaconsFileSort)

	 
		try:
			subprocess.call(u"rm '{}rejected/rejects*'".format(self.indigoPreferencesPluginDir), shell=True )
			self.indiLOG.log(20,u"old rejected/rejects files removed".format(self.indigoPreferencesPluginDir))
		except: pass


		self.fixConfig(checkOnly = [u"all",u"rpi"],fromPGM=u"buttonConfirmMACDeleteOLDHISTORYCALLBACK")
		ll2 = len(self.beacons)
		self.indiLOG.log(20,u"from initially good {} beacons # of beacons removed from BEACONlist: {}".format(ll0, ll0-ll2) )
		self.setALLrPiV(u"piUpToDate", [u"updateParamsFTP"])

		return valuesDict

####-------------------------------------------------------------------------####
	def buttonSetAllExistingDevicesToActiveCALLBACK(self, valuesDict=None, typeId="", devId=0):
		for beacon in self.beacons:
			if self.beacons[beacon][u"indigoId"] != 0: 
				self.beacons[beacon][u"ignore"] = 0
				try:
					dev = indigo.devices[int(self.beacons[beacon][u"indigoId"])]
					props = dev.pluginProps
					props[u"ignore"] = u"0"
					props[u"enabled"] = True
					self.deviceStopCommIgnore = time.time()
					dev.replacePluginPropsOnServer(props)
 				except:
					pass
		self.indiLOG.log(20,u"set all existing iBeacon devices to active")

		return valuesDict
####-------------------------------------------------------------------------####
	def buttonSetAllExistingDevicesToOFFCALLBACK(self, valuesDict=None, typeId="", devId=0):
		for beacon in self.beacons:
			if self.beacons[beacon][u"indigoId"] != 0: 
				self.beacons[beacon][u"ignore"] = 1
				try:
					dev = indigo.devices[int(self.beacons[beacon][u"indigoId"])]
					props = dev.pluginProps
					props[u"ignore"] = u"1"
					props[u"enabled"] = False
					self.deviceStopCommIgnore = time.time()
					dev.replacePluginPropsOnServer(props)
 				except:
					pass
		self.indiLOG.log(20,u"set all existing iBeacon devices to in active")

		return valuesDict
####-------------------------------------------------------------------------####
	def buttonSetAllbeaconsTonoFastDownCALLBACK(self, valuesDict=None, typeId="", devId=0):
		for dev in indigo.devices.iter(u"props.isBeaconDevice"):
			try:
				props = dev.pluginProps
				props[u"fastDown"] = u"0"
				self.deviceStopCommIgnore = time.time()
				dev.replacePluginPropsOnServer(props)
			except:
				pass
		self.indiLOG.log(20,u"set all existing iBeacon devices to no fastDown")
		self.fixConfig(checkOnly = [u"all",u"rpi"],fromPGM=u"buttonSetAllbeaconsTonoFastDownCALLBACK")
		self.setALLrPiV(u"piUpToDate", [u"updateParamsFTP"])
		valuesDict[u"MSG"] = u"all beacon set to no Fast Down"
		return valuesDict
###-------------------------------------------------------------------------####
	def buttonSetAllbeaconsTonoSignalDeltaCALLBACK(self, valuesDict=None, typeId="", devId=0):
		for dev in indigo.devices.iter(u"props.isBeaconDevice"):
			try:
				props = dev.pluginProps
				props[u"signalDelta"] = u"999"
				self.deviceStopCommIgnore = time.time()
				dev.replacePluginPropsOnServer(props)
			except:
				pass
		self.indiLOG.log(20,u"set all existing iBeacon devices to no Signal Delta")
		self.fixConfig(checkOnly = [u"all",u"rpi"],fromPGM=u"buttonSetAllbeaconsTonoSignalDeltaCALLBACK")
		self.setALLrPiV(u"piUpToDate", [u"updateParamsFTP"])
		valuesDict[u"MSG"] = u"all beacon set to no Signal Delta"
		return valuesDict
###-------------------------------------------------------------------------####
	def buttonSetAllbeaconsTonominSignalOffCALLBACK(self, valuesDict=None, typeId="", devId=0):
		for dev in indigo.devices.iter(u"props.isBeaconDevice"):
			try:
				props = dev.pluginProps
				props[u"minSignalOff"] = u"-999"
				dev.replacePluginPropsOnServer(props)
			except:
				pass
		self.indiLOG.log(20,u"set all existing iBeacon devices to no Signal min off")
		self.fixConfig(checkOnly = [u"all",u"rpi"],fromPGM=u"buttonSetAllbeaconsTonominSignalOffCALLBACK")
		self.setALLrPiV(u"piUpToDate", [u"updateParamsFTP"])
		valuesDict[u"MSG"] = u"all beacon set to no Signal min off "
		return valuesDict
###-------------------------------------------------------------------------####
	def buttonSetAllbeaconsTonominSignalOnCALLBACK(self, valuesDict=None, typeId="", devId=0):
		for dev in indigo.devices.iter(u"props.isBeaconDevice"):
			try:
				props = dev.pluginProps
				props[u"minSignalOn"] = _GlobalConst_emptyBeaconProps[u"minSignalOn"]
				dev.replacePluginPropsOnServer(props)
			except:
				pass
		self.indiLOG.log(20,u"set all existing iBeacon devices to no fastDown")
		self.fixConfig(checkOnly = [u"all",u"rpi"],fromPGM=u"buttonSetAllbeaconsTonominSignalOnCALLBACK")
		self.setALLrPiV(u"piUpToDate", [u"updateParamsFTP"])
		valuesDict[u"MSG"] = u"all beacon set to no Signal min ON"
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
			elif u"gpio" in props:
				valuesDict[u"i" + props[u"gpio"]] = True
			else:
				for ii in range(10):
					if u"INPUTdevId"+str(ii) in props and len(props[u"INPUTdevId"+str(ii)]) >3:
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

		elif u"gpio" in props:
			gpio = props[u"gpio"]
			if valuesDict[u"INPUT_" +gpio]:
				resetGPIOCount.append(gpio)
		else:
			for ii in range(10):
				if valuesDict[u"INPUT_"+str(ii)] == True:
					if theType == u"INPUTcoincidence":
						theType= u"INPUTpulse"
						if u"INPUTdevId"+str(ii) in props and len(props[u"INPUTdevId"+str(ii)])>3:
								resetGPIOCount.append(devId)
								break
				 
		if resetGPIOCount == []: return valuesDict

		textToSend = json.dumps([{u"device": typeId, u"command":u"file",u"fileName":u"/home/pi/pibeacon/temp/"+theType+u".reset",u"fileContents":resetGPIOCount}])
		self.sendtoRPI(self.RPI[piU][u"ipNumberPi"], piU, textToSend, calledFrom=u"resetGPIOCountCALLBACKmenu")

		if self.decideMyLog(u"UpdateRPI"): self.indiLOG.log(10,u"resetGPIOCount requested: for {} on pi:{}; pins:{}".format(dev.name, piU, resetGPIOCount))
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
			xList.append((unicode(41-ii),u"Channel-"+unicode(41-ii)))
		xList.append((u"0",u"no pick"))
		return xList


####-------------------------------------------------------------------------####
	def confirmdeviceRPIanyPropBUTTON(self, valuesDict, typeId="", devId=""):
		try:
			self.anyProperTydeviceNameOrId = valuesDict[u"deviceNameOrId"]
		except:
			self.indiLOG.log(40,self.anyProperTydeviceNameOrId +u" not in defined")
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
			self.indiLOG.log(40,unicode(self.anyProperTydeviceNameOrId) +u" not in defined")
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
			self.indiLOG.log(40,valuesDict[u"deviceNameOrId"] +u" not in indigodevices")
			return

		if u"propertyName" not in valuesDict:
			self.indiLOG.log(40,u"u propertyName not in valuesDict")
			return
		props = dev.pluginProps
		propertyName =valuesDict[u"propertyName"] 
		if propertyName not in props:
			self.indiLOG.log(40,propertyName+u" not in pluginProps")
			return
		if u"propertyContents" not in valuesDict:
			self.indiLOG.log(40,u"propertyContents not in valuesDict")
			return
		self.indiLOG.log(20,u"updating {}     {}  {}".format(dev.name, propertyName, props[propertyName]))

		props[propertyName] = self.convertVariableOrDeviceStateToText(valuesDict[u"propertyContents"])

		self.deviceStopCommIgnore = time.time()
		dev.replacePluginPropsOnServer(props)
		return

####-------------------------------------------------------------------------####
	def getAnyPropertyCALLBACKaction(self, action1=None, typeId="", devId=0):
		valuesDict = action1.props
		##self.indiLOG.log(20,u" property request:"+ unicode(valuesDict) )
		try:
			var = indigo.variables[u"piBeacon_property"]
		except:
			indigo.variable.create(u"piBeacon_property", "", self.iBeaconFolderVariablesName)

		try: id = int(valuesDict[u"deviceNameOrId"])
		except: id = valuesDict[u"deviceNameOrId"]
		try: dev = indigo.devices[id]
		except: 
			self.indiLOG.log(40,valuesDict[u"deviceNameOrId"] +u" not in indigodevices")
			indigo.variable.updateValue(u"piBeacon_property",u"{} not in indigodevices".format(valuesDict[u"deviceNameOrId"]))
			return {u"propertyName":"ERROR: " +valuesDict[u"deviceNameOrId"] +u" not in indigodevices"}

		if u"propertyName" not in valuesDict:
			self.indiLOG.log(40,u"propertyName not in valuesDict")
			indigo.variable.updateValue(u"piBeacon_property",u"propertyNamenot in valuesDict")
			return {u"propertyName":"ERROR:  propertyName  not in valuesDict"}
		props = dev.pluginProps
		propertyName =valuesDict[u"propertyName"] 
		if propertyName not in props:
			self.indiLOG.log(40,propertyName+u" not in pluginProps")
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
					vd[u"MSG"] = u"error outputDev not set"
					return
###			   #self.indiLOG.log(20,unicode(vd))

			typeId			  = u"setTEA5767"
			props			  = dev.pluginProps
			piServerNumber	  = props[u"address"].split(u"-")[1]
			ip				  = self.RPI[piServerNumber][u"ipNumberPi"]
			if self.decideMyLog(u"OutputDevice"): self.indiLOG.log(10,u"pi: "+unicode(ip)+u"  "+unicode(vd))

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
				cmds[u"restart"] = u"1"
			if u"scan" in command and command[u"scan"] !="":
				cmds[u"scan"] = self.convertVariableOrDeviceStateToText(command[u"scan"])
				if u"minSignal" in command and command[u"minSignal"] !="":
					cmds[u"minSignal"] = self.convertVariableOrDeviceStateToText(command[u"minSignal"])
			if updateProps: 
				self.deviceStopCommIgnore = time.time()
				dev.replacePluginPropsOnServer(props)
				dev = indigo.devices[devId]
				self.addToStatesUpdateDict(devId,"status"   ,"f= u"+unicode(props[u"defFreq"]) + "; mute= u" +unicode(props[u"mute"]))
				self.addToStatesUpdateDict(devId,"frequency",props[u"defFreq"],decimalPlaces=1)
				self.addToStatesUpdateDict(devId,"mute"     ,props[u"mute"])
				self.executeUpdateStatesDict(onlyDevID=unicode(devId), calledFrom=u"setTEA5767CALLBACKmenu")
				if props[u"mute"] ==u"1":
						dev.updateStateImageOnServer(indigo.kStateImageSel.SensorOff)
				else:
						dev.updateStateImageOnServer(indigo.kStateImageSel.SensorOn)

			startAtDateTime = 0
			if u"startAtDateTime" in valuesDict:
				startAtDateTime = self.setDelay(startAtDateTimeIN=self.convertVariableOrDeviceStateToText(vd[u"startAtDateTime"]))

			textToSend = json.dumps([{u"device": typeId, u"startAtDateTime":startAtDateTime,"command":"file",u"fileName":"/home/pi/pibeacon/setTEA5767.inp",u"fileContents":cmds}])


			try:
				line = u"\n##=======use this as a python script in an action group action :=====\n"
				line +="plug = indigo.server.getPlugin(\"com.karlwachs.piBeacon\")"
				line +="\nplug.executeAction(\"setTEA5767\" , props ={u"
				line +="\n	 \"outputDev\":\""+unicode(vd[u"outputDev"])+u"\""
				line +="\n	,\"device\":\"" +unicode(typeId)+u"\""
				line +="\n	,\"startAtDateTime\":\""+unicode(startAtDateTime)+u"\""
				for cc in cmds:
					line +="\n	,\""+cc+u"\":\""+unicode(cmds[cc])+u"\""
				line +="})\n"
				line+= u"##=======	end	   =====\n"
				if self.decideMyLog(u"OutputDevice"): self.indiLOG.log(10,u"\n"+line+u"\n")
			except:
				if self.decideMyLog(u"OutputDevice"): self.indiLOG.log(10,u"use this as a python script command:\n"+u"plug = indigo.server.getPlugin(\"com.karlwachs.piBeacon\")\nplug.executeAction(\"setTEA5767\" , props =(u"+
				  json.dumps({u"outputDev":vd[u"outputDev"],"device": typeId})+u" error")
			self.sendtoRPI(ip, piServerNumber, textToSend, calledFrom=u"setTEA5767CALLBACKmenu")
			vd[u"MSG"] = u" ok"
		except Exception, e:
				self.indiLOG.log(40,u"Line {} has error={}".format(sys.exc_traceback.tb_lineno, e))


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
			for xxx in [u"type",u"text",u"delayStart",u"offONTime",u"reset",u"font",u"width",u"fill",u"position",u"display"]:
				vd[xxx+dublicateTo] = vd[xxx+dublicateFrom]

			## show new ones on screen 
			vd = self.setdisplayPropsWindowCALLBACKbutton(valuesDict=vd)

		except Exception, e:
			if unicode(e) != u"None":
				self.indiLOG.log(40,u"Line {} has error={}".format(sys.exc_traceback.tb_lineno, e))
		return vd

####-------------------------------------------------------------------------####
	def setdisplayPropsWindowCALLBACKbutton(self, valuesDict=None, typeId="", devId=0):
		vd = valuesDict
		try:	fromWindow = int(vd[u"fromWindow"])
		except: return vd 
		for xx in vd:
			if u"xYAYx" in xx:
				yy = xx.split(u"xYAYx")
				if yy[1] == u"99": continue
				fromProp =	yy[0]+unicode(int(yy[1])+fromWindow)
				if fromProp in vd:
					vd[xx] = vd[fromProp]
		vd[u"windowStart"] = vd[u"fromWindow"]+u" .. to "+ unicode(int(vd[u"fromWindow"])+10)
		return vd

####-------------------------------------------------------------------------####
	def savedisplayPropsWindowCALLBACKbutton(self, valuesDict=None, typeId="", devId=0):
		vd = valuesDict
		try:	fromWindow = int(vd[u"fromWindow"])
		except: return vd 
		for xx in vd:
			if u"xYAYx" in xx:
				yy = xx.split(u"xYAYx")
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
			###if self.decideMyLog(u"OutputDevice"): self.indiLOG.log(10,u"setdisplayCALLBACKmenu: "+ unicode(vd))
			try:
				dev = indigo.devices[int(vd[u"outputDev"])]
			except:
				try:
					dev = indigo.devices[vd[u"outputDev"]]
				except:
					self.indiLOG.log(20,u"setdisplayCALLBACKmenu error outputDev not set")
					vd[u"MSG"] = u"error outputDev not set"
					return
###			   #self.indiLOG.log(20,unicode(vd))

			props = dev.pluginProps
			piServerNumber	  = props[u"address"].split(u"-")[1]
			typeId			  = u"OUTPUT-Display"
			if u"command" in vd:
				cmds = vd[u"command"]
				for iii in range(200):
					if u"%%v:" not in cmds and "%%d:" not in cmds and "%%eval:" not in cmds and "%%FtoC:" not in cmds: break
					cmds= self.convertVariableOrDeviceStateToText(self.convertVariableOrDeviceStateToText(cmds))

				if cmds .find(u"[{'") ==0: #  this will not work for json  replace ' with " as text delimiters and save any " 
					cmds = cmds.replace(u"'",u"aa123xxx123xxxaa").replace('"',"'").replace(u"aa123xxx123xxxaa",'"')

				try:
					cmds = json.loads(cmds)
				except Exception, e:
					if unicode(e) != u"None":
						self.indiLOG.log(40,u"Line {} has error={}".format(sys.exc_traceback.tb_lineno, e))
					self.indiLOG.log(40,u"setdisplayCALLBACKmenuv error in json conversion for "+unicode(cmds))
					vd[u"MSG"] = u"error in json conversion"
					return
				if self.decideMyLog(u"OutputDevice"): self.indiLOG.log(10,u" after json conversion:"+unicode(cmds)+u"\n")

				delCMDS =[]					   
				for ii in range(len(cmds)):
					cType = cmds[ii][u"type"]
					if cType == u"0" or cType == "" or \
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
								self.indiLOG.log(40,u" error in input: position= u"+  unicode(cmds[ii][u"position"]) )	 
								valuesDict[u"MSG"] = u"error in position"
					if cType =="textWformat" and u"text" in cmds[ii] and "FORMAT" in cmds[ii][u"text"]: 
						try:
							xx = cmds[ii][u"text"].split(u"FORMAT")
							cmds[ii][u"text"] = xx[1]%(float(xx[0]))
						except:
							self.indiLOG.log(40,u"setdisplayCALLBACK error in formatting: "+ unicode(cmds[ii][u"text"]))
					if cType not in[u"text",u"textWformat",u"dateString",u"image"]:
						if u"text" in cmds[ii]: del cmds[ii][u"text"]
				if len(delCMDS) >0:
					for ii in delCMDS[::-1]:
						del cmds[ii]

			else:
				###if self.decideMyLog(u"OutputDevice"): self.indiLOG.log(10,u"input:"+ unicode(vd))
				cmds =[]
				nn =-1
				for ii in range(100):
					iiS = unicode(ii)
					if u"type"+iiS not in vd: continue
					cType = vd[u"type"+iiS]
					if cType == u"0":				  continue
					if cType == "":					  continue
					if cType in [u"text",u"textWformat",u"clock",u"dateString",u"digitalClock",u"analogClock",u"date",u"NOP",u"line",u"point",u"ellipse",u"vBar",u"hBar",u"vBarwBox",u"hBarwBox",u"labelsForPreviousObject",u"rectangle",u"triangle",u"hist",u"exec",u"image",u"dot"]:
						cmds.append({})
						nn+=1
						cmds[nn][u"type"]				  = cType
						if cType ==u"analogClock":
							cmds[nn][u"hh"]	  = {}
							cmds[nn][u"mm"]	  = {}
							cmds[nn][u"ss"]	  = {}
							cmds[nn][u"ticks"] = {}
							cmds[nn][u"box"]	  = {}

						if u"text"+iiS in vd:
							cmds[nn][u"text"]			  = self.convertVariableOrDeviceStateToText(vd[u"text"+iiS])
							if cType =="textWformat" and "%%FORMAT:" in cmds[nn][u"text"]: 
								try:
									xx = cmds[nn][u"text"].split(u"%%FORMAT:")
									cmds[nn][u"text"] = xx[1]%(float(xx[0]))
								except:
									self.indiLOG.log(40,u"setdisplayCALLBACK error in formatting: "+ unicode(cmds[nn][u"text"]))
							   
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
							cmds[nn][u"box"][u"on"]		  = self.convertVariableOrDeviceStateToText(vd[u"box"+iiS])

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

						if cType not in[u"text",u"textWformat",u"dateString",u"image",u"labelsForPreviousObject"]:
							if u"text" in cmds[nn]:	 del cmds[nn][u"text"]
						if cType == u"point":
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
			intensity			= u"100" 
			showDateTime		= u"0"
			restoreAfterBoot	= False
			xwindowSize 		= u"0,0"
			xwindows			= u"off"
			zoom 				= 1.0

			if u"repeat" in vd:
				repeat = self.convertVariableOrDeviceStateToText(vd[u"repeat"])

			if u"xwindows" in vd and vd[u"xwindows"].lower() == u"on":
				if u"xwindowSize" in vd:
					xwindows	= u"ON"
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
				line = u"\n##=======use this as a python script in an action group action :=====\n"
				line +=u"plug = indigo.server.getPlugin(\"com.karlwachs.piBeacon\")"
				line +="\nplug.executeAction(\"Display\" ,	props ={"
				line +="\n     \"outputDev\":\""+unicode(vd[u"outputDev"])+u"\""
				line +="\n    ,\"device\":\"" +unicode(typeId)+u"\""
				line +="\n    ,\"restoreAfterBoot\":\""+unicode(restoreAfterBoot)+u"\""
				line +="\n    ,\"intensity\":\""+unicode(intensity)+u"\""
				line +="\n    ,\"xwindows\":\""+(xwindows)+u"\""
				line +="\n    ,\"xwindowSize\":\""+unicode(xwindowSize)+u"\""
				line +="\n    ,\"zoom\":\""+unicode(zoom)+u"\""
				line +="\n    ,\"repeat\":\""+unicode(repeat)+u"\""
				line +="\n    ,\"resetInitial\":\""+unicode(resetInitial)+u"\""
				line +="\n    ,\"scrollxy\":\""+unicode(scrollxy)+u"\""
				line +="\n    ,\"showDateTime\":\""+unicode(showDateTime)+u"\""
				line +="\n    ,\"startAtDateTime\":\""+unicode(startAtDateTime)+u"\""
				line +="\n    ,\"scrollPages\":\""+unicode(scrollPages)+u"\""
				line +="\n    ,\"scrollDelay\":\""+unicode(scrollDelay)+u"\""
				line +="\n    ,\"scrollDelayBetweenPages\":\""+unicode(scrollDelayBetweenPages)+u"\""
				line +="\n    ,\"command\":'['+\n     '"

				### this will create list of dicts, one per command, remove blank items, sort  ,.. 
				doList =[u"type",u"position",u"width",u"fill",u"font",u"text",u"offONTime",u"display",u"reset",u"labelsForPreviousObject"] # sorted by this
				noFont =[u"NOP",u"line",u"point",u"ellipse",u"vBar",u"hBar",u"vBarwBox",u"hBarwBox",u"rectangle",u"triangle",u"hist",u"exec",u"image",u"dot"]
				for cc in range(len(cmds)):
					delItem=[]
					if len(cmds[cc]) > 0:
						line += u"{"
						for item in doList:
							if item in cmds[cc]:
								if cmds[cc][item] !="" and not ( item ==u"font" and cmds[cc][u"type"] in noFont) :
									line +='"'+item+'":'+json.dumps(cmds[cc][item]).strip(u" ")+u", "
								else:# this is blank
									delItem.append(item)
		  
						for item in cmds[cc]: # this is for the others not listed in the sort List
							if item in doList: continue
							if cmds[cc][item] != "":
								line += u'"'+item+u'":'+json.dumps(cmds[cc][item]).strip(u" ")+u", "
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
				line += u"##=======   end  =====\n"

				if self.decideMyLog(u"OutputDevice"): self.indiLOG.log(10,u"\n"+line+u"\n")
				vd[u"MSG"] = u" ok"

			except Exception, e:
				if unicode(e) != u"None":
					self.indiLOG.log(40,u"Line {} has error={}".format(sys.exc_traceback.tb_lineno, e))
					vd[u"MSG"] = u"error"
			jData = {u"device": typeId,  "restoreAfterBoot": False, u"intensity":intensity, u"zoom":zoom,"repeat":repeat,"resetInitial":resetInitial,"startAtDateTime":startAtDateTime,
				u"scrollxy":scrollxy, u"showDateTime":showDateTime,"scrollPages":scrollPages,"scrollDelay":scrollDelay,"scrollDelayBetweenPages":scrollDelayBetweenPages,
				u"command": cmds}
			if xwindows.lower() == u"on" and xwindowSize !="0,0":
				jData[u"xwindows"] = xwindows
				jData[u"xwindowSize"] = xwindowSize
			textToSend = json.dumps([jData])
			self.sendtoRPI(ip, piServerNumber, textToSend, calledFrom=u"setdisplayCALLBACKmenu")

		except Exception, e:
			if unicode(e) != u"None":
				self.indiLOG.log(40,u"Line {} has error={}".format(sys.exc_traceback.tb_lineno, e))
				self.indiLOG.log(40,u"error display check "+unicode(vd))
				valuesDict[u"MSG"] = u"error in parameters"
		return vd


	def setupListDisplay(self,theDict,tType,lenItem=0,default=""):
		try:
			ret = default
			if tType in theDict:
				ret = self.convertVariableOrDeviceStateToText(theDict[tType])
				if len(ret) > 0: 
					if u"," in ret:
						ret	 =	self.addBrackets(ret,cType=lenItem)
					else:
						ret = int(ret)
		except Exception, e:
			if unicode(e) != u"None":
				self.indiLOG.log(40,u"Line {} has error={}".format(sys.exc_traceback.tb_lineno, e))
		return ret
####-------------------------------------------------------------------------####
	def addBrackets(self,pos,cType="",default=[]):
		try:
			test = unicode(pos).strip(u",")

			if len(test) ==0: return default
			if cType == u"point":
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
			test = test.split(u",")	 
			pp = []
			for t in test:
					try:	x = int(float(t))
					except: x = t
					pp.append(x)
			if nItems !=-1 and nItems != len(pp):
				self.indiLOG.log(20,u"addBrackets error in input: pos= {}; wrong number of coordinates, should be: {}".format(pos, nItems) )

			return pp
		except Exception, e:
			if unicode(e) != u"None":
				self.indiLOG.log(40,u"Line {} has error={}".format(sys.exc_traceback.tb_lineno, e))
			self.indiLOG.log(40,u"addBrackets error in input: cType:{};  default= {};  pos= {}".format(cType, default, pos) )	 
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
					self.indiLOG.log(40,u"error outputDev not set")
					vd[u"MSG"] = u"error outputDev not set"
					return vd
###			   #self.indiLOG.log(20,unicode(vd))

			props = dev.pluginProps
			piServerNumber	  = props[u"address"].split(u"-")[1]
			typeId			  = u"OUTPUT-neopixel"
			lightON = False
			maxRGB	= 0
			if u"command" in vd:
				cmds = vd[u"command"]
				for iii in range(200):
					if u"%%v:" not in cmds and "%%d:" not in cmds: break
					cmds= self.convertVariableOrDeviceStateToText(cmds)
				if self.decideMyLog(u"OutputDevice"): self.indiLOG.log(10,u"input:\n"+ unicode(vd[u"command"])+u"\n result:\n"+unicode(cmds)+u"\n")

				if cmds .find(u"[{'") ==0: #  this will not work for json  replace ' with " as text delimiters and save any " 
					cmds = cmds.replace(u"'",u"aa123xxx123xxxaa").replace('"',"'").replace(u"aa123xxx123xxxaa",'"')

				try:
					cmds = json.loads(cmds)
				except Exception, e:
					if unicode(e) != u"None":
						self.indiLOG.log(40,u"Line {} has error={}".format(sys.exc_traceback.tb_lineno, e))
					self.indiLOG.log(40,u"error in json conversion for "+unicode(cmds))
					vd[u"MSG"] = u"error in json conversion"
					return
				if self.decideMyLog(u"OutputDevice"): self.indiLOG.log(10,u" after json conversion:\n"+unicode(cmds)+u"\n")

				for ii in range(len(cmds)):
					cType = cmds[ii][u"type"]
					if u"position" in cmds[ii]:
							cmds, xx, ok = self.makeACompleteList(u"position", cmds[ii],cmds,ii,ii)
							if not ok: return vd 
					if not (cType == u"image"):
						if u"text" in cmds[ii]: del cmds[ii][u"text"]

			else:
				cmds =[]
				nn =-1
				for ii in range(100):
					iiC= unicode(ii)
					if u"type"+unicode(ii) not in vd: continue
					cType = vd[u"type"+iiC]
					if cType == u"0":				  continue
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

						if	cType != u"image" :
							if u"text" in cmds[nn]:	 del cmds[nn][u"text"]

					elif cType ==u"thermometer":
						if u"startPixelx"+iiC in vd and "endPixelx"+iiC in vd and "startPixelRGB"+iiC in vd and "endPixelRGB"+iiC in vd and "deltaColorSteps"+iiC in vd:
							cmds.append({})
							nn+=1
							cmds[nn][u"type"]				  = u"points"
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
							if self.decideMyLog(u"OutputDevice"):self.indiLOG.log(20,u";  startPixelx:"+unicode(startPixelx) +u";  endPixelx:"+unicode(endPixelx) +u";  startPixelRGB:"+unicode(startPixelRGB)+u";   endPixelRGB:"+unicode(endPixelRGB) +u";   deltaColorSteps:"+unicode(deltaColorSteps)	 ) 
							nsteps	   =  max(0,abs(endPixelx - startPixelx))
							deltaC	   =  [endPixelRGB[ll] - startPixelRGB[ll] for ll in range(3)]
							deltaCabs  =  map(abs, deltaC)
							deltaCN	   =  sum(deltaCabs)
							stepSize   =  float(deltaCN)/ max(1,nsteps)	 
							stepSizeSign   =  [cmp(deltaC[0],0),cmp(deltaC[1],0),cmp(deltaC[2],0)] 
							if self.decideMyLog(u"OutputDevice"):self.indiLOG.log(20,u";  nsteps:"+unicode(nsteps) +u";  deltaC:"+unicode(deltaC) +u";  deltaCabs:"+unicode(deltaCabs) +u";  deltaCN:"+unicode(deltaCN) +u";  stepSize:"+unicode(stepSize)+u";  stepSizeSign:"+unicode(stepSizeSign) ) 
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
							if self.decideMyLog(u"OutputDevice"):self.indiLOG.log(20,unicode(pos)) 
							cmds[nn][u"position"] = pos
						else:
							vd[u"MSG"] = u"error in type"
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
			intensity = u"100" 
			showDateTime = u"0"
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
				line = u"\n##=======use this as a python script in an action group action :=====\n"
				line +="plug = indigo.server.getPlugin(\"com.karlwachs.piBeacon\")"
				line +="\nplug.executeAction(\"Neopixel\" , props ={u"
				line +="\n     \"outputDev\":\""+unicode(vd[u"outputDev"])+u"\""
				line +="\n    ,\"device\":\"" +unicode(typeId)+u"\""
				line +="\n    ,\"restoreAfterBoot\":"+unicode(restoreAfterBoot)
				line +="\n    ,\"intensity\":"+unicode(intensity)
				line +="\n    ,\"repeat\":"+unicode(repeat)
				line +="\n    ,\"resetInitial\":\""+unicode(resetInitial)+u"\""
				line +="\n    ,\"command\":'['+\n     '"
				for cc in cmds:
					line+=json.dumps(cc)+u"'+\n    ',"
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
				line+= u"##=======   end   =====\n"
				if self.decideMyLog(u"OutputDevice"): self.indiLOG.log(10,u"\n"+line+u"\n")
			except Exception, e:
				if unicode(e) != u"None":
					self.indiLOG.log(40,u"Line {} has error={}".format(sys.exc_traceback.tb_lineno, e))
				if self.decideMyLog(u"OutputDevice"): self.indiLOG.log(40,u"use this as a ppython script command:\n"+u"plug = indigo.server.getPlugin(\"com.karlwachs.piBeacon\")\nplug.executeAction(\"Neopixel\" , props ="+
				  (json.dumps({u"outputDev":vd[u"outputDev"],"device": typeId, "restoreAfterBoot": False, u"intensity":intensity,"repeat":repeat,"resetInitial":resetInitial})).strip(u"}").replace(u"false",u"False").replace(u"true",u"True")+u"\n,\"command\":'"+json.dumps(cmds) +u"'})"+u"\n")
				self.indiLOG.log(20,u"vd: "+unicode(vd))

			chList= []
			if u"writeOutputToState" not in props or (u"writeOutputToState" in props and props[u"writeOutputToState"] == u"1"):
				chList.append({u"key":u"OUTPUT",u"value": unicode(cmds).replace(u" ","")})
			chList.append({u"key":u"status",u"value": round(maxRGB/2.55)})
			self.execUpdateStatesList(dev,chList)
			if lightON:
				dev.updateStateImageOnServer(indigo.kStateImageSel.PowerOn)
			else:
				dev.updateStateImageOnServer(indigo.kStateImageSel.PowerOff)

			self.sendtoRPI(ip, piServerNumber, textToSend, calledFrom=u"setneopixelCALLBACKmenu")
			vd[u"MSG"] = u" ok"

		except Exception, e:
			if unicode(e) != u"None":
				self.indiLOG.log(40,u"Line {} has error={}".format(sys.exc_traceback.tb_lineno, e))
				self.indiLOG.log(40,u"error display check "+unicode(vd))
				valuesDict[u"MSG"] = u"error in parameters"
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
			if self.decideMyLog(u"OutputDevice"): self.indiLOG.log(10,u"setdisplayCALLBACKmenu: "+ unicode(vd))
			try:
				dev = indigo.devices[int(vd[u"outputDev"])]
			except:
				try:
					dev = indigo.devices[vd[u"outputDev"]]
				except:
					self.indiLOG.log(40,u"error outputDev not set")
					vd[u"MSG"] = u"error outputDev not set"
					return
###			   #self.indiLOG.log(20,unicode(vd))

			props = dev.pluginProps
			piServerNumber	  = props[u"address"].split(u"-")[1]
			typeId			  = u"setStepperMotor"
			if u"command" in vd:
				cmds = vd[u"command"]
				for iii in range(200):
					if u"%%v:" not in cmds and "%%d:" not in cmds: break
					cmds= self.convertVariableOrDeviceStateToText(self.convertVariableOrDeviceStateToText(cmds))
				if self.decideMyLog(u"OutputDevice"): self.indiLOG.log(10,u"input:"+ unicode(vd[u"command"])+u" result:"+unicode(cmds)+u"\n")

				try:
					cmds = json.loads(cmds)
				except Exception, e:
					if unicode(e) != u"None":
						self.indiLOG.log(40,u"Line {} has error={}".format(sys.exc_traceback.tb_lineno, e))
					self.indiLOG.log(40,u"error in json conversion for "+unicode(cmds))
					vd[u"MSG"] = u"error in json conversion"
					return
				if self.decideMyLog(u"OutputDevice"): self.indiLOG.log(10,u" after json conversion:"+unicode(cmds)+u"\n")


			else:
				###if self.decideMyLog(u"OutputDevice"): self.indiLOG.log(10,u"input:"+ unicode(vd))
				cmds =[]
				nn =-1
				for ii in range(100):
						iiS = unicode(ii)
						if u"cmd-"+iiS in vd:
							cmds.append({}); nn+=1
							if  vd[u"cmd-"+iiS] =="steps":
								if u"steps-"+iiS in vd:		
									try:  cmds[nn][u"steps"] 		= int(vd[u"steps-"+iiS])
									except: cmds[nn][u"steps"] 		= 0

								if u"waitBefore-"+iiS in vd:	
									try: cmds[nn][u"waitBefore"]		= float(vd[u"waitBefore-"+iiS])
									except: cmds[nn][u"waitBefore"]	= 0

								if u"waitAfter-"+iiS in vd:	
									try: cmds[nn][u"waitAfter"]		= float(vd[u"waitAfter-"+iiS])
									except: cmds[nn][u"waitAfter"]	= 0

								if u"stayOn-"+iiS in vd:	
									try: cmds[nn][u"stayOn"]		= int(vd[u"stayOn-"+iiS])
									except: cmds[nn][u"stayOn"] 		= 1

								if u"dir-"+iiS in vd:	
									try: cmds[nn][u"dir"]			= int(vd[u"dir-"+iiS])
									except: cmds[nn][u"dir"] 		= 1

								if u"GPIO.0-"+iiS in vd:
									try: cmds[nn][u"GPIO.0"]		= int(vd[u"GPIO.0-"+iiS])
									except: pass

								if u"GPIO.1-"+iiS in vd:
									try: cmds[nn][u"GPIO.1"]		= int(vd[u"GPIO.1-"+iiS])
									except: pass

								if u"GPIO.2-"+iiS in vd:
									try: cmds[nn][u"GPIO.2"]		= int(vd[u"GPIO.2-"+iiS])
									except: pass

							elif vd[u"cmd-"+iiS] == u"sleepMotor":
								cmds[nn][u"sleepMotor"] 			= 1
								if u"waitBefore-"+iiS in vd:	
									try: cmds[nn][u"waitBefore"]		= float(vd[u"waitBefore-"+iiS])
									except: cmds[nn][u"waitBefore"] 	= 0
								if u"waitAfter-"+iiS in vd:	
									try: cmds[nn][u"waitAfter"]		= float(vd[u"waitAfter-"+iiS])
									except: cmds[nn][u"waitAfter"] 	= 0


							elif vd[u"cmd-"+iiS] == u"wakeMotor":
								cmds[nn][u"wakeMotor"] 			= 1
								if u"waitBefore-"+iiS in vd:	
									try: cmds[nn][u"waitBefore"]		= float(vd[u"waitBefore-"+iiS])
									except: cmds[nn][u"waitBefore"] 	= 0
								if u"waitAfter-"+iiS in vd:	
									try: cmds[nn][u"waitAfter"]		= float(vd[u"waitAfter-"+iiS])
									except: cmds[nn][u"waitAfter"] 	= 0

							elif vd[u"cmd-"+iiS] == u"offMotor":
								cmds[nn][u"offMotor"] 				= 1
								if u"waitBefore-"+iiS in vd:	
									try: cmds[nn][u"waitBefore"]		= float(vd[u"waitBefore-"+iiS])
									except: cmds[nn][u"waitBefore"] 	= 0
								if u"waitAfter-"+iiS in vd:	
									try: cmds[nn][u"waitAfter"]		= float(vd[u"waitAfter-"+iiS])
									except: cmds[nn][u"waitAfter"] 	= 0

							elif vd[u"cmd-"+iiS] == u"onMotor":
								cmds[nn][u"onMotor"] 				= 1
								if u"waitBefore-"+iiS in vd:	
									try: cmds[nn][u"waitBefore"]		= float(vd[u"waitBefore-"+iiS])
									except: cmds[nn][u"waitBefore"] 	= 0
								if u"waitAfter-"+iiS in vd:	
									try: cmds[nn][u"waitAfter"]		= float(vd[u"waitAfter-"+iiS])
									except: cmds[nn][u"waitAfter"] 	= 0


							elif vd[u"cmd-"+iiS] == u"wait":
								cmds[nn][u"wait"] 					= int(vd[u"wait-"+iiS])
	
							if cmds[nn] == {}: del cmds[-1]

				#self.indiLOG.log(20,	unicode(vd))
			ip = self.RPI[piServerNumber][u"ipNumberPi"]

			startAtDateTime = 0
			if u"startAtDateTime" in valuesDict:
				startAtDateTime = self.setDelay(startAtDateTimeIN=self.convertVariableOrDeviceStateToText(vd[u"startAtDateTime"]))

			repeat				= 1
			if u"repeat" in vd:
				repeat = self.convertVariableOrDeviceStateToText(vd[u"repeat"])

			waitForLast				= u"1"
			if u"waitForLast" in vd:
				waitForLast = self.convertVariableOrDeviceStateToText(vd[u"waitForLast"])

			try:
				line = u"\n##=======use this as a python script in an action group action :=====\n"
				line +=u"plug = indigo.server.getPlugin(\"com.karlwachs.piBeacon\")"
				line +=u"\nplug.executeAction(\"StepperMotor\" ,	props ={"
				line +=u"\n     \"outputDev\":\""+unicode(vd[u"outputDev"])+u"\""
				line +=u"\n    ,\"device\":\"" +unicode(typeId)+u"\""
				line +=u"\n    ,\"dev.id\":\"" +unicode(dev.id)+u"\""
				line +=u"\n    ,\"repeat\":\""+unicode(repeat)+u"\""
				line +=u"\n    ,\"waitForLast\":\""+unicode(waitForLast)+u"\""
				line +=u"\n    ,\"command\":'['+\n     '"

				### this will create list of dicts, one per command, remove blank items, sort  ,.. 
				doList =[u"steps", u"sleepMotor",  u"offMotor", u"wait", u"stayON", u"waitBefore", u"waitAfter", u"dir", u"GPIO.0", u"GPIO.1", u"GPIO.2"] # sorted by this
				for cc in range(len(cmds)):
					delItem=[]
					if len(cmds[cc]) > 0:
						line +=u"{"
						for item in doList:
							if item in cmds[cc]:
								if cmds[cc][item] !="" :
									line +=u'"'+item+u'":'+json.dumps(cmds[cc][item]).strip(u" ")+u", "
								else:# this is blank
									delItem.append(item)
		  
						## remove blanks 
						for item in delItem: 
							del cmds[cc][item]
						# close line 
						line  = line.strip(u", ") + u"}'+\n    ',"

				## finish cmd lines
				line  = line.strip(u"'+\n        ',")	+ u"]'\n	 })\n"
				## end of output
				line += u"##=======   end   =====\n"

				if self.decideMyLog(u"OutputDevice"): self.indiLOG.log(10,u"\n"+line+u"\n")
				vd[u"MSG"] = u" ok"

			except Exception, e:
				if unicode(e) != u"None":
					self.indiLOG.log(40,u"Line {} has error={}".format(sys.exc_traceback.tb_lineno, e))
					vd[u"MSG"] = u"error"
			textToSend = json.dumps([{u"device": typeId, u"repeat":repeat, u"waitForLast":waitForLast,u"dev.id":dev.id, u"startAtDateTime":startAtDateTime, u"command": cmds}])
			self.sendtoRPI(ip, piServerNumber, textToSend, calledFrom=u"setStepperMotorCALLBACKmenu")

		except Exception, e:
			if unicode(e) != u"None":
				self.indiLOG.log(40,u"Line {} has error={}".format(sys.exc_traceback.tb_lineno, e))
				self.indiLOG.log(40,u"error stepperMotor check "+unicode(vd))
				valuesDict[u"MSG"] = u"error in parameters"
		return vd



####-------------------------------------------------------------------------####
	def makeACompleteList(self,item, vd,cmds=[],nn="",ii=""):
		try:
			if item+unicode(ii) in vd:
				xxx				 = unicode(self.convertVariableOrDeviceStateToText(unicode(vd[item+unicode(ii)])))
				if xxx =="": return cmds, vd, True
				if xxx[0]  !=u"[": xxx = u"["+xxx
				if xxx[-1] !=u"]": xxx =xxx+ u"]"
				try:
					if cmds ==[]:
						cmds			 = json.loads(xxx)
					else:
						cmds[nn][item]	 = json.loads(xxx)
					return cmds, vd, True
				except Exception, e:
					self.indiLOG.log(40,u"Line {} has error={}".format(sys.exc_traceback.tb_lineno, e))
					self.indiLOG.log(40,u" error in input: "+item+u" ii="+unicode(ii)+u" nn="+unicode(nn)+ " cmds="+	 unicode(cmds) + " xxx="+  unicode(xxx))
					vd[u"MSG"] = u"error in parameter"
				return cmds,vd, False
		except Exception, e:
			if unicode(e) != u"None":
				self.indiLOG.log(40,u"Line {} has error={}".format(sys.exc_traceback.tb_lineno, e))
				self.indiLOG.log(40,u"item " +unicode(item)+unicode(ii)+u"  , vd "+unicode(vd))
			return cmds,vd, False
		return cmds,vd, True



####-------------------------------------------------------------------------####
	def sendFileToRPIviaSocket(self,ip, piU, fileName,fileContents,fileMode="w",touchFile=True):
		try: 
			out= (json.dumps([{u"command":"file",u"fileName":fileName,"fileContents":fileContents,"fileMode":fileMode,"touchFile":touchFile}]))
			if self.decideMyLog(u"OutputDevice"): self.indiLOG.log(10,	u"sending file to  "+ip+u";  "+ out )
			self.sendtoRPI(ip, piU, out, calledFrom=u"sendFileToRPIviaSocket")
		except Exception, e:
				self.indiLOG.log(40,u"Line {} has error={}".format(sys.exc_traceback.tb_lineno, e))
		return




####-------------------------------------------------------------------------####
	def presendtoRPI(self, piU, out):
		retC = 0
		if piU == u"999":
			for piU in self.RPI:
				if self.RPI[piU][u"ipNumberPi"] == "":	 continue
				if self.RPI[piU][u"piOnOff"]	== "":	 continue
				if self.RPI[piU][u"piOnOff"]	== u"0": continue
				retC = max(retC, self.sendtoRPI(self.RPI[piU][u"ipNumberPi"], piU, out , calledFrom=u"presendtoRPI 1") )
		else:
			if self.RPI[piU][u"piOnOff"]	== "":	 return	 2
			if self.RPI[piU][u"piOnOff"]	== u"0": return	 2
			if self.RPI[piU][u"ipNumberPi"] == "":	 return	 2
			retC = self.sendtoRPI(self.RPI[piU][u"ipNumberPi"], piU, out, calledFrom=u"presendtoRPI 2")

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
					self.indiLOG.log(20,u"sendtoRPI sending to pi# {}  {} skipped due to recent failure count, reset by dis-enable & enable rPi ;  command-string={};  calledFrom:{}".format(piU, ip, theString, calledFrom) )
					return -1

			if self.decideMyLog(u"OutputDevice") or self.decideMyLog(u"SocketRPI"): self.indiLOG.log(10,u"sendtoRPI sending to  {} {} command-string={};  calledFrom:{}".format(piU, ip, theString, calledFrom) )
				# Create a socket (SOCK_STREAM means a TCP socket)
			sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
			sock.settimeout(3.)
			try:
					# Connect to server and send data
					sock.connect((ip, int(self.rPiCommandPORT)))
					sock.sendall(theString + "\n")
			except Exception, e:
					if unicode(e) != u"None":
						if	time.time() > self.currentlyBooting:  # NO MSG IF RPIS ARE BOOTING
							if time.time() - self.RPIBusy[piU]  > 20: # supress warning if we just updated the RPI
								self.indiLOG.log(20,u"socket-send not working,  rPi:{} {} is currently updating, delaying send".format(piU, ip) )
							else:
								if unicode(e).find(u"onnection refused") ==-1:
									self.indiLOG.log(30,u"error in socket-send to rPi:{} {}  cmd= {}...{}".format(piU, ip, theString[0:30],theString[-30:]) )
								else:
									self.indiLOG.log(30,u"error in socket-send to rPi:{} {}, connection refused, rebooting/restarting RPI?".format(piU, ip) )
							self.checkIPSendSocketOk[ip][u"count"] += 1 
							self.checkIPSendSocketOk[ip][u"time"]	= time.time()
						try:	sock.close()
						except: pass
						return -1
			finally:
					sock.close()
		except Exception, e:
			if unicode(e) != u"None":
				if	time.time() > self.currentlyBooting: # NO MSG IF RPIS ARE BOOTING
					if unicode(e).find(u"onnection refused") ==-1:
						self.indiLOG.log(40,u"error in socket-send to rPi:{} {}  cmd= {}..{}".format(piU, ip, theString[0:30],theString[-30:]) )
						self.indiLOG.log(40,u"Line {} has error={}".format(sys.exc_traceback.tb_lineno, e))
					else:
						self.indiLOG.log(30,u"error in socket-send to rPi:{} (), connection refused,  rebooting/restarting RPI?".format(piU, ip) )
					self.checkIPSendSocketOk[ip][u"count"] += 1 
					self.checkIPSendSocketOk[ip][u"time"]   = -time.time()
				try:	sock.close()
				except: pass
				return -1
		self.checkIPSendSocketOk[ip][u"count"] = 0 
		self.checkIPSendSocketOk[ip][u"time"]  = time.time()
		return 0


####-------------------------------------------------------------------------####
	def playSoundFileCALLBACKmenu(self, valuesDict=None, typeId="", devId=0):
		try:
			valuesDict[u"typeId"]		 = u"playSound"
			valuesDict[u"cmd"]			 = u"playSound"
			self.setPin(valuesDict)
		except Exception, e:
			if unicode(e) != u"None":
				self.indiLOG.log(40,u"Line {} has error={}".format(sys.exc_traceback.tb_lineno, e))
			return valuesDict
		return valuesDict

####-------------------------------------------------------------------------####
	def restartPluginCALLBACKaction(self, action1=None, typeId="", devId=0):
		self.quitNow		= u"Internal restart requested, ignore indigo warning message >>piBeacon Error ..."
		return


####-------------------------------------------------------------------------####
	def restartPluginCALLBACKmenu(self, valuesDict=None, typeId="", devId=0):
		self.quitNow		 = u"Internal restart requested, ignore indigo warning message >>piBeacon Error ..."
		valuesDict[u"MSG"]	 = u"internal restart underway, exit menu"
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
				devId = int(valuesDict[u"devIdOfBeacon"])		
				return  self.getBeaconParametersCALLBACKmenu( valuesDict=valuesDict, devId=devId, force=True )
		except Exception, e:
			if unicode(e) != u"None":
				self.indiLOG.log(40,u"Line {} has error={}".format(sys.exc_traceback.tb_lineno, e))
		return valuesDict

####-------------------------------------------------------------------------####
	def getBeaconParametersCALLBACKmenu(self, valuesDict=None, typeId="", devId=0, force=True):
		
		try:
			# must be enabled in config 
			if not force and self.checkBeaconParametersDisabled: return 

			if self.decideMyLog(u"BatteryLevel"): self.indiLOG.log(20,u"getBeaconParameters requesting update for beacon devId:{}".format(devId)) 

			devices = {}

			if  valuesDict is None: 
				self.indiLOG.log(20,u"getBeaconParameters no data input") 
				return  valuesDict

			# check if it is all beacons
			beacon = ""
			if devId != 0: 
				try: 
					beaconDev = indigo.devices[devId]
					beacon    =  beaconDev.address
				except:
					# all beacons and rpi
					valuesDict[u"piServerNumber"]  = u"all"


			if u"piServerNumber" not in  valuesDict:   
				self.indiLOG.log(20,u"getBeaconParameters piServerNumber not defined") 
				return  valuesDict

			if valuesDict[u"piServerNumber"]  == u"-1": 
				valuesDict[u"piServerNumber"]  = u"all"

			# check if anythinges beside "all or a number, if so: set to all"
			if valuesDict[u"piServerNumber"]  != u"all":
				try: 	int(valuesDict[u"piServerNumber"])
				except: valuesDict[u"piServerNumber"]  = u"all"


			# make list of devicesper RPI
			for piU in _rpiBeaconList:
				if valuesDict[u"piServerNumber"] == piU or valuesDict[u"piServerNumber"] == u"all" or valuesDict[u"piServerNumber"] == u"999":
					devices[piU] = {} 

			# thsi is for timeouts for rpis 
			minTime ={}
			for piU2 in _rpiList:
				minTime[piU2] = 0 

			for dev in indigo.devices.iter(u"props.isBeaconDevice"):
				props = dev.pluginProps
				if u"status" not in dev.states: continue
				if dev.states[u"status"] !="up": continue
				if beacon != "" and (dev.address != beacon or devId != dev.id): continue
				if valuesDict[u"piServerNumber"] == u"all" or valuesDict[u"piServerNumber"] == u"999":
					piU = str(dev.states[u"closestRPI"])
				else:
					piU = valuesDict[u"piServerNumber"]

				# just a double check
				if piU not in _rpiBeaconList: continue

				
				mac  = dev.address
				dd = {}
				typeOfBeacon = self.beacons[mac][u"typeOfBeacon"]
				if typeOfBeacon !="":
					#if "SupportsBatteryLevel" not in props: 							 continue
					#if not  props[u"SupportsBatteryLevel"]:  							 continue
					if typeOfBeacon not in self.knownBeaconTags: 						 continue
					if type(self.knownBeaconTags[typeOfBeacon][u"battCmd"]) != type({}): continue
					if u"uuid" not in self.knownBeaconTags[typeOfBeacon][u"battCmd"]: 	 continue
					if u"bits" not in self.knownBeaconTags[typeOfBeacon][u"battCmd"]: 	 continue
					if u"shift" not in self.knownBeaconTags[typeOfBeacon][u"battCmd"]: 	 continue
					#if self.decideMyLog(u"BatteryLevel"): self.indiLOG.log(20,u"getBeaconParameters checking beacon: {:30s};".format(dev.name) )

					# check if we should do battery time check at this hour, some beacons beep (nutale) if battery level is checked
					if not force and "batteryLevelCheckhours" in props:
						hh = (datetime.datetime.now()).hour
						batteryLevelCheckhours =  props[u"batteryLevelCheckhours"].split(u"/")
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
					#if self.decideMyLog(u"BatteryLevel"): self.indiLOG.log(20,u"getBeaconParameters pass 1" )
					
					if u"batteryLevelUUID" in props  and props[u"batteryLevelUUID"]  == u"gatttool":
						try: 	batteryLevelLastUpdate = self.getTimetimeFromDateString(dev.states[u"batteryLevelLastUpdate"])
						except: batteryLevelLastUpdate = 0
						try: 	batteryLevel = int(dev.states[u"batteryLevel"])
						except: batteryLevel = 0

						#if self.decideMyLog(u"BatteryLevel"): self.indiLOG.log(20,u"getBeaconParameters pass 2" )
						if force or batteryLevel < 20  or (time.time() - batteryLevelLastUpdate) > (3600*17): # if successful today and battery level > 20% dont need to redo it again
							#if self.decideMyLog(u"BatteryLevel"): self.indiLOG.log(20,u"getBeaconParameters pass 3" )
							try: 
								dist = float( dev.states[u"Pi_{:02d}_Distance".format(int(piU))] )
								if dist < 99.:
									dd = {u"battCmd":self.knownBeaconTags[typeOfBeacon][u"battCmd"]}
									minTime[piU] += 10
									self.beacons[mac][u"lastBusy"] = time.time() + 90
									dev.updateStateOnServer(u"isBeepable",u"busy")
									if self.decideMyLog(u"BatteryLevel"): self.indiLOG.log(20,u"getBeaconParameters requesting update from RPI:{:2s} for beacon: {:30s}; lastV: {:3d}; last successful check @: {}; distance to RPI:{:4.1f}; cmd:{}".format(piU, dev.name, dev.states[u"batteryLevel"], dev.states[u"batteryLevelLastUpdate"], dist, dd) )

								elif force: # if successful today and battery level > 30% dont need to redo it again
									 self.indiLOG.log(30,u"Battery level update outdated  for beacon: {:30s}; not doable on requested pi#{}, not visible on that pi".format(dev.name, piU ) )

								if (time.time() - batteryLevelLastUpdate) > (3600*24*3): # error message if last update > 3 days ago
									 self.indiLOG.log(30,u"Battery level update outdated  for beacon: {:30s}; lastV: {:3d}; last successful check @: {}".format(dev.name, dev.states[u"batteryLevel"], dev.states[u"batteryLevelLastUpdate"] ) )
							except Exception, e:
								self.indiLOG.log(40,u"Line {} has error={}".format(sys.exc_traceback.tb_lineno, e))

						else:
							if self.decideMyLog(u"BatteryLevel"): self.indiLOG.log(20,u"getBeaconParameters no update needed              for beacon: {:30s}; lastV: {:3d}; last successful check @: {}".format(dev.name, dev.states[u"batteryLevel"], dev.states[u"batteryLevelLastUpdate"] ) )
					

				# this is the list of beacons for THIS RPI
				if dd !={}:
					devices[piU][dev.address] = dd

			minTime    = max(list(minTime.values()))
			nDownAddWait = True
			nothingFor = []
			countB = 0
			countP = 0
			for piU2 in devices:
					if devices[piU2] == {}: 
						if valuesDict[u"piServerNumber"] == u"all" or valuesDict[u"piServerNumber"] == u"999":
							nothingFor.append(int(piU2))
					else:
						xx						= {}
						xx[u"cmd"]		 		= u"getBeaconParameters"
						xx[u"typeId"]			= json.dumps(devices[piU2])
						xx[u"piServerNumber"]	= piU2
						countB += len(devices[piU2])
						countP += 1
						if self.decideMyLog(u"BatteryLevel"): self.indiLOG.log(20,u"getBeaconParameters request list for pi{};  {}".format(piU2, xx) )

						if nDownAddWait: self.setCurrentlyBooting(minTime+10, setBy=u"getBeaconParameters (batteryLevel ..)")
						nDownAddWait = False
						self.setPin(xx)

			if nothingFor != "": 
				if self.decideMyLog(u"BatteryLevel"): self.indiLOG.log(20,u"getBeaconParameters no active/requested beacons on rpi# {}".format(sorted(nothingFor)) )
			valuesDict[u"MSG"]  = u"get BatL {} beacons on {} Pi".format(countB,countP)
			valuesDict[u"MSG2"]  = u""

		except Exception, e:
			if unicode(e) != u"None":
				self.indiLOG.log(40,u"Line {} has error={}".format(sys.exc_traceback.tb_lineno, e))

		return valuesDict


####-------------------------------------------------------------------------####
	def makeBatteryLevelReportCALLBACKmenu(self, valuesDict=None, typeId="", devId=0, force=True):
		try:
			out =u"battery level report:\n Dev---------------------------------------    MAC#               Beacon-Type           Status   ClosestRPI      BeepCommand BatteryLevel Last Sucessful Update"
			for dev in indigo.devices.iter(u"props.isBeaconDevice"):
				piU = str(dev.states[u"closestRPI"])
				mac  = dev.address
				typeOfBeacon = self.beacons[mac][u"typeOfBeacon"]

				batlevel  = u"         off"
				if typeOfBeacon in self.knownBeaconTags:
					if self.knownBeaconTags[typeOfBeacon][u"battCmd"] != u"off":
						if u"batteryLevel" in dev.states:
							batlevel = u"{:12d}".format(dev.states[u"batteryLevel"])

				benabled = u"not capable"
				try: 	benabled = dev.states[u"isBeepable"]
				except:	pass

				lastU = u"xxx"
				try:
					if dev.enabled:
						lastU = dev.states[u"batteryLevelLastUpdate"]
					else:
						lastU = u"disabled"
				except: pass

				out += u"\n{:45s}  {:18s} {:20s}  {:15s}  {:6d}  {:11s} {:12s} {} ".format( dev.name, mac, typeOfBeacon, dev.states[u"status"], int(piU), benabled, batlevel, lastU)
			indigo.server.log(out)
			valuesDict[u"MSG2"]  = u"bat report in std indigo log"
			valuesDict[u"MSG"]   = u""
		except Exception, e:
			if unicode(e) != u"None":
				self.indiLOG.log(40,u"Line {} has error={}".format(sys.exc_traceback.tb_lineno, e))

		return valuesDict



####-------------------------------------------------------------------------####
	def sendBeepCommandCALLBACKaction(self, action1=None, typeId="", devId=0):
		return self.sendBeepCommandCALLBACKmenu(action1.props)

####-------------------------------------------------------------------------####
	def sendBeepCommandCALLBACKmenu(self, valuesDict=None, typeId="", devId=0, force=True):
		
		if  valuesDict is None: return  valuesDict
		if self.decideMyLog(u"Beep"): self.indiLOG.log(20,u"beep beacon {}".format(valuesDict) )

		if u"selectbeaconForBeep" not in  valuesDict: return  valuesDict
		dev = indigo.devices[int(valuesDict[u"selectbeaconForBeep"])]
		props = dev.pluginProps
		if dev.states[u"status"] !="up": return valuesDict

		if u"piServerNumber" not in valuesDict: return valuesDict
		try:  	int(valuesDict[u"piServerNumber"])
		except:	valuesDict[u"piServerNumber"] = u"-1"

		if valuesDict[u"piServerNumber"] != u"-1":
			piU= valuesDict[u"piServerNumber"]
		else:
			piU = str(dev.states[u"closestRPI"])

		if piU not in _rpiBeaconList: return valuesDict
		if u"mustBeUp" in valuesDict and valuesDict[u"mustBeUp"] == u"1":
			mustBeUp = True
		else:
			mustBeUp = False


		beacon  = dev.address
		if  time.time() - self.beacons[beacon][u"lastBusy"] < 0:
			if self.decideMyLog(u"Beep"): 
				self.indiLOG.log(20,u"beep beacon requested  for {}  rejected as last beep end too short time ago {}".format(beacon, time.time() - self.beacons[beacon][u"lastBusy"]) )
				return valuesDict			
		self.beacons[beacon][u"lastBusy"] = time.time() + float(valuesDict[u"beepTime"]) + 50
		dev.updateStateOnServer(u"isBeepable",u"busy")

		typeOfBeacon = props[u"typeOfBeacon"]
		if typeOfBeacon !="":
			if typeOfBeacon in self.knownBeaconTags:
				if self.knownBeaconTags[typeOfBeacon][u"beepCmd"] != u"off":
					cmd 					= self.knownBeaconTags[typeOfBeacon][u"beepCmd"]
					cmd[u"beepTime"] 		= float(valuesDict[u"beepTime"])
					cmd[u"mustBeUp"] 		= mustBeUp
					xx 						= {u"cmd":u"beepBeacon", u"piServerNumber":piU, u"typeId":json.dumps({beacon:cmd})}
					if self.decideMyLog(u"Beep"): self.indiLOG.log(20,u"beep beacon requested  on pi{};  {}".format(piU, xx) )
					self.setCurrentlyBooting(20, setBy=u"beep beacon")
					self.setPin(xx)
					valuesDict[u"MSG"] = "beep {} on pi{} ".format(beacon, piU)
		return valuesDict

####-------------------------------------------------------------------------####
	def startCalibrationCALLBACKmenu(self, valuesDict=None, typeId="", devId=0):
		valuesDict[u"cmd"]		 = u"startCalibration"
		self.setPin(valuesDict)


####-------------------------------------------------------------------------####
	def execAcceptNewBeaconsCALLBACKmenu(self, valuesDict=None, typeId="", devId=0):

		if self.acceptNewTagiBeacons != valuesDict[u"acceptNewTagiBeacons"]: 
			self.setALLrPiV(u"piUpToDate", [u"updateParamsFTP"])
		self.acceptNewTagiBeacons = valuesDict[u"acceptNewTagiBeacons"]
		self.pluginPrefs[u"acceptNewTagiBeacons"] = valuesDict[u"acceptNewTagiBeacons"]	

		if unicode(self.acceptNewiBeacons) != valuesDict[u"acceptNewiBeacons"]: 
				self.setALLrPiV(u"piUpToDate", [u"updateParamsFTP"])
		try: 	xxx = int(valuesDict[u"acceptNewiBeacons"])
		except: xxx = 999 # do not accept new beacons
		self.acceptNewiBeacons = xxx
		self.pluginPrefs[u"acceptNewiBeacons"] = xxx

		valuesDict[u"MSG"] = u"RSSI >{}; Tag={}".format(valuesDict[u"acceptNewiBeacons"], valuesDict[u"acceptNewTagiBeacons"])
		return valuesDict

####-------------------------------------------------------------------------####
	def printBLEAnalysisCALLBACKmenu(self, valuesDict=None, typeId="", devId=0):
		valuesDict[u"cmd"]	 			= u"BLEAnalysis"
		valuesDict[u"typeId"]	 		= valuesDict[u"minRSSI"]
		self.setPin(valuesDict)

####-------------------------------------------------------------------------####
	def printtrackMacCALLBACKmenu(self, valuesDict=None, typeId="", devId=0):


		mac = valuesDict[u"mac"].upper()
		existingMAC = valuesDict[u"existingMAC"].upper()
		valuesDict[u"typeId"] = mac
		if mac != u"*":
			if not self.isValidMAC(mac):
				if not self.isValidMAC(existingMAC):
					valuesDict[u"MSG"]	= u"bad MAC number"
					return valuesDict
				else:
					valuesDict[u"typeId"]	= existingMAC
				

		valuesDict[u"cmd"]	 	= u"trackMac"
		self.setPin(valuesDict)
		valuesDict[u"MSG"] 		= u"cmd sub. for:"+ valuesDict[u"typeId"]
		return valuesDict

####-------------------------------------------------------------------------####
	def setnewMessageCALLBACKmenu(self, valuesDict=None, typeId="", devId=0):
		valuesDict[u"cmd"]		 = u"newMessage"
		self.setPin(valuesDict)

####-------------------------------------------------------------------------####
	def setresetDeviceCALLBACKmenu(self, valuesDict=None, typeId="", devId=0):
		valuesDict[u"cmd"]		 = u"resetDevice"
		self.setPin(valuesDict)
		if valuesDict[u"typeId"] != u"rainSensorRG11": return 

		# reseting plugin data for rain sensor:
		piServerNumber = int(valuesDict[u"piServerNumber"] )
		for dev in indigo.devices.iter(u"props.isSensorDevice"):
			if dev.deviceTypeId !="rainSensorRG11": continue

			for key in [u"rainRate",u"rainRateMinToday",u"rainRateMaxToday",u"rainRateMinYesterday",u"rainRateMaxYesterday",u"hourRain",u"lasthourRain",u"dayRain",u"lastdayRain",u"weekRain",u"lastweekRain",u"monthRain",u"lastmonthRain",u"yearRain",u"lastyearRain"]:
				self.addToStatesUpdateDict(dev.id, key, 0)
			self.addToStatesUpdateDict(dev.id, "resetDate", datetime.datetime.now().strftime(_defaultDateStampFormat))
			self.executeUpdateStatesDict(onlyDevID=dev.id, calledFrom=u"setresetDeviceCALLBACKmenu")

			dev2 = indigo.devices[dev.id]
			props= dev2.pluginProps
			for key in [u"hourRainTotal",u"dayRainTotal" ,"weekRainTotal",u"monthRainTotal",u"yearRainTotal"]:
				props[key] = 0
			self.deviceStopCommIgnore = time.time()
			dev2.replacePluginPropsOnServer(props)
		return 



####-------------------------------------------------------------------------####
	def setMyoutputCALLBACKmenu(self, valuesDict=None, typeId="", devId=0):
		valuesDict[u"typeId"]			 = u"myoutput"
		valuesDict[u"cmd"]				 = u"myoutput"
		self.setPin(valuesDict)

####-------------------------------------------------------------------------####
	def setMCP4725CALLBACKmenu(self, valuesDict=None, typeId="", devId=0):
		devId = int(valuesDict[u"outputDev"])
		dev = indigo.devices[devId]
		props = dev.pluginProps
		valuesDict[u"typeId"]			 = u"setMCP4725"
		valuesDict[u"devId"]			 = dev.id
		valuesDict[u"i2cAddress"]		 = props[u"i2cAddress"]
		valuesDict[u"piServerNumber"]	 = props[u"address"].split(u"-")[1]
		#valuesDict[u"cmd"]				  = u"analogWrite"
		self.setPin(valuesDict)

####-------------------------------------------------------------------------####
	def setPCF8591dacCALLBACKmenu(self, valuesDict=None, typeId="", devId=0):
		devId = int(valuesDict[u"outputDev"])
		dev = indigo.devices[devId]
		props = dev.pluginProps
		valuesDict[u"typeId"]			 = u"setPCF8591dac"
		valuesDict[u"devId"]			 = dev.id
		valuesDict[u"i2cAddress"]		 = props[u"i2cAddress"]
		valuesDict[u"piServerNumber"]	 = props[u"address"].split(u"-")[1]
		#valuesDict[u"cmd"]				  = u"analogWrite"
		self.setPin(valuesDict)


####-------------------------------------------------------------------------####


# noinspection SpellCheckingInspection
	def actionControlDimmerRelay(self, action, dev0):
		try:
			props0 = dev0.pluginProps
			if dev0.deviceTypeId == u"neopixel-dimmer":
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
							self.indiLOG.log(40,u"Line {} has error={}".format(sys.exc_traceback.tb_lineno, e))
							return
				except Exception, e:
					self.indiLOG.log(40,u"Line {} has error={}".format(sys.exc_traceback.tb_lineno, e))
					return

				if self.decideMyLog(u"OutputDevice"): self.indiLOG.log(10,u"{}".format(action) )
	 
				if not action.configured:
					self.indiLOG.log(20,u"actionControlDimmerRelay neopixel-dimmer not enabled:{}".format(unicode(dev0.name)) )
					return
				###action = dev.deviceAction
				if u"pixelMenulist" in props0 and props0[u"pixelMenulist"] != "":
					position = props0[u"pixelMenulist"]
					if position.find(u"*") >-1:
						position='u[u"*","*"]'
				else:
					try:
						position = u"["
						for ii in range(100):
							mmm = u"pixelMenu{}".format(ii)
							if	mmm not in props0 or props0[mmm] =="":		continue
							if len(props0[mmm].split(u",")) !=2:			continue
							position += u"[{}],".format(props0[mmm])
						position  = position.strip(u",") +u"]"
						position = json.loads(position)
					except Exception, e:
						self.indiLOG.log(40,u"Line {} has error={}".format(sys.exc_traceback.tb_lineno, e))
						self.indiLOG.log(40,u"position data: ".format(position))
						position=[]
				chList =[]


				RGB = [0,0,0,-1]

				channelKeys={u"redLevel":0,u"greenLevel":1,u"blueLevel":2,u"whiteLevel":3}
				if action.deviceAction == indigo.kDeviceAction.TurnOn:
					chList.append({u'key':u"onOffState", u'value':True})
					RGB=[255,255,255,-1]
				elif action.deviceAction == indigo.kDeviceAction.TurnOff:
					chList.append({u'key':u"onOffState", u'value':False})
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
						chList.append({u'key':col, u'value':white})
				else:
					RGB[3] = int(  round( (RGB[0]+RGB[1]+RGB[2])/3. )  )  ## 0..3*2.55=7.65

				for channel in channelKeys:
					if channel in dev0.states:
						chList.append(	{  'key':channel, 'value':int(round(RGB[channelKeys[channel]]/2.55))  }	 )

				if max(RGB) > 55: chList.append({u'key':u"onOffState", u'value':True})	   ## scale is 0-255
				else:			  chList.append({u'key':u"onOffState", u'value':False})

				#if "whiteLevel" in chList: del chList[u"whiteLevel"]
				self.execUpdateStatesList(dev0,chList)

				ppp =[]
				if unicode(position).find(u"*") > -1:
					ppp=[u"*",u"*",RGB[0],RGB[1],RGB[2]]
				else:
					for p in position:
						p[0] = min(	 max((ymax-1),0),int(p[0])	)
						p[1] = min(	 max((xmax-1),0),int(p[1])	)
						ppp.append([p[0],p[1],RGB[0],RGB[1],RGB[2]])
				if u"speedOfChange" in props0 and props0[u"speedOfChange"] !="":
					try:
						valuesDict[u"speedOfChange0"]		  = int(props0[u"speedOfChange"])
					except Exception, e:
						self.indiLOG.log(40,u"Line {} has error={}".format(sys.exc_traceback.tb_lineno, e))
				if self.decideMyLog(u"OutputDevice"): self.indiLOG.log(10,u"props0 {}".format(props0) )

				valuesDict[u"outputDev"]		 = devId
				valuesDict[u"type0"]			 = u"points"
				valuesDict[u"position0"]		 = json.dumps(ppp)
				valuesDict[u"display0"]			 = u"immediate"
				valuesDict[u"reset0"]			 = ""
				valuesDict[u"restoreAfterBoot"]	 = True

				if self.decideMyLog(u"OutputDevice"): self.indiLOG.log(10,u"valuesDict {}".format(valuesDict) )

				self.setneopixelCALLBACKmenu(valuesDict)

				return


			#####  GPIO		 
			else:
				dev= dev0
			props = dev.pluginProps

			if self.decideMyLog(u"OutputDevice"): self.indiLOG.log(10,u"deviceAction \n{}\n props {}".format(action, props))
			valuesDict={}
			valuesDict[u"outputDev"]=dev.id
			valuesDict[u"piServerNumber"] = props[u"piServerNumber"]
			valuesDict[u"deviceDefs"]	  = props[u"deviceDefs"]
			if dev.deviceTypeId ==u"OUTPUTgpio-1-ONoff":
				valuesDict[u"typeId"]	  = u"OUTPUTgpio-1-ONoff"
				typeId					  = u"OUTPUTgpio-1-ONoff"
			else: 
				valuesDict[u"typeId"]	  = u"OUTPUTgpio-1"
				typeId					  = u"OUTPUTgpio-1"
			if u"deviceDefs" in props:
				dd = json.loads(props[u"deviceDefs"])
				if len(dd) >0 and "gpio" in dd[0]:
					valuesDict[u"GPIOpin"]	  = dd[0][u"gpio"]
				elif u"gpio" in props:
					valuesDict[u"GPIOpin"] = props[u"gpio"]
				else:
					self.indiLOG.log(20,u"deviceAction error, gpio not defined action={}\n props {}".format(action.replace(u"\n",""), props) )
			elif u"gpio" in props:
				valuesDict[u"GPIOpin"] = props[u"gpio"]
			else:
				self.indiLOG.log(20,u"deviceAction error, gpio not defined action={}\n props {}".format(action.replace(u"\n",""), props) )
			   


			###### TURN ON ######
			if action.deviceAction == indigo.kDimmerRelayAction.TurnOn:
				valuesDict[u"cmd"] = u"up"

			###### TURN OFF ######
			elif action.deviceAction == indigo.kDimmerRelayAction.TurnOff:
				valuesDict[u"cmd"] = u"down"

			###### TOGGLE ######
			elif action.deviceAction == indigo.kDimmerRelayAction.Toggle:
				newOnState = not dev.onState
				if newOnState: valuesDict[u"cmd"] = u"up"
				else:		   valuesDict[u"cmd"] = u"down"

			###### SET BRIGHTNESS ######
			elif action.deviceAction == indigo.kDimmerRelayAction.SetBrightness:
				newBrightness = action.actionValue
				valuesDict[u"cmd"] = u"analogWrite"
				valuesDict[u"analogValue"] = unicode(float(newBrightness))


			###### BRIGHTEN BY ######
			elif action.deviceAction == indigo.kDimmerRelayAction.BrightenBy:
				newBrightness = dev.brightness + action.actionValue
				if newBrightness > 100:
					newBrightness = 100
				valuesDict[u"cmd"] = u"analogWrite"
				valuesDict[u"analogValue"] = unicode(float(newBrightness))

			###### DIM BY ######
			elif action.deviceAction == indigo.kDimmerRelayAction.DimBy:
				newBrightness = dev.brightness - action.actionValue
				if newBrightness < 0:
					newBrightness = 0
				valuesDict[u"cmd"] = u"analogWrite"
				valuesDict[u"analogValue"] = unicode(float(newBrightness))

			else:
				return

			self.setPinCALLBACKmenu(valuesDict, typeId)
			return
		except Exception, e:
			if unicode(e) != u"None":
				self.indiLOG.log(40,u"Line {} has error={}".format(sys.exc_traceback.tb_lineno, e))


####-------------------------------------------------------------------------####
	def actionControlGeneral(self, action, dev):
		###### STATUS REQUEST ######
		if action.deviceAction == indigo.kDeviceGeneralAction.RequestStatus:
			self.indiLOG.log(20,u"sent \"{}\"  status request".format(dev.name) )

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
			for dev in indigo.devices.iter(u"props.isSensorDevice"):
				if dev.deviceTypeId==  "INPUTpulse": 
					xList.append((dev.id, u"{}".format(dev.name)))
			return xList


####-------------------------------------------------------------------------####
	def filterINPUTdevices(self, valuesDict=None, filter="", typeId="", devId=""):
			xList = []
			for dev in indigo.devices.iter(u"props.isSensorDevice"):
				if dev.deviceTypeId.find(u"INPUTgpio") == -1 and dev.deviceTypeId.find(u"INPUTtouch") == -1 and dev.deviceTypeId.find(u"INPUTpulse") == -1 and dev.deviceTypeId.find(u"INPUTcoincidence") == -1: continue
				xList.append((dev.id, u"{}".format(dev.name)))
			return xList




####-------------------------------------------------------------------------####
	def filterOUTPUTdevicesACTION(self, valuesDict=None, filter="", typeId="",devId=""):
		xList = []
		for dev in indigo.devices.iter(u"props.isOutputDevice"):
			if dev.deviceTypeId.find(u"OUTPUTgpio") ==-1: continue
			xList.append((dev.id,u"{}".format(dev.name)))
		return xList
####-------------------------------------------------------------------------####
	def filterOUTPUTrelaydevicesACTION(self, valuesDict=None, filter="", typeId="",devId=""):
		xList = []
		for dev in indigo.devices.iter(u"props.isOutputDevice"):
			if dev.deviceTypeId.find(u"OUTPUTi2cRelay") ==-1: continue
			xList.append((dev.id,u"{}".format(dev.name)))
		return xList

####-------------------------------------------------------------------------####
	def filterOUTPUTchannelsACTION(self, valuesDict=None, filter="", typeId="", devId=""):
		okList = []
		#self.indiLOG.log(20,	u"self.outdeviceForOUTPUTgpio " + unicode(self.outdeviceForOUTPUTgpio))
		if self.outdeviceForOUTPUTgpio =="": return []
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
					okList.append((ll[0],u"OUTPUT_"+unicode(ii)+u" "+ll[1]))
					break
			#self.indiLOG.log(20,unicode(okList))
		except Exception, e:
			if unicode(e) != u"None":
				self.indiLOG.log(40,u"Line {} has error={}".format(sys.exc_traceback.tb_lineno, e))
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
		timeZones[12+12] = u"Pacific/Auckland"
		timeZones[11+12] = u"Pacific/Pohnpei"
		timeZones[10+12] = u"Australia/Melbourne"
		timeZones[9+12]	 = u"Asia/Tokyo"
		timeZones[8+12]	 = u"Asia/Shanghai"
		timeZones[7+12]	 = u"Asia/Saigon"
		timeZones[6+12]	 = u"Asia/Dacca"
		timeZones[5+12]	 = u"Asia/Karachi"
		timeZones[4+12]	 = u"Asia/Dubai"
		timeZones[3+12]	 = u"/Europe/Moscow"
		timeZones[2+12]	 = u"/Europe/Helsinki"
		timeZones[1+12]	 = u"/Europe/Berlin"
		timeZones[0+12]	 = u"/Europe/London"
		timeZones[-1+12] = u"Atlantic/Cape_Verde"
		timeZones[-2+12] = u"Atlantic/South_Georgia"
		timeZones[-3+12] = u"America/Buenos_Aires"
		timeZones[-4+12] = u"America/Puerto_Rico"
		timeZones[-5+12] = u"/US/Eastern"
		timeZones[-6+12] = u"/US/Central"
		timeZones[-7+12] = u"/US/Mountain"
		timeZones[-8+12] = u"/US/Pacific"
		timeZones[-9+12] = u"/US/Alaska"
		timeZones[-10+12] = u"Pacific/Honolulu"
		timeZones[-11+12] = u"US/Samoa"
		for ii in range(len(timeZones)):
			if ii > 12:
				xxx.append((unicode(ii-12)+u" "+timeZones[ii], u"+"+unicode(abs(ii-12))+u" "+timeZones[ii]))
			else:
				xxx.append((unicode(ii-12)+u" "+timeZones[ii], (unicode(ii-12))+u" "+timeZones[ii]))
		xxx.append((u"99 -", u"do not set"))
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
				self.indiLOG.log(20,u"deviceDefs not in valuesDict, need to define OUTPUT device properly " )
				return valuesDict
			valuesDict[u"deviceDefs"] = props[u"deviceDefs"]
		except:
			self.indiLOG.log(20,u"device not properly defined, please define OUTPUT ")
			return valuesDict

		#self.outdeviceForOUTPUTgpio = ""
		dev = indigo.devices[devId]
		props = dev.pluginProps
		valuesDict[u"typeId"]	  = dev.deviceTypeId
		valuesDict[u"devId"]	  = devId
		if u"i2cAddress" in props:
			valuesDict[u"i2cAddress"]	  = props[u"i2cAddress"]
		if self.decideMyLog(u"OutputDevice"): self.indiLOG.log(10,u"setPinCALLBACKmenu  valuesDict\n{}".format(valuesDict))
		self.setPin(valuesDict)


####-------------------------------------------------------------------------####
	def setDelay(self, startAtDateTimeIN=""):
		startAtDateTimeIN = unicode(startAtDateTimeIN)
		if self.decideMyLog(u"OutputDevice"): self.indiLOG.log(10,u"startAtDateTimeIN: "+ startAtDateTimeIN)
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
					if self.decideMyLog(u"OutputDevice"): self.indiLOG.log(10,u"startAtDateTimeIN: doing datetime")
					startAtDateTime	   = startAtDateTimeIN.replace(u"-","").replace(u":","").replace(u" ","").replace(u"/","").replace(u".","").replace(u",","")
					startAtDateTime	   = startAtDateTime.ljust(14,"0")
					return	 max(0, self.getTimetimeFromDateString(startAtDateTime, fmrt= u"%Y%m%d%H%M%S") - time.time() )
				except Exception, e:
					self.indiLOG.log(40,u"Line {} has error={}".format(sys.exc_traceback.tb_lineno, e))
					return 0
		except Exception, e:
			self.indiLOG.log(40,u"Line {} has error={}".format(sys.exc_traceback.tb_lineno, e))
		return 0



####-------------------------------------------------------------------------####
	def setPin(self, valuesDict=None):
		#self.indiLOG.log(20,	unicode(valuesDict))

		#self.outdeviceForOUTPUTgpio =""
		try:
			if u"piServerNumber" not in valuesDict:
				self.indiLOG.log(20,u"setPIN missing parameter: piServerNumber not defined")
				return
			piU = valuesDict[u"piServerNumber"]
			pi = int(piU)
			if piU not in _rpiList:
				self.indiLOG.log(20,u"setPIN bad parameter: piServerNumber out of range: " + piU)
				return

			if self.RPI[piU][u"piOnOff"] != u"1":
				self.indiLOG.log(20,u"setPIN bad parameter: piServer is not enabled: " + piU)
				return

			try:
				if not indigo.devices[int(self.RPI[piU][u"piDevId"])].enabled:
					return 
			except:
				return

			ip = self.RPI[piU][u"ipNumberPi"]
			if u"typeId" in valuesDict:	typeId = valuesDict[u"typeId"]
			else:						typeId = ""

			startAtDateTime = 0
			if u"startAtDateTime" in valuesDict:
				startAtDateTime = self.setDelay(startAtDateTimeIN=valuesDict[u"startAtDateTime"])

			if u"restoreAfterBoot"	 in valuesDict:
				restoreAfterBoot   = valuesDict[u"restoreAfterBoot"]
				if restoreAfterBoot !=u"1": restoreAfterBoot = u"0"
			else:
				restoreAfterBoot =u"0"

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

			if typeId == u"myoutput":
				if u"text" not in valuesDict:
					self.indiLOG.log(20,u"setPIN bad parameter: text not supplied: for pi#" + piU)
					return

				if self.decideMyLog(u"OutputDevice"): self.indiLOG.log(10,	u"sending command to rPi at " + ip + u"; port: " + unicode(self.rPiCommandPORT) + u"; cmd: myoutput;    "+ valuesDict[u"text"]		)
				self.sendGPIOCommand(ip, pi, typeId, u"myoutput",  text=valuesDict[u"text"])
				return


			if typeId == u"playSound":
					if u"soundFile" not in valuesDict:
						self.indiLOG.log(20,u"setPIN bad parameter: soundFile not supplied: for pi#" + piU)
						return
					try:
						line = u"\n##=======use this as a python script in an action group action :=====\n"
						line +=u"plug = indigo.server.getPlugin(\"com.karlwachs.piBeacon\")"
						line +=u"\nplug.executeAction(\"playSoundFile\" , props ={u"
						line +=u"\n	 \"outputDev\":\""+unicode(valuesDict[u"outputDev"])+u"\""
						line +=u"\n	,\"device\":\"" +unicode(typeId)+u"\""
						line +=u"\n	,\"restoreAfterBoot\":"+unicode(restoreAfterBoot)
						line +=u"\n	,\"startAtDateTime\":\""+unicode(startAtDateTime)+u"\""
						line +=u"\n	,\"cmd\":\""+valuesDict[u"cmd"]+u"\""
						line +=u"\n	,\"soundFile\":\""+valuesDict[u"soundFile"]+u"\"})\n"
						line+= u"##=======	end	   =====\n"
						if self.decideMyLog(u"OutputDevice"): self.indiLOG.log(10,u"\n"+line+u"\n")
					except:
						if self.decideMyLog(u"OutputDevice"): self.indiLOG.log(10,	u"sending command to rPi at " + ip + "; port: " + unicode(self.rPiCommandPORT) + "; cmd: " + valuesDict[u"cmd"] + ";  " + valuesDict[u"soundFile"])
					self.sendGPIOCommand(ip, pi,typeId, valuesDict[u"cmd"], soundFile=valuesDict[u"soundFile"])
					return

			if u"cmd" not in valuesDict:
				self.indiLOG.log(20,u" setPIN bad parameter: cmd not set:")
				return
			cmd = valuesDict[u"cmd"]

			if cmd not in _GlobalConst_allowedCommands:
				self.indiLOG.log(20,u" setPIN bad parameter: cmd bad:{}; allowed commands= {}".format(cmd, _GlobalConst_allowedCommands))
				return

			if cmd == u"getBeaconParameters":
				#self.indiLOG.log(10,u"sending command to rPi at {}; port: {}; cmd:{} ;  devices".format(pi, self.rPiCommandPORT, valuesDict[u"cmd"], valuesDict[u"typeId"]) )
				self.sendGPIOCommand(ip, pi, valuesDict[u"typeId"], valuesDict[u"cmd"])
				return

			if cmd == u"beepBeacon":
				if self.decideMyLog(u"OutputDevice"): self.indiLOG.log(10,u"sending command to rPi at {}; port: {}; cmd:{} ;  devices:{}".format(pi, self.rPiCommandPORT, valuesDict[u"cmd"], valuesDict[u"typeId"]) )
				self.sendGPIOCommand(ip, pi, valuesDict[u"typeId"], valuesDict[u"cmd"])
				return

			if cmd == u"newMessage":
				if u"typeId" not in valuesDict:
					self.indiLOG.log(20,u"setPIN bad parameter: typeId not supplied: for pi#{}".format(piU))
					return

				if self.decideMyLog(u"OutputDevice"): self.indiLOG.log(10,u"sending command to rPi at {}; port: {}; cmd:{} ;  typeId:{}".format(piU, self.rPiCommandPORT, valuesDict[u"cmd"], valuesDict[u"typeId"]) )
				self.sendGPIOCommand(ip, pi, typeId, valuesDict[u"cmd"])
				return


			if cmd == u"resetDevice":
				if u"typeId" not in valuesDict:
					self.indiLOG.log(20,u"setPIN bad parameter: typeId not supplied: for pi#{}".format(piU))
					return

				if self.decideMyLog(u"OutputDevice"): sself.indiLOG.log(10,u"sending command to rPi at {}; port: {}; cmd:{} ;  typeId:{}".format(piU, self.rPiCommandPORT, valuesDict[u"cmd"], valuesDict[u"typeId"]) )
				self.sendGPIOCommand(ip, pi, typeId, valuesDict[u"cmd"])
				return

			if cmd == u"startCalibration":
				if u"typeId" not in valuesDict:
					self.indiLOG.log(20,u"setPIN bad parameter: typeId not supplied: for pi#{}".format(piU))
					return

				if True:  self.indiLOG.log(20,u"sending command to rPi at {}; port: {}; cmd:{} ;  typeId:{}".format(piU, self.rPiCommandPORT, valuesDict[u"cmd"], valuesDict[u"typeId"]) )
				self.sendGPIOCommand(ip, pi, typeId, valuesDict[u"cmd"])
				return
			if cmd == u"BLEAnalysis":
				if True:  self.indiLOG.log(20,u"sending command to rPi at {}; port: {}; cmd:{} ".format(ip, self.rPiCommandPORT, valuesDict[u"cmd"]) )
				self.sendGPIOCommand(ip, pi, typeId, valuesDict[u"cmd"])
				return
			if cmd == u"trackMac":
				if True:  self.indiLOG.log(20,u"sending command to rPi at {}; port: {}; cmd:{} ".format(ip, self.rPiCommandPORT, valuesDict[u"cmd"]) )
				self.sendGPIOCommand(ip, pi, typeId, valuesDict[u"cmd"])
				return


			try:
				devIds = unicode(valuesDict[u"devId"])
				devId = int(devIds)
				dev = indigo.devices[devId]
				props=dev.pluginProps
			except:
				self.indiLOG.log(20,u" setPIN bad parameter: OUTPUT device not created: for pi#{}".format(piU))
				return

			if typeId in [u"setMCP4725",u"setPCF8591dac"]:
				try:
					i2cAddress = props[u"i2cAddress"]
					out = ""
					# _GlobalConst_allowedCommands		=[u"up",u"down",u"pulseUp",u"pulseDown",u"continuousUpDown",u"disable"]	# commands support for GPIO pins
					if cmd == u"analogWrite":
						out = cmd
					elif cmd == u"pulseUp":
						out = cmd + "," + unicode(pulseUp)
					elif cmd == u"pulseDown":
						out = cmd + "," + unicode(pulseDown)
					elif cmd == u"continuousUpDown":
						out = cmd + u"," + unicode(pulseUp) + "" + unicode(pulseUp) + u"," + unicode(nPulses)
					out += cmd + u"," + unicode(analogValue)
					out += cmd + u"," + unicode(rampTime)
					if u"writeOutputToState" not in props or (u"writeOutputToState" in props and props[u"writeOutputToState"] == u"1"): self.addToStatesUpdateDict(dev.id, u"OUTPUT", out)
				except Exception, e:
					self.indiLOG.log(40,u"Line {} has error={}".format(sys.exc_traceback.tb_lineno, e))
					outN = 0
				try:
					line = u"\n##=======use this as a python script in an action group action :=====\n"
					line +=u"plug = indigo.server.getPlugin(\"com.karlwachs.piBeacon\")"
					line +=u"\nplug.executeAction(\"set"+typeId+u"\" , props ={u"
					line +=u"\n	 \"outputDev\":\""+unicode(valuesDict[u"outputDev"])+u"\""
					line +=u"\n	,\"device\":\"" +unicode(typeId)+u"\""
					line +=u"\n	,\"restoreAfterBoot\":"+unicode(restoreAfterBoot)
					line +=u"\n	,\"startAtDateTime\":\""+unicode(startAtDateTime)+u"\""
					line +=u"\n	,\"cmd\":\""+valuesDict[u"cmd"]+u"\""
					line +=u"\n	,\"pulseUp\":\""+unicode(pulseUp)+u"\""
					line +=u"\n	,\"pulseDown\":\""+unicode(pulseDown)+u"\""
					line +=u"\n	,\"rampTime\":\""+unicode(rampTime)+u"\""
					line +=u"\n	,\"analogValue\":\""+unicode(analogValue)+u"\"})\n"
					line +=u"##=======	end	   =====\n"
					if self.decideMyLog(u"OutputDevice"): self.indiLOG.log(10,u"\n"+line+u"\n")
				except:
					if self.decideMyLog(u"OutputDevice"): self.indiLOG.log(10,u"sending command to rPi at " + ip + u"; port: " + unicode(self.rPiCommandPORT) +
							   u"; cmd: " + unicode(cmd) + u";  pulseUp: " + unicode(pulseUp) + ";  pulseDown: " +
							   unicode(pulseDown) + u";  nPulses: " + unicode(nPulses) + u";  analogValue: " + unicode(analogValue)+ u";  rampTime: " + unicode(rampTime)+ 
							   u";  restoreAfterBoot: " + unicode(restoreAfterBoot)+ u";   startAtDateTime: " + startAtDateTime)

				self.sendGPIOCommand(ip, pi, typeId, cmd, i2cAddress=i2cAddress,pulseUp=pulseUp, pulseDown=pulseDown, nPulses=nPulses, analogValue=analogValue,rampTime=rampTime, restoreAfterBoot=restoreAfterBoot , startAtDateTime=startAtDateTime, inverseGPIO =inverseGPIO, devId=devId )
				self.executeUpdateStatesDict(onlyDevID=dev.id, calledFrom=u"setPin")
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
				elif  u"OUTPUT" in valuesDict:
					output = int(valuesDict[u"OUTPUT"])
					deviceDefs = json.loads(valuesDict[u"deviceDefs"])
					if output <= len(deviceDefs):
						if u"gpio" in deviceDefs[output]:
							GPIOpin = deviceDefs[output][u"gpio"]
						else:
							self.indiLOG.log(20,u" setPIN bad parameter: no GPIOpin defined:" + unicode(valuesDict))
							return
					else:
						self.indiLOG.log(20,u" setPIN bad parameter: no GPIOpin defined:" + unicode(valuesDict))
						return
				else:
					self.indiLOG.log(20,u" setPIN bad parameter: no GPIOpin defined:" + unicode(valuesDict))
					return

				if u"inverseGPIO" in valuesDict:  # overwrite individual defs  if explicitely inverse defined 
					try: 											inverseGPIO = (valuesDict[u"inverseGPIO"])
					except:											inverseGPIO = False
				else:
					if deviceDefs[int(output)][u"outType"] == u"0":	inverseGPIO = False
					else:										  	inverseGPIO = True

				if typeId == u"OUTPUTgpio-1":
					analogValue = float(analogValue)
					b = ""
					if cmd == u"up":
						b = 100
					elif cmd == u"down":
						b = 0
					elif cmd == u"analogWrite":
						b = int(float(analogValue))
					if b != "" and u"onOffState" in dev.states:
						self.addToStatesUpdateDict(dev.id,u"brightnessLevel", b)
						if b >1: 
							self.addToStatesUpdateDict(dev.id,u"onOffState", True)
						else:
							self.addToStatesUpdateDict(dev.id,u"onOffState", False)
				if typeId == u"OUTPUTgpio-1-ONoff":
					if cmd == u"analogWrite": cmd ="up"
					analogValue =100
					b = ""
					if cmd == u"up":
						analogValue =100
						b = 100
					elif cmd == u"down":
						analogValue =0
						b = 0
					if b != "" and u"onOffState" in dev.states:
						if b >1:
							self.addToStatesUpdateDict(dev.id,u"onOffState", True)
						else:
							self.addToStatesUpdateDict(dev.id,u"onOffState", False)
				if typeId == u"OUTPUTi2cRelay":
					b = ""
					if cmd == u"up":
						b = 100
					elif cmd == u"down":
						b = 0
					if b != "" and u"onOffState" in dev.states:
						if b >1:
							self.addToStatesUpdateDict(dev.id,u"onOffState", True)
						else:
							self.addToStatesUpdateDict(dev.id,u"onOffState", False)


				try:
					out = ""
					# _GlobalConst_allowedCommands		=[u"up",u"down",u"pulseUp",u"pulseDown",u"continuousUpDown",u"disable"]	# commands support for GPIO pins
					if cmd == u"up" or cmd == u"down":
						out = cmd
					elif cmd == u"pulseUp":
						out = cmd + u"," + unicode(pulseUp)
					elif cmd == u"pulseDown":
						out = cmd + u"," + unicode(pulseDown)
					elif cmd == u"continuousUpDown":
						out = cmd + "," + unicode(pulseUp) + u"," + unicode(pulseUp) + u"," + unicode(nPulses)
					elif cmd == u"rampUp" or cmd == u"rampDown" or cmd == u"rampUpDown":
						out = cmd + "," + unicode(pulseUp) + "," + unicode(pulseUp) + u"," + unicode(nPulses)+ u"," + unicode(rampTime)
					elif cmd == u"analogWrite":
						out = cmd + u"," + unicode(analogValue)
					outN = int(output)
					if u"OUTPUT_{:02d}".format(outN) in dev.states: self.addToStatesUpdateDict(dev.id,u"OUTPUT_{:02d}".format(outN), out)
					if u"OUTPUT" in dev.states and ( u"writeOutputToState" not in props or (u"writeOutputToState" in props and props[u"writeOutputToState"] == u"1") ): self.addToStatesUpdateDict(dev.id,u"OUTPUT", out)
				except Exception, e:
					self.indiLOG.log(40,u"Line {} has error={}".format(sys.exc_traceback.tb_lineno, e))
					outN = 0
				try:
					line = u"\n##=======use this as a python script in an action group action :=====\n"
					line +=u"plug = indigo.server.getPlugin(\"com.karlwachs.piBeacon\")"
					line +=u"\nplug.executeAction(\"setPins\" , props ={u"
					line +=u"\n	 \"outputDev\":\""+unicode(valuesDict[u"outputDev"])+u"\""
					line +=u"\n	,\"device\":\"" +unicode(typeId)+u"\""
					line +=u"\n	,\"restoreAfterBoot\":"+unicode(restoreAfterBoot)
					line +=u"\n	,\"startAtDateTime\":\""+unicode(startAtDateTime)+u"\""
					line +=u"\n	,\"cmd\":\""+valuesDict[u"cmd"]+u"\""
					line +=u"\n	,\"pulseUp\":\""+unicode(pulseUp)+u"\""
					line +=u"\n	,\"pulseDown\":\""+unicode(pulseDown)+u"\""
					line +=u"\n	,\"rampTime\":\""+unicode(rampTime)+u"\""
					line +=u"\n	,\"analogValue\":\""+unicode(analogValue)+u"\""
					line +=u"\n	,\"i2cAddress\":\""+unicode(i2cAddress)+u"\""
					line +=u"\n	,\"GPIOpin\":\""+unicode(GPIOpin)+u"\"})\n"
					line+= u"##=======  end  =====\n"
					if self.decideMyLog(u"OutputDevice"): self.indiLOG.log(10,u"\n"+line+u"\n")
				except:
					if self.decideMyLog(u"OutputDevice"): self.indiLOG.log(10,u"sending command to rPi at " + ip + u"; port: " + unicode(self.rPiCommandPORT) + u" pin: " +
							   unicode(GPIOpin) + "; GPIOpin: " + unicode(GPIOpin) + u"OUTPUT#" + unicode(outN) + u"i2cAddress" + unicode(i2cAddress) + u"; cmd: " +
							   unicode(cmd) + ";  pulseUp: " + unicode(pulseUp) + ";  pulseDown: " +
							   unicode(pulseDown) + u"; nPulses: " + unicode(nPulses) + u"; analogValue: " + unicode(analogValue)+ u"; rampTime: " + unicode(rampTime)+ u";  restoreAfterBoot: " + unicode(restoreAfterBoot)+ u"; startAtDateTime: " + startAtDateTime)

				self.sendGPIOCommand(ip, pi, typeId, cmd, GPIOpin=GPIOpin, i2cAddress=i2cAddress, pulseUp=pulseUp, pulseDown=pulseDown, nPulses=nPulses, analogValue=analogValue, rampTime=rampTime, restoreAfterBoot=restoreAfterBoot , startAtDateTime=startAtDateTime, inverseGPIO =inverseGPIO, devId=devId )
				self.executeUpdateStatesDict(onlyDevID= devIds, calledFrom=u"setPin END")
				return

			self.indiLOG.log(20,u"setPIN:   no condition met, returning")

		except Exception, e:
			if unicode(e) != u"None":
				self.indiLOG.log(40,u"Line {} has error={}".format(sys.exc_traceback.tb_lineno, e))

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
			self.setONErPiV(piU,u"piUpToDate",[u"updateParamsFTP",u"rebootSSH"])
			self.rPiRestartCommand[pi]		= u"rebootSSH"  ## which part need to restart on rpi
			self.RPI[piU][u"ipNumberPiSendTo"] = self.RPI[piU][u"ipNumberPi"]
		return valuesDict


	###########################		MENU   END #################################




	###########################		ACTION	#################################

####-------------------------------------------------------------------------####
	def sendConfigviaSocketCALLBACKaction(self, action1=None, typeId="", devId=0):
		try:
			v = action1.props
			if v[u"configurePi"] =="": return
			piU= unicode(v[u"configurePi"])
			ip= self.RPI[piU][u"ipNumberPi"]
			if len(ip.split(u".")) != 4:
				self.indiLOG.log(20,u"sendingFile to rPI,  bad parameters:"+piU+u"  "+ip+u"  "+ unicode(v))
				return
			try:
				if not	indigo.devices[int(self.RPI[piS][u"piDevId"])].enabled: return
			except:
				return

			fileContents = self.makeParametersFile(piS,retFile=True)
			if len(fileContents) >0:
				if self.decideMyLog(u"OutputDevice"): self.indiLOG.log(10,	u"sending parameters file via socket: "+unicode(v)+u" \n"+fileContents)
				self.sendFileToRPIviaSocket(ip,piU,u"/home/pi/pibeacon/parameters",fileContents,fileMode="w")

		except Exception, e:
			if unicode(e) != u"None":
				self.indiLOG.log(40,u"Line {} has error={}".format(sys.exc_traceback.tb_lineno, e))
		return


####-------------------------------------------------------------------------####
	def sendExtraPagesToRpiViaSocketCALLBACKaction(self, action1=None, typeId="", devId=0):
		try:
			v = action1.props
			if v[u"configurePi"] =="": return
			piU= unicode(v[u"configurePi"])
			ip= self.RPI[piU][u"ipNumberPi"]
			if len(ip.split(u".")) != 4:
				self.indiLOG.log(20,u"sendingFile to rPI,  bad parameters:"+piU+u"  "+ip+u"  "+ unicode(v))
				return
			try:
				if not	indigo.devices[int(self.RPI[piU][u"piDevId"])].enabled: return
			except:
				return

			#if self.decideMyLog(u"OutputDevice"): self.indiLOG.log(10,u"sending extrapage file via socket: "+unicode(v))
			fileContents =[]
			#self.indiLOG.log(20,unicode(propsOut))
			for ii in range(10):
				if u"extraPage"+unicode(ii)+u"Line0" in v and u"extraPage"+unicode(ii)+u"Line1" in v and u"extraPage"+unicode(ii)+u"Color" in v:
					line0 = self.convertVariableOrDeviceStateToText(v[u"extraPage"+unicode(ii)+u"Line0"])
					line1 = self.convertVariableOrDeviceStateToText(v[u"extraPage"+unicode(ii)+u"Line1"])
					color = self.convertVariableOrDeviceStateToText(v[u"extraPage"+unicode(ii)+u"Color"])
					fileContents.append([line0,line1,color])
			if len(fileContents) >0:
				self.sendFileToRPIviaSocket(ip, piU, u"/home/pi/pibeacon/temp/extraPageForDisplay.inp",json.dumps(fileContents),fileMode="w",touchFile=False)

		except Exception, e:
			if unicode(e) != u"None":
				self.indiLOG.log(40,u"Line {} has error={}".format(sys.exc_traceback.tb_lineno, e))
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
					self.indiLOG.log(20,u"device not in valuesDict, need to define parameters properly ")
					return

			props = dev.pluginProps
			if u"deviceDefs" not in props:
				self.indiLOG.log(20,u"deviceDefs not in valuesDict, need to define OUTPUT device properly ")
				return
			valuesDict[u"deviceDefs"] = props[u"deviceDefs"]
			valuesDict[u"piServerNumber"] = props[u"piServerNumber"]
			if u"i2cAddress" in props:
				valuesDict[u"i2cAddress"] = props[u"i2cAddress"]


		except:
			self.indiLOG.log(20,u"setPinCALLBACKaction device not properly defined, please define OUTPUT ")
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
				self.indiLOG.log(20,u"setMCP4725CALLBACKaction action put wrong, device name/id	not installed/ configured:" + unicode(valuesDict))
				return

		props = dev.pluginProps
		typeId							= u"setMCP4725"
		valuesDict[u"typeId"]			 = typeId
		valuesDict[u"devId"]			 = dev.id
		valuesDict[u"i2cAddress"]		 = props[u"i2cAddress"]
		valuesDict[u"piServerNumber"]	 = props[u"address"].split(u"-")[1]
		valuesDict[u"cmd"]				 = u"analogWrite"
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
				self.indiLOG.log(20,u"setPCF8591dacCALLBACKaction action put wrong, device name/id  not installed/ configured:" + unicode(valuesDict))
				return

		props = dev.pluginProps
		typeId							 = u"setPCF8591dac"
		valuesDict[u"typeId"]			 = typeId
		valuesDict[u"devId"]			 = dev.id
		valuesDict[u"i2cAddress"]		 = props[u"i2cAddress"]
		valuesDict[u"piServerNumber"]	 = props[u"address"].split(u"-")[1]
		valuesDict[u"cmd"]				 = u"analogWrite"
		self.setPin(valuesDict)
		return


####-------------------------------------------------------------------------####
	def startCalibrationCALLBACKaction(self, action1):
		valuesDict = action1.props
		valuesDict[u"cmd"] = u"startCalibration"
		self.setPin(valuesDict)

####-------------------------------------------------------------------------####
	def setnewMessageCALLBACKaction(self, action1):
		valuesDict = action1.props
		valuesDict[u"cmd"] 				= u"newMessage"
		self.setPin(valuesDict)
		valuesDict[u"cmd"]	 			= u"resetDevice"

####-------------------------------------------------------------------------####
	def setresetDeviceCALLBACKAction(self, action1):
		valuesDict = action1.props
		valuesDict[u"cmd"]		 		= u"resetDevice"
		self.setPin(valuesDict)

####-------------------------------------------------------------------------####
	def setMyoutputCALLBACKaction(self, action1):
		valuesDict = action1.props
		valuesDict[u"typeId"]			 = u"myoutput"
		valuesDict[u"cmd"]				 = u"myoutput"
		self.setPin(valuesDict)
		return

####-------------------------------------------------------------------------####
	def playSoundFileCALLBACKaction(self, action1):
		valuesDict = action1.props
		valuesDict[u"typeId"]			 = u"playSound"
		valuesDict[u"cmd"]				 = u"playSound"
		self.setPin(valuesDict)
		return
	###########################		ACTION	 END #################################


	###########################	   Config  #################################
####-------------------------------------------------------------------------####
	def XXgetPrefsConfigUiValues(self):
		valuesDict= indigo.Dict()
		valuesDict[u"piServerNumber"]  = 99
		valuesDict[u"ipNumberPi"]	   = u"192.168.1.999"
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
			valuesDict[u"beaconOrSensor"] = u"iBeacon and Sensor rPi"
		else:
			valuesDict[u"beaconOrSensor"] = u"Sensor only rPi"
		usePassword = self.RPI[piU][u"passwordPi"]
		if	self.RPI[piU][u"passwordPi"] == u"raspberry":
			for piU0 in self.RPI:
				if self.RPI[piU0][u"passwordPi"] !="raspberry":
					usePassword = self.RPI[piU0][u"passwordPi"]
					break
		valuesDict[u"passwordPi"]		 = usePassword

		useID = self.RPI[piU][u"userIdPi"]
		if	self.RPI[piU][u"userIdPi"] == u"pi":
			for piU0 in self.RPI:
				if self.RPI[piU0][u"userIdPi"] !=u"pi" and len(self.RPI[piU0][u"userIdPi"]) > 1:
					useID = self.RPI[piU0][u"userIdPi"]
					break
		valuesDict[u"userIdPi"]			 = useID

		useIP = self.RPI[piU][u"ipNumberPi"]
		if self.RPI[piU][u"ipNumberPi"] == "":
			for piU0 in self.RPI:
				if self.RPI[piU0][u"ipNumberPi"] != "":
					useIP = self.RPI[piU0][u"ipNumberPi"]+u"x"
					break
		valuesDict[u"ipNumberPi"]		 = useIP

		valuesDict[u"enablePiEntries"]	 = True
		valuesDict[u"piOnOff"]			 = self.RPI[piU][u"piOnOff"]
		valuesDict[u"enableRebootCheck"] = self.RPI[piU][u"enableRebootCheck"]
		valuesDict[u"MSG"]				 = u"enter configuration"
		return valuesDict

####-------------------------------------------------------------------------####
	def buttonConfirmPiServerConfigCALLBACK(self, valuesDict=None, typeId="", devId=0):
		try:
			piU = valuesDict[u"piServerNumber"]
			pi = int(piU)
		#### check pi on/off
			p01 = valuesDict[u"piOnOff"]

			if p01 =="delete":
				self.delRPI(pi=pi, calledFrom=u"buttonConfirmPiServerConfigCALLBACK" )
				return valuesDict

			if p01 == u"0":  # off 
				self.RPI[piU][u"piOnOff"] = u"0"
				self.resetUpdateQueue(piU)
				valuesDict[u"MSG"] = u"Pi server disabled"
				try:
					dev= indigo.devices[self.RPI[piU][u"piDevId"]]
					dev.enabled = False
					dev.replaceOnServer()
					self.stopOneUpdateRPIqueues(piU, reason=u"set RPI off")
				except:
					pass
				return valuesDict
				
########## from here on it is ON 
			dateString	= datetime.datetime.now().strftime(_defaultDateStampFormat)

		####### check ipnumber
			ipn = valuesDict[u"ipNumberPi"]
			if not self.isValidIP(ipn):
				valuesDict[u"MSG"] = u"ip number not correct"
				return valuesDict



			# first test if already used somewhere else
			for piU3 in self.RPI:
				if piU == piU3: continue
				if self.RPI[piU3][u"piOnOff"] == u"0": continue
				if self.RPI[piU3][u"ipNumberPi"] == ipn:
						valuesDict[u"MSG"] = u"ip number already in use"
						return valuesDict

			if self.RPI[piU][u"ipNumberPi"]	  != ipn:
				self.RPI[piU][u"ipNumberPi"]   = ipn
				self.setONErPiV(piU,u"piUpToDate", [u"updateParamsFTP"])
			self.RPI[piU][u"ipNumberPiSendTo"] = ipn

			#### check authkey vs std password ..
			self.RPI[piU][u"authKeyOrPassword"] = valuesDict[u"authKeyOrPassword"]


			#### check userid password ..
			if self.RPI[piU][u"userIdPi"]	  != valuesDict[u"userIdPi"]:
				self.RPI[piU][u"userIdPi"]	   = valuesDict[u"userIdPi"]
				self.setONErPiV(piU,u"piUpToDate", [u"updateParamsFTP"])

			if self.RPI[piU][u"passwordPi"]	  != valuesDict[u"passwordPi"]:
				self.RPI[piU][u"passwordPi"]   = valuesDict[u"passwordPi"]
				self.setONErPiV(piU,u"piUpToDate", [u"updateParamsFTP"])

			if self.RPI[piU][u"enableRebootCheck"] != valuesDict[u"enableRebootCheck"]:
				self.RPI[piU][u"enableRebootCheck"] = valuesDict[u"enableRebootCheck"]
				self.setONErPiV(piU,u"piUpToDate", [u"updateParamsFTP"])


			valuesDict[u"MSG"] = u"Pi server configuration set"

			valuesDict[u"enablePiEntries"] = False
			if self.decideMyLog(u"UpdateRPI"): self.indiLOG.log(10,u"buttonConfirmPiServerConfigCALLBACK... pi#=        {}".format(piU))
			if self.decideMyLog(u"UpdateRPI"): self.indiLOG.log(10,u"valuesDict= {}".format(valuesDict))
			if self.decideMyLog(u"UpdateRPI"): self.indiLOG.log(10,u"RPI=        {}".format(self.RPI[piU]))

			if piU in  _rpiBeaconList:
						if self.RPI[piU][u"piDevId"] == 0: # check if  existing device
							found =False
							for dev in indigo.devices.iter(u"props.isRPIDevice"):
								try: 
									if dev.description.split(u"-")[1] == piU:
										props=dev.pluginProps
										if props[u"ipNumberPi"] != ipn:
											props[u"ipNumberPi"] = ipn
											self.deviceStopCommIgnore = time.time()
											dev.replacePluginPropsOnServer(props)
											self.updateNeeded += u"fixConfig"
											self.setONErPiV(piU,u"piUpToDate", [u"updateParamsFTP"])

										self.RPI[piU][u"piDevId"] = dev.id
										found = True
										break
								except:
									pass
							if not found:
									self.indiLOG.log(30,u"making new RPI: {};   ip: {}".format(pi, ipn))
									indigo.device.create(
										protocol		= indigo.kProtocol.Plugin,
										address			= u"00:00:00:00:pi:{:02d}".format(pi),
										name			= u"Pi_{}".format(pi),
										description		= u"Pi-{}-{}".format(pi,ipn),
										pluginId		= self.pluginId,
										deviceTypeId	= u"rPI",
										folder			= self.piFolderId,
										props			= copy.deepcopy(_GlobalConst_emptyrPiProps)
										)

									try:
										dev = indigo.devices[u"Pi_" +piU]
									except Exception, e:
										if unicode(e).find(u"timeout waiting") > -1:
											self.indiLOG.log(40,u"Line {} has error={}".format(sys.exc_traceback.tb_lineno, e))
											self.indiLOG.log(40,u"communication to indigo is interrupted")
											return valuesDict
										if unicode(e).find(u"not found in database") ==-1:
											self.indiLOG.log(40,u"Line {} has error={}".format(sys.exc_traceback.tb_lineno, e))
											return valuesDict
										self.indiLOG.log(40,u"Line {} has error={}".format(sys.exc_traceback.tb_lineno, e))

									dev.updateStateImageOnServer(indigo.kStateImageSel.SensorOn)
									self.addToStatesUpdateDict(dev.id,u"status", u"expired")
									self.addToStatesUpdateDict(dev.id,u"note", u"Pi-" + piU)
									self.addToStatesUpdateDict(dev.id,u"created",dateString)
									self.executeUpdateStatesDict(onlyDevID=dev.id, calledFrom=u"updateBeaconStates new rpi")
									self.RPI[piU][u"piMAC"] = u"00:00:00:00:pi:{:02d}".format(pi)
									self.RPI[piU][u"piDevId"] = dev.id

						else:
							try:
								dev= indigo.devices[self.RPI[piU][u"piDevId"]]
							except Exception, e: 
								if unicode(e).find(u"not found in database") >-1:
									dev = indigo.device.create(
										protocol		= indigo.kProtocol.Plugin,
										address			= u"Pi-{:02d}".format(pi),
										name			= u"Pi_{}".format(pi),
										description		= u"Pi-{:02d}-{}".format(pi,ipn),
										pluginId		= self.pluginId,
										deviceTypeId	= u"rPI",
										folder			= self.piFolderId,
										props			= copy.deepcopy(_GlobalConst_emptyrPiProps)
										)
									self.RPI[piU][u"piMAC"] = u"00:00:00:00:pi:{:02d}".format(pi)
									self.RPI[piU][u"piDevId"] = dev.id
						props= dev.pluginProps
						self.addToStatesUpdateDict(dev.id,u"note", u"Pi-{}".format(pi))
						props[u"description"] 				= u"Pi-{}-{}".format(pi,ipn)
						self.deviceStopCommIgnore 			= time.time()
						dev.replacePluginPropsOnServer(props)
						self.RPI[piU][u"piOnOff"] 	= u"1"
						dev.enabled = (p01 == u"1")

###### 
			if piU in _rpiSensorList:
						self.indiLOG.log(20,u"rpiSensor checking  RPI: {};   ip:{}; piDevId:{}".format(pi, ipn, self.RPI[piU][u"piDevId"]))
						if self.RPI[piU][u"piDevId"] == 0: # check if  existing device
							found =False
							for dev in indigo.devices.iter(u"props.isRPISensorDevice"):
								if dev.address.split(u"-")[1] == piU:
									props=dev.pluginProps
									if props[u"ipNumberPi"] != ipn:
										props[u"ipNumberPi"] = ipn
										self.deviceStopCommIgnore = time.time()
										dev.replacePluginPropsOnServer(props)
										self.updateNeeded += u"fixConfig"
										self.setONErPiV(piU,u"piUpToDate", [u"updateParamsFTP"])

									self.RPI[piU][u"piDevId"] = dev.id
									found = True
									break
							if not found:
								self.indiLOG.log(20,u"rpiSensor not found making new RPI")
								dev= indigo.device.create(
									protocol		= indigo.kProtocol.Plugin,
									address			= u"Pi-"+piU,
									name			= u"Pi_Sensor_" + piU,
									description		= u"Pi-" + piU+u"-"+ipn,
									pluginId		= self.pluginId,
									deviceTypeId	= u"rPI-Sensor",
									folder			= self.piFolderId,
									props		= {
											u"typeOfBeacon": u"rPi-Sensor",
											u"sendToIndigoSecs": 90,
											u"shutDownPinInput" : u"-1",
											u"shutDownPinOutput" : u"-1",
											u"expirationTime" : u"90",
											u"isRPISensorDevice" : True,
											u"SupportsStatusRequest": 	  _GlobalConst_emptyrPiProps[u"SupportsStatusRequest"],
											u"AllowOnStateChange": 		  _GlobalConst_emptyrPiProps[u"AllowOnStateChange"],
											u"AllowSensorValueChange":    _GlobalConst_emptyrPiProps[u"AllowSensorValueChange"],
											u"fastDown" : u"0",
											u"ipNumberPi":ipn}
									)
								self.addToStatesUpdateDict(dev.id,u"created",datetime.datetime.now().strftime(_defaultDateStampFormat))
								self.addToStatesUpdateDict(dev.id,u"note", u"Pi-" + piU)
								self.RPI[piU][u"piDevId"] = dev.id
								self.updateNeeded += u"fixConfig"
								self.setONErPiV(piU,u"piUpToDate", [u"updateParamsFTP"])
								try: self.indiLOG.log(20,u"rpiSensor created:{}, in folder:{}".format(dev.name,indigo.devices.folders.getName(self.piFolderId)))
								except: pass
						else:
							self.indiLOG.log(20,u"rpiSensor exists, no need to make new one")
							try:
								dev= indigo.devices[self.RPI[piU][u"piDevId"]]
							except Exception, e: 
								self.indiLOG.log(20,u"rpiSensor .. does not exists, failed to find")
								if unicode(e).find(u"not found in database") >-1:
									dev= indigo.device.create(
										protocol		= indigo.kProtocol.Plugin,
										address			= u"Pi-"+piU,
										name			= u"Pi_Sensor_" +piU,
										description		= u"Pi-" + piU+u"-"+ipn,
										pluginId		= self.pluginId,
										deviceTypeId	= u"rPI-Sensor",
										folder			= self.piFolderId,
										props		= {
											u"typeOfBeacon": u"rPi-Sensor",
											u"sendToIndigoSecs": 90,
											u"shutDownPinInput" : u"-1",
											u"shutDownPinOutput" : u"-1",
											u"expirationTime" : u"90",
											u"isRPISensorDevice" : True,
											u"SupportsStatusRequest": 	  _GlobalConst_emptyrPiProps[u"SupportsStatusRequest"],
											u"AllowOnStateChange": 		  _GlobalConst_emptyrPiProps[u"AllowOnStateChange"],
											u"AllowSensorValueChange":    _GlobalConst_emptyrPiProps[u"AllowSensorValueChange"],
											u"fastDown" : u"0",
											u"ipNumberPi":ipn}
										)
									self.addToStatesUpdateDict(dev.id,u"created",dateString)
									self.addToStatesUpdateDict(dev.id,u"note", u"Pi-" + piU)
									self.RPI[piU][u"piDevId"] = dev.id
									self.updateNeeded += u"fixConfig"
									self.setONErPiV(piU,u"piUpToDate", [u"updateParamsFTP"])
						dev= indigo.devices[self.RPI[piU][u"piDevId"]]
						props= dev.pluginProps
						self.addToStatesUpdateDict(dev.id,u"note", u"Pi-" + piU)
						props[u"description"] 				= u"Pi-"+piU+u"-"+ipn
						self.RPI[piU][u"piMAC"] 			= piU
						self.deviceStopCommIgnore 			= time.time()
						dev.replacePluginPropsOnServer(props)
						self.RPI[piU][u"piOnOff"] 			= u"1"
			try:
				dev= indigo.devices[self.RPI[piU][u"piDevId"]]
				dev.enabled = True
				#try:	del self.checkIPSendSocketOk[self.RPI[piU][u"ipNumberPi"]]
				#except: pass
				self.executeUpdateStatesDict(onlyDevID=dev.id, calledFrom=u"buttonConfirmPiServerConfigCALLBACK end")
			except:
				pass
			self.RPI[piU][u"piOnOff"] = u"1"
			self.startOneUpdateRPIqueue(piU, reason=u"; from basic setup")

			self.fixConfig(checkOnly = [u"all",u"rpi"],fromPGM=u"buttonConfirmPiServerConfigCALLBACK")

		except Exception, e:
			if unicode(e) != u"None":
				self.indiLOG.log(40,u"Line {} has error={}".format(sys.exc_traceback.tb_lineno, e))


		self.RPI[piU][u"piOnOff"] = u"1"
		self.writeJson(self.RPI, fName=self.indigoPreferencesPluginDir + u"RPIconf", fmtOn=self.RPIFileSort)
		self.startUpdateRPIqueues(u"restart", piSelect=piU)
		self.setONErPiV(piU,u"piUpToDate", [u"updateAllFilesFTP"])


		return valuesDict

####-------------------------------------------------------------------------####
	def delRPI(self, pi="", dev=u"none", calledFrom=""):
		try:
			devID = u"none"

			if dev == u"none" and pi == "": return
			if pi !="":
				try: pi = int(pi)
				except: return 
				piU = unicode(pi)
				devID = int(self.RPI[piU][u"piDevId"])
				self.indiLOG.log(30,u"=== delRPI:  deleting pi:{}  devID:{}, calledFrom: {} ".format(pi, devID, calledFrom) )
				try: indigo.device.delete(devID)
				except: pass
				self.resetRPI(piU)	
				return

			if dev !="none":
				devID = dev.id
				self.indiLOG.log(30,u"=== delRPI:  deleting dev:{}, calledFrom: {} ".format(dev.name, calledFrom) )
				pp =  dev.description.split(u"-")
				try: indigo.device.delete(devID)
				except: pass
				if len(pp) >1:
					try: pi = int(pp[1])
					except: return
					self.resetRPI(piU)	
				return

		except Exception, e:
			if unicode(e) != u"None":
				self.indiLOG.log(40,u"Line {} has error={}".format(sys.exc_traceback.tb_lineno, e))
			self.indiLOG.log(40,u"trying to delete indigo device for pi# {};  devID:{}; calledFrom:{}".format(pi, devID, calledFrom))
		return 

####-------------------------------------------------------------------------####
	def resetRPI(self, pi):
		piU = unicode(pi)
		if piU not in _rpiList: return 
		if piU in _rpiSensorList:
			self.RPI[piU] = copy.copy(_GlobalConst_emptyRPISENSOR)
		else: 
			self.RPI[piU] = copy.copy(_GlobalConst_emptyRPI)
		self.RPI[piU][u"piOnOff"] = u"0" 
		self.writeJson(self.RPI, fName=self.indigoPreferencesPluginDir + u"RPIconf", fmtOn=self.RPIFileSort)
		self.stopOneUpdateRPIqueues(piU, reason=u"rpi deleted / reset")

####-------------------------------------------------------------------------####

	def validatePrefsConfigUi(self, valuesDict):

		try:
			try: self.enableFING	= valuesDict[u"enableFING"]
			except: self.enableFING	= u"0"
			self.debugLevel 		= []

			for d in _debugAreas:
				if valuesDict[u"debug"+d]: self.debugLevel.append(d)
			try:			   
				if self.debugRPI	!= int(valuesDict[u"debugRPI"]): self.setALLrPiV(u"piUpToDate", [u"updateParamsFTP"])
				self.debugRPI		= int(valuesDict[u"debugRPI"])
			except: pass

			self.setLogfile(valuesDict[u"logFileActive2"])
	 
			self.enableBroadCastEvents					= valuesDict[u"enableBroadCastEvents"]

			try: 
				xx = valuesDict[u"SQLLoggingEnable"].split(u"-")
				yy = {u"devices":xx[0]==u"on", u"variables":xx[1]==u"on"}
				if yy != self.SQLLoggingEnable:
					self.SQLLoggingEnable = yy
					self.actionList[u"setSqlLoggerIgnoreStatesAndVariables"] = True
			except Exception, e:
				self.indiLOG.log(30,u"Line {} has error={}".format(sys.exc_traceback.tb_lineno, e))
				self.SQLLoggingEnable = {u"devices":True, u"variables":True}



			try: self.speedUnits					= max(0.01, float(valuesDict[u"speedUnits"]))
			except: self.speedUnits					= 1.
			try: self.distanceUnits					=  max(0.0254, float(valuesDict[u"distanceUnits"]))
			except: self.distanceUnits				= 1.
			try: self.lightningTimeWindow			= float(valuesDict[u"lightningTimeWindow"])
			except: self.lightningTimeWindow		= 10.
			try: self.lightningNumerOfSensors		= int(valuesDict[u"lightningNumerOfSensors"])
			except: self.lightningNumerOfSensors	= 1

			self.setClostestRPItextToBlank 			= valuesDict[u"setClostestRPItextToBlank"] !="1"

			for nn in range(len(_GlobalConst_groupList)):
				group = _GlobalConst_groupList[nn]
				self.groupListUsedNames[group] = valuesDict[u"groupName{}".format(nn)]

			self.pressureUnits						= valuesDict[u"pressureUnits"]	# 1 for Pascal
			self.tempUnits							= valuesDict[u"tempUnits"]	# Celsius, Fahrenheit, Kelvin
			self.tempDigits							= int(valuesDict[u"tempDigits"])  # 0/1/2

			newRain									= valuesDict[u"rainUnits"]	# mm inches
			self.rainDigits							= int(valuesDict[u"rainDigits"])  # 0/1/2
			if newRain != self.rainUnits:
				mult = 1.
				if	 newRain == u"inch"	and self.rainUnits == u"mm":	mult = 1./25.4
				elif newRain == u"inch"	and self.rainUnits == u"cm":	mult = 1./2.54
				elif newRain == u"mm"	and self.rainUnits == u"cm":	mult = 10.
				elif newRain == u"mm"	and self.rainUnits == u"inch": mult = 25.4
				elif newRain == u"cm"	and self.rainUnits == u"inch": mult = 2.54
				elif newRain == u"cm"	and self.rainUnits == u"mm":	mult = 0.1
				for dev in indigo.devices.iter(u"props.isSensorDevice"):
					if dev.deviceTypeId.find(u"rainSensorRG11") != -1: 
						props = dev.pluginProps
						for state in dev.states:
							if state.find(u"Rain") >-1 or state.find(u"rainRate") >-1:
								try: x = float(dev.states[state])
								except: continue
								self.addToStatesUpdateDict(dev.id,state, x*mult, decimalPlaces=self.rainDigits )
						self.executeUpdateStatesDict(onlyDevID=dev.id, calledFrom=u"validatePrefsConfigUi")
					   
						for prop in [u"hourRainTotal",u"lasthourRainTotal",u"dayRainTotal" ,"lastdayRainTotal",u"weekRainTotal",u"lastWeekRainTotal",u"monthRainTotal" ,u"lastmonthRainTotal",u"yearRainTotal"]:
								try:	props[prop] = float(props[prop]) * mult
								except: pass
						self.deviceStopCommIgnore = time.time()
						dev.replacePluginPropsOnServer(props)

			self.rainUnits =   newRain
			self.rebootHour							= int(valuesDict[u"rebootHour"])
			self.removeJunkBeacons					= valuesDict[u"removeJunkBeacons"] == u"1"
			xxx										= valuesDict[u"restartBLEifNoConnect"] == u"1"
			if xxx != self.restartBLEifNoConnect:
				self.setALLrPiV(u"piUpToDate", [u"updateParamsFTP"])
			self.restartBLEifNoConnect				= xxx


			try: self.enableRebootRPIifNoMessages	 = int(valuesDict[u"enableRebootRPIifNoMessages"])
			except: self.enableRebootRPIifNoMessages = 999999999

			xxx = valuesDict[u"rpiDataAcquistionMethod"]
			if xxx != self.rpiDataAcquistionMethod:
				self.setALLrPiV(u"piUpToDate", [u"updateParamsFTP"])
			self.rpiDataAcquistionMethod = xxx


			try:
				self.automaticRPIReplacement		= unicode(valuesDict[u"automaticRPIReplacement"]).lower() == u"true" 
			except:
				self.automaticRPIReplacement		= False 

			try:	self.maxSocksErrorTime			= float(valuesDict[u"maxSocksErrorTime"])
			except: self.maxSocksErrorTime			= 600.
			self.compressRPItoPlugin				= valuesDict[u"compressRPItoPlugin"]



			try:
				self.piUpdateWindow 				= float(valuesDict[u"piUpdateWindow"])
			except:
				valuesDict[u"piUpdateWindow"] 		= 0
				self.piUpdateWindow 				= 0.


			try:	self.beaconPositionsUpdateTime 	= float(valuesDict[u"beaconPositionsUpdateTime"])
			except: pass
			try:	self.beaconPositionsdeltaDistanceMinForImage = float(valuesDict[u"beaconPositionsdeltaDistanceMinForImage"])
			except: pass
			self.beaconPositionsData[u"Xscale"]				= (valuesDict[u"beaconPositionsimageXscale"])
			self.beaconPositionsData[u"Yscale"]				= (valuesDict[u"beaconPositionsimageYscale"])
			self.beaconPositionsData[u"Zlevels"]			= (valuesDict[u"beaconPositionsimageZlevels"])
			self.beaconPositionsData[u"dotsY"]				= (valuesDict[u"beaconPositionsimageDotsY"])

			self.beaconPositionsData[u"captionTextSize"]	= (valuesDict[u"beaconPositionsCaptionTextSize"])
			self.beaconPositionsData[u"textPosLargeCircle"]	= (valuesDict[u"beaconPositionstextPosLargeCircle"])
			self.beaconPositionsData[u"labelTextSize"]		= (valuesDict[u"beaconPositionsLabelTextSize"])
			self.beaconPositionsData[u"titleTextSize"]		= (valuesDict[u"beaconPositionsTitleTextSize"])
			self.beaconPositionsData[u"titleText"]			= (valuesDict[u"beaconPositionsTitleText"])
			self.beaconPositionsData[u"titleTextColor"]		= (valuesDict[u"beaconPositionsTitleTextColor"])
			self.beaconPositionsData[u"titleTextPos"]		= (valuesDict[u"beaconPositionsTitleTextPos"])
			self.beaconPositionsData[u"titleTextRotation"]	= (valuesDict[u"beaconPositionsTitleTextRotation"])

			self.beaconPositionsData[u"randomBeacons"] 		= (valuesDict[u"beaconRandomBeacons"])
			self.beaconPositionsData[u"LargeCircleSize"] 	= (valuesDict[u"beaconLargeCircleSize"])
			self.beaconPositionsData[u"SymbolSize"] 		= (valuesDict[u"beaconSymbolSize"])
			self.beaconPositionsData[u"ShowExpiredBeacons"] = (valuesDict[u"beaconShowExpiredBeacons"])
			self.beaconPositionsData[u"ShowCaption"]		= (valuesDict[u"beaconPositionsimageShowCaption"])
			self.beaconPositionsData[u"showTimeStamp"]		= (valuesDict[u"beaconPositionsShowTimeStamp"]) =="1"

			self.beaconPositionsData[u"Outfile"]			= (valuesDict[u"beaconPositionsimageOutfile"])
			self.beaconPositionsData[u"ShowRPIs"]			= (valuesDict[u"beaconPositionsimageShowRPIs"])
			self.beaconPositionsData[u"compress"]			= (valuesDict[u"beaconPositionsimageCompress"])
			self.beaconPositionsUpdated						= 2



			xxx = valuesDict[u"rebootWatchDogTime"]
			if xxx != self.rebootWatchDogTime:
				self.setALLrPiV(u"piUpToDate", [u"updateParamsFTP"])
			self.rebootWatchDogTime = xxx

			self.expectTimeout = valuesDict[u"expectTimeout"]


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
				self.indiLOG.log(20,u"switching communication, will send new config to all RPI and restart plugin")
				self.setALLrPiV(u"piUpToDate", [u"updateParamsFTP"])
			self.indigoInputPORT = xx

			try:
				xx = (valuesDict[u"IndigoOrSocket"])
			except:
				xx = 9999
			if xx != self.IndigoOrSocket:
				self.quitNow = u"restart, commnunication was switched "
				self.indiLOG.log(20,u"switching communication, will send new config to all RPI and restart plugin")
				self.setALLrPiV(u"piUpToDate", [u"updateParamsFTP"])
			self.IndigoOrSocket = xx

			try: 	xx = valuesDict[u"iBeaconFolderName"]
			except:	xx = u"PI_Beacons_new"
			if xx != self.iBeaconDevicesFolderName:
				self.iBeaconDevicesFolderName = xx
				self.getFolderIdOfBeacons()

			try:	xx = valuesDict[u"iBeaconFolderVariablesName"]
			except:	xx = u"piBeacons"
			try:	yy = valuesDict[u"iBeaconFolderVariableDataTransferVarsName"]
			except:	yy = u"piBeacons_dataTransferVars"
			if xx != self.iBeaconFolderVariablesName or yy != self.iBeaconFolderVariableDataTransferVarsName:
				self.iBeaconFolderVariablesName = xx
				self.iBeaconFolderVariableDataTransferVarsName = yy
				self.getFolderIdOfBeacons()

			upNames = False
			if self.groupCountNameDefault != valuesDict[u"groupCountNameDefault"]:	   upNames = True
			if self.ibeaconNameDefault	  != valuesDict[u"ibeaconNameDefault"]:		   upNames = True
			self.groupCountNameDefault = valuesDict[u"groupCountNameDefault"]
			self.ibeaconNameDefault	   = valuesDict[u"ibeaconNameDefault"]
			if upNames:
				self.deleteAndCeateVariables(False)
				self.varExcludeSQLList = [u"pi_IN_"+str(ii) for ii in _rpiList]
				self.varExcludeSQLList.append(self.ibeaconNameDefault+u"With_ClosestRPI_Change")
				self.varExcludeSQLList.append(self.ibeaconNameDefault+u"Rebooting")
				self.varExcludeSQLList.append(self.ibeaconNameDefault+u"With_Status_Change")
				for group in _GlobalConst_groupList:
					for tType in [u"Home", u"Away"]:
						self.varExcludeSQLList.append(self.groupCountNameDefault+group+u"_"+tType)
				self.actionList[u"setSqlLoggerIgnoreStatesAndVariables"] = True


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
			eth0					= '{"on":u"dontChange",	u"useIP":u"use"}'
			wlan0					= '{"on":u"dontChange",	u"useIP":u"useIf"}'
			try:	mm  			= {u"eth0":json.loads(valuesDict[u"eth0"]), u"wlan0":json.loads(valuesDict[u"wlan0"]) }
			except: mm  			= {u"eth0":json.loads(eth0),u"wlan0":json.loads(wlan0)}

			if ss != self.wifiSSID or pp != self.wifiPassword or kk != self.key_mgmt or mm != self.wifiEth:
				self.wifiSSID		= ss
				self.wifiPassword	= pp
				self.key_mgmt		= kk
				self.wifiEth		= mm
				self.setALLrPiV(u"piUpToDate", [u"updateParamsFTP"])

			if u"all" in self.debugLevel:
				self.printConfig()

			self.fixConfig(checkOnly = [u"all",u"rpi",u"force"],fromPGM=u"validatePrefsConfigUi")
		except Exception, e:
			if unicode(e) != u"None":
				self.indiLOG.log(40,u"Line {} has error={}".format(sys.exc_traceback.tb_lineno, e))
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
		self.quitNow		  = ""

		self.startTime		  = time.time()
		self.stackReady		  = False
		self.socketServer	  = None


		for ii in range(2):
			if self.pluginPrefs.get(u"authentication", u"digest") == u"none": break
			if self.userIdOfServer !="" and self.passwordOfServer != "": break
			self.indiLOG.log(30,u"indigo server userid or password not configured in config and security level is set to digest or basic")
			self.sleep(10)


		
		self.writeJson(self.pluginVersion, fName=self.indigoPreferencesPluginDir + u"currentVersion")

		self.initSprinkler()

		if self.indigoInputPORT > 0 and self.IndigoOrSocket == u"socket":
			self.setCurrentlyBooting(50, setBy=u"initConcurrentThread")
			self.socketServer, self.stackReady	= self.startTcpipListening(self.myIpNumber, self.indigoInputPORT)
			self.setCurrentlyBooting(40, setBy=u"initConcurrentThread")
		else:
			self.indiLOG.log(20,u" ..  subscribing to indigo variable changes" )
			indigo.variables.subscribeToChanges()
			self.setCurrentlyBooting(40, setBy=u"initConcurrentThread")
			self.stackReady			= True

		self.lastMinuteChecked	= now.minute
		self.lastHourChecked	= now.hour
		self.lastDayChecked		= [-1 for ii in range(len(self.checkBatteryLevelHours)+2)]
		self.lastSecChecked		= 0
		self.countLoop			= 0
		self.indiLOG.log(10,u" ..   checking sensors" )
		self.syncSensors()

		self.indiLOG.log(10,u" ..   checking BLEconnect" )
		self.BLEconnectCheckPeriod(force=True)
		self.indiLOG.log(10,u" ..   checking beacons" )
		self.BeaconsCheckPeriod(now, force=True)

		self.rPiRestartCommand = [u"master" for ii in range(_GlobalConst_numberOfRPI)]	## which part need to restart on rpi
		self.setupFilesForPi()
		if self.currentVersion != self.pluginVersion :
			self.setCurrentlyBooting(40, setBy=u"initConcurrentThread")
			self.indiLOG.log(10,u" ..  new py programs  etc will be send to rPis")
			for piU in self.RPI:
				if self.RPI[piU][u"ipNumberPi"] != "":
					self.setONErPiV(piU,u"piUpToDate", [u"updateAllFilesFTP",u"restartmasterSSH"])
			self.indiLOG.log(10,u" ..  new pgm versions send to rPis")
		else:
			for piU in self.RPI:
				if self.RPI[piU][u"ipNumberPi"] != "":
					self.setONErPiV(piU,u"piUpToDate", [u"updateParamsFTP"])

		if len(self.checkCarsNeed) > 0:
			for carId in self.checkCarsNeed:
				self.updateAllCARbeacons(carId, force=True)

		self.checkForUpdates(datetime.datetime.now())

		self.lastUpdateSend = time.time()  # used to send updates to all rPis if not done anyway every day
		self.pluginState	= u"run"
		self.setCurrentlyBooting(50, setBy=u"initConcurrentThread")

		return 





	###########################	   cProfile stuff   ############################ START
####-----------------  ---------
	def getcProfileVariable(self):

		try:
			if self.timeTrVarName in indigo.variables:
				xx = (indigo.variables[self.timeTrVarName].value).strip().lower().split(u"-")
				if len(xx) ==1: 
					cmd = xx[0]
					pri = ""
				elif len(xx) == 2:
					cmd = xx[0]
					pri = xx[1]
				else:
					cmd = u"off"
					pri  = ""
				self.timeTrackWaitTime = 20
				return cmd, pri
		except Exception, e:
			pass

		self.timeTrackWaitTime = 60
		return u"off",""

####-----------------            ---------
	def printcProfileStats(self,pri=""):
		try:
			if pri !="": pick = pri
			else:		 pick = u'cumtime'
			outFile		= self.indigoPreferencesPluginDir+u"timeStats"
			indigo.server.log(u" print time track stats to: {}.dump / txt  with option: {}".format(outFile, pick) )
			self.pr.dump_stats(outFile+u".dump")
			sys.stdout 	= open(outFile+u".txt", "w")
			stats 		= pstats.Stats(outFile+u".dump")
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
			self.do_cProfile  			= u"x"
			self.timeTrVarName 			= u"enableTimeTracking_"+self.pluginShortName
			indigo.server.log(u"testing if variable {} is == on/off/print-option to enable/end/print time tracking of all functions and methods (option:'',calls,cumtime,pcalls,time)".format(self.timeTrVarName))

		self.lastTimegetcProfileVariable = time.time()

		cmd, pri = self.getcProfileVariable()
		if self.do_cProfile != cmd:
			if cmd == u"on": 
				if  self.cProfileVariableLoaded ==0:
					indigo.server.log(u"======>>>>   loading cProfile & pstats libs for time tracking;  starting w cProfile ")
					self.pr = cProfile.Profile()
					self.pr.enable()
					self.cProfileVariableLoaded = 2
				elif  self.cProfileVariableLoaded >1:
					self.quitNow = u" restart due to change  ON  requested for print cProfile timers"
			elif cmd == u"off" and self.cProfileVariableLoaded >0:
					self.pr.disable()
					self.quitNow = u" restart due to  OFF  request for print cProfile timers "
		if cmd == u"print"  and self.cProfileVariableLoaded >0:
				self.pr.disable()
				self.printcProfileStats(pri=pri)
				self.pr.enable()
				indigo.variable.updateValue(self.timeTrVarName,u"done")

		self.do_cProfile = cmd
		return 

####-----------------            ---------
	def checkcProfileEND(self):
		if self.do_cProfile in[u"on",u"print"] and self.cProfileVariableLoaded >0:
			self.printcProfileStats(pri="")
		return
	###########################	   cProfile stuff   ############################ END



####-----------------   main loop          ---------
	def runConcurrentThread(self):

		self.dorunConcurrentThread()
		self.checkcProfileEND()
		self.sleep(1)
		if self.quitNow !="":
			indigo.server.log( u"runConcurrentThread stopping plugin due to:  ::::: {} :::::".format(self.quitNow))
			serverPlugin = indigo.server.getPlugin(self.pluginId)
			serverPlugin.restart(waitUntilDone=False)


		self.indiLOG.log(20,u"killing 2")
		subprocess.call(u"/bin/kill -9 "+unicode(self.myPID), shell=True )

		return



####-----------------   main loop          ---------
	def dorunConcurrentThread(self): 

		self.initConcurrentThread()


		if self.logFileActive != u"standard":
			indigo.server.log(u" ..  initialized")
			self.indiLOG.log(10,u" ..  initialized, starting loop" )
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
					if self.enableFING == u"1":
						self.updateFING(u"loop ")
					if len(self.sendBroadCastEventsList) >0: self.sendBroadCastNOW()

		except self.StopThread:
			indigo.server.log( u"stop requested from indigo ")
		## stop and processing of messages received 
		if self.quitNow !="": indigo.server.log( " .. quitNow: {}--- you might see an indigo error message, can be ignored ".format(self.quitNow))
		else: indigo.server.log( u" .. quitNow:  empty")

		self.stackReady	 = False 
		self.pluginState = u"stop"


		# save all parameters to file 
		self.fixConfig(checkOnly = [u"all",u"rpi",u"beacon",u"CARS",u"sensors",u"output",u"force"],fromPGM=u"finish") # runConcurrentThread end

		self.stopUpdateRPIqueues()
		time.sleep(1)

		if self.socketServer is not None:  
			self.indiLOG.log(20,u" ..   stopping tcpip stack")
			self.socketServer.shutdown()
			self.socketServer.server_close()
			time.sleep(1)
			# kill procs that might still be waiting / ...  
			lsofCMD	 = u"/usr/sbin/lsof -i tcp:"+unicode(self.indigoInputPORT)
			ret = subprocess.Popen(lsofCMD, shell=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE).communicate()
			#indigo.server.log(u".. stopping tcpip stack: lsof cmd result:\n{}".format(ret[0]))
			self.killHangingProcess(ret)



		return


####-------------------------------------------------------------------------####
	def checkGroups(self):
		self.setGroupStatus(init=self.statusChanged ==2)

####-------------------------------------------------------------------------####


# noinspection SpellCheckingInspection
	def updateFING(self, source):
		if self.enableFING == u"0": return
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
						self.indiLOG.log(40,u"Line {} has error={}".format(sys.exc_traceback.tb_lineno, e))
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
					if self.decideMyLog(u"Fing"): self.indiLOG.log(10,	u"updating fingscan ; source:" + source + u"     try# " + unicode(i + 1) + u";   with " + unicode(names) + u" " + unicode(devIDs) + u" " + unicode(states))
					plug = indigo.server.getPlugin(u"com.karlwachs.fingscan")
					if plug.isEnabled():
						plug.executeAction(u"piBeaconUpdate", props={u"deviceId": devIDs})
						self.fingscanTryAgain = False
						break
					else:
						if i == 2:
							self.indiLOG.log(20,u"fingscan plugin not reachable")
							self.fingscanTryAgain = True
						self.sleep(1)
		except Exception, e:
			if unicode(e) != u"None":
				self.indiLOG.log(40,u"Line {} has error={}".format(sys.exc_traceback.tb_lineno, e))

		return

####----------------- if FINGSCAN is enabled send update signal	 ---------
	def sendBroadCastNOW(self):
		try:
			x = False
			if	self.enableBroadCastEvents == u"0":
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
				msg ={u"pluginId":self.pluginId,u"data":msg}
				try:
					if self.decideMyLog(u"BC"): self.myLog( text=u"updating BC with " + unicode(msg),mType=u"BroadCast" )
					indigo.server.broadcastToSubscribers(u"deviceStatusChanged", json.dumps(msg))
				except Exception, e:
					if unicode(e) != u"None":
						self.indiLOG.log(40,u"updating sendBroadCastNOW has error Line {} has error={};    fingscan update failed".format(sys.exc_traceback.tb_lineno, e))

		except Exception, e:
			if unicode(e) != u"None":
				self.indiLOG.log(40,u"updating sendBroadCastNOW has error Line {} has error={}".format(sys.exc_traceback.tb_lineno, e))
			else:
				x = True
		return x


####-------------------------------------------------------------------------####
	def printpiUpToDate(self):
		try:
			xList = ""
			for piU in self.RPI:
				ok = True
				for action	in self.RPI[piU][u"piUpToDate"]:
					if action not in _GlobalConst_allowedpiSends:
						ok = False
						break
				xList += piU+u":"+unicode(self.RPI[piU][u"piUpToDate"])+u"; "
				if not ok: self.RPI[piU][u"piUpToDate"]=[]
			if self.decideMyLog(u"OfflineRPI"): self.indiLOG.log(10,u"printpiUpToDate list .. pi#:[actionLeft];.. ([]=ok): "+ xList	 ) 
		except Exception, e:
			if unicode(e) != u"None":
				self.indiLOG.log(40,u"Line {} has error={}".format(sys.exc_traceback.tb_lineno, e))
		return

####-------------------------------------------------------------------------####
	def findAnyTaskPi(self, item):
		try:
			for piU in self.RPI:
				if self.RPI[piU][item] !=[]:
					return True
		except Exception, e:
			if unicode(e) != u"None":
				self.indiLOG.log(40,u"Line {} has error={}".format(sys.exc_traceback.tb_lineno, e))
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

			self.checkForUpdates(now)

			if self.sendInitialValue != "": self.sendInitialValuesToOutput()

			self.checkMinute(now)

			self.sprinklerStats()


			if self.queueList !="":
				for ii in range(40):
					if ii > 0 and self.decideMyLog(u"BeaconData"): self.indiLOG.log(10,u"wait for queue to become available in main loop,   ii={}  {}".format(ii, self.queueList))
					if self.queueList =="": break
					self.sleep(0.05)

			self.startUpdateRPIqueues(u"restart")

			self.queueList = u"periodCheck"		 # block incoming messages from processing
			self.BLEconnectCheckPeriod()

			anyChange = self.BeaconsCheckPeriod(now)
			
			self.checkForCars()

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
		except Exception, e:
			if unicode(e) != u"None":
				self.indiLOG.log(40,u"Line {} has error={}".format(sys.exc_traceback.tb_lineno, e))

		return anyChange

####-------------------------------------------------------------------------####
	def checkForCars(self):
		try:
			if len(self.checkCarsNeed) > 0:
				delID ={}
				for carId in self.checkCarsNeed:
					if self.checkCarsNeed[carId] >0 and time.time()> self.checkCarsNeed[carId]:
						self.updateAllCARbeacons(carId)
						if self.checkCarsNeed[carId] == 0:
							delID[carId] = 1

				for carId in delID:
					del self.checkCarsNeed[carId]

		except Exception, e:
			if unicode(e) != u"None":
				self.indiLOG.log(40,u"Line {} has error={}".format(sys.exc_traceback.tb_lineno, e))

		return 


####-------------------------------------------------------------------------####
	def checkIfNotBeepableExpired(self):
		try:
			for beacon in self.beacons:
				if u"lastBusy" not in self.beacons[beacon] or self.beacons[beacon][u"lastBusy"] < 20000:
					self.beacons[beacon][u"lastBusy"] = time.time() - 1000
				if self.beacons[beacon][u"indigoId"] > 0: 
					if self.beacons[beacon][u"note"].find(u"beacon") > -1: 
						if self.beacons[beacon][u"lastBusy"] > 10000:
							if self.beacons[beacon][u"lastBusy"] > 0:
								if time.time() - self.beacons[beacon][u"lastBusy"] > -5:
									try: dev = indigo.devices[self.beacons[beacon][u"indigoId"]]
									except: continue
									if dev.enabled: 
										if u"isBeepable" in dev.states:  # wait until created, next reload
											tag = dev.states[u"typeOfBeacon"].split(u"-")[0]
											if tag in self.knownBeaconTags and self.knownBeaconTags[tag][u"beepCmd"] != u"off":
												dev.updateStateOnServer(u"isBeepable",u"YES")
												self.beacons[beacon][u"lastBusy"] = time.time() - 1000
											else:
												dev.updateStateOnServer(u"isBeepable",u"not capable")

		except Exception, e:
			if unicode(e) != u"None":
				self.indiLOG.log(40,u"Line {} has error={}".format(sys.exc_traceback.tb_lineno, e))
		return


####-------------------------------------------------------------------------####
	def performActionList(self):
		try:
			if self.actionList[u"setTime"] != []: 

				for action in self.actionList[u"setTime"]:
					if action[u"action"] == u"setTime":
						self.doActionSetTime(action[u"value"])

			if self.actionList[u"setSqlLoggerIgnoreStatesAndVariables"] :
				self.actionList[u"setSqlLoggerIgnoreStatesAndVariables"] = False
				self.setSqlLoggerIgnoreStatesAndVariables()

		except Exception, e:
			if unicode(e) != u"None":
				self.indiLOG.log(40,u"Line {} has error={}".format(sys.exc_traceback.tb_lineno, e))
		self.actionList[u"setTime"] = []
		return


####-------------------------------------------------------------------------####
	def replaceAddress(self):
		try:
			if self.newADDRESS !={}:
				for devId in self.newADDRESS:
					try:
						dev = indigo.devices[devId]
						if len(self.newADDRESS[devId]) == len(u"01:02:03:04:05:06"):
							self.indiLOG.log(20,u"updating {}  address with: {}".format(dev.name, self.newADDRESS[devId]))
							props = dev.pluginProps
							props[u"address"]= self.newADDRESS[devId]
							self.deviceStopCommIgnore = time.time()
							dev.replacePluginPropsOnServer(props)
							dev = indigo.devices[devId]
							props = dev.pluginProps
					except Exception, e:
						if unicode(e) != u"None":
							self.indiLOG.log(40,u"Line {} has error={}".format(sys.exc_traceback.tb_lineno, e))
							self.indiLOG.log(40,u"ok if replacing RPI")
				self.newADDRESS={}

		except Exception, e:
			if unicode(e) != u"None":
				self.indiLOG.log(40,u"Line {} has error={}".format(sys.exc_traceback.tb_lineno, e))



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
					inverseGPIO = (deviceDefs[n][u"outType"] == u"1")
					gpio = deviceDefs[n][u"gpio"]
					if self.decideMyLog(u"OutputDevice"): self.indiLOG.log(10,u"sendInitialValuesToOutput init pin: sending to pi# {}; pin: {}  {};  deviceDefs: {}".format(piServerNumber, props[u"gpio"], cmd, props[u"deviceDefs"]) )
					self.sendGPIOCommand(ip, int(piServerNumber), dev.deviceTypeId, cmd, GPIOpin=gpio, restoreAfterBoot="1", inverseGPIO =inverseGPIO )

		except Exception, e:
			if unicode(e) != u"None":
				self.indiLOG.log(40,u"Line {} has error={}".format(sys.exc_traceback.tb_lineno, e))
		self.sendInitialValue = ""
		return


####-------------------------------------------------------------------------####
	def checkForUpdates(self,now):
		anyChange= False
		try:

			if time.time()- self.lastUpdateSend > 3600:	 ## send config every hour, no other action
				self.rPiRestartCommand = ["" for ii in range(_GlobalConst_numberOfRPI)]  # soft update, no restart required
				self.setALLrPiV(u"piUpToDate", [u"updateParamsFTP"])

			if (self.updateNeeded.find(u"enable") > -1) or (self.updateNeeded.find(u"disable") > -1): 
				self.fixConfig(checkOnly = [u"all",u"rpi",u"force"], fromPGM=u"checkForUpdates") # checkForUpdates  # ok only if changes requested
				#self.syncSensors()
				self.setupFilesForPi(calledFrom=u"checkForUpdates enable/disable")
				try:
					pi = self.updateNeeded.split(u"-")
					if len(pi) >1:
						self.setONErPiV(pi[1],"piUpToDate", [u"updateParamsFTP"])
						if self.decideMyLog(u"UpdateRPI"): self.indiLOG.log(10,u"sending update to pi#{}".format(pi))
				except Exception, e:
					if unicode(e) != u"None":
						self.indiLOG.log(40,u"Line {} has error={}".format(sys.exc_traceback.tb_lineno, e))

				self.updateNeeded = "" 
	 
			if self.updateNeeded.find(u"fixConfig") > -1 or self.findAnyTaskPi(u"piUpToDate"):
				if self.decideMyLog(u"UpdateRPI"): self.indiLOG.log(10,u"checkForUpdates updateNeeded {}  findAnyTaskPi: {}".format(self.updateNeeded, self.findAnyTaskPi(u"piUpToDate")) )
				self.fixConfig(checkOnly = [u"all",u"rpi",u"force"],fromPGM=u"checkForUpdates") # checkForUpdates  # ok only if changes requested
				self.setupFilesForPi(calledFrom=u"checkForUpdates")
				self.updateNeeded = ""


			if not self.findAnyTaskPi(u"piUpToDate"):
				self.updateRejectListsCount =0
			else:
					self.newIgnoreMAC = 0
					for piU in self.RPI:

						if u"initSSH" in self.RPI[piU][u"piUpToDate"]:
							self.sshToRPI(piU, fileToSend=u"initSSH.exp")

						if u"upgradeOpSysSSH" in self.RPI[piU][u"piUpToDate"]:
							self.sshToRPI(piU, fileToSend=u"upgradeOpSysSSH.exp", endAction= u"end")

						if u"updateAllFilesFTP" in self.RPI[piU][u"piUpToDate"]:
							self.sendFilesToPiFTP(piU, fileToSend=u"updateAllFilesFTP.exp")

						if u"updateParamsFTP" in self.RPI[piU][u"piUpToDate"]:
							self.sendFilesToPiFTP(piU, fileToSend=u"updateParamsFTP.exp")

						if u"restartmasterSSH" in self.RPI[piU][u"piUpToDate"]:
							self.sshToRPI(piU, fileToSend=u"restartmasterSSH.exp")

						if self.updateRejectListsCount < _GlobalConst_numberOfRPI:
							self.updateRejectListsCount +=1
							self.updateRejectLists()
						else:
							self.printpiUpToDate()

					if self.findTaskPi(u"piUpToDate",u"getStatsSSH"):
						for piU in self.RPI:
							if u"getStatsSSH" in self.RPI[piU][u"piUpToDate"]:
								self.sshToRPI(piU,fileToSend=u"getStatsSSH.exp")

					if self.findTaskPi(u"piUpToDate",u"getLogFileSSH"):
						for piU in self.RPI:
							if u"getLogFileSSH" in self.RPI[piU][u"piUpToDate"]:
								self.sshToRPI(piU,fileToSend=u"getLogFileSSH.exp")

					if self.findTaskPi(u"piUpToDate",u"shutdownSSH"):
						for piU in self.RPI:
							if u"shutdownSSH" in self.RPI[piU][u"piUpToDate"]:
								self.sshToRPI(piU,fileToSend=u"shutdownSSH.exp")

					if self.findTaskPi(u"piUpToDate",u"rebootSSH"):
						for piU in self.RPI:
							if u"rebootSSH" in self.RPI[piU][u"piUpToDate"] and not  u"updateParamsFTP" in self.RPI[piU][u"piUpToDate"]:
								self.sshToRPI(piU,fileToSend=u"rebootSSH.exp")

					if self.findTaskPi(u"piUpToDate",u"resetOutputSSH"):
						for piU in self.RPI:
							if u"resetOutputSSH" in self.RPI[piU][u"piUpToDate"]  and not  u"updateParamsFTP" in self.RPI[piU][u"piUpToDate"]:
								self.sshToRPI(piU,fileToSend=u"resetOutputSSH.exp")

		except Exception, e:
			if unicode(e) != u"None":
				self.indiLOG.log(40,u"Line {} has error={}".format(sys.exc_traceback.tb_lineno, e))
		return anyChange


####-------------------------------------------------------------------------####
	def checkMinute(self, now):
		if now.minute == self.lastMinuteChecked: return

		try:
			self.fixConfig(checkOnly = [u"all"], fromPGM=u"checkMinute") # checkMinute
			self.checkRPIStatus()
			self.checkSensorStatus()
			self.saveTcpipSocketStats()

			self.freezeAddRemove = False

			if now.minute % 5 == 0:
				if self.newIgnoreMAC > 0:
					for piU in self.RPI:
						self.setONErPiV(piU,u"piUpToDate", [u"updateParamsFTP"])
					self.newIgnoreMAC = 0

				for piU in self.RPI:
					if self.RPI[piU][u"piOnOff"] == u"0":					continue
					if self.RPI[piU][u"piDevId"] ==	 0:						continue
					if time.time() - self.RPI[piU][u"lastMessage"] < 330.:	continue
					if self.decideMyLog(u"Logic"): self.indiLOG.log(10,u"pi server # {}  ip# {}  has not send a message in the last {:.0f} seconds".format(piU, self.RPI[piU][u"ipNumberPi"], time.time() - self.RPI[piU][u"lastMessage"]))

		except Exception, e:
			if unicode(e) != u"None":
				self.indiLOG.log(40,u"Line {} has error={}".format(sys.exc_traceback.tb_lineno, e))
		return

####-------------------------------------------------------------------------####
	def BLEconnectCheckPeriod(self, force = False):
		try:
			if time.time()< self.currentlyBooting:
				return
			for dev in indigo.devices.iter(u"props.isBLEconnectDevice"):
				if not dev.enabled: continue
				if self.queueListBLE == u"update": self.sleep(0.1)
				lastStatusChangeDT = 99999
				props = dev.pluginProps
				try:
					expirationTime = float(props[u"expirationTime"]) + 0.1
				except:
					continue
				status = u"expired"
				lastUp = dev.states[u"lastUp"]
				dt = time.time() - self.getTimetimeFromDateString(lastUp)
				if dt <= 1 * expirationTime:
					status = u"up"
				elif dt <= 2 * expirationTime:
					status = u"down"


				if dev.states[u"status"] != status or self.initStatesOnServer or force:
					if u"lastStatusChange" in dev.states: 
						lastStatusChangeDT   =  time.time() - self.getTimetimeFromDateString(dev.states[u"lastStatusChange"]) 
					if lastStatusChangeDT > 3: 
						#if self.decideMyLog(u"BLE") and dev.name.find(u"BLE-C") >-1: self.indiLOG.log(10,u"BLEconnectCheckPeriod :"+dev.name+u";  new status:"+ status+u"; old status:"+ dev.states[u"status"]+u"   dt="+ unicode(dt) +u"; lastUp="+unicode(lastUp)+u"; expirationTime="+unicode(expirationTime))
						if status == u"up":
							dev.updateStateImageOnServer(indigo.kStateImageSel.SensorOn)
						elif status == u"down":
							dev.updateStateImageOnServer(indigo.kStateImageSel.SensorOff)
						else:
							dev.updateStateImageOnServer(indigo.kStateImageSel.SensorTripped)
					self.addToStatesUpdateDict(dev.id,u"status", status)

				if status != u"up":
					if unicode(dev.states[u"closestRPI"]) != u"-1":
						self.addToStatesUpdateDict(dev.id,u"closestRPI", -1)

				self.executeUpdateStatesDict(onlyDevID=dev.id, calledFrom=u"BLEconnectCheckPeriod end")	  


		except Exception, e:
			if unicode(e) != u"None":
				self.indiLOG.log(40,u"Line {} has error={}".format(sys.exc_traceback.tb_lineno, e))
		return

####-------------------------------------------------------------------------####
	def checkSensorStatus(self):

		try:
			for dev in indigo.devices.iter(u"props.isSensorDevice"):
				if dev.deviceTypeId not in _GlobalConst_allowedSensors and dev.deviceTypeId not in _BLEsensorTypes: continue
				dt = time.time()- self.checkSensorMessages(dev.id,u"lastMessage", default=time.time())

				if time.time()< self.currentlyBooting: continue 
				if dt > 600:
					try:
						if	dev.pluginProps[u"displayS"].lower().find(u"temp")==-1:
							dev.updateStateImageOnServer(indigo.kStateImageSel.PowerOff)
						else:
							dev.updateStateImageOnServer(indigo.kStateImageSel.PowerOff)
					except:
						self.indiLOG.log(20,u"checkSensorStatus: {} property displayS missing, please edit and save ".format(dev.name) )
						dev.updateStateImageOnServer(indigo.kStateImageSel.Error)
			self.saveSensorMessages(devId="")

		except Exception, e:
			if unicode(e) != u"None":
				self.indiLOG.log(40,u"Line {} has error={}".format(sys.exc_traceback.tb_lineno, e))
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
				if self.RPI[piU][u"piOnOff"] == u"0": 
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
						if dev.states[u"status"] in [u"down",u"expired"]:
							dev.setErrorStateOnServer(u"Pconnection and BLE down")
							dev.updateStateImageOnServer(indigo.kStateImageSel.SensorTripped)
						else:
							dev.setErrorStateOnServer("")
							dev.updateStateImageOnServer(indigo.kStateImageSel.PowerOff)

				elif time.time()- self.RPI[piU][u"lastMessage"] >120:
					self.addToStatesUpdateDict(dev.id,u"online", u"down")
					if piU in _rpiSensorList: 
						self.addToStatesUpdateDict(dev.id,u"status", u"down")
						dev.updateStateImageOnServer(indigo.kStateImageSel.PowerOff)
					else:
						if dev.states[u"status"] in [u"down",u"expired"]:
							dev.setErrorStateOnServer(u"IPconnection and BLE down")
							dev.updateStateImageOnServer(indigo.kStateImageSel.SensorTripped)
						else:
							dev.setErrorStateOnServer("")
							dev.updateStateImageOnServer(indigo.kStateImageSel.PowerOff)

				else:
					self.addToStatesUpdateDict(dev.id,u"online", u"up")
					self.addToStatesUpdateDict(dev.id,u"status", u"up")
					dev.setErrorStateOnServer("")
					if piU in _rpiSensorList: 
							dev.updateStateImageOnServer(indigo.kStateImageSel.SensorOn)
					else:
						if dev.states[u"status"] in [u"down",u"expired"]:
							dev.updateStateImageOnServer(indigo.kStateImageSel.SensorOff)
						else:
							dev.updateStateImageOnServer(indigo.kStateImageSel.SensorOn)

		except Exception, e:
			if unicode(e) != u"None":
				self.indiLOG.log(40,u"Line {} has error={}".format(sys.exc_traceback.tb_lineno, e))


		return



####-------------------------------------------------------------------------####


# noinspection SpellCheckingInspection
	def BeaconsCheckPeriod(self, now, force = False):
		try:
			if	time.time()< self.currentlyBooting:
				if time.time()> self.lastUPtoDown:
					self.indiLOG.log(20,u"BeaconsCheckPeriod waiting for reboot, no changes in up--> down status for another {:.0f}[secs]".format(self.currentlyBooting - time.time())) 
					self.lastUPtoDown  = time.time()+90
				return False # noting for the next x minutes due to reboot 
			anyChange = False
			for beacon in self.beacons:
				if not self.beacons[beacon][u"enabled"]: continue
				if self.beacons[beacon][u"ignore"] > 0 : continue

				if len(self.beacons[beacon][u"receivedSignals"]) < len(_rpiBeaconList):  
					self.fixBeaconPILength(beacon, u"receivedSignals")

				if beacon.find(u"00:00:00:00") ==0: continue
				dev = ""
				if self.selectBeaconsLogTimer !={}: 
					for sMAC in self.selectBeaconsLogTimer:
						if beacon.find(sMAC[:self.selectBeaconsLogTimer[sMAC]]) ==0:
							self.indiLOG.log(20,u"sel.beacon logging: CheckPeriod -0- :{};".format(beacon)  )
				changed = False
				if u"status" not in self.beacons[beacon] : continue
				## pause is set at device stop, check if still paused skip


				if self.selectBeaconsLogTimer !={}: 
					for sMAC in self.selectBeaconsLogTimer:
						if beacon.find(sMAC[:self.selectBeaconsLogTimer[sMAC]]) ==0:
							self.indiLOG.log(20,u"sel.beacon logging: CheckPeriod -1- :{}; passed pause".format(beacon) )

				if self.beacons[beacon][u"lastUp"] > 0:
					if self.beacons[beacon][u"ignore"] == 1 :
						if time.time()- self.beacons[beacon][u"lastUp"] > 3 * 86000 :  ## 3 days
							self.beacons[beacon][u"ignore"] = 2
					# if self.beacons[beacon][u"status"] ==u"expired": continue
					if self.beacons[beacon][u"ignore"] > 0 : continue
				if self.selectBeaconsLogTimer !={}: 
					for sMAC in self.selectBeaconsLogTimer:
						if beacon.find(sMAC[:self.selectBeaconsLogTimer[sMAC]]) ==0:
							self.indiLOG.log(20,u"sel.beacon logging: CheckPeriod -2- :{}; passed ignore".format(beacon) )

				expT = float(self.beacons[beacon][u"expirationTime"])
				if self.beacons[beacon][u"lastUp"] < 0:	 # fast down was last                  event, block for 5 secs after that
					if time.time() + self.beacons[beacon][u"lastUp"] > 5:
						self.beacons[beacon][u"lastUp"] = time.time()- expT-0.1
					else:
						if self.selectBeaconsLogTimer !={}: 
							for sMAC in self.selectBeaconsLogTimer:
								if beacon.find(sMAC[:self.selectBeaconsLogTimer[sMAC]]) ==0:
									self.indiLOG.log(20,u"sel.beacon logging: CheckPeriod -3- :{};  no change in up status, dt:{:.0f}".format(beacon, time.time() + self.beacons[beacon][u"lastUp"]) )
						continue

				delta = time.time()- self.beacons[beacon][u"lastUp"]  ##  no !! - self.beacons[beacon][u"updateSignalValuesSeconds"]

				if self.beacons[beacon][u"status"] == u"up" :
					if delta >  2*expT:
						self.beacons[beacon][u"status"] = u"expired"
					elif delta > expT :
						self.beacons[beacon][u"status"] = u"down"
						self.beacons[beacon][u"updateFING"] = 1
						#self.indiLOG.log(20,	u" up to down secs: delta= u" + unicode(delta) + " expT: " + unicode(expT) + "  " + beacon)
						changed = True
						changed = True 
				elif self.beacons[beacon][u"status"] == u"down" :
					if delta >  2*expT:
						self.beacons[beacon][u"status"] = u"expired"
						changed = True
				elif self.beacons[beacon][u"status"] == "":
					self.beacons[beacon][u"status"] = u"expired"
					changed = True
				if	self.initStatesOnServer: changed = True
				if self.selectBeaconsLogTimer !={}: 
					for sMAC in self.selectBeaconsLogTimer:
						if beacon.find(sMAC[:self.selectBeaconsLogTimer[sMAC]]) ==0:
							self.indiLOG.log(20,u"sel.beacon logging: CheckPeriod -4- :{}; status: {};  deltaT: {}".format(beacon, self.beacons[beacon][u"status"], delta))


				if changed or force:
					if self.decideMyLog(u"BeaconData"): self.indiLOG.log(10,u" CheckPeriod -5- :{}; changed=true or force {}" .format(beacon, self.beacons[beacon][u"status"]) )
						

					try :
						dev = indigo.devices[self.beacons[beacon][u"indigoId"]]
						props = dev.pluginProps
						if dev.states[u"groupMember"] !="": anyChange = True
						self.addToStatesUpdateDict(dev.id,u"status", self.beacons[beacon][u"status"])

						if self.beacons[beacon][u"status"] == u"up":
							if u"closestRPI" in dev.states: 
								closest =  self.findClosestRPI(beacon,dev)
								if closest != dev.states[u"closestRPI"]:
									if unicode(dev.states[u"closestRPI"]) != "-1":
										self.addToStatesUpdateDict(dev.id,u"closestRPILast", dev.states[u"closestRPI"])
										self.addToStatesUpdateDict(dev.id,u"closestRPITextLast", dev.states[u"closestRPIText"])
									self.addToStatesUpdateDict(dev.id,u"closestRPI", closest)
									self.addToStatesUpdateDict(dev.id,u"closestRPIText",self.getRPIdevName((closest)))
							if self.beacons[beacon][u"note"].find(u"beacon")>-1: 
								dev.updateStateImageOnServer(indigo.kStateImageSel.SensorOn) # not for RPI's

						elif self.beacons[beacon][u"status"] == u"down":
							if self.beacons[beacon][u"note"].find(u"beacon") > -1:
								if u"closestRPI" in dev.states:
									if closestRPI != dev.states[u"closestRPI"]:
										if unicode(dev.states[u"closestRPI"]) != u"-1":
											self.addToStatesUpdateDict(dev.id,u"closestRPILast", dev.states[u"closestRPI"])
											self.addToStatesUpdateDict(dev.id,u"closestRPITextLast", dev.states[u"closestRPIText"])
									self.addToStatesUpdateDict(dev.id,u"closestRPI", -1)
									if self.setClostestRPItextToBlank:self.addToStatesUpdateDict(dev.id,u"closestRPIText", "")
								dev.updateStateImageOnServer(indigo.kStateImageSel.SensorOff)
							#else: this is handled in RPI update
							#	 dev.updateStateImageOnServer(indigo.kStateImageSel.Error)

						else:
							if self.beacons[beacon][u"note"].find(u"beacon") > -1:
								dev.updateStateImageOnServer(indigo.kStateImageSel.SensorTripped)
								if u"closestRPI" in dev.states:
									if closestRPI != dev.states[u"closestRPI"]:
										if unicode(dev.states[u"closestRPI"]) != u"-1":
											self.addToStatesUpdateDict(dev.id,u"closestRPILast", dev.states[u"closestRPI"])
											self.addToStatesUpdateDict(dev.id,u"closestRPITextLast", dev.states[u"closestRPIText"])
									self.addToStatesUpdateDict(dev.id,u"closestRPI", -1)
									if self.setClostestRPItextToBlank: self.addToStatesUpdateDict(dev.id,u"closestRPIText", "")
							#else: this is handled in RPI update
							#	 dev.updateStateImageOnServer(indigo.kStateImageSel.Error)

						if beacon in self.CARS[u"beacon"]: 
							self.updateCARS(beacon,dev,self.beacons[beacon])

						if u"showBeaconOnMap" in props and props[u"showBeaconOnMap"] in _GlobalConst_beaconPlotSymbols:self.beaconPositionsUpdated =3

					except Exception, e:
						if unicode(e).find(u"timeout waiting") > -1:
							self.indiLOG.log(40,u"Line {} has error={}".format(sys.exc_traceback.tb_lineno, e))
							self.indiLOG.log(40,u"BeaconsCheckPeriod communication to indigo is interrupted")
							return

				if now.minute != self.lastMinuteChecked:
					try :
						devId = int(self.beacons[beacon][u"indigoId"])
						if devId > 0 :
							try:
								dev = indigo.devices[self.beacons[beacon][u"indigoId"]]
								if self.beacons[beacon][u"ignore"]	 == -1: # was special, device exists now, set back to normal 
									self.indiLOG.log(20,u"BeaconsCheckPeriod minute resetting ignore from -1 to 0 for beacon: {}   beaconDict: {}".format(beacon, self.beacons[beacon]))
									self.beacons[beacon][u"ignore"] = 0
							except Exception, e:
								if unicode(e).find(u"timeout waiting") > -1:
									self.indiLOG.log(40,u"Line {} has error={}".format(sys.exc_traceback.tb_lineno, e))
									self.indiLOG.log(40,u"BeaconsCheckPeriod communication to indigo is interrupted")
									return
								if unicode(e).find(u"not found in database") ==-1:
									self.indiLOG.log(40,u"Line {} has error={}".format(sys.exc_traceback.tb_lineno, e))
									return

								self.indiLOG.log(20,u"=== deleting device beaconDict: " + unicode(self.beacons[beacon]))
								self.beacons[beacon][u"indigoId"] = 0
								self.beacons[beacon][u"ignore"]	  = 1
								dev = ""
								continue

							if dev != "" and dev.states[u"status"] == u"up":
								maxTimeWOutSignal = 330.
								try: 	 maxTimeWOutSignal = max(maxTimeWOutSignal,float(self.beacons[beacon][u"expirationTime"]))
								except: pass

								for piU in _rpiBeaconList:
									piXX = u"Pi_{:02d}".format(int(piU))
									if dev.states[piXX+u"_Distance"] == 99999.: continue
									if dev.states[piXX+u"_Time"] != "":
										piTime = self.getTimetimeFromDateString(dev.states[piXX+u"_Time".format(int(piU))]) 
										if time.time()- piTime> max(maxTimeWOutSignal, self.beacons[beacon][u"updateSignalValuesSeconds"]):
											self.addToStatesUpdateDict(dev.id,piXX+u"_Distance", 99999.,decimalPlaces=1)
									else:
										self.addToStatesUpdateDict(dev.id,piXX+u"_Distance", 99999.,decimalPlaces=1)

					except Exception, e:
						if unicode(e) != u"None":
							self.indiLOG.log(40,u"Line {} has error={}".format(sys.exc_traceback.tb_lineno, e))

				if changed and beacon in self.CARS[u"beacon"]: 
					self.updateCARS(beacon, dev, self.beacons[beacon])

				if dev !="":
					self.executeUpdateStatesDict(onlyDevID=dev.id, calledFrom=u"BeaconsCheckPeriod end")

		except Exception, e:
			if unicode(e) != u"None":
				self.indiLOG.log(40,u"Line {} has error={}".format(sys.exc_traceback.tb_lineno, e))
				try: self.indiLOG.log(40,u"============= {}".format(dev.name))
				except: pass
		return anyChange

####-------------------------------------------------------------------------####
	def checkHour(self,now):
		try:
		
			if now.hour == self.lastHourChecked: return
			if now.hour ==0:
				self.resetMinMaxSensors()
			self.rollOverRainSensors()

			self.fixConfig(checkOnly = [u"all",u"rpi",u"force"],fromPGM=u"checkHour")
			if now.hour ==0 :
				self.checkPiEnabled()

			self.saveCARS(force=True)
			try:
				for beacon in self.beacons:	 # sync with indigo
					if beacon.find(u"00:00:00:00") ==0: continue
					if self.beacons[beacon][u"indigoId"] != 0:	# sync with indigo
						try :
							dev = indigo.devices[self.beacons[beacon][u"indigoId"]]
							if self.beacons[beacon][u"ignore"] == 1:
								self.indiLOG.log(20,u"=== deleting device: {} beacon to be ignored, clean up ".format(dev.name))
								indigo.device.delete(dev)
								continue
							self.beacons[beacon][u"status"] = dev.states[u"status"]
							self.beacons[beacon][u"note"] = dev.states[u"note"]

	 
							if self.removeJunkBeacons:
								if dev.name == u"beacon_" + beacon and self.beacons[beacon][u"status"] == u"expired" and time.time()- self.beacons[beacon][u"lastUp"] > 3600 and self.countLoop > 10 :
									self.indiLOG.log(30,u"=== deleting beacon: {}  expired, no messages for > 1 hour and still old name, if you want to keep beacons, you must rename them after they are created".format(dev.name))
									self.beacons[beacon][u"ignore"] = 1
									self.newIgnoreMAC += 1
									indigo.device.delete(dev)
						except Exception, e:
							if unicode(e) != u"None":
								self.indiLOG.log(40,u"Line {} has error={}".format(sys.exc_traceback.tb_lineno, e))
							if unicode(e).find(u"timeout waiting") >-1:
								self.indiLOG.log(40,u"communication to indigo is interrupted")
								return
							if unicode(e).find(u"not found in database") >-1:
								self.indiLOG.log(40,u"=== deleting mark .. indigoId lookup error, setting to ignore beaconDict: {}".format(self.beacons[beacon]) )
								self.beacons[beacon][u"indigoId"] = 0
								self.beacons[beacon][u"ignore"]   = 1
								self.beacons[beacon][u"status"]   = u"ignored"
							else:
								return

					else :
						self.beacons[beacon][u"status"] = u"ignored"
						if self.beacons[beacon][u"ignore"] == 0:
							self.indiLOG.log(20,u"setting beacon: {}  to ignore --  was set to indigo-id=0 before".format(beacon) )
							self.indiLOG.log(20,u"       contents: {}".format(self.beacons[beacon])  )
							self.beacons[beacon][u"ignore"]	 = 1
							self.newIgnoreMAC 				+= 1
							self.writeJson(self.beacons, fName=self.indigoPreferencesPluginDir + "beacons", fmtOn=self.beaconsFileSort)


			except Exception, e:
				if unicode(e) != u"None":
					self.indiLOG.log(40,u"Line {} has error={}".format(sys.exc_traceback.tb_lineno, e))

			try:
				if now.hour == 0:
					self.deleteAndCeateVariables(True)	# delete and recreate the variables at midnight to remove their sql database entries
					self.setALLrPiV(u"piUpToDate", [u"updateParamsFTP"])
					##self.rPiRestartCommand = ["" for ii in range(_GlobalConst_numberOfRPI)] # dont do this use the default for each pibeacon
					self.setupFilesForPi()
					for piU in self.RPI:
						self.sendFilesToPiFTP(piU, fileToSend=u"updateParamsFTP.exp")
					self.updateRejectLists()
			except Exception, e:
				if unicode(e) != u"None":
					self.indiLOG.log(40,u"Line {} has error={}".format(sys.exc_traceback.tb_lineno, e))
		except Exception, e:
			if unicode(e) != u"None":
				self.indiLOG.log(40,u"Line {} has error={}".format(sys.exc_traceback.tb_lineno, e))

####-------------------------------------------------------------------------####
	def checkDay(self,now):
			# do check once a day at 10 am

		if time.time() <= self.currentlyBooting + 130: return 


		##### first check ibeacons battery updates:
		### get battery status from ibeacon 
		try:
				for ii in range(len(self.checkBatteryLevelHours)):
					if self.lastDayChecked[ii] != now.day and now.hour == self.checkBatteryLevelHours[ii]: 
						self.getBeaconParametersCALLBACKmenu(valuesDict={u"piServerNumber":u"all"}, force=False)
						self.lastDayChecked[ii] = now.day
						return 
		except Exception, e:
			if unicode(e) != u"None":
				self.indiLOG.log(40,u"Line {} has error={}".format(sys.exc_traceback.tb_lineno, e))

		try:
		### report on bad ibeacon battery status
			if self.lastDayChecked[len(self.checkBatteryLevelHours)] != now.day and now.hour == 8:
				badBeacons	= 0
				testBeacons	= 0
				out			= ""
				for dev in indigo.devices.iter(u"props.isBeaconDevice"):
					props = dev.pluginProps
					if u"batteryLevelUUID" not in props: 					continue
					if props[u"batteryLevelUUID"] == u"off":					continue
					if u"batteryLevel" not in dev.states: 					continue
					if u"batteryLevelLastUpdate" not in dev.states: 			continue
					testBeacons += 1
					try: 	batteryLevel = int(dev.states[u"batteryLevel"])	
					except: batteryLevel = 0
					batteryLevelLastUpdate = dev.states[u"batteryLevelLastUpdate"]	
					if len(batteryLevelLastUpdate) < 19: batteryLevelLastUpdate = u"2000-01-01 00:00:00"
					lastTimeStamp = self.getTimetimeFromDateString(batteryLevelLastUpdate)
					#self.indiLOG.log(10,u"  ibeacon: {:30s}  level: {:3d}%,  last update was: {} ".format(dev.name, batteryLevel, batteryLevelLastUpdate) )
					if time.time() - lastTimeStamp > 2*24*3600:
						badBeacons+=1
						out += u"{:35s}last level reported: {:3d}%, has not been updated for > 2 days: {}\n".format(dev.name, batteryLevel, batteryLevelLastUpdate) 
						#trigger  tbi
					elif batteryLevel < 20:
						badBeacons+=1
						out += u"{:35s}      level down to: {:3d}% ... charge or replace battery\n".format(dev.name, batteryLevel) 
						#trigger tbi
				if out != "":
					self.indiLOG.log(30,u"batterylevel level test:\n{}".format(out) )
				elif testBeacons > 0 and badBeacons == 0: self.indiLOG.log(20,u"batterylevel level test:  no iBeacon found with low battery indicator or old update")
				self.lastDayChecked[len(self.checkBatteryLevelHours)] = now.day

		
		except Exception, e:
			if unicode(e) != u"None":
				self.indiLOG.log(40,u"Line {} has error={}".format(sys.exc_traceback.tb_lineno, e))

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
						self.indiLOG.log(20,u"pi# {} is configured but not enabled, mistake? This is checked once a day;  to turn it off set userId or password of unused rPi to empty ".format(piU))
		except Exception, e:
			if unicode(e) != u"None":
				self.indiLOG.log(40,u"Line {} has error={}".format(sys.exc_traceback.tb_lineno, e))

####-------------------------------------------------------------------------####
	def syncSensors(self):
		try:
			anyChange = False
			#ss = time.time()
			for dev in indigo.devices.iter(u"props.isSensorDevice ,props.isOutputDevice"):
				sensor = dev.deviceTypeId
				devId  = dev.id
				props  = dev.pluginProps
				if u"piServerNumber" in props:
					try:
						pi = int(props[u"piServerNumber"])
						piU = unicode(pi)
					except:
						self.indiLOG.log(20,u"device not fully defined, please edit {} pi# not defined:  {}".format(dev.name, unicode(props)))
						continue

					if self.checkDevToPi(piU, devId, dev.name, u"input",  u"in",  sensor, _GlobalConst_allowedSensors + _BLEsensorTypes): anyChange= True
					#indigo.server.log(u"syncSensors A01: "+ unicode(anyChange)+u"  "+ unicode(time.time() - ss))
					if self.checkDevToPi(piU, devId, dev.name, u"output", u"out", sensor, _GlobalConst_allowedOUTPUT):  anyChange= True

				if u"description" in props and	props[u"description"] !="" and props[u"description"] != dev.description:
					dev.description =  props[u"description"] 
					dev.replaceOnServer()
					anyChange = True
			#indigo.server.log(u"syncSensors AT: "+ unicode(anyChange)+u"  "+ unicode(time.time() - ss))

			for piU in self.RPI:
				self.checkSensortoPi(piU, u"input")
				self.checkSensortoPi(piU, u"output")
				if self.mkSensorList(piU): anyChange =True
			#indigo.server.log(u"syncSensors BT: "+ unicode(anyChange)+u"  "+ unicode(time.time() - ss))

		except Exception, e:
			if unicode(e) != u"None":
				self.indiLOG.log(40,u"Line {} has error={}".format(sys.exc_traceback.tb_lineno, e))
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

					self.indiLOG.log(40,u"Line {} has error={}".format(sys.exc_traceback.tb_lineno, e))
					if unicode(e).find(u"timeout waiting") > -1:
						self.indiLOG.log(40,u"communication to indigo is interrupted")
						return False
					if unicode(e).find(u"not found in database") ==-1:
						return False
					name=""
				self.indiLOG.log(20,u"fixing 1  {}   {} pi {}; sensor: {} devName: {}".format(name, devId, piU, sensor, name) )
				self.indiLOG.log(20,u"fixing 1  rpi {}".format(self.RPI[piU][io]))
				self.RPI[piU][io][sensor] = {unicode(devId): ""}
				self.setONErPiV(piU,u"piUpToDate", [u"updateParamsFTP"])
				anyChange = True
			if len(self.RPI[piU][io][sensor]) == 0:
				self.RPI[piU][io][sensor] = {unicode(devId): ""}
				anyChange = True

			elif unicode(devId) not in self.RPI[piU][io][sensor]:
				self.indiLOG.log(20,u"fixing 2  {}   {}  pi {} sensor{}".format(name, devId, piU, sensor) )
				self.RPI[piU][io][sensor][unicode(devId)] = ""
				anyChange = True
		except Exception, e:
			if unicode(e) != u"None":
				self.indiLOG.log(40,u"Line {} has error={}".format(sys.exc_traceback.tb_lineno, e))
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
									self.indiLOG.log(40,u"Line {} has error={}".format(sys.exc_traceback.tb_lineno, e))
									self.indiLOG.log(40,u"communication to indigo is interrupted")
									return True
								if unicode(e).find(u" not found in database") ==-1:
									self.indiLOG.log(40,u"Line {} has error={}".format(sys.exc_traceback.tb_lineno, e))
									return True

								deldevID[devIDrpi] = 1
								self.indiLOG.log(40,u"device not found in indigo DB, ok if device was just deleted")
								self.indiLOG.log(40,u"removing input device from parameters for pi#:{}  devID={}".format(piU, devIDrpi))
								anyChange = True
								continue


							props = dev.pluginProps
							if u"rPiEnable"+piU not in props and  u"piServerNumber" not in props:
								self.indiLOG.log(20,u"piServerNumber not in props for pi#: {}  devID= {}   removing sensor{}".format(piU, devID, self.RPI[piU][io][sensor]) )
								self.RPI[piU][io][sensor] = {}
								anyChange = True
								continue

							if u"piServerNumber" in props:
								if sensor != dev.deviceTypeId or devID != dev.id or piU != props[u"piServerNumber"]:
									self.indiLOG.log(20,u"sensor/devid/pi/wrong for  pi#: {}  devID= {} props{}\n >>>>> removing sensor <<<<".format(piU, self.RPI[piU][io][sensor], unicode(props)) )
									self.RPI[piU][io][sensor] = {}
									anyChange = True
								if dev.deviceTypeId  not in _BLEsensorTypes:
									if u"address" in props:
										if props[u"address"] != u"Pi-" + piU:
											props[u"address"] = u"Pi-" + piU
											if self.decideMyLog(u"Logic"): self.indiLOG.log(10,u"updating address for {}".format(piU) )
											self.deviceStopCommIgnore = time.time()
											dev.replacePluginPropsOnServer(props)
											anyChange = True
									else:
										props[u"address"] = u"Pi-" + piU
										self.deviceStopCommIgnore = time.time()
										dev.replacePluginPropsOnServer(props)
										if self.decideMyLog(u"Logic"): self.indiLOG.log(10,u"updating address for {}".format(piU) )
										anyChange = True
							else:
								pass

						except Exception, e:
							self.indiLOG.log(40,u"Line {} has error={}".format(sys.exc_traceback.tb_lineno, e))
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
			if unicode(e) != u"None":
				self.indiLOG.log(40,u"Line {} has error={}".format(sys.exc_traceback.tb_lineno, e))
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
								xxx = unicode(dev.states[ttx]).split(u".")
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
							self.executeUpdateStatesDict(onlyDevID=dev.id, calledFrom=u"resetMinMaxSensors")
		except Exception, e:
			if unicode(e) != u"None":
				self.indiLOG.log(40,u"Line {} has error={}".format(sys.exc_traceback.tb_lineno, e))

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
			if unicode(e) != u"None":
				self.indiLOG.log(40,u"Line {} has error={}".format(sys.exc_traceback.tb_lineno, e))

####----------------------reset rain sensor every hour/day/week/month/year -----------------------------------####
	def rollOverRainSensors(self):
		try:
			dd = datetime.datetime.now()
			currDate = (dd.strftime(u"%Y-%m-%d-%H")).split(u"-")
			weekNumber = dd.isocalendar()[1]

			#self.indiLOG.log(20,	u"currDate: " +unicode(currDate), mType="rollOverRainSensors")
			for dev in indigo.devices.iter(u"props.isSensorDevice"):
				if dev.deviceTypeId.find(u"rainSensorRG11") == -1: continue
				if	not dev.enabled: continue
				props = dev.pluginProps
				lastTest = props[u"lastDateCheck"].split(u"-")
				try:
					ff = datetime.datetime.strptime(props[u"lastDateCheck"], "%Y-%m-%d-%H")
					lastweek = ff.isocalendar()[1]
				except:
					lastweek = -1

				#self.indiLOG.log(20,	u"lasttest: " +unicode(lastTest), mType="rollOverRainSensors")
				for test in [u"hour",u"day",u"week",u"month",u"year"]:
					if test == u"hour"	and int(lastTest[3]) == int(currDate[3]): continue
					if test == u"day"	and int(lastTest[2]) == int(currDate[2]): continue
					if test == u"month"	and int(lastTest[1]) == int(currDate[1]): continue
					if test == u"year"	and int(lastTest[0]) == int(currDate[0]): continue
					if test == u"week"	and lastweek		 == weekNumber:		  continue
					ttx = test+u"Rain"
					val = dev.states[ttx]
					#self.indiLOG.log(20,	u"rolling over: " +unicode(ttx)+";  using current val: "+ unicode(val), mType="rollOverRainSensors")
					self.addToStatesUpdateDict(dev.id,u"last"+ttx, val,decimalPlaces=self.rainDigits)
					self.addToStatesUpdateDict(dev.id,ttx, 0,decimalPlaces=self.rainDigits)
					try:	 props[test+u"RainTotal"]  = float(dev.states[u"totalRain"])
					except:	 props[test+u"RainTotal"]  = 0
				props[u"lastDateCheck"] = dd.strftime(u"%Y-%m-%d-%H")
				self.deviceStopCommIgnore = time.time()
				dev.replacePluginPropsOnServer(props)
				self.executeUpdateStatesDict(onlyDevID=dev.id, calledFrom=u"rollOverRainSensors")
		except Exception, e:
			if unicode(e) != u"None":
				self.indiLOG.log(40,u"Line {} has error={}".format(sys.exc_traceback.tb_lineno, e))


####-------------------------------------------------------------------------####
	def mkSensorList(self, pi):
		try:
			anyChange = False
			sensorList = ""
			INPgpioTypes = []
			piU = unicode(pi)
			for sensor in self.RPI[piU][u"input"]:
				if sensor not in _GlobalConst_allowedSensors and sensor not in _BLEsensorTypes: continue
				if sensor ==u"ultrasoundDistance": continue
				try:
					#					 devId= int(self.RPI[piU][u"input"][sensor].keys()[0])# we only need the first one
					for devIds in self.RPI[piU][u"input"][sensor]:
						devId = int(devIds)
						if devId < 1: 1 / 0
						dev = indigo.devices[devId]
						props = dev.pluginProps
						if dev.enabled:
							sensorList += sensor+u"*"+unicode(devId)	 # added; below only works if just one BLE if several and only one gets disabled it is still present, hence we need to add extra
							if u"i2cAddress" in props:
								sensorList+= u"*"+props[u"i2cAddress"]
							if u"spiAddress" in props:
								sensorList+= u"*"+props[u"spiAddress"]
							if u"gpioPin" in props:
								sensorList+= u"*"+props[u"gpioPin"]
							if u"resModel" in props:
								sensorList+= u"*"+props[u"resModel"]
							if u"gain" in props:
								sensorList+= u"*"+props[u"gain"]
							sensorList+=u","

				except Exception, e:
					self.indiLOG.log(40,u"Line {} has error={}".format(sys.exc_traceback.tb_lineno, e))
					if unicode(e).find(u"timeout waiting") > -1:
						self.indiLOG.log(40,u"communication to indigo is interrupted")
						return
					if unicode(e).find(u"not found in database") ==-1:
						return
					self.RPI[piU][u"input"][sensor] = {}
			if sensorList != self.RPI[piU][u"sensorList"]:
				self.setONErPiV(piU,u"piUpToDate", [u"updateParamsFTP"])
				anyChange = True
			self.RPI[piU][u"sensorList"] = sensorList

		except Exception, e:
			if unicode(e) != u"None":
				self.indiLOG.log(40,u"Line {} has error={}".format(sys.exc_traceback.tb_lineno, e))
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
			if unicode(e) != u"None":
				self.indiLOG.log(40,u"Line {} has error={}".format(sys.exc_traceback.tb_lineno, e))
			self.indiLOG.log(40,newVar.value)


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
				self.indiLOG.log(20,u"bad data  Pi not integer:  {}".format(varNameIN) )
				return

			if self.trackRPImessages == pi:
				self.indiLOG.log(20,u"pi# {} msg tracking: {} ".format(piU, varUnicode ) )

			if piU not in _rpiList:
				self.indiLOG.log(20,u"pi# rejected outside range:  {}".format(varNameIN) )
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
				if u"BLEconnect" in varJson[u"sensors"]:
					self.BLEconnectupdateAll(piU, varJson[u"sensors"])
				self.updateSensors(piU, varJson[u"sensors"])

			# print BLE report 
			if  u"trackMac" in varJson:
				#self.indiLOG.log(30,varNameIN+u"  " + varUnicode[0:100])
				self.printtrackMac(piU, varJson[u"trackMac"])


			# print BLE report 
			if  u"BLEAnalysis" in varJson:
				#self.indiLOG.log(30,varNameIN+u"  " + varUnicode[0:100])
				self.printBLEAnalysis(piU, varJson[u"BLEAnalysis"])

			##
			# update outputState
			if u"outputs" in varJson:
				self.updateOutput(piU, varJson[u"outputs"])

			##
			if u"BLEreport" in varJson: 
				self.printBLEreport(varJson[u"BLEreport"])
				return 

			##
			if u"i2c" in varJson:
				self.checkI2c(piU, varJson[u"i2c"])

			##
			if u"bluetooth" in varJson:
				self.checkBlueTooth(piU, varJson[u"bluetooth"])

			self.findClosestiBeaconToRPI(piU, beaconUpdatedIds=beaconUpdatedIds, BeaconOrBLE="beacon")
			self.executeUpdateStatesDict(calledFrom=u"addToDataQueue")


		except Exception, e:
			if unicode(e) != u"None":
				self.indiLOG.log(40,u"Line {} has error={}".format(sys.exc_traceback.tb_lineno, e))
			self.indiLOG.log(40,varNameIN+u"  " + varUnicode[0:30])


####-------------------------------------------------------------------------####
	def workOnQueue(self):

		beaconUpdatedIds =[]
		self.queueActive  = True
		while not self.messagesQueue.empty():
			item = self.messagesQueue.get() 
			for ii in range(40):
				if self.queueList ==u"update" : break
				if self.queueList ==""		  : break
				if ii > 0:	pass
				time.sleep(0.05)
			self.queueList = u"update"  
			beaconUpdatedIds += self.execUpdate(item[0],item[1],item[2],item[3])
			#### indigo.server.log(unicode(item[1])+u"  "+ unicode(beaconUpdatedIds)+u" "+ item[3])
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
						self.indiLOG.log(20,u"sel.beacon logging: RPI MAC#:{} ; pi#={} ".format(piMAC, piU) )

			if u"piMAC" in data:
				if self.decideMyLog(u"BeaconData"): self.indiLOG.log(10,u"new iBeacon message----------------------------------- \n {}".format(varUnicode) )
				secondsCollected = 0
				if u"secsCol" in data:
					secondsCollected = data[u"secsCol"]
				msgs = data[u"msgs"]
				if len(msgs) > 0 and piMAC != "":
					if u"ipAddress" in data:
						ipAddress = data[u"ipAddress"]
						if self.RPI[piU][u"ipNumberPi"] != "" and self.RPI[piU][u"ipNumberPi"] != ipAddress:
							if ipAddress == "":
								self.setONErPiV(piU,u"piUpToDate", [u"updateParamsFTP",u"rebootSSH"])
								self.indiLOG.log(30,u"rPi#: {}  ip# send from rPi is empty, you should restart rPi, ip# should be {}".format(piU, self.RPI[piU][u"ipNumberPi"] ))
								return beaconUpdatedIds
							else:
								self.indiLOG.log(30,u"rPi#:{} {}: IP number has changed to {}, please fix in menue/pibeacon/setup RPI to reflect changed IP number or fix IP# on RPI\n this can happen when WiFi and ethernet are both active, try setting wlan/eth parameters in RPI device edit;  ==> ignoring data".format(piU, self.RPI[piU][u"ipNumberPi"], ipAddress ))
								return beaconUpdatedIds
					else:
						return beaconUpdatedIds

					beaconUpdatedIds = self.updateBeaconStates(piU, piN, ipAddress, piMAC, secondsCollected, msgs)
					self.RPI[piU][u"emptyMessages"] = 0
				elif len(msgs) == 0 and piMAC != "":
					self.RPI[piU][u"emptyMessages"] +=1
					if	self.RPI[piU][u"emptyMessages"] >  min(self.enableRebootRPIifNoMessages,10) :
						if	self.RPI[piU][u"emptyMessages"] %5 ==0:
							self.indiLOG.log(20,u"RPI# {} check , too many empty messages in a row: {}".format(piU, self.RPI[piU][u"emptyMessages"]) )
							self.indiLOG.log(20,u" please check RPI" )
						if	self.RPI[piU][u"emptyMessages"] > self.enableRebootRPIifNoMessages:
							self.indiLOG.log(30,u"RPI# {} check , too many empty messages in a row: {}".format(piU, self.RPI[piU][u"emptyMessages"]) )
							self.indiLOG.log(30,u"sending reboot command to RPI")
							self.setONErPiV(piU,u"piUpToDate",[u"updateParamsFTP",u"rebootSSH"])
							self.RPI[piU][u"emptyMessages"] = 0

		except Exception, e:
			if unicode(e) != u"None":
				self.indiLOG.log(40,u"Line {} has error={}".format(sys.exc_traceback.tb_lineno, e))
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
			
			rpiDev = indigo.devices[self.RPI[piU][u"piDevId"]]
			if u"closestiBeacon" not in rpiDev.states:		return 

			rpiProps = rpiDev.pluginProps
			cutOffForClosestBeacon = 300
			if u"cutOffForClosestBeacon" in rpiProps:
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
				if u"isRPIDevice" 		in props:															continue
				if u"isRPISensorDevice"	in props:															continue
				if u"IgnoreBeaconForClosestToRPI" in props and props[u"IgnoreBeaconForClosestToRPI"] !="0":	continue



				try: 
					if dist  < closestDist:
						closestDist = dist
						closestName = dev.name
				except Exception, e:
					self.indiLOG.log(40,u"Line {} has error={}".format(sys.exc_traceback.tb_lineno, e))
					
			if closestDist < cutOffForClosestBeacon:
					cN = closestName+u"@"+unicode(closestDist)
					if rpiDev.states[u"closestiBeacon"] !=cN:
						self.addToStatesUpdateDict(unicode(rpiDev.id),u"closestiBeacon", cN)
						self.addToStatesUpdateDict(unicode(rpiDev.id),u"closestiBeaconLast", rpiDev.states[u"closestiBeacon"])
			else:
				if rpiDev.states[u"closestiBeacon"] != u"None":
					self.addToStatesUpdateDict(unicode(rpiDev.id), u"closestiBeacon", u"None")
					
					 
		except Exception, e:
			if unicode(e) != u"None":
				self.indiLOG.log(40,u"Line {} has error={}".format(sys.exc_traceback.tb_lineno, e))


####-------------------------------------------------------------------------####
	def checkincomingMACNo(self, data, pi, timeStampOfReceive):

		piU = unicode(pi)
		piMAC = ""
		piN   = -1
		try:

			if u"piMAC" in data:
				piMAC = unicode(data[u"piMAC"])
			if piMAC == u"0" or piMAC == "": 
				return False, "", ""

			#if str(pi) =="9": self.indiLOG.log(20,u"receiving: pi "+piU+u"  piMAC:" + piMAC)
			piN = int(data[u"pi"])
			piNU = unicode(piN)
			if piNU not in _rpiList :
				if self.decideMyLog(u"all"): self.indiLOG.log(10,u"bad data  Pi# not in range: {}".format(piNU))
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
					self.indiLOG.log(20,u"MAC# from RPI message, has new MAC# {} changing to new BLE-MAC number, old MAC#{}--  pi# {}".format(piMAC, beacon, piU) )
					beacon = piMAC
				if len(beacon) == 17: ## len(u"11:22:33:44:55:66")
						indigoId = int(self.RPI[piU][u"piDevId"])
						if len(self.RPI[piU][u"piMAC"]) != 17 or indigoId == 0:
							self.indiLOG.log(10,u"MAC# from RPI message is new {} not in internal list .. new RPI?{}".format(beacon, piU))

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
									if self.decideMyLog(u"Logic"): self.indiLOG.log(10,u"MAC# from RPI  was updated")
								except Exception, e:
									self.indiLOG.log(40,u"Line {} has error={}".format(sys.exc_traceback.tb_lineno, e))
									if self.decideMyLog(u"Logic"): self.indiLOG.log(10,u"MAC# from RPI...	 indigoId: {} does not exist, ignoring".format(indigoId) )

						# added to cover situation when RPI was set to expire by mistake ==>  reset it to ok
						if beacon in self.beacons: 
							if self.beacons[beacon][u"ignore"] > 0: self.beacons[beacon][u"ignore"] = 0
							self.beacons[beacon][u"lastUp"] = time.time()

		except Exception, e:
			if unicode(e) != u"None":
				self.indiLOG.log(40,u"Line {} has error={}".format(sys.exc_traceback.tb_lineno, e))
			return False, "", ""

		return True, piMAC, piNU



####-------------------------------------------------------------------------####
	def compareRpiTime(self, data, pi, devPI, timeStampOfReceive):
		piU = unicode(pi)
		pi = int(pi)
		dt = time.time() - timeStampOfReceive
		if dt > 4.: self.indiLOG.log(10,u"significant internal delay occured digesting data from rPi:{}    {:.1f} [secs]".format(piU, dt) )
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
					self.indiLOG.log(20,u"rPi "+piU+u" wrong time zone: " + tz + u"    vs "+ tzMAC+u"    on MAC ")
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
								self.actionList.append({u"action":"setTime",u"value":piU})
								self.indiLOG.log(20,u"rPi {} do a time sync MAC --> RPI, time off by: {5.1f}[secs]".format(piU, time.time()-ts) )
					except: pass


			if tz != tzMAC or (abs(deltaT) > 100):
				# do not check time / time zone if disabled 
					self.timeErrorCount[pi] +=1
					if self.timeErrorCount[pi]	 < 3:
						try:	  deltaT = u"{}".format(deltaT)
						except:	  deltaT = u"{:.0f} - {}".format(time.time, ts)
						self.indiLOG.log(20,u"please do \"sudo raspi-config\" on rPi: {}, set time, reboot ...      send: TIME-Tsend= {}      /epoch seconds UTC/  timestamp send= {}; TZ send is={}".format(piU, deltaT, ts, tz) )

			if (abs(time.time()-float(ts)) < 2. and tz == tzMAC)  or self.timeErrorCount[pi] > 1000:
				self.timeErrorCount[pi] = 0

		except Exception, e:
			if unicode(e).find(u"timeout waiting") > -1:
				self.indiLOG.log(40,u"communication to indigo is interrupted")
			self.indiLOG.log(40,u"Line {} has error={}".format(sys.exc_traceback.tb_lineno, e))
		return


####-------------------------------------------------------------------------####
	def printBLEreport(self, BLEreport):
		try:
			self.indiLOG.log(20,u"BLEreport received:")
			for rep in BLEreport:
					self.indiLOG.log(20,u"=======================================\n"+BLEreport[rep][0].strip(u"\n"))
					if len(BLEreport[rep][1]) < 5:
						self.indiLOG.log(20,u"no errors")
					else:
						self.indiLOG.log(20,u"errors:\n"+BLEreport[rep][1].strip(u"\n"))
		except Exception, e:
			if unicode(e) != u"None":
				self.indiLOG.log(40,u"Line {} has error={}".format(sys.exc_traceback.tb_lineno, e))


####-------------------------------------------------------------------------####
	def printtrackMac(self, piU, report):
		name = ""
		try:
			out = u"\ntrackMac report received  from RPI#:{}\n".format( piU)
			out += report.replace(u";;",u"\n")
			self.myLog(text= out)
		except Exception, e:
			if unicode(e) != u"None":
				self.indiLOG.log(40,u"Line {} has error={}".format(sys.exc_traceback.tb_lineno, e))




####-------------------------------------------------------------------------####
	def printBLEAnalysis(self, piU, report):
		name = ""
		try:
			out = u"\n\nBLEAnalysis received for beacons with signal (rssi) > {}; from RPI#:{}".format(report[u"rssiCutoff"], piU)
			#self.indiLOG.log(20,u"BLEAnalysis :{}".format(report))
			for existing in [u"new_Beacons",u"existing_Beacons",u"rejected_Beacons"]:
				out+= u"\n================================ {} ============================================".format(existing)
				rr = report[existing]
				for mac in rr:
					name = ""
					if mac in self.beacons and self.beacons[mac][u"indigoId"] >0:
						try:	name = u"-"+indigo.devices[int(self.beacons[mac][u"indigoId"])].name
						except:	pass

					if existing == u"rejected_Beacons":
						out += u"\n===MAC# "+mac+u"  "+name+u" == {}\n".format(rr[mac])
						
					else:
						out += u"\n===MAC# "+mac+u"  "+name+u" == ; raw data:\n"
						for item in [u"n_of_MSG_Types", "raw_data",u"mfg_info",u"iBeacon",u"MSG_in_10Secs",u"typeOfBeacon",u"max_rssi",u"max_TX",u"pos_of_reverse_MAC_in_UUID",u"pos_of_MAC_in_UUID",u"possible_knownTag_options"]:
							if item not in rr[mac]:
								out += u"missing: "+item+u"\n"
								continue
							if item == u"raw_data":
								out += u"raw data:\n"
								for ii in rr[mac][item]:
									out+= u"- {}\n".format(ii)
							elif item == u"possible_knownTag_options":
								out += u"possible knownTag options:\n"
								for ii in rr[mac][item]:
									out+= u"-- {}\n".format(ii)
							else:
								out += u"{:28s}: {}\n".format(item, rr[mac][item])
			self.myLog(text= out)
		except Exception, e:
			if unicode(e) != u"None":
				self.indiLOG.log(40,u"Line {} has error={}".format(sys.exc_traceback.tb_lineno, e))
			self.myLog(text= out)
			indigo.server.log(u"printBLEAnalysis :{}".format(report))

####-------------------------------------------------------------------------####
	def checkI2c(self, piU, i2c):
		try:
			for i2cChannel in i2c:
				if i2cChannel is not None:
					if i2cChannel.find(u"i2c.ERROR:.no.such.file....redo..SSD?") > -1 :
						self.indiLOG.log(20,u" pi#{}  has bad i2c config. you might need to replace SSD".format(piU))
		except:
			pass


####-------------------------------------------------------------------------####
	def checkBlueTooth(self, piU, blueTooth):
		try:
			if blueTooth is not None:
				if blueTooth.find(u"startup.ERROR:...SSD.damaged?") > -1 :
					self.indiLOG.log(30,u" pi#{} bluetooth did not startup. you might need to replace SSD".format(piU))
		except:
			pass


####-------------------------------------------------------------------------####
	def updateAlive(self, varJson,varUnicode,  timeStampOfReceive):
		if u"pi" not in varJson : return 
		try:
			if self.decideMyLog(u"DevMgmt"):	 self.indiLOG.log(20,u"rPi alive message :  {}".format(varUnicode))
			if (varUnicode).find(u"_dump_") >-1: 
				self.indiLOG.log(40,u"rPi error message: Please check that RPI  you might need to replace SD")
				self.indiLOG.log(40,varUnicode)
				return 
			if (varUnicode).find(u"data may be corrupt") >-1: 
				self.indiLOG.log(30,u"rPi error message: >>dosfsck has error: data may be corrupt<<<   Please check that RPI  you might need to replace SD")
				self.indiLOG.log(30,varUnicode)
				return 
			pi = int(varJson[u"pi"])
			piU = unicode(pi)
			if piU not in _rpiList:
				self.indiLOG.log(20,u"pi# out of range:  {}".format(varUnicode))
				return

			if self.trackRPImessages  == pi:
				self.indiLOG.log(20,u"pi# {} msg tracking:  {}".format(piU,varUnicode))

			self.RPI[piU][u"lastMessage"] = time.time()

			if u"reboot" in varJson:
				self.setRPIonline(piU,new="reboot")
				indigo.variable.updateValue(self.ibeaconNameDefault+u"Rebooting",u"reset from :"+piU+u" at "+datetime.datetime.now().strftime(_defaultDateStampFormat))
				if u"text" in varJson and varJson[u"text"].find(u"bluetooth_startup.ERROR:") >-1:
					self.indiLOG.log(20,u"RPI# "+piU+ " "+varJson[u"text"]+u" Please check that RPI ")
				return

			try:
				dev = indigo.devices[self.RPI[piU][u"piDevId"]]
			except Exception, e:

				if unicode(e).find(u"timeout waiting") > -1:
					self.indiLOG.log(40,u"Line {} has error={}".format(sys.exc_traceback.tb_lineno, e))
					self.indiLOG.log(40,u"communication to indigo is interrupted")
					return
				if unicode(e).find(u"not found in database") ==-1:
					self.indiLOG.log(40,u"Line {} has error={}".format(sys.exc_traceback.tb_lineno, e))
					return
				self.RPI[piU][u"piDevId"]=0
				return
			self.compareRpiTime(varJson,piU,dev, timeStampOfReceive)
			self.setRPIonline(piU)


			self.updateStateIf(piU, dev, varJson, u"sensors_active")
			self.updateStateIf(piU, dev, varJson, u"i2c_active")
			self.updateStateIf(piU, dev, varJson, u"rpi_type")
			self.updateStateIf(piU, dev, varJson, u"fan_OnTime_Percent", decimalPlaces=0)
			self.updateStateIf(piU, dev, varJson, u"op_sys")
			self.updateStateIf(piU, dev, varJson, u"last_boot")
			self.updateStateIf(piU, dev, varJson, u"last_masterStart")
			self.updateStateIf(piU, dev, varJson, u"RPI_throttled")
			self.updateStateIf(piU, dev, varJson, u"temp", deviceStateName="Temperature")

			if u"i2cError" in varJson:
				self.indiLOG.log(30,u"RPi# {} has i2c error, not found in i2cdetect {}".format(piU,varJson[u"i2cError"]) )

			dev.updateStateImageOnServer(indigo.kStateImageSel.SensorOn)
			if dev.states[u"status"] != u"up" :
				self.addToStatesUpdateDict(dev.id,u"status", u"up")

			if dev.states[u"online"] != u"up":
				self.addToStatesUpdateDict(dev.id,u"online", u"up")

			if pi < _GlobalConst_numberOfiBeaconRPI:
				if self.RPI[piU][u"piMAC"] in self.beacons:
					self.beacons[self.RPI[piU][u"piMAC"]][u"lastUp"] = time.time()

			self.executeUpdateStatesDict(onlyDevID=dev.id, calledFrom=u"addToDataQueue pi_IN_Alive")

		except Exception, e:
			if unicode(e).find(u"timeout waiting") > -1:
				self.indiLOG.log(40,u"Line {} has error={}".format(sys.exc_traceback.tb_lineno, e))
				self.indiLOG.log(40,u"communication to indigo is interrupted")
				return
			if unicode(e) != u"None":
				self.indiLOG.log(40,u"Line {} has error={}".format(sys.exc_traceback.tb_lineno, e))
				self.indiLOG.log(40,u"variable pi_IN_Alive wrong format: " + varUnicode+u" you need to push new upgrade to rPi")

		return


####-------------------------------------------------------------------------####
	def updateStateIf(self, piU, dev, varJson, stateName, deviceStateName="", makeString=False, decimalPlaces=1 ):

		try:
			if deviceStateName == "": deviceStateName = stateName
			if stateName in varJson:
				###self.indiLOG.log(20,u"updateStateIf : "+statename+u"  "+ unicode(varJson[statename]))
				if deviceStateName == u"Temperature": 
					x, UI, decimalPlaces, useFormat = self.convTemp(varJson[stateName])
				elif makeString:
					x  = varJson[stateName].strip(u"{").strip(u"}")
					UI = x
					decimalPlaces = 0
				else: 
					x, UI, decimalPlaces  =  varJson[stateName], varJson[stateName], decimalPlaces

				if deviceStateName =="RPI_throttled": 
					old = dev.states[deviceStateName] 
					if old != x:
						if x != u"none" and x != "" and x != u"no_problem_detected":
							self.indiLOG.log(40,u"RPi# {} has power state has problem   new:>>{}<<, previous:{}".format(piU, x, old) )
						if x == u"none" or x == u"no_problem_detected":
							self.indiLOG.log(40,u"RPi# {} has power state has recovered  new:>>{}<<, previous:{}".format(piU, x, old) )

				self.setStatusCol( dev, deviceStateName, x, UI, "", "",{})
				return x
		except Exception, e:
				self.indiLOG.log(40,u"Line {} has error={}".format(sys.exc_traceback.tb_lineno, e))
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
					self.delRPI(pi=pi, calledFrom=u"setRPIonline")
					return 

			if setLastMessage:
				self.addToStatesUpdateDict(dev.id,u"last_MessageFromRpi", datetime.datetime.now().strftime(_defaultDateStampFormat))
		

			if new==u"up":
				#self.addToStatesUpdateDict(dev.id,u"lastMessage", now)
				dev.updateStateImageOnServer(indigo.kStateImageSel.SensorOn)
				if u"status" in dev.states and dev.states[u"status"] != u"up":
					self.addToStatesUpdateDict(unicode(devID),u"status", u"up")
				if u"online" in dev.states and dev.states[u"online"] != u"up":
					self.addToStatesUpdateDict(dev.id,u"online", u"up")
				return
			if new == u"reboot":
				#self.addToStatesUpdateDict(dev.id,u"lastMessage", now)
				if dev.states[u"online"] != u"reboot":
					dev.updateStateImageOnServer(indigo.kStateImageSel.SensorOff)
					self.addToStatesUpdateDict(dev.id,u"online", u"reboot")
					self.setCurrentlyBooting(self.bootWaitTime, setBy=u"setting status of pi# "+piU+u"   to reboot  or until new message arrives")
					if piU not in _rpiBeaconList: 
						self.addToStatesUpdateDict(dev.id,u"status", u"reboot")
					return
			if new == u"offline":
				if dev.states[u"online"] != u"down":
					#dev.updateStateImageOnServer(indigo.kStateImageSel.SensorOff)
					self.addToStatesUpdateDict(dev.id,u"online", u"down")
					if piU in _rpiSensorList: 
						self.addToStatesUpdateDict(dev.id,u"status", u"down")
					return



		except Exception, e:
			if unicode(e).find(u"timeout waiting") > -1:
				self.indiLOG.log(40,u"Line {} has error={}".format(sys.exc_traceback.tb_lineno, e))
				self.indiLOG.log(40,u"communication to indigo is interrupted")
				return
			if unicode(e) != u"None":
				self.indiLOG.log(40,u"Line {} has error={}".format(sys.exc_traceback.tb_lineno, e))
				self.indiLOG.log(40,u" pi" + piU+u"  RPI"+ unicode(self.RPI[piU]) )
		return
####-------------------------------------------------------------------------####
	def checkSensorPiSetup(self, piSend, data, piNReceived):

		try:
			#self.indiLOG.log(20,	u"called checkSensorPiSetup")
			if piSend != piNReceived:
				self.indiLOG.log(20,u"sensor pi " + piSend + u" wrong pi# "+piNReceived+u" number please fix in setup rPi")
				return -1
			if u"ipAddress" in data:
				if self.RPI[piSend][u"ipNumberPi"] != data[u"ipAddress"]:
					self.indiLOG.log(20,u"sensor pi " + piSend + u" wrong IP number please fix in setup rPi, received: -->" +data[u"ipAddress"]+u"<-- if it is empty a rPi reboot might solve it")
					return -1
			devId = self.RPI[piSend][u"piDevId"]
			Found= False
			try:
				dev= indigo.devices[devId]
				Found =True
			except Exception, e:
			   
				self.indiLOG.log(40,u"Line {} has error={}".format(sys.exc_traceback.tb_lineno, e))
				if unicode(e).find(u"timeout waiting") > -1:
					self.indiLOG.log(40,u"communication to indigo is interrupted")
					return -1

			if not Found:
				self.indiLOG.log(20,u"sensor pi " + piSend + u"- devId: " + unicode(devId) +u" not found, please configure the rPi:  "+ unicode(self.RPI[piSend]))
			if Found:
				if dev.states[u"status"] != u"up":
						self.addToStatesUpdateDict(dev.id,u"status",u"up")
						dev.updateStateImageOnServer(indigo.kStateImageSel.SensorOn)
				if dev.states[u"online"] != u"up":
						self.addToStatesUpdateDict(dev.id,u"online",u"up")
						dev.updateStateImageOnServer(indigo.kStateImageSel.SensorOn)

		except Exception, e:
			if unicode(e) != u"None":
				self.indiLOG.log(40,u"Line {} has error={}".format(sys.exc_traceback.tb_lineno, e))
				self.indiLOG.log(40,unicode(data))
		return 0



####-------------------------------------------------------------------------####
	## as we accumulate changes , dev.states does not contain the latest. check update list and if not there then check dev.states
	def getCurrentState(self, dev, devIds, state, fromMETHOD=""):
		try:
			if devIds in self.updateStatesDict and state in self.updateStatesDict[devIds]:
				return self.updateStatesDict[devIds][state][u"value"] 
			else:  
				return dev.states[state] 

		except Exception, e1:
			try:  # rare case that updateStatesDict has been updated and clear whil we do this, then take new dev.state happens ~ 1/week with MANY devices
				#self.indiLOG.log(10,u"in Line {} has error(s) ={}, getCurrentState not in dyn list, trying to use indigo state... " .format(sys.exc_traceback.tb_lineno, e1))
				ret =  indigo.devices[dev.id].states[state] 
				#self.indiLOG.log(10,u"...  was fixed using indigo states")
				return ret
			except Exception, e:
				self.indiLOG.log(40,u"in Line {} has error(s) ={} {}".format(sys.exc_traceback.tb_lineno, e, e1))
				self.indiLOG.log(40,u"  .. called from= {};  state= {};  updateStatesDict= {}".format(fromMETHOD, state, self.updateStatesDict) )
				try:	self.indiLOG.log(40,u"  .. dev= {}".format(dev.name) )
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
	def calcPostion(self, dev, expirationTime, rssi=""): ## add Signal time dist status
		try:
			devID			= dev.id
			name			= dev.name
			devIds			= unicode(dev.id)
			deltaDistance	= 0.
			status			= u"expired"
			distanceToRpi	 = []
			pitimeNearest	= u"1900-00-00 00:00:00"
			lastUp			= 0
			lastUpS			= ""
			update			= False
			#if devID ==78067927: self.indiLOG.log(10,u"dist  "+ dev.name)
			lastStatusChangeDT = 99999
			try:
				if u"lastUp" in dev.states: 
					lastUp =  self.getTimetimeFromDateString(self.getCurrentState(dev,devIds,"lastUp", fromMETHOD="calcPostion1"))

			except Exception, e:
				self.indiLOG.log(40,u"Line {} has error={}".format(sys.exc_traceback.tb_lineno, e))
				lastUp	= 0

			if dev.deviceTypeId == u"BLEconnect":
				activePis = self.getActiveBLERPI(dev)
				lastBusy = 0
			else:
				activePis = range(_GlobalConst_numberOfiBeaconRPI)
				try: 	lastBusy = self.beacons[dev.address][u"lastBusy"]
				except:	lastBusy = 0

			# do not calculate new position if beacon is busy eg beep, get battery
			if time.time() - lastBusy < 0: return False, 0

			for pi1 in activePis:
				pi1U = unicode(pi1)
				piXX = u"Pi_{:02d}".format(pi1)
				signal = self.getCurrentState(dev,devIds,piXX+u"_Signal", fromMETHOD="calcPostion2")
				if signal == "": continue
				txPower = self.getCurrentState(dev,devIds,"TxPowerReceived")
				if txPower == "": txPower =-30

				piTimeS = self.getCurrentState(dev,devIds,piXX+u"_Time", fromMETHOD="calcPostion3")
				if piTimeS is not None and len(piTimeS) < 5: continue

				if piTimeS > pitimeNearest:
					pitimeNearest = piTimeS

				piT2 = self.getTimetimeFromDateString(piTimeS) 
				if piT2 < 10: piT2 = time.time()
				try:
					dist = self.getCurrentState(dev,devIds,piXX+u"_Distance", fromMETHOD="calcPostion4")
					dist = float(dist)
				except Exception, e:
					self.indiLOG.log(40,u"Line {} has error={}".format(sys.exc_traceback.tb_lineno, e) )
					dist = 99999.

				piTimeUse = piT2
				if dist == 9999. and  lastUp != 0: 
					piTimeUse = lastUp

				if signal == -999:
					if	 (time.time()- piTimeUse <   					 expirationTime) :	    
						status =  "up"
						#if dev.name.find(u"BLE-") >-1:	self.indiLOG.log(10,u"setting status up  calcPostion sig  = -999  "  )
					elif (time.time()- piTimeUse < expirationTime)	and status != u"up": 
						status = u"down"
						#if dev.name.find(u"BLE-") >-1:	self.indiLOG.log(10,u"setting status up  calcPostion sig  = -999  "  )
				else:
					if dist >= 99990. and txPower < -20:							 continue
					if dist == "" or (dist >= 99990. and signal > -50):				 continue # fake signals with bad TXpower 
					if dist > 50./max(self.distanceUnits, 0.3) and signal > -50:	 continue # fake signals with bad TXpower 
					if time.time()- piTimeUse  < expirationTime:  
						status = u"up"
					elif (time.time()- piTimeUse < expirationTime)	and status != u"up": 
						status = u"down"

					if time.time()- piTimeUse  < max(90.,expirationTime):								   # last signal not in expiration range anymore , use at least 90 secs.. for cars exp is 15 secs and it forgets the last signals too quickly
						distanceToRpi.append([dist , pi1])

			if rssi !=-999: # dont set status for fast down messages, is done before
				currStatus =  self.getCurrentState(dev,devIds,"status", fromMETHOD="calcPostion5") 
				if currStatus!= status :
					if u"lastStatusChange" in dev.states: 
						try: lastStatusChangeDT  =  time.time() - self.getTimetimeFromDateString(dev.states[u"lastStatusChange"])
						except Exception, e:
								if unicode(e) != u"None":
									self.indiLOG.log(40,u"Line {} has error={}".format(sys.exc_traceback.tb_lineno, e))
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

				pos =[u"PosX",u"PosY",u"PosZ"]
				for ii in range(3):
					dd = abs(float(dev.states[pos[ii]]) - newPos[ii])
					if dd > 1./self.distanceUnits:	 # min delta = 1 meter
						self.addToStatesUpdateDict(devIds,pos[ii], newPos[ii],decimalPlaces=1)
						deltaDistance +=dd

		except Exception, e:
			if unicode(e) != u"None":
				self.indiLOG.log(40,u"Line {} has error={}".format(sys.exc_traceback.tb_lineno, e))
		return update, deltaDistance



####-------------------------------------------------------------------------####
	def BLEconnectupdateAll(self, piU, sensors):
		pi = int(piU)
		for sensor in sensors:
			if sensor == u"BLEconnect":
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
				if self.queueListBLE ==""		 : break
				if ii > 0:	pass
				time.sleep(0.05)
			self.queueListBLE = u"update"  
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
		piI = int(piU)
		try:
			for devId in info:
				if self.decideMyLog(u"BLE"): self.indiLOG.log(10,u"BLEconnect pi:{};  data:{} ".format(piU, info))
				try:
					dev = indigo.devices[int(devId)]
				except Exception, e:

					if unicode(e).find(u"timeout waiting") > -1:
						self.indiLOG.log(40,u"Line {} has error={}".format(sys.exc_traceback.tb_lineno, e))
						self.indiLOG.log(40,u"BLEconnectupdate communication to indigo is interrupted")
						return
					self.indiLOG.log(20,u"BLEconnectupdate devId not defined in devices pi:{}; devId={}; info:{}".format( piU, devId, info))
					continue
				if not dev.enabled: continue
				props = dev.pluginProps
				data={}
				for mac in info[devId]:
					if mac.upper() != props[u"macAddress"].upper() : continue
					data= info[devId][mac]
					break
				if data == {}:
					self.indiLOG.log(20,u"data empty for info[devid][mac];  pi:{}; devId={}; info:{} ".format( piU, devId, info) )
					continue

				if u"rssi" not in data:
					self.indiLOG.log(10,u"BLEconnectupdate ignoring msg; rssi missing; PI= {}; mac:{};  data:{}".format(piU, mac, data))
					return updateBLE
				rssi	  = float(data[u"rssi"])
				txPowerR  = float(data[u"txPower"])
				if self.decideMyLog(u"BLE"): self.indiLOG.log(10,u"BLEconnectupdate PI= {}; mac:{}  rssi:{}  txPowerR:{} TxPowerSet:{}".format(piU, mac, rssi, txPowerR, props[u"beaconTxPower"]))

				txSet = 999
				try: txSet = int(props[u"beaconTxPower"]) 
				except: pass
				if txSet != 999: 
					txPower = float(txSet)
				else:
					txPower = txPowerR
	
				expirationTime = int(props[u"expirationTime"])

				if dev.states[u"created"] == "":
					self.addToStatesUpdateDict(dev.id,u"created", datetime.datetime.now().strftime(_defaultDateStampFormat))

				piXX = u"Pi_{:02d}".format(piI)

				if rssi > -160 and unicode(dev.states[piXX+u"_Signal"]) != unicode(rssi):
					self.addToStatesUpdateDict(dev.id, piXX+u"_Signal",int(rssi) )
				if txPowerR !=-999 and	unicode(dev.states[u"TxPowerReceived"]) != unicode(txPowerR):
					self.addToStatesUpdateDict(dev.id, u"TxPowerReceived",txPowerR  )

				if rssi < -160: upD = u"down"
				else:			upD = u"up"

				if upD==u"up":
					dist=	 round( self.calcDist(txPower,  rssi) / self.distanceUnits, 1)
					if self.decideMyLog(u"BLE"): self.indiLOG.log(10,u"rssi txP dist dist-Corrected.. rssi:{} txPower:{}  dist:{}  rssiCaped:{}".format(rssi, txPower, dist, min(txPower,rssi)))
					self.addToStatesUpdateDict(dev.id,piXX+u"_Time",	datetime.datetime.now().strftime(_defaultDateStampFormat)  )
					self.addToStatesUpdateDict(dev.id,u"lastUp",datetime.datetime.now().strftime(_defaultDateStampFormat))
					if abs(dev.states[piXX+u"_Distance"] - dist) > 0.5 and abs(dev.states[piXX+u"_Distance"] - dist)/max(0.5,dist) > 0.05:
						self.addToStatesUpdateDict(dev.id,piXX+u"_Distance", dist,decimalPlaces=1)
				else:
					dist=99999.
					if dev.states[u"status"] == u"up":
						if self.decideMyLog(u"BLE"): self.indiLOG.log(10,u"NOT UPDATING::::  updating time  status was up, is down now dist = 99999 for MAC: {}".format(mac) )
						#self.addToStatesUpdateDict(dev.id,u"Pi_{:02d}_Time".format(piU),	datetime.datetime.now().strftime(_defaultDateStampFormat))
				#self.executeUpdateStatesDict()
				update, deltaDistance = self.calcPostion(dev,expirationTime)
				updateBLE = update or updateBLE

				if rssi > -160: 
					newClosestRPI = self.findClosestRPIForBLEConnect(dev, piU, dist)
					if newClosestRPI != dev.states[u"closestRPI"]:
						#indigo.server.log(dev.name+u", newClosestRPI: "+unicode(newClosestRPI)) 
						if newClosestRPI == -1:
							self.addToStatesUpdateDict(dev.id,u"closestRPI", -1)
							if self.setClostestRPItextToBlank: self.addToStatesUpdateDict(dev.id,u"closestRPIText", "")
						else:
							#indigo.server.log(dev.name+u", uodateing  newClosestRPI: "+unicode(newClosestRPI)+ " getRPIdevName:  "+self.getRPIdevName(newClosestRPI) ) 
							if unicode(dev.states[u"closestRPI"]) !="-1":
								self.addToStatesUpdateDict(dev.id,u"closestRPILast", dev.states[u"closestRPI"])
								self.addToStatesUpdateDict(dev.id,u"closestRPITextLast", dev.states[u"closestRPIText"])
							self.addToStatesUpdateDict(dev.id,u"closestRPI", newClosestRPI)
							self.addToStatesUpdateDict(dev.id,u"closestRPIText", self.getRPIdevName((newClosestRPI)))

				self.executeUpdateStatesDict(onlyDevID=dev.id, calledFrom=u"BLEconnectupdate end")	
 
		except Exception, e:
			if unicode(e) != u"None":
				self.indiLOG.log(40,u"Line {} has error={}".format(sys.exc_traceback.tb_lineno, e))
				if unicode(e).find(u"timeout waiting") > -1:
					self.indiLOG.log(40,u"communication to indigo is interrupted")

		return updateBLE


####-------------------------------------------------------------------------####
	def updateOutput(self, piU, outputs):
		data=""
		dateString = datetime.datetime.now().strftime(_defaultDateStampFormat)
		try:

			for output in outputs:
				if output.find(u"OUTPUTgpio") == -1 and output.find(u"OUTPUTi2cRelay") == -1: continue

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
							self.indiLOG.log(40,u"Line {} has error={}".format(sys.exc_traceback.tb_lineno, e))
							self.indiLOG.log(40,u"communication to indigo is interrupted")
							return
						if unicode(e).find(u"not found in database") ==-1:
							self.indiLOG.log(40,u"Line {} has error={}".format(sys.exc_traceback.tb_lineno, e))
							return

						self.indiLOG.log(40,u"bad devId send from pi:"+ piU+ u"devId: "+devIds+u" deleted?")
						continue

					if not dev.enabled:
						self.indiLOG.log(20,u"dev not enabled send from pi:{} dev: {}".format(piU, dev.name) )
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

					if output.find(u"OUTPUTgpio-1") > -1 or output.find(u"OUTPUTi2cRelay") > -1:
						if self.decideMyLog(u"SensorData"): self.indiLOG.log(10,u"{} received {}".format(output, Data) )
						self.OUTPUTgpio1(dev, props, data)
						continue


				for devIds in devUpdate:
					if devIds in self.updateStatesDict:
						if self.decideMyLog(u"SensorData"): self.indiLOG.log(10,u"pi# {}  {}  {}".format(piU, devIds, self.updateStatesDict) )
						self.executeUpdateStatesDict(onlyDevID=devIds, calledFrom=u"updateOutput end")

		except Exception, e:
			if unicode(e) != u"None":
				self.indiLOG.log(40,u"Line {} has error={}".format(sys.exc_traceback.tb_lineno, e))
				if unicode(e).find(u"timeout waiting") > -1:
					self.indiLOG.log(40,u"updateOutput communication to indigo is interrupted")


####-------------------------------------------------------------------------####
	def OUTPUTgpio1(self, dev, props, data):
		try:
			if u"actualGpioValue" in data and "outputType" in props:
				actualGpioValue = unicode(data[u"actualGpioValue"]).lower()

				self.addToStatesUpdateDict(dev.id,u"actualGpioValue", data[u"actualGpioValue"])
				if props[u"outType"] == u"0": # not inverse
					if actualGpioValue =="high" :upState = u"on"
					else:               		 upState = u"off"
				else:
					if actualGpioValue =="low"  :upState = u"on"
					else:               		 upState = u"off"

				self.addToStatesUpdateDict(dev.id,u"status", upState)
				self.addToStatesUpdateDict(dev.id,u"onOffState", upState=="on")

		except Exception, e:
			if unicode(e) != u"None":
				self.indiLOG.log(40,u"Line {} has error={}".format(sys.exc_traceback.tb_lineno, e))
			self.indiLOG.log(40,unicode(data))
		return



####-------------------------------------------------------------------------####
	def updateSensors(self, pi, sensors):
		data=""
		dateString = datetime.datetime.now().strftime(_defaultDateStampFormat)
		piU = unicode(pi)
		try:
			if self.decideMyLog(u"SensorData"): self.indiLOG.log(10,u"sensor input  pi: {}; data {}" .format(piU, sensors))
			# data[u"sensors"][sensor][u"temp,hum,press,INPUT"]

			for sensor in sensors:
				if sensor == u"i2cChannels":
					continue  # need to implement test for i2c channel active

				if sensor == u"BLEconnect":
					continue

				if sensor == u"setTEA5767":
					self.updateTEA5767(sensors[sensor],sensor)
					continue

				if sensor == u"getBeaconParameters":
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
							self.indiLOG.log(40,u"Line {} has error={}".format(sys.exc_traceback.tb_lineno, e))
							self.indiLOG.log(40,u"communication to indigo is interrupted")
							return
						if unicode(e).find(u"not found in database") ==-1:
							self.indiLOG.log(40,u"Line {} has error={}".format(sys.exc_traceback.tb_lineno, e))
							return

						self.indiLOG.log(20,u"bad devId send from pi:"+ piU+ u"devId: "+devIds+u" deleted?")
						continue

					if not dev.enabled:
						if self.decideMyLog(u"UpdateRPI"): self.indiLOG.log(10,u"dev not enabled send from pi:{} dev: {}".format(piU, dev.name) )
						continue

					self.saveSensorMessages(devId=devIds, item=u"lastMessage", value=time.time())


					data = sensors[sensor][devIds]
					uData = unicode(data)
					if sensor=="mysensors":
						self.indiLOG.log(20,sensor+u" received "+ uData)

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

					self.updateCommonStates(dev, data, whichKeysToDisplay, pi)



					if dev.deviceTypeId == u"as726x":
						if u"green" in data:
							data[u"illuminance"] = float(data[u"green"])*6.83
						self.updateRGB(dev, data, whichKeysToDisplay, dispType=4)
						if u"temp" in data:
							x, UI, decimalPlaces, useFormat  = self.convTemp(data[u"temp"])
							self.addToStatesUpdateDict(dev.id,u"temperature", x, decimalPlaces=decimalPlaces)
							updateProps0, doUpdate = self.updateChangedValues(dev, x, props, u"Temperature", useFormat, whichKeysToDisplay, decimalPlaces)
							if updateProps: 
								props[doUpdate[0]] = doUpdate[1]
								self.deviceStopCommIgnore = time.time()
								dev.replacePluginPropsOnServer(props)

						if u"LEDcurrent" in data:
							self.addToStatesUpdateDict(dev.id,u"LEDcurrent", data[u"LEDcurrent"], decimalPlaces=1)
						continue

					if sensor == u"i2cTCS34725" :
						self.updateRGB(dev, data, whichKeysToDisplay)
						continue

					self.updateLight(dev, data, whichKeysToDisplay)

					if sensor == u"ultrasoundDistance" :
						self.updateDistance(dev, data, whichKeysToDisplay)
						continue

					if sensor == u"vl503l0xDistance" :
						self.updateDistance(dev, data, whichKeysToDisplay)
						continue

					if sensor == u"vl6180xDistance" :
						self.updateDistance(dev, data, whichKeysToDisplay)
						continue

					if sensor == u"vcnl4010Distance" :
						self.updateDistance(dev, data, whichKeysToDisplay)
						continue

					if sensor == u"apds9960" :
						self.updateapds9960(dev, data)
						continue

					if sensor.find(u"INPUTgpio-") >-1:
						self.updateINPUT(dev, data, whichKeysToDisplay, int(sensor.split(u"INPUTgpio-")[1]), sensor)
						continue

					if sensor.find(u"INPUTtouch-") >-1:
						self.updateINPUT(dev, data, whichKeysToDisplay, int(sensor.split(u"INPUTtouch-")[1]), sensor)
						continue

					if sensor.find(u"INPUTtouch12-") >-1:
						self.updateINPUT(dev, data, whichKeysToDisplay, int(sensor.split(u"INPUTtouch12-")[1]), sensor)
						continue

					if sensor.find(u"INPUTtouch16-") >-1:
						self.updateINPUT(dev, data, whichKeysToDisplay, int(sensor.split(u"INPUTtouch16-")[1]), sensor)
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
						self.indiLOG.log(20,sensor+u"  into input")
						self.updateINPUT(dev, data, whichKeysToDisplay, 10, sensor)
						continue

					if sensor == u"myprogram" :
						self.updateINPUT(dev, data, whichKeysToDisplay, 10, sensor)
						continue

					if dev.deviceTypeId == u"Wire18B20":
						self.updateOneWire(dev,data,whichKeysToDisplay,piU)
						continue

					if dev.deviceTypeId == u"BLEmyBLUEt":
						self.updateBLEmyBLUEt(dev,data,props,whichKeysToDisplay)
						continue

					if dev.deviceTypeId == u"ina219":
						self.updateina219(dev,data,whichKeysToDisplay)
						continue

					if dev.deviceTypeId == u"ina3221":
						self.updateina3221(dev,data,whichKeysToDisplay)
						continue

					if dev.deviceTypeId == u"i2cADC121":
						self.updateADC121(dev,data,whichKeysToDisplay)
						continue

					if dev.deviceTypeId == u"l3g4200":
						self.updateGYROS(dev,data,whichKeysToDisplay)
						continue

					if dev.deviceTypeId == u"bno055":
						self.updateGYROS(dev,data,whichKeysToDisplay)
						continue

					if dev.deviceTypeId == u"mag3110":
						self.updateGYROS(dev,data,whichKeysToDisplay)
						continue

					if dev.deviceTypeId == u"hmc5883L":
						self.updateGYROS(dev,data,whichKeysToDisplay)
						continue

					if dev.deviceTypeId == u"mpu6050":
						self.updateGYROS(dev,data,whichKeysToDisplay)
						continue

					if dev.deviceTypeId == u"mpu9255":
						self.updateGYROS(dev,data,whichKeysToDisplay)
						continue

					if dev.deviceTypeId == u"lsm303":
						self.updateGYROS(dev,data,whichKeysToDisplay)
						continue

					if dev.deviceTypeId in [u"INPUTpulse",u"INPUTcoincidence"]:
						self.updatePULSE(dev,data,whichKeysToDisplay)
						continue


					if sensor == u"rainSensorRG11":
						self.updaterainSensorRG11(dev,data,whichKeysToDisplay)
						continue


					if sensor == u"pmairquality":
						self.updatePMAIRQUALITY(dev,data,whichKeysToDisplay)
						continue

					if sensor == u"launchpgm":
						st = data[u"status"]
						self.addToStatesUpdateDict(dev.id, "status", st)
						if st == u"running": 
							dev.updateStateImageOnServer(indigo.kStateImageSel.SensorOn)
						elif st == u"not running": 
							dev.updateStateImageOnServer(indigo.kStateImageSel.SensorOff)
						elif st == u"not checked": 
							dev.updateStateImageOnServer(indigo.kStateImageSel.SensorTripped)
						continue

					try: 	newStatus = dev.states[u"status"]
					except: newStatus = ""

					if sensor in [u"sgp30",u"ccs811"]:
						try:
							x, UI  = int(float(data[u"CO2"])),  u"CO2 {:.0f}[ppm] ".format(float(data[u"CO2"]))
							newStatus = self.setStatusCol( dev, u"CO2", x, UI, whichKeysToDisplay, indigo.kStateImageSel.TemperatureSensorOn,newStatus, decimalPlaces = 1)
							updateProps0, doUpdate =  self.updateChangedValues(dev, x, props, u"CO2", u"{:d}%", whichKeysToDisplay, 0)
							if updateProps0: props[doUpdate[0]] = doUpdate[1]; updateProps = updateProps or updateProps0
							x, UI  = int(float(data[u"VOC"])),  u"VOC {:.0f}[ppb]".format(float(data[u"VOC"]))
							newStatus = self.setStatusCol( dev, u"VOC", x, UI, whichKeysToDisplay, indigo.kStateImageSel.TemperatureSensorOn,newStatus, decimalPlaces = 1)
							updateProps0, doUpdate = self.updateChangedValues(dev, x, props, u"VOC", u"{:d}%", whichKeysToDisplay, 0)
							if updateProps0: props[doUpdate[0]] = doUpdate[1]; updateProps = updateProps or updateProps0

						except Exception, e:
							self.indiLOG.log(40,u"Line {} has error={}".format(sys.exc_traceback.tb_lineno, e))
							self.indiLOG.log(20,unicode(props))


					if sensor == u"as3935":
						try:
							if data[u"eventType"]  == u"no Action yet":
								self.addToStatesUpdateDict(dev.id,u"eventType", u"no Data")
							elif data[u"eventType"]	 == u"no lightning today":
								self.addToStatesUpdateDict(dev.id,u"eventType", u"no lightning today")
							elif data[u"eventType"]	 == u"measurement":
								self.addToStatesUpdateDict(dev.id,u"eventType", u"measurement") 
								if data[u"lightning"]  == u"lightning detected":
									x, UI  = int(float(data[u"distance"])),	  "Distance {:.0f}[km]".format(float(data[u"distance"]))
									newStatus = self.setStatusCol( dev, u"distance", x, UI, whichKeysToDisplay, indigo.kStateImageSel.TemperatureSensorOn,newStatus, decimalPlaces = 0)
									self.addToStatesUpdateDict(dev.id,u"energy", float(data[u"energy"])) 
									newStatus = self.setStatusCol( dev, u"lightning", data[u"lightning"], u"lightning "+datetime.datetime.now().strftime(u"%m-%d %H:%M:%S"), whichKeysToDisplay, indigo.kStateImageSel.TemperatureSensorOn,newStatus)
									self.addToStatesUpdateDict(dev.id,u"lastLightning", datetime.datetime.now().strftime(_defaultDateStampFormat)) 
									rightNow = time.time()
									nDevs = 1
									#indigo.server.log(u"  checking devL for "+ dev.name )
									for devL in indigo.devices.iter(u"props.isLightningDevice"):
										if devL.id == dev.id: continue
										deltaTime = time.time() - self.getTimetimeFromDateString( devL.states[u"lastLightning"])
										if deltaTime < self.lightningTimeWindow : 
											nDevs += 1
										#indigo.server.log(u" deltaTime: "+ unicode(deltaTime))
									if nDevs >= self.lightningNumerOfSensors:
										indigo.variable.updateValue(u"lightningEventDevices",unicode(nDevs))
										time.sleep(0.01) # make shure the # of devs gets updated first
										indigo.variable.updateValue(u"lightningEventDate",datetime.datetime.now().strftime(_defaultDateStampFormat))

								elif data[u"lightning"].find(u"Noise") == 0: 
									self.addToStatesUpdateDict(dev.id,u"lightning", u"calibrating,- sensitivity ")
								elif data[u"lightning"].find(u"Disturber") == 0: 
									self.addToStatesUpdateDict(dev.id,u"lightning", u"calibrating,- Disturber event ")
						except Exception, e:
							self.indiLOG.log(40,u"Line {} has error={}".format(sys.exc_traceback.tb_lineno, e))
							self.indiLOG.log(40,unicode(props) +u"\n"+ unicode(data))
						continue


					if sensor in[u"mhzCO2"]:
						try:
							x, UI  = int(float(data[u"CO2"])),  u"CO2 {:.0f}[ppm]".format(float(data[u"CO2"]))
							newStatus   = self.setStatusCol( dev, u"CO2", x, UI, whichKeysToDisplay, indigo.kStateImageSel.TemperatureSensorOn,newStatus, decimalPlaces = 1)
							updateProps0, doUpdate = self.updateChangedValues(dev, x, props, u"CO2", "{:d}%", whichKeysToDisplay, 0)
							if updateProps0: props[doUpdate[0]] = doUpdate[1]; updateProps = updateProps or updateProps0

							if abs( float(dev.states[u"CO2offset"]) - float(data[u"CO2offset"])	) > 1: 
								self.setONErPiV(piU,u"piUpToDate", [u"updateParamsFTP"])
							self.addToStatesUpdateDict(dev.id,u"calibration", data[u"calibration"]) 
							self.addToStatesUpdateDict(dev.id,u"raw", float(data[u"raw"]),	decimalPlaces = 1) 
							self.addToStatesUpdateDict(dev.id,u"CO2offset", float(data[u"CO2offset"]),	decimalPlaces = 1) 
						except Exception, e:
							self.indiLOG.log(40,u"Line {} has error={}".format(sys.exc_traceback.tb_lineno, e))
							self.indiLOG.log(40,unicode(props))


					if u"hum" in data:
						hum = max(0.,min(data[u"hum"],100.))
						x, UI, decimalPlaces  = self.convHum(hum)
						newStatus = self.setStatusCol( dev, u"Humidity", x, UI, whichKeysToDisplay, indigo.kStateImageSel.HumiditySensor,newStatus, decimalPlaces = decimalPlaces )
						updateProps0, doUpdate = self.updateChangedValues(dev, x, props, u"Humidity", u"{:d}%", whichKeysToDisplay, decimalPlaces)
						if updateProps0: props[doUpdate[0]] = doUpdate[1]; updateProps = updateProps or updateProps0


					if u"temp" in data:
						temp = data[u"temp"]
						x, UI, decimalPlaces, useFormat = self.convTemp(temp)
						newStatus = self.setStatusCol( dev, u"Temperature", x, UI, whichKeysToDisplay, indigo.kStateImageSel.TemperatureSensorOn,newStatus, decimalPlaces = decimalPlaces )
						updateProps0, doUpdate = self.updateChangedValues(dev, x, props, u"Temperature", useFormat, whichKeysToDisplay, decimalPlaces)
						if updateProps0: props[doUpdate[0]] = doUpdate[1]; updateProps = updateProps or updateProps0

					if u"AmbientTemperature" in data:
						temp = data[u"AmbientTemperature"]
						x, UI, decimalPlaces, useFormat  = self.convTemp(temp)
						newStatus = self.setStatusCol( dev, u"AmbientTemperature", x, UI, whichKeysToDisplay, indigo.kStateImageSel.HumiditySensor,newStatus, decimalPlaces = decimalPlaces )
						updateProps0, doUpdate = self.updateChangedValues(dev, x, props, u"AmbientTemperature", useFormat, whichKeysToDisplay, decimalPlaces)
						if updateProps0: props[doUpdate[0]] = doUpdate[1]; updateProps = updateProps or updateProps0


					if u"press" in data:
						if False and u"Altitude" in dev.states and u"temp" in data:
							#indigo.server.log(u"Altitude    "+unicode(data[u"press"])+u"  "+ unicode(props))
							x, UI, decimalPlaces, useFormat  = self.convAlt(data[u"press"], props, data[u"temp"])
							newStatus = self.setStatusCol( dev, u"Altitude", x, UI, whichKeysToDisplay, indigo.kStateImageSel.HumiditySensor,newStatus, decimalPlaces = decimalPlaces )
							updateProps0, doUpdate = self.updateChangedValues(dev, x, props, u"Altitude", useFormat, whichKeysToDisplay, decimalPlaces)
							if updateProps0: props[doUpdate[0]] = doUpdate[1]; updateProps = updateProps or updateProps0

						newStatus, updateProps0, doUpdate = self.setPressureDisplay(dev, props, data, whichKeysToDisplay,newStatus)
						if updateProps0: props[doUpdate[0]] = doUpdate[1]; updateProps = updateProps or updateProps0

					if dev.deviceTypeId == u"BLEaprilAccel":
						self.updateAPRILaccel(dev,data,whichKeysToDisplay, pi)

					if dev.deviceTypeId == u"BLERuuviTag":
						self.updateBLERuuviTag(dev,data,whichKeysToDisplay, pi)

					if dev.deviceTypeId in [u"BLEiBS01",u"BLEiBS02",u"BLEiBS03"]:
						self.updateBLEiBSxxOneOnOff(dev,data,whichKeysToDisplay, pi)

					if dev.deviceTypeId == u"BLEiBS03G":
						self.updateBLEiBS03G(dev,data,whichKeysToDisplay, pi)

					if dev.deviceTypeId in [u"BLEiBS03RG",u"BLEiBS01RG",u"BLESatech"]:
						self.updateBLEiBS0xRG(dev,data,whichKeysToDisplay, pi)

					if dev.deviceTypeId in [u"BLEiSensor-onOff",u"BLEiSensor-on",u"BLEiSensor-RemoteKeyFob",u"BLEiSensor-TempHum"]:
						self.updateBLEiSensor(dev,data,whichKeysToDisplay, pi)

					if u"proximity" in data:
						newStatus, updateProps0, doUpdate = self.setProximity(dev, props, data, whichKeysToDisplay,newStatus)
						if updateProps0: props[doUpdate[0]] = doUpdate[1]; updateProps = updateProps or updateProps0


					if u"moisture" in data:
						newStatus, updateProps0, doUpdate = self.setMoistureDisplay(dev, props, data, whichKeysToDisplay,newStatus)
						self.updateLight(dev, data, whichKeysToDisplay)
						if updateProps0: props[doUpdate[0]] = doUpdate[1]; updateProps = updateProps or updateProps0

					if u"Vertical" in data:
						try:
							x, UI  = float(data[u"Vertical"]),  u"{:7.3f}".format(float(data[u"Vertical"]))
							newStatus = self.setStatusCol( dev, u"VerticalMovement", x, UI, whichKeysToDisplay, indigo.kStateImageSel.TemperatureSensorOn,newStatus, decimalPlaces = 3)
						except: pass

					if u"Horizontal" in data:
						try:
							x, UI  = float(data[u"Horizontal"]), u"{:7.3f}".format(float(data[u"Horizontal"]))
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
							x, UI  = float(data[u"MovementAbs"]), u"{:5.2f}".format(float(data[u"MovementAbs"]))
							newStatus = self.setStatusCol( dev, u"MovementAbs", x, UI, whichKeysToDisplay, indigo.kStateImageSel.TemperatureSensorOn,newStatus, decimalPlaces = 2)
						except: pass

					if u"Movement" in data:
						try:
							x, UI  = float(data[u"Movement"]), u"{:5.2f}".format(float(data[u"Movement"]))
							newStatus = self.setStatusCol( dev, u"Movement", x, UI, whichKeysToDisplay, indigo.kStateImageSel.TemperatureSensorOn,newStatus, decimalPlaces = 2)
						except: pass

					if u"Uniformity" in data:
						try:
							x, UI  = float(data[u"Uniformity"]), u"{:5.1f}".format(float(data[u"Uniformity"]))
							newStatus = self.setStatusCol( dev, u"Uniformity", x, UI, whichKeysToDisplay, indigo.kStateImageSel.TemperatureSensorOn,newStatus, decimalPlaces = 1)
						except: pass

					if sensor == u"amg88xx" and u"rawData" in data :
						try:
							if (u"imageFilesaveRawData" in props and props[u"imageFilesaveRawData"] =="1") or (u"imageFileNumberOfDots" in props and props[u"imageFileNumberOfDots"] !="-"):
								# exapnd to 8x8 matrix, data is in 4 byte packages *100
								pixPerRow = 8
								dataRaw = json.loads(data[u"rawData"])
								dataRaw = json.dumps([[dataRaw[kkkx] for kkkx in range(pixPerRow*(iiix), pixPerRow*(iiix+1))] for iiix in range(pixPerRow)])

								if u"imageFilesaveRawData" in props and props[u"imageFilesaveRawData"] =="1":
										newStatus = self.setStatusCol( dev, u"rawData", dataRaw,"", whichKeysToDisplay, indigo.kStateImageSel.TemperatureSensorOn,newStatus, decimalPlaces = "")
								if u"imageFileNumberOfDots" in props and props[u"imageFileNumberOfDots"] !="-":
									if u"imageFileName" in props and len(props[u"imageFileName"])>1:
										imageParams	  = json.dumps( {u"logFile":self.PluginLogFile, u"logLevel":props[u"imageFilelogLevel"],u"compress":props[u"imageFileCompress"],u"fileName":self.cameraImagesDir+props[u"imageFileName"],u"numberOfDots":props[u"imageFileNumberOfDots"],u"dynamic":props[u"imageFileDynamic"],u"colorBar":props[u"imageFileColorBar"]} )
										cmd = self.pythonPath + u" '" + self.pathToPlugin + u"makeCameraPlot.py' '" +imageParams+u"' '"+dataRaw+u"' & "  
										if props[u"imageFilelogLevel"] == u"1": self.indiLOG.log(20,u"AMG88 command:{}".format(cmd))
										subprocess.call(cmd, shell=True)
						except Exception, e:
							self.indiLOG.log(40,u"Line {} has error={}".format(sys.exc_traceback.tb_lineno, e))
							self.indiLOG.log(40,unicode(props))
							self.indiLOG.log(40,unicode(len(data[u"rawData"]))+u"     "+data[u"rawData"])

					if sensor == u"mlx90640" and u"rawData" in data :
						try:
							if (u"imageFilesaveRawData" in props and props[u"imageFilesaveRawData"] == u"1") or (u"imageFileNumberOfDots" in props and props[u"imageFileNumberOfDots"] != u"-"):
								# exapnd to 8x8 matrix, data is in 4 byte packages *100
								dataRaw = data[u"rawData"]

								if u"imageFilesaveRawData" in props and props[u"imageFilesaveRawData"] == u"1" and False:
										newStatus = self.setStatusCol( dev, u"rawData", dataRaw,"", whichKeysToDisplay, indigo.kStateImageSel.TemperatureSensorOn,newStatus, decimalPlaces = "")
								if u"imageFileNumberOfDots" in props and props[u"imageFileNumberOfDots"] !="-":
									if u"imageFileName" in props and len(props[u"imageFileName"])>1:
										imageParams	  = json.dumps( {u"logFile":self.PluginLogFile, u"logLevel":props[u"imageFilelogLevel"],"compress":props[u"imageFileCompress"],u"fileName":self.cameraImagesDir+props[u"imageFileName"],u"numberOfDots":props[u"imageFileNumberOfDots"],u"dynamic":props[u"imageFileDynamic"],u"colorBar":props[u"imageFileColorBar"]} )
										cmd = self.pythonPath + u" '" + self.pathToPlugin + u"makeCameraPlot.py' '" +imageParams+u"' '"+dataRaw+u"' & "  
										if props[u"imageFilelogLevel"] == u"1": self.indiLOG.log(20,u"mlx90640 command:{}".format(cmd))
										subprocess.call(cmd, shell=True)
						except Exception, e:
							self.indiLOG.log(40,u"Line {} has error={}".format(sys.exc_traceback.tb_lineno, e))
							self.indiLOG.log(40,unicode(props))
							self.indiLOG.log(40,unicode(len(data[u"rawData"]))+u"     "+data[u"rawData"])


					if sensor == u"lidar360" :
						try:
								xx = data[u"triggerValues"]
								newStatus = self.setStatusCol( dev, u"Leaving_count", 					xx[u"current"][u"GT"][u"totalCount"],	u"leaving Count:{}".format(xx[u"current"][u"GT"][u"totalCount"]),			whichKeysToDisplay, indigo.kStateImageSel.TemperatureSensorOn,newStatus, decimalPlaces = 0)
								newStatus = self.setStatusCol( dev, u"Approaching_count", 				xx[u"current"][u"LT"][u"totalCount"],	u"approaching Count:{}".format(xx[u"current"][u"LT"][u"totalCount"]),		whichKeysToDisplay, indigo.kStateImageSel.TemperatureSensorOn,newStatus, decimalPlaces = 0)
								newStatus = self.setStatusCol( dev, u"Re-Calibration_needed_count",		xx[u"calibrated"][u"GT"][u"totalCount"],u"calibration Count:{}".format(xx[u"calibrated"][u"GT"][u"totalCount"]), 	whichKeysToDisplay, indigo.kStateImageSel.TemperatureSensorOn,newStatus, decimalPlaces = 0)
								newStatus = self.setStatusCol( dev, u"Room_occupied_count", 			xx[u"calibrated"][u"LT"][u"totalCount"],u"occupied Count:{}".format(xx[u"calibrated"][u"LT"][u"totalCount"]),		whichKeysToDisplay, indigo.kStateImageSel.TemperatureSensorOn,newStatus, decimalPlaces = 0)

								newStatus = self.setStatusCol( dev, u"Leaving_value", 					xx[u"current"][u"GT"][u"totalSum"],		u"leaving value:{}".format(xx[u"current"][u"GT"][u"totalSum"]),				whichKeysToDisplay, indigo.kStateImageSel.TemperatureSensorOn,newStatus, decimalPlaces = 0)
								newStatus = self.setStatusCol( dev, u"Approaching_value", 				xx[u"current"][u"LT"][u"totalSum"],		u"approcahing value:{}".format(xx[u"current"][u"LT"][u"totalSum"]), 		whichKeysToDisplay, indigo.kStateImageSel.TemperatureSensorOn,newStatus, decimalPlaces = 0)
								newStatus = self.setStatusCol( dev, u"Re-Calibration_needed_value", 	xx[u"calibrated"][u"GT"][u"totalSum"],	u"calibration value:{}".format(xx[u"calibrated"][u"GT"][u"totalSum"]),		whichKeysToDisplay, indigo.kStateImageSel.TemperatureSensorOn,newStatus, decimalPlaces = 0)
								newStatus = self.setStatusCol( dev, u"Room_occupied_value", 			xx[u"calibrated"][u"LT"][u"totalSum"],	u"occupied value:{}".format(xx[u"calibrated"][u"LT"][u"totalSum"]),			whichKeysToDisplay, indigo.kStateImageSel.TemperatureSensorOn,newStatus, decimalPlaces = 0)

								newStatus = self.setStatusCol( dev, u"Current_NonZeroBins", 			xx[u"current"][u"nonZero"],				u"current non zero bins:{}".format(xx[u"current"][u"nonZero"]),			whichKeysToDisplay, indigo.kStateImageSel.TemperatureSensorOn,newStatus, decimalPlaces = 0)
								newStatus = self.setStatusCol( dev, u"Calibration_NonZeroBins", 		xx[u"calibrated"][u"nonZero"],			u"calibration non zero bins:{}".format(xx[u"calibrated"][u"nonZero"]),		whichKeysToDisplay, indigo.kStateImageSel.TemperatureSensorOn,newStatus, decimalPlaces = 0)
								newStatus = self.setStatusCol( dev, u"ubsPortUsed", 					xx[u"port"],							xx[u"port"],																whichKeysToDisplay, indigo.kStateImageSel.TemperatureSensorOn,newStatus, decimalPlaces = 0)

								varName =(dev.name+u"_calibrated").replace(u" ","_")
								try:
									var = indigo.variables[varName]
								except:
									var = indigo.variable.create(varName,"")
									self.varExcludeSQLList.append(var)

								if u"calibrated" in data and len(data[u"calibrated"]) > 10:
									indigo.variable.updateValue(varName, json.dumps(data[u"calibrated"]))
								else:
									try:	data[u"calibrated"] =  json.loads(var.value)
									except: data[u"calibrated"] = []

								if u"saveRawData" in props and props[u"saveRawData"] == u"1":
									varName =(dev.name+u"_data").replace(u" ","_")
									try:
										var = indigo.variables[varName]
									except:
										indigo.variable.create(varName, varName)
										self.varExcludeSQLList.append(varName)
									indigo.variable.updateValue(varName, json.dumps(data))


								if len(props[u"fileName"]) < 5:	fileName = self.indigoPreferencesPluginDir+u"lidar360Images/"+dev.name+u".png"
								else: 						  	fileName = props[u"fileName"]

								if u"mode" in props and props[u"mode"] in [u"manual",u"auto"] and (u"sendPixelData" in props and props[u"sendPixelData"] =="1"):
									dataFile = u"/tmp/makelidar360.dat"
									if  os.path.isfile(dataFile):
										lastlidar360PlotTime = os.path.getmtime(dataFile)
									else: lastlidar360PlotTime = 0
									if (    u"showImageWhen" not in props or  
											( time.time() - lastlidar360PlotTime > float(props[u"showImageWhen"]) ) or 
											data[u"triggerValues"][u"current"][u"GT"][u"totalCount"] != 0 or 
											data[u"triggerValues"][u"current"][u"LT"][u"totalCount"] != 0 or
											data[u"triggerValues"][u"calibrated"][u"GT"][u"totalCount"] != 0 or
											data[u"triggerValues"][u"calibrated"][u"LT"][u"totalCount"] != 0    ): 

										imageParams	  ={u"logFile":self.PluginLogFile, 
													u"logLevel":props[u"logLevel"],
													u"dataFile":"/tmp/makelidar360.dat",
													u"compress":props[u"fileCompress"],
													u"fileName":fileName,
													u"xMin":props[u"xMin"],
													u"xMax":props[u"xMax"],
													u"yMin":props[u"yMin"],
													u"yMax":props[u"yMax"],
													u"scalefactor":props[u"scalefactor"],
													u"showZeroValues":props[u"showZeroValues"],
													u"mode":props[u"mode"],
													u"showPhi0":props[u"showPhi0"],
													u"showZeroDot":props[u"showZeroDot"],
													u"frameON":props[u"frameON"],
													u"DPI":props[u"DPI"],
													u"showTriggerValues":props[u"showTriggerValues"],
													u"doNotUseDataRanges":props[u"doNotUseDataRanges"],
													u"showTimeStamp":props[u"showTimeStamp"],
													u"showDoNotTrigger":props[u"showDoNotTrigger"],
													u"fontSize":props[u"fontSize"],
													u"showLegend":props[u"showLegend"],
													u"topText":props[u"topText"],
													u"frameTight":props[u"frameTight"],
													u"yOffset":props[u"yOffset"],
													u"xOffset":props[u"xOffset"],
													u"numberOfDotsX":props[u"numberOfDotsX"],
													u"numberOfDotsY":props[u"numberOfDotsY"],
													u"phiOffset":props[u"phiOffset"],
													u"anglesInOneBin":props[u"anglesInOneBin"],
													u"colorCurrent":props[u"colorCurrent"],
													u"colorCalibrated":props[u"colorCalibrated"],
													u"colorLast":props[u"colorLast"],
													u"colorBackground":props[u"colorBackground"]} 
										#allData = json.dumps({u"imageParams":imageParams, u"data":data})
										cmd = self.pythonPath + u" '" + self.pathToPlugin + u"makeLidar360Plot.py' '" +json.dumps(imageParams)+u"'  & "  
										if props[u"logLevel"] in [u"1",u"3"] : self.indiLOG.log(20,u"lidar360 command:{}".format(cmd))
										self.writeJson(data, fName=u"/tmp/makeLidar360.dat") 
										subprocess.call(cmd, shell=True)
						except Exception, e:
							self.indiLOG.log(40,u"Line {} has error={}".format(sys.exc_traceback.tb_lineno, e))
							self.indiLOG.log(40,u"props: {}".format(props))
							self.indiLOG.log(40,u"triggervalues: {}".format(data[u"triggerValues"]) )

					if updateProps:
						self.deviceStopCommIgnore = time.time()
						dev.replacePluginPropsOnServer(props)

		
				for devIds in devUpdate:
					if devIds in self.updateStatesDict:
						if self.decideMyLog(u"SensorData"): self.indiLOG.log(10,u"pi# "+piU + "  " + unicode(devIds)+u"  "+unicode(self.updateStatesDict))
						self.executeUpdateStatesDict(onlyDevID=devIds, calledFrom=u"updateSensors end")
			self.saveSensorMessages(devId="")

		except Exception, e:
			if unicode(e) != u"None":
				self.indiLOG.log(40,u"Line {} has error={}".format(sys.exc_traceback.tb_lineno, e))
				self.indiLOG.log(40,u"pi# "+piU + "  " + unicode(sensors))

		return

####-------------------------------------------------------------------------####
	def updaterainSensorRG11(self, dev, data, whichKeysToDisplay):
		try:
			props = dev.pluginProps
			if u"lastUpdate" not in props or props[u"lastUpdate"]==u"0":
				props[u"lastUpdate"] = time.time()
			dd = datetime.datetime.now().strftime(_defaultDateStampFormat)
			updateDev = False
			##indigo.server.log(unicode(data))
			rainChanges = []
			if len(dev.states[u"resetDate"]) < 5:
				rainChanges.append([u"resetDate", dd, dd,""])
				#self.addToStatesUpdateDict(dev.id, "resetDate", datetime.datetime.now().strftime(_defaultDateStampFormat))

			if	 self.rainUnits == u"inch":	   mult = 1/25.4	; unit = u"in"
			elif self.rainUnits == u"cm":	   mult = 0.1 		; unit = u"cm"
			else:                              mult = 1 		; unit = u"mm"

			if u"format" in props and len(props[u"format"])<2: form = u"%.{}f[{}]".format(self.rainDigits+1, self.rainUnits)
			else:											  form = props[u"format"]

			for cc in [u"totalRain", u"rainRate", u"measurementTime", u"mode", u"rainLevel", u"sensitivity",u"nBuckets",u"nBucketsTotal",u"bucketSize"]:
				if cc in data:

					if cc == u"totalRain":
						x = float(data[cc])*mult	 # is in mm 
						rainChanges.append([cc, x, form%x, self.rainDigits])
						for zz in [u"hourRain",u"dayRain",u"weekRain",u"monthRain",u"yearRain"]:
							zzP= zz+u"Total"
							if zzP in props:
								oldV = float(props[zzP])
								if oldV > x:
									props[zzP] = x
									updateDev = True
									oldV = x
								rainChanges.append([zz, x-oldV, unicode(x-oldV), self.rainDigits])


					elif cc == u"rainRate":
						x = float(data[cc])*mult	 # is in mm 
						rainChanges.append([cc, x, form%x, self.rainDigits+1])
						self.fillMinMaxSensors(dev,"rainRate",x,self.rainDigits)
						if u"rainTextMap" in props:
							rtm	 = props[u"rainTextMap"].split(u";")
							lowerLimit =[]
							rainText =[]
							for nn in range(len(rtm)):
								item = rtm[nn].split(u":")
								if len(item) !=2: continue
								try: 
									limit = float(item[0])
									if x <= limit or nn+1 == len(rtm) :
										rainChanges.append([u"rainText", item[1],unicode(item[1]),""])
										break
								except: pass

					elif cc == u"measurementTime":
						x = data[cc]
						rainChanges.append([cc, int(x), unicode(int(x)),""])

					elif cc == u"rainLevel":
						try: x = int(data[cc])
						except: x = 0
						labels = (props[u"rainMsgMap"]).split(u";")
						if x in [0,1,2,3,4]:
							if x >1: 
								rainChanges.append([u"lastRain",dd,dd,""])
							if len(labels) > x:
								rainChanges.append([cc, labels[x],labels[x],""])
								if whichKeysToDisplay == cc: 
									rainChanges.append([u"status", labels[x], labels[x],""])
					elif cc == u"nBuckets":
						try: x = int(data[cc])
						except: x = 0
						rainChanges.append([cc, int(x),unicode(int(x)),""])
					elif cc == u"nBucketsTotal":
						try: x = int(data[cc])
						except: x = 0
						rainChanges.append([cc, int(x),unicode(int(x)),""])
					elif cc == u"bucketSize":
						try: 
							xx = u"0[{}]".format(unit)
							x = float(data[cc])*mult
							if x > 0:  xx = u"{:.2f}[{}]".format(x, unit)
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
			if unicode(e) != u"None":
				self.indiLOG.log(40,u"Line {} has error={}".format(sys.exc_traceback.tb_lineno, e))
			self.indiLOG.log(40,unicode(data))
		return


###-------------------------------------------------------------------------####
	def updateBLERuuviTag(self, dev, data, whichKeysToDisplay,pi):
		try:
			self.setStatusCol(dev,u"measurementCount",		 data[u"measurementCount"],	u"{}".format(data[u"measurementCount"]),				whichKeysToDisplay,"","",decimalPlaces=0)
			self.setStatusCol(dev,u"movementCount",			 data[u"movementCount"],	u"{}".format(data[u"movementCount"]),				whichKeysToDisplay,"","",decimalPlaces=0)

		except Exception, e:
			if unicode(e) != u"None":
				self.indiLOG.log(40,u"Line {} has error={}".format(sys.exc_traceback.tb_lineno, e))
			self.indiLOG.log(40,unicode(data))
		return

###-------------------------------------------------------------------------####
	def updateCommonStates(self, dev, data, whichKeysToDisplay,pi):
		try:
				#if dev.id == 985980096: self.indiLOG.log(20,u"updateCommonStates: pi#:{}, {} data{},\n whichKeysToDisplay:{}".format(pi, dev.name,data,whichKeysToDisplay))
				if u"rssi" in data 											and u"rssi" in dev.states and unicode(data[u"rssi"]) != unicode(dev.states[u"rssi"]):		
									self.addToStatesUpdateDict(dev.id, u"rssi", data[u"rssi"])	

				if u"txPower" in data 										and u"txPower" in dev.states and unicode(data[u"txPower"]) != unicode(dev.states[u"txPower"]):		
									self.addToStatesUpdateDict(dev.id, u"txPower", data[u"txPower"])	

				if u"batteryLevel" in data 	and data[u"batteryLevel"] !="" 	and u"batteryLevel" in dev.states and unicode(data[u"batteryLevel"]) != unicode(dev.states[u"batteryLevel"]):	
									self.addToStatesUpdateDict(dev.id, u"batteryLevel", data[u"batteryLevel"])	

				if u"batteryVoltage" in data and data[u"batteryVoltage"] !="" and u"batteryVoltage" in dev.states and unicode(data[u"batteryVoltage"]) != unicode(dev.states[u"batteryVoltage"]):	
									self.addToStatesUpdateDict(dev.id, u"batteryVoltage", data[u"batteryVoltage"])	

				if u"trigger" in data and data[u"trigger"] !="" 				and u"trigger" in dev.states and unicode(data[u"trigger"]) != unicode(dev.states[u"trigger"]):		
									self.setStatusCol(dev,u"trigger",	data[u"trigger"],							unicode(data[u"trigger"]),							whichKeysToDisplay,"","",decimalPlaces=0)

				if  u"accelerationX" in data and  data[u"accelerationX"] != "" and u"accelerationX" in dev.states and unicode(data[u"accelerationX"]) != unicode(dev.states[u"accelerationX"]):
									self.setStatusCol(dev,u"accelerationX",			 data[u"accelerationX"],			 u"{} [cm/s^2]".format(data[u"accelerationX"]),		whichKeysToDisplay,"","",decimalPlaces=0)

				if u"accelerationY" in data and  data[u"accelerationY"] != "" and u"accelerationY" in dev.states and unicode(data[u"accelerationY"]) != unicode(dev.states[u"accelerationY"]):
									self.setStatusCol(dev,u"accelerationY",			 data[u"accelerationY"],			 u"{} [cm/s^2]".format(data[u"accelerationY"]),		whichKeysToDisplay,"","",decimalPlaces=0)

				if  u"accelerationZ" in data and  data[u"accelerationZ"] != "" and u"accelerationZ" in dev.states and unicode(data[u"accelerationZ"]) != unicode(dev.states[u"accelerationZ"]):
									self.setStatusCol(dev,u"accelerationZ",			 data[u"accelerationZ"],			 u"{} [cm/s^2]".format(data[u"accelerationZ"]),		whichKeysToDisplay,"","",decimalPlaces=0)

				if  u"accelerationTotal" in data and  data[u"accelerationTotal"] != "" and u"accelerationTotal" in dev.states and unicode(data[u"accelerationTotal"]) != unicode(dev.states[u"accelerationTotal"]):
									self.setStatusCol(dev,u"accelerationTotal",		 data[u"accelerationTotal"],		 u"{} [cm/s^2]".format(data[u"accelerationTotal"]),	whichKeysToDisplay,"","",decimalPlaces=0)

				if  u"accelerationXYZMaxDelta" in data and  data[u"accelerationXYZMaxDelta"] != "" and u"accelerationXYZMaxDelta" in dev.states and unicode(data[u"accelerationXYZMaxDelta"]) != unicode(dev.states[u"accelerationXYZMaxDelta"]):
									self.setStatusCol(dev,u"accelerationXYZMaxDelta",data[u"accelerationXYZMaxDelta"],u"{} [cm/s^2]".format(data[u"accelerationXYZMaxDelta"]),whichKeysToDisplay,"","",decimalPlaces=0)

				if  u"acceleratiaccelerationVectorDeltaonX" in data and  data[u"accelaccelerationVectorDeltaerationX"] != "" and "accelerationVectorDelta" in dev.states and unicode(data[u"accelerationVectorDelta"]) != unicode(dev.states[u"accelerationVectorDelta"]):
									self.setStatusCol(dev,u"accelerationVectorDelta",data[u"accelerationVectorDelta"],"{} %".format(data[u"accelerationVectorDelta"]),	whichKeysToDisplay,"","",decimalPlaces=0)

				if  u"secsSinceStart" in data and  data[u"secsSinceStart"] != "" and u"secsSinceStart" in dev.states and unicode(data[u"secsSinceStart"]) != unicode(dev.states[u"secsSinceStart"]):
									self.setStatusCol(dev,u"secsSinceStart",data[u"secsSinceStart"],"{}".format(data[u"secsSinceStart"]),	whichKeysToDisplay,"","",decimalPlaces=0)

				if  u"counter" in data and  data[u"counter"] != "" and u"counter" in dev.states and unicode(data[u"counter"]) != unicode(dev.states[u"counter"]):
									self.setStatusCol(dev,u"counter",data[u"counter"],u"{}".format(data[u"counter"]),	whichKeysToDisplay,"","",decimalPlaces=0)

				if  u"chipTemperature" in data and  data[u"chipTemperature"] != "" and u"chipTemperature" in dev.states: 
					x, UI, decimalPlaces, useFormat  = self.convTemp(data[u"chipTemperature"])
					if unicode(x) != unicode(dev.states[u"chipTemperature"]):
						self.addToStatesUpdateDict(dev.id, u"chipTemperature", x)

				if  "lastUpdateFromRPI" in dev.states and  unicode(pi) != unicode(dev.states[u"lastUpdateFromRPI"]): 															
									self.addToStatesUpdateDict(dev.id, u"lastUpdateFromRPI", pi)
		except Exception, e:
			if unicode(e) != u"None":
				self.indiLOG.log(40,u"Line {} has error={}".format(sys.exc_traceback.tb_lineno, e))
			self.indiLOG.log(40,unicode(data))



###-------------------------------------------------------------------------####
	def updateBLEiBS0xRG(self, dev, data, whichKeysToDisplay,pi):
		try:

				if u"onOff1" in data and "button" in dev.states:
					self.setStatusCol(dev,u"button",		 	data[u"onOff1"],			 		 	unicode(data[u"onOff1"]),						whichKeysToDisplay,"","",decimalPlaces=0)

				if u"onOff" in data and "onOffState" in dev.states: 		self.addToStatesUpdateDict(dev.id, u"onOffState", data[u"onOff"]) 

		except Exception, e:
			if unicode(e) != u"None":
				self.indiLOG.log(40,u"Line {} has error={}".format(sys.exc_traceback.tb_lineno, e))
			self.indiLOG.log(40,unicode(data))



###-------------------------------------------------------------------------####
	def updateBLEiSensor(self, dev, data, whichKeysToDisplay,pi):
		try:


			props = dev.pluginProps
			if u"onOffSetting" in props and props[u"onOffSetting"] == u"on=green,off=grey": 
				inverse = False
			else:
				inverse = True #on=red,off=green

			stChanged = False
			if dev.deviceTypeId == u"BLEiSensor-on":
				if u"onOff" in data and data[u"onOff"]:
					self.addToStatesUpdateDict(dev.id, u"previousOnEvent", 	dev.states[u"currentOnEvent"]) 
					self.addToStatesUpdateDict(dev.id, u"currentOnEvent", 	datetime.datetime.now().strftime(_defaultDateStampFormat)) 
					self.addToStatesUpdateDict(dev.id, u"onOffState",  		True) 
					dev.updateStateImageOnServer(indigo.kStateImageSel.SensorOn)
					self.delayedActions[u"data"].put( {u"actionTime":time.time()+1.1  , u"devId":dev.id,u"image":u"off", u"updateItems":[{u"stateName":u"onOffState", u"value":False}]})

			else:
				if u"onOff" in data and u"onOffState" in dev.states:
					if data[u"onOff"]: 
						if not dev.states[u"onOffState"]:
							self.addToStatesUpdateDict(dev.id, u"previousOnEvent", 	dev.states[u"currentOnEvent"]) 
							self.addToStatesUpdateDict(dev.id, u"currentOnEvent", 	datetime.datetime.now().strftime(_defaultDateStampFormat)) 
							self.addToStatesUpdateDict(dev.id, u"onOffState",  		True) 
							if inverse:		dev.updateStateImageOnServer(indigo.kStateImageSel.SensorTripped)
							else:			dev.updateStateImageOnServer(indigo.kStateImageSel.SensorOn)
							stChanged = True
					else:	
						if dev.states[u"onOffState"]:
							self.addToStatesUpdateDict(dev.id,u"onOffState",  False) 
							if inverse:		dev.updateStateImageOnServer(indigo.kStateImageSel.SensorOn)
							else:			dev.updateStateImageOnServer(indigo.kStateImageSel.SensorOff)
							stChanged = True
				else: pass

			if u"SOS" 		in data and "SOS" 			in dev.states:	
				if data[u"SOS"]:
					self.addToStatesUpdateDict(dev.id, u"previousOnEvent", 	dev.states[u"currentOnEvent"]) 
					self.addToStatesUpdateDict(dev.id, u"currentOnEvent", 	datetime.datetime.now().strftime(_defaultDateStampFormat)) 
					self.addToStatesUpdateDict(dev.id, u"previousOnType", 	dev.states[u"currentOnType"]) 
					self.addToStatesUpdateDict(dev.id, u"currentOnType",  	"SOS") 
					self.setStatusCol(dev, u"status", 1, "SOS", whichKeysToDisplay, "","")
					self.addToStatesUpdateDict(dev.id,u"onOffState",  		True) 
					dev.updateStateImageOnServer(indigo.kStateImageSel.SensorOn)
					self.delayedActions[u"data"].put( {u"actionTime":time.time()+1.1  , u"devId":dev.id,u"image":u"off", u"updateItems":[{u"stateName":u"onOffState", u"value":False}]})
				self.addToStatesUpdateDict(dev.id, u"SOS", 					data[u"SOS"]) 

			if u"home" 		in data and u"home" 			in dev.states:	
				if data[u"home"]:
					self.addToStatesUpdateDict(dev.id, u"previousOnEvent", 	dev.states[u"currentOnEvent"]) 
					self.addToStatesUpdateDict(dev.id, u"currentOnEvent", 	datetime.datetime.now().strftime(_defaultDateStampFormat)) 
					self.addToStatesUpdateDict(dev.id, u"previousOnType", 	dev.states[u"currentOnType"]) 
					self.addToStatesUpdateDict(dev.id, u"currentOnType",  	u"home") 
					self.setStatusCol(dev, u"status", 2, "home", whichKeysToDisplay, "","")
					self.addToStatesUpdateDict(dev.id,u"onOffState",  		True) 
					dev.updateStateImageOnServer(indigo.kStateImageSel.SensorOn)
					self.delayedActions[u"data"].put( {u"actionTime":time.time()+1.1  , u"devId":dev.id,u"image":u"off", u"updateItems":[{u"stateName":u"onOffState", u"value":False}]})
				self.addToStatesUpdateDict(dev.id, u"home", 				data[u"home"]) 

			if u"away" 		in data and u"away" 			in dev.states:	
				if data[u"away"]:
					self.addToStatesUpdateDict(dev.id, u"previousOnEvent", 	dev.states[u"currentOnEvent"]) 
					self.addToStatesUpdateDict(dev.id, u"currentOnEvent", 	datetime.datetime.now().strftime(_defaultDateStampFormat)) 
					self.addToStatesUpdateDict(dev.id, u"previousOnType", 	dev.states[u"currentOnType"]) 
					self.addToStatesUpdateDict(dev.id, u"currentOnType",  	u"away") 
					self.setStatusCol(dev, u"status", 3, u"away", whichKeysToDisplay, "","")
					self.addToStatesUpdateDict(dev.id,u"onOffState",  		True) 
					dev.updateStateImageOnServer(indigo.kStateImageSel.SensorOn)
					self.delayedActions[u"data"].put( {u"actionTime":time.time()+1.1  , u"devId":dev.id,u"image":u"off", u"updateItems":[{u"stateName":u"onOffState", u"value":False}]})
				self.addToStatesUpdateDict(dev.id, u"away", 				data[u"away"]) 

			if u"disarm" 	in data and u"disarm" 		in dev.states:	
				if data[u"disarm"]:
					self.addToStatesUpdateDict(dev.id, u"previousOnEvent", 	dev.states[u"currentOnEvent"]) 
					self.addToStatesUpdateDict(dev.id, u"currentOnEvent", 	datetime.datetime.now().strftime(_defaultDateStampFormat)) 
					self.addToStatesUpdateDict(dev.id, u"previousOnType", 	dev.states[u"currentOnType"]) 
					self.addToStatesUpdateDict(dev.id, u"currentOnType",  	u"disarm") 
					self.setStatusCol(dev, u"status", 4, u"disarm", whichKeysToDisplay, "","")
					self.addToStatesUpdateDict(dev.id,u"onOffState",  		True) 
					dev.updateStateImageOnServer(indigo.kStateImageSel.SensorOn)
					self.delayedActions[u"data"].put( {u"actionTime":time.time()+1.1  , u"devId":dev.id,u"image":u"off", u"updateItems":[{u"stateName":u"onOffState", u"value":False}]})
				self.addToStatesUpdateDict(dev.id, u"disarm", 				data[u"disarm"]) 

			if u"bits" 		in data  and u"bits" 		in dev.states:	self.addToStatesUpdateDict(dev.id, u"bits", 				data[u"bits"]) 
			if u"state" 	in data  and u"state" 		in dev.states:	self.addToStatesUpdateDict(dev.id, u"state", 				data[u"state"]) 
			if u"sensorType" in data and u"sensorType" 	in dev.states:	self.addToStatesUpdateDict(dev.id, u"sensorType", 			data[u"sensorType"]) 
			if u"sendsAlive" in data and u"sendsAlive" 	in dev.states:	self.addToStatesUpdateDict(dev.id, u"sendsAlive", 			data[u"sendsAlive"]) 
			if u"lowVoltage" in data and u"lowVoltage" 	in dev.states:	self.addToStatesUpdateDict(dev.id, u"lowVoltage", 			data[u"lowVoltage"]) 
			if u"tampered" 	in data  and u"tampered" 	in dev.states:	self.addToStatesUpdateDict(dev.id, u"tampered", 			data[u"tampered"]) 

			if 						u"lastAliveMessage" in dev.states: 	self.addToStatesUpdateDict(dev.id, u"lastAliveMessage", 	datetime.datetime.now().strftime(_defaultDateStampFormat)) 

			if "currentOnEvent" in dev.states and not stChanged: 		self.addToStatesUpdateDict(dev.id, u"lastSensorChange", 	dev.states[u"currentOnEvent"]) 

		# set to grey if expired	 dev.updateStateImageOnServer(indigo.kStateImageSel.SensorOff)

		except Exception, e:
			if unicode(e) != u"None":
				self.indiLOG.log(40,u"Line {} has error={}".format(sys.exc_traceback.tb_lineno, e))
			self.indiLOG.log(40,unicode(data))
		return

###-------------------------------------------------------------------------####
	def updateBLEiBSxxOneOnOff(self, dev, data, whichKeysToDisplay,pi):
		try:
			props = dev.pluginProps
			if u"onOffSetting" in props and props[u"onOffSetting"] == u"on=green,off=grey": 
				inverse = False
			else:
				inverse = True

			stChanged = False
			if data[u"onOff"]: 
				if not dev.states[u"onOffState"]:
					self.addToStatesUpdateDict(dev.id, u"previousOnEvent", 	dev.states[u"currentOnEvent"]) 
					self.addToStatesUpdateDict(dev.id, u"currentOnEvent", 	datetime.datetime.now().strftime(_defaultDateStampFormat)) 
					self.addToStatesUpdateDict(dev.id,u"onOffState",  		True) 
					if not inverse:	dev.updateStateImageOnServer(indigo.kStateImageSel.SensorOn)
					else:			dev.updateStateImageOnServer(indigo.kStateImageSel.SensorTripped)
					stChanged = True
				if not stChanged: 	self.addToStatesUpdateDict(dev.id, u"lastSensorChange", 	dev.states[u"currentOnEvent"]) 

			else:	
				if dev.states[u"onOffState"]:
					self.addToStatesUpdateDict(dev.id,u"onOffState",  		False) 
					self.addToStatesUpdateDict(dev.id,u"previousOffEvent", 	dev.states[u"currentOffEvent"]) 
					self.addToStatesUpdateDict(dev.id,u"currentOffEvent", 	datetime.datetime.now().strftime(_defaultDateStampFormat)) 
					dev.updateStateImageOnServer(indigo.kStateImageSel.SensorOff)
					stChanged = True
				if not stChanged: 	self.addToStatesUpdateDict(dev.id, u"lastSensorChange", 	dev.states[u"currentOffEvent"]) 



		except Exception, e:
			if unicode(e) != u"None":
				self.indiLOG.log(40,u"Line {} has error={}".format(sys.exc_traceback.tb_lineno, e))
			self.indiLOG.log(40,unicode(data))
		return


###-------------------------------------------------------------------------####
	def updateAPRILaccel(self, dev, data, whichKeysToDisplay,pi):
		try:
			if u"onOff1" in data:
				self.addToStatesUpdateDict(dev.id,u"onOffState",  	data[u"onOff1"]) 
				self.setStatusCol(dev,u"move",		 		  		data[u"onOff1"],				 	 unicode(data[u"onOff1"]),						whichKeysToDisplay,"","")
				if data[u"onOff1"]: 
						self.addToStatesUpdateDict(dev.id,u"previousMove", dev.states[u"currentMove"]) 
						self.addToStatesUpdateDict(dev.id,u"currentMove", datetime.datetime.now().strftime(_defaultDateStampFormat)) 

			if u"onOff" in data:
				self.setStatusCol(dev,u"button",		 		  	data[u"onOff"],				 		 unicode(data[u"onOff"]),						whichKeysToDisplay,"","")
				if data[u"onOff"]: 
						self.addToStatesUpdateDict(dev.id,u"previousOnEvent", dev.states[u"currentOnEvent"]) 
						self.addToStatesUpdateDict(dev.id,u"currentOnEvent", datetime.datetime.now().strftime(_defaultDateStampFormat)) 

		except Exception, e:
			if unicode(e) != u"None":
				self.indiLOG.log(40,u"Line {} has error={}".format(sys.exc_traceback.tb_lineno, e))
			self.indiLOG.log(40,unicode(data))
		return


###-------------------------------------------------------------------------####
	def updateBLEiBS03(self, dev, data, whichKeysToDisplay,pi):
		try:
			if u"onOff" in data:
				self.addToStatesUpdateDict(dev.id,u"onOffState",  data[u"onOff"]) 
				self.setStatusCol(dev,u"magSwitch",		 		  data[u"onOff"],				 		 unicode(data[u"onOff"]),						whichKeysToDisplay,"","")
				self.setStatusCol(dev,u"button",		 		  data[u"onOff1"],				 		 unicode(data[u"onOff1"]),						whichKeysToDisplay,"","")

				if not dev.states[u"button"]:
					if data[u"onOff"]: 
						self.addToStatesUpdateDict(dev.id,u"previousOnEvent", dev.states[u"currentOnEvent"]) 
						self.addToStatesUpdateDict(dev.id,u"currentOnEvent", datetime.datetime.now().strftime(_defaultDateStampFormat)) 
				else:
					if not data[u"onOff"]: 
						self.addToStatesUpdateDict(dev.id,u"previousOffEvent", dev.states[u"currentOffEvent"]) 
						self.addToStatesUpdateDict(dev.id,u"currentOffEvent", datetime.datetime.now().strftime(_defaultDateStampFormat)) 

				if not dev.states[u"magSwitch"]:
					if data[u"onOff1"]: 
						self.addToStatesUpdateDict(dev.id,u"previousOnEvent", dev.states[u"currentOnEvent"]) 
						self.addToStatesUpdateDict(dev.id,u"currentOnEvent", datetime.datetime.now().strftime(_defaultDateStampFormat)) 
				else:
					if not data[u"onOff1"]: 
						self.addToStatesUpdateDict(dev.id,u"previousOffEvent", dev.states[u"currentOffEvent"]) 
						self.addToStatesUpdateDict(dev.id,u"currentOffEvent", datetime.datetime.now().strftime(_defaultDateStampFormat)) 


		except Exception, e:
			if unicode(e) != u"None":
				self.indiLOG.log(40,u"Line {} has error={}".format(sys.exc_traceback.tb_lineno, e))
			self.indiLOG.log(40,unicode(data))
		return




####-------------------------------------------------------------------------####
	def updatePMAIRQUALITY(self, dev, data, whichKeysToDisplay):
		try:
			for cc in [u"pm10_standard",u"pm25_standard",u"pm100_standard",u"pm10_env",u"pm25_env",u"pm100_env",u"particles_03um",u"particles_05um",u"particles_10um",u"particles_25um",u"particles_50um",u"particles_100um"]:
				if cc in data:
					if cc.find(u"pm") >-1: units = u"ug/m3"
					else:				  units  = u"C/0.1L"
					x, UI  = int(float(data[cc])), u"{}={:.0f}[{}]".format(cc,float(data[cc]),units)

					self.setStatusCol(dev,cc,x,UI,whichKeysToDisplay,"","",decimalPlaces=0)

					if cc == u"pm25_standard":
						if	  x < 12:		airQuality = u"Good"
						elif  x < 35.4:		airQuality = u"Moderate" 
						elif  x < 55.4:		airQuality = u"Unhealthy Sensitve" 
						elif  x < 150.4:	airQuality = u"Unhealthy" 
						elif  x < 250.4:	airQuality = u"Very Unhealthy" 
						else:				airQuality = u"Hazardous"


						self.setStatusCol(dev,u"airQuality",airQuality,"Air Quality is "+airQuality,whichKeysToDisplay,"","",decimalPlaces=1)

						useSetStateColor = False
						if  cc == whichKeysToDisplay: 
							useSetStateColor = self.setStateColor(dev, dev.pluginProps, data[cc])
						if not useSetStateColor:
							if	 airQuality == u"Good":		 dev.updateStateImageOnServer(indigo.kStateImageSel.SensorOn)
							elif airQuality == u"Moderate":	 dev.updateStateImageOnServer(indigo.kStateImageSel.SensorOff)
							else:							 dev.updateStateImageOnServer(indigo.kStateImageSel.SensorTripped)

		except Exception, e:
			if unicode(e) != u"None":
				self.indiLOG.log(40,u"Line {} has error={}".format(sys.exc_traceback.tb_lineno, e))
			self.indiLOG.log(40,unicode(data))
		return



####-------------------------------------------------------------------------####
	def setPressureDisplay(self, dev, props, data, whichKeysToDisplay, newStatus):
		try:
			updateProps = False
			doUpdate    = []
			if u"press" in data:
				p = float(data[u"press"])

				if self.pressureUnits == u"atm":
					useFormat = u"{:6.3f} atm" ;		decimalPlaces = 4; mult = 0.000009869233
					p *= mult ; pu = useFormat.format(p)
				elif self.pressureUnits == u"bar":
					useFormat = u"{:6.3f} Bar" ;		decimalPlaces = 4; mult = 0.00001
					p *= mult ; pu = useFormat.format(p)
				elif self.pressureUnits.lower() == u"mbar":
					useFormat = u"{:6.1f} mBar";		decimalPlaces = 1; mult = 0.01
					p *= mult; pu = useFormat.format(p)
				elif self.pressureUnits == u"mm":
					useFormat = u"{:6.0f} mmHg";		decimalPlaces = 0; mult = 0.00750063
					p *= mult ; pu = useFormat.format(p)
				elif self.pressureUnits == u"Torr":
					useFormat = u"{:.0f} Torr" ;		decimalPlaces = 0; mult = 0.00750063
					p *= mult; pu = useFormat.format(p)
				elif self.pressureUnits == u"inches":
					useFormat = u"{:6.2f} inches";	decimalPlaces = 2; mult = 0.000295299802
					p *= mult ; pu = useFormat.format(p)
				elif self.pressureUnits == u"PSI":
					useFormat = u"{:6.2f} PSI";		decimalPlaces = 2; mult = 0.000145038
					p *= mult ; pu = useFormat.format(p)
				elif self.pressureUnits == u"hPascal":
					useFormat = u"{:.0f} hPa";		decimalPlaces = 0; mult = 0.01
					p *= mult ; pu = useFormat.format(p)
				else:
					useFormat = u"{:.0f}  Pa"; 		decimalPlaces = 0; mult = 1.
					p *= mult ; pu = useFormat.format(p)
				#self.indiLOG.log(20,u"p ={}  units:{}".format( p, self.pressureUnits ) )
				pu = pu.strip()
				newStatus = self.setStatusCol(dev, u"Pressure", p, pu, whichKeysToDisplay, "",newStatus, decimalPlaces = 0)
				updateProps, doUpdate = self.updateChangedValues(dev, p, props, u"Pressure", useFormat, whichKeysToDisplay, 0)

		except Exception, e:
			if unicode(e) != u"None":
				self.indiLOG.log(40,u"Line {} has error={}".format(sys.exc_traceback.tb_lineno, e))
		#self.indiLOG.log(20,u"returning {} {} {} dat:{} ".format(useFormat, decimalPlaces, p, data) )
		return newStatus, updateProps, doUpdate


####-------------------------------------------------------------------------####
	def setProximityDisplay(self, dev, props, data, whichKeysToDisplay, newStatus):
		try:
			updateProps = False
			doUpdate    = []
			if u"proximity" in data:
				p = float(data[u"proximity"])
				useFormat = u"{:.1f} m"; 		decimalPlaces = 0; mult = 1.
				p *= mult ; pu = useFormat.format(p)
				#self.indiLOG.log(20,u"p ={}  units:{}".format( p, self.pressureUnits ) )
				pu = pu.strip()
				newStatus = self.setStatusCol(dev, u"Proximity", p, pu, whichKeysToDisplay, "",newStatus, decimalPlaces = 0)
				updateProps, doUpdate = self.updateChangedValues(dev, p, props, u"Proximity", useFormat, whichKeysToDisplay, 0)

		except Exception, e:
			if unicode(e) != u"None":
				self.indiLOG.log(40,u"Line {} has error={}".format(sys.exc_traceback.tb_lineno, e))
		#self.indiLOG.log(20,u"returning {} {} {} dat:{} ".format(useFormat, decimalPlaces, p, data) )
		return newStatus, updateProps, doUpdate



####-------------------------------------------------------------------------####
	def setMoistureDisplay(self, dev, props, data, whichKeysToDisplay, newStatus):
		try:
			updateProps = False
			doUpdate    = []
			if u"moisture" in data:
				raw = int(float(data[u"moisture"]))
				try: 	minM = float(props[u"minMoisture"])
				except: minM = 330.
				try: 	maxM = float(props[u"maxMoisture"])
				except: maxM = 630.
				relM = int(100*float(raw-minM)/max(1.,maxM-minM))
				relMU = u"{}%".format(relM)
		
				updateProps, doUpdate = self.updateChangedValues(dev, relM, props, u"Moisture", "", "",0)
				self.addToStatesUpdateDict(dev.id, u"Moisture_raw", raw)
				newStatus = self.setStatusCol(dev, u"Moisture", relM, relMU, u"Moisture", "",newStatus, decimalPlaces = 0)

			
		except Exception, e:
			if unicode(e) != u"None":
				self.indiLOG.log(40,u"Line {} has error={}".format(sys.exc_traceback.tb_lineno, e))
		#self.indiLOG.log(20,u"returning {} {} {} dat:{} ".format(useFormat, decimalPlaces, p, data) )
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

			#if dev.name =="s-11-iSensor-door-button": indigo.server.log(dev.name+u"  in setStatusCol "+key+u"  "+unicode(value)+u"   "+unicode(valueUI))

			if whichKeysToDisplay !="":
				for i in range(whichKeysToDisplaylength):
					if whichKeysToDisplayList[i] == key:
						#if dev.name == u"s-11-iSensor-door-button": indigo.server.log(dev.name+u"  in after  whichKeysToDisplayList")

						if currentDisplay[i] != valueUI:
							if i==0:
								if  not self.setStateColor(dev, dev.pluginProps, value):
									if  image != "":
										dev.updateStateImageOnServer(image)
							currentDisplay[i] = valueUI		   
							newStatus= u"/".join(currentDisplay)
							#if dev.name == u"s-11-iSensor-door-button": indigo.server.log(dev.name+u"  in bf   sensorValue  states:"+unicode(dev.states))
							if u"sensorValue" in dev.states:
								#if dev.name =="s-3-rainSensorRG11": indigo.server.log(dev.name+u" af sensorValue")

								# make a very small random number must not be same, otehr no update if it is not a number 
								try: 	x = float(value)
								except:
									tt = time.time()
									x = (tt - int(tt))/10000000000000.
									decimalPlaces =""
									##indigo.server.log(dev.name+u"  setStatusCol key:"+key+u"  value:"+unicode(value) +u"  x:"+unicode(x)+u"  decimalPlaces:"+unicode(decimalPlaces))
								#if dev.name =="s-3-rainSensorRG11": indigo.server.log(dev.name+u"  "+key+u"  "+unicode(value)+u"   "+unicode(x)+u"  "+valueUI)
								if decimalPlaces !="":
									self.addToStatesUpdateDict(dev.id,u"sensorValue", round(x,decimalPlaces), decimalPlaces=decimalPlaces, uiValue=newStatus,force=force)
								else:
									self.addToStatesUpdateDict(dev.id,u"sensorValue", x, uiValue=newStatus,force=force)
							self.addToStatesUpdateDict(dev.id,u"status", newStatus,force=force)
							break


		except Exception, e:
			if unicode(e) != u"None":##
				self.indiLOG.log(40,u"Line {} has error={}".format(sys.exc_traceback.tb_lineno, e))
				self.indiLOG.log(40,u"dev:{}, key:{}".format(dev.name, key))
		return newStatus

 
####-------------------------------------------------------------------------####
	def updateOneWire(self,dev, data, whichKeysToDisplay, piU):

		## add check for addNewOneWireSensors only add new one if TRUE 
		## format:
		#"sensors":{u"Wire18B20":{
		#"1565508294":{u"temp":[{u"28-0316b5fa44ff":u"24.3"}]},
		#"1447141059":{u"temp":[{u"28-0516b332fbff":u"24.8"}]},
		#"416059968": {u"temp":[{u"28-800000035de5":u"21.8"},	{u"28-0416b39944ff":u"24.6"}]},  ## can be multiple 
		#"1874530568":{u"temp":[{u"28-0516b33621ff":u"24.6"}]}}}
		## 
		try:
			for NNN in data[u"temp"]:
				if not isinstance(NNN, type({})): 
					continue ## old format , skip ; must be list
				for serialNumber in NNN:
					temp = NNN[serialNumber]
					if temp == u"85.0":	temp = u"999.9"
					x, UI, decimalPlaces, useFormat  = self.convTemp(temp)
					if dev.states[u"serialNumber"] == "" or dev.states[u"serialNumber"] == serialNumber: # =="" new, ==Serial# already setup
						if dev.states[u"serialNumber"] == "": 
							self.addToStatesUpdateDict(dev.id,u"serialNumber",serialNumber)
							self.setONErPiV(piU,u"piUpToDate", [u"updateParamsFTP"])
						if serialNumber != u"sN= u" + dev.description:
							if dev.description.find(u"sN= u") == 0:
								snOld = dev.description.split(u" ")
								addtext = ""
								if len(snOld) >2: addtext= u" "+ u" ".join(snOld[2:])
								if snOld[1] != serialNumber:
									dev.description = u"sN= u" + serialNumber +addtext
									dev.replaceOnServer()
							else:
								dev.description = u"sN= u" + serialNumber 
								dev.replaceOnServer()
							dev = indigo.devices[dev.id]
						props = dev.pluginProps
						self.setStatusCol( dev, u"Temperature", x, UI, whichKeysToDisplay, indigo.kStateImageSel.TemperatureSensorOn,dev.states[u"status"], decimalPlaces = decimalPlaces )
						updateProps, doUpdate = self.updateChangedValues(dev, x, props, u"Temperature", useFormat, whichKeysToDisplay, decimalPlaces)
						if updateProps: 
							props[doUpdate[0]] = doUpdate[1]
							self.deviceStopCommIgnore = time.time()
							dev.replacePluginPropsOnServer(props)

					else: # try to somewhere else
						#indigo.server.log(u"  not present, checking other " )
						foundSelf	= False
						for dev0 in indigo.devices.iter(u"props.isSensorDevice"):
							if dev0.deviceTypeId != u"Wire18B20": continue
							if dev0.name == dev.name: continue
							if dev0.states[u"serialNumber"] == serialNumber: 
								#indigo.server.log(u"  found serial number " +dev0.name +u"  "+ serialNumber	)
								foundSelf =True
								self.setStatusCol( dev0, u"Temperature", x, UI, whichKeysToDisplay, indigo.kStateImageSel.TemperatureSensorOn,dev0.states[u"status"],decimalPlaces = decimalPlaces )
								if serialNumber != u"sN= u" + dev0.description:
									dev0.description = u"sN= u" + serialNumber
									dev0.replaceOnServer()
								break
						if not foundSelf : # really not setup
							try:
								props = indigo.devices[int(self.RPI[piU][u"piDevId"])].pluginProps
								if u"addNewOneWireSensors" in props and props[u"addNewOneWireSensors"] == u"1":
									dev1 = indigo.device.create(
											protocol		= indigo.kProtocol.Plugin,
											address			= u"Pi-"+piU,
											name			= dev.name+u"_"+serialNumber,
											pluginId		= self.pluginId,
											deviceTypeId	= u"Wire18B20",
											folder			= self.piFolderId,
											description		= u"sN= u" + serialNumber,
											props			= {u"piServerNumber":piU, u"displayState":u"status", u"displayS":u"Temperature", u"offsetTemp":u"0",  u"displayEnable": u"0", u"isSensorDevice":True,
																u"SupportsSensorValue":True, u"SupportsOnState":False, u"AllowSensorValueChange":False, "AllowOnStateChange":False, u"SupportsStatusRequest":False}
											)

									if u"input"	   not in self.RPI[piU]			 : self.RPI[piU][u"input"] ={}
									if u"Wire18B20" not in self.RPI[piU][u"input"] : self.RPI[piU][u"input"][u"Wire18B20"] ={}
									self.RPI[piU][u"input"][u"Wire18B20"][unicode(dev1.id)] = ""
									self.addToStatesUpdateDict(unicode(dev1.id),u"serialNumber",serialNumber)
									self.setStatusCol( dev1, u"Temperature", x, UI, whichKeysToDisplay, indigo.kStateImageSel.TemperatureSensorOn,dev1.states[u"status"], decimalPlaces = decimalPlaces )
									props = dev1.pluginProps
									updateProps, doUpdate = self.updateChangedValues(dev, x, props, "Temperature", useFormat, whichKeysToDisplay, decimalPlaces)
									if updateProps: 
										props[doUpdate[0]] = doUpdate[1]
										self.deviceStopCommIgnore = time.time()
										dev1.replacePluginPropsOnServer(props)
									self.executeUpdateStatesDict(onlyDevID=unicode(dev1.id), calledFrom=u"updateOneWire")
									self.setONErPiV(piU,u"piUpToDate", [u"updateParamsFTP"])
									self.saveConfig()
							except Exception, e:
								self.indiLOG.log(40,u"Line {} has error={}".format(sys.exc_traceback.tb_lineno, e))
								continue

		except Exception, e:
				self.indiLOG.log(40,u"Line {} has error={}".format(sys.exc_traceback.tb_lineno, e))


 
####-------------------------------------------------------------------------####
	def updateBLEmyBLUEt(self, dev, data, props, whichKeysToDisplay):
		try:
			x, UI, decimalPlaces, useFormat  = self.convTemp(data[u"temp"])
			self.setStatusCol( dev, u"Temperature", x, UI, whichKeysToDisplay, indigo.kStateImageSel.TemperatureSensorOn,dev.states[u"status"], decimalPlaces = decimalPlaces )
			updateProps, doUpdate = self.updateChangedValues(dev, x, props, u"Temperature", useFormat, whichKeysToDisplay, decimalPlaces)
			if updateProps: 
				props[doUpdate[0]] = doUpdate[1]
				self.deviceStopCommIgnore = time.time()
				dev.replacePluginPropsOnServer(props)
				props[doUpdate[0]] = doUpdate[1]

		except Exception, e:
			if unicode(e) != u"None":
				self.indiLOG.log(40,u"Line {} has error={}".format(sys.exc_traceback.tb_lineno, e))


 
####-------------------------------------------------------------------------####
	def updatePULSE(self, dev, data, whichKeysToDisplay):
		if self.decideMyLog(u"SensorData"): self.indiLOG.log(10,u"updatePULSE {}".format(data))
		props = dev.pluginProps
		try:	
			dd = datetime.datetime.now().strftime(_defaultDateStampFormat) 
			countList = [(0,0),(0,0)] # is list of [[time0 ,count0], [time1 ,count1],...]  last counts up to 3600 secs,  then pop out last
			if u"countList" in props: countList= json.loads(props[u"countList"])
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
						#self.indiLOG.log(10,u"updatePULSE bf count pop countList:{}".format(countList) )
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
 
				#self.indiLOG.log(20,u"updatePULSE minPointer:{}; tt:{:.0f}; countList:{}".format(minPointer, time.time(), countList) )
				self.setStatusCol( dev, u"count", data[u"count"], u"{:.0f}[c]".format(data[u"count"]), whichKeysToDisplay, "","", decimalPlaces = "" )
				if cOld <= data[u"count"]: 
					countsPerMinute =   60.    * ( countList[minPointer][1]  - countList[0][1] ) /  max(1., ( countList[minPointer][0]  - countList[0][0]) )
					countsPerHour   = 3600.    * ( countList[hourPointer][1] - countList[0][1] ) /  max(1., ( countList[hourPointer][0] - countList[0][0]) )
					countsPerDay    = 3600.*24 * ( countList[-1][1]          - countList[0][1] ) /  max(1., ( countList[-1][0]          - countList[0][0]) )
					#self.indiLOG.log(10,u"updatePULSE cmp:{}; cOld:{};  sdata: {};  tt:{}; dcount:{}; dtt:{}; ll:{}; countList:{}".format(countsPerMinute, cOld, data, time.time(), ( countList[-1][1] - countList[0][1] ), (countList[-1][0]  - countList[0][0]) , len(countList),  countList ) )
					self.setStatusCol( dev, u"countsPerLast", countsPerSecond, 	 u"{:.2f}[c/s]".format(countsPerSecond), whichKeysToDisplay, "","", decimalPlaces = 2 )
					self.setStatusCol( dev, u"countsPerMinute", countsPerMinute, u"{:.2f}[c/m]".format(countsPerMinute), whichKeysToDisplay, "","", decimalPlaces = 2 )
					self.setStatusCol( dev, u"countsPerHour",   countsPerHour,   u"{:.1f}[c/h]".format(countsPerHour),   whichKeysToDisplay, "","", decimalPlaces = 2 )
					self.setStatusCol( dev, u"countsPerDay",    countsPerDay,  	 u"{:.1f}[c/d]".format(countsPerDay),    whichKeysToDisplay, "","", decimalPlaces = 2 )
					if cOld != countList[-1][1]: self.addToStatesUpdateDict(dev.id,u"lastCountTime",dd)
				props[u"countList"] = json.dumps(countList)
				self.deviceStopCommIgnore = time.time()
				dev.replacePluginPropsOnServer(props)
			else:
				pass

			if u"burst" in data and data[u"burst"] !=0 and data[u"burst"] !="":
					self.addToStatesUpdateDict(dev.id,u"ulastBurstTime",dd )

			if u"continuous" in data and data[u"continuous"] !="":
					if data[u"continuous"] > 0: 
						self.addToStatesUpdateDict(dev.id,u"lastContinuousEventTime",dd )
						self.addToStatesUpdateDict(dev.id,u"lastContinuousEventStopTime","")
					else: 
						if dev.states[u"lastContinuousEventStopTime"] == "":
							self.addToStatesUpdateDict(dev.id,u"lastContinuousEventStopTime",dd)

		except Exception, e:
			if unicode(e) != u"None":
				self.indiLOG.log(40,u"Line {} has error={}".format(sys.exc_traceback.tb_lineno, e))
		return 
 
 

####-------------------------------------------------------------------------####
## this will update the states xxxChangeyyMinutes / Hours eg TemperatureChange10Minutes TemperatureChange1Hour TemperatureChange6Hour
## has problems when there are no updates, values can be  stale over days 
	def updateChangedValues(self,dev, value, props, propToUpdate, useFormat, whichKeysToDisplay, decimalPlaces):
		try:	
			if propToUpdate not in dev.states: 					
				self.indiLOG.log(20,u"updateChangedValues: prop{}  \nnot in props: {}".format(propToUpdate, props))
				return False, []

			updateList = []
			for state in dev.states:
				## state  eg =  "temperatureChange1Hour"
				if state.find(propToUpdate+u"Change") == 0:
					upU = state.split(u"Change")[1]
					if len(upU) < 2: continue
					if upU.find(u"Hour") >-1:     updateN = u"Hour";   updateMinutes = 3600
					elif upU.find(u"Minute") >-1: updateN = u"Minute"; updateMinutes = 60
					else: continue
					amount = upU.split(updateN)[0]
					updateList.append( {u"state":state, u"unit":updateN, u"deltaSecs":updateMinutes * int(amount), u"pointer":0, u"changed":0} )

			##updateList ==[{u"state":u"temperatureChange1Hour", u"unit":u"Hour", udeltaSecs":60, u"pointer":0, u"changed":0}, ...] )

			updateList = sorted(updateList, key = lambda x: x[u"deltaSecs"])				
			if len(updateList) < 1: return False, []

			## get last list
			if propToUpdate+u"list" in props: 
				valueList = json.loads(props[propToUpdate+u"list"])
			else:
				valueList = [(0,0),(0,0)]


			if type(value) == float and useFormat.find(u"{:d}") ==-1:	valueList.append([int(time.time()),round(value,decimalPlaces)])
			else:														valueList.append([int(time.time()),int(value)])

			jj 		= len(updateList)
			cutMax	= updateList[-1][u"deltaSecs"]
			ll		= len(valueList)
			for ii in range(ll):
				if len(valueList) <= 2: break
				if (valueList[-1][0] - valueList[0][0]) > cutMax: valueList.pop(0)
				else: 				    break

						
			ll = len(valueList)
			if ll > 1:
				for kk in range(jj):
					cut = updateList[kk][u"deltaSecs"]
					updateList[kk][u"pointer"] = 0
					if cut != cutMax: # we can skip the largest, must be first and last entry
						for ii in range(ll-1,-1,-1):
							if (valueList[-1][0] - valueList[ii][0]) <= cut:
								updateList[kk][u"pointer"] = ii
							else:
								break

					changed			 = ( valueList[-1][1] - valueList[updateList[kk][u"pointer"]][1] )
					try: 	uChanged = useFormat.format(changed)
					except: uChanged = unicode(changed)
					#updateList[kk][u"changed"] = uChanged
					self.setStatusCol( dev, updateList[kk][u"state"], changed, uChanged, whichKeysToDisplay, "","", decimalPlaces = decimalPlaces )

			return True, [propToUpdate+u"list",json.dumps(valueList).strip(u" ")]

		except Exception, e:
			#if unicode(e) != u"None":
				self.indiLOG.log(40,u"Line {} has error={}".format(sys.exc_traceback.tb_lineno, e))
		return False, []
 

####-------------------------------------------------------------------------####
	def updateTEA5767(self,sensors,sensor):
		if self.decideMyLog(u"OutputDevice"): self.indiLOG.log(10,sensor+u"     "+unicode(sensors))
		for devId in sensors:
			try:
				dev = indigo.devices[int(devId)]
				iii = 0
				for channels in sensors[devId][u"channels"]:
					self.indiLOG.log(20,u"updateTEA5767 sensor: "+sensor+u"  "+unicode(channels))
					freq   = channels[u"freq"]
					Signal = channels[u"Signal"]
					ch = u"Channel-{02d}".format(iii)
					self.addToStatesUpdateDict(devId,ch,"f="+unicode(freq)+u"; Sig="+unicode(Signal))
					iii+=1
				for ii in range(iii,41):
					ch = u"Channel-{02d}".format(ii)
					self.addToStatesUpdateDict(devId,ch,"")
			except Exception, e:
				if unicode(e) != u"None":
					self.indiLOG.log(40,u"Line {} has error={}".format(sys.exc_traceback.tb_lineno, e))
		return 
	   
####-------------------------------------------------------------------------####
	def updateGetBeaconParameters(self, pi, data):
## 		format:		data[u"sensors"][u"getBeaconParameters"][mac] = {state:{value}}}

		try:
			if self.decideMyLog(u"BatteryLevel"): self.indiLOG.log(20,u"GetBeaconParameters update received  pi#:{};  data:{}".format(pi, data) )
			for beacon in data:
				if beacon in self.beacons:
					indigoId = int(self.beacons[beacon][u"indigoId"])
					if indigoId > 0:
						dev = indigo.devices[int(indigoId)]
						props = dev.pluginProps
						try: 	batteryLevelLastUpdate = time.mktime(time.strptime(dev.states[u"batteryLevelLastUpdate"], _defaultDateStampFormat ))
						except: batteryLevelLastUpdate = time.mktime(time.strptime(u"2000-01-01 00:00:00", _defaultDateStampFormat ))
						for state in data[beacon]:

							if state == u"batteryLevel"  and u"batteryLevel" in dev.states and u"batteryLevelLastUpdate" in dev.states: 
								# this with an integer data payload = battery level
								if type(data[beacon][state]) == type(1):
									if  data[beacon][state] > 0:
										if self.decideMyLog(u"BatteryLevel"): self.indiLOG.log(20,u"GetBeaconParameters updating state:{} with:{}".format(state, data[beacon][state]) )
										self.addToStatesUpdateDict(indigoId, state, data[beacon][state])
										self.addToStatesUpdateDict(indigoId, "batteryLevelLastUpdate", datetime.datetime.now().strftime(_defaultDateStampFormat))
									else:
										if time.time() - batteryLevelLastUpdate > 24*3600: self.indiLOG.log(20,u"GetBeaconParameters update received pi:{} beacon:{} .. {};  bad data read; last good update was {}, current batterylevel status: {}".format(pi,beacon, data[beacon], dev.states[u"batteryLevelLastUpdate"], dev.states[u"batteryLevel"]  ) )

								# this with a text payload, error message
								else:
									if len(dev.states[u"batteryLevelLastUpdate"] ) < 10:
										self.addToStatesUpdateDict(indigoId, "batteryLevelLastUpdate", "2000-01-01 00:00:00")
									if time.time() - batteryLevelLastUpdate > 24*3600: self.indiLOG.log(20,u"GetBeaconParameters update received pi:{}  beacon:{} .. error msg: {}; last update was {}, current batterylevel status: {}".format(pi,beacon, data[beacon][state], dev.states[u"batteryLevelLastUpdate"], dev.states[u"batteryLevel"] ) )
							else:
								if time.time() - batteryLevelLastUpdate > 24*3600: self.indiLOG.log(20,u"GetBeaconParameters update received pi:{} beacon:{},  wrong beacon device.. error msg: {}".format(pi, beacon, data[beacon][state] ) )
					else:
						self.indiLOG.log(20,u"GetBeaconParameters update received pi:{} beacon:{},  no indigo device present.. msg: {}".format(pi, beacon, data[beacon][state] ) )



		except Exception, e:
			if unicode(e) != u"None":
				self.indiLOG.log(40,u"Line {} has error={}".format(sys.exc_traceback.tb_lineno, e))

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
				upState = u"INPUT_"+unicode(upS)
			except:pass
			decimalPlaces = 0

			for ii in range(max(1,nInputs)):
				INPUT_raw = False

				if nInputs >10:
						inputState = u"INPUT_{:02d}" .format(ii+addToInputName)
				elif nInputs == 1 and  u"INPUT" in dev.states:
						inputState = u"INPUT"
						upState	   = u"INPUT"
				elif nInputs == 0 and  u"INPUT" in dev.states:
						inputState = u"INPUT"
						if u"INPUT_raw" in dev.states: 
							INPUT_raw = True
				else:	inputState = u"INPUT_{}".format(ii+addToInputName)


				if self.decideMyLog(u"SensorData"): self.indiLOG.log(20,u"updateINPUT: {};  sensor: {};  upState: {}; inputState: {};  data: {}".format(dev.name, sensor, upState, inputState, data) )
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
								dp = unicode(v).split(u".")
								if len(dp)   == 0:	decimalPlaces = 0
								elif len(dp) == 2:	decimalPlaces = len(dp[1])
							except: pass

						if INPUT_raw: ss = v

						if inputState+u"MaxYesterday" in dev.states:
							self.fillMinMaxSensors(dev,inputState,v,decimalPlaces=decimalPlaces)

						if upState == inputState:
							if not self.setStateColor(dev,props,ss):
								fs = self.getNumber(ss)
								if ss == u"1" or ss == u"up" or (fs != 0. and fs != u"x"):
									on = True
									self.setIcon(dev,props,u"SensorOff-SensorOn",1)
								else:
									on = False
									self.setIcon(dev,props,u"SensorOff-SensorOn",0)

							if u"onOffState" in dev.states: 
								self.addToStatesUpdateDict(dev.id,u"onOffState",on, uiValue=ssUI)
								if dev.states[u"status"] != ssUI + unit:
									self.addToStatesUpdateDict(dev.id,u"status", ssUI)
							if u"sensorValue" in dev.states: 
								if self.decideMyLog(u"SensorData"): self.indiLOG.log(30,u"{};  sensor:{};  sensorValue".format(dev.name, sensor) )
								self.setStatusCol(dev, upState, ss, ssUI + unit, upState, "","", decimalPlaces = decimalPlaces)
							else:
								if dev.states[u"status"] != ssUI + unit:
									self.addToStatesUpdateDict(dev.id,u"status", ssUI+unit)

		except Exception, e:
			if unicode(e) != u"None":
				self.indiLOG.log(40,u"Line {} has error={}".format(sys.exc_traceback.tb_lineno, e))

####-------------------------------------------------------------------------####
	def setStateColor(self, dev, props, ss):
		try:
			if not( u"stateGreen" in props and u"stateGrey" in props and u"stateRed" in props): return False
			try:
				commands = {u"green":props[u"stateGreen"], u"grey":props[u"stateGrey"], u"red":props[u"stateRed"]} 
				ok = False
				for cmd in commands:
					if len(commands[cmd]) > 0: ok = True 
				if commands[u"green"] == commands[u"grey"] and commands[u"grey"] == commands[u"red"]: return False
			except: return False
			if not ok: return 

			x = self.getNumber(ss)
			#if self.decideMyLog(u"Special"):self.indiLOG.log(20,u"setStateColor for dev {}, x={};  eval syntax: {}".format(dev.name, x, commands) )
			for col in [u"green",u"grey",u"red"]:
				try: 
					if len(commands[col]) == 0: continue
					if eval(commands[col]) :
						if col == u"green": dev.updateStateImageOnServer(indigo.kStateImageSel.SensorOn)
						if col == u"grey": dev.updateStateImageOnServer(indigo.kStateImageSel.SensorOff)
						if col == u"red": dev.updateStateImageOnServer(indigo.kStateImageSel.SensorTripped)
						return True
				except: 
					if commands[col].find(u"x") ==-1:
						self.indiLOG.log(20,u"setStateColor for dev {}, x={};  color: {};  wrong eval syntax: {};  x=  x> ... statement part missing, eg x>25; not just >25".format(dev.name, x, col, commands[col]) )
					else:
						self.indiLOG.log(20,u"setStateColor for dev {}, x={};  color: {};  wrong eval syntax: {}".format(dev.name, x, col, commands[col]) )	



		except Exception, e:
			if unicode(e) != u"None":
				self.indiLOG.log(40,u"Line {} has error={}".format(sys.exc_traceback.tb_lineno, e))
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
			if self.decideMyLog(u"SensorData"): self.indiLOG.log(40,u"Line {} has error={}".format(sys.exc_traceback.tb_lineno, e))
			return



####-------------------------------------------------------------------------####
	def updateapds9960(self, dev, data):
		try:
			props = dev.pluginProps
			input = u"gesture"
			if input in data:
				if unicode(data[input]).find(u"bad") >-1:
					self.addToStatesUpdateDict(dev.id,u"status", u"no sensor data - disconnected?")
					self.setIcon(dev,props,u"SensorOff-SensorOn",0)
					return
				else:
					if data[input] !="NONE":
						if props[u"displayS"] == input:
							self.addToStatesUpdateDict(dev.id,u"status", data[input])
						self.addToStatesUpdateDict(dev.id,input,data[input])
						self.addToStatesUpdateDict(dev.id,input+u"Date",datetime.datetime.now().strftime(_defaultDateStampFormat))
						self.setIcon(dev,props,u"SensorOff-SensorOn",1)


			input = u"gestureData"
			if input in data:
					if data[input] !="":
						if props[u"displayS"] == input:
							self.addToStatesUpdateDict(dev.id,u"status", data[input])
						self.addToStatesUpdateDict(dev.id,input,data[input])
						self.setIcon(dev,props,u"SensorOff-SensorOn",1)

			input = u"distance"
			if input in data:
				if unicode(data[input]).find(u"bad") >-1:
					self.addToStatesUpdateDict(dev.id,u"status", u"no sensor data - disconnected?")
					self.setIcon(dev,props,u"SensorOff-SensorOn",0)
				else:
					if data[input] !="NONE":
						if props[u"displayS"] == input:
							self.addToStatesUpdateDict(dev.id,u"status", data[input])
						self.addToStatesUpdateDict(dev.id,input,data[input])
						self.addToStatesUpdateDict(dev.id,input+u"Date",datetime.datetime.now().strftime(_defaultDateStampFormat))
						self.setIcon(dev,props,u"SensorOff-SensorOn",1)

			input = u"proximity"
			if input in data:
				if unicode(data[input]).find(u"bad") >-1:
					self.addToStatesUpdateDict(dev.id,u"status", u"no sensor data - disconnected?")
					self.setIcon(dev,props,u"SensorOff-SensorOn",0)
				else:
						if props[u"displayS"] == input:
							self.addToStatesUpdateDict(dev.id,u"status", data[input])
						self.addToStatesUpdateDict(dev.id,input,data[input])
						self.addToStatesUpdateDict(dev.id,input+u"Date",datetime.datetime.now().strftime(_defaultDateStampFormat))
						self.setIcon(dev,props,u"SensorOff-SensorOn",1)

			self.updateRGB(dev, data, props[u"displayS"])

		except Exception, e:
			if self.decideMyLog(u"SensorData"): self.indiLOG.log(40,u"Line {} has error={}".format(sys.exc_traceback.tb_lineno, e))



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
				for input in [u"Current"+unicode(jj),u"ShuntVoltage"+unicode(jj),u"BusVoltage"+unicode(jj)]:
					if input in data:
						if unicode(data[input]).find(u"bad") >-1:
							self.setStatusCol( dev, input, 0,  u"no sensor data - disconnected?", u"Current"+unicode(jj), "","" )
							self.setIcon(dev,props,u"SensorOff-SensorOn",0)
							return
						if data[input] !="":
							ss, ssUI, unit = self.addmultOffsetUnit(data[input], dev.pluginProps)
							self.setStatusCol( dev, input, ss, ssUI+unit, whichKeysToDisplay, "","" )
				self.setIcon(dev,props,u"SensorOff-SensorOn",1)
		except Exception, e:
			if self.decideMyLog(u"SensorData"): self.indiLOG.log(40,u"Line {} has error={}".format(sys.exc_traceback.tb_lineno, e))

####-------------------------------------------------------------------------####
	def updateADC121(self,dev,data,whichKeysToDisplay):
		try:
			input = u"adc"
			props = dev.pluginProps
			xType = props[u"type"]
			pp = {u"offset": props[u"offset"],u"mult":props[u"mult"], u"unit": u"ppm",u"format":u"%2d"}

			if unicode(data[input]).find(u"bad") >-1:
					self.addToStatesUpdateDict(dev.id,u"status", u"no sensor data - disconnected?")
					self.setIcon(dev,props,u"SensorOff-SensorOn",0)
					return

			self.setIcon(dev,props,u"SensorOff-SensorOn",1)
			if input in data:
					if data[input] != "":
						ADC = data[input]
						MaxBits = 4095.	  # 12 bits
						Vcc		= 5000.	  # mVolt max

						if	 xType.find(u"MQ") > -1:
							try:	Vca		= float(dev.props[u"Vca"] )	  # mVolt  at clean Air / calibration
							except: Vca		= 3710.

						if	xType ==u"MQ7": #CO
							pp[u"unit"]		=u"ppm CO"
							pp[u"format"]	=u"%.2f"
							RR1 = 0.22
							RR2 = 0.02
							C1	= 10.
							C2	= 1000.
							k = math.log(RR1/RR2) / math.log(C1/C2)
							a = math.exp(  math.log(RR1) -	k * math.log(C1)  )
							RR = (MaxBits/ADC -1.) / (Vcc/Vca -1.)
							val = math.pow(RR/a,1./k)

						elif   xType ==u"MQ9": # CO
							pp[u"unit"]		=u"ppm CO"
							pp[u"format"]	=u"%.2f"
							RR1 = 1.5
							RR2 = 0.78
							C1	= 200
							C2	= 1000.
							k = math.log(RR1/RR2) / math.log(C1/C2)
							a = math.exp(  math.log(RR1) -	k * math.log(C1)  )
							RR = (MaxBits/ADC -1.) / (Vcc/Vca -1.)
							val = math.pow(RR/a,1./k)

						elif   xType ==u"MQ9-5LPG": # LPG
							pp[u"unit"]		=u"ppm LPG"
							pp[u"format"]	=u"%.2f"
							RR1 = 2.0
							RR2 = 0.31
							C1	= 200
							C2	= 10000.
							k = math.log(RR1/RR2) / math.log(C1/C2)
							a = math.exp(  math.log(RR1) -	k * math.log(C1)  )
							RR = (MaxBits/ADC -1.) / (Vcc/Vca -1.)
							val = math.pow(RR/a,1./k)

						elif   xType ==u"MQ9-5CH4": # CH4
							pp[u"unit"]		=u"ppm CH4"
							pp[u"format"]	=u"%.2f"
							RR1 = 3.0
							RR2 = 0.69
							C1	= 200
							C2	= 10000.
							k = math.log(RR1/RR2) / math.log(C1/C2)
							a = math.exp(  math.log(RR1) -	k * math.log(C1)  )
							RR = (MaxBits/ADC -1.) / (Vcc/Vca -1.)
							val = math.pow(RR/a,1./k)

						elif  xType ==u"MQ4": # LNG
							pp[u"unit"]		=u"ppm CNG"
							pp[u"format"]	=u"%.2f"
							RR1 = 2.5  
							RR2 = 0.42
							C1	= 20.
							C2	= 10000.
							k = math.log(RR1/RR2) / math.log(C1/C2)
							a = math.exp(  math.log(RR1) -	k * math.log(C1)  )
							RR = (MaxBits/ADC -1.) / (Vcc/Vca -1.)
							val = math.pow(RR/a,1./k)


						elif xType ==u"MQ3-Alcohol": #alcohol
							pp[u"unit"]		=u"Alcohol mg/l"
							pp[u"format"]	=u"%.2f"
							RR1 = 2.2  
							RR2 = 0.11
							C1	= 0.1
							C2	= 10.
							k = math.log(RR1/RR2) / math.log(C1/C2)
							a = math.exp(  math.log(RR1) -	k * math.log(C1)  )
							RR = (MaxBits/ADC -1.) / (Vcc/Vca -1.)
							val = math.pow(RR/a,1./k)

						elif xType ==u"MQ3-Benzene": #alcohol
							pp[u"unit"]		=u"Benzene mg/l"
							pp[u"format"]	=u"%.2f"
							RR1 = 3. 
							RR2 = 0.75
							C1	= 0.1
							C2	= 10.
							k = math.log(RR1/RR2) / math.log(C1/C2)
							a = math.exp(  math.log(RR1) -	k * math.log(C1)  )
							RR = (MaxBits/ADC -1.) / (Vcc/Vca -1.)
							val = math.pow(RR/a,1./k)

						elif xType ==u"MQ131": #Ozone
							pp[u"unit"]		=u"ppm Ozon"
							pp[u"format"]	=u"%.2f"
							RR1 = 3	 
							RR2 = 0.3
							C1	= 5.  
							C2	= 100.
							k = math.log(RR1/RR2) / math.log(C1/C2)
							a = math.exp(  math.log(RR1) -	k * math.log(C1)  )
							RR = (MaxBits/ADC -1.) / (Vcc/Vca -1.)
							val = math.pow(RR/a,1./k)

						elif xType ==u"A13XX": # hall effect sensor
							pp[u"unit"]		=u"º"
							pp[u"format"]	=u"%.2f"
							val		= (ADC / MaxBits) * 360.0

						elif xType ==u"TA12_200": # linear current sensor
							pp[u"unit"]		=u"mA"
							pp[u"format"]	=u"%.1f"
							val		= ADC 

						elif xType ==u"adc": # simple ADC
							pp[u"unit"]	=u"mV"
							pp[u"format"]=u"%0d"
							val			= ADC *(Vcc/MaxBits)


						ss, ssUI, unit = self.addmultOffsetUnit(val, pp)

						self.setStatusCol( dev, u"value", ss, ssUI+unit, whichKeysToDisplay, "","" )
						self.setStatusCol( dev, u"adc", ADC, unicode(ADC), whichKeysToDisplay,"","" )
		except Exception, e:
			if self.decideMyLog(u"SensorData"): self.indiLOG.log(40,u"Line {} has error={}".format(sys.exc_traceback.tb_lineno, e))


####-------------------------------------------------------------------------####
	def updateGYROS(self,dev,data,upState):
		try:
			props = dev.pluginProps
			if unicode(data).find(u"bad") >-1:
					self.addToStatesUpdateDict(dev.id,u"status", u"no sensor data - disconnected?")
					self.setIcon(dev, props, u"SensorOff-SensorOn" ,0)
					return
			self.setIcon(dev,props,u"SensorOff-SensorOn",1)
			theList = [u"EULER",u"QUAT", u"accelerationZ",u"GYR",u"ACC",u"LIN",u"GRAV",u"ROT"]
			XYZSumSQ = 0
			for input in theList:
				if input not in data: continue
				out = ""
				if input ==u"EULER":
					for dim in [u"heading",u"pitch",u"roll"]:
						if dim not in data[input]: continue
						if data[input][dim] =="":	continue
						ss, ssUI, unit = self.addmultOffsetUnit(data[input][dim], dev.pluginProps)
						out+=ss+u","
						self.addToStatesUpdateDict(dev.id,dim,ss)
				else:
					for dim in [u"x",u"y",u"z",u"w",u"q",u"r",u"s"]:
						if dim not in data[input]: continue
						if data[input][dim] =="":	continue
						ss, ssUI, unit = self.addmultOffsetUnit(data[input][dim], dev.pluginProps)
						out+=ss+u","
						self.addToStatesUpdateDict(dev.id,input+dim,ss)
						if u"XYZSumSQ" in dev.states and (input ==u"GYR" or input == u"accelerationZ"): 
							XYZSumSQ +=data[input][dim]*data[input][dim]
				if upState == input:
					self.addToStatesUpdateDict(dev.id,u"status", out.strip(u","))

				if u"XYZSumSQ" in dev.states and (input ==u"GYR" or input ==u"accelerationZ"):  
					xys= u"{:7.2f}".format(math.sqrt(XYZSumSQ)).strip()
					self.addToStatesUpdateDict(dev.id,u"XYZSumSQ",xys)
					if upState == u"XYZSumSQ":
						self.addToStatesUpdateDict(dev.id,u"status", xys)


			input = u"calibration"
			stateName  = u"calibration"
			if stateName in dev.states and input in data:
				if data[input] !="": 
					out=""
					for dim in data[input]:
						out += dim+u":"+unicode(data[input][dim])+u","
					out= out.strip(u",").strip(u" ")
					if	upState == input:
						self.addToStatesUpdateDict(dev.id,u"status",out)
					self.addToStatesUpdateDict(dev.id,stateName,out)

			input	   = u"temp"
			stateName  = u"Temperature"
			if stateName in dev.states and input in data:
				if data[input] != "": 
					x, UI, decimalPlaces = self.mintoday(data[input])
					if	upState == stateName :
						self.addToStatesUpdateDict(dev.id,u"status",UI)
					self.addToStatesUpdateDict(dev.id,stateName ,x, decimalPlaces= decimalPlaces)

		except Exception, e:
			if self.decideMyLog(u"SensorData"): self.indiLOG.log(40,u"Line {} has error={}".format(sys.exc_traceback.tb_lineno, e))


####-------------------------------------------------------------------------####
	def updateDistance(self, dev, data, whichKeysToDisplay):
			#{u"ultrasoundDistance":{u"477759402":{u"distance":1700.3591060638428}}
		try:

			input = u"distance"
			if input in data:
				if unicode(data[input]).find(u"bad") >-1:
					self.addToStatesUpdateDict(dev.id,u"status", u"no sensor data - disconnected?")
					self.setIcon(dev,props,u"SensorOff-SensorOn",0)
					return

				props = dev.pluginProps
				units = u"cm"
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
				ud   = u"[]"
				if units == u"cm":
					ud = u" [cm]"
					dist = distR
					dist0 = u"{:.1f}{}".format(distR, ud)
				elif units == u"m":
					ud = u" [m]"
					dist = distR*0.01
					dist0 = u"{:}.2f}{}".format(dist, ud)
				elif units == u"inches":
					ud = u' "'
					dist = distR*0.3937
					dist0 = u"{:.1f}{}".format(dist, ud)
				elif units == u"feet":
					ud = u" '"
					dist = distR*0.03280839895
					dist0 = u"{:.2f}{}".format(dist, ud)
				self.setStatusCol(dev, u"distance", dist, dist0, whichKeysToDisplay, "","", decimalPlaces = 2)

				self.addToStatesUpdateDict(dev.id,u"measuredNumber", raw)

				if u"speed" in data:
					try: 
						speed = float(data[u"speed"]) / max(self.speedUnits*100., 0.01)	 # comes in cm/sec
						units = self.speedUnits
						sp = unicode(speed) 
						ud = u"[]"
						if units == 0.01:
							ud = u" [cm/s]"
							sp = (u"%8.1f"%(speed)).replace(u" ","")
							decimalPlaces = 1
						elif units == 1.0:
							ud = u" [m/s]"
							sp = (u"%8.2f"%(speed)).replace(u" ","")
							decimalPlaces = 2
						elif units == 0.0254:
							ud = u' [i/s]'
							sp = (u"%7.1f"%(speed)).replace(u" ","")
							decimalPlaces = 1
						elif units == 0.348:
							ud = u" [f/s]"
							sp = (u"%8.2f"%(speed)).replace(u" ","")
							decimalPlaces = 2
						elif units == 0.9144:
							ud = u" [y/s]"
							sp = (u"%8.2f"%(speed)).replace(u" ","")
							decimalPlaces = 2
						elif units == 3.6:
							ud = u" [kmh]"
							sp = (u"%8.2f"%(speed)).replace(u" ","")
							decimalPlaces = 2
						elif units == 2.2369356:
							ud = u" [mph]"
							sp = (u"%8.2f"%(speed)).replace(u" ","")
							decimalPlaces = 2
						self.setStatusCol(dev, u"speed", speed, sp+ud, whichKeysToDisplay, "","", decimalPlaces = decimalPlaces)
					except:
						pass


				if u"actionShortDistanceLimit" in props:
					try: cutoff= float(props[u"actionShortDistanceLimit"])
					except: cutoff= 50
				else:		cutoff= 50
				if dist < cutoff:
						self.setIcon(dev,props,u"SensorOff-SensorOn",1)
				else:
						self.setIcon(dev,props,u"SensorOff-SensorOn",0)

		except Exception, e:
			if self.decideMyLog(u"SensorData"): self.indiLOG.log(40,u"Line {} has error={}".format(sys.exc_traceback.tb_lineno, e))





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
			if val == ""														: return u"x"
			try:
				ttt = unicode(val).upper()															# if unicode return ""	 (-->except:)
				if ttt== u"TRUE"  or ttt == u"ON"  or ttt == u"T" or ttt== u"UP"						: return 1.0	 # true/on	 --> 1
				if ttt== u"FALSE" or ttt == u"OFF" or ttt == u"F" or ttt== u"DOWN" or ttt==  u"EXPIRED"	: return 0.0		# false/off --> 0
			except:
				pass
			try:
				xx = ''.join([c for c in val if c in  u'-1234567890.'])								# remove non numbers
				lenXX= len(xx)
				if	lenXX > 0:																		# found numbers..if len( ''.join([c for cin xx if c in	'.']) )			  >1	: return "x"		# remove strings that have 2 or more dots " 5.5 6.6"
					if len(''.join([c for c in	xx if c in u'-']) )			 >1 : return u"x"		# remove strings that have 2 or more -	  u" 5-5 6-6"
					if len( ''.join([c for c  in xx if c in u'1234567890']) ) ==0: return u"x"		# remove strings that just no numbers, just . amd - eg "abc.xyz- hij"
					if lenXX ==1												: return float(xx)	# just one number
					if xx.find(u"-") > 0										: return u"x"		 # reject if "-" is not in first position
					valList =  list(val)															# make it a list
					count =	 0																		# count number of numbers
					for i in range(len(val)-1):														# reject -0 1 2.3 4  not consecutive numbers:..
						if (len(''.join([c for c in valList[i ] if c in	 u'-1234567890.'])) ==1 ):  # check if this character is a number, if yes:
							count +=1																#
							if count >= lenXX									: break		 # end of # of numbers, end of test: break, its a number
							if (len(''.join([c for c in valList[i+1] if c in u'-1234567890.'])) )== 0:  return u"x"  # next is not a number and not all numbers accounted for, so it is numberXnumber
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
				if props[u"onOff"] == u"ON-off":
					if ui ==1.:
						return "1", u"off", ""
					else:
						return "0", u"ON", ""

				if props[u"onOff"] == u"on-off":
					if ui ==1.:
						return "1", u"off", ""
					else:
						return "0", u"on", ""

				if props[u"onOff"] == u"off-ON":
					if ui ==1.:
						return "1", u"ON", ""
					else:
						return "0", u"off", ""

				if props[u"onOff"] == u"off-on":
					if ui ==1.:
						return "1", u"on", ""
					else:
						return "0", u"off", ""

				if props[u"onOff"] == u"open-closed":
					if ui ==1.:
						return "1", u"open", ""
					else:
						return "0", u"closed", ""

				if props[u"onOff"] == u"closed-open":
					if ui ==1.:
						return "1", u"closed", ""
					else:
						return "0", u"open",  ""

				if props[u"onOff"] == u"up-down":
					if ui ==1.:
						return "1", u"up", ""
					else:
						return "0", u"down", ""

				if props[u"onOff"] == u"closed-open":
					if ui ==1.:
						return "1", u"closed", ""
					else:
						return "0", u"open", ""

				if props[u"onOff"] == u"down-up":
					if ui ==1.:
						return "1", u"down", ""
					else:
						return "0", u"up", ""

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

			if u"resistorSensor" in props and props[u"resistorSensor"] != u"0":
				feedVolt = float(props[u"feedVolt"])
				feedResistor = float(props[u"feedResistor"])
				if props[u"resistorSensor"] == u"ground": # sensor is towards ground
					ui = feedResistor / max(((feedVolt / max(ui, 0.0001)) - 1.), 0.001)
				elif props[u"resistorSensor"] == u"V+": # sensor is towards V+
					ui = feedResistor *(feedVolt / max(ui, 0.0001) -1.)

			if u"maxMin" in props and props[u"maxMin"] == u"1":
				MAXRange = 100; MINRange = 10
				if u"MAXRange" in props and props[u"MAXRange"] != "" and u"MINRange" in props and props[u"MAXRange"] != "":
					try: 	MAXRange = eval(props[u"MAXRange"])
					except: pass
					try: 	MINRange = eval(props[u"MINRange"])
					except: pass
					ui = (ui - MINRange) / max(MAXRange - MINRange,0001)


			if u"valueOrdivValue" in props and props[u"valueOrdivValue"] == u"1/value":
				ui = 11. / max(ui, 0.000001)
				
			if u"logScale" in props and props[u"logScale"] == u"1":
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
			if unicode(e) != u"None":
				self.indiLOG.log(40,u"Line {} has error={}".format(sys.exc_traceback.tb_lineno, e))
			ui   = unicode(data)
			unit = ""	   
		return dd, ui, unit


####-------------------------------------------------------------------------####
	def updateLight(self, dev, data, upState,theType=""):
		try:
			if u"illuminance" in data or u"lux" in data or u"UV" in data or u"UVA" in data or u"UVB" in data or u"IR" in data or u"ambient" in data or u"white"  or u"visible" in data:
				props =	 dev.pluginProps
				if u"unit" in props: unit = props[u"unit"]
				else:				unit = ""
				if u"format" in props: formatN = props[u"format"]
				else:				   formatN = u"%7.2f"
				logScale="0"
				if u"logScale" in props: 
					logScale = props[u"logScale"]
					if logScale ==u"1":
						if u"format" in props: formatN = props[u"format"]
						else:				  formatN = u"%7.2f"


				if u"UVA" in data and "UVB" in data and not "UV" in data and "UV" in dev.states:
					data[u"UV"] = (float(data[u"UVA"]) + float(data[u"UVB"]) )/2.

				for  state, key in [[u"illuminance",u"lux"],[u"illuminance",u"illuminance"],[u"IR",u"IR"],[u"UVA",u"UVA"],[u"UVB",u"UVB"],[u"UV",u"UV"],[u"ambient",u"ambient"],[u"white",u"white"],[u"visible",u"visible"]]:
					if state in dev.states and key in data :
						if logScale !=u"1": self.setStatusCol(dev, state, round(float(data[key]),2),  formatN % (float(data[key]))+unit,                                         upState, "","",decimalPlaces=2 )
						else:				self.setStatusCol(dev, state, round(float(data[key]),2), (formatN % math.log10(max(0.1,float(data[key]))) ).replace(u" ", "")+unit, upState, "","",decimalPlaces=2 )
						#self.fillMinMaxSensors(dev,state,data[key],decimalPlaces=2)

				if u"red" in data:
					self.updateRGB( dev, data, upState, theType=theType)

				   
		except Exception, e:
			if unicode(e) != u"None":
				if self.decideMyLog(u"SensorData"): self.indiLOG.log(40,u"Line {} has error={}".format(sys.exc_traceback.tb_lineno, e))

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
					if u"stateGreen" not in props: dev.updateStateImageOnServer(indigo.kStateImageSel.LightSensorOn)
					if u"illuminance" in dev.states and u"illuminance" not in data:
						il = (-0.32466 * data[u'red']) + (1.57837 * data[u'green']) + (-0.73191 * data[u'blue'])  # fron adafruit
						ilUI = (u"%.1f" % il + u"[Lux]").replace(u" ", "")
						self.setStatusCol(dev, u"illuminance", round(il,1), ilUI, upState, "","",decimalPlaces=1 )
					if u"kelvin" in dev.states:
						k = int(self.calcKelvin(data))
						self.setStatusCol(dev, u"kelvin", k, unicode(k) + u"[ºK]", upState, "","",decimalPlaces=0 )
			if upState == u"red/green/blue":
						self.addToStatesUpdateDict(dev.id,u"status", u"r/g/b: "+unicode(data[u'red'])+u"/"+unicode(data[u'green'])+u"/"+unicode(data[u'blue'])+unit )



		except Exception, e:
			if unicode(e) != u"None":
				self.indiLOG.log(40,u"Line {} has error={}".format(sys.exc_traceback.tb_lineno, e))

####-------------------------------------------------------------------------####
	def updateRGB2(self, dev, color, data, upState,unit, dispType=""):

		try:
			if color not in dev.states: 
				return 0
			if dispType != "":
				try: 
					delta = abs(dev.states[color] - float(data[color]))
				except:
					delta = 10000
				if delta < 10 ** (-int(dispType)): return 0

				if color == u"lux"  or color == u"illuminance":	 dispType=2
				self.setStatusCol(dev, color, float(data[color]), color+u" "+unicode(data[color])+unit, upState, "","",decimalPlaces=dispType )
				return 1

			if dev.states[color] != unicode(data[color]):
				self.setStatusCol(dev, color, float(data[color]), u"color "+unicode(data[color])+unit, upState, "","",decimalPlaces=dispType )
				return 1
			return 0
		except Exception, e:
			if unicode(e) != u"None":
				self.indiLOG.log(40,u"Line {} has error={}".format(sys.exc_traceback.tb_lineno, e))
		return 0
####-------------------------------------------------------------------------####
	def calcKelvin(self, data):	 # from adafruit
		X = (-0.14282 * data[u'red']) + (1.54924 * data[u'green']) + (-0.95641 * data[u'blue'])
		Y = (-0.32466 * data[u'red']) + (1.57837 * data[u'green']) + (-0.73191 * data[u'blue'])
		Z = (-0.68202 * data[u'red']) + (0.77073 * data[u'green']) + (0.56332  * data[u'blue'])

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
			useFormat = u"{:."+unicode(self.tempDigits)+u"f}"
			suff = u"ºC"
			temp = float(temp)

			if temp == 999.9:
				return 999.9,u"badSensor", 1, useFormat

			if self.tempUnits == u"Fahrenheit":
				temp = temp * 9. / 5. + 32.
				suff = u"ºF"
			elif self.tempUnits == u"Kelvin":
				temp += 273.15
				suff = u"ºK"

			temp = round(temp,self.tempDigits)
			tempU = useFormat.format(temp) 
			return temp, tempU + suff,self.tempDigits, useFormat

		except:pass
		return -99, "",self.tempDigits, useFormat


####-------------------------------------------------------------------------####
	def convAlt(self, press, props, temp):
		try:
			offsetAlt = 0.
			if u"offsetAlt" in props:
				try: offsetAlt = float(props[u"offsetAlt"])
				except: pass
			pAtSeeLevel = 101325.0 # in pascal 

			alt = ((temp + 273.15)/0.0065)  *  ( 1. - pow( pAtSeeLevel / press, 0.1902843) ) + offsetAlt

			useFormat 	= u"{:.1f}"
			suff 		= u"[m]"
			cString 	= u"%.1f"
			aD 			= 1
			alt = float(alt)
			if self.distanceUnits == u"0.01":
				alt *= 100.
				suff = u" cm"
				cString = u"%.0f"
				aD = 0
			elif self.distanceUnits == u"0.0254":
				alt /= 0.0254
				suff = u' inch'
				cString = u"%.0f"
				aD = 0
			elif self.distanceUnits == u"0.348":
				alt /= 2.54
				suff = u" feet"
				cString = u"%.1f"
				aD = 1
			elif self.distanceUnits == u"0.9144":
				alt /= 0.9144
				suff = u" y"
				cString = u"%.2f"
				aD = 1
			else:
				pass
			altU = (cString % alt).strip()
			return round(alt,aD) , altU + suff,aD, useFormat
		except:pass
		return -99, "",aD, useFormat



####-------------------------------------------------------------------------####
	def convHum(self, hum):
		try:
			return int(float(hum)), u"{:0f}%".format(float(hum)) ,0
		except:
			return -99, "",0

####-------------------------------------------------------------------------####
	def convGas(self, GasIN, dev, props):
		 #data[u"GasResistance"], data[u"AirQuality"], data[u"GasBaseline"],data[u"SensorStatus"] 
		try:
			bad = False
			try:
					GasResistance	 = u"{:.0f}KOhm" .format(float(GasIN[u"GasResistance"])/1000.)
					GasResistanceInt = int(float(GasIN[u"GasResistance"]))
			except: 
					bad = True
			try:
					AirQuality	  = u"{:.0f}%".format(float(GasIN[u"AirQuality"]))
					AirQualityInt = int(float(GasIN[u"AirQuality"]) )
					AirQualityTextItems = props.get(u"AirQuality0-100ToTextMapping",u"90=Good/70=Average/55=little bad/40=bad/25=worse/0=very bad").split(u"/")
					ok = False
					if len(AirQualityTextItems) >2:
						try:
							aq = []
							for ii in AirQualityTextItems:
								xx = ii.split(u"=")
								aq.append([int(xx[0]),xx[1]])
							ok = True
						except:
							pass
					if not ok:
						aq = []
						AirQualityTextItems = u"95=Good/85=Average/75=Little Bad/65=Bad/50=Worse/0=Very Bad".split(u"/")
						for ii in AirQualityTextItems:
							xx = ii.split(u"=")
							aq.append([int(xx[0]),xx[1]])

					AirQualityText = aq[-1][1]
					for ii in aq:
						if AirQualityInt > ii[0]: 
							AirQualityText = ii[1]
							#self.indiLOG.log(30,u"AirQuality:{}; result:{}; aq {} --> {}".format(AirQuality, ii, AirQualityTextItems, aq))
							break
			except: 
					bad = True
					AirQualityText  = ""
			try:
					baseline	  = (u"%.0f" % (float(GasIN[u"GasBaseline"]))).strip()+u"%"
					baselineInt	  = int(float(GasIN[u"GasBaseline"]))
			except: 
					bad = True
			try:
					SensorStatus  = GasIN[u"SensorStatus"]
					if SensorStatus.find(u"measuring") ==-1:
						AirQuality = SensorStatus
			except: 
					bad = True
				
			if not bad:
				#self.indiLOG.log(30,u"{} returning: {} {} {} {} {} {} {} {}".format(dev.name, GasResistanceInt, GasResistance , AirQualityInt, AirQuality, baselineInt, baseline, SensorStatus, AirQualityText))
				return GasResistanceInt, GasResistance , AirQualityInt, AirQuality, baselineInt, baseline, SensorStatus, AirQualityText
			else:
				return "", "","", "","", "", "", ""
		except:
			return "", "","", "","", "", "", ""


####-------------------------------------------------------------------------####
	def getDeviceDisplayStateId(self, dev):
		props = dev.pluginProps
		if u"displayState" in props:
			return props[u"displayState"]
		elif u"displayStatus" in dev.states:
			return	u"displayStatus"
		else:
			return u"status"

###-------------------------------------------------------------------------####
	def checkForFastDown(self, mac, piMACSend, dev, props, rssi, fromPiU, newStates):
		try:
			updateSignal = False
			updateFINGnow = False
			piXX = u"Pi_{:02d}".format(int(fromPiU))

			if newStates[u"status"] == u"up" and rssi == -999. and time.time() > self.currentlyBooting:	## check for fast down signal ==-999
				if self.decideMyLog(u"CAR") and self.decideMyLog(u"BeaconData"): self.indiLOG.log(10,u"testing fastdown from pi:{:2s}  for:{};  piStillUp? {}, new sig=-999; oldsig={:4d}  status={} ".format(fromPiU, mac, piStillUp, dev.states[piXX+u"_Signal"], dev.states[u"status"]))

				newStates= self.addToStatesUpdateDict(dev.id,piXX+u"_Signal", -999, newStates=newStates)
				self.beacons[mac][u"receivedSignals"][int(fromPiU)][u"lastSignal"] = time.time() - 999

				noneUp = []
				for pixx in range(_GlobalConst_numberOfiBeaconRPI):
					if ( time.time() - self.beacons[mac][u"receivedSignals"][pixx][u"lastSignal"] < 60 and  
						 dev.states[u"Pi_{:02d}_Signal".format(pixx)] > -999 ):
						noneUp.append(pixx) #.append([pixx,time.time() - self.beacons[mac][u"receivedSignals"][pixx][u"lastSignal"] ])

				if self.selectBeaconsLogTimer !={}: 
					for sMAC in self.selectBeaconsLogTimer:
						if mac.find(sMAC[:self.selectBeaconsLogTimer[sMAC]]) ==0:
							self.indiLOG.log(20,u"sel.beacon logging: newMSG-999-1  - :{} -999 received, rpi still w signal:{}".format(mac, noneUp))

				if noneUp == []:
					updateSignal = True
					if mac != piMACSend: dev.updateStateImageOnServer(indigo.kStateImageSel.SensorOff)	# only for regluar ibeacons..
					newStates = self.addToStatesUpdateDict(dev.id,u"status", u"down",newStates=newStates)
					self.beacons[mac][u"status"] = u"down"
					self.beacons[mac][u"updateFING"] = 1
					updateFINGnow = True
					self.beacons[mac][u"lastUp"] = -time.time()
					newStates = self.addToStatesUpdateDict(dev.id,u"closestRPI", -1,newStates=newStates)
					if self.setClostestRPItextToBlank: newStates = newStates = self.addToStatesUpdateDict(dev.id,u"closestRPIText", "",newStates=newStates)
					if u"showBeaconOnMap" in props and props[u"showBeaconOnMap"] in _GlobalConst_beaconPlotSymbols: self.beaconPositionsUpdated =4
					if self.selectBeaconsLogTimer !={}: 
						for sMAC in self.selectBeaconsLogTimer:
							if mac.find(sMAC[:self.selectBeaconsLogTimer[sMAC]]) ==0:
								self.indiLOG.log(20,u"sel.beacon logging: newMSG-999-2  - :{};  set status to down\nnewStates:{}".format(mac, unicode(newStates).replace(u"\n","") ))
			return updateSignal, updateFINGnow, newStates 

		except Exception, e:

			if unicode(e).find(u"timeout waiting") > -1:
				self.indiLOG.log(40,u"Line {} has error={}".format(sys.exc_traceback.tb_lineno, e))
				self.indiLOG.log(40,u"communication to indigo is interrupted")
				return 
			if e != None	and unicode(e).find(u"not found in database") ==-1:
				self.indiLOG.log(40,u"Line {} has error={}".format(sys.exc_traceback.tb_lineno, e))
		return updateSignal, updateFINGnow, newStates 


###-------------------------------------------------------------------------####
	def handleBeaconRealSignal(self, mac, piMACSend, dev, props, beaconUpdatedIds, rssi, txPower, rssiOffset, fromPiU, newStates, updateSignal, updateFINGnow, dateString ):

		try:
			fromPiI = int(fromPiU)
			logTRUEfromChangeOFRPI = False
			updateSignal = False
			updateFINGnow = False
			closestRPI = -1
			oldRPI = -1
			piXX = u"Pi_{:02d}".format(fromPiI)

			if dev.deviceTypeId == u"beacon": 
				try:	oldRPI = int(dev.states[u"closestRPI"])
				except: oldRPI =-1

			try:     distCalc = float(dev.states[piXX+u"_Distance"])
			except:  distCalc = 99999

			if rssi != -999.:
				if self.selectBeaconsLogTimer !={}: 
					for sMAC in self.selectBeaconsLogTimer:
						if mac.find(sMAC[:self.selectBeaconsLogTimer[sMAC]]) ==0:
							self.indiLOG.log(20,u"sel.beacon logging: newMSG    up  - :{}; set status up, rssi:{}".format(mac, rssi))

				if ( self.beacons[mac][u"lastUp"] > -1) :
					self.beacons[mac][u"receivedSignals"][fromPiI][u"rssi"]  = rssi
					self.beacons[mac][u"receivedSignals"][fromPiI][u"lastSignal"]  = time.time()
					self.beacons[mac][u"lastUp"] = time.time()
					distCalc = 9999
					closestRPI = -1
					try:
						minTxPower = float(self.beacons[mac][u"beaconTxPower"])
					except:
						minTxPower = 99999.
					if dev.deviceTypeId in [u"beacon",u"rPI"]: 
						txx = float(txPower)
						if minTxPower <	 991.: 
							txx = minTxPower
							distCalc = self.calcDist(  txx, (rssi+rssiOffset) )/ self.distanceUnits
							self.beacons[mac][u"receivedSignals"][fromPiI][u"distance"]  = distCalc
						closestRPI = self.findClosestRPI(mac, dev)

					if	( time.time()- self.beacons[mac][u"updateWindow"] > self.beacons[mac][u"updateSignalValuesSeconds"] or
						  time.time()- self.beacons[mac][u"receivedSignals"][fromPiI][u"lastSignal"] > 100. ):  # ==0 or xx seconds updates for 75 seconds, this RPI msg older than 100 secs then xx secs no update for next time
						self.beacons[mac][u"updateWindow"] = time.time()

					if (dev.deviceTypeId == u"beacon" and closestRPI != oldRPI) and self.trackSignalChangeOfRPI:
						logTRUEfromChangeOFRPI = True

					try: newStates[piXX+u"_Signal"] 
					except: self.indiLOG.log(40,u"{} no state {}".format(dev.name ,piXX+u"_Signal") )

					if (
						( self.beacons[mac][u"status"] != u"up" )																or	# was down now up
						( time.time() - self.beacons[mac][u"updateWindow"] < 70 )												or	# update for 70 seconds then break 
						( newStates[piXX+u"_Signal"] == -999 )																	or	# was down now up
						( abs( newStates[piXX+u"_Signal"] - self.beacons[mac][u"receivedSignals"][fromPiI][u"rssi"] ) >20 )		or	# signal change large
						( dev.deviceTypeId == u"beacon" and closestRPI != newStates[u"closestRPI"] )							# clostest RPi has changed
						):				   
							updateSignal = True
							newStates = self.addToStatesUpdateDict(dev.id,piXX+u"_Signal", int(rssi-rssiOffset),newStates=newStates)
							newStates = self.addToStatesUpdateDict(dev.id,u"TxPowerReceived",float(txPower),newStates=newStates)

							if dev.deviceTypeId == u"beacon"  and distCalc < 100/self.distanceUnits and not (u"IgnoreBeaconForClosestToRPI" in props and props[u"IgnoreBeaconForClosestToRPI"] !="0"):
								beaconUpdatedIds.append([fromPiI,dev.id, distCalc])
								self.beacons[mac][u"receivedSignals"][fromPiI][u"distance"] = distCalc
							newStates = self.addToStatesUpdateDict(dev.id,piXX+u"_Distance", distCalc,newStates=newStates ,decimalPlaces=1  )
							newStates = self.addToStatesUpdateDict(dev.id,piXX+u"_Time", dateString,newStates=newStates)
					if newStates[u"status"] != u"up":  
						if mac != piMACSend: dev.updateStateImageOnServer(indigo.kStateImageSel.SensorOn)
						newStates=self.addToStatesUpdateDict(dev.id,u"status", u"up",newStates=newStates)
						self.beacons[mac][u"updateFING"] = 1
						updateFINGnow = True
						self.beacons[mac][u"status"] = u"up"
						if u"showBeaconOnMap" in props and props[u"showBeaconOnMap"] in _GlobalConst_beaconPlotSymbols: self.beaconPositionsUpdated =5

					if dev.deviceTypeId == u"beacon" or dev.deviceTypeId == u"rPI": 
						if closestRPI != dev.states[u"closestRPI"]:
							if unicode(dev.states[u"closestRPI"]) != u"-1":
								self.addToStatesUpdateDict(dev.id,u"closestRPILast", dev.states[u"closestRPI"])
								self.addToStatesUpdateDict(dev.id,u"closestRPITextLast", dev.states[u"closestRPIText"])
						newStates = self.addToStatesUpdateDict(dev.id,u"closestRPI",     closestRPI,newStates=newStates)
						newStates = self.addToStatesUpdateDict(dev.id,u"closestRPIText", self.getRPIdevName((closestRPI)),newStates=newStates)

				self.beacons[mac][u"indigoId"] = dev.id
				self.beacons[mac][u"receivedSignals"][fromPiI][u"rssi"]  = rssi
				self.beacons[mac][u"receivedSignals"][fromPiI][u"lastSignal"]  = time.time()
				self.beacons[mac][u"lastUp"] = time.time()

				if self.beacons[mac][u"receivedSignals"][fromPiI][u"rssi"] != rssi+rssiOffset:
					self.beacons[mac][u"receivedSignals"][fromPiI] = {u"rssi":rssi+rssiOffset, u"lastSignal":time.time(), u"distance":distCalc}
			return updateSignal, updateFINGnow, newStates, logTRUEfromChangeOFRPI, oldRPI, closestRPI, beaconUpdatedIds


		except Exception, e:

			if unicode(e).find(u"timeout waiting") > -1:
				self.indiLOG.log(40,u"Line {} has error={}".format(sys.exc_traceback.tb_lineno, e))
				self.indiLOG.log(40,u"communication to indigo is interrupted")
				return 
			if e != None	and unicode(e).find(u"not found in database") ==-1:
				self.indiLOG.log(40,u"Line {} has error={}".format(sys.exc_traceback.tb_lineno, e))
		return updateSignal, updateFINGnow, newStates, logTRUEfromChangeOFRPI, oldRPI, closestRPI, beaconUpdatedIds

###-------------------------------------------------------------------------####

	def handleRPIMessagePart(self, piMACSend, newRPI, fromPiU, piNReceived, ipAddress, dateString, beaconUpdatedIds):
		try:


			if self.RPI[fromPiU][u"piMAC"] != piMACSend:
				if self.RPI[fromPiU][u"piMAC"] == "" or self.RPI[fromPiU][u"piMAC"].find(u"00:00:") ==0:
					newRPI = self.RPI[fromPiU][u"piMAC"] 
					self.indiLOG.log(20,u"pi#: {};  MAC number change from: {}; to: {}".format(fromPiU, newRPI, piMACSend) )
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
							self.indiLOG.log(20,u"trying: to replace , create new RPI for   "+piMACSend+u"  "+unicode(props))
							if piMACSend not in self.beacons:
								replaceRPIBeacon =""
								for btest in self.beacons:
									if self.beacons[btest][u"indigoId"] == existingIndigoId:
										replaceRPIBeacon = btest
										break
								if replaceRPIBeacon !="":
									self.beacons[piMACSend] = copy.deepcopy(self.beacons[replaceRPIBeacon])
									del self.beacons[replaceRPIBeacon]
									self.indiLOG.log(20,u" replacing old beacon")
								else:
									self.beacons[piMACSend]					  = copy.deepcopy(_GlobalConst_emptyBeacon) 
									self.beacons[piMACSend][u"ignore"]		  = 0
									self.beacons[piMACSend][u"indigoId"]	  = existingIndigoId
									self.beacons[piMACSend][u"note"]		  = u"Pi-"+unicode(fromPiU)
									self.beacons[piMACSend][u"typeOfBeacon"]  = u"rPI"
									self.beacons[piMACSend][u"status"]		  = u"up" 
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
								self.fixConfig(checkOnly = [u"all",u"rpi"],fromPGM=u"updateBeaconStates pichanged") # updateBeaconStates # ok only if new MAC for rpi ...
								self.addToStatesUpdateDict(unicode(existingPiDev.id),u"vendorName", self.getVendortName(piMACSend))
							else:
								if self.beacons[piMACSend][u"typeOfBeacon"].lower() !="rpi": 
									pass # let the normal process replace the beacon with the RPI
								else:
									self.RPI[fromPiU][u"piMAC"] = piMACSend
									self.indiLOG.log(20,u"might have failed to replace RPI pi#: {}; piMACSend: {}; , you have to do it manually; beacon with type = rpi already exist ".format(fromPiU, piMACSend) )

					except Exception, e:
							self.indiLOG.log(40,u"Line {} has error={}".format(sys.exc_traceback.tb_lineno, e))
							self.indiLOG.log(40,u"failed to replace RPI pi#= {};  piMACSend: {};  you have to do it manually".format(fromPiU, piMACSend) )


			if self.RPI[fromPiU][u"piNumberReceived"] != piNReceived:
				self.RPI[fromPiU][u"piNumberReceived"] = piNReceived
				updatepIP = True
			else:
				updatepIP = False


			keepThisMessage = True
			foundPI = False
			if piMACSend in self.beacons:
				indigoId = self.beacons[piMACSend][u"indigoId"]
				try:
					dev = indigo.devices[indigoId]
				except Exception, e:

					if unicode(e).find(u"timeout waiting") > -1:
						self.indiLOG.log(40,u"Line {} has error={}".format(sys.exc_traceback.tb_lineno, e))
						self.indiLOG.log(40,u"communication to indigo is interrupted")
						return beaconUpdatedIds
					if unicode(e).find(u"not found in database") ==-1:
						self.indiLOG.log(40,u"Line {} has error={}".format(sys.exc_traceback.tb_lineno, e))
						self.indiLOG.log(40,u"updateBeaconStates beacons dict: "+ unicode(self.beacons[piMACSend]))
					return False, beaconUpdatedIds, updatepIP

				try:
					if dev.deviceTypeId == u"rPI":
						foundPI = True
						if dev.states[u"note"] != u"Pi-" + piNReceived:
							dev.updateStateOnServer(u"note", u"Pi-" + piNReceived)
							#self.addToStatesUpdateDict(dev.id,u"note", u"Pi-" + piNReceived)
						self.beacons[piMACSend][u"lastUp"] = time.time()
						self.RPI[piNReceived][u"piDevId"] = dev.id
						if dev.description != u"Pi-"+ piNReceived+u"-"+ipAddress:
							dev.description = u"Pi-"+ piNReceived+u"-"+ipAddress
							dev.replaceOnServer()

					else:
						indigo.device.delete(dev)
						self.indiLOG.log(30,u"=== deleting beacon: {} replacing simple beacon with rPi model(1)".format(dev.name) )
						del self.beacons[piMACSend]

				except Exception, e:
					if unicode(e) != u"None":
						self.indiLOG.log(40,u"Line {} has error={}".format(sys.exc_traceback.tb_lineno, e))
						self.indiLOG.log(40,u"beacons[piMACSend] pi#: {}; Pisend: {}; indigoID: {}; beaconsDict: {}".format(fromPiU,  piMACSend, indigoId, self.beacons[piMACSend] ) )
						if unicode(e).find(u"timeout waiting") > -1:
							self.indiLOG.log(40,u"Line {} has error={}".format(sys.exc_traceback.tb_lineno, e))
							self.indiLOG.log(40,u"communication to indigo is interrupted")
							return beaconUpdatedIds
						self.indiLOG.log(40,u"smallErr", text =u" error ok if new / replaced RPI")

					del self.beacons[piMACSend]

			if not foundPI:
				if piMACSend in self.beacons: del self.beacons[piMACSend]
				delDEV = []
				dev = ""
				for dev in indigo.devices.iter(u"props.isRPIDevice"):
					props = dev.pluginProps

					try:
						if props[u"address"] == newRPI and newRPI != "":
							newRPI = u"found"
							break

						elif props[u"address"] == piMACSend:
							delDEV.append(dev)
							self.RPI[piNReceived][u"piDevId"] = 0
					except:

						self.indiLOG.log(20,u"device has no address, setting piDevId=0: {}  {} {}".format(dev.name, dev.id, unicode(props)) )
						delDEV.append(dev)
						self.RPI[fromPiU][u"piDevId"] = 0

				for devx in delDEV:
					self.indiLOG.log(20,u"===  deleting beacon: {}  replacing simple beacon with rPi model(2)".format(devx.name) )
					try:
						indigo.device.delete(devx)
					except:
						pass

				if newRPI != u"found":
					self.indiLOG.log(20,u"creating new pi (3.)  -- fromPI: {};   piNR: {};   piMACSend: {};   ipAddress: {} " .format(fromPiU, piNReceived, piMACSend, ipAddress) )

					newProps = copy.copy(_GlobalConst_emptyrPiProps)
					newProps[u"rpiDataAcquistionMethod"] = self.rpiDataAcquistionMethod

					indigo.device.create(
						protocol		= indigo.kProtocol.Plugin,
						address			= piMACSend,
						name			= u"Pi_" + piMACSend,
						description		= u"Pi-" + piNReceived+u"-"+ipAddress,
						pluginId		= self.pluginId,
						deviceTypeId	= u"rPI",
						folder			= self.piFolderId,
						props			= newProps
						)

					try:
						dev = indigo.devices[u"Pi_" + piMACSend]
					except Exception, e:
						if unicode(e).find(u"timeout waiting") > -1:
							self.indiLOG.log(40,u"Line {} has error={}".format(sys.exc_traceback.tb_lineno, e))
							self.indiLOG.log(40,u"communication to indigo is interrupted")
							return  False, beaconUpdatedIds, updatepIP
						if unicode(e).find(u"not found in database") ==-1:
							self.indiLOG.log(40,u"Line {} has error={}".format(sys.exc_traceback.tb_lineno, e))
							return  False, beaconUpdatedIds 
						self.indiLOG.log(40,u"Line {} has error={}".format(sys.exc_traceback.tb_lineno, e))
						return  False, beaconUpdatedIds, updatepIP

				dev.updateStateImageOnServer(indigo.kStateImageSel.SensorOn)
				self.addToStatesUpdateDict(dev.id,u"vendorName", self.getVendortName(piMACSend))
				self.addToStatesUpdateDict(dev.id,u"status", u"up")
				self.addToStatesUpdateDict(dev.id,u"note", u"Pi-" + piNReceived)
				self.addToStatesUpdateDict(dev.id,u"TxPowerSet", float(_GlobalConst_emptyrPiProps[u"beaconTxPower"]))
				self.addToStatesUpdateDict(dev.id,u"created", dateString)
				self.addToStatesUpdateDict(dev.id,u"Pi_{:02d}_Signal".format(int(fromPiU)), 0)
				self.addToStatesUpdateDict(dev.id,u"TxPowerReceived",0)
				self.executeUpdateStatesDict(onlyDevID=dev.id, calledFrom=u"updateBeaconStates new rpi")

				self.updatePiBeaconNote[piMACSend] 				= 1
				self.beacons[piMACSend]							= copy.deepcopy(_GlobalConst_emptyBeacon)
				self.beacons[piMACSend][u"expirationTime"]		= self.secToDown
				self.beacons[piMACSend][u"indigoId"]			= dev.id
				self.beacons[piMACSend][u"updateFING"]			= 0
				self.beacons[piMACSend][u"status"]				= u"up"
				self.beacons[piMACSend][u"lastUp"]				= time.time()
				self.beacons[piMACSend][u"note"]				= u"Pi-" + piNReceived
				self.beacons[piMACSend][u"typeOfBeacon"]		= u"rPI"
				self.beacons[piMACSend][u"created"]				= dateString
				self.RPI[fromPiU][u"piDevId"]					= dev.id  # used to quickly look up the rPI devices in indigo
				self.RPI[fromPiU][u"piNumberReceived"]			= piNReceived
				self.RPI[fromPiU][u"piMAC"]						= piMACSend
				self.setONErPiV(frompiU,u"piUpToDate", [u"updateParamsFTP",u"rebootSSH"])
				self.fixConfig(checkOnly = [u"all",u"rpi",u"force"],fromPGM=u"updateBeaconStates1") # updateBeaconStates # ok only if new MAC for rpi ...

		except Exception, e:
			if unicode(e).find(u"timeout waiting") > -1:
				self.indiLOG.log(40,u"Line {} has error={}".format(sys.exc_traceback.tb_lineno, e))
				self.indiLOG.log(40,u"communication to indigo is interrupted")
			if e != None	and unicode(e).find(u"not found in database") ==-1:
				self.indiLOG.log(40,u"Line {} has error={}".format(sys.exc_traceback.tb_lineno, e))
			keepThisMessage = False

		return  keepThisMessage, beaconUpdatedIds, updatepIP 


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
			indigoId = self.beacons[mac][u"indigoId"]
			if indigoId != 0:
				try:
					dev = indigo.devices[indigoId]
					name = dev.name
					props = dev.pluginProps
					newStates = copy.copy(dev.states)
				except Exception, e:
					if unicode(e).find(u"timeout waiting") > -1:
						self.indiLOG.log(40,u"Line {} has error={}".format(sys.exc_traceback.tb_lineno, e))
						self.indiLOG.log(40,u"communication to indigo is interrupted")
						return setALLrPiVUpdate, dev, props, newStates, False
					if unicode(e).find(u"not found in database") ==-1:
						self.indiLOG.log(40,u"Line {} has error={}".format(sys.exc_traceback.tb_lineno, e))
						return setALLrPiVUpdate, dev, props, newStates, False
					self.indiLOG.log(40,u"Line {} has error={}".format(sys.exc_traceback.tb_lineno, e)   + " indigoId:{}".format(self.beacons[mac][u"indigoId"]))
					self.beacons[mac][u"indigoId"] = 0

			else: # no indigoId found, double check 
				for dev in indigo.devices.iter(u"props.isBeaconDevice,props.isRPIDevice"):
						props = dev.pluginProps
						if u"address" in props:
							if props[u"address"] == mac:
								if dev.deviceTypeId != u"beacon": 
									self.indiLOG.log(10,u" rejecting new beacon, same mac number already exist for different device type: {}  dev: {}".format(dev.deviceTypeId, dev.name))
									continue
								else:
									self.beacons[mac][u"indigoId"] = dev.id
									name = dev.name
									newStates = copy.copy(dev.states)
									break


			if rssi < self.acceptNewiBeacons and name == "" and self.beacons[mac][u"ignore"] >= 0: 
				if self.selectBeaconsLogTimer !={}: 
					for sMAC in self.selectBeaconsLogTimer:
						if mac.find(sMAC[:self.selectBeaconsLogTimer[sMAC]]) ==0:
							self.indiLOG.log(20,u"sel.beacon logging: newMSG rej rssi :{}; name= empty".format(mac)  )
				return setALLrPiVUpdate, dev, props, newStates, False


			if name == "":
				self.indiLOG.log(20,u"creating new beacon,  received from pi #  {}/{}:   beacon-{}  typeOfBeacon: {}".format(fromPiU, piMACSend, mac, typeOfBeacon) )

				name = u"beacon_" + mac
				desc 		 = typeOfBeacon
				SupportsBatteryLevel = False
				batteryLevelUUID	 = u"off"
				beaconBeepUUID 		 = u"off"
				useOnlyPrioTagMessageTypes = u"0"
				if typeOfBeacon in self.knownBeaconTags:
					if  type(self.knownBeaconTags[typeOfBeacon][u"battCmd"]) == type({}) and u"uuid" in self.knownBeaconTags[typeOfBeacon][u"battCmd"]:
						SupportsBatteryLevel = True
						batteryLevelUUID	 = u"gatttool"
					if  type(self.knownBeaconTags[typeOfBeacon][u"battCmd"]) == type("") and u"msg" in self.knownBeaconTags[typeOfBeacon][u"battCmd"]:
						SupportsBatteryLevel = True
						batteryLevelUUID	 = u"msg"
					useOnlyPrioTagMessageTypes = self.knownBeaconTags[typeOfBeacon][u"useOnlyThisTagToAcceptBeaconMsgDefault"]

				newprops = copy.copy(_GlobalConst_emptyBeaconProps)
				newprops[u"typeOfBeacon"] 				= typeOfBeacon
				newprops[u"version"] 					= typeOfBeacon # this is for  the firmware field
				newprops[u"SupportsBatteryLevel"] 		= SupportsBatteryLevel
				newprops[u"batteryLevelUUID"] 			= batteryLevelUUID
				newprops[u"beaconBeepUUID"]				= beaconBeepUUID
				newprops[u"useOnlyPrioTagMessageTypes"]	= useOnlyPrioTagMessageTypes
				indigo.device.create(
					protocol		= indigo.kProtocol.Plugin,
					address			= mac,
					name			= name,
					description		= desc,
					pluginId		= self.pluginId,
					deviceTypeId	= u"beacon",
					folder			= self.piFolderId,
					props			= newprops
					)
				try:
					dev = indigo.devices[u"beacon_" + mac]
					props = dev.pluginProps
				except Exception, e:

					if unicode(e).find(u"timeout waiting") > -1:
						self.indiLOG.log(40,u"Line {} has error={}".format(sys.exc_traceback.tb_lineno, e))
						self.indiLOG.log(40,u"communication to indigo is interrupted")
						return setALLrPiVUpdate, dev, props, newStates, False
				dev.updateStateImageOnServer(indigo.kStateImageSel.SensorOn)
				self.addToStatesUpdateDict(dev.id,u"vendorName", self.getVendortName(mac))
				self.addToStatesUpdateDict(dev.id,u"status", u"up")
				self.addToStatesUpdateDict(dev.id,u"typeOfBeacon", typeOfBeacon)
				self.addToStatesUpdateDict(dev.id,u"note", u"beacon-other")
				self.addToStatesUpdateDict(dev.id,u"created", dateString)
				self.addToStatesUpdateDict(dev.id,u"TxPowerSet", float(_GlobalConst_emptyBeaconProps[u"beaconTxPower"]))

				for iiU in _rpiBeaconList:
					if iiU == fromPiU: continue
					try: self.addToStatesUpdateDict(dev.id,u"Pi_{:02d}_Signal".format(int(iiU)),-999)
					except: pass
				self.addToStatesUpdateDict(dev.id,u"Pi_{:02d}_Signal".format(int(fromPiU)), int(rssi+rssiOffset))
				self.addToStatesUpdateDict(dev.id,u"TxPowerReceived",float(txPower))
				self.addToStatesUpdateDict(dev.id,u"closestRPI",fromPiI)
				self.addToStatesUpdateDict(dev.id,u"closestRPIText",self.getRPIdevName(fromPiU) )
				self.addToStatesUpdateDict(dev.id,u"closestRPILast",fromPiI)
				self.addToStatesUpdateDict(dev.id,u"closestRPITextLast",self.getRPIdevName(fromPiU) )

				self.beacons[mac][u"typeOfBeacon"] = u"other"
				self.beacons[mac][u"created"] = dateString
				self.beacons[mac][u"expirationTime"] = self.secToDown
				self.beacons[mac][u"lastUp"] = time.time()
				self.beacons[mac][u"enabled"] = True

				self.executeUpdateStatesDict(onlyDevID=dev.id, calledFrom=u"updateBeaconStates new beacon")
				self.fixConfig(checkOnly = [u"beacon"],fromPGM=u"updateBeaconStates new beacon") # updateBeaconStates
				if self.newBeaconsLogTimer >0:
					if time.time()> self.newBeaconsLogTimer:
						self.newBeaconsLogTimer =0
					else:
						self.indiLOG.log(20,u"new beacon logging: created:"+unicode(dateString.split(u" ")[1])+u" "+mac+u" "+ name.ljust(20)+u" "+ typeOfBeacon.ljust(25)+ u"  pi#="+fromPiU+ u" rssi="+unicode(rssi)+ u"  txPower="+unicode(txPower))

				setALLrPiVUpdate = u"updateParamsFTP"

				dev = indigo.devices[name]
				newStates = copy.copy(dev.states)
		except Exception, e:
			if unicode(e).find(u"timeout waiting") > -1:
				self.indiLOG.log(40,u"Line {} has error={}".format(sys.exc_traceback.tb_lineno, e))
				self.indiLOG.log(40,u"communication to indigo is interrupted")
			if e != None	and unicode(e).find(u"not found in database") ==-1:
				self.indiLOG.log(40,u"Line {} has error={}".format(sys.exc_traceback.tb_lineno, e))
			keepThisMessage = False

		return setALLrPiVUpdate, dev, props, newStates, keepThisMessage


####-------------------------------------------------------------------------####
	def checkBeaconDictIfok(self, mac, dateString, rssi, fromPiU, msg, isTagged):
		try:
			if (mac in self.beacons and self.beacons[mac][u"ignore"] >0 ):
				if self.decideMyLog(u"BeaconData"): self.indiLOG.log(10,u" rejected beacon because its in reject family: pi: {}; beacon: {}".format(fromPiU, msg) )
				return False  # ignore certain type of beacons, but only for new ones, old ones must be excluded individually

			if mac not in self.beacons:
				if  rssi >  self.acceptNewiBeacons or isTagged:
					self.beacons[mac] = copy.deepcopy(_GlobalConst_emptyBeacon)
					self.beacons[mac][u"created"] = dateString
					self.beacons[mac][u"lastUp"]  = time.time()
				else:
					self.indiLOG.log(20,u" rejected beacon because do not accept new beacons is on or rssi:{}<{};  types{};{}; pi:{}; beaconMSG:{} ".format(rssi, self.acceptNewiBeacons, type(rssi), type(self.acceptNewiBeacons), fromPiU, msg))
				return False 
			else:
				if self.beacons[mac][u"ignore"] == 0 and self.beacons[mac][u"indigoId"] == 0 and isTagged:
					self.beacons[mac] = copy.deepcopy(_GlobalConst_emptyBeacon)
					self.beacons[mac][u"created"] = dateString
					self.beacons[mac][u"lastUp"]  = time.time()
					self.beacons[mac][u"ignore"] = -1
					self.indiLOG.log(20,u"new beacon from type ID (2)  rssi:{}<{};   pi:{}; typeID:{}; beaconMSG:{} ".format(rssi, self.acceptNewiBeacons, fromPiU, self.acceptNewTagiBeacons, msg))
				if not self.beacons[mac][u"enabled"]: 					return False 

			if self.beacons[mac][u"ignore"] > 0: 						return False  
			return True
		except Exception, e:
			if unicode(e).find(u"timeout waiting") > -1:
				self.indiLOG.log(40,u"Line {} has error={}".format(sys.exc_traceback.tb_lineno, e))
				self.indiLOG.log(40,u"communication to indigo is interrupted")
			if e != None	and unicode(e).find(u"not found in database") ==-1:
				self.indiLOG.log(40,u"Line {} has error={}".format(sys.exc_traceback.tb_lineno, e))
		return  False


####-------------------------------------------------------------------------####
	def updateBeaconStates(self, fromPi, piNReceived, ipAddress, piMACSend, nOfSecs, msgs):

		try:
			setALLrPiVUpdate = ""
			beaconUpdatedIds = []
			updateFINGnow = False
			ln = len(msgs)
			if ln < 1: return beaconUpdatedIds
			dateString = datetime.datetime.now().strftime(_defaultDateStampFormat)

			newRPI			= ""
			fromPiU 		= unicode(fromPi)
			fromPiI			= int(fromPi)
			piNReceived		= unicode(piNReceived)
			if self.selectBeaconsLogTimer !={}: 
				for sMAC in self.selectBeaconsLogTimer:
					if piMACSend.find(sMAC[:self.selectBeaconsLogTimer[sMAC]]) ==0:
						self.indiLOG.log(20,u"sel.beacon logging: RPI msg: {}; pi#: {:2s};  {:3d}".format(piMACSend, fromPiU, msgs) )

			# rpi
			keepThisMessage, beaconUpdatedIds, updatepIP = self.handleRPIMessagePart(piMACSend, newRPI, fromPiU, piNReceived, ipAddress, dateString, beaconUpdatedIds)
			if not keepThisMessage: return beaconUpdatedIds


			###########################	 ibeacons ############################
			#### ---- update ibeacon info
			for msg in msgs:
				if True: # get data from message 
					if type(msg) != type({}): continue 
					mac		= msg[u"mac"].upper()
					reason	= msg[u"reason"]
					if u"typeOfBeacon" not in msg: 
						self.indiLOG.log(20,u"msg not complete  mac:{}; pi#={:2s}; msg:{}".format(mac, fromPiU, msg) )
						continue
					typeOfBeacon = msg[u"typeOfBeacon"]
					isTagged = (self.acceptNewTagiBeacons == u"all" and typeOfBeacon in self.knownBeaconTags) or typeOfBeacon == self.acceptNewTagiBeacons
					try:	rssi = float(msg[u"rssi"])
					except: rssi = -999.
					txPower = msg[u"txPower"]
					lCount	= msg[u"count"]
					rssiOffset = 0
					if rssi == -999 : 
						txPower = 0
					else: 
						try:	rssiOffset = float(self.RPI[fromPiU][u"rssiOffset"] )
						except: rssiOffset = 0
					try:	batteryLevel = msg[u"batteryLevel"]
					except: batteryLevel = ""
					try:	iBeacon	 = msg[u"iBeacon"]
					except: iBeacon  = ""
					if u"mfg_info" in msg: 	mfg_info = msg[u"mfg_info"]
					else:					mfg_info = ""


				if self.selectBeaconsLogTimer !={}: 
					for sMAC in self.selectBeaconsLogTimer:
						if mac.find(sMAC[:self.selectBeaconsLogTimer[sMAC]]) ==0:
							self.indiLOG.log(20,u"sel.beacon logging: newMSG    -1  - :{}; pi#={:2s}; msg{}".format(mac, fromPiU, msg) )

				if not self.checkBeaconDictIfok( mac, dateString, rssi, fromPiU, msg, isTagged): continue


				setALLrPiVUpdate, dev, props, newStates, keepThisMessage = self.getBeaconDeviceAndCheck( mac, typeOfBeacon, rssi, txPower, fromPiU, piMACSend, dateString, rssiOffset)
				if not keepThisMessage:  continue

				self.addToStatesUpdateDict(dev.id,u"updateReason", reason)

				if batteryLevel != "" and type(batteryLevel) == type(1) and  u"batteryLevel" in dev.states:
						newStates = self.addToStatesUpdateDict(dev.id,u"batteryLevel", int(msg[u"batteryLevel"]), newStates=newStates)
						newStates = self.addToStatesUpdateDict(dev.id,u"batteryLevelLastUpdate", datetime.datetime.now().strftime(_defaultDateStampFormat),newStates=newStates)

				if iBeacon  != "" and "iBeacon"  in dev.states:						newStates = self.addToStatesUpdateDict(dev.id,u"iBeacon", iBeacon, newStates=newStates)
				if mfg_info != "" and "mfg_info" in dev.states:						newStates = self.addToStatesUpdateDict(dev.id,u"mfg_info", mfg_info, newStates=newStates)


				if typeOfBeacon != "" and u"typeOfBeacon" in dev.states: 			newStates = self.addToStatesUpdateDict(dev.id,u"typeOfBeacon", typeOfBeacon, newStates=newStates)
				if typeOfBeacon != "": 												self.beacons[mac][u"typeOfBeacon"] = typeOfBeacon
				if typeOfBeacon != "" and (u"version" not in props or props[u"version"] != typeOfBeacon):
					props[u"version"] = typeOfBeacon
					dev.replacePluginPropsOnServer(props)


				updateSignal, updateFINGnow, newStates = self.checkForFastDown(mac, piMACSend, dev, props, rssi, fromPiU, newStates)


				# thsi enables better / faster location bounding to only specific room/ rpi
				logTRUEfromSignal = False	   
				if self.trackSignalStrengthIfGeaterThan[0] <99.:
					try:
						deltaSignalLOG = (rssi + rssiOffset - float(self.beacons[mac][u"receivedSignals"][fromPiI][u"rssi"]))
						if self.trackSignalStrengthIfGeaterThan[1] == u"i":
							logTRUEfromSignal =	 ( abs(deltaSignalLOG) > self.trackSignalStrengthIfGeaterThan[0]  ) or	(rssi ==-999. and float(self.beacons[mac][u"receivedSignals"][fromPiI][u"rssi"]) !=-999)
						else:
							logTRUEfromSignal =	 ( abs(deltaSignalLOG) > self.trackSignalStrengthIfGeaterThan[0]  ) and ( rssi !=-999 and self.beacons[mac][u"receivedSignals"][fromPiI][u"rssi"] !=-999)

					except Exception, e:

						self.indiLOG.log(40,u"Line {} has error={}".format(sys.exc_traceback.tb_lineno, e))
						logTRUEfromSignal = False



				updateSignal, updateFINGnow, newStates, logTRUEfromChangeOFRPI, oldRPI, closestRPI, beaconUpdatedIds = self.handleBeaconRealSignal(mac, piMACSend, dev, props, beaconUpdatedIds, rssi, txPower, rssiOffset, fromPiU, newStates, updateSignal, updateFINGnow, dateString )


				if self.selectBeaconsLogTimer !={}: 
					for sMAC in self.selectBeaconsLogTimer:
						if mac.find(sMAC[:self.selectBeaconsLogTimer[sMAC]]) ==0:
							self.indiLOG.log(20,u"sel.beacon logging: newMSG    -3  - :{}; bf cars".format(mac))

				if mac in self.CARS[u"beacon"]:
					if dev.states[u"status"] != newStates[u"status"] and time.time()- self.startTime > 30:
						self.updateCARS(mac,dev,newStates)

				if self.selectBeaconsLogTimer !={}: 
					for sMAC in self.selectBeaconsLogTimer:
						if mac.find(sMAC[:self.selectBeaconsLogTimer[sMAC]]) ==0:
							self.indiLOG.log(20,u"sel.beacon logging: newMSG    -4  - :{}; bf calc dist".format(mac))

				if updateSignal and "note" in dev.states and dev.states[u"note"].find(u"beacon") >-1:  
					try:
						props=dev.pluginProps
						expirationTime=props[u"expirationTime"]
						update, deltaDistance =self.calcPostion(dev, expirationTime, rssi=rssi)
						if ( update or (deltaDistance > self.beaconPositionsdeltaDistanceMinForImage) ) and u"showBeaconOnMap" in props and props[u"showBeaconOnMap"] in _GlobalConst_beaconPlotSymbols:
							#self.indiLOG.log(20,u"beaconPositionsUpdated; calcPostion:"+name+u" pi#="+fromPiU	  +u"   deltaDistance:"+ unicode(deltaDistance)	  +u"   update:"+ unicode(update)  )
							self.beaconPositionsUpdated =6

					except Exception, e:
						if unicode(e) != u"None":
							self.indiLOG.log(40,u"Line {} has error={}".format(sys.exc_traceback.tb_lineno, e))

				if self.newBeaconsLogTimer >0:
						try:
							created = self.getTimetimeFromDateString(dev.states[u"created"]) 
							if created + self.newBeaconsLogTimer > 2*time.time():
								self.indiLOG.log(20,u"new.beacon logging: newMSG     -2- :"+mac+u";  "+dev.name+ u" pi#="+fromPiU +u";  #Msgs="+unicode(lCount).ljust(2)    + u"  rssi="+unicode(rssi).rjust(6)      +u"                      txPow="+unicode(txPower).rjust(6)+u" cr="+dev.states[u"created"]+u" typeOfBeacon="+ typeOfBeacon)
							if self.newBeaconsLogTimer < time.time():
								self.indiLOG.log(20,u"new.beacon logging: resetting  newBeaconsLogTimer to OFF")
								self.newBeaconsLogTimer =0
						except Exception, e:
							self.indiLOG.log(40,u"Line {} has error={}".format(sys.exc_traceback.tb_lineno, e))

				if self.selectBeaconsLogTimer !={}: 
					for sMAC in self.selectBeaconsLogTimer:
						if mac.find(sMAC[:self.selectBeaconsLogTimer[sMAC]]) ==0:
							self.indiLOG.log(20,u"sel.beacon logging: newMSG    -5  - :{}; passed".format(mac))

				if logTRUEfromChangeOFRPI:
					self.indiLOG.log(20,u"ChangeOfRPI.beacon logging     :"+mac+u"  "+dev.name       + u" pi#="+unicode(closestRPI)+u" oldpi=" + unicode(oldRPI)+u";   #Msgs="+unicode(lCount).ljust(2)    + u"  rssi="+unicode(rssi).rjust(6)    + u"                        txPow="+unicode(txPower).rjust(6))
		  
				if logTRUEfromSignal:
					if abs(deltaSignalLOG)	 > 500 and rssi > -200:
						self.indiLOG.log(20,u"ChangeOfSignal.beacon logging:        "+mac+u";  "+dev.name+ u" pi#="+fromPiU     +u";  #Msgs="+unicode(lCount).ljust(2)     +u"  rssi="+unicode(rssi).rjust(6)         + u" off --> ON             txPow="+unicode(txPower).rjust(6))
					elif abs(deltaSignalLOG) > 500 and rssi < -200:
						self.indiLOG.log(20,u"ChangeOfSignal.beacon logging:        "+mac+u";  "+dev.name+ u" pi#="+fromPiU     +u";  #Msgs="+unicode(lCount).ljust(2)     +u"  rssi="+unicode(rssi).rjust(6)         + u" ON  --> off            txPow="+unicode(txPower).rjust(6))
					else:
						self.indiLOG.log(20,u"ChangeOfSignal.beacon logging:        "+mac+u";  "+dev.name+ u" pi#="+fromPiU     +u";  #Msgs="+unicode(lCount).ljust(2)     +u"  rssi="+unicode(rssi).rjust(6)         + u" new-old_Sig.= u"+ unicode(deltaSignalLOG).rjust(5)+ u"     txPow="+unicode(txPower).rjust(6))

				self.executeUpdateStatesDict(onlyDevID=dev.id, calledFrom=u"updateBeaconStates 1") 

			if updatepIP:
				if self.decideMyLog(u"Logic"): self.indiLOG.log(10,u"trying to update device note   for pi# " + fromPiU)
				if piMACSend in self.beacons:
					if self.beacons[piMACSend][u"indigoId"] != 0:
						try:
							dev = indigo.devices[self.beacons[piMACSend][u"indigoId"]]
							dev.updateStateOnServer(unicode(dev.id),u"note", u"PI-" + fromPiU)

						except Exception, e:
							if unicode(e).find(u"timeout waiting") > -1:
								self.indiLOG.log(40,u"Line {} has error={}".format(sys.exc_traceback.tb_lineno, e))
								self.indiLOG.log(40,u"communication to indigo is interrupted")
								return beaconUpdatedIds

							self.indiLOG.log(20,u"Could not update device for pi# " + fromPiU)

			if updateFINGnow: 
				self.updateFING(u"event")

		except Exception, e:

			if unicode(e).find(u"timeout waiting") > -1:
				self.indiLOG.log(40,u"Line {} has error={}".format(sys.exc_traceback.tb_lineno, e))
				self.indiLOG.log(40,u"communication to indigo is interrupted")
				return 
			if e != None	and unicode(e).find(u"not found in database") ==-1:
				self.indiLOG.log(40,u"Line {} has error={}".format(sys.exc_traceback.tb_lineno, e))

		if setALLrPiVUpdate == u"updateParamsFTP":
			self.setALLrPiV(u"piUpToDate", [u"updateParamsFTP"])


		return beaconUpdatedIds



####-------------------------------------------------------------------------####
	def manageDescription(self, existing, newFirstPart):
		try:
			newresult  = existing.split(u" ")
			if newresult[0] == newFirstPart: return existing
			newresult[0] = newFirstPart
			return " ".join(newresult)
		except Exception, e:
			if unicode(e) != u"None":
				self.indiLOG.log(40,u"Line {} has error={}".format(sys.exc_traceback.tb_lineno, e))
		return existing


####-------------------------------------------------------------------------####
	def getRPIdevName(self, closestRPI):
		closestRPIText =""
		if closestRPI != u"-1":
			try: closestRPIText = indigo.devices[int(self.RPI[unicode(closestRPI)][u"piDevId"])].name
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
			if currClosestRPI !=-1	and (time.time() - self.beacons[mac][u"receivedSignals"][currClosestRPI][u"lastSignal"]) <70.: # [u"receivedSignals"] =[rssi, timestamp,dist]
				currMinDist	= self.beacons[mac][u"receivedSignals"][currClosestRPI][u"distance"]
		except Exception, e: 
			if unicode(e) != u"None":
				self.indiLOG.log(40,u"Line {} has error={}".format(sys.exc_traceback.tb_lineno, e))
			currClosestRPI =-1; currMinDist = -9999.

		for sMAC in self.selectBeaconsLogTimer:
			if mac.find(sMAC[:self.selectBeaconsLogTimer[sMAC]]) ==0:
				self.indiLOG.log(20,u"sel.beacon logging: ClostR 1        :{}; currClosestRPIL:{}, newClosestRPI:{},  newMinDist:{}   currMinDist:{}".format(mac, currClosestRPI, newClosestRPI, newMinDist,  currMinDist))


		try:
			for piU in _rpiBeaconList:
				pi = int(piU)
				if self.RPI[piU][u"piOnOff"] != u"0": 
					bbb = self.beacons[mac][u"receivedSignals"][pi]
					try: # if empty field skip
						if time.time() - bbb[u"lastSignal"]  < 100.:  # signal recent enough
							if bbb[u"rssi"] > -300: 
								if bbb[u"distance"] < newMinDist:
									newMinDist   = bbb[u"distance"]
									newClosestRPI  = pi
						for sMAC in self.selectBeaconsLogTimer:
							if False and mac.find(sMAC[:self.selectBeaconsLogTimer[sMAC]]) ==0:
								self.indiLOG.log(20,u"sel.beacon logging: ClostR 2 :{}; piU:{}, t-lastSignal:{}, distance:{}; newClosestRPI:{}".format(mac,piU,  time.time() - bbb[u"lastSignal"],  bbb[u"distance"], newClosestRPI) )
					except:
						pass
			# dont switch if: <	 4 dBm diff and	 not defined then keep current 

			#if deviBeacon.states[u"note"].find(u"Pi-") > -1: self.indiLOG.log(20,u"checking for clostest RPI- {} {} {} {} ".format(mac, deviBeacon.name, newClosestRPI, newMinDist))

			if abs(newMinDist - currMinDist)  < 0.5 and  currClosestRPI !=-1: # 
				newClosestRPI = currClosestRPI
			for sMAC in self.selectBeaconsLogTimer:
				if mac.find(sMAC[:self.selectBeaconsLogTimer[sMAC]]) ==0:
					self.indiLOG.log(20,u"sel.beacon logging: ClostR 3        :{}; currClosestRPI:{}, newClosestRPI:{},  newMinDist:{}   currMinDist:{}".format(mac, currClosestRPI, newClosestRPI, newMinDist,  currMinDist) )

		except Exception, e: 
			if unicode(e) != u"None":
				self.indiLOG.log(40,u"Line {} has error={}".format(sys.exc_traceback.tb_lineno, e))
		return newClosestRPI

	
#		####calc distance from received signal and transmitted power assuming Signal ~ Power/r**2---------
####-------------------------------------------------------------------------####
	def findClosestRPIForBLEConnect(self, devBLE, pi, dist):
		if self.decideMyLog(u"BLE"): self.indiLOG.log(10,u"findClosestRPIForBLEConnect into   dev:{}, pi:{}, dist:{}".format(devBLE.name, pi, dist) )
		if u"closestRPI" not in devBLE.states: return -4

		newMinDist     = 99999.
		currMinDist    = 99999.
		newClosestRPI  = -1
		currClosestRPI = -1

		try:

			currClosestRPI	= int(devBLE.states[u"closestRPI"])
			piXX = u"Pi_{:02d}".format(currClosestRPI)
			if currClosestRPI != -1:
				deltaSec = time.time() - self.getTimetimeFromDateString(devBLE.states[piXX+u"_Time"])
				if deltaSec < 120.:
					currMinDist	= devBLE.states[piXX+u"_Distance"]
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
				if self.RPI[piU][u"piOnOff"] == u"0": 	continue
				piXX = u"Pi_{:02d}".format(pix)
				try: # if empty field skip
					deltaSec = time.time() - self.getTimetimeFromDateString(devBLE.states[piXX+u"_Time"])
					if deltaSec  < 120.:  # signal recent enough
						if float(devBLE.states[piXX+u"_Distance"]) <  newMinDist:
								newMinDist   =  float(devBLE.states[piXX+u"_Distance"])
								newClosestRPI  = pix
					if self.decideMyLog(u"BLE"): self.indiLOG.log(10,u"findClosestRPIForBLEConnect loop pi:{}, newClosestRPI:{}, devdist:{}, newDist:{} deltaS:{}".format(piU, newClosestRPI, devBLE.states[piXX+u"_Distance"],newMinDist, deltaSec ) )
				except Exception, e: 
					if unicode(e) != u"None":
						self.indiLOG.log(40,u"Line {} has error={}".format(sys.exc_traceback.tb_lineno, e) )
			# dont switch if: <	 4 dBm diff and	 not defined then keep current 
			if abs(newMinDist - currMinDist) < 2 and  currClosestRPI !=-1: # 
				newClosestRPI = currClosestRPI
		except Exception, e: 
			if unicode(e) != u"None":
				self.indiLOG.log(40,u"Line {} has error={}".format(sys.exc_traceback.tb_lineno, e))
		if self.decideMyLog(u"BLE"): self.indiLOG.log(10,u"findClosestRPIForBLEConnect return w  newClosestRPI:{}".format(newClosestRPI) )
		
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
			###self.indiLOG.log(20,unicode(power)+u"  "+ unicode(rssi) +u" " +unicode(dist)) 
			return dist

		except	 Exception, e:
			if unicode(e) != u"None":
				self.indiLOG.log(40,u"Line {} has error={}".format(sys.exc_traceback.tb_lineno, e))
		return 99999.


	def getActiveBLERPI(self, dev):
		xx = dev.description.lower().split(u"pi")
		activePis =[]
		if len(xx) == 2:
			xx = xx[1].split(u",")
			for x in xx:
				try: activePis.append( int(x.replace(u" ","") ) )
				except: pass
		else:
			activePis =[]
		return activePis

####-------------------------------------------------------------------------####
	def sendGPIOCommand(self, ip, pi, typeId, cmd, GPIOpin=0, pulseUp=0, pulseDown=0, nPulses=0, analogValue=0,rampTime=0, i2cAddress=0,text="",soundFile="",restoreAfterBoot="0",startAtDateTime=0, inverseGPIO=False, devId=0):
		cmd1 =""
		try:
			if	 cmd == u"newMessage":
				cmd1 = {u"device": typeId,  u"command":cmd, u"startAtDateTime": startAtDateTime}
			elif cmd == u"startCalibration":
				cmd1 = {u"device": typeId,  u"command":cmd, u"startAtDateTime": startAtDateTime}
			elif cmd == u"BLEAnalysis":
				cmd1 = {u"minRSSI": typeId, u"command":cmd, u"startAtDateTime": startAtDateTime}
			elif cmd == u"trackMac":
				cmd1 = {u"mac": typeId, u"command":cmd, u"startAtDateTime": startAtDateTime}
			elif cmd == u"resetDevice":
				cmd1 = {u"device": typeId,  u"command":cmd, u"startAtDateTime": startAtDateTime}
			elif cmd == u"getBeaconParameters":
				cmd1 = {u"device": typeId,  u"command":cmd, u"startAtDateTime": startAtDateTime}
			elif cmd == u"beepBeacon":
				cmd1 = {u"device": typeId,  u"command":cmd, u"startAtDateTime": startAtDateTime}
			else:
				if typeId == u"setMCP4725":
					cmd1 = {u"device": typeId, u"command": cmd, u"i2cAddress": i2cAddress, u"values":{u"analogValue":analogValue,"rampTime":rampTime,"pulseUp":pulseUp,"pulseDown": pulseDown,"nPulses":nPulses},"restoreAfterBoot": restoreAfterBoot, u"startAtDateTime": startAtDateTime, u"devId": devId}

				elif typeId == u"setPCF8591dac":
					cmd1 = {u"device": typeId, u"command": cmd, u"i2cAddress": i2cAddress, u"values":{u"analogValue":analogValue,"rampTime":rampTime,"pulseUp":pulseUp,"pulseDown": pulseDown,"nPulses":nPulses},"restoreAfterBoot": restoreAfterBoot, u"startAtDateTime": startAtDateTime, u"devId": devId}

				elif typeId == u"myoutput":
					cmd1 = {u"device": typeId, u"command": u"myoutput", u"text": text, u"restoreAfterBoot": restoreAfterBoot, u"startAtDateTime": startAtDateTime, u"devId": devId}

				elif typeId == u"playSound":
					cmd1 = {u"device": typeId, u"command": cmd, u"soundFile": soundFile, u"startAtDateTime": startAtDateTime, u"devId": devId}

				elif typeId.find(u"OUTPUTgpio") >- 1:
					if cmd == u"up" or cmd == u"down":
						cmd1 = {u"device": typeId, u"command": cmd, u"pin": GPIOpin, u"restoreAfterBoot": restoreAfterBoot, u"startAtDateTime": startAtDateTime, u"inverseGPIO": inverseGPIO, u"devId": devId}
					elif cmd in[u"pulseUp",u"pulseDown",u"continuousUpDown",u"analogWrite"]:
						cmd1 = {u"device": typeId, u"command": cmd, u"pin": GPIOpin, u"values": {u"analogValue":analogValue,"pulseUp":pulseUp,"pulseDown": pulseDown,"nPulses":nPulses}, u"restoreAfterBoot": restoreAfterBoot, u"startAtDateTime": startAtDateTime, u"inverseGPIO": inverseGPIO, u"devId": devId}
					elif cmd == u"disable":
						cmd1 = {u"device": typeId, u"command": cmd, u"pin": GPIOpin, u"devId": devId}

				elif typeId.find(u"OUTPUTi2cRelay") >- 1:
					if cmd == u"up" or cmd == u"down":
						cmd1 = {u"device": typeId, u"command": cmd, u"pin": GPIOpin, u"restoreAfterBoot": restoreAfterBoot, u"startAtDateTime": startAtDateTime, u"inverseGPIO": inverseGPIO, u"devId": devId, "i2cAddress":i2cAddress}
					elif cmd in[u"pulseUp",u"pulseDown",u"continuousUpDown"]:
						cmd1 = {u"device": typeId, u"command": cmd, u"pin": GPIOpin, u"values": {u"pulseUp":pulseUp,u"pulseDown": pulseDown,u"nPulses":nPulses}, u"restoreAfterBoot": restoreAfterBoot, u"startAtDateTime": startAtDateTime, u"inverseGPIO": inverseGPIO, u"devId": devId, u"i2cAddress":i2cAddress}
					elif cmd == u"disable":
						cmd1 = {u"device": typeId, u"command": cmd, u"pin": GPIOpin, u"devId": devId}

				elif typeId.find(u"display") >- 1:
					if cmd == u"up" or cmd == u"down":
						cmd1 = {u"device": typeId, u"command": cmd,	 u"restoreAfterBoot": restoreAfterBoot, u"devId": devId}

			try: cmds = json.dumps([cmd1])
			except Exception, e:
				self.indiLOG.log(40,u"json error for cmds:{}".format(cmd1))
				return

			if self.decideMyLog(u"OutputDevice"): self.indiLOG.log(10,	u"sendGPIOCommand: " + cmds)
			self.sendtoRPI(ip, pi ,cmds, calledFrom=u"sendGPIOCommand")

		except Exception, e:
			if unicode(e) != u"None":
				self.indiLOG.log(40,u"Line {} has error={}".format(sys.exc_traceback.tb_lineno, e))



####-------------------------------------------------------------------------####
	def sendGPIOCommands(self, ip, pi, cmd, GPIOpin, inverseGPIO):
		nCmds = len(cmd)
		cmd1 =[]
		try:
			for kk in range(nCmds):
				if cmd[kk] == u"up" or cmd[kk] == u"down":
					cmd1.append({u"device": "OUTPUTgpio-1", u"command": cmd[kk], u"pin": GPIOpin[kk], u"inverseGPIO": inverseGPIO[kk]})

			cmds = json.dumps(cmd1)

			if self.decideMyLog(u"OutputDevice"): self.indiLOG.log(10,u"sendGPIOCommand-s-: {}".format(cmds) )
			self.sendtoRPI(ip, pi ,cmds, calledFrom=u"sendGPIOCommand")

		except Exception, e:
			if unicode(e) != u"None":
				self.indiLOG.log(40,u"Line {} has error={}".format(sys.exc_traceback.tb_lineno, e))




			###########################	   UTILITIES  #### START #################


####-------------------------------------------------------------------------####
	def setupFilesForPi(self, calledFrom=""):
		try:
			if time.time() - self.lastsetupFilesForPi < 5: return 
			self.lastsetupFilesForPi = time.time()
			if self.decideMyLog(u"UpdateRPI"): self.indiLOG.log(10,u"updating pi server files called from: {}".format(calledFrom) )

			self.makeBeacons_parameterFile()

			for piU in self.RPI:
				if self.RPI[piU][u"piOnOff"] == u"0": continue
				self.makeParametersFile(piU)
				self.makeInterfacesFile(piU)
				self.makeSupplicantFile(piU)

			   
		except Exception, e:
				self.indiLOG.log(40,u"Line {} has error={}".format(sys.exc_traceback.tb_lineno, e))
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
			for beacon in self.beacons:
				if self.beacons[beacon][u"ignore"] >= 1 or self.beacons[beacon][u"ignore"] == -1:  xx1.append(beacon)
				devId = self.beacons[beacon][u"indigoId"]
				if devId >0:
					try:	dev = indigo.devices[devId]
					except: continue
					props = dev.pluginProps
					if self.beacons[beacon][u"ignore"] == 0 and dev.enabled:
						xx2[beacon] = { u"typeOfBeacon":"", u"useOnlyIfTagged":""}
						tag = self.beacons[beacon][u"typeOfBeacon"]
						xx2[beacon][u"typeOfBeacon"] = tag
					
						xx2[beacon][u"useOnlyIfTagged"] = 0
						try: 
							xx2[beacon][u"useOnlyIfTagged"] = int(self.beacons[beacon][u"useOnlyPrioTagMessageTypes"])
						except: 
							if tag in self.knownBeaconTags:
								xx2[beacon][u"useOnlyIfTagged"] = self.knownBeaconTags[tag][u"useOnlyThisTagToAcceptBeaconMsgDefault"]

					try:
						if int(props[u"signalDelta"]) < 200:
							xx4[beacon] = int(props[u"signalDelta"])
					except:pass
					try:
						if int(props[u"minSignalOn"]) >-200:
							xx5[beacon] = int(props[u"minSignalOn"])
					except:	pass
					try:
						if int(props[u"minSignalOff"]) >200:
							xx5[beacon] = int(props[u"minSignalOff"])
					except:	pass
					try:	
						if int(props[u"fastDown"]) >0: 
							xx8[beacon] = {u"seconds":int(props[u"fastDown"])}
					except:	pass

			out[u"ignoreMAC"]			= xx1
			out[u"onlyTheseMAC"]		= xx2
			out[u"signalDelta"]			= xx4
			out[u"minSignalOn"]			= xx5
			out[u"minSignalOff"]		= xx6
			out[u"fastDownList"]		= xx8

			##self.indiLOG.log(40,u"out: {}".format(out))

			out = json.dumps(out, sort_keys=True, indent=2)
			f = open(self.indigoPreferencesPluginDir + "all/beacon_parameters", u"w")
			f.write(out)
			f.close()
			if len(out) > 50000:
					self.indiLOG.log(50,"parameter file:\n{}all/beacon_parameters\n has become TOOO BIG, \nplease do menu/ignore individual beacons and reset history.\nyou might also want to switch off accept new ibeacons in config\n".format(self.indigoPreferencesPluginDir) )
			f = open(self.indigoPreferencesPluginDir + "all/beacon_parameters", u"w")
			f.write(out)
			f.close()

			try:
				f = open(self.indigoPreferencesPluginDir + u"all/knownBeaconTags", u"w")
				f.write(json.dumps(self.knownBeaconTags))
				f.close()
			except Exception, e:
					self.indiLOG.log(40,u"Line {} has error={}".format(sys.exc_traceback.tb_lineno, e))
		except Exception, e:
				self.indiLOG.log(40,u"Line {} has error={}".format(sys.exc_traceback.tb_lineno, e))
		return



####-------------------------------------------------------------------------####
	def makeInterfacesFile(self,piU):
		try:
			if self.RPI[piU][u"piOnOff"] == u"0": return
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
				self.indiLOG.log(40,u"Line {} has error={}".format(sys.exc_traceback.tb_lineno, e))
		return

####-------------------------------------------------------------------------####
	def makeSupplicantFile(self,piU):
		try:
			if self.RPI[piU][u"piOnOff"] == u"0": return
			f = open(self.indigoPreferencesPluginDir + "interfaceFiles/wpa_supplicant.conf." + piU, u"w")
			f.write(u"ctrl_interface=DIR=/var/run/wpa_supplicant GROUP=netdev\n")
			f.write(u"update_config=1\n")
			f.write(u"country=US\n")
			f.write(u"network={\n")
			f.write('   ssid="' + self.wifiSSID + '"\n')
			f.write('   psk="' + self.wifiPassword + '"\n')
			if self.key_mgmt != "" and self.key_mgmt != u"NONE":
				f.write('   key_mgmt="' + self.key_mgmt + '"\n')
			f.write(u"}\n")
			f.close()
		except Exception, e:
				self.indiLOG.log(40,u"Line {} has error={}".format(sys.exc_traceback.tb_lineno, e))
		return

####-------------------------------------------------------------------------####
	def makeParametersFile(self, piU, retFile=False):
		try:
				if self.RPI[piU][u"piOnOff"] == u"0": return
				out = {}
				pi = int(piU)

				out[u"configured"]		  		  = (datetime.datetime.now()).strftime(_defaultDateStampFormat)
				out[u"rebootWatchDogTime"]		  = self.rebootWatchDogTime
				out[u"GPIOpwm"]					  = self.GPIOpwm
				if pi == self.debugRPI:	out[u"debugRPI"] = 1
				else:					out[u"debugRPI"] = 0
				out[u"restartBLEifNoConnect"]	  = self.restartBLEifNoConnect
				out[u"acceptNewiBeacons"]		  = self.acceptNewiBeacons
				out[u"acceptNewTagiBeacons"]	  = self.acceptNewTagiBeacons
				out[u"rebootHour"]				  = -1
				out[u"ipOfServer"]				  = self.myIpNumber
				out[u"portOfServer"]			  = self.portOfServer
				out[u"compressRPItoPlugin"]		  = self.compressRPItoPlugin
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
				out[u"enableiBeacons"]			  = self.RPI[piU][u"enableiBeacons"]
				out[u"pressureUnits"]			  = self.pluginPrefs.get(u"pressureUnits", u"hPascal")
				out[u"distanceUnits"]			  = self.pluginPrefs.get(u"distanceUnits", u"1.0")
				out[u"tempUnits"]				  = self.pluginPrefs.get(u"tempUnits", u"C")
				out[u"IPnumberOfRPI"]			  = self.RPI[piU][u"ipNumberPi"]
				out[u"deltaChangedSensor"]		  = self.RPI[piU][u"deltaChangedSensor"]
				out[u"sensorRefreshSecs"]		  = float(self.RPI[piU][u"sensorRefreshSecs"])
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
							self.indiLOG.log(40,u"Line {} has error={}".format(sys.exc_traceback.tb_lineno, e))
							self.indiLOG.log(40,u"communication to indigo is interrupted")
							return
						if unicode(e).find(u"not found in database") >-1:
							self.indiLOG.log(40,u"Line {} has error={}".format(sys.exc_traceback.tb_lineno, e))
							self.indiLOG.log(40,u"RPI:{} devid:{} not in indigo, if RPI justd eleted, it will resolve itself ".format(piU ,piID))
							self.delRPI(pi=piU, calledFrom=u"makeParametersFile")
							self.updateNeeded += u",fixConfig"
							self.fixConfig(checkOnly = [u"all",u"rpi",u"force"],fromPGM=u"makeParametersFile bad rpi") 
						else:	 
							self.indiLOG.log(40,u"Line {} has error={}".format(sys.exc_traceback.tb_lineno, e))
							self.indiLOG.log(40,u"RPI: {} error ..  piDevId not set:{}".format(piU ,self.RPI[piU]))
							self.updateNeeded += u",fixConfig"
							self.fixConfig(checkOnly = [u"all",u"rpi"],fromPGM=u"makeParametersFile2")

					if piDeviceExist: 

						if u"rpiDataAcquistionMethod" in props and props[u"rpiDataAcquistionMethod"] in [u"socket",u"hcidumpWithRestart",_GlobalConst_emptyrPiProps[u"rpiDataAcquistionMethod"]]:
								out[u"rpiDataAcquistionMethod"]	  = props[u"rpiDataAcquistionMethod"]
						else:
								out[u"rpiDataAcquistionMethod"]	  = self.rpiDataAcquistionMethod

						if u"compressRPItoPlugin" in props:
							try: 	out[u"compressRPItoPlugin"] =  int(props[u"compressRPItoPlugin"])
							except: pass			

						if u"eth0" in props and "wlan0" in props:
							try: 	out[u"wifiEth"] =  {u"eth0":json.loads(props[u"eth0"]),u"wlan0":json.loads(props[u"wlan0"])}
							except: pass			

						if u"startXonPi" in props:
							try:    out[u"startXonPi"]  = props[u"startXonPi"]
							except: out[u"startXonPi"]  = u"leaveAlone"

						if u"typeForPWM" in props:
							try:    out[u"typeForPWM"]  = props[u"typeForPWM"]
							except: out[u"typeForPWM"]  = u"GPIO"

						
						if u"timeZone" in props:
							try:    out[u"timeZone"]  = props[u"timeZone"]
							except: out[u"timeZone"]  = u"99"

						if u"clearHostsFile" in props:
							try:    out[u"clearHostsFile"]  = props[u"clearHostsFile"]
							except: out[u"clearHostsFile"]  = u"0"

						out[u"ifNetworkChanges"]  = u"0"
						if u"ifNetworkChanges" in props:
							out[u"ifNetworkChanges"]	=  (props[u"ifNetworkChanges"])

						out[u"addNewOneWireSensors"]  = u"0"
						if u"addNewOneWireSensors" in props:
							out[u"addNewOneWireSensors"]	=  (props[u"addNewOneWireSensors"])

						out[u"startWebServerSTATUS"]  = u"0"
						if u"startWebServerSTATUS" in props:
							out[u"startWebServerSTATUS"]	=  int(props[u"startWebServerSTATUS"])

						out[u"startWebServerINPUT"]  = u"0"
						if u"startWebServerINPUT" in props:
							out[u"startWebServerINPUT"]	=  int(props[u"startWebServerINPUT"])

						out[u"GPIOTypeAfterBoot1"]  = u"off"
						if u"GPIOTypeAfterBoot1" in props:
							out[u"GPIOTypeAfterBoot1"]			=  props[u"GPIOTypeAfterBoot1"]

						out[u"GPIOTypeAfterBoot2"]  = u"off"
						if u"GPIOTypeAfterBoot2" in props:
							out[u"GPIOTypeAfterBoot2"]			=  props[u"GPIOTypeAfterBoot2"]

						out[u"GPIONumberAfterBoot1"]  = u"-1"
						if u"GPIONumberAfterBoot1" in props:
							try:    out[u"GPIONumberAfterBoot1"]	=  int(props[u"GPIONumberAfterBoot1"])
							except: pass
						out[u"GPIONumberAfterBoot2"]  = u"-1"
						if u"GPIONumberAfterBoot2" in props:
							try:    out[u"GPIONumberAfterBoot2"]	=  int(props[u"GPIONumberAfterBoot2"])
							except: pass

						out[u"simpleBatteryBackupEnable"]  =  u"0"
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


						out[u"shutDownPinEnable"]  =  u"0"
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


						out[u"batteryUPSshutdownEnable"]  =  u"0"
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

						if u"rebootAtMidnight" in props and props[u"rebootAtMidnight"] == u"0":
							out[u"rebootHour"]			 = -1
						else:	 
							out[u"rebootHour"]			 = self.rebootHour

						if u"sleepAfterBoot" in props and props[u"sleepAfterBoot"] in [u"0",u"5",u"10",u"15"]:
							out[u"sleepAfterBoot"]			 = props[u"sleepAfterBoot"]
						else:
							out[u"sleepAfterBoot"]			 = u"10"


						out = self.updateSensProps(out, props, u"fanEnable", elseSet=u"-")
						out = self.updateSensProps(out, props, u"fanGPIOPin", elseSet=u"-1")
						out = self.updateSensProps(out, props, u"fanTempOnAtTempValue", elseSet=u"60")
						out = self.updateSensProps(out, props, u"fanTempOffAtTempValue", elseSet=u"2")
						out = self.updateSensProps(out, props, u"fanTempDevId", elseSet=u"0")


						out = self.updateSensProps(out, props, u"networkType", elseSet=u"fullIndigo")
						out = self.updateSensProps(out, props, u"BeaconUseHCINo")
						out = self.updateSensProps(out, props, u"BLEconnectUseHCINo")
						out = self.updateSensProps(out, props, u"BLEconnectMode")
						out = self.updateSensProps(out, props, u"enableMuxI2C")
						out = self.updateSensProps(out, props, u"bluetoothONoff")
						out = self.updateSensProps(out, props, u"useRTC", elseSet="")
						out = self.updateSensProps(out, props, u"pin_webAdhoc")
						out = self.updateSensProps(out, props, u"useRamDiskForLogfiles", elseSet=u"0")
						out = self.updateSensProps(out, props, u"rebootCommand")
						out = self.updateSensProps(out, props, u"BLEserial", elseSet=u"sequential")
						out = self.updateSensProps(out, props, u"sendToIndigoSecs")

				except Exception, e:
					self.indiLOG.log(40,u"Line {} has error={}".format(sys.exc_traceback.tb_lineno, e))
					return ""



				out[u"rPiRestartCommand"]	 = self.rPiRestartCommand[pi]
				if self.rPiRestartCommand[pi].find(u"reboot") >- 1:
					out[u"reboot"] = datetime.datetime.now().strftime(u"%Y-%m-%d-%H:%M:%S")

				out[u"timeStamp"]  = datetime.datetime.now().strftime(u"%Y-%m-%d-%H:%M:%S")

				self.rPiRestartCommand[pi]= ""


				out[u"sensors"]				 = {}
				for sensor in self.RPI[piU][u"input"]:
					try:
						if sensor not in _GlobalConst_allowedSensors and sensor not in _BLEsensorTypes: continue
						if sensor not in self.RPI[piU][u"input"]: continue
						if len(self.RPI[piU][u"input"][sensor]) == 0: continue
						sens = {}
						for devIdS in self.RPI[piU][u"input"][sensor]:
							if devIdS == u"0" or devIdS == "": continue
							try:
								devId = int(devIdS)
								dev = indigo.devices[devId]
							except Exception, e:
								if unicode(e).find(u"timeout waiting") > -1:
									self.indiLOG.log(40,u"Line {} has error={}".format(sys.exc_traceback.tb_lineno, e))
									self.indiLOG.log(40,u"communication to indigo is interrupted")
									return
								self.indiLOG.log(40,u"Line {} has error={}".format(sys.exc_traceback.tb_lineno, e))
								continue

							if not dev.enabled: continue
							props = dev.pluginProps
							sens[devIdS] = {}

							if u"deviceDefs" in props:
								try:    sens[devIdS] = {u"INPUTS":json.loads(props[u"deviceDefs"])}
								except: pass
							sens[devIdS] = self.updateSensProps(sens[devIdS], props, u"gpio")

							if u"serialNumber" in dev.states:
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
							if u"noI2cCheck" not in props or  not props[u"noI2cCheck"]:
								sens[devIdS] = self.updateSensProps(sens[devIdS], props, u"i2cAddress")

							sens[devIdS] = self.updateSensProps(sens[devIdS], props, u"sensorRefreshSecs")
							sens[devIdS] = self.updateSensProps(sens[devIdS], props, u"codeType")
							sens[devIdS] = self.updateSensProps(sens[devIdS], props, u"nBits")
							sens[devIdS] = self.updateSensProps(sens[devIdS], props, u"nInputs")
							sens[devIdS] = self.updateSensProps(sens[devIdS], props, u"isBLESensorDevice")

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
							sens[devIdS] = self.updateSensProps(sens[devIdS], props, u"offsetAlt")
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

							sens[devIdS] = self.updateSensProps(sens[devIdS], props, u"updateIndigoTiming")
							sens[devIdS] = self.updateSensProps(sens[devIdS], props, u"updateIndigoDeltaTemp")
							sens[devIdS] = self.updateSensProps(sens[devIdS], props, u"updateIndigoDeltaAccelVector")
							sens[devIdS] = self.updateSensProps(sens[devIdS], props, u"updateIndigoDeltaMaxXYZ")

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
							###if self.decideMyLog(u"OfflineRPI"): self.indiLOG.log(10,piU + "  sensor " + unicode(out[u"sensors"][sensor]) )
					except Exception, e:
						self.indiLOG.log(40,u"Line {} has error={}".format(sys.exc_traceback.tb_lineno, e))
						self.indiLOG.log(40,unicode(sens))

				out[u"sensorList"] = self.RPI[piU][u"sensorList"]

				out[u"output"]={} 
				for devOut in indigo.devices.iter(u"props.isOutputDevice"):
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
														  u"RGB":json.loads(u"["+propsOut[u"clockMMmarksRGB"]+u"]"),
														  u"marks":json.loads(propsOut[u"clockMMmarks"])}

								theDict[u"marks"][u"SS"] = {u"ringNo":json.loads(u"["+propsOut[u"clockSSmarksRings"]+u"]"),
														  u"RGB":json.loads(u"["+propsOut[u"clockSSmarksRGB"]+u"]"),
														  u"marks":json.loads(propsOut[u"clockSSmarks"])}

								theDict[u"marks"][u"DD"] = {u"ringNo":json.loads(u"["+propsOut[u"clockDDmarksRings"]+u"]"),
														  u"RGB":json.loads(u"["+propsOut[u"clockDDmarksRGB"]+u"]"),
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

								if u"motorType" in propsOut:
									theDict[u"motorType"]				= propsOut[u"motorType"]
									if propsOut[u"motorType"].find(u"unipolar") > -1 or propsOut[u"motorType"].find(u"bipolar") > -1:
										theDict[u"pin_CoilA1"]			= propsOut[u"pin_CoilA1"]
										theDict[u"pin_CoilA2"]			= propsOut[u"pin_CoilA2"]
										theDict[u"pin_CoilB1"]			= propsOut[u"pin_CoilB1"]
										theDict[u"pin_CoilB2"]			= propsOut[u"pin_CoilB2"]
									elif propsOut[u"motorType"].find(u"DRV8834") > -1:
										theDict[u"pin_Step"]			= propsOut[u"pin_Step"]
										theDict[u"pin_Dir"]				= propsOut[u"pin_Dir"]
										theDict[u"pin_Sleep"]			= propsOut[u"pin_Sleep"]
									elif propsOut[u"motorType"].find(u"A4988") > -1:
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
						if u"noI2cCheck" not in propsOut or  not propsOut[u"noI2cCheck"]:
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
							##self.indiLOG.log(20,unicode(propsOut))
							extraPageForDisplay =[]
							#self.indiLOG.log(20,unicode(propsOut))
							for ii in range(10):
								if u"extraPage"+unicode(ii)+u"Line0" in propsOut and "extraPage"+unicode(ii)+u"Line1" in propsOut and u"extraPage"+unicode(ii)+u"Color" in propsOut:
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
						self.indiLOG.log(30,u"creating paramatersfile .. please fix device {}; rpi number wrong {} , outdput dev not linked ?, typeId: {}, out[output]: {}".format(devOut.name, piU, typeId, out[u"output"]))


				out = self.writeJson(out, fName = self.indigoPreferencesPluginDir + u"interfaceFiles/parameters." + piU , fmtOn=self.parametersFileSort )
 
		except Exception, e:
				self.indiLOG.log(40,u"Line {} has error={}".format(sys.exc_traceback.tb_lineno, e))
		if retFile: return out
		return

####-------------------------------------------------------------------------####
	def updateSensProps(self, sens, props, param, elseSet=None):
		if param in props and props[param] !="":
			sens[param] = props[param]
		elif  param in props and props[param] == "" and elseSet	 == u"--force--":
			sens[param] = ""
		elif elseSet  is not None:
			sens[param] = elseSet

		return sens



####-------------------------------------------------------------------------####
####------------------delayed action queu management ------------------------START
####-------------------------------------------------------------------------####
	def startDelayedActionQueue(self):

		if self.delayedActions[u"state"] == u"running":
				self.indiLOG.log(20,u"no need to start Thread, delayed action thread already running" )
				return 

		self.indiLOG.log(20,u" .. restarting   thread for delayed actions, state was: {}".format(self.delayedActions[u"state"]) )
		self.delayedActions[u"lastCheck"] = time.time()
		self.delayedActions[u"state"] = u"start"
		self.sleep(0.1)
		self.delayedActions[u"thread"]  = threading.Thread(name=u'self.delayedActionsThread', target=self.delayedActionsThread)
		self.delayedActions[u"thread"].start()
		return 
###-------------------------------------------------------------------------####
	def stopDelayedActionQueue(self):

		if self.delayedActions[u"state"] != u"running":
				self.indiLOG.log(20,u"no need to stop Thread, delayed action thread already stopped" )
				return 

		self.indiLOG.log(20,u" .. stopping   thread for delayed actions, state was: {}".format(self.delayedActions[u"state"]) )
		self.delayedActions[u"lastCheck"] = time.time()
		self.delayedActions[u"state"] = u"stop"
		return 

####-------------------------------------------------------------------------####
	def delayedActionsThread(self):
		try:
			self.delayedActions[u"state"] = u"running"
			if self.decideMyLog(u"Special"): self.indiLOG.log(20,u"delayedActionsThread starting ")
			while self.delayedActions[u"state"] == u"running":
				self.sleep(1)
				self.delayedActions[u"lastCheck"] = time.time()

				addback = []
				while not self.delayedActions[u"data"].empty():
					action = self.delayedActions[u"data"].get()

					#if self.decideMyLog(u"Special"): self.indiLOG.log(20,u"delayedActionsThread time?{:.1f}; action:{} ".format(time.time() - action[u"actionTime"], action))

					self.delayedActions[u"lastActive"]  = time.time()

					if time.time() - action[u"actionTime"] < 0: 
						addback.append(action)
						continue

					dev = indigo.devices[action[u"devId"]]
					for updateItem in action[u"updateItems"]: 
						if self.decideMyLog(u"Special"): self.indiLOG.log(20,u"delayedActionsThread updateItem:{} ".format(updateItem))
						if updateItem[u"stateName"] in dev.states:
							if u"uiValue" in updateItem:
								dev.updateStateOnServer( updateItem[u"stateName"], updateItem[u"value"], uiValue=updateItem[u"uiValue"])
							else:
								dev.updateStateOnServer( updateItem[u"stateName"], updateItem[u"value"])

					if u"image" in action:
						if action[u"image"] == u"on":
							dev.updateStateImageOnServer(indigo.kStateImageSel.SensorOn)
						elif action[u"image"] == u"off":
							dev.updateStateImageOnServer(indigo.kStateImageSel.SensorOff)
						elif action[u"image"] == u"tripped":
							dev.updateStateImageOnServer(indigo.kStateImageSel.SensorTripped)

				for action in addback:
					self.delayedActions[u"data"].put(action)	


		except Exception, e:
			if unicode(e) != u"None":
				self.indiLOG.log(40,u"Line {} has error={}".format(sys.exc_traceback.tb_lineno, e))
		self.indiLOG.log(20,u"delayedActions  update thread stopped, state was:{}".format(self.delayedActions[u"state"]) )
		self.delayedActions[u"state"] = u"stopped - exiting thread"
		return

###-------------------------------------------------------------------------####
####------------------delayed action queu management ------------------------end
###-------------------------------------------------------------------------####




####------------------rpi update queue management ----------------------------START
####------------------rpi update queue management ----------------------------START
####------------------rpi update queue management ----------------------------START

####-------------------------------------------------------------------------####
	def startUpdateRPIqueues(self, state, piSelect="all"):
		if state =="start":
			self.laststartUpdateRPIqueues = time.time()
			self.indiLOG.log(10,u"starting UpdateRPIqueues ")
			for piU in self.RPI:
				if self.RPI[piU][u"piOnOff"] != u"1": continue
				if piSelect == u"all" or piU == piSelect:
						self.startOneUpdateRPIqueue(piU)

		elif state =="restart":
			if (piSelect == u"all" and time.time() - self.laststartUpdateRPIqueues > 70) or piSelect != u"all":
				self.laststartUpdateRPIqueues = time.time()
				for piU in self.RPI:
					if self.RPI[piU][u"piOnOff"] != u"1": continue
					if piSelect == u"all" or piU == piSelect:
						if time.time() - self.rpiQueues[u"lastCheck"][piU] > 100:
							self.stopUpdateRPIqueues(piSelect=piU)
							time.sleep(0.5)
						if  time.time() - self.rpiQueues[u"lastCheck"][piU] > 100:
							self.startOneUpdateRPIqueue(piU, reason=u"active messages pending timeout")
						elif self.rpiQueues[u"state"][piU] != u"running":
							self.startOneUpdateRPIqueue(piU, reason=u"not running")
		return 

####-------------------------------------------------------------------------####
	def startOneUpdateRPIqueue(self, piU, reason=""):

		if self.RPI[piU][u"piOnOff"] != u"1": return 
		if piU in self.rpiQueues[u"state"]:
			if self.rpiQueues[u"state"][piU] == u"running":
				self.indiLOG.log(20,u"no need to start Thread, pi# {} thread already running".format(piU) )
				return 

		self.indiLOG.log(20,u" .. restarting   thread for pi# {}, state was : {} - {}".format(piU, self.rpiQueues[u"state"][piU], reason) )
		self.rpiQueues[u"lastCheck"][piU] = time.time()
		self.rpiQueues[u"state"][piU]	= u"start"
		self.sleep(0.1)
		self.rpiQueues[u"thread"][piU]  = threading.Thread(name=u'self.rpiUpdateThread', target=self.rpiUpdateThread, args=(piU,))
		self.rpiQueues[u"thread"][piU].start()
		return 
###-------------------------------------------------------------------------####
	def stopUpdateRPIqueues(self, piSelect="all"):
		self.rpiQueues[u"reset"]		= {}
		for piU in self.RPI:
			if piU == piSelect or piSelect == u"all":
				self.stopOneUpdateRPIqueues(piU, reason=u"; "+ piSelect+u";")
		return 
###-------------------------------------------------------------------------####
	def stopOneUpdateRPIqueues(self, piU, reason=""):
		self.rpiQueues[u"state"][piU]	= u"stop "+reason
		self.rpiQueues[u"reset"][piU]	= True
		return 


####-------------------------------------------------------------------------####
	def sendFilesToPiFTP(self, piU, fileToSend="",endAction="repeatUntilFinished"):
		if time.time() - self.rpiQueues[u"lastCheck"][piU] > 100 or self.rpiQueues[u"state"][piU] != u"running":
			self.startUpdateRPIqueues(u"restart", piSelect=piU)
		next = {u"pi":piU, u"fileToSend":fileToSend, u"endAction":endAction, u"type":u"ftp", u"tries":0, u"exeTime":time.time()}
		self.removeONErPiV(piU, u"piUpToDate", [fileToSend])
		if self.testIfAlreadyInQ(next,piU): 	return 
		if self.decideMyLog(u"UpdateRPI"): self.indiLOG.log(10,u"FTP adding to update list {}".format(next) )
		self.rpiQueues[u"data"][piU].put(next)
		return
####-------------------------------------------------------------------------####
	def sshToRPI(self, piU, fileToSend="", endAction="repeatUntilFinished"):
		if time.time() - self.rpiQueues[u"lastCheck"][piU] > 100:
			self.startUpdateRPIqueues(u"restart", piSelect=piU)
		next = {u"pi":piU, u"fileToSend":fileToSend, u"endAction":endAction, u"type":u"ssh", u"tries":0, u"exeTime":time.time()}
		self.removeONErPiV(piU, u"piUpToDate", [fileToSend])
		if self.testIfAlreadyInQ(next,piU): 	return 
		if self.decideMyLog(u"UpdateRPI"): self.indiLOG.log(10,u"SSH adding to update list {}".format(next) )
		self.rpiQueues[u"data"][piU].put(next)
		return
####-------------------------------------------------------------------------####
	def resetUpdateQueue(self, piU):
		self.rpiQueues[u"reset"][piU] = True
		return
####-------------------------------------------------------------------------####
	def testIfAlreadyInQ(self, next, piU):
		currentQueue = list(self.rpiQueues[u"data"][piU].queue)
		for q in currentQueue:
			if q[u"pi"] == next[u"pi"] and q[u"fileToSend"] == next[u"fileToSend"]:
				if self.decideMyLog(u"UpdateRPI"): self.indiLOG.log(10,u"FTP NOT adding to update list already presend {}".format(next) )
				return True
		return False

####-------------------------------------------------------------------------####
	def rpiUpdateThread(self,piU):
		try:
			self.rpiQueues[u"state"][piU] = u"running"
			if self.decideMyLog(u"UpdateRPI"): self.indiLOG.log(20,u"rpiUpdateThread starting  for pi# {}".format(piU) )
			while self.rpiQueues[u"state"][piU] == u"running":
				self.rpiQueues[u"lastCheck"][piU]  = time.time()
				time.sleep(1)
				addBack =[]
				while not self.rpiQueues[u"data"][piU].empty():
					self.rpiQueues[u"lastActive"][piU]  = time.time()
					next = self.rpiQueues[u"data"][piU].get()
					self.rpiQueues[u"lastData"][piU] = unicode(next)
					##if self.decideMyLog(u"UpdateRPI"): self.indiLOG.log(20,u"reset on/off  update queue for pi#{} .. {}".format(piU, self.rpiQueues[u"reset"][piU]) )

					if self.RPI[piU][u"piOnOff"] == u"0": 		
						if self.decideMyLog(u"UpdateRPI"): self.indiLOG.log(20,u"rpiUpdateThread skipping;  Pi#: {} is OFF".format(piU) )
						self.rpiQueues[u"reset"][piU] = True
						break
					if self.decideMyLog(u"UpdateRPI"): self.indiLOG.log(20,u"rpiUpdateThread executing  {}".format(next) )
					if piU != unicode(next[u"pi"]): 			
						if self.decideMyLog(u"UpdateRPI"): self.indiLOG.log(20,u"rpiUpdateThread skipping; pi numbers wrong  {} vs {} ".format(piU, next[u"pi"]) )
						continue
					if self.RPI[piU][u"piOnOff"] == u"0": 		
						if self.decideMyLog(u"UpdateRPI"): self.indiLOG.log(20,u"rpiUpdateThread skipping;  Pi#: {} is OFF".format(piU) )
						continue
					if self.RPI[piU][u"ipNumberPi"] == "": 	
						if self.decideMyLog(u"UpdateRPI"): self.indiLOG.log(20,u"rpiUpdateThread skipping pi#:{}  ip number blank".format(piU)  )
						continue
					if piU in self.rpiQueues[u"reset"] and self.rpiQueues[u"reset"][piU]: 
						if self.decideMyLog(u"UpdateRPI"): self.indiLOG.log(20,u"rpiUpdateThread resetting queue data for pi#:{}".format(piU) )
						continue
					try:
						id = int(self.RPI[piU][u"piDevId"])
						if id != 0 and not indigo.devices[id].enabled: 
							self.rpiQueues[u"reset"][piU] = True
							if self.decideMyLog(u"OfflineRPI"): self.indiLOG.log(20,u"device {} not enabled, no sending to RPI".format(indigo.devices[id].name) )
							continue
					except Exception, e:
						if unicode(e) != u"None":
							self.indiLOG.log(40,u"Line {} has error={}".format(sys.exc_traceback.tb_lineno, e))
							self.indiLOG.log(20,u"setting update queue for pi#{} to empty".format(piU))
						self.rpiQueues[u"reset"][piU] = True

					# time for sending?
					if next[u"exeTime"] > time.time():
						addBack.append((next)) # no , wait 
						continue
					self.RPIBusy[piU] = time.time()

					if next[u"type"] == u"ftp":
						retCode, text = self.execSendFilesToPiFTP(piU, fileToSend=next[u"fileToSend"], endAction= next[u"endAction"])
					else:
						retCode, text = self.execSshToRPI(piU, fileToSend=next[u"fileToSend"], endAction= next[u"endAction"])

					if retCode ==0: # all ok?
						self.setRPIonline(piU)
						self.RPI[piU][u"lastMessage"] = time.time()
						continue

					else: # some issues
						next[u"tries"] +=1
						next[u"exeTime"]  = time.time()+5

						if 5 < next[u"tries"] and next[u"tries"] < 10: # wait a little longer
							if self.decideMyLog(u"UpdateRPI"): self.indiLOG.log(20,u"last updates were not successful wait, then try again")
							next[u"exeTime"] = time.time()+10

						elif next[u"tries"] > 9:  # wait a BIT longer before trying again
							if self.decideMyLog(u"OfflineRPI"): self.indiLOG.log(20,u"rPi update delayed due to failed updates rPI# {}".format(piU) )
							self.setRPIonline(piU, new=u"offline")
							next[u"exeTime"]  = time.time()+20
							next[u"tries"] = 0

						addBack.append(next)
				try: 	self.rpiQueues[u"data"][piU].task_done()
				except: pass
				if addBack !=[]:
					for nxt in addBack:
						self.rpiQueues[u"data"][piU].put(nxt)
				self.rpiQueues[u"reset"][piU] =False
		except Exception, e:
			if unicode(e) != u"None":
				self.indiLOG.log(40,u"Line {} has error={}".format(sys.exc_traceback.tb_lineno, e))
		self.indiLOG.log(20,u"rpi: {}  update thread stopped, state was:{}".format(piU,self.rpiQueues[u"state"][piU] ) )
		self.rpiQueues[u"state"][piU] = u"stopped - exiting thread"
		return



####-------------------------------------------------------------------------####
	def execSendFilesToPiFTP(self, piU, fileToSend=u"updateParamsFTP.exp",endAction="repeatUntilFinished"):
		ret =["",""]
		try:
			if self.decideMyLog(u"UpdateRPI"): self.indiLOG.log(20,u"enter  sendFilesToPiFTP #{}  fileToSend:".format(piU, fileToSend) )
			if fileToSend==u"updateParamsFTP.exp": self.newIgnoreMAC = 0
			self.lastUpdateSend = time.time()


			pingR = self.testPing(self.RPI[piU][u"ipNumberPiSendTo"])
			if pingR != 0:
				if self.decideMyLog(u"OfflineRPI") or self.decideMyLog(u"UpdateRPI"): self.indiLOG.log(20,u" pi server # {}  PI# {}    not online - does not answer ping - , skipping update".format(piU, self.RPI[piU][u"ipNumberPiSendTo"]) )
				self.setRPIonline(piU,new="offline")
				return 1, [u"ping offline",""]

			prompt = self.getPrompt(piU,fileToSend)

			cmd0 = u"/usr/bin/expect '" + self.pathToPlugin + fileToSend + u"'" + u" "
			cmd0+=	self.RPI[piU][u"userIdPi"] + " " + self.RPI[piU][u"passwordPi"]+u" " + prompt+u" "
			cmd0+=	self.RPI[piU][u"ipNumberPiSendTo"] + " "
			cmd0+=	piU + " '" + self.indigoPreferencesPluginDir + "' '" + self.pathToPlugin + "pi'" + " "+self.expectTimeout

			if self.decideMyLog(u"UpdateRPI"): self.indiLOG.log(20,u"updating pi server config for # {} executing\n{}".format(piU, cmd0) )
			p = subprocess.Popen(cmd0, shell=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
			ret = p.communicate()

			if fileToSend == u"upgradeOpSysSSH.exp" :
				return 0, ret

			if len(ret[1]) > 0:
				ret, ok = self.fixHostsFile(ret, piU)
				if not ok: return 0, ret
				self.indiLOG.log(20,u"return code from fix " + unicode(ret) + u" trying again to configure PI")
				p = subprocess.Popen(cmd0, shell=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
				ret = p.communicate()

			if ret[0][-600:].find(u"sftp> ") > -1:
				if self.decideMyLog(u"UpdateRPI"): self.indiLOG.log(20,u"UpdateRPI seems to have been completed for pi# {}  {}".format(piU, fileToSend) )
				return 0, [u"ok",""]
			else:
				self.sleep(2)  # try it again after 2 seconds
				p = subprocess.Popen(cmd0, shell=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
				ret = p.communicate()
				if ret[0][-600:].find(u"sftp> ") > -1:
					if self.decideMyLog(u"UpdateRPI"): self.indiLOG.log(20,u"UpdateRPI seems to have been completed for pi# {}  {}".format(piU, fileToSend) )
					return 0, [u"ok",""]
				else:
					self.indiLOG.log(20,u"setup pi response (2) message>>>> \n{}\n<<<<<<".format(ret[0].strip(u"\n")) )
					self.indiLOG.log(20,u"setup pi response (2) error>>>>>> \n{}\n<<<<<<".format(ret[1].strip(u"\n")) )
					return 1, [u"offline",""]
			return 0, ret
		except Exception, e:
			if unicode(e) != u"None":
				self.indiLOG.log(40,u"Line {} has error={}".format(sys.exc_traceback.tb_lineno, e))
		return 1, ret




####-------------------------------------------------------------------------####
	def execSshToRPI(self, piU, fileToSend="", endAction="repeatUntilFinished"):
		ret=["",""]
		try:
			if self.testPing(self.RPI[piU][u"ipNumberPi"]) != 0:
				if self.decideMyLog(u"OfflineRPI") or self.decideMyLog(u"UpdateRPI"): self.indiLOG.log(20,u" pi server # {} PI# {}  not online - does not answer ping - , skipping update".format(piU, self.RPI[piU][u"ipNumberPiSendTo"] ))
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
				if fileToSend.find(u"getiBeaconListbluetoothctSSH") >-1: 
					ff =fileToSend
					cmd = u"/usr/bin/expect '" + self.pathToPlugin + ff+u"' " + " " + self.RPI[piU][u"userIdPi"] + " " + self.RPI[piU][u"passwordPi"] + " " + prompt+  "  "+ self.RPI[piU][u"ipNumberPiSendTo"]+ " "+self.expectTimeout
					self.indiLOG.log(20,u"getting iBeacon list with bluetoothctl scan on from PI# {} .. this will take > 30 secs \ncmd:{}".format(piU, cmd) )

				elif fileToSend.find(u"getiBeaconListhcidumpSSH") >-1: 
					ff =fileToSend
					cmd = u"/usr/bin/expect '" + self.pathToPlugin + ff+u"' " + " " + self.RPI[piU][u"userIdPi"] + " " + self.RPI[piU][u"passwordPi"] + " " + prompt+  "  "+ self.RPI[piU][u"ipNumberPiSendTo"]+ " "+self.expectTimeout
					self.indiLOG.log(20,u"getting iBeacon list with bluetoothctl scan on from PI# {} .. this will take > 30 secs \ncmd:{}".format(piU, cmd) )

				elif fileToSend.find(u"getiBeaconListbluetoothctAndhcidumpSSH") >-1: 
					ff =fileToSend
					cmd = u"/usr/bin/expect '" + self.pathToPlugin + ff+u"' " + " " + self.RPI[piU][u"userIdPi"] + " " + self.RPI[piU][u"passwordPi"] + " " + prompt+  "  "+ self.RPI[piU][u"ipNumberPiSendTo"]+ " "+self.expectTimeout
					self.indiLOG.log(20,u"getting iBeacon list with bluetoothctl scan on from PI# {} .. this will take > 2x30 secs \ncmd:{}".format(piU, cmd) )

				elif fileToSend.find(u"1") >-1:
					hci="0"
					if fileToSend.find(u"1") >-1:
						hci="1"
					ff =fileToSend.replace(u"0","").replace(u"1","")
					cmd = u"/usr/bin/expect '" + self.pathToPlugin + ff+u"' " + " " + self.RPI[piU][u"userIdPi"] + " " + self.RPI[piU][u"passwordPi"] + " " + prompt+  "  "+ self.RPI[piU][u"ipNumberPiSendTo"]+ " "+self.expectTimeout+u" hci"+hci
					self.indiLOG.log(20,u"getting iBeacon list from PI# {} using hci{} .. this will take > 30 secs \ncmd:{}".format(piU, hci, cmd) )

			else:

				cmd = u"/usr/bin/expect '" + self.pathToPlugin + fileToSend+u"' " + " " + self.RPI[piU][u"userIdPi"] + " " + self.RPI[piU][u"passwordPi"] + " " + prompt+u" "+ self.RPI[piU][u"ipNumberPiSendTo"]+ " "+self.expectTimeout+ " "+batch
			if self.decideMyLog(u"UpdateRPI") : self.indiLOG.log(10,fileToSend+u" Pi# {}\n{}".format(piU, cmd) )
			if batch == u" ":
				ret = subprocess.Popen(cmd, shell=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE).communicate()
				if self.decideMyLog(u"UpdateRPI"): self.indiLOG.log(10,u"response: {}".format(ret) )
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
				self.indiLOG.log(20,u"{} Pi# {}  {}".format(fileToSend, piU, ret1) )

			if fileToSend.find(u"getStats") >-1: 
				try:
					ret1= ((ret[0].split(u"===fix==="))[-1]).replace(u"\n\n", u"\n").replace(u"\n", tag)
					self.indiLOG.log(20,u"stats from Pi# {}{}{}{}Stats end ===========".format(piU, tag, ret1, tag ) )
				except:
					self.indiLOG.log(20,u"stats from Pi# {} raw \n {} \n errors:\n{}" .format(piU, ret[0].replace(u"\n\n", u"\n"), ret[1].replace(u"\n\n", u"\n")) )

				return 0, ret

			if fileToSend.find(u"getiBeaconListbluetoothctSSH") >-1: 
				try:
					if ret[0].find(u"error")> -1:
						ret1= ret[0].replace(u"\n\n", u"\n").replace(u"\n", tag)
						self.indiLOG.log(20,u"\nibeaconList bluetoothctl form Pi# {} error,  END ====".format(piU, tag, ret1, tag) )
					else:
						ret1= u"Discovery started\n"+(ret[0].split(u"Discovery started")[-1]).replace(u"[[0;93m", u"[").replace(u"[[0;92m", u"[").replace(u"[0m", "").replace(u"\n", tag).split(u"- nohup:")[0]
						self.indiLOG.log(20,u"\nibeaconList form Pi# {} collected over 20 secs ==============:  {}{}{}bluetoothctl scan  END         ===================================".format(piU, tag, ret1, tag) )
				except:
					self.indiLOG.log(20,u"getiBeaconList from Pi# {} raw \n {} \n errors:\n{}" .format(piU, ret[0].replace(u"\n\n", u"\n"), ret[1].replace(u"\n\n", u"\n")) )

				return 0, ret

			if fileToSend.find(u"getiBeaconListbluetoothctAndhcidumpSSH") >-1: 
				try:
					if ret[0].find(u"error")> -1:
						ret1= ret[0].replace(u"\n\n", u"\n").replace(u"\n", tag)
						self.indiLOG.log(20,u"\nibeaconList bluetoothctl form Pi# {} error,  END ====".format(piU, tag, ret1, tag) )
					else:
						ret1= u"Discovery started\n"+(ret[0].split(u"hcidump --raw")[-1]).replace(u"[[0;93m", u"[").replace(u"[[0;92m", u"[").replace(u"[0m", "").replace(u"\n", tag).split(u"- nohup:")[0]
 						xx= ret[0].replace(u"\nPi#"+piU+u" - ", "")
						xx= ret[0].replace(u"Pi#"+piU+u" - ", "")
						ret1 =""
						for line in xx:
 							if line.find(u">") > 0: continue
			
						self.indiLOG.log(20,u"\nibeaconList form Pi# {} collected over 20 secs ==============:  {}{}{}bluetoothctl scan  END         ===================================".format(piU, tag, ret1, tag) )
				except:
					self.indiLOG.log(20,u"getiBeaconList from Pi# {} raw \n {} \n errors:\n{}" .format(piU, ret[0].replace(u"\n\n", u"\n"), ret[1].replace(u"\n\n", u"\n")) )

				return 0, ret

			if fileToSend.find(u"getiBeaconList") >-1: 
				try:
					if ret[0].find(u"failed: Input/output error")> -1:
						ret1= ret[0].replace(u"\n\n", u"\n").replace(u"\n", tag)
						self.indiLOG.log(20,u"\nibeaconList form Pi# {} error, try with other hci 0/1 channel {}{} {} END ====".format(piU, tag, ret1, tag) )
					else:
						ret1= ((ret[0].split(u"LE Scan ..."))[-1]).split(u"Killed")[0].replace(u"\n\n", u"\n").replace(u"\n", tag)
						self.indiLOG.log(20,u"\nibeaconList form Pi# {} collected over 20 secs ==============:  {}{}{}ibeaconList  END         ===================================".format(piU, tag, ret1, tag) )
				except:
					self.indiLOG.log(20,u"getiBeaconList from Pi# {} raw \n {} \n errors:\n{}" .format(piU, ret[0].replace(u"\n\n", u"\n"), ret[1].replace(u"\n\n", u"\n")) )

				return 0, ret

			if fileToSend.find(u"getLogFileSSH") >-1: 
				try:	
					ret1= ( ( (ret[0].split(u"tail -1000 /var/log/pibeacon.log"))[1] ).split(u"echo 'end token' >")[0] ).replace(u"\n\n", u"\n").replace(u"\n", tag)
					self.indiLOG.log(20,u"{}pibeacon logfile from Pi# {}  ==============:  {}{}{}pibeacon logfile  END    ===================================\n".format(tag, piU, tag, ret1,tag) )
				except Exception, e:
					if unicode(e) != u"None":
						self.indiLOG.log(40,u"Line {} has error={}".format(sys.exc_traceback.tb_lineno, e))
						self.indiLOG.log(20,u"pibeacon logfile from Pi# {} raw \n {} \n errors:\n{}" .format(piU, ret[0].replace(u"\n\n", u"\n"), ret[1].replace(u"\n\n", u"\n")) )

				return 0, ret

			return 0, ret

		except Exception, e:
			if unicode(e) != u"None":
				self.indiLOG.log(40,u"Line {} has error={}".format(sys.exc_traceback.tb_lineno, e))
		return 1, ret




####-------------------------------------------------------------------------####
	def getPrompt(self, piU,fileToSend):
		prompt ="assword"
		if self.RPI[piU][u"authKeyOrPassword"] == u"login:":
			if fileToSend.find(u"FTP") >-1:
				prompt ="connect"
			else: 
				prompt ="login:"

		return prompt


####-------------------------------------------------------------------------####
	def fixHostsFile(self, ret, pi):
		try:
			piU = unicode(pi)
			if self.decideMyLog(u"UpdateRPI"): self.indiLOG.log(10,u"setup pi response (1)\n" + unicode(ret))
			if ret[0].find(u".ssh/known_hosts:") > -1:
				if (subprocess.Popen(u"/usr/bin/csrutil status" , shell=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE).communicate()[0].find(u"enabled")) >-1:
					if self.decideMyLog(u"bigErr"): 
						self.indiLOG.log(40,u'ERROR can not update hosts known_hosts file,    "/usr/bin/csrutil status" shows system enabled SIP; please edit manually with \n"nano {}/.ssh/known_hosts"\n and delete line starting with {}'.format(self.MAChome, self.RPI[piU][u"ipNumberPiSendTo"]) )
						self.indiLOG.log(40,u"trying to fix from within plugin, if it happens again you need to do it manually")
					try:
						f = open(self.MAChome+u'/.ssh/known_hosts',u"r")
						lines  = f.readlines()
						f.close()
						f = open(self.MAChome+u'/.ssh/known_hosts',u"w")
						for line in lines:
							if line.find(self.RPI[piU][u"ipNumberPiSendTo"]) >-1:continue
							if len(line) < 10: continue
							f.write(line+u"\n")
						f.close()
					except Exception, e:
						self.indiLOG.log(40,u"Line {} has error={}".format(sys.exc_traceback.tb_lineno, e))

					return ["",""], False

				fix1 = ret[0].split(u"Offending RSA key in ")
				if len(fix1) > 1:
					fix2 = fix1[1].split(u"\n")[0].strip(u"\n").strip(u"\n")
					fix3 = fix2.split(u":")
					if len(fix3) > 1:
						fixcode = u"/usr/bin/perl -pi -e 's/\Q$_// if ($. == u" + fix3[1] + ");' " + fix3[0]
						self.indiLOG.log(40,u"wrong RSA key, trying to fix with: {}".format(fixcode) )
						p = subprocess.Popen(fixcode, shell=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
						ret = p.communicate()
 
		except Exception, e:
			if unicode(e) != u"None":
				self.indiLOG.log(40,u"Line {} has error={}".format(sys.exc_traceback.tb_lineno, e))
		return ret, True

####------------------rpi update queue management ----------------------------END
####------------------rpi update queue management ----------------------------END
####------------------rpi update queue management ----------------------------END



####-------------------------------------------------------------------------####
	def configureWifi(self, pi):
		return
		try:
			self.setupFilesForPi(calledFrom=u"configureWifi")
		except Exception, e:
			if unicode(e) != u"None":
				self.indiLOG.log(40,u"Line {} has error={}".format(sys.exc_traceback.tb_lineno, e))
		return

####-------------------------------------------------------------------------####
	def testPing(self, ipN):
		try:
			ss = time.time()
			ret = subprocess.call(u"/sbin/ping  -c 1 -W 40 -o " + ipN, shell=True) # send max 2 packets, wait 40 msec   if one gets back stop
			if self.decideMyLog(u"UpdateRPI"): self.indiLOG.log(10,u" sbin/ping  -c 1 -W 40 -o {} return-code: {}".format(ipN, ret) )

			#indigo.server.log(  ipN+u"-1  "+ unicode(ret) +u"  "+ unicode(time.time() - ss)  )

			if int(ret) ==0:  return 0
			self.sleep(0.1)
			ret = subprocess.call(u"/sbin/ping  -c 1 -W 400 -o " + ipN, shell=True)
			if self.decideMyLog(u"UpdateRPI"): self.indiLOG.log(10,u"/sbin/ping  -c 1 -W 400 -o {} ret-code: ".format(ipN, ret) )

			#indigo.server.log(  ipN+u"-2  "+ unicode(ret) +u"  "+ unicode(time.time() - ss)  )

			if int(ret) ==0:  return 0
			return 1
		except Exception, e:
			if unicode(e) != u"None":
				self.indiLOG.log(40,u"Line {} has error={}".format(sys.exc_traceback.tb_lineno, e))

		#indigo.server.log(  ipN+u"-3  "+ unicode(ret) +u"  "+ unicode(time.time() - ss)  )
		return 1


####-------------------------------------------------------------------------####
	def printBeaconsIgnoredButton(self, valuesDict=None, typeId=""):

		############## list of beacons in history
		#				  1234567890123456	1234567890123456789012 1234567890 123456 123456789
		#				  75:66:B5:0A:9F:DB beacon-75:66:B5:0A:9   expired		   0	  1346
		self.myLog( text = u"#	defined beacons-------------", mType="pi configuration")
		self.myLog( text = u"#  Beacon MAC        indigoName                 indigoId Status           type    txMin ignore sigDlt minSig    LastUp[s] ExpTime updDelay created   lastStatusChange",  mType=u"pi configuration")
		for status in [u"ignored", ""]:
			for beaconDeviceType in self.knownBeaconTags:
				self.printBeaconInfoLine(status, beaconDeviceType)


	def printHelp(self):
		try: 
			helpText  = u'  \n' 
			helpText += u'=============== setup HELP ======  \n' 
			helpText += u'  \n'
			helpText += u'  To START,  here the basic steps:   \n' 
			helpText += u'  1.  in CONFIG setup at minimum userID,PassWD, ipNumber of indigo server    n'
			helpText += u'  2.  Setup of physical rPi servers:    \n'
			helpText += u'      ssh pi@ipnumber      password default = pibeacon    \n'
			helpText += u'      passwd                   to change default pasword    \n'
			helpText += u'      sudo raspi-config    to set time zone, expand SD ..,   \n'
			helpText += u'         get ip number of RPI w ifconfig  \n'
			helpText += u'  3.  in menu   Initial BASIC setup of rPi servers      \n'
			helpText += u'          set ipNumber, userID, password of RPI# x (0-19)  \n'
			helpText += u'  \n'
			helpText += u'  4. Now wait until the first ibeacon and RPI devices show up in indigo  \n'
			helpText += u'    If nothing happens, do a  Send Config/Restart/PGM/Sound/...       \n'
			helpText += u'    to send all files to RPI, then  \n'
			helpText += u'    ssh to RPI and check programs that are running: ps -ef | grep .py  \n'
			helpText += u'       At minimum master.py, beaconloop.py, receiveGPIOcommands.py   \n'
			helpText += u'           should be running  \n'
			helpText += u'       if installLibs.py is running, it is updating op-sys files.   \n'
			helpText += u'           That might take several hours  \n'
			helpText += u'  5. You then want to disable accept new beacons in config  \n'
			helpText += u'     any car driving by likely has some beacons sending messages.  \n'
			helpText += u'     To add new beacons set accept new beacons to eg -60  dBm  \n'
			helpText += u'       Put your new beacon onto the rpi, wait a minute  \n'
			helpText += u'          and check the new beacon(s) created  \n'
			helpText += u'       Set accept new beacons to off in config  \n'
			helpText += u'       Then move the beacon far away and check again,   \n'
			helpText += u'          find the beacon that has the signal reduced  \n'
			helpText += u'       Then move it back to the RPI and check if signal is high again.  \n'
			helpText += u'       Then set the beacon at 1m distance and note the signal strength.   \n'
			helpText += u'         Edit the beacon and set TX power to that value(it is likely ~ -60).   \n'
			helpText += u'         That will make the distance calulation more accurate  \n'
			helpText += u'  \n'
			helpText += u'  Other remarks...  \n'
			helpText += u'  1. Some beacon types are automatically recognized by the plugin:  see section below\n'
			helpText += u'     checkout the file "knownBeaconTags.full_copy_to_use_as_example"  \n'
			helpText += u'     in the plugin prefrence directory for a full list  \n'
			helpText += u'     Using these types makes your live much easier  \n'
			helpText += u'  2. It is advisable to have at least 2 RPI that "see" each other (in bluetooth range)  \n'
			helpText += u'     that makes the overall system more stable and enables   \n'
			helpText += u'     location mapping in x,y,z coordinates  \n'
			helpText += u'     The location mapping gets much better if you have an RPI in each room  \n'
			helpText += u'  \n'
			helpText += u'=============== END setup HELP ===========  \n'
			helpText += u'  \n'
			helpText += u'  \n'

# /Library/Application Support/Perceptive Automation/Indigo 7.4/Plugins/piBeacon.indigoPlugin/Contents/Server Plugin/
			filesIn   = self.pathToPlugin.split("Server Plugin/")[0]
			helpText += u'  for changelog: check out {}changelist.txt  \n'.format(filesIn)
			helpText += u'  \n'
			helpText += u'  \n'
			f = open(filesIn+u"beaconTypes.txt","r")
			fff = f.read()
			f.close()
			helpText += u'=============== BEACONS            ===========  \n'
			helpText += fff
			helpText += u'=============== BEACONS     .. END ===========  \n'

			f = open(filesIn+u"BLE-sensorTypes.txt","r")
			fff = f.read()
			f.close()

			helpText += u'  \n'
			helpText += u'=============== BLE-Sensors        ===========  \n'
			helpText += fff
			helpText += u'=============== BLE SENSORS .. END ===========  \n'
			helpText += u'  \n'
			self.myLog( text = helpText, destination="")
			self.myLog( text = helpText, destination="standard")
		except Exception, e:
			if unicode(e) != u"None":
				self.indiLOG.log(40,u"Line {} has error={}".format(sys.exc_traceback.tb_lineno, e))


####-------------------------------------------------------------------------####
	def printConfig(self):
		try: 
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
			self.myLog( text = u"beacon indigo folder Name    {}" .format(self.iBeaconDevicesFolderName),									   	mType= u"pi configuration")
			self.myLog( text = u"accept newiBeacons           {}" .format(self.acceptNewiBeacons),									   	mType= u"pi configuration")
			self.myLog( text = u"distance Units	              {}; 1=m, 0.01=cm , 0.0254=in, 0.3=f, 0.9=y".format(self.distanceUnits), 	mType= u"pi configuration")
			self.myLog( text = "", 																									mType= u"pi configuration")
			self.myLog( text = u" ========== EXPERT parameters for each PI:----------", 												mType= u"pi configuration")
			self.myLog( text = u"port# on rPi 4 GPIO commands {}" .format(self.rPiCommandPORT),	   										mType= u"pi configuration")
			self.myLog( text = u" "															  ,	   										mType= u"pi configuration")

			self.myLog( text = u"  # R# 0/1 IP#             beacon-MAC        indigoName                 Pos X,Y,Z    indigoID UserID    Password       If-rPI-Hangs   SensorAttached",mType= u"pi configuration")
			for pi  in range(len(self.RPI)):
				try:
					piU = str(pi)
					if piU not in self.RPI: 
						self.indiLOG.log(40,u"RPI#{} has problem: , not in self.RPI".format(pi))
						continue
					if self.RPI[piU][u"piDevId"] == 0:	 continue
					try:
						dev = indigo.devices[self.RPI[piU][u"piDevId"]]
					except Exception, e:
						if unicode(e).find(u"timeout waiting") > -1:
							self.indiLOG.log(40,u"Line {} has error={}".format(sys.exc_traceback.tb_lineno, e))
							self.indiLOG.log(40,u"communication to indigo is interrupted")
							return

						self.indiLOG.log(40,u"Line {} has error={}".format(sys.exc_traceback.tb_lineno, e))
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
				except Exception, e:
					self.indiLOG.log(40,u"Line {} has error={}".format(sys.exc_traceback.tb_lineno, e))
					self.indiLOG.log(40,u"RPI#{} has problem:  disabled?".format(pi))



			self.myLog( text = "", mType="pi configuration")
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
							self.indiLOG.log(30,u" beaconId not in devices:{} ; type: {}; car name:{}".format(beaconId, bNames[nn], carName))
							continue
						beaconDev= indigo.devices[beaconId]
						propsB = beaconDev.pluginProps
						bN[nn] = (beaconDev.name)
						bF[nn] = propsB[u"fastDown"]
					homeSince = int(time.time() - self.CARS[u"carId"][dd][u"homeSince"])
					if homeSince > 9999999: homeSince = u" "
					awaySince = int(time.time() - self.CARS[u"carId"][dd][u"awaySince"])
					if awaySince > 9999999: awaySince= u" "
					homeSince = unicode(homeSince).ljust(7)
					awaySince = unicode(awaySince).ljust(7)
					out =  carName +u" "+homeSince+u" - "+awaySince
					for n in range(len(bNames)):
						out += u" " + bN[n].strip().ljust(30) 
					self.myLog( text = out, mType= u"pi configuration")
					out =  "         ....FastDown".ljust(30)+ " ".ljust(18)
					for n in range(len(bNames)):
						if bF[n] !=" ":
							out += u" " + (bF[n]+u"[sec]").strip().ljust(30)
						else:
							out += u" " + (u" ").ljust(30)

					self.myLog( text = out, mType= u"pi configuration")
				self.myLog( text = "", mType= u"pi configuration")
				"""
configuration         - ==========  defined beacons ==============
  08:31:46 pi configuration         -#  Beacon MAC        indigoName                 indigoId Status enabled               type txMin ignore fastDw sigDlt min on/off battery UUIDlastUpdate/level         LastUp[s] ExpTime updDelay lastStatusChange    created 
  08:31:46 pi configuration         -1  24:DA:11:27:E5:D4 b-iHere_black-C          1940213429 up       True         Nonda_iHere   -55      0      0    999 -999/-999                                              45     120        0 2019-01-09 23:58:14 2020-09-14 08:06:47
  08:31:46 pi configuration         -6  00:EA:23:11:2B:E4 b-xy-Mazda -red-1-2        60052985 up       True                XY_1   -59      0      0    999 -999/-999random127/100 -09-05 09:20:18,l=0             45      90        0 2017-09-07 23:44:36 2020-09-14 08:07:49
				"""
			if True:
				self.myLog( text = u" ==========  defined beacons ==============", mType= u"pi configuration")
				self.myLog( text = u"#  Beacon MAC        indigoName                 indigoId Status enabled               type txMin ignore fastDw sigDlt min-on/off batteryUUID lastUpdate/level         LastUp[s] ExpTime updDelay lastStatusChange    created ",
						   mType= u"pi configuration")
				for status in [u"up", u"down", u"expired"]:
					for beaconDeviceType in self.knownBeaconTags:
						self.printBeaconInfoLine(status, beaconDeviceType)

				self.myLog( text = "", mType= u"pi configuration")

			if True:
				self.myLog( text = u"update-thread status", mType= u"pi configuration")
				self.myLog( text = u"pi# state       lastCheck lastActive   lastData", mType= u"pi configuration")
				for ii in range(_GlobalConst_numberOfRPI ):
					piU = unicode(ii)
					self.myLog( text = u"{:3s} {:10s} {:10.1f} {:10.1f}  {}".format( piU, self.rpiQueues[u"state"][piU], time.time()-self.rpiQueues[u"lastCheck"][piU], time.time()-self.rpiQueues[u"lastActive"][piU], self.rpiQueues[u"lastData"][piU][:99] ),  mType= u"pi configuration")
				self.myLog( text = "", mType= u"pi configuration")

		except Exception, e:
			if unicode(e) != u"None":
				self.indiLOG.log(40,u"Line {} has error={}".format(sys.exc_traceback.tb_lineno, e))


####-------------------------------------------------------------------------####
	def printGroups(self):
		############## list groups with members
		try:
			indigo.server.log("printGroups  groupListUsedNames:{}   \ngroupStatusList{}:".format(self.groupListUsedNames, self.groupStatusList))

			self.myLog( text = "", mType= u"pi configuration")
			self.myLog( text = u"========== beacon groups    ================", mType= u"pi configuration")
			self.myLog( text = u"GroupName-----             members // counts ",mType= u"pi configuration")

			groupMemberNames = {}
			for group in _GlobalConst_groupList:
				groupMemberNames[group] = ""

 			for dev	in indigo.devices.iter(self.pluginId):
				if "groupMember" not in dev.states:  continue
				if dev.states[u"groupMember"] == "": continue
				indigo.server.log(u"printGroups   dev:{}  groupMember:{}".format(dev.name, dev.states[u"groupMember"]))

				for group in self.groupListUsedNames:
					if self.groupListUsedNames[group] !="" and  self.groupListUsedNames[group] in dev.states[u"groupMember"]:
						groupMemberNames[group] += dev.name +u"; "
					indigo.server.log(u"printGroups   group:{}  groupNameUsedForVar:{}  groupMemberNames:{}".format(group, self.groupListUsedNames[group], groupMemberNames[group]))

			for nn in range(len(_GlobalConst_groupList)):
				group = _GlobalConst_groupList[nn]
				groupNameUsedForVar = self.groupListUsedNames[group]
				if groupNameUsedForVar == "" and groupMemberNames[group] !="":
					groupNameUsedForVar = "please edit devs, set member"
				self.myLog( text = u"{}/{:20s}:{}" .format(group, groupNameUsedForVar, groupMemberNames[group]),mType= u"pi configuration")
				out=u"                           "
				out+=u"nHome: {};".format(self.groupStatusList[group][u"nHome"])
				out+=u" oneHome: {};".format(self.groupStatusList[group][u"oneHome"])
				out+=u" allHome: {};".format(self.groupStatusList[group][u"allHome"])
				out+=u"    nAway: {};".format(self.groupStatusList[group][u"nAway"])
				out+=u" oneAway: {};".format(self.groupStatusList[group][u"oneAway"])
				out+=u" allAway: {};".format(self.groupStatusList[group][u"allAway"])
				out+=u"    memberIDs: "
				for member in self.groupStatusList[group][u"members"]:
					out+= member+u"; "
				self.myLog( text = out,mType=u"pi configuration")
			self.myLog( text = "", mType= u"pi configuration")


			self.myLog( text = u" ==========  Parameters END ================", mType=  u"pi configuration")

		except Exception, e:
			if unicode(e) != u"None":
				self.indiLOG.log(40,u"Line {} has error={}".format(sys.exc_traceback.tb_lineno, e))

		return 

####-------------------------------------------------------------------------####
	def resetTcpipSocketStatsCALLBACK(self, valuesDict=None, typeId=""):
		self.dataStats={u"startTime":time.time(),"data":{}}


####-------------------------------------------------------------------------####
	def printTCPIPstats(self, all="yes"):

		############## tcpip stats 
		if self.socketServer is not None or True:
			if all == u"yes":
					startDate= time.strftime(_defaultDateStampFormat,time.localtime(self.dataStats[u"startTime"]))
					self.myLog( text = "", mType= u"pi TCPIP socket")
					self.myLog( text = u"Stats for RPI-->INDIGO data transfers. Tracking started {}. Report TX errors if time between errors is <{:.0f} Min".format(startDate, self.maxSocksErrorTime/60), mType=	u"pi TCPIP socket")
			self.myLog( text = u"IP              name          type      first               last                    #MSGs       #bytes bytes/MSG  maxBytes  bytes/min   MSGs/min", mType= u"pi TCPIP socket")

			### self.dataStats[u"data"][IPN][name][type] = {u"firstTime":time.time(),"lastTime":0,"count":0,"bytes":0}

			secMeasured	  = max(1., (time.time() - self.dataStats[u"startTime"]))
			minMeasured	  = secMeasured/60.
			totBytes = 0.0
			totMsg	 = 0.0
			maxBytes = 0
			for IPN in sorted(self.dataStats[u"data"].keys()):
				if all == u"yes" or all==IPN:
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

							self.myLog( text = u"{} {} {} {} {} {} {} {} {}  {}  {}".format(IPN.ljust(15), name.ljust(12), xType.ljust(10), dtFT, dtLT, count, bytesT, bytesPerMsg, maxByt, bytesPerMin, msgsPerMin),mType=" ")
			if all == u"yes" and totMsg >0:
				bytesPerMsg	  = unicode(int(totBytes/totMsg)).rjust(9)
				bytesPerMin	  = (u"%9.1f"% (totBytes/minMeasured)  ).rjust(9)
				msgsPerMin	  = (u"%9.2f"% (totMsg/minMeasured)	   ).rjust(9)
				maxBytes	  =	 unicode(maxBytes).rjust(9)
				self.myLog( text = u"total                                                                          {:10d}{:13d} {} {}  {}  {}".format(int(totMsg), int(totBytes), bytesPerMsg, maxBytes, bytesPerMin, msgsPerMin ),mType=" ")
				self.myLog( text = u" ===  Stats for RPI --> INDIGO data transfers ==  END total time measured: {:.0f} {} ; min measured: {:.0f}".format( int(time.strftime(u"%d", time.gmtime(secMeasured)))-1, time.strftime(u"%H:%M:%S", time.gmtime(secMeasured)), minMeasured ), mType=	 u"pi TCPIP socket")
		return

####-------------------------------------------------------------------------####
	def printUpdateStats(self,):
		if len(self.dataStats[u"updates"]) ==0: return 
		nSecs = max(1,(time.time()-	 self.dataStats[u"updates"][u"startTime"]))
		nMin  = nSecs/60.
		startDate= time.strftime(_defaultDateStampFormat,time.localtime(self.dataStats[u"updates"][u"startTime"]))
		self.myLog( text = "",mType=" " )
		self.myLog( text = u"===    measuring started at: {}".format(startDate), mType="indigo update stats " )
		self.myLog( text = u"updates: {:10d};   updates/sec: {:10.2f};   updates/minute: {:10.2f}".format(self.dataStats[u"updates"][u"devs"], self.dataStats[u"updates"][u"devs"] /nSecs, self.dataStats[u"updates"][u"devs"]  /nMin), mType=  u"    device ")
		out = u"(#states #updates #updates/min) "
		for ii in range(1,10):
			out+= u"({:1d} {:1d} {:3.1f}) ".format(ii, self.dataStats[u"updates"][u"nstates"][ii], self.dataStats[u"updates"][u"nstates"][ii]/nMin) 
		out+= u"({:1d} {:1d} {:3.1f})".format(10, self.dataStats[u"updates"][u"nstates"][10], self.dataStats[u"updates"][u"nstates"][10]/nMin) 
		self.myLog( text = u"updates: {}".format(out), mType=  u"    #states")
		self.myLog( text = u"===	total time measured: {}".format( time.strftime(u"%H:%M:%S", time.gmtime(nSecs)) ), mType= u"indigo update stats" )
		return 


####-------------------------------------------------------------------------####
	def printBeaconInfoLine(self, status, xType):

		try:
			cc = 0
			for beacon in self.beacons:
				if self.beacons[beacon][u"typeOfBeacon"] != xType: continue
				if self.beacons[beacon][u"status"] 		 != status: continue
				batteryLevelLastUpdate = ""
				batteryLevelUUID = ""
				try:
					dev = indigo.devices[self.beacons[beacon][u"indigoId"]]
					name = dev.name
					props = dev.pluginProps
					if u"minSignalOn" not in props: continue # old device
					lastStatusChange = dev.states[u"lastStatusChange"]
					if u"batteryLevelUUID" in props and props[u"batteryLevelUUID"].find(u"batteryLevel") >-1:
						batteryLevelUUID = props[u"batteryLevelUUID"].replace(u"-batteryLevel-int-bits=","").replace(u"2A19-","").replace(u"-norm=",u"/").replace(u"randomON",u"random")
						if u"batteryLevelLastUpdate" in dev.states: 
							batteryLevelLastUpdate = dev.states[u"batteryLevelLastUpdate"][4:]
							if len(batteryLevelLastUpdate) < 10: batteryLevelLastUpdate = u"01-01 00:00:00"
							batteryLevelLastUpdate += u",l="+str(dev.states[u"batteryLevel"])
							batteryLevelLastUpdate = batteryLevelLastUpdate
				except Exception, e:
					if unicode(e).find(u"timeout waiting") > -1:
						self.indiLOG.log(40,u"Line {} has error={}".format(sys.exc_traceback.tb_lineno, e))
						self.indiLOG.log(40,u"communication to indigo is interrupted")
						return
					name = u" "
					lastStatusChange = u" "
				if len(batteryLevelUUID) != 14: batteryLevelUUID = batteryLevelUUID.ljust(14)
				if len(batteryLevelLastUpdate) !=21: batteryLevelLastUpdate = batteryLevelLastUpdate.ljust(21)

				cc += 1
				if len(name) > 22: name = name[:21] + ".."
				line = unicode(cc).ljust(2) + " " + beacon + " " + name.ljust(24) + " " +  unicode(self.beacons[beacon][u"indigoId"]).rjust(10) + " "+\
					   self.beacons[beacon][u"status"].ljust(8) +\
					   unicode(dev.enabled).rjust(5) + \
					   self.beacons[beacon][u"typeOfBeacon"].rjust(20)+\
					   unicode(self.beacons[beacon][u"beaconTxPower"]).rjust(6) + " " + \
					   unicode(self.beacons[beacon][u"ignore"]).rjust(6) + " " + \
					   unicode(props[u"fastDown"]).rjust(6) + " " + \
					   unicode(props[u"signalDelta"]).rjust(6) + " " + \
					   unicode(props[u"minSignalOn"]).rjust(4) +u"/"+unicode(props[u"minSignalOff"]).rjust(4) + \
					   batteryLevelUUID +\
					   batteryLevelLastUpdate +\
					   unicode(min(999999999,int(time.time() - self.beacons[beacon][u"lastUp"])      ) ).rjust(13) + " " + \
					   unicode(min(999999,   int(self.beacons[beacon][u"expirationTime"])            ) ).rjust(7)  + " " + \
					   unicode(min(9999999,  int(self.beacons[beacon][u"updateSignalValuesSeconds"]) ) ).rjust(8)  + " " + \
					   unicode(self.beacons[beacon][u"created"]).ljust(19) +u" "+\
					   lastStatusChange.ljust(19)
				self.myLog( text = line, mType= u"pi configuration")

			if status == u"ignored":
				for beacon in self.beacons:
					if self.beacons[beacon][u"typeOfBeacon"] != type: continue
					if self.beacons[beacon][u"status"] != status: continue
					if self.beacons[beacon][u"ignore"] == 1:
						name = u" "
						cc += 1
						line = unicode(cc).ljust(2) + " " + beacon + " " + name.ljust(24) + " " +u" ".ljust(10) + " "+ \
							   self.beacons[beacon][u"status"].ljust(8)  + \
							   unicode(dev.enabled).rjust(5) + \
							   self.beacons[beacon][u"typeOfBeacon"].rjust(20)  + \
							   " ".rjust(6) + " " + \
							   " ".rjust(6) + " " + \
							   " ".rjust(6) + " " + \
							   " ".rjust(6) + " " + \
							   unicode(u"-").rjust(23) +\
							   unicode(min(999999999,int(time.time() - self.beacons[beacon][u"lastUp"]))).rjust(13) + " " + \
							   unicode(min(999999,int(self.beacons[beacon][u"expirationTime"]))).rjust(7) + " " + \
							   unicode(min(9999999,int(self.beacons[beacon][u"updateSignalValuesSeconds"]))).rjust(8) + " " + \
							   unicode(self.beacons[beacon][u"created"]).ljust(19)
						self.myLog( text = line, mType=	 u"pi configuration")
				for beacon in self.beacons:
					if self.beacons[beacon][u"typeOfBeacon"] != type: continue
					if self.beacons[beacon][u"status"] != status:	  continue
					if self.beacons[beacon][u"ignore"] == 2:
						name = u" "
						cc += 1
						line = unicode(cc).ljust(2) + " " + beacon + " " + name.ljust(24) + " " +u" ".ljust(10) + " "+ \
							   self.beacons[beacon][u"status"].ljust(8) + \
							   "     "  + \
							   self.beacons[beacon][u"typeOfBeacon"].rjust(10) + " " + \
							   unicode(self.beacons[beacon][u"beaconTxPower"]).rjust(6)  + \
							   " ".rjust(6) + " " + \
							   " ".rjust(6) + " " + \
							   " ".rjust(6) + " " + \
							   unicode(u"-").rjust(23) +\
							   unicode(min(999999999,int(time.time() - self.beacons[beacon][u"lastUp"]))).rjust(12) + " " + \
							   unicode(min(999999,int(self.beacons[beacon][u"expirationTime"]))).rjust(7) + " " + \
							   unicode(min(9999999,int(self.beacons[beacon][u"updateSignalValuesSeconds"]))).rjust(8) + " " + \
							   unicode(self.beacons[beacon][u"created"]).ljust(19)
						self.myLog( text = line, mType= u"pi configuration")


		except Exception, e:
			if	unicode(e).find(u"UnexpectedNullErrorxxxx") >-1: return newStates
			self.indiLOG.log(40,u"Line {} has error={}".format(sys.exc_traceback.tb_lineno, e))



####-------------------------------------------------------------------------####
	def updateRejectLists(self):
		if u"UpdateRPI" in self.debugLevel: deb = u"1"
		else: deb =""
		cmd = self.pythonPath + u" '" + self.pathToPlugin + u"updateRejects.py' "+ deb +u" & "
		if self.doRejects:	subprocess.call(cmd, shell=True)
		else:				subprocess.call(u"rm '"+ self.indigoPreferencesPluginDir + "rejected/rejects*'  > /dev/null 2>&1 " , shell=True)





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
		elif u"note" in dev.states and dev.states[u"note"].find(u"Pi") ==0:
			pi= dev.states[u"note"].split(u"-")[1]
			self.RPI[piU][u"lastMessage"]=time.time()
		elif dev.deviceTypeId =="BLEconnect":
			self.addToStatesUpdateDict(dev.id,u"lastUp",datetime.datetime.now().strftime(_defaultDateStampFormat))

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


	def addToStatesUpdateDict(self,devId, key, value, newStates="",decimalPlaces="",uiValue="", force=False):
		devId=unicode(devId)
		try:
			try:

				for ii in range(10):
					if self.executeUpdateStatesDictActive == "":
						break
					self.sleep(0.05)
				self.executeUpdateStatesDictActive = devId+u"-add"

				if devId not in self.updateStatesDict: 
					self.updateStatesDict[devId] = {}

				if key in self.updateStatesDict[devId]:
					if value != self.updateStatesDict[devId][key][u"value"]:
						self.updateStatesDict[devId][key] = {}
						if newStates != "":
							newStates[key] = {}

				self.updateStatesDict[devId][key] = {u"value":value,u"decimalPlaces":decimalPlaces,u"force":force,u"uiValue":uiValue}

				if newStates != "": newStates[key] = value

			except Exception, e:
				if unicode(e).find(u"UnexpectedNullErrorxxxx") == -1: 
					if unicode(e).find(str(devId)) == -1 or self.decideMyLog(u"Special"):
						self.indiLOG.log(30,u"Line {} has error={}".format(sys.exc_traceback.tb_lineno, e)   )
						self.indiLOG.log(30,u"addToStatesUpdateDict: this happens when 2 update processes overlap. should not be a probelm if it happens not too frequently")
						self.indiLOG.log(30,u"devId:{};  key:{}; value:{}; newStates:{};".format(devId, key, value, newStates))



		except Exception, e:
			if	unicode(e).find(u"UnexpectedNullErrorxxxx") >-1: return newStates
			self.indiLOG.log(40,u"Line {} has error={}".format(sys.exc_traceback.tb_lineno, e))
		self.executeUpdateStatesDictActive = ""
		return newStates

####-------------------------------------------------------------------------####
	def executeUpdateStatesDict(self,onlyDevID="0", calledFrom=""):
		try:
			if len(self.updateStatesDict) == 0: return
			#if "1929700622" in self.updateStatesDict: self.indiLOG.log(10,u"executeUpdateStatesList calledfrom: "+calledFrom +u"; onlyDevID: " +onlyDevID +u"; updateStatesList: " +unicode(self.updateStatesDict))
			onlyDevID = unicode(onlyDevID)

			for ii in range(10):
				if	self.executeUpdateStatesDictActive == "":
					break
				self.sleep(0.05)

			self.executeUpdateStatesDictActive = onlyDevID+u"-exe"


			local = {}
			#		 
			if onlyDevID == u"0":
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
						value = local[devId][key][u"value"]
						if key not in dev.states and key != u"lastSensorChange":
							self.indiLOG.log(20,u"executeUpdateStatesDict: key: {}  not in states for dev:{}".format(key, dev.name) )
						elif key in dev.states:
							upd = False
							if local[devId][key][u"decimalPlaces"] != "": # decimal places present?
								try: 
									if round(value,local[devId][key][u"decimalPlaces"]) !=	 round(dev.states[key],local[devId][key][u"decimalPlaces"]):
										upd=True
								except: 
										upd=True
							else: 
								if unicode(value) != unicode(dev.states[key]):
										upd=True
							if local[devId][key][u"force"]: 
										upd=True
							if upd:
								nKeys +=1
								if devId not in changedOnly: changedOnly[devId]={}
								changedOnly[devId][key] = {u"value":local[devId][key][u"value"], u"decimalPlaces":local[devId][key][u"decimalPlaces"], u"uiValue":local[devId][key][u"uiValue"]}
								if u"lastSensorChange" in dev.states and "lastSensorChange" not in changedOnly[devId]:
									nKeys +=1
									changedOnly[devId][u"lastSensorChange"] = {u"value":dateString,u"decimalPlaces":"",u"uiValue":""}

					##if dev.name =="b-radius_3": self.indiLOG.log(10,	u"changedOnly "+unicode(changedOnly))
					if devId in changedOnly and len(changedOnly[devId]) >0:
						chList=[]
						for key in changedOnly[devId]:
							if key ==u"status":	 
								self.statusChanged = max(1,self.statusChanged)
								value =changedOnly[devId][key][u"value"]
								if u"lastStatusChange" in dev.states and u"lastStatusChange" not in changedOnly[devId]:
									try:
										st	= unicode(value).lower() 
										if st in [u"up",u"down",u"expired",u"on",u"off",u"1",u"0"]:
											props =dev.pluginProps
											if	self.enableBroadCastEvents == u"all" or	(u"enableBroadCastEvents" in props and props[u"enableBroadCastEvents"] == u"1" ):
												msg = {u"action":u"event", u"id":unicode(dev.id), u"name":dev.name, u"state":u"status", u"valueForON":u"up", u"newValue":st}
												if self.decideMyLog(u"BC"): self.indiLOG.log(10,u"executeUpdateStatesDict msg added :" + unicode(msg))
												self.sendBroadCastEventsList.append(msg)
											if dateString != dev.states[u"lastStatusChange"]:
												chList.append({u"key": u"lastStatusChange", u"value":dateString})
									except: pass

								if dev.deviceTypeId ==u"beacon" or dev.deviceTypeId.find(u"rPI") > -1 or dev.deviceTypeId == u"BLEconnect": 
									chList.append({u"key":u"displayStatus",u"value":self.padDisplay(value)+dateString[5:] })
									if	 value == u"up":
										chList.append({u"key":u"onOffState",u"value":True, u"uiValue":self.padDisplay(value)+dateString[5:] })
										dev.updateStateImageOnServer(indigo.kStateImageSel.SensorOn)
									elif value == u"down":
										chList.append({u"key":u"onOffState",u"value":False, u"uiValue":self.padDisplay(value)+dateString[5:] })
										dev.updateStateImageOnServer(indigo.kStateImageSel.SensorOff)
									else:
										chList.append({u"key":u"onOffState",u"value":False, u"uiValue":self.padDisplay(value)+dateString[5:] })
										dev.updateStateImageOnServer(indigo.kStateImageSel.SensorTripped)

								if u"lastSensorChange"  in dev.states and (key != u"lastSensorChange" or ( key == u"lastSensorChange" and nKeys >0)): 
									chList.append({u"key":u"lastSensorChange",u"value":dateString})

							if changedOnly[devId][key][u"uiValue"] != "":
								if changedOnly[devId][key][u"decimalPlaces"] != "" and key in dev.states:
									chList.append({u"key":key,u"value":changedOnly[devId][key][u"value"], u"decimalPlaces":changedOnly[devId][key][u"decimalPlaces"],u"uiValue":changedOnly[devId][key][u"uiValue"]})
									#indigo.server.log(dev.name+u"  into changed1 "+unicode(chList))
								else:
									chList.append({u"key":key,"value":changedOnly[devId][key][u"value"],"uiValue":changedOnly[devId][key][u"uiValue"]})
									#indigo.server.log(dev.name+u"  into changed "+unicode(chList))
							else:
								if changedOnly[devId][key][u"decimalPlaces"] != "" and key in dev.states:
									chList.append({u"key":key,"value":changedOnly[devId][key][u"value"], u"decimalPlaces":changedOnly[devId][key][u"decimalPlaces"]})
								else:
									chList.append({u"key":key,"value":changedOnly[devId][key][u"value"]})
							if dev.deviceTypeId ==u"beacon": 
								if key ==u"status": 
									trigStatus			 = dev.name
									devnamechangedStat	 = dev.name+ u"     "+key+ u"    old="+unicode(dev.states[key])+ u"     new="+unicode(changedOnly[devId][key][u"value"])
								if key ==u"closestRPI": 
									trigRPIchanged		 = dev.name
									devnamechangedRPI	 = dev.name+ u"     "+key+ u"    old="+unicode(dev.states[key])+ u"     new="+unicode(changedOnly[devId][key][u"value"]) 

							if False and dev.id == 110169124:
								self.indiLOG.log(20,u"{} key:{}, val:{}; chList:{}".format(dev.address, key, value, chList))
								
						##if dev.name =="b-radius_3": self.indiLOG.log(10,	u"chList "+unicode(chList))

						self.execUpdateStatesList(dev,chList)

				if trigStatus !="":
					try:
						indigo.variable.updateValue(self.ibeaconNameDefault+u"With_Status_Change",trigStatus)
					except Exception, e:
							self.indiLOG.log(40,u"status changed: {}".format(devnamechangedStat))
							self.indiLOG.log(40,u"Line {} has error={}".format(sys.exc_traceback.tb_lineno, e)   + u" trying again")
							time.sleep(0.5)
							indigo.variable.updateValue(self.ibeaconNameDefault+u"With_Status_Change",trigStatus)
							self.indiLOG.log(40,u"worked 2. time")
					self.triggerEvent(u"someStatusHasChanged")

				if trigRPIchanged !="":
					try:
						indigo.variable.updateValue(self.ibeaconNameDefault+u"With_ClosestRPI_Change",trigRPIchanged)
					except Exception, e:
							self.indiLOG.log(40,u"RPI   changed: {}".format(devnamechangedRPI))
							self.indiLOG.log(40,u"Line {} has error={}".format(sys.exc_traceback.tb_lineno, e)   + u" trying again")
							time.sleep(0.5)
							indigo.variable.updateValue(self.ibeaconNameDefault+u"With_ClosestRPI_Change",trigRPIchanged)
							self.indiLOG.log(40,u"worked 2. time")
					self.triggerEvent(u"someClosestrPiHasChanged")

		except Exception, e:
			if	unicode(e).find(u"UnexpectedNullErrorxxxx") ==-1: 
				self.indiLOG.log(40,u"Line {} has error={}".format(sys.exc_traceback.tb_lineno, e))
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
			if unicode(e) != u"None":
				self.indiLOG.log(40,u"Line {} has error={}".format(sys.exc_traceback.tb_lineno, e))
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
			if unicode(e) != u"None":
				self.indiLOG.log(40,u"Line {} has error={}".format(sys.exc_traceback.tb_lineno, e))
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
				vText= u"{:.1f}".format((float(var)-32.)*5./9.)
			except Exception, e:
				self.indiLOG.log(40,u"Line {} has error={}".format(sys.exc_traceback.tb_lineno, e))
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
			if unicode(e) != u"None":
				self.indiLOG.log(40,u"Line {} has error={}".format(sys.exc_traceback.tb_lineno, e))
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
				vText= u"{:.1f}".format((float(var)*9./5.) + 32)
			except Exception, e:
				self.indiLOG.log(40,u"Line {} has error={}".format(sys.exc_traceback.tb_lineno, e))
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
			if unicode(e) != u"None":
				self.indiLOG.log(40,u"Line {} has error={}".format(sys.exc_traceback.tb_lineno, e))
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
				self.indiLOG.log(40,u"Line {} has error={}".format(sys.exc_traceback.tb_lineno, e))
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
				self.indiLOG.log(40,u"Line {} has error={}".format(sys.exc_traceback.tb_lineno, e))
				return textIn, False
		except Exception, e:
			if unicode(e) != u"None":
				self.indiLOG.log(40,u"Line {} has error={}".format(sys.exc_traceback.tb_lineno, e))
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
			if unicode(e) != u"None":
				self.indiLOG.log(40,u"Line {} has error={}".format(sys.exc_traceback.tb_lineno, e))
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
			if unicode(e) != u"None":
				self.indiLOG.log(40,u"Line {} has error={}".format(sys.exc_traceback.tb_lineno, e))
		return textIn, False



####-----------------  calc # of blanks to be added to state column to make things look better aligned. ---------
	def padDisplay(self,status):
		if	 status == u"up":		return status.ljust(11)
		elif status == u"expired":	return status.ljust(8)
		elif status == u"down":		return status.ljust(9)
		elif status == u"changed":	return status.ljust(8)
		elif status == u"double":	return status.ljust(8)
		elif status == u"ignored":	return status.ljust(8)
		else:						return status.ljust(10)



####-----------------	 ---------
	def completePath(self,inPath):
		if len(inPath) == 0: return ""
		if inPath == u" ":	 return ""
		if inPath[-1] !="/": inPath +="/"
		return inPath

########################################
########################################
####----checkPluginPath----
########################################
########################################
####------ --------
	def checkPluginPath(self, pluginName, pathToPlugin):

		if pathToPlugin.find(u"/" + self.pluginName + ".indigoPlugin/") == -1:
			self.indiLOG.log(50,u"--------------------------------------------------------------------------------------------------------------")
			self.indiLOG.log(50,u"The pluginName is not correct, please reinstall or rename")
			self.indiLOG.log(50,u"It should be   /Libray/....../Plugins/" + pluginName + ".indigoPlugin")
			p = max(0, pathToPlugin.find(u"/Contents/Server"))
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
		indigo.server.log(u"creating plugin prefs directory ")
		os.mkdir(toPath)
		if not os.path.isdir(toPath): 	
			self.indiLOG.log(50,"| preference directory can not be created. stopping plugin:  "+ toPath)
			self.indiLOG.log(50,u"--------------------------------------------------------------------------------------------------------------")
			self.sleep(100)
			return False
		indigo.server.log(u"| preference directory created;  all config.. files will be here: "+ toPath)
			
		if not os.path.isdir(fromPath): 
			indigo.server.log(u"--------------------------------------------------------------------------------------------------------------")
			return True
		cmd = u"cp -R '"+ fromPath+u"'  '"+ toPath+u"'"
		subprocess.call(cmd, shell=True )
		self.sleep(1)
		indigo.server.log(u"| plugin files moved:  "+ cmd)
		indigo.server.log(u"| please delete old files")
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
		if   self.logFileActive ==u"standard":	self.logFile = ""
		elif self.logFileActive ==u"indigo":	self.logFile = self.indigoPath.split(u"Plugins/")[0]+u"Logs/"+self.pluginId+u"/plugin.log"
		else:									self.logFile = self.indigoPreferencesPluginDir +u"plugin.log"
		self.myLog( text=u"myLogSet setting parameters -- logFileActive= {}; logFile= {};  debug plugin:{}   RPI#:{}".format(self.logFileActive, self.logFile, self.debugLevel, self.debugRPI) , destination=u"standard")



####-----------------  check logfile sizes ---------
	def checkLogFiles(self):
		return
		try:
			self.lastCheckLogfile = time.time()
			if self.logFileActive ==u"standard": return 
			
			fn = self.logFile.split(u".log")[0]
			if os.path.isfile(fn + ".log"):
				fs = os.path.getsize(fn + ".log")
				if fs > self.maxLogFileSize:  
					if os.path.isfile(fn + "-2.log"):
						os.remove(fn + "-2.log")
					if os.path.isfile(fn + "-1.log"):
						os.rename(fn + ".log", fn + "-2.log")
						os.remove(fn + "-1.log")
					os.rename(fn + ".log", fn + "-1.log")
					indigo.server.log(u" reset logfile due to size > {:.1f} [MB]".format(self.maxLogFileSize/1024./1024.) )
		except	Exception, e:
				self.indiLOG.log(50, u"checkLogFiles Line {} has error={}".format(sys.exc_traceback.tb_lineno, e))
			
			
####-----------------	 ---------
	def decideMyLog(self, msgLevel):
		try:
			if msgLevel	 == u"all" or u"all" in self.debugLevel:	 return True
			if msgLevel	 == ""	  and u"all" not in self.debugLevel: return False
			if msgLevel in self.debugLevel:							 return True
			return False
		except	Exception, e:
			if unicode(e) != u"None":
				indigo.server.log( u"decideMyLog Line {} has error={}".format(sys.exc_traceback.tb_lineno, e))
		return False

####-----------------  print to logfile or indigo log  ---------
	def myLog(self,	 text="", mType="", errorType="", showDate=True, destination=""):
		   

		try:
			if	self.logFileActive == u"standard" or destination.find(u"standard") >-1:
				if errorType == u"smallErr":
					self.indiLOG.error(u"------------------------------------------------------------------------------")
					self.indiLOG.error(text)
					self.indiLOG.error(u"------------------------------------------------------------------------------")

				elif errorType == u"bigErr":
					self.indiLOG.error(u"==================================================================================")
					self.indiLOG.error(text)
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
				if mType == "":
					f.write((ts+u" " +u" ".ljust(25)  +u"-" + text + u"\n").encode(u"utf8"))
					#indigo.server.log((ts+u" " +u" ".ljust(25)  +u"-" + text + u"\n"))
				else:
					f.write((ts+u" " +mType.ljust(25) +u"-" + text + u"\n").encode(u"utf8"))
					#indigo.server.log((ts+u" " +mType.ljust(25) +u"-" + text + u"\n"))
				f.close()
				return


		except	Exception, e:
			if unicode(e) != u"None":
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
			if self.RPI[piU][u"piOnOff"] == u"0": continue#OKconvert
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
		if len(macx) != 6 : # len(mac.split(u"D0:D2:B0:88:7B:76")): 
			return False

		for xx in macx:
			if len(xx) !=2:
				return False

			try: 	int(xx,16)
			except: return False

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
					self.indiLOG.log(30,u"TCPIP socket error rate high for {}/{} ; previous:{}".format(IPN, name, dtLT) )
					self.printTCPIPstats(all=IPN)
				self.saveTcpipSocketStats()
			elif u"Socket" in self.debugLevel:
					pass


		except Exception, e:
			if unicode(e) != u"None":
				self.indiLOG.log(40,u"Line {} has error={}".format(sys.exc_traceback.tb_lineno, e))
		return 


####-------------------------------------------------------------------------####
	def startTcpipListening(self, myIpNumber, indigoInputPORT):
			socketServer = None
			stackReady	 = False
			self.indiLOG.log(20,u" ..   starting tcpip socket listener, for RPI data, might take some time, using: ip#={} ;  port#= {}".format(myIpNumber, indigoInputPORT) )
			tcpStart = time.time()
			lsofCMD	 =u"/usr/sbin/lsof -i tcp:{}".format(indigoInputPORT)
			ret = subprocess.Popen(lsofCMD, shell=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE).communicate()
			if self.decideMyLog(u"StartSocket"): self.indiLOG.log(10,u" ..   startTcpipListening lsof output:{}".format(ret) )
			self.killHangingProcess(ret)
			for ii in range(90):  #	 gives port busy for ~ 60 secs if restart, new start it is fine, error message continues even if it works -- indicator =ok: if lsof gives port number  
				try:
					socketServer = ThreadedTCPServer((myIpNumber,int(indigoInputPORT)), ThreadedTCPRequestHandler)
					if self.decideMyLog(u"StartSocket"): self.indiLOG.log(10,u" ..   startTcpipListening try#: {:d} time elapsed: {:4.1f} secs; setting re-use = 1; timout = 5 ".format(ii, time.time()-tcpStart) )
					socketServer.socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
					#socketServer.socket.setsockopt(socket.SOL_SOCKET, socket.timeout, 5 )
					socketServer.socket.settimeout( 5 )
				except Exception, e:
					if self.decideMyLog(u"StartSocket"): self.indiLOG.log(10,u" ..   startTcpipListening try#: {:d} time elapsed: {:4.1f} secs; resp: {}".format(ii, time.time()-tcpStart, e ) )

				try:
					ret = subprocess.Popen(lsofCMD, shell=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE).communicate()
					if len(ret[0]) >0: #  if lsof gives port number it works.. 
						if self.decideMyLog(u"StartSocket"): self.indiLOG.log(10,u" ..   startTcpipListening {}   output:\n{}".format(lsofCMD, ret[0].strip(u"\n")) )
						TCPserverHandle = threading.Thread(target=socketServer.serve_forever)
						TCPserverHandle.daemon =True # don't hang on exit
						TCPserverHandle.start()
						break
				except Exception, e:
					if unicode(e).find(u"serve_forever") == -1:
						self.indiLOG.log(40,u"Line {} has error={}".format(sys.exc_traceback.tb_lineno, e))
					self.killHangingProcess(ret)
 
				if	 ii <= 2:	tcpWaitTime = 7
				else:			tcpWaitTime = 1
				self.sleep(tcpWaitTime)
			try:
				tcpName = TCPserverHandle.getName() 
				self.indiLOG.log(20,u' ..   startTcpipListening tcpip socket listener running; thread-ID: {}'.format(tcpName) )#	+ " try:"+ unicode(ii)+u"  time elapsed:"+ unicode(time.time()-tcpStart) )
				stackReady = True


			except Exception, e:
				self.indiLOG.log(40,u"Line {} has error={}".format(sys.exc_traceback.tb_lineno, e))
				self.indiLOG.log(40,u" ..   startTcpipListening tcpip stack did not load, restarting.. if this error continues, try restarting indigo server")
				self.quitNow = u" tcpip stack did not load, restart"
			return	socketServer, stackReady

####-------------------------------------------------------------------------####
	def killHangingProcess(self, ret):

			test = (ret[0].strip(u"\n")).split(u"\n")

			if len(test) > 1:
				try: 
					for xx in test[1:]: # skip headerline
						pidTokill = int((xx.split())[1])
						killcmd = u"/bin/kill -9 {}".format(pidTokill)
						self.indiLOG.log(20,u" ..   startTcpipListening .. trying to kill hanging process with: {}, process:{} ".format(killcmd, xx) )
						subprocess.call(killcmd, shell=True)
				except Exception, e:
					self.indiLOG.log(40,u"Line {} has error={}".format(sys.exc_traceback.tb_lineno, e))


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
			len0 = 0
			piName = u"none"
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
			seqN = 0
			try: # to catch timeout 
				while True: # until end of message
					seqN +=1
					buff = self.request.recv(4096)#  max observed is ~ 3000 bytes
					if not buff or len(buff) == 0:#	 or len(buff) < 4096: 
						break
					data0 += buff
					len0  = len(data0)

					### check if package is complete:
					test = data0[:30].split(u"x-6-a")
					try: 
						nBytes = int(test[0])
						name   = test[2]
						startOfData = len(str(nBytes)) + 2*len(u"x-6-a") + len(test[1])
						dataS = [test[0],test[1],data0[startOfData:]]
					except Exception, e:
						indigo.activePlugin.indiLOG.log(40,u"ThreadedTCPRequestHandler Line {} has error={}".format(sys.exc_traceback.tb_lineno, e) )
						break

					if len(dataS) == 3 and int(dataS[0]) == len(dataS[2]): 
						break

					#safety valves
					if time.time() - tStart > 15: break 
					if	len0 > 40*4096: # check for overflow = 40 packages
						indigo.activePlugin.handlesockReporting(self.client_address[0],len0,u"unknown",u"errBuffOvfl" )
						self.request.close()
						return 
			except Exception, e:
				e= unicode(e)
				self.request.settimeout(1) 
				self.request.send(u"error")
				self.request.close()
				if e.find(u"timed out") ==-1: 
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
						if package1[0:14].find(u"++compressed==") != -1:
							package1 = zlib.decompress(package1[14:])          
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
				if dataS[2][0:14] == u"++compressed==":
					dataS[2] = zlib.decompress(dataS[2][14:])          
					if indigo.activePlugin.decideMyLog(u"Socket"): indigo.activePlugin.indiLOG.log(10,u"TCPIP socket  listener uncompressedfile len:{}".format(len(dataS[2])) )
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




