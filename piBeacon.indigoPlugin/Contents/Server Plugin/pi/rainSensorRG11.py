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
        found ={str(ii):{"RISING":0,"GPIOchanged":0,"BOTH":0 } for ii in range(100)}
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
                powerOFF(calledFrom="read")
            if gpioSW1 != int(sss["gpioSW1"]):
                gpioSW1 = int(sss["gpioSW1"])
                GPIO.setup(gpioSW1, GPIO.OUT)
            if gpioSW2 != int(sss["gpioSW2"]):
                gpioSW2 = int(sss["gpioSW2"])
                GPIO.setup(gpioSW2, GPIO.OUT)
            if gpioSW5 != int(sss["gpioSW5"]):
                gpioSW5 = int(sss["gpioSW5"])
                GPIO.setup(gpioSW5, GPIO.OUT)
            switchToLowerSensitive["checkIfIsRaining"]  = int(sss["TimeSwitchSensitivityRainToMayBeRaining"])
            switchToLowerSensitive["maybeRain"]         = int(sss["TimeSwitchSensitivityMayBeRainingToHigh"])
            switchToLowerSensitive["highSensitive"]     = int(sss["TimeSwitchSensitivityHighToMed"])
            switchToLowerSensitive["medSensitive"]      = int(sss["TimeSwitchSensitivityMedToLow"])
            
            switchToHigherSensitive["lowSensitive"]     = int(sss["TimeSwitchSensitivityLowToMed"])
            switchToHigherSensitive["medSensitive"]     = int(sss["TimeSwitchSensitivityMedToHigh"])
            switchToHigherSensitive["highSensitive"]    = int(sss["TimeSwitchSensitivityHighToAnyRain"])
                
            if gpioIn != int(sss["gpioIn"]):
                gpioIn  = int(sss["gpioIn"])
                GPIO.setup(gpioIn,  GPIO.IN, pull_up_down=GPIO.PUD_UP)
                GPIO.add_event_detect(gpioIn, GPIO.FALLING,     callback=GPIOchanged, bouncetime=200)  
                if sss["sensorMode"] != "dynamic":  setModeTo("checkIfIsRaining", calledFrom="readParams1")

            if sensorMode != sss["sensorMode"]:
                if sss["sensorMode"] != "dynamic":
                    sendShortStatus(rainMsg["checkIfIsRaining"])
                    lastModeSwitch= time.time()
                setModeTo(sss["sensorMode"],force=True, calledFrom="readParams2")

            sensorMode                                  = sss["sensorMode"]
            sendMSGEverySecs                            = float(sss["sendMSGEverySecs"])

            powerON(calledFrom="read")


            
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
 
