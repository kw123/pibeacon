#!/usr/bin/python
# -*- coding: utf-8 -*-
# by Karl Wachs
# 2018-01-10
# version 0.9 
##
##
#! /usr/bin/env python
# -*- coding: utf-8 -*-
####################

import sys, os, time, json, datetime,subprocess,copy
import math
import copy
import logging
from collections import OrderedDict
import smbus


sys.path.append(os.getcwd())
import	piBeaconUtils	as U
import	piBeaconGlobals as G
G.program = "amg88xx"


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




class bitfield(object):
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


# AMG88xx default address.
AMG88xx_I2CADDR	   = 0x69

AMG88xx_PCTL		= 0x00
AMG88xx_RST			= 0x01
AMG88xx_FPSC		= 0x02
AMG88xx_INTC		= 0x03
AMG88xx_STAT		= 0x04
AMG88xx_SCLR		= 0x05
#0x06 reserved
AMG88xx_AVE			= 0x07
AMG88xx_INTHL		= 0x08
AMG88xx_INTHH		= 0x09
AMG88xx_INTLL		= 0x0A
AMG88xx_INTLH		= 0x0B
AMG88xx_IHYSL		= 0x0C
AMG88xx_IHYSH		= 0x0D
AMG88xx_TTHL		= 0x0E
AMG88xx_TTHH		= 0x0F
AMG88xx_INT_OFFSET	= 0x010
AMG88xx_PIXEL_OFFSET = 0x80

# Operating Modes
AMG88xx_NORMAL_MODE = 0x00
AMG88xx_SLEEP_MODE	= 0x01
AMG88xx_STAND_BY_60 = 0x20
AMG88xx_STAND_BY_10 = 0x21

#sw resets
AMG88xx_FLAG_RESET	= 0x30
AMG88xx_INITIAL_RESET = 0x3F
	
#frame rates
AMG88xx_FPS_10		= 0x00
AMG88xx_FPS_1		= 0x01
	
#int enables
AMG88xx_INT_DISABLED = 0x00
AMG88xx_INT_ENABLED		= 0x01
	
#int modes
AMG88xx_DIFFERENCE	= 0x00
AMG88xx_ABSOLUTE_VALUE = 0x01

AMG88xx_PIXEL_ARRAY_SIZE = 64
AMG88xx_PIXEL_TEMP_CONVERSION = .25
AMG88xx_THERMISTOR_CONVERSION = .0625

def constrain(val, min_val, max_val):
	return min(max_val, max(min_val, val))
		

