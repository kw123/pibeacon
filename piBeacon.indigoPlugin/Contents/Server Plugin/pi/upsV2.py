#! /usr/bin/env python
# -*- coding: utf-8 -*-
####################
# pibeacon Plugin
# copied from  https://github.com/rcdrones/UPSPACK_V2
# adopted to piBeacon environment
# karlwachs@me.com

import serial
import re
import RPi.GPIO as GPIO
import os
import sys
import time
import datetime

class UPS2:
	def __init__(self, port):
		self.ser  = serial.Serial(port, 9600)
		
	def getData(self):
		# first flush and wait for new data , sending every 1 sec
		#self.ser.flushInput()		
		#time.sleep(0.1)
		##
		# GOOD,BATCAP 84,Vout 5204 $
		#$ SmartUPS V1.00,Vin GOOD,BATCAP 84,Vout 5204 $
		#$ SmartUPS V1.00,Vin GOO 
		####

		line = ""
		uart_string =""
		lines = ""
		good  = ""
		for ii in range(10):
			nn = self.ser.inWaiting()
			if  nn !=0:
				time.sleep(0.01)
				nn = self.ser.inWaiting()
				uart_string = self.ser.read(nn)
				# check if we got a full line
				#$ SmartUPS V1.00,Vin GOOD,BATCAP 84,Vout 5204 $
				if len(uart_string) > 30 and uart_string[-2] =="$" and uart_string[0] =="$": break
				if len(uart_string) > 50 : break
				if uart_string[0] !="$": continue
				time.sleep(0.2)
				nn = self.ser.inWaiting()
				uart_string += self.ser.read(nn)
				if len(uart_string) > 30 and uart_string[-2] =="$": 
					break
				
				
			else:
				time.sleep(0.2)
		lines = uart_string.strip().split("\n")
		nLines = len(lines)

		for nn in range(nLines):
			if lines[nLines-nn-1].count("$") == 2 and lines[nLines-nn-1][-1] =="$":
				good = lines[nLines-nn-1].strip().strip("$").strip().split(",")	
				break			

		if good == "":
			return "", "no connection", "", ""

#	print(uart_string)
		#print "tries",ii, "data", good 
		version 	= ""
		vin 		= ""
		batcap 		= ""
		vout 		= ""
		for dd in good:
			if   "SmartUPS" in dd: version 	= dd.split(" ")[1]
			elif "Vin" 		in dd: vin 		= dd.split(" ")[1]
			elif "BATCAP" 	in dd: batcap 	= dd.split(" ")[1]
			elif "Vout" 	in dd: vout 	= dd.split(" ")[1]

		return version, vin, batcap, vout
	

def setupShutdownSignalFromUPS(bcm_io):
	global shutdownSignalFromUPSPin
	if bcm_io < 1: return 
	shutdownSignalFromUPSPin = bcm_io
	GPIO.setup(shutdownSignalFromUPSPin, GPIO.IN, pull_up_down=GPIO.PUD_DOWN)
	GPIO.add_event_detect(shutdownSignalFromUPSPin, GPIO.FALLING, callback= shutdownSignalFromUPS, bouncetime=1000)


def shutdownSignalFromUPS(channel):
	global shutdownSignalFromUPS_pin
	if channel != shutdownSignalFromUPSPin: return 
	print("detect LOW bat capacity::: ")
	time.sleep(1)
	if GPIO.input(shutdownSignalFromUPSPin) !=0:
		print("detect LOW bat capacity::: system back up")
		return
	#U.doReboot(tt=10, text="shutdown by UPS signal battery capacity", cmd="sudo sync; wait 2; sudo shutdown now")
	


if __name__ == "__main__":
	GPIO.setwarnings(False)
	GPIO.setmode(GPIO.BCM)
	
	print("Testing UPS v2 ")
	setupShutdownSignalFromUPS(5)

	getInfo = UPS2("/dev/ttyS0")
#	getInfo = UPS2("/dev/ttyAMA0")
	i = 1
#	
	while True:
		version, vin, batcap, vout = getInfo.getData()
		
		print("UPS Version:         {}".format(version) )
		print("Battery Capacity:    {} %".format(batcap))
		print("UPS Output Voltage:  {} mV".format(vout))
		print("UPS INPUT Voltage:   {}".format(vin))
		print("\n")
		
		i = i+1
		
		if i == 10000:
			i = 1
		time.sleep(80)
   
		
		
	