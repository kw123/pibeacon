#!/usr/bin/env python3
# -*- coding: utf-8 -*-
####################
# piBeaconConstants.py - the STATIC tables of the piBeacon plugin
#
# Split out of plugin.py: these ~900 lines of pure data (plugin-pref defaults, the device-type /
# state maps, the allowed sensor + output lists, the GPIO and icon tables) had nothing to do with
# the plugin logic and pushed the first line of real code to line 930.
#
# Everything here is DATA ONLY - no indigo import, no plugin state, nothing that runs at import
# time except the small loops that expand the tables. plugin.py imports the names explicitly.
#
# NOTE the two things that deliberately stayed in plugin.py: the "import indigo" try block, and the
# AppKit text-measurement helpers (_padTargetPx / _textWidthPx / _setupTextMeasurement). Those are
# not constants - _setupTextMeasurement REBINDS its module globals at runtime, and an imported name
# is a snapshot, so moving them would have left plugin.py reading stale values after every re-measure.
####################
import time

######### set new  pluginconfig defaults
# this needs to be updated for each new property added to pluginProps.
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
				"uselastMessageReceived":						False,
				"setClostestRPItextToBlank":					"1",
				"sendFullUUID":									"1",
				"removeJunkBeacons":							"1",
				"checkBeaconParametersDisabled":				False,
				"myIpNumber":									"192.168.1.x",
				"indigoInputPORT":								"12087",
				"blockNonLocalIp":								False,
				"checkRPIipForReject":							True,
				"maxSocksErrorTime":							"10",
				"compressRPItoPlugin":							"20000",
				"userIdOfServer":								"",
				"passwordOfServer":								"",
				"key_mgmt":										"NONE",
				"enableAutoconfigEmptySSD":						True,
				"rebootIfNoMessagesSeconds":					"99999999999999",
				"enableRebootRPIifNoMessages":					"999999999",
				"eth0":											'{"on":"on", "useIP":"use"}',
				"wlan0":										'{"on":"dontChange", "useIP":"use"}',
				"piUpdateWindow":								"0",
				"rPiCommandPORT":								"9999",
				"rebootHour":									"1",
				"expectTimeout":								"20",
				"restartBLEifNoConnect":						"1",
				"rebootWatchDogTime":							"-1",
				"GPIOpwm":										"1",
				"rpiDataAcquistionmethod":						"socket",
				"BLEconnectmode":								"attSocket",
				"displayPadTarget":								"80",
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
				"debugUpdateIndigo":							False,
				"debugSensorIcon":								False,
				"debugSpecial":									False,
				"debugDelayedActions":							False,
				"debugall":										False,
				"showLoginTest":								False,
				"execcommandsListAction":						"delete",
				"getBatteryMethod":								"interactive"
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
_sqlLoggerIgnoreStates = {"isBeaconDevice":			"Pi_00_Time,Pi_01_Time,Pi_02_Time,Pi_03_Time,Pi_04_Time,Pi_05_Time,Pi_06_Time,Pi_07_Time,Pi_08_Time,Pi_09_Time,Pi_10_Time,Pi_11_Time,Pi_12_Time,Pi_13_Time,Pi_14_Time,Pi_15_Time,Pi_16_Time,Pi_17_Time,Pi_18_Time,Pi_19_Time,TxPowerReceived,typeOfBeacon,closestRPIText,closestRPITextLast,displayStatus,status,status_ui,lastUpdateBatteryLevel,sensorvalue_ui,trigger,lastStatusChange,iBeacon,mfg_info"
						, "isRPIDevice":			"Pi_00_Time,Pi_01_Time,Pi_02_Time,Pi_03_Time,Pi_04_Time,Pi_05_Time,Pi_06_Time,Pi_07_Time,Pi_08_Time,Pi_09_Time,Pi_10_Time,Pi_11_Time,Pi_12_Time,Pi_13_Time,Pi_14_Time,Pi_15_Time,Pi_16_Time,Pi_17_Time,Pi_18_Time,Pi_19_Time,TxPowerReceived,typeOfBeacon,closestRPIText,closestRPITextLast,displayStatus,status,status_ui,online,i2cactive,sensorvalue_ui,trigger,lastStatusChange,lastMessageFromRpi"
						, "isBLEconnectDevice":		"Pi_00_Time,Pi_01_Time,Pi_02_Time,Pi_03_Time,Pi_04_Time,Pi_05_Time,Pi_06_Time,Pi_07_Time,Pi_08_Time,Pi_09_Time,Pi_10_Time,Pi_11_Time,Pi_12_Time,Pi_13_Time,Pi_14_Time,Pi_15_Time,Pi_16_Time,Pi_17_Time,Pi_18_Time,Pi_19_Time,TxPowerReceived,closestRPIText,closestRPITextLast,displayStatus,status,status_ui,sensorvalue_ui,lastStatusChange"
						, "isRPISensorDevice":		"displayStatus,status,status_ui,sensorvalue_ui,lastStatusChange,lastMessageFromRpi"
						, "isBLESensorDevice":		"displayStatus,status,status_ui,sensorvalue_ui,lastStatusChange"
						, "isBLElongConnectDevice":	"displayStatus,status,status_ui,sensorvalue_ui,lastStatusChange"
						, "isSensorDevice":			"displayStatus,status,status_ui,sensorvalue_ui,lastStatusChange"}


_debugAreas = ["Logic", "DevMgmt", "BeaconData", "SensorData", "OutputDevice", "UpdateRPI", "OfflineRPI", "BLE", "CAR", "all", "Socket", "StartSocket", "Special", "PlotPositions", "SocketRPI", "BatteryLevel", "SQLlogger", "SQLSuppresslog", "SensorIcon", "Beep", "UpdateTimeAndZone","GarageDoor","DelayedActions","UpdateIndigo","lastRPI","FindMy"]
_lastRPIoffText = "off, to enable turn debug on"		# shown in state lastUpdateFromRPI while its debug area is off



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
	"RPINumber":					"-1",
	"expectTimeout":				"",
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
	"rpiDataAcquistionmethod":  	"socket",
	"BLEconnectMode":				"useDefault",
	"shutDownPinOutput" :			"-1" }

# on/off state images per onOffSetting scheme: (image when ON, image when OFF). "" = set none.
# SensorOn = green, SensorOff = grey, SensorTripped = red - the names are not obvious, which is
# how "off = Grey" ended up showing a green icon for years.
_GlobalConst_onOffImages = {
			"on=green,off=grey":	("SensorOn",		"SensorOff"),
			"on=red,off=grey":		("SensorTripped",	"SensorOff"),
			"on=green,off=red":		("SensorOn",		"SensorTripped"),
			"on=red,off=green":		("SensorTripped",	"SensorOn"),
			"on=grey,off=red":		("SensorOff",		"SensorTripped"),
			"on=grey,off=green":	("SensorOff",		"SensorOn"),
			"off":					("",				""),
			}
_GlobalConst_fillMinMaxStates = ["countPerMinute", "Temperature", "AmbientTemperature", "Pressure", "Altitude", "Humidity", "Visible", "White", "Illuminance", "IR", "CO2", "VOC", "INPUT_0", "rainRate", "Moisture", "INPUT","Conductivity","Formaldehyde","AmbientLight"]

# families of values that can be switched off per device in DEVICE EDIT, checkbox id = "<family>_EnableValues".
# unchecking drops the whole family from the device state list; the values are then never written either,
# because setStatusCol() returns early for states the device does not have.
#   "categories":    the state categories (_stateListToDevTypes keys) the family covers
#   "default":       used when the device has no "<family>_EnableValues" prop yet (ie every existing device)
#   "defaultOffFor": device types that default to OFF instead - for hardware that does not have that sensor.
#                    The checkbox stays available, so it can simply be switched on if a later
#                    hardware revision does deliver the value.
_GlobalConst_optionalStateFamilies = {
	"Temperature":	{"default":True, "categories":["Temperature"]},
	"Humidity":		{"default":True, "categories":["Humidity"]},
	"Pressure":		{"default":True, "categories":["Pressure"]},
	"acceleration":	{"default":True, "categories":["accelerationX", "accelerationY", "accelerationZ", "accelerationTotal", "accelerationVectorDelta", "accelerationXYZMaxDelta"]},
	"CO2":			{"default":True, "categories":["CO2"]},
	"VOC":			{"default":True, "categories":["VOC"]},
	# Ruuvi dropped the light sensor from the Air, the E1 luminosity field is always the
	# "invalid" marker there - so OFF for the Air, unchanged for all the real light sensors
	"Illuminance":	{"default":True, "categories":["Illuminance"], "defaultOffFor":["BLERuuviAir"]}
}

