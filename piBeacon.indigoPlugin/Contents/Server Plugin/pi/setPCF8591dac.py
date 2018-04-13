#!/usr/bin/env python
# -*- coding: utf-8 -*-
# by Karl Wachs
# feb 5 2016
# version 0.7 
##
import smbus
import re
import json, sys,subprocess, os, time, datetime
import copy

sys.path.append(os.getcwd())
import  piBeaconUtils   as U
import  piBeaconGlobals as G
G.program = "setPCF8591dac"

devType = "i2cPCF8591dac"

###########


def readParams():
    global allowedGPIOoutputPins
    inp,inpRaw = U.doRead()
    if inp == "": return
    try:
        if u"debugRPI"          in inp:  G.debug=             int(inp["debugRPI"]["debugRPIOUTPUT"])

    except  Exception, e:
        U.toLog(-1, u"in Line '%s' has error='%s'" % (sys.exc_traceback.tb_lineno, e))
         

######### main ######

myPID       = str(os.getpid())
readParams()
U.toLog(1, "setPCF8591  command :" + unicode(sys.argv))

command = json.loads(sys.argv[1])

if "i2cAddress" in command:
    i2cAddress= int(command["i2cAddress"])
else:
    U.toLog(-1, "setPCF8591dac bad command " + command + "  i2cAddress not included")
    exit(1)
    
U.killOldPgm(myPID,"setPCF8591dac.py", param1='"i2cAddress": "' + str(i2cAddress) + '"')# del old instances of myself if they are still running

U.toLog(2, "startAtDateTime"+ str(command["startAtDateTime"]))
U.toLog(2, "time.time()    "+ str(time.time()))


if "startAtDateTime" in command:
    try:
        delayStart = max(0,U.calcStartTime(command,"startAtDateTime")-time.time())
        if delayStart > 0:
            U.toLog(2, "delayStart delayed by: "+ str(delayStart))
            time.sleep(delayStart)
    except  Exception, e:
        U.toLog(-1,  u"in Line '%s' has error='%s'" % (sys.exc_traceback.tb_lineno, e))


bus = smbus.SMBus(1)

values=""
if "values" in command:
    values =  command["values"]
    
if "cmd" in command:   cmd =  command["cmd"]
else:                  cmd = "analogWrite"
if cmd =="disable":
    exit()
    
        
#    "values:{analogValue:"analogValue+",pulseUp:"+ pulseUp + ",pulseDown:" + pulseDown + ",nPulses:" + nPulses}

try:
    if "pulseUp" in values:     pulseUp   = max(0.,float(values["pulseUp"])  -0.0003)
    else:                       pulseUp   = 0
    if "pulseDown" in values:   pulseDown = max(0.,float(values["pulseDown"])-0.0003)
    else:                       pulseDown = 0
    if "nPulses" in values:     nPulses   = int(values["nPulses"])
    else:                       nPulses   = 0
    if "analogValue" in values: 
                                analogValue = values["analogValue"]
                                bits = int(float(values["analogValue"])/3300.*255.)
    else:                       
                                bits = 0
                                analogValue = 0
    U.toLog(1, "cmd: "+str(cmd)+"  up:"+str(values["pulseUp"])+"  down:"+str(values["pulseDown"])+"  nPulses:"+str(values["nPulses"])+"  volts:"+str(values["analogValue"]))

    
    if cmd == "analogWrite":
        #U.toLog(2, "analogWrite:"+str(analogValue))
        bus.write_byte_data(int(i2cAddress),0x40, bits)

    elif cmd == "pulseUp":
        #U.toLog(2, "pulse UP:"+str(pulseUp)+"  bits:"+str(bits))
        bus.write_byte_data(int(i2cAddress),0x40, bits)
        time.sleep(pulseUp)
        bus.write_byte_data(int(i2cAddress),0x40, 0)

    elif cmd == "pulseDown":
        #U.toLog(2, "pulse down:"+str(pulseDown)+"  bits:"+str(bits))
        bus.write_byte_data(int(i2cAddress),0x40, 0)
        time.sleep(pulseUp)
        bus.write_byte_data(int(i2cAddress),0x40, bits)

    elif cmd == "continuousUpDown":
        nn=0
        while nn< nPulses:
            nn+=1
            #U.toLog(2, "continuousUpDown: up:"+str(pulseUp)+"  down:"+str(pulseDown)+"  bits:"+str(bits))
            bus.write_byte_data(int(i2cAddress),0x40, bits)
            time.sleep(pulseUp)
            bus.write_byte_data(int(i2cAddress),0x40, 0)
            time.sleep(pulseDown)

    U.removeOutPutFromFutureCommands(i2cAddress+1000, devType)
            

except  Exception, e:
    U.toLog(-1, u"in Line '%s' has error='%s'" % (sys.exc_traceback.tb_lineno, e))