def GPIOchanged(gpio):  
    global sensor, sensors
    global gpioIn , gpioSW1 ,gpioSW2, gpioSW5, cyclePower
    global lastClick,lastClick2, lastEventStarted, lastEventStarted2, lastCheckIfisRaining
    global lastModeSwitch
    global switchToLowerSensitive, switchToHigherSensitive, bucketSize
    global status
    global simpleCount 
    global rainMsg
    global ON, off
    global sensorMode
    global ProgramStart
    
    if gpio != gpioIn: return 
    U.toLog(1,  "into GPIOchanged, GPIO in: " +str(GPIO.input(gpioIn)), doPrint=True)
    if time.time() - ProgramStart < 20: return 
    
    time.sleep(0.05)
    simpleCount +=1
    gpioStatus = GPIO.input(gpioIn)==ON
    U.toLog(1,  "gpio"+str(gpio)+ " "+ str(gpioStatus)+"  "+str(simpleCount)+ " since last %4.2f"%(time.time() - lastClick) )
    if time.time() - lastClick < 0.1: return  
    lastClick2 = lastClick
    lastClick  = time.time()
    if time.time() - lastModeSwitch < 1: return 
    U.toLog(1, "accepted  currentMode "+ status["currentMode"], doPrint=True)


    newRainTime  = max(0.001, time.time()  - lastEventStarted)
    newRainTime2  = max(0.001, time.time() - lastEventStarted2)
    lastEventStarted2 = lastEventStarted
    lastEventStarted  = time.time()


    # static, shortcut to check if its rainging, will just send a msg, no rain amount 
    if sensorMode != "dynamic":
        if sensorMode == "checkIfIsRaining" : 
            if cyclePower:
                if time.time() - lastCheckIfisRaining > switchToLowerSensitive["checkIfIsRaining"] and switchToLowerSensitive["checkIfIsRaining"] >0:
                    lastCheckIfisRaining = time.time()
                    sendShortStatus(rainMsg["maybeRain"])
                    powerOFF(calledFrom="GPIOchanged0-0")
                    time.sleep(3)
                    powerON(calledFrom="GPIOchanged0-1")
                    return 
            lastCheckIfisRaining = time.time()
            sendShortStatus(rainMsg["medSensitive"])
            U.writeRainStatus(status)
            return 
        # calc amount of rain etc     
        bucket = bucketSize[status["currentMode"] ]
        accumBuckets(bucket)
        U.toLog(1,status["currentMode"] +"  "+str(bucket)+"  "+ str(newRainTime) , doPrint=True )
        U.writeRainStatus(status)



    # we are here because a the relay clicked.
    # start at checkIfIsRaining. if std: switch to maybe raining 
    #   if not start go to highSensitive immediately 
    # 
    # if maybe rain: next click must happen withing x secs, if not reset to checkIfRaining.  (ie 2.click in xx secs)
    #  if not go back to check if is raining 
    if sensorMode == "dynamic":
        if  status["currentMode"]  == "checkIfIsRaining":
            if time.time() - lastCheckIfisRaining > switchToLowerSensitive["checkIfIsRaining"] and switchToLowerSensitive["checkIfIsRaining"] >0:
                sendShortStatus(rainMsg["maybeRain"])
                powerOFF(calledFrom="GPIOchanged1-1")
                setModeTo("maybeRain", force=True, calledFrom="GPIOchanged1-1", powerCycle=False)
                time.sleep(5)
                lastClick = time.time()
                lastCheckIfisRaining = time.time()
                powerON(calledFrom="GPIOchanged1-1")
                U.writeRainStatus(status)
                return 
            ### this should only happen when switchToLowerSensitive["checkIfIsRaining"] ==0 
            lastCheckIfisRaining = time.time()
            setModeTo("highSensitive", force=True, calledFrom="GPIOchanged1-2")
            sendShortStatus(rainMsg["highSensitive"])
            U.writeRainStatus(status)
            return 

        if status["currentMode"]  == "maybeRain": 
            if time.time() - lastCheckIfisRaining > switchToLowerSensitive["maybeRain"] and switchToLowerSensitive["maybeRain"] >0:
                sendShortStatus(rainMsg["checkIfIsRaining"])
                powerOFF(calledFrom="GPIOchanged1-3")
                setModeTo("checkIfIsRaining", force=True, calledFrom="GPIOchanged1-3", powerCycle=False)
                time.sleep(5)
                lastCheckIfisRaining = time.time()
                lastClick = time.time() 
                powerON(calledFrom="GPIOchanged1-3")
                U.writeRainStatus(status)
                return 
            lastCheckIfisRaining = time.time()
            setModeTo("highSensitive", force=True, calledFrom="GPIOchanged2")
            sendShortStatus(rainMsg["highSensitive"])
            U.writeRainStatus(status)
            return 


        # calc amount of rain etc     
        bucket = bucketSize[status["currentMode"] ]
        accumBuckets(bucket)
        U.toLog(1,status["currentMode"] +"  "+str(bucket)+"  "+ str(newRainTime) , doPrint=True )


        if status["currentMode"]  == "highSensitive":
            if   newRainTime2 < switchToLowerSensitive["highSensitive"]: # require 3 clicks
                 if status["values"]["buckets"] > 0: checkIfMSGtoBeSend(force =True)
                 if setModeTo("medSensitive", calledFrom="GPIOchanged3"):
                    sendShortStatus(rainMsg["medSensitive"])
            elif newRainTime >  switchToHigherSensitive["highSensitive"]: # require 2 clicks
                 if status["values"]["buckets"] > 0: checkIfMSGtoBeSend(force =True)
                 if setModeTo("checkIfIsRaining", calledFrom="GPIOchanged4"):
                    sendShortStatus(rainMsg["checkIfIsRaining"])
                 lastModeSwitch= time.time()+switchToHigherSensitive["highSensitive"]

        elif status["currentMode"]  == "medSensitive":
            if   newRainTime2 <  switchToLowerSensitive["medSensitive"]: # require 3 clicks
                 if status["values"]["buckets"] > 0: checkIfMSGtoBeSend(force =True)
                 if setModeTo("lowSensitive", calledFrom="GPIOchanged5"):
                  sendShortStatus(rainMsg["lowSensitive"])
            elif newRainTime >  switchToHigherSensitive["medSensitive"]: # require 2 clicks
                 if status["values"]["buckets"] > 0: checkIfMSGtoBeSend(force =True)
                 if setModeTo("highSensitive", calledFrom="GPIOchanged6"):
                    sendShortStatus(rainMsg["highSensitive"])
                 lastModeSwitch= time.time()+switchToHigherSensitive["highSensitive"]

        elif status["currentMode"]  == "lowSensitive":
            if   newRainTime >  switchToHigherSensitive["lowSensitive"]: # require 2 clicks
                 if status["values"]["buckets"] > 0: checkIfMSGtoBeSend(force =True)
                 if setModeTo("medSensitive", calledFrom="GPIOchanged7"):
                    sendShortStatus(rainMsg["medSensitive"])
                 lastModeSwitch= time.time()+switchToHigherSensitive["medSensitive"]
            
            
        
    U.writeRainStatus(status)
    return 


