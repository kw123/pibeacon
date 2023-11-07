#!/usr/bin/python
# -*- coding: utf-8 -*-
# by Karl Wachs
# feb 5 2016
# version 0.9 
##
##  read one wire sensors 18b20 through RPI tools
##  using 
##    ls -o /sys/bus/w1/devices/
##     to get a list of sensors
##  then to read each sensor read 
##     /sys/bus/w1/devices/<<sn>>/w1_slave
##
##  also read config.txt to get a map of buschannel to GPIO mapping
##  
##  then send every xx secs or if change data to indigo through socket or http.
##
##

## ==========>> ok for py3

import math

import  sys, os, time, json, datetime,subprocess,copy

import RPi.GPIO as GPIO
GPIO.setmode(GPIO.BCM)
GPIO.setwarnings(False)


try: import Queue
except: import queue as Queue

import threading


sys.path.append(os.getcwd())
import  piBeaconUtils   as U
import  piBeaconGlobals as G

G.program = "Wire18B20"
_defaultDateStampFormat = "%Y-%m-%d_%H:%M:%S"



####-------------------------------------------------------------------------####
# ===========================================================================
def readPopen(cmd):
		try:
			ret, err = subprocess.Popen(cmd, shell=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE).communicate()
			return ret.decode('utf_8'), err.decode('utf_8')
		except Exception as e:
			U.logger.log(20,"", exc_info=True)



# ===========================================================================
def crc8(data):
	"""
	Compute CRC
	"""
	crc = 0
	for i in range(len(data)):
		byte = int(data[i],16)
		for b in range(8):
			fb_bit = (crc ^ byte) & 0x01
			if fb_bit == 0x01:
				crc = crc ^ 0x18
			crc = (crc >> 1) & 0x7f
			if fb_bit == 0x01:
				crc = crc | 0x80
			byte = byte >> 1
	return crc


# ===========================================================================
def checkIfReset(needToReset):
	global oneWireResetGpio, oneWireResetIsUpDown
	global lastReset, noResetBefore
	global resetTime, lastResetDateTime
	global resetCounter, oneWireForceReboot

	
	if not needToReset:
		lastReset = time.time()
		resetCounter = 0
		return 

	U.logger.log(20,"reboot:   checking resetCounter:{}>{}? ".format(resetCounter,oneWireForceReboot))
	if oneWireForceReboot > 0 and resetCounter > oneWireForceReboot:
		U.logger.log(30,"doing hard reset ")
		U.sendRebootHTML("onewire_hanging",reboot=True, force=False, wait=2.)
		
	try:
		if type(oneWireResetGpio) != int: 		return 
		if oneWireResetIsUpDown not in["up","down"]: 	return 
		U.logger.log(20,"check reset wait:{:.0f} ".format(noResetBefore - time.time() + lastReset ))
		if time.time() - lastReset <  noResetBefore: return
		U.logger.log(20,"doing a reset on GPIO:{} for {} secs, setting to:{} ".format(oneWireResetGpio, resetTime, oneWireResetIsUpDown))
		upDown = oneWireResetIsUpDown == "up"
		GPIO.output(oneWireResetGpio, upDown)
		time.sleep(resetTime)
		GPIO.output(oneWireResetGpio, not upDown)
		time.sleep(7)
		lastReset = time.time() + noResetBefore
		lastResetDateTime = datetime.datetime.now().strftime(_defaultDateStampFormat)
		resetCounter += 1
		U.logger.log(20,"reset is finished ".format())
	except  Exception as e:
		U.logger.log(20,"doing a reset failed on GPIO:{} for {} secs, setting to:{} ".format(oneWireResetGpio, resetTime, oneWireResetIsUpDown), exc_info=True)


	return


# ===========================================================================
# ================one wire stuff   ======================================
# ===========================================================================

