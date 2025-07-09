#!/usr/bin/env python
# -*- coding: utf-8 -*-
#
## py prept, but _rpi_ws281x  not available as py3 

import sys
import os 
import time
import subprocess
import copy
import datetime
import json


sys.path.append(os.getcwd())
import	piBeaconUtils	as U
import	piBeaconGlobals as G

G.program = "neopixel2"
import math
import atexit
import colorsys
from neopix2 import _rpi_ws281x as ws # this has to come after the path extension




# Adafruit NeoPixel library port to the rpi_ws281x library.
# Author: Tony DiCola (tony@tonydicola.com), Jeremy Garff (jer@jers.net)

def Color(red, green, blue):
	"""Convert the provided red, green, blue color to a 24-bit color value.
	Each color component should be a value 0-255 where 0 is the lowest intensity
	and 255 is the highest intensity.
	"""
	return (red << 16) | (green << 8) | blue
def applyIntensity(c):
	global intensity, multIntensity
	global lightMinDimForDisplay, lightMaxDimForDisplay
	ret = [0,0,0]
	try:
		for ii in range(3):	
			r = c[ii] * intensity * multIntensity
			r = int( min(r , lightMaxDimForDisplay) )
			if c[ii] > 0:  r = int( max( r, lightMinDimForDisplay) )
			ret[ii] = r
		#U.logger.log(20, u"applyIntensity c: {}; ret: {};   {};   {};   {};   {}".format(c, ret, intensity, multIntensity, lightMaxDimForDisplay, lightMinDimForDisplay))
		return ret
	except Exception as e:
		U.logger.log(30,"", exc_info=True)
		U.logger.log(30, u"c: {}; int: {}; intmult: {}".format(c, intensity, multIntensity ))
		return ret


class _LED_Data(object):
	"""Wrapper class which makes a SWIG LED color data array look and feel like
	a Python list of integers.
	"""
	def __init__(self, channel, size):
		self.size = size
		self.channel = channel

	def __getitem__(self, pos):
		"""Return the 24-bit RGB color value at the provided position or slice
		of positions.
		"""
		# Handle if a slice of positions are passed in by grabbing all the values
		# and returning them in a list.
		if isinstance(pos, slice):
			return [ws.ws2811_led_get(self.channel, n) for n in range(pos.indices(self.size))]
		# Else assume the passed in value is a number to the position.
		else:
			return ws.ws2811_led_get(self.channel, pos)

	def __setitem__(self, pos, value):
		"""Set the 24-bit RGB color value at the provided position or slice of
		positions.
		"""
		# Handle if a slice of positions are passed in by setting the appropriate
		# LED data values to the provided values.
		if isinstance(pos, slice):
			index = 0
			for n in range(pos.indices(self.size)):
				ws.ws2811_led_set(self.channel, n, value[index])
				index += 1
		# Else assume the passed in value is a number to the position.
		else:
			return ws.ws2811_led_set(self.channel, pos, value)


class Adafruit_NeoPixel(object):
	def __init__(self, num, pin, freq_hz=800000, dma=5, invert=False, brightness=128, channel=0):
		"""Class to represent a NeoPixel/WS281x LED display.  Num should be the
		number of pixels in the display, and pin should be the GPIO pin connected
		to the display signal line (must be a PWM pin like 18!).  Optional
		parameters are freq, the frequency of the display signal in hertz (default
		800khz), dma, the DMA channel to use (default 5), invert, a boolean
		specifying if the signal line should be inverted (default False), and
		channel, the PWM channel to use (defaults to 0).
		"""
		# Create ws2811_t structure and fill in parameters.
		self._leds = ws.new_ws2811_t()

		# Initialize the channels to zero
		for channum in range(2):
			chan = ws.ws2811_channel_get(self._leds, channum)
			ws.ws2811_channel_t_count_set(chan, 0)
			ws.ws2811_channel_t_gpionum_set(chan, 0)
			ws.ws2811_channel_t_invert_set(chan, 0)
			ws.ws2811_channel_t_brightness_set(chan, 0)

		# Initialize the channel in use
		self._channel = ws.ws2811_channel_get(self._leds, channel)
		ws.ws2811_channel_t_count_set(self._channel, num)
		ws.ws2811_channel_t_gpionum_set(self._channel, pin)
		ws.ws2811_channel_t_invert_set(self._channel, 0 if not invert else 1)
		ws.ws2811_channel_t_brightness_set(self._channel, brightness)
		ws.ws2811_channel_t_strip_type_set(self._channel, ws.WS2811_STRIP_GRB)

		# Initialize the controller
		ws.ws2811_t_freq_set(self._leds, freq_hz)
		ws.ws2811_t_dmanum_set(self._leds, dma)

		# Grab the led data array.
		self._led_data = _LED_Data(self._channel, num)
		
		# Substitute for __del__, traps an exit condition and cleans up properly
		atexit.register(self._cleanup)


	def __del__(self):
		# Required because Python will complain about memory leaks
		# However there's no guarantee that "ws" will even be set 
		# when the __del__ method for this class is reached.
		if ws is not None:
			self._cleanup()

	def _cleanup(self):
		# Clean up memory used by the library when not needed anymore.
		if self._leds is not None:
			print("Exiting cleanly")
			ws.ws2811_fini(self._leds)
			ws.delete_ws2811_t(self._leds)
			self._leds = None
			self._channel = None
			# Note that ws2811_fini will free the memory used by led_data internally.

	def begin(self):
		"""Initialize library, must be called once before other functions are
		called.
		"""
		resp = ws.ws2811_init(self._leds)
		if resp != 0:
			raise RuntimeError('ws2811_init failed with code {}'.format(resp))
		
	def show(self):
		#print "Update the display with the data from the LED buffer."
		resp = ws.ws2811_render(self._leds)
		if resp != 0:
			raise RuntimeError('ws2811_render failed with code {0}'.format(resp))
		#print "Update the display with the data from the LED buffer. ... DONE"
		

	def setPixelColor(self, n, color):
		"""Set LED at position n to the provided 24-bit color value (in RGB order).
		"""
		self._led_data[n] = color

	def setPixelColorRGB(self, n, red, green, blue):
		"""Set LED at position n to the provided red, green, and blue color.
		Each color component should be a value from 0 to 255 (where 0 is the
		lowest intensity and 255 is the highest intensity).
		"""
		self.setPixelColor(n, Color(red, green, blue))

	def setPixelColorRGBlist(self, n, colors):
		"""Set LED at position n to the provided red, green, and blue color.
		Each color component should be a value from 0 to 255 (where 0 is the
		lowest intensity and 255 is the highest intensity).
		"""
		self.setPixelColor(n, Color(colors[0],colors[1],colors[2]))


	def getBrightness(self):
		return ws.ws2811_channel_t_brightness_get(self._channel)

	def setBrightness(self, brightness):
		"""Scale each LED in the buffer by the provided brightness.	 A brightness
		of 0 is the darkest and 255 is the brightest.
		"""
		ws.ws2811_channel_t_brightness_set(self._channel, brightness)

	def getPixels(self):
		"""Return an object which allows access to the LED display data as if 
		it were a sequence of 24-bit RGB values.
		"""
		return self._led_data

	def numPixels(self):
		"""Return the number of pixels in the display."""
		return ws.ws2811_channel_t_count_get(self._channel)

	def getPixelColor(self, n):
		"""Get the 24-bit RGB color value for the LED at position n."""
		return self._led_data[n]

	def getPixelColorRGB(self, n):
		c = lambda: None
		setattr(c, 'r', self._led_data[n] >> 16 & 0xff)
		setattr(c, 'g', self._led_data[n] >> 8	& 0xff)	   
		setattr(c, 'b', self._led_data[n]	 & 0xff)
		return c




