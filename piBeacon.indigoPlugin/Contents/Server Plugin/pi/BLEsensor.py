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
	global myBLEmac
	try:
		## good explanation: http://gaiger-G.programming.blogspot.com/2015/01/bluetooth-low-energy.html
		U.toLog(-1,"(re)starting bluetooth", doPrint = True)
		ret = subprocess.Popen("hciconfig hci0 down ",shell=True,stdout=subprocess.PIPE,stderr=subprocess.PIPE).communicate()  # enable bluetooth
		time.sleep(0.2)
		ret = subprocess.Popen("hciconfig hci0 up ",shell=True,stdout=subprocess.PIPE,stderr=subprocess.PIPE).communicate()	 # enable bluetooth
		#ret = subprocess.Popen("hciconfig hci0 leadv 3",shell=True,stdout=subprocess.PIPE,stderr=subprocess.PIPE).communicate() # enable ibeacon signals, next is the ibeacon message
		HCIs = U.whichHCI()
		useHCI,  myBLEmac, devId = U.selectHCI(HCIs, G.BLEconnectUseHCINo,"UART")
		if devId <0 :
			return 0,  "", -1,
		U.toLog(-1,"MAC#:%s; on useHCI:%s;  HCIs:%s; devId:%s"%(myBLEmac,unicode(useHCI), unicode(HCIs), unicode(devId) ), doPrint = True) 

			

		#ret = subprocess.Popen("hciconfig hci0 leadv 3",shell=True,stdout=subprocess.PIPE,stderr=subprocess.PIPE).communicate() # enable ibeacon signals, next is the ibeacon message
		OGF					= " 0x08"
		OCF					= " 0x0008"
		iBeaconPrefix		= " 1E 02 01 1A 1A FF 4C 00 02 15"
		uuid				= " 2f 23 44 54 cf 6d 4a 0f ad f2 f4 91 1b a9 ff a6"
		maj					= " 00 09"
		min					= " 00 "+"0%x"%(int(pi))
		txP					= " C5 00"
		cmd	 = "hcitool -i "+useHCI+" cmd" + OGF + OCF + iBeaconPrefix + uuid + maj + min + txP
		U.toLog(-1,cmd, doPrint=True )
		ret = subprocess.Popen(cmd,shell=True,stdout=subprocess.PIPE,stderr=subprocess.PIPE).communicate()
		####################################set adv params		minInt	 maxInt		  nonconectable	 +??  <== THIS rpi to send beacons every 10 secs only 
		#											   00 40=	0x4000* 0.625 msec = 16*4*256 = 10 secs	 bytes are reverse !! 
		#											   00 10=	0x1000* 0.625 msec = 16*1*256 = 2.5 secs
		#											   00 04=	0x0400* 0.625 msec =	4*256 = 0.625 secs
		cmd	 = "hcitool -i "+useHCI+" cmd" + OGF + " 0x0006"	  + " 00 10"+ " 00 20" +  " 03"			   +   " 00 00 00 00 00 00 00 00 07 00"
		## maxInt= A0 00 ==	 100ms;	 40 06 == 1000ms; =0 19 = 4 =seconds  (0x30x00	==> 64*256*0.625 ms = 10.024secs  use little endian )
		U.toLog(-1,cmd, doPrint=True )
		ret = subprocess.Popen(cmd,shell=True,stdout=subprocess.PIPE,stderr=subprocess.PIPE).communicate()
		####################################LE Set Advertise Enable
		cmd	 = "hcitool -i "+useHCI+" cmd" + OGF + " 0x000a" + " 01"
		U.toLog(-1,cmd, doPrint=True )
		ret = subprocess.Popen(cmd,shell=True,stdout=subprocess.PIPE,stderr=subprocess.PIPE).communicate()

		ret = subprocess.Popen("hciconfig ",shell=True,stdout=subprocess.PIPE,stderr=subprocess.PIPE).communicate()
		U.toLog(-1,"BLE start returned :  "+unicode(ret))
	except Exception, e: 
		U.toLog(-1,"beaconloop exit at restart BLE stack error:"+unicode(e),permanentLog=True, doPrint=True )
		time.sleep(10)
		f = open(G.homeDir+"temp/restartNeeded","w")
		f.write("bluetooth_startup.ERROR:"+unicode(e))
		f.close()
		subprocess.Popen("hciconfig "+useHCI+" down ",shell=True,stdout=subprocess.PIPE,stderr=subprocess.PIPE).communicate()  # enable bluetooth
		subprocess.Popen("service bluetooth restart ",shell=True ,stdout=subprocess.PIPE,stderr=subprocess.PIPE).communicate()
		subprocess.Popen("service dbus restart ",shell=True ,stdout=subprocess.PIPE,stderr=subprocess.PIPE).communicate()
		return 0, "", -5

	U.toLog(-1,"my BLE mac# is : "+ unicode(myBLEmac))
	if myBLEmac !="":
		f=open(G.homeDir+"myBLEmac","w")
		f.write(myBLEmac)
		f.close()

	try:
		sock = bluez.hci_open_dev(devId)
		U.toLog(-1, "ble thread started")
	except	Exception, e:
		U.toLog(-1,"error accessing bluetooth device..."+unicode(e),permanentLog=True)
		f = open(G.homeDir+"temp/rebootNeeded","w")
		f.write("bluetooth_startup.ERROR:"+unicode(e))
		f.close()
		subprocess.Popen("hciconfig "+useHCI+" down ",shell=True,stdout=subprocess.PIPE,stderr=subprocess.PIPE).communicate()  # enable bluetooth
		subprocess.Popen("service bluetooth restart ",shell=True ,stdout=subprocess.PIPE,stderr=subprocess.PIPE).communicate()
		subprocess.Popen("service dbus restart ",shell=True ,stdout=subprocess.PIPE,stderr=subprocess.PIPE).communicate()
		return 0,  "", -1
		
	try:
		hci_le_set_scan_parameters(sock)
		hci_enable_le_scan(sock)
	except	Exception, e:
		U.toLog(-1, u"in Line {} has error={}".format(sys.exc_traceback.tb_lineno, e),permanentLog=True)
		if unicode(e).find("Bad file descriptor") >-1:
			f = open(G.homeDir+"temp/rebootNeeded","w")
			f.write("bluetooth_startup.ERROR:Bad_file_descriptor...SSD.damaged?")
			f.close()
		if unicode(e).find("Network is down") >-1:
			f = open(G.homeDir+"temp/rebootNeeded","w")
			f.write("bluetooth_startup.ERROR:Network_is_down...need_to_reboot")
			f.close()
		subprocess.Popen("hciconfig "+useHCI+" down ",shell=True,stdout=subprocess.PIPE,stderr=subprocess.PIPE).communicate()  # enable bluetooth
		subprocess.Popen("service bluetooth restart ",shell=True ,stdout=subprocess.PIPE,stderr=subprocess.PIPE).communicate()
		subprocess.Popen("service dbus restart ",shell=True ,stdout=subprocess.PIPE,stderr=subprocess.PIPE).communicate()
		return 0,  "", -1
	return sock,  myBLEmac, devId






