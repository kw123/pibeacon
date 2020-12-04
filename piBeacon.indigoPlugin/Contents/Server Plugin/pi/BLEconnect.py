#!/usr/bin/env python
# -*- coding: utf-8 -*-
# by Karl Wachs
# mar 2 2016
# version 0.95
##
##	 read BLE sensors and send http to indigo with data
#

##
import	sys, os, subprocess, copy
import	time,datetime
import	json
import  pexpect

try:
	import bluetooth
	import bluetooth._bluetooth as bt
	bluezPresent = True
except:
	bluezPresent = False

import struct
import array
import fcntl


sys.path.append(os.getcwd())
import	piBeaconUtils	as U
import	piBeaconGlobals as G
G.program = "BLEconnect"


#################################
def readParams():
		global debug, ipOfServer,myPiNumber,passwordOfServer, userIdOfServer, authentication,ipOfServer,portOfServer,sensorList,restartBLEifNoConnect
		global macList 
		global oldRaw, lastRead, BLEconnectMode
		global sensor
		global oneisBLElongConnectDevice

		inp,inpRaw,lastRead2 = U.doRead(lastTimeStamp=lastRead)
		if inp == "": return False
		if lastRead2 == lastRead: return False
		lastRead  = lastRead2
		if inpRaw == oldRaw: return False
		oldRaw	   = inpRaw

		oldSensor		  = sensorList

		try:

			U.getGlobalParams(inp)

			sensors = {}
			oneisBLElongConnectDevice = False
			if "sensors" in inp:	
				if "BLEconnect" in inp["sensors"]: 
					sensors["BLEconnect"] = copy.copy(inp["sensors"]["BLEconnect"])
				for ss in inp["sensors"]:
					#if ss == "BLEdirectMiTempHumSquare":	U.logger.log(30, u"1-ss:{} ".format(ss))
					oneActive = False
					for devId in inp["sensors"][ss]:
						#if ss == "BLEdirectMiTempHumSquare":	U.logger.log(30, u"1-devId:{} ".format(devId))
						if "isBLElongConnectDevice" in inp["sensors"][ss][devId] and inp["sensors"][ss][devId]["isBLElongConnectDevice"]:
							#if ss == "BLEdirectMiTempHumSquare":	U.logger.log(30, u"1-sensors[ss]:{} ".format(inp["sensors"][ss]))
							oneActive = True
							oneisBLElongConnectDevice = True
							if "isBLElongConnectDevice" not in sensors:
								sensors["isBLElongConnectDevice"] = {}
					if oneActive:
						sensors["isBLElongConnectDevice"][ss] = copy.copy(inp["sensors"][ss])

			if sensors == {}:
				U.logger.log(30, u" no {} definitions supplied in sensorList stopping (1)".format(sensor))
				exit()


			if "restartBLEifNoConnect"	in inp:	 restartBLEifNoConnect=		  (inp["restartBLEifNoConnect"])
			if "sensorList"				in inp:	 sensorList=				  (inp["sensorList"])

			if bluezPresent:
				if "BLEconnectMode"			in inp:	 BLEconnectMode=			  (inp["BLEconnectMode"])
			else:
				BLEconnectMode = "commandLine"

			macListNew={}

			if "BLEconnect" in sensors:
				for devId in sensors["BLEconnect"]:
					thisMAC = sensors["BLEconnect"][devId]["macAddress"]
					macListNew[thisMAC]={"type":"isBLEconnect",
										 "iPhoneRefreshDownSecs":float(sensors[devId]["iPhoneRefreshDownSecs"]),
										 "iPhoneRefreshUpSecs":float(sensors[devId]["iPhoneRefreshUpSecs"]),
										 "BLEtimeout":max(1.,float(sensors[devId]["BLEtimeout"])),
										 "up":False,
										 "lastTesttt":time.time()-1000.,
										 "lastMsgtt":time.time()-1000. ,
										 "lastData":{},
										 "triesWOdata": 0,
										 "quickTest": 0.,
										 "devId": devId }


					"""
					"BLEdirectMiTempHumSquare": {
					  "1610077898": {
						"isBLElongConnectDevice": true, 
						"mac": "A4:C1:38:C3:42:17", 
						"offsetHum": "0", 
						"offsetTemp": "0", 
						"updateIndigoTiming": "30"
					  }
					"""
			if "isBLElongConnectDevice" in sensors:
				CCC = sensors["isBLElongConnectDevice"]
				for ss in CCC: 	
					#if ss == "BLEdirectMiTempHumSquare":	U.logger.log(30, u"CCC:{} ".format(CCC))
					for devId in CCC[ss]:
						#if ss == "BLEdirectMiTempHumSquare":	U.logger.log(30, u"devId:{} ".format(devId))
						if "mac" in CCC[ss][devId]:
							thisMAC = CCC[ss][devId]["mac"]
							#if ss == "BLEdirectMiTempHumSquare":	U.logger.log(30, u"thisMAC:{} ".format(thisMAC))
							if thisMAC not in macListNew:
								macListNew[thisMAC]={"type":"isBLElongConnectDevice",
													 "updateIndigoTiming":60,
													 "readSensorEvery":120,
													 "lastTesttt":time.time()-1000.,
													 "lastMsgtt":time.time()-1000. ,
													 "lastData": {},
													 "up": False,
													 "offsetHum": 0,
													 "offsetTemp": 0.,
													 "devType": ss,
													 "badSensor": 0,
													 "triesWOdata": 0,
													 "quickTest": 0. ,
													 "devId": devId 
													 }


							if "readSensorEvery" in CCC[ss][devId]:
								try:	macListNew[thisMAC]["readSensorEvery"] = float(CCC[ss][devId]["readSensorEvery"])
								except: macListNew[thisMAC]["readSensorEvery"] = 120
							if "updateIndigoTiming" in CCC[ss][devId]:
								try:	macListNew[thisMAC]["updateIndigoTiming"] = float(CCC[ss][devId]["updateIndigoTiming"])
								except: macListNew[thisMAC]["updateIndigoTiming"] = 120

							if "offsetHum" in CCC[ss][devId]:
								try:	macListNew[thisMAC]["offsetHum"] = float(CCC[ss][devId]["offsetHum"])
								except: pass
							if "offsetTemp" in CCC[ss][devId]:
								try:	macListNew[thisMAC]["offsetTemp"] = float(CCC[ss][devId]["offsetTemp"])
								except: pass
					if ss =="BLEdirectMiTempHumSquare":	U.logger.log(30, u"macListNew:{} ".format(macListNew))

			for thisMAC in macListNew:
				if thisMAC not in macList:
					macList[thisMAC] = copy.copy(macListNew[thisMAC])
				else:
					if macList[thisMAC]["type"] == "BLEconnect": 
						macList[thisMAC]["iPhoneRefreshDownSecs"] = macListNew[thisMAC]["iPhoneRefreshDownSecs"]
						macList[thisMAC]["iPhoneRefreshUpSecs"]	  = macListNew[thisMAC]["iPhoneRefreshUpSecs"]
						macList[thisMAC]["BLEtimeout"]	 		  = macListNew[thisMAC]["BLEtimeout"]
					elif macList[thisMAC]["type"] == "isBLElongConnectDevice": 
						macList[thisMAC]["updateIndigoTiming"]	  = macListNew[thisMAC]["updateIndigoTiming"]

			delMac={}
			for thisMAC in macList:
				if thisMAC not in macListNew:
					delMac[thisMAC] = 1
			for	 thisMAC in delMac:
				del macList[thisMAC]

			if len(macList) == 0:
				U.logger.log(30, u"no BLEconnect - BLElongConnect devices supplied in parameters (2)")
				exit()

			return True
			
		except	Exception, e:
			U.logger.log(50,u"in Line {} has error={}".format(sys.exc_traceback.tb_lineno, e) )
		return False


