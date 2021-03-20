#!/usr/bin/python
# -*- coding: utf-8 -*-
# SPDX-FileCopyrightText: 2021 ladyada for Adafruit Industries
# SPDX-License-Identifier: MIT

import time
import sys
import json
import os
import datetime
#sys.path.append(os.getcwd())
#sys.path.append('/usr/lib/python3/dist-packages') 

import	piBeaconUtils	as U
import	piBeaconGlobals as G
G.program ="DHT3"
# Initial the dht device, with data pin connected to:
#dhtDevice = adafruit_dht.DHT22(board.D17)

# you can pass DHT22 use_pulseio=False if you wouldn't like to use pulseio.
# This may be necessary on a Linux single board computer like the Raspberry Pi,
# but it will not work in CircuitPython.

#print ("\n"+sys.argv[1]+"\n")
params   = json.loads(sys.argv[1])

outfile  = params["outfile"]
stopfile = params["stopfile"]
sensors  = params["sensors"]

"""
    sensors ={"848749478":{"gpioPin": "17"}}
#                 12345678901234567890123456789012345678901234567890
#python3 DHT.py3 '{"outfile": "temp/dht.out", "sensors": {"848749478": {"dhtType": "22", "gpioPin": "17"}}, "stopfile": "temp/dht.stop"}'
"""

import board
import adafruit_dht

U.setLogging()
myPID		= str(os.getpid())
U.logger.log(20,"DHT.py3 starting v 0.91, pid={}, params:{}".format(myPID, params))

U.killOldPgm(myPID,G.program+".py3")# kill old instances of myself if they are still running


dhtDevice = {}
for devId in sensors:
	pin = sensors[devId]["gpioPin"]
	
	if "dhtType" in sensors[devId]: dhtType = sensors[devId]["dhtType"]
	else:							dhtType = "22"

	if dhtType == "22":
		if pin == "17": dhtDevice[pin] = adafruit_dht.DHT22(board.D17, use_pulseio=False)
		if pin == "27": dhtDevice[pin] = adafruit_dht.DHT22(board.D27, use_pulseio=False)
		if pin == "22": dhtDevice[pin] = adafruit_dht.DHT22(board.D22, use_pulseio=False)
		if pin == "5":  dhtDevice[pin] = adafruit_dht.DHT22(board.D5,  use_pulseio=False)
		if pin == "6":  dhtDevice[pin] = adafruit_dht.DHT22(board.D6,  use_pulseio=False)
		if pin == "13": dhtDevice[pin] = adafruit_dht.DHT22(board.D13, use_pulseio=False)
		if pin == "18": dhtDevice[pin] = adafruit_dht.DHT22(board.D18, use_pulseio=False)
		if pin == "23": dhtDevice[pin] = adafruit_dht.DHT22(board.D23, use_pulseio=False)
		if pin == "24": dhtDevice[pin] = adafruit_dht.DHT22(board.D24, use_pulseio=False)
		if pin == "25": dhtDevice[pin] = adafruit_dht.DHT22(board.D25, use_pulseio=False)
		if pin == "12": dhtDevice[pin] = adafruit_dht.DHT22(board.D12, use_pulseio=False)
		if pin == "16": dhtDevice[pin] = adafruit_dht.DHT22(board.D16, use_pulseio=False)
		if pin == "20": dhtDevice[pin] = adafruit_dht.DHT22(board.D20, use_pulseio=False)
		if pin == "21": dhtDevice[pin] = adafruit_dht.DHT22(board.D21, use_pulseio=False)
	else:
		if pin == "17": dhtDevice[pin] = adafruit_dht.DHT11(board.D17, use_pulseio=False)
		if pin == "27": dhtDevice[pin] = adafruit_dht.DHT11(board.D27, use_pulseio=False)
		if pin == "22": dhtDevice[pin] = adafruit_dht.DHT11(board.D22, use_pulseio=False)
		if pin == "5":  dhtDevice[pin] = adafruit_dht.DHT11(board.D5,  use_pulseio=False)
		if pin == "6":  dhtDevice[pin] = adafruit_dht.DHT11(board.D6,  use_pulseio=False)
		if pin == "13": dhtDevice[pin] = adafruit_dht.DHT11(board.D13, use_pulseio=False)
		if pin == "18": dhtDevice[pin] = adafruit_dht.DHT11(board.D18, use_pulseio=False)
		if pin == "23": dhtDevice[pin] = adafruit_dht.DHT11(board.D23, use_pulseio=False)
		if pin == "24": dhtDevice[pin] = adafruit_dht.DHT11(board.D24, use_pulseio=False)
		if pin == "25": dhtDevice[pin] = adafruit_dht.DHT11(board.D25, use_pulseio=False)
		if pin == "12": dhtDevice[pin] = adafruit_dht.DHT11(board.D12, use_pulseio=False)
		if pin == "16": dhtDevice[pin] = adafruit_dht.DHT11(board.D16, use_pulseio=False)
		if pin == "20": dhtDevice[pin] = adafruit_dht.DHT11(board.D20, use_pulseio=False)
		if pin == "21": dhtDevice[pin] = adafruit_dht.DHT11(board.D21, use_pulseio=False)


while True:
	out = {}
	#print (" looping")
	for devId in sensors:
		out[devId]={"temp":"","hum":""}
		pin = sensors[devId]["gpioPin"]
		#print ("pin:{} ".format(pin))
		temp = ""
		hum = ""
		for ii in range(5):
			# 
			try:
				temp = dhtDevice[pin].temperature
				hum  = dhtDevice[pin].humidity
				break
			except RuntimeError as error:
				# Errors happen fairly often, DHT"s are hard to read, just keep going, only log every 3 try
				if ii > 3: U.logger.log(20,"RuntimeError:  {}".format(error))
			except Exception as error:
				if ii > 3: U.logger.log(20,"error:  {}".format(error))
				raise error
			time.sleep(2.0)

		out[devId] = {"temp":temp,"hum":hum}
	out = json.dumps(out)
	#U.logger.log(20,"{}".format(out))

	writeOk = False
	for ii in range(3):
		try:
			f = open(outfile,"w")
			f.write(out)
			f.close()
			writeOk = True
			break
		except:
			try:	f.close()
			except:	pass
			time.sleep(1)

	if not writeOk: 
		U.logger.log(20,"exit due to write failure")
		exit()

	if os.path.isfile(stopfile): 
		os.remove()
		U.logger.log(20,"exit due to stop file")
		exit()

	time.sleep(6.1)
