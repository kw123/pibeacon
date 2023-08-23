#! /usr/bin/env python3
# -*- coding: utf-8 -*-
####################
import time

import sys, os, time, json, datetime,subprocess,copy
import logging
from datetime import timedelta
import adafruit_scd4x
import board

i2c = board.I2C()  # uses board.SCL and board.SDA

sys.path.append(os.getcwd())
import	piBeaconUtils	as U
import	piBeaconGlobals as G

G.program = "sensirionscd40"




###############################
###############################
class SENSORclass():
	def __init__(self,  fastSlow="fast"):
		i2c_addr=0x62
		self._i2c_addr = i2c_addr

		try:
			self.forceCalibration = 0
			self.thisSensor = adafruit_scd4x.SCD4X(i2c)
			time.sleep(0.1)
			self.thisSensor.stop_periodic_measurement()
			if fastSlow == "slow":
				self.thisSensor.start_low_periodic_measurement()
			else:
				self.thisSensor.start_periodic_measurement()

			time.sleep(2)

		except Exception as e:
			U.logger.log(30,"", exc_info=True)
			try: del self.thisSensor 
			except: pass
		return 

	def getData(self): 
		try:
			if self.thisSensor.data_ready:
				return  self.thisSensor.read_data()
			else:
				return "notready", 0, ""
		except Exception as e:
			U.logger.log(20,"getData ", exc_info=True)
			time.sleep(5)
		return "","",""



	def get_auto_self_calibration_active(self):
		return self.thisSensor.self_calibration_enabled 

	def get_AltitudeCompensation(self):
		return self.thisSensor.altitude 

	def get_Force_self_calibration(self):
		return self.forceCalibration

	def get_temperature_offset():
		return self.thisSensor.temperature_offset

	def serialNumber(self):
		return self.thisSensor.serial_number


	def stop_measurements(self):
		self.thisSensor.stop_periodic_measurement()
		return 

	def start_measurements(self):
		self.thisSensor.start_periodic_measurement()
		return 

	def start_30sec_measurements(self,meter):
		self.start_low_periodic_measurement()
		return 

	def set_altitude(self,meter):
		self.thisSensor.altitude = meter
		return



	def set_auto_self_calibration_active(self, onOff):
		if onOff : value = 1
		else: value = 0
		self.thisSensor.self_calibration_enabled = onOff
		return 

	def set_Force_self_calibration(self, pOffset):
		self.forceCalibration = pOffset
		self.thisSensor.force_calibration(pOffset)
		return 

	def set_temperature_offset(self, toffset):
		self.thisSensor.force_calibration(toffset)
		return 

	def soft_reset(self):
		self.thisSensor.reinit()

	def set_Reset(self):
		self.thisSensor.factory_reset()
		return 


# ===========================================================================
# read params
# ===========================================================================

