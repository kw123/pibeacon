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


from ctypes import *
import smbus

sys.path.append(os.getcwd())
import  piBeaconUtils   as U
import  piBeaconGlobals as G
G.program = "vl503l0xDistance"
G.debug = 0
import  displayDistance as DISP
i2cbus = smbus.SMBus(1)


VL53L0X_GOOD_ACCURACY_MODE      = 0   # Good Accuracy mode
VL53L0X_BETTER_ACCURACY_MODE    = 1   # Better Accuracy mode
VL53L0X_BEST_ACCURACY_MODE      = 2   # Best Accuracy mode
VL53L0X_LONG_RANGE_MODE         = 3   # Longe Range mode
VL53L0X_HIGH_SPEED_MODE         = 4   # High Speed mode

accuracyDistanceModes= ["VL53L0X_GOOD_ACCURACY_MODE","VL53L0X_BETTER_ACCURACY_MODE","VL53L0X_BEST_ACCURACY_MODE","VL53L0X_LONG_RANGE_MODE","VL53L0X_HIGH_SPEED_MODE"]


# ===========================================================================
# read params
# ===========================================================================

#################################        
def readParams():
    global  sensorList, sensors, logDir, sensor,  sensorRefreshSecs, dynamic, mode, deltaDist,displayEnable
    global output, sensorActive, timing, tof, distanceUnits
    global actionDistanceOld, actionShortDistance, actionShortDistanceLimit, actionMediumDistance, actionMediumDistanceLimit, actionLongDistance, actionLongDistanceLimit
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
          
        if "sensorList"         in inp:  sensorList=         (inp["sensorList"])
        if "sensors"            in inp:  sensors =           (inp["sensors"])
        if "debugRPI"           in inp:  G.debug=             int(inp["debugRPI"]["debugRPISENSOR"])
        if "distanceUnits"      in inp:  distanceUnits=      (inp["distanceUnits"])
        
        if "output"             in inp:  output=             (inp["output"])
   
 
        if sensor not in sensors:
            U.logger.log(30, "vlx503l0xDistance is not in parameters = not enabled, stopping vlx503l0xDistance.py" )
            exit()
            
 
        sensorUp = doWeNeedToStartSensor(sensors,sensorsOld,sensor)


        if sensorUp != 0: # something has changed
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
                if "acuracyDistanceMode" in sensors[sensor][devId]:
                    acuracyDistanceMode= int(sensors[sensor][devId]["acuracyDistanceMode"])
            except: 
                acuracyDistanceMode = VL53L0X_LONG_RANGE_MODE
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


        if sensorUp == 1:
            if not sensorActive:
                U.logger.log(30,"==== Start ranging =====; mode= "+unicode(accuracyDistanceModes[acuracyDistanceMode]))
                startSensor(acuracyDistanceMode)

            elif acuracyDistanceMode != acuracyDistanceModeOld:
                U.logger.log(30, "==== re-Start ranging =====; mode= "+unicode(accuracyDistanceModes[acuracyDistanceMode]))
                tof.stop_ranging()
                startSensor(acuracyDistanceMode)
                
        if sensorUp == -1:
            tof.stop_ranging()
            U.logger.log(30, "==== stop  ranging =====")
            exit()


    except  Exception, e:
        U.logger.log(30, u"in Line {} has error={}".format(sys.exc_traceback.tb_lineno, e))


def startSensor(mode):
    global timing, acuracyDistanceModeOld
    try:
        ok=True
        for ii in range(10):
            retCode = tof.start_ranging(mode= mode)
            if retCode != 25: 
                time.sleep(5)
                U.logger.log(30, " retcode wrong: "+ unicode(retCode)+"  trying again #"+unicode(ii) )
            else:
                ok=True
                timing = tof.get_timing()/1000000.00 # uS --> in seconds
                break
                acuracyDistanceModeOld = mode
        if not ok:
                print datetime.datetime.now().strftime("%Y%m%d-%H:%M:%S"),sensor, " retcode "+unicode(retCode)+" wrong, giving up after tries:"+unicode(ii) 
                U.logger.log(30, "==== ranging retcode wrong: "+unicode(retCode)+"  giving up after tries:"+unicode(ii) )
                exit()
        U.logger.log(30, "==== ranging started ok ====")
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






