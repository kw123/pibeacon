#!/usr/bin/env python
# -*- coding: utf-8 -*-


""" 

 vcnl40xx  ToF range finder program

"""


import sys, os, time, json, datetime,subprocess,copy
import smbus

sys.path.append(os.getcwd())
import  piBeaconUtils   as U
import  piBeaconGlobals as G
G.program = "vcnl4010Distance"
import  displayDistance as DISP

# ===========================================================================
# read params
# ===========================================================================

#################################        
def readParams():
    global sensorList, sensors, logDir, sensor,  sensorRefreshSecs, dynamic, mode, deltaDist,displayEnable
    global output, sensorActive, timing, tof, distanceUnits
    global actionDistanceOld, actionShortDistance, actionShortDistanceLimit, actionLongDistance, actionLongDistanceLimit
    global distanceOffset, distanceMax
    global oldRaw, lastRead
    try:

        inp,inpRaw,lastRead2 = U.doRead(lastTimeStamp=lastRead)
        if inp == "": return
        if lastRead2 == lastRead: return
        lastRead   = lastRead2
        if inpRaw == oldRaw: return
        oldRaw     = inpRaw


        externalSensor=False
        sensorList=[]
        sensorsOld= copy.copy(sensors)

        U.getGlobalParams(inp)
          
        if "sensorList"         in inp:  sensorList=             (inp["sensorList"])
        if "sensors"            in inp:  sensors =               (inp["sensors"])
        if "distanceUnits"      in inp:  distanceUnits=          (inp["distanceUnits"])
        
        if "output"             in inp:  output=                 (inp["output"])
   
 
        if sensor not in sensors:
            U.logger.log(30, "40xx Distance  is not in parameters = not enabled, stopping vl6180xDistance.py" )
            exit()
            
 
        sensorChanged = doWeNeedToStartSensor(sensors,sensorsOld,sensor)


        if sensorChanged != 0: # something has changed
            if os.path.isfile(G.homeDir+"temp/"+sensor+".dat"):
                os.remove(G.homeDir+"temp/"+sensor+".dat")
                
        dynamic = False
        deltaDist={}
        for devId in sensors[sensor]:
            deltaDist[devId]  = 0.1
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

            try:
                if "deltaDist" in sensors[sensor][devId]: 
                    deltaDist[devId]= float(sensors[sensor][devId]["deltaDist"])/100.
            except:
                pass
            try:
                if "dUnits" in sensors[sensor][devId] and sensors[sensor][devId]["dUnits"] !="":
                    distanceUnits = sensors[sensor][devId]["dUnits"]
            except  Exception, e:
                pass

            try:
                if "actionShortDistance" in sensors[sensor][devId]:         actionShortDistance = (sensors[sensor][devId]["actionShortDistance"])
            except:                                                         actionShortDistance = ""

            try:
                if "actionMediumDistance" in sensors[sensor][devId]:        actionMediumDistance = (sensors[sensor][devId]["actionMediumDistance"])
            except:                                                         actionMediumDistance = ""

            try:
                if "actionLongDistance" in sensors[sensor][devId]:          actionLongDistance = (sensors[sensor][devId]["actionLongDistance"])
            except:                                                         actionLongDistance = ""

            try:
                if "actionShortDistanceLimit" in sensors[sensor][devId]:    actionShortDistanceLimit = float(sensors[sensor][devId]["actionShortDistanceLimit"])
            except:                                                         actionShortDistanceLimit = -1

            try:
                if "actionLongDistanceLimit" in sensors[sensor][devId]:     actionLongDistanceLimit = float(sensors[sensor][devId]["actionLongDistanceLimit"])
            except:                                                         actionLongDistanceLimit = -1

            try:
                if True:                                                    maxCurrent = 8
                if "maxCurrent" in sensors[sensor][devId]:                  maxCurrent = int(sensors[sensor][devId]["maxCurrent"])
            except:                                                         maxCurrent = 8
            if devId not in distanceOffset:
                    distanceOffset[devId] = 2000
                    distanceMax[devId]    = int(5000*(maxCurrent/2.))

            #print sensorChanged, sensorActive, distanceMax
            if sensorChanged == 1:
                if not sensorActive:
                    U.logger.log(30,"==== Start ranging =====")
                    tof = VCNL40xx(address=0x13,maxCurrent=maxCurrent)
            sensorActive = True
            
            
        if sensorChanged == -1:
            U.logger.log(30, "==== stop  ranging =====")
            exit()


    except  Exception, e:
        U.logger.log(30, u"in Line {} has error={}".format(sys.exc_traceback.tb_lineno, e))




