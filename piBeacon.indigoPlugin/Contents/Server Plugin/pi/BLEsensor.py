#!/usr/bin/env python
# -*- coding: utf-8 -*-
# test BLE Scanning software
# jcs 6/8/2014
#  adopted by Karl Wachs Nov27	2015
# version 1.1  Dec 24
# v 2	 feb 5 2016


import sys, os, subprocess
import time,datetime
import struct
import bluetooth._bluetooth as bluez
import json

sys.path.append(os.getcwd())
import	piBeaconUtils as U
import	piBeaconGlobals as G
G.program = "BLEsensor"

#################################  BLE iBeaconScanner  ----> start
# BLE iBeaconScanner based on https://github.com/adamf/BLE/blob/master/ble-scanner.py
# JCS 06/07/14


# BLE scanner based on https://github.com/adamf/BLE/blob/master/ble-scanner.py
# BLE scanner, based on https://code.google.com/p/pybluez/source/browse/trunk/examples/advanced/inquiry-with-rssi.py

# https://github.com/pauloborges/bluez/blob/master/tools/hcitool.c for lescan
# https://kernel.googlesource.com/pub/scm/bluetooth/bluez/+/5.6/lib/hci.h for opcodes
# https://github.com/pauloborges/bluez/blob/master/lib/hci.c#L2782 for functions used by lescan

# performs a simple device inquiry, and returns a list of ble advertizements 
# discovered device

# NOTE: Python's struct.pack() will add padding bytes unless you make the endianness explicit. Little endian
# should be used for BLE. Always start a struct.pack() format string with "<"


LE_META_EVENT = 0x3e
LE_PUBLIC_ADDRESS=0x00
LE_RANDOM_ADDRESS=0x01
LE_SET_SCAN_PARAMETERS_CP_SIZE=7
OGF_LE_CTL=0x08
OCF_LE_SET_SCAN_PARAMETERS=0x000B
OCF_LE_SET_SCAN_ENABLE=0x000C
OCF_LE_CREATE_CONN=0x000D

LE_ROLE_MASTER = 0x00
LE_ROLE_SLAVE = 0x01

# these are actually subevents of LE_META_EVENT
EVT_LE_CONN_COMPLETE=0x01
EVT_LE_ADVERTISING_REPORT=0x02
EVT_LE_CONN_UPDATE_COMPLETE=0x03
EVT_LE_READ_REMOTE_USED_FEATURES_COMPLETE=0x04

# Advertisment event types
ADV_IND=0x00
ADV_DIRECT_IND=0x01
ADV_SCAN_IND=0x02
ADV_NONCONN_IND=0x03
ADV_SCAN_RSP=0x04

def stringFromPacket(pkt):
	myString = ""
	for c in pkt:
		myString +=	 "%02x" %struct.unpack("B",c)[0]
	return myString 

def returnnumberpacket(pkt):
	myInteger = 0
	multiple = 256
	for c in pkt:
		myInteger +=  struct.unpack("B",c)[0] * multiple
		multiple = 1
	return myInteger 

def returnstringpacket(pkt):
	myString = ""
	for c in pkt:
		myString +=	 "%02x" %struct.unpack("B",c)[0]
	return myString 

def printpacket(pkt):
	for c in pkt:
		sys.stdout.write("%02x " % struct.unpack("B",c)[0])

def get_packed_bdaddr(bdaddr_string):
	packable_addr = []
	addr = bdaddr_string.split(':')
	addr.reverse()
	for b in addr: 
		packable_addr.append(int(b, 16))
	return struct.pack("<BBBBBB", *packable_addr)

def packed_bdaddr_to_string(bdaddr_packed):
	return ':'.join('%02x'%i for i in struct.unpack("<BBBBBB", bdaddr_packed[::-1]))

def hci_enable_le_scan(sock):
	hci_toggle_le_scan(sock, 0x01)

def hci_disable_le_scan(sock):
	hci_toggle_le_scan(sock, 0x00)

def hci_toggle_le_scan(sock, enable):
	cmd_pkt = struct.pack("<BB", enable, 0x00)
	bluez.hci_send_cmd(sock, OGF_LE_CTL, OCF_LE_SET_SCAN_ENABLE, cmd_pkt)


def hci_le_set_scan_parameters(sock):
	cmd_pkt = struct.pack("<BBBBBBB", 0x01, 0x0, 0x10, 0x0, 0x10,0x01, 0x00)
	bluez.hci_send_cmd(sock, OGF_LE_CTL,OCF_LE_SET_SCAN_ENABLE, cmd_pkt) 


