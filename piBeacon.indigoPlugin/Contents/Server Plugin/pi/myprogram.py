#!/usr/bin/python
# -*- coding: utf-8 -*-
# by Karl Wachs
# feb 5 2016
# version 0.9 
##
##  get sensor values and write the to a file in json format for later pickup, 
##  do it in a timed manner not to load the system, is every 1 seconds then 30 senods break
##

import  sys, os, time, json, datetime,subprocess,copy
sys.path.append(os.getcwd())
import  piBeaconUtils   as U
import  piBeaconGlobals as G

G.program = "myprogram"





# ===========================================================================
# getMyprogram
# ===========================================================================

def getMyprogram(sensor, data):
    """Collects readings for all devices of the given 'myprogram' sensor type, attempting to parse a per-device value payload into the data dict; devices whose value is empty are flagged via incrementBadSensor, and the updated data dict is returned (with the sensor entry removed if it ends up empty).

    Inputs:
        sensor (str): sensor type key to look up in the sensors dict
        data (dict): accumulator dict that collected sensor readings are added to
    Outputs:
        dict: the data dict updated with this sensor's per-device values
    """
    global sensors, sValues, displayInfo

    if sensor not in sensors : return data    
    try:
        data[sensor] ={}
        for devId in sensors[sensor]:
            if "freeParameter" in sensors[sensor][devId]: freeParameter = sensors[sensor][devId]["freeParameter"]
            else: freeParameter =""
            params = json.dumps({"devId":devId,"freeParameter":freeParameter})
            
            
            ## this is my program action "
            
            #print "getsensorvalue cmd to myprogra"+cmd
            v = "xxx"
            try:    v=json.loads(v)
            except: v={}
            #print "v:", v
            if v!={}:
                data[sensor][devId] = copy.copy(v)
                if devId in badSensors: del badSensors[devId]
            else:
                data= incrementBadSensor(devId,sensor,data)
    except  Exception as e:
        U.logger.log(30,"", exc_info=True)
    if sensor in data and data[sensor]=={}: del data[sensor]
    return data


def incrementBadSensor(devId,sensor,data,text="badSensor"):
    """Tracks repeated failures for a device by incrementing a counter and appending text in the global badSensors dict; once the failure count exceeds 2, it records the accumulated text under data[sensor][devId]["badSensor"] and clears the device's entry. Returns the updated data dict.

    Inputs:
        devId (str): device id whose failure count is tracked
        sensor (str): sensor type key under which to record the bad-sensor flag
        data (dict): data dict updated with the bad-sensor marker
        text (str): failure description text appended on each increment (default 'badSensor')
    Outputs:
        dict: the data dict, possibly annotated with a badSensor entry
    """
    global badSensors
    try:
        if devId not in badSensors:badSensors[devId] ={"count":0,"text":text}
        badSensors[devId]["count"] +=1
        badSensors[devId]["text"]  +=text
        #print badSensors
        if  badSensors[devId]["count"]  > 2:
            if sensor not in data: data={sensor:{devId:{}}}
            if devId not in data[sensor]: data[sensor][devId]={}
            data[sensor][devId]["badSensor"] = badSensors[devId]["text"]
            del badSensors[devId]
    except  Exception as e:
        U.logger.log(30,"", exc_info=True)
    return data 


        
# ===========================================================================
# sensor end
# ===========================================================================

 
# ===========================================================================
# read params
# ===========================================================================


def readParams():
        """Reads the latest parameter input from the plugin (via U.doRead), and if it is new and changed, applies global params, output, sensors and refresh interval to module globals and rebuilds the sensor list; exits the process if no 'myprogram' sensor is configured. Returns a boolean result code (always False here).

        Inputs:
            None.
        Outputs:
            bool: result code, False; may also call exit() if no myprogram sensor present
        """
        global sensorList, sensors, sendToIndigoSecs, sensorRefreshSecs
        global output
        global tempUnits, pressureUnits, distanceUnits
        global oldRaw, lastRead

        rCode= False

        inp, inpRaw, lastRead2 = U.doRead(lastTimeStamp=lastRead)
        if inp == "": return rCode
        if lastRead2 == lastRead: return rCode
        lastRead  = lastRead2
        if inpRaw == oldRaw: return rCode
        oldRaw     = inpRaw

        oldSensor  = sensorList
        sensorList = []
        sensorsOld = copy.copy(sensors)
        outputOld  = "{}".format(output)


        U.getGlobalParams(inp)
        if "output"               in inp: output=                  (inp["output"])
        if "sensors"              in inp: sensors =                (inp["sensors"])
        if "sensorRefreshSecs"    in inp: sensorRefreshSecs = float(inp["sensorRefreshSecs"])


        sensorList=""
        for sensor in sensors:
            sensorList+=sensor.split("-")[0]+","

        if sensorList.find("myprogram") ==-1:
            exit()

        return rCode




