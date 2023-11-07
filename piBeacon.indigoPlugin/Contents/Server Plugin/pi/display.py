#!/usr/bin/env python
# -*- coding: utf-8 -*-


## ok for py3 but not for LED pixel board 

import spidev
import sys
import os, subprocess, copy
import time, datetime
import RPi.GPIO as gpio
from PIL import Image
from PIL import ImageDraw
from PIL import ImageFont
import PIL.ImageOps	 
import PIL
import numpy as np
#import pygame


import	json
import	smbus

import threading
import signal
import math


sys.path.append(os.getcwd())
import	piBeaconUtils	as U
import	piBeaconGlobals as G

G.program = "display"
U.setLogging()

#
_defaultDateStampFormat			   = u"%Y-%m-%d %H:%M:%S"


class setupKillMyself:
	def __init__(self):
		signal.signal(signal.SIGINT, self.doExit)
		signal.signal(signal.SIGTERM, self.doExit)

	def doExit(self, signum, frame):
		global klillMyselfTimeout
		if klillMyselfTimeout > 0 and time.time() - klillMyselfTimeout > 20: # need to ignore for some seconds, receiving signals at startup 
			try: outputDev.delPy()
			except: pass
			U.logger.log(30, u"exiting display, received kill signal ")
			os.kill(os.getpid(), signal.SIGTERM)
			sys.exit()


class LCD1602():
	def __init__(self, i2caddr=0x3f,backgroundLightEnabed=1): 

		self.BUS= smbus.SMBus(1)
		self.LCD_ADDR = i2caddr
		self.BLEN = backgroundLightEnabed
		try:
			self.send_command(0x33) # Must initialize to 8-line mode at first
			time.sleep(0.005)
			self.send_command(0x32) # Then initialize to 4-line mode
			time.sleep(0.005)
			self.send_command(0x28) # 2 Lines & 5*7 dots
			time.sleep(0.005)
			self.send_command(0x0C) # Enable display without cursor
			time.sleep(0.005)
			self.clear()			# Clear Screen
			self.openlight()		# Enable the backlight
		except	Exception as e:
				U.logger.log(30,"", exc_info=True)
		return 
			

	def write_word(self, data):
		temp = data
		if self.BLEN == 1:
			temp |= 0x08
		else:
			temp &= 0xF7
		self.BUS.write_byte(self.LCD_ADDR ,temp)

	def send_command(self,comm):
		try:
			# Send bit7-4 firstly
			buf = comm & 0xF0
			buf |= 0x04				  # RS = 0, RW = 0, EN = 1
			self.write_word(buf)
			time.sleep(0.002)
			buf &= 0xFB				  # Make EN = 0
			self.write_word(buf)

			# Send bit3-0 secondly
			buf = (comm & 0x0F) << 4
			buf |= 0x04				  # RS = 0, RW = 0, EN = 1
			self.write_word(buf)
			time.sleep(0.002)
			buf &= 0xFB				  # Make EN = 0
			self.write_word(buf)
		except	Exception as e:
				U.logger.log(30,"", exc_info=True)

	def send_data(self,data):
		try:
			# Send bit7-4 first
			buf = data & 0xF0
			buf |= 0x05				  # RS = 1, RW = 0, EN = 1
			self.write_word(buf)
			time.sleep(0.002)
			buf &= 0xFB				  # Make EN = 0
			self.write_word(buf)

			# Send bit3-0 second
			buf = (data & 0x0F) << 4
			buf |= 0x05				  # RS = 1, RW = 0, EN = 1
			self.write_word(buf)
			time.sleep(0.002)
			buf &= 0xFB				  # Make EN = 0
			self.write_word(buf)
		except	Exception as e:
				U.logger.log(30,"", exc_info=True)


	def clear(self):
		self.send_command(0x01) # Clear Screen

	def openlight(self):  # Enable the backlight
		self.BUS.write_byte(self.LCD_ADDR,0x08)

	def write(self,x, y, str):
		x =max(0,min(x,15))
		y =max(0,min(y, 1))

		# Move cursor
		addr = 0x80 + 0x40 * y + x
		self.send_command(addr)

		for chr in str:
			self.send_data(ord(chr))

	def destroy(self):
		del self.BUS





#### this is the magic: need to kill the child (actually this pid !!!) , 
###	  otherwise its hanging, but not too early, let it finish starting up 
def doInterrupt():
		time.sleep(2.)
		os.kill(os.getpid(), signal.SIGTERM)
		return

class bigScreen :
	screen = None
	
	def __init__(self,overwriteXmax=0,overwriteYmax=0, name="pibeacon display"):
		global bigScreenSize, pygameInitialized
		import pygame
		self.pygame=pygame
		if not pygameInitialized:
			self.pygame.init()
		self.oldScreensize = [0,0]

		try: 
		##Ininitializes a new pygame screen using the framebuffer"
		# Based on "Python GUI in Linux frame buffer"
		# http://www.karoltomala.com/blog/?p=679
			disp_no = os.getenv("DISPLAY")
			if not pygameInitialized:
		
				# Check which frame buffer drivers are available
				# Start with fbcon since directfb hangs with composite output
				drivers = ['fbcon', 'directfb', 'svgalib']
				found = ""
				for driver in drivers:
					# Make sure that SDL_VIDEODRIVER is set
					if not os.getenv('SDL_VIDEODRIVER'):
						os.putenv('SDL_VIDEODRIVER', driver)
					try:
						self.pygame.display.init()
					except	Exception as e:
						U.logger.log(30,"", exc_info=True)
						U.logger.log(30, u"Driver: {0} failed.".format(driver))
						continue
					found = driver
					break
	
				if found == "":
					U.logger.log(30, u"bigscreen no driver out of :{};  found -- exiting".format(found) )
					raise Exception('No suitable video driver found!')
					return 
				U.logger.log(20, u"found: {}".format(driver)  )		 
				

			pygameInitialized = True

			## ge sizeList:  eg =  [(1680, 1050), (1440, 900), (1280, 1024), (1280, 960), (1152, 864), (1024, 768), (832, 624), (800, 600), (720, 400), (640, 480)]
			sizeList = self.pygame.display.list_modes()
			U.logger.log(20, u"screen sizeList:{}".format(sizeList) )
			fullScreenSize = sizeList[0]  #self.pygame.display.Info().current_w, self.pygame.display.Info().current_h]

			U.logger.log(20, u"Framebuffer 1: fullsize:{} - oldSize:{};  check if we want to overwrite supplied  x:{}; y:{}, displayResolution:{}".format(fullScreenSize, bigScreenSize, overwriteXmax, overwriteYmax, displayResolution) )
			for xy in sizeList:
				if displayResolution[0] == xy[0] and displayResolution[1] == xy[1]:
					fullScreenSize = xy
					break
			if self.oldScreensize != fullScreenSize:

				if disp_no:
					U.logger.log(20, "using X display = {0}".format(disp_no))
					if overwriteXmax == 0 and overwriteYmax == 0:
						bigScreenSize[0] = int(0.95*fullScreenSize[0])
						bigScreenSize[1] = int(0.95*fullScreenSize[1])
					else:
						bigScreenSize[0] = min(int(overwriteXmax), fullScreenSize[0])
						bigScreenSize[1] = min(int(overwriteYmax), fullScreenSize[1])
					self.pygame.display.set_caption(name)
					self.screen = self.pygame.display.set_mode(bigScreenSize)
					U.logger.log(20, u"Framebuffer 2.a size: {};  overwrite x:{}; y:{}".format(bigScreenSize, overwriteXmax, overwriteYmax) )
				else:
					if displayResolution != (0,0):
						if False and (displayResolution[0] > fullScreenSize[0] or displayResolution[1] > fullScreenSize[1]):
							bigScreenSize = fullScreenSize[0]
						else:
							bigScreenSize = displayResolution
						U.logger.log(20, u"Framebuffer 2.b size: set to indigo-dev output def: {} vs available {}".format( bigScreenSize, fullScreenSize) )
						self.screen = self.pygame.display.set_mode(displayResolution, self.pygame.FULLSCREEN)
					else:
						bigScreenSize = fullScreenSize
						self.screen = self.pygame.display.set_mode(sizeList[0], self.pygame.FULLSCREEN)
						U.logger.log(20, u"Framebuffer 2.c size: {};  ignore overwrite x:{}; y:{}, use fullscreen  -  xterm not running".format(bigScreenSize, overwriteXmax, overwriteYmax) )
					subprocess.call("echo fullScreen > "+G.homeDir+"pygame.active", shell=True) # after this we can not do startx, need to reboot first

			self.oldScreensize = fullScreenSize
			U.logger.log(20, u"got screen object" )

			# Clear the screen to start
			self.screen.fill((0, 0, 0))		   
			# Initialise font support
			self.pygame.font.init()
			# Render the screen
			self.pygame.display.update()
		except	Exception as e:
			U.logger.log(30,"", exc_info=True)


	def __del__(self):
		"Destructor to make sure pygame shuts down, etc."
		try: pass#  no good !!!   self.pygame.quit()
		except: pass
	
	def delPy(self):
		try:  self.pygame.quit()
		except: pass

	def clearScreen(self):
		return


	def sendImage(self,idata):
		global bigScreenSize
		# Fill the screen with red (255, 0, 0)
		t = self.pygame.image.frombuffer(idata.tobytes() , idata.size, idata.mode)
#		 t = self.pygame.image.fromstring(idata.tobytes() , idata.size, idata.mode)
		self.screen.blit(t,(0,0))
		self.pygame.display.flip() 



# ###########################  SSD1351 #################################################################
SSD1351_I2C_ADDRESS			= 0x3C	  # 011110+SA0+RW - 0x3C or 0x3D
SSD1351_SETCONTRAST			= 0x81
SSD1351_DISPLAYALLON_RESUME = 0xA4
SSD1351_DISPLAYALLON		= 0xA5
SSD1351_NORMALDISPLAY		= 0xA6
SSD1351_INVERTDISPLAY		= 0xA7
SSD1351_DISPLAYOFF			= 0xAE
SSD1351_DISPLAYON			= 0xAF
SSD1351_SETDISPLAYOFFSET	= 0xD3
SSD1351_SETCOMPINS			= 0xDA
SSD1351_SETVCOMDETECT		= 0xDB
SSD1351_SETDISPLAYCLOCKDIV	= 0xD5
SSD1351_SETPRECHARGE		= 0xD9
SSD1351_SETMULTIPLEX		= 0xA8
SSD1351_SETLOWCOLUMN		= 0x00
SSD1351_SETHIGHCOLUMN		= 0x10
SSD1351_SETSTARTLINE		= 0x40
SSD1351_MEMORYMODE			= 0x20
SSD1351_COLUMNADDR			= 0x21
SSD1351_PAGEADDR			= 0x22
SSD1351_COMSCANINC			= 0xC0
SSD1351_COMSCANDEC			= 0xC8
SSD1351_SEGREMAP			= 0xA0
SSD1351_CHARGEPUMP			= 0x8D
SSD1351_EXTERNALVCC			= 0x1
SSD1351_SWITCHCAPVCC		= 0x2

# Scrolling constants
SSD1351_ACTIVATE_SCROLL						= 0x2F
SSD1351_DEACTIVATE_SCROLL					= 0x2E
SSD1351_SET_VERTICAL_SCROLL_AREA			= 0xA3
SSD1351_RIGHT_HORIZONTAL_SCROLL				= 0x26
SSD1351_LEFT_HORIZONTAL_SCROLL				= 0x27
SSD1351_VERTICAL_AND_RIGHT_HORIZONTAL_SCROLL= 0x29
SSD1351_VERTICAL_AND_LEFT_HORIZONTAL_SCROLL = 0x2A
SSD1351_HORIZSCROLL		= 0x96
SSD1351_STOPSCROLL		= 0x9E
SSD1351_STARTSCROLL		= 0x9F



#?	SSD1351_DELAYS_HWFILL		 (3)
#? SSD1351_DELAYS_HWLINE	   (1)

# SSD1351 Commands
SSD1351_SETCOLUMN		= 0x15
SSD1351_SETROW			= 0x75
SSD1351_WRITERAM		= 0x5C
SSD1351_READRAM			= 0x5D
SSD1351_SETREMAP		= 0xA0
SSD1351_STARTLINE		= 0xA1
SSD1351_DISPLAYOFFSET	= 0xA2
SSD1351_DISPLAYALLOFF	= 0xA4
SSD1351_DISPLAYALLON	= 0xA5
SSD1351_NORMALDISPLAY	= 0xA6
SSD1351_INVERTDISPLAY	= 0xA7
SSD1351_FUNCTIONSELECT	= 0xAB
SSD1351_DISPLAYOFF		= 0xAE
SSD1351_DISPLAYON		= 0xAF
SSD1351_PRECHARGE		= 0xB1
SSD1351_DISPLAYENHANCE	= 0xB2
SSD1351_CLOCKDIV		= 0xB3
SSD1351_SETVSL			= 0xB4
SSD1351_SETGPIO			= 0xB5
SSD1351_PRECHARGE2		= 0xB6
SSD1351_SETGRAY			= 0xB8
SSD1351_USELUT			= 0xB9
SSD1351_PRECHARGELEVEL	= 0xBB
SSD1351_VCOMH			= 0xBE
SSD1351_CONTRASTABC		= 0xC1
SSD1351_CONTRASTMASTER	= 0xC7
SSD1351_MUXRATIO		= 0xCA
SSD1351_COMMANDLOCK		= 0xFD


SSD1351_WIDTH			= 128
SSD1351_HEIGHT			= 128