def get_shape():
	"""Returns the shape (width, height) of the display"""
	global MAP

	return (len(MAP), len(MAP[0]))

def _clean_shutdown():
	"""Registered at exit to ensure ws2812 cleans up after itself
	and all pixels are turned off.
	"""
	off()



def brightness(b=0.2):
	"""Set the display brightness between 0.0 and 1.0

	0.2 is highly recommended, UnicornHat can get painfully bright!

	:param b: Brightness from 0.0 to 1.0 (default 0.2)
	"""

	if b > 1 or b < 0:
		raise ValueError('Brightness must be between 0.0 and 1.0')

	"""Absolute max brightness has been capped to 50%, do not change
	this unless you know what you're doing.
	UnicornHAT draws too much current above 50%."""
	brightness = int(b*128.0)
	if brightness < 30:
		print("Warning: Low brightness chosen, your UnicornHAT might not light up!")
	ws2812.setBrightness(brightness)


def get_brightness():
	"""Get the display brightness value

	Returns a float between 0.0 and 1.0
	"""
	return round(ws2812.getBrightness()/128.0, 3)


def clear():
	global LED_COUNT
	"""Clear the buffer"""
	for x in range(LED_COUNT):
		ws2812.setPixelColorRGB(x, 0, 0, 0)


def off():
	"""Clear the buffer and immediately update UnicornHat

	Turns off all pixels."""
	clear()
	show()


def get_index_from_xy(x, y):
	global flipDisplay, height,width, LED_COUNT
	"""Convert an x, y value to an index on the display

	:param x: Horizontal position from 0 to 7
	:param y: Vertical position from 0 to 7
	"""
	wx = len(MAP[0]) - 1
	wy = len(MAP) - 1


	if flipDisplay !=0:
		y = (wy)-y

		if flipDisplay == 90 and wx == wy:
			x, y = y, (wx)-x
		elif flipDisplay == 180:
			x, y = (wx)-x, (wy)-y
		elif flipDisplay == 270 and wx == wy:
			x, y = (wy)-y, x

	try:
		index = MAP[y][x]
	except IndexError:
		index = LED_COUNT-1
		
	return index


def set_pixel_hsv(x, y, h, s, v):
	"""Set a single pixel to a colour using HSV

	:param x: Horizontal position from 0 to 7
	:param y: Veritcal position from 0 to 7
	:param h: Hue from 0.0 to 1.0 ( IE: degrees around hue wheel/360.0 )
	:param s: Saturation from 0.0 to 1.0
	:param v: Value (also known as brightness) from 0.0 to 1.0
	"""
	index = get_index_from_xy(x, y)
	if index is not None:
		r, g, b = [int(n*255) for n in colorsys.hsv_to_rgb(h, s, v)]
		ws2812.setPixelColorRGB(index, r, g, b)


def set_pixel(x, y, r, g, b):
	try:
		"""Set a single pixel to RGB colour

		:param x: Horizontal position from 0 to 7
		:param y: Veritcal position from 0 to 7
		:param r: Amount of red from 0 to 255
		:param g: Amount of green from 0 to 255
		:param b: Amount of blue from 0 to 255
		"""
		index = get_index_from_xy(x, y)
		if index is not None:
			ws2812.setPixelColorRGB(index, r, g, b)
	except Exception as e:
			U.logger.log(30,"", exc_info=True)

def get_pixel(x, y):
	"""Get the RGB value of a single pixel

	:param x: Horizontal position from 0 to 7
	:param y: Veritcal position from 0 to 7"""
	index = get_index_from_xy(x, y)
	if index is not None:
		pixel = ws2812.getPixelColorRGB(index)
		return int(pixel.r), int(pixel.g), int(pixel.b)
	return 0,0,0

def set_all(r, g, b):
	"""Set all pixels to a specific colour"""
	shade_pixels(lambda x, y: (r, g, b))


def shade_pixels(shader):
	"""Set all pixels using a pixel shader style function

	:param pixels: A function which accepts the x and y positions of a pixel and returns values r, g and b

	For example, this would be synonymous to clear::

		set_pixels(lambda x, y: return 0,0,0)

	Or perhaps we want to map red along the horizontal axis, and blue along the vertical::

		set_pixels(lambda x, y: return (x/7.0) * 255, 0, (y/7.0) * 255)
	"""
	
	width, height = get_shape()
	for x in range(width):
		for y in range(height):
			r, g, b = shader(x, y)
			set_pixel(x, y, r, g, b)


def set_pixels(pixels):
	"""Set all pixels using an array of `get_shape()`"""

	shade_pixels(lambda x, y: pixels[y][x])


def get_pixels():
	"""Get the RGB value of all pixels in a 7x7x3 2d array of tuples"""
	width, height = get_shape()
	return [[get_pixel(x, y) for x in range(width)] for y in range(height)]





def makeMAP(devType, OrderOfMatrix="lrlr"):
	#
	"""
	Store a map of pixel indexes for
	translating x, y coordinates.
	"""
	h,w=devType.split("x")
	w=int(w)
	h=int(h)
 
	if	devType =="8x4":   
		mm=	 [
			[24, 16, 8,	 0],
			[25, 17, 9,	 1],
			[26, 18, 10, 2],
			[27, 19, 11, 3],
			[28, 20, 12, 4],
			[29, 21, 13, 5],
			[30, 22, 14, 6],
			[31, 23, 15, 7]	 ]
	else: 
		if h ==1: 
			mm =  [[ ii	 for ii in range(w) ] ]
		else:
			mm=[]
			for k in range(h):
				if k%2 ==1 and OrderOfMatrix == "lrlr": # strip of led are in order: = left to right; left to right === other is left to right; right to left 
					mm.append([ w-ii-1+(k)*w  for ii in range(w) ] )
				else:
					mm.append([ ii+(k)*w  for ii in range(w) ] )
	linMap =[nn for nn in range(w*h)]
	#for ii in range(len(mm)):
	#	 for kk in range(len(mm[0])):
	#		 linMap.append(mm[ii][kk])
	##print OrderOfMatrix, mm, linMap
	return mm, linMap

#=============================



