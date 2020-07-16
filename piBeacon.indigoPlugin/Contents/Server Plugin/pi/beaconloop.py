#!/usr/bin/env python
# -*- coding: utf-8 -*-
# test BLE Scanning software
# jcs 6/8/2014
#  adopted by Karl Wachs Nov27	2015
# version 1.1  Dec 24
# v 2	 feb 5 2016


from __future__ import division
import sys, os, subprocess, copy
import time,datetime
import struct
import bluetooth._bluetooth as bluez
import json

import math

sys.path.append(os.getcwd())
import	piBeaconUtils as U
import	piBeaconGlobals as G
G.program = "beaconloop"

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


def twos_complement(value, bits):
    if (value & (1 << (bits - 1))) != 0:
        value = value - (1 << bits)
    return value


def rshift(val, n):
    """
    Arithmetic right shift, preserves sign bit.
    https://stackoverflow.com/a/5833119 .
    """
    return (val % 0x100000000) >> n


def returnnumberpacket(pkt):
	myInteger = 0
	multiple = 256
	for c in pkt:
		myInteger +=  struct.unpack("B",c)[0] * multiple
		multiple = 1
	return myInteger 

def stringFromPacket(pkt):
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

#def hci_le_set_scan_parameters(sock, scan_type=constants.LE_SCAN_ACTIVE,  # 0x01
#								interval=0x10, window=0x10,
#								own_bdaddr_type=constants.LE_RANDOM_ADDRESS, # ==0x01
#								filter_type=constants.LE_FILTER_ALLOW_ALL):	 # ==0x00
#	 # TODO: replace B with appropriate size and remove 0 padding.
#	 cmd_pkt = struct.pack("<BBBBBBB", scan_type, 0x0, interval, 0x0, window,own_bdaddr_type, filter_type)
#	 bluez.hci_send_cmd(sock, constants.OGF_LE_CTL,constants.OCF_LE_SET_SCAN_PARAMETERS, cmd_pkt)
			
	

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
			cmd = "sudo hciconfig "+hci+" down &"
			U.logger.log(10,"startBlueTooth down: {}" .format(cmd))
			subprocess.call(cmd, shell=True) # disable bluetooth
			time.sleep(0.2)
			cmd = "sudo hciconfig "+hci+" up &"
			U.logger.log(10,"startBlueTooth  up: {}" .format(cmd))
			subprocess.call(cmd, shell=True) # enable bluetooth
		time.sleep(0.3)


		#### selct the proper hci bus: if just one take that one, if 2, use bus="uart", if no uart use hci0
		HCIs = U.whichHCI()
		if HCIs !={} and "hci" in  HCIs and HCIs["hci"] !={}:

			#U.logger.log(30,"myBLEmac HCIs{}".format( HCIs))
			useHCI,  myBLEmac, devId = U.selectHCI(HCIs["hci"], G.BeaconUseHCINo,"UART")
			if myBLEmac ==  -1:
				U.logger.log(20,"myBLEmac wrong: myBLEmac:{}, HCIs:{}".format( myBLEmac, HCIs))
				return 0,  0, -1, useHCI
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
		else:
			ret =["",""]

		if ret[1] != "":	U.logger.log(30,"BLE start returned:\n{}error:>>{}<<".format(ret[0],ret[1]))
		else:			 	
				U.logger.log(20,"BLE start returned:\n{}my BLE mac# is >>{}<<".format(ret[0], myBLEmac))
				if useHCI in HCIs["hci"]:
					if HCIs["hci"][useHCI]["upDown"] == "DOWN":
						if downCount > 1:
							U.logger.log(30,"reboot requested,{} is DOWN using hciconfig ".format(useHCI))
							writeFile("temp/rebootNeeded","bluetooth_startup {} is DOWN using hciconfig FORCE".format(useHCI))
							time.sleep(10)
						downCount +=1
						time.sleep(10)
						return 0,  "", -1, useHCI
				else:
					U.logger.log(30," {}  not in hciconfig list".format(useHCI))
					downCount +=1
					if downCount > 1:
						U.logger.log(30,"reboot requested,{} is DOWN using hciconfig ".format(useHCI))
						writeFile("temp/rebootNeeded","bluetooth_startup {} is DOWN using hciconfig FORCE".format(useHCI))
						time.sleep(10)
					downCount +=1
					time.sleep(10)
					return 0,  "", -1, useHCI
					
				
		if myBLEmac != "":
			writeFile("myBLEmac",myBLEmac)
		else:
			return 0, "", -1, useHCI

	except Exception, e: 
		U.logger.log(50,u"exit at restart BLE stack error  in Line {} has error={}".format(sys.exc_traceback.tb_lineno, e))
		time.sleep(10)
		writeFile("restartNeeded","bluetooth_startup.ERROR:{}".format(e))
		downHCI(useHCI)
		time.sleep(0.2)
		return 0, "", -5, useHCI


	try:
		sock = bluez.hci_open_dev(devId)
		U.logger.log(30, "ble thread started")
	except	Exception, e:
		U.logger.log(30,"error accessing bluetooth device...".format(e))
		if downCount > 2:
			writeFile("temp/rebootNeeded","bluetooth_startup.ERROR:{} FORCE ".format(e))
			downHCI(useHCI)
		downCount +=1
		return 0,  "", -1, useHCI
		
	try:
		hci_le_set_scan_parameters(sock)
		hci_enable_le_scan(sock)
	except	Exception, e:
		U.logger.log(50, u"in Line {} has error={}".format(sys.exc_traceback.tb_lineno, e))
		if unicode(e).find("Bad file descriptor") >-1:
			writeFile("temp/rebootNeeded","bluetooth_startup.ERROR:Bad_file_descriptor...SSD.damaged? FORCE ")
		if unicode(e).find("Network is down") >-1:
			if downCount > 2:
				writeFile("temp/rebootNeeded","bluetooth_startup.ERROR:Network_is_down...need_to_reboot FORCE ")
			downCount +=1
		downHCI(useHCI)
		return 0, "", -1, useHCI
	return sock, myBLEmac, 0, useHCI

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

#################################
def readbeacon_ExistingHistory():
	global	beacon_ExistingHistory, lastWriteHistory
	try:
		fg=open("{}beacon_ExistingHistory".format(G.homeDir),"r")
		beacon_ExistingHistory=json.loads(fg.read())
		fg.close()
		reset=False
		for beacon in beacon_ExistingHistory:
			if "txPower" not in beacon_ExistingHistory["beacon"]: reset=True
			if "uuid"	 not in beacon_ExistingHistory["beacon"]: reset=True
		if reset:
			beacon_ExistingHistory={}
	except: 
		beacon_ExistingHistory={}
	lastWriteHistory=time.time()
	return
	

#################################
def writebeacon_ExistingHistory():
	global	 beacon_ExistingHistory, lastWriteHistory
	if time.time() - lastWriteHistory < 100: return
	lastWriteHistory=time.time()
	try:
		fg=open("{}beacon_ExistingHistory".format(G.homeDir),"w")
		fg.write(json.dumps(beacon_ExistingHistory))
		fg.close()
	except	Exception, e:
		if unicode(e).find("Read-only file system:") >-1:
			subprocess.call("sudo reboot", shell=True)
#################################
def fixOldNames():

	if os.path.isfile(G.homeDir+"beaconsExistingHistory"):
		subprocess.call("sudo mv "+G.homeDir+"beaconsExistingHistory " + G.homeDir+"beacon_ExistingHistory", shell=True)


#################################
def handleHistory():
	global	beacon_ExistingHistory, deleteHistoryAfterSeconds

	delHist=[]		  
	for beaconMAC in beacon_ExistingHistory:
		if beacon_ExistingHistory[beaconMAC]["lCount"] < 0: beacon_ExistingHistory[beaconMAC]["lCount"] =10
		beacon_ExistingHistory[beaconMAC]["lCount"] -= 1
		beacon_ExistingHistory[beaconMAC]["reason"] = 0
		if time.time() - beacon_ExistingHistory[beaconMAC]["timeSt"] > deleteHistoryAfterSeconds : # delete history if older than 2 days with no message
			delHist.append(beaconMAC)
				
	# delete old data if older than 2 days		  
	for beaconMAC in delHist:
		del beacon_ExistingHistory[beaconMAC]

	# save history to file
	writebeacon_ExistingHistory() 