#################################  BLE iBeaconScanner  ----> end
def startBlueTooth(pi):
	global myBLEmac, downCount 

	useHCI	 = ""
	myBLEmac = ""
	devId	 = 0
	## good explanation: http://gaiger-G.programming.blogspot.com/2015/01/bluetooth-low-energy.html
	U.logger.log(30,"(re)starting bluetooth")
	try:
		HCIs = U.whichHCI()
		for hci in HCIs["hci"]:
			U.logger.log(20,"down and up :{}".format(hci))
			subprocess.call("sudo hciconfig {} down &".format(hci), shell=True) # disable bluetooth
			time.sleep(0.2)
			subprocess.call("sudo hciconfig {} up &".format(hci), shell=True) # enable bluetooth
		time.sleep(0.3)


		#### selct the proper hci bus: if just one take that one, if 2, use bus="uart", if no uart use hci0
		HCIs = U.whichHCI()
		#

		#U.logger.log(30,"myBLEmac HCIs{}".format( HCIs))
		useHCI,  myBLEmac, devId = U.selectHCI(HCIs["hci"], G.BeaconUseHCINo,"UART")
		if myBLEmac ==  -1:
			U.logger.log(20,"myBLEmac wrong: myBLEmac:{}".format( myBLEmac))
			return 0,  0, -1
		U.logger.log(20,"Beacon Use HCINo {};  useHCI:{};  myBLEmac:{}; devId:{}" .format(G.BeaconUseHCINo, useHCI, myBLEmac, devId))
			

		#ret = subprocess.Popen("hciconfig hci0 leadv 3",shell=True,stdout=subprocess.PIPE,stderr=subprocess.PIPE).communicate() # enable ibeacon signals, next is the ibeacon message
		OGF					= " 0x08"
		OCF					= " 0x0008"
		iBeaconPrefix		= " 1E 02 01 1A 1A FF 4C 00 02 15"
		uuid				= " 2f 23 44 54 cf 6d 4a 0f ad f2 f4 91 1b a9 ff a6"
		MAJ					= " 00 09"
		MIN					= " 00 "+"0%x"%(int(pi))
		txP					= " C5 00"
		#cmd	 = "hcitool -i "+useHCI+" cmd" + OGF + OCF + iBeaconPrefix + uuid + MAJ + MIN + txP
		cmd	 = "hcitool -i {} cmd{}{}{}{}{}{}{} &".format(useHCI, OGF, OCF, iBeaconPrefix, uuid, MAJ, MIN, txP)
		U.logger.log(20,cmd) 
		subprocess.call(cmd,shell=True,stdout=subprocess.PIPE)
		time.sleep(0.2)
		####################################set adv params		minInt	 maxInt		  nonconectable	 +??  <== THIS rpi to send beacons every 10 secs only 
		#											   00 40=	0x4000* 0.625 msec = 16*4*256 = 10 secs	 bytes are reverse !! 
		#											   00 10=	0x1000* 0.625 msec = 16*1*256 = 2.5 secs
		#											   00 04=	0x0400* 0.625 msec =	4*256 = 0.625 secs
		#cmd	 = "hcitool -i "+useHCI+" cmd" + OGF + " 0x0006"	  + " 00 10"+ " 00 20" +  " 03"			   +   " 00 00 00 00 00 00 00 00 07 00"
		cmd	 = "hcitool -i {} cmd{} 0x0006 00 10 00 20 03 00 00 00 00 00 00 00 00 07 00 &".format(useHCI, OGF)
		## maxInt= A0 00 ==	 100ms;	 40 06 == 1000ms; =0 19 = 4 =seconds  (0x30x00	==> 64*256*0.625 ms = 10.024secs  use little endian )
		U.logger.log(20,cmd) 
		subprocess.call(cmd,shell=True,stdout=subprocess.PIPE)
		####################################LE Set Advertise Enable
		#cmd	 = "hcitool -i "+useHCI+" cmd" + OGF + " 0x000a" + " 01"
		time.sleep(0.2)
		cmd	 = "hcitool -i {} cmd{} 0x000a 01 &".format(useHCI, OGF)
		U.logger.log(20,cmd) 
		subprocess.call(cmd,shell=True,stdout=subprocess.PIPE)
		time.sleep(0.2)


		HCIs = U.whichHCI()
		ret = HCIs["ret"]

		if ret[1] != "":	U.logger.log(30,"BLE start returned:\n{}error:>>{}<<".format(ret[0],ret[1]))
		else:			 	
				U.logger.log(20,"BLE start returned:\n{}my BLE mac# is >>{}<<".format(ret[0], myBLEmac))
				if useHCI in HCIs["hci"]:
					if HCIs["hci"][useHCI]["upDown"] == "DOWN":
						if downCount > 1:
							U.logger.log(30,"reboot requested,{} is DOWN using hciconfig ".format(useHCI))
							writeFile("temp/rebootNeeded","bluetooth_startup {} is DOWN using hciconfig ".format(useHCI))
							time.sleep(10)
						downCount +=1
						time.sleep(10)
						return 0,  "", -1
				else:
					U.logger.log(30," {}  not in hciconfig list".format(useHCI))
					downCount +=1
					time.sleep(10)
					return 0,  "", -1
					
				
		if myBLEmac != "":
			writeFile("myBLEmac",myBLEmac)
		else:
			return 0, "", -1

	except Exception, e: 
		U.logger.log(50,u"exit at restart BLE stack error  in Line {} has error={}".format(sys.exc_traceback.tb_lineno, e))
		time.sleep(10)
		writeFile("restartNeeded","bluetooth_startup.ERROR:{}".format(e))
		downHCI(useHCI)
		time.sleep(0.2)
		return 0, "", -5


	try:
		sock = bluez.hci_open_dev(devId)
		U.logger.log(30, "ble thread started")
	except	Exception, e:
		U.logger.log(30,"error accessing bluetooth device...".format(e))
		if downCount > 2:
			writeFile("temp/rebootNeeded","bluetooth_startup.ERROR:".format(e))
			downHCI(useHCI)
		downCount +=1
		return 0,  "", -1
		
	try:
		hci_le_set_scan_parameters(sock)
		hci_enable_le_scan(sock)
	except	Exception, e:
		U.logger.log(50, u"in Line {} has error={}".format(sys.exc_traceback.tb_lineno, e))
		if unicode(e).find("Bad file descriptor") >-1:
			writeFile("temp/rebootNeeded","bluetooth_startup.ERROR:Bad_file_descriptor...SSD.damaged?")
		if unicode(e).find("Network is down") >-1:
			if downCount > 2:
				writeFile("temp/rebootNeeded","bluetooth_startup.ERROR:Network_is_down...need_to_reboot")
			downCount +=1
		downHCI(useHCI)
		return 0, "", -1 
	return sock, myBLEmac, 0