#################################
def tryToConnectSocket(MAC,BLEtimeout,devId):
	global errCount, lastConnect

	if time.time() - lastConnect < 3: time.sleep( max(0,min(0.5,(3.0- (time.time() - lastConnect) ))) )

	retdata	 = {"rssi": -999, "txPower": -999,"flag0ok":0,"byte2":0}
	try:
		for ii in range(5):	 # wait until (wifi) sending is finsihed
			if os.path.isfile(G.homeDir + "temp/sending"):
				#print "delaying hci"
				time.sleep(0.5)
			else:
				 break

		hci_sock = bt.hci_open_dev(devId)
		hci_fd	 = hci_sock.fileno()

		# Connect to device (to whatever you like)
		bt_sock = bluetooth.BluetoothSocket(bluetooth.L2CAP)
		bt_sock.settimeout(BLEtimeout)

		try:
			result	= bt_sock.connect_ex((MAC, 1))	# PSM 1 - Service Discovery
			reqstr = struct.pack("6sB17s", bt.str2ba(MAC), bt.ACL_LINK, "\0" * 17)
			request = array.array("c", reqstr)
			handle = fcntl.ioctl(hci_fd, bt.HCIGETCONNINFO, request, 1)
			handle = struct.unpack("8xH14x", request.tostring())[0]
			cmd_pkt=struct.pack('H', handle)
			# Send command to request RSSI
			socdata = bt.hci_send_req(hci_sock, bt.OGF_STATUS_PARAM, bt.OCF_READ_RSSI, bt.EVT_CMD_COMPLETE, 4, cmd_pkt)
			bt_sock.close()
			hci_sock.close()
			flag0ok	  = struct.unpack('b', socdata[0])[0]
			txPower	  = struct.unpack('b', socdata[1])[0]
			byte2	  = struct.unpack('b', socdata[2])[0]
			rssi	  = struct.unpack('b', socdata[3])[0]
			#print MAC, test0, txPower, test2, signal
			retdata["flag0ok"]	= flag0ok
			retdata["byte2"]	= byte2
			if flag0ok == 0 and not (txPower == rssi and rssi == 0 ):
				retdata["rssi"]	= rssi
				retdata["txPower"]	= txPower
		except IOError:
			# Happens if connection fails (e.g. device is not in range)
			bt_sock.close()
			hci_sock.close()
			for ii in range(30):
				if os.path.isfile(G.homeDir+"temp/stopBLE"):
					time.sleep(5)
				else:
					break
			errCount += 1
			if errCount  < 10: return {}
			subprocess.call("rm {}temp/stopBLE > /dev/null 2>&1".format(G.homeDir), shell=True)
			U.logger.log(20, u"in Line {} has error ... sock.recv error, likely time out ".format(sys.exc_traceback.tb_lineno))
			U.restartMyself(reason="sock.recv error", delay = 10)

	except	Exception, e:
			U.logger.log(30, u"in Line {} has error={}".format(sys.exc_traceback.tb_lineno, e))
	U.logger.log(10, "{}:  {}".format(MAC, retdata))
	errCount = 0
	return retdata




