#!/usr/bin/python
# -*- coding: utf-8 -*-
# by Karl Wachs
# feb 5 2016
# version 0.9 
##
##	get sensor values and write the to a file in json format for later pickup, 
##	do it in a timed manner not to load the system, is every 1 seconds then 30 senods break
##

import	sys, os, time, json, datetime,subprocess,copy

sys.path.append(os.getcwd())
import	piBeaconUtils	as U
import	piBeaconGlobals as G

G.program = "DHT"
import Adafruit_DHT





# ===========================================================================
# DHT
# ===========================================================================




def getDATAdht(DHTpinI,Type,devId):
		global sensorDHT, startDHT, lastRead
		global lastSensorRead
		t,h="",""
		try:
			ii=startDHT[str(DHTpinI)]
		except:
			if startDHT =="":
				startDHT  = {}
				sensorDHT = {}
			if devId not in lastSensorRead: 
				lastSensorRead[devId] = 0
			startDHT[str(DHTpinI)] = 1
			if Type.lower() == "11":		
				sensorDHT[str(DHTpinI)] = Adafruit_DHT.DHT11
			else:	  
				sensorDHT[str(DHTpinI)] = Adafruit_DHT.DHT22
		try:
			if time.time() - lastSensorRead[devId] < 3.: time.sleep( max(0, min(3.1, 3.5 - (time.time() - lastRead )) ) )
			h, t = Adafruit_DHT.read_retry(sensorDHT[str(DHTpinI)], int(DHTpinI))
			if "{}".format(h) == "None" or "{}".format(t) == "None":
				time.sleep(3.) # min wait between read -s 2.0 secs, give it a little more..
				h, t = Adafruit_DHT.read_retry(sensorDHT[str(DHTpinI)], int(DHTpinI))
				if "{}".format(h) == "None" or "{}".format(t) == "None":
					U.logger.log(20, " return data failed: h:"+"{}".format(h)+" t:"+"{}".format(t)+"  Type:"+"{}".format(Type)+"  pin:"+"{}".format(DHTpinI) )
			#U.logger.log(20, " return data: t:{}, h:{} pin: {}".format(t, h, DHTpinI) )
#			# sensorDHT=""
			lastSensorRead[devId] = time.time() 
			try: return float(t),float(h)
			except: return "",""
			#else: return "" ,""  
		except	Exception as e:
			U.logger.log(20,"", exc_info=True)
			U.logger.log(20, u" pin: "+ str(DHTpinI)+" return value: t={}".format(t)+"; h={}".format(h) )
		lastSensorRead[devId] = time.time() 
		return "",""


def getDHTdata():
	global badSensors
	global sensors, sensor
	try:
		dhtData ={}
		for devId in sensors[sensor]:
			dhtData[devId] = {"temp":"","hum":""}
			t,h = getDATAdht(sensors[sensor][devId]["gpioPin"],sensors[sensor][devId]["dhtType"], devId  )
			dhtData[devId] = {"temp":t,"hum":h}
	except	Exception as e:
		U.logger.log(30,"", exc_info=True)
	return dhtData



def getDHT(dataI):
	global badSensors
	global sensors, sensor
	try:
		dhtData = {}
		if sensor in sensors:
			dataI[sensor]={}
			dhtData = getDHTdata()

			for devId in dhtData:
				t = dhtData[devId]["temp"]
				if t != "":
					try:	
						t = round(float(t) + float(sensors[sensor][devId]["offsetTemp"]),1)
					except: pass
					dataI[sensor][devId] = {"temp":t}
					h = dhtData[devId]["hum"]	
					if h != "":
						try:	h = int(float(h) + float(sensors[sensor][devId]["offsetHum"]))
						except: pass
						dataI[sensor][devId]["hum"] = h
						if devId in badSensors: del badSensors[devId]
					time.sleep(0.1)
				else:
					dataI = incrementBadSensor(devId, data)
	except	Exception as e:
		U.logger.log(30,"", exc_info=True)

	if sensor in dataI and data[sensor]== {}: del dataI[sensor]
	return dataI