class draw():

	def __init__(self, GPIOpin = 18,nx=8,ny=8):
		
		self.maxX  = nx
		self.maxY  = ny
		self.maxX1 = nx-1
		self.maxY1 = ny-1
		self.pin= GPIOpin
		self.resetImage()

	def resetImage(self,RGB=[0,0,0]):
		
		#self.PIXELS =[]
		#print " resetting image to :", RGB
		self.PIXELS=[[applyIntensity(RGB) for x in range(self.maxX)] for y in range(self.maxY)]
		#print " pixels:", self.PIXELS

	def rectangle(self,pos):
		global intensity
		xleft  = pos[0]
		yleft  = pos[1]
		xright = pos[2]
		yright = pos[3]
		for x in range( max(0,min(self.maxX,xleft)),  max(0,min(self.maxX,xright+1)) ):
			for y in range( max(0,min(self.maxY,yleft)),max(0,min(self.maxY,yright+1)) ):
				self.PIXELS[y][x]=applyIntensity(pos[4:7])
		return
		
	def line(self,pos):
		try:
			sx = 1
			sy = 1
			xStart = pos[1]
			xEnd   = pos[3]
			yStart = pos[0]
			yEnd   = pos[2]
			if pos[3]-pos[1]< 0: 
				sx =-1
				xStart = pos[3]
				xEnd   = pos[1]
			if pos[2]-pos[0]< 0: 
				sy =-1
				
			if xStart == xEnd:	  
				for y in range(yStart,yEnd+sy,sy):
					self.PIXELS[y][pos[1]]=applyIntensity(pos[4:7])
				return
					
			m = float(pos[2]-pos[0])/(pos[3]-pos[1])
			b =	 -m*pos[1] + pos[0]
			for x in range(max(0,min(self.maxX,xStart)),max(0,min(self.maxX,xEnd+1))):
					y = int(x * m + b)
					self.PIXELS[max(0,min(self.maxY1,y))][x]=applyIntensity(pos[4:7])
			return
		except Exception as e:
			U.logger.log(30,"", exc_info=True)
			U.logger.log(30, u"pos {}".format(pos))

		
	def sLine(self, pos):
		try:
			xStart = pos[0]
			xEnd   = pos[1]
			for x in range(max(0,min(self.maxX,xStart)),max(0,min(self.maxX,xEnd+1))):
				self.PIXELS[0][x] = applyIntensity(pos[-3:])
			#U.logger.log(30, u"draw line from {} to {}, w color:{}".format(xStart,xEnd, pos[-3:]))
			return
		except Exception as e:
			U.logger.log(30,"", exc_info=True)
			U.logger.log(30, u"pos {}".format(pos))



	def point(self,pos):
		try:
			self.PIXELS[max(0,min(self.maxY1,pos[0]))][max(0,min(self.maxX1,pos[1]))] =applyIntensity(pos[2:5])
		except Exception as e:
			U.logger.log(30,"", exc_info=True)
			U.logger.log(30, u"pos {}".format(pos))
		return 

	def pixelImage(self,pos,pixs):
		
		xstart = pos[1]
		ystart = pos[2]
		xN = len(pixs[0])
		yN = len(pixs)
		xi= 0
		for x in range( max(0,min(self.maxX1,xstart)) ,max(0,min(self.maxX1,xN)) ):
			yi=0
			for y in range( max(0,min(self.maxY1,ystart)),max(0,min(self.maxY1,yN)) ):
				self.PIXELS[max(0,min(self.maxY1,y))][max(0,min(self.maxX1,x))]=applyIntensity(pixs[yi,xi])
				yi+=1
			xi+=1
		return


	def matrix(self,pos):
		if isinstance(pos[0], list):
			for y in range(len(pos)):
				for x in range(len(pos[0])):
					self.PIXELS[max(0,min(self.maxY1,y))][max(0,min(self.maxX1,x))] = applyIntensity(pos[y][x])
		else:		 
			U.logger.log(30,u" error type:"+cType+" pos:{}".format(pos) )
		return
		
	def points(self,pos):
		try:
			ppp = "{}".format(pos)
			if ppp.find("*") >-1:  # get rgb values = last three numbers in eg [["*","*",3,4,5]] or ["*","*",3,4,5]
				ppp = ppp.replace("[","").replace("]","").replace(" ","").split(",")
				if len(ppp)>3:
					ppp = [int(ppp[-3]),int(ppp[-2]),int(ppp[-1])]
					for y in range(self.maxY):
						for x in range(self.maxX):
							self.PIXELS[y][x]= applyIntensity(ppp)
				return 
			if isinstance(pos[0], list):
				for kk in range(len(pos)):
					y= pos[kk][0]
					x= pos[kk][1]
					self.PIXELS[max(0,min(self.maxY1,y))][max(0,min(self.maxX1,x))] = applyIntensity(pos[kk][2:5])
			else:		 
				U.logger.log(30,u" error type:"+cType+" pos:{}".format(pos) )
		except Exception as e:
			U.logger.log(30,"", exc_info=True)


	def rotateCenter(self,phi=math.pi/2.):
		
		temp = copy.copy(self.PIXELS)
		x0 = int(self.maxX/2.)
		y0 = int(self.maxY/2.)
		for xA in range(0,self.maxX):
			x = xA - x0
			newX = x*math.cos(phi)+x0
			for yA in range(0,self.maxY):
				y = yA - y0
				newY = y*math.sin(phi)+y0
				self.PIXELS[newY][newX] = temp[yA,xA]
		return


	def shiftHorizontal(self,dx):
		
		temp = copy.copy(self.PIXELS)
		self.resetImage()
		for xA in range(0,self.maxX):
			x = xA +dx
			if x > (self.maxX-1): continue
			for y in range(0,self.maxY):
				self.PIXELS[y][x] = temp[y,xA]
		return

	def shiftVertical(self,dy):
		
		temp = copy.copy(self.PIXELS)
		self.resetImage()
		for yA in range(0,self.maxY):
			y = yA +dy
			if y > (self.maxY-1): continue
			for x in range(0,self.maxX):
				self.PIXELS[y][x] = temp[yA,x]
		return
		
	def printPIXELS(self, calledFrom=""):
		U.logger.log(10,"pixels "+ calledFrom +" {}".format(len(self.PIXELS))+"  {}".format(self.PIXELS)[0:50]+"	<<<<" )
		return

	def show(self,rotate = 0, rotateSeconds=0,speedOfChange=0):
		global LED_COUNT, linearDATA
		try:
			##print "hello"
			self.printPIXELS(calledFrom="show")
			linearOld = copy.copy(linearDATA) 
			linearDATA =[[0,0,0] for ii in range(LED_COUNT)]
			for y in range(0,self.maxY):
					for x in range(0,self.maxX):
						#if type(self.PIXELS[max(0,min(self.maxY1,y))][max(0,min(self.maxX1,x))][0]) !="int": 
						#	 U.logger.log(30, u"error in show,  RGB not int") 
						#	 continue 
						index = get_index_from_xy(x, y)
						#print x,y,index , self.PIXELS[max(0,min(self.maxY1,y))][max(0,min(self.maxX1,x))]
						#print x,y,index
						if index is not None:
							linearDATA[index] =	 self.PIXELS[y][x]
			if rotate ==0:
				if speedOfChange ==0:
					#U.logger.log(30,"bf show LED_COUNT:{} ; linearDATA:{}".format(LED_COUNT, linearDATA) ) 
					for index in range(LED_COUNT):
						#U.logger.log(30,"index:{} ; linearDATA:{}".format(index, linearDATA[index]) ) 
						ws2812.setPixelColorRGBlist(index,linearDATA[index] )
					ws2812.show() 
				else: 
					steps		= speedOfChange/0.02 +1
					delta		= 1./steps
					value		= 0
					timeStart	= 0
					#print " in show ",steps,speedOfChange,linearDATA, linearOld
					for ii in range(int(steps)):
						for index in range(LED_COUNT):
							red = max(0,min(255,int(  (linearDATA[index][0]- linearOld[index][0])*value+ linearOld[index][0]  )))
							gre = max(0,min(255,int(  (linearDATA[index][1]- linearOld[index][1])*value+ linearOld[index][1]  )))
							blu = max(0,min(255,int(  (linearDATA[index][2]- linearOld[index][2])*value+ linearOld[index][2]  )))
							ws2812.setPixelColorRGB(index,red,gre,blu)
						#print "in loop", delta,steps,value,red,gre,blu
						ws2812.show()
						value	  += delta 
						time.sleep(delta)
						


				return
			
			else:
				revINDEX = copy.copy(linMAP)
				lastCheck1 = time.time()
				lastCheck2 = time.time()
				jj=1
				while jj < abs(rotate):	 #	range does not for for VERY large numebrs
					jj+=1
					if rotate >0:
						revINDEX.insert(0,revINDEX.pop())
					else:
						revINDEX.insert(LED_COUNT,revINDEX.pop(0))
						
					for kk in range(LED_COUNT):
						ws2812.setPixelColorRGBlist(revINDEX[kk], linearDATA[kk])
					ws2812.show() 
					if time.time() - lastCheck1 > 1:
						lastCheck1 = time.time()
						if checkIfnewReboot(): return 
						if checkIfnewInput(): return
						if time.time() - lastCheck2 > 10:
							if readParams() ==1: 
								restartNEOpixel()
								return
							lastCheck2 = time.time()
					time.sleep(rotateSeconds)
				#print " end of loop ", jj 
				
				
		except Exception as e:
			U.logger.log(30,"", exc_info=True)
			U.logger.log(30," pixel len:{}".format(len(self.PIXELS))+"  {}".format(self.PIXELS)[0:100])
			
	def clear(self,RGB):
		global LED_COUNT
		for x in range(LED_COUNT):
			rgb = applyIntensity(RGB)
			ws2812.setPixelColorRGB(x, rgb[0],  rgb[1],  rgb[2] )


