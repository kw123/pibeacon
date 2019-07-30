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
charCommandsW.append([" exit submenu",				"doMenueExit(setMenuParam)"] )

charCommandsS=[]
for ii in range(len(ALLCHARACTERS)):
	charCommandsS.append([" "+ALLCHARACTERS[ii],	"addChar('"+ALLCHARACTERS[ii]+"')"])
	charCommandsS.append(["  ..delete last Char",	"deleteLastChar()"])
	charCommandsS.append(["  ..save and exit",		"doSaveMenu(setMenuParam)"])
charCommandsS.append([" exit submenu",				"doMenueExit(setMenuParam)"] )


##               top option               selection, command
MENUSTRUCTURE =[[],[]]
MENUSTRUCTURE[0]=[	
					[" Info @ http:",			"setMenuParam=''"],
					[" 12 or 24 clock",			"setMenuParam=''"],
					[" mode light vs shadow",	"setMenuParam=''"],
					[" light ON/off",			"setMenuParam=''"],
					[" light off",				"setMenuParam=''"],
					[" set position",			"setMenuParam=''"],
					[" demo speed",				"setMenuParam=''"],
					[" reset",					"setMenuParam=''"],
					[" restart",				"setMenuParam=''"],
					[" light intensity",		"setMenuParam=''"],
					[" light max",				"setMenuParam=''"],
					[" light min",				"setMenuParam=''"],
					[" light Sens max",			"setMenuParam=''"],
					[" light Sens min",			"setMenuParam=''"],
					[" adhoc Wifi",				"setMenuParam=''"],
				]
#					[" WiFi SID",				"setMenuParam='WiFissidString'"],
#					[" WiFi Passwd",			"setMenuParam='WiFiPassString'"],
#				]
#                         [menu text          ,  function to call ],  [ , ],  [ , ]   ..
MENUSTRUCTURE[1]=[	
					[	[" http:ip#",""], 										[" update..", ""											],	[" ip#:8010",""]												],
					[	[" 12",   				"set1224(12)"],					[" 24", 					"set1224(24)"					],																	], 
					[	[" normal SunDial",		"setSunMode('normal shadow')"],	[" Sun straight down",	"setSunMode('light straight down')"	],																	],
					[	[" always on",   		"setLightOff(0,0)"],			[" off",   					"setLightOff(0,24)"				],																	], 
					[	[" 0-6",   				"setLightOff(0,6)"],			[" 23-6",   				"setLightOff(23,6)"				],	[" 0-7",   "setLightOff(0,7)"], [" 23-7", 	"setLightOff(23,7)"]], 
					[	[" set to correct position", "setOffset()"], 			[" then press and hold ", 	"setOffset()"					],	[" SELECT for 2secs ", 	"setOffset()"]							],
					[	[" normal", "setSpeed(1)"],								[" demo speed slow",		"setSpeed(55)"					],	[" demo speed fast", "setSpeed(400)"], 							],
					[	[" clock reset",		"doReset()"], 																																					],
					[	[" system", 			"doRestart()"],																																					], 
					[	[" increase",   		"increaseLEDSlope()"],			[" decrease", 	"decreaseLEDSlope()"						],																	], 
					[	[" increase",   		"increaseLEDmax()"],			[" decrease", 	"decreaseLEDmax()"							],																	], 
					[	[" increase",   		"increaseLEDmin()"],			[" decrease", 	"decreaseLEDmin()"							],																	], 
					[	[" increase",   		"increaselightSensMax()"],		[" decrease", 	"decreaselightSensMax()"					],																	], 
					[	[" increase",   		"increaselightSensMin()"],		[" decrease", 	"decreaselightSensMin()"					],																	], 
					[	[" start",   			"setAdhocWiFi('start')"],		[" stop",		"setAdhocWiFi('stop')"						],																	], 
				]