class AMG88xx_class(object):
	def __init__(self, mode=AMG88xx_NORMAL_MODE, address=AMG88xx_I2CADDR, i2c=None, **kwargs):
		try:
			self._logger = logging.getLogger('AMG88xx')
			# Check that mode is valid.
			if mode not in [AMG88xx_NORMAL_MODE, AMG88xx_SLEEP_MODE, AMG88xx_STAND_BY_60, AMG88xx_STAND_BY_10]:
				raise ValueError('Unexpected mode value {0}.  Set mode to one of AMG88xx_NORMAL_MODE, AMG88xx_SLEEP_MODE, AMG88xx_STAND_BY_60, or AMG88xx_STAND_BY_10'.format(mode))
			self._mode = mode
			# Create I2C device.
			self.bus = smbus.SMBus(1)
			self.i2c_addr  = address

			#set up the registers
			self._pctl	= bitfield([('PCTL', 8)])
			self._rst	= bitfield([('RST', 8)])
			self._fpsc	= bitfield([('FPS', 1)])
			self._intc	= bitfield([('INTEN', 1), ('INTMOD', 1)])
			self._stat	= bitfield([('unused', 1), ('INTF', 1), ('OVF_IRS', 1), ('OVF_THS', 1)])
			self._sclr	= bitfield([('unused', 1), ('INTCLR', 1), ('OVS_CLR', 1), ('OVT_CLR', 1)])
			self._ave	= bitfield([('unused', 5), ('MAMOD', 1)])

			self._inthl = bitfield([('INT_LVL_H', 8)])
			self._inthh = bitfield([('INT_LVL_H', 4)])

			self._intll = bitfield([('INT_LVL_H', 8)])
			self._intlh = bitfield([('INT_LVL_L', 4)])

			self._ihysl = bitfield([('INT_HYS', 8)])
			self._ihysh = bitfield([('INT_HYS', 4)])

			self._tthl	= bitfield([('TEMP', 8)])
			self._tthh	= bitfield([('TEMP',3), ('SIGN',1)])

			#enter normal mode
			self._pctl.PCTL = self._mode
			self.bus.write_byte_data(self.i2c_addr,AMG88xx_PCTL, self._pctl.get())

			#software reset
			self._rst.RST = AMG88xx_INITIAL_RESET
			self.bus.write_byte_data(self.i2c_addr,AMG88xx_RST, self._rst.get())

			#disable interrupts by default
			self.disableInterrupt()

			#set to 10 FPS
			self._fpsc.FPS = AMG88xx_FPS_10
			self.bus.write_byte_data(self.i2c_addr,AMG88xx_FPSC, self._fpsc.get())
		except	Exception, e:
			U.logger.log(30, u"in Line {} has error={}".format(sys.exc_traceback.tb_lineno, e))
		return 

	def readU16(self, reg, little_endian=True):
		"Reads an unsigned 16-bit value from the I2C device"
		try:
			result = self.bus.read_word_data(self.i2c_addr,reg)
			# Swap bytes if using big endian because read_word_data assumes little
			# endian on ARM (little endian) systems.
			if not little_endian:
				result = ((result << 8) & 0xFF00) + (result >> 8)
			return result
		except IOError, err:
			return self.errMsg()

	def readS16(self, reg, little_endian=True):
		"Reads a signed 16-bit value from the I2C device"
		try:
			result = self.readU16(reg,little_endian)
			if result > 32767: result -= 65536
			return result
		except IOError, err:
			return self.errMsg()

	def write8(self, reg, value):
		"Writes an 8-bit value to the specified register/address"
		try:
			self.bus.write_byte_data(self.i2c_addr, reg, value)
			if self.debug:
				print "I2C: Wrote 0x%02X to register 0x%02X" % (value, reg)
		except IOError, err:
			return self.errMsg()


	def setMovingAverageMode(self, mode):
		self._ave.MAMOD = mode
		self.bus.write_byte_data(self.i2c_addr,AMG88xx_AVE, self._ave.get())

	def setInterruptLevels(self, high, low, hysteresis):

		highConv = int(high / AMG88xx_PIXEL_TEMP_CONVERSION)
		highConv = constrain(highConv, -4095, 4095)
		self._inthl.INT_LVL_H = highConv & 0xFF

		self._inthh.INT_LVL_H = (highConv & 0xF) >> 4
		self.bus.write_byte_data(self.i2c_addr,AMG88xx_INTHL, self._inthl.get())
		self.bus.write_byte_data(self.i2c_addr,AMG88xx_INTHH, self._inthh.get())

		lowConv = int(low / AMG88xx_PIXEL_TEMP_CONVERSION)
		lowConv = constrain(lowConv, -4095, 4095)
		self._intll.INT_LVL_L = lowConv & 0xFF
		self._intlh.INT_LVL_L = (lowConv & 0xF) >> 4
		self.bus.write_byte_data(self.i2c_addr,AMG88xx_INTLL, self._intll.get())
		self.bus.write_byte_data(self.i2c_addr,AMG88xx_INTLH, self._intlh.get())

		hysConv = int(hysteresis / AMG88xx_PIXEL_TEMP_CONVERSION)
		hysConv = constrain(hysConv, -4095, 4095)
		self._ihysl.INT_HYS = hysConv & 0xFF
		self._ihysh.INT_HYS = (hysConv & 0xF) >> 4
		self.bus.write_byte_data(self.i2c_addr,AMG88xx_IHYSL, self._ihysl.get())
		self.bus.write_byte_data(self.i2c_addr,AMG88xx_IHYSH, self._ihysh.get())


	def enableInterrupt(self):

		self._intc.INTEN = 1
		self.bus.write_byte_data(self.i2c_addr,AMG88xx_INTC, self._intc.get())


	def disableInterrupt(self):

		self._intc.INTEN = 0
		self.bus.write_byte_data(self.i2c_addr,AMG88xx_INTC, self._intc.get())


	def setInterruptMode(self, mode):

		self._intc.INTMOD = mode
		self.bus.write_byte_data(self.i2c_addr,AMG88xx_INTC, self._intc.get())


	def getInterrupt(self):
		buf = []
		for i in range(0, 8):
			buf.append(self.bus.read_byte_data(self.address,AMG88xx_INT_OFFSET + i))
			
		return buf

	def clearInterrupt(self):

		self._rst.RST = AMG88xx_FLAG_RESET
		self.write8(AMG88xx_RST, self._rst.get())


	def readThermistor(self):

		raw = self.readU16(AMG88xx_TTHL)
		return self.signedMag12ToFloat(raw) * AMG88xx_THERMISTOR_CONVERSION
	
	def readPixels(self,oldPixels):
		try:
			buf = []
	
			minV =9999
			maxV = -111
			aveV = 0
			nVal = 0
		
			ambtemp		= self.readThermistor() 
			movement	= 0
			movementabs = 0
			blockSize	= 32
			blockSize2	= blockSize/2
			lines		= 8
			nBlocks		= AMG88xx_PIXEL_ARRAY_SIZE / blockSize * 2
			buf = copy.copy(oldPixels)
			rawData	   =""
			for ii in range(nBlocks):
				offset = AMG88xx_PIXEL_OFFSET+ii*blockSize
				block = self.bus.read_i2c_block_data( self.i2c_addr, offset, blockSize)
				##print block
				for i in range(blockSize2):

					converted = self.twoCompl12( ( block[i*2+1] << 8) + block[i*2] ) * AMG88xx_PIXEL_TEMP_CONVERSION 
					#print converted, block[i*2+1], block[i*2], (block[i*2+1] << 8) + block[i*2] 
					buf[nVal] = converted
					nVal	 += 1
					aveV	 += converted

					if converted > maxV: maxV= converted
					if converted < minV: minV= converted

					k = ii*blockSize2+i
					delta		   =  ( (converted - oldPixels[k]) / max(0.1,converted+oldPixels[k]) )
					movement	  +=  ( delta )
					movementabs	  +=  ( delta )**2 
			movement	= 100*(movement/nVal)
			movementabs = 100*math.sqrt(movementabs/nVal)
			aveV /= max(nVal,1)

			uniformity	= 0
			for k in range(nVal):
				uniformity += (buf[k] - aveV)**2
			uniformity = nVal/max(0.1,math.sqrt(uniformity) )

			if False:
				vertical1	 = 0
				horizontal1	 = 0
				vertical2	 = 0
				horizontal2	 = 0
				for i in range(lines):
					for j in range(lines-1):
						k  = i + j*lines
						k2 = k +   lines
						m  = j + i*lines  
						m2 = m + 1
						vertical1	  +=  ( (buf[k]	 - oldPixels[k2])  / max(0.1,oldPixels[k2] + buf[k])  ) 
						vertical2	  +=  ( (buf[k2] - oldPixels[k] ) / max(0.1,oldPixels[k]  + buf[k2]) ) 
						horizontal1	  +=  ( (buf[m]	 - oldPixels[m2])  / max(0.1,oldPixels[m2] + buf[m])  )
						horizontal2	  +=  ( (buf[m2] - oldPixels[m] ) / max(0.1,oldPixels[m]  + buf[m2]) )
						###print i,j,k,k2,m,m2

				vertical1	= 100.*(vertical1/nVal) 
				vertical2	= 100.*(vertical2/nVal) 
				horizontal1 = 100.*(horizontal1/nVal) 
				horizontal2 = 100.*(horizontal2/nVal) 


			return buf, maxV, minV, aveV, nVal, ambtemp, uniformity, movement, movementabs
		except	Exception, e:
			U.logger.log(30, u"in Line {} has error={}".format(sys.exc_traceback.tb_lineno, e))
		return ""

		
	def signedMag12ToFloat(self, val):
		#take first 11 bits as absolute val
		if	0x7FF & val == val:
			return float(val)
		else:
			return	- float(0x7FF & val)

	def twoCompl12(self, val):
		if	0x7FF & val == val:
			return float(val)
		else:
			return float((val-4096))


 # ===========================================================================
