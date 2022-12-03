#!/usr/bin/python
# -*- coding: utf-8 -*-
## adopted from adafruit 
#
#

import sys, os, time, json, datetime,subprocess,copy
import math
import RPi.GPIO as GPIO
try:
	import numpy
	_numpy =True
	import warnings	
	warnings.filterwarnings('ignore')
except:
	_numpy = False

sys.path.append(os.getcwd())
import	piBeaconUtils	as U
import	piBeaconGlobals as G

G.program = "max31865"
#!/usr/bin/python
#The MIT License (MIT)
#
#Copyright (c) 2015 Stephen P. Smith
#
#Permission is hereby granted, free of charge, to any person obtaining a copy
#of this software and associated documentation files (the "Software"), to deal
#in the Software without restriction, including without limitation the rights
#to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
#copies of the Software, and to permit persons to whom the Software is
#furnished to do so, subject to the following conditions:
#
#The above copyright notice and this permission notice shall be included in all
#copies or substantial portions of the Software.
#
#THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
#IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
#FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
#AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
#LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
#OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
#SOFTWARE.


class max31865(object):
	"""Reading Temperature from the MAX31865 with GPIO using 
	   the Raspberry Pi.  Any pins can be used.
	   Numpy can be used to completely solve the Callendar-Van Dusen equation 
	   but it slows the temp reading down.  I commented it out in the code.  
	   Both the quadratic formula using Callendar-Van Dusen equation (ignoring the
	   3rd and 4th degree parts of the polynomial) and the straight line approx.
	   temperature is calculated with the quadratic formula one being the most accurate.
	"""
	
	def __init__(self, csPin, misoPin, mosiPin, clkPin, nWires, referenceResistor, resistorAt0C, hertz50_60):
		self.csPin = csPin
		self.misoPin = misoPin
		self.mosiPin = mosiPin
		self.clkPin = clkPin
		self.setupGPIO()
		self.nWires = nWires
		self.referenceResistor = referenceResistor
		self.resistorAt0C = resistorAt0C
		self.hertz50_60 = hertz50_60
		self.ratio	= self.resistorAt0C/self.referenceResistor
		self.ratio4	= 0.25
		self.comp	= math.sqrt(1 + ( self.ratio4 / self.ratio -1.) )
		
		
	def setupGPIO(self):
		GPIO.setwarnings(False)
		GPIO.setmode(GPIO.BCM)
		GPIO.setup(self.csPin, GPIO.OUT)
		GPIO.setup(self.misoPin, GPIO.IN)
		GPIO.setup(self.mosiPin, GPIO.OUT)
		GPIO.setup(self.clkPin, GPIO.OUT)

		GPIO.output(self.csPin, GPIO.HIGH)
		GPIO.output(self.clkPin, GPIO.LOW)
		GPIO.output(self.mosiPin, GPIO.LOW)

	def readTemp(self):
		#
		# b10000000 = 0x80
		# 0x8x to specify 'write register value'
		# 0xx0 to specify 'configuration register'
		#
		# 0b10110010 = 0xB2
		# Config Register
		# ---------------
		# bit 7: Vbias -> 1 (ON)
		# bit 6: Conversion Mode -> 0 (MANUAL)
		# bit5: 1-shot ->1 (ON)
		# bit4: 3-wire select -> 1 (3 wire config)
		# bits 3-2: fault detection cycle -> 0 (none)
		# bit 1: fault status clear -> 1 (clear any fault)
		# bit 0: 50/60 Hz filter select -> 0 (60Hz)
		#
		# 0b11010010 or 0xD2 for continuous auto conversion 
		# at 60Hz (faster conversion)
		#

		#one shot
		outByte=  0b10100010
		if self.hertz50_60 ==50: outByte | 0b00000001
		if self.nWires     ==3:  outByte | 0b00010000
		self.writeRegister(0, outByte&0xff)

		# conversion time is less than 100ms
		time.sleep(.1) #give it 100ms for conversion

		# read all registers
		out = self.readRegisters(0,8)
		## print self.referenceResistor, out
		conf_reg = out[0]
		#print "config register byte: %x" % conf_reg

		[rtd_msb, rtd_lsb] = [out[1], out[2]]
		rtd_ADC_Code = (( rtd_msb << 8 ) | rtd_lsb ) >> 1
			
		temp_C = self.calcPT100Temp(rtd_ADC_Code)

		[hft_msb, hft_lsb] = [out[3], out[4]]
		hft = (( hft_msb << 8 ) | hft_lsb ) >> 1
		#print "high fault threshold: %d" % hft

		[lft_msb, lft_lsb] = [out[5], out[6]]
		lft = (( lft_msb << 8 ) | lft_lsb ) >> 1
		#print "low fault threshold: %d" % lft

		status = out[7]
		#
		# 10 Mohm resistor is on breakout board to help
		# detect cable faults
		# bit 7: RTD High Threshold / cable fault open 
		# bit 6: RTD Low Threshold / cable fault short
		# bit 5: REFIN- > 0.85 x VBias -> must be requested
		# bit 4: REFIN- < 0.85 x VBias (FORCE- open) -> must be requested
		# bit 3: RTDIN- < 0.85 x VBias (FORCE- open) -> must be requested
		# bit 2: Overvoltage / undervoltage fault
		# bits 1,0 don't care	
		#print "Status byte: %x" % status

		if ((status & 0x80) == 1):
			raise FaultError("High threshold limit (Cable fault/open)")
		if ((status & 0x40) == 1):
			raise FaultError("Low threshold limit (Cable fault/short)")
		if ((status & 0x04) == 1):
			raise FaultError("Overvoltage or Undervoltage Error") 
		return  temp_C
		
	def writeRegister(self, regNum, dataByte):
		GPIO.output(self.csPin, GPIO.LOW)
		
		# 0x8x to specify 'write register value'
		addressByte = 0x80 | regNum;
		
		# first byte is address byte
		self.sendByte(addressByte)
		# the rest are data bytes
		self.sendByte(dataByte)

		GPIO.output(self.csPin, GPIO.HIGH)
		
	def readRegisters(self, regNumStart, numRegisters):
		out = []
		GPIO.output(self.csPin, GPIO.LOW)
		
		# 0x to specify 'read register value'
		self.sendByte(regNumStart)
		
		for byte in range(numRegisters):	
			data = self.recvByte()
			out.append(data)

		GPIO.output(self.csPin, GPIO.HIGH)
		return out

	def sendByte(self,byte):
		for bit in range(8):
			GPIO.output(self.clkPin, GPIO.HIGH)
			if (byte & 0x80):
				GPIO.output(self.mosiPin, GPIO.HIGH)
			else:
				GPIO.output(self.mosiPin, GPIO.LOW)
			byte <<= 1
			GPIO.output(self.clkPin, GPIO.LOW)

	def recvByte(self):
		byte = 0x00
		for bit in range(8):
			GPIO.output(self.clkPin, GPIO.HIGH)
			byte <<= 1
			if GPIO.input(self.misoPin):
				byte |= 0x1
			GPIO.output(self.clkPin, GPIO.LOW)
		return byte	
	
	def calcPT100Temp(self, RTD_ADC):
		if RTD_ADC == 0: return ""
		a = .00390830
		b = -.000000577500
		# c = -4.18301e-12 # for -200 <= T <= 0 (degC)
		c = -0.00000000000418301
		# c = 0 # for 0 <= T <= 850 (degC)
		#print "RTD ADC Code: %d" % RTD_ADC_Code
		Res_RTD = (RTD_ADC) * (self.referenceResistor / 32768.0) # PTxx Resistance
		#print self.referenceResistor, RTD_ADC, Res_RTD
		# Callendar-Van Dusen equation
		# Res_RTD = self.resistorAt0C * (1 + a*T + b*T**2 + c*(T-100)*T**3)
		# Res_RTD = self.resistorAt0C + a*self.resistorAt0C*T + b*self.resistorAt0C*T**2 # c = 0
		# (c*self.resistorAt0C)T**4 - (c*self.resistorAt0C)*100*T**3  
		# + (b*self.resistorAt0C)*T**2 + (a*self.resistorAt0C)*T + (self.resistorAt0C - Res_RTD) = 0
		#
		# quadratic formula:
		# for 0 <= T <= 850 (degC)

		
		temp_CL 	=    (RTD_ADC/(128.*self.ratio4))*self.comp     - 1024.0*self.ratio4/self.comp                                                      

		temp_C = (  -(a*self.resistorAt0C) + math.sqrt(a*self.resistorAt0C* a*self.resistorAt0C - 4*(b*self.resistorAt0C)*(self.resistorAt0C - Res_RTD))  ) / (2*(b*self.resistorAt0C))

		temp_C_numpy = -1000
		temp   = temp_C
		if temp_C < 0 :
			temp = temp_CL
			if _numpy:	
				try:
					# removing numpy.roots will greatly speed things up
					temp_numpy = numpy.roots([c*self.resistorAt0C, -c*self.resistorAt0C*100, b*self.resistorAt0C, a*self.resistorAt0C, (self.resistorAt0C - Res_RTD)])
					#print temp_numpy
					delta= 99999
					ii=0
					for xx in temp_numpy:
						#print ii, xx
						ii+=1
						if xx.imag ==0:
							newDelta = abs((xx.real - temp))
							if newDelta < delta:
								temp_C_numpy = xx.real
								delta = newDelta
					#print ii, temp, temp_C_numpy, delta
					if delta < 10: temp = temp_C_numpy
				except	Exception as e:
					U.logger.log(30,"", exc_info=True)
		
		if temp_C < 0:
			temp = min(0,temp)

		return temp

