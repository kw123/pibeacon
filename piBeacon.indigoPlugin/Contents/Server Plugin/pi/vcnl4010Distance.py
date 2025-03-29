#!/usr/bin/env python
# -*- coding: utf-8 -*-


""" 

 vcnl40xx  ToF range finder program

"""


import sys, os, time, json, datetime,subprocess,copy
import smbus

sys.path.append(os.getcwd())
import  piBeaconUtils   as U
import  piBeaconGlobals as G

G.program = "vcnl4010Distance"
import  displayDistance as DISP

# ===========================================================================
# read params
# ===========================================================================

#################################		
def readParams():
	global sensorList, sensors, logDir, sensor,  sensorRefreshSecs, dynamic, mode, deltaDist, deltaDistAbs,displayEnable
	global output, sensorActive, timing, sensCl, distanceUnits
	global distanceOffset, distanceMax
	global oldRaw, lastRead
	try:


		inp, inpRaw, lastRead2 = U.doRead(lastTimeStamp=lastRead)
		if inp == "": return False
		if lastRead2 == lastRead: return False
		lastRead   = lastRead2
		if inpRaw == oldRaw: return False
		oldRaw	 = inpRaw


		externalSensor = False
		sensorList=[]
		sensorsOld= copy.copy(sensors)

		U.getGlobalParams(inp)
		  
		if "sensorList"		in inp:  sensorList=		inp["sensorList"]
		if "sensors"		in inp:  sensors =			inp["sensors"]
		if "distanceUnits"	in inp:  distanceUnits=		inp["distanceUnits"]
		
		if "output"			 in inp:  output=			inp["output"]

		if sensor not in sensors:
			U.logger.log(20, "{} is not in parameters = not enabled, stopping".format(G.program) )
			time.sleep(1)
			U.killOldPgm(-1,G.program+".py")
			sys.exit(0)
			
 
		sensorChanged = doWeNeedToStartSensor(sensors,sensorsOld,sensor)


		if sensorChanged != 0: # something has changed
			if os.path.isfile(G.homeDir+"temp/"+sensor+".dat"):
				os.remove(G.homeDir+"temp/"+sensor+".dat")
				
		dynamic = False
		deltaDist = {}
		deltaDistAbs = {}
		for devId in sensors[sensor]:
			deltaDist[devId]  = 0.1
			try:
				xx = sensors[sensor][devId]["sensorRefreshSecs"].split("#")
				sensorRefreshSecs = float(xx[0]) 
				if sensorRefreshSecs  < 0: dynamic=True
				if len(xx)==2: 
					try: mode = int(xx[1])
					except: mode =0
			except:
				sensorRefreshSecs = 2	
				mode =0

			try:
				if "displayEnable" in sensors[sensor][devId]: 
					displayEnable = sensors[sensor][devId]["displayEnable"]
			except:
				display = False	

			try:	deltaDist[devId] = float(sensors[sensor][devId].get("deltaDist",10))/100.
			except: deltaDist[devId] = 0.1

			try:	deltaDistAbs[devId] = float(sensors[sensor][devId].get("deltaDistAbs",10))
			except: deltaDistAbs[devId] = 10.

			try:
				if "dUnits" in sensors[sensor][devId] and sensors[sensor][devId]["dUnits"] !="":
					distanceUnits = sensors[sensor][devId]["dUnits"]
			except  Exception as e:
				pass

			try:
				if True:												maxCurrent = 8
				if "maxCurrent" in sensors[sensor][devId]:				maxCurrent = int(sensors[sensor][devId]["maxCurrent"])
			except:														maxCurrent = 8
			if devId not in distanceMax:
					distanceMax[devId]	= int(5000*(maxCurrent/2.))

			#print sensorChanged, sensorActive, distanceMax
			if sensorChanged == 1:
				if not sensorActive:
					U.logger.log(30,"==== Start ranging =====")
					sensCl = VCNL40xx(address=0x13,maxCurrent=maxCurrent)
			sensorActive = True
			U.readDistanceSensor(devId, sensors, sensor)
			
			
		if sensorChanged == -1:
			U.logger.log(30, "==== stop  ranging =====")
			exit()
			return  True


	except  Exception as e:
		U.logger.log(30,"", exc_info=True)
	return  True




#################################
def doWeNeedToStartSensor(sensors,sensorsOld,selectedSensor):
	if selectedSensor not in sensors:	return -1
	if selectedSensor not in sensorsOld: return 1

	for devId in sensors[selectedSensor] :
			if devId not in sensorsOld[selectedSensor] :			return 1
			for prop in sensors[sensor][devId] :
				if prop not in sensorsOld[selectedSensor][devId] :  return 1
				if sensors[selectedSensor][devId][prop] != sensorsOld[selectedSensor][devId][prop]:
					return 1
   
	for devId in sensorsOld[selectedSensor]:
			if devId not in sensors[selectedSensor] :			   return 1
			for prop in sensorsOld[selectedSensor][devId] :
				if prop not in sensors[selectedSensor][devId] :	 return 1

	return 0