def readParams(init):
	global	 collectMsgs, sendAfterSeconds, loopMaxCallBLE,	 ignoreUUID,UUIDtoIphoneReverse,  beacon_ExistingHistory, deleteHistoryAfterSeconds,ignoreMAC,signalDelta,UUIDtoIphone,offsetUUID,fastDown,maxParseSec,batteryLevelPosition,doNotIgnore
	global acceptNewiBeacons, acceptNewTagiBeacons,onlyTheseMAC,enableiBeacons, sendFullUUID,BLEsensorMACs, minSignalCutoff, acceptJunkBeacons,knownBeaconTags
	global oldRaw,	lastRead
	if init:
		collectMsgs			= 10  # in parse loop collect how many messages max	  ========	all max are an "OR" : if one hits it stops
		sendAfterSeconds	= 60  # collect for xx seconds then send msg
		loopMaxCallBLE		= 900 # max loop count	in main pgm to collect msgs
		maxParseSec			= 2	  # stop aprse loop after xx seconds 
		portOfServer		= "8176"
		G.ipOfServer	  	= ""
		G.passwordOfServer	= ""
		G.userIdOfServer  	= ""
		G.myPiNumber	  	= "0"
		deleteHistoryAfterSeconds  =72000

	inp,inpRaw,lastRead2 = U.doRead(lastTimeStamp=lastRead)
	doParams = True
	if inp == "":				doParams = False
	if lastRead2 == lastRead:	doParams = False
	lastRead   = lastRead2
	if inpRaw == oldRaw:		doParams = False
	oldRaw	   = inpRaw

	if doParams:
		try:
			if "enableiBeacons"		in inp:	 enableiBeacons=	   (inp["enableiBeacons"])
			if enableiBeacons == "0":
				U.logger.log(50," termination ibeacon scanning due to parameter file")
				time.sleep(0.5)
				sys.exit(3)
			U.getGlobalParams(inp)

			if "rebootSeconds"			in inp:	 rebootSeconds=		  int(inp["rebootSeconds"])
			if "sendAfterSeconds"		in inp:	 sendAfterSeconds=	  int(inp["sendAfterSeconds"])
			if "acceptNewiBeacons"		in inp:	 acceptNewiBeacons=	  int(inp["acceptNewiBeacons"])
			if "acceptNewTagiBeacons"	in inp:	 acceptNewTagiBeacons=	 (inp["acceptNewTagiBeacons"])
			if "sendFullUUID"			in inp:	 sendFullUUID=			 (inp["sendFullUUID"]=="1" )
			if "acceptJunkBeacons"		in inp:	 acceptJunkBeacons=		 (inp["acceptJunkBeacons"]=="1" )


			if "deleteHistoryAfterSeconds"	in inp:
									  deleteHistoryAfterSeconds=  int(inp["deleteHistoryAfterSeconds"])
			BLEsensorMACs = {}

			if "sensors"			 in inp: 
				sensors =			 (inp["sensors"])
				for sensor in ["BLEsensor","BLERuuviTag"]:
					if sensor in sensors:
						for devId in sensors[sensor]:
							sensD	= sensors[sensor][devId]
							mac		= sensD["mac"]
							BLEsensorMACs[mac]={}
							BLEsensorMACs[mac]["type"]				   			= sensD["type"]
							BLEsensorMACs[mac]["devId"]				   			= devId
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
							try:	BLEsensorMACs[mac]["updateIndigoDeltaAcceleration"]	= float(sensD["updateIndigoDeltaAcceleration"])/100.
							except: BLEsensorMACs[mac]["updateIndigoDeltaAcceleration"] 	= 0.3
							try:	BLEsensorMACs[mac]["updateIndigoDeltaTurn"] = float(sensD["updateIndigoDeltaTurn"])/100.
							except: BLEsensorMACs[mac]["updateIndigoDeltaTurn"] = 0.3
							try:	BLEsensorMACs[mac]["updateIndigoDeltaTemp"] = float(sensD["updateIndigoDeltaTemp"])
							except: BLEsensorMACs[mac]["updateIndigoDeltaTemp"] = 1 # =1C 
							try:	BLEsensorMACs[mac]["minSendDelta"] 			= float(sensD["minSendDelta"])
							except: BLEsensorMACs[mac]["minSendDelta"] 			= 4 #  seconds betwen updates

							BLEsensorMACs[mac]["accelerationTotal"]				= 0
							BLEsensorMACs[mac]["accelerationX"]				 	= 0
							BLEsensorMACs[mac]["accelerationY"]				 	= 0
							BLEsensorMACs[mac]["accelerationZ"]				 	= 0
							BLEsensorMACs[mac]["temp"]				 			= -100
							BLEsensorMACs[mac]["lastUpdate"]				 	= 0

		except	Exception, e:
			U.logger.log(30,u"in Line {} has error={}".format(sys.exc_traceback.tb_lineno, e))



	try:
		f = open("{}temp/beacon_parameters".format(G.homeDir),"r")
		InParams = json.loads(f.read().strip("\n"))
		f.close()
	except:
		InParams = {}

	try:
		f = open("{}temp/knownBeaconTags".format(G.homeDir),"r")
		knownBeaconTags = json.loads(f.read().strip("\n"))
		f.close()
	except:		
		knownBeaconTags = {}
	try:		onlyTheseMAC=InParams["onlyTheseMAC"]
	except:		onlyTheseMAC={}

	try:		ignoreUUID=InParams["ignoreUUID"]
	except:		ignoreUUID=[]

	try:		ignoreMAC=InParams["ignoreMAC"]
	except:		ignoreMAC=[]

	try:		doNotIgnore=InParams["doNotIgnore"]
	except:		doNotIgnore=[]

	try:		offsetUUID=InParams["offsetUUID"]
	except:		offsetUUID={}
		
	try:		fastDown=InParams["fastDown"]
	except:		fastDown={}

	try:		minSignalCutoff=InParams["minSignalCutoff"]
	except:		minSignalCutoff={}

	try:		batteryLevelPosition=InParams["batteryLevelPosition"]
	except:		batteryLevelPosition={}

	try:		signalDelta=InParams["signalDelta"]
	except:		signalDelta={}

	try:		UUIDtoIphone=InParams["UUIDtoIphone"]
	except:		UUIDtoIphone={}

	try:
		UUIDtoIphoneReverse={}
		for mac in UUIDtoIphone:
			ok, UUID2 = setUUIDcompare(UUIDtoIphone[mac][0],UUIDtoIphone[mac][1],UUIDtoIphone[mac][2])
			if ok:
				UUIDtoIphoneReverse[UUID2] = mac
	except:	   
		UUIDtoIphoneReverse={}


		
	U.logger.log(0,"fastDown:            {}".format(fastDown))
	U.logger.log(0,"signalDelta:         {}".format(signalDelta))
	U.logger.log(0,"ignoreUUID:          {}".format(ignoreUUID))
	U.logger.log(0,"ignoreMAC:           {}".format(ignoreMAC))
	U.logger.log(0,"UUIDtoIphone:        {}".format(UUIDtoIphone))
	U.logger.log(0,"UUIDtoIphoneReverse: {}".format(UUIDtoIphoneReverse))
	return


		
	
#################################
def composeMSG(beaconsNew,timeAtLoopStart,reasonMax):
	global	 collectMsgs, sendAfterSeconds, loopMaxCallBLE,	 ignoreUUID,  beacon_ExistingHistory, deleteHistoryAfterSeconds
	global myBLEmac, sendFullUUID,  mapReasonToText, downCount, beaconsOnline
	try:
		if myBLEmac == "00:00:00:00:00:00":
			time.sleep(2)
			U.restartMyself(param="", reason="bad BLE  =00..00")

		data=[]
		for beaconMAC in beaconsNew:
			if beaconMAC not in beacon_ExistingHistory: continue
			try:
				testIphone, mac =checkIfIphone(beaconsNew[beaconMAC]["uuid"],beaconMAC)
				if sendFullUUID or beacon_ExistingHistory[beaconMAC]["lCount"] ==0 or beacon_ExistingHistory[beaconMAC]["lCount"] ==5 or beacon_ExistingHistory[beaconMAC]["reason"] ==2 or testIphone:
					uuid= beaconsNew[beaconMAC]["uuid"]
					if sendFullUUID:
						beacon_ExistingHistory[beaconMAC]["lCount"]=0
					else:
						beacon_ExistingHistory[beaconMAC]["lCount"]=10
				else:
					uuid= "x-x-x"
				if beaconsNew[beaconMAC]["count"] !=0 :
					avePower	=float("%5.0f"%(beaconsNew[beaconMAC]["txPower"]	/beaconsNew[beaconMAC]["count"]))
					aveSignal	=float("%5.1f"%(beaconsNew[beaconMAC]["rssi"]		/beaconsNew[beaconMAC]["count"]))
					if avePower > -200:
						beaconsOnline[beaconMAC] = int(time.time())
					r  = min(6,max(0,beacon_ExistingHistory[beaconMAC]["reason"]))
					rr = mapReasonToText[r]
					newData = {"mac":beaconMAC,"reason":rr,"uuid":uuid,"rssi":aveSignal,"txPower":avePower,"count":beaconsNew[beaconMAC]["count"],"batteryLevel":beaconsNew[beaconMAC]["bLevel"],"pktInfo":beaconsNew[beaconMAC]["pktInfo"]}
					downCount = 0
					#print r, beacon_ExistingHistory[beaconMAC]["reason"], newData
					data.append(newData)
					beacon_ExistingHistory[beaconMAC]["rssi"]  = beaconsNew[beaconMAC]["rssi"]/max(beaconsNew[beaconMAC]["count"],1.) # average last rssi
					beacon_ExistingHistory[beaconMAC]["count"] = beaconsNew[beaconMAC]["count"] 
					beacon_ExistingHistory[beaconMAC]["timeSt"] = time.time()
			except	Exception, e:
				U.logger.log(30,u"in Line {} has error={}".format(sys.exc_traceback.tb_lineno, e))
				U.logger.log(30, " error composing msg \n{}".format(beaconsNew[beaconMAC]))

		secsCollected=int(time.time()-timeAtLoopStart)
##		  if unicode(data).find("0C:F3:EE:00:66:15") > -1:	 print data

		if len(data) >10: downCount = 0
		data ={"msgs":data,"pi":str(G.myPiNumber),"piMAC":myBLEmac,"secsCol":secsCollected,"reason":mapReasonToText[reasonMax]}
		U.sendURL(data)

		# save active iBeacons for getbeaconparameters() process
		copyBE = copy.copy(beaconsOnline)
		for be in copyBE:
			if time.time() - copyBE[be] > 90:
				del beaconsOnline[be]
		U.writeJson("{}temp/beaconsOnline".format(G.homeDir), beaconsOnline, sort_keys=False, indent=0)

	except	Exception, e:
		U.logger.log(30,u"in Line {} has error={}".format(sys.exc_traceback.tb_lineno, e))