def readParams(pgmType=""):
	global devType,	 intensityDevice,flipDisplay, signalPin,OrderOfMatrix, PWMchannel, DMAchannel, frequency
	global astOrderOfMatrix, lastdevType, lastsignalPin, lastintensityDevice, lastPWMchannel, lastDMAchannel,lastfrequency
	global lastlightSensorValue, lastTimeLightSensorValue, lastTimeLightSensorFile, lightSensorValueRaw, lightSensorSlopeForDisplay
	global lightMinDimForDisplay, lightMaxDimForDisplay, lightSensorOnForDisplay, useLightSensorType, useLightSensorDevId
	global multIntensity, intensity, intensityDevice, lightSensorValue
	global inpRaw
	global oldRaw, lastRead
	try:
		retCode					= 0

		inp, inpRaw, lastRead2 = U.doRead(lastTimeStamp=lastRead)
		if inp == "": return retCode
		if lastRead2 == lastRead: return retCode
		lastRead   = lastRead2
		if inpRaw == oldRaw: return retCode
		oldRaw	   = inpRaw

		lastintensityDevice		= intensityDevice
		lastsignalPin			= signalPin
		lastdevType				= devType
		lastOrderOfMatrix		= OrderOfMatrix
		lastPWMchannel			= PWMchannel
		lastDMAchannel			= DMAchannel
		lastfrequency			= frequency
		
		if "output"				in inp:	 
			output=				  (inp["output"])
			if pgmType in output:
				for devid in output[pgmType]:
					ddd			= output[pgmType][devid][0]
					if "devType"  in ddd: 
						devType		= ddd["devType"]
					if "devTypeLEDs" in ddd and "devTypeROWs" in ddd:
						devType = ddd["devTypeROWs"]+"x"+ddd["devTypeLEDs"]
						
					if "intensity"		in ddd:
						intensityDevice		= float(ddd["intensity"])/100.
					if "flipDisplay"	in ddd:
						flipDisplay			= ddd["flipDisplay"]
					if "signalPin"		in ddd:
						signalPin			= int(ddd["signalPin"])
					if "OrderOfMatrix"	in ddd:
						OrderOfMatrix		= (ddd["OrderOfMatrix"])
					if "frequency"	in ddd:
						try:	frequency		 = int(ddd["frequency"])
						except: pass
					if "DMAchannel"	 in ddd:
						try:	DMAchannel		 = int(ddd["DMAchannel"])
						except: pass
					if "PWMchannel"	 in ddd:
						try:	PWMchannel		 = int(ddd["PWMchannel"])
						except: pass
					U.logger.log(20, " new params "+
					  "	 devType={}".format(devType)	  +
					  "	 signalPin={}".format(signalPin)	 +
					  "	 OrderOfMatrix={}".format(OrderOfMatrix)	 +
					  "	 intensityDevice={}".format(intensityDevice)+
					  "	 PWMchannel={}".format(PWMchannel)+
					  "	 DMAchannel={}".format(DMAchannel)+
					  "	 frequency={}".format(frequency)+
					  "	 flipDisplay={}".format(flipDisplay))
					if lastdevType !="" and ( frequency != lastfrequency):	
						U.logger.log(10, " new frequency={}".format(frequency)+" new={}".format(lastfrequency))
						retCode = 1
					if lastdevType !="" and ( DMAchannel != lastDMAchannel):  
						U.logger.log(10, " new DMAchannel={}".format(DMAchannel)+" new={}".format(lastDMAchannel))
						retCode = 1
					if lastdevType !="" and ( PWMchannel != lastPWMchannel):  
						U.logger.log(10, " new PWMchannel={}".format(PWMchannel)+" new={}".format(lastPWMchannel))
						retCode = 1
					if lastdevType !="" and ( signalPin != lastsignalPin):	
						U.logger.log(10, " new signalPin={}".format(signalPin)+" new={}".format(lastsignalPin))
						retCode = 1
					if lastdevType !="" and ( devType != lastdevType ):	 
						U.logger.log(10, " new devType={}".format(lastdevType)+" new={}".format(devType))
						retCode = 1
					if lastdevType !="" and ( OrderOfMatrix != lastOrderOfMatrix):	
						U.logger.log(10, " new OrderOfMatrix={}".format(OrderOfMatrix)+" new={}".format(lastOrderOfMatrix))
						retCode = 1


					if "lightSensorOnForDisplay" in ddd:
						try:	
							lightSensorOnForDisplay = ddd["lightSensorOnForDisplay"]
						except Exception as e:
								U.logger.log(30,"", exc_info=True)

					if "lightSensorForDisplay-DevId-type" in ddd:
						try:	
							useLightSensorDevId =     ddd["lightSensorForDisplay-DevId-type"].split("-")[0]
							useLightSensorType  =     ddd["lightSensorForDisplay-DevId-type"].split("-")[1]
						except Exception as e:
								U.logger.log(30,"", exc_info=True)

					if "lightSensorSlopeForDisplay" in ddd:
						try:	
							lightSensorSlopeForDisplay = max(0.01, min(300., float(ddd["lightSensorSlopeForDisplay"]) ) )
						except Exception as e:
								U.logger.log(30,"", exc_info=True)
					if "lightMinDimForDisplay" in ddd:
						try:	
							lightMinDimForDisplay = max(0.0, min(255., float(ddd["lightMinDimForDisplay"]) ) )
						except: pass
					if "lightMaxDimForDisplay" in ddd:
						try:	
							lightMaxDimForDisplay = max(0.0, min(255., float(ddd["lightMaxDimForDisplay"]) ) )
						except: pass


	except Exception as e:
		U.logger.log(30,"", exc_info=True)
	return	retCode
					   
