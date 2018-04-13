#!/usr/bin/env python
# -*- coding: utf-8 -*-
# by Karl Wachs
# feb 5 2016
# version 0.9 
##
##  get sensor values and write the to a file in json format for later pickup, 
##  do it in a timed manner not to load the system, is every 1 seconds then 30 senods break
##

import  sys, os, time, json, datetime,subprocess,copy
import math

import RPi.GPIO as GPIO


GPIO.setmode(GPIO.BCM)
sys.path.append(os.getcwd())
import  piBeaconUtils   as U
import  piBeaconGlobals as G
import  displayDistance as DISP
G.program = "ultrasoundDistance"





# ===========================================================================
# read params
# ===========================================================================

#################################        
def readParams():
    global sensors, sensor,  sensorRefreshSecs, dynamic, mode, deltaDist,displayEnable
    global output
    global distanceUnits
    global oldRaw, lastRead
    try:

        inp,inpRaw,lastRead2 = U.doRead(lastTimeStamp=lastRead)
        if inp == "": return
        if lastRead2 == lastRead: return
        lastRead   = lastRead2
        if inpRaw == oldRaw: return
        oldRaw     = inpRaw

        sensorsOld= copy.copy(sensors)
       
        U.getGlobalParams(inp)
         
        if "sensors"                in inp:  sensors =           (inp["sensors"])
        if "distanceUnits"          in inp:  distanceUnits=      (inp["distanceUnits"])
        
        if "output"                 in inp:  output=             (inp["output"])
   
 
        if sensor not in sensors:
            U.toLog(-1, "ultrasound is not in parameters = not enabled, stopping ultrasoundDistance.py" )
            exit()
            
 
        sensorUp = U.doWeNeedToStartSensor(sensors,sensorsOld,sensor)


        if sensorUp != 0: # something has changed
            if os.path.isfile(G.homeDir+"temp/"+sensor+".dat"):
                os.remove(G.homeDir+"temp/"+sensor+".dat")

        if sensorUp == 1:
            for devId in sensors[sensor]:
                GPIO.setwarnings(False)
                gpioPin= int(sensors[sensor][devId]["gpioTrigger"])
                GPIO.setup(gpioPin,  GPIO.OUT)
                gpioPin= int(sensors[sensor][devId]["gpioEcho"])
                GPIO.setup(gpioPin,  GPIO.IN,  pull_up_down = GPIO.PUD_UP)
        if sensorUp == -1:
            pass
            # stop sensor
        dynamic = False
        deltaDist={}
        for devId in sensors[sensor]:
            try:
                xx = sensors[sensor][devId]["sensorRefreshSecs"].split("#")
                sensorRefreshSecs = int(xx[0]) 
                if sensorRefreshSecs  < 0: dynamic=True
                if len(xx)==2: 
                    try: mode = int(xx[1])
                    except: mode =0
                
            except:
                sensorRefreshSecs = 100    
                mode =0

            try:
                if "displayEnable" in sensors[sensor][devId]: 
                    displayEnable = sensors[sensor][devId]["displayEnable"]
            except:
                display = False    


            deltaDist[devId]  = 0.1
            try:
                if "deltaDist" in sensors[sensor][devId]: 
                    deltaDist[devId]= float(sensors[sensor][devId]["deltaDist"])/100.
            except:
                pass

            try:
                if "units" in sensors[sensor][devId]:
                    units= sensors[sensor][devId]["units"]
                    distanceUnits = units
            except  Exception, e:
                pass


    except  Exception, e:
        U.toLog(-1, u"in Line '%s' has error='%s'" % (sys.exc_traceback.tb_lineno, e))


#################################
def getultrasoundDistance(devId):
    global sensor,sensors , first
    try:
        echoPin    = int(sensors[sensor][devId]["gpioEcho"])  
        triggerPin = int(sensors[sensor][devId]["gpioTrigger"]) 
        GPIO.output(triggerPin, False)
        time.sleep(0.06)
        if first: time.sleep(10) ; first = False
        
        elapsed=[9999999.,9999999.,9999999.]
        badSensor=0
        for ii in range(3):
            time.sleep(0.01)
            # send pulse
            GPIO.output(triggerPin, True)
            time.sleep(0.0002)
            GPIO.output(triggerPin, False)

            start = time.time()
            # wait for echo to start
            if GPIO.input(echoPin)==1:
                badSensor+=1
                continue
            while GPIO.input(echoPin)==0:
                if time.time() - start > 0.01 : 
                    badSensor+=1
                    break
            start = time.time()

            #wait for echo to stop
            while GPIO.input(echoPin)==1:
                if time.time()-start > 0.035: # max range is 4m : 4*2/340 = 8/334 = 0.0239 , use some safety and set to 0.035
                    #print " overflow, skip" 
                    time.sleep(0.1)
                    break  # skip this measurement

            # delta is the round trip time
            elapsed[ii]=(time.time() - start)
            #print elapsed
        # pick medium value
        if badSensor > 1: return "badSensor"
        result = sorted(elapsed)[1]
        if result >  0.1: 
            #print "overflow"
            return "500.0" # set to max = 5 m
        #print "res= ",result 
        return  ("%7.2f"%(result * 17000.)).strip() # 17000 = 34000/2 ...  /2 due to round trip; 1 msec = 17 cm distance
    except  Exception, e:
            U.toLog(-1, u"in Line '%s' has error='%s'" % (sys.exc_traceback.tb_lineno, e))
    return ""        
 
 


 
