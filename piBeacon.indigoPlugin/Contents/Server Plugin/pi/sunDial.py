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

import pigpio

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
charCommandsW=[]
for ii in range(len(ALLCHARACTERS)):
	charCommandsW.append([" "+ALLCHARACTERS[ii],		"addChar('"+ALLCHARACTERS[ii]+"')"])
	charCommandsW.append(["  ..delete last Char",	"deleteLastChar()"])
	charCommandsW.append(["  ..save and exit",		"doSaveMenu(setMenuParam)"])
charCommandsW.append([" exit submenu",				"doMenuUp(setMenuParam)"] )

charCommandsS=[]
for ii in range(len(ALLCHARACTERS)):
	charCommandsS.append([" "+ALLCHARACTERS[ii],	"addChar('"+ALLCHARACTERS[ii]+"')"])
	charCommandsS.append(["  ..delete last Char",	"deleteLastChar()"])
	charCommandsS.append(["  ..save and exit",		"doSaveMenu(setMenuParam)"])
charCommandsS.append([" exit submenu",				"doMenuUp(setMenuParam)"] )


##               top option               selection, command
MENUSTRUCTURE =[[],[]]
MENUSTRUCTURE[0]=[	
					[" status 2",				"setMenuParam=''"],
					[" power off",				"setMenuParam=''"],
					[" 12 or 24 clock",			"setMenuParam=''"],
					[" light intensity",		"setMenuParam=''"],
					[" move",					"setMenuParam=''"],
					[" reset",					"setMenuParam=''"],
					[" restart",				"setMenuParam=''"],
					[" start Web config",		"setMenuParam=''"],
					[" WiFi SID",				"setMenuParam='WiFissidString'"],
					[" WiFi Passwd",			"setMenuParam='WiFiPassString'"],
				]
