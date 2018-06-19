#!/usr/bin/python
# -*- coding: utf-8 -*-
# by Karl Wachs
# 2018-01-28
# version 0.1 
##
##
#! /usr/bin/env python
# -*- coding: utf-8 -*-
####################

import sys, os, time, json, datetime,subprocess,copy
import math
import copy
from collections import OrderedDict
import smbus


sys.path.append(os.getcwd())
import  piBeaconUtils   as U
import  piBeaconGlobals as G
G.program = "mhz-I2C"
G.debug = 0
#simple bitfield object


#H.yasuhiro,2017/1/17

class mhz16_class:
    type
    ppm         = 0
     
    IOCONTROL   = 0X0E << 3
    FCR         = 0X02 << 3
    LCR         = 0X03 << 3
    DLL         = 0x00 << 3
    DLH         = 0X01 << 3
    THR         = 0X00 << 3
    RHR         = 0x00 << 3
    TXLVL       = 0X08 << 3
    RXLVL       = 0X09 << 3
         
    def __init__(self, address = 0x4d, sensorType=1):
        self.i2c_addr = address
        self.i2c      = smbus.SMBus(1)
        if sensorType ==1:
            self.cmd_measure       = [0xFF,0x01,0x9C,0x00,0x00,0x00,0x00,0x00,0x63]
            self.cmd_calibrateZero = [0xFF,0x01,0x87,0x00,0x00,0x00,0x00,0x00,0x78]
            self.beginData         = 4 
            self.commandByteReturn = self.cmd_measure[2]
        else:
            self.cmd_measure       = [0xFF,0x01,0x86,0x00,0x00,0x00,0x00,0x00,0x79] # does not work 
            self.cmd_calibrateZero = [0xFF,0x87,0x87,0x00,0x00,0x00,0x00,0x00,0xF2]  # does not work 
#            self.cmd_calibrateZero = [0xFF,0x01,0x87,0x00,0x00,0x00,0x00,0x00,0x78]
            self.beginData         = 2 
            self.commandByteReturn = self.cmd_measure[2]
     
    def start(self):
        try:
            self.write_register(self.IOCONTROL, 0x08)
        except IOError:
            pass
                     
        self.write_register(self.FCR, 0x07)
        self.write_register(self.LCR, 0x83)
        self.write_register(self.DLL, 0x60)
        self.write_register(self.DLH, 0x00)
        self.write_register(self.LCR, 0x03)
 
    def calibrate(self):
        try:
            self.write_register(self.FCR, 0x07)
            self.send(self.cmd_calibrateZero)
            time.sleep(0.1)
            return
        except  Exception, e:
            U.toLog(-1, u"in Line '%s' has error='%s'" % (sys.exc_traceback.tb_lineno, e))
        self.co2 = -1
 
    def measure(self):
        try:
            self.write_register(self.FCR, 0x07)
            self.send(self.cmd_measure)
            self.parse(self.receive())
            return
        except  Exception, e:
            U.toLog(-1, u"in Line '%s' has error='%s'" % (sys.exc_traceback.tb_lineno, e))
        self.co2 = -1
 
    def parse(self, response):
        checksum = 0
        #print response
 
        if len(response) < 9:
            if len(response) == 8 and response[0] !=255:
                response = [255] + response
                #print "fixed"
            else:
                self.co2 = -1
                return
 
        for i in range (0, 9):
            checksum += response[i]
            
        self.co2 = -1
        if response[0] == 0xFF:
            if response[1] == self.commandByteReturn:
                if checksum % 256 == 0xFF:
                    self.co2  = (response[self.beginData]<<8) + response[self.beginData+1]
        #print self.co2
 
    def read_register(self, reg_addr):
        time.sleep(0.001)
        return self.i2c.read_byte_data(self.i2c_addr, reg_addr)
         
    def write_register(self, reg_addr, val):
        time.sleep(0.001)
        self.i2c.write_byte_data(self.i2c_addr, reg_addr, val)
         
    def send(self, command):
        self.commandByte= command[2]
        if self.read_register(self.TXLVL) >= len(command):  # can we send enough bytes , should be 9
            self.i2c.write_i2c_block_data(self.i2c_addr, self.THR, command)
 
    def receive(self):
        try:
            n     = 9
            buf   = []
            start = time.clock()
            errcountMAX = 2
            while n > 0:
                try: 
                    rx_level = self.read_register(self.RXLVL) # are there enough bytes available to read , should be 9.
                except Exception, e:
                    time.sleep(0.004)
                    errcountMAX -= 1
                    if errcountMAX == 0: 
                        U.toLog(0, u"receive read_register too may tries stopping read,  has error='%s'" % ( e))
                        return buf
                    continue
                    
                if rx_level > n:
                    rx_level = n
 
                buf.extend(self.i2c.read_i2c_block_data(self.i2c_addr, self.RHR, rx_level))
                n = n - rx_level
 
                if time.clock() - start > 0.2:
                    break
                
            return buf
        except  Exception, e:
            U.toLog(-1, u"receive in Line '%s' has error='%s'" % (sys.exc_traceback.tb_lineno, e))
        return []


