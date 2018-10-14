#!/usr/bin/python
# -*- coding: utf-8 -*-
# by Karl Wachs
# 2018-01-28
# version 0.1 
##
##
#! /usr/bin/env python
# -*- coding: utf-8 -*-
####################

import sys, os, time, json, datetime,subprocess,copy
import math
import copy
from collections import OrderedDict
import smbus


sys.path.append(os.getcwd())
import	piBeaconUtils	as U
import	piBeaconGlobals as G
G.program = "ccs811"
G.debug = 0
#simple bitfield object
from collections import OrderedDict

class Adafruit_bitfield(object):
	def __init__(self, _structure):
		self._structure = OrderedDict(_structure)

		for key, value in self._structure.items():
			setattr(self, key, 0)

	def get(self):
		fullreg = 0
		pos = 0
		for key, value in self._structure.items():
			fullreg = fullreg | ( (getattr(self, key) & (2**value - 1)) << pos )
			pos = pos + value

		return fullreg

	def set(self, data):
		pos = 0
		for key, value in self._structure.items():
			setattr(self, key, (data >> pos) & (2**value - 1))
			pos = pos + value
			
			# Copyright (c) 2017 Adafruit Industries
# Author: Dean Miller
#
# Permission is hereby granted, free of charge, to any person obtaining a copy
# of this software and associated documentation files (the "Software"), to deal
# in the Software without restriction, including without limitation the rights
# to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
# copies of the Software, and to permit persons to whom the Software is
# furnished to do so, subject to the following conditions:
#
# The above copyright notice and this permission notice shall be included in
# all copies or substantial portions of the Software.
#
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
# IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
# FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
# AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
# LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
# OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN
# THE SOFTWARE.


CCS811_ADDRESS				 = 0x5A

CCS811_STATUS				 = 0x00
CCS811_MEAS_MODE			 = 0x01
CCS811_ALG_RESULT_DATA		 = 0x02
CCS811_RAW_DATA				 = 0x03
CCS811_ENV_DATA				 = 0x05
CCS811_NTC					 = 0x06
CCS811_THRESHOLDS			 = 0x10
CCS811_BASELINE				 = 0x11
CCS811_HW_ID				 = 0x20
CCS811_HW_VERSION			 = 0x21
CCS811_FW_BOOT_VERSION		 = 0x23
CCS811_FW_APP_VERSION		 = 0x24
CCS811_ERROR_ID				 = 0xE0
CCS811_SW_RESET				 = 0xFF

CCS811_BOOTLOADER_APP_ERASE	 = 0xF1
CCS811_BOOTLOADER_APP_DATA	 = 0xF2
CCS811_BOOTLOADER_APP_VERIFY = 0xF3
CCS811_BOOTLOADER_APP_START	 = 0xF4

CCS811_DRIVE_MODE_IDLE		 = 0x00
CCS811_DRIVE_MODE_1SEC		 = 0x01
CCS811_DRIVE_MODE_10SEC		 = 0x02
CCS811_DRIVE_MODE_60SEC		 = 0x03
CCS811_DRIVE_MODE_250MS		 = 0x04

CCS811_HW_ID_CODE			 = 0x81
CCS811_REF_RESISTOR			 = 100000