#################################
def checkIfNewOrDeltaSignalOrWasMissing(reason,beaconMAC,beaconMSG, beaconsNew):
	global collectMsgs, sendAfterSeconds, loopMaxCallBLE, ignoreUUID,	 beacon_ExistingHistory, deleteHistoryAfterSeconds,signalDelta,fastDown, minSignalCutoff
	global onlyTheseMAC
 
	t=time.time()
	rssi = float(beaconMSG[2])
	try:
		if beaconMAC not in beacon_ExistingHistory: # is it new?
			if beaconMAC in minSignalCutoff:
				if	rssi < minSignalCutoff[beaconMAC]:
					#print "rejecting: ", beaconMAC, minSignalCutoff[beaconMAC] ,  float(beaconMSG[2])
					return reason
				else:
					#print "accepting: ", beaconMAC, minSignalCutoff[beaconMAC] ,  float(beaconMSG[2])
					pass
			if beaconMAC not in onlyTheseMAC:
				reason = 2
			else:
				reason = 5

			beacon_ExistingHistory[beaconMAC]={"uuid":beaconMSG[1],"lCount":1,"txPower":float(beaconMSG[3]),"rssi":rssi,"reason":reason,"timeSt":t,"count":beaconsNew[beaconMAC]["dCount"]}
			
		# no up if signal weak  
		elif beaconMAC in minSignalCutoff and rssi < minSignalCutoff[beaconMAC]:# 
			return reason

		elif beacon_ExistingHistory[beaconMAC]["rssi"] == -999: # in fast down mode, was down for some time
			reason = 4 
			#print " rssi=-999 "+ beaconMAC +"; dT: "+unicode(t-beacon_ExistingHistory[beaconMAC]["timeSt"])+"sec; rssi= "+beaconMSG[2] +"; ex history: "+unicode(beacon_ExistingHistory[beaconMAC])+"; fd: "+ unicode(fastDown)+"; t:"+unicode(t) 
			beacon_ExistingHistory[beaconMAC]={"uuid":beaconMSG[1],"lCount":1,"txPower":float(beaconMSG[3]),"rssi":rssi,"reason":reason,"timeSt":t,"count":beaconsNew[beaconMAC]["dCount"]}
	 

 
		elif (t - beacon_ExistingHistory[beaconMAC]["timeSt"])	> 1.3*sendAfterSeconds: # not new but have not heard for > 1+1/3 periods
			reason = 5
			beacon_ExistingHistory[beaconMAC]["reason"] = reason
			#print	"curl: first msg after	collect time "+ beaconMAC +" "+unicode(beacon_ExistingHistory[beaconMAC])

		elif beaconMAC in signalDelta: 
			if beacon_ExistingHistory[beaconMAC]["rssi"] != -999. and rssi != 0:
				if abs(beacon_ExistingHistory[beaconMAC]["rssi"]-rssi) >  signalDelta[beaconMAC] :	# delta signal > xxdBm (set param)
					if beaconsNew[beaconMAC]["dCount"] > 0:
						#print beaconMAC, "signalDelta",beacon_ExistingHistory[beaconMAC]["rssi"], float(beaconMSG[2]), signalDelta[beaconMAC] 
						reason = 6
						beacon_ExistingHistory[beaconMAC]["reason"] = reason
						beaconsNew[beaconMAC]["count"] = 2
						beaconsNew[beaconMAC]["rssi"]  = beaconsNew[beaconMAC]["rssiLast"] + rssi
						#U.logger.log(30, "signalDelta A) mac:{} rssi: {} , dc:{};; hist c:{} - rssiAv{}".format(beaconMAC, beaconMSG[2], beaconsNew[beaconMAC]["dCount"], beacon_ExistingHistory[beaconMAC]["count"], beacon_ExistingHistory[beaconMAC]["rssi"]) )
					else:
						beaconsNew[beaconMAC]["dCount"]    +=1 
						beaconsNew[beaconMAC]["rssiLast"]  = rssi
						#U.logger.log(30, "signalDelta B) mac:{} rssi: {} , dc:{};; hist c:{} - rssiAv{}".format(beaconMAC, beaconMSG[2], beaconsNew[beaconMAC]["dCount"], beacon_ExistingHistory[beaconMAC]["count"], beacon_ExistingHistory[beaconMAC]["rssi"]) )
				else:
					#U.logger.log(30, "signalDelta C) mac:{} rssi: {} , dc:{};; hist c:{} - rssiAv{}".format(beaconMAC, beaconMSG[2], beaconsNew[beaconMAC]["dCount"], beacon_ExistingHistory[beaconMAC]["count"], beacon_ExistingHistory[beaconMAC]["rssi"]) )
					beaconsNew[beaconMAC]["dCount"]    = 0
					beaconsNew[beaconMAC]["rssiLast"]  = -999



		beacon_ExistingHistory[beaconMAC]["reason"] = max(1,beacon_ExistingHistory[beaconMAC]["reason"])
		beacon_ExistingHistory[beaconMAC]["timeSt"] = t
	except	Exception, e:
		U.logger.log(30,u"in Line {} has error={}".format(sys.exc_traceback.tb_lineno, e))
	return reason


#################################
def checkIfIphone(uuid,beaconMAC):
	global UUIDtoIphone,UUIDtoIphoneReverse
	try: 
		## ----------  check if this is an iphone
		#print mac, uuid
		macFound = findUUIDcompare(uuid,UUIDtoIphone,UUIDtoIphoneReverse) 
		if macFound == "": return False, beaconMAC
		else:			   
			return True,  macFound

	except	Exception, e:
		U.logger.log(30,u"in Line {} has error={}".format(sys.exc_traceback.tb_lineno, e))
	return False, beaconMAC

#################################
def findUUIDcompare(uuid,UUIDtoIphone,UUIDtoIphoneReverse):
	try:
		if len(UUIDtoIphone) == 0:								 return ""
		if	 uuid in UUIDtoIphoneReverse:						 return UUIDtoIphoneReverse[uuid]

		UUid = uuid.split("-")
		if len(UUid)	!=3:									return ""
		elif UUid[0]+"--"				 in UUIDtoIphoneReverse: return UUIDtoIphoneReverse[UUid[0]+"--"]
		elif UUid[0]+"-" +UUid[1]+"-"	 in UUIDtoIphoneReverse: return UUIDtoIphoneReverse[UUid[0]+"-" +UUid[1]+"-"]
		elif UUid[0]+"--"+UUid[2]		 in UUIDtoIphoneReverse: return UUIDtoIphoneReverse[UUid[0]+"--"+UUid[2]]
		else:													 return ""

		return ""
	except	Exception, e:
		U.logger.log(30,u"in Line {} has error={}".format(sys.exc_traceback.tb_lineno, e))
	return ""
		
#################################
def setUUIDcompare(uuid, constantUUIDmajMIN,lenOfUUID):
	try:
		UUIDx = uuid.split("-")
		UUid  = uuid
		if len(UUIDx)	 !=3:			return False, uuid
		if len(UUIDx[0]) != lenOfUUID:	return False, uuid
		if	 constantUUIDmajMIN	 == "uuid--min":	UUid = "{}--{}".format(UUIDx[0], UUIDx[2])
		elif constantUUIDmajMIN	 == "uuid-maj-":	UUid = "{}-{}-".format(UUIDx[0], UUIDx[2])
		elif constantUUIDmajMIN	 == "uuid--":		UUid = UUIDx[0]
		return True, UUid
	except	Exception, e:
		U.logger.log(30,u"in Line {} has error={}".format(sys.exc_traceback.tb_lineno, e))
	return False, uuid


	
#################################
def checkIfFastDown(beaconsNew,reason):
	global fastDown,beacon_ExistingHistory
	try:
	## ----------  check if this is a fast down device
		tt= time.time()
		for beacon in fastDown:
			##print " test " 
			if beacon not in beacon_ExistingHistory:		   continue # not in history never had an UP signal is already gone

			if beacon in beaconsNew:
				if tt- beaconsNew[beacon]["timeSt"] < fastDown[beacon]["seconds"]: 
					#print "test if FD" +beacon+"  dt:"+str(t- beacon_ExistingHistory[beacon]["timeSt"]) +" fd:"+ str( fastDown[beacon])+" ;rssi: "+ str(beaconsNew[beacon]["rssi"])
					beacon_ExistingHistory[beacon]["rssi"]		=beaconsNew[beacon]["rssi"]
					beacon_ExistingHistory[beacon]["timeSt"]	=tt
					beacon_ExistingHistory[beacon]["txPower"]	=beaconsNew[beacon]["txPower"]
					beacon_ExistingHistory[beacon]["uuid"]		=beaconsNew[beacon]["uuid"]
					beacon_ExistingHistory[beacon]["count"]		=beaconsNew[beacon]["count"]
					beacon_ExistingHistory[beacon]["pkLen"]		=beaconsNew[beacon]["pkLen"]
					continue 

				if tt- beacon_ExistingHistory[beacon]["timeSt"] <	fastDown[beacon]["seconds"]: continue		#  shorter trigger
			elif   tt- beacon_ExistingHistory[beacon]["timeSt"] <	fastDown[beacon]["seconds"]: continue		#  have not received anything this period, give it a bit more time
			if beacon_ExistingHistory[beacon]["rssi"] == -999: continue # already fast down send

				 
			reason = 3
			beacon_ExistingHistory[beacon]["timeSt"]= tt
			beacon_ExistingHistory[beacon]["rssi"]= -999
			beacon_ExistingHistory[beacon]["reason"]= reason
			if "pkLen" not in beacon_ExistingHistory: 
				beacon_ExistingHistory[beacon]["pkLen"]=""
			beaconsNew[beacon]={
				"uuid":beacon_ExistingHistory[beacon]["uuid"],
				"txPower":beacon_ExistingHistory[beacon]["txPower"],
				"rssi":-999,
				"timeSt":tt,
				"bLevel":"",
				"pkLen":beacon_ExistingHistory[beacon]["pkLen"],
				"count":1}# [uid-major-minor,txPower,signal strength, # of measuremnts
	except	Exception, e:
		U.logger.log(30,u"in Line {} has error={}".format(sys.exc_traceback.tb_lineno, e))

				
	return reason, beaconsNew

#################################, check if signal strength is acceptable for fastdown 
def checkIfFastDownMinSignal(beaconMAC,rssi,fastDown):
	try:
		if	beaconMAC in fastDown:
			if "fastDownMinSignal" in fastDown[beaconMAC]:
				if fastDown[beaconMAC]["fastDownMinSignal"] > rssi: return True
	except	Exception, e:
		U.logger.log(30,u"in Line {} has error={}".format(sys.exc_traceback.tb_lineno, e))
	return False
		
#################################
def checkIfIgnore(uuid,beaconMAC):
	global beacon_ExistingHistory, ignoreUUID,ignoreMAC,doNotIgnore,alreadyIgnored, onlyTheseMAC
	 
	## ----------  check if we should ignore this one
	## is this on teh MUST NOT IGNORE LIST?		

	if beaconMAC in doNotIgnore:  return False
	if beaconMAC in onlyTheseMAC: return False
	
	for ignoreThisUuid in ignoreUUID: 
		if	len(ignoreThisUuid) > 2:
			if uuid[:len(ignoreThisUuid)] == ignoreThisUuid : 
				try:
					del beacon_ExistingHistory[beaconMAC] # delete history if it exists
				except:
					pass
				if beaconMAC not in alreadyIgnored:
					toReject("UUID;"+uuid+";"+beaconMAC ) 
					alreadyIgnored[beaconMAC]=1
				return True
			
	if beaconMAC in ignoreMAC:	
			try:
				del beacon_ExistingHistory[beaconMAC] # delete history if it exists
			except:
				pass
			if beaconMAC not in alreadyIgnored:
				toReject("UUID;"+uuid+";"+beaconMAC ) 
				alreadyIgnored[beaconMAC]=1
			return True
	return False  
		  


#################################
def checkIfBLErestart():
	if os.path.isfile(G.homeDir + "temp/BLErestart") :
		os.remove(G.homeDir + "temp/BLErestart")
		U.logger.log(30," restart of BLE stack requested") 
		return True
	return False