def setModeTo(newMode, calledFrom="", powerCycle=True, force = False):
    global lastModeSwitch, minTimeBetweenModeSwitch
    global status, ProgramStart

    #if time.time() - ProgramStart < 20: return 

    U.toLog(0, "try to set new mode  "+newMode+ " from "+status["currentMode"]+"  tt - lastModeSwitch: "+str(time.time() - lastModeSwitch) +" called from: "+calledFrom,doPrint=True )
    if (time.time() - lastModeSwitch < minTimeBetweenModeSwitch) and not force: 
        return False
        
    U.toLog(0, "setting mode to: "+newMode+ ";   from currrentMode: "+status["currentMode"] ,doPrint=True)
    
    if status["currentMode"] != newMode or force:
        setSwitch(newMode, powerCycle=powerCycle)
        status["lastMode"]     = status["currentMode"]
        status["currentMode"]  = newMode
        lastModeSwitch         = time.time()
        return True

    return False

def setSwitch(newMode, powerCycle=True):
    global gpioIn , gpioSW1 ,gpioSW2, gpioSW5, gpioSWP, cyclePower
    global ON, off
    if cyclePower and powerCycle:
        powerOFF(calledFrom="setSwitch")
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
    if cyclePower and powerCycle:
        powerON(calledFrom="setSwitch")
        time.sleep(1)
    return