#################################
def writeFile(outFile, text):
	try:
		f = open("{}{}".format(G.homeDir, outFile),"w")
		f.write(text)
		f.close()
		#U.logger.log(20, u"===== writing to {}{} text:{}".format(G.homeDir, outFile, text))
	except	Exception, e:
		U.logger.log(50, u"in Line {} has error={}".format(sys.exc_traceback.tb_lineno, e))
		if unicode(e).find("Read-only file system:") >-1:
			f = open(G.homeDir+"temp/rebootNeeded","w")
			f.write("Read-only file system")
			f.close()
	return


def downHCI(useHCI):
	try:
		subprocess.Popen("hciconfig {} down &".format(useHCI),shell=True,stdout=subprocess.PIPE,stderr=subprocess.PIPE) # enable bluetooth
		time.sleep(0.2)
		subprocess.Popen("service bluetooth restart &",shell=True ,stdout=subprocess.PIPE,stderr=subprocess.PIPE)
		time.sleep(0.2)
		subprocess.Popen("service dbus restart &",shell=True ,stdout=subprocess.PIPE,stderr=subprocess.PIPE)
		time.sleep(0.2)
	except	Exception, e:
		U.logger.log(50, u"in Line {} has error={}".format(sys.exc_traceback.tb_lineno, e))
	return

	
#################################
def toReject(text):
	try:
		f=open("{}temp/rejects".format(G.homeDir),"a")
		f.write(str(time.time())+";"+text+"\n")
		f.close()
	except	Exception, e:
		if unicode(e).find("Read-only file system:") >-1:
			f = open(G.homeDir+"temp/rebootNeeded","w")
			f.write("Read-only file system")
			f.close()





def readParams(init):
	global BLEsensorMACs
	global oldRaw,	lastRead, sensor
	if init:
		G.ipOfServer	  =""
		G.passwordOfServer=""
		G.userIdOfServer  =""
		G.myPiNumber	  ="0"

	inp,inpRaw,lastRead2 = U.doRead(lastTimeStamp=lastRead)
	doParams = True
	if inp == "":				doParams = False
	if lastRead2 == lastRead:	doParams = False
	lastRead   = lastRead2
	if inpRaw == oldRaw:		doParams = False
	oldRaw	   = inpRaw
	if not doParams: return 

	try:
		U.getGlobalParams(inp)

		if "rebootSeconds"		in inp:	 rebootSeconds=		  int(inp["rebootSeconds"])
		if "sendAfterSeconds"	in inp:	 sendAfterSeconds=	  int(inp["sendAfterSeconds"])

		try:
			if "sensors"			 in inp: 
				sensors =			 (inp["sensors"])
				for sensor in ["BLEsensor","BLERuuviTag"]:
					if sensor in sensors:
						for devId in sensors[sensor]:
							sensD	= sensors[sensor][devId]
							mac		= sensD["mac"]
							if mac not in BLEsensorMACs: BLEsensorMACs[mac] = {}
							
							BLEsensorMACs[mac]["type"] 							= sensD["type"]
							BLEsensorMACs[mac]["devId"] 						= devId
							try:	BLEsensorMACs[mac]["offsetPress"]   		= float(sensD["offsetPress"])
							except: BLEsensorMACs[mac]["offsetPress"]			= 0.
							try:	BLEsensorMACs[mac]["offsetHum"]   			= float(sensD["offsetHum"])
							except: BLEsensorMACs[mac]["offsetHum"]				= 0.
							try:	BLEsensorMACs[mac]["offsetTemp"]   			= float(sensD["offsetTemp"])
							except: BLEsensorMACs[mac]["offsetTemp"]			= 0.
							try:	BLEsensorMACs[mac]["multiplyTemp"] 			= float(sensD["multiplyTemp"])
							except: BLEsensorMACs[mac]["multiplyTemp"] 			= 1.
							try:	BLEsensorMACs[mac]["updateIndigoTiming"] 	= float(sensD["updateIndigoTiming"])
							except: BLEsensorMACs[mac]["updateIndigoTiming"] 	= 10.
							try:	BLEsensorMACs[mac]["updateIndigoDeltaAccelVector"]	= float(sensD["updateIndigoDeltaAccelVector"])
							except: BLEsensorMACs[mac]["updateIndigoDeltaAccelVector"] = 30. # % total abs of vector change
							try:	BLEsensorMACs[mac]["updateIndigoDeltaMaxXYZ"] = float(sensD["updateIndigoDeltaMaxXYZ"])
							except: BLEsensorMACs[mac]["updateIndigoDeltaMaxXYZ"] = 30. # N/s*s *1000 
							try:	BLEsensorMACs[mac]["updateIndigoDeltaTemp"] = float(sensD["updateIndigoDeltaTemp"])
							except: BLEsensorMACs[mac]["updateIndigoDeltaTemp"] = 1 # =1C 
							try:	BLEsensorMACs[mac]["minSendDelta"] 			= float(sensD["minSendDelta"])
							except: BLEsensorMACs[mac]["minSendDelta"] 			= 4 #  seconds betwen updates
							if "accelerationTotal" not in BLEsensorMACs[mac]:
								BLEsensorMACs[mac]["accelerationTotal"]				= 0
								BLEsensorMACs[mac]["accelerationX"]				 	= 0
								BLEsensorMACs[mac]["accelerationY"]				 	= 0
								BLEsensorMACs[mac]["accelerationZ"]				 	= 0
								BLEsensorMACs[mac]["temp"]				 			= -100
								BLEsensorMACs[mac]["lastUpdate"]				 	= 0

			U.logger.log(30, "BLE sensors found: {}".format(BLEsensorMACs) )
		except	Exception, e:
			U.logger.log(30,u"in Line {} has error={}".format(sys.exc_traceback.tb_lineno, e))

	except	Exception, e:
		U.logger.log(30,u"in Line {} has error={}".format(sys.exc_traceback.tb_lineno, e))

	return	True

		
