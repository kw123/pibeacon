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
sys.path.append(os.getcwd())

import math
import copy
import logging
import smbus2
import math
import serial



sys.path.append(os.getcwd())
import	piBeaconUtils	as U
import	piBeaconGlobals as G

G.program = "mlx90640"


########  serial Read ########
"""MIT License

Copyright (c) 2019 

Permission is hereby granted, free of charge, to any person obtaining a copy
of this software and associated documentation files (the "Software"), to deal
in the Software without restriction, including without limitation the rights
to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
copies of the Software, and to permit persons to whom the Software is
furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in all
copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
SOFTWARE."""


# function to get Emissivity from MCU
def get_emissivity():
	ser.write(serial.to_bytes([0xA5,0x55,0x01,0xFB]))
	read = ser.read(4)
	return read[2]/100

# function to get temperatures from MCU (Celsius degrees x 100)

########################### Main cycle #################################

#######  serial Read ########


########  i2cr Read ########
class MLX90640():
	
	def __init__(self, address=0x33):    #default 0x33
		try: 
			self.address = address
			self.bus = smbus2.SMBus(1)
			self.addr = address
			self.gain = self.getGain()
			self.VDD0 = 3.3
			self.DV = self.getVDD()		
			self.VDD = self.DV+self.VDD0
			self.Ta0 = 25
			self.Ta = self.getTa()
			self.emissivity = 1
			self.TGC = self.getTGC()
			self.chessNotIL = 1
			self.KsTa = self.getKsTa()
			self.KsTo1, self.KsTo2, self.KsTo3, self.KsTo4 = self.getKsTo()
			self.step, self.CT3, self.CT4 = self.getCorners()
			self.CT1 = 40
			self.CT2 = 0		
			self.alphaCorrR1 = 1/float(1+ self.KsTo1*(0-(-40)))
			self.alphaCorrR2 = 1
			self.alphaCorrR3 = 1 + self.KsTo2*(self.CT3-0)
			self.alphaCorrR4 = self.alphaCorrR3*(1+self.KsTo3*(self.CT4-self.CT3))
		except	Exception as e:
			U.logger.log(30,"", exc_info=True)
		
	def getRegs(self,reg,num):
		write = smbus2.i2c_msg.write(self.addr,[reg>>8,reg&0xFF])
		read = smbus2.i2c_msg.read(self.address,num)
		self.bus.i2c_rdwr(write, read)
		return list(read)
			
	def getRegf(self,reg):
		write = smbus2.i2c_msg.write(self.addr,[reg>>8,reg&0xFF])
		read = smbus2.i2c_msg.read(self.address,2)
		self.bus.i2c_rdwr(write, read)
		result = list(read)
		return (result[0]<<8)+result[1]

	def root4(self,num):
		ret = 0
		try:
			ret = math.sqrt(math.sqrt(max(0.,num)))
		except	Exception as e:
			U.logger.log(30,"", exc_info=True)
		return ret 

	def getTGC(self):
		TGC = self.getRegf(0x243C) & 0x00FF
		if TGC > 127:
			TGC = TGC - 256
		
		return TGC
		
	def getVDD(self):
		Kvdd = (self.getRegf(0x2433) & 0xFF00)/256
		if Kvdd > 127:
			Kvdd = Kvdd -256
		Kvdd = Kvdd*32
		
		Vdd25 = self.getRegf(0x2433) & 0x00FF
		Vdd25 = (Vdd25-256)*32 - 8192
		
		RAM = self.getRegf(0x072A)
		if RAM > 32767:
			RAM = RAM - 65536

		DV = (RAM - Vdd25)/float(Kvdd)	
		
		return DV

	def getTa(self):
		KVptat = (self.getRegf(0x2432) & 0xFC00)/1024
		if KVptat > 31:
			KVptat = KVptat - 62
		
		KVptat = KVptat/4096.0
		
		KTptat = self.getRegf(0x2432) & 0x03FF
		if KTptat > 511:
			KTptat = KTptat - 1022
		
		KTptat = KTptat/8.0
		
		Vptat25 = self.getRegf(0x2431)
		if Vptat25 > 32767:
			Vptat25 = Vptat25 - 65536
		Vptat = self.getRegf(0x0720)
		if Vptat > 32767:
			Vptat = Vptat - 65536
		Vbe = self.getRegf(0x0700)
		if Vbe > 32767:
			Vbe = Vbe - 65536
		AlphaptatEE = (self.getRegf(0x2410) & 0xF000)/4096
		Alphaptat = (AlphaptatEE/4)+8
		Vptatart = (Vptat/float(Vptat * Alphaptat + Vbe))*262144
		
		Ta = ((Vptatart/float(1+KVptat*self.DV)-Vptat25)/float(KTptat))+self.Ta0
		return Ta

	def getGain(self):
		GAIN = self.getRegf(0x2430)
		if GAIN > 32767:
			GAIN = GAIN - 65536
		RAM = self.getRegf(0x070A)
		if RAM > 32767:
			RAM = RAM - 65536
		return GAIN/float(RAM)
				
	def pixnum(self,i,j):
		return (i-1)*32 + j

	def patternChess(self,i,j):
		pixnum = self.pixnum(i,j)
		a = (pixnum-1)/32
		b = int((pixnum-1)/32)/2
		return int(a) - int(b)*2
		
	def getKsTa(self):
		KsTaEE = (self.getRegf(0x243C) & 0xFF00) >> 256
		if KsTaEE > 127:
			KsTaEE = KsTaEE -256
		
		KsTa = KsTaEE/8192.0
		return KsTa
	
	def getKsTo(self):
		EE1 = self.getRegf(0x243D)
		EE2 = self.getRegf(0x243E)
		KsTo1 = EE1 & 0x00FF
		KsTo3 = EE2 & 0x00FF
		KsTo2 = (EE1 & 0xFF00) >> 8
		KsTo4 = (EE2 & 0xFF00) >> 8

		if KsTo1 > 127:
			KsTo1 = KsTo1 -256
		if KsTo2 > 127:
			KsTo2 = KsTo2 -256
		if KsTo3 > 127:
			KsTo3 = KsTo3 -256
		if KsTo4 > 127:
			KsTo4 = KsTo4 -256
		
		KsToScale = (self.getRegf(0x243F) & 0x000F)+8
		KsTo1 = KsTo1/float(pow(2,KsToScale))
		KsTo2 = KsTo2/float(pow(2,KsToScale))
		KsTo3 = KsTo3/float(pow(2,KsToScale))
		KsTo4 = KsTo4/float(pow(2,KsToScale))
		return KsTo1, KsTo2, KsTo3, KsTo4
		
	def getCorners(self):
		EE = self.getRegf(0x243F)
		step = ((EE & 0x3000)>>12)*10
		CT3 = ((EE & 0x00f0)>>4)*step
		CT4 = ((EE & 0x0f00)>>8)*(step+CT3)
		return step, CT3, CT4
		
	def getPixData(self,i,j):
		Offsetavg = self.getRegf(0x2411)
		if Offsetavg > 32676:
			Offsetavg = Offsetavg-65536

		scaleVal = self.getRegf(0x2410)
		OCCscaleRow = (scaleVal&0x0f00)/256
		OCCscaleCol = (scaleVal&0x00F0)/16
		OCCscaleRem = (scaleVal&0x000F)
		rowAdd = 0x2412 + ((i-1)/4)
		colAdd = 0x2418 + ((j-1)/4)
		rowMask = 0xF<<(4*((i-1)%4))
		colMask = 0xF<<(4*((j-1)%4))

		OffsetPixAdd = 0x243F+((i-1)*32)+j
		OffsetPixVal = self.getRegf(OffsetPixAdd)
		OffsetPix = (OffsetPixVal & 0xFC00)/1024
		if OffsetPix >31:
			OffsetPix = OffsetPix - 64

		OCCRow = (self.getRegf(rowAdd) & rowMask)>>(4*((i-1)%4))
		if OCCRow >7:
			OCCRow = OCCRow -16

		OCCCol = (self.getRegf(colAdd) & colMask)>>(4*((j-1)%4))
		if OCCCol > 7:
			OCCCol = OCCCol -16

		pixOffset = Offsetavg + OCCRow*pow(2,OCCscaleRow) + OCCCol*pow(2,OCCscaleCol) + OffsetPix*pow(2,OCCscaleRem)
		
		KtaEE = (OffsetPixVal & 0x000E)/2
		if KtaEE > 3:
			KtaEE = KtaEE - 7

		colEven = not (j%2)
		rowEven = not (i%2)
		rowOdd = not rowEven
		colOdd = not colEven
		KtaAvAddr = 0x2436 + (colEven)
		KtaAvMask = 0xFF00 >> (8*rowEven)
		
		KtaRC = (self.getRegf(KtaAvAddr) & KtaAvMask) >> 8* rowOdd
		if KtaRC > 127:
			KtaRC = KtaAvRC - 256
		
		KtaScale1 = ((self.getRegf(0x2438) & 0x00F0) >>4)+8
		KtaScale2 = (self.getRegf(0x2438) & 0x000F)

		Kta = (KtaRC+(KtaEE<<KtaScale2))/float(pow(2,KtaScale1))
		
		shiftNum = (rowOdd*4)+(colOdd*8)
		KvMask = 0x000F << shiftNum
		Kv = (self.getRegf(0x2434) & KvMask) >> shiftNum
		if Kv > 7:
			Kv = Kv-16
		
		KvScale = (self.getRegf(0x2438) & 0x0F00)>>8
		
		Kv = Kv/float(KvScale)
		
		RAMaddr = 0x400+((i-1)*32)+ j-1
		RAM = self.getRegf(RAMaddr)
		if RAM > 32767:
			RAM = RAM - 65536
		pixGain = RAM*self.gain
		pixOs = pixGain - pixOffset*(1+Kta*(self.Ta - self.Ta0)*(1+Kv*(self.VDD - self.VDD0)))
		return pixOs

	def getCompensatedPixData(self,i,j):
		try: 
			pixOs = self.getPixData(i,j)
			#print i,j,pixOs
			Kgain = ((self.gain -1)/10)+1
		
			pixGainCPSP0 = self.getRegf(0x0708)		
			if pixGainCPSP0 > 32767:
				pixGainCPSP0 = pixGainCPSP0 - 65482
		
			pixGainCPSP1 = self.getRegf(0x0728)
			if pixGainCPSP1 > 32767:
				pixGainCPSP1 = pixGainCPSP1 - 65482
		
			pixGainCPSP0 = pixGainCPSP0*Kgain
			pixGainCPSP1 = pixGainCPSP1*Kgain
		
			OffCPSP0 = self.getRegf(0x243A) & 0x03FF
			if OffCPSP0 > 511:
				OffCPSP0 = OffCPSP0-1024
		
			OffCPSP1d = (self.getRegf(0x243A) &0xFC00)>>10
			if OffCPSP1d > 31:
				OffCPSP1d = OffCPSP1d-64
		
			OffCPSP1 = OffCPSP1d + OffCPSP0
		
			KvtaCPEEVal = self.getRegf(0x243B)
			KvtaScaleVal = self.getRegf(0x2438)
		
			KtaScale1 = ((KvtaScaleVal & 0x00F0)>>4)+8
			KvScale = (KvtaScaleVal & 0x0F00)>>8
		
			KtaCPEE = KvtaCPEEVal & 0x00FF
			if KtaCPEE > 127:
				KtaCPEE = KtaCPEE -256
		
			KvCPEE = (KvtaCPEEVal & 0xFF00)>>8
		
			KtaCP = KtaCPEE/float(pow(2,KtaScale1))
			KvCP = KvCPEE/float(pow(2,KvScale))
		
			b = (1+KtaCP*(self.Ta - self.Ta0))*(1+ KvCP*(self.VDD - self.VDD0))
			pixOSCPSP0 = pixGainCPSP0 - OffCPSP0*b
			pixOSCPSP1 = pixGainCPSP1 - OffCPSP1*b
		
			if self.chessNotIL:
				pattern = self.patternChess(i,j)
			else:
				pattern = self.patternChess(i,j)
		
			VIREmcomp = pixOs/self.emissivity
			VIRcomp = VIREmcomp - self.TGC*((1-pattern)*pixOSCPSP0 + pattern*pixOSCPSP1)
			###########TESTED TO HERE
		
			reg2439val = self.getRegf(0x2439)
			reg2420val = self.getRegf(0x2420)
			alphaScaleCP = ((reg2420val & 0xF000)>>12) + 27
			CPP1P0ratio = (reg2439val & 0xFC00)>>10
			if CPP1P0ratio >31:
				CPP1P0ratio = CPP1P0ratio -64
		
			alphaRef = self.getRegf(0x2421)
			alphaScale = ((reg2420val & 0xF000)>>12) + 30
		
			rowAdd = 0x2422 + ((i-1)/4)
			colAdd = 0x2428 + ((j-1)/4)
			rowMask = 0xF<<(4*((i-1)%4))
			colMask = 0xF<<(4*((j-1)%4))		

			ACCRow = (self.getRegf(rowAdd) & rowMask)>>(4*((i-1)%4))
			if ACCRow >7:
				ACCRow = ACCRow -16

			ACCCol = (self.getRegf(colAdd) & colMask)>>(4*((j-1)%4))
			if ACCCol > 7:
				ACCCol = ACCCol -16
		
			ACCScaleRow = (reg2420val & 0x0F00)>>8
			ACCScaleCol = (reg2420val & 0x00F0)>>4
			ACCScaleRem = (reg2420val & 0x000F)
		
			alphaPixel = (self.getRegf(0x241f+self.pixnum(i,j))&0x03f0)>>4
		
			alpha = (alphaRef+(ACCRow<<ACCScaleRow)+(ACCCol<<ACCScaleCol)+(alphaPixel<<ACCScaleRem))/float(pow(2,alphaScale))
		
			alphaCPSP0 = (reg2439val & 0x03ff)/float(pow(2,alphaScaleCP))
			alphaCPSP1 = alphaCPSP0*(1+CPP1P0ratio/128.0)
			alphacomp= alpha - self.TGC*((1-pattern)*alphaCPSP0 + pattern*alphaCPSP1)*(1+self.KsTa*(self.Ta-self.Ta0))

			Tak4 = pow(self.Ta + 273.15,4)
			Trk4 = pow(self.Ta-8 + 273.15,4)
			Tar = Trk4-(Trk4-Tak4)/self.emissivity
			Sx = self.KsTo2*self.root4(pow(alphacomp,3)*VIRcomp + pow(alphacomp,4)*Tar)
			ret = self.root4((VIRcomp/(alphacomp*(1-self.KsTo2*273.15)+Sx))+Tar) - 273.15
			#print i,j, pixOs, ret
			return ret
		except	Exception as e:
			U.logger.log(30,"", exc_info=True)
		return 0

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
	global usbPort
	try:



		inp,inpRaw,lastRead2 = U.doRead(lastTimeStamp=lastRead)
		if inp == "": return
		if lastRead2 == lastRead: return
		lastRead   = lastRead2
		if inpRaw == oldRaw: return
		oldRaw	   = inpRaw
		
		externalSensor=False
		sensorList=[]
		sensorsOld= copy.deepcopy(sensors)


		
		U.getGlobalParams(inp)
		  
		if "sensorList"			in inp:	 sensorList=			 (inp["sensorList"])
		if "sensors"			in inp:	 sensors =				 (inp["sensors"])
		
 
		if sensor not in sensors:
			U.logger.log(30, "{} is not in parameters = not enabled, stopping {}.py".format(sensor,sensor) )
			exit()
			

		U.logger.log(0, "{} reading new parameter file".format(sensor) )

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

			if devId not in usbPort:	usbPort[devId]						= -1
			test = ""
			try:
				old = usbPort[devId]
				if "usbPort" in sensors[sensor][devId]: 
					test = sensors[sensor][devId]["usbPort"]
					if test != "autoPick" or old.find("USB") == -1:
						usbPort[devId] = sensors[sensor][devId]["usbPort"]
			except: test = "autoPick"

			if old ==-1 or old.find("USB") == -1  or (old !=-1 and test != old and test != "autoUSB") : 
				if test == "autoUSB":
					usbPort[devId] = U.findActiveUSB()
				else: usbPort[devId] = test
				if not U.checkIfusbSerialActive(usbPort[devId]):
					U.logger.log(30, u"{} is not active, return ".format(usbPort[devId]))
					usbPort[devId] =""
					continue
			if old != usbPort[devId]:
				restart = True



			
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

				
			if devId not in sensorClass or  restart:
				startSensor(devId, i2cAddress)
				if sensorClass[devId] =="":
					return
			U.logger.log(30," new parameters read: i2cAddress:{}".format(i2cAddress) +"; minSendDelta:{}".format(minSendDelta)+
					   ";  deltaX:{}".format(deltaX[devId])+";  sensorRefreshSecs:{}".format(sensorRefreshSecs) )
				
		deldevID={}		   
		for devId in sensorClass:
			if devId not in sensors[sensor]:
				deldevID[devId]=1
		for dd in  deldevID:
			del sensorClass[dd]
		if len(sensorClass) ==0: 
			####exit()
			pass



	except	Exception as e:
		U.logger.log(30,"", exc_info=True)
		