# ===========================================================================
# read params
# ===========================================================================

#################################        
def readParams():
    global sensorList, sensors, logDir, sensor,  sensorRefreshSecs, displayEnable
    global rawOld,i2cAddress
    global deltaX, mhz16, minSendDelta
    global oldRaw, lastRead
    global startTime
    global CO2normal, CO2offset,sensitivity,timeaboveCalibrationMAX
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
        if "debugRPI"           in inp:  G.debug=             int(inp["debugRPI"]["debugRPISENSOR"])
         
 
        if sensor not in sensors:
            U.toLog(-1, G.program+" is not in parameters = not enabled, stopping "+G.program+".py" )
            exit()
            

        U.toLog(-1, G.program+" reading new parameter file" )

        if sensorRefreshSecs == 91:
            try:
                xx     = str(inp["sensorRefreshSecs"]).split("#")
                sensorRefreshSecs = float(xx[0]) 
            except:
                sensorRefreshSecs = 91    
        deltaX={}
        restart = False
        for devId in sensors[sensor]:
            deltaX[devId]  = 0.1

            try:
                if "sensorRefreshSecs" in sensors[sensor][devId]:
                    xx = sensors[sensor][devId]["sensorRefreshSecs"].split("#")
                    sensorRefreshSecs = float(xx[0]) 
            except:
                sensorRefreshSecs = 5    
            
            old = i2cAddress
            try:
                if "i2cAddress" in sensors[sensor][devId]: 
                    i2cAddress = int(sensors[sensor][devId]["i2cAddress"])
            except:
                i2cAddress = ""    
            if old != i2cAddress: restart = True

            try:
                if "deltaX" in sensors[sensor][devId]: 
                    deltaX[devId]= float(sensors[sensor][devId]["deltaX"])/100.
            except:
                deltaX[devId] = 0.1

            try:
                if "CO2normal" in sensors[sensor][devId]: 
                    CO2normal[devId]= float(sensors[sensor][devId]["CO2normal"])
            except:
                CO2normal[devId] = 410

            try:
                if "CO2offset" in sensors[sensor][devId]: 
                    CO2offset[devId]= float(sensors[sensor][devId]["CO2offset"])
            except:
                CO2offset[devId] = 0

            try:
                if "sensitivity" in sensors[sensor][devId]: 
                    sensitivity[devId]= sensors[sensor][devId]["sensitivity"]
            except:
                sensitivity[devId] = "medium"

            try:
                if "timeaboveCalibrationMAX" in sensors[sensor][devId]: 
                    timeaboveCalibrationMAX[devId]= float(sensors[sensor][devId]["sensitivity"])
            except:
                timeaboveCalibrationMAX[devId] = 1200


            try:
                if "minSendDelta" in sensors[sensor][devId]: 
                    minSendDelta= float(sensors[sensor][devId]["minSendDelta"])
            except:
                minSendDelta = 5.

                
            if devId not in mhz16sensor or  restart:
                startSensor(devId, i2cAddress)
                if mhz16sensor[devId] =="":
                    return
            U.toLog(-1," new parameters read: i2cAddress:" +unicode(i2cAddress) +";  minSendDelta:"+unicode(minSendDelta)+
                       ";  deltaX:"+unicode(deltaX[devId])+";  sensorRefreshSecs:"+unicode(sensorRefreshSecs) +"  restart:"+str(restart))
                
        deldevID={}        
        for devId in mhz16sensor:
            if devId not in sensors[sensor]:
                deldevID[devId]=1
        for dd in  deldevID:
            del mhz16sensor[dd]
        if len(mhz16sensor) ==0: 
            ####exit()
            pass


    except  Exception, e:
        U.toLog(-1, u"in Line '%s' has error='%s'" % (sys.exc_traceback.tb_lineno, e))
        print sensors[sensor]
        



