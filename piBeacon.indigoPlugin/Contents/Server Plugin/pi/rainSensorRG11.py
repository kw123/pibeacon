#!/usr/bin/env python
# -*- coding: utf-8 -*-
# by Karl Wachs
# mar 2 2016
# version 0.95
##
##   read GPIO INPUT and send http to indigo with data if pulses detected
#

##

import  sys, os, subprocess, copy
import  time,datetime
import  json
import  RPi.GPIO as GPIO  

sys.path.append(os.getcwd())
import  piBeaconUtils   as U
import  piBeaconGlobals as G
G.program = "rainSensorRG11"
GPIO.setmode(GPIO.BCM)


def readParams():
    global sensor, sensors
    global gpioIn , gpioSW1 ,gpioSW2, gpioSW5, gpioSWP, cyclePower, sensorMode
    global ON, off
    global oldRaw, lastRead
    global switchToLowerSensitive, switchToHigherSensitive, bucketSize
    global status
    try:
        restart = False


        inp,inpRaw,lastRead2 = U.doRead(lastTimeStamp=lastRead)
        if inp == "": return
        if lastRead2 == lastRead: return
        lastRead  = lastRead2
        if inpRaw == oldRaw: return
        oldRaw     = inpRaw


        oldSensors        = sensors

        U.getGlobalParams(inp)
        if "sensors"            in inp : sensors =              (inp["sensors"])
        if "debugRPI"           in inp:  G.debug=             int(inp["debugRPI"]["debugRPISENSOR"])

        if sensor not in sensors:
            U.toLog(0,  "no "+ G.program+" sensor defined, exiting",doPrint=True)
            exit()

        sens= sensors[sensor]
        #print "sens:", sens
        found ={str(ii):{"RISING":0,"FALLING":0,"BOTH":0 } for ii in range(100)}
        for devId in sens:
            sss= sens[devId]
            if "gpioIn"                    not in sss: continue
            if "gpioSW5"                   not in sss: continue
            if "gpioSW2"                   not in sss: continue
            if "gpioSW1"                   not in sss: continue
            if "gpioSWP"                   not in sss: continue
            if "sensorMode"                not in sss: continue
            
            cyclePower  = sss["cyclePower"] != "0"

            if gpioIn != -1 and gpioIn != int(sss["gpioIn"]):
                restart = True
                U.toLog(0,  "gpios channel changed, need to restart",doPrint=True)
                U.restartMyself(param="", reason=" new gpioIn",doPrint=True)
                return 

            if gpioSWP != int(sss["gpioSWP"]):
                gpioSWP = int(sss["gpioSWP"])
                GPIO.setup(gpioSWP, GPIO.OUT)
                GPIO.output(gpioSWP, off)
            if gpioSW1 != int(sss["gpioSW1"]):
                gpioSW1 = int(sss["gpioSW1"])
                GPIO.setup(gpioSW1, GPIO.OUT)
            if gpioSW2 != int(sss["gpioSW2"]):
                gpioSW2 = int(sss["gpioSW2"])
                GPIO.setup(gpioSW2, GPIO.OUT)
            if gpioSW5 != int(sss["gpioSW5"]):
                gpioSW5 = int(sss["gpioSW5"])
                GPIO.setup(gpioSW5, GPIO.OUT)
            
            print status
            switchToLowerSensitive["checkIfIsRaining"]  = int(sss["TimeSwitchSensitivityRainToHigh"])
            switchToLowerSensitive["highSensitive"]     = int(sss["TimeSwitchSensitivityHighToMed"])
            switchToLowerSensitive["medSensitive"]      = int(sss["TimeSwitchSensitivityMedToLow"])
            
            switchToHigherSensitive["lowSensitive"]     = int(sss["TimeSwitchSensitivityLowToMed"])
            switchToHigherSensitive["medSensitive"]     = int(sss["TimeSwitchSensitivityMedToHigh"])
            switchToHigherSensitive["highSensitive"]    = int(sss["TimeSwitchSensitivityHighToRain"])
                
            if gpioIn != int(sss["gpioIn"]):
                gpioIn  = int(sss["gpioIn"])
                GPIO.setup(gpioIn,  GPIO.IN, pull_up_down=GPIO.PUD_UP)
                GPIO.add_event_detect(gpioIn, GPIO.FALLING,     callback=FALLING, bouncetime=200)  
                if sss["sensorMode"] != "dynamic":  setModeTo("checkIfIsRaining")

            if sensorMode != sss["sensorMode"]:
                if sss["sensorMode"] != "dynamic":
                    sendShortStatus(rainMsg["checkIfIsRaining"])
                    lastModeSwitch= time.time()
                setModeTo(sss["sensorMode"],force=True)

            sensorMode                                  = sss["sensorMode"]



            
    except  Exception, e:
        U.toLog(-1, u"in Line '%s' has error='%s'" % (sys.exc_traceback.tb_lineno, e),doPrint=True)
                