#################################
def startSensor(devId,i2cAddress):
	global sensors,sensor
	global startTime
	global sensorClass, oldPix,  ny,ny
	global ser
	global usbPort
	try: 
		U.logger.log(30,"==== Start {} ===== @ address use: {} ".format(sensor,i2cAddress))
		startTime =time.time()

		p =[]
		oldPix[devId] =[]
		for ii in range(ny):
			p.append(0)
		for ii in range(nx):
			oldPix[devId].append(p)


		i2cAdd = U.muxTCA9548A(sensors[sensor][devId]) # switch mux on if requested and use the i2c address of the mix if enabled
		if str(i2cAdd).find("USB") >-1 or str(i2cAdd).find("serial") >-1:
			U.muxTCA9548Areset()

			if str(i2cAdd).find("serial") >-1: 
				devName = U.getSerialDEV()
				sensorClass[devId] = serial.Serial(devName)
				sensorClass[devId].baudrate = 115200

				# set frequency of module to 4 Hz
				sensorClass[devId].write(serial.to_bytes([0xA5,0x25,0x01,0xCB]))
				time.sleep(0.1)

				# Starting automatic data colection
				sensorClass[devId].write(serial.to_bytes([0xA5,0x35,0x02,0xDC]))
			else:
				devName = usbPort[devId]
				sensorClass[devId] = serial.Serial(devName)
				sensorClass[devId].baudrate = 115200

				# set frequency of module to 4 Hz
				sensorClass[devId].write(serial.to_bytes([0xA5,0x25,0x01,0xCB]))
				time.sleep(0.1)

				# Starting automatic data colection
				sensorClass[devId].write(serial.to_bytes([0xA5,0x35,0x02,0xDC]))

		if int(i2cAdd) >0:
				try:
					U.logger.log(30, u" i2cAdd {}".format(i2cAdd) )
					sensorClass[devId]  =	  MLX90640(address=i2cAdd)
				except	Exception as e:
					U.logger.log(30,"", exc_info=True)
					sensorClass[devId] =""
				time.sleep(1)

	except	Exception as e:
		U.logger.log(30,"", exc_info=True)