def readParams(init):
	global BLEsensorMACs
	global oldRaw,	lastRead, sensor
	if init:
		G.debug			  = 2
		G.ipOfServer	  =""
		G.passwordOfServer=""
		G.userIdOfServer  =""
		G.myPiNumber	  ="0"

	inp,inpRaw,lastRead2 = U.doRead(lastTimeStamp=lastRead)
	if inp == "":				return False
	if lastRead2 == lastRead:	return False
	lastRead   = lastRead2
	if inpRaw == oldRaw:		return False
	oldRaw	   = inpRaw

	try:
		U.getGlobalParams(inp)

		if "debugRPI"			in inp:	 G.debug=			  int(inp["debugRPI"]["debugRPIBEACON"])
		if "rebootSeconds"		in inp:	 rebootSeconds=		  int(inp["rebootSeconds"])
		if "enableRebootCheck"	in inp:	 enableRebootCheck=		 (inp["enableRebootCheck"])
		if "sendAfterSeconds"	in inp:	 sendAfterSeconds=	  int(inp["sendAfterSeconds"])

		BLEsensorMACs = {}
		sensor		  = "BLEsensor"
		if "sensors"			 in inp: 
			sensors =				 (inp["sensors"])
			if sensor in sensors:
				for devId in sensors[sensor]:
					sensD	= sensors[sensor][devId]
					mac		= sensD["mac"]
					BLEsensorMACs[mac]={}
					BLEsensorMACs[mac]["type"]						 = sensD["type"]
					BLEsensorMACs[mac]["devId"]						 = devId
					try:	BLEsensorMACs[mac]["offsetTemp"]		 = float(sensD["offsetTemp"])
					except: BLEsensorMACs[mac]["offsetTemp"]		 = 0.
					try:	BLEsensorMACs[mac]["multiplyTemp"]		 = float(sensD["multiplyTemp"])
					except: BLEsensorMACs[mac]["multiplyTemp"]		 = 1.
					try:	BLEsensorMACs[mac]["offsetWind"]		 = float(sensD["offsetWind"])
					except: BLEsensorMACs[mac]["offsetWind"]		 = 0.
					try:	BLEsensorMACs[mac]["multiplyWind"]		 = float(sensD["multiplyWind"])
					except: BLEsensorMACs[mac]["multiplyWind"]		 = 1.
					try:	BLEsensorMACs[mac]["updateIndigoTiming"] = float(sensD["updateIndigoTiming"])
					except: BLEsensorMACs[mac]["updateIndigoTiming"] = 0.
					BLEsensorMACs[mac]["lastUpdate"]				 = -1
		U.toLog(-1, "BLE sensors found: %s"%unicode(BLEsensorMACs), doPrint=True )

	except	Exception, e:
		U.toLog(-1,u"in Line {} has error={}".format(sys.exc_traceback.tb_lineno, e))

	return	True

		