def mapBusmasterToGpio():
	global busMasterToGPIO, lastmapBusmasterToGpio, oneWireGpios
	try:
		"""
use :
looking  in /boot/config.txt for eg: 
dtoverlay=w1-gpio
dtparam=gpiopin=26   <-- this will be  busmaster 4
dtoverlay=w1-gpio
dtparam=gpiopin=5
dtoverlay=w1-gpio
dtparam=gpiopin=17
dtoverlay=w1-gpio
dtparam=gpiopin=4   <-- this will be  busmaster 1
or 
oneWireGpios set in rpi device edit = [1,4,6,7,8..]
		"""

		if time.time() - lastmapBusmasterToGpio < 60: return  

		doPrint = False
		lastmapBusmasterToGpio = time.time()
		busMasterToGPIOOld = copy.copy(busMasterToGPIO)
		newMapping = False
		busMasterToGPIO = {}

		if (oneWireGpios) == 0: #(use /boot/config.txt to check)
			f = open("/boot/config.txt","r")
			configTxt = f.read().split("\n")
			f.close
			pinsFound = []
			for lll in configTxt:	
				if doPrint: U.logger.log(20,"next line in config.txt>>{}<<  ".format(lll))
				if lll.find("dtparam=gpiopin=") > -1:
					pinsFound.append(lll.split("=")[-1])
					if doPrint: U.logger.log(20,"pinsFound:{}  ".format(pinsFound))
			pinsFound.reverse() # the mapping is revers to the sequence the commands that are listed in config.boot 
			for ii in range(len(pinsFound)):
				iss = str(ii+1)
				busMasterToGPIO[iss] = pinsFound[ii]
				if iss not in busMasterToGPIOOld or busMasterToGPIO[iss] != busMasterToGPIOOld[iss]:
					newMapping = True

			if newMapping:
				U.logger.log(20,"Changed or first mapping of busmaster channel to GPIO used:{} in \"`ls -o /sys/bus/w1/devices/`\" ".format(busMasterToGPIO))


		else:  # use oneWireGpios set in rpi device edit 
			for ii in range(len(oneWireGpios)):
				iss = str(ii+1)
				busMasterToGPIO[iss] = oneWireGpios[ii]
				if iss not in busMasterToGPIOOld or busMasterToGPIO[iss] != busMasterToGPIOOld[iss]:
					newMapping = True

			if newMapping:
				U.logger.log(20,"Changed or first mapping of busmaster channel to GPIO used:{}, oneWireGpios:{} ".format(busMasterToGPIO, oneWireGpios))
			


	except  Exception as e:
		U.logger.log(20,"v2", exc_info=True)
		busMasterToGPIO = {}
	return 	



	"""
replacing in /boot/config.txt:
dtoverlay=w1-gpio
dtparam=gpiopin=26
	"""
# ===========================================================================
def enableoneWireGPIO():
	global sensors, oneWireGpios,oneWireGpiosLast, lastmapBusmasterToGpio, busMasterToGPIOOld, busMasterToGPIO

	try:

		if len(oneWireGpios) == 0: return # not setup

		# check if everythings is already done:
		fnameForData = "{}temp/{}.busmaster".format(G.homeDir,G.program)
		oldData, inRaw = U.readJson(fnameForData)
		if oldData.get("oneWireGpios",[] ) == oneWireGpios:
			if len(oldData.get("busMasterToGPIO",{}) ) == len(oneWireGpios):
				busMasterToGPIO = oldData.get("busMasterToGPIO",{})
				U.logger.log(20," already done: oneWireGpios:{} - busMasterToGPIO:{}".format(oneWireGpios, busMasterToGPIO))
				return 

		# another check
		U.logger.log(20," (1) {} -- already done?: {}".format(oneWireGpios, oneWireGpios == oneWireGpiosLast))
		if oneWireGpios == oneWireGpiosLast: return 

		bmActive = []

		linesDir = readPopen("ls -o /sys/bus/w1/devices/")[0].strip("\n").split("\n")
		# count lines w   lrwxrwxrwx 1 root 0 Sep 16 02:06 w1_bus_master8 -> ../../../devices/w1_bus_master8
		
		#get all currently active busmasters
		for line in linesDir:
			if line.find("/devices/w1_bus_master") >- 1:  
				busMaster = (line.split("/devices/w1_bus_master")[1].split("/"))  #  reject ... ../devices/w1_bus_master5/28-800000035de5
				if len(busMaster) > 1: continue
				bmActive.append(busMaster[0])
				

		# all done?
		if len(bmActive) == len(oneWireGpios):
			U.logger.log(20,"all busmasters active: {} vs {} ".format(bmActive, len(oneWireGpios)))
			return

		# here we do the work, setup the pgms and busmasters
		ret = readPopen("sudo modprobe w1-gpio")
		U.logger.log(20,"enabling modprobe w1-gpio result:{}".format( ret))
		#U.logger.log(20,"oneWireGpios:{},oneWireGpiosR:{}".format( oneWireGpios, oneWireGpiosR))

		# now the busmasters
		for gpio in oneWireGpios:
			U.echoLastAlive(G.program) # prevent master from restarting this pgm

			# one by one
			ret = readPopen("sudo dtoverlay w1-gpio gpiopin={} pullup=0".format(gpio))
			U.logger.log(20,"adding busmaster: {} result:{}".format(gpio, ret))

			# check if it is done
			found = False
			for ii in range(5):
				if found: break
				time.sleep(0.5)
				linesDir = readPopen("ls -o /sys/bus/w1/devices/")[0].strip("\n").split("\n")
				for line in linesDir:
					if line.find("/devices/w1_bus_master") > -1:  
						newBM = (line.split("/devices/w1_bus_master")[1].split("/"))  #  reject ... ../devices/w1_bus_master5/28-800000035de5
						if len(newBM) > 1: continue
						#U.logger.log(20,"checking gpio:{}  busmaster:{},  lines for new BM line:{}".format(gpio, newBM, line))
						if newBM[0] in bmActive: continue
						U.logger.log(20,"adding gpio:{}  busmaster:{}, ".format(gpio, newBM[0]))
						bmActive.append(newBM[0])
						busMasterToGPIO[newBM[0]] = gpio
						lastmapBusmasterToGpio = time.time()
						found = True
						break

		U.logger.log(20,"busMasterToGPIO:{} ".format(busMasterToGPIO))

		# save stuff for nect time 
		oneWireGpiosLast = oneWireGpios
		busMasterToGPIOOld = copy.copy(busMasterToGPIO)
		U.writeJson(fnameForData, { "busMasterToGPIO":busMasterToGPIO,"oneWireGpios":oneWireGpios})

		time.sleep(10)  # wait until sensors are recognized by system, takes some secs 
	except  Exception as e:
		U.logger.log(20,"v2", exc_info=True)
		busMasterToGPIO = {}
	return 


