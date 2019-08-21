#!/usr/bin/python
# -*- coding: utf-8 -*-
# by Karl Wachs
# feb 5 2016
# version 0.9 
##
##  get sensor values and write the to a file in json format for later pickup, 
##  do it in a timed manner not to load the system, is every 1 seconds then 30 senods break
##

import math

import  sys, os, time, json, datetime,subprocess,copy

import re

sys.path.append(os.getcwd())
import  piBeaconUtils   as U
import  piBeaconGlobals as G
G.program = "Wire18B20"



# ===========================================================================
# 18B20
# ===========================================================================
def get18B20(sensor, data):
    global sensors, addNewOneWireSensors
    if sensor not in sensors:    return data 
    if len(sensors[sensor]) == 0:return data 

    foundId = -1
    try:
        data[sensor]={}
        try:
            devs=subprocess.Popen("cat /sys/bus/w1/devices/w1_bus_master1/w1_master_slaves",shell=True,stdout=subprocess.PIPE,stderr=subprocess.PIPE).communicate()[0].split("\n")
            #print " getting data devs= "+str( devs )+ "<< "
            ret = {}
            for line in devs:
                if len(line) < 5: continue
                if line.find("28-")==-1: continue  # should be something like: "28-800000035de5"
                U.logger.log(10,"wire18B20 return data1 "+ unicode(line))
                if not os.path.isfile("/sys/bus/w1/devices/"+line+"/w1_slave"): continue
                oneWirecmd="cat  /sys/bus/w1/devices/"+line+"/w1_slave"
                dataW= subprocess.Popen(oneWirecmd,shell=True,stdout=subprocess.PIPE,stderr=subprocess.PIPE).communicate()[0].strip("\n").split("\n")
                U.logger.log(10,"wire18B20 return data2 "+ unicode(dataW))
                ##59 01 ff ff 7f ff ff ff 82 : crc=82 YES
                ##59 01 ff ff 7f ff ff ff 82 t=21562
                #print data
                if len(dataW) ==2:
                    if "YES" in dataW[0]:
                        t1=dataW[1].split("t=")
                        if len(t1)==2:
                            try:ret[line] = round(float(t1[1])/1000.,1)
                            except: ret[line] ="bad data"
                            ##ret[line] = ("%.2f"%(float(t1[1])/1000.)).strip()
            tempList= ret # {"28-800000035de5": 21.6, ...}  
        except  Exception, e:
            U.logger.log(30, u"in Line {} has error={}".format(sys.exc_traceback.tb_lineno, e))
            U.logger.log(30, u"return  value: data="+ unicode(data))
            tempList = {} 

        devId0 = sensors[sensor].keys()[0] # get any key 

        if tempList!={}:
            if "serialNumber" not in sensors[sensor][devId0]: sensors[sensor][devId0]["serialNumber"] = "0"
            if "serialNumber" in sensors[sensor][devId0] and sensors[sensor][devId0]["serialNumber"].find("28-") ==-1: # nothing registed yet: add first sensor
                for ss in tempList:
                    data[sensor][devId0] ={"temp":[{ss:tempList[ss]}]} # not registered in indigo yet, add first one to it 
                    return data
            elif "serialNumber" in sensors[sensor][devId0]:
                #print tempList
                for serialNumber in tempList:
                    foundId = -1
                    for devId in sensors[sensor]:
                        #print "trying devId", devId ,sensors[sensor][devId]
                        if "serialNumber" in sensors[sensor][devId] and serialNumber == sensors[sensor][devId]["serialNumber"]:
                            try:     tempList[serialNumber]  = round(  float(tempList[serialNumber]) + float(sensors[sensor][devId]["offsetTemp"]) ,1)
                            except:  pass
                            if devId not in data[sensor]: data[sensor][devId]={}
                            if "temp" not in data[sensor][devId] : 
                                #print devId,serialNumber, data[sensor][devId],  "adding temp"
                                data[sensor][devId]["temp"]=[]
                            data[sensor][devId]["temp"].append({serialNumber:tempList[serialNumber]})
                            #print "1",devId,  data[sensor]
                            foundId = devId
                            break
                    
                    if foundId == -1 and addNewOneWireSensors == "1":
                            if devId0 not in data[sensor]:         data[sensor][devId0]={}
                            if "temp" not in data[sensor][devId0]: data[sensor][devId0]["temp"] =[]
                            data[sensor][devId0]["temp"].append({serialNumber:tempList[serialNumber]}) # not registered in indigo yet, add it to the last devId
                            #print "2", devId0, data[sensor][devId0]
                
                
                if foundId in badSensors: del badSensors[devId]
                time.sleep(0.1)
        else:
                data= incrementBadSensor(devId0,sensor,data,text="badSensor, no info")

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
        if "enableSPIpinsAsGpio"  in inp: enableSPIpinsAsGpio=     (inp["enableSPIpinsAsGpio"])
        if "enableTXpinsAsGpio"   in inp: enableTXpinsAsGpio=      (inp["enableTXpinsAsGpio"])
        if "output"               in inp: output=                  (inp["output"])
        if "tempUnits"            in inp: tempUnits=               (inp["tempUnits"])
        if "pressureUnits"        in inp: pressureUnits=           (inp["pressureUnits"])
        if "distanceUnits"        in inp: distanceUnits=           (inp["distanceUnits"])
        if "sensors"              in inp: sensors =                (inp["sensors"])
        if "sensorRefreshSecs"    in inp: sensorRefreshSecs = float(inp["sensorRefreshSecs"])
        if "addNewOneWireSensors" in inp: addNewOneWireSensors =   (inp["addNewOneWireSensors"])


        sensorList=""
        for sensor in sensors:
            sensorList+=sensor.split("-")[0]+","
        if sensorList.find("Wire18B20") ==-1:
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
global enableTXpinsAsGpio,enableSPIpinsAsGpio
global tempUnits, pressureUnits, distanceUnits
global regularCycle
global oldRaw, lastRead
global sensorRefreshSecs
global addNewOneWireSensors