def doSensors(pkt, mac, rx, tx, nBytesThisMSG, hexData, UUID, Maj, Min):
	global BLEsensorMACs
	bl = ""
	try:

		if mac in BLEsensorMACs and BLEsensorMACs[mac]["type"] == "myBLUEt":  								
			return domyBlueT( pkt, mac, rx, tx, nBytesThisMSG, hexData, UUID, Maj, Min)

		## check if Ruuvi tag present at right position, should be at pos 22
		ruuviTagPos 	= hexData.find("FF990405") 
		ruuviTagFound	= ruuviTagPos > 20 and ruuviTagPos < 24 # give range just in case
		ruuviSensorActive = ( mac in BLEsensorMACs  and BLEsensorMACs[mac]["type"] == "RuuviTag")
		#if mac == "ED:1B:05:6E:CA:59":
		#	U.logger.log(30,u"ruuvitag -1 mac:{};  pos={}; ruuviSensorActive:{}, hexData:{}".format(mac, ruuviTagPos, ruuviSensorActive, hexData))
		if ruuviTagFound or ruuviSensorActive: 
			return  doRuuviTag(pkt, mac, rx, tx, nBytesThisMSG, hexData, ruuviTagPos, ruuviSensorActive, UUID, Maj, Min)

	except	Exception, e:
		U.logger.log(30,u"in Line {} has error={}".format(sys.exc_traceback.tb_lineno, e))
	return tx, bl, UUID, Maj, Min, False


#################################
def domyBlueT(pkt,UUID,Maj,Min,mac,rx,tx):
	global BLEsensorMACs, sensor
	try:
		data ={sensor:{}}
		if mac not in BLEsensorMACs: return 
		if time.time() - BLEsensorMACs[mac]["lastUpdate"]  < BLEsensorMACs[mac]["updateIndigoTiming"]: 
			#print "rejecting ", time.time() - BLEsensorMACs[mac]["lastUpdate"] ,  BLEsensorMACs[mac]["updateIndigoTiming"]
			return 
		#print "accepting ", time.time() - BLEsensorMACs[mac]["lastUpdate"] ,  BLEsensorMACs[mac]["updateIndigoTiming"]
		BLEsensorMACs[mac]["lastUpdate"] = time.time()
		devId		= BLEsensorMACs[mac]["devId"]
		data		= {sensor:{devId:{}}}
		if BLEsensorMACs[mac]["type"] == "myBLUEt":
			RawData = list(struct.unpack("BBB", pkt[31:34])) # get bytes # 31,32,33	 (starts at # 0 , #33 has sign, if !=0 subtract 2**15
			if RawData[2] != 0: tSign = 0x10000 # == 65536 == 2<<15
			else:				tSign = 0
			r8			= RawData[1] << 8 
			sensorData	= ( r8 + RawData[0] - tSign ) /100.
			UUID		= UUID[0:12]+"-"+Maj+"-"+Min
			try:	temp  = (sensorData + BLEsensorMACs[mac]["offsetTemp"]) * BLEsensorMACs[mac]["multiplyTemp"]
			except: temp  = sensorData
			data[sensor][devId] = {"temp":temp,"type":BLEsensorMACs[mac]["type"],"mac":mac,"rssi":float(rx),"txPower":float(tx),"UUID":UUID}
		elif BLEsensorMACs[mac]["type"] =="blueRadio":
			return 
			#RawData = list(struct.unpack("BBB", pkt[31:34])) # get bytes # 31,32,33  (starts at # 0 , #33 has sign, if !=0 subtract 2**15
			#if RawData[2] != 0: tSign = 0x10000 # == 65536 == 2<<15
			#else:				 tSign = 0
			#r8			 = RawData[1] << 8 
			#sensorData	 = ( r8 + RawData[0] - tSign ) /100.
			#UUID		 = UUID[0:12]+"-"+Maj+"-"+Min
			#try:	 temp  = (sensorData + BLEsensorMACs[mac]["offsetTemp"]) * BLEsensorMACs[mac]["multiplyTemp"]
			#except: temp  = sensorData
			#data[sensor][devId] = {"temp":temp,"type":BLEsensorMACs[mac]["type"],"mac":mac,"rssi":float(rx),"txPower":float(tx),"UUID":UUID}
		elif BLEsensorMACs[mac]["type"] == "windWeatherFlow":
			U.logger.log(30,"{} {} {} {} pkt: {} {}".format(mac, UUID, Maj, Min, len(pkt), pkt) )
			RawData = list(struct.unpack("BBBBBBBBB", pkt[31:31+(2+2+2+2+1)])) # get 25 bytes  
			U.logger.log(30, "RawData: {}".format(RawData))
			start= 0
			name  = "", RawData[0:16]
			wind  = (RawData[start+0] <<8 + RawData[start+2])/10.
			temp  = (RawData[start+2] <<8 + RawData[start+4])/10.
			windC = (RawData[start+4] <<8 + RawData[start+8])/10.
			Batt  = (RawData[start+6] <<8 + RawData[start+8])/10.
			pow	  =	 RawData[start+8]
			
			UUID		= UUID[0:12]+"-"+Maj+"-"+Min
			sensor		= "BLEsensor"
			devId		= BLEsensorMACs[mac]["devId"]
			try:	wind  = (wind + BLEsensorMACs[mac]["offsetWind"]) * BLEsensorMACs[mac]["multiplyWind"]
			except: wind  = wind
			try:	temp  = (temp + BLEsensorMACs[mac]["offsetTemp"]) * BLEsensorMACs[mac]["multiplyTemp"]
			except: temp  = temp
			data[sensor][devId] = {"temp":temp,"Wind":wind,"WindChill":windC,"Battery":Batt,"Power":pow, "type":BLEsensorMACs[mac]["type"],"mac":mac,"rssi":float(rx),"txPower":float(tx),"UUID":UUID}


			print "wind, temp, windC, Batt, pow ", wind, temp, windC, Batt, pow
		if data[sensor][devId] !={}:	
			U.sendURL({"sensors":data})

	except	Exception, e:
		U.logger.log(30,u"in Line {} has error={}".format(sys.exc_traceback.tb_lineno, e))
		#print RawData				
	""" from the sensor web site:
		private void submitScanResult(BluetoothDevice device, int rssi, byte[] scanRecord)
		{
			int temp;
			 // device has hw address and name, signal strength in rssi, raw packet in scanRecord

			// temperature in C (* 100) appears to be in bytes 17 and 18, maybe 19..
			// TODO no official docs on this (?)
			// this seems to cover usable range
			if ((0xff & scanRecord[19]) == 0xff)
			{
				temp = (0xff & scanRecord[18]) * 256;
				temp += (0xff & scanRecord[17]);
				temp = temp - 0x10000;
			}
			else
			{
				temp = (0xff & scanRecord[18]) * 256;
				temp += (0xff & scanRecord[17]);
			}
			if (this.resultReceiver != null) {
				Bundle b = new Bundle();
				b.putString("scanResult", device.getAddress() + ": " + (temp / 100.0)+	" C / " + ((temp / 100.0) * 9.0 / 5.0 + 32.0) + " F");
				this.resultReceiver.send(0, b);
			}
		}

		WIND sensor `
		typedef struct __attribute__((packed)){
		char deviceName[16]; // meter name
		UInt16 windSpeed; // wind speed
		UInt16 airTemprature; // air temperature
		UInt16 windChill; // wind chill
		UInt16 batteryLevel; // battery level
		char apoByte; // automatic power off byte
		} Packet;
		

	"""						   
	return