class ccs811_class(object):
	def __init__(self, mode=CCS811_DRIVE_MODE_250MS, address=CCS811_ADDRESS):
		# Check that mode is valid.
		if mode not in [CCS811_DRIVE_MODE_IDLE, CCS811_DRIVE_MODE_1SEC, CCS811_DRIVE_MODE_10SEC, CCS811_DRIVE_MODE_60SEC, CCS811_DRIVE_MODE_250MS]:
			raise ValueError('Unexpected mode value {0}.  Set mode to one of CCS811_DRIVE_MODE_IDLE, CCS811_DRIVE_MODE_1SEC, CCS811_DRIVE_MODE_10SEC, CCS811_DRIVE_MODE_60SEC or CCS811_DRIVE_MODE_250MS'.format(mode))

		# Create I2C device.
		self.bus		 = smbus.SMBus(1)
		self.i2c_address = address

		#set up the registers
		self._status = Adafruit_bitfield([('ERROR' , 1), ('unused', 2), ('DATA_READY' , 1), ('APP_VALID', 1), ('unused2' , 2), ('FW_MODE' , 1)])
		
		self._meas_mode = Adafruit_bitfield([('unused', 2), ('INT_THRESH', 1), ('INT_DATARDY', 1), ('DRIVE_MODE', 3)])

		self._error_id = Adafruit_bitfield([('WRITE_REG_INVALID', 1), ('READ_REG_INVALID', 1), ('MEASMODE_INVALID', 1), ('MAX_RESISTANCE', 1), ('HEATER_FAULT', 1), ('HEATER_SUPPLY', 1)])

		self.start(mode = mode)

	def start(self, mode = CCS811_DRIVE_MODE_250MS):
		try:
			self._TVOC = 0
			self._eCO2 = 0
			self.tempOffset = 0
			self.SWReset()
			time.sleep(0.5)
		
				#check that the HW id is correct
			tp =  self.readU8(CCS811_HW_ID)	 
			tpOk = "ok" if tp== 0x81 else "error" 
			U.toLog(2, "-- id code	  %x  =	  %s "% (tp, tpOk)	)

			#try to start the app
			self.writeList(CCS811_BOOTLOADER_APP_START, [])
			time.sleep(1.5)
			#make sure there are no errors and we have entered application mode

			tp = self.checkError()
			tpOk = "ok" if tp==1 else "error" 
			U.toLog(2, "-- error code %x  =	  %s "% (tp, tpOk)	)

			tp =  self._status.FW_MODE	
			tpOk = "ok" if tp== 1 else "error" 
			U.toLog(2, "-- mode code  %x  =	  %s "% (tp, tpOk)	)

			time.sleep(1)
		
			self.disableInterrupt()
		
			#default to read every second
			self.setDriveMode(mode)
		except	Exception, e:
			U.toLog(-1, u" error in starting css sensor in Line '%s' has error='%s'" % (sys.exc_traceback.tb_lineno, e))
		


	def setDriveMode(self, mode):

		self._meas_mode.DRIVE_MODE = mode
		self.write8(CCS811_MEAS_MODE, self._meas_mode.get())


	def enableInterrupt(self):

		self._meas_mode.INT_DATARDY = 1
		self.write8(CCS811_MEAS_MODE, self._meas_mode.get())


	def disableInterrupt(self):

		self._meas_mode.INT_DATARDY = 0
		self.write8(CCS811_MEAS_MODE, self._meas_mode.get())


	def available(self):

		self._status.set(self.readU8(CCS811_STATUS))
		if(not self._status.DATA_READY):
			return False
		else:
			return True


	def readData(self):

		try:
			if(not self.available()):
				return False
			else:
				buf = self.readList(CCS811_ALG_RESULT_DATA, 8)

				self._eCO2 = (buf[0] << 8) | (buf[1])
				self._TVOC = (buf[2] << 8) | (buf[3])
			
				if(self._status.ERROR):
					return buf[5]
				
				else:
					return 0
		except	Exception, e:
			U.toLog(-1, u" error in starting css sensor in Line '%s' has error='%s'" % (sys.exc_traceback.tb_lineno, e))
		return	0		


	def setEnvironmentalData(self, humidity, temperature):

		''' Humidity is stored as an unsigned 16 bits in 1/512%RH. The
		default value is 50% = 0x64, 0x00. As an example 48.5%
		humidity would be 0x61, 0x00.'''
		
		''' Temperature is stored as an unsigned 16 bits integer in 1/512
		degrees there is an offset: 0 maps to -25C. The default value is
		25C = 0x64, 0x00. As an example 23.5% temperature would be
		0x61, 0x00.
		The internal algorithm uses these values (or default values if
		not set by the application) to compensate for changes in
		relative humidity and ambient temperature.'''

		pp			= int(temperature)
		fractional	= temperature - pp

		temp_high = ((pp + 25) << 9)
		temp_low  = (int(fractional *512) & 0x1FF)
		
		temp_conv = (temp_high | temp_low)

		## only take full int numebrs, shift left one then clear upper bits, take lower bit and a 0
		hum_perc = (humidity << 1) &0xFF
		buf = [hum_perc, 0x00,((temp_conv >> 8) & 0xFF), (temp_conv & 0xFF)]
		
		self.writeList(CCS811_ENV_DATA, buf)



	#calculate temperature based on the NTC register
	def calculateTemperature(self):

		buf = self.readList(CCS811_NTC, 4)

		vref  = (buf[0] << 8) | buf[1]
		vrntc = (buf[2] << 8) | buf[3]
		rntc  = (float(vrntc) * float(CCS811_REF_RESISTOR) / float(vref) )

		ntc_temp = math.log(rntc / 10000.0)
		ntc_temp /= 3380.0
		ntc_temp += 1.0 / (25 + 273.15)
		ntc_temp = 1.0 / ntc_temp
		ntc_temp -= 273.15
		return ntc_temp - self.tempOffset


	def setThresholds(self, low_med, med_high, hysteresis):

		buf = [((low_med >> 8) & 0xF), (low_med & 0xF), ((med_high >> 8) & 0xF), (med_high & 0xF), hysteresis ]
		
		self.writeList(CCS811_THRESHOLDS, buf)


	def SWReset(self):

		#reset sequence from the datasheet
		seq = [0x11, 0xE5, 0x72, 0x8A]
		self.writeList(CCS811_SW_RESET, seq)


	def checkError(self):

		self._status.set(self.readU8(CCS811_STATUS))
		return self._status.ERROR

	def getTVOC(self):
		return self._TVOC

	def geteCO2(self):
		return self._eCO2