# reverse lookup built once: state category -> family name
_GlobalConst_stateCategoryToFamily = {}
for _famName in _GlobalConst_optionalStateFamilies:
	for _famCat in _GlobalConst_optionalStateFamilies[_famName]["categories"]:
		_GlobalConst_stateCategoryToFamily[_famCat] = _famName

_GlobalConst_emptyRPI =	  {
	"rpiType":					"rPi",
	"enableRebootCheck":		"restartLoop",
	"enableiBeacons":			"1",
	"input":					{},
	"ipNumberPi":				"",
	"expectTimeout":			"",
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
	"lastSSDCheck":				0,
	"clearQueue":				False,
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
	"lastTimeIPChanged": 		time.time() - 300000000,
	"userIdPi": 				"pi"}


_GlobalConst_emptyRPISENSOR =	{
	"rpiType":					"rPiSensor",
	"enableRebootCheck":		"restartLoop",
	"enableiBeacons":			"0",
	"input":					{},
	"ipNumberPi":				"",
	"expectTimeout":			"",
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
	"lastSSDCheck":				0,
	"sendToIndigoSecs":			90,
	"sensorRefreshSecs":		20,
	"deltaChangedSensor":		5,
	"emptyMessages":			0,
	"lastTimeIPChanged": 		time.time() - 300000000,
	"userIdPi": 				"pi"}

_GlobalConst_allGPIOlist = [
	  ("-1", "L1  do not use +3.3V")
	, ("2",  "L3  GPIO02 -- I2C")
	, ("3",  "L5  GPIO03 -- I2C")
	, ("4",  "L7  GPIO04 -- ONE WIRE")
	, ("-1", "L9  do not use ground")
	, ("17", "L11 GPIO17 -- DHT")
	, ("27", "L13 GPIO27")
	, ("22", "L15 GPIO22")
	, ("-1", "L17 do not use +3.3V")
	, ("10", "L19 GPIO10 -- SPS MOSI")
	, ("9",  "L21 GPIO09 -- SPS MISO")
	, ("11", "L23 GPIO11 -- SPS SCLK")
	, ("-1", "L25 do not use +3.3V")
	, ("-1", "L27 do not use ID_SD")
	, ("5",  "L29 GPIO05 ")
	, ("6",  "L31 GPIO06 ")
	, ("13", "L33 GPIO13")
	, ("19", "L35 GPIO19")
	, ("26", "L37 GPIO26")
	, ("-1", "L39 do not use ground")
	, ("-1", "R2  do not use +5V")
	, ("-1", "R4  do not use +5V")
	, ("-1", "R6  do not use ground")
	, ("14", "R8  GPIO14  -- TX - REBOOT PIN OUT")
	, ("15", "R10 GPIO15 -- RX - REBOOT PIN IN")
	, ("18", "R12 GPIO18")
	, ("-1", "R14 do not use ground")
	, ("23", "R16 GPIO23")
	, ("24", "R18 GPIO24")
	, ("-1", "R20 do not use ground")
	, ("25", "R22 GPIO25")
	, ("8",  "R24 GPIO08 -- SPS CE0")
	, ("7",  "R26 GPIO07 -- SPS CE1")
	, ("-1", "R28 do not use ID_SC")
	, ("-1", "R30 do not use ground")
	, ("12", "R32 GPIO12")
	, ("-1", "R34 do not use ground")
	, ("16", "R36 GPIO16")
	, ("20", "R38 GPIO20")
	, ("21", "R40 GPIO21")]

_GlobalConst_ICONLIST	= [
	["NoImage", 			"NoImage"],
	["PowerOff", 			"PowerOn"],
	["PowerOn", 			"PowerOff"],
	["DimmerOn", 			"DimmerOff"],
	["DimmerOff", 			"DimmerOn"],
	["FanOff", 				"FanHigh"],
	["FanHigh", 			"FanOff"],
	["SprinklerOff", 		"SprinklerOn"],
	["SprinklerOn", 		"SprinklerOff"],
	["SensorOff", 			"SensorOn"],
	["SensorOn", 			"SensorOff"],
	["SensorOn", 			"SensorTripped"],
	["SensorTripped", 		"SensorOn"],
	["SensorOff", 			"SensorTripped"],
	["SensorTripped", 		"SensorOff"],
	["EnergyMeterOff", 		"EnergyMeterOn"],
	["LightSensorOn", 		"LightSensor"],
	["LightSensor", 		"LightSensorOn"],
	["MotionSensor", 		"MotionSensorTripped"],
	["MotionSensorTripped",	"MotionSensor"],
	["DoorSensorOpened",	"DoorSensorClosed"],
	["DoorSensorClosed", 	"DoorSensorOpened"],
	["WindowSensorClosed",	"WindowSensorOpened"],
	["WindowSensorOpened",	"WindowSensorClosed"],
	["TemperatureSensor",	"TemperatureSensorOn"],
	["HumiditySensor",		"HumiditySensorOn"],
	["HumidifierOff",		"HumidifierOn"],
	["DehumidifierOff",		"DehumidifierOn"],
	["TimerOn", 			"TimerOff"],
	["TimerOff", 			"TimerOn"]]


_GlobalConst_beaconPlotSymbols = [
	"text", "dot", "smallCircle", "largeCircle", "square"] # label/text only, dot, small circle, circle prop to dist to rpi, square (for RPI)



_BLEsensorTypes =["BLERuuviTag", "BLERuuviAir",
				"BLEiBS01", "BLEiBS01T", "BLEiBS01RG", "BLEiBS03G", "BLEiBS03T", "BLEiBS03TP", "BLEiBS03RG", "BLEiTrackButton", "BLEShellyButton","BLEShellyMotion","BLEShellyDoor",
				"BLEaprilAccel", "BLEaprilTHL", "BLEThermopro", "BLETempspike",
				"BLEminewE8", "BLEminewS1TH", "BLEminewS1TT", "BLEminewS1Plus", "BLEminewAcc",
				"BLEiSensor-on", "BLEiSensor-onOff", "BLEiSensor-RemoteKeyFob", "BLEiSensor-TempHum",
				"BLEblueradio",
				"BLEKKMsensor",
				"BLESatech",
				"BLEHunterNodeBT",
				"BLEmeeblue-on",
				"BLEswitchbotTempHum","BLEswitchbotTempHumCO2","BLEthermoBeacon", "BLEswitchbotMotion", "BLEswitchbotMMWaveMotion", "BLEswitchbotContact","BLEswitchbotHumidifierEvap",
				"BLEXiaomiMiTempHumRound", "BLEXiaomiMiTempHumClock", "BLEXiaomiMiformaldehyde", "BLEgoveeTempHum"]

_BLEconnectSensorTypes = ["BLEinkBirdPool01B","BLEXiaomiMiVegTrug","BLEXiaomiMiTempHumSquare"]

_GlobalConst_allowedSensors = [
	 "BLEfindMyGroup",														  # apple find my tags, counted as a group
	 "ultrasoundDistance", "vl503l0xDistance", "vl503l1xDistance", "vl6180xDistance", "vcnl4010Distance", # dist / light
	 "apds9960",															  # dist gesture
	 "i2cTCS34725", "i2cTSL2561", "i2cVEML6070", "i2cVEML6030", "i2cVEML6040", "i2cVEML7700",		# light
	 "i2cVEML6075", "i2cIS1145", "i2cOPT3001",									# light
	 "BLEmyBLUEt",
	 "Wire18B20", "i2cTMP102", "i2cMCP9808", "i2cLM35A",						 # temp
	 "DHT", "i2cAM2320", "i2cSHT21", "si7021",						 # temp / hum
	 "BLEXiaomiMiTempHumSquare",
	 "BLEXiaomiMiVegTrug",
	 "BLEinkBirdPool01B",	
	 "BLEKKMsensor",														
	 "i2cBMPxx", "i2cT5403", "i2cBMP280", "i2cMS5803",						 # temp / press
	 "i2cBMExx",															 # temp / press/ hum /
	 "i2cBMExx",															 # temp / press/ hum /
	 "bme680",																   #
	 "DF2301Q",																   # DF2301Q speach input
	 "FaceGesture",															   # face gesture input sensor
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
	 "MAX44009",																# Illuminance sensor
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
	"neopixel", "neopixel-dimmer", "neopixelClock", "OUTPUTswitchbotRelay", "OUTPUTswitchbotCurtain", "OUTPUTswitchbotCurtain3", "OUTPUTgpio-1-ONoff", "OUTPUTgpio-1", "OUTPUTi2cRelay", "OUTPUTgpio-4", "OUTPUTgpio-10", "OUTPUTgpio-26", "setMCP4725", "OUTPUTxWindows", "display", "setPCF8591dac", "setTEA5767", "sundial", "setStepperMotor", "FBHtempshow", "OUTPUTthermostatIRac"]