class FaultError(Exception):
	pass

# ===========================================================================
# read params
# ===========================================================================

#################################		 
def readParams():
	global sensorList, sensors, logDir, sensor,	 sensorRefreshSecs
	global rawOld
	global deltaX, max31865sensor, minSendDelta
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

		
 
		if sensor not in sensors:
			U.logger.log(30, G.program+" is not in parameters = not enabled, stopping "+G.program+".py" )
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
				if "GPIOcsPin" in sensors[sensor][devId]: 			GPIOcsPin = int(sensors[sensor][devId]["GPIOcsPin"])
			except:	GPIOcsPin = 8	   

			try:
				if "GPIOmisoPin" in sensors[sensor][devId]: 		GPIOmisoPin = int(sensors[sensor][devId]["GPIOmisoPin"])
			except:	GPIOmisoPin = 8	   

			try:
				if "GPIOmosiPin" in sensors[sensor][devId]: 		GPIOmosiPin = int(sensors[sensor][devId]["GPIOmosiPin"])
			except:	GPIOmosiPin = 8	   

			try:
				if "GPIOclkPin" in sensors[sensor][devId]: 			GPIOclkPin = int(sensors[sensor][devId]["GPIOclkPin"])
			except:	GPIOclkPin = 8	   

			try:
				if "nWires" in sensors[sensor][devId]: 				nWires = int(sensors[sensor][devId]["nWires"])
			except:	nWires = 3  

			try:
				if "referenceResistor" in sensors[sensor][devId]: 	referenceResistor = float(sensors[sensor][devId]["referenceResistor"])
			except:	referenceResistor = 4300	   


			try:
				if "resistorAt0C" in sensors[sensor][devId]: 		resistorAt0C = float(sensors[sensor][devId]["resistorAt0C"])
			except:	resistorAt0C = 1000	   


			try:
				if "hertz50_60" in sensors[sensor][devId]: 			hertz50_60 = int(sensors[sensor][devId]["hertz50_60"])
			except:	hertz50_60 = 60	   


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

				
			if devId not in max31865sensor:
				U.logger.log(30,"==== Start "+G.program +";   devID: "+ str(devId)+";    R-at 0C: %d"%(resistorAt0C))
				max31865sensor[devId] = max31865(GPIOcsPin,GPIOmisoPin,GPIOmosiPin,GPIOclkPin,nWires,referenceResistor,resistorAt0C,hertz50_60)
				U.logger.log(30," started "+ str(devId))

				
		deldevID={}		   
		for devId in max31865sensor:
			if devId not in sensors[sensor]:
				deldevID[devId]=1
		for dd in  deldevID:
			del max31865sensor[dd]
		if len(max31865sensor) ==0: 
			####exit()
			pass

	except	Exception as e:
		U.logger.log(30,"", exc_info=True)