#						charCommandsS,				
#						charCommandsW
#				]
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


			self.displayCommand(
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

			self.displayClear()
			self.displayShow()

		except IOError as e:
			raise IOError(e.errno, "Failed to initialize SH1106 display driver")

	def displayImage(self, image):
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
			self.displayCommand(page, 0x02, 0x10)
			page += 1

			buf = []
			for x in range(self.width):
				byte = 0
				for n in range(0, step, self.width):
					byte |= (pix[x + y + n] & 0x01) << 8
					byte >>= 1

				buf.append(byte)

			self.displayData(buf)



	def displayCommand(self, *cmd):
		"""
		Sends a command or sequence of commands through to the
		device - maximum allowed is 32 bytes in one go.
		"""
		assert(len(cmd) <= 32)
		self.bus.write_i2c_block_data(self.addr, self.cmd_mode, list(cmd))

	def displayData(self, data):
		"""
		Sends a data byte or sequence of data bytes through to the
		device - maximum allowed in one transaction is 32 bytes, so if
		data is larger than this it is sent in chunks.
		"""
		for i in range(0, len(data), 32):
			self.bus.write_i2c_block_data(self.addr, self.data_mode, list(data[i:i+32]))

	def displayShow(self):
		"""
		Sets the display mode ON, waking the device out of a prior
		low-power sleep mode.
		"""
		self.displayCommand(self.DISPLAYON)

	def displayHide(self):
		"""
		Switches the display mode OFF, putting the device in low-power
		sleep mode.
		"""
		self.displayCommand(self.DISPLAYOFF)

	def displayClear(self):
		"""
		Initializes the device memory with an empty (blank) image.
		"""
		self.displayImage(PIL.Image.new('1', (self.width, self.height)))

# ------------------    ------------------ 
def displayStart():
	global outputDev, displayFont
	global lineCoordinates, lineCoordDeltaY, lastLines
	global xPixels, yPixels
	global displayPriority, waitForDisplayToRest
	global draw, imData
	global displayMenuLevelActive, displayMenuAreaActive, displayMenuSubAreaActive
	global charString, WiFissidString, WiFiPassString, setMenuParam

	try:
		xPixels 				= 128
		yPixels 				= 64
		lineCoordDeltaY			= [0,0,32,25,16,13]
		lineCoordinates			= [[],[],[],[],[],[]]
		lineCoordinates[2] 		= [(0,+2),(0,lineCoordDeltaY[2]*1+2)]
		lineCoordinates[3] 		= [(0,+2),(0,lineCoordDeltaY[3]*1+2),(4,lineCoordDeltaY[3]*2+2)]
		lineCoordinates[4] 		= [(0,+2),(0,lineCoordDeltaY[4]*1+2),(0,lineCoordDeltaY[4]*2+2),(0,lineCoordDeltaY[4]*3+2)]
		lineCoordinates[5] 		= [(0,+2),(0,lineCoordDeltaY[5]*1+2),(0,lineCoordDeltaY[5]*2+2),(0,lineCoordDeltaY[5]*3+2),(0,lineCoordDeltaY[5]*4+2)]
		lastLines 				= ["","","","","","","",""]
		displayPriority    		= 0
		waitForDisplayToRest	= 60.
		displayMenuLevelActive	= -1
		displayMenuAreaActive	= -1
		displayMenuSubAreaActive= 0
		charString				= ""
		WiFissidString			= ""
		WiFiPassString			= ""
		setMenuParam			= ""

		outputDev				= sh1106(width=xPixels, height=yPixels)

		displayFont 			= ImageFont.load_default()
		imData					= PIL.Image.new('1', (xPixels,yPixels))
		draw 					= ImageDraw.Draw(imData)
	except Exception, e:
		U.logger.log(40, u"Line {} has error={}".format(sys.exc_traceback.tb_lineno, e))
	return

# ------------------    ------------------ 
def displaySetPriority(level=0):
	global displayPriority
	displayPriority = level

# ------------------    ------------------ 
def displayReSetPriority():
	global displayPriority
	displayPriority = 0

# ------------------    ------------------ 
def displayReservePriority():
	global displayPriority
	displayPriority = 5

# ------------------    ------------------ 
def displayDrawLines( lines, clear=True, prio=0, inverse=False, show=True, force =False):
	global outputDev, displayFont
	global lineCoordinates, lastLines
	global xPixels, yPixels, imData, draw
	global displayPriority, waitForDisplayToRest
	global displayStarted

	try:
		nLines = len(lines)

		if not displayStarted: return 
		#print "displayDrawLines", lines, nLines, clear, prio, inverse, show, displayPriority

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
			displayClear(prio=prio, inverse=inverse, force=force)

		if inverse: fill =0
		else: 		fill =255

		#print "displayDrawLines draw"
		for ii in range(len(lines)):
			draw.text(lineCoordinates[nLines][ii], lines[ii],  font=displayFont, fill=fill)

		if show: displayDoShowImage()
	except Exception, e:
		U.logger.log(40, u"Line {} has error={}".format(sys.exc_traceback.tb_lineno, e))
	return 

# ------------------    ------------------ 
def displayDrawLine( line, iLine=1, nLines=3, focus=False, prio=0, inverse=False):
	global outputDev, displayFont
	global lineCoordinates, lastLines
	global xPixels, yPixels, imData, draw
	global displayPriority, waitForDisplayToRest
	global displayStarted

	try:
		if not displayStarted: return 

		if displayPriority > 0: 
			if time.time() - displayPriority > waitForDisplayToRest:
				displayPriority = 0
	
		if prio < displayPriority: return 
		displayPriority = prio 


		if focus:	fill = 0
		else: 		fill = 255

		#print "drawDisplayLine", line, iLine, nLines, focus, prio, inverse, fill
		displayClear((lineCoordinates[nLines][iLine][0], lineCoordinates[nLines][iLine][1]-2, xPixels,  lineCoordinates[nLines][iLine][1] +lineCoordDeltaY[nLines]-2), prio=prio, inverse=inverse  )
		draw.text(lineCoordinates[nLines][iLine], line,  font=displayFont, fill=fill)
	except Exception, e:
		U.logger.log(40, u"Line {} has error={}".format(sys.exc_traceback.tb_lineno, e))
	
	return 

#
# ------------------    ------------------ 
def displayClear( area=[], prio=0, inverse=False, show=False, force=False):
	global outputDev, displayFont
	global lineCoordinates, lastLines
	global xPixels, yPixels, imData, draw
	global displayPriority, waitForDisplayToRest
	global lastLines
	global displayStarted

	try:
		if not displayStarted: return 

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
		if show: displayDoShowImage()
	except Exception, e:
		U.logger.log(40, u"Line {} has error={}".format(sys.exc_traceback.tb_lineno, e))
	return

# ------------------    ------------------ 
def displayComposeMenu(useLevel, area, subArea, nLines):
	global setMenuParam, charString
	global displayStarted

	try:
		if not displayStarted: return 

		lines =[]
		top   = MENUSTRUCTURE[0]
		U.logger.log(20,"useLev:{}, aerea:{}, subA:{}, nLines:{}, top[area][0]:s{}".format(useLevel, area, subArea, nLines, top[area][0]) )

		displayClear(prio=time.time()+100)
		if useLevel== 0:
			start = max(0, min(area, len(top) - nLines) )
			end   = min(area+nLines, len(top) )
			nn =-1
			for ii in range(start, end):
				nn +=1
				if ii == area:
	#				lines.append(  str(area)+" "+str(level)+"  "+str(subarea)+" x "+str(MENUSTRUCTURE[level][ii])  )
					displayDrawLine( str(top[ii][0]) , iLine=nn, nLines=nLines,  prio=time.time()+100, focus=True, inverse=True)
				else:
					displayDrawLine( str(top[ii][0]), iLine=nn, nLines=nLines, prio=time.time()+100)

		if useLevel == 1:
			short2 = MENUSTRUCTURE[1][area]
			if subArea < len(short2):
				start = max(0, min(subArea, len(short2) - nLines) )
				if charString =="":
					end   = min(subArea+nLines-1, len(short2) )
				else:
					end   = min(subArea+nLines-2, len(short2) )
				displayDrawLine( top[area][0][0:20]+" ==>" , iLine=0, nLines=nLines, prio=time.time()+100, )
				nn=0
				U.logger.log(20, "start:{},  end:{},  setMenuParam:{},  str:{}".format(start, end, setMenuParam, charString) )
				for ii in range(start, end):
					nn+=1
					if ii == subArea:
						displayDrawLine( str(short2[ii][0]), iLine=nn, nLines=nLines, prio=time.time()+100, focus=True, inverse=True )
					else:
						displayDrawLine( str(short2[ii][0]), iLine=nn, nLines=nLines, prio=time.time()+100)
				if charString !="":
					displayDrawLine(charString, iLine=nn+1, nLines=nLines, prio=time.time()+100)
		displayDoShowImage()
	except Exception, e:
		U.logger.log(40, u"Line {} has error={}".format(sys.exc_traceback.tb_lineno, e))
	return 

# ------------------    ------------------ 
def displayComposeMenu0():
	global displayMenuLevelActive, displayMenuAreaActive, displayMenuSubAreaActive
	global displayStarted
	if not displayStarted: return 
	if displayMenuLevelActive ==0:	nLines = 4
	else:							nLines = 5
	displayComposeMenu(displayMenuLevelActive, displayMenuAreaActive, displayMenuSubAreaActive, nLines)
	displayDoShowImage()

# ------------------    ------------------ 
def displayDoShowImage():
	global imData, outputDev
	global displayStarted
	if not displayStarted: return 
	outputDev.displayImage(imData)


# ------------------    ------------------ 
def displayShowStandardStatus(force=False):
	global overallStatus, totalStepsDone, maxStepsUsed, sensorDict, amPM1224
	try:
		displayDrawLines(["St:{}; Clk:{}".format(overallStatus, amPM1224), "@ Pos.: {}/{}".format(totalStepsDone,maxStepsUsed),  "IP#:{}".format(G.ipAddress),  "Wifi:{};".format(getWifiInfo(longShort=1)),   datetime.datetime.now().strftime("%a, %Y-%m-%d %H:%M")])
		updatewebserverStatus("normal")
	except Exception, e:
		U.logger.log(40, u"Line {} has error={}".format(sys.exc_traceback.tb_lineno, e))
	return 
# ------------------    ------------------ 
def displayShowShutDownMessage():
	displayDrawLines(["shutting down...","Save to disconnect","  power in 30 secs", datetime.datetime.now().strftime("%a, %Y-%m-%d %H:%M"),""], clear=True, force=True, show=True)

# ------------------    ------------------ 
def displayShowStatus2(force=True):
	global overallStatus, totalStepsDone, maxStepsUsed, sensorDict
	displayDrawLines(["Web INFO:","  {}".format(G.ipAddress),"Web ENTRY:","  {}:8001".format(G.ipAddress),"", datetime.datetime.now().strftime("%a, %Y-%m-%d %H:%M")], clear=True, force=force, show=True)

# ------------------    ------------------ 

def getWifiInfo(longShort=0):
	global eth0IP, wifi0IP

	labels = [["o","off"],["A","active"],["P","search"],["I","adhoc"]]
	wifiInfo = labels[0][longShort]
	try:
		if G.wifiType == "adhoc":
			wifiInfo = labels[3][longShort]
		elif G.wifiEnabled:
			if wifi0IP !="":
				wifiInfo = labels[1][longShort]
			else:
				wifiInfo = labels[2][longShort]
	except Exception, e:

		U.logger.log(40, u"Line {} has error={}".format(sys.exc_traceback.tb_lineno, e))
	return wifiInfo

# ------------------    ------------------ 
def updatewebserverStatus(status):
	global amPM1224
	global lightSensorValue, lightSensNorm, intensityRGB
	global numberOfStepsCableAllows, stepsIn360, maxStepsUsed, totalStepsDone, offsetOfPosition, zeroPosition
	global leftBoundaryOfCable, rightBoundaryOfCable, numberOfStepsCableAllows
	global sensorDict
	global intensityMax, intensityMin, intensitySlope

	try: 
		statusData		= []

		statusData.append( "SunDial Current status" )
		statusData.append( "update-time..... = {}".format(datetime.datetime.now().strftime(u"%H:%M:%S")) )
		statusData.append( "IP-Number....... = {}".format(G.ipAddress))
		statusData.append( 'set params at... = click on: <a href="http://{}:8010" style="color:rgb(255,255,255)">{}:8010 </a>'.format(G.ipAddress,G.ipAddress))
		statusData.append( "WiFi enabled.... = {} - id={}".format(getWifiInfo(longShort=1), G.wifiID) )
		statusData.append( "opStatus........ = {}".format(status ) )
		statusData.append( " ")
		statusData.append( "12/24 mode...... = {}".format(amPM1224) )
		statusData.append( "shadow/SUN mode. = {}".format(lightShadowVsDown) )
		statusData.append( " ")
		statusData.append( "intensity....... = slope:{:.2f}, Min:{:.4f}, Max:{:.1f}".format(intensitySlope, intensityMin, intensityMax)  )
		statusData.append( "norm RGB........ = {:.0f}, {:.0f}, {:.0f}".format(intensityRGB[0]*100, intensityRGB[1]*100, intensityRGB[2]*100)  )
		statusData.append( "multiply RGB.... = {:.0f}, {:.0f}, {:.0f}".format(multiplyRGB[0]*100, multiplyRGB[1]*100, multiplyRGB[2]*100)  )
		statusData.append( "Light CurrVal... = {:.3f} sensor value".format(lightSensorValue) )
		statusData.append( "Light SensNorm.. = {} (light = sensValue/norm)".format(lightSensNorm) )
		statusData.append( "Light Max....... = {} Sensor range".format(lightSensMax) )
		statusData.append( "Light Min....... = {} Sensor range".format(lightSensMin) )
		cc = timeToColor(secSinceMidnit)
		statusData.append( "currentColor.... = R:{:.1f}, G:{:.1f}, B:{:.1f}".format(cc[0]*100, cc[1]*100, cc[2]*100) )
		statusData.append( " ")
		statusData.append( "Steps max Cable. = {}".format(numberOfStepsCableAllows ) )
		statusData.append( "Steps in 360.... = {}".format(stepsIn360 ) )
		statusData.append( "maxStepsUsed.... = {} from 0 to 24/12".format(maxStepsUsed) )
		statusData.append( "at Step Now..... = {}".format(totalStepsDone) )
		statusData.append( "offset.......... = {}".format(offsetOfPosition) )
		statusData.append( "zeroPosition.... = {}".format(zeroPosition) )
		statusData.append( "leftBoundary.... = {}".format(leftBoundaryOfCable) )
		statusData.append( "rightBoundary... = {}".format(rightBoundaryOfCable) )
		statusData.append( "delta Boundary.. = {}".format(numberOfStepsCableAllows) )
		statusData.append( " ")
		statusData.append( "Sensor 0........ = {}".format(sensorDict["sensor"][0]["clicked"]) )
		statusData.append( "Sensor 12....... = {}".format(sensorDict["sensor"][1]["clicked"]) )
		statusData.append( "Sensor 0 marksR. = {}".format(unicode(sensorDict["sensor"][0]["right"]).replace("[","").replace("]","").replace(" ","").replace("-1","-")) )
		statusData.append( "Sensor 0 marksL. = {}".format(unicode(sensorDict["sensor"][0]["left"]).replace("[","").replace("]","").replace(" ","").replace("-1","-")) )
		statusData.append( "Sensor 12 marksR.= {}".format(unicode(sensorDict["sensor"][1]["right"]).replace("[","").replace("]","").replace(" ","").replace("-1","-")) )
		statusData.append( "Sensor 12 marksL.= {}".format(unicode(sensorDict["sensor"][1]["left"]).replace("[","").replace("]","").replace(" ","").replace("-1","-")) )
		statusData.append( "Sensor LineChk1. = {}".format(sensorDict["sensor"][2]["clicked"]) )
		statusData.append( "Sensor LineChk2. = {}".format(sensorDict["sensor"][3]["clicked"]) )

		U.logger.log(10, u"web status update:{}".format(statusData) )

		U.updateWebStatus(json.dumps(statusData) )
	except Exception, e:
		U.logger.log(40, u"Line {} has error={}".format(sys.exc_traceback.tb_lineno, e))

def removebracketsetc(data):
	out = unicode(data).replace("[","").replace("]","").replace(" ","")


def readCommand():
	global lastPosition, gpiopinNumbers, zeroPosition, rememberPostionInCommand, offsetOfPosition, totalStepsDone, amPM1224, lightShadowVsDown, secSinceMidnit0, stepsIn360
	global timeShift, intensitySlope, multiplyRGB
	try:
		if not os.path.isfile(G.homeDir+"temp/sundial.cmd"): return 

		f=open(G.homeDir+"temp/sundial.cmd","r")
		cmds = f.read().strip()
		f.close()
		os.system("rm  "+ G.homeDir+"temp/sundial.cmd > /dev/null 2>&1 ")

		if len(cmds) < 2: return 
		rememberPostionInCommand  = lastPosition
		cmds = cmds.lower().replace(" ","").strip(";")
	### cmds: =["go0","getBoundaries","doLR","RGB:"]
		U.logger.log(20, u"cmds: >>{}<<".format(cmds))

		cmds = cmds.split(";")
		for cmd in cmds:
			cmd =cmd.strip()

			if cmd.find("start") > -1:
				nSteps = totalStepsDone
				if nSteps < 0: 	dir =-1
				else:			dir = 1
				U.logger.log(20, u"go to 0: = -totalStepsDone:{}".format(totalStepsDone))
				move( abs(nSteps),  dir)

			elif cmd.find("zero") > -1:
				nSteps = lastPosition-zeroPosition
				if nSteps < 0: 	dir =-1
				else:			dir = 1
				U.logger.log(20, u"go to 0: = -zeroPosition:{} ; nSteps:{}; totsteps:{}".format(zeroPosition,nSteps,totalStepsDone))
				totalStepsDone += nSteps
				move( abs(nSteps),  dir)

			elif cmd.find("lightSensNorm") > -1:
				cmd = cmd.split(":")
				if len(cmd) != 2: continue
				try:    cmd = float(cmd[1])
				except: continue
				if cmd < 1000: continue
				U.logger.log(20, u"adjusting light sensor normalization factor:{} from: ".format(lightSensNorm),cmd)
				lightSensNorm = cmd

			elif cmd.find("hh:") > -1:
				cmd = cmd.split(":")
				if len(cmd) != 2: continue
				try:    cmd = float(cmd[1])
				except: continue
				hh = cmd
				if amPM1224 ==12: 	hh *=2
				hh %= 24
				nSteps = int(float(hh * maxStepsUsed) /24) - totalStepsDone
				if nSteps < 0: 	dir =-1
				else:			dir = 1
				U.logger.log(20, u"go to hour={} = steps:{} from :{}".format(hh, nSteps, totalStepsDone))
				totalStepsDone += nSteps
				move( abs(nSteps),  dir)

			elif cmd.find("now") > -1:
				nSteps = int(maxStepsUsed * float(secSinceMidnit )/(24*3600)) - totalStepsDone
				if nSteps < 0: 	dir =-1
				else:			dir = 1
				U.logger.log(20, u"go to now: sec={:.0f} = steps:{} ..  from :{}".format(secSinceMidnit, nSteps, totalStepsDone))
				totalStepsDone += nSteps
				move( abs(nSteps),  dir)

			elif cmd.find("steps:") >-1:
				cmd =cmd.split(":")
				if len(cmd) != 2: continue
				nSteps = int(cmd[1])
				if nSteps < 0: 	dir =-1
				else:			dir = 1
				U.logger.log(20, u"make steps: {} direction: {}, tot steps:{}".format(nSteps, dir, totalStepsDone))
				totalStepsDone += nSteps
				move( abs(nSteps),  dir)

			elif cmd.find("timesshift:")> -1:
				cmd = cmd.split(":")
				if len(cmd) != 2: continue
				try:    cmd = float(cmd[1])
				except: continue
				timeShift = float(cmd)*3600
				U.logger.log(20, u"time shift  hours:{}".format(cmd[1]))

			elif cmd.find("offsetArm:") >-1:
				cmd =cmd.split(":")
				if len(cmd) != 2: continue
				try:    cmd = int(cmd[1])
				except: continue
				if abs (cmd) > 1000: continue
				U.logger.log(20, u"setting arm offset to {}  from:{}".format(offsetOfPosition, cmd))
				offsetOfPosition = cmd
				saveParameters(force=True)
				stopLoop = False
				U.restartMyself(reason="with new position offset")

			elif cmd.find("calibrate:") >-1:
				cmd =cmd.split(":")
				if len(cmd) != 2: continue
				if cmd[1] == "currenttime":
					tt = int(secSinceMidnit)
				else:
					tt = int(float(cmd[1])*3600)
				rememberPos 	= lastPosition
				hh = int(tt/3600)
				U.logger.log(20, "setting offset .. w tt secs:{} = {:2d}:{:2d}, current ..  steps:{}; zero:{}, offset:{} .. doing LR".format(tt, hh, int(tt-hh*3600)/60, totalStepsDone, zeroPosition, offsetOfPosition))
				# this will move back to zero.. new zero will have the number of steps to 0 from correct postion
				findLeftRight()
				stepsBackToZero = rememberPos - zeroPosition 
				stepsShouldbe   =  int(   (float(tt * maxStepsUsed)) /(24.*3600)  )
				offsetOfPosition = int( stepsBackToZero -  stepsShouldbe ) 
				if 	offsetOfPosition   > stepsIn360: offsetOfPosition -= stepsIn360
				elif -offsetOfPosition > stepsIn360: offsetOfPosition += stepsIn360
				U.logger.log(20, "after left right, new zero:{}, stepsBackToZero:{}, stepsShouldbe:{}, new offset:{}".format(zeroPosition, stepsBackToZero, stepsShouldbe, offsetOfPosition))
				charString = "set off: {}".format(offsetOfPosition)
				displayComposeMenu0()
				time.sleep(2)
				saveParameters(force=True)
				stopLoop = False
				U.restartMyself(reason="with new position offset")

			elif cmd =="getboundaries":
				U.logger.log(20, u"force boundaries of cables:")
				findBoundariesOfCable(force=True)
				U.restartMyself(reason="after find boundaries", doPrint= True)

			elif cmd in ["leftrightcalibration", "dolr"]:
				U.logger.log(20, u"force LR:")
				findLeftRight()
				getOffset()

			elif cmd =="restart":
				U.logger.log(20, u"restart sundial:")
				U.restartMyself(reason="manual command", doPrint= True)
				time.sleep(20)

			elif cmd =="reset":
				U.logger.log(20, u"resetting parameters:")
				os.system("rm  "+ G.homeDir+"sunDial.parameters > /dev/null 2>&1 ")
				os.system("rm  "+ G.homeDir+"temp/sunDial.positions ")
				U.restartMyself(reason="reset request", doPrint= True)
				time.sleep(20)

			elif cmd.find("shutdown") >-1:
				U.logger.log(30, u"shutdown sundial")
				doSunDialShutdown()
				U.doReboot(20, "shutdown  requested", cmd="sudo sync; wait 2; sudo shutdown now")

			elif cmd.find("led:") >-1:
				cmd =cmd.split(":")
				if len(cmd) != 2: continue
				RGB = cmd[1].split(",")
				if cmd[1] == "up":
					intensitySlope *=1.5
				elif cmd[1] == "down":
					intensitySlope /=1.5
				elif cmd[1] == "off":
					lightOffBetweenHours[0] = 0
					lightOffBetweenHours[1] = 24
					U.logger.log(20, u"set LED off")
					setColor(force=True)
				elif cmd[1] == "on":
					lightOffBetweenHours[0] = 0
					lightOffBetweenHours[1] = 0
					U.logger.log(20, u"set LED ON")
					setColor(force=True)
				elif len(RGB) == 3:
					U.logger.log(20, u"set LED RGBmultiplier to {}".format(RGB) )
					for RGBNumber in range(len(gpiopinNumbers["pin_rgbLED"])):
						multiplyRGB[RGBNumber] = float(RGB[RGBNumber])/100.
					setColor(force=True)
				else:
					intensitySlope = float(cmd[1])
					intensitySlope = min(500.,max(intensitySlope, 0.1))
					setColor(force=True)
					U.logger.log(20, u"set LED multiplier to:{}".format(intensitySlope) )

			elif cmd.find("sleep:") >-1:
				cmd =cmd.split(":")
				if len(cmd) != 2: continue
				sleepTime = float(cmd[1])
				U.logger.log(20, u"sleep for {}".format(sleepTime) )
				time.sleep(sleepTime)

			elif cmd.find("mode") >-1:
				cmd =cmd.split(":")
				if len(cmd) != 2: continue
				if "shadow" in lightShadowVsDown and "shadow" in cmd[1]:	continue
				if "light"  in lightShadowVsDown and "light"  in cmd[1]:	 continue
				if amPM1224 == 12 				 and cmd[1] =="12": 		continue
				if amPM1224 == 24				 and cmd[1] =="24": 		continue
				if "shadow" in cmd[1]: 
					lightShadowVsDown = "normal shadow"
					charString = u"set {}".format(lightShadowVsDown)
					displayComposeMenu0()
					saveParameters(force=True)
					U.logger.log(20, u"set light to  {}".format(lightShadowVsDown))
					time.sleep(2)
					U.restartMyself(reason=" new sun setting")
				elif "shadow" in cmd[1]: 
					llightShadowVsDown = "light straight down"
					charString = u"set {}".format(lightShadowVsDown)
					displayComposeMenu0()
					saveParameters(force=True)
					U.logger.log(20, u"set light to  {}".format(lightShadowVsDown))
					time.sleep(2)
					U.restartMyself(reason=" new sun setting")
				else:
					cmd = int(cmd[1])
					if amPM1224 == cmd: 
						U.logger.log(20, u"set AMPM:{}  no change from :{} ".format(cmd, amPM1224))
						continue
					charString = u"set to AMPM {}".format(cmd)
					amPM1224 = cmd
					displayComposeMenu0()
					saveParameters(force=True)
					U.logger.log(20, u"set AMPM {} ".format(cmd))
					time.sleep(2)

			else:
				U.logger.log(20, u"cmds avail: \nrestart;reset;off;goStart;goNow;goZero;goHH:hh;goSteps:nn;\ntimeshift:hh;getBoundaries;leftrightcalibration;\nLED:on/off/up/down/x/r,g,b;lightSensNorm:xx;sleep:secs;mode:shadow/light/12/24;\ncalibrate:currrentTime/1/2/..24  no spaces, use ; between cmds" )
	except Exception, e:
		U.logger.log(40, u"Line {} has error={}".format(sys.exc_traceback.tb_lineno, e))
	return 
		

# ########################################
# #########   sensor events ############
# ########################################

# ------------------    ------------------ 
def boundarySensorEventGPIO(pin):
	global inFixBoundaryMode, currentlyMoving, limitSensorTriggered, lastPosition, findBoundaryMode, sensorDict
	global lastEventOfPin

	try:
		execboundarySensorEvent(pin)
	except Exception, e:
		U.logger.log(40, u"Line {} has error={}".format(sys.exc_traceback.tb_lineno, e))
	return

# ------------------    ------------------ 
def boundarySensorEventPIG(pin, level, tick):
	global inFixBoundaryMode, currentlyMoving, limitSensorTriggered, lastPosition, findBoundaryMode, sensorDict

	try:
		execboundarySensorEvent(pin)
	except Exception, e:
		U.logger.log(40, u"Line {} has error={}".format(sys.exc_traceback.tb_lineno, e))

	return

# ------------------    ------------------ 
def execboundarySensorEvent(pin):
	global inFixBoundaryMode, currentlyMoving, limitSensorTriggered, lastPosition, findBoundaryMode, sensorDict
	global lastEventOfPin

	try:		
		sensNumber = sensorDict["gpioToSensNumber"][pin]
		U.logger.log(20, "pin:{}, delta time:{:.2f}".format(pin, time.time() - lastEventOfPin[pin] ))
		if time.time() - lastEventOfPin[pin] < 0.5: 
			return 
		lastEventOfPin[pin] = time.time()

		getSensors()
		U.logger.log(20, "limitSensorTriggered sens#:{};  pin#{}, name:{}, timeSinceLastMove:{:.2f},   limitSensorTriggered:{}, inFixBoundaryMode:{}, sensSt2:{}, sensSt3:{}".format(sensNumber, pin, pinsToName[pin],time.time() - currentlyMoving,limitSensorTriggered,inFixBoundaryMode,sensorDict["sensor"][2]["status"],sensorDict["sensor"][3]["status"] ))

		if time.time() - currentlyMoving < 0.1:
			U.logger.log(20, "limitSensorTriggered .. currently moving, ignored, continue ")
			return 

		if inFixBoundaryMode !=0: 
			return # alread in fix mode
		if findBoundaryMode: 
			U.logger.log(20, "limitSensorTriggered .. currently in find cable boundaries, ignored, continue ")
			return 

		if (sensorDict["sensor"][2]["status"] == 1 or sensNumber ==2) and limitSensorTriggered != 1:	
			limitSensorTriggered = 1
			savePositions()
			saveFixBoundaryMode(set=1)
			U.restartMyself(reason="entering fixmode, trigger of left boundary", doPrint= True)
		if (sensorDict["sensor"][3]["status"] == 1 or sensNumber ==3) and limitSensorTriggered != -1:
			limitSensorTriggered = -1
			savePositions()
			saveFixBoundaryMode(set=-1)
			U.restartMyself(reason="entering fixmode, trigger of right boundary", doPrint= True)
	except Exception, e:
		U.logger.log(40, u"Line {} has error={}".format(sys.exc_traceback.tb_lineno, e))

	return
# ------------------    ------------------ 
# ------------------    ------------------ 


	

# ########################################
# #########   button funtions ############
# ########################################
# ------------------    ------------------ 

# ------------------    ------------------ 
def buttonPressedEventGPIO(pin):
	global gpiopinNumbers, pinsToName, displayPriority
	global displayMenuLevelActive, displayMenuAreaActive, displayMenuSubAreaActive
	global lastExpireDisplay
	global lastEventOfPin
	try:
		if pin not in pinsToName: 			return 
		U.logger.log(20, "pin:{}, delta time:{:.2f}".format(pin, time.time() - lastEventOfPin[pin] ))
		if time.time() - lastEventOfPin[pin] < 0.5: 
			return 
		lastEventOfPin[pin] = time.time()
		val = getPinValue(pinsToName[pin], ON=0)
		U.logger.log(20, "pin:{}  {}, val:{}, displ<enLevActive:{},  displayMenuAreaActive:{}, displayMenuSubAreaActive:{}".format(pin, pinsToName[pin], val, displayMenuLevelActive, displayMenuAreaActive, displayMenuSubAreaActive) )
		execbuttonPressedEvent(pin)

	except Exception, e:
		U.logger.log(40, u"Line {} has error={}".format(sys.exc_traceback.tb_lineno, e))
	return 

# ------------------    ------------------ 
def buttonPressedEventPIG(pin, level, tick):
	global gpiopinNumbers, pinsToName, displayPriority
	global displayMenuLevelActive, displayMenuAreaActive, displayMenuSubAreaActive
	global lastExpireDisplay
	global lastEventOfPin
	try:
		if pin not in pinsToName: 			return 
		U.logger.log(10, "pin:{}, level:{}, delta time:{:.2f}".format(pin, level, time.time() - lastEventOfPin[pin] ))
		if time.time() - lastEventOfPin[pin] < 0.1: 
			return 
		if level == 1:
			lastEventOfPin[pin] = time.time()+0.4
			return 
		execbuttonPressedEvent(pin)

	except Exception, e:
		U.logger.log(40, u"Line {} has error={}".format(sys.exc_traceback.tb_lineno, e))
	return 



# ------------------    ------------------ 
def execbuttonPressedEvent(pin):
	global gpiopinNumbers, pinsToName, displayPriority
	global displayMenuLevelActive, displayMenuAreaActive, displayMenuSubAreaActive
	global lastExpireDisplay
	global lastEventOfPin

	try:
		lastExpireDisplay = time.time() +20.

		if displayMenuLevelActive < -1:
			displayMenuLevelActive += 1
			if displayMenuLevelActive < 0:
				displayShowStandardStatus(force=True)
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
				U.logger.log(20, "action0:>{}<<".format(cmd) )
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
				displayComposeMenu0()

			elif displayMenuLevelActive == 1:
				displayMenuSubAreaActive += 1
				if displayMenuSubAreaActive >= len(MENUSTRUCTURE[1][displayMenuAreaActive]):
					displayMenuSubAreaActive = 0
				displayComposeMenu0()

			else:
				return 	

		elif pinsToName[pin] == "pin_Up": 
			if displayMenuLevelActive == 0:
				displayMenuAreaActive -= 1
				if displayMenuAreaActive < 0:
					displayMenuAreaActive = len(MENUSTRUCTURE[0])-1
				displayComposeMenu0()
			elif displayMenuLevelActive == 1:
				displayMenuSubAreaActive -= 1
				if displayMenuSubAreaActive < 0:
					displayMenuSubAreaActive = len(MENUSTRUCTURE[1][displayMenuAreaActive])-1
				displayComposeMenu0()
			else:
				return 	

		elif pinsToName[pin] == "pin_Exit":
			displayMenuLevelActive 		-= 1
			displayMenuSubAreaActive 	= -1

			if displayMenuLevelActive 	< 0:
				U.logger.log(20, "setting to normal display")
				displayPriority 		= 0
				displayMenuLevelActive 	= -1
				displayShowStandardStatus(force=True)

			elif displayMenuLevelActive == 0:
				displayComposeMenu0()


	except Exception, e:
		U.logger.log(40, u"Line {} has error={}".format(sys.exc_traceback.tb_lineno, e))
# ------------------    ------------------ 
# ------------------    ------------------ 
def doAction():
	global displayMenuLevelActive, displayMenuAreaActive, displayMenuSubAreaActive
	global setMenuParam

	try:
		U.logger.log(20, "(1) displayMenuLevelActive: {};  displayMenuAreaActive:{}; subArea:{}".format(displayMenuLevelActive, displayMenuAreaActive, displayMenuSubAreaActive))

		if displayMenuAreaActive < 0: return 

		if displayMenuLevelActive == 0:
			displayComposeMenu0()
			cmd = MENUSTRUCTURE[0][displayMenuAreaActive][1]
			U.logger.log(20, "action0:>>{}<<".format(cmd) )
			exec(cmd) 

		elif displayMenuLevelActive == 1:
			if displayMenuSubAreaActive < 0: return 
			displayComposeMenu0()
			cmd = MENUSTRUCTURE[1][displayMenuAreaActive][displayMenuSubAreaActive][1]
			U.logger.log(20, "action0:>>{}<<".format(cmd) )
			exec(cmd) 
			if displayMenuLevelActive == 0:
				displayComposeMenu0()
	except Exception, e:
		U.logger.log(40, u"Line {} has error={}".format(sys.exc_traceback.tb_lineno, e))
	
	return 
# ------------------    ------------------ 
def doMenueExit(param):
	global displayMenuLevelActive 
	global displayPriority
	global charString 
	global amPM1224

	try:
		U.logger.log(20, "(1) {}".format(param))

		displayMenuLevelActive -=1

		if displayMenuLevelActive < 0:
			displayPriority = 0
			displayMenuLevelActive =-1
			displayShowStandardStatus(force=True)

		if param == "off":
				doSunDialShutdown()
				U.doReboot(20, "shutdown pin pressed", cmd="sudo sync; wait 2; sudo shutdown now")
		if param == "reset":
				writeBackParams({})
				U.restartMyself(reason=" reset requested")
		if param == "restart":
				doSunDialShutdown()
				U.restartMyself(reason=" restart requested")
	except Exception, e:
		U.logger.log(40, u"Line {} has error={}".format(sys.exc_traceback.tb_lineno, e))
	return 


# ------------------    ------------------ 
def addChar(c):
	global charString, WiFissidString, WiFiPassString, setMenuParam
	charString +=c
	U.logger.log(20, "addChar charString %s   %s" %(c, charString))
	return 

# ------------------    ------------------ 
def deleteLastChar():
	global charString, WiFissidString, WiFiPassString, setMenuParam
	U.logger.log(20, "deleteLastChar")
	if len(charString)>0: charString = charString[0:-1]
	U.logger.log(20, "deleteLastChar charString %s" %charString)
	return 

# ------------------    ------------------ 
def doSaveMenu(param):
	global charString, WiFissidString, WiFiPassString, setMenuParam

	try:
		U.logger.log(20, " into doSaveMenu %s" %param)
		if param == "": return
		if param == setMenuParam:
			if   setMenuParam == "WiFissidString":
				WiFissidString = charString
			elif setMenuParam == "WiFiPassString":
				WiFiPassString = charString
			doSetWiFiParams()
		charString = ""
	except Exception, e:
		U.logger.log(40, u"Line {} has error={}".format(sys.exc_traceback.tb_lineno, e))
	return
		
# ------------------    ------------------
def doSetWiFiParams():
	global charString, WiFissidString, WiFiPassString, setMenuParam
	U.logger.log(20, "into doSetWiFiParams WiFissidString: %s    WiFiPassString: %s"%(WiFissidString,WiFiPassString))
	return

# ------------------    ------------------ 
def powerOff():
	U.logger.log(20, "into powerOff")
	#U.doReboot(1.," shut down at " +str(datetime.datetime.now())+"   button pressed",cmd="shutdown -h now ")
	return 



# ------------------    ------------------ 
# ------------------    ------------------ 
# ------------------    ------------------ 
# ------------------    ------------------ 
def changeValueButtonInput(nameString, name, maxV, minV, start, maxDelta, increasDecrease):
	global charString
	try:
		time.sleep(0.1)
		U.logger.log(20, "(1) name:{} pin V:{}, val:{}, max:{}, min:{}, delta{}, maxD:{}, up/Dn:{} ".format(nameString, getPinValue("pin_Select",ON=0, doPrint=True), name, maxV, minV, start, maxDelta, increasDecrease))
		delta = start
		name = min(maxV, max(minV, name+delta) )
		time.sleep(0.1)
		charString = "val = {}".format(name)
		displayComposeMenu0()
		for ii in range(40):
			if getPinValue("pin_Select", ON=0)==0: break
			U.logger.log(20, "pin_Select still pressed val:{}".format(name) )
			delta = min(maxDelta, delta*1.5)
			name = max(minV, min(maxV, name+delta*increasDecrease) )
			setColor(force=True)
			charString = "val = {}".format(name)
			displayComposeMenu0()
			time.sleep(0.3)
		U.logger.log(20, "exit  new:{}".format(name))
		time.sleep(2)
	except Exception, e:
		U.logger.log(40, u"Line {} has error={}".format(sys.exc_traceback.tb_lineno, e))
	charString =""
	return name
#------------------    ------------------ 
def increaseLEDSlope():
	global intensitySlope
	intensitySlope = changeValueButtonInput("increaseLEDSlope", intensitySlope, 5., 0.1, 0.02, 0.2, 1)
def decreaseLEDSlope():
	global intensitySlope
	intensitySlope = changeValueButtonInput("decreaseLEDSlope", intensitySlope, 5., 0.1, 0.01, 0.1, -1)
# ------------------    ------------------ 
def increaseLEDmax():
	global intensityMax
	intensityMax = changeValueButtonInput("increaseLEDmax", intensityMax, 1., 0.2, 0.01, 0.1, 1)
def decreaseLEDmax():
	global intensityMax
	intensityMax = changeValueButtonInput("decreaseLEDmax", intensityMax, 1., 0.2, 0.01, 0.05, -1)
# ------------------    ------------------ 
def increaseLEDmin():
	global intensityMin
	intensityMin = increaseValue("increaseLEDmin", intensityMin, 0.2, 0.001, 0.01, 0.05, 1)
def decreaseLEDmin():
	global intensityMin
	intensityMin = changeValueButtonInput("decreaseLEDmin", intensityMin, 0.2, 0.001, 0.01, 0.05, -1)
# ------------------    ------------------ 
def increaselightSensMax():
	global lightSensMax
	lightSensMax = changeValueButtonInput("increaselightSensMax", lightSensMax, 1., 0.2, 0.01, 0.1, 1)
def decreaselightSensMax():
	global lightSensMax
	lightSensMax = changeValueButtonInput("decreaselightSensMax", lightSensMax, 1., 0.2, 0.01, 0.05, -1)
# ------------------    ------------------ 
def increaselightSensMin():
	global lightSensMin
	lightSensMin = changeValueButtonInput("increaselightSensMin", lightSensMin, 0.05, 0.0001, 0.0001, 0.001, 1)
	return
def decreaselightSensMin():
	global lightSensMin
	lightSensMin = changeValueButtonInput("decreaselightSensMin", lightSensMin, 0.01, 0.0001, 0.0001, 0.001, -1)
# ------------------    ------------------ 
# ------------------    ------------------ 
# ------------------    ------------------ 

def setLightOff(off, on):
	global lightOffBetweenHours
	U.logger.log(20, "setting lights off at: {}; on at:{}".format(off,on))
	lightOffBetweenHours =[off,on]
	return 



# ------------------    ------------------ 
def setAdhocWiFi(setTo):
	global webAdhoc
	try:
		if webAdhoc == setTo: 
			U.logger.log(20, "change wifi not done, already set to {}".format(setTo))
			return
		time.sleep(2)
		if getPinValue("pin_Select", ON=0) == 0: 
			U.logger.log(20, "select not pressed for > 2secs")
			return

		webAdhoc = setTo
		if webAdhoc =="start":
			charString = "rebooting to wifiAdhoc"
			displayComposeMenu0()
			time.sleep(3)
			U.setStartAdhocWiFi()

		if webAdhoc =="stop":
			charString = "switching back to normal wifi"
			displayComposeMenu0()
			time.sleep(3)
			U.setStopAdhocWiFi()

	except Exception, e:
		U.logger.log(40, u"Line {} has error={}".format(sys.exc_traceback.tb_lineno, e))
	return 


# ------------------    ------------------ 
def setSunMode(setTo):
	global lightShadowVsDown
	global charString
	try:
		if lightShadowVsDown == setTo: 
			U.logger.log(20, "change light mode not changed alread set to {}".format(setTo))
			return
		time.sleep(2)
		if getPinValue("pin_Select", ON=0) == 0: 
			U.logger.log(20, "select not pressed for > 2secs")
			return
		lightShadowVsDown = setTo #  = (24*60*60)/2 #  = 1/2 day
		charString = "set to: {}".format(setTo)
		displayComposeMenu0()
		saveParameters(force=True)
		time.sleep(3)
		U.logger.log(20, "change light mode to {}".format(lightShadowVsDown))
		U.restartMyself(reason=" setSunModetoNormal")
	except Exception, e:
		U.logger.log(40, u"Line {} has error={}".format(sys.exc_traceback.tb_lineno, e))
	return 



# ------------------    ------------------ 
def doRestart():
	try:
		U.logger.log(20, " ")
		time.sleep(2)	
		if getPinValue("pin_Select", ON=0) == 0: 
			U.logger.log(20, "select not pressed for > 2secs")
			return
		U.logger.log(20, "restart requested")
		charString = "executing restart"
		displayComposeMenu0()
		time.sleep(2)
		saveParameters()
		#U.restartMyself(reason=" restart requested")
	except Exception, e:
		U.logger.log(40, u"Line {} has error={}".format(sys.exc_traceback.tb_lineno, e))
	return 

# ------------------    ------------------ 
def doReset():
	try:
		U.logger.log(20, "into doReset")
		time.sleep(2)	
		if getPinValue("pin_Select", ON=0) == 0: 
			U.logger.log(20, "select not pressed for > 2secs")
			return
		U.logger.log(20, "reset requested")
		os.system("rm  "+ G.homeDir+"sunDial.parameters > /dev/null 2>&1 ")
		os.system("rm  "+ G.homeDir+"temp/sunDial.positions ")
		charString = "executing reset"
		displayComposeMenu0()
		time.sleep(20)
		#U.restartMyself(reason=" restart requested")
	except Exception, e:
		U.logger.log(40, u"Line {} has error={}".format(sys.exc_traceback.tb_lineno, e))
	return 

# ------------------    ------------------ 
def setOffset():
	global lastPosition, zeroPosition, offsetOfPosition, stopLoop
	global charString
	try:
		U.logger.log(20, "(1) last zero:{}".format(zeroPosition))
		time.sleep(2)	
		if getPinValue("pin_Select", ON=0) == 0: 
			U.logger.log(20, "select not pressed for > 2secs")
			return
		stopLoop = True
		rememberZero = zeroPosition
		# this will kove back to zero.. new zero will have the numebr of steps to 0 fromcorrect postion
		U.logger.log(20, "(2) doing left right ")
		findLeftRight()
		offsetOfPosition = rememberZero - zeroPosition
		U.logger.log(20, "(2) after left right, new zero:{}, offset:{}".format(zeroPosition, offsetOfPosition))
		charString = "set to: {}".format(offsetOfPosition)
		displayComposeMenu0()
		time.sleep(2)
		saveParameters(force=True)
		stopLoop = False
		U.restartMyself(reason="with new position offset")
	except Exception, e:
		U.logger.log(40, u"Line {} has error={}".format(sys.exc_traceback.tb_lineno, e))
	return 
	return 

# ------------------    ------------------ 
def set1224(setTo):
	global amPM1224
	global charString
	try:
		if amPM1224 == int(setTo): 
			U.logger.log(20, "set 12/24 not changed, stay at{}".format(setTo))
			return 
		time.sleep(2)	
		if getPinValue("pin_Select", ON=0) == 0: 
			U.logger.log(20, "select not pressed for > 2secs")
			return
		U.logger.log(20, "set to hour clock:{}".format(setTo))
		amPM1224 = int(setTo)
		charString = "set to: {}".format(setTo)
		displayComposeMenu0()
		saveParameters(force=True)
		time.sleep(2)
		U.restartMyself(reason=" new AM pm setting")
	except Exception, e:
		U.logger.log(40, u"Line {} has error={}".format(sys.exc_traceback.tb_lineno, e))
	return 

# ------------------    ------------------ 
def setSpeed(setTo):
	global speed, speedDemoStart
	global charString
	try:
		setTo = int(setTo) 
		if speed == setTo: return 
		if speedDemoStart < 2 and setTo < 2: return 
		time.sleep(2)	
		if getPinValue("pin_Select", ON=0) == 0: 
			U.logger.log(20, "select not pressed for > 2secs")
			return
		speedDemoStart = time.time()
		if setTo > 0: U.logger.log(20, "set speed to ")
		charString = "set to: {}".format(setTo)
		displayComposeMenu0()
		time.sleep(2)
		U.restartMyself(reason="setting speed to", param= str(setTo))
	except Exception, e:
		U.logger.log(40, u"Line {} has error={}".format(sys.exc_traceback.tb_lineno, e))
	return 


# ########################################
# #########    read /write params    #####
# ########################################

# ------------------    ------------------ 
def writeBackParams(data):
	U.logger.log(10, "data:{}".format(data))
	U.writeJson(G.homeDir+"sunDial.parameters", data, sort_keys=True, indent=2)
	U.logger.log(10, "data written")
	data,raw  = U.readJson(G.homeDir+"sunDial.parameters")
	U.logger.log(10, "data read back:{}".format(data))





# ------------------    ------------------ 
def savePositions():
	global lastPosition, zeroPosition, maxStepsUsed
	data = {"lastPosition":lastPosition,"zeroPosition":zeroPosition,"maxStepsUsed":maxStepsUsed}
	U.writeJson(G.homeDir+"temp/sunDial.positions", data)

# ------------------    ------------------ 
def getPositions():
	global lastPosition, zeroPosition, maxStepsUsed, offsetOfPosition
	lastPosition = 0
	zeroPosition = 999999999
	
	data,raw  = U.readJson(G.homeDir+"temp/sunDial.positions")
	if data !={}: 
		try: lastPosition = int(data["lastPosition"])
		except: pass
		try: zeroPosition = int(data["zeroPosition"])
		except: pass
		try: maxStepsUsed =int( data["maxStepsUsed"])
		except: pass
		try: offsetOfPosition =int( data["offsetOfPosition"])
		except: pass


# ------------------    ------------------ 
def resetBoundariesOfCable():
	sunDialParameters["leftBoundaryOfCable"] = 0
	sunDialParameters["findBoundaryMode"] = 0
	sunDialParameters["numberOfStepsCableAllows"] = 0
	saveParameters(force=True)

# ------------------    ------------------ 
def findBoundariesOfCable(force=False):
	global  findBoundaryMode, rightBoundaryOfCable, leftBoundaryOfCable, limitSensorTriggered, stepsIn360, numberOfStepsCableAllows

	try:
		if not force:
			findBoundaryMode = False
			if numberOfStepsCableAllows != 0: return 

		findBoundaryMode = True
		limitSensorTriggered = 0
		U.logger.log(20,"finding boundaries of cable,  right then left....")
		for ii in range(3):
			U.logger.log(20,"finding boundaries, first right")
			resetSensors()
			rightBoundaryOfCable = move( 10,   -1, fast=False, updateSequence=False, stopIfBoundarySensor=[False,True])
			resetSensors()
			rightBoundaryOfCable = move( 9000,  1, fast=False, updateSequence=False, stopIfBoundarySensor=[False,True])
			U.logger.log(20,"finding boundaries, first found at:{}".format(rightBoundaryOfCable))
			if abs(rightBoundaryOfCable) > 5000: 
				os.system("rm  "+ G.homeDir+"sunDial.parameters ")
				os.system("rm  "+ G.homeDir+"temp/sunDial.positions ")
				U.restartMyself(reason="reset request", doPrint= True)
				time.sleep(10)
				continue
			resetSensors()
			limitSensorTriggered = 0
			U.logger.log(20,"right found:{};   finding boundaries, now left".format(rightBoundaryOfCable))
			leftBoundaryOfCable = move( 10,    1, fast=False, updateSequence=False, stopIfBoundarySensor=[True,False])
			if abs(rightBoundaryOfCable - leftBoundaryOfCable) > 5000: 
				os.system("rm  "+ G.homeDir+"sunDial.parameters  ")
				os.system("rm  "+ G.homeDir+"temp/sunDial.positions ")
				U.restartMyself(reason="reset request", doPrint= True)
				time.sleep(10)
				continue
			resetSensors()
			leftBoundaryOfCable = move( 6000, -1, fast=True, updateSequence=False, stopIfBoundarySensor=[True,False])
			U.logger.log(20,"finding boundaries, left found at:{}".format(leftBoundaryOfCable))
			resetSensors()
			limitSensorTriggered = 0
			numberOfStepsCableAllows = abs(rightBoundaryOfCable - leftBoundaryOfCable)
			if numberOfStepsCableAllows > stepsIn360 *2: break
			U.logger.log(20,"finding boundaries  not finished, left:{};  right:{};  delta:{} to small, try again".format(leftBoundaryOfCable, rightBoundaryOfCable, numberOfStepsCableAllows))

		U.logger.log(20,"finding boundaries finished, left:{};  right:{};  delta:{}".format(leftBoundaryOfCable, rightBoundaryOfCable, numberOfStepsCableAllows))
		saveParameters()
		U.logger.log(20,"finding boundaries moving right to ~ middle between left and right boundaries: {} steps, current step count:{}".format(int(numberOfStepsCableAllows*.6) -20, lastPosition))
		U.logger.log(20,"... before move call")
		limitSensorTriggered = 0
		resetSensors()
		retCode = move( int(numberOfStepsCableAllows*.6) -20, 1, stopIfBoundarySensor=[False,True])
		U.logger.log(20,"... after move current step count:{}, retCode={} ".format(lastPosition, retCode))
		resetSensors()
		limitSensorTriggered = 0
		saveFixBoundaryMode(set=0)
		findBoundaryMode = False
	except Exception, e:
		U.logger.log(40, u"Line {} has error={}".format(sys.exc_traceback.tb_lineno, e))
	return

# ------------------    ------------------ 
def resetSensors():
	global sensorDict
	try:
 		sensorDict["sensor"][2]["status"] = 0
		sensorDict["sensor"][3]["status"] = 0
		sensorDict["sensor"][2]["newValue"] = -1
		sensorDict["sensor"][3]["newValue"] = -1
		sensorDict["sensor"][2]["lastValue"] = -1
		sensorDict["sensor"][3]["lastValue"] = -1
	except Exception, e:
		U.logger.log(40, u"Line {} has error={}".format(sys.exc_traceback.tb_lineno, e))
	return 
# ------------------    ------------------ 
def saveParameters(force = False):
	global amPM1224, intensitySlope, intensityMax, intensityMin, lightSensMin, lightSensMax , lightSensNorm
	global timeZone, offsetOfPosition 
	global rightBoundaryOfCable, leftBoundaryOfCable, numberOfStepsCableAllows
	global lightShadowVsDown, inFixBoundaryMode, lastFixBoundaryMode
	global lightOffBetweenHours
	global lastsaveParameters, multiplyRGB
	global sunDialParameters

	if time.time() - lastsaveParameters < 100 and not force: return 
	lastsaveParameters = time.time()
	try:
		anyChange = 0
		anyChange += upINP("lightOffBetweenHours",		lightOffBetweenHours			) 
		anyChange += upINP("amPM1224",				amPM1224			) 
		anyChange += upINP("intensityMult",			intensitySlope	)
		anyChange += upINP("intensityMax",			intensityMax	) 
		anyChange += upINP("intensityMin",			intensityMin	)
		anyChange += upINP("lightSensMin",			lightSensMin	) 
		anyChange += upINP("lightSensMax",			lightSensMax	) 
		anyChange += upINP("lightSensNorm",			lightSensNorm	) 
		anyChange += upINP("multiplyRGB",			multiplyRGB	) 
		anyChange += upINP("timeZone",				timeZone,			) 
		anyChange += upINP("offsetOfPosition",		offsetOfPosition	) 
		anyChange += upINP("rightBoundaryOfCable",	rightBoundaryOfCable	) 
		anyChange += upINP("leftBoundaryOfCable",	leftBoundaryOfCable	) 
		anyChange += upINP("numberOfStepsCableAllows",	numberOfStepsCableAllows	) 
		anyChange += upINP("lightShadowVsDown",		lightShadowVsDown		) 
		anyChange += upINP("inFixBoundaryMode",		inFixBoundaryMode		) 
		anyChange += upINP("lastFixBoundaryMode",	lastFixBoundaryMode		) 
		if anyChange >0 or force:
			writeBackParams(sunDialParameters)
			U.logger.log(10, u"anyChange:{} writing params:{}".format(anyChange, sunDialParameters))
	except Exception, e:
		U.logger.log(40, u"Line {} has error={}".format(sys.exc_traceback.tb_lineno, e))
	return

# ------------------    ------------------ 
def saveFixBoundaryMode(set=999, tt=-1):
	global lastFixBoundaryMode, inFixBoundaryMode
	if set != 999: 
		inFixBoundaryMode = set
	if tt == -1:
		sunDialParameters["inFixBoundaryMode"]   = inFixBoundaryMode
		sunDialParameters["lastFixBoundaryMode"] = lastFixBoundaryMode
	else:
		sunDialParameters["inFixBoundaryMode"]   = inFixBoundaryMode
		sunDialParameters["lastFixBoundaryMode"] = tt
	saveParameters(force=True)

# ------------------    ------------------ 
def	upINP(parm, value):
	global sunDialParameters
	if parm not in sunDialParameters or sunDialParameters[parm] != value:
		#print "sundial updating", parm, value
		sunDialParameters[parm] = value
		return 1
	return 0

# ------------------    ------------------ 
def getParameters():
	global amPM1224, intensitySlope, intensityMax, intensityMin, lightSensMin, lightSensMax , lightSensNorm
	global timeZone, offsetOfPosition 
	global rightBoundaryOfCable, leftBoundaryOfCable, numberOfStepsCableAllows
	global lightOffBetweenHours
	global lightShadowVsDown, inFixBoundaryMode, lastFixBoundaryMode
	global sunDialParameters, multiplyRGB

	try:
		data,raw  = U.readJson(G.homeDir+"sunDial.parameters")
		U.logger.log(20, u" data:{}".format(data))
		
		sunDialParameters = data
		try: lightOffBetweenHours		= data["lightOffBetweenHours"]
		except: lightOffBetweenHours	= [0,0]

		try: amPM1224 					= data["amPM1224"]
		except: amPM1224				= 24

		try: intensitySlope 			= data["intensitySlope"]
		except: intensitySlope			= 1.

		try: intensityMax				= min(data["intensityMax"],1.0)
		except: intensityMax			= 1.

		try: intensityMin				= max(data["intensityMin"], 0.004)
		except:	intensityMin			= 0.004

		try: multiplyRGB				= data["multiplyRGB"]
		except:	multiplyRGB				= [1,1,1]

		try: lightSensMin				= max(data["lightSensMin"],0.001)
		except: lightSensMin			= 0.001

		try: lightSensMax				= min(data["lightSensMax"], 1.0 )
		except: lightSensMax			= 1.0

		try: lightSensNorm				= data["lightSensNorm"]
		except: lightSensNorm			= 12000

		try: timeZone					= data["timeZone"]
		except: timeZone				= "6 /US/Central"

		try: offsetOfPosition			= data["offsetOfPosition"]
		except: offsetOfPosition		= 0

		try: rightBoundaryOfCable		= data["rightBoundaryOfCable"]
		except: rightBoundaryOfCable	= 0

		try: leftBoundaryOfCable		= data["leftBoundaryOfCable"]
		except: leftBoundaryOfCable		= 0

		try: numberOfStepsCableAllows	= data["numberOfStepsCableAllows"]
		except: numberOfStepsCableAllows= 0

		try: lightShadowVsDown			= data["lightShadowVsDown"]
		except: lightShadowVsDown		= "normal shadow"

		try: lastFixBoundaryMode		= data["lastFixBoundaryMode"]
		except: lastFixBoundaryMode		= 0

		try: inFixBoundaryMode			= data["inFixBoundaryMode"]
		except: inFixBoundaryMode		= 0
		changeTimeZone(int(timeZone.split(" ")[0]))
		U.logger.log(20, u" inFixBoundaryMode:{}".format(inFixBoundaryMode))
	
		saveParameters(force=True)
	except Exception, e:
		U.logger.log(40, u"Line {} has error={}".format(sys.exc_traceback.tb_lineno, e))
	return


# ------------------    ------------------ 
def changedINPUT(theDict, key, lastValue, func, countChange=False):
	global anyInputChange
	if key not in theDict: return lastValue
	try: 	newV = func(theDict[key])
	except: return lastValue
	if lastValue != newV and countChange: anyInputChange += 1
	return newV
		
# ------------------    ------------------ 
def dummy(a):
	return a


# ------------------    ------------------ 
def readParams():
	global sensor, output, inpRaw, inp, useRTC
	global lastCl, timeZone, currTZ
	global oldRaw, lastRead
	global doReadParameters
	global clockDictLast, clockDict
	global buttonDict, sensorDict
	global pinsToName, anyInputChange
	global startWebServerSTATUS, startWebServerINPUT

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
		 


		if "debugRPI"						in inp:	 G.debug=		  				int(inp["debugRPI"]["debugRPIOUTPUT"])
		if "useRTC"							in inp:	 useRTC=					       (inp["useRTC"])
		if "output"							in inp:	 output=			 			   (inp["output"])
		if u"startWebServerSTATUS" 			in inp:	 startWebServerSTATUS= 			  int(inp["startWebServerSTATUS"])
		if u"startWebServerINPUT" 			in inp:	 startWebServerINPUT= 			  int(inp["startWebServerINPUT"])

		#### G.debug = 2 
		if G.program not in output:
			U.logger.log(30, G.program+ " is not in parameters = not enabled, stopping "+ G.program+".py" )
			exit()

		anyInputChange = False
		clock = output[G.program]
		for devId in  clock:
			clockDict		= clock[devId][0]
			if clockDictLast == clockDict: continue
			clockDictLast 	= clockDict


			#print clockDict
			if "timeZone"	 in clockDict:	
				if len(clockDict["timeZone"]) > 5 and timeZone !=	(clockDict["timeZone"]):
					changed 	= max(2, changed)  
					timeZone 	= (clockDict["timeZone"])
					tznew  		= int(timeZone.split(" ")[0])
					changeTimeZone(tznew)

			clockDict["timeZone"] = str(currTZ)+" "+ timeZones[currTZ+12]
			
	 		break
		return -changed - anyInputChange

	except Exception, e:
		U.logger.log(40, u"Line {} has error={}".format(sys.exc_traceback.tb_lineno, e))
		time.sleep(10)
		return 3


# ------------------    ------------------ 
def changeTimeZone(tznew):
	global timeZone, timeZones, currTZ
	try:
		if tznew != currTZ and False:
			U.logger.log(30, u"changing timezone from "+str(currTZ)+"  "+timeZones[currTZ+12]+" to "+str(tznew)+"  "+timeZones[tznew+12])
			os.system("sudo cp /usr/share/zoneinfo/"+timeZones[tznew+12]+" /etc/localtime")
			currTZ = tznew
	
	except Exception, e:
		U.logger.log(40, u"Line {} has error={}".format(sys.exc_traceback.tb_lineno, e))
	return	
# ########################################
# #########    basic setup funtions  #####
# ########################################
# ------------------    ------------------ 
def setupTimeZones():
	global timeZone, timeZones, currTZ
	try:
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
	except Exception, e:
		U.logger.log(40, u"Line {} has error={}".format(sys.exc_traceback.tb_lineno, e))
	return	


# ------------------    ------------------ 
def defineMotorType():
	global SeqCoils, minStayOn, motorType, stepsIn360, maxStepsUsed, nStepsInSequence
	SeqCoils = []

	try:
		mtSplit    		= motorType.split("-")
		mult 		    = int(mtSplit[2])
		stepsIn360 		= int(mtSplit[1])*mult
		maxStepsUsed	= stepsIn360 
	except:
		U.logger.log(40, "stopping  motorType wrong "+unicode(motorType)+"  "+unicode(mtSplit))
		exit()

	try:
		if mtSplit[0] == "bipolar":
			minStayOn = 0.01
			if motorType.find("-1") >-1:
				SeqCoils.append([0, 0, 0, 0])  # off
				SeqCoils.append([0, 1, 1, 0])
				SeqCoils.append([0, 1, 0, 1])
				SeqCoils.append([1, 0, 0, 1])
				SeqCoils.append([1, 0, 1, 0])
			elif motorType.find("-2") >-1:
				U.logger.log(20, "motorType = "+unicode(motorType))
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
			U.logger.log(40, "stopping  motorType not defined")
			exit()

		nStepsInSequence= len(SeqCoils) -1
		#print nStepsInSequence, SeqCoils
	except Exception, e:
		U.logger.log(40, u"Line {} has error={}".format(sys.exc_traceback.tb_lineno, e))
	return 

# ------------------    ------------------ 
def setgpiopinNumbers():
	global gpiopinNumbers, motorType, sensorDict, buttonDict, PIGPIO, pwmRange, lastEventOfPin
	### GPIO pins ########

	try:
		motorType						= "bipolar-400-2-PIG"

	## gpio -g mode 23 in;gpio -g read
		gpiopinNumbers ={}
		gpiopinNumbers["pin_CoilA1"] 	= 21 # blue lowest GPIO right 
		gpiopinNumbers["pin_CoilA2"] 	= 20 # pink
		gpiopinNumbers["pin_CoilB1"] 	= 16 # yellow
		gpiopinNumbers["pin_CoilB2"] 	= 12 # orange

		gpiopinNumbers["pin_sensor0"] 	= 23  # 0 clock
		gpiopinNumbers["pin_sensor1"] 	= 24  # 12 clock
		gpiopinNumbers["pin_sensor2"] 	= 4   # cap swicth sens
		gpiopinNumbers["pin_sensor3"] 	= 17  # switch sensor

		gpiopinNumbers["pin_Up"] 		= 11
		gpiopinNumbers["pin_Dn"] 		= 9
		gpiopinNumbers["pin_Select"] 	= 10
		gpiopinNumbers["pin_Exit"] 		= 22

		gpiopinNumbers["pin_rgbLED"]	= [26, # R: 2x 6.8 Ohm = 3.8  Ohm; dV at 0.3A = 2.2V;  lowest GPIO left
										   19, # G: 2x 2.7 Ohm = 1.35 Ohm; dV at 0.3A = 3.0V
										   13] # B: 2x 2.1 Ohm = 1.1  Ohm; dV at 0.3A = 3.1V


		pinsToName[gpiopinNumbers["pin_Up"]]		= "pin_Up"
		pinsToName[gpiopinNumbers["pin_Dn"]]		= "pin_Dn"
		pinsToName[gpiopinNumbers["pin_Select"]]	= "pin_Select"
		pinsToName[gpiopinNumbers["pin_Exit"]]		= "pin_Exit"
		pinsToName[gpiopinNumbers["pin_sensor0"]]	= "sens0"
		pinsToName[gpiopinNumbers["pin_sensor1"]]	= "sens12"
		pinsToName[gpiopinNumbers["pin_sensor2"]]	= "sensCap"
		pinsToName[gpiopinNumbers["pin_sensor3"]]	= "sensSw"
		lastEventOfPin ={}
		for pin in pinsToName:
			lastEventOfPin[pin] = time.time()



		sensorDict			 = {}
		sensorDict["sensor"] = []
		sensorDict["sensor"].append({"ON":0,"pull":1,"lastCeck":0, "lastValue":-1,"newValue":-1,"clicked":"N", "left":[-1,-1,-1,-1,-1,-1,-1,-1,-1], "right":[-1,-1,-1,-1,-1,-1,-1,-1,-1], "status":-1, "event": 0}) 
		sensorDict["sensor"].append({"ON":0,"pull":1,"lastCeck":0, "lastValue":-1,"newValue":-1,"clicked":"N", "left":[-1,-1,-1,-1,-1,-1,-1,-1,-1], "right":[-1,-1,-1,-1,-1,-1,-1,-1,-1], "status":-1, "event": 0}) 
		sensorDict["sensor"].append({"ON":1,"pull":0,"lastCeck":0, "lastValue":0, "newValue":-1,"clicked":"N", "left":[-1,-1,-1,-1,-1,-1,-1,-1,-1], "right":[-1,-1,-1,-1,-1,-1,-1,-1,-1], "status": 0, "event": 1}) 
		sensorDict["sensor"].append({"ON":0,"pull":1,"lastCeck":0, "lastValue":0, "newValue":-1,"clicked":"N", "left":[-1,-1,-1,-1,-1,-1,-1,-1,-1], "right":[-1,-1,-1,-1,-1,-1,-1,-1,-1], "status": 0, "event":-1}) 
		sensorDict["sequence"]				= [0,1,1,1,1,0,0,0,0] # sensors firing when turning right in parts of 360/8: (0,1,2,3,4,5,6,7,8=360 )
																	  # 4 magents every 1/8 of 360, 2 reed sensor at 0(#0-sensor0) and 180(#1=sensor1)
		sensorDict["currentSeqNumber"]		= -1 #  0,1,2,3,4,5,6,7,8
		sensorDict["currentSeqDirection"]	= 0  # -1,+1
		sensorDict["gpioToSensNumber"]		= {}  # for reverse looup 
		for nn in range(4):
			sensorDict["gpioToSensNumber"][gpiopinNumbers["pin_sensor"+str(nn)]] = nn 

		buttonDict				= {}
		for key in [ "pin_Up", "pin_Dn", "pin_Select", "pin_Exit"]:
			buttonDict[key] = {"lastCeck":0, "lastValue":-1,"newValue":-1}


		U.logger.log(10, unicode(sensorDict))
		U.logger.log(10, unicode(buttonDict))

		if not U.pgmStillRunning("pigpiod"): 	
			U.logger.log(30, "starting pigpiod")
			os.system("sudo pigpiod -s 4 &")
			time.sleep(0.5)
			if not U.pgmStillRunning("pigpiod"): 	
				U.logger.log(30, " restarting myself as pigpiod not running, need to wait for timeout to release port 8888")
				time.sleep(20)
				doSunDialShutdown()
				U.restartMyself(reason="pigpiod not running")
				exit(0)

		PIGPIO = pigpio.pi()
		pwmRange = 1000


		defineGPIOout(gpiopinNumbers["pin_CoilA1"])
		defineGPIOout(gpiopinNumbers["pin_CoilA2"])
		defineGPIOout(gpiopinNumbers["pin_CoilB1"])
		defineGPIOout(gpiopinNumbers["pin_CoilB2"])


		defineGPIOout(gpiopinNumbers["pin_rgbLED"][0], pwm=1)
		defineGPIOout(gpiopinNumbers["pin_rgbLED"][1], pwm=1)
		defineGPIOout(gpiopinNumbers["pin_rgbLED"][2], pwm=1)

		defineGPIOin("pin_Up",		event=-1, evpgm="button", pull=1)
		defineGPIOin("pin_Dn",		event=-1, evpgm="button", pull=1)
		defineGPIOin("pin_Select",	event=-1, evpgm="button", pull=1)
		defineGPIOin("pin_Exit",	event=-1, evpgm="button", pull=1)


		defineGPIOin("pin_sensor0", pull=sensorDict["sensor"][0]["pull"] )
		defineGPIOin("pin_sensor1", pull=sensorDict["sensor"][1]["pull"] )
		defineGPIOin("pin_sensor2", pull=sensorDict["sensor"][2]["pull"], event=sensorDict["sensor"][3]["event"], evpgm="sw")
		defineGPIOin("pin_sensor3", pull=sensorDict["sensor"][3]["pull"], event=sensorDict["sensor"][3]["event"], evpgm="sw" )

		defineMotorType()
	except Exception, e:
		U.logger.log(40, u"Line {} has error={}".format(sys.exc_traceback.tb_lineno, e))
	return 


# ########################################
# #########    basic GPIO funtions  ######
# ########################################

# ------------------    ------------------ 
def defineGPIOinGPIO(pinName, event=0, pull=1, evpgm="button"):
	global gpiopinNumbers
	pin = gpiopinNumbers[pinName]
	if pin <=1: return 
	try:
		#print "defineGPIOin ", pinName, pin, "pull: ", pull
		if pull==1:
			GPIO.setup( pin, GPIO.IN, pull_up_down=GPIO.PUD_UP)
		else:
			GPIO.setup( pin, GPIO.IN, pull_up_down=GPIO.PUD_DOWN)

		if event !=0:
			#print " setup event for ", pin
			if evpgm =="button":
				if event == 1 : GPIO.add_event_detect(pin, GPIO.RISING,  buttonPressedEventGPIO, bouncetime=300)	
				if event ==-1 : GPIO.add_event_detect(pin, GPIO.FALLING, buttonPressedEventGPIO, bouncetime=300)	
			else: 				
				if event == 1 : GPIO.add_event_detect(pin, GPIO.RISING,  boundarySensorEventGPIO, bouncetime=100)	
				if event ==-1 : GPIO.add_event_detect(pin, GPIO.FALLING, boundarySensorEventGPIO, bouncetime=100)	
			###PIGPIO.set_glitch_filter(pin, 10000) # steady for 10 msec 

	except Exception, e:
		U.logger.log(40, u"defineGPIOinLine {} has error={}".format(sys.exc_traceback.tb_lineno, e))
		if unicode(e).find("object has no attribute 'send'")> -1:
			os.system("sudo killall pigpiod")
			U.logger.log(40, u"restarting pigpiod .. this will take > 30 secs ")
			time.sleep(30)
			U.restartMyself(reason="pigpiod needs to be restarted")
		time.sleep(30)
		U.restartMyself(reason="pigpio does not start, trying to restart")
	return


# ------------------    ------------------ 
def defineGPIOin(pinName, event=0, pull=1, evpgm="button"):
	global PIGPIO
	global gpiopinNumbers
	pin = gpiopinNumbers[pinName]
	if pin <=1: return 
	try:
		#print "defineGPIOin ", pinName, pin, "pull: ", pull
		PIGPIO.set_mode( pin,  pigpio.INPUT )
		if pull==1:
			PIGPIO.set_pull_up_down( pin, pigpio.PUD_UP)
		else:
			PIGPIO.set_pull_up_down( pin, pigpio.PUD_DOWN)

		if event !=0:
			#print " setup event for ", pin
			if evpgm =="button":
				if event == 1 : PIGPIO.callback(pin, pigpio.RISING_EDGE, buttonPressedEventPIG)	
				if event ==-1 : PIGPIO.callback(pin, pigpio.EITHER_EDGE, buttonPressedEventPIG)	
			else: 				
				if event == 1 : PIGPIO.callback(pin, pigpio.RISING_EDGE,  boundarySensorEventPIG)	
				if event ==-1 : PIGPIO.callback(pin, pigpio.FALLING_EDGE, boundarySensorEventPIG)	
			PIGPIO.set_glitch_filter(pin, 10000) # steady for 10 msec 

	except Exception, e:
		U.logger.log(40, u"defineGPIOinLine {} has error={}".format(sys.exc_traceback.tb_lineno, e))
		if unicode(e).find("object has no attribute 'send'")> -1:
			os.system("sudo killall pigpiod")
			U.logger.log(40, u"restarting pigpiod .. this will take > 30 secs ")
			time.sleep(30)
			U.restartMyself(reason="pigpiod needs to be restarted")
		time.sleep(30)
		U.restartMyself(reason="pigpio does not start, trying to restart")
	return


# ------------------    ------------------ 
def defineGPIOout(pin, pwm = 0,freq =1000):
	global PIGPIO, pwmRange, colPWM
	#print "defineGPIOout", pin, pwm, freq
	try:
		PIGPIO.set_mode(pin, pigpio.OUTPUT)
		if pwm !=0:
			PIGPIO.set_PWM_frequency(pin, pwmRange)
			PIGPIO.set_PWM_range(pin, pwmRange)
			PIGPIO.set_PWM_dutycycle(pin, 0)
	except Exception, e:
		U.logger.log(40, u"defineGPIOoutLine {} has error={}".format(sys.exc_traceback.tb_lineno, e))
		if unicode(e).find("object has no attribute 'send'")> -1:
			os.system("sudo killall pigpiod")
			U.logger.log(40, u"restarting pigpiod .. this will take > 30 secs ")
			time.sleep(30)
			U.restartMyself(reason="pigpiod needs to be restarted")
		U.restartMyself(reason="pigpio does not start, trying to restart")
		
	return

# ------------------    ------------------ 
def setGPIOValue(pin,val,amplitude =-1):
	global PIGPIO, pwmRange
	try:
		pin = int(pin)
		if amplitude == -1:
			PIGPIO.write( pin, val )
		else:
			if amplitude > 0 and val !=0:
				PIGPIO.set_PWM_dutycycle( (pin), int(pwmRange*amplitude) )
				#print "setGPIOValue ", pin, val,amplitude, int(pwmRange*amplitude/100.), PIGPIO.get_PWM_dutycycle(int(pin)) 
			else:
				PIGPIO.write( (pin), 0 )
				PIGPIO.set_PWM_dutycycle( int(pin), 0)
	except Exception, e:
		U.logger.log(30, u"defineGPIOoutLine {} has error={}".format(sys.exc_traceback.tb_lineno, e))
		if unicode(e).find("object has no attribute 'send'") > -1:
			os.system("sudo killall pigpiod")
			U.logger.log(30, u"restarting pigpiod .. this will take > 30 secs ")
			time.sleep(30)
			U.restartMyself(reason="pigpiod needs to be restarted")
		U.restartMyself(reason="pigpio does not start, trying to restart")
	return

# ------------------    ------------------ 
def getPinValueGPIO(pinName, pin=-1, ON=1, doPrint=False):
	global gpiopinNumbers
	ret = -1

	try:
		if pin == -1:
			if pinName not in gpiopinNumbers: return -1
			if gpiopinNumbers[pinName] < 1:   return -1
			pin = gpiopinNumbers[pinName]

		ret = GPIO.input(pin)
		if  doPrint: 
			U.logger.log(20, u" pin:{} #:{} ON:{},  value:{}".format(pinName, pin, ON, ret) )
		if ON == 0: 
			if ret == 0:	ret = 1
			else:       	ret = 0

	except Exception, e:
		U.logger.log(40, u"defineGPIOoutLine {} has error={}".format(sys.exc_traceback.tb_lineno, e))
		U.logger.log(40, u"pinName {}".format(pinName))
		if unicode(e).find("object has no attribute 'send'") > -1:
			os.system("sudo killall pigpiod")
			U.logger.log(40, u"restarting pigpiod .. this will take > 30 secs ")
			time.sleep(30)
			U.restartMyself(reason="pigpiod needs to be restarted")
		time.sleep(30)
		U.restartMyself(reason="pigpio does not start, trying to restart")
	return ret

# ------------------    ------------------ 
def getPinValue(pinName, pin=-1, ON = 1, doPrint=False):
	global gpiopinNumbers, PIGPIO
	ret = -1
	try:
		if pin == -1:
			if pinName not in gpiopinNumbers: return -1
			if gpiopinNumbers[pinName] < 1:   return -1
			pin = gpiopinNumbers[pinName]

		ret = PIGPIO.read(pin)
		if  doPrint: 
			U.logger.log(20, u" pin:{} #:{} ON:{} sens:{}".format(pinName, pin, ON, ret) )
		if ON == 0: 
			if ret == 0:	ret = 1
			else:       	ret = 0

	except Exception, e:
		U.logger.log(40, u"defineGPIOoutLine {} has error={}".format(sys.exc_traceback.tb_lineno, e))
		U.logger.log(40, u"pinName {}".format(pinName))
		if unicode(e).find("object has no attribute 'send'") > -1:
			os.system("sudo killall pigpiod")
			U.logger.log(40, u"restarting pigpiod .. this will take > 30 secs ")
			time.sleep(30)
			U.restartMyself(reason="pigpiod needs to be restarted")
		time.sleep(30)
		U.restartMyself(reason="pigpio does not start, trying to restart")
	return ret

###   gpio -g mode 23 out;gpio -g write 23 1
###   gpio -g mode 23 in;gpio -g read 23
# ########################################
# #########  moving functions ############
# ########################################
 
# ------------------    ------------------ 
def makeStep(seq, only2=False):
	global gpiopinNumbers
	global SeqCoils
	if only2 and sum(SeqCoils[seq]) == 1: 
		return False
	#print "makeStep", seq, SeqCoils[seq]
	setGPIOValue(gpiopinNumbers["pin_CoilA1"], SeqCoils[seq][0])
	setGPIOValue(gpiopinNumbers["pin_CoilA2"], SeqCoils[seq][1])
	setGPIOValue(gpiopinNumbers["pin_CoilB1"], SeqCoils[seq][2])
	setGPIOValue(gpiopinNumbers["pin_CoilB2"], SeqCoils[seq][3])
	return True


# ------------------    ------------------ 
def setMotorOFF():
	global motorType
	makeStep(0)
	return


 
# ------------------    ------------------ 
def move(steps, direction, stayOn=0.01, force = 0, stopIfMagSensor=[False,False], updateSequence=False, fast=False, stopIfBoundarySensor=[True,True], doPrint=False):
	global lastStep
	global gpiopinNumbers
	global SeqCoils
	global nStepsInSequence
	global whereIs12
	global minStayOn
	global motorType
	global PIGPIO
	global currentSequenceNo
	global totalStepsDone
	global inFixBoundaryMode
	global currentlyMoving
	global lastPosition, rightBoundaryOfCable, leftBoundaryOfCable, findBoundaryMode

	if doPrint: U.logger.log(20, "into move") 
	iSteps= 0
	try:
		stayOn = max(minStayOn,stayOn)
		lStep = lastStep
		if doPrint: U.logger.log(20, "steps:{} direction:{}, stayOn:{:.3f}, force:{}, stopIfMagSensor:{}, updateSequence:{}, inFixBoundaryMode:{}".format(steps,  direction, stayOn, force, stopIfMagSensor, updateSequence, inFixBoundaryMode) )
		steps = abs(int(steps))

		getSensors()
		last1 = sensorDict["sensor"][1]["status"]
		last0 = sensorDict["sensor"][0]["status"]
		for i in range(steps):
			currentlyMoving = time.time()

			if updateSequence: 
				 determineSequenceNo(totalStepsDone+iSteps)

			if findBoundaryMode:
					if doPrint: U.logger.log(20, "finB.  dir: {}, 3:{}, 2:{}, lastPosition:{}, iSteps:{}".format(direction, sensorDict["sensor"][3]["status"], sensorDict["sensor"][2]["status"], lastPosition, iSteps ) )
					if direction ==  1  and sensorDict["sensor"][3]["status"] == 1: 
						if doPrint: U.logger.log(20, "returning, touching sensor 3") 
						return lastPosition
					if direction ==  -1 and sensorDict["sensor"][2]["status"] == 1: 
						if doPrint: U.logger.log(20, "returning, touching sensor 2" ) 		
						return lastPosition

			else:
				if (sensorDict["sensor"][2]["status"] == 1 or sensorDict["sensor"][3]["status"] == 1 ) and inFixBoundaryMode==0:
					if sensorDict["sensor"][2]["status"] == 1:	
						saveFixBoundaryMode(set=1)
					if sensorDict["sensor"][3]["status"] == 1:	
						saveFixBoundaryMode(set=-1)
					U.logger.log(20, "fixing (1) starting due to: cap switch sens: {};   switch sensor:{}".format(sensorDict["sensor"][2]["status"], sensorDict["sensor"][3]["status"]))
					U.restartMyself(reason="need to fix boundaries #1 left:{}, right{}".format(sensorDict["sensor"][2]["status"], sensorDict["sensor"][3]["status"]), delay=5)

				if inFixBoundaryMode  !=0 and ( (sensorDict["sensor"][2]["status"] == 1  and stopIfBoundarySensor[0])  or  (sensorDict["sensor"][3]["status"] == 1  and stopIfBoundarySensor[1]) ):
					U.logger.log(20, "move  return due fix!=0  sens2=T, stopifB0=T sens3=T or stopIfB1=T: direction%d, inFixBoundaryMode:%d" %(direction,inFixBoundaryMode)+" cap switch sens: "+unicode(sensorDict["sensor"][2]["status"])+";   switch sensor:"+unicode(sensorDict["sensor"][3]["status"]))
					return iSteps


				if not updateSequence or ( currentSequenceNo < 8 and sensorDict["sensor"][0] == 1 ):
					if i >= force: 
						if last0 != sensorDict["sensor"][0]["status"] and sensorDict["sensor"][0]["status"] == 1 and stopIfMagSensor[0]: 
							U.logger.log(20, "move  return due to: last0!=sens0, mag0=T, direction%d, inFixBoundaryMode:%d"%(direction, inFixBoundaryMode)+" cap switch sens: "+unicode(sensorDict["sensor"][2]["status"])+";   switch sensor:"+unicode(sensorDict["sensor"][3]["status"]))
							return iSteps
						if last1 != sensorDict["sensor"][1]["status"] and sensorDict["sensor"][1]["status"] == 1 and stopIfMagSensor[1]: 
							U.logger.log(20, "move  return due to: last1!=sens1, mag1=T, direction%d, inFixBoundaryMode:%d"%(direction, inFixBoundaryMode)+" cap switch sens: "+unicode(sensorDict["sensor"][2]["status"])+";   switch sensor:"+unicode(sensorDict["sensor"][3]["status"]))
							return iSteps

				if currentSequenceNo == 8 and sensorDict["sensor"][0] == 1:
					if i >= force: 
						if last0 != sensorDict["sensor"][0]["status"] and sensorDict["sensor"][0]["status"] == 1 and stopIfMagSensor[0]: 
							return iSteps
						if last1 != sensorDict["sensor"][1]["status"] and sensorDict["sensor"][1]["status"] == 1 and stopIfMagSensor[1]: 
							return iSteps

			last1 = sensorDict["sensor"][1]["status"]
			last0 = sensorDict["sensor"][0]["status"]

			iSteps += 1
			lStep += direction
			lastPosition += direction
			savePositions()

			if   lStep >= len(SeqCoils):	lStep = 1
			elif lStep <  1: 				lStep = len(SeqCoils)-1

			lastStep = lStep
			if makeStep(lStep, only2=fast):
				time.sleep(stayOn)
			if doPrint: U.logger.log(20, "moved, now at:{}".format(lastPosition) )
			getSensors()

	###			U.logger.log(40, " not sleeping")

		getSensors()
		if (sensorDict["sensor"][2]["status"] == 1 or sensorDict["sensor"][3]["status"]== 1) and inFixBoundaryMode ==0 and not findBoundaryMode:
			if sensorDict["sensor"][2]["status"] == 1:	saveFixBoundaryMode(set=1)
			if sensorDict["sensor"][3]["status"] == 1:	saveFixBoundaryMode(set=-1)
			
			U.logger.log(20, "fixing  (2) starting due to: cap switch sens: "+unicode(sensorDict["sensor"][2]["status"])+";   switch sensor:"+unicode(sensorDict["sensor"][3]["status"]))
			doSunDialShutdown()
			U.restartMyself(reason="need to fix boundaries #2", delay=5 )

	except Exception, e:
		U.logger.log(40, u"Line {} has error={}".format(sys.exc_traceback.tb_lineno, e))

	#if speed < 100 or stayOn > 0.5: setOffset()
	return iSteps

# ------------------    ------------------ 
def testIfMove( waitBetweenSteps, lastMove ):
	global maxStepsUsed, startSteps
	global speed
	global t0
	global printON
	global totalStepsDone
	global hour, minute, second
	global secSinceMidnit	
	global PIGPIO
	global currentSequenceNo, inbetweenSequences

	try:
		lasttotalStepsDone = totalStepsDone
		secs = secSinceMidnit
		if amPM1224 == 12: secs 	/=2
		nextTotalSteps 	= min( int( secs / (waitBetweenSteps*speed)   ), maxStepsUsed )
		U.logger.log(10, "wait:{}, lastMove:{}, secSinceMidnit:{}, secs:{}, nextTotalSteps:{}, totalStepsDone:{}" .format(waitBetweenSteps, lastMove, secSinceMidnit, secs, nextTotalSteps, totalStepsDone) )
		if nextTotalSteps != totalStepsDone:
			nextStep    = nextTotalSteps - totalStepsDone 

			if nextStep <0:	direction = -1
			else:			direction =  1

			U.logger.log(20, "secSinMidn:{:.2f}; secseff:{:.2f}; {:02d}:{:02d}:{:02d}; dt:{:.5f} ; nstep:{}; tSteps:{}; curtSeqN:{};  inbSeq:{};  inFixM:{}; s2:{}, s3:{}; dir:{}".format(secSinceMidnit, secs, hour,minute,second, (time.time()-t0), nextStep, totalStepsDone, currentSequenceNo, inbetweenSequences, inFixBoundaryMode, sensorDict["sensor"][2]["status"],sensorDict["sensor"][3]["status"],  direction))

			if nextStep != 0: 
				if speed > 10 or nextStep >5: stayOn =0.01
				else:		                  stayOn =0.01
				if lasttotalStepsDone < 10: force = 10 
				else:					force = 0
				#print "dir, nextStep", dir, nextStep
				if currentSequenceNo < 7: force = int(maxStepsUsed*0.9)
				steps = move(int(abs(nextStep)), direction, stayOn=stayOn, force=force, updateSequence=True)
				lastMove = time.time()


				### no with offset!!
				##if currentSequenceNo == 8 and sensorDict["sensor"][0]["status"] == 1:
				##	nextStep =0

				setColor()

			totalStepsDone += nextStep

			#saveTime(secSinceMidnit)
			t0=time.time()
	except Exception, e:
		U.logger.log(40, u"Line {} has error={}".format(sys.exc_traceback.tb_lineno, e))

	return lastMove


# ------------------    ------------------ 
def determineSequenceNo(lSteps):
	global currentSequenceNo, inbetweenSequences

	try:
	#print "into  determineSequenceNo.. inbetweenSequences:",inbetweenSequences, "lSteps",lSteps
		if lSteps < 15: 
			currentSequenceNo = 0
			inbetweenSequences    = False
			return 
		if inbetweenSequences:
			if sensorDict["sensor"][0]["status"] == 1 or sensorDict["sensor"][1]["status"] == 1:
				currentSequenceNo += 1
				inbetweenSequences = False
				#print "updating currentSequenceNo", currentSequenceNo,"inbetweenSequences",inbetweenSequences, "lSteps",lSteps
		if     sensorDict["sensor"][0]["status"] == 0 and sensorDict["sensor"][1]["status"] == 0:
				#print "updating currentSequenceNo", currentSequenceNo,"inbetweenSequences",inbetweenSequences, "lSteps",lSteps
				inbetweenSequences = True
	except Exception, e:
		U.logger.log(40, u"Line {} has error={}".format(sys.exc_traceback.tb_lineno, e))
	return						
	
		

# ------------------    ------------------ 
def testIfRewind( ):
	global maxStepsUsed, startSteps
	global t0
	global printON
	global totalStepsDone
	global hour, minute, second
	global secSinceMidnit	
	global useoffsetOfPosition
	global lastPosition, zeroPosition
	global speed


	try:

		if  totalStepsDone >= maxStepsUsed or (speed > 1. and totalStepsDone >= maxStepsUsed-10): 

			if useoffsetOfPosition >=0:			dir = 1
			else:								dir = -1

			if useoffsetOfPosition !=0:
				move (useoffsetOfPosition, -dir,  force=30, stopIfMagSensor=[False,False] )

			U.logger.log(20, "rewind..   secSinceMidnit:{:.2f}; {:02d}:{:02d}:{:02d}; dt:{:.5f}; totSteps:{}".format(secSinceMidnit, hour,minute,second, (time.time()-t0), totalStepsDone))
			move (maxStepsUsed,-1,  force=30, stopIfMagSensor=[False,True] )
			move (maxStepsUsed,-1,  force=30, stopIfMagSensor=[True,False] )
			move (maxStepsUsed,-1,  force=30, stopIfMagSensor=[True,False] )
			if useoffsetOfPosition !=0:
				if useoffsetOfPosition >=0:			dir = 1
				else:								dir = -1
				move (useoffsetOfPosition, dir,   force=30, stopIfMagSensor=[False,False] )

			totalStepsDone = 0
			t0=time.time()
		totalStepsDone = max(0, min(totalStepsDone, maxStepsUsed) )
	except Exception, e:
		U.logger.log(40, u"Line {} has error={}".format(sys.exc_traceback.tb_lineno, e))

	return 




# ------------------    ------------------ 
def fastStart():
	global maxStepsUsed,stepsIn360
	global printON
	global waitBetweenSteps, secondsTotalInDay 
	global amPM1224
	global whereIs12
	global currentSequenceNo
	global limitSensorTriggered
	global lastPosition, zeroPosition, lastFixBoundaryMode
	try:
		if zeroPosition  > 9999: 
			U.logger.log(20, "trying to do start, zeroPosition not defined:{}, need to do full calibration".format(zeroPosition))
			return False

		delta = lastPosition - zeroPosition
		if abs(delta) > maxStepsUsed*1.2: return False
		if time.time() - lastFixBoundaryMode  < 200: return False
		return False

		updatewebserverStatus(status="try fast start")

		if delta < 0: 
			direction = 1
			nSteps = [abs(delta) + 8,-5,-1,-1,-1,-1,-1,-1,-1,-1,-1]
		else:
			direction = -1
			nSteps = [delta-4,1,1,1,1,1,1,1,1,1,1,1]
	
	
		U.logger.log(20, "trying to do fast start  lastPosition:{}, zeroPosition:{}, move:{}, dir:{} ".format(lastPosition, zeroPosition, delta, direction) )
		set = False
		for nn in nSteps:
			dd = direction * (nn/abs(nn))
			steps = move( abs(nn) , dd, stopIfMagSensor=[False,False] )
			getSensors()
			U.logger.log(20, "fast start  result: after lastPosition:{}, zeroPosition:{}, move:{}, dir:{};  ==> sens0:{}".format(lastPosition, zeroPosition, abs(nn),dd, sensorDict["sensor"][0]["status"]) )
			if  sensorDict["sensor"][0]["status"] == 1: 
				set = True
				if abs(lastPosition - zeroPosition) > 6: 
					U.logger.log(20, "trying to do fast start start failed, zero has shifted to much: {}".format(lastPosition - zeroPosition))
					return False
				zeroPosition = lastPosition
				savePositions()
				break
	
		if not set:
			U.logger.log(20, "trying to do fast start start failed, sensor0status !=1 ".format(sensorDict["sensor"][0]["status"] ))
			return

		if amPM1224 ==24:	waitBetweenSteps 	= secondsTotalInDay     / maxStepsUsed 
		else: 				waitBetweenSteps 	= secondsTotalInHalfDay / maxStepsUsed 
		waitBetweenSteps /=speed

		currentSequenceNo = 0
		zeroPosition = lastPosition
		U.logger.log(20, "at position 0  ; waitBetweenSteps:{:.1f}; maxStepsUsed:{}; zeroPosition:{}".format(waitBetweenSteps, maxStepsUsed, zeroPosition))
		displayDrawLines([" wait:{:.1f}".format(waitBetweenSteps)," nSteps:{}".format(maxStepsUsed)," zero:{}".format(zeroPosition), datetime.datetime.now().strftime("%a, %Y-%m-%d %H:%M")])
		return True
	except Exception, e:
		U.logger.log(40, u"line {} has error={}".format(sys.exc_traceback.tb_lineno, e))

	return False


# ------------------    ------------------ 
def findLeftRight():
	global maxStepsUsed,stepsIn360
	global printON
	global waitBetweenSteps, secondsTotalInDay 
	global amPM1224
	global whereIs12
	global currentSequenceNo
	global limitSensorTriggered
	global lastPosition, zeroPosition
	
	try:
		limitSensorTriggered = 0
		time.sleep(0.1)

		stayOn = 0.01

		maxSteps = int(stepsIn360+2)
		updatewebserverStatus(status="finding left right boundaries")

		# check if we start at 0 left or right
		getSensors()
		#  sensorDict["pin_sensor0"]["status"]

		U.logger.log(20, "starting left right ")
		displayDrawLines(["starting left right","determining limits", datetime.datetime.now().strftime("%a, %Y-%m-%d %H:%M")])

		steps 		= 0 
		stepsTotal	= 0
		oneEights = int(stepsIn360 /8.)+10
		pp = True
		if pp: printLrLog("0000 === ", steps, 0, short=True)
		while True:
			# THIS IS THE EASIEST SIMPLE CASE:
			if sensorDict["sensor"][1]["status"] == 1: # 12 o-clock sensor on at start = we are in the middle, exit basic find
				steps = move( oneEights*6  , -1, force=30, stopIfMagSensor=[True,False] )
				if pp: printLrLog("0100 === ", steps, -1, extra=" fist step done", short=True)
				break

			# THIS IS THE MOST DIFFICULT, SOMEWHERE CLOSE TO 0 OR 24:
			elif sensorDict["sensor"][0]["status"] == 1:
				#test if still on when moving right
				steps = move( 10  , 1, force=11, stopIfMagSensor=[False,False] )
				if pp: printLrLog("0200 === ", steps, -1, short=True)

				if sensorDict["sensor"][0]["status"] == 0:
					steps = move( oneEights*8  , 1, force=6, stopIfMagSensor=[True,True] )
					if pp: printLrLog("0201 === ", steps, 1, short=True)

					if sensorDict["sensor"][0]["status"] == 1:
						steps = move( oneEights*10, -1, force=6, stopIfMagSensor=[False,True] )
						if pp: printLrLog("0202 === ", steps, -1, short=True)


					if sensorDict["sensor"][1]["status"] == 1:
						steps = move( oneEights*8  ,-1, force=6, stopIfMagSensor=[True,False] )
						if pp: printLrLog("0203 === ", steps, -1, short=True)
						break


				if sensorDict["sensor"][0]["status"] == 1:
					steps = move( oneEights*8  , -1, force=6, stopIfMagSensor=[False,True] )
					if pp: printLrLog("0210 === ", steps, -1, short=True)


				if sensorDict["sensor"][1]["status"] == 0:
					steps = move( oneEights*6 , 1, force=30, stopIfMagSensor=[True,True] )
					if pp: printLrLog(-3, "0211 === ", steps, -1, short=True)
					if sensorDict["sensor"][1]["status"] == 1:
						steps = move( oneEights*6 , -1, force=30, stopIfMagSensor=[True,False] )
						if pp: printLrLog("0212 === ", steps, -1, short=True)
						break

					if sensorDict["sensor"][0]["status"] == 1:
						steps = move( oneEights*6 , -1, force=30, stopIfMagSensor=[False,True] )
						if pp: printLrLog("0230 === ", steps, -1, short=True)
						steps = move( oneEights*6 , -1, force=30, stopIfMagSensor=[True,False] )
						break

				if sensorDict["sensor"][1]["status"] == 1:
					# found a midle, just continue to 0
					steps = move( oneEights*6  , -1, force=30, stopIfMagSensor=[True,False] )
					if pp: printLrLog("0300 === ", steps, -1)
					break
				if pp: U.logger.log(50, "0400 === no if condition found")


			else:
			
				steps = move( 5  , 1, force=6, stopIfMagSensor=[True,False] )
				if pp: printLrLog("1000 === ", steps, -1, short=True)
				if sensorDict["sensor"][1]["status"] == 0 and sensorDict["sensor"][1]["status"] == 0:
					steps = move( oneEights*5  , 1, force=2, stopIfMagSensor=[True,True] )
					if pp: printLrLog("1100 === ", steps, 1, short=True)

				if sensorDict["sensor"][1]["status"] == 1:
					steps = move( oneEights*6 , -1, force=30, stopIfMagSensor=[True,False] )
					if pp: printLrLog("1200 === ", steps, -1, short=True)

				if sensorDict["sensor"][0]["status"] == 1:
					steps = move( oneEights*3 , -1, force=5, stopIfMagSensor=[True,True] )
					if pp: printLrLog("1300 === ", steps, -1, short=True)
					if sensorDict["sensor"][0]["status"] == 1:
						steps = move( oneEights*8 ,  -1, force=30, stopIfMagSensor=[False,True] )
						if pp: printLrLog("1310 === ", steps, -1, short=True)
						steps = move( oneEights*8 , -1, force=30, stopIfMagSensor=[True,False] )
						if pp: printLrLog("1311 === ", steps, -1, short=True)
						break
						# done

					elif sensorDict["sensor"][1]["status"] == 1:
						steps = move( oneEights*8, -1, force=10, stopIfMagSensor=[True,False] )
						if pp: printLrLog("1321 === ", steps, -1)
						break
						# done

					elif sensorDict["sensor"][0]["status"] == 0:
						steps = move( oneEights*8 , -1, force=30, stopIfMagSensor=[True,True] )
						if pp: printLrLog("1340 === ", steps, -1, short=True)
						if sensorDict["sensor"][1]["status"] == 1:
							steps = move(stayOn, oneEights*8 , -1, force=10, stopIfMagSensor=[False,True] )
							break

						steps = move( oneEights*5 , -1, force=30, stopIfMagSensor=[True,False] )
						if pp: printLrLog("11341 === ", steps, -1, short=True)
						break
			U.logger.log(40, "============ no sensors found , try with fix boundaies to move the pole.")
			displayDrawLines(["pole stuck?", " doing recovery", datetime.datetime.now().strftime("%a, %Y-%m-%d %H:%M")])
			#time.sleep(1)
			findBoundariesOfCable(force=True)
			U.restartMyself(reason="no sensor found")
			return 

		if getLightSensorValue(force=True): setColor(force=True)

		displayDrawLines(["confirming", " left-right limits", datetime.datetime.now().strftime("%a, %Y-%m-%d %H:%M")])

		U.logger.log(20, "finding limits checking 6 left beyond limits, then right 360 + 1 magnet ")
		time.sleep(0.1)
		steps = move( oneEights*2,             -1, force=0, stopIfMagSensor=[False,False] )
		time.sleep(0.1)
		steps = move( oneEights*2,              1, force=0, stopIfMagSensor=[False,False])
		U.logger.log(20, "finding limits ,  2 mags left and right, back at 0")
		time.sleep(0.1)


		sensorDict["sensor"][0]["left"][0]  = 0
		## now we are at start
		## do full 360:
		pp = False
		U.logger.log(20, "finding limits, first turn right %d times"%len(sensorDict["sequence"]))
		#time.sleep(5)
		seqN       = 0
		stepsTotal = 0
		if  sensorDict["sensor"][0]["status"] == 1:
			sensorDict["sensor"][0]["right"][0]  = 0
		for nn in range(len(sensorDict["sequence"])-1): # move right (+1) 
			steps = move( oneEights*6,  1, force=20, stopIfMagSensor=[True,True] )
			stepsTotal += steps
			seqN +=1
			if pp: printLrLog("right === ", nn, steps)
			if  sensorDict["sensor"][1]["status"] == 1:
				sensorDict["sensor"][1]["right"][seqN]  = stepsTotal
			if  sensorDict["sensor"][0]["status"] == 1:
				sensorDict["sensor"][0]["right"][seqN]  = stepsTotal
			#time.sleep(2)
		U.logger.log(20, "finding limits checking 2 right beyond limits, then back to 0 ")
		time.sleep(0.1)
		steps = move( oneEights*2,             1, force=0, stopIfMagSensor=[False,False], fast=False )
		time.sleep(0.1)
		steps = move( oneEights*2,            -1, force=0, stopIfMagSensor=[False,False], fast=False )
		time.sleep(0.1)

		rightLimit  = int(min(stepsIn360*1.04,max(stepsIn360*0.96,stepsTotal)))
		displayDrawLines(["right limit set  confirming left limit", datetime.datetime.now().strftime("%a, %Y-%m-%d %H:%M")])
		if pp: U.logger.log(20, "right limit set  confirming left limit ")
		if getLightSensorValue(force=True): setColor(force=True)

		stepsTotal = 0
		seqN       = 8
		U.logger.log(20, "finding limits, second turn left %d times"%len(sensorDict["sequence"]))
		#time.sleep(5)
		if  sensorDict["sensor"][0]["status"] == 1:
			sensorDict["sensor"][0]["left"][seqN] = rightLimit - 0
		for nn in range(len(sensorDict["sequence"])-1):
			steps = move( int(oneEights*2), -1, force=20, stopIfMagSensor=[True,True] )
			stepsTotal += steps
			seqN -=1
			if pp: printLrLog("left  === ", nn, steps)
			if  sensorDict["sensor"][1]["status"] == 1:
				sensorDict["sensor"][1]["left"][seqN] = rightLimit - stepsTotal
			if  sensorDict["sensor"][0]["status"] == 1:
				sensorDict["sensor"][0]["left"][seqN] = rightLimit - stepsTotal
			#time.sleep(2)

		leftLimit = stepsTotal
	
		if getLightSensorValue(force=True): setColor(force=True)


		if pp: U.logger.log(20, unicode(sensorDict))
		if abs(rightLimit + leftLimit) > stepsIn360*2:
			addToBlinkQueue(text=["S","O","S"])

		time.sleep(0.1)

		maxStepsUsed  = int(min(stepsIn360*1.09,max(stepsIn360*0.99,rightLimit)))

		waitBetweenSteps 	= secondsTotalInDay / maxStepsUsed 
		if amPM1224 ==12:	waitBetweenSteps 	/= 2
		waitBetweenSteps /=speed

		currentSequenceNo = 0
		zeroPosition = lastPosition
		U.logger.log(20, " at position 0  ; waitBetweenSteps:%1f; maxStepsUsed:%d"%(waitBetweenSteps,maxStepsUsed))
		displayDrawLines(["wait:%.1f; nSteps:%d"%(waitBetweenSteps,maxStepsUsed), datetime.datetime.now().strftime("%a, %Y-%m-%d %H:%M")])
		time.sleep(2)
	except Exception, e:
		U.logger.log(40, u"Line {} has error={}".format(sys.exc_traceback.tb_lineno, e))

	return 

def printLrLog(lead,a,b, extra="", short=False):
	global sensorDict
	if short:
		U.logger.log(10, lead+ "%d %d %s"%(a,b,extra))
	else:
		U.logger.log(10, lead+ "%d %d %s\n0 : %s\n12:%s"%(a,b,extra,unicode(sensorDict["sensor"][0]),unicode(sensorDict["sensor"][1])))



# ########################################
# #########     blinks  ##########
# ########################################

def addToBlinkQueue(text =[], color=[1,1,1], stop = False, end=False, restore = True):
	global blinkThread, stopBlink

	try:
		if stop: 
			stopBlink =True
			time.sleep(1)
			U.logger.log(20, " clear queue bf %d" % blinkThread["queue"].qsize())
			blinkThread["queue"].queue.clear()
			U.logger.log(20, " clear queue af %d" % blinkThread["queue"].qsize())
			stopBlink =True
			return 

		if end: 
			stopBlink =True
			time.sleep(1)
			U.logger.log(20, " clear queue bf %d" % blinkThread["queue"].qsize())
			blinkThread["queue"].queue.clear()
			U.logger.log(20, " clear queue af %d" % blinkThread["queue"].qsize())
			blinkThread["thread"].join()
			return 

		add ={}
		if blinkThread["color"]   : add["color"] = color
		add["text"]    = text
		add["restore"] = restore
		stopBlink  = False
		blinkThread["queue"].put(add) 
	except Exception, e:
		U.logger.log(40, u"Line {} has error={}".format(sys.exc_traceback.tb_lineno, e))
	return

def blinkQueue():
	global blinkThread, stopBlink

	try:
		while True:
			while not blinkThread["queue"].empty():
				#print" checking queue size", actionQueue.qsize() 
				action = blinkThread["queue"].get()
				doBlink(action) 
				if blinkThread["end"]:
					sys.exit()
				if stopBlink: break
			if LastHourColorSetToRemember !=[]:
				setColor( blink=0, color=LastHourColorSetToRemember, force = False)
			if blinkThread["end"]:
				sys.exit()
			time.sleep(1)
		sys.exit()
	except Exception, e:
		U.logger.log(40, u"Line {} has error={}".format(sys.exc_traceback.tb_lineno, e))
	return



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
def setColor( blink=0, color=[1.,1.,1.], force = False):
	global colPWM, LastHourColorSet, secSinceMidnit,secSinceMidnit0, LastHourColorSetToRemember, timeAtlastColorChange
	global gpiopinNumbers

	try:
		lastC = LastHourColorSet

		if stopBlink: return 
		if blink != 0 :
			for p in range(len(gpiopinNumbers["pin_rgbLED"])):
				pin = gpiopinNumbers["pin_rgbLED"][p]
				if  blink == 1:
					if color[p] >= 0:
						setGPIOValue( pin, 1, amplitude= getIntensity(0.5, color[p], p))
				elif blink == -1: 
					setGPIOValue( pin, 0, )

			LastHourColorSet = -1


		else:
			if abs(secSinceMidnit0-lastC) > 30  and (time.time() - timeAtlastColorChange) >10 or force:
				cm = timeToColor(secSinceMidnit0)
				for RGBNumber in range(len(gpiopinNumbers["pin_rgbLED"])):
					pin = gpiopinNumbers["pin_rgbLED"][RGBNumber]
					setGPIOValue( pin, 1, amplitude=getIntensity(cm[RGBNumber], color[RGBNumber], RGBNumber ) )	
					#print "LED int: ", p, intens, lightSensorValue, " secs since last:", abs(secSinceMidnit-lastC)
				timeAtlastColorChange = time.time()
				LastHourColorSet = secSinceMidnit0
				LastHourColorSetToRemember = color
	except Exception, e:
		U.logger.log(40, u"Line {} has error={}".format(sys.exc_traceback.tb_lineno, e))
	return

# ------------------    ------------------ 
def getIntensity(Vin, colorFactor, RGBNumber):
	global lightShadowVsDown
	global lightOffBetweenHours
	global lightSensorValue
	global intensitySlope
	global intensityMin, intensityMax
	global intensityRGB, multiplyRGB
	global hour

	Vout = 0.3
	try:
		if lightShadowVsDown.find("normal") ==-1 : Vin *= 0.5
		if Vin ==0: return 0.
		if lightOffBetweenHours !=[0,0]:
			if ( (hour >= lightOffBetweenHours[0] and hour < lightOffBetweenHours[1]) or
				 (hour >= lightOffBetweenHours[0] and lightOffBetweenHours[0] > lightOffBetweenHours[1]) or
				 (hour <  lightOffBetweenHours[1] and lightOffBetweenHours[0] > lightOffBetweenHours[1])
				) :
				return 0
		## between 0 and 1
		Vout=  min( intensityMax, max( intensityMin, float(Vin) * colorFactor * intensitySlope *intensityRGB[RGBNumber] * lightSensorValue) * multiplyRGB[RGBNumber] 	)
		U.logger.log(10, u"Vout:{:.3f}, Vin:{:.3f}, RGB:{}, colorFactor:{},  intensityMax:{}, intensityMin:{},  intensitySlope:{}, lightSensorValue:{:.4f}".format(Vout, Vin, RGBNumber, colorFactor, intensityMax, intensityMin,  intensitySlope, lightSensorValue))
	except Exception, e:
		U.logger.log(40, u"Line {} has error={}".format(sys.exc_traceback.tb_lineno, e))

	return Vout


# ------------------    ------------------ 
# ------------------    ------------------ 
def testIfBlink( ):
	global speed, blinkHour, hour
	if speed == 1:
		if second % 60 < 20 and blinkHour != hour:
			blinkHour = hour
			addToBlinkQueue(text=["o", "n"], color=[1,1,1], stop=False, end=False, restore=True)
	return 

# ------------------    ------------------ 
def blinkLetters(letters, color):
	global morseCode
	global longBlink, shortBlink, breakBlink
	global stopBlink
	for l in letters:
		if l in morseCode:
			for sig in morseCode[l]:
				if sig == 1:	blink(longBlink,  breakBlink, 1, color)
				else:   		blink(shortBlink, breakBlink, 1, color)
			time.sleep(breakBlink)
	return

# ------------------    ------------------ 
def blink(on, off, n, color):
	global stopBlink
	for i in range(n):
		if stopBlink: return 
		setColor(blink=1, color=color)
		time.sleep(on)	
		if stopBlink: return 
		setColor(blink=-1, color=color)
		time.sleep(off)	
	return 


# ------------------    ------------------ 
def settimeToColor():
	global times, rgb, av
	times = [   0, 		   4*60*60,	   8*60*60,		11*60*60,	  13*60*60,		 16*60*60,	20*60*60,	 24*60*60]
	rgb   = [ [20,20,20], [20,20,20], [80,30,30], [80,80,100], [80,80,100], [100,100,100], [100,70,70], [100,70,70] ]
	for ii in range(0, len(times)):
		av = (rgb[ii][0]+rgb[ii][1]+rgb[ii][2])/3.
		rgb[ii][0] /=av 
		rgb[ii][1] /=av 
		rgb[ii][2] /=av 
# ------------------    ------------------ 
def timeToColor(tt):
	global times, rgb, av

	try:
		rgbout= rgb[0]
		for ii in range(1, len(times)):
			if tt > times[ii]: continue
			dt = (tt-times[ii-1])/(times[ii]-times[ii-1]) 
			for rr in range(3):
				rgbout[rr] = (dt * (rgb[ii][rr]-rgb[ii-1][rr]) + rgb[ii-1][rr])
			break
	except Exception, e:
		U.logger.log(40, u"Line {} has error={}".format(sys.exc_traceback.tb_lineno, e))

	return rgbout

# ------------------    ------------------ 
def getLightSensorValue(force=False):
	global lightSensorValue, lastlightSensorValue, lastTimeLightSensorValue, lastTimeLightSensorFile, lightSensorValueRaw, lightSensNorm
	global lightSensMax, lightSensMin
	try:
		tt0 = time.time()
		if (tt0 - lastTimeLightSensorValue < 2) and not force:		return False
		if not os.path.isfile(G.homeDir+"temp/lightSensor.dat"):	return False
		rr , raw = U.readJson(G.homeDir+"temp/lightSensor.dat")
		if rr == {}:
			time.sleep(0.1)
			rr, raw = U.readJson(G.homeDir+"temp/lightSensor.dat")
		os.system("sudo rm "+G.homeDir+"temp/lightSensor.dat")
		if rr == {} or "time" not in rr: 							return False
		tt = float(rr["time"])
		if tt == lastTimeLightSensorFile:						 	return False
		lastTimeLightSensorFile = tt
		lightSensorValueREAD = float(rr["light"])
		sensor = rr["sensor"]
		if   sensor == "i2cTSL2561":	maxRange = 2000.
		elif sensor == "i2cOPT3001":	maxRange = 2000.
		elif sensor == "i2cVEML6030":	maxRange = 700.
		elif sensor == "i2cIS1145":		maxRange = 2000.
		else:							maxRange = 1000.
		if lightSensNorm != 0:		maxRange = lightSensNorm

		lightSensorValueRaw = lightSensorValueREAD/maxRange    
		lightSensorValueRaw = max(lightSensMin, lightSensorValueRaw)
		if lightSensorValueRaw >= lightSensMax:
			lightSensorValueRaw = 1.
		# lightSensorValueRaw should be now between ~ 0.001 and ~1.
		if force:	
			lightSensorValue = lightSensorValueRaw
			return True
		if (  abs(lightSensorValueRaw-lastlightSensorValue) / (max (0.005, lightSensorValueRaw+lastlightSensorValue))  ) < 0.05: return False
		lightSensorValue = (lightSensorValueRaw*1 + lastlightSensorValue*9) / 10.
		lastTimeLightSensorValue = tt0
		U.logger.log(20, "lightSensorValue read:{:.0f}, raw:{:.3f};  new used:{:.4f};  last:{:.4f}; maxR:{:.1f}".format(lightSensorValueREAD, lightSensorValueRaw, lightSensorValue, lastlightSensorValue,  maxRange))
		lastlightSensorValue = lightSensorValue
		return True
	except Exception, e:
		U.logger.log(40, u"Line {} has error={}".format(sys.exc_traceback.tb_lineno, e))
	return False


# ########################################
# #########   time   funtions ############
# ########################################
# ------------------    ------------------ 
def getTime():
	global speed, amPM1224
	global hour, minute, second
	global secSinceMidnit, secSinceMidnit0
	global secForTestStart
	global timeShift

	try:
		if speed !=1.0:
			secSinceMidnit = (time.time() - secForTestStart)*speed
		else:
			today = datetime.date.today()
			secSinceMidnit  = (time.time() - time.mktime(today.timetuple()))
		secSinceMidnit -= timeShift
		secSinceMidnit  = int(secSinceMidnit)

		secSinceMidnit0 = secSinceMidnit
		#secSinceMidnit += lightShadowVsDown
		if amPM1224 == 12:
			secSinceMidnit *= 2 
		secSinceMidnit %= secondsTotalInDay

		hour   = int( secSinceMidnit0/(60*60) )
		minute = int( (secSinceMidnit0 - hour*60*60) /60 )
		second = int( secSinceMidnit0 - hour*60*60 - minute*60)
	except Exception, e:
		U.logger.log(40, u"Line {} has error={}".format(sys.exc_traceback.tb_lineno, e))

		return 


#
# ------------------    ------------------ 
def getSensors(doPrint=False):
	global 	sensorDict
	try:
		anyChange = False
		for n in range(len(sensorDict["sensor"])): # 90,1 = reed swithes 0/12 oClock,  2,3 are boundary switches
			newValue = getPinValue( "pin_sensor"+str(n), ON=sensorDict["sensor"][n]["ON"], doPrint=doPrint )
			if doPrint:  U.logger.log(20, u"sens:   pin_sensor{}  V:{}; oldV:{} oldV-1:{}".format(n, newValue, sensorDict["sensor"][n]["newValue"], sensorDict["sensor"][n]["lastValue"]) )
			if newValue != sensorDict["sensor"][n]["newValue"]:
				anyChange = True
				sensorDict["sensor"][n]["lastValue"]	= sensorDict["sensor"][n]["newValue"]
				sensorDict["sensor"][n]["clicked"]		= "Y"
				sensorDict["sensor"][n]["newValue"]		= newValue

				if newValue == 1:
					sensorDict["sensor"][n]["status"]	= 1
				else:
					if n < 2: # only for reed switches, the boundary switches are reset by the test pgm
						sensorDict["sensor"][n]["status"]	= 0
 
	except Exception, e:
		U.logger.log(40, u"Line {} has error={}".format(sys.exc_traceback.tb_lineno, e))


			
	return 
			

# ------------------    ------------------ 
def fixBoundaries():
	global sensorDict
	global stepsIn360
	global inFixBoundaryMode
	global limitSensorTriggered
	global currentSequenceNo

	try:
		limitSensorTriggered = 0

		sens = sensorDict["sensor"]
		sens[2]["status"] = 0
		sens[3]["status"] = 0
		if inFixBoundaryMode == 0: return 


		currentSequenceNo = 0
		completTurns = 1.5
		totStepsToFix = int( max( abs(leftBoundaryOfCable-rightBoundaryOfCable)*0.6, int(stepsIn360*completTurns)  ) )
		turns = float(totStepsToFix/float(stepsIn360))

		U.logger.log(20, "fixingBoundary 1, steps: {}; turns: {:.1f}*360; leftB: {}; rightB: {}; starting due to inFixBoundaryMode:{}; capS:{}; switchS:{}".format(totStepsToFix, turns, leftBoundaryOfCable, rightBoundaryOfCable, inFixBoundaryMode, sens[2]["status"], sens[3]["status"]))

		if inFixBoundaryMode ==1:
			stepsDone = move( totStepsToFix, 1,  force=0, stopIfMagSensor=[False,False],  updateSequence=False, fast=True , stopIfBoundarySensor=[False,True])
		else:
			stepsDone = move( totStepsToFix, -1, force=0, stopIfMagSensor=[False,False],  updateSequence=False, fast=True , stopIfBoundarySensor=[True,False])
		U.logger.log(20, "fixingBoundary after 1, left-capS: {}; right-switchS: {}; stepsDone: {}".format(sens[2]["status"],sens[3]["status"],stepsDone))

		if inFixBoundaryMode == -1:
			if sens[2]["newValue"] == 1:
				U.logger.log(20, "fixingBoundary 2; after  +1(right) {} direction steps forward".format(totStepsToFix))
				sens[2]["status"] = 0
				sens[3]["status"] = 0
				stepsDone = move( totStepsToFix,  1, force=0, stopIfMagSensor=[False,False],  updateSequence=False, fast=True, stopIfBoundarySensor=[False,True])
				getSensors()
				U.logger.log(20, "fixing  after 2.1: left-capS: {}; right-switchS: {}; stepsDone {}".format(sens[2]["status"], sens[3]["status"],stepsDone))
		else:
			if sens[3]["newValue"] == 1:
				U.logger.log(20, "fixing  3; after  +1(lft) {} direction steps backwards".format(totStepsToFix) )
				sens[2]["status"] = 0
				sens[3]["status"] = 0
				stepsDone = move( totStepsToFix, -1, force=0, stopIfMagSensor=[False,False],  updateSequence=False, fast=True, stopIfBoundarySensor=[True,False])
				getSensors()
				U.logger.log(20, "fixingBoundary  after 3.1, left-capS:%d; right-switchS: {}; stepsDone: {}".format(sens[2]["status"], sens[3]["status"], stepsDone))

		if sens[2]["newValue"] == 0: sens[2]["status"] = 0
		if sens[3]["newValue"] == 0: sens[3]["status"] = 0

		if  sens[2]["status"]==0 and sens[3]["status"]==0: 
			saveFixBoundaryMode(set=0, tt=time.time()-1000)
			return 

		if sens[2]["status"] == 1:	saveFixBoundaryMode(set=1, tt=time.time())
		if sens[3]["status"] == 1:	saveFixBoundaryMode(set=-1, tt=time.time())
		U.logger.log(20, "fixingBoundary end, redo due to: capS:{}; switchS:{}; stepsDone:{}".format(sens[2]["status"], sens[3]["status"], stepsDone))
		U.restartMyself(reason="fix boundaries  failed", delay=5)
	except Exception, e:
		U.logger.log(40, u"Line {} has error={}".format(sys.exc_traceback.tb_lineno, e))


# ------------------    ------------------ 
def doSunDialShutdown():
	U.logger.log(40, " setting shutdown params ")
	try: displayClear(show=True, force=True)
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

	except Exception, e:
		U.logger.log(40, u"Line {} has error={}".format(sys.exc_traceback.tb_lineno, e)+"   bad sensor data")
	return 

# ------------------    ------------------ 
def getOffset():
	global useoffsetOfPosition, offsetOfPosition, lightShadowVsDown, stepsIn360, totalStepsDone, lasttotalStepsDone
	try:
		useoffsetOfPosition = int(offsetOfPosition)
		if lightShadowVsDown.find("normal") ==-1:
			 useoffsetOfPosition += stepsIn360/2
		if useoffsetOfPosition !=0:
			# bring between -800 and 800 
			if   useoffsetOfPosition > stepsIn360: 	useoffsetOfPosition -= stepsIn360
			if 	-useoffsetOfPosition > stepsIn360:	useoffsetOfPosition += stepsIn360
			if 	-useoffsetOfPosition > stepsIn360:	useoffsetOfPosition += stepsIn360
			#bring between -400.. 400 eg 700 --> -100  ; -700--> 100
			if    useoffsetOfPosition > stepsIn360/2: 	useoffsetOfPosition -= stepsIn360
			elif -useoffsetOfPosition > stepsIn360/2:	useoffsetOfPosition += stepsIn360

			if useoffsetOfPosition >=0:			dir = 1
			else:								dir = -1
			U.logger.log(30, "moving  to useoffsetOfPosition:{}, offsetOfPosition:{}, dir:{}".format(useoffsetOfPosition,offsetOfPosition , dir))
			move(abs(useoffsetOfPosition), dir)
			U.logger.log(30, "at new Offset")
			time.sleep(2)
		totalStepsDone 		= 0
		lasttotalStepsDone	= 0

	except Exception, e:
		U.logger.log(40, u"Line {} has error={}".format(sys.exc_traceback.tb_lineno, e)+"   bad sensor data")




def execSunDial(reqSpeed):

	global clockDict, clockLightSet, useRTC
	global sensor, output, inpRaw
	global oldRaw,	lastRead, inp
	global timeZones, timeZone
	global doReadParameters
	global networkIndicatorON
	global lastStep, colPWM,  LastHourColorSet
	global intensity
	global maxStepsUsed, startSteps, stepsIn360, nStepsInSequence
	global speed, amPM1224, motorType
	global gpiopinNumbers, SeqCoils
	global blinkHour
	global t0
	global printON
	global totalStepsDone
	global hour, minute, second
	global secSinceMidnit, secSinceMidnit0
	global webAdhoc
	global longBlink, shortBlink, breakBlink
	global morseCode
	global whereIs12
	global minStayOn
	global RestartLastOff 
	global clockDictLast
	global blinkThread, stopBlink
	global PIGPIO, pwmRange
	global colPWM
	global speedDemoStart
	global timeAtlastColorChange
	global overallStatus
	global buttonDict, sensorDict
	global currentSequenceNo, inbetweenSequences
	global lightSensorValue, lastlightSensorValue, lastTimeLightSensorValue, lastTimeLightSensorFile, lightSensorValueRaw
	global pinsToName
	global menuPosition
	global lastExpireDisplay
	global lightSensNorm
	global intensityRGB
	global intensityMax, intensityMin, intensitySlope
	global inFixBoundaryMode
	global currentlyMoving
	global limitSensorTriggered
	global lightShadowVsDown
	global displayStarted
	global offsetOfPosition, useoffsetOfPosition
	global lastPosition, zeroPosition, rightBoundaryOfCable, leftLimit
	global secForTestStart
	global lastFixBoundaryMode
	global lastsaveParameters
	global stopLoop
	global sunDialParameters
	global eth0IP, wifi0IP
	global secondsTotalInDay, secondsTotalInHalfDay
	global LastHourColorSetToRemember
	global hour, minute, second
	global lightOffBetweenHours
	global waitBetweenSteps
	global startWebServerSTATUS, startWebServerINPUT
	global timeShift, multiplyRGB

	morseCode= {"A":[0,1], 		"B":[1,0,0,0],	 "C":[1,0,1,0], "D":[1,0,0], 	"E":[0], 		"F":[0,0,1,0], 	"G":[1,1,0],	"H":[0,0,0,0], 	"I":[0,0],
				"J":[0,1,1,1], 	"K":[1,0,1], 	"L":[0,1,0,0], 	"M":[1,1], 		"N":[1,0], 		"O":[1,1,1], 	"P":[0,1,1,0],	"Q":[1,1,0,1], 	"R":[0,1,0],
				"S":[0,0,0], 	"T":[1], 		"U":[0,0,1], 	"V":[0,0,0,1], 	"W":[0,1,1], "X":[1,0,0,1], 	"%Y":[1,0,1,1], 	"Z":[1,1,0,0],
				"0":[1,1,1,1,1], "1":[0,1,1,1,1], "2":[0,0,1,1,1], "3":[0,0,0,1,1], "4":[0,0,0,0,1], "5":[0,0,0,0,0], "6":[1,0,0,0,0], "7":[1,1,0,0,0], "8":[1,1,1,0,0], "9":[1,1,1,1,0],
				"s":[0], # one short
				"l":[1], # one long
				"b":[0,0,0,1]}  # beethoven ddd DAAA

	startWebServerSTATUS	= ""
	startWebServerINPUT		= ""
	timeShift				= 0
	lightOffBetweenHours	= [0,0]
	sunDialParameters		= {}
	lastsaveParameters		= time.time()
	lastFixBoundaryMode		= 0
	useoffsetOfPosition		= 0
	offsetOfPosition		= 0
	lightShadowVsDown		="normal"
	limitSensorTriggered	= 0
	currentlyMoving			= time.time() + 10000.
	inFixBoundaryMode		= 0
	lightSensNorm			= 1000000
	lastExpireDisplay		= time.time()
	menuPosition			= ["",""]
	pinsToName				= {}
	lightSensorValue		= 0.5
	lastlightSensorValue	= 0.5
	lastTimeLightSensorValue =0
	lastTimeLightSensorFile = 0
	lightSensorValueRaw		= 0
	secSinceMidnit0			= 0
	inbetweenSequences		= False
	currentSequenceNo		= 0
	overallStatus 			="OK"
	buttonDict				= {}
	sensorDict				= {}
	timeAtlastColorChange	= 0
	speedDemoStart			= -1

	PIGPIO					= ""
	pwmRange				= 0
	colPWM 					= {}

	longBlink			  	= 0.6
	shortBlink			  	= 0.2
	breakBlink			  	= 0.5

	webAdhoc			  	= ""
	# constants 
	adhocWebLast		  	= 0
	motorType			  	= "xx"
	startSteps			  	= 0
	secondsTotalInDay     	= 60.*60.*24.
	secondsTotalInHalfDay 	= 60.*60.*12
	intensitySlope     		= 1.
	intensityMax      		= 1.
	intensityMin      		= 0.0045

	intensityRGB			= [.65,.85,1.] # rel RGB scale
	multiplyRGB				= [1,1,1] # miultiply to RGB value
	ave  = (intensityRGB[0]+intensityRGB[1]+intensityRGB[2])/3.
	intensityRGB			= [intensityRGB[0]/ave, intensityRGB[1]/ave, intensityRGB[2]/ave]

	amPM1224			  	= 24
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
	debug					= 0
	loopCount				= 0
	sensor					= G.program
	lastGPIOreset	 		= 0
	G.lastAliveSend	 		= time.time() -1000
	loopC			 		= 0
	lastShutDownTest 		= -1
	lastRESETTest	 		= -1
	printON 				= True
	totalStepsDone 				= 0
	t0						= time.time()
	blinkHour				= -1
	nextStep 				= 1
	whereIs12 				= {-1:-1, 1:-1, "average":-1, "active":False}
	clockDictLast			= {}
	LastHourColorSetToRemember =[]
	secForTestStart 		= time.time()
	lastPosition			= 0 
	zeroPosition			= 0

	U.setLogging()


	U.logger.log(30, "====== starting ======")


	try:

		if reqSpeed != 1: 
			speed = reqSpeed
			speedDemoStart = time.time()
			U.logger.log(30, "demo mode,  speed = {}".format(int(speed)))
		else:
			speed = 1
			speedDemoStart = -1


		myPID		= str(os.getpid())
		U.killOldPgm(myPID, G.program+".py")# kill old instances of myself if they are still running


		checkNumberOfRestarts()

		try: 
			displayStart()
			displayStarted = True
		except:
			U.logger.log(40, " display did not start")
			displayStarted = False
	

		displayDrawLines(["Status:   starting up", ".. read params, time..",  datetime.datetime.now().strftime("%a, %Y-%m-%d %H:%M")])



		setgpiopinNumbers()

		setupTimeZones()
		#print "current tz:", currTZ,JulDelta,JanDelta,NowDelta, timeZones[currTZ+12], timeZones

		getParameters()


		if readParams() ==3:
			U.logger.log(40, " parameters not defined")
			U.checkParametersFile("parameters-DEFAULT-sunDial", force = True)
			time.sleep(20)
			doSunDialShutdown()
			U.restartMyself(reason=" bad parameters read", doPrint = True)

		U.getIPNumber() 
		eth0IP, wifi0IP, G.eth0Enabled, G.wifiEnabled = U.getIPCONFIG()

		setMotorOFF()

		getPositions()

		getTime()

		U.echoLastAlive(G.program)

		#U.logger.log(30, "gpiopinNumbers:"+unicode(gpiopinNumbers))

		settimeToColor()

		stopBlink	= False
		blinkThread = {"color":True, "stop":False, "end":False, "queue": Queue.Queue(), "thread": threading.Thread(name=u'blinkQueue', target=blinkQueue, args=())}	
		blinkThread["thread"].start()



		### here it starts 
		lightSensorValue = 0.1
		getLightSensorValue(force=True)
		setColor(force=True)

		U.setStartwebserverSTATUS()
		U.setStartwebserverINPUT()
		updatewebserverStatus(status="starting")
		# for display on clock show info web site and change wifi and country settings
		MENUSTRUCTURE[1][0][0][0] ="{}:{}".format(G.ipAddress,startWebServerSTATUS)
		MENUSTRUCTURE[1][0][2][0] ="{}:{}".format(G.ipAddress,startWebServerINPUT)

		findBoundariesOfCable()


		## check if out of boundary, if yes: fix it 
		boundariesWhereFixed = False
		if inFixBoundaryMode != 0:
			updatewebserverStatus(status="fixing boundaries")
			delta = time.time()-lastFixBoundaryMode
			U.logger.log(30, "in FIX boundary mode, last one {:.0f} sec ago".format(delta))
			if delta < 60: 
				resetBoundariesOfCable()
				saveFixBoundaryMode(tt=time.time())
				U.restartMyself(reason=" fix boundary twice in a minute") 
			displayDrawLines(["Status:     ","in FIX boundary mode",  datetime.datetime.now().strftime("%a, %Y-%m-%d %H:%M")])
			addToBlinkQueue(text=["s","o","s"])
			fixBoundaries()
			boundariesWhereFixed = True
			saveFixBoundaryMode(set=0,tt=time.time() )
	
		U.echoLastAlive(G.program)


		#addToBlinkQueue(text = ["S","T","A","R","T"][1,1,1],)
		#time.sleep(3)

		displayDrawLines(["Status:     finding",".. L/R  Stop-Limits",  datetime.datetime.now().strftime("%a, %Y-%m-%d %H:%M")])

		waitBetweenSteps 	= secondsTotalInDay     / maxStepsUsed 


		if boundariesWhereFixed or not fastStart():
			## here we find mag sensor 0/12 or A/B limits:
			findLeftRight()

		U.echoLastAlive(G.program)


		getLightSensorValue(force=True)
		setColor(force=True)
		sleepDefault = waitBetweenSteps/(5*speed)


		U.logger.log(30, "\n=========clock starting at zero postion, parameters:\nspeed:{:.1f}, totalStepsDone:{}, sleepDefault:{:.1f},\nwaitBetweenSteps:{:.2f},  amPM1224:{}, secSinceMidnit:{:.1f}, secSinceMidnit0:{:.1f}, zero@{}\nintensity Min:{}, Max:{}, Slope:{}, lightSNorm:{}, LightMin:{}, lightMax:{}, RGB:{} "
						 .format(speed, totalStepsDone, sleepDefault, waitBetweenSteps, amPM1224, secSinceMidnit,secSinceMidnit0, zeroPosition,intensityMin,intensityMax, intensitySlope, lightSensNorm, lightSensMin, lightSensMax, intensityRGB))
		time.sleep(2)



		getOffset()

		nextStep = 1


		U.logger.log(30, "eth0IP:%s:, wifi0IP:%s:, G.eth0Enabled:%s, G.wifiEnabled:%s"%(eth0IP, wifi0IP, unicode(G.eth0Enabled), unicode(G.wifiEnabled)))

		displayShowStandardStatus(force=True)

		expireDisplay = 50
		lastExpireDisplay = time.time()
		inFixBoundaryMode =0

		lastMove = time.time() - waitBetweenSteps
		totalStepsDone = 0
		stopLoop = False
		saveParameters(force = True)
		while True:
				while stopLoop:
					sleep(3)
				saveParameters()

				if speedDemoStart > 1 and time.time() - speedDemoStart > 300:
					U.restartMyself(reason=" resetting speed to normal after 300 secs", doPrint = True)

				if limitSensorTriggered != 0:
			
					U.restartMyself(reason="entering fixmode,  trigger of boundaries", doPrint = True)

				getTime()

				##  here we move
				lastMove = testIfMove( waitBetweenSteps, lastMove )
				##  

				nextMove = lastMove + waitBetweenSteps
				testIfRewind()
				sleep =  sleepDefault
				testIfBlink()
				slept = 0
				lastDisplay = 0
				startSleep = time.time()
				sleep = nextMove - startSleep
				endSleep = startSleep + sleep
				minSleep = max(0.1, min(0.2, sleep))
				ii = 1000
				lastDisplay = time.time()
				#print "	sleep ", sleep," nextMove", nextMove,"minSleep",minSleep,"tt", time.time()
				U.echoLastAlive(G.program)

				while ii > 0:
					readCommand()
					if getLightSensorValue():
						setColor(force=True)
					elif (  abs(lightSensorValueRaw - lightSensorValue) / (max(0.005, lightSensorValueRaw + lightSensorValue))  ) > 0.05:
							#print " step up down light: ",lightSensorValue, lightSensorValueRaw, (lightSensorValueRaw*1 + lightSensorValue*9) / 10.
							lightSensorValue = (lightSensorValueRaw*1 + lightSensorValue*9) / 10.
							lastlightSensorValue = lightSensorValue
							setColor(force=True)
					if ii % 30 == 0:
						U.echoLastAlive(G.program)
					ii -= 1
					time.sleep(minSleep)
					slept += minSleep

					if U.checkifRebooting(): 
						displayShowShutDownMessage()
						time.sleep(3)
						doSunDialShutdown()
						time.sleep(1)
						exit()


					tt = time.time()
					if tt >= endSleep: break
					if tt - lastDisplay > 5:
						if tt - lastExpireDisplay < expireDisplay:
							if G.wifiType =="adhoc": 	overallStatus = "wifiAdhoc"
							else:						overallStatus = "ok"
							displayShowStandardStatus()
							#print "main loop showStandardStatusDisplay"
						else:
							displayMenuSubAreaActive = -2
							displayClear(show = True)
						updatewebserverStatus("normal")

						saveParameters()
						if readParams() < -1:
							U.restartMyself(reason="parameters changed significantly", doPrint = True)
						lastDisplay = tt

	

	except Exception, e:
		U.logger.log(40, u"Line {} has error={}".format(sys.exc_traceback.tb_lineno, e))
	stopBlink = True
	time.sleep(1)
	return



#######################################
# #########       main        ##########
# ######################################
try:   	reqSpeed = float(sys.argv[1])
except:	reqSpeed = 1.

execSunDial(reqSpeed)
exit()
	


		

