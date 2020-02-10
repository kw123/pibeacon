#!/usr/bin/env python
# -*- coding: utf-8 -*-



import sys, os, time, json, datetime,subprocess,copy
import smbus

sys.path.append(os.getcwd())
import	piBeaconUtils	as U
import	piBeaconGlobals as G
import math
G.program = "mlx90614"


#################################
def doDisplay():
	global displayInfo,sValues
	global output
	global initDisplay
	global tempUnits, pressureUnits, distanceUnits

	if "display" not in displayInfo: return

	if not displayInfo["display"]: return
	
	try:
		##print " to display:", dist, output
		if len(output) ==0: return
		if "display" not in output: return

		try:
			a=initDisplay  # this fails if fist time
		except:
			initDisplay=0 # start display.py if we come here after startup first time
			os.system("/usr/bin/python "+G.homeDir+"display.py	&" )
			time.sleep(0.2)

		if initDisplay > 300:
			os.system("/usr/bin/python "+G.homeDir+"display.py	&" )
			initDisplay =0
			time.sleep(0.2)
		initDisplay +=1

		
		if not U.pgmStillRunning("display.py"):
			os.system("/usr/bin/python "+G.homeDir+"display.py	&" )
			time.sleep(0.2)


		x0T = 0
		x1V = 0
		reduceFont =0.88
			
		for devid in output["display"]:
			ddd = output["display"][devid][0]
			if "devType" not in ddd:  continue
			devType		= ddd["devType"]
			displayResolution	  = ""
			try:
				if "displayResolution" in ddd:
					displayResolution	= ddd["displayResolution"].split("x")
					displayResolution	= [int(displayResolution[0]),int(displayResolution[1])]				   
			except:pass
			if "intensity"	in ddd: 
				intensity  = int(ddd["intensity"])

			displayWAIT				= "wait"
			scrollDelay				= 1
			scrollDelayBetweenPages = 1.
			scrollDelaySet			= 1.


			if "scrollSpeed"  in ddd:
				if	 ddd["scrollSpeed"] =="slow":
					scrollDelaySet =2.0
					scrollDelayBetweenPages =2.
				elif ddd["scrollSpeed"] =="fast":
					scrollDelayBetweenPages =0.5
					scrollDelaySet = 0.5

			scrollxy =""
			if "scrollxy"  in ddd: 
				scrollxy  = ddd["scrollxy"]
			if scrollxy not in ["up","down","left","right"]:
				scrollxy=""	   

			delayStart				=1
			if scrollxy =="": 
				delayStart			=1.2

			
			showDateTime ="1"
			if "showDateTime"  in ddd: 
				showDateTime  = ddd["showDateTime"]
				
				
			extraPageForDisplay=[]
			if "extraPageForDisplay"  in ddd: 
				extraPageForDisplay	 = ddd["extraPageForDisplay"]

			if os.path.isfile(G.homeDir+"temp/extraPageForDisplay.inp"):
				f = open(G.homeDir+"temp/extraPageForDisplay.inp","r")
				extraPageForDisplay=json.loads( f.read())
				f.close()
			
			font =""
			fwidth0 ="22"
			fwidth1 ="30"
			pos1= "[0,0]"	 
			intensity=100
			fillT =[]
			fill = [int(255*intensity/100),int(255*intensity/100),int(255*intensity/100)]
			fillCL =[200,200,200]
			if devType.find("RGBmatrix")>-1:
				scrollDelay =0.05
				fill0 = [0,0,0]
				fwidth0 ="0"
				fwidth1 ="0"

			if devType == "RGBmatrix16x16":
				ymax = 16
				xmax = 16
				fontUP	  ="5x8.pil"	
				fontDOWN  ="5x8.pil"	
				posy0= 0	
				posy1= 8	
				
			elif devType == "RGBmatrix32x16":
				ymax = 16
				xmax = 32
				fontUP	  ="5x8.pil"	
				fontDOWN  ="5x8.pil"	
				posy0= 0	
				posy1= 8	
				
			elif devType == "RGBmatrix32x32":
				ymax = 32
				xmax = 32
				fontUP	  ="5x8.pil"	
				fontDOWN  ="8x13.pil"	 
				posy0= 1	
				posy1= 16	 
				reduceFont =1
				
			elif devType == "RGBmatrix64x32":
				ymax = 32
				xmax = 64
				fontUP	  ="6x9.pil"	
				fontDOWN  ="9x18.pil"	 
				posy0= 1	
				posy1= 16	 
				
			elif devType == "RGBmatrix96x32":
				ymax = 32
				xmax = 96
				fontUP	  ="6x9.pil"	
				fontDOWN  ="9x18.pil"	 
				posy0= 1	
				posy1= 16	 
				clock ="[10,0,25,16]"
				fontCL ="9x18.pil"	  
				
			elif devType=="ssd1351":
				scrollDelay =0.05
				fill0 = [0,0,0]
				scrollDelay =0.015
				ymax = 128
				xmax = 128
				fontUP	  ="Arial.ttf"	  
				fontDOWN  ="Arial.ttf"	  
				fwidth0 ="26"
				fwidth1 ="48"
				posy0= 5	
				posy1= 60	 
				reduceFont = 0.91
				
			elif devType=="st7735":
				scrollDelay =0.015
				fill0 = [0,0,0]
				reset = fill0
				ymax = 128
				xmax = 160
				fontUP	  ="Arial.ttf"	  
				fontDOWN  ="Arial.ttf"	  
				fwidth0 ="36"
				fwidth1 ="60"
				posy0= 5	
				posy1= 60	 
				
			elif devType in ["ssd1306"]:
				scrollDelay =0.015
				ymax = 64
				xmax = 128
				fill = 255
				fillT=[255,255,255,255,255,255]
				fill0=0
				fontUP	  ="Arial.ttf"	  
				fontDOWN  ="Arial.ttf"	  
				fwidth0 ="14"
				fwidth1 ="30"
				posy0= 0	
				posy1= 30	 
				
			elif devType in ["sh1106"]:
				scrollDelay =0.015
				ymax = 64
				xmax = 128
				fill = 255
				fillT=[255,255,255,255]
				fill0=0
				fontUP	  ="Arial.ttf"	  
				fontDOWN  ="Arial.ttf"	  
				fwidth0 ="14"
				fwidth1 ="30"
				posy0= 0	
				posy1= 30	 
				
			elif devType.lower().find("screen") >-1:
				reduceFont	= 0.930
				scrollDelay = 0.015
				fill0		= [0,0,0]
				reset		= fill0
				fontUP		="Arial.ttf"	
				fontDOWN	="Arial.ttf"	
				ymax	= 480
				xmax	= 800
				fwidth0 = 150
				fwidth1 = 250
				x0T		= 10
				x1V		= 0
				posy0	= 0	   
				posy1	= 210	 
				if len( displayResolution ) ==2:
					try:
						ymax = displayResolution[1]
						xmax = displayResolution[0]
					except:
						pass
				try:	
					fwidth0 = int(fwidth0 *ymax / 500) 
					fwidth1 = int(fwidth1 *ymax / 500) 
					posy1	= int(ymax/2.) 
				except: pass	