#################################
def tryToConnectCommandLine(MAC,BLEtimeout):
	global errCount, lastConnect, useHCI

	if time.time() - lastConnect < 3: time.sleep( max(0,min(0.5,(3.0- (time.time() - lastConnect) ))) )
	retdata	 = {"rssi": -999, "txPower": -999,"flag0ok":0,"byte2":0}
	try:
		for ii in range(5):	 # wait until (wifi) sending is finished
			if os.path.isfile(G.homeDir + "temp/sending"):
				#print "delaying hci"
				time.sleep(0.5)
			else:
				 break
		# Connection timed out
		# Input/output error ok for 1. step, not ok for step 2
		#  stop:  "Device is not available."
	  #timeout -s SIGINT 5s hcitool cc  3C:22:FB:0F:D6:78; hcitool rssi 3C:22:FB:0F:D6:78; hcitool tpl 3C:22:FB:0F:D6:78
	  #sudo timeout -s SIGINT 5s hcitool -i hci0  cc  8C:86:1E:3D:5C:66;sudo hcitool -i hci0 rssi 8C:86:1E:3D:5C:66;sudo hcitool -i hci0 tpl 8C:86:1E:3D:5C:66
		for ii in range(2):
			cmd = "sudo timeout -s SIGINT {:.1f}s hcitool -i {}  cc {};sleep 0.2; hcitool -i {} rssi {} ;sleep 0.2;hcitool -i {} tpl {}".format(BLEtimeout, useHCI, MAC, useHCI,  MAC, useHCI, MAC)
			U.logger.log(10, cmd)
			ret = subprocess.Popen(cmd, shell=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE).communicate()
			parts = ret[0].strip("\n").split("\n")
			U.logger.log(10, "{}  1. try ret: {} --- err>>{}<<".format(MAC, ret[0].strip("\n"), ret[1].strip("\n")))

			found = False
			for line in parts:
					if line.find("RSSI return value:") >- 1:
						retdata["rssi"] = int(line.split("RSSI return value:")[1].strip())
						found = True
					if line.find("Current transmit power level:") > -1:
						retdata["txPower"] = int(line.split("Current transmit power level:")[1].strip())
						found = True
			if found: break
			time.sleep(1)

	except  Exception, e:
			U.logger.log(30, u"in Line {} has error={}".format(sys.exc_traceback.tb_lineno, e))
			return {}
	
	U.logger.log(10, "{} return data: {}".format(MAC, retdata))
	return retdata



#################################
#
#  these are devices we need to connect to , then wait for resposne, not like BC devicees, we just listen to.
#
#################################
def tryToConnectToDevice(MAC):
	global macList
	try:
		if macList[MAC]["devType"] == "BLEXiaomiMiTempHumSquare":
			return BLEXiaomiMiTempHumSquare(MAC)

		elif macList[MAC]["devType"] == "BLEXiaomiMiVegTrug":
			return BLEXiaomiMiVegTrug(MAC)

	except  Exception, e:
			U.logger.log(30, u"in Line {} has error={}".format(sys.exc_traceback.tb_lineno, e))
			return {}

	return {"connected":False, "ok":False }