#################################
#################################
######## BLE SENSORS ############
#################################
#################################
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
		if ruuviTagFound or ruuviSensorActive: 
			return  doRuuviTag(pkt, mac, rx, tx, nBytesThisMSG, hexData, ruuviTagPos, ruuviSensorActive, UUID, Maj, Min)

	except	Exception, e:
		U.logger.log(30,u"in Line {} has error={}".format(sys.exc_traceback.tb_lineno, e))
	return tx, bl, UUID, Maj, Min, False

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
		return tx, "", "myBlueT", mac, "sensor",True
	except	Exception, e:
		U.logger.log(30,u"in Line {} has error={}".format(sys.exc_traceback.tb_lineno, e))
	return tx, "", UUID, Maj, Min, False
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
			return tx, "", UUID, Maj, Min

		UUID 						= "ruuviTag"
		Maj  						= mac
		Min  						= "sensor"
		sensor 						= "BLERuuviTag"
		# make data into right format (bytes)
		byte_data 					= bytearray.fromhex(hexData[ruuviTagPos + 6:])
		# umpack the first set of data
		batteryVoltage, txPower 	= doRuuviTag_powerinfo(byte_data)
		batteryLevel 				= int(max(0,100* (batteryVoltage - 2900.)/(3200.-2900.)))

		if not ruuviSensorActive: # we have found the ruuvitag, just the sensor is active on this RPI, but the iBeacon is
			# overwrite UUID etc for this ibeacon if used later
			return str(txPower), str(batteryLevel), UUID, Maj, Min, False

		# sensor is active, get all data and send if conditions ok

		# unpack  rest of sensor data 
		accelerationTotal, accelerationX, accelerationY, accelerationZ 	= doRuuviTag_magValues(byte_data)
		temp 					= doRuuviTag_temperature(byte_data)

		# make deltas compared to last send 
		deltaaccelerationTotal 	= abs(BLEsensorMACs[mac]["accelerationTotal"] 	- accelerationTotal) / max(.001,abs(BLEsensorMACs[mac]["accelerationTotal"] + accelerationTotal))
		deltaaccelerationX 		= abs(BLEsensorMACs[mac]["accelerationX"] 		- accelerationX) 	 / max(.001,abs(BLEsensorMACs[mac]["accelerationX"] 	+ accelerationX))
		deltaaccelerationY 		= abs(BLEsensorMACs[mac]["accelerationY"] 		- accelerationY)	 / max(.001,abs(BLEsensorMACs[mac]["accelerationY"] 	+ accelerationY))
		deltaaccelerationZ 		= abs(BLEsensorMACs[mac]["accelerationZ"] 		- accelerationZ)	 / max(.001,abs(BLEsensorMACs[mac]["accelerationZ"] 	+ accelerationZ))
		deltatemp 				= abs(BLEsensorMACs[mac]["temp"] - temp)  
		deltaTurn 				= int( float(deltaaccelerationX + deltaaccelerationY + deltaaccelerationY) * (100./3.) )
		deltaTime 				= time.time() - BLEsensorMACs[mac]["lastUpdate"]

		# check if we should send data to indigo
		if (deltaTime 					> BLEsensorMACs[mac]["minSendDelta"] and				# dont send too often
				( 
				deltaTime 				> BLEsensorMACs[mac]["updateIndigoTiming"] or 			# send min every xx secs
				deltatemp 				> BLEsensorMACs[mac]["updateIndigoDeltaTemp"] or		# temp change triggerssend
				deltaaccelerationTotal	> BLEsensorMACs[mac]["updateIndigoDeltaAcceleration"] or# acceleration change triggers send
				deltaTurn				> BLEsensorMACs[mac]["updateIndigoDeltaTurn"]			# acceleration-turn change triggers send
				)
			): 
			dd={   # the data dict to be send 
				'data_format': 5,
				'hum': 					int(doRuuviTag_humidity(byte_data)	 + BLEsensorMACs[mac]["offsetHum"]),
				'temp': 				round(temp							 + BLEsensorMACs[mac]["offsetTemp"],2),
				'press': 				round(doRuuviTag_pressure(byte_data) + BLEsensorMACs[mac]["offsetPress"],1),
				'accelerationTotal': 	int(accelerationTotal),
				'accelerationX': 		int(accelerationX),
				'accelerationY': 		int(accelerationY),
				'accelerationZ': 		int(accelerationZ),
				'accelerationTurn':		int(deltaTurn),
				'batteryLevel': 		int(batteryLevel),
				'batteryVoltage': 		int(batteryVoltage),
				'movementCount': 		int(doRuuviTag_movementcounter(byte_data)),
				'measurementCount': 	int(doRuuviTag_measurementsequencenumber(byte_data)),
				'txPower': 				int(txPower),
				"rssi":					int(rx),
			}

			U.logger.log(10, "mac:{}    RX:{}; TX:{}; nBytes:{}, deltas:{},{},{},{}, data:{}".format(mac, rx, tx, nBytesThisMSG, deltaTime > BLEsensorMACs[mac]["updateIndigoTiming"],	deltatemp > BLEsensorMACs[mac]["updateIndigoDeltaTemp"], deltaaccelerationTotal > BLEsensorMACs[mac]["updateIndigoDeltaAcceleration"], deltaTurn > BLEsensorMACs[mac]["updateIndigoDeltaTurn"], dd ) )

			## compose complete message
			U.sendURL({"sensors":{sensor:{BLEsensorMACs[mac]["devId"]:dd}}})

			# remember last values
			BLEsensorMACs[mac]["lastUpdate"] 			= time.time()
			BLEsensorMACs[mac]["accelerationTotal"] 	= accelerationTotal
			BLEsensorMACs[mac]["accelerationX"] 		= accelerationX
			BLEsensorMACs[mac]["accelerationY"] 		= accelerationY
			BLEsensorMACs[mac]["accelerationZ"] 		= accelerationZ
			BLEsensorMACs[mac]["updateIndigoDeltaTurn"] = deltaTurn
			BLEsensorMACs[mac]["temp"] 					= temp

		# overwrite UUID etc for this ibeacon if used later
		return str(txPower), str(batteryLevel), UUID, Maj, Min, True

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



#################################
def checkIFtrackMacIsRequested():
	global logCountTrackMac, trackMac, nLogMgsTrackMac, startTimeTrackMac, trackMacText
	try:
		if not os.path.isfile(G.homeDir+"temp/beaconloop.trackmac"): return False
		f = open(G.homeDir+"temp/beaconloop.trackmac","r")
		trackMac = f.read().strip("\n")
		f.close()
		trackMacText = ""
		writeTrackMac("","\nTRACKMAC started on pi#:"+str(G.myPiNumber)+", for MAC# "+trackMac+"\n")
		startTimeTrackMac = time.time()
		subprocess.call("rm {}temp/beaconloop.trackmac".format(G.homeDir), shell=True)
		subprocess.call("rm {}temp/trackmac.log".format(G.homeDir), shell=True)
		logCountTrackMac = nLogMgsTrackMac
	except	Exception, e:
		U.logger.log(30,u"in Line {} has error={}".format(sys.exc_traceback.tb_lineno, e))

#################################
def writeTrackMac(textOut0, textOut2):
	global logCountTrackMac, trackMac, nLogMgsTrackMac, trackMacText
	try:
		f = open(G.homeDir+"temp/trackmac.log","a")
		if textOut0 == "":
			f.write(textOut2+"\n")
		else:
			f.write(textOut0+trackMac+", "+textOut2+"\n")
		f.close()
		print textOut0,trackMac,textOut2
		trackMacText += textOut0+textOut2+";;"
	except	Exception, e:
		U.logger.log(30,u"in Line {} has error={}".format(sys.exc_traceback.tb_lineno, e))