#################################
def convertPixels(oldPix,pix,nx,ny):
		try:
	
			minV =9999
			maxV = -111
			aveV = 0
			nVal = nx*ny
		
			movement	= 0
			movementabs = 0
			nAve = 0
			for ii in range(nx):
				for jj in range(ny):
					if  pix[ii][jj] < 60 and  pix[ii][jj] > -10:
						aveV += pix[ii][jj]
						nAve +=1
			aveV /= max(nAve,1)
			uniformity	= 0

			for ii in range(nx):
				for jj in range(ny):
					if  pix[ii][jj] > 60 or  pix[ii][jj] < -10 or abs(pix[ii][jj]-aveV) > 20:
						 pix[ii][jj] = round(aveV,1)

					if pix[ii][jj] > maxV: maxV= pix[ii][jj]
					if pix[ii][jj] < minV: minV= pix[ii][jj]
					delta		 	=   (pix[ii][jj] - oldPix[ii][jj]) / max(0.1, pix[ii][jj]+oldPix[ii][jj]) 
					movement		+=  ( delta )
					movementabs		+=  ( delta*delta )
					uniformity 		+= (pix[ii][jj]- aveV)**2
			movement	= 100.*(movement/nVal)
			movementabs = 100.*math.sqrt(movementabs/nVal)
			uniformity  = nVal/max(0.1,math.sqrt(uniformity) )

			ret	 = {	 
				"MaximumPixel":			round(maxV, 1),
				"MinimumPixel":			round(minV, 1),
				"temp":					round(aveV, 1),
				"Uniformity":			round(uniformity, 6),
				"Movement":				round(movement, 6), 
				"MovementAbs":			round(movementabs, 6)}
			ret["rawData"] =json.dumps(pix).replace(" ","")
			return ret
		except	Exception as e:
			U.logger.log(30,"", exc_info=True)
		return ""



