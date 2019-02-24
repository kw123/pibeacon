#!/usr/bin/env python
# -*- coding: utf-8 -*-
# by Karl Wachs
# feb 5 2016
# version 0.9 
##
###
#import RPi.GPIO as GPIO
import sys, os, time, json, datetime,subprocess,copy
import threading
import Queue

import smbus
from PIL import ImageFont, ImageDraw
import PIL
import	RPi.GPIO as GPIO  
GPIO.setmode(GPIO.BCM)
GPIO.setwarnings(False)


sys.path.append(os.getcwd())
import	piBeaconUtils	as U
import	piBeaconGlobals as G
G.program = "sunDial"



######### constants #################

ALLCHARACTERS = (		 "a","b","c","d","e","f","g","h","i","j","k","l","m","n","o","p","q","r","s","t","u","v","w","x","y","z",
				 "A","B","C","D","E","F","G","H","I","J","K","L","M","N","O","P","Q","R","S","T","U","V","W","X","Y","Z",
				 "1","2","3","4","5","6","7","8","9","0",
				 ".",",","/","=","-","!","@","#","$","%","^","&","*","_","+",":",";","<",">","(",")","[","]","{","}")
charCommands=[]
for ii in range(len(ALLCHARACTERS)):
	charCommands.append([ALLCHARACTERS[ii],"addChar('"+ALLCHARACTERS[ii]+"')"])

charCommands.append(["delete last Char", "deleteLastChar()"])
charCommands.append(["exit submenu", "doMenuUp()"] )

##               top option               selection, command
MENUSTRUCTURE =[[],[]]
MENUSTRUCTURE[0]=[	"power off",
					"light intensity",
					"left Right",
					"reset",
					"restart",
					"start Web for config",
					"WiFi SID",
					"WiFi Passwd",
				]
#                         menu text          ,  function to call   
MENUSTRUCTURE[1]=[	[	["confirm power off",	"powerOff()"],												["exit submenu", "doMenuUp()"] 	],
					[	["light up",   			"increaseLED()"],		["light down", "decreaseLED()"],	["exit submenu", "doMenuUp()"] 	], 
					[	["move left", 			"moveLeft()"], 			["move right", "moveRight()"],		["exit submenu", "doMenuUp()"] 	],
					[	["reset clock",  		"doReset()"], 												["exit submenu", "doMenuUp()"] 	],
					[	["restart system", 		"doReststart()"],											["exit submenu", "doMenuUp()"] 	], 
					[	["start Web",   		"startWeb()"], 			["stop Web",    "stopWeb()"], 		["exit submenu", "doMenuUp()"] 	],
						charCommands,				
						charCommands
				]
######### constants #################




# ########################################
# #########    display part          #####
# ########################################


#GPIO.setmode(GPIO.BCM)
#GPIO.setwarnings(False)

#!/usr/bin/env python

# The MIT License (MIT)
#
# Copyright (c) 2015 Richard Hull
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
# OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
# SOFTWARE.

class sh1106():

	def __init__(self, bus=None, port=1, address=0x3C, width=128, height=64):
		try:
			self.cmd_mode 			= 0x00
			self.data_mode 			= 0x40
			self.bus 				= smbus.SMBus(port)
			self.addr 				= address
			self.width 				= width
			self.height 			= height
			self.pages 				= int(self.height / 8)
			self.CHARGEPUMP			= 0x8D
			self.COLUMNADDR			= 0x21
			self.COMSCANDEC			= 0xC8
			self.COMSCANINC			= 0xC0
			self.DISPLAYALLON		= 0xA5
			self.DISPLAYALLON_RESUME = 0xA4
			self.DISPLAYOFF			= 0xAE
			self.DISPLAYON			= 0xAF
			self.EXTERNALVCC		= 0x1
			self.INVERTDISPLAY		= 0xA7
			self.MEMORYMODE			= 0x20
			self.NORMALDISPLAY		= 0xA6
			self.PAGEADDR			= 0x22
			self.SEGREMAP			= 0xA0
			self.SETCOMPINS			= 0xDA
			self.SETCONTRAST 		= 0x81
			self.SETDISPLAYCLOCKDIV = 0xD5
			self.SETDISPLAYOFFSET 	= 0xD3
			self.SETHIGHCOLUMN 		= 0x10
			self.SETLOWCOLUMN 		= 0x00
			self.SETMULTIPLEX 		= 0xA8
			self.SETPRECHARGE 		= 0xD9
			self.SETSEGMENTREMAP 	= 0xA1
			self.SETSTARTLINE 		= 0x40
			self.SETVCOMDETECT 		= 0xDB
			self.SWITCHCAPVCC 		= 0x2


			self.command(
				self.DISPLAYOFF,
				self.MEMORYMODE,
				self.SETHIGHCOLUMN,			0xB0, 0xC8,
				self.SETLOWCOLUMN,			0x10, 0x40,
				self.SETCONTRAST,			0x7F,
				self.SETSEGMENTREMAP,
				self.NORMALDISPLAY,
				self.SETMULTIPLEX,			0x3F,
				self.DISPLAYALLON_RESUME,
				self.SETDISPLAYOFFSET,   	0x00,
				self.SETDISPLAYCLOCKDIV, 	0xF0,
				self.SETPRECHARGE,			0x22,
				self.SETCOMPINS,			0x12,
				self.SETVCOMDETECT,			0x20,
				self.CHARGEPUMP,		 	0x14)

			self.clear()
			self.show()

		except IOError as e:
			raise IOError(e.errno, "Failed to initialize SH1106 display driver")

	def display(self, image):
		"""
		Takes a 1-bit image and dumps it to the SH1106 OLED display.
		"""
		assert(image.mode == '1')
		assert(image.size[0] == self.width)
		assert(image.size[1] == self.height)

		page = 0xB0
		pix = list(image.getdata())
		step = self.width * 8
		for y in range(0, self.pages * step, step):

			# move to given page, then reset the column address
			self.command(page, 0x02, 0x10)
			page += 1

			buf = []
			for x in range(self.width):
				byte = 0
				for n in range(0, step, self.width):
					byte |= (pix[x + y + n] & 0x01) << 8
					byte >>= 1

				buf.append(byte)

			self.data(buf)



	def command(self, *cmd):
		"""
		Sends a command or sequence of commands through to the
		device - maximum allowed is 32 bytes in one go.
		"""
		assert(len(cmd) <= 32)
		self.bus.write_i2c_block_data(self.addr, self.cmd_mode, list(cmd))

	def data(self, data):
		"""
		Sends a data byte or sequence of data bytes through to the
		device - maximum allowed in one transaction is 32 bytes, so if
		data is larger than this it is sent in chunks.
		"""
		for i in range(0, len(data), 32):
			self.bus.write_i2c_block_data(self.addr,
										  self.data_mode,
										  list(data[i:i+32]))

	def show(self):
		"""
		Sets the display mode ON, waking the device out of a prior
		low-power sleep mode.
		"""
		self.command(self.DISPLAYON)

	def hide(self):
		"""
		Switches the display mode OFF, putting the device in low-power
		sleep mode.
		"""
		self.command(self.DISPLAYOFF)

	def clear(self):
		"""
		Initializes the device memory with an empty (blank) image.
		"""
		self.display(PIL.Image.new('1', (self.width, self.height)))

# ------------------    ------------------ 
def startDisplay():
	global outputDev, displayFont
	global lineCoordinates3, lineCoordinates4, lastLines
	global xPixels, yPixels
	global displayPriority, waitForDisplayToRest
	global draw, imData
	global displayMenuLevelActive, displayMenuAreaActive, displayMenuSubAreaActive

	xPixels 				= 128
	yPixels 				= 64
	lineCoordinates3 		= [(0,0),(0,25),(4,50)]
	lineCoordinates4 		= [(0,0),(0,16),(0,32),(4,48)]
	lastLines 				= ["","","",""]

	outputDev				= sh1106(width=xPixels, height=yPixels)

	displayFont 			= ImageFont.load_default()
	imData					= PIL.Image.new('1', (xPixels,yPixels))
	draw 					= ImageDraw.Draw(imData)
	displayPriority    		= 0
	waitForDisplayToRest	= 60.
	displayMenuLevelActive	= -1
	displayMenuAreaActive	= -1
	displayMenuSubAreaActive= 0

# ------------------    ------------------ 
def setDisplayPriority(level=0):
	global displayPriority
	displayPriority = level

# ------------------    ------------------ 
def resetDisplayPriority():
	global displayPriority
	displayPriority = 0

# ------------------    ------------------ 
def reserveDisplayPriority():
	global displayPriority
	displayPriority = 5



# ------------------    ------------------ 
def drawDisplayLines( lines, nLines=3, clear=True, prio=0):
	global outputDev, displayFont
	global lineCoordinates3, lineCoordinates4, lastLines
	global xPixels, yPixels, imData, draw
	global displayPriority, waitForDisplayToRest


	if displayPriority > 0: 
		if time.time() - displayPriority > waitForDisplayToRest:
			displayPriority = 0
	
	if prio < displayPriority: return 
	displayPriority = prio 

	new = False
	for ii in range(len(lines)):
		if lines[ii] != lastLines[ii]:
			new=True
			break
	if not new: return 

	lastLines	= copy.copy(lines)
	if clear:
		clearDisplay()

	if nLines ==3:
		for ii in range(len(lines)):
			draw.text(lineCoordinates3[ii], lines[ii],  font=displayFont, fill=255)
	if nLines ==4:
		for ii in range(len(lines)):
			draw.text(lineCoordinates4[ii], lines[ii],  font=displayFont, fill=255)
	outputDev.display(imData)

	return 