class VL53L0X(object):
    """VL53L0X ToF."""

    object_number = 0

    def __init__(self, address=0x29, TCA9548A_Num=255, TCA9548A_Addr=0, **kwargs):
        """Initialize the VL53L0X ToF Sensor from ST"""
        self.device_address   = address
        self.TCA9548A_Device  = TCA9548A_Num
        self.TCA9548A_Address = TCA9548A_Addr
        self.my_object_number  = VL53L0X.object_number
        VL53L0X.object_number += 1

    def start_ranging(self, mode = VL53L0X_LONG_RANGE_MODE):
        """Start VL53L0X ToF Sensor Ranging"""
        retCode = tof_lib.startRanging(self.my_object_number, mode, self.device_address, self.TCA9548A_Device, self.TCA9548A_Address)
        #print "startRanging ", retCode
        return retCode

    def stop_ranging(self):
        """Stop VL53L0X ToF Sensor Ranging"""
        retCode = tof_lib.stopRanging(self.my_object_number)
        #print "stopRanging ",retCode
        return retCode

    def get_distance(self):
        """Get distance from VL53L0X ToF Sensor"""
        return tof_lib.getDistance(self.my_object_number)

    # This function included to show how to access the ST library directly
    # from python instead of through the simplified interface
    def get_timing(self):
        Dev = POINTER(c_void_p)
        Dev = tof_lib.getDev(self.my_object_number)
        budget = c_uint(0)
        budget_p = pointer(budget)
        Status =  tof_lib.VL53L0X_GetMeasurementTimingBudgetMicroSeconds(Dev, budget_p)
        if (Status == 0):
            return (budget.value + 1000)
        else:
            return -1


 


 
#################################

# i2c bus read callback
def i2c_read(address, reg, data_p, length):
    ret_val = 0
    result = []

    try:
        result = i2cbus.read_i2c_block_data(address, reg, length)
    except IOError:
        ret_val = -1

    if (ret_val == 0):
        for index in range(length):
            data_p[index] = result[index]

    return ret_val

# i2c bus write callback
def i2c_write(address, reg, data_p, length):
    ret_val = 0
    data = []

    for index in range(length):
        data.append(data_p[index])
    try:
        i2cbus.write_i2c_block_data(address, reg, data)
    except IOError:
        ret_val = -1

    return ret_val
#################################
#################################
def getDistance():
    global sensor, sensors, first, tof, badSensor
    global actionDistanceOld, actionShortDistance, actionShortDistanceLimit, actionMediumDistance, actionMediumDistanceLimit, actionLongDistance, actionLongDistanceLimit

    try:
        if first: time.sleep(3) ; first = False
        for ii in range(10):
            distance = tof.get_distance()
            if (distance > 0):
                    distance  = min(distance,10000.)/10. # = 10 meters = 10,000 mm
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
                    return  ("%7.1f"%(distance)).strip() #  return in cm

        if badSensor >3: return "badSensor"
    except  Exception, e:
            U.logger.log(30, u"in Line {} has error={}".format(sys.exc_traceback.tb_lineno, e))
            U.logger.log(30, u"distance>>" + unicode(distance)+"<<")
    return ""        



#################################

#################################



             
global sensorList, externalSensor,senors,sensorRefreshSecs,sensor, NSleep, ipAddress, dynamic, mode, deltaDist, first, displayEnable
global output, authentication, badSensor
global distanceUnits, sensorActive, timing
global distanceMode , acuracyDistanceMode, acuracyDistanceModeOld
global actionShortDistance, actionShortDistanceLimit, actionMediumDistance, actionMediumDistanceLimit, actionLongDistance, actionLongDistanceLimit, actionDistanceOld
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