#################################
def getValues(devId):
	global sensor, sensors,	 sensorClass, badSensor
	global oldPix, ny,ny
	global startTime
	global lastMeasurement
	global uniformityOLD,  movementOLD, horizontal1OLD, horizontal2OLD, vertical1OLD, vertical2OLD
	global ser

	val = ""
	try:
		#print "len", len(pix[devId]), len(pix[devId][0]), nx, ny
		i2cAdd = U.muxTCA9548A(sensors[sensor][devId]) # switch mux on if requested and use the i2c address of the mix if enabled
		if str(i2cAdd).find("USB") >-1 or str(i2cAdd).find("serial"):
				U.muxTCA9548Areset()
				ddd = sensorClass[devId].read(1544)
				rawData=[]
				for ii in range(nx):
					ttt =[]
					for jj in range(ny):
						ind = ( ii*ny +jj )*2
						ttt.append(round( float(ord(ddd[ind+4]) + ord(ddd[ind+1+4])*256)/100, 1))
					rawData.append(ttt)
		else:
			if int(i2cAdd) >0:
				if sensorClass[devId] =="":
					badSensor +=1
				return "badSensor"
				rawData=[]
				for ii in range(nx):
					ttt =[]
					for jj in range(ny):
						ttt.append(round(sensorClass[devId].getCompensatedPixData(ii,jj),1)) 
						#print jj,ttt
					rawData.append(ttt)
					#print "after",pix[devId], ttt
				val["ambientTemperature"] = 0
				U.muxTCA9548Areset()

		#print rawData
		val = convertPixels(oldPix[devId],rawData,nx,ny)
		val["ambientTemperature"] = round(float(  (ord(ddd[1540]) + ord(ddd[1541])*256) )/100.,1)
		 ##  [maxV, minV, aveV, uniformity, movement, movementabs]
		oldPix[devId] = copy.deepcopy(rawData)

		#U.logger.log(30, " pix {}".format( pix[devId]))
		badSensor = 0
	except	Exception as e:
		U.logger.log(30,"", exc_info=True)
		badSensor+=1
		if badSensor >3: ret = "badSensor"
	return val





############################################
global rawOld
global sensor, sensors, badSensor
global deltaX, sensorClass, minSendDelta
global oldRaw, lastRead
global startTime,  lastMeasurement
global oldPix,  ny,ny
global uniformityOLD,  movementOLD, horizontal1OLD, horizontal2OLD, vertical1OLD, vertical2OLD 
global usbPort
usbPort						= {}
oldPix						= {}
nx							= 32
ny							= 24

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
sensorClass					={}
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
lastValues0			= {"temp":0,  "MovementAbs":0,	"Uniformity":0,	 }
deltaMin			= {"temp":0.3,"MovementAbs":0.8,"Uniformity":1.0 }
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
					lastValues[devId]  =copy.deepcopy(lastValues0)
					lastValues2[devId] =copy.deepcopy(lastValues0)
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
					lastValues2[devId] =copy.deepcopy(lastValues0)
					lastValues[devId]  =copy.deepcopy(lastValues0)
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
					lastValues2[devId] = copy.deepcopy(lastValues[devId])
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
	except	Exception as e:
		U.logger.log(30,"", exc_info=True)
		time.sleep(5.)
try: 	G.sendThread["run"] = False; time.sleep(1)
except: pass
sys.exit(0)
 

		