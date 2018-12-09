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

ACTIONS={"LS":"ls",
		 "REBOOT":		   "sudo reboot",
		 "SHUTDOWN":	   "sudo shutdown -h now",
		 "REBOOTFORCE":	   "sudo sync;sync;sudo reboot -f"}
		 
programFiles=[			"ultrasoundDistance",
						"beaconloop",
						"master",
						"INPUTgpio",
						"INPUTtouch12",
						"INPUTtouch16",
						"installLibs",
						"setGPIO",
						"mysensors",
						"myprogram",
						"playsound",
						"display",
						"receiveGPIOcommands",
						"myoutput",
						"launchpgm",
						"execcommand",
						"setmcp4725",
						"setPCF8591dac",
						"DHT",
						"Wire18B20",
						"spiMCP3008",
						"simplei2csensors",
						"BLEconnect",
						"BLEsensor",
						"setTEA5767",
						"apds9960",
						"ina219",
						"ina3221",
						"tmp006",
						"si7021",
						"as726x",
						"l3g4200",
						"bno055",
						"bme680",
						"pmairquality",
						"amg88xx",
						"sgp30",
						"ccs811",
						"mhz-I2C",
						"mhz-SERIAL",
						"mag3110",
						"hmc5883L",
						"rainSensorRG11",
						"mpu9255",
						"lsm303",
						"mlx90614",
						"as3935",
						"mpu6050",
						"neopixel",
						"neopixelClock",
						"vcnl4010Distance",
						"vl6180xDistance",
						"checkSystemLOG",
						"vl503l0xDistance",
						"copyToTemp",
						"OUTPUTgpio"]
theSpecialSensorList =[ "ultrasoundDistance",
						"vl503l0xDistance",
						"vcnl4010Distance",
						"vl6180xDistance",
						"i2cAPDS9960",
						"l3g4200",
						"bno055" ,
						"hmc5883L",
						"mag3110",
						"lsm303",
						"mlx90614",
						"as3935",
						"si7021",
						"tmp006",
						"ina219",
						"ina3221",
						"as726x",
						"mpu6050",
						"amg88xx",
						"rainSensorRG11",
						"sgp30",
						"ccs811",
						"mhz-I2C",
						"mhz-SERIAL",
						"bme680",
						"pmairquality",
						"launchpgm",
						"mpu9255"]
parameterFileList  =[	"patterns",
						"beacon_parameters",
						"parameters"]
						