#################################
def doWeNeedToStartSensor(sensors,sensorsOld,selectedSensor):
    if selectedSensor not in sensors:    return -1
    if selectedSensor not in sensorsOld: return 1

    for devId in sensors[selectedSensor] :
            if devId not in sensorsOld[selectedSensor] :            return 1
            for prop in sensors[sensor][devId] :
                if prop not in sensorsOld[selectedSensor][devId] :  return 1
                if sensors[selectedSensor][devId][prop] != sensorsOld[selectedSensor][devId][prop]:
                    return 1
   
    for devId in sensorsOld[selectedSensor]:
            if devId not in sensors[selectedSensor] :               return 1
            for prop in sensorsOld[selectedSensor][devId] :
                if prop not in sensors[selectedSensor][devId] :     return 1

    return 0




# The MIT License (MIT)
#
# Copyright (c) 2016 Adafruit Industries
#
# Permission is hereby granted, free of charge, to any person obtaining a copy
# of this software and associated documentation files (the "Software"), to deal
# in the Software without restriction, including without limitation the rights
# to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
# copies of the Software, and to permit persons to whom the Software is
# furnished to do so, subject to the following conditions:
#
# The above copyright notice and this permission notice shall be included in all
# copies or substantial portions of the Software.
#
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
# IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
# FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
# AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
# LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
# OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
# SOFTWARE.
import time
import smbus


# Common VCNL40xx constants:
VCNL40xx_ADDRESS          = 0x13
VCNL40xx_COMMAND          = 0x80
VCNL40xx_PRODUCTID        = 0x81
VCNL40xx_IRLED            = 0x83
VCNL40xx_AMBIENTPARAMETER = 0x84
VCNL40xx_AMBIENTDATA      = 0x85
VCNL40xx_PROXIMITYDATA    = 0x87
VCNL40xx_PROXIMITYADJUST  = 0x8A
VCNL40xx_3M125            = 0
VCNL40xx_1M5625           = 1
VCNL40xx_781K25           = 2
VCNL40xx_390K625          = 3
VCNL40xx_MEASUREAMBIENT   = 0x10
VCNL40xx_MEASUREPROXIMITY = 0x08
VCNL40xx_AMBIENTREADY     = 0x40
VCNL40xx_PROXIMITYREADY   = 0x20

# VCBL4000 constants:
VCNL4000_SIGNALFREQ       = 0x89

# VCNL4010 constants:
VCNL4010_PROXRATE         = 0x82
VCNL4010_INTCONTROL       = 0x89
VCNL4010_INTSTAT          = 0x8E
VCNL4010_MODTIMING        = 0x8F
VCNL4010_INT_PROX_READY   = 0x80
VCNL4010_INT_ALS_READY    = 0x40