# read params
# ===========================================================================

#################################		 
def readParams():
	global sensorList, sensors, logDir, sensor,	 sensorRefreshSecs, displayEnable
	global rawOld
	global deltaX, amg88xx, minSendDelta
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
		
 
		if sensor not in sensors:
			U.logger.log(30, "amg88xx is not in parameters = not enabled, stopping amg88xx.py" )
			exit()
			

		U.logger.log(0, "amg88xx reading new parameter file" )

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
				sensorRefreshSecs = 91	  
			if old != sensorRefreshSecs: restart = True

			
			i2cAddress = U.getI2cAddress(sensors[sensor][devId], default ="")

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

				
			if devId not in amg88xxsensor or  restart:
				startSensor(devId, i2cAddress)
				if amg88xxsensor[devId] =="":
					return
			U.logger.log(30," new parameters read: i2cAddress:" +unicode(i2cAddress) +";	 minSendDelta:"+unicode(minSendDelta)+
					   ";  deltaX:"+unicode(deltaX[devId])+";  sensorRefreshSecs:"+unicode(sensorRefreshSecs) )
				
		deldevID={}		   
		for devId in amg88xxsensor:
			if devId not in sensors[sensor]:
				deldevID[devId]=1
		for dd in  deldevID:
			del amg88xxsensor[dd]
		if len(amg88xxsensor) ==0: 
			####exit()
			pass



	except	Exception, e:
		U.logger.log(30, u"in Line {} has error={}".format(sys.exc_traceback.tb_lineno, e))
		print sensors[sensor]
		



