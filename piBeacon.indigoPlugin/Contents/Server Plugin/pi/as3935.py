#!/usr/bin/python
# -*- coding: utf-8 -*-
# by Karl Wachs
# 2018-06-13
# version 0.1 
##
##
## lightning sensor 
####################

import sys, os, time, json, datetime, subprocess, copy
import smbus
import RPi.GPIO as GPIO
import time
import datetime


sys.path.append(os.getcwd())
import	piBeaconUtils	as U
import	piBeaconGlobals as G

G.program = "as3935"


class RPi_AS3935:

	def __init__(self, address, bus=1, minNoiseFloor = 1):
		self.address		= address
		self.i2cbus			= smbus.SMBus(bus)
		self.minNoiseFloor	= minNoiseFloor

	def calibrate(self, tun_cap):
		"""Calibrate the lightning sensor - this takes up to half a second
		and is blocking.
		The value of tun_cap should be between 0 and 15, and is used to set
		the internal tuning capacitors (0-120pF in steps of 8pF)
		"""
		time.sleep(0.08)
		registers = self.read_data()
		if registers ==[]: return -1
		if tun_cap is not None:
			if tun_cap < 16 and tun_cap > -1:
				self.set_byte(0x08, (registers[8] & 0xF0) | tun_cap)
				time.sleep(0.002)
			else:
				raise Exception("Value of TUN_CAP must be between 0 and 15")

		U.logger.log(30, "setting cap param to %d  =	 %d	 pF" %( tun_cap, tun_cap*8))
		self.set_byte(0x3D, 0x96)
		time.sleep(0.002)
		registers = self.read_data()
		if registers ==[]: return -1

		self.set_byte(0x08, registers[8] | 0x20)
		time.sleep(0.002)
		self.set_byte(0x08, registers[8] & 0xDF)
		time.sleep(0.002)
		return 0 

	def reset(self):
		"""Reset all registers to their default power on values
		"""
		self.set_byte(0x3C, 0x96)

	def get_interrupt(self):
		"""Get the value of the interrupt register
		0x01 - Too much noise
		0x04 - Disturber
		0x08 - Lightning
		255	 - read error
		"""
		registers = self.read_data()
		if registers ==[]: return 255 
		else:			   return registers[3] & 0x0F

	def get_distance(self):
		"""Get the estimated distance of the most recent lightning event
		"""
		registers = self.read_data()
		if registers ==[]:					return -1
		if registers[7] & 0x3F == 0x3F:		return False
		else:								return registers[7] & 0x3F

	def get_energy(self):
		"""Get the calculated energy of the most recent lightning event
		"""
		#print"get_energy bf read"
		registers = self.read_data()
		if registers ==[]: return -1
	   #print"get_energy",	registers
		return ((registers[6] & 0x1F) << 16) | (registers[5] << 8) | registers[4]

	def get_noise_floor(self):
		"""Get the noise floor value.
		Actual voltage levels used in the sensor are located in Table 16
		of the data sheet.
		"""
		registers = self.read_data()
		if registers ==[]: return -1
	   #print"get_noise_floor",	 registers
		return (registers[1] & 0x70) >> 4

	def set_noise_floor(self, noisefloor):
		"""Set the noise floor value.

		Actual voltage levels used in the sensor are located in Table 16
		of the data sheet.
		"""
		U.logger.log(30, "setting noise floor to %d" %( max(noisefloor,self.minNoiseFloor))) 
		if noisefloor <= self.minNoiseFloor: return self.minNoiseFloor
		registers = self.read_data()
		if registers ==[]: return 0

		nf = (noisefloor & 0x07) << 4
		write_data = (registers[1] & 0x8F) + nf
		self.set_byte(1, write_data)
		return noisefloor

	def lower_noise_floor(self, min_noise=1):
		"""Lower the noise floor by one step.
		min_noise is the minimum step that the noise_floor should be
		lowered to.
		"""
		floor = self.get_noise_floor()
		if floor == -1: return -1
		if floor > min_noise:
			floor = floor - 1
			U.logger.log(30,	 "lowering noise floor to %d"% floor) 
			self.set_noise_floor(floor)
		return floor

	def raise_noise_floor(self, max_noise=7):
		"""Raise the noise floor by one step
		max_noise is the maximum step that the noise_floor should be
		raised to.
		"""
		floor = self.get_noise_floor()
		if floor ==-1: return -1
		if floor < max_noise:
			floor = floor + 1
			U.logger.log(30, "raising noise floor to %d" % floor) 
			self.set_noise_floor(floor)
		return floor

	def get_min_strikes(self):
		"""Get the number of lightning detections required before an
		interrupt is raised.
		"""
		
		registers = self.read_data()
		if registers ==[]: return -1
		value = (registers[2] >> 4) & 0x03
		try:			return [1,5,9,16][value]
		except:			raise Exception("Value must be 0,1,2,3")
		return 1

	def set_min_strikes(self, min_strikes):
		"""Set the number of lightning detections required before an
		interrupt is raised.
		Valid values are 1, 5, 9, and 16, any other raises an exception.
		"""
		U.logger.log(30, "set min strikes to	 %d" % min_strikes) 
		ms = 0
		if	 min_strikes == 1:	  ms = 0
		elif min_strikes == 5:	  ms = 1
		elif min_strikes == 9:	  ms = 2
		elif min_strikes == 16:	  ms = 3
		else:
			raise Exception("Value must be 1, 5, 9, or 16")

		registers = self.read_data()
		if registers ==[]: return 

		write_data = (registers[2] & 0xCF) + ((ms & 0x03) << 4)
		self.set_byte(0x02, write_data)

	def get_indoors(self):
		"""Determine whether or not the sensor is configured for indoor
		use or not.
		Returns 1 if configured to be indoors, out dorr 0, error 255.
		"""
		registers = self.read_data()
		
		if registers ==[]:				 return 255
		if registers[0] & 0x20 == 0x20:	 return 1
		else:							 return 0

	def set_indoors(self, indoors):
		"""Set whether or not the sensor should use an indoor configuration.
		"""
		U.logger.log(30, "setting indoor %d "% indoors) 
		registers = self.read_data()
		if registers == []: return 

		if indoors:		 write_value = (registers[0] & 0xC1) | 0x24
		else:			 write_value = (registers[0] & 0xC1) | 0x1C
		self.set_byte(0x00, write_value)

	def set_mask_disturber(self, mask_dist):
		"""Set whether or not disturbers should be masked (no interrupts for
		what the sensor determines are man-made events)
		"""
		registers = self.read_data()
		if registers ==[]: return 
		if mask_dist:	 write_value = registers[3] | 0x20
		else:			 write_value = registers[3] & 0xDF
		self.set_byte(0x03, write_value)

	def get_mask_disturber(self):
		"""Get whether or not disturbers are masked or not.
		Returns True if interrupts are masked, false otherwise
		"""
		registers = self.read_data()
		if registers ==[]:				   return False 
		if registers[3] & 0x20 == 0x20:	   return True
		else:							   return False

	def set_disp_lco(self, display_lco):
		"""Have the internal LC oscillator signal displayed on the interrupt pin for
		measurement.
		Passing display_lco=True enables the output, False disables it.
		"""
		registers = self.read_data()
		if registers ==[]: return 
		
		if display_lco:	  self.set_byte(0x08, (registers[8] | 0x80))
		else:			  self.set_byte(0x08, (registers[8] & 0x7F))
		time.sleep(0.002)

	def get_disp_lco(self):
		"""Determine whether or not the internal LC oscillator is displayed on the
		interrupt pin.
		Returns True if the LC oscillator is being displayed on the interrupt pin,
		False otherwise
		"""
		registers = self.read_data()
		if registers ==[]:				   return False
		if registers[8] & 0x80 == 0x80:	   return True
		else:							   return False

	def set_byte(self, register, value):
		self.i2cbus.write_byte_data(self.address, register, value)

	def read_data(self):
		try:	ret = self.i2cbus.read_i2c_block_data(self.address, 0x00)
		except: ret=[]
		U.logger.log(10, "{}".format(ret))
		return ret
		