#################################
def checkIfAliveNeedsToBeSend():
    """Sends an alive/heartbeat signal to the plugin (via U.sendURL with sendAlive=True) if more than 330 seconds have elapsed since the last alive signal was sent.

    Inputs:
        None.
    Outputs:
        None: sends alive URL to plugin as a side effect; logs on exception
    """
    try:
        if time.time() - G.lastAliveSend> 330:  # do we have to send alive signal to plugin?
            U.sendURL(sendAlive=True )
    except  Exception as e:
        U.logger.log(30,"", exc_info=True)
    return


#################################
#################################
#################################
#################################
#################################
#################################
#################################
#################################
             
global sensorList, sensors,badSensors
global regularCycle
global oldRaw, lastRead
global sensorRefreshSecs


sensorRefreshSecs   = 90
oldRaw              = ""
lastRead            = 0
loopCount           = 0
sensorList          = []
sensors             = {}
authentication      = "digest"
quick               = False
output              = {}

readParams()

if U.getIPNumber() > 0:
    U.logger.log(30," myprogram no ip number  exiting ")
    time.sleep(10)
    exit()

U.setLogging()

myPID       = str(os.getpid())
U.killOldPgm(myPID,G.program+".py")# kill old instances of myself if they are still running

NSleep= int(sensorRefreshSecs)
if G.networkType  in G.useNetwork and U.getNetwork() == "off": 
    if U.getIPNumber() > 0:
        time.sleep(10)

eth0IP, wifi0IP, G.eth0Enabled,G.wifiEnabled = U.getIPCONFIG()


tt                  = time.time()
badSensors          = {}
lastData            = {}
lastMsg             = 0
lastAliveSend       = tt
G.tStart            = tt
lastregularCycle    = tt
lastRead            = tt
regularCycle        = True
lastData={}

while True:
    try:
        tt = time.time()
        data={}
        
        if regularCycle:
            if "myprogram"      in sensors: data = getMyprogram("myprogram", data)



        loopCount +=1
        
        delta =-1
        changed = 0
        if lastData=={}: 
            changed = 1
        else:
            for sens in data:
                if changed>0: break
                if sens not in lastData:
                    changed= 2
                    break
                for devid in data[sens]:
                    if changed>0: break
                    if devid not in lastData[sens]:
                        changed= 3
                        break
                    for devType in data[sens][devid]:
                        if changed>0: changed = 4
                        if devType not in lastData[sens][devid]:
                            changed= 5
                            break
                        try:
                            xxx = U.testBad( data[sens][devid][devType],lastData[sens][devid][devType], -1 )
                            if xxx > (G.deltaChangedSensor/100.): 
                                changed= xxx
                                break
                        except  Exception as e:
                            #print e
                            #print lastData[sens][dd]
                            #print data[sens][dd]
                            changed= 7
                            break
        if data !={} and (      changed >0 or   ( (tt-lastMsg) >  G.sendToIndigoSecs  or (tt-lastMsg) > 200  )       ):
            lastMsg = tt
            lastData=copy.copy(data)
            try:
                #U.logger.log(10, u"sending url: {}".format(data))
                U.sendURL({"sensors":data})
            except  Exception as e:
                U.logger.log(30,"", exc_info=True)
            time.sleep(0.05)

        quick = U.checkNowFile(G.program)                

        U.makeDATfile(G.program, data)
        U.echoLastAlive(G.program)


        tt= time.time()
        NSleep = int(sensorRefreshSecs)*2
        if tt- lastregularCycle > sensorRefreshSecs:
            regularCycle = True
            lastregularCycle  = tt

        for n in range(NSleep):
            if quick: break

            readParams()
            time.sleep(0.5)
            quick = U.checkNowFile(G.program)                
            if tt - lastRead > 5 :
                lastRead = tt
                checkIfAliveNeedsToBeSend()
    except  Exception as e:
        U.logger.log(30,"", exc_info=True)
        time.sleep(5.)
try: 	G.sendThread["run"] = False; time.sleep(1)
except: pass
sys.exit(0)