#################################
def BLEAnalysis(hci):
	global onlyTheseMAC, knownBeaconTags
	try:
		if not os.path.isfile(G.homeDir+"temp/beaconloop.BLEAnalysis"): return False

		dataCollectionTime = 22 # secs 


		f = open(G.homeDir+"temp/beaconloop.BLEAnalysis","r")
		rssiCutoff = int(f.read().strip("\n"))
		f.close()

		subprocess.call("rm {}temp/beaconloop.BLEAnalysis".format(G.homeDir), shell=True)


		## init, set dict and delete old files
		MACs={}
		subprocess.Popen("sudo chmod +777 "+G.homeDir+"temp/*",shell=True,stdout=subprocess.PIPE,stderr=subprocess.PIPE)
		subprocess.Popen("sudo rm "+G.homeDir+"temp/lescan.data",shell=True,stdout=subprocess.PIPE,stderr=subprocess.PIPE)
		subprocess.Popen("sudo rm "+G.homeDir+"temp/hcidump.data",shell=True,stdout=subprocess.PIPE,stderr=subprocess.PIPE)
		subprocess.Popen("sudo rm "+G.homeDir+"temp/hcidump.temp",shell=True,stdout=subprocess.PIPE,stderr=subprocess.PIPE)
		subprocess.Popen("sudo rm "+G.homeDir+"temp/bluetoothctl.data",shell=True,stdout=subprocess.PIPE,stderr=subprocess.PIPE)
		subprocess.Popen("sudo rm "+G.homeDir+"temp/BLEAnalysis-new.json",shell=True,stdout=subprocess.PIPE,stderr=subprocess.PIPE)
		subprocess.Popen("sudo rm "+G.homeDir+"temp/BLEAnalysis-existing.json",shell=True,stdout=subprocess.PIPE,stderr=subprocess.PIPE)
		subprocess.Popen("sudo rm "+G.homeDir+"temp/BLEAnalysis-rejected.json",shell=True,stdout=subprocess.PIPE,stderr=subprocess.PIPE)

		## now listen to BLE
		starttime = time.time()
		U.logger.log(20, u"starting  BLEAnalysis, rssi cutoff= {}[dBm]".format(rssiCutoff))
		U.logger.log(20, u"sudo hciconfig {} reset".format(hci))
		subprocess.Popen("sudo hciconfig "+hci+" reset",shell=True,stdout=subprocess.PIPE,stderr=subprocess.PIPE).communicate()
		U.logger.log(20, "sudo timeout -s SIGINT "+str(dataCollectionTime)+"s hcitool -i "+hci+" lescan")
		subprocess.Popen("sudo timeout -s SIGINT "+str(dataCollectionTime)+"s hcitool -i "+hci+" lescan > "+G.homeDir+"temp/lescan.data &",shell=True,stdout=subprocess.PIPE,stderr=subprocess.PIPE)
		time.sleep(0.3)
		U.logger.log(20, "sudo timeout -s SIGINT "+str(dataCollectionTime)+"s hcidump -i "+hci+" --raw  | sed -e :a -e '$!N;s/\\n  //;ta' -e 'P;D'")
		subprocess.Popen("sudo timeout -s SIGINT "+str(dataCollectionTime)+"s hcidump -i "+hci+" --raw  | sed -e :a -e '$!N;s/\\n  //;ta' -e 'P;D' > "+G.homeDir+"temp/hcidump.data &",shell=True,stdout=subprocess.PIPE,stderr=subprocess.PIPE)
		time.sleep(dataCollectionTime)
		U.logger.log(20, "sudo timeout -s SIGINT "+str(dataCollectionTime)+"s bluetoothctl scan on")
		subprocess.Popen("sudo timeout -s SIGINT "+str(dataCollectionTime)+"s bluetoothctl scan on > "+G.homeDir+"temp/bluetoothctl.data &",shell=True,stdout=subprocess.PIPE,stderr=subprocess.PIPE)
		time.sleep(dataCollectionTime+.1)
		U.logger.log(20, "prep done; after@: {:.1f} secs".format(time.time()-starttime))
		subprocess.Popen("sudo chmod +777 "+G.homeDir+"temp/*",shell=True,stdout=subprocess.PIPE,stderr=subprocess.PIPE)



		###### analyse output  #######
		if True: # bluetoothctl
			f = open(G.homeDir+"temp/bluetoothctl.data","r")
			xxx = f.read()
			f.close()
			DeviceFound = False
			out = []
			linesIn = 0
			linesDevices = 0
			linesAccepted = 0
			for line in xxx.split("\n"):
				linesIn +=1
				if " Device "			not in line: continue
				if " Manufacturer"		    in line: continue
				if " TxPower: " 			in line: continue
				if " UUIDs: "	 			in line: continue
				if " ServiceData " 			in line: continue
				linesAccepted +=1

				data = line.split(" Device ")[1]
				items = data.split(" ")
				mac = items[0]
				#if mac == "DD:33:0A:11:15:E3": print "bluetoothctl found DD:33:0A:11:15:E3", line

				if " RSSI: " in data:
					items = data.split(" RSSI: ")
					#print mac, items
					if mac not in MACs: 
						linesDevices +=1
						MACs[mac] = {"max_rssi":-99, "max_TX": -99,"MSG_in_10Secs": 0,"mfg_info":"","n_of_MSG_Types":0, "beaconType":[],"beaconType-msg#":[],"raw_data":[],"pos_of_MAC_in_UUID":[],"pos_of_reverse_MAC_in_UUID":[], "possible_knownTag_options":[]}
					try:	MACs[mac]["max_rssi"] = max(MACs[mac]["max_rssi"],int(items[1]))
					except: pass
				else:
					items = data.split(" ")
					#print mac, items
					if mac not in MACs: 
						linesDevices +=1
						MACs[mac] = {"max_rssi":-99, "max_TX": -99,"MSG_in_10Secs": 0,"mfg_info":"","n_of_MSG_Types":0, "beaconType":[],"beaconType-msg#":[],"raw_data":[],"pos_of_MAC_in_UUID":[],"pos_of_reverse_MAC_in_UUID":[], "possible_knownTag_options":[]}
					try:	MACs[mac]["mfg_info"] = items[-1]
					except: pass
			U.logger.log(20, "finished  bluetoothctl:lines -in: {:4d}, accepted: {:4d},  n-devices: {:4d}".format(linesIn,linesAccepted,linesDevices ))
		if True: # hcidump
		##                                                                                    
		##  tag-pos: =MACstart  0  2  4  6  8  1  1  1  1  1  2  2  2  2  2  3  3  3  3  3  4  4  4  4  4  5  ... 
		##                      0  2  4  6  8  0  2  4  6  8  0  2  4  6  8  0  2  4  6  8  0  2  4  6  8  0 
		##                      MA C# ## ## ## ##                                                                                                            RX TX
		## 04 3E 2A 02 01 00 00 6B 5F 24 32 DA A4 1E 02 01 06 1A FF 4C 00 02 15 53 70 6F 74 79 50 61 6C 54 65 72 72 61 63 6F 6D 1A DD D6 24 CA AF 
		## 01 23 45 67 89 11 23 45 67 89 21 23 45 67 89 31 23 45 67 89 41 23 45 67 89 51 23 45 67 89 61 23 45 67 89 7 # seq # 
		## 01234567891123456789212345678931234567894123456789512345678961234567897 # seq # 
		## 04 3E 27 02 01 00 00 1F E3 92 30 0D DC 1B 02 01 06 03 03 AA FE 13 16 AA FE 10 D4 03 67 6F 6F 2E 67 6C 2F 50 48 4E 53 64", 
		## 04 3E 26 02 01 04 00 1F E3 92 30 0D DC 1A 0E 16 F0 FF 1B 02 09 02 DC 0D 30 92 E3 1F 64 0A 09 46 53 43 5F 42 50 31 30", 
		##                                                       FF 4C                                                                    
		## ID packet Type                                        APPLE                                                                    
		## 
			f = open(G.homeDir+"temp/hcidump.data","r")
			xxx = f.read()
			f.close()
			#print xxx [0:100]
			linesIn = 0
			linesDevices = 0
			linesAccepted = 0
			for line in xxx.split("\n"):
				linesIn +=1
				if len(line) < 60: 		continue
				if line.find(">") ==-1: continue
				linesAccepted +=1
				line = line[2:].strip()
				items = line.split()
				mac = (items[7:13])[::-1]
				mac = ":".join(mac)
				#if mac =="DD:33:0A:11:15:E3": print "hcidump found DD:33:0A:11:15:E3", line
				if mac not in MACs: 
					MACs[mac] = {"max_rssi":-99, "max_TX": -99,"MSG_in_10Secs": 0,"mfg_info":"","n_of_MSG_Types":0,"beaconType":[],"beaconType-msg#":[],"raw_data":[],"pos_of_MAC_in_UUID":[],"pos_of_reverse_MAC_in_UUID":[], "possible_knownTag_options":[]}
				#print mac, "present:>{}<".format(line[2:-3])
				present = False
				try: 
					rssi 	= max(MACs[mac]["max_rssi"],  int("%i"%struct.unpack('b', line[-2:].decode('hex'))) )
					max_TX 	= MACs[mac]["max_TX"] = max(MACs[mac]["max_TX"],  int("%i"%struct.unpack('b', line[-5:-3].decode('hex'))) )
				except: continue
				for ll in MACs[mac]["raw_data"]:
					#print mac, "test   :>{}<".format(ll[0:-3])
					if line[:-6].strip() == ll:# w/o RX TX
						present = True
						#print mac, "test   : duplicate"
						break
				if not present:
					#U.logger.log(20, "adding:>>{}<< ".format(line[:-3])) 
					MACs[mac]["raw_data"].append( line[:-6] )
					linesDevices +=1
				
				MACs[mac]["MSG_in_10Secs"] +=1
				MACs[mac]["max_rssi"] 	= rssi
				MACs[mac]["max_TX"] 	= max_TX
				if mac =="DD:33:0A:11:15:E3": print "hcidump found DD:33:0A:11:15:E3", MACs[mac]
			out+= "\nhcidump\n" 
			out+= xxx
			U.logger.log(20, "finished  hcidump:     lines -in: {:4d}, accepted: {:4d},  n-devices: {:4d}".format(linesIn,linesAccepted,linesDevices ))

		if True: # lescan
			linesIn = 0
			linesDevices = 0
			linesAccepted = 0
			f = open(G.homeDir+"temp/lescan.data","r")
			xxx = f.read()
			f.close()
			out += "\nlescan\n" 
			out += xxx
			for line in xxx.split("\n"):
				linesIn +=1
				if line.find(":") >-1:
					items = line.split()
					if len(items) <1: continue
					mac = items[0]
					#print mac, items
					linesAccepted +=1
					#if mac =="DD:33:0A:11:15:E3": print "lescan found DD:33:0A:11:15:E3", items[1]
					if mac not in MACs: 
						MACs[mac] = {"max_rssi":-99, "max_TX": -99,"MSG_in_10Secs": 0,"mfg_info":"","n_of_MSG_Types":0,"beaconType":[],"beaconType-msg#":[],"raw_data":[],"pos_of_MAC_in_UUID":[],"pos_of_reverse_MAC_in_UUID":[], "possible_knownTag_options":[]}
						linesDevices +=1
					if items[1].find("unknown") ==-1:
						MACs[mac]["mfg_info"] = items[1].strip()
			U.logger.log(20, "finished  lescan:      lines -in: {:4d}, accepted: {:4d},  n-devices: {:4d}".format(linesIn,linesAccepted,linesDevices ))

		# clean up 
		delMAC = {}
		for mac in MACs:
			#if mac =="DD:33:0A:11:15:E3": print "macs    DD:33:0A:11:15:E3"
			if MACs[mac]["raw_data"]  == []:  
				delMAC[mac] = "Reason: no_raw_data, " + str(MACs[mac])
			if MACs[mac]["max_rssi"] < rssiCutoff: 
				if mac not in delMAC:
					delMAC[mac]  = "Reason: max_rssi:"+str(MACs[mac]["max_rssi"])+" < cuttoff; " + str( MACs[mac]["raw_data"])
				else:
					delMAC[mac] +=       ", max_rssi:"+str(MACs[mac]["max_rssi"])+" < cuttoff; " + str( MACs[mac]["raw_data"])

		out1 ="\n MACs not accepted:\n"
		for mac in delMAC:
			#if mac =="DD:33:0A:11:15:E3": print "deleting:", mac,  delMAC[mac]
			out1 += "{}: {}\n".format(mac, delMAC[mac])
			del MACs[mac]
		#U.logger.log(20, out1)
		
		knownMACS = {}
		newMACs   = {}
		#U.logger.log(20, "MACs: {} ".format(MACs)) 


		## now combine the 3 results in to known and new 
		for mac in MACs:
			#print  "tagging mac: : {} ".format(mac)
			MACs[mac]["MSG_in_10Secs"] = "{:.1f}".format(10.* float(MACs[mac]["MSG_in_10Secs"])/dataCollectionTime) #  of messages in 10 secs
			if mac in onlyTheseMAC:
				#print  "tagging      in onlyTheseMAC"
				knownMACS[mac] = copy.deepcopy(MACs[mac])
				nmsg = 0
				for msg in knownMACS[mac]["raw_data"]:
					nmsg += 1
					hexStr = msg.replace(" ","")[14:]
					#U.logger.log(20, "hexstr: {} ".format(hexStr)) 
					knownMACS[mac]["n_of_MSG_Types"] = nmsg
					for tag in knownBeaconTags:
						#U.logger.log(20, "tag: {} ".format(tag)) 
						posFound, dPostest = testComplexTag(hexStr, tag, mac, mac.replace(":",""), hexStr[0:12])
						if posFound != -1:
							knownMACS[mac]["beaconType"].append(tag)
							knownMACS[mac]["beaconType-msg#"].append(nmsg)
							knownMACS[mac]["possible_knownTag_options"].append(" use: "+tag)

							
			else:
				#print  "tagging  not in onlyTheseMAC"
				newMACs[mac] = copy.deepcopy(MACs[mac])
				nmsg = 0
				for msg in newMACs[mac]["raw_data"]:
					nmsg += 1
					hexStr = msg.replace(" ","")[14:] # this starts w MAC # no spaces
					macPos = hexStr[12:].find(mac.replace(":","")) #check if mac # present afetr mac #
					RmacPos = hexStr[12:].find(hexStr[0:12])	  # check if reverse mac# repsent after mac 
					if macPos  >-1: macPos  += 12
					if RmacPos >-1: RmacPos += 12
					newMACs[mac]["possible_knownTag_options"].append('"name_here":{"battCmd": "off", "beepCmd": "off", "dBm": "-61","prio": 1, "pos": 12,"posDelta": 0,"tag":"'+hexStr[12:-10]+'"}')
					newMACs[mac]["beaconType"].append("")
					newMACs[mac]["beaconType-msg#"].append(nmsg)
					newMACs[mac]["pos_of_MAC_in_UUID"].append(macPos)
					newMACs[mac]["pos_of_reverse_MAC_in_UUID"].append(RmacPos)
					newMACs[mac]["n_of_MSG_Types"] = nmsg
					if macPos >-1: 	
						newMACs[mac]["possible_knownTag_options"][-1] = '"name_here":{"battCmd": "off", "beepCmd": "off", "dBm": "-61","prio": 1, "pos": 12,"posDelta": 0,"tag":"'+hexStr[12:macPos]+'MAC#########"}'
					elif RmacPos >-1: 	
						newMACs[mac]["possible_knownTag_options"][-1] = '"name_here":{"battCmd": "off", "beepCmd": "off", "dBm": "-61","prio": 1, "pos": 12,"posDelta": 0,"tag":"'+hexStr[12:RmacPos]+'RMAC########"}'
					for tag in knownBeaconTags:
						posFound, dPostest = testComplexTag(hexStr, tag, mac, mac.replace(":",""), hexStr[0:12])
						if posFound != -1:
							newMACs[mac]["beaconType"][-1] = tag
							newMACs[mac]["beaconType-msg#"][-1] = nmsg
							newMACs[mac]["possible_knownTag_options"][-1] = '"name_here":{"battCmd": "off", "beepCmd": "off", "dBm": "-61","prio": 1, "pos": '+str(posFound)+',"posDelta": 0,"tag":"'+hexStr[12:-10]+'"}'
							newMACs[mac]["pos_of_MAC_in_UUID"][-1] = macPos
							newMACs[mac]["pos_of_reverse_MAC_in_UUID"][-1] = RmacPos
							if macPos >-1: 	
								newMACs[mac]["possible_knownTag_options"][-1] = '"name_here":{"battCmd": "off", "beepCmd": "off", "dBm": "-61","prio": 1, "pos": '+str(posFound)+',"posDelta": 0,"tag":"'+hexStr[12:macPos]+'MAC#########"}'
							if RmacPos >-1: 	
								newMACs[mac]["possible_knownTag_options"][-1] = '"name_here":{"battCmd": "off", "beepCmd": "off", "dBm": "-61","prio": 1, "pos": '+str(posFound)+',"posDelta": 0,"tag":"'+hexStr[12:RmacPos]+'RMAC########"}'
							break




		## save results and send to plugin 
		f = open(G.homeDir+"temp/BLEAnalysis-new.json","w")
		f.write(json.dumps(newMACs, sort_keys=True, indent=2) )
		f.close()
		f = open(G.homeDir+"temp/BLEAnalysis-existing.json","w")
		f.write(json.dumps(knownMACS, sort_keys=True, indent=2) )
		f.close()
		f = open(G.homeDir+"temp/BLEAnalysis-rejected.json","w")
		f.write(json.dumps(delMAC, sort_keys=True, indent=2) )
		f.close()
		U.logger.log(20, "finished  BLEAnalysis: {:.1f} secs".format(time.time()-starttime))
		subprocess.Popen("sudo chmod +777 "+G.homeDir+"temp/*",shell=True,stdout=subprocess.PIPE,stderr=subprocess.PIPE)
		U.sendURL({"BLEAnalysis":{"rejected_Beacons":delMAC, "new_Beacons":newMACs,"existing_Beacons":knownMACS,"rssiCutoff":str(rssiCutoff)}},squeeze=False)
		time.sleep(1)

	except	Exception, e:
		U.logger.log(30,u"in Line {} has error={}".format(sys.exc_traceback.tb_lineno, e))
	return True