#################################
def domyBlueT(pkt, mac, rx, tx, nBytesThisMSG, hexData, UUID, Maj, Min):
	global BLEsensorMACs
	try:
		RawData = list(struct.unpack("BBB", pkt[31:34])) # get bytes # 31,32,33	 (starts at # 0 , #33 has sign, if !=0 subtract 2**15
		if RawData[2] != 0: tSign = 0x10000 # == 65536 == 2<<15
		else:				tSign = 0
		r8				= RawData[1] << 8 
		sensorData		= ( r8 + RawData[0] - tSign ) /100.
		sensor			= "BLEsensor"
		devId			= BLEsensorMACs[mac]["devId"]
		try:	temp  	= (sensorData + BLEsensorMACs[mac]["offsetTemp"]) * BLEsensorMACs[mac]["multiplyTemp"]
		except: temp  	= sensorData
		U.logger.log(10, "{}   RX:{}; TX:{}; temp:{}; nBytes:{}".format(mac, rx, tx, temp, nBytesThisMSG) )
		# print "raw, tSign, t1<<8, sensorData, sensorData*9./5 +32.", RawData, tSign, r8, temp, sensorData, sensorData*9./5 +32.
		if time.time() - BLEsensorMACs[mac]["lastUpdate"]  > BLEsensorMACs[mac]["updateIndigoTiming"]: 
			data   = {sensor:{devId:{}}}
			data[sensor][devId] = {"temp":temp, "type":BLEsensorMACs[mac]["type"],"mac":mac,"rssi":float(rx),"txPower":float(tx)}
			U.sendURL({"sensors":data})
			BLEsensorMACs[mac]["lastUpdate"] = time.time()
		return tx, "", "myBlueT", mac, "sensor", True
	except	Exception, e:
		U.logger.log(30,u"in Line {} has error={}".format(sys.exc_traceback.tb_lineno, e))
	return tx, "", UUID, Maj, Min, True
		#print RawData				
	""" from the sensor web site:
		private void submitScanResult(BluetoothDevice device, int rssi, byte[] scanRecord)
		{
			int temp;
			 // device has hw address and name, signal strength in rssi, raw packet in scanRecord

			// temperature in C (* 100) appears to be in bytes 17 and 18, maybe 19..
			// TODO no official docs on this (?)
			// this seems to cover usable range
			if ((0xff & scanRecord[19]) == 0xff)
			{
				temp = (0xff & scanRecord[18]) * 256;
				temp += (0xff & scanRecord[17]);
				temp = temp - 0x10000;
			}
			else
			{
				temp = (0xff & scanRecord[18]) * 256;
				temp += (0xff & scanRecord[17]);
			}
			if (this.resultReceiver != null) {
				Bundle b = new Bundle();
				b.putString("scanResult", device.getAddress() + ": " + (temp / 100.0)+	" C / " + ((temp / 100.0) * 9.0 / 5.0 + 32.0) + " F");
				this.resultReceiver.send(0, b);
			}
		}
	"""						   