# ===========================================================================
def readOneChannel(busMaster):
	global retData, threadCMD, readQueue, devIdToSerialNumber, busMasterToGPIO
	doPrint = True
	doPrint1 = False
	doPrint2 = False
	retData["data"][busMaster] = {}
	tStart = time.time()
	goodSensors = 0
	Nsensors = 0
	gpio = busMasterToGPIO.get(busMaster,"-1")
	if doPrint1: U.logger.log(20,"{:>5.2f}.. into busmaster: {}  ".format(time.time()-tStart, busMaster ))
	try:
		waitForFill = time.time()
		while threadCMD[busMaster]["state"] == "collecting":
			time.sleep(0.1)
			if time.time() - waitForFill > 1.:
				break
		
		waitForFinshed = time.time()
		while threadCMD[busMaster]["state"] == "filled":
			time.sleep(0.1)
			if time.time() - waitForFinshed > 20:
				break

			while not readQueue[busMaster].empty():
				Nsensors +=1
				sn, devId, gpio = readQueue[busMaster].get()
				gpio = int(gpio)
				if doPrint1: U.logger.log(20,"{:>5.2f}.. busmaster{} readQueue loop not empty Nsensors:{} sn:{}, devId:{}, gpio:{} ".format(time.time()-tStart, busMaster, Nsensors, sn, devId, gpio ))
				retData["data"][busMaster][sn] = {"temp": -995,"devId":  serialNumberToDevId.get(sn,"-1"), "gpioUsed":gpio }
				for tries in range(2):
					if doPrint1: U.logger.log(20,"{:>5.2f}.. try to read  busMaster{}, sn{}".format(time.time()-tStart, busMaster, sn))
					if os.path.isfile("/sys/bus/w1/devices/"+sn+"/w1_slave"): 
						f = open("/sys/bus/w1/devices/"+sn+"/w1_slave","r")
						dataW = f.read().strip("\n").split("\n")
						f.close()
						# finished reading
						if doPrint2: U.logger.log(20,"{:>5.2f}.. read  busMaster{}, sn{}, data: {}".format(time.time()-tStart, busMaster, sn, dataW))
						##59 01 ff ff 7f ff ff ff 82 : crc=82 YES
						##59 01 ff ff 7f ff ff ff 82 t=21562

						# now checking if ok. first find yes, then check crc, then get Temp value
						if len(dataW) == 2:
							if "YES" in dataW[0]:
								crc =  int(dataW[0].split("crc=")[1].split(" ")[0],16)    #  == crc=82 
								crccheck = crc8(dataW[0].split(" :")[0].split(" ")[0:8])  #  input: 59 01 ff ff 7f ff ff ff
								#if doPrint1: U.logger.log(20,"{:>5.2f}.. crc:{}, crccheck:{}".format(time.time()-tStart, crc, crcInt))
								if crc != crccheck:
									if doPrint: U.logger.log(20,"{:>5.2f}.. bad data, crc check failed".format(time.time()-tStart))
								else:
									t1 = dataW[1].split("t=")
									if len(t1) == 2:
										try:	
											temp = round(float(t1[1])/1000.,2)
											if temp == 85.0: temp = +990
											else:
												retData["data"][busMaster][sn]["temp"] = temp
												retData["totalGoodSensors"] += 1
												goodSensors += 1
											if doPrint2: U.logger.log(20,"{:>5.2f}.. busMaster:{}, dev#:{:>2d}/{:<2d},  devId:{:>12s},  busMaster#{}, GPIO:{} sn:{}, temp:{} done".format(time.time()-tStart, busMaster, goodSensors, Nsensors, devId, busMaster, gpio , sn, temp))
											break
										except  Exception as e:
											U.logger.log(20,"v2", exc_info=True)
											if doPrint: U.logger.log(20,"{:>5.2f}.. bad data1: {}".format(time.time()-tStart, dataW))
									else:
										if doPrint: U.logger.log(20,"{:>5.2f}.. bad data2: {}".format(time.time()-tStart, dataW))
							else:
								if doPrint: U.logger.log(20,"{:>5.2f}.. bad data3: {}".format(time.time()-tStart, dataW))
					time.sleep(1)
				if doPrint2: U.logger.log(20,"{:>5.2f}.. {} end of while not empty  goodSensors:{}/{}, state:{}, empty?{}".format(time.time()-tStart, busMaster, goodSensors, Nsensors, threadCMD[busMaster]["state"] , readQueue[busMaster].empty()))
			break

	except  Exception as e:
			U.logger.log(20,"v2", exc_info=True)
	if doPrint and goodSensors != Nsensors: 
			U.logger.log(20,"{:>5.2f}..========= busmaster:{}, gpio:{:>2}, goodSensors:{:}/{:}".format(time.time()-tStart, busMaster, gpio, goodSensors, Nsensors))


	threadCMD[busMaster]["state"] = "finished"
		
	return 