class VCNL40xx():

    def __init__(self,address=VCNL40xx_ADDRESS,maxCurrent=10):
        self.bus = smbus.SMBus(1)
        self.address = address
        
        self.bus.write_byte_data(self.address, VCNL4010_INTCONTROL, 0x0)
        # VCNL4010 address, 0x13(19)
        # Select command register, 0x80(128)
        #		0xFF(255)	Enable ALS and proximity measurement, LP oscillator
        self.bus.write_byte_data(0x13, VCNL40xx_COMMAND, 0xff)# 1<<1|1<<2)
        # VCNL4010 address, 0x13(19)
        # set ir-led current 
        self.bus.write_byte_data(0x13, VCNL40xx_IRLED,maxCurrent) #  0-20 = 0- 200mA
        # Select proximity rate register, 0x82(130)
        self.bus.write_byte_data(0x13, VCNL4010_PROXRATE,1<<1|1) # = 00000011 = 16 measuremnts per second
        # VCNL4010 address, 0x13(19)
        # Select ambient light register, 0x84(132)
        self.bus.write_byte_data(0x13, VCNL40xx_AMBIENTPARAMETER, 1<<7|1<<6|1<<5|1<<4|1<<3|1<<2) # 1 1110000 = cont. conversion + 10 samples per second + 1000 = auto offset


    def read_Data(self, timeout_sec=1):
        try:
            data = self.bus.read_i2c_block_data(0x13, 0x85, 4)
            luminance = data[0] * 256 + data[1]
            distance  = data[2] * 256 + data[3] 
            
            return   distance, luminance, data
            #return self._device.readU16BE(VCNL40xx_AMBIENTDATA)
        except  Exception, e:
            U.logger.log(30, u"in Line {} has error={}".format(sys.exc_traceback.tb_lineno, e))
        return "","",[]


       
#################################
def readSensor():
    global sensor, sensors,  tof, badSensor, distanceOffset, distanceMax
    global actionDistanceOld, actionShortDistance, actionShortDistanceLimit, actionMediumDistance, actionMediumDistanceLimit, actionLongDistance, actionLongDistanceLimit
    distance   = "badSensor"
    luminance  = ""
    try:
        for ii in range(4):
            distance0,luminance, data = tof.read_Data()
            if distance0 != "":
                distance = distance0 - distanceOffset[devId]
                distance = max(0,distanceMax[devId]- distance)
                #print "in getsensor", data,luminance, distance0, distance,  "min=",distanceOffset[devId], "max=",distanceMax[devId]
                badSensor = 0
                #print " bf action test ", actionShortDistance, actionMediumDistance, actionLongDistance
                if actionShortDistance !="":
                    if actionDistanceOld !="short"  and distance <= actionShortDistanceLimit:
                        if actionDistanceOld != "short":
                            os.system(actionShortDistance)
                            actionDistanceOld ="short"
                        
                if actionMediumDistance !="":
                    if actionDistanceOld !="medium"  and distance >  actionShortDistanceLimit and distance < actionLongDistanceLimit:
                        if actionDistanceOld != "medium":
                            os.system(actionMediumDistance)
                            actionDistanceOld ="medium"
                        
                if actionLongDistance !="":
                    if actionDistanceOld !="long"    and distance >=  actionLongDistanceLimit:
                        if actionDistanceOld != "long":
                            os.system(actionLongDistance)
                            actionDistanceOld ="long"
                                
                return  distance, luminance #  return in cm/lux
            time.sleep(0.02)
        if badSensor >3: return "badSensor"
    except  Exception, e:
            U.logger.log(30, u"in Line {} has error={}".format(sys.exc_traceback.tb_lineno, e))
            U.logger.log(30, u"distance>>" + unicode(distance)+"<<")
    return distance  , luminance     





############################################
global distanceOffset, distanceMax, inpRaw
global sensor, sensors, first, tof, badSensor, sensorActive
global actionDistanceOld, actionShortDistance, actionShortDistanceLimit, actionMediumDistance, actionMediumDistanceLimit, actionLongDistance, actionLongDistanceLimit
global oldRaw,  lastRead
oldRaw                  = ""
lastRead                = 0
        