# ===========================================================================
# read params
# ===========================================================================

#################################		 
def readParams():
	global sensorList, sensors, logDir, sensor,	 sensorRefreshSecs
	global rawOld,i2cAddress
	global as3935sensor, minSendDelta
	global oldRaw, lastRead
	global startTime
	global inside, minStrikes, tuneCapacitor, minNoiseFloor, interruptGPIO,calibrationDynamic, noiseFloor, CapValue
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
		 
 
		if sensor not in sensors:
			U.logger.log(30, G.program+" is not in parameters = not enabled, stopping "+G.program+".py" )
			exit()
			

		U.logger.log(30, G.program+" reading new parameter file" )

		if sensorRefreshSecs == 91:
			try:
				xx	   = str(inp["sensorRefreshSecs"]).split("#")
				sensorRefreshSecs = float(xx[0]) 
			except:
				sensorRefreshSecs = 91	  
		deltaX={}
		restart = False
		for devId in sensors[sensor]:
			deltaX[devId]  = 0.1

			try:
				old = minStrikes
				if "minStrikes" in sensors[sensor][devId]:
					minStrikes = int(sensors[sensor][devId]["minStrikes"])
			except:
				old = 0
				minStrikes = 1	  
			if old != minStrikes: restart = True

			try:
				old = calibrationDynamic
				if "calibrationDynamic" in sensors[sensor][devId]:
					calibrationDynamic = int(sensors[sensor][devId]["calibrationDynamic"])
			except:
				calibrationDynamic = 1	  
			if old != calibrationDynamic: restart = True


			try:
				old = tuneCapacitor
				if "tuneCapacitor" in sensors[sensor][devId]:
					tuneCapacitor = int(sensors[sensor][devId]["tuneCapacitor"])
			except:
				tuneCapacitor = 15	  
			if old != tuneCapacitor: restart = True


			try:
				old = minNoiseFloor
				if "minNoiseFloor" in sensors[sensor][devId]:
					minNoiseFloor = int(sensors[sensor][devId]["minNoiseFloor"])
			except:
				minNoiseFloor = 2	
			if old != minNoiseFloor: restart = True

			try:
				old = noiseFloor
				if "noiseFloor" in sensors[sensor][devId]:
					noiseFloor = int(sensors[sensor][devId]["noiseFloor"])
			except:
				noiseFloor = 3	 
			if old != noiseFloor: restart = True

			old = inside
			try:
				if "inside" in sensors[sensor][devId]: 
					inside = int(sensors[sensor][devId]["inside"])
			except:
				inside = 0	 
			if old != inside: restart = True


			
			old = i2cAddress
			i2cAddress = U.getI2cAddress(sensors[sensor][devId], default ="")
			if old != i2cAddress: restart = True


			try:
				if "interruptGPIO" in sensors[sensor][devId]: 
					interruptGPIO= int(sensors[sensor][devId]["interruptGPIO"])
			except:
				interruptGPIO = 17


			try:
				if "minSendDelta" in sensors[sensor][devId]: 
					minSendDelta= float(sensors[sensor][devId]["minSendDelta"])
			except:
				minSendDelta = 5.

				
			if devId not in as3935sensor or	 restart:
				startSensor(devId )
				if as3935sensor[devId] =="":
					return
				U.logger.log(30,"new parameters read: \n  i2cAddress:{}".format(i2cAddress) +";	 minSendDelta:{}".format(minSendDelta)+";"+
						"  interruptGPIO:{}".format(interruptGPIO)+";  sensorRefreshSecs:{}".format(sensorRefreshSecs) +"\n"+
						"  minStrikes:{}".format(minStrikes)		 +";  calibrationDynamic:{}".format(calibrationDynamic) +"  inside:"+str(inside)+";"+
						"  tuneCapacitor:{}".format(tuneCapacitor)+ " = "+CapValue[tuneCapacitor]+"pF;"+
						"  minNoiseFloor:{}".format(minNoiseFloor)			+"	noiseFloor:"+str(noiseFloor)+"\n"+
						"  restart:"+str(restart))
				
		deldevID={}		   
		for devId in as3935sensor:
			if devId not in sensors[sensor]:
				deldevID[devId]=1
		for dd in  deldevID:
			del as3935sensor[dd]
		if len(as3935sensor) ==0: 
			####exit()
			pass


	except	Exception as e:
		U.logger.log(30,"", exc_info=True)
		U.logger.log(30,"{}".format(sensors[sensor]) ) 
		