# ===========================================================================
# 18B20
# ===========================================================================
def get18B20(sensor):
	global sensors, oneWireAddNewSensors
	global lastGoodRead
	global tStartProgram
	global serialNumberToDevId, devIdToSerialNumber
	global busMasterToGPIO, gpioUsed
	global retData, threadCMD, readQueue
	global sendMetaData

	data = {}
	if sensor not in sensors:		return data, False
	if len(sensors[sensor]) == 0:	return data, False

	doPrint = False
	doPrint1 = False
	doPrint2 = False
	doPrint3= False
	doPrint4= False
	doPrint5= False
	doPrint6= False
	foundId = -1
	needToReset = False

	threadCMD = {}
	readQueue = {}
	sensorOnBusmaster = {}
	retData = {"state":"init","data":{}, "totalGoodSensors":0 }

	try:
		tStart = time.time()
		data[sensor] = {}
		gpioUsed =  "-1"
		try:
			if doPrint: U.logger.log(20,"starting new read of sensors".format())
			ret = {}
			linesDir = readPopen("ls -o /sys/bus/w1/devices/")[0].strip("\n").split("\n")
			"""
this looks like:
lrwxrwxrwx 1 root 0 Aug 29 02:06 28-000d770e64ff -> ../../../devices/w1_bus_master4/28-000d770e64ff
..
lrwxrwxrwx 1 root 0 Aug 29 02:06 28-3ce10457da57 -> ../../../devices/w1_bus_master1/28-3ce10457da57
lrwxrwxrwx 1 root 0 Aug 29 02:06 28-0516b33a17ff -> ../../../devices/w1_bus_master3/28-0516b33a17ff
lrwxrwxrwx 1 root 0 Aug 29 02:06 28-3ce104570a38 -> ../../../devices/w1_bus_master2/28-3ce104570a38
...
lrwxrwxrwx 1 root 0 Aug 29 02:06 w1_bus_master1 -> ../../../devices/w1_bus_master1
...
looking for the string at the end, eg: 28-3ce104570a38 and bus master # here 1..4 
			"""
			lines1 = 0
			for line in linesDir:
				if line.find("/devices/w1_") >- 1:  
					busMaster= (line.split("/devices/w1_bus_master")[1].split("/"))[0]  # will [[have busmaster, serial number] ...] 
					if busMaster not in readQueue:
						if doPrint1: U.logger.log(20, "{:>5.2f}..adding busmaster to threads  {}".format(time.time()-tStart, busMaster))
						sensorOnBusmaster[busMaster] = 0
						readQueue[busMaster] = Queue.Queue()
						threadCMD[busMaster] = {}
						threadCMD[busMaster]["thread"]  = threading.Thread(name=u'readOneChannel', target=readOneChannel, args=(busMaster,))
						threadCMD[busMaster]["state"]   = "collecting"
						threadCMD[busMaster]["thread"].start()
					if line.find("/28-") > -1 and line.find("/devices/w1_") > -1:  
						sn = (line.split("/devices/w1_bus_master")[1].split("/"))[1]  # will [[have busmaster, serial number] ...] 
						lines1 += 1
						if doPrint1: U.logger.log(20, "{:>5.2f}.. filling queue with busmaster:{}  sn:{},  gpio:{:>2}, devId:{:} ,".format(time.time()-tStart, busMaster, sn, busMasterToGPIO.get(busMaster,"-1"), serialNumberToDevId.get(sn,"-1")))
						readQueue[busMaster].put((sn, serialNumberToDevId.get(sn,"-1"), busMasterToGPIO.get(busMaster,"-1")))
						sensorOnBusmaster[busMaster] += 1
			mklist =""
			for ii in sensorOnBusmaster:
				mklist += "{}:{},{}; ".format(ii, sensorOnBusmaster.get(ii,""), busMasterToGPIO.get(ii,""))
			if doPrint: U.logger.log(20, "{:>5.2f}.. done with filling threads found :{} sensors, busM: Nsens,Gpio: {}".format(time.time()-tStart, lines1, mklist))

		except  Exception as e:
			U.logger.log(20,"v2", exc_info=True)
			U.logger.log(20, "return  value: data={}".format(data))
			retData = {} 
			return {}, needToReset


		for xx in sensors[sensor]:
			devId0 = xx
			break# get any key 

		if doPrint2: U.logger.log(20, "{:>5.2f}.. 1 ".format(time.time()-tStart))

		for busMaster in threadCMD:
			threadCMD[busMaster]["state"]   = "filled"
		if doPrint2: U.logger.log(20, "{:>5.2f}.. 2  filled ".format(time.time()-tStart))

		startRead = time.time()
		stillRunning = True
		while time.time() - startRead < 20:
			time.sleep(0.1)
			if not stillRunning: break 
			stillRunning = False
			for busMaster in threadCMD:
				if threadCMD[busMaster]["state"] != "finished": 
					if doPrint1: U.logger.log(20,"{:>5.2f}..  not finished busMaster:{}, State:{}".format(time.time()-tStart, busMaster, threadCMD[busMaster]["state"]))
					stillRunning = True
					break 

		for busMaster in threadCMD:
			if threadCMD[busMaster]["state"] != "finished": 
				threadCMD[busMaster]["state"] = "cleanup"
		time.sleep(0.2)
		if doPrint2: U.logger.log(20, "{:>5.2f}.. 3 ".format(time.time()-tStart))

		for busMaster in copy.copy(threadCMD):
			threadCMD[busMaster]["thread"] .join()
			del threadCMD[busMaster]
		if doPrint2: U.logger.log(20, "{:>5.2f}.. 4 ".format(time.time()-tStart))


		missingDevId = copy.copy(devIdToSerialNumber)
		for busMaster in retData["data"]:
			for serialNumber in retData["data"][busMaster]:
				if retData["data"][busMaster][serialNumber].get("temp",-991) > -800. and retData["data"][busMaster][serialNumber].get("temp",991) < 800.:
					if retData["data"][busMaster][serialNumber]["devId"]  in devIdToSerialNumber: del missingDevId[retData["data"][busMaster][serialNumber]["devId"]]

		if missingDevId != {}:
			for devId in missingDevId:
				if doPrint: U.logger.log(20,"{:>5.2f}..  missing devId:{},  serialNumber:{}".format(time.time()-tStart, devId, missingDevId[devId] ))


		if doPrint: U.logger.log(20,"{:>5.2f}..  all finished  .. #of busMasters:{}, totalGoodSensors:{}".format(time.time()-tStart, len(retData["data"]), retData["totalGoodSensors"], retData["data"]))

		sendMetaData += 1
		count1 = 0
		for busMaster in retData["data"]:
			for serialNumber in retData["data"][busMaster]:
				count1 +=1
				# good read?
				if retData["data"][busMaster][serialNumber]["temp"] < -900 or retData["data"][busMaster][serialNumber]["temp"] > 900:  # no good
					continue

				temp = retData["data"][busMaster][serialNumber]["temp"] 
				devId = retData["data"][busMaster][serialNumber]["devId"] 
				gpioUsed = retData["data"][busMaster][serialNumber]["gpioUsed"] 

				if "serialNumber" not in sensors[sensor][devId0]: sensors[sensor][devId0]["serialNumber"] = "0"

				#  first device foud send back and return
				if "serialNumber" in sensors[sensor][devId0] and sensors[sensor][devId0]["serialNumber"].find("28-") == -1:
						data[sensor][devId0] = {"temp":[{serialNumber:round(temp,1)}]} # not registered in indigo yet, add first one to it 
						sensors[sensor][devId0]["lastGoodData"] = time.time()
				
						if doPrint: U.logger.log(20,"return 1".format())
						return data, needToReset

				# existing devices 
				elif "serialNumber" in sensors[sensor][devId0]:
						iii = 0
						#if doPrint: U.logger.log(20,"{:>5.2f}..  serialNumber in sensors".format(time.time()-tStart))
						lastGoodRead[serialNumber] = {"time":time.time(), "temp":round(temp,1) ,  "busMaster":busMaster, "devId":devId}

						foundId = -1
						iii +=1
						devId = serialNumberToDevId.get(serialNumber,"-1") 
						if doPrint2: U.logger.log(20,"{:>5.2f}.. count1:{}, testing #{}, serialNumber:{}, devId:{}, ok?:{}".format(time.time()-tStart, count1, iii, serialNumber, devId,  devId != "-1" and devId not in data[sensor]))
						if devId != "-1" and devId not in data[sensor]: # normal case
							data[sensor][devId] = {}
							offset = float(sensors[sensor][devId].get("offsetTemp",0.))
							data[sensor][devId]["temp"] = [{serialNumber:round(temp+offset,1) }]
							if devId in lastBadRead and len(lastBadRead[devId]) == 3:
									if len(lastBadRead[devId]["dt"] ) > 0:
										data[sensor][devId]["lastBadRead"] = lastBadRead[devId]["dt"] 
							if (sendMetaData % 10) == 0:
								if gpioUsed != "-1":
									data[sensor][devId]["gpioUsed"] = gpioUsed
								data[sensor][devId]["busMaster"] = busMaster
								if len(lastResetDateTime) > 5:
									data[sensor][devId]["lastReset"] = lastResetDateTime
							foundId = devId
							lastGoodRead[serialNumber]["devId"] = devId
					
						else: # devid not found check if missing ..
							for devId in sensors[sensor]:
								
								if doPrint2: U.logger.log(20,"not found, looking at #:{}, devId:{}, sens: {}".format(count1,  devId, sensors[sensor][devId]))
					
								if "serialNumber" in sensors[sensor][devId] and serialNumber == sensors[sensor][devId]["serialNumber"]:
									if devId not in data[sensor]: data[sensor][devId] = {}
									if "temp" not in data[sensor][devId] : 
										#print devId,serialNumber, data[sensor][devId],  "adding temp"
										data[sensor][devId]["temp"] = []
									data[sensor][devId]["temp"].append({serialNumber:temp})
									if busMaster != "":
										data[sensor][devId]["busMaster"] = busMaster
									if doPrint2: U.logger.log(20,"serialNumber found at devId:{}, lastREset:{}".format(devId, lastResetDateTime))
									foundId = devId
									lastGoodRead[serialNumber]["devId"] = devId
									break
				
							if foundId == -1:
								if  oneWireAddNewSensors == "1":
									if doPrint: U.logger.log(20,"{:>5.2f}.. serialNumber:{}, not found, adding to devId0:{}".format(time.time()-tStart, serialNumber,devId0))
									if devId0 not in data[sensor]:		 data[sensor][devId0] = {}
									if "temp" not in data[sensor][devId0]: data[sensor][devId0]["temp"] = []
									data[sensor][devId0]["temp"].append({serialNumber:temp}) # not registered in indigo yet, add it to the last devId
									if doPrint2: U.logger.log(20,"{:>5.2f}..  serialNumber:{}, not found, adding to devId0:{}, data:{}".format(time.time()-tStart,serialNumber,devId0,data[sensor][devId0]["temp"]))
								else:
									if doPrint2: U.logger.log(20,"{:>5.2f}..  serialNumber:{}, not found, ignoring, oneWireAddNewSensors:{}".format(time.time()-tStart,serialNumber, oneWireAddNewSensors))
									#print "2", devId0, data[sensor][devId0]
				
				
				if foundId in badSensors: del badSensors[devId]
				time.sleep(0.1)
		else:
				data = incrementBadSensor(devId0,sensor,data,text="badSensor, no info")

	except  Exception as e:
		U.logger.log(20,"v2", exc_info=True)
	
	#check if we need to use older data, just in case we did not read a specific sensor
	try:
		for serialNumber in lastGoodRead:
			devId = lastGoodRead[serialNumber].get("devId","-1")
			# aignore this sensor?
			#if doPrint: U.logger.log(20,"check if we need to use old data serialNumber:{},".format(serialNumber))

			#  data needed for this sensor?
			if devId not in devIdToSerialNumber:	
				continue

			#U.logger.log(20,"... :{},".format(devId))
			#  data found this round?
			if devId in data[sensor]: 
					continue

			if doPrint3: U.logger.log(20,"{:>5.2f}..  no current data for devId:{}".format(time.time()-tStart,devId))

			# if too old: ignore
			if time.time() - lastGoodRead[serialNumber]["time"] > 20:
				#if doPrint: U.logger.log(20,"... : previous found data to old".format())
				continue

			# backfill with previous data 
			backFill = {"temp":[{serialNumber:lastGoodRead[serialNumber]["temp"]}]}
 
			if doPrint3: U.logger.log(20,"... : backfill with :{}, from {:.0f} secs ago".format(backFill, time.time()- lastGoodRead[serialNumber]["time"]))
			data[sensor][devId] = backFill
	except  Exception as e:
		U.logger.log(20,"v2", exc_info=True)

	try:
		# check if sensor listed is not available, if yes then send a -991, after things are settled down  (100 secs)
		if time.time() - tStartProgram > 20:
			for devId in devIdToSerialNumber:
				if doPrint5: U.logger.log(20,"{:>5.2f}.. checking devId:{} if present in data3".format(time.time()-tStart, devId))
				if devId in data[sensor]: 
					lastBadRead[devId] = {}
					continue

				serialNumber = devIdToSerialNumber[devId]
				data[sensor][devId] = {"temp":[{serialNumber:-993}]}

				needToReset = True
				if lastBadRead[devId]  == {}:
					lastBadRead[devId] = {"ts":time.time(), "datetime":datetime.datetime.now(),"dt":""}

				lastBadRead[devId]["dt"] = "{}+{:.0f}[secs]".format( lastBadRead[devId]["datetime"].strftime(_defaultDateStampFormat), time.time()-lastBadRead[devId]["ts"] )
				data[sensor][devId]["lastBadRead"] = lastBadRead[devId]["dt"] 
				if doPrint6: U.logger.log(20,"{:>5.2f}.. missing devId:{}, sn:{}".format(time.time()-tStart, devId, serialNumber))


	except  Exception as e:
		U.logger.log(20,"v2", exc_info=True)


	if doPrint5: U.logger.log(20,"{:5.2f}.., return final data:{}".format(time.time()-tStart, data))
	if sensor in data and data[sensor] == {}: del data[sensor]
	
	return data, needToReset	