#################################

             
global senors,sensorRefreshSecs,sensor, NSleep, ipAddress, dynamic, mode, deltaDist, first, displayEnable
global output, authentication
global distanceUnits
global oldRaw,  lastRead
oldRaw                  = ""
lastRead                = 0

distanceUnits               = "1.0"

actionShortDistance         = ""
actionShortDistanceLimit    = 5.
actionMediumDistance        = ""
actionMediumDistanceLimit   = 10
actionLongDistance          = ""
actionLongDistanceLimit     = 20.
actionDistanceOld           = 0

debug                       = 5
first                       = False
loopCount                   = 0
sensorRefreshSecs           = 60
NSleep                      = 100
sensors                     = {}
sensor                      = G.program
quick                       = False
lastMsg                     = 0
dynamic                     = False
mode                        = 0
display                     = "0"
output                      = {}
delta                       = 0
readParams()

myPID       = str(os.getpid())
U.killOldPgm(myPID,G.program+".py")# kill old instances of myself if they are still running

if U.getIPNumber() > 0:
    print " no ip number "
    time.sleep(10)
    exit()

print "ultrasound ip:"+ G.ipAddress


U.echoLastAlive(G.program)

lastDist            = {}
lastTime            = {}
lastData            = {}
lastSend            = 0
lastDisplay         = 0
maxDeltaSpeed       = 40. # = mm/sec
G.lastAliveSend     = time.time() -1000
while True:
    try:
        tt = time.time()
        data={}
        data["sensors"]     = {}
        if sensor in sensors:
            for devId in sensors[sensor]:
                if devId not in lastDist: 
                    lastDist[devId] =-500.
                    lastTime[devId] =0.
                dist =getultrasoundDistance(devId)
                if dist =="badSensor":
                    first=True
                    U.toLog(-1," bad sensor, sleeping for 10 secs")
                    data0={}
                    data0[sensor]={}
                    data0[sensor][devId]={}
                    data0[sensor][devId]["distance"]="badSensor"
                    data["sensors"]     = data0
                    U.sendURL(data)
                    lastDist[devId] =-100.
                    continue
                    
                data["sensors"]     = {sensor:{devId:{}}}
                dist   =  float(dist)
                delta  =  dist - lastDist[devId]
                deltaT =  max((tt   - lastTime[devId]),0.01)
                speed  =  delta / deltaT
                deltaN= abs(delta) / max (0.5,(dist+lastDist[devId])*2.)
                if delta > 400: 
                    G.lastAliveSend = tt
                else:
                    if ( (dynamic and ( deltaN > deltaDist[devId])) or 
                         (  (tt - abs(sensorRefreshSecs)) > G.lastAliveSend )   or 
                         ( quick )  or 
                         ( speed > maxDeltaSpeed)  ):
                        data["sensors"][sensor][devId]["distance"] = dist
                        data["sensors"][sensor][devId]["speed"]    = speed
                        U.sendURL(data)
                lastDist[devId]  = dist
                lastTime[devId]  = tt

                if displayEnable =="1" and ( (dynamic and ( deltaN > 0.02)) or (tt - lastDisplay >2.   or quick)) :
                    lastDisplay = tt
                    DISP.displayDistance(dist, sensor, sensors, output, distanceUnits)
                    
        if delta > 400: quick = True
        else:           quick = False
        
        loopCount +=1
        
        U.makeDATfile(G.program, data)

        quick = U.checkNowFile(G.program)                

        readParams()

        U.echoLastAlive(G.program)

        nLoops= max(sensorRefreshSecs*2, 2)
        #print loopCount, nLoops, mode
        for n in range(nLoops):
            if quick:               break
            if   mode == 0: time.sleep(0.45)
            elif mode == 1: time.sleep(0.2)
            elif mode == 2: time.sleep(0.0001)
            else:           time.sleep(1.)
            if n%15 == 14:  
                #print "read p"
                readParams()
                if n > max(abs(sensorRefreshSecs), 1)*2: break
        #print "end of loop", loopCount
    except  Exception, e:
        U.toLog(-1, u"in Line '%s' has error='%s'" % (sys.exc_traceback.tb_lineno, e))
        time.sleep(5.)
sys.exit(0)
