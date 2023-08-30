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
##     /sys/bus/w1/devices/<<sn>>/w1_slav
##
##  also read config.txt to get a map of buschannel to GPIO mapping
##  
##  then send every xx secs or if change data to indigo through socket or http.
##
##

## ==========>> ok for py3

import math

import  sys, os, time, json, datetime,subprocess,copy

sys.path.append(os.getcwd())
import  piBeaconUtils   as U
import  piBeaconGlobals as G

G.program = "Wire18B20"


####-------------------------------------------------------------------------####
def readPopen(cmd):
		try:
			ret, err = subprocess.Popen(cmd, shell=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE).communicate()
			return ret.decode('utf_8'), err.decode('utf_8')
		except Exception as e:
			U.logger.log(20,"", exc_info=True)



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
# 18B20
# ===========================================================================
def get18B20(sensor, data):
	global sensors, addNewOneWireSensors
	global lastGoodRead
	global tStartProgram
	global serialNumberToDevId
	global busMasterToGPIO, gpioUsed


	if sensor not in sensors:	return data 
	if len(sensors[sensor]) == 0:return data 

	doPrint = False
	doPrint1 = False
	doPrint2 = False
	doPrint3= False
	doPrint4= False
	doPrint5= False
	foundId = -1
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
			devs = []
			lines1 = 0
			for line in linesDir:
				if line.find("/28-") > -1 and line.find("/devices/w1_") >- 1:  
					lines1 += 1
					devs.append(line.split("/devices/w1_bus_master")[1].split("/"))  # will [[have busmaster, serial number] ...] 
			if doPrint1: U.logger.log(20, "{:>5.2f}.. getting data N:{}, {}".format(time.time()-tStart,len(devs), devs))

			busMaster = ""
			lines = 0
			for dev in devs:
				try:
					busMaster, sn  = dev
					devId   = serialNumberToDevId.get(sn,"-1")
					gpioUsed = busMasterToGPIO.get(busMaster,"-1")
					if doPrint: U.logger.log(20,"{:>5.2f}.. dev#:{:>2d}/{:<2d},  devId:{:>12s},  busMaster#{}, GPIO:{} sn:{}".format(time.time()-tStart, lines+1, lines1, devId, busMaster, gpioUsed , sn))

					# now read the values for each sensor
					if not os.path.isfile("/sys/bus/w1/devices/"+sn+"/w1_slave"): continue
					f = open("/sys/bus/w1/devices/"+sn+"/w1_slave","r")
					dataW = f.read().strip("\n").split("\n")
					f.close()
					# finished reading
					if doPrint: U.logger.log(20,"{:>5.2f}.. data: {}".format(time.time()-tStart, dataW))
					##59 01 ff ff 7f ff ff ff 82 : crc=82 YES
					##59 01 ff ff 7f ff ff ff 82 t=21562

					# now checking if ok. first find yes, then check crc, then get Temp value
					if len(dataW) == 2:
						if "YES" in dataW[0]:
							crc =  int(dataW[0].split("crc=")[1].split(" ")[0],16)    #  == crc=82 
							crccheck = crc8(dataW[0].split(" :")[0].split(" ")[0:8])  #  input: 59 01 ff ff 7f ff ff ff
							if doPrint1: U.logger.log(20,"{:>5.2f}.. crc:{}, crccheck:{}".format(time.time()-tStart, crc, crcInt))
							if crc != crccheck:
								if doPrint: U.logger.log(20,"{:>5.2f}.. bad data, crc check failed".format(time.time()-tStart))
							else:
								t1 = dataW[1].split("t=")
								if len(t1) == 2:
									try:	
										lines += 1
										ret[sn] = [round(float(t1[1])/1000.,1),  busMaster, serialNumberToDevId.get(sn,"-1"), gpioUsed ]
									except:	
										if doPrint: U.logger.log(20,"{:>5.2f}.. bad data: {}".format(time.time()-tStart, dataW))
								else:
									if doPrint: U.logger.log(20,"{:>5.2f}.. bad data: {}".format(time.time()-tStart, dataW))
						else:
							if doPrint: U.logger.log(20,"{:>5.2f}.. bad data: {}".format(time.time()-tStart, dataW))

								##ret[line] = ("%.2f"%(float(t1[1])/1000.)).strip()
				except  Exception as e:
					U.logger.log(30,"", exc_info=True)


			tempList = ret # {"28-800000035de5": 21.6, ...}  
		except  Exception as e:
			U.logger.log(30,"", exc_info=True)
			U.logger.log(30, u"return  value: data={}".format(data))
			tempList = {} 

		for xx in sensors[sensor]:
			devId0 = xx
			break# get any key 

		if doPrint: U.logger.log(20,"{:>5.2f}.. found :{}/{} good sensors, devId0:{} (used for new sensors found to send to indigo)".format(time.time()-tStart, lines, lines1, devId0, tempList))

		if tempList != {}:
			if "serialNumber" not in sensors[sensor][devId0]: sensors[sensor][devId0]["serialNumber"] = "0"
			if "serialNumber" in sensors[sensor][devId0] and sensors[sensor][devId0]["serialNumber"].find("28-") == -1: # new sensors 
				for xx in tempList:
					ss = xx[0]
					busMaster = xx[1]
					devId = xx[2]
					data[sensor][devId0] = {"temp":[{ss:tempList[ss][0]}]} # not registered in indigo yet, add first one to it 
					sensors[sensor][devId0]["lastGoodData"] = time.time()
					
					if doPrint: U.logger.log(20,"return 1".format())
					return data

			# old 
			elif "serialNumber" in sensors[sensor][devId0]:
				iii = 0
				#if doPrint: U.logger.log(20,"{:>5.2f}..  serialNumber in sensors".format(time.time()-tStart))
				for serialNumber in tempList:
					if len(tempList[serialNumber]) == 4:
						lastGoodRead[serialNumber] = {"time":time.time(), "temp":tempList[serialNumber][0], "devId":tempList[serialNumber][1], "busMaster":tempList[serialNumber][2], "devId":tempList[serialNumber][3]}
					else:
						continue

					foundId = -1
					iii +=1
					devId = serialNumberToDevId.get(serialNumber,"-1") 
					if doPrint4: U.logger.log(20,"{:>5.2f}.. testing #{}/{}, serialNumber:{}, devId:{}, tempList:{}, devidInData:{}".format(time.time()-tStart, iii, lines, serialNumber,serialNumberToDevId.get(serialNumber,"-1"), tempList[serialNumber], devId in data[sensor]))
					if devId != "-1" and devId not in data[sensor]:
						data[sensor][devId] = {}
						data[sensor][devId]["temp"] = [{serialNumber:tempList[serialNumber][0]}]
						data[sensor][devId]["gpioUsed"] = tempList[serialNumber][3] 
						if tempList[serialNumber][1] != "":
							data[sensor][devId]["busMaster"] = tempList[serialNumber][1]
						if doPrint1: U.logger.log(20,"{:>5.2f}.. {:>2d}/{}: serialNumber {} found in serialNumberToDevId:{}".format(time.time()-tStart, iii, len(tempList), serialNumber, devId))
						foundId = devId
						lastGoodRead[serialNumber]["devId"] = devId
						
					else: # need to a check of the dicts 
						for devId in sensors[sensor]:
							#if doPrint: U.logger.log(20,"looking at devId:{}, sens: {}".format( devId, sensors[sensor][devId]))
						
							if "serialNumber" in sensors[sensor][devId] and serialNumber == sensors[sensor][devId]["serialNumber"]:
								try:	 tempList[serialNumber][0]  = round(  float(tempList[serialNumber][0]) + float(sensors[sensor][devId]["offsetTemp"]) ,1)
								except:  pass
								if devId not in data[sensor]: data[sensor][devId] = {}
								if "temp" not in data[sensor][devId] : 
									#print devId,serialNumber, data[sensor][devId],  "adding temp"
									data[sensor][devId]["temp"] = []
								data[sensor][devId]["temp"].append({serialNumber:tempList[serialNumber][0]})
								if tempList[serialNumber][1] != "":
									data[sensor][devId]["busMaster"] = tempList[serialNumber][1]
								#if doPrint: U.logger.log(20,"serialNumber found at devId:{}".format(devId))
								foundId = devId
								lastGoodRead[serialNumber]["devId"] = devId
								break
					
						if foundId == -1:
							if  addNewOneWireSensors == "1":
								if doPrint: U.logger.log(20,"{:>5.2f}.. serialNumber:{}, not found, adding to devId0:{}".format(time.time()-tStart, serialNumber,devId0))
								if devId0 not in data[sensor]:		 data[sensor][devId0] = {}
								if "temp" not in data[sensor][devId0]: data[sensor][devId0]["temp"] = []
								data[sensor][devId0]["temp"].append({serialNumber:tempList[serialNumber][0]}) # not registered in indigo yet, add it to the last devId
								if doPrint: U.logger.log(20,"{:>5.2f}..  serialNumber:{}, not found, adding to devId0:{}, data:{}".format(time.time()-tStart,serialNumber,devId0,data[sensor][devId0]["temp"]))
							else:
								if doPrint: U.logger.log(20,"{:>5.2f}..  serialNumber:{}, not found, ignoring, addNewOneWireSensors:{}".format(time.time()-tStart,serialNumber, addNewOneWireSensors))
								#print "2", devId0, data[sensor][devId0]
				
				
				if foundId in badSensors: del badSensors[devId]
				time.sleep(0.1)
		else:
				data = incrementBadSensor(devId0,sensor,data,text="badSensor, no info")

	except  Exception as e:
		U.logger.log(30,"", exc_info=True)
	
	#check if we need to use older data, just in case wedid not read a specific sensor
	try:
		for serialNumber in lastGoodRead:
			devId = lastGoodRead[serialNumber].get("devId","-1")
			# aignore this sensor?
			#if doPrint: U.logger.log(20,"check if we need to use old data serialNumber:{},".format(serialNumber))

			#  data needed for this sensor?
			if devId not in sensors[sensor]:	
				continue

			#U.logger.log(20,"... :{},".format(devId))
			#  data found this round?
			if devId in data[sensor]: 
					continue

			if doPrint3: U.logger.log(20,"{:>5.2f}..  no current data for devId:{}".format(time.time()-tStart,devId))

			# if too old: ignore
			if time.time() - lastGoodRead[serialNumber]["time"] > 60:
				#if doPrint: U.logger.log(20,"... : previous found data to old".format())
				continue

			# backfill with previous data 
			backFill = {"temp":[{serialNumber:lastGoodRead[serialNumber]["temp"]}], "busMaster":lastGoodRead[serialNumber]["busMaster"]}
 
			if doPrint3: U.logger.log(20,"... : backfill with :{}, from {:.0f} secs ago".format(backFill, time.time()- lastGoodRead[serialNumber]["time"]))
			data[sensor][devId] = backFill
	except  Exception as e:
		U.logger.log(30,"", exc_info=True)

	try:
		# check if sensor listed is not available, if yes then send a -991, after things are settled down  (2 minutes)
		if time.time() - tStartProgram > 60:
			for devId in sensors[sensor]:
				if doPrint2: U.logger.log(20,"{:>5.2f}.. checking devId:{}if present in data3".format(time.time()-tStart, devId,))
				if devId in data[sensor]: continue
				serialNumber = sensors[sensor][devId] ["serialNumber"]
				data[sensor][devId] = {"temp":[{serialNumber:-9993}]}
				if doPrint2: U.logger.log(20,"{:>5.2f}.. setting temp of devId:{}, sN:{}, to -999".format(time.time()-tStart, devId, serialNumber))
	except  Exception as e:
		U.logger.log(30,"", exc_info=True)


	if doPrint5: U.logger.log(20,"{:5.2f}.., return final data:{}".format(time.time()-tStart, data))
	if sensor in data and data[sensor] == {}: del data[sensor]
			
	return data	




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
		U.logger.log(30,"", exc_info=True)
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
		global addNewOneWireSensors
		global serialNumberToDevId

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
		if "addNewOneWireSensors" 	in inp: addNewOneWireSensors = 	(inp["addNewOneWireSensors"])


		sensorList = ""
		for sensor in sensors:
			sensorList+=sensor.split("-")[0]+","
		if sensorList.find(G.program) == -1:
			U.logger.log(30,"{} not defined in parameters, exiting  ".format(G.program))
			exit()

		serialNumberToDevId ={}
		for devId in sensors[G.program]:
			if "serialNumber" in sensors[G.program][devId]:
				serialNumberToDevId[sensors[G.program][devId]["serialNumber"]] = devId
		U.logger.log(20,"serialNumberToDevId:{}  ".format(serialNumberToDevId))

		return