#################################
def getValues(devId):
	global sensor, sensors,	 max31865sensor, badSensor

	temp = "" 
	try:
		temp	 = max31865sensor[devId].readTemp()
		if temp ==""  or not temp:
			badSensor+=1
			return "badSensor"
		data = {"temp":round(temp,3)}
		badSensor = 0
		return data
	except	Exception as e:
		if badSensor >2 and badSensor < 5: 
			U.logger.log(30,"", exc_info=True)
			U.logger.log(30, u"temp>>{}<<".format(temp))
		badSensor+=1
	if badSensor >3: 
		return "badSensor"
	return ""		 






############################################
global rawOld
global sensor, sensors, badSensor
global deltaX, max31865sensor, minSendDelta
global oldRaw, lastRead

oldRaw						=""
lastRead					= 0

minSendDelta				= 5.
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
loopSleep					= 1
rawOld						= ""
max31865sensor				={}
deltaX						= {}
U.setLogging()

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
		sendNOW = False
		if sensor in sensors:
			data["sensors"] = {sensor:{}}
			for devId in sensors[sensor]:
				if devId not in lastValue: lastValue[devId] =-500.
				values = getValues(devId)
				if values == "": continue
				data["sensors"][sensor][devId] = {}
				if values =="badSensor":
					sensorWasBad = True
					data["sensors"][sensor][devId]["current"]="badSensor"
					if badSensor < 5: 
						U.logger.log(30," bad sensor")
						U.sendURL(data)
					lastValue[devId] =-100.
					continue
				elif values["temp"] !="" :
					if sensorWasBad: # sensor was bad, back up again, need to do a restart to set config 
						U.restartMyself(reason=" back from bad sensor, need to restart to get sensors reset",doPrint=False)
					
					data["sensors"][sensor][devId] = values
					current = float(values["temp"])
					delta	= current-lastValue[devId]
					deltaN	= abs(delta) / max (0.5,(current+lastValue[devId])/2.)
				else:
					continue
				#print values, deltaN, deltaX[devId]
				if ( ( deltaN > deltaX[devId]						   ) or 
					 (	tt - abs(G.sendToIndigoSecs) > G.lastAliveSend	) or  
					 ( quick										   )   ) and  \
				   ( ( tt - G.lastAliveSend > minSendDelta			   )   ):
						sendNOW = True
						lastValue[devId]  = current
			if sendNOW: U.sendURL(data)

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
		
	except	Exception as e:
		U.logger.log(30,"", exc_info=True)
		time.sleep(5.)
try: 	G.sendThread["run"] = False; time.sleep(1)
except: pass
sys.exit(0)