actionShortDistance         = ""
actionShortDistanceLimit    = 5.
actionMediumDistance        = ""
actionMediumDistanceLimit   = 10
actionLongDistance          = ""
actionLongDistanceLimit     = 20.
actionDistanceOld           = 0
distanceOffset              = {}
distanceMax                 = {}
first                       = False
loopCount                   = 0
sensorRefreshSecs           = 60
NSleep                      = 100
sensorList                  = []
sensors                     = {}
sensor                      = G.program
quick                       = False
lastMsg                     = 0
dynamic                     = False
mode                        = 0
display                     = "0"
output                      = {}
badSensor                   = 0
sensorActive                = False
loopSleep                   = 0.1

U.setLogging()

myPID       = str(os.getpid())
U.killOldPgm(myPID,G.program+".py")# kill old instances of myself if they are still running

if U.getIPNumber() > 0:
    time.sleep(10)
    exit()

# Create a VCNL4010/4000 instance.

readParams()


time.sleep(1)
lastRead = time.time()

U.echoLastAlive(G.program)

lastDist            = {}
lastData            = {}
lastTime            = {}
maxDeltaSpeed       = 40. # = mm/sec
lastSend            = 0
lastDisplay         = 0
maxDeltaSpeed       = 40. # = mm/sec
lastRead            = time.time()
G.lastAliveSend     = time.time() -1000
lastLux   = -999999
lastLux2  = 0
tt0 = time.time()
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
                distance,lux =readSensor()
                data["sensors"][sensor] = {devId:{}}

                if distance =="badSensor":
                    U.logger.log(30," bad sensor")
                    data["sensors"][sensor][devId]["distance"]="badSensor"
                    U.sendURL(data)
                    lastDist[devId] =-100.
                    continue
                else:
                    data["sensors"][sensor][devId]["distance"] = distance

                if lux !="": 
                            data["sensors"][sensor][devId]["lux"] =lux
                            lastLux2 = lastLux
                            lastLux  = float(lux)
                else:
                            data["sensors"][sensor][devId]["lux"] =lastLux


                dist = float(distance)
                delta=  dist - lastDist[devId]
                deltaT =  max(tt   - lastTime[devId],0.01)
                speed  =  delta / deltaT
                deltaN= abs(delta) / max (0.5,(dist+lastDist[devId])/2.)
                if (  
                    ( deltaN > deltaDist[devId] ) or  
                    ( (tt - G.lastAliveSend) > abs(sensorRefreshSecs))  or 
                    ( quick )  or 
                    ( speed > maxDeltaSpeed )  or 
                    ( abs(lastLux2 - lastLux)/ max(1.,lastLux2 + lastLux) > deltaDist[devId] )  ): # 10%
                        data["sensors"][sensor][devId]["speed"] = speed
                        G.lastAliveSend = tt
                        U.sendURL(data)
                lastDist[devId]  = dist
                lastTime[devId]  = tt

                if displayEnable =="1" and  ((deltaN > 0.05  and  tt - lastDisplay >1.)   or  tt - G.lastAliveSend >10. or quick):
                    lastDisplay = tt
                    DISP.displayDistance(dist, sensor, sensors, output, distanceUnits)
                    U.logger.log(10, unicode(dist)+"  "+unicode(deltaDist) )   
                    #print datetime.datetime.now().strftime("%Y%m%d-%H:%M:%S"),sensor, dist , deltaDist   
        quick = False
        loopCount +=1
        
        U.makeDATfile(G.program, data)

        quick = U.checkNowFile(G.program)                

        U.echoLastAlive(G.program)

        if loopCount %20 ==0 and not quick:
            if tt - lastRead > 5.:  
                readParams()
                lastRead = tt
        time.sleep(1)
        #print "end of loop", loopCount
    except  Exception, e:
        U.logger.log(30, u"in Line {} has error={}".format(sys.exc_traceback.tb_lineno, e))
        time.sleep(5.)
try: 	G.sendThread["run"] = False; time.sleep(1)
except: pass
sys.exit(0)
        
        
        
 