###############################
def readParams():
	global sensorList, sensors, logDir, sensor,	 sensorRefreshSecs, displayEnable
	global deltaX, SENSOR, minSendDelta, sensorMode
	global oldRaw, lastRead
	global startTime, lastMeasurement, sendToIndigoSecs
	try:



		inp,inpRaw,lastRead2 = U.doRead(lastTimeStamp=lastRead)
		if inp == "": return
		if lastRead2 == lastRead: return
		lastRead   = lastRead2
		if inpRaw == oldRaw: return
		oldRaw	   = inpRaw
		
		externalSensor = False
		sensorList = []
		sensorsOld = copy.copy(sensors)

		U.getGlobalParams(inp)
		  
		if "sensorList"			in inp:	 sensorList=			 (inp["sensorList"])
		if "sensors"			in inp:	 sensors =				 (inp["sensors"])
		
 
		if sensor not in sensors:
			U.logger.log(30, "{} is not in parameters = not enabled, stopping {}.py".format(G.program,G.program) )
			exit()
			

		U.logger.log(10,"{} reading new parameters".format(G.program) )

		if sensor not in sensorsOld:
			sensorsOld[sensor] = {}

		deltaX={}
		restart = False
		sendToIndigoSecs = G.sendToIndigoSecs	
		for devId in sensors[sensor]:
			if devId not in sensorsOld[sensor]:
				 sensorsOld[sensor][devId] = {}

			try:
				if devId not in deltaX: deltaX[devId]  = 2
				if "deltaX" in sensors[sensor][devId]: 
					deltaX[devId]= float(sensors[sensor][devId]["deltaX"])/100.
			except:
				deltaX[devId] = 2

			delSens = False


			if sensors[sensor][devId].get("altitudeCompensation","")  		!= sensorsOld[sensor][devId].get("altitudeCompensation",""):
				delSens = True

			if sensors[sensor][devId].get("autoCalibration","1")  			!= sensorsOld[sensor][devId].get("autoCalibration","1"):
				delSens = True

			if sensors[sensor][devId].get("sensorTemperatureOffset","")		!= sensorsOld[sensor][devId].get("sensorTemperatureOffset",""):
				delSens = True

			if sensors[sensor][devId].get("fastSlowRead","fast")			!= sensorsOld[sensor][devId].get("fastSlowRead","fast"):
				delSens = True

			if "altitudeCompensation"		not in sensors[sensor][devId]:	sensors[sensor][devId]["altitudeCompensation"] 		= ""
			if "autoCalibration" 			not in sensors[sensor][devId]:	sensors[sensor][devId]["autoCalibration"] 			= "1"
			if "sensorTemperatureOffset" 	not in sensors[sensor][devId]:	sensors[sensor][devId]["sensorTemperatureOffset"] 	= ""
			if "fastSlowRead" 				not in sensors[sensor][devId]:	sensors[sensor][devId]["fastSlowRead"] 				= "fast"

			if delSens:
				if devId in SENSOR: del SENSOR[devId]

			try:
				if "minSendDelta" in sensors[sensor][devId]: 
					minSendDelta = float(sensors[sensor][devId]["minSendDelta"])
			except:
				minSendDelta = 5.

				
			if devId not in SENSOR or  restart:
				U.logger.log(20," new parameters read:  minSendDelta:{};  deltaX:{}; sensorRefreshSecs:{}".format( minSendDelta, deltaX[devId], sensorRefreshSecs) )
				startSensor(devId)
				if SENSOR[devId] == "":
					return
		deldevID={}		   
		for devId in SENSOR:
			if devId not in sensors[sensor]:
				deldevID[devId]=1
		for dd in  deldevID:
			del SENSOR[dd]
		if len(SENSOR) ==0: 
			####exit()
			pass



	except Exception as e:
		U.logger.log(30,"", exc_info=True)
		U.logger.log(30, "{}".format(sensors[sensor]))
		


#################################
def startSensor(devId, Co2Target="", reset=False):
	global sensors,sensor
	global startTime
	global SENSOR, i2c_bus
	global serialNumber, sensorTemperatureOffset, autoCalibration, sensorCo2Target, altitudeCompensation
	startTime =time.time()

	
	if devId  in SENSOR:
		if reset:
			U.logger.log(20," soft resetting sensor")
			SENSOR[devId].thisSensor.soft_reset()
			del SENSOR[devId]
		if not reset and Co2Target != "": 
			SENSOR[devId].thisSensor.set_Force_self_calibration(Co2Target)
			sensorCo2Target[devId]			= SENSOR[devId].thisSensor.get_Force_self_calibration()


	if devId not  in SENSOR:
		try:
			autoCalibration[devId]			= True
			SENSOR[devId]					= SENSORclass( fastSlow= sensors[sensor][devId].get("fastSlowRead","fast") )
			if SENSOR[devId]				== "": return 

			try:
				serialNumber[devId]				= SENSOR[devId].serialNumber()
			except: pass

			if Co2Target != "": 
				U.logger.log(20," setting co2 calib. to:{}".format(Co2Target))
				if Co2Target != 400:
					sensors[sensor][devId]["autoCalibration"] = "0"
				SENSOR[devId].thisSensor.set_Force_self_calibration(Co2Target)

			if sensors[sensor][devId]["altitudeCompensation"] != "": 
				SENSOR[devId].scd30.set_AltitudeCompensation(int(sensors[sensor][devId]["altitudeCompensation"]))

			if sensors[sensor][devId]["autoCalibration"] != "": 
				SENSOR[devId].thisSensor.set_auto_self_calibration( sensors[sensor][devId]["autoCalibration"] == "1" )

			if sensors[sensor][devId]["sensorTemperatureOffset"] != "": 
				SENSOR[devId].thisSensor.set_temperature_offset( int(sensors[sensor][devId]["sensorTemperatureOffset"]) )
				time.sleep(1)

			AutocalibWas					= SENSOR[devId].get_auto_self_calibration_active()
			altitudeCompensation[devId]		= SENSOR[devId].get_AltitudeCompensation()
			sensorCo2Target[devId]			= SENSOR[devId].get_Force_self_calibration()
			sensorTemperatureOffset[devId]	= SENSOR[devId].get_temperature_offset()
			U.logger.log(20," version: {}, auto-calibration was set to: {:}, temperature offset was:{}, Co2 target:{}, altitudeCompensation:{}".format(serialNumber[devId], AutocalibWas, sensorTemperatureOffset[devId], sensorCo2Target[devId], altitudeCompensation[devId]) )
			# set auto calib 


			U.logger.log(20,"  first data read: {}".format(ret ) )
			autoCalibration[devId]			= SENSOR[devId].get_auto_self_calibration_active()
			sensorTemperatureOffset[devId]	= SENSOR[devId].get_temperature_offset()

		except	Exception as e:
			U.logger.log(30,"", exc_info=True)
			SENSOR[devId] = ""
			return
	U.muxTCA9548Areset()