#################################
#################################
## Ruuvi ########################
#################################
def doRuuviTag(pkt, mac, rx, tx, nBytesThisMSG,hexData, ruuviTagPos, ruuviSensorActive, UUID, Maj, Min):
	global BLEsensorMACs, sensors

	""" ruuvi data format: https://github.com/ruuvi/ruuvi-sensor-protocols/blob/master/dataformat_05.md
offset	Allowed Values		description
0		5					Data format (8bit)
1-2		-32767 ... 32767	Temperature in 0.005 degrees
3-4		0 ... 40 000		Humidity (16bit unsigned) in 0.0025% (0-163.83% range, though realistically 0-100%)
5-6		0 ... 65534			Pressure (16bit unsigned) in 1 Pa units, with offset of -50 000 Pa
7-8		-32767 ... 32767	Acceleration-X (Most Significant Byte first)
9-10	-32767 ... 32767	Acceleration-Y (Most Significant Byte first)
11-12	-32767 ... 32767	Acceleration-Z (Most Significant Byte first)
13-14	0...2046, 0...30	Power info (11+5bit unsigned), first 11 bits is the battery voltage above 1.6V, in millivolts (1.6V to 3.646V range). 
							Last 5 bits unsigned are the TX power above -40dBm, in 2dBm steps. (-40dBm to +20dBm range)
15		0 ... 254			Movement counter (8 bit unsigned), incremented by motion detection interrupts from accelerometer
16-17	0 ... 65534			Measurement sequence number (16 bit unsigned), each time a measurement is taken, this is incremented by one, used for measurement de-duplication. 
							Depending on the transmit interval, multiple packets with the same measurements can be sent, and there may be measurements that never were sent.
18-23	Any valid mac		48bit MAC address, should be same as in message  (==mac)
	"""

	try:
		
		if len(hexData) < ruuviTagPos+24:  # 24 = number of bytes for ruuvi data required
			return tx, "", UUID, Maj, Min, False

		UUID 						= "ruuviTag"
		Maj  						= mac
		Min  						= "sensor"
		sensor 						= "BLERuuviTag"
		# make data into right format (bytes)
		byte_data 					= bytearray.fromhex(hexData[ruuviTagPos + 6:])
		# umpack the first set of data

		if not ruuviSensorActive: # we have found the ruuvitag, but the sensor is not active on this RPI, but the iBeacon is
			# overwrite UUID etc for this ibeacon if used later
			return tx, "", UUID, Maj, Min, False

		# sensor is active, get all data and send if conditions ok


		# unpack  rest of sensor data 
		accelerationTotal, accelerationX, accelerationY, accelerationZ 	= doRuuviTag_magValues(byte_data)
		temp 					= doRuuviTag_temperature(byte_data)
		batteryVoltage, txPower = doRuuviTag_powerinfo(byte_data)
		battreyLowVsTemp		= (1. + min(0,temp-8)/100.) * 2900 # (changes to 2871 @ -2C; to = 2842 @-12C )
		batteryLevel 			= int(min(100,max(0,100* (batteryVoltage - battreyLowVsTemp)/(3200.-battreyLowVsTemp))))
		# make deltas compared to last send 
		dX 			= abs(BLEsensorMACs[mac]["accelerationX"]		- accelerationX)
		dY 			= abs(BLEsensorMACs[mac]["accelerationY"]		- accelerationY)
		dZ 			= abs(BLEsensorMACs[mac]["accelerationZ"]		- accelerationZ)
		dTot 		= math.sqrt(dX*dX +dY*dY +dZ*dZ) # in N/s**2 *1000
		deltaXYZ	= int(max(dX, dY, dZ))  # in N/s**2 *1000

		deltatemp 	= abs(BLEsensorMACs[mac]["temp"] - temp)  
		deltaTime 	= time.time() - BLEsensorMACs[mac]["lastUpdate"]

		# check if we should send data to indigo
		trigMinTime	= deltaTime 	> BLEsensorMACs[mac]["minSendDelta"] 				# dont send too often
		trigTime 	= deltaTime 	> BLEsensorMACs[mac]["updateIndigoTiming"]  			# send min every xx secs
		trigTemp 	= deltatemp 	> BLEsensorMACs[mac]["updateIndigoDeltaTemp"] 			# temp change triggers
		trigAccel 	= dTot			> BLEsensorMACs[mac]["updateIndigoDeltaAccelVector"] 	# acceleration change triggers 
		trigDeltaXZY= deltaXYZ		> BLEsensorMACs[mac]["updateIndigoDeltaMaxXYZ"]			# acceleration-turn change triggers 
		trig = ""
		if trigTime:		trig += "Time/"
		else:
			if trigTemp: 	trig += "Temp/"
			if trigAccel:	trig += "Accel-Total/"
			if trigDeltaXZY:trig += "Accel-Max-xyz/"
		#U.logger.log(20, "mac:{}    trigMinTime:{} deltaXYZ:{}, trig:{}".format(mac, trigMinTime, deltaXYZ, trig) )

		if trigMinTime and	( trigTime or trigTemp or trigAccel or trigDeltaXZY ):
			dd={   # the data dict to be send 
				'data_format': 5,
				'hum': 					int(doRuuviTag_humidity(byte_data)	 + BLEsensorMACs[mac]["offsetHum"]),
				'temp': 				round(temp							 + BLEsensorMACs[mac]["offsetTemp"],2),
				'press': 				round(doRuuviTag_pressure(byte_data) + BLEsensorMACs[mac]["offsetPress"],1),
				'accelerationTotal': 	int(accelerationTotal),
				'accelerationX': 		int(accelerationX),
				'accelerationY': 		int(accelerationY),
				'accelerationZ': 		int(accelerationZ),
				'accelerationXYZMaxDelta':int(deltaXYZ),
				'accelerationVectorDelta':int(dTot),
				'batteryLevel': 		int(batteryLevel),
				'batteryVoltage': 		int(batteryVoltage),
				'movementCount': 		int(doRuuviTag_movementcounter(byte_data)),
				'measurementCount': 	int(doRuuviTag_measurementsequencenumber(byte_data)),
				'trigger': 				trig.strip("/"),
				'txPower': 				int(txPower),
				"rssi":					int(rx),
			}
			#U.logger.log(20, " .... sending  data:{}".format( dd ) )

			## compose complete message
			U.sendURL({"sensors":{sensor:{BLEsensorMACs[mac]["devId"]:dd}}})

			# remember last values
			BLEsensorMACs[mac]["lastUpdate"] 			= time.time()
			BLEsensorMACs[mac]["accelerationTotal"] 	= accelerationTotal
			BLEsensorMACs[mac]["accelerationX"] 		= accelerationX
			BLEsensorMACs[mac]["accelerationY"] 		= accelerationY
			BLEsensorMACs[mac]["accelerationZ"] 		= accelerationZ
			BLEsensorMACs[mac]["temp"] 					= temp

		# overwrite UUID etc for this ibeacon if used later
		return str(txPower), str(batteryLevel), UUID, Maj, Min, False

	except	Exception, e:
		U.logger.log(30,u"in Line {} has error={}".format(sys.exc_traceback.tb_lineno, e))
	# return incoming parameetrs
	return tx, "", UUID, Maj, Min, False