def checkIfDownGradedNeeded():
    global lastModeSwitch, lastDownGradeCheck, checkForDowngradeEvery, lastEventStarted, lastEventStarted2
    global minTimeBetweenModeSwitch
    global sensorMode
    global status, ProgramStart

    if time.time() - ProgramStart < 20: return 

    if time.time() - lastDownGradeCheck < checkForDowngradeEvery:    return 
    if time.time() - lastModeSwitch     < minTimeBetweenModeSwitch:  return 
    lastRainTime = time.time()- lastEventStarted 
    if lastRainTime < 5:                                             return 

    if sensorMode == "dynamic": 
        if   status["currentMode"] == "lowSensitive" and lastRainTime > switchToHigherSensitive["lowSensitive"]:
            if setModeTo("medSensitive", calledFrom="checkIfDownGradedNeeded1"):
                sendShortStatus(rainMsg["medSensitive"])
                lastModeSwitch= time.time()+switchToHigherSensitive["medSensitive"]
        elif status["currentMode"] == "medSensitive" and lastRainTime > switchToHigherSensitive["medSensitive"]:
             if setModeTo("highSensitive", calledFrom="checkIfDownGradedNeeded2"):
                sendShortStatus(rainMsg["highSensitive"])
                lastModeSwitch= time.time()+switchToHigherSensitive["highSensitive"]
        elif status["currentMode"] == "highSensitive" and lastRainTime > switchToHigherSensitive["highSensitive"]:
            if setModeTo("checkIfIsRaining", calledFrom="checkIfDownGradedNeeded3"):
                sendShortStatus(rainMsg["checkIfIsRaining"])
                lastModeSwitch= time.time()
                lastModeSwitch= time.time()+switchToHigherSensitive["highSensitive"]
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
    global lastCalcCheck, sendMSGEverySecs, ProgramStart, sensorMode
    if time.time()- lastCalcCheck < max( sendMSGEverySecs, switchToLowerSensitive[status["currentMode"]] ) and not force: return 
    if time.time() - ProgramStart < 20: return 
    lastCalcCheck = time.time()
    
    rate, totalRain, measurementTime = calcRates()
    resetMes()
    data={"sensors":{sensor:{}}}
    for devId in sensors[sensor]: 
        if rate ==0:
            rainLevel = rainMsg["checkIfIsRaining"]
        else:
            rainLevel = rainMsg[status["currentMode"]]
        data["sensors"][sensor][devId] = {"rainRate": rate, "totalRain": totalRain, "measurementTime":measurementTime,"mode":sensorMode,"sensitivity":status["currentMode"],"rainLevel":rainLevel}
    U.sendURL(data,wait=False)


            
def checkIfRelayON():
    global lastRelayONCheck
    global gpioIn, gpioSWP, ON, off, cyclePower
    global lastEventStarted, lastEventStarted2
    maxONTime = 40
    if time.time()- lastRelayONCheck < 10: return 
    if time.time()- lastEventStarted < maxONTime: return 
    gpioStatus = GPIO.input(gpioIn)==ON
    if gpioStatus:
        if cyclePower:
            powerCyleRelay()
            if status["currentMode"] == "checkIfIsRaining":
                U.toLog(-1, "resetting device in \"check if raining mode\", signal relay is ON for > "+str(maxONTime)+"secs: %d"%( time.time()- lastEventStarted)+"  to enable to detect new rain" ,doPrint=True)
            else:
                U.toLog(-1, "hanging? resetting device, signal relay is on for > "+str(maxONTime)+"secs: "+str( time.time()- lastEventStarted)+"  current Status"+status["currentMode"] ,doPrint=True)
            lastEventStarted = time.time()
        
    lastRelayONCheck = time.time()
       

def powerCyleRelay():
    global gpioSWP, ON, off
    powerOFF(calledFrom="powerCyleRelay")
    powerON(calledFrom="powerCyleRelay")


def powerON(calledFrom=""):
    global gpioSWP, ON, off
    GPIO.output(gpioSWP, off)
    time.sleep(0.5)

def powerOFF(calledFrom=""):
    global gpioSWP, ON, off
    GPIO.output(gpioSWP, ON)
    time.sleep(0.5)


        
def sendShortStatus(level):
    global sensorMode, status, ProgramStart, lastShortMsgSend, lastShortMsg
    if time.time() - ProgramStart < 20:    return 
    if time.time() - lastShortMsgSend < 5: return 
    data={"sensors":{sensor:{}}}
    for devId in sensors[sensor]: 
        data["sensors"][sensor][devId] = {"rainLevel":level,"mode":sensorMode,"sensitivity":status["currentMode"] }
    if lastShortMsg != data["sensors"][sensor]: 
        U.sendURL(data,wait=False)
        lastShortMsgSend = time.time()
    lastShortMsg = data["sensors"][sensor]
    return
  
  
global sensors
global oldParams
global oldRaw,  lastRead
global gpioIn , gpioSW1 ,gpioSW2, gpioSW5, gpioSWP, cyclePower, sensorMode
global lastModeSwitch, minTimeBetweenModeSwitch
global switchToLowerSensitive, switchToHigherSensitive, bucketSize
global lastClick,lastClick2, lastEventStarted, lastEventStarted2
global lastDirection
global values
global status
global simpleCount 
global lastDownGradeCheck, checkForDowngradeEvery, lastCalcCheck, lastCheckIfisRaining
global lastCalcCheck, sendMSGEverySecs
global rainMsg
global ON, off
global lastRelayONCheck
global ProgramStart
global lastShortMsgSend
global lastShortMsg