def setupSensors():

        U.toLog(0, "starting setup GPIOs ",doPrint=True)

        ret=subprocess.Popen("modprobe w1-gpio" ,shell=True,stdout=subprocess.PIPE,stderr=subprocess.PIPE).communicate()
        if len(ret[1]) > 0:
            U.toLog(-1, "starting GPIO: return error "+ ret[0]+"\n"+ret[1],doPrint=True)
            return False

        ret=subprocess.Popen("modprobe w1_therm",shell=True,stdout=subprocess.PIPE,stderr=subprocess.PIPE).communicate()
        if len(ret[1]) > 0:
            U.toLog(-1, "starting GPIO: return error "+ ret[0]+"\n"+ret[1],doPrint=True)
            return False

        return True
 
def FALLING(gpio):  
    global sensor, sensors
    global gpioIn , gpioSW1 ,gpioSW2, gpioSW5
    global startTimer, lastEventStarted
    global lastModeSwitch
    global switchToLowerSensitive, switchToHigherSensitive, bucketSize
    global status
    global simpleCount 
    global rainMsg
    global sensorMode
    
    if gpio != gpioIn: return 
    time.sleep(0.05)
    simpleCount +=1
    gpioStatus = GPIO.input(gpioIn)
    U.toLog(1,  "gpio"+str(gpio)+ " "+ str(gpioStatus)+"  "+str(simpleCount)+ " since last %4.2f"%(time.time() - startTimer) )
    if time.time() - startTimer < 0.1: return  
    startTimer = time.time()
    if time.time() - lastModeSwitch < 1: return 
    U.toLog(1, "accepted  currentMode "+ status["currentMode"], doPrint=True)


    newRainTime  = max(0.001, time.time() - lastEventStarted)
    lastEventStarted = time.time()
    
    if sensorMode == "checkIfIsRaining" : 
        sendShortStatus(rainMsg["highSensitive"])
        U.writeRainStatus(status)
        return 


    if status["currentMode"]  == "checkIfIsRaining": 
        if sensorMode == "dynamic":
            setModeTo("highSensitive", force=True)
            sendShortStatus(rainMsg["highSensitive"])
            U.writeRainStatus(status)
            return 

    
    bucket = bucketSize[status["currentMode"] ]
    accumBuckets(bucket)
    U.toLog(1,status["currentMode"] +"  "+str(bucket)+"  "+ str(newRainTime) , doPrint=True )

    if sensorMode =="dynamic": 

        if status["currentMode"]  == "highSensitive":
            if   newRainTime < switchToLowerSensitive["highSensitive"]: 
                 if status["values"]["buckets"] > 0: checkIfMSGtoBeSend(force =True)
                 if setModeTo("medSensitive"):
                    sendShortStatus(rainMsg["medSensitive"])
            elif newRainTime >  switchToHigherSensitive["highSensitive"]: 
                 if status["values"]["buckets"] > 0: checkIfMSGtoBeSend(force =True)
                 if setModeTo("checkIfIsRaining"):
                    sendShortStatus(rainMsg["checkIfIsRaining"])

        elif status["currentMode"]  == "medSensitive":
            if   newRainTime <  switchToLowerSensitive["medSensitive"]: 
                 if status["values"]["buckets"] > 0: checkIfMSGtoBeSend(force =True)
                 if setModeTo("lowSensitive"):
                  sendShortStatus(rainMsg["lowSensitive"])
            elif newRainTime >  switchToHigherSensitive["medSensitive"]: 
                 if status["values"]["buckets"] > 0: checkIfMSGtoBeSend(force =True)
                 if setModeTo("highSensitive"):
                    sendShortStatus(rainMsg["highSensitive"])

        elif status["currentMode"]  == "lowSensitive":
            if   newRainTime >  switchToHigherSensitive["lowSensitive"]: 
                 if status["values"]["buckets"] > 0: checkIfMSGtoBeSend(force =True)
                 if setModeTo("medSensitive"):
                    sendShortStatus(rainMsg["medSensitive"])
            
            
        
    U.writeRainStatus(status)
    return 