#################################
def BLEXiaomiMiTempHumSquare(MAC):
	global errCount, macList, maxTrieslongConnect, useHCI

	data = {"connected":False, "ok":False }
	try:

		"""
		will take ~ 8-12 secs to connect then send data every 5 secs or so, 
			when issuing command immediate afterwads, will likely retuurn dat, when waiting for more than 10 secs it will need a pause of > 1 minute 
		returns:
			Characteristic value was written successfully
			Notification handle = 0x0036 value: 9c 08 37 06 0c 
			Notification handle = 0x0036 value: a5 08 3a 06 0c 
		error msg:
			connect error: Transport endpoint is not connected (107)
			connect error: Function not implemented (38)
		need to add:
			 hciX default 
		"""
		if time.time() - macList[MAC]["lastTesttt"] < macList[MAC]["readSensorEvery"]: return {"ok":False}

		if macList[MAC]["triesWOdata"] >= maxTrieslongConnect/2 and macList[MAC]["triesWOdata"]%3 != 0:
			# skip some after many tries
			macList[MAC]["lastTesttt"] = macList[MAC]["readSensorEvery"] + 10
			macList[MAC]["triesWOdata"] +=1
			return {"ok":False}

			
		timewait = 15
		for ii in range(1):

			startCMD = time.time()

			expCommands = connectGATT(useHCI, MAC, 5, 20)
			if expCommands == "":
				macList[MAC]["triesWOdata"] +=1
				data["triesWOdata"] = macList[MAC]["triesWOdata"]
				if macList[MAC]["triesWOdata"] > maxTrieslongConnect:
					macList[MAC]["triesWOdata"] = 0
					U.logger.log(20, u"error, triesWOdata:{} HCI available:={}".format(macList[MAC]["triesWOdata"], HCIs))
					return {"ok":True, "connected":False, "triesWOdata": macList[MAC]["triesWOdata"]}
				return data

			readData = []

			for nn in range(2):
				readData = writeAndListenGattcmd(expCommands, "char-write-req 0038 0100", "value:", 5, 15)
				if readData == []: continue
				break


			#U.logger.log(20, "{}  {}. try ret:{}".format(MAC, ii, readData))
			if len(readData) == 5:
				data["temp"] 			= round( float(int(readData[1]+readData[0],16)/100. + macList[MAC]["offsetTemp"]),1) 
				data["hum"]  			= int( int(readData[2],16) + macList[MAC]["offsetHum"] )
				data["batteryVoltage"]	= int(readData[4]+readData[3],16)
				data["batteryLevel"]	= batLevelTempCorrection(data["batteryVoltage"], data["temp"], batteryVoltAt100 = 3000, batteryVoltAt0=2700. )
				data["ok"]   			= True
				data["connected"]   	= True
				macList[MAC]["triesWOdata"] = 0
				U.logger.log(20, "{} return data: {}".format(MAC, data))
				if macList[MAC]["lastData"] == {}:
					macList[MAC]["lastData"] = copy.copy(data)
					macList[MAC]["lastTesttt"] = 0.
				if ( abs(data["temp"] - macList[MAC]["lastData"]["temp"])      > 1	or
					 abs(data["hum"]  - macList[MAC]["lastData"]["hum"])       > 2	or
					 data["connected"] !=macList[MAC]["lastData"]["connected"]		or
					 time.time()      - macList[MAC]["lastTesttt"]             > 60.):
					macList[MAC]["lastTesttt"] = time.time()
					macList[MAC]["lastData"]  = copy.copy(data)
					return data
				else:
					return {"ok":False, "connected":True, "triesWOdata": macList[MAC]["triesWOdata"]}
			if time.time() - startCMD < (timewait -1): time.sleep(10) 
			macList[MAC]["triesWOdata"] += 1

		data["triesWOdata"] = macList[MAC]["triesWOdata"]
		if macList[MAC]["triesWOdata"] >= maxTrieslongConnect:
			macList[MAC]["triesWOdata"] = 0
			HCIs = U.whichHCI()
			U.logger.log(20, u"error, triesWOdata:{} HCI available:={}".format(macList[MAC]["triesWOdata"], HCIs))
			return {"ok":True, "connected":False, "triesWOdata": macList[MAC]["triesWOdata"]}

	except  Exception, e:
		U.logger.log(30, u"in Line {} has error={}".format(sys.exc_traceback.tb_lineno, e))
		return "badData"
	
	U.logger.log(20, "{} return data: {}".format(MAC, data))
	
	return data



#################################
def BLEXiaomiMiVegTrug(MAC):
	global errCount, macList, maxTrieslongConnect, useHCI

	data = {"connected":False, "ok":False }
	try:
		if time.time() - macList[MAC]["lastTesttt"] < macList[MAC]["readSensorEvery"]: return {"ok":False}

		if macList[MAC]["triesWOdata"] >= maxTrieslongConnect/2 and macList[MAC]["triesWOdata"]%3 != 0:
			macList[MAC]["lastTesttt"] = macList[MAC]["readSensorEvery"] + 10
			# skip some after many tries
			macList[MAC]["triesWOdata"] +=1
			return {"ok":False}

		"""
		# start reading:  char-write-req 33 A01F

		get fist set: char-read-hnd 38
		# 7b in little 
		#    0: batteryLevel
		#    1: ??
		#  2-6: fw eg: '56 2d 33 2e 32 2e 34', 

		get second set: char-read-hnd 35
		# 16b in l endian
		#   0-1: temp 0.1 [°C]
		#     2: ??
		#   3-6: bright [lux]
		#     7: moist [%]
		#   8-9: conduct [µS/cm]
		# 10-15: ?? 
		# eg: 'f4 00 69 00 00 00 00 1d 11 01 02 3c 00 fb 34 9b'
		"""
		#U.logger.log(20,"flowercare mac:{}".format(MAC))
			
		U.logger.log(20, u"{},  tries:{}, DT:{}".format(MAC, macList[MAC]["triesWOdata"], time.time() - macList[MAC]["lastTesttt"]))
		expCommands = connectGATT(useHCI, MAC, 5,15)
		if expCommands == "":
			macList[MAC]["triesWOdata"] +=1
			data["triesWOdata"] = macList[MAC]["triesWOdata"]
			if macList[MAC]["triesWOdata"] > maxTrieslongConnect:
				macList[MAC]["triesWOdata"] = 0
				U.logger.log(20, u"error, triesWOdata:{}".format(macList[MAC]["triesWOdata"]))
				return {"ok":True, "connected":False, "triesWOdata": macList[MAC]["triesWOdata"]}
			return data

		result1 = []
		result2 = []

		for nn in range(1):
			if not writeGattcmd(expCommands, "char-write-req 33 A01F", "Characteristic value was written successfully", 5):
									continue

			result1 = readGattcmd(expCommands, "char-read-hnd 38", "Characteristic value/descriptor:", 7, 5)
			if result1 == []:		continue

			result2 = readGattcmd(expCommands, "char-read-hnd 35", "Characteristic value/descriptor:", 16, 5)
			if result2 == []:		continue

			break

		disconnectGattcmd(expCommands, 5)

		U.logger.log(20, u"connect results:{} - {}".format(result1, result2))

		if result1 == [] or result2 == []:
			data["triesWOdata"] = macList[MAC]["triesWOdata"]
			if macList[MAC]["triesWOdata"] >= maxTrieslongConnect:
				macList[MAC]["triesWOdata"] = 0
				U.logger.log(20, u"error, triesWOdata:{} HCI available:={}".format(macList[MAC]["triesWOdata"], HCIs))
				return {"ok":True, "connected":False, "triesWOdata": macList[MAC]["triesWOdata"]}
			return data

		data["batteryLevel"]		= int(result1[0],16)
		try:	data["Version"]		= "".join(result1[2:]).decode("hex")
		except: data["Version"]		= "unknown"
		data["temp"]  				= round( int(result2[1]+result2[0],16)/10., 1)
		data["illuminance"]			= int(result2[6]+result2[5]+result2[4]+result2[3],16)
		data["moisture"] 			= int(result2[7],16)
		data["Conductivity"]		= int(result2[9]+result2[8],16)
		data["ok"]					= True
		data["connected"]			= True
		if macList[MAC]["lastData"] == {}:
			macList[MAC]["lastData"] = copy.copy(data)
			macList[MAC]["lastTesttt"] = 0.
		macList[MAC]["triesWOdata"] = 0
		if ( abs(data["temp"] 			- macList[MAC]["lastData"]["temp"])			> 1 	or
			 abs(data["moisture"]  		- macList[MAC]["lastData"]["moisture"])		> 2 	or
			 abs(data["Conductivity"]	- macList[MAC]["lastData"]["Conductivity"])	> 2 	or
			     (data["connected"]	   != macList[MAC]["lastData"]["connected"])			or
			      time.time()           - macList[MAC]["lastTesttt"]             	> 119.):
			macList[MAC]["lastTesttt"] = time.time()
			macList[MAC]["lastData"]  = copy.copy(data)
			U.logger.log(20, "{} return data: {}".format(MAC, data))
			return data

		data = {"ok":False, "connected":True, "triesWOdata": macList[MAC]["triesWOdata"]}
		U.logger.log(20, "{} return data: {}".format(MAC, data))
		return data

	except  Exception, e:
		U.logger.log(30, u"in Line {} has error={}".format(sys.exc_traceback.tb_lineno, e))
		return "badData"
	
	U.logger.log(20, "{} return data: {}".format(MAC, data))
	
	return data