#################################
def doRuuviTag_temperature( data):
	"""Return temperature in celsius"""
	if data[1:2] == 0x7FFF:
		return 0

	temperature = twos_complement((data[1] << 8) + data[2], 16) / 200
	return round(temperature, 2)

#################################
def doRuuviTag_humidity( data):
	"""Return humidity %"""
	if data[3:4] == 0xFFFF:
		return 0

	humidity = ((data[3] & 0xFF) << 8 | data[4] & 0xFF) / 400
	return round(humidity, 2)

#################################
def doRuuviTag_pressure( data):
	"""Return air pressure hPa"""
	if data[5:6] == 0xFFFF:
		return 0

	pressure = ((data[5] & 0xFF) << 8 | data[6] & 0xFF) + 50000
	return round(pressure, 1)

#################################
def doRuuviTag_magValues( data):
	"""Return mageration mG"""
	if (data[7:8] == 0x7FFF or
			data[9:10] == 0x7FFF or
			data[11:12] == 0x7FFF):
		return (0, 0, 0)

	acc_x = twos_complement((data[7] << 8) + data[8], 16)
	acc_y = twos_complement((data[9] << 8) + data[10], 16)
	acc_z = twos_complement((data[11] << 8) + data[12], 16)
	return math.sqrt(acc_x * acc_x + acc_y * acc_y + acc_z * acc_z), acc_x, acc_y, acc_z

#################################
def doRuuviTag_powerinfo( data):
	"""Return battery voltage and tx power"""
	power_info = (data[13] & 0xFF) << 8 | (data[14] & 0xFF)
	battery_voltage = rshift(power_info, 5) + 1600
	tx_power = (power_info & 0b11111) * 2 - 40

	if rshift(power_info, 5) == 0b11111111111:
		battery_voltage = 0
	if (power_info & 0b11111) == 0b11111:
		tx_power = -9999
	#print  (round(battery_voltage, 3), tx_power)

	return (battery_voltage, tx_power)


#################################
def doRuuviTag_movementcounter( data):
	return data[15] & 0xFF

#################################
def doRuuviTag_measurementsequencenumber( data):
	measurementSequenceNumber = (data[16] & 0xFF) << 8 | data[17] & 0xFF
	return measurementSequenceNumber

#################################
def doRuuviTag_mac( data):
	return ''.join('{:02x}'.format(x) for x in data[18:24])

#################################
## Ruuvi  END   #################
#################################


####### main pgm / loop ############


#################################



####### main pgm / loop ############

def execBLEsensor():
	global myBLEmac, BLEsensorMACs
	global oldRaw,	lastRead, sensor
	global downCount

	downCount			= 0
	oldRaw				= ""
	lastRead			= 0
	G.authentication	= "digest"
	myBLEmac			= ""
	BLEsensorMACs		= {}

	myPID			= str(os.getpid())
	U.setLogging()
	U.killOldPgm(myPID,"{}.py".format(G.program))

	sensor				= G.program	 
	readParams(True)

	# getIp address 
	if U.getIPNumber() > 0:
		U.logger.log(30, " no ip number exiting" )
		time.sleep(10)
		return 