#################################
def startSensor(devId):
	global sensors, sensor, badSensor
	global startTime
	global as3935sensor 
	global inside, minStrikes, tuneCapacitor, minNoiseFloor, interruptGPIO, noiseFlorSet,calibrationDynamic, noiseFloor, CapValue
	
	U.logger.log(30,"==== Start "+G.program+" ===== @ i2c= {}".format(i2cAddress))
	startTime =time.time()

	i2cAdd = U.muxTCA9548A(sensors[sensor][devId]) # switch mux on if requested and use the i2c address of the mix if enabled
	data = ""
	try:
		as3935sensor[devId]	 =	RPi_AS3935(address=i2cAdd, minNoiseFloor=minNoiseFloor)
		as3935sensor[devId].set_indoors( inside == 1)
		noiseFlorSet = as3935sensor[devId].set_noise_floor(max(noiseFloor,minNoiseFloor))
		as3935sensor[devId].set_min_strikes(minStrikes)
		if	as3935sensor[devId].calibrate(tuneCapacitor)  ==-1:
			time.sleep(10)
			data={"sensors":{sensor:{devId:{"eventType":"badsensor"}}}}
			badSensor
		else: badSensor = False
						
	except	Exception as e:
		U.logger.log(30,"", exc_info=True)
		data={"sensors":{sensor:{devId:{"eventType":"badsensor"}}}}
		badSensor = True
	if badSensor:
		U.sendURL(data,squeeze=False)
		as3935sensor[devId]	  =""
		return 
	time.sleep(.1)

	U.muxTCA9548Areset()

	try:	GPIO.setmode(GPIO.BCM)
	except: pass
	try:	GPIO.remove_event_detect(interruptGPIO)
	except: pass

	GPIO.setup(interruptGPIO, GPIO.IN)
	GPIO.add_event_detect(interruptGPIO, GPIO.RISING, callback=handle_interrupt)
	U.logger.log(30, "end of event setup" )
	return 