def startSensor(devId,i2cAddress):
	global sensors,sensor
	global startTime
	global amg88xxsensor, oldPixels
	U.logger.log(30,"==== Start amg88xx ===== @ i2c= " +unicode(i2cAddress))
	startTime =time.time()


	i2cAdd = U.muxTCA9548A(sensors[sensor][devId]) # switch mux on if requested and use the i2c address of the mix if enabled
	oldPixels[devId]	= [0 for ii in range(64)]
	
	try:
		amg88xxsensor[devId]  =	 AMG88xx_class(address=i2cAdd)
		
	except	Exception, e:
		U.logger.log(30, u"in Line {} has error={}".format(sys.exc_traceback.tb_lineno, e))
		amg88xxsensor[devId] =""
	time.sleep(.1)

	U.muxTCA9548Areset()



#################################
def getValues(devId):
	global sensor, sensors,	 amg88xxsensor, badSensor
	global oldPixels
	global startTime
	global lastMeasurement
	global uniformityOLD,  movementOLD, horizontal1OLD, horizontal2OLD, vertical1OLD, vertical2OLD

	ret = ""
	try:
		if amg88xxsensor[devId] =="":
			badSensor +=1
			return "badSensor"
		i2cAdd = U.muxTCA9548A(sensors[sensor][devId]) # switch mux on if requested and use the i2c address of the mix if enabled
		##print oldPixels
		oldPixels[devId] , maxV, minV, average, nPixels, AmbientTemperature, uniformity,  movement, movementAbs= amg88xxsensor[devId].readPixels(oldPixels[devId])
		#print	"  average %5.1f AmbientTemperature %5.1f movement %4.2f movementAbs %4.2f	uniformity %4.2f "%( average, AmbientTemperature, movement, movementAbs, uniformity)
		#print	"  movement %4.2f  uniformity %4.2f horizontal1 %4.1f horizontal2 %4.1f vertical1 %4.1f vertical2 %4.1f"%(	movement-movementOLD, uniformity-uniformityOLD, horizontal1-horizontal1OLD, horizontal2-horizontal2OLD, vertical1-vertical1OLD, vertical2-vertical2OLD)
	 
			 
		ret	 = {"Movement":				( "%7.1f"%( movement			) ).strip(), 
				"MovementAbs":			( "%7.1f"%( movementAbs			  ) ).strip(), 
#				 "Vertical1":			 ( "%7.3f"%( vertical1			 ) ).strip(), 
#				 "Horizontal1":			 ( "%7.3f"%( horizontal1		 ) ).strip(), 
				"Uniformity":			( "%7.1f"%( uniformity			) ).strip(), 
				"AmbientTemperature":	( "%7.1f"%( AmbientTemperature	) ).strip(), 
				"MaximumPixel":			( "%7.1f"%( maxV				) ).strip(), 
				"MinimumPixel":			( "%7.1f"%( minV				) ).strip(), 
				"temp":					( "%7.1f"%( average				) ).strip(),
				"rawData":				json.dumps(oldPixels[devId]).replace(" ","")}
		U.logger.log(0, unicode(ret)) 
		badSensor = 0
	except	Exception, e:
		U.logger.log(30, u"in Line {} has error={}".format(sys.exc_traceback.tb_lineno, e))
		badSensor+=1
		if badSensor >3: ret = "badSensor"
	U.muxTCA9548Areset()
	return ret