def setModeTo(newMode, force = False):
    global lastModeSwitch, minTimeBetweenModeSwitch
    global status

    U.toLog(0, " try to set new mode  "+newMode+ " from "+status["currentMode"]+"  tt - lastModeSwitch: "+str(time.time() - lastModeSwitch) ,doPrint=True )
    if (time.time() - lastModeSwitch < minTimeBetweenModeSwitch) and not force: 
        return False
        
    U.toLog(0, " setting mode to: "+newMode+ ";   from "+status["currentMode"] ,doPrint=True)
    
    if status["currentMode"] != newMode or force:
        setSwitch(newMode)
        status["lastMode"]     = status["currentMode"]
        status["currentMode"]  = newMode
        lastModeSwitch         = time.time()
        return True

    return False

def setSwitch(newMode):
    global gpioIn , gpioSW1 ,gpioSW2, gpioSW5, gpioSWP, cyclePower
    global ON, off
    if cyclePower:
        GPIO.output(gpioSWP, ON)
        time.sleep(0.1)
    if   newMode =="checkIfIsRaining":
        GPIO.output(gpioSW5, ON)
        GPIO.output(gpioSW2, off)
        GPIO.output(gpioSW1, off)
    elif newMode =="lowSensitive":
        GPIO.output(gpioSW5, off)
        GPIO.output(gpioSW2, off)
        GPIO.output(gpioSW1, off)
    elif newMode =="medSensitive":
        GPIO.output(gpioSW5, off)
        GPIO.output(gpioSW2, off)
        GPIO.output(gpioSW1, ON)
    elif newMode =="highSensitive":
        GPIO.output(gpioSW5, off)
        GPIO.output(gpioSW2, ON)
        GPIO.output(gpioSW1, off)
    if cyclePower:
        time.sleep(1)
        GPIO.output(gpioSWP, off)
        time.sleep(1)
    return


def checkIfDownGradedNeeded():
    global lastModeSwitch, lastDownGradeCheck, checkForDowngradeEvery, lastEventStarted
    global minTimeBetweenModeSwitch
    global sensorMode
    global status
    
    if time.time() - lastDownGradeCheck < checkForDowngradeEvery:    return 
    if time.time() - lastModeSwitch     < minTimeBetweenModeSwitch:  return 
    lastRainTime = time.time()- lastEventStarted 
    if lastRainTime < 5:                                             return 

    if sensorMode == "dynamic": 
        if   status["currentMode"] == "lowSensitive" and lastRainTime > switchToHigherSensitive["lowSensitive"]:
            if setModeTo("medSensitive"):
                sendShortStatus(rainMsg["medSensitive"])
                lastModeSwitch= time.time()
        elif status["currentMode"] == "medSensitive" and lastRainTime > switchToHigherSensitive["medSensitive"]:
             if setModeTo("highSensitive"):
                sendShortStatus(rainMsg["highSensitive"])
                lastModeSwitch= time.time()
        elif status["currentMode"] == "highSensitive" and lastRainTime > switchToHigherSensitive["highSensitive"]:
            if setModeTo("checkIfIsRaining"):
                sendShortStatus(rainMsg["checkIfIsRaining"])
                lastModeSwitch= time.time()
    else:
        if   lastRainTime > switchToHigherSensitive[sensorMode]:
                sendShortStatus(rainMsg["checkIfIsRaining"])
                lastModeSwitch= time.time()
        
    lastDownGradeCheck = time.time()
    return