#################################
# this compares the tag string with the incoming hex strin:
# 
# if "RMAC########" in tag string replace it w reverse mac
# if "MAC#########" in tag string repalce it w plan mac
# if x/X in tag string replace char in incoming hex string w X  (= ignore) 
# then do a find 
## 12020106030202180AFF4B4D0XRMAC########
###

def testComplexTag(hexstring, tag, mac, macplain, macplainReverse ):
	global knownBeaconTags, logCountTrackMac, trackMac
	try:
		testString 	= copy.copy(hexstring)
		tagPos 		= int(knownBeaconTags[tag]["pos"])
		tagString 	= copy.copy(knownBeaconTags[tag]["tag"]).upper()
		if tagString.find("X") >-1:
			indexes = [n for n, v in enumerate(tagString) if v == 'X'] 
			testString 	= list(testString.upper())
			for ii in indexes:
				if ii+tagPos < len(testString):
					testString[ii+tagPos] = "X"
				else: return -1,100

			testString = ("").join(testString)
		if tagString.find("RMAC########") >-1:
			tagString = tagString.replace("RMAC########", macplainReverse)
		elif tagString.find("MAC#########") >-1:
			tagString = tagString.replace("MAC#########", macplain)
		posFound 	= testString.find(tagString)
		dPos 		= posFound - tagPos
		if  mac == trackMac and logCountTrackMac >0:
			writeTrackMac("tag-  ","posFound: "+str(posFound)+", dPos: "+str(dPos)+", tag: "+tag+ ", "+str( knownBeaconTags[tag]["tag"])+", tagString: "+tagString)
		return posFound, dPos
	except	Exception, e:
		U.logger.log(30,u"in Line {} has error={}".format(sys.exc_traceback.tb_lineno, e))
		U.logger.log(30,u"Mac#:{}".format(mac))
	return -1,100 



#################################
#################################
######## BLE SENSORS END  #######
#################################
#################################


####### main pgm / loop ############


#################################



####### main pgm / loop ############

def execbeaconloop():
	global	 collectMsgs, sendAfterSeconds, loopMaxCallBLE,	 ignoreUUID,  beacon_ExistingHistory, deleteHistoryAfterSeconds,lastWriteHistory,maxParseSec,batteryLevelPosition
	global acceptNewiBeacons, acceptNewTagiBeacons, onlyTheseMAC,enableiBeacons,offsetUUID,alreadyIgnored, sendFullUUID, minSignalCutoff, acceptJunkBeacons, knownBeaconTags
	global myBLEmac, BLEsensorMACs
	global oldRaw,	lastRead
	global UUIDtoIphone, UUIDtoIphoneReverse, mapReasonToText
	global downCount, doNotIgnore, beaconsOnline, logCountTrackMac, trackMac, nLogMgsTrackMac, startTimeTrackMac, trackMacText

	acceptNewTagiBeacons = ""
	beaconsOnline		= {}

	downCount 			= 0

	BLEsensorMACs 		= {}
	startTimeTrackMac	= 0
	trackMacText		= ""
	#						0		1		2				3			4			5				6				7			8			9
	mapReasonToText		= ["init","timer","new_beacon","fastDown","fastDown_back","beacon_is_back","delta_signal","quickSens","newParams","",""]
	acceptJunkBeacons	= False
	oldRaw				= ""
	lastRead			= 0
	minSignalCutoff		= {}
	acceptNewiBeacons	= -999
	enableiBeacons		= "1"
	G.authentication	= "digest"
	# get params
	onlyTheseMAC		={}
	ignoreUUID			=[]
	ignoreMAC			=[]
	doNotIgnore			=[]
	signalDelta			={}
	UUIDtoIphone		={}
	UUIDtoIphoneReverse		  ={}
	offsetUUID			={}
	fastDown			={}
	batteryLevelPosition={}
	alreadyIgnored		={}
	lastIgnoreReset		=0
	myBLEmac			= ""
	sensor				= G.program	 
	sendFullUUID		= False
	badMacs				= ["00:00:00:00:00:00"]

	myPID			= str(os.getpid())
	#kill old G.programs
	U.setLogging()
	U.killOldPgm(myPID,G.program+".py")
	count = U.killOldPgm(-1,"hciconfig")
	if count > 4:
		U.logger.log(50,"beaconloop exit, hciconfig, to many ghost hciconfig processes running:{}".format(count))
		U.sendRebootHTML("bluetooth_startup is DOWN  too many  ghost hciconfig processes running ",reboot=True, force=True)
		time.sleep(10)

	readParams(True)
	fixOldNames()


	# getIp address 
	if U.getIPNumber() > 0:
		U.logger.log(30, " no ip number ")
		time.sleep(10)
		exit(2)


	# get history
	readbeacon_ExistingHistory()


	## start bluetooth
	for ii in range(5):
		sock, myBLEmac, retCode, useHCI = startBlueTooth(G.myPiNumber)  
		if retCode ==0: break 
		time.sleep(3)
	if retCode != 0: 
		U.logger.log(30,"beaconloop exit, recode from getting BLE stack >0, after 3 tries:")
		sys.exit(1)

	
	loopCount		= 0
	tt				= time.time()
	logfileCheck	= tt + 10
	paramCheck		= tt + 10
	sensCheck 		= tt + 10
	lastIgnoreReset = tt + 10

	U.echoLastAlive(G.program)
	lastAlive		= tt
	G.tStart		= tt
	beaconsNew		= {}
	trackMac		= ""
	nLogMgsTrackMac	= 11 # # of message logged for sepcial mac 
	bleRestartCounter = 0
	eth0IP, wifi0IP, G.eth0Enabled,G.wifiEnabled = U.getIPCONFIG()
	##print "beaconloop", eth0IP, wifi0IP, G.eth0Enabled, G.wifiEnabled

	lastMSGwithData1 = tt
	lastMSGwithData2 = tt
	maxLoopCount	 = 6000
	restartCount	 = 0
	logCountTrackMac		 = 0 

	U.logger.log(30, "starting loop")
	try:
		while True:
			loopCount += 1
			tt = time.time()
			if tt - lastIgnoreReset > 600: # check once per 10 minutes
				alreadyIgnored ={}
				lastIgnoreReset =tt
				eth0IP, wifi0IP, G.eth0Enabled, G.wifiEnabled = U.getIPCONFIG()
					
			
			beaconsNew = {}
		
			U.logger.log(0,"beacons info: {}".format(beacon_ExistingHistory))
			timeAtLoopStart = tt

			U.echoLastAlive(G.program)

			reason = 1

			if checkIfBLErestart():
				bleRestartCounter +=1
				if bleRestartCounter > 10: 
					U.restartMyself(param="", reason="bad BLE restart")
					time.sleep(1)
					sys.exit(4)

				sock, myBLEmac, retCode, useHCI = startBlueTooth(G.myPiNumber)
				if retCode != 0:
					U.logger.log(30,"stopping {} bad BLE start retCode= {}".format(G.program, retCode) )
					if downCount > 1: sys.exit(5)
					time.sleep(2)
					continue

			old_filter = sock.getsockopt( bluez.SOL_HCI, bluez.HCI_FILTER, 14)

			# perform a device inquiry on bluetooth device #0
			# The inquiry should last 8 * 1.28 = 10.24 seconds
			# before the inquiry is performed, bluez should flush its cache of
			# previously discovered devices
			flt = bluez.hci_filter_new()
			bluez.hci_filter_all_events(flt)
			bluez.hci_filter_set_ptype(flt, bluez.HCI_EVENT_PKT)
			sock.setsockopt( bluez.SOL_HCI, bluez.HCI_FILTER, flt )
			sock.settimeout(12)

			sendAfter= sendAfterSeconds
			iiWhile = maxLoopCount # if 0.01 sec/ loop = 60 secs normal: 10/sec = 600 
			while iiWhile > 0:
				iiWhile -= 1
				tt = time.time()
				
				
				if reason > 1 and tt -G.tStart > 30: break	# only after ~30 seconds after start....  to avoid lots of short messages in the beginning = collect all ibeacons before sending

				if tt - timeAtLoopStart	 > sendAfter: 
					break # send curl msgs after collecting for xx seconds

				## get new data