# ------------------    ------------------ 
def drawDisplayLine( line, iLine=1, nLines=3, prio=0 ):
	global outputDev, displayFont
	global lineCoordinates3, lineCoordinates4, lastLines
	global xPixels, yPixels, imData, draw
	global displayPriority,waitForDisplayToRest

	if displayPriority > 0: 
		if time.time() - displayPriority > waitForDisplayToRest:
			displayPriority = 0
	
	if prio < displayPriority: return 
	displayPriority = prio 

	if nLines ==3:
		clearDisplay((0, lineCoordinates3[iLine[2]]+25, 128, lineCoordinates3[iLine[2]]+25 ) )
		draw.text(lineCoordinates3[iLine], line,  font=displayFont, fill=255)
	if nLines ==4:
		clearDisplay((0, lineCoordinates4[iLine[2]]+16, 128, lineCoordinates4[iLine[2]]+16 ) )
		draw.text(lineCoordinates4[iLine], line,  font=displayFont, fill=255)
	
	outputDev.display(imData)

	return 
# ------------------    ------------------ 
def drawDisplayLineOnOff( line, iLine=1, nLines=3, onOff ="off", prio=0):
	global outputDev, displayFont
	global lineCoordinates3, lineCoordinates4, lastLines
	global xPixels, yPixels, imData, draw
	global displayPriority, waitForDisplayToRest

	if displayPriority > 0: 
		if time.time() - displayPriority > waitForDisplayToRest:
			displayPriority = 0
	
	if prio < displayPriority: return 
	displayPriority = prio 

	
	if onOff !="off": line = "#"+line

	if nLines ==3:
		clearDisplay((0, lineCoordinates3[iLine[2]]+25, 128, lineCoordinates3[iLine[2]]+25 ) )
		draw.text(lineCoordinates3[iLine], line,  font=displayFont, fill=255)
	if nLines ==4:
		clearDisplay((0, lineCoordinates4[iLine[2]]+16, 128, lineCoordinates4[iLine[2]]+16 ) )
		draw.text(lineCoordinates4[iLine], line,  font=displayFont, fill=255)
	
	outputDev.display(imData)

	return 

#
# ------------------    ------------------ 
def clearDisplay( area=[], prio=0):
	global outputDev, displayFont
	global lineCoordinates, lastLines
	global xPixels, yPixels, imData, draw
	global displayPriority, waitForDisplayToRest

	if displayPriority > 0: 
		if time.time() - displayPriority > waitForDisplayToRest:
			displayPriority = 0
	
	if prio < displayPriority: return 
	displayPriority = prio 


	if area ==[]:
		draw.rectangle((0, 0, xPixels, yPixels), outline=0, fill=0)
		outputDev.display(imData)
	else:
		draw.rectangle(area, outline=0, fill=0)
		outputDev.display(imData)
		
# ------------------    ------------------ 
def composeMenu(useLevel, area,subArea,nLines):

	#print "composeMenu", useLevel, area,subArea,nLines
	lines=[]
	short = MENUSTRUCTURE[useLevel]
	if useLevel== 0:
		start = max(0, min(area, len(short) - nLines) )
		end   = min(area+nLines, len(short) )
		for ii in range(start, end):
			if ii == area:
#				lines.append(  str(area)+" "+str(level)+"  "+str(subarea)+" x "+str(MENUSTRUCTURE[level][ii])  )
				lines.append( "x "+str(short[ii])  )
			else:
				lines.append( "  "+str(short[ii])  )

	if useLevel == 1:
		short2 = short[area]
		if subArea < len(short2):
			start = max(0, min(subArea, len(short2) - nLines) )
			end   = min(subArea+nLines, len(short2) )
			#print start, end , short2
			for ii in range(start, end):
				if ii == subArea:
					lines.append( "x "+str(short2[ii][0]) )
				else:
					lines.append( "  "+str(short2[ii][0])  )
	return lines

# ########################################
# #########   button funtions ############
# ########################################
# ------------------    ------------------ 
def doAction(area,subArea):
	global displayMenuLevelActive
	print "doAction", displayMenuLevelActive, area, subArea

	if displayMenuLevelActive == 0:
		lines = composeMenu(0,area, subArea,4)
		drawDisplayLines( lines, nLines=4, clear=True, prio=time.time()+100)
		print lines

	elif displayMenuLevelActive == 1:
		eval(MENUSTRUCTURE[1][area][subArea][1]) 
		if displayMenuLevelActive==0:
			lines = composeMenu(1,area, subArea,4)
			drawDisplayLines( lines, nLines=4, clear=True, prio=time.time()+100)
			print lines

	elif displayMenuLevelActive < 0:
		displayMenuLevelActive =-1
	
	return 



# ------------------    ------------------ 
def buttonPressed(pin):
	global gpiopinSET, pinsToName
	global displayMenuLevelActive, displayMenuAreaActive, displayMenuSubAreaActive

	if pin not in pinsToName: 				return 
	if getPinValue(gpiopinSET[pin]) < 1: 	return 

	if gpiopinSET[pin] == "pin_Select": 
		displayMenuLevelActive += 1
		if displayMenuLevelActive  == 0:
			doAction(displayMenuAreaActive, displayMenuSubAreaActive)
		elif displayMenuLevelActive > 0:
			displayMenuLevelActive = 1
			doAction(displayMenuAreaActive, displayMenuSubAreaActive)
		else:
			return 	

	if gpiopinSET[pin] == "pin_Up":
		if displayMenuLevelActive == 0:
			displayMenuAreaActive += 1
			if displayMenuAreaActive > len(MENUSTRUCTURE[0]):
				displayMenuAreaActive = 0
			doAction(displayMenuAreaActive, displayMenuSubAreaActive)
		elif displayMenuLevelActive == 1:
			displayMenuSubAreaActive += 1
			if displayMenuSubAreaActive > len(MENUSTRUCTURE[1]):
				displayMenuSubAreaActive = 0
			doAction(displayMenuAreaActive, displayMenuSubAreaActive)
		else:
			return 	

	elif gpiopinSET[pin]=="pin_Dn": 
		if displayMenuLevelActive == 0:
			displayMenuAreaActive -= 1
			if displayMenuAreaActive < 0:
				displayMenuAreaActive = len(MENUSTRUCTURE[0])-1
			doAction(displayMenuAreaActive, displayMenuSubAreaActive)
		elif displayMenuLevelActive == 1:
			displayMenuSubAreaActive -= 1
			if displayMenuSubAreaActive < 0:
				displayMenuSubAreaActive = len(MENUSTRUCTURE[1])-1
			doAction(displayMenuAreaActive, displayMenuSubAreaActive)
		else:
			return 	

	elif gpiopinSET[pin]=="pin_Exit":
		displayMenuLevelActive -=1

		if displayMenuLevelActive < 0:
			displayPriority = 0
			displayMenuLevelActive = -1
		elif displayMenuLevelActive == 0:
				doAction(displayMenuAreaActive, displayMenuSubAreaActive)


# ------------------    ------------------ 
def powerOff():
	print " into powerOff" 
	doReboot(1.," shut down at " +str(datetime.datetime.now())+"   button pressed",cmd="shutdown -h now ")
	return 


# ------------------    ------------------ 
def increaseLED():
	global intensity
	print " into increaseLED" 
	nSteps =1
	while getPinValue("pin_Up") ==1:
			#print "pin_IntensityUp"
			nSteps = min(5, nSteps*1.5)
			intensity["Mult"] = max(10,intensity["Mult"]+nSteps)
			setColor( force = True)
			time.sleep(0.3)
	return 


# ------------------    ------------------ 
def decreaseLED():
	global intensity
	print " into decreaseLED" 
	nSteps =1
	while getPinValue("pin_Dn")==1:
			#print "pin_IntensityDn"
			nSteps = min(5, nSteps*1.5)
			intensity["Mult"] = max(5,intensity["Mult"]-nSteps)
			setColor( force = True)
			time.sleep(0.3)
	return 


# ------------------    ------------------ 
def startWeb():
	print " into startWeb" 
	if webAdhoc: return 
	pass
	webAdhoc = False


# ------------------    ------------------ 
def stopWeb():
	global webAdhoc
	print " into stopWeb" 
	if not webAdhoc: return 
	webAdhoc = False
	return 



# ------------------    ------------------ 
def doReststart():
	print " into doReststart" 
	time.sleep(1)	
 
	if getPinValue("pin_Select") ==1:
		print "restart requested"
		time.sleep(10)
		U.restartMyself(param=" restart requested", reason="",doPrint=True)
	return 

# ------------------    ------------------ 
def doReset():
	print " into doReset" 
	time.sleep(1)	
 
	if getPinValue("pin_Select") == 1:
		print "restart requested"
		time.sleep(10)
		U.restartMyself(param=" restart requested", reason="",doPrint=True)

# ------------------    ------------------ 
def moveRight():
	print " into moveRight"
	while getPinValue("pin_Up") == 1:
		move(0.05, 2, 1, force = 10)
	return 

# ------------------    ------------------ 
def moveLeft():
	print " into moveLeft"
	while getPinValue("pin_Dn") == 1:
		move(0.05, 2, -1, force = 10)
	return 

# ------------------    ------------------ 
def doMenuUp():
	global displayMenuLevelActive 
	global displayPriority

	displayMenuLevelActive -=1

	if displayMenuLevelActive < 0:
		displayPriority = 0
		displayMenuLevelActive =-1

	return 



# ########################################
# #########    read params           #####
# ########################################