######## io methods		   
	def writeList(self, command,buf):
		try:
			self.bus.write_i2c_block_data(self.i2c_address, command, buf)
		except	Exception, e:
			U.toLog(-1, u"writeList	 in Line '%s' has error='%s'" % (sys.exc_traceback.tb_lineno, e))

	def readList(self, command,	 length):
		try:
			return self.bus.read_i2c_block_data(self.i2c_address,command,length)
		except	Exception, e:
			U.toLog(-1, u"readList	in Line '%s' has error='%s'" % (sys.exc_traceback.tb_lineno, e))
		return []

	def readU8(self, reg):
		try:
			return	self.bus.read_byte_data(self.i2c_address, reg)
		except	Exception, e:
			U.toLog(-1, u"readU8  in Line '%s' has error='%s'" % (sys.exc_traceback.tb_lineno, e))
		return 0
	def write8(self, reg,value):
		try:
			self.bus.write_byte_data(self.i2c_address, reg, value)
		except	Exception, e:
			U.toLog(-1, u"write8  in Line '%s' has error='%s'" % (sys.exc_traceback.tb_lineno, e))



 # ===========================================================================
# read params
# ===========================================================================

#################################		 
def readParams():
	global sensorList, sensors, logDir, sensor,	 sensorRefreshSecs, displayEnable
	global rawOld
	global deltaX, ccs811, minSendDelta
	global oldRaw, lastRead
	global startTime
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
			

		U.toLog(-1, G.program+" reading new parameter file" )

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
			old = sensorRefreshSecs
			try:
				if "sensorRefreshSecs" in sensors[sensor][devId]:
					xx = sensors[sensor][devId]["sensorRefreshSecs"].split("#")
					sensorRefreshSecs = float(xx[0]) 
			except:
				sensorRefreshSecs = 5	 
			if old != sensorRefreshSecs: restart = True

			
			try:
				if "i2cAddress" in sensors[sensor][devId]: 
					i2cAddress = int(sensors[sensor][devId]["i2cAddress"])
			except:
				i2cAddress = ""	   

			old = deltaX[devId]
			try:
				if "deltaX" in sensors[sensor][devId]: 
					deltaX[devId]= float(sensors[sensor][devId]["deltaX"])/100.
			except:
				deltaX[devId] = 0.1
			if old != deltaX[devId]: restart = True

			old = minSendDelta
			try:
				if "minSendDelta" in sensors[sensor][devId]: 
					minSendDelta= float(sensors[sensor][devId]["minSendDelta"])
			except:
				minSendDelta = 5.
			if old != minSendDelta: restart = True

				
			if devId not in ccs811sensor or	 restart:
				startSensor(devId, i2cAddress)
				if ccs811sensor[devId] =="":
					return
			U.toLog(-1," new parameters read: i2cAddress:" +unicode(i2cAddress) +";	 minSendDelta:"+unicode(minSendDelta)+
					   ";  deltaX:"+unicode(deltaX[devId])+";  sensorRefreshSecs:"+unicode(sensorRefreshSecs) )
				
		deldevID={}		   
		for devId in ccs811sensor:
			if devId not in sensors[sensor]:
				deldevID[devId]=1
		for dd in  deldevID:
			del ccs811sensor[dd]
		if len(ccs811sensor) ==0: 
			####exit()
			pass


	except	Exception, e:
		U.toLog(-1, u"in Line '%s' has error='%s'" % (sys.exc_traceback.tb_lineno, e))
		print sensors[sensor]
		