#################################
def disconnectGattcmd(expCommands, timeout):	
	try:
		expCommands.sendline("disconnect" )
		#U.logger.log(20,"sendline disconnect ")
		ret = expCommands.expect([">","Error",pexpect.TIMEOUT], timeout=5)
		if ret == 0:
			return True
		else:
			U.logger.log(20,"... error: {}".format(expCommands.after))
	except  Exception, e:
		U.logger.log(30, u"in Line {} has error={}".format(sys.exc_traceback.tb_lineno, e))
	return False


#################################
def writeGattcmd(expCommands, cc, expectedTag, timeout):	
	try:		
		for ii in range(3):
			#U.logger.log(20,"sendline  cmd{}".format( cc))
			expCommands.sendline( cc )
			ret = expCommands.expect([expectedTag,"Error","failed",pexpect.TIMEOUT], timeout=5)
			if ret == 0:
				#U.logger.log(20,"... successful: BF:{}-- AF:{}--".format(expCommands.before, expCommands.after))
				return True
			else: 
				U.logger.log(20, u"... error, quit: {}-{}".format(expCommands.before, expCommands.after))
				continue
			ret = expCommands.expect("\n")

	except  Exception, e:
		U.logger.log(30, u"in Line {} has error={}".format(sys.exc_traceback.tb_lineno, e))
	return False

#################################
def writeAndListenGattcmd(expCommands, cc, expectedTag, nBytes, timeout):
	try:
		for kk in range(2):
			#U.logger.log(20,"sendline  cmd{}".format( cc))
			expCommands.sendline( cc )
			ret = expCommands.expect([expectedTag,"Error","failed",pexpect.TIMEOUT], timeout=timeout)
			if ret == 0:
				#U.logger.log(20,"... successful:  BF:{}-- AF:{}--".format(expCommands.before,expCommands.after))
				ret = expCommands.expect("\n")
				xx = (expCommands.before.replace("\r","").strip()).split() 
				if len(xx) == nBytes:
					return xx
				else:
					U.logger.log(20,"... error: len != 7")
					continue
			else:
				U.logger.log(20,"... error: {}-{}".format(expCommands.before,expCommands.after))
				continue
	except  Exception, e:
		U.logger.log(30, u"in Line {} has error={}".format(sys.exc_traceback.tb_lineno, e))
	return []
#################################
def readGattcmd(expCommands, cc, expectedTag, nBytes, timeout):
	try:
		for kk in range(2):
			#U.logger.log(20,"sendline  cmd{}".format( cc))
			expCommands.sendline( cc )
			ret = expCommands.expect([expectedTag,"Error","failed",pexpect.TIMEOUT], timeout=timeout)
			if ret == 0:
				#U.logger.log(20,"... successful:  BF:{}-- AF:{}--".format(expCommands.before,expCommands.after))
				ret = expCommands.expect("\n")
				xx = (expCommands.before.replace("\r","").strip()).split() 
				if len(xx) == nBytes:
					return xx
				else:
					U.logger.log(20,"... error: len != 7")
					continue
			else:
				U.logger.log(20,"... error: {}-{}".format(expCommands.before,expCommands.after))
				continue
	except  Exception, e:
		U.logger.log(30, u"in Line {} has error={}".format(sys.exc_traceback.tb_lineno, e))
	return []


