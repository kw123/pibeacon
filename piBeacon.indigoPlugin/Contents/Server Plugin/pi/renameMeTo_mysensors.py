#!/usr/bin/env python
# -*- coding: utf-8 -*-
# by Karl Wachs
# march 1 2016
# exampel program to get data and send it to indigo
import  sys
import os
import time
import json
import datetime
import subprocess
import copy

sys.path.append(os.getcwd())
import  piBeaconUtils   as U
import  piBeaconGlobals as G

G.program = "mysensors"


# ===========================================================================
# read params do not change
# ===========================================================================
def readParams():
        global debug, sensorList,freeParameter,sensorRefreshSecs, sensors

        sensorList  = "0"
        oldfreeParameter = copy.copy(freeParameter)
        inp,inRaw = U.doRead()

        U.getGlobalParams(inp)
        if "sensors"            in inp:  sensors =                   (inp["sensors"])

        if G.program not in sensors: 
            exit()
        sensor = sensors[G.program]
        for id in sensor:
            if "freeParameter"  in sensor[id]:  freeParameter[id] =             sensor[id]["freeParameter"]

        # check if anything new
        if id not in oldfreeParameter or freeParameter[id] != oldfreeParameter[id]:
            startMySensors(freeParameter[id])



# ===========================================================================
# sensor start  adopt to your needs
# ===========================================================================

def startMySensors(parameter):
        try:
            # do your init here

            ## add any init code here for address # addr
            U.logger.log(30, u"starting my sensors {}".format(parameter) )
        except  Exception as e:
            U.logger.log(20,"", exc_info=True)
            U.logger.log(30, u"channel used: {}".format(parameter) )

def getMySensors(parameter):
        try:
            v = ["","","","","","","","","","",]   # set return to empty
            # do your stuff here, this if for testing to something into the data
            x = time.time()  # some dummy data
            v = [str(x), str(x/2), "0", "1", "2", "3", "4", "5", "6", "7"]  ## <-- this is your data to be send back
            return v
        except  Exception as e:
            U.logger.log(20,"", exc_info=True)
        return ""


# ===========================================================================
# sensor end
# ===========================================================================


# ===========================================================================
# Main, should ok as is
# ===========================================================================


global debug, sensorList, externalSensor,freeParameter,indigoIds, ipAddress, sensors

debug             = 5 # will be overwritten in readParams
nInputs           = 10 # number of input channels 1...10 max

loopCount         = 0  # for loop,  not used could be deleted, but you might need it
sensorRefreshSecs = 10 # will be overwritten in readParams, number of seconds to sleep in each loop
sensorList        = [] # list of sensor, we are looking for "mysensors"
freeParameter     = {}  # store address / parameters we get from indigo in device config of mysensors in readParams

sensor            = G.program
U.setLogging()

readParams()           # get parameters send from indigo

if U.getIPNumber() > 0:
    time.sleep(10)
    exit()

myPID             = str(os.getpid())
U.killOldPgm(myPID, G.program+".py")# kill old instances of myself if they are still running

quick    = False
lastData = {}
loopCount = 0

while True:  # loop for ever
        loopCount +=1
        data={}
        try:
            ### get data
            
            if sensor in sensors:# do mysensor
                data["sensors"]={sensor:{}}
                for id in sensors[sensor]:
                    v = getMySensors(freeParameter[id])
                    if v != "" :
                        data["sensors"][sensor][id] = {}
                        for ii in range(min(nInputs,len(v))):
                            data["sensors"][sensor][id]["INPUT_"+str(ii)]  = v[ii]
            ### send data to plugin
            if loopCount%1 == 0 or quick or lastData != data: 
                U.sendURL(data)
            lastData = copy.copy(data)
            
            # make data file for debugging
            U.makeDATfile(G.program, data)

            # check if we should send data now, requested by plugin
            quick = U.checkNowFile(G.program)                

            # make alive file for mast to signal we are still running
            if loopCount %20 ==0:
                U.echoLastAlive(G.program)

        except  Exception, e :
            U.logger.log(20,"", exc_info=True)

        time.sleep(sensorRefreshSecs) # sleep the requested amount
        readParams()  # check if we have new parameetrs

sys.exit(0)        