#################################
def getValues(devId):
	global sensor, sensors,	 SENSOR, badsensorCountCO2
	global startTime, sendToIndigoSecs, sensorMode
	global serialNumber, sensorTemperatureOffset, autoCalibration, sensorCo2Target, altitudeCompensation

	
	try:
		if devId not in SENSOR:
			startSensor(devId) 
		if SENSOR[devId] == "": 
			return "badSensor"

		CO2, temp, hum = 	SENSOR[devId].getData()

		if CO2  == "notReady":
			return 0, 0, 0
		#print ("\n\nCO2:{}, temp:{}, hum:{}, \n\n".format(CO2, temp, hum ))
		if type(temp) != float: 
			if badsensorCountCO2[devId]  > 5: return "badSensor"
			return ""

		#U.logger.log(20, u"CO2:{}, temp:{}, hum:{}".format(CO2, temp, hum))
		if "offsetTemp" in sensors[sensor][devId]: temp += float(sensors[sensor][devId]["offsetTemp"])
		if "offsetHum"  in sensors[sensor][devId]: hum  += float(sensors[sensor][devId]["offsetHum"])
		if "offsetCO2"  in sensors[sensor][devId]: CO2  += float(sensors[sensor][devId]["offsetCO2"])
		data = {"temp":	round(temp,1), "CO2": CO2, "hum": hum, "serialNumber":serialNumber[devId], "autoCalibration": autoCalibration[devId], 
				"sensorTemperatureOffset": sensorTemperatureOffset[devId],"sensorCo2Target":sensorCo2Target[devId], "altitudeCompensation":altitudeCompensation[devId],
				 "fastSlowRead":sensors[sensor][devId].get("fastSlowRead","fast")} 
		badsensorCountCO2[devId]  = 0
		return data
	except	Exception as e:
		U.logger.log(30,"end of getValues", exc_info=True)
	if badsensorCountCO2[devId]  > 5: return "badSensor"
	return ""