# ===========================================================================
def incrementBadSensor(devId,sensor,data,text="badSensor"):
	global badSensors
	try:
		if devId not in badSensors:badSensors[devId] ={"count":0,"text":text}
		badSensors[devId]["count"] +=1
		badSensors[devId]["text"]  +=text
		#print badSensors
		if  badSensors[devId]["count"]  > 2:
			if sensor not in data: data={sensor:{devId:{}}}
			if devId not in data[sensor]: data[sensor][devId]={}
			data[sensor][devId]["badSensor"] = badSensors[devId]["text"]
			del badSensors[devId]
	except  Exception as e:
		U.logger.log(20,"v2", exc_info=True)
	return data 


		
# ===========================================================================
# sensor end
# ===========================================================================

 
# ===========================================================================
# read params
# ===========================================================================


def readParams():
		global sensorList, sensors, sendToIndigoSecs,enableTXpinsAsGpio,enableSPIpinsAsGpio, sensorRefreshSecs
		global output
		global tempUnits, pressureUnits, distanceUnits
		global oldRaw, lastRead
		global clockLightSensor
		global oneWireAddNewSensors
		global serialNumberToDevId, devIdToSerialNumber
		global oneWireResetGpio, oneWireResetIsUpDown, lastBadRead, oneWireGpios, oneWireGpiosOld, oneWireForceReboot

		rCode= False
		#U.logger.log(20," reading params")

		

		inp,inpRaw,lastRead2 = U.doRead(lastTimeStamp=lastRead)
		if inp == "": return rCode
		if lastRead2 == lastRead: return rCode
		lastRead  = lastRead2
		if inpRaw == oldRaw: return 
		oldRaw	 = inpRaw

		oldSensor  = sensorList
		sensorsOld = copy.copy(sensors)
		oneWireGpiosOld = oneWireGpios

		#U.logger.log(20," read   params")

		U.getGlobalParams(inp)
		if "enableSPIpinsAsGpio"	in inp: enableSPIpinsAsGpio=	(inp["enableSPIpinsAsGpio"])
		if "enableTXpinsAsGpio"		in inp: enableTXpinsAsGpio=	 	(inp["enableTXpinsAsGpio"])
		if "output"					in inp: output=					(inp["output"])
		if "tempUnits"				in inp: tempUnits=				(inp["tempUnits"])
		if "pressureUnits"			in inp: pressureUnits=			(inp["pressureUnits"])
		if "distanceUnits"			in inp: distanceUnits=			(inp["distanceUnits"])
		if "sensors"				in inp: sensors =				(inp["sensors"])
		if "sensorRefreshSecs"		in inp: sensorRefreshSecs = 	float(inp["sensorRefreshSecs"])
		if "oneWireAddNewSensors" 	in inp: oneWireAddNewSensors = 	(inp["oneWireAddNewSensors"])
		oneWireForceReboot = 	int(inp.get("oneWireForceReboot","-1"))

		oneWireGpios = 	inp.get("oneWireGpios","").replace(" ",",")
		oneWireGpios = oneWireGpios.split(",")
		if oneWireGpiosOld != [] and oneWireGpiosOld != oneWireGpios:
			U.restartMyself(reason="new gpio parameters")


		sensorList = ""
		for sensor in sensors:
			sensorList+=sensor.split("-")[0]+","
		if sensorList.find(G.program) == -1:
			U.logger.log(20,"{} not defined in parameters, exiting  ".format(G.program))
			exit()

		devIdToSerialNumber = {}
		serialNumberToDevId = {}
		for devId in sensors[G.program]:
			if "serialNumber" in sensors[G.program][devId]:
				serialNumberToDevId[sensors[G.program][devId]["serialNumber"]] = devId
				devIdToSerialNumber[devId] = sensors[G.program][devId]["serialNumber"]
			if devId not in lastBadRead:
				lastBadRead[devId] = {}

		U.logger.log(20,"serialNumberToDevId:{}  ".format(serialNumberToDevId))


		oneWireResetGpio = 		inp.get("oneWireResetGpio","")
		oneWireResetIsUpDown = 	inp.get("oneWireResetIsUpDown","up")
		try: 
			oneWireResetGpio = int(oneWireResetGpio)
			upDown = oneWireResetIsUpDown == "up"
			GPIO.setup(oneWireResetGpio, GPIO.OUT)
			GPIO.output(oneWireResetGpio, not upDown)
		except: pass


		return