##		  print xmax,ymax,posy1,fwidth1
		
		nPages=0
		posText0=[]
		posText1=[]
		outText0=[]
		outText1=[]




		if scrollxy !="":
			reset		= ""
		else:
			reset		= fill0
			displayWAIT ="immediate"
		if True:
			dx=0;dy=0
			if scrollxy in ["left","right"]:
				dx = xmax
				dy = 0
			elif scrollxy in ["up","down"]:
				dx = 0
				dy = ymax 

			if showDateTime =="1":
				nPages = 2	
			else:
				nPages = 0 
				
			# sValues = {"temp":[v1,v2,v3],"hum":[v1,v2,v3,v4],....}
			#print sValues
			if "temp" in sValues:
				theValues	= sValues["temp"][0]
				theText		= sValues["temp"][1]
				if len(theValues) >0:
					for	 ii in range(len(theValues)):
						t =	 float(theValues[ii])
						if tempUnits == u"Fahrenheit":
							t = t * 9. / 5. + 32.
							tu = " Temp[F]"
						elif tempUnits == u"Kelvin":
							t+= 273.15
							tu= " Temp[K]"
						else:
							tu= " Temp[C]"
						if theText[ii] !="":
							tu= theText[ii]
						t = "%5.1f" % t
						if devType not in ["sh1106","ssd1306"]:
							fillT+=[0,255,0]
						posText0.append([nPages*dx+x0T,nPages*dy+ posy0])
						posText1.append([nPages*dx+x1V,nPages*dy+ posy1])
						outText0.append(tu)
						outText1.append(t)
						nPages+=1
			if "ambient" in sValues:
				theValues	= sValues["ambient"][0]
				theText		= sValues["ambient"][1]
				if len(theValues) >0:
					for	 ii in range(len(theValues)):
						t =	 float(theValues[ii])
						if tempUnits == u"Fahrenheit":
							t = t * 9. / 5. + 32.
							tu = "A-Temp[F]"
						elif tempUnits == u"Kelvin":
							t+= 273.15
							tu= "A-Temp[K]"
						else:
							tu= "A-Temp[C]"
						if theText[ii] !="":
							tu= theText[ii]
						t = "%5.1f" % t
						if devType not in ["sh1106","ssd1306"]:
							fillT+=[0,0,255]
						posText0.append([nPages*dx+x0T,nPages*dy+ posy0])
						posText1.append([nPages*dx+x1V,nPages*dy+ posy1])
						if theText[ii] !="":
							outText0.append(theText[ii])
						outText1.append("	%2d"%float(t))
						nPages+=1

			if "hum" in sValues:
				theValues	= sValues["hum"][0]
				theText		= sValues["hum"][1]
				if len(theValues) >0:
					for	 ii in range(len(theValues)):
						h =	 float(theValues[ii])
						if devType not in ["sh1106","ssd1306"]:
							fillT +=[0,0,255]
						posText0.append([nPages*dx+x0T,nPages*dy+ posy0])
						posText1.append([nPages*dx+x1V,nPages*dy+ posy1])
						if theText[ii] !="":
							outText0.append(theText[ii])
						else:	 
							outText0.append("  Hum[%]")
						outText1.append("	%2d"%float(h))
						nPages+=1

			if "press" in sValues:
				theValues	= sValues["press"][0]
				theText		= sValues["press"][1]
				if len(theValues) >0:
					for	 ii in range(len(theValues)):
						p =	 float(theValues[ii])
						if pressureUnits == "atm":
							p *= 0.000009869233; p = "%6.3f"%p; pu= "P[atm]"
						elif pressureUnits == "bar":
							p *= 0.00001; p = "%7.4f" % p;		pu= "P[Bar]"
						elif pressureUnits.lower() == "mbar":
							p *= 0.01; p = "%6.1f" % p	 ;		pu= "P[mBar]"
						elif pressureUnits == "mm":
							p *= 0.00750063; p = "%6.1f"%p;		  pu= 'P[mmHg]'
						elif pressureUnits == "Torr":
							p *= 0.00750063; p = "%6.1f"%p;		  pu= "P[Torr]"
						elif pressureUnits == "inches":
							p *= 0.000295299802; p = "%6.2f"%p; pu= 'P["Hg]'
						elif pressureUnits == "PSI":
							p *= 0.000145038; pu = "%6.2f"%p;	pu= "P[PSI]"
						elif pressureUnits == "hPascal":
							p /= 100.; pu = "%6.2f"% p;			pu= "P[hPa]"
						else:
							p = "%9d" % p; pu = 'P[Pa]'
						p=p.strip(); pu=pu.strip()	  
						if devType not in ["sh1106","ssd1306"]:
							fillT.+=[255,0,0]
						posText0.append([nPages*dx+x0T,nPages*dy+ posy0])
						posText1.append([nPages*dx+x1V,nPages*dy+ posy1])
						if theText[ii] !="":
							outText0.append(theText[ii])
						else:	 
							outText0.append(pu)
						outText1.append(p)		  
						nPages+=1

			if "lux" in sValues:
				theValues	= sValues["lux"][0]
				theText		= sValues["lux"][1]
				logScale	= sValues["lux"][2]
				if len(theValues) >0:
					for	 ii in range(len(theValues)):
						lux =  theValues[ii]
						lux =  float(lux)
						if logScale[ii] =="1":
							l = ("%7.2f"%math.log10(max(1.,lux))).replace(" ","")
							lu	=  "[lux]-log"
						else:
							l = "%6d"%lux; lu = '[lux]'
						l=l.strip(); lu=lu.strip()	  
						if devType not in ["sh1106","ssd1306"]:
							fillT += [255,0,0]
						posText0.append([nPages*dx+x0T,nPages*dy+ posy0])
						posText1.append([nPages*dx+x1V,nPages*dy+ posy1])
						if theText[ii] !="":
							outText0.append(theText[ii])
						else:	 
							outText0.append(lu)
						outText1.append(l)		  
						nPages+=1

			##print extraPageForDisplay
			if extraPageForDisplay !=[] and extraPageForDisplay !="":
				for newPage in extraPageForDisplay:
					if newPage[0] =="" and newPage[1] =="": continue
					posText0.append([nPages*dx+x0T,nPages*dy+ posy0])
					posText1.append([nPages*dx+x1V,nPages*dy+ posy1])
					if newPage[0] !="":
						outText0.append(newPage[0])
					else:	 
						outText0.append("")
					if newPage[1] !="":
						outText1.append(newPage[1])
					else:	 
						outText1.append("")
					color =[255,255,255]   
					if newPage[2] !="":
						try: color = json.loads("["+newPage[2].strip("(").strip(")").strip("[").strip("]")+"]")
						except:pass
					fillT.append(color)
					nPages+=1
				

			if showDateTime =="1":
				 sensorPages = nPages -2
			else:
				sensorPages	 = nPages
				
			if scrollxy == "": nPages=1
			#if devType=="st7735": nPages = 1
			out={"resetInitial": "", "repeat": 999,"scrollxy":scrollxy,"scrollPages":str(nPages),"scrollDelayBetweenPages":str(scrollDelayBetweenPages),"scrollDelay":str(scrollDelay*scrollDelaySet)}
			
			out["command"]=[]
			if showDateTime =="1":
				out["command"].append({"type": "date","fill":str(fillCL),"delayStart":str(delayStart*scrollDelaySet),"display":displayWAIT,"reset":str(fill0)})
				out["command"].append({"type": "clock","fill":str(fillCL),"delayStart":str(delayStart*scrollDelaySet),"display":displayWAIT,"reset":str(reset)})
			else:
				out["command"].append({"type": "NOP","reset":str(fill0)})

			for ii in range(0,sensorPages):
				##if ii==0 :reset = fill0
				if scrollxy =="":reset = fill0
				else:	 reset = ""
				if ii==(sensorPages-1) or scrollxy =="":disp = "immediate"
				else:				   disp = "wait"
				next = outText0[ii]
				pos	 = posText0[ii]
				fwidthV = int(fwidth0)
				nred = len(next.strip()) - 8
				while nred > 0:
						fwidthV *=reduceFont
						nred -=1
				out["command"].append({"type": "text","fill":str(fillT[ii]),"reset":str(reset),"delayStart":str(delayStart*scrollDelaySet), "position":pos,"display":"wait","text":next,"font":fontUP,"width":str(int(fwidthV))})
				comma = ","
				next = outText1[ii]
				pos	 = posText1[ii]
				fwidthV = int(fwidth1)
				nred = len(next.strip()) - 4
				while nred > 0:
						fwidthV *=reduceFont
						nred -=1
				#print	"fwidthV,2",fwidthV ,fwidth1 ,nred ,next
				#print len(next.strip()), next , fwidth1, fwidthV
					
				out["command"].append({"type": "text","fill":str(fillT[ii]),"delayStart":str(delayStart*scrollDelaySet),"position":pos, "display":disp, "text":next,"font":fontDOWN,"width":str(int(fwidthV))})
		#print out
		try:
			f=open(G.homeDir+"temp/display.inp","a"); f.write(json.dumps(out)+"\n"); f.close()
		except:
			try:
				print "retry to write to display.inp"
				time.sleep(0.1)
				f=open(G.homeDir+"temp/display.inp","a"); f.write(json.dumps(out)+"\n"); f.close()
			except	Exception, e:
				print u"in Line {} has error={}".format(sys.exc_traceback.tb_lineno, e)
				if unicode(e).find("No space left on device") >-1:
					os.system("rm "+G.homeDir+"temp/* ")
		return 
	except	Exception, e:
		print u"in Line {} has error={}".format(sys.exc_traceback.tb_lineno, e)
		print sValues