## start bluetooth

	## start bluetooth
	for ii in range(5):
		sock, myBLEmac, retCode= startBlueTooth(G.myPiNumber)  
		if retCode ==0: break 
		time.sleep(3)
	if retCode != 0: 
		U.logger.log(30,"beaconloop exit, recode from getting BLE stack >0, after 3 tries:")
		return 


	
	loopCount	 = 0
	tt			 = time.time()
	paramCheck	 = tt

	U.echoLastAlive(G.program)
	U.logger.log(30,"starting loop" )
	G.tStart= time.time()

	errCount = 0
	try:
		while True:
			tt = time.time()
				   
			
			timeAtLoopStart = tt


			old_filter = sock.getsockopt( bluez.SOL_HCI, bluez.HCI_FILTER, 14)

			# perform a device inquiry on bluetooth device #0
			# The inquiry should last 8 * 1.28 = 10.24 seconds
			# before the inquiry is performed, bluez should flush its cache of
			# previously discovered devices
			flt = bluez.hci_filter_new()
			bluez.hci_filter_all_events(flt)
			bluez.hci_filter_set_ptype(flt, bluez.HCI_EVENT_PKT)
			sock.setsockopt( bluez.SOL_HCI, bluez.HCI_FILTER, flt )


			ii = 1000
			while ii>0:
				ii-=1
				tt=time.time()
				quick = U.checkNowFile(sensor)				  
				if tt - paramCheck >2:
					newParametersFile = readParams(False)
					paramCheck=time.time()
					if newParametersFile: 
						quick = True

				## get new data
	#			 allBeaconMSGs = parse_events(sock, collectMsgs,offsetUUID,batteryLevelPosition,maxParseSec ) # get the data:  get up to #collectMsgs at one time
				allBeaconMSGs=[]
				try:	
					pkt = sock.recv(255)
					errCount = 0
				except	Exception, e:
					for ii in range(30):
						if os.path.isfile("{}temp/stopBLE".format(G.homeDir)):
							time.sleep(5)
						else:
							break
					subprocess.call("rm {}temp/stopBLE".format(G.homeDir), shell=True)
					U.logger.log(50, u"in Line {} has error={}.. sock.recv error, likely time out ".format(sys.exc_traceback.tb_lineno, e))
					time.sleep(1)
					U.restartMyself(param="", reason="sock.recv error")
					U.logger.log(50,u"in Line {} has error={}".format(sys.exc_traceback.tb_lineno, e))
					errCount += 1
					if errCount > 3:
						break

				doP = False
				if len(pkt) > 15: 
					num_reports = struct.unpack("B", pkt[4])[0]
					num_reports =1
					try:
						offS = 7
						for i in range(0, num_reports):
							if len(pkt) < offS + 6: 
								U.logger.log(30,"bad data "+unicode(i)+"  "+unicode(num_reports)+"  "+unicode(offS + 6)+"  " +unicode(len(pkt)) + " xx" )
								break
							# build the return string: mac#, uuid-major-minor,txpower??,rssi
							mac	 = (packed_bdaddr_to_string(pkt[offS :offS + 6])).upper()
							hexData	 			= (stringFromPacket(pkt[offS:])).upper()
							
							pkLen				= len(pkt)
							nBytesThisMSG		= ord(pkt[offS+6])

							msgStart			= offS+7
							AD1Len				= ord(pkt[msgStart])
							AD1Start			= msgStart+1
							if nBytesThisMSG > 17:
								AD2Len			= ord(pkt[AD1Start+AD1Len])
								AD2Start		= AD1Start+AD1Len +1
							else:
								AD2Len			= AD1Len
								AD2Start		= AD1Start

							offsetU			= 0
							uuidStart		= AD2Start ##  (-Maj-Min-batteryLength-TX-RSSI)
							uuidLen			= msgStart+nBytesThisMSG-uuidStart-2-2-1-offsetU
							if uuidStart > pkLen-2 or  uuidStart < 12:
								uuidLen			 = min(nBytesThisMSG-5,16)
								uuidStart		 = AD1Start+2

							UUID = returnstringpacket(pkt[uuidStart : uuidStart +uuidLen])

							if len(UUID)>32:
								UUID=UUID[len(UUID)-32:]  # drop AD2 stuff only used the real UUID 
							Maj	 = "%i" % returnnumberpacket(pkt[uuidStart+uuidLen	: uuidStart+uuidLen+2])
							Min	 = "%i" % returnnumberpacket(pkt[uuidStart+uuidLen+2: uuidStart+uuidLen+4])
							#lastB = 
							tx	 = "%i" % struct.unpack("b", pkt[ -2 ])
							rx	 = "%i" % struct.unpack("b", pkt[ -1 ])

							doSensors(pkt, mac, rx, tx, nBytesThisMSG, hexData, UUID, Maj, Min)
							time.sleep(1)
							break


					except	Exception, e:
						U.logger.log(50,u"in Line {} has error={}".format(sys.exc_traceback.tb_lineno, e))
						U.logger.log(30, " BLEsensor "+"bad data") 
						continue# skip if bad data

			sock.setsockopt( bluez.SOL_HCI, bluez.HCI_FILTER, old_filter )
			#print "reason",datetime.datetime.now(), reason
			U.echoLastAlive(G.program)
	except	Exception, e:
		U.logger.log(50,u"in Line {} has error={}".format(sys.exc_traceback.tb_lineno, e))
		U.logger.log(30, "  exiting loop due to error\n")
execBLEsensor()
print ("{} BLEsensor end of {}".format( datetime.datetime.now().strftime("%Y%m%d-%H:%M:%S"), G.program) ) 
try: 	G.sendThread["run"] = False; time.sleep(1)
except: pass
sys.exit(0)