# gpio pin usage report: prop-name prefix -> what the pin DOES, where the device type alone would
# be wrong or unhelpful. An INPUTpulse device reads on gpioEcho but drives gpioTrigger, and a
# DF2301Q voice sensor drives an output pin per recognised command. Prefix match, lower case,
# first hit wins - anything not listed falls back to the device type.
_GlobalConst_gpioFieldDirection = {
	"gpiotrigger":				"out",
	"gpioecho":					"in",
	"onewiregpios":				"in/out",	# 1-wire is a bidirectional bus on one pin
	"onewireresetgpio":			"out",		# Wire18B20.py sets it to GPIO.OUT and drives it
	"gpioin":					"in",
	"gpionumberforcmdaction":	"out",
	"gpiocmdindicator":			"out",
	"gpiozone":					"out",
	"interruptgpio":			"in",
	"pin_webadhoc":				"in",
	"shutdowninputpin":			"in",
	"shutdownsignalfromupspin":	"in",
	"shutdownpinvoltsensor":	"in",
	"shutdownpinoutput":		"out",
	"shutdownpinvetooutput":	"out",
	"shutdownpinenable":		"out",
	}

# props that only POINT AT an output pin somebody else owns, instead of claiming it. A DF2301Q or
# FaceGesture sensor drives an indicator LED on a recognised command - several sensors sharing one
# LED is the normal setup, not a collision. Only pins claimed by more than one OWNER are a fault.
_GlobalConst_gpioReferenceFields = ["gpionumberforcmdaction", "gpiocmdindicator"]

# binding fields that say nothing about the HARDWARE, so a pin field hidden behind them is still a
# real pin: piDone/stateDone only mean "the dialog has not been confirmed yet", the others are
# convenience toggles for how much of the dialog is shown. Bindings on anything else - devType,
# typeOfUPS, mode, NumZones, resistorSensor ... - do describe the hardware and ARE honoured.
_GlobalConst_gpioIgnoreBindingOn = ["piDone", "stateDone", "expertMode", "showSpecialParameters", "showBeaconOnMap"]

_GlobalConst_groupList = ["Family", "Guests", "Other1", "Other2", "Other3", "Other4", "Other5"]
_GlobalConst_groupListDef = ["BEACON","PI","BLEconnect","SENSOR"]


_defaultDateStampFormat = "%Y-%m-%d %H:%M:%S"
_defaultDateStampFormatDay = "%H:%M:%S"


################################################################################
# for dev states:


# which dev types in general have which states and which property (real int, ...)
_devtypesToStates = {}
_devtypesToStates["rpiAndBeacon"] = {}
#_devtypesToStates["rpiAndBeacon"]["iBeacon"] = "String"	
_devtypesToStates["rpiAndBeacon"]["trigger"] = "String"	
_devtypesToStates["rpiAndBeacon"]["typeOfBeacon"] = "String"	
_devtypesToStates["rpiAndBeacon"]["vendorName"] = "String"	
_devtypesToStates["rpiAndBeacon"]["mfg_info"] = "String"	

_devtypesToStates["rpiAndBeaconAndBLEconnect"] = {}
for ii in range(_GlobalConst_numberOfiBeaconRPI):
	kk = f"{ii:02d}"
	_devtypesToStates["rpiAndBeaconAndBLEconnect"]["Pi_"+kk+"_Signal"] = "Integer"	
	_devtypesToStates["rpiAndBeaconAndBLEconnect"]["Pi_"+kk+"_Distance"] = "Real"	
	_devtypesToStates["rpiAndBeaconAndBLEconnect"]["Pi_"+kk+"_Time"] = "String"	

_devtypesToStates["rpiAndBeaconAndBLEconnect"]["PosX"] = "Real"	
_devtypesToStates["rpiAndBeaconAndBLEconnect"]["PosY"] = "Real"	
_devtypesToStates["rpiAndBeaconAndBLEconnect"]["PosZ"] = "Real"	
_devtypesToStates["rpiAndBeaconAndBLEconnect"]["lastUpdateFromRPI"] = "String"	
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
_devtypesToStates["rpiAndSensor"]["i2c_ok"] = "String"	
_devtypesToStates["rpiAndSensor"]["lastMessageFromRpi"] = "String"	
_devtypesToStates["rpiAndSensor"]["online"] = "String"	
_devtypesToStates["rpiAndSensor"]["lastStatusChange"] = "String"	


_devtypesToStates["rpi"] = {}
_devtypesToStates["rpi"]["RPI_throttled"] = "String"	
_devtypesToStates["rpi"]["sensors_active"] = "String"	
_devtypesToStates["rpi"]["closestiBeacon"] = "String"	
_devtypesToStates["rpi"]["closestiBeaconLast"] = "String"	
#_devtypesToStates["rpi"]["iBeacon"] = "String"	
# ONE state per BLE radio instead of five states that each named the radio of one role
# ("what is hci1 doing" used to mean reading all five and cross-referencing macs).
# Content: UP / USB / mac / usb-id / BLE4|BLE5|BLE4+5 / function(s), see hciStateStrings().
_devtypesToStates["rpi"]["hci0"] = "String"
_devtypesToStates["rpi"]["hci1"] = "String"
_devtypesToStates["rpi"]["hci2"] = "String"
_devtypesToStates["rpi"]["hci3"] = "String"
# which radio does BT5 extended advertising: "hci2-USB-58:11:22:53:8C:D5" (the reserved
# extended-listener dongle), "...-scan" when the scan radio itself delivers extended, or
# "None" when this rpi has no BLE5 reception. Replaces the old yes/no supportsBLE5 - with 3-4 dongles per rpi the
# useful fact is WHICH radio, not whether one of them can.


_devtypesToStates["beacon"] = {}
_devtypesToStates["beacon"]["lastStatusChange"] = "String"	
_devtypesToStates["beacon"]["isBeepable"] = "String"	
_devtypesToStates["beacon"]["vendorName"] = "String"	
_devtypesToStates["beacon"]["lastUpdateBatteryLevel"] = "String"	
_devtypesToStates["beacon"]["lastBatteryReplaced"] = "String"	
#_devtypesToStates["beacon"]["iBeacon"] = "String"	


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


# add min max ... to state name
_devtypesToStates["realSensor"] 	= {"":"Real"	, "Trend":"String", "MinTodayAt":"String",	"MaxYesterdayAt":"String",	"MinYesterdayAt":"String",	"MaxTodayAt":"String",	"MinToday":"Real",		"MaxYesterday":"Real",		"MinYesterday":"Real",		"MaxToday":"Real",		"AveToday":"Real",		"AveYesterday":"Real",		"MeasurementsToday":"Number",	"MeasurementsYesterday":"Integer",	"ChangeMinutes05":"Real",		"ChangeMinutes10":"Real",		"ChangeMinutes20":"Real",		"ChangeHours01":"Real",		"ChangeHours02":"Real",		"ChangeHours06":"Real",		"ChangeHours12":"Real"  ,	"ChangeHours24":"Real",		"ChangeHours48":"Real"}
_devtypesToStates["integerSensor"]	= {"":"Integer"	, "Trend":"String", "MinTodayAt":"String",	"MaxYesterdayAt":"String",	"MinYesterdayAt":"String",	"MaxTodayAt":"String",	"MinToday":"Integer",	"MaxYesterday":"Integer",	"MinYesterday":"Integer",	"MaxToday":"Integer",	"AveToday":"Integer",	"AveYesterday":"Integer",	"MeasurementsToday":"Integer",	"MeasurementsYesterday":"Integer",	"ChangeMinutes05":"Integer",	"ChangeMinutes10":"Integer",	"ChangeMinutes20":"Integer",	"ChangeHours01":"Integer",	"ChangeHours02":"Integer",	"ChangeHours06":"Integer",	"ChangeHours12":"Integer",	"ChangeHours24":"Integer",	"ChangeHours48":"Integer"}
_devtypesToStates["String"]		= {"":"String"}
_devtypesToStates["boolean"]	= {"":"boolean"}