# ===========================================================================
# utils II
# ===========================================================================

def putValText(sensorInfo,values,params):
	global sValues,displayInfo
	if not G.displayEnable: return	  
	llength= len(values)
	for ii in range(llength):
		sValues[params[ii]][0].append(values[ii])
		if "logScale" in sensorInfo:	
			sValues[params[ii]][2].append(sensorInfo["logScale"])
		else:
			sValues[params[ii]][2].append("0")

	if "displayText" in sensorInfo:
		splits = sensorInfo["displayText"].split(";")
		if len(splits)== llength:
			for ii in range(llength):
				sValues[params[ii]][1].append(splits[ii])
		else:	 
			for ii in range(llength):
				sValues[params[ii]][1].append("")
	else:	 
		for ii in range(llength):
			sValues[params[ii]][1].append("")

		
	displayInfo["display"]= True
			
	return 

def incrementBadSensor(devId,sensor,data):
	global badSensors
	try:
		if devId not in badSensors:badSensors[devId] =0
		badSensors[devId] +=1
		#print badSensors
		if	badSensors[devId]  > 2:
			if sensor not in data: data={sensor:{devId:{}}}
			if devId not in data[sensor]: data[sensor][devId]={}
			data[sensor][devId]["badSensor"]=True
			badSensors[devId] =0
	except	Exception, e:
		U.logger.log(30, u"in Line {} has error={}".format(sys.exc_traceback.tb_lineno, e))
	return data 