# ------------------    ------------------ 
def readParams():
	global sensor, output, inpRaw, inp, useRTC
	global speed, amPM1224, motorType
	global lastCl, timeZone, currTZ
	global oldRaw, lastRead
	global doReadParameters
	global gpiopinSET
	global clockDictLast
	global colPWM, beepPWM
	global PIGPIO, pwmRange, pigpio
	global speedOverWrite
	global SeqCoils
	global buttonDict, sensorDict
	global pinsToName

	try:

		changed =0
		inpLast= inp
		inp,inpRaw,lastRead2 = U.doRead(lastTimeStamp=lastRead)


		if inp == "": 
			inp = inpLast
			return changed
			
		if lastRead2 == lastRead: return changed
		lastRead  = lastRead2
		if inpRaw == oldRaw: return changed
		oldRaw	   = inpRaw
		U.getGlobalParams(inp)
		 


		if "debugRPI"				in inp:	 G.debug=		  				int(inp["debugRPI"]["debugRPIOUTPUT"])
		if "useRTC"					in inp:	 useRTC=					       (inp["useRTC"])
		if "pin_webAdhoc"		    in inp:  gpiopinSET["pin_webAdhoc"]	= 	int(inp["pin_webAdhoc"])
		if "output"					in inp:	 output=			 			   (inp["output"])
		#### G.debug = 2 
		if G.program not in output:
			U.toLog(-1, G.program+ " is not in parameters = not enabled, stopping "+ G.program+".py" )
			exit()
		clockLightSensor =0
		if "clockLightSensor"			in inp: 
			try:	xx = float(inp["clockLightSensor"])
			except: xx = 0
			clockLightSensor =xx


		clock = output[G.program]
		for devId in  clock:
			clockDict		= clock[devId][0]
			if clockDictLast == clockDict: continue
			clockDictLast 	= clockDict


			print clockDict
			if "timeZone"			 in clockDict:	
				if timeZone !=			   (clockDict["timeZone"]):
					changed = max(2, changed)  
					timeZone =				   (clockDict["timeZone"])
					tznew  = int(timeZone.split(" ")[0])
					if tznew != currTZ:
						U.toLog(-1, u"changing timezone from "+str(currTZ)+"  "+timeZones[currTZ+12]+" to "+str(tznew)+"  "+timeZones[tznew+12])
						os.system("sudo cp /usr/share/zoneinfo/"+timeZones[tznew+12]+" /etc/localtime")
						currTZ = tznew

			clockDict["timeZone"] = str(currTZ)+" "+ timeZones[currTZ+12]
				
			if "intensityMult"		in clockDict:  intensity["Mult"]				=	float(clockDict["intensityMult"])
			if "intensityMax"		in clockDict:  intensity["Max"]					=	float(clockDict["intensityMax"])
			if "intensityMin"		in clockDict:  intensity["Min"]					=	float(clockDict["intensityMin"])
			if "speed"			 	in clockDict:  speed		   					=	float(clockDict["speed"])
			if speedOverWrite >-1: speed = speedOverWrite
			if "motorType"		 	in clockDict:  motorType				 		=	    (clockDict["motorType"])

			if "pin_CoilA1"			in clockDict: gpiopinSET["pin_CoilA1"]			=	int(clockDict["pin_CoilA1"])
			if "pin_CoilA2"			in clockDict: gpiopinSET["pin_CoilA2"]			=	int(clockDict["pin_CoilA2"])
			if "pin_CoilB1"			in clockDict: gpiopinSET["pin_CoilB1"]			=	int(clockDict["pin_CoilB1"])
			if "pin_CoilB2"			in clockDict: gpiopinSET["pin_CoilB2"]			=	int(clockDict["pin_CoilB2"])

			if "pin_Step"			in clockDict: gpiopinSET["pin_Step"]			=	int(clockDict["pin_Step"])
			if "pin_Dir"			in clockDict: gpiopinSET["pin_Dir"]				=	int(clockDict["pin_Dir"])
			if "pin_Sleep"			in clockDict: gpiopinSET["pin_Sleep"]			=	int(clockDict["pin_Sleep"])

			if "pin_beep"			in clockDict: gpiopinSET["pin_beep"]			=	int(clockDict["pin_beep"])
			if "pin_rgbLED_R"		in clockDict: gpiopinSET["pin_rgbLED"][0]		=	int(clockDict["pin_rgbLED_R"])
			if "pin_rgbLED_G"		in clockDict: gpiopinSET["pin_rgbLED"][1]		=	int(clockDict["pin_rgbLED_G"])
			if "pin_rgbLED_B"		in clockDict: gpiopinSET["pin_rgbLED"][2]		=	int(clockDict["pin_rgbLED_B"])

			if "pin_sensor0"		in clockDict: gpiopinSET["pin_sensor0"]			=	int(clockDict["pin_sensor0"])
			if "pin_sensor1"		in clockDict: gpiopinSET["pin_sensor1"]			=	int(clockDict["pin_sensor1"])
			if "pin_sensor2"		in clockDict: gpiopinSET["pin_sensor2"]			=	int(clockDict["pin_sensor2"])
			if "pin_sensor3"		in clockDict: gpiopinSET["pin_sensor3"]			=	int(clockDict["pin_sensor3"])


			if "pin_Up"				in clockDict: gpiopinSET["pin_Up"]				=	int(clockDict["pin_Up"])
			if "pin_Dn"				in clockDict: gpiopinSET["pin_Dn"]				=	int(clockDict["pin_Dn"])
			if "pin_Select"			in clockDict: gpiopinSET["pin_Select"]			=	int(clockDict["pin_Select"])
			if "pin_Exit"			in clockDict: gpiopinSET["pin_Exit"]			=	int(clockDict["pin_Exit"])



			
			sensorDict["sensor"] = []
			sensorDict["sensor"].append({"lastCeck":0, "lastValue":-1,"newValue":-1, "left":[-1,-1,-1,-1,-1,-1,-1,-1,-1], "right":[-1,-1,-1,-1,-1,-1,-1,-1,-1], "status":-1}) 
			sensorDict["sensor"].append({"lastCeck":0, "lastValue":-1,"newValue":-1, "left":[-1,-1,-1,-1,-1,-1,-1,-1,-1], "right":[-1,-1,-1,-1,-1,-1,-1,-1,-1], "status":-1}) 
			sensorDict["sensor"].append({"lastCeck":0, "lastValue":-1,"newValue":-1, "left":[-1,-1,-1,-1,-1,-1,-1,-1,-1], "right":[-1,-1,-1,-1,-1,-1,-1,-1,-1], "status":-1}) 
			sensorDict["sensor"].append({"lastCeck":0, "lastValue":-1,"newValue":-1, "left":[-1,-1,-1,-1,-1,-1,-1,-1,-1], "right":[-1,-1,-1,-1,-1,-1,-1,-1,-1], "status":-1}) 
			sensorDict["sequence"]				= [0,1,1,1,1,0,0,0,0] # sensors firing when turning right in parts of 360/8: (0,1,2,3,4,5,6,7,8=360 )
																		  # 4 magents every 1/8 of 360, 2 reed sensor at 0(#0-sensor0) and 180(#1=sensor1)
			sensorDict["currentSeqNumber"]		= -1 #  0,1,2,3,4,5,6,7,8
			sensorDict["currentSeqDirection"]	= 0  # -1,+1


			for key in gpiopinSET:
				if key in [ "pin_Up", "pin_Dn", "pin_Select", "pin_Exit"]:
					buttonDict[key] = {"lastCeck":0, "lastValue":-1,"newValue":-1}


			print "sensorDict", sensorDict
			print "buttonDict", buttonDict

			pwm = 0
			if PIGPIO == "":
				import pigpio
				PIGPIO = pigpio.pi()
				pwmRange = 1000
			if not U.pgmStillRunning("pigpiod"): 	
				U.toLog(-1, "starting pigpiod", doPrint=True)
				os.system("sudo pigpiod -s 1 &")
				time.sleep(0.5)
				if not U.pgmStillRunning("pigpiod"): 	
					U.toLog(-1, " restarting myself as pigpiod not running, need to wait for timeout to release port 8888", doPrint=True)
					time.sleep(20)
					U.restartMyself(reason="pigpiod not running")
					exit(0)

			MT  =  motorType.split("-")

			if motorType.find("unipolar") >-1 or motorType.find("bipolar") >-1:
				defineGPIOout(gpiopinSET["pin_CoilA1"],pwm=pwm, freq=40000)
				defineGPIOout(gpiopinSET["pin_CoilA2"],pwm=pwm, freq=40000)
				defineGPIOout(gpiopinSET["pin_CoilB1"],pwm=pwm, freq=40000)
				defineGPIOout(gpiopinSET["pin_CoilB2"],pwm=pwm, freq=40000)

			elif motorType.find("DRV8834") >-1 :
				defineGPIOout(gpiopinSET["pin_Step"])
				defineGPIOout(gpiopinSET["pin_Dir"])
				defineGPIOout(gpiopinSET["pin_Sleep"])
				defineGPIOin("pin_Fault")
			elif motorType.find("A4988") >-1:
				defineGPIOout(gpiopinSET["pin_Step"])
				defineGPIOout(gpiopinSET["pin_Dir"])
				defineGPIOout(gpiopinSET["pin_Sleep"])
							

			defineGPIOout(gpiopinSET["pin_rgbLED"][0], pwm=1,pig=True)
			defineGPIOout(gpiopinSET["pin_rgbLED"][1], pwm=1,pig=True)
			defineGPIOout(gpiopinSET["pin_rgbLED"][2], pwm=1,pig=True)

			defineGPIOout(gpiopinSET["pin_beep"],      pwm=1)


			defineGPIOin("pin_Up")
			defineGPIOin("pin_Dn")
			defineGPIOin("pin_Select")
			defineGPIOin("pin_Exit")
			pinsToName[gpiopinSET["pin_Up"]]		= "pin_Up"
			pinsToName[gpiopinSET["pin_Dn"]]		= "pin_Dn"
			pinsToName[gpiopinSET["pin_Select"]]	= "pin_Select"
			pinsToName[gpiopinSET["pin_Exit"]]		= "pin_Exit"


			defineGPIOin("pin_sensor0")
			defineGPIOin("pin_sensor1")
			defineGPIOin("pin_sensor2")
			defineGPIOin("pin_sensor3")


			defineMotorType()

			## print clockDict
			break
		return changed

	except	Exception, e:
		print  u"in Line '%s' has error='%s'" % (sys.exc_traceback.tb_lineno, e)
		U.toLog(-1, u"in Line '%s' has error='%s'" % (sys.exc_traceback.tb_lineno, e))
		time.sleep(10)
		return 3