class SSD1351:
	import RPi.GPIO as gpio
	gpio.setwarnings(False)
	COMMAND = gpio.LOW
	DATA	= gpio.HIGH
	def __init__(self, dc, rst, cs,ce):
		try:
			self.rst = int(rst)
			self.dc = int(dc)
			self.cs = int(cs)
			self.ce = int(ce)  #(channel 0/1)
			self.width	= SSD1351_WIDTH
			self.height = SSD1351_HEIGHT
		
			gpio.setmode(gpio.BCM)

			gpio.setup(self.dc, gpio.OUT)
			gpio.output(self.dc, gpio.LOW)

			gpio.setup(self.rst, gpio.OUT)
			gpio.output(self.rst, gpio.HIGH)
		
			gpio.setup(self.cs, gpio.OUT)
			gpio.output(self.cs, gpio.HIGH)

			self.__OpenSPI() # Setup SPI.
			self.__Setup() # Setup device screen.
			#self.Clear() # Blank the screen.
			return
		except	Exception as e:
				U.logger.log(30,"", exc_info=True)
				U.logger.log(30, u"SPI likely not enabled")

	def __OpenSPI(self):
		self.spi = spidev.SpiDev()
		self.spi.open(0, self.ce )
		self.spi.mode = 3
		self.spi.max_speed_hz = 8000000
		self.spi.cshigh = False
		return

	def __WriteCommand(self, data):
		gpio.output(self.dc, self.COMMAND)
		if isinstance(data, list) or isinstance(data, tuple):
			self.spi.xfer(data)
		return

	def __WriteData(self, data):
		gpio.output(self.dc, self.DATA)
		if isinstance(data, list) or isinstance(data, tuple):
			self.spi.xfer(data)
		return
		
	def restart0(self):
		self.__WriteCommand([SSD1351_COMMANDLOCK])	# set command lock
		self.__WriteData([0x12])
		self.__WriteCommand([SSD1351_COMMANDLOCK])	# set command lock
		self.__WriteData([0xB1])
		self.__WriteCommand([SSD1351_SETREMAP])
		self.__WriteData([0x74])
		self.__WriteCommand([SSD1351_SETCOLUMN])
		self.__WriteData([0x00])
		self.__WriteData([0x7F])
		self.__WriteCommand([SSD1351_SETROW])
		self.__WriteData([0x00])
		self.__WriteData([0x7F])
		self.__WriteCommand([SSD1351_STARTLINE])  # 0xA1
		self.__WriteData([128])	 # this is for 128x128
		self.__WriteCommand([SSD1351_DISPLAYOFFSET])	 # 0xA2
		self.__WriteData([0x0])
	
	def __Setup(self):
		self.spi.cshigh = True
		self.spi.xfer([0])
		gpio.output(self.cs, gpio.LOW)
		time.sleep(0.1)
		gpio.output(self.rst, gpio.LOW)
		time.sleep(0.5)
		gpio.output(self.rst, gpio.HIGH)
		time.sleep(0.5)
		self.spi.cshigh = False
		self.spi.xfer([0])
		self.__WriteCommand([SSD1351_COMMANDLOCK])	# set command lock
		self.__WriteData([0x12])
		self.__WriteCommand([SSD1351_COMMANDLOCK])	# set command lock
		self.__WriteData([0xB1])
		self.__WriteCommand([SSD1351_DISPLAYOFF])	# 0xAE
		self.__WriteCommand([SSD1351_CLOCKDIV])		# 0xB3
		self.__WriteCommand([0xF1])						# 7:4 = Oscillator Frequency, 3:0 = CLK Div Ratio (A[3:0]+1 = 1..16)
		self.__WriteCommand([SSD1351_MUXRATIO])
		self.__WriteData([127])
		self.__WriteCommand([SSD1351_SETREMAP])
		self.__WriteData([0x74])
		self.__WriteCommand([SSD1351_SETCOLUMN])
		self.__WriteData([0x00])
		self.__WriteData([0x7F])
		self.__WriteCommand([SSD1351_SETROW])
		self.__WriteData([0x00])
		self.__WriteData([0x7F])
		self.__WriteCommand([SSD1351_STARTLINE])  # 0xA1
		self.__WriteData([128])	 # this is for 128x128
		self.__WriteCommand([SSD1351_DISPLAYOFFSET])	 # 0xA2
		self.__WriteData([0x0])
		self.__WriteCommand([SSD1351_SETGPIO])
		self.__WriteData([0x00])
		self.__WriteCommand([SSD1351_FUNCTIONSELECT])
		self.__WriteData([0x01])						 #internal (diode drop)
		self.__WriteCommand([SSD1351_PRECHARGE])		  # 0xB1
		self.__WriteCommand([0x32])
		self.__WriteCommand([SSD1351_VCOMH])			  # 0xBE
		self.__WriteCommand([0x05])
		self.__WriteCommand([SSD1351_NORMALDISPLAY])	  # 0xA6
		self.__WriteCommand([SSD1351_CONTRASTABC])
		self.__WriteData([0xC8])
		self.__WriteData([0x80])
		self.__WriteData([0xC8])
		self.__WriteCommand([SSD1351_CONTRASTMASTER])
		self.__WriteData([0x0F])
		self.__WriteCommand([SSD1351_SETVSL])
		self.__WriteData([0xA0])
		self.__WriteData([0xB5])
		self.__WriteData([0x55])
		self.__WriteCommand([SSD1351_PRECHARGE2])
		self.__WriteData([0x01])
		


		return

	def Remove(self):
		gpio.cleanup()
		self.spi.close()
		return


	def Clear(self):
		# self.__WriteCommand([CLEAR_WINDOW, 0, 0, 128, 128])
		return

	def TestEntireDisplay(self, enable):
		if enable:
			self.__WriteCommand([SSD1351_DISPLAYALLON])
		else:
			self.__WriteCommand([SSD1351_DISPLAYALLOFF])
		return

	def EnableDisplay(self, enable):
		if enable:
			self.__WriteCommand([SSD1351_DISPLAYON])
		else:
			self.__WriteCommand([SSD1351_DISPLAYOFF])
		return



		#self.__WriteCommand([CONTINUOUS_SCROLLING_SETUP, horizontal, 0x00, 0x3F, vertical, 0x00])
		return

	def EnableScrollMode(self, enable):
		if enable:
			self.__WriteCommand([SSD1351_ACTIVATE_SCROLL])
		else:
			self.__WriteCommand([SSD1351_DEACTIVATE_SCROLL])
		return



	def sendImage(self, buff):
		self.__WriteCommand([SSD1351_WRITERAM])
		bufLen= len(buff)
		for ll in range(0,bufLen,4096):
			self.__WriteData(buff[ll:min(bufLen,ll+4096)])
		return








# ###########################  st7735 for adafruit 1.8 #################################################################
#  copied and mod from Author : Bruce E. Hall, W8BH <bhall66@gmail.com>

#TFT to RPi connections
# PIN TFT RPi
# 1 backlight 3v3		==> #15
# 2 MISO <none>			==> na
# 3 CLK SCLK (GPIO 11)	==> #23
# 4 MOSI MOSI (GPIO 10) ==> #17
# 5 CS-TFT GND			==> #25 
# 6 CS-CARD <none>		==> na
# 7 D/C GPIO 25			==> #22
# 8 RESET <none>		==> na
# 9 VCC 3V3				==> #15
# 10 GND GND			==> #25
st7735_DC	   = 25
st7735_XSIZE   = 128
st7735_YSIZE   = 160
st7735_XMAX	   = st7735_XSIZE-1
st7735_YMAX	   = st7735_YSIZE-1
#Color constants
#TFT display constants
st7735_SWRESET = 0x01
st7735_SLPIN   = 0x10
st7735_SLPOUT  = 0x11
st7735_PTLON   = 0x12
st7735_NORON   = 0x13
st7735_INVOFF  = 0x20
st7735_INVON   = 0x21
st7735_DISPOFF = 0x28
st7735_DISPON  = 0x29
st7735_CASET   = 0x2A
st7735_RASET   = 0x2B
st7735_RAMWR   = 0x2C
st7735_RAMRD   = 0x2E
st7735_PTLAR   = 0x30
st7735_MADCTL  = 0x36
st7735_COLMOD  = 0x3A




class st7735:
	import RPi.GPIO as gpio
	gpio.setwarnings(False)
	COMMAND = gpio.LOW
	DATA	= gpio.HIGH
	def __init__(self, dc, rst, cs,ce):
		try:
			self.rst = int(rst)
			self.dc = int(dc)
			self.cs = int(cs)
			self.ce = int(ce)  #(channel 0/1)
			self.width	= st7735_XMAX
			self.height = st7735_YMAX
			#print "__init__", dc,rst,cs,ce
			gpio.setmode(gpio.BCM)

			gpio.setup(self.dc, gpio.OUT)
			#gpio.output(self.dc, gpio.LOW)
			self.__OpenSPI() # Setup SPI.
			self.__Setup() # Setup device screen.
			#self.Clear() # Blank the screen.
			return
		except	Exception as e:
				U.logger.log(30,"", exc_info=True)
				U.logger.log(30, u"SPI likely not enabled")

	def __OpenSPI(self):
		self.spi = spidev.SpiDev()
		self.spi.open(0, self.ce )
		#self.spi.mode = 0
		self.spi.mode = 0
		self.spi.max_speed_hz = 15000000
		return
	
	def __Setup(self):
		#print " st7735: __Setup"
		self.__WriteCommand([st7735_SWRESET]) 
		time.sleep(0.2)
		self.__WriteCommand([st7735_SLPOUT])  # set command lock
		self.__WriteCommand([st7735_COLMOD])  # set color mode 
		self.__WriteData([0x05])			  #	 ....  to 16 bit			 
		#self.__WriteCommand([st7735_DISPOFF])
		self.__WriteCommand([st7735_DISPON])
		self.clearScreen()
		#self.SetOrientation(180)
		
		
	def SetOrientation(self,degrees):
		"Set the display orientation to 0,90,180,or 270 degrees"
		if degrees==90: arg=0x60
		elif degrees==180: arg=0xC0
		elif degrees==270: arg=0xA0
		else: arg=0x00
		self.__WriteCommand([st7735_MADCTL])  # 
		self.__WriteData([arg])			   
		


	def clearScreen(self):		  
		#print " st7735: clearScreen"
		self.__WriteCommand([st7735_CASET]) #set column range (x0,x1)
		self.__WriteData([0,0,0,self.width])			  
		self.__WriteCommand([st7735_RASET]) #	  set row range (y0,y1)
		self.__WriteData([0,0,0,self.height])			   

		value = 0x0001
		valHi = value >> 8 #separate color into two bytes
		valLo = value & 0xFF

		buff = [valHi,valLo]*self.width*(self.height)
		bufLen= len(buff)
		#print "bufLen", bufLen
		self.__WriteCommand([st7735_RAMWR]) #	  RAM write
		gpio.output(self.dc, self.DATA)
		for ll in range(0,bufLen,2048):
			self.spi.writebytes(buff[ll:min(bufLen,ll+2048)])
		##time.sleep(2)
		return



	def restart0(self):
		self.clearScreen()
		return

	def __WriteCommand(self, data):
		gpio.output(self.dc, self.COMMAND)
		if isinstance(data, list) or isinstance(data, tuple):
			self.spi.writebytes(data)
		return

	def __WriteData(self, data):
		gpio.output(self.dc, self.DATA)
		if isinstance(data, list) or isinstance(data, tuple):
			self.spi.writebytes(data)
		return
		


	def Remove(self):
		gpio.cleanup()
		self.spi.close()
		return

	def EnableDisplay(self, enable):
		if enable:
			self.__WriteCommand([st7735_DISPON])
		else:
			self.__WriteCommand([st7735_DISPOFF])
		return

	def sendImage(self, buff):
		##self.clearScreen()
		self.__WriteCommand([st7735_RAMWR])
		bufLen= len(buff)
		for ll in range(0,bufLen,2048):
			self.__WriteData(buff[ll:min(bufLen,ll+2048)])
		return



# ###########################  SSD1351 #################################################################



############# oled import ####################################
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
	"""
	A device encapsulates the I2C connection (address/port) to the SH1106
	OLED display hardware. The init method pumps commands to the display
	to properly initialize it. Further control commands can then be
	called to affect the brightness. Direct use of the command() and
	data() methods are discouraged.
	"""

	def __init__(self, port=1, address=0x3C, width=128, height=64):
		##super(sh1106, self).__init__(port, address)
		self.width = width
		self.height = height
		self.pages = int(self.height / 8)
		self.cmd_mode =0
		self.data_mode = int(0x40)
		self.bus = smbus.SMBus(port)
		self.addr = int(address)

		self.command(
			const.DISPLAYOFF,
			const.MEMORYMODE,
			const.SETHIGHCOLUMN,	  0xB0, 0xC8,
			const.SETLOWCOLUMN,		  0x10, 0x40,
			const.SETCONTRAST,		  0x7F,
			const.SETSEGMENTREMAP,
			const.NORMALDISPLAY,
			const.SETMULTIPLEX,		  0x3F,
			const.DISPLAYALLON_RESUME,
			const.SETDISPLAYOFFSET,	  0x00,
			const.SETDISPLAYCLOCKDIV, 0xF0,
			const.SETPRECHARGE,		  0x22,
			const.SETCOMPINS,		  0x12,
			const.SETVCOMDETECT,	  0x20,
			const.CHARGEPUMP,		  0x14,
			const.DISPLAYON)

	def display(self, image):
		"""
		Takes a 1-bit image and dumps it to the SH1106 OLED display.
		"""
		assert(image.mode == '1')
		assert(image.size[0] == self.width)
		assert(image.size[1] == self.height)

		pix = list(image.getdata())
		page = 0xB0
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

	def display1(self, pix):
		# will receive just the bits, not the image
		page = 0xB0
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