# dev state has wich properties, 1. if add min max etc 2. real, int, strig ..
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
_addingstates["Red"]							= {"addTag":False, "States":{"Red":"Integer"}}
_addingstates["Green"]							= {"addTag":False, "States":{"Green":"Integer"}}
_addingstates["Blue"]							= {"addTag":False, "States":{"Blue":"Integer"}}
_addingstates["Orange"]							= {"addTag":False, "States":{"Orange":"Real"}}
_addingstates["Yellow"]							= {"addTag":False, "States":{"Yellow":"Real"}}
_addingstates["Violet"]							= {"addTag":False, "States":{"Violet":"Real"}}
_addingstates["LEDcurrent"]						= {"addTag":False, "States":{"LEDcurrent":"Real"}}
_addingstates["clear"]							= {"addTag":False, "States":{"Clear":"Integer"}}
_addingstates["rotation"]						= {"addTag":False, "States":{"rotation":"Integer"}}
_addingstates["Illuminance"]					= {"addTag":True, "States":_devtypesToStates["realSensor"]}
_addingstates["AmbientTemperature"]				= {"addTag":True, "States":_devtypesToStates["realSensor"]}
_addingstates["Temperature"]					= {"addTag":True, "States":_devtypesToStates["realSensor"]}
_addingstates["IR"]								= {"addTag":True, "States":_devtypesToStates["realSensor"]}
_addingstates["AmbientLight"]					= {"addTag":True, "States":_devtypesToStates["realSensor"]}
_addingstates["White"]							= {"addTag":True, "States":_devtypesToStates["realSensor"]}
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

# INPUT/OUTPUT on-off devices: same display as beacons/rpis - the state WORD plus a
# timestamp, pixel-aligned by padDisplay(). Written in executeUpdateStatesDict whenever
# onOffState changes; getDeviceDisplayStateId then prefers "displayStatus" automatically.
_addingstates["onOffDisplayStatus"]			= {"addTag":False, "States":{"displayStatus":"String", "lastOn":"String", "lastOff":"String"}}

_addingstates["accelerationX"]					= {"addTag":False, "States":{"accelerationX":"Integer"}}
_addingstates["accelerationY"]					= {"addTag":False, "States":{"accelerationY":"Integer"}}
_addingstates["accelerationZ"]					= {"addTag":False, "States":{"accelerationZ":"Integer"}}
_addingstates["accelerationVectorDelta"]		= {"addTag":False, "States":{"accelerationVectorDelta":"Integer"}}
_addingstates["accelerationTotal"]				= {"addTag":False, "States":{"accelerationTotal":"Integer"}}
_addingstates["accelerationXYZMaxDelta"]		= {"addTag":False, "States":{"accelerationXYZMaxDelta":"Integer"}}

_addingstates["batteryVoltage"]					= {"addTag":False, "States":{"batteryVoltage":"Real"}}

# Find My group counter. The states a BLEfindMyGroup device carries - see pi/findMyGroup.py.
# HOW MANY ARE ACTIVE - find my devices whose mac was in the LAST MESSAGE from an rpi. Settled:
# it only moves after the new value has held for stableSecs, so a tag rotating its mac is
# invisible. numberOfActiveRaw is the same thing unsettled, the union of this instant.
# NAMED "ACTIVE" AND NOT "COUNT" because the number beside it is membersUp, and "memberCount vs
# membersUp" told nobody which was which. ACTIVE is transmitting right now; UP is present, which
# includes a tag inside memberDownDelaySecs that has simply not been heard in the last report.
# It is also the numberOf* family the breakdown already uses - airtags, airpods, other, total.
# THE RPI SENDS THE SAME NAME. The message field and the indigo state used to be two different
# words for one number, which is exactly the confusion this rename is for. They changed together,
# so every rPi must be pushed with this version - an rPi still sending the old field names is not
# understood at all. That is deliberate: a silent half-rename is worse than a loud mismatch
_addingstates["numberOfActive"]					= {"addTag":False, "States":{"numberOfActive":"Integer"}}
_addingstates["numberOfActiveRaw"]				= {"addTag":False, "States":{"numberOfActiveRaw":"Integer"}}
# HOW MANY MEMBER DEVICES ARE UP, which is NOT numberOfActive and is bigger than it most of the
# time. The two answer "present" with different evidence and both are right: active is the macs in
# the LAST MESSAGE, while a member device stays up for memberDownDelaySecs after it stops being
# heard, because one report that does not mention a tag is not evidence the tag has gone.
# So "7 members, 13 up" means seven were in the last message and six more were heard inside the
# delay. Without this state that difference has to be worked out from the member table every time
_addingstates["numberOfUp"]						= {"addTag":False, "States":{"numberOfUp":"Integer"}}
# and how many member devices EXIST, which the state column shows beside it as "12/16 up". The
# total is the number people actually go and count - it is what says whether slots are filling up
# with tags that have gone - and having it here means not counting rows in the device list to find it
_addingstates["numberOfMembers"]				= {"addTag":False, "States":{"numberOfMembers":"Integer"}}
_addingstates["numberOfWeak"]					= {"addTag":False, "States":{"numberOfWeak":"Integer"}}
_addingstates["numberOfCandidates"]				= {"addTag":False, "States":{"numberOfCandidates":"Integer"}}
_addingstates["strongestRSSI"]					= {"addTag":False, "States":{"strongestRSSI":"Integer"}}
_addingstates["numberOfActivePrevious"]					= {"addTag":False, "States":{"numberOfActivePrevious":"Integer"}}
_addingstates["numberOfActiveChanged"]				= {"addTag":False, "States":{"numberOfActiveChanged":"String"}}
# with several rpis feeding one device: how many of the enabled rpis are currently reporting
# ("2 of 3"), and how many tags more than one rpi can hear. A tag heard by two rpis is far better
# evidence of "really inside" than any single signal level, which is why it gets its own state
_addingstates["pisReporting"]					= {"addTag":False, "States":{"pisReporting":"String"}}
_addingstates["seenBy2Plus"]					= {"addTag":False, "States":{"seenBy2Plus":"Integer"}}
_addingstates["findMyTrigger"]					= {"addTag":False, "States":{"findMyTrigger":"String"}}
# WHAT the members are, split by their apple continuity types AND BY UP/DOWN - two counters per
# kind, not one. COUNTED OVER THE MEMBER DEVICES, each from its own appleTypes.
# WHY TWO AND NOT ONE. A single numberOfAirtags had to answer both "how many airtags are HERE"
# and "how many airtags does this group KNOW ABOUT", which are different numbers that differ by
# exactly the ones that have gone quiet - so whichever it was counted over, it was the wrong
# answer to the other question. Counted over the live union it read 0 airpods while two devices
# in the list both said airpods, because airpods earpieces go back in their case and stop
# advertising altogether; counted over all the devices it would say 2 while none was here.
# Neither number is inferred now. Both are counted.
# THE ARITHMETIC CLOSES ON STATES THAT ALREADY EXIST, which is why the split is worth the six
# states: the three ...Up add up to numberOfUp, and all six add up to numberOfMembers. They are
# tallied at the same three points in the member loop that decide up or down, so they are made
# of that decision and cannot drift from it.
# A DOWN MEMBER KEEPS ITS KIND: appleTypes stays on the device when it goes down, because it is
# the record of what was there, and that is what the ...Down counters are counting.
# "airtags" is the honest-but-shorter name for "sends find my and nothing else": that is an
# airtag or any other find my accessory, and nothing in the frame can narrow it further - see
# findMyAppleTypes(). "airpods" is the 07+12 pair a case sends with the lid open. "other" is
# everything else, ie a mac that also does live-apple-device things, which a tag cannot
_addingstates["numberOfAirtagsUp"]				= {"addTag":False, "States":{"numberOfAirtagsUp":"Integer"}}
_addingstates["numberOfAirtagsDown"]			= {"addTag":False, "States":{"numberOfAirtagsDown":"Integer"}}
_addingstates["numberOfAirpodsUp"]				= {"addTag":False, "States":{"numberOfAirpodsUp":"Integer"}}
_addingstates["numberOfAirpodsDown"]			= {"addTag":False, "States":{"numberOfAirpodsDown":"Integer"}}
_addingstates["numberOfOtherUp"]				= {"addTag":False, "States":{"numberOfOtherUp":"Integer"}}
_addingstates["numberOfOtherDown"]				= {"addTag":False, "States":{"numberOfOtherDown":"Integer"}}
# and all six added up, so the breakdown CHECKS ITSELF at a glance instead of in your head.
# It equals numberOfMembers by construction - every device lands in exactly one of the six - and
# that is the point: when it does not, something is wrong and it is visible without a calculator
_addingstates["numberOfTotal"]					= {"addTag":False, "States":{"numberOfTotal":"Integer"}}
# ONE DEVICE PER MEMBER, not one state per slot. The rpi hands out slot numbers 01..NN (sticky -
# a mac keeps its slot while it stays a member) and the plugin gives each slot in use its own
# indigo device, "findmy_NN", carrying the states below. The device NAME is the label, editable in
# place, which is what 20 name fields in a dialog were standing in for.
# WHAT THIS DOES NOT FIX: the device is bound to a SLOT, not to a tag. Find my macs rotate and
# nothing in the frame is stable, so if a slot changes hands the device describes something else -
# now under a name somebody chose, which is more misleading than a numbered state was. That is why
# mac / previousMacs / lastMacChange sit ON the device: the drift has to be visible.
_GlobalConst_findMyMemberStates = 60		# THE CEILING for member devices, mirrored by MAXSLOTS in
											# pi/findMyGroup.py. The group device's "maxSlots" menu picks the number
											# actually in use and is clamped to this on BOTH sides - they have to agree
											# or the rpi hands out a slot no device exists for.
											# NO STATES SCALE WITH IT: one DEVICE per member, not one state per slot,
											# so this is a loop bound and nothing more