acuracyDistanceMode         = VL53L0X_LONG_RANGE_MODE
acuracyDistanceModeOld      = -1
G.debug                     = 5
first                       = False
loopCount                   = 0
sensorRefreshSecs           = 60
NSleep                      = 100
sensorList                  = []
sensors                     = {}
sensor                      = G.program
quick                       = False
dynamic                     = False
mode                        = 0
display                     = "0"
output                      = {}
badSensor                   = 0
sensorActive                = False
timing =1
U.setLogging()

myPID       = str(os.getpid())
U.killOldPgm(myPID,G.program+".py")# kill old instances of myself if they are still running

if U.getIPNumber() > 0:
    time.sleep(10)
    exit()


# Load VL53L0X shared lib 
tof_lib = CDLL(G.homeDir+"vl53l0x_python.so")

# Create read function pointer
READFUNC = CFUNCTYPE(c_int, c_ubyte, c_ubyte, POINTER(c_ubyte), c_ubyte)
read_func = READFUNC(i2c_read)

# Create write function pointer
WRITEFUNC = CFUNCTYPE(c_int, c_ubyte, c_ubyte, POINTER(c_ubyte), c_ubyte)
write_func = WRITEFUNC(i2c_write)

# pass i2c read and write function pointers to VL53L0X library
tof_lib.VL53L0X_set_i2c(read_func, write_func)


# cerate instance
tof = VL53L0X()

readParams()

U.echoLastAlive(G.program)

lastDist            = {}
lastData            = {}
lastTime            = {}
maxDeltaSpeed       = 40. # = mm/sec
lastDisplay         = 0
lastRead            = time.time()
G.lastAliveSend     = time.time() -1000
loopSleep           = 0.1
while True:
    try:
        tt = time.time()
        data={}
        data["sensors"]     = {}
        quick2 = False
        if sensor in sensors:
            for devId in sensors[sensor]:
                if devId not in lastDist: 
                    lastDist[devId] =-500.
                    lastTime[devId] =0.
                dist =getDistance()
                if dist =="badSensor":
                    first=True
                    U.logger.log(30," bad sensor, sleeping for 10 secs")
                    data0={}
                    data0[sensor]={}
                    data0[sensor][devId]={}
                    data0[sensor][devId]["distance"]="badSensor"
                    data["sensors"]     = data0
                    U.sendURL(data)
                    lastDist[devId] =-100.
                    continue
                    
                data["sensors"]     = {sensor:{devId:{}}}
                dist = float(dist)
                delta=  dist - lastDist[devId]
                deltaT =  max(tt   - lastTime[devId],0.01)
                speed  =  delta / deltaT
                deltaN= abs(delta) / max (0.5,(dist+lastDist[devId])/2.)
                if ( ( deltaN > deltaDist[devId] ) or 
                     (  (tt - abs(sensorRefreshSecs)) > G.lastAliveSend)   or 
                     (  quick )  or 
                     ( speed > maxDeltaSpeed)  ):
                        data["sensors"][sensor][devId]["distance"] = dist
                        data["sensors"][sensor][devId]["speed"]    = speed
                        U.sendURL(data)
                lastDist[devId]  = dist
                lastTime[devId]  = tt

                if displayEnable =="1" and  ((deltaN > 0.05  and  tt - lastDisplay >1.)   or  tt - lastDisplay >10. or quick):
                    lastDisplay = tt
                    DISP.displayDistance(dist, sensor, sensors, output, distanceUnits)
                    U.logger.log(10, unicode(dist)+"  "+unicode(deltaDist) )   
                    #print datetime.datetime.now().strftime("%Y%m%d-%H:%M:%S"),sensor, dist , deltaDist   

        loopCount +=1
        
        U.makeDATfile(G.program, data)

        quick = U.checkNowFile(G.program)                
        U.echoLastAlive(G.program)
                    

        if loopCount %11 ==0:
            tt= time.time()
            if tt - lastRead > 5.:  
                readParams()
                lastRead = tt
        if not quick: 
            time.sleep(loopSleep)
        #print "end of loop", loopCount
    except  Exception, e:
        U.logger.log(30, u"in Line {} has error={}".format(sys.exc_traceback.tb_lineno, e))
        time.sleep(5.)
sys.exit(0)
