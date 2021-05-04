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
G.program = "sundial"

global sundialVersion
sundialVersion			= 16.1



######### constants #################

##               top option               selection, command
MENUSTRUCTURE =[[],[]]
MENUSTRUCTURE[0]=[	
					[" Info @ http:",			"setMenuParam=''"],#0
					[" light ON/off",			"setMenuParam=''"],#1
					[" light off",				"setMenuParam=''"],#2
					[" 12 or 24 clock",			"setMenuParam=''"],#3
					[" mode light/shadow",		"setMenuParam=''"],#4
					[" demo speed",				"setMenuParam=''"],#5
					[" network",				"setMenuParam=''"],#6
					[" light intensity",		"setMenuParam=''"],#7
					[" restart",				"setMenuParam=''"],#8
					[" adhoc Wifi",				"setMenuParam=''"],#9
				]
#					[" WiFi SID",				"setMenuParam='WiFissidString'"],
#					[" WiFi Passwd",			"setMenuParam='WiFiPassString'"],
#				]
#                         [menu text          ,  function to call ],  [ , ],  [ , ]   ..
MENUSTRUCTURE[1]=[	
					[	[" http:ip#",""], 										[" setup..", ""											],	[" ip#:8010",""]													], #0
					[	[" always on",   		"setLightOff(0,0)"],			[" off",   					"setLightOff(0,24)"				],																	], #1
					[	[" 0-6",   				"setLightOff(0,6)"],			[" 23-6",   				"setLightOff(23,6)"				],	[" 0-7",   "setLightOff(0,7)"], [" 23-7", 	"setLightOff(23,7)"]], #2
					[	[" 12",   				"set1224(12)"],					[" 24", 					"set1224(24)"					],																	], #3
					[	[" normal sundial",		"setSunMode('normal')"],		[" Sun straight down",	"setSunMode('down')"	],																				], #4
					[	[" normal", "setSpeed(1)"],								[" demo speed slow",		"setSpeed(55)"					],	[" demo speed fast", "setSpeed(400)"], 							], #5
					[	[" WiFi restart", 		"doRestartWiFi()"],				[" ETH restart", 		"doRestartETH()"],																						], #6
					[	[" increase",   		"increaseLEDSlope()"],			[" decrease", 	"decreaseLEDSlope()"						],																	], #7
					[	[" restart", 			"doRestartMaster()"],			[" reboot sys", 		"doRebootPi()"],					[" shutdown",		"doHaltPi()"], 									], #8
					[	[" start",   			"setAdhocWiFi('start')"],		[" stop",		"setAdhocWiFi('stop')"						],																	], #9 
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
		return 0
	except Exception, e:
		U.logger.log(40, u"Line {} has error={}".format(sys.exc_traceback.tb_lineno, e))
	return -1

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

		if displayStarted <0: return 
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
		if displayStarted <0: return 

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
		if displayStarted <0: return 

		if displayPriority > 0: 
			if time.time() - displayPriority > waitForDisplayToRest:
				displayPriority = 0
	
		if prio < displayPriority: return 
		displayPriority = prio 
		lastLines 				= ["","","","","","","",""]


		if inverse: fill=255
		else:		fill=0

		#print "clearDisplay", area, inverse, fill
		if area == []:
			draw.rectangle((0, 0, xPixels, yPixels), outline=0, fill=fill)
		else:
			draw.rectangle(area, outline=0, fill=fill)
		if show: displayDoShowImage()
	except Exception, e:
		U.logger.log(40, u"Line {} has error={}".format(sys.exc_traceback.tb_lineno, e))
		displayStarted = -time.time()
	return

# ------------------    ------------------ 
def displayComposeMenu(useLevel, area, subArea, nLines):
	global setMenuParam, charString
	global displayStarted

	try:
		if displayStarted <0: return 

		lines =[]
		top   = MENUSTRUCTURE[0]
		U.logger.log(10,"useLev:{}, aerea:{}, subA:{}, nLines:{}, top[area][0]:s{}".format(useLevel, area, subArea, nLines, top[area][0]) )

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
				U.logger.log(10, "start:{},  end:{},  setMenuParam:{},  str:{}".format(start, end, setMenuParam, charString) )
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
	if displayStarted <0: return 
	if displayMenuLevelActive ==0:	nLines = 4
	else:							nLines = 5
	displayComposeMenu(displayMenuLevelActive, displayMenuAreaActive, displayMenuSubAreaActive, nLines)
	displayDoShowImage()

# ------------------    ------------------ 
def displayDoShowImage():
	global imData, outputDev
	global displayStarted
	if displayStarted <0: return 
	outputDev.displayImage(imData)


# ------------------    ------------------ 
def displayShowStandardStatus(force=False):
	global overallStatus, totalStepsDone, maxStepsUsed, sensorDict, amPM1224, sundialVersion
	try:
		displayDrawLines(["St:{}; Clk:{}; V:{:.1f}".format(overallStatus, amPM1224, sundialVersion), "@ Pos.: {}/{}".format(totalStepsDone,maxStepsUsed),  "IP#:{}".format(G.ipAddress),  "Wifi:{};".format(getWifiInfo(longShort=1)),   datetime.datetime.now().strftime("%a, %Y-%m-%d %H:%M")])
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
	global lightSensorValue, lightSensNorm, lightSensNormDefault, intensityRGB
	global numberOfStepsCableAllows, stepsIn360, maxStepsUsed, totalStepsDone, offsetOfPositionCount, zeroPositionCount
	global leftBoundaryOfCableCount, rightBoundaryOfCableCount, numberOfStepsCableAllows
	global sensorDict
	global intensityMax, intensityMin, intensitySlope
	global timeShift
	global sundialVersion
	global currentRGBValue
	global times, rgb
	global uptime


	try: 
		statusData		= []
		cc = timeToColor(secSinceMidnit)
		tz = U.getTZ()
		out1  = ""
		out2 = ""
		out3 = ""
		out4 = ""
		for h in range(24):
			rgbc = timeToColor(h*3600)
			if    h < 6:	out1 += "{:03d},{:03d},{:03d} ".format(int(rgbc[0]*100), int(rgbc[1]*100), int(rgbc[2]*100) ) 
			elif  h < 12:	out2 += "{:03d},{:03d},{:03d} ".format(int(rgbc[0]*100), int(rgbc[1]*100), int(rgbc[2]*100) ) 
			elif  h < 18:	out3 += "{:03d},{:03d},{:03d} ".format(int(rgbc[0]*100), int(rgbc[1]*100), int(rgbc[2]*100) ) 
			else:			out4 += "{:03d},{:03d},{:03d} ".format(int(rgbc[0]*100), int(rgbc[1]*100), int(rgbc[2]*100) ) 
		xxx = []
		xxx.append("sundial Current status" )
		xxx.append("update-time........... ={}  TZ: {}".format(datetime.datetime.now().strftime(u"%H:%M:%S"), tz) )
		xxx.append("up-since.............. ={}".format(uptime) )
		xxx.append("IP-Number............. ={}".format(G.ipAddress))
		xxx.append('to set parameters..... =click on: <a href="http://{}:8010" style="color:rgb(255,255,255)">{}:8010 </a>'.format(G.ipAddress,G.ipAddress))
		xxx.append("WiFi enabled.......... ={} - id={}".format(getWifiInfo(longShort=1), G.wifiID) )
		xxx.append("opStatus.............. ={}".format(status) )
		xxx.append("version............... ={:.1f}".format(sundialVersion) )
		xxx.append("12/24 mode............ ={}".format(amPM1224) )
		xxx.append("shadow/SUN mode....... ={}".format(lightShadowVsDown) )
		xxx.append(" ")
		xxx.append("LED:")
		xxx.append("Current output........ =R:{:.1f}, G:{:.1f}, B:{:.1f}".format(int(currentRGBValue[0]*100),int(currentRGBValue[1]*100),int(currentRGBValue[2]*100))  )
		xxx.append("Slope; [range]........ ={:.2f};  [{:.4f} ... {:.1f}]".format(intensitySlope, intensityMin, intensityMax  ) )
		xxx.append("RGB multiplier set @.. =R:{:.2f}, G:{:.2f}, B:{:.2f} - 100=normal".format(multiplyRGB[0]*100, multiplyRGB[1]*100, multiplyRGB[2]*100)  )
		xxx.append("RGB weight factors.... =R:{:.0f}, G:{:.0f}, B:{:.0f} - for white light".format(intensityRGB[0]*100, intensityRGB[1]*100, intensityRGB[2]*100)  )
		xxx.append("Color (RGB) / day")
		xxx.append("current..RGB-Color.... ={:03d},{:03d},{:03d}".format(int(cc[0]*100), int(cc[1]*100), int(cc[2]*100) ) )
		xxx.append("early morning...00..05 ={}".format(out1.strip()) )
		xxx.append("morning.........06..11 ={}".format(out2.strip()) )
		xxx.append("afternoon.......12..17 ={}".format(out3.strip()) )
		xxx.append("evening.........18..23 ={}".format(out4.strip()) )
		xxx.append("Light Sensor:")
		xxx.append("Current value......... ={:.3f}".format(lightSensorValue) )
		xxx.append("Slope; [range]........ ={:.2f};  [{:.3f} ... {:.1f}]".format(lightSensNormDefault/lightSensNorm, lightSensMin, lightSensMax) )
		xxx.append(" ")
		xxx.append("Mechanical Hardware:")
		xxx.append("Max steps Cable allows ={}".format(numberOfStepsCableAllows ) )
		xxx.append("Steps in 360.......... ={}".format(stepsIn360 ) )
		xxx.append("Max Steps Used........ ={} from 0 to 24/12".format(maxStepsUsed) )
		xxx.append("At Step Now........... ={}".format(totalStepsDone) )
		xxx.append("Zero Position (HH=0)@. ={}".format(zeroPositionCount) )
		xxx.append("offset HH=0 - offset.. ={}".format(offsetOfPositionCount) )
		xxx.append("leftBoundary.......... ={}".format(leftBoundaryOfCableCount) )
		xxx.append("rightBoundary......... ={}".format(rightBoundaryOfCableCount) )
		xxx.append("delta Boundary........ ={}".format(numberOfStepsCableAllows) )
		xxx.append(" ")
		xxx.append("Debug info:")
		xxx.append("Sensor 0.............. ={}".format(sensorDict["sensor"][0]["clicked"]) )
		xxx.append("Sensor 12............. ={}".format(sensorDict["sensor"][1]["clicked"]) )
		xxx.append("Sensor 0 marksR....... ={}".format(unicode(sensorDict["sensor"][0]["right"]).replace("[","").replace("]","").replace(" ","").replace("-1","-")) )
		xxx.append("Sensor 0 marksL....... ={}".format(unicode(sensorDict["sensor"][0]["left"]).replace("[","").replace("]","").replace(" ","").replace("-1","-")) )
		xxx.append("Sensor 12 marksR...... ={}".format(unicode(sensorDict["sensor"][1]["right"]).replace("[","").replace("]","").replace(" ","").replace("-1","-")) )
		xxx.append("Sensor 12 marksL...... ={}".format(unicode(sensorDict["sensor"][1]["left"]).replace("[","").replace("]","").replace(" ","").replace("-1","-")) )
		xxx.append("Sensor LineChk1....... ={}".format(sensorDict["sensor"][2]["clicked"]) )
		xxx.append("Sensor LineChk2....... ={}".format(sensorDict["sensor"][3]["clicked"]) )
		xxx.append("timeShift............. ={:.0f} (Hours, for testing only)".format(timeShift/3600) )

		statusData = ""
		for x in xxx:
			statusData += (x +"<br>")
		U.logger.log(10, u"web status update:{}".format(xxx) )

		U.writeJson(G.homeDir+"statusData."+ G.myPiNumber, xxx, sort_keys=True, indent=2 )
		U.updateWebStatus(statusData)
	except Exception, e:
		U.logger.log(40, u"Line {} has error={}".format(sys.exc_traceback.tb_lineno, e))

def removebracketsetc(data):
	out = unicode(data).replace("[","").replace("]","").replace(" ","")


# ------------------    ------------------ 
def webServerInputExtraText():
	try:
		xxx = []
		y  = ""
		y +=	'<hr align="left" width="70%" >'
		y +=	'<p><b>SUNDIAL.............:  enter sundial parameters below:</b></p>'
		y +=	'= Settings for light, direction, down/shadow, 12/24 hour<br>'
		y +=	'direction /12/24....:  <select name="mode">'
		y +=			'<option value="-1">do+not+change</option>'
		y +=			'<option value="mode:d">light straight Down</option>'
		y +=			'<option value="mode:n">use normal shadow mode</option>'
		y +=			'<option value="mode:12">use 12 hour clock</option>'
		y +=			'<option value="mode:24">use 24 hour clock</option>'
		y +=		'</select>'
		xxx.append(y)
		y  =	'led slope...........:  <select name="led">'
		y +=			'<option value="-1">do+not+change</option>'
		y +=			'<option value="led:0.15">0.15  dark </option>'
		y +=			'<option value="led:0.2">0.2</option>'
		y +=			'<option value="led:0.3">0.3</option>'
		y +=			'<option value="led:0.5">0.5</option>'
		y +=			'<option value="led:0.7">0.7</option>'
		y +=			'<option value="led:1.0">1.0 normal </option>'
		y +=			'<option value="led:1.5">1.5</option>'
		y +=			'<option value="led:2.0">2.0</option>'
		y +=			'<option value="led:3.0">3.0</option>'
		y +=			'<option value="led:5.0">5.0</option>'
		y +=			'<option value="led:7.5">7.5</option>'
		y +=			'<option value="led:10">10</option>'
		y +=			'<option value="led:15">15</option>'
		y +=			'<option value="led:20">20 bright</option>'
		y +=			'<option value="led:30">30</option>'
		y +=			'<option value="led:50">50</option>'
		y +=			'<option value="led:75">75</option>'
		y +=			'<option value="led:100">100</option>'
		y +=			'<option value="led:150">150</option>'
		y +=			'<option value="led:200">200</option>'
		y +=			'<option value="led:300">300</option>'
		y +=			'<option value="led:500">500  very bright </option>'
		y +=		'</select>'
		xxx.append(y)
		y  =		'led color...........:  <select name="LED">'
		y +=			'<option value="-1">do+not+change</option>'
		y +=			'<option value="led:220,0,0">red</option>'
		y +=			'<option value="led:30,0,0">red dark</option>'
		y +=			'<option value="led:0,220,0">green</option>'
		y +=			'<option value="led:0,30,0">green dark</option>'
		y +=			'<option value="led:0,0,220">blue</option>'
		y +=			'<option value="led:0,0,30">blue dark</option>'
		y +=			'<option value="led:0,120,120">saphire</option>'
		y +=			'<option value="led:120,120,0">yellow</option>'
		y +=			'<option value="led:150,100,0">orange</option>'
		y +=			'<option value="led:130,0,130">pink</option>'
		y +=			'<option value="led:30,30,30">grey</option>'
		y +=			'<option value="led:100,100,100">white</option>'
		y +=		'</select>'
		xxx.append(y)
		y  =	'led off..on hours...:  <select name="lightoff">'
		y +=			'<option value="-1">do+not+change</option>'
		y +=			'<option value="lightoff:0,0">on</option>'
		y +=			'<option value="lightoff:22,6">off between 22..6</option>'
		y +=			'<option value="lightoff:23,6">off between 23..6</option>'
		y +=			'<option value="lightoff:24,6">off between 24..6</option>'
		y +=			'<option value="lightoff:22,7">off between 22..7</option>'
		y +=			'<option value="lightoff:23,7">off between 23..7</option>'
		y +=			'<option value="lightoff:24,7">off between 24..7</option>'
		y +=			'<option value="lightoff:22,8">off between 22..8</option>'
		y +=			'<option value="lightoff:23,8">off between 23..8</option>'
		y +=			'<option value="lightoff:24,8">off between 24..8</option>'
		y +=		'</select>'
		xxx.append(y)
		y  =	'light sensor slope..: <select name="lightSensor">'
		y +=			'<option value="-1">do+not+change</option>'
		y +=			'<option value="lightSensor:0.016;">*64 highest</option>'
		y +=			'<option value="lightSensor:0.031;">*32 </option>'
		y +=			'<option value="lightSensor:0.063;">*16 </option>'
		y +=			'<option value="lightSensor:0.125;">"*8 </option>'
		y +=			'<option value="lightSensor:0.25;">*4 </option>'
		y +=			'<option value="lightSensor:0.50;">*2 </option>'
		y +=			'<option value="lightSensor:1.00;">normal default </option>'
		y +=			'<option value="lightSensor:2.00;">/2</option>'
		y +=			'<option value="lightSensor:4.00;">/4</option>'
		y +=			'<option value="lightSensor:8.00;">/8</option>'
		y +=			'<option value="lightSensor:16.00;">/16</option>'
		y +=			'<option value="lightSensor:32.00;">/32</option>'
		y +=			'<option value="lightSensor:64.00;">/64 lowest</option>'
		y +=		'</select>'
		xxx.append(y)
		xxx.append('= Calibrations')
		y  =	'move arm to.........: <select name="goto">'
		y +=			'<option value="-1">do+not+change</option>'
		y +=			'<option value="goNow">goto now = current time </option>'
		y +=			'<option value="led:80,80,80;gohh:0;sleep:3;gohh:3;sleep:3;gohh:6;sleep:3;gohh:9;sleep:3;gohh:11;sleep:3;goNow;">goto hour= 0 3 6 9 11 </option>'
		y +=			'<option value="led:80,80,80;gohh:0;sleep:3;gohh:3;sleep:3;gohh:12;sleep:3;gohh:18;sleep:3;gohh:23;sleep:3;goNow;">goto hour= 0 6 12 18 23 </option>'
		y +=		'</select>'
		xxx.append(y)
		y  =	'adjust arm offset...: <select name="offsetArm">'
		y +=			'<option value="0">do+not+change</option>'
		y +=			'<option value="offsetArm:-200">200 click left ~ 1/4 turn</option>'
		y +=			'<option value="offsetArm:-100">100 click left</option>'
		y +=			'<option value="offsetArm:-50">50 click left</option>'
		y +=			'<option value="offsetArm:-20">20 click left ~-38 minutes</option>'
		y +=			'<option value="offsetArm:-10">10 click left </option>'
		y +=			'<option value="offsetArm:-9">9 click left</option>'
		y +=			'<option value="offsetArm:-8">8 click left</option>'
		y +=			'<option value="offsetArm:-7">7 click left</option>'
		y +=			'<option value="offsetArm:-6">6 click left</option>'
		y +=			'<option value="offsetArm:-5">5 click left</option>'
		y +=			'<option value="offsetArm:-4">4 click left</option>'
		y +=			'<option value="offsetArm:-3">3 click left</option>'
		y +=			'<option value="offsetArm:-2">2 click left</option>'
		y +=			'<option value="offsetArm:-1">1 click left ~ -2 minutes</option>'
		y +=			'<option value="offsetArm:1">1 click right ~ +2 minutes</option>'
		y +=			'<option value="offsetArm:2">2 click right</option>'
		y +=			'<option value="offsetArm:3">3 click right</option>'
		y +=			'<option value="offsetArm:4">4 click right</option>'
		y +=			'<option value="offsetArm:5">5 click right</option>'
		y +=			'<option value="offsetArm:6">6 click right</option>'
		y +=			'<option value="offsetArm:7">7 click right</option>'
		y +=			'<option value="offsetArm:8">8 click right</option>'
		y +=			'<option value="offsetArm:9">9 click right</option>'
		y +=			'<option value="offsetArm:10">10 click right</option>'
		y +=			'<option value="offsetArm:20">20 click right ~+38 minutes</option>'
		y +=			'<option value="offsetArm:50">50 click right</option>'
		y +=			'<option value="offsetArm:100">100 click right</option>'
		y +=			'<option value="offsetArm:200">200 click right ~ 1/4 turn</option>'
		y +=		'</select>'
		xxx.append(y)

		y  =	'calibrate arm.......: <select name="calibrate">'
		y +=			'<option value="-1">do+not+change</option>'
		y +=			'<option value="calibrate:12">move arm to 12, then submit; must be 24, normal light mode</option>'
		y +=		'</select>'
		xxx.append(y)
		y  =	'set speed to (demo.): <select name="speed">'
		y +=			'<option value="-1">do+not+change</option>'
		y +=			'<option value="speed:1;gohh:0;sleep:1;gonow"   > normal speed </option>'
		y +=			'<option value="speed:60"  > 1 minute in 1 secs </option>'
		y +=			'<option value="speed:120" > 2 minutes in 1 sec ~ one move/sec</option>'
		y +=			'<option value="speed:300" > 5 minutes in 1 sec, one day in 288 secs </option>'
		y +=			'<option value="speed:600" > 10 minutes in 1 sec, one day in 144 secs </option>'
		y +=			'<option value="speed:1200"> 1 hour in 3 sec, one day in 72 secs</option>'
		y +=		'</select>'
		xxx.append(y)
		y  =		're-boot shutdown etc: <select name="re">'
		y +=			'<option value="-1">do+not+change</option>'
		y +=			'<option value="restart"  >soft restart clock </option>'
		y +=			'<option value="reboot"   >powercycle clock </option>'
		y +=			'<option value="shutdown" >shutdown clock, wait 30 secs before power off switch</option>'
		y +=			'<option value="halt"     >halt clock, wait 30 secs before power off switch</option>'
		y +=		'</select>'
		xxx.append(y)
		y  =	'enable auto update..: <select name="autoupdate">'
		y +=			'<option value="-1">do+not+change</option>'
		y +=			'<option value="E" >Enable</option>'
		y +=			'<option value="D" >Disable</option>'
		y +=		'</select>'
		xxx.append(y)
		xxx.append('= Raw commands ... experts only!')
		xxx.append('command .........: <input type = "text" name = "cmd"     value = "none" maxlength = "100" />')
		xxx.append('-restart.........: (soft restarts the clock')
		xxx.append('-reboot..........: power cycle the clock')
		xxx.append('-shutdown........: power down the clock - shutdown')
		xxx.append('-halt............: power down the clock - halt')
		xxx.append('-reset;reset.....: resets the params, needs calibration')
		xxx.append('-goNow...........: go to current time')
		xxx.append('-goHH:hh.........: go to hour:0-24')
		xxx.append('-goSteps:x.......: go x steps (0..+-800 forward/backwards')
		xxx.append('-speed:x.........: set demo speed, eg x= 1=normal, 50, 100 ..')
		xxx.append('-LED:up/down.....: increase / decrease LED intensity */ 2')
		xxx.append('-LED:x...........: set LED slope to 0-500')
		xxx.append('-LED:r,g,b.......: set LED RGB values to 0-100,0-100,0-100')
		xxx.append('-lightoff:x,y....: set LED off between hours [x,y]')
		xxx.append('-lightSensor:x...: set light sensor slope to 0.01-100')
		xxx.append('-sleep:x.........: stop any move for x secs')
		xxx.append('-mode:N/D........: set mode to Normal, or light straight Down')
		xxx.append('-mode:12/24......: sets mode to 12 hour or 24 hour mode')
		xxx.append('-getBoundaries...: find absolute cable boundaries')
		xxx.append('-offsetArm:x.....: adjust rel offset to current')
		xxx.append('-calibrate:N/hh..: move arm to pos. Now or hour, then Submit')
		xxx.append('-autoupdate:E/D..: Enable/Disable auto update download')
		xxx.append('-timeshift:hh....: change time by hh hours (for testing')
		xxx.append('lower case ok, command concatenation w. ; eg LED:50;sleep:5')
		xxx.append('then--------------==> <input type="button" onclick="submit()" value="Submit SUNDIAL Parameters"/>')
		defaults	= {"autoupdate":"-1","re":"-1","speed":"-1","mode":"-1","led":"-1","LED":"-1","calibrate":"-1","lightSensor":"-1","lightoff":"-1","offsetArm":"0","goto":"-1","cmd":"none","leftrightcalib":"-1"}

		webServerInputHTML = ""
		for x in xxx:
			webServerInputHTML += (x +"<br>")
		out = json.dumps({"webServerInputHTML":webServerInputHTML,"defaults":defaults,"outputFile":G.homeDir+"temp/sundial.cmd"})
		U.logger.log(10, u"web status update:{}".format(out) )
		U.updateWebINPUT(out)
	except Exception, e:
		U.logger.log(40, u"Line {} has error={}".format(sys.exc_traceback.tb_lineno, e))



def readCommand():
	global lastPositionCount, gpiopinNumbers, zeroPositionCount, rememberPostionInCommand, offsetOfPositionCount, totalStepsDone, amPM1224, lightShadowVsDown, secSinceMidnit0, stepsIn360
	global timeShift, intensitySlope, multiplyRGB
	global lightSensNorm, lightSensNormDefault
	global lastMove, updateDownloadEnable
	global waitForOtherItems
	retCode = False
	try:
		if not os.path.isfile(G.homeDir+"temp/sundial.cmd"): return  retCode

		f=open(G.homeDir+"temp/sundial.cmd","r")
		cmds = f.read().strip()
		f.close()
		os.system("rm  "+ G.homeDir+"temp/sundial.cmd > /dev/null 2>&1 ")

		if len(cmds) < 2: return retCode
		rememberPostionInCommand  = lastPositionCount
		cmds = cmds.lower().replace(" ","").strip(";")
	### cmds: =["go0","getBoundaries","doLR","RGB:"]
		U.logger.log(20, u"cmds: >>{}<<".format(cmds))

		restCount = 0
		cmds = cmds.split(";")
		for cmd in cmds:
			cmd =cmd.strip()


			if cmd.find("zero") > -1:
				nSteps = lastPositionCount-zeroPositionCount
				if nSteps < 0: 	direction =-1
				else:			direction = 1
				U.logger.log(10, u"go to 0: = -zeroPositionCount:{} ; nSteps:{}; totsteps:{}".format(zeroPositionCount,nSteps,totalStepsDone) )
				totalStepsDone += nSteps
				move( abs(nSteps),  direction)

			elif cmd.find("lightsensor") > -1:
				cmd = cmd.split(":")
				if len(cmd) != 2: continue
				try:    cmd = float(cmd[1])
				except:			continue
				if cmd < 0.01:	continue
				if cmd > 100: 	continue
				U.logger.log(10, u"adjusting light sensor normalization factor to to: {:.2f}; was: {:.2f}".format(cmd, lightSensNormDefault/lightSensNorm) )
				lightSensNorm = lightSensNormDefault * cmd
				saveParameters(force=True)

			elif cmd.find("lightoff") > -1:
				cmd = cmd.split(":")
				if len(cmd) != 2: continue
				try:  cmd = cmd[1].split(",")
				except:			  continue
				if len(cmd) != 2: continue
				try: 
					setLightOff(int(cmd[0]),int(cmd[1]))
				except: continue
				setColor(force=True)
				saveParameters(force=True)

			elif cmd.find("gohh:") > -1:
				cmd = cmd.split(":")
				if len(cmd) != 2: continue
				try:    cmd = float(cmd[1])
				except: continue
				hh = cmd
				if amPM1224 ==12: 	hh *=2
				hh %= 24
				nSteps = int(float(hh * maxStepsUsed) /24) - totalStepsDone
				if nSteps < 0: 	direction =-1
				else:			direction = 1
				U.logger.log(10, u"go to hour={} = steps:{} from :{}".format(hh, nSteps, totalStepsDone))
				totalStepsDone += nSteps
				move( abs(nSteps),  direction)

			elif cmd.find("gonow") > -1:
				nSteps = int(maxStepsUsed * float(secSinceMidnit )/(24*3600)) - totalStepsDone
				if nSteps < 0: 	direction =-1
				else:			direction = 1
				U.logger.log(10, u"go to now: sec={:.0f} = steps:{} ..  from :{}".format(secSinceMidnit, nSteps, totalStepsDone))
				totalStepsDone += nSteps
				move( abs(nSteps),  direction)

			elif cmd.find("steps:") >-1:
				cmd =cmd.split(":")
				if len(cmd) != 2: continue
				nSteps = int(cmd[1])
				if nSteps < 0: 	direction =-1
				else:			direction = 1
				U.logger.log(10, u"make steps: {} directionection: {}, tot steps:{}".format(nSteps, direction, totalStepsDone))
				totalStepsDone += nSteps
				move( abs(nSteps),  direction)

			elif cmd.find("offsetarm:") >-1:
				cmd =cmd.split(":")
				if len(cmd) != 2: continue
				try:    off = int(cmd[1])
				except: continue
				if abs (off) > 500: continue
				if off == 0: 		continue
				U.logger.log(10, u"setting arm offset from {}  by:{}".format(offsetOfPositionCount, off))
				if off > 0:		move(abs(off), 1)
				if off < 0:		move(abs(off),-1)
				offsetOfPositionCount += off
				getOffset()
				saveParameters(force=True)

			elif cmd.find("calibrate:") >-1:
				cmd =cmd.split(":")
				if len(cmd) != 2: continue
				if cmd[1] in ["now","n","ct"]:
					tt = int(secSinceMidnit)
				else:
					tt = int(float(cmd[1])*3600)
				waitForOtherItems = True
				rememberPos 	= lastPositionCount
				hh = int(tt/3600)
				U.logger.log(20, "setting offset .. w tt secs:{} = {:2d}:{:2d}, current ..  steps:{}; zero:{}, offset:{} .. doing LR".format(tt, hh, int(tt-hh*3600)/60, totalStepsDone, zeroPositionCount, offsetOfPositionCount))
				# this will move back to zero.. new zero will have the number of steps to 0 from correct postion
				findLeftRight()
				stepsBackToZero = rememberPos - zeroPositionCount 
				stepsShouldbe   =  int(   (float(tt * maxStepsUsed)) /(24.*3600)  )
				offsetOfPositionCount = int( stepsBackToZero -  stepsShouldbe ) 
				if 	offsetOfPositionCount   > stepsIn360: offsetOfPositionCount -= stepsIn360
				elif -offsetOfPositionCount > stepsIn360: offsetOfPositionCount += stepsIn360
				U.logger.log(20, "after left right, new zero:{}, stepsBackToZero:{}, stepsShouldbe:{}, new offset:{}".format(zeroPositionCount, stepsBackToZero, stepsShouldbe, offsetOfPositionCount))
				charString = "set off: {}".format(offsetOfPositionCount)
				displayComposeMenu0()
				time.sleep(2)
				waitForOtherItems = False
				saveParameters(force=True)
				U.restartMyself(reason="with new position offset")

			elif cmd =="getboundaries":
				U.logger.log(10, u"force boundaries of cables:")
				findBoundariesOfCabl(trigger="command")
				saveParameters(force=True)
				U.restartMyself(reason="after find boundaries", doPrint= True)

			elif cmd in ["leftrightcalib", "dolr"]:
				U.logger.log(10, u"force LR:")
				saveParameters(force=True)
				U.restartMyself(reason="web  command for L/R", doPrint= True)

			elif cmd =="restart":
				U.logger.log(20, u"web restart requested")
				doRestartMaster( button=False)

			elif cmd =="reset":
				resetCount +=1
				if restCount == 2: # must be submitted twice
					doReset(button=False)
				saveParameters(force=True)
				
			elif cmd == "shutdown":
				U.logger.log(20, u"web shutdown requested")
				doShutdownPi(button=False)
				
			elif cmd == "halt":
				U.logger.log(20, u"web halt requested")
				doHaltPi(button=False)

			elif cmd =="reboot":
				U.logger.log(20, u"web: reboot requested")
				saveParameters(force=True)
				U.doReboot(tt=0, text="web reboot  requested",   cmd="sudo killall python;sudo killall pigpiod;sudo sync;wait 2;sudo reboot now;wait 2;sudo reboot -f")
				time.sleep(20)


			elif cmd.find("led:") >-1:
				cmd =cmd.split(":")
				if len(cmd) != 2: continue
				cmd = cmd[1]
				RGB = cmd.split(",")
				if cmd == "up":
					intensitySlope *=2.
				elif cmd == "down":
					intensitySlope /=2.
				elif cmd == "off":
					lightOffBetweenHours[0] = 0
					lightOffBetweenHours[1] = 24
					U.logger.log(10, u"set LED off")
				elif cmd == "on":
					lightOffBetweenHours[0] = 0
					lightOffBetweenHours[1] = 0
					U.logger.log(10, u"set LED ON")
				elif len(RGB) == 3:
					U.logger.log(10, u"set LED RGBmultiplier to {}".format(RGB) )
					for RGBNumber in range(len(gpiopinNumbers["pin_rgbLED"])):
						multiplyRGB[RGBNumber] = float(RGB[RGBNumber])/100.
				else:
					intensitySlope = float(cmd)
					intensitySlope = min(500.,max(intensitySlope, 0.01))
					setColor(force=True)
					U.logger.log(20, u"set LED multiplier to:{}".format(intensitySlope) )
				setColor(force=True)
				saveParameters(force=True)


			elif cmd.find("sleep:") >-1:
				cmd =cmd.split(":")
				if len(cmd) != 2: continue
				sleepTime = float(cmd[1])
				U.logger.log(10, u"sleep for {}".format(sleepTime) )
				time.sleep(sleepTime)

			elif cmd.find("mode:") >-1:
				cmd =cmd.split(":")
				if len(cmd) != 2: continue
				cmd = cmd[1]
				try: 
					int(cmd)
					set1224(cmd, 		button=False)
				except:
					setSunMode(cmd, 	button=False)
				retCode = True
				saveParameters(force=True)
	
			elif cmd.find("speed:") > -1:
				cmd = cmd.split(":")
				if len(cmd) != 2: continue
				setSpeed(cmd[1], button=False)
				retCode = True
	
			elif cmd.find("autoupdate:") > -1:
				cmd = cmd.split(":")
				if len(cmd) != 2: continue
				updateDownloadEnable["sundial"] =   cmd[1].find("e") == 0
				U.writeJson(G.homeDir+"updateDownloadEnable", updateDownloadEnable, sort_keys=True, indent=2)

			elif cmd.find("timeshift:")> -1:
				cmd = cmd.split(":")
				if len(cmd) != 2: continue
				try:    hh = min(24, max(-24, float(cmd[1])))
				except: continue
				U.logger.log(10, u"time shift  hours:{:.0f}".format(hh))
				timeShift = float(hh)*3600
				setwaitParams()
				getTime()
				lastMove = 0
				saveParameters(force=True)
				testIfMove()
				retCode = True

			else:
				U.logger.log(10, u"cmds avail - no spaces\n"+
								"-restart........: (soft) restarts the clock\n"+
								"-reset..........: resets the params, req. offset calibration\n"+
								"-reboot.........: power cycle the clock\n"+
								"-shutdown.......: power down the clock - shutdown\n"+
								"-halt...........: power down the clock - halt\n"+
								"-goZero ........: go to 0 postion\n"+
								"-goNow..........: go to current time\n"+
								"-goHH:hh........: go to hour:0-24\n"+
								"-goSteps:x......: go x steps (0-800) forward/backwards\n"+
								"-speed:x........: set demo speed, eg x= 1=normal, 50, 100 ..\n"+
								"-LED:on/off.....: switches LED on/off\n"+
								"-LED:up/down....: increase / decrease LED intensity */ 1.5\n"+
								"-LED:x..........: set LED intensity to 0-100; 1 = normal\n"+
								"-LED:r,g,b......: set LED RGB values to 0-100,0-100,0-100; 100= normal\n"+
								"-lightoff:x,y...: set LED off between hours [x,y]\n"+
								"-lightSensor:x..: set light sensor sensitivity to 0.1-10; 1 = normal\n"+
								"-sleep:x........: stop any move for x secs\n"+
								"-mode:N/D.......: set mode to Normal, or light straight Down\n"+
								"-mode:12/24.....: sets mode to 12 hour or 24 hour mode\n"+
								"-getBoundaries..: find absolute boundaries, turns multiple times left then right to find cable boundaries, then goes to middle\n"+
								"-offsetArm:x....: set offset to x (-400..+400); set offset steps between magsensor =0 and time=0 Hours\n"+
								"-calibrate:N/hh.: first move arm to pos. Now or hour=hh, then Submit\n"+
								"-timeshift:hh...: change time by hh hours -- just for for testing\n"+
								"upper/lower case fine, command concatenation with ';', \n"+
								"eg:   LED:50;goHH:10;sleep:5;goNow .. sets LED to high, goes to hour = 10, waits 5 secs and goes back to current time")

		saveParameters(force=True)
	
	except Exception, e:
		U.logger.log(40, u"Line {} has error={}".format(sys.exc_traceback.tb_lineno, e))
	return retCode
		

# ########################################
# #########   sensor events ############
# ########################################

# ------------------    ------------------ 
def boundarySensorEventGPIO(pin):
	global boundaryMode, currentlyMoving, limitSensorTriggered, lastPositionCount, sensorDict
	global lastEventOfPin

	try:
		execboundarySensEvnt(pin)
	except Exception, e:
		U.logger.log(40, u"Line {} has error={}".format(sys.exc_traceback.tb_lineno, e))
	return

# ------------------    ------------------ 
def boundarySensorEventPIG(pin, level, tick):
	global boundaryMode, currentlyMoving, limitSensorTriggered, lastPositionCount, sensorDict

	try:
		execboundarySensEvnt(pin)
	except Exception, e:
		U.logger.log(40, u"Line {} has error={}".format(sys.exc_traceback.tb_lineno, e))

	return

# ------------------    ------------------ 
def execboundarySensEvnt(pin):
	global boundaryMode, currentlyMoving, limitSensorTriggered, lastPositionCount, sensorDict
	global lastEventOfPin

	try:		
		sensNumber = sensorDict["gpioToSensNumber"][pin]
		U.logger.log(10, "pin:{}, delta time:{:.2f}".format(pin, time.time() - lastEventOfPin[pin] ))
		if time.time() - lastEventOfPin[pin] < 0.5: 
			return 
		lastEventOfPin[pin] = time.time()

		getSensors()
		U.logger.log(20, "limitSensorTriggered sens#:{};  pin#{}, name:{}, timeSinceLastMove:{:.2f},   limitSensorTriggered:{}, boundaryMode:{}, sensSt2:{}, sensSt3:{}".format(sensNumber, pin, pinsToName[pin],time.time() - currentlyMoving,limitSensorTriggered,boundaryMode,sensorDict["sensor"][2]["status"],sensorDict["sensor"][3]["status"] ))

		if time.time() - currentlyMoving < 0.1:
			U.logger.log(20, "limitSensorTriggered .. currently moving, ignored, continue ")
			return 

		if boundaryMode !=0: 
			U.logger.log(20, "limitSensorTriggered .. currently in find/fix cable boundaries, ignored, continue ")
			return 

		if (sensorDict["sensor"][2]["status"] == 1 or sensNumber ==2) and limitSensorTriggered != 1:	
			limitSensorTriggered = 1
			savePositions()
			saveBoundaryMode(set=1)
			U.restartMyself(reason="entering fixmode, trigger of left boundary", doPrint= True)
		if (sensorDict["sensor"][3]["status"] == 1 or sensNumber ==3) and limitSensorTriggered != -1:
			limitSensorTriggered = -1
			savePositions()
			saveBoundaryMode(set=-1)
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
		U.logger.log(10, "pin:{}, delta time:{:.2f}".format(pin, time.time() - lastEventOfPin[pin] ))
		if time.time() - lastEventOfPin[pin] < 0.5: 
			return 
		lastEventOfPin[pin] = time.time()
		val = getPinValue(pinsToName[pin], ON=0)
		U.logger.log(10, "pin:{}  {}, val:{}, displ<enLevActive:{},  displayMenuAreaActive:{}, displayMenuSubAreaActive:{}".format(pin, pinsToName[pin], val, displayMenuLevelActive, displayMenuAreaActive, displayMenuSubAreaActive) )
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
				U.logger.log(10, "action0:>{}<<".format(cmd) )
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
				U.logger.log(10, "setting to normal display")
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
		U.logger.log(10, "(1) displayMenuLevelActive: {};  displayMenuAreaActive:{}; subArea:{}".format(displayMenuLevelActive, displayMenuAreaActive, displayMenuSubAreaActive))

		if displayMenuAreaActive < 0: return 

		if displayMenuLevelActive == 0:
			displayComposeMenu0()
			cmd = MENUSTRUCTURE[0][displayMenuAreaActive][1]
			U.logger.log(10, "action0:>>{}<<".format(cmd) )
			exec(cmd) 

		elif displayMenuLevelActive == 1:
			if displayMenuSubAreaActive < 0: return 
			displayComposeMenu0()
			cmd = MENUSTRUCTURE[1][displayMenuAreaActive][displayMenuSubAreaActive][1]
			U.logger.log(10, "action0:>>{}<<".format(cmd) )
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
		U.logger.log(10, "(1) {}".format(param))

		displayMenuLevelActive -=1

		if displayMenuLevelActive < 0:
			displayPriority = 0
			displayMenuLevelActive =-1
			displayShowStandardStatus(force=True)

		if param == "off":
				dosundialShutdown()
				U.doReboot(tt=20, text="shutdown pin pressed", cmd="sudo sync; wait 2; sudo shutdown now;wait 2;sudo shutdown -f")
		if param == "reset":
				writeBackParams({})
				U.restartMyself(reason=" reset requested")
		if param == "restart":
				dosundialShutdown()
				U.restartMyself(reason=" restart requested")
	except Exception, e:
		U.logger.log(40, u"Line {} has error={}".format(sys.exc_traceback.tb_lineno, e))
	return 


# ------------------    ------------------ 
def doSaveMenu(param):
	global charString, WiFissidString, WiFiPassString, setMenuParam

	try:
		U.logger.log(10, " into doSaveMenu %s" %param)
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
	U.logger.log(10, "into doSetWiFiParams WiFissidString: %s    WiFiPassString: %s"%(WiFissidString,WiFiPassString))
	return

# ------------------    ------------------ 
def powerOff():
	U.logger.log(10, "into powerOff")
	#U.doReboot(tt=1., text="   button pressed", cmd="shutdown -h now ")
	return 



# ------------------    ------------------ 
# ------------------    ------------------ 
# ------------------    ------------------ 
# ------------------    ------------------ 
def changeValueButtonInput(nameString, name, maxV, minV, start, maxDelta, increasDecrease):
	global charString
	try:
		time.sleep(0.1)
		U.logger.log(10, "(1) name:{} pin V:{}, val:{}, max:{}, min:{}, delta{}, maxD:{}, up/Dn:{} ".format(nameString, getPinValue("pin_Select",ON=0, doPrint=True), name, maxV, minV, start, maxDelta, increasDecrease))
		delta = start
		name = min(maxV, max(minV, name+delta) )
		time.sleep(0.1)
		charString = "val = {}".format(name)
		displayComposeMenu0()
		for ii in range(50):
			if getPinValue("pin_Select", ON=0)==0: break
			U.logger.log(10, "pin_Select still pressed val:{}".format(name) )
			delta = min(maxDelta, delta*1.5)
			name = max(minV, min(maxV, name+delta*increasDecrease) )
			setColor(force=True)
			charString = "val = {:.2f}".format(name)
			displayComposeMenu0()
			time.sleep(0.3)
		U.logger.log(10, "exit  new:{}".format(name))
		saveParameters()
	except Exception, e:
		U.logger.log(40, u"Line {} has error={}".format(sys.exc_traceback.tb_lineno, e))
	charString =""
	return name
#------------------    ------------------ 
def increaseLEDSlope():
	global intensitySlope
	intensitySlope = changeValueButtonInput("increaseLEDSlope", intensitySlope, 500., 0.1, 0.2, 5, 1)
def decreaseLEDSlope():
	global intensitySlope
	intensitySlope = changeValueButtonInput("decreaseLEDSlope", intensitySlope, 500., 0.1, 0.1, 5, -1)
# ------------------    ------------------ 
def increaseLEDmax():
	global intensityMax
	intensityMax = changeValueButtonInput("increaseLEDmax", intensityMax, 1., 0.2, 0.01, 0.1, 1)
def decreaseLEDmax():
	global intensityMax
	intensityMax = changeValueButtonInput("decreaseLEDmax", intensityMax, 1., 0.2, 0.01, 0.05, -1)
# ------------------    ------------------ 
def increaseLEDmin():
	global intensityMin, ledCutoff
	intensityMin = increaseValue("increaseLEDmin", intensityMin, 0.2, ledCutoff, 0.01, 0.05, 1)
def decreaseLEDmin():
	global intensityMin, ledCutoff
	intensityMin = changeValueButtonInput("decreaseLEDmin", intensityMin, 0.2, ledCutoff, 0.01, 0.05, -1)
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
	U.logger.log(10, "setting lights off at: {}; on at:{}".format(off,on))
	lightOffBetweenHours =[int(off),int(on)]
	setColor(force=True)
	return 



# ------------------    ------------------ 
def setAdhocWiFi(setTo):
	global webAdhoc
	global charString
	try:
		if webAdhoc == setTo: 
			U.logger.log(10, "change wifi not done, already set to {}".format(setTo))
			return
		time.sleep(2)
		if getPinValue("pin_Select", ON=0) == 0: 
			U.logger.log(10, "select not pressed for > 2secs")
			return

		webAdhoc = setTo
		if webAdhoc =="start":
			charString = "rebooting to wifiAdhoc"
			displayComposeMenu0()
			time.sleep(1)
			U.setStartAdhocWiFi()

		if webAdhoc =="stop":
			charString = "switching back to normal wifi"
			displayComposeMenu0()
			time.sleep(1)
			U.setStopAdhocWiFi()

	except Exception, e:
		U.logger.log(40, u"Line {} has error={}".format(sys.exc_traceback.tb_lineno, e))
	return 



# ------------------    ------------------ 
def doRestartWiFi():
	global charString
	try:
		time.sleep(2)	
		if getPinValue("pin_Select", ON=0) == 0: 
			U.logger.log(10, "select not pressed for > 2secs")
			return
		U.logger.log(10, "restart WiFi requested")
		charString = "executing restart"
		displayComposeMenu0()
		U.stopWiFi()
		U.startWiFi()
		time.sleep(5)
		U.restartMaster(reason="WiFi network restart")
	except Exception, e:
		U.logger.log(40, u"Line {} has error={}".format(sys.exc_traceback.tb_lineno, e))
	return 

# ------------------    ------------------ 
def doRestartETH():
	global charString
	try:
		time.sleep(2)	
		if getPinValue("pin_Select", ON=0) == 0: 
			U.logger.log(10, "select not pressed for > 2secs")
			return
		U.logger.log(20, "restart ETHERNET requested")
		charString = "executing restart"
		displayComposeMenu0()
		U.stopEth()
		U.startEth()
		time.sleep(5)
		U.restartMaster(reason="ETH network restart")
	except Exception, e:
		U.logger.log(40, u"Line {} has error={}".format(sys.exc_traceback.tb_lineno, e))
	return 



# ------------------    ------------------ 
def doShutdownPi(button=True):
	global charString
	try:
		if button:
			time.sleep(2)	
			if getPinValue("pin_Select", ON=0) == 0: 
				U.logger.log(10, "select not pressed for > 2secs")
				return
		U.logger.log(50, u"shutdown  requested")
		charString = "executing shutdown"
		displayComposeMenu0()
		time.sleep(2)
		saveParameters()
		U.doReboot(tt=1,cmd="sudo killall pythom;sudo sync;sudo sleep 9;sudo shutdown now", text="button requested")
	except Exception, e:
		U.logger.log(40, u"Line {} has error={}".format(sys.exc_traceback.tb_lineno, e))
	return 
# ------------------    ------------------ 
def doHaltPi(button=True):
	global charString
	try:
		if button:
			time.sleep(2)	
			if getPinValue("pin_Select", ON=0) == 0: 
				U.logger.log(10, "select not pressed for > 2secs")
				return
		U.logger.log(50, u"shutdown halt requested")
		charString = "executing shutdown"
		displayComposeMenu0()
		time.sleep(2)
		saveParameters()
		U.doReboot(tt=1,cmd="sudo killall pythom;sudo sync;sudo sleep 9;sudo halt", text="button requested")
	except Exception, e:
		U.logger.log(40, u"Line {} has error={}".format(sys.exc_traceback.tb_lineno, e))
	return 

# ------------------    ------------------ 
def doRebootPi(button=True):
	global charString
	try:
		if button:
			time.sleep(2)	
			if getPinValue("pin_Select", ON=0) == 0: 
				U.logger.log(10, "select not pressed for > 2secs")
				return
		U.logger.log(20, "reboot requested")
		charString = "executing reboot"
		displayComposeMenu0()
		time.sleep(2)
		saveParameters()
		U.doReboot(tt=1, text="button requested")
	except Exception, e:
		U.logger.log(40, u"Line {} has error={}".format(sys.exc_traceback.tb_lineno, e))
	return 

# ------------------    ------------------ 
def doRestartMaster(button=True):
	global charString
	try:
		if button:
			time.sleep(2)	
			if getPinValue("pin_Select", ON=0) == 0: 
				U.logger.log(10, "select not pressed for > 2secs")
				return
		U.logger.log(20, "restart requested")
		charString = "executing restart"
		displayComposeMenu0()
		time.sleep(2)
		saveParameters(force=True)
		U.restartMaster(reason="botton/web command", doPrint= True)
	except Exception, e:
		U.logger.log(40, u"Line {} has error={}".format(sys.exc_traceback.tb_lineno, e))
	return 


# ------------------    ------------------ 
def doReset(button=True):
	global charString
	try:
		if button:
			time.sleep(2)	
			if getPinValue("pin_Select", ON=0) == 0: 
				U.logger.log(10, "select not pressed for > 2secs")
				return
		U.logger.log(20, "reset requested")
		os.system("rm  "+ G.homeDir+"sundial.parameters > /dev/null 2>&1 ")
		os.system("rm  "+ G.homeDir+"temp/sundial.positions ")
		charString = "executing reset"
		displayComposeMenu0()
		time.sleep(1)
		U.restartMaster(reason="reset command", doPrint= True)
	except Exception, e:
		U.logger.log(40, u"Line {} has error={}".format(sys.exc_traceback.tb_lineno, e))
	return 

# ------------------    ------------------ 
def setOffset():
	global lastPositionCount, zeroPositionCount, offsetOfPositionCount, waitForOtherItems
	global charString
	try:
		U.logger.log(10, "(1) last zero:{}".format(zeroPositionCount))
		time.sleep(2)	
		if getPinValue("pin_Select", ON=0) == 0: 
			U.logger.log(10, "select not pressed for > 2secs")
			return
		waitForOtherItems = True
		rememberZero = zeroPositionCount
		# this will kove back to zero.. new zero will have the numebr of steps to 0 fromcorrect postion
		U.logger.log(20, "(2) doing left right ")
		findLeftRight()
		offsetOfPositionCount = rememberZero - zeroPositionCount
		U.logger.log(20, "(2) after left right, new zero:{}, offset:{}".format(zeroPositionCount, offsetOfPositionCount))
		charString = "set to: {}".format(offsetOfPositionCount)
		displayComposeMenu0()
		time.sleep(2)
		saveParameters(force=True)
		waitForOtherItems = False
		U.restartMyself(reason="with new position offset")
	except Exception, e:
		U.logger.log(40, u"Line {} has error={}".format(sys.exc_traceback.tb_lineno, e))
	return 

# ------------------    ------------------ 
def set1224(setTo, button=True):
	global amPM1224
	global charString
	try:
		if amPM1224 == int(setTo): 
			U.logger.log(10, "set 12/24 not changed, stay at{}".format(setTo))
			return 
		if button:
			time.sleep(2)	
			if getPinValue("pin_Select", ON=0) == 0: 
				U.logger.log(10, "select not pressed for > 2secs")
				return
		U.logger.log(20, "set to clock mode:{}".format(setTo))
		amPM1224 = int(setTo)
		charString = "set to: {}".format(setTo)
		displayComposeMenu0()
		setwaitParams()
		getTime()
		lastMove = 0
		saveParameters(force=True)
		testIfMove()
	except Exception, e:
		U.logger.log(40, u"Line {} has error={}".format(sys.exc_traceback.tb_lineno, e))
	return 


# ------------------    ------------------ 
def setSunMode(setTo, button=True):
	global lightShadowVsDown
	global charString
	try:
		if button:
			time.sleep(2)
			if getPinValue("pin_Select", ON=0) == 0: 
				U.logger.log(10, "select not pressed for > 2secs")
				return
		if setTo in ["normal","n"]: setTo = "normal"; direction = 1
		elif setTo in ["down","d"]: setTo = "down";   direction =-1
		else: return 
		if lightShadowVsDown == setTo:
			U.logger.log(10, "already in {} mode, no change".format(lightShadowVsDown))
			return 

		lightShadowVsDown = setTo
		charString = "set to: {}".format(lightShadowVsDown)
		displayComposeMenu0()
		U.logger.log(20, "change light mode to {}".format(lightShadowVsDown))
		move(stepsIn360/2,  direction )
		setwaitParams()
		getTime()
		lastMove = 0
		saveParameters(force=True)
		testIfMove()
	except Exception, e:
		U.logger.log(40, u"Line {} has error={}".format(sys.exc_traceback.tb_lineno, e))
	return 


#------------------    ------------------ 
def setSpeed(setTo, button=True):
	global speed, speedDemoStart
	global charString
	try:
		U.logger.log(10, "entering w setTo:{}, button:{}, curr speed:{}".format(setTo, button, speed))
		setTo = min(3600, max(1, int(setTo) ))
		if speed == setTo: return 
		if speedDemoStart < 2 and setTo < 2: return 
		if button:
			time.sleep(2)	
			if getPinValue("pin_Select", ON=0) == 0: 
				U.logger.log(10, "select not pressed for > 2 secs")
				return
		speedDemoStart = time.time()
		if setTo > 0: U.logger.log(10, "set speed to {}".format(setTo))
		charString = "set to: {}".format(setTo)
		displayComposeMenu0()
		speed = setTo
		setwaitParams()
		getTime()
		testIfRewind(force=True)
	except Exception, e:
		U.logger.log(40, u"Line {} has error={}".format(sys.exc_traceback.tb_lineno, e))
	return 


# ########################################
# #########    read /write params    #####
# ########################################

# ------------------    ------------------ 
def writeBackParams(data):
	U.logger.log(10, "data:{}".format(data))
	U.writeJson(G.homeDir+"sundial.parameters", data, sort_keys=True, indent=2)
	U.logger.log(10, "data written")
	data,raw  = U.readJson(G.homeDir+"sundial.parameters")
	U.logger.log(10, "data read back:{}".format(data))





# ------------------    ------------------ 
def savePositions():
	global lastPositionCount, zeroPositionCount, maxStepsUsed
	data = {"lastPositionCount":lastPositionCount,"zeroPositionCount":zeroPositionCount,"maxStepsUsed":maxStepsUsed}
	U.writeJson(G.homeDir+"temp/sundial.positions", data)

# ------------------    ------------------ 
def getPositions():
	global lastPositionCount, zeroPositionCount, maxStepsUsed, offsetOfPositionCount
	lastPositionCount = 0
	zeroPositionCount = 999999999
	
	data,raw  = U.readJson(G.homeDir+"temp/sundial.positions")
	if data !={}: 
		try: lastPositionCount = int(data["lastPositionCount"])
		except: pass
		try: zeroPositionCount = int(data["zeroPositionCount"])
		except: pass
		try: maxStepsUsed 	   = int( data["maxStepsUsed"])
		except: pass


# ------------------    ------------------ 
def resetBoundariesOfCable():
	global leftBoundaryOfCableCount, findAbsoluteBoundaryMode, numberOfStepsCableAllows
	leftBoundaryOfCableCount = 0
	findAbsoluteBoundaryMode = 0
	numberOfStepsCableAllows = 0
	saveParameters(force=True)

# ------------------    ------------------ 
def findBoundariesOfCabl(trigger="command"):
	global boundaryMode, rightBoundaryOfCableCount, leftBoundaryOfCableCount, limitSensorTriggered, stepsIn360, numberOfStepsCableAllows, numberOfStepsCableAllowsMax
	global lastPositionCount

	try:
		foundEnd				= False
		boundarysteps			= [1,0]
		leftRight    			= [0,0]
		dirText 				= ["right","left"]
		command					= trigger
		stopIfBS 				= {-1:[True,False], 1:[False, True]}
		direction 				=  1

		limitSensorTriggered = 0
		maxSteps = 6000		
		trySteps = 200
		backstep = 20
		triesSteps = 300
		ntries   = maxSteps/ 90
		
		U.logger.log(10,"dir:{}; first:{} then:{}, trigger:{}, boundaryMode:{}".format(direction, dirText[boundarysteps[0]], dirText[boundarysteps[1]], trigger, boundaryMode) )
		boundaryMode = trigger
		for ii in range(3):
			U.logger.log(10,"{}".format(dirText[boundarysteps[0]]))
			resetSensors()
			#wiggle forward and backwards, just in case
			U.logger.log(10,"{}, doing steps: {}, dir:{}, stop if BS:{}".format(dirText[boundarysteps[0]], trySteps, direction,stopIfBS[direction]))
			stepsTaken0, sensFired = move( trySteps,   direction, fast=False, updateSequence=False, stopIfMagSensor=[True,True], stopIfBoundarySensor=stopIfBS[direction])
			resetSensors()
			if abs(stepsTaken0) == trySteps:
				time.sleep(0.1)
				U.logger.log(10,"moving {} did  not work, moving back {}; try again steps/200:{}".format(dirText[boundarysteps[0]], backstep, stepsTaken0))
				move( backstep,   -direction, fast=False, updateSequence=False, stopIfMagSensor=[True,True], stopIfBoundarySensor=stopIfBS[-direction])
				time.sleep(0.1)
				continue
			resetSensors()

			U.logger.log(10,"{}, doing steps: {}, dir:{}, stop if BS:{}".format(dirText[boundarysteps[0]],maxSteps,direction,stopIfBS[direction]))

			stepsTaken1 = 0
			foundEnd = False
			for ii in range(ntries):
				temp, sensFired = move( triesSteps,  direction, fast=True, force=30, updateSequence=False, stopIfMagSensor=[True,True], stopIfBoundarySensor=stopIfBS[direction])
				if abs(temp) == triesSteps:
					break
				stepsTaken1 += abs(temp)
				if sensFired in [2, 3]:
					foundEnd = True
					break
			if not foundEnd: continue
			resetSensors()
			if trigger != "command": 
				nsteps =  int(   2.7 * stepsIn360  )
				U.logger.log(10,"{}, doing steps to middle : {}, dir:{}, stop if BS:{}".format(dirText[boundarysteps[1]], nsteps,-direction,stopIfBS[-direction]))
				move( nsteps, -direction, fast=True, stopIfBoundarySensor=stopIfBS[-direction])
				resetSensors()
				saveBoundaryMode(set=0, tt=time.time())
				U.logger.log(10,"finished")
				return 

			leftRight[0] = lastPositionCount
			time.sleep(0.1)
			U.logger.log(20,"{}, first found at pos:{} steps to boundary:{}".format(dirText[boundarysteps[0]],lastPositionCount, stepsTaken1))

			limitSensorTriggered = 0
			U.logger.log(20,"first found:{};   finding boundaries, now {}".format(leftRight[0], dirText[boundarysteps[1]]))
			U.logger.log(20,"{}, doing steps: {}, dir:{}, stop if BS:{}".format(dirText[boundarysteps[1]], backstep, direction,stopIfBS[direction]))
			stepsTaken0, sensFired = move( trySteps,   -direction, fast=False, updateSequence=False, stopIfMagSensor=[True,True], stopIfBoundarySensor=stopIfBS[-direction])
			resetSensors()
			if abs(stepsTaken0) == trySteps:
				time.sleep(0.1)
				U.logger.log(20,"moving {} did  not work, moving back {}; try again steps/200:{}".format(dirText[boundarysteps[0]], backstep, stepsTaken0))
				move( backstep,   direction, fast=False, updateSequence=False, stopIfMagSensor=[True,True], stopIfBoundarySensor=stopIfBS[direction])
				time.sleep(0.1)
				resetSensors()
				continue

			U.logger.log(20,"{}, doing steps: {}, dir:{}, stop if BS:{}".format(dirText[boundarysteps[1]], maxSteps, -direction, stopIfBS[-direction]))
			stepsTaken1 = 0
			foundEnd= False
			for ii in range(ntries):
				temp, sensFired = move( triesSteps,  -direction, fast=True, force=30, updateSequence=False, stopIfMagSensor=[True,True], stopIfBoundarySensor=stopIfBS[-direction])
				if abs(temp) == triesSteps:
					break
				stepsTaken1 += abs(temp)
				if sensFired in [2, 3]: 
					foundEnd = True
					break
			if not foundEnd: continue
			resetSensors()
			leftRight[1] = lastPositionCount
			U.logger.log(20,"{}, found at:{}, steps taken:{}".format(dirText[boundarysteps[1]], lastPositionCount, stepsTaken1))

			rightBoundaryOfCableCount = leftRight[0]
			leftBoundaryOfCableCount  = leftRight[1]

			limitSensorTriggered = 0
			temp = abs(rightBoundaryOfCableCount - leftBoundaryOfCableCount)
			if temp > numberOfStepsCableAllowsMax or  temp < stepsIn360 *2: 
				U.logger.log(20," not finished, left:{};  right:{};  delta:{} to small, try again".format(leftBoundaryOfCableCount, rightBoundaryOfCableCount, temp))
				continue
			numberOfStepsCableAllows = temp 
			break
		time.sleep(0.1)
		if not foundEnd:
			U.logger.log(20,"NOT finished, try to restart")
			boundaryMode = trigger
			resetBoundariesOfCable()
			U.restartMyself(reason="boundary not found, resetting params")
			time.sleep(5)

		U.logger.log(20,"finished, left:{};  right:{};  delta:{}".format(leftBoundaryOfCableCount, rightBoundaryOfCableCount, numberOfStepsCableAllows))
		saveParameters()
		nsteps =  int( min(numberOfStepsCableAllowsMax * 0.6, max(  3 * stepsIn360,  numberOfStepsCableAllows- 2 * stepsIn360 ) ) )
		U.logger.log(20,"moving right to ~ middle between left and right boundaries: {} steps, current step count:{}".format(nsteps, lastPositionCount))
		limitSensorTriggered = 0
		resetSensors()
		move( nsteps, 1, stopIfBoundarySensor=[False,True])
		resetSensors()
		limitSensorTriggered = 0
		boundaryMode = 0
		saveBoundaryMode(set=0, tt=time.time())
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
	global offsetOfPositionCount 
	global rightBoundaryOfCableCount, leftBoundaryOfCableCount, numberOfStepsCableAllows
	global lightShadowVsDown, boundaryMode, lastBoundaryMode
	global lightOffBetweenHours
	global lastsaveParameters, multiplyRGB
	global sundialParameters

	if time.time() - lastsaveParameters < 100 and not force: return 
	lastsaveParameters = time.time()
	try:
		anyChange = 0
		anyChange += upINP("lightOffBetweenHours",		lightOffBetweenHours			) 
		anyChange += upINP("amPM1224",					amPM1224			) 
		anyChange += upINP("intensitySlope",			intensitySlope	)
		anyChange += upINP("intensityMax",				intensityMax	) 
		anyChange += upINP("intensityMin",				intensityMin	)
		anyChange += upINP("lightSensMin",				lightSensMin	) 
		anyChange += upINP("lightSensMax",				lightSensMax	) 
		anyChange += upINP("lightSensNorm",				lightSensNorm	) 
		anyChange += upINP("multiplyRGB",				multiplyRGB	,index=3) 
		anyChange += upINP("offsetOfPositionCount",		offsetOfPositionCount	) 
		anyChange += upINP("rightBoundaryOfCableCount",	rightBoundaryOfCableCount	) 
		anyChange += upINP("leftBoundaryOfCableCount",	leftBoundaryOfCableCount	) 
		anyChange += upINP("numberOfStepsCableAllows",	numberOfStepsCableAllows	) 
		anyChange += upINP("lightShadowVsDown",			lightShadowVsDown		) 
		anyChange += upINP("boundaryMode",				boundaryMode		) 
		anyChange += upINP("lastBoundaryMode",			lastBoundaryMode		) 
		if anyChange >0 or force:
			writeBackParams(sundialParameters)
			U.logger.log(20, u"anyChange:{} writing params:{}".format(anyChange, sundialParameters))
	except Exception, e:
		U.logger.log(40, u"Line {} has error={}".format(sys.exc_traceback.tb_lineno, e))
	return

# ------------------    ------------------ 
def saveBoundaryMode(set=999, tt=-1):
	global lastBoundaryMode, boundaryMode
	if set != 999: 
		boundaryMode = set
	if tt !=-1:
		lastBoundaryMode = tt
	saveParameters(force=True)

# ------------------    ------------------ 
def	upINP(parm, value,index=-1):
	global sundialParameters
	retcode = 0
	if index >= 0:
		if parm not in sundialParameters:
			sundialParameters
			sundialParameters[parm]=[]
			for ii in range(index):
				sundialParameters[parm].append(value[ii])
			retcode = 1
		for ii in range(index):
			if sundialParameters[parm][ii] != value[ii]:
				sundialParameters[parm][ii] = value[ii]
				retcode = 1
	else:
		if parm not in sundialParameters or sundialParameters[parm] != value:
			sundialParameters[parm] = value
			retcode = 1
	return retcode

# ------------------    ------------------ 
def getParameters():
	global amPM1224, intensitySlope, intensityMax, intensityMin, lightSensMin, lightSensMax , lightSensNorm, lightSensNormDefault, ledCutoff
	global offsetOfPositionCount 
	global rightBoundaryOfCableCount, leftBoundaryOfCableCount, numberOfStepsCableAllows, numberOfStepsCableAllowsMax
	global lightOffBetweenHours
	global lightShadowVsDown, boundaryMode, lastBoundaryMode
	global sundialParameters, multiplyRGB

	try:
		data,raw  = U.readJson(G.homeDir+"sundial.parameters")
		U.logger.log(10, u" data:{}".format(data))

		sundialList={"lightOffBetweenHours":[0,0],"amPM1224":24,"intensitySlope":1.,"intensityMax":1.,"intensityMin":ledCutoff,"multiplyRGB":[1,1,1],
					"lightSensMin": 0.001,"lightSensMax":1.,"lightSensNorm":lightSensNormDefault,
					"offsetOfPositionCount":0,"rightBoundaryOfCableCount":0,"leftBoundaryOfCableCount":0,"numberOfStepsCableAllows":0,
					"lightShadowVsDown":"normal shadow","lastBoundaryMode":0,"boundaryMode":0}

		sundialParameters = {}		
		for item in sundialList:

			if item == "lightOffBetweenHours":
					try: lightOffBetweenHours		= data["lightOffBetweenHours"]
					except: lightOffBetweenHours	= sundialList[item]
					sundialParameters[item]			= lightOffBetweenHours

			elif item == "amPM1224":
					try: amPM1224 					= data["amPM1224"]
					except: amPM1224				= sundialList[item]
					sundialParameters[item]			= amPM1224

			elif item == "intensitySlope":
					try: intensitySlope 			= data["intensitySlope"]
					except: intensitySlope			= sundialList[item]
					sundialParameters[item]			= intensitySlope

			elif item == "intensityMax":
					try: intensityMax				= min(data["intensityMax"],1.0)
					except: intensityMax			= sundialList[item]
					sundialParameters[item]			= intensityMax

			elif item == "intensityMin":
					try: intensityMin				= max(data["intensityMin"], ledCutoff)
					except:	intensityMin			= sundialList[item] ## range of 400
					sundialParameters[item]			= intensityMin

			elif item == "multiplyRGB":
					try: multiplyRGB				= data["multiplyRGB"]
					except:	multiplyRGB				= sundialList[item]
					sundialParameters[item]			= multiplyRGB

			elif item == "lightSensMin":
					try: lightSensMin				= max(data["lightSensMin"],0.001)
					except: lightSensMin			= sundialList[item]
					sundialParameters[item]			= lightSensMin

			elif item == "lightSensMax":
					try: lightSensMax				= min(data["lightSensMax"], 1.0 )
					except: lightSensMax			= sundialList[item]
					sundialParameters[item]			= lightSensMax

			elif item == "lightSensNorm":
					try: lightSensNorm				= data["lightSensNorm"]
					except: lightSensNorm			= sundialList[item]
					sundialParameters[item]			= lightSensNorm

			elif item == "offsetOfPositionCount":
					try: offsetOfPositionCount		= data["offsetOfPositionCount"]
					except: offsetOfPositionCount	= sundialList[item]
					sundialParameters[item]			= offsetOfPositionCount

			elif item == "rightBoundaryOfCableCount":
					try: rightBoundaryOfCableCount	= data["rightBoundaryOfCableCount"]
					except: rightBoundaryOfCableCount= sundialList[item]
					sundialParameters[item]			= rightBoundaryOfCableCount

			elif item == "leftBoundaryOfCableCount":
					try: leftBoundaryOfCableCount	= data["leftBoundaryOfCableCount"]
					except: leftBoundaryOfCableCount= sundialList[item]
					sundialParameters[item]			= leftBoundaryOfCableCount

			elif item == "numberOfStepsCableAllows":
					try: numberOfStepsCableAllows	= min(data["numberOfStepsCableAllows"], numberOfStepsCableAllowsMax)
					except: numberOfStepsCableAllows= sundialList[item]
					sundialParameters[item]			= numberOfStepsCableAllows

			elif item == "lightShadowVsDown":
					try: lightShadowVsDown			= data["lightShadowVsDown"]
					except: lightShadowVsDown		= sundialList[item]
					sundialParameters[item]			= lightShadowVsDown

			elif item == "lastBoundaryMode":
					try: lastBoundaryMode			= data["lastBoundaryMode"]
					except: lastBoundaryMode		= sundialList[item]
					sundialParameters[item]			= lastBoundaryMode

			elif item == "boundaryMode":
					try: boundaryMode				= data["boundaryMode"]
					except: boundaryMode			= sundialList[item]
					sundialParameters[item]			= boundaryMode

		U.logger.log(10, u" boundaryMode:{}".format(boundaryMode))
	
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
	global lastCl
	global oldRaw, lastRead
	global doReadParameters
	global clockDictLast, clockDict
	global buttonDict, sensorDict
	global pinsToName, anyInputChange
	global startWebServerSTATUS, startWebServerINPUT
	global updateDownloadEnable

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
		 


		if "debugRPI"						in inp:	 G.debug=		  				int(inp["debugRPI"])
		if "useRTC"							in inp:	 useRTC=					       (inp["useRTC"])
		if "output"							in inp:	 output=			 			   (inp["output"])
		if u"startWebServerSTATUS" 			in inp:	 startWebServerSTATUS= 			  int(inp["startWebServerSTATUS"])
		if u"startWebServerINPUT" 			in inp:	 startWebServerINPUT= 			  int(inp["startWebServerINPUT"])

		#### G.debug = 2 
		if G.program not in output:
			U.logger.log(30, G.program+ " is not in parameters = not enabled, stopping "+ G.program+".py" )
			exit()
		
		for devId in output["sundial"]:
			U.logger.log(10, "output{}".format(output["sundial"][devId]) )
			current, temp = U.readJson(G.homeDir+"updateDownloadEnable")
			if "sundial" in current:
				updateDownloadEnable["sundial"] = current["sundial"]
			else:
				updateDownloadEnable["sundial"] = output["sundial"][devId][0]["updateDownloadEnable"] == "1"

		return -changed 
	except Exception, e:
		U.logger.log(40, u"Line {} has error={}".format(sys.exc_traceback.tb_lineno, e))
		time.sleep(10)
		return 3


# ########################################
# #########    basic setup funtions  #####
# ########################################
# ------------------    ------------------ 

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
				U.logger.log(10, "motorType = "+unicode(motorType))
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
	global gpiopinNumbers, motorType, sensorDict, buttonDict, PIGPIO, pwmRange, pwmFreq, lastEventOfPin, ledCutoff
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


		U.logger.log(20, "{}".format(pinsToName))
		U.logger.log(20, "{}".format(gpiopinNumbers))
		U.logger.log(20, "{}".format(sensorDict))
		U.logger.log(20, "{}".format(buttonDict))

		if not U.pgmStillRunning("pigpiod"): 	
			U.logger.log(10, "starting pigpiod")
			os.system("sudo pigpiod -s 2 &")
			time.sleep(0.5)
			if not U.pgmStillRunning("pigpiod"): 	
				U.logger.log(30, "restarting myself as pigpiod not running, need to wait for timeout to release port 8888")
				time.sleep(20)
				dosundialShutdown()
				U.restartMyself(reason="pigpiod not running")
				exit(0)

		PIGPIO = pigpio.pi()
		pwmRange  = 40000
		pwmFreq   = 40
		ledCutoff = 20./float(pwmRange)
		# this gives a range   0.0005


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
def defineGPIOout(pin, pwm = 0):
	global PIGPIO, pwmRange, colPWM, pwmFreq
	#print "defineGPIOout", pin, pwm, freq
	try:
		PIGPIO.set_mode(pin, pigpio.OUTPUT)
		if pwm !=0:
			PIGPIO.set_PWM_frequency(pin, pwmFreq)
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
	global PIGPIO, pwmRange, pwmFreq
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
			U.logger.log(10, u" pin:{} #:{} ON:{},  value:{}".format(pinName, pin, ON, ret) )
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
			U.logger.log(10, u" pin:{} #:{} ON:{} sens:{}".format(pinName, pin, ON, ret) )
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
	global boundaryMode, lastBoundaryMode
	global currentlyMoving
	global lastPositionCount, rightBoundaryOfCableCount, leftBoundaryOfCableCount

	if doPrint: U.logger.log(10, "into move") 
	actualStepsTakeninMove= 0
	try:
		stayOn = max(minStayOn,stayOn)
		lStep = lastStep
		if doPrint: U.logger.log(10, "steps:{} direction:{}, stayOn:{:.3f}, force:{}, stopIfMagSensor:{}, updateSequence:{}, boundaryMode:{}".format(steps,  direction, stayOn, force, stopIfMagSensor, updateSequence, boundaryMode) )
		steps = abs(int(steps))

		getSensors()
		last1 = sensorDict["sensor"][1]["status"]
		last0 = sensorDict["sensor"][0]["status"]
		for i in range(steps):
			currentlyMoving = time.time()

			if updateSequence: 
				 determineSequenceNo(totalStepsDone+actualStepsTakeninMove)

				
			if boundaryMode == 0:
				if sensorDict["sensor"][2]["status"] == 1:	
					saveBoundaryMode(set=1)
					savePositions()
					U.logger.log(10, "fixing (1) starting due to: sw  switch sens: {};   switch sensor:{}".format(sensorDict["sensor"][2]["status"], sensorDict["sensor"][3]["status"]))
					U.restartMyself(reason="need to fix boundaries #1 left:{}, right{}".format(sensorDict["sensor"][2]["status"], sensorDict["sensor"][3]["status"]), delay=5)
				if sensorDict["sensor"][3]["status"] == 1:	
					saveBoundaryMode(set=-1)
					savePositions()
					U.logger.log(10, "fixing (2) starting due to: cap switch sens: {};   switch sensor:{}".format(sensorDict["sensor"][2]["status"], sensorDict["sensor"][3]["status"]))
					U.restartMyself(reason="need to fix boundaries #1 left:{}, right{}".format(sensorDict["sensor"][2]["status"], sensorDict["sensor"][3]["status"]), delay=5)

			if sensorDict["sensor"][2]["status"] == 1 and stopIfBoundarySensor[0]:
				U.logger.log(10, "return sens2=T, stopifB0=T actualStepsTakeninMove:{:3d}, requested:{:3d}; dir:{}, stopfMag:{}, stopIfBS:{}".format(actualStepsTakeninMove, steps, direction, stopIfMagSensor, stopIfBoundarySensor) )
				savePositions()
				return actualStepsTakeninMove, 2

			if sensorDict["sensor"][3]["status"] == 1 and stopIfBoundarySensor[1]:
				U.logger.log(10, "return sens3=T, stopifB1=T actualStepsTakeninMove:{:3d}, requested:{:3d}; dir:{}, stopfMag:{}, stopIfBS:{}".format(actualStepsTakeninMove, steps, direction, stopIfMagSensor, stopIfBoundarySensor) )
				savePositions()
				return actualStepsTakeninMove, 3

			if sensorDict["sensor"][0]["status"] == 1 and stopIfMagSensor[0] and i >= force:
				U.logger.log(10, "return sens0=T, stopifM0=T actualStepsTakeninMove:{:3d}, requested:{:3d}; dir:{}, stopfMag:{}, stopIfBS:{}".format(actualStepsTakeninMove, steps, direction, stopIfMagSensor, stopIfBoundarySensor) )
				savePositions()
				return actualStepsTakeninMove, 0

			if sensorDict["sensor"][1]["status"] == 1 and stopIfMagSensor[1] and i >= force:
				U.logger.log(10, "return sens1=T, stopifM1=T actualStepsTakeninMove:{:3d}, requested:{:3d}; dir:{}, stopfMag:{}, stopIfBS:{}".format(actualStepsTakeninMove, steps, direction, stopIfMagSensor, stopIfBoundarySensor) )
				savePositions()
				return actualStepsTakeninMove, 1


			if not updateSequence or ( currentSequenceNo < 8 and sensorDict["sensor"][0] == 1 ):
				if i >= force: 
					if last0 != sensorDict["sensor"][0]["status"] and sensorDict["sensor"][0]["status"] == 1 and stopIfMagSensor[0]: 
						U.logger.log(10, "move  return due to: last0!=sens0, mag0=T, direction{}, boundaryMode:{}".format(direction, boundaryMode)+" cap switch sens: "+unicode(sensorDict["sensor"][2]["status"])+";   switch sensor:"+unicode(sensorDict["sensor"][3]["status"]))
						return actualStepsTakeninMove, 0
					if last1 != sensorDict["sensor"][1]["status"] and sensorDict["sensor"][1]["status"] == 1 and stopIfMagSensor[1]: 
						U.logger.log(10, "move  return due to: last1!=sens1, mag1=T, direction:{}, boundaryMode:{}".format(direction, boundaryMode)+" cap switch sens: "+unicode(sensorDict["sensor"][2]["status"])+";   switch sensor:"+unicode(sensorDict["sensor"][3]["status"]))
						return actualStepsTakeninMove, 1

			if currentSequenceNo == 8 and sensorDict["sensor"][0] == 1:
				if i >= force: 
					if last0 != sensorDict["sensor"][0]["status"] and sensorDict["sensor"][0]["status"] == 1 and stopIfMagSensor[0]: 
						savePositions()
						return actualStepsTakeninMove, 0
					if last1 != sensorDict["sensor"][1]["status"] and sensorDict["sensor"][1]["status"] == 1 and stopIfMagSensor[1]: 
						savePositions()
						return actualStepsTakeninMove, 1

			last1 = sensorDict["sensor"][1]["status"]
			last0 = sensorDict["sensor"][0]["status"]
			resetSensors()

			actualStepsTakeninMove += direction
			lStep += direction
			lastPositionCount += direction

			if   lStep >= len(SeqCoils):	lStep = 1
			elif lStep <  1: 				lStep = len(SeqCoils)-1

			lastStep = lStep
			if makeStep(lStep, only2=fast):
				time.sleep(stayOn)
			if doPrint: U.logger.log(10, "moved, now at:{}".format(lastPositionCount) )
			getSensors()
		
		savePositions()
		resetSensors()

	###			U.logger.log(40, " not sleeping")


	except Exception, e:
		U.logger.log(40, u"Line {} has error={}".format(sys.exc_traceback.tb_lineno, e))

	#if speed < 100 or stayOn > 0.5: setOffset()
	return actualStepsTakeninMove, -1

# ------------------    ------------------ 
def testIfMove(force = False ):
	global maxStepsUsed, startSteps
	global speed
	global t0
	global printON
	global totalStepsDone
	global hour, minute, second
	global secSinceMidnit	
	global PIGPIO
	global waitBetweenSteps
	global currentSequenceNo, inbetweenSequences
	global lastMove

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

			if totalStepsDone%5 == 0: U.logger.log(20, "secSinMidn:{:.2f}; secseff:{:.2f}; {:02d}:{:02d}:{:02d}; dt:{:.5f} ; nstep:{}; tSteps:{}; curtSeqN:{};  inbSeq:{};  boundaryMode:{}; s2:{}, s3:{}; dir:{}".format(secSinceMidnit, secs, hour,minute,second, (time.time()-t0), nextStep, totalStepsDone, currentSequenceNo, inbetweenSequences, boundaryMode, sensorDict["sensor"][2]["status"],sensorDict["sensor"][3]["status"],  direction))

			if nextStep != 0: 
				if speed > 10 or nextStep >5: stayOn =0.01
				else:		                  stayOn =0.01
				if lasttotalStepsDone < 10: force = 10 
				else:					force = 0
				#print "dir, nextStep", dir, nextStep
				if currentSequenceNo < 7: force = int(maxStepsUsed*0.9)
				move(int(abs(nextStep)), direction, stayOn=stayOn, force=force, updateSequence=True)
				lastMove = time.time()
				setColor()

			totalStepsDone += nextStep

			#saveTime(secSinceMidnit)
			t0=time.time()
	except Exception, e:
		U.logger.log(40, u"Line {} has error={}".format(sys.exc_traceback.tb_lineno, e))

	return 


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
def testIfRewind(force= False):
	global maxStepsUsed, startSteps
	global t0
	global printON
	global totalStepsDone
	global hour, minute, second
	global secSinceMidnit	
	global useoffsetOfPositionCount
	global lastPositionCount, zeroPositionCount
	global speed


	try:


		if force:
			move (totalStepsDone,-1,  force=30, stopIfMagSensor=[False,False] )
			totalStepsDone = 0

		elif  totalStepsDone >= maxStepsUsed or (speed > 1. and totalStepsDone >= maxStepsUsed-10): 

			if useoffsetOfPositionCount >=0:		direction = +1
			else:									direction = -1

			if useoffsetOfPositionCount !=0:
				steps0, sensFiredmove = move(useoffsetOfPositionCount, -direction,  force=30, stopIfMagSensor=[False,False] )
				U.logger.log(10, "should be at full position = offset steps:{}".format(steps0))
				time.sleep(5)

			U.logger.log(10, "rewind..   secSinceMidnit:{:.2f}; {:02d}:{:02d}:{:02d}; dt:{:.5f}; totSteps:{}".format(secSinceMidnit, hour,minute,second, (time.time()-t0), totalStepsDone))
			steps1, sensFiredmove = move (maxStepsUsed,-1,  force=30, stopIfMagSensor=[False,True] )
			steps2, sensFiredmove = move (maxStepsUsed,-1,  force=30, stopIfMagSensor=[True,False] )
			move (2,-1,  force=30, stopIfMagSensor=[False,False] )
			#steps3, sensFiredmove = move (maxStepsUsed,-1,  force=30, stopIfMagSensor=[True,False] )
			U.logger.log(10, "should be at offset position steps: {},{}, total:{}".format(steps1, steps2+2,  (steps1 + steps2 +2) ))
			time.sleep(5)
			if useoffsetOfPositionCount !=0:
				steps4, sensFiredmove = move (useoffsetOfPositionCount+2, direction,   force=30, stopIfMagSensor=[False,False] )
				U.logger.log(10, "should be at hh=0 position  steps:{}".format(steps4))
				time.sleep(5)
			speed = 1
			setwaitParams()
			getTime()
		
			totalStepsDone = 0
			t0=time.time()
		totalStepsDone = max(0, min(totalStepsDone, maxStepsUsed) )
	except Exception, e:
		U.logger.log(40, u"Line {} has error={}".format(sys.exc_traceback.tb_lineno, e))

	return 




# ------------------    ------------------ 
def findLeftRight():
	global maxStepsUsed,stepsIn360
	global printON
	global waitBetweenSteps, secondsTotalInDay 
	global amPM1224
	global whereIs12
	global currentSequenceNo
	global limitSensorTriggered
	global lastPositionCount, zeroPositionCount
	
	try:
		limitSensorTriggered = 0
		time.sleep(0.1)

		stayOn = 0.01

		maxSteps = int(stepsIn360+2)
		updatewebserverStatus(status="finding left right boundaries")

		# check if we start at 0 left or right
		getSensors()
		#  sensorDict["pin_sensor0"]["status"]

		U.logger.log(10, "starting left right ")
		displayDrawLines(["starting left right","determining limits", datetime.datetime.now().strftime("%a, %Y-%m-%d %H:%M")])

		steps 		= 0 
		stepsTotal	= 0
		oneEights = int(stepsIn360 /8.)+10
		pp = False
		if pp: printLrLog("0000 === ", steps, 0, short=True)
		while True:
			# THIS IS THE EASIEST SIMPLE CASE:
			if sensorDict["sensor"][1]["status"] == 1: # 12 o-clock sensor on at start = we are in the middle, exit basic find
				steps, sensFired = move( oneEights*6  , -1, force=30, stopIfMagSensor=[True,False] )
				stepsTotal +=steps
				if pp: printLrLog("0100 === ", steps, -1, extra=" fist step done", short=True)
				break

			# THIS IS THE MOST DIFFICULT, SOMEWHERE CLOSE TO 0 OR 24:
			elif sensorDict["sensor"][0]["status"] == 1:
				#test if still on when moving right
				steps, sensFired = move( 10  , 1, force=11, stopIfMagSensor=[False,False] )
				stepsTotal +=steps
				if pp: printLrLog("0200 === ", steps, -1, short=True)

				if sensorDict["sensor"][0]["status"] == 0:
					steps, sensFired = move( oneEights*8  , 1, force=6, stopIfMagSensor=[True,True] )
					stepsTotal +=steps
					if pp: printLrLog("0201 === ", steps, 1, short=True)

					if sensorDict["sensor"][0]["status"] == 1:
						steps, sensFired = move( oneEights*10, -1, force=6, stopIfMagSensor=[False,True] )
						stepsTotal +=steps
					if pp: printLrLog("0202 === ", steps, -1, short=True)


					if sensorDict["sensor"][1]["status"] == 1:
						steps, sensFired = move( oneEights*8  ,-1, force=6, stopIfMagSensor=[True,False] )
						stepsTotal +=steps
					if pp: printLrLog("0203 === ", steps, -1, short=True)
					break


				if sensorDict["sensor"][0]["status"] == 1:
					steps, sensFired = move( oneEights*8  , -1, force=6, stopIfMagSensor=[False,True] )
					stepsTotal +=steps
				if pp: printLrLog("0210 === ", steps, -1, short=True)


				if sensorDict["sensor"][1]["status"] == 0:
					steps, sensFired = move( oneEights*6 , 1, force=30, stopIfMagSensor=[True,True] )
					stepsTotal +=steps
					if pp: printLrLog(-3, "0211 === ", steps, -1, short=True)
					if sensorDict["sensor"][1]["status"] == 1:
						steps, sensFired = move( oneEights*6 , -1, force=30, stopIfMagSensor=[True,False] )
						if pp: printLrLog("0212 === ", steps, -1, short=True)
						break

					if sensorDict["sensor"][0]["status"] == 1:
						steps, sensFired = move( oneEights*6 , -1, force=30, stopIfMagSensor=[False,True] )
						stepsTotal +=steps
						if pp: printLrLog("0230 === ", steps, -1, short=True)
						steps, sensFired = move( oneEights*6 , -1, force=30, stopIfMagSensor=[True,False] )
						break

				if sensorDict["sensor"][1]["status"] == 1:
					# found a midle, just continue to 0
					steps, sensFired = move( oneEights*6  , -1, force=30, stopIfMagSensor=[True,False] )
					stepsTotal +=steps
					if pp: printLrLog("0300 === ", steps, -1)
					break
				if pp: U.logger.log(50, "0400 === no if condition found")


			else:
			
				steps, sensFired = move( 5  , 1, force=6, stopIfMagSensor=[True,False] )
				stepsTotal +=steps
				if pp: printLrLog("1000 === ", steps, -1, short=True)
				if sensorDict["sensor"][1]["status"] == 0 and sensorDict["sensor"][1]["status"] == 0:
					steps, sensFired = move( oneEights*5  , 1, force=2, stopIfMagSensor=[True,True] )
					stepsTotal +=steps
					if pp: printLrLog("1100 === ", steps, 1, short=True)

				if sensorDict["sensor"][1]["status"] == 1:
					steps, sensFired = move( oneEights*6 , -1, force=30, stopIfMagSensor=[True,False] )
					stepsTotal +=steps
					if pp: printLrLog("1200 === ", steps, -1, short=True)

				if sensorDict["sensor"][0]["status"] == 1:
					steps, sensFired = move( oneEights*3 , -1, force=5, stopIfMagSensor=[True,True] )
					stepsTotal +=steps
					if pp: printLrLog("1300 === ", steps, -1, short=True)
					if sensorDict["sensor"][0]["status"] == 1:
						steps, sensFired = move( oneEights*8 ,  -1, force=30, stopIfMagSensor=[False,True] )
						stepsTotal +=steps
						if pp: printLrLog("1310 === ", steps, -1, short=True)
						steps, sensFired = move( oneEights*8 , -1, force=30, stopIfMagSensor=[True,False] )
						stepsTotal +=steps
						if pp: printLrLog("1311 === ", steps, -1, short=True)
						break
						# done

					elif sensorDict["sensor"][1]["status"] == 1:
						steps, sensFired = move( oneEights*8, -1, force=10, stopIfMagSensor=[True,False] )
						stepsTotal +=steps
						if pp: printLrLog("1321 === ", steps, -1)
						break
						# done

					elif sensorDict["sensor"][0]["status"] == 0:
						steps, sensFired = move( oneEights*8 , -1, force=30, stopIfMagSensor=[True,True] )
						stepsTotal +=steps
						if pp: printLrLog("1340 === ", steps, -1, short=True)
						if sensorDict["sensor"][1]["status"] == 1:
							steps, sensFired = move(stayOn, oneEights*8 , -1, force=10, stopIfMagSensor=[False,True] )
							break

						steps, sensFired = move( oneEights*5 , -1, force=30, stopIfMagSensor=[True,False] )
						stepsTotal +=steps
						if pp: printLrLog("11341 === ", steps, -1, short=True)
						break
			U.logger.log(40, "============ no sensors found , try with fix boundaies to move the pole.")
			displayDrawLines(["pole stuck?", " doing recovery", datetime.datetime.now().strftime("%a, %Y-%m-%d %H:%M")])
			#time.sleep(1)
			findBoundariesOfCabl(trigger="command")
			U.restartMyself(reason="no sensor found")
			return 

		if getLightSensorValue(force=True): setColor(force=True)



		displayDrawLines(["confirming", " left-right limits", datetime.datetime.now().strftime("%a, %Y-%m-%d %H:%M")])

		U.logger.log(10, "at 0 mag; total steps done:{} ".format(stepsTotal))

			

		sensorDict["sensor"][0]["left"][0]  = 0
		## now we are at start
		## do full 360:
		pp = False
		U.logger.log(10, "first turn right(+) {} steps".format(len(sensorDict["sequence"])) )
		seqN       = 0
		if  sensorDict["sensor"][0]["status"] == 1:
			sensorDict["sensor"][0]["right"][0]  = 0
		for nn in range(len(sensorDict["sequence"])-1): # move right (+1) 
			steps, sensFired = move( oneEights*6,  1, force=40, stopIfMagSensor=[True,True] )
			stepsTotal += steps
			seqN +=1
			if pp: printLrLog("right === ", nn, steps)
			if  sensorDict["sensor"][1]["status"] == 1:
				sensorDict["sensor"][1]["right"][seqN]  = abs(stepsTotal)
			if  sensorDict["sensor"][0]["status"] == 1:
				sensorDict["sensor"][0]["right"][seqN]  = abs(stepsTotal)
		U.logger.log(10, "right(+) finished, total steps:{}".format(stepsTotal))

		rightLimit  = int(min(stepsIn360*1.01,max(stepsIn360*0.995,stepsTotal)))
		displayDrawLines(["right limit set,  confirming left limit", datetime.datetime.now().strftime("%a, %Y-%m-%d %H:%M")])
		U.logger.log(10, "right limit set, now  confirming left(-) limit,  should be at max  total steps:{}".format(stepsTotal))
		if getLightSensorValue(force=True): setColor(force=True)

		stepsTotal2 = 0
		seqN        = 8
		U.logger.log(10, "now turn left(-) {} steps".format(len(sensorDict["sequence"])) )
		time.sleep(0.5)
		if  sensorDict["sensor"][0]["status"] == 1:
			sensorDict["sensor"][0]["left"][seqN] = rightLimit - 0
		for nn in range(len(sensorDict["sequence"])-1):
			steps, sensFired = move( int(oneEights*2), -1, force=40, stopIfMagSensor=[True,True] )
			stepsTotal  += steps
			stepsTotal2 += abs(steps)
			seqN -=1
			if pp: printLrLog("left  === ", nn, steps)
			if  sensorDict["sensor"][1]["status"] == 1:
				sensorDict["sensor"][1]["left"][seqN] = rightLimit - stepsTotal2
			if  sensorDict["sensor"][0]["status"] == 1:
				sensorDict["sensor"][0]["left"][seqN] = rightLimit - stepsTotal2
			#time.sleep(2)
		#steps, sensFired = move( 4, -1, force=4, stopIfMagSensor=[False,False] )
		#stepsTotal  += steps
		#stepsTotal2 += abs(steps)

		leftLimit = stepsTotal2
	
		if getLightSensorValue(force=True): setColor(force=True)


		if pp: U.logger.log(10, unicode(sensorDict))
		if abs(rightLimit + leftLimit) > stepsIn360*2.01:
			addToBlinkQueue(text=["S","O","S"])

		time.sleep(0.1)

		maxStepsUsed  = int(min(stepsIn360*1.01,max(stepsIn360*0.99,rightLimit)))

		setwaitParams()

		currentSequenceNo = 0
		zeroPositionCount = lastPositionCount
		U.logger.log(20, "should be at position mag=0  ; waitBetweenSteps:{:.1f}; maxStepsUsed:{}, total steps:{}, zeromag@:{}".format(waitBetweenSteps,maxStepsUsed, stepsTotal, lastPositionCount))
		displayDrawLines(["wait:{:.1f}; nSteps:{}".format(waitBetweenSteps,maxStepsUsed), datetime.datetime.now().strftime("%a, %Y-%m-%d %H:%M")])
		time.sleep(1)
	except Exception, e:
		U.logger.log(40, u"Line {} has error={}".format(sys.exc_traceback.tb_lineno, e))

	return 



# ------------------    ------------------ 
def printLrLog(lead, a, b, extra="", short=False):
	global sensorDict
	try:
		if short:
			U.logger.log(20, "{} {} {} {}".format(lead, a, b, extra))
		else:
			U.logger.log(20, "{} {} {} {}\n0 : {}\n12:{}".format(lead, a,b,extra,sensorDict["sensor"][0],sensorDict["sensor"][1]) )
	except Exception, e:
		U.logger.log(40, u"Line {} has error={}".format(sys.exc_traceback.tb_lineno, e))



# ########################################
# #########     blinks  ##########
# ########################################

def addToBlinkQueue(text =[], color=[1,1,1], stop = False, end=False, restore = True):
	global blinkThread, stopBlink

	try:
		if stop: 
			stopBlink =True
			time.sleep(1)
			U.logger.log(10, " clear queue bf {}".format( blinkThread["queue"].qsize()) )
			blinkThread["queue"].queue.clear()
			U.logger.log(10, " clear queue af {}".format( blinkThread["queue"].qsize()) )
			stopBlink =True
			return 

		if end: 
			stopBlink =True
			time.sleep(1)
			U.logger.log(10, " clear queue bf {}".format( blinkThread["queue"].qsize()) )
			blinkThread["queue"].queue.clear()
			U.logger.log(10, " clear queue af {}".format( blinkThread["queue"].qsize()) )
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
	global gpiopinNumbers, currentRGBValue

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
					currentRGBValue[RGBNumber] = getIntensity(cm[RGBNumber], color[RGBNumber], RGBNumber )
					setGPIOValue( pin, 1, amplitude = currentRGBValue[RGBNumber] )	
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
	global ledCutoff
	global hour

	Vout = 0.3
	try:
		if lightShadowVsDown.find("normal") == -1 : Vin *= 0.5
		if Vin ==0: return 0.
		if lightOffBetweenHours !=[0,0]:
			if ( (hour >= lightOffBetweenHours[0] and hour < lightOffBetweenHours[1]) or
				 (hour >= lightOffBetweenHours[0] and lightOffBetweenHours[0] > lightOffBetweenHours[1]) or
				 (hour <  lightOffBetweenHours[1] and lightOffBetweenHours[0] > lightOffBetweenHours[1])
				) :	return 0.

		Vout=  min( intensityMax, max( ledCutoff, intensityMin, float(Vin) * colorFactor * intensitySlope *intensityRGB[RGBNumber] * lightSensorValue) * multiplyRGB[RGBNumber] 	)
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
	global timesBinsForRGB, rgbTime, av
	timesBinsForRGB     = [   0, 		 	4*60*60,	   5*60*60,		7*60*60,	8*60*60,	  9*60*60,		10*60*60,	   11*60*60,	12*60*60,	14*60*60,		15*60*60,	  16*60*60,     18*60*60,  20*60*60,   21*60*60,    23*60*60, 	24*60*60]
	rgbTime   			= [ [100,100,100], [100,90,90], [100,30,30], [100,50,50],  [100,70,70], [100,100,100], [100,100,100], [80,80,100], [60,60,100], [80,80,100],[100,100,100], [100,70,70], [100,30,30], [100,60,60], [100,90,90], [100,98,98], [100,100,100] ]
	ll = len(timesBinsForRGB)
	for ii in range(0, ll):
		av = (rgbTime[ii][0]+rgbTime[ii][1]+rgbTime[ii][2])/3.
		rgbTime[ii][0] /=av 
		rgbTime[ii][1] /=av 
		rgbTime[ii][2] /=av 
	U.logger.log(20, u"rgb/ time {} ".format(rgbTime) )
# ------------------    ------------------ 
def timeToColor(tt):
	global timesBinsForRGB, rgbTime, av

	try:
		rgbout= copy.copy(rgbTime[0])
		if tt < 3600: return rgbout
		for ii in range(1, len(timesBinsForRGB)):
			if tt > timesBinsForRGB[ii]: continue
			dt = (tt-timesBinsForRGB[ii-1])/(timesBinsForRGB[ii]-timesBinsForRGB[ii-1]) 
			for rr in range(3):
				rgbout[rr] = (dt * (rgbTime[ii][rr]-rgbTime[ii-1][rr]) + rgbTime[ii-1][rr])
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
		xx = rr["sensors"]
		light = ""
		sensor =""
		for ss in xx:
			for dev in xx[ss]:
				if "light" in xx[ss][dev]: 
					light =  xx[ss][dev]["light"]
					sensor =ss
					break
		if light == "" or sensor =="": return 
		lastTimeLightSensorFile = tt
		lightSensorValueREAD = float(light)
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
		U.logger.log(10, "lightSensorValue read:{:.0f}, raw:{:.3f};  new used:{:.4f};  last:{:.4f}; maxR:{:.1f}".format(lightSensorValueREAD, lightSensorValueRaw, lightSensorValue, lastlightSensorValue,  maxRange))
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
	global speedDemoStart
	global timeShift

	try:
		if speed !=1.0:
			secSinceMidnit = (time.time() - speedDemoStart)*speed
		else:
			today = datetime.date.today()
			secSinceMidnit  = (time.time() - time.mktime(today.timetuple()))
		secSinceMidnit += timeShift
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


# ------------------    ------------------ 
def setwaitParams():
	global waitBetweenSteps, secondsTotalInDay, maxStepsUsed, amPM1224, speed
	try:
		waitBetweenSteps 	= secondsTotalInDay / maxStepsUsed 
		if amPM1224 ==12:	waitBetweenSteps 	/= 2
		waitBetweenSteps /=speed
		sleepDefault = waitBetweenSteps/(5*speed)

	except Exception, e:
		U.logger.log(40, u"Line {} has error={}".format(sys.exc_traceback.tb_lineno, e))

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
			

#
# ------------------    ------------------ 
def dosundialShutdown():
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
	global useoffsetOfPositionCount, offsetOfPositionCount, lightShadowVsDown, stepsIn360, totalStepsDone, lasttotalStepsDone
	try:
		useoffsetOfPositionCount = int(offsetOfPositionCount)
		if lightShadowVsDown.find("normal") == -1:
			 useoffsetOfPositionCount += stepsIn360/2
		if useoffsetOfPositionCount !=0:
			# bring between -800 and 800 
			if   useoffsetOfPositionCount > stepsIn360:	useoffsetOfPositionCount -= stepsIn360
			if 	-useoffsetOfPositionCount > stepsIn360:	useoffsetOfPositionCount += stepsIn360
			if 	-useoffsetOfPositionCount > stepsIn360:	useoffsetOfPositionCount += stepsIn360
			#bring between -400.. 400 eg 700 --> -100  ; -700--> 100
			if    useoffsetOfPositionCount > stepsIn360/2: 	useoffsetOfPositionCount -= stepsIn360
			elif -useoffsetOfPositionCount > stepsIn360/2:	useoffsetOfPositionCount += stepsIn360
		U.logger.log(10, " useoffsetOfPositionCount:{}, offsetOfPositionCount:{}".format(useoffsetOfPositionCount,offsetOfPositionCount))

	except Exception, e:
		U.logger.log(40, u"Line {} has error={}".format(sys.exc_traceback.tb_lineno, e))

# ------------------    ------------------ 
def moveOffset():
	global useoffsetOfPositionCount, offsetOfPositionCount, lightShadowVsDown, stepsIn360, totalStepsDone, lasttotalStepsDone
	try:
		if useoffsetOfPositionCount !=0:
			if useoffsetOfPositionCount > 0: direction  = +1	
			if useoffsetOfPositionCount < 0: direction  = -1	
			U.logger.log(10, "moving  to useoffsetOfPositionCount:{}, offsetOfPositionCount:{}, dir:{}".format(useoffsetOfPositionCount,offsetOfPositionCount , direction))
			move(abs(useoffsetOfPositionCount), direction)
			U.logger.log(10, "at Offset")
			time.sleep(0.5)
		totalStepsDone 		= 0
		lasttotalStepsDone	= 0

	except Exception, e:
		U.logger.log(40, u"Line {} has error={}".format(sys.exc_traceback.tb_lineno, e))


# ------------------    ------------------ 
def wiggleArm():

	try:
		U.logger.log(10, u"wiggling arm to losen it: 5 steps l/r/l/r")
		move( 5,   1,  force=5, updateSequence=False, stopIfMagSensor=[False,False], stopIfBoundarySensor=[False,False])
		time.sleep(0.2)
		move( 5,  -1,  force=5, updateSequence=False, stopIfMagSensor=[False,False], stopIfBoundarySensor=[False,False])
		time.sleep(0.2)
		move( 5,   1,  force=5, updateSequence=False, stopIfMagSensor=[False,False], stopIfBoundarySensor=[False,False])
		time.sleep(0.2)
		move( 5,  -1,  force=5, updateSequence=False, stopIfMagSensor=[False,False], stopIfBoundarySensor=[False,False])

	except Exception, e:
		U.logger.log(40, u"Line {} has error={}".format(sys.exc_traceback.tb_lineno, e))


# ------------------    ------------------ 
def getFTPupdate():
	global lastUpdateCheck, lastUpdatecheckDay
	global sundialVersion
	global updateDownloadEnable

	try:
		if not updateDownloadEnable["sundial"]: return 
		if time.time()- lastUpdateCheck < 100:	return 
		lastUpdateCheck = time.time()
		now = datetime.datetime.now()
		day = now.day
		if day == lastUpdatecheckDay: 			return 
		lastUpdatecheckDay = day
		if not os.path.isdir(G.homeDir+"install"):
			os.system("mkdir  "+G.homeDir+"install")
		if not os.path.isdir(G.homeDir+"old"):
			os.system("mkdir  "+G.homeDir+"old")
		os.system("sudo /usr/bin/python {}getnewVersion.py {:.1f} {}.py  {} &".format(G.homeDir, sundialVersion, G.program, G.myPiNumber))

	except Exception, e:
		U.logger.log(40, u"Line {} has error={}".format(sys.exc_traceback.tb_lineno, e))



def execsundial(reqSpeed):

	global clockDict, clockLightSet, useRTC
	global sensor, output, inpRaw
	global oldRaw, lastRead, inp
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
	global lightSensNorm, lightSensNormDefault
	global intensityRGB
	global intensityMax, intensityMin, intensitySlope, ledCutoff
	global boundaryMode
	global currentlyMoving
	global limitSensorTriggered
	global lightShadowVsDown
	global displayStarted
	global offsetOfPositionCount, useoffsetOfPositionCount
	global lastPositionCount, zeroPositionCount, rightBoundaryOfCableCount, leftLimit
	global secForSpeedTestStart
	global lastBoundaryMode
	global lastsaveParameters
	global waitForOtherItems
	global sundialParameters
	global eth0IP, wifi0IP
	global secondsTotalInDay, secondsTotalInHalfDay
	global LastHourColorSetToRemember
	global hour, minute, second
	global lightOffBetweenHours
	global startWebServerSTATUS, startWebServerINPUT
	global timeShift, multiplyRGB
	global numberOfStepsCableAllowsMax
	global lastMove
	global waitbetweenSteps
	global lastUpdateCheck, lastUpdatecheckDay
	global sundialVersion
	global updateDownloadEnable
	global currentRGBValue
	global uptime

	morseCode= {"A":[0,1], 		"B":[1,0,0,0],	 "C":[1,0,1,0], "D":[1,0,0], 	"E":[0], 		"F":[0,0,1,0], 	"G":[1,1,0],	"H":[0,0,0,0], 	"I":[0,0],
				"J":[0,1,1,1], 	"K":[1,0,1], 	"L":[0,1,0,0], 	"M":[1,1], 		"N":[1,0], 		"O":[1,1,1], 	"P":[0,1,1,0],	"Q":[1,1,0,1], 	"R":[0,1,0],
				"S":[0,0,0], 	"T":[1], 		"U":[0,0,1], 	"V":[0,0,0,1], 	"W":[0,1,1], "X":[1,0,0,1], 	"%Y":[1,0,1,1], 	"Z":[1,1,0,0],
				"0":[1,1,1,1,1], "1":[0,1,1,1,1], "2":[0,0,1,1,1], "3":[0,0,0,1,1], "4":[0,0,0,0,1], "5":[0,0,0,0,0], "6":[1,0,0,0,0], "7":[1,1,0,0,0], "8":[1,1,1,0,0], "9":[1,1,1,1,0],
				"s":[0], # one short
				"l":[1], # one long
				"b":[0,0,0,1]}  # beethoven ddd DAAA

	currentRGBValue			= [0,0,0]
	updateDownloadEnable	= {"sundial":False}
	lastUpdateCheck			= time.time()
	lastUpdatecheckDay		= ""
	numberOfStepsCableAllowsMax = 6000
	startWebServerSTATUS	= ""
	startWebServerINPUT		= ""
	timeShift				= 0
	lightOffBetweenHours	= [0,0]
	sundialParameters		= {}
	lastsaveParameters		= time.time()
	lastBoundaryMode		= 0
	boundaryMode			= 0
	useoffsetOfPositionCount= 0
	offsetOfPositionCount	= 0
	lightShadowVsDown		="normal"
	limitSensorTriggered	= 0
	currentlyMoving			= time.time() + 10000.
	lightSensNormDefault	= 4000.
	lightSensNorm			= lightSensNormDefault
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
	speedDemoStart			= 1

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
	ledCutoff				= 0.00001
	intensityMin      		= ledCutoff

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
	lastPositionCount			= 0 
	zeroPositionCount			= 0

	U.setLogging()


	U.logger.log(30, "====================== starting  ======  version: {:.1f}\n".format(sundialVersion))


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
			if  displayStart() ==0: displayStarted = time.time()
			else: 					displayStarted = - time.time() -1000
		except:
			U.logger.log(40, " display did not start")
			displayStarted = -1
	

		displayDrawLines(["Status:   starting up", ".. read params, time..",  datetime.datetime.now().strftime("%a, %Y-%m-%d %H:%M")])



		setgpiopinNumbers()


		getParameters()


		if readParams() ==3:
			U.logger.log(40, " parameters not defined")
			U.checkParametersFile("parameters-DEFAULT-sundial", force = True)
			time.sleep(20)
			dosundialShutdown()
			U.restartMyself(reason=" bad parameters read", doPrint = True)

		U.getIPNumber() 
		eth0IP, wifi0IP, G.eth0Enabled, G.wifiEnabled = U.getIPCONFIG()
		webServerInputExtraText()
		U.setStartwebserverSTATUS()
		U.setStartwebserverINPUT()

		getPositions()

		getTime()

		uptime = subprocess.Popen("/usr/bin/uptime -s" ,shell=True,stdout=subprocess.PIPE,stderr=subprocess.PIPE).communicate()[0]

		U.echoLastAlive(G.program)


		settimeToColor()

		stopBlink	= False
		blinkThread = {"color":True, "stop":False, "end":False, "queue": Queue.Queue(), "thread": threading.Thread(name=u'blinkQueue', target=blinkQueue, args=())}	
		blinkThread["thread"].start()



		### here it starts 
		lightSensorValue = 0.1
		getLightSensorValue(force=True)
		setColor(force=True)

		updatewebserverStatus(status="starting")
		# for display on clock show info web site and change wifi and country settings
		if len(G.ipAddress) > 7:
			MENUSTRUCTURE[1][0][0][0] ="{}:{}".format(G.ipAddress,startWebServerSTATUS)
			MENUSTRUCTURE[1][0][2][0] ="{}:{}".format(G.ipAddress,startWebServerINPUT)
		else:
			MENUSTRUCTURE[1][0][0][0] ="no network"
			MENUSTRUCTURE[1][0][2][0] ="no setup"


		### this needs fixing!!  
		updatewebserverStatus(status="setting boundary")
		wiggleArm()
		displayDrawLines(["Status:     ","setting boundary",  datetime.datetime.now().strftime("%a, %Y-%m-%d %H:%M")])
		findBoundariesOfCabl(trigger=1)
	
		U.echoLastAlive(G.program)


		displayDrawLines(["Status:     finding",".. L/R  Stop-Limits",  datetime.datetime.now().strftime("%a, %Y-%m-%d %H:%M")])

		findLeftRight()

		U.echoLastAlive(G.program)


		getLightSensorValue(force=True)
		setColor(force=True)
		sleepDefault = waitBetweenSteps/(5*speed)


		U.logger.log(20, "\n=========clock starting at zero position, parameters:\nspeed:{:.1f}, totalStepsDone:{}, sleepDefault:{:.1f},\nwaitBetweenSteps:{:.2f},  amPM1224:{}, secSinceMidnit:{:.1f}, secSinceMidnit0:{:.1f}, zero@{}\nintensity Min:{}, Max:{}, Slope:{}, lightSNorm:{}, LightMin:{}, lightMax:{}, RGB:{} "
						 .format(speed, totalStepsDone, sleepDefault, waitBetweenSteps, amPM1224, secSinceMidnit,secSinceMidnit0, zeroPositionCount,intensityMin,intensityMax, intensitySlope, lightSensNorm, lightSensMin, lightSensMax, intensityRGB))
		time.sleep(0.1)

		getOffset()
		moveOffset()

		nextStep = 1


		U.logger.log(20, "eth0IP:%s:, wifi0IP:%s:, G.eth0Enabled:%s, G.wifiEnabled:%s"%(eth0IP, wifi0IP, unicode(G.eth0Enabled), unicode(G.wifiEnabled)))

		displayShowStandardStatus(force=True)

		expireDisplay = 50
		lastExpireDisplay = time.time()
		boundaryMode =0

		lastMove = time.time() - waitBetweenSteps
		totalStepsDone = 0
		waitForOtherItems = False
		saveParameters(force = True)
		while True:
				for iii in range(50):
					if not waitForOtherItems: break
					sleep(3)

				getFTPupdate()
			
				saveParameters()

				if speedDemoStart > 1 and time.time() - speedDemoStart > 300:
					U.restartMyself(reason=" resetting speed to normal after 300 secs", doPrint = True)

				if limitSensorTriggered != 0:
					U.restartMyself(reason="entering fixmode,  trigger of boundaries", doPrint = True)

				getTime()

				##  here we move
				setwaitParams()
				testIfMove()
				##  Here we move if needed
				nextMove = lastMove + waitBetweenSteps
				testIfRewind()
				sleep =  sleepDefault
				testIfBlink()
				slept = 0
				lastDisplay = 0
				startSleep = time.time()
				sleep = nextMove - startSleep
				endSleep = startSleep + sleep
				minSleep = 0.2
				ii = 1000
				lastDisplay = time.time()
				#print "sleep ", sleep," nextMove", nextMove,"minSleep",minSleep,"tt", time.time()
				U.echoLastAlive(G.program)

				while ii > 0:
					# check for light, other input, display 
					if readCommand(): break
					if getLightSensorValue():
						setColor(force=True)
					elif (  abs(lightSensorValueRaw - lightSensorValue) / (max(0.005, lightSensorValueRaw + lightSensorValue))  ) > 0.05:
							#print " step up down light: ",lightSensorValue, lightSensorValueRaw, (lightSensorValueRaw*1 + lightSensorValue*9) / 10.
							lightSensorValue = (lightSensorValueRaw*1 + lightSensorValue*9) / 10.
							lastlightSensorValue = lightSensorValue
							setColor(force=True)
					if ii % 100 == 0:
						U.echoLastAlive(G.program)
					ii -= 1
					time.sleep(minSleep)
					slept += minSleep

					if U.checkifRebooting(): 
						displayShowShutDownMessage()
						time.sleep(3)
						dosundialShutdown()
						time.sleep(1)
						exit()


					tt = time.time()
					if tt >= endSleep: break
					if tt - lastDisplay > 5:
						if displayStarted < -10:
							if time.time() + displayStarted > 300: # last ok start try > 300 secs ago if error 1300 secs
								if  displayStart() ==0: displayStarted = time.time()
								else: 					displayStarted = - time.time() -1000
								
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

execsundial(reqSpeed)
exit()
	


		