############################################
def execSensor():
	global sensor, sensors, sensorList, badsensorCountCO2
	global deltaX, SENSOR, minSendDelta, sensorMode
	global oldRaw, lastRead
	global startTime, sendToIndigoSecs, sensorRefreshSecs, lastMeasurement
	global serialNumber
	global serialNumber, sensorTemperatureOffset, autoCalibration, sensorCo2Target, altitudeCompensation

	serialNumber				= {}
	sensorTemperatureOffset		= {}
	autoCalibration				= {}
	sensorCo2Target				= {}
	altitudeCompensation		= {}
	sensorMode					= {}
	sendToIndigoSecs			= 20
	startTime					= time.time()
	lastMeasurement				= time.time()
	oldRaw						= ""
	lastRead					= 0
	minSendDelta				= 5.
	loopCount					= 0
	sensorRefreshSecs			= 9
	sensorList					= []
	sensors						= {}
	sensor						= G.program
	quick						= False
	output						= {}
	SENSOR						= {}
	deltaX						= {}
	myPID						= str(os.getpid())
	U.setLogging()
	U.killOldPgm(myPID,G.program+".py")# kill old instances of myself if they are still running


	if U.getIPNumber() > 0:
		time.sleep(10)
		exit()

	readParams()

	time.sleep(1)

	lastRead = time.time()

	U.echoLastAlive(G.program)


	lastValues0			= {"moisture":0,"temp":0, "hum":0}
	lastValues			= {}
	lastValues2			= {}
	lastData			= {}
	lastSend			= 0
	G.lastAliveSend		= time.time()
	badsensorCountCO2	= {}
	notReadyCountCO2	= {}

	sensorWasBad 		= False

	while True:
		try:
			tt = time.time()
			sendData = False
			data ={}
			if sensor in sensors:
				data = {"sensors": {sensor:{}}}
				for devId in sensors[sensor]:
					if devId not in badsensorCountCO2: badsensorCountCO2[devId] = 0
					if devId not in notReadyCountCO2: notReadyCountCO2[devId] = 0
					Co2Target = U.checkNewCalibration(G.program)
					if Co2Target:
						try:	del SENSOR[devId]
						except:	pass
						U.logger.log(20," Co2Target:{}".format(Co2Target))

						if type(Co2Target) == type({}):
							Co2Target["value"] = max(400, int(Co2Target["value"]))
							startSensor(devId, Co2Target=Co2Target["value"]) # set co2 to lowest value
						else:	
							startSensor(devId, Co2Target=440) # set co2 to lowest value

					if U.checkResetFile(G.program):
						U.logger.log(20," resetting sensor")
						startSensor(devId, Co2Target=430, reset=True) # 


					if devId not in lastValues: 
						lastValues[devId]  = copy.copy(lastValues0)
						lastValues2[devId] = copy.copy(lastValues0)
					values = getValues(devId)



					if values in ["badSensor",""]:
						badsensorCountCO2[devId]  = True
						data["sensors"][sensor][devId] = "badSensor"
						if badSensor < 5: 
							U.logger.log(20,"bad sensor count  limit reached")
							U.sendURL(data)
							badsensorCountCO2[devId] += 1
						else:
							if badsensorCountCO2[devId] == 0:
								U.restartMyself(param="", reason="badsensor",doPrint=True,python3=True)
						lastValues2[devId] = copy.copy(lastValues0)
						lastValues[devId]  = copy.copy(lastValues0)
						continue

					if values in ["notReady"]:
						notReadyCountCO2[devId]  +=1
						if notReadyCountCO2[devId]  == 10:
							data["sensors"][sensor][devId] = "badSensor"
							U.logger.log(20,"bad sensor count  limit reached")
							U.sendURL(data)
							notReadyCountCO2[devId] = 0
						self.sleep(5)
						continue

					if values["CO2"] < 380: 
						badsensorCountCO2[devId] +=1
						U.logger.log(20," badsensorCountCO2:{}, co2:{}".format(badsensorCountCO2[devId] , values["CO2"] ))
						if badsensorCountCO2[devId]  > 12:
							U.restartMyself(param="", reason="co2 value to low",doPrint=True,python3=True)

						elif badsensorCountCO2[devId]  > 6:
							sensorCo2Target[devId] += 30	
							startSensor(devId, Co2Target=sensorCo2Target[devId], reset=True) # 
							continue

						elif badsensorCountCO2[devId]  == 7:
							pass
						else:
							continue

					data["sensors"][sensor][devId] = {}
					badsensorCountCO2[devId] = 0
					data["sensors"][sensor][devId] = values
					deltaN = 0
					for xx in lastValues0:
						try:
							current = float(values[xx])
							delta	= current-lastValues2[devId][xx]
							delta  /=  max (0.5,(current+lastValues2[devId][xx])/2.)
							deltaN	= max(deltaN,abs(delta) )
							lastValues[devId][xx] = current
						except: pass

					if (   ( deltaN > deltaX[devId]	 ) or  (  tt - abs(sendToIndigoSecs) > G.lastAliveSend  ) or quick ) and  ( tt - G.lastAliveSend > minSendDelta ):
						sendData = True
						lastValues2[devId] = copy.copy(lastValues[devId])
			##print (data)
			if sendData:
				U.sendURL(data)
			U.makeDATfile(G.program, data)

			loopCount +=1

			##U.makeDATfile(G.program, data)
			quick = U.checkNowFile(G.program)				 
							 
			U.echoLastAlive(G.program)

			tt= time.time()
			if tt - lastRead > 5.:	
				readParams()
				lastRead = tt
			time.sleep( max(0, (lastMeasurement+sensorRefreshSecs) - time.time() ) )
			lastMeasurement = time.time()

		except	Exception as e:
			U.logger.log(30,"", exc_info=True)
			time.sleep(5.)


G.pythonVersion = int(sys.version.split()[0].split(".")[0])
# output: , use the first number only
#3.7.3 (default, Apr  3 2019, 05:39:12) 
#[GCC 8.2.0]

execSensor()
try: 	G.sendThread["run"] = False; time.sleep(1)
except: pass
sys.exit(0)