#################################
def handle_interrupt(channel):
	global as3935sensor,sensors, sensor, lastEvent, lastTime, lastSend, restartNeededCounter, interruptGPIO, calibrationDynamic
	global noiseFlorSet
	time.sleep(0.003)

	if interruptGPIO != channel: return
	
	if sensor in sensors:
		data = {"sensors": {sensor:{}}}
		msg ={}
		for devId in sensors[sensor]:
			distance = -1
			energy	 = 0
			reason = as3935sensor[devId].get_interrupt()
			lastEvent = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
			lastTime = time.time()
			#print "event;	 reason: ",reason, lastEvent
			msg = {"eventType":"measurement","lightning":"","distance":-1,"energy":-1}

			if reason == 1:
				if noiseFlorSet < 7 and	 calibrationDynamic == 1:
					msg["lightning"] = "Noise level too high - adjusting"
					as3935sensor[devId].raise_noise_floor()
					restartNeededCounter =0
				else:
					msg["lightning"] = "Noise level too high - no adjustment due to setting"

			elif reason == 4:
				if calibrationDynamic == 1 : 
					msg["lightning"] = "Disturber detected - masking"
					as3935sensor[devId].set_mask_disturber(True)
					restartNeededCounter =0
				else:
					msg["lightning"] = "Disturber detected - no	 masking due to setting"

			elif reason == 8:
				energy	 = as3935sensor[devId].get_energy()
				distance = as3935sensor[devId].get_distance()
				msg["lightning"] = "lightning detected"
				msg["distance"]	 = distance
				msg["energy"]	 = energy
				restartNeededCounter =0

			elif reason == 255:
				U.logger.log(10, "read error")
				restartNeededCounter +=1
				continue

			elif reason == 0:
				U.logger.log(10, "nothing read, skipping event ")
				continue

			else:
				U.logger.log(10, "unknown read error, reason: {}".format(reason))
				restartNeededCounter +=1
				continue


			if msg !="lightning detected":
				#print "reject ", msg
				if time.time() - lastSend  < 180: return 


			data["sensors"][sensor][devId]=msg
			U.logger.log(10,	" sending:{}".format(data))
			U.sendURL(data,squeeze=False)
			msg["lastEvent"] = lastEvent
			msg["lastTime"]	 = lastTime
			lastSend = time.time()
			f=open(G.homeDir+"lightning.dat","w")
			f.write(json.dumps(msg))
			f.close()
			