###################### init #################
    
uPmm                     = 25.4
minTimeBetweenModeSwitch = 10
lastDirection            = 99
lastClick                = 0
lastClick2               = 0
lastEventStarted         = 0 
lastEventStarted2        = 0
lastModeSwitch           = 0
simpleCount              = 0
switchToLowerSensitive   = {"checkIfIsRaining":0,        "maybeRain":0,   "highSensitive":1,            "medSensitive":1,           "lowSensitive":99999999 }  # time between signals;  switch from xx to next higher bucket capacity = lower sinsititvity 
switchToHigherSensitive  = {"checkIfIsRaining":99999999, "maybeRain":100, "highSensitive":100,          "medSensitive":100,         "lowSensitive":100       }  # time between signals;  switch from xx to next lower bucket capacity  if time between signals is > secs eg medSensitive to highSensitive
rainMsg                  = {"checkIfIsRaining":0,        "maybeRain":1,   "highSensitive":2,            "medSensitive":3,           "lowSensitive":4        }
bucketSize               = {"checkIfIsRaining":0,        "maybeRain":0,   "highSensitive":0.0001*uPmm,  "medSensitive":0.001*uPmm,  "lowSensitive":0.01*uPmm}  # in inches --> mm
gpioIn                   = -1 
gpioSW1                  = -1
gpioSW2                  = -1
gpioSW5                  = -1
gpioSWP                  = -1
sensorMode               = "dynamic"
cyclePower               = True
ON                       = False # for relay outoput 
off                      = True  # for relay outoput 

restart                  = False
lastRead                 = 0
oldRaw                   = ""
status                   = {"values":{"startMes":0, "buckets":0, "bucketsTotal":0, "nMes":0, "lastBucket":0},"currentMode":"checkIfIsRaining","lastMode":""}
checkForDowngradeEvery   = 10
sendMSGEverySecs         = 70
lastRelayONCheck         = 0
lastCheckIfisRaining     = 0 
lastDownGradeCheck       = 0
lastCalcCheck            = 0 
lastRead                 = time.time() +20
ProgramStart             = time.time() 
lastShortMsgSend         = 0
lastShortMsg             = {}

myPID       = str(os.getpid())
U.killOldPgm(myPID,G.program+".py")# old old instances of myself if they are still running

GPIO.setwarnings(False)

# check if everything is installed
for i in range(100):
    if not setupSensors(): 
        time.sleep(10)
        if i%50==0: U.toLog(-1,"sensor libs not installed, need to wait until done",doPrint=True)
    else:
        break    
if U.getIPNumber() > 0:
    U.toLog(-1," sensors no ip number  exiting ", doPrint =True)
    time.sleep(10)
    exit()

sensor            = G.program
sensors           ={}
loopCount         = 0

U.toLog(-1, "starting "+G.program+" program",doPrint=True)

ret = U.readRainStatus()
if ret != {}: status = ret
readParams()
setModeTo(status["currentMode"], force = True, calledFrom="main")
U.writeRainStatus(status)
if status["currentMode"] == "checkIfIsRaining": sendShortStatus(rainMsg["checkIfIsRaining"])

G.lastAliveSend     = time.time()


quick  = 0

G.tStart            = time.time() 
lastRead            = time.time()
shortWait           = 1


while True:
    try:
        tt= time.time()
        

        if status["currentMode"]  == "maybeRain": 
            if time.time() - lastCheckIfisRaining > switchToLowerSensitive["maybeRain"] and switchToLowerSensitive["maybeRain"] >0:
                lastCheckIfisRaining = time.time()
                setModeTo("checkIfIsRaining", force=True, calledFrom="loop check maybeRain")
                sendShortStatus(rainMsg["checkIfIsRaining"])
                U.writeRainStatus(status)

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