# ===========================================================================
# read params
# ===========================================================================

#################################		 
def readParams():
	global sensorList, sensors,	 sensor,  sensorRefreshSecs, displayEnable
	global output, sensorActive, timing
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
		  
		  
		if "sensors"			 in inp:  sensors =				  (inp["sensors"])
		if "output"				 in inp:  output=				  (inp["output"])
		if "tempUnits"			 in inp:  tempUnits=			  (inp["tempUnits"])

		if sensor not in sensors:
			U.logger.log(30, G.program+" is not in parameters = not enabled, stopping "+G.program )
			exit()
			
		sensorChanged = doWeNeedToStartSensor(sensors,sensorsOld,sensor)
			
		if sensorChanged == -1:
			U.logger.log(30, "==== stop	"+G.program+ " sensorChanged==-1 =====")
			exit()

		U.getGlobalParams(inp)



		for devId in sensors[sensor]:
			U.getMAGReadParameters(sensors[sensor][devId],devId)

		if sensorChanged != 0: # something has changed
			if os.path.isfile(G.homeDir+"temp/"+sensor+".dat"):
				os.remove(G.homeDir+"temp/"+sensor+".dat")
				
			

	except	Exception, e:
		U.logger.log(30, u"in Line {} has error={}".format(sys.exc_traceback.tb_lineno, e))