#################################
#################################
#################################
#################################
#################################
#################################
#################################
#################################
def execWire():			 
	global sensorList, sensors,badSensors
	global enableTXpinsAsGpio,enableSPIpinsAsGpio
	global tempUnits, pressureUnits, distanceUnits
	global regularCycle
	global oldRaw, lastRead
	global sensorRefreshSecs
	global oneWireAddNewSensors
	global lastGoodRead
	global tStartProgram
	global serialNumberToDevId
	global gpioUsed
	global lastmapBusmasterToGpio, busMasterToGPIO
	global devIdToSerialNumber, serialNumberToDevId
	global oneWireResetGpio, oneWireResetIsUpDown
	global lastReset, noResetBefore, lastBadRead
	global resetTime, lastResetDateTime, sendMetaData
	global oneWireGpios,oneWireGpiosLast
	global resetCounter, oneWireForceReboot

	oneWireForceReboot		= -1
	resetCounter			= 0
	oneWireGpiosLast		= "//"
	oneWireGpios			= []
	oneWireResetIsUpDown	= "up"
	lastBadRead				= {}
	sendMetaData			= 0
	lastResetDateTime		= ""
	oneWireResetGpio		= 23
	oneWireResetIsUpDown	= "up"
	lastReset				= 0
	noResetBefore			= 20
	resetTime				= 15
	devIdToSerialNumber		= {}
	serialNumberToDevId		= {}
	busMasterToGPIO			= {}
	lastmapBusmasterToGpio	= 0
	gpioUsed				= {}
	lastGoodRead			= {}
	serialNumberToDevId		= {}
	oneWireAddNewSensors	="0"
	sensorRefreshSecs   	= 90
	oldRaw			  		= ""
	lastRead				= 0
	tempUnits		   		="Celsius"
	loopCount		   		= 0
	sensorList		  		= ""
	sensors			 		= {}
	enableTXpinsAsGpio  	= "0"
	enableSPIpinsAsGpio 	= "0"
	authentication	  		= "digest"
	quick			   		= False
	output			  		= {}
	U.setLogging()

	myPID	   = str(os.getpid())
	U.killOldPgm(myPID,G.program+".py")# kill old instances of myself if they are still running


	readParams()

	if U.getIPNumber() > 0:
		U.logger.log(20,"getsensors no ip number  exiting ")
		time.sleep(10)
		exit()

	U.echoLastAlive(G.program)
	enableoneWireGPIO()
	U.echoLastAlive(G.program)

	NSleep= int(sensorRefreshSecs)
	if G.networkType  in G.useNetwork and U.getNetwork() == "off": 
		if U.getIPNumber() > 0:
			U.logger.log(20,"no ip number working, giving up")
			time.sleep(10)

	eth0IP, wifi0IP, G.eth0Enabled,G.wifiEnabled = U.getIPCONFIG()

	tStartProgram 		= time.time()
	tt				  	= time.time()
	badSensors		  	= {}
	lastData			= {}
	lastMsg				 = 0
	G.tStart			= tt
	lastregularCycle	= tt
	lastRead			= tt
	regularCycle		= True
	lastData			= {}
	xxx				 	= -1
	doPrint 			= False

	sens = G.program

	mapBusmasterToGpio()

	while True:
		try:
			data = {}
			needToReset = False
	   
			if regularCycle:
				if sens	 in sensors: data, needToReset = get18B20(sens)
			if doPrint: U.logger.log(20," data :{}".format(data))

			loopCount +=1
		
			delta =-1
			changed = 0

			if  time.time()-lastMsg >  G.sendToIndigoSecs  or time.time()-lastMsg > 200:	 
				changed = 1

			else:
				if lastData == {}: 
					changed = 2
				else:
					if sens not in lastData:
						changed = 2
					else:
						if sens not in data: continue
						for devid in data[sens]:
							if changed > 0: 
								break
							if devid not in lastData[sens]:
								changed  = 3
								break
							if "temp" in data[sens][devid]: 
								if "temp" not in lastData[sens][devid]:
									changed =  5
									break
							if "busMaster" in data[sens][devid]: 
									changed =  6
									break
							if "lastBadRead" in data[sens][devid]: 
									changed =  7
									break

							#print dd, lastData[sens][dd], data[sens][dd]
							if "temp" not in data[sens][devid]:
									changed = 8
									break
							nSens = len(data[sens][devid]["temp"])
							if nSens != len(lastData[sens][devid]["temp"]):
								changed = 9
								break
							try:
								for nnn in range(nSens):
									for serialNumber in data[sens][devid]["temp"][nnn]:
										if serialNumber in lastData[sens][devid]["temp"][nnn]: 
											#U.logger.log(20, " changed indicator:{}, sending url: {}".format(changed, data))
											xxx = U.testBad( data[sens][devid]["temp"][nnn][serialNumber], lastData[sens][devid]["temp"][nnn][serialNumber], xxx )
											if xxx > (G.deltaChangedSensor/100.): 
												changed = xxx
												break
										else:
											changed = 10
											break
							except  Exception as e:
								U.logger.log(20,"v2", exc_info=True)
								#print e
								#print lastData[sens][dd]
								#print data[sens][dd]
								changed = 7
								break

			if data != {} and changed > 0:
				lastMsg = time.time()
				lastData = copy.copy(data)
				try:
					U.sendURL({"sensors":copy.deepcopy(data)})
				except  Exception as e:
					U.logger.log(20,"v2", exc_info=True)
				time.sleep(.05)

			quick = U.checkNowFile(G.program)				

			for sensor in data:
				for devId in data[sensor]:
					#U.logger.log(20,"dev:{}, {}".format(devId, data[sensor][devId]))
					if sensor in sensors:
						if devId in sensors[sensor]:
							data[sensor][devId]["name"] = sensors[sensor][devId]["name"]
			U.makeDATfile(G.program, {"sensors":data})
			U.echoLastAlive(G.program)
			checkIfReset(needToReset)


			tt= time.time()
			NSleep = int(sensorRefreshSecs)
			if tt- lastregularCycle > sensorRefreshSecs:
				regularCycle = True
				lastregularCycle  = tt

			for n in range(NSleep):
				if quick: break

				mapBusmasterToGpio()

				readParams()

				time.sleep(1)
				quick = U.checkNowFile(G.program)				
				if tt - lastRead > 5:
					lastRead = tt
					U.checkIfAliveNeedsToBeSend()
		except  Exception as e:
			U.logger.log(20,"v2", exc_info=True)
			time.sleep(5.)


####### start here #######
execWire()
		
try: 	G.sendThread["run"] = False; time.sleep(1)
except: pass
		
sys.exit(0)		   