def mapBusmasterToGpio():
	global busMasterToGPIO, lastmapBusmasterToGpio
	try:
		"""
looking  in /boot/config.txt for eg: 
dtoverlay=w1-gpio
dtparam=gpiopin=26   <-- this will be  busmaster 4
dtoverlay=w1-gpio
dtparam=gpiopin=5
dtoverlay=w1-gpio
dtparam=gpiopin=17
dtoverlay=w1-gpio
dtparam=gpiopin=4   <-- this will be  busmaster 1
		"""

		if time.time() - lastmapBusmasterToGpio < 60: return  
		doPrint = False
		lastmapBusmasterToGpio = time.time()
		busMasterToGPIOOld = copy.copy(busMasterToGPIO)
		f = open("/boot/config.txt","r")
		configTxt = f.read().split("\n")
		f.close
		pinsFound = []
		newMapping = False
		busMasterToGPIO = {}
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
			U.logger.log(20,"Changed or first mapping of busmaster channel to GPIO used:{} in \"ls -o /sys/bus/w1/devices/\" ".format(busMasterToGPIO))

	except  Exception as e:
		U.logger.log(30,"", exc_info=True)
		busMasterToGPIO = {}
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
	global addNewOneWireSensors
	global lastGoodRead
	global tStartProgram
	global serialNumberToDevId
	global gpioUsed
	global lastmapBusmasterToGpio, busMasterToGPIO

	busMasterToGPIO			= {}
	lastmapBusmasterToGpio	= 0
	gpioUsed				= {}
	lastGoodRead			= {}
	serialNumberToDevId		= {}
	addNewOneWireSensors	="0"
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

	readParams()

	if U.getIPNumber() > 0:
		U.logger.log(30,"getsensors no ip number  exiting ")
		time.sleep(10)
		exit()


	myPID	   = str(os.getpid())
	U.killOldPgm(myPID,G.program+".py")# kill old instances of myself if they are still running

	NSleep= int(sensorRefreshSecs)
	if G.networkType  in G.useNetwork and U.getNetwork() == "off": 
		if U.getIPNumber() > 0:
			U.logger.log(30,"no ip number working, giving up")
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
	   
			if regularCycle:
				if sens	 in sensors: data = get18B20(sens,	 data)
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
								try:
									#print dd, lastData[sens][dd], data[sens][dd]
									nSens = len(data[sens][devid]["temp"])
									if nSens != len(lastData[sens][devid]["temp"]):
										changed = 6
										break
									for nnn in range(nSens):
										for serialNumber in data[sens][devid]["temp"][nnn]:
											if serialNumber in lastData[sens][devid]["temp"][nnn]: 
												xxx = U.testBad( data[sens][devid]["temp"][nnn][serialNumber], lastData[sens][devid]["temp"][nnn][serialNumber], xxx )
												if xxx > (G.deltaChangedSensor/100.): 
													changed = xxx
													break
											else:
												changed = 7
												break
								except  Exception as e:
									U.logger.log(30,"", exc_info=True)
									#print e
									#print lastData[sens][dd]
									#print data[sens][dd]
									changed = 7
									break

			if data != {} and changed > 0:
				lastMsg = time.time()
				lastData = copy.copy(data)
				try:
					#U.logger.log(20, u" changed indicator:{}, sending url: {}".format(changed, data))
					U.sendURL({"sensors":data})
				except  Exception as e:
					U.logger.log(30,"", exc_info=True)
				time.sleep(0.05)

			quick = U.checkNowFile(G.program)				

			U.makeDATfile(G.program, {"sensors":data})
			U.echoLastAlive(G.program)


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
			U.logger.log(30,"", exc_info=True)
			time.sleep(5.)


####### start here #######
execWire()
		
try: 	G.sendThread["run"] = False; time.sleep(1)
except: pass
		
sys.exit(0)		   
