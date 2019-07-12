#!/usr/bin/python
# -*- coding: utf-8 -*-
## adopted from adafruit 
#
#

import sys, os, time, json, datetime,subprocess,copy
import smbus

sys.path.append(os.getcwd())
import	piBeaconUtils	as U
import	piBeaconGlobals as G
G.program = "si7021"
G.debug = 0


# ===========================================================================
# INA219 Class
# ===========================================================================
class si7021:

	 # Constructor
	def __init__(self, i2cAddress=""):


		if i2cAddress =="" or i2cAddress ==0:
			self.i2cAddress = 0x40
		else:
			self.i2cAddress = i2cAddress
				
		self.bus = smbus.SMBus(1)

	def getdata(self):
		try:
			result= self.bus.write_byte(self.i2cAddress,0xF5)
			time.sleep(0.3)
			r1 = self.bus.read_byte(self.i2cAddress)
			r2 = self.bus.read_byte(self.i2cAddress)
			#print "hum", r1, r2
			hum = ((r1*256+ r2)*125 / 65536.0) - 6	  
			result= self.bus.write_byte(self.i2cAddress,0xF3)
			time.sleep(0.3)
			r1 = self.bus.read_byte(self.i2cAddress)
			r2 = self.bus.read_byte(self.i2cAddress)
			#print "temp", r1, r2 
			temp = ( (r1 * 256 + r2) * 175.72 / 65536.0) - 46.85 
			return temp,hum
		except	Exception, e:
			U.toLog(-1, u"in Line {} has error={}".format(sys.exc_traceback.tb_lineno, e))
			return "",""
 # ===========================================================================
# read params
# ===========================================================================

#################################		 
def readParams():
	global sensorList, sensors, logDir, sensor,	 sensorRefreshSecs
	global rawOld
	global deltaX, SI7021sensor, minSendDelta
	global oldRaw, lastRead
	try:



		inp,inpRaw,lastRead2 = U.doRead(lastTimeStamp=lastRead)
		if inp == "": return
		if lastRead2 == lastRead: return
		lastRead   = lastRead2
		if inpRaw == oldRaw: return
		oldRaw	   = inpRaw
		
		externalSensor=False
		sensorList=[]
		sensorsOld= copy.copy(sensors)


		
		U.getGlobalParams(inp)
		  
		if "sensorList"			in inp:	 sensorList=			 (inp["sensorList"])
		if "sensors"			in inp:	 sensors =				 (inp["sensors"])
		if "debugRPI"			in inp:	 G.debug=			  int(inp["debugRPI"]["debugRPISENSOR"])
		
 
		if sensor not in sensors:
			U.toLog(-1, G.program+" is not in parameters = not enabled, stopping "+G.program+".py" )
			exit()
			
				
		deltaX={}
		for devId in sensors[sensor]:
			deltaX[devId]  = 0.1
			try:
				xx = sensors[sensor][devId]["sensorRefreshSecs"].split("#")
				sensorRefreshSecs = float(xx[0]) 
			except:
				sensorRefreshSecs = 90	  


			try:
				if "i2cAddress" in sensors[sensor][devId]: 
					i2cAddress = int(sensors[sensor][devId]["i2cAddress"])
			except:
				i2cAddress = ""	   

			try:
				if "deltaX" in sensors[sensor][devId]: 
					deltaX[devId]= float(sensors[sensor][devId]["deltaX"])/100.
			except:
				deltaX[devId] = 0.05

			try:
				if "minSendDelta" in sensors[sensor][devId]: 
					minSendDelta= float(sensors[sensor][devId]["minSendDelta"])/100.
			except:
				minSendDelta = 5.

				
			if devId not in SI7021sensor:
				U.toLog(-1,"==== Start "+G.program+" ===== @ i2c= " +unicode(i2cAddress))
				i2cAdd = U.muxTCA9548A(sensors[sensor][devId])
				SI7021sensor[devId] = si7021(i2cAddress=i2cAdd)
				U.muxTCA9548Areset()
				
		deldevID={}		   
		for devId in SI7021sensor:
			if devId not in sensors[sensor]:
				deldevID[devId]=1
		for dd in  deldevID:
			del SI7021sensor[dd]
		if len(SI7021sensor) ==0: 
			####exit()
			pass

	except	Exception, e:
		U.toLog(-1, u"in Line {} has error={}".format(sys.exc_traceback.tb_lineno, e))



