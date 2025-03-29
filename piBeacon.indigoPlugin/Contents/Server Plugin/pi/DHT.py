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
#import Adafruit_DHT

import adafruit_dht
import board




# ===========================================================================
# DHT
# ===========================================================================




def getDATAdht(DHTpinI,Type,devId):
		global sensorDHT, startDHT, lastRead
		global lastSensorRead
		t,h="",""
		pin = str(DHTpinI)
		try:
			ii=int(startDHT[pin])
		except:
			if startDHT =="":
				startDHT  = {}
				sensorDHT = {}
			startDHT[pin] = 1
			if Type.lower() == "11":	
				if pin == "17": sensorDHT[pin] = adafruit_dht.DHT11(board.D17,use_pulseio=False)
				if pin == "27": sensorDHT[pin] = adafruit_dht.DHT11(board.D27,use_pulseio=False)
				if pin == "22": sensorDHT[pin] = adafruit_dht.DHT11(board.D22,use_pulseio=False)
				if pin == "5":  sensorDHT[pin] = adafruit_dht.DHT11(board.D5, use_pulseio=False)
				if pin == "6":  sensorDHT[pin] = adafruit_dht.DHT11(board.D6, use_pulseio=False)
				if pin == "13": sensorDHT[pin] = adafruit_dht.DHT11(board.D13,use_pulseio=False)
				if pin == "19": sensorDHT[pin] = adafruit_dht.DHT11(board.D19,use_pulseio=False)
				if pin == "26": sensorDHT[pin] = adafruit_dht.DHT11(board.D26,use_pulseio=False)
				if pin == "21": sensorDHT[pin] = adafruit_dht.DHT11(board.D21,use_pulseio=False)
				if pin == "20": sensorDHT[pin] = adafruit_dht.DHT11(board.D20,use_pulseio=False)
				if pin == "16": sensorDHT[pin] = adafruit_dht.DHT11(board.D16,use_pulseio=False)
				if pin == "12": sensorDHT[pin] = adafruit_dht.DHT11(board.D16,use_pulseio=False)
				if pin == "25": sensorDHT[pin] = adafruit_dht.DHT11(board.D25,use_pulseio=False)
				if pin == "24": sensorDHT[pin] = adafruit_dht.DHT11(board.D24,use_pulseio=False)
				if pin == "23": sensorDHT[pin] = adafruit_dht.DHT11(board.D23,use_pulseio=False)
			else:	  
				if pin == "17": sensorDHT[pin] = adafruit_dht.DHT22(board.D17,use_pulseio=False)
				if pin == "27": sensorDHT[pin] = adafruit_dht.DHT22(board.D27,use_pulseio=False)
				if pin == "22": sensorDHT[pin] = adafruit_dht.DHT22(board.D22,use_pulseio=False)
				if pin == "5":  sensorDHT[pin] = adafruit_dht.DHT22(board.D5, use_pulseio=False)
				if pin == "6":  sensorDHT[pin] = adafruit_dht.DHT22(board.D6, use_pulseio=False)
				if pin == "13": sensorDHT[pin] = adafruit_dht.DHT22(board.D13,use_pulseio=False)
				if pin == "19": sensorDHT[pin] = adafruit_dht.DHT22(board.D19,use_pulseio=False)
				if pin == "26": sensorDHT[pin] = adafruit_dht.DHT22(board.D26,use_pulseio=False)
				if pin == "21": sensorDHT[pin] = adafruit_dht.DHT22(board.D21,use_pulseio=False)
				if pin == "20": sensorDHT[pin] = adafruit_dht.DHT22(board.D20,use_pulseio=False)
				if pin == "16": sensorDHT[pin] = adafruit_dht.DHT22(board.D16,use_pulseio=False)
				if pin == "12": sensorDHT[pin] = adafruit_dht.DHT22(board.D12,use_pulseio=False)
				if pin == "25": sensorDHT[pin] = adafruit_dht.DHT22(board.D25,use_pulseio=False)
				if pin == "24": sensorDHT[pin] = adafruit_dht.DHT22(board.D24,use_pulseio=False)
				if pin == "23": sensorDHT[pin] = adafruit_dht.DHT22(board.D23,use_pulseio=False)
				U.logger.log(20,"setup DHT pin:{}, sensor:{}".format(pin, sensorDHT[pin] ) )
		try:
			if devId not in lastSensorRead: 
				lastSensorRead[devId] = time.time()

			if time.time() - lastSensorRead[devId] < 3.: time.sleep( max(0, min(3.1, 3.5 - (time.time() - lastRead )) ) )
			for ii in range(10):
				t = ""
				h = ""
				try:
					#U.logger.log(20,"    pin: reading t".format(pin) )
					t = sensorDHT[pin].temperature
					h = sensorDHT[pin].humidity
					t = round(t,1)
					h = round(h,1)
					#U.logger.log(20,"ok  pin:{}  t={};  h={}".format(pin, t, h) )
					break
				except:
					#U.logger.log(20,"err pin:{}  t={};  h={}".format(pin, t, h) )
					time.sleep(3)
			lastSensorRead[devId] = time.time() 
			return t , h 
		except Exception as e:
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
	except Exception as e:
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
	except Exception as e:
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
	except Exception as e:
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

		inp, inpRaw, lastRead2 = U.doRead(lastTimeStamp=lastRead)
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
		#if "sensorRefreshSecs"	  in inp: sensorRefreshSecs = float(inp["sensorRefreshSecs"])

		sensorList=""
		for sens in sensors:
			sensorList+=sens.split("-")[0]+","

		if sensorList.find("DHT") ==-1:
			U.logger.log(30,"no {} sensor defined, exiting ".format(G.program ))
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


sensorRefreshSecs	= 10
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

U.logger.log(30,"starting sensor")


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
		if lastData == {}: 
			changed = 1
		else:
			for sens in data:
				if changed > 0: break
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
							#U.logger.log(20,"{}  old:{}  new:{}".format(devid, lastData[sens][devid], data[sens][devid]))
							xxx = U.testBad( data[sens][devid][devType],lastData[sens][devid][devType], xxx )
							if xxx > (G.deltaChangedSensor/100.): 
								changed = xxx
								break
						except Exception as e:
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
			except Exception as e:
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
	except Exception as e:
		U.logger.log(30,"", exc_info=True)
		time.sleep(5.)
sys.exit(0)