#################################
def startSensor(devId,i2cAddress):
	global sensors,sensor
	global startTime
	global ccs811sensor
	U.toLog(-1,"==== Start "+G.program+" ===== @ i2c= " +unicode(i2cAddress))
	startTime =time.time()


	i2cAdd = U.muxTCA9548A(sensors[sensor][devId]) # switch mux on if requested and use the i2c address of the mix if enabled
	
	try:
		ccs811sensor[devId]	 =	ccs811_class(address=i2cAdd)
		for ii in range(100):
			if ccs811sensor[devId].available(): break
			time.sleep(0.5)
			
		temp = ccs811sensor[devId].calculateTemperature()
		ccs811sensor[devId].tempOffset = temp - 25.0

		time.sleep(1)
		try:ccs811sensor[devId].start()
		except: pass
		try: temp = ccs811sensor[devId].calculateTemperature()
		except: pass
				
	except	Exception, e:
		U.toLog(-1, u"in Line '%s' has error='%s'" % (sys.exc_traceback.tb_lineno, e))
		ccs811sensor[devId]	  =""
	time.sleep(.1)

	U.muxTCA9548Areset()


#################################
def getValues(devId):
	global sensor, sensors,	 ccs811sensor, badSensor
	global startTime, lastTemp, lastVOC, countVOC, countCO2, lastCO2
	global lastMeasurement

	try:
		ret =""
		if ccs811sensor[devId] =="": 
			badSensor +=1
			return "badSensor"
		i2cAdd = U.muxTCA9548A(sensors[sensor][devId]) # switch mux on if requested and use the i2c address of the mix if enabled
		if ccs811sensor[devId] =="": 
			badSensor +=1
			return "badSensor"
		goodData = False
		newVOC	 = -1
		newCO2	 = -1
		n		 = 0
		CO2		 = 0
		VOC		 = 0
		TEMP	 = 0
		co2		 = 0
		voc		 = 0
		for kk in range(15):
		
			for ii in range(20):
				if ccs811sensor[devId].available():
					try: temp = ccs811sensor[devId].calculateTemperature()
					except: temp = lastTemp
					if temp < -20	or	 temp > 50	 or	  (lastTemp !=-100 and abs(temp-lastTemp) > 10):  temp = lastTemp
					lastTemp = temp
					if	not ccs811sensor[devId].readData():
						co2 = ccs811sensor[devId].geteCO2()
						voc = ccs811sensor[devId].getTVOC()

						## check if bad data, if jumped too much rewuest a re-read 
						if co2 > 8200  or co2 == 0 :
							U.toLog(2, "data read out of bounce	 CO2: %d"%(co2))
							time.sleep(0.5)
							continue
						if	voc > 1200:
							U.toLog(2, "data read out of bounce	 VOC: %d"%(voc))
							time.sleep(0.5)
							continue



						if lastCO2 !=-100 and (abs(co2 -lastCO2) > 50 or co2 > 450)	  and countCO2 < 2:
							U.toLog(2, "data read jump			 CO2: %d"%co2 )
							countCO2 +=1
							time.sleep(0.5)
							continue

						if lastVOC !=-100 and (abs(voc -lastVOC) > 100	or voc > 100) and countVOC < 2:
							U.toLog(2, "data read jump			 VOC: %d"%voc )
							countVOC +=1
							time.sleep(0.5)
							continue

						else:

							if newVOC ==-1:
								newVOC = voc
								newCO2 = co2
								U.toLog(2, "CO2: %d" %co2+ "ppm; TVOC: %d ppb"% voc+ "; temp: %4.1f" %temp +"  first ok read" )
								time.sleep(0.5)
								continue

							if abs(newVOC-voc) > 10 or abs(newCO2-co2) > 10:
								U.toLog(2, "CO2: %d" %co2+ "ppm; TVOC: %d ppb"% voc+ "; temp: %4.1f" %temp +"  re-read not the same " )
								newVOC = voc
								newCO2 = co2
								time.sleep(0.5)
								continue
							co2 = (co2+newCO2)/2
							voc = (voc+newVOC)/2
							break
					else:
						U.toLog(0, "ERROR data not ready!")
						co2 = ccs811sensor[devId].geteCO2()
						voc = ccs811sensor[devId].getTVOC()
						U.toLog(2, "CO2: %d" %co2+ "ppm, TVOC: %d"% voc+ " temp: %4.1f" %temp  )
						try:ccs811sensor[devId].start()
						except: pass
						time.sleep(0.5)
			if co2 == 0 and voc == 0: continue
			VOC += voc
			CO2 += co2
			TEMP+= temp
			n	+= 1
			if n > 3: 
				goodData =True
				VOC /=n
				CO2 /=n
				TEMP/=n
				break
			time.sleep(0.2)

		if goodData:
			U.toLog(2, "n:"+str(n)+" CO2: %d" %CO2+ "ppm; TVOC: %d ppb"% VOC+ "; temp: %4.1f" %TEMP	 +"	 accepted")
			ret	 = {"CO2":		   ( "%d"%( CO2			 ) ).strip(), 
					"VOC":		   ( "%d"%( VOC			 ) ).strip(),
					"temp":		   ( "%4.1f"%( TEMP		 ) ).strip()}
			U.toLog(3, unicode(ret)) 
			badSensor = 0
			goodData  = True
			countCO2  = 0
			lastCO2	  = CO2
			countVOC  = 0
			lastVOC	  = VOC
			lastTemp  = TEMP
	except	Exception, e:
		U.toLog(-1, u"in Line '%s' has error='%s'" % (sys.exc_traceback.tb_lineno, e))
		badSensor+=1
		if badSensor >3: ret = "badSensor"
		ccs811sensor[devId].start()
		goodData = True
	if not goodData:
		badSensor+=1
		if badSensor >5: 
			ret = "badSensor"
			ccs811sensor[devId].start()

	U.muxTCA9548Areset()
	return ret