#################################
def connectGATT(useHCI, MAC, timeoutGattool, timeoutConnect):

	try:
		nTries = 1
		for kk in range(nTries):
			cmd = "sudo /usr/bin/gatttool -i {} -b {} -I".format(useHCI,  MAC) 
			U.logger.log(20,"{} ;  expect: >".format(cmd))
			expCommands = pexpect.spawn(cmd)
			ret = expCommands.expect([">","error",pexpect.TIMEOUT], timeout=timeoutGattool)
			if ret == 0:
				U.logger.log(20,"... successful: {}-==-:{}".format(expCommands.before,expCommands.after))
			else:
				if kk == nTries -1: 
					U.logger.log(20, u"... error, giving up: {}-==-:{}".format(expCommands.before,expCommands.after))
					time.sleep(1)
					return ""
				U.logger.log(20, u"... error:  {}-==-:{}".format(expCommands.before,expCommands.after))
				continue

			time.sleep(0.1)
			ntriesConnect = 2
			#ret = expCommands.expect(".*", timeout=0.5)s
			#U.logger.log(20,"... .*: {}-==-:{}".format(expCommands.before,expCommands.after))
			for ii in range(ntriesConnect):
				try:
					U.logger.log(20,"expect: Connection successful ")
					expCommands.sendline("connect")
					ret = expCommands.expect(["Connection successful","Error", pexpect.TIMEOUT], timeout=timeoutConnect)
					if ret == 0:
						U.logger.log(20,"... successful: {}-==-:{}".format(expCommands.before,expCommands.after))
						#ret = expCommands.expect(".*", timeout=0.5)
						#U.logger.log(20,"... .*: {}-==-:{}".format(expCommands.before,expCommands.after))
						return expCommands
					else:
						U.logger.log(20, u"... error: {}-==-:{}".format(expCommands.before,expCommands.after))

				except Exception, e:
					U.logger.log(20, u"Line {} has error={}".format(sys.exc_traceback.tb_lineno, e))
				time.sleep(1)
			time.sleep(1)


			U.logger.log(20, u"connect error giving up")

		return ""
	except  Exception, e:
		U.logger.log(30, u"in Line {} has error={}".format(sys.exc_traceback.tb_lineno, e))
	return ""


#################################
def batLevelTempCorrection(batteryVoltage, temp, batteryVoltAt100=3000., batteryVoltAt0=2700.):
	try:
		batteryLowVsTemp			= (1. + 0.7*min(0.,temp-10.)/100.) * batteryVoltAt0 # (changes to 0.9* 2700 @ 0C; to = 0.8*2700 @-10C )
		batteryLevel 				= int(min(100.,max(0.,100.* (batteryVoltage - batteryLowVsTemp)/(batteryVoltAt100-batteryLowVsTemp))))
		return batteryLevel
	except	Exception, e:
		U.logger.log(30,u"in Line {} has error={}".format(sys.exc_traceback.tb_lineno, e))
	return 0

#################################

