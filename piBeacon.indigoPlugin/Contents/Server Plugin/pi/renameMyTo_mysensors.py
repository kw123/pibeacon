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
        global debug, sensorList,cAddress,sensorRefreshSecs, sensors

        sensorList  = "0"
        cAddressOld = copy.copy(cAddress)
        cAddress    = {}
        inp,inRaw = U.doRead()

        U.getGlobalParams(inp)
        if u"debugRPI"          in inp:  debug=                   int(inp["debugRPI"]["debugRPImystuff"])

        if "sensorList"         in inp:  sensorList =                (inp["sensorList"])
        if "sensorRefreshSecs"  in inp:  sensorRefreshSecs =    float(inp["sensorRefreshSecs"])
        if "cAddress"           in inp:  xxx =                        inp["cAddress"]
        if "sensors"            in inp:  sensors =                   (inp["sensors"])

        if sensorList.find("mysensors") == -1 : return
        if "mysensors" not in xxx: return

        same=True
        cAddress= copy.copy(xxx["mysensors"])

        # check if anything new
        if "mysensors" not in cAddressOld :
            same=False
        else:
            for addr in cAddress:
                if addr not in cAddressOld :
                    same=False
                    break
                elif len(cAddress) != len(cAddressOld) :
                    same=False
                    break
                if cAddressOld[addr] != cAddress[addr] :
                    same=False
                    break

            # start each "channel, device or what every you like to do
            for addr in cAddress:
                startMySensors(addr=addr)



# ===========================================================================
# sensor start  adopt to your needs
# ===========================================================================

def startMySensors(addr=0):
        global cAddress
        try:
            # do your init here
            parameter= cAddress[addr]
            ## add any init code here for address # addr
            U.toLog(-1, u"starting my sensors " + unicode(cAddress) + ";    dev= " + unicode(addr))
        except  Exception, e:
            U.toLog(-1, u"in Line '%s' has error='%s'" % (sys.exc_traceback.tb_lineno, e))
            U.toLog(-1, u"channel used: " + unicode(cAddress) + ";    addr= " + unicode(addr))

def getMySensors(addr=0):
        global cAddress
        try:
            parameter = cAddress[addr]
            v = ["","","","","","","","","","",]   # set return to empty
            # do your stuff here, this if for testing to something into the data
            x = time.time()  # some dummy data
            v = [str(x), str(x/2), "0", "1", "2", "3", "4", "5", "6", "7"]  ## <-- this is your data to be send back
            return v
        except  Exception, e:
            U.toLog(-1, u"in Line '%s' has error='%s'" % (sys.exc_traceback.tb_lineno, e))
        return ""


# ===========================================================================
# sensor end
# ===========================================================================


# ===========================================================================
# Main, should ok as is
# ===========================================================================


global debug, sensorList, externalSensor,cAddress,sensorRefreshSecs, ipAddress, sensors

debug             = 5 # will be overwritten in readParams
nInputs           = 10 # number of input channels 1...10 max

loopCount         = 0  # for loop,  not used could be deleted, but you might need it
sensorRefreshSecs = 33 # will be overwritten in readParams, number of seconds to sleep in each loop
sensorList        = [] # list of sensor, we are looking for "mysensors"
cAddress          = [] # store address / parameters we get from indigo in device config of mysensors in readParams

sensor            = G.program
readParams()           # get parameters send from indigo

if U.getIPNumber() > 0:
    print "mysensor  no ip number  exit "
    time.sleep(10)
    exit()

myPID             = str(os.getpid())
U.killOldPgm(myPID, G.program+".py")# kill old instances of myself if they are still running

quick    = False
lastData = {}
loopCount = 0
while True:  # loop for ever
        data={}
        try:
            ### get data
            if sensor in sensors > -1 :# do mysensor
                for  nAddr in range(len(cAddress)) :
                    v = getMySensors(addr=nAddr)
                    if v != "" :
                        addr = cAddress[nAddr]
                        data[sensor] = {}
                        data[sensor][addr] = { }
                        for ii in range(min(nInputs,len(v))):
                            data[sensors][addr]["INPUT_"+str(ii)]  = v[ii]
            loopCount +=1
            ### send data to plugin
            if loopcount%100 == 0 or quick or lastData != data: 
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
            U.toLog(-1, u"in Line '%s' has error='%s'" % (sys.exc_traceback.tb_lineno, e))

        time.sleep(sensorRefreshSecs) # sleep the requested amount
        readParams()  # check if we have new parameetrs

sys.exit(0)        