#################################
def startSensor(devId,i2cAddress):
    global sensors, sensor
    global startTime
    global mhz16sensor 
    
    U.toLog(-1,"==== Start "+G.program+" ===== @ i2c= " +unicode(i2cAddress))
    startTime =time.time()


    i2cAdd = U.muxTCA9548A(sensors[sensor][devId]) # switch mux on if requested and use the i2c address of the mix if enabled
    
    try:
        mhz16sensor[devId]  =  mhz16_class(address=i2cAdd, sensorType=2)
            
        time.sleep(1)
        mhz16sensor[devId].start()
                        
    except  Exception, e:
        U.toLog(-1, u"in Line '%s' has error='%s'" % (sys.exc_traceback.tb_lineno, e))
        mhz16sensor[devId]   =""
    time.sleep(.1)

    U.muxTCA9548Areset()
#################################
def calibrateSensor(devId):
    global sensors, sensor
    global mhz16sensor
    global CO2normal, CO2offset,sensitivity   
    
    i2cAdd = U.muxTCA9548A(sensors[sensor][devId]) # switch mux on if requested and use the i2c address of the mix if enabled
    #print "calibrating"
    ret ="" 
    try: 
         CO2offset[devId] = 0  
         mhz16sensor[devId].calibrate()
         time.sleep(5)
         ret = getValues(devId,nMeasurements=3)
         if ret == "badSensor":
            print " calibration did not work exit " 
            print ret
            time.sleep(5)
            return
            
         co2 = ret["CO2"]

         CO2offset[devId] = CO2normal[devId] - co2 
         #print "calib co2, CO2offset, CO2normal: ", co2, CO2offset[devId], CO2normal[devId]
    except  Exception, e:
        print "ret =", ret
        U.toLog(-1, u"in Line '%s' has error='%s'" % (sys.exc_traceback.tb_lineno, e))
    time.sleep(.1)