#				allBeaconMSGs = parse_events(sock, collectMsgs,offsetUUID,batteryLevelPosition,maxParseSec ) # get the data:  get up to #collectMsgs at one time
				allBeaconMSGs=[]
				try: pkt = sock.recv(255)
				except Exception, e:
					for ii in range(10):
						if os.path.isfile(G.homeDir+"temp/stopBLE"):
							U.logger.log(20,  "stopBLE is present, waiting for it to disappear")
							time.sleep(5)
						else:
							break
					if os.path.isfile(G.homeDir+"temp/stopBLE"): 
						subprocess.call("rm {}temp/stopBLE".format(G.homeDir), shell=True)
						stopBLE = "stopBLE file PRESENT"
					else:
						stopBLE = "stopBLE file NOT present"

					U.logger.log(50, u"in Line {} has error={}.. sock.recv error, likely time out, {}".format(sys.exc_traceback.tb_lineno, e, stopBLE))
					time.sleep(1)
					U.restartMyself(param="", reason="sock.recv error")
	
				doP = False
				##U.logger.log(20, "loopCount:{}  #:{}  len:{}".format(loopCount, iiWhile, len(pkt))) 
				pkLen = len(pkt)
				if pkLen > 20: 
					num_reports = struct.unpack("B", pkt[4])[0]
					num_reports = 1
					try:
						offS = 7
						for i in range(0, num_reports):
							if pkLen < offS + 10: 
								U.logger.log(20, "bad data{} {} {} {}xx".format(i, num_reports, offS + 6, pkLen))
								break
							# build the return string: mac#, uuid-major-minor,txpower??,rssi
							mac	 				= (packed_bdaddr_to_string(pkt[offS :offS + 6])).upper()
							lastMSGwithData1 	= int(time.time())
							hexstr	 			= (stringFromPacket(pkt[offS:])).upper()
							macplainReverse 	= hexstr[0:12]
							macplain 			= mac.replace(":","")


							########  track mac  start / end ############
							if logCountTrackMac >0:
								if mac == trackMac:
									logCountTrackMac -= 1
									if logCountTrackMac  > 0: 	
										writeTrackMac("RAW---", (datetime.datetime.now().strftime("%H:%M:%S.%f"))[:-5]+ " logCountTrackMac: "+ str(logCountTrackMac)+" hex: "+hexstr)
										
								if 	logCountTrackMac <= 0 or time.time() - startTimeTrackMac > 30:
									writeTrackMac("END   ","FINISHed TRACKMAC logging ===")
									logCountTrackMac  = -1
									U.sendURL(data={"trackMac":trackMacText}, squeeze=False)
									trackMac = ""
							########  track mac  ############
 
									
			
							if mac in badMacs: continue
							if mac in batteryLevelPosition: blOffset= batteryLevelPosition[mac] 
							else:							blOffset= 0
							if mac in offsetUUID:
								offsetU = int(offsetUUID[mac])
							else: 
								offsetU = 0

							nBytesThisMSG		= ord(pkt[offS+6])
							if not acceptJunkBeacons:
								if nBytesThisMSG < 10: 
									#print "reject nBytesThisMSG" 
									continue # this is not supported ..
						

							msgStart			= offS + 7
							if pkLen < msgStart+8 : continue
							AD1Len				= ord(pkt[msgStart])
							AD1Start			= msgStart + 1
							if nBytesThisMSG > 17:
								if AD1Start+AD1Len >= pkLen: continue
								AD2Len			= ord(pkt[AD1Start+AD1Len])
								AD2Start		= AD1Start+AD1Len + 1
							else:
								AD2Len			= AD1Len
								AD2Start		= AD1Start

						
							uuidStart			= AD2Start ##  (-Maj-Min-batteryLength-TX-RSSI)
							uuidLen				= msgStart+nBytesThisMSG-uuidStart-2-2-1-offsetU
							if uuidStart > pkLen - 2 or  uuidStart < 12:
								uuidLen			= min(nBytesThisMSG - 5, 16)
								uuidStart		= AD1Start + 2

							if uuidStart >= pkLen or uuidStart+uuidLen > pkLen : continue
							UUID = stringFromPacket(pkt[uuidStart : uuidStart+uuidLen])
						
							mfgID = stringFromPacket(pkt[msgStart+5])+stringFromPacket(pkt[msgStart+6])  # 4C00 = ibeacon apple
							pType = stringFromPacket(pkt[msgStart+7])  # 02  = procimity beacon, BE  = ALT beacon nBytes  = 27
							beaconType = stringFromPacket(pkt[msgStart+4]).upper()  #  FF = iBeacon
							beaconType += "-"+pType.upper() 
							uuidstart2 = msgStart+8
							try:
								lUUID = max( 1, min(ord(pkt[uuidstart2]), nBytesThisMSG - msgStart))
								UUID2 = stringFromPacket(pkt[uuidstart2+1 :uuidstart2+1+lUUID])
							except: continue

							txx	 = stringFromPacket(pkt[ -2 ])
							bl3	 = "%i" % struct.unpack("b", pkt[ -3 ])
							tx	 = "%i" % struct.unpack("b", pkt[ -2 ])
							rx	 = "%i" % struct.unpack("b", pkt[ -1 ])

							if len(UUID) > 32:
								UUID=UUID[len(UUID) -32:]  # drop AD2 stuff only use the real UUID 
							Maj	 = "%i" % returnnumberpacket(pkt[uuidStart+uuidLen	  : uuidStart+uuidLen + 2])
							Min	 = "%i" % returnnumberpacket(pkt[uuidStart+uuidLen + 2: uuidStart+uuidLen + 4])
							bl	 = ""	


							tagFound 			= False
							UUID1 				= ""
							prio 				= -1
							tag 				= "no"
							dPos 				= -100
							rejectThisMessage 	= False
		
							if mac == trackMac  and logCountTrackMac >0:
								writeTrackMac( "0-    ", "UUID: "+UUID+ ", Maj: "+Maj+", Min: "+Min +", RX:"+str(rx)+", TX:"+str(tx)+", pos-3int:"+str(bl3))

							### is this a know beacon with a known tag ?
							if mac in onlyTheseMAC  and onlyTheseMAC[mac] != ["",0,"",""]:
								tag 			= onlyTheseMAC[mac][0]
								prio 			= onlyTheseMAC[mac][1]
								uuidMajMin 		= onlyTheseMAC[mac][2].split("-")
								useOnlyPrioMsg 	= onlyTheseMAC[mac][3] == "1"
								if mac == trackMac and logCountTrackMac >0:
									writeTrackMac( "1-    ", "tag:"+tag+ ", prio:"+str(prio)+", uuidMajMin:"+str(uuidMajMin)+", useOnlyPrioMsg: "+str(useOnlyPrioMsg))
								# right message format, if yes us main UUID
								if  tag in knownBeaconTags:
									UUID1 	= onlyTheseMAC[mac][0]
									UUID 	= UUID1
									Maj 	= uuidMajMin[1]
									Min 	= uuidMajMin[2]
									tagFound = True
									if useOnlyPrioMsg:
										posFound, dPos = testComplexTag(hexstr, tag, mac, macplain, macplainReverse)
										if posFound == -1 or abs(dPos) > knownBeaconTags[tag]["posDelta"]:
											rejectThisMessage = True
											tagFound = False


							if  mac == trackMac  and logCountTrackMac >0:
								writeTrackMac( "5-    ", "rejectThisMessage:" +str(rejectThisMessage)+ ", UUID: "+UUID +"  "+ Maj+"  "+ Min)
							if rejectThisMessage : continue

							## mac not in current list?
							if UUID1 == "":
								## check if in tag list
								for tag in knownBeaconTags:
									if knownBeaconTags[tag]["pos"] == -1: 			 	continue
									posFound, dPos = testComplexTag(hexstr, tag, mac, macplain, macplainReverse)
									if posFound == -1: 									continue
									if abs(dPos) > knownBeaconTags[tag]["posDelta"]: 	continue
									if acceptNewTagiBeacons == "all" or acceptNewTagiBeacons == tag:
										tagFound = True
										UUID = tag
									break

							if  mac == trackMac  and logCountTrackMac >0:
								writeTrackMac( "9-    ", "tagFound"+str(tagFound)+ ", UUID: "+UUID)

							tx, bl,UUID, Maj, Min, isSensor  = doSensors(pkt, mac, rx, tx, nBytesThisMSG, hexstr, UUID, Maj, Min)

							if mac == trackMac and logCountTrackMac >0:
								writeTrackMac( "Bat-0 ", "isSensor:"+str(isSensor)+", checking bat:"+str(knownBeaconTags[tag]["battCmd"]))
							if not isSensor:
								if bl == "" and tag in knownBeaconTags:
									if type(knownBeaconTags[tag]["battCmd"]) != type({}) and knownBeaconTags[tag]["battCmd"].find("msg:") >-1:
										# parameter format:     "battCmd": "msg:pos=-3,norm=255", 
										try:
											params	=  knownBeaconTags[tag]["battCmd"]
											params	= params.split("msg:")[1]
											if mac == trackMac and logCountTrackMac >0:
												writeTrackMac(  "Bat-1 ","params:{}".format( params) )
											params	= params.split(",")
											batPos	= int(params[0].split("=")[1])*2
											norm	= float(params[1].split("=")[1])
											bl	 	= "{:.0f}".format( 100.* int(hexstr[batPos:batPos+2],16)/norm )
											if mac == trackMac and logCountTrackMac >0:
												writeTrackMac(  "Batl-2 ","params:{}, batpos:{}, norm:{}, bl:{}".format(params, batPos, norm, bl) )
										except	Exception, e:
											if mac == trackMac and logCountTrackMac >0:
												writeTrackMac("", u"in Line {} has error={}".format(sys.exc_traceback.tb_lineno, e))
											bl		= ""

								if not acceptJunkBeacons:
									if UUID == "": 
										#print "reject UUID" 
										if  mac == trackMac  and logCountTrackMac >0:
											writeTrackMac( "10    ", "tagFound reject bad uuid")
										continue # this is not supported ..
								
							
							lastMSGwithData2 = int(time.time())
						

							if  mac == trackMac and logCountTrackMac >0:
								writeTrackMac( "11-   ", "added to beaconMSG")
							beaconMSG = [mac, UUID+"-"+Maj+"-"+Min, rx, tx, bl, beaconType, nBytesThisMSG]

							#U.logger.log(10, "{} {}-{}-{}  RX:{}, TX:{}, BL:{}, bTp:{}, pType:{}, lUUID:{},  nBytes:{}".format(mac, UUID, Maj, Min, rx, tx, bl, bType,  pType, lUUID, nBytesThisMSG) )
							if  mac == trackMac and logCountTrackMac >0:U.logger.log(10, "{}  {}-{}-{}  RX:{}, TX:{},  TXx:{}, BL:{}, bType:{} , mfgId:{},  lUUID:{:2d},  nBytes:{:2d},  pktl:{:2d}".format(mac, UUID.ljust(33), Maj.rjust(6), Min.ljust(6), rx.ljust(4), tx.ljust(4),  txx, bl, beaconType, mfgID, lUUID, nBytesThisMSG, pkLen) )
							if False and   mac == trackMac : #False and ( G.debug>3  or mac[0:5]=="E0:48" or pkLen < 20 ):
									doP=True
									print beaconMSG, " len: "+str(pkLen)+" nBytesThisMSG: "+str(nBytesThisMSG)+	 " AD1Start: "+str(AD1Start)+  " AD1Len: "+str(AD1Len)+	 " AD2Start: "+str(AD2Start)+  " AD2Len: "+str(AD2Len)+	 " uuidStart: "+str(uuidStart)+	 " uuidLen: "+str(uuidLen)
									print	  ( " " .join( str(n).rjust(4) for n in range( offS )  )  )	 + " | "							+ ( " " .join( str(n).rjust(4) for n in range(offS, offS + 6 )	)  )  + " | " +	 ( " " .join( str(n).rjust(4) for n in range( offS + 6,pkLen )	)  )
									print "	 "+ "  ".join(str((stringFromPacket(pkt[n:n+1]))).ljust(3) for n in range(  offS )	) + "|	 "+ "  ".join(str((stringFromPacket(pkt[n:n+1]))).ljust(3) for n in range(offS,  offS + 6 )	 ) + "|	  "+ "	".join(str((stringFromPacket(pkt[n:n+1]))).ljust(3) for n in range( offS + 6,pkLen )	  )
									print " ".join(str(ord(pkt[n])).rjust(4) for n in range(   offS	 )	)+ " | "								+" ".join(str(ord(pkt[n])).rjust(4) for n in range( offS,  offS + 6	 )	)+ " | "+ " ".join(str(ord(pkt[n])).rjust(4) for n in range(  offS + 6,pkLen  )	 )
									print " ".join(str("%i" % struct.unpack("b", pkt[n ])).rjust(4) for n in range( offS ) )+ " | "			   + " ".join(str("%i" % struct.unpack("b", pkt[n ])).rjust(4) for n in range(offS, offS + 6) )+ " | "+ " ".join(str("%i" % struct.unpack("b", pkt[n ])).rjust(4) for n in range(offS + 6,pkLen) )
									#print "temp ", tempString , tempString/ 100., (tempString/ 100. )*1.8 + 32
							
							offS+=nBytesThisMSG
							#U.logger.log(0, "allBeaconMSGs: "+unicode( beaconMSG) )


							try: 
								beaconMAC	= mac
								uuid		= UUID+"-"+Maj+"-"+Min
								rssi		= float(rx)
								txPower		= float(tx)
								bLevel		= bl
								pkLen		= nBytesThisMSG
							except	Exception, e:
								U.logger.log(50, u"in Line {} has error={}".format(sys.exc_traceback.tb_lineno, e))
								U.logger.log(30, "bad data >> "+unicode(beaconMSG)+"  <<beaconMSG")
								continue# skip if bad data
 
							### if in fast down lost and signal < xx ignore this signal= count as not there 
							if beaconMAC in fastDown : sendAfter = min(45., sendAfterSeconds)
							if checkIfFastDownMinSignal(beaconMAC,rssi,fastDown): 
								if  mac == trackMac and logCountTrackMac >0:
									writeTrackMac( "12-   ", "checkIfFastDownMinSignal ")
								continue

							iphoneUUID, beaconMAC = checkIfIphone(uuid,beaconMAC)
							if not iphoneUUID:
								if checkIfIgnore(uuid,beaconMAC): 
									if  mac == trackMac and logCountTrackMac >0:
										writeTrackMac( "13-   ", "reject checkIfIgnore ") 
									continue

							if not (beaconMAC in onlyTheseMAC or beaconMAC in doNotIgnore):
								#print " new beacon: ",beaconMAC, tagFound, uuid    # this is a new one
								if rssi < acceptNewiBeacons and not tagFound: 
									if  mac == trackMac and logCountTrackMac >0:
										writeTrackMac( "14-   ", "reject rssi <  and !tagFound  ")
									continue						  # if new it must have signal > threshold

							if beaconMAC not in beaconsNew: # add fresh one if not in new list
								beaconsNew[beaconMAC]={"uuid":uuid,"txPower":txPower,"rssi":rssi,"count":1,"timeSt":tt,"bLevel":bl,"pktInfo":"len:"+str(pkLen)+", type:"+beaconType, "dCount":0}# [uid-major-minor,txPower,signal strength, # of measuremnts
								#reason = 3
							
							else:  # increment averages and counters
								beaconsNew[beaconMAC]["rssi"]	 += rssi # signal
								beaconsNew[beaconMAC]["count"]	 += 1  # count for calculating averages
								beaconsNew[beaconMAC]["txPower"] += txPower # transmit power
								beaconsNew[beaconMAC]["timeSt"]	 = tt  # count for calculating averages
								beaconsNew[beaconMAC]["bLevel"]	 = bLevel # battery level or temp of sensor 
							reason= checkIfNewOrDeltaSignalOrWasMissing(reason,beaconMAC,beaconMSG,beaconsNew)
							if  mac == trackMac and logCountTrackMac >0:
								writeTrackMac( "99    ", "accepted")
							####if beaconMAC =="0C:F3:EE:00:66:15": print  beaconsNew

					except	Exception, e:
						U.logger.log(50, u"in Line {} has error={}".format(sys.exc_traceback.tb_lineno, e)+ "  bad data, skipping")
						try:
							print "	 MAC:  ", mac
							print "	 UUID: ", UUID
						except: pass
						continue# skip if bad data


				reason, beaconsNew = checkIfFastDown(beaconsNew,reason) # send -999 if gone 

				if tt - sensCheck > 4:
					if U.checkNowFile(sensor): reason = 7 # quickSens
					sensCheck = tt		
	  
					if BLEAnalysis(useHCI):
						sock, myBLEmac, retCode, useHCI = startBlueTooth(G.myPiNumber)

					checkIFtrackMacIsRequested()

				if tt - paramCheck > 10:
					if readParams(False): reason = 8 # new params
					paramCheck=time.time()

			


			sock.setsockopt( bluez.SOL_HCI, bluez.HCI_FILTER, old_filter )
			#print "reason",datetime.datetime.now(), reason
			composeMSG(beaconsNew,timeAtLoopStart,reason)
			handleHistory() 
			U.echoLastAlive(G.program)


			dt1 = int(time.time() - lastMSGwithData1)
			dt2 = int(time.time() - lastMSGwithData2)
			if dt1 > G.rebootIfNoMessagesSeconds:
				if dt1 > 90 or dt2 > 90:
					G.debug = 10
					maxLoopCount = 20
					restartCount +=1
					U.logger.log(30, u" time w/out any message .. anydata: %6d[secs];  okdata: %6d[secs];   loopCount:%d;  restartCount:%d"%(dt1,dt2,loopCount,restartCount))
					if dt2 > 400 :
						time.sleep(20)
						U.restartMyself(param="", reason="bad BLE (2),restart")
					if restartCount > 1:
						U.logger.log(30, " restarting BLE stack due to no messages "+G.program)
						sock, myBLEmac, retCode, useHCI = startBlueTooth(G.myPiNumber)
						maxLoopCount = 6000
				else:
					restartCount = 0

	except	Exception, e:
		U.logger.log(50, u"in Line {} has error={}".format(sys.exc_traceback.tb_lineno, e))
		U.logger.log(30, "  exiting loop due to error\n restarting "+G.program)
		time.sleep(20)
		subprocess.call("/usr/bin/python "+G.homeDir+G.program+".py &", shell=True)
	try: 	G.sendThread["run"] = False; time.sleep(1)
	except: pass

U.echoLastAlive(G.program)
execbeaconloop()

U.logger.log(30,"end of beaconloop.py ") 
sys.exit(0)		   