############################################
global rawOld
global sensor, sensors, badSensor
global deltaX, ccs811sensor, minSendDelta
global	lastRead
global startTime,  lastMeasurement, lastTemp, lastVOC, countVOC, countCO2, lastCO2, reStartReq 


lastTemp					= -100
lastVOC						= -100	  
countVOC					= 0
countCO2					= 0
lastCO2						= -100
reStartReq					 = False


startTime					= time.time()
lastMeasurement				= time.time()
oldRaw						= ""
lastRead					= 0
minSendDelta				= 5.
G.debug						= 5
loopCount					= 0
sensorRefreshSecs			= 91
NSleep						= 100
sensorList					= []
sensors						= {}
sensor						= G.program
quick						= False
display						= "0"
output						= {}
badSensor					= 0
sensorActive				= False
rawOld						= ""
ccs811sensor				   ={}
deltaX				  = {}
displayEnable				= 0
myPID		= str(os.getpid())
U.killOldPgm(myPID,G.program+".py")# kill old instances of myself if they are still running


if U.getIPNumber() > 0:
	time.sleep(10)
	exit()
readParams()

time.sleep(1)

lastRead = time.time()

U.echoLastAlive(G.program)

#					  used for deltax comparison to trigger update to indigo
lastValues0			= {"CO2":0,	 "VOC":0}
deltaMin			= {"CO2":3,	 "VOC":2}
lastValues			= {}
lastValues2			= {}
lastData			= {}
lastSend			= 0
lastDisplay			= 0
lastRead			= time.time()
G.lastAliveSend		= time.time() -1000