#################################
def getValues(devId,nMeasurements=5):
    global sensor, sensors,  mhz16sensor, badSensor
    global startTime, CO2offset, CO2normal, sensitivity

    try:
        ret ="badSensor"
        if mhz16sensor[devId] =="": 
            badSensor +=1
            return "badSensor"
        i2cAdd = U.muxTCA9548A(sensors[sensor][devId]) # switch mux on if requested and use the i2c address of the mix if enabled
        if mhz16sensor[devId] =="": 
            badSensor +=1
            return "badSensor"
        nnn      = max(2,nMeasurements)
        raw      = 0
        nMeas    = 0.
        addIfBad = 2
        ii       = 0
        while ii < nnn:
            ii+=1
            mhz16sensor[devId].measure()
            co2 =  mhz16sensor[devId].co2
            U.toLog(1, " co2 raw: %d" %co2 )
            if co2 ==-1: 
                ii -= addIfBad  # onetime only 
                addIfBad = 0
                U.toLog(-1, u"bad data read ")

                continue
            raw += co2
            nMeas +=1.
            if ii != nnn-1: time.sleep(2)
            if ii%5 ==0: U.echoLastAlive(G.program)

        if raw ==0:
            needRestart =True
            badSensor+=1
            if badSensor >3: ret = "badSensor"
            mhz16sensor[devId].start()
            return ret
            
        raw /= nMeas 
        CO2 = raw + CO2offset[devId]
        #print "raw, CO2, CO2offset, CO2normal", raw, CO2, CO2offset[devId], CO2normal[devId]
        ret  = {"CO2":           ( round(CO2,1)            )
               ,"CO2offset":     ( round(CO2offset[devId],1)      )
               ,"CO2calibration":( round(CO2normal[devId],1) ) 
               ,"raw":           ( round(raw,1)            ) }
        U.toLog(1, unicode(ret)) 
        badSensor = 0
    except  Exception, e:
        U.toLog(-1, u"in Line '%s' has error='%s'" % (sys.exc_traceback.tb_lineno, e))
        badSensor+=1
        if badSensor >3: ret = "badSensor"
        mhz16sensor[devId].start()
 
    U.muxTCA9548Areset()
    return ret






############################################
global rawOld,i2cAddress
global sensor, sensors, badSensor
global deltaX, mhz16sensor, minSendDelta
global  lastRead
global startTime,  lastMeasurement, reStartReq 
global CO2offset, CO2normal, sensitivity,timeaboveCalibrationMAX


i2cAddress                  =""
timeOKCalibration           ={}
timeaboveCalibrationMAX     ={}
sensitivity                 = {}
CO2normal                   = {}
CO2offset                   = {}
reStartReq                  = False
startTime                   = time.time()
lastMeasurement             = time.time()
oldRaw                      = ""
lastRead                    = 0
minSendDelta                = 5.
G.debug                     = 5
loopCount                   = 0
sensorRefreshSecs           = 91
NSleep                      = 100
sensorList                  = []
sensors                     = {}
sensor                      = G.program
quick                       = False
display                     = "0"
output                      = {}
badSensor                   = 0
sensorActive                = False
rawOld                      = ""
mhz16sensor                 ={}
deltaX                      = {}
displayEnable               = 0
myPID       = str(os.getpid())
U.killOldPgm(myPID,G.program+".py")# kill old instances of myself if they are still running


if U.getIPNumber() > 0:
    time.sleep(10)
    exit()
readParams()

time.sleep(1)

lastRead = time.time()

U.echoLastAlive(G.program)

#                     used for deltax comparison to trigger update to indigo
lastValues0         = {"CO2":0}
lastValues          = {}
lastData            = {}
lastSend            = 0
lastDisplay         = 0
lastRead            = time.time()
G.lastAliveSend     = time.time() -1000

msgCount            = 0
loopSleep           = 1
sensorWasBad        = False


calibTime        = time.time()
needCalibration = False
calibrationWaitTime = 60 # secs

calibrating       = 20