addNewOneWireSensors="0"
sensorRefreshSecs   = 90
oldRaw              = ""
lastRead            = 0
tempUnits           ="Celsius"
loopCount           = 0
sensorList          = ""
sensors             = {}
enableTXpinsAsGpio  = "0"
enableSPIpinsAsGpio = "0"
authentication      = "digest"
quick               = False
output              = {}
U.setLogging()

readParams()

if U.getIPNumber() > 0:
    U.logger.log(30," getsensors no ip number  exiting ")
    time.sleep(10)
    exit()


myPID       = str(os.getpid())
U.killOldPgm(myPID,G.program+".py")# kill old instances of myself if they are still running

NSleep= int(sensorRefreshSecs)
if G.networkType  in G.useNetwork and U.getNetwork() == "off": 
    if U.getIPNumber() > 0:
        U.logger.log(30,"no ip number working, giving up")
        time.sleep(10)

eth0IP, wifi0IP, G.eth0Enabled,G.wifiEnabled = U.getIPCONFIG()


tt                  = time.time()
badSensors          = {}
lastData            = {}
lastMsg             = 0
G.tStart            = tt
lastregularCycle    = tt
lastRead            = tt
regularCycle        = True
lastData            = {}
xxx                 = -1

while True:
    try:
        tt = time.time()
        data={}
       
        if regularCycle:
            if "Wire18B20"      in sensors: data = get18B20("Wire18B20",     data)


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
                            if sens =="Wire18B20":
                                nSens = len(data[sens][devid][devType])
                                if nSens != len(lastData[sens][devid][devType]):
                                    changed =7
                                    break
                                for nnn in range(nSens):
                                    for serialNumber in data[sens][devid][devType][nnn]:
                                        if serialNumber in lastData[sens][devid][devType][nnn]: 
                                            xxx = U.testBad( data[sens][devid][devType][nnn][serialNumber],lastData[sens][devid][devType][nnn][serialNumber], xxx )
                            else:
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
                U.logger.log(50, u"in Line {} has error={}".format(sys.exc_traceback.tb_lineno, e))
            time.sleep(0.05)

        quick = U.checkNowFile(G.program)                

        U.makeDATfile(G.program, {"sensors":data})
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
        U.logger.log(50,u"in Line {} has error={}".format(sys.exc_traceback.tb_lineno, e))
        time.sleep(5.)
sys.exit(0)