def accumBuckets(bucket):
    global status
    status["values"]["buckets"]   += bucket
    status["values"]["nMes"]      += 1
    status["values"]["lastBucket"] = bucket
    status["values"]["lastMes"]    = time.time()
    return
    
def calcRates():
    status["values"]["bucketsTotal"] += status["values"]["buckets"]
    deltaTime                         = time.time() -  status["values"]["startMes"]
    rainRate                          = (status["values"]["buckets"] / max(0.01,deltaTime)) *3600  # per hour
    U.writeRainStatus(status)
    return rainRate, status["values"]["bucketsTotal"], deltaTime

def resetMes():
    status["values"]["buckets"]    = 0
    status["values"]["startMes"]   = time.time()
    status["values"]["lastBucket"] = 0
    status["values"]["lastMes"]    = 0

def resetValues():
    status["values"]["buckets"]    = 0
    status["values"]["startMes"]   = time.time()
    status["values"]["lastBucket"] = 0
    status["values"]["lastMes"]    = 0
    status["values"]["bucketsTotal"] = 0
    U.writeRainStatus(status)


            
def checkIfMSGtoBeSend(force =False):
    global lastCalcCheck, checkForMsgEvery
    if time.time()- lastCalcCheck < checkForMsgEvery and not force: return 
    lastCalcCheck = time.time()
    
    rate, totalRain, measurentTime = calcRates()
    resetMes()
    data={"sensors":{sensor:{}}}
    for devId in sensors[sensor]: 
        if rate ==0:
            rainLevel = rainMsg["checkIfIsRaining"]
        else:
            rainLevel = rainMsg[status["currentMode"]]
        data["sensors"][sensor][devId] = {"rainRate": rate, "totalRain": totalRain, "measurentTime":measurentTime,"mode":sensorMode,"sensitivity":status["currentMode"],"rainLevel":rainLevel}
    U.sendURL(data,wait=False)


            
def checkIfRelayON():
    global lastRelayONCheck
    global gpioIn, gpioSWP, ON, off
    global lastEventStarted
    maxONTime = 40
    if time.time()- lastRelayONCheck < 10: return 
    if time.time()- lastEventStarted < maxONTime: return 
    gpioStatus = GPIO.input(gpioIn)
    if gpioStatus == 0:
        GPIO.output(gpioSWP, ON)
        time.sleep(0.5)
        GPIO.output(gpioSWP, off)
        time.sleep(0.5)
        if status["currentMode"] == "checkIfIsRaining":
            U.toLog(-1, "resetting device in \"check if raining mode\", signal relay is ON for > "+str(maxONTime)+"secs: %d"%( time.time()- lastEventStarted)+"  to enable to detect new rain" ,doPrint=True)
        else:
            U.toLog(-1, "hanging? resetting device, signal relay is on for > "+str(maxONTime)+"secs: "+str( time.time()- lastEventStarted)+"  current Status"+status["currentMode"] ,doPrint=True)
        lastEventStarted = time.time()
    lastRelayONCheck = time.time()
       



        
def sendShortStatus(level):
    global sensorMode, status
    data={"sensors":{sensor:{}}}
    for devId in sensors[sensor]: 
        data["sensors"][sensor][devId] = {"rainLevel":level,"mode":sensorMode,"sensitivity":status["currentMode"] }
    U.sendURL(data,wait=False)
    return
  
  