def readNewInput():
	try:
		f = open(G.homeDir+"temp/neopixel.inp","r")
		xxx = f.read().strip("\n") 
		items = xxx.split("\n")
		f.close()
		os.remove(G.homeDir+"temp/neopixel.inp")
		U.logger.log(10," new input: {}".format(xxx))
		return items
	except:	 
		items=[]
		try:
			os.remove(G.homeDir+"temp/neopixel.inp")
		except:
			pass
	return []

		
def checkIfnewInput():
		return os.path.isfile(G.homeDir+"temp/neopixel.inp")

def checkIfnewReboot():
		return os.path.isfile(G.homeDir+"temp/rebooting.now")


def saveLastCommands(items):
	try:
		f = open(G.homeDir+"neopixel.last","w")
		f.write(json.dumps(items))	
		f.close()
	except Exception as e:
		U.logger.log(30,"", exc_info=True)

def readLastCommands():
	try:
		if os.path.isfile(G.homeDir+"neopixel.last"):
			f	= open(G.homeDir+"neopixel.last","r")
			xxx = f.read()	
			f.close()
			return json.loads(xxx)
	except Exception as e:
		U.logger.log(30,"", exc_info=True)
	return []

def deleteLastCommands():
	try:
		if os.path.isfile(G.homeDir+"neopixel.last"):
			os.remove(G.homeDir+"neopixel.last")
	except: pass
	
# ------------------    ------------------ 
def restartNEOpixel(param=""):
	global devType,lastdevType
	U.restartMyself(reason="restarting due to new device type, old="+devTypeLast+" new="+devType, param=param, doPrint=True)


# ------------------    ------------------ 
def getLightSensorValue(force=False):
	global lastlightSensorValue, lastTimeLightSensorValue, lastTimeLightSensorFile, lightSensorValueRaw, lightSensorSlopeForDisplay
	global lightMinDimForDisplay, lightMaxDimForDisplay, lightSensorOnForDisplay, intensity, useLightSensorType, useLightSensorDevId
	global multIntensity, intensityDevice, lightSensorValue
	try:
		tt0 = time.time()
		#U.logger.log(20, "lightSensorValue 1")
		if not lightSensorOnForDisplay:								return False
		if (tt0 - lastTimeLightSensorValue < 2) and not force:		return False
		if not os.path.isfile(G.homeDir+"temp/lightSensor.dat"):	return False
###{  "sensors": {    "i2cOPT3001": {      "393522233": {        "light": 40.96      }    }  },   "time": 1568991254.784975}
		rr , raw = U.readJson(G.homeDir+"temp/lightSensor.dat")
		if rr == {}:
			time.sleep(0.1)
			rr, raw = U.readJson(G.homeDir+"temp/lightSensor.dat")
		subprocess.call("sudo rm "+G.homeDir+"temp/lightSensor.dat >/dev/null 2>&1", shell=True)
		if rr == {} or "time" not in rr: 							return False
		if "sensors" not in rr: 									return False
		U.logger.log(10, "lightSensor useLightSensorDevId{}, useLightSensorType:{}  read: {} ".format(useLightSensorDevId, useLightSensorType, rr) )
		if useLightSensorType not in rr["sensors"]: 				return False
		if useLightSensorDevId  not in rr["sensors"][useLightSensorType]: return False
		tt = float(rr["time"])
		if tt == lastTimeLightSensorFile:							return False	

		lightSensorValueREAD = -1
		for devId in rr["sensors"][useLightSensorType]:
			if devId == useLightSensorDevId:
				lightSensorValueREAD = float(rr["sensors"][useLightSensorType][devId]["light"])
				break
		if lightSensorValueREAD ==-1 : 								return False
		lastTimeLightSensorFile = tt

		#U.logger.log(20, "lightSensorValue 2")
		if   useLightSensorType == "i2cTSL2561":	maxRange = 2000.
		elif useLightSensorType == "i2cOPT3001":	maxRange = 60.
		elif useLightSensorType == "i2cVEML6030":	maxRange = 700.
		elif useLightSensorType == "i2cIS1145":		maxRange = 2000.
		else:										maxRange = 1000.

		lightSensorValueRaw = lightSensorValueREAD * (lightSensorSlopeForDisplay/maxRange) 
		lightSensorValueRaw = max(0.05, lightSensorValueRaw)
		lightSensorValueRaw = min(20, lightSensorValueRaw)
		# lightSensorValueRaw should be now between ~ 0.001 and ~1.
		#if force:	
		#	lightSensorValue = lightSensorValueRaw
		#	return True
		if (  abs(lightSensorValueRaw-lastlightSensorValue) / (max (0.005, lightSensorValueRaw+lastlightSensorValue))  ) < 0.05: 
																	return False
		lightSensorValue = (lightSensorValueRaw*1 + lastlightSensorValue*3) / 4.
		lastTimeLightSensorValue = tt0
		#U.logger.log(20, "lightSensorValue sl:{};  read:{:.0f}, raw:{:.3f};  new used:{:.4f};  last:{:.4f}; maxR:{:.1f}, inties:{}; {}".format(lightSensorSlopeForDisplay, lightSensorValueREAD, lightSensorValueRaw, lightSensorValue, lastlightSensorValue,  maxRange, intensityDevice,  multIntensity) )
		lastlightSensorValue = lightSensorValue
		multIntensity =  intensityDevice * lightSensorValue
		return True
	except Exception as e:
		U.logger.log(30,"", exc_info=True)
	return False


