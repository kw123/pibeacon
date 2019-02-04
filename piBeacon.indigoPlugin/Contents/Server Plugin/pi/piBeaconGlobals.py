#!/usr/bin/env python
# -*- coding: utf-8 -*-
   
## do 
# sys.path.append(os.getcwd())
# import  piBeaconGlobals as G
# then ref the variables as G.xxx
# they will be valid across all imported modules if included.
#
homeDir				= "/home/pi/pibeacon/"
homeDir0			= "/home/pi/"
logDir				= "/run/user/1000/pibeacon/"
program				= "undefined"
debug				= 1
ipAddress			= ""
passwordOfServer	= ""
userIdOfServer		= ""
authentication		= "digest"
ipOfServer			= ""
portOfServer		= ""
myPiNumber			= ""
lastAliveSend		= 0.
lastAliveSend2		= 0.
tStart				= 0.
ipConnection		= 0.
lastAliveEcho		= 0
actionDict			= {}
sensorWasBad		= False
badCount0			= 0
badCount0			= 0
badCount1			= 0
badCount2			= 0
badCount3			= 0
badCount4			= 0
badCount5			= 0
badCount5			= 0
badCount6			= 0
badCount7			= 0
badCount8			= 0
badCount9			= 0
sendToIndigoSecs	= 90
deltaChangedSensor	= 5
networkStatus		= "no"	 # "no" = no network what so ever / "local" =only local can't find anything else/ "inet" = internet yes, indigo no / "indigoLocal" = indigo not internet / "indigoInet" = indigo with internet
ntpStatus			= "not started" #	/ "started, working" / "started, not working" / "temp disabled" / "stopped, after not working"
i2cAddress			=0
minSendDelta		=20
sensorLoopWait		=2
sensorRefreshSecs	=20
displayEnable		=0
deltaX				={}
magOffset			={}
magDivider			={}
magResolution		={}
magGain				=""
accelerationGain	=""
declination			={}
enableCalibration	={}
offsetTemp			={}
threshold			={}
useRTC				="init"
networkType			="fullIndigo"
rebootCommand		= "reboot now"
useNetwork			= ["", "fullIndigo", "indigo"]
expectedIPnumberOfRPI =""
wifiType			="normal"
eth0Enabled			= False
wifiEnabled			= False
wifiOFF				= "ON"
shutDownPinOutput	= -1
enableMuxI2C		= -1
enableMuxBus		= ""
IndigoOrSocket		= "indigo"
indigoInputPORT		= 0

BeaconUseHCINo		="-1"
BLEconnectUseHCINo	="-1"
last_masterStart	=""

ACTIONS={"LS":"ls",
		 "REBOOT":		   "sudo reboot",
		 "SHUTDOWN":	   "sudo shutdown -h now",
		 "REBOOTFORCE":	   "sudo sync;sync;sudo reboot -f"}
		 
programFiles=[			"beaconloop",
						"master",
						"INPUTgpio",
						"INPUTRotatarySwitch",
						"INPUTRotataryPulseSwitch",
						"INPUTtouch12",
						"INPUTtouch16",
						"installLibs",
						"mysensors",
						"myprogram",
						"receiveGPIOcommands",
						"myoutput",
						"simplei2csensors",
						"BLEconnect",
						"BLEsensor",
						"setGPIO",
						"playsound",
						"checkSystemLOG",
						"copyToTemp"]

specialOutputList=[		"display",
						"myoutput",
						"setmcp4725",
						"setPCF8591dac",
						"spiMCP3008",
						"setTEA5767",
						"neopixel",
						"sunDial",
						"setStepperMotor",
						"neopixelClock",
						"OUTPUTgpio"]

specialSensorList =[ 	"amg88xx",
						"as726x",
						"APDS9960",
						"bme680",
						"bno055" ,
						"ccs811",
						"DHT",
						"hmc5883L",
						"lsm303",
						"l3g4200",
						"mag3110",
						"mlx90614",
						"mhzI2C",
						"mhzSERIAL",
						"as3935",
						"si7021",
						"tmp006",
						"tmp007",
						"Wire18B20",
						"max31865",
						"ina219",
						"ina3221",
						"launchpgm",
						"max31865",
						"mpu6050",
						"mpu9255",
						"rainSensorRG11",
						"sgp30",
						"pmairquality",
						"vl503l0xDistance",
						"vcnl4010Distance",
						"vl6180xDistance",
						"ultrasoundDistance"]

parameterFileList  =[	"patterns",
						"beacon_parameters",
						"parameters"]

timeZones =[]
for ii in range(-12,13):
	if ii<0:
		timeZones.append("/Etc/GMT+" +str(abs(ii)))
	else:
		timeZones.append("/Etc/GMT-"+str(ii))
		
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
