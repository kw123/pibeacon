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
import	piBeaconUtils	as U
import	piBeaconGlobals as G
import traceback
G.program = "setmcp4725"


def setVoltage(bytes, persist=False):
	try:
		if persist:
			bus.write_i2c_block_data(i2cAddress, 0x60, bytes)
		else:
			bus.write_i2c_block_data(i2cAddress, 0x40, bytes)
	except	Exception as e:
			U.logger.log(30, u"in Line {} has error={}".format(traceback.extract_tb(sys.exc_info()[2])[-1][1], e))

###########
def readParams():
	global allowedGPIOoutputPins
	inp,inpRaw = U.doRead()
	if inp == "": return
	U.getGlobalParams(inp)

######### main ######
U.setLogging()

myPID		= str(os.getpid())
readParams()
U.logger.log(10, "setmcp4725	command :" + unicode(sys.argv))

command = json.loads(sys.argv[1])


i2cAddress = U.getI2cAddress(command, default ="")

if i2cAddress=="":
    U.logger.log(30, "setmcp4725 bad command " + command + "  i2cAddress not included")
    exit(1)
	
if "startAtDateTime" in command:
	try:
		delayStart = max(0,U.calcStartTime(command,"startAtDateTime")-time.time())
		if delayStart > 0:
			time.sleep(delayStart)
	except:
		pass

U.killOldPgm(myPID,"setmcp4725.py", param1='"i2cAddress": "' + str(i2cAddress) + '"')# del old instances of myself if they are still running

U.logger.log(10, "setmcp4725	command " + unicode(command) )

bus = smbus.SMBus(1)

nPulses		= 0
pulseUp		= 0
pulseDown	= 0
analogValue = 0
values		= {}
cmd			= ""
bytes		= [0,0]

if "cmd" in command:
	cmd =  command["cmd"]
	if cmd =="disable":
		exit()
else:
	U.logger.log(30, "setmcp4725	 no cmd given " + unicode(command) )
	exit()
U.logger.log(10, "setmcp4725	cmd " + unicode(cmd) )

if "values" in command:
	values =  command["values"]
if values =="":
	exit()
U.logger.log(30, "setmcp4725	 values " + unicode(values) )

if "analogValue" in values:
	analogValue = int(float(values["analogValue"])/3300 * 4096)
	bits = min( 4095, max(0,analogValue ))
	bytes = [(bits >> 4) & 0xFF, (bits << 4) & 0xFF]
	
if "pulseUp" in values:
	pulseUp	  =	 max(0,float(values["pulseUp"])	 -0.0005)
	
if "pulseDown" in values:
	pulseDown = max(0,float(values["pulseDown"]) -0.0005)
	
if "nPulses" in values:
	nPulses = values["nPulses"]
	
 
badi2c =0
if cmd =="analogWrite":
	try:
		setVoltage(bytes,persist=False)
	except	Exception as e:
		U.logger.log(30, u"in Line {} has error={}".format(traceback.extract_tb(sys.exc_info()[2])[-1][1], e))
	exit()

if cmd =="continuousUpDown":
	try:
		nn=0
		while nn< nPulses:
			nn+=1
			setVoltage(bytes,persist=False)
			time.sleep(pulseUp)
			setVoltage([0,0],persist=False)
			time.sleep(pulseDown)
	except	Exception as e:
		U.logger.log(30, u"in Line {} has error={}".format(traceback.extract_tb(sys.exc_info()[2])[-1][1], e))
	exit()
	
if cmd =="pulseUp":
	try:
		setVoltage(bytes,persist=False)
		time.sleep(pulseUp)
		setVoltage([0,0],persist=False)
	except	Exception as e:
		U.logger.log(30, u"in Line {} has error={}".format(traceback.extract_tb(sys.exc_info()[2])[-1][1], e))
	exit()
	
if cmd =="pulseDown":
	try:
		setVoltage([0,0],persist=False)
		time.sleep(pulseDown)
		setVoltage(bytes,persist=False)
	except	Exception as e:
		U.logger.log(30, u"in Line {} has error={}".format(traceback.extract_tb(sys.exc_info()[2])[-1][1], e))
	exit()
	
U.logger.log(30, u"cmd not implemented: "+cmd)