class ssd1306():
	"""
	A device encapsulates the I2C connection (address/port) to the SSD1306
	OLED display hardware. The init method pumps commands to the display
	to properly initialize it. Further control commands can then be
	called to affect the brightness. Direct use of the command() and
	data() methods are discouraged.
	"""
	def __init__(self, port=1, address=0x3C, width=128, height=64):
		#super(ssd1306, self).__init__(port, address)
		self.width = width
		self.height = height
		self.pages = int(self.height / 8)
		self.cmd_mode =0
		self.data_mode = int(0x40)
		self.bus = smbus.SMBus(port)
		self.addr = int(address)

		self.command(
			const.DISPLAYOFF,
			const.SETDISPLAYCLOCKDIV, 0x80,
			const.SETMULTIPLEX,		  0x3F,
			const.SETDISPLAYOFFSET,	  0x00,
			const.SETSTARTLINE,
			const.CHARGEPUMP,		  0x14,
			const.MEMORYMODE,		  0x00,
			const.SEGREMAP,
			const.COMSCANDEC,
			const.SETCOMPINS,		  0x12,
			const.SETCONTRAST,		  0xCF,
			const.SETPRECHARGE,		  0xF1,
			const.SETVCOMDETECT,	  0x40,
			const.DISPLAYALLON_RESUME,
			const.NORMALDISPLAY,
			const.DISPLAYON)

	def display(self, image):
		"""
		Takes a 1-bit image and dumps it to the SSD1306 OLED display.
		"""
		assert(image.mode == '1')
		assert(image.size[0] == self.width)
		assert(image.size[1] == self.height)

		self.command(
			const.COLUMNADDR, 0x00, self.width-1,  # Column start/end address
			const.PAGEADDR,	  0x00, self.pages-1)  # Page start/end address

		pix = list(image.getdata())
		step = self.width * 8
		buf = []
		for y in range(0, self.pages * step, step):
			i = y + self.width-1
			while i >= y:
				byte = 0
				for n in range(0, step, self.width):
					byte |= (pix[i + n] & 0x01) << 8
					byte >>= 1

				buf.append(byte)
				i -= 1

		self.data(buf)

	def display1(self, pix):
		# will receive just the bits, not the image
		page = 0xB0
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


class const:
	CHARGEPUMP = 0x8D
	COLUMNADDR = 0x21
	COMSCANDEC = 0xC8
	COMSCANINC = 0xC0
	DISPLAYALLON = 0xA5
	DISPLAYALLON_RESUME = 0xA4
	DISPLAYOFF = 0xAE
	DISPLAYON = 0xAF
	EXTERNALVCC = 0x1
	INVERTDISPLAY = 0xA7
	MEMORYMODE = 0x20
	NORMALDISPLAY = 0xA6
	PAGEADDR = 0x22
	SEGREMAP = 0xA0
	SETCOMPINS = 0xDA
	SETCONTRAST = 0x81
	SETDISPLAYCLOCKDIV = 0xD5
	SETDISPLAYOFFSET = 0xD3
	SETHIGHCOLUMN = 0x10
	SETLOWCOLUMN = 0x00
	SETMULTIPLEX = 0xA8
	SETPRECHARGE = 0xD9
	SETSEGMENTREMAP = 0xA1
	SETSTARTLINE = 0x40
	SETVCOMDETECT = 0xDB
	SWITCHCAPVCC = 0x2



################### ###################	 analogClock  ############################################### START
def analogClockInit(inParms={}):
		global analogClockParams, minStartForNegative
		defparams = {"ticks12": {"start":0.9,  "end":1.0,  "width":6,  "fill":(150,150,150)}, ## ticks every 5 minutes
					 "ticks4":	{"start":0.77, "end":1.0,  "width":6,  "fill":(150,150,150)}, ## ticks at 0,15,30,45
					 "hh":		{"start":0.0,  "end":0.55, "width":35, "fill":(255,0,0)	   }, ## hour  hand params
					 "mm":		{"start":0.05, "end":0.75, "width":20, "fill":(0,255,0)	   }, ## minute hand params
					 "ss":		{"start":0.1,  "end":0.95, "width":6,  "fill":(0,0,255)	   }, ## sec hand params
					 "box":		{"on":"circle","fill":(80,80,80),"width":30},
					 "position":[245,370],													  ## center in pixel from top left 
					 "radius":	[240,330],													  ## radius of clock in x,y ,some displays are stretched need different scales in x,y
					 "flipY":	 -1,														  ## if display is flipped 
					 "mode":	"lineRound,,",												 ## modes
					 "font":	"Arial.ttf",
					 "width":	 "28"
							  }	 
		minStartForNegative = 0.1
		minIntValue   = 30 
		try:
			#print " into analogClock init2", inParms
			## set clock parameters
			analogClockParams = copy.copy(defparams)

			if inParms !={}:
				for pp in defparams:
					pp0 = pp
					if pp.find("ticks") == 0: pp0 = "ticks"
					if pp.find("box")	== 0: pp0 = "box"

					if pp0 in inParms:
						if type(analogClockParams[pp]) is dict:
							for kk in analogClockParams[pp]:
								if kk in inParms[pp0] and inParms[pp0] !="":
									analogClockParams[pp][kk] = copy.copy(inParms[pp0][kk])
						else:
							analogClockParams[pp] = copy.copy(inParms[pp0])

			for xx in ["hh","mm","ss"]:
				analogClockParams[xx]["fill"]  = getFill("screen", analogClockParams[xx]["fill"], minIntValue=minIntValue)
			for xx in ["ticks4","ticks12","box"]:
				analogClockParams[xx]["fill"]  = getFill("screen", analogClockParams[xx]["fill"], minIntValue=minIntValue)
			#print " into analogClockParams init2", analogClockParams
				
			analogClockParams["mode"]	=  str(analogClockParams["mode"]).split(",")
			if len(analogClockParams["mode"]) !=3: 
				analogClockParams["mode"]	=  str(defparams["mode"]).split(",")
			
			if defparams["radius"] != analogClockParams["radius"]:
				scale = (analogClockParams["radius"][0] / defparams["radius"][0] + analogClockParams["radius"][1] / defparams["radius"][1]  )*0.5
				analogClockParams["hh"]["width"]		= zoomit(analogClockParams["hh"]["width"] * scale)
				analogClockParams["mm"]["width"]		= zoomit(analogClockParams["mm"]["width"] * scale)
				analogClockParams["ss"]["width"]		= zoomit(analogClockParams["ss"]["width"] * scale)
				analogClockParams["ticks4"]["width"]	= zoomit(analogClockParams["ticks4"]["width"] * scale)
				analogClockParams["ticks12"]["width"]	= zoomit(analogClockParams["ticks12"]["width"] * scale)
			analogClockParams["position"]			= zoomit(analogClockParams["position"])
			analogClockParams["radius"]				= zoomit(analogClockParams["radius"])
			#print " into analogClockParams init3", analogClockParams

			
			## show first pic
			analogClockShow()
		except	Exception as e:
				U.logger.log(30,"", exc_info=True)
		
		return 
		
	
	
def analogClockShow(hours=True, minutes=True, seconds=True):
		global analogClockParams, minStartForNegative
		try:		

			R	   = analogClockParams["radius"]
			C	   = analogClockParams["position"]
			fill   = analogClockParams["box"]["fill"]
			W	   = float(analogClockParams["box"]["width"])/2.
			if analogClockParams["box"]["on"]=="box":
				draw.rectangle((C[0]-R[0]-W,C[1]-R[1]-W,C[0]+R[0]+W,C[1]+R[1]+W),fill=fill)
				draw.rectangle((C[0]-R[0]  ,C[1]-R[1]  ,C[0]+R[0]  ,C[1]+R[1]  ),fill=(0,0,0))
			elif analogClockParams["box"]["on"]=="circle":
				dotWRadius( C[0], C[1],	 fill,	  R[0]+W, R[1]+W)
				dotWRadius( C[0], C[1],	 (0,0,0), R[0],	  R[1])


			nowST = datetime.datetime.now()
			h =(nowST.hour)%12 
			m = nowST.minute 
			s = nowST.second 
			fontF =	 mkfont(analogClockParams)

			for minTicks in range(12):
			   #print "ticks", angle0, pos
				if analogClockParams["mode"][2] == "TicksNumbers":
					if minTicks %3 ==0: continue
				analogClockdrTheLine(float(3.14159*2./12. *	 minTicks), "ticks12")
		   
			for minTicks in range(4):
			   #print "ticks", angle0, pos
				if analogClockParams["mode"][2] != "TicksNumbers":
					analogClockdrTheLine(float(3.14159*2./4.  *	 minTicks), "ticks4")
				else:
					analogClockdrNumbers(float(3.14159*2./12.  *  (minTicks*3+3)),minTicks*3+3,"ticks4")

			# draw Hour hand
			if hours:
				analogClockdrTheLine(float(3.14159*2./12.	 * (h+m/60.)), "hh")

			# draw Minute hand
			if minutes:
				analogClockdrTheLine(float(3.14159*2./60.	 * m)		 , "mm")

			# draw Second hand
			if secs:
				analogClockdrTheLine(float(3.14159*2./60.	 * s)		 , "ss",ss=s)

			if  False and hours and analogClockParams["mode"][0].find("line") > -1:
				R	   = analogClockParams["radius"]
				C	   = analogClockParams["position"]
				dotWRadius(C[0]	 , C[1] , analogClockParams["hh"]["fill"], 2 * analogClockParams["hh"]["width"] * R[0]/(R[0]+R[1]), 2 * W * R[1]/(R[0]+R[1]) ) # inner circle 

			 

		except	Exception as e:
				U.logger.log(30,"", exc_info=True)
		return 


def analogClockdrNumbers(angle,number,hand):
		global analogClockParams, minStartForNegative
		global digitalClockParams
		global multIntensity

		global fontx
		try:
			da = 3.14159*0.5# rotate to 0 = top
			mode   = analogClockParams["mode"]
			Start  = analogClockParams[hand]["start"]
			End	   = analogClockParams[hand]["end"]
			fill   = analogClockParams[hand]["fill"]
			W	   = analogClockParams[hand]["width"]
			R	   = analogClockParams["radius"]
			C	   = analogClockParams["position"]
			Flip   = analogClockParams["flipY"]
			fw = int(analogClockParams["width"])
			pos=[C[0],C[1]]
			pos[0]+=		 math.cos(da-angle) * R[0] * End   # x end
			pos[1]+= Flip *	 math.sin(da-angle) * R[1] * End   # y end	 .. of line
			if number ==12: 
				pos[0]-= fw/1.9
				pos[1]+= 0
			if number ==3: 
				pos[0]-= fw/2.
				pos[1]-= fw/2.
			if number ==6: 
				pos[0]-= fw/4.
				pos[1]-= fw
			if number ==9: 
				pos[0]-= 0
				pos[1]-= fw/2.
			
			fontF =	 mkfont(analogClockParams)
			#print "number", angle,pos,number
			
			draw.text(pos, "{}".format(number), font=fontx[fontF], fill=(int(255.*multIntensity),int(255.*multIntensity),int(255.*multIntensity)))
		except	Exception as e:
				U.logger.log(30,"", exc_info=True)


def analogClockdrTheLine(angle,hand,ss=0):
		global analogClockParams, minStartForNegative
		try:
			mode   = analogClockParams["mode"]
			Start  = analogClockParams[hand]["start"]
			if mode[1] == "opposite": 
				Start= max(minStartForNegative,Start)
			End	   = analogClockParams[hand]["end"]
			fill   = analogClockParams[hand]["fill"]
			W	   = analogClockParams[hand]["width"]
			R	   = analogClockParams["radius"]
			R0	   = (R[0]+R[1])*0.5
			C	   = analogClockParams["position"]
			Flip   = analogClockParams["flipY"]

			if hand.find("ticks") == 0:
					P	 = [C[0],C[1],C[0],C[1]]
					P[0]+=		  math.sin(angle) * R[0] * Start   # x start
					P[1]+= Flip * math.cos(angle) * R[1] * Start   # y start
					P[2]+=		  math.sin(angle) * R[0] * End	   # x end
					P[3]+= Flip * math.cos(angle) * R[1] * End	   # y end	 .. of line
					draw.line( P, fill=fill, width=int(W) )



			elif mode[0].find("line") > -1:
				P	 = [C[0],C[1],C[0],C[1]]
				if mode[1]== "opposite":
					P[0]+= -	   math.sin(angle) * R[0] * Start	# x start
					P[1]+= -Flip * math.cos(angle) * R[1] * Start	# y start
					P[2]+=		   math.sin(angle) * R[0] * End		# x end
					P[3]+=	Flip * math.cos(angle) * R[1] * End		# y end	  .. of line
				else:
					P[0]+=		  math.sin(angle) * R[0] * Start	# x start
					P[1]+= Flip * math.cos(angle) * R[1] * Start	# y start
					P[2]+=		  math.sin(angle) * R[0] * End		# x end
					P[3]+= Flip * math.cos(angle) * R[1] * End		# y end	  .. of line

				draw.line( P, fill=fill, width=int(W) )

				if mode[0].find("lineRound") >-1:
					dotWRadius(	   P[2],   P[3] , fill,		(W*0.8) * R[0]/(R[0]+R[1]),		(W*0.8) * R[1]/(R[0]+R[1]) )  # add half circle at the end
					if hand in ["hh"]:
						dotWRadius(C[0]	 , C[1] , fill, 2 * W * R[0]/(R[0]+R[1]), 2 * W * R[1]/(R[0]+R[1]) ) # inner circle 



			elif mode[0].find("triangle") >-1:
				Px= [C[0],C[0],C[0]]
				Py= [C[1],C[1],C[1]]
				da = 3.14159*0.5# rotate to 0 = top
				# x'= x*costheta + y*sintheta }
				# y'=-x*sintheta + y*costheta .} 

				x1	 = Start*R0
				x2	 = Start*R0
				y1	 = +W
				y2	 = -W
				if mode[1]== "opposite":
					x1	 = -x1
					x2	 = -x2
				dx1=  (math.cos(da-angle) * x1	+ math.sin(da-angle) *y1 )	 # x start
				dy1=  (math.cos(da-angle) * y1	- math.sin(da-angle) *x1 )	 # y start
				dx2=  (math.cos(da-angle) * x2	+ math.sin(da-angle) *y2 )	 # x start
				dy2=  (math.cos(da-angle) * y2	- math.sin(da-angle) *x2 )	 # y start

				Px[0]+=dx1	*R[0]/R[1]
				Py[0]+=dy1	*R[1]/R[0]
				Px[1]+=dx2	*R[0]/R[1]
				Py[1]+=dy2	*R[1]/R[0]
				
				Px[2]+=				 math.cos(da-angle) * R[0] * End						 # x end
				Py[2]+=		  Flip * math.sin(da-angle) * R[1] * End						 # y end   .. of line

				draw.polygon( [(Px[0], Py[0]),(Px[1], Py[1]), (Px[2], Py[2])], fill = fill )

			return


		except	Exception as e:
				U.logger.log(30,"", exc_info=True)



		