def incrementBadSensor(devId, dataI, theText="badSensor"):
	global badSensors, sensor
	try:
		if devId not in badSensors: badSensors[devId] = {"count":0,"text":theText}
		badSensors[devId]["count"] +=1
		badSensors[devId]["text"]  +=theText
		#print badSensors
		if	badSensors[devId]["count"]	> 2:
			if sensor not in dataI: dataI={sensor:{devId:{}}}
			if devId not in dataI[sensor]: dataI[sensor][devId]={}
			dataI[sensor][devId]["badSensor"] = badSensors[devId]["text"]
			del badSensors[devId]
	except	Exception as e:
		U.logger.log(30,"", exc_info=True)
		U.logger.log(30, u"theText{}".format(theText))
	return dataI


		
# ===========================================================================
# sensor end
# ===========================================================================

 
# ===========================================================================
# read params
# ===========================================================================


def readParams():
		global sensorList, sensors, enableTXpinsAsGpio, sensorRefreshSecs
		global output
		global oldRaw, lastRead

		rCode= False

		inp,inpRaw,lastRead2 = U.doRead(lastTimeStamp=lastRead)
		if inp == "": return rCode
		if lastRead2 == lastRead: return rCode
		lastRead  = lastRead2
		if inpRaw == oldRaw: return 
		oldRaw	   = inpRaw

		oldSensor  = sensorList
		sensorsOld = copy.copy(sensors)
		outputOld  = "{}".format(output)


		U.getGlobalParams(inp)
		if "output"				  in inp: output=				   (inp["output"])
		if "sensors"			  in inp: sensors =				   (inp["sensors"])
		if "sensorRefreshSecs"	  in inp: sensorRefreshSecs = float(inp["sensorRefreshSecs"])

		sensorList=""
		for sens in sensors:
			sensorList+=sens.split("-")[0]+","

		if sensorList.find("DHT") ==-1:
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
			 
global sensorList, sensors,badSensors, sensor
global startDHT
global regularCycle
global oldRaw, lastRead
global sensorRefreshSecs, lastSensorRead


sensorRefreshSecs	= 90
oldRaw				= ""
lastRead			= 0
lastSensorRead		= {}
startDHT			= ""
loopCount			= 0
sensorList			= []
sensors				= {}
DHTpin				= 17
enableTXpinsAsGpio	= "0"
quick				= False
output				= {}
sensor				= "DHT"

U.setLogging()

readParams()
if U.getIPNumber() > 0:
	U.logger.log(30," getsensors no ip number  exiting ")
	time.sleep(10)
	exit()


myPID		= str(os.getpid())
U.killOldPgm(myPID,G.program+".py")# kill old instances of myself if they are still running

NSleep= int(sensorRefreshSecs)
if G.networkType  in G.useNetwork and U.getNetwork() == "off": 
	if U.getIPNumber() > 0:
		U.logger.log(30," no ip number working, giving up")
		time.sleep(10)

eth0IP, wifi0IP, G.eth0Enabled,G.wifiEnabled = U.getIPCONFIG()


tt					= time.time()
badSensors			= {}
lastData			= {}
lastMsg				= 0
lastAliveSend		= tt
G.tStart			= tt
lastregularCycle	= tt
lastRead			= tt
regularCycle		= True
lastData			= {}
xxx 				= -1
while True:
	try:
		tt = time.time()
		data = {}

		if regularCycle:
			data = getDHT(data)

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
							U.logger.log(10,"{}  {}  {}".format(devid, lastData[sens][devid], data[sens][devid]))
							xxx = U.testBad( data[sens][devid][devType],lastData[sens][devid][devType], xxx )
							if xxx > (G.deltaChangedSensor/100.): 
								changed = xxx
								break
						except	Exception as e:
							#print e
							#print lastData[sens][dd]
							#print data[sens][dd]
							changed= 7
							break

		if data !={} and (	changed > 0 or	( (tt-lastMsg) >  G.sendToIndigoSecs  or (tt-lastMsg) > 120	 )		 ):
			lastMsg = tt
			lastData=copy.copy(data)
			try:
				#U.logger.log(10, u"sending url: {}".format(data))
				U.sendURL({"sensors":data})
			except	Exception as e:
				U.logger.log(30,"", exc_info=True)
			time.sleep(0.05)

		quick = U.checkNowFile(G.program)				 

		U.makeDATfile(G.program, {"sensors":data})
		U.echoLastAlive(G.program)


		tt= time.time()
		NSleep = max(3.5, int(sensorRefreshSecs)*2) 
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
	except	Exception as e:
		U.logger.log(30,"", exc_info=True)
		time.sleep(5.)
sys.exit(0)