############################################
global rawOld,i2cAddress
global sensor, sensors, badSensor
global as3935sensor, minSendDelta
global lastRead
global startTime, reStartReq
global sensorList, sensors, logDir, sensor,	 sensorRefreshSecs
global badSensor
global lastEvent,lastTime,lastSend,restartNeededCounter, CapValue


global inside, minStrikes, tuneCapacitor, minNoiseFloor,interruptGPIO, noiseFlorSet, calibrationDynamic,noiseFloor

CapValue					= {0:"0",1:"8",2:"16",3:"24",4:"32",5:"40",6:"48",7:"56",8:"64",9:"72",10:"80",11:"88",12:"96",13:"104",14:"112",15:"120"}
inside						= 0
minStrikes					= 1
tuneCapacitor				= 15
minNoiseFloor				= 3
interruptGPIO				= 17
noiseFlorSet				= 0
calibrationDynamic			= 1
noiseFloor					= 3
lastSend					= 0
restartNeededCounter		= 0
lastEvent					= ""
lastTime					= 0
badSensor					= False
as3935sensor				= {}
startTime					= time.time()
lastMeasurement				= time.time()
oldRaw						= ""
lastRead					= 0
minSendDelta				= 5.
loopCount					= 0
sensorRefreshSecs			= 91
sensorList					= []
sensors						= {}
sensor						= G.program
quick						= False
i2cAddress					=""
reStartReq					= False

U.setLogging()

myPID		= str(os.getpid())
U.killOldPgm(myPID,G.program+".py")# kill old instances of myself if they are still running

if U.getIPNumber() > 0:
	time.sleep(10)
	exit()
readParams()

time.sleep(1)

lastRead = time.time()

try:
	f=open(G.homeDir+"lightning.dat","r")
	msg = json.loads(f.read())
	f.close()
	if "lastTime"  in msg: lastTime	 = msg["lastTime"]
	if "lastEvent" in msg: lastEvent = msg["lastEvent"]
except:
	pass
	
if time.time() - lastTime > 60*60*24*33: lastTime = 0


U.echoLastAlive(G.program)
lastSend = 0
while True:
	time.sleep(20)
	U.echoLastAlive(G.program)
	readParams()
	lastRead = time.time()
	if restartNeededCounter > 3: reStartReq = True
	if time.time() - lastSend > 201:  
		if sensor in sensors:
			data = {"sensors": {sensor:{}}}
			for devId in sensors[sensor]:
				if badSensor: 
					data["sensors"][sensor][devId]={"eventType":"badsensor"}
				
				else:
					if lastTime == 0:
						data["sensors"][sensor][devId]={"eventType":"no Action yet"}
					elif datetime.datetime.now().strftime("%d") != lastEvent[8:10]: # same day?
						data["sensors"][sensor][devId]={"eventType":"no lightning today"}
					else:
						data["sensors"][sensor][devId]={"eventType":"none"}
				if time.time() - lastTime > 600 and calibrationDynamic ==1:
					as3935sensor[devId].lower_noise_floor()
					lastTime = time.time() - 400
				lastSend = time.time()	  
				U.sendURL(data,squeeze=False)


	if reStartReq:
		time.sleep(5)
		subprocess.call("/usr/bin/python "+G.homeDir+G.program+".py &", shell=True)


try: 	G.sendThread["run"] = False; time.sleep(1)
except: pass