#################################
def doWeNeedToStartSensor(sensors,sensorsOld,selectedSensor):
	if selectedSensor not in sensors:	 return -1
	if selectedSensor not in sensorsOld: return 1

	for devId in sensors[selectedSensor] :
			if devId not in sensorsOld[selectedSensor] :			return 1
			for prop in sensors[sensor][devId] :
				if prop not in sensorsOld[selectedSensor][devId] :	return 1
				if sensors[selectedSensor][devId][prop] != sensorsOld[selectedSensor][devId][prop]:
					return 1
   
	for devId in sensorsOld[selectedSensor]:
			if devId not in sensors[selectedSensor] :				return 1
			for prop in sensorsOld[selectedSensor][devId] :
				if prop not in sensors[selectedSensor][devId] :		return 1

	return 0




# ===========================================================================
# MLX90614
# ===========================================================================

"""
MLX90614 driver. 
You might need to enter this command on your Raspberry Pi:
echo "Y" > /sys/module/i2c_bcm2708/parameters/combined
done now in this program when MLX sensor starts first
"""


class MLX90614:

	MLX90614_RAWIR1		= 0x04
	MLX90614_RAWIR2		= 0x05
	MLX90614_TA			= 0x06	# remote data temp
	MLX90614_TOBJ1		= 0x07	#  ambient data 
	MLX90614_TOBJ2		= 0x08

	MLX90614_TOMAX		= 0x20
	MLX90614_TOMIN		= 0x21
	MLX90614_PWMCTRL	= 0x22
	MLX90614_TARANGE	= 0x23
	MLX90614_EMISS		= 0x24
	MLX90614_CONFIG		= 0x25
	MLX90614_ADDR		= 0x0E
	MLX90614_ID1		= 0x3C
	MLX90614_ID2		= 0x3D
	MLX90614_ID3		= 0x3E
	MLX90614_ID4		= 0x3F


	def __init__(self, address=0x5a, bus_num=1):
		self.bus_num = bus_num
		self.address = address
		self.bus = smbus.SMBus(bus=bus_num)

	def test(self):
		print  "MLX90614_CONFIG", self.bus.read_word_data(self.address, self.MLX90614_CONFIG)
		print  "MLX90614_PWMCTRL",self.bus.read_word_data(self.address, self.MLX90614_PWMCTRL)
		print  "MLX90614_EMISS",  self.bus.read_word_data(self.address, self.MLX90614_EMISS)
		print  "MLX90614_TOMAX",  self.bus.read_word_data(self.address, self.MLX90614_TOMAX)
		print  "MLX90614_TOMIN",  self.bus.read_word_data(self.address, self.MLX90614_TOMIN)
		""" example read
		MLX90614_CONFIG 40884
		MLX90614_PWMCTRL 513
		MLX90614_EMISS 65535
		MLX90614_TOMAX 39315
		MLX90614_TOMIN 25315
		"""
		
		#print	= self.bus.read_word_data(self.address, MLX90614_RAWIR2)
		return 

	def get_amb_temp(self):
		data = self.bus.read_word_data(self.address, self.MLX90614_TA)
		return (data*0.02) - 273.15

	def get_obj_temp(self):
		data = self.bus.read_word_data(self.address, self.MLX90614_TOBJ1)
		return (data*0.02) - 273.15



	   