############################################
global rawOld
global sensor, sensors, badSensor
global deltaX, amg88xxsensor, minSendDelta
global oldRaw, lastRead
global startTime,  lastMeasurement
global oldPixels
global uniformityOLD,  movementOLD, horizontal1OLD, horizontal2OLD, vertical1OLD, vertical2OLD 
oldPixels					={}
uniformityOLD				= 0
movementOLD					= 0
horizontal1OLD				= 0
horizontal2OLD				= 0
vertical1OLD				= 0
vertical2OLD				= 0
	

startTime					= time.time()
lastMeasurement				= time.time()
oldRaw						= ""
lastRead					= 0
minSendDelta				= 5.
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
loopSleep					= 0.5
rawOld						= ""
amg88xxsensor					={}
deltaX				  = {}
displayEnable				= 0
myPID		= str(os.getpid())
U.setLogging()

U.killOldPgm(myPID,G.program+".py")# kill old instances of myself if they are still running


if U.getIPNumber() > 0:
	time.sleep(10)
	exit()

readParams()

time.sleep(1)

lastRead = time.time()

U.echoLastAlive(G.program)

#					  used for deltax comparison to trigger update to indigo
lastValues0			= {"temp":0,  "MovementAbs":0,	"Uniformity":0,	 "AmbientTemperature":0}
deltaMin			= {"temp":0.3,"MovementAbs":0.8,"Uniformity":1.0,"AmbientTemperature":0.5}
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
						U.logger.log(30," bad sensor")
						U.sendURL(data)
					else:
						U.restartMyself(param="", reason="badsensor",doPrint=True)
					lastValues2[devId] =copy.copy(lastValues0)
					lastValues[devId]  =copy.copy(lastValues0)
					continue
				elif values["temp"] !="" :
					if sensorWasBad: # sensor was bad, back up again, need to do a restart to set config 
						U.restartMyself(reason=" back from bad sensor, need to restart to get sensors reset",doPrint=False)
					
					data["sensors"][sensor][devId] = values
					deltaN =0
					for xx in lastValues0:
						try:
							current = float(values[xx])
							delta= abs(current-lastValues2[devId][xx])
							if delta < deltaMin[xx]: continue
							delta  /= max (0.5,(current+lastValues2[devId][xx])/2.)
							deltaN	= max(deltaN,delta) 
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
		if	U.checkNewCalibration(G.program): gasBaseLine = -200 # forces new calibration				
		U.echoLastAlive(G.program)

		if loopCount %5 ==0 and not quick:
			if time.time() - lastRead > 5.:	 
				readParams()
				lastRead = time.time()
		#if gasBaseLine ==0: loopSleep = 1
		#else:				 loopSleep = sensorRefreshSecs
		if not quick:
			time.sleep(loopSleep)
	except	Exception, e:
		U.logger.log(30, u"in Line {} has error={}".format(sys.exc_traceback.tb_lineno, e))
		time.sleep(5.)
try: 	G.sendThread["run"] = False; time.sleep(1)
except: pass
sys.exit(0)
 

		