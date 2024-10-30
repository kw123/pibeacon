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
logDir				= "/var/log/"
program				= "undefined"
debug				= 0
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
sendToIndigoSecs	= 90 # send update at least every xx seconds
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
magFregRate			=""
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
eth0Active 			= False
wifiActive 			= False
wifiEth				= {"eth0":{"on":"dontChange", "useIP":"use"}, "wlan0":{"on":"dontChange", "useIP":"use"}}
wifiEthOld			= {"eth0":{"on":"dontChange", "useIP":"use"}, "wlan0":{"on":"dontChange", "useIP":"use"}}
getBatteryMethod	= "batch"
shutDownPinOutput	= -1
enableMuxI2C		= -1
enableMuxBus		= ""
IndigoOrSocket		= "socket"
indigoInputPORT		= 0
switchedToWifi 		= 0
wlan0Packets		= ""
eth0Packets			= ""
wlan0PacketsOld		= ""
eth0PacketsOld		= ""
packetsTime			= 0
packetsTimeOld		= 0
sundialActive		= ""
BeaconUseHCINo		= "-1"
BLEconnectUseHCINo	= "-1"
last_masterStart	= ""
wifiID				= ""
sendThread			= {}
rebootIfNoMessagesSeconds = 99999999999
ipOfRouter			= ""
enableRebootCheck	= "restartLoop"
pythonVersion		= 2
compressRPItoPlugin = 2000
ipNumberRpiStatic	= False
ipNumberPi			= ""
networkRestartTries = 0
lastVcode			= ""
apiKey				= ""
rpiIPNumber			= ""
restartMaxLogfile	= 100000
restartLogfileName	= logDir+"beaconloop.restarts"
# 	UUID: Battery Service           (0000180f-0000-1000-8000-00805f9b34fb)  -- gatttols char-read-uuid 2A19

"""
import sys
if sys.version[0] != "3":
	sys.path.append("/home/pi/.local/lib/python2.7/site-packages/")
else:
	sys.path.append("/home/pi/.local/lib/python3.7/site-packages/")
"""

ACTIONS={"LS":"ls",
		 "REBOOT":		   "sudo reboot",
		 "SHUTDOWN":	   "sudo shutdown -h now",
		 "REBOOTFORCE":	   "sudo sync;sync;sudo reboot -f"}
		 
programFiles=[			"beaconloop",
						"master",
						"installLibs",
						"mysensors",
						"myprogram",
						"receiveCommands",
						"myoutput",
						"simplei2csensors",
						"BLEconnect",
						"playsound",
						"checkSystemLOG",
						"copyToTemp"]

specialOutputList=[		"display",
						"myoutput",
						"setmcp4725",
						"setPCF8591dac",
						"spiMCP3008",
						"setTEA5767",
						"neopixel2",
						"neopixel3",
						"sundial",
						"setStepperMotor",
						"neopixelClock",
						"OUTPUTgpio"]

specialSensorList =[ 	"amg88xx",
						"INPUTgpio",
						"INPUTpulse",
						"INPUTRotarySwitchIncremental",
						"INPUTRotarySwitchAbsolute",
						"INPUTtouch12",
						"INPUTtouch16",
						"lidar360",
						"mlx90640",
						"as726x",
						"APDS9960",
						"bme680",
						"bmp388",
						"bno055" ,
						"PCF8591",
						"ADS1x15",
						"MAX44009",
						"ccs811",
						"DHT",
						"hmc5883L",
						"lsm303",
						"l3g4200",
						"mag3110",
						"mlx90614",
						"mhzCO2",
						"as3935",
						"si7021",
						"tmp006",
						"tmp007",
						"tmp117",
						"Wire18B20",
						"max31865",
						"ina219",
						"ina3221",
						"launchpgm",
						"max31865",
						"mpu6050",
						"mpu9255",
						"rainSensorRG11",
						"moistureSensor",
						"sensirionscd30",
						"sgp30",
						"sgp40",
						"pmairquality",
						"vl503l0xDistance",
						"vcnl4010Distance",
						"vl6180xDistance",
						"DF2301Q",
						"ultrasoundDistance"]
isBLEdirectSensorDevice =["BLEdirectMiTempHumRound"]
## not used anymore BLEsensorTypes =      ["BLEmyBLUEt","BLERuuviTag", "BLEiBS01", "BLEiBS01T",  "BLEiBS01RG", "BLEiBS02", "BLEiBS03","BLEiBS03G","BLEiBS03T","BLEiBS03TP", "BLEiBS03RG", "BLEminewE8", "BLEiSensor-TempHum", "BLEiSensor-onOff", "BLEiSensor-on", "BLEiSensor-RemoteKeyFob","BLESatech"]
parameterFileList   =[	"beacon_parameters",
						"parameters",
						"knownBeaconTags"]

python2SensorsMustDo	= ["neopixel2"]
python3SensorsMustDo	= ["tmp117","lidar360","moistureSensor", "sensirionscd30","neopixel3","vl503l0xDistance","vl503l1xDistance","vcnl4010Distance","vl6180xDistance","ultrasoundDistance","pmairquality","DF2301Q"]
python3SensorsCanDo		= [	"ADS1x15", 
							"simplei2csensors",
							"INPUTgpio","INPUTpulse",
							"bme680",
							"mhzCO2",
							"DHT",
							"sgp30","sgp40",
							"lsm303",
							"display",
							"Wire18B20"]
python3Apps				= ["beaconloop", "BLEconnect", "copyToTemp", "receiveCommands"]

appDoesNotExist			= ["INPUTcoincidence"]

loggerSet = False

apiKey = ""

global logging, logger

timeZones =[]
for ii in range(-12,13):
	if ii<0:
		timeZones.append("/Etc/GMT+{}".format(abs(ii)))
	else:
		timeZones.append("/Etc/GMT-{}".format(ii))

timeZone		 = "99 none"
timeZones[12+12] = "Pacific/Auckland"
timeZones[11+12] = "Pacific/Pohnpei"
timeZones[10+12] = "Australia/Melbourne"
timeZones[9+12]	 = "Asia/Tokyo"
timeZones[8+12]	 = "Asia/Shanghai"
timeZones[7+12]	 = "Asia/Saigon"
timeZones[6+12]	 = "Asia/Dacca"
timeZones[5+12]	 = "Asia/Karachi"
timeZones[4+12]	 = "Asia/Dubai"
timeZones[3+12]	 = "Europe/Moscow"
timeZones[2+12]	 = "Europe/Helsinki"
timeZones[1+12]	 = "Europe/Amsterdam"
timeZones[0+12]	 = "Europe/London"
timeZones[-1+12] = "Atlantic/Cape_Verde"
timeZones[-2+12] = "Atlantic/South_Georgia"
timeZones[-3+12] = "America/Buenos_Aires"
timeZones[-4+12] = "America/Puerto_Rico"
timeZones[-5+12] = "US/Eastern"
timeZones[-6+12] = "US/Central"
timeZones[-7+12] = "US/Mountain"
timeZones[-8+12] = "US/Pacific"
timeZones[-9+12] = "US/Alaska"
timeZones[-10+12] = "Pacific/Honolulu"
timeZones[-11+12] = "US/Samoa"