# ########################################
# #########    basic setup funtions  #####
# ########################################
# ------------------    ------------------ 
def setupTimeZones():
	global timeZone, timeZones, currTZ
	timeZone = ""
	timeZones =[]
	for ii in range(-12,13):
		if ii<0:
			timeZones.append("/Etc/GMT+" +str(abs(ii)))
		else:
			timeZones.append("/Etc/GMT-"+str(ii))
		
	timeZones[12+12]  = "Pacific/Auckland"
	timeZones[11+12]  = "Pacific/Pohnpei"
	timeZones[10+12]  = "Australia/Melbourne"
	timeZones[9+12]	  = "Asia/Tokyo"
	timeZones[8+12]	  = "Asia/Shanghai"
	timeZones[7+12]	  = "Asia/Saigon"
	timeZones[6+12]	  = "Asia/Dacca"
	timeZones[5+12]	  = "Asia/Karachi"
	timeZones[4+12]	  = "Asia/Dubai"
	timeZones[3+12]	  = "/Europe/Moscow"
	timeZones[2+12]	  = "/Europe/Helsinki"
	timeZones[1+12]	  = "/Europe/Berlin"
	timeZones[0+12]	  = "/Europe/London"
	timeZones[-1+12]  = "Atlantic/Cape_Verde"
	timeZones[-2+12]  = "Atlantic/South_Georgia"
	timeZones[-3+12]  = "America/Buenos_Aires"
	timeZones[-4+12]  = "America/Puerto_Rico"
	timeZones[-5+12]  = "/US/Eastern"
	timeZones[-6+12]  = "/US/Central"
	timeZones[-7+12]  = "/US/Mountain"
	timeZones[-8+12]  = "/US/Pacific"
	timeZones[-9+12]  = "/US/Alaska"
	timeZones[-10+12] = "Pacific/Honolulu"
	timeZones[-11+12] = "US/Samoa"
	#print "timeZones:", timeZones

	#delta to UTC:
	JulDelta = int(subprocess.Popen("date -d '1 Jul' +%z " ,shell=True,stdout=subprocess.PIPE,stderr=subprocess.PIPE).communicate()[0].strip("\n").strip())/100
	JanDelta = int(subprocess.Popen("date -d '1 Jan' +%z " ,shell=True,stdout=subprocess.PIPE,stderr=subprocess.PIPE).communicate()[0].strip("\n").strip())/100
	NowDelta = int(subprocess.Popen("date  +%z "		   ,shell=True,stdout=subprocess.PIPE,stderr=subprocess.PIPE).communicate()[0].strip("\n").strip())/100

	currTZ = JanDelta
	return 


# ------------------    ------------------ 
def defineMotorType():
	global SeqCoils, minStayOn, motorType, stepsIn360, maxStepsUsed, nStepsInSequence
	SeqCoils = []

	try:
		mtSplit    		= motorType.split("-")
		mult 		    = int(mtSplit[2])
		stepsIn360 		= int(mtSplit[1])*mult
		maxStepsUsed	= stepsIn360 -1
	except:
		print " stopping  motorType wrong", motorType, mtSplit
		exit()

	if mtSplit[0] == "bipolar":
		minStayOn = 0.001
		if motorType.find("-1") >-1:
			SeqCoils.append([0, 0, 0, 0])  # off
			SeqCoils.append([0, 1, 1, 0])
			SeqCoils.append([0, 1, 0, 1])
			SeqCoils.append([1, 0, 0, 1])
			SeqCoils.append([1, 0, 1, 0])
		elif motorType.find("-2") >-1:
			print "morotype = ", motorType
			SeqCoils.append([0, 0, 0, 0])  # off

			SeqCoils.append([0, 1, 1, 0])
			SeqCoils.append([0, 1, 0, 0])
			SeqCoils.append([0, 1, 0, 1])
			SeqCoils.append([0, 0, 0, 1])
			SeqCoils.append([1, 0, 0, 1])
			SeqCoils.append([1, 0, 0, 0])
			SeqCoils.append([1, 0, 1, 0])
			SeqCoils.append([0, 0, 1, 0])
			"""
			SeqCoils.append([0, 0, 1, 0])
			SeqCoils.append([1, 0, 1, 0])
			SeqCoils.append([1, 0, 0, 0])
			SeqCoils.append([1, 0, 0, 1])
			SeqCoils.append([0, 0, 0, 1])
			SeqCoils.append([0, 1, 0, 1])
			SeqCoils.append([0, 1, 0, 0])
			SeqCoils.append([0, 1, 1, 0])
			"""


	elif mtSplit[0] == "unipolar":
		SeqCoils.append([0, 0, 0, 0]) # off
		SeqCoils.append([1, 0, 0, 1])
		SeqCoils.append([1, 0, 0, 0])
		SeqCoils.append([1, 1, 0, 0])
		SeqCoils.append([0, 1, 0, 0])
		SeqCoils.append([0, 1, 1, 0])
		SeqCoils.append([0, 0, 1, 0])
		SeqCoils.append([0, 0, 1, 1])
		SeqCoils.append([0, 0, 0, 1])
		minStayOn = 0.001
		maxStepsUsed	= stepsIn360 -10

	elif mtSplit[0] =="DRV8834" or mtSplit[0] == "A4988":
		minStayOn = 0.001

	else:
		print " stopping  motorType not defined"
		exit()

	nStepsInSequence= len(SeqCoils) -1
	print nStepsInSequence, SeqCoils
	return 

# ------------------    ------------------ 
def setgpiopinSET():
	global gpiopinSET
	### GPIO pins ########
	gpiopinSET						= {}
	gpiopinSET["pin_CoilA1"]      	= -1 # blue
	gpiopinSET["pin_CoilA2"]      	= -1 # pink
	gpiopinSET["pin_CoilB1"]      	= -1 # yellow
	gpiopinSET["pin_CoilB2"]      	= -1 # orange

	gpiopinSET["pin_Fault"]      	= -1 # orange
	gpiopinSET["pin_Dir"]      		= -1 # orange
	gpiopinSET["pin_Step"]      	= -1 # orange
	gpiopinSET["pin_Sleep"]      	= -1 # orange
	gpiopinSET["pin_Enable"]    	= -1 # orange
	gpiopinSET["pin_Reset"] 		= -1


	gpiopinSET["pin_rgbLED"]	 	= [-1,-1,-1] # r g b pins

	gpiopinSET["pin_Up"]   			= -1
	gpiopinSET["pin_Dn"]  			= -1

	gpiopinSET["pin_Select"]		= -1
	gpiopinSET["pin_Exit"]			= -1

	gpiopinSET["pin_sensor0"]  		= -1
	gpiopinSET["pin_sensor1"] 		= -1
	gpiopinSET["pin_sensor2"]  		= -1
	gpiopinSET["pin_sensor3"] 		= -1


	return 


# ########################################
# #########    masic GPIO funtions  ######
# ########################################

# ------------------    ------------------ 
def defineGPIOin(pinName, event= False):
	global PIGPIO, pigpio
	pin = gpiopinSET[pinName]
	if pin <=1: return 
	try:
		if PIGPIO !="":
			PIGPIO.set_mode( pin,  pigpio.INPUT )
			PIGPIO.set_pull_up_down( pin, pigpio.PUD_UP)
			if event:
				PIGPIO.set_glitch_filter(pin, 30000) # steady for 30 msec 
				PIGPIO.callback(pin, pigpio.FALLING_EDGE, buttonPressed )	
		else:
			try:    
				GPIO.setup( pin, GPIO.IN, pull_up_down=GPIO.PUD_UP)
			except	Exception, e:
				U.toLog(-1, u"in Line '%s' has error='%s'" % (sys.exc_traceback.tb_lineno, e), doPrint=True)
	except	Exception, e:
		U.toLog(-1, u"in Line '%s' has error='%s'" % (sys.exc_traceback.tb_lineno, e), doPrint=True)
	return

# ------------------    ------------------ 
def defineGPIOout(pin, pwm = 0,freq =1000, pig=False):
	global PIGPIO, pigpio, pwmRange, colPWM
	print "defineGPIOout", pin, pwm, freq, pig
	if PIGPIO !="" :
		PIGPIO.set_mode( pin, pigpio.OUTPUT )
		if pwm !=0:
			PIGPIO.set_PWM_frequency( pin, pwmRange )
			PIGPIO.set_PWM_range( pin, pwmRange )
			PIGPIO.set_PWM_dutycycle( pin, 0 )
			print ("frequency: "+ unicode(PIGPIO.get_PWM_frequency(pin)))
	else:
		try:   
			GPIO.setup( pin,	GPIO.OUT)
			if pwm !=0:
				colPWM[pin] = GPIO.PWM(pin, 100)
		except: pass
	return




# ------------------    ------------------ 
def setGPIOValue(pin,val,amplitude =-1, pig=False):
	global PIGPIO, pwmRange
	pin = int(pin)
	if PIGPIO !="":
		if amplitude == -1:
			PIGPIO.write( (pin), val )
		else:
			if amplitude >0 and val !=0:
				PIGPIO.set_PWM_dutycycle( (pin), int(pwmRange*amplitude/100.) )
				#print "setGPIOValue ", pin, val,amplitude, int(pwmRange*amplitude/100.), PIGPIO.get_PWM_dutycycle(int(pin)) 
			else:
				PIGPIO.write( (pin), 0 )
				#PIGPIO.set_PWM_dutycycle( int(pin), 0)
	else:
		if amplitude == -1:
			GPIO.output( (pin), int(val) )
		else:
			colPWM[pin].start( amplitude )	
	return

# ------------------    ------------------ 
def getPinValue(pinName,pin=-1):
	global gpiopinSET, PIGPIO

	if pin ==-1:
		if pinName not in gpiopinSET: return -1
		if gpiopinSET[pinName] < 1:   return -1
		pin = gpiopinSET[pinName]

	if PIGPIO =="":
		ret =  GPIO.input(pin)
		#print "reading pin", pinName, ret 
	else:
		ret = PIGPIO.read(pin)

	return (ret-1)*-1


# ########################################
# #########  moving functions ############
# ########################################
 