# The MIT License (MIT)
#
# Copyright (c) 2016 Adafruit Industries
#
# Permission is hereby granted, free of charge, to any person obtaining a copy
# of this software and associated documentation files (the "Software"), to deal
# in the Software without restriction, including without limitation the rights
# to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
# copies of the Software, and to permit persons to whom the Software is
# furnished to do so, subject to the following conditions:
#
# The above copyright notice and this permission notice shall be included in all
# copies or substantial portions of the Software.
#
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
# IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
# FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
# AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
# LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
# OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
# SOFTWARE.
import time
import smbus


# Common VCNL40xx constants:
VCNL40xx_ADDRESS		  = 0x13
VCNL40xx_COMMAND		  = 0x80
VCNL40xx_PRODUCTID		= 0x81
VCNL40xx_IRLED			= 0x83
VCNL40xx_AMBIENTPARAMETER = 0x84
VCNL40xx_AMBIENTDATA	  = 0x85
VCNL40xx_PROXIMITYDATA	= 0x87
VCNL40xx_PROXIMITYADJUST  = 0x8A
VCNL40xx_3M125			= 0
VCNL40xx_1M5625		   = 1
VCNL40xx_781K25		   = 2
VCNL40xx_390K625		  = 3
VCNL40xx_MEASUREAMBIENT   = 0x10
VCNL40xx_MEASUREPROXIMITY = 0x08
VCNL40xx_AMBIENTREADY	 = 0x40
VCNL40xx_PROXIMITYREADY   = 0x20

# VCBL4000 constants:
VCNL4000_SIGNALFREQ	   = 0x89

# VCNL4010 constants:
VCNL4010_PROXRATE		 = 0x82
VCNL4010_INTCONTROL	   = 0x89
VCNL4010_INTSTAT		  = 0x8E
VCNL4010_MODTIMING		= 0x8F
VCNL4010_INT_PROX_READY   = 0x80
VCNL4010_INT_ALS_READY	= 0x40



class VCNL40xx():

	def __init__(self,address=VCNL40xx_ADDRESS,maxCurrent=10):
		self.bus = smbus.SMBus(1)
		self.address = address
		
		self.bus.write_byte_data(self.address, VCNL4010_INTCONTROL, 0x0)
		# VCNL4010 address, 0x13(19)
		# Select command register, 0x80(128)
		#		0xFF(255)	Enable ALS and proximity measurement, LP oscillator
		self.bus.write_byte_data(self.address, VCNL40xx_COMMAND, 0xff)# 1<<1|1<<2)
		# VCNL4010 address, 0x13(19)
		# set ir-led current 
		self.bus.write_byte_data(self.address, VCNL40xx_IRLED,maxCurrent) #  0-20 = 0- 200mA
		# Select proximity rate register, 0x82(130)
		self.bus.write_byte_data(self.address, VCNL4010_PROXRATE,1<<1|1) # = 00000011 = 16 measuremnts per second
		# VCNL4010 address, 0x13(19)
		# Select ambient light register, 0x84(132)
		self.bus.write_byte_data(self.address, VCNL40xx_AMBIENTPARAMETER, 1<<7|1<<6|1<<5|1<<4|1<<3|1<<2) # 1 1110000 = cont. conversion + 10 samples per second + 1000 = auto offset


	def read_Data(self, timeout_sec=1):
		try:
			data = self.bus.read_i2c_block_data(self.address, 0x85, 4)
			luminance = data[0] * 256 + data[1]
			distance  = max(1, data[2] * 256 + data[3] - 8*256 -90)
			
			return   distance, luminance, data
			#return self._device.readU16BE(VCNL40xx_AMBIENTDATA)
		except  Exception as e:
			U.logger.log(30,"", exc_info=True)
		return "","",[]


	   
#################################
def readSensor():
	global sensor, sensors,  sensCl, badSensor, distanceMax
	global actionDistanceOld, actionShortDistance, actionShortDistanceLimit, actionMediumDistance, actionLongDistance, actionLongDistanceLimit
	global distance0Offset, distance0Max
	distance   = "badSensor"
	luminance  = ""
	try:
		for ii in range(2):
			tof0, luminance, data = sensCl.read_Data()
			if tof0 != "":
				#if tof0 < distance0Offset: distance0Offset= tof0
				#if tof0 > distance0Max: distance0Max = tof0
				tof = max (1, tof0 - distance0Offset)
				distance = (distance0Max / tof )/20.# in cm 
				badSensor = 0
								
				return  distance, luminance #  return in cm/lux
			time.sleep(0.02)

		badSensor += 1
		if badSensor >30: 
			badSensor = 0
			return "badSensor", ""
	except  Exception as e:
			U.logger.log(30,"", exc_info=True)
			U.logger.log(30, u"distance>>{}<<".format(distance))
	return "",""	 