####################################################################################################################################
####################################################################################################################################
####################################################################################################################################
####################################################################################################################################
def execBLEconnect():
	global sensorList,restartBLEifNoConnect
	global macList,oldParams
	global oldRaw,	lastRead
	global errCount, lastConnect
	global BLEconnectMode
	global sensor
	global oneisBLElongConnectDevice
	global maxTrieslongConnect
	global useHCI


	maxTrieslongConnect 	= 7
	oneisBLElongConnectDevice = False
	BLEconnectMode			= "commandLine" # socket or commandLine
	oldRaw					= ""
	lastRead				= 0
	errCount				= 0
	###################### constants #################

	####################  input gios   ...allrpi	  only rpi2 and rpi0--
	oldParams		  = ""
	#####################  init parameters that are read from file 
	sensorList			= "0"
	G.authentication	= "digest"
	restartBLEifNoConnect = True
	sensor				= G.program
	macList				={}
	waitMin				=2.
	oldRaw				= ""

	myPID			= str(os.getpid())
	U.setLogging()
	U.killOldPgm(myPID,G.program+".py")# kill  old instances of myself if they are still running

	loopCount		  = 0
	sensorRefreshSecs = 90
	U.logger.log(30, "starting BLEconnect program ")
	readParams()

	time.sleep(1)  # give HCITOOL time to start

	shortWait			= 1.	# seconds  wait between loop
	lastEverything		= time.time()-10000. # -1000 do the whole thing initially
	lastAlive			= time.time()
	lastData			= {}
	lastRead			= -1

	if U.getIPNumber() > 0:
		U.logger.log(30," no ip number ")
		time.sleep(10)
		exit()


	G.tStart			= time.time() 
	lastMsg				={}
	#print iPhoneRefreshDownSecs
	#print iPhoneRefreshUpSecs
	startSeconds		= time.time()
	lastSignal			= time.time()
	restartCount		= 0
	nextTest			= 60
	nowTest				= 0
	nowP				= False
	oldRetry			= False
	eth0IP, wifi0IP, eth0Enabled, wifiEnabled = U.getIPCONFIG()
	##print eth0IP, wifi0IP, G.eth0Enabled, G.wifiEnabled


	## give other ble functions time to finish
	doNotUseHCI = ""
	BusUsedByBeaconloop = ""
	if oneisBLElongConnectDevice:
		for ii in range(3):
			time.sleep(ii)
			hciBeaconloopUsed, raw  = U.readJson("{}temp/beaconloop.hci".format(G.homeDir))
			if raw != "": 
				doNotUseHCI 		= hciBeaconloopUsed["usedHCI"]
				BusUsedByBeaconloop = hciBeaconloopUsed["usedBus"]
				break


	#### selct the proper hci bus: if just one take that one, if 2, use bus="USB", if no uart use hci0

	#need to add:
	#	 hciX default 

	HCIs = U.whichHCI()
	"""
	{'hci': {
	u'hci0': {'bus': u'USB',  'BLEmac': u'5C:F3:70:6D:D9:4A', 'numb': 0, 'upDown': 'UP'}, 
	u'hci1': {'bus': u'UART', 'BLEmac': u'DC:A6:32:6E:E6:D0', 'numb': 1, 'upDown': 'UP'}}, 
	'ret': [u'hci1:\tType: Primary  Bus: UART\n\tBD Address: DC:A6:32:6E:E6:D0  ACL MTU: 1021:8  SCO MTU: 64:1\n\tUP RUNNING \n\tRX bytes:218659024 acl:5 sco:0 events:6395583 errors:0\n\tTX bytes:5859 acl:4 sco:0 commands:226 errors:0\n\nhci0:\tType: Primary  Bus: USB\n\tBD Address: 5C:F3:70:6D:D9:4A  ACL MTU: 1021:8  SCO MTU: 64:1\n\tUP RUNNING \n\tRX bytes:124594 acl:1716 sco:0 events:9040 errors:0\n\tTX bytes:68257 acl:870 sco:0 commands:5086 errors:0\n\n', u'']}
	"""
	#U.logger.log(20, "BLE(long)connect--HCIs:  {}".format(HCIs))
	if HCIs["hci"] != {}:
		if len(HCIs["hci"]) < 2 and oneisBLElongConnectDevice:
			text = "BLE(long)connect: only one BLE dongle, need 2 to run, will restart BLE stack (hciattach /dev/ttyAMA0 bcm43xx 921600 noflow -) and try again,, HCI inf:\n{}".format(HCIs)
			U.logger.log(20, text)
			U.sendURL( data={"data":{"error":text}}, squeeze=False, wait=True )
			cmd = "timeout 5 sudo hciattach /dev/ttyAMA0 bcm43xx 921600 noflow -"
			ret = subprocess.Popen(cmd, shell=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE).communicate()
			U.logger.log(20, "cmd: {} and ret:".format(cmd, ret))

			cmd = "timeout 20 sudo hciattach /dev/ttyAMA0 bcm43xx 921600 noflow -"
			ret = subprocess.Popen(cmd, shell=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE).communicate()
			U.logger.log(20, "cmd: {} and ret:".format(cmd, ret))
			time.sleep(5)
			exit()

		U.logger.log(20, "BLE(long)connect: BLEconnectUseHCINo-bus: {}; default:{}, HCIUsedByBeaconloop:{}; BusUsedByBeaconloop:{}".format(G.BLEconnectUseHCINo, "USB", doNotUseHCI, BusUsedByBeaconloop))
		useHCI,  myBLEmac, BLEid, bus = U.selectHCI(HCIs["hci"], G.BLEconnectUseHCINo, "USB", doNotUseHCI=doNotUseHCI)
		if BLEid < 0:
			text = "BLEconnect: BLE STACK is not UP HCI-info:\n{}".format(HCIs)
			U.logger.log(20, text)
			U.sendURL( data={"data":{"error":text}}, squeeze=False, wait=True )
			time.sleep(25)
			exit()
	else:
			text = "BLEconnect: BLE STACK HCI is empty HCI:{}".format(HCIs)
			U.logger.log(20, text)
			U.sendURL( data={"data":{"error":text}}, squeeze=False, wait=True )
			time.sleep(25)
			exit()



	U.logger.log(20, "BLE(long)connect: using mac:{};  useHCI: {}; bus: {}; mode: {} searching for MACs:\n{}".format(myBLEmac, useHCI, HCIs["hci"][useHCI]["bus"], BLEconnectMode , macList))
	lastConnect = time.time()
	while True:

			tt = time.time()
			if tt - nowTest > 15:
				nowP	= False
				nowTest = 0
			if tt - lastRead > 4 :
				newParameterFile = readParams()
				eth0IP, wifi0IP, G.eth0Enabled, G.wifiEnabled = U.getIPCONFIG()
				lastRead=tt

			if restartBLEifNoConnect and (tt - lastSignal > (2*3600+ 600*restartCount)) :
				U.logger.log(30, "requested a restart of BLE stack due to no signal for {:.0f} seconds".format(tt-lastSignal))
				subprocess.call("echo xx > {}temp/BLErestart".format(G.homeDir), shell=True) # signal that we need to restart BLE
				lastSignal = time.time() +30
				restartCount +=1

			nextTest = 300

			if not oneisBLElongConnectDevice:
				for thisMAC in macList:
					if macList[thisMAC]["type"] == "BLEconnect":
						if macList[thisMAC]["up"]:
							nextTest = min(nextTest, macList[thisMAC]["lastTesttt"] + (macList[thisMAC]["iPhoneRefreshUpSecs"]*0.90)   -tt )
						else:
							nextTest = min(nextTest, macList[thisMAC]["lastTesttt"] + macList[thisMAC]["iPhoneRefreshDownSecs"] -tt - macList[thisMAC]["quickTest"] )
						nT= max(int(nextTest),1)
						fTest = max(0.2, nextTest / nT )
						#print "fTest",thisMAC, fTest
						for ii in range(nT):
							tt = time.time()
							if fTest > 0:
								time.sleep(fTest)  
							if not nowP and tt - nowTest > 20.:
								quick = U.checkNowFile(sensor)				  
								if quick:
									for ml in macList :
										macList[ml]["lastData"]	   = {"rssi":-999,"txPower":-999}
										macList[ml]["lastTesttt"]  = 0.
										#macList[ml]["lastMsgtt"]  = 0.
										macList[ml]["retryIfUPtemp"] = macList[ml]["retryIfUP"]
										macList[ml]["retryIfUP"] = False
										macList[ml]["up"]		 = False
									nowTest = tt
									nowP	= True
									break

							if nowP and tt - nowTest > 5 and tt - nowTest < 10.:
								for ml in macList:
									nowTest = 0.
									nowP	= False
									#print "resetting  ", ml, onlyThisMAC, nowTest


			for thisMAC in macList:
				tt = time.time()
				#if nowP: print "nowP:	testing: "+thisMAC,macList[ml]["retryIfUP"], tt - macList[thisMAC]["lastTesttt"]
				if macList[thisMAC]["type"] == "BLEconnect":
					if macList[thisMAC]["up"]:
						if tt - macList[thisMAC]["lastTesttt"] <= macList[thisMAC]["iPhoneRefreshUpSecs"]*0.90:	  continue
					elif tt - macList[thisMAC]["lastTesttt"] <= macList[thisMAC]["iPhoneRefreshDownSecs"] - macList[thisMAC]["quickTest"]:	 continue


					######### here we actually get the data from the phones ###################
					if BLEconnectMode == "socket":
						data0 = tryToConnectSocket(thisMAC, macList[thisMAC]["BLEtimeout"], BLEid)
					else:
						data0 = tryToConnectCommandLine(thisMAC, macList[thisMAC]["BLEtimeout"])

					lastConnect = time.time()


					#print	data0
					macList[thisMAC]["lastTesttt"] = tt

				
					if	data0 != {}:
						if data0["rssi"] !=-999:
							macList[thisMAC]["up"] = True
							lastSignal	 = time.time()
							restartCount = 0
							if os.path.isfile(G.homeDir + "temp/BLErestart"):
								os.remove(G.homeDir + "temp/BLErestart")

						else:
							macList[thisMAC]["up"] = False

						if data0["rssi"]!=macList[thisMAC]["lastData"] or (tt-macList[thisMAC]["lastMsgtt"]) > (macList[thisMAC]["iPhoneRefreshUpSecs"]-1.): # send htlm message to indigo, if new data, or last msg too long ago
							if macList[thisMAC]["lastData"] != -999 and not macList[thisMAC]["up"] and (tt-macList[thisMAC]["lastMsgtt"]) <	 macList[thisMAC]["iPhoneRefreshUpSecs"]+2.:
								macList[thisMAC]["quickTest"] =macList[thisMAC]["iPhoneRefreshDownSecs"]/2.
								continue
							#print "sending "+thisMAC+" " + datetime.datetime.now().strftime("%M:%S"), macList[thisMAC]["up"] , macList[thisMAC]["quickTest"], data0
							macList[thisMAC]["quickTest"] = 0.
							#print "af -"+datetime.datetime.now().strftime("%M:%S"), macList[thisMAC]["up"], macList[thisMAC]["quickTest"], data0
							macList[thisMAC]["lastMsgtt"]  = tt
							macList[thisMAC]["lastData"] = data0["rssi"]
							data={}
							data["sensors"]					= {"BLEconnect":{macList[thisMAC]["devId"]:{thisMAC:data0}}}
							U.sendURL(data=data)

					else:
						macList[thisMAC]["up"] = False

				if macList[thisMAC]["type"] == "isBLElongConnectDevice":
					if tt - macList[thisMAC]["lastTesttt"] <= macList[thisMAC]["updateIndigoTiming"]: continue

					data0 = tryToConnectToDevice(thisMAC)

					if	data0 != {}:
						data = {}
						#U.logger.log(20, "BLEconnect: data:{}".format(data0))
						if "badSensor" in data0:
							macList[thisMAC]["up"] = False
							macList[thisMAC]["badSensor"] +=1
							if macList[thisMAC]["badSensor"] > 3:
								data["sensors"] = {macList[thisMAC]["devType"]:{macList[thisMAC]["devId"]:"badSensor"}}
							continue
						macList[thisMAC]["badSensor"] = 0
						macList[thisMAC]["up"] = True
						if "ok" in data0:
							if data0["ok"]:
								data["sensors"]				= {macList[thisMAC]["devType"]:{macList[thisMAC]["devId"]:data0}}
								U.sendURL(data=data)
							if macList[thisMAC]["triesWOdata"] >  2* maxTrieslongConnect:
								U.logger.log(20, "requested a restart of BLE stack due to no sensor signal  for {} tries".format( macList[thisMAC]["triesWOdata"]))
								time.sleep(5)
								subprocess.call("echo xx > {}temp/BLErestart".format(G.homeDir), shell=True) # signal that we need to restart BLE
							
					else:
						macList[thisMAC]["up"] = False




			loopCount+=1
			time.sleep(2)
			#print "no answer sleep for " + str(iPhoneRefreshDownSecs)
			U.echoLastAlive(G.program)

execBLEconnect()
		
try: 	G.sendThread["run"] = False; time.sleep(1)
except: pass
		
sys.exit(0)		   