# ------------------    ------------------ 
def makeStep(seq, amplitude=-1):
	global gpiopinSET
	global SeqCoils
	#print "makeStep", seq, SeqCoils[seq], amplitude
	count = sum(SeqCoils[seq])
	a = amplitude
	#if count > 1 and amplitude ==99:
	#	a *= 0.6
	setGPIOValue(gpiopinSET["pin_CoilA1"], SeqCoils[seq][0], int(a))
	setGPIOValue(gpiopinSET["pin_CoilA2"], SeqCoils[seq][1], int(a))
	setGPIOValue(gpiopinSET["pin_CoilB1"], SeqCoils[seq][2], int(a))
	setGPIOValue(gpiopinSET["pin_CoilB2"], SeqCoils[seq][3], int(a))


def makeStepDRV8834(dir):
	global gpiopinSET
	global lastDirection
	global isDisabled
	global isSleep


	if isDisabled or isSleep: 
		setMotorON()
		time.sleep(0.01)

	if dir != lastDirection: 
		setGPIOValue(gpiopinSET["pin_Dir"], dir==1)
		lastDirection = dir
		time.sleep(0.1)

	setGPIOValue(gpiopinSET["pin_Step"], 1)
	time.sleep(0.0001)
	setGPIOValue(gpiopinSET["pin_Step"], 0)
	time.sleep(0.0001)


# ------------------    ------------------ 
def setMotorON():
	global motorType, isDisabled, isSleep
	if motorType.find("DRV8834") >-1 or motorType.find("A4988") >-1 :
		setGPIOValue(gpiopinSET["pin_Sleep"], 1)
		setGPIOValue(gpiopinSET["pin_Enable"], 0)
	else:
		pass
	isSleep 	= False
	isDisabled  = False

def setMotorOFF():
	global motorType, isDisabled, isSleep
	if motorType.find("DRV8834") >-1 or motorType.find("A4988") >-1 :
		setGPIOValue(gpiopinSET["pin_Sleep"], 0)
		setGPIOValue(gpiopinSET["pin_Enable"], 1)
	else:
		pass#makeStep(0)
	isSleep 	= True
	isDisabled  = True

def setMotorSleep():
	global motorType, isDisabled, isSleep
	if motorType.find("DRV8834") >-1 or motorType.find("A4988") >-1 :
		setGPIOValue(gpiopinSET["pin_Sleep"], 0)
	else:
		pass#makeStep(0)
	isSleep = True

 
# ------------------    ------------------ 
def move(stayOn, steps, direction, force = 0, stopIf=[False,False],  updateSequence=False):
	global lastStep
	global gpiopinSET
	global SeqCoils
	global nStepsInSequence
	global whereIs12
	global minStayOn
	global motorType
	global PIGPIO
	global currentSequenceNo
	global totalSteps


	stayOn = max(minStayOn,stayOn)
	lStep = lastStep
	#print "steps", steps,  direction, stayOn, lastStep
	steps = int(steps)
	iSteps= 0

	getSensors()
	last1 = sensorDict["sensor"][1]["status"]
	last0 = sensorDict["sensor"][0]["status"]
	for i in range(steps):

		getSensors()
		if updateSequence: 
			 determineSequenceNo(totalSteps+iSteps)

		if not updateSequence or ( currentSequenceNo < 8 and sensorDict["sensor"][0] == 1 ):
			if i >= force: 
				if last0 != sensorDict["sensor"][0]["status"] and sensorDict["sensor"][0]["status"] == 1 and stopIf[0]: 
					getSensors()
					return iSteps
				if last1 != sensorDict["sensor"][1]["status"] and sensorDict["sensor"][1]["status"] == 1 and stopIf[1]: 
					getSensors()
					return iSteps

		if currentSequenceNo == 8 and sensorDict["sensor"][0] == 1:
			if i >= force: 
				if last0 != sensorDict["sensor"][0]["status"] and sensorDict["sensor"][0]["status"] == 1 and stopIf[0]: 
					getSensors()
					return iSteps
				if last1 != sensorDict["sensor"][1]["status"] and sensorDict["sensor"][1]["status"] == 1 and stopIf[1]: 
					getSensors()
					return iSteps

		last1 = sensorDict["sensor"][1]["status"]
		last0 = sensorDict["sensor"][0]["status"]


		iSteps += 1
		lStep += direction

		if motorType.find("DRV8834") >-1:
			makeStepDRV8834(direction)
		else:
			if   lStep >= len(SeqCoils):	lStep = 1
			elif lStep <  1: 				lStep = len(SeqCoils)-1

			if PIGPIO != "" and False:
				if steps > 1:
					pass # print "makeStep lstep", steps, iSteps, lStep, lastStep
				makeStep(lStep, amplitude=100)
				if steps == 1:
					time.sleep(0.1)
					makeStep(lStep, amplitude=99)
			else:
				makeStep(lStep)
				time.sleep(0.01)

	 	lastStep = lStep
		time.sleep(stayOn)
	getSensors()
	#if speed < 100 or stayOn > 0.5: setOFF()
	return iSteps

# ------------------    ------------------ 
def testIfMove( waitBetweenSteps, nextStep ):
	global maxStepsUsed, startSteps
	global speed
	global t0
	global printON
	global totalSteps
	global hour, minute, second
	global secSinMidnit, hour12, secSinMidnit2	
	global rewindDone
	global PIGPIO
	global currentSequenceNo, inbetweenSequences

	drawDisplayLines(["status","@ Pos.: %d/%d"%(nextStep,maxStepsUsed), datetime.datetime.now().strftime("%a, %Y-%m-%d %H:%M")])
	lasttotalSteps = totalSteps
	nextTotalSteps 	= min( int( secSinMidnit2 / waitBetweenSteps), maxStepsUsed )
	if nextTotalSteps != totalSteps:
		nextStep    = nextTotalSteps - totalSteps 

		if nextStep <0:	dir = -1
		else:			dir =  1

		if printON: print "secSinMidnit 2 ", "%.2f"%secSinMidnit, "H",hour, "M",minute, "S",second, "dt %.5f"%(time.time()-t0), "nstep",nextStep, "totSteps",totalSteps,"currentSequenceNo", currentSequenceNo,"inbetweenSequences", inbetweenSequences

		if nextStep != 0: 
			if speed > 10 or nextStep >5: stayOn =0.001
			else:		                  stayOn =0.1
			if lasttotalSteps < 10: force = 10 
			else:					force = 0
			#print "dir, nextStep", dir, nextStep
			if currentSequenceNo < 7: force = 750
			steps = move(stayOn, int( abs(nextStep) ), dir, force = force, updateSequence=True)
			if currentSequenceNo == 8 and sensorDict["sensor"][0]["status"] == 1:
				nextStep =0
			
			if speed == 1 and nextStep ==1 and PIGPIO == "":
				setMotorSleep()
			setColor()

		totalSteps += nextStep
		drawDisplayLines(["status","@ Pos.: %d/%d"%(totalSteps,maxStepsUsed), datetime.datetime.now().strftime("%a, %Y-%m-%d %H:%M")])

		#saveTime(secSinMidnit)
		rewindDone = True
		t0=time.time()
	return   nextStep


# ------------------    ------------------ 
def determineSequenceNo(lSteps):
	global currentSequenceNo, inbetweenSequences

	#print "into  determineSequenceNo.. inbetweenSequences:",inbetweenSequences, "lSteps",lSteps
	if lSteps < 15: 
		currentSequenceNo = 0
		inbetweenSequences    = False
		return 
	if inbetweenSequences:
		if sensorDict["sensor"][0]["status"] == 1 or  sensorDict["sensor"][1]["status"] == 1:
			currentSequenceNo +=1
			inbetweenSequences = False
			#print "updating currentSequenceNo", currentSequenceNo,"inbetweenSequences",inbetweenSequences, "lSteps",lSteps
	if     sensorDict["sensor"][0]["status"] == 0 and sensorDict["sensor"][1]["status"] == 0:
			#print "updating currentSequenceNo", currentSequenceNo,"inbetweenSequences",inbetweenSequences, "lSteps",lSteps
			inbetweenSequences = True
						
	
		

# ------------------    ------------------ 
def testIfRewind( nextStep ):
	global maxStepsUsed, startSteps
	global t0
	global printON
	global totalSteps
	global hour, minute, second
	global secSinMidnit, hour12, secSinMidnit2	
	global rewindDone


	if hour12 > 6: rewindDone = False
	if (hour12 < 3 and  not rewindDone) or nextStep ==0 and currentSequenceNo ==8 and sensorDict["sensor"][0] == 1:

		if printON: print "rewind ", "%.2f"%secSinMidnit, "H",hour, "M",minute, "S",second, "dt %.5f"%(time.time()-t0), "nstep",nextStep, "totSteps",totalSteps
		move (0.001,maxStepsUsed,-1,  force=30, stopIf = [False,True] )
		move (0.001,maxStepsUsed,-1,  force=30, stopIf = [True,False] )
		rewindDone = True
		totalSteps = 0
		t0=time.time()
	totalSteps = max(0, min(totalSteps, maxStepsUsed) )

	return 



