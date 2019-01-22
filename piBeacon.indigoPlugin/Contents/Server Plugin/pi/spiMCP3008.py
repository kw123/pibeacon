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
G.program = "spiMCP3008"



# ===========================================================================
# MCP3008
# ===========================================================================


def startMCP3008(devId):
        global spi0,spi1

        spiAdd=0
        try:
            ss= ""
            if "spiMCP3008" in sensors:
                ss="spiMCP3008"
            if "spiMCP3008-1" in sensors:
                ss="spiMCP3008-1"
            if ss!="" :  
                if sensors[ss][devId]["spiAddress"]!="":
                    spiAdd=int(sensors[ss][devId]["spiAddress"])
                    if spiAdd >1 : spiAdd = 1
                    if spiAdd <0 : spiAdd = 0

                    if spiAdd == 0:
                        spi0 = spidev.SpiDev()
                        spi0.open(0,0)
                    if spiAdd == 1:
                        spi1 = spidev.SpiDev()
                        spi1.open(0,1)
                    #print spiAdd, spi0,spi1    
        except  Exception, e:
            U.toLog(-1, u"in Line '%s' has error='%s'" % (sys.exc_traceback.tb_lineno, e))
            U.toLog(-1, u"spi channel used: "+ unicode(spiAdd)+";    dev= "+unicode(dev))

def getMCP3008(sensor, data):
    global sensorMCP3008, MCP3008Started
    global sensors
    global spi0,spi1

    if "spiMCP3008" in sensors:
        spiAdd = int(sensors["spiMCP3008"][devId]["spiAddress"])
    if "spiMCP3008-1" in sensors:
        spiAdd = int(sensors["spiMCP3008-1"][devId]["spiAddress"])

    data[sensor] ={}

    try:
        if sensor.find("-1") ==-1:
            for devId in sensors[sensor]:
                data[sensor][devId]={}
                # read the analog pin
                v=["","","","","","","",""]
                s,e=0,8
                for pin in range(s,e):
                    if spiAdd == 0:
                        adc = spi0.xfer2([1,(8+pin)<<4,0])
                    if spiAdd==1:
                        adc = spi1.xfer2([1,(8+pin)<<4,0])
                    v = int(1000*(((adc[1]&3) << 8) + adc[2])*3.3/1024.)
                    data[sensor][devId]["INPUT_"+str(pin)]  =v
                    if devId in badSensors: del badSensors[devId]
            if sensor in data and data[sensor]=={}: del data[sensor]
        else:
            for devId in sensors[sensor]:
                data[sensor][devId]={}
                if "input" in sensors[sensor][devId]:
                    pin= int(sensors[sensor][devId]["input"])
                else:
                    pin=0
                if spiAdd == 0:
                    adc = spi0.xfer2([1,(8+pin)<<4,0])
                if spiAdd==1:
                    adc = spi1.xfer2([1,(8+pin)<<4,0])
                v = int(1000*(((adc[1]&3) << 8) + adc[2])*3.3/1024.)
                data[sensor][devId]["INPUT_0"]  =v
                if devId in badSensors: del badSensors[devId]
    except  Exception, e:
        U.toLog(-1, u"in Line '%s' has error='%s'" % (sys.exc_traceback.tb_lineno, e))
        data= incrementBadSensor(devId,sensor,data)
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
        sensorList = []
        sensorsOld = copy.copy(sensors)
        outputOld  = unicode(output)


        U.getGlobalParams(inp)
        if "debugRPI"             in inp:  G.debug=             int(inp["debugRPI"]["debugRPISENSOR"])
        if "enableSPIpinsAsGpio"  in inp: enableSPIpinsAsGpio=     (inp["enableSPIpinsAsGpio"])
        if "enableTXpinsAsGpio"   in inp: enableTXpinsAsGpio=      (inp["enableTXpinsAsGpio"])
        if "output"               in inp: output=                  (inp["output"])
        if "sensors"              in inp: sensors =                (inp["sensors"])
        if "sensorRefreshSecs"    in inp: sensorRefreshSecs = float(inp["sensorRefreshSecs"])


        sensorList=""
        for sensor in sensors:
            sensorList+=sensor.split("-")[0]+","
        if sensorList.find("spi") ==-1:
            exit()

        return rCode






#################################
def checkSPSstatus():
    global sensorList, sensors,spi0,spi1, enableSPIpinsAsGpio
    if spi0 ==0 and spi1 ==0 and enableSPIpinsAsGpio=="0" and "spiMCP3008" in sensorList:
        #print "point1", spi0, spi1 , enableSPIpinsAsGpio, sensorList
        import spidev
        if enableSPIpinsAsGpio=="0" and "spiMCP3008" in sensors:
            for devId in sensors["spiMCP3008"] :
                startMCP3008(devId)
        if enableSPIpinsAsGpio=="0" and "spiMCP3008-1" in sensors:
            for devId in sensors["spiMCP3008-1"] :
                startMCP3008(devId)

#################################
#################################
#################################
#################################
             
global sensorList, sensors,spi0,spi1,badSensors
global enableTXpinsAsGpio,enableSPIpinsAsGpio
global tempUnits, pressureUnits, distanceUnits
global regularCycle
global oldRaw, lastRead
global clockLightSensor, sensorRefreshSecs
global addNewOneWireSensors


sensorRefreshSecs   = 90
clockLightSensor    = "0"
oldRaw              = ""
lastRead            = 0
tempUnits           ="Celsius"
pressureUnits       = "mBar"
distanceUnits       = "1"
loopCount           = 0
sensorList          = []
sensors             = {}
DHTpin              = 17
spi0                = 0
spi1                = 0
enableTXpinsAsGpio  = "0"
enableSPIpinsAsGpio = "0"
authentication      = "digest"
quick               = False
output              = {}

readParams()
if enableSPIpinsAsGpio=="0" and ( "spiMCP3008" in sensors or "spiMCP3008-1" in sensors):
    import spidev
if enableSPIpinsAsGpio=="0" and "spiMCP3008" in sensors :
    for devId in sensors["spiMCP3008"]:
        startMCP3008(devId)
if enableSPIpinsAsGpio=="0" and "spiMCP3008-1" in sensors:
    for devId in sensors["spiMCP3008-1"]:
        startMCP3008(devId)

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
G.tStart            = tt
lastregularCycle    = tt
lastRead            = tt
regularCycle        = True
lastData={}

while True:
    try:
        tt = time.time()
        data={}
        sValues={"temp":[[],[],[]],"press":[[],[],[]],"hum":[[],[],[]],"lux":[[],[],[]]}      
        displayInfo={}
        
        if regularCycle:
            if "spiMCP3008"     in sensors: data = getMCP3008("spiMCP3008",  data)
            if "spiMCP3008-1"   in sensors: data = getMCP3008("spiMCP3008-1",data)

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