global sensors
global oldParams
global oldRaw,  lastRead
global gpioIn , gpioSW1 ,gpioSW2, gpioSW5, gpioSWP, cyclePower, sensorMode
global lastModeSwitch, minTimeBetweenModeSwitch
global switchToLowerSensitive, switchToHigherSensitive, bucketSize
global startTimer, lastEventStarted
global lastDirection
global values
global status
global simpleCount 
global lastDownGradeCheck, checkForDowngradeEvery, lastCalcCheck
global lastCalcCheck, checkForMsgEvery
global rainMsg
global ON, off
global lastRelayONCheck

###################### init #################
    
minTimeBetweenModeSwitch = 3
lastDirection            = 99
startTimer               = 0
lastEventStarted         = 0 
lastModeSwitch           = 0
simpleCount              = 0
switchToLowerSensitive   = {"checkIfIsRaining":0,        "highSensitive":1,     "medSensitive":1,      "lowSensitive":99999999}  # time between signals;  switch from xx to next higher bucket capacity = lower sinsititvity 
switchToHigherSensitive  = {"checkIfIsRaining":99999999, "highSensitive":10,    "medSensitive":10,     "lowSensitive":10}   # time between signals;  switch from xx to next lower bucket capacity  if time between signals is > secs eg medSensitive to highSensitive
bucketSize               = {"highSensitive":0.0001*25.4,  "medSensitive":0.001*25.4,   "lowSensitive":0.01*25.4} # in inches --> mm
rainMsg                  = {"checkIfIsRaining":0,"highSensitive":1,  "medSensitive":2,   "lowSensitive":3}
gpioIn                   = -1
gpioSW1                  = -1
gpioSW2                  = -1
gpioSW5                  = -1
gpioSWP                  = -1
sensorMode               = "dynamic"
cyclePower               = True
ON                       = False
off                      = True

restart                  = False
lastRead                 = 0
oldRaw                   = ""
status                   = {"values":{"startMes":0, "buckets":0, "bucketsTotal":0, "nMes":0, "lastBucket":0},"currentMode":"checkIfIsRaining","lastMode":""}
checkForDowngradeEvery   = 10
checkForMsgEvery         = 55
lastRelayONCheck         = 0


myPID       = str(os.getpid())
U.killOldPgm(myPID,G.program+".py")# old old instances of myself if they are still running


sensor            = G.program
sensors           ={}
loopCount         = 0

U.toLog(-1, "starting "+G.program+" program",doPrint=True)

print "1", status["currentMode"]
ret = U.readRainStatus()
print "2", status["currentMode"]
if ret != {}: status = ret
readParams()
print "3", status["currentMode"]
setModeTo(status["currentMode"], force = True)
U.writeRainStatus(status)
if status["currentMode"] == "checkIfIsRaining": sendShortStatus(rainMsg["checkIfIsRaining"])
print "4", status["currentMode"]



# check if everything is installed
for i in range(100):
    if not setupSensors(): 
        time.sleep(10)
        if i%50==0: U.toLog(-1,"sensor libs not installed, need to wait until done",doPrint=True)
    else:
        break    
        

G.lastAliveSend     = time.time()
# set alive file at startup


if U.getIPNumber() > 0:
    U.toLog(-1," sensors no ip number  exiting ", doPrint =True)
    time.sleep(10)
    exit()

quick  = 0

G.tStart            = time.time() 
lastRead            = time.time()
shortWait           = 1
lastDownGradeCheck  = 0
lastCalcCheck       = 0 



while True:
    try:
        tt= time.time()
        
        if loopCount %10 ==0:
    
            if time.time()- lastRead > 5:
                readParams()
                lastRead = time.time()
                if U.checkResetFile(G.program):
                    resetValues()
                    checkIfMSGtoBeSend(force=True)

            checkIfRelayON()

            checkIfDownGradedNeeded()
            checkIfMSGtoBeSend()


            if loopCount%60==0:
                    U.echoLastAlive(G.program)
            
        if restart:
            U.restartMyself(param="", reason=" new definitions",doPrint=True)


        loopCount+=1
        time.sleep(shortWait)
    except  Exception, e:
        U.toLog(-1, u"in Line '%s' has error='%s'" % (sys.exc_traceback.tb_lineno, e),doPrint=True)
        time.sleep(5.)


sys.exit(0)