_GlobalConst_findMyMacHistory   = 5			# macs kept in previousMacs, mirrored by MACHISTORY there
_devtypesToStates["BLEfindMyMember"] = {
		"mac":			"String",		# the rotating mac in this slot right now, blank when empty
		"rssi":			"Integer",
		"distance":		"Real",			# METRES (or whatever distanceUnits says) from the rPi that hears
										# it best, from rssi and the device's own "rssi at 1 m" - the same
										# calcDist() every beacon in this plugin uses
		"distanceIndicator":"String",	# separated / nearby / lenNN - AN INDICATOR OF DISTANCE FROM THE
										# OWNER, which is why it is not called distance. "nearby" = the tag
										# believes its owner's phone is with it; "separated" = it does not,
										# and is broadcasting the rotating key so any passing apple device
										# can report where it is. Independent of the distance above: a
										# separated tag can be on the desk next to the rPi
		"battery":		"String",		# full / medium / low / critical - reverse engineered, not a spec.
										# TWO BITS of the status byte is ALL the battery a find my frame
										# carries, so these four words are the whole resolution there is.
										# indigo's OWN batteryLevel renders the same two bits as 100/50/20/1%
										# - it is NOT declared here and is not a plugin state at all: it
										# comes from the SupportsBatteryLevel property, which the first real
										# reading switches on. See findMyEnableBatteryLevel in plugin.py
		"slot":			"String",		# "01".."50", the number the rpi assigned
		"previousMacs":	"String",		# the macs this slot held before, NEWEST FIRST, at most
										# _GlobalConst_findMyMacHistory of them: "D0:75:.., C7:8B:.."
										# A find my mac rotates every 15 min, so the current mac says
										# nothing about which tag this is - the trail of them is the
										# only way to tell a rotation from a slot changing hands
		"lastMacChange":"String",		# and when it went - "yyyy-mm-dd hh:mm:ss". NAMED FOR THE MAC on
										# purpose: it is not "when did anything about this device
										# change", it is the moment the slot's mac was replaced
		"lastStatusChange":"String",	# and when it last went up or down. The state column shows the
										# LATER of these two, so it reads "when did something happen
										# here" rather than "when did a message arrive"
		"appleTypes":	"String",		# every apple continuity type this mac sends, and what they add
										# up to: "12  tag", "07|12  airpods/case", "05|0C|10|12
										# phone/mac". A TAG SENDS ONLY FIND MY, so a single "12" is the
										# mark of a real tag and anything more is airpods, a phone or a
										# mac - which the word after the codes already says
		"hintByte":		"String",		# THE LAST BYTE OF THE SEPARATED PAYLOAD, two hex digits - "8D" -
										# or blank for a tag that has only ever sent the 2 byte nearby
										# payload, which has no such byte. BLANK MEANS "NEVER SAID",
										# not "said zero", which is why it is text and not a number.
										# NO PUBLISHED MEANING beyond "0x00 on ios", and it is named for
										# what it IS rather than what it might be on purpose - a label
										# that turns out to be wrong is worse than no label.
										# WHAT IT IS NOT, MEASURED 2026-09-25 AND SETTLED: it is not a
										# pointer to another device's address. That theory came from
										# two eyeballed coincidences - hint 8D beside a mac ending 8D,
										# hint 96 beside a mac ending 96 - and the calibration log
										# killed it in one pass: across 151 rows the hint matched the
										# last byte of another mac present at the time 3 times, which
										# is at or below chance for a byte and a dozen macs.
										# WHAT IT IS: a 15 MINUTE EPOCH MARKER, and nothing to do with
										# the key. Six true transitions on one rPi landed at 16:14:32,
										# 16:15:03 (three independent macs at once) and 16:30:03 /
										# 16:30:13 - a 15 minute boundary, synchronised across devices
										# with nothing to do with each other.
										# AND IT IS THE ONLY THING THAT MOVES. Two separated frames
										# from one tag 19 minutes apart, across the 16:30 boundary,
										# differ in EXACTLY ONE BYTE of 31: the hint, 83 -> 7B. Status,
										# all 22 key bytes and the key-bits byte are byte-identical.
										# So it is not key material and not derived from it - the key
										# sat still while this moved
										# THEREFORE USELESS AS A ROTATION MATCHER, and worse than
										# useless: at an epoch boundary every hint changes, so matching
										# on it would refuse exactly the rotations that happen there.
										# Kept because it costs nothing and a marked epoch is the kind
										# of thing that turns out to be handy - NOT because a use for
										# it is expected. Nothing reads it
		"movedRpi":		"String",		# when this tag last moved from one rPi to ANOTHER - ie when
										# closestRPI went from one real rPi to a different real one. NOT written
										# when it merely goes down and comes back on the same rPi, which is not a
										# move - the same rule that governs closestRPILast
		"tagIds":		"String",		# THE LINEAGE, "2-1043, 5-77" - this tag's id on each rPi that can
										# hear it. The mac joins two rPis at one INSTANT; a tagId joins one rPi
										# across TIME, because the rPi keeps it when the mac rotates. Both are
										# needed to keep this device on the same physical tag - see
										# matchRotation() in pi/findMyGroup.py
		"previousStatusChange":"String",# THE ONE BEFORE IT. A member that goes down and comes back a few
										# seconds later used to leave nothing behind: the return overwrote
										# lastStatusChange and the dip was gone unless somebody happened to
										# be watching. With both, "previous 19:52:48, last 19:52:51" says
										# plainly that it flapped, and how long it was away
		"previousTagIds":"String",		# the lineages this device held BEFORE, newest first, "; " between
										# them. A LINEAGE CHANGE WITH NO MAC CHANGE is the signature of a
										# wrong rotation match: the rPi handed this mac's lineage to a
										# newcomer while this mac was still transmitting. It is over in
										# seconds and left no trace at all, so it had to be watched live
										# to be seen - which is not a way to debug anything
		"lastTagIdChange":"String",		# and when the lineage last moved. Beside lastMacChange it says
										# which of the two changed, which is the whole question
		"lastSeen":		"String",		# when any rPi last reported this tag. NOT the same as lastStatusChange:
										# that is when it changed, this is when it was last HEARD, and the
										# difference is what the down-delay below is measured against
		"created":		"String",		# when this slot first came into use and this device was made
		}
_addingstates["BLEfindMyMember"]				= {"addTag":False, "States":_devtypesToStates["BLEfindMyMember"]}

