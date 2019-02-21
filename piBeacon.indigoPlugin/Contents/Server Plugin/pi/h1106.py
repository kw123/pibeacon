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


import smbus
from PIL import ImageFont, ImageDraw
import PIL


class sh1106():

	def __init__(self, bus=None, port=1, address=0x3C, width=128, height=64):
		try:
			self.cmd_mode = 0x00
			self.data_mode = 0x40
			self.bus = smbus.SMBus(port)
			self.addr = address
			self.width = width
			self.height = height
			self.pages = int(self.height / 8)
			self.CHARGEPUMP = 0x8D
			self.COLUMNADDR = 0x21
			self.COMSCANDEC = 0xC8
			self.COMSCANINC = 0xC0
			self.DISPLAYALLON = 0xA5
			self.DISPLAYALLON_RESUME = 0xA4
			self.DISPLAYOFF = 0xAE
			self.DISPLAYON = 0xAF
			self.EXTERNALVCC = 0x1
			self.INVERTDISPLAY = 0xA7
			self.MEMORYMODE = 0x20
			self.NORMALDISPLAY = 0xA6
			self.PAGEADDR = 0x22
			self.SEGREMAP = 0xA0
			self.SETCOMPINS = 0xDA
			self.SETCONTRAST = 0x81
			self.SETDISPLAYCLOCKDIV = 0xD5
			self.SETDISPLAYOFFSET = 0xD3
			self.SETHIGHCOLUMN = 0x10
			self.SETLOWCOLUMN = 0x00
			self.SETMULTIPLEX = 0xA8
			self.SETPRECHARGE = 0xD9
			self.SETSEGMENTREMAP = 0xA1
			self.SETSTARTLINE = 0x40
			self.SETVCOMDETECT = 0xDB
			self.SWITCHCAPVCC = 0x2


			self.command(
				self.DISPLAYOFF,
				self.MEMORYMODE,
				self.SETHIGHCOLUMN,	  0xB0, 0xC8,
				self.SETLOWCOLUMN,	   0x10, 0x40,
				self.SETCONTRAST,		0x7F,
				self.SETSEGMENTREMAP,
				self.NORMALDISPLAY,
				self.SETMULTIPLEX,	   0x3F,
				self.DISPLAYALLON_RESUME,
				self.SETDISPLAYOFFSET,   0x00,
				self.SETDISPLAYCLOCKDIV, 0xF0,
				self.SETPRECHARGE,	   0x22,
				self.SETCOMPINS,		 0x12,
				self.SETVCOMDETECT,	  0x20,
				self.CHARGEPUMP,		 0x14)

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

##############
xPixel = 128
yPixel = 64

outputDev = sh1106(width=xPixel, height=yPixel)

font = ImageFont.load_default()
#
line1 = "line 1 234567890"
line2 = "line 2 234567890"
line3 = "line 3 234567890"
imData = PIL.Image.new('1', (xPixel,yPixel))
draw = ImageDraw.Draw(imData)
draw.rectangle((0, 0, xPixel,yPixel), outline=0, fill=0)
draw.text(( 0, 0), line1,  font=font, fill=255)
draw.text((30, 30),line2 , font=font, fill=255)
draw.text((50, 50),line3 , font=font, fill=255)
outputDev.display(imData)