#################################
def doSensors(pkt,UUID,Maj,Min,mac,rx,tx):
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
		if BLEsensorMACs[mac]["type"] =="myBLUEt":
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
		elif BLEsensorMACs[mac]["type"] =="windWeatherFlow":
			U.toLog(-1, unicode(mac)+" "+unicode(UUID)+" "+unicode( Maj)+" "+unicode(Min) +"pkt: "+unicode(len(pkt)) +" "+unicode(pkt), doPrint=True )
			RawData = list(struct.unpack("BBBBBBBBB", pkt[31:31+(2+2+2+2+1)])) # get 25 bytes  
			U.toLog(-1, "RawData: %s"%unicode(RawData),doPrint=True )
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
		U.toLog(-1,u"in Line {} has error={}".format(sys.exc_traceback.tb_lineno, e), doPrint=True)
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


####### main pgm / loop ############


#################################



####### main pgm / loop ############


global myBLEmac, BLEsensorMACs
global oldRaw,	lastRead, sensor
oldRaw					= ""
lastRead				= 0
G.debug				= 2
G.authentication	= "digest"
# get params
myBLEmac			= ""
BLEsensorMACs		= {}

myPID			= str(os.getpid())
#kill old G.programs
U.killOldPgm(myPID,G.program+".py")



sensor				= G.program	 
readParams(True)


# getIp address 
if U.getIPNumber() > 0:
	U.toLog(-1, " no ip number ", doPrint=True )
	time.sleep(10)
	exit()


## start bluetooth
sock,  myBLEmac, retCode = startBlueTooth(G.myPiNumber)  
if retCode <0: 
	U.toLog(-1, " stopping due to bad BLE start ", doPrint=True )
	sys.exit(1)

	
loopCount	 = 0
tt			 = time.time()
paramCheck	 = tt

U.echoLastAlive(G.program)
U.toLog(-1,"starting loop", doPrint=True )
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
				U.toLog(-1,u"in Line {} has error={}".format(sys.exc_traceback.tb_lineno, e),permanentLog=True)
				errCount += 1
				if errCount > 3:
					break
				pkt =[]

			doP = False
			if len(pkt) > 15: 
				num_reports = struct.unpack("B", pkt[4])[0]
				num_reports =1
				try:
					offS = 7
					for i in range(0, num_reports):
						if len(pkt) < offS + 6: 
							U.toLog(-1,"bad data "+unicode(i)+"  "+unicode(num_reports)+"  "+unicode(offS + 6)+"  " +unicode(len(pkt)) + " xx", doPrint=True )
							break
						# build the return string: mac#, uuid-major-minor,txpower??,rssi
						mac	 = (packed_bdaddr_to_string(pkt[offS :offS + 6])).upper()
						if mac not in BLEsensorMACs: 
							continue
							
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

						doSensors(pkt,UUID,Maj,Min,mac,rx,tx)
						time.sleep(1)

						break


				except	Exception, e:
					U.toLog(-1,u"in Line {} has error={}".format(sys.exc_traceback.tb_lineno, e),permanentLog=True,doPrint=True)
					U.toLog(-1, " BLEsensor "+"bad data", doPrint=True) 
					continue# skip if bad data

		sock.setsockopt( bluez.SOL_HCI, bluez.HCI_FILTER, old_filter )
		#print "reason",datetime.datetime.now(), reason
		U.echoLastAlive(G.program)
except	Exception, e:
	U.toLog(-1,u"in Line {} has error={}".format(sys.exc_traceback.tb_lineno, e),permanentLog=True)
	U.toLog(-1, "  exiting loop due to error\n")

print datetime.datetime.now().strftime("%Y%m%d-%H:%M:%S")+" BLEcsensor end of "+G.program	 
sys.exit(0)