#                         menu text          ,  function to call   
MENUSTRUCTURE[1]=[	
					[	[" WEB Functions",""], [" Info @ http:ip#",""], [" update @ ..ip#:8001", ""], [" exit submenu", "doMenuUp('')"] 	],
					[	[" confirm",			"powerOff()"],												[" exit submenu", "doMenuUp('off')"] 	],
					[	[" 12",   				"set12()"],				[" 24", 	"set24()"],				[" exit submenu", "doMenuUp('amPM')"] 	], 
					[	[" up",   				"increaseLED()"],		[" down", 	"decreaseLED()"],		[" exit submenu", "doMenuUp('LED')"] 	], 
					[	[" left", 				"moveLeft()"], 			[" right", 	"moveRight()"],			[" exit submenu", "doMenuUp('move')"] 	],
					[	[" clock reset",		"doReset()"], 												[" exit submenu", "doMenuUp('reset')"] 	],
					[	[" system", 			"doReststart()"],											[" exit submenu", "doMenuUp('restart')"]], 
					[	[" start",   			"startWeb()"], 			[" stop",	"stopWeb()"], 			[" exit submenu", "doMenuUp('WEB')"] 	],
						charCommandsS,				
						charCommandsW
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
	global lineCoordinates, lineCoordDeltaY, lastLines
	global xPixels, yPixels
	global displayPriority, waitForDisplayToRest
	global draw, imData
	global displayMenuLevelActive, displayMenuAreaActive, displayMenuSubAreaActive
	global charString, WiFissidString, WiFiPassString, setMenuParam

	xPixels 				= 128
	yPixels 				= 64
	lineCoordDeltaY			= [0,0,32,25,16,13]
	lineCoordinates			= [[],[],[],[],[],[]]
	lineCoordinates[2] 		= [(0,+2),(0,lineCoordDeltaY[2]*1+2)]
	lineCoordinates[3] 		= [(0,+2),(0,lineCoordDeltaY[3]*1+2),(4,lineCoordDeltaY[3]*2+2)]
	lineCoordinates[4] 		= [(0,+2),(0,lineCoordDeltaY[4]*1+2),(0,lineCoordDeltaY[4]*2+2),(0,lineCoordDeltaY[4]*3+2)]
	lineCoordinates[5] 		= [(0,+2),(0,lineCoordDeltaY[5]*1+2),(0,lineCoordDeltaY[5]*2+2),(0,lineCoordDeltaY[5]*3+2),(0,lineCoordDeltaY[5]*4+2)]
	lastLines 				= ["","","","","","","",""]

	outputDev				= sh1106(width=xPixels, height=yPixels)

	displayFont 			= ImageFont.load_default()
	imData					= PIL.Image.new('1', (xPixels,yPixels))
	draw 					= ImageDraw.Draw(imData)
	displayPriority    		= 0
	waitForDisplayToRest	= 60.
	displayMenuLevelActive	= -1
	displayMenuAreaActive	= -1
	displayMenuSubAreaActive= 0
	charString				= ""
	WiFissidString			= ""
	WiFiPassString			= ""
	setMenuParam			= ""

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
def drawDisplayLines( lines, nLines=3, clear=True, prio=0, inverse=False, show=True, force =False):
	global outputDev, displayFont
	global lineCoordinates, lastLines
	global xPixels, yPixels, imData, draw
	global displayPriority, waitForDisplayToRest

	#print "drawDisplayLines", lines, nLines, clear, prio, inverse, show, displayPriority

	if displayPriority > 0: 
		if time.time() - displayPriority > waitForDisplayToRest:
			displayPriority = 0
	
	if prio < displayPriority: return 
	displayPriority = prio 

	if not force:
		new = False
		for ii in range(len(lines)):
			if lines[ii] != lastLines[ii]:
				new=True
				break
		if not new: return 

	lastLines	= copy.copy(lines)
	if clear:
		clearDisplay(prio=prio, inverse=inverse, force=force)

	if inverse: fill =0
	else: 		fill =255

	#print "drawDisplayLines draw"
	for ii in range(len(lines)):
		draw.text(lineCoordinates[nLines][ii], lines[ii],  font=displayFont, fill=fill)

	if show: doShowImage()
	return 

# ------------------    ------------------ 
def drawDisplayLine( line, iLine=1, nLines=3, focus=False, prio=0, inverse=False):
	global outputDev, displayFont
	global lineCoordinates, lastLines
	global xPixels, yPixels, imData, draw
	global displayPriority, waitForDisplayToRest

	if displayPriority > 0: 
		if time.time() - displayPriority > waitForDisplayToRest:
			displayPriority = 0
	
	if prio < displayPriority: return 
	displayPriority = prio 


	if focus:	fill = 0
	else: 		fill = 255

	#print "drawDisplayLine", line, iLine, nLines, focus, prio, inverse, fill
	clearDisplay((lineCoordinates[nLines][iLine][0], lineCoordinates[nLines][iLine][1]-2, xPixels,  lineCoordinates[nLines][iLine][1] +lineCoordDeltaY[nLines]-2), prio=prio, inverse=inverse  )
	draw.text(lineCoordinates[nLines][iLine], line,  font=displayFont, fill=fill)
	
	return 

#
# ------------------    ------------------ 
def clearDisplay( area=[], prio=0, inverse=False, show=False, force=False):
	global outputDev, displayFont
	global lineCoordinates, lastLines
	global xPixels, yPixels, imData, draw
	global displayPriority, waitForDisplayToRest
	global lastLines

	if displayPriority > 0: 
		if time.time() - displayPriority > waitForDisplayToRest:
			displayPriority = 0
	
	if prio < displayPriority: return 
	displayPriority = prio 
	lastLines 				= ["","","","","","","",""]


	if inverse: fill=255
	else:		fill=0

	#print "clearDisplay", area, inverse, fill
	if area ==[]:
		draw.rectangle((0, 0, xPixels, yPixels), outline=0, fill=fill)
	else:
		draw.rectangle(area, outline=0, fill=fill)
	if show: doShowImage()
		
# ------------------    ------------------ 
def composeMenu(useLevel, area, subArea, nLines):
	global setMenuParam, charString

	lines =[]
	top   = MENUSTRUCTURE[0]
	print "composeMenu", useLevel, area,subArea,nLines, "top[area][0]", top[area][0]

	clearDisplay(prio=time.time()+100)
	if useLevel== 0:
		start = max(0, min(area, len(top) - nLines) )
		end   = min(area+nLines, len(top) )
		nn =-1
		for ii in range(start, end):
			nn +=1
			if ii == area:
#				lines.append(  str(area)+" "+str(level)+"  "+str(subarea)+" x "+str(MENUSTRUCTURE[level][ii])  )
				drawDisplayLine( str(top[ii][0]) , iLine=nn, nLines=nLines,  prio=time.time()+100, focus=True, inverse=True)
			else:
				drawDisplayLine( str(top[ii][0]), iLine=nn, nLines=nLines, prio=time.time()+100)

	if useLevel == 1:
		short2 = MENUSTRUCTURE[1][area]
		if subArea < len(short2):
			start = max(0, min(subArea, len(short2) - nLines) )
			if charString =="":
				end   = min(subArea+nLines-1, len(short2) )
			else:
				end   = min(subArea+nLines-2, len(short2) )
			drawDisplayLine( top[area][0][0:20]+" ==>" , iLine=0, nLines=nLines, prio=time.time()+100, )
			nn=0
			print "composeMenu start, end, setMenuParam",start, end, setMenuParam, charString
			for ii in range(start, end):
				nn+=1
				if ii == subArea:
					drawDisplayLine( str(short2[ii][0]), iLine=nn, nLines=nLines, prio=time.time()+100, focus=True, inverse=True )
				else:
					drawDisplayLine( str(short2[ii][0]), iLine=nn, nLines=nLines, prio=time.time()+100)
			if charString !="":
				drawDisplayLine(charString, iLine=nn+1, nLines=nLines, prio=time.time()+100)
	doShowImage()
	return 

# ------------------    ------------------ 
def composeMenu0():
	global displayMenuLevelActive, displayMenuAreaActive, displayMenuSubAreaActive
	if displayMenuLevelActive ==0:	nLines = 4
	else:							nLines = 5
	composeMenu(displayMenuLevelActive, displayMenuAreaActive, displayMenuSubAreaActive, nLines)
	doShowImage()

# ------------------    ------------------ 
def doShowImage():
	global imData, outputDev
	outputDev.display(imData)


# ------------------    ------------------ 
def showStandardStatusDisplay(force=False):
	global overallStatus, totalSteps, maxStepsUsed, sensorDict
	value =""
	for ii in range(len(sensorDict["sensor"])):
		value +=str(sensorDict["sensor"][ii]["clicked"] )+" "
	value = value.strip(" ")
	drawDisplayLines(["St:"+overallStatus+"; Wifi:"+str(G.wifiEnabled)[0]+"; Cl:"+amPM1224,"IP#:"+G.ipAddress ,"SensClicked: "+value,"@ Pos.: %d/%d"%(totalSteps,maxStepsUsed), datetime.datetime.now().strftime("%a, %Y-%m-%d %H:%M")], nLines=5)
	updatewebserverStatus("normal")

# ------------------    ------------------ 
def showStatus2(force=True):
	global overallStatus, totalSteps, maxStepsUsed, sensorDict
	drawDisplayLines(["Web INFO:","  "+G.ipAddress,"Web ENTRY:","  "+G.ipAddress+":8001","", datetime.datetime.now().strftime("%a, %Y-%m-%d %H:%M")], nLines=5, clear=True, force=force, show=True)


# ------------------    ------------------ 
def updatewebserverStatus(status):
	global amPM1224, intensity, whereIs12, whereIsTurnF, whereIsTurnB, totalSteps, stepsIn360
	statusData		= []

	statusData.append( "SunDial Current status" )
	statusData.append( "time........... = "+ datetime.datetime.now().strftime(u"%H:%M") )
	statusData.append( "IP-Number...... = "+ G.ipAddress )
	statusData.append( "WiFi enabled... = "+ str(G.wifiEnabled) )
	statusData.append( "opStatus....... = "+ status )
	statusData.append( "12/24 mode..... = "+ amPM1224 )
	statusData.append( "intensity...... = "+ "scale:%d"%intensity["Mult"] + ", Min:%d"%intensity["Min"] + ", Max:%d"%intensity["Max"]  )
	statusData.append( "Steps in 360... = "+ "%d"%stepsIn360 )
	statusData.append( "maxStepsUsed... = "+ "%d"%maxStepsUsed+" from 0 to 24/12" )
	statusData.append( "Step Now....... = "+ "%d"%totalSteps )
	statusData.append( "Sensor 0....... = "+ "%s"%sensorDict["sensor"][0]["clicked"])
	statusData.append( "Sensor 12...... = "+ "%s"%sensorDict["sensor"][1]["clicked"])
	statusData.append( "Sensor LineChk1 = "+ "%s"%sensorDict["sensor"][2]["clicked"])
	statusData.append( "Sensor LineChk2 = "+ "%s"%sensorDict["sensor"][3]["clicked"])
	cc = timeToColor(secSinMidnit)
	statusData.append( "currentColor... = "+ "R:%d"%cc[0] + ", G:%d"%cc[1] + ", B:%d"%cc[2] + " / 255" )

	U.updateWebStatus(json.dumps(statusData) )


# ########################################
# #########   button funtions ############
# ########################################
# ------------------    ------------------ 
def doAction():
	global displayMenuLevelActive, displayMenuAreaActive, displayMenuSubAreaActive
	global setMenuParam
	print "doAction displayMenuLevelActive", displayMenuLevelActive,"; displayMenuAreaActive", displayMenuAreaActive, "; subArea", displayMenuSubAreaActive

	if displayMenuAreaActive < 0: return 

	if displayMenuLevelActive == 0:
		composeMenu0()
		cmd = MENUSTRUCTURE[0][displayMenuAreaActive][1]
		print "action0:>>%s<<"%cmd
		exec(cmd) 

	elif displayMenuLevelActive == 1:
		if displayMenuSubAreaActive < 0: return 
		composeMenu0()
		cmd = MENUSTRUCTURE[1][displayMenuAreaActive][displayMenuSubAreaActive][1]
		print "action1:>>%s<<"%cmd
		exec(cmd) 
		if displayMenuLevelActive == 0:
			composeMenu0()
	
	return 



# ------------------    ------------------ 
def buttonPressed(pin, level, tick):
	global gpiopinNumber, pinsToName, displayPriority
	global displayMenuLevelActive, displayMenuAreaActive, displayMenuSubAreaActive
	global lastExpireDisplay

	if pin not in pinsToName: 			return 
	val = getPinValue("0", pin=pin) 
	if val ==-1: 						return 
	print " buttonPressed ", pin, pinsToName[pin], val, displayMenuLevelActive, displayMenuAreaActive, displayMenuSubAreaActive


	lastExpireDisplay = time.time() +20.

	if displayMenuLevelActive < -1:
		displayMenuLevelActive += 1
		if displayMenuLevelActive < 0:
			showStandardStatusDisplay(force=True)
			return 
			


	if pinsToName[pin] == "pin_Select": 
		if displayMenuLevelActive  == -1 or displayMenuAreaActive < 0:
			displayMenuAreaActive = 0

		if displayMenuLevelActive  <= 0:
			displayMenuSubAreaActive =-1

		if displayMenuSubAreaActive < 0:
			displayMenuLevelActive += 1

		if displayMenuLevelActive  == 0:
			doAction()

		elif displayMenuLevelActive  == 1:
			cmd = MENUSTRUCTURE[0][displayMenuAreaActive][1]
			print "action0:>>%s<<"%cmd
			exec(cmd) 

		if displayMenuLevelActive > 0:
			if displayMenuSubAreaActive < 0:
				displayMenuSubAreaActive = 0
			displayMenuLevelActive = 1
			doAction()
		else:
			return 	


	if pinsToName[pin] == "pin_Dn":

		if displayMenuLevelActive == 0:
			displayMenuAreaActive += 1
			if displayMenuAreaActive >= len(MENUSTRUCTURE[0]):
				displayMenuAreaActive = 0
			composeMenu0()

		elif displayMenuLevelActive == 1:
			displayMenuSubAreaActive += 1
			if displayMenuSubAreaActive >= len(MENUSTRUCTURE[1][displayMenuAreaActive]):
				displayMenuSubAreaActive = 0
			composeMenu0()

		else:
			return 	

	elif pinsToName[pin] == "pin_Up": 
		if displayMenuLevelActive == 0:
			displayMenuAreaActive -= 1
			if displayMenuAreaActive < 0:
				displayMenuAreaActive = len(MENUSTRUCTURE[0])-1
			composeMenu0()
		elif displayMenuLevelActive == 1:
			displayMenuSubAreaActive -= 1
			if displayMenuSubAreaActive < 0:
				displayMenuSubAreaActive = len(MENUSTRUCTURE[1][displayMenuAreaActive])-1
			composeMenu0()
		else:
			return 	

	elif pinsToName[pin] == "pin_Exit":
		displayMenuLevelActive 		-= 1
		displayMenuSubAreaActive 	= -1

		if displayMenuLevelActive 	< 0:
			print " setting to normal display"
			displayPriority 		= 0
			displayMenuLevelActive 	= -1
			showStandardStatusDisplay(force=True)

		elif displayMenuLevelActive == 0:
			composeMenu0()

# ------------------    ------------------ 
def addChar(c):
	global charString, WiFissidString, WiFiPassString, setMenuParam
	charString +=c
	print "addChar charString", c, charString
	return 

# ------------------    ------------------ 
def deleteLastChar():
	global charString, WiFissidString, WiFiPassString, setMenuParam
	print "deleteLastChar"
	if len(charString)>0: charString = charString[0:-1]
	print "deleteLastChar charString", charString
	return 

# ------------------    ------------------ 
def doSaveMenu(param):
	global charString, WiFissidString, WiFiPassString, setMenuParam
	print " into doSaveMenu", param
	if param == "" : return 
	if param == setMenuParam:
		if   setMenuParam == "WiFissidString":
			WiFissidString = charString
		elif setMenuParam == "WiFiPassString":
			WiFiPassString = charString
		doSetWiFiParams()
	charString =""
		
def doSetWiFiParams():
	global charString, WiFissidString, WiFiPassString, setMenuParam
	print "into doSetWiFiParams WiFissidString:", WiFissidString,";  WiFiPassString:", WiFiPassString
	return 

# ------------------    ------------------ 
def powerOff():
	print " into powerOff" 
	#U.doReboot(1.," shut down at " +str(datetime.datetime.now())+"   button pressed",cmd="shutdown -h now ")
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
		time.sleep(1)
		#U.restartMyself(param=" restart requested", reason="",doPrint=True)
	return 

# ------------------    ------------------ 
def doReset():
	print " into doReset" 
	time.sleep(1)	
 
	if getPinValue("pin_Select") == 1:
		print "restart requested"
		time.sleep(1)
		#U.restartMyself(param=" restart requested", reason="",doPrint=True)

# ------------------    ------------------ 
def moveRight():
	print " into moveRight"
	while getPinValue("pin_Up") == 1:
		move(0.006, 2, 1, force = 10)
	return 

# ------------------    ------------------ 
def moveLeft():
	print " into moveLeft"
	while getPinValue("pin_Dn") == 1:
		move(0.006, 2, -1, force = 10)
	return 
# ------------------    ------------------ 
def set12():
	global amPM1224Update
	print " set to 24 hour clock"
	amPM1224Update = "24"
	return 
# ------------------    ------------------ 
def set24():
	global amPM1224Update
	print " set to 12 hour clock"
	amPM1224Update = "12"
	return 



# ------------------    ------------------ 
def doMenuUp(param):
	global displayMenuLevelActive 
	global displayPriority
	global charString 
	global amPM1224Update, amPM1224

	print " into doMenuUp", param

	displayMenuLevelActive -=1

	if displayMenuLevelActive < 0:
		displayPriority = 0
		displayMenuLevelActive =-1
		showStandardStatusDisplay(force=True)
	charString =""
	if param == "amPM" or param == "LED":
		updateParams()
		if amPM1224Update != amPM1224:
			doSunDialShutdown()
			U.restartMyself(param=" new AM pm setting", reason="",doPrint=True)
	return 


# ########################################
# #########    read /write params    #####
# ########################################

# ------------------    ------------------ 
def writeBackParams(data):

	print " writeBackParams"
	U.writeJson(G.homeDir+"temp/parameters",data,sort_keys=True, indent=2)
	U.writeJson(G.homeDir+"parameters",data,sort_keys=True, indent=2)

# ------------------    ------------------ 
def updateParams():
	global clockDict, inp, amPM1224, intensity, timeZone

	for devType in inp["output"]:
		if devType== "sunDial":
			for devId in inp["output"]["sunDial"]:
				#inp["output"]["sunDial"][devId ][0] = copy.copy(clockDict)
				inp["output"]["sunDial"][devId][0]["amPM1224"] 		= amPM1224
				inp["output"]["sunDial"][devId][0]["intensityMult"] = intensity["Mult"]
				inp["output"]["sunDial"][devId][0]["intensityMax"] 	= intensity["Max"]	
				inp["output"]["sunDial"][devId][0]["intensityMin"] 	= intensity["Min"]	
				inp["output"]["sunDial"][devId][0]["timeZone"] 		= timeZone

	writeBackParams(inp)

# ------------------    ------------------ 
def changedINPUT(theDict, key, lastValue, func):
	global anyInputChange
	if key not in theDict: return lastValue
	try: 	newV = func(theDict[key])
	except: return lastValue
	if lastValue != newV: anyInputChange = True
	return newV
		
# ------------------    ------------------ 
def dummy(a):
	return a


# ------------------    ------------------ 
def readParams():
	global sensor, output, inpRaw, inp, useRTC
	global speed, amPM1224,amPM1224Update, motorType
	global lastCl, timeZone, currTZ
	global oldRaw, lastRead
	global doReadParameters
	global gpiopinNumber
	global clockDictLast, clockDict
	global colPWM
	global speedOverWrite
	global SeqCoils
	global buttonDict, sensorDict
	global pinsToName, anyInputChange

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
		if "output"					in inp:	 output=			 			   (inp["output"])
		#### G.debug = 2 
		if G.program not in output:
			U.toLog(-1, G.program+ " is not in parameters = not enabled, stopping "+ G.program+".py" )
			exit()

		anyInputChange = False
		clock = output[G.program]
		for devId in  clock:
			clockDict		= clock[devId][0]
			if clockDictLast == clockDict: continue
			clockDictLast 	= clockDict


			#print clockDict
			if "timeZone"	 in clockDict:	
				if timeZone !=	(clockDict["timeZone"]):
					changed 	= max(2, changed)  
					timeZone 	= (clockDict["timeZone"])
					tznew  		= int(timeZone.split(" ")[0])
					if tznew != currTZ:
						U.toLog(-1, u"changing timezone from "+str(currTZ)+"  "+timeZones[currTZ+12]+" to "+str(tznew)+"  "+timeZones[tznew+12])
						os.system("sudo cp /usr/share/zoneinfo/"+timeZones[tznew+12]+" /etc/localtime")
						currTZ = tznew

			clockDict["timeZone"] = str(currTZ)+" "+ timeZones[currTZ+12]
				
			amPM1224 					= changedINPUT(clockDict, "amPM1224", 		amPM1224, 						dummy)
			amPM1224Update				= amPM1224
			intensity["Mult"] 			= changedINPUT(clockDict, "intensityMult", 	intensity["Mult"],				float)
			intensity["Max"] 			= changedINPUT(clockDict, "intensityMax", 	intensity["Max"],				float)
			intensity["Min"] 			= changedINPUT(clockDict, "intensityMin", 	intensity["Min"],				float)
			intensity["Mult"] 			= changedINPUT(clockDict, "intensityMult", 	intensity["Mult"],				float)

			speed						= changedINPUT(clockDict, "speed", 			speed,							float)
			if speedOverWrite >-1: speed = speedOverWrite
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
		minStayOn = 0.01
		if motorType.find("-1") >-1:
			SeqCoils.append([0, 0, 0, 0])  # off
			SeqCoils.append([0, 1, 1, 0])
			SeqCoils.append([0, 1, 0, 1])
			SeqCoils.append([1, 0, 0, 1])
			SeqCoils.append([1, 0, 1, 0])
		elif motorType.find("-2") >-1:
			print "motorType = ", motorType
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

	else:
		print " stopping  motorType not defined"
		exit()

	nStepsInSequence= len(SeqCoils) -1
	#print nStepsInSequence, SeqCoils
	return 

# ------------------    ------------------ 
def setgpiopinNumber():
	global gpiopinNumber, motorType, sensorDict, buttonDict, PIGPIO, pwmRange
	### GPIO pins ########
	motorType						= "bipolar-400-2-PIG"

	gpiopinNumber ={}
	gpiopinNumber["pin_CoilA1"] 	= 21 # blue
	gpiopinNumber["pin_CoilA2"] 	= 20 # pink
	gpiopinNumber["pin_CoilB1"] 	= 16 # yellow
	gpiopinNumber["pin_CoilB2"] 	= 12 # orange

	gpiopinNumber["pin_sensor0"] 	= 23
	gpiopinNumber["pin_sensor1"] 	= 24
	gpiopinNumber["pin_sensor2"] 	= 4
	gpiopinNumber["pin_sensor3"] 	= 17

	gpiopinNumber["pin_Up"] 		= 11
	gpiopinNumber["pin_Dn"] 		= 9
	gpiopinNumber["pin_Select"] 	= 10
	gpiopinNumber["pin_Exit"] 		= 22

	gpiopinNumber["pin_rgbLED"]		= [19,13,26]


	sensorDict			 = {}
	sensorDict["sensor"] = []
	sensorDict["sensor"].append({"ON":0,"pull":1,"lastCeck":0, "lastValue":-1,"newValue":-1,"clicked":"N", "left":[-1,-1,-1,-1,-1,-1,-1,-1,-1], "right":[-1,-1,-1,-1,-1,-1,-1,-1,-1], "status":-1}) 
	sensorDict["sensor"].append({"ON":0,"pull":1,"lastCeck":0, "lastValue":-1,"newValue":-1,"clicked":"N", "left":[-1,-1,-1,-1,-1,-1,-1,-1,-1], "right":[-1,-1,-1,-1,-1,-1,-1,-1,-1], "status":-1}) 
	sensorDict["sensor"].append({"ON":1,"pull":0,"lastCeck":0, "lastValue":-1,"newValue":-1,"clicked":"N", "left":[-1,-1,-1,-1,-1,-1,-1,-1,-1], "right":[-1,-1,-1,-1,-1,-1,-1,-1,-1], "status":0}) 
	sensorDict["sensor"].append({"ON":1,"pull":1,"lastCeck":0, "lastValue":-1,"newValue":-1,"clicked":"N", "left":[-1,-1,-1,-1,-1,-1,-1,-1,-1], "right":[-1,-1,-1,-1,-1,-1,-1,-1,-1], "status":0}) 
	sensorDict["sequence"]				= [0,1,1,1,1,0,0,0,0] # sensors firing when turning right in parts of 360/8: (0,1,2,3,4,5,6,7,8=360 )
																  # 4 magents every 1/8 of 360, 2 reed sensor at 0(#0-sensor0) and 180(#1=sensor1)
	sensorDict["currentSeqNumber"]		= -1 #  0,1,2,3,4,5,6,7,8
	sensorDict["currentSeqDirection"]	= 0  # -1,+1

	buttonDict				= {}
	for key in [ "pin_Up", "pin_Dn", "pin_Select", "pin_Exit"]:
		buttonDict[key] = {"lastCeck":0, "lastValue":-1,"newValue":-1}


	print "sensorDict", sensorDict
	print "buttonDict", buttonDict

	if not U.pgmStillRunning("pigpiod"): 	
		U.toLog(-1, "starting pigpiod", doPrint=True)
		os.system("sudo pigpiod -s 1 &")
		time.sleep(0.5)
		if not U.pgmStillRunning("pigpiod"): 	
			U.toLog(-1, " restarting myself as pigpiod not running, need to wait for timeout to release port 8888", doPrint=True)
			time.sleep(20)
			doSunDialShutdown
			U.restartMyself(reason="pigpiod not running")
			exit(0)

	PIGPIO = pigpio.pi()
	pwmRange = 1000


	defineGPIOout(gpiopinNumber["pin_CoilA1"])
	defineGPIOout(gpiopinNumber["pin_CoilA2"])
	defineGPIOout(gpiopinNumber["pin_CoilB1"])
	defineGPIOout(gpiopinNumber["pin_CoilB2"])


	defineGPIOout(gpiopinNumber["pin_rgbLED"][0], pwm=1)
	defineGPIOout(gpiopinNumber["pin_rgbLED"][1], pwm=1)
	defineGPIOout(gpiopinNumber["pin_rgbLED"][2], pwm=1)

	defineGPIOin("pin_Up",		event=True)
	defineGPIOin("pin_Dn",		event=True)
	defineGPIOin("pin_Select",	event=True)
	defineGPIOin("pin_Exit",	event=True)
	pinsToName[gpiopinNumber["pin_Up"]]		= "pin_Up"
	pinsToName[gpiopinNumber["pin_Dn"]]		= "pin_Dn"
	pinsToName[gpiopinNumber["pin_Select"]]	= "pin_Select"
	pinsToName[gpiopinNumber["pin_Exit"]]		= "pin_Exit"


	defineGPIOin("pin_sensor0", pull =sensorDict["sensor"][0]["pull"] )
	defineGPIOin("pin_sensor1", pull =sensorDict["sensor"][1]["pull"] )
	defineGPIOin("pin_sensor2", pull =sensorDict["sensor"][2]["pull"] )
	defineGPIOin("pin_sensor3", pull =sensorDict["sensor"][3]["pull"] )

	defineMotorType()


	return 


# ########################################
# #########    masic GPIO funtions  ######
# ########################################

# ------------------    ------------------ 
def defineGPIOin(pinName, event= False, pull=1):
	global PIGPIO
	pin = gpiopinNumber[pinName]
	if pin <=1: return 
	try:
		#print " defineGPIOin ", pin, "pull: ", pull
		PIGPIO.set_mode( pin,  pigpio.INPUT )
		if pull==1:
			PIGPIO.set_pull_up_down( pin, pigpio.PUD_UP)
		else:
			PIGPIO.set_pull_up_down( pin, pigpio.PUD_DOWN)

		if event:
			#print " setup event for ", pin
			PIGPIO.callback(pin, pigpio.FALLING_EDGE, buttonPressed )	
			PIGPIO.set_glitch_filter(pin, 30000) # steady for 30 msec 

	except	Exception, e:
		U.toLog(-1, u"in Line '%s' has error='%s'" % (sys.exc_traceback.tb_lineno, e), doPrint=True)
	return

# ------------------    ------------------ 
def defineGPIOout(pin, pwm = 0,freq =1000):
	global PIGPIO, pwmRange, colPWM
	# print "defineGPIOout", pin, pwm, freq
	try:
		PIGPIO.set_mode( pin, pigpio.OUTPUT )
		if pwm !=0:
			PIGPIO.set_PWM_frequency( pin, pwmRange )
			PIGPIO.set_PWM_range( pin, pwmRange )
			PIGPIO.set_PWM_dutycycle( pin, 0 )
	except	Exception, e:
		U.toLog(-1, u"in Line '%s' has error='%s'" % (sys.exc_traceback.tb_lineno, e), doPrint=True)
	return




# ------------------    ------------------ 
def setGPIOValue(pin,val,amplitude =-1):
	global PIGPIO, pwmRange
	pin = int(pin)
	if amplitude == -1:
		PIGPIO.write( pin, val )
	else:
		if amplitude >0 and val !=0:
			PIGPIO.set_PWM_dutycycle( (pin), int(pwmRange*amplitude/100.) )
			#print "setGPIOValue ", pin, val,amplitude, int(pwmRange*amplitude/100.), PIGPIO.get_PWM_dutycycle(int(pin)) 
		else:
			PIGPIO.write( (pin), 0 )
			#PIGPIO.set_PWM_dutycycle( int(pin), 0)
	return

# ------------------    ------------------ 
def getPinValue(pinName,pin=-1, ON = 1):
	global gpiopinNumber, PIGPIO

	if pin ==-1:
		if pinName not in gpiopinNumber: return -1
		if gpiopinNumber[pinName] < 1:   return -1
		pin = gpiopinNumber[pinName]

	if ON == 0: 
		ret = ( PIGPIO.read(pin) -1) * (-1)
	else: 
		ret =  PIGPIO.read(pin)
	return ret


# ########################################
# #########  moving functions ############
# ########################################
 
# ------------------    ------------------ 
def makeStep(seq, only2=False):
	global gpiopinNumber
	global SeqCoils
	if only2 and sum(SeqCoils[seq]) == 1: 
		return False
	#print "makeStep", seq, SeqCoils[seq]
	setGPIOValue(gpiopinNumber["pin_CoilA1"], SeqCoils[seq][0])
	setGPIOValue(gpiopinNumber["pin_CoilA2"], SeqCoils[seq][1])
	setGPIOValue(gpiopinNumber["pin_CoilB1"], SeqCoils[seq][2])
	setGPIOValue(gpiopinNumber["pin_CoilB2"], SeqCoils[seq][3])
	return True


# ------------------    ------------------ 
def setMotorOFF():
	global motorType
	makeStep(0)
	return


 
# ------------------    ------------------ 
def move(stayOn, steps, direction, force = 0, stopIf=[False,False], updateSequence=False, inFixMode=0 ):
	global lastStep
	global gpiopinNumber
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
	#print "steps, direction, stayOn, force, stopIf, updateSequence, inFixMode ", steps,  direction, stayOn, force, stopIf, updateSequence, inFixMode
	steps = int(steps)
	iSteps= 0

	getSensors()
	last1 = sensorDict["sensor"][1]["status"]
	last0 = sensorDict["sensor"][0]["status"]
	for i in range(steps):

		if updateSequence: 
			 determineSequenceNo(totalSteps+iSteps)

		if (sensorDict["sensor"][2]["status"] == 1  or sensorDict["sensor"][3]["status"] == 1 ) and  inFixMode==0:
			if sensorDict["sensor"][2]["status"] == 1:	writeFixMode( 1)
			if sensorDict["sensor"][3]["status"] == 1:	writeFixMode(-1)
			print " fixing  starting due to:", sensorDict["sensor"][2]["status"], sensorDict["sensor"][3]["status"]
			doSunDialShutdown()
			U.restartMyself(reason="need to fix boundaries #1")

		if sensorDict["sensor"][2]["status"] == 1  and  inFixMode == -1:
			return iSteps
		if sensorDict["sensor"][3]["status"] == 1  and  inFixMode ==  1:
			return iSteps


		if not updateSequence or ( currentSequenceNo < 8 and sensorDict["sensor"][0] == 1 ):
			if i >= force: 
				if last0 != sensorDict["sensor"][0]["status"] and sensorDict["sensor"][0]["status"] == 1 and stopIf[0]: 
					return iSteps
				if last1 != sensorDict["sensor"][1]["status"] and sensorDict["sensor"][1]["status"] == 1 and stopIf[1]: 
					return iSteps

		if currentSequenceNo == 8 and sensorDict["sensor"][0] == 1:
			if i >= force: 
				if last0 != sensorDict["sensor"][0]["status"] and sensorDict["sensor"][0]["status"] == 1 and stopIf[0]: 
					return iSteps
				if last1 != sensorDict["sensor"][1]["status"] and sensorDict["sensor"][1]["status"] == 1 and stopIf[1]: 
					return iSteps

		last1 = sensorDict["sensor"][1]["status"]
		last0 = sensorDict["sensor"][0]["status"]

		iSteps += 1
		lStep += direction

		if   lStep >= len(SeqCoils):	lStep = 1
		elif lStep <  1: 				lStep = len(SeqCoils)-1

	 	lastStep = lStep
		if makeStep(lStep, only2=(inFixMode!=0)):
			time.sleep(stayOn)
		getSensors()

###			print " not sleeping"

	getSensors()
	if (sensorDict["sensor"][2]["status"] == 1 or sensorDict["sensor"][3]["status"]== 1) and inFixMode ==0:
		if sensorDict["sensor"][2]["status"] == 1:	writeFixMode( 1)
		if sensorDict["sensor"][3]["status"] == 1:	writeFixMode(-1)
		print " fixing 2  starting due to:", sensorDict["sensor"][2], sensorDict["sensor"][3]
		doSunDialShutdown()
		U.restartMyself(reason="need to fix boundaries #2" )

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

	lasttotalSteps = totalSteps
	nextTotalSteps 	= min( int( secSinMidnit2 / waitBetweenSteps), maxStepsUsed )
	if nextTotalSteps != totalSteps:
		nextStep    = nextTotalSteps - totalSteps 

		if nextStep <0:	dir = -1
		else:			dir =  1

		if False and printON: print "secSinMidnit 2 ", "%.2f"%secSinMidnit, "H",hour, "M",minute, "S",second, "dt %.5f"%(time.time()-t0), "nstep",nextStep, "totSteps",totalSteps,"currentSequenceNo", currentSequenceNo,"inbetweenSequences", inbetweenSequences

		if nextStep != 0: 
			if speed > 10 or nextStep >5: stayOn =0.001
			else:		                  stayOn =0.01
			if lasttotalSteps < 10: force = 10 
			else:					force = 0
			#print "dir, nextStep", dir, nextStep
			if currentSequenceNo < 7: force = 750
			steps = move(stayOn, int( abs(nextStep) ), dir, force = force, updateSequence=True)
			if currentSequenceNo == 8 and sensorDict["sensor"][0]["status"] == 1:
				nextStep =0
			setColor()

		totalSteps += nextStep

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

	stayOn = 0.006

	maxSteps = int(stepsIn360+2)

	# check if we start at 0 left or right
	getSensors()
	#  sensorDict["pin_sensor0"]["status"]

	print " \n starting left right \n"
	drawDisplayLines(["starting left right","determing limits", datetime.datetime.now().strftime("%a, %Y-%m-%d %H:%M")])

	steps 		= 0
	stepsTotal	= 0
	oneEights = int(stepsIn360 /8.)+10
	pp = False
	if pp: print "0000 ===", steps, 0, sensorDict["sensor"][0], "--",sensorDict["sensor"][1]
	while True:
		# THIS IS THE EASIEST SIMPLE CASE:
		if sensorDict["sensor"][1]["status"] == 1:
			steps = move(stayOn, oneEights*6  , -1, force=30, stopIf = [True,False] )
			if pp: print "0100 ===", steps,-1, sensorDict["sensor"][0], "--",sensorDict["sensor"][1]
			break

		# THIS IS THE MOST DIFFICULT, SOMEWHERE CLOSE TO 0 OR 24:
		elif sensorDict["sensor"][0]["status"] == 1:
			#test if still on when moving right
			steps = move(stayOn, 10  , 1, force=11, stopIf = [False,False] )
			#print "0200 ===", steps, 1, sensorDict["sensor"][0], "--",sensorDict["sensor"][1]

			if sensorDict["sensor"][0]["status"] == 0:
				steps = move(stayOn, oneEights*8  , 1, force=6, stopIf = [True,True] )
				if pp: print "0201 ===", steps, 1, sensorDict["sensor"][0], "--",sensorDict["sensor"][1]

				if sensorDict["sensor"][0]["status"] == 1:
					steps = move(stayOn, oneEights*10, -1, force=6, stopIf = [False,True] )
					if pp: print "0202 ===", steps, 1, sensorDict["sensor"][0], "--",sensorDict["sensor"][1]


				if sensorDict["sensor"][1]["status"] == 1:
					steps = move(stayOn, oneEights*8  ,-1, force=6, stopIf = [True,False] )
					if pp: print "0203 ===", steps, -1, sensorDict["sensor"][0], "--",sensorDict["sensor"][1]
					break


			if sensorDict["sensor"][0]["status"] == 1:
				steps = move(stayOn, oneEights*8  , -1, force=6, stopIf = [False,True] )
				if pp: print "0210 ===", steps, -1, sensorDict["sensor"][0], "--",sensorDict["sensor"][1]


			if sensorDict["sensor"][1]["status"] == 0:
				steps = move(stayOn, oneEights*6 , 1, force=30, stopIf = [True,True] )
				if pp: print "0211 ===", steps, 1, sensorDict["sensor"][0], "--",sensorDict["sensor"][1]
				if sensorDict["sensor"][1]["status"] == 1:
					steps = move(stayOn, oneEights*6 , -1, force=30, stopIf = [True,False] )
					if pp: print "0212 ===", steps, -1, sensorDict["sensor"][0], "--",sensorDict["sensor"][1]
					break

				if sensorDict["sensor"][0]["status"] == 1:
					steps = move(stayOn, oneEights*6 , -1, force=30, stopIf = [False,True] )
					if pp: print "0230 ===", steps, -1, sensorDict["sensor"][0], "--",sensorDict["sensor"][1]
					steps = move(stayOn, oneEights*6 , -1, force=30, stopIf = [True,False] )
					break

			if sensorDict["sensor"][1]["status"] == 1:
				# found a midle, just continue to 0
				steps = move(stayOn, oneEights*6  , -1, force=30, stopIf = [True,False] )
				if pp: print "0300 ===", steps, -1, sensorDict["sensor"][0], "--",sensorDict["sensor"][1]
				break


		else:
			steps = move(stayOn, 5  , 1, force=6, stopIf = [True,False] )
			if pp: print "1000 ===", steps, 1, sensorDict["sensor"][0], "--",sensorDict["sensor"][1]
			if sensorDict["sensor"][1]["status"] == 0 and sensorDict["sensor"][1]["status"] == 0:
				steps = move(stayOn, oneEights*5  , 1, force=2, stopIf = [True,True] )
				if pp: print "1100 ===", steps, 1, sensorDict["sensor"][0], "--",sensorDict["sensor"][1]

			if sensorDict["sensor"][1]["status"] == 1:
				steps = move(stayOn, oneEights*6 , -1, force=30, stopIf = [True,False] )
				if pp: print "1200 ===", steps, -1, sensorDict["sensor"][0], "--",sensorDict["sensor"][1]
				break

			if sensorDict["sensor"][0]["status"] == 1:
				steps = move(stayOn, oneEights*3 , -1, force=5, stopIf = [True,True] )
				if pp: print "1300 ===", steps, -1, sensorDict["sensor"][0], "--",sensorDict["sensor"][1]
				if sensorDict["sensor"][0]["status"] == 1:
					steps = move(stayOn, oneEights*8 ,  -1, force=30, stopIf = [False,True] )
					if pp: print "1310 ===", steps, -1, sensorDict["sensor"][0], "--",sensorDict["sensor"][1]
					steps = move(stayOn, oneEights*8 , -1, force=30, stopIf = [True,False] )
					if pp: print "1311 ===", steps, -1, sensorDict["sensor"][0], "--",sensorDict["sensor"][1]
					break
					# done

				elif sensorDict["sensor"][1]["status"] == 1:
					steps = move(stayOn, oneEights*8, -1, force=10, stopIf = [True,False] )
					if pp: print "1320 ===", steps, -1, sensorDict["sensor"][0], "--",sensorDict["sensor"][1]
					break
					# done

				elif sensorDict["sensor"][0]["status"] == 0:
					steps = move(stayOn, oneEights*8 , -1, force=30, stopIf = [True,True] )
					if pp: print "1340 ===", steps, -1, sensorDict["sensor"][0], "--",sensorDict["sensor"][1]
					if sensorDict["sensor"][1]["status"] == 1:
						steps = move(stayOn, oneEights*8 , -1, force=10, stopIf = [False,True] )
						break

					steps = move(stayOn, oneEights*5 , -1, force=30, stopIf = [True,False] )
					if pp: print "11341 ===", steps, -1, sensorDict["sensor"][0], "--",sensorDict["sensor"][1]
					break
		print " no sensors found"
		time.sleep(1000)
		return 
	if getLightSensorValue(force=True): setColor(force=True)

	drawDisplayLines(["confirming"," left-right limits", datetime.datetime.now().strftime("%a, %Y-%m-%d %H:%M")])

	sensorDict["sensor"][0]["left"][0]  = 0
	## now we are at start
	## do full 360:
	pp = False
	print "\n finding limits"
	seqN       = 0
	stepsTotal = 0
	if  sensorDict["sensor"][0]["status"] == 1:
		sensorDict["sensor"][0]["right"][0]  = 0
	for nn in range(len(sensorDict["sequence"])-1):
		steps = move(stayOn, oneEights*6,  1, force=20, stopIf = [True,True] )
		stepsTotal += steps
		seqN +=1
		if pp: print "right ===", nn,  steps, sensorDict["sensor"][0], "--",sensorDict["sensor"][1]
		if  sensorDict["sensor"][1]["status"] == 1:
			sensorDict["sensor"][1]["right"][seqN]  = stepsTotal
		if  sensorDict["sensor"][0]["status"] == 1:
			sensorDict["sensor"][0]["right"][seqN]  = stepsTotal
	rightLimit = stepsTotal
	drawDisplayLines(["right limit set","confirming left limit", datetime.datetime.now().strftime("%a, %Y-%m-%d %H:%M")])
	if pp: print "right limit set","confirming left limit", datetime.datetime.now().strftime("%a, %Y-%m-%d %H:%M")
	if getLightSensorValue(force=True): setColor(force=True)

	stepsTotal = 0
	seqN       = 8
	if  sensorDict["sensor"][0]["status"] == 1:
		sensorDict["sensor"][0]["left"][seqN]  = rightLimit - 0
	for nn in range(len(sensorDict["sequence"])-1):
		steps = move(stayOn, int(oneEights*2), -1, force=20, stopIf = [True,True] )
		stepsTotal += steps
		seqN -=1
		if pp: print "left  ===", nn,  steps, sensorDict["sensor"][0], "--",sensorDict["sensor"][1]
		if  sensorDict["sensor"][1]["status"] == 1:
			sensorDict["sensor"][1]["left"][seqN]  = rightLimit - stepsTotal
		if  sensorDict["sensor"][0]["status"] == 1:
			sensorDict["sensor"][0]["left"][seqN]  = rightLimit - stepsTotal

	leftLimit = stepsTotal
	
	if getLightSensorValue(force=True): setColor(force=True)


	if pp: print sensorDict
	if abs(rightLimit + leftLimit) > stepsIn360*2:
		addToBlinkQueue(text=["S","O","S"])

	time.sleep(0.1)

	maxStepsUsed  = max(1,rightLimit)

	if amPM1224 =="24":	waitBetweenSteps 	= secondsTotalInDay     / maxStepsUsed 
	else: 				waitBetweenSteps 	= secondsTotalInHalfDay / maxStepsUsed 
	currentSequenceNo = 0
	print "waitBetweenSteps", waitBetweenSteps, "maxStepsUsed",maxStepsUsed
	drawDisplayLines(["wait and nSteps:","%d, %d"%(waitBetweenSteps,maxStepsUsed), datetime.datetime.now().strftime("%a, %Y-%m-%d %H:%M")])

	return 




# ########################################
# #########     blinks  ##########
# ########################################

def addToBlinkQueue(text =[], color=[1,1,1], stop = False, end=False, restore = True):
	global blinkThread, stopBlink


	if stop: 
		stopBlink =True
		time.sleep(1)
		print" clear queue bf " ,blinkThread["queue"].qsize() 
		blinkThread["queue"].queue.clear()
		print" clear queue af",blinkThread["queue"].qsize() 
		stopBlink =True
		return 

	if end: 
		stopBlink =True
		time.sleep(1)
		print" clear queue bf " ,blinkThread["queue"].qsize() 
		blinkThread["queue"].queue.clear()
		print" clear queue af",blinkThread["queue"].qsize() 
		blinkThread["thread"].join()
		return 

	add ={}
	if blinkThread["color"]   : add["color"] = color
	add["text"]    = text
	add["restore"] = restore
	stopBlink  = False
	blinkThread["queue"].put(add) 


def blinkQueue():
	global blinkThread, stopBlink

	while True:
		while not blinkThread["queue"].empty():
			#print" checking queue size", actionQueue.qsize() 
			action = blinkThread["queue"].get()
			doBlink(action) 
			if blinkThread["end"]:
				sys.exit()
			if stopBlink: break
		if LastHourColorSetToRemember !=[]:
			setColor( blink=0, color = LastHourColorSetToRemember, force = False)
		if blinkThread["end"]:
			sys.exit()
		time.sleep(1)
	sys.exit()



# ########################################
# #########     LED  funtions ############
# ########################################

# ------------------    ------------------ 
def doBlink(action):
	global stopBlink
	stopBlink = False
	if "text" not in action: return 
	blinkLetters(action["text"], [1,1,1])

# ------------------    ------------------ 
def setColor( blink=0, color = [1.,1.,1.], force = False):
	global colPWM, LastHourColorSet, secSinMidnit, LastHourColorSetToRemember, timeAtlastColorChange
	global gpiopinNumber

	lastC = LastHourColorSet

	if stopBlink: return 
	if blink !=0 : 
		for p in range(len(gpiopinNumber["pin_rgbLED"])):
			pin = gpiopinNumber["pin_rgbLED"][p]
			if  blink ==1: 
				if color[p] >= 0:
					setGPIOValue( pin, 1, amplitude= getIntensity(100*color[p]))
			elif blink == -1: 
				setGPIOValue( pin, 1,  amplitude=getIntensity(0) )

		LastHourColorSet = -1


	else:
		if abs(secSinMidnit-lastC) > 30  and (time.time() - timeAtlastColorChange) >10 or force:
			cm = timeToColor(secSinMidnit)
			for p in range(len(gpiopinNumber["pin_rgbLED"])):
				pin = gpiopinNumber["pin_rgbLED"][p]
				intens = getIntensity(cm[p]*color[p]) 
				setGPIOValue( pin, 1, amplitude=intens)	
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
			addToBlinkQueue(text =["o","n"], color=[1,1,1], stop = False, end=False, restore = True)
	return 

# ------------------    ------------------ 
def blinkLetters(letters, color):
	global morseCode
	global longBlink, shortBlink, breakBlink
	global stopBlink
	for l in letters:
		if l in morseCode:
			for sig in morseCode[l]:
				if sig ==1:	blink(longBlink,  breakBlink, 1, color)
				else:   	blink(shortBlink, breakBlink, 1, color)
			time.sleep(breakBlink)
	return

# ------------------    ------------------ 
def blink(on, off, n, color):
	global stopBlink
	for i in range(n):
		if stopBlink: return 
		setColor(blink= 1, color=color)
		time.sleep(on)	
		if stopBlink: return 
		setColor(blink=-1, color=color)
		time.sleep(off)	
	return 


# ------------------    ------------------ 
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

# ------------------    ------------------ 
def getLightSensorValue(force=False):
	global lightSensorValue, lastlightSensorValue, lastTimeLightSensorValue, lastTimeLightSensorFile, lightSensorValueRaw
	try:
		tt0 = time.time()
		if ( tt0 - lastTimeLightSensorValue  < 2) and not force:	return False
		if not os.path.isfile(G.homeDir+"temp/lightSensor.dat"):	return False
		rr , raw = U.readJson(G.homeDir+"temp/lightSensor.dat")
		if rr == {}:
			time.sleep(0.1)
			rr, raw = U.readJson(G.homeDir+"temp/lightSensor.dat")
		os.system("sudo rm "+G.homeDir+"temp/lightSensor.dat")
		if rr =={} or "time" not in rr: 							return False
		tt = float(rr["time"])
		if tt == lastTimeLightSensorFile:						 	return False
		lastTimeLightSensorFile = tt
		lightSensorValueREAD = float(rr["light"])
		sensor = rr["sensor"]
		if sensor == "i2cTSL2561":
			maxRange = 15000.
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
		lightSensorValue = (lightSensorValueRaw*5 + lastlightSensorValue*4) / 9.
		lastTimeLightSensorValue = tt0
		print "lightSensorValue2 ", lightSensorValueRaw, lightSensorValue, lastlightSensorValue, lightSensorValueREAD, maxRange
		lastlightSensorValue = lightSensorValue
		return True
	except	Exception, e:
		U.toLog(-1, u"in Line '%s' has error='%s'" % (sys.exc_traceback.tb_lineno, e)+"   bad sensor data", doPrint=True)
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

#
# ------------------    ------------------ 
def getSensors():
	global 	sensorDict
	anyChange = False
	for n in range(len(sensorDict["sensor"])): # 90,1 = reed swithes 0/12 oClock,  2,3 are boundary switches
		newValue = getPinValue( "pin_sensor"+str(n), ON=sensorDict["sensor"][n]["ON"] )
		#print "getSensors:   pin_sensor"+str(n), newValue
		if newValue != sensorDict["sensor"][n]["newValue"]:
			sensorDict["sensor"][n]["lastValue"]	= sensorDict["sensor"][n]["newValue"]
			sensorDict["sensor"][n]["clicked"]		= "Y"
			sensorDict["sensor"][n]["newValue"]		= newValue

			if newValue == 1:
				sensorDict["sensor"][n]["status"]	= 1
			else:
				if n < 3: # only for reed switches, the boundary switches are rest by the test pgm
					sensorDict["sensor"][n]["status"]	= 0
	

		out =""
		for ii in range(3):
			out += str(ii)+":" + str(sensorDict["sensor"][ii]["newValue"])+", "+ str(sensorDict["sensor"][ii]["status"])+", "+ str(sensorDict["sensor"][ii]["pull"])+";  ==  "
		#print "getSensors:  sensorDict sensors ",out
 
			
	return 
			
# ------------------    ------------------ 
def writeFixMode(fixMode):
	U.writeJson(G.homeDir+"sunDial.fixMode", {"fixMode":fixMode})

# ------------------    ------------------ 
def readFixMode():
	fixMode= False
	zz, raw = U.readJson(G.homeDir+"sunDial.fixMode")
	if "fixMode" in zz:
		return zz["fixMode"]
	return 	False

# ------------------    ------------------ 
def fixBoundaries(inFixMode):
	global sensorDict
	global stepsIn360


	print " fixing 3 turns starting due to:",inFixMode,  "3",  sensorDict["sensor"][2]["status"],"4", sensorDict["sensor"][3]["status"]
	sensorDict["sensor"][2]["status"] = 0
	sensorDict["sensor"][3]["status"] = 0
	move(0.006, stepsIn360*3, inFixMode, force=stepsIn360*3, stopIf=[False,False],  updateSequence=False, inFixMode=inFixMode)
	print " fixing  after 1:",inFixMode,  "2", sensorDict["sensor"][2]["status"],"3", sensorDict["sensor"][3]["status"]

	if inFixMode == -1:
		if sensorDict["sensor"][2]["newValue"] == 1:
			sensorDict["sensor"][2]["status"] = 0
			print " fixing  after 2: +1 dir 1.1 turns"
			move(0.006, int(stepsIn360*1.1),  1, force=stepsIn360*3, stopIf=[False,False],  updateSequence=False, inFixMode=1)
			getSensors()
			print " fixing  after 2.1:  ", "3",sensorDict["sensor"][2]["status"], "4",sensorDict["sensor"][3]["status"]
	else:
		if sensorDict["sensor"][3]["newValue"] == 1:
			sensorDict["sensor"][3]["status"] = 0
			print " fixing  after 3: -1 dir 1.1 turns"
			move(0.006, int(stepsIn360*1.1), -1, force=stepsIn360*3, stopIf=[False,False],  updateSequence=False, inFixMode=-1)
			print " fixing  after 3.1:",inFixMode, "2",sensorDict["sensor"][2]["status"], "3",sensorDict["sensor"][3]["status"]
			getSensors()

	if sensorDict["sensor"][2]["newValue"] == 0: sensorDict["sensor"][2]["status"] = 0
	if sensorDict["sensor"][3]["newValue"] == 0: sensorDict["sensor"][3]["status"] = 0

	if  sensorDict["sensor"][2]["status"]==0 and sensorDict["sensor"][3]["status"]==0: 
		writeFixMode(0)
		return 

	if sensorDict["sensor"][2]["status"] == 1:	writeFixMode( 1)
	if sensorDict["sensor"][3]["status"] == 1:	writeFixMode(-1)
	print " fixing  redo due to:",  "3",sensorDict["sensor"][2]["status"], "4",sensorDict["sensor"][3]["status"]
	doSunDialShutdown()
	U.restartMyself(reason="need to fix boundaries #3")


# ------------------    ------------------ 
def doSunDialShutdown():
	try: clearDisplay(show=True,force=True)
	except: pass
	try:	setMotorOFF()
	except: pass
	return 

# ------------------    ------------------ 
def checkNumberOfRestarts():
	try:
		restarts = -1
		if not os.path.isfile(G.homeDir+"temp/" + G.program+".restarts"): 
			os.system("echo '"+str(restarts+1)+"'  > "+ G.homeDir+"temp/" + G.program+".restarts")
			return 

		f = open(G.homeDir+"temp/" + G.program+".restarts")
		try:    restarts = int(f.read())
		except: restarts =0
		f.close()

		os.system("echo '"+str(restarts+1)+"'  > "+ G.homeDir+"temp/" + G.program+".restarts")

		if restarts > 10:
			os.system("echo  'sundial_hung restart master' > "+G.homeDir+"temp/restartNeeded")
			return

	except	Exception, e:
		U.toLog(-1, u"checkNumberOfReststarts in Line '%s' has error='%s'" % (sys.exc_traceback.tb_lineno, e)+"   bad sensor data", doPrint=True)
	return 


# ########################################
# #########    web   funtions ############
# ########################################
 #######################################
# #########       main        ##########
# ######################################

global clockDict, clockLightSet, useRTC
global sensor, output, inpRaw
global oldRaw,	lastRead, inp
global timeZones, timeZone
global doReadParameters
global networkIndicatorON
global lastStep, colPWM,  LastHourColorSet
global intensity
global maxStepsUsed, startSteps, stepsIn360, nStepsInSequence
global speed, amPM1224,amPM1224Update, motorType, adhocWeb
global gpiopinNumber, SeqCoils
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
global blinkThread, stopBlink
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
global lastExpireDisplay


morseCode= {"A":[0,1], 		"B":[1,0,0,0],	 "C":[1,0,1,0], "D":[1,0,0], 	"E":[0], 		"F":[0,0,1,0], 	"G":[1,1,0],	"H":[0,0,0,0], 	"I":[0,0],
			"J":[0,1,1,1], 	"K":[1,0,1], 	"L":[0,1,0,0], 	"M":[1,1], 		"N":[1,0], 		"O":[1,1,1], 	"P":[0,1,1,0],	"Q":[1,1,0,1], 	"R":[0,1,0],
			"S":[0,0,0], 	"T":[1], 		"U":[0,0,1], 	"V":[0,0,0,1], 	"W":[0,1,1], "X":[1,0,0,1], 	"%Y":[1,0,1,1], 	"Z":[1,1,0,0],
			"0":[1,1,1,1,1], "1":[0,1,1,1,1], "2":[0,0,1,1,1], "3":[0,0,0,1,1], "4":[0,0,0,0,1], "5":[0,0,0,0,0], "6":[1,0,0,0,0], "7":[1,1,0,0,0], "8":[1,1,1,0,0], "9":[1,1,1,1,0],
			"s":[0], # one short
			"l":[1], # one long
			"b":[0,0,0,1]}  # beethoven ddd DAAA

lastExpireDisplay		= time.time()
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
amPM1224Update			= amPM1224
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
	

checkNumberOfRestarts()

startDisplay()

drawDisplayLines(["Status:   starting up",".. read params, time..",  datetime.datetime.now().strftime("%a, %Y-%m-%d %H:%M")])


setgpiopinNumber()

setupTimeZones()
#print "current tz:", currTZ,JulDelta,JanDelta,NowDelta, timeZones[currTZ+12], timeZones

if readParams() ==3:
		U.toLog(-1," parameters not defined", doPrint=True)
		U.checkParametersFile("parameters-DEFAULT-sunDial", force = True)
		time.sleep(20)
		doSunDialShutdown()
		U.restartMyself(param=" bad parameters read", reason="",doPrint=True)


setMotorOFF()

getTime()


U.echoLastAlive(G.program)


print "gpiopinNumber", gpiopinNumber



stopBlink	= False
blinkThread = {"color":True, "stop":False, "end":False, "queue": Queue.Queue(), "thread": threading.Thread(name=u'blinkQueue', target=blinkQueue, args=())}	
blinkThread["thread"].start()



### here it starts 
lightSensorValue = 0.1
getLightSensorValue(force=True)
setColor(force=True)



## check if out of boundary, if yes: fix it 
fixmode =readFixMode()
if fixmode !=0:
	print "in FIX boundary mode"
	drawDisplayLines(["Status:     ","in FIX boundary mode",  datetime.datetime.now().strftime("%a, %Y-%m-%d %H:%M")])
	addToBlinkQueue(text=["s","o","s"])
	fixBoundaries(fixmode)
	


#addToBlinkQueue(text = ["S","T","A","R","T"][1,1,1],)
#time.sleep(3)

drawDisplayLines(["Status:     finding",".. L/R  Stop-Limits",  datetime.datetime.now().strftime("%a, %Y-%m-%d %H:%M")])

leftLimit 			= 0
rightLimit 			= 800
maxStepsUsed  		= rightLimit
waitBetweenSteps 	= secondsTotalInDay     / maxStepsUsed 
findLeftRight()



getLightSensorValue(force=True)
setColor(force=True)

sleepDefault = waitBetweenSteps/(5*speed)


print "clock starting;   waitBetweenSteps", waitBetweenSteps, "speed", speed, "totalSteps",totalSteps,"sleepDefault", sleepDefault,"amPM1224",amPM1224,"secSinMidnit2",secSinMidnit2
print "intensity", intensity

nextStep = 1

U.getIPNumber() 
eth0IP, wifi0IP, G.eth0Enabled, G.wifiEnabled = U.getIPCONFIG()

print "eth0IP, wifi0IP, G.eth0Enabled, G.wifiEnabled", eth0IP, wifi0IP, G.eth0Enabled, G.wifiEnabled
if not G.eth0Enabled and not G.wifiEnabled:
	U.setStartAdhocWiFi()

U.setStartwebserverSTATUS()
U.setStartwebserverINPUT()
updatewebserverStatus(status="starting")


showStandardStatusDisplay(force=True)

expireDisplay = 50
lastExpireDisplay = time.time()

while True:
			
	getTime()

	lastMove = time.time()
	nextStep = testIfMove( waitBetweenSteps, nextStep )

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
	#print "	sleep ", sleep," nextMove", nextMove,"minSleep",minSleep,"tt", time.time()

	while ii >0:
		if getLightSensorValue():
			setColor(force=True)
		elif (  abs(lightSensorValueRaw-lightSensorValue) / (max (0.005,lightSensorValueRaw+lightSensorValue))  ) > 0.05: 
				lightSensorValue = (lightSensorValueRaw*5 + lightSensorValue*4) / 9.
				setColor(force=True)

		ii -= 1
		time.sleep(minSleep)
		slept += minSleep

		if U.checkifRebooting(): doSunDialShutdown()


		tt = time.time()
		if tt >= endSleep: break
		if tt - lastDisplay  > 5:	
			lastDisplay = tt
			if tt - lastExpireDisplay < expireDisplay:
				showStandardStatusDisplay()
				#print "main loop showStandardStatusDisplay"
			else:
				#print "main loop clear display"
				displayMenuSubAreaActive = -2
				clearDisplay(show = True)

			readParams()

		

	
stopBlink	= True
time.sleep(1)
blinkThread["thread"].join


		