# WHICH RPI HEARS THIS TAG, AND HOW WELL - the same states a beacon carries, with the same names
# and, deliberately, the SAME TYPES: indigo's sql logger makes one column per state NAME across
# every device type, so Pi_02_Distance being a Real here and a Real there is not a nicety, it is
# the difference between logging and the "failures updating device history" that .53 caused
# (see checkStateTypeCollisions). Same names also means a control page or a plot written for
# beacons works on these devices unchanged.
#   Pi_NN_Signal     the LAST rssi that rpi measured - never overwritten when it stops
#   Pi_NN_Distance   metres from THAT rpi, from that rssi and the device's "rssi at 1 m"
#   Pi_NN_Time       when that reading was taken
#   Pi_NN_State      up / weak / down / noData - what that rpi is saying about this tag RIGHT
#                    NOW, which is what says whether the three above are live or are the last
#                    thing it heard. FOUR VALUES because "down" used to mean three things:
#                      up      in that rpi's member list - the trio beside it is live
#                      weak    it HEARS the tag and does not count it (below joinRssi, or short
#                              of minPackets). A threshold to adjust, not a tag that has gone
#                      noData  that rpi is not reporting at all. It says nothing about this tag
#                              because it is saying nothing - not the same as "cannot hear it"
#                      down    reporting, and this tag is in nothing it sent
#                    A trigger for "not properly here" is != "up", which covers all three.
#                    -999 / 999 are stamped once at birth and mean ONE thing for the life of
#                    the device: that rpi has never heard this tag. Nothing overwrites a real
#                    reading with them - the question "is it here now" has its own state
# ALL of them are declared; getDeviceStateList drops the ones that do not apply - an rpi that is
# switched off, and on a member device any rpi its GROUP does not have enabled. That is why
# saving the group device rebuilds its members' state lists.
_devtypesToStates["findMyPerRpi"] = {}
for ii in range(_GlobalConst_numberOfiBeaconRPI):
	kk = f"{ii:02d}"
	_devtypesToStates["findMyPerRpi"]["Pi_"+kk+"_Signal"]	= "Integer"
	_devtypesToStates["findMyPerRpi"]["Pi_"+kk+"_Distance"]	= "Real"
	_devtypesToStates["findMyPerRpi"]["Pi_"+kk+"_Time"]		= "String"
	_devtypesToStates["findMyPerRpi"]["Pi_"+kk+"_State"]	= "String"
# and which of them is nearest now, with the one before it. The TEXT pair carries the rpi's
# indigo device NAME: "2" is not something to read off a control page, "Pi_kitchen" is
_devtypesToStates["findMyPerRpi"]["closestRPI"]			= "Integer"	# the rpi that heard it LAST -
																			# not blanked when nobody does
_devtypesToStates["findMyPerRpi"]["closestRPIText"]		= "String"
_devtypesToStates["findMyPerRpi"]["closestRPILast"]		= "Integer"	# kept when the tag goes down -
_devtypesToStates["findMyPerRpi"]["closestRPITextLast"]	= "String"	# "where was it last seen"
_addingstates["findMyPerRpi"]					= {"addTag":False, "States":_devtypesToStates["findMyPerRpi"]}

_addingstates["packetId"]						= {"addTag":False, "States":{"packetId":"Integer"}}
_addingstates["currentEvent"]					= {"addTag":False, "States":{"currentEvent":"String"}}
_addingstates["previousEvent"]					= {"addTag":False, "States":{"previousEvent":"String"}}
_addingstates["currentEventType"]				= {"addTag":False, "States":{"currentEventType":"String"}}
_addingstates["previousEventType"]				= {"addTag":False, "States":{"previousEventType":"String"}}
_addingstates["OUTPUT"]							= {"addTag":False, "States":{"OUTPUT":"String"}}
_addingstates["status"]							= {"addTag":False, "States":{"status":"String"}}
_addingstates["actualStatus"]					= {"addTag":False, "States":{"actualStatus":"String"}}
_addingstates["inverse"]						= {"addTag":False, "States":{"inverse":"Boolean"}}
_addingstates["initial"]						= {"addTag":False, "States":{"initial":"String"}}

_addingstates["counter"]						= {"addTag":False, "States":{"counter":"Integer"}}
_addingstates["cmd"]							= {"addTag":False, "States":{"cmd":"String"}}
_addingstates["cmdAt"]							= {"addTag":False, "States":{"cmdAt":"String"}}
_addingstates["cmdText"]						= {"addTag":False, "States":{"cmdText":"String"}}
_addingstates["lastCmd"]						= {"addTag":False, "States":{"lastCmd":"String"}}
_addingstates["lastCmdAt"]						= {"addTag":False, "States":{"lastCmdAt":"String"}}
_addingstates["lastCmd2"]						= {"addTag":False, "States":{"lastCmd2":"String"}}
_addingstates["lastCmd2At"]						= {"addTag":False, "States":{"lastCmd2At":"String"}}
_addingstates["faces"]							= {"addTag":False, "States":{"faces":"Integer"}}
_addingstates["facesX"]							= {"addTag":False, "States":{"facesX":"Integer"}}
_addingstates["facesY"]							= {"addTag":False, "States":{"facesY":"Integer"}}
_addingstates["facesScore"]						= {"addTag":False, "States":{"facesScore":"Integer"}}
_addingstates["cmdScore"]						= {"addTag":False, "States":{"cmdScore":"Integer"}}
_addingstates["PM25"]							= {"addTag":False, "States":{"PM25":"Real"}}	# 0.1 ug/m3 resolution - Integer truncated 1.2 -> 1
_addingstates["PM1"]							= {"addTag":False, "States":{"PM1":"Real"}}
_addingstates["PM4"]							= {"addTag":False, "States":{"PM4":"Real"}}
_addingstates["PM10"]							= {"addTag":False, "States":{"PM10":"Real"}}
_addingstates["NOx"]							= {"addTag":False, "States":{"NOx":"Integer"}}
_addingstates["humidityMode"]					= {"addTag":False, "States":{"humidityMode":"String"}}
_addingstates["overHumidifyProtection"]			= {"addTag":False, "States":{"overHumidifyProtection":"Boolean"}}
_addingstates["childLock"]						= {"addTag":False, "States":{"childLock":"Boolean"}}
_addingstates["tankRemoved"]					= {"addTag":False, "States":{"tankRemoved":"Boolean"}}
_addingstates["tiltedAlert"]					= {"addTag":False, "States":{"tiltedAlert":"Boolean"}}
_addingstates["filterMissing"]					= {"addTag":False, "States":{"filterMissing":"Boolean"}}
_addingstates["MeterBound"]						= {"addTag":False, "States":{"MeterBound":"Boolean"}}
_addingstates["waterLevel"]						= {"addTag":False, "States":{"waterLevel":"String"}}
_addingstates["filterRunTime"]					= {"addTag":False, "States":{"filterRunTime":"Integer"}}
_addingstates["targetHumidity"]					= {"addTag":False, "States":{"targetHumidity":"Integer"}}
_addingstates["alarmBits"]						= {"addTag":False, "States":{"alarmBits":"String"}}



#which devtype has which state
_stateListToDevTypes = {}
for _fmState in (["numberOfMembers","numberOfUp","numberOfActive","numberOfActiveRaw",
					"numberOfWeak","numberOfCandidates","strongestRSSI",
					"numberOfActivePrevious","numberOfActiveChanged","findMyTrigger","pisReporting","seenBy2Plus",
					"numberOfAirtagsUp","numberOfAirtagsDown",
					"numberOfAirpodsUp","numberOfAirpodsDown",
					"numberOfOtherUp","numberOfOtherDown","numberOfTotal",
					]):
	_stateListToDevTypes[_fmState]				= {"BLEfindMyGroup":1}

_stateListToDevTypes["BLEfindMyMember"]			= {"BLEfindMyMember":1}
_stateListToDevTypes["findMyPerRpi"]			= {"BLEfindMyMember":1}
_stateListToDevTypes["packetId"]				= {"BLEShellyDoor":1,"BLEShellyMotion":1,"BLEShellyButton":1}
_stateListToDevTypes["currentEvent"]			= {"BLEShellyDoor":1,"BLEShellyMotion":1,"BLEShellyButton":1}
_stateListToDevTypes["previousEvent"]			= {"BLEShellyDoor":1,"BLEShellyMotion":1,"BLEShellyButton":1}
_stateListToDevTypes["currentEventType"]		= {"BLEShellyButton":1}
_stateListToDevTypes["previousEventType"]		= {"BLEShellyButton":1}

_stateListToDevTypes["cmd"]						= {"DF2301Q":1,"FaceGesture":1}
_stateListToDevTypes["cmdAt"]					= {"DF2301Q":1,"FaceGesture":1}
_stateListToDevTypes["lastCmd"]					= {"DF2301Q":1,"FaceGesture":1}
_stateListToDevTypes["lastCmdAt"]				= {"DF2301Q":1,"FaceGesture":1}
_stateListToDevTypes["lastCmd2"]				= {"DF2301Q":1,"FaceGesture":1}
_stateListToDevTypes["lastCmd2At"]				= {"DF2301Q":1,"FaceGesture":1}
_stateListToDevTypes["cmdText"]					= {"DF2301Q":1,"FaceGesture":1}
_stateListToDevTypes["faces"]					= {"FaceGesture":1}
_stateListToDevTypes["facesScore"]				= {"FaceGesture":1}
_stateListToDevTypes["facesX"]					= {"FaceGesture":1}
_stateListToDevTypes["facesY"]					= {"FaceGesture":1}
_stateListToDevTypes["cmdScore"]				= {"FaceGesture":1}