# ===========================================================================
# MLX90614
# ===========================================================================
def getMLX90614(sensor, data):
		global sensorMLX90614, MLX90614Started
		global sensors, sValues, displayInfo

		try:
			if sensor not in sensors: return data
			t=""
			a=""   
			try:
				ii= MLX90614Started
			except:	   
				MLX90614Started=1
				sensorMLX90614 ={}
				U.setStopCondition(on=True)

			for devId in sensors[sensor]:
				i2cAdd = U.muxTCA9548A(sensors[sensor][devId])

				if devId not in sensorMLX90614 :
					sensorMLX90614[devId]=MLX90614(address=i2cAdd)

				a = round(sensorMLX90614[devId].get_amb_temp(),1)
				t = round(sensorMLX90614[devId].get_obj_temp(),1)
				if t!="":
					try:	t = (float(t) + float(sensors[sensor][devId]["offsetTemp"]))
					except: continue
					data["sensors"][sensor][devId] = {"temp":t}

					if a!="":
						try:	a = float(a) + float(sensors[sensor][devId]["offsetTemp"])
						except: continue
						data["sensors"][sensor][devId]["AmbientTemperature"]=a


					if devId in badSensors: del badSensors[devId]
					putValText(sensors[sensor][devId],[t,a],["temp","ambient"])
				else:
					data= incrementBadSensor(devId,sensor,data)
		except	Exception, e:
			U.logger.log(30, u"in Line {} has error={}".format(sys.exc_traceback.tb_lineno, e))
		if sensor in data["sensors"] and data["sensors"][sensor]=={}: del data["sensors"][sensor]
		U.muxTCA9548Areset()
		return data
 