msgCount			= 0
loopSleep			= sensorRefreshSecs
sensorWasBad		= False

while True:
	try:
		data = {"sensors": {sensor:{}}}
		sendData = False
		if sensor in sensors:
			for devId in sensors[sensor]:
				if devId not in lastValues: 
					lastValues[devId]  =copy.copy(lastValues0)
					lastValues2[devId] =copy.copy(lastValues0)
				values = getValues(devId)
				if values == "": continue
				data["sensors"][sensor][devId]={}
				if values =="badSensor":
					sensorWasBad = True
					data["sensors"][sensor][devId]="badSensor"
					if badSensor < 5: 
						U.toLog(-1," bad sensor")
						U.sendURL(data)
					else:
						U.restartMyself(param="", reason="badsensor",doPrint=True)
					lastValues2[devId] =copy.copy(lastValues0)
					lastValues[devId]  =copy.copy(lastValues0)
					if badSensor > 5: reStartReq = True 
					continue
				elif values["CO2"] !="" :
					if sensorWasBad: # sensor was bad, back up again, need to do a restart to set config 
						U.restartMyself(reason=" back from bad sensor, need to restart to get sensors reset",doPrint="False")
					
					data["sensors"][sensor][devId] = values
					deltaN =0
					for xx in lastValues0:
						try:
							current = float(values[xx])
							delta= abs(current-lastValues2[devId][xx])
							if delta < deltaMin[xx]: continue
							delta  /=  max (0.5,(current+lastValues2[devId][xx])/2.)
							deltaN = max(deltaN,delta) 
							lastValues[devId][xx] = current
						except: pass
				else:
					continue
				if ( msgCount > 5 and (	 ( deltaN > deltaX[devId]  ) or	 (	time.time() - abs(G.sendToIndigoSecs) > G.lastAliveSend	 ) or  quick   ) and  ( time.time() - G.lastAliveSend > minSendDelta ) ):
					sendData = True
					lastValues2[devId] = copy.copy(lastValues[devId])
				msgCount  +=1

		if sendData:
			U.sendURL(data)
		loopCount +=1

		##U.makeDATfile(G.program, data)
		quick = U.checkNowFile(G.program)				 
		U.echoLastAlive(G.program)

		if loopCount %5 ==0 and not quick:
			if time.time() - lastRead > 5.:	 
				readParams()
				lastRead = time.time()
		if not quick:
			time.sleep(loopSleep)
		if reStartReq:
			time.sleep(5)
			os.system("/usr/bin/python "+G.homeDir+G.program+".py &")

	except	Exception, e:
		U.toLog(-1, u"in Line '%s' has error='%s'" % (sys.exc_traceback.tb_lineno, e))
		time.sleep(5.)
sys.exit(0)
 

		