# ------------------    ------------------ 
def findLeftRight():
	global maxStepsUsed,stepsIn360
	global printON
	global waitBetweenSteps, secondsTotalInDay, maxStepsUsed 
	global amPM1224
	global whereIs12,  whereIsTurnF, whereIsTurnB
	global currentSequenceNo

	time.sleep(0.3)

	stayOn = 0.001
	if stepsIn360 < 1000:
		stayOn =0.001

	maxSteps = int(stepsIn360+2)

	# check if we start at 0 left or right
	getSensors()
	#  sensorDict["pin_sensor0"]["status"]

	print " \n starting left right \n"
	drawDisplayLines(["starting left right","determing limits", datetime.datetime.now().strftime("%a, %Y-%m-%d %H:%M")])

	steps 		= 0
	stepsTotal	= 0
	oneEights = int(stepsIn360 /8.)+10
	#print "0000 ===", steps, 0, sensorDict["sensor"][0], "--",sensorDict["sensor"][1]
	while True:
		# THIS IS THE EASIEST SIMPLE CASE:
		if sensorDict["sensor"][1]["status"] == 1:
			steps = move(stayOn, oneEights*6  , -1, force=30, stopIf = [True,False] )
			#print "0100 ===", steps,-1, sensorDict["sensor"][0], "--",sensorDict["sensor"][1]
			break

		# THIS IS THE MOST DIFFICULT, SOMEWHERE CLOSE TO 0 OR 24:
		elif sensorDict["sensor"][0]["status"] == 1:
			#test if still on when moving right
			steps = move(stayOn, 10  , 1, force=11, stopIf = [False,False] )
			#print "0200 ===", steps, 1, sensorDict["sensor"][0], "--",sensorDict["sensor"][1]

			if sensorDict["sensor"][0]["status"] == 0:
				steps = move(stayOn, oneEights*8  , 1, force=6, stopIf = [True,True] )
				#print "0201 ===", steps, 1, sensorDict["sensor"][0], "--",sensorDict["sensor"][1]

				if sensorDict["sensor"][0]["status"] == 1:
					steps = move(stayOn, oneEights*10, -1, force=6, stopIf = [False,True] )
					#print "0202 ===", steps, 1, sensorDict["sensor"][0], "--",sensorDict["sensor"][1]


				if sensorDict["sensor"][1]["status"] == 1:
					steps = move(stayOn, oneEights*8  ,-1, force=6, stopIf = [True,False] )
					#print "0203 ===", steps, -1, sensorDict["sensor"][0], "--",sensorDict["sensor"][1]
					break


			if sensorDict["sensor"][0]["status"] == 1:
				steps = move(stayOn, oneEights*8  , -1, force=6, stopIf = [False,True] )
				#print "0210 ===", steps, -1, sensorDict["sensor"][0], "--",sensorDict["sensor"][1]


			if sensorDict["sensor"][1]["status"] == 0:
				steps = move(stayOn, oneEights*6 , 1, force=30, stopIf = [True,True] )
				#print "0211 ===", steps, 1, sensorDict["sensor"][0], "--",sensorDict["sensor"][1]
				if sensorDict["sensor"][1]["status"] == 1:
					steps = move(stayOn, oneEights*6 , -1, force=30, stopIf = [True,False] )
					#print "0212 ===", steps, -1, sensorDict["sensor"][0], "--",sensorDict["sensor"][1]
					break

				if sensorDict["sensor"][0]["status"] == 1:
					steps = move(stayOn, oneEights*6 , -1, force=30, stopIf = [False,True] )
					#print "0230 ===", steps, -1, sensorDict["sensor"][0], "--",sensorDict["sensor"][1]
					steps = move(stayOn, oneEights*6 , -1, force=30, stopIf = [True,False] )
					break

			if sensorDict["sensor"][1]["status"] == 1:
				# found a midle, just continue to 0
				steps = move(stayOn, oneEights*6  , -1, force=30, stopIf = [True,False] )
				#print "0300 ===", steps, -1, sensorDict["sensor"][0], "--",sensorDict["sensor"][1]
				break


		else:
			steps = move(stayOn, 5  , 1, force=6, stopIf = [True,False] )
			#print "1000 ===", steps, 1, sensorDict["sensor"][0], "--",sensorDict["sensor"][1]
			if sensorDict["sensor"][1]["status"] == 0 and sensorDict["sensor"][1]["status"] == 0:
				steps = move(stayOn, oneEights*5  , 1, force=2, stopIf = [True,True] )
				#print "1100 ===", steps, 1, sensorDict["sensor"][0], "--",sensorDict["sensor"][1]

			if sensorDict["sensor"][1]["status"] == 1:
				steps = move(stayOn, oneEights*6 , -1, force=30, stopIf = [True,False] )
				#print "1200 ===", steps, -1, sensorDict["sensor"][0], "--",sensorDict["sensor"][1]
				break

			if sensorDict["sensor"][0]["status"] == 1:
				steps = move(stayOn, oneEights*3 , -1, force=5, stopIf = [True,True] )
				#print "1300 ===", steps, -1, sensorDict["sensor"][0], "--",sensorDict["sensor"][1]
				if sensorDict["sensor"][0]["status"] == 1:
					steps = move(stayOn, oneEights*8 ,  -1, force=30, stopIf = [False,True] )
					#print "1310 ===", steps, -1, sensorDict["sensor"][0], "--",sensorDict["sensor"][1]
					steps = move(stayOn, oneEights*8 , -1, force=30, stopIf = [True,False] )
					#print "1311 ===", steps, -1, sensorDict["sensor"][0], "--",sensorDict["sensor"][1]
					break
					# done

				elif sensorDict["sensor"][1]["status"] == 1:
					steps = move(stayOn, oneEights*8, -1, force=10, stopIf = [True,False] )
					#print "1320 ===", steps, -1, sensorDict["sensor"][0], "--",sensorDict["sensor"][1]
					break
					# done

				elif sensorDict["sensor"][0]["status"] == 0:
					steps = move(stayOn, oneEights*8 , -1, force=30, stopIf = [True,True] )
					#print "1340 ===", steps, -1, sensorDict["sensor"][0], "--",sensorDict["sensor"][1]
					if sensorDict["sensor"][1]["status"] == 1:
						steps = move(stayOn, oneEights*8 , -1, force=10, stopIf = [False,True] )
						break

					steps = move(stayOn, oneEights*5 , -1, force=30, stopIf = [True,False] )
					#print "11341 ===", steps, -1, sensorDict["sensor"][0], "--",sensorDict["sensor"][1]
					break
		print " no sensors found"
		time.sleep(1000)
		return 
	if getLightSensorValue(force=True): setColor(force=True)

	drawDisplayLines(["confirming"," left-right limits", datetime.datetime.now().strftime("%a, %Y-%m-%d %H:%M")])

	sensorDict["sensor"][0]["left"][0]  = 0
	## now we are at start
	## do full 360:
	print "\n fiding limits"
	seqN       = 0
	stepsTotal = 0
	if  sensorDict["sensor"][0]["status"] == 1:
		sensorDict["sensor"][0]["right"][0]  = 0
	for nn in range(len(sensorDict["sequence"])-1):
		steps = move(stayOn, oneEights*6,  1, force=20, stopIf = [True,True] )
		stepsTotal += steps
		seqN +=1
		#print "right ===", nn,  steps, sensorDict["sensor"][0], "--",sensorDict["sensor"][1]
		if  sensorDict["sensor"][1]["status"] == 1:
			sensorDict["sensor"][1]["right"][seqN]  = stepsTotal
		if  sensorDict["sensor"][0]["status"] == 1:
			sensorDict["sensor"][0]["right"][seqN]  = stepsTotal
	rightLimit = stepsTotal
	drawDisplayLines(["right limit set","confirming left limit", datetime.datetime.now().strftime("%a, %Y-%m-%d %H:%M")])
	if getLightSensorValue(force=True): setColor(force=True)

	stepsTotal = 0
	seqN       = 8
	if  sensorDict["sensor"][0]["status"] == 1:
		sensorDict["sensor"][0]["left"][seqN]  = rightLimit - 0
	for nn in range(len(sensorDict["sequence"])-1):
		steps = move(stayOn, int(oneEights*2), -1, force=20, stopIf = [True,True] )
		stepsTotal += steps
		seqN -=1
		#print "left  ===", nn,  steps, sensorDict["sensor"][0], "--",sensorDict["sensor"][1]
		if  sensorDict["sensor"][1]["status"] == 1:
			sensorDict["sensor"][1]["left"][seqN]  = rightLimit - stepsTotal
		if  sensorDict["sensor"][0]["status"] == 1:
			sensorDict["sensor"][0]["left"][seqN]  = rightLimit - stepsTotal

	leftLimit = stepsTotal
	
	if getLightSensorValue(force=True): setColor(force=True)


	if printON: print sensorDict
	if abs(rightLimit + leftLimit) > stepsIn360*2:
		addToBeepBlinkQueue(text=["S","O","S"])

	time.sleep(0.1)

	maxStepsUsed  = max(1,rightLimit)

	if amPM1224 =="24":	waitBetweenSteps 	= secondsTotalInDay     / maxStepsUsed 
	else: 				waitBetweenSteps 	= secondsTotalInHalfDay / maxStepsUsed 
	currentSequenceNo = 0
	print "waitBetweenSteps", waitBetweenSteps, "maxStepsUsed",maxStepsUsed
	drawDisplayLines(["wait and nSteps:","%d, %d"%(waitBetweenSteps,maxStepsUsed), datetime.datetime.now().strftime("%a, %Y-%m-%d %H:%M")])

	return 




# ########################################
# #########     beeps & blinks  ##########
# ########################################

def addToBeepBlinkQueue(text =[], color=[1,1,1], sound=1, stop = False, end=False, restore = True):
	global beepBlinkThread, stopBlinkBeep


	if stop: 
		stopBlinkBeep =True
		time.sleep(1)
		print" clear queue bf " ,beepBlinkThread["queue"].qsize() 
		beepBlinkThread["queue"].queue.clear()
		print" clear queue af",beepBlinkThread["queue"].qsize() 
		stopBlinkBeep =True
		return 

	if end: 
		stopBlinkBeep =True
		time.sleep(1)
		print" clear queue bf " ,beepBlinkThread["queue"].qsize() 
		beepBlinkThread["queue"].queue.clear()
		print" clear queue af",beepBlinkThread["queue"].qsize() 
		beepBlinkThread["thread"].join()
		return 

	add ={}
	if beepBlinkThread["beep"]    : add["beep"]  = sound
	if beepBlinkThread["color"]   : add["color"] = color
	add["text"]    = text
	add["restore"] = restore
	stopBlinkBeep  = False
	beepBlinkThread["queue"].put(add) 


def beepBlinkQueue():
	global beepBlinkThread, stopBlinkBeep

	while True:
		while not beepBlinkThread["queue"].empty():
			#print" checking queue size", actionQueue.qsize() 
			action = beepBlinkThread["queue"].get()
			doBlinkBeep(action) 
			if beepBlinkThread["end"]:
				sys.exit()
			if stopBlinkBeep: break
		if LastHourColorSetToRemember !=[]:
			setColor( blink=0, color = LastHourColorSetToRemember, force = False)
		if beepBlinkThread["end"]:
			sys.exit()
		time.sleep(1)
	sys.exit()