############################################
global	inpRaw
global sensor, sensors, first, badSensor, badSensors, sensorActive
global sensors, sValues, displayInfo
global sensorMLX90614, MLX90614Started
global oldRaw,	lastRead
oldRaw					= ""
lastRead				= 0
		

displayInfo					={}
first						= False
loopCount					= 0
sensorRefreshSecs			= 60
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
badSensors					= {}
sensorActive				= False
loopSleep					= 0.1
U.setLogging()

myPID		= str(os.getpid())
U.killOldPgm(myPID,G.program+".py")# kill old instances of myself if they are still running

if U.getIPNumber() > 0:
	time.sleep(10)
	exit()

# Create a VCNL4010/4000 instance.

readParams()

time.sleep(1)
lastRead = time.time()

U.echoLastAlive(G.program)

lastMsgBad			= 0
lastValue			= {}
lastData			= {}
lastSend			= 0
lastDisplay			= 0
lastRead			= time.time()
G.lastAliveSend		= time.time() -1000
lastLux	  = -999999
lastLux2  = 0
tt0 = time.time()
while True:
	try:
		tt = time.time()
		data={}
		data["sensors"]		= {}
		sValues={"temp":[[],[],[]],"ambient":[[],[],[]]}	  
		if sensor in sensors:
			retCode =""
			for devId in sensors[sensor]:
				data["sensors"][sensor] = {devId:{}}
				if devId not in lastValue: lastValue[devId] ={"temp":0,"AmbientTemperature":0}
				data =getMLX90614(sensor,data)
				if sensor not in data["sensors"]:
					if tt-lastMsgBad < 20: continue
					lastMsgBad = tt
					U.logger.log(30," bad sensor")
					data["sensors"]={sensor:{devId:{"temp":"badSensor"}}}
					U.sendURL(data)
					lastValue[devId] ={}
					continue
				if "temp" in  data["sensors"][sensor][devId]:
					if abs(data["sensors"][sensor][devId]["temp"] - lastValue[devId]["temp"])/max(0.1,data["sensors"][sensor][devId]["temp"] + lastValue[devId]["temp"])*2. > G.deltaX[devId]:
						 retCode = "sendNow" 
					#print retCode, G.deltaX[devId],data["sensors"][sensor][devId],	 lastValue[devId], abs(data["sensors"][sensor][devId]["temp"] - lastValue[devId]["temp"])/max(0.1,data["sensors"][sensor][devId]["temp"] + lastValue[devId]["temp"])*2.
					if (  (time.time() - G.lastAliveSend > abs(G.sensorRefreshSecs) or quick or retCode=="sendNow" )  and (time.time() - G.lastAliveSend > G.minSendDelta) ):
							#print	"sending", unicode(data)
							U.sendURL(data)
							lastValue  = copy.copy(data["sensors"][sensor])

		lastMsgBad = tt
		doDisplay()

		quick = False
		loopCount +=1
		
		U.makeDATfile(G.program, data)

		quick = U.checkNowFile(G.program)				 

		U.echoLastAlive(G.program)

		if loopCount %20 ==0 and not quick:
			if tt - lastRead > 5.:	
				readParams()
				lastRead = tt
		time.sleep(0.3)
		#print "end of loop", loopCount
	except	Exception, e:
		U.logger.log(30, u"in Line {} has error={}".format(sys.exc_traceback.tb_lineno, e))
		time.sleep(5.)
try: 	G.sendThread["run"] = False; time.sleep(1)
except: pass
sys.exit(0)
		
		
		
 