loopCount = 0
while True:
    try:
        data = {"sensors": {sensor:{}}}
        sendData = False
        if sensor in sensors:
            for devId in sensors[sensor]:
                if devId not in lastValues: 
                    lastValues[devId]         = copy.copy(lastValues0)
                    timeOKCalibration[devId ] = 0
                
                if loopCount ==0:
                    calibTime = time.time()
                    calibrateSensor(devId)

                loopCount +=1
                values = getValues(devId, nMeasurements=3 )
                if values == "": continue
                data["sensors"][sensor][devId]={}
                if values =="badSensor":
                    sensorWasBad = True
                    data["sensors"][sensor][devId]="badSensor"
                    if badSensor < 5: 
                        U.toLog(-1," bad sensor")
                        U.sendURL(data)
                    else:
                        U.restartMyself(param="", reason="badsensor",doPrint=True)
                    lastValues[devId]  =copy.copy(lastValues0)
                    if badSensor > 5: reStartReq = True 
                    continue
                elif values["CO2"] !="" :
                    if sensorWasBad: # sensor was bad, back up again, need to do a restart to set config 
                        U.restartMyself(reason=" back from bad sensor, need to restart to get sensors reset",doPrint="False")
                    
                    data["sensors"][sensor][devId] = values
                    needCalibration  = False
                    x1 =       data["sensors"][sensor][devId]["CO2"] - CO2normal[devId] 

                    if   sensitivity[devId] =="small" : recalib = [20,20]
                    elif sensitivity[devId] =="medium": recalib = [30,30]
                    else                              : recalib = [50,50]

                    if (  x1 < -recalib[0]   )   or   (  abs(x1) > recalib[1] and time.time() - calibTime < calibrationWaitTime   ): 
                        #print "delta calib",  data["sensors"][sensor][devId]["CO2"], CO2normal[devId],data["sensors"][sensor][devId]["CO2"] - CO2normal[devId] , time.time() - calibTime 
                        needCalibration  = True
                    else:
                        if abs(x1)  > recalib[1]:
                            if time.time() - timeOKCalibration[devId] > timeaboveCalibrationMAX[devId]:
                                #print "time for recalibration after %d [sec]"%(time.time() - timeOKCalibration)
                                needCalibration  = True
                        else:
                            timeOKCalibration[devId] = time.time()
                            calibrating             -= 1
                    deltaN = 0
                    delta  = 99999
                    for xx in lastValues0:
                        try:
                            current = float(values[xx])
                            delta   = abs(current-lastValues[devId][xx])/ max (0.5,(current+lastValues[devId][xx])/2.)
                            deltaN  = max(deltaN,delta) 
                            lastValues[devId][xx] = current
                        except: pass
                    #print "delta %.4f" % deltaN, deltaX[devId]
                    #print " delta co2 compared to last:", delta
                    if   time.time() - calibTime > calibrationWaitTime: 
                        data["sensors"][sensor][devId]["calibration"] ="set"
                    elif (  (time.time() - calibTime) > calibrationWaitTime/3)  and delta < abs(recalib[0]):
                        data["sensors"][sensor][devId]["calibration"] ="set Preliminary"
                    else:
                        data["sensors"][sensor][devId]["calibration"] ="finding"
                else:
                    continue
                #print "G.sendToIndigoSecs), G.lastAliveSend , minSendDelta",G.sendToIndigoSecs, G.lastAliveSend , minSendDelta
                if (( deltaN > deltaX[devId]   or  (  time.time() -  G.lastAliveSend  > abs(G.sendToIndigoSecs) ) or  quick   ) and  ( time.time() - G.lastAliveSend > minSendDelta ) ):
                    sendData = True

        #print "calibrating", calibrating
        if sendData or calibrating >=0:
            U.sendURL(data)
        loopCount +=1

        ##U.makeDATfile(G.program, data)
        quick = U.checkNowFile(G.program)                
        U.echoLastAlive(G.program)

        if loopCount %5 ==0 and not quick:
            if time.time() - lastRead > 5.:  
                readParams()
                lastRead = time.time()

        if U.checkNewCalibration(G.program) or needCalibration :
            U.toLog(-1, u"set CO2 calibration")
            if sensor in sensors:
                for devId in sensors[sensor]:
                    calibrateSensor(devId)
                    timeOKCalibration[devId] = time.time()
                    calibTime                = time.time()
                    calibrating              = 10

        if not quick:
            time.sleep(loopSleep)
        if reStartReq:
            time.sleep(5)
            os.system("/usr/bin/python "+G.homeDir+G.program+".py &")

    except  Exception, e:
        U.toLog(-1, u"in Line '%s' has error='%s'" % (sys.exc_traceback.tb_lineno, e))
        time.sleep(5.)
sys.exit(0)
 

        