# ------------------    ------------------ 
def checkLightSensor():
	global lastlightSensorValue, lastTimeLightSensorValue, lastTimeLightSensorFile, lightSensorValueRaw
	global lightMinDimForDisplay, lightMaxDimForDisplay, lightSensorOnForDisplay
	global multIntensity, intensityDevice, lightSensorValue
	try:
		
			
		if not lightSensorOnForDisplay : return False
		if not getLightSensorValue(force=True):
			if (  abs(lightSensorValueRaw - lightSensorValue) / (max(0.005, lightSensorValueRaw + lightSensorValue))  ) > 0.05:
				#U.logger.log(20, " step up down light: lsv:{};  lsvR:{};  newlsv:{}; inties:{};  {}".format(lightSensorValue, lightSensorValueRaw, (lightSensorValueRaw*1 + lightSensorValue*3) / 4.,  intensityDevice,  multIntensity) )
				lightSensorValue     = (lightSensorValueRaw*1 + lightSensorValue*3) / 4.
				lastlightSensorValue = lightSensorValue
				multIntensity =  intensityDevice * lightSensorValue
				return True
			else:
				if lightSensorValue == lightSensorValueRaw: return False
				lightSensorValue     = lightSensorValueRaw
				multIntensity = intensityDevice * lightSensorValue
				#U.logger.log(20, " step read    light: lsv:{};  lsvR:{};  newlsv:{}; inties:{}; {}".format(lightSensorValue, lightSensorValueRaw, (lightSensorValueRaw*1 + lightSensorValue*3) / 4.,  intensityDevice,  multIntensity) )
				return True
	except Exception as e:
		U.logger.log(30,"", exc_info=True)
	
#=============================
#=============================


global LED_COUNT, rotation, intenstity, intensity, lastAlive
global devType,	 intensityDevice,flipDisplay, signalPin,OrderOfMatrix, PWMchannel, DMAchannel, frequency
global lastOrderOfMatrix, lastdevType, lastsignalPin, lastintensityDevice, lastPWMchannel, lastDMAchannel,lastfrequency
global lastlightSensorValue, lastTimeLightSensorValue, lastTimeLightSensorFile, lightSensorValueRaw, lightSensorSlopeForDisplay
global lightMinDimForDisplay, lightMaxDimForDisplay, lightSensorOnForDisplay
global useLightSensorType, useLightSensorDevId
global multIntensity, intensity, intensityDevice, lightSensorValue
global height,width
global linearDATA
global oldRaw,	lastRead
oldRaw					= ""
lastRead				= 0

# LED strip configuration:
signalPin		= 18	  # GPIO pin connected to the pixels (must support PWM!).
#LED_FREQ_HZ	 =	400000	# LED signal frequency in hertz (usually 800khz)
LED_FREQ_HZ		= 800000  # LED signal frequency in hertz (usually 800khz)
LED_DMA			= 5		  # DMA channel to use for generating signal (try 5)
LED_BRIGHTNESS	= 255	  # Set to 0 for darkest and 255 for brightest
LED_CHANNEL		= 0		  # PWM channel
LED_INVERT		= False	  # True to invert the signal (when using NPN transistor level shift)
devType			= ""
flipDisplay		= 0
PWMchannel		= 0
DMAchannel		= 5
frequency		= 800000
intensity		= 1
intensityDevice = 1

useLightSensorType 			= ""
useLightSensorDevId 		= 0

multIntensity				= 1
lightSensorValue			= 1.
lastlightSensorValue 		= 0
lastTimeLightSensorValue	= 0
lastTimeLightSensorFile 	= 0
lightSensorValueRaw 		= 1
lightSensorSlopeForDisplay 	= 1.
lightMinDimForDisplay  		= 0.3
lightMaxDimForDisplay		= 255
lightSensorOnForDisplay 	= False


pgmType	 = "neopixel"
setClock = ""
try:
		pgmType	 = sys.argv[1]
		setClock = sys.argv[2]
except: pass

#print "pgmType", pgmType

OrderOfMatrix	= "lrrl"
inpRaw			= ""
U.setLogging()

readParams(pgmType=pgmType)
U.logger.log(20, u"=========== (re) started neopixel  ============{}".format(sys.argv))


LED_CHANNEL	   = PWMchannel
LED_FREQ_HZ	   = frequency
LED_DMA		   = DMAchannel




if devType	  == "": 
	U.logger.log(30, u"{} , no neopixel section in parameters file available".format(datetime.datetime.now()))
	exit()

MAP,linMAP		   = makeMAP(devType, OrderOfMatrix=OrderOfMatrix)
height,width = get_shape()
LED_COUNT	 = width*height
linearDATA =[[0,0,0] for ii in range(LED_COUNT)]


ws2812 = Adafruit_NeoPixel(LED_COUNT, signalPin, LED_FREQ_HZ, LED_DMA, LED_INVERT, LED_BRIGHTNESS, LED_CHANNEL)
ws2812.begin()

brightness(intensityDevice)

image = draw(nx=width,ny=height)
##image.clear([0,0,0])## not enabled, keep last alive 

#items.append({})
#items[0]["resetInitial"]	 = [0,0,0]
#items[0]["repeat"]			 = 1
#items[0]["startAtDateTime"] = 0
#items[0]["command"]		 = []
#items[0]["command"].append(   {"type":"sPoint","position":[0,0,100,100,100],"display":"immediate"}	 )
#items[0]["command"].append(   {"type":"sPoint","position":[1,0,100,0,100],"display":"immediate"}  )
#items[0]["command"].append(   {"type":"sPoint","position":[0,0,200,0,0],"display":"immediate"}	 )
#items[0]["command"].append(   {"type":"line","position":[7,10,0,7,0,255,0],"display":"wait"}  )
#items[0]["command"].append(   {"type":"line","position":[0,3,7,3,0,0,255],"display":"wait"}  )
#items[0]["command"].append(   {"type":"line","position":[3,7,3,0,255,0,0],"display":"immediate"}  )
#items[0]["command"].append(   {"type":"rectangle","position":[2,2,4,4,255,0,0],"display":"immediate"}	)
#items[0]["command"].append(   {"type":"sPoint","position":[6,6,255,255,0],"display":"immediate"}  )

#print items
items			= []
loopCount		= 0
loop			= 0
lastAlive		= 0
devTypeLast		= devType
lastItems		= []
redoItems 		= False
lastClock 		= 0
tclockLast 		= time.time() -1
myPID			= str(os.getpid())
U.killOldPgm(myPID,G.program+".py")


iknightriderInd = 0
iknightriderDir = 1