def dotWRadius( x0, y0,	 fill, widthX, widthY,outline=None):
		try:
			draw.ellipse( (x0 - widthX , y0 - widthY , x0 + widthX , y0 + widthY ), fill=fill, outline=outline)
		except	Exception as e:
				U.logger.log(30,"", exc_info=True)


################### ###################	  analogClock  ############################################### END
	

################### ###################	 digitalClock  ############################################### START
def digitalClockInit(inParms={}):
		global intensity, intensityDevice
		global digitalClockParams, minStartForNegative
		defparams = {"position":[0,0],													  ## top left corner
					 "width":	40,														  ## font size 
					 "fill":	[255,255,255],											  ## color of digits
					 "flipY":	 -1,													  ## if display is flipped 
					 "format":	 "%H:%M:%S",											  ## digfital clock	 
					 "font":	"Arial.ttf",
							  }	 
		minStartForNegative = 0.1
		try:
			#print " into analogClock init2", inParms
			## set clock parameters
			digitalClockParams = copy.copy(defparams)
			## show first pic
			for pp in defparams:
				if pp in inParms:
					digitalClockParams[pp] = copy.copy(inParms[pp])
			digitalClockShow()
		except	Exception as e:
				U.logger.log(30,"", exc_info=True)
		return 
		
	
	
def digitalClockShow(hours=True, minutes=True, seconds=True):
		global multIntensity
		try:
			P	   = digitalClockParams["position"]
			fillD  = digitalClockParams["fill"]
			format = digitalClockParams["format"]

			nowST = datetime.datetime.now().strftime(format)
			fontF =	 mkfont(digitalClockParams)

			draw.text(P, nowST, font=fontx[fontF], fill=(int(fillD[0]*multIntensity),int(fillD[1]*multIntensity),int(fillD[2]*multIntensity)))
			 

		except	Exception as e:
				U.logger.log(30,"", exc_info=True)
		return 




################### ###################	  analogClock  ############################################### END
	
	
	
	
############# oled import ####################################
	
def RGBto565array( image,invert=False):
		pb = np.array(image).astype('uint16')
		if invert:
			pb= np.fliplr(np.transpose(pb,(1,0,2)))
		color = ((pb[:,:,0] & 0xF8) << 8) | ((pb[:,:,1] & 0xFC) << 3) | (pb[:,:,2] >> 3)
		return np.dstack(((color >> 8) & 0xFF, color & 0xFF)).flatten().tolist()




def readParams():
		global i2cAddress, devType, font, flipDisplay, PIN_CS , PIN_RST, PIN_DC, PIN_CE
		global lastRead, newRead
		global useLightSensorType, useLightSensorDevId, lightSensorSlopeForDisplay, lightSensorOnForDisplay, lightMinDimForDisplay
		global multIntensity, intensity, intensityDevice, lightSensorValue
		global runLoop, displayResolution

		newRead		= False
		inp,inpRaw,ttt = U.doRead(lastTimeStamp=lastRead)
		if ttt		== lastRead: return
		if inp		== "": return
		lastRead	= ttt
		newRead		= True

		U.getGlobalParams(inp)
		if "output"				in inp:	 
			output=				  (inp["output"])
			if "display" in output:
				for devid in output["display"]:
					ddd = output["display"][devid][0]
					if "devType"  not in ddd: continue
					devType		= ddd["devType"]
						
					i2cAddress = U.getI2cAddress(ddd, default=0)


					if "font"	 in ddd: 
						font	= ddd["font"]
					if "intensity" in ddd:
						intensityDevice	 = int(ddd["intensity"])/100.
						multIntensity = intensity * intensityDevice * lightSensorValue
					if "flipDisplay" in ddd:
						flipDisplay	 =ddd["flipDisplay"]


						
					### for SSD1351! device	   
					if "PIN_CS" in ddd:
						try:	PIN_CS	= int(ddd["PIN_CS"])
						except: pass
					if "PIN_CE" in ddd:
						try:	PIN_CE	= int(ddd["PIN_CE"])
						except: pass
					if "PIN_DC" in ddd:
						try:	PIN_DC	= int(ddd["PIN_DC"])
						except: pass
					if "PIN_RST" in ddd:
						try:	PIN_RST = int(ddd["PIN_RST"])
						except: pass


					lightSensorOnForDisplay = ddd.get("lightSensorOnForDisplay",False)

					if lightSensorOnForDisplay:
						if "lightSensorForDisplayDevIdType" in ddd:
							try:	
								useLightSensorDevId =     ddd["lightSensorForDisplayDevIdType"].split("-")[0]
								useLightSensorType  =     ddd["lightSensorForDisplayDevIdType"].split("-")[1]
							except	Exception as e:
									U.logger.log(30,"", exc_info=True)

						if "lightSensorSlopeForDisplay" in ddd:
							try:	
								lightSensorSlopeForDisplay = max(0.01, min(300., float(ddd["lightSensorSlopeForDisplay"]) ) )
							except	Exception as e:
									U.logger.log(30,"", exc_info=True)
						if "lightMinDimForDisplay" in ddd:
							try:	
								lightMinDimForDisplay = max(0.0, min(1., float(ddd["lightMinDimForDisplay"]) ) )
							except: pass


					if "displayResolution" in ddd:
						try:	
							xx = ddd["displayResolution"]
							if   "x" in xx: x ="x"
							elif "," in xx: x =","
							xx = ddd["displayResolution"].split(x)
							if len(xx) ==2:
								displayResolution = (int(xx[0]),int(xx[1]))
						except: pass

			else:
				runLoop = False

		else:
			runLoop = False
		if not runLoop:
			subprocess.call("rm "+G.homeDir+"temp/display.inp > /dev/null 2>&1", shell=True)
			U.logger.log(30, u"exiting display, output dev display not defined")
			try: outputDev.delPy()
			except: pass
			os.kill(os.getpid(), signal.SIGTERM)
			sys.exit()
		return		

		
def checkRGBcolor(inV, defColor, RGBtype="RGB", minIntValue= 0):
	global multIntensity
	try:
		inValue=str(inV)
		if RGBtype == "RGB":
			if inValue.count(",") == 2:
				value= str(inValue).strip("[").strip("]").strip("(").strip(")").replace(" ","").split(",")
				for ii in range(3):
					value[ii]=int(float(value[ii])*multIntensity)
					if value[ii] !=0: value[ii]=max(minIntValue,value[ii])
				#U.logger.log(20, u"checkRGBcolor  inV:{}, value:{}".format inV, value))
				return tuple(value)
			elif inValue.count(",") == 0:
				for ii in range(3):
					value[ii]=int(float(inValue)*multIntensity)
					if value[ii] !=0: value[ii]=max(minIntValue,value[ii])
			return tuple(value)
		else:
			try:
				retV = int(inValue) 
				if retV != 0: retV = max(minIntValue, retV)
				return retV
			except:
				return defColor
	except	Exception as e:
		return defColor