############################################
global distanceOffset, distanceMax, inpRaw, deltaDist, deltaDistAbs, deltaDistAbs
global sensor, sensors, first, badSensor, sensorActive
global oldRaw,  lastRead, sensCl, distance0Offset, distance0Max


distance0Offset				= 140
distance0Max				= 63397
sensCl						= ""

oldRaw						= ""
lastRead					= 0
maxRange					= 20.

distanceOffset				= {}
distanceMax					= {}
first						= False
loopCount					= 0
sensorRefreshSecs			= 2
NSleep						= 100
sensorList					= []
sensors						= {}
sensor						= G.program
quick						= False
lastMsg						= 0
dynamic						= False
mode						= 0
display						= "0"
output						= {}
badSensor					= 0
sensorActive				= False
loopSleep					= 0.1
sendEvery					= 30.
U.setLogging()

myPID	   = str(os.getpid())
U.killOldPgm(myPID,G.program+".py")# kill old instances of myself if they are still running

if U.getIPNumber() > 0:
	time.sleep(10)
	exit()

# Create a VCNL4010/4000 instance.

readParams()


time.sleep(1)
lastRead = time.time()

U.echoLastAlive(G.program)

lastDist			= {}
lastData			= {}
lastTime			= {}
lastSend			= 0
lastDisplay			= 0
maxDeltaSpeed		= 40. # = mm/sec
lastRead			= time.time()
G.lastAliveSend		= time.time() -1000
lastLux				= -999999
lastLux2			= 0
tt0					= time.time()

while True:
	try:
		if sensCl == "":
			time.sleep(20)
			break
		tt = time.time()
		data = {}
		data["sensors"]     = {}
		if sensor in sensors:
			data["sensors"][sensor] = {}
			for devId in sensors[sensor]:
				data["sensors"][sensor][devId] = {}
				if devId not in lastDist: 
					lastDist[devId] =-500.
					lastTime[devId] =0.
				dist, lux =readSensor()

				if dist == "":
					continue

				if dist == "badSensor":
					U.logger.log(30," bad sensor")
					data["sensors"][sensor][devId]["distance"]="badSensor"
					U.sendURL(data)
					lastDist[devId] =-100.
					continue

				if lux != "": 
							data["sensors"][sensor][devId]["Illuminance"] =lux
							lastLux2 = lastLux
							lastLux  = float(lux)
				else:
							data["sensors"][sensor][devId]["Illuminance"] = lastLux

				#U.logger.log(20, "{}  {}".format(dist, lux) ) 
				dist = round(float(dist),1)
				if dist > maxRange: dist = 999
				delta  = dist - lastDist[devId]
				deltaA = abs(dist - lastDist[devId])
				deltaT = max(tt   - lastTime[devId],0.01)
				speed  = delta / deltaT
				deltaN = deltaA / max (0.5,(dist+lastDist[devId])/2.)
				regionEvents = U.doActionDistance(dist, speed, devId)

				trigDD 	= deltaN > deltaDist[devId]
				trigDDa	= deltaA > deltaDistAbs[devId]
				trigDT	= tt - sendEvery > lastTime[devId]	
				trigQi	= quick
				trigL	= abs(lastLux2 - lastLux) / max(1.,lastLux2 + lastLux) > deltaDist[devId]
				if ( trigDD and trigDDa ) or trigDT or trigQi or trigL or regionEvents[2]: 
							trig = ""
							if trigL: 					trig +="Light;"
							if trigDD or trigDDa:		trig +="Dist;"
							if trigDT: 					trig +="Time;"
							if regionEvents[0] != "": 		
								trig += "distanceEvent"
								data["sensors"][sensor][devId]["distanceEvent"]	= regionEvents[0]
							data["sensors"][sensor][devId]["stopped"]	= regionEvents[1]
							trig = trig.strip(";")
							data["sensors"][sensor][devId]["trigger"]	= trig
							data["sensors"][sensor][devId]["distance"]	= dist
							data["sensors"][sensor][devId]["speed"] 	= round(speed,2)
							U.sendURL(data)
							lastDist[devId]  = dist
							lastTime[devId]  = tt
							G.lastAliveSend = tt

				if displayEnable not in ["","0"]:
					DISP.displayDistance(dist, sensor, sensors, output, distanceUnits)
					#print datetime.datetime.now().strftime("%Y%m%d-%H:%M:%S"),sensor, dist , deltaDist   

		loopCount +=1
		
		U.makeDATfile(G.program, data)

		quick = U.checkNowFile(G.program)				

		U.echoLastAlive(G.program)

		
		#U.logger.log(20, "loopCount:{}  quick:{}".format(loopCount, quick) )   
		if loopCount %20 == 0 and not quick:
			if tt - lastRead > 5.:  
				if readParams(): break 
				lastRead = tt
		time.sleep(sensorRefreshSecs)
		#print "end of loop", loopCount
	except  Exception as e:
		U.logger.log(30,"", exc_info=True)
		time.sleep(5.)
try: 	G.sendThread["run"] = False; time.sleep(1)
except: pass
sys.exit(0)