#################################
def getValues(devId):
	global sensor, sensors,	 SI7021sensor, badSensor

	i2cAdd = U.muxTCA9548A(sensors[sensor][devId])
	temp = ""
	hum = ""
	try:
		temp,hum	 = SI7021sensor[devId].getdata()
		if temp =="" or hum =="" :
			badSensor+=1
			U.muxTCA9548Areset()
			return "badSensor"
		data = {"temp":round(temp,1), "hum":round(hum,1)}
		badSensor = 0
		U.muxTCA9548Areset()
		return data
	except	Exception, e:
		if badSensor >2 and badSensor < 5: 
			U.toLog(-1, u"in Line {} has error={}".format(sys.exc_traceback.tb_lineno, e))
			U.toLog(-1, u"temp>>{}<<".format(temp) )
		badSensor+=1
	if badSensor >3: 
		U.muxTCA9548Areset()
		return "badSensor"
	U.muxTCA9548Areset()
	return ""		 






############################################
global rawOld
global sensor, sensors, badSensor
global deltaX, SI7021sensor, minSendDelta
global oldRaw, lastRead

oldRaw						=""
lastRead					= 0

minSendDelta				= 5.
G.debug						= 5
loopCount					= 0
sensorRefreshSecs			= 60
NSleep						= 100
sensorList					= []
sensors						= {}
sensor						= G.program
quick						= False
output						= {}
badSensor					= 0
sensorActive				= False
loopSleep					= 0.5
rawOld						= ""
SI7021sensor				={}
deltaX						= {}
myPID		= str(os.getpid())
U.killOldPgm(myPID,G.program+".py")# kill old instances of myself if they are still running


if U.getIPNumber() > 0:
	time.sleep(10)
	exit()

readParams()

time.sleep(1)

lastRead = time.time()

U.echoLastAlive(G.program)




lastValue		  = {}
lastData			= {}
lastSend			= 0
lastRead			= time.time()
G.lastAliveSend		= time.time() -1000

sensorWasBad = False
while True:
	try:
		tt	 = time.time()
		data = {"sensors": {}}
		if sensor in sensors:
			for devId in sensors[sensor]:
				if devId not in lastValue: lastValue[devId] =-500.
				values = getValues(devId)
				if values == "": continue
				data["sensors"] = {sensor:{}}
				data["sensors"][sensor] = {devId:{}}
				if values =="badSensor":
					sensorWasBad = True
					data["sensors"][sensor][devId]["Current"]="badSensor"
					if badSensor < 5: 
						U.toLog(-1," bad sensor")
						U.sendURL(data)
					lastValue[devId] =-100.
					continue
				elif values["temp"] !="" :
					if sensorWasBad: # sensor was bad, back up again, need to do a restart to set config 
						U.restartMyself(reason=" back from bad sensor, need to restart to get sensors reset",doPrint="False")
					
					data["sensors"][sensor][devId] = values
					current = float(values["temp"])
					delta	= current-lastValue[devId]
					deltaN	= abs(delta) / max (0.5,(current+lastValue[devId])/2.)
				else:
					continue
				
				if ( ( deltaN > deltaX[devId]						   ) or 
					 (	tt - abs(G.sendToIndigoSecs) > G.lastAliveSend	) or  
					 ( quick										   )   ) and  \
				   ( ( tt - G.lastAliveSend > minSendDelta			   )   ):
						U.sendURL(data)
						lastValue[devId]  = current

		loopCount +=1

		U.makeDATfile(G.program, data)
		quick = U.checkNowFile(G.program)				 
		U.echoLastAlive(G.program)

		if loopCount %40 ==0 and not quick:
			tt= time.time()
			if tt - lastRead > 5.:	
				readParams()
				lastRead = tt
		if not quick:
			time.sleep(loopSleep)
		
	except	Exception, e:
		U.toLog(-1, u"in Line {} has error={}".format(sys.exc_traceback.tb_lineno, e))
		time.sleep(5.)
sys.exit(0)