def updateDevice(outputDev,matrix, overwriteXmax=0, overwriteYmax=0, reset=""):
	global	maxPages, i2cAddress,lasti2cAddress, devType,devTypeLast, font, flipDisplay, PIN_CS , PIN_RST, PIN_DC, PIN_CE
	global bigScreenSize
	port		= 1

	ymax = 1
	xmax = 1
	xmin = 0
	ymin = 0

	try:
		if devType.lower().find("rgbmatrix") >-1:
			if matrix == "":
				if devType.lower() == "rgbmatrix16x16":
					ymax = 16
					xmax = 16
				elif devType.lower() == "rgbmatrix32x16":
					ymax = 16
					xmax = 32
				elif devType.lower() == "rgbmatrix32x32":
					ymax = 32
					xmax = 32
				elif devType.lower() == "rgbmatrix64x32":
					ymax = 32
					xmax = 64
				elif devType.lower() == "rgbmatrix96x32":
					ymax = 32
					xmax = 96

				if int(sys.version[0]) >=3:
					from rgbmatrix import RGBMatrix as Adafruit_RGBmatrix
					from rgbmatrix import RGBMatrixOptions
					options = RGBMatrixOptions()
					options.rows = xmax
					options.cols = ymax
					options.chain_length = 1
					options.parallel = 1
					options.hardware_mapping = 'regular'  # If you have an Adafruit HAT: 'adafruit-hat'
					matrix = RGBMatrix(options = options)

				else:
					sys.path.append(os.getcwd()+"/neopix2")
					from rgbmatrix import Adafruit_RGBmatrix
			
					matrix = Adafruit_RGBmatrix(ymax, xmax//32)


		elif devType.lower()== "ssd1306":
			if outputDev == "":
				outputDev = ssd1306(port=port, address=i2cAddress) 
			ymax = 64
			xmax = 128
		elif devType.lower() == "sh1106":
			if outputDev == "":
				outputDev = sh1106(port=port, address=i2cAddress)  
			ymax = 64
			xmax = 128
		elif devType.lower() == "ssd1351":
			if outputDev == "":
				outputDev = SSD1351(PIN_DC, PIN_RST, PIN_CS,PIN_CE)	 
				outputDev.EnableDisplay(True)
			ymax = 128
			xmax = 128
		elif devType.lower() == "st7735":
			if outputDev == "":
				outputDev = st7735(PIN_DC, PIN_RST, PIN_CS,PIN_CE)	
				#outputDev.EnableDisplay(True)
			ymax = 128
			xmax = 160
		elif devType.lower().find("screen")>-1:
			if reset !="":
				try: 
					U.logger.log(20, u"resetting  screen output device")
					##outputDev.delPy()
				except: pass
				outputDev = ""
				if reset == "stop": return 

			if outputDev == "":
				os.putenv ( "SDL_VIDEODRIVER" , "fbcon" )
				interrupter = threading.Thread(target=doInterrupt)
				interrupter.start()
				outputDev=bigScreen(overwriteXmax=overwriteXmax, overwriteYmax=overwriteYmax)
				ymax = bigScreenSize[1]
				xmax = bigScreenSize[0]
				
		elif devType.lower().find("lcd1602")>-1:
			if outputDev == "":
				outputDev = LCD1602(i2caddr=i2cAddress,backgroundLightEnabed=1)	 
				ymax = 2
				xmax = 16
		fontDir= G.homeDir+"fonts/"

	except	Exception as e:
			U.logger.log(30,"", exc_info=True)
			if "{}".format(e).find("fontDir") > 0:
				U.logger.log(30," display device not properly setup.. display device interface (eg SPI ...) not properly setup..")
			sys.exit()

	return fontDir,xmin,xmax,ymin,ymax,matrix,outputDev






def getScrollPages(data):
	try:
		if "scrollxy" in data:
			scrollxy = data["scrollxy"]
			if scrollxy == "0": scrollxy=""
		else:
			scrollxy=""

		scrollPages =1
		if "scrollPages" in data:
			try: scrollPages = int(data["scrollPages"])
			except: pass

		scrollDelay=0.2
		if "scrollDelay" in data:
			try:
				scrollDelay = float(data["scrollDelay"])
			except: pass

		scrollDelayBetweenPages=0.0
		if "scrollDelayBetweenPages" in data:
			try:
				scrollDelayBetweenPages = float(data["scrollDelayBetweenPages"])
			except: pass
		return scrollPages, scrollDelay, scrollDelayBetweenPages, scrollxy
	except	Exception as e:
			U.logger.log(30,"", exc_info=True)

def setScrollPages(scrollxy,scrollPages):
	global maxPages
	maxPagesX=1
	maxPagesY=1
	scrollPages=1
	if	scrollxy in ["up","down","left","right"]:
		if scrollxy.find("up") > -1 or scrollxy.find("down") > -1:	
			maxPagesY = maxPages
		elif scrollxy.find("left") > -1 or scrollxy.find("right") > -1:	 
			maxPagesX = maxPages

		if scrollPages !="":
			try:
				scrollPages = int(data["scrollPages"])
				if scrollxy.lower().find("left") >-1 or	 scrollxy.lower().find("right") >-1:
					scrollPages= min(maxPagesX,scrollPages)	   
				if scrollxy.lower().find("up") >-1 or  scrollxy.lower().find("down") >-1:
					scrollPages= min(maxPagesY,scrollPages)	   
			except: pass
		else:
			maxPagesX=1
			maxPagesY=1
	maxPagesY= min(maxPagesY,scrollPages)	 
	maxPagesX= min(maxPagesX,scrollPages)	 

	scrollPages = min(scrollPages,max(maxPagesX,maxPagesY)) 
	
	lastscrollPages = scrollPages
	lastScrollxy	= scrollxy
	return scrollPages, maxPagesY, maxPagesX, scrollxy, lastScrollxy, lastscrollPages


def mkfont(cmd):
	global fontx
	fontF ="0"
	if "font" in cmd and len(cmd["font"]) >0:
		font=cmd["font"]
	 
		fontw="0"
		if "width" in cmd: 
			try: fontw = str(zoomit(cmd["width"]))
			except: pass

		if font+fontw not in fontx:
			try:
				fontF = font+fontw
				if	 font.lower().find(".pil")>-1:
					U.logger.log(10,fontDir+font)
					fontx[fontF] = ImageFont.load(fontDir+font)
				elif  font.lower().find(".ttf")>-1:
					fontx[fontF] = ImageFont.truetype(fontDir+font, int(fontw))
			except	Exception as e:
					U.logger.log(30,"", exc_info=True)
		else:
			fontF = font+fontw
	return fontF

def getFill(devType,fill,minIntValue = 0):
		if devType.lower().find("rgbmatrix")> -1: 
			fill = checkRGBcolor(str(fill),fill, minIntValue=minIntValue)
		elif  devType.lower() in ["ssd1351"]: 
			fill = checkRGBcolor(str(fill),fill, minIntValue=minIntValue)
		elif  devType.lower().find("screen") >-1: 
			fill = checkRGBcolor(str(fill),fill, minIntValue=minIntValue)
		elif  devType.lower() in ["st7735"]: 
			fill = checkRGBcolor(str(fill),fill, minIntValue=minIntValue)
		elif  devType.lower() in ["sh1106","ssd1306"]: 
			fill = checkRGBcolor(str(fill),fill, minIntValue=minIntValue, RGBtype="1")
		return fill

# ------------------    ------------------ 
def onDecision(cType,offTime0,onTime,offTime1,startRepeatTime,tti):
	if offTime0 == 0 and offTime1==0: 
		#print cType, offTime0,onTime,offTime1,startRepeatTime,tti, True
		return True
	dd = (tti - startRepeatTime ) % (onTime+offTime0+offTime1)	
	if	 dd <  offTime0 or dd >=  offTime0+onTime: 
		#print cType, offTime0,onTime,offTime1,startRepeatTime,tti, False
		return False
	else:
		#print cType, offTime0,onTime,offTime1,startRepeatTime,tti, True
		return True

# ------------------    ------------------ 
def getLightSensorValue(force=False):
	global  lastlightSensorValue, lastTimeLightSensorValue, lastTimeLightSensorFile, lightSensorValueRaw, lightSensorSlopeForDisplay
	global lightSensMax, lightMinDimForDisplay, lightSensorOnForDisplay, intensity, useLightSensorType, useLightSensorDevId
	global multIntensity, intensity, intensityDevice, lightSensorValue
	try:
		tt0 = time.time()
		#U.logger.log(20, "lightSensorValue 1")
		if not lightSensorOnForDisplay:		return False
		if (tt0 - lastTimeLightSensorValue < 2) and not force:		return False
		if not os.path.isfile(G.homeDir+"temp/lightSensor.dat"):	return False
###{  "sensors": {    "i2cOPT3001": {      "393522233": {        "light": 40.96      }    }  },   "time": 1568991254.784975}
		rr , raw = U.readJson(G.homeDir+"temp/lightSensor.dat")
		if rr == {}:
			time.sleep(0.1)
			rr, raw = U.readJson(G.homeDir+"temp/lightSensor.dat")
		subprocess.call("sudo rm "+G.homeDir+"temp/lightSensor.dat", shell=True)
		if rr == {} or "time" not in rr: 							return False
		if "sensors" not in rr: 									return False
		U.logger.log(10, "lightSensor useLightSensorDevId{}, useLightSensorType:{}  read: {} ".format(useLightSensorDevId, useLightSensorType, rr) )
		if useLightSensorType not in rr["sensors"]: 				return False
		if useLightSensorDevId  not in rr["sensors"][useLightSensorType]: return 
		tt = float(rr["time"])
		if tt == lastTimeLightSensorFile:						 	return False	

		lightSensorValueREAD = -1
		for devId in rr["sensors"][useLightSensorType]:
			if devId == useLightSensorDevId:
				lightSensorValueREAD = float(rr["sensors"][useLightSensorType][devId]["light"])
				break
		if lightSensorValueREAD ==-1 : return 
		lastTimeLightSensorFile = tt

		#U.logger.log(20, "lightSensorValue 2")
		if   useLightSensorType == "i2cTSL2561":	maxRange = 2000.
		elif useLightSensorType == "i2cOPT3001":	maxRange = 60.
		elif useLightSensorType == "i2cVEML6030":	maxRange = 700.
		elif useLightSensorType == "i2cIS1145":		maxRange = 2000.
		else:										maxRange = 1000.

		lightSensorValueRaw = lightSensorValueREAD/maxRange  *   lightSensorSlopeForDisplay
		lightSensorValueRaw = max(lightMinDimForDisplay, lightSensorValueRaw)
		if lightSensorValueRaw >= lightSensMax:
			lightSensorValueRaw = 1.
		# lightSensorValueRaw should be now between ~ 0.001 and ~1.
		#if force:	
		#	lightSensorValue = lightSensorValueRaw
		#	return True
		if (  abs(lightSensorValueRaw-lastlightSensorValue) / (max (0.005, lightSensorValueRaw+lastlightSensorValue))  ) < 0.05: return False
		lightSensorValue = (lightSensorValueRaw*1 + lastlightSensorValue*3) / 4.
		lastTimeLightSensorValue = tt0
		U.logger.log(10, "lightSensorValue sl:{};  read:{:.0f}, raw:{:.3f};  new used:{:.4f};  last:{:.4f}; maxR:{:.1f}, inties:{}; {}; {}".format(lightSensorSlopeForDisplay, lightSensorValueREAD, lightSensorValueRaw, lightSensorValue, lastlightSensorValue,  maxRange, intensity, intensityDevice,  multIntensity) )
		lastlightSensorValue = lightSensorValue
		multIntensity = intensity * intensityDevice * lightSensorValue
		return True
	except Exception as e:
		U.logger.log(40,"", exc_info=True)
	return False

# ------------------    ------------------ 
def checkLightSensor():
	global lastlightSensorValue, lastTimeLightSensorValue, lastTimeLightSensorFile, lightSensorValueRaw, lightSensorSlopeForDisplay
	global lightSensMax, lightMinDimForDisplay, lightSensorOnForDisplay
	global multIntensity, intensity, intensityDevice, lightSensorValue
	try:
		
			
		if not lightSensorOnForDisplay : return 
		if not getLightSensorValue(force=True):
			if (  abs(lightSensorValueRaw - lightSensorValue) / (max(0.005, lightSensorValueRaw + lightSensorValue))  ) > 0.05:
				U.logger.log(10, " step up down light: lsv:{};  lsvR:{};  newlsv:{}; inties:{}; {}; {}".format(lightSensorValue, lightSensorValueRaw, (lightSensorValueRaw*1 + lightSensorValue*3) / 4.,  intensity, intensityDevice,  multIntensity) )
				lightSensorValue     = (lightSensorValueRaw*1 + lightSensorValue*3) / 4.
				lastlightSensorValue = lightSensorValue
				multIntensity = intensity * intensityDevice * lightSensorValue
			else:
				if lightSensorValue == lightSensorValueRaw: return 
				lightSensorValue     = lightSensorValueRaw
				multIntensity = intensity * intensityDevice * lightSensorValue
				U.logger.log(10, " step up down light: lsv:{};  lsvR:{};  newlsv:{}; inties:{}; {}; {}".format(lightSensorValue, lightSensorValueRaw, (lightSensorValueRaw*1 + lightSensorValue*3) / 4.,  intensity, intensityDevice,  multIntensity) )
	except Exception as e:
		U.logger.log(40,"", exc_info=True)



# ------------------    ------------------ 
def zoomit(inVar):
	global zoom
	var = copy.copy(inVar)
	try:
		#U.logger.log(20, u"zoomit1 var:{}; type(var):{}".format(var, type(var)) )
		if type(var) == type([]):
			for ll in range(len(var)):
				if var[ll] >0:
					var[ll] = int(max(1.0,var[ll]*zoom))
				else:
					var[ll] = int(var[ll]*zoom)
			#U.logger.log(20, u"zoomit2 var:{}; type(var):{} ".format(var, type(var)) )
			return var
		else:
			if inVar > 0:
				var = int(max(1.0,var*zoom))
			else:
				var = int(var*zoom)
			return   var

	except Exception as e:
		U.logger.log(40,"", exc_info=True)
		U.logger.log(40, u"zoomitE var:{}; type(var):{} ".format(var, type(var)) )
	return inVar

######### main	########
global maxPages, i2cAddress,lasti2cAddress, devType,devTypeLast, font, flipDisplay, PIN_CS , PIN_RST, PIN_DC, PIN_CE
global fontx, bigScreenSize
global lastRead, newRead
global lastlightSensorValue, lastTimeLightSensorValue, lastTimeLightSensorFile, lightSensorValueRaw, lightSensorSlopeForDisplay
global lightSensMax, lightMinDimForDisplay, lightSensorOnForDisplay
global useLightSensorType, useLightSensorDevId
global multIntensity, intensity, intensityDevice, lightSensorValue
global bigScreenSize
global zoom, runLoop, pygameInitialized
global klillMyselfTimeout, displayResolution

displayResolution			= (0,0)

klillMyselfTimeout			= time.time()
pygameInitialized			= False

runLoop 					= True
	
zoom 						= 1.0
bigScreenSize				= [0,0]

useLightSensorType 			= ""
useLightSensorDevId 		= 0

lightSensorValue			= 1.
lastlightSensorValue 		= 0
lastTimeLightSensorValue	= 0
lastTimeLightSensorFile 	= 0
lightSensorValueRaw 		= 1
lightSensorSlopeForDisplay 	= 1.49
lightSensMax  				= 1
lightMinDimForDisplay  		= 0.3
lightSensorOnForDisplay 	= False


newRead						= True
lastRead					= 0


####################SSD1351 pins
PIN_CS						= 19	#  GPIO
PIN_RST 					= 26	#  
PIN_DC						= 25	#	 
PIN_CE						= 1		# device number	 ok

lastAlive  					= 0
i2cAddress 					= 60

######### scroll params
scrollxy		 			= ""
lastScrollxy	 			= ""

lastscrollPages	 			= 1
scrollPages		 			= 1
maxPages		 			= 9
lastdevType					= ""
devType						= "yy"

font						= "Red Alert"
fontx						= {"0": ImageFont.load_default()}
intensityDevice	 			= 1.
flipDisplay		 			= "0"
intensity		 			= 1.
loop			 			= 0
lasti2cAddress	 			= 0
outputDev		 			= ""
matrix			 			= ""
startAtDateTime	  			= time.time()
fontDir 					= G.homeDir+"fonts"

readParams()

lasti2cAddress				= i2cAddress
devTypeLast					= devType 
items			 			= []
myPID			 			= str(os.getpid())

U.setLogLevel()
U.logger.log(30,"starting display")
U.killOldPgm(myPID,G.program+".py")
U.echoLastAlive(G.program)

#setupKillMyself()

try:
	if len(sys.argv[1]) > 10:
		items=[sys.argv[1]]
	else: 
		items  = [json.dumps({"restoreAfterBoot": False, "resetInitial": "","scrollxy":scrollxy,"startAtDateTime":startAtDateTime})]
		subprocess.call("cp "+G.homeDir+"display.inp "+G.homeDir+"temp/display.inp ", shell=True )
except:
	items  = [json.dumps({"restoreAfterBoot": False, "resetInitial": "","scrollxy":scrollxy,"startAtDateTime":startAtDateTime})]
	subprocess.call("cp "+G.homeDir+"display.inp "+G.homeDir+"temp/display.inp ", shell=True )

time.sleep(0.1)
#data = json.loads(items[0])

fontDir,xmin,xmax,ymin,ymax,matrix,outputDev = updateDevice(outputDev,matrix)


scrollPages, maxPagesY, maxPagesX, scrollxy, lastScrollxy, lastscrollPages=	 setScrollPages(scrollxy,scrollPages)

imageDefined 				= False
TextForLCD					= [" "," "]
TextPosForLCD 				= [0,0]
loopCount					= 0
lastAnalog					= time.time()
lastDigital					= time.time()
digitalclockInitialized		= ""
analogclockInitialized		= ""

U.logger.log(20,"looping over input" )

while runLoop:
	try:
		lastPos =[]
		for item in items:
			try:
				if len(item) < 10: continue
				data		= json.loads(item)
				#print json.dumps(data,sort_keys=True, indent=2)
			except	Exception as e:
				U.logger.log(30,"bad input {}".format(item) )
				U.logger.log(30,"", exc_info=True)
				continue
			
			if devType != devTypeLast :	 # restart	myself if new device type
				U.logger.log(30, " restarting due to new device type, old="+devTypeLast+" new="+"devType")
				time.sleep(0.2)
				subprocess.call("/usr/bin/python "+G.homeDir+"display.py &", shell=True)
			if i2cAddress != lasti2cAddress :  # restart  myself if new device type
				U.logger.log(30, " restarting due to new device type, old={}, new=".format(lasti2cAddress, i2cAddress))
				time.sleep(0.2)
				subprocess.call("/usr/bin/python "+G.homeDir+"display.py &", shell=True)

			try:
				zoom = 1.
				if "zoom" in data: 
					zoom		 = float(data["zoom"])
			except:pass


			try:
				intensity = 1.
				if "intenstity" in data: 
					intenstity		 = float(data["intenstity"])/100.
			except:pass
			multIntensity = intensity * intensityDevice * lightSensorValue
					
			resetInitial = ""
			scrollPages, scrollDelay, scrollDelayBetweenPages, scrollxy = getScrollPages(data)

			if "resetInitial" in data: resetInitial= data["resetInitial"]
			if resetInitial	 !=""  or lastScrollxy != scrollxy or str(scrollPages) != str(lastscrollPages) or not imageDefined:
				scrollPages, maxPagesY, maxPagesX, scrollxy, lastScrollxy, lastscrollPages=	 setScrollPages(scrollxy,scrollPages)
				
				if devType.lower() in ["sh1106","ssd1306"]:
					imData= Image.new('1',	 (xmax*maxPagesX, ymax*maxPagesY))
					draw =ImageDraw.Draw(imData)
					draw.rectangle( (0,0, xmax*maxPagesX, ymax*maxPagesY), outline=0, fill=checkRGBcolor(resetInitial,0,RGBtype=1) )
					outputDev.display(imData)

				elif devType.lower() in ["ssd1351"]:
					imData= Image.new('RGB', (xmax*maxPagesX, ymax*maxPagesY))
					draw =ImageDraw.Draw(imData)
					draw.rectangle((0,0, xmax*maxPagesX, ymax*maxPagesY), outline=0, fill= checkRGBcolor(resetInitial,(0,0,0)) )
					outputDev = SSD1351(PIN_DC, PIN_RST, PIN_CS,PIN_CE)
					outputDev.EnableDisplay(True)

				elif devType.lower() in ["st7735"]:
					imData= Image.new('RGB', (xmax*maxPagesX, ymax*maxPagesY))
					draw =ImageDraw.Draw(imData)
					draw.rectangle((0,0, xmax*maxPagesX, ymax*maxPagesY), outline=0, fill= checkRGBcolor(resetInitial,(0,0,0)) )
					outputDev = st7735(PIN_DC, PIN_RST, PIN_CS,PIN_CE)
					outputDev.EnableDisplay(True)

				elif devType.lower().find("rgbmatrix")> -1: 
					imData= Image.new('RGB', (xmax*maxPagesX, ymax*maxPagesY))
					draw =ImageDraw.Draw(imData)
					draw.rectangle((0,0, xmax*maxPagesX, ymax*maxPagesY), outline=0, fill= checkRGBcolor(resetInitial,(0,0,0)) )
					matrix.Fill(0,0,0) 
					matrix.Clear()

				#elif devType.lower().find("screen")> -1: 
				#	imData= Image.new('RGB', (xmax*maxPagesX, ymax*maxPagesY))
				#	draw =ImageDraw.Draw(imData)
				#	draw.rectangle((0,0, xmax*maxPagesX, ymax*maxPagesY), outline=0, fill= checkRGBcolor(resetInitial,(0,0,0)) )
				elif devType.lower().find("lcd1602")> -1: 
					outputDev.write(0, 0, '				   ')
					outputDev.write(0, 1, '				   ')
					TextPosForLCD		= [0,0]
					TextForLCD			= [" "," "]
					maxPages			= 1

			xwindowSize =[0,0]
			xwindows    ="off"
			if devType.lower().find("screen")> -1: 
				if "xwindows" in data: xwindows = data["xwindows"].lower()
				if "xwindowSize" in data: 
					try:
						try: xwindowSize = json.loads(data["xwindowSize"])
						except:
							xwindowSize = (data["xwindowSize"]).split(",")
							xwindowSize  = [int(xwindowSize[0]), int(xwindowSize[1])]
					except: pass
				U.logger.log(10, "=== 0 start new disp dev: = sizes:{} {}".format(xwindowSize, xwindows)  )
				if 	xwindowSize != [0,0] and xwindows =="on":
 					U.logger.log(10, "=== 1 start new disp dev")

				if resetInitial  !=""  or lastScrollxy != scrollxy or str(scrollPages) != str(lastscrollPages) or not imageDefined or (
					(xwindowSize != [0,0] and (xwindowSize[0] != xmax or xwindowSize[1] != ymax) ) ):
					scrollPages, maxPagesY, maxPagesX, scrollxy, lastScrollxy, lastscrollPages=	 setScrollPages(scrollxy,scrollPages)
					if xwindows == "on" :
						if int(xwindowSize[0]) != xmax or int(xwindowSize[1]) != ymax:
							U.logger.log(20, "=== 3 start new disp dev: = size:{};   old  x:{}; y:{}".format(xwindowSize, xmax, ymax))
							fontDir,xmin,xmax,ymin,ymax,matrix,outputDev = updateDevice(outputDev, matrix, overwriteXmax=xwindowSize[0] , overwriteYmax=xwindowSize[1], reset = "reset" )
							U.logger.log(20, "=== 3 start new disp dev: = sizes:{}; {}".format(xmax, ymax))

					U.logger.log(10, "=== starting image ===")
					imData= Image.new('RGB', (xmax*maxPagesX, ymax*maxPagesY))
					draw =ImageDraw.Draw(imData)
					draw.rectangle((0,0, xmax*maxPagesX, ymax*maxPagesY), outline=0, fill= checkRGBcolor(resetInitial,(0,0,0)) )

				imageDefined=True

	
			repeat=1
			try:
				if "repeat" in data: repeat		 = int(data["repeat"])
			except:
				pass

			if "startAtDateTime" in data:
				try:
					startAtDateTime =  float(data["startAtDateTime"]) -time.time()
					if startAtDateTime > 0:
						time.sleep(startAtDateTime)
				except:
					pass

			
							
	
			nnxx =0
			startRepeatTime = int(time.time())	   
			while nnxx < repeat:
				nnxx+=1
				if "command" not in data: break 
				loopCount+=1
				ncmds = len(data["command"])
				npage=-1
				waited =False
				checkLightSensor()
				U.logger.log(10, "item:"+item )
				for cmd in data["command"]:
					try:
						if os.path.isfile(G.homeDir+"temp/rebooting.now"): break
						
						U.logger.log(10, "{}".format(cmd) )
						if "type" not in cmd: continue
						cType = cmd["type"]
						if cType == "" or cType == "0":	 continue
			
						fill = 255
						if devType.lower().find("rgbmatrix")> -1 or devType.lower() in ["ssd1351","st7735"]:   
							fill=(int(100.*multIntensity),int(100.*multIntensity),int(100.*multIntensity))

						if "fill" in cmd: 
							fill = cmd["fill"]
						fill = getFill(devType,fill)
						
						reset =""
						if "reset" in cmd:
							reset =cmd["reset"]

						if loopCount%100000 ==0:
							#print " resetting due to loopcount",loopCount
							if devType.lower() in ["ssd1351"]:
								outputDev = SSD1351(PIN_DC, PIN_RST, PIN_CS,PIN_CE)
								#outputDev.EnableDisplay(False)
								outputDev.EnableDisplay(True)

						if "display" not in cmd or cmd["display"] != "wait": 
							delayStart=0
							if "delayStart" in cmd:
								try: 
									delayStart = float(cmd["delayStart"])
									time.sleep(delayStart)
								except: pass
								


						onTime	 = 9999999999999
						offTime0 = 0
						offTime1 = 0
						if "offONTime" in cmd:
							try:
								offTime0 = int(float(cmd["offONTime"][0]))
								onTime	 = int(float(cmd["offONTime"][1]))
								offTime1 = int(float(cmd["offONTime"][2]))
							except:
								onTime	 = 9999999999999
								offTime0 = 0
								offTime1 = 0
						
						
						if reset!="" : 
							npage = -1

							if devType in ["sh1106","ssd1306"]:
								imData= Image.new('1', (xmax*maxPagesX, ymax))
								draw = ImageDraw.Draw(imData)
								draw.rectangle((0,0, xmax, ymax), outline=0, fill=int(reset))

							elif devType.lower() in ["ssd1351"]:
								imData= Image.new('RGB', (xmax*maxPagesX, ymax*maxPagesY))
								draw = ImageDraw.Draw(imData)
								rr = checkRGBcolor(str(reset),(0,0,0))
								draw.rectangle((0,0, xmax*maxPagesX, ymax*maxPagesY), outline=0, fill=rr)
								outputDev.restart0()
								outputDev.EnableDisplay(True)

							elif devType.lower() in ["st7735"]:
								imData= Image.new('RGB', (xmax*maxPagesX, ymax*maxPagesY))
								draw = ImageDraw.Draw(imData)
								rr = checkRGBcolor(str(reset),(0,0,0))
								draw.rectangle((0,0, xmax*maxPagesX, ymax*maxPagesY), outline=0, fill=rr)
								#outputDev.restart0()
								#outputDev.EnableDisplay(True)

							
							elif devType.lower().find("rgbmatrix")> -1: 
								imData= Image.new('RGB', (xmax*maxPagesX, ymax*maxPagesY))
								draw = ImageDraw.Draw(imData)
								rr = checkRGBcolor(str(reset),(0,0,0))
								draw.rectangle((0,0, xmax*maxPagesX, ymax*maxPagesY), outline=0, fill=rr)
							
							elif devType.lower().find("screen")> -1: 
								imData= Image.new('RGB', (xmax*maxPagesX, ymax*maxPagesY))
								draw = ImageDraw.Draw(imData)
								rr = checkRGBcolor(str(reset),(0,0,0))
								draw.rectangle((0,0, xmax*maxPagesX, ymax*maxPagesY), outline=0, fill=rr)

							elif devType.lower().find("lcd1602")> -1: 
								outputDev.write(0, 0, '				   ')
								outputDev.write(0, 1, '				   ')
								TextPosForLCD	= [0,0]
								TextForLCD		= [" "," "]
								maxPages		= 1

						if cType == "NOP" :
								U.logger.log(10,u"skipping display .. NOP")
								continue

						npage+=1
 
				
						pos=[0,0]
						if "position" in cmd:
							pos = cmd["position"]

						width=0
						if "width" in cmd:
							# handle "", 1, "1", [3,4], "3,4" ,"[3,4]"
							if "," in "{}".format(cmd["width"]):
								try:
									w = "{}".format(cmd["width"]).strip("[").strip("]").split(",")
									width = [zoomit(w[0]),zoomit(w[1])]
								except: 
									width =[1,1]
							else:
								try:	width = int(zoomit(cmd["width"]))
								except: pass

						tti= int(time.time())
						if cType == "text" or cType == "textWformat":  ###########################################################################
							if onDecision(cType,offTime0,onTime,offTime1,startRepeatTime,tti):
								if "text" in cmd and len(cmd["text"]) >0:

									if devType.lower().find("lcd1602")> -1: 
										if pos[1] == 0: 
											TextPosForLCD[0]=int(pos[0])
											TextForLCD[0]	= cmd["text"]
										else:
											TextPosForLCD[1]=int(pos[0])
											TextForLCD[1]	= cmd["text"]
									else:
										fontF =	 mkfont(cmd)
										#U.logger.log(20,u"cType:"+cType+" pos:{}".format(pos) +" text:" + cmd["text"]+" fontF:{}".format(fontF)+" fill:{}".format(fill))
										#U.logger.log(20,u"text pos:{}, zomit:{} ".format(pos,zoomit(pos)) )
										draw.text(zoomit(pos), cmd["text"], font=fontx[fontF], fill=fill)


						elif cType == "dateString":	 ###########################################################################
							if onDecision(cType,offTime0,onTime,offTime1,startRepeatTime,tti):
								U.logger.log(10,u"cType:"+cType+" pos:{}".format(pos) +" width:{}".format(width)+" fill:{}".format(fill))
								theText = datetime.datetime.now().strftime(cmd["text"])
								fontF =	 mkfont(cmd)
								draw.text(zoomit(pos), theText, font=fontx[fontF], fill=fill)


						elif cType == "line":  ###########################################################################
							if onDecision(cType,offTime0,onTime,offTime1,startRepeatTime,tti):
								U.logger.log(10,u"cType:"+cType+" pos:{}".format(pos) +" width:{}".format(width)+" fill:{}".format(fill))
								if type(pos[0]) == type([]) or type(pos[0]) == type(()):
									for xx in pos:
										draw.line(zoomit(xx),fill=fill,width=width)
								else:		
									draw.line(zoomit(pos),fill=fill,width=width)

						elif cType == "dot":  ###########################################################################
							if onDecision(cType,offTime0,onTime,offTime1,startRepeatTime,tti):
								U.logger.log(10,u"cType:"+cType+" pos:{}".format(pos) +" width:{}".format(width)+" fill:{}".format(fill))
								p = zoomit(pos)
								if isinstance(width,int):
									dotWRadius( p[0], p[1],	 fill, width,	 width,	  outline=None)
								else:
									dotWRadius( p[0], p[1],	 fill, width[0], width[1],outline=None)

				
						elif cType == "vBar":  ###########################################################################
							if onDecision(cType,offTime0,onTime,offTime1,startRepeatTime,tti):
								U.logger.log(10,u"cType:"+cType+" pos:{}".format(pos) +" width:{}".format(width)+" fill:{}".format(fill))
								p = zoomit(pos)
								p =[p[0],p[1],p[0],p[1],p+p[2]]
								draw.line(p,fill=fill,width=width)


						elif cType == "hBar":  ###########################################################################
							if onDecision(cType,offTime0,onTime,offTime1,startRepeatTime,tti):
								U.logger.log(10,u"cType:	"+cType+" pos:{}".format(pos) +" width:{}".format(width)+" fill:{}".format(fill))
								#print u"cType:	 "+cType+" pos:{}".format(pos) +" width:{}".format(width)+" fill:{}".format(fill)
								p = zoomit(pos)
								p =[p[0],p[1],p[0]+p[2],p[1]]
								draw.line(p,fill=fill,width=width)


						elif cType == "vBarwBox":  ###########################################################################
							if onDecision(cType,offTime0,onTime,offTime1,startRepeatTime,tti):
								U.logger.log(10,u"cType:"+cType+" pos:{}".format(pos) +" width:{}".format(width)+" fill:{}".format(fill))
								p = zoomit(pos)
								draw.line([p[0]+width/2,p[1]	   ,p[0]+width/2,p[1]+p[3]]	,fill=fill,width=1)
								draw.line([p[0]-width/2,p[1]	   ,p[0]-width/2,p[1]+p[3]]	,fill=fill,width=1)
								draw.line([p[0]-width/2,p[1]+p[3],p[0]+width/2,p[1]+p[3]]	,fill=fill,width=1)
								lastPos = ["vBarwBox",copy.copy(p),width]
								draw.line([p[0],p[1],p[0],p[1]+p[2]],fill=fill,width=width)


						elif cType == "hBarwBox":  ###########################################################################
							if onDecision(cType,offTime0,onTime,offTime1,startRepeatTime,tti):
								U.logger.log(10,u"cType:"+cType+" pos:{}".format(pos) +" width:{}".format(width)+" fill:{}".format(fill))
								p = zoomit(pos)
								draw.line([p[0],		  p[1]-width/2 ,p[0]+p[3] ,p[1]-width/2]   ,fill=fill,width=1)
								draw.line([p[0],		  p[1]+width/2 ,p[0]+p[3] ,p[1]+width/2]   ,fill=fill,width=1)
								draw.line([p[0]+p[3], p[1]-width/2 ,p[0]+p[3] ,p[1]+width/2]   ,fill=fill,width=1)
								lastPos = ["hBarwBox",copy.copy(p),width]
								p =[p[0],p[1],p[0]+p[2],p[1]]
								draw.line(p,fill=fill,width=width)

						elif cType == "labelsForPreviousObject":  ###########################################################################
							if onDecision(cType,offTime0,onTime,offTime1,startRepeatTime,tti):
								U.logger.log(10,u"cType:"+cType+" pos:{}".format(pos) +" width:{}".format(width)+" fill:{}".format(fill))
								if len(lastPos) ==3:
									fontF 		= mkfont(cmd)
									direction 	= lastPos[0]
									frame 		= lastPos[1]
									frameW 		= lastPos[2]
									ll 			= len(frame)
										
									if 	len(pos) ==3:
										lineWidth	= zoomit(pos[1])
										pp 			= pos[2]
										if direction == "vBarwBox":
											if ll >0 and len(pp) >0:
												x0 = int(frame[0]  - frameW/2)
												y0 = frame[1] 
												for tick in pp:
													valueNumber = zoomit(tick[0])
													valueText   = str(tick[1])
													if pos[0].upper() =="R": LR = lineWidth +width
													else:					 LR = -len(valueText)*width*0.6
													line = (x0, y0-valueNumber, x0+frameW, y0-valueNumber)
													draw.line(line ,fill=fill, width=lineWidth)
													if tick[1] !="":
														draw.text([int(x0+LR), int(y0-valueNumber-width/2)], valueText, font=fontx[fontF], fill=fill)
										if direction == "hBarwBox":
											if ll >0 and len(pp) >0:
												y0 = int(frame[3] - frameW/2)
												x0 = frame[0] 
												for tick in pp:
													valueNumber = zoomit(tick[0])
													valueText   = str(tick[1])
													if pos[0].upper() =="T": TB = -width*1.05
													else:					 TB = lineWidth*1.5
													line = (x0-valueNumber, y0 , x0-valueNumber, y0+frameW)
													draw.line(line ,fill=fill, width=lineWidth)
													if tick[1] !="":
														draw.text((int(x0-valueNumber -len(valueText)*width/2), int(y0+TB)), valueText, font=fontx[fontF], fill=fill)


						elif cType == "hist":  ###########################################################################
							if onDecision(cType,offTime0,onTime,offTime1,startRepeatTime,tti):
								U.logger.log(10,u"cType:"+cType+" pos:{}".format(pos) +" fill:{}".format(fill))
								p = zoomit(pos)
								x0= pos[0]
								y0= pos[1]
								ymax = p[2]
								w=	width
								for ii in range(3,len(p)):
									draw.line([x0+w*(ii-3)+(ii-3)*2+2,y0-pos[ii]/2, x0+w*(ii-2)+(ii-3)*2+2,y0-pos[ii]/2]   ,fill=fill,width=pos[ii])
								draw.line([x0,y0, x0+w*(len(pos)-1)+(len(pos)-2)*2,y0]	 ,fill=fill,width=1)
								draw.line([x0,y0, x0,ymax]	 ,fill=fill,width=1)

 
						elif cType == "point":	###########################################################################
							if onDecision(cType,offTime0,onTime,offTime1,startRepeatTime,tti):
								U.logger.log(10,u"cType:"+cType+" pos:{}".format(pos) +" fill:{}".format(fill))
								p = zoomit(pos)
								if isinstance(p[0], list):
									for x in p:
										U.logger.log(10, "{}".format(cmd))
										draw.point(x,fill=fill)
								else:		 
									draw.point(p,fill=fill)


						elif cType == "ellipse":  ###########################################################################
							if onDecision(cType,offTime0,onTime,offTime1,startRepeatTime,tti):
								U.logger.log(10,u"cType:"+cType+" pos:{}".format(pos) +" fill:{}".format(fill))
								draw.ellipse(zoomit(pos),fill=fill)


						elif cType == "rectangle":	###########################################################################
							if onDecision(cType,offTime0,onTime,offTime1,startRepeatTime,tti):
								U.logger.log(10,u"cType:	"+cType+" pos:{}".format(pos) +" fill:{}".format(fill)+" multIntensity:{}".format(multIntensity))
								draw.rectangle(zoomit(pos), fill=fill)


						elif cType == "triangle":  ###########################################################################
							# pos:[x0,y0,length,value], width =wdith, fill = color of thermomether, 
							if onDecision(cType,offTime0,onTime,offTime1,startRepeatTime,tti):
								U.logger.log(10,u"cType:"+cType+" pos:{}".format(pos) +" fill:{}".format(fill))
								p = zoomit(pos)
								draw.polygon( [(p[0], p[1]),(p[2], p[3]),(p[4], p[5])], fill = fill )



					
						elif cType == "image" and "text" in cmd and len(cmd["text"]) >0:  ###########################################################################
							if onDecision(cType,offTime0,onTime,offTime1,startRepeatTime,tti):
								U.logger.log(10,u"cType:"+cType+" pos:{}".format(pos) +" text:" + cmd["text"]+" fill:{}".format(fill))
								imData = Image.open("/home/pi/pibeacon/displayfiles/"+cmd["text"])
								p = zoomit(pos)
								if devType.lower().find("rgbmatrix")== -1 and devType.lower() not in ["ssd1351"]: 
									out = imData.convert("1")
									if fill ==0:
										out = out.convert('L')
										out = PIL.ImageOps.invert(out)
										out = out.convert('1')
									draw.bitmap(p, out,fill=255)
								else:
									imData.load()


						elif cType == "clock" or cType == "date" and onDecision(cType,offTime0,onTime,offTime1,startRepeatTime,tti): ###########################################################################
							dx = 0
							dy = 0
							if scrollxy.lower().find("left")> -1 or scrollxy.lower().find("right")> -1:
								dx = xmax*npage
								dy = 0
							if scrollxy.lower().find("up")> -1 or scrollxy.lower().find("down")> -1:
								dx = 0
								dy = ymax*npage

							nowST = datetime.datetime.now()
							HM	= nowST.strftime("%H:%M")
							sec = nowST.strftime("%S")
							Y	= nowST.strftime("%Y")
							MD	= nowST.strftime("%m-%d")

							if cType == "clock" :  ###########################################################################
								if devType.lower()	== "ssd1351": 
									fontF =	 mkfont({"font":"Arial.ttf","width":"51"})
									draw.text((dx	,dy+35)	 , HM	, font=fontx[fontF], fill=fill)
									
								elif devType.lower()  == "st7735": 
									fontF =	 mkfont({"font":"Arial.ttf","width":"60"})
									draw.text((dx+5	  ,dy+35)  , HM	  , font=fontx[fontF], fill=fill)

								elif devType.lower().find("screen")> -1: 
									ff =250
									try:	ff = int(ff *bigScreenSize[1] / 500) 
									except: pass	
									ddy = int(bigScreenSize[1] /4.)
									fontF =	 mkfont({"font":"Arial.ttf","width":str(ff)})
									draw.text((dx+20   ,dy+ddy)	 , HM	, font=fontx[fontF], fill=fill)

								elif devType.lower()== "rgbmatrix64x32": 
									fontF =	 mkfont({"font":"8x13.pil","width":"0"})
									draw.text((dx,dy+10)	, HM+":"+sec	 , font=fontx[fontF], fill=fill)

								U.logger.log(10,u"cType:"+cType+" fill:{}".format(fill)+" font"+str(fontF)+" at:"+str(dx)+" "+ str(dy))

							elif cType == "date" : ###########################################################################
								if devType.lower()	== "ssd1351": 
									fontF =	 mkfont({"font":"Arial.ttf","width":"51"})
									draw.text((dx,dy)	  , Y	 , font=fontx[fontF], fill=fill)
									draw.text((dx,dy+70)  , MD	  , font=fontx[fontF], fill=fill)

								elif devType.lower()  == "st7735": 
									fontF =	 mkfont({"font":"Arial.ttf","width":"60"})
									draw.text((dx+2,dy)		, Y	   , font=fontx[fontF], fill=fill)
									draw.text((dx+2,dy+68)	, MD	, font=fontx[fontF], fill=fill)

								elif devType.lower().find("screen")> -1: 
									ff =250
									try:	ff = int(ff *bigScreenSize[1] / 500) 
									except: pass	
									ddy = int(bigScreenSize[1] - ff+1.1)
									fontF =	 mkfont({"font":"Arial.ttf","width":str(ff)})
									draw.text((dx+20,dy)	 , Y	, font=fontx[fontF], fill=fill)
									draw.text((dx+20,dy+ddy) , MD	 , font=fontx[fontF], fill=fill)


								elif devType.lower()== "rgbmatrix64x32": 
									fontF =	 mkfont({"font":"9x18B.pil","width":"0"})
									draw.text((dx,dy)	  , Y	 , font=fontx[fontF], fill=fill)
									draw.text((dx,dy+16)  , MD	 , font=fontx[fontF], fill=fill)



						elif cType == "analogClock" and onDecision(cType,offTime0,onTime,offTime1,startRepeatTime,tti)			  : ###########################################################################
								if offTime0 ==0 and	 offTime1 ==0:	 secs = True
								else:								 secs = False
								if True or cmd != analogclockInitialized or newRead:
									analogclockInitialized = copy.copy(cmd)
									analogClockInit(inParms=cmd)
									lastAnalog	   = int(time.time())
								 
								tt= time.time()
								#print "tt - lastAnalog", tt - lastAnalog 
								if os.path.isfile(G.homeDir+"temp/rebooting.now"): break
								if int(tt)	== lastAnalog: 
									time.sleep( 1.02 - (tt - lastAnalog) ) 
								lastAnalog = int(time.time())
								analogClockShow( seconds = secs)

						elif cType == "digitalClock" and onDecision(cType,offTime0,onTime,offTime1,startRepeatTime,tti)			   : ###########################################################################
								if offTime0 ==0 and	 offTime1 ==0:	 secs = True
								else:								 secs = False
								if cmd != digitalclockInitialized or newRead:
									digitalclockInitialized = copy.copy(cmd)
									digitalClockInit(inParms=cmd)
									lastDigital	   = int(time.time())
								 
								tt= time.time()
								#print "tt - lastAnalog", tt - lastAnalog 
								if os.path.isfile(G.homeDir+"temp/rebooting.now"): break
								if int(tt)	== lastDigital: 
									time.sleep( 1.02 - (tt - lastDigital) ) 
								lastDigital = int(time.time())
								digitalClockShow( seconds = secs)



						if "display" not in cmd or cmd["display"] != "wait":  ###########################################################################

							U.logger.log(10, u"displaying  "+ cmd["type"]+ "  scrollxy:"+scrollxy+"  delay:"+str(scrollDelay))
							
							if flipDisplay =="1":
								imData = imData.transpose(PIL.Image.ROTATE_180)

							if devType.lower().find("screen")>-1 :
							
								if scrollPages <=1: # single page no need to map anything		 
									outputDev.sendImage(imData)
									if os.path.isfile(G.homeDir+"temp/rebooting.now"): break
									if scrollDelayBetweenPages >0: time.sleep(scrollDelayBetweenPages)

								else:
									if os.path.isfile(G.homeDir+"temp/rebooting.now"): break
									if scrollxy.lower().find("left")> -1:
										for ii in range(0,xmax*(scrollPages-1),4):
											shifted = imData.crop(box=(ii,0,ii+xmax,ymax))
											outputDev.sendImage(shifted)
											if scrollDelayBetweenPages >0 and (abs(ii)%xmax ==0 or ii==0):time.sleep(scrollDelayBetweenPages)
											time.sleep(scrollDelay)
										if scrollDelayBetweenPages >0: time.sleep(scrollDelayBetweenPages)

									elif scrollxy.lower().find("right")> -1:
										for ii in range(xmax*(scrollPages-1),-1,-4):
											shifted = imData.crop(box=(ii,0,ii+xmax,ymax))
											outputDev.sendImage(shifted)
											if scrollDelayBetweenPages >0 and abs(ii)%xmax ==0: time.sleep(scrollDelayBetweenPages)
											time.sleep(scrollDelay)
										if scrollDelayBetweenPages >0: time.sleep(scrollDelayBetweenPages)

									elif scrollxy.lower().find("down")> -1:
										for ii in range(ymax*(scrollPages-1),-1,-4):
											shifted = imData.crop(box=(0,ii,xmax,ii+ymax))
											outputDev.sendImage(shifted)
											if scrollDelayBetweenPages >0 and abs(ii)%ymax ==0: time.sleep(scrollDelayBetweenPages)
											time.sleep(scrollDelay)
										if scrollDelayBetweenPages >0: time.sleep(scrollDelayBetweenPages)

									elif scrollxy.lower().find("up")> -1:
										for ii in range(0,ymax*(scrollPages-1),4):
											shifted = imData.crop(box=(0,ii,xmax,ii+ymax))
											outputDev.sendImage(shifted)
											if scrollDelayBetweenPages >0 and (abs(ii)%ymax ==0 or ii==0): time.sleep(scrollDelayBetweenPages)
											time.sleep(scrollDelay)
										if scrollDelayBetweenPages >0: time.sleep(scrollDelayBetweenPages)

								
							elif devType.lower() in ["st7735"]:
							
								if scrollPages <=1:
									outputDev.sendImage(RGBto565array(imData,invert=True))
									if scrollDelayBetweenPages >0 : time.sleep(scrollDelayBetweenPages)

								else:
									if scrollxy.lower().find("left")> -1:
										for ii in range(0,xmax*(scrollPages-1),4):
											shifted = imData.crop(box=(ii,0,ii+xmax,ymax))
											outputDev.sendImage(RGBto565array(shifted,invert=True))
											if scrollDelayBetweenPages >0 and (abs(ii)%xmax ==0 or ii==0): time.sleep(scrollDelayBetweenPages)
											time.sleep(scrollDelay)
										if scrollDelayBetweenPages >0: time.sleep(scrollDelayBetweenPages)
										
									elif scrollxy.lower().find("right")> -1:
										for ii in range(xmax*(scrollPages-1),-1,-4):
											shifted = imData.crop(box=(ii,0,ii+xmax,ymax))
											outputDev.sendImage(RGBto565array(shifted,invert=True))
											if scrollDelayBetweenPages >0 and (abs(ii)%xmax ==0):  time.sleep(scrollDelayBetweenPages)
											time.sleep(scrollDelay)
										if scrollDelayBetweenPages >0: time.sleep(scrollDelayBetweenPages)

									elif scrollxy.lower().find("down")> -1:
										for ii in range(ymax*(scrollPages-1),-1,-4):
											shifted = imData.crop(box=(0,ii,xmax,ii+ymax))
											outputDev.sendImage(RGBto565array(shifted,invert=True))
											if scrollDelayBetweenPages >0 and (abs(ii)%ymax ==0): time.sleep(scrollDelayBetweenPages)
											time.sleep(scrollDelay)
										if scrollDelayBetweenPages >0: time.sleep(scrollDelayBetweenPages)

									elif scrollxy.lower().find("up")> -1:
										for ii in range(0,ymax*(scrollPages-1),4):
											shifted = imData.crop(box=(0,ii,xmax,ii+ymax))
											outputDev.sendImage(RGBto565array(shifted,invert=True))
											if scrollDelayBetweenPages >0 and (abs(ii)%ymax ==0 or ii==0) :time.sleep(scrollDelayBetweenPages)
											time.sleep(scrollDelay)
										if scrollDelayBetweenPages >0: time.sleep(scrollDelayBetweenPages)									 
									


							
							elif devType.lower() in ["sh1106","ssd1306"]:
							
								if scrollPages <=1: # single page no need to map anything		 
									outputDev.display(imData)
									if scrollDelayBetweenPages >0: time.sleep(scrollDelayBetweenPages)
									
								else:
									xm2=  xmax
									ym =  ymax
									pix = list(imData.getdata())
									out=np.reshape(np.array(pix),(ym*maxPagesY,xm2*maxPagesX))
									if scrollxy.lower().find("left")> -1:
										for ii in range(0,xm2*(scrollPages-1),4):
											outputDev.display1(out[:,ii:xm2+ii].flatten().tolist())
											if scrollDelayBetweenPages >0 and (abs(ii-1)%xm2 ==0 or ii==0):time.sleep(scrollDelayBetweenPages)
											time.sleep(scrollDelay)
										if scrollDelayBetweenPages >0: time.sleep(scrollDelayBetweenPages)

									elif scrollxy.lower().find("right")> -1:
										for ii in range(xm2*(scrollPages-1),-1,-4):
											outputDev.display1(out[:,ii:xm2+ii].flatten().tolist())
											if scrollDelayBetweenPages >0 and abs(ii)%xm2 ==0: time.sleep(scrollDelayBetweenPages)
											time.sleep(scrollDelay)
										if scrollDelayBetweenPages >0: time.sleep(scrollDelayBetweenPages)

									elif scrollxy.lower().find("down")> -1:
										for ii in range(ym*(scrollPages-1),-1,-4):
											outputDev.display1(out[ii:ym+ii,:].flatten().tolist())
											if scrollDelayBetweenPages >0 and abs(ii)%ym ==0: time.sleep(scrollDelayBetweenPages)
											time.sleep(scrollDelay)
										if scrollDelayBetweenPages >0: time.sleep(scrollDelayBetweenPages)

									elif scrollxy.lower().find("up")> -1:
										for ii in range(0,ym*(scrollPages-1),4):
											outputDev.display1(out[ii:ym+ii,:].flatten().tolist())
											if scrollDelayBetweenPages >0 and (abs(ii)%ym ==0 or ii==0): time.sleep(scrollDelayBetweenPages)
											time.sleep(scrollDelay)
										if scrollDelayBetweenPages >0: time.sleep(scrollDelayBetweenPages)



							elif devType.lower() in ["ssd1351"]:
							   
								out1 = RGBto565array(imData)

								if scrollPages <=1: # single page no need to map anything		 
									outputDev.sendImage(out1)
									if scrollDelayBetweenPages >0: time.sleep(scrollDelayBetweenPages)

								else: # single page no need to map anything			
									xm2= 2*xmax
									ym =   ymax
									out=np.reshape(np.array(out1),(ym*maxPagesY,xm2*maxPagesX))
									#print "dim:", out.shape
									if scrollxy.lower().find("left")> -1:
										for ii in range(0,xm2*(scrollPages-1),4):
											outputDev.sendImage(out[:,ii:xm2+ii].flatten().tolist())
											if scrollDelayBetweenPages >0 and (abs(ii)%xm2 ==0 or ii==0): time.sleep(scrollDelayBetweenPages)
											time.sleep(scrollDelay)
										if scrollDelayBetweenPages >0 : time.sleep(scrollDelayBetweenPages)
										
									elif scrollxy.lower().find("right")> -1:
										for ii in range(xm2*(scrollPages-1),-1,-4):
											outputDev.sendImage(out[:,ii:xm2+ii].flatten().tolist())
											if scrollDelayBetweenPages >0 and abs(ii)%xm2 ==0:	time.sleep(scrollDelayBetweenPages)
											time.sleep(scrollDelay)
										if scrollDelayBetweenPages >0: time.sleep(scrollDelayBetweenPages)

									elif scrollxy.lower().find("down")> -1:
										for ii in range(ym*(scrollPages-1),-1,-4):
											outputDev.sendImage(out[ii:ym+ii,:].flatten().tolist())
											if scrollDelayBetweenPages >0 and abs(ii)%ym ==0: time.sleep(scrollDelayBetweenPages)
											time.sleep(scrollDelay)
										if scrollDelayBetweenPages >0: time.sleep(scrollDelayBetweenPages)

									elif scrollxy.lower().find("up")> -1:
										for ii in range(0,ym*(scrollPages-1),4):
											outputDev.sendImage(out[ii:ym+ii,:].flatten().tolist())
											if scrollDelayBetweenPages >0 and (abs(ii)%ym ==0  or ii==0):time.sleep(scrollDelayBetweenPages)
											time.sleep(scrollDelay)
										if scrollDelayBetweenPages >0: time.sleep(scrollDelayBetweenPages)


							elif devType.lower().find("rgbmatrix")> -1:

								if scrollPages <=1: # single page no need to map anything		 
									matrix.SetImage(imData.im.id,0,0)
									if scrollDelayBetweenPages >0: time.sleep(scrollDelayBetweenPages)

								else:
									if scrollxy.lower().find("right")> -1:
										for ii in range(-xmax*(scrollPages-1),0,1):
											matrix.SetImage(imData.im.id,ii,0) # (imagematrix,x,y)
											if scrollDelayBetweenPages >0 and (abs(ii)%xmax ==0 ): time.sleep(scrollDelayBetweenPages)
											time.sleep(scrollDelay)
										if scrollDelayBetweenPages >0: time.sleep(scrollDelayBetweenPages)
										##matrix.fill(0,0,0)	   
											
									elif scrollxy.lower().find("left")> -1:
										for ii in range(0,-xmax*(scrollPages-1),-1):
											matrix.SetImage(imData.im.id,ii,0) # (imagematrix,x,y)
											if scrollDelayBetweenPages >0 and (abs(ii)%xmax ==0 or ii==0): time.sleep(scrollDelayBetweenPages)
											time.sleep(scrollDelay)
										if scrollDelayBetweenPages >0: time.sleep(scrollDelayBetweenPages)
											
									elif scrollxy.lower().find("down")> -1:
										for ii in range(-ymax*(scrollPages-1),0,1):
											matrix.SetImage(imData.im.id,0,ii) # (imagematrix,x,y)
											if scrollDelayBetweenPages >0 and abs(ii)%ymax ==0: time.sleep(scrollDelayBetweenPages)
											time.sleep(scrollDelay)
										if scrollDelayBetweenPages >0: time.sleep(scrollDelayBetweenPages)

									elif scrollxy.lower().find("up")> -1:
										for ii in range(0,-ymax*(scrollPages-1),-1):
											matrix.SetImage(imData.im.id,0,ii) # (imagematrix,x,y)
											if scrollDelayBetweenPages >0 and (abs(ii)%ymax ==0 or ii==0): time.sleep(scrollDelayBetweenPages)
											time.sleep(scrollDelay)
										if scrollDelayBetweenPages >0: time.sleep(scrollDelayBetweenPages)

							elif devType.lower().find("lcd1602")> -1:
								outputDev.write(TextPosForLCD[0],0, TextForLCD[0])
								outputDev.write(TextPosForLCD[1],1, TextForLCD[1])

							waited = True
							
						tt= time.time()
						if tt - lastAlive > 29.:  
							lastAlive =tt
							subprocess.call("echo	 "+str(tt)+" > "+G.homeDir+"temp/alive.display", shell=True)

						if os.path.isfile(G.homeDir+"temp/rebooting.now"): break
						if os.path.isfile(G.homeDir+"temp/display.inp"): break
					except	Exception as e:
						try:
							U.logger.log(30,"", exc_info=True)
							U.logger.log(30, "{}".format(cmd))
						except: # hard delete logfiles
							subprocess.call("sudo  chown -R pi:pi /var/log/*", shell=True)
							subprocess.call("sudo echo "" >  /var/log/pibeacon.log", shell=True)

				newRead = False
				if os.path.isfile(G.homeDir+"temp/display.inp"): break
				if os.path.isfile(G.homeDir+"temp/rebooting.now"): break

		time.sleep(0.1) 
		items=[]
		try:
			if os.path.isfile(G.homeDir+"temp/rebooting.now"):
				try: outputDev.delPy()
				except: pass
				klillMyselfTimeout = -1 # killing myself..
				U.logger.log(30, " exiting - stop was requested ") 	
				os.kill(os.getpid(), signal.SIGTERM)
				runLoop = False
				break

			if os.path.isfile(G.homeDir+"temp/display.inp") :
				readParams()
				i2cAddress = U.getI2cAddress(data, default ="")
				if i2cAddress != lasti2cAddress:
					lasti2cAddress = i2cAddress

				f = open(G.homeDir+"temp/display.inp","r")
				xxx= f.read().strip("\n") 
				items = xxx.split("\n")
				f.close()
				os.remove(G.homeDir+"temp/display.inp")
				#U.logger.log(20, " read new inputfile items:{}...".format(str(items)[0:100])) 	
				if xxx == "stop":
					try: outputDev.delPy()
					except: pass
					klillMyselfTimeout = -1 # killing myself..
					U.logger.log(30, " exiting - stop was requested ") 	
					os.kill(os.getpid(), signal.SIGTERM)
					runLoop = False
					break

				newRead = True
		except:	 
			items = []
			try:
				os.remove(G.homeDir+"temp/display.inp")
			except:
				pass
				
		if loop %20 ==0:
			U.echoLastAlive(G.program)
		loop +=1 

	except	Exception as e:
		U.logger.log(30,"", exc_info=True)
		items=[]

U.logger.log(30, " exiting display end of loop") 	
sys.exit(0)		   
