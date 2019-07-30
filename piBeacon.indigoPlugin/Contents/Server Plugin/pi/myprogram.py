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
isys.path.append(os.getcwd())
import  piBeaconUtils   as U
import  piBeaconGlobals as G
G.program = "myprogram"





# ===========================================================================
# getMyprogram
# ===========================================================================

def getMyprogram(sensor, data):
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
    except  Exception, e:
        U.logger.log(30, u"in Line {} has error={}".format(sys.exc_traceback.tb_lineno, e))
    if sensor in data and data[sensor]=={}: del data[sensor]
    return data


def incrementBadSensor(devId,sensor,data,text="badSensor"):
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
    except  Exception, e:
        U.logger.log(30, u"in Line {} has error={}".format(sys.exc_traceback.tb_lineno, e))
    return data 


        
# ===========================================================================
# sensor end
# ===========================================================================

 
# ===========================================================================
# read params
# ===========================================================================


def readParams():
        global sensorList, sensors, sendToIndigoSecs, sensorRefreshSecs
        global output
        global tempUnits, pressureUnits, distanceUnits
        global oldRaw, lastRead

        rCode= False

        inp,inpRaw,lastRead2 = U.doRead(lastTimeStamp=lastRead)
        if inp == "": return rCode
        if lastRead2 == lastRead: return rCode
        lastRead  = lastRead2
        if inpRaw == oldRaw: return 
        oldRaw     = inpRaw

        oldSensor  = sensorList
        sensorList = []
        sensorsOld = copy.copy(sensors)
        outputOld  = unicode(output)


        U.getGlobalParams(inp)
        if "debugRPI"             in inp:  G.debug=             int(inp["debugRPI"]["debugRPISENSOR"])
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
    try:
        if time.time() - G.lastAliveSend> 330:  # do we have to send alive signal to plugin?
            U.sendURL(sendAlive=True )
    except  Exception, e:
        U.logger.log(30, u"in Line {} has error={}".format(sys.exc_traceback.tb_lineno, e))
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
if G.networkType  in G.useNetwork and U.getNetwork() == 1: 
    if U.getIPNumber() > 0:
        print datetime.datetime.now().strftime("%Y%m%d-%H:%M:%S")+" "+G.program+" no ip number working, giving up"
        time.sleep(10)
        exit()
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
                            xxx = U.testBad( data[sens][devid][devType],lastData[sens][devid][devType], xxx )
                            if xxx > (G.deltaChangedSensor/100.): 
                                changed= xxx
                                break
                        except  Exception, e:
                            #print e
                            #print lastData[sens][dd]
                            #print data[sens][dd]
                            changed= 7
                            break
#        print "changed", changed,     tt-lastMsg, G.sendToIndigoSecs ,  tt-lastMsg, G.deltaChangedSensor, data
        if data !={} and (      changed >0 or   ( (tt-lastMsg) >  G.sendToIndigoSecs  or (tt-lastMsg) > 200  )       ):
            lastMsg = tt
            lastData=copy.copy(data)
            try:
                #U.logger.log(10, u"sending url: "+unicode(data))
                U.sendURL({"sensors":data})
            except  Exception, e:
                U.logger.log(30, u"in Line {} has error={}".format(sys.exc_traceback.tb_lineno, e))
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
    except  Exception, e:
        U.logger.log(30, u"in Line {} has error={}".format(sys.exc_traceback.tb_lineno, e))
        time.sleep(5.)
sys.exit(0)