_stateListToDevTypes["lastBatteryReplaced"]		= {"BLEiSensor-onOff":1, "BLEmeeblue-on":1, "BLEiSensor-on":1, "BLEiSensor-TempHum":1}
_stateListToDevTypes["status"]					= {"garageDoor":1, "FBHtempshow":1}
_stateListToDevTypes["actualStatus"]			= {"OUTPUTswitchbotRelay":1, "OUTPUTi2cRelay":1, "OUTPUTgpio-1-ONoff":1, "OUTPUTgpio-1":1}
_stateListToDevTypes["inverse"]					= {"OUTPUTi2cRelay":1, "OUTPUTgpio-1-ONoff":1, "OUTPUTgpio-1":1}
_stateListToDevTypes["initial"]					= {"OUTPUTi2cRelay":1, "OUTPUTgpio-1-ONoff":1, "OUTPUTgpio-1":1}
_stateListToDevTypes["OUTPUT"]					= {"OUTPUTi2cRelay":1, "OUTPUTgpio-1-ONoff":1, "OUTPUTgpio-1":1, "setMCP4725":1, "setPCF8591dac":1, "display":1, "neopixel":1}
_stateListToDevTypes["counter"]					= {"BLEXiaomiMiTempHumClock":1, "BLEXiaomiMiformaldehyde":1, "BLEXiaomiMiTempHumRound":1, "BLEgoveeTempHum":1, "BLESatech":1, "BLEiSensor-onOff":1, "BLEiSensor-on":1, "BLEswitchbotContact":1 ,"DF2301Q":1,"FaceGesture":1, "BLEswitchbotTempHumCO2":1}
_stateListToDevTypes["Conductivity"]			= {"BLEXiaomiMiVegTrug":1 }
_stateListToDevTypes["Moisture"]				= {"BLEXiaomiMiVegTrug":1, "moistureSensor":1 }
_stateListToDevTypes["speed"]					= {"vcnl4010Distance":1, "vl6180xDistance":1, "ultrasoundDistance":1, "vl503l1xDistance":1, "vl503l0xDistance":1}
_stateListToDevTypes["distanceEvent"]			= {"vcnl4010Distance":1, "vl6180xDistance":1, "ultrasoundDistance":1, "vl503l1xDistance":1, "vl503l0xDistance":1}
_stateListToDevTypes["trigger"]					= {"vcnl4010Distance":1, "vl6180xDistance":1, "ultrasoundDistance":1, "vl503l1xDistance":1, "vl503l0xDistance":1, "BLERuuviTag":1, "BLERuuviAir":1, "BLEiBS01T":1, "BLEthermoBeacon":1, "BLEinkBirdPool01B":1, "BLEShellyDoor":1, "BLEShellyMotion":1, "BLEShellyButton":1}
_stateListToDevTypes["distance"]				= {"vcnl4010Distance":1, "vl6180xDistance":1, "ultrasoundDistance":1, "vl503l1xDistance":1, "vl503l0xDistance":1}
_stateListToDevTypes["distanceRaw"]				= {"vcnl4010Distance":1, "vl6180xDistance":1, "ultrasoundDistance":1, "vl503l1xDistance":1, "vl503l0xDistance":1}
_stateListToDevTypes["rotation"]				= {"BLEShellyDoor":1}
_stateListToDevTypes["batteryVoltage"]			= {"BLERuuviTag":1, "BLEiBS01T":1, "BLEiBS03T":1, "BLEiBS03TP":1, "BLEminewS1TH":1, "BLEXiaomiMiTempHumRound":1, "BLEXiaomiMiTempHumSquare":1, "BLEminewAcc":1, "BLEminewS1Plus":1, "BLEthermoBeacon":1, "BLEinkBirdPool01B":1, "BLEKKMsensor":1, "BLEiBS03RG":1, "BLEiBS01RG":1, "BLEiBS01":1, "BLESatech":1, "BLEmeeblue-on":1}
_stateListToDevTypes["IR"]						= {"i2cTSL2561":1}
_stateListToDevTypes["Kelvin"]					= {"i2cTCS34725":1, "apds9960":1}
_stateListToDevTypes["Clear"]					= {"i2cTCS34725":1, "apds9960":1}
_stateListToDevTypes["Orange"]					= {"as726x":1}
_stateListToDevTypes["Yellow"]					= {"as726x":1}
_stateListToDevTypes["Violet"]					= {"as726x":1}
_stateListToDevTypes["LEDcurrent"]				= {"as726x":1}
_stateListToDevTypes["alarmBits"]				= {"BLEswitchbotTempHumCO2":1}
_stateListToDevTypes["Red"]						= {"i2cTCS34725":1, "apds9960":1,"i2cVEML6040":1, "as726x":1}
_stateListToDevTypes["Green"]					= {"i2cTCS34725":1, "apds9960":1,"i2cVEML6040":1, "as726x":1}
_stateListToDevTypes["Blue"]					= {"i2cTCS34725":1, "apds9960":1,"i2cVEML6040":1, "as726x":1}
_stateListToDevTypes["White"]					= {"i2cVEML7700":1, "i2cVEML6030":1,"i2cVEML6040":1,"apds9960":1}
_stateListToDevTypes["AmbientLight"]			= {"i2cTSL2561":1,"i2cVEML7700":1,"i2cVEML6030":1}
_stateListToDevTypes["Illuminance"]				= {"apds9960":1, "BLEXiaomiMiVegTrug":1, "BLEaprilTHL":1, "i2cTCS34725":1, "MAX44009":1, "as726x":1, "i2cOPT3001":1, "i2cTSL2561":1, "moistureSensor":1, "vcnl4010Distance":1, "vl6180xDistance":1,"BLEShellyDoor":1,"BLEShellyMotion":1, "BLERuuviAir":1}
_stateListToDevTypes["Temperature"]				= {"BLEKKMsensor":1,"DHT":1, "mlx90614":1, "BLERuuviTag":1, "BLERuuviAir":1, "BLEiBS01T":1, "BLEiBS01T":1, "BLEiBS03T":1, "BLEiBS03TP":1, "BLEminewS1TH":1, "BLEthermoBeacon":1, "BLEXiaomiMiVegTrug":1, "BLEXiaomiMiformaldehyde":1, "BLEXiaomiMiTempHumClock":1, "BLEXiaomiMiTempHumRound":1, "BLEXiaomiMiTempHumSquare":1, "BLEgoveeTempHum":1, "BLEminewS1Plus":1, "BLEinkBirdPool01B":1, "BLEaprilTHL":1, "BLEThermopro":1, "BLETempspike":1, "BLESatech":1, "BLEiSensor-TempHum":1, "BLEswitchbotTempHum":1, "BLEswitchbotTempHumCO2":1, "BLEswitchbotHumidifierEvap":1, "Wire18B20":1, "i2cTMP102":1, "i2cMCP9808":1, "i2cLM35A":1, "ccs811":1, "i2cT5403":1, "i2cMS5803":1, "i2cBMPxx":1, "i2cBMP280":1, "bmp388":1, "i2cSHT21":1, "i2cAM2320":1, "i2cBMExx":1, "bme680":1, "si7021":1, "tmp006":1, "tmp007":1, "tmp117":1, "max31865":1, "sensirionscd30":1, "sensirionscd40":1, "rPI":1, "rPI-Sensor":1}
_stateListToDevTypes["AmbientTemperature"]		= {"mlx90614":1, "tmp006":1, "tmp007":1, "BLEiBS03TP":1, "amg88xx":1}
_stateListToDevTypes["Humidity"]				= {"BLEKKMsensor":1,"BLEiBS01T":1, "DHT":1, "BLERuuviTag":1,  "BLERuuviAir":1, "BLEminewS1TH":1, "BLEXiaomiMiformaldehyde":1, "BLEthermoBeacon":1, "BLEXiaomiMiTempHumClock":1, "BLEXiaomiMiTempHumRound":1, "BLEXiaomiMiTempHumSquare":1, "BLEgoveeTempHum":1, "BLEminewS1Plus":1, "BLEaprilTHL":1, "BLEThermopro":1, "BLESatech":1, "BLEiSensor-TempHum":1, "BLEswitchbotTempHum":1, "BLEswitchbotTempHumCO2":1, "BLEswitchbotHumidifierEvap":1, "i2cSHT21":1, "i2cAM2320":1, "i2cBMExx":1, "bme680":1, "si7021":1,  "sensirionscd30":1, "sensirionscd40":1}
_stateListToDevTypes["CO2"]						= {"BLERuuviAir":1, "sensirionscd30":1, "sensirionscd40":1, "sgp30":1, "mhzCO2":1, "ccs811":1, "BLEswitchbotTempHumCO2":1}
_stateListToDevTypes["Pressure"]				= {"BLERuuviTag":1,  "BLERuuviAir":1,  "BLEiBS01T":1, "i2cT5403":1, "i2cMS5803":1, "i2cBMPxx":1, "i2cBMP280":1, "bmp388":1, "i2cBMExx":1, "bme680":1 }
_stateListToDevTypes["VOC"]						= {"BLERuuviAir":1, "sgp30":1, "sgp40":1, "ccs811":1, "bmp388":1}
_stateListToDevTypes["AirQuality"]				= {"bme680":1}
_stateListToDevTypes["Formaldehyde"]			= {"BLEXiaomiMiformaldehyde":1 }
_stateListToDevTypes["rpiAndBeacon"]			= {"beacon":1, "rPI":1}
_stateListToDevTypes["rpiAndSensorAndBeacon"]	= {"beacon":1, "rPI":1, "rPI-Sensor":1}
_stateListToDevTypes["rpiAndSensor"]			= {"rPI":1, "rPI-Sensor":1}
_stateListToDevTypes["rPI"]						= {"rPI":1}
_stateListToDevTypes["beacon"]					= {"beacon":1}
_stateListToDevTypes["BLEconnect"]				= {"BLEconnect":1}
_stateListToDevTypes["beaconOn"]				= {"BLEiSensor-onOff":1, "BLEmeeblue-on":1, "BLEiSensor-on":1, "BLEiSensor-RemoteKeyFob":1, "BLEswitchbotMotion":1, "BLEswitchbotMMWaveMotion":1, "BLEswitchbotContact":1}
_stateListToDevTypes["beaconSensorStates"]		= {"BLERuuviTag":1,  "BLERuuviAir":1, "BLEmeeblue-on":1, "BLEthermoBeacon":1, "BLEiBS03T":1, "BLEmyBLUEt":1, "BLEiBS03TP":1, "BLEiBS01T":1, "BLEblueradio":1, "BLEminewS1TH":1, "BLEXiaomiMiTempHumClock":1, "BLEXiaomiMiformaldehyde":1, "BLEXiaomiMiTempHumRound":1, "BLEXiaomiMiTempHumSquare":1, "BLEgoveeTempHum":1, "BLEminewAcc":1, "BLEminewS1Plus":1, "BLEinkBirdPool01B":1, "BLEaprilAccel":1, "BLEaprilTHL":1, "BLEThermopro":1, "BLETempspike":1, "BLEiBS03RG":1, "BLEiBS01RG":1, "BLEiBS01":1, "BLESatech":1, "BLEiSensor-onOff":1, "BLEiSensor-on":1, "BLEiSensor-RemoteKeyFob":1, "BLEiSensor-TempHum":1, "BLEswitchbotTempHum":1, "BLEswitchbotTempHumCO2":1, "BLEswitchbotMotion":1, "BLEswitchbotMMWaveMotion":1, "BLEswitchbotContact":1}
_stateListToDevTypes["rpiAndBeaconAndBLEconnect"] = {"beacon":1, "rPI":1, "BLEconnect":1}
_stateListToDevTypes["accelerationVectorDelta"]	 = {"BLERuuviTag":1,"BLEminewAcc":1,"BLEminewS1Plus":1,"BLEKKMsensor":1,"BLEaprilAccel":1,"BLEiBS03RG":1,"BLEiBS01RG":1,"BLESatech":1}
_stateListToDevTypes["accelerationX"]	 		= {"BLERuuviTag":1,"BLEminewAcc":1,"BLEminewS1Plus":1,"BLEKKMsensor":1,"BLEaprilAccel":1,"BLEiBS03RG":1,"BLEiBS01RG":1,"BLESatech":1}
_stateListToDevTypes["accelerationY"]	 		= {"BLERuuviTag":1,"BLEminewAcc":1,"BLEminewS1Plus":1,"BLEKKMsensor":1,"BLEaprilAccel":1,"BLEiBS03RG":1,"BLEiBS01RG":1,"BLESatech":1}
_stateListToDevTypes["accelerationZ"]	 		= {"BLERuuviTag":1,"BLEminewAcc":1,"BLEminewS1Plus":1,"BLEKKMsensor":1,"BLEaprilAccel":1,"BLEiBS03RG":1,"BLEiBS01RG":1,"BLESatech":1}
_stateListToDevTypes["accelerationTotal"]	 	= {"BLERuuviTag":1,"BLEminewAcc":1,"BLEminewS1Plus":1,"BLEKKMsensor":1,"BLEaprilAccel":1,"BLEiBS03RG":1,"BLEiBS01RG":1,"BLESatech":1}
_stateListToDevTypes["accelerationXYZMaxDelta"]	 = {"BLERuuviTag":1,"BLEminewAcc":1,"BLEminewS1Plus":1,"BLEKKMsensor":1,"BLEaprilAccel":1,"BLEiBS03RG":1,"BLEiBS01RG":1,"BLESatech":1}
_stateListToDevTypes["accelerationXYZMaxDelta"]	 = {"BLERuuviTag":1,"BLEminewAcc":1,"BLEminewS1Plus":1,"BLEKKMsensor":1,"BLEaprilAccel":1,"BLEiBS03RG":1,"BLEiBS01RG":1,"BLESatech":1}
_stateListToDevTypes["PM25"]	 				= {"BLERuuviAir":1}
_stateListToDevTypes["NOx"]	 					= {"BLERuuviAir":1}
# PM 1.0 / 4.0 / 10 + Illuminance arrive only with Ruuvi data format E1 (BT5 extended adv)
_stateListToDevTypes["PM1"]	 					= {"BLERuuviAir":1}
_stateListToDevTypes["PM4"]	 					= {"BLERuuviAir":1}
_stateListToDevTypes["PM10"] 					= {"BLERuuviAir":1}
_stateListToDevTypes["onOffDisplayStatus"]		= {"INPUTRotarySwitchAbsolute":1, "INPUTRotarySwitchIncremental":1, "INPUTcoincidence":1, "INPUTgpio-1":1, "INPUTgpio-26":1, "INPUTgpio-4":1, "INPUTgpio-8":1, "INPUTpulse":1, "INPUTtouch-1":1, "INPUTtouch-12":1, "INPUTtouch-16":1, "INPUTtouch-4":1, "OUTPUTgpio-1":1, "OUTPUTgpio-1-ONoff":1, "OUTPUTgpio-10":1, "OUTPUTgpio-26":1, "OUTPUTgpio-4":1, "OUTPUTi2cRelay":1, "OUTPUTswitchbotCurtain":1, "OUTPUTswitchbotCurtain3":1, "OUTPUTswitchbotRelay":1, "OUTPUTxWindows":1}
_stateListToDevTypes["humidityMode"]			= {"BLEswitchbotHumidifierEvap":1}
_stateListToDevTypes["overHumidifyProtection"]	= {"BLEswitchbotHumidifierEvap":1}
_stateListToDevTypes["childLock"]	 			= {"BLEswitchbotHumidifierEvap":1}
_stateListToDevTypes["tankRemoved"]	 			= {"BLEswitchbotHumidifierEvap":1}
_stateListToDevTypes["tiltedAlert"]	 			= {"BLEswitchbotHumidifierEvap":1}
_stateListToDevTypes["filterMissing"]	 		= {"BLEswitchbotHumidifierEvap":1}
_stateListToDevTypes["MeterBound"]	 			= {"BLEswitchbotHumidifierEvap":1}
_stateListToDevTypes["waterLevel"]	 			= {"BLEswitchbotHumidifierEvap":1}
_stateListToDevTypes["filterRunTime"]	 		= {"BLEswitchbotHumidifierEvap":1}
_stateListToDevTypes["targetHumidity"]	 		= {"BLEswitchbotHumidifierEvap":1}



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
