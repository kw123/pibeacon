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
import Adafruit_DHT

sys.path.append(os.getcwd())
import  piBeaconUtils   as U
import  piBeaconGlobals as G
G.program = "DHT"





# ===========================================================================
# DHT
# ===========================================================================

def getDATAdht(DHTpin,Type):
        global sensorDHT, startDHT
        t,h="",""
        try:
            ii=startDHT[str(DHTpin)]
        except:
            if startDHT =="":
                startDHT={}
                sensorDHT={}
            startDHT[str(DHTpin)]  = 1
            if Type.lower() == "dht11":     
                sensorDHT[str(DHTpin)] = Adafruit_DHT.DHT11
            else:     
                sensorDHT[str(DHTpin)] = Adafruit_DHT.DHT22
        try:
            h,t = Adafruit_DHT.read_retry(sensorDHT[str(DHTpin)], int(DHTpin))
            if unicode(h) == "None" or unicode(t) == "None":
                print " return data failed: "+str(h)+" "+str(t), Type,  "pin",str(DHTpin), " try again"
                time.sleep(1)
                h,t = Adafruit_DHT.read_retry(sensorDHT[str(DHTpin)], int(DHTpin))
            #f h is not None and t is not None:
            #print " return data: "+str(h)+" "+str(t), Type, "pin",str(DHTpin)
#           # sensorDHT=""
            return ("%5.1f"%float(t)).strip(),("%3d"%float(h)).strip()
            #else: return "" ,""  
        except  Exception, e:
            U.toLog(-1, u"in Line '%s' has error='%s'" % (sys.exc_traceback.tb_lineno, e))
            U.toLog(-1, u" pin: "+ str(DHTpin)+" return  value: t="+ unicode(t)+"; h=" + unicode(h)  )
        return "",""



def getDHT(sensor,data):
    global badSensors
    global sensors, sValues, displayInfo
    try:
        if sensor in sensors :
            data[sensor]={}
            for devId in sensors[sensor]:
                t,h =getDATAdht(sensors[sensor][devId]["gpioPin"],sensor)
                if t!="":
                    try:    t = str(float(t) + float(sensors[sensor][devId]["offsetTemp"]))
                    except: pass
                    data[sensor][devId] = {"temp":str(t).strip(" ")}
                    if h!= "":
                        try:    h = str(float(h)  + float(sensors[sensor][devId]["offsetHum"]))
                        except: pass
                        data[sensor][devId]["hum"]=str(h).strip(" ")
                        if devId in badSensors: del badSensors[devId]
                    time.sleep(0.1)
                else:
                    data= incrementBadSensor(devId,sensor,data)
    except  Exception, e:
        U.toLog(-1, u"in Line '%s' has error='%s'" % (sys.exc_traceback.tb_lineno, e))

    if sensor in data and data[sensor]== {}: del data[sensor]
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
        U.toLog(-1, u"in Line '%s' has error='%s'" % (sys.exc_traceback.tb_lineno, e))
    return data 


        
# ===========================================================================
# sensor end
# ===========================================================================

 
# ===========================================================================
# read params
# ===========================================================================


def readParams():
        global sensorList, sensors, sendToIndigoSecs,enableTXpinsAsGpio,enableSPIpinsAsGpio, sensorRefreshSecs
        global output
        global tempUnits, pressureUnits, distanceUnits
        global oldRaw, lastRead
        global clockLightSensor
        global addNewOneWireSensors

        rCode= False

        inp,inpRaw,lastRead2 = U.doRead(lastTimeStamp=lastRead)
        if inp == "": return rCode
        if lastRead2 == lastRead: return rCode
        lastRead  = lastRead2
        if inpRaw == oldRaw: return 
        oldRaw     = inpRaw

        oldSensor  = sensorList
        sensorsOld = copy.copy(sensors)
        outputOld  = unicode(output)


        U.getGlobalParams(inp)
        if "debugRPI"             in inp:  G.debug=             int(inp["debugRPI"]["debugRPISENSOR"])
        if "output"               in inp: output=                  (inp["output"])
        if "tempUnits"            in inp: tempUnits=               (inp["tempUnits"])
        if "pressureUnits"        in inp: pressureUnits=           (inp["pressureUnits"])
        if "sensors"              in inp: sensors =                (inp["sensors"])
        if "sensorRefreshSecs"    in inp: sensorRefreshSecs = float(inp["sensorRefreshSecs"])


        sensorList=""
        for sensor in sensors:
            sensorList+=sensor.split("-")[0]+","

        if sensorList.find("DHT") ==-1:
            exit()
            
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
global startDHT
global tempUnits 
global regularCycle
global oldRaw, lastRead
global  sensorRefreshSecs


sensorRefreshSecs   = 90
oldRaw              = ""
lastRead            = 0
startDHT            = ""
tempUnits           ="Celsius"
loopCount           = 0
sensorList          = []
sensors             = {}
DHTpin              = 17
enableTXpinsAsGpio  = "0"
quick               = False
output              = {}

readParams()

if U.getIPNumber() > 0:
    U.toLog(-1," getsensors no ip number  exiting ", doPrint =True)
    time.sleep(10)
    exit()


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
            if "DHTxx"          in sensors: data = getDHT("DHTxx",           data)
            if "DHT11"          in sensors: data = getDHT("DHT11",           data)



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
                            #print dd, lastData[sens][dd], data[sens][dd]
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
                #U.toLog(2, u"sending url: "+unicode(data))
                U.sendURL({"sensors":data})
            except  Exception, e:
                U.toLog(-1, u"in Line '%s' has error='%s'" % (sys.exc_traceback.tb_lineno, e),permanentLog=True)
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
            if tt - lastRead > 5:
                lastRead = tt
                U.checkIfAliveNeedsToBeSend()
    except  Exception, e:
        U.toLog(-1, u"in Line '%s' has error='%s'" % (sys.exc_traceback.tb_lineno, e),permanentLog=True)
        time.sleep(5.)
sys.exit(0)