# ########################################
# #########     LED  funtions ############
# ########################################

# ------------------    ------------------ 
def doBlinkBeep(action):
	global stopBlinkBeep
	stopBlinkBeep = False
	if "text" not in action: return 
	blinkLetters(action["text"], [1,1,1], action["beep"])

# ------------------    ------------------ 
def setColor( blink=0, color = [1.,1.,1.], beep=-1, force = False):
	global colPWM, LastHourColorSet, secSinMidnit, LastHourColorSetToRemember, timeAtlastColorChange
	global gpiopinSET

	lastC = LastHourColorSet

	if stopBlinkBeep: return 
	if blink !=0 : 
		for p in range(len(gpiopinSET["pin_rgbLED"])):
			pin = gpiopinSET["pin_rgbLED"][p]
			if  blink ==1: 
				if color[p] >= 0:
					setGPIOValue( pin, 1, amplitude= getIntensity(100*color[p]) , pig=True )
			elif blink == -1: 
				setGPIOValue( pin, 1,  amplitude=getIntensity(0), pig=True )

		if  blink == 1: 
			if beep >= 0 : setGPIOValue(  gpiopinSET["pin_beep"], 1  )	
		else:			   setGPIOValue(  gpiopinSET["pin_beep"], 0  )	

		LastHourColorSet = -1


	else:
		if abs(secSinMidnit-lastC) > 30  and (time.time() - timeAtlastColorChange) >10 or force:
			cm = timeToColor(secSinMidnit)
			for p in range(len(gpiopinSET["pin_rgbLED"])):
				pin = gpiopinSET["pin_rgbLED"][p]
				intens = getIntensity(cm[p]*color[p]) 
				setGPIOValue( pin, 1, amplitude=intens, pig=True )	
				#print "LED int: ", p, intens, lightSensorValue, " secs since last:", abs(secSinMidnit-lastC)
			timeAtlastColorChange = time.time()
			LastHourColorSet = secSinMidnit
			LastHourColorSetToRemember = color

# ------------------    ------------------ 
def getIntensity(intens):
	global  intensity
	retV=  min( intensity["Max"], max(intensity["Min"],float(intens)*(intensity["Mult"]/100.) * lightSensorValue ) )
	#print  "intens", retV
	return retV


# ------------------    ------------------ 
# ------------------    ------------------ 
def testIfBlink( ):
	global speed, blinkHour, hour
	if speed ==1:
		if  second%60 < 20 and blinkHour != hour:
			blinkHour = hour
			addToBeepBlinkQueue(text =["o","n"], color=[1,1,1], sound=1, stop = False, end=False, restore = True)
	return 

# ------------------    ------------------ 
def blinkLetters(letters, color, beep):
	global morseCode
	global longBlink, shortBlink, breakBlink
	global stopBlinkBeep
	for l in letters:
		if l in morseCode:
			for sig in morseCode[l]:
				if sig ==1:	blink(longBlink,  breakBlink, 1, color, beep)
				else:   	blink(shortBlink, breakBlink, 1, color, beep)
			time.sleep(breakBlink)
	return

# ------------------    ------------------ 
def blink(on, off, n, color, beep):
	global stopBlinkBeep
	for i in range(n):
		if stopBlinkBeep: return 
		setColor(blink= 1, color=color, beep=beep)
		time.sleep(on)	
		if stopBlinkBeep: return 
		setColor(blink=-1, color=color, beep=beep)
		time.sleep(off)	
	return 


def timeToColor(tt):
	times = [   0, 		   4*60*60,	   8*60*60,		11*60*60,	  13*60*60,		 16*60*60,	20*60*60,	 24*60*60]
	rgb   = [ [20,20,20], [20,20,20], [80,30,30], [100,100,100], [100,100,100], [50,50,50], [80,30,30], [20,20,20] ]
	rgbout= rgb[0]
	for ii in range(1,len(times)):
		if tt > times[ii]: continue
		dt = (tt-times[ii-1])/(times[ii]-times[ii-1]) 
		for rr in range(3):
			rgbout[rr] =  dt * (rgb[ii][rr]-rgb[ii-1][rr])  +  rgb[ii-1][rr]
		break
	return rgbout

def getLightSensorValue(force=False):
	global lightSensorValue, lastlightSensorValue, lastTimeLightSensorValue, lastTimeLightSensorFile, lightSensorValueRaw
	try:
		tt0 = time.time()
		if ( tt0 - lastTimeLightSensorValue  < 2) and not force:	return False
		if not os.path.isfile(G.homeDir+"temp/lightSensor.dat"):	return False
		f=open(G.homeDir+"temp/lightSensor.dat","r")
		rr = json.loads(f.read())
		f.close()
		tt = float(rr["time"])
		if tt == lastTimeLightSensorFile:						 	return False
		lastTimeLightSensorFile = tt
		lightSensorValueREAD = float(rr["light"])
		sensor = rr["sensor"]
		if sensor == "i2cTSL2561":
			maxRange = 12000.
		elif sensor == "i2cOPT3001":
			maxRange =	2000.
		elif sensor == "i2cVEML6030":
			maxRange =	700.
		elif sensor == "i2cIS1145":
			maxRange =	2000.
		else:
			maxRange =	1000.
		lightSensorValueRaw =  max(min(1.,lightSensorValueREAD/maxRange) ,0.0001 ) *2. # scale factor 2 to not just reduce, but also increase light, max will cut if off at 100%
		if force:	
			lightSensorValue = lightSensorValueRaw
			return True
		if (  abs(lightSensorValueRaw-lastlightSensorValue) / (max (0.005,lightSensorValueRaw+lastlightSensorValue))  ) < 0.05: return False
		lightSensorValue = (lightSensorValueRaw*2 + lastlightSensorValue*1) / 3.
		lastTimeLightSensorValue = tt0
		print "lightSensorValue", lightSensorValueRaw, lightSensorValue, lastlightSensorValue, lightSensorValueREAD, maxRange
		lastlightSensorValue = lightSensorValue
		return True
	except	Exception, e:
		U.toLog(-1, u"in Line '%s' has error='%s'" % (sys.exc_traceback.tb_lineno, e), doPrint=True)
	return False


# ########################################
# #########   time   funtions ############
# ########################################
# ------------------    ------------------ 
def getTime():
	global speed, amPM1224
	global hour, minute, second
	global secSinMidnit, hour12, secSinMidnit2	

	today = datetime.date.today()
	secSinMidnit = (time.time() - time.mktime(today.timetuple()))*speed
	secSinMidnit = secSinMidnit %(secondsTotalInDay)
	hour   = int( secSinMidnit/(60*60) )
	minute = int( (secSinMidnit - hour*60*60) /60 )
	second = int( secSinMidnit - hour*60*60 - minute*60)
	if amPM1224 == "12": 
		hour12 = hour%12
		secSinMidnit2 = secSinMidnit%secondsTotalInHalfDay
	elif amPM1224 == "24": 
		hour12 = hour
		secSinMidnit2  =secSinMidnit
	else: 
		hour12 = hour
		secSinMidnit2  =secSinMidnit
	return 

# ------------------    ------------------ 
def getamPM():
	val = getPinValue("pin_amPM1224")
	if val == 1:
		return "12"
	elif val == 0:
		return "24"
	return "error"

# ------------------    ------------------ 
def testForAmPM():
	global amPM1224
	val = getamPM()
	if   val == "12":
		#print "pin_amPM1224 on"
		if amPM1224 =="24":
			getTime()
			findLeftRight()
		amPM1224 = "12"
	elif val == "24":
		if amPM1224 =="12":
			getTime()
			findLeftRight()
		amPM1224 = "24"


#
# ------------------    ------------------ 
def getSensors():
	global 	sensorDict
	anyChange = False
	for n in range(len(sensorDict["sensor"])):
		newValue = getPinValue( "pin_sensor"+str(n) )
		#print "newValue",key, sensorDict["sensor"][key]
		if newValue != sensorDict["sensor"][n]["newValue"]:
			sensorDict["sensor"][n]["lastValue"] = sensorDict["sensor"][n]["newValue"]
			sensorDict["sensor"][n]["newValue"] = newValue
			anyChange = True

	if anyChange:
		if  sensorDict["sensor"][0]["newValue"] == 1:
			sensorDict["sensor"][0]["status"] = 1
			sensorDict["sensor"][1]["status"] = 0
			sensorDict["sensor"][2]["status"] = 0
		else:
			sensorDict["sensor"][0]["status"] = 0
			if  sensorDict["sensor"][1]["newValue"] == 1:
				sensorDict["sensor"][1]["status"] = 1
				sensorDict["sensor"][2]["status"] = 0
			else:
				sensorDict["sensor"][1]["status"] = 0
				if  sensorDict["sensor"][2]["newValue"] == 1:
					sensorDict["sensor"][2]["status"] = 1
				else:
					sensorDict["sensor"][2]["status"] = 0

		if (sensorDict["sensor"][0]["newValue"] == 0 and 
			sensorDict["sensor"][1]["newValue"] == 0 and
			sensorDict["sensor"][2]["newValue"] == 0 and 
			sensorDict["sensor"][3]["newValue"] == 0) :	sensorDict["sensor"][3]["status"] = "wireFault"
		else:													sensorDict["sensor"][3]["status"] = "ok"
 
			
	return anyChange



# ########################################
# #########    web   funtions ############
# ########################################