time.sleep(0.1)
while True:
	#U.logger.log(20,"after while")
	ttx = time.time()
	try:
		if loop == 1 and  (items == [] or items ==""):
			items = readLastCommands()

		if redoItems and lastItems != []: 
			items = copy.copy(lastItems)

		for item in items:
		
			#print item
			try:
				if len(item) < 1: continue
				try:	
					data = json.loads(item)
				except Exception as e:
					if loop >0:
						U.logger.log(30,"", exc_info=True)
						U.logger.log(30,"{}".format(item)[0:100])
					data = item
				#print json.dumps(data,sort_keys=True, indent=2)
			except Exception as e:
				U.logger.log(30,"bad input {}".format(item) )
				U.logger.log(30,"", exc_info=True)
				continue

			restoreAfterBoot = False
			if items !=[] and "restoreAfterBoot" in data:
				try: 
					restoreAfterBoot = "{}".format(data["restoreAfterBoot"]).lower() 
					if restoreAfterBoot == "true" or  restoreAfterBoot == "1" :
						U.logger.log(10, " do a restore after reboot:{}".format(restoreAfterBoot))
						saveLastCommands(items)
					else:
						deleteLastCommands()
				except: pass

			if "resetInitial" in data or "res" in data:
				try: 
					if   "res" in data:				resetInitial= data["res"]
					elif "resetInitial" in data:	resetInitial= data["resetInitial"]
					if resetInitial !=[] and resetInitial !="":
						try:resetInitial= json.loads(resetInitial)
						except: pass
						U.logger.log(10, "resetting initial:".format(resetInitial))
						image.resetImage(resetInitial)
						image.show()
				except: pass


			if "startAtDateTime" in data:
				try:
					startAtDateTime =  float(data["startAtDateTime"]) -time.time()
					if startAtDateTime > 0:
						time.sleep(startAtDateTime)
				except:
					pass

			
			repeat=1
			try:
				if "repeat" in data: repeat = int(data["repeat"])
			except:
				pass

			setClock = ""
			try:
				if "setClock" in data: 
					setClock	  = data["setClock"]
				if setClock == "off":
					image.resetImage([0,0,0])
					image.show()
					exit()
			except:
				pass


			
			intensity=1.
			try:
				if "intensity" in data: intensity	   = float(data["intensity"])/100.
			except:
				pass
							
			cType =""
			nnxx =0		
			while nnxx < repeat or repeat < 0:
					tt0 =time.time()
					nnxx+=1
					if "command" not in data: break 
					loopCount+=1
					#print "comand", data["command"]
					ncmds = len(data["command"])
					npage=-1
					waited = False
					for cmd in data["command"]:
						try:
								tt= time.time()
								U.logger.log(10, "cmd:{}".format(cmd) )
								if "type" not in cmd: continue
								cType = cmd["type"]
								if cType == "" or cType == "0":	 continue
			

								reset =""
								if "reset" in cmd:
									reset = cmd["reset"]
									if reset !=[]:
										try:		image.resetImage(reset)
										except:		U.logger.log(30, " reset error :{}".format(reset))


								if loopCount%100000 ==0:
									#print " resetting due to loopcount",loopCount
									if devType!="":
										pass


								if "display" not in cmd or cmd["display"] != "wait": 
									delayStart=0
									if "delayStart" in cmd:
										try: 
											delayStart = float(cmd["delayStart"])
											time.sleep(delayStart)
										except: pass
								
								if cType == "NOP" :
										U.logger.log(10,u"skipping display .. NOP")
										continue

								rotate=0
								if "rotate" in cmd :
									try:
										rotate = int(cmd["rotate"])
									except: rotate = 0

								rotateSeconds=0.
								if "rotateSeconds" in cmd:
									try:
										rotateSeconds = float(cmd["rotateSeconds"])
									except: rotateSeconds = 0

								speedOfChange=0
								if "speedOfChange" in cmd:
									try:
										speedOfChange = int(cmd["speedOfChange"])
									except: speedOfChange = 0
				
								pos = [0,0,0,0,0]
								if "p" in cmd or "position" in cmd:
									if "p" in 	   		cmd: pos = cmd["p"]
									if "position" in 	cmd: pos = cmd["position"]

						
								#U.logger.log(10,u"type:"+cType+" pos:{}".format(pos)[0:20] )
								if cType == "line"  or cType.lower() == "l": # 2 d line
									image.line(pos)
							
								elif cType.lower() == "sline"  or cType.lower() == "sl": # one d line  [xs,xe,R,G,B]
									image.sLine(pos)
				
							
								elif cType == "rectangle" or cType == "r":
									image.rectangle(pos)
				
 
								elif cType.lower() == "spoint" or cType == "sp":
									image.point(pos)
					
								elif cType == "image" and "text" in cmd and len(cmd["text"]) >0:
										U.logger.log(10,u"type:"+cType+" pos:{}".format(pos) +" text:" + cmd["text"])
										pass

								elif cType == "matrix":
									image.matrix(pos)

								elif cType == "points":
									image.points(pos)


								elif cType == "knightrider" or cType == "kr":
										if len(pos) != 7:
											U.logger.log(20,u"not enough parameters for postion:{}, should be 7".format(pos))
											time.sleep(3)
											continue

										sleepTime = max(0.05, pos[0])
										nsteps  = pos[1]
										xstart = pos[2]
										xend   = pos[3]
										RGB = pos[4:]

										resetLEDS = [0, xstart, 0, xend+nsteps, 0, 0, 0]
										xx = [0, xstart + iknightriderInd, 0, xend+ iknightriderInd] + RGB
										if xx[1] <= xstart: 			iknightriderDir = 1
										if iknightriderInd >= nsteps: 	iknightriderDir = -1
										iknightriderInd += iknightriderDir
										#U.logger.log(20,u" sleep:{},  iRaiderInd{}, iRaiderDir:{}, pos:{} xx:{} ".format(pos[0], iRaiderInd, iRaiderDir, pos, xx))
										image.line(resetLEDS)
										image.line(xx)
										time.sleep(sleepTime) 

								elif cType == "colorknightrider" or cType == "ckr":
										if len(pos) < 6:
											U.logger.log(20,u"not enough parameters for postion:{}, should be > +3/6/9/...".format(pos))
											time.sleep(3)
											continue

										sleepTime = max(0.05, pos[0])
										nsteps  = pos[1]
										xstart = pos[2]

										if cType == "ckrr": 	
											nLEDs = pos[3]
											LEDs = []
											for i23 in range(nLEDs):
												LEDs.append(pos[4])
												LEDs.append(pos[5])
												LEDs.append(pos[6])
												LEDs.append(pos[7])
												LEDs.append(pos[8])
												LEDs.append(pos[9])
												LEDs.append(pos[10])
												LEDs.append(pos[11])
												LEDs.append(pos[12])

										else: 					
											nLEDs  = int((len(pos) - 3 )/3)
											LEDs   = pos[3:]

										xend = xstart + nLEDs
										resetLEDS = [0, xstart-nLEDs, 0, xend+nsteps, 0, 0, 0]
										image.line(resetLEDS)

										#U.logger.log(20,u" pos:{},, xstart:{},, xend:{},, nLEDs:{},, resetLEDS:{}, ".format(pos, xstart, xend, nLEDs, resetLEDS ))
										for nn in range(nLEDs):
											x = xstart + iknightriderInd+nn
											nl = nn*3
											#U.logger.log(20,u"  iRaiderInd{}, iRaiderDir:{},x:{}, nl:{} ".format(iknightriderInd, iknightriderDir, x, nl))
											xx = [0, x] + LEDs[nl:nl+3]
											image.point(xx)
										time.sleep(sleepTime) 
										if xx[1] <= xstart: 			iknightriderDir = 1
										if iknightriderInd >= nsteps: 	iknightriderDir = -1
										iknightriderInd += iknightriderDir

								elif cType == "clock":
									tt1 = time.time()
									if setClock == "off":
										image.resetImage([0,0,0])
										image.show()
										exit()
									speed = 1
									if len("{}".format(pos)) < 20: 
										U.logger.log(30, u"clock:  bad data, exiting")
										time.sleep(1)
										exit()
									if "speed" in pos:
										try: speed = int(pos["speed"])
										except: 
											pass
									if tt- lastClock < 1 and speed ==1 and setClock =="":
										#print	"tt- lastClock", tt- lastClock
										continue 
									#print speed, pos
									if speed == 1 and setClock == "":
										lastClock = int(tt)
										dd = datetime.datetime.now()
										hh = dd.hour
										if hh > 11: hh -=12	 # 0-11
										mm = dd.minute	# 0..59
										ss = dd.second	# 0..59
										smh={"SS":dd.second,"MM":dd.minute,"HH":hh,"DD":dd.day} 
									elif setClock != "":
										dhms = setClock.split(":")
										hh = int(dhms[1])
										if hh > 11: hh -=12	 # 0-11
										smh={"SS":int(dhms[3]),"MM":int(dhms[2]),"HH":hh,"DD":int(dhms[0])} 
										#print hms, smh
									else:
										try:
											s+=2
										except:
											s = 0
											m = 0
											h = 0
											d = 0
										if s > 59: 
											s = 0
											m+= 2
										if m >59:
											m = 0
											h+= 1
										if h > 11: 
											d+=1
											h =0
										smh={"SS":s,"MM":m,"HH":h,"DD":d} 
										#print "sped >1", smh 
									lin	  = [[0,i,0,0,0] for i in range(len(linMAP))]
									if "marks" in pos:
										ma = pos["marks"]
										if ma !="":
											for aa in ["HH","SS","MM","DD"]:
												if aa not in ma: continue
												rgb = ma[aa]["RGB"]
												for kk in ma[aa]["index"]:
													for ii in kk:
														if ii < 0:			continue
														if ii >= LED_COUNT: continue
														lin[ii] =  [0,ii, int(rgb[0]),int(rgb[1]),int(rgb[2])]
									for aa in ["SS","MM","HH","DD","extraLED"]:
										if aa in pos and pos[aa] !="":
											try:
												xx	   = pos[aa]["index"]
												rgb	   = pos[aa]["RGB"]
												blink  = [1,1]
												try:	blink  = pos[aa]["blink"]
												except: blink  = [1,1]
												for jj in range(len(xx)):
													if aa in smh and jj !=smh[aa]: continue
													for ii in xx[jj]:
														if ii < 0:			continue
														if ii >= LED_COUNT: continue
														if ((blink ==[1,0]						) or  
															(blink ==[1,1]	and smh["SS"]%2 >  0) or
															(blink ==[2,1]	and smh["SS"]%3 >  0) or
															(blink ==[3,1]	and smh["SS"]%4 >  0) or
															(blink ==[4,1]	and smh["SS"]%5 >  0) or
															(blink ==[9,1]	and smh["SS"]%10 > 0) or
															(blink ==[14,1] and smh["SS"]%15 > 0) or
															(blink ==[29,1] and smh["SS"]%30 > 0) or
															(blink ==[59,1] and smh["SS"]%60 > 0) or
															(blink ==[0,1]	and smh["SS"]%2 == 0) or
															(blink ==[2,1]	and smh["SS"]%3	 < 2) or
															(blink ==[2,2]	and smh["SS"]%4	 < 2) or
															(blink ==[3,1]	and smh["SS"]%4	 < 3) or
															(blink ==[3,2]	and smh["SS"]%5	 < 3) or
															(blink ==[3,3]	and smh["SS"]%6	 < 3) or
															(blink ==[0,2]	and smh["SS"]%3 == 0) or
															(setClock !=""						)):
															#print aa,"ii",ii
															ll = lin[ii][2:]
															lin[ii] =  [0,ii,rgb[0]+ll[0],rgb[1]+ll[1],rgb[2]+ll[2]]
											except Exception as e:
												U.logger.log(30,"", exc_info=True)
												U.logger.log(30, aa +"  {}".format(pos[aa]))
									for ii in range(len(lin)):
										lin[ii] =  [0,lin[ii][1], min(255,max(lin[ii][2],0)),min(255,max(lin[ii][3],0)),min(255,max(lin[ii][4],0)) ]
											
									tt2 = time.time()
									image.points(lin)

								if "display" not in cmd or cmd["display"] != "wait": 
									U.logger.log(10, u"displaying	 {}".format(cmd["type"]) )
									tt3 = time.time()
									image.show(rotate=rotate, rotateSeconds=rotateSeconds, speedOfChange=speedOfChange)
								if cType == "clock":
									if speed !=1:
										time.sleep(0.2)
										#print "neopixel sleep 0.2"
									else:
										tt = time.time()
										slTime = max( 0,0.3 - (	 max(tt-int(tt), tt - lastClock) )	)
										#print "sleep for ",tt-int(tt), slTime, speed,	tt-tt0, tt-tt1,tt-tt2,tt-tt3
										time.sleep(slTime)
										#print "neopixel sleep", slTime,tt-tt2, tt-tt3, tt-tt0, tt-int(tt) , tt- tclockLast
									if setClock !="":
										time.sleep(1)
										
								waited = True
							
								tt= time.time()
								if tt - lastAlive > 20.:  
									lastAlive =tt
									#print "echo alive"
									U.echoLastAlive(G.program)
									if readParams(pgmType=pgmType) ==1:
										restartNEOpixel(param =pgmType )

								if checkIfnewInput(): break
								
						except Exception as e:
							U.logger.log(30,"", exc_info=True)
					if checkIfnewInput(): break
					if checkIfnewReboot(): break
					if cType == "clock": 
						time.sleep(min(0.1, max(0,time.time()- lastClock)))
					#print "neopixel sleep end repeat ", time.time() -tt0
		time.sleep(0.1) 
		if items != []:
			lastItems = copy.copy(items)
		items = []
		if checkIfnewReboot(): break
		try:
			if checkIfnewInput():
				items = readNewInput()
			redoItems = checkLightSensor()
		except Exception as e:
			U.logger.log(30,"", exc_info=True)
				
		if loop %20 ==0:
			if readParams(pgmType=pgmType) ==1:
				restartNEOpixel(param =pgmType )
			U.echoLastAlive(G.program)
		loop +=1 
		#print "neopixel sleep end item ", time.time() -ttx


	except Exception as e:
		U.logger.log(30,"", exc_info=True)
		items=[]

U.logger.log(30, u"exiting at end")

atexit.register()
		
sys.exit(0)		   