def updateStatus(status):
	global amPM1224, intensity, whereIs12, whereIsTurnF, whereIsTurnB, totalSteps, stepsIn360
	WebStatusFile	=  G.homeDir+"/temp/sunDial.status"
	statusData		= []
	statusData.append( "time........... = "+ datetime.datetime.now().strftime(u"%H:%M") )
	statusData.append( "opStatus....... = "+ status )
	statusData.append( "12/24 mode..... = "+ amPM1224 )
	statusData.append( "intensity...... = "+ "scale:%d"%intensity["Mult"] + ", Min:%d"%intensity["Min"] + ", Max:%d"%intensity["Max"]  )
	statusData.append( "Steps in 360... = "+ "%d"%stepsIn360 )
	statusData.append( "maxStepsUsed... = "+ "%d"%maxStepsUsed+" from 0 to 24/12" )
	statusData.append( "Step Now....... = "+ "%d"%totalSteps )
	statusData.append( "12 sensor @.... = "+ "%d"%whereIs12["average"]+" step " )
	statusData.append( "TurnSensorF @.. = "+ "%d"%whereIsTurnF["average"]+" step " )
	statusData.append( "TurnSensorB @.. = "+ "%d"%whereIsTurnF["average"]+" step " )
	cc = timeToColor(secSinMidnit)
	statusData.append( "currentColor... = "+ "R:%d"%cc[0] + ", G:%d"%cc[1] + ", B:%d"%cc[2] + " / 255" )

	U.updateWebStatus(WebStatusFile, json.dumps(statusData) )


 #######################################
# #########       main        ##########
# ######################################

global clockDict, clockLightSet, useRTC
global sensor, output, inpRaw
global oldRaw,	lastRead, inp
global timeZones, timeZone
global doReadParameters
global networkIndicatorON
global lastStep, colPWM,  LastHourColorSet, beepPWM
global intensity
global maxStepsUsed, startSteps, stepsIn360, nStepsInSequence
global speed, amPM1224, motorType, adhocWeb
global gpiopinSET, SeqCoils
global blinkHour
global t0
global printON
global totalSteps
global hour, minute, second
global secSinMidnit, hour12, secSinMidnit2	
global webAdhocLastOff, webAdhoc
global rewindDone
global longBlink, shortBlink, breakBlink
global morseCode
global whereIs12, whereIsTurnF, whereIsTurnB
global minStayOn
global lastDirection
global isDisabled, isSleep
global isFault
global RestartLastOff 
global clockDictLast
global beepBlinkThread, stopBlinkBeep
global PIGPIO, pwmRange
global colPWM
global speedOverWrite
global timeAtlastColorChange
global overallStatus
global buttonDict, sensorDict
global currentSequenceNo, inbetweenSequences
global lightSensorValue, lastlightSensorValue, lastTimeLightSensorValue, lastTimeLightSensorFile, lightSensorValueRaw
global pinsToName
global menuPosition


morseCode= {"A":[0,1], 		"B":[1,0,0,0],	 "C":[1,0,1,0], "D":[1,0,0], 	"E":[0], 		"F":[0,0,1,0], 	"G":[1,1,0],	"H":[0,0,0,0], 	"I":[0,0],
			"J":[0,1,1,1], 	"K":[1,0,1], 	"L":[0,1,0,0], 	"M":[1,1], 		"N":[1,0], 		"O":[1,1,1], 	"P":[0,1,1,0],	"Q":[1,1,0,1], 	"R":[0,1,0],
			"S":[0,0,0], 	"T":[1], 		"U":[0,0,1], 	"V":[0,0,0,1], 	"W":[0,1,1], "X":[1,0,0,1], 	"%Y":[1,0,1,1], 	"Z":[1,1,0,0],
			"0":[1,1,1,1,1], "1":[0,1,1,1,1], "2":[0,0,1,1,1], "3":[0,0,0,1,1], "4":[0,0,0,0,1], "5":[0,0,0,0,0], "6":[1,0,0,0,0], "7":[1,1,0,0,0], "8":[1,1,1,0,0], "9":[1,1,1,1,0],
			"s":[0], # one short
			"l":[1], # one long
			"b":[0,0,0,1]}  # beethoven ddd DAAA

menuPosition			= ["",""]
pinsToName				= {}
lightSensorValue		= 0.5
lastlightSensorValue	= 0.5
lastTimeLightSensorValue =0
lastTimeLightSensorFile = 0
lightSensorValueRaw		= 0

inbetweenSequences			= False
currentSequenceNo		= 0
overallStatus 			="OK"
buttonDict				= {}
sensorDict				= {}
timeAtlastColorChange	= 0
speedOverWrite			= -1

PIGPIO					= ""
pwmRange				= 0
colPWM 					= {}

longBlink			  	= 0.6
shortBlink			  	= 0.2
breakBlink			  	= 0.5

isFault				  	= False

isDisabled			  	= True
isSleep				  	= True
lastDirection		  	= 0
webAdhocLastOff		  	= time.time() + 100
webAdhoc			  	= False
# constants 
adhocWebLast		  	= 0
motorType			  	= "xx"
startSteps			  	= 0
secondsTotalInDay     	= 60.*60.*24.
secondsTotalInHalfDay 	= 60.*60.*12
intensity             	= {}
intensity["Mult"]     	= 100.
intensity["Max"]      	= 100.
intensity["Min"]      	= 10.
amPM1224			  	= "24"
speed				  	= 1
RestartLastOff 		  	= time.time()+100

lastStep              	= 0
LastHourColorSet      	= -1
nightMode				= 0
doReadParameters		= True
dd						= datetime.datetime.now()
oldRaw					= ""
lastRead				= 0
inpRaw					= ""
inp						= ""
debug					= 5
loopCount				= 0
sensor					= G.program
lastGPIOreset	 		= 0
G.lastAliveSend	 		= time.time() -1000
loopC			 		= 0
lastShutDownTest 		= -1
lastRESETTest	 		= -1
printON 				= True
totalSteps 				= 0
t0						= time.time()
blinkHour				= -1
rewindDone 				= True
nextStep 				= 1
whereIs12 				= {-1:-1, 1:-1, "average":-1, "active":False}
whereIsTurnF 			= {-1:-1, 1:-1, "average":-1, "active":False}
whereIsTurnB 			= {-1:-1, 1:-1, "average":-1, "active":False}
clockDictLast			= {}
LastHourColorSetToRemember =[]

myPID		= str(os.getpid())
U.killOldPgm(myPID,G.program+".py")# kill old instances of myself if they are still running

try:    speedOverWrite = int(sys.argv[1])
except: speedOverWrite =-1
	

startDisplay()

drawDisplayLines(["Status:   starting up",".. read params, time..",  datetime.datetime.now().strftime("%a, %Y-%m-%d %H:%M")])


setgpiopinSET()

setupTimeZones()
#print "current tz:", currTZ,JulDelta,JanDelta,NowDelta, timeZones[currTZ+12], timeZones

if readParams() ==3:
		U.toLog(-1," parameters not defined", doPrint=True)
		U.checkParametersFile("parameters-DEFAULT-sunDial", force = True)
		time.sleep(20)
		U.restartMyself(param=" bad parameters read", reason="",doPrint=True)


setMotorOFF()

U.echoLastAlive(G.program)


print "gpiopinSET",gpiopinSET



stopBlinkBeep	= False
beepBlinkThread = {"color":True, "beep":True,"stop":False, "end":False, "queue": Queue.Queue(), "thread": threading.Thread(name=u'beepBlinkQueue', target=beepBlinkQueue, args=())}	
beepBlinkThread["thread"].start()



amPM1224 = getamPM()

### here it starts 
getTime()
lightSensorValue = 0.1
getLightSensorValue(force=True)
setColor(force=True)

addToBeepBlinkQueue(text=["b","b","b","b","b","b"])
#addToBeepBlinkQueue(text = ["S","T","A","R","T"][1,1,1],)
#time.sleep(3)

drawDisplayLines(["Status:     finding",".. L/R  Stop-Limits",  datetime.datetime.now().strftime("%a, %Y-%m-%d %H:%M")])

findLeftRight()

getLightSensorValue(force=True)
setColor(force=True)

sleepDefault = waitBetweenSteps/(5*speed)


print "clock starting;   waitBetweenSteps", waitBetweenSteps, "speed", speed, "totalSteps",totalSteps,"sleepDefault", sleepDefault,"amPM1224",amPM1224,"secSinMidnit2",secSinMidnit2
print "intensity", intensity

nextStep = 1
U.startAdhocWebserver()
U.webserverForStatus()
updateStatus(status="starting")

while True:
			
	getTime()

	lastMove = time.time()
	nextStep = testIfMove( waitBetweenSteps, nextStep )
	drawDisplayLines(["Status "+overallStatus,"@ Pos.: %d/%d"%(totalSteps,maxStepsUsed), datetime.datetime.now().strftime("%a, %Y-%m-%d %H:%M")])

	nextMove = lastMove + waitBetweenSteps/speed
	testIfRewind( nextStep )
	sleep =  sleepDefault
	testIfBlink()
	slept= 0
	lastDisplay = 0
	sleep = nextMove - time.time()
	startSleep = time.time()
	sleep = nextMove - startSleep
	endSleep = startSleep + sleep
	minSleep = max(0.1,min(0.25,sleep))
	ii = 1000
	lastDisplay = time.time()
	print "	sleep ", sleep," nextMove", nextMove,"minSleep",minSleep,"tt", time.time()

	while ii >0:
		if getLightSensorValue():
			setColor(force=True)
		elif (  abs(lightSensorValueRaw-lightSensorValue) / (max (0.005,lightSensorValueRaw+lightSensorValue))  ) > 0.05: 
				lightSensorValue = (lightSensorValueRaw*2 + lightSensorValue*1) / 3.
				setColor(force=True)

		ii -= 1
		time.sleep(minSleep)
		slept += minSleep

		tt = time.time()
		if tt >= endSleep: break
		if lastDisplay - tt > 5:	
			lastDisplay = tt
			drawDisplayLines(["Status "+overallStatus,"@ Pos.: %d/%d"%(totalSteps,maxStepsUsed), datetime.datetime.now().strftime("%a, %Y-%m-%d %H:%M")])

	U.checkAdhocWebserverOutput()
	updateStatus(status="normal")

	
stopBlinkBeep	= True
time.sleep(1)
beepBlinkThread["thread"].join


		

